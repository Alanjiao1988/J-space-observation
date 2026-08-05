"""Fail-closed tooling for the Phase 1.0D review-only transport recovery.

This module has no provider client and performs no network I/O. Azure control
plane and Blob readbacks are supplied as JSON evidence by the operator. The
module normalizes deployment limits, reconstructs frozen request bytes offline,
seals the capacity certificate, and builds/verifies the one recovery Job and
lock contracts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.semantic_review import addendum as review_contract  # noqa: E402
from jspace_observation.semantic_review_v2 import addendum_v2  # noqa: E402

SCHEMA_VERSION = "phase1-0d-transport-recovery/v1"
CERTIFICATE_SCHEMA_VERSION = "phase1-0d-transport-capacity-certificate/v1"
CERTIFICATE_MANIFEST_SCHEMA_VERSION = (
    "phase1-0d-transport-capacity-certificate-manifest/v1"
)
LOCK_SCHEMA_VERSION = "phase1-0d-transport-recovery-lock/v1"

AUTHORITY_PATH = (
    "docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md"
)
AUTHORITY_SHA256 = (
    "dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b"
)
STARTING_COMMIT = "d145b1c79db8b6866fadaa8875c2374a813a7e31"
STARTING_TREE = "b4329a4062415cf7cb3b058d3defe6da7c14f25c"
REQUIRED_ANCESTOR = "5ae85cb838ff2c8d296ee90b10f1ca2e9f885b0a"

V1_PROTECTED_FILE_COUNT = 152
V1_PROTECTED_ROLLUP = (
    "436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd"
)
V2_PROTECTED_FILE_COUNT = 36
V2_PROTECTED_ROLLUP = (
    "ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a"
)
V2_PROTECTED_MANIFEST_SHA256 = (
    "9b7705ccdc630bce5fe77503c35ff6644cd37f876b886fa9cd8a14f8c7012e77"
)

GENERATION_IMAGE_DIGEST = (
    "sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
)
V1_REVIEW_IMAGE_DIGEST = (
    "sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10"
)
V2_REVIEW_IMAGE_DIGEST = (
    "sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd"
)
V2_REVIEW_IMAGE_COMMIT = "1b56f775b5457e2e11124559052ad4caf028fdad"
V2_REVIEW_IMAGE_REF = (
    "acrjspaceobssea0708231738.azurecr.io/"
    "j-space-observation-phase1-0d-review-v2@"
    + V2_REVIEW_IMAGE_DIGEST
)

GENERATION_RUN_ID = "20260804T154518Z"
GENERATION_JOB_NAME = "job-jspace-p10d-confirmation"
GENERATION_EXECUTION = "job-jspace-p10d-confirmation-pdlhmah"
GENERATION_PREFIX = f"phase1-headroom-confirmation/{GENERATION_RUN_ID}"
SOURCE_MANIFEST_REPO_PATH = (
    f"artifacts/phase1-0d-confirmation/{GENERATION_RUN_ID}/artifact_manifest.json"
)
SOURCE_MANIFEST_SHA256 = (
    "76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536"
)
QUALIFICATION_RUN_ID = "20260803T230642Z"
QUALIFICATION_RECEIPT_SHA256 = (
    "fc18950ab10ae576559d8ab2102f4c4363428f0c5d8619e762488435a4b56875"
)
QUALIFICATION_MANIFEST_SHA256 = (
    "9e942f49667ac15ec0c0cbccdbc12af39612079e399f9bde6de025268fd40206"
)
SMOKE_RUN_ID = "20260803T235227Z"
SMOKE_RECEIPT_SHA256 = (
    "c1bd6cbbcf888511cfee9da48111e7950f0c746988937a02a386dfcc574137fc"
)
SMOKE_MANIFEST_SHA256 = (
    "aa0aabb37a9a41bea476fd5e612fc32208af9495316e30ad98081481a07a3c43"
)

OLD_FORMAL_RUN_ID = "20260804T181247Z"
OLD_FORMAL_JOB_NAME = "job-p10d-rv2-r-d4a84a59bc28a91f"
OLD_FORMAL_EXECUTION = "job-p10d-rv2-r-d4a84a59bc28a91f-tjzwlse"
OLD_FORMAL_LOCK_SHA256 = (
    "d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f"
)
OLD_TERMINAL_ARCHIVE_SHA256 = (
    "41694a6b9593756d3cbed3014367887567f5e785840dce86bceb2da41a39c204"
)
OLD_TERMINAL_ARCHIVE_REPO_PATH = (
    "artifacts/phase1-0d-semantic-review-v2-formal/"
    f"{OLD_FORMAL_RUN_ID}/artifact_manifest.json"
)
OLD_RESULT_PREFIX = (
    f"phase1-headroom-confirmation-review-v2/{OLD_FORMAL_RUN_ID}"
)

BLOB_ACCOUNT = "stjspacefiles0709085305"
BLOB_CONTAINER = "jspace-results"
RECOVERY_LOCK_BLOB = (
    "phase1-0d-semantic-review-v2/transport-recovery/formal-review-lock.json"
)
RECOVERY_RESULT_ROOT = (
    "phase1-headroom-confirmation-review-v2-transport-recovery"
)
CAPACITY_ARTIFACT_ROOT = (
    "artifacts/phase1-0d-semantic-review-v2-transport-capacity"
)
CAPACITY_CERTIFICATE_NAME = "00_capacity_certificate.json"
CAPACITY_MANIFEST_NAME = "artifact_manifest.json"
CAPACITY_BLOB_PREFIX = (
    "phase1-0d-semantic-review-v2/transport-recovery/capacity"
)

RESOURCE_GROUP = "rg-jspace-observation-sea"
CONTAINER_APP_ENVIRONMENT = "cae-jspace-observation-sea-vnet2"
WORKLOAD_PROFILE_NAME = "Consumption"
IDENTITY_NAME = "id-jspace-p10d-review-sea"
IDENTITY_CLIENT_ID = "67d9b724-e00b-4a87-a1ce-fce2308685a2"
ACR_NAME = "acrjspaceobssea0708231738"
ACR_LOGIN_SERVER = f"{ACR_NAME}.azurecr.io"
REPLICA_TIMEOUT_SECONDS = 612300
REVIEW_TIMEOUT_SECONDS = 612000

PROFILE_SHA256 = {
    "primary": "5b2352bf8428e0c278397b24efa2469cbb94692be64f8e0b50e878c3c85c97af",
    "secondary": "35ebb8afc283a17baa12cf422cb952a5d088bd5690e1a731b9f76fd1b3af2b8e",
    "third": "5361270acc780b00d73de0dff9b51baefcd103d0f9cd0678a923b8dc3749bf4f",
}
ROLE_CONTRACTS = {
    "primary": {
        "account": "aj-gpt56-25-943b-eastus2",
        "resource_group": "gpt56-sol-2025-rg",
        "deployment": "gpt-5-6-sol-global",
        "endpoint_host": "aj-gpt56-25-943b-eastus2.openai.azure.com",
        "location": "eastus2",
        "model_format": "OpenAI",
        "model_name": "gpt-5.6-sol",
        "model_version": "2026-07-09",
        "sku_name": "GlobalStandard",
        "minimum_tpm": 1_000_000,
        "minimum_rpm": 1_000,
        "usage_name": "OpenAI.GlobalStandard.gpt-5.6-sol",
    },
    "secondary": {
        "account": "aif-jspace-p10d-review-eastus2",
        "resource_group": RESOURCE_GROUP,
        "deployment": "mistral-large-3-global",
        "endpoint_host": "aif-jspace-p10d-review-eastus2.services.ai.azure.com",
        "location": "eastus2",
        "model_format": "Mistral AI",
        "model_name": "Mistral-Large-3",
        "model_version": "1",
        "sku_name": "GlobalStandard",
        "minimum_tpm": 500_000,
        "minimum_rpm": 500,
        "usage_name": "AIServices.GlobalStandard.Mistral-Large-3",
    },
    "third": {
        "account": "aif-jspace-p10d-review-eastus2",
        "resource_group": RESOURCE_GROUP,
        "deployment": "deepseek-v4-pro-global",
        "endpoint_host": "aif-jspace-p10d-review-eastus2.services.ai.azure.com",
        "location": "eastus2",
        "model_format": "DeepSeek",
        "model_name": "DeepSeek-V4-Pro",
        "model_version": "2026-04-23",
        "sku_name": "GlobalStandard",
        "minimum_tpm": 1_000_000,
        "minimum_rpm": 500,
        "usage_name": "AIServices.GlobalStandard.DeepSeek-V4-Pro",
    },
}
ACCOUNT_CONTRACTS = {
    "aj-gpt56-25-943b-eastus2": {
        "resource_group": "gpt56-sol-2025-rg",
        "location": "eastus2",
        "kind": "OpenAI",
        "sku_name": "S0",
        "arm_endpoint_host": "aj-gpt56-25-943b-eastus2.openai.azure.com",
        "registered_endpoint_hosts": [
            "aj-gpt56-25-943b-eastus2.openai.azure.com"
        ],
    },
    "aif-jspace-p10d-review-eastus2": {
        "resource_group": RESOURCE_GROUP,
        "location": "eastus2",
        "kind": "AIServices",
        "sku_name": "S0",
        "arm_endpoint_host": (
            "aif-jspace-p10d-review-eastus2.cognitiveservices.azure.com"
        ),
        "registered_endpoint_hosts": [
            "aif-jspace-p10d-review-eastus2.services.ai.azure.com"
        ],
    },
}
IDENTITY_ROUTE_CONTRACT = {
    "identity_name": IDENTITY_NAME,
    "client_id": IDENTITY_CLIENT_ID,
    "authentication": "Entra ID user-assigned managed identity",
    "role_assignments": {
        "primary_account": "Cognitive Services OpenAI User",
        "shared_account": "Cognitive Services OpenAI User",
        "blob_container": "Storage Blob Data Contributor",
        "container_registry": "AcrPull",
    },
}

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
JOB_NAME = re.compile(r"^job-p10d-rv2-tr-[0-9a-f]{8}$")

REQUEST_ROLLUP_DOMAIN = (
    "jspace-phase1-0d/transport-recovery/request-bodies/v1"
)
CAPACITY_PATCH_ALLOWED_CHANGE_PATHS = {
    ("etag",),
    ("properties", "currentCapacity"),
    ("properties", "provisioningState"),
    ("properties", "rateLimits"),
    ("sku", "capacity"),
}
SUCCESS_REQUIRED_MEMBERS = {
    "00_execution_receipt.json",
    "artifact_manifest.json",
    "review/all_judgments.json",
    "review/primary/judgments.json",
    "review/primary/raw_response_manifest.json",
    "review/secondary/judgments.json",
    "review/secondary/raw_response_manifest.json",
    "review/secondary/selection_receipt.json",
    "review/third/judgments.json",
    "review/third/raw_response_manifest.json",
    "review/third/disagreement_receipt.json",
    "final/05_decision.json",
    "final/artifact_manifest.json",
}
TERMINAL_ARCHIVE_MEMBERS = {
    "00_terminal_receipt.json",
    "01_terminal_console_excerpt.txt",
    "02_transport_recovery_lock.json",
    "03_capacity_certificate_manifest.json",
}


class RecoveryError(RuntimeError):
    """A transport-recovery invariant could not be proven."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise RecoveryError(f"value is not canonical JSON: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], description: str
) -> None:
    observed = set(value)
    if observed != expected:
        raise RecoveryError(
            f"{description} keys differ: missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)}"
        )


