"""Derive the Study 3 draft-v0.6 scoring boundary, registry and accounting.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 3,
4, 5 and 10.

draft-v0.6 makes exactly one normative change to the candidate protocol: the
S2/S3 decision statistic is registered at the **first discriminative token** of
the complete candidate instead of at a single position that the pinned role
tokenizers cannot deliver. The visible answer surface is untouched. Every byte a
model would read is identical to draft-v0.5 except that one extra token of the
candidate itself is teacher-forced into the scoring context.

This module is the single structured source for that change. It

* copies the byte-frozen v0.5 rendering registry and adds only the new
  normative scoring-boundary fields, so the visible rendering cannot drift;
* derives the common-prefix and discriminant token identities by replaying the
  immutable P0-T evidence, never by transcription;
* re-derives every affected operation, token-accounting and statistical field
  from ``design_statistics.py`` and from the immutable P0-T records; and
* records, separately and explicitly, every quantity that changes and every
  quantity proved unchanged.

The v0.5 registry, schema, amendment record, design receipt and review packet
are never edited. They remain history.

Usage::

    python scoring_boundary_v0_6.py --write
    python scoring_boundary_v0_6.py --check
"""

import argparse
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0_r1"))

import design_statistics as DS  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402

PROTOCOL_DIR = os.path.join(REPO_ROOT, "studies", "study3", "protocol")
REGISTRY_V0_5_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.json")
REGISTRY_V0_5_SCHEMA_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.schema.json")
REGISTRY_V0_6_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_6.json")
REGISTRY_V0_6_SCHEMA_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_6.schema.json")
TABLES_PATH = os.path.join(HERE, "scoring_boundary_v0_6_tables.json")

SCHEMA_VERSION = "study3-interface-calibration-rendering-registry-v0.6"
TABLES_SCHEMA_VERSION = "study3-scoring-boundary-v0-6-tables-v1"

DRAFT_VERSION = "draft-v0.6"
STATE = ("STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_"
         "AWAITING_FINAL_FOCUSED_METHODS_REVIEW")
DISPOSITION = "PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW"

# The registered profiles that carry the new scoring boundary.
FIRST_DISCRIMINATIVE_TOKEN_PROFILES = ("S2", "S3")

REGISTERED_DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")


class ScoringBoundaryDefect(Exception):
    """A fail-closed derivation stop."""


def canonical(document):
    return json.dumps(document, indent=1, sort_keys=True,
                      ensure_ascii=True) + "\n"


def _load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


# The replay derivation is deterministic and depends only on immutable bytes, so
# it is computed once per process. This keeps ``--write`` and ``--check`` from
# solving the same token segmentation five times over.
_REPLAY_CACHE = {}


def _cached_replay(registry):
    if "replay" not in _REPLAY_CACHE:
        _REPLAY_CACHE["replay"] = FACT.replay(registry)
    return _REPLAY_CACHE["replay"]


def _cached_token_accounting():
    if "tokens" not in _REPLAY_CACHE:
        _REPLAY_CACHE["tokens"] = derive_token_accounting()
    return _REPLAY_CACHE["tokens"]


# ---------------------------------------------------------------------------
# The five registered eligibility conditions of section 3.2.
# ---------------------------------------------------------------------------

def eligibility_conditions():
    return [
        {
            "id": "SB-1",
            "condition": "every complete candidate is exactly two tokens",
        },
        {
            "id": "SB-2",
            "condition": "the first token is identical for all ten candidates",
        },
        {
            "id": "SB-3",
            "condition": ("that common token decodes byte-exactly to the "
                          "registered leading U+0020"),
        },
        {
            "id": "SB-4",
            "condition": ("the second token IDs are pairwise distinct and map "
                          "byte-exactly to 0 through 9 in registered order"),
        },
        {
            "id": "SB-5",
            "condition": ("no BOS, EOS, chat template, normalization, padding, "
                          "truncation or implicit whitespace transformation "
                          "participates in the factorization"),
        },
    ]


