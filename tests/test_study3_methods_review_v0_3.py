"""Committed validation for the SECOND independent methods review of Study 3 draft-v0.3.

This module is the committed, decision-bearing check for the review outputs. It adds no
dependency: the JSON Schema subset used by the committed schema is enforced by a
self-contained validator in this file, and the validator refuses any schema construct it
cannot fully enforce, so a schema keyword can never be silently ignored.

Nothing here executes a model, a tokenizer, a bank, a seed, a split or a network call.
Every assertion is CPU-only and model-free.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

REVIEWED_COMMIT = "2b36f5321d830ea6f70fff2b7bbca3cb93394046"
REVIEWED_TREE = "98d71cb35cca7b55d8f96f131064a5b9654dd3c7"

REVIEW_JSON = "studies/study3/reviews/v0_3_independent_methods_review.json"
REVIEW_SCHEMA = "studies/study3/reviews/v0_3_independent_methods_review.schema.json"
REVIEW_MD = "studies/study3/reviews/v0_3_independent_methods_review.md"
RECALC_PY = "studies/study3/analysis/independent_methods_recalculation_v0_3.py"
RECALC_JSON = "studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json"
AUTHORITY_MD = "studies/study3/prompts/study3_v0_3_independent_methods_review_authority.md"
RECEIPT_JSON = "studies/study3/methods_review_receipt_v0_3.json"

PROHIBITED_SOURCES = (
    "studies/study3/analysis/design_statistics.py",
    "studies/study3/analysis/independent_methods_recalculation.py",
)

# Mutable, reviewed inputs that the immutable v0.3 generator reads. The historical check
# materialises every one of them from REVIEWED_COMMIT, so it never consumes current-draft
# bytes. This list is cross-checked against the generator's own declaration below.
HISTORICAL_GENERATOR_INPUTS = (
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
    "studies/study3/analysis/independent_methods_review_packet_v0_3.md",
    "studies/study3/reviews/v0_3_operator_amendment.json",
    "studies/study3/reviews/v0_3_operator_amendment.md",
)

# Current-draft bytes that must never be reachable from the isolated historical snapshot.
CURRENT_DRAFT_BYTES_FORBIDDEN_IN_SNAPSHOT = (
    "studies/study3/analysis/design_statistics.py",
    "studies/study3/analysis/design_statistics_tables.json",
    "studies/study3/analysis/independent_methods_review_packet_v0_4.md",
    "studies/study3/design_receipt_v0_4.json",
    "studies/study3/reviews/v0_4_operator_amendment.json",
    "studies/study3/reviews/v0_4_operator_amendment.md",
    "tests/test_study3_design.py",
    "tests/test_study3_methods_review.py",
    "tests/test_study3_methods_review_v0_3.py",
)

INHERITED_IDS = tuple(f"S3MR-{i:03d}" for i in range(1, 21))
UR_IDS = tuple(f"UR-{i:02d}" for i in range(1, 23))

DISPOSITIONS = (
    "STUDY3_V0_3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED",
    "STUDY3_V0_3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES",
    "STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED",
)

STATE = "STUDY3_DRAFT_V0_3_SECOND_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION"

REVIEWED_BLOBS = {
    "studies/study3/analysis/independent_methods_review_packet_v0_3.md":
        (29040, "62016c0f0512b616b5342e0a3be0e578dbeb4c97086b91e3618745e525aaa397"),
    "studies/study3/design_receipt_v0_3.json":
        (26342, "9067313a671a318fbedc75b6c486bb55015dbb337d09690f73fddbd573dc9e27"),
    "studies/study3/prompts/study3_v0_3_design_amendment_authority.md":
        (34682, "de85aeff25e827e49d3e7c60d517b50cc69649d66190995a804ab2bc44308667"),
    "studies/study3/reviews/v0_3_operator_amendment.md":
        (50720, "7d0014ff111974f13dca683e0cebf62f60a6b52e8f40c78bcfb90b3ebd2f7f96"),
    "studies/study3/reviews/v0_3_operator_amendment.json":
        (46502, "29a1b33dde48d6969edea49fcc73e56003d5ebc24233883728a295b9ec265271"),
    "studies/study3/reviews/v0_3_operator_amendment.schema.json":
        (22608, "a7411718527397fb8ea5177032cdcea1274e0fc6a2591b6bb052c50ecdae0edf"),
    "studies/study3/analysis/design_statistics.py":
        (69226, "8e279bbbd7e7322c8d823dc807bcdbc5d6a80c4e3f7e4a9385dd37e9b7eae4c5"),
    "studies/study3/analysis/design_statistics_tables.json":
        (53100, "a185b0145707b59d8c0a7da6438fc2f718f59175d37fdf40b4d38e98c79035c2"),
    "studies/study3/protocol/interface_calibration_protocol_draft.json":
        (206696, "db2d51cce9971e916b3a02a5da0bb1a1e6a1c271bb79162e3c8515836db60a09"),
    "studies/study3/protocol/interface_calibration_protocol_draft.md":
        (97393, "670968eac4ec78f45e6eaaa270a4666957df5c7127dc7e4d7dfe4e71dac41633"),
    "studies/study3/protocol/interface_calibration_protocol.schema.json":
        (140007, "1f15d2434133f24dfd7b1add908c9f5904b83e9317d17cc51c13c430743f4f89"),
    "studies/study3/analysis/study2_to_study3_design_traceability.md":
        (21049, "17037a5ca04354db3bdd489d89653056f99960942e7979fbf8a3ecfba7aee620"),
    "studies/study3/references/methods_sources.md":
        (20916, "7efa77c33c3b8dae406efe4aa3f8b57c644fa4242140d72c1a3ff2528d37ef9a"),
    "studies/study3/references/positive_reference_dossier.md":
        (11734, "f300a4cbad9d809b0d5e878e9de43ddd0eb85bdb6737b0a8a3bbbcc650323e24"),
    "tests/test_study3_design.py":
        (93590, "4b7f831878b2c58e98be13db44af560c4d8a2b31301a168e47c68c4b1250a633"),
    "tests/test_study3_methods_review.py":
        (60781, "331d2a7644ee3256d7a145fa8ba83d0b02dcfd1faa1ed8989b726c1c656509ba"),
}


# ----------------------------------------------------------------------------------
# committed-blob helpers
# ----------------------------------------------------------------------------------

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True)


def _reviewed_commit_available() -> bool:
    return _git("cat-file", "-e", f"{REVIEWED_COMMIT}^{{commit}}").returncode == 0


def _blob_at_reviewed_commit(path: str) -> bytes:
    """Committed bytes of ``path`` at the reviewed commit, never working-tree bytes."""
    result = _git("cat-file", "blob", f"{REVIEWED_COMMIT}:{path}")
    assert result.returncode == 0, f"cannot read {path} at {REVIEWED_COMMIT}: {result.stderr!r}"
    return result.stdout


def _committed_bytes(path: str) -> bytes:
    """Committed bytes of a review output, preferring the index over the working tree.

    The repository is checked out with core.autocrlf on some platforms, so working-tree
    bytes are not authoritative. The index entry is used when available and the file is
    normalised to LF otherwise, which keeps the byte bindings platform-independent.
    """
    listed = _git("ls-files", "-s", "--", path)
    if listed.returncode == 0 and listed.stdout.strip():
        object_id = listed.stdout.split()[1].decode()
        blob = _git("cat-file", "blob", object_id)
        if blob.returncode == 0:
            return blob.stdout
    raw = (REPO_ROOT / path).read_bytes()
    return raw.replace(b"\r\n", b"\n")


def _text(path: str) -> str:
    return _committed_bytes(path).decode("utf-8")


def _json(path: str) -> dict:
    return json.loads(_text(path))


def _declared_decision_bearing_artifacts() -> tuple[str, ...]:
    """Artifacts the immutable v0.3 generator declares it reads, parsed without importing it."""
    tree = ast.parse(_text(RECALC_PY))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DECISION_BEARING_ARTIFACTS"
            for target in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("the v0.3 generator no longer declares DECISION_BEARING_ARTIFACTS")


def _materialise_reviewed_snapshot(root: Path) -> None:
    """Build an isolated tree holding only reviewed-commit inputs and the immutable outputs.

    The generator resolves every path it reads from its own ``__file__``, so placing it under
    ``root`` makes ``root`` its repository. Nothing outside this tree is reachable, which is
    what keeps the historical check independent of the current draft.
    """
    for relative in HISTORICAL_GENERATOR_INPUTS:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_blob_at_reviewed_commit(relative))
    for relative in (RECALC_PY, RECALC_JSON):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_committed_bytes(relative))


@pytest.fixture(scope="module")
def review() -> dict:
    return _json(REVIEW_JSON)


@pytest.fixture(scope="module")
def schema() -> dict:
    return _json(REVIEW_SCHEMA)


@pytest.fixture(scope="module")
def markdown() -> str:
    return _text(REVIEW_MD)


# ----------------------------------------------------------------------------------
# self-contained JSON Schema subset validator (no new dependency)
# ----------------------------------------------------------------------------------

ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "$comment", "title", "description", "examples", "default"})
SUPPORTED_KEYWORDS = frozenset({
    "type", "const", "enum", "pattern", "minLength", "maxLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
    "required", "properties", "additionalProperties", "items", "allOf", "anyOf", "if", "then", "else",
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
                    raise SchemaUnsupported(f"{key} must be an object")
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
            raise SchemaUnsupported(f"unsupported schema keyword: {key!r}")


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


def validate(instance, node, path: str = "$") -> list[str]:
    """Validate ``instance`` against the supported subset; return a list of error strings."""
    errors: list[str] = []
    if not isinstance(node, dict):
        return errors

    if "type" in node and not _check_type(instance, node["type"]):
        errors.append(f"{path}: expected type {node['type']}, got {type(instance).__name__}")
        return errors

    if "const" in node and instance != node["const"]:
        errors.append(f"{path}: expected const {node['const']!r}, got {instance!r}")

    if "enum" in node and instance not in node["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {node['enum']!r}")

    if isinstance(instance, str):
        if "pattern" in node and not re.search(node["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {node['pattern']!r}")
        if "minLength" in node and len(instance) < node["minLength"]:
            errors.append(f"{path}: shorter than minLength {node['minLength']}")
        if "maxLength" in node and len(instance) > node["maxLength"]:
            errors.append(f"{path}: longer than maxLength {node['maxLength']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in node and instance < node["minimum"]:
            errors.append(f"{path}: below minimum {node['minimum']}")
        if "maximum" in node and instance > node["maximum"]:
            errors.append(f"{path}: above maximum {node['maximum']}")

    if isinstance(instance, list):
        if "minItems" in node and len(instance) < node["minItems"]:
            errors.append(f"{path}: fewer than minItems {node['minItems']}")
        if "maxItems" in node and len(instance) > node["maxItems"]:
            errors.append(f"{path}: more than maxItems {node['maxItems']}")
        if node.get("uniqueItems"):
            seen = [json.dumps(item, sort_keys=True) for item in instance]
            if len(set(seen)) != len(seen):
                errors.append(f"{path}: items are not unique")
        if isinstance(node.get("items"), dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, node["items"], f"{path}[{index}]"))

    if isinstance(instance, dict):
        if "minProperties" in node and len(instance) < node["minProperties"]:
            errors.append(f"{path}: fewer than minProperties {node['minProperties']}")
        if "maxProperties" in node and len(instance) > node["maxProperties"]:
            errors.append(f"{path}: more than maxProperties {node['maxProperties']}")
        for name in node.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")
        declared = node.get("properties", {})
        for name, sub in declared.items():
            if name in instance:
                errors.extend(validate(instance[name], sub, f"{path}.{name}"))
        if "additionalProperties" in node:
            extra = node["additionalProperties"]
            for name, value in instance.items():
                if name in declared:
                    continue
                if extra is False:
                    errors.append(f"{path}: additional property {name!r} is not allowed")
                elif isinstance(extra, dict):
                    errors.extend(validate(value, extra, f"{path}.{name}"))

    for index, sub in enumerate(node.get("allOf", [])):
        errors.extend(validate(instance, sub, f"{path}/allOf[{index}]"))

    if "anyOf" in node:
        if all(validate(instance, sub, path) for sub in node["anyOf"]):
            errors.append(f"{path}: matches none of anyOf")

    if "if" in node:
        if not validate(instance, node["if"], path):
            if "then" in node:
                errors.extend(validate(instance, node["then"], f"{path}/then"))
        elif "else" in node:
            errors.extend(validate(instance, node["else"], f"{path}/else"))

    return errors


# ----------------------------------------------------------------------------------
# schema conformance
# ----------------------------------------------------------------------------------

def test_the_validator_refuses_any_schema_construct_it_cannot_enforce(schema):
    assert_schema_is_fully_enforceable(schema)


def test_the_committed_review_validates_against_the_committed_schema(review, schema):
    errors = validate(review, schema)
    assert errors == [], "committed review does not satisfy the committed schema:\n" + "\n".join(errors[:40])


# ----------------------------------------------------------------------------------
# independent recalculation
# ----------------------------------------------------------------------------------

def test_independent_recalculation_check_mode_reproduces_the_committed_tables(tmp_path):
    """The v0.3 recalculation is a historical check, so it runs on a reviewed-commit snapshot.

    Historical-review test-harness scope erratum: executing the generator inside the live
    repository silently turned a check on draft-v0.3 into a check on whichever draft happens
    to be checked out, so an authorised draft-v0.4 protocol amendment necessarily broke it.
    The generator, its committed table and the expected result are all unchanged; only the
    inputs are pinned to the commit that was actually reviewed.
    """
    if not _reviewed_commit_available():
        pytest.fail(
            f"reviewed commit {REVIEWED_COMMIT} is not present; the review must be validated against a clone "
            f"that contains the reviewed history"
        )

    snapshot = tmp_path / "reviewed_snapshot"
    _materialise_reviewed_snapshot(snapshot)

    declared = _declared_decision_bearing_artifacts()
    uncovered = [path for path in declared if not (snapshot / path).is_file()]
    assert uncovered == [], f"the reviewed snapshot does not cover every declared input: {uncovered}"

    for path in CURRENT_DRAFT_BYTES_FORBIDDEN_IN_SNAPSHOT:
        assert not (snapshot / path).exists(), \
            f"{path} must not be reachable from the isolated historical recalculation"

    for relative in (RECALC_PY, RECALC_JSON):
        assert (snapshot / relative).read_bytes() == _committed_bytes(relative), \
            f"{relative} must enter the snapshot byte-for-byte unchanged"

    result = subprocess.run(
        [sys.executable, str(snapshot / RECALC_PY), "--check"],
        cwd=snapshot, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"--check failed:\n{result.stdout}\n{result.stderr}"
    assert "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS" in result.stdout


def test_the_independent_implementation_never_reaches_a_prohibited_source():
    source = _text(RECALC_PY)
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    for name in imported:
        assert "design_statistics" not in name, f"prohibited import {name!r}"
        assert "independent_methods_recalculation" not in name or name.endswith("_v0_3"), \
            f"prohibited import {name!r}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"exec", "eval", "__import__"}, \
                f"dynamic execution primitive {node.func.id} is prohibited"
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"import_module", "exec_module", "load_module", "spec_from_file_location"}, \
                f"dynamic loading primitive {node.attr} is prohibited"
    assert "importlib" not in imported

    docstring_nodes: set[int] = set()
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) \
            and isinstance(tree.body[0].value.value, str):
        docstring_nodes.add(id(tree.body[0].value))
    declaration_nodes: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PROHIBITED_SOURCE_MODULES" for target in node.targets
        ):
            for sub in ast.walk(node):
                declaration_nodes.add(id(sub))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for prohibited in PROHIBITED_SOURCES:
                if prohibited in node.value:
                    allowed = id(node) in declaration_nodes or id(node) in docstring_nodes
                    assert allowed, (
                        f"prohibited path literal {prohibited!r} is reachable outside the module docstring "
                        f"and the PROHIBITED_SOURCE_MODULES declaration"
                    )


def test_the_review_declares_and_evidences_its_independence(review):
    declaration = review["reviewer_independence_declaration"]
    assert declaration["not_the_drafting_party"] is True
    assert declaration["coordinated_with_drafting_session"] is False
    for key in (
        "prohibited_sources_imported", "prohibited_sources_executed",
        "prohibited_sources_dynamically_loaded", "prohibited_sources_copied_through_reachable_literals",
        "prohibited_sources_used_for_control_flow",
    ):
        assert declaration[key] is False, key
    assert set(declaration["prohibited_sources"]) == set(PROHIBITED_SOURCES)
    assert "BEFORE" in declaration["ordering"]
    audit = review["prohibited_source_audit"]
    assert audit["imports_found"] == []
    assert audit["exec_or_eval_found"] is False
    assert audit["importlib_found"] is False
    assert audit["prohibited_path_literals_found"] == []


# ----------------------------------------------------------------------------------
# binding to the reviewed object
# ----------------------------------------------------------------------------------

def _binding_errors(review: dict) -> list[str]:
    """Errors when the recorded reviewed-artifact identities disagree with the committed blobs."""
    errors: list[str] = []
    recorded = review["reviewed_artifact_identities"]
    if set(recorded) != set(REVIEWED_BLOBS):
        errors.append("recorded reviewed artifacts differ from the bound set")
    for path, (size, digest) in sorted(REVIEWED_BLOBS.items()):
        entry = recorded.get(path)
        if entry is None:
            errors.append(f"{path}: not recorded")
            continue
        if entry["bytes"] != size:
            errors.append(f"{path}: recorded {entry['bytes']} bytes, committed {size}")
        if entry["sha256"] != digest:
            errors.append(f"{path}: recorded sha256 does not match the committed blob")
    return errors


def test_reviewed_blobs_bind_to_the_starting_commit(review):
    if not _reviewed_commit_available():
        pytest.fail(
            f"reviewed commit {REVIEWED_COMMIT} is not present; the review must be validated against a clone "
            f"that contains the reviewed history"
        )
    head_tree = _git("rev-parse", f"{REVIEWED_COMMIT}^{{tree}}").stdout.decode().strip()
    assert head_tree == REVIEWED_TREE

    for path, (size, digest) in sorted(REVIEWED_BLOBS.items()):
        data = _blob_at_reviewed_commit(path)
        assert len(data) == size, f"{path}: {len(data)} bytes, expected {size}"
        assert hashlib.sha256(data).hexdigest() == digest, f"{path}: sha256 mismatch"

    assert _binding_errors(review) == []


def test_an_altered_reviewed_artifact_identity_is_detected(review):
    mutated = copy.deepcopy(review)
    mutated["reviewed_artifact_identities"]["studies/study3/design_receipt_v0_3.json"]["sha256"] = "0" * 64
    assert _binding_errors(mutated), "an altered reviewed-artifact identity must be detected"

    mutated = copy.deepcopy(review)
    mutated["reviewed_artifact_identities"].pop("studies/study3/design_receipt_v0_3.json")
    assert _binding_errors(mutated), "a dropped reviewed-artifact identity must be detected"


def test_the_review_object_is_recorded_as_unmodified(review):
    obj = review["review_object"]
    assert obj["changed_paths"] == 26
    assert obj["added"] == 6
    assert obj["modified"] == 20
    assert obj["deletions_renames_copies_type_changes"] == 0
    assert obj["immutable_during_this_review"] is True
    assert obj["reviewer_edited_any_reviewed_path"] is False


def test_the_reviewer_did_not_edit_either_existing_study3_test_module():
    """Both test modules that existed at the reviewed commit are unchanged in that history.

    Historical-review test-harness scope erratum: this assertion is about what the reviewer
    did to the reviewed history, so it must read the committed blobs at REVIEWED_COMMIT.
    Reading live index or working-tree bytes made it a check on the current draft instead,
    which any later authorised amendment of tests/test_study3_design.py necessarily breaks.
    The expected sizes and digests are unchanged.
    """
    if not _reviewed_commit_available():
        pytest.fail(
            f"reviewed commit {REVIEWED_COMMIT} is not present; the review must be validated against a clone "
            f"that contains the reviewed history"
        )
    for path in ("tests/test_study3_design.py", "tests/test_study3_methods_review.py"):
        size, digest = REVIEWED_BLOBS[path]
        data = _blob_at_reviewed_commit(path)
        assert len(data) == size, f"{path} was modified by the reviewer"
        assert hashlib.sha256(data).hexdigest() == digest, f"{path} was modified by the reviewer"


# ----------------------------------------------------------------------------------
# authority identity
# ----------------------------------------------------------------------------------

def test_source_and_committed_authority_are_byte_identical(review):
    data = _committed_bytes(AUTHORITY_MD)
    source = review["source_authority"]
    committed = review["committed_authority"]
    assert committed["path"] == AUTHORITY_MD
    assert committed["byte_identical_to_source"] is True
    assert len(data) == source["bytes"] == committed["bytes"]
    digest = hashlib.sha256(data).hexdigest()
    assert digest == source["sha256"] == committed["sha256"]
    assert data.count(b"\r") == 0 == source["cr_count"]
    assert data.count(b"\n") == source["lf_count"]
    assert data.endswith(b"\n") is False
    assert source["trailing_newline"] is False
    assert source["preserved_before_any_repository_mutation"] is True


# ----------------------------------------------------------------------------------
# inherited identifier sets and finding parity
# ----------------------------------------------------------------------------------

def test_exactly_twenty_inherited_findings_are_adjudicated_once_each(review):
    ids = [row["finding_id"] for row in review["inherited_finding_adjudications"]]
    assert len(ids) == 20
    assert sorted(ids) == sorted(INHERITED_IDS)
    assert len(set(ids)) == 20


def test_exactly_twenty_two_unresolved_items_are_adjudicated_once_each(review):
    ids = [row["item_id"] for row in review["unresolved_item_adjudications"]]
    assert len(ids) == 22
    assert sorted(ids) == sorted(UR_IDS)
    assert len(set(ids)) == 22


def test_every_finding_carries_a_stable_id_severity_evidence_rationale_and_consequence(review):
    seen = set()
    for row in review["new_findings"]:
        assert re.fullmatch(r"S3MR2-\d{3}", row["finding_id"]), row["finding_id"]
        assert row["finding_id"] not in seen
        seen.add(row["finding_id"])
        assert row["severity"] in ("BLOCKING", "MAJOR", "MINOR")
        assert row["evidence_paths"] and all(p.strip() for p in row["evidence_paths"])
        assert row["evidence_fields"] and all(f.strip() for f in row["evidence_fields"])
        assert row["rationale"].strip()
        assert row["consequence"].strip()
        assert row["repair_class"].strip()
    numbers = sorted(int(f.split("-")[1]) for f in seen)
    assert numbers == list(range(1, len(numbers) + 1)), "finding IDs must be contiguous from S3MR2-001"


def test_new_findings_referenced_by_inherited_adjudications_and_cross_artifacts_all_exist(review):
    declared = {row["finding_id"] for row in review["new_findings"]}
    for row in review["inherited_finding_adjudications"]:
        created = row["new_defect_created"]
        if created:
            for token in re.findall(r"S3MR2-\d{3}", created):
                assert token in declared, f"{row['finding_id']} references undeclared {token}"
    for row in review["cross_artifact_adjudications"]:
        for token in row["finding_ids"]:
            assert token in declared, f"cross-artifact candidate references undeclared {token}"
    for row in review["unresolved_methods_items"]:
        if row["id"].startswith("S3MR2-"):
            assert row["id"] in declared


def test_every_candidate_inconsistency_receives_exactly_one_status(review):
    allowed = {"CONFIRMED_BLOCKING", "CONFIRMED_MAJOR", "CONFIRMED_MINOR", "CONFIRMED_NONBLOCKING",
               "NOT_CONFIRMED", "QUALIFIED"}
    candidates = [row["candidate"] for row in review["cross_artifact_adjudications"]]
    assert len(candidates) == len(set(candidates)), "a candidate is adjudicated more than once"
    for row in review["cross_artifact_adjudications"]:
        assert row["status"] in allowed


def test_every_mandatory_audit_target_is_answered(review):
    required = {
        "6.1_i3_estimand_and_construct_validity",
        "6.2_exact_binomial_model_and_sampling_frame",
        "6.3_type_i_multiplicity_and_executable_selection",
        "6.4_family_and_profile_level_power",
        "6.5_tango_retirement_and_descriptive_remnants",
        "6.6_i4_s4_and_od2",
        "6.7_i5_confirmation_lifecycle",
        "6.8_operation_accounting_and_feasibility",
        "6.9_cross_artifact_consistency_and_claim_ceiling",
    }
    assert set(review["mandatory_audit_answers"]) == required
    for name, answer in review["mandatory_audit_answers"].items():
        assert isinstance(answer, dict) and answer, f"{name} is empty"


# ----------------------------------------------------------------------------------
# fail-closed disposition rules
# ----------------------------------------------------------------------------------

def test_the_disposition_is_one_of_the_three_permitted_strings(review):
    assert review["disposition"] in DISPOSITIONS
    assert review["state"] == STATE


def test_the_successor_action_matches_the_disposition_and_never_jumps_to_freeze(review):
    expected = {
        DISPOSITIONS[0]: "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND",
        DISPOSITIONS[1]: "OPERATOR_CONFORMANCE_AMENDMENT_FOR_DRAFT_V0_3_1",
        DISPOSITIONS[2]: "OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4",
    }
    assert review["next_legal_action"] == expected[review["disposition"]]
    lowered = review["next_legal_action"].lower()
    for forbidden in ("freeze", "execute", "execution", "bank", "seed", "p3_q", "confirmation"):
        assert forbidden not in lowered


def test_acceptance_as_specified_is_impossible_while_anything_blocking_or_major_stands(review, schema):
    if review["disposition"] == DISPOSITIONS[0]:
        assert all(f["severity"] == "MINOR" for f in review["new_findings"])
        assert review["unresolved_methods_items"] == []
        assert all(
            row["status"] == "VERIFIED_RESOLVED"
            for row in review["inherited_finding_adjudications"]
            if row["original_severity"] == "BLOCKING"
        )
    else:
        mutated = copy.deepcopy(review)
        mutated["disposition"] = DISPOSITIONS[0]
        mutated["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"
        assert validate(mutated, schema), (
            "the schema must reject acceptance as specified while blocking or major methods items stand"
        )


def test_methods_blockers_are_kept_separate_from_the_operator_decision(review):
    methods_ids = {row["id"] for row in review["unresolved_methods_items"]}
    operator_ids = {row["id"] for row in review["unresolved_operator_items"]}
    assert "OD2" in operator_ids
    assert "UR-22" in operator_ids
    assert "OD2" not in methods_ids, "OD2 must never be recorded as an unresolved methods item"
    assert "UR-22" not in methods_ids
    for row in review["unresolved_operator_items"]:
        assert row["kept_separate_from_methods_blockers"] is True

    retained = [
        row for row in review["unresolved_item_adjudications"]
        if row["status"] == "CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION"
    ]
    assert [row["item_id"] for row in retained] == ["UR-22"], (
        "CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION is legal only for the OD2/UR-22 boundary"
    )
    assert all(
        row["status"] != "CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION"
        for row in review["inherited_finding_adjudications"]
    )


def test_per_cell_power_is_never_presented_as_profile_level_power_without_a_derivation(review):
    block = review["per_cell_and_joint_power_decisions"]
    if block["does_the_protocol_label_per_cell_power_as_overall_power"] is True:
        assert block["derived_values"]["assumption_stated"].strip()
        assert block["decision"].strip()
        assert block["blocking_or_not"].strip()
        for profile in ("S1", "S2", "S3"):
            entry = block["derived_values"][f"{profile}_development_eligibility"]
            assert "under_independence" in entry
            assert "frechet_lower_bound_arbitrary_dependence" in entry


# ----------------------------------------------------------------------------------
# zero operations, false flags, nothing selected
# ----------------------------------------------------------------------------------

def test_every_operation_counter_is_zero(review):
    counters = review["operation_counters"]
    assert len(counters) == 22
    for name, value in counters.items():
        assert value == 0, f"{name} is {value}"


def test_no_prohibited_authority_flag_is_set(review):
    flags = review["authority_flags"]
    assert len(flags) == 8
    for name, value in flags.items():
        assert value is False, f"{name} is {value}"


def test_no_results_banks_seeds_model_outputs_or_evidence_rows(review):
    for key in ("results", "bank_rows", "seeds", "evidence_rows"):
        assert review[key] == [], f"{key} must be empty"


def test_the_review_selects_no_interface_and_no_positive_reference(review):
    blob = json.dumps(review)
    assert '"winner_selected": false' in blob
    assert '"positive_reference_selected": false' in blob
    assert review["operation_counters"]["interfaces_selected"] == 0
    assert review["operation_counters"]["positive_references_selected"] == 0
    graph = review["multiplicity_and_selection_graph"]
    assert graph["never_selectable"] == ["S4"]
    assert graph["rescue_paths"] == []
    assert graph["fixed_selectable_profile_denominator"] == 3


def test_the_evidence_ledger_is_untouched():
    data = _committed_bytes("paper/evidence_ledger.csv")
    assert len(data) == 25241
    assert hashlib.sha256(data).hexdigest() == \
        "3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1"
    rows = data.decode("utf-8").splitlines()
    assert len(rows) == 17
    assert rows[-1].split(",")[0] == "EV-0016"


# ----------------------------------------------------------------------------------
# Markdown / JSON parity
# ----------------------------------------------------------------------------------

def test_markdown_and_json_agree_on_disposition_state_and_next_action(review, markdown):
    assert review["disposition"] in markdown
    assert review["state"] in markdown
    assert review["next_legal_action"] in markdown
    for other in DISPOSITIONS:
        if other != review["disposition"]:
            assert f"**{other}**" not in markdown, "the Markdown must assert exactly one disposition"


def test_markdown_and_json_agree_on_every_finding_id_and_severity(review, markdown):
    for row in review["new_findings"]:
        assert row["finding_id"] in markdown, f"{row['finding_id']} missing from the Markdown review"
        pattern = rf"{re.escape(row['finding_id'])}[^\n]*{re.escape(row['severity'])}"
        assert re.search(pattern, markdown), f"{row['finding_id']} severity parity failed"


def test_markdown_and_json_agree_on_every_inherited_status(review, markdown):
    for row in review["inherited_finding_adjudications"]:
        pattern = rf"{re.escape(row['finding_id'])}[^\n]*{re.escape(row['status'])}"
        assert re.search(pattern, markdown), f"{row['finding_id']} status parity failed"
    for row in review["unresolved_item_adjudications"]:
        pattern = rf"{re.escape(row['item_id'])}[^\n]*{re.escape(row['status'])}"
        assert re.search(pattern, markdown), f"{row['item_id']} status parity failed"


def test_markdown_states_the_od2_boundary_and_the_claim_ceiling(markdown):
    assert "OD2" in markdown
    assert "UNRESOLVED_BLOCKING_OPERATOR_DECISION" in markdown
    for sentence in (
        "Study 1 remains closed",
        "Study 2 remains closed",
        "Study 3 remains unfrozen",
        "No interface or positive reference is selected",
        "The original research question remains unanswered",
    ):
        assert sentence in markdown, f"missing claim-ceiling sentence: {sentence!r}"


def test_markdown_binds_the_reviewed_commit_and_the_authority(review, markdown):
    assert REVIEWED_COMMIT in markdown
    assert REVIEWED_TREE in markdown
    assert review["committed_authority"]["sha256"] in markdown


# ----------------------------------------------------------------------------------
# negative mutations: every fail-closed rule must actually bite
# ----------------------------------------------------------------------------------

def _mutations(review: dict) -> list[tuple[str, dict]]:
    cases: list[tuple[str, dict]] = []

    m = copy.deepcopy(review); m["disposition"] = "STUDY3_V0_3_METHODS_REVIEW_APPROVED"
    cases.append(("unknown disposition", m))

    m = copy.deepcopy(review); m["state"] = "STUDY3_SOMETHING_ELSE"
    cases.append(("unknown state", m))

    m = copy.deepcopy(review); m["inherited_finding_adjudications"].pop()
    cases.append(("missing inherited identifier", m))

    m = copy.deepcopy(review)
    m["inherited_finding_adjudications"][1] = copy.deepcopy(m["inherited_finding_adjudications"][0])
    cases.append(("duplicate inherited identifier", m))

    m = copy.deepcopy(review)
    extra = copy.deepcopy(m["inherited_finding_adjudications"][0]); extra["finding_id"] = "S3MR-021"
    m["inherited_finding_adjudications"].append(extra)
    cases.append(("extra inherited identifier", m))

    m = copy.deepcopy(review); m["unresolved_item_adjudications"].pop()
    cases.append(("missing UR identifier", m))

    m = copy.deepcopy(review); del m["mandatory_audit_answers"]["6.4_family_and_profile_level_power"]
    cases.append(("missing mandatory audit answer", m))

    m = copy.deepcopy(review); del m["new_findings"][0]["severity"]
    cases.append(("finding without severity", m))

    m = copy.deepcopy(review); m["new_findings"][0]["evidence_paths"] = []
    cases.append(("finding without evidence path", m))

    m = copy.deepcopy(review); m["new_findings"][0]["evidence_fields"] = []
    cases.append(("finding without evidence field", m))

    m = copy.deepcopy(review); m["new_findings"][0]["rationale"] = ""
    cases.append(("finding without rationale", m))

    m = copy.deepcopy(review); m["new_findings"][0]["consequence"] = ""
    cases.append(("finding without consequence", m))

    m = copy.deepcopy(review)
    m["disposition"] = DISPOSITIONS[0]
    m["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"
    cases.append(("acceptance as specified with unresolved blocking or major items", m))

    m = copy.deepcopy(review)
    m["disposition"] = DISPOSITIONS[0]
    m["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"
    m["new_findings"] = [f for f in m["new_findings"] if f["severity"] == "MINOR"]
    m["unresolved_methods_items"] = []
    cases.append(("acceptance as specified with an inherited BLOCKING not verified resolved", m))

    m = copy.deepcopy(review)
    m["unresolved_item_adjudications"][0]["status"] = "CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION"
    cases.append(("CORRECTLY_RETAINED used outside UR-22", m))

    m = copy.deepcopy(review)
    m["inherited_finding_adjudications"][0]["status"] = "CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION"
    cases.append(("CORRECTLY_RETAINED used on an inherited finding", m))

    m = copy.deepcopy(review); m["operation_counters"]["forward_passes"] = 1
    cases.append(("non-zero operation counter", m))

    m = copy.deepcopy(review); m["authority_flags"]["frozen"] = True
    cases.append(("true freeze flag", m))

    m = copy.deepcopy(review); m["authority_flags"]["execution_authorized"] = True
    cases.append(("true execution flag", m))

    m = copy.deepcopy(review); m["authority_flags"]["winner_selected"] = True
    cases.append(("selected interface", m))

    m = copy.deepcopy(review); m["authority_flags"]["positive_reference_selected"] = True
    cases.append(("selected positive reference", m))

    m = copy.deepcopy(review); m["bank_rows"] = [{"row": 1}]
    cases.append(("bank row present", m))

    m = copy.deepcopy(review); m["seeds"] = [1]
    cases.append(("seed present", m))

    m = copy.deepcopy(review); m["results"] = [{"gate": "I3", "passed": True}]
    cases.append(("result present", m))

    m = copy.deepcopy(review); m["evidence_rows"] = [{"id": "EV-0017"}]
    cases.append(("evidence row present", m))

    m = copy.deepcopy(review); m["authority_flags"]["confirmation_access_authorized"] = True
    cases.append(("confirmation access authorized", m))

    m = copy.deepcopy(review); m["next_legal_action"] = "OPERATOR_REVIEW_ADOPTION_AND_OD2_RESOLUTION_ROUND"
    cases.append(("successor action inconsistent with the disposition", m))

    m = copy.deepcopy(review)
    del m["per_cell_and_joint_power_decisions"]["derived_values"]["assumption_stated"]
    cases.append(("per-cell power asserted as profile power without a stated derivation", m))

    m = copy.deepcopy(review)
    m["reviewer_independence_declaration"]["prohibited_sources_imported"] = True
    cases.append(("independence declaration contradicted", m))

    m = copy.deepcopy(review); m["committed_authority"]["byte_identical_to_source"] = False
    cases.append(("committed authority not byte identical to source", m))

    m = copy.deepcopy(review); m["review_object"]["reviewer_edited_any_reviewed_path"] = True
    cases.append(("reviewer edited the reviewed object", m))

    m = copy.deepcopy(review); m["multiplicity_and_selection_graph"]["rescue_paths"] = ["pooled rate"]
    cases.append(("a rescue path exists", m))

    return cases


def test_the_schema_rejects_every_prohibited_mutation(review, schema):
    unenforced = []
    for label, mutated in _mutations(review):
        if not validate(mutated, schema):
            unenforced.append(label)
    assert unenforced == [], "the schema failed to reject: " + "; ".join(unenforced)


def test_the_schema_accepts_the_unmutated_committed_review(review, schema):
    assert validate(review, schema) == []


# ----------------------------------------------------------------------------------
# receipt
# ----------------------------------------------------------------------------------

def test_the_receipt_binds_the_round(review):
    receipt = _json(RECEIPT_JSON)
    assert receipt["disposition"] == review["disposition"]
    assert receipt["state"] == review["state"]
    assert receipt["starting_commit"] == REVIEWED_COMMIT
    assert receipt["starting_tree"] == REVIEWED_TREE
    assert receipt["next_legal_action"] == review["next_legal_action"]
    assert receipt["evidence_ledger"]["sha256"] == \
        "3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1"
    assert receipt["evidence_ledger"]["rows"] == 16
    assert all(value == 0 for value in receipt["operation_counters"].values())
    assert all(value is False for value in receipt["authority_flags"].values())
    assert RECEIPT_JSON not in receipt["new_artifacts"], "the receipt must not carry its own self-hash"
    for path in (REVIEW_MD, REVIEW_JSON, REVIEW_SCHEMA, RECALC_PY, RECALC_JSON, AUTHORITY_MD):
        assert path in receipt["new_artifacts"], f"{path} missing from the receipt"


def test_the_receipt_path_whitelist_is_the_observed_path_set():
    receipt = _json(RECEIPT_JSON)
    added = set(receipt["path_whitelist"]["added"])
    modified = set(receipt["path_whitelist"]["modified"])
    assert len(added) == 8, "exactly eight paths may be added"
    assert len(modified) <= 9, "at most nine existing paths may be modified"
    assert len(added | modified) <= 17, "the hard ceiling is seventeen changed paths"
    assert added.isdisjoint(modified)
    assert set(receipt["path_whitelist"]["observed"]) == (added | modified)
