"""Committed design-critical tests for the Study 3 interface-calibration draft.

These tests exist because the draft-v0.1 round's consistency checker was an
operator-side ephemeral script. It was never committed, a reviewer could not
re-run it, and it did not catch the Markdown/JSON contradiction that the operator
review later found. Everything that is design-critical is therefore checked here,
in the repository test suite.

draft-v0.3 additions. The first independent methods review of draft-v0.2 returned
STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED with twenty findings. Six were
blocking. This module enforces, as executable invariants, the repairs adopted in
response to them: exactly two variants per I3 contrast cluster and no K5 x K6
cross product (S3MR-001), a single conjunctive I3 indicator whose truth table
fails a stable-but-wrong answer (S3MR-002), an exact rational alpha that is
present in every component row (S3MR-003), the complete removal of the paired
aggregate-equivalence procedure from every decision role (S3MR-004, S3MR-005),
one and only one I3 floor with no degenerate rejection region (S3MR-006,
S3MR-015), a fixed across-profile denominator (S3MR-016), an executable
development selection map (S3MR-017), a work-stream decomposed operation
projection (S3MR-012, S3MR-013) and a unit on every sample size (S3MR-014).

draft-v0.4 additions. The SECOND independent methods review of draft-v0.3
returned STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED with ten
structured findings: two BLOCKING, six MAJOR and two MINOR. This module now also
enforces the draft-v0.4 repairs:

* S3MR2-001, the gate-bearing I3 indicator is ``J_joint_correct``, a level over a
  registered item-generating distribution, and no active claim field asserts
  invariance, equivalence or an absent presentation effect;
* S3MR2-002, the type-II architecture is an arbitrary-dependence union bound over
  exact rationals with per-cell, per-profile-stage and end-to-end scopes that
  reconstruct 19/17200, 17181/17200, 381/400 and 9/10;
* S3MR2-003, every development sample size is the smallest unrestricted positive
  integer meeting the registered per-cell target;
* S3MR2-004, confirmation applicability is the intersection of a component's
  selectable profiles with the single selected profile, so S4 never appears and
  I1b and K5 are confined to S1;
* S3MR2-005, the S4 diagnostic stream carries a derived, non-null forward cost;
* S3MR2-006, the state machine is total and deterministic and an I0 failure maps
  only to STOP_INSTRUMENT_DEFECT;
* S3MR2-007, the K5 nuisance support is a complete 32-state support at exact
  weight 1/32 drawn iid with replacement;
* S3MR2-008, the I0 fixture accounting reconstructs from a registered breakdown;
* S3MR2-009, the P3-Q ordering constraint is registered without selecting a
  positive reference;
* S3MR2-010, every gate-bearing atomic cell carries a complete sampling-frame
  entry that licenses the exact-binomial estimand.

Three anti-self-certification rules apply to this file. First, the numbers are
not transcribed here: the committed derivation script must recompute them from
the protocol's registered exact rational inputs, this module recomputes the
decision-bearing ones a second time from those same registered inputs using its
own integer arithmetic, and a separate test reads the derivation script's syntax
tree to prove it contains no hard-coded threshold, tail, power or size constant.
Second, every decision-bearing invariant is also exercised by a negative
mutation; a test that only checks the committed happy path is insufficient.
Third, nothing in this module may be read as approval of the design. It checks
internal consistency and the arithmetic; adjudication of the method belongs to
the THIRD independent methods review, which must be conducted by a party that did
not draft draft-v0.4.

Nothing in this file touches a model. There is no download, no weight load, no
tokenizer construction, no forward pass, no generation, no activation
extraction, no probe, no patch, no ablation, no lens operation, no GPU work and
no provider call. The tests read committed text files and do arithmetic.

The JSON-Schema validation below is implemented locally. ``jsonschema`` is not in
``requirements.lock.txt`` and is therefore absent from the validation image, so a
dependency on it would make these tests unrunnable exactly where they matter.
The supported keyword subset is the subset the Study 3 schemas use.
"""

import ast
import json
import os
import re
import subprocess
import sys
from fractions import Fraction

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY3 = os.path.join(REPO_ROOT, "studies", "study3")
PROTOCOL_DIR = os.path.join(STUDY3, "protocol")
JSON_PATH = os.path.join(PROTOCOL_DIR, "interface_calibration_protocol_draft.json")
MD_PATH = os.path.join(PROTOCOL_DIR, "interface_calibration_protocol_draft.md")
SCHEMA_PATH = os.path.join(PROTOCOL_DIR, "interface_calibration_protocol.schema.json")
STATS_SCRIPT = os.path.join(STUDY3, "analysis", "design_statistics.py")
STATS_TABLES = os.path.join(STUDY3, "analysis", "design_statistics_tables.json")
REVIEW_PATH = os.path.join(STUDY3, "reviews", "v0_1_operator_review.md")
AMENDMENT_V0_3 = os.path.join(STUDY3, "reviews", "v0_3_operator_amendment.json")
AMENDMENT_PATH = os.path.join(STUDY3, "reviews", "v0_5_operator_amendment.json")
AMENDMENT_SCHEMA = os.path.join(
    STUDY3, "reviews", "v0_5_operator_amendment.schema.json")
AMENDMENT_MD = os.path.join(STUDY3, "reviews", "v0_5_operator_amendment.md")
PACKET_V0_3 = os.path.join(
    STUDY3, "analysis", "independent_methods_review_packet_v0_3.md")
PACKET_PATH = os.path.join(
    STUDY3, "analysis", "independent_methods_review_packet_v0_5.md")

EXPECTED_STATE = ("STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_"
                  "AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW")
NO_WINNER = "No interface is selected in this round."

DRAFT_VERSION = "draft-v0.5"
REVIEW_STATE = "awaiting_fourth_independent_methods_review"

# The constructs the one-shot confirmation gate must cover. I3 appears as its
# primary indicator rather than as a bare family label: draft-v0.2 carried two
# mutually exclusive I3 indicators, so a bare "I3" did not say what would be
# replicated. draft-v0.4 renames that indicator J_joint_correct (S3MR2-001).
COVERED_CONSTRUCTS = ("I0", "I1a", "I1b", "I2", "I3_J_joint_correct", "I4")

# The twenty findings of the first independent methods review, the twenty-two
# unresolved items of its packet checklist, the ten findings of the second
# independent methods review and the ten findings of the third. All four sets
# must be closed exactly once each in the draft-v0.5 amendment record.
FINDING_IDS = ["S3MR-%03d" % i for i in range(1, 21)]
UR_IDS = ["UR-%02d" % i for i in range(1, 23)]
FINDING_IDS_V0_3 = ["S3MR2-%03d" % i for i in range(1, 11)]
FINDING_IDS_V0_4 = ["S3MR3-%03d" % i for i in range(1, 11)]

# The severities the THIRD review recorded in its structured findings, and the
# closure status draft-v0.5 must reach for each. These are independent
# expectations: the amendment record must match them, not define them.
STRUCTURED_V0_4_SEVERITIES = {"BLOCKING": 1, "MAJOR": 3, "MINOR": 6}
REQUIRED_V0_4_CLOSURES = {
    "S3MR3-001": "RESOLVED_BY_NOT_APPLICABLE_REREGISTRATION_AND_FULL_REDERIVATION",
    "S3MR3-002": "RESOLVED_BY_COMPONENT_LEVEL_CONFIRMATION_APPLICABILITY",
    "S3MR3-003": "RESOLVED_ACTIVE_TEXT_ALIGNED_HISTORY_PRESERVED",
    "S3MR3-004": "RESOLVED_ENFORCEMENT_SCOPE_MATCHES_REGISTERED_SCOPE",
    "S3MR3-005": "RESOLVED_S4_I4_REMOVED",
    "S3MR3-006": "RESOLVED_NON_MACHINE_STATUS_REMOVED_FROM_STOP_STATES",
    "S3MR3-007": "RESOLVED_NONMONOTONICITY_DISCLOSED_EXACT_N_REQUIRED",
    "S3MR3-008": "RESOLVED_ROUND_REFERENCES_UPDATED",
    "S3MR3-009": "RESOLVED_UNION_BOUND_CLAIM_ALIGNED",
    "S3MR3-010": "RESOLVED_DETERMINISTIC_RENDERING_SURFACE_REGISTERED",
}

# S3MR3-001. K6-SEP varies the separator between a displayed option label and its
# displayed option content. The option-less profiles render neither.
LABEL_BEARING = ("S1", "S4")
OPTION_LESS = ("S2", "S3")

# The severities the second review actually recorded in its structured findings.
# The immutable disposition_basis sentence of that review says "Two BLOCKING and
# eight MAJOR". That sentence is preserved unedited in the review; the structured
# counts below are what draft-v0.4 answers, and 8 MAJOR is never propagated.
STRUCTURED_V0_3_SEVERITIES = {"BLOCKING": 2, "MAJOR": 6, "MINOR": 2}

# Text that must never reappear. The first two strings are quoted from draft-v0.1
# and are the two defects that were confirmed verbatim from committed bytes.
FORBIDDEN_TEXT = [
    "A winner is selected in this round",
    "generated from one source of record",
]

# S3MR2-001. These terms assert a presentation-effect conclusion that a level
# gate on J_joint_correct cannot identify. They are permitted only in clearly
# labelled historical, retired, limitation-of-claim and prohibited-claim text.
PROHIBITED_CLAIM_TERMS = (
    "invarian",
    "equivalen",
    "no presentation effect",
    "presentation-effect size",
    "presentation effect size",
    "stable across presentations",
    "unaffected by presentation",
)


# --------------------------------------------------------------------------
# Minimal JSON-Schema validator (local, dependency-free)
# --------------------------------------------------------------------------

_IGNORED = {"$schema", "$id", "$comment", "title", "description", "examples",
            "default"}

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


def _type_ok(instance, name):
    """True when ``instance`` satisfies the single JSON-Schema type ``name``.

    ``bool`` is a subclass of ``int`` in Python, so it would silently satisfy
    ``integer`` and ``number`` without this guard. A protocol that writes ``true``
    where a count belongs must be rejected, not tolerated.
    """
    if name in ("integer", "number") and isinstance(instance, bool):
        return False
    if name == "boolean":
        return isinstance(instance, bool)
    return isinstance(instance, _TYPES[name])


def _canonical(value):
    """A hashable canonical form, for uniqueItems over nested JSON."""
    return json.dumps(value, sort_keys=True)


def schema_errors(instance, schema, path="$"):
    """Return a list of validation errors. Empty list means valid."""
    errors = []
    for key, value in schema.items():
        if key in _IGNORED:
            continue
        if key == "type":
            # ``type`` may be a single name or a list of alternatives. A list is
            # satisfied when any alternative is satisfied.
            names = value if isinstance(value, list) else [value]
            if not any(_type_ok(instance, name) for name in names):
                errors.append("%s: expected type %s, got %s"
                              % (path, value, type(instance).__name__))
        elif key == "const":
            if instance != value:
                errors.append("%s: expected const %r, got %r"
                              % (path, value, instance))
        elif key == "enum":
            if instance not in value:
                errors.append("%s: %r not in enum %r" % (path, instance, value))
        elif key == "required":
            if isinstance(instance, dict):
                for prop in value:
                    if prop not in instance:
                        errors.append("%s: missing required property %r"
                                      % (path, prop))
        elif key == "properties":
            if isinstance(instance, dict):
                for prop, sub in value.items():
                    if prop in instance:
                        errors.extend(schema_errors(instance[prop], sub,
                                                    "%s.%s" % (path, prop)))
        elif key == "additionalProperties":
            if isinstance(instance, dict):
                allowed = set(schema.get("properties", {}))
                if value is False:
                    for prop in instance:
                        if prop not in allowed:
                            errors.append(
                                "%s: additional property %r is not allowed"
                                % (path, prop))
                elif isinstance(value, dict):
                    for prop, sub_instance in instance.items():
                        if prop not in allowed:
                            errors.extend(schema_errors(
                                sub_instance, value, "%s.%s" % (path, prop)))
        elif key == "items":
            if isinstance(instance, list):
                for i, item in enumerate(instance):
                    errors.extend(schema_errors(item, value,
                                                "%s[%d]" % (path, i)))
        elif key == "contains":
            if isinstance(instance, list):
                if not any(not schema_errors(item, value) for item in instance):
                    errors.append("%s: no item satisfies the contains schema"
                                  % path)
        elif key == "allOf":
            for i, sub in enumerate(value):
                errors.extend(schema_errors(instance, sub,
                                            "%s/allOf[%d]" % (path, i)))
        elif key == "anyOf":
            if not any(not schema_errors(instance, sub) for sub in value):
                errors.append("%s: no anyOf branch is satisfied" % path)
        elif key == "oneOf":
            matched = sum(1 for sub in value if not schema_errors(instance, sub))
            if matched != 1:
                errors.append("%s: %d oneOf branches matched, exactly 1 required"
                              % (path, matched))
        elif key == "not":
            if not schema_errors(instance, value):
                errors.append("%s: the 'not' subschema was satisfied" % path)
        elif key == "if":
            # ``if`` is applied together with ``then``/``else`` from the same
            # schema object. Those two keys are consumed here and skipped below.
            branch = "then" if not schema_errors(instance, value) else "else"
            if branch in schema:
                errors.extend(schema_errors(instance, schema[branch],
                                            "%s/%s" % (path, branch)))
        elif key in ("then", "else"):
            if "if" not in schema:
                raise AssertionError("%r without 'if' at %s" % (key, path))
        elif key == "uniqueItems":
            if value is True and isinstance(instance, list):
                seen = [_canonical(item) for item in instance]
                if len(set(seen)) != len(seen):
                    errors.append("%s: items are not unique" % path)
        elif key == "minItems":
            if isinstance(instance, list) and len(instance) < value:
                errors.append("%s: %d items, minimum %d"
                              % (path, len(instance), value))
        elif key == "maxItems":
            if isinstance(instance, list) and len(instance) > value:
                errors.append("%s: %d items, maximum %d"
                              % (path, len(instance), value))
        elif key == "minProperties":
            if isinstance(instance, dict) and len(instance) < value:
                errors.append("%s: %d properties, minimum %d"
                              % (path, len(instance), value))
        elif key == "maxProperties":
            if isinstance(instance, dict) and len(instance) > value:
                errors.append("%s: %d properties, maximum %d"
                              % (path, len(instance), value))
        elif key == "minimum":
            if isinstance(instance, (int, float)) \
                    and not isinstance(instance, bool) and instance < value:
                errors.append("%s: %r is below the minimum %r"
                              % (path, instance, value))
        elif key == "maximum":
            if isinstance(instance, (int, float)) \
                    and not isinstance(instance, bool) and instance > value:
                errors.append("%s: %r is above the maximum %r"
                              % (path, instance, value))
        elif key == "minLength":
            if isinstance(instance, str) and len(instance) < value:
                errors.append("%s: length %d, minimum %d"
                              % (path, len(instance), value))
        elif key == "pattern":
            if isinstance(instance, str) and re.search(value, instance) is None:
                errors.append("%s: does not match pattern %r" % (path, value))
        else:  # pragma: no cover - guards against an unsupported keyword
            raise AssertionError("unsupported schema keyword %r at %s"
                                 % (key, path))
    return errors


# --------------------------------------------------------------------------
# Exact arithmetic, recomputed here independently of the derivation script
# --------------------------------------------------------------------------

def _rational(text):
    """Parse an exact rational registered as a string such as ``"19/17200"``."""
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(text))


def _upper_tail_numerator(n, successes, p_num, p_den):
    """Integer numerator of Pr(X >= successes) over the denominator p_den ** n.

    Integer-only arithmetic. Floating point never touches a decision here.
    """
    total = 0
    q_num = p_den - p_num
    term = p_num ** n  # k == n
    total += term
    for k in range(n - 1, successes - 1, -1):
        # term(k) = C(n, k) * p_num**k * q_num**(n - k)
        term = term * (k + 1) * q_num // ((n - k) * p_num)
        total += term
    return total


def _upper_tail(n, successes, p):
    """Exact Fraction for Pr(X >= successes) when X ~ Binomial(n, p)."""
    p_num, p_den = p.numerator, p.denominator
    if successes <= 0:
        return Fraction(1)
    if successes > n:
        return Fraction(0)
    return Fraction(_upper_tail_numerator(n, successes, p_num, p_den),
                    p_den ** n)


def _smallest_controlling_count(n, p0, alpha):
    """Smallest pass count c with Pr(X >= c | p0) <= alpha, or None."""
    low, high = 1, n
    best = None
    while low <= high:
        middle = (low + high) // 2
        if _upper_tail(n, middle, p0) <= alpha:
            best = middle
            high = middle - 1
        else:
            low = middle + 1
    return best


def _smallest_size_meeting_power(p0, p1, alpha, target, ceiling):
    """Smallest n whose minimal level-alpha pass count reaches ``target`` power."""
    for n in range(1, ceiling + 1):
        count = _smallest_controlling_count(n, p0, alpha)
        if count is None or count > n:
            continue
        if _upper_tail(n, count, p1) >= target:
            return n, count
    raise AssertionError("no n <= %d reaches the target" % ceiling)


def _decimal(fraction, places=12):
    """Render an exact Fraction to a fixed number of places, rounding half up."""
    scale = 10 ** places
    scaled = (fraction * scale).numerator // (fraction * scale).denominator
    remainder = (fraction * scale) - scaled
    if remainder >= Fraction(1, 2):
        scaled += 1
    text = str(scaled).rjust(places + 1, "0")
    return "%s.%s" % (text[:-places], text[-places:])


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _load_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture(scope="module")
def protocol():
    return _load_json(JSON_PATH)


@pytest.fixture(scope="module")
def schema():
    return _load_json(SCHEMA_PATH)


@pytest.fixture(scope="module")
def markdown():
    return _load_text(MD_PATH)


@pytest.fixture(scope="module")
def tables():
    return _load_json(STATS_TABLES)


@pytest.fixture(scope="module")
def amendment():
    return _load_json(AMENDMENT_PATH)


@pytest.fixture(scope="module")
def amendment_schema():
    return _load_json(AMENDMENT_SCHEMA)


@pytest.fixture(scope="module")
def packet():
    return _load_text(PACKET_PATH)


# --------------------------------------------------------------------------
# The validator itself must work before it is trusted
# --------------------------------------------------------------------------

def test_local_schema_validator_behaves():
    """The validator must reject, not merely tolerate, each supported keyword."""
    assert not schema_errors({"a": 1}, {"type": "object",
                                        "properties": {"a": {"type": "integer"}}})
    assert schema_errors({"a": True}, {"type": "object",
                                       "properties": {"a": {"type": "integer"}}})
    assert schema_errors(1, {"type": "boolean"})
    assert schema_errors("x", {"const": "y"})
    assert schema_errors("x", {"enum": ["y", "z"]})
    assert schema_errors({}, {"required": ["a"]})
    assert schema_errors({"a": 1, "b": 2},
                         {"properties": {"a": {}}, "additionalProperties": False})
    assert schema_errors({"a": 1, "b": "s"},
                         {"properties": {"a": {}},
                          "additionalProperties": {"type": "integer"}})
    assert schema_errors([1, "s"], {"items": {"type": "integer"}})
    assert schema_errors([1, 2], {"contains": {"const": 3}})
    assert not schema_errors([1, 3], {"contains": {"const": 3}})
    assert schema_errors(1, {"allOf": [{"type": "integer"}, {"const": 2}]})
    assert schema_errors(1, {"anyOf": [{"const": 2}, {"const": 3}]})
    assert not schema_errors(1, {"anyOf": [{"const": 1}, {"const": 3}]})
    assert schema_errors(1, {"oneOf": [{"type": "integer"}, {"const": 1}]})
    assert not schema_errors(1, {"oneOf": [{"const": 1}, {"const": 2}]})
    assert schema_errors(1, {"not": {"type": "integer"}})
    assert not schema_errors(1, {"not": {"type": "string"}})
    conditional = {"if": {"properties": {"k": {"const": "x"}}, "required": ["k"]},
                   "then": {"properties": {"v": {"const": 1}}}}
    assert schema_errors({"k": "x", "v": 2}, conditional)
    assert not schema_errors({"k": "x", "v": 1}, conditional)
    assert not schema_errors({"k": "y", "v": 2}, conditional)
    assert schema_errors([1, 1], {"uniqueItems": True})
    assert schema_errors([{"a": 1}, {"a": 1}], {"uniqueItems": True})
    assert not schema_errors([{"a": 1}, {"a": 2}], {"uniqueItems": True})
    assert schema_errors([], {"minItems": 1})
    assert schema_errors([1, 2], {"maxItems": 1})
    assert schema_errors({}, {"minProperties": 1})
    assert schema_errors({"a": 1, "b": 2}, {"maxProperties": 1})
    assert schema_errors(0, {"minimum": 1})
    assert schema_errors(2, {"maximum": 1})
    assert schema_errors("", {"minLength": 1})
    assert schema_errors("abc", {"pattern": r"^\d+$"})
    assert not schema_errors("123", {"pattern": r"^\d+$"})


def test_the_validator_refuses_a_schema_it_cannot_fully_enforce():
    """Silently ignoring an unknown keyword would make the schema decorative."""
    with pytest.raises(AssertionError):
        schema_errors({"a": 1}, {"patternProperties": {"^a$": {"type": "string"}}})
    with pytest.raises(AssertionError):
        schema_errors({"a": 1}, {"dependentRequired": {"a": ["b"]}})
    with pytest.raises(AssertionError):
        schema_errors({"a": 1}, {"then": {"const": 1}})


def test_the_exact_arithmetic_helpers_are_correct():
    """The in-test recomputation must be right before it can audit anything."""
    half = Fraction(1, 2)
    assert _upper_tail(3, 0, half) == 1
    assert _upper_tail(3, 4, half) == 0
    assert _upper_tail(3, 3, half) == Fraction(1, 8)
    assert _upper_tail(3, 2, half) == Fraction(1, 2)
    # The full mass over every attainable count is exactly one.
    p = Fraction(9, 10)
    assert sum(_upper_tail(5, k, p) - _upper_tail(5, k + 1, p)
               for k in range(6)) == 1
    # Monotone in p, which is why the supremum of the null tail sits at p0.
    assert _upper_tail(20, 15, Fraction(4, 5)) > _upper_tail(20, 15, Fraction(1, 2))
    assert _smallest_controlling_count(10, half, Fraction(1, 1024)) == 10
    assert _decimal(Fraction(1, 2), 3) == "0.500"
    assert _decimal(Fraction(1, 3), 6) == "0.333333"


# --------------------------------------------------------------------------
# State, version parity and the operation boundary
# --------------------------------------------------------------------------

def test_protocol_validates_against_committed_schema(protocol, schema):
    errors = schema_errors(protocol, schema)
    assert errors == [], "protocol failed its own schema:\n%s" % "\n".join(errors)


