"""Tests for the Phase 1.2H live execution/access ledger.

Phase 1.2H terminated ``BLOCKED_ON_PRIVATE_SOURCE_ACCESS``; Phase 1.2H-R1
established authenticated byte-only access to the authoritative source and
moved the ledger to ``BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY``. The ledger is
therefore the round's principal machine-readable product, and every claim it
makes about what did *not* happen has to be enforced rather than asserted.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jspace_observation.parser_v3_v2_access_ledger import (  # noqa: E402
    BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE,
    COUNTER_GROUPS,
    COUNTER_PROVENANCE_CLASSES,
    EVENT_KINDS,
    LEDGER_SCHEMA_VERSION,
    SEMANTIC_PROJECTION_COUNTER_EXCLUDES,
    SEMANTIC_PROJECTION_EXCLUDES,
    TERMINAL_STATES,
    LedgerError,
    assert_monotonic_succession,
    counter_value,
    policy_semantics_sha256,
    validate_ledger,
)

LEDGER_PATH = ROOT / "docs" / "phase1_2h_execution_access_ledger.json"
POLICY_PATH = ROOT / "docs" / "phase1_parser_v3_v2_evaluation_policy.json"


@pytest.fixture(scope="module")
def policy_bytes() -> bytes:
    return POLICY_PATH.read_bytes()


@pytest.fixture(scope="module")
def policy(policy_bytes: bytes) -> dict:
    return json.loads(policy_bytes.decode("utf-8"))


@pytest.fixture()
def ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


# --- 1. The committed ledger ------------------------------------------------


def test_the_committed_ledger_validates_against_the_committed_policy(
    ledger, policy, policy_bytes
):
    validate_ledger(
        ledger,
        policy=policy,
        policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
    )


def test_the_committed_ledger_records_the_blocked_terminal_state(ledger):
    # R1 moved the blocker: byte-only access to the authoritative source now
    # succeeds, so BLOCKED_ON_PRIVATE_SOURCE_ACCESS is no longer true. What
    # blocks the round is the absence of a private semantic-review boundary.
    assert ledger["status"] == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    assert ledger["phase"] == "1.2H"
    assert ledger["schema_version"] == LEDGER_SCHEMA_VERSION


def test_every_prohibited_activity_is_recorded_as_zero(ledger):
    """The round's central factual claim, checked counter by counter."""
    for name in COUNTER_GROUPS["parser_execution"]:
        assert counter_value(ledger, "parser_execution", name) == 0
    for name in COUNTER_GROUPS["formal_v2_evaluation_access"]:
        assert counter_value(ledger, "formal_v2_evaluation_access", name) == 0
    for name in (
        "sealed_input_semantic_reads",
        "sealed_label_semantic_reads",
        "private_curator_files_read",
        "labels_opened_for_scoring",
    ):
        assert counter_value(ledger, "retired_v1_repair_access", name) == 0
    for name in COUNTER_GROUPS["v2_construction"]:
        assert counter_value(ledger, "v2_construction", name) == 0
    # data_plane_writes stays 0: R1 read bytes, it never wrote one. The other
    # three azure counters are no longer 0 and must not be asserted to be --- R1
    # provisioned resources and ran the gate, and a test that demanded zero here
    # would be asserting that the round did not happen.
    assert counter_value(ledger, "azure", "data_plane_writes") == 0


def test_the_byte_only_verifications_are_counted_apart_from_semantic_reads(ledger):
    """A digest of a file is not a read of its content, and the two never merge.

    This is the whole basis on which R1 claims to have touched every byte of the
    sealed set while learning nothing about it: 14 streams to a digest, 0 reads
    of content.
    """
    assert (
        counter_value(ledger, "retired_v1_repair_access",
                      "byte_only_integrity_verifications")
        == BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE
    )
    assert (
        counter_value(ledger, "retired_v1_repair_access", "sealed_input_semantic_reads")
        == 0
    )
    assert (
        counter_value(ledger, "retired_v1_repair_access", "sealed_label_semantic_reads")
        == 0
    )


def test_the_retired_set_state_is_unchanged_and_unqualified(ledger):
    state = ledger["retired_v1_state"]
    assert state["set_id"] == "parser-v3-v1"
    assert state["sealed_bytes_unchanged"] is True
    assert state["repair_input_content_accessed"] is False
    assert state["repair_label_content_accessed"] is False
    assert state["formal_evaluation_ever_run"] is False
    assert state["formal_eligibility"] == "RETIRED_AS_INELIGIBLE"
    assert (
        state["current_state_label"]
        == "SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE"
    )


