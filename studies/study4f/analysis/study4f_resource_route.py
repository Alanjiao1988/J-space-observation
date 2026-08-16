"""Study 4F unquantized resource-route proof.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Section 4 requires that, **before weight acquisition**, one accelerator is
proven able to hold the 32B checkpoint, the maximum registered KV cache and a
fixed safety reserve without offloading. If that route is unavailable the pilot
must not quantize and must not silently shard; it stops with
``STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE``.

This module performs only the proof. It constructs no model, acquires no
weights, draws no seed and reads no logit.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Dict, List, Optional

UNAVAILABLE_STATE = "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE"

#: Registered parameter counts, in units of 10^9 parameters.
CHECKPOINT_PARAMETERS: Dict[str, float] = {
    "RT": 1.5,
    "RP_B1": 7.0,
    "RP_B2": 14.0,
    "RP_B3": 32.0,
}

#: bfloat16, so two bytes per parameter. Quantization is prohibited.
BYTES_PER_PARAMETER = 2

#: Maximum registered generated tokens on the CoT route, plus the prompt
#: allowance used to bound the KV cache.
MAX_NEW_TOKENS = 4096
PROMPT_TOKEN_ALLOWANCE = 512
MAX_REGISTERED_CONTEXT = MAX_NEW_TOKENS + PROMPT_TOKEN_ALLOWANCE

#: DeepSeek-R1-Distill-Qwen-32B: 64 layers, 8 key/value heads, head dim 128.
RP_B3_LAYERS = 64
RP_B3_KV_HEADS = 8
RP_B3_HEAD_DIM = 128

#: Fixed safety reserve, in bytes.
SAFETY_RESERVE_BYTES = 4 * 1024 ** 3


def weight_bytes(role: str) -> int:
    """Unquantized bfloat16 weight footprint of a registered checkpoint."""
    if role not in CHECKPOINT_PARAMETERS:
        raise ValueError("unregistered checkpoint role: %r" % (role,))
    return int(CHECKPOINT_PARAMETERS[role] * 1e9) * BYTES_PER_PARAMETER


def kv_cache_bytes(batch_size: int = 1) -> int:
    """Maximum registered KV cache for RP_B3 at batch size 1.

    Two tensors (key and value), ``layers x kv_heads x head_dim`` elements per
    token, two bytes per element.
    """
    per_token = 2 * RP_B3_LAYERS * RP_B3_KV_HEADS * RP_B3_HEAD_DIM * \
        BYTES_PER_PARAMETER
    return per_token * MAX_REGISTERED_CONTEXT * batch_size


def required_bytes(role: str = "RP_B3") -> int:
    """Weights plus maximum registered KV cache plus the fixed safety reserve."""
    return weight_bytes(role) + kv_cache_bytes() + SAFETY_RESERVE_BYTES


def detect_accelerators() -> List[Dict[str, object]]:
    """Enumerate visible accelerators without constructing a model.

    Returns an empty list when no accelerator is visible. Importing ``torch``
    is a dependency probe, not a model construction: no checkpoint, weight file
    or tokenizer is touched here.
    """
    devices: List[Dict[str, object]] = []
    try:
        import torch  # noqa: WPS433 - dependency probe only
    except Exception:  # pragma: no cover - absent dependency is a valid answer
        return devices
    try:
        if torch.cuda.is_available():
            for index in range(torch.cuda.device_count()):
                properties = torch.cuda.get_device_properties(index)
                devices.append({
                    "backend": "cuda",
                    "index": index,
                    "name": properties.name,
                    "total_memory_bytes": int(properties.total_memory),
                })
    except Exception:  # pragma: no cover - a probe failure is not an accelerator
        pass
    try:
        backend = getattr(torch.backends, "mps", None)
        if backend is not None and backend.is_available():
            devices.append({"backend": "mps", "index": 0, "name": "mps",
                            "total_memory_bytes": 0})
    except Exception:  # pragma: no cover
        pass
    return devices


def _torch_build() -> Optional[str]:
    try:
        import torch
    except Exception:  # pragma: no cover
        return None
    return str(torch.__version__)


def prove_route(role: str = "RP_B3") -> Dict[str, object]:
    """Prove or refute the unquantized single-accelerator route.

    The proof is refuted -- never repaired -- when no accelerator is visible or
    when no single visible accelerator can hold the requirement. Quantization,
    CPU offload, disk offload and silent sharding are not fallbacks and are not
    attempted.
    """
    devices = detect_accelerators()
    requirement = required_bytes(role)
    qualifying = [device for device in devices
                  if int(device.get("total_memory_bytes", 0)) >= requirement]
    proof: Dict[str, object] = {
        "role": role,
        "weight_bytes": weight_bytes(role),
        "kv_cache_bytes": kv_cache_bytes(),
        "safety_reserve_bytes": SAFETY_RESERVE_BYTES,
        "required_bytes": requirement,
        "required_gib": round(requirement / 1024 ** 3, 3),
        "accelerators_visible": len(devices),
        "accelerators": devices,
        "qualifying_accelerators": len(qualifying),
        "quantization_attempted": False,
        "sharding_attempted": False,
        "cpu_or_disk_offload_attempted": False,
        "device_map_auto_used": False,
        "weight_files_acquired": 0,
        "model_constructions": 0,
        "torch_build": _torch_build(),
        "nvidia_smi_present": shutil.which("nvidia-smi") is not None,
        "platform": platform.platform(),
        "route_available": bool(qualifying),
        "state": None,
    }
    if not qualifying:
        proof["state"] = UNAVAILABLE_STATE
    return proof


def nvidia_smi_report() -> Optional[str]:
    """Raw ``nvidia-smi`` output, when the tool exists. Informational only."""
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv"],
            capture_output=True, text=True, check=False, timeout=60)
    except Exception:  # pragma: no cover
        return None
    return completed.stdout