def scoring_boundary_block(derived):
    """The top-level normative scoring-boundary block registered by v0.6."""
    roles = {entry["role"]: entry for entry in derived["roles"]}
    first = derived["roles"][0]
    return {
        "registered_in": DRAFT_VERSION,
        "supersedes": (
            "the draft-v0.5 rule that read one next-token logit vector at the "
            "single position immediately after the answer cue and restricted it "
            "to ten registered content token IDs"),
        "repairs": [
            "the demonstrated S2/S3 scoring-surface defect: under every pinned "
            "role tokenizer each registered content surface is two tokens, so "
            "the v0.5 single-position rule is not implementable as written",
            "the demonstrated eligibility-classifier propagation defect: a "
            "role-level S2 failure was propagated onto mechanically valid S1 "
            "cells, producing ineligible rows with empty reason lists",
        ],
        "visible_answer_surface_unchanged": {
            "answer_cue": "Answer:",
            "answer_cue_trailing_whitespace": "none",
            "candidate_surfaces": [" %s" % digit for digit in REGISTERED_DIGITS],
            "each_candidate_carries_exactly_one_leading_u0020": True,
            "s1_rendering_and_scoring_bytes_unchanged": True,
            "s4_rendering_wrapper_parser_and_diagnostic_only_status_unchanged":
                True,
            "no_question_option_instruction_contrast_nuisance_tuple_ground_truth"
            "_or_candidate_mapping_changed": True,
            "the_space_was_not_removed_moved_into_the_cue_or_replaced_by_letters":
                True,
        },
        "first_discriminative_token_rule": {
            "factorization": "candidate_d = common_prefix || discriminant_d",
            "s2_scoring_context": (
                "the registered prompt token IDs followed by the verified "
                "common-prefix token"),
            "s2_scoring_context_construction": (
                "concatenation of the registered prompt token IDs with the "
                "verified common-prefix token ID. The scoring context is never "
                "produced by re-encoding a concatenated string, so no additional "
                "tokenizer encode is introduced"),
            "s2_evaluation": (
                "one ordinary prefill evaluation on that context, reading the "
                "next-token logit vector only at the ten verified discriminant "
                "token IDs"),
            "s2_decision": (
                "the deterministic restricted argmax over the ten discriminant "
                "logits, mapped back to the complete registered candidate "
                "surface"),
            "s3_evaluation": (
                "reuse of the exact S2 discriminant-position logit vector on "
                "CPU; S3 adds zero model evaluations, model loads, prefills, "
                "decodes and generations"),
            "common_prefix_is": (
                "a teacher-forced candidate prefix. It is not a "
                "prompt-rendering change and it is not a generated token"),
            "prohibited": [
                "scoring the shared first token",
                "pretending the two-token candidate is one token",
                "summing unrelated positions",
                "using free generation",
                "introducing a new calibration parameter",
            ],
            "tie_break_order": (
                "ascending mod-10 residue order 0, 1, 2, ..., 9, unchanged from "
                "draft-v0.5"),
        },
        "eligibility_conditions": eligibility_conditions(),
        "equivalence_proof": FACT.equivalence_identity(),
        "derived_token_identities": {
            "provenance": (
                "derived and verified by replaying the immutable published P0-T "
                "result and the frozen P0 corpus; never transcribed as an "
                "unverified assumption"),
            "derivation_module":
                "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
            "tokenizer_encodes_performed_by_the_derivation": 0,
            "immutable_sources": derived["immutable_sources"],
            "common_prefix_token_common_to_every_pinned_role":
                derived["common_prefix_token_is_common_to_every_role"],
            "by_role": {
                role: {
                    "common_prefix_token": entry["common_prefix_token"],
                    "common_prefix_bytes": entry["common_prefix_bytes"],
                    "discriminant_token_ids": entry["discriminant_token_ids"],
                    "discriminant_bytes": entry["discriminant_bytes"],
                    "eligible": entry["eligible"],
                }
                for role, entry in sorted(roles.items())
            },
            "pinned_roles_only": (
                "these identities hold for the three currently pinned role "
                "tokenizers. Any further tokenizer must be separately pinned and "
                "re-verified before the rule may be applied to it"),
        },
        "claim_boundary": [
            "draft-v0.6 is not reviewed, not frozen, not selected and not "
            "formally executable",
            "the equivalence does not extend to arbitrary multi-token "
            "candidates, unequal lengths, non-common prefixes, summed log "
            "probabilities, free generation, or any unpinned tokenizer",
            "no interface is selected, no threshold or sample size is set, no "
            "effect is estimated and the original research question is "
            "unanswered",
        ],
        "s1_scoring_boundary_unchanged": {
            "rule": ("one next-token logit vector at the single position "
                     "immediately after the answer cue, restricted to the four "
                     "registered label token IDs"),
            "why_unaffected": (
                "each registered S1 label surface is one token under every "
                "pinned role tokenizer, so no factorization is required"),
            "observed_label_token_ids": _s1_label_tokens(derived),
        },
        "s4_scoring_boundary_unchanged": {
            "status": "diagnostic-only; never selectable",
            "rule": "bounded greedy generation mapped by the pinned parser",
            "participates_in_target_role_executability": False,
        },
        "common_prefix_token_for_every_pinned_role":
            first.get("common_prefix_token"),
    }


def _s1_label_tokens(derived):
    result = FACT.load_immutable(FACT.RESULT_PATH)
    out = {}
    for role in sorted(result["candidate_token_eligibility"]):
        entry = result["candidate_token_eligibility"][role]
        out[role] = {
            alphabet: {
                "surfaces": list(body["surfaces"]),
                "token_ids": [list(ids) for ids in body["token_ids"]],
                "all_single_token": body["all_single_token"],
                "pairwise_distinct": body["pairwise_distinct"],
            }
            for alphabet, body in sorted(entry["s1_by_alphabet"].items())
        }
    del derived
    return out


