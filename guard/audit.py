"""Minimal local audit record sink for disposable Kind remediation.

Every record is newline-delimited JSON and fsynced before returning. This
provides lab traceability, not a tamper-proof enterprise audit system.
"""
import json
import os
import stat
from datetime import datetime, timezone

class AuditError(RuntimeError):
    pass

def append_event(path, action, rollout, uid, resource_version):
    if not isinstance(path, str) or not path:
        raise AuditError("audit path is required")
    record = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "context": "kind-infraguard",
        "namespace": "infraguard-lab",
        "rollout": rollout,
        "uid": uid,
        "resource_version": resource_version,
    }
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise AuditError("audit target must be a regular file")
            written = os.write(fd, payload)
            if written != len(payload):
                raise AuditError("incomplete audit write")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise AuditError("audit record could not be persisted") from exc
    return record
