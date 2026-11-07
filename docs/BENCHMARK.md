# Synthetic Kind failure and recovery benchmark

`Kind Integration` runs isolated, synthetic traffic through a real Kubernetes Service.

The report artifact `infraguard-kind-report` includes UTC measurement time, baseline and faulty-rollout error rates and latency percentiles, backend attempt/rejection counts, and post-reset recovery-probe results.

The reset is manually commanded by the test harness. `manual_reset_probe_seconds` is the wall-clock duration of reset plus verification requests, **not** an autonomous rollout recovery time or an incident MTTR metric.

These results are workload-specific and must be compared across repeated runs before making performance claims. They are not derived from any company's production environment.
