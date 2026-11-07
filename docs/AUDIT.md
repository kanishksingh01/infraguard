# InfraGuard Kind-only remediation audit

When the opt-in CLI is invoked with `--execute --confirm ABORT:infraguard-lab/checkout`, it writes `abort_authorized` to an append-only local JSONL file **before** applying the guarded status patch. If the file cannot be written and fsynced, no patch is attempted. It records either `abort_patch_accepted` or `abort_refused_or_conflicted` after the Kubernetes API response. The default file is `infraguard-audit.jsonl`, overrideable with `--audit-file`.

The Argo/Prometheus CI test writes `argo-abort-audit.jsonl` and `argo-metrics-report.json` and uploads both as a GitHub Actions artifact named `infraguard-argo-evidence`.

These records are **not immutable**, tamper-evident, remotely retained, or a suitable compliance audit. Production-grade authorization, independent storage, alerting, and preflight / finalization failure recovery are unimplemented. CI uses a disposable Kind cluster and synthetic traffic.
