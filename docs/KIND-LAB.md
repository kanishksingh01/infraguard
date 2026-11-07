# Deploy a fault-injection lab in disposable Kind

Do not run this in a shared/production cluster. The container binds to all interfaces inside the pod and has an unauthenticated admin endpoint **for testing only**. The Service is ClusterIP-only; ClusterIP is not authentication. Isolate the cluster and never expose the Service through Ingress, NodePort or LoadBalancer.

## Requirements
Docker, Kind, kubectl and an isolated local Kubernetes context.

```bash
kind create cluster --name infraguard --config deploy/kind-config.yaml
docker build -t infraguard-lab:dev .
kind load docker-image infraguard-lab:dev --name infraguard
kubectl --context kind-infraguard apply -f deploy/lab.yaml
kubectl --context kind-infraguard -n infraguard-lab rollout status deploy/infraguard-fault-lab
kubectl --context kind-infraguard -n infraguard-lab port-forward svc/infraguard-fault-lab 8088:8088
```

From another terminal:
```bash
python3 -m lab.load_test --requests 120 --concurrency 12
curl -X POST 'http://127.0.0.1:8088/admin/fanout?value=8'
python3 -m lab.load_test --requests 120 --concurrency 12
curl -X POST 'http://127.0.0.1:8088/admin/fanout?value=1'
```

Delete the cluster: `kind delete cluster --name infraguard`.

## Scope
These manifests deploy the **fault lab as a normal Kubernetes Deployment**. They do not deploy an Argo Rollout or Prometheus. A future integration environment must supply the Argo Rollouts controller/CRD and Prometheus, and distinguish real rollout behavior from simulator effects. No cluster execution is claimed yet.
