"""Prospective invariants for the Phase 1.0D transport recovery."""

from __future__ import annotations

import ast
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
import shlex
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORITY = (
    REPO_ROOT
    / "docs"
    / "prompts"
    / "phase1_0d_review_only_transport_recovery_prompt.md"
)
AUTHORITY_SHA256 = (
    "dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b"
)
V1_ROLLUP = "436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd"
V2_ROLLUP = "ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a"


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = _load("recovery_v1_protected", "scripts/phase1_0d_protected_bytes.py")
v2 = _load("recovery_v2_protected", "scripts/phase1_0d_rv2_protected_bytes.py")
recovery = _load(
    "phase1_0d_transport_recovery",
    "scripts/phase1_0d_transport_recovery.py",
)
LAUNCHER = (
    REPO_ROOT
    / "infra"
    / "azure"
    / "scripts"
    / "24_run_phase1_0d_transport_recovery.sh"
)
SCHEMA = (
    REPO_ROOT / "docs" / "phase1_0d_transport_capacity_certificate.schema.json"
)
RUN_ID = "20260806T010203Z"
JOB_NAME = "job-p10d-rv2-tr-1234abcd"
LAUNCHER_COMMIT = "1" * 40
CERTIFICATE_SHA = "2" * 64
MANIFEST_SHA = "3" * 64
IDENTITY_ID = (
    "/subscriptions/redacted/resourceGroups/rg-jspace-observation-sea/"
    "providers/Microsoft.ManagedIdentity/userAssignedIdentities/"
    "id-jspace-p10d-review-sea"
)
ENVIRONMENT_ID = (
    "/subscriptions/redacted/resourceGroups/rg-jspace-observation-sea/"
    "providers/Microsoft.App/managedEnvironments/"
    "cae-jspace-observation-sea-vnet2"
)


def _rollups() -> dict[str, dict]:
    return {
        role: {
            "role": role,
            "row_count": 900,
            "ordering": "record_id ascending, identical to review_rows",
            "ordered_record_ids_sha256": "a" * 64,
            "ordered_request_body_sha256_rollup": (
                {"primary": "b", "secondary": "c", "third": "d"}[role] * 64
            ),
            "first_record_id": "record-0000",
            "last_record_id": "record-0899",
            "request_profile_sha256": recovery.PROFILE_SHA256[role],
            "all_request_hashes_are_sha256": True,
        }
        for role in recovery.ROLE_CONTRACTS
    }


def _projection(role: str, capacity: int, tpm: int, rpm: int, etag: str) -> dict:
    contract = recovery.ROLE_CONTRACTS[role]
    return {
        "account": contract["account"],
        "resource_group": contract["resource_group"],
        "deployment": contract["deployment"],
        "endpoint_host": contract["endpoint_host"],
        "location": contract["location"],
        "etag": etag,
        "sku": {"name": contract["sku_name"], "capacity": capacity},
        "properties": {
            "model": {
                "format": contract["model_format"],
                "name": contract["model_name"],
                "version": contract["model_version"],
            },
            "versionUpgradeOption": "OnceNewDefaultVersionAvailable",
            "provisioningState": "Succeeded",
            "currentCapacity": capacity,
            "rateLimits": [
                {"count": rpm, "key": "request", "renewalPeriod": 60},
                {"count": tpm, "key": "token", "renewalPeriod": 60},
            ],
            "dynamicThrottlingEnabled": None,
            "spilloverDeploymentName": None,
            "parentDeploymentName": None,
        },
        "normalized_rate_limits": {"rpm": rpm, "tpm": tpm},
    }


def _model_capacity(role: str, available: int = 10_000) -> dict:
    contract = recovery.ROLE_CONTRACTS[role]
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


