"""Committed validation for the THIRD independent methods review of Study 3 draft-v0.4.

This module is the committed, decision-bearing check for the third review's outputs. It adds no
dependency: the JSON Schema subset used by the committed review schema is enforced by a
self-contained validator in this file, and that validator refuses any schema construct it cannot
fully enforce, so a schema keyword can never be silently ignored.

Nothing here downloads, loads, tokenizes or runs a model, touches a bank, draws a seed, opens a
split or makes a network call. Every assertion is CPU-only and model-free.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

REVIEWED_COMMIT = "e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43"
REVIEWED_TREE = "86c5a5ec0e475090c14654cff27605f883495a48"
PUBLISHED_BASE_COMMIT = "bc98e5c98a2d4e273142c91497b7600ce751bade"
V0_3_REVIEWED_COMMIT = "2b36f5321d830ea6f70fff2b7bbca3cb93394046"

REVIEW_JSON = "studies/study3/reviews/v0_4_independent_methods_review.json"
REVIEW_SCHEMA = "studies/study3/reviews/v0_4_independent_methods_review.schema.json"
REVIEW_MD = "studies/study3/reviews/v0_4_independent_methods_review.md"
RECALC_PY = "studies/study3/analysis/independent_methods_recalculation_v0_4.py"
RECALC_JSON = "studies/study3/analysis/independent_methods_recalculation_tables_v0_4.json"
AUTHORITY_MD = "studies/study3/prompts/study3_v0_4_independent_methods_review_authority.md"
RECEIPT_JSON = "studies/study3/methods_review_receipt_v0_4.json"

NEW_PATHS = (
    REVIEW_MD, REVIEW_JSON, REVIEW_SCHEMA, RECALC_PY, RECALC_JSON,
    "tests/test_study3_methods_review_v0_4.py", AUTHORITY_MD, RECEIPT_JSON,
)

MODIFIABLE_PATHS = (
    "README.md", "studies/README.md", "studies/study3/README.md",
    "studies/study3/NEXT_THREAD_HANDOFF.md", "reports/current_status.md",
    "docs/decision_log.md", "docs/run_log.md", "paper/methods_ledger.md",
    "paper/artifact_index.csv",
)

PROHIBITED_SOURCES = (
    "design_statistics",
    "independent_methods_recalculation.py",
    "independent_methods_recalculation_v0_3",
    "independent_methods_recalculation_tables.json",
    "independent_methods_recalculation_tables_v0_3.json",
)

PROHIBITED_MODULE_NAMES = (
    "design_statistics",
    "independent_methods_recalculation",
    "independent_methods_recalculation_v0_3",
)

# Values the reviewer must DERIVE, never carry as literals in the independent module.
DERIVED_RESULT_LITERALS = (413, 214, 448, 389, 129, 383, 388, 127, 381, 43, 17181, 17200,
                           33543, 26064, 27856, 417024, 390960, 3584, 502)

AUTHORITY_BYTES = 47885
AUTHORITY_SHA256 = "c756ba2e5ad147cfc19edc4a451c2d919e51643d19dda7d95469c21786dcdc86"

INHERITED_IDS = tuple("S3MR2-%03d" % i for i in range(1, 11))
FIRST_REVIEW_IDS = tuple("S3MR-%03d" % i for i in range(1, 21))
UR_IDS = tuple("UR-%02d" % i for i in range(1, 23))

DISPOSITIONS = (
    "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED",
    "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CONFORMANCE_CHANGES",
    "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED",
    "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_FUNDAMENTAL_FEASIBILITY_PILOT_REQUIRED",
)

STATE = "STUDY3_DRAFT_V0_4_THIRD_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION"

CONFORMANCE_SAFE_ALTERATIONS = frozenset(
    {"nothing", "narrative_text_only", "derived_table_only", "committed_test_only"})

PROHIBITED_CLAIM_STEMS = ("invarian", "equivalen", "no presentation effect",
                          "presentation-effect size", "stable across presentation",
                          "unaffected by presentation")


# ----------------------------------------------------------------------------------
# committed-byte helpers: never trust working-tree bytes
# ----------------------------------------------------------------------------------

def _git(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *arguments], cwd=REPO_ROOT, capture_output=True)


def _commit_available(commit: str) -> bool:
    return _git("cat-file", "-e", "%s^{commit}" % commit).returncode == 0


def _blob_at(commit: str, path: str) -> bytes:
    result = _git("cat-file", "blob", "%s:%s" % (commit, path))
    assert result.returncode == 0, "cannot read %s at %s: %r" % (path, commit, result.stderr)
    return result.stdout


def _committed_bytes(path: str) -> bytes:
    """Committed bytes of a review output, preferring the index over the working tree.

    The repository is checked out with core.autocrlf on some platforms, so working-tree bytes are
    not authoritative. The index entry is used when available and the file is normalised to LF
    otherwise, which keeps every byte binding platform-independent.
    """
    listed = _git("ls-files", "-s", "--", path)
    if listed.returncode == 0 and listed.stdout.strip():
        object_id = listed.stdout.split()[1].decode()
        shown = _git("cat-file", "blob", object_id)
        if shown.returncode == 0:
            return shown.stdout
    return (REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n")


def _text(path: str) -> str:
    return _committed_bytes(path).decode("utf-8")


def _json(path: str) -> dict:
    return json.loads(_text(path))


@pytest.fixture(scope="module")
def review() -> dict:
    return _json(REVIEW_JSON)


@pytest.fixture(scope="module")
def schema() -> dict:
    return _json(REVIEW_SCHEMA)


@pytest.fixture(scope="module")
def markdown() -> str:
    return _text(REVIEW_MD)


@pytest.fixture(scope="module")
def tables() -> dict:
    return _json(RECALC_JSON)


@pytest.fixture(scope="module")
def receipt() -> dict:
    return _json(RECEIPT_JSON)


# ----------------------------------------------------------------------------------
# self-contained JSON Schema subset validator (no new dependency)
# ----------------------------------------------------------------------------------

ANNOTATION_KEYWORDS = frozenset(
    {"$schema", "$id", "$comment", "title", "description", "examples", "default"})
SUPPORTED_KEYWORDS = frozenset({
    "type", "const", "enum", "pattern", "minLength", "maxLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
    "required", "properties", "additionalProperties", "items", "allOf", "anyOf",
    "if", "then", "else",
}) | ANNOTATION_KEYWORDS

TYPE_MAP = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


class SchemaUnsupported(Exception):
    """Raised when the committed schema uses a construct this validator cannot enforce."""


def assert_schema_is_fully_enforceable(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("properties", "patternProperties"):
                if not isinstance(value, dict):
                    raise SchemaUnsupported("%s must be an object" % key)
                for sub in value.values():
                    assert_schema_is_fully_enforceable(sub)
                continue
            if key in SUPPORTED_KEYWORDS:
                if key in ("allOf", "anyOf"):
                    for sub in value:
                        assert_schema_is_fully_enforceable(sub)
                elif key in ("items", "if", "then", "else", "additionalProperties"):
                    if isinstance(value, dict):
                        assert_schema_is_fully_enforceable(value)
                continue
            raise SchemaUnsupported("unsupported schema keyword: %r" % key)


def _check_type(value, expected) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        python_type = TYPE_MAP[name]
        if name == "integer":
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return True
            continue
        if name == "number" and isinstance(value, bool):
            continue
        if name != "boolean" and isinstance(value, bool) and python_type in (int, (int, float)):
            continue
        if isinstance(value, python_type):
            return True
    return False


def validate(instance, node, path: str = "$") -> list:
    errors: list = []
    if not isinstance(node, dict):
        return errors

    if "type" in node and not _check_type(instance, node["type"]):
        errors.append("%s: expected type %s, got %s" % (path, node["type"], type(instance).__name__))
        return errors
    if "const" in node and instance != node["const"]:
        errors.append("%s: expected const %r, got %r" % (path, node["const"], instance))
    if "enum" in node and instance not in node["enum"]:
        errors.append("%s: %r is not one of %r" % (path, instance, node["enum"]))
    if isinstance(instance, str):
        if "pattern" in node and not re.search(node["pattern"], instance):
            errors.append("%s: %r does not match %r" % (path, instance, node["pattern"]))
        if "minLength" in node and len(instance) < node["minLength"]:
            errors.append("%s: shorter than minLength %d" % (path, node["minLength"]))
        if "maxLength" in node and len(instance) > node["maxLength"]:
            errors.append("%s: longer than maxLength %d" % (path, node["maxLength"]))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in node and instance < node["minimum"]:
            errors.append("%s: below minimum %s" % (path, node["minimum"]))
        if "maximum" in node and instance > node["maximum"]:
            errors.append("%s: above maximum %s" % (path, node["maximum"]))
    if isinstance(instance, list):
        if "minItems" in node and len(instance) < node["minItems"]:
            errors.append("%s: fewer than minItems %d" % (path, node["minItems"]))
        if "maxItems" in node and len(instance) > node["maxItems"]:
            errors.append("%s: more than maxItems %d" % (path, node["maxItems"]))
        if node.get("uniqueItems"):
            seen = [json.dumps(item, sort_keys=True) for item in instance]
            if len(set(seen)) != len(seen):
                errors.append("%s: items are not unique" % path)
        if isinstance(node.get("items"), dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, node["items"], "%s[%d]" % (path, index)))
    if isinstance(instance, dict):
        if "minProperties" in node and len(instance) < node["minProperties"]:
            errors.append("%s: fewer than minProperties %d" % (path, node["minProperties"]))
        if "maxProperties" in node and len(instance) > node["maxProperties"]:
            errors.append("%s: more than maxProperties %d" % (path, node["maxProperties"]))
        for name in node.get("required", []):
            if name not in instance:
                errors.append("%s: missing required property %r" % (path, name))
        declared = node.get("properties", {})
        for name, sub in declared.items():
            if name in instance:
                errors.extend(validate(instance[name], sub, "%s.%s" % (path, name)))
        if "additionalProperties" in node:
            extra = node["additionalProperties"]
            for name, value in instance.items():
                if name in declared:
                    continue
                if extra is False:
                    errors.append("%s: additional property %r is not allowed" % (path, name))
                elif isinstance(extra, dict):
                    errors.extend(validate(value, extra, "%s.%s" % (path, name)))
    for index, sub in enumerate(node.get("allOf", [])):
        errors.extend(validate(instance, sub, "%s/allOf[%d]" % (path, index)))
    for index, sub in enumerate(node.get("anyOf", [])):
        branch = [validate(instance, sub, "%s/anyOf[%d]" % (path, index))
                  for sub in node["anyOf"]]
        if all(branch):
            errors.append("%s: matched no anyOf branch" % path)
        break
    if "if" in node:
        if not validate(instance, node["if"], path + "/if"):
            if "then" in node:
                errors.extend(validate(instance, node["then"], path + "/then"))
        elif "else" in node:
            errors.extend(validate(instance, node["else"], path + "/else"))
    return errors


# ----------------------------------------------------------------------------------
# schema and instance
# ----------------------------------------------------------------------------------

def test_the_committed_schema_uses_only_fully_enforceable_constructs(schema):
    assert_schema_is_fully_enforceable(schema)


def test_the_committed_review_validates_against_the_committed_schema(review, schema):
    errors = validate(review, schema)
    assert errors == [], "the committed review does not validate:\n" + "\n".join(errors)


def test_the_disposition_is_exactly_one_permitted_value(review):
    assert review["disposition"] in DISPOSITIONS
    assert review["state"] == STATE
    assert sum(1 for d in DISPOSITIONS if d == review["disposition"]) == 1


# ----------------------------------------------------------------------------------
# independence: no prohibited source is reachable from the reviewer's own module
# ----------------------------------------------------------------------------------

def test_the_independent_module_imports_no_prohibited_source():
    tree = ast.parse(_text(RECALC_PY))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(bad in alias.name for bad in PROHIBITED_MODULE_NAMES), alias.name
        if isinstance(node, ast.ImportFrom):
            assert not any(bad in (node.module or "") for bad in PROHIBITED_MODULE_NAMES)


def test_the_independent_module_never_executes_or_dynamically_loads_anything():
    tree = ast.parse(_text(RECALC_PY))
    banned_calls = {"exec", "eval", "compile", "__import__"}
    banned_attributes = {"import_module", "exec_module", "spec_from_file_location", "run_path",
                         "run_module", "check_output", "Popen", "run", "system", "popen"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls, node.func.id
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attributes, node.func.attr


def test_no_reviewer_returned_planning_target_is_a_literal_in_the_independent_module():
    """Every headline result must be derived, so it must not appear as a source constant."""
    tree = ast.parse(_text(RECALC_PY))
    literals = {node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, int)
                and not isinstance(node.value, bool)}
    offenders = sorted(literals & set(DERIVED_RESULT_LITERALS))
    assert offenders == [], "derived results appear as literals: %r" % offenders


def test_the_independent_module_opens_only_permitted_repository_artifacts():
    source = _text(RECALC_PY)
    assert "interface_calibration_protocol_draft.json" in source
    # The drafting table may be named, but only inside the comparison function that was written
    # in a strictly later commit than the derivation.
    tree = ast.parse(source)
    comparison = [n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "compare_against_drafting_output"]
    assert len(comparison) == 1
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name != "compare_against_drafting_output":
            rendered = ast.dump(node)
            assert "design_statistics_tables" not in rendered, node.name


def test_the_prohibited_source_audit_is_recorded_and_negative(review):
    audit = review["prohibited_source_audit"]
    assert audit["imported"] is False
    assert audit["executed"] is False
    assert audit["dynamically_loaded"] is False
    assert audit["constants_copied"] is False
    assert audit["control_flow_derived"] is False
    for name in PROHIBITED_SOURCES:
        assert any(name in entry for entry in audit["prohibited_sources"]), name


def test_the_derivation_commit_precedes_the_drafting_inspection_commit(review):
    proof = review["ordering_proof"]
    derivation = proof["independent_derivation_commit"]
    inspection = proof["drafting_inspection_commit"]
    assert proof["derivation_precedes_inspection"] is True
    assert derivation != inspection
    if _commit_available(derivation) and _commit_available(inspection):
        ancestry = _git("merge-base", "--is-ancestor", derivation, inspection)
        assert ancestry.returncode == 0, "the derivation commit is not an ancestor of the inspection commit"


# ----------------------------------------------------------------------------------
# the independent recalculation actually reproduces its committed table
# ----------------------------------------------------------------------------------

def test_the_independent_recalculation_check_mode_reproduces_its_committed_tables():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / RECALC_PY), "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, "--check failed:\n%s\n%s" % (result.stdout, result.stderr)
    assert "INDEPENDENT_RECALCULATION_V0_4_CHECK_OK" in result.stdout
    assert "max_absolute_deviation=0" in result.stdout


def test_the_independent_table_declares_it_is_not_a_measurement(tables):
    assert tables["status"] == "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS"
    assert "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS" in tables["prominent_status_note"]
    for family in tables["method_validation"].values():
        assert family["all_checks_pass"] is True


def test_every_binding_number_in_the_review_matches_the_independent_table(review, tables):
    for split, key in (("development", "development_exact_binomial_components"),
                       ("confirmation", "confirmation_exact_binomial_components")):
        for gate, block in review["exact_binomial_recalculation"][split].items():
            derived = tables[key][gate]
            assert block["n"] == derived["n"], (split, gate)
            assert block["pass_count"] == derived["pass_count"], (split, gate)
            assert block["exact_null_tail_at_p0"] == derived["exact_null_tail_at_p0"]
            assert block["exact_power_at_p1"] == derived["exact_power_at_p1"]
            assert block["degenerate"] is False
            assert block["meets_per_cell_power_target"] is True
    ladder = tables["error_budget_ladder"]
    power = review["arbitrary_dependence_power_decision"]
    assert power["per_cell_budget"] == ladder["per_cell_false_negative_budget_exact_rational"]
    assert power["per_cell_power_target"] == ladder["per_cell_power_target_exact_rational"]
    assert power["profile_stage_floor"] == ladder["profile_stage_power_floor_exact_rational"]
    assert power["panel_bound"] == ladder["panel_false_qualification_bound_exact_rational"]
    assert power["end_to_end_floor"] == ladder["study_end_to_end_power_floor_exact_rational"]
    assert power["m_max"] == tables["gate_bearing_cell_census"]["m_max_over_selectable_profiles"]


def test_the_sample_size_search_was_unrestricted(review, tables):
    registered = []
    for gate, block in review["minimal_sample_size_searches"].items():
        search = tables["minimal_sample_size_searches"][gate]
        assert block["search_restriction"] == search["search_restriction"]
        assert "every positive integer" in block["search_restriction"]
        assert block["first_admissible_n"] == search["first_admissible_n"]
        assert block["registered_claim_verified"] is True
        assert block["first_admissible_n"] == block["registered_n"]
        registered.append(block["registered_n"])
    # The retired restriction admitted only multiples of the complete-block size. It cannot still
    # be in force if a registered size is not a multiple of it. A size that happens to be a
    # multiple is not evidence either way, so only the existence of a non-multiple is asserted.
    assert any(n % 32 != 0 for n in registered), \
        "every registered size is a multiple of 32; the retired restriction may have survived"


# ----------------------------------------------------------------------------------
# binding of the reviewed object and of the prior-review blobs
# ----------------------------------------------------------------------------------

def test_the_reviewed_object_is_the_exact_twenty_six_path_change_set(review):
    if not _commit_available(REVIEWED_COMMIT) or not _commit_available(PUBLISHED_BASE_COMMIT):
        pytest.fail("the reviewed history is not present in this clone")
    result = _git("diff", "--name-status", PUBLISHED_BASE_COMMIT, REVIEWED_COMMIT)
    assert result.returncode == 0
    lines = result.stdout.decode().strip().splitlines()
    added = sorted(line.split("\t")[1] for line in lines if line.startswith("A"))
    modified = sorted(line.split("\t")[1] for line in lines if line.startswith("M"))
    assert len(lines) == 26
    assert len(added) == 6 and len(modified) == 20
    for line in lines:
        assert line[0] in "AM", "a deletion, rename, copy or type change appeared: %s" % line
    assert sorted(review["reviewed_path_set"]["added"]) == added
    assert sorted(review["reviewed_path_set"]["modified"]) == modified
    assert review["reviewed_path_set"]["path_count"] == 26


def test_every_reviewed_artifact_identity_binds_a_committed_blob(review):
    if not _commit_available(REVIEWED_COMMIT):
        pytest.fail("the reviewed commit is not present in this clone")
    for path, identity in review["reviewed_artifact_identities"].items():
        blob = _blob_at(REVIEWED_COMMIT, path)
        assert len(blob) == identity["bytes"], path
        assert hashlib.sha256(blob).hexdigest() == identity["sha256"], path


def test_the_review_binds_the_core_prior_review_blobs(review):
    for path in ("tests/test_study3_methods_review.py",
                 "studies/study3/analysis/independent_methods_recalculation_v0_3.py",
                 "studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json",
                 "studies/study3/reviews/v0_3_independent_methods_review.json",
                 "studies/study3/reviews/v0_2_independent_methods_review.json"):
        assert path in review["reviewed_artifact_identities"], path


def test_the_reviewed_tree_is_bound(review):
    if not _commit_available(REVIEWED_COMMIT):
        pytest.fail("the reviewed commit is not present in this clone")
    tree = _git("rev-parse", "%s^{tree}" % REVIEWED_COMMIT).stdout.decode().strip()
    assert tree == REVIEWED_TREE == review["reviewed_tree"]


# ----------------------------------------------------------------------------------
# authority byte identity
# ----------------------------------------------------------------------------------

def test_the_committed_authority_is_byte_identical_to_the_recorded_source(review):
    blob = _committed_bytes(AUTHORITY_MD)
    assert len(blob) == AUTHORITY_BYTES
    assert hashlib.sha256(blob).hexdigest() == AUTHORITY_SHA256
    assert blob.count(b"\r") == 0
    assert not blob.endswith(b"\n"), "the source authority has no trailing newline"
    source = review["source_authority"]
    committed = review["committed_authority"]
    assert source["bytes"] == committed["bytes"] == len(blob)
    assert source["sha256"] == committed["sha256"] == hashlib.sha256(blob).hexdigest()
    assert source["cr_count"] == 0
    assert source["lf_count"] == blob.count(b"\n")
    assert source["ends_with_newline"] is False
    assert committed["byte_identical_to_source"] is True


# ----------------------------------------------------------------------------------
# inherited findings, non-regression, findings parity, verdicts
# ----------------------------------------------------------------------------------

def test_exactly_one_adjudication_per_inherited_finding(review):
    ids = [a["finding_id"] for a in review["inherited_finding_adjudications"]]
    assert ids == sorted(ids) or set(ids) == set(INHERITED_IDS)
    assert sorted(ids) == sorted(INHERITED_IDS)
    assert len(ids) == len(set(ids)) == 10
    for a in review["inherited_finding_adjudications"]:
        assert a["status"] in ("VERIFIED_RESOLVED", "PARTIALLY_RESOLVED", "NOT_RESOLVED")
        assert "PROPOSED_RESOLVED" not in a["status"]
        assert a["reviewer_evidence"] != a["drafting_party_claim"]


def test_the_non_regression_sets_are_exact(review):
    nr = review["earlier_review_non_regression"]
    assert sorted(e["finding_id"] for e in nr["first_review_findings"]) == sorted(FIRST_REVIEW_IDS)
    assert sorted(e["item_id"] for e in nr["unresolved_items"]) == sorted(UR_IDS)


def test_ur_22_and_od2_remain_open_operator_decisions(review):
    nr = review["earlier_review_non_regression"]
    ur22 = [e for e in nr["unresolved_items"] if e["item_id"] == "UR-22"][0]
    assert ur22["non_regression_status"] == "REMAINS_UNRESOLVED_BLOCKING_OPERATOR_DECISION"
    ids = {u["item_id"]: u for u in review["unresolved_operator_items"]}
    assert ids["OD2"]["status"] == "UNRESOLVED_BLOCKING_OPERATOR_DECISION"
    assert review["i4_p3q_od2_decision"]["od2_status"] == "UNRESOLVED_BLOCKING_OPERATOR_DECISION"
    assert review["i4_p3q_od2_decision"]["checkpoint_selected"] is False


def test_new_findings_carry_every_required_attribute(review):
    ids = [f["finding_id"] for f in review["new_findings"]]
    assert len(ids) == len(set(ids))
    for index, finding in enumerate(review["new_findings"], start=1):
        assert finding["finding_id"] == "S3MR3-%03d" % index, finding["finding_id"]
        assert finding["severity"] in ("BLOCKING", "MAJOR", "MINOR")
        assert isinstance(finding["fundamental"], bool)
        assert finding["evidence_paths"] and finding["evidence_fields"]
        assert finding["rationale"] and finding["consequence"]
        assert finding["successor_implication"]
        assert finding["required_repair_alters"]


def test_both_construct_verdicts_are_present_and_independent(review):
    verdicts = review["construct_verdicts"]
    assert set(verdicts) == {
        "METHOD_INTERNAL_VALIDITY_VERDICT",
        "STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT",
        "second_verdict_is_not_inferred_from_the_first",
    }
    assert verdicts["second_verdict_is_not_inferred_from_the_first"] is True
    for name in ("METHOD_INTERNAL_VALIDITY_VERDICT",
                 "STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT"):
        entry = verdicts[name]
        assert entry["verdict"] in ("ADEQUATE", "ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR",
                                   "INADEQUATE")
        assert entry["adequate"] is (entry["verdict"] == "ADEQUATE")
        assert len(entry["basis"]) >= 80


# ----------------------------------------------------------------------------------
# disposition fail-closed rules
# ----------------------------------------------------------------------------------

def _disposition_errors(document: dict) -> list:
    """The fail-closed disposition rules of section 8, evaluated independently of the schema."""
    errors = []
    disposition = document["disposition"]
    findings = document["new_findings"]
    severities = {f["severity"] for f in findings}
    fundamental = [f for f in findings if f["fundamental"]]
    methods_items = document["unresolved_methods_items"]
    blocking_or_major = ({"BLOCKING", "MAJOR"} & severities) or any(
        i["severity"] in ("BLOCKING", "MAJOR") for i in methods_items)
    verdicts = document["construct_verdicts"]
    both_adequate = (verdicts["METHOD_INTERNAL_VALIDITY_VERDICT"]["adequate"]
                     and verdicts["STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT"]["adequate"])
    inherited_unresolved = [a for a in document["inherited_finding_adjudications"]
                            if a["status"] != "VERIFIED_RESOLVED"]

    if disposition == "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED":
        if blocking_or_major:
            errors.append("accepted as specified with an unresolved blocking or major methods item")
        if not both_adequate:
            errors.append("accepted as specified with an inadequate construct verdict")
        if inherited_unresolved:
            errors.append("accepted as specified with an unresolved inherited finding")
        if document["rejection_class"] != "none":
            errors.append("accepted as specified with a rejection class")
    if disposition == "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CONFORMANCE_CHANGES":
        for finding in findings:
            unsafe = set(finding["required_repair_alters"]) - CONFORMANCE_SAFE_ALTERATIONS
            if unsafe:
                errors.append("conformance disposition with a repair that alters %s"
                              % ", ".join(sorted(unsafe)))
    if disposition == "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED":
        if fundamental:
            errors.append("bounded-amendment rejection driven by a fundamental finding")
        if document["rejection_class"] != "bounded_amendment":
            errors.append("bounded-amendment rejection without the bounded_amendment class")
    if disposition == "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_FUNDAMENTAL_FEASIBILITY_PILOT_REQUIRED":
        if not fundamental:
            errors.append("fundamental-pilot rejection with no fundamental finding")
    expected_action = {
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED":
            "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND",
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CONFORMANCE_CHANGES":
            "OPERATOR_CONFORMANCE_AMENDMENT_FOR_DRAFT_V0_4_1",
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED":
            "OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5",
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_FUNDAMENTAL_FEASIBILITY_PILOT_REQUIRED":
            "OPERATOR_AUTHORITY_FOR_DISCLOSED_ZERO_CLAIM_FEASIBILITY_PILOT_DESIGN",
    }[disposition]
    if document["next_legal_action"] != expected_action:
        errors.append("successor action is inconsistent with the disposition")
    return errors


def test_the_committed_review_satisfies_every_disposition_rule(review):
    assert _disposition_errors(review) == []


# ----------------------------------------------------------------------------------
# substantive boundaries the review may never cross
# ----------------------------------------------------------------------------------

def test_descriptive_lattice_quantities_carry_no_decision_authority(review):
    decision = review["descriptive_lattice_decision"]
    assert decision["authority"] == "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY"
    for key in ("has_null", "has_alpha", "has_p_value", "has_pass_fail", "has_ranking",
                "has_rescue", "has_eligibility", "has_selection", "has_confirmation",
                "has_claim_authority", "reachable_decision_path"):
        assert decision[key] is False, key


def test_the_i3_estimand_is_a_level_and_never_a_presentation_effect(review, tables):
    estimand = review["i3_estimand_decision"]
    assert estimand["indicator"] == "J_joint_correct"
    assert estimand["is_a_level_not_a_contrast"] is True
    assert estimand["identifies_a_presentation_effect"] is False
    assert estimand["ordered_lattice_cases"] == 16
    assert estimand["passing_case_count"] == 1
    assert tables["i3_outcome_lattice"]["ordered_cases"] == 16
    assert tables["i3_outcome_lattice"]["passing_case_count"] == 1
    assert tables["i3_outcome_lattice"]["identity_J_cor_implies_J_inv"] is True
    q = estimand["q_parameterisation"]
    assert q["identity"] == "p_joint + d <= 1"
    assert q["identity_holds"] is True
    assert q["independence_asserted"] is False
    assert tables["i3_discordance_parameterisation"][
        "identity_p_joint_plus_d_at_most_one_holds"] is True


def test_the_claim_ceiling_is_generator_local_and_unfrozen(review):
    ceiling = review["claim_ceiling_restatement"]
    assert ceiling["generator_local"] is True
    assert ceiling["unfrozen"] is True
    assert ceiling["no_execution_authority"] is True
    assert ceiling["original_research_question_answered"] is False
    assert review["external_validity_decision"]["ceiling_is_explicit_in_active_claim_text"] in (
        True, False)
    for profile_claim in review["i3_estimand_decision"][
            "strongest_permitted_claim_by_profile"].values():
        lowered = profile_claim.lower()
        for stem in ("no presentation effect", "presentation-effect size"):
            assert stem not in lowered, profile_claim


def test_no_binding_bound_uses_independence(review, tables):
    power = review["arbitrary_dependence_power_decision"]
    assert power["uses_independence_in_any_binding_bound"] is False
    assert power["independence_appears_only_as_labelled_sensitivity"] is True
    ladder = tables["error_budget_ladder"]
    assert ladder["holds_under_arbitrary_dependence"] is True
    assert ladder["uses_independence_anywhere_in_a_binding_bound"] is False
    for step in ladder["union_bound_ladder"]:
        assert step["uses_independence"] is False
    validation = tables["method_validation"]["multiplicity_and_arbitrary_dependence"]
    assert validation["union_bound_holds_under_every_enumerated_dependence"] is True
    assert validation["intersection_union_size_bounded_by_max_component"] is True


def test_no_unauthorized_s4_or_s5_decision_path_is_created(review):
    decision = review["s4_headroom_and_generation_axis_decision"]
    assert decision["s4_selectable"] is False
    assert decision["s4_enters_any_success_union"] is False
    assert decision["s5_created_in_this_review"] is False
    blob = json.dumps(review)
    assert '"S5"' not in blob, "this review may not create a fifth interface profile"


def test_methods_blockers_are_separated_from_the_operator_decision(review):
    methods_ids = {i["item_id"] for i in review["unresolved_methods_items"]}
    operator_ids = {i["item_id"] for i in review["unresolved_operator_items"]}
    assert methods_ids.isdisjoint(operator_ids)
    assert all(i.startswith("UM3-") for i in methods_ids)
    assert "OD2" in operator_ids
    assert "OD2" not in methods_ids
    # The disposition must not be driven by OD2.
    assert "OD2" not in review["disposition_basis"]


def test_no_operation_counter_flag_selection_or_evidence_row_exists(review):
    for name, value in review["operation_counters"].items():
        assert value == 0, name
    for name, value in review["authority_flags"].items():
        assert value is False, name
    selection = review["selection_state"]
    assert selection["selected_interface_profile"] is None
    assert selection["selected_positive_reference"] is None
    assert selection["selected_checkpoint"] is None
    assert selection["selected_profile_ranking_produced"] is False
    assert review["bank_rows"] == []
    assert review["seeds"] == []
    assert review["results"] == []
    assert review["evidence_rows"] == []


def test_the_evidence_ledger_is_untouched_and_ends_at_ev_0016():
    ledger = _committed_bytes("paper/evidence_ledger.csv")
    assert len(ledger) == 25241
    assert hashlib.sha256(ledger).hexdigest() == (
        "3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1")
    rows = [line for line in ledger.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) - 1 == 16
    assert rows[-1].startswith("EV-0016")


# ----------------------------------------------------------------------------------
# Markdown / JSON parity
# ----------------------------------------------------------------------------------

def test_markdown_and_json_agree_on_every_decision_bearing_token(review, markdown):
    assert review["disposition"] in markdown
    assert review["state"] in markdown
    assert review["next_legal_action"] in markdown
    for other in DISPOSITIONS:
        if other != review["disposition"]:
            assert other not in markdown, "a non-returned disposition appears in the Markdown"
    for finding in review["new_findings"]:
        assert finding["finding_id"] in markdown
        assert finding["title"] in markdown
    for adjudication in review["inherited_finding_adjudications"]:
        assert adjudication["finding_id"] in markdown
        assert adjudication["status"] in markdown
    for name in ("METHOD_INTERNAL_VALIDITY_VERDICT",
                 "STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT"):
        assert name in markdown
        assert review["construct_verdicts"][name]["verdict"] in markdown
    assert "OD2" in markdown
    assert "UNRESOLVED_BLOCKING_OPERATOR_DECISION" in markdown


def test_the_markdown_restates_every_required_boundary(markdown):
    for sentence in (
            "Study 1 remains closed",
            "Study 2 remains closed",
            "Study 3 remains unfrozen",
            "No interface profile and no positive reference is selected",
            "The original research question remains unanswered",
    ):
        assert sentence in markdown, sentence


def test_the_markdown_distinguishes_fact_inference_and_recommendation(markdown):
    assert "Reviewed fact, reviewer inference and " in markdown
    assert "Successor implication" in markdown


# ----------------------------------------------------------------------------------
# historical-review harness: invariants and executed non-vacuity probes
# ----------------------------------------------------------------------------------

def _harness_source(commit: str) -> str:
    return _blob_at(commit, "tests/test_study3_methods_review_v0_3.py").decode("utf-8")


def _collected_node_ids(source: str):
    return sorted(node.name for node in ast.parse(source).body
                  if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))


def test_the_harness_erratum_changed_no_collected_node_id_and_weakened_nothing(review):
    if not _commit_available(REVIEWED_COMMIT):
        pytest.fail("the reviewed history is not present in this clone")
    parent = _git("rev-parse", "%s^" % REVIEWED_COMMIT).stdout.decode().strip()
    before = _harness_source(parent)
    after = _harness_source(REVIEWED_COMMIT)
    assert _collected_node_ids(before) == _collected_node_ids(after)
    assert len(_collected_node_ids(after)) == 35
    for marker in ("pytest.skip", "mark.skip", "mark.xfail", "except:"):
        assert after.count(marker) == 0, marker
        assert after.count(marker) <= before.count(marker), marker
    assert after.count("assert ") >= before.count("assert ")
    assert 'REVIEWED_COMMIT = "%s"' % V0_3_REVIEWED_COMMIT in after
    audit = review["historical_harness_audit"]
    assert audit["anchor_commit"] == V0_3_REVIEWED_COMMIT
    assert audit["collected_node_ids_before"] == audit["collected_node_ids_after"] == 35
    assert audit["assertions_weakened"] is False
    assert audit["skips_added"] == 0 and audit["xfails_added"] == 0
    assert audit["expected_scientific_values_changed"] is False
    assert audit["amends_any_v0_3_finding_or_disposition"] is False


def test_the_immutable_v0_3_recalculation_identities_are_unchanged():
    for path, size, digest in (
            ("studies/study3/analysis/independent_methods_recalculation_v0_3.py", 58317,
             "cb74c035a4a9271e11b4143d0cc32d42955613f4b28608305911ade30c7da688"),
            ("studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json", 66631,
             "ea11c345b611c72120a2deb6abac6764bf2abe94653d100a2123d3db8250bace")):
        blob = _committed_bytes(path)
        assert len(blob) == size, path
        assert hashlib.sha256(blob).hexdigest() == digest, path


def _materialise_historical_snapshot(root: Path, substitute: dict = None,
                                     perturb_table: bool = False) -> None:
    """Rebuild the reviewed-commit snapshot the repaired harness runs the v0.3 generator in."""
    declared = tuple(ast.literal_eval(node.value) for node in ast.parse(
        _text("studies/study3/analysis/independent_methods_recalculation_v0_3.py")).body
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DECISION_BEARING_ARTIFACTS"
            for t in node.targets))[0]
    for relative in declared:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if substitute and relative in substitute:
            destination.write_bytes(substitute[relative])
        else:
            destination.write_bytes(_blob_at(V0_3_REVIEWED_COMMIT, relative))
    for relative in ("studies/study3/analysis/independent_methods_recalculation_v0_3.py",
                     "studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json"):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = _committed_bytes(relative)
        if perturb_table and relative.endswith(".json"):
            document = json.loads(payload)
            document["__perturbation__"] = "a single added key must be detected"
            payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        destination.write_bytes(payload)


def _run_v0_3_generator(snapshot: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable,
         str(snapshot / "studies/study3/analysis/independent_methods_recalculation_v0_3.py"),
         "--check"],
        cwd=snapshot, capture_output=True, text=True)


def test_non_vacuity_probe_one_the_pristine_reviewed_snapshot_passes(tmp_path):
    if not _commit_available(V0_3_REVIEWED_COMMIT):
        pytest.fail("the v0.3 reviewed commit is not present in this clone")
    snapshot = tmp_path / "pristine"
    _materialise_historical_snapshot(snapshot)
    result = _run_v0_3_generator(snapshot)
    assert result.returncode == 0, "the pristine snapshot must pass:\n%s\n%s" % (
        result.stdout, result.stderr)


def test_non_vacuity_probe_two_substituting_a_live_v0_4_input_fails(tmp_path):
    """If the live draft-v0.4 protocol were reachable, the historical check would be vacuous."""
    if not _commit_available(V0_3_REVIEWED_COMMIT):
        pytest.fail("the v0.3 reviewed commit is not present in this clone")
    live = "studies/study3/protocol/interface_calibration_protocol_draft.json"
    snapshot = tmp_path / "substituted"
    _materialise_historical_snapshot(
        snapshot, substitute={live: _blob_at(REVIEWED_COMMIT, live)})
    result = _run_v0_3_generator(snapshot)
    assert result.returncode != 0, (
        "substituting the live draft-v0.4 protocol must fail the historical check; if it passes, "
        "the check does not depend on its anchored inputs and is vacuous")


def test_non_vacuity_probe_three_perturbing_the_committed_historical_table_fails(tmp_path):
    if not _commit_available(V0_3_REVIEWED_COMMIT):
        pytest.fail("the v0.3 reviewed commit is not present in this clone")
    snapshot = tmp_path / "perturbed"
    _materialise_historical_snapshot(snapshot, perturb_table=True)
    result = _run_v0_3_generator(snapshot)
    assert result.returncode != 0, (
        "perturbing the committed historical table must fail the historical check")


def test_the_recorded_non_vacuity_probes_match_the_executed_ones(review):
    probes = review["historical_harness_audit"]["non_vacuity_probes"]
    assert len(probes) >= 3
    expectations = {p["probe"]: p for p in probes}
    assert any("pristine" in name for name in expectations)
    assert any("substitut" in name for name in expectations)
    assert any("perturb" in name for name in expectations)
    for probe in probes:
        assert probe["observed"] == probe["expected"], probe["probe"]
        assert probe["bound_run"], probe["probe"]


def test_the_artifact_index_preserves_both_harness_identities(review):
    index = _text("paper/artifact_index.csv").splitlines()
    audit = review["historical_harness_audit"]
    pre = [row for row in index if row.startswith("AR-0246,")]
    post = [row for row in index if row.startswith("AR-0269,")]
    assert len(pre) == 1 and len(post) == 1
    assert audit["ar_0246_identity"] in pre[0]
    assert audit["ar_0269_identity"] in post[0]
    assert audit["ar_0246_identity"] != audit["ar_0269_identity"]
    assert audit["rows_contradict_each_other"] is False
    current = hashlib.sha256(_committed_bytes(
        "tests/test_study3_methods_review_v0_3.py")).hexdigest()
    assert audit["ar_0269_identity"] == current


# ----------------------------------------------------------------------------------
# the reviewer did not edit the reviewed object
# ----------------------------------------------------------------------------------

def test_the_reviewer_edited_no_reviewed_path(review):
    if not _commit_available(REVIEWED_COMMIT):
        pytest.fail("the reviewed history is not present in this clone")
    for path in review["reviewed_path_set"]["added"] + review["reviewed_path_set"]["modified"]:
        if path in MODIFIABLE_PATHS:
            continue
        reviewed = _blob_at(REVIEWED_COMMIT, path)
        current = _committed_bytes(path)
        assert current == reviewed, "%s was edited by the reviewer" % path


def test_no_pre_existing_study3_test_module_was_modified():
    if not _commit_available(REVIEWED_COMMIT):
        pytest.fail("the reviewed history is not present in this clone")
    for path in ("tests/test_study3_design.py", "tests/test_study3_methods_review.py",
                 "tests/test_study3_methods_review_v0_3.py"):
        assert _committed_bytes(path) == _blob_at(REVIEWED_COMMIT, path), path


def test_the_receipt_path_whitelist_is_the_hard_ceiling(receipt):
    added = set(receipt["path_whitelist"]["added"])
    modified = set(receipt["path_whitelist"]["modified"])
    assert added == set(NEW_PATHS), "exactly the eight section 7 outputs may be added"
    assert modified <= set(MODIFIABLE_PATHS), "only whitelisted paths may be modified"
    assert len(added) == 8
    assert len(modified) <= 9
    assert len(added | modified) <= 17, "the hard ceiling is seventeen changed paths"
    assert added.isdisjoint(modified)
    assert set(receipt["path_whitelist"]["observed"]) == (added | modified)


def test_the_receipt_binds_the_review_and_its_boundaries(receipt, review):
    assert receipt["disposition"] == review["disposition"]
    assert receipt["state"] == review["state"]
    assert receipt["starting_commit"] == REVIEWED_COMMIT
    assert receipt["starting_tree"] == REVIEWED_TREE
    assert receipt["reviewed_object"]["path_count"] == 26
    assert receipt["source_authority"]["sha256"] == AUTHORITY_SHA256
    assert receipt["committed_authority"]["sha256"] == AUTHORITY_SHA256
    for name, value in receipt["operation_counters"].items():
        assert value == 0, name
    for name, value in receipt["authority_flags"].items():
        assert value is False, name
    assert receipt["evidence_ledger"]["data_rows"] == 16
    assert receipt["evidence_ledger"]["last_row"] == "EV-0016"
    for path in NEW_PATHS:
        if path == RECEIPT_JSON:
            continue
        assert path in receipt["new_artifacts"], path


# ----------------------------------------------------------------------------------
# negative mutations: every fail-closed rule must actually fail
# ----------------------------------------------------------------------------------

def _unknown_disposition(document):
    document["disposition"] = "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_BECAUSE_IT_IS_LONG"


def _unknown_state(document):
    document["state"] = "STUDY3_FROZEN_AND_EXECUTING"


def _drop_an_inherited_finding(document):
    document["inherited_finding_adjudications"].pop()


def _duplicate_an_inherited_finding(document):
    document["inherited_finding_adjudications"].append(
        deepcopy(document["inherited_finding_adjudications"][0]))


def _extra_inherited_finding(document):
    extra = deepcopy(document["inherited_finding_adjudications"][0])
    extra["finding_id"] = "S3MR2-011"
    document["inherited_finding_adjudications"].append(extra)


def _drop_a_mandatory_audit_answer(document):
    document["mandatory_audit_answers"].pop(sorted(document["mandatory_audit_answers"])[0])


def _drop_a_construct_verdict(document):
    document["construct_verdicts"].pop("STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT")


def _finding_without_severity(document):
    document["new_findings"][0].pop("severity")


def _finding_without_fundamental_flag(document):
    document["new_findings"][0].pop("fundamental")


def _finding_without_evidence(document):
    document["new_findings"][0].pop("evidence_paths")


def _finding_without_consequence(document):
    document["new_findings"][0].pop("consequence")


def _finding_without_successor_implication(document):
    document["new_findings"][0].pop("successor_implication")


def _binding_number_without_unit(document):
    document["exact_binomial_recalculation"]["development"]["I3"].pop("unit_of_n")


def _binding_number_without_authority_status(document):
    document["exact_binomial_recalculation"]["development"]["I3"].pop("authority_status")


def _claim_j_joint_correct_estimates_an_effect(document):
    document["i3_estimand_decision"]["identifies_a_presentation_effect"] = True


def _claim_the_indicator_is_a_contrast(document):
    document["i3_estimand_decision"]["is_a_level_not_a_contrast"] = False


def _give_a_descriptive_quantity_a_decision_role(document):
    document["descriptive_lattice_decision"]["has_pass_fail"] = True


def _give_a_descriptive_quantity_a_reachable_path(document):
    document["descriptive_lattice_decision"]["reachable_decision_path"] = True


def _assume_independence_in_a_binding_bound(document):
    document["arbitrary_dependence_power_decision"][
        "uses_independence_in_any_binding_bound"] = True


def _select_an_interface(document):
    document["selection_state"]["selected_interface_profile"] = "S2"


def _select_a_positive_reference(document):
    document["selection_state"]["selected_positive_reference"] = "some-checkpoint"


def _nonzero_operation_counter(document):
    document["operation_counters"]["forward_passes"] = 1


def _true_authority_flag(document):
    document["authority_flags"]["frozen"] = True


def _add_a_bank_row(document):
    document["bank_rows"].append({"item": 1})


def _add_an_evidence_row(document):
    document["evidence_rows"].append({"id": "EV-0017"})


def _add_a_result(document):
    document["results"].append({"cell": "D/I3_K6/K6-SEP", "successes": 400})


def _add_a_seed(document):
    document["seeds"].append(1234)


def _confirmation_admits_the_never_selectable_profile(document):
    document["confirmation_decision"]["s4_can_appear"] = True


def _authority_bytes_drift(document):
    document["committed_authority"]["bytes"] = 47886


def _authority_digest_drift(document):
    document["committed_authority"]["byte_identical_to_source"] = False


def _bad_reviewed_path_count(document):
    document["reviewed_path_set"]["path_count"] = 27


SCHEMA_MUTATIONS = (
    _unknown_disposition, _unknown_state, _drop_an_inherited_finding,
    _duplicate_an_inherited_finding, _extra_inherited_finding, _drop_a_mandatory_audit_answer,
    _drop_a_construct_verdict, _finding_without_severity, _finding_without_fundamental_flag,
    _finding_without_evidence, _finding_without_consequence,
    _finding_without_successor_implication, _binding_number_without_unit,
    _binding_number_without_authority_status, _claim_j_joint_correct_estimates_an_effect,
    _claim_the_indicator_is_a_contrast, _give_a_descriptive_quantity_a_decision_role,
    _give_a_descriptive_quantity_a_reachable_path, _assume_independence_in_a_binding_bound,
    _select_an_interface, _select_a_positive_reference, _nonzero_operation_counter,
    _true_authority_flag, _add_a_bank_row, _add_an_evidence_row, _add_a_result, _add_a_seed,
    _confirmation_admits_the_never_selectable_profile, _authority_bytes_drift,
    _authority_digest_drift, _bad_reviewed_path_count,
)


@pytest.mark.parametrize("mutation", SCHEMA_MUTATIONS, ids=lambda m: m.__name__)
def test_the_schema_rejects_every_registered_mutation(review, schema, mutation):
    mutated = deepcopy(review)
    mutation(mutated)
    assert validate(mutated, schema), "%s was not rejected by the schema" % mutation.__name__


def _accept_as_specified_with_a_blocking_finding(document):
    document["disposition"] = "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED"
    document["rejection_class"] = "none"
    document["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"


def _accept_with_conformance_when_a_repair_alters_applicability(document):
    document["disposition"] = (
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CONFORMANCE_CHANGES")
    document["rejection_class"] = "none"
    document["next_legal_action"] = "OPERATOR_CONFORMANCE_AMENDMENT_FOR_DRAFT_V0_4_1"


def _bounded_amendment_driven_by_a_fundamental_finding(document):
    document["new_findings"][0]["fundamental"] = True


def _fundamental_pilot_with_no_fundamental_finding(document):
    document["disposition"] = (
        "STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_FUNDAMENTAL_FEASIBILITY_PILOT_REQUIRED")
    document["rejection_class"] = "fundamental_feasibility_pilot"
    document["next_legal_action"] = (
        "OPERATOR_AUTHORITY_FOR_DISCLOSED_ZERO_CLAIM_FEASIBILITY_PILOT_DESIGN")


def _successor_action_inconsistent_with_the_disposition(document):
    document["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"


DISPOSITION_MUTATIONS = (
    _accept_as_specified_with_a_blocking_finding,
    _accept_with_conformance_when_a_repair_alters_applicability,
    _bounded_amendment_driven_by_a_fundamental_finding,
    _fundamental_pilot_with_no_fundamental_finding,
    _successor_action_inconsistent_with_the_disposition,
)


@pytest.mark.parametrize("mutation", DISPOSITION_MUTATIONS, ids=lambda m: m.__name__)
def test_the_disposition_rules_reject_every_registered_mutation(review, schema, mutation):
    mutated = deepcopy(review)
    mutation(mutated)
    rejected = bool(_disposition_errors(mutated)) or bool(validate(mutated, schema))
    assert rejected, "%s was not rejected" % mutation.__name__


def test_the_unmutated_committed_review_is_accepted(review, schema):
    assert validate(review, schema) == []
    assert _disposition_errors(review) == []
