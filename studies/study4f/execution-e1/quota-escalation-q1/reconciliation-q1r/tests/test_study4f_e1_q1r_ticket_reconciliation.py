"""Study 4F-E1-Q1R ticket-reconciliation and routing-survey invariants.

These tests are offline. They do not contact Azure, construct a model, or
execute a scientific cell.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve()
Q1R = HERE.parents[1]
Q1 = Q1R.parent
E1 = Q1.parent
STUDY4F = E1.parent
ROOT = STUDY4F.parents[1]

START_COMMIT = "01c07d83e8be3dd9ba2bebb31869af944ae2a21b"
START_TREE = "cca35c2178bd1c2b8688468a888eab8cd9d5b2ed"
AUTHORITY_COMMIT = "6e38543a68acffc4014fda7beff79d675a51d44a"
AUTHORITY_TREE = "328d2c281dfd87f9cbae71c4ee0838a0c0b85e2a"

AUTHORITY = (
    STUDY4F
    / "prompts"
    / "study4f_e1_q1_ticket_identity_reconciliation_and_global_routing_"
    "authority.md"
)
RECEIPT = Q1R / "reconciliation_receipt.json"
RECEIPT_SCHEMA = Q1R / "reconciliation_receipt.schema.json"
SURVEY = Q1R / "global_routing_survey.json"
SURVEY_SCHEMA = Q1R / "global_routing_survey.schema.json"
ORIGINAL_RECEIPT = Q1 / "support_ticket_receipt.json"

CLASS_RANK = {
    "R0_QUOTA_ALREADY_SUFFICIENT": 0,
    "R1_SKU_ALLOWED_QUOTA_INSUFFICIENT": 1,
    "R2_SUBSCRIPTION_RESTRICTED": 2,
    "R3_NOT_OFFERED_OR_UNRESOLVABLE": 3,
}
REQUIRED = {"H100": 40, "A100": 24}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _test_body(source: str, name: str) -> str:
    start = source.index(f"def {name}")
    tail = source[start:]
    marker = tail.find("\ndef ", 1)
    return tail if marker < 0 else tail[:marker]


@pytest.fixture(scope="module")
def receipt():
    return _json(RECEIPT)


@pytest.fixture(scope="module")
def survey():
    return _json(SURVEY)


def test_q1r_authority_is_byte_exact_and_was_published_alone(receipt):
    identity = receipt["authority"]
    payload = AUTHORITY.read_bytes()
    assert len(payload) == identity["bytes"] == 8544
    assert hashlib.sha256(payload).hexdigest() == identity["sha256"]
    assert _git("hash-object", str(AUTHORITY)).strip() == identity["git_blob"]
    assert identity["commit"] == AUTHORITY_COMMIT
    assert identity["tree"] == AUTHORITY_TREE
    assert identity["parent_commit"] == START_COMMIT
    assert identity["parent_tree"] == START_TREE
    assert identity["published_alone_as_first_successor_commit"] is True

    paths = [
        line
        for line in _git(
            "show", "--name-only", "--format=", AUTHORITY_COMMIT
        ).splitlines()
        if line
    ]
    assert paths == [
        "studies/study4f/prompts/"
        "study4f_e1_q1_ticket_identity_reconciliation_and_global_routing_"
        "authority.md"
    ]
    assert _git("show", "-s", "--format=%P", AUTHORITY_COMMIT).strip() == (
        START_COMMIT
    )


def test_q1r_authority_is_published_in_linear_origin_main_history():
    subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
         AUTHORITY_COMMIT, "origin/main"],
        check=True,
    )
    assert not _git("rev-list", "--merges", f"{START_COMMIT}..HEAD").strip()


def test_every_protected_q1_artifact_is_byte_identical_to_start(receipt):
    recorded = receipt["historical_q1_preservation"]
    assert recorded["protected_start_commit"] == START_COMMIT
    assert recorded["original_q1_bytes_modified"] is False
    assert (
        recorded["original_incorrect_suffix_preserved_in_historical_bytes"]
        is True
    )
    for artifact in recorded["artifacts"].values():
        path = artifact["path"]
        payload = (ROOT / path).read_bytes()
        start_blob = _git("rev-parse", f"{START_COMMIT}:{path}").strip()
        head_blob = _git("rev-parse", f"HEAD:{path}").strip()
        assert start_blob == head_blob == artifact["git_blob"]
        assert artifact["blob_at_start"] == start_blob
        assert artifact["byte_identical_to_start"] is True
        assert len(payload) == artifact["bytes"]
        assert hashlib.sha256(payload).hexdigest() == artifact["sha256"]


def test_no_original_q1_path_was_removed_or_modified():
    original = [
        line
        for line in _git(
            "ls-tree",
            "-r",
            "--name-only",
            START_COMMIT,
            "studies/study4f/execution-e1/quota-escalation-q1",
        ).splitlines()
        if line
    ]
    assert original
    changed = []
    for path in original:
        if _git("rev-parse", f"{START_COMMIT}:{path}").strip() != _git(
            "rev-parse", f"HEAD:{path}"
        ).strip():
            changed.append(path)
    assert changed == []


def test_reconciliation_uses_the_governing_customer_field(receipt):
    reconciliation = receipt["reconciliation"]
    assert reconciliation["classification"] == (
        "Q1_REGISTERED_REDACTED_TICKET_IDENTITY_TRANSCRIPTION_ERROR_CONFIRMED"
    )
    assert reconciliation["mismatch_type"] == "suffix_transcription"
    assert reconciliation["suffix_transcription_error"] is True
    assert reconciliation["wrong_api_field_comparison"] is False
    assert (
        reconciliation["governing_customer_identity_field"]
        == "properties.supportTicketId"
    )
    assert reconciliation["arm_resource_identity_field"] == "name"
    assert reconciliation["identities_are_distinct"] is True
    assert reconciliation["corrected_customer_ticket_suffix"] == "1753"
    assert reconciliation["historical_incorrect_registered_suffix"] == "3753"


def test_complete_ticket_tuple_matched_without_suffix_only_reasoning(receipt):
    reconciliation = receipt["reconciliation"]
    assert reconciliation["complete_tuple_matched"] is True
    assert all(reconciliation["tuple_checks"].values())
    assert reconciliation["historical_hash_matches_customer_ticket_id"] is True
    assert reconciliation["historical_hash_matches_arm_resource_name"] is False

    ticket = receipt["support_ticket_observation"]
    assert ticket["get_count"] == 1
    assert ticket["read_only"] is True
    assert ticket["created_date_normalized"] == "2026-08-18T06:25:01Z"
    assert ticket["status"] == "Open"
    assert ticket["region"] == "australiaeast"
    assert ticket["vm_family"].casefold() == (
        "standardNCadsH100v5Family".casefold()
    )
    assert ticket["requested_limit"] == 40
    assert ticket["problem_classification_display_name"] == (
        "Compute-VM (cores-vCPUs) subscription limit increases"
    )
    assert ticket["subscription_last_four"] == "d32e"


def test_q1r_commits_only_separately_labelled_salted_identity_hashes(receipt):
    reconciliation = receipt["reconciliation"]
    customer_hash = reconciliation["customer_ticket_id_salted_sha256"]
    resource_hash = reconciliation["arm_resource_name_salted_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", customer_hash)
    assert re.fullmatch(r"[0-9a-f]{64}", resource_hash)
    assert customer_hash != resource_hash
    assert "customer-facing-support-ticket-id" in (
        reconciliation["customer_ticket_id_salt_material"]
    )
    assert "arm-support-ticket-resource-name" in (
        reconciliation["arm_resource_name_salt_material"]
    )
    assert reconciliation["full_customer_ticket_id_committed_by_q1r"] is False
    assert reconciliation["full_arm_resource_name_committed_by_q1r"] is False


def test_no_q1r_artifact_leaks_a_full_ticket_or_repeats_the_arm_name():
    historical_arm_name = _json(ORIGINAL_RECEIPT)["submitted_support_ticket"][
        "ticket_resource_name"
    ]
    tracked = [
        line
        for line in _git(
            "ls-files",
            "studies/study4f/execution-e1/quota-escalation-q1/"
            "reconciliation-q1r",
            str(AUTHORITY.relative_to(ROOT)).replace("\\", "/"),
        ).splitlines()
        if line
    ]
    assert tracked
    full_case = re.compile(r"\b\d{16}\b")
    guid = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )
    for relative in tracked:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="strict")
        assert full_case.search(text) is None, relative
        assert guid.search(text) is None, relative
        assert historical_arm_name not in text, relative


def test_receipt_and_survey_validate_against_restrictive_schemas(
    receipt, survey
):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(receipt, _json(RECEIPT_SCHEMA))
    jsonschema.validate(survey, _json(SURVEY_SCHEMA))


def test_backlog_is_pending_not_approval_or_final_denial(receipt):
    response = receipt["support_correspondence"]
    assert response["classification"] == (
        "BACKLOG_PENDING_NO_APPROVAL_NO_FINAL_DENIAL"
    )
    assert response == {
        "classification": "BACKLOG_PENDING_NO_APPROVAL_NO_FINAL_DENIAL",
        "is_approval": False,
        "grants_quota": False,
        "is_final_denial": False,
        "request_remains_pending": True,
        "additional_information_required": False,
        "authorizes_h100_execution": False,
        "authorizes_a100_fallback": False,
        "authorizes_duplicate_ticket": False,
    }


def test_current_h100_quota_was_read_once_and_did_not_open_the_gate(receipt):
    quota = receipt["current_quota_observation"]
    assert quota["query_count"] == 1
    assert quota["read_only"] is True
    assert quota["region"] == "australiaeast"
    assert quota["family"] == "StandardNCadsH100v5Family"
    assert quota["used"] == 0
    assert quota["limit"] == 0
    assert quota["required_limit"] == 40
    assert quota["visible_quota_gate_satisfied"] is False
    assert quota["total_regional_vcpu_used"] == 0
    assert quota["total_regional_vcpu_limit"] == 100


def test_survey_covers_every_region_for_each_registered_route(survey):
    regions = {entry["region"] for entry in survey["entries"]}
    assert len(regions) == survey["scope"]["physical_regions_enumerated"] == 63
    assert len(survey["entries"]) == 126 == 2 * len(regions)
    for region in regions:
        assert {
            entry["route"]
            for entry in survey["entries"]
            if entry["region"] == region
        } == {"H100", "A100"}
    assert all(
        entry["physical_capacity"] == "UNKNOWN_NOT_TESTED"
        for entry in survey["entries"]
    )


def test_each_route_classification_follows_the_registered_rules(survey):
    for entry in survey["entries"]:
        classification = entry["classification"]
        assert classification in CLASS_RANK
        if not entry["sku_offered"]:
            assert classification == "R3_NOT_OFFERED_OR_UNRESOLVABLE"
        elif entry["not_available_for_subscription"]:
            assert classification == "R2_SUBSCRIPTION_RESTRICTED"
        elif entry["family_quota_limit"] is None:
            assert classification == "R3_NOT_OFFERED_OR_UNRESOLVABLE"
        else:
            expected = (
                "R0_QUOTA_ALREADY_SUFFICIENT"
                if entry["family_quota_deficit"] == 0
                and entry["regional_quota_deficit"] == 0
                else "R1_SKU_ALLOWED_QUOTA_INSUFFICIENT"
            )
            assert classification == expected
    assert not any(
        entry["classification"] == "R0_QUOTA_ALREADY_SUFFICIENT"
        for entry in survey["entries"]
    )


def test_rankings_are_recomputed_from_the_registered_order(survey):
    infinity = 10**9
    for route in ("H100", "A100"):
        entries = [
            entry for entry in survey["entries"] if entry["route"] == route
        ]
        expected = sorted(
            entries,
            key=lambda entry: (
                CLASS_RANK[entry["classification"]],
                infinity
                if entry["family_quota_deficit"] is None
                else entry["family_quota_deficit"],
                infinity
                if entry["regional_quota_deficit"] is None
                else entry["regional_quota_deficit"],
                entry["region"],
            ),
        )
        observed = survey["rankings"][route]
        assert [item["rank"] for item in observed] == list(
            range(1, len(observed) + 1)
        )
        assert [
            (
                item["region"],
                item["classification"],
                item["family_quota_deficit"],
                item["regional_quota_deficit"],
            )
            for item in observed
        ] == [
            (
                item["region"],
                item["classification"],
                item["family_quota_deficit"],
                item["regional_quota_deficit"],
            )
            for item in expected
        ]


def test_survey_recommends_at_most_one_future_candidate_per_route(survey):
    recommendations = survey["recommendations"]
    assert set(recommendations) == {"H100", "A100"}
    assert recommendations["H100"]["region"] == "australiaeast"
    assert recommendations["H100"]["family_quota_deficit"] == 40
    assert recommendations["A100"]["region"] == "brazilsouth"
    assert recommendations["A100"]["family_quota_deficit"] == 24
    for recommendation in recommendations.values():
        assert recommendation["kind"] == (
            "ONE_FUTURE_OPERATOR_AUTHORIZED_QUOTA_CANDIDATE"
        )
        assert recommendation["classification"] == (
            "R1_SKU_ALLOWED_QUOTA_INSUFFICIENT"
        )
        assert recommendation["future_quota_request_recommended"] is True


def test_read_counts_show_no_retry_polling_or_duplicate_ticket_get(survey):
    reads = survey["read_counts"]
    assert reads == {
        "subscription_location_queries": 1,
        "target_sku_queries": 2,
        "current_australiaeast_h100_quota_queries": 1,
        "current_australiaeast_h100_quota_queries_reused": 1,
        "additional_compute_usage_queries": 28,
        "australiaeast_a100_specific_quota_queries": 1,
        "support_ticket_gets_reused": 1,
        "survey_retries": 0,
        "polling_loops": 0,
    }


def test_no_azure_write_scientific_execution_or_fallback_activation(
    receipt, survey
):
    assert not any(receipt["write_counters"].values())
    assert not any(receipt["scientific_counters"].values())
    assert receipt["a100_fallback"] == {
        "authorized": False,
        "activated": False,
        "support_request_submitted": False,
    }
    safety = survey["safety"]
    for name, value in safety.items():
        assert value in (0, False), (name, value)
    assert receipt["shakedown_allowance"] == {
        "attempts_remaining": 2,
        "accelerator_hours_remaining": 6,
        "consumed_by_this_invocation": 0,
    }


def test_lifecycle_and_claim_ceiling_are_unchanged(receipt):
    assert receipt["state"] == (
        "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION"
    )
    assert not any(receipt["claim_boundary"].values())


def test_q1r_additions_are_copy_on_write_and_inside_successor_scope():
    changed = {}
    for line in _git("diff", "--name-status", START_COMMIT, "HEAD").splitlines():
        code, path = line.split("\t", 1)
        changed[path] = code
    assert set(changed.values()) == {"A"}
    prefix = (
        "studies/study4f/execution-e1/quota-escalation-q1/"
        "reconciliation-q1r/"
    )
    authority = str(AUTHORITY.relative_to(ROOT)).replace("\\", "/")
    assert set(path for path in changed if not path.startswith(prefix)) == {
        authority
    }


def test_two_new_q1_scope_expiries_are_mechanically_scope_only():
    module = (
        "studies/study4f/execution-e1/quota-escalation-q1/tests/"
        "test_study4f_e1_q1_quota_escalation.py"
    )
    assert _git("rev-parse", f"{START_COMMIT}:{module}").strip() == _git(
        "rev-parse", f"HEAD:{module}"
    ).strip()
    source = (ROOT / module).read_text(encoding="utf-8")
    names = (
        "test_q1_added_paths_only_inside_its_own_namespace_and_the_authority",
        "test_the_one_new_scope_expiry_is_mechanically_scope_only",
    )
    authority = str(AUTHORITY.relative_to(ROOT)).replace("\\", "/")
    original_authority = (
        "studies/study4f/prompts/"
        "study4f_e1_q1_manual_quota_escalation_and_conditional_resume_"
        "authority.md"
    )
    assert authority != original_authority
    for name in names:
        body = _test_body(source, name)
        assert '"diff", "--name-status"' in body
        assert '"HEAD"' in body
        assert original_authority in body.replace('"\n', "").replace(
            "\n", ""
        ) or "authority =" in body
        for forbidden in (
            "Standard_NC40ads_H100_v5",
            "StandardNCadsH100v5Family",
            "requested_new_limit",
            "model_calls",
            "cells_executed",
        ):
            assert forbidden not in body


def test_scope_expiries_are_outside_the_registered_default_suite():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'testpaths = ["tests"]' in pyproject
    assert not str(HERE.relative_to(ROOT)).replace("\\", "/").startswith(
        "tests/"
    )


def test_every_q1r_artifact_is_lf_only_without_a_bom():
    paths = list(Q1R.rglob("*.json")) + list(Q1R.rglob("*.py"))
    paths.append(AUTHORITY)
    disclosure = Q1R / "Q1R_INVOCATION_DISCLOSURE.md"
    if disclosure.exists():
        paths.append(disclosure)
    assert paths
    for path in paths:
        payload = path.read_bytes()
        assert payload
        assert b"\r" not in payload, path
        assert payload.endswith(b"\n"), path
        assert not payload.startswith(b"\xef\xbb\xbf"), path