def _passing_evidence() -> dict:
    capacities = {"primary": 1000, "secondary": 500, "third": 1000}
    evidence = {
        "observation": {
            "certificate_observed_at_utc": "2026-08-06T01:02:03Z",
            "control_plane_readback_at_utc": "2026-08-06T01:02:03Z",
            "monitor_window_end_utc": "2026-08-06T01:02:03Z",
            "private_state_readback_at_utc": "2026-08-06T01:02:03Z",
            "job_inventory_readback_at_utc": "2026-08-06T01:02:03Z",
        },
        "provider_calls": 0,
        "provider_calls_method": (
            "No provider client or inference command exists in the checker; "
            "recovery Job/execution inventory is empty."
        ),
        "request_body_rollups": _rollups(),
        "accounts": {
            name: {
                **copy.deepcopy(contract),
                "disable_local_auth": True,
            }
            for name, contract in recovery.ACCOUNT_CONTRACTS.items()
        },
        "identity_route": copy.deepcopy(recovery.IDENTITY_ROUTE_CONTRACT),
        "deployments": {},
        "quiet_window": {
            "duration_seconds": 900,
            "non_project_requests": 0,
            "complete_minute_elapsed": True,
            "query_succeeded": True,
            "deployment_dimension_verified": True,
            "per_role_request_counts": {
                role: 0 for role in recovery.ROLE_CONTRACTS
            },
        },
        "azure_monitor": {
            "api": "Microsoft.Insights/metrics",
            "interval": "PT1M",
            "window_duration_seconds": 3600,
            "roles": {
                role: {
                    "deployment": contract["deployment"],
                    "request_metric": "AzureOpenAIRequests",
                    "deployment_dimension_available": True,
                    "query_succeeded": True,
                    "request_count_60m": 0,
                    "http_429_count_60m": 0,
                    "processed_prompt_tokens_60m": 0,
                    "generated_completion_tokens_60m": 0,
                    "quiet_window_request_count": 0,
                }
                for role, contract in recovery.ROLE_CONTRACTS.items()
            },
        },
        "provider_capable_job_inventory": {
            "identity_client_id": recovery.IDENTITY_CLIENT_ID,
            "all_jobs_with_review_identity_included": True,
            "role_assignment_readback_complete": True,
            "recovery_job_count": 0,
            "recovery_execution_count": 0,
            "jobs": [
                {
                    "name": recovery.OLD_FORMAL_JOB_NAME,
                    "execution_count": 1,
                }
            ],
        },
        "blob_and_execution_state": {
            "source_object_count": 8,
            "source_manifest_sha256": recovery.SOURCE_MANIFEST_SHA256,
            "generation_execution_count": 1,
            "generation_execution": recovery.GENERATION_EXECUTION,
            "generation_execution_status": "Succeeded",
            "old_result_object_count": 0,
            "old_formal_lock_sha256": recovery.OLD_FORMAL_LOCK_SHA256,
            "old_terminal_archive_sha256": (
                recovery.OLD_TERMINAL_ARCHIVE_SHA256
            ),
            "old_formal_execution_count": 1,
            "old_formal_execution": recovery.OLD_FORMAL_EXECUTION,
            "old_formal_execution_status": "Failed",
            "recovery_lock_exists": False,
            "recovery_result_object_count": 0,
            "recovery_job_count": 0,
            "recovery_execution_count": 0,
        },
    }
    for role, contract in recovery.ROLE_CONTRACTS.items():
        projection = _projection(
            role,
            capacities[role],
            contract["minimum_tpm"],
            contract["minimum_rpm"],
            f'"etag-{role}"',
        )
        evidence["deployments"][role] = {
            "before": copy.deepcopy(projection),
            "after": copy.deepcopy(projection),
            "usage": {
                "name": contract["usage_name"],
                "localized_value": contract["usage_name"],
                "current_value": capacities[role],
                "limit": 10_000,
                "unallocated": 10_000 - capacities[role],
                "unit": "Count",
            },
            "model_capacity": _model_capacity(role),
            "mutation": None,
        }
    return evidence


def test_the_recovery_authority_is_frozen_byte_for_byte():
    assert hashlib.sha256(AUTHORITY.read_bytes()).hexdigest() == AUTHORITY_SHA256


def test_both_protected_records_remain_exact():
    v1_document = v1.load_baseline(REPO_ROOT / v1.BASELINE_FILENAME)
    v2_document = v2.load_baseline(REPO_ROOT / v2.BASELINE_FILENAME)
    assert v1_document["file_count"] == 152
    assert v1_document["rollup_sha256"] == V1_ROLLUP
    assert v2_document["file_count"] == 36
    assert v2_document["rollup_sha256"] == V2_ROLLUP
    assert v1.verify(REPO_ROOT, REPO_ROOT / v1.BASELINE_FILENAME) == []
    assert v2.verify(REPO_ROOT, REPO_ROOT / v2.BASELINE_FILENAME) == []


def test_recovery_records_use_new_ids_without_rewriting_old_records():
    decision = (REPO_ROOT / "docs" / "decision_log.md").read_text(encoding="utf-8")
    limitations = (REPO_ROOT / "paper" / "limitations_ledger.md").read_text(
        encoding="utf-8"
    )
    methods = (REPO_ROOT / "paper" / "methods_ledger.md").read_text(encoding="utf-8")
    assert decision.count("## D28 ") == 1
    assert limitations.count("## L-54 ") == 1
    assert methods.count("## M-18 ") == 1
    assert AUTHORITY_SHA256 in decision
    assert "unquantifiable prior-response resampling\nexposure" in limitations
    assert "provider_calls=0" in methods


def test_authorization_does_not_advance_cl05():
    matrix = (REPO_ROOT / "paper" / "claim_evidence_matrix.md").read_text(
        encoding="utf-8"
    )
    note = matrix[matrix.index("**2026-08-05 — one capacity-gated") :]
    assert AUTHORITY_SHA256 in note
    assert "CL-05 remains\n`preliminary`" in note
    assert "Authorization is not evidence" in note


