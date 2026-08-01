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

from jspace_observation import parser_v3_v2_access_ledger as ledger_module  # noqa: E402
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
    # Audits E (E-18) and F: this counter is now pinned to its exact value, so
    # `validate_ledger` --- which `assert_monotonic_succession` runs first ---
    # rejects the mutation before succession is reached. That is a strictly
    # earlier refusal, not a weaker one, and the pin has its own test below.
    # The event-coherence rule this test exists to protect is therefore called
    # directly, so that removing it would still fail here.
    with pytest.raises(LedgerError, match="unsupported access claim"):
        ledger_module._validate_event_counter_support(successor, successor["events"])
    with pytest.raises(LedgerError):
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
    allowed = {"hashlib", "json", "pathlib", "re", "typing", "__future__"}
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
    """The exact mutation Audit G used, which validated and was then rendered.

    The assertion targets ``_validate_successor_set_state`` directly. Since the
    F-10 correction the same mutation also falsifies the never-occurred
    provenance binding --- a set that exists cannot have had its sealed inputs
    never read --- and that rule runs earlier, so a whole-ledger ``match=``
    would silently start testing the other rule. Both must refuse it, so both
    are asserted.
    """
    ledger["successor_set_state"].update(
        {"exists": True, "sealed": True, "sealed_object_count": 120}
    )
    with pytest.raises(LedgerError, match="sets_sealed"):
        ledger_module._validate_successor_set_state(ledger, ledger["status"])
    with pytest.raises(LedgerError):
        _validate(ledger, policy)


def test_g01_exists_requires_a_constructed_or_sealed_set(ledger, policy):
    ledger["successor_set_state"]["exists"] = True
    with pytest.raises(LedgerError, match="cannot exist"):
        ledger_module._validate_successor_set_state(ledger, ledger["status"])
    with pytest.raises(LedgerError):
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
    for name, entry in list(ledger["counter_provenance"].items()):
        if not isinstance(entry, dict) or path not in entry.get("counters", []):
            continue
        entry["counters"].remove(path)
        # A composite decomposes the counters it names, so the decomposition
        # goes with it; leaving an orphaned `parts` entry would fail on the
        # wrong rule and stop this test from reaching the one it is about.
        entry.get("parts", {}).pop(path, None)
        if not entry["counters"]:
            del ledger["counter_provenance"][name]
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
    ledger["counter_provenance"]["azure_transcript_exact"]["counters"] = []
    with pytest.raises(LedgerError, match="non-empty list"):
        _validate(ledger, policy)


