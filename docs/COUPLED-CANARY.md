# Coupled bad-canary-to-SLO-to-abort test

The isolated Kind test in `.github/workflows/coupled-canary.yml` deploys a real Argo Rollout with a healthy revision (`INFRAGUARD_FANOUT=1`) and creates a new revision with eightfold backend fanout. The Python fault simulator reads that setting at container startup.

Prometheus uses namespace-restricted Kubernetes Pod discovery to scrape each Rollout Pod independently, so the canary's actual response errors are the data that drive the SLO gate. A controlled client sends requests directly to the faulty canary during a bounded test window.

Once two Prometheus SLO samples exceed policy thresholds, InfraGuard checks the active Rollout generation and UID, records an authorization event, and requests a lab-only abort through the status subresource using a least-privilege impersonated ServiceAccount. The test then verifies the stable revision can still serve traffic and publishes the results and audit artifact.

This is stronger than previous tests which used separate fault-lab traffic to trigger an unrelated canary. It still does **not** replicate real TCP connection exhaustion or establish a production availability/recovery SLO. The controller is a read-only monitor plus explicit remediation action; it is not a production-safe autonomous operator.