def test_the_successor_set_count_is_null_not_zero(ledger):
    """L-32: an unobserved quantity is undefined, not measured to be zero."""
    successor = ledger["successor_set_state"]
    assert successor["exists"] is False
    assert successor["sealed"] is False
    assert successor["sealed_object_count"] is None
    assert "L-32" in successor["sealed_object_count_note"]


def test_the_snapshot_reproduces_the_policy_block_exactly(ledger, policy):
    assert (
        ledger["phase_1_2g_finalization_snapshot"]["values"]
        == policy["execution_state"]
    )


# --- 2. The semantic projection --------------------------------------------


def test_the_semantic_hash_ignores_only_the_execution_state_block(policy):
    """A licensed state update must not move the semantic hash."""
    baseline = policy_semantics_sha256(policy)
    touched = copy.deepcopy(policy)
    touched["execution_state"]["predictions_generated"] = 7
    assert policy_semantics_sha256(touched) == baseline


def test_the_semantic_hash_moves_when_any_other_field_moves(policy):
    """And a real semantic change must not be able to hide behind one."""
    baseline = policy_semantics_sha256(policy)
    touched = copy.deepcopy(policy)
    touched["status"] = "REVIEW_REQUIRED"
    assert policy_semantics_sha256(touched) != baseline

    touched = copy.deepcopy(policy)
    touched["acceptance_thresholds"]["items"][0]["threshold_id"] = "renamed"
    assert policy_semantics_sha256(touched) != baseline


def test_the_projection_list_is_exactly_the_execution_state(ledger):
    """G-04: nothing is projected out at the top level any more.

    Excluding the whole ``execution_state`` block also excluded its free-text
    ``final_policy_is_not_a_result`` statement, so that statement could assert a
    completed evaluation without moving the hash the ledger binds.
    """
    assert SEMANTIC_PROJECTION_EXCLUDES == ()
    assert SEMANTIC_PROJECTION_COUNTER_EXCLUDES == (
        "formal_evaluation_ordinal",
        "locked_label_reads",
        "parser_v3_runs_against_any_locked_set",
        "parser_v3_v2_sealed_sets_constructed",
        "predictions_generated",
    )
    binding = ledger["policy_binding"]
    assert binding["semantic_projection_excludes"] == list(
        SEMANTIC_PROJECTION_EXCLUDES
    )
    assert binding["semantic_projection_counter_excludes"] == list(
        SEMANTIC_PROJECTION_COUNTER_EXCLUDES
    )


def test_g04_the_semantic_hash_covers_the_final_policy_statement(policy):
    """The prose claim is inside the hash; only the counters are outside it."""
    baseline = policy_semantics_sha256(policy)

    rewritten = copy.deepcopy(policy)
    rewritten["execution_state"]["final_policy_is_not_a_result"] = (
        "A formal evaluation was run and parser v3 was validated."
    )
    assert policy_semantics_sha256(rewritten) != baseline

    for counter in SEMANTIC_PROJECTION_COUNTER_EXCLUDES:
        touched = copy.deepcopy(policy)
        touched["execution_state"][counter] = 7
        assert policy_semantics_sha256(touched) == baseline, counter


def test_g04_a_narrower_counter_projection_is_refused(ledger, policy, policy_bytes):
    """Declaring the old whole-block projection must not validate."""
    broken = copy.deepcopy(ledger)
    broken["policy_binding"]["semantic_projection_excludes"] = ["execution_state"]
    with pytest.raises(LedgerError, match="semantic_projection_excludes"):
        validate_ledger(
            broken,
            policy=policy,
            policy_sha256=hashlib.sha256(
                policy_bytes.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
            ).hexdigest(),
        )

    broken = copy.deepcopy(ledger)
    broken["policy_binding"]["semantic_projection_counter_excludes"] = [
        "final_policy_is_not_a_result"
    ]
    with pytest.raises(LedgerError, match="semantic_projection_counter_excludes"):
        validate_ledger(broken)


def test_a_wider_projection_is_refused(ledger, policy, policy_bytes):
    """Projecting out more than the state block would hide a semantic change."""
    broken = copy.deepcopy(ledger)
    broken["policy_binding"]["semantic_projection_excludes"] = [
        "execution_state",
        "acceptance_thresholds",
    ]
    with pytest.raises(LedgerError, match="semantic_projection_excludes"):
        validate_ledger(
            broken, policy=policy,
            policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
        )


# --- 3. Binding enforcement -------------------------------------------------


def test_a_wrong_policy_hash_is_refused(ledger, policy):
    with pytest.raises(LedgerError, match="policy_sha256"):
        validate_ledger(ledger, policy=policy, policy_sha256="0" * 64)


