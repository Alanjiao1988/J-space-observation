"""Tests for the Phase 1.2E parser-v3 evaluation ontology repair tooling.

Every fixture here is public and synthetic. No test reads a sealed blob, a
locked input, a locked label, or any git-ignored curator file, and no test runs
a parser. The suite is organised around the Phase 1.2D defect labels: each of
``H1``-``H9`` has a negative regression fixture, and each of ``N1``-``N6`` has a
transformation test.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from jspace_observation import evaluator_validation as frozen  # noqa: E402
from jspace_observation.parser_v3_repair_contract import (  # noqa: E402
    COUNT_KINDS,
    ContractError,
    SetCounts,
    build_set_facts,
    SetSource,
    FACTS_SCHEMA_VERSION,
    verify_facts_integrity,
    set_content_digest,
    seal_facts,
    agreement_findings,
    check_agreement,
    check_contract,
    compile_contract,
    render_contract,
    validate_policy,
    write_contract,
)
from jspace_observation.parser_v3_repair_normalization import (  # noqa: E402
    NORMALIZATION_RULES,
    NormalizationError,
    QuarantineReason,
    apply_n1_literal_only_spans,
    apply_n2_canonical_reference,
    apply_n3_output_text,
    apply_n4_last_number_distractor,
    apply_n5_secondary_tags,
    apply_n6_candidate_answers,
    normalize_record,
    normalize_set,
    assert_parser_free_source,
    raw_typed_decision,
)
from jspace_observation.parser_v3_repair_ontology import (  # noqa: E402
    RESEARCH_ONLY_TYPED_DECISION_CLASSES,
    SPAN_CONVENTION,
    STRATUM_PRESENCE,
    TRUTH_TABLE,
    TRUTH_TABLE_ID,
    OntologyError,
    derive_typed_decision,
    typed_decision_class,
    validate_ontology_record,
    validate_ontology_set,
)

POLICY_PATH = ROOT / "docs" / "phase1_parser_v3_v2_evaluation_policy.json"
REPAIR_MODULES = (
    ROOT / "src" / "jspace_observation" / "parser_v3_repair_ontology.py",
    ROOT / "src" / "jspace_observation" / "parser_v3_repair_normalization.py",
    ROOT / "src" / "jspace_observation" / "parser_v3_repair_contract.py",
    ROOT / "scripts" / "parser_v3_repair_cli.py",
)

#: LF-normalised SHA-256 of every artifact Phase 1.2E must not modify.
#: Recorded from ``origin/main`` at commit 45a18f4 before any 1.2E edit.
PROTECTED_DIGESTS = {
    "src/jspace_observation/eval_parsing_v3.py": "dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e",
    "src/jspace_observation/eval_parsing_v2.py": "fe02781545e26c2f97d1731e985d081a2f1468950bec4d88700647849243d182",
    "src/jspace_observation/eval_parsing.py": "4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e",
    "src/jspace_observation/evaluator_validation.py": "63eb1c7d8b229dddafdd3d54a0d62bb415d76ae8dd5aab220bd91ff054f08344",
    "docs/phase1_parser_v2_protocol.md": "417d9ff5d27b17ce588b7713a1b1072fb32ef21a03fd135e4e339719db28866b",
    "docs/phase1_parser_v2_acceptance_gates.json": "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988",
    "docs/phase1_evaluator_validation_set.md": "d019c446393bc60dc524178c2a91018ceb8f04f881dcc80018f0282b0919f3f8",
    "docs/phase1_parser_v3_acceptance_gates.json": "2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7",
    "evaluator_sets/parser_v3_v1/manifests/set_manifest.json": "13f021abd7a052b3b7153b6a0af8ccc13f3bced4b4c280dd3abaa7ab65b949f3",
    "evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json": "ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d",
    "evaluator_sets/parser_v3_v1/manifests/labels_manifest.json": "ab32c559cd62c72d059fc2527e17d3e806d5ddc9227f8bd8f8f6b0295d7e67a2",
}


def _lf_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canon(value: str) -> str:
    return frozen.normalize_rational_literal(value)


# ---------------------------------------------------------------------------
# Synthetic set construction
# ---------------------------------------------------------------------------

_CLEAN = ("S01", "S02", "S03", "S12")

_S12_SURFACES = (
    "+07.50",
    "0.25",
    "-3.0",
    "4/8",
    "+1.5",
    "2.50",
    "-0.75",
    "6/9",
    "08.0",
    "-2.25",
)


def _span(output_text: str, literal: str, kind: str, disposition: str, *, occurrence: int = -1) -> dict:
    if occurrence < 0:
        start = output_text.rindex(literal)
    else:
        start = output_text.index(literal)
    return {
        "start": start,
        "end": start + len(literal),
        "text": literal,
        "kind": kind,
        "normalized_answer": _canon(literal),
        "disposition": disposition,
    }


_NO_ANSWER_FAILURE = {
    "S07": ("truncated_before_final_answer",),
    "S08": ("no_reliable_answer",),
    "S10": ("malformed_without_reliable_answer",),
}


def _base(case_id: str, stratum: str, presence: str, quality: str, strategy: str) -> dict:
    parse_valid = presence in ("present", "ambiguous")
    return {
        "case_id": case_id,
        "stratum": stratum,
        "expected_answer_presence": presence,
        "expected_output_quality": quality,
        "expected_extraction_strategy": strategy,
        "expected_parse_valid": parse_valid,
        "expected_parse_ambiguous": presence == "ambiguous",
        "expected_parsed_answer": None,
        "expected_candidate_answers": [],
        "expected_evidence_spans": [],
        "expected_failure_reasons": (
            [] if parse_valid else list(_NO_ANSWER_FAILURE.get(stratum, ("no_reliable_answer",)))
        ),
        "expected_format_warnings": [],
        "registered_reference_answer": "1",
        "expected_correctness": False,
        "critical_case": stratum not in _CLEAN,
    }


def _present(case_id, stratum, text, literal, kind, quality, *, correct=True) -> tuple[dict, str]:
    record = _base(case_id, stratum, "present", quality, kind_to_strategy(kind))
    span = _span(text, literal, kind, "selected")
    record["expected_parsed_answer"] = span["normalized_answer"]
    record["expected_candidate_answers"] = [span["normalized_answer"]]
    record["expected_evidence_spans"] = [span]
    record["registered_reference_answer"] = (
        span["normalized_answer"] if correct else _canon("991")
    )
    record["expected_correctness"] = correct
    return record, text


def kind_to_strategy(kind: str) -> str:
    return {
        "boxed": "boxed_answer",
        "explicit_final_marker": "explicit_final_marker",
        "explicit_answer_marker": "explicit_answer_marker",
        "terminal_equation": "terminal_equation",
        "single_candidate": "single_candidate",
    }[kind]


def build_synthetic_set() -> tuple[list[dict], dict[str, str]]:
    """A complete, valid, 120-case, 12-stratum synthetic set."""
    records: list[dict] = []
    texts: dict[str, str] = {}

    def add(record: dict, text: str) -> None:
        records.append(record)
        texts[record["case_id"]] = text

    for i in range(10):
        v = str(101 + i)
        cid = f"SYN-S01-{i:02d}"
        text = f"Reasoning proceeds carefully. \\boxed{{{v}}}"
        add(*_present(cid, "S01", text, v, "boxed", "complete"))

        v = str(201 + i)
        cid = f"SYN-S02-{i:02d}"
        text = f"Reasoning proceeds carefully. Final answer: {v}"
        add(*_present(cid, "S02", text, v, "explicit_final_marker", "complete"))

        v = str(301 + i)
        cid = f"SYN-S03-{i:02d}"
        text = f"Reasoning proceeds carefully. x = {v}"
        add(*_present(cid, "S03", text, v, "terminal_equation", "complete"))

        v = str(401 + i)
        cid = f"SYN-S04-{i:02d}"
        text = (
            f"Step one gives {410 + i} , step two gives {420 + i} . "
            f"Final answer: {v}"
        )
        add(
            *_present(
                cid,
                "S04",
                text,
                v,
                "explicit_final_marker",
                "complete",
                correct=(i != 9),
            )
        )

        v = str(501 + i)
        cid = f"SYN-S05-{i:02d}"
        text = f"Final answer: {v} , and the remaining derivation follows below."
        add(*_present(cid, "S05", text, v, "explicit_final_marker", "complete"))

        v = str(601 + i)
        cid = f"SYN-S06-{i:02d}"
        text = f"Final answer: {v} ( sanity check {660 + i} )"
        add(*_present(cid, "S06", text, v, "explicit_final_marker", "complete"))

        cid = f"SYN-S07-{i:02d}"
        text = "The final answer is"
        record = _base(cid, "S07", "no_answer", "truncated", "none")
        add(record, text)

        cid = f"SYN-S08-{i:02d}"
        text = "No determinate answer can be given here."
        record = _base(cid, "S08", "no_answer", "complete", "none")
        add(record, text)

        v = str(901 + i)
        cid = f"SYN-S09-{i:02d}"
        text = f"Reasoning proceeds carefully. \\boxed{{{v}"
        add(*_present(cid, "S09", text, v, "boxed", "malformed_recoverable"))

        cid = f"SYN-S10-{i:02d}"
        text = "Reasoning proceeds carefully. \\boxed{"
        record = _base(cid, "S10", "no_answer", "malformed_unrecoverable", "none")
        add(record, text)

        a, b = str(1101 + i), str(1151 + i)
        cid = f"SYN-S11-{i:02d}"
        text = f"Answer: {a} . Answer: {b}"
        record = _base(cid, "S11", "ambiguous", "complete", "ambiguous_candidates")
        first = _span(text, a, "explicit_answer_marker", "ambiguous_candidate")
        second = _span(text, b, "explicit_answer_marker", "ambiguous_candidate")
        record["expected_evidence_spans"] = [first, second]
        record["expected_candidate_answers"] = [
            first["normalized_answer"],
            second["normalized_answer"],
        ]
        record["registered_reference_answer"] = first["normalized_answer"]
        add(record, text)

        surface = _S12_SURFACES[i]
        cid = f"SYN-S12-{i:02d}"
        text = f"Final answer: {surface}"
        add(*_present(cid, "S12", text, surface, "explicit_final_marker", "complete"))

    return records, texts


def build_members(count: int = 12) -> list[dict]:
    return [
        {
            "name": f"object_{index:02d}.bin",
            "sha256": hashlib.sha256(f"object_{index:02d}".encode()).hexdigest(),
            "bytes": 100 + index,
        }
        for index in range(count)
    ]


@pytest.fixture(scope="module")
def synthetic_set():
    return build_synthetic_set()


@pytest.fixture(scope="module")
def policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def final_policy(policy):
    """A resolved copy of the shipped policy, used to exercise compilation."""
    resolved = copy.deepcopy(policy)
    resolved["policy_id"] = "parser-v3-v2-synthetic-test-policy"
    resolved["status"] = "FINAL"
    resolved["acceptance_thresholds"]["status"] = "FINAL"
    for item in resolved["acceptance_thresholds"]["items"]:
        item["status"] = "FINAL"
        item["value"] = 0
    resolved["comparators"]["status"] = "FINAL"
    return resolved


@pytest.fixture(scope="module")
def set_source(synthetic_set, policy):
    records, texts = synthetic_set
    return SetSource(
        set_id="parser-v3-synthetic",
        counts=SetCounts(
            sealed_object_count=12,
            total_case_count=120,
            residual_semantic_case_count=0,
        ),
        records=tuple(records),
        output_texts=texts,
        members=tuple(build_members(12)),
        gates=tuple(policy["gates"]),
    )


@pytest.fixture(scope="module")
def facts(synthetic_set, policy):
    records, texts = synthetic_set
    return build_set_facts(
        records,
        texts,
        set_id="parser-v3-synthetic",
        members=build_members(12),
        counts=SetCounts(
            sealed_object_count=12,
            total_case_count=120,
            residual_semantic_case_count=0,
        ),
        gates=policy["gates"],
    )


# ---------------------------------------------------------------------------
# Ontology: the three-class truth table
# ---------------------------------------------------------------------------


def test_truth_table_covers_exactly_three_classes():
    assert len(TRUTH_TABLE) == 3
    assert {row.answer_presence for row in TRUTH_TABLE} == {
        "present",
        "ambiguous",
        "no_answer",
    }
    for row in TRUTH_TABLE:
        assert row.parse_ambiguous is (row.answer_presence == "ambiguous")
        assert row.parsed_answer_null is (row.answer_presence != "present")


def test_truth_table_parse_validity_matches_the_frozen_instrument():
    """The scorer, not this module, decides what ``parse_valid`` means.

    Phase 1.2D's H8 listed ``ambiguous`` with ``parse_valid=false`` as a
    defect: the frozen instrument requires ``parse_valid is True`` for an
    ambiguous decision. A repair ontology that re-declared the defective
    combination would make every S11 case unscorable by construction, which is
    the condition that retired parser-v3-v1.
    """
    expected = {
        "present": True,
        "ambiguous": True,
        "no_answer": False,
    }
    for row in TRUTH_TABLE:
        assert row.parse_valid is expected[row.answer_presence], (
            f"{row.answer_presence} declares parse_valid={row.parse_valid}, "
            "which the frozen scoring instrument would reject"
        )


def test_every_truth_table_row_is_accepted_by_the_frozen_instrument(synthetic_set):
    """Each admissible class must round-trip through the scorer's own derivation."""
    records, texts = synthetic_set
    seen: set[str] = set()
    for record in records:
        decision = frozen.derive_typed_decision(record)
        assert decision == derive_typed_decision(record)
        seen.add(decision.split(":", 1)[0])
    assert seen == {"present", "ambiguous", "no_answer"}


