"""Public, synthetic tests for the Phase 1.2B locked-evaluation scaffold."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping

import pytest


ROOT = Path(__file__).parent.parent
CORE_PATH = (
    ROOT
    / "src"
    / "jspace_observation"
    / "parser_v2_locked_evaluation.py"
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = _load_module("_test_parser_v2_locked_evaluation_core", CORE_PATH)
runner = _load_module(
    "_test_run_parser_v2_locked_predictions",
    ROOT / "scripts" / "run_parser_v2_locked_predictions.py",
)
finalizer = _load_module(
    "_test_finalize_parser_v2_locked_evaluation",
    ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py",
)
bootstrap = _load_module(
    "_test_bootstrap_parser_v2_locked_evaluation",
    ROOT / "scripts" / "bootstrap_parser_v2_locked_evaluation.py",
)
azure_contract = _load_module(
    "_test_parser_v2_azure_contract",
    ROOT / "scripts" / "parser_v2_azure_contract.py",
)
runtime_config_generator = _load_module(
    "_test_create_parser_v2_runtime_config",
    ROOT / "scripts" / "create_parser_v2_runtime_config.py",
)


@pytest.fixture
def _isolated_stage_e_modules():
    def forbidden(name: str) -> bool:
        return name == "jspace_observation" or any(
            part in name for part in finalizer.FORBIDDEN_MODULE_PARTS
        )

    snapshot = {
        name: module
        for name, module in list(sys.modules.items())
        if forbidden(name)
    }
    for name in snapshot:
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if forbidden(name):
                sys.modules.pop(name, None)
        sys.modules.update(snapshot)


PARENT = "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z"
AUTHORIZATION = "public-synthetic-authorization"
TIMESTAMP = "2026-07-20T05:45:24Z"
IMPLEMENTATION = "c" * 40
IMAGE_DIGEST = "sha256:" + "d" * 64
LAUNCHER_SHA256 = "e" * 64
LAUNCHER_GIT_BLOB_OID = "f" * 40
SCORING_LEDGER_SHA256 = "d" * 64
SCORING_LEDGER_SIZE = 123
SCORING_LEDGER_ETAG = '"synthetic-scoring-ledger"'
SUBSCRIPTION_ID = "11111111-1111-4111-8111-111111111111"
RESOURCE_GROUP = "rg-synthetic-parser-v2"
BASE_IMAGE = (
    "python:3.11.14-slim-bookworm@"
    "sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d"
)


def _coordination_binding() -> dict[str, Any]:
    zone_name = "pv2-cas.invalid"
    zone_id = (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Network/privateDnsZones/{zone_name}"
    )
    return {
        "schema_version": azure_contract.COORDINATION_BINDING_SCHEMA_VERSION,
        "zone_name": zone_name,
        "zone_resource_id": zone_id,
        "zone_location": "global",
        "zone_internal_id": "44444444-4444-4444-8444-444444444444",
        "private_dns_api_version": "2024-06-01",
        "record_ttl": 300,
        "expected_vnet_link_count": 0,
        "lock_name": "pv2-cas-cannot-delete",
        "lock_resource_id": (
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
            "/providers/Microsoft.Authorization/locks/"
            "pv2-cas-cannot-delete"
        ),
        "lock_level": "CanNotDelete",
        "management_lock_api_version": "2016-09-01",
    }


def _synthetic_image_binding() -> dict[str, Any]:
    files = {
        path: {
            "git_blob_oid": (
                LAUNCHER_GIT_BLOB_OID
                if path == "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
                else "b" * 40
            ),
            "sha256": (
                LAUNCHER_SHA256
                if path == "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
                else "a" * 64
            ),
            "size": index,
        }
        for index, path in enumerate(core.IMAGE_BINDING_SOURCE_PATHS, start=1)
    }
    source = {
        "schema_version": core.BUILD_SOURCE_BINDING_SCHEMA_VERSION,
        "source_commit": IMPLEMENTATION,
        "source_repository_url": azure_contract.BUILD_SOURCE_REPOSITORY_URL,
        "remote_source_location": (
            f"{azure_contract.BUILD_SOURCE_REPOSITORY_URL}#{IMPLEMENTATION}"
        ),
        "base_image": BASE_IMAGE,
        "image_repository": "j-space-observation-parser-eval",
        "files": files,
    }
    provenance = azure_contract.build_provenance_record(
        source,
        acr_resource_id=(
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
            "/providers/Microsoft.ContainerRegistry/registries/"
            "syntheticregistry"
        ),
        login_server="syntheticregistry.azurecr.io",
        acr_location="eastasia",
        coordination_binding=_coordination_binding(),
    )
    provenance_sha256 = azure_contract.build_provenance_sha256(provenance)
    coordination = _coordination_binding()
    coordination_sha256 = azure_contract.coordination_binding_sha256(
        coordination
    )
    build_domain = provenance["coordination"]["build_slot"]["domain_sha256"]
    build_record_name = provenance["coordination"]["build_slot"]["record_name"]
    build_etag = '"synthetic-dns-record-etag"'
    oci = {
        "schema_version": core.OCI_VERIFICATION_SCHEMA_VERSION,
        "image_digest": IMAGE_DIGEST,
        "manifest_sha256": IMAGE_DIGEST.removeprefix("sha256:"),
        "config_digest": "sha256:" + "6" * 64,
        "config_sha256": "6" * 64,
        "provenance_label": {
            "name": core.BUILD_PROVENANCE_LABEL,
            "value": provenance_sha256,
        },
    }
    return {
        **source,
        "schema_version": core.IMAGE_BINDING_SCHEMA_VERSION,
        "source_binding_sha256": core.sha256_bytes(
            core.canonical_json_bytes(source)
        ),
        "build_provenance": provenance,
        "build_provenance_sha256": provenance_sha256,
        "build_run_request_sha256": "7" * 64,
        "oci_verification_sha256": core.sha256_bytes(
            core.canonical_json_bytes(oci)
        ),
        "oci_verification": oci,
        "staging_image_tag": f"staging-{IMPLEMENTATION}-{'1' * 32}",
        "image_tag": IMPLEMENTATION,
        "image_digest": IMAGE_DIGEST,
        "image_digest_ref": (
            "syntheticregistry.azurecr.io/"
            f"j-space-observation-parser-eval@{IMAGE_DIGEST}"
        ),
        "acr_build_task_run_name": "pv2tr-" + "4" * 20,
        "acr_build_task_run_resource_id": (
            f"/subscriptions/{SUBSCRIPTION_ID}/resourcegroups/{RESOURCE_GROUP}"
            "/providers/microsoft.containerregistry/registries/"
            "syntheticregistry/taskRuns/pv2tr-" + "4" * 20
        ),
        "acr_build_run_id": "ca1",
        "coordination_binding": coordination,
        "coordination_binding_sha256": coordination_sha256,
        "build_slot": {
            "domain_sha256": build_domain,
            "record_name": build_record_name,
            "record_resource_id": (
                f"{coordination['zone_resource_id']}/TXT/{build_record_name}"
            ),
            "record_etag": build_etag,
            "record_etag_sha256": hashlib.sha256(
                build_etag.encode("ascii")
            ).hexdigest(),
            "payload_sha256": "8" * 64,
            "claim_nonce": "1" * 32,
            "record_ttl": coordination["record_ttl"],
        },
        "historical_finalization_supported": True,
        "changeable_attributes": {
            "tag_write_enabled": False,
            "tag_delete_enabled": False,
            "manifest_write_enabled": False,
            "manifest_delete_enabled": False,
        },
        "cpu_only": True,
        "gpu": False,
        "stage_p_and_e_same_digest": True,
        "mutable_latest_forbidden": True,
    }


IMAGE_BINDING = _synthetic_image_binding()
IMAGE_BINDING_BYTES = core.canonical_json_bytes(IMAGE_BINDING)
IMAGE_BINDING_SHA256 = core.sha256_bytes(IMAGE_BINDING_BYTES)


def _runtime_source_bindings() -> dict[str, dict[str, str]]:
    return {
        path: {
            "git_blob_oid": IMAGE_BINDING["files"][path]["git_blob_oid"],
            "sha256": IMAGE_BINDING["files"][path]["sha256"],
        }
        for path in core.RUNTIME_SOURCE_BINDING_PATHS
    }


def _azure_destination() -> dict[str, Any]:
    prefix = (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
        "/providers"
    )
    account = "syntheticaccount"
    registry = "syntheticregistry"
    repository = "j-space-observation-parser-eval"
    return {
        "subscription_id": SUBSCRIPTION_ID,
        "resource_group": RESOURCE_GROUP,
        "location": "southeastasia",
        "container_apps": {
            "environment_name": "cae-synthetic",
            "environment_resource_id": (
                f"{prefix}/Microsoft.App/managedEnvironments/cae-synthetic"
            ),
            "job_name": "job-synthetic-parser-v2",
            "job_resource_id": (
                f"{prefix}/Microsoft.App/jobs/job-synthetic-parser-v2"
            ),
            "workload_profile": "Consumption",
        },
        "managed_identity": {
            "name": "id-synthetic-parser-v2",
            "resource_id": (
                f"{prefix}/Microsoft.ManagedIdentity/"
                "userAssignedIdentities/id-synthetic-parser-v2"
            ),
            "client_id": "22222222-2222-4222-8222-222222222222",
            "principal_id": "33333333-3333-4333-8333-333333333333",
        },
        "storage": {
            "account_name": account,
            "resource_id": (
                f"{prefix}/Microsoft.Storage/storageAccounts/{account}"
            ),
            "blob_endpoint": f"https://{account}.blob.core.windows.net",
            "container": "synthetic-container",
            "public_network_access": "Disabled",
            "shared_key_access": False,
            "allow_blob_public_access": False,
            "container_public_access": None,
        },
        "network": {
            "vnet_resource_id": (
                f"{prefix}/Microsoft.Network/virtualNetworks/vnet-synthetic"
            ),
            "infrastructure_subnet_resource_id": (
                f"{prefix}/Microsoft.Network/virtualNetworks/vnet-synthetic/"
                "subnets/snet-aca"
            ),
            "private_endpoint_subnet_resource_id": (
                f"{prefix}/Microsoft.Network/virtualNetworks/vnet-synthetic/"
                "subnets/snet-private-endpoints"
            ),
            "private_endpoint_resource_id": (
                f"{prefix}/Microsoft.Network/privateEndpoints/pe-synthetic-blob"
            ),
            "private_endpoint_name": "pe-synthetic-blob",
            "private_endpoint_resource_group": RESOURCE_GROUP,
            "private_link_connection_name": "psc-synthetic-blob",
            "storage_private_endpoint_connection_name": (
                "pec-synthetic-blob"
            ),
            "storage_private_endpoint_connection_resource_id": (
                f"{prefix}/Microsoft.Storage/storageAccounts/{account}/"
                "privateEndpointConnections/pec-synthetic-blob"
            ),
            "private_link_group_id": "blob",
            "private_link_subresource": "blob",
            "private_endpoint_nic_private_ips": ["10.0.2.4"],
            "private_dns_zone_name": "privatelink.blob.core.windows.net",
            "private_dns_zone_resource_id": (
                f"{prefix}/Microsoft.Network/privateDnsZones/"
                "privatelink.blob.core.windows.net"
            ),
            "private_dns_zone_group_name": "pdzg-synthetic-blob",
            "private_dns_vnet_link_name": "pdnsl-synthetic-vnet",
        },
        "coordination": _coordination_binding(),
        "registry": {
            "name": registry,
            "resource_id": (
                f"{prefix}/Microsoft.ContainerRegistry/registries/{registry}"
            ),
            "login_server": f"{registry}.azurecr.io",
            "repository": repository,
        },
        "image": {
            "digest": IMAGE_DIGEST,
            "reference": (
                f"{registry}.azurecr.io/{repository}@{IMAGE_DIGEST}"
            ),
            "base_image": BASE_IMAGE,
            "binding_sha256": IMAGE_BINDING_SHA256,
            "provenance": core.image_binding_essential_record(IMAGE_BINDING),
        },
    }


def _runtime_config_bytes() -> bytes:
    return core.canonical_json_bytes(
        core.build_runtime_configuration(
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            launcher_sha256=LAUNCHER_SHA256,
            launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
            source_bindings=_runtime_source_bindings(),
            azure_destination=_azure_destination(),
            image_binding=IMAGE_BINDING,
            image_binding_sha256=IMAGE_BINDING_SHA256,
        )
    )


RUNTIME_CONFIG_BYTES = _runtime_config_bytes()
CONFIG_SHA256 = core.sha256_bytes(RUNTIME_CONFIG_BYTES)
HELPER_SNAPSHOT_SET_SHA256 = core.parse_json_strict(
    RUNTIME_CONFIG_BYTES, "runtime configuration"
)["helper_snapshot_set_sha256"]


def _implementation_manifest_bytes() -> bytes:
    return core.canonical_json_bytes(
        {
            "schema_version": core.IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
            "implementation_commit": IMPLEMENTATION,
            "image_digest": IMAGE_DIGEST,
            "config_sha256": CONFIG_SHA256,
        }
    )


IMPLEMENTATION_MANIFEST_BYTES = _implementation_manifest_bytes()


@pytest.fixture
def workdir():
    root = ROOT / ".pytest-work" / uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        def remove_read_only(function, path, _error):
            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(root, onerror=remove_read_only)
        if root.parent.exists() and not any(root.parent.iterdir()):
            root.parent.rmdir()


@pytest.fixture(scope="module")
def synthetic_bundle():
    from tests import test_evaluator_validation as frozen_tests

    dataset = frozen_tests._dataset()
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    locked_inputs = deepcopy(dataset["materialized"]["locked_inputs"])
    predictions = frozen_tests._prediction_envelopes(labels, locked_inputs)
    for prediction in predictions:
        prediction["parser_result"]["parser_version"] = core.FROZEN_PARSER_VERSION
    legacy_rows = []
    old_legacy = frozen_tests._legacy_predictions(labels)
    locked_by_id = {item["case_id"]: item for item in locked_inputs}
    for row in old_legacy:
        parsed = row["parsed_answer"]
        result = {
            "parsed_answer": parsed,
            "parse_valid": row["parse_valid"],
            "parse_error_type": None if row["parse_valid"] else "no_numeric_found",
            "parse_ambiguous": row["parse_ambiguous"],
            "parse_strategy": "synthetic_frozen_legacy",
            "candidate_answers": [] if parsed is None else [parsed],
            "answer_format_warning": None,
        }
        legacy_rows.append(
            core.build_legacy_prediction(locked_by_id[row["case_id"]], result)
        )
    return {
        "frozen_tests": frozen_tests,
        "frozen": frozen_tests.v,
        "dataset": dataset,
        "labels": labels,
        "locked_inputs": locked_inputs,
        "predictions": predictions,
        "legacy": legacy_rows,
        "gates": core.load_frozen_gate_bytes(ROOT),
    }


def _score(
    bundle: Mapping[str, Any],
    *,
    predictions: list[dict[str, Any]] | None = None,
    legacy: list[dict[str, Any]] | None = None,
):
    return core.score_locked_evaluation(
        bundle["labels"],
        predictions or bundle["predictions"],
        legacy or bundle["legacy"],
        bundle["gates"],
        raise_on_invalid=True,
    )


def _synthetic_scoring_ledger(
    bundle: Mapping[str, Any],
    *,
    execution_id: str = "synthetic-scoring-execution",
):
    labels_bytes = core.canonical_jsonl_bytes(bundle["labels"])
    predictions_bytes = core.canonical_jsonl_bytes(bundle["predictions"])
    legacy_bytes = core.canonical_jsonl_bytes(bundle["legacy"])
    ordered_ids = [item["case_id"] for item in bundle["labels"]]
    context = {
        "authorization_id": AUTHORIZATION,
        "registered_parent_prefix": PARENT,
        "authorization_lock_sha256": "1" * 64,
        "authorization_manifest_sha256": "2" * 64,
        "implementation_manifest_sha256": core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        "prediction_manifest_sha256": "3" * 64,
        "prediction_seal_sha256": "4" * 64,
        "prediction_request_manifest_sha256": "5" * 64,
        "locked_manifest_sha256": "6" * 64,
        "input_manifest_sha256": "7" * 64,
        "locked_input_sha256": "8" * 64,
        "labels_manifest_sha256": "9" * 64,
        "labels_manifest_etag": '"synthetic-labels-manifest"',
        "labels_sha256": core.sha256_bytes(labels_bytes),
        "labels_size": len(labels_bytes),
        "labels_etag": '"synthetic-labels"',
        "labels_open_transaction_sha256": "a" * 64,
        "scores_prefix": core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        "scoring_retry_kind": "none",
        "stage_e_visibility_sha256": "b" * 64,
        "retry_receipt_sha256": None,
        "case_universe_sha256": core.case_universe_sha256(ordered_ids),
        "row_count": len(ordered_ids),
        "acceptance_gates_sha256": core.FROZEN_ACCEPTANCE_GATE_SHA256,
        "implementation_commit": IMPLEMENTATION,
        "image_digest": IMAGE_DIGEST,
        "config_sha256": CONFIG_SHA256,
        "scoring_execution_id": execution_id,
        "scoring_actor": "synthetic-actor",
        "created_utc": TIMESTAMP,
    }
    ledger_bytes, metrics, failures = core.build_scoring_ledger_bytes(
        labels_bytes,
        predictions_bytes,
        legacy_bytes,
        bundle["gates"],
        context=context,
        expected_ordered_case_ids=ordered_ids,
    )
    return {
        "context": context,
        "ledger_bytes": ledger_bytes,
        "labels_bytes": labels_bytes,
        "predictions_bytes": predictions_bytes,
        "legacy_bytes": legacy_bytes,
        "ordered_ids": ordered_ids,
        "metrics": metrics,
        "failures": failures,
    }


def _no_answer_result(output_text: str) -> dict[str, Any]:
    return {
        "schema_version": core.PARSER_RESULT_SCHEMA_VERSION,
        "parser_version": core.FROZEN_PARSER_VERSION,
        "answer_type": "numeric",
        "input_sha256": core.sha256_bytes(output_text.encode("utf-8")),
        "answer_presence": "absent",
        "parse_valid": False,
        "parse_ambiguous": False,
        "parsed_answer": None,
        "candidate_answers": [],
        "evidence_spans": [],
        "extraction_strategy": "none",
        "output_quality": "complete",
        "failure_reasons": ["no_reliable_answer"],
        "format_warnings": [],
    }


def _numeric_spans(
    output_text: str,
    *,
    excluded: set[tuple[int, int, str]] = frozenset(),
    excluded_value: str | None = None,
) -> list[tuple[int, int, str, str]]:
    result = []
    for match in re.finditer(r"[0-9]+", output_text):
        identity = (match.start(), match.end(), match.group())
        if identity in excluded:
            continue
        try:
            core._validate_numeric_token_context(
                output_text, match.start(), match.end(), "synthetic span"
            )
            normalized = core.normalize_rational_literal(match.group())
        except core.LockedEvaluationError:
            continue
        if normalized == excluded_value:
            continue
        result.append((*identity, normalized))
    return result


def _present_result_at(
    output_text: str, span: tuple[int, int, str, str]
) -> dict[str, Any]:
    start, end, text, normalized = span
    return {
        "schema_version": core.PARSER_RESULT_SCHEMA_VERSION,
        "parser_version": core.FROZEN_PARSER_VERSION,
        "answer_type": "numeric",
        "input_sha256": core.sha256_bytes(output_text.encode("utf-8")),
        "answer_presence": "present",
        "parse_valid": True,
        "parse_ambiguous": False,
        "parsed_answer": normalized,
        "candidate_answers": [normalized],
        "evidence_spans": [
            {
                "start": start,
                "end": end,
                "text": text,
                "kind": "single_candidate",
                "normalized_answer": normalized,
                "disposition": "selected",
            }
        ],
        "extraction_strategy": "single_candidate",
        "output_quality": "complete",
        "failure_reasons": [],
        "format_warnings": [],
    }


def _alternate_present_result(label: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {
        (item["start"], item["end"], item["text"])
        for item in label["acceptable_selected_spans"]
    }
    spans = _numeric_spans(
        label["output_text"],
        excluded=excluded,
        excluded_value=label["registered_reference_answer"],
    )
    assert spans
    return _present_result_at(label["output_text"], spans[0])


def _ambiguous_result(label: Mapping[str, Any]) -> dict[str, Any]:
    spans = _numeric_spans(label["output_text"])
    selected: list[tuple[int, int, str, str]] = []
    values: set[str] = set()
    for span in spans:
        if span[3] not in values:
            selected.append(span)
            values.add(span[3])
        if len(selected) == 2:
            break
    assert len(selected) == 2
    return {
        "schema_version": core.PARSER_RESULT_SCHEMA_VERSION,
        "parser_version": core.FROZEN_PARSER_VERSION,
        "answer_type": "numeric",
        "input_sha256": core.sha256_bytes(label["output_text"].encode("utf-8")),
        "answer_presence": "uncertain",
        "parse_valid": True,
        "parse_ambiguous": True,
        "parsed_answer": None,
        "candidate_answers": [item[3] for item in selected],
        "evidence_spans": [
            {
                "start": item[0],
                "end": item[1],
                "text": item[2],
                "kind": "single_candidate",
                "normalized_answer": item[3],
                "disposition": "ambiguous_candidate",
            }
            for item in selected
        ],
        "extraction_strategy": "ambiguous_candidates",
        "output_quality": "complete",
        "failure_reasons": [],
        "format_warnings": [],
    }


def _replace_results(
    bundle: Mapping[str, Any],
    replacements: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    predictions = deepcopy(bundle["predictions"])
    for prediction in predictions:
        replacement = replacements.get(prediction["case_id"])
        if replacement is not None:
            prediction["parser_result"] = dict(replacement)
    return predictions


def _labels(
    bundle: Mapping[str, Any],
    *,
    stratum: str | None = None,
    presence: str | None = None,
    correctness: bool | None = None,
) -> list[dict[str, Any]]:
    result = list(bundle["labels"])
    if stratum is not None:
        result = [item for item in result if item["stratum"] == stratum]
    if presence is not None:
        result = [
            item
            for item in result
            if item["expected_answer_presence"] == presence
        ]
    if correctness is not None:
        result = [
            item for item in result if item["expected_correctness"] is correctness
        ]
    return result


def _exact_legacy(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    locked = {item["case_id"]: item for item in bundle["locked_inputs"]}
    rows = []
    for label in bundle["labels"]:
        presence = label["expected_answer_presence"]
        if presence == "present":
            parsed = label["expected_parsed_answer"]
            result = {
                "parsed_answer": parsed,
                "parse_valid": True,
                "parse_error_type": None,
                "parse_ambiguous": False,
                "parse_strategy": "synthetic_exact",
                "candidate_answers": [parsed],
                "answer_format_warning": None,
            }
        elif presence == "ambiguous":
            parsed = label["expected_candidate_answers"][0]
            result = {
                "parsed_answer": parsed,
                "parse_valid": True,
                "parse_error_type": None,
                "parse_ambiguous": True,
                "parse_strategy": "synthetic_exact",
                "candidate_answers": list(label["expected_candidate_answers"]),
                "answer_format_warning": None,
            }
        else:
            result = {
                "parsed_answer": None,
                "parse_valid": False,
                "parse_error_type": "no_numeric_found",
                "parse_ambiguous": False,
                "parse_strategy": "synthetic_exact",
                "candidate_answers": [],
                "answer_format_warning": None,
            }
        rows.append(core.build_legacy_prediction(locked[label["case_id"]], result))
    return rows


def test_parser_free_core_and_finalizer_import_graph():
    core.assert_parser_free_source(CORE_PATH.read_bytes(), str(CORE_PATH))
    core.assert_parser_free_source(
        (ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py").read_bytes(),
        "finalizer",
    )
    core.assert_parser_free_subprocess(
        (CORE_PATH, ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py")
    )
    assert not any(
        name == "jspace_observation" for name in core.__dict__.get("__package__", ())
    )


def test_stage_e_ast_and_runtime_guards_reject_parser_imports(workdir):
    bad = workdir / "bad_finalizer.py"
    bad.write_text(
        "from jspace_observation.eval_parsing_v2 import parse_v2\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="forbidden import"):
        finalizer._source_import_guard(bad)
    blocker = finalizer._ParserImportBlocker()
    with pytest.raises(ImportError, match="blocks parser import"):
        blocker.find_spec("jspace_observation.eval_parsing")
    bad_subprocess = (
        b"import subprocess\n"
        b"subprocess.run(['python','-c','import jspace_observation.eval_parsing'])\n"
    )
    with pytest.raises(core.LockedEvaluationError, match="subprocess"):
        core.assert_parser_free_source(bad_subprocess, "bad_subprocess.py")
    for source in (
        b"import runpy\nrunpy.run_path('eval_parsing.py')\n",
        (
            b"from importlib.machinery import SourceFileLoader\n"
            b"loader=SourceFileLoader('alias','eval_'+'parsing_v2.py')\n"
        ),
        b"exec(open('eval_parsing.py').read(),{})\n",
    ):
        with pytest.raises(core.LockedEvaluationError, match="execution path"):
            core.assert_parser_free_source(source, "static_bypass.py")


def test_stage_p_has_no_label_reference_or_correctness_channel():
    destinations = {action.dest for action in runner._parser()._actions}
    assert not any(
        token in destination
        for destination in destinations
        for token in ("label", "reference", "correctness")
    )
    with pytest.raises(core.LockedEvaluationError, match="prohibited channel"):
        core.validate_stage_p_environment({"LOCKED_LABEL_BLOB": "private"})
    with pytest.raises(core.LockedEvaluationError, match="prohibited channel"):
        core.validate_stage_p_environment(
            {"UNRELATED_PATH": "private/locked-labels/labels.jsonl"}
        )
    with pytest.raises(core.LockedEvaluationError, match="prohibited channel"):
        core.assert_label_blind_payload({"expected_answer": "7"})
    core.assert_label_blind_payload({"labels_accessed": False, "result": {}})


def test_stage_runtime_environment_and_cli_channels_are_exact(capsys, monkeypatch):
    environment = {
        "AZURE_CLIENT_ID": "12345678-1234-1234-1234-123456789abc",
        "HOME": "/nonexistent",
        "IDENTITY_ENDPOINT": "http://localhost:42356/msi/token",
        "IDENTITY_HEADER": "platform-managed-capability",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TMPDIR": "/runtime/work",
    }
    core.validate_stage_p_environment(environment)
    core.validate_stage_e_environment(environment)
    for validator, extra in (
        (core.validate_stage_p_environment, "OPAQUE_METADATA_B64"),
        (core.validate_stage_p_environment, "LOCKED_LABEL_ALIAS"),
        (core.validate_stage_p_environment, "BASH_ENV"),
        (core.validate_stage_p_environment, "BASH_FUNC_python%%"),
        (core.validate_stage_p_environment, "CDPATH"),
        (core.validate_stage_p_environment, "GLOBIGNORE"),
        (core.validate_stage_p_environment, "PYTHONPATH"),
        (core.validate_stage_p_environment, "PYTHONWARNINGS"),
        (core.validate_stage_e_environment, "LOCKED_INPUT_ALIAS"),
        (core.validate_stage_e_environment, "PARSER_SOURCE_ALIAS"),
        (core.validate_stage_e_environment, "MODEL_PATH"),
    ):
        adversarial = dict(environment)
        adversarial[extra] = "cmVmZXJlbmNlLWNvcnJlY3RuZXNz"
        with pytest.raises(core.LockedEvaluationError):
            validator(adversarial)

    for parser, arguments in (
        (runner._parser(), ["--label-b64", "cmVmZXJlbmNl"]),
        (runner._parser(), ["--account", "opaque"]),
        (
            runner._parser(),
            ["--account-url", "one", "--account-url", "two"],
        ),
        (finalizer._parser(), ["--locked-input-path", "opaque"]),
        (finalizer._parser(), ["--parser-path", "opaque"]),
        (finalizer._parser(), ["--account-url=opaque"]),
    ):
        with pytest.raises(Exception, match="arguments rejected"):
            parser.parse_args(arguments)
    with pytest.raises(argparse.ArgumentTypeError):
        runner._execution_id("Y29ycmVjdG5lc3M")
    with pytest.raises(argparse.ArgumentTypeError):
        finalizer._execution_id("cmVmZXJlbmNl")
    assert next(
        action
        for action in runner._parser()._actions
        if action.dest == "actor"
    ).choices == ("stage-p-managed-runtime",)
    assert next(
        action
        for action in finalizer._parser()._actions
        if action.dest == "actor"
    ).choices == ("stage-e-managed-runtime",)
    adopt_destinations = {
        action.dest for action in runner._adopt_parser()._actions
    }
    assert not any(
        "input" in destination or "parser" in destination
        for destination in adopt_destinations
    )
    assert next(
        action
        for action in runner._adopt_parser()._actions
        if action.dest == "actor"
    ).choices == ("stage-p-adoption-runtime",)

    monkeypatch.setattr(runner, "_load_core", lambda: core)
    monkeypatch.setattr(
        runner,
        "_load_stage_p_parsers",
        lambda: (_ for _ in ()).throw(
            AssertionError("adopt-only CLI loaded a parser")
        ),
    )

    def adopt_only(args, *, core):
        assert args.parent_prefix == PARENT
        return {
            "status": "PREDICTIONS_VERIFIED",
            "input_count": 120,
            "parser_v2_prediction_count": 120,
            "legacy_prediction_count": 120,
        }

    monkeypatch.setattr(runner, "run_stage_p_adoption", adopt_only)
    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    adopt_args = [
        "--adopt-only",
        "--account-url",
        "https://syntheticaccount.blob.core.windows.net",
        "--expected-private-endpoint-ip",
        "10.0.0.4",
        "--container",
        "synthetic-container",
        "--parent-prefix",
        PARENT,
        "--authorization-id",
        AUTHORIZATION,
        "--predictions-prefix",
        prefixes["predictions"],
        "--state-prefix",
        prefixes["state"],
        "--visibility-prefix",
        prefixes["visibility"],
        "--prior-state-receipt-blob",
        f"{prefixes['state']}/08_inputs_read_receipt.json",
        "--prior-state-receipt-sha256",
        "1" * 64,
        "--prediction-manifest-sha256",
        "2" * 64,
        "--expected-predictions-receipt-sha256",
        "3" * 64,
        "--implementation-commit",
        IMPLEMENTATION,
        "--image-digest",
        IMAGE_DIGEST,
        "--config-sha256",
        CONFIG_SHA256,
        "--image-binding-sha256",
        IMAGE_BINDING_SHA256,
        "--helper-snapshot-set-sha256",
        HELPER_SNAPSHOT_SET_SHA256,
        "--authorization-lock-sha256",
        "4" * 64,
        "--authorization-manifest-sha256",
        "5" * 64,
        "--launcher-sha256",
        LAUNCHER_SHA256,
        "--launcher-git-blob-oid",
        LAUNCHER_GIT_BLOB_OID,
        "--retry-kind",
        "prediction_adoption",
        "--producer-retry-kind",
        "none",
        "--producer-execution-id",
        f"stage-p-{'a' * 32}",
        "--execution-id",
        f"stage-p-{'b' * 32}",
        "--actor",
        "stage-p-adoption-runtime",
    ]
    assert runner.main(adopt_args) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "PREDICTIONS_VERIFIED"
    assert runner.main(["--adopt-only", "--parser-module", "opaque"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "opaque" not in captured.err

    with pytest.raises(core.LockedEvaluationError, match="arguments are not exact"):
        finalizer._run_stage_e(
            SimpleNamespace(
                verify_only=False,
                retry_kind="none",
                verification_state="CLOSED",
                scores_manifest_sha256="a" * 64,
                closed_receipt_sha256=None,
            ),
            service=object(),
            core=core,
        )

    monkeypatch.setattr(finalizer, "_load_core", lambda: core)
    secret = "PRIVATE-ARTIFACT-CONTENT"
    assert finalizer.main(["--locked-input-path", secret]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert secret not in captured.err
    assert captured.err.strip() == (
        "STAGE_E_ERROR:ARGUMENTS_REJECTED:ArgumentError"
    )


def test_finalizer_has_no_parser_or_locked_input_option():
    destinations = {action.dest for action in finalizer._parser()._actions}
    assert not any("parser" in item or "input" in item for item in destinations)


def test_frozen_gate_hash_and_protocol_bundle_are_exact():
    gates = core.load_frozen_gate_bytes(ROOT)
    assert hashlib.sha256(gates).hexdigest() == core.FROZEN_ACCEPTANCE_GATE_SHA256
    assert (
        core.compute_protocol_bundle_sha256(ROOT)
        == core.FROZEN_PROTOCOL_BUNDLE_SHA256
    )
    with pytest.raises(core.LockedEvaluationError, match="SHA-256"):
        core.load_acceptance_gates(gates + b" ")


def test_prediction_membership_and_schemas_fail_closed(synthetic_bundle):
    gates = core.load_acceptance_gates(synthetic_bundle["gates"])
    assert len(
        core.validate_prediction_rows(
            synthetic_bundle["predictions"],
            synthetic_bundle["legacy"],
            synthetic_bundle["locked_inputs"],
            gates,
        )
    ) == gates["dataset_contract"]["total_cases"]
    with pytest.raises(core.LockedEvaluationError, match="counts"):
        core.validate_prediction_rows(
            synthetic_bundle["predictions"][:-1],
            synthetic_bundle["legacy"],
            synthetic_bundle["locked_inputs"],
            gates,
        )
    malformed = deepcopy(synthetic_bundle["predictions"])
    malformed[0]["extra"] = True
    with pytest.raises(core.LockedEvaluationError, match="schema fields"):
        core.validate_prediction_rows(
            malformed,
            synthetic_bundle["legacy"],
            synthetic_bundle["locked_inputs"],
            gates,
        )


def test_scoring_ledger_reconstructs_exact_registered_rows(synthetic_bundle):
    fixture = _synthetic_scoring_ledger(synthetic_bundle)
    validated = core.validate_scoring_ledger_bytes(
        fixture["ledger_bytes"],
        fixture["predictions_bytes"],
        fixture["legacy_bytes"],
        synthetic_bundle["gates"],
        context=fixture["context"],
        expected_ordered_case_ids=fixture["ordered_ids"],
    )
    rows = core.parse_jsonl_strict(
        fixture["ledger_bytes"], core.SCORING_LEDGER_FILENAME
    )
    assert len(rows) == 120
    assert validated["labels_bytes"] == fixture["labels_bytes"]
    assert validated["metrics"] == fixture["metrics"]
    assert validated["failures"] == fixture["failures"]
    assert [row["case_id"] for row in rows] == fixture["ordered_ids"]
    assert all(
        row["label_record_sha256"]
        == core.sha256_bytes(base64.b64decode(row["label_record_base64"]))
        for row in rows
    )


def test_scoring_ledger_rejects_forged_label_and_prediction_hash(
    synthetic_bundle,
):
    fixture = _synthetic_scoring_ledger(synthetic_bundle)
    rows = core.parse_jsonl_strict(
        fixture["ledger_bytes"], core.SCORING_LEDGER_FILENAME
    )
    forged_label_rows = deepcopy(rows)
    label = core.parse_json_strict(
        base64.b64decode(forged_label_rows[0]["label_record_base64"]),
        "synthetic ledger label",
    )
    label["curation_notes"] += " forged"
    label_bytes = core.canonical_json_bytes(label)
    forged_label_rows[0]["label_record_base64"] = base64.b64encode(
        label_bytes
    ).decode("ascii")
    forged_label_rows[0]["label_record_size"] = len(label_bytes)
    forged_label_rows[0]["label_record_sha256"] = core.sha256_bytes(
        label_bytes
    )
    with pytest.raises(
        core.LockedEvaluationError, match="registered locked labels"
    ):
        core.validate_scoring_ledger_bytes(
            core.canonical_jsonl_bytes(forged_label_rows),
            fixture["predictions_bytes"],
            fixture["legacy_bytes"],
            synthetic_bundle["gates"],
            context=fixture["context"],
            expected_ordered_case_ids=fixture["ordered_ids"],
        )

    forged_prediction_rows = deepcopy(rows)
    forged_prediction_rows[0]["parser_v2_prediction_row_sha256"] = "f" * 64
    with pytest.raises(core.LockedEvaluationError, match="mechanically"):
        core.validate_scoring_ledger_bytes(
            core.canonical_jsonl_bytes(forged_prediction_rows),
            fixture["predictions_bytes"],
            fixture["legacy_bytes"],
            synthetic_bundle["gates"],
            context=fixture["context"],
            expected_ordered_case_ids=fixture["ordered_ids"],
        )
    forged_predictions = deepcopy(synthetic_bundle["predictions"])
    forged_index = next(
        index
        for index, label in enumerate(synthetic_bundle["labels"])
        if label["expected_parsed_answer"] is not None
    )
    forged_predictions[forged_index] = core.build_prediction_envelope(
        synthetic_bundle["locked_inputs"][forged_index],
        _no_answer_result(
            synthetic_bundle["labels"][forged_index]["output_text"]
        ),
    )
    with pytest.raises(core.LockedEvaluationError, match="mechanically"):
        core.validate_scoring_ledger_bytes(
            fixture["ledger_bytes"],
            core.canonical_jsonl_bytes(forged_predictions),
            fixture["legacy_bytes"],
            synthetic_bundle["gates"],
            context=fixture["context"],
            expected_ordered_case_ids=fixture["ordered_ids"],
        )


def test_scoring_ledger_rejects_membership_order_and_execution_forgery(
    synthetic_bundle,
):
    fixture = _synthetic_scoring_ledger(synthetic_bundle)
    rows = core.parse_jsonl_strict(
        fixture["ledger_bytes"], core.SCORING_LEDGER_FILENAME
    )
    candidates = (
        rows[:-1],
        [*rows, deepcopy(rows[-1])],
        [rows[1], rows[0], *rows[2:]],
    )
    for candidate in candidates:
        with pytest.raises(core.LockedEvaluationError):
            core.validate_scoring_ledger_bytes(
                core.canonical_jsonl_bytes(candidate),
                fixture["predictions_bytes"],
                fixture["legacy_bytes"],
                synthetic_bundle["gates"],
                context=fixture["context"],
                expected_ordered_case_ids=fixture["ordered_ids"],
            )
    forged_ordinal = deepcopy(rows)
    forged_ordinal[1]["row_index"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_scoring_ledger_bytes(
            core.canonical_jsonl_bytes(forged_ordinal),
            fixture["predictions_bytes"],
            fixture["legacy_bytes"],
            synthetic_bundle["gates"],
            context=fixture["context"],
            expected_ordered_case_ids=fixture["ordered_ids"],
        )
    wrong_execution = dict(fixture["context"])
    wrong_execution["scoring_execution_id"] = "wrong-scoring-execution"
    with pytest.raises(core.LockedEvaluationError, match="immutable context"):
        core.validate_scoring_ledger_bytes(
            fixture["ledger_bytes"],
            fixture["predictions_bytes"],
            fixture["legacy_bytes"],
            synthetic_bundle["gates"],
            context=wrong_execution,
            expected_ordered_case_ids=fixture["ordered_ids"],
        )


def test_genuine_ledger_rejects_self_consistent_forged_aggregate_chain(
    synthetic_bundle,
):
    fixture = _synthetic_scoring_ledger(synthetic_bundle)
    ledger_sha256 = core.sha256_bytes(fixture["ledger_bytes"])
    ledger_size = len(fixture["ledger_bytes"])
    ledger_etag = '"synthetic-ledger"'
    context = fixture["context"]
    bindings = {
        "authorization_id": context["authorization_id"],
        "registered_parent_prefix": context["registered_parent_prefix"],
        "authorization_lock_sha256": context["authorization_lock_sha256"],
        "authorization_manifest_sha256": context[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": context[
            "implementation_manifest_sha256"
        ],
        "prediction_seal_sha256": context["prediction_seal_sha256"],
        "prediction_manifest_sha256": context["prediction_manifest_sha256"],
        "prediction_request_manifest_sha256": context[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": context["locked_manifest_sha256"],
        "input_manifest_sha256": context["input_manifest_sha256"],
        "locked_input_sha256": context["locked_input_sha256"],
        "labels_manifest_sha256": context["labels_manifest_sha256"],
        "labels_sha256": context["labels_sha256"],
        "labels_open_transaction_sha256": context[
            "labels_open_transaction_sha256"
        ],
        "scores_prefix": context["scores_prefix"],
        "scoring_retry_kind": context["scoring_retry_kind"],
        "scoring_execution_id": context["scoring_execution_id"],
        "scoring_actor": context["scoring_actor"],
        "stage_e_visibility_sha256": context[
            "stage_e_visibility_sha256"
        ],
        "retry_receipt_sha256": context["retry_receipt_sha256"],
        "scoring_ledger_sha256": ledger_sha256,
        "scoring_ledger_size": ledger_size,
        "scoring_ledger_etag": ledger_etag,
        "case_universe_sha256": context["case_universe_sha256"],
        "row_count": context["row_count"],
        "implementation_commit": context["implementation_commit"],
        "image_digest": context["image_digest"],
        "config_sha256": context["config_sha256"],
    }
    target = next(
        label
        for label in synthetic_bundle["labels"]
        if label["stratum"] == "S04"
        and label["expected_parsed_answer"] is not None
    )
    forged_predictions = _replace_results(
        synthetic_bundle,
        {
            target["case_id"]: _no_answer_result(target["output_text"]),
        },
    )
    forged_metrics, forged_failures = _score(
        synthetic_bundle, predictions=forged_predictions
    )
    assert forged_metrics["status"] == "PASS"
    forged_metrics = core.bind_metrics_artifacts(forged_metrics, **bindings)
    payload_args = {
        **bindings,
        "scores_prefix": core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        "scoring_ledger_bytes": fixture["ledger_bytes"],
        "created_utc": TIMESTAMP,
        "nonce": "synthetic-forged-aggregate",
    }
    forged_payloads, forged_decision, forged_retirement = (
        core.build_score_payloads(
            forged_metrics,
            forged_failures,
            **payload_args,
        )
    )
    transaction = core.build_scoring_transaction(
        authorization_id=context["authorization_id"],
        parent_prefix=context["registered_parent_prefix"],
        state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)[
            "state"
        ],
        scores_prefix=payload_args["scores_prefix"],
        scoring_retry_kind=context["scoring_retry_kind"],
        retry_receipt_sha256=context["retry_receipt_sha256"],
        stage_e_visibility_sha256=context[
            "stage_e_visibility_sha256"
        ],
        authorization_lock_sha256=context["authorization_lock_sha256"],
        authorization_manifest_sha256=context[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=context[
            "implementation_manifest_sha256"
        ],
        prediction_manifest_sha256=context["prediction_manifest_sha256"],
        prediction_seal_sha256=context["prediction_seal_sha256"],
        prediction_request_manifest_sha256=context[
            "prediction_request_manifest_sha256"
        ],
        locked_manifest_sha256=context["locked_manifest_sha256"],
        input_manifest_sha256=context["input_manifest_sha256"],
        locked_input_sha256=context["locked_input_sha256"],
        labels_manifest_sha256=context["labels_manifest_sha256"],
        labels_sha256=context["labels_sha256"],
        labels_open_transaction_sha256=context[
            "labels_open_transaction_sha256"
        ],
        scoring_ledger_sha256=ledger_sha256,
        scoring_ledger_size=ledger_size,
        scoring_ledger_etag=ledger_etag,
        case_universe_sha256=context["case_universe_sha256"],
        row_count=context["row_count"],
        implementation_commit=context["implementation_commit"],
        image_digest=context["image_digest"],
        config_sha256=context["config_sha256"],
        score_payloads=forged_payloads,
        outcome=forged_metrics["status"],
        execution_id=context["scoring_execution_id"],
        actor=context["scoring_actor"],
        created_utc=TIMESTAMP,
    )
    core.validate_scoring_transaction(
        transaction, score_payloads=forged_payloads
    )
    core.validate_decision(forged_metrics, forged_decision)
    core.validate_retirement_record(forged_decision, forged_retirement)
    metadata = [
        {
            "name": name,
            "size": len(forged_payloads[name]),
            "sha256": core.sha256_bytes(forged_payloads[name]),
            "etag": (
                ledger_etag
                if name == core.SCORING_LEDGER_FILENAME
                else f'"synthetic-{index}"'
            ),
        }
        for index, name in enumerate(core.SCORE_MEMBER_NAMES[:-1])
    ]
    manifest = core.build_score_manifest(
        metadata=metadata,
        authorization_id=context["authorization_id"],
        authorization_lock_sha256=context["authorization_lock_sha256"],
        authorization_manifest_sha256=context[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=context[
            "implementation_manifest_sha256"
        ],
        parent_prefix=context["registered_parent_prefix"],
        scores_prefix=payload_args["scores_prefix"],
        scoring_retry_kind=context["scoring_retry_kind"],
        retry_receipt_sha256=context["retry_receipt_sha256"],
        prediction_seal_sha256=context["prediction_seal_sha256"],
        prediction_manifest_sha256=context["prediction_manifest_sha256"],
        prediction_request_manifest_sha256=context[
            "prediction_request_manifest_sha256"
        ],
        locked_manifest_sha256=context["locked_manifest_sha256"],
        input_manifest_sha256=context["input_manifest_sha256"],
        locked_input_sha256=context["locked_input_sha256"],
        labels_manifest_sha256=context["labels_manifest_sha256"],
        labels_manifest_blob_name=(
            f"{PARENT}/locked-labels/locked_labels_manifest.json"
        ),
        labels_manifest_etag=context["labels_manifest_etag"],
        labels_blob_name=(
            f"{PARENT}/locked-labels/locked_reference_labels.jsonl"
        ),
        labels_sha256=context["labels_sha256"],
        labels_open_transaction_sha256=context[
            "labels_open_transaction_sha256"
        ],
        labels_etag=context["labels_etag"],
        scoring_ledger_sha256=ledger_sha256,
        scoring_ledger_size=ledger_size,
        scoring_ledger_etag=ledger_etag,
        case_universe_sha256=context["case_universe_sha256"],
        row_count=context["row_count"],
        scoring_transaction_sha256=core.sha256_bytes(
            core.canonical_json_bytes(transaction)
        ),
        scoring_execution_id=context["scoring_execution_id"],
        scoring_actor=context["scoring_actor"],
        stage_e_visibility_sha256="b" * 64,
        stage_e_visibility_etag='"synthetic-visibility"',
        gate_sha256=core.FROZEN_ACCEPTANCE_GATE_SHA256,
        metrics_sha256=core.sha256_bytes(
            forged_payloads["locked_evaluation_metrics.json"]
        ),
        decision_sha256=core.sha256_bytes(
            forged_payloads["locked_evaluation_decision.json"]
        ),
        retirement_sha256=core.sha256_bytes(
            forged_payloads["retirement_record.json"]
        ),
        implementation_commit=context["implementation_commit"],
        image_digest=context["image_digest"],
        config_sha256=context["config_sha256"],
        outcome=forged_metrics["status"],
        created_utc=TIMESTAMP,
    )
    manifest_bytes = core.canonical_json_bytes(manifest)
    attestation = core.build_scoring_attestation(
        transaction,
        score_manifest_bytes=manifest_bytes,
        score_manifest_etag='"synthetic-score-manifest"',
    )
    core.validate_scoring_attestation(
        attestation,
        transaction=transaction,
        score_manifest_bytes=manifest_bytes,
        score_manifest_etag='"synthetic-score-manifest"',
    )

    ledger_validation = core.validate_scoring_ledger_bytes(
        fixture["ledger_bytes"],
        fixture["predictions_bytes"],
        fixture["legacy_bytes"],
        synthetic_bundle["gates"],
        context=context,
        expected_ordered_case_ids=fixture["ordered_ids"],
    )
    recomputed_metrics = core.bind_metrics_artifacts(
        ledger_validation["metrics"], **bindings
    )
    recomputed_payloads, _, _ = core.build_score_payloads(
        recomputed_metrics,
        ledger_validation["failures"],
        **payload_args,
    )
    assert forged_metrics != recomputed_metrics
    assert any(
        forged_payloads[name] != recomputed_payloads[name]
        for name in core.SCORE_MEMBER_NAMES[2:-1]
    )


def test_stage_p_invokes_each_parser_once_with_exact_request(synthetic_bundle):
    locked = synthetic_bundle["locked_inputs"][0]
    expected_result = synthetic_bundle["predictions"][0]["parser_result"]
    requests = []
    legacy_inputs = []

    def parse_v2(request):
        requests.append(dict(request))
        return deepcopy(expected_result)

    @dataclasses.dataclass
    class Legacy:
        parsed_answer: str | None
        parse_valid: bool
        parse_error_type: str | None
        parse_ambiguous: bool
        parse_strategy: str | None
        candidate_answers: list[str] | None
        answer_format_warning: str | None

    def parse_legacy(text):
        legacy_inputs.append(text)
        return Legacy("1", True, None, False, "single_number", ["1"], None)

    predictions, legacy = runner.generate_prediction_rows(
        [locked],
        parse_v2=parse_v2,
        parse_legacy=parse_legacy,
        core=core,
    )
    assert len(predictions) == len(legacy) == 1
    assert list(requests[0]) == ["schema_version", "answer_type", "output_text"]
    assert legacy_inputs == [locked["output_text"]]


def test_metrics_overlap_frozen_scorer_and_legacy_adapter(synthetic_bundle):
    metrics, _ = _score(synthetic_bundle)
    frozen = synthetic_bundle["frozen"]
    frozen_predictions = deepcopy(synthetic_bundle["predictions"])
    seal = frozen.build_prediction_seal(
        frozen_predictions,
        synthetic_bundle["locked_inputs"],
        implementation_commit=IMPLEMENTATION,
        sealed_utc=TIMESTAMP,
    )
    frozen_legacy = [
        {"case_id": item["case_id"], "legacy_result": item["legacy_result"]}
        for item in synthetic_bundle["legacy"]
    ]
    old = frozen.score_validation_set(
        synthetic_bundle["labels"],
        frozen_predictions,
        frozen_legacy,
        locked_inputs=synthetic_bundle["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=IMPLEMENTATION,
        raise_on_invalid=True,
    )
    assert metrics["status"] == old["status"]
    assert (
        metrics["overall_typed_agreement"]["numerator"]
        == old["overall_exact_typed_decision"]["correct"]
    )
    for actual in core.TYPED_DECISION_CLASSES:
        for predicted in core.TYPED_DECISION_CLASSES:
            assert (
                metrics["confusion_matrix"][actual][predicted]["numerator"]
                == old["confusion_matrix"][actual][predicted]
            )
    assert (
        metrics["answer_presence_macro_f1"]["rate"]["rational"]
        == old["answer_presence_macro_f1"]["canonical"]
    )
    for stratum in old["per_stratum"]:
        assert (
            metrics["per_stratum"][stratum]["typed_agreement"]["numerator"]
            == old["per_stratum"][stratum]["parser_v2_correct"]
        )
    for name, old_status in old["gates"].items():
        assert metrics["gates"][name]["status"] == old_status
    for row in synthetic_bundle["legacy"]:
        assert core.adapt_legacy_result(row["legacy_result"]) == frozen.adapt_legacy_result(
            row["legacy_result"]
        )


def test_all_registered_hard_gates_are_emitted(synthetic_bundle):
    metrics, _ = _score(synthetic_bundle)
    gate_contract = core.load_acceptance_gates(synthetic_bundle["gates"])
    dataset = gate_contract["dataset_contract"]
    expected = {
        "overall_exact_typed_decision",
        "answer_presence_macro_f1",
        "ambiguity_precision",
        "ambiguity_recall",
        "no_answer_precision",
        "no_answer_recall",
        "boxed_final_miss",
        "last_number_trap",
        "wrong_span",
        "material_correctness",
        "clean_pooled_non_regression",
        "critical_strict_improvement",
        *(f"stratum_floor_{item}" for item in dataset["strata"]),
        *(
            f"answer_bearing_{item}"
            for item in dataset["answer_bearing_strata"]
        ),
        *(
            f"material_correctness_{key.removesuffix('_maximum_errors')}"
            for key in gate_contract["absolute_gates"]["material_correctness"]
            if re.fullmatch(r"S[0-9]{2}_maximum_errors", key)
        ),
    }
    assert set(metrics["gates"]) == expected
    assert all(
        set(record)
        == {
            "numerator",
            "denominator",
            "rate",
            "threshold",
            "passed",
            "status",
            "reason",
        }
        for record in metrics["gates"].values()
    )


def test_exact_fraction_threshold_comparison_never_rounds():
    boundary = core.metric_record(
        19,
        20,
        comparison=">=",
        threshold=core.Fraction(19, 20),
        mandatory=True,
    )
    below = core.metric_record(
        19 * 10**30 - 1,
        20 * 10**30,
        comparison=">=",
        threshold=core.Fraction(19, 20),
        mandatory=True,
    )
    assert boundary["status"] == "PASS"
    assert below["status"] == "FAIL"
    assert boundary["rate"]["rational"] == "19/20"


def test_overall_answer_bearing_and_floor_boundaries(synthetic_bundle):
    present = _labels(synthetic_bundle, presence="present")
    six = {
        label["case_id"]: _no_answer_result(label["output_text"])
        for label in present[:6]
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, six),
    )
    assert metrics["gates"]["overall_exact_typed_decision"]["status"] == "PASS"
    seven = dict(six)
    seven[present[6]["case_id"]] = _no_answer_result(present[6]["output_text"])
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, seven),
    )
    assert metrics["gates"]["overall_exact_typed_decision"]["status"] == "FAIL"

    s01 = _labels(synthetic_bundle, stratum="S01")
    one = {s01[0]["case_id"]: _no_answer_result(s01[0]["output_text"])}
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one),
    )
    assert metrics["gates"]["answer_bearing_S01"]["status"] == "PASS"
    two = {
        **one,
        s01[1]["case_id"]: _no_answer_result(s01[1]["output_text"]),
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, two),
    )
    assert metrics["gates"]["answer_bearing_S01"]["status"] == "FAIL"
    assert metrics["gates"]["stratum_floor_S01"]["status"] == "PASS"
    three = {
        **two,
        s01[2]["case_id"]: _no_answer_result(s01[2]["output_text"]),
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, three),
    )
    assert metrics["gates"]["stratum_floor_S01"]["status"] == "FAIL"


def test_ambiguity_precision_and_recall_boundaries(synthetic_bundle):
    ambiguous = _labels(synthetic_bundle, presence="ambiguous")
    replacements = {
        ambiguous[0]["case_id"]: _no_answer_result(ambiguous[0]["output_text"])
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, replacements),
    )
    assert metrics["gates"]["ambiguity_recall"]["status"] == "PASS"
    replacements[ambiguous[1]["case_id"]] = _no_answer_result(
        ambiguous[1]["output_text"]
    )
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, replacements),
    )
    assert metrics["gates"]["ambiguity_recall"]["status"] == "FAIL"

    present = [
        item
        for item in _labels(synthetic_bundle, stratum="S06")
        if len({span[3] for span in _numeric_spans(item["output_text"])}) >= 2
    ]
    assert len(present) >= 2
    one_fp = {present[0]["case_id"]: _ambiguous_result(present[0])}
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one_fp),
    )
    assert metrics["gates"]["ambiguity_precision"]["status"] == "PASS"
    one_fp[present[1]["case_id"]] = _ambiguous_result(present[1])
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one_fp),
    )
    assert metrics["gates"]["ambiguity_precision"]["status"] == "FAIL"


def test_no_answer_precision_and_recall_boundaries(synthetic_bundle):
    no_answer = [
        item
        for item in _labels(synthetic_bundle, presence="no_answer")
        if _numeric_spans(item["output_text"])
    ]
    assert len(no_answer) >= 4
    replacements = {
        item["case_id"]: _alternate_present_result(item)
        for item in no_answer[:3]
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, replacements),
    )
    assert metrics["gates"]["no_answer_recall"]["status"] == "PASS"
    replacements[no_answer[3]["case_id"]] = _alternate_present_result(
        no_answer[3]
    )
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, replacements),
    )
    assert metrics["gates"]["no_answer_recall"]["status"] == "FAIL"

    present = _labels(synthetic_bundle, presence="present")
    false_positives = {
        item["case_id"]: _no_answer_result(item["output_text"])
        for item in present[:3]
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, false_positives),
    )
    assert metrics["gates"]["no_answer_precision"]["status"] == "PASS"
    false_positives[present[3]["case_id"]] = _no_answer_result(
        present[3]["output_text"]
    )
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, false_positives),
    )
    assert metrics["gates"]["no_answer_precision"]["status"] == "FAIL"


def test_zero_denominator_is_na_invalid(synthetic_bundle):
    replacements = {
        label["case_id"]: _no_answer_result(label["output_text"])
        for label in synthetic_bundle["labels"]
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, replacements),
    )
    assert metrics["gates"]["ambiguity_precision"]["status"] == "NA_INVALID"
    assert metrics["gates"]["ambiguity_precision"]["passed"] is None
    assert metrics["status"] == "INVALID"


def test_boxed_final_last_number_and_wrong_span_gates(synthetic_bundle):
    s01 = _labels(synthetic_bundle, stratum="S01")[0]
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(
            synthetic_bundle,
            {s01["case_id"]: _no_answer_result(s01["output_text"])},
        ),
    )
    assert metrics["gates"]["boxed_final_miss"]["status"] == "FAIL"

    s06 = _labels(synthetic_bundle, stratum="S06")[0]
    distractor = s06["last_number_distractor_span"]
    normalized = core.normalize_rational_literal(distractor["text"])
    trap_result = _present_result_at(
        s06["output_text"],
        (
            distractor["start"],
            distractor["end"],
            distractor["text"],
            normalized,
        ),
    )
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(
            synthetic_bundle, {s06["case_id"]: trap_result}
        ),
    )
    assert metrics["gates"]["last_number_trap"]["status"] == "FAIL"

    targets = _labels(synthetic_bundle, stratum="S06")[:2]
    one = {targets[0]["case_id"]: _alternate_present_result(targets[0])}
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one),
    )
    assert metrics["gates"]["wrong_span"]["status"] == "PASS"
    one[targets[1]["case_id"]] = _alternate_present_result(targets[1])
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one),
    )
    assert metrics["gates"]["wrong_span"]["status"] == "FAIL"


def test_material_clean_and_critical_comparison_gates(synthetic_bundle):
    s03_correct = _labels(
        synthetic_bundle, stratum="S03", correctness=True
    )
    one = {
        s03_correct[0]["case_id"]: _no_answer_result(
            s03_correct[0]["output_text"]
        )
    }
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one),
    )
    assert metrics["gates"]["material_correctness"]["status"] == "PASS"
    one[s03_correct[1]["case_id"]] = _no_answer_result(
        s03_correct[1]["output_text"]
    )
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(synthetic_bundle, one),
    )
    assert metrics["gates"]["material_correctness"]["status"] == "FAIL"

    s01_correct = _labels(
        synthetic_bundle, stratum="S01", correctness=True
    )[0]
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(
            synthetic_bundle,
            {
                s01_correct["case_id"]: _no_answer_result(
                    s01_correct["output_text"]
                )
            },
        ),
    )
    assert metrics["gates"]["material_correctness_S01"]["status"] == "FAIL"

    clean_target = _labels(synthetic_bundle, stratum="S03")[0]
    metrics, _ = _score(
        synthetic_bundle,
        predictions=_replace_results(
            synthetic_bundle,
            {
                clean_target["case_id"]: _no_answer_result(
                    clean_target["output_text"]
                )
            },
        ),
        legacy=_exact_legacy(synthetic_bundle),
    )
    assert metrics["gates"]["clean_pooled_non_regression"]["status"] == "FAIL"

    metrics, _ = _score(
        synthetic_bundle, legacy=_exact_legacy(synthetic_bundle)
    )
    assert metrics["gates"]["critical_strict_improvement"]["status"] == "FAIL"


def test_invalid_schema_returns_invalid_without_dropping(synthetic_bundle):
    predictions = deepcopy(synthetic_bundle["predictions"])
    predictions[0]["parser_result"]["extra"] = "invalid"
    metrics, failures = core.score_locked_evaluation(
        synthetic_bundle["labels"],
        predictions,
        synthetic_bundle["legacy"],
        synthetic_bundle["gates"],
    )
    assert metrics["status"] == "INVALID"
    gates = core.load_acceptance_gates(synthetic_bundle["gates"])
    assert set(metrics["gates"]) == set(core.mandatory_gate_specs(gates))
    core.validate_metrics_artifact(metrics, gates)
    assert failures == []


@pytest.mark.parametrize(
    "invariant",
    (
        "ten_per_stratum",
        "global_typed_support",
        "ambiguity_topology",
        "no_answer_topology",
        "five_five_correctness",
        "critical_support",
    ),
)
def test_all_frozen_label_support_invariants_are_differentially_invalid(
    synthetic_bundle, invariant
):
    labels = deepcopy(synthetic_bundle["labels"])
    if invariant == "ten_per_stratum":
        next(item for item in labels if item["stratum"] == "S01")[
            "stratum"
        ] = "S02"
    elif invariant == "global_typed_support":
        next(
            item
            for item in labels
            if item["expected_answer_presence"] == "present"
        )["expected_answer_presence"] = "ambiguous"
    elif invariant == "ambiguity_topology":
        ambiguous = next(item for item in labels if item["stratum"] == "S11")
        present = next(item for item in labels if item["stratum"] == "S01")
        ambiguous["expected_answer_presence"] = "present"
        present["expected_answer_presence"] = "ambiguous"
    elif invariant == "no_answer_topology":
        absent = next(item for item in labels if item["stratum"] == "S09")
        present = next(item for item in labels if item["stratum"] == "S01")
        absent["expected_answer_presence"] = "present"
        present["expected_answer_presence"] = "no_answer"
    elif invariant == "five_five_correctness":
        target = next(
            item
            for item in labels
            if item["stratum"] == "S01"
            and item["expected_correctness"] is True
        )
        target["expected_correctness"] = False
    else:
        next(item for item in labels if item["critical_case"] is True)[
            "critical_case"
        ] = False

    with pytest.raises(synthetic_bundle["frozen"].ValidationSetError):
        synthetic_bundle["frozen"]._validate_locked_label_support(labels)
    frozen_predictions = deepcopy(synthetic_bundle["predictions"])
    frozen_seal = synthetic_bundle["frozen"].build_prediction_seal(
        frozen_predictions,
        synthetic_bundle["locked_inputs"],
        implementation_commit=IMPLEMENTATION,
        sealed_utc=TIMESTAMP,
    )
    frozen_legacy = [
        {"case_id": item["case_id"], "legacy_result": item["legacy_result"]}
        for item in synthetic_bundle["legacy"]
    ]
    frozen_metrics = synthetic_bundle["frozen"].score_validation_set(
        labels,
        frozen_predictions,
        frozen_legacy,
        locked_inputs=synthetic_bundle["locked_inputs"],
        prediction_seal=frozen_seal,
        implementation_commit=IMPLEMENTATION,
    )
    assert frozen_metrics["status"] == "INVALID"
    metrics, failures = core.score_locked_evaluation(
        labels,
        synthetic_bundle["predictions"],
        synthetic_bundle["legacy"],
        synthetic_bundle["gates"],
    )
    assert metrics["status"] == "INVALID"
    gates = core.load_acceptance_gates(synthetic_bundle["gates"])
    assert set(metrics["gates"]) == set(core.mandatory_gate_specs(gates))
    core.validate_metrics_artifact(metrics, gates)
    assert failures == []


def _state_chain_until(
    target: str,
    *,
    artifact_overrides: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    frozen = core._load_frozen_validation()
    overrides = {} if artifact_overrides is None else dict(artifact_overrides)
    visibility = ["public-synthetic"]
    receipts: list[dict[str, Any]] = []
    previous = None
    lock_hash = None
    for index, state in enumerate(core.HOLDOUT_STATE_SEQUENCE):
        receipt_timestamp = f"2026-07-20T05:45:{index:02d}Z"
        manifests = (
            {} if previous is None else deepcopy(previous["artifact_manifest_hashes"])
        )
        for key in core.STATE_AUTHORIZED_ARTIFACT_BINDINGS[state]:
            if key == "implementation_manifest":
                manifests[key] = core.sha256_bytes(
                    IMPLEMENTATION_MANIFEST_BYTES
                )
            elif key == "authorization_manifest":
                authorization_manifest = core.build_authorization_manifest(
                    receipts[-1],
                    _authorization_lock(receipts),
                    IMPLEMENTATION_MANIFEST_BYTES,
                    RUNTIME_CONFIG_BYTES,
                    locked_input_source_binding=(
                        _synthetic_locked_input_source_binding(receipts[-1])
                    ),
                    state_prefix=core.evaluation_prefixes(
                        PARENT, AUTHORIZATION
                    )["state"],
                    actor="synthetic-actor",
                    created_utc=receipt_timestamp,
                )
                manifests[key] = core.sha256_bytes(
                    core.canonical_json_bytes(authorization_manifest)
                )
            else:
                manifests[key] = overrides.get(
                    key, hashlib.sha256(key.encode("ascii")).hexdigest()
                )
        implementation_bound = index >= core.HOLDOUT_STATE_SEQUENCE.index(
            "IMPLEMENTATION_FROZEN"
        )
        receipt = {
            "schema_version": core.STATE_RECEIPT_SCHEMA_VERSION,
            "authorization_id": AUTHORIZATION,
            "state": state,
            "previous_state": None if previous is None else previous["state"],
            "previous_receipt_sha256": (
                None if previous is None else core.state_receipt_sha256(previous)
            ),
            "timestamp_utc": receipt_timestamp,
            "execution_id": f"execution-{state.casefold()}",
            "actor": "synthetic-actor",
            "visibility": visibility,
            "registered_parent_prefix": PARENT,
            "protocol_commit": core.FROZEN_PROTOCOL_COMMIT,
            "protocol_bundle_sha256": core.FROZEN_PROTOCOL_BUNDLE_SHA256,
            "acceptance_gates_sha256": core.FROZEN_ACCEPTANCE_GATE_SHA256,
            "implementation_commit": IMPLEMENTATION if implementation_bound else None,
            "image_digest": IMAGE_DIGEST if implementation_bound else None,
            "config_sha256": CONFIG_SHA256 if implementation_bound else None,
            "authorization_lock_sha256": (
                (lock_hash or "1" * 64) if implementation_bound else None
            ),
            "artifact_manifest_hashes": manifests,
            "retry_kind": "none",
            "outcome": "PASS" if state == "CLOSED" else None,
            "holdout_spent": index
            >= core.HOLDOUT_STATE_SEQUENCE.index("INPUTS_READ"),
            "holdout_retired": state == "CLOSED",
        }
        if state == "IMPLEMENTATION_FROZEN":
            sealed = receipts[core.HOLDOUT_STATE_SEQUENCE.index("SEALED")]
            lock = frozen.build_authorization_lock(
                sealed, receipt, IMPLEMENTATION_MANIFEST_BYTES
            )
            lock_hash = frozen.authorization_lock_sha256(lock)
            receipt["authorization_lock_sha256"] = lock_hash
        receipts.append(receipt)
        previous = receipt
        if state == target:
            break
    return receipts


def _authorization_lock(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    frozen = core._load_frozen_validation()
    sealed = receipts[core.HOLDOUT_STATE_SEQUENCE.index("SEALED")]
    implementation = receipts[
        core.HOLDOUT_STATE_SEQUENCE.index("IMPLEMENTATION_FROZEN")
    ]
    return frozen.build_authorization_lock(
        sealed, implementation, IMPLEMENTATION_MANIFEST_BYTES
    )


def _fake_blob_etag(data: bytes) -> str:
    return '"' + hashlib.sha256(data).hexdigest()[:24] + '"'


def _locked_input_reservation_bytes() -> bytes:
    return core.canonical_json_bytes(
        {
            "schema_version": (
                core._load_frozen_validation().RESERVATION_SCHEMA_VERSION
            ),
            "leaf": "locked-inputs",
            "parent_prefix": PARENT,
            "created_utc": TIMESTAMP,
            "private_nonce": "private-nonce-locked-inputs-0001",
        }
    )


def _locked_input_private_nonce_sha256() -> str:
    return core.sha256_bytes(b"private-nonce-locked-inputs-0001")


def _synthetic_locked_input_source_binding(
    implementation_receipt: Mapping[str, Any],
) -> dict[str, str]:
    reservation = _locked_input_reservation_bytes()
    manifest_sha256 = implementation_receipt["artifact_manifest_hashes"][
        "locked_inputs_manifest"
    ]
    return {
        "locked_input_reservation_blob": (
            f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
        ),
        "locked_input_reservation_sha256": core.sha256_bytes(reservation),
        "locked_input_private_nonce_sha256": (
            _locked_input_private_nonce_sha256()
        ),
        "locked_input_reservation_etag": _fake_blob_etag(reservation),
        "locked_input_manifest_blob": (
            f"{PARENT}/locked-inputs/locked_inputs_manifest.json"
        ),
        "locked_input_manifest_sha256": manifest_sha256,
        "locked_input_manifest_etag": f'"{manifest_sha256[:24]}"',
        "locked_manifest_sha256": implementation_receipt[
            "artifact_manifest_hashes"
        ]["locked_manifest"],
    }


def _authorization_manifest_bytes(
    receipts: list[dict[str, Any]],
) -> bytes:
    implementation = receipts[
        core.HOLDOUT_STATE_SEQUENCE.index("IMPLEMENTATION_FROZEN")
    ]
    unseal = receipts[
        core.HOLDOUT_STATE_SEQUENCE.index("UNSEAL_AUTHORIZED")
    ]
    manifest = core.build_authorization_manifest(
        implementation,
        _authorization_lock(receipts),
        IMPLEMENTATION_MANIFEST_BYTES,
        RUNTIME_CONFIG_BYTES,
        locked_input_source_binding=_synthetic_locked_input_source_binding(
            implementation
        ),
        state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"],
        actor=unseal["actor"],
        created_utc=unseal["timestamp_utc"],
    )
    data = core.canonical_json_bytes(manifest)
    assert core.sha256_bytes(data) == unseal["artifact_manifest_hashes"][
        "authorization_manifest"
    ]
    return data


def _advance_state(
    receipts: list[dict[str, Any]],
    state: str,
    digest: str,
    *,
    outcome: str | None = None,
) -> dict[str, Any]:
    lock = _authorization_lock(receipts)
    receipt = core.build_next_state_receipt(
        receipts[-1],
        state=state,
        artifact_manifest_sha256=digest,
        timestamp_utc=TIMESTAMP,
        execution_id=f"execution-{state.casefold()}",
        actor="synthetic-actor",
        visibility=["public-synthetic"],
        outcome=outcome,
        authorization_lock=lock,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    receipts.append(receipt)
    return receipt


@pytest.mark.parametrize("outcome", ("PASS", "FAIL", "INVALID"))
def test_pass_fail_invalid_all_close_and_retire(outcome):
    if outcome == "PASS":
        gate = core.metric_record(
            1,
            1,
            comparison=">=",
            threshold=core.Fraction(1),
            mandatory=True,
        )
    elif outcome == "FAIL":
        gate = core.metric_record(
            0,
            1,
            comparison=">=",
            threshold=core.Fraction(1),
            mandatory=True,
        )
    else:
        gate = core.metric_record(
            None,
            None,
            comparison=">=",
            threshold=core.Fraction(1),
            mandatory=True,
        )
    metrics = {"status": outcome, "gates": {"synthetic": gate}}
    receipts = _state_chain_until("SCORES_VERIFIED")
    decision = core.build_decision(
        metrics,
        authorization_id=AUTHORIZATION,
        registered_parent_prefix=PARENT,
        authorization_lock_sha256=receipts[-1][
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=receipts[-1][
            "artifact_manifest_hashes"
        ]["authorization_manifest"],
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_seal_sha256="1" * 64,
        prediction_manifest_sha256=hashlib.sha256(
            b"predictions_manifest"
        ).hexdigest(),
        prediction_request_manifest_sha256="2" * 64,
        locked_manifest_sha256=hashlib.sha256(b"locked_manifest").hexdigest(),
        input_manifest_sha256="3" * 64,
        locked_input_sha256="4" * 64,
        labels_manifest_sha256=hashlib.sha256(b"labels_manifest").hexdigest(),
        labels_sha256="5" * 64,
        labels_open_transaction_sha256="6" * 64,
        scores_prefix=core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        scoring_retry_kind="none",
        scoring_execution_id="synthetic-scoring",
        scoring_actor="synthetic-actor",
        stage_e_visibility_sha256="8" * 64,
        retry_receipt_sha256=None,
        scoring_ledger_sha256=SCORING_LEDGER_SHA256,
        scoring_ledger_size=SCORING_LEDGER_SIZE,
        scoring_ledger_etag=SCORING_LEDGER_ETAG,
        case_universe_sha256="7" * 64,
        row_count=120,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        decided_utc=TIMESTAMP,
    )
    retirement = core.build_retirement_record(
        decision,
        authorization_id=AUTHORIZATION,
        retired_utc=TIMESTAMP,
    )
    closure = core.build_closure_manifest(
        metrics,
        decision,
        retirement,
        scores_manifest_sha256=receipts[-1]["artifact_manifest_hashes"][
            "scores_manifest"
        ],
        created_utc=TIMESTAMP,
    )
    closed = core.build_next_state_receipt(
        receipts[-1],
        state="CLOSED",
        artifact_manifest_sha256=core.sha256_bytes(core.canonical_json_bytes(closure)),
        timestamp_utc=TIMESTAMP,
        execution_id=f"close-{outcome.casefold()}",
        actor="synthetic-actor",
        visibility=["public-synthetic"],
        outcome=outcome,
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    receipts.append(closed)
    assert core.validate_state_receipt_chain(
        receipts,
        require_closed=True,
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )["holdout_retired"]
    assert core.validate_state_receipt_graph(
        receipts,
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        authorization_manifest_bytes=_authorization_manifest_bytes(receipts),
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"],
    )["state"] == "CLOSED"
    core.validate_closed_outcome(closed, metrics, decision, retirement, closure)
    forged_decision = deepcopy(decision)
    forged_decision["manual_override"] = 0
    with pytest.raises(core.LockedEvaluationError):
        core.validate_closed_outcome(
            closed, metrics, forged_decision, retirement, closure
        )
    forged_retirement = deepcopy(retirement)
    forged_retirement["formal_evaluation_count"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_closed_outcome(
            closed, metrics, decision, forged_retirement, closure
        )
    forged_closure = deepcopy(closure)
    forged_closure["holdout_spent"] = 1
    with pytest.raises(core.LockedEvaluationError):
        core.validate_closed_outcome(
            closed, metrics, decision, retirement, forged_closure
        )
    with pytest.raises(core.LockedEvaluationError):
        core.validate_state_transition(
            closed,
            {**closed, "previous_receipt_sha256": core.state_receipt_sha256(closed)},
        )


def test_state_chain_rejects_skip_hash_change_and_recompute():
    receipts = _state_chain_until("PREDICTIONS_VERIFIED")
    broken = deepcopy(receipts)
    broken[-1]["previous_receipt_sha256"] = "9" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_state_receipt_chain(
            broken,
            authorization_lock=_authorization_lock(receipts),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )
    skipped = receipts[:-1]
    with pytest.raises(core.LockedEvaluationError):
        core.build_next_state_receipt(
            skipped[-1],
            state="LABELS_READ",
            artifact_manifest_sha256="8" * 64,
            timestamp_utc=TIMESTAMP,
            execution_id="skip",
            actor="synthetic",
            visibility=[],
        )


class _FakeDownload:
    def __init__(self, service, name):
        self.service = service
        self.name = name

    def readall(self):
        self.service.events.append(("download", self.name))
        return self.service.data[self.name]


class _FakeCreateConflict(RuntimeError):
    status_code = 409
    error_code = "BlobAlreadyExists"


class _FakeBlob:
    def __init__(self, service, name):
        self.service = service
        self.name = name

    def upload_blob(self, data, overwrite):
        self.service.events.append(("upload", self.name, overwrite))
        fault = self.service.upload_faults.pop(self.name, None)
        if fault == "pre_create":
            raise RuntimeError("synthetic failure before create")
        if self.name in self.service.data and not overwrite:
            raise _FakeCreateConflict("already exists")
        stored = (
            bytes(data) + b" "
            if fault == "tampered_success"
            else bytes(data)
        )
        self.service.data[self.name] = stored
        self.service.etags[self.name] = (
            '"' + hashlib.sha256(stored).hexdigest()[:24] + '"'
        )
        if fault in {"ambiguous_success", "tampered_success"}:
            raise RuntimeError("synthetic ambiguous create response")

    def download_blob(self):
        return _FakeDownload(self.service, self.name)

    def get_blob_properties(self):
        return SimpleNamespace(
            size=len(self.service.data[self.name]),
            etag=self.service.etags[self.name],
        )


class _FakeContainer:
    def __init__(self, service):
        self.service = service

    def list_blobs(self, name_starts_with):
        self.service.events.append(("list", name_starts_with))
        return _FakeListing([
            SimpleNamespace(name=name)
            for name in sorted(self.service.data)
            if name.startswith(name_starts_with)
        ])


class _FakeListing:
    def __init__(self, items):
        self.items = items

    def by_page(self, continuation_token=None):
        assert continuation_token is None
        return _FakePage(self.items)


class _FakePage:
    continuation_token = None

    def __init__(self, items):
        self.items = items
        self.returned = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.returned:
            raise StopIteration
        self.returned = True
        return self.items


class _FakeService:
    def __init__(self):
        self.data: dict[str, bytes] = {}
        self.etags: dict[str, str] = {}
        self.events: list[tuple] = []
        self.upload_faults: dict[str, str] = {}

    def preload(self, name: str, data: bytes):
        self.data[name] = data
        self.etags[name] = '"' + hashlib.sha256(data).hexdigest()[:24] + '"'

    def get_blob_client(self, container, blob):
        return _FakeBlob(self, blob)

    def get_container_client(self, container):
        return _FakeContainer(self)


def _source_manifest_bytes(
    *,
    kind: str,
    relative_path: str,
    payload: bytes,
    ordered_case_ids: list[str],
) -> bytes:
    frozen = core._load_frozen_validation()
    names = frozen.REGISTERED_LEAF_MEMBERS[kind][:-1]
    files = {
        f"{kind}/{name}": (
            payload
            if f"{kind}/{name}" == relative_path
            else _locked_input_reservation_bytes()
            if kind == "locked-inputs"
            and name == ".locked_inputs_reservation.json"
            else core.canonical_json_bytes({"synthetic": True})
        )
        for name in names
    }
    reservation_path = f"{kind}/{names[0]}"
    manifest = frozen.build_manifest(
        manifest_kind=kind,
        project_root=ROOT,
        created_utc=TIMESTAMP,
        parent_prefix=PARENT,
        ordered_case_ids=ordered_case_ids,
        counts=(
            {"cases": len(ordered_case_ids)}
            if kind == "locked-inputs"
            else {"cases": len(ordered_case_ids)}
        ),
        schemas=(
            {"locked_inputs": core.LOCKED_INPUT_SCHEMA_VERSION}
            if kind == "locked-inputs"
            else {"final_labels": core.FINAL_LABEL_SCHEMA_VERSION}
        ),
        files=files,
        reservation_sha256=core.sha256_bytes(files[reservation_path]),
        review_seals=[],
        arbitration={"stage1": 0, "stage2": 0, "unresolved": 0},
        feature_counts={},
        visibility_ledger_sha256="a" * 64,
        source_prefixes=["independent/source"],
        private_nonce=f"private-nonce-{kind}-0001",
    )
    return core.canonical_json_bytes(manifest)


def test_synthetic_end_to_end_stage_p_stage_e_and_verify_only(
    synthetic_bundle, _isolated_stage_e_modules, monkeypatch
):
    service = _FakeService()
    authenticated_service = [service]
    monkeypatch.setattr(
        bootstrap, "_git_source_bindings", lambda _commit: _runtime_source_bindings()
    )
    monkeypatch.setattr(
        core, "validate_private_endpoint_resolution", lambda *_args: None
    )
    monkeypatch.setattr(
        core, "create_blob_service", lambda _endpoint: authenticated_service[0]
    )

    def authenticate_persisted(active_service):
        authenticated_service[0] = active_service
        return bootstrap._authenticate_persisted(
            core,
            runtime=core.parse_json_strict(
                RUNTIME_CONFIG_BYTES, "runtime configuration"
            ),
            runtime_bytes=RUNTIME_CONFIG_BYTES,
            implementation=core.validate_implementation_manifest(
                IMPLEMENTATION_MANIFEST_BYTES
            ),
            implementation_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            runtime_sha256=CONFIG_SHA256,
            implementation_sha256=core.sha256_bytes(
                IMPLEMENTATION_MANIFEST_BYTES
            ),
            image_binding_bytes=IMAGE_BINDING_BYTES,
            image_binding_sha256=IMAGE_BINDING_SHA256,
            helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
            final_state="LATEST",
            prior_receipt_sha256=None,
            authorization_lock_sha256=authorization_lock_sha256,
            authorization_manifest_sha256=stage_p_args.authorization_manifest_sha256,
        )

    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    locked_input_bytes = core.canonical_jsonl_bytes(
        synthetic_bundle["locked_inputs"]
    )
    label_bytes = core.canonical_jsonl_bytes(synthetic_bundle["labels"])
    ordered_ids = [item["case_id"] for item in synthetic_bundle["locked_inputs"]]
    input_manifest_bytes = _source_manifest_bytes(
        kind="locked-inputs",
        relative_path="locked-inputs/locked_inputs.jsonl",
        payload=locked_input_bytes,
        ordered_case_ids=ordered_ids,
    )
    labels_manifest_bytes = _source_manifest_bytes(
        kind="locked-labels",
        relative_path="locked-labels/locked_reference_labels.jsonl",
        payload=label_bytes,
        ordered_case_ids=ordered_ids,
    )
    locked_input_blob = f"{PARENT}/locked-inputs/locked_inputs.jsonl"
    input_manifest_blob = (
        f"{PARENT}/locked-inputs/locked_inputs_manifest.json"
    )
    input_reservation_blob = (
        f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
    )
    labels_blob = f"{PARENT}/locked-labels/locked_reference_labels.jsonl"
    labels_manifest_blob = f"{PARENT}/locked-labels/locked_labels_manifest.json"
    for name, data in (
        (
            input_reservation_blob,
            _locked_input_reservation_bytes(),
        ),
        (locked_input_blob, locked_input_bytes),
        (input_manifest_blob, input_manifest_bytes),
        (labels_blob, label_bytes),
        (labels_manifest_blob, labels_manifest_bytes),
    ):
        service.preload(name, data)
    for name in core._load_frozen_validation().expected_parent_membership(
        PARENT
    ):
        if name not in service.data:
            service.preload(
                name, core.canonical_json_bytes({"synthetic": True})
            )
    frozen = core._load_frozen_validation()
    overall_relative = "manifests/locked_manifest.json"
    overall_manifest = frozen.build_manifest(
        manifest_kind="manifests",
        project_root=ROOT,
        created_utc=TIMESTAMP,
        parent_prefix=PARENT,
        ordered_case_ids=ordered_ids,
        counts={"cases": len(ordered_ids)},
        schemas={},
        files={
            relative: service.data[f"{PARENT}/{relative}"]
            for leaf, names in frozen.REGISTERED_LEAF_MEMBERS.items()
            for name in names
            for relative in (f"{leaf}/{name}",)
            if relative != overall_relative
        },
        reservation_sha256=core.sha256_bytes(
            service.data[
                f"{PARENT}/manifests/.locked_manifest_reservation.json"
            ]
        ),
        review_seals=[],
        arbitration={"stage1": 0, "stage2": 0, "unresolved": 0},
        feature_counts={},
        visibility_ledger_sha256="a" * 64,
        source_prefixes=["independent/source"],
        private_nonce="private-nonce-overall-0001",
    )
    overall_manifest_bytes = core.canonical_json_bytes(overall_manifest)
    service.preload(f"{PARENT}/{overall_relative}", overall_manifest_bytes)

    receipts = _state_chain_until(
        "UNSEAL_AUTHORIZED",
        artifact_overrides={
            "locked_inputs_manifest": core.sha256_bytes(input_manifest_bytes),
            "locked_labels_manifest": core.sha256_bytes(labels_manifest_bytes),
            "locked_manifest": core.sha256_bytes(overall_manifest_bytes),
        },
    )
    for receipt in receipts:
        service.preload(
            (
                f"{prefixes['state']}/"
                f"{core.STATE_RECEIPT_FILENAMES[receipt['state']]}"
            ),
            core.canonical_json_bytes(receipt),
        )
    authorization_lock = _authorization_lock(receipts)
    authorization_lock_sha256 = core.authorization_lock_sha256(
        authorization_lock
    )
    service.preload(
        f"{prefixes['state']}/{core.IMPLEMENTATION_MANIFEST_FILENAME}",
        IMPLEMENTATION_MANIFEST_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.RUNTIME_CONFIG_FILENAME}",
        RUNTIME_CONFIG_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.AUTHORIZATION_MANIFEST_FILENAME}",
        _authorization_manifest_bytes(receipts),
    )
    service.preload(
        core.authorization_lock_blob_name(authorization_lock),
        core.canonical_json_bytes(authorization_lock),
    )
    unseal = receipts[-1]
    v2_by_text = {
        label["output_text"]: prediction["parser_result"]
        for label, prediction in zip(
            synthetic_bundle["labels"],
            synthetic_bundle["predictions"],
            strict=True,
        )
    }
    legacy_by_text = {
        locked["output_text"]: legacy["legacy_result"]
        for locked, legacy in zip(
            synthetic_bundle["locked_inputs"],
            synthetic_bundle["legacy"],
            strict=True,
        )
    }

    @dataclasses.dataclass
    class LegacyResult:
        parsed_answer: str | None
        parse_valid: bool
        parse_error_type: str | None
        parse_ambiguous: bool
        parse_strategy: str | None
        candidate_answers: list[str] | None
        answer_format_warning: str | None

    stage_p_parser_calls = {"v2": 0, "legacy": 0}

    def parse_v2(request):
        stage_p_parser_calls["v2"] += 1
        return deepcopy(v2_by_text[request["output_text"]])

    def parse_legacy(text):
        stage_p_parser_calls["legacy"] += 1
        return LegacyResult(**deepcopy(legacy_by_text[text]))

    stage_p_args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        locked_input_blob=locked_input_blob,
        locked_input_sha256=core.sha256_bytes(locked_input_bytes),
        locked_input_manifest_blob=input_manifest_blob,
        locked_input_manifest_sha256=core.sha256_bytes(input_manifest_bytes),
        predictions_prefix=prefixes["predictions"],
        state_prefix=prefixes["state"],
        visibility_prefix=prefixes["visibility"],
        prior_state_receipt_blob=(
            f"{prefixes['state']}/"
            f"{core.STATE_RECEIPT_FILENAMES['UNSEAL_AUTHORIZED']}"
        ),
        prior_state_receipt_sha256=core.state_receipt_sha256(unseal),
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        authorization_lock_sha256=authorization_lock_sha256,
        authorization_manifest_sha256=core.sha256_bytes(
            _authorization_manifest_bytes(receipts)
        ),
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        retry_kind="none",
        execution_id="synthetic-stage-p",
        actor="synthetic-actor",
    )
    injected = f"{PARENT}/locked-inputs/expected_labels.jsonl"
    service.preload(injected, b'{"secret":"locked"}\n')
    with pytest.raises(core.LockedEvaluationError, match="membership"):
        runner.run_stage_p(
            stage_p_args,
            service=service,
            core=core,
            parser_functions=(parse_v2, parse_legacy),
            now=lambda: TIMESTAMP,
        )
    del service.data[injected]
    del service.etags[injected]
    parent_injected = f"{PARENT}/reports/unregistered-parent-member.json"
    service.preload(parent_injected, b"{}\n")
    input_reads_before_parent_check = service.events.count(
        ("download", locked_input_blob)
    )
    with pytest.raises(core.LockedEvaluationError, match="parent membership"):
        runner.run_stage_p(
            stage_p_args,
            service=service,
            core=core,
            parser_functions=(parse_v2, parse_legacy),
            now=lambda: TIMESTAMP,
        )
    assert service.events.count(
        ("download", locked_input_blob)
    ) == input_reads_before_parent_check
    del service.data[parent_injected]
    del service.etags[parent_injected]
    input_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    spent_blob = (
        f"{prefixes['state']}/{core.SPENT_INCOMPLETE_FILENAME}"
    )
    for receipt_fault in ("pre_create", "tampered_success"):
        receipt_failure_service = deepcopy(service)
        receipt_failure_service.upload_faults[input_receipt_blob] = receipt_fault
        parser_calls_before_receipt_failure = dict(stage_p_parser_calls)
        input_reads_before_receipt_failure = (
            receipt_failure_service.events.count(("download", locked_input_blob))
        )
        with pytest.raises(
            core.LockedEvaluationError, match="not proven durable"
        ):
            runner.run_stage_p(
                stage_p_args,
                service=receipt_failure_service,
                core=core,
                parser_functions=(parse_v2, parse_legacy),
                now=lambda: TIMESTAMP,
            )
        assert spent_blob not in receipt_failure_service.data
        assert stage_p_parser_calls == parser_calls_before_receipt_failure
        assert receipt_failure_service.events.count(
            ("download", locked_input_blob)
        ) == input_reads_before_receipt_failure
        if receipt_fault == "pre_create":
            assert input_receipt_blob not in receipt_failure_service.data
        else:
            assert input_receipt_blob in receipt_failure_service.data

    pre_input_retry_service = deepcopy(service)
    primary_stage_p_visibility = core.build_visibility_record(
        stage="P",
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        visibility_prefix=prefixes["visibility"],
        execution_id="pre-retry-stage-p-attempt",
        actor="synthetic-actor",
        created_utc=TIMESTAMP,
    )
    stage_p_visibility_blob = (
        f"{prefixes['visibility']}/stage_p_visibility.json"
    )
    core.persist_singleton(
        pre_input_retry_service,
        stage_p_args.container,
        stage_p_visibility_blob,
        core.canonical_json_bytes(primary_stage_p_visibility),
    )
    primary_prediction_reservation = core.build_reservation(
        leaf="predictions",
        prefix=prefixes["predictions"],
        authorization_id=AUTHORIZATION,
        created_utc="2026-07-20T05:45:19Z",
        nonce="pre-input-reusable-reservation",
    )
    prediction_reservation_blob = (
        f"{prefixes['predictions']}/{core.PREDICTION_MEMBER_NAMES[0]}"
    )
    core.persist_singleton(
        pre_input_retry_service,
        stage_p_args.container,
        prediction_reservation_blob,
        core.canonical_json_bytes(primary_prediction_reservation),
    )
    pre_input_retry_args = deepcopy(stage_p_args)
    pre_input_retry_args.retry_kind = "infrastructure_pre_input"
    pre_input_retry_args.execution_id = "synthetic-stage-p-retry"
    retry_prefixes = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "P",
        pre_input_retry_args.retry_kind,
        pre_input_retry_args.execution_id,
    )
    pre_input_retry_args.predictions_prefix = retry_prefixes["predictions"]
    pre_input_retry_args.visibility_prefix = retry_prefixes["visibility"]
    abandoned_blob = (
        f"{retry_prefixes['visibility']}/{core.ABANDONED_ATTEMPT_FILENAME}"
    )
    retry_visibility_blob = (
        f"{retry_prefixes['visibility']}/stage_p_visibility.json"
    )
    retry_reservation = core.build_reservation(
        leaf="predictions",
        prefix=retry_prefixes["predictions"],
        authorization_id=AUTHORIZATION,
        created_utc="2026-07-20T05:45:19Z",
        nonce="current-retry-reservation",
        parent_prefix=PARENT,
        stage="P",
        retry_kind=pre_input_retry_args.retry_kind,
        execution_id=pre_input_retry_args.execution_id,
    )
    retry_reservation_blob = (
        f"{retry_prefixes['predictions']}/{core.PREDICTION_MEMBER_NAMES[0]}"
    )
    core.persist_singleton(
        pre_input_retry_service,
        stage_p_args.container,
        retry_reservation_blob,
        core.canonical_json_bytes(retry_reservation),
    )
    root_retry_args = deepcopy(pre_input_retry_args)
    root_retry_args.predictions_prefix = prefixes["predictions"]
    root_retry_args.visibility_prefix = prefixes["visibility"]
    retry_parser_calls_before_rejections = dict(stage_p_parser_calls)
    with pytest.raises(core.LockedEvaluationError, match="attempt prefix"):
        runner.run_stage_p(
            root_retry_args,
            service=pre_input_retry_service,
            core=core,
            parser_functions=(parse_v2, parse_legacy),
            now=lambda: "2026-07-20T05:45:25Z",
        )
    assert stage_p_parser_calls == retry_parser_calls_before_rejections

    old_visibility_service = deepcopy(pre_input_retry_service)
    old_visibility_service.preload(
        retry_visibility_blob,
        old_visibility_service.data[stage_p_visibility_blob],
    )
    with pytest.raises(core.LockedEvaluationError, match="visibility membership"):
        runner.run_stage_p(
            pre_input_retry_args,
            service=old_visibility_service,
            core=core,
            parser_functions=(parse_v2, parse_legacy),
            now=lambda: "2026-07-20T05:45:25Z",
        )

    nested_extra_service = deepcopy(pre_input_retry_service)
    nested_extra_service.preload(
        f"{retry_prefixes['predictions']}/unexpected.json", b"{}\n"
    )
    with pytest.raises(core.LockedEvaluationError, match="initial set"):
        runner.run_stage_p(
            pre_input_retry_args,
            service=nested_extra_service,
            core=core,
            parser_functions=(parse_v2, parse_legacy),
            now=lambda: "2026-07-20T05:45:25Z",
        )

    primary_metadata = [
        {
            "blob_name": name,
            "size": len(pre_input_retry_service.data[name]),
            "sha256": core.sha256_bytes(pre_input_retry_service.data[name]),
            "etag": pre_input_retry_service.etags[name],
        }
        for name in sorted(
            (stage_p_visibility_blob, prediction_reservation_blob)
        )
    ]
    valid_abandoned = core.build_abandoned_attempt_record(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        prior_stage="P",
        prior_retry_kind="none",
        prior_execution_id=primary_stage_p_visibility["execution_id"],
        prior_actor=primary_stage_p_visibility["actor"],
        abandoned_members=primary_metadata,
        current_retry_kind=pre_input_retry_args.retry_kind,
        current_execution_id=pre_input_retry_args.execution_id,
        current_actor=pre_input_retry_args.actor,
        prior_state_receipt_sha256=core.state_receipt_sha256(unseal),
        created_utc="2026-07-20T05:45:25Z",
    )
    tampered_metadata = deepcopy(primary_metadata)
    tampered_metadata[0]["sha256"] = "9" * 64
    tampered_abandoned = core.build_abandoned_attempt_record(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        prior_stage="P",
        prior_retry_kind="none",
        prior_execution_id=primary_stage_p_visibility["execution_id"],
        prior_actor=primary_stage_p_visibility["actor"],
        abandoned_members=tampered_metadata,
        current_retry_kind=pre_input_retry_args.retry_kind,
        current_execution_id=pre_input_retry_args.execution_id,
        current_actor=pre_input_retry_args.actor,
        prior_state_receipt_sha256=core.state_receipt_sha256(unseal),
        created_utc="2026-07-20T05:45:25Z",
    )
    missing_metadata_abandoned = deepcopy(valid_abandoned)
    missing_metadata_abandoned["abandoned_members"][0].pop("etag")
    for forged_abandoned in (
        tampered_abandoned,
        missing_metadata_abandoned,
    ):
        forged_service = deepcopy(pre_input_retry_service)
        forged_service.preload(
            abandoned_blob, core.canonical_json_bytes(forged_abandoned)
        )
        with pytest.raises(core.LockedEvaluationError, match="abandoned"):
            runner.run_stage_p(
                pre_input_retry_args,
                service=forged_service,
                core=core,
                parser_functions=(parse_v2, parse_legacy),
                now=lambda: "2026-07-20T05:45:25Z",
            )
    assert stage_p_parser_calls == retry_parser_calls_before_rejections

    retry_spent_service = deepcopy(pre_input_retry_service)
    retry_spent_parser_calls = 0

    def failing_retry_parser(_request):
        nonlocal retry_spent_parser_calls
        retry_spent_parser_calls += 1
        raise ValueError("synthetic retry parser failure")

    with pytest.raises(ValueError, match="synthetic retry parser failure"):
        runner.run_stage_p(
            pre_input_retry_args,
            service=retry_spent_service,
            core=core,
            parser_functions=(failing_retry_parser, parse_legacy),
            now=lambda: "2026-07-20T05:45:25Z",
        )
    assert retry_spent_parser_calls == 1
    retry_spent_blob = (
        f"{prefixes['state']}/{core.SPENT_INCOMPLETE_FILENAME}"
    )
    retry_spent = core.parse_json_strict(
        retry_spent_service.data[retry_spent_blob], "retry spent-incomplete"
    )
    assert retry_spent["prediction_prefix"] == retry_prefixes["predictions"]
    assert retry_spent["visibility_prefix"] == retry_prefixes["visibility"]
    assert retry_spent["retry_kind"] == "infrastructure_pre_input"
    assert retry_spent["retry_receipt_blob"] == (
        f"{prefixes['state']}/"
        f"{core.STATE_RETRY_RECEIPT_FILENAMES['infrastructure_pre_input']}"
    )
    assert retry_spent["retry_receipt_sha256"]
    assert "case_id" not in retry_spent_service.data[retry_spent_blob].decode(
        "utf-8"
    )

    primary_before_retry = {
        name: (
            pre_input_retry_service.data[name],
            pre_input_retry_service.etags[name],
        )
        for name in (stage_p_visibility_blob, prediction_reservation_blob)
    }
    retry_start = len(pre_input_retry_service.events)
    pre_input_result = runner.run_stage_p(
        pre_input_retry_args,
        service=pre_input_retry_service,
        core=core,
        parser_functions=(parse_v2, parse_legacy),
        now=lambda: "2026-07-20T05:45:25Z",
    )
    assert pre_input_result["status"] == "PREDICTIONS_VERIFIED"
    assert pre_input_result["predictions_prefix"] == retry_prefixes["predictions"]
    assert pre_input_result["visibility_prefix"] == retry_prefixes["visibility"]
    assert pre_input_result["retry_receipt_sha256"]
    assert {
        name: (
            pre_input_retry_service.data[name],
            pre_input_retry_service.etags[name],
        )
        for name in primary_before_retry
    } == primary_before_retry
    assert core.list_exact_prefix(
        pre_input_retry_service,
        stage_p_args.container,
        retry_prefixes["visibility"],
    ) == {abandoned_blob, retry_visibility_blob}
    abandoned = core.parse_json_strict(
        pre_input_retry_service.data[abandoned_blob], "abandoned retry"
    )
    retry_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RETRY_RECEIPT_FILENAMES['infrastructure_pre_input']}"
    )
    persisted_retry_receipt = core.parse_json_strict(
        pre_input_retry_service.data[retry_receipt_blob], "retry receipt"
    )
    core.validate_retry_state_receipt_provenance(
        persisted_retry_receipt,
        previous=unseal,
        abandoned_attempt_record=abandoned,
        abandoned_attempt_blob_name=abandoned_blob,
        abandoned_attempt_record_sha256=core.sha256_bytes(
            pre_input_retry_service.data[abandoned_blob]
        ),
    )
    private_reads_before_authentication = {
        blob: pre_input_retry_service.events.count(("download", blob))
        for blob in (locked_input_blob, labels_blob)
    }
    retry_prediction_authentication = authenticate_persisted(
        pre_input_retry_service
    )
    assert retry_prediction_authentication["prediction_attempt"][
        "retry_kind"
    ] == "infrastructure_pre_input"
    assert retry_prediction_authentication["prediction_attempt"][
        "predictions_prefix"
    ] == retry_prefixes["predictions"]
    assert retry_prediction_authentication["scoring_attempt"] is None
    assert {
        blob: pre_input_retry_service.events.count(("download", blob))
        for blob in (locked_input_blob, labels_blob)
    } == private_reads_before_authentication
    assert not any(
        event[0] == "upload"
        and event[1]
        in {
            stage_p_visibility_blob,
            prediction_reservation_blob,
            retry_reservation_blob,
        }
        for event in pre_input_retry_service.events[retry_start:]
    )

    retry_adoption_service = deepcopy(pre_input_retry_service)
    retry_predictions_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
    )
    del retry_adoption_service.data[retry_predictions_receipt_blob]
    del retry_adoption_service.etags[retry_predictions_receipt_blob]
    retry_adoption_parser_calls = 0

    def forbidden_retry_parser(_value):
        nonlocal retry_adoption_parser_calls
        retry_adoption_parser_calls += 1
        raise AssertionError("retry crash adoption invoked a parser")

    retry_recovery_args = deepcopy(pre_input_retry_args)
    retry_recovery_args.execution_id = "synthetic-stage-p-retry-recovery"
    retry_input_reads = retry_adoption_service.events.count(
        ("download", locked_input_blob)
    )
    retry_adoption_start = len(retry_adoption_service.events)
    retry_adopted = runner.run_stage_p(
        retry_recovery_args,
        service=retry_adoption_service,
        core=core,
        parser_functions=(forbidden_retry_parser, forbidden_retry_parser),
        now=lambda: "2026-07-20T05:45:25Z",
    )
    assert retry_adopted["crash_adopted"] is True
    assert retry_adopted["parsers_invoked"] is False
    assert retry_adoption_parser_calls == 0
    assert retry_adoption_service.events.count(
        ("download", locked_input_blob)
    ) == retry_input_reads
    assert [
        event[1]
        for event in retry_adoption_service.events[retry_adoption_start:]
        if event[0] == "upload"
    ] == [retry_predictions_receipt_blob]

    post_input_retry_args = deepcopy(pre_input_retry_args)
    post_input_retry_args.execution_id = "forbidden-post-input-retry"
    post_input_prefixes = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "P",
        post_input_retry_args.retry_kind,
        post_input_retry_args.execution_id,
    )
    post_input_retry_args.predictions_prefix = post_input_prefixes["predictions"]
    post_input_retry_args.visibility_prefix = post_input_prefixes["visibility"]
    with pytest.raises(core.LockedEvaluationError):
        runner.run_stage_p(
            post_input_retry_args,
            service=pre_input_retry_service,
            core=core,
            parser_functions=(forbidden_retry_parser, forbidden_retry_parser),
            now=lambda: "2026-07-20T05:45:25Z",
        )
    assert retry_adoption_parser_calls == 0

    spent_service = deepcopy(service)
    parser_calls = 0

    def failing_parser(_request):
        nonlocal parser_calls
        parser_calls += 1
        raise ValueError("private parser detail must be redacted")

    with pytest.raises(ValueError, match="redacted"):
        runner.run_stage_p(
            stage_p_args,
            service=spent_service,
            core=core,
            parser_functions=(failing_parser, parse_legacy),
            now=lambda: TIMESTAMP,
        )
    assert parser_calls == 1
    spent_blob = (
        f"{prefixes['state']}/{core.SPENT_INCOMPLETE_FILENAME}"
    )
    spent = core.parse_json_strict(
        spent_service.data[spent_blob], "spent-incomplete record"
    )
    assert spent["detail"] == "redacted"
    assert spent["holdout_spent"] is True
    assert spent["holdout_retired"] is False
    assert spent["parser_rerun_allowed"] is False
    assert spent["prediction_prefix"] == prefixes["predictions"]
    assert spent["visibility_prefix"] == prefixes["visibility"]
    assert spent["retry_kind"] == "none"
    assert spent["retry_receipt_blob"] is None
    assert spent["retry_receipt_sha256"] is None
    assert "case_id" not in spent_service.data[spent_blob].decode("utf-8")
    spent_bytes = spent_service.data[spent_blob]
    with pytest.raises(core.LockedEvaluationError, match="spent incomplete"):
        runner.run_stage_p(
            stage_p_args,
            service=spent_service,
            core=core,
            parser_functions=(failing_parser, parse_legacy),
            now=lambda: TIMESTAMP,
        )
    assert parser_calls == 1
    assert spent_service.data[spent_blob] == spent_bytes

    before_p = len(service.events)
    stage_p = runner.run_stage_p(
        stage_p_args,
        service=service,
        core=core,
        parser_functions=(parse_v2, parse_legacy),
        now=lambda: TIMESTAMP,
    )
    assert stage_p["status"] == "PREDICTIONS_VERIFIED"
    assert stage_p["parser_v2_prediction_count"] == 120
    assert stage_p["legacy_prediction_count"] == 120
    source_binding_fields = core._LOCKED_INPUT_SOURCE_BINDING_FIELDS
    bound_artifacts = [
        core.parse_json_strict(
            service.data[
                f"{prefixes['state']}/{core.AUTHORIZATION_MANIFEST_FILENAME}"
            ],
            "authorization manifest",
        ),
        core.parse_json_strict(
            service.data[
                f"{prefixes['predictions']}/prediction_request_manifest.json"
            ],
            "prediction request",
        ),
        core.parse_json_strict(
            service.data[f"{prefixes['predictions']}/prediction_seal.json"],
            "prediction seal",
        ),
        core.parse_json_strict(
            service.data[
                f"{prefixes['predictions']}/prediction_artifact_manifest.json"
            ],
            "prediction manifest",
        ),
    ]
    for field in source_binding_fields:
        assert all(
            artifact[field] == bound_artifacts[0][field]
            for artifact in bound_artifacts
        )
    assert not any(
        "/locked-labels/" in event[1]
        for event in service.events[before_p:]
        if len(event) > 1 and isinstance(event[1], str)
    )

    prediction_adoption_service = deepcopy(service)
    prediction_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
    )
    del prediction_adoption_service.data[prediction_receipt_blob]
    del prediction_adoption_service.etags[prediction_receipt_blob]
    input_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    persisted_input_receipt = core.parse_json_strict(
        prediction_adoption_service.data[input_receipt_blob],
        "INPUTS_READ receipt",
    )
    adoption_calls = 0

    def forbidden_reparse(_request):
        nonlocal adoption_calls
        adoption_calls += 1
        raise AssertionError("crash adoption invoked a parser")

    recovery_args = deepcopy(stage_p_args)
    recovery_args.execution_id = "synthetic-stage-p-recovery"
    prediction_manifest_blob = (
        f"{prefixes['predictions']}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    for forged_kind in ("manifest", "visibility"):
        forged_adoption_service = deepcopy(prediction_adoption_service)
        if forged_kind == "manifest":
            forged_manifest = core.parse_json_strict(
                forged_adoption_service.data[prediction_manifest_blob],
                "forged prediction manifest",
            )
            forged_manifest["config_sha256"] = "0" * 64
            forged_adoption_service.preload(
                prediction_manifest_blob,
                core.canonical_json_bytes(forged_manifest),
            )
        else:
            forged_visibility = core.parse_json_strict(
                forged_adoption_service.data[stage_p_visibility_blob],
                "forged Stage-P visibility",
            )
            forged_visibility["execution_id"] = recovery_args.execution_id
            forged_adoption_service.preload(
                stage_p_visibility_blob,
                core.canonical_json_bytes(forged_visibility),
            )
        forged_input_reads = forged_adoption_service.events.count(
            ("download", locked_input_blob)
        )
        with pytest.raises(core.LockedEvaluationError):
            runner.run_stage_p(
                recovery_args,
                service=forged_adoption_service,
                core=core,
                parser_functions=(forbidden_reparse, forbidden_reparse),
                now=lambda: TIMESTAMP,
            )
        assert prediction_receipt_blob not in forged_adoption_service.data
        assert forged_adoption_service.events.count(
            ("download", locked_input_blob)
        ) == forged_input_reads
    assert adoption_calls == 0

    pending = authenticate_persisted(prediction_adoption_service)
    assert pending["state"] == "INPUTS_READ"
    assert pending["prediction_attempt"] is None
    assert pending["scoring_attempt"] is None
    assert pending["pending_prediction_attempt"]["receipt_persisted"] is False
    assert pending["pending_prediction_attempt"][
        "execution_id"
    ] == persisted_input_receipt["execution_id"]
    assert pending["pending_prediction_attempt"][
        "expected_prediction_state_receipt_sha256"
    ] == pending["pending_prediction_attempt"][
        "prediction_state_receipt_sha256"
    ]
    for malformed in ("incomplete", "tampered", "multiple"):
        malformed_service = deepcopy(prediction_adoption_service)
        if malformed == "incomplete":
            missing_blob = (
                f"{prefixes['predictions']}/prediction_seal.json"
            )
            del malformed_service.data[missing_blob]
            del malformed_service.etags[missing_blob]
        elif malformed == "tampered":
            malformed_service.preload(
                prediction_manifest_blob,
                malformed_service.data[prediction_manifest_blob] + b" ",
            )
        else:
            malformed_service.preload(
                f"{prefixes['predictions']}/attempts/forged/member.json",
                b"{}\n",
            )
        with pytest.raises(core.LockedEvaluationError):
            authenticate_persisted(malformed_service)

    explicit_adoption_service = deepcopy(prediction_adoption_service)
    explicit_adoption_args = SimpleNamespace(
        account_url=stage_p_args.account_url,
        expected_private_endpoint_ip=["10.0.0.4"],
        container=stage_p_args.container,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        predictions_prefix=prefixes["predictions"],
        state_prefix=prefixes["state"],
        visibility_prefix=prefixes["visibility"],
        prior_state_receipt_blob=input_receipt_blob,
        prior_state_receipt_sha256=core.state_receipt_sha256(
            persisted_input_receipt
        ),
        prediction_manifest_sha256=stage_p["prediction_manifest_sha256"],
        expected_predictions_receipt_sha256=pending[
            "pending_prediction_attempt"
        ]["expected_prediction_state_receipt_sha256"],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        authorization_lock_sha256=authorization_lock_sha256,
        authorization_manifest_sha256=stage_p_args.authorization_manifest_sha256,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        retry_kind="prediction_adoption",
        producer_retry_kind="none",
        producer_execution_id=persisted_input_receipt["execution_id"],
        execution_id="synthetic-stage-p-adoption",
        actor="stage-p-adoption-runtime",
    )
    explicit_input_reads = explicit_adoption_service.events.count(
        ("download", locked_input_blob)
    )
    explicit_start = len(explicit_adoption_service.events)
    monkeypatch.setattr(
        runner,
        "_load_stage_p_parsers",
        lambda: (_ for _ in ()).throw(
            AssertionError("adopt-only execution loaded a parser")
        ),
    )
    explicit_adopted = runner.run_stage_p_adoption(
        explicit_adoption_args,
        service=explicit_adoption_service,
        core=core,
    )
    assert explicit_adopted["mode"] == "prediction_adoption"
    assert explicit_adoption_service.events.count(
        ("download", locked_input_blob)
    ) == explicit_input_reads
    assert [
        event[1]
        for event in explicit_adoption_service.events[explicit_start:]
        if event[0] == "upload"
    ] == [prediction_receipt_blob]

    adoption_input_reads = prediction_adoption_service.events.count(
        ("download", locked_input_blob)
    )
    adoption_start = len(prediction_adoption_service.events)
    adopted = runner.run_stage_p(
        recovery_args,
        service=prediction_adoption_service,
        core=core,
        parser_functions=(forbidden_reparse, forbidden_reparse),
        now=lambda: TIMESTAMP,
    )
    assert adopted["crash_adopted"] is True
    assert adopted["parsers_invoked"] is False
    assert adoption_calls == 0
    assert (
        f"{prefixes['state']}/{core.SPENT_INCOMPLETE_FILENAME}"
        not in prediction_adoption_service.data
    )
    assert prediction_adoption_service.events.count(
        ("download", locked_input_blob)
    ) == adoption_input_reads
    adopted_receipt = core.parse_json_strict(
        prediction_adoption_service.data[prediction_receipt_blob],
        "adopted prediction receipt",
    )
    assert adopted_receipt["execution_id"] == persisted_input_receipt[
        "execution_id"
    ]
    assert adopted_receipt["execution_id"] != recovery_args.execution_id
    adoption_uploads = [
        event[1]
        for event in prediction_adoption_service.events[adoption_start:]
        if event[0] == "upload"
    ]
    assert adoption_uploads == [prediction_receipt_blob]

    stage_e_args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        predictions_prefix=prefixes["predictions"],
        prediction_manifest_sha256=stage_p["prediction_manifest_sha256"],
        scores_prefix=prefixes["scores"],
        state_prefix=prefixes["state"],
        visibility_prefix=prefixes["visibility"],
        labels_blob=labels_blob,
        labels_sha256=core.sha256_bytes(label_bytes),
        labels_manifest_blob=labels_manifest_blob,
        labels_manifest_sha256=core.sha256_bytes(labels_manifest_bytes),
        prior_state_receipt_blob=(
            f"{prefixes['state']}/"
            f"{core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
        ),
        prior_state_receipt_sha256=stage_p["predictions_receipt_sha256"],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        authorization_lock_sha256=authorization_lock_sha256,
        authorization_manifest_sha256=core.sha256_bytes(
            _authorization_manifest_bytes(receipts)
        ),
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        retry_kind="none",
        execution_id="synthetic-stage-e",
        actor="synthetic-actor",
        verify_only=False,
        verification_state="CLOSED",
        scores_manifest_sha256=None,
        closed_receipt_sha256=None,
    )
    labels_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['LABELS_READ']}"
    )
    ambiguous_labels_service = deepcopy(service)
    ambiguous_labels_service.upload_faults[labels_receipt_blob] = (
        "ambiguous_success"
    )
    ambiguous_start = len(ambiguous_labels_service.events)
    ambiguous_result = finalizer.run_stage_e(
        stage_e_args,
        service=ambiguous_labels_service,
        core=core,
        now=lambda: "2026-07-20T05:45:59Z",
    )
    assert ambiguous_result["status"] == "PASS"
    ambiguous_events = ambiguous_labels_service.events[ambiguous_start:]
    assert ambiguous_events.count(("download", labels_blob)) == 1
    assert ambiguous_events.index(("download", labels_blob)) < (
        ambiguous_events.index(("upload", labels_receipt_blob, False))
    )

    missing_labels_service = deepcopy(service)
    missing_labels_service.upload_faults[labels_receipt_blob] = "pre_create"
    missing_start = len(missing_labels_service.events)
    missing_result = finalizer.run_stage_e(
        stage_e_args,
        service=missing_labels_service,
        core=core,
        now=lambda: "2026-07-20T05:45:59Z",
    )
    assert missing_result["status"] == "INVALID"
    assert missing_labels_service.events[missing_start:].count(
        ("download", labels_blob)
    ) == 1
    assert (
        f"{prefixes['state']}/{core.INVALID_CLOSURE_FILENAME}"
        in missing_labels_service.data
    )

    tampered_labels_service = deepcopy(service)
    tampered_labels_service.upload_faults[labels_receipt_blob] = (
        "tampered_success"
    )
    tampered_start = len(tampered_labels_service.events)
    with pytest.raises(
        core.LockedEvaluationError,
        match="could not reach authenticated CLOSED",
    ):
        finalizer.run_stage_e(
            stage_e_args,
            service=tampered_labels_service,
            core=core,
            now=lambda: "2026-07-20T05:45:59Z",
        )
    assert tampered_labels_service.events[tampered_start:].count(
        ("download", labels_blob)
    ) == 1

    retry_prediction_stage_e_service = deepcopy(pre_input_retry_service)
    retry_prediction_stage_e_args = deepcopy(stage_e_args)
    retry_prediction_stage_e_args.predictions_prefix = retry_prefixes[
        "predictions"
    ]
    retry_prediction_stage_e_args.prediction_manifest_sha256 = (
        pre_input_result["prediction_manifest_sha256"]
    )
    retry_prediction_stage_e_args.prior_state_receipt_sha256 = (
        pre_input_result["predictions_receipt_sha256"]
    )
    retry_prediction_stage_e_args.execution_id = (
        "synthetic-stage-e-consuming-p-retry"
    )
    retry_prediction_stage_e = finalizer.run_stage_e(
        retry_prediction_stage_e_args,
        service=retry_prediction_stage_e_service,
        core=core,
        now=lambda: "2026-07-20T05:46:00Z",
    )
    assert retry_prediction_stage_e["status"] == "PASS"
    retry_prediction_stage_e_authentication = authenticate_persisted(
        retry_prediction_stage_e_service
    )
    assert retry_prediction_stage_e_authentication["prediction_attempt"][
        "predictions_prefix"
    ] == retry_prefixes["predictions"]
    assert retry_prediction_stage_e_authentication["scoring_attempt"][
        "scores_prefix"
    ] == prefixes["scores"]
    scorer_primary_service = deepcopy(service)
    prediction_receipt = core.parse_json_strict(
        scorer_primary_service.data[
            f"{prefixes['state']}/"
            f"{core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
        ],
        "PREDICTIONS_VERIFIED receipt",
    )
    primary_visibility = core.build_visibility_record(
        stage="E",
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        visibility_prefix=prefixes["visibility"],
        execution_id="pre-retry-stage-e-attempt",
        actor="primary-synthetic-actor",
        created_utc="2026-07-20T05:46:01Z",
    )
    stage_e_visibility_blob = (
        f"{prefixes['visibility']}/stage_e_visibility.json"
    )
    primary_visibility_persistence = core.persist_singleton(
        scorer_primary_service,
        stage_e_args.container,
        stage_e_visibility_blob,
        core.canonical_json_bytes(primary_visibility),
    )
    primary_score_reservation = core.build_reservation(
        leaf="scores",
        prefix=prefixes["scores"],
        authorization_id=AUTHORIZATION,
        created_utc="2026-07-20T05:45:59Z",
        nonce="pre-label-primary-score-reservation",
        parent_prefix=PARENT,
        stage="E",
        retry_kind="none",
        execution_id="pre-retry-stage-e-attempt",
    )
    score_reservation_blob = (
        f"{prefixes['scores']}/{core.SCORE_MEMBER_NAMES[0]}"
    )
    core.persist_singleton(
        scorer_primary_service,
        stage_e_args.container,
        score_reservation_blob,
        core.canonical_json_bytes(primary_score_reservation),
    )
    persisted_prediction_manifest = scorer_primary_service.data[
        f"{prefixes['predictions']}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    ]
    stale_transaction_service = deepcopy(scorer_primary_service)
    stale_labels_transaction = core.build_labels_open_transaction(
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        state_prefix=prefixes["state"],
        scores_prefix=prefixes["scores"],
        scoring_retry_kind="none",
        retry_receipt_sha256=None,
        authorization_lock_sha256=authorization_lock_sha256,
        authorization_manifest_sha256=(
            stage_e_args.authorization_manifest_sha256
        ),
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_manifest_sha256=core.sha256_bytes(
            persisted_prediction_manifest
        ),
        prediction_seal_sha256=core.sha256_bytes(
            stale_transaction_service.data[
                f"{prefixes['predictions']}/prediction_seal.json"
            ]
        ),
        prediction_request_manifest_sha256=core.sha256_bytes(
            stale_transaction_service.data[
                f"{prefixes['predictions']}/prediction_request_manifest.json"
            ]
        ),
        input_manifest_sha256=core.sha256_bytes(input_manifest_bytes),
        locked_manifest_sha256=prediction_receipt[
            "artifact_manifest_hashes"
        ]["locked_manifest"],
        labels_manifest_sha256=core.sha256_bytes(labels_manifest_bytes),
        labels_manifest_blob_name=labels_manifest_blob,
        labels_manifest_etag=stale_transaction_service.etags[
            labels_manifest_blob
        ],
        labels_blob_name=labels_blob,
        labels_sha256=core.sha256_bytes(label_bytes),
        ordered_case_ids=ordered_ids,
        prior_receipt_sha256=core.state_receipt_sha256(
            prediction_receipt
        ),
        visibility_blob_name=stage_e_visibility_blob,
        visibility_sha256=primary_visibility_persistence["sha256"],
        visibility_etag=primary_visibility_persistence["etag"],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        execution_id="pre-retry-stage-e-attempt",
        actor="primary-synthetic-actor",
        created_utc="2026-07-20T05:46:01Z",
    )
    labels_transaction_blob = (
        f"{prefixes['state']}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    core.persist_labels_open_transaction(
        stale_transaction_service,
        stage_e_args.container,
        prefixes["state"],
        stale_labels_transaction,
    )
    pending_scoring = authenticate_persisted(stale_transaction_service)
    assert pending_scoring["state"] == "PREDICTIONS_VERIFIED"
    assert pending_scoring["scoring_attempt"] is None
    assert pending_scoring["pending_scoring_attempt"][
        "closure_required"
    ] is True
    assert pending_scoring["pending_scoring_attempt"]["retry_kind"] == "none"
    assert pending_scoring["pending_scoring_attempt"]["execution_id"] == (
        "pre-retry-stage-e-attempt"
    )
    assert pending_scoring["locked_labels_payload_read"] is False
    assert pending_scoring["score_payload_read"] is False
    for field, forged_value in (
        ("actor", "forged-stage-e-actor"),
        ("config_sha256", "f" * 64),
        ("visibility_sha256", "e" * 64),
    ):
        forged_pending_service = deepcopy(stale_transaction_service)
        forged_pending_transaction = deepcopy(stale_labels_transaction)
        forged_pending_transaction[field] = forged_value
        forged_pending_service.preload(
            labels_transaction_blob,
            core.canonical_json_bytes(forged_pending_transaction),
        )
        forged_label_reads = forged_pending_service.events.count(
            ("download", labels_blob)
        )
        with pytest.raises(core.LockedEvaluationError):
            authenticate_persisted(forged_pending_service)
        assert forged_pending_service.events.count(
            ("download", labels_blob)
        ) == forged_label_reads

    closure_only_service = deepcopy(stale_transaction_service)
    closure_only_args = deepcopy(stage_e_args)
    closure_only_args.close_invalid_only = True
    closure_only_args.verify_only = True
    closure_only_args.retry_kind = "verification_only"
    closure_only_args.scores_manifest_sha256 = None
    closure_only_args.closed_receipt_sha256 = None
    closure_only_args.execution_id = "synthetic-invalid-closure"
    closure_only_args.actor = "stage-e-invalid-closure-runtime"
    closure_only_args.producer_retry_kind = "none"
    closure_only_args.producer_execution_id = "pre-retry-stage-e-attempt"
    closure_label_reads = closure_only_service.events.count(
        ("download", labels_blob)
    )
    closure_result = finalizer.run_stage_e(
        closure_only_args,
        service=closure_only_service,
        core=core,
        now=lambda: "2026-07-20T05:46:02Z",
    )
    assert closure_result["status"] == "INVALID"
    assert closure_result["mode"] == "invalid_closure_recovery"
    assert closure_result["labels_reread"] is False
    assert closure_result["metrics_recomputed"] is False
    assert closure_only_service.events.count(("download", labels_blob)) == (
        closure_label_reads
    )
    closure_authentication = authenticate_persisted(closure_only_service)
    assert closure_authentication["state"] == "CLOSED"
    assert closure_authentication["result_status"] == "INVALID"
    assert closure_authentication["invalid_scoring_attempt"]["execution_id"] == (
        "pre-retry-stage-e-attempt"
    )

    scorer_retry_args = deepcopy(stage_e_args)
    scorer_retry_args.retry_kind = "scorer_infrastructure"
    scorer_retry_args.execution_id = "synthetic-scorer-retry"
    scorer_retry_prefixes = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "E",
        "scorer_infrastructure",
        scorer_retry_args.execution_id,
    )
    scorer_retry_args.scores_prefix = scorer_retry_prefixes["scores"]
    scorer_retry_args.visibility_prefix = scorer_retry_prefixes["visibility"]
    stale_label_reads = stale_transaction_service.events.count(
        ("download", labels_blob)
    )
    invalid_blob = (
        f"{prefixes['state']}/{core.INVALID_CLOSURE_FILENAME}"
    )
    invalid_closed_blob = (
        f"{prefixes['state']}/{core.STATE_RECEIPT_FILENAMES['CLOSED']}"
    )
    stale_transaction_service.upload_faults[invalid_blob] = "ambiguous_success"
    stale_transaction_service.upload_faults[invalid_closed_blob] = (
        "ambiguous_success"
    )
    invalid_result = finalizer.run_stage_e(
        scorer_retry_args,
        service=stale_transaction_service,
        core=core,
        now=lambda: "2026-07-20T05:46:02Z",
    )
    assert invalid_result["status"] == "INVALID"
    assert invalid_result["holdout_retired"] is True
    assert invalid_result["labels_reread"] is False
    assert stale_transaction_service.events.count(
        ("download", labels_blob)
    ) == stale_label_reads
    invalid_manifest = core.parse_json_strict(
        stale_transaction_service.data[invalid_blob],
        "INVALID closure",
    )
    invalid_labels_receipt = core.parse_json_strict(
        stale_transaction_service.data[
            f"{prefixes['state']}/"
            f"{core.STATE_RECEIPT_FILENAMES['LABELS_READ']}"
        ],
        "INVALID LABELS_READ",
    )
    invalid_closed = core.parse_json_strict(
        stale_transaction_service.data[invalid_closed_blob],
        "INVALID CLOSED",
    )
    core.validate_invalid_closed_outcome(
        invalid_closed,
        invalid_manifest,
        labels_open_transaction=stale_labels_transaction,
        labels_read_receipt=invalid_labels_receipt,
    )
    assert invalid_manifest["result_status"] == "INVALID"
    assert invalid_manifest["metrics_accepted"] is False
    assert invalid_manifest["decision_accepted"] is False
    invalid_text = stale_transaction_service.data[invalid_blob].decode("utf-8")
    assert all(
        token not in invalid_text
        for token in (
            "output_text",
            "registered_reference_answer",
            "expected_parsed_answer",
            "case_id",
            "PV2-",
        )
    )
    forged_invalid = deepcopy(invalid_manifest)
    forged_invalid["metrics_accepted"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_invalid_closed_outcome(
            invalid_closed,
            forged_invalid,
            labels_open_transaction=stale_labels_transaction,
            labels_read_receipt=invalid_labels_receipt,
        )
    authenticated_invalid = authenticate_persisted(
        stale_transaction_service
    )
    assert authenticated_invalid["state"] == "CLOSED"
    assert authenticated_invalid["result_status"] == "INVALID"
    assert authenticated_invalid["scoring_attempt"] is None
    invalid_uploads_before = [
        event
        for event in stale_transaction_service.events
        if event[0] == "upload"
    ]
    recovered_invalid = finalizer.run_stage_e(
        scorer_retry_args,
        service=stale_transaction_service,
        core=core,
        now=lambda: "2026-07-20T05:46:03Z",
    )
    assert recovered_invalid["writes_performed"] is False
    assert [
        event
        for event in stale_transaction_service.events
        if event[0] == "upload"
    ] == invalid_uploads_before

    reused_visibility_args = deepcopy(scorer_retry_args)
    reused_visibility_args.visibility_prefix = prefixes["visibility"]
    with pytest.raises(core.LockedEvaluationError):
        finalizer.run_stage_e(
            reused_visibility_args,
            service=deepcopy(scorer_primary_service),
            core=core,
            now=lambda: "2026-07-20T05:46:02Z",
        )

    scorer_retry_service = deepcopy(scorer_primary_service)
    primary_partial_before = {
        name: (
            scorer_retry_service.data[name],
            scorer_retry_service.etags[name],
        )
        for name in (
            score_reservation_blob,
            stage_e_visibility_blob,
        )
    }
    scorer_retry_start = len(scorer_retry_service.events)
    scorer_retry_result = finalizer.run_stage_e(
        scorer_retry_args,
        service=scorer_retry_service,
        core=core,
        now=lambda: "2026-07-20T05:46:02Z",
    )
    assert scorer_retry_result["status"] == "PASS"
    assert scorer_retry_result["scores_prefix"] == scorer_retry_prefixes[
        "scores"
    ]
    assert scorer_retry_result["visibility_prefix"] == scorer_retry_prefixes[
        "visibility"
    ]
    assert {
        name: (
            scorer_retry_service.data[name],
            scorer_retry_service.etags[name],
        )
        for name in primary_partial_before
    } == primary_partial_before
    abandoned_blob = core.derive_abandoned_attempt_blob_name(
        PARENT,
        AUTHORIZATION,
        "E",
        "scorer_infrastructure",
        scorer_retry_args.execution_id,
    )
    retry_visibility_blob = (
        f"{scorer_retry_prefixes['visibility']}/stage_e_visibility.json"
    )
    assert core.list_exact_prefix(
        scorer_retry_service,
        stage_e_args.container,
        scorer_retry_prefixes["visibility"],
    ) == {abandoned_blob, retry_visibility_blob}
    abandoned = core.parse_json_strict(
        scorer_retry_service.data[abandoned_blob],
        "abandoned Stage-E attempt",
    )
    assert {item["blob_name"] for item in abandoned["abandoned_members"]} == {
        score_reservation_blob,
        f"{prefixes['visibility']}/stage_p_visibility.json",
        stage_e_visibility_blob,
    }
    retry_manifest_blob = (
        f"{scorer_retry_prefixes['scores']}/"
        f"{core.SCORE_MEMBER_NAMES[-1]}"
    )
    retry_manifest = core.parse_json_strict(
        scorer_retry_service.data[retry_manifest_blob],
        "scorer retry score manifest",
    )
    retry_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RETRY_RECEIPT_FILENAMES['scorer_infrastructure']}"
    )
    assert retry_manifest["scoring_retry_kind"] == "scorer_infrastructure"
    assert retry_manifest["scores_prefix"] == scorer_retry_prefixes["scores"]
    assert retry_manifest["scoring_execution_id"] == (
        scorer_retry_args.execution_id
    )
    assert retry_manifest["retry_receipt_sha256"] == core.sha256_bytes(
        scorer_retry_service.data[retry_receipt_blob]
    )
    assert not any(
        event[0] == "upload"
        and event[1]
        in {
            stage_e_visibility_blob,
            score_reservation_blob,
        }
        for event in scorer_retry_service.events[scorer_retry_start:]
    )
    assert (
        "upload",
        labels_transaction_blob,
        False,
    ) in scorer_retry_service.events[scorer_retry_start:]
    retry_crash_service = deepcopy(scorer_retry_service)
    for name in core.SCORE_MEMBER_NAMES[1:]:
        blob = f"{scorer_retry_prefixes['scores']}/{name}"
        del retry_crash_service.data[blob]
        del retry_crash_service.etags[blob]
    for name in (
        core.SCORING_TRANSACTION_FILENAME,
        core.SCORING_ATTESTATION_FILENAME,
        core.STATE_RECEIPT_FILENAMES["SCORES_VERIFIED"],
        core.STATE_RECEIPT_FILENAMES["CLOSED"],
        core.CLOSURE_MANIFEST_FILENAME,
    ):
        blob = f"{prefixes['state']}/{name}"
        del retry_crash_service.data[blob]
        del retry_crash_service.etags[blob]
    retry_crash_authentication = authenticate_persisted(retry_crash_service)
    assert retry_crash_authentication["state"] == "LABELS_READ"
    assert retry_crash_authentication["scoring_attempt"] is None
    assert retry_crash_authentication["pending_scoring_attempt"][
        "retry_kind"
    ] == "scorer_infrastructure"
    assert retry_crash_authentication["pending_scoring_attempt"][
        "execution_id"
    ] == scorer_retry_args.execution_id

    retry_closure_args = deepcopy(scorer_retry_args)
    retry_closure_args.close_invalid_only = True
    retry_closure_args.verify_only = True
    retry_closure_args.retry_kind = "verification_only"
    retry_closure_args.scores_manifest_sha256 = None
    retry_closure_args.closed_receipt_sha256 = None
    retry_closure_args.execution_id = "synthetic-retry-invalid-closure"
    retry_closure_args.actor = "stage-e-invalid-closure-runtime"
    retry_closure_args.producer_retry_kind = "scorer_infrastructure"
    retry_closure_args.producer_execution_id = scorer_retry_args.execution_id
    retry_crash_label_reads = retry_crash_service.events.count(
        ("download", labels_blob)
    )
    retry_crash_closure = finalizer.run_stage_e(
        retry_closure_args,
        service=retry_crash_service,
        core=core,
        now=lambda: "2026-07-20T05:46:30Z",
    )
    assert retry_crash_closure["status"] == "INVALID"
    assert retry_crash_closure["metrics_recomputed"] is False
    assert retry_crash_service.events.count(("download", labels_blob)) == (
        retry_crash_label_reads
    )

    score_payload_blobs = {
        f"{scorer_retry_prefixes['scores']}/{name}"
        for name in core.SCORE_MEMBER_NAMES[:-1]
    }
    protected_reads_before_authentication = {
        blob: scorer_retry_service.events.count(("download", blob))
        for blob in {locked_input_blob, labels_blob, *score_payload_blobs}
    }
    scorer_retry_authentication = authenticate_persisted(
        scorer_retry_service
    )
    assert scorer_retry_authentication["scoring_attempt"]["retry_kind"] == (
        "scorer_infrastructure"
    )
    assert scorer_retry_authentication["scoring_attempt"]["scores_prefix"] == (
        scorer_retry_prefixes["scores"]
    )
    assert scorer_retry_authentication["score_payload_read"] is True
    for blob in (locked_input_blob, labels_blob):
        assert scorer_retry_service.events.count(("download", blob)) == (
            protected_reads_before_authentication[blob]
        )
    for blob in score_payload_blobs:
        assert scorer_retry_service.events.count(("download", blob)) == (
            protected_reads_before_authentication[blob] + 1
        )
    recreated_score_service = deepcopy(scorer_retry_service)
    recreated_score_blob = sorted(score_payload_blobs)[0]
    recreated_score_service.etags[recreated_score_blob] = '"recreated-score-etag"'
    with pytest.raises(core.LockedEvaluationError):
        authenticate_persisted(recreated_score_service)
    scorer_verification_args = deepcopy(scorer_retry_args)
    scorer_verification_args.verify_only = True
    scorer_verification_args.retry_kind = "verification_only"
    scorer_verification_args.execution_id = (
        "synthetic-scorer-verification"
    )
    scorer_verification_args.visibility_prefix = (
        core.derive_attempt_prefix(
            PARENT,
            AUTHORIZATION,
            "visibility",
            "E",
            "verification_only",
            scorer_verification_args.execution_id,
        )
    )
    scorer_verification_args.scores_manifest_sha256 = (
        scorer_retry_result["scores_manifest_sha256"]
    )
    scorer_verification_args.closed_receipt_sha256 = (
        scorer_retry_result["closed_receipt_sha256"]
    )
    scorer_label_reads = scorer_retry_service.events.count(
        ("download", labels_blob)
    )
    scorer_verification = finalizer.run_stage_e(
        scorer_verification_args,
        service=scorer_retry_service,
        core=core,
        now=lambda: "2026-07-21T05:46:02Z",
    )
    assert scorer_verification["scores_prefix"] == (
        scorer_retry_prefixes["scores"]
    )
    assert scorer_verification["metrics_recomputed"] is False
    assert scorer_retry_service.events.count(
        ("download", labels_blob)
    ) == scorer_label_reads
    scorer_verification_authentication = authenticate_persisted(
        scorer_retry_service
    )
    assert scorer_verification_authentication[
        "verification_retry_execution_id"
    ] == scorer_verification_args.execution_id
    assert scorer_verification_authentication["scoring_attempt"][
        "scores_prefix"
    ] == scorer_retry_prefixes["scores"]
    assert scorer_verification_args.visibility_prefix != (
        scorer_retry_prefixes["visibility"]
    )

    before_e = len(service.events)
    stage_e = finalizer.run_stage_e(
        stage_e_args,
        service=service,
        core=core,
        now=lambda: TIMESTAMP,
    )
    assert stage_e["status"] == "PASS"
    assert stage_e["holdout_retired"] is True
    assert stage_e["formal_evaluation_count"] == 1
    labels_receipt_blob = (
        f"{prefixes['state']}/"
        f"{core.STATE_RECEIPT_FILENAMES['LABELS_READ']}"
    )
    stage_e_events = service.events[before_e:]
    assert not any(
        len(event) > 1
        and isinstance(event[1], str)
        and event[1].startswith(f"{PARENT}/locked-inputs/")
        for event in stage_e_events
    )
    assert stage_e_events.index(("download", labels_blob)) < (
        stage_e_events.index(("upload", labels_receipt_blob, False))
    ) < stage_e_events.index(("download", labels_receipt_blob))
    assert set(core.SCORE_MEMBER_NAMES) == {
        name.removeprefix(f"{prefixes['scores']}/")
        for name in service.data
        if name.startswith(f"{prefixes['scores']}/")
    }
    score_manifest_blob = (
        f"{prefixes['scores']}/{core.SCORE_MEMBER_NAMES[-1]}"
    )
    score_manifest = core.parse_json_strict(
        service.data[score_manifest_blob], "scores manifest"
    )
    ledger_blob = (
        f"{prefixes['scores']}/{core.SCORING_LEDGER_FILENAME}"
    )
    ledger_rows = core.parse_jsonl_strict(
        service.data[ledger_blob], core.SCORING_LEDGER_FILENAME
    )
    assert len(ledger_rows) == 120
    ledger_member = next(
        item
        for item in score_manifest["payload_members"]
        if item["name"] == core.SCORING_LEDGER_FILENAME
    )
    assert ledger_member == {
        "name": core.SCORING_LEDGER_FILENAME,
        "sha256": core.sha256_bytes(service.data[ledger_blob]),
        "size": len(service.data[ledger_blob]),
        "etag": service.etags[ledger_blob],
    }
    metrics = core.parse_json_strict(
        service.data[
            f"{prefixes['scores']}/locked_evaluation_metrics.json"
        ],
        "metrics",
    )
    decision = core.parse_json_strict(
        service.data[
            f"{prefixes['scores']}/locked_evaluation_decision.json"
        ],
        "decision",
    )
    assert (
        score_manifest["labels_sha256"]
        == metrics["labels_sha256"]
        == decision["labels_sha256"]
    )
    assert (
        score_manifest["labels_open_transaction_sha256"]
        == metrics["labels_open_transaction_sha256"]
        == decision["labels_open_transaction_sha256"]
    )
    scoring_transaction_blob = (
        f"{prefixes['state']}/{core.SCORING_TRANSACTION_FILENAME}"
    )
    scoring_attestation_blob = (
        f"{prefixes['state']}/{core.SCORING_ATTESTATION_FILENAME}"
    )
    scoring_transaction = core.parse_json_strict(
        service.data[scoring_transaction_blob], "scoring transaction"
    )
    scoring_attestation = core.parse_json_strict(
        service.data[scoring_attestation_blob], "scoring attestation"
    )
    assert (
        score_manifest["scoring_transaction_sha256"]
        == stage_e["scoring_transaction_sha256"]
        == core.sha256_bytes(service.data[scoring_transaction_blob])
    )
    core.validate_scoring_attestation(
        scoring_attestation,
        transaction=scoring_transaction,
        score_manifest_bytes=service.data[score_manifest_blob],
        score_manifest_etag=service.etags[score_manifest_blob],
    )
    tampered_score_service = deepcopy(service)
    for name in (
        core.STATE_RECEIPT_FILENAMES["SCORES_VERIFIED"],
        core.STATE_RECEIPT_FILENAMES["CLOSED"],
        core.CLOSURE_MANIFEST_FILENAME,
    ):
        blob = f"{prefixes['state']}/{name}"
        del tampered_score_service.data[blob]
        del tampered_score_service.etags[blob]
    tampered_report_blob = (
        f"{prefixes['scores']}/locked_evaluation_report.md"
    )
    tampered_score_service.preload(
        tampered_report_blob,
        tampered_score_service.data[tampered_report_blob] + b"forged\n",
    )
    replacement_manifest = deepcopy(score_manifest)
    replacement_member = next(
        item
        for item in replacement_manifest["payload_members"]
        if item["name"] == "locked_evaluation_report.md"
    )
    replacement_member.update(
        {
            "size": len(tampered_score_service.data[tampered_report_blob]),
            "sha256": core.sha256_bytes(
                tampered_score_service.data[tampered_report_blob]
            ),
            "etag": tampered_score_service.etags[tampered_report_blob],
        }
    )
    replacement_manifest_bytes = core.canonical_json_bytes(
        replacement_manifest
    )
    tampered_score_service.preload(
        score_manifest_blob,
        replacement_manifest_bytes,
    )
    replacement_attestation = core.build_scoring_attestation(
        scoring_transaction,
        score_manifest_bytes=replacement_manifest_bytes,
        score_manifest_etag=tampered_score_service.etags[
            score_manifest_blob
        ],
    )
    tampered_score_service.preload(
        scoring_attestation_blob,
        core.canonical_json_bytes(replacement_attestation),
    )
    tampered_pending = authenticate_persisted(tampered_score_service)
    assert tampered_pending["state"] == "LABELS_READ"
    assert tampered_pending["scoring_attempt"] is None
    assert tampered_pending["pending_scoring_attempt"][
        "closure_required"
    ] is True
    assert tampered_pending["score_payload_read"] is True

    tampered_closure_args = deepcopy(stage_e_args)
    tampered_closure_args.close_invalid_only = True
    tampered_closure_args.verify_only = True
    tampered_closure_args.retry_kind = "verification_only"
    tampered_closure_args.scores_manifest_sha256 = None
    tampered_closure_args.closed_receipt_sha256 = None
    tampered_closure_args.execution_id = "synthetic-tampered-invalid-closure"
    tampered_closure_args.actor = "stage-e-invalid-closure-runtime"
    tampered_closure_args.producer_retry_kind = "none"
    tampered_closure_args.producer_execution_id = stage_e_args.execution_id
    tampered_label_reads = tampered_score_service.events.count(
        ("download", labels_blob)
    )
    tampered_bytes = tampered_score_service.data[tampered_report_blob]
    tampered_closure = finalizer.run_stage_e(
        tampered_closure_args,
        service=tampered_score_service,
        core=core,
        now=lambda: "2026-07-20T05:46:30Z",
    )
    assert tampered_closure["status"] == "INVALID"
    assert tampered_closure["metrics_recomputed"] is False
    assert tampered_score_service.data[tampered_report_blob] == tampered_bytes
    assert tampered_score_service.events.count(("download", labels_blob)) == (
        tampered_label_reads
    )

    verification_parser_calls = dict(stage_p_parser_calls)

    forged_transaction_service = deepcopy(service)
    transaction_blob = (
        f"{prefixes['state']}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    forged_transaction = core.parse_json_strict(
        forged_transaction_service.data[transaction_blob],
        "labels-open transaction",
    )
    forged_transaction["config_sha256"] = "f" * 64
    forged_transaction_service.preload(
        transaction_blob, core.canonical_json_bytes(forged_transaction)
    )
    forged_verification_args = deepcopy(stage_e_args)
    forged_verification_args.verify_only = True
    forged_verification_args.retry_kind = "verification_only"
    forged_verification_args.execution_id = "synthetic-forged-verification"
    forged_verification_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        forged_verification_args.execution_id,
    )
    forged_verification_args.scores_manifest_sha256 = stage_e[
        "scores_manifest_sha256"
    ]
    forged_verification_args.closed_receipt_sha256 = stage_e[
        "closed_receipt_sha256"
    ]
    forged_label_reads = forged_transaction_service.events.count(
        ("download", labels_blob)
    )
    with pytest.raises(core.LockedEvaluationError):
        finalizer.run_stage_e(
            forged_verification_args,
            service=forged_transaction_service,
            core=core,
            now=lambda: TIMESTAMP,
        )
    assert forged_transaction_service.events.count(
        ("download", labels_blob)
    ) == forged_label_reads

    closure_adoption_service = deepcopy(service)
    closed_blob = (
        f"{prefixes['state']}/{core.STATE_RECEIPT_FILENAMES['CLOSED']}"
    )
    del closure_adoption_service.data[closed_blob]
    del closure_adoption_service.etags[closed_blob]
    closure_adoption_args = deepcopy(stage_e_args)
    closure_adoption_args.verify_only = True
    closure_adoption_args.retry_kind = "verification_only"
    closure_adoption_args.execution_id = "synthetic-closure-adoption"
    closure_adoption_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        closure_adoption_args.execution_id,
    )
    closure_adoption_args.scores_manifest_sha256 = stage_e[
        "scores_manifest_sha256"
    ]
    closure_adoption_args.closed_receipt_sha256 = None
    closure_adoption_start = len(closure_adoption_service.events)
    closure_adopted = finalizer.run_stage_e(
        closure_adoption_args,
        service=closure_adoption_service,
        core=core,
        now=lambda: TIMESTAMP,
    )
    assert closure_adopted["closure_adopted"] is True
    closure_adoption_uploads = [
        event[1]
        for event in closure_adoption_service.events[
            closure_adoption_start:
        ]
        if event[0] == "upload"
    ]
    assert closure_adoption_uploads == [
        (
            f"{prefixes['state']}/"
            f"{core.STATE_RETRY_RECEIPT_FILENAMES['verification_only']}"
        ),
        (
            f"{closure_adoption_args.visibility_prefix}/"
            "stage_e_visibility.json"
        ),
        closed_blob,
    ]

    recovery_service = deepcopy(service)
    for name in (
        core.STATE_RECEIPT_FILENAMES["SCORES_VERIFIED"],
        core.STATE_RECEIPT_FILENAMES["CLOSED"],
        core.CLOSURE_MANIFEST_FILENAME,
    ):
        blob = f"{prefixes['state']}/{name}"
        del recovery_service.data[blob]
        del recovery_service.etags[blob]
    recovery_args = deepcopy(stage_e_args)
    recovery_args.verify_only = True
    recovery_args.verification_state = "LABELS_READ"
    recovery_args.retry_kind = "verification_only"
    recovery_args.execution_id = "synthetic-verification-recovery"
    recovery_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        recovery_args.execution_id,
    )
    recovery_args.scores_manifest_sha256 = stage_e[
        "scores_manifest_sha256"
    ]
    recovery_args.closed_receipt_sha256 = None
    recovery_label_reads = recovery_service.events.count(
        ("download", labels_blob)
    )
    delayed_recovery_timestamp = "2026-07-21T05:45:24Z"
    recovered = finalizer.run_stage_e(
        recovery_args,
        service=recovery_service,
        core=core,
        now=lambda: delayed_recovery_timestamp,
    )
    assert recovered["status"] == "PASS"
    assert recovered["metrics_recomputed"] is False
    assert recovered["evaluation_artifact_bytes_modified"] is False
    assert recovered["recovery_state_bytes_written"] is True
    assert recovery_service.events.count(
        ("download", labels_blob)
    ) == recovery_label_reads
    for state in ("SCORES_VERIFIED", "CLOSED"):
        recovered_receipt = core.parse_json_strict(
            recovery_service.data[
                f"{prefixes['state']}/{core.STATE_RECEIPT_FILENAMES[state]}"
            ],
            f"recovered {state} receipt",
        )
        assert (
            recovered_receipt["timestamp_utc"]
            == delayed_recovery_timestamp
        )

    unattested_service = deepcopy(service)
    for name in (
        core.SCORING_ATTESTATION_FILENAME,
        core.STATE_RECEIPT_FILENAMES["SCORES_VERIFIED"],
        core.STATE_RECEIPT_FILENAMES["CLOSED"],
        core.CLOSURE_MANIFEST_FILENAME,
    ):
        blob = f"{prefixes['state']}/{name}"
        del unattested_service.data[blob]
        del unattested_service.etags[blob]
    unattested_args = deepcopy(recovery_args)
    unattested_args.execution_id = "synthetic-unattested-recovery"
    unattested_label_reads = unattested_service.events.count(
        ("download", labels_blob)
    )
    unattested_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        unattested_args.execution_id,
    )
    unattested_result = finalizer.run_stage_e(
        unattested_args,
        service=unattested_service,
        core=core,
        now=lambda: TIMESTAMP,
    )
    assert unattested_result["status"] == "INVALID"
    assert unattested_result["result_status"] == "INVALID"
    assert unattested_result["metric_retry_allowed"] is False
    assert (
        f"{prefixes['state']}/{core.INVALID_CLOSURE_FILENAME}"
        in unattested_service.data
    )
    assert (
        f"{prefixes['state']}/{core.STATE_RECEIPT_FILENAMES['CLOSED']}"
        in unattested_service.data
    )
    assert unattested_service.events.count(
        ("download", labels_blob)
    ) == unattested_label_reads

    label_reads = service.events.count(("download", labels_blob))
    verification_args = deepcopy(stage_e_args)
    verification_args.verify_only = True
    verification_args.retry_kind = "verification_only"
    verification_args.execution_id = "synthetic-verification-final"
    verification_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        verification_args.execution_id,
    )
    verification_args.scores_manifest_sha256 = stage_e[
        "scores_manifest_sha256"
    ]
    verification_args.closed_receipt_sha256 = stage_e[
        "closed_receipt_sha256"
    ]
    verification = finalizer.run_stage_e(
        verification_args,
        service=service,
        core=core,
        now=lambda: TIMESTAMP,
    )
    assert verification["mode"] == "verification_only"
    assert verification["metrics_recomputed"] is False
    assert verification["bytes_modified"] is True
    assert service.events.count(("download", labels_blob)) == label_reads
    assert stage_p_parser_calls == verification_parser_calls
    score_uploads = [
        event
        for event in service.events
        if event[0] == "upload"
        and event[1].startswith(f"{prefixes['scores']}/")
    ]
    score_upload_count = len(score_uploads)
    verification_again = finalizer.run_stage_e(
        verification_args,
        service=service,
        core=core,
        now=lambda: "2026-07-21T05:45:24Z",
    )
    assert verification_again["bytes_modified"] is False
    assert len(
        [
            event
            for event in service.events
            if event[0] == "upload"
            and event[1].startswith(f"{prefixes['scores']}/")
        ]
    ) == score_upload_count
    different_verification_args = deepcopy(verification_args)
    different_verification_args.execution_id = "different-verification"
    different_verification_args.visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        different_verification_args.execution_id,
    )
    with pytest.raises(core.LockedEvaluationError, match="another execution"):
        finalizer.run_stage_e(
            different_verification_args,
            service=service,
            core=core,
            now=lambda: "2026-07-21T05:45:25Z",
        )


def test_stage_p_receipt_failures_and_cross_execution_crash_adoption(
    synthetic_bundle, _isolated_stage_e_modules, monkeypatch
):
    class StagePComplete(Exception):
        pass

    def stop_before_stage_e(*_args, **_kwargs):
        raise StagePComplete

    monkeypatch.setattr(finalizer, "run_stage_e", stop_before_stage_e)
    with pytest.raises(StagePComplete):
        test_synthetic_end_to_end_stage_p_stage_e_and_verify_only(
            synthetic_bundle, _isolated_stage_e_modules, monkeypatch
        )


def test_overwrite_false_reservation_first_manifest_last_and_exact_membership():
    service = _FakeService()
    prefix = f"{PARENT}/predictions/{AUTHORIZATION}"
    names = (".reservation.json", "payload.json", "artifact_manifest.json")
    payloads = {
        ".reservation.json": core.canonical_json_bytes({"reservation": True}),
        "payload.json": core.canonical_json_bytes({"value": 1}),
    }
    result = core.persist_manifest_last_prefix(
        service,
        "synthetic-container",
        prefix,
        member_names=names,
        payloads=payloads,
        manifest_builder=lambda metadata: {
            "members": metadata,
            "manifest_uploaded_last": True,
        },
    )
    uploads = [event for event in service.events if event[0] == "upload"]
    assert [event[1].rsplit("/", 1)[-1] for event in uploads] == list(names)
    assert all(event[2] is False for event in uploads)
    assert set(service.data) == {f"{prefix}/{name}" for name in names}
    assert result["verified_count"] == 3
    with pytest.raises(core.LockedEvaluationError, match="not empty"):
        core.persist_manifest_last_prefix(
            service,
            "synthetic-container",
            prefix,
            member_names=names,
            payloads=payloads,
            manifest_builder=lambda metadata: {"members": metadata},
        )


def test_inputs_read_receipt_is_verified_before_payload_reader():
    receipts = _state_chain_until("UNSEAL_AUTHORIZED")
    input_receipt = core.build_next_state_receipt(
        receipts[-1],
        state="INPUTS_READ",
        artifact_manifest_sha256="7" * 64,
        timestamp_utc=TIMESTAMP,
        execution_id="stage-p",
        actor="synthetic",
        visibility=["locked-inputs"],
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    service = _FakeService()
    input_blob = f"{PARENT}/locked-inputs/locked_inputs.jsonl"
    input_bytes = b'{"synthetic":true}\n'
    service.preload(input_blob, input_bytes)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    runner.persist_input_receipt_then_read_inputs(
        core,
        service,
        container="synthetic-container",
        state_prefix=state_prefix,
        input_receipt=input_receipt,
        locked_input_blob=input_blob,
        locked_input_sha256=core.sha256_bytes(input_bytes),
        locked_input_size=len(input_bytes),
    )
    receipt_blob = (
        f"{state_prefix}/{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    receipt_upload = service.events.index(("upload", receipt_blob, False))
    receipt_verify = service.events.index(("download", receipt_blob))
    input_download = service.events.index(("download", input_blob))
    assert receipt_upload < receipt_verify < input_download
    downloads_before = service.events.count(("download", input_blob))
    with pytest.raises(core.LockedEvaluationError, match="overwrite-false"):
        runner.persist_input_receipt_then_read_inputs(
            core,
            service,
            container="synthetic-container",
            state_prefix=state_prefix,
            input_receipt=input_receipt,
            locked_input_blob=input_blob,
            locked_input_sha256=core.sha256_bytes(input_bytes),
            locked_input_size=len(input_bytes),
        )
    assert service.events.count(("download", input_blob)) == downloads_before


def test_inputs_read_ambiguous_create_reauthenticates_once_without_reread():
    receipts = _state_chain_until("UNSEAL_AUTHORIZED")
    input_receipt = core.build_next_state_receipt(
        receipts[-1],
        state="INPUTS_READ",
        artifact_manifest_sha256="7" * 64,
        timestamp_utc=TIMESTAMP,
        execution_id="stage-p",
        actor="synthetic",
        visibility=["locked-inputs"],
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    service = _FakeService()
    input_blob = f"{PARENT}/locked-inputs/locked_inputs.jsonl"
    input_bytes = b'{"synthetic":true}\n'
    service.preload(input_blob, input_bytes)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    receipt_blob = (
        f"{state_prefix}/{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    service.upload_faults[receipt_blob] = "ambiguous_success"

    persistence, downloaded, _ = runner.persist_input_receipt_then_read_inputs(
        core,
        service,
        container="synthetic-container",
        state_prefix=state_prefix,
        input_receipt=input_receipt,
        locked_input_blob=input_blob,
        locked_input_sha256=core.sha256_bytes(input_bytes),
        locked_input_size=len(input_bytes),
    )

    assert downloaded == input_bytes
    assert persistence == {
        "blob_name": receipt_blob,
        "size": len(service.data[receipt_blob]),
        "sha256": core.sha256_bytes(service.data[receipt_blob]),
        "etag": service.etags[receipt_blob],
    }
    assert service.events.count(("download", input_blob)) == 1
    with pytest.raises(core.LockedEvaluationError, match="reread is prohibited"):
        runner.persist_input_receipt_then_read_inputs(
            core,
            service,
            container="synthetic-container",
            state_prefix=state_prefix,
            input_receipt=input_receipt,
            locked_input_blob=input_blob,
            locked_input_sha256=core.sha256_bytes(input_bytes),
            locked_input_size=len(input_bytes),
        )
    assert service.events.count(("download", input_blob)) == 1


@pytest.mark.parametrize(
    ("fault", "receipt_exists"),
    (("pre_create", False), ("tampered_success", True)),
)
def test_inputs_read_failure_never_advances_without_exact_durable_receipt(
    fault, receipt_exists
):
    receipts = _state_chain_until("UNSEAL_AUTHORIZED")
    input_receipt = core.build_next_state_receipt(
        receipts[-1],
        state="INPUTS_READ",
        artifact_manifest_sha256="7" * 64,
        timestamp_utc=TIMESTAMP,
        execution_id="stage-p",
        actor="synthetic",
        visibility=["locked-inputs"],
        authorization_lock=_authorization_lock(receipts),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    service = _FakeService()
    input_blob = f"{PARENT}/locked-inputs/locked_inputs.jsonl"
    input_bytes = b'{"synthetic":true}\n'
    service.preload(input_blob, input_bytes)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    receipt_blob = (
        f"{state_prefix}/{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    service.upload_faults[receipt_blob] = fault

    with pytest.raises(core.LockedEvaluationError, match="not proven durable"):
        runner.persist_input_receipt_then_read_inputs(
            core,
            service,
            container="synthetic-container",
            state_prefix=state_prefix,
            input_receipt=input_receipt,
            locked_input_blob=input_blob,
            locked_input_sha256=core.sha256_bytes(input_bytes),
            locked_input_size=len(input_bytes),
        )

    assert (receipt_blob in service.data) is receipt_exists
    if receipt_exists:
        assert service.data[receipt_blob] != core.canonical_json_bytes(
            input_receipt
        )
    assert service.events.count(("download", input_blob)) == 0


def test_labels_open_singleton_is_verified_before_label_reader():
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    labels_blob = f"{PARENT}/locked-labels/locked_reference_labels.jsonl"
    labels_bytes = b'{"synthetic":true}\n'
    transaction = core.build_labels_open_transaction(
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        state_prefix=state_prefix,
        scores_prefix=core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        scoring_retry_kind="none",
        retry_receipt_sha256=None,
        authorization_lock_sha256="6" * 64,
        authorization_manifest_sha256="7" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_manifest_sha256="1" * 64,
        prediction_seal_sha256="8" * 64,
        prediction_request_manifest_sha256="9" * 64,
        input_manifest_sha256="a" * 64,
        locked_manifest_sha256="2" * 64,
        labels_manifest_sha256="3" * 64,
        labels_manifest_blob_name=(
            f"{PARENT}/locked-labels/locked_labels_manifest.json"
        ),
        labels_manifest_etag='"labels-manifest-etag"',
        labels_blob_name=labels_blob,
        labels_sha256=core.sha256_bytes(labels_bytes),
        ordered_case_ids=["PV2-" + "1" * 20],
        prior_receipt_sha256="4" * 64,
        visibility_blob_name=(
            f"{core.evaluation_prefixes(PARENT, AUTHORIZATION)['visibility']}/"
            "stage_e_visibility.json"
        ),
        visibility_sha256="5" * 64,
        visibility_etag='"visibility-etag"',
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        execution_id="stage-e",
        actor="synthetic",
        created_utc=TIMESTAMP,
    )
    forged_ordinal = deepcopy(transaction)
    forged_ordinal["formal_evaluation_ordinal"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_labels_open_transaction(forged_ordinal)
    service = _FakeService()
    service.preload(labels_blob, labels_bytes)
    finalizer.persist_transaction_then_read_labels(
        core,
        service,
        container="synthetic-container",
        state_prefix=state_prefix,
        transaction=transaction,
        labels_blob=labels_blob,
        labels_sha256=core.sha256_bytes(labels_bytes),
        labels_size=len(labels_bytes),
    )
    transaction_blob = (
        f"{state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    assert service.events.index(("upload", transaction_blob, False)) < (
        service.events.index(("download", transaction_blob))
    ) < service.events.index(("download", labels_blob))
    label_downloads = service.events.count(("download", labels_blob))
    with pytest.raises(core.LockedEvaluationError, match="overwrite-false"):
        finalizer.persist_transaction_then_read_labels(
            core,
            service,
            container="synthetic-container",
            state_prefix=state_prefix,
            transaction=transaction,
            labels_blob=labels_blob,
            labels_sha256=core.sha256_bytes(labels_bytes),
            labels_size=len(labels_bytes),
        )
    assert service.events.count(("download", labels_blob)) == label_downloads


def _sealed_public_bundle(synthetic_bundle):
    request = core.build_prediction_request_manifest(
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        prediction_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)[
            "predictions"
        ],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        authorization_lock_sha256="1" * 64,
        authorization_manifest_sha256="2" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        locked_manifest_sha256="3" * 64,
        input_receipt_sha256="4" * 64,
        locked_input_reservation_blob=(
            f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
        ),
        locked_input_reservation_sha256=core.sha256_bytes(
            _locked_input_reservation_bytes()
        ),
        locked_input_private_nonce_sha256=(
            _locked_input_private_nonce_sha256()
        ),
        locked_input_reservation_etag='"reservation-etag"',
        locked_input_blob=f"{PARENT}/locked-inputs/locked_inputs.jsonl",
        locked_input_sha256=core.sha256_bytes(
            core.canonical_jsonl_bytes(synthetic_bundle["locked_inputs"])
        ),
        locked_input_etag='"input-etag"',
        locked_input_manifest_blob=(
            f"{PARENT}/locked-inputs/locked_inputs_manifest.json"
        ),
        locked_input_manifest_sha256="5" * 64,
        locked_input_manifest_etag='"manifest-etag"',
        visibility_blob=(
            f"{core.evaluation_prefixes(PARENT, AUTHORIZATION)['visibility']}/"
            "stage_p_visibility.json"
        ),
        visibility_sha256="6" * 64,
        visibility_etag='"visibility-etag"',
        ordered_case_ids=[
            item["case_id"] for item in synthetic_bundle["locked_inputs"]
        ],
        created_utc=TIMESTAMP,
    )
    seal = core.build_locked_prediction_seal(
        request_manifest=request,
        predictions=synthetic_bundle["predictions"],
        legacy_predictions=synthetic_bundle["legacy"],
        locked_inputs=synthetic_bundle["locked_inputs"],
        sealed_utc=TIMESTAMP,
    )
    return (
        request,
        seal,
        core.canonical_json_bytes(request),
        core.canonical_jsonl_bytes(synthetic_bundle["predictions"]),
        core.canonical_jsonl_bytes(synthetic_bundle["legacy"]),
    )


def test_self_consistent_alternate_prediction_universe_is_not_authorized(
    synthetic_bundle,
):
    alternate_inputs = deepcopy(synthetic_bundle["locked_inputs"])
    alternate_ids = [f"PV2-{index:020x}" for index in range(1, 121)]
    for locked, case_id in zip(
        alternate_inputs,
        alternate_ids,
        strict=True,
    ):
        locked["case_id"] = case_id
    alternate_predictions = [
        core.build_prediction_envelope(locked, prediction["parser_result"])
        for locked, prediction in zip(
            alternate_inputs,
            synthetic_bundle["predictions"],
            strict=True,
        )
    ]
    alternate_legacy = [
        core.build_legacy_prediction(locked, legacy["legacy_result"])
        for locked, legacy in zip(
            alternate_inputs, synthetic_bundle["legacy"], strict=True
        )
    ]
    alternate_input_bytes = core.canonical_jsonl_bytes(alternate_inputs)
    source_manifest_bytes = _source_manifest_bytes(
        kind="locked-inputs",
        relative_path="locked-inputs/locked_inputs.jsonl",
        payload=alternate_input_bytes,
        ordered_case_ids=alternate_ids,
    )
    source_manifest_sha256 = core.sha256_bytes(source_manifest_bytes)
    request = core.build_prediction_request_manifest(
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        prediction_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)[
            "predictions"
        ],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        authorization_lock_sha256="1" * 64,
        authorization_manifest_sha256="2" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        locked_manifest_sha256="3" * 64,
        input_receipt_sha256="4" * 64,
        locked_input_reservation_blob=(
            f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
        ),
        locked_input_reservation_sha256=core.sha256_bytes(
            _locked_input_reservation_bytes()
        ),
        locked_input_private_nonce_sha256=(
            _locked_input_private_nonce_sha256()
        ),
        locked_input_reservation_etag='"alternate-reservation-etag"',
        locked_input_blob=f"{PARENT}/locked-inputs/locked_inputs.jsonl",
        locked_input_sha256=core.sha256_bytes(alternate_input_bytes),
        locked_input_etag='"alternate-input-etag"',
        locked_input_manifest_blob=(
            f"{PARENT}/locked-inputs/locked_inputs_manifest.json"
        ),
        locked_input_manifest_sha256=source_manifest_sha256,
        locked_input_manifest_etag='"alternate-manifest-etag"',
        visibility_blob=(
            f"{core.evaluation_prefixes(PARENT, AUTHORIZATION)['visibility']}/"
            "stage_p_visibility.json"
        ),
        visibility_sha256="6" * 64,
        visibility_etag='"visibility-etag"',
        ordered_case_ids=alternate_ids,
        created_utc=TIMESTAMP,
    )
    seal = core.build_locked_prediction_seal(
        request_manifest=request,
        predictions=alternate_predictions,
        legacy_predictions=alternate_legacy,
        locked_inputs=alternate_inputs,
        sealed_utc=TIMESTAMP,
    )
    payloads = {
        ".prediction_reservation.json": core.canonical_json_bytes(
            core.build_reservation(
                leaf="predictions",
                prefix=request["prediction_prefix"],
                authorization_id=AUTHORIZATION,
                created_utc=TIMESTAMP,
                nonce="alternate-universe-nonce",
            )
        ),
        "prediction_request_manifest.json": core.canonical_json_bytes(request),
        "parser_v2_locked_predictions.jsonl": core.canonical_jsonl_bytes(
            alternate_predictions
        ),
        "legacy_locked_predictions.jsonl": core.canonical_jsonl_bytes(
            alternate_legacy
        ),
        "prediction_seal.json": core.canonical_json_bytes(seal),
    }
    metadata = [
        {
            "name": name,
            "size": len(payloads[name]),
            "sha256": core.sha256_bytes(payloads[name]),
            "etag": f'"alternate-{index}"',
        }
        for index, name in enumerate(core.PREDICTION_MEMBER_NAMES[:-1])
    ]
    manifest = core.build_prediction_artifact_manifest(
        metadata=metadata,
        seal_sha256=core.sha256_bytes(payloads["prediction_seal.json"]),
        prediction_seal=seal,
        request_manifest=request,
        created_utc=TIMESTAMP,
    )
    manifest_bytes = core.canonical_json_bytes(manifest)
    for mutate in (
        lambda value: value.update({"row_count": float(value["row_count"])}),
        lambda value: value["payload_members"][0].update({"size": True}),
    ):
        forged_manifest = deepcopy(manifest)
        mutate(forged_manifest)
        forged_manifest_bytes = core.canonical_json_bytes(forged_manifest)
        with pytest.raises(core.LockedEvaluationError):
            core.validate_prediction_artifact_manifest(
                forged_manifest_bytes,
                expected_sha256=core.sha256_bytes(forged_manifest_bytes),
                parent_prefix=PARENT,
                authorization_id=AUTHORIZATION,
            )
    artifacts = {
        **payloads,
        core.PREDICTION_MEMBER_NAMES[-1]: manifest_bytes,
    }
    with pytest.raises(core.LockedEvaluationError, match="provenance"):
        core.validate_prediction_artifact_graph(
            manifest_bytes,
            manifest,
            artifacts,
            gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
            source_manifest_bytes=source_manifest_bytes,
            source_manifest_etag='"alternate-manifest-etag"',
            expected_authorization_id=AUTHORIZATION,
            expected_parent_prefix=PARENT,
            expected_prediction_manifest_sha256=core.sha256_bytes(
                manifest_bytes
            ),
            expected_input_manifest_sha256="f" * 64,
            expected_input_receipt_sha256="4" * 64,
            expected_authorization_lock_sha256="1" * 64,
            expected_authorization_manifest_sha256="2" * 64,
            expected_implementation_manifest_sha256=core.sha256_bytes(
                IMPLEMENTATION_MANIFEST_BYTES
            ),
            expected_locked_manifest_sha256="3" * 64,
            expected_implementation_commit=IMPLEMENTATION,
            expected_image_digest=IMAGE_DIGEST,
            expected_config_sha256=CONFIG_SHA256,
        )


def test_labels_payload_and_metrics_require_exact_sealed_universe_and_gates(
    synthetic_bundle,
):
    gates = core.load_acceptance_gates(synthetic_bundle["gates"])
    expected_ids = [
        item["case_id"] for item in synthetic_bundle["locked_inputs"]
    ]
    alternate_labels = deepcopy(synthetic_bundle["labels"])
    alternate_labels[0]["case_id"] = "PV2-" + "f" * 20
    alternate_labels_bytes = core.canonical_jsonl_bytes(alternate_labels)
    with pytest.raises(core.LockedEvaluationError):
        core.validate_locked_labels_bytes(
            alternate_labels_bytes,
            gates,
            expected_sha256=core.sha256_bytes(alternate_labels_bytes),
            expected_ordered_case_ids=expected_ids,
        )

    metrics, _ = _score(synthetic_bundle)
    missing = deepcopy(metrics)
    missing["gates"].pop(next(iter(missing["gates"])))
    with pytest.raises(core.LockedEvaluationError):
        core.validate_metrics_artifact(missing, gates)
    fake = deepcopy(metrics)
    fake["gates"]["invented_optional_gate"] = deepcopy(
        next(iter(fake["gates"].values()))
    )
    with pytest.raises(core.LockedEvaluationError):
        core.validate_metrics_artifact(fake, gates)
    irrational = deepcopy(metrics)
    irrational["gates"]["overall_exact_typed_decision"]["threshold"][
        "numerator"
    ] += 1
    with pytest.raises(core.LockedEvaluationError):
        core.validate_metrics_artifact(irrational, gates)


def test_metrics_recompute_legacy_deltas_and_reject_forged_critical_pass(
    synthetic_bundle,
):
    metrics, _ = _score(synthetic_bundle)
    gates = core.load_acceptance_gates(synthetic_bundle["gates"])
    assert metrics["status"] == "PASS"

    forged_overall = deepcopy(metrics)
    overall_delta = metrics["legacy_comparison"]["overall_delta"]
    forged_overall["legacy_comparison"]["overall_delta"] = core.metric_record(
        overall_delta["numerator"] + 1,
        overall_delta["denominator"],
    )
    with pytest.raises(core.LockedEvaluationError, match="overall aggregates"):
        core.validate_metrics_artifact(forged_overall, gates)

    forged_clean = deepcopy(metrics)
    clean_delta = metrics["legacy_comparison"]["clean_delta"]
    alternate_clean_gate = core.metric_record(
        clean_delta["numerator"] + 1,
        clean_delta["denominator"],
        comparison=">=",
        threshold=core.Fraction(0),
        count_limit=0,
        mandatory=True,
    )
    forged_clean["legacy_comparison"]["clean_delta"] = alternate_clean_gate
    forged_clean["gates"]["clean_pooled_non_regression"] = alternate_clean_gate
    with pytest.raises(core.LockedEvaluationError, match="clean aggregates"):
        core.validate_metrics_artifact(forged_clean, gates)

    bindings = {
        "authorization_id": AUTHORIZATION,
        "registered_parent_prefix": PARENT,
        "authorization_lock_sha256": "1" * 64,
        "authorization_manifest_sha256": "2" * 64,
        "implementation_manifest_sha256": core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        "prediction_seal_sha256": "3" * 64,
        "prediction_manifest_sha256": "4" * 64,
        "prediction_request_manifest_sha256": "5" * 64,
        "locked_manifest_sha256": "6" * 64,
        "input_manifest_sha256": "7" * 64,
        "locked_input_sha256": "8" * 64,
        "labels_manifest_sha256": "9" * 64,
        "labels_sha256": "a" * 64,
        "labels_open_transaction_sha256": "b" * 64,
        "scores_prefix": core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        "scoring_retry_kind": "none",
        "scoring_execution_id": "synthetic-scoring",
        "scoring_actor": "synthetic-actor",
        "stage_e_visibility_sha256": "d" * 64,
        "retry_receipt_sha256": None,
        "scoring_ledger_sha256": SCORING_LEDGER_SHA256,
        "scoring_ledger_size": SCORING_LEDGER_SIZE,
        "scoring_ledger_etag": SCORING_LEDGER_ETAG,
        "case_universe_sha256": "c" * 64,
        "row_count": gates["dataset_contract"]["total_cases"],
        "implementation_commit": IMPLEMENTATION,
        "image_digest": IMAGE_DIGEST,
        "config_sha256": CONFIG_SHA256,
    }
    forged = core.bind_metrics_artifacts(metrics, **bindings)
    critical = gates["legacy_comparison_gates"][
        "critical_strict_improvement"
    ]
    denominator = gates["dataset_contract"]["cases_per_stratum"]
    for stratum in critical["strata"]:
        forged["legacy_comparison"]["critical_net_gain_by_stratum"][
            stratum
        ] = core.metric_record(0, denominator)
    forged_critical_gate = core.metric_record(
        critical["minimum_net_gain_in_at_least_one_stratum"],
        denominator,
        comparison=">=",
        threshold=core.Fraction(
            critical["minimum_net_gain_in_at_least_one_stratum"],
            denominator,
        ),
        count_limit=critical["minimum_net_gain_in_at_least_one_stratum"],
        mandatory=True,
    )
    forged["legacy_comparison"][
        "critical_strict_improvement"
    ] = forged_critical_gate
    forged["gates"]["critical_strict_improvement"] = forged_critical_gate

    decision = core.build_decision(
        forged, **bindings, decided_utc=TIMESTAMP
    )
    retirement = core.build_retirement_record(
        decision,
        authorization_id=AUTHORIZATION,
        retired_utc=TIMESTAMP,
    )
    closure = core.build_closure_manifest(
        forged,
        decision,
        retirement,
        scores_manifest_sha256="d" * 64,
        created_utc=TIMESTAMP,
    )
    assert decision["formal_decision"] == "PASS"
    assert decision["metrics_sha256"] == core.sha256_bytes(
        core.canonical_json_bytes(forged)
    )
    assert retirement["decision_sha256"] == core.sha256_bytes(
        core.canonical_json_bytes(decision)
    )
    assert closure["retirement_sha256"] == core.sha256_bytes(
        core.canonical_json_bytes(retirement)
    )
    with pytest.raises(core.LockedEvaluationError, match="critical net gain"):
        core.validate_metrics_artifact(
            forged, gates, require_bindings=True
        )


def test_scoring_transaction_attests_exact_original_score_bytes():
    payloads = {
        name: f"synthetic:{name}\n".encode()
        for name in core.SCORE_MEMBER_NAMES[:-1]
    }
    transaction = core.build_scoring_transaction(
        authorization_id=AUTHORIZATION,
        parent_prefix=PARENT,
        state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"],
        scores_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["scores"],
        scoring_retry_kind="none",
        retry_receipt_sha256=None,
        stage_e_visibility_sha256="d" * 64,
        authorization_lock_sha256="1" * 64,
        authorization_manifest_sha256="2" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_manifest_sha256="3" * 64,
        prediction_seal_sha256="4" * 64,
        prediction_request_manifest_sha256="5" * 64,
        locked_manifest_sha256="6" * 64,
        input_manifest_sha256="7" * 64,
        locked_input_sha256="8" * 64,
        labels_manifest_sha256="9" * 64,
        labels_sha256="a" * 64,
        labels_open_transaction_sha256="b" * 64,
        scoring_ledger_sha256=core.sha256_bytes(
            payloads[core.SCORING_LEDGER_FILENAME]
        ),
        scoring_ledger_size=len(
            payloads[core.SCORING_LEDGER_FILENAME]
        ),
        scoring_ledger_etag='"score-1"',
        case_universe_sha256="c" * 64,
        row_count=120,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        score_payloads=payloads,
        outcome="PASS",
        execution_id="original-scoring-execution",
        actor="synthetic-actor",
        created_utc=TIMESTAMP,
    )
    core.validate_scoring_transaction(transaction, score_payloads=payloads)
    forged_ordinal = deepcopy(transaction)
    forged_ordinal["formal_evaluation_ordinal"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_scoring_transaction(
            forged_ordinal, score_payloads=payloads
        )
    tampered_payloads = dict(payloads)
    tampered_payloads["locked_evaluation_report.md"] += b"private text\n"
    with pytest.raises(core.LockedEvaluationError, match="original"):
        core.validate_scoring_transaction(
            transaction, score_payloads=tampered_payloads
        )

    metadata = [
        {
            "name": name,
            "size": len(payloads[name]),
            "sha256": core.sha256_bytes(payloads[name]),
            "etag": f'"score-{index}"',
        }
        for index, name in enumerate(core.SCORE_MEMBER_NAMES[:-1])
    ]
    manifest = core.build_score_manifest(
        metadata=metadata,
        authorization_id=AUTHORIZATION,
        authorization_lock_sha256="1" * 64,
        authorization_manifest_sha256="2" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        parent_prefix=PARENT,
        scores_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["scores"],
        scoring_retry_kind="none",
        retry_receipt_sha256=None,
        prediction_seal_sha256="4" * 64,
        prediction_manifest_sha256="3" * 64,
        prediction_request_manifest_sha256="5" * 64,
        locked_manifest_sha256="6" * 64,
        input_manifest_sha256="7" * 64,
        locked_input_sha256="8" * 64,
        labels_manifest_sha256="9" * 64,
        labels_manifest_blob_name=(
            f"{PARENT}/locked-labels/locked_labels_manifest.json"
        ),
        labels_manifest_etag='"labels-manifest"',
        labels_blob_name=(
            f"{PARENT}/locked-labels/locked_reference_labels.jsonl"
        ),
        labels_sha256="a" * 64,
        labels_open_transaction_sha256="b" * 64,
        labels_etag='"labels"',
        scoring_ledger_sha256=core.sha256_bytes(
            payloads[core.SCORING_LEDGER_FILENAME]
        ),
        scoring_ledger_size=len(
            payloads[core.SCORING_LEDGER_FILENAME]
        ),
        scoring_ledger_etag='"score-1"',
        case_universe_sha256="c" * 64,
        row_count=120,
        scoring_transaction_sha256=core.sha256_bytes(
            core.canonical_json_bytes(transaction)
        ),
        scoring_execution_id="original-scoring-execution",
        scoring_actor="synthetic-actor",
        stage_e_visibility_sha256="d" * 64,
        stage_e_visibility_etag='"visibility"',
        gate_sha256=core.FROZEN_ACCEPTANCE_GATE_SHA256,
        metrics_sha256=core.sha256_bytes(
            payloads["locked_evaluation_metrics.json"]
        ),
        decision_sha256=core.sha256_bytes(
            payloads["locked_evaluation_decision.json"]
        ),
        retirement_sha256=core.sha256_bytes(
            payloads["retirement_record.json"]
        ),
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        outcome="PASS",
        created_utc=TIMESTAMP,
    )
    manifest_bytes = core.canonical_json_bytes(manifest)
    core.validate_score_manifest(
        manifest_bytes,
        expected_sha256=core.sha256_bytes(manifest_bytes),
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
    )
    forged_payload_metadata = deepcopy(manifest)
    forged_payload_metadata["payload_members"][0]["size"] = True
    forged_payload_metadata_bytes = core.canonical_json_bytes(
        forged_payload_metadata
    )
    with pytest.raises(core.LockedEvaluationError, match="schema is invalid"):
        core.validate_score_manifest(
            forged_payload_metadata_bytes,
            expected_sha256=core.sha256_bytes(
                forged_payload_metadata_bytes
            ),
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
        )
    forged_manifest = deepcopy(manifest)
    forged_manifest["formal_evaluation_count"] = True
    forged_manifest_bytes = core.canonical_json_bytes(forged_manifest)
    with pytest.raises(core.LockedEvaluationError):
        core.validate_score_manifest(
            forged_manifest_bytes,
            expected_sha256=core.sha256_bytes(forged_manifest_bytes),
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
        )
    attestation = core.build_scoring_attestation(
        transaction,
        score_manifest_bytes=manifest_bytes,
        score_manifest_etag='"score-manifest"',
    )
    core.validate_scoring_attestation(
        attestation,
        transaction=transaction,
        score_manifest_bytes=manifest_bytes,
        score_manifest_etag='"score-manifest"',
    )
    forged_ordinal = deepcopy(attestation)
    forged_ordinal["formal_evaluation_ordinal"] = True
    with pytest.raises(core.LockedEvaluationError):
        core.validate_scoring_attestation(
            forged_ordinal,
            transaction=transaction,
            score_manifest_bytes=manifest_bytes,
            score_manifest_etag='"score-manifest"',
        )
    forged = deepcopy(attestation)
    forged["score_manifest_sha256"] = "f" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_scoring_attestation(
            forged,
            transaction=transaction,
            score_manifest_bytes=manifest_bytes,
            score_manifest_etag='"score-manifest"',
        )


@pytest.mark.parametrize(
    "field",
    ("parser_source_sha256", "protocol_bundle_sha256", "parser_version"),
)
def test_source_protocol_and_version_mismatches_fail_before_scoring(
    synthetic_bundle, field
):
    request, seal, request_bytes, predictions_bytes, legacy_bytes = (
        _sealed_public_bundle(synthetic_bundle)
    )
    core.validate_locked_prediction_seal(
        seal,
        request_manifest_bytes=request_bytes,
        predictions_bytes=predictions_bytes,
        legacy_predictions_bytes=legacy_bytes,
        expected_authorization_id=AUTHORIZATION,
        expected_parent_prefix=PARENT,
    )
    broken = deepcopy(seal)
    broken[field] = "9" * 64
    with pytest.raises(core.LockedEvaluationError, match="frozen binding"):
        core.validate_locked_prediction_seal(
            broken,
            request_manifest_bytes=request_bytes,
            predictions_bytes=predictions_bytes,
            legacy_predictions_bytes=legacy_bytes,
            expected_authorization_id=AUTHORIZATION,
            expected_parent_prefix=PARENT,
        )


def test_public_renderer_requires_retirement_and_omits_private_details(
    synthetic_bundle,
):
    metrics, failures = _score(synthetic_bundle)
    decision = core.build_decision(
        metrics,
        authorization_id=AUTHORIZATION,
        registered_parent_prefix=PARENT,
        authorization_lock_sha256="7" * 64,
        authorization_manifest_sha256="8" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_seal_sha256="4" * 64,
        prediction_manifest_sha256="1" * 64,
        prediction_request_manifest_sha256="9" * 64,
        locked_manifest_sha256="5" * 64,
        input_manifest_sha256="a" * 64,
        locked_input_sha256="b" * 64,
        labels_manifest_sha256="6" * 64,
        labels_sha256="2" * 64,
        labels_open_transaction_sha256="3" * 64,
        scores_prefix=core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        scoring_retry_kind="none",
        scoring_execution_id="synthetic-scoring",
        scoring_actor="synthetic-actor",
        stage_e_visibility_sha256="d" * 64,
        retry_receipt_sha256=None,
        scoring_ledger_sha256=SCORING_LEDGER_SHA256,
        scoring_ledger_size=SCORING_LEDGER_SIZE,
        scoring_ledger_etag=SCORING_LEDGER_ETAG,
        case_universe_sha256="c" * 64,
        row_count=120,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        decided_utc=TIMESTAMP,
    )
    with pytest.raises(core.LockedEvaluationError, match="retirement"):
        core.render_public_report(metrics, decision, {})
    retirement = core.build_retirement_record(
        decision,
        authorization_id=AUTHORIZATION,
        retired_utc=TIMESTAMP,
    )
    report = core.render_public_report(metrics, decision, retirement)
    assert b"output_text" not in report
    assert b"registered_reference_answer" not in report
    assert b"PV2-" not in report
    assert f"Mismatched cases: {len(failures)}".encode() in report


def test_cpu_image_and_launch_scaffold_have_no_model_secret_or_gpu_path():
    requirements = (ROOT / "requirements-parser-v2-eval.txt").read_text(
        encoding="utf-8"
    )
    dockerfile = (ROOT / "Dockerfile.parser-v2-eval").read_text(encoding="utf-8")
    launcher = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    assert not re.search(
        r"torch|transformers|cuda|nvidia|safetensors|tensorflow|"
        r"vllm|triton|onnxruntime|deepspeed",
        requirements,
        re.I,
    )
    assert not re.search(r"cuda|nvidia|--gpus", dockerfile, re.I)
    assert "groupadd" not in dockerfile
    assert "useradd" not in dockerfile
    assert "'parser-eval:x:10001:' >> /etc/group" in dockerfile
    assert (
        "'parser-eval:x:10001:10001::/nonexistent:/bin/false'"
        in dockerfile
    )
    assert "scripts/stage_p_entrypoint.sh /workspace/bin/stage-p" in dockerfile
    assert (
        "scripts/stage_p_adopt_entrypoint.sh /workspace/bin/stage-p-adopt"
        in dockerfile
    )
    assert "scripts/stage_e_entrypoint.sh /workspace/bin/stage-e" in dockerfile
    for name in (
        "stage_p_entrypoint.sh",
        "stage_p_adopt_entrypoint.sh",
        "stage_e_entrypoint.sh",
    ):
        entrypoint = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert entrypoint.startswith("#!/bin/bash -p\n")
        assert "exec /usr/bin/env -i" in entrypoint
        assert "unset BASH_ENV ENV CDPATH GLOBIGNORE PYTHONPATH" in entrypoint
        assert "compgen -A function" in entrypoint
        assert "/usr/local/bin/python3.11 -I" in entrypoint
        assert "AZURE_CLIENT_ID=\"$client_id\"" in entrypoint
        assert "IDENTITY_ENDPOINT=\"$identity_endpoint\"" in entrypoint
        assert "IDENTITY_HEADER=\"$identity_header\"" in entrypoint
        assert "PYTHONHASHSEED=0" in entrypoint
        assert not re.search(
            r"model|cuda|nvidia|secret|locked-label", entrypoint, re.I
        )
    assert '"replicaRetryLimit": 0' in launcher
    assert '"resources": {"cpu": 2.0, "memory": "4Gi"}' in launcher
    assert "ManagedIdentityCredential" in CORE_PATH.read_text(encoding="utf-8")
    assert "DefaultAzureCredential" not in CORE_PATH.read_text(encoding="utf-8")
    with pytest.raises(core.LockedEvaluationError, match="model/GPU"):
        core.validate_no_model_gpu_configuration({"MODEL_PATH": "forbidden"})
    with pytest.raises(core.LockedEvaluationError, match="key/SAS"):
        core.validate_managed_identity_configuration(
            "https://storageaccount.blob.core.windows.net",
            {
                "AZURE_CLIENT_ID": "client",
                "AZURE_STORAGE_KEY": "secret",
            },
        )


def test_stage_p_source_manifest_is_exact_label_blind_and_redacted(
    synthetic_bundle,
):
    payload = core.canonical_jsonl_bytes(synthetic_bundle["locked_inputs"])
    ids = [item["case_id"] for item in synthetic_bundle["locked_inputs"]]
    data = _source_manifest_bytes(
        kind="locked-inputs",
        relative_path="locked-inputs/locked_inputs.jsonl",
        payload=payload,
        ordered_case_ids=ids,
    )
    checked = core.validate_locked_source_manifest(
        data,
        expected_manifest_sha256=core.sha256_bytes(data),
        expected_payload_sha256=core.sha256_bytes(payload),
        parent_prefix=PARENT,
        manifest_kind="locked-inputs",
        payload_relative_path="locked-inputs/locked_inputs.jsonl",
        gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
    )
    assert checked["payload_size"] == len(payload)
    assert set(checked) == {
        "manifest_sha256",
        "payload_sha256",
        "payload_size",
        "ordered_case_ids",
    }
    for mutate in (
        lambda value: value["counts"].update({"cases": True}),
        lambda value: value["files"][0].update({"size": True}),
        lambda value: value["files"][1].update(
            {"size": float(value["files"][1]["size"])}
        ),
    ):
        forged = core.parse_json_strict(data, "manifest")
        mutate(forged)
        forged_bytes = core.canonical_json_bytes(forged)
        with pytest.raises(core.LockedEvaluationError):
            core.validate_locked_source_manifest(
                forged_bytes,
                expected_manifest_sha256=core.sha256_bytes(forged_bytes),
                expected_payload_sha256=core.sha256_bytes(payload),
                parent_prefix=PARENT,
                manifest_kind="locked-inputs",
                payload_relative_path="locked-inputs/locked_inputs.jsonl",
                gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
            )

    for mutate, secret in (
        (
            lambda value: value.update(
                {"expected_answer_supersecret": "locked-plaintext-supersecret"}
            ),
            "expected_answer_supersecret",
        ),
        (
            lambda value: value["files"].append(
                {
                    "path": "locked-labels/locked_reference_labels.jsonl",
                    "size": 1,
                    "sha256": "7" * 64,
                }
            ),
            "locked_reference_labels",
        ),
        (
            lambda value: value.update(
                {"metadata_extension": "Y29ycmVjdG5lc3M6dHJ1ZQ=="}
            ),
            "metadata_extension",
        ),
        (
            lambda value: value["feature_counts"].update(
                {"opaque_metadata_b64": 1}
            ),
            "opaque_metadata_b64",
        ),
    ):
        record = core.parse_json_strict(data, "manifest")
        mutate(record)
        adversarial = core.canonical_json_bytes(record)
        with pytest.raises(core.LockedEvaluationError) as caught:
            core.validate_locked_source_manifest(
                adversarial,
                expected_manifest_sha256=core.sha256_bytes(adversarial),
                expected_payload_sha256=core.sha256_bytes(payload),
                parent_prefix=PARENT,
                manifest_kind="locked-inputs",
                payload_relative_path="locked-inputs/locked_inputs.jsonl",
                gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
            )
        assert secret not in str(caught.value)
        assert "locked-plaintext-supersecret" not in str(caught.value)


def test_locked_input_nonce_requires_exact_preregistered_reservation(
    synthetic_bundle,
):
    frozen = core._load_frozen_validation()
    payload = core.canonical_jsonl_bytes(synthetic_bundle["locked_inputs"])
    ids = [item["case_id"] for item in synthetic_bundle["locked_inputs"]]
    reservation = _locked_input_reservation_bytes()
    manifest = _source_manifest_bytes(
        kind="locked-inputs",
        relative_path="locked-inputs/locked_inputs.jsonl",
        payload=payload,
        ordered_case_ids=ids,
    )

    def overall_bytes(input_manifest: bytes) -> bytes:
        files: dict[str, bytes] = {}
        for leaf, names in frozen.REGISTERED_LEAF_MEMBERS.items():
            for name in names:
                relative = f"{leaf}/{name}"
                if relative == "manifests/locked_manifest.json":
                    continue
                if relative == "locked-inputs/.locked_inputs_reservation.json":
                    files[relative] = reservation
                elif relative == "locked-inputs/locked_inputs.jsonl":
                    files[relative] = payload
                elif relative == "locked-inputs/locked_inputs_manifest.json":
                    files[relative] = input_manifest
                else:
                    files[relative] = core.canonical_json_bytes(
                        {"opaque": relative}
                    )
        overall = frozen.build_manifest(
            manifest_kind="manifests",
            project_root=ROOT,
            created_utc=TIMESTAMP,
            parent_prefix=PARENT,
            ordered_case_ids=ids,
            counts={"cases": len(ids)},
            schemas={},
            files=files,
            reservation_sha256=core.sha256_bytes(
                files["manifests/.locked_manifest_reservation.json"]
            ),
            review_seals=[],
            arbitration={"stage1": 0, "stage2": 0, "unresolved": 0},
            feature_counts={},
            visibility_ledger_sha256="a" * 64,
            source_prefixes=["independent/source"],
            private_nonce="independent-overall-private-nonce",
        )
        return core.canonical_json_bytes(overall)

    overall = overall_bytes(manifest)
    checked = core.validate_locked_input_source_binding(
        reservation_bytes=reservation,
        reservation_blob=(
            f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
        ),
        reservation_etag=_fake_blob_etag(reservation),
        manifest_bytes=manifest,
        manifest_blob=f"{PARENT}/locked-inputs/locked_inputs_manifest.json",
        manifest_etag=_fake_blob_etag(manifest),
        locked_manifest_bytes=overall,
        expected_locked_manifest_sha256=core.sha256_bytes(overall),
        expected_manifest_sha256=core.sha256_bytes(manifest),
        expected_payload_sha256=core.sha256_bytes(payload),
        parent_prefix=PARENT,
        gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
    )
    assert checked["binding"]["locked_input_reservation_sha256"] == (
        core.sha256_bytes(reservation)
    )
    assert checked["binding"]["locked_input_private_nonce_sha256"] == (
        _locked_input_private_nonce_sha256()
    )

    forged_record = core.parse_json_strict(manifest, "locked input manifest")
    forged_record["private_nonce"] = base64.b64encode(
        b"correctness:true-without-preregistered-reservation"
    ).decode("ascii")
    forged_manifest = core.canonical_json_bytes(forged_record)
    core.validate_locked_source_manifest(
        forged_manifest,
        expected_manifest_sha256=core.sha256_bytes(forged_manifest),
        expected_payload_sha256=core.sha256_bytes(payload),
        parent_prefix=PARENT,
        manifest_kind="locked-inputs",
        payload_relative_path="locked-inputs/locked_inputs.jsonl",
        gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
    )
    forged_overall = overall_bytes(forged_manifest)
    with pytest.raises(core.LockedEvaluationError, match="preregistered"):
        core.validate_locked_input_source_binding(
            reservation_bytes=reservation,
            reservation_blob=(
                f"{PARENT}/locked-inputs/.locked_inputs_reservation.json"
            ),
            reservation_etag=_fake_blob_etag(reservation),
            manifest_bytes=forged_manifest,
            manifest_blob=(
                f"{PARENT}/locked-inputs/locked_inputs_manifest.json"
            ),
            manifest_etag=_fake_blob_etag(forged_manifest),
            locked_manifest_bytes=forged_overall,
            expected_locked_manifest_sha256=core.sha256_bytes(forged_overall),
            expected_manifest_sha256=core.sha256_bytes(forged_manifest),
            expected_payload_sha256=core.sha256_bytes(payload),
            parent_prefix=PARENT,
            gates=core.load_acceptance_gates(synthetic_bundle["gates"]),
        )


def test_schema_and_stage_p_top_level_errors_never_echo_untrusted_data(
    monkeypatch, capsys,
):
    secret_key = "expected_answer_extremely_secret"
    secret_value = "LOCKED-PLAINTEXT-DO-NOT-ECHO"
    with pytest.raises(core.LockedEvaluationError) as caught:
        core._require_exact_fields(
            {secret_key: secret_value}, {"safe"}, "synthetic artifact"
        )
    assert secret_key not in str(caught.value)
    assert secret_value not in str(caught.value)

    monkeypatch.setattr(runner, "_load_core", lambda: core)
    monkeypatch.setattr(
        runner,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda raw: SimpleNamespace(raw=raw)
        ),
    )

    def fail_stage_p(*args, **kwargs):
        del args, kwargs
        raise core.LockedEvaluationError(
            f"{secret_key}={secret_value}"
        )

    monkeypatch.setattr(runner, "run_stage_p", fail_stage_p)
    assert runner.main(["--safe-channel"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert secret_key not in captured.err
    assert secret_value not in captured.err
    assert captured.err.strip() == (
        "STAGE_P_ERROR:EXECUTION_REJECTED:LockedEvaluationError"
    )


def test_stage_public_status_output_is_aggregate_only(monkeypatch, capsys):
    secret = "RAW-PRIVATE-BLOB-PAYLOAD"
    monkeypatch.setattr(runner, "_load_core", lambda: core)
    monkeypatch.setattr(
        runner,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda raw: SimpleNamespace(raw=raw)
        ),
    )
    monkeypatch.setattr(
        runner,
        "run_stage_p",
        lambda *args, **kwargs: {
            "stage": "P",
            "status": "PREDICTIONS_VERIFIED",
            "input_count": 120,
            "parser_v2_prediction_count": 120,
            "legacy_prediction_count": 120,
            "private_payload": secret,
            "authorization_id": AUTHORIZATION,
        },
    )
    assert runner.main(["--safe"]) == 0
    stage_p_output = capsys.readouterr()
    assert secret not in stage_p_output.out
    assert AUTHORIZATION not in stage_p_output.out
    assert set(json.loads(stage_p_output.out)) == {
        "stage",
        "status",
        "input_count",
        "parser_v2_prediction_count",
        "legacy_prediction_count",
        "labels_accessed",
    }

    monkeypatch.setattr(finalizer, "_load_core", lambda: core)
    monkeypatch.setattr(
        finalizer,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda raw: SimpleNamespace(raw=raw)
        ),
    )
    monkeypatch.setattr(
        finalizer,
        "run_stage_e",
        lambda *args, **kwargs: {
            "stage": "E",
            "status": "PASS",
            "formal_evaluation_count": 1,
            "holdout_retired": True,
            "private_payload": secret,
            "authorization_id": AUTHORIZATION,
        },
    )
    assert finalizer.main(["--safe"]) == 0
    stage_e_output = capsys.readouterr()
    assert secret not in stage_e_output.out
    assert AUTHORIZATION not in stage_e_output.out
    assert set(json.loads(stage_e_output.out)) == {
        "stage",
        "status",
        "formal_evaluation_count",
        "holdout_retired",
        "parser_rerun",
    }


def test_stage_e_subprocess_blocks_dynamic_alias_parser_loading(workdir):
    exploit = workdir / "alias_exploit.py"
    exploit.write_text(
        "import importlib.util,importlib.machinery,sys\n"
        "captured_spec=importlib.util.spec_from_file_location\n"
        "captured_loader=importlib.machinery.SourceFileLoader\n"
        "spec=importlib.util.spec_from_file_location('_finalizer',sys.argv[1])\n"
        "module=importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "module._load_core()\n"
        "blocked=[]\n"
        "try:\n"
        " captured_spec('innocent_alias',sys.argv[2])\n"
        "except ImportError:\n"
        " blocked.append('spec')\n"
        "try:\n"
        " captured_loader('innocent_alias_2',sys.argv[2])\n"
        "except ImportError:\n"
        " blocked.append('loader')\n"
        "raise SystemExit(0 if blocked==['spec','loader'] else 9)\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(exploit),
            str(ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py"),
            str(ROOT / "src" / "jspace_observation" / "eval_parsing_v2.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_stage_e_subprocess_blocks_runpy_saved_loaders_source_and_interpreters(
    workdir,
):
    exploit = workdir / "stage_e_bypass_matrix.py"
    exploit.write_text(
        "import importlib.machinery,importlib.util,os,pathlib,runpy,"
        "subprocess,sys\n"
        "finalizer_path=pathlib.Path(sys.argv[1])\n"
        "parser_path=pathlib.Path(sys.argv[2])\n"
        "source=parser_path.read_bytes()\n"
        "compiled=compile(source,'renamed_safe_source.py','exec')\n"
        "saved_run_path=runpy.run_path\n"
        "saved_spec_factory=importlib.util.spec_from_file_location\n"
        "saved_loader_class=importlib.machinery.SourceFileLoader\n"
        "saved_run=subprocess.run\n"
        "saved_popen=subprocess.Popen\n"
        "pre_spec=saved_spec_factory('_pre_parser',parser_path)\n"
        "pre_module=importlib.util.module_from_spec(pre_spec)\n"
        "saved_spec_exec=pre_spec.loader.exec_module\n"
        "saved_get_code=pre_spec.loader.get_code\n"
        "pre_loader=saved_loader_class('_pre_loader',str(parser_path))\n"
        "pre_loader_spec=importlib.util.spec_from_loader("
        "'_pre_loader',pre_loader)\n"
        "pre_loader_module=importlib.util.module_from_spec(pre_loader_spec)\n"
        "saved_loader_exec=pre_loader.exec_module\n"
        "spec=saved_spec_factory('_stage_e_finalizer',finalizer_path)\n"
        "module=importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "module._load_core()\n"
        "attempts={\n"
        " 'runpy':lambda:saved_run_path(str(parser_path)),\n"
        " 'saved_spec_exec':lambda:saved_spec_exec(pre_module),\n"
        " 'saved_get_code':lambda:saved_get_code('_pre_parser'),\n"
        " 'saved_loader_exec':lambda:saved_loader_exec(pre_loader_module),\n"
        " 'captured_spec':lambda:saved_spec_factory('_alias',parser_path),\n"
        " 'captured_loader':lambda:saved_loader_class('_alias2',"
        "str(parser_path)),\n"
        " 'direct_source':lambda:exec(source,{}),\n"
        " 'precompiled_source':lambda:exec(compiled,{}),\n"
        " 'saved_run':lambda:saved_run([sys.executable,'-c','print(1)']),\n"
        " 'saved_popen':lambda:saved_popen([sys.executable,'-c','print(1)']),\n"
        " 'stage_p_exec':lambda:saved_run(['/workspace/bin/stage-p']),\n"
        " 'renamed_exec':lambda:saved_run(['innocent-runtime-copy']),\n"
        " 'system':lambda:os.system('python -c \"print(1)\"'),\n"
        "}\n"
        "blocked=[]\n"
        "for name,attempt in attempts.items():\n"
        " try:\n"
        "  attempt()\n"
        " except (ImportError,PermissionError,RuntimeError):\n"
        "  blocked.append(name)\n"
        "raise SystemExit(0 if blocked==list(attempts) else 9)\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(exploit),
            str(ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py"),
            str(ROOT / "src" / "jspace_observation" / "eval_parsing.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_parser_result_validation_is_broadly_differential(synthetic_bundle):
    frozen = synthetic_bundle["frozen"]
    comparisons = 0
    for prediction, locked in zip(
        synthetic_bundle["predictions"],
        synthetic_bundle["locked_inputs"],
        strict=True,
    ):
        result = prediction["parser_result"]
        variants = [deepcopy(result)]
        if locked["output_text"].strip():
            bad_empty = deepcopy(result)
            bad_empty["output_quality"] = "empty"
            variants.append(bad_empty)
        extra = deepcopy(result)
        extra["untrusted_extra"] = "secret"
        variants.append(extra)
        if result["answer_presence"] == "present":
            bad_present = deepcopy(result)
            bad_present["evidence_spans"][0][
                "disposition"
            ] = "ambiguous_candidate"
            variants.append(bad_present)
        elif result["answer_presence"] == "uncertain":
            bad_ambiguous = deepcopy(result)
            bad_ambiguous["evidence_spans"][0]["disposition"] = "selected"
            variants.append(bad_ambiguous)
        else:
            bad_absent = deepcopy(result)
            bad_absent["parse_valid"] = True
            variants.append(bad_absent)
        for variant in variants:
            try:
                frozen.validate_parser_result(
                    variant, locked["output_text"]
                )
                frozen_accepts = True
            except frozen.ValidationSetError:
                frozen_accepts = False
            try:
                core.validate_parser_result(
                    variant, locked["output_text"]
                )
                core_accepts = True
            except core.LockedEvaluationError:
                core_accepts = False
            assert core_accepts is frozen_accepts
            comparisons += 1
    assert comparisons >= 400


def test_s06_requires_distinct_exact_rightmost_numeric_distractor(
    synthetic_bundle,
):
    frozen = synthetic_bundle["frozen"]
    label = deepcopy(_labels(synthetic_bundle, stratum="S06")[0])
    registered = label["last_number_distractor_span"]
    assert (
        core.normalize_rational_literal(registered["text"])
        != label["expected_parsed_answer"]
    )
    alternative = label["acceptable_selected_spans"][0]
    assert (alternative["start"], alternative["end"]) != (
        registered["start"],
        registered["end"],
    )
    start, end, text = (
        alternative["start"],
        alternative["end"],
        alternative["text"],
    )
    label["last_number_distractor_span"] = {
        "start": start,
        "end": end,
        "text": text,
    }
    with pytest.raises(frozen.ValidationSetError):
        frozen.validate_final_label(label)
    with pytest.raises(core.LockedEvaluationError):
        core.validate_final_label(
            label,
            core.load_acceptance_gates(synthetic_bundle["gates"]),
            name="S06 label",
        )


def test_decision_retirement_and_closure_reject_forgery_and_cross_auth():
    gate = core.metric_record(
        0,
        1,
        comparison=">=",
        threshold=core.Fraction(1),
        mandatory=True,
    )
    metrics = {"status": "FAIL", "gates": {"synthetic": gate}}
    metrics = core.bind_metrics_artifacts(
        metrics,
        authorization_id=AUTHORIZATION,
        registered_parent_prefix=PARENT,
        authorization_lock_sha256="7" * 64,
        authorization_manifest_sha256="8" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_seal_sha256="1" * 64,
        prediction_manifest_sha256="2" * 64,
        prediction_request_manifest_sha256="9" * 64,
        locked_manifest_sha256="3" * 64,
        input_manifest_sha256="a" * 64,
        locked_input_sha256="b" * 64,
        labels_manifest_sha256="4" * 64,
        labels_sha256="5" * 64,
        labels_open_transaction_sha256="6" * 64,
        scores_prefix=core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        scoring_retry_kind="none",
        scoring_execution_id="synthetic-scoring",
        scoring_actor="synthetic-actor",
        stage_e_visibility_sha256="d" * 64,
        retry_receipt_sha256=None,
        scoring_ledger_sha256=SCORING_LEDGER_SHA256,
        scoring_ledger_size=SCORING_LEDGER_SIZE,
        scoring_ledger_etag=SCORING_LEDGER_ETAG,
        case_universe_sha256="c" * 64,
        row_count=120,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
    )
    decision = core.build_decision(
        metrics,
        authorization_id=AUTHORIZATION,
        registered_parent_prefix=PARENT,
        authorization_lock_sha256="7" * 64,
        authorization_manifest_sha256="8" * 64,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        prediction_seal_sha256="1" * 64,
        prediction_manifest_sha256="2" * 64,
        prediction_request_manifest_sha256="9" * 64,
        locked_manifest_sha256="3" * 64,
        input_manifest_sha256="a" * 64,
        locked_input_sha256="b" * 64,
        labels_manifest_sha256="4" * 64,
        labels_sha256="5" * 64,
        labels_open_transaction_sha256="6" * 64,
        scores_prefix=core.evaluation_prefixes(
            PARENT, AUTHORIZATION
        )["scores"],
        scoring_retry_kind="none",
        scoring_execution_id="synthetic-scoring",
        scoring_actor="synthetic-actor",
        stage_e_visibility_sha256="d" * 64,
        retry_receipt_sha256=None,
        scoring_ledger_sha256=SCORING_LEDGER_SHA256,
        scoring_ledger_size=SCORING_LEDGER_SIZE,
        scoring_ledger_etag=SCORING_LEDGER_ETAG,
        case_universe_sha256="c" * 64,
        row_count=120,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        decided_utc=TIMESTAMP,
    )
    forged = deepcopy(decision)
    forged["formal_decision"] = "PASS"
    with pytest.raises(core.LockedEvaluationError):
        core.validate_decision(metrics, forged)
    for field in (
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
    ):
        forged_binding = deepcopy(decision)
        forged_binding[field] = "9" * 64
        with pytest.raises(core.LockedEvaluationError):
            core.validate_decision(metrics, forged_binding)
    with pytest.raises(core.LockedEvaluationError):
        core.build_retirement_record(
            decision,
            authorization_id="different-authorization",
            retired_utc=TIMESTAMP,
        )
    retirement = core.build_retirement_record(
        decision,
        authorization_id=AUTHORIZATION,
        retired_utc=TIMESTAMP,
    )
    cross = deepcopy(retirement)
    cross["authorization_id"] = "different-authorization"
    with pytest.raises(core.LockedEvaluationError):
        core.validate_retirement_record(decision, cross)
    forged_retirement = deepcopy(retirement)
    forged_retirement["labels_open_transaction_sha256"] = "9" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_retirement_record(decision, forged_retirement)


def test_full_frozen_state_graph_lock_forks_and_exact_retries():
    chain = _state_chain_until("UNSEAL_AUTHORIZED")
    lock = _authorization_lock(chain)
    with pytest.raises(
        core.LockedEvaluationError, match="persisted authorization manifest"
    ):
        core.validate_state_receipt_graph(
            chain,
            authorization_lock=lock,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )
    result = core.validate_state_receipt_graph(
        chain,
        authorization_lock=lock,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        authorization_manifest_bytes=_authorization_manifest_bytes(chain),
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"],
    )
    assert result["state"] == "UNSEAL_AUTHORIZED"
    assert [item["state"] for item in chain] == list(
        core.HOLDOUT_STATE_SEQUENCE[
            : core.HOLDOUT_STATE_SEQUENCE.index("UNSEAL_AUTHORIZED") + 1
        ]
    )
    for receipt in chain:
        expected = set().union(
            *(
                core.STATE_AUTHORIZED_ARTIFACT_BINDINGS[state]
                for state in core.HOLDOUT_STATE_SEQUENCE[
                    : core.HOLDOUT_STATE_SEQUENCE.index(receipt["state"]) + 1
                ]
            )
        )
        assert set(receipt["artifact_manifest_hashes"]) == expected

    forged_lock = deepcopy(lock)
    forged_lock["visibility_sha256"] = "f" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_state_receipt_graph(
            chain,
            authorization_lock=forged_lock,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            authorization_manifest_bytes=_authorization_manifest_bytes(chain),
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            state_prefix=core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"],
        )

    fork = deepcopy(chain[1])
    fork["execution_id"] = "forked-execution"
    fork["timestamp_utc"] = "2026-07-20T05:46:01Z"
    with pytest.raises(core.LockedEvaluationError, match="forked"):
        core.validate_state_receipt_graph([chain[0], chain[1], fork])

    retry = core.build_retry_state_receipt(
        chain[-1],
        retry_kind="infrastructure_pre_input",
        timestamp_utc="2026-07-20T05:47:00Z",
        execution_id="retry-one",
        actor="synthetic-actor",
        visibility=["retry"],
        history=chain,
        authorization_lock=lock,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    assert retry["artifact_manifest_hashes"] == chain[-1][
        "artifact_manifest_hashes"
    ]
    with pytest.raises(core.LockedEvaluationError):
        core.build_retry_state_receipt(
            retry,
            retry_kind="infrastructure_pre_input",
            timestamp_utc="2026-07-20T05:48:00Z",
            execution_id="retry-two",
            actor="synthetic-actor",
            visibility=["retry"],
            history=[*chain, retry],
            authorization_lock=lock,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )

    predictions_chain = _state_chain_until("PREDICTIONS_VERIFIED")
    scorer_retry = core.build_retry_state_receipt(
        predictions_chain[-1],
        retry_kind="scorer_infrastructure",
        timestamp_utc="2026-07-20T05:49:00Z",
        execution_id="scorer-retry",
        actor="synthetic-actor",
        visibility=["retry"],
        history=predictions_chain,
        authorization_lock=_authorization_lock(predictions_chain),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    assert scorer_retry["state"] == "PREDICTIONS_VERIFIED"

    labels_chain = _state_chain_until("LABELS_READ")
    with pytest.raises(
        core.LockedEvaluationError, match="timestamp regresses"
    ):
        core.build_retry_state_receipt(
            labels_chain[-1],
            retry_kind="verification_only",
            timestamp_utc="2026-07-20T05:45:00Z",
            execution_id="regressed-verification-retry",
            actor="synthetic-actor",
            visibility=["retry"],
            history=labels_chain,
            authorization_lock=_authorization_lock(labels_chain),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )
    verification_retry = core.build_retry_state_receipt(
        labels_chain[-1],
        retry_kind="verification_only",
        timestamp_utc="2026-07-20T05:50:00Z",
        execution_id="verification-retry",
        actor="synthetic-actor",
        visibility=["retry"],
        history=labels_chain,
        authorization_lock=_authorization_lock(labels_chain),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    assert verification_retry["artifact_manifest_hashes"] == labels_chain[-1][
        "artifact_manifest_hashes"
    ]

    regressed_chain = _state_chain_until("PREDICTIONS_VERIFIED")
    regressed_chain[-1]["timestamp_utc"] = "2026-07-20T05:44:59Z"
    frozen = core._load_frozen_validation()
    frozen.validate_state_receipt_chain(
        regressed_chain,
        authorization_lock=_authorization_lock(regressed_chain),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
    )
    with pytest.raises(
        core.LockedEvaluationError, match="timestamp regresses"
    ):
        core.validate_state_receipt_chain(
            regressed_chain,
            authorization_lock=_authorization_lock(regressed_chain),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )


def test_stage_p_authenticates_real_lock_graph_and_rejects_hash_only_or_extras():
    service = _FakeService()
    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    chain = _state_chain_until("UNSEAL_AUTHORIZED")
    lock = _authorization_lock(chain)
    for receipt in chain:
        service.preload(
            f"{prefixes['state']}/{core.STATE_RECEIPT_FILENAMES[receipt['state']]}",
            core.canonical_json_bytes(receipt),
        )
    service.preload(
        f"{prefixes['state']}/{core.IMPLEMENTATION_MANIFEST_FILENAME}",
        IMPLEMENTATION_MANIFEST_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.RUNTIME_CONFIG_FILENAME}",
        RUNTIME_CONFIG_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.AUTHORIZATION_MANIFEST_FILENAME}",
        _authorization_manifest_bytes(chain),
    )
    service.preload(
        core.authorization_lock_blob_name(lock),
        core.canonical_json_bytes(lock),
    )
    authorization_manifest_blob = (
        f"{prefixes['state']}/{core.AUTHORIZATION_MANIFEST_FILENAME}"
    )
    authorization_manifest_bytes = service.data.pop(
        authorization_manifest_blob
    )
    authorization_manifest_etag = service.etags.pop(
        authorization_manifest_blob
    )
    with pytest.raises(core.LockedEvaluationError, match="incomplete"):
        core.authenticate_authorization_bundle(
            service,
            "synthetic-container",
            project_root=ROOT,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            state_prefix=prefixes["state"],
            implementation_commit=IMPLEMENTATION,
            image_digest=IMAGE_DIGEST,
            config_sha256=CONFIG_SHA256,
        )
    service.data[authorization_manifest_blob] = authorization_manifest_bytes
    service.etags[authorization_manifest_blob] = authorization_manifest_etag
    with pytest.raises(core.LockedEvaluationError):
        core.authenticate_authorization_bundle(
            service,
            "synthetic-container",
            project_root=ROOT,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            state_prefix=prefixes["state"],
            implementation_commit=IMPLEMENTATION,
            image_digest=IMAGE_DIGEST,
            config_sha256=CONFIG_SHA256,
            launcher_sha256=LAUNCHER_SHA256,
            launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
            expected_prior_receipt_sha256=core.state_receipt_sha256(chain[-1]),
            expected_authorization_lock_sha256="f" * 64,
        )
    checked = core.authenticate_authorization_bundle(
        service,
        "synthetic-container",
        project_root=ROOT,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        state_prefix=prefixes["state"],
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        config_sha256=CONFIG_SHA256,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        expected_prior_receipt_sha256=core.state_receipt_sha256(chain[-1]),
        expected_authorization_lock_sha256=core.authorization_lock_sha256(lock),
    )
    assert checked["holdout_id"] == lock["holdout_id"]
    service.preload(f"{prefixes['state']}/unexpected.json", b"{}\n")
    with pytest.raises(core.LockedEvaluationError, match="unexpected object"):
        core.authenticate_authorization_bundle(
            service,
            "synthetic-container",
            project_root=ROOT,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            state_prefix=prefixes["state"],
            implementation_commit=IMPLEMENTATION,
            image_digest=IMAGE_DIGEST,
            config_sha256=CONFIG_SHA256,
        )


def test_authorization_manifest_is_a_persisted_real_lock_artifact():
    chain = _state_chain_until("UNSEAL_AUTHORIZED")
    implementation = chain[
        core.HOLDOUT_STATE_SEQUENCE.index("IMPLEMENTATION_FROZEN")
    ]
    lock = _authorization_lock(chain)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    data = _authorization_manifest_bytes(chain)
    manifest = core.parse_json_strict(data, "authorization manifest")
    assert manifest["locked_input_private_nonce_sha256"] == (
        _locked_input_private_nonce_sha256()
    )
    service = _FakeService()
    persistence = core.persist_authorization_manifest(
        service,
        "synthetic-container",
        state_prefix,
        manifest,
        implementation_receipt=implementation,
        authorization_lock=lock,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
    )
    assert persistence["sha256"] == chain[-1]["artifact_manifest_hashes"][
        "authorization_manifest"
    ]
    forged = deepcopy(manifest)
    forged["authorization_lock_sha256"] = "9" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_authorization_manifest(
            core.canonical_json_bytes(forged),
            implementation_receipt=implementation,
            authorization_lock=lock,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            state_prefix=state_prefix,
        )
    forged = deepcopy(manifest)
    forged["locked_input_private_nonce_sha256"] = "8" * 64
    with pytest.raises(core.LockedEvaluationError):
        core.validate_state_receipt_graph(
            chain,
            authorization_lock=lock,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            authorization_manifest_bytes=core.canonical_json_bytes(forged),
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            state_prefix=state_prefix,
        )


def test_bootstrap_latest_authenticates_the_actual_advanced_state(monkeypatch):
    service = _FakeService()
    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    chain = _state_chain_until("INPUTS_READ")
    lock = _authorization_lock(chain)
    for receipt in chain:
        service.preload(
            (
                f"{prefixes['state']}/"
                f"{core.STATE_RECEIPT_FILENAMES[receipt['state']]}"
            ),
            core.canonical_json_bytes(receipt),
        )
    authorization_manifest = _authorization_manifest_bytes(chain)
    service.preload(
        f"{prefixes['state']}/{core.IMPLEMENTATION_MANIFEST_FILENAME}",
        IMPLEMENTATION_MANIFEST_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.RUNTIME_CONFIG_FILENAME}",
        RUNTIME_CONFIG_BYTES,
    )
    service.preload(
        f"{prefixes['state']}/{core.AUTHORIZATION_MANIFEST_FILENAME}",
        authorization_manifest,
    )
    service.preload(
        core.authorization_lock_blob_name(lock),
        core.canonical_json_bytes(lock),
    )
    monkeypatch.setattr(
        bootstrap,
        "_git_source_bindings",
        lambda _commit: _runtime_source_bindings(),
    )
    monkeypatch.setattr(
        core,
        "validate_private_endpoint_resolution",
        lambda *_args, **_kwargs: ("10.0.2.4",),
    )
    monkeypatch.setattr(core, "create_blob_service", lambda _url: service)
    result = bootstrap._authenticate_persisted(
        core,
        runtime=core.parse_json_strict(RUNTIME_CONFIG_BYTES, "runtime"),
        runtime_bytes=RUNTIME_CONFIG_BYTES,
        implementation=core.validate_implementation_manifest(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        implementation_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        runtime_sha256=CONFIG_SHA256,
        implementation_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        image_binding_bytes=IMAGE_BINDING_BYTES,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        final_state="LATEST",
        prior_receipt_sha256=None,
        authorization_lock_sha256=core.authorization_lock_sha256(lock),
        authorization_manifest_sha256=core.sha256_bytes(
            authorization_manifest
        ),
    )
    assert result["state"] == "INPUTS_READ"
    assert result["prior_state_receipt_sha256"] == core.state_receipt_sha256(
        chain[-1]
    )
    service.preload(
        f"{prefixes['predictions']}/forged-early-member.json",
        b"{}\n",
    )
    with pytest.raises(
        core.LockedEvaluationError,
        match="authorization-scoped Blob membership|pending prediction producer",
    ):
        bootstrap._authenticate_persisted(
            core,
            runtime=core.parse_json_strict(RUNTIME_CONFIG_BYTES, "runtime"),
            runtime_bytes=RUNTIME_CONFIG_BYTES,
            implementation=core.validate_implementation_manifest(
                IMPLEMENTATION_MANIFEST_BYTES
            ),
            implementation_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            runtime_sha256=CONFIG_SHA256,
            implementation_sha256=core.sha256_bytes(
                IMPLEMENTATION_MANIFEST_BYTES
            ),
            image_binding_bytes=IMAGE_BINDING_BYTES,
            image_binding_sha256=IMAGE_BINDING_SHA256,
            helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
            final_state="LATEST",
            prior_receipt_sha256=None,
            authorization_lock_sha256=core.authorization_lock_sha256(lock),
            authorization_manifest_sha256=core.sha256_bytes(
                authorization_manifest
            ),
        )


def _seed_manifest_only_registered_parent(
    service: _FakeService, synthetic_bundle: Mapping[str, Any]
) -> set[str]:
    frozen = core._load_frozen_validation()
    ids = [item["case_id"] for item in synthetic_bundle["locked_inputs"]]
    files: dict[str, bytes] = {}
    manifest_bytes: dict[str, bytes] = {}
    for leaf in ("development", "locked-inputs", "locked-labels", "reports"):
        names = frozen.REGISTERED_LEAF_MEMBERS[leaf]
        for name in names[:-1]:
            relative = f"{leaf}/{name}"
            if name == names[0]:
                files[relative] = core.canonical_json_bytes(
                    {
                        "schema_version": frozen.RESERVATION_SCHEMA_VERSION,
                        "leaf": leaf,
                        "parent_prefix": PARENT,
                        "created_utc": TIMESTAMP,
                        "private_nonce": f"manifest-only-{leaf}",
                    }
                )
            elif name.endswith(".jsonl"):
                files[relative] = b'{"opaque":"not-downloaded"}\n'
            elif name.endswith(".md"):
                files[relative] = b"synthetic aggregate report\n"
            else:
                files[relative] = core.canonical_json_bytes(
                    {"leaf": leaf, "name": name}
                )
        ordered = (
            ids
            if leaf in {"locked-inputs", "locked-labels"}
            else ids[:60]
            if leaf == "development"
            else []
        )
        schemas = (
            {"locked_inputs": core.LOCKED_INPUT_SCHEMA_VERSION}
            if leaf == "locked-inputs"
            else {"final_labels": core.FINAL_LABEL_SCHEMA_VERSION}
            if leaf == "locked-labels"
            else {}
        )
        manifest = frozen.build_manifest(
            manifest_kind=leaf,
            project_root=ROOT,
            created_utc=TIMESTAMP,
            parent_prefix=PARENT,
            ordered_case_ids=ordered,
            counts={"cases": len(ordered)},
            schemas=schemas,
            files={
                f"{leaf}/{name}": files[f"{leaf}/{name}"]
                for name in names[:-1]
            },
            reservation_sha256=core.sha256_bytes(
                files[f"{leaf}/{names[0]}"]
            ),
            review_seals=[],
            arbitration={"stage1": 0, "stage2": 0, "unresolved": 0},
            feature_counts={},
            visibility_ledger_sha256="a" * 64,
            source_prefixes=["synthetic/source"],
            private_nonce=f"manifest-only-{leaf}",
        )
        path = f"{leaf}/{names[-1]}"
        manifest_bytes[leaf] = core.canonical_json_bytes(manifest)
        files[path] = manifest_bytes[leaf]

    manifest_names = frozen.REGISTERED_LEAF_MEMBERS["manifests"]
    for name in manifest_names[:-1]:
        path = f"manifests/{name}"
        files[path] = (
            core.canonical_json_bytes(
                {
                    "schema_version": frozen.RESERVATION_SCHEMA_VERSION,
                    "leaf": "manifests",
                    "parent_prefix": PARENT,
                    "created_utc": TIMESTAMP,
                    "private_nonce": "manifest-only-overall",
                }
            )
            if name == manifest_names[0]
            else core.canonical_json_bytes(
                {"leaf": "manifests", "name": name}
            )
        )
    overall = frozen.build_manifest(
        manifest_kind="manifests",
        project_root=ROOT,
        created_utc=TIMESTAMP,
        parent_prefix=PARENT,
        ordered_case_ids=[],
        counts={"cases": 0},
        schemas={},
        files={
            f"{leaf}/{name}": files[f"{leaf}/{name}"]
            for leaf, names in frozen.REGISTERED_LEAF_MEMBERS.items()
            for name in names
            if not (
                leaf == "manifests"
                and name == frozen.REGISTERED_LEAF_MEMBERS["manifests"][-1]
            )
        },
        reservation_sha256=core.sha256_bytes(
            files[f"manifests/{manifest_names[0]}"]
        ),
        review_seals=[],
        arbitration={"stage1": 0, "stage2": 0, "unresolved": 0},
        feature_counts={},
        visibility_ledger_sha256="a" * 64,
        source_prefixes=["synthetic/source"],
        private_nonce="manifest-only-overall",
    )
    files[f"manifests/{manifest_names[-1]}"] = core.canonical_json_bytes(
        overall
    )
    expected = set()
    for relative, data in files.items():
        blob = f"{PARENT}/{relative}"
        service.preload(blob, data)
        expected.add(blob)
    assert expected == set(frozen.expected_parent_membership(PARENT))
    return expected


def test_custodian_bootstrap_is_manifest_only_and_authenticates_full_chain(
    synthetic_bundle, monkeypatch
):
    monkeypatch.setattr(
        bootstrap,
        "_git_source_bindings",
        lambda _commit: _runtime_source_bindings(),
    )
    service = _FakeService()
    frozen_parent = _seed_manifest_only_registered_parent(
        service, synthetic_bundle
    )
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        expected_private_endpoint_ip="10.0.0.4",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        state_prefix=state_prefix,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        runtime_config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        execution_id="custodian-bootstrap",
        actor="synthetic-custodian",
    )
    with pytest.raises(core.LockedEvaluationError, match="custodian"):
        bootstrap.run_bootstrap(
            args,
            service=service,
            core=core,
            now=lambda: "2026-07-20T06:00:00Z",
            custodian_authorized=False,
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            image_binding_bytes=IMAGE_BINDING_BYTES,
        )
    event_start = len(service.events)
    result = bootstrap.run_bootstrap(
        args,
        service=service,
        core=core,
        now=lambda: "2026-07-20T06:00:00Z",
        custodian_authorized=True,
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        image_binding_bytes=IMAGE_BINDING_BYTES,
    )
    assert result["status"] == "UNSEAL_AUTHORIZED"
    assert result["locked_input_payload_read"] is False
    assert result["locked_labels_payload_read"] is False
    bootstrap_uploads = [
        event
        for event in service.events[event_start:]
        if event[0] == "upload"
    ]
    assert bootstrap_uploads[0][1] == result["authorization_lock_blob"]
    assert not bootstrap_uploads[0][1].startswith(f"{state_prefix}/")
    manifest_downloads = {
        event[1]
        for event in service.events[event_start:]
        if event[0] == "download" and event[1] in frozen_parent
    }
    assert manifest_downloads == {
        f"{PARENT}/development/development_manifest.json",
        f"{PARENT}/locked-inputs/.locked_inputs_reservation.json",
        f"{PARENT}/locked-inputs/locked_inputs_manifest.json",
        f"{PARENT}/locked-labels/locked_labels_manifest.json",
        f"{PARENT}/reports/reports_manifest.json",
        f"{PARENT}/manifests/locked_manifest.json",
    }
    assert not any(
        event[0] == "download"
        and (
            event[1].endswith("locked_inputs.jsonl")
            or event[1].endswith("locked_reference_labels.jsonl")
            or "reviewer_" in event[1]
            or "arbitration_" in event[1]
        )
        for event in service.events[event_start:]
    )
    state_members = core._authorization_state_members(
        state_prefix, final_state="UNSEAL_AUTHORIZED"
    )
    assert core.list_exact_prefix(
        service, args.container, state_prefix
    ) == state_members
    core.validate_registered_parent_membership(
        service,
        args.container,
        PARENT,
        core.expected_registered_parent_membership(PARENT, state_members),
    )
    rerun_start = len(service.events)
    rerun = bootstrap.run_bootstrap(
        args,
        service=service,
        core=core,
        now=lambda: "2026-07-21T06:00:00Z",
        custodian_authorized=True,
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        image_binding_bytes=IMAGE_BINDING_BYTES,
    )
    assert rerun["unseal_receipt_sha256"] == result["unseal_receipt_sha256"]
    assert not any(
        event[0] == "upload" for event in service.events[rerun_start:]
    )


def test_bootstrap_competing_lock_wins_before_authorization_prefix_writes(
    synthetic_bundle, monkeypatch
):
    class CompetingLockBlob(_FakeBlob):
        def upload_blob(self, data, overwrite):
            if self.name.startswith(
                f"{core.AUTHORIZATION_LOCK_BLOB_PREFIX}/"
            ):
                attempted = bytes(data)
                self.service.attempted_lock_bytes = attempted
                self.service.events.append(("upload", self.name, overwrite))
                competing = core.parse_json_strict(
                    attempted, "attempted authorization lock"
                )
                competing["authorization_id"] = (
                    "competing-synthetic-authorization"
                )
                self.service.preload(
                    self.name, core.canonical_json_bytes(competing)
                )
                raise RuntimeError("competing authorization won")
            super().upload_blob(data, overwrite)

    class CompetingLockService(_FakeService):
        attempted_lock_bytes: bytes | None = None

        def get_blob_client(self, container, blob):
            return CompetingLockBlob(self, blob)

    monkeypatch.setattr(
        bootstrap,
        "_git_source_bindings",
        lambda _commit: _runtime_source_bindings(),
    )
    service = CompetingLockService()
    _seed_manifest_only_registered_parent(service, synthetic_bundle)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        expected_private_endpoint_ip="10.0.0.4",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        state_prefix=state_prefix,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        runtime_config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        execution_id="losing-custodian-bootstrap",
        actor="synthetic-custodian",
    )
    with pytest.raises(
        core.LockedEvaluationError,
        match="existing bootstrap singleton differs",
    ):
        bootstrap.run_bootstrap(
            args,
            service=service,
            core=core,
            now=lambda: "2026-07-20T06:00:00Z",
            custodian_authorized=True,
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            image_binding_bytes=IMAGE_BINDING_BYTES,
        )

    uploads = [event for event in service.events if event[0] == "upload"]
    assert len(uploads) == 1
    lock_blob = uploads[0][1]
    assert lock_blob.startswith(f"{core.AUTHORIZATION_LOCK_BLOB_PREFIX}/")
    assert service.attempted_lock_bytes is not None
    assert service.data[lock_blob] != service.attempted_lock_bytes
    assert core.list_exact_prefix(
        service, args.container, state_prefix
    ) == set()
    assert not any(
        event[0] == "upload" and event[1].startswith(f"{state_prefix}/")
        for event in service.events
    )


def test_bootstrap_recovers_after_global_lock_only_crash(
    synthetic_bundle, monkeypatch
):
    class CrashAfterLockBlob(_FakeBlob):
        def upload_blob(self, data, overwrite):
            if (
                self.service.crash_state_upload
                and self.name.startswith(f"{self.service.state_prefix}/")
            ):
                self.service.crash_state_upload = False
                raise RuntimeError("synthetic crash after global lock")
            super().upload_blob(data, overwrite)

    class CrashAfterLockService(_FakeService):
        crash_state_upload = True

        def __init__(self, state_prefix):
            super().__init__()
            self.state_prefix = state_prefix

        def get_blob_client(self, container, blob):
            return CrashAfterLockBlob(self, blob)

    monkeypatch.setattr(
        bootstrap,
        "_git_source_bindings",
        lambda _commit: _runtime_source_bindings(),
    )
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    service = CrashAfterLockService(state_prefix)
    _seed_manifest_only_registered_parent(service, synthetic_bundle)
    args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        expected_private_endpoint_ip="10.0.0.4",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        state_prefix=state_prefix,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        runtime_config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        execution_id="winning-custodian-bootstrap",
        actor="winning-synthetic-custodian",
    )
    with pytest.raises(core.LockedEvaluationError, match="overwrite-false"):
        bootstrap.run_bootstrap(
            args,
            service=service,
            core=core,
            now=lambda: "2026-07-20T06:00:00Z",
            custodian_authorized=True,
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            image_binding_bytes=IMAGE_BINDING_BYTES,
        )

    lock_blobs = {
        name
        for name in service.data
        if name.startswith(f"{core.AUTHORIZATION_LOCK_BLOB_PREFIX}/")
    }
    assert len(lock_blobs) == 1
    assert core.list_exact_prefix(
        service, args.container, state_prefix
    ) == set()

    rerun_args = deepcopy(args)
    rerun_args.execution_id = "losing-rerun-invocation"
    rerun_args.actor = "losing-rerun-actor"
    result = bootstrap.run_bootstrap(
        rerun_args,
        service=service,
        core=core,
        now=lambda: "2026-07-21T06:00:00Z",
        custodian_authorized=True,
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        image_binding_bytes=IMAGE_BINDING_BYTES,
    )
    draft_blob = (
        f"{state_prefix}/"
        f"{core.STATE_RECEIPT_FILENAMES['DRAFT_PROTOCOL']}"
    )
    draft = core.parse_json_strict(service.data[draft_blob], "recovered draft")
    assert draft["execution_id"] == "winning-custodian-bootstrap-00"
    assert draft["actor"] == "winning-synthetic-custodian"
    assert draft["timestamp_utc"] == "2026-07-20T06:00:00Z"
    assert result["authorization_lock_blob"] in lock_blobs
    assert not any(
        event[0] == "download"
        and (
            event[1].endswith("locked_inputs.jsonl")
            or event[1].endswith("locked_reference_labels.jsonl")
        )
        for event in service.events
    )


def test_bootstrap_lock_only_rejects_competing_authorization(
    synthetic_bundle, monkeypatch
):
    monkeypatch.setattr(
        bootstrap,
        "_git_source_bindings",
        lambda _commit: _runtime_source_bindings(),
    )
    service = _FakeService()
    _seed_manifest_only_registered_parent(service, synthetic_bundle)
    state_prefix = core.evaluation_prefixes(PARENT, AUTHORIZATION)["state"]
    original_args = SimpleNamespace(
        account_url="https://syntheticaccount.blob.core.windows.net",
        expected_private_endpoint_ip="10.0.0.4",
        container="synthetic-container",
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        state_prefix=state_prefix,
        implementation_commit=IMPLEMENTATION,
        image_digest=IMAGE_DIGEST,
        runtime_config_sha256=CONFIG_SHA256,
        image_binding_sha256=IMAGE_BINDING_SHA256,
        helper_snapshot_set_sha256=HELPER_SNAPSHOT_SET_SHA256,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
        execution_id="winning-custodian-bootstrap",
        actor="winning-synthetic-custodian",
    )
    result = bootstrap.run_bootstrap(
        original_args,
        service=service,
        core=core,
        now=lambda: "2026-07-20T06:00:00Z",
        custodian_authorized=True,
        runtime_config_bytes=RUNTIME_CONFIG_BYTES,
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        image_binding_bytes=IMAGE_BINDING_BYTES,
    )
    for name in list(service.data):
        if name.startswith(f"{state_prefix}/"):
            del service.data[name]
            del service.etags[name]

    competing_authorization = "competing-synthetic-authorization"
    competing_runtime_bytes = core.canonical_json_bytes(
        core.build_runtime_configuration(
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=competing_authorization,
            launcher_sha256=LAUNCHER_SHA256,
            launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
            source_bindings=_runtime_source_bindings(),
            azure_destination=_azure_destination(),
            image_binding=IMAGE_BINDING,
            image_binding_sha256=IMAGE_BINDING_SHA256,
        )
    )
    competing_config_sha256 = core.sha256_bytes(competing_runtime_bytes)
    competing_implementation_bytes = core.canonical_json_bytes(
        {
            "schema_version": core.IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
            "implementation_commit": IMPLEMENTATION,
            "image_digest": IMAGE_DIGEST,
            "config_sha256": competing_config_sha256,
        }
    )
    competing_args = deepcopy(original_args)
    competing_args.authorization_id = competing_authorization
    competing_args.state_prefix = core.evaluation_prefixes(
        PARENT, competing_authorization
    )["state"]
    competing_args.runtime_config_sha256 = competing_config_sha256
    competing_args.implementation_manifest_sha256 = core.sha256_bytes(
        competing_implementation_bytes
    )
    competing_args.execution_id = "competing-custodian-bootstrap"
    with pytest.raises(
        core.LockedEvaluationError,
        match="existing authorization lock immutable binding mismatch",
    ):
        bootstrap.run_bootstrap(
            competing_args,
            service=service,
            core=core,
            now=lambda: "2026-07-21T06:00:00Z",
            custodian_authorized=True,
            runtime_config_bytes=competing_runtime_bytes,
            implementation_manifest_bytes=competing_implementation_bytes,
            image_binding_bytes=IMAGE_BINDING_BYTES,
        )
    assert set(service.data) == {
        *core._load_frozen_validation().expected_parent_membership(PARENT),
        result["authorization_lock_blob"],
    }


def test_manifest_last_checks_parent_membership_and_redownloads_every_member():
    service = _FakeService()
    baseline_blob = f"{PARENT}/development/existing.json"
    service.preload(baseline_blob, b"existing\n")
    prefix = f"{PARENT}/predictions/{AUTHORIZATION}"
    names = (".reservation.json", "payload.json", "artifact_manifest.json")
    payloads = {
        ".reservation.json": core.canonical_json_bytes({"reservation": True}),
        "payload.json": core.canonical_json_bytes({"value": 1}),
    }
    result = core.persist_manifest_last_prefix(
        service,
        "synthetic-container",
        prefix,
        member_names=names,
        registered_member_names=names,
        payloads=payloads,
        manifest_builder=lambda metadata: {"members": metadata},
        parent_prefix=PARENT,
        registered_parent_members_before={baseline_blob},
    )
    assert result["manifest_uploaded_last"] is True
    for name in names:
        assert ("download", f"{prefix}/{name}") in service.events

    tainted = _FakeService()
    tainted.preload(baseline_blob, b"existing\n")
    tainted.preload(
        f"{PARENT}/state/{AUTHORIZATION}/unexpected.json", b"unexpected\n"
    )
    with pytest.raises(core.LockedEvaluationError, match="parent membership"):
        core.persist_manifest_last_prefix(
            tainted,
            "synthetic-container",
            prefix,
            member_names=names,
            registered_member_names=names,
            payloads=payloads,
            manifest_builder=lambda metadata: {"members": metadata},
            parent_prefix=PARENT,
            registered_parent_members_before={baseline_blob},
        )


def test_runtime_config_hash_commands_prefixes_and_retry_policy_are_bound():
    record = core.build_runtime_configuration(
        source_commit=IMPLEMENTATION,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        source_bindings=_runtime_source_bindings(),
        azure_destination=_azure_destination(),
        image_binding=IMAGE_BINDING,
        image_binding_sha256=IMAGE_BINDING_SHA256,
    )
    data = core.canonical_json_bytes(record)
    assert core.validate_runtime_configuration(
        data,
        expected_sha256=core.sha256_bytes(data),
        source_commit=IMPLEMENTATION,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
    ) == record
    assert record["stage_commands"] == {
        "P": {"command": ["/workspace/bin/stage-p"], "args_prefix": []},
        "P_ADOPT": {
            "command": ["/workspace/bin/stage-p-adopt"],
            "args_prefix": [],
        },
        "E": {"command": ["/workspace/bin/stage-e"], "args_prefix": []},
    }
    assert record["schema_version"] == "phase1-parser-v2-runtime-config/v5"
    assert record["retry_policy"]["prediction_adoption_max"] == 1
    for path, replacement in (
        (("stage_commands", "P", "command"), ["sh"]),
        (("bindings", "state_prefix"), "wrong/prefix"),
        (("retry_policy", "scorer_infrastructure_max"), 2),
        (("retry_policy", "scorer_infrastructure_max"), True),
        (("job", "replica_completion_count"), True),
        (("job", "gpu"), 0),
        (("job", "managed_identity_only"), 1),
        (("azure_destination", "storage", "shared_key_access"), 0),
        (("azure_destination", "storage", "allow_blob_public_access"), True),
        (("azure_destination", "storage", "container_public_access"), "Blob"),
    ):
        forged = deepcopy(record)
        target = forged
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        forged_bytes = core.canonical_json_bytes(forged)
        with pytest.raises(core.LockedEvaluationError):
            core.validate_runtime_configuration(
                forged_bytes,
                expected_sha256=core.sha256_bytes(forged_bytes),
                source_commit=IMPLEMENTATION,
                parent_prefix=PARENT,
                authorization_id=AUTHORIZATION,
                launcher_sha256=LAUNCHER_SHA256,
                launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
            )
    with pytest.raises(core.LockedEvaluationError):
        core.validate_runtime_configuration(
            data,
            expected_sha256="9" * 64,
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
        )


def test_effective_launcher_attempt_prefix_routing_rejects_forgery():
    def authenticated_attempt(
        stage: str, retry_kind: str, execution_id: str, output_leaf: str
    ) -> dict[str, str]:
        prefixes = core.evaluation_attempt_prefixes(
            PARENT, AUTHORIZATION, stage, retry_kind, execution_id
        )
        output_prefix = prefixes[output_leaf]
        visibility_prefix = prefixes["visibility"]
        return {
            "stage": stage,
            "retry_kind": retry_kind,
            "execution_id": execution_id,
            "attempt_binding_sha256": core.attempt_binding_sha256(
                stage, retry_kind, execution_id
            ),
            f"{output_leaf}_prefix": output_prefix,
            f"{output_leaf}_prefix_sha256": core.attempt_prefix_sha256(
                output_prefix
            ),
            "visibility_prefix": visibility_prefix,
            "visibility_prefix_sha256": core.attempt_prefix_sha256(
                visibility_prefix
            ),
        }

    prediction = authenticated_attempt(
        "P", "infrastructure_pre_input", "stage-p-retry", "predictions"
    )
    scoring = authenticated_attempt(
        "E", "scorer_infrastructure", "stage-e-retry", "scores"
    )
    stage_p = core.derive_effective_launcher_attempt_prefixes(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        stage="P",
        retry_kind="infrastructure_pre_input",
        execution_id="current-stage-p-retry",
        verification_only=False,
        authenticated_prediction_attempt=None,
        authenticated_scoring_attempt=None,
    )
    current_stage_p = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "P",
        "infrastructure_pre_input",
        "current-stage-p-retry",
    )
    assert stage_p["predictions_prefix"] == current_stage_p["predictions"]
    assert stage_p["visibility_prefix"] == current_stage_p["visibility"]

    primary_stage_e = core.derive_effective_launcher_attempt_prefixes(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        stage="E",
        retry_kind="none",
        execution_id="current-stage-e",
        verification_only=False,
        authenticated_prediction_attempt=prediction,
        authenticated_scoring_attempt=None,
    )
    assert primary_stage_e["predictions_prefix"] == prediction[
        "predictions_prefix"
    ]
    assert primary_stage_e["scores_prefix"] == core.evaluation_prefixes(
        PARENT, AUTHORIZATION
    )["scores"]

    scorer_retry = core.derive_effective_launcher_attempt_prefixes(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        stage="E",
        retry_kind="scorer_infrastructure",
        execution_id="current-scorer-retry",
        verification_only=False,
        authenticated_prediction_attempt=prediction,
        authenticated_scoring_attempt=None,
    )
    current_scorer = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "E",
        "scorer_infrastructure",
        "current-scorer-retry",
    )
    assert scorer_retry["predictions_prefix"] == prediction[
        "predictions_prefix"
    ]
    assert scorer_retry["scores_prefix"] == current_scorer["scores"]
    assert scorer_retry["visibility_prefix"] == current_scorer["visibility"]

    verification = core.derive_effective_launcher_attempt_prefixes(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        stage="E",
        retry_kind="verification_only",
        execution_id="current-verification",
        verification_only=True,
        authenticated_prediction_attempt=prediction,
        authenticated_scoring_attempt=scoring,
    )
    current_verification = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        "E",
        "verification_only",
        "current-verification",
    )
    assert verification["predictions_prefix"] == prediction[
        "predictions_prefix"
    ]
    assert verification["scores_prefix"] == scoring["scores_prefix"]
    assert verification["visibility_prefix"] == current_verification[
        "visibility"
    ]
    assert verification["current_attempt_binding_sha256"] == (
        core.attempt_binding_sha256(
            "E", "verification_only", "current-verification"
        )
    )

    forged = deepcopy(prediction)
    forged["predictions_prefix"] = core.evaluation_prefixes(
        PARENT, AUTHORIZATION
    )["predictions"]
    with pytest.raises(core.LockedEvaluationError, match="prefix differs"):
        core.derive_effective_launcher_attempt_prefixes(
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            stage="E",
            retry_kind="none",
            execution_id="forged-stage-e",
            verification_only=False,
            authenticated_prediction_attempt=forged,
            authenticated_scoring_attempt=None,
        )


def test_exact_json_equality_distinguishes_every_json_type_recursively():
    assert core.exact_json_equal(
        {"items": [True, 1, 1.0, "1", None]},
        {"items": [True, 1, 1.0, "1", None]},
    )
    for left, right in (
        (True, 1),
        (False, 0),
        (1, 1.0),
        (1, "1"),
        ([{"ordinal": True}], [{"ordinal": 1}]),
        ({"enabled": 1}, {"enabled": True}),
    ):
        assert not core.exact_json_equal(left, right)


def test_metrics_reject_bool_int_confusion_in_derived_counts(synthetic_bundle):
    metrics, _ = _score(synthetic_bundle)
    forged = deepcopy(metrics)
    forged["gate_summary"]["na_invalid"] = False
    with pytest.raises(core.LockedEvaluationError):
        core.validate_metrics_artifact(forged, synthetic_bundle["gates"])


def test_arbitrary_locked_digest_without_image_binding_is_rejected():
    legacy = core.parse_json_strict(RUNTIME_CONFIG_BYTES, "runtime")
    del legacy["image_binding"]
    del legacy["image_binding_sha256"]
    del legacy["helper_snapshot_set_sha256"]
    legacy["azure_destination"]["image"] = {
        "digest": IMAGE_DIGEST,
        "reference": (
            "syntheticregistry.azurecr.io/"
            f"j-space-observation-parser-eval@{IMAGE_DIGEST}"
        ),
        "base_image": BASE_IMAGE,
    }
    data = core.canonical_json_bytes(legacy)
    with pytest.raises(core.LockedEvaluationError, match="schema fields"):
        core.validate_runtime_configuration(
            data,
            expected_sha256=core.sha256_bytes(data),
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            expected_image_digest=IMAGE_DIGEST,
        )


def test_bootstrap_requires_caller_expected_image_binding_hash():
    args = SimpleNamespace(
        runtime_config_sha256=CONFIG_SHA256,
        implementation_manifest_sha256=core.sha256_bytes(
            IMPLEMENTATION_MANIFEST_BYTES
        ),
    )
    with pytest.raises(
        core.LockedEvaluationError,
        match="runtime/implementation/image-binding hash mismatch",
    ):
        bootstrap.run_bootstrap(
            args,
            core=core,
            custodian_authorized=True,
            runtime_config_bytes=RUNTIME_CONFIG_BYTES,
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            image_binding_bytes=IMAGE_BINDING_BYTES,
        )


def test_runtime_external_image_and_implementation_mismatches_are_rejected():
    other_binding, other_binding_sha, _, _, _ = (
        _live_image_binding_inputs()
    )
    with pytest.raises(core.LockedEvaluationError, match="expected hash mismatch"):
        core.validate_runtime_configuration(
            RUNTIME_CONFIG_BYTES,
            expected_sha256=CONFIG_SHA256,
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            image_binding_bytes=other_binding,
            expected_image_binding_sha256=other_binding_sha,
        )
    with pytest.raises(core.LockedEvaluationError, match="digest binding mismatch"):
        core.validate_runtime_configuration(
            RUNTIME_CONFIG_BYTES,
            expected_sha256=CONFIG_SHA256,
            source_commit=IMPLEMENTATION,
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            expected_image_digest="sha256:" + "9" * 64,
            image_binding_bytes=IMAGE_BINDING_BYTES,
            expected_image_binding_sha256=IMAGE_BINDING_SHA256,
        )


def test_build_and_launcher_static_hardening_contract():
    build = (
        ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v2_eval.sh"
    ).read_text(encoding="utf-8")
    launch = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    runtime_generator = (
        ROOT / "scripts" / "create_parser_v2_runtime_config.py"
    ).read_text(encoding="utf-8")
    assert build.startswith("#!/bin/bash -p\n")
    assert launch.startswith("#!/bin/bash -p\n")
    assert "/bin/bash --noprofile --norc -p" in build
    for token in (
        "status --porcelain=v1 --untracked-files=all",
        "HEAD == SOURCE_SHA == origin/main",
        "APPROVED_ORIGIN_URL=",
        "remote get-url origin",
        "exact-remote-source",
        "REMOTE_SOURCE_LOCATION",
        "git -C \"$PROJECT_ROOT\" archive --format=tar \"$SOURCE_SHA\"",
        '-- "${BUILD_INPUTS[@]}"',
        "archive context membership differs from source binding",
        '"hash-object", "--stdin"',
        "refs/remotes/origin/main",
        "check-ignore -q",
        "PINNED_BASE_IMAGE=",
        "cat-file\", \"blob\"",
        "source_binding_sha256",
        "build_provenance_sha256",
        "build_run_request_sha256",
        "create-acr-task-run",
        "validate-acr-task-run",
        "TASK_RUN_NAME=",
        "TASK_RUN_RESOURCE_ID=",
        "TASK_RUN_URL=",
        '--header "If-None-Match: *"',
        "--retry 0",
        "--max-redirs 0",
        "validate-oci-image",
        "validate-oci-evidence",
        "validate-image-binding-oci",
        "OCI_VERIFICATION_SHA256",
        "validate-coordination-zone",
        "create-claim-envelope --kind build",
        "create-txt-record-body",
        "BUILD_CAPABILITY",
        '"$BUILD_CREATE_STATUS" == "201"',
        "GET-only recovery",
        "the one-shot build is permanently stranded",
        "curl is required for OCI provenance verification",
        "OCI registry token retrieval failed",
        "--query refreshToken",
        'data-urlencode = "grant_type=refresh_token"',
        'data-urlencode = "service=%s"',
        'data-urlencode = "scope=repository:%s:pull"',
        'data-urlencode = "refresh_token=%s"',
        '"https://${LOGIN_SERVER}/oauth2/token"',
        "OCI scoped registry token exchange failed",
        'header = "Authorization: Bearer %s"',
        '".dockerignore"',
        "changeableAttributes.writeEnabled",
        "changeableAttributes.deleteEnabled",
        "TASK_RUN_PRE_PUT_GET_STATUS",
        "only GET adoption follows",
        "GIT_NO_REPLACE_OBJECTS=1",
        "Refusing to read or execute an unauthenticated source commit",
        "existing finalization record differs",
        "scripts/create_parser_v2_runtime_config.py",
        "scripts/bootstrap_parser_v2_locked_evaluation.py",
        "scripts/parser_v2_azure_contract.py",
        "scripts/parser_v2_process_worker.py",
        "scripts/stage_p_entrypoint.sh",
        "scripts/stage_p_adopt_entrypoint.sh",
        "scripts/stage_e_entrypoint.sh",
    ):
        assert token in build
    assert "--force" not in build
    assert "az acr build" not in build
    assert build.count('raw_arm_request_once PUT "$TASK_RUN_URL"') == 1
    assert build.count('raw_arm_request_once PUT "$BUILD_RECORD_URL"') == 1
    build_raw_helper = build[
        build.index("raw_arm_request_once() {"):
        build.index("readonly -f raw_arm_request_once")
    ]
    oci_helper = build[
        build.index("authenticate_oci_provenance_label() {"):
        build.index('mkdir "$CONTEXT_DIR"')
    ]
    assert build_raw_helper.count("--retry 0") == 1
    assert build.index("GIT_NO_REPLACE_OBJECTS=1") < build.index(
        'git -C "$PROJECT_ROOT"'
    )
    assert build.index("fetch --quiet --no-tags") < build.index(
        "snapshot_nonce="
    )
    assert "RESERVATION_OWNER" not in build
    assert "OCI config label retrieval unavailable" not in build
    assert "--user " not in oci_helper
    assert 'user = "%s:%s"' not in oci_helper
    assert "--query accessToken" not in oci_helper
    assert oci_helper.count('header = "Authorization: Bearer %s"') == 2
    assert oci_helper.count('data-urlencode = "refresh_token=%s"') == 1
    assert oci_helper.index("--query refreshToken") < oci_helper.index(
        '"https://${LOGIN_SERVER}/oauth2/token"'
    )
    assert oci_helper.index(
        '"https://${LOGIN_SERVER}/oauth2/token"'
    ) < oci_helper.index(
        '"https://${LOGIN_SERVER}/v2/${IMAGE_REPOSITORY}/manifests/${digest}"'
    )
    assert 'echo "$access_token"' not in build
    assert 'echo "$refresh_token"' not in build
    assert 'echo "$management_token"' not in build
    assert '"$TASK_RUN_URL"' in build
    assert '"$CONTEXT_DIR")' not in build
    assert "Mutable latest is forbidden" in build
    assert build.index(
        'authenticate_oci_provenance_label "$DIGEST"'
    ) < build.index("az acr import")
    approved_base = (ROOT / "Dockerfile.jlens").read_text(
        encoding="utf-8"
    ).splitlines()[0].removeprefix("FROM ")
    assert f'PINNED_BASE_IMAGE="{approved_base}"' in build
    assert core.PARSER_V2_EVAL_BASE_IMAGE == approved_base
    assert (
        f"ARG PYTHON_BASE_IMAGE={approved_base}"
        in (ROOT / "Dockerfile.parser-v2-eval").read_text(encoding="utf-8")
    )
    for token in (
        "verify-private",
        "--storage-container",
        "/blobServices/default/containers/${BLOB_CONTAINER}",
        "privateLinkResources?api-version=",
        "privateEndpointConnections?api-version=",
        "--storage-private-link-resources",
        "privateDnsZoneGroups?api-version=",
        "virtualNetworkLinks?api-version=",
        "roleAssignments?api-version=",
        "workloadProfileStates?api-version=",
        "PARSER_EVAL_RECOVER_CLAIM_NAME",
        "PARSER_EVAL_VERIFICATION_STATE",
        "create-claim-envelope --kind launch",
        "create-claim-envelope --kind dispatch",
        "validate-coordination-zone",
        "COORDINATION_BINDING_SHA256",
        "LAUNCH_CAPABILITY",
        "DISPATCH_CAPABILITY",
        "START_RESPONSE_FILE",
        "arm-list",
        "| tr -d '\\r'",
        "launcher-git-blob-oid",
        "authorization-manifest-sha256",
        "PARSER_EVAL_RUNTIME_CONFIG_FILE",
        "validate-live-job-projection",
        "baseline_execution_membership_sha256",
        "execution-membership",
        "adopt-remove-one",
        "PRIVATE_ENDPOINT_IPS_JSON",
        "authenticate_persisted_state",
        "authenticate_persisted_state LATEST",
        "CLAIM_STATE_RECEIPT_SHA256",
        "validate-live-image-binding",
        "ACR_BUILD_TASK_RUN_RESOURCE_ID",
        "--task-run",
        "GIT_NO_REPLACE_OBJECTS=1",
        "IMAGE_BINDING_SNAPSHOT_FILE",
        "HELPER_SNAPSHOT_MANIFEST_FILE",
        "verify_snapshot_git_bindings",
        "JSPACE_PV2_VERIFIED_REEXEC",
        '/bin/bash --noprofile --norc -p "$SNAPSHOT_LAUNCHER"',
        "exec /usr/bin/env -i",
        "unset BASH_ENV ENV CDPATH GLOBIGNORE PYTHONPATH",
        'readonly PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"',
        "image-binding-sha256",
        "helper-snapshot-set-sha256",
        "Persisted state changed before dispatch claim",
        "BLOB_PRIVATE_DNS_LINK_NAME",
        "BLOB_PRIVATE_DNS_ZONE_GROUP_NAME",
        '"initContainers": []',
        '"volumes": []',
        '"volumeMounts": []',
        '"probes": []',
        "Stage environment contains an unregistered channel",
    ):
        assert token in launch
    assert "PARSER_EVAL_ACTOR" not in launch
    assert "PARSER_EVAL_EXECUTION_ID" not in launch
    assert "replicaRetryLimit\": 0" in launch
    assert "role assignment list --all" not in launch
    assert "auto-follow service pagination" not in launch
    launcher_oci_helper = launch[
        launch.index("reauthenticate_runtime_destination() {"):
        launch.index("authenticate_persisted_state() {")
    ]
    assert "--query accessToken" not in launcher_oci_helper
    assert "--query refreshToken" in launcher_oci_helper
    assert 'data-urlencode = "grant_type=refresh_token"' in launcher_oci_helper
    assert 'data-urlencode = "service=%s"' in launcher_oci_helper
    assert (
        'data-urlencode = "scope=repository:%s:pull"'
        in launcher_oci_helper
    )
    assert (
        'data-urlencode = "refresh_token=%s"' in launcher_oci_helper
    )
    assert (
        '"https://${LOGIN_SERVER}/oauth2/token"' in launcher_oci_helper
    )
    assert 'user = "%s:%s"' not in launcher_oci_helper
    assert launcher_oci_helper.count(
        'header = "Authorization: %s %s"'
    ) == 2
    assert launcher_oci_helper.count('"Bearer" "$access_token"') == 2
    assert (
        'header = "Authorization: ' + ("*" * 6) + '"'
        not in launcher_oci_helper
    )
    assert 'echo "$access_token"' not in launcher_oci_helper
    assert 'echo "$refresh_token"' not in launcher_oci_helper
    assert launch.index("GIT_NO_REPLACE_OBJECTS=1") < launch.index(
        '"git", "-C", project_root'
    )
    assert 'parser.add_argument("--image-binding", type=Path, required=True)' in (
        runtime_generator
    )
    assert 'parser.add_argument("--image-binding-sha256", required=True)' in (
        runtime_generator
    )
    assert "_stable_read(args.image_binding)" in runtime_generator
    assert "_fetch_approved_origin()" in runtime_generator
    assert "_stable_read(Path(__file__).resolve()) != committed_self" in (
        runtime_generator
    )
    assert (
        "core = _load_core(args.source_commit, args.evaluation_profile)"
        in runtime_generator
    )
    # The unseeded-core defect family: the profile has to be fixed before
    # the core executes, and both directions must be asserted.
    assert (
        'module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = profile_id'
        in runtime_generator
    )
    assert (
        "if core_module.ACTIVE_PARSER_PROFILE_ID != profile_id:"
        in runtime_generator
    )
    assert (
        'if "_PRESEEDED_PARSER_PROFILE_ID" in core_module.__dict__:'
        in runtime_generator
    )
    assert "compile(source, source_name, \"exec\")" in runtime_generator
    assert "spec_from_file_location" not in runtime_generator
    assert (
        "core_module._load_frozen_validation = lambda: validation_module"
        in runtime_generator
    )
    assert '"--no-replace-objects"' in runtime_generator
    assert "for path in core.IMAGE_BINDING_SOURCE_PATHS" in runtime_generator
    assert 'image_binding["files"] != committed_image_sources' in (
        runtime_generator
    )
    assert "IMAGE_BINDING_SHA256_FILE=" in build
    assert launch.index("status --porcelain=v1 --untracked-files=all") < (
        launch.index('"cat-file", "blob", oid]')
    ) < launch.index('/bin/bash --noprofile --norc -p "$SNAPSHOT_LAUNCHER"')
    assert build.index(
        '--image "${IMAGE_REPOSITORY}@${DIGEST}"'
    ) < build.index(
        '--image "${IMAGE_REPOSITORY}:${FINAL_TAG}"',
        build.index("# Lock the manifest first"),
    )
    bash = shutil.which("bash")
    if sys.platform == "win32":
        git = shutil.which("git")
        git_bash = (
            Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if git
            else None
        )
        if git_bash is not None and git_bash.is_file():
            bash = str(git_bash)
    if bash:
        subprocess.run(
            [
                bash,
                "-n",
                (
                    ROOT
                    / "infra"
                    / "azure"
                    / "scripts"
                    / "09_build_parser_v2_eval.sh"
                ).as_posix(),
            ],
            check=True,
        )
        subprocess.run(
            [
                bash,
                "-n",
                (
                    ROOT
                    / "infra"
                    / "azure"
                    / "scripts"
                    / "10_run_parser_v2_locked_eval.sh"
                ).as_posix(),
            ],
            check=True,
        )


def test_launcher_and_build_scrub_shell_and_python_interposition():
    bash = shutil.which("bash")
    if sys.platform == "win32":
        git = shutil.which("git")
        git_bash = (
            Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if git
            else None
        )
        if git_bash is not None and git_bash.is_file():
            bash = str(git_bash)
    if not bash:
        pytest.skip("Bash is unavailable")
    secret = "DO-NOT-LEAK-INTERPOSITION-VALUE"
    python_path_secret = "DO-NOT-LEAK-PYTHONPATH-VALUE"
    marker = (
        ROOT
        / "results"
        / "runs"
        / f".parser-v2-interposition-{uuid.uuid4().hex}"
    )
    adversarial = (
        ROOT / "tests" / "fixtures" / "parser_v2_adversarial_bash_env.sh"
    )
    common = dict(os.environ)
    common.update(
        {
            "BASH_ENV": adversarial.as_posix(),
            "ENV": secret,
            "CDPATH": secret,
            "GLOBIGNORE": secret,
            "PYTHONPATH": python_path_secret,
            "PYTHONHOME": secret,
            "PYTHONSTARTUP": secret,
            "PYTHONWARNINGS": secret,
            "INTERPOSITION_SECRET": secret,
            "INTERPOSITION_MARKER": marker.as_posix(),
        }
    )
    commands = [
        (
            ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v2_eval.sh",
            {
                "ACR_NAME": "syntheticregistry",
                "RESOURCE_GROUP": "rg-synthetic",
                "SOURCE_SHA": "a" * 40,
                "JSPACE_PV2_BUILD_CLEAN_REEXEC": "1",
            },
        ),
        (
            ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh",
            {
                "PARSER_EVAL_STAGE": "X",
                "PARSER_EVAL_VERIFY_ONLY": "false",
                "PARSER_EVAL_VERIFICATION_STATE": "CLOSED",
                "PARSER_EVAL_RETRY_KIND": "none",
                "PARSER_EVAL_INITIAL_BOOTSTRAP": "false",
                "PARSER_EVAL_RUNTIME_CONFIG_FILE": secret,
                "PARSER_EVAL_CONFIG_SHA256": "a" * 64,
                "PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE": secret,
                "PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256": "b" * 64,
                "PARSER_EVAL_IMAGE_BINDING_FILE": secret,
                "PARSER_EVAL_IMAGE_BINDING_SHA256": "c" * 64,
                "JSPACE_PV2_LAUNCH_CLEAN_REEXEC": "1",
            },
        ),
    ]
    try:
        for script, additions in commands:
            environment = {**common, **additions}
            completed = subprocess.run(
                [bash, script.as_posix()],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            combined = completed.stdout + completed.stderr
            assert completed.returncode != 0
            assert secret not in combined
            assert python_path_secret not in combined
            assert not marker.exists()
    finally:
        marker.unlink(missing_ok=True)


def _extract_launcher_python(
    launcher: str, opener: str, closer: str
) -> str:
    start = launcher.index(opener) + len(opener)
    end = launcher.index(closer, start)
    return launcher[start:end]


def _materialize_test_launcher_snapshots(root: Path) -> dict[str, Any]:
    repository = root / "snapshot-repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", str(repository)],
        check=True,
        capture_output=True,
    )
    helper_path = "scripts/parser_v2_azure_contract.py"
    trusted_helper = b'print("trusted-helper")\n'
    for relative_path in core.RUNTIME_SOURCE_BINDING_PATHS:
        path = repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            trusted_helper
            if relative_path == helper_path
            else f"registered:{relative_path}\n".encode()
        )
    subprocess.run(
        ["git", "-C", str(repository), "add", "--all"],
        check=True,
        capture_output=True,
    )
    tree = subprocess.run(
        ["git", "-C", str(repository), "write-tree"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.replace("\r", "").strip()
    bindings = {}
    for relative_path in core.RUNTIME_SOURCE_BINDING_PATHS:
        oid = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "rev-parse",
                f"{tree}:{relative_path}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.replace("\r", "").strip()
        data = subprocess.run(
            ["git", "-C", str(repository), "cat-file", "blob", oid],
            check=True,
            capture_output=True,
        ).stdout
        bindings[relative_path] = {
            "git_blob_oid": oid,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    (repository / helper_path).write_bytes(b'print("swapped-helper")\n')

    runtime_bytes = core.canonical_json_bytes(
        {
            "schema_version": core.RUNTIME_CONFIG_SCHEMA_VERSION,
            "source_commit": tree,
            "source_bindings": bindings,
            "helper_snapshot_set_sha256": core.sha256_bytes(
                core.canonical_json_bytes(bindings)
            ),
        }
    )
    implementation_bytes = b'{"record":"implementation"}\n'
    image_bytes = b'{"record":"image-binding"}\n'
    runtime_source = root / "runtime.json"
    implementation_source = root / "implementation.json"
    image_source = root / "image-binding.json"
    runtime_source.write_bytes(runtime_bytes)
    implementation_source.write_bytes(implementation_bytes)
    image_source.write_bytes(image_bytes)

    snapshot = root / "snapshots"
    snapshot.mkdir()
    runtime_target = snapshot / "runtime.snapshot.json"
    implementation_target = snapshot / "implementation.snapshot.json"
    image_target = snapshot / "image.snapshot.json"
    source_root = snapshot / "sources"
    manifest = snapshot / "helper-snapshots.json"
    launcher = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    materializer = _extract_launcher_python(
        launcher,
        '"$SNAPSHOT_SOURCE_ROOT" "$HELPER_SNAPSHOT_MANIFEST_FILE" <<\'PY\'\n',
        '\nPY\n    SNAPSHOT_LAUNCHER=',
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            materializer,
            str(repository),
            tree,
            str(runtime_source),
            str(runtime_target),
            core.sha256_bytes(runtime_bytes),
            str(implementation_source),
            str(implementation_target),
            core.sha256_bytes(implementation_bytes),
            str(image_source),
            str(image_target),
            core.sha256_bytes(image_bytes),
            str(source_root),
            str(manifest),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    git_verifier = _extract_launcher_python(
        launcher,
        '        "$SNAPSHOT_SOURCE_ROOT" <<\'PY\'\n',
        "\nPY\n}\n\nverify_snapshot_git_bindings",
    )
    verified = subprocess.run(
        [
            sys.executable,
            "-c",
            git_verifier,
            str(repository),
            tree,
            str(runtime_target),
            core.sha256_bytes(runtime_bytes),
            str(manifest),
            str(source_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stderr
    return {
        "launcher": launcher,
        "repository": repository,
        "runtime": runtime_target,
        "runtime_sha256": core.sha256_bytes(runtime_bytes),
        "implementation": implementation_target,
        "implementation_sha256": core.sha256_bytes(implementation_bytes),
        "image": image_target,
        "image_sha256": core.sha256_bytes(image_bytes),
        "source_root": source_root,
        "manifest": manifest,
        "helper_path": helper_path,
        "git_verifier": git_verifier,
        "tree": tree,
    }


def test_worktree_helper_swap_executes_only_registered_git_snapshot(workdir):
    state = _materialize_test_launcher_snapshots(workdir)
    launcher = state["launcher"]
    assert launcher.index(
        "status --porcelain=v1 --untracked-files=all"
    ) < launcher.index('"git", "-C", project_root, "cat-file", "blob", oid]')
    snapshot_helper = state["source_root"] / state["helper_path"]
    worktree_helper = state["repository"] / state["helper_path"]
    assert subprocess.run(
        [sys.executable, str(snapshot_helper)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "trusted-helper"
    assert subprocess.run(
        [sys.executable, str(worktree_helper)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "swapped-helper"


def test_missing_registered_helper_snapshot_aborts(workdir):
    state = _materialize_test_launcher_snapshots(workdir)
    missing = state["source_root"] / state["helper_path"]
    missing.chmod(stat.S_IWRITE)
    missing.unlink()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            state["git_verifier"],
            str(state["repository"]),
            state["tree"],
            str(state["runtime"]),
            state["runtime_sha256"],
            str(state["manifest"]),
            str(state["source_root"]),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "helper snapshot is unavailable" in completed.stderr


def test_runtime_destination_and_transitive_manifest_bindings_are_exact():
    record = core.build_runtime_configuration(
        source_commit=IMPLEMENTATION,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        source_bindings=_runtime_source_bindings(),
        azure_destination=_azure_destination(),
        image_binding=IMAGE_BINDING,
        image_binding_sha256=IMAGE_BINDING_SHA256,
    )
    data = core.canonical_json_bytes(record)
    assert record["azure_destination_sha256"] == core.runtime_destination_sha256(
        _azure_destination()
    )
    assert record["azure_destination"]["image"]["digest"] == IMAGE_DIGEST
    assert record["job"]["replica_retry_limit"] == 0
    assert record["job"]["cpu"] == "2.0"
    assert record["job"]["memory"] == "4Gi"
    assert record["job"]["workload_profile"] == "Consumption"
    assert set(record["source_bindings"]) == set(
        core.RUNTIME_SOURCE_BINDING_PATHS
    )
    assert "scripts/parser_v2_azure_contract.py" in record["source_bindings"]
    assert (
        "infra/azure/scripts/phase05_claim_election.py"
        not in record["source_bindings"]
    )
    core.validate_runtime_configuration(
        data,
        expected_sha256=core.sha256_bytes(data),
        source_commit=IMPLEMENTATION,
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        launcher_sha256=LAUNCHER_SHA256,
        launcher_git_blob_oid=LAUNCHER_GIT_BLOB_OID,
        expected_azure_destination=_azure_destination(),
        expected_image_digest=IMAGE_DIGEST,
    )
    for path, value in (
        (
            ("azure_destination", "subscription_id"),
            "44444444-4444-4444-8444-444444444444",
        ),
        (
            ("azure_destination", "network", "private_link_group_id"),
            "file",
        ),
        (
            ("azure_destination", "network", "private_dns_zone_name"),
            "example.invalid",
        ),
        (
            ("azure_destination", "image", "digest"),
            "sha256:" + "9" * 64,
        ),
        (
            ("azure_destination", "image", "base_image"),
            "python:3.11-slim@sha256:" + "8" * 64,
        ),
        (("job", "replica_retry_limit"), 1),
    ):
        forged = deepcopy(record)
        target = forged
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        forged_data = core.canonical_json_bytes(forged)
        with pytest.raises(core.LockedEvaluationError):
            core.validate_runtime_configuration(
                forged_data,
                expected_sha256=core.sha256_bytes(forged_data),
                source_commit=IMPLEMENTATION,
                parent_prefix=PARENT,
                authorization_id=AUTHORIZATION,
            )


def test_launcher_bootstrap_body_and_authorization_bind_image_and_helpers():
    runtime = core.parse_json_strict(RUNTIME_CONFIG_BYTES, "runtime")
    implementation = core.validate_implementation_manifest(
        IMPLEMENTATION_MANIFEST_BYTES
    )
    chain = _state_chain_until("UNSEAL_AUTHORIZED")
    authorization = core.parse_json_strict(
        _authorization_manifest_bytes(chain), "authorization manifest"
    )
    assert core.sha256_bytes(RUNTIME_CONFIG_BYTES) == implementation[
        "config_sha256"
    ]
    assert runtime["image_binding"] == IMAGE_BINDING
    assert runtime["image_binding_sha256"] == IMAGE_BINDING_SHA256
    assert authorization["image_binding_sha256"] == IMAGE_BINDING_SHA256
    assert authorization["helper_snapshot_set_sha256"] == (
        HELPER_SNAPSHOT_SET_SHA256
    )

    launcher = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    bootstrap_source = (
        ROOT / "scripts" / "bootstrap_parser_v2_locked_evaluation.py"
    ).read_text(encoding="utf-8")
    for token in (
        '"--image-binding-sha256", runtime["image_binding_sha256"]',
        '"image-binding-sha256": runtime["image_binding_sha256"]',
        '"image_binding_sha256"',
        '"helper_snapshot_set_sha256"',
        '"coordination_binding_sha256"',
        "JOB_BODY_SHA256",
        '"job_body_sha256"',
    ):
        assert token in launcher
    assert launcher.index('"image-binding-sha256":') < launcher.index(
        'JOB_BODY_SHA256="$(scalar sha256sum "$BODY_FILE")"'
    )
    for token in (
        "--image-binding-file",
        "--image-binding-sha256",
        "--helper-snapshot-set-sha256",
        '"image_binding_sha256": image_binding_sha256',
        '"helper_snapshot_set_sha256": helper_snapshot_set_sha256',
    ):
        assert token in bootstrap_source


def test_arm_nextlink_pagination_and_cr_normalization_are_explicit():
    first = (
        "https://management.azure.com/subscriptions/"
        f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
        "Microsoft.App/jobs?api-version=2024-03-01"
    )
    second = first + "&$skiptoken=opaque"
    pages = [
        {"value": [{"name": "job-a\r"}], "nextLink": second + "\r"},
        {"value": [{"name": "job-b"}]},
    ]
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        page = pages[len(calls) - 1]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(page).encode("utf-8"),
            stderr=b"",
        )

    assert azure_contract.collect_arm_list(first, run=run) == [
        {"name": "job-a"},
        {"name": "job-b"},
    ]
    assert len(calls) == 2
    assert calls[1][0][calls[1][0].index("--url") + 1] == second
    assert all("--all" not in command for command, _ in calls)

    def escaped(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "value": [],
                    "nextLink": "https://attacker.invalid/next?api-version=1",
                }
            ).encode(),
            stderr=b"",
        )

    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.collect_arm_list(first, run=escaped)


@pytest.mark.parametrize(
    "next_link",
    [
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/another-rg/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.Network/privateEndpoints"
            "?api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2023-05-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01&arbitrary=value"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01"
            "&api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/%6Aobs?api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs/../jobs"
            "?api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com@attacker.invalid/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01&$skiptoken=opaque"
        ),
        (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01&$skiptoken=opaque#"
        ),
        (
            "https://MANAGEMENT.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
            "Microsoft.App/jobs?api-version=2024-03-01&$skiptoken=opaque"
        ),
    ],
)
def test_arm_nextlink_is_bound_to_the_exact_initial_collection(next_link):
    first = (
        "https://management.azure.com/subscriptions/"
        f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
        "Microsoft.App/jobs?api-version=2024-03-01"
    )

    def escaped(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"value": [], "nextLink": next_link}).encode(),
            stderr=b"",
        )

    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.collect_arm_list(first, run=escaped)


def test_arm_pagination_rejects_semantic_loops_and_duplicate_membership():
    first = (
        "https://management.azure.com/subscriptions/"
        f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/"
        "Microsoft.App/jobs?api-version=2024-03-01"
    )
    second = first + "&$skiptoken=opaque"
    pages = [
        {"value": [{"id": "/jobs/a"}], "nextLink": second},
        {"value": [{"id": "/jobs/b"}], "nextLink": second},
    ]

    def looped(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(pages.pop(0)).encode(),
            stderr=b"",
        )

    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.collect_arm_list(first, run=looped)

    pages = [
        {"value": [{"id": "/jobs/a"}], "nextLink": second},
        {"value": [{"id": "/jobs/a"}]},
    ]

    def duplicated(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(pages.pop(0)).encode(),
            stderr=b"",
        )

    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.collect_arm_list(first, run=duplicated)


def _protected_job_body() -> dict[str, Any]:
    destination = _azure_destination()
    return {
        "location": "southeastasia",
        "identity": {
            "type": "UserAssigned",
            "userAssignedIdentities": {
                destination["managed_identity"]["resource_id"]: {}
            },
        },
        "tags": {
            "authorization-id": AUTHORIZATION,
            "launch-state": "claimed-for-start",
            "predictions-attempt-prefix-sha256": "1" * 64,
            "scores-attempt-prefix-sha256": "2" * 64,
            "visibility-attempt-prefix-sha256": "3" * 64,
            "current-attempt-binding-sha256": "4" * 64,
        },
        "properties": {
            "environmentId": destination["container_apps"][
                "environment_resource_id"
            ],
            "workloadProfileName": "Consumption",
            "configuration": {
                "triggerType": "Manual",
                "replicaTimeout": 3600,
                "replicaRetryLimit": 0,
                "manualTriggerConfig": {
                    "replicaCompletionCount": 1,
                    "parallelism": 1,
                },
                "registries": [
                    {
                        "server": destination["registry"]["login_server"],
                        "identity": destination["managed_identity"][
                            "resource_id"
                        ],
                    }
                ],
                "secrets": [],
            },
            "template": {
                "containers": [
                    {
                        "name": "parser-v2-locked-eval",
                        "image": destination["image"]["reference"],
                        "command": ["/workspace/bin/stage-p"],
                        "args": ["--authorization-id", AUTHORIZATION],
                        "env": [
                            {
                                "name": "AZURE_CLIENT_ID",
                                "value": destination["managed_identity"][
                                    "client_id"
                                ],
                            }
                        ],
                        "resources": {"cpu": 2.0, "memory": "4Gi"},
                        "volumeMounts": [],
                        "probes": [],
                    }
                ],
                "initContainers": [],
                "volumes": [],
            },
        },
    }


def test_job_projection_covers_every_code_and_data_injection_surface():
    expected = _protected_job_body()
    projection, digest = azure_contract.compare_job_with_body(expected, expected)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert projection["properties"]["template"]["initContainers"] == []
    assert projection["properties"]["template"]["volumes"] == []
    assert projection["properties"]["template"]["containers"][0]["probes"] == []
    mutators = [
        lambda body: body["properties"]["configuration"]["secrets"].append(
            {"name": "injected", "value": "secret"}
        ),
        lambda body: body["properties"]["template"]["initContainers"].append(
            {"name": "injected", "image": "attacker.invalid/image"}
        ),
        lambda body: body["properties"]["template"]["volumes"].append(
            {"name": "injected"}
        ),
        lambda body: body["properties"]["template"]["containers"].append(
            deepcopy(body["properties"]["template"]["containers"][0])
        ),
        lambda body: body["properties"]["template"]["containers"][0][
            "volumeMounts"
        ].append({"volumeName": "injected", "mountPath": "/workspace"}),
        lambda body: body["properties"]["template"]["containers"][0][
            "probes"
        ].append({"type": "Liveness"}),
        lambda body: body["properties"]["template"]["containers"][0].update(
            {"lifecycle": {"postStart": {"exec": {"command": ["sh"]}}}}
        ),
        lambda body: body["properties"]["template"].update(
            {"serviceBinds": [{"serviceId": "injected"}]}
        ),
        lambda body: body["properties"]["template"].update(
            {"terminationGracePeriodSeconds": 30}
        ),
        lambda body: body["properties"]["template"]["containers"][0].update(
            {"workingDir": "/injected"}
        ),
        lambda body: body["properties"]["template"]["containers"][0]["env"].append(
            {"name": "INJECTED", "secretRef": "secret"}
        ),
        lambda body: body["properties"]["configuration"].update(
            {"replicaRetryLimit": False}
        ),
        lambda body: body["properties"]["configuration"].update(
            {"replicaTimeout": 3600.0}
        ),
        lambda body: body["tags"].update(
            {"predictions-attempt-prefix-sha256": "9" * 64}
        ),
    ]
    for mutate in mutators:
        live = deepcopy(expected)
        mutate(live)
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.compare_job_with_body(live, expected)


def test_prediction_adoption_job_is_parser_disabled(workdir):
    launcher = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    builder = _extract_launcher_python(
        launcher,
        '"$IMPLEMENTATION_MANIFEST_SHA256" "$JOB_ID" <<\'PY\'\n',
        "\nPY\n\nJOB_BODY_SHA256=",
    )
    runtime_path = workdir / "runtime.json"
    stage_path = workdir / "stage.json"
    body_path = workdir / "job.json"
    runtime_path.write_bytes(RUNTIME_CONFIG_BYTES)
    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    producer_execution = f"stage-p-{'a' * 32}"
    stage_path.write_bytes(
        core.canonical_json_bytes(
            {
                "stage": "P",
                "verify_only": "false",
                "verification_state": "CLOSED",
                "retry_kind": "prediction_adoption",
                "execution_id": f"stage-p-{'b' * 32}",
                "actor": "stage-p-adoption-runtime",
                "locked_input_sha256": "",
                "locked_input_manifest_sha256": "",
                "prediction_manifest_sha256": "1" * 64,
                "labels_sha256": "",
                "labels_manifest_sha256": "",
                "scores_manifest_sha256": "",
                "closed_receipt_sha256": "",
                "prior_receipt_sha256": "2" * 64,
                "predictions_prefix": prefixes["predictions"],
                "scores_prefix": "",
                "visibility_prefix": prefixes["visibility"],
                "predictions_attempt_prefix_sha256": (
                    core.attempt_prefix_sha256(prefixes["predictions"])
                ),
                "scores_attempt_prefix_sha256": "",
                "visibility_attempt_prefix_sha256": (
                    core.attempt_prefix_sha256(prefixes["visibility"])
                ),
                "current_attempt_binding_sha256": (
                    core.attempt_binding_sha256(
                        "P",
                        "prediction_adoption",
                        f"stage-p-{'b' * 32}",
                    )
                ),
                "authenticated_prediction_retry_kind": "none",
                "authenticated_prediction_execution_id": producer_execution,
                "authenticated_scoring_retry_kind": "",
                "authenticated_scoring_execution_id": "",
                "producer_retry_kind": "none",
                "producer_execution_id": producer_execution,
                "expected_predictions_receipt_sha256": "3" * 64,
            }
        )
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            builder,
            str(runtime_path),
            str(stage_path),
            str(body_path),
            "pv2-launch-" + "1" * 32,
            "1" * 32,
            "prediction_adoption",
            "4" * 64,
            "5" * 64,
            core.sha256_bytes(IMPLEMENTATION_MANIFEST_BYTES),
            (
                f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
                "/providers/Microsoft.App/jobs/pv2-adopt"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    body = json.loads(body_path.read_text(encoding="utf-8"))
    container = body["properties"]["template"]["containers"][0]
    assert container["command"] == ["/workspace/bin/stage-p-adopt"]
    option_names = {
        token
        for token in container["args"]
        if isinstance(token, str) and token.startswith("--")
    }
    assert not any(
        "locked-input" in option or "parser" in option
        for option in option_names
    )
    assert "--prediction-manifest-sha256" in option_names
    assert "--producer-execution-id" in option_names


def test_invalid_closure_job_is_bound_to_original_scorer(workdir):
    launcher = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    builder = _extract_launcher_python(
        launcher,
        '"$IMPLEMENTATION_MANIFEST_SHA256" "$JOB_ID" <<\'PY\'\n',
        "\nPY\n\nJOB_BODY_SHA256=",
    )
    runtime_path = workdir / "runtime.json"
    stage_path = workdir / "stage.json"
    body_path = workdir / "job.json"
    runtime_path.write_bytes(RUNTIME_CONFIG_BYTES)
    prefixes = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    execution_id = f"stage-e-{'b' * 32}"
    producer_execution_id = f"stage-e-{'a' * 32}"
    visibility_prefix = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "E",
        "verification_only",
        execution_id,
    )
    stage_path.write_bytes(
        core.canonical_json_bytes(
            {
                "stage": "E",
                "verify_only": "true",
                "close_invalid_only": "true",
                "verification_state": "LABELS_READ",
                "retry_kind": "verification_only",
                "execution_id": execution_id,
                "actor": "stage-e-invalid-closure-runtime",
                "locked_input_sha256": "",
                "locked_input_manifest_sha256": "",
                "prediction_manifest_sha256": "1" * 64,
                "labels_sha256": "2" * 64,
                "labels_manifest_sha256": "3" * 64,
                "scores_manifest_sha256": "",
                "closed_receipt_sha256": "",
                "prior_receipt_sha256": "4" * 64,
                "predictions_prefix": prefixes["predictions"],
                "scores_prefix": prefixes["scores"],
                "visibility_prefix": visibility_prefix,
                "predictions_attempt_prefix_sha256": (
                    core.attempt_prefix_sha256(prefixes["predictions"])
                ),
                "scores_attempt_prefix_sha256": (
                    core.attempt_prefix_sha256(prefixes["scores"])
                ),
                "visibility_attempt_prefix_sha256": (
                    core.attempt_prefix_sha256(visibility_prefix)
                ),
                "current_attempt_binding_sha256": (
                    core.attempt_binding_sha256(
                        "E",
                        "verification_only",
                        execution_id,
                    )
                ),
                "authenticated_prediction_retry_kind": "none",
                "authenticated_prediction_execution_id": "stage-p-" + "c" * 32,
                "authenticated_scoring_retry_kind": "none",
                "authenticated_scoring_execution_id": producer_execution_id,
                "producer_retry_kind": "none",
                "producer_execution_id": producer_execution_id,
                "expected_predictions_receipt_sha256": "",
            }
        )
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            builder,
            str(runtime_path),
            str(stage_path),
            str(body_path),
            "pv2-launch-" + "1" * 32,
            "1" * 32,
            "invalid_closure",
            "5" * 64,
            "6" * 64,
            core.sha256_bytes(IMPLEMENTATION_MANIFEST_BYTES),
            (
                f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
                "/providers/Microsoft.App/jobs/pv2-close"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    body = json.loads(body_path.read_text(encoding="utf-8"))
    container = body["properties"]["template"]["containers"][0]
    assert container["command"] == ["/workspace/bin/stage-e"]
    assert "--close-invalid-only" in container["args"]
    assert "--verify-only" in container["args"]
    assert "--scores-manifest-sha256" not in container["args"]
    producer_index = container["args"].index("--producer-execution-id")
    assert container["args"][producer_index + 1] == producer_execution_id
    assert body["tags"]["invalid-closure-only"] == "true"


def test_launcher_job_put_and_start_are_dns_capability_dominated():
    launch = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    start_token = '"https://management.azure.com${JOB_ID}/start?api-version=2024-03-01"'
    assert launch.count(start_token) == 1
    start_index = launch.index(start_token)
    dispatch_create_index = launch.index(
        'raw_arm_request_once PUT "$DISPATCH_RECORD_URL"'
    )
    dispatch_gate_index = launch.index(
        'if [[ "$DISPATCH_CAPABILITY" ==', dispatch_create_index
    )
    assert dispatch_create_index < dispatch_gate_index < start_index
    assert '"$DISPATCH_CREATE_STATUS" == "201"' in launch[
        dispatch_create_index:dispatch_gate_index
    ]
    assert "GET cannot mint start capability" in launch[
        dispatch_create_index:start_index
    ]
    assert "if ! authenticate_exact_execution_baseline" in launch[
        dispatch_gate_index:start_index
    ]
    assert "validate-live-job-projection" in launch[
        dispatch_gate_index:start_index
    ]
    assert "only execution GET/list adoption follows" in launch[start_index:]
    assert "start must never be retried" in launch[start_index:]
    recovery_start = launch.index(
        'if [[ "$RECOVERY_ONLY" == "true" ]]; then\n'
        '    if [[ "$JOB_BODY_SHA256" != "$CLAIM_JOB_BODY_SHA256"'
    )
    recovery_end = launch.index(
        'if [[ -z "$EXECUTION_NAME" && "$RECOVERY_ONLY" == "true" ]]',
        recovery_start,
    )
    recovery_branch = launch[recovery_start:recovery_end]
    assert "authenticate_dispatch_txt_record" in recovery_branch
    assert "Recovery has no authenticated dispatch TXT record" in recovery_branch
    assert "raw_arm_request_once PUT" not in recovery_branch
    assert "/start?api-version=" not in recovery_branch

    snapshot_end = launch.index(
        "unset RUNTIME_CONFIG_SOURCE_FILE "
        "IMPLEMENTATION_MANIFEST_SOURCE_FILE"
    )
    after_snapshot = launch[snapshot_end:]
    assert "$RUNTIME_CONFIG_SOURCE_FILE" not in after_snapshot
    assert "$IMPLEMENTATION_MANIFEST_SOURCE_FILE" not in after_snapshot
    assert launch.count("$RUNTIME_CONFIG_SOURCE_FILE") == 1
    assert launch.count("$IMPLEMENTATION_MANIFEST_SOURCE_FILE") == 1
    assert (
        'python - "$RUNTIME_CONFIG_SNAPSHOT_FILE" '
        '"$STAGE_BINDINGS_FILE" "$BODY_FILE"'
    ) in after_snapshot
    assert '--runtime-config-file "$RUNTIME_CONFIG_SNAPSHOT_FILE"' in (
        after_snapshot
    )
    assert (
        '"$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE"' in after_snapshot
    )
    adoption_start = launch.index(
        'stage["retry_kind"] == "prediction_adoption"\n):',
        launch.index("common = ["),
    )
    adoption_end = launch.index(
        'elif stage["stage"] == "P":', adoption_start
    )
    adoption_branch = launch[adoption_start:adoption_end]
    assert "--locked-input" not in adoption_branch
    assert "--parser" not in adoption_branch
    assert '"P_ADOPT"' in launch[adoption_end:]
    assert "verify_immutable_launch_inputs" in launch[
        dispatch_gate_index:start_index
    ]
    assert (
        'az rest --method get --url "$BUILD_SLOT_RECORD_URL"' in launch
    )
    assert '--expected-domain-sha256 "$BUILD_SLOT_DOMAIN_SHA256"' in launch
    assert "live build TXT slot differs from the image binding" in launch
    job_put = 'raw_arm_request_once PUT "$JOB_URL"'
    assert launch.count(job_put) == 1
    job_put_index = launch.index(job_put)
    launch_create_index = launch.index(
        'raw_arm_request_once PUT "$LAUNCH_RECORD_URL"'
    )
    baseline_get = 'raw_arm_get_once "$JOB_URL" "$LIVE_JOB_FILE"'
    assert launch.count(baseline_get) == 1
    baseline_get_index = launch.index(baseline_get)
    assert baseline_get_index < launch_create_index
    baseline_gate = launch[baseline_get_index:launch_create_index]
    assert '200)' in baseline_gate
    assert '404)' in baseline_gate
    assert "Exact immutable Job baseline GET returned" in baseline_gate
    launch_gate_index = launch.index(
        'if [[ "$LAUNCH_CAPABILITY" ==', launch_create_index
    )
    assert launch_create_index < launch_gate_index < job_put_index
    assert '"$LAUNCH_CREATE_STATUS" == "201"' in launch[
        launch_create_index:launch_gate_index
    ]
    pre_job_get = (
        'raw_arm_get_once "$JOB_URL" "$PRE_JOB_PUT_GET_FILE"'
    )
    assert launch.count(pre_job_get) == 1
    pre_job_get_index = launch.index(pre_job_get)
    assert launch_gate_index < pre_job_get_index < job_put_index
    assert '"$PRE_JOB_PUT_GET_STATUS" != "404"' in launch[
        pre_job_get_index:job_put_index
    ]
    assert "GET cannot mint Job-PUT capability" in launch[
        launch_create_index:job_put_index
    ]
    job_ready_index = launch.index(
        "if ! wait_for_exact_ready_job;",
        job_put_index,
    )
    assert job_put_index < job_ready_index < dispatch_create_index
    raw_helper = launch[
        launch.index("raw_arm_request_once() {"):
        launch.index("readonly -f raw_arm_request_once")
    ]
    assert raw_helper.count("--request \"$method\"") == 1
    assert raw_helper.count("--retry 0") == 1
    assert raw_helper.count("--max-redirs 0") == 1
    assert 'headers+=(--header "If-None-Match: *")' in launch
    assert "az rest --method patch" not in launch
    assert "If-Match" not in launch
    assert "az containerapp job update" not in launch
    assert "launch-state=start-requested" not in launch
    launch_claim_creation = launch[
        launch.index('python - "$LAUNCH_CLAIM_VALUES_FILE"'):
        launch.index('raw_arm_request_once PUT "$LAUNCH_RECORD_URL"')
    ]
    dispatch_claim_creation = launch[
        launch.index('python - "$DISPATCH_CLAIM_VALUES_FILE"'):
        launch.index('raw_arm_request_once PUT "$DISPATCH_RECORD_URL"')
    ]
    for claim_creation in (launch_claim_creation, dispatch_claim_creation):
        for private_value in (
            "locked_reference_labels",
            "locked_inputs.jsonl",
            "labels_bytes",
            "output_text",
            "case_id",
        ):
            assert private_value not in claim_creation


def test_failed_launcher_reads_never_authenticate_capabilities(workdir):
    launch = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    bash = shutil.which("bash")
    if sys.platform == "win32":
        git = shutil.which("git")
        git_bash = (
            Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if git
            else None
        )
        if git_bash is not None and git_bash.is_file():
            bash = str(git_bash)
    if not bash:
        pytest.skip("Bash is unavailable")

    baseline_start = launch.index("authenticate_exact_execution_baseline() {")
    baseline_end = launch.index(
        "\n}\n\nderive_dispatch_domain_binding()",
        baseline_start,
    ) + 3
    baseline_function = launch[baseline_start:baseline_end]
    baseline_script = workdir / "baseline-failure.sh"
    baseline_script.write_text(
        f"""#!/bin/bash
set -u
{baseline_function}
scalar() {{
    local value
    value="$("$@" | tr -d '\\r')" || return 1
    printf '%s' "$value"
}}
python() {{
    local action="${{2:-}}"
    local field=""
    local output=""
    local index
    for ((index=1; index<=$#; index++)); do
        if [[ "${{!index}}" == "--output" ]]; then
            index=$((index + 1))
            output="${{!index}}"
        elif [[ "${{!index}}" == "--field" ]]; then
            index=$((index + 1))
            field="${{!index}}"
        fi
    done
    [[ "$FAIL_STEP" == "$action" ]] && return 9
    if [[ "$action" == "arm-list" ]]; then
        printf '[]\\n' >"$output"
    elif [[ "$action" == "execution-membership" ]]; then
        printf '{{"count":0,"sha256":"abc"}}\\n' >"$output"
    elif [[ "$action" == "get" ]]; then
        [[ "$FAIL_STEP" == "get-$field" ]] && return 9
        [[ "$field" == "count" ]] && printf '0\\n' || printf 'abc\\n'
    else
        return 9
    fi
}}
readonly -f python scalar
AZURE_HELPER=helper
EXECUTIONS_URL=https://management.azure.com/executions
EXECUTIONS_FILE='{(workdir / "executions.json").as_posix()}'
CURRENT_EXECUTION_MEMBERSHIP_FILE='{(workdir / "membership.json").as_posix()}'
CLAIM_PRIOR_EXECUTION_COUNT=0
CLAIM_PRIOR_EXECUTION_NAMES_SHA256=abc
for FAIL_STEP in arm-list execution-membership get-count get-sha256; do
    printf 'STALE\\n' >"$EXECUTIONS_FILE"
    printf 'STALE\\n' >"$CURRENT_EXECUTION_MEMBERSHIP_FILE"
    if authenticate_exact_execution_baseline; then
        exit 91
    fi
    grep -q STALE "$EXECUTIONS_FILE" && exit 92
    grep -q STALE "$CURRENT_EXECUTION_MEMBERSHIP_FILE" && exit 93
done
exit 0
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [bash, baseline_script.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    destination_start = launch.index("reauthenticate_runtime_destination() {")
    destination_end = launch.index(
        "\n}\n\nauthenticate_persisted_state()",
        destination_start,
    ) + 3
    destination_function = launch[destination_start:destination_end]
    destination_script = workdir / "coordination-failure.sh"
    paths = {
        name: (workdir / f"{name}.json").as_posix()
        for name in (
            "zone",
            "links",
            "lock",
            "validation",
            "build",
            "build_evidence",
        )
    }
    destination_script.write_text(
        f"""#!/bin/bash
set -u
{destination_function}
verify_immutable_launch_inputs() {{ return 0; }}
scalar() {{
    local value
    value="$("$@" | tr -d '\\r')" || return 1
    printf '%s' "$value"
}}
az() {{
    if [[ "${{1:-}}" == "account" ]]; then
        printf '%s\\n' "$SUBSCRIPTION_ID"
        return 0
    fi
    local url=""
    local index
    for ((index=1; index<=$#; index++)); do
        if [[ "${{!index}}" == "--url" ]]; then
            index=$((index + 1))
            url="${{!index}}"
        fi
    done
    if [[ "$FAIL_STEP" == "zone" && "$url" == *"/zone?"* ]] \
        || [[ "$FAIL_STEP" == "lock" && "$url" == *"/lock?"* ]] \
        || [[ "$FAIL_STEP" == "build" && "$url" == *"/TXT/build?"* ]]; then
        return 9
    fi
    printf '{{}}\\n'
}}
python() {{
    local action="${{2:-}}"
    local output=""
    local index
    for ((index=1; index<=$#; index++)); do
        if [[ "${{!index}}" == "--output" ]]; then
            index=$((index + 1))
            output="${{!index}}"
        fi
    done
    if [[ "$action" == "arm-list" ]]; then
        [[ "$FAIL_STEP" == "links" ]] && return 9
        printf '[]\\n' >"$output"
        return 0
    fi
    if [[ "$action" == "validate-coordination-zone" ]]; then
        printf '{{}}\\n' >"$output"
        printf '%s\\n' "$COORDINATION_BINDING_SHA256"
        return 0
    fi
    return 9
}}
readonly -f verify_immutable_launch_inputs scalar az python
SCRATCH_DIR='{workdir.as_posix()}'
SUBSCRIPTION_ID='{SUBSCRIPTION_ID}'
COORDINATION_ZONE_RESOURCE_ID=/zone
COORDINATION_LOCK_RESOURCE_ID=/lock
COORDINATION_DNS_API_VERSION=1
COORDINATION_LOCK_API_VERSION=1
COORDINATION_ZONE_FILE='{paths["zone"]}'
COORDINATION_LINKS_FILE='{paths["links"]}'
COORDINATION_LOCK_FILE='{paths["lock"]}'
COORDINATION_VALIDATION_FILE='{paths["validation"]}'
COORDINATION_BINDING_FILE='{(workdir / "binding.json").as_posix()}'
COORDINATION_BINDING_SHA256={'a' * 64}
BUILD_SLOT_RECORD_URL=https://management.azure.com/TXT/build?api-version=1
BUILD_SLOT_LIVE_FILE='{paths["build"]}'
BUILD_SLOT_EVIDENCE_FILE='{paths["build_evidence"]}'
BUILD_SLOT_RECORD_NAME=build
BUILD_SLOT_DOMAIN_SHA256={'b' * 64}
COORDINATION_RECORD_TTL=300
AZURE_HELPER=helper
for FAIL_STEP in zone links lock build; do
    for file in "$COORDINATION_ZONE_FILE" "$COORDINATION_LINKS_FILE" \
        "$COORDINATION_LOCK_FILE" "$COORDINATION_VALIDATION_FILE" \
        "$BUILD_SLOT_LIVE_FILE" "$BUILD_SLOT_EVIDENCE_FILE"; do
        printf 'STALE\\n' >"$file"
    done
    if reauthenticate_runtime_destination; then
        exit 94
    fi
    for file in "$COORDINATION_ZONE_FILE" "$COORDINATION_LINKS_FILE" \
        "$COORDINATION_LOCK_FILE" "$COORDINATION_VALIDATION_FILE" \
        "$BUILD_SLOT_LIVE_FILE" "$BUILD_SLOT_EVIDENCE_FILE"; do
        grep -q STALE "$file" && exit 95
    done
done
exit 0
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [bash, destination_script.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_build_task_run_put_is_dns_capability_dominated():
    build = (
        ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v2_eval.sh"
    ).read_text(encoding="utf-8")
    claim_put = 'raw_arm_request_once PUT "$BUILD_RECORD_URL"'
    task_put = 'raw_arm_request_once PUT "$TASK_RUN_URL"'
    gate = 'if [[ "$BUILD_CAPABILITY" =='
    assert build.count(claim_put) == 1
    assert build.count(task_put) == 1
    assert build.count(gate) == 1
    assert (
        '"$BUILD_TXT_BODY_FILE" "$BUILD_TXT_CREATE_RESPONSE_FILE" true)'
        in build
    )
    assert '"$TASK_RUN_BODY" "$TASK_RUN_RESPONSE_BODY" false)' in build
    claim_index = build.index(claim_put)
    gate_index = build.index(gate, claim_index)
    task_index = build.index(task_put)
    assert claim_index < gate_index < task_index
    pre_task_get = (
        'raw_arm_get_once "$TASK_RUN_URL" \\\n'
        '        "$TASK_RUN_PRE_PUT_GET_FILE"'
    )
    assert build.count(pre_task_get) == 1
    pre_task_get_index = build.index(pre_task_get)
    assert gate_index < pre_task_get_index < task_index
    assert '"$TASK_RUN_PRE_PUT_GET_STATUS" != "404"' in build[
        pre_task_get_index:task_index
    ]
    assert '"$BUILD_CREATE_STATUS" == "201"' in build[claim_index:gate_index]
    assert "GET-only recovery" in build[claim_index:gate_index]
    assert "only GET adoption follows" in build[task_index:]
    assert "Microsoft.Resources/deployments" not in build
    assert "If-Match" not in build
    coordination_start = build.index("authenticate_coordination_zone() {")
    coordination_end = build.index(
        "\n}\nif ! COORDINATION_BINDING_SHA256=",
        coordination_start,
    )
    coordination = build[coordination_start:coordination_end]
    for path in (
        "COORDINATION_ZONE_FILE",
        "COORDINATION_LINKS_FILE",
        "COORDINATION_LOCK_FILE",
        "COORDINATION_VALIDATION_FILE",
    ):
        assert f': >"${path}"' in coordination
    assert coordination.count("|| return 1") >= 4


def test_dns_raw_arm_paths_are_one_shot_and_obsolete_cas_is_absent():
    build = (
        ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v2_eval.sh"
    ).read_text(encoding="utf-8")
    launch = (
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    contract = (
        ROOT / "scripts" / "parser_v2_azure_contract.py"
    ).read_text(encoding="utf-8")
    for source in (build, launch):
        helper = source[
            source.index("raw_arm_request_once() {"):
            source.index("readonly -f raw_arm_request_once")
        ]
        for option in (
            "curl --disable --config -",
            "--proto '=https'",
            "--proto-redir '=https'",
            "--retry 0",
            "--max-redirs 0",
            "--connect-timeout 30",
            "--max-time 120",
        ):
            assert option in helper
        assert helper.count("| curl ") == 1
        assert 'Authorization: Bearer %s' in helper
        assert 'echo "$token"' not in helper
        assert "--config \"$token\"" not in helper
    for obsolete in (
        "Microsoft.Resources/deployments",
        "prepare_job_replacement_cas",
        "validate_job_replacement_cas",
        "prepare_build_start_cas",
        "validate_build_start_cas",
        "attach_http_response_etag",
        "launch-history",
        "phase05_claim_election",
    ):
        assert obsolete not in build
        assert obsolete not in launch
        assert obsolete not in contract


def test_azure_contract_cli_supplies_only_local_id_and_scalar_helpers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert azure_contract.main(["new-id"]) == 0
    assert re.fullmatch(r"[0-9a-f]{32}\n", capsys.readouterr().out)
    source = tmp_path / "values.json"
    source.write_text(
        '{"nested":{"count":2,"value":"exact"}}\n', encoding="ascii"
    )
    assert (
        azure_contract.main(
            ["get", "--json", str(source), "--field", "nested.value"]
        )
        == 0
    )
    assert capsys.readouterr().out == "exact\n"
    assert (
        azure_contract.main(
            ["get", "--json", str(source), "--field", "nested.count"]
        )
        == 0
    )
    assert capsys.readouterr().out == "2\n"


def _build_claim_values(nonce: str = "1" * 32) -> dict[str, Any]:
    return {
        "claim_nonce": nonce,
        "source_commit": IMPLEMENTATION,
        "task_run_name": "pv2tr-" + "4" * 20,
        "staging_tag": f"staging-{IMPLEMENTATION}-{nonce}",
        "task_run_resource_id_sha256": "1" * 64,
        "build_run_request_sha256": "2" * 64,
        "source_binding_sha256": "3" * 64,
        "build_provenance_sha256": "4" * 64,
        "coordination_binding_sha256": (
            azure_contract.coordination_binding_sha256(
                _coordination_binding()
            )
        ),
    }


def _claim_record(
    envelope: Mapping[str, Any],
    *,
    etag: str = '"dns-etag"',
) -> dict[str, Any]:
    coordination = _coordination_binding()
    name = azure_contract.dns_txt_record_name(
        envelope["kind"], envelope["domain_sha256"]
    )
    body = azure_contract.build_txt_record_set_body(
        envelope, ttl=coordination["record_ttl"]
    )
    return {
        "id": f"{coordination['zone_resource_id']}/TXT/{name}",
        "name": name,
        "type": "Microsoft.Network/privateDnsZones/TXT",
        "etag": etag,
        **body,
    }


def test_private_dns_txt_n_contenders_grant_one_ephemeral_capability():
    coordination = _coordination_binding()
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    name = azure_contract.dns_txt_record_name("build", domain)
    state: dict[str, Any] = {}
    put_counts = [0] * 8
    capabilities = []
    for index in range(8):
        nonce = f"{index + 1:032x}"
        envelope = azure_contract.build_claim_envelope(
            "build", domain, _build_claim_values(nonce)
        )

        def put(body, index=index, envelope=envelope):
            put_counts[index] += 1
            if not state:
                state["record"] = _claim_record(envelope)
                return 201, deepcopy(state["record"])
            return 412, {"error": {"code": "PreconditionFailed"}}

        capability = azure_contract.attempt_txt_record_create_once(
            put,
            lambda: deepcopy(state["record"]),
            request_body=azure_contract.build_txt_record_set_body(
                envelope, ttl=coordination["record_ttl"]
            ),
            zone_resource_id=coordination["zone_resource_id"],
            record_name=name,
            ttl=coordination["record_ttl"],
            expected_envelope=envelope,
        )
        capabilities.append(capability)
    assert put_counts == [1] * 8
    assert sum(
        isinstance(item, azure_contract.DnsCreateCapability)
        for item in capabilities
    ) == 1


@pytest.mark.parametrize(
    "status",
    (200, 202, 301, 307, 400, 409, 412, 429, 500, 503, 599),
)
def test_non_201_txt_create_status_grants_nothing_and_never_retries(status: int):
    coordination = _coordination_binding()
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    envelope = azure_contract.build_claim_envelope(
        "build", domain, _build_claim_values()
    )
    calls = {"put": 0, "get": 0}

    def put(_body):
        calls["put"] += 1
        return status, {"error": {"code": "synthetic"}}

    def get():
        calls["get"] += 1
        return _claim_record(envelope)

    assert azure_contract.attempt_txt_record_create_once(
        put,
        get,
        request_body=azure_contract.build_txt_record_set_body(
            envelope, ttl=coordination["record_ttl"]
        ),
        zone_resource_id=coordination["zone_resource_id"],
        record_name=azure_contract.dns_txt_record_name("build", domain),
        ttl=coordination["record_ttl"],
        expected_envelope=envelope,
    ) is None
    assert calls == {"put": 1, "get": 0}


@pytest.mark.parametrize("failure", (TimeoutError(), ConnectionResetError()))
def test_txt_create_transport_ambiguity_grants_nothing_once(failure: Exception):
    coordination = _coordination_binding()
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    envelope = azure_contract.build_claim_envelope(
        "build", domain, _build_claim_values()
    )
    calls = 0

    def put(_body):
        nonlocal calls
        calls += 1
        raise failure

    assert azure_contract.attempt_txt_record_create_once(
        put,
        lambda: _claim_record(envelope),
        request_body=azure_contract.build_txt_record_set_body(
            envelope, ttl=coordination["record_ttl"]
        ),
        zone_resource_id=coordination["zone_resource_id"],
        record_name=azure_contract.dns_txt_record_name("build", domain),
        ttl=coordination["record_ttl"],
        expected_envelope=envelope,
    ) is None
    assert calls == 1


def test_get_authenticates_txt_claim_but_cannot_mint_capability():
    coordination = _coordination_binding()
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    envelope = azure_contract.build_claim_envelope(
        "build", domain, _build_claim_values()
    )
    evidence = azure_contract.authenticate_existing_txt_record(
        _claim_record(envelope),
        zone_resource_id=coordination["zone_resource_id"],
        record_name=azure_contract.dns_txt_record_name("build", domain),
        ttl=coordination["record_ttl"],
        expected_kind="build",
        expected_domain_sha256=domain,
    )
    assert evidence["status"] == "TXT_RECORD_AUTHENTICATED"
    assert not isinstance(evidence, azure_contract.DnsCreateCapability)
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.DnsCreateCapability(
            object(),
            kind="build",
            domain_sha256=domain,
            record_name=evidence["record_name"],
        )


def test_txt_name_chunks_canonical_size_and_tamper_rejection():
    coordination = _coordination_binding()
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    envelope = azure_contract.build_claim_envelope(
        "build", domain, _build_claim_values()
    )
    name = azure_contract.dns_txt_record_name("build", domain)
    assert name == f"build-{domain[:32]}.{domain[32:]}"
    chunks = azure_contract.encode_txt_chunks(envelope)
    assert all(len(chunk.encode("ascii")) <= 255 for chunk in chunks)
    assert azure_contract.decode_txt_chunks(chunks) == envelope
    assert azure_contract.build_txt_record_set_body(
        envelope, ttl=coordination["record_ttl"]
    ) == {
        "properties": {
            "ttl": coordination["record_ttl"],
            "txtRecords": [{"value": chunks}],
        }
    }
    with pytest.raises(azure_contract.AzureContractError, match="exceeds"):
        azure_contract._canonical_ascii_bytes({"value": "x" * 4096})
    with pytest.raises(azure_contract.AzureContractError, match="membership"):
        azure_contract.decode_txt_chunks(["v1:00:01:AA"] * 33)
    record = _claim_record(envelope)
    assert azure_contract.validate_txt_record_set(
        record,
        zone_resource_id=coordination["zone_resource_id"],
        record_name=name,
        ttl=coordination["record_ttl"],
        expected_envelope=envelope,
    )["domain_sha256"] == domain
    mutations = []
    wrong_order = deepcopy(record)
    wrong_order["properties"]["txtRecords"][0]["value"] = list(
        reversed(wrong_order["properties"]["txtRecords"][0]["value"])
    )
    mutations.append(wrong_order)
    extra_record = deepcopy(record)
    extra_record["properties"]["txtRecords"].append({"value": ["v1:00:01:AA"]})
    mutations.append(extra_record)
    wrong_ttl = deepcopy(record)
    wrong_ttl["properties"]["ttl"] += 1
    mutations.append(wrong_ttl)
    wrong_id = deepcopy(record)
    wrong_id["id"] += "-forged"
    mutations.append(wrong_id)
    missing_etag = deepcopy(record)
    del missing_etag["etag"]
    mutations.append(missing_etag)
    malformed_etag = deepcopy(record)
    malformed_etag["etag"] = "etag with whitespace"
    mutations.append(malformed_etag)
    wrong_name = deepcopy(record)
    wrong_name["name"] += "-forged"
    mutations.append(wrong_name)
    for forged in mutations:
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.validate_txt_record_set(
                forged,
                zone_resource_id=coordination["zone_resource_id"],
                record_name=name,
                ttl=coordination["record_ttl"],
                expected_envelope=envelope,
            )


def test_claim_envelope_rejects_floats_secrets_labels_outputs_and_case_ids():
    domain = azure_contract.claim_domain_sha256(
        "build", {"immutable_sha256": "a" * 64}
    )
    for forbidden in (
        {"secret": "not-allowed"},
        {"raw_holdout": "not-allowed"},
        {"labels": ["not-allowed"]},
        {"outputs": {"not": "allowed"}},
        {"case_id": "private-case"},
    ):
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.claim_domain_sha256("build", forbidden)
    claims = _build_claim_values()
    for key, value in (
        ("secret", "credential"),
        ("labels", "private"),
        ("output", "private"),
        ("case_id", "private"),
    ):
        forged = {**claims, key: value}
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.build_claim_envelope("build", domain, forged)
    floated = deepcopy(claims)
    floated["baseline_execution_count"] = 1.0
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract._canonical_ascii_bytes(floated)


def test_launch_and_dispatch_claim_envelopes_are_exact_and_canonical():
    nonce = "2" * 32
    baseline = azure_contract.execution_membership([])
    launch_domain = azure_contract.claim_domain_sha256(
        "launch", {"immutable_sha256": "a" * 64}
    )
    launch_values = {
        "authorization_id": AUTHORIZATION,
        "claim_nonce": nonce,
        "stage": "P",
        "mode": "prediction",
        "retry_kind": "none",
        "execution_id": f"stage-p-{nonce}",
        "job_name": "pv2-p-" + "a" * 24,
        "job_resource_id_sha256": "1" * 64,
        "job_body_sha256": "2" * 64,
        "job_projection_sha256": "3" * 64,
        "baseline_execution_membership_sha256": baseline["sha256"],
        "baseline_execution_count": 0,
        "state_receipt_sha256": "4" * 64,
        "config_sha256": "5" * 64,
        "image_binding_sha256": "6" * 64,
        "helper_snapshot_set_sha256": "7" * 64,
        "implementation_manifest_sha256": "8" * 64,
        "authorization_lock_sha256": "9" * 64,
        "authorization_manifest_sha256": "a" * 64,
        "azure_destination_sha256": "b" * 64,
        "launcher_sha256": "c" * 64,
        "launcher_git_blob_oid": IMPLEMENTATION,
        "coordination_binding_sha256": "d" * 64,
    }
    launch = azure_contract.build_claim_envelope(
        "launch", launch_domain, launch_values
    )
    assert azure_contract.decode_txt_chunks(
        azure_contract.encode_txt_chunks(launch)
    ) == launch
    adoption_values = {
        **launch_values,
        "mode": "prediction_adoption",
        "retry_kind": "prediction_adoption",
    }
    adoption = azure_contract.build_claim_envelope(
        "launch", launch_domain, adoption_values
    )
    assert adoption["claims"]["mode"] == "prediction_adoption"
    for field, value in (
        ("mode", "prediction"),
        ("retry_kind", "none"),
    ):
        forged_adoption = {**adoption_values, field: value}
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.build_claim_envelope(
                "launch", launch_domain, forged_adoption
            )

    dispatch_domain = azure_contract.claim_domain_sha256(
        "dispatch", {"immutable_sha256": "e" * 64}
    )
    dispatch_values = {
        key: value
        for key, value in launch_values.items()
        if key
        not in {
            "stage",
            "mode",
            "retry_kind",
            "launcher_sha256",
            "launcher_git_blob_oid",
        }
    }
    dispatch_values.update(
        {
            "launch_record_name": azure_contract.dns_txt_record_name(
                "launch", launch_domain
            ),
            "launch_domain_sha256": launch_domain,
            "launch_record_etag_sha256": "e" * 64,
            "launch_payload_sha256": "f" * 64,
        }
    )
    dispatch = azure_contract.build_claim_envelope(
        "dispatch", dispatch_domain, dispatch_values
    )
    assert azure_contract.decode_txt_chunks(
        azure_contract.encode_txt_chunks(dispatch)
    ) == dispatch
    for envelope in (launch, dispatch):
        forged = deepcopy(envelope)
        forged["claims"]["unexpected"] = "private"
        with pytest.raises(azure_contract.AzureContractError, match="fields"):
            azure_contract.validate_claim_envelope(forged)


def _coordination_zone_records():
    binding = _coordination_binding()
    zone = {
        "id": binding["zone_resource_id"],
        "name": binding["zone_name"],
        "type": "Microsoft.Network/privateDnsZones",
        "location": "global",
        "properties": {
            "internalId": binding["zone_internal_id"],
            "provisioningState": "Succeeded",
            "numberOfVirtualNetworkLinks": 0,
            "numberOfVirtualNetworkLinksWithRegistration": 0,
        },
    }
    lock = {
        "id": binding["lock_resource_id"],
        "name": binding["lock_name"],
        "type": "Microsoft.Authorization/locks",
        "properties": {"level": "CanNotDelete"},
    }
    return binding, zone, [], lock


def test_coordination_zone_rejects_link_lock_or_recreation():
    binding, zone, links, lock = _coordination_zone_records()
    assert azure_contract.validate_coordination_zone(
        binding, zone, links, lock
    )["status"] == "COORDINATION_ZONE_AUTHENTICATED"
    opaque_internal_id = base64.b64encode(
        b"ImmutableZoneIdentity;44444444-4444-4444-8444-444444444444;0"
    ).decode("ascii")
    opaque_binding = {**binding, "zone_internal_id": opaque_internal_id}
    opaque_zone = deepcopy(zone)
    opaque_zone["properties"]["internalId"] = opaque_internal_id
    assert (
        azure_contract.validate_coordination_binding(opaque_binding)[
            "zone_internal_id"
        ]
        == opaque_internal_id
    )
    assert (
        core.validate_coordination_binding(opaque_binding)[
            "zone_internal_id"
        ]
        == opaque_internal_id
    )
    assert azure_contract.validate_coordination_zone(
        opaque_binding, opaque_zone, links, lock
    )["status"] == "COORDINATION_ZONE_AUTHENTICATED"
    case_changed = deepcopy(opaque_zone)
    case_changed["properties"]["internalId"] = (
        opaque_internal_id[0].swapcase() + opaque_internal_id[1:]
    )
    with pytest.raises(azure_contract.AzureContractError, match="recreated"):
        azure_contract.validate_coordination_zone(
            opaque_binding, case_changed, links, lock
        )
    for invalid_internal_id in ("not-base64", "A" * 16):
        invalid_binding = {
            **binding,
            "zone_internal_id": invalid_internal_id,
        }
        with pytest.raises(
            azure_contract.AzureContractError, match="internal ID"
        ):
            azure_contract.validate_coordination_binding(invalid_binding)
        with pytest.raises(core.LockedEvaluationError, match="internal ID"):
            core.validate_coordination_binding(invalid_binding)
    linked = [{"name": "forbidden-link"}]
    with pytest.raises(azure_contract.AzureContractError, match="zero VNet links"):
        azure_contract.validate_coordination_zone(
            binding, zone, linked, lock
        )
    unlocked = deepcopy(lock)
    unlocked["properties"]["level"] = "ReadOnly"
    with pytest.raises(azure_contract.AzureContractError, match="CanNotDelete"):
        azure_contract.validate_coordination_zone(
            binding, zone, links, unlocked
        )
    recreated = deepcopy(zone)
    recreated["properties"]["internalId"] = (
        "55555555-5555-4555-8555-555555555555"
    )
    with pytest.raises(azure_contract.AzureContractError, match="recreated"):
        azure_contract.validate_coordination_zone(
            binding, recreated, links, lock
        )
    blob_binding = deepcopy(binding)
    blob_binding["zone_name"] = "privatelink.blob.core.windows.net"
    blob_binding["zone_resource_id"] = (
        binding["zone_resource_id"].rsplit("/", 1)[0]
        + "/privatelink.blob.core.windows.net"
    )
    with pytest.raises(azure_contract.AzureContractError, match="must not be"):
        azure_contract.validate_coordination_binding(blob_binding)


def test_execution_membership_hash_and_remove_one_adoption():
    baseline = ["execution-a", "execution-b"]
    membership = azure_contract.execution_membership(baseline)
    assert membership["count"] == 2
    assert re.fullmatch(r"[0-9a-f]{64}", membership["sha256"])
    assert azure_contract.adopt_remove_one_execution(
        baseline, ["execution-a", "execution-b", "execution-c"]
    ) == "execution-c"
    for current in (
        baseline,
        ["execution-a", "execution-c"],
        ["execution-a", "execution-b", "execution-c", "execution-d"],
    ):
        with pytest.raises(
            azure_contract.AzureContractError, match="remove-one"
        ):
            azure_contract.adopt_remove_one_execution(baseline, current)


def _build_source_binding() -> dict[str, Any]:
    files = {}
    for index, path in enumerate(
        (
            "Dockerfile.parser-v2-eval",
            "requirements-parser-v2-eval.txt",
            "scripts/parser_v2_azure_contract.py",
        ),
        start=1,
    ):
        files[path] = {
            "git_blob_oid": f"{index:x}" * 40,
            "sha256": f"{index + 3:x}" * 64,
            "size": index * 100,
        }
    return {
        "schema_version": (
            azure_contract.BUILD_SOURCE_BINDING_SCHEMA_VERSION
        ),
        "source_commit": IMPLEMENTATION,
        "source_repository_url": (
            azure_contract.BUILD_SOURCE_REPOSITORY_URL
        ),
        "remote_source_location": (
            f"{azure_contract.BUILD_SOURCE_REPOSITORY_URL}#{IMPLEMENTATION}"
        ),
        "base_image": BASE_IMAGE,
        "image_repository": "j-space-observation-parser-eval",
        "files": files,
    }


def _build_provenance() -> tuple[dict[str, Any], str]:
    record = azure_contract.build_provenance_record(
        _build_source_binding(),
        acr_resource_id=(
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
            "/providers/Microsoft.ContainerRegistry/registries/"
            "syntheticregistry"
        ),
        login_server="syntheticregistry.azurecr.io",
        acr_location="eastasia",
        coordination_binding=_coordination_binding(),
    )
    return record, azure_contract.build_provenance_sha256(record)


def _acr_task_run(
    provenance: Mapping[str, Any],
    provenance_sha256: str,
    *,
    status: str = "Succeeded",
) -> tuple[dict[str, Any], str]:
    tag = f"staging-{IMPLEMENTATION}-{'1' * 32}"
    request = azure_contract.build_acr_run_request(
        build_provenance=provenance,
        build_provenance_sha256_value=provenance_sha256,
        staging_tag=tag,
    )
    request_sha256 = hashlib.sha256(
        azure_contract._canonical_bytes(request)
    ).hexdigest()
    outputs = []
    if status == "Succeeded":
        outputs.append(
            {
                "registry": provenance["acr"]["login_server"],
                "repository": provenance["acr"]["repository"],
                "tag": tag,
                "digest": IMAGE_DIGEST,
            }
        )
    task_run_name = "pv2tr-" + "4" * 20
    acr_id = provenance["acr"]["resource_id"]
    run = {
        "id": f"{acr_id}/runs/ca1",
        "name": "ca1",
        "type": "Microsoft.ContainerRegistry/registries/runs",
        "properties": {
            "runId": "ca1",
            "runType": "QuickRun",
            "status": status,
            "outputImages": outputs,
        },
    }
    return (
        {
            "id": f"{acr_id}/taskRuns/{task_run_name}",
            "name": task_run_name,
            "type": "Microsoft.ContainerRegistry/registries/taskRuns",
            "location": provenance["acr"]["location"],
            "properties": {
                "provisioningState": "Succeeded",
                "forceUpdateTag": request_sha256,
                "runRequest": request,
                "runResult": run,
            },
        },
        tag,
    )


def _live_image_binding_inputs() -> tuple[
    bytes, str, dict[str, Any], bytes, bytes
]:
    binding = deepcopy(IMAGE_BINDING)
    provenance_sha256 = binding["build_provenance_sha256"]
    config_bytes = azure_contract._canonical_bytes(
        {
            "config": {
                "Labels": {
                    azure_contract.BUILD_PROVENANCE_LABEL: (
                        provenance_sha256
                    )
                }
            }
        }
    )
    config_digest = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    manifest_bytes = azure_contract._canonical_bytes(
        {
            "schemaVersion": 2,
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": config_digest,
                "size": len(config_bytes),
            },
            "layers": [],
        }
    )
    image_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    oci = azure_contract.validate_oci_image_artifacts(
        manifest_bytes,
        config_bytes,
        expected_manifest_digest=image_digest,
        expected_provenance_sha256=provenance_sha256,
    )
    task_run, _ = _acr_task_run(
        binding["build_provenance"], provenance_sha256
    )
    task_run["properties"]["runResult"]["properties"]["outputImages"][0][
        "digest"
    ] = image_digest
    binding.update(
        {
            "image_digest": image_digest,
            "image_digest_ref": (
                f"{binding['build_provenance']['acr']['login_server']}/"
                f"{binding['image_repository']}@{image_digest}"
            ),
            "acr_build_task_run_name": task_run["name"],
            "acr_build_task_run_resource_id": task_run["id"],
            "acr_build_run_id": task_run["properties"]["runResult"][
                "properties"
            ]["runId"],
            "build_run_request_sha256": hashlib.sha256(
                azure_contract._canonical_bytes(
                    task_run["properties"]["runRequest"]
                )
            ).hexdigest(),
            "oci_verification": oci,
            "oci_verification_sha256": (
                azure_contract.oci_verification_evidence_sha256(oci)
            ),
        }
    )
    binding_bytes = core.canonical_json_bytes(binding)
    binding_sha256 = core.sha256_bytes(binding_bytes)
    assert core.validate_image_binding(
        binding_bytes,
        expected_sha256=binding_sha256,
        expected_source_commit=IMPLEMENTATION,
    ) == binding
    return (
        binding_bytes,
        binding_sha256,
        task_run,
        manifest_bytes,
        config_bytes,
    )


def test_live_image_binding_authenticates_complete_persisted_evidence():
    binding_bytes, binding_sha, task_run, manifest, config = (
        _live_image_binding_inputs()
    )
    binding = core.parse_json_strict(binding_bytes, "image binding")
    checked = azure_contract.validate_live_image_binding(
        binding_bytes,
        expected_sha256=binding_sha,
        live_task_run=task_run,
        manifest_bytes=manifest,
        config_bytes=config,
        resolved_final_digest=binding["image_digest"],
        tag_write_enabled="false",
        tag_delete_enabled="false",
        manifest_write_enabled="false",
        manifest_delete_enabled="false",
        expected_source_commit=IMPLEMENTATION,
        expected_acr_resource_id=(
            binding["build_provenance"]["acr"]["resource_id"]
        ),
        expected_login_server=(
            binding["build_provenance"]["acr"]["login_server"]
        ),
        expected_repository=binding["image_repository"],
    )
    assert checked["status"] == "LIVE_IMAGE_BINDING_AUTHENTICATED"
    assert checked["image_binding_sha256"] == binding_sha
    official_shape = deepcopy(task_run)
    official_shape["type"] = (
        "microsoft.containerregistry/registries/taskruns"
    )
    del official_shape["location"]
    assert azure_contract.validate_live_image_binding(
        binding_bytes,
        expected_sha256=binding_sha,
        live_task_run=official_shape,
        manifest_bytes=manifest,
        config_bytes=config,
        resolved_final_digest=binding["image_digest"],
        tag_write_enabled="false",
        tag_delete_enabled="false",
        manifest_write_enabled="false",
        manifest_delete_enabled="false",
        expected_source_commit=IMPLEMENTATION,
        expected_acr_resource_id=(
            binding["build_provenance"]["acr"]["resource_id"]
        ),
        expected_login_server=(
            binding["build_provenance"]["acr"]["login_server"]
        ),
        expected_repository=binding["image_repository"],
    )["status"] == "LIVE_IMAGE_BINDING_AUTHENTICATED"
    wrong_location = deepcopy(task_run)
    wrong_location["location"] = "westus"
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_live_image_binding(
            binding_bytes,
            expected_sha256=binding_sha,
            live_task_run=wrong_location,
            manifest_bytes=manifest,
            config_bytes=config,
            resolved_final_digest=binding["image_digest"],
            tag_write_enabled="false",
            tag_delete_enabled="false",
            manifest_write_enabled="false",
            manifest_delete_enabled="false",
            expected_source_commit=IMPLEMENTATION,
            expected_acr_resource_id=(
                binding["build_provenance"]["acr"]["resource_id"]
            ),
            expected_login_server=(
                binding["build_provenance"]["acr"]["login_server"]
            ),
            expected_repository=binding["image_repository"],
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "build-run",
        "task-run",
        "missing-run-request-field",
        "source-location",
        "oci-config",
        "final-digest",
        "tag-lock",
        "missing-lock-evidence",
        "manifest-lock",
    ),
)
def test_live_image_binding_rejects_wrong_build_source_oci_and_locks(
    mutation: str,
):
    binding_bytes, binding_sha, task_run, manifest, config = (
        _live_image_binding_inputs()
    )
    binding = core.parse_json_strict(binding_bytes, "image binding")
    resolved_digest = binding["image_digest"]
    tag_write = tag_delete = manifest_write = manifest_delete = "false"
    if mutation == "build-run":
        task_run["properties"]["runResult"]["name"] = "ca2"
        task_run["properties"]["runResult"]["properties"]["runId"] = "ca2"
    elif mutation == "task-run":
        task_run["name"] = "pv2tr-" + "5" * 20
    elif mutation == "missing-run-request-field":
        del task_run["properties"]["runRequest"]["sourceLocation"]
    elif mutation == "source-location":
        task_run["properties"]["runRequest"]["sourceLocation"] = (
            f"{azure_contract.BUILD_SOURCE_REPOSITORY_URL}#{'2' * 40}"
        )
    elif mutation == "oci-config":
        config += b" "
    elif mutation == "final-digest":
        resolved_digest = "sha256:" + "9" * 64
    elif mutation == "tag-lock":
        tag_write = "true"
    elif mutation == "missing-lock-evidence":
        tag_delete = ""
    elif mutation == "manifest-lock":
        manifest_delete = "true"
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_live_image_binding(
            binding_bytes,
            expected_sha256=binding_sha,
            live_task_run=task_run,
            manifest_bytes=manifest,
            config_bytes=config,
            resolved_final_digest=resolved_digest,
            tag_write_enabled=tag_write,
            tag_delete_enabled=tag_delete,
            manifest_write_enabled=manifest_write,
            manifest_delete_enabled=manifest_delete,
            expected_source_commit=IMPLEMENTATION,
            expected_acr_resource_id=(
                binding["build_provenance"]["acr"]["resource_id"]
            ),
            expected_login_server=(
                binding["build_provenance"]["acr"]["login_server"]
            ),
            expected_repository=binding["image_repository"],
        )


def test_image_binding_requires_canonical_exact_record_and_immutable_locks():
    noncanonical = (json.dumps(IMAGE_BINDING, indent=2) + "\n").encode()
    with pytest.raises(core.LockedEvaluationError, match="not canonical ASCII"):
        core.validate_image_binding(
            noncanonical,
            expected_sha256=core.sha256_bytes(noncanonical),
        )
    forged = deepcopy(IMAGE_BINDING)
    forged["changeable_attributes"]["tag_write_enabled"] = True
    forged_bytes = core.canonical_json_bytes(forged)
    with pytest.raises(core.LockedEvaluationError, match="not immutable"):
        core.validate_image_binding(
            forged_bytes,
            expected_sha256=core.sha256_bytes(forged_bytes),
        )
    forged = deepcopy(IMAGE_BINDING)
    forged["changeable_attributes"]["tag_write_enabled"] = 0
    forged_bytes = core.canonical_json_bytes(forged)
    with pytest.raises(core.LockedEvaluationError, match="not immutable"):
        core.validate_image_binding(
            forged_bytes,
            expected_sha256=core.sha256_bytes(forged_bytes),
        )
    with pytest.raises(core.LockedEvaluationError, match="source commit mismatch"):
        core.validate_image_binding(
            IMAGE_BINDING_BYTES,
            expected_sha256=IMAGE_BINDING_SHA256,
            expected_source_commit="2" * 40,
        )
    for expected in (
        {
            "expected_acr_resource_id": (
                f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
                "/providers/Microsoft.ContainerRegistry/registries/other"
            )
        },
        {"expected_login_server": "other.azurecr.io"},
        {"expected_repository": "other/repository"},
    ):
        with pytest.raises(core.LockedEvaluationError, match="mismatch"):
            core.validate_image_binding(
                IMAGE_BINDING_BYTES,
                expected_sha256=IMAGE_BINDING_SHA256,
                **expected,
            )
    for field, value in (
        ("base_image", "python:3.11@sha256:" + "8" * 64),
        ("image_tag", "2" * 40),
        ("acr_build_task_run_name", "not/a/task"),
        (
            "acr_build_task_run_resource_id",
            "/subscriptions/forged/taskRuns/forged",
        ),
        ("acr_build_run_id", "not/a/run"),
        ("build_run_request_sha256", "not-a-hash"),
    ):
        forged = deepcopy(IMAGE_BINDING)
        forged[field] = value
        forged_bytes = core.canonical_json_bytes(forged)
        with pytest.raises(core.LockedEvaluationError):
            core.validate_image_binding(
                forged_bytes,
                expected_sha256=core.sha256_bytes(forged_bytes),
            )


def test_build_provenance_is_canonical_and_binds_every_build_input():
    provenance, digest = _build_provenance()
    source = _build_source_binding()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert provenance["source_binding"] == source
    assert provenance["source_binding_sha256"] == hashlib.sha256(
        azure_contract._canonical_bytes(source)
    ).hexdigest()
    assert provenance["build_context"]["registered_paths"] == sorted(
        source["files"]
    )
    assert provenance["build_context"]["dockerfile"] == {
        "path": "Dockerfile.parser-v2-eval",
        **source["files"]["Dockerfile.parser-v2-eval"],
    }
    assert provenance["build_context"]["dependencies"] == [
        {
            "path": "requirements-parser-v2-eval.txt",
            **source["files"]["requirements-parser-v2-eval.txt"],
        }
    ]
    assert provenance["expected_run_request"]["platform"] == {
        "os": "Linux",
        "architecture": "amd64",
    }
    assert provenance["remote_source"] == {
        "repository_url": azure_contract.BUILD_SOURCE_REPOSITORY_URL,
        "commit": IMPLEMENTATION,
        "source_location": (
            f"{azure_contract.BUILD_SOURCE_REPOSITORY_URL}#{IMPLEMENTATION}"
        ),
    }
    assert set(provenance["expected_run_request"]["fields"]) == (
        azure_contract.BUILD_RUN_REQUEST_FIELDS
    )
    assert provenance["expected_images"]["final_name"].endswith(
        f":{IMPLEMENTATION}"
    )
    forged = deepcopy(provenance)
    forged["source_binding"]["files"][
        "Dockerfile.parser-v2-eval"
    ]["size"] += 1
    with pytest.raises(
        azure_contract.AzureContractError, match="not canonical"
    ):
        azure_contract.validate_build_provenance(
            forged, expected_sha256=digest
        )


def test_remote_build_source_rejects_alternate_url_commit_query_or_ref():
    repository = azure_contract.BUILD_SOURCE_REPOSITORY_URL
    expected = f"{repository}#{IMPLEMENTATION}"
    assert (
        azure_contract.exact_remote_git_source(repository, IMPLEMENTATION)
        == expected
    )
    assert (
        azure_contract.validate_remote_git_source(
            expected,
            repository_url=repository,
            source_commit=IMPLEMENTATION,
        )
        == expected
    )
    for forged in (
        f"https://example.com/Alanjiao1988/J-space-observation.git#{IMPLEMENTATION}",
        f"https://github.com/other/J-space-observation.git#{IMPLEMENTATION}",
        f"{repository}#{'9' * 40}",
        f"{repository}?download=1#{IMPLEMENTATION}",
        f"{repository}#main",
        f"{repository}#refs/heads/main",
    ):
        with pytest.raises(azure_contract.AzureContractError):
            azure_contract.validate_remote_git_source(
                forged,
                repository_url=repository,
                source_commit=IMPLEMENTATION,
            )
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.exact_remote_git_source(
            "https://github.com/Alanjiao1988/J-space-observation",
            IMPLEMENTATION,
        )


def test_runtime_source_binding_ignores_git_replacement_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(tmp_path), *arguments],
            check=True,
            capture_output=True,
        )
        return completed.stdout.decode("ascii").strip()

    git("init", "--quiet")
    git("config", "user.email", "synthetic@example.invalid")
    git("config", "user.name", "Synthetic Test")
    source = tmp_path / "source.txt"
    source.write_text("original\n", encoding="ascii")
    git("add", "source.txt")
    git("commit", "--quiet", "-m", "original")
    original_commit = git("rev-parse", "HEAD")
    original_oid = git(
        "--no-replace-objects",
        "rev-parse",
        f"{original_commit}:source.txt",
    )
    source.write_text("replacement\n", encoding="ascii")
    git("commit", "--quiet", "-am", "replacement")
    replacement_commit = git("rev-parse", "HEAD")
    git("replace", original_commit, replacement_commit)
    assert git("rev-parse", f"{original_commit}:source.txt") != original_oid

    monkeypatch.setattr(runtime_config_generator, "PROJECT_ROOT", tmp_path)
    binding = runtime_config_generator._git_blob_binding(
        original_commit, "source.txt"
    )
    assert binding["git_blob_oid"] == original_oid
    assert binding["sha256"] == hashlib.sha256(b"original\n").hexdigest()


def test_runtime_generator_loads_only_committed_core_and_validator_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(tmp_path), *arguments],
            check=True,
            capture_output=True,
        )
        return completed.stdout.decode("ascii").strip()

    git("init", "--quiet")
    git("config", "user.email", "synthetic@example.invalid")
    git("config", "user.name", "Synthetic Test")
    validator_path = tmp_path / "validator.py"
    core_path = tmp_path / "core.py"
    validator_source = (
        b'CONSTRUCTION_STATES = ("A",)\n'
        b'EVALUATION_STATES = ("B",)\n'
        b'STATE_AUTHORIZED_ARTIFACT_BINDINGS = {"A": frozenset({"x"})}\n'
        b'MARKER = "committed-validator"\n'
    )
    validator_sha256 = hashlib.sha256(validator_source).hexdigest()
    core_source = (
        f'_FROZEN_EVALUATOR_VALIDATION_SHA256 = "{validator_sha256}"\n'
        'ACTIVE_PARSER_PROFILE_ID = globals().pop(\n'
        '    "_PRESEEDED_PARSER_PROFILE_ID", "parser-v2-v1"\n'
        ")\n"
        'CONSTRUCTION_STATE_SEQUENCE = ("A",)\n'
        'EVALUATION_STATE_SEQUENCE = ("B",)\n'
        'STATE_AUTHORIZED_ARTIFACT_BINDINGS = {"A": frozenset({"x"})}\n'
        'MARKER = "committed-core"\n'
        "def _load_frozen_validation():\n"
        '    raise RuntimeError("mutable path loader must be replaced")\n'
    ).encode("ascii")
    validator_path.write_bytes(validator_source)
    core_path.write_bytes(core_source)
    git("add", "core.py", "validator.py")
    git("commit", "--quiet", "-m", "committed helpers")
    commit = git("rev-parse", "HEAD")
    monkeypatch.setattr(runtime_config_generator, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        runtime_config_generator, "CORE_RELATIVE_PATH", "core.py"
    )
    monkeypatch.setattr(
        runtime_config_generator,
        "FROZEN_VALIDATION_RELATIVE_PATH",
        "validator.py",
    )

    core_module = runtime_config_generator._load_core(commit)
    assert core_module.MARKER == "committed-core"
    assert (
        core_module._load_frozen_validation().MARKER
        == "committed-validator"
    )

    core_path.write_text('MARKER = "mutable-core"\n', encoding="ascii")
    validator_path.write_text(
        'MARKER = "mutable-validator"\n', encoding="ascii"
    )
    reloaded = runtime_config_generator._load_core(commit)
    assert reloaded.MARKER == "committed-core"
    assert (
        reloaded._load_frozen_validation().MARKER
        == "committed-validator"
    )


def _validate_task_run(
    task_run: Mapping[str, Any],
    provenance: Mapping[str, Any],
    provenance_sha256: str,
    tag: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return azure_contract.validate_acr_task_run(
        task_run,
        expected_task_run_name="pv2tr-" + "4" * 20,
        expected_acr_resource_id=provenance["acr"]["resource_id"],
        build_provenance=provenance,
        build_provenance_sha256_value=provenance_sha256,
        staging_tag=tag,
        **kwargs,
    )


def test_acr_task_run_body_and_response_bind_exact_full_provenance():
    provenance, provenance_sha256 = _build_provenance()
    task_run, tag = _acr_task_run(provenance, provenance_sha256)
    body = azure_contract.build_acr_task_run_body(
        build_provenance=provenance,
        build_provenance_sha256_value=provenance_sha256,
        staging_tag=tag,
    )
    request = body["properties"]["runRequest"]
    assert set(request) == azure_contract.BUILD_RUN_REQUEST_FIELDS
    assert body["properties"]["forceUpdateTag"] == hashlib.sha256(
        azure_contract._canonical_bytes(request)
    ).hexdigest()
    accepted = _validate_task_run(
        task_run,
        provenance,
        provenance_sha256,
        tag,
        require_succeeded=True,
        expected_digest=IMAGE_DIGEST,
        expected_run_id="ca1",
    )
    assert accepted["output_digest"] == IMAGE_DIGEST
    assert accepted["task_run_name"] == "pv2tr-" + "4" * 20
    assert accepted["build_provenance_sha256"] == provenance_sha256
    response_without_empty_credentials = deepcopy(task_run)
    del response_without_empty_credentials["properties"]["runRequest"][
        "credentials"
    ]
    normalized = _validate_task_run(
        response_without_empty_credentials,
        provenance,
        provenance_sha256,
        tag,
        require_succeeded=True,
        expected_digest=IMAGE_DIGEST,
        expected_run_id="ca1",
        expected_run_request_sha256=accepted["run_request_sha256"],
    )
    assert normalized["run_request_sha256"] == accepted["run_request_sha256"]
    response_without_force_tag = deepcopy(task_run)
    del response_without_force_tag["properties"]["forceUpdateTag"]
    assert _validate_task_run(
        response_without_force_tag,
        provenance,
        provenance_sha256,
        tag,
        require_succeeded=True,
        expected_digest=IMAGE_DIGEST,
    )["run_id"] == "ca1"


def test_acr_task_run_rejects_missing_or_forged_request_fields():
    provenance, provenance_sha256 = _build_provenance()
    task_run, tag = _acr_task_run(provenance, provenance_sha256)
    mutations = [
        (
            lambda value, field=field: value["properties"][
                "runRequest"
            ].pop(field)
        )
        for field in azure_contract.BUILD_RUN_REQUEST_FIELDS - {"credentials"}
    ]
    mutations.extend(
        (
            lambda value: value["properties"]["runRequest"].update(
                {"dockerFilePath": "Dockerfile"}
            ),
            lambda value: value["properties"]["runRequest"].update(
                {"platform": {"os": "Linux", "architecture": "arm64"}}
            ),
            lambda value: value["properties"]["runRequest"].update(
                {"imageNames": ["j-space-observation-parser-eval:wrong"]}
            ),
            lambda value: value["properties"]["runRequest"][
                "arguments"
            ][1].update({"value": "9" * 64}),
            lambda value: value["properties"]["runRequest"][
                "arguments"
            ].pop(),
            lambda value: value["properties"]["runRequest"][
                "arguments"
            ][0].update({"isSecret": True}),
            lambda value: value["properties"]["runRequest"].update(
                {"extraControl": True}
            ),
            lambda value: value["properties"]["runRequest"].update(
                {"credentials": {"sourceRegistry": "forbidden"}}
            ),
        )
    )
    for mutate in mutations:
        forged = deepcopy(task_run)
        mutate(forged)
        with pytest.raises(azure_contract.AzureContractError):
            _validate_task_run(
                forged,
                provenance,
                provenance_sha256,
                tag,
                require_succeeded=True,
            )


def test_acr_task_run_rejects_forged_resource_force_tag_or_child_run():
    provenance, provenance_sha256 = _build_provenance()
    task_run, tag = _acr_task_run(provenance, provenance_sha256)
    mutations = (
        lambda value: value.update({"name": "pv2tr-" + "5" * 20}),
        lambda value: value.update({"id": value["id"] + "-forged"}),
        lambda value: value.update({"location": "westus"}),
        lambda value: value.update(
            {"identity": {"type": "SystemAssigned"}}
        ),
        lambda value: value["properties"].update(
            {"forceUpdateTag": "9" * 64}
        ),
        lambda value: value["properties"]["runResult"].update(
            {"type": "Microsoft.ContainerRegistry/registries/tasks"}
        ),
        lambda value: value["properties"]["runResult"].update(
            {"id": provenance["acr"]["resource_id"] + "/runs/ca2"}
        ),
        lambda value: value["properties"]["runResult"]["properties"].update(
            {"runType": "QuickBuild"}
        ),
        lambda value: value["properties"]["runResult"]["properties"].update(
            {"runRequest": value["properties"]["runRequest"]}
        ),
    )
    for mutate in mutations:
        forged = deepcopy(task_run)
        mutate(forged)
        with pytest.raises(azure_contract.AzureContractError):
            _validate_task_run(
                forged,
                provenance,
                provenance_sha256,
                tag,
                require_succeeded=True,
            )


def test_acr_task_run_allows_authenticated_pre_run_provisioning_only():
    provenance, provenance_sha256 = _build_provenance()
    task_run, tag = _acr_task_run(provenance, provenance_sha256)
    task_run["properties"]["provisioningState"] = "Creating"
    del task_run["properties"]["runResult"]
    checked = _validate_task_run(
        task_run, provenance, provenance_sha256, tag
    )
    assert checked["status"] == "Creating"
    assert checked["run_id"] is None
    with pytest.raises(azure_contract.AzureContractError):
        _validate_task_run(
            task_run,
            provenance,
            provenance_sha256,
            tag,
            require_succeeded=True,
        )


def test_acr_task_run_rejects_wrong_output_image_or_provenance():
    provenance, provenance_sha256 = _build_provenance()
    task_run, tag = _acr_task_run(provenance, provenance_sha256)
    outputs = task_run["properties"]["runResult"]["properties"][
        "outputImages"
    ]
    for field, value in (
        ("registry", "other.azurecr.io"),
        ("repository", "other"),
        ("tag", f"staging-{IMPLEMENTATION}-{'2' * 32}"),
        ("digest", "sha256:" + "9" * 64),
    ):
        forged = deepcopy(task_run)
        forged["properties"]["runResult"]["properties"]["outputImages"][0][
            field
        ] = value
        with pytest.raises(azure_contract.AzureContractError):
            _validate_task_run(
                forged,
                provenance,
                provenance_sha256,
                tag,
                require_succeeded=True,
                expected_digest=IMAGE_DIGEST,
            )
    forged = deepcopy(task_run)
    forged["properties"]["runResult"]["properties"]["outputImages"] = []
    with pytest.raises(azure_contract.AzureContractError):
        _validate_task_run(
            forged,
            provenance,
            provenance_sha256,
            tag,
            require_succeeded=True,
        )
    assert len(outputs) == 1
    with pytest.raises(
        azure_contract.AzureContractError, match="provenance SHA-256"
    ):
        _validate_task_run(
            task_run,
            provenance,
            "8" * 64,
            tag,
            require_succeeded=True,
        )


def test_acr_task_run_crash_recovery_is_get_only_and_reauthenticates():
    provenance, provenance_sha256 = _build_provenance()
    running, tag = _acr_task_run(
        provenance, provenance_sha256, status="Running"
    )
    discovered = _validate_task_run(
        running, provenance, provenance_sha256, tag
    )
    assert discovered["status"] == "Running"
    assert discovered["output_digest"] is None
    completed, _ = _acr_task_run(provenance, provenance_sha256)
    winning = _validate_task_run(
        completed,
        provenance,
        provenance_sha256,
        tag,
        require_succeeded=True,
    )
    recovered = _validate_task_run(
        deepcopy(completed),
        provenance,
        provenance_sha256,
        tag,
        require_succeeded=True,
        expected_digest=winning["output_digest"],
        expected_run_id=winning["run_id"],
        expected_run_request_sha256=winning["run_request_sha256"],
    )
    assert recovered == winning
    changed = deepcopy(completed)
    changed["properties"]["runRequest"]["sourceLocation"] += "&changed=1"
    with pytest.raises(azure_contract.AzureContractError):
        _validate_task_run(
            changed,
            provenance,
            provenance_sha256,
            tag,
            require_succeeded=True,
            expected_digest=winning["output_digest"],
            expected_run_id=winning["run_id"],
            expected_run_request_sha256=winning[
                "run_request_sha256"
            ],
        )


def test_oci_image_config_label_binds_build_provenance():
    _, provenance_sha256 = _build_provenance()
    config = json.dumps(
        {
            "config": {
                "Labels": {
                    azure_contract.BUILD_PROVENANCE_LABEL: (
                        provenance_sha256
                    )
                }
            }
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
    manifest = json.dumps(
        {"schemaVersion": 2, "config": {"digest": config_digest}},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    manifest_digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
    evidence = azure_contract.validate_oci_image_artifacts(
        manifest,
        config,
        expected_manifest_digest=manifest_digest,
        expected_provenance_sha256=provenance_sha256,
    )
    assert evidence["provenance_label"]["value"] == provenance_sha256
    assert evidence["manifest_sha256"] == manifest_digest.removeprefix(
        "sha256:"
    )
    assert evidence["config_sha256"] == config_digest.removeprefix("sha256:")
    evidence_sha256 = azure_contract.oci_verification_evidence_sha256(evidence)
    assert azure_contract.validate_oci_verification_evidence(
        evidence,
        expected_image_digest=manifest_digest,
        expected_provenance_sha256=provenance_sha256,
        expected_sha256=evidence_sha256,
    ) == evidence
    forged = config.replace(
        provenance_sha256.encode(), ("9" * 64).encode()
    )
    with pytest.raises(
        azure_contract.AzureContractError, match="config digest"
    ):
        azure_contract.validate_oci_image_artifacts(
            manifest,
            forged,
            expected_manifest_digest=manifest_digest,
            expected_provenance_sha256=provenance_sha256,
        )
    forged_config_digest = "sha256:" + hashlib.sha256(forged).hexdigest()
    forged_manifest = json.dumps(
        {
            "schemaVersion": 2,
            "config": {"digest": forged_config_digest},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    with pytest.raises(
        azure_contract.AzureContractError, match="provenance label"
    ):
        azure_contract.validate_oci_image_artifacts(
            forged_manifest,
            forged,
            expected_manifest_digest=(
                "sha256:" + hashlib.sha256(forged_manifest).hexdigest()
            ),
            expected_provenance_sha256=provenance_sha256,
        )
    missing = json.dumps(
        {"config": {"Labels": {}}},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    missing_config_digest = "sha256:" + hashlib.sha256(missing).hexdigest()
    missing_manifest = json.dumps(
        {
            "schemaVersion": 2,
            "config": {"digest": missing_config_digest},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    with pytest.raises(
        azure_contract.AzureContractError, match="provenance label"
    ):
        azure_contract.validate_oci_image_artifacts(
            missing_manifest,
            missing,
            expected_manifest_digest=(
                "sha256:" + hashlib.sha256(missing_manifest).hexdigest()
            ),
            expected_provenance_sha256=provenance_sha256,
        )
    dockerfile = (ROOT / "Dockerfile.parser-v2-eval").read_text(
        encoding="utf-8"
    )
    assert "ARG BUILD_PROVENANCE_SHA256" in dockerfile
    assert (
        'org.opencontainers.image.build-provenance-sha256="'
        '${BUILD_PROVENANCE_SHA256}"'
    ) in dockerfile


def test_missing_oci_evidence_fails_crash_finalization_closed():
    _, provenance_sha256 = _build_provenance()
    with pytest.raises(
        azure_contract.AzureContractError, match="evidence fields"
    ):
        azure_contract.validate_oci_verification_evidence(
            {},
            expected_image_digest=IMAGE_DIGEST,
            expected_provenance_sha256=provenance_sha256,
        )
    with pytest.raises(
        azure_contract.AzureContractError, match="omits OCI"
    ):
        azure_contract.validate_image_binding_oci_evidence(
            {"image_digest": IMAGE_DIGEST},
            expected_image_digest=IMAGE_DIGEST,
            expected_provenance_sha256=provenance_sha256,
            expected_evidence_sha256="a" * 64,
        )


def _private_topology_records():
    destination = _azure_destination()
    storage = destination["storage"]
    network = destination["network"]
    apps = destination["container_apps"]
    nic_id = (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/"
        "providers/Microsoft.Network/networkInterfaces/nic-synthetic-pe"
    )
    storage_record = {
        "id": storage["resource_id"],
        "name": storage["account_name"],
        "properties": {
            "publicNetworkAccess": "Disabled",
            "allowSharedKeyAccess": False,
            "allowBlobPublicAccess": False,
            "networkAcls": {"defaultAction": "Deny"},
        },
    }
    storage_container_record = {
        "id": (
            f"{storage['resource_id']}/blobServices/default/containers/"
            f"{storage['container']}"
        ),
        "name": storage["container"],
        "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
        "properties": {"publicAccess": None},
    }
    private_link_resources = [
        {
            "id": (
                f"{storage['resource_id']}/privateLinkResources/"
                f"{network['private_link_subresource']}"
            ),
            "name": network["private_link_subresource"],
            "type": "Microsoft.Storage/storageAccounts/privateLinkResources",
            "properties": {
                "groupId": network["private_link_group_id"],
                "requiredMembers": [network["private_link_subresource"]],
                "requiredZoneNames": [network["private_dns_zone_name"]],
            },
        }
    ]
    environment = {
        "id": apps["environment_resource_id"],
        "properties": {
            "vnetConfiguration": {
                "infrastructureSubnetId": network[
                    "infrastructure_subnet_resource_id"
                ]
            }
        },
    }
    endpoint = {
        "id": network["private_endpoint_resource_id"],
        "name": network["private_endpoint_name"],
        "properties": {
            "subnet": {"id": network["private_endpoint_subnet_resource_id"]},
            "manualPrivateLinkServiceConnections": [],
            "privateLinkServiceConnections": [
                {
                    "name": network["private_link_connection_name"],
                    "properties": {
                        "privateLinkServiceId": storage["resource_id"],
                        "groupIds": ["blob"],
                        "privateLinkServiceConnectionState": {
                            "status": "Approved"
                        },
                    },
                }
            ],
            "networkInterfaces": [{"id": nic_id}],
            "customDnsConfigs": [
                {
                    "fqdn": (
                        f"{storage['account_name']}.blob.core.windows.net"
                    ),
                    "ipAddresses": ["10.0.2.4"],
                }
            ],
        },
    }
    connections = [
        {
            "id": network[
                "storage_private_endpoint_connection_resource_id"
            ],
            "name": network["storage_private_endpoint_connection_name"],
            "properties": {
                "privateEndpoint": {
                    "id": network["private_endpoint_resource_id"]
                },
                "privateLinkServiceConnectionState": {"status": "Approved"},
            }
        }
    ]
    groups = [
        {
            "id": (
                f"{network['private_endpoint_resource_id']}/"
                f"privateDnsZoneGroups/{network['private_dns_zone_group_name']}"
            ),
            "name": network["private_dns_zone_group_name"],
            "properties": {
                "privateDnsZoneConfigs": [
                    {
                        "properties": {
                            "privateDnsZoneId": network[
                                "private_dns_zone_resource_id"
                            ]
                        }
                    }
                ]
            },
        }
    ]
    links = [
        {
            "id": (
                f"{network['private_dns_zone_resource_id']}/"
                f"virtualNetworkLinks/{network['private_dns_vnet_link_name']}"
            ),
            "name": network["private_dns_vnet_link_name"],
            "properties": {
                "virtualNetwork": {"id": network["vnet_resource_id"]},
                "provisioningState": "Succeeded",
            },
        }
    ]
    dns = {
        "id": (
            f"{network['private_dns_zone_resource_id']}/A/"
            f"{storage['account_name']}"
        ),
        "name": f"{network['private_dns_zone_name']}/{storage['account_name']}",
        "properties": {"aRecords": [{"ipv4Address": "10.0.2.4"}]},
    }
    nics = [
        {
            "id": nic_id,
            "properties": {
                "ipConfigurations": [
                    {"properties": {"privateIPAddress": "10.0.2.4"}}
                ]
            },
        }
    ]
    return (
        destination,
        storage_record,
        storage_container_record,
        environment,
        endpoint,
        private_link_resources,
        connections,
        groups,
        links,
        dns,
        nics,
    )


def test_private_endpoint_topology_is_exact_and_dns_is_pe_nic_only():
    (
        destination,
        storage,
        storage_container,
        environment,
        endpoint,
        private_link_resources,
        connections,
        groups,
        links,
        dns,
        nics,
    ) = _private_topology_records()
    workload_profiles = [
        {
            "name": "Consumption",
            "properties": {"workloadProfileType": "Consumption"},
        }
    ]
    result = azure_contract.validate_private_endpoint_topology(
        destination,
        storage=storage,
        storage_container=storage_container,
        environment=environment,
        workload_profile_states=workload_profiles,
        private_endpoint=endpoint,
        storage_private_link_resources=private_link_resources,
        storage_connections=connections,
        dns_zone_groups=groups,
        dns_links=links,
        dns_record=dns,
        nics=nics,
        resolved_ips=["10.0.2.4"],
    )
    assert result["private_endpoint_ips"] == ["10.0.2.4"]
    assert result["private_link_group_id"] == "blob"
    assert result["private_link_subresource"] == "blob"
    assert result["private_link_required_zone_names"] == [
        "privatelink.blob.core.windows.net"
    ]
    assert result["workload_profile"] == {
        "name": "Consumption",
        "workload_profile_type": "Consumption",
    }
    assert result["storage_container_public_access"] is None
    assert result["storage_allow_blob_public_access"] is False
    arm_none_container = deepcopy(storage_container)
    arm_none_container["properties"]["publicAccess"] = "None"
    arm_none_result = azure_contract.validate_private_endpoint_topology(
        destination,
        storage=storage,
        storage_container=arm_none_container,
        environment=environment,
        workload_profile_states=workload_profiles,
        private_endpoint=endpoint,
        storage_private_link_resources=private_link_resources,
        storage_connections=connections,
        dns_zone_groups=groups,
        dns_links=links,
        dns_record=dns,
        nics=nics,
        resolved_ips=["10.0.2.4"],
    )
    assert arm_none_result["storage_container_public_access"] is None
    empty_custom_dns = deepcopy(endpoint)
    empty_custom_dns["properties"]["customDnsConfigs"] = []
    empty_custom_dns_result = azure_contract.validate_private_endpoint_topology(
        destination,
        storage=storage,
        storage_container=storage_container,
        environment=environment,
        workload_profile_states=workload_profiles,
        private_endpoint=empty_custom_dns,
        storage_private_link_resources=private_link_resources,
        storage_connections=connections,
        dns_zone_groups=groups,
        dns_links=links,
        dns_record=dns,
        nics=nics,
        resolved_ips=["10.0.2.4"],
    )
    assert empty_custom_dns_result["private_endpoint_ips"] == ["10.0.2.4"]
    for public_access in ("Blob", "Container"):
        public_container = deepcopy(storage_container)
        public_container["properties"]["publicAccess"] = public_access
        with pytest.raises(azure_contract.AzureContractError, match="publicly"):
            azure_contract.validate_private_endpoint_topology(
                destination,
                storage=storage,
                storage_container=public_container,
                environment=environment,
                workload_profile_states=workload_profiles,
                private_endpoint=endpoint,
                storage_private_link_resources=private_link_resources,
                storage_connections=connections,
                dns_zone_groups=groups,
                dns_links=links,
                dns_record=dns,
                nics=nics,
                resolved_ips=["10.0.2.4"],
            )
    public_storage = deepcopy(storage)
    public_storage["properties"]["allowBlobPublicAccess"] = True
    with pytest.raises(azure_contract.AzureContractError, match="posture"):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=public_storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=endpoint,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    missing_container = deepcopy(storage_container)
    missing_container["id"] += "-other"
    with pytest.raises(azure_contract.AzureContractError, match="missing"):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=missing_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=endpoint,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    assert "groupIds" not in connections[0]["properties"]
    forged = deepcopy(endpoint)
    forged["properties"]["privateLinkServiceConnections"][0]["properties"][
        "groupIds"
    ] = ["file"]
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=forged,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=endpoint,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4", "20.1.1.1"],
        )
    missing_endpoint_group = deepcopy(endpoint)
    del missing_endpoint_group["properties"]["privateLinkServiceConnections"][0][
        "properties"
    ]["groupIds"]
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=missing_endpoint_group,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    missing_storage_group = deepcopy(private_link_resources)
    del missing_storage_group[0]["properties"]["groupId"]
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=workload_profiles,
            private_endpoint=endpoint,
            storage_private_link_resources=missing_storage_group,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    missing_required_zone = deepcopy(private_link_resources)
    del missing_required_zone[0]["properties"]["requiredZoneNames"]
    with pytest.raises(azure_contract.AzureContractError):
        azure_contract.validate_private_endpoint_topology(
        destination,
        storage=storage,
        storage_container=storage_container,
        environment=environment,
        workload_profile_states=workload_profiles,
        private_endpoint=empty_custom_dns,
        storage_private_link_resources=missing_required_zone,
        storage_connections=connections,
        dns_zone_groups=groups,
        dns_links=links,
        dns_record=dns,
        nics=nics,
        resolved_ips=["10.0.2.4"],
        )
    missing_profile_type = deepcopy(workload_profiles)
    del missing_profile_type[0]["properties"]["workloadProfileType"]
    with pytest.raises(
        azure_contract.AzureContractError,
        match="explicitly Consumption",
    ):
        azure_contract.validate_private_endpoint_topology(
            destination,
            storage=storage,
            storage_container=storage_container,
            environment=environment,
            workload_profile_states=missing_profile_type,
            private_endpoint=endpoint,
            storage_private_link_resources=private_link_resources,
            storage_connections=connections,
            dns_zone_groups=groups,
            dns_links=links,
            dns_record=dns,
            nics=nics,
            resolved_ips=["10.0.2.4"],
        )
    launcher = (
        ROOT
        / "infra"
        / "azure"
        / "scripts"
        / "10_run_parser_v2_locked_eval.sh"
    ).read_text(encoding="utf-8")
    assert "--workload-profile-states" in launcher
    assert "--storage-container" in launcher
    assert "/blobServices/default/containers/${BLOB_CONTAINER}" in launcher
    assert '.get("workloadProfileType", profile_name)' not in launcher


def test_blob_listing_uses_explicit_continuation_tokens_and_rejects_repeats():
    class Pager:
        def __init__(self, page, token):
            self.page = page
            self.continuation_token = token
            self.used = False

        def __iter__(self):
            return self

        def __next__(self):
            if self.used:
                raise StopIteration
            self.used = True
            return self.page

    class Listing:
        def __init__(self):
            self.tokens = []

        def by_page(self, continuation_token=None):
            self.tokens.append(continuation_token)
            if continuation_token is None:
                return Pager(
                    [SimpleNamespace(name=f"{PARENT}/state/a.json")],
                    "next-token",
                )
            assert continuation_token == "next-token"
            return Pager(
                [SimpleNamespace(name=f"{PARENT}/state/b.json")],
                None,
            )

    listing = Listing()
    service = SimpleNamespace(
        get_container_client=lambda _container: SimpleNamespace(
            list_blobs=lambda **_kwargs: listing
        )
    )
    assert core.list_exact_prefix(
        service, "synthetic-container", f"{PARENT}/state"
    ) == {
        f"{PARENT}/state/a.json",
        f"{PARENT}/state/b.json",
    }
    assert listing.tokens == [None, "next-token"]
    unpaged = SimpleNamespace(
        get_container_client=lambda _container: SimpleNamespace(
            list_blobs=lambda **_kwargs: []
        )
    )
    with pytest.raises(
        core.LockedEvaluationError, match="explicit paging"
    ):
        core.list_exact_prefix(
            unpaged, "synthetic-container", f"{PARENT}/state"
        )

    class RepeatedTokenListing:
        def by_page(self, continuation_token=None):
            return Pager([], "repeated")

    repeated = SimpleNamespace(
        get_container_client=lambda _container: SimpleNamespace(
            list_blobs=lambda **_kwargs: RepeatedTokenListing()
        )
    )
    with pytest.raises(
        core.LockedEvaluationError, match="continuation token is invalid"
    ):
        core.list_exact_prefix(
            repeated, "synthetic-container", f"{PARENT}/state"
        )


@pytest.mark.parametrize(
    "invalid_member",
    (
        f"{PARENT}/state",
        f"{PARENT}/state-sibling/forged.json",
        f"{PARENT}/state//forged.json",
        f"{PARENT}/state/../forged.json",
        f"{PARENT}/state/",
    ),
)
def test_blob_listing_rejects_paged_out_of_prefix_and_ambiguous_members(
    invalid_member,
):
    class Pager:
        def __init__(self, page, token):
            self.page = page
            self.continuation_token = token

        def __iter__(self):
            yield self.page

    class Listing:
        def by_page(self, continuation_token=None):
            if continuation_token is None:
                return Pager(
                    [SimpleNamespace(name=f"{PARENT}/state/valid.json")],
                    "page-2",
                )
            assert continuation_token == "page-2"
            return Pager([SimpleNamespace(name=invalid_member)], None)

    service = SimpleNamespace(
        get_container_client=lambda _container: SimpleNamespace(
            list_blobs=lambda **_kwargs: Listing()
        )
    )
    with pytest.raises(core.LockedEvaluationError):
        core.list_exact_prefix(
            service, "synthetic-container", f"{PARENT}/state"
        )


def test_shell_heredocs_are_quoted_and_lf_with_adversarial_values_rejected():
    paths = (
        ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v2_eval.sh",
        ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v2_locked_eval.sh",
    )
    for path in paths:
        data = path.read_bytes()
        assert b"\r" not in data
        for line in data.decode("utf-8").splitlines():
            if "<<" in line and "PY" in line:
                assert "<<'PY'" in line or '<<"PY"' in line
    forged = _azure_destination()
    forged["container_apps"]["job_name"] = 'job";$(touch injected)\nnext'
    with pytest.raises(core.LockedEvaluationError):
        core.validate_runtime_azure_destination(forged)
    assert "source_binding" not in inspect.signature(
        bootstrap.run_bootstrap
    ).parameters
    assert {
        "runtime_config_bytes",
        "implementation_manifest_bytes",
        "image_binding_bytes",
    }.issubset(inspect.signature(bootstrap.run_bootstrap).parameters)
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for relative in (
        ".gitattributes",
        "infra/azure/README.md",
        "infra/azure/scripts/09_build_parser_v2_eval.sh",
        "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
        "infra/azure/scripts/phase05_claim_election.py",
        "scripts/bootstrap_parser_v2_locked_evaluation.py",
        "scripts/parser_v2_azure_contract.py",
        "scripts/parser_v2_process_worker.py",
        "scripts/stage_p_entrypoint.sh",
        "scripts/stage_p_adopt_entrypoint.sh",
        "scripts/stage_e_entrypoint.sh",
        "tests/fixtures/parser_v2_adversarial_bash_env.sh",
    ):
        assert f"{relative} text eol=lf" in attributes


def _legacy_numeric_oracle(output: str) -> dict[str, Any]:
    text = re.sub(
        r"<think>.*?</think>",
        "",
        output,
        flags=re.DOTALL | re.IGNORECASE,
    )
    explicit = re.findall(
        r"(?:final\s+answer|answer|the\s+answer\s+is)"
        r"\s*[:：]?\s*(-?\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not matches:
        return {
            "parsed_answer": None,
            "parse_valid": False,
            "parse_error_type": "no_numeric_found",
            "parse_ambiguous": False,
            "parse_strategy": "no_numeric_found",
            "candidate_answers": [],
            "answer_format_warning": None,
        }
    reasoning_like = bool(
        re.search(
            r"step[-\s]*by[-\s]*step|explanation|follow these steps|"
            r"to solve|first,|then,|therefore|because|\bstep\s*\d+\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    parsed = explicit[-1] if explicit else matches[-1]
    strategy = (
        "explicit_answer"
        if explicit
        else ("single_number" if len(matches) == 1 else "last_number")
    )
    ambiguous = len(matches) > 1 and (reasoning_like or len(text) > 80)
    warning = None
    if ambiguous:
        warning = f"multiple_numeric_candidates:{len(matches)}"
    elif len(matches) > 1:
        warning = f"multiple_numbers_short_output:{len(matches)}"
    return {
        "parsed_answer": parsed,
        "parse_valid": True,
        "parse_error_type": None,
        "parse_ambiguous": ambiguous,
        "parse_strategy": strategy,
        "candidate_answers": matches,
        "answer_format_warning": warning,
    }


def test_legacy_parser_is_exact_numeric_only_and_differential():
    loaded = runner._load_stage_p_parsers()
    assert len(loaded) == 2
    _, parse_numeric = loaded
    source = (
        ROOT / "src" / "jspace_observation" / "eval_parsing.py"
    ).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    assert hashlib.sha256(source).hexdigest() == (
        core.FROZEN_LEGACY_PARSER_SOURCE_SHA256
    )
    assert runner._git_blob_oid(source) == core.FROZEN_LEGACY_PARSER_GIT_BLOB_OID
    assert core.FROZEN_LEGACY_PARSER_COMMIT == core.FROZEN_STARTING_COMMIT
    assert parse_numeric.__module__ not in sys.modules
    assert set(parse_numeric.__globals__) == {
        "__builtins__",
        "__name__",
        "ParseResult",
        "parse_numeric_answer",
        "re",
    }
    assert set(parse_numeric.__builtins__) == {"bool", "len"}
    assert "_jspace_stage_p_frozen_legacy" not in sys.modules
    assert not any(
        isinstance(value, ModuleType)
        and any(
            hasattr(value, name)
            for name in ("create_eval_record", "evaluate_answer", "parse_and_score")
        )
        for value in parse_numeric.__globals__.values()
    )
    corpus = [
        "",
        "no numeric answer",
        "12",
        "1 2",
        "first, 1 then, 2",
        "<think>1 and 2</think> final answer: -3.5",
        "the answer is 7; confidence 99",
        "x " * 50 + "1 and 2",
        "Answer：004.50",
    ]
    for output_text in corpus:
        assert dataclasses.asdict(parse_numeric(output_text)) == (
            _legacy_numeric_oracle(output_text)
        )


def test_frozen_files_remain_at_registered_public_hashes():
    development = (
        ROOT / "evaluator_sets" / "parser_v2_v1" / "development_cases.jsonl"
    ).read_bytes()
    assert hashlib.sha256(development).hexdigest() == (
        "bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27"
    )
    source = (
        ROOT / "src" / "jspace_observation" / "eval_parsing_v2.py"
    ).read_bytes()
    package_name = "_test_frozen_parser_hash"
    package = ModuleType(package_name)
    package.__path__ = [  # type: ignore[attr-defined]
        str(ROOT / "src" / "jspace_observation")
    ]
    sys.modules[package_name] = package
    try:
        _load_module(
            f"{package_name}.evaluator_validation",
            ROOT / "src" / "jspace_observation" / "evaluator_validation.py",
        )
        parser_module = _load_module(
            f"{package_name}.eval_parsing_v2",
            ROOT / "src" / "jspace_observation" / "eval_parsing_v2.py",
        )
        assert parser_module.compute_parser_source_sha256(source) == (
            core.FROZEN_PARSER_SOURCE_SHA256
        )
        assert parser_module.PARSER_VERSION == core.FROZEN_PARSER_VERSION
    finally:
        for name in list(sys.modules):
            if name == package_name or name.startswith(f"{package_name}."):
                sys.modules.pop(name, None)


def test_stage_p_parser_v2_facade_is_process_only_and_matches_public_fixtures():
    parser_modules_before = {
        name
        for name in sys.modules
        if "eval_parsing_v2" in name or "evaluator_validation" in name
    }
    parse_v2, _ = runner._load_stage_p_parsers()
    assert callable(parse_v2)
    assert dir(parse_v2) == []
    assert not hasattr(parse_v2, "__globals__")
    assert not hasattr(parse_v2, "__dict__")
    with pytest.raises(AttributeError):
        parse_v2.__call__
    assert type(parse_v2).__slots__ == ()
    assert not any(
        hasattr(parse_v2, name)
        for name in (
            "compare_parsed_answer_to_reference",
            "reference_answer",
            "correctness",
            "module",
            "loader",
            "worker_path",
        )
    )
    assert not any(
        isinstance(value, ModuleType)
        for name in dir(parse_v2)
        for value in (
            getattr(parse_v2, name, None),
        )
    )
    assert parser_modules_before == {
        name
        for name in sys.modules
        if "eval_parsing_v2" in name or "evaluator_validation" in name
    }

    package_name = "_test_public_parser_oracle"
    package = ModuleType(package_name)
    package.__path__ = [  # type: ignore[attr-defined]
        str(ROOT / "src" / "jspace_observation")
    ]
    sys.modules[package_name] = package
    try:
        _load_module(
            f"{package_name}.evaluator_validation",
            ROOT / "src" / "jspace_observation" / "evaluator_validation.py",
        )
        oracle_module = _load_module(
            f"{package_name}.eval_parsing_v2",
            ROOT / "src" / "jspace_observation" / "eval_parsing_v2.py",
        )
        fixtures = [
            json.loads(line)
            for line in (
                ROOT
                / "evaluator_sets"
                / "parser_v2_v1"
                / "development_cases.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        for fixture in fixtures:
            request = {
                "schema_version": core.PARSER_REQUEST_SCHEMA_VERSION,
                "answer_type": "numeric",
                "output_text": fixture["output_text"],
            }
            assert parse_v2(request) == oracle_module.parse_v2(request)
    finally:
        for name in list(sys.modules):
            if name == package_name or name.startswith(f"{package_name}."):
                sys.modules.pop(name, None)


def test_stage_p_parser_v2_facade_rejects_nonexact_or_noisy_worker(
    monkeypatch,
):
    request = {
        "schema_version": core.PARSER_REQUEST_SCHEMA_VERSION,
        "answer_type": "numeric",
        "output_text": "answer: 1",
    }
    for stdout, stderr, message in (
        (b"{}\n", b"", "noncanonical"),
        (b"{}\n", b"untrusted worker detail", "rejected request"),
    ):
        monkeypatch.setattr(
            runner.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(
                returncode=0,
                stdout=stdout,
                stderr=stderr,
            ),
        )
        with pytest.raises(RuntimeError, match=message) as caught:
            runner._invoke_parser_v2_worker(request)
        assert "untrusted worker detail" not in str(caught.value)

    forged = dict(request)
    forged["schema_version"] = "wrong"
    with pytest.raises(RuntimeError, match="request rejected"):
        runner._invoke_parser_v2_worker(forged)

    parse_v2, _ = runner._load_stage_p_parsers()
    secret = "Y29ycmVjdG5lc3M6dHJ1ZQ=="
    with pytest.raises(RuntimeError) as caught:
        parse_v2(
            {
                "schema_version": core.PARSER_REQUEST_SCHEMA_VERSION,
                "answer_type": "numeric",
                "output_text": "Answer: 1",
                "reference_answer": secret,
            }
        )
    assert secret not in str(caught.value)


def _retry_attempt_member(
    blob_name: str,
    marker: str,
    *,
    size: int = 1,
) -> dict[str, Any]:
    return {
        "blob_name": blob_name,
        "size": size,
        "sha256": marker * 64,
        "etag": f'"retry-{marker}"',
    }


def _abandoned_retry_record(
    previous: Mapping[str, Any],
    *,
    stage: str,
    retry_kind: str,
    prior_execution_id: str,
    current_execution_id: str,
    current_actor: str = "synthetic-actor",
) -> dict[str, Any]:
    output_leaf = "predictions" if stage == "P" else "scores"
    prior_prefixes = core.evaluation_attempt_prefixes(
        PARENT,
        AUTHORIZATION,
        stage,
        "none",
        prior_execution_id,
    )
    return core.build_abandoned_attempt_record(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        prior_stage=stage,
        prior_retry_kind="none",
        prior_execution_id=prior_execution_id,
        prior_actor="synthetic-prior-actor",
        abandoned_members=[
            _retry_attempt_member(
                f"{prior_prefixes['visibility']}/partial_visibility.json",
                "2",
            ),
            _retry_attempt_member(
                f"{prior_prefixes[output_leaf]}/partial_output.json",
                "1",
            ),
        ],
        current_retry_kind=retry_kind,
        current_execution_id=current_execution_id,
        current_actor=current_actor,
        prior_state_receipt_sha256=core.state_receipt_sha256(previous),
        created_utc=TIMESTAMP,
    )


def test_retry_attempt_protocol_prefixes_are_canonical_unique_and_nonsecret():
    assert {
        "ABANDONED_ATTEMPT_SCHEMA_VERSION",
        "derive_attempt_prefix",
        "validate_exact_attempt_prefix",
        "build_abandoned_attempt_record",
        "validate_abandoned_attempt_record",
        "abandoned_attempt_sha256",
        "expected_authorization_attempt_membership",
        "build_provenance_bound_retry_state_receipt",
    }.issubset(core.__all__)
    roots = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    raw_execution_id = "../../raw/execution-id"
    primary = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "predictions",
        "P",
        "none",
        raw_execution_id,
    )
    retry = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "predictions",
        "P",
        "infrastructure_pre_input",
        raw_execution_id,
    )
    retry_again = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "predictions",
        "P",
        "infrastructure_pre_input",
        raw_execution_id,
    )
    different_retry = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "predictions",
        "P",
        "infrastructure_pre_input",
        "different-execution",
    )
    retry_visibility = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "visibility",
        "P",
        "infrastructure_pre_input",
        raw_execution_id,
    )

    assert primary == roots["predictions"]
    assert retry == retry_again
    assert retry != different_retry
    assert raw_execution_id not in retry
    assert retry.split("/")[-1] == retry_visibility.split("/")[-1]
    assert re.fullmatch(r"[0-9a-f]{64}", retry.split("/")[-1])
    assert (
        core.derive_attempt_prefix(
            PARENT,
            AUTHORIZATION,
            "state",
            "P",
            "infrastructure_pre_input",
            raw_execution_id,
        )
        == roots["state"]
    )
    assert set(
        core.evaluation_attempt_prefixes(
            PARENT,
            AUTHORIZATION,
            "E",
            "verification_only",
            "verification-execution",
        )
    ) == {"visibility", "state"}


def test_retry_attempt_protocol_rejects_wrong_combinations_paths_and_types():
    retry = core.derive_attempt_prefix(
        PARENT,
        AUTHORIZATION,
        "scores",
        "E",
        "scorer_infrastructure",
        "scorer-execution",
    )
    assert (
        core.validate_exact_attempt_prefix(
            retry,
            PARENT,
            AUTHORIZATION,
            "scores",
            "E",
            "scorer_infrastructure",
            "scorer-execution",
        )
        == retry
    )
    for leaf in ("predictions", "scores"):
        with pytest.raises(core.LockedEvaluationError):
            core.derive_attempt_prefix(
                PARENT,
                AUTHORIZATION,
                leaf,
                "E",
                "verification_only",
                "verification-execution",
            )
    with pytest.raises(core.LockedEvaluationError):
        core.derive_attempt_prefix(
            PARENT,
            AUTHORIZATION,
            "predictions",
            "P",
            "scorer_infrastructure",
            "wrong-stage",
        )
    for forged in (
        core.evaluation_prefixes(PARENT, AUTHORIZATION)["scores"],
        retry.rsplit("/", 1)[0],
        f"{retry}/../raw-execution",
        f"{retry[:-1]}0",
    ):
        with pytest.raises(core.LockedEvaluationError):
            core.validate_exact_attempt_prefix(
                forged,
                PARENT,
                AUTHORIZATION,
                "scores",
                "E",
                "scorer_infrastructure",
                "scorer-execution",
            )
    for stage, retry_kind, execution_id in (
        (True, "none", "execution"),
        ("P", 1, "execution"),
        ("P", "none", False),
    ):
        with pytest.raises(core.LockedEvaluationError):
            core.derive_attempt_prefix(
                PARENT,
                AUTHORIZATION,
                "predictions",
                stage,
                retry_kind,
                execution_id,
            )


def test_retry_attempt_protocol_abandoned_record_is_exact_and_tamper_evident():
    previous = _state_chain_until("UNSEAL_AUTHORIZED")[-1]
    record = _abandoned_retry_record(
        previous,
        stage="P",
        retry_kind="infrastructure_pre_input",
        prior_execution_id="primary-stage-p",
        current_execution_id="retry-stage-p",
    )
    assert record["abandoned_members"] == sorted(
        record["abandoned_members"], key=lambda item: item["blob_name"]
    )
    assert record["abandoned_membership_sha256"] == (
        core.attempt_membership_sha256(record["abandoned_members"])
    )
    assert core.validate_abandoned_attempt_record(record) == record
    assert core.abandoned_attempt_sha256(record) == core.sha256_bytes(
        core.canonical_json_bytes(record)
    )
    assert core.abandoned_attempt_blob_name(record).startswith(
        f"{record['current_visibility_prefix']}/"
    )
    assert "retry-stage-p" not in record["current_output_prefix"]

    tampered_records = []
    reordered = deepcopy(record)
    reordered["abandoned_members"] = list(
        reversed(reordered["abandoned_members"])
    )
    tampered_records.append(reordered)
    extra = deepcopy(record)
    extra["extra"] = "forbidden"
    tampered_records.append(extra)
    missing = deepcopy(record)
    missing.pop("prior_actor")
    tampered_records.append(missing)
    bool_size = deepcopy(record)
    bool_size["abandoned_members"][0]["size"] = True
    tampered_records.append(bool_size)
    member_hash = deepcopy(record)
    member_hash["abandoned_members"][0]["sha256"] = "8" * 64
    tampered_records.append(member_hash)
    wrong_hash = deepcopy(record)
    wrong_hash["abandoned_membership_sha256"] = "9" * 64
    tampered_records.append(wrong_hash)
    wrong_path = deepcopy(record)
    wrong_path["current_output_prefix"] = core.evaluation_prefixes(
        PARENT, AUTHORIZATION
    )["predictions"]
    tampered_records.append(wrong_path)
    state_member = deepcopy(record)
    state_member["abandoned_members"][0]["blob_name"] = (
        f"{core.evaluation_prefixes(PARENT, AUTHORIZATION)['state']}/"
        "forbidden.json"
    )
    tampered_records.append(state_member)
    sibling_member = deepcopy(record)
    sibling_member["abandoned_members"][0]["blob_name"] = (
        f"{core.evaluation_prefixes(PARENT, AUTHORIZATION)['scores']}/"
        "sibling.json"
    )
    tampered_records.append(sibling_member)
    for tampered in tampered_records:
        with pytest.raises(core.LockedEvaluationError):
            core.validate_abandoned_attempt_record(tampered)

    with pytest.raises(core.LockedEvaluationError):
        core.build_abandoned_attempt_record(
            parent_prefix=PARENT,
            authorization_id=AUTHORIZATION,
            prior_stage="P",
            prior_retry_kind="none",
            prior_execution_id="same-execution",
            prior_actor="actor",
            abandoned_members=[],
            current_retry_kind="infrastructure_pre_input",
            current_execution_id="same-execution",
            current_actor="actor",
            prior_state_receipt_sha256="1" * 64,
            created_utc=TIMESTAMP,
        )


@pytest.mark.parametrize(
    ("stage", "retry_kind", "target_state"),
    (
        ("P", "infrastructure_pre_input", "UNSEAL_AUTHORIZED"),
        ("E", "scorer_infrastructure", "PREDICTIONS_VERIFIED"),
    ),
)
def test_retry_attempt_protocol_receipt_links_abandoned_attempt_exactly(
    stage,
    retry_kind,
    target_state,
):
    chain = _state_chain_until(target_state)
    previous = chain[-1]
    execution_id = f"bound-{retry_kind}"
    record = _abandoned_retry_record(
        previous,
        stage=stage,
        retry_kind=retry_kind,
        prior_execution_id=f"primary-{stage.casefold()}",
        current_execution_id=execution_id,
    )
    receipt = core.build_provenance_bound_retry_state_receipt(
        previous,
        retry_kind=retry_kind,
        timestamp_utc="2026-07-20T05:55:00Z",
        execution_id=execution_id,
        actor="synthetic-actor",
        history=chain,
        authorization_lock=_authorization_lock(chain),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        abandoned_attempt_record=record,
        abandoned_attempt_blob_name=core.abandoned_attempt_blob_name(record),
        abandoned_attempt_record_sha256=core.abandoned_attempt_sha256(record),
    )
    assert receipt["visibility"] == core.abandoned_attempt_retry_visibility(record)
    core.validate_retry_state_receipt_provenance(
        receipt,
        previous=previous,
        abandoned_attempt_record=record,
    )
    with pytest.raises(core.LockedEvaluationError):
        core.abandoned_attempt_retry_visibility(
            record,
            expected_record_sha256="8" * 64,
        )

    tampered = deepcopy(receipt)
    tampered["visibility"] = sorted(
        [*tampered["visibility"], "unexpected_linkage=forbidden"]
    )
    with pytest.raises(core.LockedEvaluationError, match="visibility"):
        core.validate_retry_state_receipt_provenance(
            tampered,
            previous=previous,
            abandoned_attempt_record=record,
        )
    with pytest.raises(core.LockedEvaluationError):
        core.build_retry_state_receipt(
            previous,
            retry_kind=retry_kind,
            timestamp_utc="2026-07-20T05:55:00Z",
            execution_id=execution_id,
            actor="synthetic-actor",
            visibility=["old-unbound-marker"],
            history=chain,
            authorization_lock=_authorization_lock(chain),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            abandoned_attempt_record=record,
        )
    with pytest.raises(core.LockedEvaluationError):
        core.build_provenance_bound_retry_state_receipt(
            previous,
            retry_kind=retry_kind,
            timestamp_utc="2026-07-20T05:55:00Z",
            execution_id=execution_id,
            actor="synthetic-actor",
            history=chain,
            authorization_lock=_authorization_lock(chain),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        )


def test_retry_attempt_protocol_verification_binds_only_prior_artifacts():
    chain = _state_chain_until("LABELS_READ")
    previous = chain[-1]
    hashes = {
        "prior_score_manifest_sha256": "3" * 64,
        "prior_labels_open_transaction_sha256": "4" * 64,
        "prior_scoring_attestation_sha256": "5" * 64,
    }
    receipt = core.build_provenance_bound_retry_state_receipt(
        previous,
        retry_kind="verification_only",
        timestamp_utc="2026-07-20T05:56:00Z",
        execution_id="verification-bound",
        actor="synthetic-actor",
        history=chain,
        authorization_lock=_authorization_lock(chain),
        implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
        **hashes,
    )
    expected = core.verification_retry_visibility(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        execution_id="verification-bound",
        **hashes,
    )
    assert receipt["visibility"] == expected
    assert any(
        item.startswith("current_visibility_attempt_prefix=")
        for item in expected
    )
    assert not any("predictions" in item or "scores" in item for item in expected)
    core.validate_retry_state_receipt_provenance(
        receipt,
        previous=previous,
        **hashes,
    )

    tampered = deepcopy(receipt)
    tampered["visibility"] = [
        item.replace("3" * 64, "6" * 64)
        for item in tampered["visibility"]
    ]
    with pytest.raises(core.LockedEvaluationError, match="visibility"):
        core.validate_retry_state_receipt_provenance(
            tampered,
            previous=previous,
            **hashes,
        )
    missing_hash = dict(hashes)
    missing_hash.pop("prior_scoring_attestation_sha256")
    with pytest.raises(core.LockedEvaluationError):
        core.build_provenance_bound_retry_state_receipt(
            previous,
            retry_kind="verification_only",
            timestamp_utc="2026-07-20T05:56:00Z",
            execution_id="verification-bound",
            actor="synthetic-actor",
            history=chain,
            authorization_lock=_authorization_lock(chain),
            implementation_manifest_bytes=IMPLEMENTATION_MANIFEST_BYTES,
            **missing_hash,
        )


def test_retry_attempt_protocol_membership_uses_only_explicit_descriptors():
    chain = _state_chain_until("UNSEAL_AUTHORIZED")
    previous = chain[-1]
    record = _abandoned_retry_record(
        previous,
        stage="P",
        retry_kind="infrastructure_pre_input",
        prior_execution_id="membership-primary",
        current_execution_id="membership-retry",
    )
    record_bytes = core.canonical_json_bytes(record)
    descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=PARENT,
        authorization_id=AUTHORIZATION,
        stage="P",
        retry_kind="infrastructure_pre_input",
        execution_id="membership-retry",
        members=[
            _retry_attempt_member(
                f"{record['current_output_prefix']}/retry_output.json",
                "6",
            ),
            {
                "blob_name": core.abandoned_attempt_blob_name(record),
                "size": len(record_bytes),
                "sha256": core.abandoned_attempt_sha256(record),
                "etag": '"retry-record"',
            },
        ],
    )
    roots = core.evaluation_prefixes(PARENT, AUTHORIZATION)
    primary_state_member = f"{roots['state']}/synthetic_state.json"
    primary = {
        "predictions": {
            member["blob_name"]
            for member in record["abandoned_members"]
            if member["blob_name"].startswith(f"{roots['predictions']}/")
        },
        "scores": set(),
        "state": {primary_state_member},
        "visibility": {
            member["blob_name"]
            for member in record["abandoned_members"]
            if member["blob_name"].startswith(f"{roots['visibility']}/")
        },
    }
    expected = core.expected_authorization_attempt_membership(
        PARENT,
        AUTHORIZATION,
        [record, descriptor],
        primary_membership=primary,
    )
    explicitly_named = {
        member["blob_name"] for member in record["abandoned_members"]
    } | {
        member["blob_name"] for member in descriptor["members"]
    } | {core.abandoned_attempt_blob_name(record), primary_state_member}
    assert set().union(*expected.values()) == explicitly_named
    assert expected["state"] == {primary_state_member}
    assert (
        f"{roots['predictions']}/attempts/arbitrary/extra.json"
        not in expected["predictions"]
    )
    assert core.evaluation_prefixes(PARENT, AUTHORIZATION) == roots

    nested_primary = deepcopy(primary)
    nested_primary["predictions"].add(
        f"{roots['predictions']}/attempts/arbitrary/extra.json"
    )
    with pytest.raises(core.LockedEvaluationError):
        core.expected_authorization_attempt_membership(
            PARENT,
            AUTHORIZATION,
            [record, descriptor],
            primary_membership=nested_primary,
        )
    reordered = deepcopy(descriptor)
    reordered["members"] = list(reversed(reordered["members"]))
    with pytest.raises(core.LockedEvaluationError):
        core.validate_attempt_membership_descriptor(reordered)
    with pytest.raises(core.LockedEvaluationError):
        core.expected_authorization_attempt_membership(
            PARENT,
            AUTHORIZATION,
            [{"schema_version": "unregistered"}],
        )
