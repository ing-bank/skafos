import os
import logging

from skafos.stream_watch import StreamWatch
from kubernetes import client, config

from pods import Pod

if __name__ == "__main__":
    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()

    logging.getLogger().setLevel(logging.INFO)

    OBJECTTYPES = [Pod]
    STREAMWATCH = StreamWatch('./crd.yaml', OBJECTTYPES)
    STREAMWATCH.run()
