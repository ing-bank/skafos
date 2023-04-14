"""
Main class of operator
"""
import logging
import threading
from queue import Queue
from threading import Lock
from typing import Union

from kubernetes import client, watch

from skafos import crdregistration
from skafos.healthcheck import start_healthcheck, beat_healthcheck
from skafos.leaderelection import become_leader


class StreamWatch:
    """
    Responsible for creating EventListener derivations and handling of CRD events.
    """
    __active = False

    def __init__(self, target: Union[str, dict], listeners: list, config: dict = None):
        """
        Client and Gauge will be passed to EventListener objects as they are created. the target must be a path
        to a crd.yaml file or a dict. In case of a dictionary the following keys are expected:
        * (optional) args list
        * (optional) kwargs dict
        * method: method that returns a reference to a method of the kubernetes.client.api_client.ApiClient
        * (optional) api: kubernetes.client.api_client.ApiClient

        For example:
        {
            'args': [parameters],
            'kwargs': {'named': 'parameters'}
            'method': lambda x: x.some_method
            'api': client.CoreV1Api
        }

        :param target:
        :param [] listeners:
        :param config:
        """
        self.logger = logging.getLogger('skafos')

        self.target = target
        self.listeners = listeners

        self.config = config
        self.api_client = client.api_client.ApiClient(configuration=config)
        self.lock = Lock()

    def reconcile(self, event):
        """
        Handles a new custom CRD event from Kubernetes event stream.

        :param event: CRD event produced by Kubernetes event stream
        """
        current_event = event

        if isinstance(event['object'], dict) and event['object']["metadata"].get("name") is None:
            return
        elif (not isinstance(event['object'], dict)) and event['object'].metadata.name is None:
            return

        self.lock.acquire()
        ev_state = {}
        try:
            processed_items = []
            for listener in self.listeners:
                init_listener = listener
                if callable(listener):
                    init_listener = listener(client.api_client.ApiClient(configuration=self.config), current_event)
                    self.lock.release()

                processed_items.append(init_listener)
                processed_event_successfully = False
                try:
                    processed_event_successfully = init_listener.process(current_event, ev_state)
                except Exception:
                    logging.exception('listener failed to process event')

                if callable(listener):
                    self.lock.acquire()

                if not processed_event_successfully:
                    self.logger.warning("Listener returned False on event, rolling back previous changes")
                    for old_listener in reversed(processed_items):
                        old_listener.rollback()
                    break  # Do not process remaining listeners; we have already failed
        finally:
            self.lock.release()

    @staticmethod
    def create_config(ssl_path):
        """
        creating config and adding kube ca to allowed ca's.

        :param str ssl_path: Path to SSL certificate
        :return: client.Configuration object
        """
        configuration = client.Configuration()
        configuration.verify_ssl = True
        configuration.ssl_ca_cert = ssl_path
        return configuration

    def register_crd(self, api_client, singular):
        """
        Check if CRD registration is already done, if not: make it so (shut up Wesley).
        """
        ext_client = client.ApiextensionsV1beta1Api(api_client)

        current_crds = [x["spec"]["names"]["kind"].lower() for x in
                        ext_client.list_custom_resource_definition().to_dict()["items"]]

        if singular not in current_crds:
            self.logger.info("need to create crd")
            crdregistration.register(ext_client, path_to_crd=self.target)
        else:
            self.logger.info("No need to register, as CRD is already registered")

    def get_stream_config(self):
        if isinstance(self.target, str):
            api = client.CustomObjectsApi(self.api_client)

            group, version, plural, singular = crdregistration.get_crd_config(self.target)
            self.register_crd(self.api_client, singular)

            return api, [group, version, plural], {}, lambda x: x.list_cluster_custom_object

        elif isinstance(self.target, dict):
            if 'api' in self.target:
                api = self.target['api'](self.api_client)
            else:
                api = client.CoreV1Api(self.api_client)

            return api, self.target.get('args', []), self.target.get('kwargs', {}), self.target['method']

    def run(self, timeout=7200, n_threads=48, healthcheck_port=5000, leader_election_ns=''):
        """
        This function will continuously watch and process the kubernetes event stream for
        CRD events. This is a (perpetually) blocking operation.
        """
        api, args, kwargs, method = self.get_stream_config()
        start_healthcheck(timeout + 60, port=healthcheck_port)

        if leader_election_ns:
            become_leader(leader_election_ns)

        def worker(index, jobs):
            logging.debug('Worker %d up', index)
            while True:
                job = jobs.get()
                try:
                    logging.debug('Worker %d (%s) is processing a job', index, threading.currentThread().getName())
                    self.reconcile(job)
                    logging.debug('Worker %d (%s) has %d jobs left in queue',
                                  index, threading.currentThread().getName(), jobs.qsize())
                except Exception as ex:
                    logging.error('Worker %d (%s) failed: %s', index, threading.currentThread().getName(), str(ex))

        # Every worker (in its own thread) has a queue. New events get hashed by name to a queue index.
        # When there are multiple events for the same object they end up in the same queue, no race conditions.
        queues = [Queue() for _ in range(n_threads)]

        threads = []
        for i in range(n_threads):
            t = threading.Thread(target=worker, args=(i, queues[i]), daemon=True)
            t.start()
            threads.append(t)

        resource_version = 0
        while True:
            self.logger.info("(re)starting stream")
            watcher = watch.Watch()
            stream = watcher.stream(method(api), *args, **kwargs,
                                    resource_version=resource_version, timeout_seconds=timeout)
            beat_healthcheck()

            for new_event in stream:
                self.logger.debug("rv: %s", str(resource_version))
                self.logger.debug(new_event)
                if new_event["type"] == "ERROR" and new_event["object"]["reason"] == "Expired":
                    watcher.stop()
                else:
                    event_name = 'anonymous'
                    try:
                        event_name = new_event['raw_object']['metadata']['name']
                    except:
                        pass

                    designated_worker = hash(event_name) % n_threads
                    queues[designated_worker].put(new_event)

                    self.logger.debug("Thread count: " + str(threading.active_count()))
                    for i, t in enumerate(threads):  # Health Check
                        if not t.is_alive():
                            raise Exception('Worker ' + str(i) + ' is not alive')
