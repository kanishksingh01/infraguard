import json
import os
import tempfile
import unittest
from unittest.mock import Mock
from guard.audit import append_event, AuditError
from guard.remediation import abort_with_preconditions, RemediationError
from guard.kubernetes import parse_rollout

def rollout():
    return {"kind": "Rollout", "metadata": {"name": "checkout", "namespace": "infraguard-lab",
            "uid": "uid1", "resourceVersion": "234", "generation": 2},
            "spec": {"replicas": 2},
            "status": {"phase": "Progressing", "observedGeneration": 2,
                       "readyReplicas": 1}}

class AuditTests(unittest.TestCase):
    def test_two_audit_records_for_successful_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "audit.jsonl")
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return Mock(returncode=0,
                            stdout=json.dumps(rollout()) if "get" in cmd else "{}")
            evidence = {"decision": "ABORT_RECOMMENDED", "action_executed": False,
                        "rollout": parse_rollout(rollout()).as_dict()}
            result = abort_with_preconditions("checkout", evidence, approved=True,
                                             run=runner, audit_path=path)
            self.assertTrue(result["action_executed"])
            with open(path, encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            self.assertEqual([r["action"] for r in records],
                             ["abort_authorized", "abort_patch_accepted"])
            self.assertEqual(records[0]["uid"], "uid1")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_audit_unavailable_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return Mock(returncode=0, stdout=json.dumps(rollout()))
            evidence = {"decision": "ABORT_RECOMMENDED", "action_executed": False,
                        "rollout": parse_rollout(rollout()).as_dict()}
            with self.assertRaisesRegex(RemediationError, "audit preflight"):
                abort_with_preconditions("checkout", evidence, approved=True,
                    run=runner, audit_path=os.path.join(folder, "missing", "audit.jsonl"))
            self.assertEqual(len(calls), 1)
            self.assertIn("get", calls[0])

    def test_nonregular_file_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(AuditError):
                append_event(folder, "test", "rollout", "uid", "rv")

if __name__ == "__main__":
    unittest.main()
