"""Committed guard for the Study 3 draft-v0.2 independent methods review.

This module enforces the review's fail-closed contract. It validates the review
document against its committed schema using a dependency-free validator, because
``jsonschema`` is deliberately absent from ``requirements.lock.txt`` and this
round may not add a dependency. It re-runs the independent recalculation in
check mode, proves that the independent implementation never reaches the
drafting implementation, binds the reviewed artifacts by content hash, and
carries a negative-mutation battery that demonstrates each fail-closed rule can
actually reject a corrupted review rather than merely accepting a well-formed
one.

The review under guard is an *independent* review: nothing here may be relaxed
to make the review pass, and ``tests/test_study3_design.py`` - which belongs to
the review object - is not touched by this module.

**Commit addressing.** This module guards a *historical* review of a *historical*
design. Every byte it asserts about is therefore read from an explicit commit,
never from ``HEAD`` and never from the working tree:

* ``REVIEWED_COMMIT`` is the design draft-v0.2 the reviewer actually reviewed.
* ``REVIEW_COMMIT`` is the commit that published the review's own outputs.

Later rounds legitimately amend the design, the registries and the routing
documents. An earlier implementation of this module compared mutable ``HEAD``
files against draft-v0.2 hashes, which made a *permitted* later amendment look
like tampering with the review. Addressing the historical blobs by commit removes
that false coupling without changing a single asserted value: the disposition,
the finding text, the counts, the checklist answers and every recalculated number
are exactly as the reviewer returned them, and no assertion is weakened.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The design bytes the independent reviewer reviewed.
REVIEWED_COMMIT = "8a2c4a0b2a73c5d802988333f11ea6c22828f6f5"
# The commit that published the review's own outputs and registrations.
REVIEW_COMMIT = "e4bcda3a487ea9c9a085e3943103a07501014431"

REVIEW_JSON_PATH = ("studies/study3/reviews/"
                    "v0_2_independent_methods_review.json")
REVIEW_SCHEMA_PATH = ("studies/study3/reviews/"
                      "v0_2_independent_methods_review.schema.json")
REVIEW_MD_PATH = "studies/study3/reviews/v0_2_independent_methods_review.md"
RECALC_TABLES_PATH = ("studies/study3/analysis/"
                      "independent_methods_recalculation_tables.json")
RECEIPT_PATH = "studies/study3/methods_review_receipt_v0_2.json"
DESIGN_TEST_PATH = "tests/test_study3_design.py"

# The reviewer's own recalculation is immutable. It is executed from committed
# bytes rather than from the checkout, because it compares itself against the
# drafting table it reviewed, and draft-v0.3 legitimately rewrites that table.
RECALC_SCRIPT_PATH = ("studies/study3/analysis/"
                      "independent_methods_recalculation.py")
RECALC_SCRIPT = os.path.join(
    REPO_ROOT, "studies", "study3", "analysis",
    "independent_methods_recalculation.py")
RECALC_TABLES_BASENAME = "independent_methods_recalculation_tables.json"
DRAFTING_TABLES_PATH = "studies/study3/analysis/design_statistics_tables.json"
DRAFTING_TABLES_BASENAME = "design_statistics_tables.json"
DRAFTING_SCRIPT_BASENAME = "design_statistics"

PERMITTED_DISPOSITIONS = (
    "STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED",
    "STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES",
    "STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED",
)

EXPECTED_STATE = (
    "STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION"
)


# --------------------------------------------------------------------------
# Dependency-free JSON Schema validator
# --------------------------------------------------------------------------
#
# Supports the subset the committed review schema actually uses. Any unsupported
# keyword raises rather than being silently ignored, so a schema that quietly
# stopped constraining anything would fail this suite instead of passing it.

_ANNOTATION_KEYWORDS = frozenset(
    {"$schema", "$id", "title", "description", "examples", "default"})

_SUPPORTED_KEYWORDS = frozenset({
    "type", "const", "enum", "required", "properties", "additionalProperties",
    "items", "contains", "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
    "minItems", "maxItems", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "uniqueItems", "propertyNames",
})

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaViolation(Exception):
    """Raised when an instance does not satisfy the committed schema."""


def _fail(where: str, message: str) -> None:
    raise SchemaViolation("%s: %s" % (where or "<root>", message))


def _matches(instance, schema) -> bool:
    """Non-raising form, for anyOf/oneOf/not/contains/if."""
    try:
        _validate(instance, schema, "<probe>")
    except SchemaViolation:
        return False
    return True


def _validate(instance, schema, where: str = "") -> None:
    if not isinstance(schema, dict):
        raise SchemaViolation("schema fragment at %s is not an object" % where)

    unknown = set(schema) - _SUPPORTED_KEYWORDS - _ANNOTATION_KEYWORDS
    if unknown:
        raise SchemaViolation(
            "unsupported schema keyword(s) %s at %s; the validator must be "
            "extended rather than silently skipping them"
            % (sorted(unknown), where or "<root>"))

    if "type" in schema:
        expected = schema["type"]
        names = [expected] if isinstance(expected, str) else list(expected)
        for name in names:
            if name not in _TYPE_CHECKS:
                raise SchemaViolation("unknown type %r at %s" % (name, where))
        if not any(_TYPE_CHECKS[name](instance) for name in names):
            _fail(where, "expected type %s, got %s"
                  % (expected, type(instance).__name__))

    if "const" in schema and instance != schema["const"]:
        _fail(where, "expected const %r, got %r" % (schema["const"], instance))

    if "enum" in schema and instance not in schema["enum"]:
        _fail(where, "value %r not in enum %r" % (instance, schema["enum"]))

    if "not" in schema and _matches(instance, schema["not"]):
        _fail(where, "value %r matched a forbidden 'not' subschema" % (instance,))

    for subschema in schema.get("allOf", []):
        _validate(instance, subschema, where)

    if "anyOf" in schema and not any(
            _matches(instance, sub) for sub in schema["anyOf"]):
        _fail(where, "value matched no anyOf branch")

    if "oneOf" in schema:
        hits = sum(1 for sub in schema["oneOf"] if _matches(instance, sub))
        if hits != 1:
            _fail(where, "value matched %d oneOf branches, expected 1" % hits)

    if "if" in schema:
        branch = "then" if _matches(instance, schema["if"]) else "else"
        if branch in schema:
            _validate(instance, schema[branch], where)

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            _fail(where, "string shorter than minLength %d (was %d)"
                  % (schema["minLength"], len(instance)))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            _fail(where, "string longer than maxLength %d" % schema["maxLength"])
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            _fail(where, "string does not match pattern %r" % schema["pattern"])

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            _fail(where, "value %r below minimum %r"
                  % (instance, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            _fail(where, "value %r above maximum %r"
                  % (instance, schema["maximum"]))

    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                _fail(where, "missing required property %r" % name)
        properties = schema.get("properties", {})
        for name, value in instance.items():
            if name in properties:
                _validate(value, properties[name], "%s.%s" % (where, name))
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                _fail(where, "unexpected propert%s %s"
                      % ("y" if len(extra) == 1 else "ies", extra))
        if "propertyNames" in schema:
            for name in instance:
                _validate(name, schema["propertyNames"], "%s.<key>" % where)

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            _fail(where, "array has %d items, minItems is %d"
                  % (len(instance), schema["minItems"]))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            _fail(where, "array has %d items, maxItems is %d"
                  % (len(instance), schema["maxItems"]))
        if "items" in schema:
            for index, value in enumerate(instance):
                _validate(value, schema["items"], "%s[%d]" % (where, index))
        if "contains" in schema and not any(
                _matches(value, schema["contains"]) for value in instance):
            _fail(where, "no array element satisfied the 'contains' subschema")
        if schema.get("uniqueItems") is True:
            rendered = [json.dumps(v, sort_keys=True) for v in instance]
            if len(set(rendered)) != len(rendered):
                _fail(where, "array items are not unique")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def _commit_is_reachable(commit: str) -> bool:
    """True when ``commit`` is an object in this clone.

    A shallow or partial clone cannot answer questions about history. That is an
    environment limitation, not a repository defect, so the affected checks skip
    with an explicit reason rather than failing or silently degrading to a
    weaker source of bytes.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", REPO_ROOT, "cat-file", "-e", commit + "^{commit}"],
            capture_output=True)
    except OSError:
        return False
    return completed.returncode == 0


