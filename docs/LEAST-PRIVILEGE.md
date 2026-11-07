# Laboratory least-privilege remediation identity

The Argo integration now applies `deploy/remediation-rbac.yaml` in disposable Kind. The abort adapter always uses Kubernetes API impersonation of `system:serviceaccount:infraguard-lab:infraguard-remediator` for both the immediately-preceding Rollout GET and the status-subresource patch.

The Role allows GET on `rollouts.argoproj.io` and GET/PATCH on `rollouts/status`. It does not grant parent Rollout PATCH or Deployment DELETE. CI checks allowed and denied permissions and the real abort test validates the status patch.

**Important:** Impersonation is available because the disposable Kind CI runner's kubeconfig is cluster-admin. The same command will fail for a real user who lacks impersonation privileges. This is an API-authorization test, not proof of an independently authenticated in-cluster ServiceAccount token workflow, hardened credential management, or production-safe authorization. No non-lab context/namespace is selectable by the remediation CLI.