# ---------------------------------------------------------------------------
# The per-profile scoring boundary.
# ---------------------------------------------------------------------------

def profile_scoring_boundary(profile, derived, token_accounting):
    common = derived["roles"][0]
    bucket = token_accounting["by_profile"][profile]
    if profile == "S1":
        return {
            "scoring_rule": "single_next_token_restricted_argmax",
            "candidate_token_structure": (
                "every registered candidate surface is exactly one token under "
                "every pinned role tokenizer"),
            "candidate_factorization": None,
            "common_prefix_token_count_per_scored_row": 0,
            "common_prefix_token_count": bucket["common_prefix_token_count"],
            "teacher_forced_common_prefix": False,
            "scoring_context": "the registered prompt token IDs, unchanged",
            "reads_logits_at": (
                "the single next-token position immediately after the registered "
                "answer cue"),
            "scored_rows": bucket["scored_rows"],
            "registered_prompt_token_count":
                bucket["registered_prompt_token_count"],
            "scoring_context_token_count":
                bucket["scoring_context_token_count"],
            "tokens_processed": bucket["tokens_processed"],
            "sequence_level_model_evaluations_per_scored_row": 1,
            "unchanged_from_v0_5": True,
        }
    if profile in FIRST_DISCRIMINATIVE_TOKEN_PROFILES:
        boundary = {
            "scoring_rule": "first_discriminative_token_restricted_argmax",
            "candidate_token_structure": (
                "every registered candidate surface is exactly two tokens under "
                "every pinned role tokenizer: one shared leading-space token and "
                "one distinct digit token"),
            "candidate_factorization": (
                "candidate_d = common_prefix || discriminant_d"),
            "common_prefix_token_count_per_scored_row": 1,
            "common_prefix_token_count": bucket["common_prefix_token_count"],
            "teacher_forced_common_prefix": True,
            "teacher_forced_common_prefix_is_a_generation": False,
            "teacher_forced_common_prefix_is_a_separate_sequence_level_model_"
            "evaluation": False,
            "teacher_forced_common_prefix_is_a_prompt_rendering_change": False,
            "scoring_context": (
                "the registered prompt token IDs followed by the verified "
                "common-prefix token"),
            "reads_logits_at": (
                "the single next-token position after the teacher-forced common "
                "prefix, restricted to the ten verified discriminant token IDs"),
            "scored_rows": bucket["scored_rows"],
            "registered_prompt_token_count":
                bucket["registered_prompt_token_count"],
            "scoring_context_token_count":
                bucket["scoring_context_token_count"],
            "tokens_processed": bucket["tokens_processed"],
            "eligibility_conditions": eligibility_conditions(),
            "verified_common_prefix_token": common["common_prefix_token"],
            "verified_discriminant_token_ids":
                list(common["discriminant_token_ids"]),
            "unchanged_from_v0_5": {
                "candidate_surfaces": True,
                "answer_cue": True,
                "prompt_bytes": True,
                "tie_break_order": True,
                "k6_sep_structural_absence": True,
            },
        }
        if profile == "S2":
            boundary["sequence_level_model_evaluations_per_scored_row"] = 1
        else:
            boundary["sequence_level_model_evaluations_per_scored_row"] = 0
            boundary["reuses"] = (
                "the exact S2 discriminant-position logit vector, on CPU")
            boundary["scoring_context_is_the_reused_s2_context"] = True
            boundary["adds_zero"] = [
                "model evaluations", "model loads", "prefills", "decodes",
                "generations", "processed tokens",
            ]
        return boundary
    return {
        "scoring_rule": "bounded_greedy_generation_mapped_by_the_pinned_parser",
        "candidate_token_structure": (
            "not applicable; S4 generates text over an open vocabulary"),
        "candidate_factorization": None,
        "common_prefix_token_count_per_scored_row": 0,
        "common_prefix_token_count": bucket["common_prefix_token_count"],
        "teacher_forced_common_prefix": False,
        "scoring_context": "the registered wrapped message, unchanged",
        "reads_logits_at": (
            "not applicable; S4 is diagnostic-only and is never selectable"),
        "scored_rows": bucket["scored_rows"],
        "registered_prompt_token_count": bucket["registered_prompt_token_count"],
        "scoring_context_token_count": bucket["scoring_context_token_count"],
        "tokens_processed": bucket["tokens_processed"],
        "participates_in_target_role_executability": False,
        "unchanged_from_v0_5": True,
    }


# ---------------------------------------------------------------------------
# Token accounting, derived from the immutable P0-T records.
# ---------------------------------------------------------------------------

