"""Study 4F-E1 registered accelerator selection.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

Sections 3 and 4. Exactly two accelerator SKUs are registered, and H100 must be
attempted before A100:

===================================  ====  ==============  ======
SKU                                  GPUs  nominal GPU GB  vCPUs
===================================  ====  ==============  ======
``Standard_NC40ads_H100_v5``         1     94              40
``Standard_NC24ads_A100_v4``         1     80              24
===================================  ====  ==============  ======

T4, A10, V100, multi-GPU ND-series, Spot VMs and confidential-GPU substitutions
are not eligible and cannot be reached through this module.

Quota and capacity are *different things* and are reported separately:

* **quota** is an entitlement read from the authenticated quota API before
  anything is provisioned;
* **capacity** is only ever observed by attempting a real on-demand deployment.

When no eligible SKU/region has sufficient quota, capacity is *not observed at
all* and must not be described as unavailable. That is the whole point of
section 4.1: nothing is provisioned, so nothing is learned about capacity.

This module creates nothing. It is a pure function of discovery evidence.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

#: Registered SKU attempt order. H100 before A100, always.
REGISTERED_SKUS: Tuple[Dict[str, object], ...] = (
    {
        "sku": "Standard_NC40ads_H100_v5",
        "family": "StandardNCadsH100v5Family",
        "gpu": "H100 NVL",
        "gpu_count": 1,
        "nominal_gpu_memory_gb": 94,
        "vcpus": 40,
        "order": 1,
    },
    {
        "sku": "Standard_NC24ads_A100_v4",
        "family": "StandardNCADSA100v4Family",
        "gpu": "A100",
        "gpu_count": 1,
        "nominal_gpu_memory_gb": 80,
        "vcpus": 24,
        "order": 2,
    },
)

#: Accelerator classes that may never be substituted in.
PROHIBITED_SUBSTITUTIONS: Tuple[str, ...] = (
    "T4", "A10", "V100", "multi_gpu_nd_series", "spot_vm",
    "confidential_gpu",
)

#: The Azure restriction reason that removes a region from consideration.
DISQUALIFYING_RESTRICTION = "NotAvailableForSubscription"

#: Section 4.2 permits at most four on-demand deployment attempts in total.
MAX_DEPLOYMENT_ATTEMPTS = 4

NO_QUOTA_STATE = "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL"
NO_CAPACITY_STATE = "STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE"


class Study4FE1SelectionError(RuntimeError):
    """Raised when selection is driven outside its registered contract."""


def sku_record(sku: str) -> Dict[str, object]:
    for record in REGISTERED_SKUS:
        if record["sku"] == sku:
            return dict(record)
    raise Study4FE1SelectionError("unregistered SKU: %r" % (sku,))


def normalize_region(region: str) -> str:
    """Canonical region key used for the registered lexicographic ordering.

    The Azure APIs return a mixture of ``eastus2`` and ``CanadaCentral`` for the
    same kind of value, so the ordering is defined over the lowercase form with
    separators removed. Without this the ordering would depend on which API
    happened to answer, which is not a registered degree of freedom.
    """
    return "".join(ch for ch in region.lower() if ch.isalnum())


def region_is_offered(offer: Mapping[str, object]) -> bool:
    """True when the SKU is returned for the region without a hard restriction."""
    if not offer.get("returned_for_sku", False):
        return False
    if not offer.get("permitted_by_subscription_and_policy", False):
        return False
    for restriction in offer.get("restrictions") or ():
        if str(restriction) == DISQUALIFYING_RESTRICTION:
            return False
    return True


def has_sufficient_quota(offer: Mapping[str, object], vcpus: int) -> bool:
    """Both the VM-family and the total-regional vCPU budget must admit one VM."""
    family_free = (int(offer["family_vcpu_limit"]) -
                   int(offer["family_vcpu_used"]))
    total_free = (int(offer["total_regional_vcpu_limit"]) -
                  int(offer["total_regional_vcpu_used"]))
    return family_free >= vcpus and total_free >= vcpus


def eligible_regions(offers: Sequence[Mapping[str, object]], sku: str,
                     *, require_quota: bool = True) -> List[str]:
    """Registered eligible regions for one SKU, in lexicographic order.

    ``require_quota=False`` yields the *otherwise eligible* set: every region
    that satisfies every registered criterion except the family-vCPU quota that
    section 4.1 would ask for. It is used only to name the single SKU/region a
    quota request may be submitted for, never to provision anything.
    """
    record = sku_record(sku)
    vcpus = int(record["vcpus"])
    selected = []
    for offer in offers:
        if offer.get("sku") != sku:
            continue
        if not region_is_offered(offer):
            continue
        if require_quota and not has_sufficient_quota(offer, vcpus):
            continue
        if not require_quota:
            total_free = (int(offer["total_regional_vcpu_limit"]) -
                          int(offer["total_regional_vcpu_used"]))
            if total_free < vcpus:
                continue
        selected.append(str(offer["region"]))
    return sorted(selected, key=normalize_region)


def registered_attempt_order(offers: Sequence[Mapping[str, object]],
                             *, require_quota: bool = True
                             ) -> List[Dict[str, object]]:
    """The full registered SKU/region order: H100 first, then A100."""
    order: List[Dict[str, object]] = []
    for record in REGISTERED_SKUS:
        sku = str(record["sku"])
        for region in eligible_regions(offers, sku, require_quota=require_quota):
            order.append({
                "sku": sku,
                "family": record["family"],
                "vcpus": record["vcpus"],
                "region": region,
                "region_sort_key": normalize_region(region),
                "sku_order": record["order"],
            })
    return order


def select(offers: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    """Resolve the registered section 4 branch from discovery evidence alone.

    Returns the quota branch when no eligible SKU/region has sufficient quota.
    Capacity is deliberately left unobserved in that branch.
    """
    with_quota = registered_attempt_order(offers, require_quota=True)
    without_quota = registered_attempt_order(offers, require_quota=False)
    if with_quota:
        return {
            "branch": "quota_exists",
            "quota_sufficient_anywhere": True,
            "attempt_order": with_quota[:MAX_DEPLOYMENT_ATTEMPTS],
            "full_registered_order": with_quota,
            "capacity_observed": False,
            "quota_request_target": None,
            "state": None,
        }
    return {
        "branch": "no_sufficient_quota",
        "quota_sufficient_anywhere": False,
        "attempt_order": [],
        "full_registered_order": [],
        "capacity_observed": False,
        "quota_request_target": without_quota[0] if without_quota else None,
        "state": NO_QUOTA_STATE,
    }


def quota_request(target: Optional[Mapping[str, object]]) -> Dict[str, object]:
    """The single minimal quota request section 4.1 permits.

    Exactly one instance of the first eligible SKU/region and nothing larger:
    40 family vCPUs for ``Standard_NC40ads_H100_v5`` or 24 for
    ``Standard_NC24ads_A100_v4``.
    """
    if target is None:
        raise Study4FE1SelectionError(
            "no otherwise-eligible SKU/region exists to request quota for")
    record = sku_record(str(target["sku"]))
    return {
        "sku": record["sku"],
        "family": record["family"],
        "region": str(target["region"]),
        "requested_family_vcpus": int(record["vcpus"]),
        "instances_requested": 1,
        "is_the_minimal_registered_request": True,
        "larger_request_prohibited": True,
    }


def record_failed_attempt(sku: str, region: str, zone: Optional[str],
                          azure_error_code: str, kind: str) -> Dict[str, object]:
    """Section 4.2 evidence for one failed on-demand deployment attempt."""
    kinds = ("quota", "policy", "sku_restriction", "capacity")
    if kind not in kinds:
        raise Study4FE1SelectionError("unregistered failure kind: %r" % (kind,))
    sku_record(sku)
    return {
        "sku": sku,
        "region": region,
        "zone": zone,
        "azure_error_code": azure_error_code,
        "failure_kind": kind,
        "spot_used": False,
        "model_operation_occurred": False,
        "weights_acquired": 0,
        "model_calls": 0,
    }


def freeze(sku: str, region: str, zone: Optional[str]) -> Dict[str, object]:
    """Section 4.3. Freeze the first successfully provisioned SKU/region/zone.

    Freezing happens *before any model output is observed*, and after it no
    switch from H100 to A100 and no region change is legal.
    """
    record = sku_record(sku)
    return {
        "frozen": True,
        "sku": record["sku"],
        "gpu": record["gpu"],
        "gpu_count": record["gpu_count"],
        "vcpus": record["vcpus"],
        "region": region,
        "zone": zone,
        "frozen_before_any_model_output": True,
        "sku_switch_permitted_after_first_study_bank_call": False,
        "region_switch_permitted_after_first_study_bank_call": False,
    }
