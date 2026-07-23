#!/usr/bin/env python3
"""Custodian-only, manifest-only bootstrap for one locked evaluation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import hashlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping


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
PARSER_SOURCE_PATH = "src/jspace_observation/eval_parsing_v2.py"
BOOTSTRAP_VISIBILITY = [
    "custodian-only-bootstrap",
    "manifest-only:no-locked-payload-or-label-read",
]


def _load_core() -> ModuleType:
    name = "_jspace_parser_v2_locked_eval_bootstrap"
    spec = importlib.util.spec_from_file_location(name, CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot direct-load locked-evaluation core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _timestamps(start: str, count: int) -> list[str]:
    try:
        parsed = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        raise RuntimeError("bootstrap clock did not return canonical UTC") from None
    return [
        (parsed + timedelta(seconds=index)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for index in range(count)
    ]


def _git_source_bindings(
    implementation_commit: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, dict[str, str]]:
    commit = implementation_commit
    checked = subprocess.run(
        ["git", "--no-replace-objects", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    if checked.returncode != 0:
        raise RuntimeError("implementation commit is not present in the repository")
    core = _load_core()
    parser_oid = subprocess.run(
        ["git", "--no-replace-objects", "rev-parse", f"{commit}:{PARSER_SOURCE_PATH}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    try:
        parser_blob_oid = parser_oid.stdout.decode("ascii").replace("\r", "").strip()
    except UnicodeDecodeError:
        parser_blob_oid = ""
    if (
        parser_oid.returncode != 0
        or parser_blob_oid != core.FROZEN_PARSER_GIT_BLOB_OID
    ):
        raise RuntimeError(
            "implementation commit does not contain the frozen parser source"
        )
    bindings: dict[str, dict[str, str]] = {}
    for relative_path in core.RUNTIME_SOURCE_BINDING_PATHS:
        oid = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "rev-parse",
                f"{commit}:{relative_path}",
            ],
            cwd=project_root,
            capture_output=True,
            check=False,
        )
        if oid.returncode != 0:
            raise RuntimeError(
                "implementation commit omits a registered runtime source"
            )
        try:
            blob_oid = oid.stdout.decode("ascii").replace("\r", "").strip()
        except UnicodeDecodeError:
            raise RuntimeError("Git returned a non-ASCII blob ID") from None
        if "\n" in blob_oid:
            raise RuntimeError("Git returned a non-scalar blob ID")
        content = subprocess.run(
            ["git", "--no-replace-objects", "cat-file", "blob", blob_oid],
            cwd=project_root,
            capture_output=True,
            check=False,
        )
        if content.returncode != 0:
            raise RuntimeError("cannot read a registered runtime Git blob")
        bindings[relative_path] = {
            "git_blob_oid": blob_oid,
            "sha256": hashlib.sha256(content.stdout).hexdigest(),
        }
    return bindings


def _persist_or_authenticate(
    core: ModuleType,
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
) -> dict[str, Any]:
    parent = blob_name.rsplit("/", 1)[0]
    if blob_name in core.list_exact_prefix(service, container, parent):
        return _authenticate_existing(core, service, container, blob_name, data)
    try:
        result = core.persist_singleton(
            service, container, blob_name, data
        )
    except core.LockedEvaluationError as upload_error:
        try:
            persisted, etag = core.download_stable_blob(
                service, container, blob_name
            )
        except core.LockedEvaluationError:
            raise upload_error
        if persisted != data:
            raise core.LockedEvaluationError(
                f"existing bootstrap singleton differs: {blob_name}"
            ) from upload_error
        return {
            "blob_name": blob_name,
            "sha256": core.sha256_bytes(data),
            "etag": etag,
            "size": len(data),
            "overwrite": False,
            "adopted": True,
        }
    result["adopted"] = False
    return result


def _authenticate_existing(
    core: ModuleType,
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
) -> dict[str, Any]:
    persisted, etag = core.download_stable_blob(
        service, container, blob_name
    )
    if persisted != data:
        raise core.LockedEvaluationError(
            f"existing bootstrap singleton differs: {blob_name}"
        )
    return {
        "blob_name": blob_name,
        "sha256": core.sha256_bytes(data),
        "etag": etag,
        "size": len(data),
        "overwrite": False,
        "adopted": True,
    }


def _recover_lock_identity(
    core: ModuleType, lock: Mapping[str, Any]
) -> tuple[str, str, str]:
    execution_id = lock["execution_id"]
    base_execution_id, separator, suffix = execution_id.rpartition("-")
    if separator != "-" or suffix != "06" or not base_execution_id:
        raise core.LockedEvaluationError(
            "existing authorization lock execution identity is not recoverable"
        )
    try:
        implementation_time = datetime.strptime(
            lock["created_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        raise core.LockedEvaluationError(
            "existing authorization lock timestamp is not recoverable"
        ) from None
    timestamp_start = (
        implementation_time - timedelta(seconds=6)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return base_execution_id, lock["actor"], timestamp_start


def _manifest_metadata(
    record: Mapping[str, Any], path: str
) -> Mapping[str, Any]:
    matches = [
        item
        for item in record["files"]
        if isinstance(item, Mapping) and item.get("path") == path
    ]
    if len(matches) != 1:
        raise RuntimeError(f"sealed manifest omits exact metadata for {path}")
    return matches[0]


def _load_manifest_only_bindings(
    core: ModuleType,
    service: Any,
    container: str,
    parent_prefix: str,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = core._load_frozen_validation()
    manifest_paths = {
        "development": "development/development_manifest.json",
        "locked-inputs": "locked-inputs/locked_inputs_manifest.json",
        "locked-labels": "locked-labels/locked_labels_manifest.json",
        "reports": "reports/reports_manifest.json",
        "manifests": "manifests/locked_manifest.json",
    }
    records: dict[str, Mapping[str, Any]] = {}
    raw: dict[str, bytes] = {}
    etags: dict[str, str] = {}
    for kind, relative in manifest_paths.items():
        data, etag = core.download_stable_blob(
            service, container, f"{parent_prefix}/{relative}"
        )
        record = core.parse_json_strict(data, relative)
        if core.canonical_json_bytes(record) != data:
            raise core.LockedEvaluationError(
                f"{relative} is not canonical immutable JSON"
            )
        try:
            frozen.validate_manifest(record)
        except Exception:
            raise core.LockedEvaluationError(
                f"{relative} is not a registered frozen manifest"
            ) from None
        core._validated_manifest_files(record, name=relative)
        if (
            record["manifest_kind"] != kind
            or record["parent_prefix"] != parent_prefix
        ):
            raise core.LockedEvaluationError(
                f"{relative} has a disconnected parent/kind binding"
            )
        records[kind] = record
        raw[kind] = data
        etags[kind] = etag

    sealed = records["manifests"]
    for kind in ("development", "locked-inputs", "locked-labels", "reports"):
        relative = manifest_paths[kind]
        metadata = _manifest_metadata(sealed, relative)
        if (
            not core.exact_json_equal(metadata.get("size"), len(raw[kind]))
            or metadata.get("sha256") != core.sha256_bytes(raw[kind])
        ):
            raise core.LockedEvaluationError(
                "sealed manifest does not authenticate every leaf manifest"
            )

    input_payload_path = "locked-inputs/locked_inputs.jsonl"
    input_payload = _manifest_metadata(
        records["locked-inputs"], input_payload_path
    )
    core.validate_locked_source_manifest(
        raw["locked-inputs"],
        expected_manifest_sha256=core.sha256_bytes(raw["locked-inputs"]),
        expected_payload_sha256=input_payload["sha256"],
        parent_prefix=parent_prefix,
        manifest_kind="locked-inputs",
        payload_relative_path=input_payload_path,
        gates=gates,
    )
    if (
        not core.exact_json_equal(
            records["locked-labels"]["ordered_case_ids"],
            records["locked-inputs"]["ordered_case_ids"],
        )
        or len(records["locked-labels"]["ordered_case_ids"])
        != gates["dataset_contract"]["total_cases"]
    ):
        raise core.LockedEvaluationError(
            "locked-label manifest universe differs from locked inputs"
        )
    _manifest_metadata(
        records["locked-labels"],
        "locked-labels/locked_reference_labels.jsonl",
    )
    for kind, manifest_path in (
        ("locked-inputs", "locked-inputs/locked_inputs_manifest.json"),
        ("locked-labels", "locked-labels/locked_labels_manifest.json"),
    ):
        sealed_leaf = _manifest_metadata(sealed, manifest_path)
        if sealed_leaf["sha256"] != core.sha256_bytes(raw[kind]):
            raise core.LockedEvaluationError(
                "sealed source-manifest binding is disconnected"
            )

    reservation_relative = "locked-inputs/.locked_inputs_reservation.json"
    reservation_blob = f"{parent_prefix}/{reservation_relative}"
    reservation_bytes, reservation_etag = core.download_stable_blob(
        service, container, reservation_blob
    )
    locked_input_source = core.validate_locked_input_source_binding(
        reservation_bytes=reservation_bytes,
        reservation_blob=reservation_blob,
        reservation_etag=reservation_etag,
        manifest_bytes=raw["locked-inputs"],
        manifest_blob=f"{parent_prefix}/{manifest_paths['locked-inputs']}",
        manifest_etag=etags["locked-inputs"],
        locked_manifest_bytes=raw["manifests"],
        expected_locked_manifest_sha256=core.sha256_bytes(raw["manifests"]),
        expected_manifest_sha256=core.sha256_bytes(raw["locked-inputs"]),
        expected_payload_sha256=input_payload["sha256"],
        parent_prefix=parent_prefix,
        gates=gates,
    )

    historical = {
        "protocol_manifest": core.FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates": core.FROZEN_ACCEPTANCE_GATE_SHA256,
        "selection_plan": _manifest_metadata(
            sealed, "manifests/locked_case_mapping.json"
        )["sha256"],
        "overlap_report": _manifest_metadata(
            sealed, "manifests/overlap_report.json"
        )["sha256"],
        "construction_manifest": core.sha256_bytes(raw["reports"]),
        "reservations_manifest": _manifest_metadata(
            sealed, "manifests/.locked_manifest_reservation.json"
        )["sha256"],
        "development_manifest": core.sha256_bytes(raw["development"]),
        "locked_inputs_manifest": core.sha256_bytes(raw["locked-inputs"]),
        "locked_labels_manifest": core.sha256_bytes(raw["locked-labels"]),
        "reports_manifest": core.sha256_bytes(raw["reports"]),
        "locked_manifest": core.sha256_bytes(raw["manifests"]),
    }
    return {
        "hashes": historical,
        "records": records,
        "bytes": raw,
        "locked_input_source": locked_input_source,
    }


def _receipt(
    core: ModuleType,
    *,
    previous: Mapping[str, Any] | None,
    state: str,
    authorization_id: str,
    parent_prefix: str,
    additions: Mapping[str, str],
    timestamp_utc: str,
    execution_id: str,
    actor: str,
    implementation_commit: str | None = None,
    image_digest: str | None = None,
    config_sha256: str | None = None,
    authorization_lock_sha256: str | None = None,
) -> dict[str, Any]:
    manifests = (
        {} if previous is None else dict(previous["artifact_manifest_hashes"])
    )
    manifests.update(additions)
    index = core.HOLDOUT_STATE_SEQUENCE.index(state)
    record = {
        "schema_version": core.STATE_RECEIPT_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "state": state,
        "previous_state": None if previous is None else previous["state"],
        "previous_receipt_sha256": (
            None if previous is None else core.state_receipt_sha256(previous)
        ),
        "timestamp_utc": timestamp_utc,
        "execution_id": execution_id,
        "actor": actor,
        "visibility": BOOTSTRAP_VISIBILITY,
        "registered_parent_prefix": parent_prefix,
        "protocol_commit": core.FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": core.FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": core.FROZEN_ACCEPTANCE_GATE_SHA256,
        "implementation_commit": implementation_commit,
        "image_digest": image_digest,
        "config_sha256": config_sha256,
        "authorization_lock_sha256": authorization_lock_sha256,
        "artifact_manifest_hashes": manifests,
        "retry_kind": "none",
        "outcome": None,
        "holdout_spent": index
        >= core.HOLDOUT_STATE_SEQUENCE.index("INPUTS_READ"),
        "holdout_retired": False,
    }
    core.validate_state_receipt(record)
    return record


def run_bootstrap(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
    now: Callable[[], str] = _utc_now,
    custodian_authorized: bool = False,
    runtime_config_bytes: bytes | None = None,
    implementation_manifest_bytes: bytes | None = None,
    image_binding_bytes: bytes | None = None,
) -> dict[str, Any]:
    active_core = core or _load_core()
    if type(custodian_authorized) is not bool or not custodian_authorized:
        raise active_core.LockedEvaluationError(
            "bootstrap is restricted to the custodian execution role"
        )
    active_core.validate_no_model_gpu_configuration(os.environ)
    active_core.compute_protocol_bundle_sha256(PROJECT_ROOT)
    gate_bytes = active_core.load_frozen_gate_bytes(PROJECT_ROOT)
    gates = active_core.load_acceptance_gates(gate_bytes)
    if (
        runtime_config_bytes is None
        or implementation_manifest_bytes is None
        or image_binding_bytes is None
    ):
        raise active_core.LockedEvaluationError(
            "bootstrap requires complete runtime/implementation/image-binding bytes"
        )
    runtime_bytes = bytes(runtime_config_bytes)
    implementation_bytes = bytes(implementation_manifest_bytes)
    binding_bytes = bytes(image_binding_bytes)
    runtime_sha256 = active_core.sha256_bytes(runtime_bytes)
    implementation_sha256 = active_core.sha256_bytes(implementation_bytes)
    image_binding_sha256 = getattr(args, "image_binding_sha256", None)
    if (
        runtime_sha256 != args.runtime_config_sha256
        or implementation_sha256 != args.implementation_manifest_sha256
        or active_core.sha256_bytes(binding_bytes)
        != image_binding_sha256
    ):
        raise active_core.LockedEvaluationError(
            "bootstrap runtime/implementation/image-binding hash mismatch"
        )
    implementation = active_core.validate_implementation_manifest(
        implementation_bytes
    )
    parent = active_core.validate_registered_parent_prefix(args.parent_prefix)
    authorization_id = active_core.validate_authorization_id(
        args.authorization_id
    )
    state_prefix = active_core.evaluation_prefixes(
        parent, authorization_id
    )["state"]
    if args.state_prefix != state_prefix:
        raise active_core.LockedEvaluationError(
            "bootstrap state prefix is not authorization-specific"
        )
    source_bindings = _git_source_bindings(args.implementation_commit)
    launcher = source_bindings[
        "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    ]
    runtime = active_core.validate_runtime_configuration(
        runtime_bytes,
        expected_sha256=runtime_sha256,
        source_commit=args.implementation_commit,
        parent_prefix=parent,
        authorization_id=authorization_id,
        launcher_sha256=launcher["sha256"],
        launcher_git_blob_oid=launcher["git_blob_oid"],
        expected_image_digest=args.image_digest,
        image_binding_bytes=binding_bytes,
        expected_image_binding_sha256=image_binding_sha256,
    )
    helper_snapshot_set_sha256 = getattr(
        args, "helper_snapshot_set_sha256", None
    )
    destination = runtime["azure_destination"]
    if (
        not active_core.exact_json_equal(
            runtime["source_bindings"], source_bindings
        )
        or implementation["implementation_commit"] != args.implementation_commit
        or implementation["image_digest"] != args.image_digest
        or implementation["config_sha256"] != runtime_sha256
        or destination["storage"]["blob_endpoint"] != args.account_url
        or destination["storage"]["container"] != args.container
        or destination["image"]["digest"] != args.image_digest
        or runtime["image_binding_sha256"] != image_binding_sha256
        or runtime["helper_snapshot_set_sha256"]
        != helper_snapshot_set_sha256
    ):
        raise active_core.LockedEvaluationError(
            "bootstrap persisted implementation/runtime destination mismatch"
        )
    if service is None:
        active_core.validate_private_endpoint_resolution(
            args.account_url,
            destination["network"]["private_endpoint_nic_private_ips"],
        )
    active_service = service or active_core.create_blob_service(args.account_url)
    frozen_parent = set(
        active_core._load_frozen_validation().expected_parent_membership(parent)
    )
    evaluation = active_core.evaluation_prefixes(parent, authorization_id)
    existing_state_members = active_core.list_exact_prefix(
        active_service, args.container, state_prefix
    )
    allowed_state_members = active_core._authorization_state_members(
        state_prefix, final_state="UNSEAL_AUTHORIZED"
    )
    if not existing_state_members.issubset(allowed_state_members):
        raise active_core.LockedEvaluationError(
            "bootstrap state destination contains an unexpected object"
        )
    for leaf in ("predictions", "scores", "visibility"):
        if active_core.list_exact_prefix(
            active_service, args.container, evaluation[leaf]
        ):
            raise active_core.LockedEvaluationError(
                f"bootstrap destination is not empty: {leaf}"
            )

    manifest_bindings = _load_manifest_only_bindings(
        active_core,
        active_service,
        args.container,
        parent,
        gates,
    )
    hashes = manifest_bindings["hashes"]
    holdout_id = active_core.derive_holdout_id(
        parent, hashes["locked_manifest"]
    )
    expected_lock_blob = (
        f"{active_core.AUTHORIZATION_LOCK_BLOB_PREFIX}/{holdout_id}.json"
    )
    lock_members = active_core.list_exact_prefix(
        active_service,
        args.container,
        active_core.AUTHORIZATION_LOCK_BLOB_PREFIX,
    )
    existing_authorization_lock: dict[str, Any] | None = None
    existing_authorization_lock_bytes: bytes | None = None
    if expected_lock_blob in lock_members:
        existing_authorization_lock_bytes, _ = (
            active_core.download_stable_blob(
                active_service, args.container, expected_lock_blob
            )
        )
        lock_record = active_core.parse_json_strict(
            existing_authorization_lock_bytes, "authorization lock"
        )
        if (
            active_core.canonical_json_bytes(lock_record)
            != existing_authorization_lock_bytes
        ):
            raise active_core.LockedEvaluationError(
                "existing authorization lock is not canonical immutable JSON"
            )
        active_core.validate_authorization_lock(lock_record)
        existing_authorization_lock = dict(lock_record)
        expected_lock_bindings = {
            "holdout_id": holdout_id,
            "registered_parent_prefix": parent,
            "locked_manifest_sha256": hashes["locked_manifest"],
            "authorization_id": authorization_id,
            "implementation_commit": args.implementation_commit,
            "image_digest": args.image_digest,
            "config_sha256": runtime_sha256,
            "implementation_manifest_sha256": implementation_sha256,
            "visibility_sha256": active_core.sha256_bytes(
                active_core.canonical_json_bytes(BOOTSTRAP_VISIBILITY)
            ),
        }
        if any(
            not active_core.exact_json_equal(
                existing_authorization_lock[key], expected
            )
            for key, expected in expected_lock_bindings.items()
        ):
            raise active_core.LockedEvaluationError(
                "existing authorization lock immutable binding mismatch"
            )
        if (
            active_core.authorization_lock_blob_name(
                existing_authorization_lock
            )
            != expected_lock_blob
        ):
            raise active_core.LockedEvaluationError(
                "existing authorization lock path binding mismatch"
            )

    draft_blob = (
        f"{state_prefix}/"
        f"{active_core.STATE_RECEIPT_FILENAMES['DRAFT_PROTOCOL']}"
    )
    if existing_authorization_lock is not None:
        bootstrap_execution_id, bootstrap_actor, timestamp_start = (
            _recover_lock_identity(active_core, existing_authorization_lock)
        )
    elif draft_blob in existing_state_members:
        draft_bytes, _ = active_core.download_stable_blob(
            active_service, args.container, draft_blob
        )
        draft = active_core.parse_json_strict(
            draft_bytes, "DRAFT_PROTOCOL receipt"
        )
        active_core.validate_state_receipt(draft)
        if (
            draft["state"] != "DRAFT_PROTOCOL"
            or draft["authorization_id"] != authorization_id
            or draft["registered_parent_prefix"] != parent
            or draft["execution_id"] != f"{args.execution_id}-00"
            or draft["actor"] != args.actor
        ):
            raise active_core.LockedEvaluationError(
                "existing bootstrap chain belongs to another execution"
            )
        bootstrap_execution_id = args.execution_id
        bootstrap_actor = args.actor
        timestamp_start = draft["timestamp_utc"]
    else:
        bootstrap_execution_id = args.execution_id
        bootstrap_actor = args.actor
        timestamp_start = now()
    timestamps = _timestamps(timestamp_start, 8)
    state_additions = {
        "DRAFT_PROTOCOL": {},
        "PROTOCOL_FROZEN": {
            "protocol_manifest": hashes["protocol_manifest"],
            "acceptance_gates": hashes["acceptance_gates"],
        },
        "PRIVATE_CONSTRUCTION": {
            "selection_plan": hashes["selection_plan"],
            "overlap_report": hashes["overlap_report"],
            "construction_manifest": hashes["construction_manifest"],
        },
        "RESERVED": {
            "reservations_manifest": hashes["reservations_manifest"]
        },
        "PAYLOAD_COMPLETE": {
            "development_manifest": hashes["development_manifest"],
            "locked_inputs_manifest": hashes["locked_inputs_manifest"],
            "locked_labels_manifest": hashes["locked_labels_manifest"],
            "reports_manifest": hashes["reports_manifest"],
        },
        "SEALED": {"locked_manifest": hashes["locked_manifest"]},
    }
    receipts: list[dict[str, Any]] = []
    previous = None
    for index, state in enumerate(active_core.CONSTRUCTION_STATE_SEQUENCE):
        receipt = _receipt(
            active_core,
            previous=previous,
            state=state,
            authorization_id=authorization_id,
            parent_prefix=parent,
            additions=state_additions[state],
            timestamp_utc=timestamps[index],
            execution_id=f"{bootstrap_execution_id}-{index:02d}",
            actor=bootstrap_actor,
        )
        if previous is not None:
            active_core.validate_state_transition(previous, receipt)
        receipts.append(receipt)
        previous = receipt

    provisional_implementation = _receipt(
        active_core,
        previous=receipts[-1],
        state="IMPLEMENTATION_FROZEN",
        authorization_id=authorization_id,
        parent_prefix=parent,
        additions={"implementation_manifest": implementation_sha256},
        timestamp_utc=timestamps[6],
        execution_id=f"{bootstrap_execution_id}-06",
        actor=bootstrap_actor,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=runtime_sha256,
        authorization_lock_sha256="1" * 64,
    )
    frozen = active_core._load_frozen_validation()
    authorization_lock = frozen.build_authorization_lock(
        receipts[-1],
        provisional_implementation,
        implementation_bytes,
    )
    if existing_authorization_lock is not None:
        if (
            active_core.state_receipt_sha256(receipts[-1])
            != existing_authorization_lock["sealed_receipt_sha256"]
            or not active_core.exact_json_equal(
                authorization_lock, existing_authorization_lock
            )
        ):
            raise active_core.LockedEvaluationError(
                "reconstructed SEALED/IMPLEMENTATION chain differs from "
                "the existing authorization lock"
            )
        authorization_lock = existing_authorization_lock
    lock_sha256 = active_core.authorization_lock_sha256(authorization_lock)
    implementation_receipt = _receipt(
        active_core,
        previous=receipts[-1],
        state="IMPLEMENTATION_FROZEN",
        authorization_id=authorization_id,
        parent_prefix=parent,
        additions={"implementation_manifest": implementation_sha256},
        timestamp_utc=timestamps[6],
        execution_id=f"{bootstrap_execution_id}-06",
        actor=bootstrap_actor,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=runtime_sha256,
        authorization_lock_sha256=lock_sha256,
    )
    active_core.validate_state_transition(
        receipts[-1],
        implementation_receipt,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_bytes,
    )
    if not active_core.exact_json_equal(
        authorization_lock,
        frozen.build_authorization_lock(
            receipts[-1], implementation_receipt, implementation_bytes
        ),
    ):
        raise active_core.LockedEvaluationError(
            "authorization lock is not deterministic"
        )
    receipts.append(implementation_receipt)

    authorization_manifest = active_core.build_authorization_manifest(
        implementation_receipt,
        authorization_lock,
        implementation_bytes,
        runtime_bytes,
        locked_input_source_binding=manifest_bindings[
            "locked_input_source"
        ]["binding"],
        state_prefix=state_prefix,
        actor=bootstrap_actor,
        created_utc=timestamps[7],
    )
    authorization_manifest_bytes = active_core.canonical_json_bytes(
        authorization_manifest
    )
    unseal_receipt = active_core.build_next_state_receipt(
        implementation_receipt,
        state="UNSEAL_AUTHORIZED",
        artifact_manifest_sha256=active_core.sha256_bytes(
            authorization_manifest_bytes
        ),
        timestamp_utc=timestamps[7],
        execution_id=f"{bootstrap_execution_id}-07",
        actor=bootstrap_actor,
        visibility=BOOTSTRAP_VISIBILITY,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_bytes,
    )
    receipts.append(unseal_receipt)
    active_core.validate_state_receipt_chain(
        receipts,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_bytes,
    )

    authorization_lock_bytes = active_core.canonical_json_bytes(
        authorization_lock
    )
    authorization_lock_blob = active_core.authorization_lock_blob_name(
        authorization_lock
    )
    if authorization_lock_blob != expected_lock_blob:
        raise active_core.LockedEvaluationError(
            "reconstructed authorization lock path differs from frozen metadata"
        )
    if (
        existing_authorization_lock_bytes is not None
        and authorization_lock_bytes != existing_authorization_lock_bytes
    ):
        raise active_core.LockedEvaluationError(
            "reconstructed authorization lock bytes differ from persisted lock"
        )

    prefix_payloads = [
        (
            active_core.state_receipt_blob_name(state_prefix, receipt),
            active_core.canonical_json_bytes(receipt),
        )
        for receipt in receipts[:6]
    ]
    prefix_payloads.extend(
        [
            (
                f"{state_prefix}/{active_core.IMPLEMENTATION_MANIFEST_FILENAME}",
                implementation_bytes,
            ),
            (
                f"{state_prefix}/{active_core.RUNTIME_CONFIG_FILENAME}",
                runtime_bytes,
            ),
            (
                active_core.state_receipt_blob_name(
                    state_prefix, implementation_receipt
                ),
                active_core.canonical_json_bytes(implementation_receipt),
            ),
            (
                f"{state_prefix}/{active_core.AUTHORIZATION_MANIFEST_FILENAME}",
                authorization_manifest_bytes,
            ),
            (
                active_core.state_receipt_blob_name(
                    state_prefix, unseal_receipt
                ),
                active_core.canonical_json_bytes(unseal_receipt),
            ),
        ]
    )
    payload_by_blob = dict(prefix_payloads)
    authenticated_existing = {
        blob_name: _authenticate_existing(
            active_core,
            active_service,
            args.container,
            blob_name,
            payload_by_blob[blob_name],
        )
        for blob_name in sorted(existing_state_members)
    }

    persisted: list[dict[str, Any]] = [
        _persist_or_authenticate(
            active_core,
            active_service,
            args.container,
            authorization_lock_blob,
            authorization_lock_bytes,
        )
    ]
    active_core.validate_registered_parent_membership(
        active_service,
        args.container,
        parent,
        frozen_parent | existing_state_members,
    )
    for blob_name, data in prefix_payloads:
        persisted.append(
            authenticated_existing.get(blob_name)
            or _persist_or_authenticate(
                active_core, active_service, args.container, blob_name, data
            )
        )
    state_members = active_core._authorization_state_members(
        state_prefix, final_state="UNSEAL_AUTHORIZED"
    )
    active_core.validate_authorization_membership(
        active_service,
        args.container,
        parent_prefix=parent,
        authorization_id=authorization_id,
        expected={
            "predictions": set(),
            "scores": set(),
            "state": state_members,
            "visibility": set(),
        },
    )
    active_core.validate_registered_parent_membership(
        active_service,
        args.container,
        parent,
        active_core.expected_registered_parent_membership(
            parent, state_members
        ),
    )
    authenticated = active_core.authenticate_authorization_bundle(
        active_service,
        args.container,
        project_root=PROJECT_ROOT,
        parent_prefix=parent,
        authorization_id=authorization_id,
        state_prefix=state_prefix,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=runtime_sha256,
        launcher_sha256=launcher["sha256"],
        launcher_git_blob_oid=launcher["git_blob_oid"],
        expected_azure_destination=destination,
        expected_image_binding_sha256=image_binding_sha256,
        expected_helper_snapshot_set_sha256=helper_snapshot_set_sha256,
        expected_prior_receipt_sha256=active_core.state_receipt_sha256(
            unseal_receipt
        ),
        expected_authorization_lock_sha256=lock_sha256,
        expected_authorization_manifest_sha256=active_core.sha256_bytes(
            authorization_manifest_bytes
        ),
        final_state="UNSEAL_AUTHORIZED",
    )
    return {
        "status": "UNSEAL_AUTHORIZED",
        "authorization_id": authorization_id,
        "state_prefix": state_prefix,
        "authorization_lock_blob": authenticated["authorization_lock_blob"],
        "authorization_lock_sha256": lock_sha256,
        "authorization_manifest_sha256": active_core.sha256_bytes(
            authorization_manifest_bytes
        ),
        "implementation_manifest_sha256": implementation_sha256,
        "runtime_config_sha256": runtime_sha256,
        "image_binding_sha256": image_binding_sha256,
        "helper_snapshot_set_sha256": helper_snapshot_set_sha256,
        "unseal_receipt_sha256": active_core.state_receipt_sha256(
            unseal_receipt
        ),
        "persisted_singleton_count": len(persisted),
        "locked_input_payload_read": False,
        "locked_labels_payload_read": False,
        "overwrite": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Custodian-only locked-evaluation bootstrap",
        allow_abbrev=False,
    )
    parser.add_argument("--runtime-config-file", type=Path, required=True)
    parser.add_argument("--runtime-config-sha256", required=True)
    parser.add_argument("--implementation-manifest-file", type=Path, required=True)
    parser.add_argument("--implementation-manifest-sha256", required=True)
    parser.add_argument("--image-binding-file", type=Path, required=True)
    parser.add_argument("--image-binding-sha256", required=True)
    parser.add_argument("--helper-snapshot-set-sha256", required=True)
    parser.add_argument("--execution-id")
    parser.add_argument(
        "--actor", choices=("phase1-parser-v2-custodian",)
    )
    parser.add_argument(
        "--authenticate-only-state",
        choices=(
            "LATEST",
            "UNSEAL_AUTHORIZED",
            "INPUTS_READ",
            "PREDICTIONS_VERIFIED",
            "LABELS_READ",
            "SCORES_VERIFIED",
            "CLOSED",
        ),
    )
    parser.add_argument("--prior-state-receipt-sha256")
    parser.add_argument("--authorization-lock-sha256")
    parser.add_argument("--authorization-manifest-sha256")
    return parser


def _download_canonical_record(
    core: ModuleType,
    service: Any,
    container: str,
    blob_name: str,
    record_name: str,
) -> tuple[dict[str, Any], bytes, str]:
    data, etag = core.download_stable_blob(service, container, blob_name)
    record = core.parse_json_strict(data, record_name)
    if not isinstance(record, Mapping) or core.canonical_json_bytes(record) != data:
        raise core.LockedEvaluationError(
            f"{record_name} singleton bytes are not canonical"
        )
    return dict(record), data, etag


def _member_metadata(
    core: ModuleType, blob_name: str, data: bytes, etag: str
) -> dict[str, Any]:
    return {
        "blob_name": blob_name,
        "size": len(data),
        "sha256": core.sha256_bytes(data),
        "etag": etag,
    }


def _receipt_for_state(
    core: ModuleType,
    receipts: list[Mapping[str, Any]],
    state: str,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in receipts
        if item["state"] == state and item["retry_kind"] == "none"
    ]
    if len(matches) != 1:
        raise core.LockedEvaluationError(
            f"authenticated receipt chain does not identify {state}"
        )
    return matches[0]


def _receipt_by_sha256(
    core: ModuleType,
    receipts: list[Mapping[str, Any]],
    receipt_sha256: str,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in receipts
        if core.state_receipt_sha256(item) == receipt_sha256
    ]
    if len(matches) != 1:
        raise core.LockedEvaluationError(
            "authenticated retry predecessor is not unique"
        )
    return matches[0]


def _authenticate_abandoned_attempt(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_receipt: Mapping[str, Any],
    receipts: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blob_name = core.derive_abandoned_attempt_blob_name(
        parent_prefix,
        authorization_id,
        stage,
        retry_receipt["retry_kind"],
        retry_receipt["execution_id"],
    )
    record, data, etag = _download_canonical_record(
        core,
        service,
        container,
        blob_name,
        "abandoned attempt record",
    )
    checked = core.validate_abandoned_attempt_record(record)
    previous = _receipt_by_sha256(
        core, receipts, retry_receipt["previous_receipt_sha256"]
    )
    core.validate_retry_state_receipt_provenance(
        retry_receipt,
        previous=previous,
        abandoned_attempt_record=checked,
        abandoned_attempt_blob_name=blob_name,
        abandoned_attempt_record_sha256=core.sha256_bytes(data),
    )
    return checked, _member_metadata(core, blob_name, data, etag)


def _authenticate_prediction_attempt(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    authorization_id: str,
    receipts: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], set[str], set[str]]:
    prediction_receipt = _receipt_for_state(
        core, receipts, "PREDICTIONS_VERIFIED"
    )
    retries = [
        item
        for item in receipts
        if item["retry_kind"] == "infrastructure_pre_input"
    ]
    if len(retries) > 1:
        raise core.LockedEvaluationError(
            "authenticated prediction state repeats its retry"
        )
    retry_receipt = retries[0] if retries else None
    retry_kind = "none" if retry_receipt is None else retry_receipt["retry_kind"]
    execution_id = prediction_receipt["execution_id"]
    if retry_receipt is not None:
        input_receipt = _receipt_for_state(core, receipts, "INPUTS_READ")
        if (
            retry_receipt["execution_id"] != execution_id
            or input_receipt["execution_id"] != execution_id
            or input_receipt["previous_receipt_sha256"]
            != core.state_receipt_sha256(retry_receipt)
        ):
            raise core.LockedEvaluationError(
                "successful prediction receipt does not descend from its retry"
            )
    prefixes = core.evaluation_attempt_prefixes(
        parent_prefix,
        authorization_id,
        "P",
        retry_kind,
        execution_id,
    )
    prediction_prefix = prefixes["predictions"]
    visibility_prefix = prefixes["visibility"]
    manifest_sha256 = prediction_receipt["artifact_manifest_hashes"][
        "predictions_manifest"
    ]
    manifest_blob = f"{prediction_prefix}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    manifest_data, manifest_etag = core.download_stable_blob(
        service, container, manifest_blob
    )
    manifest = core.validate_prediction_artifact_manifest(
        manifest_data,
        expected_sha256=manifest_sha256,
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(manifest) != manifest_data:
        raise core.LockedEvaluationError(
            "prediction artifact manifest bytes are not canonical"
        )
    expected_prediction_members = {
        f"{prediction_prefix}/{name}" for name in core.PREDICTION_MEMBER_NAMES
    }
    if (
        core.list_exact_prefix(service, container, prediction_prefix)
        != expected_prediction_members
    ):
        raise core.LockedEvaluationError(
            "successful prediction attempt membership is not exact"
        )
    metadata = {
        item["name"]: item for item in manifest["payload_members"]
    }
    authenticated_payloads: dict[str, tuple[bytes, str]] = {}
    for name, item in sorted(metadata.items()):
        authenticated_payloads[name] = core.download_verified_blob(
            service,
            container,
            f"{prediction_prefix}/{name}",
            expected_sha256=item["sha256"],
            expected_size=item["size"],
            expected_etag=item["etag"],
        )
    request_name = "prediction_request_manifest.json"
    request_blob = f"{prediction_prefix}/{request_name}"
    request_data, request_etag = authenticated_payloads[request_name]
    request = core.parse_json_strict(request_data, "prediction request manifest")
    core.validate_prediction_request_manifest(
        request,
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(request) != request_data:
        raise core.LockedEvaluationError(
            "prediction request manifest bytes are not canonical"
        )
    seal_name = "prediction_seal.json"
    seal_blob = f"{prediction_prefix}/{seal_name}"
    seal_data, seal_etag = authenticated_payloads[seal_name]
    seal = core.parse_json_strict(seal_data, "locked prediction seal")
    core.validate_locked_prediction_seal_metadata(
        seal,
        request_manifest_bytes=request_data,
        prediction_manifest=manifest,
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(seal) != seal_data:
        raise core.LockedEvaluationError(
            "locked prediction seal bytes are not canonical"
        )
    visibility_blob = f"{visibility_prefix}/stage_p_visibility.json"
    visibility_data, visibility_etag = core.download_verified_blob(
        service,
        container,
        visibility_blob,
        expected_sha256=manifest["stage_p_visibility_sha256"],
        expected_etag=manifest["stage_p_visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_data, "Stage-P visibility record"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="P",
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(visibility) != visibility_data:
        raise core.LockedEvaluationError(
            "Stage-P visibility bytes are not canonical"
        )
    members = [
        _member_metadata(
            core,
            f"{prediction_prefix}/{name}",
            authenticated_payloads[name][0],
            authenticated_payloads[name][1],
        )
        for name in sorted(authenticated_payloads)
    ]
    members.extend(
        [
            _member_metadata(
                core, manifest_blob, manifest_data, manifest_etag
            ),
            _member_metadata(
                core, visibility_blob, visibility_data, visibility_etag
            ),
        ]
    )
    descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        stage="P",
        retry_kind=retry_kind,
        execution_id=execution_id,
        members=members,
    )
    core.validate_attempt_membership_descriptor(descriptor)
    expected_predictions = {
        item["blob_name"]
        for item in descriptor["members"]
        if item["blob_name"].startswith(f"{prediction_prefix}/")
    }
    expected_visibility = {
        item["blob_name"]
        for item in descriptor["members"]
        if item["blob_name"].startswith(f"{visibility_prefix}/")
    }
    retry_receipt_sha256 = None
    if retry_receipt is not None:
        abandoned, abandoned_metadata = _authenticate_abandoned_attempt(
            core,
            service,
            container,
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            stage="P",
            retry_receipt=retry_receipt,
            receipts=receipts,
        )
        retry_receipt_sha256 = core.state_receipt_sha256(retry_receipt)
        roots = core.evaluation_prefixes(parent_prefix, authorization_id)
        expected_predictions |= {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['predictions']}/")
        }
        expected_visibility |= {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['visibility']}/")
        }
        expected_visibility.add(abandoned_metadata["blob_name"])
        if core.list_exact_prefix(
            service, container, visibility_prefix
        ) != {
            visibility_blob,
            abandoned_metadata["blob_name"],
        }:
            raise core.LockedEvaluationError(
                "prediction retry visibility membership is not exact"
            )
    roots = core.evaluation_prefixes(parent_prefix, authorization_id)
    if core.list_exact_prefix(
        service, container, roots["predictions"]
    ) != expected_predictions:
        raise core.LockedEvaluationError(
            "authorization prediction membership is not exact"
        )
    attempt = {
        "stage": "P",
        "retry_kind": retry_kind,
        "execution_id": execution_id,
        "attempt_binding_sha256": core.attempt_binding_sha256(
            "P", retry_kind, execution_id
        ),
        "predictions_prefix": prediction_prefix,
        "predictions_prefix_sha256": core.attempt_prefix_sha256(
            prediction_prefix
        ),
        "visibility_prefix": visibility_prefix,
        "visibility_prefix_sha256": core.attempt_prefix_sha256(
            visibility_prefix
        ),
        "prediction_state_receipt_sha256": core.state_receipt_sha256(
            prediction_receipt
        ),
        "prediction_manifest_sha256": manifest_sha256,
        "prediction_request_manifest_sha256": core.sha256_bytes(request_data),
        "prediction_seal_sha256": core.sha256_bytes(seal_data),
        "input_manifest_sha256": request[
            "locked_input_manifest_sha256"
        ],
        "attempt_descriptor_sha256": (
            core.attempt_membership_descriptor_sha256(descriptor)
        ),
        "retry_receipt_sha256": retry_receipt_sha256,
    }
    return attempt, expected_predictions, expected_visibility


def _authenticate_pending_prediction_attempt(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    authorization_id: str,
    receipts: list[Mapping[str, Any]],
    authorization_lock: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
) -> tuple[dict[str, Any] | None, set[str], set[str]]:
    input_receipt = _receipt_for_state(core, receipts, "INPUTS_READ")
    retries = [
        item
        for item in receipts
        if item["retry_kind"] == "infrastructure_pre_input"
    ]
    if len(retries) > 1:
        raise core.LockedEvaluationError(
            "pending prediction producer repeats its retry"
        )
    retry_kind = "none" if not retries else retries[0]["retry_kind"]
    execution_id = input_receipt["execution_id"]
    prefixes = core.evaluation_attempt_prefixes(
        parent_prefix,
        authorization_id,
        "P",
        retry_kind,
        execution_id,
    )
    prediction_prefix = prefixes["predictions"]
    prediction_members = core.list_exact_prefix(
        service, container, prediction_prefix
    )
    if not prediction_members:
        return None, set(), set()
    expected_members = {
        f"{prediction_prefix}/{name}" for name in core.PREDICTION_MEMBER_NAMES
    }
    if prediction_members != expected_members:
        raise core.LockedEvaluationError(
            "pending prediction producer is incomplete or non-unique"
        )
    manifest_blob = (
        f"{prediction_prefix}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    manifest_data, _ = core.download_stable_blob(
        service, container, manifest_blob
    )
    manifest = core.validate_prediction_artifact_manifest(
        manifest_data,
        expected_sha256=core.sha256_bytes(manifest_data),
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    visibility_blob = (
        f"{prefixes['visibility']}/stage_p_visibility.json"
    )
    visibility_data, _ = core.download_verified_blob(
        service,
        container,
        visibility_blob,
        expected_sha256=manifest["stage_p_visibility_sha256"],
        expected_etag=manifest["stage_p_visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_data, "pending Stage-P visibility"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="P",
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    expected_receipt = core.build_next_state_receipt(
        input_receipt,
        state="PREDICTIONS_VERIFIED",
        artifact_manifest_sha256=core.sha256_bytes(manifest_data),
        timestamp_utc=manifest["created_utc"],
        execution_id=visibility["execution_id"],
        actor=visibility["actor"],
        visibility=[
            *visibility["artifact_classes"],
            f"record_sha256:{manifest['stage_p_visibility_sha256']}",
        ],
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
    )
    attempt, expected_predictions, expected_visibility = (
        _authenticate_prediction_attempt(
            core,
            service,
            container,
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=[*receipts, expected_receipt],
        )
    )
    attempt["receipt_persisted"] = False
    attempt["expected_prediction_state_receipt_sha256"] = (
        core.state_receipt_sha256(expected_receipt)
    )
    return attempt, expected_predictions, expected_visibility


def _authenticate_scoring_attempt(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    state_prefix: str,
    parent_prefix: str,
    authorization_id: str,
    receipts: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], set[str], set[str]]:
    labels_blob = f"{state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    scoring_blob = f"{state_prefix}/{core.SCORING_TRANSACTION_FILENAME}"
    attestation_blob = f"{state_prefix}/{core.SCORING_ATTESTATION_FILENAME}"
    labels, labels_data, _ = _download_canonical_record(
        core, service, container, labels_blob, "labels-open transaction"
    )
    transaction, transaction_data, _ = _download_canonical_record(
        core, service, container, scoring_blob, "scoring transaction"
    )
    attestation, attestation_data, _ = _download_canonical_record(
        core, service, container, attestation_blob, "scoring attestation"
    )
    core.validate_labels_open_transaction(
        labels,
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
    )
    core.validate_scoring_transaction(transaction)
    labels_sha256 = core.sha256_bytes(labels_data)
    transaction_sha256 = core.sha256_bytes(transaction_data)
    common_bindings = (
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "retry_receipt_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "execution_id",
        "actor",
    )
    if (
        any(
            not core.exact_json_equal(labels[field], transaction[field])
            for field in common_bindings
        )
        or labels["visibility_sha256"]
        != transaction["stage_e_visibility_sha256"]
        or transaction["labels_open_transaction_sha256"] != labels_sha256
    ):
        raise core.LockedEvaluationError(
            "labels-open and scoring transaction bindings differ"
        )
    scores_prefix = transaction["scores_prefix"]
    manifest_blob = f"{scores_prefix}/{core.SCORE_MEMBER_NAMES[-1]}"
    if attestation["score_manifest_blob_name"] != manifest_blob:
        raise core.LockedEvaluationError(
            "scoring attestation manifest path is not exact"
        )
    manifest_data, manifest_etag = core.download_verified_blob(
        service,
        container,
        manifest_blob,
        expected_sha256=attestation["score_manifest_sha256"],
        expected_etag=attestation["score_manifest_etag"],
    )
    manifest = core.validate_score_manifest(
        manifest_data,
        expected_sha256=attestation["score_manifest_sha256"],
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
    )
    if core.canonical_json_bytes(manifest) != manifest_data:
        raise core.LockedEvaluationError(
            "score manifest bytes are not canonical"
        )
    core.validate_scoring_attestation(
        attestation,
        transaction=transaction,
        score_manifest_bytes=manifest_data,
        score_manifest_etag=manifest_etag,
    )
    if (
        attestation["scoring_transaction_sha256"] != transaction_sha256
        or attestation["labels_open_transaction_sha256"] != labels_sha256
    ):
        raise core.LockedEvaluationError(
            "scoring attestation transaction hashes differ"
        )
    expected_score_members = {
        f"{scores_prefix}/{name}" for name in core.SCORE_MEMBER_NAMES
    }
    if (
        core.list_exact_prefix(service, container, scores_prefix)
        != expected_score_members
    ):
        raise core.LockedEvaluationError(
            "successful scoring attempt membership is not exact"
        )
    state_names = {
        item["state"]: item
        for item in receipts
        if item["retry_kind"] == "none"
    }
    scores_receipt = state_names.get("SCORES_VERIFIED")
    if (
        scores_receipt is not None
        and scores_receipt["artifact_manifest_hashes"]["scores_manifest"]
        != attestation["score_manifest_sha256"]
    ):
        raise core.LockedEvaluationError(
            "SCORES_VERIFIED receipt does not bind the attested manifest"
        )
    retry_kind = transaction["scoring_retry_kind"]
    execution_id = transaction["execution_id"]
    retries = [
        item
        for item in receipts
        if item["retry_kind"] == "scorer_infrastructure"
    ]
    if (
        (retry_kind == "none" and retries)
        or (retry_kind != "none" and len(retries) != 1)
    ):
        raise core.LockedEvaluationError(
            "scoring attempt retry identity is not unique"
        )
    retry_receipt = None if retry_kind == "none" else retries[0]
    if retry_receipt is not None and (
        retry_receipt["execution_id"] != execution_id
        or transaction["retry_receipt_sha256"]
        != core.state_receipt_sha256(retry_receipt)
    ):
        raise core.LockedEvaluationError(
            "scoring transaction does not bind its retry receipt"
        )
    visibility_prefix = core.derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "visibility",
        "E",
        retry_kind,
        execution_id,
    )
    visibility_blob = f"{visibility_prefix}/stage_e_visibility.json"
    if labels["visibility_blob_name"] != visibility_blob:
        raise core.LockedEvaluationError(
            "labels-open visibility path is not exact"
        )
    visibility_data, visibility_etag = core.download_verified_blob(
        service,
        container,
        visibility_blob,
        expected_sha256=labels["visibility_sha256"],
        expected_etag=labels["visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_data, "Stage-E scoring visibility record"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(visibility) != visibility_data:
        raise core.LockedEvaluationError(
            "Stage-E scoring visibility bytes are not canonical"
        )
    score_payloads: dict[str, bytes] = {}
    members = []
    for item in manifest["payload_members"]:
        member_blob = f"{scores_prefix}/{item['name']}"
        member_data, member_etag = core.download_verified_blob(
            service,
            container,
            member_blob,
            expected_sha256=item["sha256"],
            expected_size=item["size"],
            expected_etag=item["etag"],
        )
        score_payloads[item["name"]] = member_data
        members.append(
            _member_metadata(
                core,
                member_blob,
                member_data,
                member_etag,
            )
        )
    core.validate_scoring_transaction(
        transaction,
        score_payloads=score_payloads,
    )
    members.extend(
        [
            _member_metadata(
                core, manifest_blob, manifest_data, manifest_etag
            ),
            _member_metadata(
                core, visibility_blob, visibility_data, visibility_etag
            ),
        ]
    )
    descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        stage="E",
        retry_kind=retry_kind,
        execution_id=execution_id,
        members=members,
    )
    core.validate_attempt_membership_descriptor(descriptor)
    expected_scores = {
        item["blob_name"]
        for item in descriptor["members"]
        if item["blob_name"].startswith(f"{scores_prefix}/")
    }
    expected_visibility = {
        item["blob_name"]
        for item in descriptor["members"]
        if item["blob_name"].startswith(f"{visibility_prefix}/")
    }
    if retry_receipt is not None:
        abandoned, abandoned_metadata = _authenticate_abandoned_attempt(
            core,
            service,
            container,
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            stage="E",
            retry_receipt=retry_receipt,
            receipts=receipts,
        )
        roots = core.evaluation_prefixes(parent_prefix, authorization_id)
        expected_scores |= {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['scores']}/")
        }
        expected_visibility |= {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['visibility']}/")
        }
        expected_visibility.add(abandoned_metadata["blob_name"])
        if core.list_exact_prefix(
            service, container, visibility_prefix
        ) != {
            visibility_blob,
            abandoned_metadata["blob_name"],
        }:
            raise core.LockedEvaluationError(
                "scoring retry visibility membership is not exact"
            )
    roots = core.evaluation_prefixes(parent_prefix, authorization_id)
    if core.list_exact_prefix(
        service, container, roots["scores"]
    ) != expected_scores:
        raise core.LockedEvaluationError(
            "authorization score membership is not exact"
        )
    attempt = {
        "stage": "E",
        "retry_kind": retry_kind,
        "execution_id": execution_id,
        "attempt_binding_sha256": core.attempt_binding_sha256(
            "E", retry_kind, execution_id
        ),
        "scores_prefix": scores_prefix,
        "scores_prefix_sha256": core.attempt_prefix_sha256(scores_prefix),
        "visibility_prefix": visibility_prefix,
        "visibility_prefix_sha256": core.attempt_prefix_sha256(
            visibility_prefix
        ),
        "score_manifest_sha256": attestation["score_manifest_sha256"],
        "labels_manifest_sha256": transaction["labels_manifest_sha256"],
        "labels_sha256": transaction["labels_sha256"],
        "labels_open_transaction_sha256": labels_sha256,
        "scoring_transaction_sha256": transaction_sha256,
        "scoring_attestation_sha256": core.sha256_bytes(attestation_data),
        "prediction_manifest_sha256": transaction[
            "prediction_manifest_sha256"
        ],
        "prediction_request_manifest_sha256": transaction[
            "prediction_request_manifest_sha256"
        ],
        "prediction_seal_sha256": transaction["prediction_seal_sha256"],
        "attempt_descriptor_sha256": (
            core.attempt_membership_descriptor_sha256(descriptor)
        ),
        "retry_receipt_sha256": transaction["retry_receipt_sha256"],
    }
    return attempt, expected_scores, expected_visibility


def _authenticate_pending_scoring_attempt(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    state_prefix: str,
    parent_prefix: str,
    authorization_id: str,
    receipts: list[Mapping[str, Any]],
    authorization: Mapping[str, Any],
    prediction_attempt: Mapping[str, Any],
) -> tuple[dict[str, Any], set[str], set[str]]:
    transaction_blob = (
        f"{state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    transaction, transaction_data, _ = _download_canonical_record(
        core,
        service,
        container,
        transaction_blob,
        "pending labels-open transaction",
    )
    core.validate_labels_open_transaction(
        transaction,
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
    )
    prediction_receipts = [
        item
        for item in receipts
        if item["state"] == "PREDICTIONS_VERIFIED"
        and item["retry_kind"] == "none"
    ]
    if len(prediction_receipts) != 1:
        raise core.LockedEvaluationError(
            "pending scoring prediction receipt is not unique"
        )
    prediction_receipt = prediction_receipts[0]
    if (
        transaction["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
        or transaction["authorization_manifest_sha256"]
        != authorization["authorization_manifest_sha256"]
        or transaction["implementation_manifest_sha256"]
        != authorization["implementation_manifest_sha256"]
        or transaction["locked_manifest_sha256"]
        != authorization["locked_manifest_sha256"]
        or transaction["implementation_commit"]
        != prediction_receipt["implementation_commit"]
        or transaction["image_digest"] != prediction_receipt["image_digest"]
        or transaction["config_sha256"] != prediction_receipt["config_sha256"]
        or transaction["prediction_manifest_sha256"]
        != prediction_attempt["prediction_manifest_sha256"]
        or transaction["prediction_request_manifest_sha256"]
        != prediction_attempt["prediction_request_manifest_sha256"]
        or transaction["prediction_seal_sha256"]
        != prediction_attempt["prediction_seal_sha256"]
        or transaction["input_manifest_sha256"]
        != prediction_attempt["input_manifest_sha256"]
    ):
        raise core.LockedEvaluationError(
            "pending labels-open transaction provenance differs"
        )

    prediction_manifest_blob = (
        f"{prediction_attempt['predictions_prefix']}/"
        f"{core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    prediction_manifest_data, _ = core.download_stable_blob(
        service,
        container,
        prediction_manifest_blob,
    )
    prediction_manifest = core.validate_prediction_artifact_manifest(
        prediction_manifest_data,
        expected_sha256=prediction_attempt["prediction_manifest_sha256"],
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        expected_retry_kind=prediction_attempt["retry_kind"],
        expected_execution_id=prediction_attempt["execution_id"],
    )
    labels_manifest_blob = (
        f"{parent_prefix}/locked-labels/locked_labels_manifest.json"
    )
    labels_blob = (
        f"{parent_prefix}/locked-labels/locked_reference_labels.jsonl"
    )
    labels_manifest_data, labels_manifest_etag = (
        core.download_verified_blob(
            service,
            container,
            labels_manifest_blob,
            expected_sha256=transaction["labels_manifest_sha256"],
            expected_etag=transaction["labels_manifest_etag"],
        )
    )
    gates = core.load_acceptance_gates(
        core.load_frozen_gate_bytes(PROJECT_ROOT)
    )
    labels_binding = core.validate_locked_labels_manifest(
        labels_manifest_data,
        expected_manifest_sha256=transaction["labels_manifest_sha256"],
        expected_payload_sha256=transaction["labels_sha256"],
        parent_prefix=parent_prefix,
        payload_relative_path=(
            "locked-labels/locked_reference_labels.jsonl"
        ),
        gates=gates,
    )
    if (
        labels_binding["ordered_case_ids"]
        != prediction_manifest["ordered_case_ids"]
        or labels_binding["manifest_sha256"]
        != prediction_receipt["artifact_manifest_hashes"][
            "locked_labels_manifest"
        ]
    ):
        raise core.LockedEvaluationError(
            "pending scoring label universe differs from predictions"
        )

    retry_kind = transaction["scoring_retry_kind"]
    execution_id = transaction["execution_id"]
    scores_prefix = core.validate_exact_attempt_prefix(
        transaction["scores_prefix"],
        parent_prefix,
        authorization_id,
        "scores",
        "E",
        retry_kind,
        execution_id,
    )
    retry_receipts = [
        item
        for item in receipts
        if item["retry_kind"] == "scorer_infrastructure"
    ]
    scoring_predecessor = prediction_receipt
    if retry_kind == "none":
        if retry_receipts:
            raise core.LockedEvaluationError(
                "pending scoring has an unmatched scorer retry"
            )
        retry_receipt_sha256 = None
    else:
        if retry_kind != "scorer_infrastructure" or len(retry_receipts) != 1:
            raise core.LockedEvaluationError(
                "pending scorer retry is not unique"
            )
        retry_receipt = retry_receipts[0]
        retry_receipt_sha256 = core.state_receipt_sha256(retry_receipt)
        if (
            retry_receipt["execution_id"] != execution_id
            or retry_receipt["actor"] != transaction["actor"]
            or transaction["retry_receipt_sha256"]
            != retry_receipt_sha256
        ):
            raise core.LockedEvaluationError(
                "pending scorer retry provenance differs"
            )
        scoring_predecessor = retry_receipt

    visibility_prefix = core.derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "visibility",
        "E",
        retry_kind,
        execution_id,
    )
    visibility_blob = f"{visibility_prefix}/stage_e_visibility.json"
    visibility_data, visibility_etag = core.download_verified_blob(
        service,
        container,
        visibility_blob,
        expected_sha256=transaction["visibility_sha256"],
        expected_etag=transaction["visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_data,
        "pending Stage-E visibility",
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if (
        visibility_data != core.canonical_json_bytes(visibility)
        or visibility["actor"] != transaction["actor"]
    ):
        raise core.LockedEvaluationError(
            "pending Stage-E visibility provenance differs"
        )

    reservation_blob = f"{scores_prefix}/{core.SCORE_MEMBER_NAMES[0]}"
    reservation_data, _ = core.download_stable_blob(
        service,
        container,
        reservation_blob,
    )
    reservation = core.parse_json_strict(
        reservation_data,
        "pending scores reservation",
    )
    core._require_exact_fields(
        reservation,
        {
            "schema_version",
            "leaf",
            "prefix",
            "authorization_id",
            "created_utc",
            "nonce",
            "overwrite",
        },
        "pending scores reservation",
    )
    rebuilt_reservation = core.build_reservation(
        leaf=reservation["leaf"],
        prefix=reservation["prefix"],
        authorization_id=reservation["authorization_id"],
        created_utc=reservation["created_utc"],
        nonce=reservation["nonce"],
        parent_prefix=parent_prefix,
        stage="E",
        retry_kind=retry_kind,
        execution_id=execution_id,
    )
    if (
        reservation_data != core.canonical_json_bytes(reservation)
        or not core.exact_json_equal(reservation, rebuilt_reservation)
        or reservation["prefix"] != scores_prefix
    ):
        raise core.LockedEvaluationError(
            "pending score reservation provenance differs"
        )
    expected_transaction = core.build_labels_open_transaction(
        authorization_id=authorization_id,
        parent_prefix=parent_prefix,
        state_prefix=state_prefix,
        scores_prefix=scores_prefix,
        scoring_retry_kind=retry_kind,
        retry_receipt_sha256=retry_receipt_sha256,
        authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        prediction_manifest_sha256=prediction_attempt[
            "prediction_manifest_sha256"
        ],
        prediction_seal_sha256=prediction_attempt[
            "prediction_seal_sha256"
        ],
        prediction_request_manifest_sha256=prediction_attempt[
            "prediction_request_manifest_sha256"
        ],
        input_manifest_sha256=prediction_attempt["input_manifest_sha256"],
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        labels_manifest_sha256=labels_binding["manifest_sha256"],
        labels_manifest_blob_name=labels_manifest_blob,
        labels_manifest_etag=labels_manifest_etag,
        labels_blob_name=labels_blob,
        labels_sha256=labels_binding["payload_sha256"],
        ordered_case_ids=labels_binding["ordered_case_ids"],
        prior_receipt_sha256=core.state_receipt_sha256(
            scoring_predecessor
        ),
        visibility_blob_name=visibility_blob,
        visibility_sha256=core.sha256_bytes(visibility_data),
        visibility_etag=visibility_etag,
        implementation_commit=prediction_receipt[
            "implementation_commit"
        ],
        image_digest=prediction_receipt["image_digest"],
        config_sha256=prediction_receipt["config_sha256"],
        execution_id=execution_id,
        actor=visibility["actor"],
        created_utc=core.max_canonical_utc(
            reservation["created_utc"],
            scoring_predecessor["timestamp_utc"],
            visibility["created_utc"],
        ),
    )
    if not core.exact_json_equal(transaction, expected_transaction):
        raise core.LockedEvaluationError(
            "pending labels-open transaction differs from provenance"
        )
    labels_receipts = [
        item
        for item in receipts
        if item["state"] == "LABELS_READ" and item["retry_kind"] == "none"
    ]
    if len(labels_receipts) > 1:
        raise core.LockedEvaluationError(
            "pending scoring repeats LABELS_READ"
        )
    expected_labels_receipt = core.build_next_state_receipt(
        scoring_predecessor,
        state="LABELS_READ",
        artifact_manifest_sha256=labels_binding["manifest_sha256"],
        timestamp_utc=expected_transaction["created_utc"],
        execution_id=execution_id,
        actor=visibility["actor"],
        visibility=[
            *visibility["artifact_classes"],
            f"record_sha256:{core.sha256_bytes(visibility_data)}",
        ],
        authorization_lock=authorization["authorization_lock"],
        implementation_manifest_bytes=authorization[
            "implementation_manifest_bytes"
        ],
    )
    if labels_receipts and not core.exact_json_equal(
        labels_receipts[0],
        expected_labels_receipt,
    ):
        raise core.LockedEvaluationError(
            "pending LABELS_READ receipt differs from transaction"
        )

    roots = core.evaluation_prefixes(parent_prefix, authorization_id)
    expected_scores = core.list_exact_prefix(
        service,
        container,
        roots["scores"],
    )
    expected_visibility = core.list_exact_prefix(
        service,
        container,
        roots["visibility"],
    )
    if reservation_blob not in expected_scores or visibility_blob not in (
        expected_visibility
    ):
        raise core.LockedEvaluationError(
            "pending scoring attempt membership is incomplete"
        )
    return (
        {
            "stage": "E",
            "retry_kind": retry_kind,
            "execution_id": execution_id,
            "actor": visibility["actor"],
            "attempt_binding_sha256": core.attempt_binding_sha256(
                "E",
                retry_kind,
                execution_id,
            ),
            "scores_prefix": scores_prefix,
            "scores_prefix_sha256": core.attempt_prefix_sha256(
                scores_prefix
            ),
            "visibility_prefix": visibility_prefix,
            "visibility_prefix_sha256": core.attempt_prefix_sha256(
                visibility_prefix
            ),
            "labels_manifest_sha256": labels_binding["manifest_sha256"],
            "labels_sha256": labels_binding["payload_sha256"],
            "labels_open_transaction_sha256": core.sha256_bytes(
                transaction_data
            ),
            "prediction_manifest_sha256": prediction_attempt[
                "prediction_manifest_sha256"
            ],
            "prediction_request_manifest_sha256": prediction_attempt[
                "prediction_request_manifest_sha256"
            ],
            "prediction_seal_sha256": prediction_attempt[
                "prediction_seal_sha256"
            ],
            "expected_labels_state_receipt_sha256": (
                core.state_receipt_sha256(expected_labels_receipt)
            ),
            "labels_state_receipt_persisted": bool(labels_receipts),
            "score_artifacts_authenticated": False,
            "closure_required": True,
            "retry_receipt_sha256": retry_receipt_sha256,
        },
        expected_scores,
        expected_visibility,
    )


def _authenticate_verification_visibility(
    core: ModuleType,
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    authorization_id: str,
    receipts: list[Mapping[str, Any]],
    verification_receipt: Mapping[str, Any],
    scoring_attempt: Mapping[str, Any],
) -> set[str]:
    previous = _receipt_by_sha256(
        core, receipts, verification_receipt["previous_receipt_sha256"]
    )
    core.validate_retry_state_receipt_provenance(
        verification_receipt,
        previous=previous,
        prior_score_manifest_sha256=scoring_attempt[
            "score_manifest_sha256"
        ],
        prior_labels_open_transaction_sha256=scoring_attempt[
            "labels_open_transaction_sha256"
        ],
        prior_scoring_attestation_sha256=scoring_attempt[
            "scoring_attestation_sha256"
        ],
    )
    execution_id = verification_receipt["execution_id"]
    visibility_prefix = core.derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "visibility",
        "E",
        "verification_only",
        execution_id,
    )
    visibility_blob = f"{visibility_prefix}/stage_e_visibility.json"
    visibility_data, visibility_etag = core.download_stable_blob(
        service, container, visibility_blob
    )
    visibility = core.parse_json_strict(
        visibility_data, "Stage-E verification visibility record"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=authorization_id,
        expected_parent_prefix=parent_prefix,
        expected_retry_kind="verification_only",
        expected_execution_id=execution_id,
    )
    if core.canonical_json_bytes(visibility) != visibility_data:
        raise core.LockedEvaluationError(
            "Stage-E verification visibility bytes are not canonical"
        )
    metadata = _member_metadata(
        core, visibility_blob, visibility_data, visibility_etag
    )
    descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        stage="E",
        retry_kind="verification_only",
        execution_id=execution_id,
        members=[metadata],
    )
    core.validate_attempt_membership_descriptor(descriptor)
    if core.list_exact_prefix(
        service, container, visibility_prefix
    ) != {visibility_blob}:
        raise core.LockedEvaluationError(
            "verification visibility membership is not exact"
        )
    return {visibility_blob}


def _authenticate_persisted(
    core: ModuleType,
    *,
    runtime: Mapping[str, Any],
    runtime_bytes: bytes,
    implementation: Mapping[str, str],
    implementation_bytes: bytes,
    runtime_sha256: str,
    implementation_sha256: str,
    image_binding_bytes: bytes,
    image_binding_sha256: str,
    helper_snapshot_set_sha256: str,
    final_state: str,
    prior_receipt_sha256: str | None,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
) -> dict[str, Any]:
    bindings = runtime["bindings"]
    destination = core.validate_runtime_azure_destination(
        runtime["azure_destination"]
    )
    source_bindings = _git_source_bindings(
        implementation["implementation_commit"]
    )
    launcher = source_bindings[
        "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    ]
    checked_runtime = core.validate_runtime_configuration(
        runtime_bytes,
        expected_sha256=runtime_sha256,
        source_commit=implementation["implementation_commit"],
        parent_prefix=bindings["registered_parent_prefix"],
        authorization_id=bindings["authorization_id"],
        launcher_sha256=launcher["sha256"],
        launcher_git_blob_oid=launcher["git_blob_oid"],
        expected_azure_destination=destination,
        expected_image_digest=implementation["image_digest"],
        image_binding_bytes=image_binding_bytes,
        expected_image_binding_sha256=image_binding_sha256,
    )
    if (
        not core.exact_json_equal(
            checked_runtime["source_bindings"], source_bindings
        )
        or implementation["config_sha256"] != runtime_sha256
        or core.sha256_bytes(implementation_bytes) != implementation_sha256
    ):
        raise core.LockedEvaluationError(
            "persisted authentication inputs are not the committed implementation"
        )
    storage = destination["storage"]
    core.validate_private_endpoint_resolution(
        storage["blob_endpoint"],
        destination["network"]["private_endpoint_nic_private_ips"],
    )
    service = core.create_blob_service(storage["blob_endpoint"])
    state_prefix = bindings["state_prefix"]
    state_members = core.list_exact_prefix(
        service, storage["container"], state_prefix
    )
    if final_state == "LATEST":
        present_states = [
            state
            for state in core.HOLDOUT_STATE_SEQUENCE
            if (
                f"{state_prefix}/{core.STATE_RECEIPT_FILENAMES[state]}"
                in state_members
            )
        ]
        if not present_states:
            raise core.LockedEvaluationError(
                "persisted state has no authenticated receipt"
            )
        final_state = present_states[-1]
    spent_incomplete = (
        f"{state_prefix}/{core.SPENT_INCOMPLETE_FILENAME}" in state_members
    )
    labels_transaction = (
        f"{state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
        in state_members
    )
    scoring_transaction = (
        f"{state_prefix}/{core.SCORING_TRANSACTION_FILENAME}" in state_members
    )
    scoring_attestation = (
        f"{state_prefix}/{core.SCORING_ATTESTATION_FILENAME}" in state_members
    )
    closure_manifest = (
        f"{state_prefix}/{core.CLOSURE_MANIFEST_FILENAME}" in state_members
    )
    invalid_closure = (
        f"{state_prefix}/{core.INVALID_CLOSURE_FILENAME}" in state_members
    )
    state_index = core.HOLDOUT_STATE_SEQUENCE.index(final_state)
    pending_scoring_state = (
        labels_transaction
        and final_state in {"PREDICTIONS_VERIFIED", "LABELS_READ"}
        and not invalid_closure
        and not closure_manifest
    )
    if (
        (
            state_index
            >= core.HOLDOUT_STATE_SEQUENCE.index("LABELS_READ")
            and not invalid_closure
            and not (scoring_transaction and scoring_attestation)
            and not pending_scoring_state
        )
        or (
            final_state == "CLOSED"
            and not (closure_manifest or invalid_closure)
        )
        or (scoring_transaction and not labels_transaction)
        or (closure_manifest and not scoring_attestation)
        or (
            invalid_closure
            and (
                final_state not in {"LABELS_READ", "CLOSED"}
                or not labels_transaction
                or closure_manifest
            )
        )
    ):
        raise core.LockedEvaluationError(
            "persisted-state singleton membership is incomplete"
        )
    authenticated = core.authenticate_authorization_bundle(
        service,
        storage["container"],
        project_root=PROJECT_ROOT,
        parent_prefix=bindings["registered_parent_prefix"],
        authorization_id=bindings["authorization_id"],
        state_prefix=bindings["state_prefix"],
        implementation_commit=implementation["implementation_commit"],
        image_digest=implementation["image_digest"],
        config_sha256=runtime_sha256,
        launcher_sha256=launcher["sha256"],
        launcher_git_blob_oid=launcher["git_blob_oid"],
        expected_prior_receipt_sha256=prior_receipt_sha256,
        expected_authorization_lock_sha256=authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            authorization_manifest_sha256
        ),
        expected_azure_destination=destination,
        expected_image_binding_sha256=image_binding_sha256,
        expected_helper_snapshot_set_sha256=helper_snapshot_set_sha256,
        final_state=final_state,
        labels_transaction=labels_transaction,
        scoring_transaction=scoring_transaction,
        scoring_attestation=scoring_attestation,
        closure_manifest=closure_manifest,
        spent_incomplete=spent_incomplete,
        invalid_closure=invalid_closure,
    )
    verification_retries = [
        receipt
        for receipt in authenticated["receipts"]
        if receipt["retry_kind"] == "verification_only"
    ]
    if len(verification_retries) > 1:
        raise core.LockedEvaluationError(
            "persisted state repeats the verification retry singleton"
        )
    parent_prefix = bindings["registered_parent_prefix"]
    authorization_id = bindings["authorization_id"]
    receipts = authenticated["receipts"]
    prediction_attempt = None
    pending_prediction_attempt = None
    scoring_attempt = None
    pending_scoring_attempt = None
    invalid_scoring_attempt = None
    score_payload_read = False
    expected_predictions: set[str] = set()
    expected_scores: set[str] = set()
    expected_visibility: set[str] = set()
    if final_state == "INPUTS_READ":
        (
            pending_prediction_attempt,
            expected_predictions,
            prediction_visibility,
        ) = _authenticate_pending_prediction_attempt(
            core,
            service,
            storage["container"],
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=receipts,
            authorization_lock=authenticated["authorization_lock"],
            implementation_manifest_bytes=authenticated[
                "implementation_manifest_bytes"
            ],
        )
        expected_visibility |= prediction_visibility
    elif state_index >= core.HOLDOUT_STATE_SEQUENCE.index(
        "PREDICTIONS_VERIFIED"
    ):
        (
            prediction_attempt,
            expected_predictions,
            prediction_visibility,
        ) = _authenticate_prediction_attempt(
            core,
            service,
            storage["container"],
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=receipts,
        )
        expected_visibility |= prediction_visibility
    if invalid_closure:
        invalid = authenticated["invalid_closure_record"]
        expected_scores = {
            item["blob_name"]
            for item in invalid["observed_score_members"]
        }
        expected_visibility |= {
            item["blob_name"]
            for item in invalid["observed_visibility_members"]
        }
        if invalid["scoring_retry_kind"] == "scorer_infrastructure":
            retry_receipts = [
                item
                for item in receipts
                if item["retry_kind"] == "scorer_infrastructure"
            ]
            if len(retry_receipts) != 1:
                raise core.LockedEvaluationError(
                    "INVALID scoring retry receipt is not exact"
                )
            abandoned, abandoned_metadata = _authenticate_abandoned_attempt(
                core,
                service,
                storage["container"],
                parent_prefix=parent_prefix,
                authorization_id=authorization_id,
                stage="E",
                retry_receipt=retry_receipts[0],
                receipts=receipts,
            )
            roots = core.evaluation_prefixes(
                parent_prefix, authorization_id
            )
            expected_scores |= {
                item["blob_name"]
                for item in abandoned["abandoned_members"]
                if item["blob_name"].startswith(f"{roots['scores']}/")
            }
            expected_visibility |= {
                item["blob_name"]
                for item in abandoned["abandoned_members"]
                if item["blob_name"].startswith(f"{roots['visibility']}/")
            }
            expected_visibility.add(abandoned_metadata["blob_name"])
        (
            invalid_scoring_attempt,
            invalid_expected_scores,
            invalid_expected_visibility,
        ) = _authenticate_pending_scoring_attempt(
            core,
            service,
            storage["container"],
            state_prefix=state_prefix,
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=receipts,
            authorization=authenticated,
            prediction_attempt=prediction_attempt,
        )
        if (
            invalid_expected_scores != expected_scores
            or invalid_expected_visibility != expected_visibility
            or invalid_scoring_attempt["retry_kind"]
            != invalid["scoring_retry_kind"]
            or invalid_scoring_attempt["execution_id"]
            != invalid["scoring_execution_id"]
            or invalid_scoring_attempt["actor"]
            != invalid["scoring_actor"]
            or invalid_scoring_attempt[
                "labels_open_transaction_sha256"
            ]
            != invalid["labels_open_transaction_sha256"]
            or invalid_scoring_attempt[
                "expected_labels_state_receipt_sha256"
            ]
            != invalid["labels_read_receipt_sha256"]
            or invalid_scoring_attempt["retry_receipt_sha256"]
            != invalid["retry_receipt_sha256"]
        ):
            raise core.LockedEvaluationError(
                "INVALID closure producer projection differs"
            )
    elif pending_scoring_state:
        if (
            final_state == "LABELS_READ"
            and scoring_transaction
            and scoring_attestation
        ):
            score_payload_read = True
            try:
                (
                    scoring_attempt,
                    expected_scores,
                    scoring_visibility,
                ) = _authenticate_scoring_attempt(
                    core,
                    service,
                    storage["container"],
                    state_prefix=state_prefix,
                    parent_prefix=parent_prefix,
                    authorization_id=authorization_id,
                    receipts=receipts,
                )
                expected_visibility |= scoring_visibility
            except core.LockedEvaluationError:
                scoring_attempt = None
        if scoring_attempt is None:
            (
                pending_scoring_attempt,
                expected_scores,
                scoring_visibility,
            ) = _authenticate_pending_scoring_attempt(
                core,
                service,
                storage["container"],
                state_prefix=state_prefix,
                parent_prefix=parent_prefix,
                authorization_id=authorization_id,
                receipts=receipts,
                authorization=authenticated,
                prediction_attempt=prediction_attempt,
            )
            expected_visibility |= scoring_visibility
    elif state_index >= core.HOLDOUT_STATE_SEQUENCE.index("LABELS_READ"):
        score_payload_read = True
        (
            scoring_attempt,
            expected_scores,
            scoring_visibility,
        ) = _authenticate_scoring_attempt(
            core,
            service,
            storage["container"],
            state_prefix=state_prefix,
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=receipts,
        )
        expected_visibility |= scoring_visibility
    if verification_retries:
        if scoring_attempt is None:
            raise core.LockedEvaluationError(
                "verification receipt has no authenticated scoring attempt"
            )
        expected_visibility |= _authenticate_verification_visibility(
            core,
            service,
            storage["container"],
            parent_prefix=parent_prefix,
            authorization_id=authorization_id,
            receipts=receipts,
            verification_receipt=verification_retries[0],
            scoring_attempt=scoring_attempt,
        )
    core.validate_authorization_membership(
        service,
        storage["container"],
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        expected={
            "predictions": expected_predictions,
            "scores": expected_scores,
            "state": state_members,
            "visibility": expected_visibility,
        },
    )
    return {
        "status": "PERSISTED_STATE_AUTHENTICATED",
        "state": final_state,
        "runtime_config_sha256": authenticated["runtime_config_sha256"],
        "implementation_manifest_sha256": (
            authenticated["implementation_manifest_sha256"]
        ),
        "authorization_lock_sha256": (
            authenticated["authorization_lock_sha256"]
        ),
        "authorization_manifest_sha256": (
            authenticated["authorization_manifest_sha256"]
        ),
        "prior_state_receipt_sha256": core.state_receipt_sha256(
            authenticated["prior_receipt"]
        ),
        "verification_retry_execution_id": (
            None
            if not verification_retries
            else verification_retries[0]["execution_id"]
        ),
        "prediction_attempt": prediction_attempt,
        "pending_prediction_attempt": pending_prediction_attempt,
        "scoring_attempt": scoring_attempt,
        "pending_scoring_attempt": pending_scoring_attempt,
        "invalid_scoring_attempt": invalid_scoring_attempt,
        "result_status": authenticated["result_status"],
        "image_digest": implementation["image_digest"],
        "azure_destination_sha256": checked_runtime[
            "azure_destination_sha256"
        ],
        "image_binding_sha256": checked_runtime["image_binding_sha256"],
        "helper_snapshot_set_sha256": checked_runtime[
            "helper_snapshot_set_sha256"
        ],
        "private_read_performed": True,
        "locked_input_payload_read": False,
        "locked_labels_payload_read": False,
        "score_payload_read": score_payload_read,
        "writes_performed": False,
    }


def main() -> int:
    cli = _parser().parse_args()
    try:
        core = _load_core()
        runtime_bytes = cli.runtime_config_file.read_bytes()
        implementation_bytes = cli.implementation_manifest_file.read_bytes()
        image_binding_bytes = cli.image_binding_file.read_bytes()
        runtime = core.parse_json_strict(runtime_bytes, "runtime config")
        implementation = core.validate_implementation_manifest(
            implementation_bytes
        )
        bindings = runtime.get("bindings")
        destination = runtime.get("azure_destination")
        if not isinstance(bindings, Mapping) or not isinstance(
            destination, Mapping
        ):
            raise core.LockedEvaluationError(
                "persisted runtime configuration is incomplete"
            )
        storage = destination.get("storage")
        image = destination.get("image")
        network = destination.get("network")
        if not all(
            isinstance(item, Mapping) for item in (storage, image, network)
        ):
            raise core.LockedEvaluationError(
                "persisted Azure runtime destination is incomplete"
            )
        args = argparse.Namespace(
            account_url=storage["blob_endpoint"],
            container=storage["container"],
            parent_prefix=bindings["registered_parent_prefix"],
            authorization_id=bindings["authorization_id"],
            state_prefix=bindings["state_prefix"],
            implementation_commit=implementation["implementation_commit"],
            image_digest=image["digest"],
            runtime_config_sha256=cli.runtime_config_sha256,
            implementation_manifest_sha256=(
                cli.implementation_manifest_sha256
            ),
            image_binding_sha256=cli.image_binding_sha256,
            helper_snapshot_set_sha256=cli.helper_snapshot_set_sha256,
            execution_id=cli.execution_id,
            actor=cli.actor,
        )
        if os.environ.get("JSPACE_LOCKED_EVAL_ROLE") != "custodian":
            raise core.LockedEvaluationError(
                "bootstrap is restricted to the custodian execution role"
            )
        if cli.authenticate_only_state is not None:
            required_hashes = (
                cli.authorization_lock_sha256,
                cli.authorization_manifest_sha256,
            )
            if cli.authenticate_only_state != "LATEST":
                required_hashes = (
                    cli.prior_state_receipt_sha256,
                    *required_hashes,
                )
            if any(value is None for value in required_hashes):
                raise core.LockedEvaluationError(
                    "persisted-state authentication hashes are incomplete"
                )
            result = _authenticate_persisted(
                core,
                runtime=runtime,
                runtime_bytes=runtime_bytes,
                implementation=implementation,
                implementation_bytes=implementation_bytes,
                runtime_sha256=cli.runtime_config_sha256,
                implementation_sha256=(
                    cli.implementation_manifest_sha256
                ),
                image_binding_bytes=image_binding_bytes,
                image_binding_sha256=cli.image_binding_sha256,
                helper_snapshot_set_sha256=(
                    cli.helper_snapshot_set_sha256
                ),
                final_state=cli.authenticate_only_state,
                prior_receipt_sha256=cli.prior_state_receipt_sha256,
                authorization_lock_sha256=cli.authorization_lock_sha256,
                authorization_manifest_sha256=(
                    cli.authorization_manifest_sha256
                ),
            )
        else:
            if cli.execution_id is None or cli.actor is None:
                raise core.LockedEvaluationError(
                    "initial bootstrap requires exact execution and actor"
                )
            result = run_bootstrap(
                args,
                core=core,
                custodian_authorized=True,
                runtime_config_bytes=runtime_bytes,
                implementation_manifest_bytes=implementation_bytes,
                image_binding_bytes=image_binding_bytes,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BOOTSTRAP_FAILED",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