def test_the_authority_forbids_pre_certificate_inference_and_a_second_recovery():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert "explicit provider_calls=0" in text
    assert "there is no second recovery execution" in text
    assert "Do not run:" in text
    for forbidden in (
        "provider qualification",
        "the 20-fixture smoke or any subset of it",
        "a one-row target probe",
        "a dry-run chat completion",
    ):
        assert forbidden in text


def test_all_authority_pinned_identities_are_full_and_exact():
    assert recovery.AUTHORITY_SHA256 == AUTHORITY_SHA256
    assert recovery.STARTING_COMMIT == "d145b1c79db8b6866fadaa8875c2374a813a7e31"
    assert recovery.STARTING_TREE == "b4329a4062415cf7cb3b058d3defe6da7c14f25c"
    assert recovery.V1_PROTECTED_FILE_COUNT == 152
    assert recovery.V2_PROTECTED_FILE_COUNT == 36
    assert recovery.V1_PROTECTED_ROLLUP == V1_ROLLUP
    assert recovery.V2_PROTECTED_ROLLUP == V2_ROLLUP
    assert recovery.GENERATION_JOB_NAME == "job-jspace-p10d-confirmation"
    assert (
        recovery.GENERATION_EXECUTION
        == "job-jspace-p10d-confirmation-pdlhmah"
    )
    assert recovery.OLD_FORMAL_JOB_NAME == "job-p10d-rv2-r-d4a84a59bc28a91f"
    assert (
        recovery.OLD_FORMAL_EXECUTION
        == "job-p10d-rv2-r-d4a84a59bc28a91f-tjzwlse"
    )
    for digest in (
        recovery.V2_PROTECTED_MANIFEST_SHA256,
        recovery.SOURCE_MANIFEST_SHA256,
        recovery.QUALIFICATION_RECEIPT_SHA256,
        recovery.QUALIFICATION_MANIFEST_SHA256,
        recovery.SMOKE_RECEIPT_SHA256,
        recovery.SMOKE_MANIFEST_SHA256,
        recovery.OLD_FORMAL_LOCK_SHA256,
        recovery.OLD_TERMINAL_ARCHIVE_SHA256,
        *recovery.PROFILE_SHA256.values(),
    ):
        assert recovery.SHA256.fullmatch(digest)
    assert recovery.GENERATION_IMAGE_DIGEST == (
        "sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
    )
    assert recovery.V1_REVIEW_IMAGE_DIGEST == (
        "sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10"
    )
    assert recovery.V2_REVIEW_IMAGE_DIGEST == (
        "sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd"
    )


def test_capacity_checker_imports_no_network_or_provider_client():
    source = (
        REPO_ROOT / "scripts" / "phase1_0d_transport_recovery.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports.isdisjoint(
        {"azure", "http", "requests", "socket", "urllib", "openai"}
    )


def test_rate_limits_normalize_original_windows_without_guessing():
    observed = recovery.normalize_rate_limits(
        [
            {"count": 10, "key": "request", "renewalPeriod": 10},
            {"count": 250_000, "key": "token", "renewalPeriod": 30},
        ]
    )
    assert observed["rpm"] == 60
    assert observed["tpm"] == 500_000
    assert observed["original_rules"] == [
        {"count": 10, "key": "request", "renewalPeriod": 10},
        {"count": 250_000, "key": "token", "renewalPeriod": 30},
    ]


@pytest.mark.parametrize(
    "rules",
    (
        None,
        [],
        [{"count": 1, "key": "request", "renewalPeriod": 60}],
        [
            {"count": 1, "key": "request", "renewalPeriod": 60},
            {"count": 2, "key": "request", "renewalPeriod": 60},
            {"count": 3, "key": "token", "renewalPeriod": 60},
        ],
        [
            {"count": 1, "key": "request", "renewalPeriod": 60, "unit": "x"},
            {"count": 3, "key": "token", "renewalPeriod": 60},
        ],
        [
            {"count": 1, "key": "request", "renewalPeriod": 60},
            {"count": 1, "key": "other", "renewalPeriod": 60},
        ],
    ),
)
def test_absent_or_ambiguous_rate_limits_fail_closed(rules):
    with pytest.raises(recovery.RecoveryError):
        recovery.normalize_rate_limits(rules)


def test_capacity_floor_uses_both_tpm_and_rpm():
    assert (
        recovery.minimum_capacity_for_floor(
            36,
            current_tpm=36_000,
            current_rpm=36,
            minimum_tpm=1_000_000,
            minimum_rpm=1_000,
        )
        == 1000
    )
    assert (
        recovery.minimum_capacity_for_floor(
            50,
            current_tpm=50_000,
            current_rpm=50,
            minimum_tpm=500_000,
            minimum_rpm=500,
        )
        == 500
    )


