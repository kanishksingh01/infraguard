"""Lab-only, opt-in Argo Rollouts abort with optimistic concurrency guards.

This is intentionally restricted to disposable Kind. No production execution
is allowed by this CLI regardless of current kubeconfig.
"""
import argparse
import json
import subprocess
import sys
from guard.kubernetes import parse_rollout, validate_name, KubernetesError
from guard.observe import observe
from guard.audit import append_event, AuditError

LAB_CONTEXT = "kind-infraguard"
LAB_NAMESPACE = "infraguard-lab"

class RemediationError(RuntimeError):
    pass

def read_raw_rollout(name, run=subprocess.run):
    validate_name(name, "name")
    cmd = ["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
           "get", "rollouts.argoproj.io", name, "-o", "json", "--request-timeout=5s"]
    try:
        result = run(cmd, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RemediationError("rollout observation failed") from exc
    if result.returncode:
        raise RemediationError("unable to retrieve rollout in disposable lab")
    try:
        data = json.loads(result.stdout)
        state = parse_rollout(data)
    except (TypeError, ValueError, json.JSONDecodeError, KubernetesError) as exc:
        raise RemediationError("invalid rollout response") from exc
    if state.name != name or state.namespace != LAB_NAMESPACE:
        raise RemediationError("rollout identity mismatch")
    return data, state

def abort_with_preconditions(name, evidence, *, approved=False, run=subprocess.run, audit_path=None):
    """Opt-in abort using JSON Patch TEST operations for atomic CAS on status.

    Fails closed on any missing metadata, mismatched generation or unsafe phase.
    The caller must have already performed two consecutive *fresh* SLO checks.
    """
    if not approved:
        raise RemediationError("explicit approval required")
    if not isinstance(evidence, dict) or evidence.get("decision") != "ABORT_RECOMMENDED":
        raise RemediationError("fresh SLO evidence does not justify abort")
    if evidence.get("action_executed") is not False:
        raise RemediationError("invalid decision evidence")
    original = evidence.get("rollout")
    if not isinstance(original, dict):
        raise RemediationError("missing rollout evidence")
    document, state = read_raw_rollout(name, run=run)
    for field in ("name", "namespace", "generation", "uid"):
        if original.get(field) != getattr(state, field):
            raise RemediationError("rollout changed since SLO evaluation")
    if state.phase not in ("Progressing", "Paused") or state.reconciling:
        raise RemediationError("rollout is not an active, observed canary")
    metadata = document.get("metadata") or {}
    uid = metadata.get("uid")
    rv = metadata.get("resourceVersion")
    if not isinstance(uid, str) or not uid or not isinstance(rv, str) or not rv:
        raise RemediationError("missing Kubernetes optimistic-concurrency metadata")
    # Required audit preflight: refuse a write if the audit sink is inaccessible.
    if audit_path is not None:
        try:
            append_event(audit_path, "abort_authorized", name, uid, rv)
        except AuditError as exc:
            raise RemediationError("audit preflight failed; no mutation attempted") from exc
    # A single API patch atomically tests identity + version before changing status.
    patch = [
        {"op": "test", "path": "/metadata/uid", "value": uid},
        {"op": "test", "path": "/metadata/resourceVersion", "value": rv},
        {"op": "add", "path": "/status/abort", "value": True},
    ]
    command = ["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
               "patch", "rollouts.argoproj.io", name, "--subresource=status",
               "--type=json", "--patch", json.dumps(patch, separators=(",", ":")),
               "--request-timeout=5s"]
    try:
        result = run(command, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RemediationError("abort patch transport error; verify actual status") from exc
    if result.returncode:
        if audit_path is not None:
            append_event(audit_path, "abort_refused_or_conflicted", name, uid, rv)
        raise RemediationError("abort refused or conflicted; re-evaluate before retrying")
    if audit_path is not None:
        try:
            append_event(audit_path, "abort_patch_accepted", name, uid, rv)
        except AuditError as exc:
            raise RemediationError("abort may have executed; audit finalization failed: verify status") from exc
    return {"action": "abort", "cluster_context": LAB_CONTEXT,
            "namespace": LAB_NAMESPACE, "name": name, "generation": state.generation,
            "action_executed": True, "resource_version_before": rv}

def main():
    parser = argparse.ArgumentParser(description="Lab-only guarded Argo Rollouts abort")
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--prometheus", required=True)
    parser.add_argument("--policy", default="examples/lab-policy.json")
    parser.add_argument("--execute", action="store_true", help="Allow a lab-only mutation")
    parser.add_argument("--audit-file", default="infraguard-audit.jsonl", help="Local, append-only JSONL audit")
    parser.add_argument("--confirm", default="", help="Must equal ABORT:infraguard-lab/<name>")
    args = parser.parse_args()
    try:
        validate_name(args.rollout, "name")
        # Read fresh metrics from the target on *this invocation*. No stored report accepted.
        evidence = observe(LAB_NAMESPACE, args.rollout, args.prometheus,
                           args.policy, samples=2, interval=10,
                           kubectl="kubectl", context=LAB_CONTEXT)
        if not args.execute:
            print(json.dumps({"execution": "disabled", "decision": evidence["decision"]}))
            return 2 if evidence["decision"] == "ABORT_RECOMMENDED" else 3
        if args.confirm != f"ABORT:{LAB_NAMESPACE}/{args.rollout}":
            raise RemediationError("confirmation phrase does not match lab target")
        outcome = abort_with_preconditions(args.rollout, evidence, approved=True,
                                           audit_path=args.audit_file)
        print(json.dumps(outcome))
        return 0
    except (RemediationError, AuditError, ValueError, OSError) as exc:
        print(json.dumps({"action_executed": False, "error": str(exc)}), file=sys.stderr)
        return 4

if __name__ == "__main__":
    sys.exit(main())
