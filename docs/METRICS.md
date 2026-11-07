# Prometheus telemetry for the isolated lab

The simulator exposes:
- `GET /metrics`: JSON snapshot for human debugging (existing endpoint).
- `GET /prometheus`: Prometheus exposition counters and gauges.

Counters: `infraguard_gateway_requests_total`, `infraguard_gateway_success_total`, `infraguard_gateway_errors_total`, `infraguard_backend_attempts_total`, `infraguard_backend_rejected_total`.

Gauges: `infraguard_backend_active`, `infraguard_backend_peak_active`, `infraguard_backend_capacity`, `infraguard_fanout`.

For a disposable Kind cluster, first deploy `deploy/lab.yaml`, then deploy `deploy/prometheus.yaml`. Access Prometheus only through a local port-forward. Example policy: `examples/lab-policy.json`. The metrics endpoint is test-only; do not expose the unauthenticated fault toggle publicly.

Prometheus rate windows require adequate samples; a missing or empty result must cause HOLD in the SLO gate. Gateway p99 latency is measured by the external load generator in P0; a service-side latency histogram is not implemented yet.
