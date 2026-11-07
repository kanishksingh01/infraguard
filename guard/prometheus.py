"""Read-only Prometheus instant-vector query client using the Python standard library."""
import json
import math
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

class PrometheusError(RuntimeError):
    pass

def fetch_scalar(base_url: str, query: str, timeout: float = 3) -> float:
    """Require a single numeric instant-vector series or scalar; reject ambiguous results."""
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username:
        raise ValueError("Prometheus URL must be an http(s) URL without embedded credentials")
    url = base_url.rstrip("/") + "/api/v1/query?" + urlencode({"query": query})
    try:
        with urlopen(url, timeout=timeout) as response:
            document = json.load(response)
    except (OSError, ValueError, TimeoutError) as exc:
        raise PrometheusError(f"query failed: {type(exc).__name__}") from exc
    if document.get("status") != "success":
        raise PrometheusError("query did not succeed")
    payload = document.get("data", {})
    kind = payload.get("resultType")
    if kind == "scalar":
        item = payload.get("result")
        if not isinstance(item, list) or len(item) != 2:
            raise PrometheusError("invalid scalar payload")
        raw = item[1]
    elif kind == "vector":
        items = payload.get("result")
        if not isinstance(items, list) or len(items) != 1:
            raise PrometheusError("expected exactly one timeseries")
        raw = items[0].get("value", [None, None])[1]
    else:
        raise PrometheusError("expected a scalar or instant vector")
    try:
        result = float(raw)
    except (TypeError, ValueError) as exc:
        raise PrometheusError("non-numeric sample") from exc
    if not math.isfinite(result):
        raise PrometheusError("non-finite sample")
    return result