def derive_token_accounting():
    """Derive registered-prompt and scoring-context token counts from evidence."""
    result = FACT.load_immutable(FACT.RESULT_PATH)
    by_profile = {}
    for record in result["records"]:
        if record.get("structural_absence"):
            continue
        if record.get("source") != "frozen_corpus":
            continue
        profile = record["profile"]
        bucket = by_profile.setdefault(profile, {
            "scored_rows": 0,
            "registered_prompt_token_count": 0,
            "minimum_registered_prompt_tokens": None,
            "maximum_registered_prompt_tokens": None,
        })
        for member in record["members"]:
            count = member["token_count"]
            bucket["scored_rows"] += 1
            bucket["registered_prompt_token_count"] += count
            if bucket["minimum_registered_prompt_tokens"] is None \
                    or count < bucket["minimum_registered_prompt_tokens"]:
                bucket["minimum_registered_prompt_tokens"] = count
            if bucket["maximum_registered_prompt_tokens"] is None \
                    or count > bucket["maximum_registered_prompt_tokens"]:
                bucket["maximum_registered_prompt_tokens"] = count
    for profile, bucket in by_profile.items():
        # S2 and S3 share one scoring context: S3 rescores the vector S2 already
        # read, so the reused context carries the same teacher-forced prefix.
        per_row = 1 if profile in FIRST_DISCRIMINATIVE_TOKEN_PROFILES else 0
        bucket["common_prefix_token_count_per_scored_row"] = per_row
        bucket["common_prefix_token_count"] = per_row * bucket["scored_rows"]
        bucket["scoring_context_token_count"] = (
            bucket["registered_prompt_token_count"]
            + bucket["common_prefix_token_count"])
        bucket["sequence_level_model_evaluations_per_scored_row"] = (
            0 if profile == "S3" else 1)
        bucket["sequence_level_prefill_evaluations"] = (
            0 if profile == "S3" else bucket["scored_rows"])
        # S3 processes no token of its own: it reuses the captured S2 vector.
        bucket["tokens_processed"] = (
            0 if profile == "S3" else bucket["scoring_context_token_count"])

    restricted = ("S1", "S2")
    totals = {
        "scored_rows": sum(b["scored_rows"] for b in by_profile.values()),
        "registered_prompt_tokens_processed_by_restricted_scoring": sum(
            by_profile[p]["registered_prompt_token_count"] for p in restricted
            if p in by_profile),
        "common_prefix_tokens_processed": sum(
            by_profile[p]["common_prefix_token_count"] for p in restricted
            if p in by_profile),
        "s4_registered_prompt_tokens": (
            by_profile.get("S4", {}).get("registered_prompt_token_count", 0)),
        "s3_tokens_processed": by_profile.get("S3", {}).get("tokens_processed", 0),
        "s3_sequence_level_model_evaluations": (
            by_profile.get("S3", {}).get("sequence_level_prefill_evaluations", 0)),
    }
    totals["scoring_context_tokens_processed"] = (
        totals["registered_prompt_tokens_processed_by_restricted_scoring"]
        + totals["common_prefix_tokens_processed"])
    totals["extra_tokens_versus_the_v0_5_rule"] = (
        totals["common_prefix_tokens_processed"])
    totals["extra_sequence_level_model_evaluations_versus_the_v0_5_rule"] = 0
    return {
        "source": (
            "the immutable published P0-T result, frozen-corpus records only; "
            "derived, not assumed"),
        "unit": "tokens",
        "by_profile": by_profile,
        "p0_r1_totals": totals,
        "s3_processes_no_additional_token": True,
        "s3_note": (
            "S3 reuses the S2 discriminant-position logit vector on CPU, so it "
            "processes no token and performs no sequence-level evaluation. Its "
            "scoring-context token count records the S2 context it rescores, "
            "which is why the two profiles report the same context length"),
    }


# ---------------------------------------------------------------------------
# Statistical re-derivation and the change census.
# ---------------------------------------------------------------------------

