# InfraGuard — Delivery and release gates

## Implemented and integration-tested
- Connection-fanout failure lab, Python tests, Docker image and disposable Kind Deployment.
- Prometheus counters and real PromQL-based consecutive-breach SLO gate.
- Real Argo Rollouts canary observation and explicit, lab-only abort.
- UID/resourceVersion checks, preflight audit records, namespace-restricted ServiceAccount impersonation, and negative RBAC checks.
- Repeatable synthetic fault-reset Kind reports and Argo audit evidence artifacts.

## Still required before claiming an end-to-end finished product
- [x] Couple fault generation to the actual Argo canary Pod and scrape its own Prometheus SLO evidence.
- [x] Verify healthy stable-Service responses after guarded abort: 24/24 requests in one synthetic Kind run.
- [ ] Repeat coupled experiments under varied load to quantify uncertainty in detection and recovery.
- Validate trusted identity, change approval, audit retention and authorization against realistic threat models.
- Compare results with native Argo Rollouts analysis and statistically robust repeated benchmarks.

## Latest coupled experiment
[Verified Kind/Argo/Prometheus recovery workflow](https://github.com/kanishksingh01/infraguard/actions/runs/42425398415): 754/800 faulty canary calls failed; Prometheus sampled 93.75% errors; the guarded abort succeeded; stable Service passed 24/24 requests after abort. Abort-to-stable-verification was 34.36 s in one synthetic trial, not a production MTTR guarantee.

## Current release classification
**Experimental lab prototype, not production-ready.** No production cluster mutations are supported. See [end-to-end walkthrough](END-TO-END.md).