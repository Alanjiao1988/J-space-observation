"""Study 4F-E1 dedicated, recoverable and explicitly deletable Azure plan.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

Sections 5 and 12. This module *emits* a deployment plan. It calls no Azure API,
creates nothing and deletes nothing, so it can be tested exhaustively without a
subscription and without a qualifying accelerator.

Two properties carry the whole recoverability argument:

* the resource group name is **deterministically derived from the E1 authority
  commit**, so the same authority always names the same group and a later
  operator can find it without guessing;
* every cleanup target is an **explicit, fully resolved resource ID**. Section 12
  forbids globs and unresolved variables for deletion, so
  :func:`cleanup_targets` refuses to emit either.

An existing resource group is never used and never deleted.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Mapping, Optional, Sequence

PROJECT_TAG = "J-space-observation"
STUDY_TAG = "study4f-e1"

#: Derivation material for the dedicated resource-group name.
RESOURCE_GROUP_PREFIX = "rg-study4f-e1-"
RESOURCE_GROUP_SEED = "STUDY4F_E1_RESOURCE_GROUP|%s"
RESOURCE_GROUP_SUFFIX_LENGTH = 16

#: Resource kinds E1 may create inside its own dedicated group.
RESOURCE_KINDS: Sequence[str] = (
    "resource_group", "virtual_network", "subnet", "network_security_group",
    "network_interface", "public_ip", "os_disk", "virtual_machine",
)

#: A fully resolved ARM resource ID. Anything else is refused.
RESOURCE_ID_PATTERN = re.compile(
    r"^/subscriptions/[0-9a-fA-F-]{36}/resourceGroups/[A-Za-z0-9._\-]+"
    r"/providers/[A-Za-z0-9.]+/[A-Za-z0-9]+/[A-Za-z0-9._\-]+$")

#: Substrings that indicate a glob or an unresolved variable.
FORBIDDEN_ID_MARKERS: Sequence[str] = ("*", "?", "$", "{", "}", "%", "<", ">")


class Study4FE1DeploymentPlanError(RuntimeError):
    """Raised when a plan would violate a registered deployment constraint."""


def resource_group_name(authority_commit: str) -> str:
    """Deterministic dedicated resource-group name for one E1 authority."""
    if not authority_commit or len(authority_commit) != 40:
        raise Study4FE1DeploymentPlanError(
            "the E1 authority commit must be a full 40-hex commit id")
    int(authority_commit, 16)
    digest = hashlib.sha256(
        (RESOURCE_GROUP_SEED % (authority_commit.lower(),)).encode("utf-8")
    ).hexdigest()
    return RESOURCE_GROUP_PREFIX + digest[:RESOURCE_GROUP_SUFFIX_LENGTH]


def tags(authority_commit: str, created_at: str, expires_at: str
         ) -> Dict[str, str]:
    """Every created resource carries the registered tag set."""
    if not created_at or not expires_at:
        raise Study4FE1DeploymentPlanError(
            "creation and automatic expiry timestamps are both required")
    if expires_at <= created_at:
        raise Study4FE1DeploymentPlanError(
            "the automatic expiry timestamp must follow creation")
    return {
        "project": PROJECT_TAG,
        "study": STUDY_TAG,
        "authority_commit": authority_commit,
        "created_at": created_at,
        "expires_at": expires_at,
    }


def build_plan(authority_commit: str, sku: str, region: str,
               zone: Optional[str], created_at: str, expires_at: str,
               *, os_disk_gib: int = 1024) -> Dict[str, object]:
    """Emit the full deployment plan without contacting Azure."""
    if os_disk_gib < 512:
        raise Study4FE1DeploymentPlanError(
            "the OS/local disk must hold four immutable checkpoints and artifacts")
    group = resource_group_name(authority_commit)
    return {
        "schema_version": "study4f-e1-deployment-plan-v1",
        "creates_nothing_when_emitted": True,
        "resource_group": group,
        "resource_group_is_new_and_dedicated": True,
        "reuses_an_existing_resource_group": False,
        "deletes_an_existing_resource_group": False,
        "region": region,
        "zone": zone,
        "vm": {
            "sku": sku,
            "priority": "Regular",
            "spot": False,
            "os": "Linux",
            "gpu_count": 1,
            "os_disk_gib": os_disk_gib,
            "nvidia_driver_required": True,
            "container_runtime_required": True,
        },
        "network": {
            "public_service_endpoint": False,
            "management_path_only": True,
            "outbound_access": "immutable checkpoint and container acquisition only",
        },
        "secrets": {
            "in_source": False,
            "in_cloud_init": False,
            "in_logs": False,
        },
        "tags": tags(authority_commit, created_at, expires_at),
        "resource_kinds": list(RESOURCE_KINDS),
    }


def _reject_unresolved(resource_id: str) -> None:
    for marker in FORBIDDEN_ID_MARKERS:
        if marker in resource_id:
            raise Study4FE1DeploymentPlanError(
                "cleanup target contains a glob or unresolved variable: %r"
                % (resource_id,))
    if not RESOURCE_ID_PATTERN.match(resource_id):
        raise Study4FE1DeploymentPlanError(
            "cleanup target is not a fully resolved resource id: %r"
            % (resource_id,))


def cleanup_targets(resource_ids: Sequence[str], resource_group: str
                    ) -> List[str]:
    """Validate the explicit deletion set. Refuses globs and foreign groups."""
    if not resource_group.startswith(RESOURCE_GROUP_PREFIX):
        raise Study4FE1DeploymentPlanError(
            "refusing to enumerate cleanup outside a dedicated E1 group")
    targets: List[str] = []
    needle = "/resourceGroups/%s/" % (resource_group,)
    for resource_id in resource_ids:
        _reject_unresolved(resource_id)
        if needle not in resource_id:
            raise Study4FE1DeploymentPlanError(
                "cleanup target is outside the dedicated E1 group: %r"
                % (resource_id,))
        targets.append(resource_id)
    return targets


def cleanup_verdict(plan: Mapping[str, object],
                    remaining: Sequence[str],
                    artifacts_published: bool) -> Dict[str, object]:
    """Section 12 disposition after artifacts are retrieved and hash-verified.

    When artifact publication failed the VM is still deallocated, but the
    dedicated group is retained rather than deleted: reporting its exact state
    is required, deleting the only copy is not.
    """
    billable = [resource_id for resource_id in remaining
                if "/virtualMachines/" in resource_id
                or "/disks/" in resource_id
                or "/networkInterfaces/" in resource_id
                or "/publicIPAddresses/" in resource_id]
    return {
        "artifacts_published_and_hash_verified": bool(artifacts_published),
        "vm_deallocated": True,
        "resource_group": plan["resource_group"],
        "resource_group_deleted": bool(artifacts_published) and not billable,
        "resource_group_retained_for_recovery": not bool(artifacts_published),
        "remaining_resources": list(remaining),
        "remaining_billable_resources": billable,
        "no_billable_accelerator_remains": not billable,
    }
