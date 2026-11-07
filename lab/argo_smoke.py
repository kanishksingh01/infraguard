"""Test the real Argo Rollouts status-subresource abort on disposable Kind."""
import json
import subprocess
import time
from guard.remediation import LAB_CONTEXT, LAB_NAMESPACE, abort_with_preconditions, read_raw_rollout

NAME = "checkout"

def kubectl(*args):
    result = subprocess.run(["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
                             *args, "--request-timeout=5s"], text=True, capture_output=True,
                            timeout=12, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl {args[0]} failed (exit={result.returncode}): {result.stderr[-400:]}")
    return result.stdout

def wait_for(check, label, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            doc, state = read_raw_rollout(NAME)
            if check(doc, state):
                return doc, state
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Rollout did not reach {label} state in {timeout}s")

def main():
    # Initial rollout must converge before simulating a new canary.
    wait_for(lambda doc, state: state.phase == "Healthy" and not state.reconciling
             and state.ready_replicas == state.desired_replicas, "healthy")

    patch = json.dumps({"spec": {"template": {"metadata": {
        "annotations": {"infraguard.dev/revision": "v2"}}}}})
    kubectl("patch", "rollouts.argoproj.io", NAME, "--type=merge", "--patch", patch)

    doc, state = wait_for(
        lambda doc, state: not state.reconciling and state.phase in ("Progressing", "Paused")
          and bool((doc.get("status") or {}).get("pauseConditions")),
        "paused canary")

    # This is synthetic lab evidence to exercise ONLY the CAS-protected remediation path.
    # It must not be confused with a live Prometheus SLO decision.
    evidence = {"decision": "ABORT_RECOMMENDED", "action_executed": False,
                "rollout": state.as_dict()}
    result = abort_with_preconditions(NAME, evidence, approved=True)
    if not result["action_executed"]:
        raise AssertionError("abort status patch was not applied")

    def aborted(doc, state):
        status = doc.get("status") or {}
        return bool(status.get("abort")) or state.phase == "Degraded"

    last, final = wait_for(aborted, "aborted/degraded")
    print(json.dumps({"action": result, "rollout_phase": final.phase,
                      "abort_status": (last.get("status") or {}).get("abort"),
                      "note": "synthetic approval evidence, Kind only"}, indent=2))
    print("SUCCESS: real Argo Rollouts abort was observed within disposable Kind")

if __name__ == "__main__":
    main()
