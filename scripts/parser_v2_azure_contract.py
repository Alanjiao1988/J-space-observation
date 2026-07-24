#!/usr/bin/env python3
"""Fail-closed Azure control-plane helpers for parser-v2 evaluation tooling."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit


PROJECT_ROOT = Path(
    os.environ.get("JSPACE_PV2_PROJECT_ROOT", Path(__file__).resolve().parents[1])
).resolve()
CORE_PATH = Path(
    os.environ.get(
        "JSPACE_PV2_CORE_PATH",
        PROJECT_ROOT
        / "src"
        / "jspace_observation"
        / "parser_v2_locked_evaluation.py",
    )
).resolve()
BUILD_PROVENANCE_SCHEMA_VERSION = "phase1-parser-v2-build-provenance/v4"
BUILD_SOURCE_BINDING_SCHEMA_VERSION = (
    "phase1-parser-v2-build-source-binding/v2"
)
BUILD_PROVENANCE_ARGUMENT = "BUILD_PROVENANCE_SHA256"
BASE_IMAGE_ARGUMENT = "PYTHON_BASE_IMAGE"
BUILD_PROVENANCE_LABEL = (
    "org.opencontainers.image.build-provenance-sha256"
)
BUILD_DOCKERFILE_PATH = "Dockerfile.parser-v2-eval"
BUILD_DEPENDENCY_PATHS = ("requirements-parser-v2-eval.txt",)
BUILD_PLATFORM = {"os": "Linux", "architecture": "amd64"}
BUILD_SOURCE_REPOSITORY_URL = (
    "https://github.com/Alanjiao1988/J-space-observation.git"
)
BUILD_RUN_REQUEST_FIELDS = frozenset(
    {
        "type",
        "imageNames",
        "dockerFilePath",
        "platform",
        "arguments",
        "isPushEnabled",
        "noCache",
        "sourceLocation",
        "isArchiveEnabled",
        "credentials",
        "agentConfiguration",
        "timeout",
    }
)
BUILD_OUTPUT_IMAGE_FIELDS = frozenset(
    {"registry", "repository", "tag", "digest"}
)
OCI_VERIFICATION_SCHEMA_VERSION = (
    "phase1-parser-v2-oci-verification/v1"
)
COORDINATION_BINDING_SCHEMA_VERSION = (
    "phase1-parser-v2-dns-coordination/v1"
)
CLAIM_DOMAIN_SCHEMA_VERSION = "phase1-parser-v2-claim-domain/v1"
CLAIM_ENVELOPE_SCHEMA_VERSION = "phase1-parser-v2-dns-claim/v1"
CLAIM_KINDS = frozenset({"build", "launch", "dispatch"})
PRIVATE_DNS_RECORD_SET_API_VERSION = "2024-06-01"
MANAGEMENT_LOCK_API_VERSION = "2016-09-01"
TXT_CHUNK_DATA_LENGTH = 192
TXT_CHUNK_LIMIT = 32
TXT_PAYLOAD_LIMIT = 4096
TXT_CHUNK_VERSION = "v1"
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_GIT_OID_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_REPOSITORY_PATTERN = re.compile(
    r"^[a-z0-9]+(?:(?:[._-]|/)[a-z0-9]+)*$"
)
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TASK_RUN_NAME_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{3,48}[a-z0-9])$", re.ASCII
)
_AZURE_LOCATION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$", re.ASCII)
_ARM_API_VERSION_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:-preview)?$", re.ASCII
)
_ARM_PATH_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9._()-]+$", re.ASCII)
_ARM_QUERY_NAME_PATTERN = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9._-]*|\$[A-Za-z][A-Za-z0-9._-]*)$",
    re.ASCII,
)
_ARM_QUERY_VALUE_CHARACTER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]$", re.ASCII)
_ARM_CONTINUATION_QUERY_PARAMETERS = frozenset(
    {"$skiptoken", "$skipToken", "skipToken", "continuationToken"}
)
_DNS_ZONE_NAME_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
    re.ASCII,
)
_DNS_RECORD_NAME_PATTERN = re.compile(
    r"^(?:build|launch|dispatch)-[0-9a-f]{32}\.[0-9a-f]{32}$",
    re.ASCII,
)
_OPAQUE_AUTHORIZATION_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{15,127}$", re.ASCII
)
_LOCK_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._()-]{1,90}$", re.ASCII)
_AZURE_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII | re.IGNORECASE,
)
_OPAQUE_INTERNAL_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9+/]{16,252}={0,2}$", re.ASCII
)
_COORDINATION_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "zone_name",
        "zone_resource_id",
        "zone_location",
        "zone_internal_id",
        "private_dns_api_version",
        "record_ttl",
        "expected_vnet_link_count",
        "lock_name",
        "lock_resource_id",
        "lock_level",
        "management_lock_api_version",
    }
)
_BUILD_CLAIM_FIELDS = frozenset(
    {
        "claim_nonce",
        "source_commit",
        "task_run_name",
        "staging_tag",
        "task_run_resource_id_sha256",
        "build_run_request_sha256",
        "source_binding_sha256",
        "build_provenance_sha256",
        "coordination_binding_sha256",
    }
)
_LAUNCH_CLAIM_FIELDS = frozenset(
    {
        "authorization_id",
        "claim_nonce",
        "stage",
        "mode",
        "retry_kind",
        "execution_id",
        "job_name",
        "job_resource_id_sha256",
        "job_body_sha256",
        "job_projection_sha256",
        "baseline_execution_membership_sha256",
        "baseline_execution_count",
        "state_receipt_sha256",
        "config_sha256",
        "image_binding_sha256",
        "helper_snapshot_set_sha256",
        "implementation_manifest_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "azure_destination_sha256",
        "launcher_sha256",
        "launcher_git_blob_oid",
        "coordination_binding_sha256",
    }
)
_DISPATCH_CLAIM_FIELDS = frozenset(
    {
        "authorization_id",
        "claim_nonce",
        "execution_id",
        "launch_record_name",
        "launch_domain_sha256",
        "launch_record_etag_sha256",
        "launch_payload_sha256",
        "job_name",
        "job_resource_id_sha256",
        "job_body_sha256",
        "job_projection_sha256",
        "baseline_execution_membership_sha256",
        "baseline_execution_count",
        "state_receipt_sha256",
        "config_sha256",
        "image_binding_sha256",
        "helper_snapshot_set_sha256",
        "implementation_manifest_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "azure_destination_sha256",
        "coordination_binding_sha256",
    }
)


class AzureContractError(RuntimeError):
    """Raised when an Azure response differs from the immutable contract."""


def _load_core() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_jspace_parser_v2_azure_contract_core", CORE_PATH
    )
    if spec is None or spec.loader is None:
        raise AzureContractError("cannot load locked-evaluation core")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_azure_value(value: Any) -> Any:
    """Strip PowerShell/Git-Bash CR characters from every Azure scalar."""
    if isinstance(value, str):
        return value.replace("\r", "")
    if isinstance(value, list):
        return [normalize_azure_value(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = normalize_azure_value(key)
            if normalized_key in normalized:
                raise AzureContractError(
                    "CR normalization produced a duplicate Azure field"
                )
            normalized[normalized_key] = normalize_azure_value(item)
        return normalized
    return value


def _load_json(path: str | Path, name: str) -> Any:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AzureContractError(f"{name} is not valid UTF-8 JSON") from None
    return normalize_azure_value(value)


def _canonical_bytes(value: Any) -> bytes:
    def validate(item: Any) -> None:
        if item is None or type(item) in {bool, int, str}:
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise AzureContractError("JSON contains a non-finite number")
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise AzureContractError("JSON contains a non-string key")
                validate(child)
            return
        raise AzureContractError("JSON contains an unsupported value type")

    validate(value)
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_bytes(_canonical_bytes(value))


def _canonical_ascii_bytes(value: Any) -> bytes:
    def validate(item: Any) -> None:
        if item is None or type(item) in {bool, int}:
            return
        if type(item) is str:
            if (
                not item.isascii()
                or any(ord(character) < 0x20 or ord(character) == 0x7F for character in item)
            ):
                raise AzureContractError("claim JSON contains a non-ASCII/control value")
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str or not key.isascii():
                    raise AzureContractError("claim JSON contains a non-ASCII key")
                validate(child)
            return
        raise AzureContractError(
            "claim JSON contains a float or unsupported value type"
        )

    validate(value)
    data = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    if len(data) > TXT_PAYLOAD_LIMIT:
        raise AzureContractError("claim payload exceeds the bounded TXT payload")
    return data


def _parse_canonical_ascii_json(data: bytes, name: str) -> Any:
    if not isinstance(data, bytes) or len(data) > TXT_PAYLOAD_LIMIT:
        raise AzureContractError(f"{name} size is invalid")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise AzureContractError(f"{name} is not ASCII") from None

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AzureContractError(f"{name} contains a duplicate field")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=no_duplicates,
            parse_float=lambda _: (_ for _ in ()).throw(
                AzureContractError(f"{name} contains a float")
            ),
            parse_constant=lambda _: (_ for _ in ()).throw(
                AzureContractError(f"{name} contains a non-finite number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError):
        raise AzureContractError(f"{name} is not valid JSON") from None
    if _canonical_ascii_bytes(value) != data:
        raise AzureContractError(f"{name} is not canonical ASCII JSON")
    return value


def _require_sha256_value(value: Any, name: str) -> str:
    checked = _require_safe_string(value, name)
    if not _SHA256_PATTERN.fullmatch(checked):
        raise AzureContractError(f"{name} is not a full SHA-256")
    return checked


def _require_ascii_name(
    value: Any, name: str, pattern: re.Pattern[str]
) -> str:
    checked = _require_safe_string(value, name)
    if not checked.isascii() or not pattern.fullmatch(checked):
        raise AzureContractError(f"{name} is invalid")
    return checked


def _coordination_zone_id(value: Any, zone_name: str) -> str:
    checked = _require_safe_string(value, "coordination zone resource ID")
    match = re.fullmatch(
        r"/subscriptions/(?P<subscription>[0-9a-fA-F-]{36})/"
        r"resourceGroups/(?P<resource_group>[A-Za-z0-9._()-]{1,90})/"
        r"providers/Microsoft\.Network/privateDnsZones/"
        r"(?P<zone>[^/]+)",
        checked,
        re.ASCII | re.IGNORECASE,
    )
    if (
        match is None
        or match.group("zone").casefold() != zone_name
        or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            match.group("subscription"),
            re.ASCII,
        )
    ):
        raise AzureContractError(
            "coordination zone resource ID is not the exact Private DNS zone"
        )
    return checked


def _coordination_internal_id(value: Any) -> str:
    internal_id = _require_safe_string(
        value, "coordination zone internal ID"
    )
    if _AZURE_UUID_PATTERN.fullmatch(internal_id):
        return internal_id.casefold()
    if not _OPAQUE_INTERNAL_ID_PATTERN.fullmatch(internal_id):
        raise AzureContractError("coordination zone internal ID is invalid")
    try:
        decoded = base64.b64decode(internal_id, validate=True)
    except (binascii.Error, ValueError):
        raise AzureContractError(
            "coordination zone internal ID is invalid"
        ) from None
    if (
        len(decoded) < 16
        or base64.b64encode(decoded).decode("ascii") != internal_id
    ):
        raise AzureContractError("coordination zone internal ID is invalid")
    return internal_id


def validate_coordination_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the immutable, unlinked Private DNS coordination binding."""
    if not isinstance(value, Mapping) or set(value) != _COORDINATION_BINDING_FIELDS:
        raise AzureContractError("coordination binding fields are not exact")
    zone_name = _require_ascii_name(
        value["zone_name"], "coordination zone name", _DNS_ZONE_NAME_PATTERN
    ).casefold()
    if zone_name == "privatelink.blob.core.windows.net":
        raise AzureContractError(
            "coordination zone must not be the Blob private-link zone"
        )
    zone_id = _coordination_zone_id(value["zone_resource_id"], zone_name)
    internal_id = _coordination_internal_id(value["zone_internal_id"])
    ttl = value["record_ttl"]
    links = value["expected_vnet_link_count"]
    if (
        value["schema_version"] != COORDINATION_BINDING_SCHEMA_VERSION
        or value["zone_location"] != "global"
        or value["private_dns_api_version"]
        != PRIVATE_DNS_RECORD_SET_API_VERSION
        or value["management_lock_api_version"] != MANAGEMENT_LOCK_API_VERSION
        or type(ttl) is not int
        or not 60 <= ttl <= 3600
        or type(links) is not int
        or links != 0
        or value["lock_level"] != "CanNotDelete"
    ):
        raise AzureContractError("coordination binding controls are invalid")
    lock_name = _require_ascii_name(
        value["lock_name"], "coordination management-lock name", _LOCK_NAME_PATTERN
    )
    lock_id = _require_safe_string(
        value["lock_resource_id"], "coordination management-lock resource ID"
    )
    suffix = f"/providers/Microsoft.Authorization/locks/{lock_name}"
    if not lock_id.casefold().endswith(suffix.casefold()):
        raise AzureContractError("coordination management-lock identity is invalid")
    lock_scope = lock_id[: -len(suffix)]
    zone_parts = zone_id.split("/")
    ancestors = {
        "/".join(zone_parts[:3]).casefold(),
        "/".join(zone_parts[:5]).casefold(),
        zone_id.casefold(),
    }
    if lock_scope.casefold() not in ancestors:
        raise AzureContractError(
            "coordination management lock is not direct or inherited"
        )
    checked = {
        "schema_version": COORDINATION_BINDING_SCHEMA_VERSION,
        "zone_name": zone_name,
        "zone_resource_id": zone_id,
        "zone_location": "global",
        "zone_internal_id": internal_id,
        "private_dns_api_version": PRIVATE_DNS_RECORD_SET_API_VERSION,
        "record_ttl": ttl,
        "expected_vnet_link_count": 0,
        "lock_name": lock_name,
        "lock_resource_id": lock_id,
        "lock_level": "CanNotDelete",
        "management_lock_api_version": MANAGEMENT_LOCK_API_VERSION,
    }
    if _canonical_ascii_bytes(dict(value)) != _canonical_ascii_bytes(checked):
        raise AzureContractError("coordination binding is not canonical")
    return checked


def coordination_binding_sha256(value: Mapping[str, Any]) -> str:
    checked = validate_coordination_binding(value)
    return hashlib.sha256(_canonical_ascii_bytes(checked)).hexdigest()


