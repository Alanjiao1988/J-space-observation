"""Tests for the frozen Phase 1.0D semantic-review v2 instrument.

Two obligations, both prospective, both required before any provider call.

*Static*: the bank is exactly what the authority registered — 20 fixtures, four
per label, unique ids, four presented fields each, the exact canonical hash, no
target leakage, and no silent reuse of the retired v1 bank.

*Executable*: the rubric's ordered rules, applied in order by a reader, produce
the registered expected label for every fixture.  That is the check the v1 round
did not have.  v1 froze a rubric whose rule 3 selected the last complete literal
surface and a fixture whose expected label followed prose after that surface;
the contradiction was hashed, verified inside an image and never once executed.

The reference reader below deliberately refuses to run on anything that is not
one of the 20 registered synthetic fixtures.  Under ``DR-01`` an automatic
parser may triage but may never produce a final label, so this must never grow
into something that could read a target output — the whitelist makes that a
structural property rather than a promise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jspace_observation.semantic_review_v2 import addendum_v2 as contract

REPO_ROOT = Path(__file__).resolve().parent.parent

RUBRIC_SHA256 = "91f687087fbd56cb07369da7a4c28beddb49d822f2d6fa1832cb3849a26f60e3"
FIXTURE_BANK_SHA256 = "41adb246ec36d5ac7b16f5144c466351b93abe8b3f56dc811e58a789b197e75f"
ADDENDUM_SHA256 = "20e5f30455f90a95c07e05e080e51443511c957e09d4ce97a42bd118bd9268e4"
AUTHORITY_SHA256 = "7b93c90a299ff4e77b83d4633624053f8ce53afcd04279ca3050c5ab14428e19"

V1_ADDENDUM_SHA256 = "582640de645030daf957fbc3e5c7947008b78d1596b674687a73f20ba749bdc3"
V1_RUBRIC_SHA256 = "a0d5b22bd6d4ef1012db676ff3431c3d2e6825f1ec4ade1a7c7801817ba8765d"

SURFACE = re.compile(r"^.*?Final answer:[ \t]*(?P<span>\S.*?)[ \t]*$", re.MULTILINE)


@pytest.fixture(scope="module")
def book():
    return contract.load_addendum_v2(REPO_ROOT)


@pytest.fixture(scope="module")
def fixtures(book):
    return list(book.document["smoke_fixtures"])


# --------------------------------------------------------------------------
# static obligations
# --------------------------------------------------------------------------


def test_the_rubric_bytes_are_the_frozen_bytes():
    path = REPO_ROOT / contract.RUBRIC_PATH
    assert contract.v1.sha256_file(path) == RUBRIC_SHA256


def test_the_addendum_and_authority_bytes_are_the_frozen_bytes(book):
    assert book.sha256 == ADDENDUM_SHA256
    assert book.rubric_sha256 == RUBRIC_SHA256
    assert book.document["authority_prompt_sha256"] == AUTHORITY_SHA256


def test_the_bank_holds_exactly_twenty_unique_fixtures(fixtures):
    assert len(fixtures) == 20
    assert len({f["fixture_id"] for f in fixtures}) == 20


def test_the_bank_is_balanced_at_four_fixtures_per_label(fixtures):
    counts: dict[str, int] = {}
    for fixture in fixtures:
        counts[fixture["expected_label"]] = counts.get(fixture["expected_label"], 0) + 1
    assert counts == {label: 4 for label in contract.LABELS}


def test_the_bank_reproduces_its_canonical_hash(book, fixtures):
    assert contract.fixture_bank_sha256(fixtures) == FIXTURE_BANK_SHA256
    assert (
        book.document["conformance_bank"]["fixture_bank_sha256"] == FIXTURE_BANK_SHA256
    )


def test_every_row_carries_exactly_the_four_presented_fields(fixtures):
    for fixture in fixtures:
        assert tuple(sorted(fixture["row"])) == tuple(sorted(contract.PRESENTED_FIELDS))


def test_no_selected_target_task_id_appears_in_the_bank(fixtures):
    snapshot = json.loads(
        (REPO_ROOT / "docs/phase1_0d_protocol_snapshot.json").read_text(encoding="utf-8")
    )
    task_ids = snapshot["snapshot"]["selection"]["task_ids"]
    assert len(task_ids) == 300
    contract.assert_no_target_leakage(fixtures, task_ids)


def test_the_retired_v1_bank_is_not_reused(fixtures):
    ids = {f["fixture_id"] for f in fixtures}
    assert not ids & contract.RETIRED_V1_FIXTURE_IDS
    haystack = contract.canonical_bank(fixtures)
    assert "Both of those answers are equally my final commitment" not in haystack


def test_the_two_last_surface_fixtures_carry_the_registered_expectations(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    correct = by_id["v2_correct_last_surface_wins"]
    incorrect = by_id["v2_incorrect_last_surface_wins"]
    assert correct["expected_label"] == "correct"
    assert incorrect["expected_label"] == "incorrect"
    # The trap is only a trap if the two point in opposite directions: a
    # reviewer cannot satisfy both by guessing one label.
    assert correct["row"]["output_text"].rstrip().endswith(
        "the registered surface above remains my final answer."
    )
    assert incorrect["row"]["output_text"].rstrip().endswith(
        "Both candidate lines seem equally plausible to me."
    )


def test_the_v1_instrument_is_bound_as_history_and_unchanged(book):
    parents = book.document["historical_parents"]
    assert parents["v1_addendum_sha256"] == V1_ADDENDUM_SHA256
    assert parents["v1_rubric_sha256"] == V1_RUBRIC_SHA256
    assert (
        contract.v1.sha256_file(REPO_ROOT / parents["v1_addendum"]) == V1_ADDENDUM_SHA256
    )
    assert contract.v1.sha256_file(REPO_ROOT / parents["v1_rubric"]) == V1_RUBRIC_SHA256
    assert parents["v1_final_state"] == "BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION"


def test_the_pass_criterion_is_sixty_of_sixty_with_no_tolerance(book):
    rules = book.document["smoke_rules"]
    assert rules["pass_criterion"] == {
        "valid_responses": 60,
        "schema_valid_one_key_labels": 60,
        "visible_completions_within_cap": 60,
        "exact_expected_label_matches": 60,
        "transport_failures_after_registered_retry": 0,
        "malformed_responses": 0,
        "semantic_retries": 0,
    }
    assert rules["no_majority_rule"] is True
    assert "no RV3" in rules["one_round_ceiling"]
    assert (
        book.document["terminal_states"]["instrument_unqualified"]
        == "CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_INSTRUMENT_UNQUALIFIED"
    )


def test_the_panel_and_request_profiles_are_the_live_proven_ones(book):
    expected = {
        "primary": ("gpt-5-6-sol-global", "gpt-5.6-sol", "2026-07-09"),
        "secondary": ("mistral-large-3-global", "Mistral-Large-3", "1"),
        "third": ("deepseek-v4-pro-global", "DeepSeek-V4-Pro", "2026-04-23"),
    }
    v1_doc = json.loads(
        (REPO_ROOT / "docs/phase1_0d_semantic_review_addendum.json").read_text(
            encoding="utf-8"
        )
    )
    for role, (deployment, model, version) in expected.items():
        profile = book.roles[role]
        assert (profile.deployment, profile.model, profile.model_version) == (
            deployment,
            model,
            version,
        )
        assert profile.region == "eastus2"
        assert profile.path_candidates == ("/openai/v1/chat/completions",)
        assert profile.api_version_candidates == ("",)
        assert profile.max_visible_output_tokens == 64
        # Section 7: reuse the v1 request bodies exactly.
        assert profile.request == v1_doc["roles"][role]["request"]


def test_the_target_experiment_bindings_are_unchanged(book):
    snapshot = json.loads(
        (REPO_ROOT / "docs/phase1_0d_protocol_snapshot.json").read_text(encoding="utf-8")
    )
    assert (
        book.document["base_protocol_sha256"]
        == "25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8"
    )
    assert (
        book.document["task_ids_sha256"] == snapshot["snapshot"]["selection"]["task_ids_sha256"]
    )
    assert (
        book.document["generation_image_digest"]
        == "sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
    )


def test_the_independence_loss_is_disclosed_in_the_frozen_bytes(book):
    bank = book.document["conformance_bank"]
    assert "after the v1 responses were observed" in bank["authored"]
    assert "instrument-calibration independence" in bank["independence_disclosure"]
    assert "Target-data independence is intact" in bank["independence_disclosure"]
    boundary = book.document["claim_boundary"]
    for forbidden in ("headroom", "hidden reasoning", "J-lens validity", "J-space"):
        assert forbidden in boundary


def test_the_gate_persists_its_receipt_even_on_mismatch(book):
    persistence = book.document["evidence_persistence"]
    assert persistence["create_only"] is True
    assert persistence["overwrite_forbidden"] is True
    assert persistence["manifest_written_last"] is True
    assert persistence["upload_on_mismatch"] is True
    for field in (
        "request_body_sha256",
        "response_body_sha256",
        "observed_label",
        "match",
        "finish_reason",
        "visible_completion_tokens",
        "latency_seconds",
        "retry_count",
    ):
        assert field in persistence["per_call_receipt_fields"]


def test_the_smoke_stage_cannot_reach_target_storage(book):
    isolation = book.document["target_isolation"]
    assert isolation["smoke_receives_generation_pack_prefix"] is False
    assert isolation["smoke_may_list_or_read_target_storage"] is False


# --------------------------------------------------------------------------
# executable rubric ordering
# --------------------------------------------------------------------------


def _complete_surfaces(output_text: str) -> list[str]:
    """Rule 2a: occurrences whose own line carries a non-empty answer span."""

    return [match.group("span") for match in SURFACE.finditer(output_text)]


def _conflicting(span: str) -> bool:
    """Rule 2b: the selected surface itself offers co-equal alternatives."""

    lowered = span.lower()
    return " or " in lowered or lowered.startswith("either ")


def _reference_label(fixture_id: str, row: dict[str, str]) -> str:
    """Apply the v2 rubric's rules in their stated order.

    Restricted to the 20 registered synthetic fixtures on purpose: under DR-01
    no automatic reader may ever produce a final label for a target row, so this
    is made incapable of seeing one rather than merely discouraged from it.
    """

    if fixture_id not in _REGISTERED_IDS:
        raise AssertionError(
            f"the reference reader is fixture-only and refuses {fixture_id!r}"
        )

    question = row["question"]
    reference = row["registered_answer"]
    output_text = row["output_text"]

    # 1. invalid
    if not question.strip() or not reference.strip():
        return "invalid"

    # 2. select the commitment
    surfaces = _complete_surfaces(output_text)
    if surfaces:
        selected = surfaces[-1]  # 2a: the last complete surface, prose notwithstanding
        if _conflicting(selected):  # 2b
            return "unresolved"  # 4
        # 5 / 6, on the sole selected commitment
        return "correct" if _equivalent(selected, reference) else "incorrect"

    # 2c: no complete surface, so read the whole output for final commitments
    commitments = _whole_output_commitments(output_text)
    if not commitments:
        return "no_answer"  # 3
    if len(commitments) > 1:
        return "unresolved"  # 4
    raise AssertionError(  # pragma: no cover - unreachable for the frozen bank
        "no registered fixture asserts exactly one final commitment without a "
        "complete surface, so this reader has no honest way to compare one"
    )


def _equivalent(span: str, reference: str) -> bool:
    """Rule 5: harmless case/whitespace variation and exact numeric equality."""

    left = span.strip().rstrip(".").strip()
    right = reference.strip()
    if left.casefold() == right.casefold():
        return True
    try:
        return float(left) == float(right)
    except ValueError:
        return False


def _whole_output_commitments(output_text: str) -> list[str]:
    """Rule 2c, for the registered no-surface fixtures only.

    "Mere possibilities considered during reasoning are not commitments", so an
    output is only read as committing when it says so.  Nothing in the bank
    asserts exactly one final commitment without a literal surface, which is
    why the single-commitment branch above never fires here; it is kept so the
    ordering is complete rather than tuned to the bank.
    """

    lowered = output_text.strip().lower()
    if not lowered:
        return []
    explicit = lowered.count("final committed answer")
    if explicit:
        return ["commitment"] * explicit
    if "co-equal final answers" in lowered:
        return ["commitment", "commitment"]
    return []


_REGISTERED_IDS = frozenset(
    {
        "v2_correct_exact",
        "v2_correct_case_equivalent",
        "v2_correct_numeric_equivalent",
        "v2_correct_last_surface_wins",
        "v2_incorrect_exact",
        "v2_incorrect_entity",
        "v2_incorrect_value",
        "v2_incorrect_last_surface_wins",
        "v2_no_answer_empty",
        "v2_no_answer_refusal",
        "v2_no_answer_reasoning_only",
        "v2_no_answer_empty_surface",
        "v2_invalid_empty_question",
        "v2_invalid_empty_reference",
        "v2_invalid_whitespace_question",
        "v2_invalid_whitespace_reference",
        "v2_unresolved_coequal_commitments",
        "v2_unresolved_surface_alternatives",
        "v2_unresolved_surface_disjunction",
        "v2_unresolved_no_surface_conflict",
    }
)


def test_the_registered_id_whitelist_matches_the_frozen_bank(fixtures):
    assert {f["fixture_id"] for f in fixtures} == set(_REGISTERED_IDS)


def test_the_reference_reader_refuses_anything_outside_the_bank():
    with pytest.raises(AssertionError, match="fixture-only"):
        _reference_label(
            "phase1_0d_row_0001",
            {
                "record_id": "phase1_0d_row_0001",
                "question": "q",
                "registered_answer": "a",
                "output_text": "Final answer: a",
            },
        )


def test_the_ordered_rubric_reproduces_every_registered_expectation(fixtures):
    """The check v1 lacked: execute the ordering against the whole bank."""

    disagreements = []
    for fixture in fixtures:
        observed = _reference_label(fixture["fixture_id"], fixture["row"])
        if observed != fixture["expected_label"]:
            disagreements.append(
                f"{fixture['fixture_id']}: {observed} != {fixture['expected_label']}"
            )
    assert not disagreements, disagreements


def test_the_last_complete_surface_wins(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    row = by_id["v2_correct_last_surface_wins"]["row"]
    assert _complete_surfaces(row["output_text"]) == ["7", "6"]
    assert _reference_label("v2_correct_last_surface_wins", row) == "correct"


def test_prose_after_the_selected_surface_cannot_override_it(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    row = by_id["v2_incorrect_last_surface_wins"]["row"]
    assert row["output_text"].rstrip().endswith("equally plausible to me.")
    # Prose calls the two lines equally plausible; rule 2a has already selected
    # the last one, so rule 4 does not fire and the label is a plain miss.
    assert _reference_label("v2_incorrect_last_surface_wins", row) == "incorrect"
    # This is exactly the shape that broke v1, with the expectation now
    # following the rubric's own ordering.
    v1_shaped = row["output_text"]
    assert v1_shaped.count("Final answer:") == 2


def test_incompatible_alternatives_inside_the_selected_surface_are_unresolved(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    for fixture_id in ("v2_unresolved_surface_alternatives", "v2_unresolved_surface_disjunction"):
        row = by_id[fixture_id]["row"]
        assert len(_complete_surfaces(row["output_text"])) == 1
        assert _reference_label(fixture_id, row) == "unresolved"


def test_coequal_commitments_without_a_literal_surface_are_unresolved(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    for fixture_id in (
        "v2_unresolved_coequal_commitments",
        "v2_unresolved_no_surface_conflict",
    ):
        row = by_id[fixture_id]["row"]
        assert _complete_surfaces(row["output_text"]) == []
        assert _reference_label(fixture_id, row) == "unresolved"


def test_explored_alternatives_without_commitment_are_no_answer(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    for fixture_id in (
        "v2_no_answer_empty",
        "v2_no_answer_refusal",
        "v2_no_answer_reasoning_only",
        "v2_no_answer_empty_surface",
    ):
        row = by_id[fixture_id]["row"]
        assert _reference_label(fixture_id, row) == "no_answer"


def test_an_incomplete_surface_is_not_a_commitment(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    row = by_id["v2_no_answer_empty_surface"]["row"]
    assert row["output_text"].rstrip().endswith("Final answer:")
    assert _complete_surfaces(row["output_text"]) == []


def test_empty_or_whitespace_record_fields_are_invalid(fixtures):
    by_id = {f["fixture_id"]: f for f in fixtures}
    for fixture_id in (
        "v2_invalid_empty_question",
        "v2_invalid_empty_reference",
        "v2_invalid_whitespace_question",
        "v2_invalid_whitespace_reference",
    ):
        row = by_id[fixture_id]["row"]
        # invalid is decided by the record, never by the output being wrong
        assert row["output_text"].startswith("Final answer:")
        assert _reference_label(fixture_id, row) == "invalid"


def test_the_v1_fixture_would_have_failed_this_check():
    """The regression that justifies the whole method (M-16).

    The v1 rubric selected the last complete surface too, so executing its
    ordering against its own fixture would have produced ``incorrect`` and the
    contradiction would have been caught before any provider call.
    """

    v1_doc = json.loads(
        (REPO_ROOT / "docs/phase1_0d_semantic_review_addendum.json").read_text(
            encoding="utf-8"
        )
    )
    fixture = next(
        f for f in v1_doc["smoke_fixtures"] if f["fixture_id"] == "smoke_unresolved"
    )
    surfaces = _complete_surfaces(fixture["row"]["output_text"])
    assert surfaces == ["4", "5"]
    assert surfaces[-1] != fixture["row"]["registered_answer"]
    assert fixture["expected_label"] == "unresolved"


# --------------------------------------------------------------------------
# loader refusals
# --------------------------------------------------------------------------


def _write_variant(tmp_path: Path, mutate) -> Path:
    document = json.loads(
        (REPO_ROOT / contract.ADDENDUM_PATH).read_text(encoding="utf-8")
    )
    mutate(document)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / contract.ADDENDUM_PATH).write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (tmp_path / contract.RUBRIC_PATH).write_bytes(
        (REPO_ROOT / contract.RUBRIC_PATH).read_bytes()
    )
    return tmp_path


def test_the_loader_refuses_a_bank_short_one_fixture(tmp_path):
    root = _write_variant(tmp_path, lambda d: d["smoke_fixtures"].pop())
    with pytest.raises(contract.AddendumError, match="19 fixtures"):
        contract.load_addendum_v2(root)


def test_the_loader_refuses_a_relabelled_fixture(tmp_path):
    def relabel(document):
        document["smoke_fixtures"][0]["expected_label"] = "incorrect"

    root = _write_variant(tmp_path, relabel)
    with pytest.raises(contract.AddendumError, match="not balanced|hashes to"):
        contract.load_addendum_v2(root)


def test_the_loader_refuses_a_reused_v1_fixture(tmp_path):
    def reuse(document):
        document["smoke_fixtures"][0]["fixture_id"] = "smoke_unresolved"
        document["smoke_fixtures"][0]["row"]["record_id"] = "smoke_unresolved"

    root = _write_variant(tmp_path, reuse)
    with pytest.raises(contract.AddendumError, match="retired v1 bank"):
        contract.load_addendum_v2(root)


def test_the_loader_refuses_a_lowered_pass_criterion(tmp_path):
    def lower(document):
        document["smoke_rules"]["pass_criterion"]["exact_expected_label_matches"] = 59

    root = _write_variant(tmp_path, lower)
    with pytest.raises(contract.AddendumError, match="60/60"):
        contract.load_addendum_v2(root)


def test_the_loader_refuses_an_added_majority_rule(tmp_path):
    def majority(document):
        document["smoke_rules"]["no_majority_rule"] = False

    root = _write_variant(tmp_path, majority)
    with pytest.raises(contract.AddendumError, match="majority"):
        contract.load_addendum_v2(root)


def test_the_loader_refuses_a_row_carrying_a_fifth_field(tmp_path):
    def leak(document):
        document["smoke_fixtures"][0]["row"]["task_family"] = "synthetic_relation"

    root = _write_variant(tmp_path, leak)
    with pytest.raises(contract.AddendumError, match="four presented fields"):
        contract.load_addendum_v2(root)


def test_the_leakage_guard_catches_a_quoted_task_id(fixtures):
    smuggled = [dict(f) for f in fixtures]
    smuggled[0] = {
        **smuggled[0],
        "row": {**smuggled[0]["row"], "question": "see task pg2h_hard_0007"},
    }
    with pytest.raises(contract.AddendumError, match="target task ids"):
        contract.assert_no_target_leakage(smuggled, ["pg2h_hard_0007"])
