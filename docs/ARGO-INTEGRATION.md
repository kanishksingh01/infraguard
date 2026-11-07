# Argo Rollouts integration test (Kind only)

This workflow installs a pinned Argo Rollouts v1.10.2 controller and CRDs in a disposable GitHub-hosted Kind cluster, deploys two lab replicas, changes a pod-template annotation to create a canary, waits for the canary pause and calls the guarded abort status patch.

## Safety and scope
- All writes are confined to the disposable `kind-infraguard` context in the `infraguard-lab` namespace.
- Test approval evidence is synthetic and generated inside CI, **not** a real Prometheus evaluation.
- It validates a specific Argo Rollouts API behavior; it does not validate production-ready incident response.
- The controller is installed cluster-wide only inside an isolated ephemeral test cluster.
- There is no route from the workflow to a customer, employer, or production cluster.

## Success criterion
A new canary reaches a paused state, atomic JSON Patch preconditions pass against the current UID/resourceVersion, the abort status patch succeeds, and the controller reflects aborted/degraded state within 120 seconds.

## What remains
End-to-end *real* Prometheus-based automated recommendations; event-based continuous observation; immutable audit reporting; measured rollback recovery; and expanded RBAC checks.