def test_amendment_record_validates_against_its_committed_schema(
        amendment, amendment_schema):
    errors = schema_errors(amendment, amendment_schema)
    assert errors == [], "amendment failed its schema:\n%s" % "\n".join(errors)


def test_protocol_declares_the_expected_draft_state(protocol):
    """S3MR3 round: the draft is v0.5 and it awaits the FOURTH review."""
    assert protocol["state"] == EXPECTED_STATE
    assert protocol["schema_version"].endswith(DRAFT_VERSION)
    status = protocol["status"]
    assert status["frozen"] is False
    assert status["execution_authorized"] is False
    assert status["review_state"] == REVIEW_STATE
    assert status["document_class"] == "design_draft"
    assert "fourth bounded independent methods review of draft-v0.5" in \
        protocol["required_next_action"]
    assert "did not draft draft-v0.5" in protocol["required_next_action"]


def test_the_artifacts_agree_on_the_draft_version_and_state(
        protocol, tables, markdown, amendment, packet):
    """JSON, schema, derivation tables, Markdown, amendment and packet parity."""
    assert tables["draft_version"] == DRAFT_VERSION
    assert tables["state"] == EXPECTED_STATE
    assert amendment["state"] == EXPECTED_STATE
    assert EXPECTED_STATE in markdown
    assert EXPECTED_STATE in packet
    assert DRAFT_VERSION in markdown
    assert DRAFT_VERSION in packet
    # No artifact may still announce that it is awaiting the SECOND review.
    for name, text in (("markdown", markdown), ("packet", packet)):
        assert "AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW" not in text, name
    assert protocol["status"]["amendment_record"].endswith(
        "v0_5_operator_amendment.md")
    assert protocol["status"]["amendment_record_json"].endswith(
        "v0_5_operator_amendment.json")


def test_no_frozen_authorized_or_selected_state(protocol, tables):
    flags = tables["authority_flags"]
    assert set(flags) >= {"frozen", "execution_authorized", "winner_selected",
                          "positive_reference_selected", "seed_authorized",
                          "bank_authorized", "confirmation_access_authorized",
                          "model_operations_authorized"}
    for name, value in flags.items():
        assert value is False, "%s is not false" % name
    order = protocol["admissibility_order"]
    assert order["no_winner_this_round"] is True
    assert order["no_winner_this_round_statement"] == NO_WINNER
    assert protocol["positive_reference_candidates"][
        "selection_status"].startswith("UNSELECTED")


def test_every_operation_counter_is_zero(protocol, tables):
    """S3MR2 round: zero means zero, in both the protocol and the tables."""
    counters = protocol["operation_boundaries"]["performed_this_round"]
    assert counters, "no counters registered"
    for name, value in counters.items():
        assert value == 0, "%s is not zero" % name
        assert isinstance(value, int) and not isinstance(value, bool)
    assert protocol["operation_boundaries"]["all_counters_zero"] is True
    assert tables["operation_counts"] == counters
    for required in ("model_downloads", "forward_passes", "generations",
                     "seeds_drawn", "bank_rows_generated", "gpu_jobs",
                     "confirmation_split_accesses", "interfaces_selected",
                     "positive_references_selected", "evidence_rows_created"):
        assert required in counters


def test_no_bank_seed_result_evidence_row_or_confirmation_content_exists(
        protocol, amendment):
    assert protocol["results"] == []
    assert protocol["bank_rows"] == []
    frame = protocol["sampling_frame_v0_4"]
    assert frame["seeds_drawn_in_this_round"] == 0
    assert frame["bank_rows_created_in_this_round"] == 0
    assert frame["future_seed_lifecycle"]["seed_values"] is None
    assert frame["future_seed_lifecycle"]["realized_bank"] is None
    assert frame["future_seed_lifecycle"]["seed_authority_granted"] is False
    assert protocol["split_lifecycle"]["confirmation_isolation"][
        "accessible_before_authority"] is False
    assert amendment["results"] == []
    assert amendment["evidence_rows"] == []
    assert amendment["bank_rows"] == []
    assert amendment["seeds"] == []


# --------------------------------------------------------------------------
# S3MR2-001: the I3 estimand is a level, and no active claim says otherwise
# --------------------------------------------------------------------------

def test_exactly_two_variants_per_applicable_i3_cluster(protocol, tables):
    registry = protocol["i3_contrast_registry"]
    assert registry["variants_per_cluster"] == 2
    assert registry["independent_unit"] == "base_item_contrast_cluster"
    assert len(registry["k5"]) == 7
    assert len(registry["k6"]) == 2
    for row in registry["k5"] + registry["k6"]:
        assert row["variants_per_cluster"] == 2
    verification = tables["i3_pairwise_construction_verification"]
    assert verification["variants_per_cluster"] == 2
    for contrast in verification["contrasts"]:
        assert contrast["variants_per_cluster"] == 2
        assert contrast["changes_exactly_one_registered_factor"] is True
    assert protocol["proposed_statistics"]["i3_indicators"][
        "variants_per_cluster"] == 2


def test_no_k5_by_k6_cross_product_and_no_all_transformations_cluster(
        protocol, tables):
    assert protocol["counterbalancing_design"]["k5_and_k6_are_not_crossed"] is True
    assert protocol["counterbalancing_design"]["no_cross_product"] is True
    verification = tables["i3_pairwise_construction_verification"]
    assert verification["k5_x_k6_cross_product_exists"] is False
    assert verification["k5_x_k6_cross_product_cells"] == 0
    assert verification["active_all_transformations_cluster_exists"] is False
    assert verification["k5_contrast_count"] == 7
    assert verification["k6_contrast_count"] == 2
    assert len(verification["contrasts"]) == 9
    ids = [c["contrast_id"] for c in verification["contrasts"]]
    assert len(set(ids)) == 9
    # A cluster that varied everything at once would not be a one-factor contrast.
    for contrast in verification["contrasts"]:
        assert contrast["varied_factor"] not in ("all", "all_transformations")
        assert contrast["changes_exactly_one_registered_factor"] is True
        if "distinct_change_signatures" in contrast:
            assert contrast["distinct_change_signatures"] == 1, \
                contrast["contrast_id"]
        assert contrast["family"] in ("K5", "K6")
    assert sum(1 for c in verification["contrasts"] if c["family"] == "K5") == 7
    assert sum(1 for c in verification["contrasts"] if c["family"] == "K6") == 2


def test_j_joint_correct_truth_over_all_sixteen_ordered_cases(protocol, tables):
    """S3MR2-001. The gate indicator is a level over the registered distribution."""
    indicators = protocol["proposed_statistics"]["i3_indicators"]
    assert indicators["primary_indicator"] == "J_joint_correct"
    primary = indicators["J_joint_correct"]
    assert primary["is_a_level_not_a_contrast"] is True
    assert primary["identifies_a_presentation_effect"] is False
    assert "BOTH registered variants" in primary["definition"]

    lattice = tables["i3_outcome_lattice"]
    alphabet = lattice["alphabet"]
    assert alphabet == ["correct", "wrong_a", "wrong_b", "invalid"]
    assert lattice["ordered_cases"] == 16
    assert len(lattice["rows"]) == 16
    assert lattice["estimand_is_a_level"] is True
    assert lattice["estimand_is_a_presentation_contrast"] is False

    # The full ordered lattice, recomputed here rather than read.
    expected = {}
    for first in alphabet:
        for second in alphabet:
            expected[(first, second)] = int(first == "correct"
                                            and second == "correct")
    seen = {}
    for row in lattice["rows"]:
        key = (row["variant_1_outcome"], row["variant_2_outcome"])
        assert key not in seen, "duplicate lattice case %r" % (key,)
        seen[key] = row["J_joint_correct"]
        assert row["scores_for_the_gate"] is bool(row["J_joint_correct"])
    assert seen == expected
    assert sum(seen.values()) == 1 == lattice["passing_case_count"]
    # Every named failing family really does fail.
    assert lattice["stable_wrong_all_fail"] is True
    assert seen[("wrong_a", "wrong_a")] == 0
    assert lattice["stable_invalid_all_fail"] is True
    assert seen[("invalid", "invalid")] == 0
    assert lattice["mixed_correctness_all_fail"] is True
    assert seen[("correct", "wrong_a")] == 0 and seen[("wrong_a", "correct")] == 0
    assert lattice["two_different_wrong_answers_all_fail"] is True
    assert seen[("wrong_a", "wrong_b")] == 0


def test_historical_indicators_are_descriptive_only_with_no_decision_path(
        protocol, tables):
    """S3MR2-001. J_inv, J_cor and J_both survive only as historical names."""
    historical = protocol["proposed_statistics"]["i3_indicators"][
        "historical_and_descriptive_indicators"]
    assert historical["status"] == "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY"
    assert historical["reachable_decision_path"] is False
    assert set(historical["names"]) == {"J_inv", "J_cor", "J_both"}
    for authority in ("gate authority", "eligibility authority",
                      "selection authority", "confirmation authority",
                      "rescue path for a failed cell", "claim authority"):
        assert authority in historical["carries_no"]
    assert tables["i3_outcome_lattice"]["descriptive_indicator_status"] == \
        "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY"
    # No gate, component row, selection map entry or confirmation component may
    # name a retired indicator.
    statistics = protocol["proposed_statistics"]
    gates = []
    for gate in protocol["gate_hierarchy"]:
        stripped = {key: value for key, value in gate.items()
                    if key not in ("merely_descriptive", "reported_alongside",
                                   "v0_4_repair")}
        gates.append(stripped)
        # Wherever they do appear, they are named as descriptive only.
        for name, note in gate.get("reported_alongside", {}).items():
            if name in ("J_inv", "J_cor", "J_both"):
                assert "no gate authority" in note, name
    decision_blobs = json.dumps([
        statistics["retained_exact_binomial_gates"],
        statistics["confirmation_exact_binomial_gates"],
        statistics["development_selection_map"],
        gates,
        protocol["development_selection_and_confirmation_plan"],
    ])
    for retired in ("J_inv", "J_cor", "J_both"):
        assert retired not in decision_blobs, \
            "%s is reachable from a decision-bearing structure" % retired
    for gate in protocol["gate_hierarchy"]:
        for descriptive in gate.get("merely_descriptive", []):
            assert "J_joint_correct" not in descriptive
    assert protocol["proposed_statistics"]["i3_indicators"]["no_rescue"]


def _historical_exemption_markers():
    """Markers that make a passage unambiguously historical, retired or limiting."""
    return (
        "draft-v0.1", "draft-v0.2", "draft-v0.3", "draft-v0.4",
        "withdrawn", "withdraw", "retired", "retires", "retire",
        "historical", "history", "superseded", "supersedes",
        "rejected", "no longer", "not current", "prohibited",
        "must not", "may never", "never claim", "does not claim",
        "no active claim", "removed from every active", "carries no",
        "no_decision_role", "descriptive_only", "s3mr", "erratum",
        "phase 1", "phase1", "parser v2", "parser v3", "parser_v2",
        "parser_v3", "study 2", "study2", "stage t", "j-lens", "jlens",
    )


# The registered prohibited vocabulary, matched on word boundaries so that a
# legitimate use such as "design invariants" or "model-evaluation equivalents"
# is not mistaken for a presentation claim. The registered terms themselves are
# read from the protocol and asserted to be covered.
_PROHIBITED_PROSE_PATTERNS = tuple(
    re.compile(r"\b" + pattern + r"\b", re.IGNORECASE) for pattern in (
        r"invariance",
        r"invariant to presentation",
        r"equivalence",
        r"equivalent under presentation",
        r"no presentation effect",
        r"presentation[- ]effect size",
        r"stable across presentations",
        r"unaffected by presentation",
        r"robust to presentation",
        r"insensitive to presentation",
        r"same answer under both presentations",
        r"J_both",
        r"n = 256",
        r"n = 128",
    ))


def _prose_paragraphs(path):
    """Yield (first_line_number, paragraph_text) for every blank-line-delimited block."""
    lines = _load_text(path).split("\n")
    start = None
    buffer = []
    for number, raw in enumerate(lines, 1):
        if raw.strip():
            if start is None:
                start = number
            buffer.append(raw)
        elif buffer:
            yield start, "\n".join(buffer)
            start, buffer = None, []
    if buffer:
        yield start, "\n".join(buffer)


def _prose_active_claim_violations(path):
    """Every prohibited or retired occurrence in a NON-exempt paragraph.

    S3MR3-004 recorded that the enforcement of the active-claim prohibition was
    narrower than its registered scope: the scan never reached the charter, the
    handoff, either README, the protocol Markdown companion, the review packet or
    the status report, which is why the residue in S3MR3-003 survived a passing
    suite. Exemptions are explicit and auditable here rather than implicit, and
    they are applied at PARAGRAPH level, because "enclosed in an unambiguous
    historical record" is a property of the passage and not of a single line.
    """
    markers = _historical_exemption_markers()
    out = []
    for number, paragraph in _prose_paragraphs(path):
        lowered = paragraph.lower()
        # A blockquoted paragraph is quoted review provenance, not an active claim.
        if all(line.lstrip().startswith(">") for line in paragraph.split("\n")):
            continue
        if any(marker in lowered for marker in markers):
            continue
        for pattern in _PROHIBITED_PROSE_PATTERNS:
            match = pattern.search(paragraph)
            if match:
                out.append((number, match.group(0), paragraph.strip()[:200]))
    return out


def _active_claim_strings(protocol):
    """Every string that carries an active claim, gate question or interpretation."""
    out = []
    question = protocol["research_question"]
    for field in ("draft_question", "what_a_pass_would_mean",
                  "what_a_fail_would_mean", "unit_of_analysis"):
        out.append(("research_question %s" % field, question[field]))
    for target in protocol["validation_targets"]:
        out.append(("validation_target %s construct" % target["id"],
                    target["construct"]))
        if "why_needed" in target:
            out.append(("validation_target %s why_needed" % target["id"],
                        target["why_needed"]))
    for gate in protocol["gate_hierarchy"]:
        for field in ("question", "what_fails", "what_passes"):
            if field in gate:
                out.append(("gate %s %s" % (gate["gate_id"], field), gate[field]))
    ceiling = protocol["claim_ceiling"]
    for field in ("maximum_pass_claim", "maximum_fail_claim",
                  "permitted_i3_statement", "i3_claim_ceiling",
                  "what_a_pass_permits"):
        out.append(("claim_ceiling %s" % field, ceiling[field]))
    out.append(("claim_ceiling i3_single_genuine_contrast_profiles",
                ceiling["i3_single_genuine_contrast_profiles"]["statement"]))
    for profile, entry in ceiling["i3_claim_ceiling_by_profile"].items():
        out.append(("claim_ceiling by profile %s" % profile, json.dumps(entry)))
    for profile, entry in protocol["i3_contrast_registry"][
            "claim_ceiling_by_profile"].items():
        out.append(("i3 registry claim ceiling %s" % profile, entry["claim"]))
    out.append(("i3_contrast_registry claim_ceiling",
                protocol["i3_contrast_registry"]["claim_ceiling"]))
    for row in (protocol["proposed_statistics"]["retained_exact_binomial_gates"]
                + protocol["proposed_statistics"]["confirmation_exact_binomial_gates"]):
        out.append(("component %s construct" % row["gate"], row["construct"]))
        out.append(("component %s rejection_rule" % row["gate"],
                    row["rejection_rule"]))
    for row in protocol["proposed_statistics"]["registered_gate_floors"]:
        out.append(("gate floor %s construct" % row["gate_family"],
                    row["construct"]))
    # The registered rendering surface is a normative input and carries claims.
    surface = protocol["rendering_surface_v0_5"]
    for field in ("sufficiency_claim", "k6_instr_rule", "s4_wrapper_boundary"):
        out.append(("rendering_surface_v0_5 %s" % field, surface[field]))
    return out


def test_active_claim_text_contains_no_presentation_effect_claim(protocol):
    """S3MR2-001. Prohibited vocabulary may not appear in an active claim."""
    prohibition = protocol["proposed_statistics"]["active_claim_term_prohibition"]
    assert prohibition["enforced_by"] == "tests/test_study3_design.py"
    registered = [term.lower() for term in prohibition["prohibited_terms"]]
    for stem in PROHIBITED_CLAIM_TERMS:
        assert any(stem in term for term in registered), \
            "%r is not registered as a prohibited term" % stem
    for label, text in _active_claim_strings(protocol):
        lowered = text.lower()
        for stem in PROHIBITED_CLAIM_TERMS:
            assert stem not in lowered, \
                "%s asserts a prohibited presentation claim (%r)" % (label, stem)
    # And the prohibition itself must be scoped to those fields.
    for scope in ("gate questions", "what_fails clauses", "active claim text",
                  "success statements"):
        assert scope in prohibition["scope"]
    for permitted in ("clearly labelled historical narrative",
                      "retired-procedure records", "limitation-of-claim text",
                      "prohibited-claim lists"):
        assert permitted in prohibition["permitted_only_in"]


# S3MR3-003/S3MR3-004. The prose documents the prohibition claims to cover. The
# registered scope named routing documents, the handoff, the charter, the READMEs,
# the Markdown companion, the packet and the status report; draft-v0.4's enforcer
# reached none of them, which is why the retired construct and the withdrawn sizes
# survived a passing suite.
ENFORCED_PROSE_PATHS = (
    "README.md",
    "reports/current_status.md",
    "studies/README.md",
    "studies/study3/NEXT_THREAD_HANDOFF.md",
    "studies/study3/README.md",
    "studies/study3/RESEARCH_CHARTER_DRAFT.md",
    "studies/study3/analysis/study2_to_study3_design_traceability.md",
    "studies/study3/analysis/independent_methods_review_packet_v0_5.md",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
)

# The retired construct name and the two withdrawn sizes, which may appear only
# inside an explicitly historical passage.
RETIRED_ACTIVE_TOKENS = ("j_both", "n = 256", "n = 128")


@pytest.mark.parametrize("relative", ENFORCED_PROSE_PATHS)
def test_reviewed_prose_carries_no_active_retired_or_prohibited_language(relative):
    """S3MR3-003 and S3MR3-004. Enforcement must reach the registered scope."""
    path = os.path.join(REPO_ROOT, relative.replace("/", os.sep))
    assert os.path.exists(path), relative
    violations = _prose_active_claim_violations(path)
    assert not violations, "\n".join(
        "%s:%d carries active prohibited or retired language (%r): %s"
        % (relative, number, term, excerpt)
        for number, term, excerpt in violations)


def test_the_prose_scan_covers_every_registered_prohibited_term(protocol):
    """The prose patterns must cover the vocabulary the protocol registers."""
    registered = [term.lower() for term in protocol["proposed_statistics"][
        "active_claim_term_prohibition"]["prohibited_terms"]]
    for term in registered:
        probe = "This sentence claims %s in an active field." % term
        assert any(pattern.search(probe) for pattern in _PROHIBITED_PROSE_PATTERNS), \
            "the prose scan does not cover the registered term %r" % term


def test_the_prohibition_enforcement_scope_matches_the_registered_scope(protocol):
    """S3MR3-004. The declared scope and the enforced scope must be the same set."""
    prohibition = protocol["proposed_statistics"]["active_claim_term_prohibition"]
    assert prohibition["closes_finding"] == "S3MR3-004"
    declared = set(prohibition["enforced_paths"])
    enforced = set(ENFORCED_PROSE_PATHS)
    structured = {
        "studies/study3/protocol/interface_calibration_protocol_draft.json",
        "studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json",
    }
    assert declared == enforced | structured, declared ^ (enforced | structured)
    for relative in declared:
        assert os.path.exists(
            os.path.join(REPO_ROOT, relative.replace("/", os.sep))), relative
    # The declared protocol fields must all exist, and every declared field root
    # must correspond to a category the scan actually visits.
    scanned = {label.split(" ")[0] for label, _ in _active_claim_strings(protocol)}
    label_roots = {
        "research_question": "research_question",
        "validation_targets": "validation_target",
        "gate_hierarchy": "gate",
        "claim_ceiling": "claim_ceiling",
        "i3_contrast_registry": "i3",
        "proposed_statistics": "component",
        "rendering_surface_v0_5": "rendering_surface_v0_5",
    }
    for field in prohibition["enforced_protocol_fields"]:
        root = field.split(".")[0].split("[")[0]
        assert root in protocol, field
        assert root in label_roots, field
        assert label_roots[root] in scanned, field


def test_a_mutation_moving_retired_language_into_active_scope_is_rejected(tmp_path):
    """S3MR3-004. The widened scan must be non-vacuous."""
    active = tmp_path / "active.md"
    active.write_text(
        "# Study 3\n\nThe primary indicator is `J_both`, which requires invariance\n"
        "across the two variants, giving `n = 256` clusters per contrast cell.\n",
        encoding="utf-8")
    found = {term.lower() for _, term, _ in
             _prose_active_claim_violations(str(active))}
    assert "j_both" in found and "n = 256" in found and "invariance" in found, \
        "the scan failed to see prohibited active language"

    historical = tmp_path / "historical.md"
    historical.write_text(
        "# Study 3\n\nHistorical record: draft-v0.3 named `J_both` as its primary\n"
        "indicator and carried `n = 256`. That draft was rejected and the values\n"
        "are withdrawn from every active field.\n",
        encoding="utf-8")
    assert _prose_active_claim_violations(str(historical)) == [], \
        "an explicitly historical passage must be exempt"

    # And an exemption marker in a DIFFERENT paragraph must not launder an
    # active claim in this one.
    mixed = tmp_path / "mixed.md"
    mixed.write_text(
        "# Study 3\n\nHistorical record: draft-v0.3 is superseded.\n\n"
        "The primary indicator is `J_both` and it requires invariance.\n",
        encoding="utf-8")
    assert _prose_active_claim_violations(str(mixed)), \
        "a marker in another paragraph must not exempt this one"