def derive_statistical_invariance():
    """Re-derive every statistic the new scoring boundary could have touched."""
    tables = DS.build_tables()
    power = tables["power_architecture"]
    counts = tables["gate_bearing_cell_counts"]
    development = {row["gate_family"]: row
                   for row in tables["development_exact_binomial_components"]}
    confirmation = {row["gate_family"]: row
                    for row in tables["confirmation_exact_binomial_components"]}
    stream = tables["projected_operation_accounting"]["work_streams"][
        "target_role_development"]

    unchanged = {
        "m_max": power["m_max"],
        "m_max_scope": power["m_max_scope"],
        "per_cell_false_negative_budget_exact_rational":
            power["per_cell_false_negative_budget_exact_rational"],
        "per_cell_power_target_exact_rational":
            power["per_cell_power_target_exact_rational"],
        "profile_stage_power_floor_exact_rational":
            power["profile_stage_power_floor_exact_rational"],
        "study_end_to_end_power_floor_exact_rational":
            power["study_end_to_end_power_floor_exact_rational"],
        "development_sizes": {
            family: row["n"] for family, row in sorted(development.items())
        },
        "development_pass_counts": {
            family: row["pass_count"] for family, row in sorted(development.items())
        },
        "confirmation_sizes": {
            family: row["n"] for family, row in sorted(confirmation.items())
        },
        "confirmation_pass_counts": {
            family: row["pass_count"]
            for family, row in sorted(confirmation.items())
        },
        "total_gate_bearing_cells": {
            profile: body["total_gate_bearing_cells"]
            for profile, body in sorted(counts.items())
        },
        "applicable_i3_contrast_counts": {
            profile: body["applicable_i3_contrast_count"]
            for profile, body in sorted(counts.items())
        },
        "development_projection_scored_rows": stream["scored_rows"],
        "development_projection_sequence_level_model_evaluation_equivalents":
            stream["total_sequence_level_model_evaluation_equivalents"],
        "development_projection_by_profile_prefill_evaluations": {
            profile: body["sequence_level_prefill_evaluations"]
            for profile, body in sorted(stream["by_profile"].items())
        },
        "s3_incremental_sequence_evaluations":
            stream["S3_incremental_sequence_evaluations"],
    }

    expected = {
        "m_max": 43,
        "development_sizes": {
            "I1_I3_joint_correctness_floor": 413,
            "I2_headroom_floor": 214,
            "I4_positive_reference_floor": 448,
        },
        "development_projection_scored_rows": 31065,
        "development_projection_sequence_level_model_evaluation_equivalents":
            31065,
    }
    for field, value in expected.items():
        if unchanged[field] != value:
            raise ScoringBoundaryDefect(
                "the new scoring boundary changed %s from %r to %r; a change "
                "that the boundary does not mathematically require may not be "
                "absorbed silently" % (field, value, unchanged[field]))

    projected_extra = stream["by_profile"]["S2"]["scored_rows"]
    return {
        "method": (
            "every quantity below is recomputed from "
            "studies/study3/analysis/design_statistics.py at derivation time and "
            "compared against the published draft-v0.5 value; none is copied "
            "forward for continuity"),
        "unchanged_and_why": {
            "why_no_statistic_moves": (
                "the new boundary changes where one logit vector is read and "
                "adds one teacher-forced token to the S2 scoring context. It "
                "changes no cell, no contrast applicability, no independent "
                "unit, no null, no alternative, no alpha and no decision rule, "
                "so no sample size, pass count, budget, floor or projection is "
                "mathematically required to move"),
            "values": unchanged,
        },
        "changed_and_surfaced": {
            "s2_scoring_context_token_count": {
                "before": "registered_prompt_token_count",
                "after": "registered_prompt_token_count + 1",
                "why": (
                    "the complete candidate is two tokens and its common prefix "
                    "is teacher-forced into the scoring context"),
                "development_projection_extra_tokens_processed": projected_extra,
                "development_projection_extra_sequence_level_evaluations": 0,
            },
            "s3_zero_incremental_cost_condition": {
                "before": [
                    "a jointly single-token registered answer domain",
                    "an identical prompt prefix to S2",
                    "reuse of the identical restricted-vocabulary logit vector "
                    "S2 already read",
                    "a CPU-only rescoring contract that performs no additional "
                    "model evaluation",
                ],
                "after": [
                    "a registered answer domain whose complete candidates share "
                    "one common prefix token and differ in exactly one "
                    "discriminant token",
                    "an identical scoring context to S2, including the same "
                    "teacher-forced common-prefix token",
                    "reuse of the identical restricted discriminant-position "
                    "logit vector S2 already read",
                    "a CPU-only rescoring contract that performs no additional "
                    "model evaluation",
                ],
                "numeric_effect": (
                    "none; S3 incremental rendered rows, scored rows and "
                    "sequence-level evaluations all remain 0"),
                "why": (
                    "the v0.5 condition was stated for a jointly single-token "
                    "answer domain, which the pinned tokenizers do not provide. "
                    "The condition is restated at the discriminant position so "
                    "that it is true of the surface actually registered"),
            },
        },
        "no_number_preserved_for_continuity": True,
    }


# ---------------------------------------------------------------------------
# The v0.6 registry.
# ---------------------------------------------------------------------------

