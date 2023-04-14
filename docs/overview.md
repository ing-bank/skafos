## Watching the event stream
First, import the Kubernetes event stream watcher:
```python
from skafos.stream_watch import StreamWatch
```

You can then create a `StreamWatch` instance:
```python
listeners = []
path_to_crd = '/path/to/crd.yml'
stream_watch = StreamWatch(path_to_crd, listeners)
```
We keep listeners empty for now, they will be explained further on.
Listeners are classes that handle incoming events. They will be called,
and even created if needed, by the `StreamWatch` instance.

The `StreamWatch` will watch for custom event objects 
the moment it will run. It will notify listeners the moment there
is a new event. For example:
```python
stream_watch.run()  # This is a blocking call
```

To stop the blocking loop, call `stream_watch.stop()`. Note that this will
mean that the watcher stream does not refresh after a timeout, so it can take
some time. To modify the timeout, specify it in run, e.g.: 
```
stream_watch.run(timeout=60)  # Seconds
```

## Handeling objects
When there is a new event the `StreamWatch` will call listeners you specified.
All listeners should inherit from the `EventListener class`, like so:

```python
from skafos.event_listener import EventListener


class MyListener(EventListener):
    def create(self):
        """Called on a new create event"""
    
    def update(self):
        """Called on an update event"""
        
    def delete(self):
        """Called on a delete event"""
        
    def error(self):
        """Called on an error event"""
```

`StreamWatch` will set the following parameters in `EventListener` automatically:
* `event`, the (raw) received event
* `metadata`, the key **metadata** from the received event.

### Reference and classname listeners
You can pass listeners to `StreamWatch` in two ways:
* By **reference**: you supply a class instance, this instance will be re-used continously
* By **classname**: you supply a class name, `StreamWatch` will initialise this class per event.

For example, take the following class:
```python
class Metrics(EventListener):
    number_of_updates = 0
    
    def update(self):
        self.number_of_updates += 1
```
The `Metrics` class should be created only once. We supply it to the `StreamWatch` like
this:
```python
listeners = [Metrics()]
stream_watch = StreamWatch('/path/to/crd.yml', listeners)
stream_watch.run()
```
In this case `StreamWatch` will re-use the `Metrics()` class with each event; it will **not** be
re-created. Now consider a case where we want a new instance to be created every time there
is a new event, then we supply a class name:
```python
listeners = [MyListener]
stream_watch = StreamWatch('/path/to/crd.yml', listeners)
stream_watch.run()
```

## Keep alive
All `EventListener` instances are protected with a `try-except` clause for all exceptions.
This ensures that everything keeps running even if there is an unexpected event.

## Health checks
Health checks are based on the health of the event stream. The port for health checks can be configured via
the `healthcheck_port` variable in the `StreamWatch.run` method.

## Leader election
Leader election is required for running with multiple replicas. To enable it set the Namespace name `leader_election_ns`
variable in the `StreamWatch.run` method. This will result in a ConfigMap being updated in that namespace, so the 
operator SA needs permissions for that.

## Running inside a cluster
When you run your operator inside a cluster (as a deployment), don't forget to provide the appropriate RBAC!