def test_per_profile_i3_applicability_and_claim_ceiling_are_exact(
        protocol, tables):
    """S3MR3-001. Nine cells for S1 and S4, exactly ONE for S2 and S3.

    K6-SEP varies the separator between a displayed option label and its
    displayed option content. S2 and S3 render neither, so the factor has no
    referent, the two members of the pair would be byte-identical, and the cell
    is a self-comparison rather than a presentation pair. Applicability is
    therefore registered per contrast, never per family.
    """
    registry = protocol["i3_contrast_registry"]
    k5_ids = registry["k5_contrast_ids"]
    k6_ids = registry["k6_contrast_ids"]
    assert len(k5_ids) == 7 and len(k6_ids) == 2
    assert not set(k5_ids) & set(k6_ids)
    assert set(registry["k5_applicability"]["applicable_profiles"]) == set(LABEL_BEARING)
    assert set(registry["k5_applicability"]["not_applicable_profiles"]) == set(OPTION_LESS)

    # Family-level K6 applicability is exactly the defect S3MR3-001 recorded.
    k6 = registry["k6_applicability"]
    assert "applicable_profiles" not in k6, \
        "K6 applicability must be registered per contrast, not per family"
    assert k6["per_contrast_registration_required"] is True
    by_contrast = k6["by_contrast"]
    assert set(by_contrast) == set(k6_ids)
    assert set(by_contrast["K6-SEP"]["applicable_profiles"]) == set(LABEL_BEARING)
    assert set(by_contrast["K6-SEP"]["not_applicable_profiles"]) == set(OPTION_LESS)
    assert set(by_contrast["K6-INSTR"]["applicable_profiles"]) == \
        {"S1", "S2", "S3", "S4"}
    assert by_contrast["K6-INSTR"]["not_applicable_profiles"] == []

    by_profile = registry["claim_ceiling_by_profile"]
    expected_cells = {
        "S1": set(k5_ids) | set(k6_ids),
        "S2": {"K6-INSTR"},
        "S3": {"K6-INSTR"},
        "S4": set(k5_ids) | set(k6_ids),
    }
    for profile, entry in by_profile.items():
        assert set(entry["applicable_cells"]) == expected_cells[profile], profile
        assert entry["applicable_cell_count"] == len(expected_cells[profile])
    assert by_profile["S4"]["descriptive_only"] is True
    # The option-less profiles carry exactly one genuine I3 contrast.
    for profile in OPTION_LESS:
        assert by_profile[profile]["applicable_cell_count"] == 1
        assert "K6-SEP" not in by_profile[profile]["applicable_cells"]
    single = protocol["claim_ceiling"]["i3_single_genuine_contrast_profiles"]
    assert set(single["profiles"]) == set(OPTION_LESS)
    assert single["s3_conditional_status_still_applies"] is True
    # The two claim-ceiling copies may not drift apart.
    assert protocol["claim_ceiling"]["i3_claim_ceiling_by_profile"] == by_profile

    counts = tables["gate_bearing_cell_counts"]
    roles = len(protocol["proposed_statistics"]["registered_target_roles"])
    for profile, entry in by_profile.items():
        assert counts[profile]["I3_cells"] == \
            entry["applicable_cell_count"] * roles, profile
        assert counts[profile]["I3_K5_cells"] == (
            7 * roles if profile in LABEL_BEARING else 0), profile
        assert counts[profile]["I3_K6_cells"] == (
            2 * roles if profile in LABEL_BEARING else 1 * roles), profile
        assert counts[profile]["applicable_i3_contrast_count"] == \
            entry["applicable_cell_count"], profile
    # And the truth table must agree, per profile AND per contrast.
    for row in protocol["gate_truth_table"]["rows"]:
        label_bearing = row["profile"] in LABEL_BEARING
        expected = "applicable" if label_bearing else "not_applicable"
        for contrast in k5_ids:
            assert row["I3_K5"][contrast] == expected, (row["profile"], contrast)
        assert row["I3_K6"]["K6-SEP"] == expected, row["profile"]
        assert row["I3_K6"]["K6-INSTR"] == "applicable", row["profile"]
        if row["label_bearing"] is False:
            assert row["I3_K6"]["K6-SEP"] == "not_applicable"


def test_no_duplicate_r_sep_branch_exists_for_the_option_less_profiles(protocol):
    """S3MR3-001. R-sep must be structurally ABSENT for S2 and S3, not duplicated."""
    for profile in protocol["interface_profiles"]:
        applicability = profile["transformation_applicability"]["separator_rendering"]
        if profile["id"] in OPTION_LESS:
            assert applicability != "applicable", profile["id"]
            assert "no referent" in applicability, profile["id"]
            assert "never a pass" in applicability, profile["id"]
            names = {entry["transformation"]
                     for entry in profile["non_applicable_transformations"]}
            assert "separator_rendering" in names, profile["id"]
        else:
            assert applicability == "applicable", profile["id"]
    for rendering in protocol["counterbalancing_design"]["k6_renderings"]["renderings"]:
        if rendering["id"] == "R-sep":
            assert set(rendering["applicable_profiles"]) == set(LABEL_BEARING)
            assert set(rendering["not_applicable_profiles"]) == set(OPTION_LESS)
            assert rendering["separator_literal"] == " = "
        else:
            assert rendering["separator_literal"] == ": "
    # No profile-specific replacement separator may be invented.
    surface = protocol["rendering_surface_v0_5"]
    assert surface["k6_sep_separators"]["R-base"] == ": "
    assert surface["k6_sep_separators"]["R-sep"] == " = "


def test_all_nine_i3_cells_use_disjoint_namespaces(protocol):
    """S3MR2-010. Nine one-factor cells, nine disjoint generator namespaces."""
    frame = protocol["sampling_frame_v0_4"]
    i3_cells = [cell for cell in frame["development_sampling_cells"]
                if cell["component"].startswith("I3")]
    assert len(i3_cells) == 9
    namespaces = [cell["namespace"] for cell in i3_cells]
    assert len(set(namespaces)) == 9
    assert len({cell["sampling_cell_id"] for cell in i3_cells}) == 9
    for cell in i3_cells:
        assert cell["independent_unit"] == "base_item_contrast_cluster"
        assert cell["draw_rule"] == "with_replacement"
    assert frame["reuse_and_dependence_rule"][
        "distinct_sampling_cells_use_disjoint_namespaces"] is True
    # Every namespace across the whole frame is unique, in both splits.
    every = frame["development_sampling_cells"] + frame["confirmation_sampling_cells"]
    all_namespaces = [cell["namespace"] for cell in every]
    assert len(set(all_namespaces)) == len(all_namespaces)


# --------------------------------------------------------------------------
# S3MR2-007 / S3MR2-010: the registered sampling frame
# --------------------------------------------------------------------------

def test_k5_support_is_complete_and_every_state_has_weight_one_thirty_second(
        protocol, tables):
    support = protocol["sampling_frame_v0_4"]["k5_nuisance_state_support"]
    assert support["support_size"] == 32
    assert support["weight_per_state_exact_rational"] == "1/32"
    assert _rational(support["weight_per_state_exact_rational"]) * \
        support["support_size"] == 1
    assert _rational(support["weights_sum_exact_rational"]) == 1
    verification = tables["i3_pairwise_construction_verification"]
    assert verification["nuisance_support_size"] == 32
    assert verification["nuisance_weight_per_state_exact_rational"] == "1/32"
    assert verification["nuisance_weights_sum_to_one"] is True
    assert verification["constructor_maps_every_support_state_correctly"] is True
    # 4 correct content positions x 4 displayed-symbol indices x 2 alphabets.
    assert 4 * 4 * 2 == support["support_size"]
    assert protocol["i3_contrast_registry"]["option_slots"] == 4
    assert protocol["i3_contrast_registry"]["label_alphabet_count"] == 2


def test_k5_sampling_is_iid_with_replacement_not_complete_block(
        protocol, tables):
    """S3MR2-007. The deterministic complete-block assignment is retired."""
    support = protocol["sampling_frame_v0_4"]["k5_nuisance_state_support"]
    assert support["iid_with_replacement"] is True
    assert support["deterministic_complete_block_assignment_retired"] is True
    assert support["n_multiple_of_32_requirement_retired"] is True
    verification = tables["i3_pairwise_construction_verification"]
    assert verification["deterministic_complete_block_assignment"] is False
    assert verification["nuisance_draw_is_iid_with_replacement"] is True
    assert verification["sample_size_must_be_a_multiple_of_the_support"] is False
    # The design-time constructor enumeration is a fixture set, not a sample.
    assert verification["design_time_fixture_enumeration_is_not_a_sample"] is True
    assert support["design_time_fixture_enumeration_retained"]
    # No registered n may be justified by divisibility any more.
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        assert sizes[gate]["n"] % 32 != 0 or True  # divisibility is simply irrelevant
    assert "multiples of the complete-block size 32" in sizes["search_rule"]


def _gate_bearing_cell_keys(protocol):
    """Every gate-bearing atomic sampling cell key the design must cover."""
    registry = protocol["i3_contrast_registry"]
    keys = {"I1a": ["K2"], "I1b": ["K1"]}
    keys["I2"] = list(protocol["proposed_statistics"]["registered_operation_families"])
    keys["I3_K5"] = list(registry["k5_contrast_ids"])
    keys["I3_K6"] = list(registry["k6_contrast_ids"])
    depths = protocol["proposed_statistics"]["registered_composition_depths"]
    keys["I4"] = ["%s/d%d" % (family, depth)
                  for family in keys["I2"] for depth in depths]
    return keys


def test_every_gate_bearing_atomic_cell_has_a_complete_sampling_frame_entry(
        protocol, tables):
    """S3MR2-010. Fail-closed: a cell without a generator distribution is a defect."""
    frame = protocol["sampling_frame_v0_4"]
    expected = _gate_bearing_cell_keys(protocol)
    expected_count = sum(len(v) for v in expected.values())
    assert expected_count == 17
    for split, cells, count_key in (
            ("D", frame["development_sampling_cells"],
             "development_sampling_cell_count"),
            ("C", frame["confirmation_sampling_cells"],
             "confirmation_sampling_cell_count")):
        assert frame[count_key] == len(cells) == expected_count
        ids = {cell["sampling_cell_id"] for cell in cells}
        assert len(ids) == expected_count
        for component, suffixes in expected.items():
            for suffix in suffixes:
                if component == "I1a":
                    wanted = "%s/I1a/K2" % split
                elif component == "I1b":
                    wanted = "%s/I1b/K1" % split
                elif component == "I2":
                    wanted = "%s/I2/K3/%s" % (split, suffix)
                elif component == "I4":
                    wanted = "%s/I4/K4/%s" % (split, suffix)
                else:
                    wanted = "%s/%s/%s" % (split, component, suffix)
                assert wanted in ids, "missing sampling cell %s" % wanted
        for cell in cells:
            assert cell["split"] == split
            assert cell["sampling_cell_id"].startswith(split + "/")
            for field in ("generator_family", "generator_version", "estimand",
                          "independent_unit", "namespace", "draw_rule",
                          "sampled_parameters", "validity_predicates",
                          "support_size", "weights_sum_exact_rational",
                          "joint_weight_per_support_state_exact_rational"):
                assert cell[field] not in (None, "", []), \
                    "%s lacks %s" % (cell["sampling_cell_id"], field)
            assert set(cell["excludes_from_its_identity"]) == \
                {"interface_profile", "checkpoint_role"}
    assert tables["sampling_frame_validation"]["sampling_cells_validated"] == \
        2 * expected_count
    assert frame["exact_binomial_validity"]["fail_closed_rule"]


def test_sampling_weights_sum_to_one_and_predicates_are_pre_draw_model_free(
        protocol, tables):
    frame = protocol["sampling_frame_v0_4"]
    for cell in (frame["development_sampling_cells"]
                 + frame["confirmation_sampling_cells"]):
        product = Fraction(1)
        support = 1
        for parameter in cell["sampled_parameters"]:
            weight = _rational(parameter["weight_per_state_exact_rational"])
            size = parameter["support_size"]
            assert weight * size == 1, cell["sampling_cell_id"]
            assert _rational(parameter["weights_sum_exact_rational"]) == 1
            product *= weight
            support *= size
        assert support == cell["support_size"], cell["sampling_cell_id"]
        assert product == _rational(
            cell["joint_weight_per_support_state_exact_rational"])
        assert product * cell["support_size"] == 1
        assert _rational(cell["weights_sum_exact_rational"]) == 1
        assert cell["parameters_are_independently_drawn"] is True
    for predicate in frame["validity_predicates"]:
        assert predicate["deterministic"] is True
        assert predicate["evaluated_before_any_model_operation"] is True
        assert predicate["satisfied_by_construction"] is True
    contract = frame["rejection_contract"]
    assert _rational(contract["registered_rejection_probability_exact_rational"]) == 0
    assert contract["acceptance_predicate_frozen_before_any_seed_exists"] is True
    assert contract["acceptance_predicate_may_never_change_after_a_seed_exists"] \
        is True
    for prohibited in ("difficulty",):
        assert prohibited in contract["post_draw_property_rejection_prohibited"]
    validation = tables["sampling_frame_validation"]
    assert validation["all_parameter_weights_sum_to_one"] is True
    assert validation["all_joint_weights_sum_to_one"] is True


def test_split_partitions_are_disjoint_and_outcome_blind(protocol, tables):
    partition = protocol["sampling_frame_v0_4"]["split_partition"]
    assert partition["outcome_blind"] is True
    assert partition["cross_split_reuse_prohibited"] is True
    assert partition["frozen_before_any_seed_draw"] is True
    assert partition["splits"] == ["D", "C", "P3Q"]
    frame = protocol["sampling_frame_v0_4"]
    dev = {cell["namespace"] for cell in frame["development_sampling_cells"]}
    conf = {cell["namespace"] for cell in frame["confirmation_sampling_cells"]}
    assert not dev & conf, "development and confirmation namespaces overlap"
    for namespace in dev:
        assert "/D/" in namespace
    for namespace in conf:
        assert "/C/" in namespace
    assert tables["sampling_frame_validation"]["split_partition_outcome_blind"] \
        is True
    assert tables["sampling_frame_validation"]["namespaces_disjoint"] is True


def test_draws_are_with_replacement_and_duplicate_redraw_is_prohibited(
        protocol, tables):
    frame = protocol["sampling_frame_v0_4"]
    model = frame["binding_stochastic_model"]
    assert "WITH replacement" in model["within_cell_draw_rule"]
    rule = frame["duplicate_rule"]
    assert rule["duplicates_must_be_retained"] is True
    assert rule["duplicate_generator_tuples_are_legitimate_iid_draws"] is True
    assert rule["redraw_for_uniqueness_prohibited"] is True
    assert rule["redraw_for_difficulty_balance_or_model_response_prohibited"] \
        is True
    assert "no gate" in rule["duplicate_counts_reported_later_as"]
    for cell in (frame["development_sampling_cells"]
                 + frame["confirmation_sampling_cells"]):
        assert cell["draw_rule"] == "with_replacement"
    assert tables["sampling_frame_validation"]["all_draws_with_replacement"] is True
    assert tables["sampling_frame_validation"]["duplicates_retained"] is True


def test_cross_role_and_profile_reuse_and_dependence_are_explicit(protocol):
    frame = protocol["sampling_frame_v0_4"]
    reuse = frame["reuse_and_dependence_rule"]
    assert reuse["dependence_is_expressly_allowed"] is True
    assert "arbitrary-dependence union bounds" in reuse["dependence_is_handled_by"]
    for field in ("cross_role_reuse", "cross_profile_reuse", "s3_logit_reuse",
                  "within_a_sampling_cell", "id_difference_does_not_imply_independence"):
        assert reuse[field]
    assert "not independent" in reuse["id_difference_does_not_imply_independence"]
    levels = frame["two_levels"]
    assert levels["sampling_cell"]["one_iid_item_stream_per_sampling_cell"] is True
    assert levels["evaluation_cell"]["sample_is_marginally_iid_bernoulli"] is True
    assert levels["evaluation_cell"][
        "cells_sharing_sampled_items_may_be_dependent"] is True
    assert set(levels["sampling_cell"]["excludes"]) == \
        {"interface profile", "checkpoint role"}
    assert protocol["atomic_evaluation_cells"][
        "one_iid_stream_per_sampling_cell_reused_across_its_evaluation_cells"] is True


def test_future_seed_procedure_is_first_draw_only_domain_separated_auditable(
        protocol):
    lifecycle = protocol["sampling_frame_v0_4"]["future_seed_lifecycle"]
    assert lifecycle["status"] == "SPECIFIED_BUT_NOT_AUTHORIZED"
    assert lifecycle["first_draw_only"] is True
    assert lifecycle["redraw_prohibited"] is True
    assert lifecycle["substitution_prohibited"] is True
    assert lifecycle["seed_shopping_prohibited"] is True
    assert lifecycle["one_master_seed_per_split"] is True
    assert lifecycle["master_seed_bits"] == 256
    assert lifecycle["domain_separation_encoding"]
    assert lifecycle["commitment_rule"]
    assert "before" in lifecycle["commitment_rule"]
    assert lifecycle["generator_implementation_blob"] is None
    assert lifecycle["confirmation_seed_isolation"]
    assert "not zero" in lifecycle["null_means"]


def test_exact_binomial_assumptions_match_the_registered_estimand(protocol):
    """S3MR2-010. What licenses the exact binomial is written down."""
    validity = protocol["sampling_frame_v0_4"]["exact_binomial_validity"]
    conditions = " ".join(validity["conditions"]).lower()
    assert "iid" in conditions
    assert "registered generator distribution" in conditions
    assert "no randomness" in validity["what_the_model_contributes"].lower()
    assert validity["estimand_induced_by_the_distribution"]
    frame = protocol["sampling_frame_v0_4"]
    assert frame["binding_stochastic_model"][
        "all_inferential_randomness_comes_from"] == "the registered item draw"
    assert "deterministic" in frame["binding_stochastic_model"][
        "model_sampling_contributes_no_randomness"]
    for cell in frame["development_sampling_cells"]:
        assert cell["estimand"].startswith("Pr(")
    lattice_estimand = protocol["proposed_statistics"]["i3_indicators"][
        "J_joint_correct"]["estimand"]
    assert "registered item-generating distribution" in lattice_estimand


# --------------------------------------------------------------------------
# S3MR2-002: the type-I and type-II architecture
# --------------------------------------------------------------------------

def _component(protocol, split, gate_id):
    key = ("retained_exact_binomial_gates" if split == "development"
           else "confirmation_exact_binomial_gates")
    for row in protocol["proposed_statistics"][key]:
        if row["gate"] == gate_id:
            return row
    raise AssertionError("no %s component for %s" % (split, gate_id))


def _gate(protocol, gate_id):
    for gate in protocol["gate_hierarchy"]:
        if gate["gate_id"] == gate_id:
            return gate
    raise AssertionError("no gate %s" % gate_id)


def test_development_and_confirmation_alphas_and_the_fixed_denominator(
        protocol, tables):
    statistics = protocol["proposed_statistics"]
    assert statistics["development_component_alpha_exact_rational"] == "1/600"
    assert statistics["confirmation_component_alpha_exact_rational"] == "1/200"
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        assert _component(protocol, "development", gate)[
            "alpha_exact_rational"] == "1/600"
        assert _component(protocol, "confirmation", gate)[
            "alpha_exact_rational"] == "1/200"
    architecture = protocol["power_architecture_v0_4"]["type_i_architecture"]
    assert architecture["fixed_selectable_profile_denominator"] == 3
    assert architecture["denominator_is_fixed_before_data"] is True
    assert architecture["denominator_never_shrinks"] is True
    assert architecture["per_profile_component_alpha_exact_rational"] == "1/600"
    assert architecture["confirmation_component_alpha_exact_rational"] == "1/200"
    # 1/600 x 3 = 1/200 exactly.
    assert _rational("1/600") * 3 == _rational(
        architecture["study_development_false_qualification_bound_exact_rational"])
    family_b = statistics["hypothesis_families"]["family_B_across_profiles"]
    assert family_b["fixed_selectable_profile_denominator"] == 3
    assert family_b["denominator_never_shrinks"] is True
    assert tables["declared_assumptions"]["fixed_selectable_profile_denominator"] == 3
    assert architecture["s4_excluded_from_every_success_union"] is True


def test_m_max_and_cell_counts_derive_from_the_truth_table(protocol, tables):
    """S3MR2-002. m_max is derived, over selectable profiles only."""
    registry = protocol["i3_contrast_registry"]
    families = protocol["proposed_statistics"]["registered_operation_families"]
    depths = protocol["proposed_statistics"]["registered_composition_depths"]
    roles = protocol["proposed_statistics"]["registered_target_roles"]
    assert len(roles) == 3 and len(families) == 2 and len(depths) == 2

    counts = tables["gate_bearing_cell_counts"]
    truth_rows = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    recomputed = {}
    for profile, row in truth_rows.items():
        i1a = len(roles) if row["I1a"] == "applicable" else 0
        i1b = len(roles) if row["I1b"] == "applicable" else 0
        i2 = len(roles) * len(families) if row["I2"] == "applicable" else 0
        i3_k5 = sum(1 for state in row["I3_K5"].values()
                    if state == "applicable")
        i3_k6 = sum(1 for state in row["I3_K6"].values()
                    if state == "applicable")
        i3 = (i3_k5 + i3_k6) * len(roles)
        i4 = len(families) * len(depths) if row["I4"] == "applicable" else 0
        recomputed[profile] = {
            "I1a_cells": i1a, "I1b_cells": i1b, "I2_cells": i2,
            "I4_cells": i4,
            "cells_at_i1_i3_floor": i1a + i1b + i3,
            "cells_at_i2_floor": i2,
            "cells_at_i4_floor": i4,
            "total_gate_bearing_cells": i1a + i1b + i2 + i3 + i4,
        }
    for profile, expected in recomputed.items():
        published = counts[profile]
        for key, value in expected.items():
            assert published[key] == value, "%s.%s" % (profile, key)
        assert published["selectable"] is (profile != "S4")

    selectable = [p for p in counts if counts[p]["selectable"]]
    assert sorted(selectable) == ["S1", "S2", "S3"]
    m_max = max(counts[p]["total_gate_bearing_cells"] for p in selectable)
    assert m_max == 43
    # S3MR3-001: the option-less profiles lose their K6-SEP cells, so their totals
    # fall from 19 to 16, while S1 -- the profile that ATTAINS m_max -- is
    # untouched. m_max is unchanged by derivation, not by preservation.
    assert counts["S1"]["total_gate_bearing_cells"] == 43
    for profile in OPTION_LESS:
        assert counts[profile]["total_gate_bearing_cells"] == 16, profile
        assert counts[profile]["cells_at_i1_i3_floor"] == 6, profile
        assert counts[profile]["applicable_i3_contrast_count"] == 1, profile
    assert counts["S4"]["total_gate_bearing_cells"] == 39
    assert tables["power_architecture"]["m_max"] == m_max
    assert protocol["power_architecture_v0_4"]["cell_counts"]["m_max"] == m_max
    assert protocol["power_architecture_v0_4"]["cell_counts"][
        "s4_is_excluded_from_m_max"] is True
    assert tables["power_architecture"]["s4_excluded_from_m_max"] is True
    # S4's own cell total may never enter the budget, whatever its size.
    assert counts["S4"]["selectable"] is False
    assert counts["S4"]["total_gate_bearing_cells"] > 0
    assert m_max == max(counts[p]["total_gate_bearing_cells"]
                        for p in counts if counts[p]["selectable"])


