"""Tests for the deterministic ``parser-v3-v2`` construction rules.

Phase 1.2H-R2 / 1.2J. Public synthetic fixtures only; nothing here reads a
private set, a sealed blob or a locked label.

As with the lifecycle tests, several cases mutate the module's own declared
tables and require the behaviour to follow, because the recurrent finding in
this repository is a check bound to something other than the thing that runs.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from jspace_observation import parser_v3_v2_construction as construction
from jspace_observation.parser_v3_v2_construction import (
    BlockedOnSetRepair,
    ConstructionError,
)


def _decision(**overrides: Any) -> dict[str, Any]:
    base = {field: f"value-{field}" for field in construction.AGREEMENT_FIELDS}
    base.update(overrides)
    return base


def _valid_case(index: int) -> dict[str, Any]:
    stratum = construction.STRATA[index // construction.STRATUM_QUOTA]
    if index < 80:
        decision_class = "present"
    elif index < 110:
        decision_class = "no_answer"
    else:
        decision_class = "ambiguous"
    case: dict[str, Any] = {
        "case_id": f"synthetic-{index:04d}",
        "stratum": stratum,
        "decision_class": decision_class,
        "eligible": True,
        "adjudicable": True,
        "mandatory": True,
        "unresolved": False,
        "subtype_slot": f"{stratum}-slot-{index % construction.STRATUM_QUOTA}",
        "literal_spans": [{"literal": True, "start": 0, "end": 4}],
    }
    if stratum == "S06":
        case["rightmost_distractor_registration"] = True
    if stratum == "S11":
        case["ambiguity_registration"] = True
    return case


def _valid_set() -> list[dict[str, Any]]:
    return [_valid_case(index) for index in range(construction.TOTAL_CASES)]


# ---------------------------------------------------------------------------
# declared constants
# ---------------------------------------------------------------------------


class TestDeclaredConstants:
    def test_the_strata_and_quota_multiply_to_the_total(self) -> None:
        assert len(construction.STRATA) == 12
        assert construction.STRATUM_QUOTA * 12 == construction.TOTAL_CASES == 120

    def test_gate_pinned_and_residual_strata_partition_the_strata(self) -> None:
        gate = set(construction.GATE_PINNED_STRATA)
        residual = set(construction.RESIDUAL_STRATA)
        assert not gate.intersection(residual)
        assert gate.union(residual) == set(construction.STRATA)

    def test_the_gate_pinned_and_residual_counts_are_eighty_and_forty(self) -> None:
        assert len(construction.GATE_PINNED_STRATA) * construction.STRATUM_QUOTA == 80
        assert len(construction.RESIDUAL_STRATA) * construction.STRATUM_QUOTA == 40

    def test_the_decision_class_quotas_sum_to_the_total(self) -> None:
        assert sum(construction.DECISION_CLASS_QUOTA.values()) == construction.TOTAL_CASES
        assert set(construction.DECISION_CLASS_QUOTA) == set(construction.DECISION_CLASSES)

    def test_there_are_exactly_three_decision_classes(self) -> None:
        """No fourth or research-only class may exist."""
        assert len(construction.DECISION_CLASSES) == 3

    def test_every_exported_name_exists(self) -> None:
        for name in construction.__all__:
            assert hasattr(construction, name), f"{name} is exported but missing"


# ---------------------------------------------------------------------------
# blinding
# ---------------------------------------------------------------------------


class TestBlinding:
    def test_a_clean_reviewer_packet_is_accepted(self) -> None:
        construction.assert_reviewer_packet_is_blind(
            {"case_content": "text", "public_ontology_packet": {"slots": []}}
        )

    @pytest.mark.parametrize(
        "forbidden", sorted(construction.REVIEWER_FORBIDDEN_INPUTS)
    )
    def test_each_forbidden_reviewer_input_is_refused(self, forbidden: str) -> None:
        with pytest.raises(ConstructionError, match="forbidden input"):
            construction.assert_reviewer_packet_is_blind(
                {
                    "case_content": "text",
                    "public_ontology_packet": {},
                    forbidden: "anything",
                }
            )

    def test_a_reviewer_packet_missing_the_public_packet_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="missing required input"):
            construction.assert_reviewer_packet_is_blind({"case_content": "text"})

    def test_reviewers_cannot_see_each_others_decisions(self) -> None:
        assert "other_reviewer_decision" in construction.REVIEWER_FORBIDDEN_INPUTS

    def test_the_arbiter_may_not_see_the_old_label_before_adjudication(self) -> None:
        packet = {
            "case_content": "text",
            "public_ontology_packet": {},
            "reviewer_a": _decision(),
            "reviewer_b": _decision(),
            "old_label": "historic",
        }
        with pytest.raises(ConstructionError, match="only permitted after"):
            construction.assert_arbiter_packet_is_scoped(
                packet, adjudication_permanently_recorded=False
            )

    def test_the_arbiter_may_see_the_old_label_once_adjudication_is_recorded(self) -> None:
        packet = {
            "case_content": "text",
            "public_ontology_packet": {},
            "reviewer_a": _decision(),
            "reviewer_b": _decision(),
            "old_label": "historic",
        }
        construction.assert_arbiter_packet_is_scoped(
            packet, adjudication_permanently_recorded=True
        )

    def test_an_arbiter_packet_without_both_decisions_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="missing required input"):
            construction.assert_arbiter_packet_is_scoped(
                {
                    "case_content": "t",
                    "public_ontology_packet": {},
                    "reviewer_a": _decision(),
                },
                adjudication_permanently_recorded=False,
            )

    def test_the_recorded_flag_must_be_a_bool(self) -> None:
        with pytest.raises(ConstructionError, match="must be a bool"):
            construction.assert_arbiter_packet_is_scoped(
                {
                    "case_content": "t",
                    "public_ontology_packet": {},
                    "reviewer_a": _decision(),
                    "reviewer_b": _decision(),
                },
                adjudication_permanently_recorded="yes",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# agreement surface
# ---------------------------------------------------------------------------


class TestAgreementSurface:
    def test_identical_decisions_do_not_reach_the_arbiter(self) -> None:
        assert construction.disagreeing_fields(_decision(), _decision()) == ()
        assert construction.routes_to_arbiter(_decision(), _decision()) is False

    @pytest.mark.parametrize("field", construction.AGREEMENT_FIELDS)
    def test_every_agreement_field_is_actually_consulted(self, field: str) -> None:
        """Mutation control: differing on any listed field must route to arbitration."""
        other = _decision(**{field: "different"})
        assert construction.disagreeing_fields(_decision(), other) == (field,)
        assert construction.routes_to_arbiter(_decision(), other) is True

    def test_a_missing_field_counts_as_disagreement_not_agreement(self) -> None:
        incomplete = _decision()
        del incomplete["literal_spans"]
        assert "literal_spans" in construction.disagreeing_fields(_decision(), incomplete)

    def test_agreement_on_the_typed_decision_alone_is_not_agreement(self) -> None:
        a = _decision()
        b = _decision(literal_spans="elsewhere")
        assert a["typed_decision"] == b["typed_decision"]
        assert construction.routes_to_arbiter(a, b) is True

    def test_a_non_mapping_decision_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="must be a mapping"):
            construction.disagreeing_fields(_decision(), ["not", "a", "mapping"])  # type: ignore[arg-type]


class TestArbitrationRouting:
    def _decisions(self) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
        return {
            "agree-1": (_decision(), _decision()),
            "agree-2": (_decision(), _decision()),
            "differ-1": (_decision(), _decision(stratum="S02")),
        }

    def test_exactly_the_disagreements_are_accepted(self) -> None:
        construction.assert_only_disagreements_reached_arbiter(
            arbitrated_case_ids=["differ-1"], decisions_by_case=self._decisions()
        )

    def test_arbitrating_an_agreed_case_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="without a disagreement"):
            construction.assert_only_disagreements_reached_arbiter(
                arbitrated_case_ids=["differ-1", "agree-1"],
                decisions_by_case=self._decisions(),
            )

    def test_skipping_a_disagreement_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="never reached the arbiter"):
            construction.assert_only_disagreements_reached_arbiter(
                arbitrated_case_ids=[], decisions_by_case=self._decisions()
            )

    def test_an_arbitrated_case_with_no_recorded_decisions_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="no recorded decisions"):
            construction.assert_only_disagreements_reached_arbiter(
                arbitrated_case_ids=["ghost"], decisions_by_case=self._decisions()
            )


# ---------------------------------------------------------------------------
# quarantine and bounded replacement
# ---------------------------------------------------------------------------


class TestQuarantineAndReplacement:
    @pytest.mark.parametrize("reason", sorted(construction.QUARANTINE_REASONS))
    def test_every_registered_reason_is_accepted(self, reason: str) -> None:
        construction.assert_quarantine_reason_is_registered(reason)

    @pytest.mark.parametrize("reason", ["other", "inconvenient", "", "OTHER"])
    def test_an_unregistered_reason_is_refused(self, reason: str) -> None:
        with pytest.raises(ConstructionError, match="not a registered quarantine reason"):
            construction.assert_quarantine_reason_is_registered(reason)

    def test_a_batch_below_the_limit_is_permitted(self) -> None:
        construction.assert_replacement_batch_within_limit(
            slot="S01-slot-0", batches_used=1, preregistered_batch_limit=3
        )

    def test_exhausting_the_limit_blocks_on_set_repair(self) -> None:
        with pytest.raises(BlockedOnSetRepair, match="BLOCKED_ON_SET_REPAIR"):
            construction.assert_replacement_batch_within_limit(
                slot="S01-slot-0", batches_used=3, preregistered_batch_limit=3
            )

    def test_blocked_on_set_repair_is_a_construction_error_subclass(self) -> None:
        """A caller catching ConstructionError must not silently swallow the block."""
        assert issubclass(BlockedOnSetRepair, ConstructionError)

    def test_a_zero_limit_is_refused_as_unfalsifiable(self) -> None:
        with pytest.raises(ConstructionError, match="positive bound"):
            construction.assert_replacement_batch_within_limit(
                slot="S01-slot-0", batches_used=0, preregistered_batch_limit=0
            )

    @pytest.mark.parametrize("bad", [-1, "3", 1.5, True, None])
    def test_a_non_integer_or_negative_count_is_refused(self, bad: Any) -> None:
        with pytest.raises(ConstructionError):
            construction.assert_replacement_batch_within_limit(
                slot="S01-slot-0", batches_used=bad, preregistered_batch_limit=3
            )


# ---------------------------------------------------------------------------
# deterministic selection
# ---------------------------------------------------------------------------


class TestDeterministicSelection:
    def _candidates(self) -> list[dict[str, Any]]:
        return [
            {"case_id": f"cand-{index}", "eligibility_rank": index % 3, "content": f"body {index}"}
            for index in range(12)
        ]

    def test_selection_is_independent_of_input_order(self) -> None:
        candidates = self._candidates()
        expected = [c["case_id"] for c in construction.select_deterministically(candidates, count=5)]
        rng = random.Random(20260802)
        for _ in range(20):
            shuffled = candidates[:]
            rng.shuffle(shuffled)
            got = [c["case_id"] for c in construction.select_deterministically(shuffled, count=5)]
            assert got == expected

    def test_rank_dominates_and_the_content_hash_breaks_ties(self) -> None:
        candidates = self._candidates()
        chosen = construction.select_deterministically(candidates, count=4)
        assert [c["eligibility_rank"] for c in chosen] == [0, 0, 0, 0]
        digests = [construction.content_hash(c["content"]) for c in chosen]
        assert digests == sorted(digests)

    def test_two_candidates_with_identical_content_are_refused(self) -> None:
        candidates = self._candidates()
        candidates.append(
            {"case_id": "duplicate", "eligibility_rank": 0, "content": candidates[0]["content"]}
        )
        with pytest.raises(ConstructionError, match="share a content hash"):
            construction.select_deterministically(candidates, count=3)

    def test_selecting_more_than_available_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="cannot select"):
            construction.select_deterministically(self._candidates(), count=99)

    def test_a_candidate_missing_a_required_field_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="is missing"):
            construction.select_deterministically(
                [{"case_id": "x", "content": "body"}], count=1
            )

    def test_a_non_integer_rank_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="eligibility_rank"):
            construction.select_deterministically(
                [{"case_id": "x", "eligibility_rank": "1", "content": "body"}], count=1
            )

    def test_the_content_hash_is_unicode_normalised(self) -> None:
        """Two spellings a reviewer cannot distinguish must be one case."""
        composed = "caf\u00e9"
        decomposed = "cafe\u0301"
        assert composed != decomposed
        assert construction.content_hash(composed) == construction.content_hash(decomposed)

    def test_the_content_hash_refuses_non_text(self) -> None:
        with pytest.raises(ConstructionError, match="must be str"):
            construction.content_hash(b"bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# collision freedom
# ---------------------------------------------------------------------------


class TestCollisionFreedom:
    def test_a_distinct_set_passes_every_rule(self) -> None:
        construction.assert_no_prohibited_collision(
            set_contents={"a": "alpha one", "b": "beta two", "c": "gamma three"}
        )

    def test_an_exact_duplicate_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="within-set collision"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "same text", "b": "same text"}
            )

    def test_a_whitespace_and_case_variant_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="normalized"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "Same   Text", "b": "same text"}
            )

    def test_a_numeric_variant_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="numeric_normalized"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "value is 3", "b": "value is 3.0"}
            )

    def test_a_template_family_variant_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="template_family"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "order abc123 shipped", "b": "order zzz999 shipped"}
            )

    def test_the_template_rule_does_not_fire_on_unrelated_prose(self) -> None:
        """Regression guard for a rule that once flagged every same-shaped pair.

        Masking every alphanumeric run reduced "alpha one" and "beta two" to one
        skeleton, so the checker reported a collision between unrelated cases and
        would have sent a sound set to repair.
        """
        family = construction.COLLISION_RULES["template_family"]
        assert family("alpha one") != family("beta two")
        assert family("the shorter path") != family("the longer route")

    def test_the_template_rule_masks_quoted_and_bracketed_slots(self) -> None:
        family = construction.COLLISION_RULES["template_family"]
        assert family('pick "red" now') == family('pick "blue" now')
        assert family("pick {red} now") == family("pick {blue} now")
        assert family('pick "red" now') != family('choose "red" now')

    def test_every_registered_rule_can_actually_reject_something(self) -> None:
        """Mutation control: a rule that never fires is not a rule."""
        provoking = {
            "exact": ("same text", "same text"),
            "normalized": ("Same   Text", "same text"),
            "numeric_normalized": ("value is 3", "value is 3.0"),
            "template_family": ("order abc123 shipped", "order zzz999 shipped"),
        }
        assert set(provoking) == set(construction.COLLISION_RULES)
        for rule_name, (left, right) in provoking.items():
            with pytest.raises(ConstructionError) as error:
                construction.assert_no_prohibited_collision(
                    set_contents={"a": left, "b": right}
                )
            assert rule_name in str(error.value)

    def test_a_cross_set_collision_is_refused(self) -> None:
        import hashlib

        text = "shared with a public corpus"
        fingerprints = {
            name: hashlib.sha256(rule(text).encode("utf-8")).hexdigest()
            for name, rule in construction.COLLISION_RULES.items()
        }
        with pytest.raises(ConstructionError, match="cross-set collision"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": text},
                external_corpus_fingerprints={"public_dev_corpus": fingerprints},
            )

    def test_authorized_reuse_is_exempt_from_the_cross_set_rule(self) -> None:
        import hashlib

        text = "reused from never-evaluated retired v1"
        fingerprints = {
            name: hashlib.sha256(rule(text).encode("utf-8")).hexdigest()
            for name, rule in construction.COLLISION_RULES.items()
        }
        construction.assert_no_prohibited_collision(
            set_contents={"a": text},
            external_corpus_fingerprints={"retired_v1": fingerprints},
            authorized_reuse_case_ids=["a"],
        )

    def test_authorized_reuse_is_not_exempt_within_the_set(self) -> None:
        """A case may not appear twice regardless of where it came from."""
        with pytest.raises(ConstructionError, match="within-set collision"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "duplicated body", "b": "duplicated body"},
                authorized_reuse_case_ids=["a", "b"],
            )

    def test_a_corpus_missing_a_registered_rule_fingerprint_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="supplied no fingerprint"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "body"},
                external_corpus_fingerprints={"partial": {"exact": "deadbeef"}},
            )

    def test_authorized_reuse_naming_an_absent_case_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="not in the set"):
            construction.assert_no_prohibited_collision(
                set_contents={"a": "body"}, authorized_reuse_case_ids=["ghost"]
            )


# ---------------------------------------------------------------------------
# artifact hygiene
# ---------------------------------------------------------------------------


class TestArtifactHygiene:
    def test_a_clean_artifact_passes(self) -> None:
        construction.assert_no_parser_field(
            {"case_id": "x", "stratum": "S01", "notes": ["a", {"depth": 1}]}
        )

    @pytest.mark.parametrize(
        "key",
        ["parser_version", "prediction", "predicted_value", "accuracy", "macro_f1", "score", "performance", "pass_rate"],
    )
    def test_a_parser_bearing_field_is_refused_at_any_depth(self, key: str) -> None:
        with pytest.raises(ConstructionError, match="parser-bearing field"):
            construction.assert_no_parser_field({"outer": [{"inner": {key: 1}}]})

    def test_the_reported_path_locates_the_offending_field(self) -> None:
        with pytest.raises(ConstructionError, match=r"artifact\.outer\[0\]\.inner\.prediction"):
            construction.assert_no_parser_field({"outer": [{"inner": {"prediction": 1}}]})


class TestHistoricalSplitIsNotATarget:
    def test_an_innocent_rule_set_passes(self) -> None:
        construction.assert_split_is_not_a_target(
            {"batch_limit": 15, "timeout_seconds": 105, "strata": 12}
        )

    def test_a_rule_set_targeting_the_split_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="must never become one"):
            construction.assert_split_is_not_a_target(
                {"migration": {"expected_repairable": 105}}
            )

    def test_the_residual_count_is_refused_too(self) -> None:
        with pytest.raises(ConstructionError, match="must never become one"):
            construction.assert_split_is_not_a_target({"target_residual": 15})

    def test_the_marking_propagates_into_nested_structures(self) -> None:
        with pytest.raises(ConstructionError, match="must never become one"):
            construction.assert_split_is_not_a_target(
                {"quota": {"nested": {"deeper": [105]}}}
            )

    def test_the_historical_values_are_recorded_for_reference(self) -> None:
        assert construction.HISTORICAL_SPLIT == {"repairable": 105, "residual": 15}


# ---------------------------------------------------------------------------
# final set invariants
# ---------------------------------------------------------------------------


class TestFinalSetInvariants:
    def test_the_synthetic_valid_set_passes(self) -> None:
        construction.assert_final_set_invariants(_valid_set())

    def test_a_short_set_is_refused(self) -> None:
        with pytest.raises(ConstructionError, match="exactly 120"):
            construction.assert_final_set_invariants(_valid_set()[:-1])

    def test_a_duplicate_case_id_is_refused(self) -> None:
        cases = _valid_set()
        cases[1]["case_id"] = cases[0]["case_id"]
        with pytest.raises(ConstructionError, match="unique"):
            construction.assert_final_set_invariants(cases)

    def test_a_skewed_stratum_is_refused(self) -> None:
        cases = _valid_set()
        cases[0]["stratum"] = "S02"
        with pytest.raises(ConstructionError, match="stratum quota"):
            construction.assert_final_set_invariants(cases)

    def test_an_unregistered_stratum_is_refused(self) -> None:
        cases = _valid_set()
        cases[0]["stratum"] = "S13"
        with pytest.raises(ConstructionError, match="unregistered stratum"):
            construction.assert_final_set_invariants(cases)

    def test_a_fourth_decision_class_is_refused(self) -> None:
        cases = _valid_set()
        cases[0]["decision_class"] = "research_only"
        with pytest.raises(ConstructionError, match="no fourth or research-only class"):
            construction.assert_final_set_invariants(cases)

    def test_a_skewed_decision_class_quota_is_refused(self) -> None:
        cases = _valid_set()
        cases[0]["decision_class"] = "no_answer"
        with pytest.raises(ConstructionError, match="decision-class quota"):
            construction.assert_final_set_invariants(cases)

    @pytest.mark.parametrize("flag", ["eligible", "adjudicable", "mandatory"])
    def test_every_case_must_carry_each_mandatory_flag(self, flag: str) -> None:
        cases = _valid_set()
        cases[7][flag] = False
        with pytest.raises(ConstructionError, match=f"is not {flag}"):
            construction.assert_final_set_invariants(cases)

    def test_a_truthy_non_true_flag_is_refused(self) -> None:
        """Identity, not truthiness: 1 is not True for an admission flag."""
        cases = _valid_set()
        cases[7]["eligible"] = 1
        with pytest.raises(ConstructionError, match="is not eligible"):
            construction.assert_final_set_invariants(cases)

    def test_an_unresolved_decision_is_refused(self) -> None:
        cases = _valid_set()
        cases[3]["unresolved"] = True
        with pytest.raises(ConstructionError, match="unresolved decision"):
            construction.assert_final_set_invariants(cases)

    def test_a_missing_subtype_slot_is_refused(self) -> None:
        cases = _valid_set()
        cases[3]["subtype_slot"] = ""
        with pytest.raises(ConstructionError, match="no subtype slot"):
            construction.assert_final_set_invariants(cases)

    def test_a_non_literal_span_is_refused(self) -> None:
        cases = _valid_set()
        cases[9]["literal_spans"] = [{"literal": False, "start": 0, "end": 1}]
        with pytest.raises(ConstructionError, match="non-literal span"):
            construction.assert_final_set_invariants(cases)

    def test_s06_requires_a_rightmost_distractor_registration(self) -> None:
        cases = _valid_set()
        for case in cases:
            if case["stratum"] == "S06":
                case["rightmost_distractor_registration"] = False
                break
        with pytest.raises(ConstructionError, match="rightmost-distractor"):
            construction.assert_final_set_invariants(cases)

    def test_s11_requires_an_ambiguity_registration(self) -> None:
        cases = _valid_set()
        for case in cases:
            if case["stratum"] == "S11":
                del case["ambiguity_registration"]
                break
        with pytest.raises(ConstructionError, match="ambiguity registration"):
            construction.assert_final_set_invariants(cases)

    def test_a_parser_bearing_field_on_a_case_is_refused(self) -> None:
        cases = _valid_set()
        cases[0]["parser_v3_result"] = "pass"
        with pytest.raises(ConstructionError, match="parser-bearing field"):
            construction.assert_final_set_invariants(cases)

    def test_the_gate_pinned_and_residual_split_is_derived_not_declared(self) -> None:
        """The 80/40 split must follow from the strata, not from a summary field."""
        cases = _valid_set()
        gate = sum(1 for c in cases if c["stratum"] in construction.GATE_PINNED_STRATA)
        residual = sum(1 for c in cases if c["stratum"] in construction.RESIDUAL_STRATA)
        assert (gate, residual) == (80, 40)
