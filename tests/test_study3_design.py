"""Committed design-critical tests for the Study 3 interface-calibration draft.

These tests exist because the draft-v0.1 round's consistency checker was an
operator-side ephemeral script. It was never committed, a reviewer could not
re-run it, and it did not catch the Markdown/JSON contradiction that the operator
review later found. Everything that is design-critical is therefore checked here,
in the repository test suite.

draft-v0.3 additions. The independent methods review of draft-v0.2 returned
STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED with twenty findings. Six were
blocking. This module now also enforces, as executable invariants, the repairs
adopted in response to them: exactly two variants per I3 contrast cluster and no
K5 x K6 cross product (S3MR-001), a single conjunctive I3 indicator whose truth
table fails a stable-but-wrong answer (S3MR-002), an exact rational alpha that is
present in every component row rather than only asserted (S3MR-003), the complete
removal of the paired aggregate-equivalence procedure from every decision role
(S3MR-004, S3MR-005), one and only one I3 floor with no degenerate rejection
region (S3MR-006, S3MR-015), a fixed across-profile denominator (S3MR-016), an
executable development selection map (S3MR-017), a work-stream decomposed
operation projection (S3MR-012, S3MR-013) and a unit on every sample size
(S3MR-014).

Two anti-self-certification rules apply to this file. First, the numbers are not
transcribed here: the committed derivation script must recompute them, and a
separate test reads that script's own syntax tree to prove it contains no
hard-coded threshold, tail or power constant. Second, nothing in this module may
be read as approval of the design. It checks internal consistency and the
arithmetic; adjudication of the method belongs to the second independent methods
review.

Nothing in this file touches a model. There is no download, no weight load, no
tokenizer construction, no forward pass, no generation, no activation
extraction, no probe, no patch, no ablation, no lens operation, no GPU work and
no provider call. The tests read committed text files and do arithmetic.

The JSON-Schema validation below is implemented locally. ``jsonschema`` is not in
``requirements.lock.txt`` and is therefore absent from the validation image, so a
dependency on it would make these tests unrunnable exactly where they matter.
The supported keyword subset is the subset the Study 3 schema uses.
"""

import ast
import json
import os
import re
import subprocess
import sys

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
AMENDMENT_PATH = os.path.join(STUDY3, "reviews", "v0_3_operator_amendment.json")
PACKET_V0_3 = os.path.join(
    STUDY3, "analysis", "independent_methods_review_packet_v0_3.md")

EXPECTED_STATE = ("STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_"
                  "AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW")
NO_WINNER = "No interface is selected in this round."

DRAFT_VERSION = "draft-v0.3"
REVIEW_STATE = "awaiting_second_independent_methods_review"

# The constructs the one-shot confirmation gate must cover. I3 appears as its
# primary indicator J_both rather than as a bare family label: draft-v0.2
# carried two mutually exclusive I3 indicators, so a bare "I3" did not say what
# would be replicated.
COVERED_CONSTRUCTS = ("I0", "I1a", "I1b", "I2", "I3_J_both", "I4")

# The twenty findings of the independent methods review of draft-v0.2 and the
# twenty-two unresolved items of its packet checklist. Both sets must be closed
# exactly once each in the amendment record.
FINDING_IDS = ["S3MR-%03d" % i for i in range(1, 21)]
UR_IDS = ["UR-%02d" % i for i in range(1, 23)]

# Text that must never reappear. The first two strings are quoted from draft-v0.1
# and are the two defects that were confirmed verbatim from committed bytes.
FORBIDDEN_TEXT = [
    "A winner is selected in this round",
    "generated from one source of record",
]


# --------------------------------------------------------------------------
# Minimal JSON-Schema validator (local, dependency-free)
# --------------------------------------------------------------------------