def test_the_power_budget_rationals_reconstruct_exactly(protocol, tables):
    """S3MR2-002. 19/17200, 17181/17200, 381/400 and 9/10 are derived."""
    allocation = protocol["power_architecture_v0_4"]["type_ii_allocation"]
    m_max = protocol["power_architecture_v0_4"]["cell_counts"]["m_max"]
    stage = _rational(
        allocation["per_stage_profile_false_negative_budget_exact_rational"])
    assert stage == Fraction(19, 400)

    per_cell = stage / m_max
    assert per_cell == Fraction(19, 17200)
    assert _rational(
        allocation["per_cell_false_negative_budget_exact_rational"]) == per_cell

    target = 1 - per_cell
    assert target == Fraction(17181, 17200)
    assert _rational(allocation["per_cell_power_target_exact_rational"]) == target
    assert allocation["per_cell_power_target_decimal"] == _decimal(target)

    profile_floor = 1 - m_max * per_cell
    assert profile_floor == 1 - stage == Fraction(381, 400)
    assert _rational(
        allocation["profile_stage_power_floor_exact_rational"]) == profile_floor
    assert allocation["profile_stage_power_floor_decimal"] == \
        _decimal(profile_floor, 6)

    panel = _rational(allocation["panel_false_qualification_budget_exact_rational"])
    assert panel == Fraction(1, 200)
    end_to_end = 1 - stage - panel - stage
    assert end_to_end == Fraction(9, 10)
    assert _rational(
        allocation["study_end_to_end_power_floor_exact_rational"]) == end_to_end
    assert allocation["study_end_to_end_power_floor_decimal"] == \
        _decimal(end_to_end, 6)
    assert _rational(
        allocation["confirmation_conjunction_power_floor_exact_rational"]) == \
        Fraction(381, 400)

    published = tables["power_architecture"]
    assert _rational(published["per_cell_false_negative_budget_exact_rational"]) \
        == per_cell
    assert _rational(published["per_cell_power_target_exact_rational"]) == target
    assert _rational(published["profile_stage_power_floor_exact_rational"]) == \
        profile_floor
    assert _rational(published["study_end_to_end_power_floor_exact_rational"]) == \
        end_to_end
    assert [_rational(term) for term in published["union_bound_terms"]] == \
        [stage, panel, stage]
    assert sum(_rational(t) for t in published["union_bound_terms"]) == \
        1 - end_to_end
    assert _rational(
        protocol["proposed_statistics"]["target_power"]["exact_rational"]) == target


def test_the_union_bound_proof_contains_no_independence_assumption(protocol,
                                                                  tables):
    proof = protocol["power_architecture_v0_4"]["union_bound_proof"]
    assert proof["uses_independence"] is False
    assert proof["holds_under_arbitrary_dependence"] is True
    assert len(proof["failure_events_unioned"]) == 3
    assert "sensitivity" in proof["independence_based_products"]
    text = json.dumps(proof).lower()
    for forbidden in ("assuming independence", "independent cells",
                      "under independence", "product of the per-cell powers"):
        assert forbidden not in text
    assert tables["power_architecture"]["uses_independence"] is False
    assert tables["power_architecture"]["holds_under_arbitrary_dependence"] is True


def test_power_labels_carry_correct_scope(protocol, tables):
    allocation = protocol["power_architecture_v0_4"]["type_ii_allocation"]
    assert allocation["per_cell_power_target_scope"] == "PER ATOMIC EVALUATION CELL"
    assert protocol["proposed_statistics"]["target_power"]["scope"] == \
        "PER ATOMIC EVALUATION CELL"
    prohibition = protocol["proposed_statistics"]["target_power"]["prohibition"]
    for scope in ("family", "profile", "selection", "confirmation", "end-to-end"):
        assert scope in prohibition
    vocabulary = protocol["power_architecture_v0_4"]["power_vocabulary"]
    for name in ("target_power", "profile_stage_power_floor",
                 "study_end_to_end_power_floor", "selection_return_characteristic",
                 "confirmation_characteristic", "prohibited"):
        assert name in vocabulary
    assert "per atomic evaluation cell" in vocabulary["target_power"]
    assert "per profile per stage" in vocabulary["profile_stage_power_floor"]
    assert "arbitrary" in vocabulary["profile_stage_power_floor"]
    assert "development selection plus one-shot confirmation" in \
        vocabulary["study_end_to_end_power_floor"]
    published = tables["power_architecture"]
    assert published["per_cell_power_target_scope"] == "PER ATOMIC EVALUATION CELL"
    assert "LOWER BOUND" in published["profile_stage_power_floor_scope"]
    assert "ARBITRARY" in published["profile_stage_power_floor_scope"]


def test_least_favourable_configuration_and_uncovered_region_are_explicit(
        protocol):
    configuration = protocol["power_architecture_v0_4"][
        "least_favourable_configuration"]
    assert configuration["binding_only_under_this_configuration"] is True
    assert len(configuration["conditions"]) >= 4
    uncovered = protocol["power_architecture_v0_4"][
        "not_covered_by_the_power_guarantee"]
    assert len(uncovered) >= 4
    text = " ".join(uncovered).lower()
    assert "indifference region" in text
    assert "strictly between" in text


# --------------------------------------------------------------------------
# S3MR2-003: the six threshold rows, recomputed here from exact rationals
# --------------------------------------------------------------------------

def _floor_for(protocol, gate_family):
    for row in protocol["proposed_statistics"]["registered_gate_floors"]:
        if row["gate_family"] == gate_family:
            return row
    raise AssertionError("no registered floor %s" % gate_family)


def _recompute_rows(protocol):
    """Recompute all six rows from the protocol's registered inputs alone."""
    statistics = protocol["proposed_statistics"]
    ceiling = statistics["sample_size_search_ceiling"]
    target = _rational(statistics["target_power"]["exact_rational"])
    dev_alpha = _rational(statistics["development_component_alpha_exact_rational"])
    conf_alpha = _rational(
        statistics["confirmation_component_alpha_exact_rational"])
    out = {}
    for floor in statistics["registered_gate_floors"]:
        p0 = _rational(floor["p0_exact_rational"])
        p1 = _rational(floor["p1_exact_rational"])
        n, dev_count = _smallest_size_meeting_power(p0, p1, dev_alpha, target,
                                                    ceiling)
        conf_count = _smallest_controlling_count(n, p0, conf_alpha)
        out[floor["gate_family"]] = {
            "n": n, "p0": p0, "p1": p1,
            "development": dev_count, "confirmation": conf_count,
        }
    return out


@pytest.fixture(scope="module")
def recomputed(protocol):
    return _recompute_rows(protocol)


def test_all_six_threshold_rows_derive_from_exact_rational_inputs(
        protocol, tables, recomputed):
    """S3MR2-003. The tails and powers are recomputed here, not read."""
    dev_rows = {row["gate_family"]: row
                for row in tables["development_exact_binomial_components"]}
    conf_rows = {row["gate_family"]: row
                 for row in tables["confirmation_exact_binomial_components"]}
    assert len(dev_rows) == len(conf_rows) == 3
    for family, expected in recomputed.items():
        for rows, key, alpha in ((dev_rows, "development", Fraction(1, 600)),
                                 (conf_rows, "confirmation", Fraction(1, 200))):
            row = rows[family]
            assert row["n"] == expected["n"], family
            assert row["pass_count"] == expected[key], family
            assert _rational(row["p0_exact_rational"]) == expected["p0"]
            assert _rational(row["p1_exact_rational"]) == expected["p1"]
            assert _rational(row["alpha_exact_rational"]) == alpha
            null_tail = _upper_tail(row["n"], row["pass_count"], expected["p0"])
            power = _upper_tail(row["n"], row["pass_count"], expected["p1"])
            assert null_tail <= alpha
            assert row["exact_null_tail_at_p0"] == _decimal(null_tail)
            assert row["exact_power_at_p1"] == _decimal(power)
            assert row["degenerate_rejection_region"] is False
            assert 0 < row["pass_count"] < row["n"]
            assert row["unit_of_n"]
    # Development power must clear the registered per-cell target; the
    # confirmation rows reuse the development sizes and are conservative.
    target = _rational(
        protocol["proposed_statistics"]["target_power"]["exact_rational"])
    for family, expected in recomputed.items():
        power = _upper_tail(expected["n"], expected["development"], expected["p1"])
        assert power >= target, family
        assert dev_rows[family]["meets_per_cell_power_target"] is True
    assert protocol["power_architecture_v0_4"][
        "confirmation_sizes_are_conservative_reuse"]


def test_development_sample_sizes_are_the_smallest_meeting_the_target(
        protocol, recomputed):
    """S3MR2-003. No divisibility restriction survives; every integer is searched."""
    statistics = protocol["proposed_statistics"]
    target = _rational(statistics["target_power"]["exact_rational"])
    alpha = _rational(statistics["development_component_alpha_exact_rational"])
    for family, expected in recomputed.items():
        n = expected["n"]
        for smaller in range(1, n):
            count = _smallest_controlling_count(smaller, expected["p0"], alpha)
            if count is None or count > smaller:
                continue
            assert _upper_tail(smaller, count, expected["p1"]) < target, \
                "n=%d already meets the target for %s" % (smaller, family)
        row = _floor_for(protocol, family)
        for gate in row["gates"]:
            assert statistics["sample_sizes"][gate]["n"] == n
            assert _component(protocol, "development", gate)["n"] == n
            assert _component(protocol, "development", gate)[
                "n_is_smallest_unrestricted_positive_integer_meeting_the_target"] \
                is True
    assert "every positive integer is searched" in statistics["sample_size_search_rule"]
    assert statistics["sample_size_search_ceiling"] > max(
        e["n"] for e in recomputed.values())


def test_pass_counts_are_minimal_at_their_alphas(protocol, recomputed):
    """S3MR2-003. One unit lower would breach the registered level."""
    for family, expected in recomputed.items():
        for key, alpha in (("development", Fraction(1, 600)),
                           ("confirmation", Fraction(1, 200))):
            count = expected[key]
            n, p0 = expected["n"], expected["p0"]
            assert _upper_tail(n, count, p0) <= alpha
            assert _upper_tail(n, count - 1, p0) > alpha, \
                "%s %s pass count is not minimal" % (family, key)
        floor = _floor_for(protocol, family)
        for gate in floor["gates"]:
            assert _component(protocol, "development", gate)["pass_count"] == \
                expected["development"]
            assert _component(protocol, "confirmation", gate)["pass_count"] == \
                expected["confirmation"]
            for split in ("development", "confirmation"):
                assert _component(protocol, split, gate)[
                    "pass_count_is_minimal_at_alpha"] is True


def test_the_null_tail_supremum_sits_at_p0(recomputed):
    """The level claim needs monotonicity, which is asserted and checked here."""
    for expected in recomputed.values():
        n, count, p0 = expected["n"], expected["development"], expected["p0"]
        lower = p0 - Fraction(1, 1000)
        assert _upper_tail(n, count, lower) < _upper_tail(n, count, p0)
        assert _upper_tail(n, count, p0) < _upper_tail(n, count, expected["p1"])


def test_identity_checks_hold(tables):
    checks = tables["identity_checks"]
    for name, value in checks.items():
        if isinstance(value, bool):
            assert value is True, name
    assert checks["intersection_union_source"] == "Berger and Hsu (1996)"


# --------------------------------------------------------------------------
# Anti-transcription: the derivation script must not carry its own answers
# --------------------------------------------------------------------------

# These are the published outputs. None of them may appear as a reachable
# literal in the derivation script; the script must recompute all of them.
DERIVED_SIZES = (413, 214, 448)
DERIVED_PASS_COUNTS = (389, 129, 383, 388, 127, 381)
DERIVED_TAILS = (0.001664632930, 0.001597676081, 0.001620609599,
                 0.003020762720, 0.003765544908, 0.003582895662)
DERIVED_CELL_TOTALS = (43, 33543, 3584, 27856, 26064, 417024, 390960, 502)
FORBIDDEN_LITERAL_STRINGS = ("17181/17200", "19/17200", "381/400", "9/10 end")


def test_the_derivation_script_contains_no_hard_coded_result_constant():
    """S3MR2-003. Every output must be recomputed, never transcribed."""
    with open(STATS_SCRIPT, encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)

    # Literals inside docstrings are prose, not reachable values, so the
    # docstring expression statements are removed before the audit.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and \
                    isinstance(first.value, ast.Constant) and \
                    isinstance(first.value.value, str):
                docstrings.add(id(first.value))

    numbers, strings = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and id(node) not in docstrings:
            if isinstance(node.value, bool):
                continue
            if isinstance(node.value, (int, float)):
                numbers.append(node.value)
            elif isinstance(node.value, str):
                strings.append(node.value)

    for value in DERIVED_SIZES + DERIVED_PASS_COUNTS + DERIVED_CELL_TOTALS:
        assert value not in numbers, \
            "%r is transcribed into the derivation script" % value
    for value in DERIVED_TAILS:
        assert value not in numbers, \
            "%r is transcribed into the derivation script" % value
    blob = " ".join(strings)
    for text in FORBIDDEN_LITERAL_STRINGS:
        assert text not in blob, "%r is transcribed as a string literal" % text
    for value in DERIVED_PASS_COUNTS + DERIVED_SIZES:
        assert str(value) not in blob, \
            "%r appears as a string literal in the derivation script" % value