def _positive_integer(value: Any, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RecoveryError(f"{description} must be a positive integer")
    return value


def _nonnegative_integer(value: Any, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RecoveryError(f"{description} must be a nonnegative integer")
    return value


def load_json(path: Path) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RecoveryError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    def reject_nonfinite(value: str) -> Any:
        raise RecoveryError(f"non-finite JSON constant {value!r} in {path}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"cannot load JSON {path}: {exc}") from exc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line:
                raise RecoveryError(f"{path}:{number} is blank")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RecoveryError(f"{path}:{number} is not an object")
            rows.append(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"cannot load JSONL {path}: {exc}") from exc
    return rows


def verify_frozen_profiles(project_root: Path) -> None:
    book = addendum_v2.load_addendum_v2(project_root)
    for role, expected in PROFILE_SHA256.items():
        observed = book.roles[role].request_profile_sha256()
        if observed != expected:
            raise RecoveryError(
                f"{role} request profile hashes to {observed}, expected {expected}"
            )
    if book.max_in_flight != 8:
        raise RecoveryError("frozen review concurrency is not 8")
    retry = dict(book.retry)
    if (
        retry.get("max_attempts") != 8
        or retry.get("identical_request_required") is not True
        or retry.get("semantic_retry_forbidden") is not True
    ):
        raise RecoveryError("frozen retry contract moved")


def request_body_rollups(
    review_form_path: Path, project_root: Path = REPO_ROOT
) -> dict[str, dict[str, Any]]:
    """Hash all 900 possible request bodies for every frozen role, offline."""

    verify_frozen_profiles(project_root)
    rows = load_jsonl(review_form_path)
    if len(rows) != 900:
        raise RecoveryError(f"review form has {len(rows)} rows, expected 900")
    expected_fields = set(review_contract.PRESENTED_FIELDS)
    for index, row in enumerate(rows):
        _require_exact_keys(row, expected_fields, f"review row {index}")
        if not isinstance(row.get("record_id"), str) or not row["record_id"]:
            raise RecoveryError(f"review row {index} has no record_id")
    ordered = sorted(rows, key=lambda item: str(item["record_id"]))
    ids = [str(row["record_id"]) for row in ordered]
    if len(set(ids)) != 900:
        raise RecoveryError("review form record_ids are not unique")

    book = addendum_v2.load_addendum_v2(project_root)
    id_rollup = sha256_bytes(canonical_json_bytes(ids))
    result: dict[str, dict[str, Any]] = {}
    for role in review_contract.ROLES:
        profile = book.roles[role]
        request_hashes: list[str] = []
        rollup = hashlib.sha256()
        rollup.update(f"{REQUEST_ROLLUP_DOMAIN}\n{role}\n".encode("ascii"))
        for record_id, row in zip(ids, ordered, strict=True):
            body = review_contract.build_request(profile, book, row)
            digest = sha256_bytes(review_contract.request_bytes(body))
            request_hashes.append(digest)
            rollup.update(f"{record_id}\t{digest}\n".encode("utf-8"))
        result[role] = {
            "role": role,
            "row_count": 900,
            "ordering": "record_id ascending, identical to review_rows",
            "ordered_record_ids_sha256": id_rollup,
            "ordered_request_body_sha256_rollup": rollup.hexdigest(),
            "first_record_id": ids[0],
            "last_record_id": ids[-1],
            "request_profile_sha256": PROFILE_SHA256[role],
            "all_request_hashes_are_sha256": all(
                SHA256.fullmatch(item) for item in request_hashes
            ),
        }
    return result


def normalize_rate_limits(rate_limits: Any) -> dict[str, Any]:
    """Normalize one exact request rule and one exact token rule to one minute."""

    if not isinstance(rate_limits, list) or not rate_limits:
        raise RecoveryError("deployment rateLimits are absent")
    by_key: dict[str, Mapping[str, Any]] = {}
    originals: list[dict[str, Any]] = []
    for index, raw in enumerate(rate_limits):
        if not isinstance(raw, Mapping):
            raise RecoveryError(f"rateLimits[{index}] is not an object")
        if set(raw) != {"count", "key", "renewalPeriod"}:
            raise RecoveryError(f"rateLimits[{index}] has ambiguous fields")
        key = str(raw["key"]).lower()
        if key not in {"request", "token"}:
            raise RecoveryError(f"unrecognized rate-limit key {key!r}")
        if key in by_key:
            raise RecoveryError(f"duplicate {key} rate-limit rule")
        count = _positive_integer(raw["count"], f"{key} count")
        window = _positive_integer(raw["renewalPeriod"], f"{key} renewalPeriod")
        normalized = Fraction(count * 60, window)
        if normalized.denominator != 1:
            raise RecoveryError(
                f"{key} rate does not normalize to an integral per-minute value"
            )
        by_key[key] = raw
        originals.append(
            {"count": count, "key": key, "renewalPeriod": window}
        )
    if set(by_key) != {"request", "token"}:
        raise RecoveryError("deployment lacks an exact request/token rate-limit pair")
    request = by_key["request"]
    token = by_key["token"]
    rpm = Fraction(
        _positive_integer(request["count"], "request count") * 60,
        _positive_integer(request["renewalPeriod"], "request renewalPeriod"),
    )
    tpm = Fraction(
        _positive_integer(token["count"], "token count") * 60,
        _positive_integer(token["renewalPeriod"], "token renewalPeriod"),
    )
    return {
        "original_rules": originals,
        "rpm": int(rpm),
        "tpm": int(tpm),
    }


def sanitize_deployment(
    role: str,
    raw: Mapping[str, Any],
    *,
    account: str,
    resource_group: str,
    endpoint_host: str,
    location: str,
) -> dict[str, Any]:
    if role not in ROLE_CONTRACTS:
        raise RecoveryError(f"unknown role {role!r}")
    contract = ROLE_CONTRACTS[role]
    supplied = {
        "account": account,
        "resource_group": resource_group,
        "endpoint_host": endpoint_host,
        "location": location.lower(),
    }
    for key, observed in supplied.items():
        expected = str(contract[key]).lower() if key == "location" else contract[key]
        if observed != expected:
            raise RecoveryError(
                f"{role} {key} is {observed!r}, expected {expected!r}"
            )
    properties = raw.get("properties")
    sku = raw.get("sku")
    if not isinstance(properties, Mapping) or not isinstance(sku, Mapping):
        raise RecoveryError(f"{role} deployment lacks properties or sku")
    model = properties.get("model")
    if not isinstance(model, Mapping):
        raise RecoveryError(f"{role} deployment lacks model")
    capacity = _positive_integer(sku.get("capacity"), f"{role} sku.capacity")
    if sku.get("name") != contract["sku_name"]:
        raise RecoveryError(f"{role} SKU differs from the frozen profile")
    expected_model = {
        "format": contract["model_format"],
        "name": contract["model_name"],
        "version": contract["model_version"],
    }
    observed_model = {key: model.get(key) for key in expected_model}
    if observed_model != expected_model:
        raise RecoveryError(
            f"{role} model differs: {observed_model!r} != {expected_model!r}"
        )
    current_capacity = properties.get("currentCapacity")
    if current_capacity is not None and current_capacity != capacity:
        raise RecoveryError(f"{role} currentCapacity differs from sku.capacity")
    normalized = normalize_rate_limits(properties.get("rateLimits"))
    etag = raw.get("etag")
    if not isinstance(etag, str) or not etag:
        raise RecoveryError(f"{role} deployment has no ETag")
    return {
        "account": account,
        "resource_group": resource_group,
        "deployment": contract["deployment"],
        "endpoint_host": endpoint_host,
        "location": location.lower(),
        "etag": etag,
        "sku": {"name": sku["name"], "capacity": capacity},
        "properties": {
            "model": expected_model,
            "versionUpgradeOption": properties.get("versionUpgradeOption"),
            "provisioningState": properties.get("provisioningState"),
            "currentCapacity": current_capacity,
            "rateLimits": normalized["original_rules"],
            "dynamicThrottlingEnabled": properties.get(
                "dynamicThrottlingEnabled"
            ),
            "spilloverDeploymentName": properties.get(
                "spilloverDeploymentName"
            ),
            "parentDeploymentName": properties.get("parentDeploymentName"),
        },
        "normalized_rate_limits": {
            "rpm": normalized["rpm"],
            "tpm": normalized["tpm"],
        },
    }


def minimum_capacity_for_floor(
    current_capacity: int,
    *,
    current_tpm: int,
    current_rpm: int,
    minimum_tpm: int,
    minimum_rpm: int,
) -> int:
    values = {
        "current_capacity": current_capacity,
        "current_tpm": current_tpm,
        "current_rpm": current_rpm,
        "minimum_tpm": minimum_tpm,
        "minimum_rpm": minimum_rpm,
    }
    for name, value in values.items():
        _positive_integer(value, name)
    by_tpm = math.ceil(Fraction(current_capacity * minimum_tpm, current_tpm))
    by_rpm = math.ceil(Fraction(current_capacity * minimum_rpm, current_rpm))
    return max(current_capacity, by_tpm, by_rpm)


def select_usage_line(role: str, usage_document: Mapping[str, Any]) -> dict[str, Any]:
    value = usage_document.get("value")
    if not isinstance(value, list):
        raise RecoveryError("Usages response has no value list")
    expected = ROLE_CONTRACTS[role]["usage_name"]
    matches = [
        item
        for item in value
        if isinstance(item, Mapping)
        and isinstance(item.get("name"), Mapping)
        and item["name"].get("value") == expected
    ]
    if len(matches) != 1:
        raise RecoveryError(
            f"{role} usage line {expected!r} matched {len(matches)} records"
        )
    raw = matches[0]
    current = _nonnegative_integer(
        raw.get("currentValue"), f"{role} usage currentValue"
    )
    limit = _positive_integer(raw.get("limit"), f"{role} usage limit")
    if current > limit:
        raise RecoveryError(f"{role} usage currentValue exceeds limit")
    if raw.get("unit") != "Count":
        raise RecoveryError(f"{role} usage unit is not Count")
    return {
        "name": expected,
        "localized_value": raw["name"].get("localizedValue"),
        "current_value": current,
        "limit": limit,
        "unallocated": limit - current,
        "unit": "Count",
    }


def select_model_capacity(
    role: str, model_capacity_document: Mapping[str, Any]
) -> dict[str, Any]:
    value = model_capacity_document.get("value")
    if not isinstance(value, list):
        raise RecoveryError("Model Capacities response has no value list")
    contract = ROLE_CONTRACTS[role]
    matches: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        properties = item.get("properties")
        model = properties.get("model") if isinstance(properties, Mapping) else None
        if (
            str(item.get("location", "")).lower() == contract["location"]
            and isinstance(properties, Mapping)
            and properties.get("skuName") == contract["sku_name"]
            and isinstance(model, Mapping)
            and model.get("format") == contract["model_format"]
            and model.get("name") == contract["model_name"]
            and model.get("version") == contract["model_version"]
        ):
            matches.append(item)
    if len(matches) != 1:
        raise RecoveryError(
            f"{role} Model Capacities record matched {len(matches)} records"
        )
    properties = matches[0]["properties"]
    available = properties.get("availableCapacity")
    if (
        isinstance(available, bool)
        or not isinstance(available, (int, float))
        or not math.isfinite(available)
    ):
        raise RecoveryError(f"{role} availableCapacity is absent or ambiguous")
    return {
        "location": contract["location"],
        "sku_name": contract["sku_name"],
        "model": {
            "format": contract["model_format"],
            "name": contract["model_name"],
            "version": contract["model_version"],
        },
        "available_capacity": available,
    }


def build_capacity_patch(before: Mapping[str, Any], target_capacity: int) -> dict[str, Any]:
    sku = before.get("sku")
    if not isinstance(sku, Mapping):
        raise RecoveryError("deployment projection has no sku")
    current = _positive_integer(sku.get("capacity"), "current capacity")
    target = _positive_integer(target_capacity, "target capacity")
    if target <= current:
        raise RecoveryError("capacity PATCH must strictly increase capacity")
    name = sku.get("name")
    if not isinstance(name, str) or not name:
        raise RecoveryError("capacity PATCH has no SKU name")
    return {"sku": {"name": name, "capacity": target}}


def _diff_paths(
    before: Any, after: Any, path: tuple[str, ...] = ()
) -> set[tuple[str, ...]]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        changed: set[tuple[str, ...]] = set()
        for key in set(before) | set(after):
            if key not in before or key not in after:
                changed.add((*path, str(key)))
            else:
                changed |= _diff_paths(before[key], after[key], (*path, str(key)))
        return changed
    if before != after:
        return {path}
    return set()


def verify_capacity_change_allowlist(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> set[tuple[str, ...]]:
    changed = _diff_paths(before, after)
    forbidden = {
        path
        for path in changed
        if not any(
            path[: len(allowed)] == allowed
            for allowed in CAPACITY_PATCH_ALLOWED_CHANGE_PATHS
        )
    }
    if forbidden:
        rendered = ", ".join(".".join(path) for path in sorted(forbidden))
        raise RecoveryError(f"capacity mutation changed non-allowlisted fields: {rendered}")
    return changed


def _gate(
    gates: list[dict[str, Any]],
    gate_id: str,
    expected: Any,
    observed: Any,
    passed: bool,
) -> None:
    gates.append(
        {
            "gate_id": gate_id,
            "expected": expected,
            "observed": observed,
            "passed": bool(passed),
        }
    )


def _validate_rollups(
    rollups: Any,
    gates: list[dict[str, Any]],
    *,
    expected_rollups: Mapping[str, Any] | None = None,
) -> None:
    if not isinstance(rollups, Mapping):
        raise RecoveryError("request_body_rollups are absent")
    if set(rollups) != set(review_contract.ROLES):
        raise RecoveryError("request_body_rollups role membership differs")
    for role in review_contract.ROLES:
        item = rollups.get(role)
        if not isinstance(item, Mapping):
            raise RecoveryError(f"{role} request-body rollup is absent")
        expected_keys = {
            "role",
            "row_count",
            "ordering",
            "ordered_record_ids_sha256",
            "ordered_request_body_sha256_rollup",
            "first_record_id",
            "last_record_id",
            "request_profile_sha256",
            "all_request_hashes_are_sha256",
        }
        _require_exact_keys(item, expected_keys, f"{role} request-body rollup")
        passed = (
            item.get("role") == role
            and item.get("row_count") == 900
            and item.get("request_profile_sha256") == PROFILE_SHA256[role]
            and item.get("all_request_hashes_are_sha256") is True
            and isinstance(item.get("ordered_record_ids_sha256"), str)
            and SHA256.fullmatch(item["ordered_record_ids_sha256"])
            and isinstance(
                item.get("ordered_request_body_sha256_rollup"), str
            )
            and SHA256.fullmatch(
                item["ordered_request_body_sha256_rollup"]
            )
            and (
                expected_rollups is None
                or item == expected_rollups.get(role)
            )
        )
        _gate(
            gates,
            f"{role}.offline_request_body_rollup",
            {"row_count": 900, "profile": PROFILE_SHA256[role]},
            {
                "row_count": item.get("row_count"),
                "profile": item.get("request_profile_sha256"),
            },
            bool(passed),
        )


def _parse_utc_second(value: Any, description: str) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
        value,
    ):
        raise RecoveryError(f"{description} is not an exact UTC-second stamp")
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc
        )
    except ValueError as exc:
        raise RecoveryError(f"{description} is not a valid UTC stamp") from exc


def evaluate_capacity_evidence(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Evaluate every mechanical gate without making a provider or Azure call."""

    gates: list[dict[str, Any]] = []
    observation = evidence.get("observation")
    if not isinstance(observation, Mapping):
        raise RecoveryError("capacity observation timestamps are absent")
    timestamp_keys = (
        "certificate_observed_at_utc",
        "control_plane_readback_at_utc",
        "monitor_window_end_utc",
        "private_state_readback_at_utc",
        "job_inventory_readback_at_utc",
    )
    parsed_timestamps = {
        key: _parse_utc_second(observation.get(key), key)
        for key in timestamp_keys
    }
    completed = parsed_timestamps["certificate_observed_at_utc"]
    timestamps_passed = all(
        observed <= completed for observed in parsed_timestamps.values()
    ) and (
        completed - min(parsed_timestamps.values())
        <= dt.timedelta(minutes=5)
    )
    _gate(
        gates,
        "capacity_evidence_timestamps",
        {
            "all_material_readbacks_not_after_certificate": True,
            "maximum_collection_span_seconds": 300,
        },
        dict(observation),
        timestamps_passed,
    )
    _gate(
        gates,
        "provider_calls_before_recovery",
        0,
        evidence.get("provider_calls"),
        evidence.get("provider_calls") == 0,
    )
    _validate_rollups(evidence.get("request_body_rollups"), gates)

    accounts = evidence.get("accounts")
    if not isinstance(accounts, Mapping):
        raise RecoveryError("account evidence is absent")
    for account_name, expected_account in ACCOUNT_CONTRACTS.items():
        account = accounts.get(account_name)
        if not isinstance(account, Mapping):
            raise RecoveryError(f"account evidence absent for {account_name}")
        observed_account = {
            key: account.get(key)
            for key in (
                "resource_group",
                "location",
                "kind",
                "sku_name",
                "arm_endpoint_host",
                "registered_endpoint_hosts",
            )
        }
        _gate(
            gates,
            f"{account_name}.account_identity",
            expected_account,
            observed_account,
            observed_account == expected_account,
        )
        _gate(
            gates,
            f"{account_name}.local_auth_disabled",
            True,
            account.get("disable_local_auth"),
            account.get("disable_local_auth") is True,
        )
    identity_route = evidence.get("identity_route")
    _gate(
        gates,
        "registered_identity_route",
        IDENTITY_ROUTE_CONTRACT,
        identity_route,
        identity_route == IDENTITY_ROUTE_CONTRACT,
    )

    deployments = evidence.get("deployments")
    if not isinstance(deployments, Mapping):
        raise RecoveryError("deployment evidence is absent")
    for role, contract in ROLE_CONTRACTS.items():
        item = deployments.get(role)
        if not isinstance(item, Mapping):
            raise RecoveryError(f"{role} deployment evidence is absent")
        before = item.get("before")
        after = item.get("after")
        usage = item.get("usage")
        model_capacity = item.get("model_capacity")
        if not all(
            isinstance(value, Mapping)
            for value in (before, after, usage, model_capacity)
        ):
            raise RecoveryError(f"{role} capacity evidence is incomplete")

        identity = {
            key: after.get(key)
            for key in (
                "account",
                "resource_group",
                "deployment",
                "endpoint_host",
                "location",
            )
        }
        expected_identity = {
            key: contract[key]
            for key in (
                "account",
                "resource_group",
                "deployment",
                "endpoint_host",
                "location",
            )
        }
        _gate(
            gates,
            f"{role}.deployment_identity",
            expected_identity,
            identity,
            identity == expected_identity,
        )
        properties = after.get("properties")
        normalized = after.get("normalized_rate_limits")
        sku = after.get("sku")
        if not all(
            isinstance(value, Mapping)
            for value in (properties, normalized, sku)
        ):
            raise RecoveryError(f"{role} deployment projection is malformed")
        state_passed = (
            properties.get("provisioningState") == "Succeeded"
            and sku.get("name") == contract["sku_name"]
            and properties.get("model")
            == {
                "format": contract["model_format"],
                "name": contract["model_name"],
                "version": contract["model_version"],
            }
        )
        _gate(
            gates,
            f"{role}.model_sku_state",
            {
                "model": [
                    contract["model_format"],
                    contract["model_name"],
                    contract["model_version"],
                ],
                "sku": contract["sku_name"],
                "provisioning": "Succeeded",
            },
            {
                "model": properties.get("model"),
                "sku": sku.get("name"),
                "provisioning": properties.get("provisioningState"),
            },
            state_passed,
        )
        no_route = (
            properties.get("spilloverDeploymentName") in (None, "")
            and properties.get("parentDeploymentName") in (None, "")
        )
        _gate(
            gates,
            f"{role}.no_spillover_or_parent",
            {"spillover": None, "parent": None},
            {
                "spillover": properties.get("spilloverDeploymentName"),
                "parent": properties.get("parentDeploymentName"),
            },
            no_route,
        )
        floor_passed = (
            isinstance(normalized.get("tpm"), int)
            and isinstance(normalized.get("rpm"), int)
            and normalized["tpm"] >= contract["minimum_tpm"]
            and normalized["rpm"] >= contract["minimum_rpm"]
        )
        _gate(
            gates,
            f"{role}.capacity_floor",
            {
                "minimum_tpm": contract["minimum_tpm"],
                "minimum_rpm": contract["minimum_rpm"],
            },
            {
                "tpm": normalized.get("tpm"),
                "rpm": normalized.get("rpm"),
            },
            floor_passed,
        )
        usage_passed = (
            usage.get("name") == contract["usage_name"]
            and usage.get("unit") == "Count"
            and isinstance(usage.get("current_value"), int)
            and isinstance(usage.get("limit"), int)
            and isinstance(usage.get("unallocated"), int)
            and usage["current_value"] >= 0
            and usage["limit"] > 0
            and usage["current_value"] <= usage["limit"]
            and usage["unallocated"]
            == usage["limit"] - usage["current_value"]
        )
        _gate(
            gates,
            f"{role}.subscription_usage_readback",
            contract["usage_name"],
            usage,
            usage_passed,
        )
        mutation = item.get("mutation")
        if mutation is None:
            mutation_passed = before == after
        elif isinstance(mutation, Mapping):
            before_arm = deepcopy(dict(before))
            after_arm = deepcopy(dict(after))
            before_arm.pop("normalized_rate_limits", None)
            after_arm.pop("normalized_rate_limits", None)
            changed = verify_capacity_change_allowlist(before_arm, after_arm)
            old_capacity = before.get("sku", {}).get("capacity")
            new_capacity = after.get("sku", {}).get("capacity")
            minimum = minimum_capacity_for_floor(
                old_capacity,
                current_tpm=before["normalized_rate_limits"]["tpm"],
                current_rpm=before["normalized_rate_limits"]["rpm"],
                minimum_tpm=contract["minimum_tpm"],
                minimum_rpm=contract["minimum_rpm"],
            )
            delta = new_capacity - old_capacity
            mutation_passed = (
                mutation.get("if_match") == before.get("etag")
                and mutation.get("api_version") == "2024-10-01"
                and mutation.get("patch_body")
                == build_capacity_patch(before, minimum)
                and new_capacity == minimum
                and delta <= usage.get("unallocated", -1)
                and delta <= model_capacity.get("available_capacity", -1)
                and bool(changed)
            )
        else:
            raise RecoveryError(f"{role} mutation record is malformed")
        _gate(
            gates,
            f"{role}.capacity_mutation",
            "none, or exact minimum increase under current ETag and quota",
            mutation,
            mutation_passed,
        )
        model_passed = (
            model_capacity.get("location") == contract["location"]
            and model_capacity.get("sku_name") == contract["sku_name"]
            and model_capacity.get("model")
            == {
                "format": contract["model_format"],
                "name": contract["model_name"],
                "version": contract["model_version"],
            }
            and isinstance(model_capacity.get("available_capacity"), (int, float))
            and not isinstance(model_capacity.get("available_capacity"), bool)
            and math.isfinite(model_capacity["available_capacity"])
        )
        _gate(
            gates,
            f"{role}.model_capacity_readback",
            "one exact model/version/SKU/location record",
            model_capacity,
            model_passed,
        )

    quiet = evidence.get("quiet_window")
    if not isinstance(quiet, Mapping):
        raise RecoveryError("quiet-window evidence is absent")
    expected_quiet_role_counts = {role: 0 for role in ROLE_CONTRACTS}
    quiet_passed = (
        isinstance(quiet.get("duration_seconds"), int)
        and quiet["duration_seconds"] >= 900
        and quiet.get("non_project_requests") == 0
        and quiet.get("complete_minute_elapsed") is True
        and quiet.get("query_succeeded") is True
        and quiet.get("deployment_dimension_verified") is True
        and quiet.get("per_role_request_counts")
        == expected_quiet_role_counts
    )
    _gate(
        gates,
        "continuous_quiet_window",
        {
            "duration_seconds": 900,
            "non_project_requests": 0,
            "complete_minute_elapsed": True,
            "query_succeeded": True,
            "deployment_dimension_verified": True,
            "per_role_request_counts": expected_quiet_role_counts,
        },
        {
            "duration_seconds": quiet.get("duration_seconds"),
            "non_project_requests": quiet.get("non_project_requests"),
            "complete_minute_elapsed": quiet.get("complete_minute_elapsed"),
            "query_succeeded": quiet.get("query_succeeded"),
            "deployment_dimension_verified": quiet.get(
                "deployment_dimension_verified"
            ),
            "per_role_request_counts": quiet.get(
                "per_role_request_counts"
            ),
        },
        quiet_passed,
    )

    monitor = evidence.get("azure_monitor")
    if not isinstance(monitor, Mapping):
        raise RecoveryError("Azure Monitor evidence is absent")
    monitor_roles = monitor.get("roles")
    if not isinstance(monitor_roles, Mapping):
        raise RecoveryError("Azure Monitor role evidence is absent")
    monitor_window_passed = (
        monitor.get("api") == "Microsoft.Insights/metrics"
        and monitor.get("interval") == "PT1M"
        and isinstance(monitor.get("window_duration_seconds"), int)
        and monitor["window_duration_seconds"] >= 3600
    )
    _gate(
        gates,
        "azure_monitor.window",
        {
            "api": "Microsoft.Insights/metrics",
            "interval": "PT1M",
            "window_duration_seconds": 3600,
        },
        {
            "api": monitor.get("api"),
            "interval": monitor.get("interval"),
            "window_duration_seconds": monitor.get(
                "window_duration_seconds"
            ),
        },
        monitor_window_passed,
    )
    for role, contract in ROLE_CONTRACTS.items():
        role_metrics = monitor_roles.get(role)
        if not isinstance(role_metrics, Mapping):
            raise RecoveryError(f"{role} Azure Monitor evidence is absent")
        count_fields = (
            "request_count_60m",
            "http_429_count_60m",
            "processed_prompt_tokens_60m",
            "generated_completion_tokens_60m",
            "quiet_window_request_count",
        )
        counts_valid = all(
            isinstance(role_metrics.get(field), int)
            and not isinstance(role_metrics.get(field), bool)
            and role_metrics[field] >= 0
            for field in count_fields
        )
        monitor_passed = (
            role_metrics.get("deployment") == contract["deployment"]
            and role_metrics.get("request_metric")
            == "AzureOpenAIRequests"
            and role_metrics.get("deployment_dimension_available") is True
            and role_metrics.get("query_succeeded") is True
            and counts_valid
            and role_metrics.get("quiet_window_request_count") == 0
        )
        _gate(
            gates,
            f"{role}.azure_monitor",
            {
                "deployment": contract["deployment"],
                "request_metric": "AzureOpenAIRequests",
                "deployment_dimension_available": True,
                "query_succeeded": True,
                "quiet_window_request_count": 0,
                "count_fields_nonnegative": True,
            },
            {
                key: role_metrics.get(key)
                for key in (
                    "deployment",
                    "request_metric",
                    "deployment_dimension_available",
                    "query_succeeded",
                    *count_fields,
                )
            },
            monitor_passed,
        )

    inventory = evidence.get("provider_capable_job_inventory")
    if not isinstance(inventory, Mapping):
        raise RecoveryError("provider-capable Job inventory is absent")
    jobs = inventory.get("jobs")
    if not isinstance(jobs, list):
        raise RecoveryError("provider-capable Job list is absent")
    names = [
        item.get("name")
        for item in jobs
        if isinstance(item, Mapping)
    ]
    jobs_valid = (
        len(names) == len(jobs)
        and all(isinstance(name, str) and name for name in names)
        and len(set(names)) == len(names)
        and all(
            isinstance(item.get("execution_count"), int)
            and not isinstance(item.get("execution_count"), bool)
            and item["execution_count"] >= 0
            for item in jobs
            if isinstance(item, Mapping)
        )
        and {
            "name": OLD_FORMAL_JOB_NAME,
            "execution_count": 1,
        }
        in jobs
    )
    inventory_passed = (
        inventory.get("identity_client_id") == IDENTITY_CLIENT_ID
        and inventory.get("all_jobs_with_review_identity_included") is True
        and inventory.get("role_assignment_readback_complete") is True
        and inventory.get("recovery_job_count") == 0
        and inventory.get("recovery_execution_count") == 0
        and jobs_valid
    )
    _gate(
        gates,
        "provider_capable_job_inventory",
        {
            "identity_client_id": IDENTITY_CLIENT_ID,
            "complete": True,
            "recovery_job_count": 0,
            "recovery_execution_count": 0,
            "old_formal_job_execution_count": 1,
        },
        {
            "identity_client_id": inventory.get("identity_client_id"),
            "all_jobs_with_review_identity_included": inventory.get(
                "all_jobs_with_review_identity_included"
            ),
            "role_assignment_readback_complete": inventory.get(
                "role_assignment_readback_complete"
            ),
            "recovery_job_count": inventory.get("recovery_job_count"),
            "recovery_execution_count": inventory.get(
                "recovery_execution_count"
            ),
            "jobs": jobs,
        },
        inventory_passed,
    )

    state = evidence.get("blob_and_execution_state")
    if not isinstance(state, Mapping):
        raise RecoveryError("Blob/execution state evidence is absent")
    expected_state = {
        "source_object_count": 8,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "generation_execution_count": 1,
        "generation_execution": GENERATION_EXECUTION,
        "generation_execution_status": "Succeeded",
        "old_result_object_count": 0,
        "old_formal_lock_sha256": OLD_FORMAL_LOCK_SHA256,
        "old_terminal_archive_sha256": OLD_TERMINAL_ARCHIVE_SHA256,
        "old_formal_execution_count": 1,
        "old_formal_execution": OLD_FORMAL_EXECUTION,
        "old_formal_execution_status": "Failed",
        "recovery_lock_exists": False,
        "recovery_result_object_count": 0,
        "recovery_job_count": 0,
        "recovery_execution_count": 0,
    }
    observed_state = {key: state.get(key) for key in expected_state}
    _gate(
        gates,
        "blob_and_execution_state",
        expected_state,
        observed_state,
        observed_state == expected_state,
    )
    return gates


def build_capacity_certificate(evidence: Mapping[str, Any]) -> dict[str, Any]:
    gates = evaluate_capacity_evidence(evidence)
    passed = all(item["passed"] for item in gates)
    certificate: dict[str, Any] = {
        "artifact": "phase1_0d_transport_capacity_certificate",
        "schema_version": CERTIFICATE_SCHEMA_VERSION,
        "authority": _expected_authority_binding(),
        "protected_bytes": _expected_protected_binding(),
        "source_gate_and_images": _expected_source_binding(),
        "old_terminal_state": _expected_old_terminal_binding(),
        "provider_calls": {
            "count": evidence.get("provider_calls"),
            "method": evidence.get("provider_calls_method"),
        },
        "evidence": deepcopy(dict(evidence)),
        "mechanical_gates": gates,
        "capacity_gate_passed": passed,
        "terminal_state": (
            None
            if passed
            else "BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY"
        ),
        "certificate_sha256_definition": (
            "certificate_payload_sha256 hashes canonical UTF-8 JSON with "
            "certificate_payload_sha256 omitted; artifact_manifest.json records "
            "the SHA-256 of the complete certificate file"
        ),
    }
    certificate["certificate_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(certificate)
    )
    return certificate


def _expected_authority_binding() -> dict[str, Any]:
    return {
        "path": AUTHORITY_PATH,
        "sha256": AUTHORITY_SHA256,
        "starting_commit": STARTING_COMMIT,
        "starting_tree": STARTING_TREE,
        "required_ancestor": REQUIRED_ANCESTOR,
    }


def _expected_protected_binding() -> dict[str, Any]:
    return {
        "v1": {
            "file_count": V1_PROTECTED_FILE_COUNT,
            "rollup_sha256": V1_PROTECTED_ROLLUP,
        },
        "v2": {
            "file_count": V2_PROTECTED_FILE_COUNT,
            "rollup_sha256": V2_PROTECTED_ROLLUP,
            "manifest_sha256": V2_PROTECTED_MANIFEST_SHA256,
        },
    }


def _expected_source_binding() -> dict[str, Any]:
    return {
        "generation_run_id": GENERATION_RUN_ID,
        "generation_prefix": GENERATION_PREFIX,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "qualification_run_id": QUALIFICATION_RUN_ID,
        "qualification_receipt_sha256": QUALIFICATION_RECEIPT_SHA256,
        "qualification_manifest_sha256": QUALIFICATION_MANIFEST_SHA256,
        "smoke_run_id": SMOKE_RUN_ID,
        "smoke_receipt_sha256": SMOKE_RECEIPT_SHA256,
        "smoke_manifest_sha256": SMOKE_MANIFEST_SHA256,
        "generation_image_digest": GENERATION_IMAGE_DIGEST,
        "v1_review_image_digest": V1_REVIEW_IMAGE_DIGEST,
        "v2_review_image_digest": V2_REVIEW_IMAGE_DIGEST,
        "v2_review_image_commit": V2_REVIEW_IMAGE_COMMIT,
    }


def _expected_old_terminal_binding() -> dict[str, Any]:
    return {
        "formal_run_id": OLD_FORMAL_RUN_ID,
        "formal_execution": OLD_FORMAL_EXECUTION,
        "formal_lock_sha256": OLD_FORMAL_LOCK_SHA256,
        "terminal_archive_sha256": OLD_TERMINAL_ARCHIVE_SHA256,
        "result_prefix": OLD_RESULT_PREFIX,
        "result_object_count": 0,
    }


def verify_capacity_certificate(
    certificate: Mapping[str, Any],
    *,
    expected_request_body_rollups: Mapping[str, Any] | None = None,
    require_request_body_rollups: bool = False,
) -> None:
    _require_exact_keys(
        certificate,
        {
            "artifact",
            "schema_version",
            "authority",
            "protected_bytes",
            "source_gate_and_images",
            "old_terminal_state",
            "provider_calls",
            "evidence",
            "mechanical_gates",
            "capacity_gate_passed",
            "terminal_state",
            "certificate_sha256_definition",
            "certificate_payload_sha256",
        },
        "capacity certificate",
    )
    if certificate.get("artifact") != "phase1_0d_transport_capacity_certificate":
        raise RecoveryError("not a transport capacity certificate")
    if certificate.get("schema_version") != CERTIFICATE_SCHEMA_VERSION:
        raise RecoveryError("capacity certificate schema differs")
    expected_payload_sha = certificate.get("certificate_payload_sha256")
    if not isinstance(expected_payload_sha, str) or not SHA256.fullmatch(
        expected_payload_sha
    ):
        raise RecoveryError("capacity certificate payload hash is malformed")
    unhashed = dict(certificate)
    del unhashed["certificate_payload_sha256"]
    if sha256_bytes(canonical_json_bytes(unhashed)) != expected_payload_sha:
        raise RecoveryError("capacity certificate payload hash differs")
    fixed_bindings = (
        ("authority", _expected_authority_binding()),
        ("protected_bytes", _expected_protected_binding()),
        ("source_gate_and_images", _expected_source_binding()),
        ("old_terminal_state", _expected_old_terminal_binding()),
    )
    for key, expected in fixed_bindings:
        if certificate.get(key) != expected:
            raise RecoveryError(f"capacity certificate {key} binding differs")
    evidence = certificate.get("evidence")
    if not isinstance(evidence, Mapping):
        raise RecoveryError("capacity certificate evidence is absent")
    expected_provider_calls = {
        "count": evidence.get("provider_calls"),
        "method": evidence.get("provider_calls_method"),
    }
    if (
        certificate.get("provider_calls") != expected_provider_calls
        or expected_provider_calls["count"] != 0
        or not isinstance(expected_provider_calls["method"], str)
        or not expected_provider_calls["method"]
    ):
        raise RecoveryError("capacity certificate provider-call binding differs")
    if require_request_body_rollups and expected_request_body_rollups is None:
        raise RecoveryError("independent request-body rollups are required")
    rollup_gates: list[dict[str, Any]] = []
    _validate_rollups(
        evidence.get("request_body_rollups"),
        rollup_gates,
        expected_rollups=expected_request_body_rollups,
    )
    if not all(item["passed"] for item in rollup_gates):
        raise RecoveryError("capacity certificate request-body rollups differ")
    gates = evaluate_capacity_evidence(evidence)
    if gates != certificate.get("mechanical_gates"):
        raise RecoveryError("capacity certificate gates do not recompute")
    passed = all(item["passed"] for item in gates)
    if certificate.get("capacity_gate_passed") is not passed:
        raise RecoveryError("capacity_gate_passed does not match the gates")
    expected_terminal = (
        None if passed else "BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY"
    )
    if certificate.get("terminal_state") != expected_terminal:
        raise RecoveryError("capacity certificate terminal state differs")


def verify_capacity_evidence_freshness(
    certificate: Mapping[str, Any],
    max_age_seconds: int,
    *,
    now_utc: dt.datetime | None = None,
) -> None:
    max_age = _positive_integer(
        max_age_seconds, "capacity evidence maximum age"
    )
    evidence = certificate.get("evidence")
    observation = (
        evidence.get("observation")
        if isinstance(evidence, Mapping)
        else None
    )
    if not isinstance(observation, Mapping):
        raise RecoveryError("capacity observation timestamps are absent")
    material_keys = (
        "certificate_observed_at_utc",
        "control_plane_readback_at_utc",
        "monitor_window_end_utc",
        "private_state_readback_at_utc",
        "job_inventory_readback_at_utc",
    )
    observed = [
        _parse_utc_second(observation.get(key), key) for key in material_keys
    ]
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise RecoveryError("freshness reference time must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)
    if any(timestamp > now + dt.timedelta(seconds=30) for timestamp in observed):
        raise RecoveryError("capacity evidence timestamp is in the future")
    oldest_age = (now - min(observed)).total_seconds()
    if oldest_age > max_age:
        raise RecoveryError(
            f"capacity evidence is stale ({oldest_age:.0f}s > {max_age}s)"
        )


def _write_create_only(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise RecoveryError(f"refusing to overwrite {path}") from exc
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def seal_capacity_certificate(
    evidence: Mapping[str, Any],
    output_dir: Path,
    *,
    review_form_path: Path,
    project_root: Path = REPO_ROOT,
) -> dict[str, str]:
    expected_rollups = request_body_rollups(review_form_path, project_root)
    if evidence.get("request_body_rollups") != expected_rollups:
        raise RecoveryError(
            "capacity evidence request-body rollups do not match independent "
            "source-form reconstruction"
        )
    certificate = build_capacity_certificate(evidence)
    verify_capacity_certificate(
        certificate,
        expected_request_body_rollups=expected_rollups,
        require_request_body_rollups=True,
    )
    certificate_bytes = canonical_json_bytes(certificate)
    certificate_path = output_dir / CAPACITY_CERTIFICATE_NAME
    manifest_path = output_dir / CAPACITY_MANIFEST_NAME
    _write_create_only(certificate_path, certificate_bytes)
    certificate_sha = sha256_bytes(certificate_bytes)
    manifest = {
        "artifact": "phase1_0d_transport_capacity_certificate_manifest",
        "schema_version": CERTIFICATE_MANIFEST_SCHEMA_VERSION,
        "manifest_written_last": True,
        "capacity_gate_passed": certificate["capacity_gate_passed"],
        "terminal_state": certificate["terminal_state"],
        "members": [
            {
                "path": CAPACITY_CERTIFICATE_NAME,
                "sha256": certificate_sha,
            }
        ],
    }
    manifest_bytes = canonical_json_bytes(manifest)
    _write_create_only(manifest_path, manifest_bytes)
    verify_capacity_certificate(
        load_json(certificate_path),
        expected_request_body_rollups=expected_rollups,
        require_request_body_rollups=True,
    )
    if sha256_bytes(certificate_path.read_bytes()) != certificate_sha:
        raise RecoveryError("certificate changed after create-only write")
    if load_json(manifest_path) != manifest:
        raise RecoveryError("certificate manifest changed after create-only write")
    return {
        "certificate_sha256": certificate_sha,
        "manifest_sha256": sha256_bytes(manifest_bytes),
    }


def verify_capacity_pack(
    certificate_path: Path,
    manifest_path: Path,
    *,
    review_form_path: Path | None = None,
    project_root: Path = REPO_ROOT,
    require_request_body_rollups: bool = False,
) -> dict[str, Any]:
    certificate = load_json(certificate_path)
    manifest = load_json(manifest_path)
    if certificate_path.read_bytes() != canonical_json_bytes(certificate):
        raise RecoveryError("capacity certificate bytes are not canonical JSON")
    if manifest_path.read_bytes() != canonical_json_bytes(manifest):
        raise RecoveryError("capacity manifest bytes are not canonical JSON")
    expected_rollups = (
        request_body_rollups(review_form_path, project_root)
        if review_form_path is not None
        else None
    )
    verify_capacity_certificate(
        certificate,
        expected_request_body_rollups=expected_rollups,
        require_request_body_rollups=require_request_body_rollups,
    )
    expected_manifest = {
        "artifact": "phase1_0d_transport_capacity_certificate_manifest",
        "schema_version": CERTIFICATE_MANIFEST_SCHEMA_VERSION,
        "manifest_written_last": True,
        "capacity_gate_passed": certificate["capacity_gate_passed"],
        "terminal_state": certificate["terminal_state"],
        "members": [
            {
                "path": CAPACITY_CERTIFICATE_NAME,
                "sha256": sha256_bytes(certificate_path.read_bytes()),
            }
        ],
    }
    if manifest != expected_manifest:
        raise RecoveryError("capacity certificate manifest differs")
    return {
        "certificate": certificate,
        "certificate_sha256": sha256_bytes(certificate_path.read_bytes()),
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
    }


def recovery_result_prefix(run_id: str) -> str:
    if not RUN_ID.fullmatch(run_id):
        raise RecoveryError("recovery run ID must be an exact UTC stamp")
    return f"{RECOVERY_RESULT_ROOT}/{run_id}"


def recovery_command(run_id: str) -> str:
    result_prefix = recovery_result_prefix(run_id)
    return (
        f"timeout --signal=TERM --kill-after=60s {REVIEW_TIMEOUT_SECONDS}s "
        "python /workspace/scripts/run_phase1_0d_semantic_review_v2.py review "
        "--project-root /workspace --out-dir /workspace/runtime/results "
        f"--run-id {run_id} --client-id {IDENTITY_CLIENT_ID} "
        f"--blob-account {BLOB_ACCOUNT} --blob-container {BLOB_CONTAINER} "
        f"--code-commit {V2_REVIEW_IMAGE_COMMIT} "
        f"--image-digest {V2_REVIEW_IMAGE_DIGEST} "
        f"--execution-timeout-seconds {REVIEW_TIMEOUT_SECONDS} "
        "--qualification-receipt-prefix "
        f"phase1-0d-semantic-review-v2/qualification/{QUALIFICATION_RUN_ID} "
        "--gate-receipt-prefix "
        f"phase1-0d-semantic-review-v2/smoke/{SMOKE_RUN_ID} "
        f"--gate-manifest-sha256 {SMOKE_MANIFEST_SHA256} "
        f"--gate-receipt-sha256 {SMOKE_RECEIPT_SHA256} "
        f"--pack-blob-prefix {GENERATION_PREFIX} "
        f"--source-manifest-sha256 {SOURCE_MANIFEST_SHA256} "
        f"--out-blob-prefix {result_prefix}"
    )


def recovery_environment(run_id: str) -> list[dict[str, str]]:
    recovery_result_prefix(run_id)
    return [
        {"name": "RESULTS_DIR", "value": "/workspace/runtime/results"},
        {"name": "TMPDIR", "value": "/workspace/runtime/cache/tmp"},
        {"name": "PYTHONUNBUFFERED", "value": "1"},
        {"name": "AZURE_CLIENT_ID", "value": IDENTITY_CLIENT_ID},
        {"name": "JSPACE_BLOB_ACCOUNT", "value": BLOB_ACCOUNT},
        {"name": "JSPACE_BLOB_CONTAINER", "value": BLOB_CONTAINER},
        {"name": "JSPACE_REVIEW_RUN_ID", "value": run_id},
        {"name": "JSPACE_REVIEW_MODE", "value": "review"},
        {"name": "JSPACE_CODE_COMMIT", "value": V2_REVIEW_IMAGE_COMMIT},
        {"name": "JSPACE_IMAGE_DIGEST", "value": V2_REVIEW_IMAGE_DIGEST},
        {"name": "JSPACE_GENERATION_RUN_ID", "value": GENERATION_RUN_ID},
        {
            "name": "JSPACE_SOURCE_MANIFEST_SHA256",
            "value": SOURCE_MANIFEST_SHA256,
        },
        {
            "name": "JSPACE_QUALIFICATION_RECEIPT_SHA256",
            "value": "",
        },
        {
            "name": "JSPACE_QUALIFICATION_MANIFEST_SHA256",
            "value": "",
        },
        {
            "name": "JSPACE_SMOKE_RECEIPT_SHA256",
            "value": SMOKE_RECEIPT_SHA256,
        },
        {
            "name": "JSPACE_SMOKE_MANIFEST_SHA256",
            "value": SMOKE_MANIFEST_SHA256,
        },
    ]


def build_recovery_job(
    *,
    run_id: str,
    job_name: str,
    launcher_commit: str,
    capacity_certificate_sha256: str,
    capacity_manifest_sha256: str,
    identity_resource_id: str,
    environment_resource_id: str,
) -> dict[str, Any]:
    if not JOB_NAME.fullmatch(job_name):
        raise RecoveryError("recovery Job name does not match the frozen namespace")
    if not SHA1.fullmatch(launcher_commit):
        raise RecoveryError("launcher commit must be a full SHA-1")
    for name, digest in (
        ("capacity certificate", capacity_certificate_sha256),
        ("capacity manifest", capacity_manifest_sha256),
    ):
        if not SHA256.fullmatch(digest):
            raise RecoveryError(f"{name} SHA-256 is malformed")
    if not identity_resource_id or not environment_resource_id:
        raise RecoveryError("identity/environment resource IDs are required")
    return {
        "location": "southeastasia",
        "identity": {
            "type": "UserAssigned",
            "userAssignedIdentities": {identity_resource_id: {}},
        },
        "tags": {
            "project": "jspace-observation",
            "phase": "1.0D",
            "track": "B",
            "round": "v2-transport-recovery",
            "stage": "semantic-review-recovery",
            "run-id": run_id,
            "project-sha": V2_REVIEW_IMAGE_COMMIT,
            "launcher-sha": launcher_commit,
            "image-digest": V2_REVIEW_IMAGE_DIGEST,
            "generation-run-id": GENERATION_RUN_ID,
            "source-manifest-sha256": SOURCE_MANIFEST_SHA256,
            "qualification-receipt-sha256": QUALIFICATION_RECEIPT_SHA256,
            "qualification-manifest-sha256": QUALIFICATION_MANIFEST_SHA256,
            "smoke-receipt-sha256": SMOKE_RECEIPT_SHA256,
            "smoke-manifest-sha256": SMOKE_MANIFEST_SHA256,
            "capacity-certificate-sha256": capacity_certificate_sha256,
            "capacity-manifest-sha256": capacity_manifest_sha256,
        },
        "properties": {
            "environmentId": environment_resource_id,
            "workloadProfileName": WORKLOAD_PROFILE_NAME,
            "configuration": {
                "triggerType": "Manual",
                "replicaTimeout": REPLICA_TIMEOUT_SECONDS,
                "replicaRetryLimit": 0,
                "manualTriggerConfig": {
                    "replicaCompletionCount": 1,
                    "parallelism": 1,
                },
                "registries": [
                    {
                        "server": ACR_LOGIN_SERVER,
                        "identity": identity_resource_id,
                    }
                ],
            },
            "template": {
                "containers": [
                    {
                        "name": "review-v2",
                        "image": V2_REVIEW_IMAGE_REF,
                        "command": ["/bin/sh"],
                        "args": ["-lc", recovery_command(run_id)],
                        "env": recovery_environment(run_id),
                        "resources": {"cpu": 2.0, "memory": "4Gi"},
                    }
                ]
            },
        },
    }


def _normalize_job_readback(job: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(job))
    normalized.pop("id", None)
    normalized.pop("name", None)
    normalized.pop("type", None)
    normalized.pop("resourceGroup", None)
    normalized.pop("systemData", None)
    properties = normalized.get("properties")
    if isinstance(properties, dict):
        for key in (
            "eventStreamEndpoint",
            "outboundIpAddresses",
            "provisioningState",
            "runningStatus",
        ):
            properties.pop(key, None)
        template = properties.get("template")
        if isinstance(template, dict):
            template.pop("initContainers", None)
            template.pop("volumes", None)
            containers = template.get("containers")
            if isinstance(containers, list):
                for container in containers:
                    if isinstance(container, dict):
                        container.pop("imageType", None)
                        resources = container.get("resources")
                        if isinstance(resources, dict):
                            resources.pop("ephemeralStorage", None)
        configuration = properties.get("configuration")
        if isinstance(configuration, dict):
            for key in (
                "dapr",
                "eventTriggerConfig",
                "identitySettings",
                "scheduleTriggerConfig",
                "secrets",
            ):
                configuration.pop(key, None)
            registries = configuration.get("registries")
            if isinstance(registries, list):
                for registry in registries:
                    if isinstance(registry, dict):
                        registry.pop("username", None)
                        registry.pop("passwordSecretRef", None)
    identity = normalized.get("identity")
    if isinstance(identity, dict):
        bindings = identity.get("userAssignedIdentities")
        if isinstance(bindings, dict):
            for resource_id in list(bindings):
                bindings[resource_id] = {}
    return normalized


def verify_recovery_job(
    job: Mapping[str, Any],
    *,
    run_id: str,
    job_name: str,
    launcher_commit: str,
    capacity_certificate_sha256: str,
    capacity_manifest_sha256: str,
    identity_resource_id: str,
    environment_resource_id: str,
) -> None:
    if job.get("name") != job_name:
        raise RecoveryError("recovery Job readback name differs")
    expected = build_recovery_job(
        run_id=run_id,
        job_name=job_name,
        launcher_commit=launcher_commit,
        capacity_certificate_sha256=capacity_certificate_sha256,
        capacity_manifest_sha256=capacity_manifest_sha256,
        identity_resource_id=identity_resource_id,
        environment_resource_id=environment_resource_id,
    )
    if _normalize_job_readback(job) != expected:
        raise RecoveryError("recovery Job readback differs from the frozen contract")


def build_recovery_lock(
    *,
    run_id: str,
    job_name: str,
    launcher_commit: str,
    capacity_certificate_sha256: str,
    capacity_manifest_sha256: str,
    request_body_rollups_value: Mapping[str, Any],
) -> dict[str, Any]:
    if not JOB_NAME.fullmatch(job_name) or not SHA1.fullmatch(launcher_commit):
        raise RecoveryError("recovery lock Job/launcher identity is malformed")
    for digest in (capacity_certificate_sha256, capacity_manifest_sha256):
        if not SHA256.fullmatch(digest):
            raise RecoveryError("recovery lock capacity identity is malformed")
    gates: list[dict[str, Any]] = []
    _validate_rollups(request_body_rollups_value, gates)
    if not all(item["passed"] for item in gates):
        raise RecoveryError("recovery lock request-body rollups do not pass")
    return {
        "artifact": "phase1_0d_transport_recovery_formal_review_lock",
        "schema_version": LOCK_SCHEMA_VERSION,
        "authority_prompt_sha256": AUTHORITY_SHA256,
        "starting_commit": STARTING_COMMIT,
        "launcher_commit": launcher_commit,
        "recovery_run_id": run_id,
        "job_name": job_name,
        "review_image_digest": V2_REVIEW_IMAGE_DIGEST,
        "review_image_commit": V2_REVIEW_IMAGE_COMMIT,
        "source": {
            "generation_run_id": GENERATION_RUN_ID,
            "prefix": GENERATION_PREFIX,
            "manifest_sha256": SOURCE_MANIFEST_SHA256,
        },
        "gate": {
            "qualification_run_id": QUALIFICATION_RUN_ID,
            "qualification_receipt_sha256": QUALIFICATION_RECEIPT_SHA256,
            "qualification_manifest_sha256": QUALIFICATION_MANIFEST_SHA256,
            "smoke_run_id": SMOKE_RUN_ID,
            "smoke_receipt_sha256": SMOKE_RECEIPT_SHA256,
            "smoke_manifest_sha256": SMOKE_MANIFEST_SHA256,
        },
        "protected_rollups": {
            "v1": V1_PROTECTED_ROLLUP,
            "v2": V2_PROTECTED_ROLLUP,
        },
        "profile_sha256": PROFILE_SHA256,
        "old_formal": {
            "run_id": OLD_FORMAL_RUN_ID,
            "execution": OLD_FORMAL_EXECUTION,
            "lock_sha256": OLD_FORMAL_LOCK_SHA256,
            "terminal_archive_sha256": OLD_TERMINAL_ARCHIVE_SHA256,
            "result_prefix": OLD_RESULT_PREFIX,
            "result_object_count": 0,
        },
        "capacity": {
            "certificate_sha256": capacity_certificate_sha256,
            "manifest_sha256": capacity_manifest_sha256,
            "capacity_gate_passed": True,
        },
        "request_body_rollups": deepcopy(dict(request_body_rollups_value)),
        "result_prefix": recovery_result_prefix(run_id),
    }


def classify_start(
    before_execution_names: Sequence[str],
    response_execution_name: str | None,
    after_execution_names: Sequence[str],
) -> dict[str, Any]:
    before = list(before_execution_names)
    after = list(after_execution_names)
    if before:
        raise RecoveryError("recovery Job was not inert before its sole start")
    if len(after) != 1:
        return {
            "state": "BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY",
            "execution_name": None,
            "start_may_be_retried": False,
        }
    established = after[0]
    if response_execution_name not in (None, "", established):
        return {
            "state": "BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY",
            "execution_name": None,
            "start_may_be_retried": False,
        }
    return {
        "state": "EXECUTION_ESTABLISHED",
        "execution_name": established,
        "start_may_be_retried": False,
    }


def verify_success_members(names: Sequence[str]) -> None:
    observed = set(names)
    missing = SUCCESS_REQUIRED_MEMBERS - observed
    if missing:
        raise RecoveryError(
            f"successful result bundle lacks members: {sorted(missing)}"
        )
    if "artifact_manifest.json" not in observed:
        raise RecoveryError("successful result bundle lacks its outer manifest")


def verify_terminal_archive_members(names: Sequence[str]) -> None:
    observed = set(names)
    expected = TERMINAL_ARCHIVE_MEMBERS | {"artifact_manifest.json"}
    if observed != expected:
        raise RecoveryError(
            f"terminal archive membership differs: "
            f"missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)}"
        )


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    rollups = subparsers.add_parser("request-rollups")
    rollups.add_argument("--review-form", required=True)
    rollups.add_argument("--project-root", default=str(REPO_ROOT))
    rollups.add_argument("--output", default="")

    normalize = subparsers.add_parser("normalize-deployment")
    normalize.add_argument("--role", choices=tuple(ROLE_CONTRACTS), required=True)
    normalize.add_argument("--deployment-json", required=True)
    normalize.add_argument("--output", required=True)

    seal = subparsers.add_parser("seal-certificate")
    seal.add_argument("--evidence", required=True)
    seal.add_argument("--output-dir", required=True)
    seal.add_argument("--review-form", required=True)
    seal.add_argument("--project-root", default=str(REPO_ROOT))

    verify = subparsers.add_parser("verify-certificate")
    verify.add_argument("--certificate", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--review-form", default="")
    verify.add_argument("--project-root", default=str(REPO_ROOT))
    verify.add_argument("--require-passing", action="store_true")

    freshness = subparsers.add_parser("verify-freshness")
    freshness.add_argument("--certificate", required=True)
    freshness.add_argument("--max-age-seconds", required=True, type=int)

    args = parser.parse_args(argv)
    try:
        if args.command == "request-rollups":
            result = request_body_rollups(
                Path(args.review_form), Path(args.project_root)
            )
            if args.output:
                _write_create_only(Path(args.output), canonical_json_bytes(result))
            else:
                sys.stdout.buffer.write(canonical_json_bytes(result))
        elif args.command == "normalize-deployment":
            contract = ROLE_CONTRACTS[args.role]
            result = sanitize_deployment(
                args.role,
                load_json(Path(args.deployment_json)),
                account=contract["account"],
                resource_group=contract["resource_group"],
                endpoint_host=contract["endpoint_host"],
                location=contract["location"],
            )
            _write_create_only(Path(args.output), canonical_json_bytes(result))
        elif args.command == "seal-certificate":
            result = seal_capacity_certificate(
                load_json(Path(args.evidence)),
                Path(args.output_dir),
                review_form_path=Path(args.review_form),
                project_root=Path(args.project_root),
            )
            sys.stdout.buffer.write(canonical_json_bytes(result))
        elif args.command == "verify-certificate":
            result = verify_capacity_pack(
                Path(args.certificate),
                Path(args.manifest),
                review_form_path=(
                    Path(args.review_form) if args.review_form else None
                ),
                project_root=Path(args.project_root),
                require_request_body_rollups=args.require_passing,
            )
            if (
                args.require_passing
                and result["certificate"]["capacity_gate_passed"] is not True
            ):
                raise RecoveryError("capacity certificate does not pass")
            sys.stdout.buffer.write(
                canonical_json_bytes(
                    {
                        "capacity_gate_passed": result["certificate"][
                            "capacity_gate_passed"
                        ],
                        "certificate_sha256": result["certificate_sha256"],
                        "manifest_sha256": result["manifest_sha256"],
                    }
                )
            )
        elif args.command == "verify-freshness":
            certificate = load_json(Path(args.certificate))
            if Path(args.certificate).read_bytes() != canonical_json_bytes(
                certificate
            ):
                raise RecoveryError(
                    "capacity certificate bytes are not canonical JSON"
                )
            verify_capacity_evidence_freshness(
                certificate, args.max_age_seconds
            )
            sys.stdout.buffer.write(
                canonical_json_bytes({"capacity_evidence_fresh": True})
            )
    except RecoveryError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