def test_usage_selection_accepts_zero_current_allocation():
    role = "secondary"
    contract = recovery.ROLE_CONTRACTS[role]
    selected = recovery.select_usage_line(
        role,
        {
            "value": [
                {
                    "name": {
                        "value": contract["usage_name"],
                        "localizedValue": "quota",
                    },
                    "unit": "Count",
                    "currentValue": 0,
                    "limit": 1000,
                }
            ]
        },
    )
    assert selected["unallocated"] == 1000


def test_usage_and_model_capacity_selectors_require_one_exact_record():
    role = "third"
    contract = recovery.ROLE_CONTRACTS[role]
    usage = {
        "name": {
            "value": contract["usage_name"],
            "localizedValue": "quota",
        },
        "unit": "Count",
        "currentValue": 50,
        "limit": 1000,
    }
    with pytest.raises(recovery.RecoveryError, match="matched 2"):
        recovery.select_usage_line(role, {"value": [usage, usage]})
    item = {
        "location": contract["location"],
        "properties": {
            "skuName": contract["sku_name"],
            "model": {
                "format": contract["model_format"],
                "name": contract["model_name"],
                "version": contract["model_version"],
            },
            "availableCapacity": 950,
        },
    }
    assert recovery.select_model_capacity(role, {"value": [item]})[
        "available_capacity"
    ] == 950
    item["properties"]["model"]["version"] = "wrong"
    with pytest.raises(recovery.RecoveryError, match="matched 0"):
        recovery.select_model_capacity(role, {"value": [item]})
    item["properties"]["model"]["version"] = contract["model_version"]
    item["properties"]["availableCapacity"] = math.nan
    with pytest.raises(recovery.RecoveryError, match="absent or ambiguous"):
        recovery.select_model_capacity(role, {"value": [item]})


def test_deployment_projection_preserves_rate_rules_and_exact_identity():
    role = "primary"
    contract = recovery.ROLE_CONTRACTS[role]
    raw = {
        "etag": '"etag"',
        "sku": {"name": "GlobalStandard", "capacity": 36},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": "gpt-5.6-sol",
                "version": "2026-07-09",
            },
            "versionUpgradeOption": "OnceNewDefaultVersionAvailable",
            "provisioningState": "Succeeded",
            "currentCapacity": 36,
            "rateLimits": [
                {"count": 36, "key": "request", "renewalPeriod": 60},
                {"count": 36_000, "key": "token", "renewalPeriod": 60},
            ],
        },
    }
    projection = recovery.sanitize_deployment(
        role,
        raw,
        account=contract["account"],
        resource_group=contract["resource_group"],
        endpoint_host=contract["endpoint_host"],
        location=contract["location"],
    )
    assert projection["normalized_rate_limits"] == {
        "rpm": 36,
        "tpm": 36_000,
    }
    raw["properties"]["model"]["version"] = "wrong"
    with pytest.raises(recovery.RecoveryError, match="model differs"):
        recovery.sanitize_deployment(
            role,
            raw,
            account=contract["account"],
            resource_group=contract["resource_group"],
            endpoint_host=contract["endpoint_host"],
            location=contract["location"],
        )


def test_capacity_patch_changes_only_sku_capacity_and_requires_an_increase():
    before = _projection("primary", 36, 36_000, 36, '"before"')
    assert recovery.build_capacity_patch(before, 1000) == {
        "sku": {"name": "GlobalStandard", "capacity": 1000}
    }
    with pytest.raises(recovery.RecoveryError, match="strictly increase"):
        recovery.build_capacity_patch(before, 36)


def test_capacity_change_allowlist_rejects_model_or_route_changes():
    before = _projection("primary", 36, 36_000, 36, '"before"')
    after = copy.deepcopy(before)
    after["etag"] = '"after"'
    after["sku"]["capacity"] = 1000
    after["properties"]["currentCapacity"] = 1000
    after["properties"]["rateLimits"][0]["count"] = 1000
    after["properties"]["rateLimits"][1]["count"] = 1_000_000
    after["normalized_rate_limits"] = {"rpm": 1000, "tpm": 1_000_000}
    # The public projection's derived normalized field is compared separately
    # from the ARM allowlist.
    before_arm = copy.deepcopy(before)
    after_arm = copy.deepcopy(after)
    before_arm.pop("normalized_rate_limits")
    after_arm.pop("normalized_rate_limits")
    assert recovery.verify_capacity_change_allowlist(before_arm, after_arm)
    after_arm["properties"]["model"]["version"] = "different"
    with pytest.raises(recovery.RecoveryError, match="non-allowlisted"):
        recovery.verify_capacity_change_allowlist(before_arm, after_arm)


