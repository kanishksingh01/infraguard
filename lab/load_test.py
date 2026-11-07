"""Dependency-free load generator for the InfraGuard local fault lab."""
import argparse
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

def percentile(values, p):
    if not values:
        return None
    sorted_values = sorted(values)
    rank = max(0, math.ceil(p / 100 * len(values)) - 1)
    return round(sorted_values[rank], 2)

def run(url, requests, concurrency, timeout=5):
    def one(_):
        started = time.perf_counter()
        try:
            with urlopen(url, timeout=timeout) as response:
                code = response.status
        except HTTPError as exc:
            code = exc.code
        except (URLError, TimeoutError, OSError):
            code = 0
        return code, (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        observations = [f.result() for f in as_completed(
            [pool.submit(one, i) for i in range(requests)])]
    latencies = [duration for _, duration in observations]
    successes = sum(1 for code, _ in observations if 200 <= code < 300)
    return {"requests": requests, "concurrency": concurrency,
            "successful": successes, "failed": requests - successes,
            "error_ratio": round((requests - successes) / requests, 4),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "p50_ms": percentile(latencies, 50), "p95_ms": percentile(latencies, 95),
            "p99_ms": percentile(latencies, 99)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8088/request")
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests and concurrency must be >= 1")
    report = run(args.url, args.requests, args.concurrency)
    output = json.dumps(report, indent=2) + "\n"
    print(output, end="")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)

if __name__ == "__main__":
    main()