def test_truth_table_rows_are_mutually_exclusive():
    """Rows are keyed by presence, so two rows sharing one would be dropped."""
    presences = [row.answer_presence for row in TRUTH_TABLE]
    assert len(set(presences)) == len(TRUTH_TABLE)
    keys = {
        (row.answer_presence, row.parse_valid, row.parse_ambiguous)
        for row in TRUTH_TABLE
    }
    assert len(keys) == len(TRUTH_TABLE)


def test_stratum_presence_matches_public_definitions():
    assert set(STRATUM_PRESENCE) == set(frozen.STRATA)
    for stratum in frozen.ANSWER_BEARING_STRATA:
        assert STRATUM_PRESENCE[stratum] == "present"
    assert STRATUM_PRESENCE["S10"] == "no_answer"
    assert STRATUM_PRESENCE["S11"] == "ambiguous"


def test_span_convention_is_literal_only():
    assert SPAN_CONVENTION == "literal_only"


def test_synthetic_set_is_valid(synthetic_set):
    records, texts = synthetic_set
    case_facts = validate_ontology_set(records, texts)
    assert len(case_facts) == 120
    classes = {fact["typed_decision_class"] for fact in case_facts}
    assert classes == {"present", "ambiguous", "no_answer"}


def test_every_typed_decision_state_is_reachable(synthetic_set):
    records, texts = synthetic_set
    decisions = {
        typed_decision_class(derive_typed_decision(record)) for record in records
    }
    assert decisions == {"present", "ambiguous", "no_answer"}