_IGNORED = {"$schema", "$id", "title", "description", "examples", "default"}

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
            if value is False and isinstance(instance, dict):
                allowed = set(schema.get("properties", {}))
                for prop in instance:
                    if prop not in allowed:
                        errors.append("%s: additional property %r is not allowed"
                                      % (path, prop))
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
        elif key == "minItems":
            if isinstance(instance, list) and len(instance) < value:
                errors.append("%s: %d items, minimum %d"
                              % (path, len(instance), value))
        elif key == "maxItems":
            if isinstance(instance, list) and len(instance) > value:
                errors.append("%s: %d items, maximum %d"
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
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def protocol():
    with open(JSON_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def markdown():
    with open(MD_PATH, encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture(scope="module")
def tables():
    with open(STATS_TABLES, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def amendment():
    with open(AMENDMENT_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def packet():
    with open(PACKET_V0_3, encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# The validator itself must work before it is trusted
# --------------------------------------------------------------------------

def test_local_schema_validator_behaves():
    assert schema_errors(3, {"type": "number"}) == []
    assert schema_errors(True, {"type": "number"}) != []
    assert schema_errors(True, {"type": "integer"}) != []
    assert schema_errors(True, {"type": "boolean"}) == []
    assert schema_errors(1, {"type": "boolean"}) != []
    assert schema_errors(None, {"type": ["integer", "null"]}) == []
    assert schema_errors(5, {"type": ["integer", "null"]}) == []
    assert schema_errors("x", {"type": ["integer", "null"]}) != []
    assert schema_errors(1, {"minimum": 1}) == []
    assert schema_errors(0, {"minimum": 1}) != []
    assert schema_errors(1, {"maximum": 1}) == []
    assert schema_errors(2, {"maximum": 1}) != []
    assert schema_errors(True, {"minimum": 1}) == [], (
        "a boolean must not be silently range-checked as a number")
    assert schema_errors("x", {"const": "x"}) == []
    assert schema_errors("y", {"const": "x"}) != []
    assert schema_errors({"a": 1}, {"required": ["a"]}) == []
    assert schema_errors({}, {"required": ["a"]}) != []
    assert schema_errors({"a": 1, "b": 2},
                         {"properties": {"a": {}}, "additionalProperties": False}) != []
    assert schema_errors([1, 2], {"contains": {"const": 2}}) == []
    assert schema_errors([1, 3], {"contains": {"const": 2}}) != []
    assert schema_errors([], {"maxItems": 0}) == []
    assert schema_errors([1], {"maxItems": 0}) != []
    assert schema_errors("abc", {"pattern": "^a"}) == []
    assert schema_errors("bbc", {"pattern": "^a"}) != []


def test_the_validator_refuses_a_schema_it_cannot_fully_enforce():
    """An unsupported keyword must raise, never be silently skipped.

    A validator that ignores what it does not understand reports success for
    constraints it never checked, which is worse than having no validator.
    """
    with pytest.raises(AssertionError):
        schema_errors(1, {"multipleOf": 2})


# --------------------------------------------------------------------------
# Positive structural validation
# --------------------------------------------------------------------------

def test_protocol_validates_against_committed_schema(protocol, schema):
    errors = schema_errors(protocol, schema)
    assert errors == [], "schema validation failed:\n" + "\n".join(errors)


def test_protocol_declares_the_expected_draft_state(protocol):
    assert protocol["state"] == EXPECTED_STATE
    assert protocol["study_identity"]["draft_version"] == DRAFT_VERSION
    assert protocol["status"]["frozen"] is False
    assert protocol["status"]["execution_authorized"] is False
    assert protocol["status"]["review_state"] == REVIEW_STATE
    assert protocol["study_identity"]["successor_authority"] == "none"


def test_the_three_artifacts_agree_on_the_draft_version(protocol, tables,
                                                        amendment, packet):
    """JSON, derivation tables, amendment record and packet must not diverge."""
    assert tables["draft_version"] == DRAFT_VERSION
    assert amendment["state"] == EXPECTED_STATE
    assert DRAFT_VERSION in packet
    assert EXPECTED_STATE in packet


def test_every_operation_counter_is_zero(protocol):
    counters = protocol["operation_boundaries"]["performed_this_round"]
    assert counters, "the counter block must not be empty"
    for name, value in counters.items():
        assert value == 0, "counter %s is %r, expected 0" % (name, value)
    assert protocol["operation_boundaries"]["all_counters_zero"] is True
    assert protocol["results"] == []
    assert protocol["bank_rows"] == []
    assert protocol["bank_construction_policy"]["rows_generated_this_round"] == 0
    assert protocol["bank_construction_policy"]["seeds_drawn_this_round"] == 0


def test_no_winner_and_no_positive_reference_selected(protocol):
    order = protocol["admissibility_order"]
    assert order["no_winner_this_round"] is True
    assert order["no_winner_this_round_statement"] == NO_WINNER
    assert order["proposed_disposition_only"] is True
    assert order["no_data_dependent_ranking"] is True
    assert "S4" in order["never_selectable"]
    pr = protocol["positive_reference_candidates"]
    assert pr["selection_status"].startswith("UNSELECTED"), pr["selection_status"]
    assert pr["blocking_decision"] == "OD2"
    # OD2 is an operator decision. Draft-v0.3 may not pre-empt it by pinning,
    # ranking, downloading, tokenizing, loading or prequalifying a candidate.
    for verb in ("selected", "preferred", "pinned", "ranked", "downloaded",
                 "tokenized", "loaded", "prequalified"):
        assert verb in pr["selection_status"], verb
    performed = pr["operations_performed_on_any_candidate"]
    if isinstance(performed, dict):
        for name, value in performed.items():
            assert value in (0, False, "none"), "%s = %r" % (name, value)


def _asserts_failing_interface_stays_eligible(text):
    """True when text claims a failing interface itself remains eligible.

    The legitimate sentence "the study stops only when no selectable interface
    profile remains eligible" contains the same words, so it is removed before
    the check. Only the draft-v0.1 claim survives that removal.
    """
    stripped = re.sub(r"no selectable interface(?: profile)? remains eligible",
                      "", text)
    return "remains eligible" in stripped


def test_i4_is_part_of_eligibility_and_fails_per_interface(protocol):
    order = protocol["admissibility_order"]
    assert "I4" in order["gates_required_for_eligibility"]
    gate = _gate(protocol, "I4")
    assert gate["part_of_eligibility"] is True
    assert gate["per_interface_not_global"] is True
    assert "eliminate this interface profile" in gate["legal_next_state_on_fail"]
    assert "eliminated" in gate["consequence_of_failure"]
    # The v0.1 contradiction was that a failing interface "remains eligible".
    for other in protocol["gate_hierarchy"]:
        for field in ("legal_next_state_on_fail", "what_fails"):
            assert not _asserts_failing_interface_stays_eligible(other[field]), \
                (other["gate_id"], field)
    assert not _asserts_failing_interface_stays_eligible(
        gate["consequence_of_failure"].split("draft-v0.1 wrote")[0])


def test_i5_covers_every_gate_bearing_construct(protocol):
    """I3 is confirmed as its primary indicator, not as an unnamed family.

    draft-v0.2 listed a bare "I3" among the confirmed constructs while carrying
    two mutually exclusive I3 indicators, so the confirmation split did not say
    which one it would replicate. draft-v0.3 names J_both, and a draft that
    reverts to the ambiguous label fails here.
    """
    gate = _gate(protocol, "I5")
    for construct in COVERED_CONSTRUCTS:
        assert construct in gate["covered_constructs"], construct
    assert "I3" not in gate["covered_constructs"]
    assert gate["accessible_before_authority"] is False
    assert "RP" in gate["model_roles"]
    assert any("K4" in inp for inp in gate["inputs"])


def test_no_gate_authorizes_mechanistic_execution(protocol):
    gates = protocol["gate_hierarchy"]
    assert [g["gate_id"] for g in gates] == ["I0", "I1a", "I1b", "I2", "I3",
                                             "I4", "I5"]
    for gate in gates:
        assert gate["authorizes_mechanistic_execution"] is False
        assert gate["fail_closed"] is True
        assert gate["no_pooling"] is True


def test_pooling_as_a_rescue_is_prohibited(protocol):
    """The sampling unit is now stated per construct, because it differs.

    draft-v0.2 declared one sampling unit, "the base item", for the whole
    design while I3 was in fact evaluated over contrast clusters. That is the
    unit-reuse defect. draft-v0.3 requires the field to name both units and to
    say they are never interchanged.
    """
    cells = protocol["atomic_evaluation_cells"]
    assert cells["no_pooling_rescue"] is True
    unit = cells["sampling_unit"]
    assert "the base item for I1a, I1b, I2 and I4" in unit
    assert "the base-item contrast cluster for I3" in unit
    assert "never interchanged" in unit
    assert cells["i3_sampling_unit"]["unit"] == "base_item_contrast_cluster"
    assert len(cells["cell_factors"]) >= 8
    prohibited = " ".join(p["prohibited"] for p in cells["pooling_prohibitions"])
    assert "K1 with K2" in prohibited
    assert "primitive operation families" in prohibited
    assert "depth 2 with depth 3" in prohibited


def test_od2_alone_remains_blocking_and_od5_od6_are_only_proposed(protocol):
    """OD5 and OD6 are adopted this round; OD2 is not the operator's to close here.

    The adopted resolutions of OD5 and OD6 are explicitly conditional on the
    second independent methods review. They must not be recorded as plain
    ``resolved``, because that would be self-approval of exactly the two
    decisions the first reviewer rejected.
    """
    assert protocol["blocking_decisions"] == ["OD2"]
    by_id = {d["id"]: d for d in protocol["unresolved_operator_decisions"]}
    assert sorted(by_id) == ["OD%d" % i for i in range(1, 9)]

    assert by_id["OD2"]["status"] == "unresolved"
    assert by_id["OD2"]["blocking"] is True

    for did in ("OD5", "OD6"):
        assert by_id[did]["status"] == "resolved_subject_to_independent_review"
        assert by_id[did]["blocking"] is False, (
            "%s is adopted in draft-v0.3 and therefore no longer blocks the "
            "second review; it must not be reported as still blocking" % did)

    for did in ("OD1", "OD3", "OD4", "OD7"):
        assert by_id[did]["status"] == "resolved"
        assert by_id[did].get("blocking") is False
    assert by_id["OD8"]["status"] == "resolved_in_part"


def test_no_decision_is_recorded_as_independently_approved(protocol, amendment):
    """The drafting party may propose a repair; it may not adjudicate it."""
    prohibition = amendment["self_approval_prohibition"]
    assert prohibition["adjudication_belongs_to"]
    assert "second independent methods review" in \
        prohibition["adjudication_belongs_to"]
    assert prohibition["the_amendment_does_not_declare_the_protocol_correct"] \
        is True
    for flag, value in amendment["authority_flags"].items():
        assert value is False, "%s = %r" % (flag, value)
    for name, value in amendment["operation_counters"].items():
        assert value == 0, "%s = %r" % (name, value)
    for empty in ("results", "bank_rows", "seeds", "evidence_rows"):
        assert amendment[empty] == [], empty


def test_study1_wording_is_not_overstated(protocol):
    statement = protocol["prior_study_statements"]["study1"]
    assert "do not establish that parsing caused" in statement
    assert "Parser-v2 separately failed its locked gate" in statement
    assert "nonauthoritative" in statement
    prohibited = protocol["claim_ceiling"]["prohibited_claims"]
    assert any("parsing caused the Study 1" in claim for claim in prohibited)


# --------------------------------------------------------------------------
# Applicability is a third value, and it must be internally consistent
# --------------------------------------------------------------------------

POSITION_LABEL_TRANSFORMS = ("position_permutation", "label_symbol_permutation",
                             "label_set_replacement")


def test_not_applicable_is_neither_pass_nor_zero_effect(protocol):
    semantics = protocol["not_applicable_semantics"]
    assert "not a pass" in semantics
    assert "not a zero effect" in semantics
    assert "may never be counted as a satisfied" in semantics


def test_applicability_matches_what_each_profile_renders(protocol):
    """A profile that shows no options cannot have a position transformation."""
    for prof in protocol["interface_profiles"]:
        applicability = prof["transformation_applicability"]
        declared_na = {na["transformation"]
                       for na in prof["non_applicable_transformations"]}
        computed_na = {t for t, v in applicability.items() if v != "applicable"}
        assert declared_na == computed_na, prof["id"]
        if not prof["options_visible"]:
            for transform in POSITION_LABEL_TRANSFORMS:
                assert applicability[transform] != "applicable", (
                    "%s renders no options but claims %s is applicable"
                    % (prof["id"], transform))
        if not prof["labels_visible"]:
            assert "I1b" not in prof["applicable_gates"], (
                "%s renders no labels but claims the binding gate applies"
                % prof["id"])
        else:
            assert "I1b" in prof["applicable_gates"], prof["id"]


def test_s4_is_never_selectable_and_s3_is_conditional(protocol):
    by_id = {p["id"]: p for p in protocol["interface_profiles"]}
    assert by_id["S4"]["selectable_status"] == "never_selectable"
    assert by_id["S3"]["selectable_status"] == "conditionally_selectable"
    assert by_id["S2"]["selectable_status"] == "selectable_preferred"
    assert by_id["S1"]["selectable_status"] == "selectable"
    ranked = [entry["interface"] for entry in
              protocol["admissibility_order"]["order"]]
    assert "S4" not in ranked
    assert ranked == ["S2", "S3", "S1"]
    reason = by_id["S3"]["selectable_status_reason"]
    assert "identical to S2" in reason
    assert "multi-token" in reason


def test_selected_label_uniformity_has_exactly_one_classification(protocol,
                                                                  tables):
    """Draft-v0.2 called it a gate and a non-gate at once. Exactly one survives.

    Finding S3MR-002's neighbourhood defect: a criterion that is simultaneously
    declared a gate and omitted from the gate component list leaves it undefined
    whether a profile can be eliminated by it. Draft-v0.3 resolves it in the
    direction that eliminates no profile on a nuisance criterion, and the
    resolution must hold in every artifact at once.
    """
    uniformity = _gate(protocol, "I3")["selected_label_uniformity"]
    assert uniformity["status"] == "DIAGNOSTIC_NUISANCE_REPORT_ONLY"
    assert set(uniformity["not_applicable_to"]) == {"S2", "S3"}
    for authority in ("carries_gate_authority", "carries_eligibility_authority",
                      "carries_selection_authority",
                      "carries_confirmation_authority"):
        assert uniformity[authority] is False, authority

    # The same criterion may not reappear as a gate component anywhere.
    families = protocol["proposed_statistics"]["hypothesis_families"]
    for member in families["family_A_within_profile"]["members"]:
        assert "uniformity" not in member.lower(), member
    for row in tables["selected_label_uniformity_diagnostic"]:
        assert row["status"] == "DIAGNOSTIC_NUISANCE_REPORT_ONLY", row
        for authority in ("carries_gate_authority",
                          "carries_eligibility_authority",
                          "carries_selection_authority",
                          "carries_confirmation_authority"):
            assert row[authority] is False, (row, authority)
    for component in protocol["development_selection_and_confirmation_plan"][
            "stage_3_confirmation"]["components"]:
        assert "uniformity" not in component["component"].lower(), component


# --------------------------------------------------------------------------
# Counterbalancing: the published construction must actually be orthogonal
# --------------------------------------------------------------------------

def _baseline_condition(k):
    """The registered baseline condition of base-item index ``k``.

    This mirrors step 1 of the committed construction algorithm. It is written
    out here independently so that the test is a check on the published rule
    rather than a call into the code the rule is supposed to constrain.
    """
    return (k % 4, (k // 4) % 4, (k // 16) % 2)


def test_counterbalancing_construction_separates_position_from_symbol(protocol,
                                                                      tables):
    """Position, displayed symbol and alphabet must be independently balanced.

    The three factors cycle at 1, 4 and 16, so a complete block of 32 consecutive
    base-item indices realises every one of the 4 x 4 x 2 conditions exactly once.
    That is what makes the design deterministic and balanced without a random
    draw, which matters because this round is not permitted to draw a seed.
    """
    design = protocol["counterbalancing_design"]
    assert design["construction_algorithm"]["randomness"].startswith("none")

    block = tables["i3_pairwise_construction_verification"][
        "k5_complete_block_size"]
    assert block == 32
    conditions = [_baseline_condition(k) for k in range(block)]
    assert len(set(conditions)) == block, (
        "a complete block must realise every condition exactly once")
    assert set(conditions) == {(p, sym, a)
                               for p in range(4)
                               for sym in range(4)
                               for a in range(2)}

    positions = [c[0] for c in conditions]
    symbols = [c[1] for c in conditions]
    alphabets = [c[2] for c in conditions]
    for value in range(4):
        assert positions.count(value) == 8
        assert symbols.count(value) == 8
    for value in range(2):
        assert alphabets.count(value) == 16
    for position in range(4):
        seen = {c[1] for c in conditions if c[0] == position}
        assert seen == {0, 1, 2, 3}, (
            "position %d must occur with every displayed symbol, otherwise "
            "position and symbol identity are confounded" % position)
    for symbol in range(4):
        seen = {c[2] for c in conditions if c[1] == symbol}
        assert seen == {0, 1}, (
            "displayed symbol %d must occur under both alphabets" % symbol)
    assert tables["i3_pairwise_construction_verification"][
        "k5_baseline_conditions_balanced_over_a_complete_block"] is True


def test_the_option_and_symbol_maps_are_bijections(protocol):
    """A non-injective map would let two slots share a symbol or a content.

    Step 3 of the published construction assigns displayed symbols by the
    rotation ``slot -> (slot + shift) mod 4``. The test replays that rule for
    every admissible shift and checks that it really is a permutation, because a
    collision would confound content identity with symbol identity and silently
    destroy the one-factor property of every K5 contrast.
    """
    steps = " ".join(protocol["counterbalancing_design"][
        "construction_algorithm"]["steps"])
    assert "bijection" in steps
    for shift in range(4):
        mapped = [(slot + shift) % 4 for slot in range(4)]
        assert sorted(mapped) == [0, 1, 2, 3], shift
    for position in range(4):
        for symbol in range(4):
            shift = (symbol - position) % 4
            assert (position + shift) % 4 == symbol, (
                "the correct content must carry the intended displayed symbol")


def test_label_alphabets_do_not_collide_with_the_answer_domain(protocol):
    alphabets = protocol["counterbalancing_design"]["label_alphabets"]
    answer_domain = {str(d) for d in range(10)}
    forbidden = [tuple(a["alphabet"]) for a in alphabets["forbidden_alphabets"]]
    assert ("1", "2", "3", "4") in forbidden
    for entry in alphabets["forbidden_alphabets"]:
        assert set(entry["alphabet"]) & answer_domain, (
            "a forbidden alphabet must actually collide with the answer domain")
    for entry in alphabets["permitted_alphabet_examples"]:
        assert not (set(entry["alphabet"]) & answer_domain), (
            "a permitted alphabet must be disjoint from the answer domain")


def test_k6_varies_one_factor_at_a_time(protocol):
    renderings = protocol["counterbalancing_design"]["k6_renderings"]
    assert renderings["count"] == 3
    assert renderings["one_factor_at_a_time"] is True
    assert renderings["answer_cue"].startswith("held constant")
    varied = [r["varies"] for r in renderings["renderings"]]
    assert varied == ["nothing", "the option separator only",
                      "the instruction wording only"]




# --------------------------------------------------------------------------
# S3MR-001: the I3 estimand must be identifiable
# --------------------------------------------------------------------------

K5_IDS = ["K5-P1", "K5-P2", "K5-P3", "K5-S1", "K5-S2", "K5-S3", "K5-A1"]
K6_IDS = ["K6-SEP", "K6-INSTR"]


def test_i3_has_exactly_two_variants_per_contrast_cluster(protocol, tables):
    """The independent unit is the cluster, and a cluster is a pair.

    Finding S3MR-001 recorded that draft-v0.2 never fixed the number of variants
    per base item, so the same symbol n meant 32 renderings in one place, 3 in
    another and 96 in a third, and no estimand could be written down. Two
    variants per cluster is now a registered structural constant, and it must be
    the same constant everywhere it appears.
    """
    registry = protocol["i3_contrast_registry"]
    assert registry["independent_unit"] == "base_item_contrast_cluster"
    assert registry["variants_per_cluster"] == 2
    for row in registry["k5"] + registry["k6"]:
        assert row["variants_per_cluster"] == 2, row["contrast_id"]
    assert protocol["proposed_statistics"]["i3_indicators"][
        "variants_per_cluster"] == 2
    assert _gate(protocol, "I3")["variants_per_independent_unit"] == 2
    assert tables["i3_pairwise_construction_verification"][
        "variants_per_base_item_contrast_cluster"] == 2


def test_k5_and_k6_are_seven_and_two_disjoint_one_factor_cells(protocol,
                                                               tables):
    """No cross product, no factorial multiplication, one factor per contrast."""
    registry = protocol["i3_contrast_registry"]
    assert [row["contrast_id"] for row in registry["k5"]] == K5_IDS
    assert [row["contrast_id"] for row in registry["k6"]] == K6_IDS
    assert len(set(K5_IDS)) == 7 and len(set(K6_IDS)) == 2

    verification = tables["i3_pairwise_construction_verification"]
    assert verification["k5_contrast_count"] == 7
    assert verification["k6_contrast_count"] == 2
    assert verification["k5_x_k6_cross_product_exists"] is False
    assert verification["k5_one_factor_per_contrast"] is True
    assert verification["k5_k6_base_item_identities_disjoint"] is True
    assert verification["k6_answer_cue_fixed_within_every_pair"] is True

    design = protocol["counterbalancing_design"]
    assert design["k5_contrast_count"] == 7
    assert design["k6_contrast_count"] == 2
    assert design["k5_and_k6_are_not_crossed"] is True
    # Each K5 contrast varies exactly one factor, and the factor it varies must
    # appear in no other contrast's held-fixed omission.
    varied = [row["varied_factor"] for row in registry["k5"]]
    assert len(varied) == 7
    for row in registry["k5"]:
        assert row["varied_factor"] not in row["held_fixed"], row["contrast_id"]
        assert row["held_fixed"], row["contrast_id"]
    for row in registry["k6"]:
        assert row["baseline_rendering"] == "R-base", row["contrast_id"]
        assert row["variant_rendering"] != row["baseline_rendering"]
        assert any("answer cue" in held or "answer_cue" in held
                   for held in row["held_fixed"]), row["contrast_id"]
    assert {row["variant_rendering"] for row in registry["k6"]} == \
        {"R-sep", "R-instr"}


def test_k5_is_not_applicable_to_s2_and_s3_and_never_counts_as_a_pass(protocol):
    """A profile that renders no labels cannot pass a label manipulation.

    Draft-v0.2's gate truth table marked the K5 transformations as PASSING for
    S2 and S3, which are content-only surfaces with no option list and no label
    alphabet. That is the exact error the same document's not_applicable
    semantics forbids.
    """
    registry = protocol["i3_contrast_registry"]
    assert set(registry["k5_applicability"]["not_applicable_profiles"]) == \
        {"S2", "S3"}
    assert set(registry["k5_applicability"]["applicable_profiles"]) == \
        {"S1", "S4"}
    assert set(registry["k6_applicability"]["applicable_profiles"]) == \
        {"S1", "S2", "S3", "S4"}

    rows = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    for profile in ("S2", "S3"):
        assert rows[profile]["I3_K5"] == "not_applicable", profile
        assert rows[profile]["label_bearing"] is False, profile
        assert rows[profile]["I3_K6"] == "applicable", profile
    for profile in ("S1", "S4"):
        assert rows[profile]["I3_K5"] == "applicable", profile
    values = {value for row in protocol["gate_truth_table"]["rows"]
              for key, value in row.items() if key.startswith("I")}
    assert "pass" not in values and "passes" not in values, (
        "an applicability table must record no outcome")
    semantics = protocol["gate_truth_table"]["value_semantics"]["not_applicable"]
    assert "not a pass" in semantics
    assert "never be counted as a satisfied gate" in semantics


# --------------------------------------------------------------------------
# S3MR-002: one indicator, and a stable wrong answer must not score
# --------------------------------------------------------------------------

def test_the_i3_indicator_truth_table_fails_stable_wrong_and_stable_invalid(
        protocol, tables):
    """J_both is the gate. A confidently repeated wrong answer scores zero.

    Draft-v0.2 carried two mutually exclusive I3 definitions, one of which scored
    a model that answered the same incorrect value under every presentation as a
    success on a gate named calibration robustness.
    """
    indicators = protocol["proposed_statistics"]["i3_indicators"]
    assert indicators["J_both"]["definition"] == "J_inv AND J_cor"
    assert "PRIMARY" in indicators["J_both"]["role"]
    assert indicators["J_inv"]["stable_invalid_scores"] == 0
    assert indicators["J_cor"]["stable_wrong_scores"] == 0
    for name in ("J_inv", "J_cor"):
        assert "never a gate indicator on its own" in indicators[name]["role"]
        assert "never a rescue path" in indicators[name]["role"]

    rows = tables["i3_indicator_truth_table"]
    assert rows, "the truth table must be enumerated, not described"
    cases = {row["case"] for row in rows}
    for required in ("both_correct", "stable_but_wrong",
                     "one_correct_one_wrong"):
        assert required in cases, required
    assert any("invalid" in case for case in cases), (
        "a stable invalid or unparseable output case must be enumerated")

    for row in rows:
        j_inv, j_cor, j_both = row["J_inv"], row["J_cor"], row["J_both"]
        assert j_both == (1 if (j_inv and j_cor) else 0), row
        assert row["scores_for_the_gate"] is bool(j_both), row
        # Ground truth and mapped content are compared in their surface form,
        # because the scorer compares rendered content, not Python types.
        truth = str(row["registered_ground_truth"])
        one = row["variant_1_mapped_content"]
        two = row["variant_2_mapped_content"]
        valid = one is not None and two is not None
        if j_cor:
            assert valid and str(one) == truth and str(two) == truth, row
        # J_inv is invariance of valid content, so an invalid output cannot be
        # invariant with anything, including another invalid output.
        assert j_inv == (1 if (valid and str(one) == str(two)) else 0), row
        # S3MR-002 in one line: identical but wrong must not score.
        if row["case"] == "stable_but_wrong":
            assert valid and str(one) == str(two) and str(one) != truth, row
            assert j_inv == 1 and j_cor == 0 and j_both == 0, row
            assert row["scores_for_the_gate"] is False, row
        if row["case"] == "stable_but_invalid":
            assert one is None and two is None, row
            assert j_inv == 0 and j_cor == 0 and j_both == 0, row


def test_j_cor_implies_j_inv_over_every_enumerated_case(protocol, tables):
    """Under a unique ground truth the two indicators are not independent.

    Draft-v0.2 presented them as if they were. Recording the implication as an
    expected integrity invariant is honest; presenting the conjunction as two
    independent pieces of evidence would not be.
    """
    for row in tables["i3_indicator_truth_table"]:
        if row["J_cor"] == 1:
            assert row["J_inv"] == 1, (
                "J_cor = 1 with J_inv = 0 is a scorer defect: %r" % row)
    invariant = protocol["proposed_statistics"]["i3_indicators"][
        "expected_integrity_invariant"]
    assert "J_cor implies J_inv" in invariant
    assert "not as evidence that the two indicators carry independent " \
           "information" in invariant


def test_no_i3_rescue_path_exists(protocol):
    """A failed contrast cell may not be rescued by any weaker summary."""
    gate = _gate(protocol, "I3")
    assert gate["no_pooling"] is True
    logic = gate["threshold_logic"]
    assert "EVERY applicable atomic contrast cell separately" in logic
    assert "A single failed cell fails the gate" in logic
    assert "may rescue a failed cell" in logic
    assert protocol["proposed_statistics"]["i3_indicators"]["no_rescue"]


# --------------------------------------------------------------------------
# Markdown / JSON semantic parity - the defect that reached publication in v0.1
# --------------------------------------------------------------------------

def test_markdown_never_reintroduces_the_v0_1_defect_text(markdown):
    for text in FORBIDDEN_TEXT:
        assert text not in markdown, "forbidden v0.1 text reappeared: %r" % text


def test_markdown_agrees_with_json_on_every_decision_marker(protocol, markdown):
    required = [
        protocol["state"],
        "**Draft version:** " + DRAFT_VERSION,
        "**Frozen:** `false`",
        "**Execution authorized:** `false`",
        "**Review state:** `%s`" % REVIEW_STATE,
        "**Successor authority:** `none`",
        NO_WINNER,
        protocol["required_next_action"],
        protocol["prior_study_statements"]["study1"],
        protocol["prior_study_statements"]["study2"],
        protocol["positive_reference_candidates"]["selection_status"],
    ]
    for marker in required:
        assert marker in markdown, "missing from the companion: %r" % marker

    for prof in protocol["interface_profiles"]:
        assert re.search(r"\| %s \|.*\| `%s` \|"
                         % (re.escape(prof["id"]),
                            re.escape(prof["selectable_status"])),
                         markdown), prof["id"]
    for gate in protocol["gate_hierarchy"]:
        assert "### Gate %s - %s" % (gate["gate_id"], gate["name"]) in markdown
    for decision in protocol["unresolved_operator_decisions"]:
        assert re.search(r"\| %s \| `%s` \| `%s` \|"
                         % (decision["id"], decision["status"],
                            str(bool(decision.get("blocking"))).lower()),
                         markdown), decision["id"]
    for counter, value in \
            protocol["operation_boundaries"]["performed_this_round"].items():
        assert "| `%s` | `%d` |" % (counter, value) in markdown, counter
    for claim in protocol["claim_ceiling"]["prohibited_claims"]:
        assert claim in markdown, claim
    for row in protocol["i3_contrast_registry"]["k5"] + \
            protocol["i3_contrast_registry"]["k6"]:
        assert row["contrast_id"] in markdown, row["contrast_id"]
    for row in protocol["gate_truth_table"]["rows"]:
        assert re.search(r"\| %s \|.*\| `?%s`? \|"
                         % (re.escape(row["profile"]),
                            re.escape(row["I3_K5"])), markdown), row["profile"]


def test_markdown_does_not_claim_an_uncommitted_generator(protocol, markdown):
    statement = protocol["status"]["authoritative_artifact"]
    assert "no such generator is committed" in statement
    assert statement in markdown


# --------------------------------------------------------------------------
# Negative mutation battery: each mutation MUST be rejected
# --------------------------------------------------------------------------

def _component(protocol, split, gate_id):
    """Return one exact-binomial component row of one split.

    ``construct`` holds the long human-readable name of the construct and
    ``gate`` holds the gate identifier, so the lookup is on ``gate``.
    """
    key = "%s_exact_binomial_gates" % (
        "retained" if split == "development" else "confirmation")
    rows = [row for row in protocol["proposed_statistics"][key]
            if row["gate"] == gate_id]
    assert len(rows) == 1, (
        "expected exactly one %s component for %s, found %d"
        % (split, gate_id, len(rows)))
    return rows[0]


def _gate(protocol, gate_id):
    for gate in protocol["gate_hierarchy"]:
        if gate["gate_id"] == gate_id:
            return gate
    raise AssertionError("gate %s is missing" % gate_id)


def _mutate(protocol, fn):
    mutated = json.loads(json.dumps(protocol))
    fn(mutated)
    return mutated


def _set_frozen(doc):
    doc["status"]["frozen"] = True


def _set_execution_authorized(doc):
    doc["status"]["execution_authorized"] = True


def _nonzero_counter(doc):
    doc["operation_boundaries"]["performed_this_round"]["forward_passes"] = 1


def _injected_counter(doc):
    doc["operation_boundaries"]["performed_this_round"]["secret_gpu_jobs"] = 0


def _winner_selected(doc):
    doc["admissibility_order"]["no_winner_this_round"] = False


def _winner_statement_flipped(doc):
    doc["admissibility_order"]["no_winner_this_round_statement"] = \
        "S2 is selected in this round."


def _s4_selectable(doc):
    for prof in doc["interface_profiles"]:
        if prof["id"] == "S4":
            prof["selectable_status"] = "selectable"


def _i4_absent_from_eligibility(doc):
    order = doc["admissibility_order"]
    order["gates_required_for_eligibility"] = [
        g for g in order["gates_required_for_eligibility"] if g != "I4"]


def _i4_not_part_of_eligibility(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I4":
            gate["part_of_eligibility"] = False


def _i5_omits_rp_and_k4(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I5":
            gate["covered_constructs"] = ["I0", "I1a", "I1b", "I2", "I3"]


def _na_counted_as_pass(doc):
    for prof in doc["interface_profiles"]:
        if prof["id"] == "S2":
            prof["transformation_applicability"]["position_permutation"] = \
                "applicable"
            prof["non_applicable_transformations"] = [
                na for na in prof["non_applicable_transformations"]
                if na["transformation"] != "position_permutation"]


def _na_semantics_weakened(doc):
    doc["not_applicable_semantics"] = (
        "not_applicable is treated as a pass, because the transformation could "
        "not have changed the answer.")


def _pooling_enabled(doc):
    doc["atomic_evaluation_cells"]["no_pooling_rescue"] = False


def _gate_pooling_enabled(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I2":
            gate["no_pooling"] = False


def _rp_selected(doc):
    doc["positive_reference_candidates"]["selection_status"] = \
        "SELECTED: Qwen2.5-Math-7B-Instruct"


def _i3_three_variants(doc):
    doc["i3_contrast_registry"]["variants_per_cluster"] = 3


def _i3_row_variant_count_drifts(doc):
    doc["i3_contrast_registry"]["k5"][0]["variants_per_cluster"] = 4


def _k5_crossed_with_k6(doc):
    doc["counterbalancing_design"]["k5_and_k6_are_not_crossed"] = False


def _k5_passes_for_a_content_only_profile(doc):
    for row in doc["gate_truth_table"]["rows"]:
        if row["profile"] == "S2":
            row["I3_K5"] = "applicable"


def _stable_wrong_scores(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_cor"][
        "stable_wrong_scores"] = 1


def _stable_invalid_scores(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_inv"][
        "stable_invalid_scores"] = 1


def _j_both_is_a_disjunction(doc):
    doc["proposed_statistics"]["i3_indicators"]["J_both"][
        "definition"] = "J_inv OR J_cor"


def _development_alpha_drifts_in_one_row(doc):
    _component(doc, "development", "I2")["alpha_exact_rational"] = "1/200"


def _confirmation_alpha_drifts_in_one_row(doc):
    _component(doc, "confirmation", "I2")["alpha_exact_rational"] = "1/600"


def _denominator_shrinks_when_s3_is_inactive(doc):
    doc["proposed_statistics"]["hypothesis_families"][
        "family_B_across_profiles"]["fixed_selectable_profile_denominator"] = 2
    doc["proposed_statistics"]["hypothesis_families"][
        "family_B_across_profiles"]["denominator_never_shrinks"] = False


def _second_i3_floor_reappears(doc):
    doc["proposed_statistics"]["i3_floor"]["active_floor_count"] = 2
    doc["proposed_statistics"]["i3_floor"]["p0_0_95_status"] = "active"


def _i3_floor_moves_to_0_95(doc):
    _component(doc, "development", "I3")["p0_exact_rational"] = "19/20"
    _component(doc, "development", "I3")["p0"] = 0.95


def _degenerate_rejection_region(doc):
    row = _component(doc, "development", "I3")
    row["pass_count"] = row["n"]


def _unit_of_n_removed(doc):
    doc["proposed_statistics"]["sample_sizes"]["I3"]["unit_of_n"] = ""


def _i3_unit_becomes_the_base_item(doc):
    doc["proposed_statistics"]["sample_sizes"]["I3"]["unit_of_n"] = \
        doc["proposed_statistics"]["sample_sizes"]["I1a"]["unit_of_n"]


def _tango_regains_gate_authority(doc):
    doc["retired_procedures"]["tango_paired_equivalence"]["status"] = \
        "retained as the I3 secondary criterion"
    doc["retired_procedures"]["tango_paired_equivalence"]["retired_from"] = []


def _uniformity_becomes_a_gate(doc):
    uniformity = _gate(doc, "I3")["selected_label_uniformity"]
    uniformity["status"] = "gate"
    uniformity["carries_gate_authority"] = True


def _selection_order_becomes_data_dependent(doc):
    plan = doc["development_selection_and_confirmation_plan"]["stage_2_selection"]
    plan["no_data_dependent_reordering"] = False
    plan["order"] = ["S1", "S2", "S3"]


def _confirmation_becomes_repeatable(doc):
    plan = doc["development_selection_and_confirmation_plan"][
        "stage_3_confirmation"]
    plan["one_shot"] = False
    plan["reselection_prohibited"] = False


def _od_resolved(od_id):
    def mutate(doc):
        for decision in doc["unresolved_operator_decisions"]:
            if decision["id"] == od_id:
                decision["status"] = "resolved"
                decision["blocking"] = False
    return mutate


def _confirmation_accessible(doc):
    doc["split_lifecycle"]["confirmation_isolation"][
        "accessible_before_authority"] = True


def _i5_accessible(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I5":
            gate["accessible_before_authority"] = True


def _claim_ceiling_removed(doc):
    del doc["claim_ceiling"]


def _bank_row_injected(doc):
    doc["bank_rows"].append({"item_id": "K3-0001", "prompt": "1+1"})


def _seed_injected(doc):
    doc["bank_construction_policy"]["seeds_drawn_this_round"] = 1


def _result_injected(doc):
    doc["results"].append({"interface": "S1", "role": "RT", "accuracy": 0.62})


def _evidence_row_injected(doc):
    doc["operation_boundaries"]["performed_this_round"]["evidence_rows_created"] = 1


def _i4_failure_leaves_interface_eligible(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I4":
            gate["legal_next_state_on_fail"] = \
                "the interface remains eligible; continue"


def _i4_failure_stops_the_whole_study(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I4":
            gate["per_interface_not_global"] = False


def _gate_authorizes_mechanism(doc):
    for gate in doc["gate_hierarchy"]:
        if gate["gate_id"] == "I5":
            gate["authorizes_mechanistic_execution"] = True


def _gate_removed(doc):
    doc["gate_hierarchy"] = [g for g in doc["gate_hierarchy"]
                             if g["gate_id"] != "I1b"]


def _state_upgraded(doc):
    doc["state"] = "STUDY3_INTERFACE_CALIBRATION_PROTOCOL_FROZEN"


def _successor_authority_named(doc):
    doc["study_identity"]["successor_authority"] = "stage_p3q_execution"


MUTATIONS = [
    ("frozen=true", _set_frozen),
    ("execution_authorized=true", _set_execution_authorized),
    ("nonzero operation counter", _nonzero_counter),
    ("injected new counter key", _injected_counter),
    ("winner selected", _winner_selected),
    ("winner statement flipped", _winner_statement_flipped),
    ("S4 selectable", _s4_selectable),
    ("I4 absent from eligibility", _i4_absent_from_eligibility),
    ("I4 not part of eligibility", _i4_not_part_of_eligibility),
    ("I5 omitting RP/K4", _i5_omits_rp_and_k4),
    ("I4 failure leaves the interface eligible",
     _i4_failure_leaves_interface_eligible),
    ("I4 failure written as a global study stop",
     _i4_failure_stops_the_whole_study),
    ("NA counted as applicable", _na_counted_as_pass),
    ("NA semantics weakened to a pass", _na_semantics_weakened),
    ("cross-family/depth pooling enabled", _pooling_enabled),
    ("gate-level pooling enabled", _gate_pooling_enabled),
    ("RP selected", _rp_selected),
    ("OD2 marked resolved", _od_resolved("OD2")),
    ("OD5 marked resolved", _od_resolved("OD5")),
    ("OD6 marked resolved", _od_resolved("OD6")),
    ("confirmation accessible before authority", _confirmation_accessible),
    ("I5 accessible before authority", _i5_accessible),
    ("claim ceiling removed", _claim_ceiling_removed),
    ("bank row injected", _bank_row_injected),
    ("seed injected", _seed_injected),
    ("model result injected", _result_injected),
    ("evidence row injected", _evidence_row_injected),
    ("a gate authorizes mechanistic execution", _gate_authorizes_mechanism),
    ("a gate removed from the hierarchy", _gate_removed),
    ("state upgraded to frozen", _state_upgraded),
    ("successor authority named", _successor_authority_named),
    # draft-v0.3 invariants, one mutation per repaired finding
    ("I3 declares three variants per cluster", _i3_three_variants),
    ("one I3 contrast row drifts to four variants",
     _i3_row_variant_count_drifts),
    ("K5 crossed with K6", _k5_crossed_with_k6),
    ("K5 marked applicable for a content-only profile",
     _k5_passes_for_a_content_only_profile),
    ("a stable wrong answer scores", _stable_wrong_scores),
    ("a stable invalid output scores", _stable_invalid_scores),
    ("J_both weakened to a disjunction", _j_both_is_a_disjunction),
    ("development alpha drifts in one component row",
     _development_alpha_drifts_in_one_row),
    ("confirmation alpha drifts in one component row",
     _confirmation_alpha_drifts_in_one_row),
    ("Family B denominator shrinks when S3 is inactive",
     _denominator_shrinks_when_s3_is_inactive),
    ("a second I3 floor reappears", _second_i3_floor_reappears),
    ("the I3 floor moves back to 0.95", _i3_floor_moves_to_0_95),
    ("a rejection region requires every unit to succeed",
     _degenerate_rejection_region),
    ("a sample size loses its unit", _unit_of_n_removed),
    ("the I3 unit is conflated with the base item",
     _i3_unit_becomes_the_base_item),
    ("the retired paired procedure regains gate authority",
     _tango_regains_gate_authority),
    ("the nuisance uniformity criterion becomes a gate",
     _uniformity_becomes_a_gate),
    ("the selection order becomes data dependent",
     _selection_order_becomes_data_dependent),
    ("confirmation becomes repeatable", _confirmation_becomes_repeatable),
]


def _rejected(doc, schema):
    """A document is rejected if the schema rejects it or a semantic law does."""
    if schema_errors(doc, schema):
        return True
    try:
        _semantic_laws(doc)
    except AssertionError:
        return True
    return False


def _semantic_laws(doc):
    """Laws that a structural schema cannot express."""
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
    by_decision = {d["id"]: d for d in doc["unresolved_operator_decisions"]}
    assert by_decision["OD2"]["status"] == "unresolved"
    assert by_decision["OD2"]["blocking"] is True
    for adopted in ("OD5", "OD6"):
        # Adopted this round, but explicitly conditional on the second review.
        # A bare "resolved" would be the drafting party approving itself.
        assert by_decision[adopted]["status"] == \
            "resolved_subject_to_independent_review"
    for prof in doc["interface_profiles"]:
        applicability = prof["transformation_applicability"]
        declared = {na["transformation"]
                    for na in prof["non_applicable_transformations"]}
        computed = {t for t, v in applicability.items() if v != "applicable"}
        assert declared == computed
        if not prof["options_visible"]:
            for transform in POSITION_LABEL_TRANSFORMS:
                assert applicability[transform] != "applicable"
        if not prof["labels_visible"]:
            assert "I1b" not in prof["applicable_gates"]
    semantics = doc["not_applicable_semantics"]
    assert "not a pass" in semantics and "not a zero effect" in semantics
    assert doc["blocking_decisions"] == ["OD2"]
    ranked = [e["interface"] for e in doc["admissibility_order"]["order"]]
    assert "S4" not in ranked
    by_id = {p["id"]: p for p in doc["interface_profiles"]}
    assert by_id["S4"]["selectable_status"] == "never_selectable"
    i5 = _gate(doc, "I5")
    assert i5["accessible_before_authority"] is False
    assert "RP" in i5["model_roles"]
    assert any("K4" in inp for inp in i5["inputs"])
    for construct in COVERED_CONSTRUCTS:
        assert construct in i5["covered_constructs"]
    assert "I3" not in i5["covered_constructs"]
    unit = doc["atomic_evaluation_cells"]["sampling_unit"]
    assert "the base-item contrast cluster for I3" in unit
    for gate in doc["gate_hierarchy"]:
        assert not _asserts_failing_interface_stays_eligible(
            gate["legal_next_state_on_fail"])
        assert not _asserts_failing_interface_stays_eligible(gate["what_fails"])

    # ---- draft-v0.3 laws -------------------------------------------------
    registry = doc["i3_contrast_registry"]
    assert registry["variants_per_cluster"] == 2
    for row in registry["k5"] + registry["k6"]:
        assert row["variants_per_cluster"] == 2
    assert len(registry["k5"]) == 7 and len(registry["k6"]) == 2
    assert doc["counterbalancing_design"]["k5_and_k6_are_not_crossed"] is True
    assert set(registry["k5_applicability"]["not_applicable_profiles"]) == \
        {"S2", "S3"}
    for row in doc["gate_truth_table"]["rows"]:
        if row["label_bearing"] is False:
            assert row["I3_K5"] == "not_applicable"

    indicators = doc["proposed_statistics"]["i3_indicators"]
    assert indicators["J_both"]["definition"] == "J_inv AND J_cor"
    assert indicators["J_inv"]["stable_invalid_scores"] == 0
    assert indicators["J_cor"]["stable_wrong_scores"] == 0

    for construct in ("I1a", "I1b", "I2", "I3", "I4"):
        development = _component(doc, "development", construct)
        confirmation = _component(doc, "confirmation", construct)
        assert development["alpha_exact_rational"] == "1/600"
        assert confirmation["alpha_exact_rational"] == "1/200"
        for row in (development, confirmation):
            assert 0 < row["pass_count"] < row["n"]
            assert row["degenerate_rejection_region"] is False
            assert row["unit_of_n"]
        assert doc["proposed_statistics"]["sample_sizes"][construct]["unit_of_n"]

    family_b = doc["proposed_statistics"]["hypothesis_families"][
        "family_B_across_profiles"]
    assert family_b["fixed_selectable_profile_denominator"] == 3
    assert family_b["denominator_never_shrinks"] is True

    floor = doc["proposed_statistics"]["i3_floor"]
    assert floor["active_floor_count"] == 1
    assert floor["p0_exact_rational"] == "9/10"
    assert floor["p0_0_95_status"] == "DELETED FROM EVERY ACTIVE FIELD"
    assert _component(doc, "development", "I3")["p0_exact_rational"] == "9/10"

    sizes = doc["proposed_statistics"]["sample_sizes"]
    assert sizes["I3"]["unit_of_n"] != sizes["I1a"]["unit_of_n"]

    retired = doc["retired_procedures"]["tango_paired_equivalence"]
    assert retired["status"] == "RETIRED FROM EVERY DECISION ROLE"
    assert len(retired["retired_from"]) >= len(DECISION_ROLES)

    uniformity = _gate(doc, "I3")["selected_label_uniformity"]
    assert uniformity["status"] == "DIAGNOSTIC_NUISANCE_REPORT_ONLY"
    assert uniformity["carries_gate_authority"] is False

    plan = doc["development_selection_and_confirmation_plan"]
    assert plan["stage_2_selection"]["order"] == ["S2", "S3", "S1"]
    assert plan["stage_2_selection"]["no_data_dependent_reordering"] is True
    assert plan["stage_3_confirmation"]["one_shot"] is True
    assert plan["stage_3_confirmation"]["reselection_prohibited"] is True
    assert plan["stage_3_confirmation"]["accessible_now"] is False


@pytest.mark.parametrize("name,mutate",
                         MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_negative_mutation_is_rejected(protocol, schema, name, mutate):
    mutated = _mutate(protocol, mutate)
    assert _rejected(mutated, schema), (
        "the mutation %r was NOT rejected; the design checks are too weak" % name)


def test_the_unmutated_protocol_is_accepted(protocol, schema):
    """Guards against a check that rejects everything, which would be useless."""
    assert not _rejected(json.loads(json.dumps(protocol)), schema)


# --------------------------------------------------------------------------
# The statistics must reproduce, and the draft must quote them faithfully
# --------------------------------------------------------------------------

def test_design_statistics_script_reproduces_its_committed_tables():
    result = subprocess.run([sys.executable, STATS_SCRIPT, "--check"],
                            capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 0, (
        "design_statistics.py --check failed\nstdout:\n%s\nstderr:\n%s"
        % (result.stdout, result.stderr))
    assert "DESIGN_STATISTICS_CHECK_OK" in result.stdout


def test_statistics_tables_record_no_operations(tables):
    for name, value in tables["operation_counts"].items():
        assert value == 0, "%s is %r" % (name, value)
    assert tables["status"] == \
        "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN"
    assert tables["draft_version"] == DRAFT_VERSION


# The planning targets returned by the independent reviewer. The derivation
# script must arrive at these INDEPENDENTLY. Transcribing them into the script
# would make the check circular, which finding S3MR-009 recorded as a defect of
# draft-v0.2, so the next test reads the script's syntax tree and fails if any
# of them is present as a literal.
DERIVED_PASS_COUNTS = (244, 243, 82, 80, 224, 222)
DERIVED_TAILS = (0.001491215117, 0.003307722347, 0.000931234262,
                 0.002962603303, 0.001081002486, 0.003276850097)
DERIVED_POWERS = (0.953040775, 0.976290353, 0.938986365, 0.972425829,
                  0.921083515, 0.963820468)


def test_the_derivation_script_contains_no_hard_coded_result_constant():
    """S3MR-009: a check that compares a script to its own transcribed answers
    verifies nothing.

    The published thresholds, exact tails and power figures must be computed.
    This test parses the committed derivation script and fails if any of the
    reviewer-returned target values appears anywhere in it as a literal, which
    is the only way to distinguish derivation from transcription without
    trusting the script's own output.
    """
    with open(STATS_SCRIPT, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    integers, floats = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                continue
            if isinstance(node.value, int):
                integers.add(node.value)
            elif isinstance(node.value, float):
                floats.add(node.value)
    for value in DERIVED_PASS_COUNTS:
        assert value not in integers, (
            "the expected pass count %d is hard-coded in the derivation "
            "script; it must be computed" % value)
    for value in DERIVED_TAILS + DERIVED_POWERS:
        assert not any(abs(value - candidate) < 1e-12 for candidate in floats), (
            "the derived quantity %r is hard-coded in the derivation script; "
            "it must be computed" % value)


def test_the_published_tables_reproduce_the_reviewer_returned_targets(tables):
    """The independent derivation must nevertheless land on the same numbers.

    The previous test proves the script does not contain the answers. This one
    proves it still reaches them. Together they are a derivation check; either
    alone is not.
    """
    expected = {
        ("development", "I1a"): (244, 0.001491215117, 0.953040775),
        ("development", "I1b"): (244, 0.001491215117, 0.953040775),
        ("development", "I2"): (82, 0.000931234262, 0.938986365),
        ("development", "I3"): (244, 0.001491215117, 0.953040775),
        ("development", "I4"): (224, 0.001081002486, 0.921083515),
        ("confirmation", "I1a"): (243, 0.003307722347, 0.976290353),
        ("confirmation", "I1b"): (243, 0.003307722347, 0.976290353),
        ("confirmation", "I2"): (80, 0.002962603303, 0.972425829),
        ("confirmation", "I3"): (243, 0.003307722347, 0.976290353),
        ("confirmation", "I4"): (222, 0.003276850097, 0.963820468),
    }
    for split in ("development", "confirmation"):
        for row in tables["%s_exact_binomial_components" % split]:
            key = (split, row["gate"])
            assert key in expected, key
            pass_count, tail, power = expected[key]
            assert row["pass_count"] == pass_count, key
            assert abs(row["exact_null_tail_at_p0"] - tail) < 5e-12, key
            assert abs(row["exact_power_at_p1"] - power) < 5e-9, key
            assert row["meets_target_power"] is True, key
            assert row["exact_null_tail_at_p0"] <= row["alpha"], key
            assert row["exact_power_at_p1"] >= tables[
                "declared_assumptions"]["target_power"], key


# --------------------------------------------------------------------------
# The amendment record must close every finding and every checklist item once
# --------------------------------------------------------------------------

def test_every_finding_is_closed_exactly_once(amendment):
    rows = amendment["closure_matrix"]
    ids = [row["finding_id"] for row in rows]
    assert ids == FINDING_IDS, ids
    assert len(set(ids)) == 20
    for row in rows:
        assert row["severity"] in ("BLOCKING", "MAJOR", "MINOR"), row
        assert row["disposition"], row["finding_id"]
        assert row["repair"], row["finding_id"]
        assert row["verification"], row["finding_id"]
        assert row["where"], row["finding_id"]
        assert row["reviewer_required_change"], row["finding_id"]
    severities = [row["severity"] for row in rows]
    assert severities.count("BLOCKING") == 6
    assert severities.count("MAJOR") == 11
    assert severities.count("MINOR") == 3


def test_every_unresolved_item_receives_exactly_one_disposition(amendment):
    rows = amendment["unresolved_item_dispositions"]
    ids = [row["id"] for row in rows]
    assert ids == UR_IDS, ids
    assert len(set(ids)) == 22
    for row in rows:
        assert row["disposition"], row["id"]
        assert row["subject"], row["id"]
        assert row["owner"], row["id"]
        assert row["reviewer_state"], row["id"]


def test_the_od2_dependent_item_is_not_quietly_relabelled(amendment):
    """UR-22 is the external qualification interface for the positive reference.

    It depends on OD2, which the operator has not resolved. An amendment round
    may not close it by drafting; recording it as resolved would misrepresent
    the state of the study to the second reviewer.
    """
    rows = {row["id"]: row for row in amendment["unresolved_item_dispositions"]}
    assert rows["UR-22"]["disposition"] == \
        "UNRESOLVED_BLOCKING_OPERATOR_DECISION"
    assert "OD2" in json.dumps(rows["UR-22"])
    decisions = {row["id"]: row for row in
                 amendment["operator_decisions_in_this_round"]}
    assert decisions["OD2"]["status"] == "unresolved"
    assert decisions["OD2"]["blocking"] is True


def test_i4_chance_floor_is_recorded_as_rejected(protocol):
    """The rejected v0.1 chance-level null stays visible as history, not policy."""
    rejected = protocol["proposed_statistics"]["rejected_v0_1_i4_chance_null"]
    assert rejected["status"] == "REJECTED_BY_OPERATOR_REVIEW"
    assert rejected["acceptance_count"] == 49
    assert abs(rejected["acceptance_rate"] - 49 / 128) < 1e-12
    assert rejected["null_hypothesis"] == "p <= 0.25"
    active = _component(protocol, "development", "I4")
    assert active["p0_exact_rational"] == "4/5", (
        "the active I4 floor must be the positive-capability floor, not chance")


def test_n_192_is_withdrawn_from_every_active_field(protocol, tables, packet,
                                                    markdown):
    """Finding S3MR-008 retired n = 192. It may survive only as narrative.

    The check is deliberately structural rather than textual: every active
    sample-size field is read and none of them may be 192, while the historical
    note that explains the withdrawal is required to still be present.
    """
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    assert "WITHDRAWN" in sizes["n_192_status"]
    assert "S3MR-008" in sizes["n_192_status"]
    for construct in ("I1a", "I1b", "I2", "I3", "I4"):
        assert sizes[construct]["n"] != 192, construct
    for split in ("development", "confirmation"):
        for row in tables["%s_exact_binomial_components" % split]:
            assert row["n"] != 192, (split, row["gate"])
    for text, where in ((packet, "packet"), (markdown, "protocol companion")):
        for line in text.split("\n"):
            if re.search(r"\bn\s*=\s*.?192.?\b", line):
                assert _is_historical_narrative(line), (
                    "n = 192 is still offered as an active justification in "
                    "the %s: %r" % (where, line))


# --------------------------------------------------------------------------
# S3MR-004 / S3MR-005: the paired aggregate procedure is retired outright
# --------------------------------------------------------------------------

def _is_historical_narrative(line):
    """True when a line is clearly labelled as describing the withdrawn v0.2 state.

    Withdrawn parameters must remain visible so that a reader can see what was
    changed and why, but they may never appear as an active field. The label is
    what separates the two, so the label is what is checked.
    """
    lowered = line.lower()
    return ("draft-v0.2" in lowered or "historical" in lowered
            or "withdrawn" in lowered or "deleted" in lowered
            or "no longer" in lowered or "s3mr-0" in lowered)


DECISION_ROLES = ("gate", "eligibility", "selection", "confirmation",
                  "claim_language", "equivalence_margin", "critical_value",
                  "discordance_grid", "conservativeness")


def test_the_paired_equivalence_procedure_carries_no_decision_role(protocol,
                                                                   tables):
    """It is removed from decision authority, not re-tuned and not defended.

    The reviewer's recalculation showed the realised size exceeded the nominal
    level, so draft-v0.2's conservativeness assertion was false. Draft-v0.3 does
    not argue with that finding and does not attempt a corrected critical value;
    it removes the procedure from every decision role, which is the only repair
    that cannot itself be wrong about the size.
    """
    retired = protocol["retired_procedures"]["tango_paired_equivalence"]
    assert retired["status"] == "RETIRED FROM EVERY DECISION ROLE"
    assert len(retired["retired_from"]) >= len(DECISION_ROLES)
    joined = " ".join(retired["retired_from"]).lower()
    for role in DECISION_ROLES:
        assert role.replace("_", " ") in joined or role in joined, role
    assert retired["false_assertion_withdrawn"]
    assert retired["historical_evidence_preserved"]
    assert "immutable historical evidence" in retired[
        "historical_evidence_rule"]
    # The amendment must ask the second reviewer to adjudicate the repair
    # rather than declaring the size defect closed by its own authority.
    assert retired["question_for_the_second_reviewer"]
    assert retired["disposition_status"].startswith("PROPOSED_RESOLVED_SUBJECT")

    assert protocol["retired_procedures"][
        "four_point_discordance_grid"]["status"] == \
        "REMOVED FROM ACTIVE VERIFICATION"
    assert protocol["retired_procedures"][
        "i3_aggregate_equivalence_secondary_criterion"]["status"] == "REMOVED"
    assert _gate(protocol, "I3")["secondary_criterion_status"]

    survivor = tables["descriptive_paired_summary"]
    assert survivor["status"].startswith("DESCRIPTIVE"), survivor["status"]
    carries_no = " ".join(survivor["carries_no"]).lower()
    for banned in ("null", "alpha", "p-value", "pass", "rescue"):
        assert banned in carries_no, banned


def test_no_active_field_reintroduces_the_retired_procedure(protocol, tables,
                                                            packet):
    """A retired procedure that survives in one table is not retired."""
    for blob, where in ((protocol, "protocol"), (tables, "tables")):
        text = json.dumps(blob)
        for offender in ("equivalence_margin", "tango_critical_value",
                         "discordance_grid_verification"):
            assert offender not in text, (where, offender)
    assert "Tango" not in packet, (
        "the v0.3 review packet must contain no live paired-equivalence "
        "procedure; the reviewer's own recalculation of it is preserved "
        "separately as immutable historical evidence")


# --------------------------------------------------------------------------
# S3MR-003 / S3MR-016: the declared level must be the implemented level
# --------------------------------------------------------------------------

def _rational(text):
    """Parse an exact rational of the form ``a/b`` into a pair of ints."""
    numerator, _, denominator = text.partition("/")
    return int(numerator), int(denominator)


def test_the_exact_rational_alpha_is_present_in_every_component_row(protocol,
                                                                    tables):
    """Draft-v0.2 stated a per-profile alpha that appeared in no component.

    A level that is asserted in prose and absent from every row it is supposed
    to govern is not implemented. Here each row carries the rational form, and
    the rational form is compared against the declared study level by exact
    integer arithmetic rather than by comparing rendered decimals.
    """
    stats = protocol["proposed_statistics"]
    assert stats["development_component_alpha_exact_rational"] == "1/600"
    assert stats["confirmation_component_alpha_exact_rational"] == "1/200"
    assert stats["study_development_screening_alpha_exact_rational"] == "1/200"

    declared = tables["declared_assumptions"]
    assert declared["development_component_alpha_exact_rational"] == "1/600"
    assert declared["confirmation_component_alpha_exact_rational"] == "1/200"
    assert declared["study_development_screening_alpha_exact_rational"] == "1/200"
    assert declared["selectable_profile_denominator"] == 3

    for row in tables["development_exact_binomial_components"]:
        assert row["alpha_exact_rational"] == "1/600", row["gate"]
    for row in tables["confirmation_exact_binomial_components"]:
        assert row["alpha_exact_rational"] == "1/200", row["gate"]
    for construct in ("I1a", "I1b", "I2", "I3", "I4"):
        assert _component(protocol, "development", construct)[
            "alpha_exact_rational"] == "1/600", construct
        assert _component(protocol, "confirmation", construct)[
            "alpha_exact_rational"] == "1/200", construct

    # 1/600 x 3 == 1/200 exactly. Integer arithmetic, no floating point.
    per_num, per_den = _rational("1/600")
    study_num, study_den = _rational("1/200")
    denominator = declared["selectable_profile_denominator"]
    assert per_num * denominator * study_den == study_num * per_den, (
        "the per-profile level must reconstruct the study screening level "
        "exactly under the fixed denominator")


def test_the_across_profile_denominator_is_fixed_and_never_shrinks(protocol,
                                                                   tables):
    """Finding S3MR-016: a denominator contingent on a post-data fact is not a
    pre-registered correction.

    S3's availability depends on whether a multi-token answer domain has been
    activated. If the denominator followed that fact, the study could test two
    profiles at a level computed for three. It is therefore 3 under every
    enumerated outcome, including the outcomes in which S3 never enters.
    """
    family = protocol["proposed_statistics"]["hypothesis_families"][
        "family_B_across_profiles"]
    assert family["fixed_selectable_profile_denominator"] == 3
    assert family["denominator_is_fixed_before_data"] is True
    assert family["denominator_never_shrinks"] is True
    assert set(family["members"]) == {"S1", "S2", "S3"}
    assert any("S4" in text for text in family["excluded"])

    plan = protocol["development_selection_and_confirmation_plan"][
        "stage_2_selection"]
    assert plan["fixed_selectable_profile_denominator"] == 3
    assert plan["denominator_never_shrinks"] is True

    inactive = [row for row in tables["development_selection_map"]
                if row["s3_multi_token_domain_activated"] is False]
    assert inactive, "the map must enumerate the S3-inactive outcomes"
    for row in tables["development_selection_map"]:
        assert row["fixed_selectable_profile_denominator"] == 3, row


def test_within_profile_conjunction_takes_no_further_correction(protocol):
    """An intersection-union test is bounded by its component level.

    Applying a further within-profile Bonferroni correction on top of it would
    be a second, unnecessary shrinkage of power that the protocol would then
    have to justify. Declaring it and not applying it would be worse.
    """
    families = protocol["proposed_statistics"]["hypothesis_families"]
    within = families["family_A_within_profile"]
    assert within["type"] == "intersection_union_conjunctive"
    assert within["correction"].startswith("none within the profile")
    assert set(within["members"]) == {"I1a", "I1b", "I2", "I3_J_both", "I4"}
    plan = protocol["development_selection_and_confirmation_plan"][
        "stage_3_confirmation"]
    assert plan["within_profile"].startswith("intersection-union")
    assert plan["multiplicity"].startswith("none across profiles")


# --------------------------------------------------------------------------
# S3MR-006 / S3MR-015: exactly one I3 floor and no degenerate rejection region
# --------------------------------------------------------------------------

def test_exactly_one_i3_floor_is_active_and_it_is_0_90(protocol, tables,
                                                       packet, markdown):
    floor = protocol["proposed_statistics"]["i3_floor"]
    assert floor["active_floor_count"] == 1
    assert floor["p0_exact_rational"] == "9/10"
    assert floor["p1_lowest_alternative_of_interest"] == 0.97
    assert floor["n"] == 256
    assert floor["unit_of_n"] == "base-item contrast clusters per contrast cell"
    assert floor["p0_0_95_status"] == "DELETED FROM EVERY ACTIVE FIELD"

    for split in ("development", "confirmation"):
        for row in tables["%s_exact_binomial_components" % split]:
            assert row["p0_exact_rational"] != "19/20", (split, row["gate"])
            assert row["p0"] != 0.95, (split, row["gate"])
    for split in ("development", "confirmation"):
        row = _component(protocol, split, "I3")
        assert row["p0_exact_rational"] == "9/10", split
    assert _gate(protocol, "I3")["primary_criterion"][
        "active_floor_count"] == 1

    # 0.95 may appear only in clearly labelled historical narrative. The lookahead
    # keeps the check from firing on longer decimals such as the power 0.953040775,
    # which is a different quantity that happens to share a prefix.
    for text, where in ((packet, "packet"), (markdown, "protocol companion")):
        for line in text.split("\n"):
            if re.search(r"0\.95(?![0-9])", line):
                assert _is_historical_narrative(line), (
                    "an unlabelled p0 = 0.95 survives in the %s: %r"
                    % (where, line))


def test_no_rejection_region_requires_every_unit_to_succeed(protocol, tables):
    """A pass count equal to n has no power against any alternative below 1.

    Draft-v0.2 produced exactly that at n = 128 with p0 = 0.95. It is not a
    conservative test; it is not a test at all.
    """
    for split in ("development", "confirmation"):
        for row in tables["%s_exact_binomial_components" % split]:
            assert row["pass_count"] < row["n"], (split, row)
            assert row["degenerate_rejection_region"] is False, (split, row)
            assert 0 < row["pass_count"], (split, row)
    for split in ("development", "confirmation"):
        for construct in ("I1a", "I1b", "I2", "I3", "I4"):
            row = _component(protocol, split, construct)
            assert row["pass_count"] < row["n"], (split, construct)
            assert row["degenerate_rejection_region"] is False
    prohibition = protocol["proposed_statistics"]["i3_floor"][
        "degenerate_region_prohibition"]
    assert "raises before emitting any table" in prohibition


# --------------------------------------------------------------------------
# S3MR-014: every n carries its unit, and the units are never conflated
# --------------------------------------------------------------------------

def test_every_sample_size_declares_its_unit(protocol, tables):
    registry = protocol["unit_registry"]
    units = {entry["unit"] for entry in registry["units"]}
    assert "base_item" in units
    assert "base_item_contrast_cluster" in units
    for entry in registry["units"]:
        assert entry["definition"], entry["unit"]
        assert entry["never_equals"], entry["unit"]
        assert entry["unit"] not in entry["never_equals"], entry["unit"]

    sizes = protocol["proposed_statistics"]["sample_sizes"]
    for construct in ("I1a", "I1b", "I2", "I3", "I4"):
        assert sizes[construct]["unit_of_n"], construct
    for split in ("development", "confirmation"):
        for row in tables["%s_exact_binomial_components" % split]:
            assert row["unit_of_n"], (split, row["gate"])
            assert row["independent_unit"], (split, row["gate"])
    for row in tables["descriptive_clopper_pearson_lower_bounds"]:
        assert row["unit_of_n"], row
    for row in tables["selected_label_uniformity_diagnostic"]:
        assert row["unit_of_n"], row
    for gate_id in ("I1a", "I1b", "I2", "I3", "I4"):
        assert _gate(protocol, gate_id)["unit_of_n"], gate_id


def test_the_i3_unit_is_the_cluster_and_never_a_rendered_row(protocol, tables):
    """S3MR-014's concrete failure: one symbol n meaning four different things."""
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    assert "contrast clusters" in sizes["I3"]["unit_of_n"]
    assert "base items" in sizes["I1a"]["unit_of_n"]
    assert sizes["I3"]["unit_of_n"] != sizes["I1a"]["unit_of_n"]
    assert sizes["I2"]["unit_of_n"] != sizes["I1a"]["unit_of_n"]
    assert sizes["I4"]["unit_of_n"] != sizes["I1a"]["unit_of_n"]
    assert "rendered" not in json.dumps(sizes).lower()
    assert "never a rendered-row" in protocol["unit_registry"]["prohibition"]

    # rendered_rows = clusters x 2 must hold as an identity, not a coincidence.
    identities = tables["projected_operation_accounting"][
        "dimensional_identities"]
    assert identities, "the projection must publish its dimensional identities"
    for row in identities:
        assert row["rendered_rows"] == row["base_item_contrast_clusters"] * 2, row
        assert row["holds"] is True, row


# --------------------------------------------------------------------------
# S3MR-017: development selection must be executable, not merely named
# --------------------------------------------------------------------------

def test_the_development_selection_map_is_total_and_deterministic(protocol,
                                                                  tables):
    """Every reachable eligibility outcome must have exactly one answer.

    Draft-v0.2 named the selection step and the confirmation gate but never said
    what selects. A rule that is decided after the eligibility pattern is known
    is a data-dependent rule, whatever it is called.
    """
    rows = tables["development_selection_map"]
    plan = protocol["development_selection_and_confirmation_plan"][
        "stage_2_selection"]
    assert plan["order"] == ["S2", "S3", "S1"]
    assert plan["never_selectable"] == ["S4"]
    assert plan["no_data_dependent_reordering"] is True
    assert plan["no_selection_this_round"] is True
    assert plan["enumerated_scenarios"] == len(rows)

    # 3 selectable profiles x an S3-activation flag = 16 enumerated outcomes.
    keys = set()
    for row in rows:
        key = (tuple(sorted(row["all_applicable_components_passed"]))
               if isinstance(row["all_applicable_components_passed"], list)
               else tuple(sorted(row["all_applicable_components_passed"].items())),
               row["s3_multi_token_domain_activated"])
        assert key not in keys, "duplicate scenario %r" % (key,)
        keys.add(key)
    assert len(keys) == len(rows) == 16

    for row in rows:
        eligible = row["eligible_profiles"]
        selected = row["selected_profile"]
        stop = row["stop_no_selectable_profile_is_eligible"]
        if not eligible:
            assert selected is None and stop is True, row
            continue
        assert stop is False, row
        expected = next(p for p in ["S2", "S3", "S1"] if p in eligible)
        assert selected == expected, (
            "the map must select the first eligible profile in the "
            "pre-registered order: %r" % row)
        assert "S4" not in eligible, row


def test_the_confirmation_stage_is_one_shot_and_inaccessible(protocol):
    plan = protocol["development_selection_and_confirmation_plan"][
        "stage_3_confirmation"]
    assert plan["gate"] == "I5"
    assert plan["one_shot"] is True
    assert plan["reselection_prohibited"] is True
    assert plan["accessible_now"] is False
    assert plan["component_alpha_exact_rational"] == "1/200"
    assert "physically disjoint" in plan["split"]
    components = {row["component"]: row for row in plan["components"]}
    assert set(components) == {"I1a", "I1b", "I2", "I3", "I4"}
    for name, row in components.items():
        assert row["n"] > 0, name
        assert row["unit_of_n"], name
        assert row["null_hypothesis"].startswith("p <="), name
        assert 0 < row["pass_count"] < row["n"], name
        assert 0 < row["exact_null_tail_at_p0"] <= 1 / 200, name
        assert row["exact_power_at_p1"] >= 0.90, name


# --------------------------------------------------------------------------
# S3MR-012 / S3MR-013: the projection is decomposed and S3 costs nothing extra
# --------------------------------------------------------------------------

WORK_STREAMS = ("deterministic_I0_fixtures", "target_role_development",
                "positive_reference_external_P3Q",
                "RP_I4_under_candidate_profiles",
                "selected_profile_one_shot_confirmation",
                "S4_diagnostic_generation")


def test_the_projection_is_decomposed_into_the_six_work_streams(tables):
    accounting = tables["projected_operation_accounting"]
    assert set(accounting["work_streams"]) == set(WORK_STREAMS)
    assert "a single undifferentiated total is prohibited" in \
        accounting["prohibition"]
    for name, stream in accounting["work_streams"].items():
        assert isinstance(stream, dict), name
        assert stream, name
    for name, value in accounting["executed_operation_counts"].items():
        assert value == 0, "%s = %r" % (name, value)


def test_the_positive_reference_stream_stays_numerically_unresolved(tables):
    """OD2 is unresolved, so its cost is unknown and must be recorded as such.

    Publishing a number for a stream whose model is not chosen would be a
    fabricated projection and would also imply a candidate had been picked.
    """
    stream = tables["projected_operation_accounting"]["work_streams"][
        "positive_reference_external_P3Q"]
    assert stream["numeric_status"] == \
        "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2"
    assert stream["why_null"]
    for key, value in stream.items():
        if key.endswith(("_rows", "_passes", "_scorings", "_jobs", "_total")):
            assert value is None, (key, value)


def test_s3_adds_no_operations_under_the_current_single_token_domain(protocol,
                                                                     tables):
    """S3MR-012 recorded a self-contradiction of a factor of four here.

    Under the current single-token answer domain S3 reads the same logits under
    the same prefix as S2, so its incremental cost is exactly zero. Zero is a
    claim that can be checked; a large number that appears in one table and not
    another cannot.
    """
    accounting = tables["projected_operation_accounting"][
        "s3_current_domain_accounting"]
    assert accounting["additional_forward_passes"] == 0
    assert accounting["additional_sequence_scoring_rows"] == 0
    assert accounting["reuses"]
    # A zero incremental cost may not be used to argue S3 out of the fixed
    # Family B denominator.
    plan = protocol["development_selection_and_confirmation_plan"][
        "stage_2_selection"]
    assert "S3" in plan["order"]
    assert plan["fixed_selectable_profile_denominator"] == 3


# --------------------------------------------------------------------------
# The operator-review record must exist and stay additive
# --------------------------------------------------------------------------

def test_operator_review_record_is_present_and_additive():
    """The v0.1 operator review is history and must survive every later round."""
    with open(REVIEW_PATH, encoding="utf-8") as handle:
        text = handle.read()
    assert ("STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_"
            "NOT_APPROVED_FOR_FREEZE") in text
    for defect in ["D-%02d" % i for i in range(1, 11)]:
        assert defect in text, defect
    assert "design_receipt.json` is retained verbatim" in text or \
           "retained verbatim" in text


def test_v0_1_receipt_is_untouched_and_still_describes_v0_1():
    receipt_path = os.path.join(STUDY3, "design_receipt.json")
    with open(receipt_path, encoding="utf-8") as handle:
        receipt = json.load(handle)
    blob = json.dumps(receipt)
    assert "DRAFT_V0_2" not in blob, (
        "the v0.1 receipt must not be rewritten to describe v0.2")
    assert "DRAFT_V0_3" not in blob, (
        "the v0.1 receipt must not be rewritten to describe v0.3")


def test_the_v0_2_receipt_still_describes_v0_2():
    """Each round writes its own receipt; none rewrites an earlier one."""
    receipt_path = os.path.join(STUDY3, "design_receipt_v0_2.json")
    with open(receipt_path, encoding="utf-8") as handle:
        receipt = json.load(handle)
    assert "DRAFT_V0_3" not in json.dumps(receipt), (
        "the v0.2 receipt must not be rewritten to describe v0.3")


def test_the_amendment_names_the_immutable_objects_it_did_not_edit(amendment):
    """The v0.2 review record is evidence about this design and stays fixed."""
    protected = amendment["immutable_objects_not_edited"]
    for required in ("v0_2_independent_methods_review",
                     "methods_review_receipt_v0_2",
                     "independent_methods_recalculation",
                     "independent_methods_review_packet",
                     "design_receipt_v0_2"):
        assert any(required in entry for entry in protected), required
    # Each named object must actually exist, so the list cannot drift into a
    # set of paths that protect nothing.
    for entry in protected:
        assert os.path.exists(os.path.join(REPO_ROOT, entry)), entry
    responds = amendment["responds_to"]
    assert responds["disposition"] == \
        "STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED"
    assert responds["findings"]["total"] == 20
    assert responds["findings"]["blocking"] == 6
    assert responds["findings"]["major"] == 11
    assert responds["findings"]["minor"] == 3
    assert responds["unresolved_items"] == 22
    assert responds["reviewed_commit"].startswith("8a2c4a0")
    assert responds["review_commit"].startswith("e4bcda3")