def test_a_wrong_semantic_hash_is_refused(ledger, policy, policy_bytes):
    broken = copy.deepcopy(ledger)
    broken["policy_binding"]["policy_semantics_sha256"] = "0" * 64
    with pytest.raises(LedgerError, match="policy_semantics_sha256"):
        validate_ledger(
            broken, policy=policy,
            policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
        )


def test_a_snapshot_that_paraphrases_the_policy_is_refused(ledger, policy):
    broken = copy.deepcopy(ledger)
    broken["phase_1_2g_finalization_snapshot"]["values"]["predictions_generated"] = 1
    with pytest.raises(LedgerError, match="snapshot of"):
        validate_ledger(broken, policy=policy)


def test_a_snapshot_not_labelled_as_history_is_refused(ledger, policy):
    broken = copy.deepcopy(ledger)
    broken["phase_1_2g_finalization_snapshot"]["role"] = "current state"
    with pytest.raises(LedgerError, match="snapshot"):
        validate_ledger(broken, policy=policy)


# --- 4. Counter typing ------------------------------------------------------


def test_a_boolean_is_not_a_count(ledger):
    """`isinstance(True, int)` is True, so the guard must exclude bool by name."""
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["parser_execution"]["candidate_predictions_generated"] = (
        False
    )
    with pytest.raises(LedgerError, match="non-negative int"):
        validate_ledger(broken)


def test_a_float_zero_is_not_a_count(ledger):
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["azure"]["data_plane_writes"] = 0.0
    with pytest.raises(LedgerError, match="non-negative int"):
        validate_ledger(broken)


def test_a_negative_count_is_refused(ledger):
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["azure"]["control_plane_reads"] = -1
    with pytest.raises(LedgerError, match="non-negative int"):
        validate_ledger(broken)


def test_an_undeclared_counter_is_refused(ledger):
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["azure"]["quietly_added"] = 3
    with pytest.raises(LedgerError, match="unknown counters"):
        validate_ledger(broken)


def test_a_missing_counter_group_is_refused(ledger):
    broken = copy.deepcopy(ledger)
    del broken["live_counters"]["parser_execution"]
    with pytest.raises(LedgerError, match="parser_execution is missing"):
        validate_ledger(broken)


# --- 5. Status must agree with the counters ---------------------------------


def test_a_blocked_source_round_cannot_record_a_semantic_read(ledger):
    broken = copy.deepcopy(ledger)
    broken["status"] = "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"
    broken["live_counters"]["retired_v1_repair_access"][
        "sealed_label_semantic_reads"
    ] = 1
    with pytest.raises(LedgerError, match="did not block on reaching it"):
        validate_ledger(broken)


def test_a_blocked_round_cannot_record_a_seal(ledger):
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["v2_construction"]["sets_sealed"] = 1
    with pytest.raises(LedgerError, match="did not block before sealing"):
        validate_ledger(broken)


def test_a_sealed_status_requires_a_seal_a_witness_and_a_contract(ledger):
    claimed = copy.deepcopy(ledger)
    claimed["status"] = "SEALED_READY_FOR_PREREGISTRATION"
    with pytest.raises(LedgerError, match="exactly one sealed set"):
        validate_ledger(claimed)

    claimed["live_counters"]["v2_construction"]["sets_sealed"] = 1
    with pytest.raises(LedgerError, match="listing witness"):
        validate_ledger(claimed)

    claimed["live_counters"]["v2_construction"]["listing_witnesses_obtained"] = 1
    with pytest.raises(LedgerError, match="exactly one final contract"):
        validate_ledger(claimed)


def test_no_phase_1_2h_ledger_may_record_a_parser_run(ledger):
    for name in COUNTER_GROUPS["parser_execution"]:
        broken = copy.deepcopy(ledger)
        broken["live_counters"]["parser_execution"][name] = 1
        with pytest.raises(LedgerError, match="no parser may"):
            validate_ledger(broken)


def test_no_phase_1_2h_ledger_may_record_a_preregistration(ledger):
    broken = copy.deepcopy(ledger)
    broken["live_counters"]["formal_v2_evaluation_access"][
        "preregistrations_completed"
    ] = 1
    with pytest.raises(LedgerError, match="neither preregistration nor evaluation"):
        validate_ledger(broken)


def test_an_invented_terminal_state_is_refused(ledger):
    broken = copy.deepcopy(ledger)
    broken["status"] = "READY_ENOUGH"
    with pytest.raises(LedgerError, match="not a recognised"):
        validate_ledger(broken)


