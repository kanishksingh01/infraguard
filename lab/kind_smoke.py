"""End-to-end verification against fault lab deployed inside a Kind cluster."""
import argparse
import json
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError
from lab.load_test import run

def get_json(url):
    with urlopen(url, timeout=3) as response:
        return json.load(response)

def set_fanout(base_url, fanout):
    with urlopen(Request(base_url + f"/admin/fanout?value={fanout}", method="POST"), timeout=3) as response:
        if response.status != 200:
            raise AssertionError(f"unexpected admin status {response.status}")

def ready(base_url, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if get_json(base_url + "/health")["capacity"] >= 1:
                return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.25)
    raise RuntimeError("port-forward health check did not become ready")

def smoke(base_url, requests=40, concurrency=4):
    ready(base_url)
    try:
        set_fanout(base_url, 1)
        baseline = run(base_url + "/request", requests, concurrency)
        baseline_metrics = get_json(base_url + "/metrics")
        set_fanout(base_url, 8)
        fault = run(base_url + "/request", requests, concurrency)
        fault_metrics = get_json(base_url + "/metrics")
        with urlopen(base_url + "/prometheus", timeout=3) as response:
            exposition = response.read().decode("utf-8")
        report = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "baseline": baseline, "fault": fault,
            "new_backend_rejections": (
                fault_metrics["backend_rejected"] - baseline_metrics["backend_rejected"]),
            "new_backend_attempts": (
                fault_metrics["backend_attempts"] - baseline_metrics["backend_attempts"]),
        }
        if baseline["failed"] != 0:
            raise AssertionError("baseline contains failed requests; lab is not isolated enough")
        if report["new_backend_attempts"] != requests * 8:
            raise AssertionError("fault configuration did not amplify backend calls by 8")
        if report["new_backend_rejections"] <= 0 or fault["failed"] <= 0:
            raise AssertionError("fault injection did not produce observable backend saturation")
        if "# TYPE infraguard_gateway_errors_total counter\n" not in exposition:
            raise AssertionError("Prometheus exposition is malformed or absent")
        restored_at = time.perf_counter()
        set_fanout(base_url, 1)
        restored = run(base_url + "/request", max(8, concurrency * 2), concurrency)
        report["post_reset_probe"] = restored
        report["manual_reset_probe_seconds"] = round(time.perf_counter() - restored_at, 4)
        if restored["failed"] != 0:
            raise AssertionError("service did not recover after manual fanout reset")
        print(json.dumps(report, indent=2))
        return report
    finally:
        set_fanout(base_url, 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18088")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", default="kind-report.json")
    args = parser.parse_args()
    if args.requests < 1 or not 1 <= args.concurrency <= 8:
        parser.error("requests must be positive and concurrency must be 1..8")
    report = smoke(args.url.rstrip("/"), args.requests, args.concurrency)
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

if __name__ == "__main__":
    main()