def test_present_decision_carries_its_canonical_value(synthetic_set):
    records, _ = synthetic_set
    record = next(r for r in records if r["stratum"] == "S12")
    decision = derive_typed_decision(record)
    assert decision.startswith("present:")
    assert decision.split(":", 1)[1] == record["expected_parsed_answer"]


def test_typed_decision_class_rejects_research_only():
    for name in RESEARCH_ONLY_TYPED_DECISION_CLASSES:
        with pytest.raises(OntologyError):
            typed_decision_class(name)


def test_undeclared_fourth_class_is_rejected(synthetic_set):
    """H8: ``present_unextractable`` has no formal image."""
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S09"))
    record["expected_parse_valid"] = False
    record["expected_parsed_answer"] = None
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])
    with pytest.raises(OntologyError):
        derive_typed_decision(record)


def test_present_without_canonical_answer_is_rejected(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(records[0])
    record["expected_parsed_answer"] = None
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_noncanonical_reference_answer_is_rejected(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(records[0])
    record["registered_reference_answer"] = "07.50"
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_stratum_presence_disagreement_is_rejected(synthetic_set):
    """The S10-labelled-present defect becomes a mechanical error."""
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S10"))
    record["expected_answer_presence"] = "present"
    record["expected_parse_valid"] = True
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_single_candidate_s11_is_rejected(synthetic_set):
    """The public S11 rule requires at least two distinct candidates."""
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S11"))
    record["expected_evidence_spans"] = record["expected_evidence_spans"][:1]
    record["expected_candidate_answers"] = record["expected_candidate_answers"][:1]
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_empty_output_quality_requires_empty_output(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S10"))
    record["expected_output_quality"] = "empty"
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_empty_output_quality_is_admissible_on_empty_output():
    record = _base("SYN-EMPTY-00", "S10", "no_answer", "empty", "none")
    fact = validate_ontology_record(record, "")
    assert fact["typed_decision"] == "no_answer"


def test_marker_inclusive_span_is_rejected(synthetic_set):
    """H5: a span the scoring instrument would reject invalidates the set."""
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S02"))
    text = texts[record["case_id"]]
    span = record["expected_evidence_spans"][0]
    marker_start = text.index("Final answer:")
    span["start"] = marker_start
    span["text"] = text[marker_start : span["end"]]
    with pytest.raises(OntologyError):
        validate_ontology_record(record, text)


def test_inconsistent_candidate_list_is_rejected(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(records[0])
    record["expected_candidate_answers"] = ["3"]
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_no_answer_must_carry_no_spans(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S07"))
    donor = next(r for r in records if r["stratum"] == "S02")
    record["expected_evidence_spans"] = copy.deepcopy(donor["expected_evidence_spans"])
    with pytest.raises(OntologyError):
        validate_ontology_record(record, texts[record["case_id"]])


def test_duplicate_case_ids_are_rejected(synthetic_set):
    records, texts = synthetic_set
    mutated = copy.deepcopy(records)
    mutated[1]["case_id"] = mutated[0]["case_id"]
    with pytest.raises(OntologyError):
        validate_ontology_set(mutated, texts)


def test_missing_locked_input_is_rejected(synthetic_set):
    records, texts = synthetic_set
    trimmed = dict(texts)
    trimmed.pop(records[0]["case_id"])
    with pytest.raises(OntologyError):
        validate_ontology_set(records, trimmed)


def test_invalid_stratum_totals_are_rejected(synthetic_set):
    records, texts = synthetic_set
    mutated = copy.deepcopy(records)
    mutated[0]["stratum"] = "S02"
    mutated[0]["critical_case"] = False
    with pytest.raises(OntologyError):
        validate_ontology_set(mutated, texts)


def test_wrong_case_count_is_rejected(synthetic_set):
    records, texts = synthetic_set
    with pytest.raises(OntologyError):
        validate_ontology_set(records[:119], texts)


# ---------------------------------------------------------------------------
# Normalisation N1-N6
# ---------------------------------------------------------------------------


def test_normalization_rules_are_the_six_recorded_rules():
    assert [rule for rule, _ in NORMALIZATION_RULES] == [
        "N1",
        "N2",
        "N3",
        "N4",
        "N5",
        "N6",
    ]


def test_n1_rewrites_a_marker_inclusive_span(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S02"))
    text = texts[record["case_id"]]
    span = record["expected_evidence_spans"][0]
    literal_start, literal_end = span["start"], span["end"]
    marker_start = text.index("Final answer:")
    span["start"] = marker_start
    span["text"] = text[marker_start:literal_end]

    updated = apply_n1_literal_only_spans(record, text)
    rewritten = updated["expected_evidence_spans"][0]
    assert (rewritten["start"], rewritten["end"]) == (literal_start, literal_end)
    assert rewritten["text"] == text[literal_start:literal_end]


def test_n1_is_a_no_op_on_a_literal_span(synthetic_set):
    records, texts = synthetic_set
    record = next(r for r in records if r["stratum"] == "S01")
    text = texts[record["case_id"]]
    assert apply_n1_literal_only_spans(record, text) == dict(record)


def test_n1_fails_closed_without_a_registered_literal(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S05"))
    text = texts[record["case_id"]]
    span = record["expected_evidence_spans"][0]
    tail_start = text.index(", and the remaining")
    span["start"] = tail_start
    span["end"] = len(text)
    span["text"] = text[tail_start:]
    with pytest.raises(NormalizationError):
        apply_n1_literal_only_spans(record, text)


def test_n1_fails_closed_on_two_distinct_unmatched_literals(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S04"))
    text = texts[record["case_id"]]
    span = record["expected_evidence_spans"][0]
    span["start"] = text.index("Step one")
    span["end"] = text.index(". Final answer") + 1
    span["text"] = text[span["start"] : span["end"]]
    span["normalized_answer"] = _canon("77777")
    with pytest.raises(NormalizationError):
        apply_n1_literal_only_spans(record, text)


def test_n2_canonicalises_the_reference_answer(synthetic_set):
    records, _ = synthetic_set
    record = copy.deepcopy(records[0])
    record["registered_reference_answer"] = "07.50"
    updated = apply_n2_canonical_reference(record)
    assert updated["registered_reference_answer"] == _canon("07.50")


def test_n3_attaches_the_registered_output_text(synthetic_set):
    records, texts = synthetic_set
    record = records[0]
    updated = apply_n3_output_text(record, texts)
    assert updated["output_text"] == texts[record["case_id"]]


def test_n3_fails_closed_without_a_locked_input(synthetic_set):
    records, _ = synthetic_set
    with pytest.raises(NormalizationError):
        apply_n3_output_text(records[0], {})


def test_n4_registers_the_rightmost_literal_for_s06(synthetic_set):
    records, texts = synthetic_set
    record = next(r for r in records if r["stratum"] == "S06")
    text = texts[record["case_id"]]
    updated = apply_n4_last_number_distractor(record, text)
    span = updated["last_number_distractor_span"]
    matches = frozen._registered_numeric_matches(text)
    assert (span["start"], span["end"]) == (matches[-1].start(), matches[-1].end())
    assert _canon(span["text"]) != record["expected_parsed_answer"]


def test_n4_fails_closed_when_the_distractor_equals_the_answer():
    text = "Final answer: 42 ( sanity check 42 )"
    record = _base("SYN-S06-BAD", "S06", "present", "complete", "explicit_final_marker")
    record["expected_parsed_answer"] = _canon("42")
    with pytest.raises(NormalizationError):
        apply_n4_last_number_distractor(record, text)


def test_n4_leaves_other_strata_without_a_distractor(synthetic_set):
    records, texts = synthetic_set
    record = next(r for r in records if r["stratum"] == "S01")
    updated = apply_n4_last_number_distractor(record, texts[record["case_id"]])
    assert "last_number_distractor_span" not in updated


def test_n5_derives_quota_diagnostic_tags(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S12"))
    record["output_text"] = texts[record["case_id"]]
    record["secondary_tags"] = ["negative_answer"]
    updated = apply_n5_secondary_tags(record)
    derived = frozen._surface_features(record) & set(frozen.QUOTA_DIAGNOSTIC_TAGS)
    assert set(updated["secondary_tags"]) & set(frozen.QUOTA_DIAGNOSTIC_TAGS) == derived


def test_n5_preserves_non_quota_tags(synthetic_set):
    records, texts = synthetic_set
    record = copy.deepcopy(records[0])
    record["output_text"] = texts[record["case_id"]]
    record["secondary_tags"] = ["continued_reasoning"]
    updated = apply_n5_secondary_tags(record)
    assert "continued_reasoning" in updated["secondary_tags"]


def test_n6_recomputes_candidates_in_first_source_order(synthetic_set):
    records, _ = synthetic_set
    record = copy.deepcopy(next(r for r in records if r["stratum"] == "S11"))
    expected = [
        span["normalized_answer"] for span in record["expected_evidence_spans"]
    ]
    record["expected_candidate_answers"] = list(reversed(expected))
    updated = apply_n6_candidate_answers(record)
    assert updated["expected_candidate_answers"] == expected


def test_normalization_is_idempotent(synthetic_set):
    records, texts = synthetic_set
    for record in records:
        once, _ = normalize_record(record, texts)
        twice, applied = normalize_record(once, texts)
        assert once == twice
        assert applied == ()


def test_normalization_preserves_every_typed_decision(synthetic_set):
    records, texts = synthetic_set
    for record in records:
        before = raw_typed_decision(record)
        after, _ = normalize_record(record, texts)
        assert raw_typed_decision(after) == before


def test_normalization_output_remains_ontology_valid(synthetic_set):
    records, texts = synthetic_set
    normalized, quarantined, receipt = normalize_set(records, texts)
    assert quarantined == {}
    assert receipt.normalized_case_count == 120
    validate_ontology_set(normalized, texts)


def test_present_unextractable_is_quarantined_not_collapsed(synthetic_set):
    records, texts = synthetic_set
    mutated = copy.deepcopy(records)
    victim = next(r for r in mutated if r["stratum"] == "S09")
    victim["expected_parse_valid"] = False
    victim["expected_parsed_answer"] = None
    assert raw_typed_decision(victim) == "present_unextractable"
    normalized, quarantined, receipt = normalize_set(mutated, texts)
    assert quarantined[victim["case_id"]] == QuarantineReason.RESEARCH_ONLY_CLASS
    assert len(normalized) == 119
    assert receipt.quarantined_case_count == 1
    assert victim["case_id"] not in [record["case_id"] for record in normalized]


def test_receipt_is_content_free(synthetic_set):
    records, texts = synthetic_set
    _, _, receipt = normalize_set(records, texts)
    payload = json.dumps(receipt.to_dict())
    for record in records:
        assert record["case_id"] not in payload
        answer = record.get("expected_parsed_answer")
        if answer:
            assert f'"{answer}"' not in payload
    for text in texts.values():
        assert text not in payload


def test_receipt_is_deterministic(synthetic_set):
    records, texts = synthetic_set
    _, _, first = normalize_set(records, texts)
    _, _, second = normalize_set(records, texts)
    assert first.to_dict() == second.to_dict()


def test_normalization_does_not_mutate_its_input(synthetic_set):
    records, texts = synthetic_set
    snapshot = copy.deepcopy(records)
    normalize_set(records, texts)
    assert records == snapshot


# ---------------------------------------------------------------------------
# Counts terminology
# ---------------------------------------------------------------------------


def test_count_kinds_are_distinct():
    assert len(set(COUNT_KINDS)) == len(COUNT_KINDS)
    assert "sealed_object_count" in COUNT_KINDS
    assert "total_case_count" in COUNT_KINDS
    assert "residual_semantic_case_count" in COUNT_KINDS


def test_counts_reject_unregistered_kind():
    counts = SetCounts(12, 120, 15)
    with pytest.raises(ContractError):
        counts.get("holdout_objects")


def test_counts_are_not_interchangeable():
    """Regression for the '12 objects' versus '15 residual cases' confusion."""
    counts = SetCounts(
        sealed_object_count=12, total_case_count=120, residual_semantic_case_count=15
    )
    assert counts.get("sealed_object_count") == 12
    assert counts.get("residual_semantic_case_count") == 15
    assert counts.get("sealed_object_count") != counts.get(
        "residual_semantic_case_count"
    )
    assert counts.to_dict()["total_case_count"] == 120


def test_counts_reject_invalid_values():
    with pytest.raises(ContractError):
        SetCounts(-1, 120, 0)
    with pytest.raises(ContractError):
        SetCounts(12, 120, 121)
    with pytest.raises(ContractError):
        SetCounts(True, 120, 0)


def test_object_count_disagreement_is_detected(policy, facts):
    """H1: declaring 15 storage objects for a 12-object prefix is an error."""
    mutated = copy.deepcopy(dict(facts))
    mutated["counts"]["sealed_object_count"] = 15
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.code == "H1" and finding.subject == "sealed_object_count"
        for finding in findings
    )


def test_locked_evaluation_report_distinguishes_objects_from_cases():
    """Regression for the ``Holdout objects 15`` reporting defect.

    The erratum quotes the defective line, so the test inspects the report's
    machine-readable summary block rather than the prose, and additionally
    requires that any surviving occurrence of the old phrasing appears only
    inside the quoted erratum.
    """
    report = (ROOT / "reports" / "phase1_parser_v3_locked_evaluation.md").read_text(
        encoding="utf-8"
    )
    block = report.split("```")[1]
    assert "sealed_object_count                12" in block
    assert "total_case_count                   120" in block
    assert "residual_semantic_case_count       15" in block
    assert "Holdout objects" not in block
    for line in report.splitlines():
        if "Holdout objects" in line:
            assert line.lstrip().startswith(">"), line
    assert "sealed_object_count" in report
    assert "residual_semantic_case_count" in report


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------


def test_shipped_policy_validates(policy):
    validate_policy(policy)


def test_shipped_policy_is_review_required(policy):
    assert policy["status"] == "REVIEW_REQUIRED"
    assert policy["acceptance_thresholds"]["status"] == "REVIEW_REQUIRED"
    assert all(
        item["value"] is None for item in policy["acceptance_thresholds"]["items"]
    )


def test_policy_support_is_derived_from_stratum_presence(policy):
    presence = policy["population"]["stratum_presence"]
    per_stratum = policy["population"]["cases_per_stratum"]
    derived = {"present": 0, "no_answer": 0, "ambiguous": 0}
    for value in presence.values():
        derived[value] += per_stratum
    assert derived == policy["population"]["typed_decision_support"]
    assert derived == {"present": 80, "no_answer": 30, "ambiguous": 10}


def test_policy_truth_table_binding(policy):
    assert policy["ontology"]["truth_table_id"] == TRUTH_TABLE_ID


def test_policy_rejects_a_fourth_declared_class(policy):
    mutated = copy.deepcopy(policy)
    mutated["ontology"]["typed_decision_classes"].append("present_unextractable")
    with pytest.raises(ContractError):
        validate_policy(mutated)


def test_policy_rejects_support_not_derived_from_presence(policy):
    mutated = copy.deepcopy(policy)
    mutated["population"]["typed_decision_support"] = {
        "present": 91,
        "no_answer": 23,
        "ambiguous": 6,
    }
    with pytest.raises(ContractError):
        validate_policy(mutated)


def test_policy_rejects_mandatory_gate_with_zero_minimum(policy):
    mutated = copy.deepcopy(policy)
    mutated["gates"][0]["minimum_denominator"] = 0
    with pytest.raises(ContractError):
        validate_policy(mutated)


def test_policy_cannot_be_final_while_thresholds_are_open(policy):
    mutated = copy.deepcopy(policy)
    mutated["status"] = "FINAL"
    with pytest.raises(ContractError):
        validate_policy(mutated)


# ---------------------------------------------------------------------------
# Set-derived facts and agreement
# ---------------------------------------------------------------------------


def test_facts_report_observed_vocabulary_and_supports(facts):
    assert facts["observed_typed_decision_vocabulary"] == [
        "ambiguous",
        "no_answer",
        "present",
    ]
    assert facts["observed_typed_decision_support"] == {
        "present": 80,
        "no_answer": 30,
        "ambiguous": 10,
    }
    assert set(facts["observed_stratum_support"].values()) == {10}
    assert facts["observed_critical_case_count"] == 80


def test_facts_are_deterministic(synthetic_set, policy):
    records, texts = synthetic_set
    kwargs = dict(
        set_id="parser-v3-synthetic",
        members=build_members(12),
        counts=SetCounts(12, 120, 0),
        gates=policy["gates"],
    )
    first = build_set_facts(records, texts, **kwargs)
    second = build_set_facts(records, texts, **kwargs)
    assert first == second


def test_facts_reject_an_inadmissible_set(synthetic_set, policy):
    records, texts = synthetic_set
    mutated = copy.deepcopy(records)
    mutated[0]["expected_parse_valid"] = False
    with pytest.raises(ContractError):
        build_set_facts(
            mutated,
            texts,
            set_id="parser-v3-synthetic",
            members=build_members(12),
            counts=SetCounts(12, 120, 0),
            gates=policy["gates"],
        )


def test_gate_denominators_are_derived_from_the_set(facts):
    assert facts["gate_denominators"]["G_S06_last_number_trap"] == 10
    assert facts["gate_denominators"]["G_clean_strata_exact"] == 40
    assert facts["gate_denominators"]["G_present_class_non_vacuous"] == 80
    assert facts["gate_denominators"]["G_null_collapse_prohibited"] == 120


def test_agreement_passes_on_a_conforming_set(policy, facts, set_source):
    assert check_agreement(policy, facts, set_source=set_source) == []


def test_a_fabricated_facts_manifest_cannot_be_used(policy, set_source):
    """A manifest with no set behind it must be refused, not compared.

    Regression for the audit finding that ``build_set_facts`` was sound but
    ``check_agreement``/``compile_contract`` accepted any mapping with the
    right schema version. A facts manifest is an operator's claim; an
    unverified claim is exactly what produced the parser-v3-v1 gate contract.
    """
    forged = {
        "schema_version": FACTS_SCHEMA_VERSION,
        "set_id": "parser-v3-synthetic",
        "counts": SetCounts(
            sealed_object_count=12,
            total_case_count=120,
            residual_semantic_case_count=0,
        ).to_dict(),
        "observed_typed_decision_vocabulary": ["ambiguous", "no_answer", "present"],
        "observed_typed_decision_support": {
            "present": 80,
            "no_answer": 30,
            "ambiguous": 10,
        },
        "observed_stratum_support": {stratum: 10 for stratum in frozen.STRATA},
        "observed_span_convention": SPAN_CONVENTION,
        "observed_critical_case_count": 80,
        "gate_denominators": {gate["gate_id"]: 120 for gate in policy["gates"]},
        "members": build_members(12),
        "member_object_count": 12,
        "case_fact_digest": "0" * 64,
        "set_sha256": "a" * 64,
    }
    forged = seal_facts(forged)
    with pytest.raises(ContractError, match="not reproducible"):
        check_agreement(policy, forged, set_source=set_source)


def test_an_edited_facts_manifest_breaks_its_own_seal(facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_typed_decision_support"] = {
        "present": 91,
        "no_answer": 23,
        "ambiguous": 6,
    }
    with pytest.raises(ContractError, match="edited after derivation"):
        verify_facts_integrity(mutated)


def test_a_facts_manifest_must_declare_every_count_kind(facts):
    mutated = copy.deepcopy(dict(facts))
    del mutated["counts"]["residual_semantic_case_count"]
    mutated = seal_facts(mutated)
    with pytest.raises(ContractError, match="omit registered kinds"):
        verify_facts_integrity(mutated)


def test_set_digest_commits_to_the_set_not_the_manifest(synthetic_set, facts):
    """``set_sha256`` must change when the set changes.

    Regression for the audit finding that it was a self-digest of the manifest
    it was inserted into, which certifies nothing about any set.
    """
    records, texts = synthetic_set
    assert facts["set_sha256"] == set_content_digest(records, texts)
    altered = copy.deepcopy(list(records))
    altered[0] = dict(altered[0])
    altered[0]["case_id"] = "SYN-S01-99"
    assert set_content_digest(altered, texts) != facts["set_sha256"]


def test_compilation_refuses_a_fabricated_manifest(final_policy, set_source, facts):
    forged = copy.deepcopy(dict(facts))
    forged["member_object_count"] = 15
    forged = seal_facts(forged)
    with pytest.raises(ContractError, match="not reproducible"):
        compile_contract(final_policy, forged, set_source=set_source)


def test_h9_support_disagreement_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_typed_decision_support"] = {
        "present": 91,
        "no_answer": 23,
        "ambiguous": 6,
    }
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.code == "H9" and finding.subject == "typed_decision_support"
        for finding in findings
    )


def test_h8_extra_class_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_typed_decision_vocabulary"] = [
        "ambiguous",
        "no_answer",
        "present",
        "present_unextractable",
    ]
    findings = agreement_findings(policy, mutated)
    assert any(finding.code == "H8" for finding in findings)


def test_h9_unexercised_class_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_typed_decision_vocabulary"] = ["no_answer", "present"]
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.code == "H9" and "never exercises" in finding.message
        for finding in findings
    )


def test_h9_stratum_support_disagreement_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_stratum_support"]["S06"] = 9
    findings = agreement_findings(policy, mutated)
    assert any(finding.subject == "stratum_support" for finding in findings)


def test_h2_case_count_disagreement_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["counts"]["total_case_count"] = 119
    findings = agreement_findings(policy, mutated)
    assert any(finding.code == "H2" for finding in findings)


def test_h3_vacuous_mandatory_gate_is_an_error(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["gate_denominators"]["G_S06_last_number_trap"] = 0
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.code == "H3" and "vacuous" in finding.message for finding in findings
    )


def test_h3_missing_gate_denominator_is_an_error(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["gate_denominators"].pop("G_S11_ambiguity_detection")
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.code == "H3" and "no denominator" in finding.message
        for finding in findings
    )


def test_h3_denominator_below_minimum_is_an_error(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["gate_denominators"]["G_present_class_non_vacuous"] = 79
    findings = agreement_findings(policy, mutated)
    assert any(finding.code == "H3" for finding in findings)


def test_h5_span_convention_disagreement_is_detected(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_span_convention"] = "marker_inclusive"
    findings = agreement_findings(policy, mutated)
    assert any(finding.code == "H5" for finding in findings)


def test_h1_membership_disagreement_is_detected(policy, facts):
    expected = [member["name"] for member in facts["members"]][:-1] + ["other.bin"]
    findings = agreement_findings(policy, facts, expected_members=expected)
    assert any(finding.code == "H1" for finding in findings)


def test_residual_semantic_cases_block_agreement(policy, facts):
    mutated = copy.deepcopy(dict(facts))
    mutated["counts"]["residual_semantic_case_count"] = 15
    findings = agreement_findings(policy, mutated)
    assert any(
        finding.subject == "residual_semantic_case_count" for finding in findings
    )


# ---------------------------------------------------------------------------
# Contract compilation
# ---------------------------------------------------------------------------


def test_compiler_refuses_a_review_required_policy(policy, facts, set_source):
    with pytest.raises(ContractError):
        compile_contract(policy, facts, set_source=set_source)


def test_compiler_refuses_open_thresholds(final_policy, facts, set_source):
    mutated = copy.deepcopy(final_policy)
    mutated["acceptance_thresholds"]["status"] = "REVIEW_REQUIRED"
    mutated["status"] = "REVIEW_REQUIRED"
    with pytest.raises(ContractError):
        compile_contract(mutated, facts, set_source=set_source)


def test_compiler_emits_a_contract_from_a_final_policy(final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    assert contract["compiled_from"]["set_id"] == facts["set_id"]
    assert contract["population"]["typed_decision_support"] == {
        "present": 80,
        "no_answer": 30,
        "ambiguous": 10,
    }
    assert len(contract["contract_sha256"]) == 64


def test_compilation_is_deterministic(final_policy, facts, set_source):
    first = render_contract(compile_contract(final_policy, facts, set_source=set_source))
    second = render_contract(compile_contract(final_policy, facts, set_source=set_source))
    assert first == second


def test_compiler_binds_every_gate_to_a_denominator(final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    for gate in contract["gates"]:
        assert isinstance(gate["denominator"], int)
        if gate["mandatory"]:
            assert gate["denominator"] >= gate["minimum_denominator"] >= 1


def test_compiler_never_edits_thresholds(final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    assert contract["acceptance_thresholds"] == final_policy["acceptance_thresholds"]


def test_compiler_refuses_a_disagreeing_set(final_policy, facts, set_source):
    mutated = copy.deepcopy(dict(facts))
    mutated["observed_typed_decision_support"]["present"] = 79
    with pytest.raises(ContractError):
        compile_contract(final_policy, mutated, set_source=set_source)


def test_compiler_refuses_to_overwrite(tmp_path, final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    target = tmp_path / "contract.json"
    write_contract(target, contract)
    with pytest.raises(ContractError):
        write_contract(target, contract)


def test_check_mode_reproduces_bytes(tmp_path, final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    target = tmp_path / "contract.json"
    write_contract(target, contract)
    check_contract(target, final_policy, facts, set_source=set_source)


def test_check_mode_detects_tampering(tmp_path, final_policy, facts, set_source):
    contract = compile_contract(final_policy, facts, set_source=set_source)
    target = tmp_path / "contract.json"
    write_contract(target, contract)
    tampered = json.loads(target.read_text(encoding="utf-8"))
    tampered["acceptance_thresholds"]["items"][0]["value"] = 999
    target.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
    with pytest.raises(ContractError):
        check_contract(target, final_policy, facts, set_source=set_source)


def test_compiler_does_not_touch_the_historical_contract(final_policy, facts, set_source):
    historical = ROOT / "docs" / "phase1_parser_v3_acceptance_gates.json"
    before = _lf_digest(historical)
    contract = compile_contract(final_policy, facts, set_source=set_source)
    assert contract["compiled_from"]["policy_id"] != "parser-v3-v1"
    assert _lf_digest(historical) == before
    with pytest.raises(ContractError):
        write_contract(historical, contract)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_set(tmp_path: Path, records, texts) -> tuple[Path, Path]:
    labels = tmp_path / "labels.jsonl"
    inputs = tmp_path / "inputs.jsonl"
    labels.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    inputs.write_text(
        "".join(
            json.dumps({"case_id": cid, "output_text": text}, sort_keys=True) + "\n"
            for cid, text in texts.items()
        ),
        encoding="utf-8",
    )
    return labels, inputs


def test_cli_facts_check_and_verify(tmp_path, synthetic_set, final_policy):
    import parser_v3_repair_cli as cli

    records, texts = synthetic_set
    labels, inputs = _write_set(tmp_path, records, texts)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(final_policy, indent=2), encoding="utf-8")
    members_path = tmp_path / "members.json"
    members_path.write_text(json.dumps(build_members(12), indent=2), encoding="utf-8")
    facts_path = tmp_path / "facts.json"

    assert (
        cli.main(
            [
                "facts",
                "--labels", str(labels),
                "--inputs", str(inputs),
                "--policy", str(policy_path),
                "--set-id", "parser-v3-synthetic",
                "--members", str(members_path),
                "--sealed-object-count", "12",
                "--out", str(facts_path),
            ]
        )
        == 0
    )
    _set_args = [
        "--labels", str(labels),
        "--inputs", str(inputs),
        "--set-id", "parser-v3-synthetic",
        "--members", str(members_path),
        "--sealed-object-count", "12",
    ]
    assert (
        cli.main(
            ["check", "--policy", str(policy_path), "--facts", str(facts_path)]
            + _set_args
        )
        == 0
    )
    contract_path = tmp_path / "contract.json"
    assert (
        cli.main(
            [
                "compile",
                "--policy", str(policy_path),
                "--facts", str(facts_path),
                "--out", str(contract_path),
            ]
            + _set_args
        )
        == 0
    )
    assert (
        cli.main(
            [
                "verify",
                "--policy", str(policy_path),
                "--facts", str(facts_path),
                "--contract", str(contract_path),
            ]
            + _set_args
        )
        == 0
    )
    # A second compile must refuse rather than overwrite.
    assert (
        cli.main(
            [
                "compile",
                "--policy", str(policy_path),
                "--facts", str(facts_path),
                "--out", str(contract_path),
            ]
            + _set_args
        )
        == 2
    )


def test_cli_check_reports_disagreement(tmp_path, synthetic_set, policy):
    """A policy that disagrees with a genuine set must be reported, not compiled."""
    import parser_v3_repair_cli as cli

    records, texts = synthetic_set
    labels, inputs = _write_set(tmp_path, records, texts)
    members_path = tmp_path / "members.json"
    members_path.write_text(json.dumps(build_members(12), indent=2), encoding="utf-8")
    mutated_policy = copy.deepcopy(dict(policy))
    # A policy that is internally consistent -- 12 strata x 12 cases, supports
    # re-derived from the same stratum presence -- but describes a larger
    # population than the set actually built. This is the H9 shape: the policy
    # is not malformed, it simply does not describe this set.
    mutated_policy["population"]["cases_per_stratum"] = 12
    mutated_policy["population"]["total_case_count"] = 144
    mutated_policy["population"]["typed_decision_support"] = {
        "present": 96,
        "no_answer": 36,
        "ambiguous": 12,
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(mutated_policy, indent=2), encoding="utf-8")

    facts_path = tmp_path / "facts.json"
    good_policy_path = tmp_path / "good_policy.json"
    good_policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    _set_args = [
        "--labels", str(labels),
        "--inputs", str(inputs),
        "--set-id", "parser-v3-synthetic",
        "--members", str(members_path),
        "--sealed-object-count", "12",
    ]
    assert (
        cli.main(
            [
                "facts",
                "--policy", str(good_policy_path),
                "--out", str(facts_path),
            ]
            + _set_args
        )
        == 0
    )
    assert (
        cli.main(
            ["check", "--policy", str(policy_path), "--facts", str(facts_path)]
            + _set_args
        )
        == 1
    )


def test_cli_refuses_a_hand_edited_facts_manifest(tmp_path, synthetic_set, policy):
    """The CLI must refuse a manifest that is not reproducible from the set."""
    import parser_v3_repair_cli as cli

    records, texts = synthetic_set
    labels, inputs = _write_set(tmp_path, records, texts)
    members_path = tmp_path / "members.json"
    members_path.write_text(json.dumps(build_members(12), indent=2), encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    facts_path = tmp_path / "facts.json"
    _set_args = [
        "--labels", str(labels),
        "--inputs", str(inputs),
        "--set-id", "parser-v3-synthetic",
        "--members", str(members_path),
        "--sealed-object-count", "12",
    ]
    assert (
        cli.main(
            ["facts", "--policy", str(policy_path), "--out", str(facts_path)]
            + _set_args
        )
        == 0
    )
    tampered = seal_facts(
        {
            **json.loads(facts_path.read_text(encoding="utf-8")),
            "observed_typed_decision_support": {
                "present": 91,
                "no_answer": 23,
                "ambiguous": 6,
            },
        }
    )
    facts_path.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
    assert (
        cli.main(
            ["check", "--policy", str(policy_path), "--facts", str(facts_path)]
            + _set_args
        )
        == 2
    )


@pytest.mark.parametrize(
    "subcommand,flag",
    [
        ("facts", "--members"),
        ("check", "--members"),
        ("check", "--expect-members"),
        ("compile", "--members"),
        ("compile", "--expect-members"),
        ("verify", "--members"),
        ("verify", "--expect-members"),
        ("normalize", "--out"),
        ("normalize", "--receipt"),
    ],
)
def test_cli_refuses_the_retired_namespace_on_every_flag(
    tmp_path, synthetic_set, policy, subcommand, flag
):
    """Every path-bearing flag must route through the refusal.

    Regression for the audit finding that ``--members`` and ``--expect-members``
    bypassed the guard entirely, against a directory that holds the private
    label files. The protocol claims the refusal has no override; this drives
    the claim through ``main`` rather than calling the helper directly.
    """
    import parser_v3_repair_cli as cli

    records, texts = synthetic_set
    labels, inputs = _write_set(tmp_path, records, texts)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    retired = tmp_path / "evaluator_sets" / "parser_v3_v1" / "members.json"
    retired.parent.mkdir(parents=True, exist_ok=True)
    retired.write_text("[]", encoding="utf-8")

    argv = [
        subcommand,
        "--labels", str(labels),
        "--inputs", str(inputs),
        flag, str(retired),
    ]
    if subcommand != "normalize":
        argv += ["--policy", str(policy_path), "--set-id", "parser-v3-synthetic"]
    if subcommand in ("check", "compile", "verify"):
        argv += ["--facts", str(tmp_path / "facts.json")]
    if subcommand == "compile":
        argv += ["--out", str(tmp_path / "contract.json")]
    if subcommand == "verify":
        argv += ["--contract", str(tmp_path / "contract.json")]

    assert cli.main(argv) == 2


def test_cli_refuses_retired_namespace_case_and_separator_variants(tmp_path):
    import parser_v3_repair_cli as cli

    for name in ("parser_v3_v1", "parser-v3-v1", "Parser_V3_V1"):
        candidate = tmp_path / "evaluator_sets" / name / "labels.jsonl"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("", encoding="utf-8")
        with pytest.raises(cli.CliError):
            cli._refuse_retired_namespace(candidate)


def test_cli_refuses_the_retired_namespace(tmp_path):
    import parser_v3_repair_cli as cli

    retired = tmp_path / "evaluator_sets" / "parser_v3_v1" / "labels.jsonl"
    retired.parent.mkdir(parents=True)
    retired.write_text("", encoding="utf-8")
    with pytest.raises(cli.CliError):
        cli._refuse_retired_namespace(retired)


def test_cli_normalize_emits_a_content_free_receipt(tmp_path, synthetic_set):
    import parser_v3_repair_cli as cli

    records, texts = synthetic_set
    labels, inputs = _write_set(tmp_path, records, texts)
    receipt_path = tmp_path / "receipt.json"
    out_path = tmp_path / "normalized.jsonl"
    assert (
        cli.main(
            [
                "normalize",
                "--labels", str(labels),
                "--inputs", str(inputs),
                "--out", str(out_path),
                "--receipt", str(receipt_path),
            ]
        )
        == 0
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["normalized_case_count"] == 120
    assert receipt["quarantined_case_count"] == 0
    payload = json.dumps(receipt)
    for record in records:
        assert record["case_id"] not in payload


# ---------------------------------------------------------------------------
# Isolation proofs
# ---------------------------------------------------------------------------


def test_repair_modules_do_not_reference_a_parser():
    for path in REPAIR_MODULES:
        source = path.read_text(encoding="utf-8")
        for forbidden in ("eval_parsing_v3", "eval_parsing_v2", "eval_parsing"):
            assert f"import {forbidden}" not in source
            assert f"from .{forbidden}" not in source
            assert f"from jspace_observation.{forbidden}" not in source


def test_repair_modules_do_not_invoke_a_parser():
    """No parser entry point or parser identity constant is referenced."""
    for path in REPAIR_MODULES:
        source = path.read_text(encoding="utf-8")
        for symbol in (
            "parse_v3",
            "parse_v2",
            "parse_answer",
            "PARSER_SOURCE_SHA256",
            "PARSER_VERSION",
            "PARSER_ALGORITHM_ID",
            "validate_parser_request",
            "validate_parser_result",
            "compare_parsed_answer_to_reference",
        ):
            assert symbol not in source, f"{path.name} references {symbol}"


def test_repair_tooling_loads_no_parser_beyond_the_package_baseline():
    """The repair modules import no parser of their own.

    ``jspace_observation/__init__.py`` eagerly imports the whole package, so any
    import from this repository already places the legacy parser in
    ``sys.modules``. The proof obligation is therefore differential: importing
    the repair tooling must load no module that importing the frozen validation
    instrument alone would not already have loaded.
    """
    template = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(ROOT / 'src')!r})\n"
        "{imports}"
        "print(json.dumps(sorted(n for n in sys.modules if 'jspace' in n)))\n"
    )
    baseline = subprocess.run(
        [
            sys.executable,
            "-c",
            template.format(
                imports="import jspace_observation.evaluator_validation\n"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    with_repair = subprocess.run(
        [
            sys.executable,
            "-c",
            template.format(
                imports=(
                    "import jspace_observation.evaluator_validation\n"
                    "import jspace_observation.parser_v3_repair_ontology\n"
                    "import jspace_observation.parser_v3_repair_normalization\n"
                    "import jspace_observation.parser_v3_repair_contract\n"
                )
            ),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    before = set(json.loads(baseline.stdout))
    after = set(json.loads(with_repair.stdout))
    added = after - before
    assert added == {
        "jspace_observation.parser_v3_repair_ontology",
        "jspace_observation.parser_v3_repair_normalization",
        "jspace_observation.parser_v3_repair_contract",
    }, sorted(added)
    assert not any("eval_parsing" in name for name in added)


def test_repair_modules_do_not_reference_private_set_paths():
    for path in REPAIR_MODULES:
        source = path.read_text(encoding="utf-8")
        assert "locked_inputs" not in source
        assert "locked_labels" not in source
        for marker in ("blob.core.windows.net", "BlobServiceClient", "azure."):
            assert marker not in source


def test_repair_sources_reference_no_parser_symbol():
    """The static half of the parser-free obligation.

    Paired with the differential import proof above. Neither alone is enough:
    a runtime check cannot show the absence of a parser in this package, and a
    static check cannot show that nothing imports one at runtime.
    """
    assert_parser_free_source(str(path) for path in REPAIR_MODULES)


def test_parser_free_source_check_actually_detects_a_parser_reference(tmp_path):
    """The checker must be able to fail, or it proves nothing."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from jspace_observation import eval_parsing_v3\n", encoding="utf-8"
    )
    with pytest.raises(NormalizationError, match="must not reference a parser"):
        assert_parser_free_source([str(offender)])


def test_protected_artifacts_are_unchanged():
    for relative, digest in PROTECTED_DIGESTS.items():
        path = ROOT / Path(relative)
        assert path.exists(), relative
        assert _lf_digest(path) == digest, relative


# --- Regressions for the second independent audit round ---------------------


def test_a_setsource_subclass_cannot_bypass_re_derivation(policy, set_source, facts):
    """An `isinstance` guard would let a subclass override `derive` and forge facts."""

    class ForgedSource(SetSource):
        def derive(self):  # pragma: no cover - must never be reached
            raise AssertionError("derive() must not dispatch through the instance")

    forged = ForgedSource(
        set_id=set_source.set_id,
        counts=set_source.counts,
        records=set_source.records,
        output_texts=set_source.output_texts,
        members=set_source.members,
        gates=set_source.gates,
    )
    with pytest.raises(ContractError, match="pass a SetSource"):
        check_agreement(policy, facts, set_source=forged)


def test_agreement_findings_is_not_public_api():
    """It trusts its input; advertising it would reopen the hole C2 closed."""
    import jspace_observation.parser_v3_repair_contract as contract_module

    assert "agreement_findings" not in contract_module.__all__
    assert "check_agreement" in contract_module.__all__


def test_write_contract_has_no_overwrite_escape_hatch(tmp_path):
    """An untested flag whose only purpose is to violate a stated invariant."""
    import inspect

    assert "allow_overwrite" not in inspect.signature(write_contract).parameters
    target = tmp_path / "contract.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="never amended in place"):
        write_contract(target, {"schema_version": "x"})


def test_n6_refuses_a_malformed_span_instead_of_raising_keyerror():
    """N6 is exported as a standalone pure function and must fail closed."""
    record = {
        "case_id": "c",
        "expected_evidence_spans": [{"normalized_answer": "3", "start": 0}],
    }
    with pytest.raises(NormalizationError) as excinfo:
        apply_n6_candidate_answers(record)
    assert excinfo.value.reason == QuarantineReason.RULE_FAILED


def test_quarantine_reasons_come_from_the_error_not_a_substring_match():
    """Substring classification silently misfiles any future rewording."""
    import jspace_observation.parser_v3_repair_normalization as norm_module

    error = NormalizationError("anything", reason=QuarantineReason.NO_SPAN_LITERAL)
    assert error.reason == QuarantineReason.NO_SPAN_LITERAL
    assert NormalizationError("no reason given").reason == QuarantineReason.RULE_FAILED
    assert not hasattr(norm_module, "_classify")


@pytest.mark.parametrize(
    "field, value",
    [
        ("expected_correctness", False),
        ("registered_reference_answer", "999"),
        ("expected_failure_reasons", ["no_reliable_answer"]),
    ],
)
def test_normalisation_quarantines_a_case_it_would_make_inadmissible(
    synthetic_set, field, value
):
    """The projection whitelist can have holes; the ontology validator cannot.

    Each mutation leaves a record that survives the licensed-projection check
    but is not admissible under the formal ontology. It must be quarantined as
    one case, not allowed through to fail whole-set validation later.
    """
    records, texts = synthetic_set
    target = next(r for r in records if r["stratum"] == "S01")
    broken = copy.deepcopy(dict(target))
    broken[field] = value
    with pytest.raises(NormalizationError) as excinfo:
        normalize_record(broken, texts)
    assert excinfo.value.reason == QuarantineReason.FAILS_ONTOLOGY


def test_whole_set_normalisation_actually_exercises_n1_and_n6(synthetic_set):
    """Idempotence over a fixture that no-ops N1 and N6 proves nothing about them."""
    records, texts = synthetic_set
    widened = []
    for record in records:
        record = copy.deepcopy(dict(record))
        spans = record.get("expected_evidence_spans") or []
        if record["stratum"] == "S02" and spans:
            span = dict(spans[0])
            span["start"] = max(0, span["start"] - 3)
            span["text"] = texts[record["case_id"]][span["start"] : span["end"]]
            record["expected_evidence_spans"] = [span] + [dict(s) for s in spans[1:]]
        if record["stratum"] == "S11" and len(spans) >= 2:
            record["expected_evidence_spans"] = [dict(s) for s in reversed(spans)]
        widened.append(record)

    normalized, quarantined, receipt = normalize_set(widened, texts)
    assert quarantined == {}
    assert receipt.rule_application_counts["N1"] >= 10
    assert receipt.rule_application_counts["N6"] >= 10

    twice, _, _ = normalize_set(normalized, texts)
    assert normalized == twice
