"""Committed design-critical tests for the Study 3 interface-calibration draft.

These tests exist because the draft-v0.1 round's consistency checker was an
operator-side ephemeral script. It was never committed, a reviewer could not
re-run it, and it did not catch the Markdown/JSON contradiction that the operator
review later found. Everything that is design-critical is therefore checked here,
in the repository test suite.

Nothing in this file touches a model. There is no download, no weight load, no
tokenizer construction, no forward pass, no generation, no activation
extraction, no probe, no patch, no ablation, no lens operation, no GPU work and
no provider call. The tests read committed text files and do arithmetic.

The JSON-Schema validation below is implemented locally. ``jsonschema`` is not in
``requirements.lock.txt`` and is therefore absent from the validation image, so a
dependency on it would make these tests unrunnable exactly where they matter.
The supported keyword subset is the subset the Study 3 schema uses.
"""

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

EXPECTED_STATE = ("STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_"
                  "AWAITING_INDEPENDENT_METHODS_REVIEW")
NO_WINNER = "No interface is selected in this round."

# Text that must never reappear. Both strings are quoted from draft-v0.1 and are
# the two defects that were confirmed verbatim from committed bytes.
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


def schema_errors(instance, schema, path="$"):
    """Return a list of validation errors. Empty list means valid."""
    errors = []
    for key, value in schema.items():
        if key in _IGNORED:
            continue
        if key == "type":
            expected = _TYPES[value]
            if value == "number" and isinstance(instance, bool):
                errors.append("%s: bool is not a number" % path)
            elif value in ("integer", "number") and isinstance(instance, bool):
                errors.append("%s: bool is not %s" % (path, value))
            elif not isinstance(instance, expected):
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


# --------------------------------------------------------------------------
# The validator itself must work before it is trusted
# --------------------------------------------------------------------------

def test_local_schema_validator_behaves():
    assert schema_errors(3, {"type": "number"}) == []
    assert schema_errors(True, {"type": "number"}) != []
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


# --------------------------------------------------------------------------
# Positive structural validation
# --------------------------------------------------------------------------

def test_protocol_validates_against_committed_schema(protocol, schema):
    errors = schema_errors(protocol, schema)
    assert errors == [], "schema validation failed:\n" + "\n".join(errors)


def test_protocol_declares_the_expected_draft_state(protocol):
    assert protocol["state"] == EXPECTED_STATE
    assert protocol["study_identity"]["draft_version"] == "draft-v0.2"
    assert protocol["status"]["frozen"] is False
    assert protocol["status"]["execution_authorized"] is False
    assert protocol["status"]["review_state"] == "awaiting_independent_methods_review"
    assert protocol["study_identity"]["successor_authority"] == "none"


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
    assert pr["selection_status"] == "NOT SELECTED; candidate dossier only"
    assert pr["blocking_decision"] == "OD2"


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
    gate = _gate(protocol, "I5")
    for construct in ("I0", "I1a", "I1b", "I2", "I3", "I4"):
        assert construct in gate["covered_constructs"]
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
    cells = protocol["atomic_evaluation_cells"]
    assert cells["no_pooling_rescue"] is True
    assert cells["sampling_unit"] == "the base item"
    assert len(cells["cell_factors"]) >= 8
    prohibited = " ".join(p["prohibited"] for p in cells["pooling_prohibitions"])
    assert "K1 with K2" in prohibited
    assert "primitive operation families" in prohibited
    assert "depth 2 with depth 3" in prohibited


def test_blocking_decisions_are_od2_od5_od6(protocol):
    assert protocol["blocking_decisions"] == ["OD2", "OD5", "OD6"]
    by_id = {d["id"]: d for d in protocol["unresolved_operator_decisions"]}
    assert sorted(by_id) == ["OD%d" % i for i in range(1, 9)]
    for did in ("OD2", "OD5", "OD6"):
        assert by_id[did]["status"] == "unresolved"
        assert by_id[did]["blocking"] is True
    for did in ("OD1", "OD3", "OD4", "OD7"):
        assert by_id[did]["status"] == "resolved"
        assert by_id[did].get("blocking") is False
    assert by_id["OD8"]["status"] == "resolved_in_part"


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


def test_selected_label_uniformity_has_exactly_one_classification(protocol):
    uniformity = _gate(protocol, "I3")["selected_label_uniformity"]
    assert uniformity["status"] == "gate"
    assert set(uniformity["not_applicable_to"]) == {"S2", "S3"}
    assert "never reclassified as diagnostic" in uniformity["single_classification"]


# --------------------------------------------------------------------------
# Counterbalancing: the published construction must actually be orthogonal
# --------------------------------------------------------------------------