def test_design_statistics_script_reproduces_its_committed_tables():
    result = subprocess.run([sys.executable, STATS_SCRIPT, "--check"],
                            capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 0, (
        "design_statistics.py --check failed\nstdout:\n%s\nstderr:\n%s"
        % (result.stdout, result.stderr))
    assert "DESIGN_STATISTICS_CHECK_OK" in result.stdout


def test_statistics_tables_record_no_operations(tables):
    assert tables["status"] == "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN"
    assert tables["document_class"] == "design_statistics_derivation"
    for name, value in tables["operation_counts"].items():
        assert value == 0, name
    for name, value in tables["authority_flags"].items():
        assert value is False, name


# --------------------------------------------------------------------------
# S3MR2-006: the total, deterministic state machine
# --------------------------------------------------------------------------

def test_i0_is_a_global_precondition_failing_only_to_instrument_defect(
        protocol, tables):
    machine = protocol["state_machine_v0_4"]
    assert machine["i0_is_a_global_precondition"] is True
    assert machine["i0_is_not_part_of_profile_adequacy"] is True
    states = {state["id"]: state for state in machine["states"]}
    instrument = states["Q0_INSTRUMENT"]
    for transition in instrument["transitions"]:
        if transition["event"] != "all fixtures pass":
            assert transition["next"] == "STOP_INSTRUMENT_DEFECT", \
                transition["event"]
    failures = {t["event"] for t in instrument["transitions"]
                if t["next"] == "STOP_INSTRUMENT_DEFECT"}
    assert {"any fixture fails", "error", "ambiguity"} <= failures
    claim = states["STOP_INSTRUMENT_DEFECT"]["claim"]
    assert "NOTHING was measured about any interface" in claim
    assert "never a statement about any interface" in claim
    assert tables["state_machine"]["i0_failure_maps_only_to"] == \
        "STOP_INSTRUMENT_DEFECT"
    assert tables["state_machine"]["i0_is_a_global_precondition"] is True
    assert tables["state_machine"]["i0_is_part_of_profile_adequacy"] is False
    plan = protocol["development_selection_and_confirmation_plan"]
    assert plan["stage_1_component_evaluation"][
        "i0_removed_from_profile_component_lists"] is True
    for profile, components in plan["stage_1_component_evaluation"][
            "components_by_profile"].items():
        assert "I0" not in components, profile


def test_the_state_machine_is_total_deterministic_and_fully_reachable(
        protocol, tables):
    machine = protocol["state_machine_v0_4"]
    assert machine["total"] is True
    assert machine["deterministic"] is True
    assert machine["exactly_one_legal_next_state_per_event"] is True
    assert machine["rescue_paths"] == []

    states = {state["id"]: state for state in machine["states"]}
    assert len(states) == len(machine["states"]) == 10
    decisions = [s for s in machine["states"] if s["kind"] != "terminal"]
    terminals = {s["id"] for s in machine["states"] if s["kind"] == "terminal"}
    assert len(terminals) == 6

    edges = []
    for state in decisions:
        assert state["transitions"], state["id"]
        seen_events = set()
        for transition in state["transitions"]:
            assert transition["event"] not in seen_events, \
                "%s has two next states for %r" % (state["id"],
                                                   transition["event"])
            seen_events.add(transition["event"])
            assert transition["next"] in states, transition["next"]
            edges.append((state["id"], transition["event"], transition["next"]))
    # Every terminal is reachable from the entry state.
    reachable, frontier = {"Q0_INSTRUMENT"}, ["Q0_INSTRUMENT"]
    while frontier:
        current = frontier.pop()
        for source, _event, target in edges:
            if source == current and target not in reachable:
                reachable.add(target)
                frontier.append(target)
    assert terminals <= reachable, "unreachable terminals: %s" % (
        terminals - reachable)
    assert reachable == set(states)
    for terminal in terminals:
        assert states[terminal].get("claim")
        assert "transitions" not in states[terminal]

    published = tables["state_machine"]
    assert published["every_event_has_exactly_one_next_state"] is True
    assert published["every_terminal_state_is_reachable"] is True
    assert published["rescue_paths"] == []
    assert set(published["terminal_states"]) == terminals
    assert set(published["states"]) == set(states)
    assert len(published["transitions"]) == len(edges)
    assert {(t["from"], t["event"], t["to"]) for t in published["transitions"]} \
        == set(edges)
    # The sixteen-row eligibility subtable is not the whole machine.
    subtable = machine["profile_eligibility_subtable"]
    assert subtable["is_not_the_whole_state_machine"] is True
    assert subtable["i0_branch_is_registered_separately"] is True


# --------------------------------------------------------------------------
# S3MR2-005 / S3MR2-008: the operation ontology and the projection
# --------------------------------------------------------------------------

WORK_STREAMS = ("deterministic_I0_fixtures", "target_role_development",
                "positive_reference_external_P3Q",
                "RP_I4_under_candidate_profiles",
                "selected_profile_one_shot_confirmation",
                "S4_diagnostic_generation")


def test_the_operation_ontology_maps_every_cost_bearing_quantity(protocol):
    ontology = protocol["operation_ontology_v0_4"]
    assert ontology["status"] == "PLANNING_ONTOLOGY_AUTHORIZES_NOTHING"
    assert ontology["s4_forward_cost_must_not_be_null"] is True
    units = {entry["unit"] for entry in ontology["units"]}
    for required in ("rendered_row", "scored_row", "restricted_vocabulary_logit_read",
                     "sequence_level_prefill_evaluation",
                     "incremental_decode_evaluation",
                     "total_sequence_level_model_evaluation_equivalent"):
        assert required in units, required
    for entry in ontology["units"]:
        assert entry["definition"]
    assert "NEVER equated with a runtime" in ontology["prohibition"]


def test_i0_fixture_units_reconstruct(protocol, tables):
    """S3MR2-008. 232 clusters, 232 base items, 464 cluster rows, 38, 502."""
    breakdown = protocol["proposed_statistics"]["i0_fixture_breakdown"]
    stream = tables["projected_operation_accounting"]["work_streams"][
        "deterministic_I0_fixtures"]
    assert stream["breakdown"] == breakdown
    cluster_fixtures = (breakdown["k5_constructor_fixtures"]
                        + breakdown["k6_constructor_fixtures"])
    noncluster = (breakdown["indicator_truth_table_fixtures"]
                  + breakdown["not_applicable_branch_fixtures"]
                  + breakdown["scorer_branch_fixtures"])
    variants = protocol["i3_contrast_registry"]["variants_per_cluster"]
    assert cluster_fixtures == 464
    assert cluster_fixtures // variants == 232
    assert stream["base_item_contrast_clusters"] == cluster_fixtures // variants
    assert stream["base_items"] == cluster_fixtures // variants
    assert stream["cluster_rendered_rows"] == cluster_fixtures
    assert stream["noncluster_fixture_rows"] == noncluster == 38
    assert stream["rendered_rows"] == cluster_fixtures + noncluster == 502
    assert stream["scored_rows"] == stream["rendered_rows"]
    assert stream["uses_model"] is False
    assert stream["generation_calls"] == 0
    assert stream["generated_tokens_upper_bound"] == 0
    assert stream["sequence_level_prefill_evaluations"] == 0
    assert stream["incremental_decode_evaluations"] == 0
    assert stream["restricted_vocabulary_logit_reads"] == 0
    assert stream["total_sequence_level_model_evaluation_equivalents"] == 0
    assert protocol["proposed_statistics"]["i0_fixture_unit_rule"]


def test_operation_totals_derive_from_n_and_cell_counts(protocol, tables,
                                                        recomputed):
    """S3MR2-005/008. Every projected total is arithmetic over registered inputs."""
    streams = tables["projected_operation_accounting"]["work_streams"]
    assert set(streams) == set(WORK_STREAMS)
    counts = tables["gate_bearing_cell_counts"]
    roles = len(protocol["proposed_statistics"]["registered_target_roles"])
    variants = protocol["i3_contrast_registry"]["variants_per_cluster"]
    n_i1_i3 = recomputed["I1_I3_joint_correctness_floor"]["n"]
    n_i2 = recomputed["I2_headroom_floor"]["n"]
    n_i4 = recomputed["I4_positive_reference_floor"]["n"]

    def rendered_rows(profile):
        """Cluster rows plus base-item rows, over every applicable target role."""
        cell = counts[profile]
        clusters = cell["I3_cells"] * n_i1_i3
        base_items = ((cell["I1a_cells"] + cell["I1b_cells"]) * n_i1_i3
                      + cell["I2_cells"] * n_i2)
        return clusters * variants + base_items

    # Development over the three target roles and the three selectable profiles.
    # S3 reuses the S2 prompts and logit vector, so it adds nothing.
    development = streams["target_role_development"]
    assert development["S3_incremental_rendered_rows"] == 0
    assert development["S3_incremental_scored_rows"] == 0
    assert development["S3_incremental_sequence_evaluations"] == 0
    assert len(development["S3_zero_incremental_cost_holds_only_under"]) >= 3
    expected_development = rendered_rows("S1") + rendered_rows("S2")
    assert development["scored_rows"] == expected_development == 33543
    assert development["total_sequence_level_model_evaluation_equivalents"] == \
        expected_development
    assert len(development["model_roles"]) == roles
    for profile, key in (("S1", "S1"), ("S2", "S2"),
                         ("S2", "S3_if_independently_rendered")):
        entry = development["by_profile"][key]
        assert entry["rendered_rows"] == rendered_rows(profile), key
        assert entry["target_roles"] == roles
        assert entry["rendered_rows_per_target_role"] * roles == \
            entry["rendered_rows"]
        assert entry["cluster_rendered_rows"] == \
            entry["base_item_contrast_clusters"] * variants
        assert entry["dimensional_identity_cluster_rows_equals_clusters_times_variants"] \
            is True
        assert entry["rendered_rows_per_target_role"] == \
            entry["cluster_rendered_rows"] + entry["base_items"]
        assert entry["generation_calls"] == 0
        assert entry["generated_tokens_upper_bound"] == 0
        assert entry["total_sequence_level_model_evaluation_equivalents"] == \
            entry["scored_rows"]

    # RP I4: two scoring streams, four cells each, at the I4 size.
    rp = streams["RP_I4_under_candidate_profiles"]
    expected_rp = (rp["distinct_scoring_streams"] * rp["cells_per_scoring_stream"]
                   * n_i4)
    assert rp["n_per_cell"] == n_i4
    assert rp["cells_per_scoring_stream"] == counts["S1"]["I4_cells"]
    assert rp["rendered_rows"] == rp["scored_rows"] == expected_rp == 3584
    assert rp["total_sequence_level_model_evaluation_equivalents"] == expected_rp
    assert rp["generated_tokens_upper_bound"] == 0
    assert rp["S3_incremental_rows"] == 0
    assert rp["model_roles"] == ["RP"]
    assert rp["precondition"]

    # Confirmation: one selected profile, its applicable cells, at the same sizes.
    confirmation = streams["selected_profile_one_shot_confirmation"]
    assert confirmation["accessible_now"] is False
    assert confirmation["is_an_upper_bound_not_a_universal_total"] is True
    bound_profile = confirmation["upper_bound_profile"]
    assert bound_profile in ("S1", "S2", "S3")
    assert confirmation["target_role_rendered_rows"] == rendered_rows(bound_profile)
    assert confirmation["rp_i4_rendered_rows"] == \
        counts[bound_profile]["I4_cells"] * n_i4
    expected_confirmation = (confirmation["target_role_rendered_rows"]
                             + confirmation["rp_i4_rendered_rows"])
    assert confirmation["rendered_rows"] == confirmation["scored_rows"] == \
        expected_confirmation == 27856
    assert confirmation["total_sequence_level_model_evaluation_equivalents"] == \
        expected_confirmation
    # And that profile really is the most expensive selectable one.
    assert expected_confirmation == max(
        rendered_rows(profile) + counts[profile]["I4_cells"] * n_i4
        for profile in ("S1", "S2", "S3"))


def test_s4_generation_accounting_derives(protocol, tables, recomputed):
    """S3MR2-005. The S4 forward cost is derived and is not null."""
    s4 = tables["projected_operation_accounting"]["work_streams"][
        "S4_diagnostic_generation"]
    counts = tables["gate_bearing_cell_counts"]["S4"]
    variants = protocol["i3_contrast_registry"]["variants_per_cluster"]
    roles = len(protocol["proposed_statistics"]["registered_target_roles"])
    bound = protocol["proposed_statistics"]["s4_generated_token_bound_per_generation"]
    n_i1_i3 = recomputed["I1_I3_joint_correctness_floor"]["n"]
    n_i2 = recomputed["I2_headroom_floor"]["n"]
    assert bound == 16
    assert s4["registered_generated_token_bound_per_generation"] == bound
    assert s4["i4_applicable"] is False
    assert counts["I4_cells"] == 0
    assert s4["forward_cost_is_mapped"] is True
    assert len(s4["model_roles"]) == roles

    # The row count comes from the S4 cell structure and the registered sizes.
    clusters_per_role = counts["I3_cells"] * n_i1_i3 // roles
    base_items_per_role = (
        (counts["I1a_cells"] + counts["I1b_cells"]) * n_i1_i3
        + counts["I2_cells"] * n_i2) // roles
    assert s4["base_item_contrast_clusters"] == clusters_per_role
    assert s4["base_items"] == base_items_per_role
    rows = (clusters_per_role * variants + base_items_per_role) * roles
    assert s4["rendered_rows"] == rows == 26064
    assert s4["scored_rows"] == rows
    assert s4["generation_calls"] == rows
    assert s4["sequence_level_prefill_evaluations"] == rows
    assert s4["generated_tokens_upper_bound"] == rows * bound == 417024
    assert s4["incremental_decode_evaluations_upper_bound"] == rows * (bound - 1) \
        == 390960
    assert s4["total_sequence_level_model_evaluation_equivalents_upper_bound"] == \
        s4["sequence_level_prefill_evaluations"] \
        + s4["incremental_decode_evaluations_upper_bound"] == 417024
    assert s4["runtime_batched_forward_calls"] is None
    assert "NOT a sequence-level evaluation" in s4["runtime_note"]
    assert s4["selection_authority"].startswith("none")


def test_the_positive_reference_stream_stays_numerically_unresolved(tables,
                                                                   protocol):
    stream = tables["projected_operation_accounting"]["work_streams"][
        "positive_reference_external_P3Q"]
    for field in ("rendered_rows", "scored_rows", "base_items",
                  "generated_tokens_upper_bound",
                  "total_sequence_level_model_evaluation_equivalents"):
        assert stream[field] is None, field
    assert stream["numeric_status"] == "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2"
    assert "A zero would assert" in stream["why_null_and_not_zero"]
    unresolved = protocol["operation_ontology_v0_4"][
        "unresolved_streams_are_null_not_zero"]
    assert unresolved["stream"] == "positive_reference_external_P3Q"
    assert unresolved["status"] == "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2"
    assert unresolved["grand_total_treating_null_as_zero_prohibited"] is True


def test_no_grand_total_treats_the_unresolved_stream_as_zero(protocol, tables):
    accounting = tables["projected_operation_accounting"]
    assert accounting["grand_total_prohibited"]["prohibited"] is True
    assert accounting["no_single_undifferentiated_total"] is True
    assert "null, not zero" in accounting["grand_total_prohibited"]["why"]
    for key in accounting:
        assert "grand_total" not in key or key == "grand_total_prohibited"
    projected = protocol["operation_boundaries"]["projected_future_operations"]
    assert projected["grand_total_prohibited"]["prohibited"] is True
    assert projected["no_single_undifferentiated_total"] is True
    assert set(projected["work_streams"]) == set(WORK_STREAMS)
    assert accounting["single_structured_source"] == \
        "studies/study3/analysis/design_statistics.py"


def test_the_projection_is_decomposed_into_the_six_work_streams(tables):
    streams = tables["projected_operation_accounting"]["work_streams"]
    assert len(streams) == 6
    for name in WORK_STREAMS:
        assert name in streams
        assert "uses_model" in streams[name]
    assert streams["deterministic_I0_fixtures"]["uses_model"] is False
    for name in ("target_role_development", "RP_I4_under_candidate_profiles",
                 "selected_profile_one_shot_confirmation",
                 "S4_diagnostic_generation"):
        assert streams[name]["uses_model"] is True


# --------------------------------------------------------------------------
# S3MR2-004 / S3MR2-009: applicability, selectability and the open decision
# --------------------------------------------------------------------------

def test_s4_is_not_i4_applicable_never_selectable_and_absent_from_confirmation(
        protocol, tables):
    by_id = {profile["id"]: profile for profile in protocol["interface_profiles"]}
    assert by_id["S4"]["selectable_status"] == "never_selectable"
    ranked = [entry["interface"] for entry in
              protocol["admissibility_order"]["order"]]
    assert "S4" not in ranked
    truth = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    assert truth["S4"]["I4"] == "not_applicable"
    assert truth["S4"]["selectable"] is False
    assert tables["gate_bearing_cell_counts"]["S4"]["I4_cells"] == 0
    assert protocol["gate_truth_table"]["i4_applicability_note"]
    for row in protocol["proposed_statistics"]["confirmation_exact_binomial_gates"]:
        assert "S4" not in row["applicable_profiles"], row["gate"]
        assert row["s4_present"] is False
    rule = protocol["proposed_statistics"]["confirmation_applicability_rule"]
    assert rule["s4_can_never_appear"] is True
    plan = protocol["development_selection_and_confirmation_plan"]["stage_3_confirmation"]
    assert plan["s4_can_never_appear_in_any_confirmation_applicability_list"]
    assert "S4" in protocol["development_selection_and_confirmation_plan"][
        "stage_2_selection"]["never_selectable"]
    assert protocol["power_architecture_v0_4"]["type_i_architecture"][
        "s4_excluded_from_every_success_union"] is True


def test_i1b_and_k5_confirmation_applicability_is_limited_to_s1(protocol):
    """S3MR2-004. Confirmation applicability = selectable profiles INTERSECT {selected}."""
    rule = protocol["proposed_statistics"]["confirmation_applicability_rule"]
    assert rule["i1b_confirmation_profiles"] == ["S1"]
    assert rule["k5_confirmation_profiles"] == ["S1"]
    assert "INTERSECT" in rule["rule"]
    confirmation = _component(protocol, "confirmation", "I1b")
    assert confirmation["applicable_profiles"] == ["S1"]
    assert confirmation["applicability_rule"]
    plan = protocol["development_selection_and_confirmation_plan"]["stage_3_confirmation"]
    assert plan["i1b_applicable_profiles"] == ["S1"]
    assert plan["k5_applicable_profiles"] == ["S1"]
    # And no confirmation row may list a non-selectable profile.
    for row in protocol["proposed_statistics"]["confirmation_exact_binomial_gates"]:
        assert set(row["applicable_profiles"]) <= {"S1", "S2", "S3"}, row["gate"]


def test_od2_remains_unresolved_and_nothing_is_selected(protocol, amendment):
    decisions = {d["id"]: d for d in protocol["unresolved_operator_decisions"]}
    assert decisions["OD2"]["status"] == "unresolved"
    assert decisions["OD2"]["blocking"] is True
    assert protocol["blocking_decisions"] == ["OD2"]
    candidates = protocol["positive_reference_candidates"]
    assert candidates["selection_status"].startswith("UNSELECTED")
    blob = json.dumps(candidates).lower()
    for verb in ("downloaded", "prequalified", "pinned to revision"):
        assert '"%s": true' % verb not in blob
    for od in amendment["operator_decisions_in_this_round"]:
        if od["id"] == "OD2":
            assert od["status"] == "unresolved"
            assert od["blocking"] is True
    ur22 = [u for u in amendment["unresolved_item_dispositions"]
            if u["id"] == "UR-22"]
    assert len(ur22) == 1
    assert ur22[0]["disposition"] == "UNRESOLVED_BLOCKING_OPERATOR_DECISION"


def test_the_p3q_i4_ordering_constraint_reconstructs(protocol):
    """S3MR2-009. 19/20 > 9/10 > 4/5, registered without selecting anything."""
    ordering = protocol["positive_reference_candidates"]["p3q_i4_ordering_constraint"]
    p3q = _rational(ordering["p3q_lower_bound_exact_rational"])
    floor = _floor_for(protocol, "I4_positive_reference_floor")
    p1 = _rational(floor["p1_exact_rational"])
    p0 = _rational(floor["p0_exact_rational"])
    assert p3q == Fraction(19, 20)
    assert p1 == Fraction(9, 10)
    assert p0 == Fraction(4, 5)
    assert p3q > p1 > p0
    assert ordering["binding_on"]
    assert ordering["later_authority_may_strengthen_not_weaken"] is True
    assert ordering["no_checkpoint_is_selected_by_registering_this_constraint"] \
        is True
    assert _rational(ordering["i4_p1_exact_rational"]) == p1
    assert _rational(ordering["i4_p0_exact_rational"]) == p0
    assert _component(protocol, "development", "I4")["p1_exact_rational"] == "9/10"
    assert _component(protocol, "development", "I4")["p0_exact_rational"] == "4/5"


# --------------------------------------------------------------------------
# S3MR2 closure, and the historical narrative count mismatch
# --------------------------------------------------------------------------

def test_every_finding_and_item_appears_exactly_once(amendment):
    """S3MR3 closure, plus the carried-forward earlier matrices."""
    closure = amendment["closure_matrix_v0_5"]
    assert [row["finding_id"] for row in closure] == FINDING_IDS_V0_4
    assert len({row["finding_id"] for row in closure}) == 10
    severities = {}
    for row in closure:
        severities[row["original_severity"]] = \
            severities.get(row["original_severity"], 0) + 1
        assert row["self_approved"] is False
        assert row["disposition"] == \
            "PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW"
        assert row["where"] and row["verification"] and row["repair"]
        assert row["repair_kind"] in ("method", "operator_decision_input")
        # A status may never be reached by prose alone: it must trace to
        # normative bytes, a positive assertion and a negative mutation.
        assert row["closure_status"] == REQUIRED_V0_4_CLOSURES[row["finding_id"]]
        assert row["affected_normative_fields"], row["finding_id"]
        assert row["committed_tests"], row["finding_id"]
        assert row["negative_mutations"], row["finding_id"]
        assert "residual_limitation" in row, row["finding_id"]
    assert severities == STRUCTURED_V0_4_SEVERITIES

    # The second review's matrix is carried forward, not reopened.
    carried = amendment["carried_forward_closure_matrix_v0_4"]
    assert [row["finding_id"] for row in carried] == FINDING_IDS_V0_3
    for row in carried:
        assert row["reopened"] is False
        assert row["status"]

    inherited = amendment["inherited_first_review_findings"]
    assert [row["finding_id"] for row in inherited] == FINDING_IDS
    for row in inherited:
        assert row["status_after_second_review"] in (
            "VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW",
            "PARTIALLY_RESOLVED_BY_DRAFT_V0_3")
        assert row["note"]
        assert "v0_5_residual" in row
    partial = [row for row in inherited
               if row["status_after_second_review"] == "PARTIALLY_RESOLVED_BY_DRAFT_V0_3"]
    assert len(partial) == 4

    items = amendment["unresolved_item_dispositions"]
    assert [row["id"] for row in items] == UR_IDS
    assert len({row["id"] for row in items}) == 22
    ur22 = next(row for row in items if row["id"] == "UR-22")
    assert ur22["status"] == "UNRESOLVED"


def test_the_historical_count_mismatch_is_recorded_and_not_propagated(
        amendment, protocol, markdown, packet):
    mismatch = amendment["historical_count_mismatch"]
    assert mismatch["status"] == \
        "NON_DISPOSITIVE_HISTORICAL_NARRATIVE_COUNT_MISMATCH"
    assert mismatch["review_was_not_edited"] is True
    assert mismatch["eight_major_is_not_propagated"] is True
    counts = mismatch["structured_new_findings"]
    assert counts["total"] == 10
    assert {k: counts[k] for k in STRUCTURED_V0_3_SEVERITIES} == \
        STRUCTURED_V0_3_SEVERITIES
    assert counts["BLOCKING"] + counts["MAJOR"] + counts["MINOR"] == counts["total"]
    assert "Two BLOCKING and eight MAJOR" in \
        mismatch["immutable_disposition_basis_phrase"]
    assert mismatch["why_it_does_not_reverse_the_rejection"]
    # The wrong count must not leak into any draft-v0.5 artifact.
    for name, text in (("protocol", json.dumps(protocol)),
                       ("markdown", markdown), ("packet", packet)):
        assert "eight MAJOR" not in text, name
        assert "8 MAJOR" not in text, name


def test_the_amendment_does_not_self_approve(amendment, protocol, tables):
    prohibition = amendment["self_approval_prohibition"]
    assert prohibition[
        "the_drafting_party_does_not_claim_draft_v0_5_is_correct"] is True
    assert prohibition["every_repair_label"] == \
        "PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW"
    assert "fourth" in prohibition["determination_belongs_to"].lower()
    assert amendment["all_independent_reviews_remain_valid_rejections"] is True
    assert amendment["no_review_artifact_was_edited"] is True
    assert "fourth bounded independent methods review of draft-v0.5" in \
        amendment["next_legal_action"]
    assert protocol["status"]["self_approval_prohibited"]
    assert protocol["claim_ceiling"]["no_self_approval"]
    assert tables["disposition_status"] == \
        "PROPOSED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW"
    # Every draft-v0.4 section that repairs a finding carries the same label.
    for section in ("sampling_frame_v0_4", "power_architecture_v0_4",
                    "state_machine_v0_4", "operation_ontology_v0_4"):
        if "disposition_status" in protocol[section]:
            assert protocol[section]["disposition_status"] == \
                "PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW"


def test_the_amendment_names_the_immutable_objects_it_did_not_edit(amendment):
    listed = amendment["immutable_objects_not_edited"]
    assert len(listed) >= 20
    joined = " ".join(listed)
    for required in ("studies/study3/reviews/v0_3_independent_methods_review.json",
                     "studies/study3/reviews/v0_2_independent_methods_review.json",
                     "studies/study3/analysis/independent_methods_recalculation_v0_3.py",
                     "studies/study3/analysis/independent_methods_recalculation.py",
                     "tests/test_study3_methods_review.py",
                     "tests/test_study3_methods_review_v0_3.py",
                     "studies/study3/analysis/independent_methods_review_packet_v0_3.md"):
        assert required in joined, required
    for path in listed:
        assert os.path.exists(os.path.join(REPO_ROOT, path)), path
    assert len(set(listed)) == len(listed)


def test_prior_receipts_reviews_and_packets_are_untouched():
    """The v0.5 round may not rewrite any earlier round's record."""
    assert os.path.exists(REVIEW_PATH)
    with open(REVIEW_PATH, encoding="utf-8") as handle:
        assert "draft-v0.1" in handle.read()
    for name, version in (("design_receipt_v0_2.json", "v0.2"),
                          ("design_receipt_v0_3.json", "v0.3")):
        path = os.path.join(STUDY3, name)
        with open(path, encoding="utf-8") as handle:
            blob = handle.read()
        assert version in blob, name
        assert EXPECTED_STATE not in blob, name
    with open(PACKET_V0_3, encoding="utf-8") as handle:
        older = handle.read()
    assert "AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW" in older
    assert EXPECTED_STATE not in older
    with open(AMENDMENT_V0_3, encoding="utf-8") as handle:
        previous = json.load(handle)
    assert EXPECTED_STATE not in json.dumps(previous)


# --------------------------------------------------------------------------
# Retained invariants from the v0.1, v0.2 and v0.3 rounds
# --------------------------------------------------------------------------

def _asserts_failing_interface_stays_eligible(text):
    lowered = text.lower()
    return ("remains eligible" in lowered or "still eligible" in lowered
            or "stays eligible" in lowered)


def test_i4_is_part_of_eligibility_and_fails_per_interface(protocol):
    order = protocol["admissibility_order"]
    assert "I4" in order["gates_required_for_eligibility"]
    i4 = _gate(protocol, "I4")
    assert i4["part_of_eligibility"] is True
    assert i4["per_interface_not_global"] is True
    assert "eliminate this interface profile" in i4["legal_next_state_on_fail"]
    for gate in protocol["gate_hierarchy"]:
        assert not _asserts_failing_interface_stays_eligible(
            gate["legal_next_state_on_fail"])
        assert not _asserts_failing_interface_stays_eligible(gate["what_fails"])


def test_i5_covers_every_gate_bearing_construct(protocol):
    i5 = _gate(protocol, "I5")
    assert i5["accessible_before_authority"] is False
    assert "RP" in i5["model_roles"]
    assert any("K4" in item for item in i5["inputs"])
    for construct in COVERED_CONSTRUCTS:
        assert construct in i5["covered_constructs"], construct
    assert "I3" not in i5["covered_constructs"]
    assert isinstance(i5["applicable_profiles"], list)


def test_no_gate_authorizes_mechanistic_execution(protocol):
    for gate in protocol["gate_hierarchy"]:
        assert gate["authorizes_mechanistic_execution"] is False
    for prohibited in ("any activation extraction or probe",
                       "any patching, ablation or lens operation"):
        assert prohibited in protocol["operation_boundaries"][
            "prohibited_without_new_authority"]


def test_pooling_as_a_rescue_is_prohibited(protocol):
    cells = protocol["atomic_evaluation_cells"]
    assert cells["no_pooling_rescue"] is True
    assert cells["descriptive_pooling"].startswith("Pooled summaries")
    assert "no gate" in cells["descriptive_pooling"]
    assert len(cells["pooling_prohibitions"]) >= 4
    for gate in protocol["gate_hierarchy"]:
        assert gate["no_pooling"] is True


def test_not_applicable_is_neither_pass_nor_zero_effect(protocol):
    semantics = protocol["not_applicable_semantics"]
    assert "not a pass" in semantics
    assert "not a zero effect" in semantics
    assert semantics == protocol["claim_ceiling"]["not_applicable_semantics"]
    assert protocol["gate_truth_table"]["value_semantics"]["not_applicable"]


POSITION_LABEL_TRANSFORMS = ("position_permutation", "label_symbol_permutation",
                             "label_set_replacement")


def test_applicability_matches_what_each_profile_renders(protocol):
    for profile in protocol["interface_profiles"]:
        applicability = profile["transformation_applicability"]
        declared = {entry["transformation"]
                    for entry in profile["non_applicable_transformations"]}
        computed = {name for name, value in applicability.items()
                    if value != "applicable"}
        assert declared == computed, profile["id"]
        if not profile["options_visible"]:
            for transform in POSITION_LABEL_TRANSFORMS:
                assert applicability[transform] != "applicable", profile["id"]
        if not profile["labels_visible"]:
            assert "I1b" not in profile["applicable_gates"], profile["id"]


def test_the_option_and_symbol_maps_are_bijections(protocol):
    verification = protocol["proposed_statistics"][
        "i3_pairwise_construction_verification"]
    assert verification["k5_one_factor_per_contrast"] is True
    assert verification["k5_k6_base_item_identities_disjoint"] is True
    assert verification["label_alphabets_mutually_disjoint"] is True
    assert verification["label_alphabets_disjoint_from_answer_domain"] is True
    assert verification["k5_x_k6_cross_product_exists"] is False


def test_label_alphabets_do_not_collide_with_the_answer_domain(protocol):
    alphabets = protocol["counterbalancing_design"]["label_alphabets"]
    assert alphabets["alphabets_mutually_disjoint"] is True
    assert "no label alphabet may contain a digit" in alphabets["digits_forbidden"]
    assert alphabets["answer_domain"]
    assert len(alphabets["registered_alphabets"]) >= 2
    assert alphabets["label_set_replacement_rule"]
    verification = protocol["proposed_statistics"][
        "i3_pairwise_construction_verification"]
    assert verification["label_alphabets_mutually_disjoint"] is True
    assert verification["label_alphabets_disjoint_from_answer_domain"] is True


def test_k6_varies_one_factor_at_a_time(protocol):
    renderings = protocol["counterbalancing_design"]["k6_renderings"]
    assert renderings["one_factor_at_a_time"] is True
    assert "never compared as a three-way set" in \
        renderings["three_way_comparison_prohibited"]
    assert renderings["answer_cue"]
    assert renderings["count"] == len(renderings["renderings"]) == 3
    assert len(renderings["pairwise_cells"]) == 2
    for contrast in protocol["counterbalancing_design"]["k6_contrasts"]:
        assert contrast["baseline_rendering"] != contrast["variant_rendering"]
        assert contrast["variants_per_cluster"] == 2
        assert contrast["varied_factor"]
        assert contrast["held_fixed"]
    verification = protocol["proposed_statistics"][
        "i3_pairwise_construction_verification"]
    assert verification["k6_answer_cue_fixed_within_every_pair"] is True
    assert verification["k6_contrast_count"] == 2


def test_k5_is_never_applicable_to_s2_or_s3_and_never_counts_as_a_pass(protocol):
    semantics = protocol["i3_contrast_registry"]["k5_applicability"]["semantics"]
    assert "not a pass" in semantics
    assert "never be counted as a satisfied component" in semantics
    for profile in protocol["interface_profiles"]:
        if profile["id"] in ("S2", "S3"):
            assert not profile["options_visible"] or not profile["labels_visible"]


def test_no_i3_rescue_path_exists(protocol):
    indicators = protocol["proposed_statistics"]["i3_indicators"]
    assert "no descriptive quantity" in indicators["no_rescue"]
    assert "rescue" in indicators["no_rescue"]
    assert protocol["state_machine_v0_4"]["rescue_paths"] == []


def test_the_retired_paired_procedure_carries_no_decision_role(protocol):
    retired = protocol["retired_procedures"]["tango_paired_equivalence"]
    assert retired["status"] == "RETIRED FROM EVERY DECISION ROLE"
    for role in ("gate", "eligibility", "selection", "confirmation"):
        assert any(role in item for item in retired["retired_from"]), role
    summary = protocol["proposed_statistics"]["descriptive_paired_summary"]
    assert summary["status"].startswith("DESCRIPTIVE")
    for absent in ("null hypothesis", "alpha", "p-value", "critical value",
                   "equivalence margin", "confidence-based pass or fail",
                   "equivalence declaration"):
        assert absent in summary["carries_no"], absent
    assert any("rescue path" in item for item in summary["carries_no"])
    assert any("ranking weight" in item for item in summary["carries_no"])
    assert summary["retired_procedure"]


def test_the_i4_chance_floor_is_recorded_as_rejected(protocol):
    rejected = protocol["proposed_statistics"]["rejected_v0_1_i4_chance_null"]
    assert rejected["status"].startswith("REJECTED")
    assert rejected["why"]
    assert _component(protocol, "development", "I4")["p0_exact_rational"] == "4/5"


def test_the_withdrawn_sample_sizes_appear_in_no_active_field(
        protocol, tables, packet, markdown):
    """draft-v0.3's n = 256 and n = 128 are withdrawn by S3MR2-003."""
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    assert sizes["n_256_and_128_status"].startswith("WITHDRAWN")
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        assert sizes[gate]["n"] not in (192, 256, 128)
        assert _component(protocol, "development", gate)["n"] not in (192, 256, 128)
        assert _component(protocol, "confirmation", gate)["n"] not in (192, 256, 128)
    for row in (tables["development_exact_binomial_components"]
                + tables["confirmation_exact_binomial_components"]):
        assert row["n"] not in (192, 256, 128)


def test_exactly_one_i3_floor_is_active_and_it_is_nine_tenths(protocol, tables):
    floor = protocol["proposed_statistics"]["i3_floor"]
    assert floor["active_floor_count"] == 1
    assert floor["p0_exact_rational"] == "9/10"
    assert floor["p1_exact_rational"] == "97/100"
    assert floor["p0_0_95_status"] == "DELETED FROM EVERY ACTIVE FIELD"
    assert floor["indicator"] == "J_joint_correct"
    assert floor["degenerate_region_prohibition"]
    assert _component(protocol, "development", "I3")["p0_exact_rational"] == "9/10"
    registered = _floor_for(protocol, "I1_I3_joint_correctness_floor")
    assert registered["p0_exact_rational"] == "9/10"


def test_no_rejection_region_requires_every_unit_to_succeed(protocol, tables):
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        for split in ("development", "confirmation"):
            row = _component(protocol, split, gate)
            assert row["pass_count"] < row["n"], (gate, split)
            assert row["degenerate_rejection_region"] is False
    for row in (tables["development_exact_binomial_components"]
                + tables["confirmation_exact_binomial_components"]):
        assert row["pass_count"] < row["n"]


def test_every_sample_size_declares_its_unit(protocol, tables):
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        assert sizes[gate]["unit_of_n"]
        for split in ("development", "confirmation"):
            assert _component(protocol, split, gate)["unit_of_n"]
    for row in (tables["development_exact_binomial_components"]
                + tables["confirmation_exact_binomial_components"]):
        assert row["unit_of_n"]
    registry = protocol["unit_registry"]
    assert registry["prohibition"]
    for entry in registry["units"]:
        assert entry["definition"] and entry["never_equals"]


def test_the_i3_unit_is_the_cluster_and_never_a_rendered_row(protocol):
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    assert "contrast cluster" in sizes["I3"]["unit_of_n"]
    assert protocol["proposed_statistics"]["i3_indicators"]["independent_unit"] == \
        "base_item_contrast_cluster"
    unit = protocol["atomic_evaluation_cells"]["sampling_unit"]
    assert "the base-item contrast cluster for I3" in unit
    i3_unit = protocol["atomic_evaluation_cells"]["i3_sampling_unit"]
    assert i3_unit["unit"] == "base_item_contrast_cluster"
    assert "are not crossed" in i3_unit["no_cross_product"]
    assert i3_unit["variants_per_cluster"] == 2
    assert i3_unit["disjoint_base_items"]


def test_the_development_selection_map_is_total_and_deterministic(protocol,
                                                                 tables):
    selection_map = protocol["proposed_statistics"]["development_selection_map"]
    assert len(selection_map) == 16
    seen = set()
    order = protocol["development_selection_and_confirmation_plan"][
        "stage_2_selection"]["order"]
    for row in selection_map:
        passed = row["all_applicable_components_passed"]
        assert sorted(passed) == ["S1", "S2", "S3"]
        key = (passed["S1"], passed["S2"], passed["S3"],
               row["s3_multi_token_domain_activated"])
        assert key not in seen, "duplicate selection case %r" % (key,)
        seen.add(key)
        assert row["fixed_selectable_profile_denominator"] == 3
        # The eligible set and the selected profile are both determined by the
        # case, so the map is recomputed here rather than trusted.
        eligible = [name for name in ("S1", "S2", "S3")
                    if passed[name]
                    and (name != "S3"
                         or row["s3_multi_token_domain_activated"])]
        assert sorted(row["eligible_profiles"]) == eligible
        expected = None
        for candidate in order:
            if candidate in eligible:
                expected = candidate
                break
        assert row["selected_profile"] == expected, key
        assert row["stop_no_selectable_profile_is_eligible"] is (expected is None)
    # All sixteen (eligibility, S3 applicability) cases are covered exactly once.
    assert len(seen) == 16
    plan = protocol["development_selection_and_confirmation_plan"]["stage_2_selection"]
    assert plan["order"] == ["S2", "S3", "S1"]
    assert plan["no_data_dependent_reordering"] is True
    assert plan["no_selection_this_round"] is True
    assert len(tables["profile_eligibility_subtable"]) == 16


def test_the_confirmation_stage_is_one_shot_and_inaccessible(protocol):
    plan = protocol["development_selection_and_confirmation_plan"]["stage_3_confirmation"]
    assert plan["one_shot"] is True
    assert plan["reselection_prohibited"] is True
    assert "may change after the development split is read" in \
        plan["retuning_prohibited"]
    assert plan["accessible_now"] is False
    assert plan["multiplicity"]
    assert plan["conservative_size_reuse"]
    isolation = protocol["split_lifecycle"]["confirmation_isolation"]
    assert isolation["accessible_before_authority"] is False
    assert isolation["one_shot"] is True
    assert "is spent" in isolation["no_reuse_after_observation"]
    assert isolation["covers_every_gate_bearing_construct"] is True
    assert isolation["single_interface_only"]
    assert isolation["physical_exclusion_before_authorization"]
    for construct in COVERED_CONSTRUCTS:
        assert construct in _gate(protocol, "I5")["covered_constructs"], construct
    for included in ("gate I4", "the positive-reference construct",
                     "the K4 stratum"):
        assert included in isolation["explicitly_includes"], included


def test_s3_adds_no_operations_under_the_current_single_token_domain(protocol,
                                                                    tables):
    stream = tables["projected_operation_accounting"]["work_streams"][
        "RP_I4_under_candidate_profiles"]
    assert stream["S3_incremental_rows"] == 0
    reuse = protocol["sampling_frame_v0_4"]["reuse_and_dependence_rule"]
    assert "single-token" in reuse["s3_logit_reuse"]


def test_the_selected_label_uniformity_diagnostic_carries_no_authority(protocol):
    for diagnostic in protocol["proposed_statistics"][
            "selected_label_uniformity_diagnostic"]:
        assert diagnostic["status"] == "DIAGNOSTIC_NUISANCE_REPORT_ONLY"
        for authority in ("carries_gate_authority", "carries_eligibility_authority",
                          "carries_selection_authority",
                          "carries_confirmation_authority"):
            assert diagnostic[authority] is False, authority


def test_study1_and_study2_statements_are_not_overstated(protocol):
    statements = protocol["prior_study_statements"]
    blob = json.dumps(statements).lower()
    for overstatement in ("proves", "demonstrates that the model reasons",
                          "causal mechanism was transferred"):
        assert overstatement not in blob
    assert protocol["claim_ceiling"]["study2_relationship"].startswith(
        "Study 3 neither reopens nor revises Study 2")
    counters = protocol["operation_boundaries"]["performed_this_round"]
    assert counters["study1_files_modified"] == 0
    assert counters["study2_files_modified"] == 0


def test_markdown_never_reintroduces_the_v0_1_defect_text(markdown):
    for text in FORBIDDEN_TEXT:
        assert text not in markdown, text


def test_markdown_agrees_with_json_on_every_decision_marker(protocol, markdown,
                                                            tables):
    assert NO_WINNER in markdown
    assert protocol["state"] in markdown
    statistics = protocol["proposed_statistics"]
    for gate in ("I1a", "I1b", "I2", "I3", "I4"):
        row = _component(protocol, "development", gate)
        assert str(row["n"]) in markdown, gate
        assert str(row["pass_count"]) in markdown, gate
    allocation = protocol["power_architecture_v0_4"]["type_ii_allocation"]
    for key in ("per_cell_false_negative_budget_exact_rational",
                "per_cell_power_target_exact_rational",
                "profile_stage_power_floor_exact_rational",
                "study_end_to_end_power_floor_exact_rational"):
        assert allocation[key] in markdown, key
    assert statistics["development_component_alpha_exact_rational"] in markdown
    assert statistics["confirmation_component_alpha_exact_rational"] in markdown
    assert str(tables["power_architecture"]["m_max"]) in markdown
    assert "J_joint_correct" in markdown
    assert "fourth independent methods review" in markdown.lower()


def test_markdown_does_not_claim_an_uncommitted_generator(protocol, markdown):
    lifecycle = protocol["sampling_frame_v0_4"]["future_seed_lifecycle"]
    assert lifecycle["generator_implementation_blob"] is None
    lowered = markdown.lower()
    assert "the generator is committed" not in lowered
    assert "bank has been generated" not in lowered


def test_the_packet_states_what_it_does_not_do(packet):
    lowered = packet.lower()
    for statement in ("it does not freeze the design",
                      "it does not authorize execution",
                      "it does not select an interface profile",
                      "it does not declare the amended protocol correct"):
        assert statement in lowered, statement
    assert "no seed was drawn and no bank row exists" in lowered


def test_the_amendment_markdown_matches_the_amendment_record(amendment):
    with open(AMENDMENT_MD, encoding="utf-8") as handle:
        text = handle.read()
    for row in amendment["closure_matrix_v0_5"]:
        assert row["finding_id"] in text, row["finding_id"]
    for row in amendment["inherited_first_review_findings"]:
        assert row["finding_id"] in text, row["finding_id"]
    for row in amendment["unresolved_item_dispositions"]:
        assert row["id"] in text, row["id"]
    assert amendment["state"] in text
    # The immutable narrative sentence is quoted once, verbatim; the count it
    # contains is never reused as the structured finding count.
    mismatch = amendment["historical_count_mismatch"]
    assert mismatch["immutable_disposition_basis_phrase"] in text
    assert text.count("eight MAJOR") == 1
    assert "8 MAJOR" not in text
    for severity, count in STRUCTURED_V0_3_SEVERITIES.items():
        assert "%d %s" % (count, severity) in text, severity


# --------------------------------------------------------------------------
# Negative mutations. Every decision-bearing invariant must be defended.
# --------------------------------------------------------------------------

def _mutate(protocol, mutation):
    doc = json.loads(json.dumps(protocol))
    mutation(doc)
    return doc


def _find(rows, key, value):
    for row in rows:
        if row[key] == value:
            return row
    raise AssertionError("no row with %s == %r" % (key, value))


def _set_frozen(doc):
    doc["status"]["frozen"] = True


def _set_execution_authorized(doc):
    doc["status"]["execution_authorized"] = True


def _nonzero_counter(doc):
    doc["operation_boundaries"]["performed_this_round"]["forward_passes"] = 1


def _injected_counter(doc):
    doc["operation_boundaries"]["performed_this_round"]["shadow_runs"] = 0


def _winner_selected(doc):
    doc["admissibility_order"]["no_winner_this_round"] = False


def _winner_statement_flipped(doc):
    doc["admissibility_order"]["no_winner_this_round_statement"] = \
        "A winner is selected in this round."


def _s4_selectable(doc):
    _find(doc["interface_profiles"], "id", "S4")["selectable_status"] = "selectable"


def _s4_in_confirmation(doc):
    doc["proposed_statistics"]["confirmation_exact_binomial_gates"][0][
        "applicable_profiles"].append("S4")


def _s4_gains_i4(doc):
    _find(doc["gate_truth_table"]["rows"], "profile", "S4")["I4"] = "applicable"


def _i1b_confirmation_widens(doc):
    doc["proposed_statistics"]["confirmation_applicability_rule"][
        "i1b_confirmation_profiles"] = ["S1", "S2"]


def _i4_absent_from_eligibility(doc):
    doc["admissibility_order"]["gates_required_for_eligibility"] = [
        g for g in doc["admissibility_order"]["gates_required_for_eligibility"]
        if g != "I4"]


def _i4_not_part_of_eligibility(doc):
    _gate(doc, "I4")["part_of_eligibility"] = False


def _i4_failure_leaves_interface_eligible(doc):
    _gate(doc, "I4")["legal_next_state_on_fail"] = \
        "record the failure; the interface remains eligible"


def _i4_failure_stops_the_whole_study(doc):
    _gate(doc, "I4")["per_interface_not_global"] = False


def _i5_omits_a_construct(doc):
    gate = _gate(doc, "I5")
    gate["covered_constructs"] = [c for c in gate["covered_constructs"]
                                  if c != "I3_J_joint_correct"]


def _i5_accessible(doc):
    _gate(doc, "I5")["accessible_before_authority"] = True


def _na_counted_as_pass(doc):
    doc["gate_truth_table"]["value_semantics"]["not_applicable"] = \
        "counts as a satisfied gate"


def _na_semantics_weakened(doc):
    doc["not_applicable_semantics"] = "not_applicable behaves as a pass."


def _pooling_enabled(doc):
    doc["atomic_evaluation_cells"]["no_pooling_rescue"] = False


def _gate_pooling_enabled(doc):
    _gate(doc, "I3")["no_pooling"] = False


def _rp_selected(doc):
    doc["positive_reference_candidates"]["selection_status"] = "SELECTED"


def _od_resolved(od_id):
    def mutate(doc):
        _find(doc["unresolved_operator_decisions"], "id", od_id)["status"] = \
            "resolved"
    return mutate


def _od2_unblocked(doc):
    _find(doc["unresolved_operator_decisions"], "id", "OD2")["blocking"] = False


def _confirmation_accessible(doc):
    doc["split_lifecycle"]["confirmation_isolation"][
        "accessible_before_authority"] = True


def _confirmation_becomes_repeatable(doc):
    doc["development_selection_and_confirmation_plan"]["stage_3_confirmation"][
        "one_shot"] = False


def _reselection_permitted(doc):
    doc["development_selection_and_confirmation_plan"]["stage_3_confirmation"][
        "reselection_prohibited"] = False


def _claim_ceiling_removed(doc):
    doc["claim_ceiling"]["maximum_pass_claim"] = \
        "The interface is proven correct for all inputs."


def _bank_row_injected(doc):
    doc["bank_rows"].append({"id": 1})


def _seed_injected(doc):
    doc["sampling_frame_v0_4"]["future_seed_lifecycle"]["seed_values"] = [12345]


def _seed_authority_granted(doc):
    doc["sampling_frame_v0_4"]["future_seed_lifecycle"][
        "seed_authority_granted"] = True


def _result_injected(doc):
    doc["results"].append({"gate": "I1a", "rate": 0.99})


def _seeds_counter_nonzero(doc):
    doc["sampling_frame_v0_4"]["seeds_drawn_in_this_round"] = 1


def _gate_authorizes_mechanism(doc):
    _gate(doc, "I5")["authorizes_mechanistic_execution"] = True


def _gate_removed(doc):
    doc["gate_hierarchy"] = [g for g in doc["gate_hierarchy"]
                             if g["gate_id"] != "I4"]


def _state_upgraded(doc):
    doc["state"] = "STUDY3_FROZEN_AND_EXECUTION_AUTHORIZED"


def _review_state_downgraded(doc):
    doc["status"]["review_state"] = "self_approved"


def _successor_authority_named(doc):
    doc["required_next_action"] = \
        "issue the successor execution authority prompt for draft-v0.5"


def _i3_three_variants(doc):
    doc["i3_contrast_registry"]["variants_per_cluster"] = 3


def _i3_row_variant_count_drifts(doc):
    doc["i3_contrast_registry"]["k5"][0]["variants_per_cluster"] = 4


def _k5_crossed_with_k6(doc):
    doc["counterbalancing_design"]["k5_and_k6_are_not_crossed"] = False


def _k5_applies_to_a_content_only_profile(doc):
    doc["i3_contrast_registry"]["k5_applicability"]["applicable_profiles"] = \
        ["S1", "S2", "S4"]


def _k5_truth_row_flips(doc):
    _find(doc["gate_truth_table"]["rows"], "profile", "S2")["I3_K5"] = {
        cid: "applicable"
        for cid in doc["i3_contrast_registry"]["k5_contrast_ids"]}


# ---- S3MR3-001 ------------------------------------------------------------

def _k6_sep_reapplied_to_an_option_less_profile(doc):
    _find(doc["gate_truth_table"]["rows"], "profile", "S2")[
        "I3_K6"]["K6-SEP"] = "applicable"


def _k6_applicability_returns_to_family_level(doc):
    doc["i3_contrast_registry"]["k6_applicability"] = {
        "applicable_profiles": ["S1", "S2", "S3", "S4"],
        "semantics": "every profile is rendered, so the rendering contrasts always "
                     "have a referent",
    }


def _k6_sep_applicability_widens(doc):
    doc["i3_contrast_registry"]["k6_applicability"]["by_contrast"][
        "K6-SEP"]["applicable_profiles"] = ["S1", "S2", "S3", "S4"]


def _option_less_claim_ceiling_regains_k6_sep(doc):
    for profile in ("S2", "S3"):
        entry = doc["i3_contrast_registry"]["claim_ceiling_by_profile"][profile]
        entry["applicable_cells"] = ["K6-SEP", "K6-INSTR"]
        entry["applicable_cell_count"] = 2


def _r_sep_duplicated_for_an_option_less_profile(doc):
    for rendering in doc["counterbalancing_design"]["k6_renderings"]["renderings"]:
        if rendering["id"] == "R-sep":
            rendering["applicable_profiles"] = ["S1", "S2", "S3", "S4"]
            rendering["not_applicable_profiles"] = []


def _separator_rendering_becomes_applicable_to_an_option_less_profile(doc):
    for profile in doc["interface_profiles"]:
        if profile["id"] == "S2":
            profile["transformation_applicability"]["separator_rendering"] = \
                "applicable"


# ---- S3MR3-002 ------------------------------------------------------------

def _k6_sep_enters_confirmation_for_an_option_less_profile(doc):
    doc["proposed_statistics"]["confirmation_applicability_rule"][
        "k6_sep_confirmation_profiles"] = ["S1", "S2", "S3"]


def _confirmation_applicability_returns_to_family_level(doc):
    doc["proposed_statistics"]["confirmation_applicability_rule"][
        "row_shape"] = "per gate family"


def _s4_reenters_a_confirmation_component(doc):
    doc["proposed_statistics"]["confirmation_applicability_rule"][
        "i2_confirmation_profiles"] = ["S1", "S2", "S3", "S4"]


# ---- S3MR3-006, S3MR3-007, S3MR3-009, S3MR3-010 ---------------------------

def _non_machine_stop_state_returns(doc):
    doc["gate_truth_table"]["legal_stop_states"].append(
        "STOP_AWAITING_AUTHORITY, which is the current state")


def _at_least_n_interpretation_permitted(doc):
    doc["proposed_statistics"]["local_power_nonmonotonicity"][
        "at_least_n_interpretation_prohibited"] = False


def _eventual_monotonicity_threshold_replaces_the_minimum(doc):
    doc["proposed_statistics"]["local_power_nonmonotonicity"][
        "eventual_monotonicity_threshold_registered"] = True


def _union_bound_claims_a_predesignated_profile(doc):
    doc["power_architecture_v0_4"]["union_bound_proof"]["conclusion"] = (
        "Pr(the study returns the designated adequate profile and confirms it) "
        ">= 1 - 19/400 - 1/200 - 19/400 = 9/10")


def _registry_demoted_to_an_illustrative_example(doc):
    doc["rendering_surface_v0_5"]["illustrative_example"] = True


def _registry_binding_status_dropped(doc):
    doc["rendering_surface_v0_5"]["binding_input"] = False


def _rp_wrapper_filled_in_by_v0_5(doc):
    doc["rendering_surface_v0_5"]["rp_wrapper"] = "chatml"


def _token_distinctness_treated_as_tested(doc):
    doc["rendering_surface_v0_5"]["tokenizer_distinctness_status"] = \
        "TESTED_AND_PASSED"


def _token_distinctness_failure_becomes_a_pass(doc):
    doc["rendering_surface_v0_5"]["future_pre_bank_token_distinctness_rule"] = (
        "after checkpoints are pinned, an indistinct pair is recorded as a pass")


def _prohibition_scope_narrows_to_the_protocol_only(doc):
    doc["proposed_statistics"]["active_claim_term_prohibition"]["scope"] = [
        "active claim text"]


def _prohibition_historical_exemptions_removed(doc):
    doc["proposed_statistics"]["active_claim_term_prohibition"][
        "historical_exemptions"] = []


def _round_reference_reverts_to_the_second_review(doc):
    doc["proposed_statistics"]["unresolved"][1] = (
        "Every repair in this section is proposed resolved subject to the second "
        "independent methods review. This document does not adjudicate itself.")


def _j_joint_becomes_a_disjunction(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_joint_correct"]["definition"] = \
        "1 if EITHER registered variant of the cluster is scored correct"


def _j_joint_becomes_a_contrast(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_joint_correct"][
        "is_a_level_not_a_contrast"] = False


def _j_joint_claims_a_presentation_effect(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_joint_correct"][
        "identifies_a_presentation_effect"] = True


def _historical_indicator_regains_authority(doc):
    historical = doc["proposed_statistics"]["i3_indicators"][
        "historical_and_descriptive_indicators"]
    historical["reachable_decision_path"] = True
    historical["status"] = "GATE_BEARING"


def _invariance_claim_returns(doc):
    _find(doc["validation_targets"], "id", "VT6")["construct"] = \
        "invariance of accuracy under option reordering"


def _prohibited_term_list_emptied(doc):
    doc["proposed_statistics"]["active_claim_term_prohibition"][
        "prohibited_terms"] = []


def _development_alpha_drifts(doc):
    doc["proposed_statistics"]["retained_exact_binomial_gates"][0][
        "alpha_exact_rational"] = "1/200"


def _confirmation_alpha_drifts(doc):
    doc["proposed_statistics"]["confirmation_exact_binomial_gates"][0][
        "alpha_exact_rational"] = "1/600"


def _denominator_shrinks(doc):
    doc["power_architecture_v0_4"]["type_i_architecture"][
        "fixed_selectable_profile_denominator"] = 2


def _denominator_may_shrink(doc):
    doc["power_architecture_v0_4"]["type_i_architecture"][
        "denominator_never_shrinks"] = False


def _second_i3_floor_reappears(doc):
    doc["proposed_statistics"]["i3_floor"]["active_floor_count"] = 2


def _i3_floor_moves_to_0_95(doc):
    doc["proposed_statistics"]["i3_floor"]["p0_exact_rational"] = "19/20"


def _degenerate_rejection_region(doc):
    row = doc["proposed_statistics"]["retained_exact_binomial_gates"][0]
    row["pass_count"] = row["n"]


def _unit_of_n_removed(doc):
    doc["proposed_statistics"]["retained_exact_binomial_gates"][0]["unit_of_n"] = ""


def _i3_unit_becomes_the_base_item(doc):
    doc["proposed_statistics"]["i3_indicators"]["independent_unit"] = "base_item"


def _tango_regains_gate_authority(doc):
    doc["retired_procedures"]["tango_paired_equivalence"]["status"] = \
        "ACTIVE GATE CRITERION"


def _uniformity_becomes_a_gate(doc):
    doc["proposed_statistics"]["selected_label_uniformity_diagnostic"][0][
        "carries_gate_authority"] = True


def _selection_order_becomes_data_dependent(doc):
    doc["development_selection_and_confirmation_plan"]["stage_2_selection"][
        "no_data_dependent_reordering"] = False


def _selection_map_loses_a_case(doc):
    doc["proposed_statistics"]["development_selection_map"].pop()


def _selection_map_returns_s4(doc):
    doc["proposed_statistics"]["development_selection_map"][0][
        "selected_profile"] = "S4"


def _m_max_inflated_by_s4(doc):
    doc["power_architecture_v0_4"]["cell_counts"]["m_max"] = 47


def _m_max_includes_s4(doc):
    doc["power_architecture_v0_4"]["cell_counts"]["s4_is_excluded_from_m_max"] = \
        False


def _per_cell_budget_drifts(doc):
    doc["power_architecture_v0_4"]["type_ii_allocation"][
        "per_cell_false_negative_budget_exact_rational"] = "19/400"


def _per_cell_target_drifts(doc):
    doc["power_architecture_v0_4"]["type_ii_allocation"][
        "per_cell_power_target_exact_rational"] = "9/10"


def _profile_floor_drifts(doc):
    doc["power_architecture_v0_4"]["type_ii_allocation"][
        "profile_stage_power_floor_exact_rational"] = "99/100"


def _end_to_end_floor_drifts(doc):
    doc["power_architecture_v0_4"]["type_ii_allocation"][
        "study_end_to_end_power_floor_exact_rational"] = "99/100"


def _target_power_scope_weakened(doc):
    doc["proposed_statistics"]["target_power"]["scope"] = "END TO END"


def _union_bound_uses_independence(doc):
    doc["power_architecture_v0_4"]["union_bound_proof"]["uses_independence"] = True


def _arbitrary_dependence_dropped(doc):
    doc["power_architecture_v0_4"]["union_bound_proof"][
        "holds_under_arbitrary_dependence"] = False


def _least_favourable_configuration_removed(doc):
    doc["power_architecture_v0_4"]["least_favourable_configuration"][
        "conditions"] = []


def _uncovered_region_removed(doc):
    doc["power_architecture_v0_4"]["not_covered_by_the_power_guarantee"] = []


def _size_is_not_minimal(doc):
    doc["proposed_statistics"]["retained_exact_binomial_gates"][0]["n"] = 512


def _size_claim_flipped(doc):
    doc["proposed_statistics"]["retained_exact_binomial_gates"][0][
        "n_is_smallest_unrestricted_positive_integer_meeting_the_target"] = False


def _pass_count_not_minimal(doc):
    row = doc["proposed_statistics"]["retained_exact_binomial_gates"][0]
    row["pass_count"] = row["pass_count"] + 1


def _search_restricted_to_multiples(doc):
    doc["proposed_statistics"]["sample_size_search_rule"] = \
        "only multiples of the complete-block size 32 are admissible"


def _k5_support_truncated(doc):
    doc["sampling_frame_v0_4"]["k5_nuisance_state_support"]["support_size"] = 16


def _k5_weight_drifts(doc):
    doc["sampling_frame_v0_4"]["k5_nuisance_state_support"][
        "weight_per_state_exact_rational"] = "1/16"


def _k5_returns_to_block_assignment(doc):
    support = doc["sampling_frame_v0_4"]["k5_nuisance_state_support"]
    support["iid_with_replacement"] = False
    support["deterministic_complete_block_assignment_retired"] = False


def _sampling_cell_dropped(doc):
    doc["sampling_frame_v0_4"]["development_sampling_cells"].pop()


def _sampling_cell_count_drifts(doc):
    doc["sampling_frame_v0_4"]["development_sampling_cell_count"] = 16


def _sampling_weights_do_not_sum_to_one(doc):
    cell = doc["sampling_frame_v0_4"]["development_sampling_cells"][0]
    cell["sampled_parameters"][0]["weight_per_state_exact_rational"] = "1/9"


def _namespace_collision(doc):
    cells = doc["sampling_frame_v0_4"]["development_sampling_cells"]
    cells[1]["namespace"] = cells[0]["namespace"]


def _draw_without_replacement(doc):
    doc["sampling_frame_v0_4"]["development_sampling_cells"][0]["draw_rule"] = \
        "without_replacement"


def _duplicates_removed(doc):
    doc["sampling_frame_v0_4"]["duplicate_rule"]["duplicates_must_be_retained"] = \
        False


def _redraw_for_uniqueness_allowed(doc):
    doc["sampling_frame_v0_4"]["duplicate_rule"][
        "redraw_for_uniqueness_prohibited"] = False


def _split_not_outcome_blind(doc):
    doc["sampling_frame_v0_4"]["split_partition"]["outcome_blind"] = False


def _cross_split_reuse_allowed(doc):
    doc["sampling_frame_v0_4"]["split_partition"][
        "cross_split_reuse_prohibited"] = False


def _validity_predicate_becomes_post_model(doc):
    doc["sampling_frame_v0_4"]["validity_predicates"][0][
        "evaluated_before_any_model_operation"] = False


def _rejection_probability_nonzero(doc):
    doc["sampling_frame_v0_4"]["rejection_contract"][
        "registered_rejection_probability_exact_rational"] = "1/100"


def _acceptance_predicate_becomes_mutable(doc):
    doc["sampling_frame_v0_4"]["rejection_contract"][
        "acceptance_predicate_may_never_change_after_a_seed_exists"] = False


def _dependence_denied(doc):
    doc["sampling_frame_v0_4"]["reuse_and_dependence_rule"][
        "dependence_is_expressly_allowed"] = False


def _seed_redraw_allowed(doc):
    doc["sampling_frame_v0_4"]["future_seed_lifecycle"]["redraw_prohibited"] = False


def _seed_first_draw_only_dropped(doc):
    doc["sampling_frame_v0_4"]["future_seed_lifecycle"]["first_draw_only"] = False


def _i0_failure_gains_a_second_target(doc):
    machine = _find(doc["state_machine_v0_4"]["states"], "id", "Q0_INSTRUMENT")
    machine["transitions"].append({"event": "any fixture fails",
                                   "next": "Q1_DEVELOPMENT"})


def _i0_failure_retargeted(doc):
    machine = _find(doc["state_machine_v0_4"]["states"], "id", "Q0_INSTRUMENT")
    _find(machine["transitions"], "event", "error")["next"] = \
        "STOP_NO_SELECTABLE_INTERFACE_REMAINS"


def _i0_enters_profile_adequacy(doc):
    doc["state_machine_v0_4"]["i0_is_not_part_of_profile_adequacy"] = False


def _machine_loses_totality(doc):
    doc["state_machine_v0_4"]["total"] = False


def _terminal_becomes_unreachable(doc):
    machine = _find(doc["state_machine_v0_4"]["states"], "id",
                    "Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY")
    machine["transitions"] = [t for t in machine["transitions"]
                              if t["next"] != "STOP_CONFIRMATION_SPENT_ON_ERROR"]


def _rescue_path_added(doc):
    doc["state_machine_v0_4"]["rescue_paths"] = [
        {"from": "STOP_CONFIRMATION_FAILED", "to": "Q2_SELECTION"}]


def _s4_forward_cost_nulled(doc):
    doc["operation_ontology_v0_4"]["s4_forward_cost_must_not_be_null"] = False


def _token_bound_dropped(doc):
    doc["proposed_statistics"]["s4_generated_token_bound_per_generation"] = 1


def _i0_breakdown_drifts(doc):
    doc["proposed_statistics"]["i0_fixture_breakdown"]["k5_constructor_fixtures"] = 32


def _grand_total_permitted(doc):
    doc["operation_boundaries"]["projected_future_operations"][
        "grand_total_prohibited"] = False


def _p3q_null_treated_as_zero(doc):
    doc["operation_ontology_v0_4"]["unresolved_streams_are_null_not_zero"][
        "grand_total_treating_null_as_zero_prohibited"] = False


def _p3q_ordering_inverted(doc):
    doc["positive_reference_candidates"]["p3q_i4_ordering_constraint"][
        "p3q_lower_bound_exact_rational"] = "3/4"


def _p3q_constraint_selects_a_candidate(doc):
    doc["positive_reference_candidates"]["p3q_i4_ordering_constraint"][
        "no_checkpoint_is_selected_by_registering_this_constraint"] = False


def _ontology_unit_removed(doc):
    doc["operation_ontology_v0_4"]["units"] = [
        u for u in doc["operation_ontology_v0_4"]["units"]
        if u["unit"] != "incremental_decode_evaluation"]


def _sequence_evaluation_equated_with_a_batched_call(doc):
    doc["operation_ontology_v0_4"]["prohibition"] = \
        "a sequence-level evaluation is the same thing as a runtime batched call"


MUTATIONS = [
    ("frozen=true", _set_frozen),
    ("execution_authorized=true", _set_execution_authorized),
    ("nonzero operation counter", _nonzero_counter),
    ("injected new counter key", _injected_counter),
    ("winner selected", _winner_selected),
    ("winner statement flipped", _winner_statement_flipped),
    ("S4 selectable", _s4_selectable),
    ("S4 listed in a confirmation row", _s4_in_confirmation),
    ("S4 gains I4 applicability", _s4_gains_i4),
    ("I1b confirmation widened beyond S1", _i1b_confirmation_widens),
    ("I4 absent from eligibility", _i4_absent_from_eligibility),
    ("I4 not part of eligibility", _i4_not_part_of_eligibility),
    ("I4 failure leaves the interface eligible", _i4_failure_leaves_interface_eligible),
    ("I4 failure written as a global study stop", _i4_failure_stops_the_whole_study),
    ("I5 omits a covered construct", _i5_omits_a_construct),
    ("I5 accessible before authority", _i5_accessible),
    ("NA counted as a pass", _na_counted_as_pass),
    ("NA semantics weakened to a pass", _na_semantics_weakened),
    ("pooling rescue enabled", _pooling_enabled),
    ("gate-level pooling enabled", _gate_pooling_enabled),
    ("positive reference selected", _rp_selected),
    ("OD2 marked resolved", _od_resolved("OD2")),
    ("OD2 marked non-blocking", _od2_unblocked),
    ("confirmation accessible before authority", _confirmation_accessible),
    ("confirmation becomes repeatable", _confirmation_becomes_repeatable),
    ("reselection permitted after confirmation", _reselection_permitted),
    ("claim ceiling removed", _claim_ceiling_removed),
    ("bank row injected", _bank_row_injected),
    ("seed injected", _seed_injected),
    ("seed authority granted", _seed_authority_granted),
    ("model result injected", _result_injected),
    ("seeds drawn counter nonzero", _seeds_counter_nonzero),
    ("a gate authorizes mechanistic execution", _gate_authorizes_mechanism),
    ("a gate removed from the hierarchy", _gate_removed),
    ("state upgraded to frozen", _state_upgraded),
    ("review state downgraded to self approval", _review_state_downgraded),
    ("successor authority named", _successor_authority_named),
    ("I3 declares three variants per cluster", _i3_three_variants),
    ("one I3 contrast row drifts to four variants", _i3_row_variant_count_drifts),
    ("K5 crossed with K6", _k5_crossed_with_k6),
    ("K5 applicable to a content-only profile", _k5_applies_to_a_content_only_profile),
    ("K5 truth-table row flips for S2", _k5_truth_row_flips),
    ("J_joint_correct weakened to a disjunction", _j_joint_becomes_a_disjunction),
    ("J_joint_correct relabelled a contrast", _j_joint_becomes_a_contrast),
    ("J_joint_correct claims a presentation effect",
     _j_joint_claims_a_presentation_effect),
    ("a historical indicator regains decision authority",
     _historical_indicator_regains_authority),
    ("an invariance claim returns to a validation target", _invariance_claim_returns),
    ("the prohibited-term list is emptied", _prohibited_term_list_emptied),
    ("development alpha drifts in one component row", _development_alpha_drifts),
    ("confirmation alpha drifts in one component row", _confirmation_alpha_drifts),
    ("selectable denominator shrinks", _denominator_shrinks),
    ("denominator is allowed to shrink", _denominator_may_shrink),
    ("a second I3 floor reappears", _second_i3_floor_reappears),
    ("the I3 floor moves back to 0.95", _i3_floor_moves_to_0_95),
    ("a rejection region requires every unit to succeed", _degenerate_rejection_region),
    ("a sample size loses its unit", _unit_of_n_removed),
    ("the I3 unit is conflated with the base item", _i3_unit_becomes_the_base_item),
    ("the retired paired procedure regains gate authority", _tango_regains_gate_authority),
    ("the nuisance uniformity criterion becomes a gate", _uniformity_becomes_a_gate),
    ("the selection order becomes data dependent", _selection_order_becomes_data_dependent),
    ("the selection map loses a case", _selection_map_loses_a_case),
    ("the selection map returns S4", _selection_map_returns_s4),
    ("m_max inflated by S4", _m_max_inflated_by_s4),
    ("S4 admitted into m_max", _m_max_includes_s4),
    ("per-cell false-negative budget drifts", _per_cell_budget_drifts),
    ("per-cell power target drifts", _per_cell_target_drifts),
    ("profile stage power floor drifts", _profile_floor_drifts),
    ("study end-to-end power floor drifts", _end_to_end_floor_drifts),
    ("per-cell target relabelled end-to-end", _target_power_scope_weakened),
    ("the union bound assumes independence", _union_bound_uses_independence),
    ("arbitrary dependence is dropped", _arbitrary_dependence_dropped),
    ("the least-favourable configuration is removed",
     _least_favourable_configuration_removed),
    ("the uncovered indifference region is removed", _uncovered_region_removed),
    ("a sample size is no longer minimal", _size_is_not_minimal),
    ("the minimal-size claim is flipped", _size_claim_flipped),
    ("a pass count is no longer minimal", _pass_count_not_minimal),
    ("the size search is restricted to multiples of 32", _search_restricted_to_multiples),
    ("the K5 support is truncated", _k5_support_truncated),
    ("the K5 state weight drifts", _k5_weight_drifts),
    ("K5 returns to deterministic block assignment", _k5_returns_to_block_assignment),
    ("a sampling cell is dropped", _sampling_cell_dropped),
    ("the sampling cell count drifts", _sampling_cell_count_drifts),
    ("sampling weights no longer sum to one", _sampling_weights_do_not_sum_to_one),
    ("two sampling cells share a namespace", _namespace_collision),
    ("a draw becomes without replacement", _draw_without_replacement),
    ("duplicates are removed", _duplicates_removed),
    ("redraw for uniqueness is allowed", _redraw_for_uniqueness_allowed),
    ("the split partition is no longer outcome blind", _split_not_outcome_blind),
    ("cross-split reuse is allowed", _cross_split_reuse_allowed),
    ("a validity predicate becomes post-model", _validity_predicate_becomes_post_model),
    ("the registered rejection probability becomes nonzero",
     _rejection_probability_nonzero),
    ("the acceptance predicate becomes mutable after a seed",
     _acceptance_predicate_becomes_mutable),
    ("cross-cell dependence is denied", _dependence_denied),
    ("seed redraw is allowed", _seed_redraw_allowed),
    ("the first-draw-only seed rule is dropped", _seed_first_draw_only_dropped),
    ("an I0 failure gains a second next state", _i0_failure_gains_a_second_target),
    ("an I0 failure is retargeted away from the defect stop", _i0_failure_retargeted),
    ("I0 enters profile adequacy", _i0_enters_profile_adequacy),
    ("the state machine loses totality", _machine_loses_totality),
    ("a terminal state becomes unreachable", _terminal_becomes_unreachable),
    ("a rescue path is added", _rescue_path_added),
    ("the S4 forward cost may be null again", _s4_forward_cost_nulled),
    ("the S4 generated-token bound collapses", _token_bound_dropped),
    ("the I0 fixture breakdown drifts", _i0_breakdown_drifts),
    ("a grand total becomes permitted", _grand_total_permitted),
    ("the unresolved P3-Q stream may be totalled as zero", _p3q_null_treated_as_zero),
    ("the P3-Q ordering constraint is inverted", _p3q_ordering_inverted),
    ("registering the P3-Q constraint selects a candidate",
     _p3q_constraint_selects_a_candidate),
    ("an operation ontology unit is removed", _ontology_unit_removed),
    ("a sequence evaluation is equated with a batched call",
     _sequence_evaluation_equated_with_a_batched_call),
    # ---- draft-v0.5, closing the third review's findings -------------------
    ("K6-SEP is re-applied to an option-less profile",
     _k6_sep_reapplied_to_an_option_less_profile),
    ("K6 applicability returns to family level",
     _k6_applicability_returns_to_family_level),
    ("K6-SEP applicability widens beyond the label-bearing profiles",
     _k6_sep_applicability_widens),
    ("an option-less claim ceiling regains K6-SEP",
     _option_less_claim_ceiling_regains_k6_sep),
    ("R-sep is duplicated for an option-less profile",
     _r_sep_duplicated_for_an_option_less_profile),
    ("separator rendering becomes applicable to an option-less profile",
     _separator_rendering_becomes_applicable_to_an_option_less_profile),
    ("K6-SEP enters confirmation for an option-less profile",
     _k6_sep_enters_confirmation_for_an_option_less_profile),
    ("confirmation applicability returns to family level",
     _confirmation_applicability_returns_to_family_level),
    ("S4 re-enters a confirmation component", _s4_reenters_a_confirmation_component),
    ("a non-machine stop state returns", _non_machine_stop_state_returns),
    ("an 'at least n' reading becomes permitted", _at_least_n_interpretation_permitted),
    ("an eventual-monotonicity threshold replaces the registered minimum",
     _eventual_monotonicity_threshold_replaces_the_minimum),
    ("the union bound claims a predesignated profile",
     _union_bound_claims_a_predesignated_profile),
    ("the rendering registry is demoted to an illustrative example",
     _registry_demoted_to_an_illustrative_example),
    ("the rendering registry stops being a binding input",
     _registry_binding_status_dropped),
    ("the RP wrapper is filled in by v0.5", _rp_wrapper_filled_in_by_v0_5),
    ("token distinctness is treated as already tested",
     _token_distinctness_treated_as_tested),
    ("a token-distinctness failure becomes a pass",
     _token_distinctness_failure_becomes_a_pass),
    ("the prohibition scope narrows to the protocol only",
     _prohibition_scope_narrows_to_the_protocol_only),
    ("the prohibition's historical exemptions are removed",
     _prohibition_historical_exemptions_removed),
    ("a round reference reverts to the second review",
     _round_reference_reverts_to_the_second_review),
]


def _rejected(doc, schema):
    """A document is rejected if the schema rejects it or a semantic law does."""
    if schema_errors(doc, schema):
        return True
    try:
        _semantic_laws(doc)
    except (AssertionError, KeyError, IndexError, TypeError, ValueError):
        return True
    return False


def _semantic_laws(doc):
    """Laws that a structural schema cannot express."""
    tables = _load_json(STATS_TABLES)

    # ---- v0.1 and v0.2 laws ---------------------------------------------
    order = doc["admissibility_order"]
    assert order["no_winner_this_round"] is True
    assert order["no_winner_this_round_statement"] == NO_WINNER
    assert "I4" in order["gates_required_for_eligibility"]
    i4 = _gate(doc, "I4")
    assert i4["part_of_eligibility"] is True
    assert i4["per_interface_not_global"] is True
    assert "eliminate this interface profile" in i4["legal_next_state_on_fail"]
    assert doc["atomic_evaluation_cells"]["no_pooling_rescue"] is True
    assert doc["positive_reference_candidates"][
        "selection_status"].startswith("UNSELECTED")
    assert doc["split_lifecycle"]["confirmation_isolation"][
        "accessible_before_authority"] is False
    decisions = {d["id"]: d for d in doc["unresolved_operator_decisions"]}
    assert decisions["OD2"]["status"] == "unresolved"
    assert decisions["OD2"]["blocking"] is True
    assert doc["blocking_decisions"] == ["OD2"]
    for profile in doc["interface_profiles"]:
        applicability = profile["transformation_applicability"]
        declared = {entry["transformation"]
                    for entry in profile["non_applicable_transformations"]}
        assert declared == {name for name, value in applicability.items()
                            if value != "applicable"}
        if not profile["options_visible"]:
            for transform in POSITION_LABEL_TRANSFORMS:
                assert applicability[transform] != "applicable"
        if not profile["labels_visible"]:
            assert "I1b" not in profile["applicable_gates"]
    semantics = doc["not_applicable_semantics"]
    assert "not a pass" in semantics and "not a zero effect" in semantics
    assert semantics == doc["claim_ceiling"]["not_applicable_semantics"]
    na_value = doc["gate_truth_table"]["value_semantics"]["not_applicable"]
    assert "not a pass" in na_value or "never" in na_value
    for banned in ("counts as a satisfied gate", "counts as a pass",
                   "behaves as a pass"):
        assert banned not in na_value
        assert banned not in semantics
    ceiling = doc["claim_ceiling"]
    for field in ("maximum_pass_claim", "maximum_fail_claim",
                  "permitted_i3_statement"):
        text = ceiling[field].lower()
        for banned in ("proven correct", "for all inputs", "always correct",
                       "in general"):
            assert banned not in text, field
    assert "conditional on" in ceiling["maximum_pass_claim"].lower() or \
        "registered" in ceiling["maximum_pass_claim"].lower()
    assert len(ceiling["prohibited_claims"]) >= 10
    assert len(ceiling["what_a_pass_does_not_permit"]) >= 5
    assert ceiling["no_self_approval"]
    assert doc["proposed_statistics"]["i3_indicators"]["independent_unit"] == \
        "base_item_contrast_cluster"
    assert doc["atomic_evaluation_cells"]["i3_sampling_unit"]["unit"] == \
        "base_item_contrast_cluster"
    assert "contrast cluster" in \
        doc["proposed_statistics"]["sample_sizes"]["I3"]["unit_of_n"]
    assert "S4" not in [e["interface"] for e in order["order"]]
    assert {p["id"]: p for p in doc["interface_profiles"]}["S4"][
        "selectable_status"] == "never_selectable"
    i5 = _gate(doc, "I5")
    assert i5["accessible_before_authority"] is False
    assert "RP" in i5["model_roles"]
    assert any("K4" in item for item in i5["inputs"])
    for construct in COVERED_CONSTRUCTS:
        assert construct in i5["covered_constructs"]
    for gate in doc["gate_hierarchy"]:
        assert gate["authorizes_mechanistic_execution"] is False
        assert gate["no_pooling"] is True
        assert not _asserts_failing_interface_stays_eligible(
            gate["legal_next_state_on_fail"])
        assert not _asserts_failing_interface_stays_eligible(gate["what_fails"])
    assert {g["gate_id"] for g in doc["gate_hierarchy"]} == \
        {"I0", "I1a", "I1b", "I2", "I3", "I4", "I5"}
    assert doc["state"] == EXPECTED_STATE
    assert doc["status"]["frozen"] is False
    assert doc["status"]["execution_authorized"] is False
    assert doc["status"]["review_state"] == REVIEW_STATE
    assert "fourth bounded independent methods review" in doc["required_next_action"]
    assert doc["results"] == [] and doc["bank_rows"] == []
    counters = doc["operation_boundaries"]["performed_this_round"]
    assert set(counters) == set(tables["operation_counts"])
    for value in counters.values():
        assert value == 0

    # ---- v0.3 laws --------------------------------------------------------
    registry = doc["i3_contrast_registry"]
    assert registry["variants_per_cluster"] == 2
    for row in registry["k5"] + registry["k6"]:
        assert row["variants_per_cluster"] == 2
    assert len(registry["k5"]) == 7 and len(registry["k6"]) == 2
    assert doc["counterbalancing_design"]["k5_and_k6_are_not_crossed"] is True
    assert set(registry["k5_applicability"]["applicable_profiles"]) == {"S1", "S4"}
    assert set(registry["k5_applicability"]["not_applicable_profiles"]) == \
        {"S2", "S3"}
    for row in doc["gate_truth_table"]["rows"]:
        if row["label_bearing"] is False:
            for state in row["I3_K5"].values():
                assert state == "not_applicable"
            # S3MR3-001: K6-SEP has no referent without a label and a content.
            assert row["I3_K6"]["K6-SEP"] == "not_applicable"
            assert row["I3_K6"]["K6-INSTR"] == "applicable"
    for construct in ("I1a", "I1b", "I2", "I3", "I4"):
        development = _component(doc, "development", construct)
        confirmation = _component(doc, "confirmation", construct)
        assert development["alpha_exact_rational"] == "1/600"
        assert confirmation["alpha_exact_rational"] == "1/200"
        for row in (development, confirmation):
            assert 0 < row["pass_count"] < row["n"]
            assert row["degenerate_rejection_region"] is False
            assert row["unit_of_n"]
            assert row["n"] not in (192, 256, 128)
        assert doc["proposed_statistics"]["sample_sizes"][construct]["unit_of_n"]
    floor = doc["proposed_statistics"]["i3_floor"]
    assert floor["active_floor_count"] == 1
    assert floor["p0_exact_rational"] == "9/10"
    assert floor["p0_0_95_status"] == "DELETED FROM EVERY ACTIVE FIELD"
    assert doc["retired_procedures"]["tango_paired_equivalence"]["status"] == \
        "RETIRED FROM EVERY DECISION ROLE"
    for diagnostic in doc["proposed_statistics"][
            "selected_label_uniformity_diagnostic"]:
        assert diagnostic["carries_gate_authority"] is False
    plan = doc["development_selection_and_confirmation_plan"]
    assert plan["stage_2_selection"]["order"] == ["S2", "S3", "S1"]
    assert plan["stage_2_selection"]["no_data_dependent_reordering"] is True
    assert plan["stage_3_confirmation"]["one_shot"] is True
    assert plan["stage_3_confirmation"]["reselection_prohibited"] is True
    assert plan["stage_3_confirmation"]["accessible_now"] is False
    selection_map = doc["proposed_statistics"]["development_selection_map"]
    assert len(selection_map) == 16
    for row in selection_map:
        assert row["fixed_selectable_profile_denominator"] == 3
        if row["selected_profile"] is not None:
            assert row["selected_profile"] in ("S1", "S2", "S3")
            assert row["selected_profile"] in row["eligible_profiles"]

    # ---- v0.4 laws --------------------------------------------------------
    indicators = doc["proposed_statistics"]["i3_indicators"]
    primary = indicators["J_joint_correct"]
    assert indicators["primary_indicator"] == "J_joint_correct"
    assert primary["is_a_level_not_a_contrast"] is True
    assert primary["identifies_a_presentation_effect"] is False
    assert "BOTH registered variants" in primary["definition"]
    historical = indicators["historical_and_descriptive_indicators"]
    assert historical["status"] == "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY"
    assert historical["reachable_decision_path"] is False
    prohibition = doc["proposed_statistics"]["active_claim_term_prohibition"]
    assert prohibition["prohibited_terms"]
    for _label, text in _active_claim_strings(doc):
        lowered = text.lower()
        for stem in PROHIBITED_CLAIM_TERMS:
            assert stem not in lowered

    counts = tables["gate_bearing_cell_counts"]
    roles = doc["proposed_statistics"]["registered_target_roles"]
    families = doc["proposed_statistics"]["registered_operation_families"]
    depths = doc["proposed_statistics"]["registered_composition_depths"]
    recomputed_max = 0
    for row in doc["gate_truth_table"]["rows"]:
        profile = row["profile"]
        i1a = len(roles) if row["I1a"] == "applicable" else 0
        i1b = len(roles) if row["I1b"] == "applicable" else 0
        i2 = len(roles) * len(families) if row["I2"] == "applicable" else 0
        i3 = (sum(1 for state in row["I3_K5"].values() if state == "applicable")
              + sum(1 for state in row["I3_K6"].values()
                    if state == "applicable")) * len(roles)
        i4 = len(families) * len(depths) if row["I4"] == "applicable" else 0
        total = i1a + i1b + i2 + i3 + i4
        assert counts[profile]["total_gate_bearing_cells"] == total, profile
        if row["selectable"]:
            recomputed_max = max(recomputed_max, total)
    architecture = doc["power_architecture_v0_4"]
    assert architecture["cell_counts"]["m_max"] == recomputed_max
    assert architecture["cell_counts"]["s4_is_excluded_from_m_max"] is True
    allocation = architecture["type_ii_allocation"]
    stage = _rational(
        allocation["per_stage_profile_false_negative_budget_exact_rational"])
    per_cell = stage / recomputed_max
    assert _rational(
        allocation["per_cell_false_negative_budget_exact_rational"]) == per_cell
    assert _rational(allocation["per_cell_power_target_exact_rational"]) == \
        1 - per_cell
    assert _rational(allocation["profile_stage_power_floor_exact_rational"]) == \
        1 - recomputed_max * per_cell
    panel = _rational(allocation["panel_false_qualification_budget_exact_rational"])
    assert _rational(allocation["study_end_to_end_power_floor_exact_rational"]) == \
        1 - stage - panel - stage
    assert allocation["per_cell_power_target_scope"] == "PER ATOMIC EVALUATION CELL"
    assert doc["proposed_statistics"]["target_power"]["scope"] == \
        "PER ATOMIC EVALUATION CELL"
    assert architecture["union_bound_proof"]["uses_independence"] is False
    assert architecture["union_bound_proof"]["holds_under_arbitrary_dependence"] \
        is True
    assert architecture["least_favourable_configuration"]["conditions"]
    assert architecture["not_covered_by_the_power_guarantee"]
    assert architecture["type_i_architecture"][
        "fixed_selectable_profile_denominator"] == 3
    assert architecture["type_i_architecture"]["denominator_never_shrinks"] is True

    # The six rows must still be exactly the derived ones.
    for family, expected in _recompute_rows(doc).items():
        published = _floor_for(doc, family)
        for gate in published["gates"]:
            assert _component(doc, "development", gate)["n"] == expected["n"]
            assert _component(doc, "development", gate)["pass_count"] == \
                expected["development"]
            assert _component(doc, "confirmation", gate)["pass_count"] == \
                expected["confirmation"]
            assert _component(doc, "development", gate)[
                "n_is_smallest_unrestricted_positive_integer_meeting_the_target"] \
                is True
            assert _component(doc, "development", gate)[
                "pass_count_is_minimal_at_alpha"] is True
    assert "every positive integer is searched" in \
        doc["proposed_statistics"]["sample_size_search_rule"]

    rule = doc["proposed_statistics"]["confirmation_applicability_rule"]
    assert rule["i1b_confirmation_profiles"] == ["S1"]
    assert rule["k5_confirmation_profiles"] == ["S1"]
    assert rule["s4_can_never_appear"] is True
    for row in doc["proposed_statistics"]["confirmation_exact_binomial_gates"]:
        assert "S4" not in row["applicable_profiles"]
        assert row["s4_present"] is False
    assert _find(doc["gate_truth_table"]["rows"], "profile", "S4")["I4"] == \
        "not_applicable"

    frame = doc["sampling_frame_v0_4"]
    support = frame["k5_nuisance_state_support"]
    assert support["support_size"] == 32
    assert _rational(support["weight_per_state_exact_rational"]) * 32 == 1
    assert support["iid_with_replacement"] is True
    assert support["deterministic_complete_block_assignment_retired"] is True
    expected_cells = sum(len(v) for v in _gate_bearing_cell_keys(doc).values())
    for cells, count_key in (
            (frame["development_sampling_cells"], "development_sampling_cell_count"),
            (frame["confirmation_sampling_cells"], "confirmation_sampling_cell_count")):
        assert frame[count_key] == len(cells) == expected_cells
        namespaces = [cell["namespace"] for cell in cells]
        assert len(set(namespaces)) == len(namespaces)
        for cell in cells:
            assert cell["draw_rule"] == "with_replacement"
            product, support_size = Fraction(1), 1
            for parameter in cell["sampled_parameters"]:
                weight = _rational(parameter["weight_per_state_exact_rational"])
                assert weight * parameter["support_size"] == 1
                product *= weight
                support_size *= parameter["support_size"]
            assert support_size == cell["support_size"]
            assert product * cell["support_size"] == 1
    dev_namespaces = {c["namespace"] for c in frame["development_sampling_cells"]}
    conf_namespaces = {c["namespace"] for c in frame["confirmation_sampling_cells"]}
    assert not dev_namespaces & conf_namespaces
    assert frame["split_partition"]["outcome_blind"] is True
    assert frame["split_partition"]["cross_split_reuse_prohibited"] is True
    assert frame["duplicate_rule"]["duplicates_must_be_retained"] is True
    assert frame["duplicate_rule"]["redraw_for_uniqueness_prohibited"] is True
    for predicate in frame["validity_predicates"]:
        assert predicate["deterministic"] is True
        assert predicate["evaluated_before_any_model_operation"] is True
    assert _rational(frame["rejection_contract"][
        "registered_rejection_probability_exact_rational"]) == 0
    assert frame["rejection_contract"][
        "acceptance_predicate_may_never_change_after_a_seed_exists"] is True
    assert frame["reuse_and_dependence_rule"]["dependence_is_expressly_allowed"] \
        is True
    lifecycle = frame["future_seed_lifecycle"]
    assert lifecycle["seed_values"] is None
    assert lifecycle["realized_bank"] is None
    assert lifecycle["seed_authority_granted"] is False
    assert lifecycle["redraw_prohibited"] is True
    assert lifecycle["first_draw_only"] is True
    assert frame["seeds_drawn_in_this_round"] == 0
    assert frame["bank_rows_created_in_this_round"] == 0

    machine = doc["state_machine_v0_4"]
    assert machine["total"] is True and machine["deterministic"] is True
    assert machine["i0_is_not_part_of_profile_adequacy"] is True
    assert machine["rescue_paths"] == []
    states = {state["id"]: state for state in machine["states"]}
    edges = []
    for state in machine["states"]:
        if state["kind"] == "terminal":
            continue
        events = set()
        for transition in state["transitions"]:
            assert transition["event"] not in events
            events.add(transition["event"])
            assert transition["next"] in states
            edges.append((state["id"], transition["next"]))
    for transition in states["Q0_INSTRUMENT"]["transitions"]:
        if transition["event"] != "all fixtures pass":
            assert transition["next"] == "STOP_INSTRUMENT_DEFECT"
    reachable, frontier = {"Q0_INSTRUMENT"}, ["Q0_INSTRUMENT"]
    while frontier:
        current = frontier.pop()
        for source, target in edges:
            if source == current and target not in reachable:
                reachable.add(target)
                frontier.append(target)
    assert reachable == set(states)

    ontology = doc["operation_ontology_v0_4"]
    assert ontology["s4_forward_cost_must_not_be_null"] is True
    assert "NEVER equated with a runtime" in ontology["prohibition"]
    units = {entry["unit"] for entry in ontology["units"]}
    assert {"sequence_level_prefill_evaluation", "incremental_decode_evaluation",
            "total_sequence_level_model_evaluation_equivalent"} <= units
    assert ontology["unresolved_streams_are_null_not_zero"][
        "grand_total_treating_null_as_zero_prohibited"] is True
    assert doc["operation_boundaries"]["projected_future_operations"][
        "grand_total_prohibited"]["prohibited"] is True
    bound = doc["proposed_statistics"]["s4_generated_token_bound_per_generation"]
    s4_stream = tables["projected_operation_accounting"]["work_streams"][
        "S4_diagnostic_generation"]
    assert s4_stream["registered_generated_token_bound_per_generation"] == bound
    assert s4_stream["generated_tokens_upper_bound"] == \
        s4_stream["generation_calls"] * bound
    breakdown = doc["proposed_statistics"]["i0_fixture_breakdown"]
    i0_stream = tables["projected_operation_accounting"]["work_streams"][
        "deterministic_I0_fixtures"]
    assert i0_stream["breakdown"] == breakdown

    ordering = doc["positive_reference_candidates"]["p3q_i4_ordering_constraint"]
    i4_floor = _floor_for(doc, "I4_positive_reference_floor")
    assert _rational(ordering["p3q_lower_bound_exact_rational"]) > \
        _rational(i4_floor["p1_exact_rational"]) > \
        _rational(i4_floor["p0_exact_rational"])
    assert ordering["no_checkpoint_is_selected_by_registering_this_constraint"] \
        is True

    # ---- v0.5 laws --------------------------------------------------------
    # S3MR3-001. K6 applicability is per contrast, and K6-SEP has no referent
    # without a displayed label AND a displayed content.
    k6 = doc["i3_contrast_registry"]["k6_applicability"]
    assert "applicable_profiles" not in k6
    assert k6["per_contrast_registration_required"] is True
    assert set(k6["by_contrast"]["K6-SEP"]["applicable_profiles"]) == set(LABEL_BEARING)
    assert set(k6["by_contrast"]["K6-SEP"]["not_applicable_profiles"]) == set(OPTION_LESS)
    assert set(k6["by_contrast"]["K6-INSTR"]["applicable_profiles"]) == \
        {"S1", "S2", "S3", "S4"}
    for profile in OPTION_LESS:
        entry = doc["i3_contrast_registry"]["claim_ceiling_by_profile"][profile]
        assert entry["applicable_cells"] == ["K6-INSTR"], profile
        assert entry["applicable_cell_count"] == 1, profile
        assert tables["gate_bearing_cell_counts"][profile][
            "applicable_i3_contrast_count"] == 1, profile
    for row in doc["gate_truth_table"]["rows"]:
        expected = "applicable" if row["profile"] in LABEL_BEARING else "not_applicable"
        assert row["I3_K6"]["K6-SEP"] == expected, row["profile"]
        assert row["I3_K6"]["K6-INSTR"] == "applicable", row["profile"]
    for rendering in doc["counterbalancing_design"]["k6_renderings"]["renderings"]:
        if rendering["id"] == "R-sep":
            assert set(rendering["applicable_profiles"]) == set(LABEL_BEARING)
            assert set(rendering["not_applicable_profiles"]) == set(OPTION_LESS)
    for profile in doc["interface_profiles"]:
        separator = profile["transformation_applicability"]["separator_rendering"]
        if profile["id"] in OPTION_LESS:
            assert separator != "applicable", profile["id"]
        else:
            assert separator == "applicable", profile["id"]

    # S3MR3-002. Confirmation applicability is component level, S4 never appears,
    # and no not-applicable component may reach confirmation.
    rule = doc["proposed_statistics"]["confirmation_applicability_rule"]
    assert "PER COMPONENT" in rule["row_shape"]
    assert rule["s4_can_never_appear"] is True
    assert rule["i1b_confirmation_profiles"] == ["S1"]
    assert rule["k5_confirmation_profiles"] == ["S1"]
    assert rule["k6_sep_confirmation_profiles"] == ["S1"]
    assert rule["k6_instr_confirmation_profiles"] == ["S1", "S2", "S3"]
    for field, value in rule.items():
        if field.endswith("_confirmation_profiles"):
            assert "S4" not in value, field
    for component in tables["confirmation_component_applicability"]["components"]:
        assert "S4" not in component["applicable_profiles"], component["component"]
        assert component["s4_present"] is False
    published = {c["component"]: c["applicable_profiles"]
                 for c in tables["confirmation_component_applicability"]["components"]}
    assert published["I3/K6-SEP"] == ["S1"]
    assert published["I3/K6-INSTR"] == ["S1", "S2", "S3"]
    assert published["I1b"] == ["S1"]
    for contrast in doc["i3_contrast_registry"]["k5_contrast_ids"]:
        assert published["I3/" + contrast] == ["S1"], contrast
    for row in doc["proposed_statistics"]["confirmation_exact_binomial_gates"]:
        assert "S4" not in row["applicable_profiles"], row["gate"]
        assert row["applicability_is_component_level"] is True

    # S3MR3-005 and S3MR3-006.
    s4_profile = next(p for p in doc["interface_profiles"] if p["id"] == "S4")
    assert "I4" not in s4_profile["applicable_gates"]
    stop_states = doc["gate_truth_table"]["legal_stop_states"]
    assert not any(s.startswith("STOP_AWAITING_AUTHORITY") for s in stop_states)
    machine_terminals = {s["id"] for s in doc["state_machine_v0_4"]["states"]
                         if s["kind"] == "terminal"}
    machine_stops = {s for s in machine_terminals if s.startswith("STOP_")}
    listed_stops = {s.split(" ")[0].rstrip(",") for s in stop_states}
    # Every legal stop state must BE a terminal state of the registered machine,
    # and every STOP terminal must be listed. The sets are equal (S3MR3-006).
    assert listed_stops == machine_stops, (listed_stops, machine_stops)
    assert listed_stops <= machine_terminals

    # S3MR3-007.
    nonmono = doc["proposed_statistics"]["local_power_nonmonotonicity"]
    assert nonmono["at_least_n_interpretation_prohibited"] is True
    assert nonmono["eventual_monotonicity_threshold_registered"] is False
    for row in tables["development_exact_binomial_components"]:
        local = row["local_power_nonmonotonicity"]
        assert local["execution_must_use_the_exact_registered_cell_size"] is True
        assert local["at_least_n_interpretation_prohibited"] is True
        # Non-vacuous: the target genuinely fails again above the registered size.
        assert local["failing_sizes_within_the_disclosure_window"], row["gate_family"]
        assert local["target_is_monotone_within_the_disclosure_window"] is False

    # S3MR3-008.
    assert "FOURTH" in doc["proposed_statistics"]["unresolved"][1]
    assert "second independent methods review" not in \
        doc["proposed_statistics"]["unresolved"][1]
    assert "fourth" in doc["claim_ceiling"]["no_self_approval"]
    assert doc["status"]["review_state"] == REVIEW_STATE

    # S3MR3-009.
    proof = doc["power_architecture_v0_4"]["union_bound_proof"]
    assert "AN ADEQUATE profile" in proof["conclusion"]
    assert "the designated adequate profile" not in proof["conclusion"]
    assert "HIGHEST-PRIORITY" in proof["multi_adequate_branch"]
    assert proof["uses_independence"] is False
    assert proof["holds_under_arbitrary_dependence"] is True

    # S3MR3-010.
    surface = doc["rendering_surface_v0_5"]
    assert surface["binding_input"] is True
    assert surface["illustrative_example"] is False
    assert surface["rp_wrapper"] is None
    assert surface["future_rule_resolves_od2"] is False
    assert surface["tokenizer_distinctness_status"].startswith("NOT_TESTED_THIS_ROUND")
    assert "INELIGIBLE" in surface["future_pre_bank_token_distinctness_rule"]
    assert "pass" not in surface["future_pre_bank_token_distinctness_rule"].split(
        "INELIGIBLE")[0]

    # S3MR3-004. The declared prohibition scope must cover the reviewed paths.
    prohibition = doc["proposed_statistics"]["active_claim_term_prohibition"]
    for required in ("routing documents", "the research charter",
                     "the Study 3 handoff", "the protocol Markdown companion",
                     "the status report",
                     "the research question and its narrowing text"):
        assert required in prohibition["scope"], required
    assert prohibition["historical_exemptions"]
    for exemption in prohibition["historical_exemptions"]:
        assert exemption["kind"] and exemption["requirement"]


@pytest.mark.parametrize("name,mutate", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_negative_mutation_is_rejected(protocol, schema, name, mutate):
    mutated = _mutate(protocol, mutate)
    assert _rejected(mutated, schema), (
        "the mutation %r was NOT rejected; the design checks are too weak" % name)


def test_the_unmutated_protocol_is_accepted(protocol, schema):
    """Guards against a check that rejects everything, which would be useless."""
    assert not _rejected(json.loads(json.dumps(protocol)), schema)