def test_900_request_body_rollups_are_offline_ordered_and_role_specific(tmp_path):
    form = tmp_path / "03_review_form.jsonl"
    rows = [
        {
            "record_id": f"record-{index:04d}",
            "question": f"What is {index} plus one?",
            "registered_answer": str(index + 1),
            "output_text": f"Final answer: {index + 1}",
        }
        for index in reversed(range(900))
    ]
    form.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    first = recovery.request_body_rollups(form, REPO_ROOT)
    second = recovery.request_body_rollups(form, REPO_ROOT)
    assert first == second
    assert {item["row_count"] for item in first.values()} == {900}
    assert len(
        {
            item["ordered_request_body_sha256_rollup"]
            for item in first.values()
        }
    ) == 3
    assert {item["first_record_id"] for item in first.values()} == {
        "record-0000"
    }
    rows[0]["role"] = "forbidden"
    form.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    with pytest.raises(recovery.RecoveryError, match="keys differ"):
        recovery.request_body_rollups(form, REPO_ROOT)


def test_passing_capacity_certificate_recomputes_and_matches_schema():
    evidence = _passing_evidence()
    certificate = recovery.build_capacity_certificate(evidence)
    recovery.verify_capacity_certificate(
        certificate,
        expected_request_body_rollups=evidence["request_body_rollups"],
        require_request_body_rollups=True,
    )
    assert certificate["capacity_gate_passed"] is True
    assert certificate["terminal_state"] is None
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(certificate)
    assert schema["properties"]["artifact"]["const"] == certificate["artifact"]
    assert (
        schema["properties"]["schema_version"]["const"]
        == certificate["schema_version"]
    )
    assert schema["properties"]["provider_calls"]["properties"]["count"][
        "const"
    ] == 0


def test_insufficient_primary_capacity_blocks_without_fabricating_a_result():
    evidence = _passing_evidence()
    primary = _projection("primary", 36, 36_000, 36, '"primary"')
    evidence["deployments"]["primary"].update(
        {
            "before": copy.deepcopy(primary),
            "after": copy.deepcopy(primary),
            "usage": {
                "name": recovery.ROLE_CONTRACTS["primary"]["usage_name"],
                "localized_value": "quota",
                "current_value": 1000,
                "limit": 1000,
                "unallocated": 0,
                "unit": "Count",
            },
            "mutation": None,
        }
    )
    certificate = recovery.build_capacity_certificate(evidence)
    recovery.verify_capacity_certificate(
        certificate,
        expected_request_body_rollups=evidence["request_body_rollups"],
        require_request_body_rollups=True,
    )
    assert certificate["capacity_gate_passed"] is False
    assert (
        certificate["terminal_state"]
        == "BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY"
    )
    primary_floor = next(
        item
        for item in certificate["mechanical_gates"]
        if item["gate_id"] == "primary.capacity_floor"
    )
    assert primary_floor["observed"] == {"tpm": 36_000, "rpm": 36}
    assert primary_floor["passed"] is False


def test_exact_minimum_etag_guarded_capacity_mutation_can_pass():
    evidence = _passing_evidence()
    role = "secondary"
    contract = recovery.ROLE_CONTRACTS[role]
    before = _projection(role, 50, 50_000, 50, '"before"')
    after = _projection(role, 500, 500_000, 500, '"after"')
    evidence["deployments"][role] = {
        "before": before,
        "after": after,
        "usage": {
            "name": contract["usage_name"],
            "localized_value": "quota",
            "current_value": 50,
            "limit": 1000,
            "unallocated": 950,
            "unit": "Count",
        },
        "model_capacity": _model_capacity(role, 950),
        "mutation": {
            "api_version": "2024-10-01",
            "if_match": '"before"',
            "patch_body": {"sku": {"name": "GlobalStandard", "capacity": 500}},
        },
    }
    certificate = recovery.build_capacity_certificate(evidence)
    assert certificate["capacity_gate_passed"] is True
    recovery.verify_capacity_certificate(
        certificate,
        expected_request_body_rollups=evidence["request_body_rollups"],
        require_request_body_rollups=True,
    )
    evidence["deployments"][role]["mutation"]["if_match"] = '"wrong"'
    assert recovery.build_capacity_certificate(evidence)[
        "capacity_gate_passed"
    ] is False


