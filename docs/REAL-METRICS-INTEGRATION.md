# Real Prometheus telemetry integration in ephemeral Kind

The `Argo Rollouts Integration` CI workflow installs Argo Rollouts and Prometheus, runs real synthetic client traffic against a containerized Kubernetes Service, waits until Prometheus observes degraded backend metrics, combines two successive SLO breaches with a live canary observation, and applies the guarded status patch in the isolated lab.

**Real components:** Kubernetes, Argo Rollouts v1.10.2, Prometheus scraping, SLO queries, authenticated local port-forwards, and Kubernetes API patching.

**Synthetic:** Workload, injected fanout regression and client traffic. This does not prove anything about OpenAI's or another company's infrastructure.

The lab expects `infraguard_gateway_errors_total` and `infraguard_backend_rejected_total` to increase during a bounded concurrency-pool storm; both must exceed thresholds in `examples/lab-policy.json`.

Automatic production rollback, realistic external dependency saturation, and recovery-SLO proof remain out of scope. CI explicitly grants approval only for the disposable Kind test.
