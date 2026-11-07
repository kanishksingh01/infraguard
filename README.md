# InfraGuard

**Infrastructure-first Kubernetes rollout safety project.** Independent engineering study; not affiliated with OpenAI.

## P0: connection-storm lab (runnable)

A deliberately minimal local simulation of a dangerous rollout: the gateway normally performs **one** backend call per request. A faulty configuration increases that to **eight** parallel backend calls, exhausting a bounded backend concurrency pool. This gives us a reproducible latency/error-rate regression before writing any Kubernetes controller.

**Requirements:** Python 3.10+; no external Python packages, accounts, cloud credentials, or paid services.

```bash
python3 -m lab.server
# In a second terminal:
python3 -m lab.load_test --requests 120 --concurrency 12 --output baseline.json
curl -X POST 'http://127.0.0.1:8088/admin/fanout?value=8'
python3 -m lab.load_test --requests 120 --concurrency 12 --output storm.json
curl -s http://127.0.0.1:8088/metrics
curl -X POST 'http://127.0.0.1:8088/admin/fanout?value=1'
python3 -m unittest discover -s tests -v
```

The server binds **127.0.0.1 only**. The admin endpoint is intentionally unauthenticated for a local fault-injection lab and **must not** be exposed publicly. Do not run it in a shared or production cluster.

### What we record
- Success/error ratio, latency distribution (p50/p95/p99), gateway requests and backend attempts.
- Active/peak backend concurrency, rejected backend attempts, and fanout configuration.
- A baseline-to-fault comparison (results are experimental, not claimed until measured).

### Roadmap
- **P0:** Local reproducible failure lab; test and benchmark the incident class.
- **P1:** Implement read-only Kubernetes/Argo Rollouts observation and Prometheus-backed SLO gate.
- **P2:** Safe dry-run decision, opt-in rollback, strict RBAC, audit logs.
- **P3:** Reproducible comparative benchmarks and documentation.
- **Later:** AI-assisted investigation; not part of the initial implementation.

See [P0 tracking issue](https://github.com/kanishksingh01/infraguard/issues/1) and [architecture blueprint](https://github.com/kanishksingh01/infraguard/issues/6).

## Safety and provenance
Use synthetic workloads and independent code. Never copy employer data, internal runbooks, or company secrets. All future cluster-affecting functionality defaults to dry-run.
