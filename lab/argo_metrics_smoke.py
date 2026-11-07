"""Real Prometheus telemetry -> deterministic SLO gate -> real Kind Argo abort.

Restricted to disposable Kind; synthetic client traffic is deliberately generated
inside GitHub CI. No production targets, credentials or cloud resources.
"""
import json
import subprocess
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from guard.cli import load_thresholds
from guard.observe import observe
from guard.prometheus import fetch_scalar, PrometheusError
from guard.remediation import LAB_CONTEXT, LAB_NAMESPACE, read_raw_rollout, abort_with_preconditions
from lab.load_test import run

NAME = "checkout"
BASE = "http://127.0.0.1:18088"
PROM = "http://127.0.0.1:19090"

def kubectl(*args):
    cmd = ["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
           *args, "--request-timeout=5s"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
    if r.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {r.stderr[-400:]}")

def wait_for_rollout(check, description, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            doc, state = read_raw_rollout(NAME)
            if check(doc, state):
                return doc, state
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Rollout never became {description}")

def start_forward(service, local_port, remote_port):
    return subprocess.Popen(
        ["kubectl", "--context", LAB_CONTEXT, "--namespace", LAB_NAMESPACE,
         "port-forward", f"service/{service}", f"{local_port}:{remote_port}",
         "--address", "127.0.0.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ready(url, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except (OSError, URLError, TimeoutError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"service not ready: {url}")

def fanout(value):
    with urlopen(Request(BASE + f"/admin/fanout?value={value}", method="POST"),
                 timeout=3) as r:
        if r.status != 200:
            raise RuntimeError("fault configuration failed")

def generate_load(stop, observations):
    while not stop.is_set():
        observations.append(run(BASE + "/request", requests=32, concurrency=4))
        stop.wait(0.3)

def main():
    forwards = []
    worker = None
    stop = threading.Event()
    observations = []
    try:
        forwards.append(start_forward("infraguard-fault-lab", 18088, 8088))
        forwards.append(start_forward("infraguard-prometheus", 19090, 9090))
        ready(BASE + "/health")
        ready(PROM + "/-/ready")
        fanout(1)
        baseline = run(BASE + "/request", requests=24, concurrency=4)
        if baseline["failed"] != 0:
            raise AssertionError(f"baseline unhealthy: {baseline}")

        wait_for_rollout(lambda d, s: s.phase == "Healthy" and not s.reconciling
                         and s.ready_replicas == s.desired_replicas, "healthy")
        revision = json.dumps({"spec": {"template": {"metadata": {
            "annotations": {"infraguard.dev/revision": "v2"}}}}})
        kubectl("patch", "rollouts.argoproj.io", NAME, "--type=merge", "--patch", revision)
        wait_for_rollout(lambda d, s: not s.reconciling
                         and s.phase in ("Progressing", "Paused")
                         and bool((d.get("status") or {}).get("pauseConditions")),
                         "paused canary")

        fanout(8)
        worker = threading.Thread(target=generate_load, args=(stop, observations), daemon=True)
        worker.start()

        thresholds = load_thresholds("examples/lab-policy.json")
        # Keep generating traffic until Prometheus has *observed* sustained breaches.
        deadline = time.monotonic() + 90
        measurements = {}
        while time.monotonic() < deadline:
            try:
                measurements = {p.name: fetch_scalar(PROM, p.query) for p in thresholds}
                if all(measurements[p.name] > p.maximum for p in thresholds):
                    break
            except (PrometheusError, OSError, ValueError):
                pass
            time.sleep(3)
        else:
            raise AssertionError(f"real Prometheus did not observe SLO breach: {measurements}")

        evidence = observe(LAB_NAMESPACE, NAME, PROM, "examples/lab-policy.json",
                           samples=2, interval=5, context=LAB_CONTEXT)
        if evidence["decision"] != "ABORT_RECOMMENDED":
            raise AssertionError(f"unexpected SLO decision: {evidence}")
        outcome = abort_with_preconditions(NAME, evidence, approved=True)
        last, state = wait_for_rollout(
            lambda d, s: bool((d.get("status") or {}).get("abort"))
            or s.phase == "Degraded", "aborted")
        print(json.dumps({"baseline": baseline, "prometheus_samples": measurements,
                          "slo_decision": evidence["decision"],
                          "abort_outcome": outcome, "rollout_phase": state.phase,
                          "load_cycles": len(observations),
                          "metric_origin": "real Prometheus scrape of synthetic workload"},
                         indent=2))
    finally:
        stop.set()
        if worker:
            worker.join(timeout=8)
        try:
            fanout(1)
        except Exception:
            pass
        for process in forwards:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

if __name__ == "__main__":
    main()
