"""Local HTTP fault-injection lab. No Kubernetes access or external dependencies."""
import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

def prometheus_metrics(snapshot):
    """Expose counters and gauges via Prometheus text exposition format."""
    metrics = {
        "infraguard_gateway_requests_total": ("counter", snapshot["gateway_requests"]),
        "infraguard_gateway_success_total": ("counter", snapshot["gateway_success"]),
        "infraguard_gateway_errors_total": ("counter", snapshot["gateway_errors"]),
        "infraguard_backend_attempts_total": ("counter", snapshot["backend_attempts"]),
        "infraguard_backend_rejected_total": ("counter", snapshot["backend_rejected"]),
        "infraguard_backend_active": ("gauge", snapshot["active_backend"]),
        "infraguard_backend_peak_active": ("gauge", snapshot["peak_active_backend"]),
        "infraguard_backend_capacity": ("gauge", snapshot["capacity"]),
        "infraguard_fanout": ("gauge", snapshot["fanout"]),
    }
    lines = []
    for name, (kind, value) in metrics.items():
        lines.extend((f"# TYPE {name} {kind}", f"{name} {int(value)}"))
    return "\n".join(lines) + "\n"

MAX_FANOUT = 8
DEFAULT_CAPACITY = 8
BACKEND_DELAY_SECONDS = 0.025

class LabState:
    def __init__(self, capacity=DEFAULT_CAPACITY):
        self.lock = threading.Lock()
        self.fanout = 1
        self.capacity = capacity
        self.active = 0
        self.peak_active = 0
        self.requests = 0
        self.success = 0
        self.errors = 0
        self.attempts = 0
        self.rejected = 0

    def configure(self, value):
        if not 1 <= value <= MAX_FANOUT:
            raise ValueError("fanout must be 1..8")
        with self.lock:
            self.fanout = value

    def backend_work(self):
        with self.lock:
            self.attempts += 1
            if self.active >= self.capacity:
                self.rejected += 1
                return False
            self.active += 1
            self.peak_active = max(self.peak_active, self.active)
        try:
            time.sleep(BACKEND_DELAY_SECONDS)
            return True
        finally:
            with self.lock:
                self.active -= 1

    def request(self):
        with self.lock:
            self.requests += 1
            fanout = self.fanout
        with ThreadPoolExecutor(max_workers=fanout) as pool:
            results = list(pool.map(lambda _: self.backend_work(), range(fanout)))
        ok = all(results)
        with self.lock:
            if ok:
                self.success += 1
            else:
                self.errors += 1
        return ok

    def snapshot(self):
        with self.lock:
            return dict(fanout=self.fanout, capacity=self.capacity,
                        active_backend=self.active, peak_active_backend=self.peak_active,
                        gateway_requests=self.requests, gateway_success=self.success,
                        gateway_errors=self.errors, backend_attempts=self.attempts,
                        backend_rejected=self.rejected)

def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body):
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/request":
                ok = state.request()
                self.respond(200 if ok else 503, {"ok": ok})
            elif route == "/prometheus":
                payload = prometheus_metrics(state.snapshot()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            elif route in ("/metrics", "/health"):
                self.respond(200, state.snapshot())
            else:
                self.respond(404, {"error": "not found"})

        def do_POST(self):
            route = urlparse(self.path)
            if route.path != "/admin/fanout":
                return self.respond(404, {"error": "not found"})
            try:
                value = int(parse_qs(route.query)["value"][0])
                state.configure(value)
            except (KeyError, ValueError, IndexError) as exc:
                return self.respond(400, {"error": str(exc)})
            self.respond(200, {"fanout": value})

        def log_message(self, format, *args):
            pass  # Suppress per-request noise in benchmarks.
    return Handler

def main():
    parser = argparse.ArgumentParser(description="Local-only InfraGuard fault lab")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1",
                        help="0.0.0.0 is for isolated container labs ONLY")
    parser.add_argument("--capacity", type=int, default=DEFAULT_CAPACITY)
    args = parser.parse_args()
    if args.capacity < 1:
        parser.error("capacity must be >= 1")
    server = ThreadingHTTPServer((args.host, args.port),
                                make_handler(LabState(args.capacity)))
    print(f"InfraGuard lab listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