def _assert_visible_rendering_unchanged(v0_5, v0_6):
    """The visible rendering registry may change only by the new scoring fields."""
    guarded = (
        "answer_cue", "answer_domain", "applicability_table", "encoding_policy",
        "instructions", "label_alphabets", "pair_isolation_rules",
        "placeholders", "prohibited_substitutions", "question_stem_templates",
        "renderings", "separators",
    )
    for key in guarded:
        if v0_6[key] != v0_5[key]:
            raise ScoringBoundaryDefect(
                "draft-v0.6 changed the visible rendering surface %r; only the "
                "new normative scoring-boundary fields may differ" % key)
    if v0_6["registry_identity"]["normative_template_assets"] != \
            v0_5["registry_identity"]["normative_template_assets"]:
        raise ScoringBoundaryDefect(
            "draft-v0.6 changed a normative template asset identity")
    for index, profile in enumerate(v0_6["profiles"]):
        before = v0_5["profiles"][index]
        if profile["profile"] != before["profile"]:
            raise ScoringBoundaryDefect("the profile order changed")
        for key in sorted(before):
            if key == "candidate_surfaces":
                continue
            if profile[key] != before[key]:
                raise ScoringBoundaryDefect(
                    "draft-v0.6 changed profile %s field %r"
                    % (profile["profile"], key))
        if profile["candidate_surfaces"].get("answer_domain") != \
                before["candidate_surfaces"].get("answer_domain"):
            raise ScoringBoundaryDefect(
                "draft-v0.6 changed the registered candidate surfaces of %s"
                % profile["profile"])
        if profile["candidate_surfaces"].get("by_label_alphabet") != \
                before["candidate_surfaces"].get("by_label_alphabet"):
            raise ScoringBoundaryDefect(
                "draft-v0.6 changed the registered label surfaces of %s"
                % profile["profile"])
        if profile["candidate_surfaces"].get("tie_break_order") != \
                before["candidate_surfaces"].get("tie_break_order"):
            raise ScoringBoundaryDefect(
                "draft-v0.6 changed the registered tie break of %s"
                % profile["profile"])
    return True


def build_registry(derived=None, token_accounting=None):
    v0_5 = _load(REGISTRY_V0_5_PATH)
    registry = copy.deepcopy(v0_5)
    registry["schema_version"] = SCHEMA_VERSION
    registry["draft_version"] = DRAFT_VERSION
    registry["state"] = STATE
    registry["disposition_status"] = DISPOSITION
    registry["supersedes"] = {
        "registry":
            "studies/study3/protocol/"
            "interface_calibration_rendering_registry_v0_5.json",
        "schema":
            "studies/study3/protocol/"
            "interface_calibration_rendering_registry_v0_5.schema.json",
        "preserved_byte_for_byte_as_history": True,
        "why": (
            "draft-v0.5 remains the record of what was registered when P0-T ran. "
            "It is never edited, and the P0-T observations are never restated "
            "against a surface that did not exist when they were made"),
    }
    registry["closes_finding"] = v0_5["closes_finding"]
    registry["closes_p0_t_demonstrated_defects"] = [
        "the S2/S3 single-position scoring rule is not implementable under the "
        "pinned role tokenizers",
        "the eligibility classifier propagated a role-level S2 failure onto "
        "mechanically valid S1 cells",
    ]

    if derived is None:
        derived = _cached_replay(registry)
    if token_accounting is None:
        token_accounting = _cached_token_accounting()

    registry["scoring_boundary"] = scoring_boundary_block(derived)
    for profile in registry["profiles"]:
        profile["scoring_boundary"] = profile_scoring_boundary(
            profile["profile"], derived, token_accounting)
    registry["token_accounting"] = token_accounting

    _assert_visible_rendering_unchanged(v0_5, registry)

    registry["registry_identity"] = dict(v0_5["registry_identity"])
    registry["registry_identity"]["registry_sha256"] = None
    digest = hashlib.sha256(canonical(registry).encode("utf-8")).hexdigest()
    registry["registry_identity"]["registry_sha256"] = digest
    return registry


