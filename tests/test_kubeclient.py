import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from guard.kubeclient import get_rollout_incluster
from guard.kubernetes import KubernetesError

DOC = {"kind": "Rollout", "metadata": {"name": "checkout", "namespace": "infraguard-lab",
       "generation": 1, "uid": "uid1"}, "spec": {"replicas": 1},
       "status": {"phase": "Healthy", "observedGeneration": 1, "readyReplicas": 1}}

class ApiTests(unittest.TestCase):
    def test_get_is_read_only_with_bearer_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            token = Path(temp) / "token"
            token.write_text("synthetic-test-token", encoding="utf-8")
            seen = []
            def opener(req, **kwargs):
                seen.append((req.get_method(), req.full_url, req.headers["Authorization"]))
                return io.BytesIO(json.dumps(DOC).encode())
            with patch("guard.kubeclient.ssl.create_default_context", return_value=object()):
                state = get_rollout_incluster("infraguard-lab", "checkout",
                                             token_file=str(token), ca_file="unused",
                                             host="kubernetes.default.svc", port=443,
                                             opener=opener)
            self.assertEqual(state.name, "checkout")
            self.assertEqual(seen[0][0], "GET")
            self.assertEqual(seen[0][2], "Bearer synthetic-test-token")
            self.assertIn("/namespaces/infraguard-lab/rollouts/checkout", seen[0][1])

    def test_missing_token_fails_closed(self):
        with self.assertRaises(KubernetesError):
            get_rollout_incluster("infraguard-lab", "checkout",
                                  token_file="/nonexistent-token", host="kubernetes.default.svc")

    def test_invalid_resource_name_blocks_request(self):
        with self.assertRaises(ValueError):
            get_rollout_incluster("lab;evil", "checkout", host="kubernetes.default.svc")

if __name__ == "__main__":
    unittest.main()