def test_counterbalancing_construction_separates_position_from_symbol(protocol):
    design = protocol["counterbalancing_design"]
    assert design["construction_algorithm"]["randomness"].startswith("none")
    pairs = [(k % 4, (k // 4) % 4) for k in range(16)]
    assert len(set(pairs)) == 16, "the construction must be a complete crossing"
    positions = [p for p, _ in pairs]
    symbols = [s for _, s in pairs]
    for value in range(4):
        assert positions.count(value) == 4
        assert symbols.count(value) == 4
    for position in range(4):
        seen = {s for p, s in pairs if p == position}
        assert seen == {0, 1, 2, 3}, (
            "position %d must occur with every displayed symbol, otherwise "
            "position and symbol identity are confounded" % position)


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
# Markdown / JSON semantic parity - the defect that reached publication in v0.1
# --------------------------------------------------------------------------

def test_markdown_never_reintroduces_the_v0_1_defect_text(markdown):
    for text in FORBIDDEN_TEXT:
        assert text not in markdown, "forbidden v0.1 text reappeared: %r" % text


def test_markdown_agrees_with_json_on_every_decision_marker(protocol, markdown):
    required = [
        protocol["state"],
        "**Draft version:** draft-v0.2",
        "**Frozen:** `false`",
        "**Execution authorized:** `false`",
        "**Review state:** `awaiting_independent_methods_review`",
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


def test_markdown_does_not_claim_an_uncommitted_generator(protocol, markdown):
    statement = protocol["status"]["authoritative_artifact"]
    assert "no such generator is committed" in statement
    assert statement in markdown


# --------------------------------------------------------------------------
# Negative mutation battery: each mutation MUST be rejected
# --------------------------------------------------------------------------

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
    assert doc["blocking_decisions"] == ["OD2", "OD5", "OD6"]
    ranked = [e["interface"] for e in doc["admissibility_order"]["order"]]
    assert "S4" not in ranked
    by_id = {p["id"]: p for p in doc["interface_profiles"]}
    assert by_id["S4"]["selectable_status"] == "never_selectable"
    i5 = _gate(doc, "I5")
    assert "RP" in i5["model_roles"]
    assert any("K4" in inp for inp in i5["inputs"])
    for construct in ("I0", "I1a", "I1b", "I2", "I3", "I4"):
        assert construct in i5["covered_constructs"]
    for gate in doc["gate_hierarchy"]:
        assert not _asserts_failing_interface_stays_eligible(
            gate["legal_next_state_on_fail"])
        assert not _asserts_failing_interface_stays_eligible(gate["what_fails"])


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


def test_statistics_tables_record_no_operations():
    with open(STATS_TABLES, encoding="utf-8") as handle:
        tables = json.load(handle)
    for name, value in tables["operation_counts"].items():
        assert value == 0, "%s is %r" % (name, value)
    assert tables["status"] == \
        "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN"
    assert tables["draft_version"] == "draft-v0.2"


def test_paired_method_was_verified_before_use():
    with open(STATS_TABLES, encoding="utf-8") as handle:
        tables = json.load(handle)
    verification = tables["paired_method_verification"]
    assert verification["mcnemar_reduction_max_abs_deviation"] < 1e-9
    assert verification["constrained_mle_max_abs_deviation"] < 1e-6
    assert verification["exact_type_i_at_boundary"]
    for row in verification["exact_type_i_at_boundary"]:
        assert row["exact_type_i"] <= 0.025


def test_i4_chance_floor_is_recorded_as_rejected(protocol):
    tables = protocol["proposed_statistics"]["rejected_v0_1_i4_chance_null"]
    assert tables["status"] == "REJECTED_BY_OPERATOR_REVIEW"
    assert tables["acceptance_count"] == 49
    assert abs(tables["acceptance_rate"] - 49 / 128) < 1e-12
    threshold = _gate(protocol, "I4")["threshold_logic"]
    assert threshold["p_floor_proposal"] == 0.80
    assert threshold["rejected_v0_1_proposal"]["status"] == \
        "REJECTED_BY_OPERATOR_REVIEW"


def test_n192_is_not_offered_as_an_i3_justification(protocol):
    sizes = protocol["proposed_statistics"]["sample_sizes"]
    assert sizes["n_192_is_not_an_i3_justification"] is True
    assert sizes["blocking_decision"] == "OD6"
    verdict = protocol["proposed_statistics"]["i3_feasibility_verdict"]
    assert verdict["margin_0_05_supported_at_any_tested_discordance"] is False
    assert verdict["margin_0_05_discordance_rates_supported"] == []


def test_paired_sensitivity_covers_the_required_discordance_rates(protocol):
    rows = protocol["proposed_statistics"][
        "i3_secondary_paired_equivalence_sensitivity"]
    rates = {row["discordance_rate"] for row in rows}
    assert {0.05, 0.10, 0.20, 0.30} <= rates
    assert all(row["method"].startswith("Tango 1998") for row in rows)


# --------------------------------------------------------------------------
# The operator-review record must exist and stay additive
# --------------------------------------------------------------------------

def test_operator_review_record_is_present_and_additive():
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
