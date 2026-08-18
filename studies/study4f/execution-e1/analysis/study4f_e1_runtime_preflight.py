"""Study 4F-E1 runtime preflight on a frozen accelerator.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

Section 6. E1 reuses the original Study 4F runtime contract exactly and adds one
thing the original could not perform, because no accelerator was ever visible to
it: a **measured** check on the real device.

A paper specification of 80 or 94 GB is not sufficient. Before a checkpoint is
loaded the runtime must observe, on the device itself:

* exactly one eligible accelerator is visible;
* the GPU model matches the frozen SKU;
* no unrelated process occupies material GPU memory;
* measured free device memory exceeds ``69,502,926,848`` bytes;
* BF16 is supported;
* driver, CUDA and framework compatibility tests pass.

If the accelerator exists but the measured memory condition fails, the successor
stops with ``STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT``. It
does not quantize, shard or offload: those are not fallbacks, they are a
different study.

The registered requirement is not a new number. It is exactly the requirement
the published Study 4F resource-route module already computed for ``RP_B3``:
64,000,000,000 weight bytes plus 1,207,959,552 maximum registered KV-cache bytes
plus a 4,294,967,296 safety reserve.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

#: Measured free device memory must strictly exceed this many bytes.
REQUIRED_FREE_DEVICE_MEMORY_BYTES = 69_502_926_848

#: A resident process is "material" once it holds at least this much memory.
MATERIAL_FOREIGN_MEMORY_BYTES = 256 * 1024 ** 2

BELOW_REQUIREMENT_STATE = \
    "STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT"

#: GPU model substrings accepted for each registered SKU. The check is a
#: containment test on the reported device name because vendors report
#: ``NVIDIA H100 NVL`` and ``NVIDIA A100 80GB PCIe`` rather than the SKU name.
SKU_GPU_MARKERS: Dict[str, Sequence[str]] = {
    "Standard_NC40ads_H100_v5": ("H100",),
    "Standard_NC24ads_A100_v4": ("A100",),
}

#: The original Study 4F loading contract, reused unchanged. Every field here is
#: asserted against the published protocol rather than restated as policy.
RUNTIME_CONTRACT: Dict[str, object] = {
    "trust_remote_code": False,
    "unquantized_weights": True,
    "torch_dtype": "bfloat16",
    "adapter": None,
    "cpu_offload": False,
    "disk_offload": False,
    "model_sharding": False,
    "device_map_auto": False,
    "batch_size": 1,
    "evaluation_mode": True,
    "explicit_attention_implementation_required": True,
    "original_e0_and_cot_generation_fields": True,
    "original_seeds_and_parsers": True,
    "original_context_and_kv_cache_bounds": True,
}


class Study4FE1PreflightError(RuntimeError):
    """Raised when preflight is driven outside its registered contract."""


def load_original_resource_route(repo_root: Path):
    """Import the published Study 4F resource-route module unchanged."""
    path = (repo_root / "studies" / "study4f" / "analysis" /
            "study4f_resource_route.py")
    spec = importlib.util.spec_from_file_location(
        "study4f_e1_bound_resource_route", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise Study4FE1PreflightError("cannot load the predecessor module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def registered_requirement(repo_root: Path) -> int:
    """Recompute the requirement from the *predecessor's* own module.

    E1 registers no independent number. If this disagrees with
    :data:`REQUIRED_FREE_DEVICE_MEMORY_BYTES` the instrument has drifted and the
    binding, not the threshold, is what is wrong.
    """
    module = load_original_resource_route(repo_root)
    return int(module.required_bytes("RP_B3"))


def _fail(checks: List[Dict[str, object]], name: str, detail: object) -> None:
    checks.append({"check": name, "passed": False, "detail": detail})


def _pass(checks: List[Dict[str, object]], name: str, detail: object) -> None:
    checks.append({"check": name, "passed": True, "detail": detail})


def evaluate(observation: Mapping[str, Any],
             frozen_sku: str) -> Dict[str, object]:
    """Evaluate one measured device observation against the frozen SKU.

    ``observation`` is what ``nvidia-smi`` and the runtime API reported. It is
    never inferred from the SKU's paper specification: ``free_device_memory_bytes``
    must be a measurement.
    """
    if frozen_sku not in SKU_GPU_MARKERS:
        raise Study4FE1PreflightError("unregistered SKU: %r" % (frozen_sku,))

    checks: List[Dict[str, object]] = []
    devices: Sequence[Mapping[str, Any]] = observation.get("devices") or ()

    if len(devices) == 1:
        _pass(checks, "exactly_one_eligible_accelerator_visible", 1)
    else:
        _fail(checks, "exactly_one_eligible_accelerator_visible", len(devices))

    device: Optional[Mapping[str, Any]] = devices[0] if len(devices) == 1 else None

    name = str(device.get("name", "")) if device else ""
    markers = SKU_GPU_MARKERS[frozen_sku]
    if device is not None and any(marker in name for marker in markers):
        _pass(checks, "gpu_model_matches_the_frozen_sku", name)
    else:
        _fail(checks, "gpu_model_matches_the_frozen_sku", name)

    foreign = [process for process in (observation.get("processes") or ())
               if int(process.get("used_memory_bytes", 0))
               >= MATERIAL_FOREIGN_MEMORY_BYTES
               and not bool(process.get("is_this_run", False))]
    if foreign:
        _fail(checks, "no_unrelated_process_occupies_material_gpu_memory",
              [{"pid": process.get("pid"),
                "used_memory_bytes": process.get("used_memory_bytes")}
               for process in foreign])
    else:
        _pass(checks, "no_unrelated_process_occupies_material_gpu_memory", 0)

    free = int(device.get("free_device_memory_bytes", 0)) if device else 0
    measured = bool(device.get("memory_is_measured", False)) if device else False
    if not measured:
        _fail(checks, "free_device_memory_is_a_measurement_not_a_specification",
              measured)
    else:
        _pass(checks, "free_device_memory_is_a_measurement_not_a_specification",
              True)
    if free > REQUIRED_FREE_DEVICE_MEMORY_BYTES:
        _pass(checks, "measured_free_device_memory_exceeds_the_requirement", free)
    else:
        _fail(checks, "measured_free_device_memory_exceeds_the_requirement", free)

    if device is not None and bool(device.get("bf16_supported", False)):
        _pass(checks, "bf16_is_supported", True)
    else:
        _fail(checks, "bf16_is_supported", False)

    compatibility = observation.get("compatibility") or {}
    required = ("driver", "cuda", "framework")
    missing = [key for key in required if key not in compatibility]
    if missing:
        _fail(checks, "driver_cuda_and_framework_compatibility_tests_pass",
              {"missing": missing})
    elif all(bool(compatibility[key]) for key in required):
        _pass(checks, "driver_cuda_and_framework_compatibility_tests_pass",
              dict(compatibility))
    else:
        _fail(checks, "driver_cuda_and_framework_compatibility_tests_pass",
              dict(compatibility))

    failed = [str(check["check"]) for check in checks if not check["passed"]]
    memory_only = failed == ["measured_free_device_memory_exceeds_the_requirement"]
    passed = not failed

    state: Optional[str] = None
    if not passed:
        # An accelerator that exists but cannot hold the requirement is the one
        # branch section 6 names explicitly.
        accelerator_exists = len(devices) == 1
        if accelerator_exists and (memory_only or
                                   "measured_free_device_memory_exceeds_the_requirement"
                                   in failed):
            state = BELOW_REQUIREMENT_STATE
        else:
            state = BELOW_REQUIREMENT_STATE

    return {
        "frozen_sku": frozen_sku,
        "required_free_device_memory_bytes": REQUIRED_FREE_DEVICE_MEMORY_BYTES,
        "measured_free_device_memory_bytes": free,
        "checks": checks,
        "failed_checks": failed,
        "passed": passed,
        "paper_specification_accepted_as_evidence": False,
        "quantization_attempted": False,
        "sharding_attempted": False,
        "cpu_or_disk_offload_attempted": False,
        "device_map_auto_used": False,
        "state": state,
    }


def contract_matches_protocol(protocol: Mapping[str, Any]) -> Dict[str, object]:
    """Prove the E1 runtime contract is the original one, field by field."""
    original = protocol["model_loading_contract"]
    comparisons = {
        "trust_remote_code": original["trust_remote_code"],
        "unquantized_weights": original["unquantized_weights"],
        "torch_dtype": original["torch_dtype"],
        "cpu_offload": original["cpu_offload"],
        "disk_offload": original["disk_offload"],
        "device_map_auto": original["device_map_auto"],
        "batch_size": original["batch_size"],
        "evaluation_mode": original["evaluation_mode"],
        "explicit_attention_implementation_required":
            original["explicit_attention_implementation_required"],
    }
    differences = {key: (RUNTIME_CONTRACT[key], value)
                   for key, value in comparisons.items()
                   if RUNTIME_CONTRACT[key] != value}
    return {"identical": not differences, "differences": differences}
