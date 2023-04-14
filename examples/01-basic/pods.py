import logging
from kubernetes import client

from skafos.event_listener import EventListener


class Pod(EventListener):
    '''
    Basic implementation. No update method as pods don't like to be updated.
    '''
    def __init__(self, api_client, event):
        super().__init__(api_client, event)

        self.core_v1 = client.CoreV1Api(api_client=api_client)

    def __create_body(self):
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "labels": {
                    "name": self.metadata["name"]
                },
                "name": self.metadata["name"]
            },
            "spec": {
                "containers": [
                    {
                        "image": self.event["object"]["spec"]["image"],
                        "imagePullPolicy": "Always",
                        "name": self.metadata["name"],
                        "ports": [
                            {
                                "containerPort": 8080,
                                "name": "http",
                                "protocol": "TCP"
                            }
                        ]
                    }
                ]
            }
        }

    def create(self):
        logging.info('%s :: creating pod', self.metadata["name"])
        try:
            self.core_v1.create_namespaced_pod(namespace=self.metadata["namespace"], body=self.__create_body())
        except client.rest.ApiException as e:
            if e.status == 403:
                logging.info('%s :: unauthorized, can also be it already exists', self.metadata["name"])
            elif e.status == 409:
                logging.info('%s :: superpod already exists', self.metadata["name"])
            else:
                logging.warning('%s :: in creation of superpod, not handled returncode: %s', self.metadata["name"],
                                str(e.status))

    def delete(self):
        logging.info('%s :: deleting pod', self.metadata["name"])
        try:
            self.core_v1.delete_namespaced_pod(name=self.metadata["name"], namespace=self.metadata["namespace"])
        except client.rest.ApiException as e:
            if e.status == 403:
                logging.info('%s :: unauthorized', self.metadata["name"])
            else:
                logging.warning('%s :: in deletion of superpod, not handled returncode: %s', self.metadata["name"],
                                str(e.status))
