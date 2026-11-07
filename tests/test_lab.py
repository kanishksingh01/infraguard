import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from lab.server import LabState, make_handler
from lab.load_test import percentile, run

class LabTests(unittest.TestCase):
    def test_fanout_validation(self):
        state = LabState()
        with self.assertRaises(ValueError):
            state.configure(0)
        with self.assertRaises(ValueError):
            state.configure(9)
        state.configure(4)
        self.assertEqual(state.snapshot()["fanout"], 4)

    def test_capacity_rejection_counter(self):
        state = LabState(capacity=1)
        state.active = 1
        self.assertFalse(state.backend_work())
        self.assertEqual(state.snapshot()["backend_rejected"], 1)

    def test_percentile(self):
        self.assertEqual(percentile([1, 2, 3, 4], 95), 4)
        self.assertIsNone(percentile([], 95))

    def test_http_end_to_end(self):
        state = LabState(capacity=8)
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            baseline = run(base + "/request", requests=5, concurrency=1)
            self.assertEqual(baseline["successful"], 5)
            with urlopen(Request(base + "/admin/fanout?value=3", method="POST")) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(state.snapshot()["fanout"], 3)
            self.assertEqual(run(base + "/request", 2, 1)["successful"], 2)
            self.assertEqual(state.snapshot()["backend_attempts"], 11)
            with self.assertRaises(HTTPError) as context:
                urlopen(Request(base + "/admin/fanout?value=99", method="POST"))
            self.assertEqual(context.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()
