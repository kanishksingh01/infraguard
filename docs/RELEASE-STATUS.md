# InfraGuard — Delivery and release gates

## Implemented and integration-tested
- Connection-fanout failure lab, Python tests, Docker image and disposable Kind Deployment.
- Prometheus counters and real PromQL-based consecutive-breach SLO gate.
- Real Argo Rollouts canary observation and explicit, lab-only abort.
- UID/resourceVersion checks, preflight audit records, namespace-restricted ServiceAccount impersonation, and negative RBAC checks.
- Repeatable synthetic fault-reset Kind reports and Argo audit evidence artifacts.

## Still required before claiming an end-to-end finished product
- Couple the *bad canary's own traffic* to the very SLO metrics used by the abort decision; currently fault lab and canary deployment are distinct components in the test.
- Prove post-abort **application availability restoration** (not merely a Degraded rollout phase).
- Validate trusted identity, change approval, audit retention and authorization against realistic threat models.
- Compare results with native Argo Rollouts analysis and statistically robust repeated benchmarks.

## Current release classification
**Experimental lab prototype, not production-ready.** No production cluster mutations are supported. See [end-to-end walkthrough](END-TO-END.md).