# --- 6. Events --------------------------------------------------------------


def test_every_committed_event_uses_a_registered_kind(ledger):
    for event in ledger["events"]:
        assert event["kind"] in EVENT_KINDS


def test_no_committed_event_reports_reading_private_content(ledger):
    for event in ledger["events"]:
        assert event["private_content_read"] is False


def test_an_unregistered_event_kind_is_refused(ledger):
    broken = copy.deepcopy(ledger)
    broken["events"][0]["kind"] = "everything_went_fine"
    with pytest.raises(LedgerError, match="not a known kind"):
        validate_ledger(broken)


def test_event_sequences_must_strictly_increase(ledger):
    broken = copy.deepcopy(ledger)
    broken["events"][1]["sequence"] = broken["events"][0]["sequence"]
    with pytest.raises(LedgerError, match="duplicated"):
        validate_ledger(broken)


# --- 7. Monotonic succession ------------------------------------------------


def test_a_successor_may_add_events_and_raise_counters(ledger):
    successor = copy.deepcopy(ledger)
    successor["live_counters"]["azure"]["control_plane_reads"] += 4
    successor["events"].append(
        {
            "sequence": ledger["events"][-1]["sequence"] + 1,
            "kind": "source_authentication_attempt",
            "role": "primary_integrator",
            "summary": "second attempt",
            "private_content_read": False,
        }
    )
    assert_monotonic_succession(ledger, successor)


def test_a_successor_may_not_lower_a_counter(ledger):
    """Monotonicity is checked on a counter no event accounts for.

    ``byte_only_integrity_verifications`` was used here originally, but Audit G
    added event-to-counter reconciliation, so zeroing it now fails the earlier
    coherence check instead --- a stricter rejection of the same mutation.
    ``azure.control_plane_reads`` has no backing event, which isolates the
    monotonicity rule itself.
    """
    successor = copy.deepcopy(ledger)
    successor["live_counters"]["azure"]["control_plane_reads"] = 0
    with pytest.raises(LedgerError, match="monotonic"):
        assert_monotonic_succession(ledger, successor)


