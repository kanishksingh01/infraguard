"""Integration: real Kind Argo Rollout with synthetic Prometheus evidence."""
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from guard.observe import observe
from guard.remediation import LAB_CONTEXT, LAB_NAMESPACE, abort_with_preconditions, read_raw_rollout

NAME = "checkout"

class SyntheticPrometheus(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith("/api/v1/query?"):
            self.send_error(404)
            return
        payload = json.dumps({"status": "success", "data": {
            "resultType": "vector", "result": [
                {"metric": {}, "value": [int(time.time()), "0.20"]}]
        }}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass

def kubectl(*args):
    result = subprocess.run(
        ["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
         *args, "--request-timeout=5s"], text=True, capture_output=True,
        timeout=12, check=False)
    if result.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {result.stderr[-400:]}")
    return result.stdout

def wait_for(predicate, label, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            doc, state = read_raw_rollout(NAME)
            if predicate(doc, state):
                return doc, state
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Rollout did not become {label} within {timeout}s")

def main():
    wait_for(lambda doc, s: s.phase == "Healthy" and not s.reconciling
             and s.ready_replicas == s.desired_replicas, "healthy")
    patch = json.dumps({"spec": {"template": {"metadata": {
        "annotations": {"infraguard.dev/revision": "v2"}}}}})
    kubectl("patch", "rollouts.argoproj.io", NAME, "--type=merge", "--patch", patch)
    wait_for(lambda doc, s: not s.reconciling and s.phase in ("Progressing", "Paused")
             and bool((doc.get("status") or {}).get("pauseConditions")), "paused canary")

    fake = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticPrometheus)
    worker = threading.Thread(target=fake.serve_forever, daemon=True)
    worker.start()
    try:
        evidence = observe(
            LAB_NAMESPACE, NAME,
            f"http://127.0.0.1:{fake.server_address[1]}",
            "examples/lab-policy.json", samples=2, interval=0.1,
            context=LAB_CONTEXT)
    finally:
        fake.shutdown()
        fake.server_close()
        worker.join(timeout=2)

    if evidence["decision"] != "ABORT_RECOMMENDED":
        raise AssertionError(f"synthetic SLO gate did not recommend abort: {evidence}")
    result = abort_with_preconditions(NAME, evidence, approved=True)
    if not result["action_executed"]:
        raise AssertionError("expected successful lab abort")

    doc, state = wait_for(
        lambda d, s: bool((d.get("status") or {}).get("abort"))
        or s.phase == "Degraded", "aborted")
    print(json.dumps({
        "action": result, "phase": state.phase,
        "synthetic_slo_decision": evidence["decision"],
        "source": "mock Prometheus metrics, REAL disposable Kind Argo state"
    }, indent=2))
    print("SUCCESS: Kind Argo Rollout observed, evaluated and aborted")

if __name__ == "__main__":
    main()