def validate_coordination_zone(
    binding: Mapping[str, Any],
    zone: Mapping[str, Any],
    virtual_network_links: Sequence[Mapping[str, Any]],
    management_lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate the existing unlinked zone, recreation ID, and exact lock."""
    checked = validate_coordination_binding(binding)
    live_zone = normalize_azure_value(zone)
    links = normalize_azure_value(list(virtual_network_links))
    lock = normalize_azure_value(management_lock)
    if (
        not isinstance(live_zone, Mapping)
        or str(live_zone.get("id", "")).casefold()
        != checked["zone_resource_id"].casefold()
        or live_zone.get("name") != checked["zone_name"]
        or str(live_zone.get("type", "")).casefold()
        != "microsoft.network/privatednszones"
        or str(live_zone.get("location", "")).casefold()
        != checked["zone_location"]
    ):
        raise AzureContractError("live coordination zone identity is not exact")
    properties = live_zone.get("properties")
    if (
        not isinstance(properties, Mapping)
        or properties.get("internalId") != checked["zone_internal_id"]
        or properties.get("provisioningState") not in {None, "Succeeded"}
    ):
        raise AzureContractError(
            "live coordination zone was recreated or is not provisioned"
        )
    for count_name in (
        "numberOfVirtualNetworkLinks",
        "numberOfVirtualNetworkLinksWithRegistration",
    ):
        if count_name in properties and properties[count_name] != 0:
            raise AzureContractError("coordination zone has a VNet link")
    if links != []:
        raise AzureContractError("coordination zone must have zero VNet links")
    if (
        not isinstance(lock, Mapping)
        or str(lock.get("id", "")).casefold()
        != checked["lock_resource_id"].casefold()
        or lock.get("name") != checked["lock_name"]
        or str(lock.get("type", "")).casefold()
        != "microsoft.authorization/locks"
        or not isinstance(lock.get("properties"), Mapping)
        or lock["properties"].get("level") != "CanNotDelete"
    ):
        raise AzureContractError("coordination zone CanNotDelete lock is not exact")
    return {
        "status": "COORDINATION_ZONE_AUTHENTICATED",
        "coordination_binding_sha256": coordination_binding_sha256(checked),
        "zone_resource_id": checked["zone_resource_id"],
        "zone_internal_id": checked["zone_internal_id"],
        "vnet_link_count": 0,
        "lock_resource_id": checked["lock_resource_id"],
        "lock_level": "CanNotDelete",
    }


def _validate_domain_value(value: Any, path: str = "binding") -> None:
    forbidden = (
        "secret",
        "password",
        "token",
        "raw",
        "holdout",
        "locked_input",
        "label",
        "output",
        "case_id",
        "caseid",
        "private_value",
    )
    if type(value) is dict:
        for key, child in value.items():
            if (
                type(key) is not str
                or not key.isascii()
                or any(fragment in key.casefold() for fragment in forbidden)
            ):
                raise AzureContractError(
                    "claim domain contains a forbidden private/secret field"
                )
            _validate_domain_value(child, f"{path}.{key}")
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _validate_domain_value(child, f"{path}[{index}]")
        return
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str and value.isascii() and not any(
        ord(character) < 0x20 or ord(character) == 0x7F for character in value
    ):
        return
    raise AzureContractError(f"{path} is not a canonical nonsecret value")


def claim_domain_sha256(kind: str, binding: Mapping[str, Any]) -> str:
    """Hash a complete deterministic claim domain without truncation."""
    if kind not in CLAIM_KINDS or not isinstance(binding, Mapping) or not binding:
        raise AzureContractError("claim domain kind/binding is invalid")
    _validate_domain_value(dict(binding))
    domain = {
        "schema_version": CLAIM_DOMAIN_SCHEMA_VERSION,
        "kind": kind,
        "binding": dict(binding),
    }
    return hashlib.sha256(_canonical_ascii_bytes(domain)).hexdigest()


def dns_txt_record_name(kind: str, domain_sha256: str) -> str:
    if kind not in CLAIM_KINDS:
        raise AzureContractError("TXT claim kind is invalid")
    domain = _require_sha256_value(domain_sha256, "TXT claim domain SHA-256")
    name = f"{kind}-{domain[:32]}.{domain[32:]}"
    if not _DNS_RECORD_NAME_PATTERN.fullmatch(name):
        raise AzureContractError("TXT record name is not DNS-safe")
    return name


def _validate_claim_values(kind: str, claims: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "build": _BUILD_CLAIM_FIELDS,
        "launch": _LAUNCH_CLAIM_FIELDS,
        "dispatch": _DISPATCH_CLAIM_FIELDS,
    }[kind]
    if not isinstance(claims, Mapping) or set(claims) != fields:
        raise AzureContractError(f"{kind} claim fields are not exact")
    checked = dict(claims)
    nonce = _require_safe_string(checked["claim_nonce"], f"{kind} claim nonce")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce, re.ASCII):
        raise AzureContractError(f"{kind} claim nonce is invalid")
    sha_fields = {
        name
        for name in fields
        if name.endswith("_sha256")
    }
    for name in sha_fields:
        checked[name] = _require_sha256_value(
            checked[name], f"{kind} claim {name}"
        )
    if kind == "build":
        commit = _require_safe_string(checked["source_commit"], "build source commit")
        if not _COMMIT_PATTERN.fullmatch(commit):
            raise AzureContractError("build source commit is invalid")
        task_run_name = _require_ascii_name(
            checked["task_run_name"], "build TaskRun name", _TASK_RUN_NAME_PATTERN
        )
        if checked["staging_tag"] != f"staging-{commit}-{nonce}":
            raise AzureContractError("build staging tag does not bind its contender")
        checked["task_run_name"] = task_run_name
    elif kind == "launch":
        authorization = _require_ascii_name(
            checked["authorization_id"],
            "launch authorization ID",
            _OPAQUE_AUTHORIZATION_PATTERN,
        )
        binding = (
            checked["stage"],
            checked["mode"],
            checked["retry_kind"],
        )
        if binding not in {
            ("P", "prediction", "none"),
            ("P", "prediction", "infrastructure_pre_input"),
            ("P", "prediction_adoption", "prediction_adoption"),
            ("E", "finalization", "none"),
            ("E", "finalization", "scorer_infrastructure"),
            ("E", "verification", "verification_only"),
        }:
            raise AzureContractError("launch stage/mode/retry binding is invalid")
        if checked["execution_id"] != f"stage-{checked['stage'].casefold()}-{nonce}":
            raise AzureContractError("launch execution ID does not bind its contender")
        checked["authorization_id"] = authorization
        _require_ascii_name(
            checked["job_name"],
            "launch Job name",
            re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.ASCII),
        )
        oid = _require_safe_string(
            checked["launcher_git_blob_oid"], "launcher Git blob OID"
        )
        if not _GIT_OID_PATTERN.fullmatch(oid):
            raise AzureContractError("launcher Git blob OID is invalid")
    else:
        checked["authorization_id"] = _require_ascii_name(
            checked["authorization_id"],
            "dispatch authorization ID",
            _OPAQUE_AUTHORIZATION_PATTERN,
        )
        launch_name = _require_ascii_name(
            checked["launch_record_name"],
            "dispatch launch record name",
            _DNS_RECORD_NAME_PATTERN,
        )
        if not launch_name.startswith("launch-"):
            raise AzureContractError("dispatch does not bind a launch TXT record")
        if launch_name != dns_txt_record_name(
            "launch", checked["launch_domain_sha256"]
        ):
            raise AzureContractError("dispatch launch record/domain binding differs")
        _require_ascii_name(
            checked["job_name"],
            "dispatch Job name",
            re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.ASCII),
        )
        if not re.fullmatch(
            r"stage-[pe]-[0-9a-f]{32}", checked["execution_id"], re.ASCII
        ):
            raise AzureContractError("dispatch execution ID is invalid")
    if kind in {"launch", "dispatch"}:
        count = checked["baseline_execution_count"]
        if type(count) is not int or count < 0 or count > 1024:
            raise AzureContractError("claim baseline execution count is invalid")
    _canonical_ascii_bytes(checked)
    return checked


def build_claim_envelope(
    kind: str,
    domain_sha256: str,
    claims: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a strict canonical nonsecret claim envelope."""
    if kind not in CLAIM_KINDS:
        raise AzureContractError("claim kind is invalid")
    domain = _require_sha256_value(domain_sha256, "claim domain SHA-256")
    checked = {
        "schema_version": CLAIM_ENVELOPE_SCHEMA_VERSION,
        "kind": kind,
        "domain_sha256": domain,
        "claims": _validate_claim_values(kind, claims),
    }
    _canonical_ascii_bytes(checked)
    return checked


def validate_claim_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema_version",
        "kind",
        "domain_sha256",
        "claims",
    }:
        raise AzureContractError("claim envelope fields are not exact")
    if value["schema_version"] != CLAIM_ENVELOPE_SCHEMA_VERSION:
        raise AzureContractError("claim envelope schema is invalid")
    rebuilt = build_claim_envelope(
        value["kind"], value["domain_sha256"], value["claims"]
    )
    if _canonical_ascii_bytes(dict(value)) != _canonical_ascii_bytes(rebuilt):
        raise AzureContractError("claim envelope is not canonical")
    return rebuilt


def encode_txt_chunks(envelope: Mapping[str, Any]) -> list[str]:
    checked = validate_claim_envelope(envelope)
    encoded = base64.urlsafe_b64encode(_canonical_ascii_bytes(checked)).decode(
        "ascii"
    ).rstrip("=")
    parts = [
        encoded[index : index + TXT_CHUNK_DATA_LENGTH]
        for index in range(0, len(encoded), TXT_CHUNK_DATA_LENGTH)
    ]
    if not parts or len(parts) > TXT_CHUNK_LIMIT:
        raise AzureContractError("claim requires too many TXT chunks")
    total = len(parts)
    chunks = [
        f"{TXT_CHUNK_VERSION}:{index:02d}:{total:02d}:{part}"
        for index, part in enumerate(parts)
    ]
    if any(len(chunk.encode("ascii")) > 255 for chunk in chunks):
        raise AzureContractError("TXT chunk exceeds the DNS character-string bound")
    return chunks


def decode_txt_chunks(chunks: Sequence[str]) -> dict[str, Any]:
    if (
        not isinstance(chunks, Sequence)
        or isinstance(chunks, (str, bytes))
        or not 1 <= len(chunks) <= TXT_CHUNK_LIMIT
    ):
        raise AzureContractError("TXT chunk membership is invalid")
    payload_parts: list[str] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks):
        if (
            not isinstance(chunk, str)
            or not chunk.isascii()
            or len(chunk.encode("ascii")) > 255
        ):
            raise AzureContractError("TXT chunk is invalid")
        match = re.fullmatch(
            rf"{TXT_CHUNK_VERSION}:([0-9]{{2}}):([0-9]{{2}}):"
            r"([A-Za-z0-9_-]{1,192})",
            chunk,
            re.ASCII,
        )
        if (
            match is None
            or int(match.group(1)) != index
            or int(match.group(2)) != total
        ):
            raise AzureContractError("TXT chunks are not exactly indexed and ordered")
        payload_parts.append(match.group(3))
    encoded = "".join(payload_parts)
    try:
        decoded = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, base64.binascii.Error):
        raise AzureContractError("TXT payload is not canonical base64url") from None
    envelope = _parse_canonical_ascii_json(decoded, "TXT claim payload")
    if not isinstance(envelope, Mapping):
        raise AzureContractError("TXT claim payload is not an object")
    checked = validate_claim_envelope(envelope)
    if encode_txt_chunks(checked) != list(chunks):
        raise AzureContractError("TXT chunks are not the canonical encoding")
    return checked


def build_txt_record_set_body(
    envelope: Mapping[str, Any], *, ttl: int
) -> dict[str, Any]:
    if type(ttl) is not int or not 60 <= ttl <= 3600:
        raise AzureContractError("TXT record TTL is invalid")
    return {
        "properties": {
            "ttl": ttl,
            "txtRecords": [{"value": encode_txt_chunks(envelope)}],
        }
    }


def _record_set_resource_id(zone_resource_id: str, record_name: str) -> str:
    return f"{zone_resource_id}/TXT/{record_name}"


def validate_txt_record_set(
    record: Mapping[str, Any],
    *,
    zone_resource_id: str,
    record_name: str,
    ttl: int,
    expected_envelope: Mapping[str, Any] | None = None,
    expected_kind: str | None = None,
    expected_domain_sha256: str | None = None,
) -> dict[str, Any]:
    """Authenticate an exact live Private DNS TXT RecordSet and payload."""
    if not isinstance(record, Mapping):
        raise AzureContractError("TXT RecordSet response is not an object")
    if not _DNS_RECORD_NAME_PATTERN.fullmatch(record_name):
        raise AzureContractError("expected TXT record name is invalid")
    expected_id = _record_set_resource_id(zone_resource_id, record_name)
    if (
        str(record.get("id", "")).casefold() != expected_id.casefold()
        or record.get("name") != record_name
        or str(record.get("type", "")).casefold()
        != "microsoft.network/privatednszones/txt"
    ):
        raise AzureContractError("live TXT RecordSet identity is not exact")
    etag = _require_safe_string(record.get("etag"), "live TXT RecordSet ETag")
    if (
        not etag.isascii()
        or len(etag) > 512
        or re.fullmatch(r"[\x21-\x7e]+", etag, re.ASCII) is None
    ):
        raise AzureContractError("live TXT RecordSet ETag is invalid")
    properties = record.get("properties")
    if (
        not isinstance(properties, Mapping)
        or properties.get("ttl") != ttl
        or type(properties.get("ttl")) is not int
    ):
        raise AzureContractError("live TXT RecordSet TTL is not exact")
    txt_records = properties.get("txtRecords")
    if (
        not isinstance(txt_records, list)
        or len(txt_records) != 1
        or not isinstance(txt_records[0], Mapping)
        or set(txt_records[0]) != {"value"}
        or not isinstance(txt_records[0]["value"], list)
    ):
        raise AzureContractError(
            "live TXT RecordSet must contain exactly one TXT record"
        )
    envelope = decode_txt_chunks(txt_records[0]["value"])
    kind = envelope["kind"]
    domain = envelope["domain_sha256"]
    if record_name != dns_txt_record_name(kind, domain):
        raise AzureContractError("TXT RecordSet name omits the full claim domain")
    if expected_kind is not None and kind != expected_kind:
        raise AzureContractError("TXT claim kind differs")
    if (
        expected_domain_sha256 is not None
        and domain
        != _require_sha256_value(
            expected_domain_sha256, "expected TXT claim domain SHA-256"
        )
    ):
        raise AzureContractError("TXT claim domain differs")
    if expected_envelope is not None:
        expected = validate_claim_envelope(expected_envelope)
        if _canonical_ascii_bytes(envelope) != _canonical_ascii_bytes(expected):
            raise AzureContractError("live TXT claim payload differs")
    payload_bytes = _canonical_ascii_bytes(envelope)
    return {
        "status": "TXT_RECORD_AUTHENTICATED",
        "record_name": record_name,
        "record_resource_id": expected_id,
        "record_etag": etag,
        "record_etag_sha256": hashlib.sha256(etag.encode("ascii")).hexdigest(),
        "record_ttl": ttl,
        "kind": kind,
        "domain_sha256": domain,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "envelope": envelope,
    }


