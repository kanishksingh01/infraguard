import unittest
from urllib.request import urlopen
import threading
from http.server import ThreadingHTTPServer
from lab.server import LabState, make_handler, prometheus_metrics

class MetricsTests(unittest.TestCase):
    def test_prometheus_metrics_are_numeric_and_labeled(self):
        text = prometheus_metrics(LabState().snapshot())
        self.assertIn("# TYPE infraguard_gateway_requests_total counter", text)
        self.assertIn("infraguard_gateway_requests_total 0", text)
        self.assertIn("infraguard_fanout 1", text)

    def test_prometheus_endpoint(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(LabState()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/prometheus"
            with urlopen(url) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("text/plain", response.headers["Content-Type"])
                self.assertIn(b"infraguard_backend_capacity", response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()