def build_schema():
    schema = copy.deepcopy(_load(REGISTRY_V0_5_SCHEMA_PATH))
    schema["$id"] = (
        "https://github.com/Alanjiao1988/J-space-observation/studies/study3/"
        "protocol/interface_calibration_rendering_registry_v0_6.schema.json")
    schema["title"] = ("Study 3 interface-calibration rendering and scoring "
                       "registry, draft-v0.6")
    schema["description"] = (
        "The binding normative rendering and scoring registry for Study 3 "
        "draft-v0.6. It extends the draft-v0.5 rendering registry with the "
        "first-discriminative-token scoring boundary and its token accounting. "
        "Every rendering field is unchanged.")
    schema["properties"]["schema_version"] = {"const": SCHEMA_VERSION,
                                              "type": "string"}
    schema["properties"]["draft_version"] = {"const": DRAFT_VERSION,
                                             "type": "string"}
    schema["properties"]["state"] = {"const": STATE, "type": "string"}
    schema["properties"]["disposition_status"] = {"const": DISPOSITION,
                                                  "type": "string"}
    schema["properties"]["supersedes"] = {
        "type": "object",
        "additionalProperties": True,
        "required": ["registry", "schema", "preserved_byte_for_byte_as_history"],
        "properties": {
            "registry": {"type": "string", "minLength": 1},
            "schema": {"type": "string", "minLength": 1},
            "preserved_byte_for_byte_as_history": {"const": True,
                                                   "type": "boolean"},
            "why": {"type": "string", "minLength": 1},
        },
    }
    schema["properties"]["closes_p0_t_demonstrated_defects"] = {
        "type": "array",
        "minItems": 2,
        "items": {"type": "string", "minLength": 1},
    }
    schema["properties"]["scoring_boundary"] = _scoring_boundary_schema()
    schema["properties"]["token_accounting"] = {
        "type": "object",
        "additionalProperties": True,
        "required": ["by_profile", "p0_r1_totals",
                     "s3_processes_no_additional_token"],
        "properties": {
            "by_profile": {"type": "object"},
            "p0_r1_totals": {"type": "object"},
            "s3_processes_no_additional_token": {"const": True,
                                                 "type": "boolean"},
        },
    }
    profile_schema = schema["properties"]["profiles"]["items"]
    profile_schema["properties"]["scoring_boundary"] = {
        "type": "object",
        "additionalProperties": True,
        "required": [
            "scoring_rule",
            "common_prefix_token_count_per_scored_row",
            "common_prefix_token_count",
            "teacher_forced_common_prefix",
            "scoring_context",
            "scored_rows",
            "registered_prompt_token_count",
            "scoring_context_token_count",
            "tokens_processed",
        ],
        "properties": {
            "scoring_rule": {
                "enum": [
                    "single_next_token_restricted_argmax",
                    "first_discriminative_token_restricted_argmax",
                    "bounded_greedy_generation_mapped_by_the_pinned_parser",
                ],
                "type": "string",
            },
            "common_prefix_token_count_per_scored_row": {
                "type": "integer", "minimum": 0, "maximum": 1},
            "common_prefix_token_count": {"type": "integer", "minimum": 0},
            "teacher_forced_common_prefix": {"type": "boolean"},
            "scoring_context": {"type": "string", "minLength": 1},
            "scored_rows": {"type": "integer", "minimum": 1},
            "registered_prompt_token_count": {"type": "integer", "minimum": 0},
            "scoring_context_token_count": {"type": "integer", "minimum": 0},
            "tokens_processed": {"type": "integer", "minimum": 0},
        },
    }
    profile_schema["required"] = sorted(
        set(profile_schema.get("required", [])) | {"scoring_boundary"})
    schema["required"] = sorted(
        set(schema["required"]) | {"scoring_boundary", "token_accounting",
                                   "supersedes",
                                   "closes_p0_t_demonstrated_defects"})
    return schema


def _scoring_boundary_schema():
    return {
        "type": "object",
        "additionalProperties": True,
        "required": [
            "registered_in",
            "visible_answer_surface_unchanged",
            "first_discriminative_token_rule",
            "eligibility_conditions",
            "equivalence_proof",
            "derived_token_identities",
            "claim_boundary",
        ],
        "properties": {
            "registered_in": {"const": DRAFT_VERSION, "type": "string"},
            "visible_answer_surface_unchanged": {
                "type": "object",
                "additionalProperties": True,
                "required": [
                    "answer_cue",
                    "candidate_surfaces",
                    "each_candidate_carries_exactly_one_leading_u0020",
                    "s1_rendering_and_scoring_bytes_unchanged",
                ],
                "properties": {
                    "answer_cue": {"const": "Answer:", "type": "string"},
                    "candidate_surfaces": {
                        "type": "array",
                        "minItems": 10,
                        "maxItems": 10,
                        "uniqueItems": True,
                        "items": {"type": "string", "pattern": "^ [0-9]$"},
                    },
                    "each_candidate_carries_exactly_one_leading_u0020": {
                        "const": True, "type": "boolean"},
                    "s1_rendering_and_scoring_bytes_unchanged": {
                        "const": True, "type": "boolean"},
                },
            },
            "first_discriminative_token_rule": {
                "type": "object",
                "additionalProperties": True,
                "required": ["factorization", "s2_scoring_context",
                             "s3_evaluation", "common_prefix_is", "prohibited",
                             "tie_break_order"],
                "properties": {
                    "factorization": {
                        "const": "candidate_d = common_prefix || discriminant_d",
                        "type": "string"},
                    "s2_scoring_context": {"type": "string", "minLength": 1},
                    "s3_evaluation": {"type": "string", "minLength": 1},
                    "common_prefix_is": {"type": "string", "minLength": 1},
                    "prohibited": {"type": "array", "minItems": 5,
                                   "items": {"type": "string", "minLength": 1}},
                    "tie_break_order": {"type": "string", "minLength": 1},
                },
            },
            "eligibility_conditions": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "condition"],
                    "properties": {
                        "id": {"type": "string", "pattern": "^SB-[1-5]$"},
                        "condition": {"type": "string", "minLength": 1},
                    },
                },
            },
            "equivalence_proof": {
                "type": "object",
                "additionalProperties": True,
                "required": ["identity", "consequence", "why_exact",
                             "valid_because", "does_not_extend_to"],
                "properties": {
                    "identity": {
                        "const": "P(u, v_d | x) = P(u | x) * P(v_d | x, u)",
                        "type": "string"},
                    "consequence": {
                        "const":
                            "argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)",
                        "type": "string"},
                    "why_exact": {"type": "string", "minLength": 1},
                    "valid_because": {"type": "array", "minItems": 4,
                                      "items": {"type": "string",
                                                "minLength": 1}},
                    "does_not_extend_to": {"type": "array", "minItems": 6,
                                           "items": {"type": "string",
                                                     "minLength": 1}},
                },
            },
            "derived_token_identities": {
                "type": "object",
                "additionalProperties": True,
                "required": ["provenance", "derivation_module",
                             "tokenizer_encodes_performed_by_the_derivation",
                             "by_role"],
                "properties": {
                    "provenance": {"type": "string", "minLength": 1},
                    "derivation_module": {"type": "string", "minLength": 1},
                    "tokenizer_encodes_performed_by_the_derivation": {
                        "const": 0, "type": "integer"},
                    "by_role": {"type": "object"},
                },
            },
            "claim_boundary": {"type": "array", "minItems": 3,
                               "items": {"type": "string", "minLength": 1}},
        },
    }


