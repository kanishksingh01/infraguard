"""Run the baseline and simulated faulty-rollout scenarios in one process."""
import argparse
import json
import threading
from http.server import ThreadingHTTPServer
from lab.load_test import run
from lab.server import LabState, make_handler

def experiment(requests=120, concurrency=12, capacity=8):
    state = LabState(capacity=capacity)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/request"
    try:
        state.configure(1)
        baseline = run(url, requests, concurrency)
        before = state.snapshot()
        state.configure(8)
        faulty = run(url, requests, concurrency)
        after = state.snapshot()
        return {
            "setup": {"requests_per_scenario": requests,
                      "client_concurrency": concurrency,
                      "backend_capacity": capacity},
            "baseline": baseline,
            "faulty_rollout": faulty,
            "attempts_per_gateway_request": {
                "baseline": round(before["backend_attempts"] / max(before["gateway_requests"], 1), 2),
                "faulty_rollout": round(
                    (after["backend_attempts"] - before["backend_attempts"]) /
                    max(after["gateway_requests"] - before["gateway_requests"], 1), 2)},
            "rejected_backend_attempts": {
                "baseline": before["backend_rejected"],
                "faulty_rollout": after["backend_rejected"] - before["backend_rejected"]},
            "interpretation": "synthetic local concurrency-pool exhaustion; not actual TCP socket exhaustion"
        }
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)

def main():
    parser = argparse.ArgumentParser(description="InfraGuard P0 baseline vs faulty rollout")
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--capacity", type=int, default=8)
    parser.add_argument("--output", default="experiment-report.json")
    args = parser.parse_args()
    if min(args.requests, args.concurrency, args.capacity) < 1:
        parser.error("requests, concurrency and capacity must be >= 1")
    report = experiment(args.requests, args.concurrency, args.capacity)
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    with open(args.output, "w", encoding="utf-8") as file:
        file.write(rendered)

if __name__ == "__main__":
    main()
