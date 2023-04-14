"""
An implementation for leader election based on a timestamp and hostname in a ConfigMap.
For Skafos we don't use the `kubernetes.leaderelection` package because we would like
to run the EventLoop in the main thread, as well as keep a heartbeat going for the health
check.

If a leader loses its claim then the program is simply terminated.
"""
import logging
from datetime import datetime, timedelta
import os
import random
import threading
import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from skafos.healthcheck import beat_healthcheck

JITTER_SEC = 5
LEADER_EXPIRED_INTERVAL_SEC = 30
LEADER_HEARTBEAT_INTERVAL_SEC = 10


def get_hostname_name():
    """
    Get hostname name gets the hostname of the Pod and generates a common name that can be shared
    across multiple replicas
    :return: (hostname, name)
    """
    hostname = os.getenv('HOSTNAME')
    name = '-'.join(hostname.split('-')[:-2]) + '-le'  # Leader Election ConfigMap name
    return hostname, name


def generate_leader_cm(namespace):
    hostname, name = get_hostname_name()

    return {
        'apiVersion': 'v1',
        'metadata': {
            'name': name,
            'namespace': namespace
        },
        'data': {
            'leader': hostname,
            'heartbeat': datetime.now().isoformat()
        }
    }


def become_leader(namespace):
    """
    Become leader blocks until a leadership claim has been established. Needs permissions to read and replace
    ConfigMap objects in the given namespace. This function also takes care of the health check until the leadership
    claim has been established.

    :param namespace: Namespace where to create the leadership claim ConfigMap
    :return: Nothing, blocks until a leadership claim has been established.
    """
    hostname, name = get_hostname_name()

    logging.getLogger('skafos').info('starting leader election')
    time.sleep(random.randint(0, JITTER_SEC))  # Some jitter to avoid all claims at the same time

    while True:
        try:
            # Read out current leader. This will raise an exception if there is no leader yet
            cm = client.CoreV1Api().read_namespaced_config_map(name, namespace)
            if cm.data['leader'] == hostname:
                return stay_leader(namespace)
            logging.getLogger('skafos').info('last heard from leader: %s %s', cm.data['leader'], cm.data['heartbeat'])

            # Check if current leader is healthy
            expiry_date = datetime.now() - timedelta(seconds=LEADER_EXPIRED_INTERVAL_SEC)
            if datetime.fromisoformat(cm.data['heartbeat']) < expiry_date:
                logging.getLogger('skafos').info('Current leader is not responsive, making leadership claim')
                client.CoreV1Api().replace_namespaced_config_map(name, namespace, generate_leader_cm(namespace))
                time.sleep(random.randint(JITTER_SEC, JITTER_SEC * 2))  # Avoid race condition for replace+read

            else:  # Our leader is healthy, wait for a while
                time.sleep(
                    random.randint(LEADER_HEARTBEAT_INTERVAL_SEC * 2, LEADER_HEARTBEAT_INTERVAL_SEC * 2 + JITTER_SEC))

            beat_healthcheck()  # Since the event loop is not yet running we have to beat the heartbeat

        except ApiException as ex:
            if ex.status == 404:  # No leader yet, claim leadership
                logging.getLogger('skafos').info('no leader yet, will try to claim leadership')
                try:
                    client.CoreV1Api().create_namespaced_config_map(namespace, generate_leader_cm(namespace))
                except ApiException as ex2:
                    if ex2.status == 409:  # Another replica beat us to it
                        logging.getLogger('skafos').info(
                            'failed to claim leadership, another leadership claim already exists')
                        continue
                    else:
                        raise ex2  # Unsupported ApiException status code, just crash
                return stay_leader(namespace)
            else:
                raise ex  # Unsupported ApiException status code, just crash


def stay_leader(namespace):
    hostname, name = get_hostname_name()
    logging.getLogger('skafos').info('we are the leader: %s', hostname)

    def update_cm_forever():
        try:
            while True:
                cm = client.CoreV1Api().read_namespaced_config_map(name, namespace)
                if cm.data['leader'] != hostname:
                    raise RuntimeError('lost leadership (us: ' + hostname + ', leader: ' + cm.data['leader'] + ')')

                client.CoreV1Api().replace_namespaced_config_map(name, namespace, generate_leader_cm(namespace))
                time.sleep(LEADER_HEARTBEAT_INTERVAL_SEC)

        except ApiException as ex:
            logging.getLogger('skafos').critical('failed to update leader election configmap. exiting.')
            raise ex
        finally:
            logging.getLogger('skafos').critical('terminating due to leader election failure')
            die()

    threading.Thread(target=update_cm_forever, daemon=True).start()


def die():
    """
    Die kills the program, main thread
    """
    import signal
    os.kill(os.getpid(), signal.SIGINT)
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGKILL)
    time.sleep(1)
    os._exit(1)
