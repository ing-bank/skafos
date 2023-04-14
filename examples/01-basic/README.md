# Basic skafos controller

## requirements on your system
 - Python3
 - a logged in client ( ~/.kube/config )
 - kubernetes client library (```pip3 install kubernetes```)

## How to start:
```
# install skafos (via install instructions of original readme)

# run the operator
kubectl apply -f crd.yaml
python app.py

# to create an instance (in other terminal):
kubectl apply -f example.yaml

# to delete the superpod again:
kubectl delete -f example.yaml
```

### Notes
Pods don't like to be updated, so there is no update method