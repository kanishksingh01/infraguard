"""Read-only Kubernetes Rollout API client using in-cluster ServiceAccount auth.

Only GET is supported. Never sends a write request or supplies kubeconfig.
"""
import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from guard.kubernetes import KubernetesError, parse_rollout, validate_name

TOKEN_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

def get_rollout_incluster(namespace, name, *, token_file=TOKEN_FILE,
                          ca_file=CA_FILE, host=None, port=None, opener=urlopen):
    validate_name(namespace, "namespace")
    validate_name(name, "name")
    host = host or os.environ.get("KUBERNETES_SERVICE_HOST")
    raw_port = port or os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    if not isinstance(host, str) or not host or any(c in host for c in "/@?# "):
        raise KubernetesError("invalid Kubernetes API service host")
    try:
        number = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise KubernetesError("invalid Kubernetes API port") from exc
    if not 1 <= number <= 65535:
        raise KubernetesError("invalid Kubernetes API port")
    try:
        with open(token_file, encoding="utf-8") as f:
            token = f.read().strip()
        if not token:
            raise KubernetesError("empty ServiceAccount token")
        context = ssl.create_default_context(cafile=ca_file)
    except OSError as exc:
        raise KubernetesError("ServiceAccount credentials unavailable") from exc
    url = f"https://{host}:{number}/apis/argoproj.io/v1alpha1/namespaces/{namespace}/rollouts/{name}"
    request = Request(url, headers={"Authorization": "Bearer " + token,
                                    "Accept": "application/json"}, method="GET")
    try:
        with opener(request, timeout=5, context=context) as resp:
            data = json.load(resp)
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        raise KubernetesError("read-only Kubernetes API GET failed") from exc
    try:
        state = parse_rollout(data)
    except (ValueError, TypeError, KubernetesError) as exc:
        raise KubernetesError("invalid Rollout API document") from exc
    if state.name != name or state.namespace != namespace:
        raise KubernetesError("Rollout identity mismatch")
    return state