class DnsCreateCapability:
    """Unserializable in-process proof of one exact create-only HTTP 201."""

    __slots__ = ("kind", "domain_sha256", "record_name", "_proof")
    _sentinel = object()

    def __init__(
        self,
        sentinel: object,
        *,
        kind: str,
        domain_sha256: str,
        record_name: str,
    ) -> None:
        if sentinel is not self._sentinel:
            raise AzureContractError("DNS create capability cannot be reconstructed")
        self.kind = kind
        self.domain_sha256 = domain_sha256
        self.record_name = record_name
        self._proof = os.urandom(32)

    def __reduce__(self) -> Any:
        raise TypeError("DNS create capability is process-local")


def dns_create_capability_from_exact_201(
    status: int,
    create_response: Mapping[str, Any],
    reread_response: Mapping[str, Any],
    *,
    zone_resource_id: str,
    record_name: str,
    ttl: int,
    expected_envelope: Mapping[str, Any],
) -> DnsCreateCapability | None:
    """Grant capability only for exact 201 plus matching returned/re-GET state."""
    if type(status) is not int or status != 201:
        return None
    created = validate_txt_record_set(
        create_response,
        zone_resource_id=zone_resource_id,
        record_name=record_name,
        ttl=ttl,
        expected_envelope=expected_envelope,
    )
    reread = validate_txt_record_set(
        reread_response,
        zone_resource_id=zone_resource_id,
        record_name=record_name,
        ttl=ttl,
        expected_envelope=expected_envelope,
    )
    if (
        created["record_etag"] != reread["record_etag"]
        or created["payload_sha256"] != reread["payload_sha256"]
        or created["record_resource_id"].casefold()
        != reread["record_resource_id"].casefold()
    ):
        raise AzureContractError("created/re-GET TXT RecordSet evidence differs")
    return DnsCreateCapability(
        DnsCreateCapability._sentinel,
        kind=created["kind"],
        domain_sha256=created["domain_sha256"],
        record_name=record_name,
    )


def attempt_txt_record_create_once(
    put: Callable[[Mapping[str, Any]], tuple[int, Mapping[str, Any]]],
    get: Callable[[], Mapping[str, Any]],
    *,
    request_body: Mapping[str, Any],
    zone_resource_id: str,
    record_name: str,
    ttl: int,
    expected_envelope: Mapping[str, Any],
) -> DnsCreateCapability | None:
    """Call the supplied PUT exactly once; transport ambiguity grants nothing."""
    try:
        status, response = put(request_body)
    except (OSError, TimeoutError, ConnectionError):
        return None
    if type(status) is not int or status != 201:
        return None
    try:
        reread = get()
        return dns_create_capability_from_exact_201(
            status,
            response,
            reread,
            zone_resource_id=zone_resource_id,
            record_name=record_name,
            ttl=ttl,
            expected_envelope=expected_envelope,
        )
    except (OSError, TimeoutError, ConnectionError, AzureContractError):
        return None


def authenticate_existing_txt_record(
    record: Mapping[str, Any],
    *,
    zone_resource_id: str,
    record_name: str,
    ttl: int,
    expected_kind: str,
    expected_domain_sha256: str,
) -> dict[str, Any]:
    """GET-only authentication deliberately returns evidence, never capability."""
    return validate_txt_record_set(
        record,
        zone_resource_id=zone_resource_id,
        record_name=record_name,
        ttl=ttl,
        expected_kind=expected_kind,
        expected_domain_sha256=expected_domain_sha256,
    )


def execution_membership(names: Sequence[str]) -> dict[str, Any]:
    normalized = normalize_azure_value(list(names))
    if (
        not isinstance(normalized, list)
        or any(
            not isinstance(name, str)
            or not name
            or not name.isascii()
            or len(name) > 256
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in name)
            for name in normalized
        )
        or normalized != sorted(set(normalized))
    ):
        raise AzureContractError(
            "execution membership must be sorted, unique, bounded ASCII"
        )
    data = _canonical_ascii_bytes(normalized)
    return {
        "count": len(normalized),
        "sha256": hashlib.sha256(data).hexdigest(),
        "names": normalized,
    }