def _blob_at(commit: str, path: str) -> bytes:
    """Return the bytes Git stores for ``path`` at an explicit ``commit``.

    There is deliberately **no** working-tree fallback. The whole point of
    addressing a historical blob by commit is that the answer must not depend on
    what the checkout currently contains, on the platform's line-ending policy,
    or on how many amendment rounds have happened since.
    """
    completed = subprocess.run(
        ["git", "-C", REPO_ROOT, "cat-file", "blob",
         "%s:%s" % (commit, path)],
        capture_output=True)
    assert completed.returncode == 0, (
        "cannot read %s at %s: %s"
        % (path, commit, completed.stderr.decode("utf-8", "replace")))
    return completed.stdout


def _json_at(commit: str, path: str):
    return json.loads(_blob_at(commit, path).decode("utf-8"))


def _require_history(*commits: str) -> None:
    for commit in commits:
        if not _commit_is_reachable(commit):
            pytest.skip("commit %s is not present in this clone" % commit)


def _committed_bytes(path: str) -> bytes:
    """Return the bytes Git stores for ``path`` at HEAD.

    The review binds *committed* content. Reading the working tree instead would
    make the binding depend on the checkout's line-ending policy, which differs
    between platforms, so a review that is correct in the validation container
    would appear corrupt on a developer machine. Falls back to the working tree
    only when Git cannot answer.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", REPO_ROOT, "cat-file", "blob", "HEAD:" + path],
            capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
    except OSError:
        pass
    with open(os.path.join(REPO_ROOT, path.replace("/", os.sep)), "rb") as handle:
        return handle.read()


@pytest.fixture(scope="module")
def review():
    _require_history(REVIEW_COMMIT)
    return _json_at(REVIEW_COMMIT, REVIEW_JSON_PATH)


@pytest.fixture(scope="module")
def schema():
    _require_history(REVIEW_COMMIT)
    return _json_at(REVIEW_COMMIT, REVIEW_SCHEMA_PATH)


@pytest.fixture(scope="module")
def tables():
    _require_history(REVIEW_COMMIT)
    return _json_at(REVIEW_COMMIT, RECALC_TABLES_PATH)


@pytest.fixture(scope="module")
def markdown():
    _require_history(REVIEW_COMMIT)
    return _blob_at(REVIEW_COMMIT, REVIEW_MD_PATH).decode("utf-8")


@pytest.fixture(scope="module")
def receipt():
    _require_history(REVIEW_COMMIT)
    return _json_at(REVIEW_COMMIT, RECEIPT_PATH)


# --------------------------------------------------------------------------
# 1. Schema validation, and 14. acceptance of the unmutated review
# --------------------------------------------------------------------------

def test_the_committed_review_validates_against_the_committed_schema(
        review, schema):
    """Requirement 1 and requirement 14: the real review must be accepted."""
    _validate(review, schema)


def test_the_validator_rejects_a_schema_it_cannot_fully_enforce():
    """A validator that ignored unknown keywords would silently stop guarding."""
    with pytest.raises(SchemaViolation) as excinfo:
        _validate({"a": 1}, {"type": "object", "dependentRequired": {"a": ["b"]}})
    assert "unsupported schema keyword" in str(excinfo.value)


# --------------------------------------------------------------------------
# 2. Independent recalculation in check mode
# --------------------------------------------------------------------------

def test_independent_recalculation_check_mode_reproduces_the_committed_tables():
    """Requirement 2: recompute from scratch and compare with the committed table.

    The reviewer's recalculation compares its own recomputation against the
    *drafting* table it reviewed. That table is
    ``design_statistics_tables.json``, which draft-v0.3 legitimately rewrites,
    so running the check against the working tree would silently start asking a
    different question: whether the v0.2 reviewer reproduces the v0.3 drafting
    party. It does not, and it must not be made to.

    The historical assertion is therefore reconstructed from committed blobs by
    explicit commit. The immutable recalculation script and its committed review
    table are taken from the review commit, the drafting table is taken from the
    reviewed design commit, and the three are materialised together in a scratch
    directory so the script's own ``os.path.dirname(__file__)`` resolution finds
    exactly the bytes the reviewer had. Nothing is weakened: the same script
    bytes recompute the same numbers and must still agree exactly.
    """
    _require_history(REVIEW_COMMIT)
    _require_history(REVIEWED_COMMIT)

    script_bytes = _blob_at(REVIEW_COMMIT, RECALC_SCRIPT_PATH)
    assert script_bytes == _committed_bytes(RECALC_SCRIPT_PATH), (
        "the independent recalculation script is immutable and must be "
        "byte-identical at HEAD and at the review commit")

    workdir = tempfile.mkdtemp(prefix="study3_recalc_")
    try:
        for name, blob in (
                (os.path.basename(RECALC_SCRIPT_PATH), script_bytes),
                (RECALC_TABLES_BASENAME,
                 _blob_at(REVIEW_COMMIT, RECALC_TABLES_PATH)),
                (DRAFTING_TABLES_BASENAME,
                 _blob_at(REVIEWED_COMMIT, DRAFTING_TABLES_PATH))):
            with open(os.path.join(workdir, name), "wb") as handle:
                handle.write(blob)
        completed = subprocess.run(
            [sys.executable,
             os.path.join(workdir, os.path.basename(RECALC_SCRIPT_PATH)),
             "--check"],
            cwd=workdir, capture_output=True, text=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    assert completed.returncode == 0, (
        "independent recalculation check mode failed:\n%s\n%s"
        % (completed.stdout, completed.stderr))
    assert "INDEPENDENT_RECALCULATION_CHECK_OK=1" in completed.stdout


# --------------------------------------------------------------------------
# 3. Independence from the drafting implementation
# --------------------------------------------------------------------------

def test_the_independent_script_never_reaches_the_drafting_implementation():
    """Requirement 3: no import, no exec, no dynamic load of design_statistics.

    Agreement with the drafting numbers is not validation, so the whole point of
    the independent recalculation is lost if it can reach the code it checks.
    This is a static assertion over the parsed source, so it holds regardless of
    which branches execute.
    """
    with open(RECALC_SCRIPT, "r", encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source, filename=RECALC_SCRIPT)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert DRAFTING_SCRIPT_BASENAME not in alias.name, (
                    "independent script imports %s" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            assert DRAFTING_SCRIPT_BASENAME not in (node.module or ""), (
                "independent script imports from %s" % node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            assert name not in {"exec", "eval", "compile"}, (
                "independent script uses %s(), which could load the drafting "
                "implementation dynamically" % name)
            if name in {"import_module", "__import__", "load_module",
                        "spec_from_file_location", "module_from_spec"}:
                raise AssertionError(
                    "independent script uses %s(), a dynamic import route" % name)

    # The script legitimately names design_statistics.py in its own independence
    # declaration and in the constant its own AST self-check compares against,
    # so the filename appearing in the source proves nothing either way. What
    # would actually break independence is reading a Python file, so that is
    # what is asserted here. Reading design_statistics_tables.json is required
    # and permitted: comparing against the drafting *output* is the review, and
    # only reaching the drafting *code* would be borrowing its reasoning.
    literals = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    literals[target.id] = node.value.value

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name not in {"open", "read_text", "read_bytes"}:
            continue
        reachable = []
        for inner in ast.walk(node):
            if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                reachable.append(inner.value)
            elif isinstance(inner, ast.Name) and inner.id in literals:
                reachable.append(literals[inner.id])
        for candidate in reachable:
            assert not candidate.endswith(".py"), (
                "independent script opens the Python file %r; it may compare "
                "against the drafting tables but never against drafting code"
                % candidate)


def test_the_review_declares_its_own_independence(review):
    independence = review["reviewer_independence"]
    assert independence["reviewer_wrote_the_reviewed_design"] is False
    assert independence["does_not_import_design_statistics"] is True
    assert independence["does_not_exec_or_dynamically_load_design_statistics"] is True
    assert independence["does_not_copy_functions_from_design_statistics"] is True
    assert independence["independent_closed_form_checks_per_family"], (
        "every statistical family needs at least one independent closed-form "
        "or published-example check; agreement with the draft proves nothing")


# --------------------------------------------------------------------------
# 4. Reviewed artifact identities
# --------------------------------------------------------------------------

def test_reviewed_artifact_identities_bind_the_review_to_exact_bytes(review):
    """Requirement 4: the review is bound to content, not to file names."""
    _require_history(REVIEWED_COMMIT)
    identities = review["reviewed_artifact_identities"]
    assert identities, "the review must record what it reviewed"
    seen = set()
    for row in identities:
        path = row["path"]
        assert path not in seen, "duplicate artifact identity for %s" % path
        seen.add(path)
        # Read the reviewed bytes at the reviewed commit. A later authorised
        # amendment round legitimately changes these files at HEAD; that is not
        # evidence that the review was tampered with.
        payload = _blob_at(REVIEWED_COMMIT, path)
        assert len(payload) == row["bytes"], (
            "%s is %d bytes, review recorded %d"
            % (path, len(payload), row["bytes"]))
        assert hashlib.sha256(payload).hexdigest() == row["sha256"], (
            "%s content differs from the reviewed bytes" % path)

    for required in ("studies/study3/protocol/interface_calibration_protocol_draft.json",
                     "studies/study3/analysis/independent_methods_review_packet.md",
                     "studies/study3/analysis/design_statistics.py",
                     "tests/test_study3_design.py"):
        assert required in seen, "review does not bind %s" % required


def test_the_review_object_is_recorded_as_unmodified(review):
    assert review["review_object_is_unmodified"] is True


# --------------------------------------------------------------------------
# 5. Exactly the 22 checklist IDs
# --------------------------------------------------------------------------

def test_exactly_the_twenty_two_packet_checklist_items_are_answered(review):
    """Requirement 5: no missing item, no invented item, no unanswered item."""
    answers = review["checklist_answers"]
    assert len(answers) == 22
    assert sorted(a["id"] for a in answers) == list(range(1, 23))
    for answer in answers:
        assert answer["status"] == "ANSWERED", (
            "checklist item %s is not answered" % answer["id"])
        assert answer["verdict"] in {"YES", "NO", "QUALIFIED"}
        assert len(answer["answer"].strip()) >= 20, (
            "checklist item %s has no substantive answer" % answer["id"])
        assert answer["evidence"], (
            "checklist item %s cites no evidence" % answer["id"])


# --------------------------------------------------------------------------
# 6. Disposition rules
# --------------------------------------------------------------------------

def test_the_disposition_is_one_of_the_three_permitted_strings(review):
    assert review["disposition"] in PERMITTED_DISPOSITIONS
    assert review["state"] == EXPECTED_STATE


def test_acceptance_as_specified_is_impossible_while_anything_is_unresolved(review):
    """Requirement 6.

    An unresolved checklist item is never acceptance, and the reviewer's ability
    to supply values the draft omitted is not grounds for accepting the draft as
    specified.
    """
    blocking = [f for f in review["findings"] if f["severity"] == "BLOCKING"]
    unresolved = [i for i in review["unresolved_items"]["items"]
                  if i["state"] != "RESOLVED"]
    if review["disposition"] == "STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED":
        assert not blocking
        assert not unresolved
        assert review["required_changes_exist"] is False
    else:
        assert review["required_changes_exist"] is True

    if blocking or unresolved:
        assert review["disposition"] != (
            "STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED")


def test_every_finding_carries_a_stable_id_severity_and_evidence(review):
    ids = [f["id"] for f in review["findings"]]
    assert len(ids) == len(set(ids)), "finding IDs must be unique"
    for finding in review["findings"]:
        assert re.fullmatch(r"S3MR-\d{3}", finding["id"])
        assert finding["severity"] in {"BLOCKING", "MAJOR", "MINOR"}
        assert finding["evidence_paths"], (
            "%s has no evidence paths" % finding["id"])
        assert finding["required_change"].strip(), (
            "%s states no required change" % finding["id"])


def test_every_candidate_inconsistency_receives_exactly_one_status(review):
    entries = review["cross_artifact_consistency"]["candidate_inconsistencies"]
    permitted = {"CONFIRMED_BLOCKING", "CONFIRMED_NONBLOCKING",
                 "NOT_CONFIRMED", "QUALIFIED"}
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for entry in entries:
        assert entry["status"] in permitted
        assert entry["files"] and entry["quoted_fields"] and entry["rationale"]


# --------------------------------------------------------------------------
# 7. Zero counters and prohibited authority flags
# --------------------------------------------------------------------------

def test_every_operation_counter_is_zero(review):
    """Requirement 7: this round performed zero experimental operations."""
    counts = review["operation_counts"]
    assert counts, "the review must account for its operations"
    nonzero = {k: v for k, v in counts.items() if v != 0}
    assert not nonzero, "non-zero operation counters: %s" % nonzero
    for name in ("model_downloads", "tokenizer_constructions", "weight_loads",
                 "forward_passes", "generations", "activation_extractions",
                 "probe_fits", "patching_operations", "ablation_operations",
                 "lens_operations", "provider_calls", "gpu_jobs",
                 "bank_rows_created", "seeds_drawn",
                 "gate_evaluations_against_a_model",
                 "confirmation_split_accesses"):
        assert name in counts, "unaccounted operation class: %s" % name


def test_no_prohibited_authority_flag_is_set(review):
    flags = review["authority_flags"]
    for name in ("frozen", "freeze_authorized", "execution_authorized",
                 "gpu_authorized", "bank_construction_authorized",
                 "model_selection_authorized", "mechanistic_authority_created"):
        assert flags[name] is False, "%s must remain false" % name


def test_no_results_banks_seeds_model_outputs_or_evidence_rows(review):
    for name in ("result_rows", "bank_rows", "seeds", "model_outputs",
                 "evidence_rows"):
        assert review[name] == [], "%s must be empty in a methods review" % name


# --------------------------------------------------------------------------
# 8 and 9. No selection; OD2 stays with the operator
# --------------------------------------------------------------------------

def test_the_review_selects_no_interface_and_no_model(review):
    selection = review["selection_state"]
    assert selection["selected_interface_profile"] is None
    assert selection["selected_positive_reference_checkpoint"] is None
    assert selection["selected_model"] is None


def test_od2_remains_operator_controlled_and_no_decision_is_adopted(review):
    """Requirement 9. OD5 and OD6 may receive recommendations but not adoption."""
    decisions = {d["id"]: d for d in review["operator_decisions"]["decisions"]}
    for expected in ("OD2", "OD5", "OD6"):
        assert expected in decisions, "%s is unaccounted for" % expected
        assert decisions[expected]["adopted_by_this_round"] is False

    assert decisions["OD2"]["review_action"] == "NONE - operator-controlled"
    for name in ("OD5", "OD6"):
        assert decisions[name]["review_action"] == "RECOMMENDATION_ONLY"


def test_no_positive_reference_checkpoint_is_named_as_a_choice(review):
    """The review may describe what OD2 must freeze; it may not choose."""
    rendered = json.dumps(review)
    forbidden_choice = re.compile(
        r"(select|choose|chosen|selected|adopt|pin|recommend)\w*[^.]{0,80}"
        r"(Qwen3-4B-Instruct-2507|Qwen2\.5-Math-7B-Instruct)",
        re.IGNORECASE)
    assert forbidden_choice.search(rendered) is None, (
        "the review appears to select a positive-reference checkpoint")
    assert review["positive_reference_statistical_requirements"][
        "od2_state"].startswith("untouched")


# --------------------------------------------------------------------------
# 10. Required changes cannot route to freeze or execution
# --------------------------------------------------------------------------

def test_required_changes_cannot_route_to_freeze_or_execution(review):
    if not review["required_changes_exist"]:
        pytest.skip("no required changes recorded")
    action = review["next_legal_action"]
    assert action["routes_directly_to_freeze"] is False
    assert action["routes_directly_to_execution"] is False
    assert "FREEZE" not in action["action_id"].upper()
    assert "EXECUT" not in action["action_id"].upper()
    assert action["prohibited_next_actions"], (
        "a non-accepting review must name what may not happen next")


def test_the_review_creates_no_execution_or_mechanistic_authority(review):
    assert review["absence_of_execution_authority"]["statement"].strip()
    ceiling = json.dumps(review["claim_ceiling"]).lower()
    assert "mechanistic" in ceiling, (
        "the claim ceiling must state that no mechanistic authority is created")


# --------------------------------------------------------------------------
# 11. Every reviewed parameter carries an unambiguous unit
# --------------------------------------------------------------------------

def test_every_recommended_parameter_declares_the_unit_of_its_sample_size(review):
    """Requirement 11.

    The draft under review leaves ``n`` without a unit in every artifact, and the
    same symbol denotes base items, derived variants and scored rows in different
    places. A review that repeated that omission would be worthless.
    """
    recommendations = review["gate_parameter_recommendations"]
    rows = recommendations["exact_binomial_gates"]
    assert rows
    for row in rows:
        assert row["unit_of_n"].strip(), (
            "gate %s recommends a sample size with no unit" % row["gate"])
        assert row["alpha_basis"].strip(), (
            "gate %s states an alpha with no basis" % row["gate"])
        assert row["p1_justification"].strip(), (
            "gate %s states an alternative with no substantive justification"
            % row["gate"])
        assert "not adopted" in row["authority_status"].lower()
    assert recommendations["paired_secondary_criterion"]["unit_of_n"].strip()
    assert "NOT_ADOPTED_NOT_FROZEN" in recommendations["binding_status"]


def test_recommended_parameters_match_the_independently_computed_tables(
        review, tables):
    """The review document may transcribe, never re-derive by hand.

    Every numeric row in the review is copied from the recalculation tables that
    were produced by the recalculation script. Asserting equality here means the
    check-mode run above transitively re-verifies the review's own numbers.
    """
    assert (review["gate_parameter_recommendations"]["exact_binomial_gates"]
            == tables["reviewed_parameter_recommendations"])
    assert (review["gate_parameter_recommendations"]["admissible_n_rule"]
            == tables["admissible_n_rule"])
    paired = review["gate_parameter_recommendations"]["paired_secondary_criterion"]
    for key in ("rejection_rule", "size_over_feasible_null_boundary",
                "power_at_nominal_critical_value",
                "conservative_critical_value_calibration"):
        assert paired[key] == tables["paired_equivalence"][key]
    projection = review["projected_operation_accounting"]
    for key in ("unit_definitions", "variants_per_base_item_by_profile",
                "work_streams", "totals", "executed_operation_counts"):
        assert projection[key] == tables["projected_cells_and_operations"][key]


def test_the_projection_reports_zero_executed_operations(review):
    totals = review["projected_operation_accounting"]["totals"]
    assert totals["forward_passes_executed_this_round"] == 0
    assert totals["generations_executed_this_round"] == 0
    executed = review["projected_operation_accounting"]["executed_operation_counts"]
    assert all(value == 0 for value in executed.values()), (
        "projected work is planning arithmetic; nothing was executed")


# --------------------------------------------------------------------------
# 12. Markdown / JSON parity
# --------------------------------------------------------------------------

def test_markdown_and_json_agree_on_every_decision_bearing_field(
        review, markdown):
    """Requirement 12.

    A human reads the Markdown and a machine reads the JSON. If they can drift,
    the review has two dispositions.
    """
    assert review["disposition"] in markdown
    assert review["state"] in markdown
    assert review["reviewed_commit"] in markdown

    for finding in review["findings"]:
        assert finding["id"] in markdown, (
            "%s is absent from the Markdown review" % finding["id"])

    for decision in review["operator_decisions"]["decisions"]:
        assert decision["id"] in markdown
        assert decision["review_action"] in markdown, (
            "%s status is not stated verbatim in the Markdown"
            % decision["id"])

    assert review["next_legal_action"]["action_id"] in markdown

    for other in PERMITTED_DISPOSITIONS:
        if other != review["disposition"]:
            occurrences = markdown.count(other)
            assert occurrences <= 3, (
                "the Markdown mentions the non-returned disposition %s too "
                "often to be unambiguous" % other)


def test_markdown_records_the_reviewed_artifact_hashes(review, markdown):
    for row in review["reviewed_artifact_identities"]:
        assert row["sha256"] in markdown, (
            "Markdown does not record the reviewed hash of %s" % row["path"])


# --------------------------------------------------------------------------
# 13. Negative-mutation battery
# --------------------------------------------------------------------------
#
# Each mutation corrupts the review in exactly one way and must be rejected. A
# schema that accepted every mutation would pass every test above while guarding
# nothing at all.

def _mutate_unknown_disposition(doc):
    doc["disposition"] = "STUDY3_METHODS_REVIEW_LOOKS_FINE_TO_ME"


def _mutate_drop_a_checklist_item(doc):
    doc["checklist_answers"] = doc["checklist_answers"][:-1]


def _mutate_add_a_checklist_item(doc):
    extra = copy.deepcopy(doc["checklist_answers"][0])
    extra["id"] = 23
    doc["checklist_answers"].append(extra)


def _mutate_unanswered_checklist_item(doc):
    doc["checklist_answers"][7]["status"] = "PENDING"


def _mutate_empty_checklist_answer(doc):
    doc["checklist_answers"][3]["answer"] = "TBD"


def _mutate_finding_without_evidence(doc):
    doc["findings"][0]["evidence_paths"] = []


def _mutate_finding_without_severity(doc):
    del doc["findings"][1]["severity"]


def _mutate_finding_with_unknown_severity(doc):
    doc["findings"][2]["severity"] = "COSMETIC"


def _mutate_parameter_without_unit(doc):
    del doc["gate_parameter_recommendations"]["exact_binomial_gates"][0]["unit_of_n"]


def _mutate_parameter_with_blank_unit(doc):
    doc["gate_parameter_recommendations"]["exact_binomial_gates"][0]["unit_of_n"] = ""


def _mutate_selected_interface(doc):
    doc["selection_state"]["selected_interface_profile"] = "S1_label_bearing"


def _mutate_selected_positive_reference(doc):
    doc["selection_state"]["selected_positive_reference_checkpoint"] = (
        "some-checkpoint-revision")


def _mutate_frozen_state(doc):
    doc["authority_flags"]["frozen"] = True


def _mutate_execution_authorized(doc):
    doc["authority_flags"]["execution_authorized"] = True


def _mutate_state_string(doc):
    doc["state"] = "STUDY3_DRAFT_V0_2_FROZEN"


def _mutate_nonzero_counter(doc):
    doc["operation_counts"]["forward_passes"] = 1


def _mutate_nonzero_gpu_counter(doc):
    doc["operation_counts"]["gpu_jobs"] = 2


def _mutate_result_row(doc):
    doc["result_rows"].append({"gate": "I1a", "successes": 190, "n": 192})


def _mutate_bank_row(doc):
    doc["bank_rows"].append({"item_id": "K1-0001"})


def _mutate_seed(doc):
    doc["seeds"].append(20240101)


def _mutate_model_output(doc):
    doc["model_outputs"].append({"prompt": "...", "completion": "B"})


def _mutate_evidence_row(doc):
    doc["evidence_rows"].append({"artifact_id": "AR-9999"})


def _mutate_accept_with_blocking_finding(doc):
    doc["disposition"] = "STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED"
    doc["required_changes_exist"] = False
    doc["findings"][0]["severity"] = "BLOCKING"


def _mutate_accept_with_unresolved_item(doc):
    doc["disposition"] = "STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED"
    doc["required_changes_exist"] = False
    for finding in doc["findings"]:
        finding["severity"] = "MINOR"
    doc["unresolved_items"]["items"][0]["state"] = "UNRESOLVED_BLOCKING"


def _mutate_reject_without_required_changes(doc):
    doc["required_changes_exist"] = False


def _mutate_next_action_routes_to_freeze(doc):
    doc["next_legal_action"]["routes_directly_to_freeze"] = True


def _mutate_next_action_routes_to_execution(doc):
    doc["next_legal_action"]["routes_directly_to_execution"] = True


def _mutate_next_action_id_is_freeze(doc):
    doc["next_legal_action"]["action_id"] = "FREEZE_STUDY3_PROTOCOL"


def _mutate_od2_adopted(doc):
    for decision in doc["operator_decisions"]["decisions"]:
        if decision["id"] == "OD2":
            decision["adopted_by_this_round"] = True


def _mutate_drop_od5(doc):
    doc["operator_decisions"]["decisions"] = [
        d for d in doc["operator_decisions"]["decisions"] if d["id"] != "OD5"]


def _mutate_unknown_inconsistency_status(doc):
    doc["cross_artifact_consistency"]["candidate_inconsistencies"][0][
        "status"] = "PROBABLY_FINE"


def _mutate_reviewer_wrote_the_design(doc):
    doc["reviewer_independence"]["reviewer_wrote_the_reviewed_design"] = True


def _mutate_independence_waived(doc):
    doc["reviewer_independence"]["does_not_import_design_statistics"] = False


def _mutate_artifact_hash(doc):
    doc["reviewed_artifact_identities"][0]["sha256"] = "0" * 64


def _mutate_review_object_modified(doc):
    doc["review_object_is_unmodified"] = False


def _mutate_missing_audit_target(doc):
    del doc["mandatory_audit_answers"]["5.5_i3_robustness_and_paired_equivalence"]


def _mutate_drop_multiplicity_graph(doc):
    del doc["multiplicity_decision"]["multiplicity_decision_graph"]


def _mutate_drop_null_alternative_set(doc):
    del doc["multiplicity_decision"]["formal_null_alternative_sets"][
        "development_selection"]


def _mutate_unregistered_optimisation(doc):
    del doc["paired_method_decision"]["optimisation_registration"]["tolerance"]


def _mutate_nonzero_projected_forward_passes(doc):
    doc["projected_operation_accounting"]["totals"][
        "forward_passes_executed_this_round"] = 810240


def _mutate_drop_a_work_stream(doc):
    del doc["projected_operation_accounting"]["work_streams"]["S4_diagnostic"]


MUTATIONS = [
    ("unknown disposition", _mutate_unknown_disposition),
    ("fewer than 22 checklist answers", _mutate_drop_a_checklist_item),
    ("more than 22 checklist answers", _mutate_add_a_checklist_item),
    ("unanswered checklist item", _mutate_unanswered_checklist_item),
    ("checklist item with no substantive answer", _mutate_empty_checklist_answer),
    ("finding with no evidence paths", _mutate_finding_without_evidence),
    ("finding with no severity", _mutate_finding_without_severity),
    ("finding with an unknown severity", _mutate_finding_with_unknown_severity),
    ("binding parameter with no unit", _mutate_parameter_without_unit),
    ("binding parameter with a blank unit", _mutate_parameter_with_blank_unit),
    ("selected interface profile", _mutate_selected_interface),
    ("selected positive reference", _mutate_selected_positive_reference),
    ("frozen state", _mutate_frozen_state),
    ("execution authorized", _mutate_execution_authorized),
    ("frozen state string", _mutate_state_string),
    ("non-zero forward-pass counter", _mutate_nonzero_counter),
    ("non-zero GPU counter", _mutate_nonzero_gpu_counter),
    ("a result row", _mutate_result_row),
    ("a bank row", _mutate_bank_row),
    ("a seed", _mutate_seed),
    ("a model output", _mutate_model_output),
    ("an evidence row", _mutate_evidence_row),
    ("accepted as specified with a blocking finding",
     _mutate_accept_with_blocking_finding),
    ("accepted as specified with an unresolved item",
     _mutate_accept_with_unresolved_item),
    ("rejection claiming no required changes",
     _mutate_reject_without_required_changes),
    ("next action routing to freeze", _mutate_next_action_routes_to_freeze),
    ("next action routing to execution", _mutate_next_action_routes_to_execution),
    ("next action id naming a freeze", _mutate_next_action_id_is_freeze),
    ("OD2 adopted by the review", _mutate_od2_adopted),
    ("OD5 missing", _mutate_drop_od5),
    ("unknown candidate-inconsistency status",
     _mutate_unknown_inconsistency_status),
    ("reviewer wrote the reviewed design", _mutate_reviewer_wrote_the_design),
    ("independence waived", _mutate_independence_waived),
    ("wrong reviewed artifact hash", _mutate_artifact_hash),
    ("review object recorded as modified", _mutate_review_object_modified),
    ("missing mandatory audit target", _mutate_missing_audit_target),
    ("missing multiplicity decision graph", _mutate_drop_multiplicity_graph),
    ("missing formal null/alternative set", _mutate_drop_null_alternative_set),
    ("unregistered nuisance optimisation", _mutate_unregistered_optimisation),
    ("non-zero projected forward passes",
     _mutate_nonzero_projected_forward_passes),
    ("missing projected work stream", _mutate_drop_a_work_stream),
]


@pytest.mark.parametrize("label,mutate",
                         MUTATIONS,
                         ids=[m[0].replace(" ", "_") for m in MUTATIONS])
def test_negative_mutation_battery_rejects_each_corrupted_review(
        label, mutate, review, schema):
    """Requirement 13: every fail-closed rule must actually be able to fail."""
    corrupted = copy.deepcopy(review)
    mutate(corrupted)
    assert corrupted != review, (
        "mutation %r did not change the document; the test would be vacuous"
        % label)

    schema_rejected = not _matches(corrupted, schema)
    guard_rejected = not _guards_accept(corrupted)

    assert schema_rejected or guard_rejected, (
        "a review corrupted with %r was accepted; the fail-closed rule for it "
        "does not exist" % label)


def _guards_accept(doc) -> bool:
    """Re-run the structural guards that live outside the schema."""
    try:
        test_exactly_the_twenty_two_packet_checklist_items_are_answered(doc)
        test_acceptance_as_specified_is_impossible_while_anything_is_unresolved(doc)
        test_every_finding_carries_a_stable_id_severity_and_evidence(doc)
        test_every_candidate_inconsistency_receives_exactly_one_status(doc)
        test_every_operation_counter_is_zero(doc)
        test_no_prohibited_authority_flag_is_set(doc)
        test_no_results_banks_seeds_model_outputs_or_evidence_rows(doc)
        test_the_review_selects_no_interface_and_no_model(doc)
        test_od2_remains_operator_controlled_and_no_decision_is_adopted(doc)
        test_required_changes_cannot_route_to_freeze_or_execution(doc)
        test_every_recommended_parameter_declares_the_unit_of_its_sample_size(doc)
        test_the_review_declares_its_own_independence(doc)
        test_the_review_object_is_recorded_as_unmodified(doc)
        test_the_projection_reports_zero_executed_operations(doc)
        test_reviewed_artifact_identities_bind_the_review_to_exact_bytes(doc)
    except (AssertionError, KeyError, IndexError, TypeError):
        return False
    except pytest.skip.Exception:
        return False
    return True


def test_the_unmutated_review_passes_every_structural_guard(review):
    """Requirement 14, from the other direction: the battery is not trivially
    rejecting everything."""
    assert _guards_accept(copy.deepcopy(review))


# --------------------------------------------------------------------------
# Review-object integrity
# --------------------------------------------------------------------------

def test_the_review_did_not_edit_the_review_object(review):
    """The reviewer may record a defect in the design test; never repair it.

    ``tests/test_study3_design.py`` is part of what was reviewed, and finding
    S3MR-009 records that it entrenches an insufficient discordance grid. That
    finding is only meaningful if the file still contained the defect **at the
    moment the review was published**.

    This is asserted at ``REVIEW_COMMIT``, not at ``HEAD``. The reviewer was
    forbidden from repairing the review object; a later *operator amendment*
    round is explicitly required to repair it. Asserting against ``HEAD`` would
    therefore convert an obligation into a violation.
    """
    _require_history(REVIEWED_COMMIT, REVIEW_COMMIT)
    identities = {row["path"]: row for row in
                  review["reviewed_artifact_identities"]}
    design_test = identities[DESIGN_TEST_PATH]
    reviewed = _blob_at(REVIEWED_COMMIT, DESIGN_TEST_PATH)
    assert hashlib.sha256(reviewed).hexdigest() == design_test["sha256"], (
        "the reviewed bytes of %s do not match the identity the review "
        "recorded" % DESIGN_TEST_PATH)
    at_review = _blob_at(REVIEW_COMMIT, DESIGN_TEST_PATH)
    assert at_review == reviewed, (
        "%s changed between the reviewed commit and the review commit; the "
        "review object must not be repaired by its reviewer" % DESIGN_TEST_PATH)


# --------------------------------------------------------------------------
# Publication-state checks
#
# These carry decision authority: publication is conditional on them, so they
# live in a committed test rather than in an operator-side helper script.
# --------------------------------------------------------------------------

STARTING_COMMIT = REVIEWED_COMMIT

CHANGED_PATH_WHITELIST = frozenset([
    # the eight new files
    "studies/study3/reviews/v0_2_independent_methods_review.md",
    "studies/study3/reviews/v0_2_independent_methods_review.json",
    "studies/study3/reviews/v0_2_independent_methods_review.schema.json",
    "studies/study3/analysis/independent_methods_recalculation.py",
    "studies/study3/analysis/independent_methods_recalculation_tables.json",
    "tests/test_study3_methods_review.py",
    "studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md",
    "studies/study3/methods_review_receipt_v0_2.json",
    # the nine modifiable routing and registry surfaces
    "README.md",
    "studies/README.md",
    "studies/study3/README.md",
    "studies/study3/NEXT_THREAD_HANDOFF.md",
    "reports/current_status.md",
    "docs/decision_log.md",
    "docs/run_log.md",
    "paper/methods_ledger.md",
    "paper/artifact_index.csv",
])

PROTECTED_FROM_THIS_ROUND = (
    "paper/evidence_ledger.csv",
    "paper/limitations_ledger.md",
    "paper/claim_evidence_matrix.md",
    "docs/phase1_0d_protected_bytes.json",
    "docs/phase1_0d_rv2_protected_bytes.json",
    "tests/test_study3_design.py",
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
    "studies/study3/analysis/design_statistics.py",
    "studies/study3/analysis/design_statistics_tables.json",
    "studies/study3/analysis/independent_methods_review_packet.md",
    "studies/study3/analysis/study2_to_study3_design_traceability.md",
    "studies/study3/references/methods_sources.md",
    "studies/study3/references/positive_reference_dossier.md",
    "studies/study3/reviews/v0_1_operator_review.md",
    "studies/study3/design_receipt.json",
    "studies/study3/design_receipt_v0_2.json",
    "requirements.lock.txt",
)


def _historical_changed_paths():
    completed = subprocess.run(
        ["git", "-C", REPO_ROOT, "diff", "--name-only",
         STARTING_COMMIT, REVIEW_COMMIT],
        capture_output=True)
    assert completed.returncode == 0, completed.stderr.decode()
    return [line for line in completed.stdout.decode("utf-8").splitlines()
            if line.strip()]


def test_the_changed_path_set_is_inside_the_authority_whitelist():
    """The review round was capped at 17 paths: 8 added, 9 modifiable.

    This is a statement about the *review round*, so it compares the reviewed
    commit with the review commit. Comparing against ``HEAD`` would fold every
    later authorised round into the review round's ceiling.
    """
    _require_history(STARTING_COMMIT, REVIEW_COMMIT)
    changed = _historical_changed_paths()
    outside = sorted(set(changed) - CHANGED_PATH_WHITELIST)
    assert not outside, "changed paths outside the whitelist: %s" % outside
    assert len(changed) == 17, (
        "%d paths changed; the review round was capped at 17" % len(changed))


def test_no_protected_path_was_touched_by_this_round():
    """Recording a defect is permitted; repairing the object is not.

    Scoped to the review round, between the reviewed commit and the review
    commit, for the same reason as the whitelist check above.
    """
    _require_history(STARTING_COMMIT, REVIEW_COMMIT)
    changed = set(_historical_changed_paths())
    for path in PROTECTED_FROM_THIS_ROUND:
        assert path not in changed, "%s must not be modified by this round" % path
    for path in changed:
        assert not path.startswith("studies/study1/"), path
        assert not path.startswith("studies/study2/"), path
        assert not path.startswith(".github/"), path
        assert not path.startswith("infra/"), path


def test_the_artifact_index_is_unique_contiguous_and_binds_real_blobs():
    """AR ids must be unique and gapless, and each digest must be a real blob.

    Evaluated at ``REVIEW_COMMIT``. The index grows with every later authorised
    round, so pinning its tail to ``AR-0221`` is a fact about the review round,
    not about ``HEAD``.
    """
    _require_history(REVIEW_COMMIT)
    payload = _blob_at(REVIEW_COMMIT, "paper/artifact_index.csv").decode("utf-8")
    lines = [line for line in payload.splitlines() if line.strip()]
    header = lines[0].split(",")
    assert header[0] == "artifact_id"
    columns = {name: index for index, name in enumerate(header)}

    ids = []
    rows_by_id = {}
    for line in lines[1:]:
        fields = line.split(",")
        assert len(fields) == len(header), line
        ids.append(fields[columns["artifact_id"]])
        rows_by_id[fields[columns["artifact_id"]]] = fields

    assert len(ids) == len(set(ids)), "duplicate artifact ids"
    numbers = [int(value.split("-")[1]) for value in ids]
    assert numbers == sorted(numbers), "artifact ids are not in order"
    assert numbers == list(range(numbers[0], numbers[0] + len(numbers))), (
        "artifact ids are not contiguous")
    assert ids[-1] == "AR-0221", (
        "the review round must end the index at AR-0221")

    for number in range(212, 222):
        artifact_id = "AR-%04d" % number
        assert artifact_id in rows_by_id, "%s is not registered" % artifact_id
        fields = rows_by_id[artifact_id]
        location = fields[columns["storage_location"]]
        assert location.startswith("repo:"), location
        path = location[len("repo:"):]
        blob = _blob_at(REVIEW_COMMIT, path)
        assert hashlib.sha256(blob).hexdigest() == fields[columns["sha256"]], (
            "%s digest does not match the committed blob for %s"
            % (artifact_id, path))
        assert len(blob) == int(fields[columns["bytes"]]), (
            "%s byte count does not match the committed blob for %s"
            % (artifact_id, path))
        usage = fields[columns["paper_usage"]]
        assert usage.endswith("_not_result"), (
            "%s must not be classified as a scientific result" % artifact_id)


def test_the_earlier_registrations_were_not_altered(review):
    """D39, M-27 and AR-0196..AR-0211 belong to the round under review."""
    _require_history(REVIEW_COMMIT)
    payload = _blob_at(REVIEW_COMMIT, "paper/artifact_index.csv").decode("utf-8")
    lines = [line for line in payload.splitlines() if line.strip()]
    for number in range(196, 212):
        artifact_id = "AR-%04d" % number
        matches = [line for line in lines
                   if line.split(",")[0] == artifact_id]
        assert len(matches) == 1, artifact_id
        assert "STUDY3-DESIGN" in matches[0], (
            "%s changed phase; prior registrations are immutable here"
            % artifact_id)

    decisions = _blob_at(REVIEW_COMMIT, "docs/decision_log.md").decode("utf-8")
    assert decisions.count("\n## D39 - ") == 1
    assert decisions.count("\n## D40 - ") == 1
    methods = _blob_at(REVIEW_COMMIT, "paper/methods_ledger.md").decode("utf-8")
    assert methods.count("\n## M-27 - ") == 1
    assert methods.count("\n## M-28 - ") == 1


def test_the_evidence_ledger_is_untouched_at_ev_0016(receipt):
    """A methods review produces no evidence row, by construction.

    Asserted at ``REVIEW_COMMIT`` against the receipt that recorded it, and again
    at ``HEAD``: the ledger is protected from every subsequent round as well, so
    both readings must agree byte for byte.
    """
    _require_history(REVIEW_COMMIT)
    payload = _blob_at(REVIEW_COMMIT, "paper/evidence_ledger.csv")
    assert payload == _committed_bytes("paper/evidence_ledger.csv"), (
        "paper/evidence_ledger.csv changed after the review round")
    recorded = receipt["protected_state"]["evidence_ledger"]
    assert len(payload) == recorded["bytes"]
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
    rows = [line for line in payload.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) - 1 == recorded["data_rows"]
    assert rows[-1].split(",")[0] == "EV-0016"


def test_both_protected_rollups_are_unchanged(receipt):
    """The two Phase 1.0D rollup records are frozen state from earlier rounds.

    Read at ``REVIEW_COMMIT`` and compared with ``HEAD``: these are protected
    from every round, so a later amendment may not move them either.
    """
    _require_history(REVIEW_COMMIT)
    for recorded in receipt["protected_state"]["protected_rollups"]:
        payload = _blob_at(REVIEW_COMMIT, recorded["path"])
        assert payload == _committed_bytes(recorded["path"]), (
            "%s changed after the review round" % recorded["path"])
        assert len(payload) == recorded["bytes"], recorded["path"]
        assert hashlib.sha256(payload).hexdigest() == recorded["sha256"], (
            recorded["path"])
        document = json.loads(payload.decode("utf-8"))
        assert document["rollup_sha256"] == recorded["rollup_sha256"]
        assert document["file_count"] == recorded["file_count"]
        assert document["file_count"] == len(document["files"])


def test_the_receipt_binds_every_new_artifact_and_omits_its_own_hash(receipt):
    """A receipt that hashed itself would be either stale or circular."""
    _require_history(REVIEWED_COMMIT, REVIEW_COMMIT)
    assert receipt["new_artifact_identities"]["self_hash_in_body"] is False
    body = json.dumps(receipt, sort_keys=True)
    own = hashlib.sha256(_blob_at(REVIEW_COMMIT, RECEIPT_PATH)).hexdigest()
    assert own not in body, "the receipt contains its own digest"

    artifacts = receipt["new_artifact_identities"]["artifacts"]
    assert [row["artifact_id"] for row in artifacts] == [
        "AR-%04d" % number for number in range(212, 219)]
    # New artifacts of the review round are read at the commit that created
    # them; reviewed artifacts are read at the commit that was reviewed.
    for row in artifacts:
        payload = _blob_at(REVIEW_COMMIT, row["path"])
        assert len(payload) == row["bytes"], row["path"]
        assert hashlib.sha256(payload).hexdigest() == row["sha256"], row["path"]

    for row in receipt["reviewed_artifact_identities"]:
        payload = _blob_at(REVIEWED_COMMIT, row["path"])
        assert len(payload) == row["bytes"], row["path"]
        assert hashlib.sha256(payload).hexdigest() == row["sha256"], row["path"]


def test_the_receipt_and_the_review_agree_on_the_disposition(review, receipt):
    assert receipt["disposition"] == review["disposition"]
    assert receipt["state"] == review["state"]
    assert receipt["required_changes_exist"] == review["required_changes_exist"]
    assert (receipt["remaining_authority"]["next_legal_action"]
            == review["next_legal_action"]["action_id"])


def test_the_receipt_grants_no_authority(receipt):
    """Every authority flag in the receipt must be negative."""
    remaining = receipt["remaining_authority"]
    assert remaining["this_round_grants"] == "none"
    for key, value in remaining.items():
        if key.endswith("_authorized"):
            assert value is False, "%s is set" % key
    for key, value in receipt["zero_operation_attestation"].items():
        if isinstance(value, int) and not isinstance(value, bool):
            assert value == 0, "%s is %r" % (key, value)
    assert receipt["publication"]["force_push_used"] is False
    assert receipt["publication"]["github_actions_used"] is False
    assert receipt["publication"]["merge_or_rebase_used"] is False


def test_no_new_file_declares_an_operation_or_an_authority():
    """A static scan of the round's own new bytes for prohibited state."""
    prohibited = (
        re.compile(r'"(frozen|freeze_authorized|execution_authorized|'
                   r'bank_construction_authorized|seed_draw_authorized|'
                   r'interface_selection_authorized|'
                   r'positive_reference_selection_authorized|'
                   r'azure_gpu_authorized|approved_for_freeze|'
                   r'approved_for_execution)"\s*:\s*true'),
        re.compile(r'"(forward_passes|generations|weight_loads|'
                   r'tokenizer_constructions|model_downloads|gpu_jobs|'
                   r'bank_rows_created|seeds_drawn|activation_extractions|'
                   r'probe_fits|patching_operations|ablation_operations|'
                   r'lens_operations|confirmation_accesses|'
                   r'gate_evaluations_on_models)"\s*:\s*(?!0\b)\d+'),
    )
    _require_history(REVIEW_COMMIT)
    for path in ("studies/study3/reviews/v0_2_independent_methods_review.json",
                 "studies/study3/methods_review_receipt_v0_2.json",
                 "studies/study3/analysis/"
                 "independent_methods_recalculation_tables.json"):
        text = _blob_at(REVIEW_COMMIT, path).decode("utf-8")
        for pattern in prohibited:
            match = pattern.search(text)
            assert match is None, "%s declares %r" % (path, match.group(0))
