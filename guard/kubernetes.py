"""Read-only Kubernetes/Argo Rollouts observation via kubectl JSON output.

This is an external-command adapter (not a Kubernetes watch). The adapter
accepts only validated resource names and runs kubectl without a shell.
"""
import json
import re
import subprocess
from dataclasses import dataclass, asdict

DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")
# Individual resource names must follow Kubernetes DNS subdomain syntax.
def validate_name(value: str, label: str) -> str:
    if not isinstance(value, str) or len(value) > 253 or not DNS_LABEL.fullmatch(value):
        raise ValueError(f"invalid Kubernetes {label}")
    for part in value.split("."):
        if len(part) > 63 or not part or part.startswith("-") or part.endswith("-"):
            raise ValueError(f"invalid Kubernetes {label}")
    return value

class KubernetesError(RuntimeError):
    pass

@dataclass(frozen=True)
class RolloutState:
    name: str
    namespace: str
    generation: int
    observed_generation: int
    phase: str
    current_step_index: int | None
    ready_replicas: int
    desired_replicas: int
    paused: bool
    reconciling: bool
    uid: str | None = None

    def as_dict(self):
        return asdict(self)

def parse_rollout(document: dict) -> RolloutState:
    if not isinstance(document, dict) or document.get("kind") != "Rollout":
        raise KubernetesError("response is not an Argo Rollouts Rollout")
    metadata = document.get("metadata") or {}
    spec = document.get("spec") or {}
    status = document.get("status") or {}
    if not isinstance(metadata, dict) or not isinstance(spec, dict) or not isinstance(status, dict):
        raise KubernetesError("invalid Rollout document")
    name = validate_name(metadata.get("name"), "name")
    namespace = validate_name(metadata.get("namespace"), "namespace")
    try:
        generation = int(metadata.get("generation", 0))
        observed = int(status.get("observedGeneration", 0))
        desired = int(spec.get("replicas", 1))
        ready = int(status.get("readyReplicas", 0))
        raw_step = status.get("currentStepIndex")
        step = None if raw_step is None else int(raw_step)
    except (TypeError, ValueError) as exc:
        raise KubernetesError("invalid rollout replica or generation fields") from exc
    if min(generation, observed, desired, ready) < 0 or (step is not None and step < 0):
        raise KubernetesError("invalid negative rollout status")
    phase = str(status.get("phase", "Unknown"))
    # A missing / lagging observedGeneration is not a reliable up-to-date state.
    reconciling = observed < generation
    return RolloutState(
        name=name, namespace=namespace, generation=generation,
        observed_generation=observed, phase=phase,
        current_step_index=step, ready_replicas=ready, desired_replicas=desired,
        paused=bool(status.get("pauseConditions")) or bool(spec.get("paused", False)),
        reconciling=reconciling,
        uid=metadata.get("uid"),
    )

def get_rollout(namespace: str, name: str, *, kubectl: str = "kubectl", timeout: float = 8, context: str | None = None) -> RolloutState:
    validate_name(namespace, "namespace")
    validate_name(name, "name")
    if timeout <= 0 or timeout > 60:
        raise ValueError("timeout must be in (0,60] seconds")
    if context is not None:
        validate_name(context, "context")
    command = [kubectl]
    if context is not None:
        command += ["--context", context]
    command += ["--namespace", namespace, "get", "rollouts.argoproj.io",
                name, "-o", "json", "--request-timeout=5s"]
    try:
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KubernetesError(f"kubectl unavailable or timed out: {type(exc).__name__}") from exc
    if result.returncode != 0:
        raise KubernetesError(f"kubectl get rollout failed (exit {result.returncode})")
    try:
        state = parse_rollout(json.loads(result.stdout))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise KubernetesError("invalid rollout JSON") from exc
    if state.name != name or state.namespace != namespace:
        raise KubernetesError("rollout identity mismatch")
    return state

def combine_rollout_and_slo(rollout: RolloutState | None, slo: dict) -> dict:
    """Conservative gate: unknown/stale rollout data can never authorize passing."""
    if rollout is None:
        return {"decision": "HOLD", "reason": "rollout observation unavailable",
                "slo": slo, "rollout": None, "action_executed": False}
    if rollout.reconciling:
        decision, reason = "HOLD", "rollout status has not observed latest generation"
    elif rollout.phase in ("Progressing", "Paused"):
        decision, reason = slo["decision"], "active rollout evaluated against SLO"
    else:
        # Do not suggest aborting a completed or unknown rollout.
        decision, reason = "HOLD", f"rollout phase {rollout.phase!r} is not an active canary"
    return {"decision": decision, "reason": reason, "slo": slo,
            "rollout": rollout.as_dict(), "action_executed": False}
