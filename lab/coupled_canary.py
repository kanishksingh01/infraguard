"""Real fault-bearing Argo canary -> Prometheus -> SLO -> guarded abort -> stable Service probe.

Runs ONLY against disposable kind-infraguard, infraguard-lab. Synthetic
connections/traffic; no real cloud account or production objects.
"""
import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen

from guard.cli import load_thresholds
from guard.observe import observe
from guard.prometheus import fetch_scalar, PrometheusError
from guard.remediation import (LAB_CONTEXT, LAB_NAMESPACE,
                               abort_with_preconditions, read_raw_rollout)
from lab.load_test import run

NAME = "checkout"
PROM = "http://127.0.0.1:19090"
CANARY = "http://127.0.0.1:18092"
STABLE = "http://127.0.0.1:18093"

def kube(*args):
    command = ["kubectl", "--context", LAB_CONTEXT, "-n", LAB_NAMESPACE,
               *args, "--request-timeout=5s"]
    result = subprocess.run(command, text=True, capture_output=True, timeout=12)
    if result.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {result.stderr[-400:]}")
    return result.stdout

def forward(resource, port):
    return subprocess.Popen(
        ["kubectl", "--context", LAB_CONTEXT, "-n", LAB_NAMESPACE,
         "port-forward", resource, f"{port}:8088" if port != 19090 else "19090:9090",
         "--address=127.0.0.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ready(url, timeout=35):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (OSError, URLError, TimeoutError):
            pass
        time.sleep(.4)
    raise TimeoutError(f"endpoint {url} not ready")

def pods():
    result = json.loads(kube("get", "pods", "-l", "app=infraguard-canary", "-o", "json"))
    return result.get("items", [])

def revision(pod):
    for c in (pod.get("spec") or {}).get("containers") or []:
        for entry in c.get("env") or []:
            if entry.get("name") == "INFRAGUARD_FANOUT":
                return entry.get("value")
    return None

def ready_revision_pods(value):
    return [pod for pod in pods() if revision(pod) == str(value)
            and any(c.get("type") == "Ready" and c.get("status") == "True"
                    for c in (pod.get("status") or {}).get("conditions") or [])]

def wait_for(predicate, label, timeout=120):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = predicate()
            if value:
                return value
        except (RuntimeError, ValueError):
            pass
        time.sleep(2)
    raise AssertionError(f"timed out waiting for {label}")

def rollout_state():
    return read_raw_rollout(NAME)

def load(stop, results):
    while not stop.is_set():
        try:
            results.append(run(CANARY + "/request", requests=32, concurrency=4))
        except (OSError, URLError, TimeoutError):
            stop.set()
            break
        stop.wait(.2)

def main():
    forwards = []
    thread = None
    stop = threading.Event()
    observations = []
    try:
        forwards.append(forward("service/infraguard-prometheus", 19090))
        ready(PROM + "/-/ready")
        wait_for(lambda: ((doc, s) if (s.phase == "Healthy"
                 and not s.reconciling and s.ready_replicas == s.desired_replicas)
                 else None) if (doc_s := rollout_state()) and
                 (doc := doc_s[0]) is not None and (s := doc_s[1]) is not None else None,
                 "initial healthy Rollout")
        forwards.append(forward("service/checkout-svc", 18093))
        ready(STABLE + "/health")
        baseline = run(STABLE + "/request", requests=24, concurrency=4)
        if baseline["failed"]:
            raise AssertionError(f"baseline not healthy: {baseline}")
        forwards[-1].terminate()
        forwards[-1].wait(timeout=5)
        forwards.pop()

        patch = json.dumps([{"op": "replace",
                             "path": "/spec/template/spec/containers/0/env/0/value",
                             "value": "8"}])
        kube("patch", "rollouts.argoproj.io", NAME, "--type=json", "--patch", patch)
        wait_for(lambda: True if (
            (s := rollout_state()[1]).phase in ("Progressing", "Paused")
            and not s.reconciling and s.paused) else None, "paused canary")
        bad = wait_for(lambda: ready_revision_pods(8), "ready faulty revision")[0]
        bad_name = bad["metadata"]["name"]
        forwards.append(forward("pod/" + bad_name, 18092))
        ready(CANARY + "/health")
        thread = threading.Thread(target=load, args=(stop, observations), daemon=True)
        thread.start()

        thresholds = load_thresholds("examples/canary-policy.json")
        deadline = time.monotonic() + 95
        samples = {}
        while time.monotonic() < deadline:
            try:
                samples = {t.name: fetch_scalar(PROM, t.query) for t in thresholds}
                if all(samples[t.name] > t.maximum for t in thresholds):
                    break
            except (PrometheusError, OSError, ValueError):
                pass
            time.sleep(3)
        else:
            raise AssertionError(f"canary's real Prometheus metrics did not breach: {samples}")

        evidence = observe(LAB_NAMESPACE, NAME, PROM, "examples/canary-policy.json",
                           samples=2, interval=5, context=LAB_CONTEXT)
        if evidence["decision"] != "ABORT_RECOMMENDED":
            raise AssertionError(f"no SLO abort recommendation: {evidence}")
        started = time.monotonic()
        outcome = abort_with_preconditions(
            NAME, evidence, approved=True, audit_path="coupled-abort-audit.jsonl")
        wait_for(lambda: True if (
            (s := rollout_state()[1]).phase == "Degraded") else None, "aborted Rollout")

        stop.set()
        thread.join(timeout=9)
        forwards[-1].terminate()
        forwards[-1].wait(timeout=5)
        forwards.pop()
        wait_for(lambda: True if (
            len(ready_revision_pods(8)) == 0 and len(ready_revision_pods(1)) >= 1
        ) else None, "healthy-only stable revision")
        forwards.append(forward("service/checkout-svc", 18093))
        ready(STABLE + "/health")
        recovered = run(STABLE + "/request", requests=24, concurrency=4)
        if recovered["failed"]:
            raise AssertionError(f"Service unavailable after canary abort: {recovered}")
        report = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_service": baseline,
            "faulty_canary_load_cycles": len(observations),
            "faulty_canary_failed_requests": sum(x["failed"] for x in observations),
            "faulty_canary_successful_requests": sum(x["successful"] for x in observations),
            "canary_prometheus_samples": samples,
            "slo_decision": evidence["decision"], "guarded_abort": outcome,
            "service_after_abort": recovered,
            "abort_to_stable_service_verification_seconds": round(time.monotonic()-started, 3),
            "fault_isolation": "faulty fanout configured on the Rollout's canary Pod",
            "scope": "synthetic backend capacity, real Kind/Argo/Prometheus; no production claims",
        }
        print(json.dumps(report, indent=2))
        with open("coupled-canary-report.json", "w", encoding="utf-8") as file:
            json.dump(report, file, indent=2)
    finally:
        stop.set()
        if thread:
            thread.join(timeout=9)
        for proc in forwards:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

if __name__ == "__main__":
    main()
