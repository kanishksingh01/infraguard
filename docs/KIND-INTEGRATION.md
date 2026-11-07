# Real Kubernetes lab CI

The `Kind Integration` workflow creates a disposable Kind cluster on a GitHub-hosted runner. It builds the Docker image from source, loads the image into the cluster, deploys the isolated ClusterIP-only fault lab, waits for the Kubernetes Deployment to become ready, and port-forwards the service to the runner's loopback.

The smoke test checks a healthy one-backend-call baseline, changes the synthetic fanout to eight calls, measures failure amplification and rejected backend attempts, verifies Prometheus exposition, and restores the healthy fanout.

### What this proves
A container runs in a real Kubernetes Pod, becomes ready, is reachable through a Kubernetes Service, and exhibits the simulated failure behavior. The workflow fails if baseline requests error, the fault doesn't cause rejection, or metrics are malformed.

### What it does not prove
There is no Argo Rollouts controller in this workflow and no automated rollback. Those are separate integration milestones. The simulated backend is an in-process concurrency pool, not a production network, database, or API.

### Security
Run only on private disposable clusters. `POST /admin/fanout` has no authentication for isolated testing and **must never** be exposed via public Ingress, public LoadBalancer, or shared-cluster Service. The workflow uses no cloud credentials and no proprietary material.