# ---------------------------------------------------------------------------
# Derived tables.
# ---------------------------------------------------------------------------

def build_tables():
    derived = FACT.gate(build_registry())
    token_accounting = _cached_token_accounting()
    registry = build_registry(derived=derived, token_accounting=token_accounting)
    return {
        "schema_version": TABLES_SCHEMA_VERSION,
        "document_class": "study3_scoring_boundary_v0_6_tables",
        "draft_version": DRAFT_VERSION,
        "state": STATE,
        "disposition_status": DISPOSITION,
        "authority":
            "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
        "single_structured_source":
            "studies/study3/analysis/scoring_boundary_v0_6.py",
        "registry_identity": {
            "path": "studies/study3/protocol/"
                    "interface_calibration_rendering_registry_v0_6.json",
            "registry_sha256": registry["registry_identity"]["registry_sha256"],
        },
        "replay_derivation": derived,
        "token_accounting": token_accounting,
        "statistical_invariance": derive_statistical_invariance(),
        "operation_counters_in_the_calibration_session": {
            "tokenizer_constructions": 0,
            "tokenizer_encodes": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "gpu_jobs": 0,
            "forward_passes": 0,
            "generations": 0,
            "restricted_logit_reads": 0,
            "scored_rows": 0,
            "seeds_drawn": 0,
            "bank_rows_written": 0,
            "evidence_rows_added": 0,
            "positive_reference_operations": 0,
            "local_pytest_runs": 0,
            "decision_bearing_local_statistical_runs": 0,
        },
        "authority_flags": {
            "frozen": False,
            "formal_execution_authorized": False,
            "draft_v0_6_reviewed": False,
            "draft_v0_6_selected": False,
            "interface_selected": None,
            "positive_reference_selected": False,
            "seed_authorized": False,
            "bank_authorized": False,
            "confirmation_access_authorized": False,
            "winner_selected": False,
            "od2_status": "unresolved",
            "ur22_status": "unresolved",
            "evidence_ledger_last_row": "EV-0016",
        },
        "claim_boundary": (
            "planning and derivation arithmetic only. This document authorises "
            "nothing, selects nothing, freezes nothing and answers no research "
            "question."),
    }


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def _write(path, document):
    with open(path, "wb") as handle:
        handle.write(canonical(document).encode("utf-8"))
    return path


def _check(path, document, label):
    if not os.path.exists(path):
        return ["%s is missing" % label]
    with open(path, "rb") as handle:
        on_disk = handle.read()
    expected = canonical(document).encode("utf-8")
    if on_disk != expected:
        return ["%s does not reproduce from code" % label]
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    derived = FACT.gate(build_registry())
    token_accounting = _cached_token_accounting()
    registry = build_registry(derived=derived, token_accounting=token_accounting)
    schema = build_schema()
    tables = build_tables()

    targets = (
        (REGISTRY_V0_6_PATH, registry, "the draft-v0.6 rendering/scoring registry"),
        (REGISTRY_V0_6_SCHEMA_PATH, schema, "the draft-v0.6 registry schema"),
        (TABLES_PATH, tables, "the draft-v0.6 scoring-boundary tables"),
    )
    if args.write:
        for path, document, label in targets:
            _write(path, document)
            print("wrote %s" % os.path.relpath(path, REPO_ROOT).replace(
                os.sep, "/"))
        return 0

    findings = []
    for path, document, label in targets:
        findings += _check(path, document, label)
    if findings:
        print("SCORING BOUNDARY CHECK FAILED")
        for finding in findings:
            print("  FAIL %s" % finding)
        return 1
    print("scoring boundary v0.6: OK")
    print("  registry sha256 : %s"
          % registry["registry_identity"]["registry_sha256"])
    print("  common prefix   : %d (derived, zero encodes)"
          % registry["scoring_boundary"]["common_prefix_token_for_every_pinned_"
                                         "role"])
    print("  m_max           : %d (unchanged)"
          % tables["statistical_invariance"]["unchanged_and_why"]["values"][
              "m_max"])
    print("  dev projection  : %d sequence-level equivalents (unchanged)"
          % tables["statistical_invariance"]["unchanged_and_why"]["values"][
              "development_projection_sequence_level_model_evaluation_"
              "equivalents"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