def test_certificate_tamper_and_overwrite_are_refused(tmp_path, monkeypatch):
    evidence = _passing_evidence()
    monkeypatch.setattr(
        recovery,
        "request_body_rollups",
        lambda *_args, **_kwargs: copy.deepcopy(
            evidence["request_body_rollups"]
        ),
    )
    review_form = tmp_path / "03_review_form.jsonl"
    hashes = recovery.seal_capacity_certificate(
        evidence,
        tmp_path,
        review_form_path=review_form,
    )
    assert recovery.SHA256.fullmatch(hashes["certificate_sha256"])
    with pytest.raises(recovery.RecoveryError, match="overwrite"):
        recovery.seal_capacity_certificate(
            evidence,
            tmp_path,
            review_form_path=review_form,
        )
    certificate_path = tmp_path / recovery.CAPACITY_CERTIFICATE_NAME
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    certificate["provider_calls"]["count"] = 1
    with pytest.raises(recovery.RecoveryError, match="payload hash differs"):
        recovery.verify_capacity_certificate(certificate)


def test_certificate_rejects_rehashed_binding_and_rollup_tampering():
    evidence = _passing_evidence()
    certificate = recovery.build_capacity_certificate(evidence)
    certificate["authority"]["sha256"] = "f" * 64
    unhashed = dict(certificate)
    del unhashed["certificate_payload_sha256"]
    certificate["certificate_payload_sha256"] = recovery.sha256_bytes(
        recovery.canonical_json_bytes(unhashed)
    )
    with pytest.raises(recovery.RecoveryError, match="authority binding differs"):
        recovery.verify_capacity_certificate(
            certificate,
            expected_request_body_rollups=evidence["request_body_rollups"],
            require_request_body_rollups=True,
        )

    certificate = recovery.build_capacity_certificate(evidence)
    independent = copy.deepcopy(evidence["request_body_rollups"])
    independent["primary"]["ordered_request_body_sha256_rollup"] = "e" * 64
    with pytest.raises(recovery.RecoveryError, match="rollups differ"):
        recovery.verify_capacity_certificate(
            certificate,
            expected_request_body_rollups=independent,
            require_request_body_rollups=True,
        )

    evidence = _passing_evidence()
    evidence["deployments"]["primary"]["model_capacity"][
        "available_capacity"
    ] = math.nan
    with pytest.raises(recovery.RecoveryError, match="canonical JSON"):
        recovery.build_capacity_certificate(evidence)


def test_capacity_evidence_freshness_is_bounded_and_fail_closed():
    evidence = _passing_evidence()
    certificate = recovery.build_capacity_certificate(evidence)
    recovery.verify_capacity_evidence_freshness(
        certificate,
        600,
        now_utc=dt.datetime(
            2026, 8, 6, 1, 7, 3, tzinfo=dt.timezone.utc
        ),
    )
    with pytest.raises(recovery.RecoveryError, match="stale"):
        recovery.verify_capacity_evidence_freshness(
            certificate,
            600,
            now_utc=dt.datetime(
                2026, 8, 6, 1, 20, 0, tzinfo=dt.timezone.utc
            ),
        )


def test_capacity_pack_rejects_noncanonical_or_duplicate_json(
    tmp_path, monkeypatch
):
    evidence = _passing_evidence()
    monkeypatch.setattr(
        recovery,
        "request_body_rollups",
        lambda *_args, **_kwargs: copy.deepcopy(
            evidence["request_body_rollups"]
        ),
    )
    review_form = tmp_path / "03_review_form.jsonl"
    recovery.seal_capacity_certificate(
        evidence,
        tmp_path,
        review_form_path=review_form,
    )
    certificate_path = tmp_path / recovery.CAPACITY_CERTIFICATE_NAME
    manifest_path = tmp_path / recovery.CAPACITY_MANIFEST_NAME
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    certificate_path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(recovery.RecoveryError, match="not canonical"):
        recovery.verify_capacity_pack(certificate_path, manifest_path)

    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text('{"key":1,"key":2}\n', encoding="utf-8")
    with pytest.raises(recovery.RecoveryError, match="duplicate JSON key"):
        recovery.load_json(duplicate_path)


def test_recovery_job_is_one_manual_nonretrying_digest_pinned_container():
    job = recovery.build_recovery_job(
        run_id=RUN_ID,
        job_name=JOB_NAME,
        launcher_commit=LAUNCHER_COMMIT,
        capacity_certificate_sha256=CERTIFICATE_SHA,
        capacity_manifest_sha256=MANIFEST_SHA,
        identity_resource_id=IDENTITY_ID,
        environment_resource_id=ENVIRONMENT_ID,
    )
    configuration = job["properties"]["configuration"]
    assert configuration["replicaRetryLimit"] == 0
    assert configuration["manualTriggerConfig"] == {
        "replicaCompletionCount": 1,
        "parallelism": 1,
    }
    containers = job["properties"]["template"]["containers"]
    assert len(containers) == 1
    assert containers[0]["image"] == recovery.V2_REVIEW_IMAGE_REF
    assert containers[0]["resources"] == {"cpu": 2.0, "memory": "4Gi"}
    command = containers[0]["args"][1]
    assert "run_phase1_0d_semantic_review_v2.py review " in command
    assert " qualify " not in command
    assert " smoke " not in command
    assert "run_phase1_0d_confirmation" not in command
    assert "parser" not in command
    assert "jlens" not in command.lower()