def test_g01_lowering_an_event_backed_counter_fails_coherence_first(ledger):
    """The same mutation on an event-backed counter is rejected even earlier."""
    successor = copy.deepcopy(ledger)
    # Also drop back to the pre-R1 status, so that the review-boundary rule is
    # not the one that fires. What is under test is narrower: an event that
    # records a byte-only verification must be backed by a counter that shows
    # one, whatever the declared status.
    successor["status"] = "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"
    successor["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = 0
    with pytest.raises(LedgerError, match="unsupported access claim"):
        assert_monotonic_succession(ledger, successor)


def test_a_successor_may_not_erase_an_event(ledger):
    successor = copy.deepcopy(ledger)
    successor["events"] = successor["events"][:-1]
    with pytest.raises(LedgerError, match="cannot be erased"):
        assert_monotonic_succession(ledger, successor)


def test_a_successor_may_not_rewrite_an_event(ledger):
    successor = copy.deepcopy(ledger)
    successor["events"][0]["summary"] = "something else entirely"
    with pytest.raises(LedgerError, match="immutable"):
        assert_monotonic_succession(ledger, successor)


# --- 8. The ledger does not touch a parser ----------------------------------


def test_the_ledger_module_names_no_parser_symbol():
    source = (
        ROOT / "src" / "jspace_observation" / "parser_v3_v2_access_ledger.py"
    ).read_text(encoding="utf-8")
    body = source.split('"""', 2)[2]
    for symbol in (
        "eval_parsing",
        "eval_parsing_v3",
        "parse_answer",
        "ParsedAnswer",
        "parse_typed",
        "legacy_parser",
    ):
        assert symbol not in body, symbol


def test_the_ledger_module_imports_only_the_standard_library():
    """State the dependency claim as what it is: an import allowlist.

    This assertion previously included the literal ``"import re"`` in the
    *parser symbol* list above. That conflated the standard library's regular
    expression module with this project's answer parser, which is the same
    overbroad-claim defect the parser-isolation wording rules forbid. The real
    claim is that the ledger pulls in no project module and no third-party
    package, and an allowlist checks that directly and more strictly than one
    substring ever did.
    """
    allowed = {"hashlib", "json", "re", "typing", "__future__"}
    tree = ast.parse(
        (
            ROOT / "src" / "jspace_observation" / "parser_v3_v2_access_ledger.py"
        ).read_text(encoding="utf-8")
    )
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError("relative import: the module must stand alone")
            seen.add((node.module or "").split(".")[0])
    assert seen <= allowed, seen - allowed


# --- 9. Audit G: the ledger cannot validate its own negation ----------------


def _sha(path):
    return hashlib.sha256(
        path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()


def _validate(ledger, policy):
    validate_ledger(ledger, policy=policy, policy_sha256=_sha(POLICY_PATH))


def test_g01_a_fabricated_sealed_successor_set_is_refused(ledger, policy):
    """The exact mutation Audit G used, which validated and was then rendered."""
    ledger["successor_set_state"].update(
        {"exists": True, "sealed": True, "sealed_object_count": 120}
    )
    with pytest.raises(LedgerError, match="sets_sealed"):
        _validate(ledger, policy)


def test_g01_exists_requires_a_constructed_or_sealed_set(ledger, policy):
    ledger["successor_set_state"]["exists"] = True
    with pytest.raises(LedgerError, match="cannot exist"):
        _validate(ledger, policy)


def test_g01_an_unsealed_set_may_not_carry_an_object_count(ledger, policy):
    """L-32: the count needs an authenticated seal-time observation."""
    ledger["successor_set_state"]["sealed_object_count"] = 0
    with pytest.raises(LedgerError, match="must be null"):
        _validate(ledger, policy)


def test_g01_a_semantic_read_event_needs_a_counter_behind_it(ledger, policy):
    ledger["events"].append(
        {
            "sequence": 999,
            "kind": "retired_v1_semantic_read",
            "role": "primary_integrator",
            "summary": "Decoded the sealed source.",
            "private_content_read": True,
        }
    )
    with pytest.raises(LedgerError, match="unsupported access claim"):
        _validate(ledger, policy)


def test_g01_an_inherently_private_event_may_not_deny_private_access(ledger, policy):
    ledger["events"].append(
        {
            "sequence": 999,
            "kind": "private_curator_file_read",
            "role": "primary_integrator",
            "summary": "Opened a curator note.",
            "private_content_read": False,
        }
    )
    with pytest.raises(LedgerError, match="by definition"):
        _validate(ledger, policy)


def test_g01_a_phase_forbidden_event_kind_is_refused(ledger, policy):
    for kind in ("parser_invocation", "prediction_generation", "formal_evaluation"):
        probe = copy.deepcopy(ledger)
        probe["events"].append(
            {
                "sequence": 999,
                "kind": kind,
                "role": "primary_integrator",
                "summary": "Did the thing.",
                "private_content_read": False,
            }
        )
        with pytest.raises(LedgerError, match="not authorised in Phase 1.2H"):
            _validate(probe, policy)


def test_g01_an_event_may_not_carry_an_unvalidated_field(ledger, policy):
    ledger["events"].append(
        {
            "sequence": 999,
            "kind": "baseline_verification",
            "role": "primary_integrator",
            "summary": "Fine.",
            "private_content_read": False,
            "reassurance": "everything is fine",
        }
    )
    with pytest.raises(LedgerError, match="unknown keys"):
        _validate(ledger, policy)


def test_g01_an_unknown_top_level_block_is_refused(ledger, policy):
    ledger["reassuring_block"] = {"everything": "fine"}
    with pytest.raises(LedgerError, match="unknown top-level keys"):
        _validate(ledger, policy)


def test_g01_an_unknown_state_field_is_refused(ledger, policy):
    ledger["successor_set_state"]["looks_ready"] = True
    with pytest.raises(LedgerError, match="unknown keys"):
        _validate(ledger, policy)


def test_g01_narrated_v1_access_must_match_the_counters(ledger, policy):
    for field in ("repair_input_content_accessed", "repair_label_content_accessed"):
        probe = copy.deepcopy(ledger)
        probe["retired_v1_state"][field] = True
        with pytest.raises(LedgerError, match="disagrees with"):
            _validate(probe, policy)


def test_g01_the_retired_state_label_cannot_be_softened(ledger, policy):
    ledger["retired_v1_state"]["current_state_label"] = "SEALED / READY"
    with pytest.raises(LedgerError, match="current_state_label"):
        _validate(ledger, policy)


def test_g01_the_retired_set_may_not_be_declared_scorable(ledger, policy):
    ledger["retired_v1_state"]["formally_scorable"] = True
    with pytest.raises(LedgerError, match="unscorable"):
        _validate(ledger, policy)


def test_g01_succession_validates_both_ledgers_before_comparing(ledger):
    """A status-only jump was accepted because neither record was validated."""
    successor = copy.deepcopy(ledger)
    successor["status"] = "SEALED_READY_FOR_PREREGISTRATION"
    with pytest.raises(LedgerError, match="requires exactly one sealed set"):
        assert_monotonic_succession(ledger, successor)


def test_g01_the_committed_ledger_is_its_own_legal_successor(ledger):
    assert_monotonic_succession(copy.deepcopy(ledger), copy.deepcopy(ledger))


def test_g01_the_generator_refuses_to_render_an_invalid_ledger(monkeypatch, tmp_path):
    """The generator published the fabricated set because it never validated."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_g01_generator", ROOT / "scripts" / "generate_current_state.py"
    )
    generator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)

    broken = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    broken["successor_set_state"].update(
        {"exists": True, "sealed": True, "sealed_object_count": 120}
    )
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(broken, indent=2), encoding="utf-8")
    monkeypatch.setattr(generator, "LEDGER_PATH", path)

    with pytest.raises(generator.LedgerError):
        generator._load_ledger()

# ---------------------------------------------------------------------------
# Section 10. Post-Audit-G self-review: the projection note is a narrated field
# ---------------------------------------------------------------------------
#
# Audit G's blocker was a narrated field drifting away from the validated field
# beside it. Applying that finding to the ledger's own text found the same
# defect one level down: after G-04 narrowed the projection to five counters,
# ``policy_binding.note`` still said the whole ``execution_state`` block was
# projected out. The structured neighbours were validated; the sentence was not.


def test_the_shipped_projection_note_names_the_counters(ledger):
    note = ledger["policy_binding"]["note"]
    assert "counters" in note
    assert "semantic_projection_counter_excludes" in note


def test_a_note_claiming_the_whole_block_is_projected_out_is_refused(
    ledger, policy
):
    """The exact stale sentence this rule was written to catch."""
    ledger["policy_binding"]["note"] = (
        "policy_semantics_sha256 is computed over the policy with "
        "execution_state projected out."
    )
    with pytest.raises(LedgerError, match="projected"):
        _validate(ledger, policy)


@pytest.mark.parametrize(
    "sentence",
    [
        "The hash excludes execution_state.",
        "We project out the whole execution_state block.",
        "execution_state is removed before hashing.",
        "The projection excluded execution_state entirely.",
    ],
)
def test_every_phrasing_of_the_overstated_claim_is_refused(
    ledger, policy, sentence
):
    ledger["policy_binding"]["note"] = sentence
    with pytest.raises(LedgerError, match="semantic hash"):
        _validate(ledger, policy)


@pytest.mark.parametrize(
    "sentence",
    [
        "The five execution_state counters are projected out.",
        "Audit G rejected projecting out the whole execution_state block.",
        "An earlier design excluded execution_state; this one does not.",
        "execution_state is no longer projected out.",
    ],
)
def test_a_qualified_sentence_still_passes(ledger, policy, sentence):
    """Naming the counters, or recording a superseded design, is legitimate."""
    ledger["policy_binding"]["note"] = sentence
    _validate(ledger, policy)


def test_the_rule_reads_every_string_field_not_only_the_note(ledger, policy):
    """bytes_modified_note is prose beside the same validated fields."""
    ledger["policy_binding"]["bytes_modified_note"] = (
        "One block changed. execution_state was projected out of the hash."
    )
    with pytest.raises(LedgerError, match="bytes_modified_note"):
        _validate(ledger, policy)


def test_the_qualifier_must_share_the_sentence_with_the_claim(ledger, policy):
    """A rejection marker in a *different* sentence must not launder a claim."""
    ledger["policy_binding"]["note"] = (
        "execution_state is projected out. A different design was rejected."
    )
    with pytest.raises(LedgerError, match="projected"):
        _validate(ledger, policy)


def test_prose_unrelated_to_the_projection_is_untouched(ledger, policy):
    ledger["policy_binding"]["note"] = (
        "The execution_state block records counters that only a licensed "
        "round may increment."
    )
    _validate(ledger, policy)

# --- R1: the private-review-boundary terminal state -------------------------
#
# Independent Audit B (B-11) found that `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`
# --- the terminal state Phase 1.2H-R1 was heading for --- was not a state this
# ledger would accept, while the *old* status was accepted alongside the new
# R1 counters. The state now exists and, crucially, has to be earned.


def test_the_review_boundary_state_is_registered():
    assert "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY" in TERMINAL_STATES


def test_the_review_boundary_state_requires_a_completed_byte_only_gate(ledger, policy):
    # The precedence rule: a round that never reached the source must record
    # BLOCKED_ON_PRIVATE_SOURCE_ACCESS, not the state that means "I reached it
    # and stopped at the reviewer". Without this, the more advanced-sounding
    # state could be claimed by a round that did strictly less.
    ledger["status"] = "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    ledger["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = 2
    with pytest.raises(LedgerError, match="byte-only access gate"):
        _validate(ledger, policy)


def test_the_review_boundary_state_is_accepted_after_the_gate(ledger, policy):
    ledger["status"] = "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    ledger["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE
    _validate(ledger, policy)


def test_a_partial_gate_does_not_earn_the_review_boundary_state(ledger, policy):
    # 13 = the two pre-R1 verifications plus 11 of the 12 objects. A gate that
    # did not complete every object has not established the byte-only claim.
    ledger["status"] = "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    ledger["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE - 1
    with pytest.raises(LedgerError, match="byte-only access gate"):
        _validate(ledger, policy)


def test_the_committed_ledger_has_actually_earned_its_state(ledger):
    """Not a mutation test: the real committed record must satisfy the rule."""
    assert ledger["status"] == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    assert (
        counter_value(ledger, "retired_v1_repair_access",
                      "byte_only_integrity_verifications")
        >= BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE
    )


def test_the_review_boundary_state_still_forbids_a_semantic_read(ledger, policy):
    # The boundary is precisely what prevents a semantic read, so a round that
    # performed one did not block on it.
    ledger["status"] = "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    ledger["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE
    ledger["live_counters"]["retired_v1_repair_access"]["sealed_input_semantic_reads"] = 1
    with pytest.raises(LedgerError, match="semantic reads"):
        _validate(ledger, policy)


def test_a_novel_terminal_state_is_still_refused(ledger, policy):
    # Adding one state must not open the door to inventing others.
    ledger["status"] = "READY_FOR_PRIVATE_REVIEW"
    with pytest.raises(LedgerError):
        _validate(ledger, policy)


# --- counter provenance -----------------------------------------------------
#
# R1 produced two kinds of number at once: counters read out of a
# schema-validated execution receipt, and counters an operator kept by hand
# across an interactive session. Recording both without saying which is which
# would let the second borrow the authority of the first.


def test_the_provenance_block_is_validated_not_decorative(ledger, policy):
    ledger["counter_provenance"]["receipt_derived_exact"]["counters"].append(
        "azure.reads_that_do_not_exist"
    )
    with pytest.raises(LedgerError, match="not a counter this ledger carries"):
        _validate(ledger, policy)


def test_a_counter_may_not_hold_two_provenances(ledger, policy):
    ledger["counter_provenance"]["operator_maintained_approximate"][
        "counters"
    ].append("azure.data_plane_writes")
    with pytest.raises(LedgerError, match="a counter has one provenance"):
        _validate(ledger, policy)


@pytest.mark.parametrize(
    "path",
    [
        "retired_v1_repair_access.sealed_input_semantic_reads",
        "retired_v1_repair_access.sealed_label_semantic_reads",
        "retired_v1_repair_access.byte_only_integrity_verifications",
        "azure.data_plane_content_reads",
        "azure.data_plane_writes",
        "parser_execution.parser_invocations_on_private_or_locked_data",
        "parser_execution.candidate_predictions_generated",
        "parser_execution.comparator_predictions_generated",
    ],
)
def test_every_safety_counter_must_declare_its_evidence(ledger, policy, path):
    for entry in ledger["counter_provenance"].values():
        if isinstance(entry, dict) and path in entry.get("counters", []):
            entry["counters"].remove(path)
    with pytest.raises(LedgerError, match="must state where its value came from"):
        _validate(ledger, policy)


def test_a_safety_counter_may_not_be_downgraded_to_recollection(ledger, policy):
    # The exact laundering this check exists to stop: move
    # "no semantic read occurred" from receipt evidence to an operator's memory
    # while leaving the value at 0, and the ledger still reads as safe.
    ledger["counter_provenance"]["receipt_derived_exact"]["counters"].remove(
        "retired_v1_repair_access.sealed_input_semantic_reads"
    )
    ledger["counter_provenance"]["operator_maintained_approximate"][
        "counters"
    ].append("retired_v1_repair_access.sealed_input_semantic_reads")
    with pytest.raises(LedgerError, match="requires machine evidence"):
        _validate(ledger, policy)


def test_a_fourth_vaguer_provenance_class_is_refused(ledger, policy):
    ledger["counter_provenance"]["believed_accurate"] = {
        "counters": ["azure.control_plane_reads"]
    }
    with pytest.raises(LedgerError, match="the classes are fixed"):
        _validate(ledger, policy)


def test_an_empty_class_is_refused(ledger, policy):
    ledger["counter_provenance"]["azure_verified_exact"]["counters"] = []
    with pytest.raises(LedgerError, match="non-empty list"):
        _validate(ledger, policy)


def test_the_classes_are_exposed_for_reuse():
    assert COUNTER_PROVENANCE_CLASSES == (
        "receipt_derived_exact",
        "azure_verified_exact",
        "structurally_zero_by_source_analysis",
        "operator_maintained_approximate",
    )


def test_every_class_carries_a_stated_meaning():
    # Audit C (C-04): a class name is not self-explanatory. Adding a class
    # without saying what it asserts is how a weak provenance claim gets to
    # look like a strong one.
    from jspace_observation.parser_v3_v2_access_ledger import (
        COUNTER_PROVENANCE_CLASS_MEANING,
    )

    assert set(COUNTER_PROVENANCE_CLASS_MEANING) == set(COUNTER_PROVENANCE_CLASSES)
    assert all(
        len(meaning) > 40 for meaning in COUNTER_PROVENANCE_CLASS_MEANING.values()
    )


# --- the ledger must agree with the receipt it cites ------------------------
#
# counter_provenance claims eight counters come from
# docs/phase1_2h_r1_access_receipt_003.json. That claim is worth nothing unless
# something checks it, so this is that check: the ledger and its cited evidence
# are compared value by value.

RECEIPT_PATH = ROOT / "docs" / "phase1_2h_r1_access_receipt_003.json"
PRE_R1_BYTE_ONLY_VERIFICATIONS = 2


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def test_the_cited_receipt_exists_and_records_a_pass(receipt):
    assert receipt["schema_version"] == "phase1-2h-r1-access-receipt/v1"
    assert receipt["execution"]["exit_status"] == "PASS"
    assert receipt["verdict"]["access_gate_passed"] is True
    assert receipt["verdict"]["invariants_failed"] == []


def test_the_byte_only_count_is_the_receipt_plus_the_pre_r1_verifications(
    ledger, receipt
):
    assert (
        counter_value(ledger, "retired_v1_repair_access",
                      "byte_only_integrity_verifications")
        == receipt["counters"]["byte_only_integrity_verifications"]
        + PRE_R1_BYTE_ONLY_VERIFICATIONS
    )


def test_the_data_plane_counters_come_from_the_receipt(ledger, receipt):
    assert (
        counter_value(ledger, "azure", "data_plane_content_reads")
        == receipt["counters"]["azure_data_plane_content_reads"]
    )
    assert (
        counter_value(ledger, "azure", "data_plane_writes")
        == receipt["counters"]["azure_data_plane_writes"]
    )


@pytest.mark.parametrize(
    ("group", "name", "receipt_key"),
    [
        ("retired_v1_repair_access", "sealed_input_semantic_reads",
         "semantic_input_reads"),
        ("retired_v1_repair_access", "sealed_label_semantic_reads",
         "semantic_label_reads"),
        ("parser_execution", "parser_invocations_on_private_or_locked_data",
         "parser_invocations"),
        ("parser_execution", "candidate_predictions_generated",
         "predictions_generated"),
    ],
)
def test_each_safety_counter_matches_its_evidence(
    ledger, receipt, group, name, receipt_key
):
    assert counter_value(ledger, group, name) == receipt["counters"][receipt_key]


def test_the_receipt_reproduces_the_committed_public_anchor(receipt):
    """The gate is only evidence because its output was already public."""
    assert (
        receipt["streaming"]["observed_aggregate_digest"]
        == "e1364afcac87516813d33a4e9fb3e370769487ab2f3ca47a08a3b4059db14e71"
    )
    assert receipt["streaming"]["objects_streamed"] == 12
    assert receipt["streaming"]["total_bytes_streamed"] == 396613
    assert receipt["streaming"]["decode_attempts"] == 0
    assert receipt["streaming"]["persist_attempts"] == 0


def test_the_receipt_carries_no_case_content(receipt):
    """A receipt that could carry a span or an answer would defeat the round.

    The bound is on shape, not length alone: every string in the receipt must be
    a single token drawn from ``[A-Za-z0-9:._-]``. Case content --- a question, a
    span, a canonical answer --- is prose, and prose cannot survive that filter.
    A length cap alone would not do it, since a 60-character answer is possible.
    """
    token = re.compile(r"^[A-Za-z0-9:._/-]{1,80}$")

    def walk(node, path="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key, f"{path}.{key} (key)"
                yield from walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from walk(value, f"{path}[{index}]")
        elif isinstance(node, str):
            yield node, path

    for value, path in walk(receipt):
        assert token.match(value), f"{path} = {value!r} is not a content-free token"
