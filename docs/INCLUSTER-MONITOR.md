# Running a read-only InfraGuard monitor inside Kubernetes

The `Dockerfile.monitor` image packages Python 3.12 and the read-only SLO monitor. It does not contain kubectl. With `--in-cluster`, the monitor reads Kubernetes' mounted ServiceAccount token and cluster CA, performs authenticated HTTPS GET requests to the Argo Rollouts API, and polls Prometheus through a ClusterIP endpoint.

`deploy/monitor.yaml` creates a dedicated ServiceAccount and namespace-scoped Role with **only** `get` on Rollouts. It also deploys a non-root, read-only-root-filesystem monitor Pod. No `rollouts/status` PATCH is granted, no abort logic is called, and no credentials are committed.

This is a read-only poller, **not** a full leader-elected Kubernetes operator. It is a disposable Kind reference, not a production deployment. HTTPS certificate and token mounting are handled by the Kubernetes ServiceAccount volume; all network access stays inside the test cluster unless externally exposed.
