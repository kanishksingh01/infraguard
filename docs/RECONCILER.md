# InfraGuard bounded reconciliation prototype

`python3 -m guard.reconciler --rollout checkout --prometheus http://127.0.0.1:9090 --cycles 12 --interval 5` evaluates the current Kind Argo Rollout and Prometheus metrics on a finite interval, preserving threshold streaks between healthy observations and clearing stale/unknown state. Default mode reports JSON decisions without changes.

A lab-only abort additionally needs `--execute --confirm ABORT:infraguard-lab/checkout`. The command checks that the named Kind context's API server uses localhost HTTPS and the existing abort path uses namespace-scoped impersonation, UID/resourceVersion preconditions and JSONL audit preflight.

This is **single-process bounded polling**, not a controller-runtime operator, and checking a localhost API is not cryptographic cluster attestation. It is not intended for production deployment.

## Live integration coverage

The coupled canary CI now calls two steps of the real `Reconciler` on fresh Rollout/Prometheus observations, spaced by five seconds, rather than directly invoking the original one-shot SLO observer. The second sustained breach executes exactly one approved lab abort; the integration subsequently checks the stable Service. This validates the bounded reconciliation logic against real Kubernetes and Prometheus, without claiming production controller-runtime functionality.