def test_the_classes_are_exposed_for_reuse():
    assert COUNTER_PROVENANCE_CLASSES == (
        "receipt_derived_exact",
        "azure_transcript_exact",
        "structurally_zero_by_source_analysis",
        "zero_because_the_activity_has_never_occurred",
        "composite_of_separately_evidenced_parts",
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


# --- Audit E / Audit F regressions -----------------------------------------


def test_a_structurally_zero_counter_may_not_carry_a_non_zero_value(ledger, policy):
    """E-05: the class asserted a zero it never checked.

    ``structurally_zero_by_source_analysis`` means "no code path can make this
    non-zero". A ledger could nonetheless report a positive value under it, so
    the class's whole meaning was decorative.

    The class rule is exercised directly here rather than through
    ``validate_ledger``. Since E-16 the same mutation is *also* caught by the
    class-independent phase pin, which runs first because it is a safety rule
    rather than a bookkeeping one --- so going through the front door would
    assert the pin's message and leave this rule untested. Both are covered:
    the pin has its own test below.
    """

    ledger["live_counters"]["retired_v1_repair_access"]["private_curator_files_read"] = 3
    with pytest.raises(LedgerError, match="falsifies the class"):
        ledger_module._validate_counter_provenance_values(
            ledger["counter_provenance"], ledger["live_counters"]
        )


def test_a_safety_counter_cannot_escape_its_zero_pin_by_changing_class(
    ledger, policy
):
    """E-16: the value rules were keyed on the provenance class.

    Audit E moved ``labels_opened_for_scoring`` into the composite class with
    two prose addends summing to 7, and ``validate_ledger`` accepted it. The
    class-keyed rules could be escaped by reclassifying. This asserts the pin
    holds under every class the ledger admits, including the two that were
    supposed to guarantee zero and the one that was used to escape them.
    """

    path = "formal_v2_evaluation_access.labels_opened_for_scoring"
    for class_name in ledger_module.COUNTER_PROVENANCE_CLASSES:
        mutated = copy.deepcopy(ledger)
        for name, block in mutated["counter_provenance"].items():
            if name == "role":
                continue
            if path in block.get("counters", []):
                block["counters"].remove(path)
            block.get("parts", {}).pop(path, None)
        target = mutated["counter_provenance"].setdefault(
            class_name, {"counters": [], "evidence": "docs/placeholder.json"}
        )
        target.setdefault("counters", []).append(path)
        if class_name == "composite_of_separately_evidenced_parts":
            target.setdefault("parts", {})[path] = [
                {"amount": 4, "evidence": "docs/phase1_2h_r1_access_receipt_003.json"},
                {"amount": 3, "evidence": "docs/phase1_2h_r1_job_execution_inventory.json"},
            ]
        mutated["live_counters"]["formal_v2_evaluation_access"][
            "labels_opened_for_scoring"
        ] = 7
        with pytest.raises(LedgerError):
            _validate(mutated, policy)


def test_a_composite_addend_on_a_safety_counter_must_cite_an_artifact(
    ledger, policy
):
    """E-16: composite addends were only required to be distinct non-empty text.

    The class-level evidence string was citation-checked, but for a composite
    that string only describes how the decomposition works --- the addends are
    where the claims live. This pins the rule that closes it, on the one safety
    counter whose correct value is positive and which therefore cannot be
    protected by a zero pin.
    """

    parts = ledger["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ]["retired_v1_repair_access.byte_only_integrity_verifications"]
    parts[1] = dict(parts[1], evidence="batch two, recalled")
    with pytest.raises(LedgerError, match="cites no committed artifact"):
        _validate(ledger, policy)


def test_a_never_occurred_counter_may_not_carry_a_non_zero_value(ledger, policy):
    ledger["live_counters"]["formal_v2_evaluation_access"][
        "sealed_input_semantic_reads"
    ] = 1
    with pytest.raises(LedgerError):
        _validate(ledger, policy)


def test_the_zero_classes_are_named_in_one_place(ledger):
    # Both zero-asserting classes must be subject to the same rule. Naming them
    # inline is how the second one would escape it.
    from jspace_observation.parser_v3_v2_access_ledger import _MUST_BE_ZERO_CLASSES

    assert _MUST_BE_ZERO_CLASSES <= set(COUNTER_PROVENANCE_CLASSES)
    assert "structurally_zero_by_source_analysis" in _MUST_BE_ZERO_CLASSES
    assert "zero_because_the_activity_has_never_occurred" in _MUST_BE_ZERO_CLASSES


def test_the_structural_class_no_longer_claims_ast_enforcement_it_lacks(ledger):
    """E-05: four counters were classed as AST-enforced when no check reaches them.

    No AST check in this repository examines a scoring path or a comparator run,
    because no such code was written. Those counters are zero because the
    activity never happened, which is a weaker fact, and they now say so.
    """

    prov = ledger["counter_provenance"]
    structural = set(prov["structurally_zero_by_source_analysis"]["counters"])
    never = set(prov["zero_because_the_activity_has_never_occurred"]["counters"])

    for path in (
        "retired_v1_repair_access.labels_opened_for_scoring",
        "formal_v2_evaluation_access.sealed_input_semantic_reads",
        "formal_v2_evaluation_access.sealed_label_semantic_reads",
        "parser_execution.comparator_predictions_generated",
    ):
        assert path in never, path
        assert path not in structural, path


def test_the_composite_counter_decomposes_into_its_addends(ledger):
    """F-06: 14 was presented as receipt-derived when the receipt reports 12."""

    prov = ledger["counter_provenance"]
    counter = "retired_v1_repair_access.byte_only_integrity_verifications"
    assert counter not in prov["receipt_derived_exact"]["counters"]

    composite = prov["composite_of_separately_evidenced_parts"]
    assert counter in composite["counters"]
    addends = composite["parts"][counter]
    assert sum(a["amount"] for a in addends) == (
        ledger["live_counters"]["retired_v1_repair_access"][
            "byte_only_integrity_verifications"
        ]
    )
    assert len({a["evidence"] for a in addends}) == len(addends)
    assert any("receipt_003" in a["evidence"] for a in addends)


def test_a_composite_whose_parts_do_not_sum_is_refused(ledger, policy):
    counter = "retired_v1_repair_access.byte_only_integrity_verifications"
    ledger["counter_provenance"]["composite_of_separately_evidenced_parts"]["parts"][
        counter
    ][0]["amount"] = 99
    with pytest.raises(LedgerError, match="sum to"):
        _validate(ledger, policy)


def test_a_composite_without_a_decomposition_is_refused(ledger, policy):
    del ledger["counter_provenance"]["composite_of_separately_evidenced_parts"]["parts"]
    # Two rules refuse this, and the stronger one speaks first: a composite with
    # no decomposition has no receipt-backed addend either, so the terminal
    # state is what fails. That ordering is correct -- it names the consequence
    # rather than the schema defect -- so the test asserts the refusal and then
    # exercises the decomposition rule directly below.
    with pytest.raises(LedgerError):
        _validate(ledger, policy)


def test_the_decomposition_rule_names_the_missing_parts_mapping(ledger):
    from jspace_observation.parser_v3_v2_access_ledger import (
        _validate_counter_provenance_values,
    )

    block = copy.deepcopy(ledger["counter_provenance"])
    del block["composite_of_separately_evidenced_parts"]["parts"]
    with pytest.raises(LedgerError, match="requires a 'parts' mapping"):
        _validate_counter_provenance_values(block, ledger["live_counters"])


def test_a_composite_whose_addends_share_evidence_is_refused(ledger, policy):
    counter = "retired_v1_repair_access.byte_only_integrity_verifications"
    parts = ledger["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ][counter]
    parts[1]["evidence"] = parts[0]["evidence"]
    with pytest.raises(LedgerError, match="not composite"):
        _validate(ledger, policy)


def test_the_boundary_state_still_requires_a_receipt_backed_addend(ledger, policy):
    """F-06 must not have weakened the C-02 rule into a formality.

    Moving the counter into the composite class could have let the terminal
    state be earned by a composite made entirely of hand-carried parts.
    """

    counter = "retired_v1_repair_access.byte_only_integrity_verifications"
    parts = ledger["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ][counter]
    for addend in parts:
        addend["evidence"] = "an operator's notebook, page 4"
    ledger["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "evidence"
    ] = "docs/phase1_2h_execution_access_ledger.json events 2 and 8"
    with pytest.raises(LedgerError, match="cite a committed access receipt"):
        _validate(ledger, policy)


def test_labels_opened_for_scoring_requires_machine_evidence():
    """E-10: the strongest safety claim the ledger makes was carriable on memory."""

    from jspace_observation.parser_v3_v2_access_ledger import (
        _MACHINE_EVIDENCE_REQUIRED,
    )

    assert (
        "formal_v2_evaluation_access.labels_opened_for_scoring"
        in _MACHINE_EVIDENCE_REQUIRED
    )


def test_labels_opened_for_scoring_may_not_be_downgraded_to_recollection(
    ledger, policy
):
    path = "formal_v2_evaluation_access.labels_opened_for_scoring"
    ledger["counter_provenance"]["zero_because_the_activity_has_never_occurred"][
        "counters"
    ].remove(path)
    ledger["counter_provenance"]["operator_maintained_approximate"]["counters"].append(
        path
    )
    with pytest.raises(LedgerError, match="requires machine evidence"):
        _validate(ledger, policy)


def test_a_parser_counter_reports_the_parser_rule_not_the_bookkeeping_rule(
    ledger, policy
):
    """The value rules run last, deliberately.

    A ledger that records a parser invocation violates the prohibition on
    running a parser. That it also falsifies the counter's provenance class is
    bookkeeping, and a reader must be told the first.
    """

    ledger["live_counters"]["parser_execution"][
        "comparator_predictions_generated"
    ] = 1
    with pytest.raises(LedgerError, match="no parser may"):
        _validate(ledger, policy)


def test_the_two_positive_safety_counters_are_pinned_to_their_exact_values(ledger):
    """Audits E (E-18) and F, independently: neither counter was constrained.

    ``_PHASE_1_2H_ZERO_ACCESS_COUNTERS`` excludes these two because their
    correct value is positive. A comment in the previous commit claimed the
    receipt-citation rule constrained them instead. It did not. Audit E set
    ``data_plane_content_reads`` to 500 with no other edit and the ledger
    validated; it then raised ``byte_only_integrity_verifications`` from 14 to
    99 by resumming the composite addends with citations to files that really
    exist, and that validated too --- the citation rule checks addend *shape*,
    never addend *amounts*, and never reached the first counter at all.

    These are the counters recording how many private objects' bytes were read
    and how many verifications stand behind the terminal state, so an operator
    typo and a deliberate inflation must look the same to the validator.
    """
    for group, name, correct in (
        ("azure", "data_plane_content_reads", 12),
        ("retired_v1_repair_access", "byte_only_integrity_verifications", 14),
    ):
        assert ledger["live_counters"][group][name] == correct

        for wrong in (correct + 1, correct - 1, 0, 500):
            mutated = copy.deepcopy(ledger)
            mutated["live_counters"][group][name] = wrong
            with pytest.raises(LedgerError):
                validate_ledger(mutated)

        # Downward mutations were already owned by the pre-existing floor rule
        # and by the event-coherence rule --- which is why both audits attacked
        # *upward*, the one direction nothing checked. So the pin is asserted to
        # own that direction specifically: deleting it makes these lines pass.
        for wrong in (correct + 1, correct + 7, 500):
            mutated = copy.deepcopy(ledger)
            mutated["live_counters"][group][name] = wrong
            with pytest.raises(LedgerError, match=f"must equal {correct}"):
                ledger_module._validate_status_agreement(mutated, mutated["status"])

    # Audit E's exact counterexample: the inflation is made self-consistent by
    # resumming the composite addends against files that exist, which is what
    # defeated every rule that was in place.
    inflated = copy.deepcopy(ledger)
    inflated["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = 99
    parts = inflated["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ]["retired_v1_repair_access.byte_only_integrity_verifications"]
    parts[1] = {
        "amount": 99 - parts[0]["amount"],
        "evidence": "docs/phase1_2h_r1_job_execution_inventory.json",
    }
    with pytest.raises(LedgerError, match="must equal 14"):
        validate_ledger(inflated)


def test_a_citation_to_a_file_that_does_not_exist_is_refused(ledger):
    """Audit F: the citation check was syntax-only.

    ``_CITATION_PATTERN`` matches any token ending in ``.py``/``.json``/``.md``,
    so ``docs/does-not-exist.json`` satisfied it. A citation that cannot be
    followed is not evidence, so cited paths are now resolved against the
    repository root and must be real files.
    """
    mutated = copy.deepcopy(ledger)
    parts = mutated["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ]["retired_v1_repair_access.byte_only_integrity_verifications"]
    parts[1] = dict(parts[1], evidence="docs/phase1_2h_r1_access_receipt_fake.json")
    with pytest.raises(LedgerError):
        validate_ledger(mutated)

    # The control: the same addend citing a file that does exist is accepted, so
    # the refusal above is attributable to existence and not to the edit itself.
    restored = copy.deepcopy(ledger)
    validate_ledger(restored)


def test_the_never_occurred_class_is_bound_to_the_state_it_appeals_to(ledger):
    """Audit F: a record assertion was passing a "machine evidence" rule.

    ``_MACHINE_EVIDENCE_REQUIRED`` was enforced as a denylist naming only
    ``operator_maintained_approximate``, so five safety counters classified
    ``zero_because_the_activity_has_never_occurred`` satisfied a rule whose
    message said safety counters "require machine evidence, not recollection".
    They do not carry machine evidence. The class text claimed "a committed
    state block records" the fact, and nothing read that block.

    Renaming the class would have left it resting on nothing, so it is bound to
    the flags it appeals to instead. The class is still documented as a record
    assertion rather than promoted to evidence.

    Audit F's third closure review (F-10) then found the bindings themselves
    semantically wrong: the four ``formal_v2_evaluation_access`` and
    ``parser_execution`` counters were checked against
    ``retired_v1_state.formal_evaluation_ever_run``, a flag recording the
    history of ``parser-v3-v1``. The counters describe the *successor* set, so
    the binding could hold while the fact it guaranteed had changed. Each
    counter is now bound to the block describing the same object, and this test
    exercises both blocks.
    """
    assert (
        "retired_v1_repair_access.labels_opened_for_scoring"
        in ledger_module._NEVER_OCCURRED_STATE_BINDINGS
    )
    assert ledger_module._NEVER_OCCURRED_STATE_BINDINGS[
        "formal_v2_evaluation_access.sealed_input_semantic_reads"
    ] == ("successor_set_state", "exists", False)
    assert ledger_module._NEVER_OCCURRED_STATE_BINDINGS[
        "parser_execution.comparator_predictions_generated"
    ] == ("successor_set_state", "formal_evaluation_ordinal", 0)

    # The two halves of the record must now fail together rather than drift.
    # A successor set springing into existence falsifies the claim that its
    # sealed inputs were never read.
    flipped = copy.deepcopy(ledger)
    flipped["successor_set_state"]["exists"] = True
    with pytest.raises(LedgerError, match="the same history"):
        ledger_module._assert_never_occurred_agrees_with_state(flipped)

    # An ordered formal evaluation falsifies the claim that no label was opened
    # to score one and no comparator ran alongside it.
    ordered = copy.deepcopy(ledger)
    ordered["successor_set_state"]["formal_evaluation_ordinal"] = 1
    with pytest.raises(LedgerError, match="the same history"):
        ledger_module._assert_never_occurred_agrees_with_state(ordered)

    # The retired-v1 counter remains bound to the retired-v1 block.
    raised = copy.deepcopy(ledger)
    raised["retired_v1_state"]["labels_opened_for_scoring"] = 3
    with pytest.raises(LedgerError, match="the same history"):
        ledger_module._assert_never_occurred_agrees_with_state(raised)

    # A counter cannot be swept into the class to avoid a stronger one unless a
    # state flag is registered for it, which is a deliberate, reviewable edit.
    moved = copy.deepcopy(ledger)
    moved["counter_provenance"]["zero_because_the_activity_has_never_occurred"][
        "counters"
    ].append("azure.data_plane_writes")
    moved["counter_provenance"]["receipt_derived_exact"]["counters"].remove(
        "azure.data_plane_writes"
    )
    with pytest.raises(LedgerError, match="no state flag is registered"):
        ledger_module._assert_never_occurred_agrees_with_state(moved)

    # And the class is described as what it is, not as machine evidence.
    note = ledger_module.COUNTER_PROVENANCE_CLASS_MEANING[
        "zero_because_the_activity_has_never_occurred"
    ]
    assert "record assertion" in note


def test_a_citation_cannot_escape_the_repository_root(ledger):
    """Audit E (E-22). The docstring claimed confinement the code did not do.

    ``(root / candidate).is_file()`` follows ``..``, so ``../package.json`` and
    ``docs/../../package.json`` resolved to real files outside the repository
    and were accepted as evidence citations.
    """
    for escaping in (
        "../package.json",
        "docs/../../package.json",
        "../../package.json",
    ):
        assert ledger_module._cited_paths_that_exist(escaping) == []

    # The control: a real in-repository path is still accepted, so the refusals
    # above are attributable to the escape and not to the check being inert.
    assert ledger_module._cited_paths_that_exist(
        "docs/phase1_2h_execution_access_ledger.json"
    ) == ["docs/phase1_2h_execution_access_ledger.json"]

    mutated = copy.deepcopy(ledger)
    parts = mutated["counter_provenance"]["composite_of_separately_evidenced_parts"][
        "parts"
    ]["retired_v1_repair_access.byte_only_integrity_verifications"]
    parts[1] = dict(parts[1], evidence="cited at ../package.json")
    with pytest.raises(LedgerError):
        validate_ledger(mutated)


def test_f09_citability_fails_closed_when_the_repository_is_absent(
    ledger, monkeypatch, tmp_path
):
    """Audit F (F-09): the missing-checkout branch reopened the shape-only hole.

    ``_cited_paths_that_exist`` degraded to ``_CITATION_PATTERN`` whenever
    ``root/"docs"`` was not a directory, so a ledger validated from an installed
    package accepted ``docs/does-not-exist.json`` again --- the weaker check
    replaced the stronger one exactly where nothing could notice. It now returns
    nothing, and the callers refuse.

    The branch is reached by pointing the module's ``__file__``-derived root at
    an empty directory, which is what an installed package without a checkout
    looks like.
    """
    real = ledger_module._cited_paths_that_exist(
        "supported by docs/phase1_2h_execution_access_ledger.json"
    )
    assert real == ["docs/phase1_2h_execution_access_ledger.json"]

    monkeypatch.setattr(
        ledger_module, "__file__", str(tmp_path / "pkg" / "mod" / "x.py")
    )
    assert (
        ledger_module._cited_paths_that_exist(
            "supported by docs/phase1_2h_execution_access_ledger.json"
        )
        == []
    )
    with pytest.raises(LedgerError, match="cite"):
        ledger_module._assert_evidence_is_citable(
            "receipt_derived_exact",
            "supported by docs/phase1_2h_execution_access_ledger.json",
        )


def test_f09_a_zero_counter_cannot_be_laundered_through_a_composite(ledger):
    """Audit F (F-09): two zero addends citing real files satisfied the shape.

    The composite class required at least two addends, each with a non-negative
    amount and a distinct citable evidence string, summing to the counter. A
    zero safety counter met all of that with ``0 + 0`` and two unrelated
    committed documents --- so the strongest-looking provenance class was
    reachable for a number nothing had measured.

    Two rules close it independently: an addend must be positive, and a counter
    whose value is zero may not be classified as a composite at all. A zero is
    not a sum of evidenced activity, and it has classes of its own that say why
    it is zero.
    """
    mutated = copy.deepcopy(ledger)
    provenance = mutated["counter_provenance"]
    path = "azure.data_plane_writes"
    for class_name in ledger_module.COUNTER_PROVENANCE_CLASSES:
        entry = provenance.get(class_name)
        if isinstance(entry, dict) and path in entry.get("counters", []):
            entry["counters"].remove(path)
    composite = provenance["composite_of_separately_evidenced_parts"]
    composite["counters"].append(path)
    composite.setdefault("parts", {})[path] = [
        {
            "amount": 0,
            "evidence": "no write in docs/thread_handoff.md",
        },
        {
            "amount": 0,
            "evidence": "no write in reports/current_status.md",
        },
    ]
    with pytest.raises(LedgerError, match="positive integer"):
        validate_ledger(mutated)

    # And with the amount rule satisfied by construction, the zero-value rule
    # still refuses it: 1 + -1 is not expressible, so the check is exercised
    # through the direct validator with a counter forced to zero.
    forced = copy.deepcopy(mutated)
    forced["counter_provenance"]["composite_of_separately_evidenced_parts"]["parts"][
        path
    ] = [
        {"amount": 1, "evidence": "cited in docs/thread_handoff.md"},
        {"amount": 1, "evidence": "cited in reports/current_status.md"},
    ]
    with pytest.raises(LedgerError, match="sum to 2"):
        validate_ledger(forced)


def test_f13_the_byte_only_constant_is_an_equality_not_a_floor(ledger):
    """Audit F (F-13): the constant's comment contradicted the rule reading it.

    The comment called ``BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE`` a floor a later
    round could exceed without moving the constant. ``_validate_status_agreement``
    pins the counter to it exactly, because E-18 showed a floor leaves the
    overstating direction free. This test fixes which of the two is the rule.
    """
    source = (
        Path(ledger_module.__file__).read_text(encoding="utf-8")
    )
    marker = "BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE: int = 14"
    comment = source[: source.index(marker)].rsplit("\n\n", 1)[-1]
    assert "floor" not in comment.split("owns the downward")[0].replace(
        "is a floor", ""
    ) or "was wrong" in comment

    raised = copy.deepcopy(ledger)
    raised["live_counters"]["retired_v1_repair_access"][
        "byte_only_integrity_verifications"
    ] = 15
    with pytest.raises(LedgerError, match="must equal 14"):
        ledger_module._validate_status_agreement(raised, raised["status"])


def test_f14_provenance_cannot_be_restated_across_succession(ledger):
    """Audit F (F-14): succession compared counters and events and nothing else.

    A successor could keep every value and every event while moving a counter
    from ``operator_asserted_unverified`` to ``receipt_derived_exact``. The
    number would not change; the reader's warrant for it would, upward, with
    nothing recorded. Audit F judged this non-blocking while no successor
    exists and said it must close before any round relies on succession.

    Provenance is now immutable across succession unless an appended event
    names the counter and both classes.
    """
    assert ledger_module.assert_monotonic_succession(ledger, copy.deepcopy(ledger)) is None

    silent = copy.deepcopy(ledger)
    provenance = silent["counter_provenance"]
    path = "azure.control_plane_reads"
    origin = "operator_maintained_approximate"
    assert path in provenance[origin]["counters"]
    provenance[origin]["counters"].remove(path)
    provenance["receipt_derived_exact"]["counters"].append(path)
    with pytest.raises(LedgerError, match="must be recorded, not applied"):
        ledger_module.assert_monotonic_succession(ledger, silent)

    # The same change is permitted when the successor appends an event that
    # names the counter and both classes, which is what makes it reviewable.
    recorded = copy.deepcopy(silent)
    corrected = next(
        event["sequence"]
        for event in reversed(recorded["events"])
        if event["kind"] != ledger_module.CORRECTION_EVENT_KIND
    )
    recorded["events"].append(
        {
            "sequence": len(recorded["events"]) + 1,
            "kind": ledger_module.CORRECTION_EVENT_KIND,
            "corrects": corrected,
            "role": "public-repository maintainer, offline",
            "private_content_read": False,
            "summary": (
                f"Reclassification of {path}. Its provenance moves from "
                f"{origin} to receipt_derived_exact. No counter value changes; "
                "this event exists so that the change in why the number should "
                "be believed is itself on the record."
            ),
        }
    )
    ledger_module.assert_monotonic_succession(ledger, recorded)

    # Dropping a classification is refused outright. The partition rule in
    # _validate_counter_provenance also refuses it, so the succession rule is
    # exercised directly to show it does not depend on that.
    dropped = copy.deepcopy(ledger)
    dropped["counter_provenance"][origin]["counters"].remove(path)
    with pytest.raises(LedgerError, match="lose its provenance"):
        ledger_module._assert_provenance_survives_succession(
            ledger, dropped, ledger_module._validate_events(dropped["events"])
        )
    with pytest.raises(LedgerError):
        ledger_module.assert_monotonic_succession(ledger, dropped)


def _correction(ledger: dict, sequence: int, summary: str) -> dict:
    """A well-formed correction event carrying ``summary``."""
    corrected = next(
        event["sequence"]
        for event in reversed(ledger["events"])
        if event["kind"] != ledger_module.CORRECTION_EVENT_KIND
    )
    return {
        "sequence": sequence,
        "kind": ledger_module.CORRECTION_EVENT_KIND,
        "corrects": corrected,
        "role": "public-repository maintainer, offline",
        "private_content_read": False,
        "summary": summary,
    }


def test_r5_three_housekeeping_events_cannot_authorise_a_reclassification(ledger):
    """Audit E (E-26) and Audit F (F-19): the F-14 rule was substring theatre.

    The first version joined every appended summary into one string and asked
    three independent questions of it. Three unrelated "housekeeping" events,
    each carrying one token, satisfied the rule while none described the change
    --- and the change they hid was an *upgrade*, from a record assertion to
    ``structurally_zero_by_source_analysis``, whose warrant is that the source
    cannot make the counter non-zero. Because that class is not a record
    assertion, walking this gate also detached the F-10 state binding: two
    independently remediated defects chained through one bypass.

    The question is now asked of one event at a time.
    """
    path = "parser_execution.comparator_predictions_generated"
    origin = "zero_because_the_activity_has_never_occurred"
    target = "structurally_zero_by_source_analysis"

    upgraded = copy.deepcopy(ledger)
    provenance = upgraded["counter_provenance"]
    assert path in provenance[origin]["counters"]
    provenance[origin]["counters"].remove(path)
    provenance[target]["counters"].append(path)

    split = copy.deepcopy(upgraded)
    base = len(split["events"])
    split["events"].extend(
        _correction(ledger, base + offset + 1, f"Housekeeping: glossary entry for {token}.")
        for offset, token in enumerate((path, origin, target))
    )
    with pytest.raises(LedgerError, match="no single appended event"):
        ledger_module._assert_provenance_survives_succession(
            ledger, split, ledger_module._validate_events(split["events"])
        )

    # A single event that names all three is still accepted, so the rule
    # narrowed rather than simply forbidding correction.
    together = copy.deepcopy(upgraded)
    together["events"].append(
        _correction(
            ledger,
            len(together["events"]) + 1,
            f"Reclassified {path} from {origin} to {target} after source analysis.",
        )
    )
    assert (
        ledger_module._assert_provenance_survives_succession(
            ledger, together, ledger_module._validate_events(together["events"])
        )
        is None
    )


def test_r5_the_succession_rule_is_a_co_occurrence_test_and_says_so(ledger):
    """The residual Audit F named is real, and is disclosed rather than closed.

    An event whose prose *denies* that any reclassification is authorised still
    satisfies the rule, because the rule tests for three strings in one summary
    and cannot read. That is a genuine limitation. It is recorded here as a
    characterisation test so no later reader mistakes the rule for a semantic
    check, and it is stated in the function's own docstring.
    """
    path = "parser_execution.comparator_predictions_generated"
    origin = "zero_because_the_activity_has_never_occurred"
    target = "structurally_zero_by_source_analysis"

    denying = copy.deepcopy(ledger)
    denying["counter_provenance"][origin]["counters"].remove(path)
    denying["counter_provenance"][target]["counters"].append(path)
    denying["events"].append(
        _correction(
            ledger,
            len(denying["events"]) + 1,
            f"No reclassification is authorized. Glossary only: {path}; {origin}; {target}.",
        )
    )
    assert (
        ledger_module._assert_provenance_survives_succession(
            ledger, denying, ledger_module._validate_events(denying["events"])
        )
        is None
    )

    doc = ledger_module._assert_provenance_survives_succession.__doc__ or ""
    assert "not a semantic check" in doc
    assert "co-occurrence" in doc


def test_r5_the_never_occurred_rule_pins_the_value_when_called_directly(ledger):
    """Audit F (F-17): the rule leaned on a rule elsewhere.

    Called alone with ``sealed_input_semantic_reads = 3`` and an unchanged
    ``successor_set_state``, this function did not object. Whole-ledger
    validation refused the ledger, but through the class-independent zero pin in
    ``_MUST_BE_ZERO_CLASSES`` --- so the guarantee a reader would attribute to
    this function was supplied by a different one.
    """
    tampered = copy.deepcopy(ledger)
    tampered["live_counters"]["formal_v2_evaluation_access"][
        "sealed_input_semantic_reads"
    ] = 3
    with pytest.raises(LedgerError, match="never occurred"):
        ledger_module._assert_never_occurred_agrees_with_state(tampered)


def test_r5_whole_ledger_validation_still_reports_the_parser_rule_first(ledger):
    """The F-17 pin must not displace the finding a reader needs first.

    A ledger recording a parser invocation has violated the prohibition on
    running a parser. That it also falsifies a provenance class is bookkeeping.
    The value pin is therefore suppressed in whole-ledger validation, where a
    late phase reports every class-versus-value failure, and active for a direct
    caller, which has no ordering to preserve.
    """
    tampered = copy.deepcopy(ledger)
    tampered["live_counters"]["parser_execution"][
        "comparator_predictions_generated"
    ] = 1
    with pytest.raises(LedgerError, match="no parser may"):
        validate_ledger(tampered)