def execution_membership_from_records(
    executions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(executions, Sequence) or any(
        not isinstance(item, Mapping) for item in executions
    ):
        raise AzureContractError("execution records are invalid")
    names = [
        _strict_string(item.get("name"), "execution name")
        for item in executions
    ]
    return execution_membership(sorted(names))


def adopt_remove_one_execution(
    baseline_names: Sequence[str],
    current_names: Sequence[str],
) -> str:
    """Return the only member whose removal exactly restores the baseline."""
    baseline = execution_membership(baseline_names)["names"]
    current = execution_membership(current_names)["names"]
    candidates = [
        name
        for index, name in enumerate(current)
        if current[:index] + current[index + 1 :] == baseline
    ]
    if len(candidates) != 1:
        raise AzureContractError(
            "execution adoption requires exact remove-one membership"
        )
    return candidates[0]


def _validate_arm_query_value(value: str) -> None:
    index = 0
    while index < len(value):
        character = value[index]
        if _ARM_QUERY_VALUE_CHARACTER_PATTERN.fullmatch(character):
            index += 1
            continue
        if (
            character != "%"
            or index + 2 >= len(value)
            or not re.fullmatch(r"[0-9A-F]{2}", value[index + 1 : index + 3])
        ):
            raise AzureContractError("ARM pagination query encoding is ambiguous")
        decoded = int(value[index + 1 : index + 3], 16)
        if (
            decoded == ord("%")
            or decoded == 0x7F
            or decoded < 0x20
            or decoded > 0x7E
            or _ARM_QUERY_VALUE_CHARACTER_PATTERN.fullmatch(chr(decoded))
        ):
            raise AzureContractError("ARM pagination query encoding is ambiguous")
        index += 3


def _arm_query(query: str) -> tuple[tuple[str, str], ...]:
    if not query:
        raise AzureContractError("ARM pagination URL omits its query")
    pairs: list[tuple[str, str]] = []
    names: set[str] = set()
    for component in query.split("&"):
        if not component or "=" not in component:
            raise AzureContractError("ARM pagination query is not exact")
        name, value = component.split("=", 1)
        if (
            not _ARM_QUERY_NAME_PATTERN.fullmatch(name)
            or not value
            or name.casefold() in names
        ):
            raise AzureContractError(
                "ARM pagination query has an invalid/repeated parameter"
            )
        _validate_arm_query_value(value)
        names.add(name.casefold())
        pairs.append((name, value))
    return tuple(pairs)


def _management_url_parts(
    value: str,
) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    if not isinstance(value, str):
        raise AzureContractError("ARM pagination URL is not exact")
    normalized = value.replace("\r", "")
    if (
        not normalized
        or not normalized.isascii()
        or any(
            ord(character) <= 0x20 or ord(character) == 0x7F
            for character in normalized
        )
        or "#" in normalized
    ):
        raise AzureContractError("ARM pagination URL is not exact")
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        raise AzureContractError("ARM pagination URL is not exact") from None
    if (
        parsed.scheme != "https"
        or parsed.netloc != "management.azure.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path.endswith("/")
        or "%" in parsed.path
        or "\\" in parsed.path
    ):
        raise AzureContractError("ARM pagination URL is not exact")
    path_parts = parsed.path[1:].split("/")
    if (
        len(path_parts) < 7
        or path_parts[0] != "subscriptions"
        or path_parts[2] != "resourceGroups"
        or path_parts[4] != "providers"
        or any(
            part in {"", ".", ".."}
            or not _ARM_PATH_SEGMENT_PATTERN.fullmatch(part)
            for part in path_parts
        )
    ):
        raise AzureContractError("ARM pagination resource path is not exact")
    return normalized, parsed.path, _arm_query(parsed.query)


def collect_arm_list(
    start_url: str,
    *,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> list[Any]:
    """Follow every explicit ARM nextLink and return exact list membership."""
    start, collection_path, initial_query = _management_url_parts(start_url)
    initial_parameters = dict(initial_query)
    api_version = initial_parameters.get("api-version")
    continuation_names = {
        name.casefold() for name in _ARM_CONTINUATION_QUERY_PARAMETERS
    }
    if (
        api_version is None
        or not _ARM_API_VERSION_PATTERN.fullmatch(api_version)
        or any(name.casefold() in continuation_names for name in initial_parameters)
    ):
        raise AzureContractError("ARM list query is not an exact initial query")
    current: str | None = start
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    records: list[Any] = []
    first_page = True
    while current is not None:
        current, current_path, current_query = _management_url_parts(current)
        current_parameters = dict(current_query)
        if current_path != collection_path:
            raise AzureContractError(
                "ARM nextLink escaped the exact collection resource path"
            )
        if not first_page:
            if any(
                current_parameters.get(name) != value
                for name, value in initial_query
            ):
                raise AzureContractError(
                    "ARM nextLink changed the exact initial query"
                )
            continuation = [
                (name, value)
                for name, value in current_query
                if name not in initial_parameters
            ]
            if (
                len(current_parameters) != len(initial_parameters) + 1
                or len(continuation) != 1
                or continuation[0][0]
                not in _ARM_CONTINUATION_QUERY_PARAMETERS
            ):
                raise AzureContractError(
                    "ARM nextLink added a non-continuation query parameter"
                )
        identity = (current_path, tuple(sorted(current_query)))
        if identity in seen:
            raise AzureContractError("ARM pagination repeated a nextLink")
        seen.add(identity)
        completed = run(
            [
                "az",
                "rest",
                "--method",
                "get",
                "--url",
                current,
                "--output",
                "json",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise AzureContractError("ARM list request failed")
        try:
            page = normalize_azure_value(
                json.loads(completed.stdout.decode("utf-8"))
            )
        except (UnicodeError, json.JSONDecodeError):
            raise AzureContractError("ARM list returned invalid JSON") from None
        if not isinstance(page, Mapping) or not isinstance(page.get("value"), list):
            raise AzureContractError("ARM list page omits its value array")
        records.extend(page["value"])
        next_link = page.get("nextLink")
        if next_link is not None and (
            not isinstance(next_link, str) or not next_link
        ):
            raise AzureContractError("ARM list nextLink is invalid")
        current = next_link
        first_page = False
    identities = [
        (
            item.get("id")
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
            else item.get("name")
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
            else None
        )
        for item in records
    ]
    if (
        None in identities
        or any(
            any(ord(character) < 32 for character in identity)
            for identity in identities
            if isinstance(identity, str)
        )
        or len(identities) != len(set(identities))
    ):
        raise AzureContractError("ARM pagination returned invalid/repeated membership")
    return records


def _require_safe_string(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 32 for character in value)
    ):
        raise AzureContractError(f"{name} is invalid")
    return value


def _require_relative_path(value: Any, name: str) -> str:
    path = _require_safe_string(value, name)
    parsed = Path(path)
    if (
        "\\" in path
        or path.startswith("/")
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise AzureContractError(f"{name} is not an exact relative path")
    return path


def exact_remote_git_source(
    repository_url: str,
    source_commit: str,
) -> str:
    """Return the one ACR remote-Git source accepted by this repository."""
    repository = _require_safe_string(
        repository_url, "build source repository URL"
    )
    commit = _require_safe_string(source_commit, "build source commit")
    parsed = urlsplit(repository)
    if (
        repository != BUILD_SOURCE_REPOSITORY_URL
        or parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.path != "/Alanjiao1988/J-space-observation.git"
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or "\\" in repository
        or "%" in repository
        or repository != repository.strip()
        or not _COMMIT_PATTERN.fullmatch(commit)
    ):
        raise AzureContractError(
            "build source repository URL/commit is not the registered origin"
        )
    return f"{repository}#{commit}"


def validate_remote_git_source(
    source_location: Any,
    *,
    repository_url: str,
    source_commit: str,
) -> str:
    """Require ACR to expose the exact registered remote URL and commit ref."""
    location = _require_safe_string(
        source_location, "ACR runRequest source location"
    )
    expected = exact_remote_git_source(repository_url, source_commit)
    parsed = urlsplit(location)
    if (
        location != expected
        or parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.path != "/Alanjiao1988/J-space-observation.git"
        or parsed.query
        or parsed.fragment != source_commit
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or "\\" in location
        or "%" in location
        or location != location.strip()
    ):
        raise AzureContractError(
            "ACR runRequest source location differs from the exact remote commit"
        )
    return expected


def _validate_build_source_binding(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema_version",
        "source_commit",
        "source_repository_url",
        "remote_source_location",
        "base_image",
        "image_repository",
        "files",
    }:
        raise AzureContractError("build source binding fields are not exact")
    if value["schema_version"] != BUILD_SOURCE_BINDING_SCHEMA_VERSION:
        raise AzureContractError("build source binding schema is invalid")
    commit = _require_safe_string(
        value["source_commit"], "build source commit"
    )
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise AzureContractError("build source commit is invalid")
    repository_url = _require_safe_string(
        value["source_repository_url"], "build source repository URL"
    )
    remote_source_location = validate_remote_git_source(
        value["remote_source_location"],
        repository_url=repository_url,
        source_commit=commit,
    )
    base_image = _require_safe_string(
        value["base_image"], "pinned base image"
    )
    if not re.search(r"@sha256:[0-9a-f]{64}$", base_image):
        raise AzureContractError("pinned base image is not digest-qualified")
    repository = _require_safe_string(
        value["image_repository"], "image repository"
    )
    if not _IMAGE_REPOSITORY_PATTERN.fullmatch(repository):
        raise AzureContractError("image repository is invalid")
    raw_files = value["files"]
    if not isinstance(raw_files, Mapping) or not raw_files:
        raise AzureContractError("build source files are missing")
    files: dict[str, dict[str, Any]] = {}
    for raw_path, raw_binding in raw_files.items():
        path = _require_relative_path(raw_path, "build source path")
        if path in files:
            raise AzureContractError("build source path is repeated")
        if not isinstance(raw_binding, Mapping) or set(raw_binding) != {
            "git_blob_oid",
            "sha256",
            "size",
        }:
            raise AzureContractError(
                f"build source binding is invalid: {path}"
            )
        oid = _require_safe_string(
            raw_binding["git_blob_oid"], f"Git blob OID for {path}"
        )
        sha256 = _require_safe_string(
            raw_binding["sha256"], f"source SHA-256 for {path}"
        )
        size = raw_binding["size"]
        if (
            not _GIT_OID_PATTERN.fullmatch(oid)
            or not _SHA256_PATTERN.fullmatch(sha256)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise AzureContractError(
                f"build source provenance is invalid: {path}"
            )
        files[path] = {
            "git_blob_oid": oid,
            "sha256": sha256,
            "size": size,
        }
    return {
        "schema_version": BUILD_SOURCE_BINDING_SCHEMA_VERSION,
        "source_commit": commit,
        "source_repository_url": repository_url,
        "remote_source_location": remote_source_location,
        "base_image": base_image,
        "image_repository": repository,
        "files": dict(sorted(files.items())),
    }


def build_provenance_record(
    source_binding: Mapping[str, Any],
    *,
    acr_resource_id: str,
    login_server: str,
    acr_location: str,
    coordination_binding: Mapping[str, Any],
    dockerfile_path: str = BUILD_DOCKERFILE_PATH,
    dependency_paths: Sequence[str] = BUILD_DEPENDENCY_PATHS,
) -> dict[str, Any]:
    """Create the one canonical, nonsecret parser image build contract."""
    source = _validate_build_source_binding(source_binding)
    resource_id = _require_safe_string(
        acr_resource_id, "ACR resource ID"
    ).casefold()
    if (
        not resource_id.startswith("/subscriptions/")
        or "/providers/microsoft.containerregistry/registries/" not in resource_id
    ):
        raise AzureContractError("ACR resource ID is invalid")
    server = _require_safe_string(login_server, "ACR login server").casefold()
    location = _require_safe_string(acr_location, "ACR location").casefold()
    registry_name = resource_id.rsplit("/", 1)[-1]
    if (
        server != f"{registry_name}.azurecr.io"
        or not _AZURE_LOCATION_PATTERN.fullmatch(location)
    ):
        raise AzureContractError("ACR login server/location binding is invalid")
    dockerfile = _require_relative_path(
        dockerfile_path, "build Dockerfile path"
    )
    dependencies = [
        _require_relative_path(path, "build dependency path")
        for path in dependency_paths
    ]
    if (
        len(dependencies) != len(set(dependencies))
        or not dependencies
        or dockerfile in dependencies
    ):
        raise AzureContractError("build dependency paths are invalid")
    files = source["files"]
    if dockerfile not in files or any(path not in files for path in dependencies):
        raise AzureContractError(
            "Dockerfile/dependency is absent from source binding"
        )
    source_binding_sha256 = hashlib.sha256(
        _canonical_bytes(source)
    ).hexdigest()
    coordination = validate_coordination_binding(coordination_binding)
    coordination_sha256 = coordination_binding_sha256(coordination)
    commit = source["source_commit"]
    repository = source["image_repository"]
    build_domain_sha256 = claim_domain_sha256(
        "build",
        {
            "source_commit": commit,
            "source_binding_sha256": source_binding_sha256,
            "acr_resource_id_sha256": hashlib.sha256(
                resource_id.encode("ascii")
            ).hexdigest(),
            "image_repository_sha256": hashlib.sha256(
                repository.encode("ascii")
            ).hexdigest(),
            "base_image_sha256": hashlib.sha256(
                source["base_image"].encode("ascii")
            ).hexdigest(),
            "coordination_binding_sha256": coordination_sha256,
        },
    )
    return {
        "schema_version": BUILD_PROVENANCE_SCHEMA_VERSION,
        "source_commit": commit,
        "remote_source": {
            "repository_url": source["source_repository_url"],
            "commit": commit,
            "source_location": source["remote_source_location"],
        },
        "pinned_base_image": source["base_image"],
        "acr": {
            "resource_id": resource_id,
            "login_server": server,
            "location": location,
            "repository": repository,
        },
        "source_binding": source,
        "source_binding_sha256": source_binding_sha256,
        "coordination": {
            "binding": coordination,
            "binding_sha256": coordination_sha256,
            "build_slot": {
                "domain_sha256": build_domain_sha256,
                "record_name": dns_txt_record_name(
                    "build", build_domain_sha256
                ),
            },
        },
        "build_context": {
            "registered_paths": sorted(files),
            "dockerfile": {"path": dockerfile, **files[dockerfile]},
            "dependencies": [
                {"path": path, **files[path]} for path in sorted(dependencies)
            ],
        },
        "expected_run_request": {
            "fields": sorted(BUILD_RUN_REQUEST_FIELDS),
            "type": "DockerBuildRequest",
            "run_type": "QuickRun",
            "source_location": source["remote_source_location"],
            "dockerfile_path": dockerfile,
            "platform": dict(BUILD_PLATFORM),
            "is_push_enabled": True,
            "no_cache": False,
            "is_archive_enabled": True,
            "credentials": {},
            "agent_configuration": {"cpu": 2},
            "timeout": 3600,
            "base_image_argument": {
                "name": BASE_IMAGE_ARGUMENT,
                "value": source["base_image"],
            },
            "provenance_argument": BUILD_PROVENANCE_ARGUMENT,
            "argument_count": 2,
        },
        "expected_images": {
            "staging_name_template": (
                f"{repository}:staging-{commit}-{{invocation_id}}"
            ),
            "final_name": f"{repository}:{commit}",
            "digest_repository": f"{server}/{repository}",
        },
        "image_config_label": {
            "name": BUILD_PROVENANCE_LABEL,
            "value_from_argument": BUILD_PROVENANCE_ARGUMENT,
        },
    }


def validate_build_provenance(
    value: Mapping[str, Any],
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema_version",
        "source_commit",
        "remote_source",
        "pinned_base_image",
        "acr",
        "source_binding",
        "source_binding_sha256",
        "coordination",
        "build_context",
        "expected_run_request",
        "expected_images",
        "image_config_label",
    }:
        raise AzureContractError("build provenance fields are not exact")
    acr = value["acr"]
    remote_source = value["remote_source"]
    context = value["build_context"]
    coordination = value["coordination"]
    if (
        not isinstance(acr, Mapping)
        or set(acr) != {
            "resource_id",
            "login_server",
            "location",
            "repository",
        }
        or not isinstance(remote_source, Mapping)
        or set(remote_source)
        != {"repository_url", "commit", "source_location"}
        or not isinstance(context, Mapping)
        or set(context) != {
            "registered_paths",
            "dockerfile",
            "dependencies",
        }
        or not isinstance(context["dockerfile"], Mapping)
        or not isinstance(context["dependencies"], list)
        or not isinstance(coordination, Mapping)
        or set(coordination)
        != {"binding", "binding_sha256", "build_slot"}
        or not isinstance(coordination["binding"], Mapping)
        or not isinstance(coordination["build_slot"], Mapping)
        or set(coordination["build_slot"])
        != {"domain_sha256", "record_name"}
    ):
        raise AzureContractError("build provenance structure is invalid")
    dependency_paths = [
        item.get("path") if isinstance(item, Mapping) else None
        for item in context["dependencies"]
    ]
    rebuilt = build_provenance_record(
        value["source_binding"],
        acr_resource_id=acr["resource_id"],
        login_server=acr["login_server"],
        acr_location=acr["location"],
        coordination_binding=coordination["binding"],
        dockerfile_path=context["dockerfile"].get("path"),
        dependency_paths=dependency_paths,
    )
    if _canonical_bytes(normalize_azure_value(value)) != _canonical_bytes(
        rebuilt
    ):
        raise AzureContractError("build provenance is not canonical")
    digest = hashlib.sha256(_canonical_bytes(rebuilt)).hexdigest()
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str)
        or not _SHA256_PATTERN.fullmatch(expected_sha256)
        or digest != expected_sha256
    ):
        raise AzureContractError("build provenance SHA-256 mismatch")
    return rebuilt


def build_provenance_sha256(value: Mapping[str, Any]) -> str:
    checked = validate_build_provenance(value)
    return hashlib.sha256(_canonical_bytes(checked)).hexdigest()


def _validate_staging_tag(
    staging_tag: str, *, source_commit: str
) -> str:
    invocation_prefix = f"staging-{source_commit}-"
    invocation_id = staging_tag.removeprefix(invocation_prefix)
    if (
        not staging_tag.startswith(invocation_prefix)
        or len(invocation_id) != 32
        or any(character not in "0123456789abcdef" for character in invocation_id)
    ):
        raise AzureContractError("ACR staging image tag is not exact")
    return staging_tag


def build_acr_run_request(
    *,
    build_provenance: Mapping[str, Any],
    build_provenance_sha256_value: str,
    staging_tag: str,
) -> dict[str, Any]:
    """Build the exact nonsecret DockerBuildRequest persisted by an ACR TaskRun."""
    provenance = validate_build_provenance(
        build_provenance,
        expected_sha256=build_provenance_sha256_value,
    )
    expected = provenance["expected_run_request"]
    staging_tag = _validate_staging_tag(
        staging_tag, source_commit=provenance["source_commit"]
    )
    return {
        "type": expected["type"],
        "imageNames": [f"{provenance['acr']['repository']}:{staging_tag}"],
        "dockerFilePath": expected["dockerfile_path"],
        "platform": dict(expected["platform"]),
        "arguments": [
            {
                "name": expected["base_image_argument"]["name"],
                "value": expected["base_image_argument"]["value"],
                "isSecret": False,
            },
            {
                "name": expected["provenance_argument"],
                "value": build_provenance_sha256_value,
                "isSecret": False,
            },
        ],
        "isPushEnabled": expected["is_push_enabled"],
        "noCache": expected["no_cache"],
        "sourceLocation": expected["source_location"],
        "isArchiveEnabled": expected["is_archive_enabled"],
        "credentials": {},
        "agentConfiguration": dict(expected["agent_configuration"]),
        "timeout": expected["timeout"],
    }


def _validate_acr_run_request(
    request: Mapping[str, Any],
    *,
    build_provenance: Mapping[str, Any],
    build_provenance_sha256_value: str,
    staging_tag: str,
    expected_run_request_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    provenance = validate_build_provenance(
        build_provenance,
        expected_sha256=build_provenance_sha256_value,
    )
    normalized = normalize_azure_value(request)
    required_fields = BUILD_RUN_REQUEST_FIELDS - {"credentials"}
    if (
        not isinstance(normalized, Mapping)
        or not required_fields.issubset(normalized)
        or not set(normalized).issubset(BUILD_RUN_REQUEST_FIELDS)
    ):
        raise AzureContractError("ACR runRequest fields are not the exact allowlist")
    canonical_request = dict(normalized)
    credentials = canonical_request.setdefault("credentials", {})
    if credentials != {}:
        raise AzureContractError("ACR runRequest credentials are not empty")
    expected_request = build_acr_run_request(
        build_provenance=provenance,
        build_provenance_sha256_value=build_provenance_sha256_value,
        staging_tag=staging_tag,
    )
    if _canonical_bytes(canonical_request) != _canonical_bytes(expected_request):
        raise AzureContractError("ACR runRequest differs from frozen provenance")
    validate_remote_git_source(
        canonical_request["sourceLocation"],
        repository_url=provenance["remote_source"]["repository_url"],
        source_commit=provenance["source_commit"],
    )
    request_sha256 = hashlib.sha256(
        _canonical_bytes(canonical_request)
    ).hexdigest()
    if expected_run_request_sha256 is not None and (
        not isinstance(expected_run_request_sha256, str)
        or not _SHA256_PATTERN.fullmatch(expected_run_request_sha256)
        or request_sha256 != expected_run_request_sha256
    ):
        raise AzureContractError("ACR runRequest differs from durable claim")
    return canonical_request, request_sha256


def build_acr_task_run_body(
    *,
    build_provenance: Mapping[str, Any],
    build_provenance_sha256_value: str,
    staging_tag: str,
) -> dict[str, Any]:
    """Create a deterministic TaskRun body; its force tag is the request hash."""
    provenance = validate_build_provenance(
        build_provenance,
        expected_sha256=build_provenance_sha256_value,
    )
    request = build_acr_run_request(
        build_provenance=provenance,
        build_provenance_sha256_value=build_provenance_sha256_value,
        staging_tag=staging_tag,
    )
    request_sha256 = hashlib.sha256(_canonical_bytes(request)).hexdigest()
    return {
        "location": provenance["acr"]["location"],
        "properties": {
            "forceUpdateTag": request_sha256,
            "runRequest": request,
        }
    }


def validate_acr_build_run(
    run: Mapping[str, Any],
    *,
    authenticated_run_request: Mapping[str, Any],
    build_provenance: Mapping[str, Any],
    build_provenance_sha256_value: str,
    staging_tag: str,
    require_succeeded: bool = False,
    expected_digest: str | None = None,
    expected_run_id: str | None = None,
    expected_run_request_sha256: str | None = None,
    expected_acr_resource_id: str | None = None,
) -> dict[str, Any]:
    """Authenticate a child ACR Run using its parent TaskRun request."""
    if type(require_succeeded) is not bool:
        raise AzureContractError("ACR success requirement must be a boolean")
    provenance = validate_build_provenance(
        build_provenance,
        expected_sha256=build_provenance_sha256_value,
    )
    normalized = normalize_azure_value(run)
    if not isinstance(normalized, Mapping):
        raise AzureContractError("ACR run is not an object")
    properties = normalized.get("properties")
    if not isinstance(properties, Mapping):
        raise AzureContractError("ACR run properties are missing")
    run_id = properties.get("runId")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise AzureContractError("ACR run ID is invalid")
    resource_name = normalized.get("name")
    if resource_name != run_id:
        raise AzureContractError("ACR run resource name differs from run ID")
    resource_id = normalized.get("id")
    expected_acr_id = (
        expected_acr_resource_id
        if expected_acr_resource_id is not None
        else provenance["acr"]["resource_id"]
    )
    if (
        not isinstance(expected_acr_id, str)
        or not expected_acr_id.startswith("/subscriptions/")
        or not isinstance(resource_id, str)
        or resource_id.casefold()
        != f"{expected_acr_id}/runs/{run_id}".casefold()
        or normalized.get("type")
        != "Microsoft.ContainerRegistry/registries/runs"
    ):
        raise AzureContractError("ACR child Run resource identity differs")
    if expected_run_id is not None and run_id != expected_run_id:
        raise AzureContractError("ACR run ID differs from durable claim")
    expected = provenance["expected_run_request"]
    if properties.get("runType") != expected["run_type"]:
        raise AzureContractError("ACR run type is not the exact quick build")
    status = properties.get("status")
    if not isinstance(status, str) or not status:
        raise AzureContractError("ACR run status is missing")
    if "runRequest" in properties:
        raise AzureContractError("ACR child Run unexpectedly carries build request")
    _, request_sha256 = _validate_acr_run_request(
        authenticated_run_request,
        build_provenance=provenance,
        build_provenance_sha256_value=build_provenance_sha256_value,
        staging_tag=staging_tag,
        expected_run_request_sha256=expected_run_request_sha256,
    )
    repository = provenance["acr"]["repository"]
    raw_outputs = properties.get("outputImages")
    output_digest: str | None = None
    completed = status == "Succeeded"
    if completed or require_succeeded or raw_outputs not in (None, []):
        if not isinstance(raw_outputs, list) or len(raw_outputs) != 1:
            raise AzureContractError("ACR completed output image is not singular")
        output = raw_outputs[0]
        if (
            not isinstance(output, Mapping)
            or set(output) != BUILD_OUTPUT_IMAGE_FIELDS
        ):
            raise AzureContractError("ACR completed output image is invalid")
        output_digest = output.get("digest")
        if (
            output.get("registry") != provenance["acr"]["login_server"]
            or output.get("repository") != repository
            or output.get("tag") != staging_tag
            or not isinstance(output_digest, str)
            or not _IMAGE_DIGEST_PATTERN.fullmatch(output_digest)
        ):
            raise AzureContractError("ACR completed output image differs")
    if require_succeeded and status != "Succeeded":
        raise AzureContractError("ACR build is not durably succeeded")
    if expected_digest is not None and (
        not isinstance(expected_digest, str)
        or not _IMAGE_DIGEST_PATTERN.fullmatch(expected_digest)
        or output_digest != expected_digest
    ):
        raise AzureContractError("ACR output digest differs from durable claim")
    return {
        "run_id": run_id,
        "status": status,
        "run_request_sha256": request_sha256,
        "build_provenance_sha256": build_provenance_sha256_value,
        "source_binding_sha256": provenance["source_binding_sha256"],
        "output_repository": repository if output_digest is not None else None,
        "output_tag": staging_tag if output_digest is not None else None,
        "output_digest": output_digest,
    }


def validate_acr_task_run(
    task_run: Mapping[str, Any],
    *,
    expected_task_run_name: str,
    expected_acr_resource_id: str,
    build_provenance: Mapping[str, Any],
    build_provenance_sha256_value: str,
    staging_tag: str,
    require_succeeded: bool = False,
    expected_digest: str | None = None,
    expected_run_id: str | None = None,
    expected_run_request_sha256: str | None = None,
) -> dict[str, Any]:
    """Authenticate a named TaskRun, its persisted request, and child Run."""
    if (
        not isinstance(expected_task_run_name, str)
        or not _TASK_RUN_NAME_PATTERN.fullmatch(expected_task_run_name)
    ):
        raise AzureContractError("ACR TaskRun name is invalid")
    provenance = validate_build_provenance(
        build_provenance,
        expected_sha256=build_provenance_sha256_value,
    )
    if (
        not isinstance(expected_acr_resource_id, str)
        or expected_acr_resource_id.casefold()
        != provenance["acr"]["resource_id"].casefold()
    ):
        raise AzureContractError("ACR TaskRun registry identity differs")
    normalized = normalize_azure_value(task_run)
    if not isinstance(normalized, Mapping):
        raise AzureContractError("ACR TaskRun is not an object")
    expected_resource_id = (
        f"{expected_acr_resource_id}/taskRuns/{expected_task_run_name}"
    )
    resource_type = normalized.get("type")
    if (
        normalized.get("name") != expected_task_run_name
        or not isinstance(normalized.get("id"), str)
        or normalized["id"].casefold() != expected_resource_id.casefold()
        or not isinstance(resource_type, str)
        or resource_type.casefold()
        != "microsoft.containerregistry/registries/taskruns"
    ):
        raise AzureContractError("ACR TaskRun resource identity differs")
    location = normalized.get("location")
    if (
        (location is not None and location != provenance["acr"]["location"])
        or normalized.get("identity") not in (None, {})
    ):
        raise AzureContractError("ACR TaskRun location/identity differs")
    properties = normalized.get("properties")
    allowed_properties = {
        "provisioningState",
        "runRequest",
        "runResult",
        "forceUpdateTag",
    }
    if (
        not isinstance(properties, Mapping)
        or not {"provisioningState", "runRequest"}.issubset(properties)
        or not set(properties).issubset(allowed_properties)
    ):
        raise AzureContractError("ACR TaskRun properties are not exact")
    request, request_sha256 = _validate_acr_run_request(
        properties["runRequest"],
        build_provenance=provenance,
        build_provenance_sha256_value=build_provenance_sha256_value,
        staging_tag=staging_tag,
        expected_run_request_sha256=expected_run_request_sha256,
    )
    if (
        "forceUpdateTag" in properties
        and properties["forceUpdateTag"] != request_sha256
    ):
        raise AzureContractError("ACR TaskRun forceUpdateTag differs")
    provisioning_state = properties["provisioningState"]
    if provisioning_state not in {
        "Creating",
        "Updating",
        "Deleting",
        "Succeeded",
        "Failed",
        "Canceled",
    }:
        raise AzureContractError("ACR TaskRun provisioning state is invalid")
    if provisioning_state in {"Updating", "Deleting", "Failed", "Canceled"}:
        raise AzureContractError("ACR TaskRun is not in an adoptable state")
    run_result = properties.get("runResult")
    if not isinstance(run_result, Mapping):
        if (
            run_result is not None
            or provisioning_state != "Creating"
            or require_succeeded
            or expected_digest is not None
            or expected_run_id is not None
        ):
            raise AzureContractError("ACR TaskRun child Run is unavailable")
        return {
            "task_run_name": expected_task_run_name,
            "task_run_resource_id": expected_resource_id,
            "task_run_provisioning_state": provisioning_state,
            "run_id": None,
            "status": provisioning_state,
            "run_request_sha256": request_sha256,
            "build_provenance_sha256": build_provenance_sha256_value,
            "source_binding_sha256": provenance["source_binding_sha256"],
            "output_repository": None,
            "output_tag": None,
            "output_digest": None,
        }
    run = validate_acr_build_run(
        run_result,
        authenticated_run_request=request,
        build_provenance=provenance,
        build_provenance_sha256_value=build_provenance_sha256_value,
        staging_tag=staging_tag,
        require_succeeded=require_succeeded,
        expected_digest=expected_digest,
        expected_run_id=expected_run_id,
        expected_run_request_sha256=request_sha256,
        expected_acr_resource_id=expected_acr_resource_id,
    )
    if require_succeeded and provisioning_state != "Succeeded":
        raise AzureContractError("ACR TaskRun is not durably provisioned")
    if provisioning_state != "Succeeded":
        run["status"] = provisioning_state
    return {
        "task_run_name": expected_task_run_name,
        "task_run_resource_id": expected_resource_id,
        "task_run_provisioning_state": provisioning_state,
        **run,
    }


def validate_oci_image_artifacts(
    manifest_bytes: bytes,
    config_bytes: bytes,
    *,
    expected_manifest_digest: str,
    expected_provenance_sha256: str,
) -> dict[str, str]:
    if (
        not isinstance(expected_manifest_digest, str)
        or not _IMAGE_DIGEST_PATTERN.fullmatch(expected_manifest_digest)
        or hashlib.sha256(manifest_bytes).hexdigest()
        != expected_manifest_digest.removeprefix("sha256:")
    ):
        raise AzureContractError("OCI manifest digest mismatch")
    try:
        manifest = normalize_azure_value(
            json.loads(manifest_bytes.decode("utf-8"))
        )
        config = normalize_azure_value(json.loads(config_bytes.decode("utf-8")))
    except (UnicodeError, json.JSONDecodeError):
        raise AzureContractError("OCI manifest/config is invalid JSON") from None
    if (
        not isinstance(manifest, Mapping)
        or type(manifest.get("schemaVersion")) is not int
        or manifest.get("schemaVersion") != 2
        or not isinstance(manifest.get("config"), Mapping)
    ):
        raise AzureContractError("OCI image manifest is invalid")
    config_digest = manifest["config"].get("digest")
    if (
        not isinstance(config_digest, str)
        or not _IMAGE_DIGEST_PATTERN.fullmatch(config_digest)
        or hashlib.sha256(config_bytes).hexdigest()
        != config_digest.removeprefix("sha256:")
    ):
        raise AzureContractError("OCI image config digest mismatch")
    labels = (
        config.get("config", {}).get("Labels")
        if isinstance(config, Mapping)
        and isinstance(config.get("config"), Mapping)
        else None
    )
    if (
        not isinstance(expected_provenance_sha256, str)
        or not _SHA256_PATTERN.fullmatch(expected_provenance_sha256)
        or not isinstance(labels, Mapping)
        or labels.get(BUILD_PROVENANCE_LABEL)
        != expected_provenance_sha256
    ):
        raise AzureContractError("OCI build provenance label mismatch")
    return {
        "schema_version": OCI_VERIFICATION_SCHEMA_VERSION,
        "image_digest": expected_manifest_digest,
        "manifest_sha256": expected_manifest_digest.removeprefix("sha256:"),
        "config_digest": config_digest,
        "config_sha256": config_digest.removeprefix("sha256:"),
        "provenance_label": {
            "name": BUILD_PROVENANCE_LABEL,
            "value": expected_provenance_sha256,
        },
    }


def validate_oci_verification_evidence(
    evidence: Mapping[str, Any],
    *,
    expected_image_digest: str,
    expected_provenance_sha256: str,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Authenticate complete nonsecret evidence from OCI manifest/config bytes."""
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "schema_version",
        "image_digest",
        "manifest_sha256",
        "config_digest",
        "config_sha256",
        "provenance_label",
    }:
        raise AzureContractError("OCI verification evidence fields are not exact")
    label = evidence["provenance_label"]
    if (
        evidence["schema_version"] != OCI_VERIFICATION_SCHEMA_VERSION
        or not isinstance(expected_image_digest, str)
        or not _IMAGE_DIGEST_PATTERN.fullmatch(expected_image_digest)
        or evidence["image_digest"] != expected_image_digest
        or evidence["manifest_sha256"]
        != expected_image_digest.removeprefix("sha256:")
        or not isinstance(evidence["config_digest"], str)
        or not _IMAGE_DIGEST_PATTERN.fullmatch(evidence["config_digest"])
        or evidence["config_sha256"]
        != evidence["config_digest"].removeprefix("sha256:")
        or not isinstance(expected_provenance_sha256, str)
        or not _SHA256_PATTERN.fullmatch(expected_provenance_sha256)
        or not isinstance(label, Mapping)
        or set(label) != {"name", "value"}
        or label["name"] != BUILD_PROVENANCE_LABEL
        or label["value"] != expected_provenance_sha256
    ):
        raise AzureContractError("OCI verification evidence differs")
    checked = {
        "schema_version": OCI_VERIFICATION_SCHEMA_VERSION,
        "image_digest": expected_image_digest,
        "manifest_sha256": evidence["manifest_sha256"],
        "config_digest": evidence["config_digest"],
        "config_sha256": evidence["config_sha256"],
        "provenance_label": {
            "name": BUILD_PROVENANCE_LABEL,
            "value": expected_provenance_sha256,
        },
    }
    digest = hashlib.sha256(_canonical_bytes(checked)).hexdigest()
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str)
        or not _SHA256_PATTERN.fullmatch(expected_sha256)
        or digest != expected_sha256
    ):
        raise AzureContractError("OCI verification evidence SHA-256 mismatch")
    return checked


def oci_verification_evidence_sha256(evidence: Mapping[str, Any]) -> str:
    image_digest = (
        evidence.get("image_digest") if isinstance(evidence, Mapping) else None
    )
    label = (
        evidence.get("provenance_label")
        if isinstance(evidence, Mapping)
        else None
    )
    provenance_sha256 = (
        label.get("value") if isinstance(label, Mapping) else None
    )
    checked = validate_oci_verification_evidence(
        evidence,
        expected_image_digest=image_digest,
        expected_provenance_sha256=provenance_sha256,
    )
    return hashlib.sha256(_canonical_bytes(checked)).hexdigest()


def validate_image_binding_oci_evidence(
    image_binding: Mapping[str, Any],
    *,
    expected_image_digest: str,
    expected_provenance_sha256: str,
    expected_evidence_sha256: str,
) -> dict[str, Any]:
    """Fail crash finalization closed when its OCI evidence is absent or forged."""
    if not isinstance(image_binding, Mapping) or "oci_verification" not in image_binding:
        raise AzureContractError("image binding omits OCI verification evidence")
    return validate_oci_verification_evidence(
        image_binding["oci_verification"],
        expected_image_digest=expected_image_digest,
        expected_provenance_sha256=expected_provenance_sha256,
        expected_sha256=expected_evidence_sha256,
    )


def validate_image_binding_record(
    data: bytes,
    *,
    expected_sha256: str,
    expected_source_commit: str | None = None,
    expected_acr_resource_id: str | None = None,
    expected_login_server: str | None = None,
    expected_repository: str | None = None,
) -> dict[str, Any]:
    """Validate the complete canonical nonsecret image finalization record."""
    try:
        return _load_core().validate_image_binding(
            data,
            expected_sha256=expected_sha256,
            expected_source_commit=expected_source_commit,
            expected_acr_resource_id=expected_acr_resource_id,
            expected_login_server=expected_login_server,
            expected_repository=expected_repository,
        )
    except Exception:
        raise AzureContractError("immutable image binding is invalid") from None


def validate_live_image_binding(
    image_binding_bytes: bytes,
    *,
    expected_sha256: str,
    live_task_run: Mapping[str, Any],
    manifest_bytes: bytes,
    config_bytes: bytes,
    resolved_final_digest: str,
    tag_write_enabled: str | bool,
    tag_delete_enabled: str | bool,
    manifest_write_enabled: str | bool,
    manifest_delete_enabled: str | bool,
    expected_source_commit: str,
    expected_acr_resource_id: str,
    expected_login_server: str,
    expected_repository: str,
) -> dict[str, Any]:
    """Reauthenticate live TaskRun, child Run, OCI bytes, tag, and locks."""
    binding = validate_image_binding_record(
        image_binding_bytes,
        expected_sha256=expected_sha256,
        expected_source_commit=expected_source_commit,
        expected_acr_resource_id=expected_acr_resource_id,
        expected_login_server=expected_login_server,
        expected_repository=expected_repository,
    )
    run = validate_acr_task_run(
        live_task_run,
        expected_task_run_name=binding["acr_build_task_run_name"],
        expected_acr_resource_id=expected_acr_resource_id,
        build_provenance=binding["build_provenance"],
        build_provenance_sha256_value=binding["build_provenance_sha256"],
        staging_tag=binding["staging_image_tag"],
        require_succeeded=True,
        expected_digest=binding["image_digest"],
        expected_run_id=binding["acr_build_run_id"],
        expected_run_request_sha256=binding["build_run_request_sha256"],
    )
    oci = validate_oci_image_artifacts(
        manifest_bytes,
        config_bytes,
        expected_manifest_digest=binding["image_digest"],
        expected_provenance_sha256=binding["build_provenance_sha256"],
    )
    if (
        _canonical_bytes(oci)
        != _canonical_bytes(binding["oci_verification"])
        or oci_verification_evidence_sha256(oci)
        != binding["oci_verification_sha256"]
        or resolved_final_digest != binding["image_digest"]
    ):
        raise AzureContractError("live image digest/OCI evidence differs")

    def immutable(value: str | bool, name: str) -> bool:
        if isinstance(value, str):
            normalized = value.replace("\r", "").casefold()
            if normalized not in {"true", "false"}:
                raise AzureContractError(f"{name} lock evidence is invalid")
            checked = normalized == "true"
        elif type(value) is bool:
            checked = value
        else:
            raise AzureContractError(f"{name} lock evidence is invalid")
        if checked:
            raise AzureContractError(f"{name} is mutable")
        return checked

    locks = {
        "tag_write_enabled": immutable(tag_write_enabled, "final tag write"),
        "tag_delete_enabled": immutable(tag_delete_enabled, "final tag delete"),
        "manifest_write_enabled": immutable(
            manifest_write_enabled, "manifest write"
        ),
        "manifest_delete_enabled": immutable(
            manifest_delete_enabled, "manifest delete"
        ),
    }
    if _canonical_bytes(locks) != _canonical_bytes(
        binding["changeable_attributes"]
    ):
        raise AzureContractError("live image lock evidence differs")
    return {
        "status": "LIVE_IMAGE_BINDING_AUTHENTICATED",
        "image_binding_sha256": expected_sha256,
        "source_commit": binding["source_commit"],
        "acr_build_task_run_name": run["task_run_name"],
        "acr_build_task_run_resource_id": run["task_run_resource_id"],
        "acr_build_run_id": run["run_id"],
        "build_run_request_sha256": run["run_request_sha256"],
        "image_digest": binding["image_digest"],
        "oci_verification_sha256": binding["oci_verification_sha256"],
        "changeable_attributes": locks,
    }


def _empty(value: Any) -> bool:
    return value in (None, [], {})


def canonical_job_projection(
    record: Mapping[str, Any],
    expected_body: Mapping[str, Any],
) -> dict[str, Any]:
    """Project every ACA code/data injection surface and fail on optional ones."""
    identity = record.get("identity") or {}
    properties = record.get("properties") or {}
    if not isinstance(identity, Mapping) or not isinstance(properties, Mapping):
        raise AzureContractError("live job body has an invalid object surface")
    configuration = properties.get("configuration") or {}
    template = properties.get("template") or {}
    if not isinstance(configuration, Mapping) or not isinstance(template, Mapping):
        raise AzureContractError("live job body has an invalid object surface")
    allowed_configuration = {
        "triggerType",
        "replicaTimeout",
        "replicaRetryLimit",
        "manualTriggerConfig",
        "registries",
        "secrets",
        "eventTriggerConfig",
        "scheduleTriggerConfig",
        "dapr",
        "identitySettings",
    }
    if set(configuration) - allowed_configuration:
        raise AzureContractError("live job exposes an unknown configuration surface")
    allowed_template = {
        "containers",
        "initContainers",
        "volumes",
        "serviceBinds",
        "terminationGracePeriodSeconds",
    }
    if set(template) - allowed_template:
        raise AzureContractError("live job exposes an unknown template surface")
    for name in ("serviceBinds", "terminationGracePeriodSeconds"):
        if not _empty(template.get(name)):
            raise AzureContractError(f"live job exposes forbidden template {name}")
    expected_tags = expected_body.get("tags") or {}
    protected_tags = sorted(expected_tags)
    tags = record.get("tags") or {}
    if set(tags) != set(expected_tags):
        raise AzureContractError("live job omits a protected tag")

    secrets = configuration.get("secrets", [])
    if secrets is None:
        secrets = []
    if secrets != []:
        raise AzureContractError("live job contains a secret")
    for name in (
        "eventTriggerConfig",
        "scheduleTriggerConfig",
        "dapr",
        "identitySettings",
    ):
        if not _empty(configuration.get(name)):
            raise AzureContractError(f"live job exposes forbidden {name}")

    containers = template.get("containers")
    init_containers = template.get("initContainers", [])
    volumes = template.get("volumes", [])
    if not isinstance(containers, list) or len(containers) != 1:
        raise AzureContractError("live job must contain exactly one container")
    if init_containers not in (None, []) or volumes not in (None, []):
        raise AzureContractError("live job has an init container or volume")
    container = containers[0]
    if not isinstance(container, Mapping):
        raise AzureContractError("live job container is invalid")
    allowed_container = {
        "name",
        "image",
        "command",
        "args",
        "env",
        "resources",
        "volumeMounts",
        "probes",
        "lifecycle",
        "securityContext",
    }
    if set(container) - allowed_container:
        raise AzureContractError("live job exposes an unknown container surface")
    env = container.get("env", [])
    if not isinstance(env, list) or any(
        not isinstance(item, Mapping)
        or set(item) != {"name", "value"}
        or "secretRef" in item
        for item in env
    ):
        raise AzureContractError("live job environment is not the exact value allowlist")
    volume_mounts = container.get("volumeMounts", [])
    probes = container.get("probes", [])
    if volume_mounts not in (None, []) or probes not in (None, []):
        raise AzureContractError("live job has a mount or probe")
    if not _empty(container.get("lifecycle")) or not _empty(
        container.get("securityContext")
    ):
        raise AzureContractError("live job has lifecycle or security context injection")

    return {
        "location": str(record.get("location", "")).casefold(),
        "identity": {
            "type": identity.get("type"),
            "userAssignedIdentityIds": sorted(
                (identity.get("userAssignedIdentities") or {}).keys()
            ),
        },
        "protectedTags": {name: tags[name] for name in protected_tags},
        "properties": {
            "environmentId": properties.get("environmentId"),
            "workloadProfileName": properties.get("workloadProfileName"),
            "configuration": {
                "triggerType": configuration.get("triggerType"),
                "replicaTimeout": configuration.get("replicaTimeout"),
                "replicaRetryLimit": configuration.get("replicaRetryLimit"),
                "manualTriggerConfig": configuration.get("manualTriggerConfig"),
                "registries": configuration.get("registries", []),
                "secrets": secrets,
                "eventTriggerConfig": None,
                "scheduleTriggerConfig": None,
                "dapr": None,
                "identitySettings": None,
            },
            "template": {
                "containers": [
                    {
                        "name": container.get("name"),
                        "image": container.get("image"),
                        "command": container.get("command"),
                        "args": container.get("args"),
                        "env": env,
                        "resources": container.get("resources"),
                        "volumeMounts": [],
                        "probes": [],
                        "lifecycle": None,
                        "securityContext": None,
                    }
                ],
                "initContainers": [],
                "volumes": [],
            },
        },
    }


def compare_job_with_body(
    live_job: Mapping[str, Any], expected_body: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    expected = canonical_job_projection(expected_body, expected_body)
    live = canonical_job_projection(live_job, expected_body)
    if _canonical_bytes(live) != _canonical_bytes(expected):
        raise AzureContractError(
            "canonical live job projection differs from the protected body"
        )
    data = _canonical_bytes(live)
    return live, hashlib.sha256(data).hexdigest()


def validate_live_job_projection_hash(
    live_job: Mapping[str, Any],
    *,
    expected_job_resource_id: str,
    expected_job_name: str,
    expected_sha256: str,
) -> tuple[dict[str, Any], str]:
    """Authenticate an immutable live Job projection without any ETag contract."""
    live = normalize_azure_value(live_job)
    resource_id = _require_safe_string(
        expected_job_resource_id, "expected Job resource ID"
    )
    job_name = _require_safe_string(expected_job_name, "expected Job name")
    if (
        not isinstance(live, Mapping)
        or str(live.get("id", "")).casefold() != resource_id.casefold()
        or live.get("name") != job_name
        or str(live.get("type", "")).casefold() != "microsoft.app/jobs"
        or not isinstance(live.get("properties"), Mapping)
        or live["properties"].get("provisioningState") != "Succeeded"
    ):
        raise AzureContractError("live immutable Job identity/state differs")
    projection = canonical_job_projection(live, live)
    projection_sha256 = hashlib.sha256(
        _canonical_bytes(projection)
    ).hexdigest()
    if projection_sha256 != _require_sha256_value(
        expected_sha256, "expected Job projection SHA-256"
    ):
        raise AzureContractError("live immutable Job projection hash differs")
    return projection, projection_sha256


def _resource_id(record: Mapping[str, Any]) -> str:
    value = record.get("id")
    if not isinstance(value, str):
        raise AzureContractError("Azure resource omits its ID")
    return value


def validate_private_endpoint_topology(
    destination: Mapping[str, Any],
    *,
    storage: Mapping[str, Any],
    storage_container: Mapping[str, Any],
    environment: Mapping[str, Any],
    workload_profile_states: Sequence[Mapping[str, Any]],
    private_endpoint: Mapping[str, Any],
    storage_private_link_resources: Sequence[Mapping[str, Any]],
    storage_connections: Sequence[Mapping[str, Any]],
    dns_zone_groups: Sequence[Mapping[str, Any]],
    dns_links: Sequence[Mapping[str, Any]],
    dns_record: Mapping[str, Any],
    nics: Sequence[Mapping[str, Any]],
    resolved_ips: Sequence[str],
) -> dict[str, Any]:
    """Authenticate Blob on both storage and PE sides, plus NIC and DNS topology."""
    core = _load_core()
    checked = core.validate_runtime_azure_destination(destination)
    network = checked["network"]
    storage_binding = checked["storage"]
    apps = checked["container_apps"]
    expected_ips = set(network["private_endpoint_nic_private_ips"])
    profile_name = apps["workload_profile"]
    matching_profiles = [
        item
        for item in workload_profile_states
        if isinstance(item, Mapping) and item.get("name") == profile_name
    ]
    if len(matching_profiles) != 1:
        raise AzureContractError(
            "live workload profile membership is not exact"
        )
    profile_properties = matching_profiles[0].get("properties")
    if (
        not isinstance(profile_properties, Mapping)
        or profile_properties.get("workloadProfileType") != "Consumption"
    ):
        raise AzureContractError(
            "live workload profile is not explicitly Consumption"
        )
    if _resource_id(storage).casefold() != storage_binding[
        "resource_id"
    ].casefold():
        raise AzureContractError("storage response is for another account")
    storage_properties = storage.get("properties")
    if (
        storage.get("name") != storage_binding["account_name"]
        or not isinstance(storage_properties, Mapping)
        or storage_properties.get("publicNetworkAccess") != "Disabled"
        or storage_properties.get("allowSharedKeyAccess") is not False
        or storage_properties.get("allowBlobPublicAccess")
        is not storage_binding["allow_blob_public_access"]
        or (storage_properties.get("networkAcls") or {}).get("defaultAction")
        != "Deny"
    ):
        raise AzureContractError("storage network/key posture changed")
    expected_container_id = (
        f"{storage_binding['resource_id']}/blobServices/default/containers/"
        f"{storage_binding['container']}"
    )
    container_properties = storage_container.get("properties")
    if (
        _resource_id(storage_container).casefold()
        != expected_container_id.casefold()
        or str(storage_container.get("name", "")).rsplit("/", 1)[-1]
        != storage_binding["container"]
        or str(storage_container.get("type", "")).casefold()
        != "microsoft.storage/storageaccounts/blobservices/containers"
        or not isinstance(container_properties, Mapping)
        or container_properties.get("publicAccess")
        is not storage_binding["container_public_access"]
    ):
        raise AzureContractError(
            "bound Blob container is missing, ambiguous, or publicly accessible"
        )
    private_link_group_id = network["private_link_group_id"]
    private_link_subresource = network["private_link_subresource"]
    expected_private_link_resource_id = (
        f"{storage_binding['resource_id']}/privateLinkResources/"
        f"{private_link_subresource}"
    )
    matching_private_link_resources = [
        item
        for item in storage_private_link_resources
        if isinstance(item, Mapping)
        and isinstance(item.get("id"), str)
        and item["id"].casefold()
        == expected_private_link_resource_id.casefold()
    ]
    if len(matching_private_link_resources) != 1:
        raise AzureContractError(
            "storage Blob private-link resource membership is not exact"
        )
    private_link_resource = matching_private_link_resources[0]
    private_link_resource_properties = private_link_resource.get("properties")
    if (
        not isinstance(private_link_resource_properties, Mapping)
        or str(private_link_resource.get("name", "")).rsplit("/", 1)[-1]
        != private_link_subresource
        or str(private_link_resource.get("type", "")).casefold()
        != "microsoft.storage/storageaccounts/privatelinkresources"
        or private_link_resource_properties.get("groupId")
        != private_link_group_id
    ):
        raise AzureContractError(
            "storage private-link resource is not explicit Blob evidence"
        )
    if _resource_id(environment).casefold() != apps[
        "environment_resource_id"
    ].casefold() or (
        (environment.get("properties") or {})
        .get("vnetConfiguration", {})
        .get("infrastructureSubnetId", "")
        .casefold()
        != network["infrastructure_subnet_resource_id"].casefold()
    ):
        raise AzureContractError("Container Apps environment subnet changed")
    if (
        _resource_id(private_endpoint).casefold()
        != network["private_endpoint_resource_id"].casefold()
        or private_endpoint.get("name") != network["private_endpoint_name"]
    ):
        raise AzureContractError("private endpoint response is for another resource")
    pe_properties = private_endpoint.get("properties") or {}
    if (
        (pe_properties.get("subnet") or {}).get("id", "").casefold()
        != network["private_endpoint_subnet_resource_id"].casefold()
        or pe_properties.get("manualPrivateLinkServiceConnections") not in (
            None,
            [],
        )
    ):
        raise AzureContractError("private endpoint subnet/manual connection changed")
    links = pe_properties.get("privateLinkServiceConnections")
    if not isinstance(links, list) or len(links) != 1:
        raise AzureContractError("private endpoint connection membership is not exact")
    link = links[0]
    link_properties = link.get("properties") or {}
    if (
        link.get("name") != network["private_link_connection_name"]
        or link_properties.get("privateLinkServiceId", "").casefold()
        != storage_binding["resource_id"].casefold()
        or _canonical_bytes(link_properties.get("groupIds"))
        != _canonical_bytes([private_link_group_id])
        or (link_properties.get("privateLinkServiceConnectionState") or {}).get(
            "status"
        )
        != "Approved"
    ):
        raise AzureContractError("private endpoint is not the exact approved Blob link")
    if len(storage_connections) != 1:
        raise AzureContractError("storage private connection membership is not exact")
    storage_connection = storage_connections[0]
    connection_properties = storage_connection.get("properties") or {}
    connection_group_ids = connection_properties.get("groupIds")
    if (
        _resource_id(storage_connection).casefold()
        != network[
            "storage_private_endpoint_connection_resource_id"
        ].casefold()
        or str(storage_connection.get("name", "")).rsplit("/", 1)[-1]
        != network["storage_private_endpoint_connection_name"]
        or
        (connection_properties.get("privateEndpoint") or {})
        .get("id", "")
        .casefold()
        != network["private_endpoint_resource_id"].casefold()
        or (
            connection_properties.get("privateLinkServiceConnectionState") or {}
        ).get("status")
        != "Approved"
        or (
            connection_group_ids is not None
            and _canonical_bytes(connection_group_ids)
            != _canonical_bytes([private_link_group_id])
        )
    ):
        raise AzureContractError("storage-side private connection is not exact")

    endpoint_nic_ids = {
        item.get("id", "").casefold()
        for item in pe_properties.get("networkInterfaces") or []
        if isinstance(item, Mapping)
    }
    if (
        not endpoint_nic_ids
        or len(nics) != len(endpoint_nic_ids)
        or {_resource_id(item).casefold() for item in nics} != endpoint_nic_ids
    ):
        raise AzureContractError("private endpoint NIC membership is not exact")
    nic_ips = {
        configuration.get("properties", {}).get("privateIPAddress")
        for nic in nics
        for configuration in (nic.get("properties") or {}).get(
            "ipConfigurations", []
        )
        if isinstance(configuration, Mapping)
    }
    if None in nic_ips or nic_ips != expected_ips:
        raise AzureContractError("private endpoint NIC private IPs changed")
    fqdn = f"{storage_binding['account_name']}.blob.core.windows.net"
    custom_dns = pe_properties.get("customDnsConfigs")
    if (
        not isinstance(custom_dns, list)
        or len(custom_dns) != 1
        or custom_dns[0].get("fqdn") != fqdn
        or set(custom_dns[0].get("ipAddresses") or []) != expected_ips
    ):
        raise AzureContractError("private endpoint Blob DNS configuration changed")

    if len(dns_zone_groups) != 1:
        raise AzureContractError("private DNS zone-group membership is not exact")
    group = dns_zone_groups[0]
    group_configs = (group.get("properties") or {}).get("privateDnsZoneConfigs")
    if (
        _resource_id(group).casefold()
        != (
            f"{network['private_endpoint_resource_id']}/privateDnsZoneGroups/"
            f"{network['private_dns_zone_group_name']}"
        ).casefold()
        or str(group.get("name", "")).rsplit("/", 1)[-1]
        != network["private_dns_zone_group_name"]
        or not isinstance(group_configs, list)
        or len(group_configs) != 1
        or (group_configs[0].get("properties") or {})
        .get("privateDnsZoneId", "")
        .casefold()
        != network["private_dns_zone_resource_id"].casefold()
    ):
        raise AzureContractError("private DNS zone group is not exact")
    if len(dns_links) != 1:
        raise AzureContractError("private DNS VNet-link membership is not exact")
    dns_link = dns_links[0]
    dns_link_properties = dns_link.get("properties") or {}
    if (
        _resource_id(dns_link).casefold()
        != (
            f"{network['private_dns_zone_resource_id']}/virtualNetworkLinks/"
            f"{network['private_dns_vnet_link_name']}"
        ).casefold()
        or str(dns_link.get("name", "")).rsplit("/", 1)[-1]
        != network["private_dns_vnet_link_name"]
        or (dns_link_properties.get("virtualNetwork") or {})
        .get("id", "")
        .casefold()
        != network["vnet_resource_id"].casefold()
        or dns_link_properties.get("provisioningState") != "Succeeded"
    ):
        raise AzureContractError("private DNS VNet link is not exact")
    record_ips = {
        item.get("ipv4Address")
        for item in (dns_record.get("properties") or {}).get("aRecords", [])
        if isinstance(item, Mapping)
    }
    if (
        _resource_id(dns_record).casefold()
        != (
            f"{network['private_dns_zone_resource_id']}/A/"
            f"{storage_binding['account_name']}"
        ).casefold()
        or str(dns_record.get("name", "")).rsplit("/", 1)[-1]
        != storage_binding["account_name"]
        or None in record_ips
        or record_ips != expected_ips
        or set(normalize_azure_value(list(resolved_ips))) != expected_ips
    ):
        raise AzureContractError("Blob DNS does not resolve only to PE NIC IPs")
    return {
        "workload_profile": {
            "name": profile_name,
            "workload_profile_type": "Consumption",
        },
        "storage_resource_id": storage_binding["resource_id"],
        "storage_container_resource_id": expected_container_id,
        "storage_allow_blob_public_access": storage_binding[
            "allow_blob_public_access"
        ],
        "storage_container_public_access": storage_binding[
            "container_public_access"
        ],
        "private_endpoint_resource_id": network["private_endpoint_resource_id"],
        "private_endpoint_ips": sorted(expected_ips),
        "private_link_group_id": private_link_group_id,
        "private_link_subresource": private_link_subresource,
        "private_dns_zone": "privatelink.blob.core.windows.net",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("new-id", allow_abbrev=False)
    get = subparsers.add_parser("get", allow_abbrev=False)
    get.add_argument("--json", type=Path, required=True)
    get.add_argument("--field", required=True)
    arm = subparsers.add_parser("arm-list", allow_abbrev=False)
    arm.add_argument("--url", required=True)
    arm.add_argument("--output", type=Path, required=True)
    coordination = subparsers.add_parser(
        "validate-coordination-zone", allow_abbrev=False
    )
    coordination.add_argument("--binding", type=Path, required=True)
    coordination.add_argument("--zone", type=Path, required=True)
    coordination.add_argument("--links", type=Path, required=True)
    coordination.add_argument("--lock", type=Path, required=True)
    coordination.add_argument("--output", type=Path, required=True)
    domain = subparsers.add_parser("claim-domain", allow_abbrev=False)
    domain.add_argument("--kind", choices=sorted(CLAIM_KINDS), required=True)
    domain.add_argument("--binding", type=Path, required=True)
    envelope = subparsers.add_parser("create-claim-envelope", allow_abbrev=False)
    envelope.add_argument("--kind", choices=sorted(CLAIM_KINDS), required=True)
    envelope.add_argument("--domain-sha256", required=True)
    envelope.add_argument("--claims", type=Path, required=True)
    envelope.add_argument("--output", type=Path, required=True)
    record_body = subparsers.add_parser(
        "create-txt-record-body", allow_abbrev=False
    )
    record_body.add_argument("--envelope", type=Path, required=True)
    record_body.add_argument("--ttl", type=int, required=True)
    record_body.add_argument("--output", type=Path, required=True)
    record_body.add_argument("--print-name", action="store_true")
    validate_record = subparsers.add_parser(
        "validate-txt-record", allow_abbrev=False
    )
    validate_record.add_argument("--record", type=Path, required=True)
    validate_record.add_argument("--zone-resource-id", required=True)
    validate_record.add_argument("--record-name", required=True)
    validate_record.add_argument("--ttl", type=int, required=True)
    validate_record.add_argument("--expected-envelope", type=Path)
    validate_record.add_argument("--expected-kind", choices=sorted(CLAIM_KINDS))
    validate_record.add_argument("--expected-domain-sha256")
    validate_record.add_argument("--output", type=Path, required=True)
    membership = subparsers.add_parser(
        "execution-membership", allow_abbrev=False
    )
    membership.add_argument("--executions", type=Path, required=True)
    membership.add_argument("--output", type=Path, required=True)
    adopt = subparsers.add_parser("adopt-remove-one", allow_abbrev=False)
    adopt.add_argument("--baseline", type=Path, required=True)
    adopt.add_argument("--executions", type=Path, required=True)
    adopt.add_argument("--output", type=Path, required=True)
    remote_source = subparsers.add_parser(
        "exact-remote-source", allow_abbrev=False
    )
    remote_source.add_argument("--repository-url", required=True)
    remote_source.add_argument("--source-commit", required=True)
    provenance = subparsers.add_parser(
        "build-provenance", allow_abbrev=False
    )
    provenance.add_argument("--source-binding", type=Path, required=True)
    provenance.add_argument("--acr-resource-id", required=True)
    provenance.add_argument("--login-server", required=True)
    provenance.add_argument("--acr-location", required=True)
    provenance.add_argument(
        "--coordination-binding", type=Path, required=True
    )
    provenance.add_argument("--output", type=Path, required=True)
    create_task_run = subparsers.add_parser(
        "create-acr-task-run", allow_abbrev=False
    )
    create_task_run.add_argument(
        "--build-provenance", type=Path, required=True
    )
    create_task_run.add_argument(
        "--build-provenance-sha256", required=True
    )
    create_task_run.add_argument("--staging-tag", required=True)
    create_task_run.add_argument("--output", type=Path, required=True)
    validate_task_run = subparsers.add_parser(
        "validate-acr-task-run", allow_abbrev=False
    )
    validate_task_run.add_argument("--task-run", type=Path, required=True)
    validate_task_run.add_argument("--expected-task-run-name", required=True)
    validate_task_run.add_argument("--expected-acr-resource-id", required=True)
    validate_task_run.add_argument(
        "--build-provenance", type=Path, required=True
    )
    validate_task_run.add_argument(
        "--build-provenance-sha256", required=True
    )
    validate_task_run.add_argument("--staging-tag", required=True)
    validate_task_run.add_argument("--require-succeeded", action="store_true")
    validate_task_run.add_argument("--expected-digest")
    validate_task_run.add_argument("--expected-run-id")
    validate_task_run.add_argument("--expected-run-request-sha256")
    validate_task_run.add_argument("--output", type=Path, required=True)
    validate_image = subparsers.add_parser(
        "validate-oci-image", allow_abbrev=False
    )
    validate_image.add_argument("--manifest", type=Path, required=True)
    validate_image.add_argument("--config", type=Path, required=True)
    validate_image.add_argument("--expected-manifest-digest", required=True)
    validate_image.add_argument(
        "--expected-provenance-sha256", required=True
    )
    validate_image.add_argument("--output", type=Path, required=True)
    validate_evidence = subparsers.add_parser(
        "validate-oci-evidence", allow_abbrev=False
    )
    validate_evidence.add_argument("--evidence", type=Path, required=True)
    validate_evidence.add_argument("--expected-image-digest", required=True)
    validate_evidence.add_argument(
        "--expected-provenance-sha256", required=True
    )
    validate_evidence.add_argument("--expected-sha256")
    validate_evidence.add_argument("--output", type=Path, required=True)
    validate_binding = subparsers.add_parser(
        "validate-image-binding-oci", allow_abbrev=False
    )
    validate_binding.add_argument("--image-binding", type=Path, required=True)
    validate_binding.add_argument("--expected-image-digest", required=True)
    validate_binding.add_argument(
        "--expected-provenance-sha256", required=True
    )
    validate_binding.add_argument(
        "--expected-evidence-sha256", required=True
    )
    validate_binding.add_argument("--output", type=Path, required=True)
    full_binding = subparsers.add_parser(
        "validate-image-binding", allow_abbrev=False
    )
    full_binding.add_argument("--image-binding", type=Path, required=True)
    full_binding.add_argument("--expected-sha256", required=True)
    full_binding.add_argument("--expected-source-commit", required=True)
    full_binding.add_argument("--expected-acr-resource-id", required=True)
    full_binding.add_argument("--expected-login-server", required=True)
    full_binding.add_argument("--expected-repository", required=True)
    full_binding.add_argument("--output", type=Path, required=True)
    live_binding = subparsers.add_parser(
        "validate-live-image-binding", allow_abbrev=False
    )
    live_binding.add_argument("--image-binding", type=Path, required=True)
    live_binding.add_argument("--expected-sha256", required=True)
    live_binding.add_argument("--task-run", type=Path, required=True)
    live_binding.add_argument("--manifest", type=Path, required=True)
    live_binding.add_argument("--config", type=Path, required=True)
    live_binding.add_argument("--resolved-final-digest", required=True)
    live_binding.add_argument("--tag-write-enabled", required=True)
    live_binding.add_argument("--tag-delete-enabled", required=True)
    live_binding.add_argument("--manifest-write-enabled", required=True)
    live_binding.add_argument("--manifest-delete-enabled", required=True)
    live_binding.add_argument("--expected-source-commit", required=True)
    live_binding.add_argument("--expected-acr-resource-id", required=True)
    live_binding.add_argument("--expected-login-server", required=True)
    live_binding.add_argument("--expected-repository", required=True)
    live_binding.add_argument("--output", type=Path, required=True)
    projection = subparsers.add_parser("project-job", allow_abbrev=False)
    projection.add_argument("--live", type=Path, required=True)
    projection.add_argument("--expected", type=Path, required=True)
    projection.add_argument("--output", type=Path, required=True)
    live_projection = subparsers.add_parser(
        "validate-live-job-projection", allow_abbrev=False
    )
    live_projection.add_argument("--live", type=Path, required=True)
    live_projection.add_argument("--expected-job-resource-id", required=True)
    live_projection.add_argument("--expected-job-name", required=True)
    live_projection.add_argument("--expected-sha256", required=True)
    live_projection.add_argument("--output", type=Path, required=True)
    private = subparsers.add_parser("verify-private", allow_abbrev=False)
    private.add_argument("--runtime-config", type=Path, required=True)
    private.add_argument("--storage", type=Path, required=True)
    private.add_argument("--storage-container", type=Path, required=True)
    private.add_argument("--environment", type=Path, required=True)
    private.add_argument(
        "--workload-profile-states", type=Path, required=True
    )
    private.add_argument("--private-endpoint", type=Path, required=True)
    private.add_argument(
        "--storage-private-link-resources", type=Path, required=True
    )
    private.add_argument("--storage-connections", type=Path, required=True)
    private.add_argument("--dns-zone-groups", type=Path, required=True)
    private.add_argument("--dns-links", type=Path, required=True)
    private.add_argument("--dns-record", type=Path, required=True)
    private.add_argument("--nics", type=Path, required=True)
    private.add_argument("--resolved-ips", type=Path, required=True)
    private.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "new-id":
        print(os.urandom(16).hex())
        return 0
    if args.command == "get":
        value = _load_json(args.json, "JSON field source")
        field = args.field.replace("\r", "")
        if not field or any(not component for component in field.split(".")):
            raise AzureContractError("JSON field path is invalid")
        for component in field.split("."):
            if not isinstance(value, Mapping) or component not in value:
                raise AzureContractError(f"JSON field is missing: {field}")
            value = value[component]
        if type(value) not in {str, int}:
            raise AzureContractError(f"JSON field is not scalar: {field}")
        print(value)
        return 0
    if args.command == "arm-list":
        _write_json(args.output, collect_arm_list(args.url))
        return 0
    if args.command == "validate-coordination-zone":
        binding = _load_json(args.binding, "coordination binding")
        zone = _load_json(args.zone, "coordination zone")
        links = _load_json(args.links, "coordination VNet links")
        lock = _load_json(args.lock, "coordination management lock")
        if (
            not isinstance(binding, Mapping)
            or not isinstance(zone, Mapping)
            or not isinstance(links, list)
            or not isinstance(lock, Mapping)
        ):
            raise AzureContractError("coordination validation inputs are invalid")
        evidence = validate_coordination_zone(binding, zone, links, lock)
        _write_json(args.output, evidence)
        print(evidence["coordination_binding_sha256"])
        return 0
    if args.command == "claim-domain":
        binding = _load_json(args.binding, "claim domain binding")
        if not isinstance(binding, Mapping):
            raise AzureContractError("claim domain binding is not an object")
        print(claim_domain_sha256(args.kind, binding))
        return 0
    if args.command == "create-claim-envelope":
        claims = _load_json(args.claims, "claim values")
        if not isinstance(claims, Mapping):
            raise AzureContractError("claim values are not an object")
        _write_json(
            args.output,
            build_claim_envelope(
                args.kind,
                args.domain_sha256.replace("\r", ""),
                claims,
            ),
        )
        return 0
    if args.command == "create-txt-record-body":
        envelope = _load_json(args.envelope, "claim envelope")
        if not isinstance(envelope, Mapping):
            raise AzureContractError("claim envelope is not an object")
        checked = validate_claim_envelope(envelope)
        _write_json(
            args.output,
            build_txt_record_set_body(checked, ttl=args.ttl),
        )
        if args.print_name:
            print(
                dns_txt_record_name(
                    checked["kind"], checked["domain_sha256"]
                )
            )
        return 0
    if args.command == "validate-txt-record":
        record = _load_json(args.record, "TXT RecordSet")
        expected = (
            _load_json(args.expected_envelope, "expected claim envelope")
            if args.expected_envelope is not None
            else None
        )
        if not isinstance(record, Mapping) or (
            expected is not None and not isinstance(expected, Mapping)
        ):
            raise AzureContractError("TXT RecordSet validation inputs are invalid")
        _write_json(
            args.output,
            validate_txt_record_set(
                record,
                zone_resource_id=args.zone_resource_id.replace("\r", ""),
                record_name=args.record_name.replace("\r", ""),
                ttl=args.ttl,
                expected_envelope=expected,
                expected_kind=args.expected_kind,
                expected_domain_sha256=(
                    args.expected_domain_sha256.replace("\r", "")
                    if args.expected_domain_sha256 is not None
                    else None
                ),
            ),
        )
        return 0
    if args.command == "execution-membership":
        records = _load_json(args.executions, "execution records")
        if not isinstance(records, list):
            raise AzureContractError("execution records are not a list")
        _write_json(args.output, execution_membership_from_records(records))
        return 0
    if args.command == "adopt-remove-one":
        baseline = _load_json(args.baseline, "baseline execution membership")
        records = _load_json(args.executions, "current execution records")
        if not isinstance(baseline, list) or not isinstance(records, list):
            raise AzureContractError("remove-one execution inputs are invalid")
        current = execution_membership_from_records(records)["names"]
        name = adopt_remove_one_execution(baseline, current)
        _write_json(
            args.output,
            {
                "action": "adopt",
                "execution_name": name,
                "current_membership": execution_membership(current),
            },
        )
        return 0
    if args.command == "exact-remote-source":
        print(
            exact_remote_git_source(
                args.repository_url.replace("\r", ""),
                args.source_commit.replace("\r", ""),
            )
        )
        return 0
    if args.command == "build-provenance":
        source = _load_json(args.source_binding, "build source binding")
        coordination = _load_json(
            args.coordination_binding, "coordination binding"
        )
        if not isinstance(source, Mapping) or not isinstance(
            coordination, Mapping
        ):
            raise AzureContractError("build source binding is not an object")
        record = build_provenance_record(
            source,
            acr_resource_id=args.acr_resource_id.replace("\r", ""),
            login_server=args.login_server.replace("\r", ""),
            acr_location=args.acr_location.replace("\r", ""),
            coordination_binding=coordination,
        )
        _write_json(args.output, record)
        print(build_provenance_sha256(record))
        return 0
    if args.command == "create-acr-task-run":
        provenance = _load_json(
            args.build_provenance, "build provenance"
        )
        if not isinstance(provenance, Mapping):
            raise AzureContractError("ACR TaskRun provenance is invalid")
        result = build_acr_task_run_body(
            build_provenance=provenance,
            build_provenance_sha256_value=(
                args.build_provenance_sha256.replace("\r", "")
            ),
            staging_tag=args.staging_tag.replace("\r", ""),
        )
        _write_json(args.output, result)
        print(
            hashlib.sha256(
                _canonical_bytes(result["properties"]["runRequest"])
            ).hexdigest()
        )
        return 0
    if args.command == "validate-acr-task-run":
        task_run = _load_json(args.task_run, "ACR TaskRun")
        provenance = _load_json(
            args.build_provenance, "build provenance"
        )
        if not isinstance(task_run, Mapping) or not isinstance(
            provenance, Mapping
        ):
            raise AzureContractError("ACR TaskRun validation inputs are invalid")
        result = validate_acr_task_run(
            task_run,
            expected_task_run_name=args.expected_task_run_name.replace("\r", ""),
            expected_acr_resource_id=args.expected_acr_resource_id.replace(
                "\r", ""
            ),
            build_provenance=provenance,
            build_provenance_sha256_value=(
                args.build_provenance_sha256.replace("\r", "")
            ),
            staging_tag=args.staging_tag.replace("\r", ""),
            require_succeeded=args.require_succeeded,
            expected_digest=(
                args.expected_digest.replace("\r", "")
                if args.expected_digest is not None
                else None
            ),
            expected_run_id=(
                args.expected_run_id.replace("\r", "")
                if args.expected_run_id is not None
                else None
            ),
            expected_run_request_sha256=(
                args.expected_run_request_sha256.replace("\r", "")
                if args.expected_run_request_sha256 is not None
                else None
            ),
        )
        _write_json(args.output, result)
        return 0
    if args.command == "validate-oci-image":
        result = validate_oci_image_artifacts(
            args.manifest.read_bytes(),
            args.config.read_bytes(),
            expected_manifest_digest=(
                args.expected_manifest_digest.replace("\r", "")
            ),
            expected_provenance_sha256=(
                args.expected_provenance_sha256.replace("\r", "")
            ),
        )
        _write_json(args.output, result)
        print(oci_verification_evidence_sha256(result))
        return 0
    if args.command == "validate-oci-evidence":
        evidence = _load_json(args.evidence, "OCI verification evidence")
        if not isinstance(evidence, Mapping):
            raise AzureContractError(
                "OCI verification evidence is not an object"
            )
        checked = validate_oci_verification_evidence(
            evidence,
            expected_image_digest=args.expected_image_digest.replace("\r", ""),
            expected_provenance_sha256=(
                args.expected_provenance_sha256.replace("\r", "")
            ),
            expected_sha256=(
                args.expected_sha256.replace("\r", "")
                if args.expected_sha256 is not None
                else None
            ),
        )
        _write_json(args.output, checked)
        print(oci_verification_evidence_sha256(checked))
        return 0
    if args.command == "validate-image-binding-oci":
        binding = _load_json(args.image_binding, "image binding")
        if not isinstance(binding, Mapping):
            raise AzureContractError("image binding is not an object")
        checked = validate_image_binding_oci_evidence(
            binding,
            expected_image_digest=(
                args.expected_image_digest.replace("\r", "")
            ),
            expected_provenance_sha256=(
                args.expected_provenance_sha256.replace("\r", "")
            ),
            expected_evidence_sha256=(
                args.expected_evidence_sha256.replace("\r", "")
            ),
        )
        _write_json(args.output, checked)
        return 0
    if args.command == "validate-image-binding":
        checked = validate_image_binding_record(
            args.image_binding.read_bytes(),
            expected_sha256=args.expected_sha256.replace("\r", ""),
            expected_source_commit=args.expected_source_commit.replace("\r", ""),
            expected_acr_resource_id=args.expected_acr_resource_id.replace(
                "\r", ""
            ),
            expected_login_server=args.expected_login_server.replace("\r", ""),
            expected_repository=args.expected_repository.replace("\r", ""),
        )
        _write_json(args.output, checked)
        print(args.expected_sha256.replace("\r", ""))
        return 0
    if args.command == "validate-live-image-binding":
        task_run = _load_json(args.task_run, "live ACR TaskRun")
        if not isinstance(task_run, Mapping):
            raise AzureContractError("live ACR TaskRun is not an object")
        checked = validate_live_image_binding(
            args.image_binding.read_bytes(),
            expected_sha256=args.expected_sha256.replace("\r", ""),
            live_task_run=task_run,
            manifest_bytes=args.manifest.read_bytes(),
            config_bytes=args.config.read_bytes(),
            resolved_final_digest=args.resolved_final_digest.replace("\r", ""),
            tag_write_enabled=args.tag_write_enabled,
            tag_delete_enabled=args.tag_delete_enabled,
            manifest_write_enabled=args.manifest_write_enabled,
            manifest_delete_enabled=args.manifest_delete_enabled,
            expected_source_commit=args.expected_source_commit.replace("\r", ""),
            expected_acr_resource_id=args.expected_acr_resource_id.replace(
                "\r", ""
            ),
            expected_login_server=args.expected_login_server.replace("\r", ""),
            expected_repository=args.expected_repository.replace("\r", ""),
        )
        _write_json(args.output, checked)
        print(checked["image_binding_sha256"])
        return 0
    if args.command == "project-job":
        live = _load_json(args.live, "live job")
        expected = _load_json(args.expected, "expected job")
        projection, digest = compare_job_with_body(live, expected)
        _write_json(args.output, projection)
        print(digest)
        return 0
    if args.command == "validate-live-job-projection":
        live = _load_json(args.live, "live job")
        if not isinstance(live, Mapping):
            raise AzureContractError("live job is not an object")
        projection, digest = validate_live_job_projection_hash(
            live,
            expected_job_resource_id=args.expected_job_resource_id.replace(
                "\r", ""
            ),
            expected_job_name=args.expected_job_name.replace("\r", ""),
            expected_sha256=args.expected_sha256.replace("\r", ""),
        )
        _write_json(args.output, projection)
        print(digest)
        return 0
    if args.command == "verify-private":
        runtime = _load_json(args.runtime_config, "runtime config")
        if not isinstance(runtime, Mapping):
            raise AzureContractError("runtime config is not an object")
        sequence_paths = (
            (
                "storage_private_link_resources",
                args.storage_private_link_resources,
            ),
            ("storage_connections", args.storage_connections),
            ("dns_zone_groups", args.dns_zone_groups),
            ("dns_links", args.dns_links),
            ("nics", args.nics),
            ("resolved_ips", args.resolved_ips),
            ("workload_profile_states", args.workload_profile_states),
        )
        sequences: dict[str, list[Any]] = {}
        for name, path in sequence_paths:
            value = _load_json(path, name)
            if not isinstance(value, list):
                raise AzureContractError(f"{name} is not an array")
            sequences[name] = value
        result = validate_private_endpoint_topology(
            runtime["azure_destination"],
            storage=_load_json(args.storage, "storage account"),
            storage_container=_load_json(
                args.storage_container, "storage Blob container"
            ),
            environment=_load_json(args.environment, "Container Apps environment"),
            workload_profile_states=sequences["workload_profile_states"],
            private_endpoint=_load_json(
                args.private_endpoint, "private endpoint"
            ),
            storage_private_link_resources=sequences[
                "storage_private_link_resources"
            ],
            storage_connections=sequences["storage_connections"],
            dns_zone_groups=sequences["dns_zone_groups"],
            dns_links=sequences["dns_links"],
            dns_record=_load_json(args.dns_record, "private DNS A record"),
            nics=sequences["nics"],
            resolved_ips=sequences["resolved_ips"],
        )
        _write_json(args.output, result)
        return 0
    raise AzureContractError("unknown helper command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AzureContractError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
