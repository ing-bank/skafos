# Skafos
Framework for Kubernetes/Openshift Operators in Python

## About
The initial open-source release of this project is provided as-is. That implies that the codebase is only a slightly
modified version of what we at ING are using. In the future we would like to extend this Open Source repository with
the appropriate pipelines and contribution mechanics. This does imply that your journey for using this project for your
own purposes can use some improvement, and we will work on that.

This project is part of the ING Neoria. Neoria contains parts of the ING Container Hosting Platform (ICHP) stack 
which is used to deliver Namespace-as-a-Service on top of OpenShift.

## Quickstart
```bash
pip install git+https://github.com/ing-bank/skafos
```

Create an EventListener, e.g.:
```python
from skafos.event_listener import EventListener


class MyCustomResource(EventListener):
    def create(self):
        print('MyCustomResource was created')

    def update(self):
        print('MyCustomResource was updated')

class Metrics(EventListener):
    pass # TODO: implement metrics here
```

Register your EventListener, and listen for events:
```python
from skafos.stream_watch import StreamWatch
from kubernetes import config

config.load_incluster_config()
listeners = [Metrics(), MyCustomResource] # Metrics object will be re-used, MyCustomResource will be instantiated on every event
StreamWatch('./crd.yaml', listeners).run() # Blocks forever
```

In this example we listen to events for a CRD defined in `crd.yaml`. Note that on startup all existing objects will
be passed as Created events (default Kubernetes watch behavior).

For a more detailed example implementation: [see the basic example](examples/01-basic/README.md)
More details on how this framework works can be found in the [docs folder](docs/overview.md)

## My First Operator
1. Create a basic crd description ( https://kubernetes.io/docs/tasks/access-kubernetes-api/custom-resources/custom-resource-definitions/#create-a-customresourcedefinition ) NOTE: if you are not on kubernetes 1.16 or higher: use "apiextensions.k8s.io/v1beta1"
2. Create your resources implementation with inheriting the EventLister class, with at least the create method [Example](examples/01-basic/pods.py)
3. Create your [app.py](examples/01-basic/app.py)
4. Start it ```python3 app.py```

Note, in Kubernetes watches when an event stream starts all the existing objects will be passed as `Created` events.

## Running without CRD
It is possible to create an Operator without CRD. In this case you are not listening to custom objects, but
the Core API. You can specify what object you want to watch by using a dict:

```python
crd = {
    'args': [],
    'kwargs': {},
    'method': lambda x: x.list_namespace
}

OPERATOR = StreamWatch(crd, [MyCustomListener])
OPERATOR.run()  # Blocking call
```

Using `args` and `kwargs` you can add parameters to the Core API method that you want to watch. In this case
the `list_namespace` method is watched, and it has no parameters.
