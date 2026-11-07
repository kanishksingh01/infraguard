import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from guard.policy import Evaluator, Threshold
from guard.prometheus import fetch_scalar, PrometheusError

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = Evaluator([Threshold("errors", "rate(errors[2m])", 0.05, 2)])

    def test_sustained_breach_requires_two_evaluations(self):
        self.assertEqual(self.evaluator.evaluate({"errors": .12})["decision"], "HOLD")
        output = self.evaluator.evaluate({"errors": .13})
        self.assertEqual(output["decision"], "ABORT_RECOMMENDED")
        self.assertTrue(output["dry_run"])
        self.assertFalse(output["action_executed"])

    def test_single_spike_resets(self):
        self.evaluator.evaluate({"errors": .12})
        self.assertEqual(self.evaluator.evaluate({"errors": .01})["decision"], "PASS")
        self.assertEqual(self.evaluator.evaluate({"errors": .12})["decision"], "HOLD")

    def test_missing_metrics_holds(self):
        self.assertEqual(self.evaluator.evaluate({})["decision"], "HOLD")
        self.assertEqual(self.evaluator.evaluate({"errors": float("nan")})["decision"], "HOLD")

    def test_policy_validation(self):
        with self.assertRaises(ValueError):
            Threshold("test", "up", float("inf"))
        with self.assertRaises(ValueError):
            Evaluator([Threshold("x", "up", 1), Threshold("x", "other", 2)])

class PrometheusTests(unittest.TestCase):
    def test_query_vector_and_ambiguity(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                result = ([{"metric": {}, "value": [123, "0.12"]}]
                          if "good" in self.path else [])
                payload = json.dumps({"status": "success", "data":
                                      {"resultType": "vector", "result": result}}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):
                pass
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{srv.server_address[1]}"
            self.assertEqual(fetch_scalar(endpoint, "good"), .12)
            with self.assertRaises(PrometheusError):
                fetch_scalar(endpoint, "missing")
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()