def test_recovery_command_and_environment_only_move_allowed_old_job_fields():
    old_command = (
        recovery.recovery_command(RUN_ID)
        .replace(RUN_ID, recovery.OLD_FORMAL_RUN_ID)
        .replace(
            f"{recovery.RECOVERY_RESULT_ROOT}/{recovery.OLD_FORMAL_RUN_ID}",
            recovery.OLD_RESULT_PREFIX,
        )
    )
    expected_old = (
        "timeout --signal=TERM --kill-after=60s 612000s python "
        "/workspace/scripts/run_phase1_0d_semantic_review_v2.py review "
        "--project-root /workspace --out-dir /workspace/runtime/results "
        "--run-id 20260804T181247Z "
        "--client-id 67d9b724-e00b-4a87-a1ce-fce2308685a2 "
        "--blob-account stjspacefiles0709085305 --blob-container jspace-results "
        "--code-commit 1b56f775b5457e2e11124559052ad4caf028fdad "
        "--image-digest "
        "sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd "
        "--execution-timeout-seconds 612000 "
        "--qualification-receipt-prefix "
        "phase1-0d-semantic-review-v2/qualification/20260803T230642Z "
        "--gate-receipt-prefix "
        "phase1-0d-semantic-review-v2/smoke/20260803T235227Z "
        "--gate-manifest-sha256 "
        "aa0aabb37a9a41bea476fd5e612fc32208af9495316e30ad98081481a07a3c43 "
        "--gate-receipt-sha256 "
        "c1bd6cbbcf888511cfee9da48111e7950f0c746988937a02a386dfcc574137fc "
        "--pack-blob-prefix phase1-headroom-confirmation/20260804T154518Z "
        "--source-manifest-sha256 "
        "76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536 "
        "--out-blob-prefix "
        "phase1-headroom-confirmation-review-v2/20260804T181247Z"
    )
    assert shlex.split(old_command) == shlex.split(expected_old)
    environment = {
        item["name"]: item["value"]
        for item in recovery.recovery_environment(RUN_ID)
    }
    assert environment["JSPACE_REVIEW_MODE"] == "review"
    assert environment["JSPACE_QUALIFICATION_RECEIPT_SHA256"] == ""
    assert environment["JSPACE_QUALIFICATION_MANIFEST_SHA256"] == ""
    assert environment["JSPACE_REVIEW_RUN_ID"] == RUN_ID


def test_job_readback_rejects_any_semantic_or_retry_mutation():
    expected = recovery.build_recovery_job(
        run_id=RUN_ID,
        job_name=JOB_NAME,
        launcher_commit=LAUNCHER_COMMIT,
        capacity_certificate_sha256=CERTIFICATE_SHA,
        capacity_manifest_sha256=MANIFEST_SHA,
        identity_resource_id=IDENTITY_ID,
        environment_resource_id=ENVIRONMENT_ID,
    )
    readback = copy.deepcopy(expected)
    readback.update(
        {
            "name": JOB_NAME,
            "id": "redacted",
            "type": "Microsoft.App/jobs",
            "resourceGroup": "rg-jspace-observation-sea",
            "systemData": {},
        }
    )
    readback["properties"].update(
        {
            "provisioningState": "Succeeded",
            "runningStatus": "Ready",
            "eventStreamEndpoint": "redacted",
            "outboundIpAddresses": ["redacted"],
        }
    )
    readback["properties"]["configuration"].update(
        {
            "dapr": None,
            "eventTriggerConfig": None,
            "identitySettings": [],
            "scheduleTriggerConfig": None,
            "secrets": None,
        }
    )
    container = readback["properties"]["template"]["containers"][0]
    container["imageType"] = "ContainerImage"
    container["resources"]["ephemeralStorage"] = ""
    readback["properties"]["template"]["initContainers"] = None
    readback["properties"]["template"]["volumes"] = None
    for binding in readback["identity"]["userAssignedIdentities"].values():
        binding.update({"clientId": "redacted", "principalId": "redacted"})
    for registry in readback["properties"]["configuration"]["registries"]:
        registry.update({"username": "", "passwordSecretRef": ""})
    recovery.verify_recovery_job(
        readback,
        run_id=RUN_ID,
        job_name=JOB_NAME,
        launcher_commit=LAUNCHER_COMMIT,
        capacity_certificate_sha256=CERTIFICATE_SHA,
        capacity_manifest_sha256=MANIFEST_SHA,
        identity_resource_id=IDENTITY_ID,
        environment_resource_id=ENVIRONMENT_ID,
    )
    readback["properties"]["configuration"]["replicaRetryLimit"] = 1
    with pytest.raises(recovery.RecoveryError, match="readback differs"):
        recovery.verify_recovery_job(
            readback,
            run_id=RUN_ID,
            job_name=JOB_NAME,
            launcher_commit=LAUNCHER_COMMIT,
            capacity_certificate_sha256=CERTIFICATE_SHA,
            capacity_manifest_sha256=MANIFEST_SHA,
            identity_resource_id=IDENTITY_ID,
            environment_resource_id=ENVIRONMENT_ID,
        )


def test_lock_binds_certificate_profiles_old_state_and_fixed_result_prefix():
    lock = recovery.build_recovery_lock(
        run_id=RUN_ID,
        job_name=JOB_NAME,
        launcher_commit=LAUNCHER_COMMIT,
        capacity_certificate_sha256=CERTIFICATE_SHA,
        capacity_manifest_sha256=MANIFEST_SHA,
        request_body_rollups_value=_rollups(),
    )
    assert lock["capacity"]["capacity_gate_passed"] is True
    assert lock["profile_sha256"] == recovery.PROFILE_SHA256
    assert lock["old_formal"]["lock_sha256"] == recovery.OLD_FORMAL_LOCK_SHA256
    assert lock["old_formal"]["result_object_count"] == 0
    assert lock["result_prefix"] == f"{recovery.RECOVERY_RESULT_ROOT}/{RUN_ID}"
    assert recovery.RECOVERY_LOCK_BLOB == (
        "phase1-0d-semantic-review-v2/transport-recovery/"
        "formal-review-lock.json"
    )


def test_zero_multiple_or_conflicting_start_outcomes_are_never_retried():
    for after, response in (([], None), (["one", "two"], None), (["one"], "two")):
        result = recovery.classify_start([], response, after)
        assert result["state"] == (
            "BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY"
        )
        assert result["start_may_be_retried"] is False
    established = recovery.classify_start([], None, ["one"])
    assert established == {
        "state": "EXECUTION_ESTABLISHED",
        "execution_name": "one",
        "start_may_be_retried": False,
    }
    with pytest.raises(recovery.RecoveryError, match="not inert"):
        recovery.classify_start(["old"], None, ["old"])


def test_success_and_terminal_archive_membership_checks_fail_closed():
    recovery.verify_success_members(sorted(recovery.SUCCESS_REQUIRED_MEMBERS))
    with pytest.raises(recovery.RecoveryError, match="lacks members"):
        recovery.verify_success_members(["00_execution_receipt.json"])
    terminal = sorted(
        recovery.TERMINAL_ARCHIVE_MEMBERS | {"artifact_manifest.json"}
    )
    recovery.verify_terminal_archive_members(terminal)
    with pytest.raises(recovery.RecoveryError, match="membership differs"):
        recovery.verify_terminal_archive_members(
            [*terminal, "partial_judgments.json"]
        )


def test_launcher_has_no_override_surface_and_only_one_start_call_site():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "if (( $# != 0 )); then" in text
    assert "REVIEW_MODE" not in text
    assert "${RESOURCE_GROUP:-" not in text
    assert "${PROJECT_SHA:-" not in text
    assert "${REPLICA_TIMEOUT:-" not in text
    assert "${REVIEW_TIMEOUT_SECONDS:-" not in text
    assert text.count("/start?api-version=") == 1
    assert text.count("START_STATUS=\"$(curl") == 1
    assert "start_may_be_retried=false" in text
    assert "az containerapp job start" not in text
    assert '--header "If-None-Match: *"' in text
    assert 'JOB_NAME="job-p10d-rv2-tr-${CAPACITY_CERTIFICATE_SHA256:0:8}"' in text
    assert text.count("verify-freshness") == 2
    assert "V2_TAG_WRITE" in text
    assert "V2_MANIFEST_DELETE" in text
    assert recovery.GENERATION_EXECUTION in text
    assert recovery.OLD_FORMAL_EXECUTION in text
    assert recovery.OLD_TERMINAL_ARCHIVE_SHA256 in text
    assert recovery.SOURCE_MANIFEST_SHA256 in text
    assert (
        ']] \\\n'
        '    || ! cmp -s "$COMMITTED_SOURCE_MANIFEST" '
        '"$BLOB_SOURCE_MANIFEST"; then'
    ) in text
    assert (
        '|| ! cmp -s "$COMMITTED_SOURCE_MANIFEST" '
        '"$BLOB_SOURCE_MANIFEST" ]]'
        not in text
    )
    assert "parser_v3" not in text
    assert "jlens" not in text.lower()


def test_launcher_is_valid_bash_syntax_on_the_azure_test_host():
    completed = subprocess.run(
        ["bash", "-n", str(LAUNCHER)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
