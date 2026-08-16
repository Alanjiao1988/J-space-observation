#!/usr/bin/env python3
"""Build the self-contained Study 3 draft-v0.7 normative bundle.

Authorities:
``studies/study3/prompts/study3_v0_7_copy_on_write_protocol_successor_authority.md``
(binding) and
``studies/study3/prompts/study3_v0_7_consolidated_amendment_authority.md``.

The operator selected ``OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL``. The legacy
v0.5 protocol trio stays byte-exact because the immutable P0 corpus manifest
byte-binds the JSON; this module writes a **new** versioned bundle beside it.

The v0.7 protocol is *derived*, not copied. Every legacy top-level key is
carried forward from the immutable v0.5 JSON so the result is self-contained
and an executor never has to layer v0.5, v0.6 and v0.7 by hand; the v0.6
scoring boundary is imported from the registered v0.6 registry; and every
numeric constant is read from the committed design-statistics tables rather
than transcribed.

``--write`` emits the bundle. ``--check`` regenerates it in memory and refuses
if a single committed byte differs, so the published bundle can never drift
from its generator.

CPU-only, deterministic, standard library only. No tokenizer, checkpoint,
model, GPU, network, cloud, seed, bank or evidence operation.
"""

from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
STUDY3 = HERE.parent
REPO_ROOT = STUDY3.parent.parent

PROTOCOL_DIR = STUDY3 / "protocol"
REVIEWS_DIR = STUDY3 / "reviews"

LEGACY_JSON = PROTOCOL_DIR / "interface_calibration_protocol_draft.json"
LEGACY_MD = PROTOCOL_DIR / "interface_calibration_protocol_draft.md"
LEGACY_SCHEMA = PROTOCOL_DIR / "interface_calibration_protocol.schema.json"
REGISTRY_V0_6 = PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_6.json"
DESIGN_TABLES = HERE / "design_statistics_tables.json"

V0_7_JSON = PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.json"
V0_7_MD = PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.md"
V0_7_SCHEMA = PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.schema.json"
V0_7_REGISTRY = PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_7.json"
V0_7_REGISTRY_SCHEMA = (PROTOCOL_DIR
                        / "interface_calibration_rendering_registry_v0_7.schema.json")
CURRENT_POINTER = PROTOCOL_DIR / "interface_calibration_protocol_current.json"
CURRENT_POINTER_SCHEMA = (PROTOCOL_DIR
                          / "interface_calibration_protocol_current.schema.json")

AMENDMENT_MD = REVIEWS_DIR / "v0_7_operator_amendment.md"
AMENDMENT_JSON = REVIEWS_DIR / "v0_7_operator_amendment.json"
AMENDMENT_SCHEMA = REVIEWS_DIR / "v0_7_operator_amendment.schema.json"

SCHEMA_VERSION = "study3-interface-calibration-protocol-draft-v0.7"
REGISTRY_SCHEMA_VERSION = "study3-interface-calibration-rendering-registry-v0.7"
POINTER_SCHEMA_VERSION = "study3-interface-calibration-protocol-current-v0.7"
AMENDMENT_SCHEMA_VERSION = "study3-v0-7-operator-amendment"

DRAFT_VERSION = "draft-v0.7"
STATE = ("STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_7_"
         "COMPLETE_AWAITING_SINGLE_FOCUSED_METHODS_REVIEW")
LEGACY_STATUS = "HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL"

SUCCESSOR_AUTHORITY = ("studies/study3/prompts/"
                       "study3_v0_7_copy_on_write_protocol_successor_authority.md")
ORIGINAL_AUTHORITY = ("studies/study3/prompts/"
                      "study3_v0_7_consolidated_amendment_authority.md")
PLACEMENT_PROBE = "studies/study3/analysis/v0_7_protocol_placement_probe.py"
PROBE_OUTPUT = "studies/study3/analysis/v0_7_protocol_placement_probe.json"
TERMINAL_DISPOSITION = ("studies/study3/reviews/"
                        "v0_7_terminal_operator_decision_required.md")

#: Section 2 of the successor authority. Verified, never rewritten.
LEGACY_TRIO = {
    "studies/study3/protocol/interface_calibration_protocol_draft.json":
        "1197e08779f6360a50effeafa8035d9b1d21c0a3b038ecc7cbc0930be03c7ca7",
    "studies/study3/protocol/interface_calibration_protocol_draft.md":
        "0376c7d5c659fe5535a216b614b6430499c7df235abcf52561dc8f075613b23f",
    "studies/study3/protocol/interface_calibration_protocol.schema.json":
        "79a8a68a51c686014f2cfe5c8cf4e782b01fc270cf3c9ae5739964abbe4c30c4",
}

#: The prohibited active-claim vocabulary, tested by mutation.
PROHIBITED_LANGUAGE = (
    "robust to prompt format",
    "template-independent",
    "format-insensitive",
    "single forward pass",
    "one forward pass",
    "no intermediate computation",
    "proves reasoning was absent",
    "distillation caused the mechanism",
    "对提示格式稳健",
    "与模板无关",
    "对格式不敏感",
)

#: Every decision-bearing marker. The Markdown companion must carry each one
#: exactly once, and each must resolve to a real path in the protocol JSON.
DECISIONS = (
    ("V07-D01", "Dual estimands E0 and D0, and the claim ceiling",
     "estimands_v0_7"),
    ("V07-D02", "E0 answer surfaces, parser and decoding contract",
     "e0_answer_and_decoding_contract"),
    ("V07-D03", "Full-context tokenization and D0 diagnostics",
     "full_context_tokenization_and_d0_diagnostics"),
    ("V07-D04", "The registered I1a/I1b/I2 competence-floor battery is retained",
     "competence_floor_battery_v0_7"),
    ("V07-D05", "Wrapper-only matched contrast and joint adequacy",
     "wrapper_matched_contrast_v0_7"),
    ("V07-D06", "Canonical generated-CoT ceiling",
     "generated_cot_ceiling_v0_7"),
    ("V07-D07", "Q0 prequalification and the RP-B ladder",
     "q0_and_rp_b_v0_7"),
    ("V07-D08", "RP-B and RP-M are separate constructs",
     "rp_b_and_rp_m_separation_v0_7"),
    ("V07-D09", "Per-checkpoint functional equivalence",
     "checkpoint_functional_equivalence_v0_7"),
    ("V07-D10", "Engineering shakedown authority and its numeric bounds",
     "engineering_shakedown_authority_v0_7"),
    ("V07-D11", "Recursive-manifest seal",
     "recursive_manifest_seal_v0_7"),
    ("V07-D12", "Activation and causal-claim boundary",
     "activation_and_causal_claim_boundary_v0_7"),
    ("V07-D13", "Copy-on-write protocol placement",
     "protocol_placement_v0_7"),
    ("V07-D14", "Deterministically deferred values and their fail-closed states",
     "deterministic_deferrals_v0_7"),
)


class BuildDefect(Exception):
    """The v0.7 bundle could not be built honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _read_json(path: Path):
    return json.loads(path.read_bytes().decode("utf-8"))


def _file_identity(path: Path) -> dict:
    payload = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }


def verify_legacy_trio() -> dict:
    observed = {}
    for relative, expected in sorted(LEGACY_TRIO.items()):
        payload = (REPO_ROOT / relative).read_bytes()
        digest = _sha256(payload)
        if digest != expected:
            raise BuildDefect(
                "%s is sha256 %s, not the registered %s; the legacy bundle must "
                "stay byte-exact" % (relative, digest, expected))
        observed[relative] = {"bytes": len(payload), "sha256": digest,
                              "status": LEGACY_STATUS}
    return observed


# ---------------------------------------------------------------------------
# Statistics, read from the committed tables rather than transcribed
# ---------------------------------------------------------------------------

def statistics() -> dict:
    tables = _read_json(DESIGN_TABLES)
    power = tables["power_architecture"]

    def rows(section):
        out = {}
        for row in tables[section]:
            key = "+".join(row["gates"])
            out[key] = {
                "gates": list(row["gates"]),
                "p0_exact_rational": row["p0_exact_rational"],
                "p1_exact_rational": row["p1_exact_rational"],
                "alpha_exact_rational": row["alpha_exact_rational"],
                "n": row["n"],
                "pass_count": row["pass_count"],
                "unit_of_n": row["unit_of_n"],
                "exact_null_tail_at_p0": row["exact_null_tail_at_p0"],
                "exact_power_at_p1": row["exact_power_at_p1"],
                "pass_count_is_minimal_at_alpha":
                    row["pass_count_is_minimal_at_alpha"],
            }
        return out

    development = rows("development_exact_binomial_components")
    confirmation = rows("confirmation_exact_binomial_components")
    if set(development) != {"I1a+I1b+I3", "I2", "I4"}:
        raise BuildDefect("the development component families changed")
    return {
        "source": "studies/study3/analysis/design_statistics_tables.json",
        "regenerated_by": "studies/study3/analysis/design_statistics.py --check",
        "development_components": development,
        "confirmation_components": confirmation,
        "power_architecture": {
            "m_max": power["m_max"],
            "s4_excluded_from_m_max": power["s4_excluded_from_m_max"],
            "per_cell_false_negative_budget_exact_rational":
                power["per_cell_false_negative_budget_exact_rational"],
            "per_cell_power_target_exact_rational":
                power["per_cell_power_target_exact_rational"],
            "per_stage_profile_false_negative_budget_exact_rational":
                power["per_stage_profile_false_negative_budget_exact_rational"],
            "profile_stage_power_floor_exact_rational":
                power["profile_stage_power_floor_exact_rational"],
            "study_end_to_end_power_floor_exact_rational":
                power["study_end_to_end_power_floor_exact_rational"],
            "panel_false_qualification_budget_exact_rational":
                power["panel_false_qualification_budget_exact_rational"],
            "uses_independence": power["uses_independence"],
            "holds_under_arbitrary_dependence":
                power["holds_under_arbitrary_dependence"],
        },
        "gate_bearing_cell_counts": tables["gate_bearing_cell_counts"],
        "battery_is_unchanged_from_v0_5": True,
        "new_mde_registered": False,
    }


def derived_constants(stats: dict) -> dict:
    """Every new v0.7 numeric constant, each derived from a registered value."""
    i1 = stats["development_components"]["I1a+I1b+I3"]
    i2 = stats["development_components"]["I2"]

    p0_i1 = Fraction(i1["p0_exact_rational"])
    p1_i1 = Fraction(i1["p1_exact_rational"])
    registered_gap = p1_i1 - p0_i1               # 97/100 - 9/10 = 7/100
    restricted_chance = Fraction(1, 10)          # ten registered surfaces
    negative_control_bound = restricted_chance + registered_gap

    e0_answer_tokens = 2                          # every surface is [220, digit]
    e0_eos_margin = 1
    return {
        "registered_alternative_gap_exact_rational": str(registered_gap),
        "registered_alternative_gap_derivation":
            "p1 - p0 for the registered I1a/I1b/I3 floor, %s - %s"
            % (i1["p1_exact_rational"], i1["p0_exact_rational"]),
        "restricted_chance_level_exact_rational": str(restricted_chance),
        "restricted_chance_level_derivation":
            "one over the ten registered candidate surfaces",
        "negative_control_equivalence_upper_bound_exact_rational":
            str(negative_control_bound),
        "negative_control_equivalence_derivation":
            "restricted chance level plus the registered alternative gap; a "
            "negative control passes only when its exact one-sided upper "
            "confidence bound at the registered development alpha lies strictly "
            "below this value. 'not significantly above chance' is not accepted",
        "wrapper_descriptive_bandwidth_exact_rational": str(registered_gap),
        "wrapper_descriptive_bandwidth_derivation":
            "the same registered alternative gap; a paired risk difference wider "
            "than the distance between the null floor and the lowest alternative "
            "of interest triggers the fixed limitation paragraph. The trigger has "
            "no gate effect",
        "generated_cot_ceiling_theta_exact_rational": i2["p0_exact_rational"],
        "generated_cot_ceiling_p1_exact_rational": i2["p1_exact_rational"],
        "generated_cot_ceiling_alpha_exact_rational": i2["alpha_exact_rational"],
        "generated_cot_ceiling_n": i2["n"],
        "generated_cot_ceiling_pass_count": i2["pass_count"],
        "generated_cot_ceiling_derivation":
            "the ceiling is a task-headroom gate, so it reuses the registered "
            "I2 primitive-headroom construct exactly: same null, same lowest "
            "alternative of interest, same alpha, same exact one-sided binomial, "
            "same regenerated n and pass count. No new MDE is introduced",
        "generated_cot_ceiling_k": 1,
        "generated_cot_ceiling_k_derivation":
            "k = 1 with deterministic decoding. Exactly one estimand is therefore "
            "registered before data and the pass@1 versus majority-vote@k choice "
            "cannot arise at execution time. Majority-vote@k is NOT registered",
        "generated_cot_ceiling_aggregation":
            "per_item_single_response_full_sequence_exact_match",
        "e0_answer_token_count": e0_answer_tokens,
        "e0_eos_margin_tokens": e0_eos_margin,
        "e0_max_new_tokens": e0_answer_tokens + e0_eos_margin,
        "e0_max_new_tokens_derivation":
            "every registered surface is exactly two tokens under the pinned "
            "role tokenizers, plus a one-token EOS margin",
        "s4_generated_token_bound_per_generation": 16,
        "s4_bound_is_unchanged": True,
        "reproducibility_tolerance": 0,
        "reproducibility_criterion":
            "byte-exact. Every decision-bearing artifact must reproduce with an "
            "identical SHA-256 under the sealed recursive manifest. The decision "
            "statistic is an integer exact-match count, so no floating-point "
            "tolerance is registered and none may be introduced",
    }


def shakedown_limits() -> dict:
    """Engineering budget only. No scientific content, no gate effect."""
    return {
        "max_fix_and_rerun_cycles": 3,
        "max_attempts_per_cycle": 1,
        "max_total_attempts": 3,
        "max_wall_clock_minutes": 240,
        "max_cpu_core_hours": 16,
        "max_gpu_hours": 0,
        "max_cloud_jobs": 6,
        "budget_class": "ENGINEERING_ONLY_NO_SCIENTIFIC_CONTENT",
        "affects_any_estimand_threshold_or_gate": False,
        "rationale":
            "these are engineering ceilings on a mechanical shakedown, not "
            "scientific parameters. They bound attempts, time, compute and cloud "
            "jobs so a shakedown cannot silently become an experiment. "
            "max_gpu_hours is zero because the whitelist covers mechanical "
            "defects only; a GPU need is outside shakedown authority",
        "whitelist": [
            "environment and dependency defects",
            "container and runtime launch defects",
            "I/O and path defects",
            "crashes before decision-bearing output",
            "logging, receipt or manifest completeness defects",
            "renderer, tokenizer or scorer mechanical defects detected by "
            "registered fixtures",
            "trivial-copy and negative-control pipeline checks",
        ],
        "outside_authority": [
            "estimand", "interface", "threshold", "item bank", "answer surface",
            "candidate ladder", "task definition", "gate logic",
        ],
        "outside_authority_state": "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED",
        "disjoint_from_formal_calibration_authority": True,
        "runs_in_this_authoring_session": False,
    }


def deferrals() -> dict:
    """Values that legitimately cannot exist before the pre-execution seal.

    Section 7 of the original authority permits freezing **or deterministically
    deferring** every execution value. Each entry below carries a deterministic
    acquisition rule and an explicit fail-closed absent state, and none is a
    ``TBD`` or an operator-discretion clause.
    """
    return {
        "policy": "every entry has a deterministic acquisition rule and a "
                  "fail-closed absent state; none may be resolved at execution "
                  "time by operator discretion",
        "tbd_permitted": False,
        "entries": [
            {
                "id": "DEFER-01",
                "value": "immutable checkpoint revision hashes",
                "acquisition_rule":
                    "populated only by the later pre-execution seal, by resolving "
                    "each registered repository identity to its immutable "
                    "revision and recording the revision hash in the recursive "
                    "manifest",
                "fail_closed_absent_state":
                    "STUDY3_V0_7_CHECKPOINT_REVISION_UNSEALED",
                "may_default": False,
            },
            {
                "id": "DEFER-02",
                "value": "RP-B ladder membership and its length L",
                "acquisition_rule":
                    "the eligibility predicate and the ordering rule are frozen "
                    "here; the concrete ladder is enumerated at the pre-execution "
                    "seal by applying them to the registered candidate families, "
                    "and L is the resulting count. The ladder is sealed before any "
                    "Q0 development result is observed, and the candidate-level "
                    "Bonferroni allocation is the registered study development "
                    "screening alpha divided by that sealed L",
                "fail_closed_absent_state":
                    "STUDY3_V0_7_RP_B_LADDER_UNSEALED",
                "may_default": False,
                "blocked_on": "OD2",
            },
            {
                "id": "DEFER-03",
                "value": "canonical generated-CoT maximum generation length",
                "acquisition_rule":
                    "per item, the largest length the sealed checkpoint's "
                    "registered context window permits after the rendered prompt "
                    "and the registered EOS margin. A ceiling must never truncate, "
                    "because a truncation artifact would be indistinguishable from "
                    "absent headroom; the maximum is therefore the most permissive "
                    "value the context allows, computed deterministically and "
                    "recorded per item in the seal",
                "fail_closed_absent_state":
                    "CANONICAL_COT_CEILING_CONTEXT_WINDOW_UNAVAILABLE",
                "may_default": False,
            },
        ],
    }


# ---------------------------------------------------------------------------
# The v0.7 normative blocks
# ---------------------------------------------------------------------------

def estimands_block() -> dict:
    return {
        "E0": {
            "id": "E0_zero_generated_reasoning_token_expressed_competence",
            "role": "primary",
            "meaning": "the model actually emits a correct registered answer "
                       "surface without emitting generated reasoning or "
                       "rationale tokens",
            "is_headline_expressed_competence_endpoint": True,
            "is_primary_behavioral_endpoint": True,
            "is_the_expressed_competence_component_of_q0": True,
            "is_the_primary_gate_for_rp_b": True,
            "establishes_absence_of_internal_computation": False,
            "answer_token_autoregression_is_part_of_the_estimand": True,
            "prohibited_descriptions": [
                "one forward pass",
                "single forward pass",
                "no intermediate computation",
                "proof that reasoning was absent",
            ],
        },
        "D0": {
            "id": "D0_single_forward_decodability",
            "role": "secondary_conditional_mechanism_claim",
            "permitted_claim": "Under the frozen counterfactual readout, "
                               "discriminant information was decodable from one "
                               "registered logit read.",
            "covers_only_the_registered_discriminant": True,
            "covers_the_complete_answer": False,
            "establishes_natural_expression": False,
            "establishes_behavioral_competence": False,
            "establishes_causal_use": False,
            "enters_q0": False,
            "enters_the_rp_b_gate": False,
            "reported_separately_from_e0": True,
            "single_forward_phrase_permitted_only_here": True,
        },
        "claim_ceiling": {
            "e0_and_d0_are_distinct_and_never_merged": True,
            "d0_alone_can_never_qualify_a_candidate": True,
            "no_universal_statement_over_all_checkpoints_or_interfaces": True,
        },
    }


def e0_contract(constants: dict, registry_identity: dict) -> dict:
    return {
        "frozen_before_any_model_result": True,
        "legal_answer_surfaces_per_item": {
            "surfaces": [" %d" % d for d in range(10)],
            "count": 10,
            "leading_code_point": "U+0020",
            "source": "the registered v0.7 rendering registry",
            "registry": registry_identity,
        },
        "normalization_policy":
            "none. The emitted byte sequence is compared to the registered "
            "surface without stripping, casefolding, unicode normalization or "
            "whitespace collapse",
        "complete_token_id_sequence_per_surface_and_revision": {
            "rule": "recorded per registered surface and per immutable "
                    "checkpoint revision in the pre-execution seal",
            "structure": "[common_prefix_token, discriminant_token]",
            "token_count_per_surface": constants["e0_answer_token_count"],
            "deferred_to": "DEFER-01",
        },
        "eos_and_stop_semantics": {
            "eos_margin_tokens": constants["e0_eos_margin_tokens"],
            "max_new_tokens": constants["e0_max_new_tokens"],
            "derivation": constants["e0_max_new_tokens_derivation"],
            "stopping_criteria": "registered EOS id set only; no string stop",
        },
        "matching_rule": {
            "kind": "full_sequence_exact_match",
            "prefix_match_permitted": False,
            "example_incorrect_output": "7 because...",
            "example_rule": "incorrect unless the complete emitted sequence is "
                            "itself a frozen legal surface",
        },
        "invalid_output_treatment": {
            "unparseable_is_incorrect": True,
            "out_of_domain_is_incorrect": True,
            "dropping_permitted": False,
            "denominator_never_shrinks": True,
        },
        "decoding_configuration": {
            "do_sample": False,
            "do_sample_is_the_actual_deterministic_switch": True,
            "temperature_alone_is_never_the_switch": True,
            "sampling_only_parameters_recorded_inactive": {
                "temperature": "INACTIVE_do_sample_false",
                "top_p": "INACTIVE_do_sample_false",
                "top_k": "INACTIVE_do_sample_false",
                "typical_p": "INACTIVE_do_sample_false",
            },
            "num_beams": 1,
            "batch_size": 1,
            "padding_side": "left",
            "reproducibility_tolerance": constants["reproducibility_tolerance"],
            "reproducibility_criterion": constants["reproducibility_criterion"],
        },
        "parser": {
            "id": "e0_parser_v0_7",
            "separate_object_from_the_ceiling_parser": True,
            "rejects": ["prefix matches", "rationale suffixes",
                        "unparseable output", "unregistered surfaces"],
            "implementation_hash_deferred_to": "DEFER-01",
        },
    }


def tokenization_block() -> dict:
    return {
        "full_context_rule": "rendered_prompt_bytes + candidate_surface_bytes",
        "candidate_only_encoding_permitted": False,
        "verified_per_candidate_and_revision": [
            "bytes",
            "complete token IDs",
            "common prefix",
            "discriminant position",
            "reconstruction and round-trip requirements",
            "equality between the IDs actually supplied to scoring and the "
            "independently computed full-string encoding",
        ],
        "d0_diagnostics": {
            "always_reported": True,
            "descriptive_only": True,
            "quantities": [
                "restricted accuracy",
                "full-vocabulary answer-set probability mass",
                "complete candidate joint log-likelihood",
                "full-vocabulary rank",
                "short-generation and E0 validity",
            ],
            "uncalibrated_probability_mass_threshold_registered": False,
            "may_rescue_a_failed_e0_gate": False,
            "enters_any_gate": False,
        },
    }


def competence_battery(stats: dict) -> dict:
    return {
        "battery": ["I1a", "I1b", "I2"],
        "retained_unchanged": True,
        "replaced_by_a_new_mde": False,
        "four_hundred_cluster_mde_registered": False,
        "component_test": "exact one-sided binomial against the registered null",
        "development_components": stats["development_components"],
        "confirmation_components": stats["confirmation_components"],
        "power_architecture": stats["power_architecture"],
        "gate_bearing_cell_counts": stats["gate_bearing_cell_counts"],
        "alpha_allocation":
            "1/600 per applicable atomic development cell, unchanged",
        "changing_the_null_or_floor_requires":
            "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED",
        "regenerated_not_transcribed": True,
        "source": stats["source"],
    }


def wrapper_block(constants: dict, registry_identity: dict) -> dict:
    return {
        "comparison_is_within_role": True,
        "arms": ["registered_common_raw_wrapper", "role_canonical_wrapper"],
        "rl_has_no_canonical_chat_template": True,
        "rl_registered_wrapper":
            "deterministic few-shot completion-format wrapper",
        "chat_versus_raw_is_the_same_intervention_across_roles": False,
        "gate": {
            "kind": "joint_adequacy",
            "conditions": [
                "raw rendering meets its competence floor",
                "role-canonical rendering meets its competence floor",
            ],
            "registers_a_template_effect_claim": False,
            "registers_an_equivalence_claim": False,
            "registers_an_invariance_claim": False,
        },
        "descriptive_reporting": {
            "paired_discordance": "always reported",
            "risk_difference": "always reported",
            "irrespective_of_magnitude_or_direction": True,
            "bandwidth_exact_rational":
                constants["wrapper_descriptive_bandwidth_exact_rational"],
            "bandwidth_derivation":
                constants["wrapper_descriptive_bandwidth_derivation"],
            "trigger_has_gate_effect": False,
            "fixed_limitation_paragraph":
                "The two registered renderings met their competence floors. The "
                "observed paired risk difference exceeded the registered "
                "descriptive bandwidth. This is reported descriptively; it "
                "licenses no claim of template effect, equivalence or "
                "invariance, and it has no effect on any gate.",
        },
        "permitted_positive_wording":
            "both registered renderings met their competence floors",
        "prohibited_wording": list(PROHIBITED_LANGUAGE[:3]) + [
            "对提示格式稳健", "与模板无关", "对格式不敏感"],
        "registry": registry_identity,
    }


def cot_ceiling_block(constants: dict) -> dict:
    return {
        "is_an_execution_precondition_gate": True,
        "is_an_interface_selector": False,
        "is_s4": False,
        "s4_remains_a_short_answer_only_generation_diagnostic": True,
        "s4_generated_token_bound_per_generation":
            constants["s4_generated_token_bound_per_generation"],
        "s4_is_ever_selectable": False,
        "frozen": {
            "canonical_route": "the role-canonical wrapper registered for the "
                               "target role in the v0.7 rendering registry",
            "route_marker_required": "<think>",
            "route_marker_is_required": True,
            "do_sample": False,
            "temperature": "INACTIVE_do_sample_false",
            "top_p": "INACTIVE_do_sample_false",
            "num_beams": 1,
            "k": constants["generated_cot_ceiling_k"],
            "k_derivation": constants["generated_cot_ceiling_k_derivation"],
            "seed_policy": "no seed is drawn; decoding is deterministic and "
                           "do_sample is false",
            "maximum_generation_length_rule":
                "deterministic per item, see DEFER-03",
            "batch_size": 1,
            "padding_side": "left",
            "parser": {
                "id": "cot_ceiling_parser_v0_7",
                "separate_object_from_the_e0_parser": True,
                "unparseable_is_incorrect": True,
                "dropping_permitted": False,
            },
            "item_level_aggregation":
                constants["generated_cot_ceiling_aggregation"],
            "theta_exact_rational":
                constants["generated_cot_ceiling_theta_exact_rational"],
            "p1_exact_rational":
                constants["generated_cot_ceiling_p1_exact_rational"],
            "alpha_exact_rational":
                constants["generated_cot_ceiling_alpha_exact_rational"],
            "n": constants["generated_cot_ceiling_n"],
            "pass_count": constants["generated_cot_ceiling_pass_count"],
            "theta_derivation": constants["generated_cot_ceiling_derivation"],
            "checkpoint_or_family_decision_granularity":
                "per immutable checkpoint revision",
            "exact_scope_of_a_failure":
                "the target route of that checkpoint revision only",
            "inferential_unit": "item",
            "reproducibility_tolerance": constants["reproducibility_tolerance"],
        },
        "statistical_unit_is_the_item": True,
        "n_times_k_responses_treated_as_independent_items": False,
        "majority_vote_at_k_registered": False,
        "failure_state": "NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE",
        "a_pass_establishes": "generated-CoT task competence only",
        "a_pass_or_failure_says_about_zero_generated_reasoning_token_competence":
            "nothing by itself",
        "can_select_an_interface": False,
        "is_outside_the_interface_selection_multiplicity_family": True,
        "does_not_change_m_max": True,
    }


def q0_rp_b_block(stats: dict) -> dict:
    return {
        "q0_is_a_one_way_prequalification_layer": True,
        "q0_pass_is_interpretable": True,
        "q0_failure_is_evidence_the_interface_is_invalid": False,
        "q0_failure_is_evidence_the_construct_does_not_exist": False,
        "q0_must_contain_an_e0_expressed_competence_component": True,
        "d0_alone_can_qualify_a_candidate": False,
        "ladder": {
            "registered_before_any_q0_development_result": True,
            "ordering_rule": "parameter count ascending; publication time as the "
                             "sole tie-break; both are predeclared observable "
                             "metadata",
            "result_informed_ordering_permitted": False,
            "priority": "same-tokenizer natural candidates first, including the "
                        "predeclared Qwen-family size ladder where eligible",
            "eligibility_predicate": [
                "pinned repository identity and immutable revision hash",
                "license permitting research use and redistribution of derived "
                "measurements",
                "not qualified, tuned or selected on the Study 3 confirmation "
                "bank",
                "runnable on the registered route",
                "natural model, not a training-constructed implicit-CoT or "
                "direct-answer model",
            ],
            "fallback_stratum": {
                "population": "training-constructed implicit-CoT or "
                              "direct-answer models",
                "separately_identified": True,
                "claim_ceiling": "the isomorphic interface construction is valid",
                "prohibited_claim": "the exact RT byte interface is valid",
            },
            "length_L_deferred_to": "DEFER-02",
            "blocked_on": "OD2",
        },
        "splits": {
            "development_and_confirmation_are_physically_item_disjoint": True,
            "development_and_confirmation_are_logically_item_disjoint": True,
            "confirmation_frozen_before_development_access": True,
            "confirmation_attempts_per_candidate": 1,
            "tuning_after_confirmation_failure_permitted": False,
            "rerun_after_confirmation_failure_permitted": False,
            "selection_rule": "first confirmed pass",
            "scan_stops_immediately_after_the_first_confirmed_pass": True,
        },
        "multiplicity": {
            "scan_continues_past_failures": True,
            "classical_fixed_sequence_protection_applies": False,
            "candidate_level_allocation":
                "study development screening alpha divided by the full "
                "predeclared ladder length L, regardless of how many candidates "
                "are actually visited",
            "study_development_screening_alpha_exact_rational": "1/200",
            "within_candidate_component_allocation_preserved_separately": True,
            "within_candidate_component_alpha_exact_rational":
                stats["development_components"]["I1a+I1b+I3"]
                ["alpha_exact_rational"],
        },
        "no_candidate_qualifies_state":
            "NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_THE_REGISTERED_LADDER",
        "no_candidate_qualifies_claim_ceiling":
            "restricted to the registered family, size range, checkpoint "
            "revisions and interface set; no universal statement about all "
            "checkpoints or all restricted-logit interfaces is permitted",
    }


def rp_separation_block() -> dict:
    return {
        "RP-B": {
            "kind": "behavioral reference for expressed competence and "
                    "interface readout",
            "tokenizer_interface_equivalence_required_for_transfer_claims": True,
        },
        "RP-M": {
            "kind": "ground-truth mechanism and method reference for patching "
                    "validation, such as a registered synthetic or "
                    "circuit-known model",
            "must_share_rt_tokenizer": False,
            "why": "it validates intervention methodology rather than the "
                   "frozen behavioral interface",
        },
        "combined_into_one_gate": False,
        "combined_into_one_claim": False,
        "rp_m_validation_required_before_natural_model_patch_claims": True,
    }


def equivalence_block() -> dict:
    return {
        "tokenizer_equivalence_inferred_from_model_names": False,
        "decision_criterion": "the four-part functional test",
        "four_part_functional_test": [
            "bytes", "token IDs in full context", "common prefix",
            "discriminant position",
        ],
        "evaluated_per": "every immutable checkpoint revision x every registered "
                         "candidate surface",
        "file_hashes_are": "provenance, not the decision criterion",
        "failure_classification": "isomorphic_reinstantiation",
        "failure_handling": "analysed as a separate stratum; may not be pooled "
                            "with checkpoints described as sharing the exact "
                            "frozen interface",
        "runtime_revisions_deferred_to": "DEFER-01",
        "intentional_deferral_representation": "explicit fail-closed state, "
                                               "never TBD",
    }


def activation_block() -> dict:
    return {
        "activation_collection_authorized": False,
        "j_lens_fitting_authorized": False,
        "patching_authorized": False,
        "ablation_authorized": False,
        "mechanism_inference_authorized": False,
        "unlocked_only_after_all_of": [
            "software and mechanical integrity",
            "engineering shakedown exit",
            "generated-CoT headroom where applicable",
            "E0 behavioral competence",
            "registered interface floors",
            "wrapper joint adequacy",
            "RP-B qualification or its registered bounded terminal outcome",
            "RP-M method validation before natural-model patch claims",
        ],
        "checkpoint_differences_may_be_described_as":
            "checkpoint-level associations only",
        "distillation_caused_the_mechanism_permitted": False,
        "causal_claim_requires":
            "a separate future design with matched training interventions and "
            "independent seeds",
    }


# ---------------------------------------------------------------------------
# Subordinate assets
# ---------------------------------------------------------------------------

def build_registry() -> dict:
    v0_6 = _read_json(REGISTRY_V0_6)
    roles = ["RT", "RL", "RI"]
    wrappers = []
    for role in roles:
        wrappers.append({
            "role": role,
            "arm": "raw",
            "wrapper_id": "wrapper_raw_common_v0_7",
            "shared_across_roles": True,
            "chat_template_applied": False,
            "description": "the registered common raw wrapper; identical bytes "
                           "for every role",
        })
        canonical = {
            "role": role,
            "arm": "canonical",
            "wrapper_id": "wrapper_canonical_%s_v0_7" % role.lower(),
            "shared_across_roles": False,
            "chat_template_applied": role != "RL",
        }
        if role == "RL":
            canonical["description"] = (
                "RL has no canonical chat template, so its role-canonical arm is "
                "a deterministic few-shot completion-format wrapper")
            canonical["few_shot_completion_format"] = True
            canonical["deterministic"] = True
        else:
            canonical["description"] = (
                "the role's registered canonical chat template")
            canonical["few_shot_completion_format"] = False
            canonical["deterministic"] = True
        wrappers.append(canonical)
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "draft_version": DRAFT_VERSION,
        "status": {"frozen": False, "execution_authorized": False},
        "subordinate_to": "interface_calibration_protocol_draft_v0_7.json",
        "inherited_v0_6_scoring_boundary": {
            "source": _file_identity(REGISTRY_V0_6),
            "schema_version": v0_6.get("schema_version"),
            "carried_forward_unchanged": True,
            "why": "the v0.6 first-discriminative-token scoring boundary is "
                   "normative and is inherited byte-identically by reference; "
                   "v0.7 adds wrapper arms and changes no scoring rule",
        },
        "answer_surfaces": {
            "surfaces": [" %d" % d for d in range(10)],
            "count": 10,
            "leading_code_point": "U+0020",
            "tokens_per_surface": 2,
            "structure": "[common_prefix_token, discriminant_token]",
            "unchanged_from_v0_5": True,
        },
        "roles": roles,
        "wrapper_arms": ["raw", "canonical"],
        "wrappers": wrappers,
        "wrapper_count": len(wrappers),
        "comparison_is_within_role": True,
        "registers_a_template_effect_claim": False,
        "model_operations_performed": 0,
    }


def build_registry_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Study 3 interface-calibration rendering registry draft-v0.7",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "draft_version", "status", "subordinate_to",
            "inherited_v0_6_scoring_boundary", "answer_surfaces", "roles",
            "wrapper_arms", "wrappers", "wrapper_count",
            "comparison_is_within_role",
            "registers_a_template_effect_claim", "model_operations_performed",
        ],
        "properties": {
            "schema_version": {"const": REGISTRY_SCHEMA_VERSION},
            "draft_version": {"const": DRAFT_VERSION},
            "status": {
                "type": "object", "additionalProperties": False,
                "required": ["frozen", "execution_authorized"],
                "properties": {"frozen": {"const": False},
                               "execution_authorized": {"const": False}},
            },
            "subordinate_to": {"const":
                               "interface_calibration_protocol_draft_v0_7.json"},
            "inherited_v0_6_scoring_boundary": {"type": "object"},
            "answer_surfaces": {"type": "object"},
            "roles": {"type": "array", "minItems": 3, "items": {"type": "string"}},
            "wrapper_arms": {"type": "array", "minItems": 2,
                             "items": {"enum": ["raw", "canonical"]}},
            "wrappers": {
                "type": "array", "minItems": 6,
                "items": {
                    "type": "object",
                    "required": ["role", "arm", "wrapper_id",
                                 "chat_template_applied", "description"],
                    "properties": {
                        "role": {"enum": ["RT", "RL", "RI"]},
                        "arm": {"enum": ["raw", "canonical"]},
                        "wrapper_id": {"type": "string"},
                    },
                },
            },
            "wrapper_count": {"type": "integer"},
            "comparison_is_within_role": {"const": True},
            "registers_a_template_effect_claim": {"const": False},
            "model_operations_performed": {"const": 0},
        },
    }


def build_pointer(protocol_identity, schema_identity, md_identity,
                  registry_identity, legacy) -> dict:
    return {
        "schema_version": POINTER_SCHEMA_VERSION,
        "active_draft_version": DRAFT_VERSION,
        "protocol_state": STATE,
        "frozen": False,
        "execution_authorized": False,
        "active_bundle": {
            "protocol_json": protocol_identity,
            "protocol_schema": schema_identity,
            "protocol_markdown": md_identity,
            "rendering_registry": registry_identity,
        },
        "legacy_protocol_historical_p0_binding_only": {
            "status": LEGACY_STATUS,
            "is_current_protocol": False,
            "files": [{"path": path, "sha256": entry["sha256"],
                       "bytes": entry["bytes"]}
                      for path, entry in sorted(legacy.items())],
            "why": "the immutable P0 corpus manifest byte-binds the legacy "
                   "protocol JSON; it is preserved as historical P0 input and is "
                   "not the active protocol",
        },
        "authorities": {
            "successor_authority": SUCCESSOR_AUTHORITY,
            "original_amendment_authority": ORIGINAL_AUTHORITY,
            "placement_probe": PLACEMENT_PROBE,
            "terminal_disposition": TERMINAL_DISPOSITION,
        },
        "amendment": "studies/study3/reviews/v0_7_operator_amendment.json",
        "next_legal_action":
            "one fresh independent single focused methods review of draft-v0.7 "
            "by a party that did not draft it",
        "fallback_to_legacy_permitted": False,
        "loader_contract": {
            "must_resolve_only_to_the_versioned_v0_7_bundle": True,
            "must_fail_closed_if_any_recorded_hash_mismatches": True,
            "must_fail_closed_if_any_active_bundle_file_is_absent": True,
            "must_not_load_interface_calibration_protocol_draft_json": True,
            "fail_closed_state": "STUDY3_V0_7_ACTIVE_PROTOCOL_UNRESOLVABLE",
        },
        "model_operations_performed": 0,
    }


def build_pointer_schema() -> dict:
    identity = {
        "type": "object", "additionalProperties": False,
        "required": ["path", "bytes", "sha256"],
        "properties": {"path": {"type": "string"},
                       "bytes": {"type": "integer"},
                       "sha256": {"type": "string",
                                  "pattern": "^[0-9a-f]{64}$"}},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Study 3 current interface-calibration protocol pointer",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "active_draft_version", "protocol_state",
            "frozen", "execution_authorized", "active_bundle",
            "legacy_protocol_historical_p0_binding_only", "authorities",
            "amendment", "next_legal_action", "fallback_to_legacy_permitted",
            "loader_contract", "model_operations_performed",
        ],
        "properties": {
            "schema_version": {"const": POINTER_SCHEMA_VERSION},
            "active_draft_version": {"const": DRAFT_VERSION},
            "protocol_state": {"const": STATE},
            "frozen": {"const": False},
            "execution_authorized": {"const": False},
            "active_bundle": {
                "type": "object", "additionalProperties": False,
                "required": ["protocol_json", "protocol_schema",
                             "protocol_markdown", "rendering_registry"],
                "properties": {"protocol_json": identity,
                               "protocol_schema": identity,
                               "protocol_markdown": identity,
                               "rendering_registry": identity},
            },
            "legacy_protocol_historical_p0_binding_only": {
                "type": "object",
                "required": ["status", "is_current_protocol", "files"],
                "properties": {"status": {"const": LEGACY_STATUS},
                               "is_current_protocol": {"const": False}},
            },
            "authorities": {"type": "object"},
            "amendment": {"type": "string"},
            "next_legal_action": {"type": "string"},
            "fallback_to_legacy_permitted": {"const": False},
            "loader_contract": {
                "type": "object",
                "required": ["must_resolve_only_to_the_versioned_v0_7_bundle",
                             "must_fail_closed_if_any_recorded_hash_mismatches",
                             "must_not_load_interface_calibration_protocol_draft_json",
                             "fail_closed_state"],
                "properties": {
                    "must_resolve_only_to_the_versioned_v0_7_bundle":
                        {"const": True},
                    "must_fail_closed_if_any_recorded_hash_mismatches":
                        {"const": True},
                    "must_not_load_interface_calibration_protocol_draft_json":
                        {"const": True},
                },
            },
            "model_operations_performed": {"const": 0},
        },
    }


# ---------------------------------------------------------------------------
# The protocol, its schema, the Markdown companion and the amendment
# ---------------------------------------------------------------------------

V0_7_BLOCK_KEYS = tuple(pointer for _, _, pointer in DECISIONS)


def build_protocol(legacy, stats, constants, registry_identity) -> dict:
    document = copy.deepcopy(_read_json(LEGACY_JSON))
    carried = sorted(document)

    document["schema_version"] = SCHEMA_VERSION
    document["state"] = STATE
    document["study_identity"] = dict(document["study_identity"],
                                      draft_version=DRAFT_VERSION)
    document["status"] = dict(
        document["status"],
        frozen=False,
        execution_authorized=False,
        review_state="awaiting_single_focused_methods_review",
        document_class="design_draft",
        amendment_record="studies/study3/reviews/v0_7_operator_amendment.md",
        amendment_record_json="studies/study3/reviews/v0_7_operator_amendment.json",
    )
    document["required_next_action"] = (
        "one fresh independent single focused methods review of draft-v0.7 by a "
        "party that did not draft it")

    document["provenance_v0_7"] = {
        "self_contained": True,
        "executor_must_layer_amendments_manually": False,
        "carried_forward_top_level_keys": carried,
        "carried_forward_key_count": len(carried),
        "derived_from": [
            {"role": "immutable legacy v0.5 protocol bundle",
             "files": [{"path": path, "sha256": entry["sha256"],
                        "status": LEGACY_STATUS}
                       for path, entry in sorted(legacy.items())]},
            {"role": "normative v0.6 scoring and rendering registry",
             "files": [_file_identity(REGISTRY_V0_6)]},
            {"role": "original v0.7 consolidated-amendment authority",
             "files": [_file_identity(REPO_ROOT / ORIGINAL_AUTHORITY)]},
            {"role": "copy-on-write successor authority",
             "files": [_file_identity(REPO_ROOT / SUCCESSOR_AUTHORITY)]},
            {"role": "placement probe and terminal disposition",
             "files": [_file_identity(REPO_ROOT / PLACEMENT_PROBE),
                       _file_identity(REPO_ROOT / PROBE_OUTPUT)]},
        ],
    }

    document["protocol_placement_v0_7"] = {
        "operator_decision": "OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL",
        "legacy_bundle_status": LEGACY_STATUS,
        "legacy_bundle_bytes_changed": 0,
        "p0_corpus_manifest_regenerated": False,
        "frozen_corpus_test_retired_or_weakened": False,
        "rendering_registry_is_the_omnibus_normative_home": False,
        "sole_top_level_normative_protocol":
            "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.json",
        "subordinate_normative_asset": registry_identity,
        "markdown_is_a_companion": True,
        "current_pointer_is_routing_only": True,
        "legacy_and_v0_6_are_provenance_inputs_not_runtime_overlays": True,
    }

    document["estimands_v0_7"] = estimands_block()
    document["e0_answer_and_decoding_contract"] = e0_contract(
        constants, registry_identity)
    document["full_context_tokenization_and_d0_diagnostics"] = tokenization_block()
    document["competence_floor_battery_v0_7"] = competence_battery(stats)
    document["wrapper_matched_contrast_v0_7"] = wrapper_block(
        constants, registry_identity)
    document["generated_cot_ceiling_v0_7"] = cot_ceiling_block(constants)
    document["q0_and_rp_b_v0_7"] = q0_rp_b_block(stats)
    document["rp_b_and_rp_m_separation_v0_7"] = rp_separation_block()
    document["checkpoint_functional_equivalence_v0_7"] = equivalence_block()
    document["engineering_shakedown_authority_v0_7"] = shakedown_limits()
    document["negative_control_equivalence_v0_7"] = {
        "quantitative_upper_bound_exact_rational":
            constants["negative_control_equivalence_upper_bound_exact_rational"],
        "derivation": constants["negative_control_equivalence_derivation"],
        "not_significantly_above_chance_is_an_equivalence_demonstration": False,
        "test": "exact one-sided upper confidence bound at the registered "
                "development alpha must lie strictly below the bound",
    }
    document["recursive_manifest_seal_v0_7"] = {
        "covers_all_decision_bearing_bytes": True,
        "inclusion": [
            "image digest", "immutable checkpoint revisions", "tokenizer files",
            "renderer and wrapper registry", "task banks",
            "readout and parser code", "thresholds and decision tables",
            "analysis code", "decoding configuration",
            "manifests and provenance records required by the registered "
            "construction",
        ],
        "inclusion_path_globs": [
            "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.*",
            "studies/study3/protocol/interface_calibration_rendering_registry_v0_7.*",
            "studies/study3/analysis/*.py",
            "studies/study3/analysis/*_tables.json",
        ],
        "explicit_exclusions": [
            "the recursive manifest file itself",
            "the terminal root record that carries the root hash",
            "generated outputs written by the sealed run",
            "__pycache__ and compiled artifacts",
        ],
        "manifest_generation_script_is_included_and_hashed": True,
        "construction": "two_level",
        "two_level_construction":
            "level one hashes every included byte and produces the manifest; "
            "level two writes the root hash into the terminal record. Neither "
            "file is required to contain its own hash, so the construction is "
            "not self-referential and has no fixed point",
        "self_referential": False,
        "root_hash_destination": "the applicable future terminal record",
    }
    document["activation_and_causal_claim_boundary_v0_7"] = activation_block()
    document["deterministic_deferrals_v0_7"] = deferrals()
    document["prohibited_language_v0_7"] = {
        "phrases": list(PROHIBITED_LANGUAGE),
        "checked_by_mutation_tests": True,
        "applies_to": ["protocol", "registry", "amendment", "markdown"],
    }
    document["decision_markers_v0_7"] = [
        {"marker": marker, "title": title, "json_key": key}
        for marker, title, key in DECISIONS
    ]
    document["numerical_closure_v0_7"] = {
        "tbd_count": 0,
        "operator_discretion_clause_count": 0,
        "unresolved_alternative_count": 0,
        "every_execution_value_is_frozen_or_deterministically_deferred": True,
        "derived_constants": constants,
    }
    document["zero_operation_boundary_v0_7"] = {
        "azure_acr_aca_gpu_cloud_operations": 0,
        "tokenizer_constructions": 0, "tokenizer_encodes": 0,
        "tokenizer_decodes": 0, "checkpoint_downloads": 0,
        "checkpoint_loads": 0, "model_weight_loads": 0, "adapter_loads": 0,
        "activation_loads": 0, "prefills": 0, "forward_passes": 0,
        "logit_reads": 0, "scoring_operations": 0, "generations": 0,
        "model_output_parses": 0, "seeds_drawn": 0,
        "task_bank_rows_generated": 0, "split_realizations": 0,
        "confirmation_accesses": 0, "interface_qualifications": 0,
        "interface_selections": 0, "rp_b_qualifications": 0,
        "rp_m_qualifications": 0, "evidence_rows_added": 0,
        "scientific_evidence_claims": 0, "github_actions_runs": 0,
    }
    document["p0_r2_historical_treatment_v0_7"] = {
        "legal_characterization": "P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS",
        "generation2_live_replay_mechanically_passed": True,
        "independently_reconstructed": True,
        "bounded_pilot_authorization_failed": True,
        "gpu_job_created_or_started": False,
        "model_tokenizer_scoring_gpu_counters_zero": True,
        "evidence_ledger_tail": "EV-0016",
        "research_question_answered": False,
        "p0_result_is_scientific_evidence": False,
        "model_competence_inferred_from_p0_r2": False,
        "generation_3_created": False,
        "audit_exceptions": [
            "aggregate attempt-ledger and handoff counts predate the final "
            "live-prefix and replay operations and are not a complete final "
            "aggregate, although the individual terminal receipts exist",
            "committed Phase-B and preflight evidence binds an earlier head and "
            "lock; no committed artifact proves the entire 38-condition "
            "admission result at the exact replay anchor",
            "the final hard-kill job used an empty CUDA_VISIBLE_DEVICES value "
            "although the authority literally specified -1; the safe no-GPU "
            "intent was preserved, but literal byte-level compliance cannot be "
            "claimed",
            "the current Git DAG establishes linear history and no merge, but "
            "historical force-push count is UNKNOWN without an independent "
            "GitHub audit log",
        ],
        "prohibited_phrases": ["full authority compliance verified",
                               "zero force-pushes verified"],
    }
    document["focused_review_packet_v0_7"] = {
        "contains_a_verdict": False,
        "review_is_performed_by": "a fresh independent party that did not draft "
                                  "v0.7",
        "permitted_returns": [
            "freeze or accept under its registered acceptance state",
            "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED",
        ],
        "may_automatically_draft_v0_8": False,
        "scope": [
            "the copy-on-write placement and the self-containment claim",
            "the dual E0/D0 estimands and the claim ceiling",
            "the E0 answer, parser and decoding contract",
            "full-context tokenization and the descriptive D0 diagnostics",
            "the retained I1a/I1b/I2 battery and its regenerated numbers",
            "wrapper joint adequacy and its descriptive bandwidth",
            "the generated-CoT ceiling and its reuse of the I2 headroom construct",
            "Q0, the RP-B ladder rule and the deferred ladder length L",
            "RP-B versus RP-M separation",
            "per-checkpoint functional equivalence",
            "the engineering shakedown budget",
            "the recursive-manifest seal construction",
            "the three deterministic deferrals and their fail-closed states",
        ],
    }
    return document


def build_protocol_schema(document) -> dict:
    required = sorted(document)
    properties = {key: {} for key in required}
    properties["schema_version"] = {"const": SCHEMA_VERSION}
    properties["state"] = {"const": STATE}
    properties["status"] = {
        "type": "object",
        "required": ["frozen", "execution_authorized"],
        "properties": {"frozen": {"const": False},
                       "execution_authorized": {"const": False}},
    }
    properties["estimands_v0_7"] = {
        "type": "object", "required": ["E0", "D0", "claim_ceiling"],
        "properties": {
            "E0": {"type": "object",
                   "required": ["id", "role",
                                "establishes_absence_of_internal_computation"],
                   "properties": {
                       "id": {"const":
                              "E0_zero_generated_reasoning_token_expressed_competence"},
                       "role": {"const": "primary"},
                       "establishes_absence_of_internal_computation":
                           {"const": False}}},
            "D0": {"type": "object",
                   "required": ["id", "enters_q0", "enters_the_rp_b_gate"],
                   "properties": {
                       "id": {"const": "D0_single_forward_decodability"},
                       "enters_q0": {"const": False},
                       "enters_the_rp_b_gate": {"const": False}}},
        },
    }
    properties["generated_cot_ceiling_v0_7"] = {
        "type": "object",
        "required": ["is_an_execution_precondition_gate", "is_an_interface_selector",
                     "statistical_unit_is_the_item", "failure_state",
                     "can_select_an_interface"],
        "properties": {
            "is_an_execution_precondition_gate": {"const": True},
            "is_an_interface_selector": {"const": False},
            "is_s4": {"const": False},
            "statistical_unit_is_the_item": {"const": True},
            "n_times_k_responses_treated_as_independent_items": {"const": False},
            "can_select_an_interface": {"const": False},
            "failure_state": {"const":
                              "NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE"},
        },
    }
    properties["wrapper_matched_contrast_v0_7"] = {
        "type": "object", "required": ["gate", "comparison_is_within_role"],
        "properties": {
            "comparison_is_within_role": {"const": True},
            "gate": {"type": "object",
                     "required": ["kind", "registers_a_template_effect_claim"],
                     "properties": {
                         "kind": {"const": "joint_adequacy"},
                         "registers_a_template_effect_claim": {"const": False},
                         "registers_an_equivalence_claim": {"const": False},
                         "registers_an_invariance_claim": {"const": False}}},
        },
    }
    properties["q0_and_rp_b_v0_7"] = {
        "type": "object",
        "required": ["q0_must_contain_an_e0_expressed_competence_component",
                     "d0_alone_can_qualify_a_candidate", "multiplicity",
                     "no_candidate_qualifies_state"],
        "properties": {
            "q0_must_contain_an_e0_expressed_competence_component": {"const": True},
            "d0_alone_can_qualify_a_candidate": {"const": False},
            "no_candidate_qualifies_state": {"const":
                "NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_THE_REGISTERED_LADDER"},
        },
    }
    properties["protocol_placement_v0_7"] = {
        "type": "object",
        "required": ["operator_decision", "legacy_bundle_bytes_changed",
                     "p0_corpus_manifest_regenerated",
                     "frozen_corpus_test_retired_or_weakened"],
        "properties": {
            "operator_decision": {"const":
                                  "OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL"},
            "legacy_bundle_bytes_changed": {"const": 0},
            "p0_corpus_manifest_regenerated": {"const": False},
            "frozen_corpus_test_retired_or_weakened": {"const": False},
        },
    }
    properties["numerical_closure_v0_7"] = {
        "type": "object",
        "required": ["tbd_count", "operator_discretion_clause_count",
                     "every_execution_value_is_frozen_or_deterministically_deferred"],
        "properties": {
            "tbd_count": {"const": 0},
            "operator_discretion_clause_count": {"const": 0},
            "unresolved_alternative_count": {"const": 0},
            "every_execution_value_is_frozen_or_deterministically_deferred":
                {"const": True},
        },
    }
    properties["decision_markers_v0_7"] = {
        "type": "array", "minItems": len(DECISIONS),
        "items": {"type": "object", "required": ["marker", "title", "json_key"]},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Study 3 interface-calibration protocol draft-v0.7",
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


# ---------------------------------------------------------------------------
# A compact fail-closed schema validator (standard library only)
# ---------------------------------------------------------------------------

def validate_against(document, schema, pointer="") -> list:
    errors = []
    kind = schema.get("type")
    if "const" in schema and document != schema["const"]:
        errors.append("%s must be %r, is %r"
                      % (pointer or "/", schema["const"], document))
        return errors
    if "enum" in schema and document not in schema["enum"]:
        errors.append("%s is not one of %r" % (pointer or "/", schema["enum"]))
        return errors
    if kind == "object":
        if not isinstance(document, dict):
            return ["%s must be an object" % (pointer or "/")]
        for name in schema.get("required", []):
            if name not in document:
                errors.append("%s/%s is required" % (pointer, name))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for name in sorted(document):
                if name not in properties:
                    errors.append("%s/%s is not a registered property"
                                  % (pointer, name))
        for name, sub in properties.items():
            if name in document and sub:
                errors.extend(validate_against(document[name], sub,
                                               "%s/%s" % (pointer, name)))
    elif kind == "array":
        if not isinstance(document, list):
            return ["%s must be an array" % (pointer or "/")]
        if len(document) < schema.get("minItems", 0):
            errors.append("%s has %d items, fewer than the required %d"
                          % (pointer or "/", len(document), schema["minItems"]))
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(document):
                errors.extend(validate_against(item, item_schema,
                                               "%s/%d" % (pointer, index)))
    elif kind == "string":
        if not isinstance(document, str):
            errors.append("%s must be a string" % (pointer or "/"))
        elif "pattern" in schema:
            import re as _re
            if not _re.match(schema["pattern"], document):
                errors.append("%s does not match %s"
                              % (pointer or "/", schema["pattern"]))
    elif kind == "integer":
        if not isinstance(document, int) or isinstance(document, bool):
            errors.append("%s must be an integer" % (pointer or "/"))
    return errors


# ---------------------------------------------------------------------------
# Markdown companion and amendment
# ---------------------------------------------------------------------------

def build_markdown(document, constants) -> bytes:
    stats = document["competence_floor_battery_v0_7"]
    dev = stats["development_components"]
    conf = stats["confirmation_components"]
    lines = []
    add = lines.append

    add("# Study 3 - interface adequacy and label-binding calibration, draft-v0.7")
    add("")
    add("> **State:** `%s`" % STATE)
    add(">")
    add("> draft-v0.7 is **not** reviewed, **not** frozen, **not** selected and")
    add("> **not** formally executable. `frozen = false` and")
    add("> `execution_authorized = false`. The determination belongs to a party")
    add("> that did not draft it.")
    add("")
    add("The JSON protocol is normative. This Markdown is its companion and")
    add("agrees with every decision-bearing JSON marker below.")
    add("")
    add("Normative JSON:")
    add("[`interface_calibration_protocol_draft_v0_7.json`]"
        "(interface_calibration_protocol_draft_v0_7.json).")
    add("")

    add("## How this document is bound to the JSON")
    add("")
    add("Each section carries a decision marker of the form `V07-Dnn`. Every")
    add("marker occurs exactly once here and exactly once in")
    add("`decision_markers_v0_7`, and each names a real top-level JSON key. The")
    add("committed tests fail if a marker is missing, duplicated or unresolvable.")
    add("")
    add("| marker | decision | JSON key |")
    add("| --- | --- | --- |")
    for marker, title, key in DECISIONS:
        add("| `%s` | %s | `%s` |" % (marker, title, key))
    add("")

    add("## Placement, and why draft-v0.7 is a new bundle `[V07-D13]`")
    add("")
    add("The operator selected `OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL`.")
    add("")
    add("The immutable P0 corpus manifest byte-binds the legacy protocol JSON, so")
    add("a single changed byte makes `p0_freeze_corpus.py --check` fail. draft-v0.7")
    add("is therefore a **new, self-contained bundle** written beside the legacy")
    add("files, which keep status `%s`" % LEGACY_STATUS)
    add("and are unchanged. The P0 corpus manifest was not regenerated and the")
    add("frozen-corpus test was not retired, weakened or waived.")
    add("")
    add("Every legacy top-level key is carried forward, so an executor reads one")
    add("protocol plus the exact subordinate assets it names, and never layers")
    add("v0.5, v0.6 and v0.7 by hand.")
    add("")

    add("## Estimands `[V07-D01]`")
    add("")
    add("**E0** - `E0_zero_generated_reasoning_token_expressed_competence` is the")
    add("primary behavioral endpoint: the model emits a correct registered answer")
    add("surface **without emitting generated reasoning tokens**. For multi-token")
    add("answers, answer-token autoregression is explicitly part of the estimand.")
    add("E0 does not establish absence of internal computation and is never")
    add("described as one forward pass or as proof that reasoning was absent.")
    add("")
    add("**D0** - `D0_single_forward_decodability` is a secondary conditional")
    add("mechanism claim, permitted only as: under the frozen counterfactual")
    add("readout, discriminant information was decodable from one registered logit")
    add("read. D0 covers only the registered discriminant, enters neither Q0 nor")
    add("the RP-B gate, and is reported separately from E0.")
    add("")

    add("## E0 answer and decoding contract `[V07-D02]`")
    add("")
    add("| item | value |")
    add("| --- | --- |")
    add("| legal surfaces | `\" 0\"`..`\" 9\"`, one leading U+0020 each |")
    add("| matching | full-sequence exact match; prefix match prohibited |")
    add("| `7 because...` | incorrect |")
    add("| unparseable or out-of-domain | incorrect, never dropped |")
    add("| `do_sample` | `false`, the actual deterministic switch |")
    add("| sampling-only parameters | recorded `INACTIVE_do_sample_false` |")
    add("| `max_new_tokens` | %d |" % constants["e0_max_new_tokens"])
    add("| EOS margin | %d token |" % constants["e0_eos_margin_tokens"])
    add("| batch size / padding side | 1 / left |")
    add("| reproducibility | byte-exact, tolerance %d |"
        % constants["reproducibility_tolerance"])
    add("")
    add("Temperature alone is never the switch. Exact reproducibility is defined")
    add("operationally: every decision-bearing artifact must reproduce with an")
    add("identical SHA-256 under the sealed recursive manifest.")
    add("")

    add("## Full-context tokenization and D0 diagnostics `[V07-D03]`")
    add("")
    add("All eligibility and scoring proofs use the actual complete context,")
    add("`rendered_prompt_bytes + candidate_surface_bytes`. Full-context")
    add("tokenization is never inferred from candidate-only encoding.")
    add("")
    add("Restricted accuracy, full-vocabulary answer-set probability mass,")
    add("complete candidate joint log-likelihood, full-vocabulary rank and")
    add("short-generation validity are pre-registered and always reported")
    add("**descriptively**. No uncalibrated probability-mass threshold is")
    add("registered, and no diagnostic can rescue a failed E0 gate.")
    add("")

    add("## The registered competence-floor battery `[V07-D04]`")
    add("")
    add("The existing I1a/I1b/I2 structure is retained. No new MDE is registered")
    add("and no 400-cluster design is created. Every number below is regenerated")
    add("by `design_statistics.py` and compared, never transcribed.")
    add("")
    add("| stage | gates | null p0 | alternative p1 | alpha | n | pass |")
    add("| --- | --- | --- | --- | --- | ---: | ---: |")
    for key in ("I1a+I1b+I3", "I2", "I4"):
        row = dev[key]
        add("| development | %s | `%s` | `%s` | `%s` | %d | %d |"
            % (key.replace("+", ", "), row["p0_exact_rational"],
               row["p1_exact_rational"], row["alpha_exact_rational"],
               row["n"], row["pass_count"]))
    for key in ("I1a+I1b+I3", "I2", "I4"):
        row = conf[key]
        add("| confirmation | %s | `%s` | `%s` | `%s` | %d | %d |"
            % (key.replace("+", ", "), row["p0_exact_rational"],
               row["p1_exact_rational"], row["alpha_exact_rational"],
               row["n"], row["pass_count"]))
    add("")
    power = stats["power_architecture"]
    add("| power quantity | exact rational |")
    add("| --- | --- |")
    add("| `m_max` | %d |" % power["m_max"])
    add("| per-cell false-negative budget | `%s` |"
        % power["per_cell_false_negative_budget_exact_rational"])
    add("| per-cell power target | `%s` |"
        % power["per_cell_power_target_exact_rational"])
    add("| profile stage power floor | `%s` |"
        % power["profile_stage_power_floor_exact_rational"])
    add("| study end-to-end power floor | `%s` |"
        % power["study_end_to_end_power_floor_exact_rational"])
    add("")
    add("A change to the scientific null, the competence floor or the meaning of")
    add("the existing floor test is outside this amendment and requires")
    add("`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`.")
    add("")

    add("## Wrapper-only matched contrast `[V07-D05]`")
    add("")
    add("Within each role, a registered common **raw** wrapper is compared with")
    add("that role's registered **canonical** wrapper. RL has no canonical chat")
    add("template, so its canonical arm is a deterministic few-shot")
    add("completion-format wrapper; chat versus raw is not the same intervention")
    add("across roles.")
    add("")
    add("The gate is **joint adequacy**: both renderings must meet their")
    add("competence floors. No template-effect, equivalence or invariance claim is")
    add("registered. The only permitted positive wording is that both registered")
    add("renderings met their competence floors.")
    add("")
    add("Paired discordance and risk difference are always reported")
    add("descriptively. The registered descriptive bandwidth is")
    add("`%s`, derived as the distance between the null floor and the lowest"
        % constants["wrapper_descriptive_bandwidth_exact_rational"])
    add("alternative of interest. Exceeding it triggers a fixed limitation")
    add("paragraph and has **no gate effect**.")
    add("")

    add("## Canonical generated-CoT ceiling `[V07-D06]`")
    add("")
    add("A separate execution-precondition gate. It is not an interface selector")
    add("and it is not S4; S4 remains a short answer-only generation diagnostic")
    add("with its existing %d-token bound and is never selectable."
        % constants["s4_generated_token_bound_per_generation"])
    add("")
    add("| frozen item | value |")
    add("| --- | --- |")
    add("| route marker | `<think>`, required |")
    add("| `do_sample` | `false` |")
    add("| `k` | %d |" % constants["generated_cot_ceiling_k"])
    add("| aggregation | `%s` |"
        % constants["generated_cot_ceiling_aggregation"])
    add("| `theta` | `%s` |"
        % constants["generated_cot_ceiling_theta_exact_rational"])
    add("| alternative | `%s` |"
        % constants["generated_cot_ceiling_p1_exact_rational"])
    add("| alpha | `%s` |"
        % constants["generated_cot_ceiling_alpha_exact_rational"])
    add("| n / pass | %d / %d |" % (constants["generated_cot_ceiling_n"],
                                    constants["generated_cot_ceiling_pass_count"]))
    add("| maximum generation length | deterministic per item, `DEFER-03` |")
    add("| granularity | per immutable checkpoint revision |")
    add("")
    add("`theta` is not invented: the ceiling is a **task-headroom** gate, so it")
    add("reuses the registered I2 primitive-headroom construct exactly - same")
    add("null, same lowest alternative of interest, same alpha, same exact")
    add("one-sided binomial, same regenerated `n` and pass count.")
    add("")
    add("`k = 1` with deterministic decoding, so exactly one estimand is")
    add("registered before data and the pass@1 versus majority-vote@k choice")
    add("cannot arise at execution time. Majority-vote@k is **not** registered.")
    add("The statistical unit is the item; `n x k` responses are never treated as")
    add("independent items. Failure yields")
    add("`NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE`. A pass establishes")
    add("generated-CoT task competence only and cannot select an interface.")
    add("")

    add("## Q0 and the RP-B ladder `[V07-D07]`")
    add("")
    add("Q0 is a one-way prequalification layer: a pass is interpretable, a")
    add("failure is not evidence that the interface is invalid or that the")
    add("construct does not exist. Q0 must contain an E0 expressed-competence")
    add("component, and D0 alone can never qualify a candidate.")
    add("")
    add("The ladder is ordered by predeclared observable metadata - parameter")
    add("count ascending, publication time as the sole tie-break. Result-informed")
    add("ordering is prohibited. Same-tokenizer natural candidates come first;")
    add("training-constructed implicit-CoT or direct-answer models appear only as")
    add("a separately identified fallback stratum whose claim ceiling is that the")
    add("isomorphic interface construction is valid, never that the exact RT byte")
    add("interface is valid.")
    add("")
    add("Development and confirmation sets are physically and logically")
    add("item-disjoint, confirmation is frozen before development access, there is")
    add("one confirmation attempt per candidate, no tuning or rerun after a")
    add("confirmation failure, selection is first-confirmed-pass, and the scan")
    add("stops immediately after the first confirmed pass.")
    add("")
    add("Because the scan continues past failures, classical fixed-sequence")
    add("protection does not apply. The candidate-level Bonferroni allocation uses")
    add("the **full** predeclared ladder length `L` regardless of how many")
    add("candidates are visited, and the within-candidate component allocation is")
    add("preserved separately. `L` is deterministically deferred as `DEFER-02`.")
    add("")
    add("If no candidate qualifies the terminal state is exactly")
    add("`NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_THE_REGISTERED_LADDER`,")
    add("whose claim ceiling is restricted to the registered family, size range,")
    add("checkpoint revisions and interface set.")
    add("")

    add("## RP-B and RP-M `[V07-D08]`")
    add("")
    add("`RP-B` is a behavioral reference for expressed competence and interface")
    add("readout. `RP-M` is a ground-truth mechanism reference for patching")
    add("validation. They are never combined into one gate or one claim. RP-M need")
    add("not share RT's tokenizer because it validates intervention methodology;")
    add("RP-B transfer claims remain subject to tokenizer and interface")
    add("equivalence.")
    add("")

    add("## Per-checkpoint functional equivalence `[V07-D09]`")
    add("")
    add("Tokenizer equivalence is never inferred from model names. For every")
    add("immutable checkpoint revision and every registered candidate surface,")
    add("bytes, token IDs in full context, common prefix and discriminant position")
    add("must all be equal. File hashes are provenance; the four-part functional")
    add("test is the decision criterion. A checkpoint failing any equality is an")
    add("`isomorphic_reinstantiation` and is analysed as a separate stratum.")
    add("")

    add("## Engineering shakedown authority `[V07-D10]`")
    add("")
    add("Disjoint from formal calibration authority, and not run in this session.")
    add("")
    shake = document["engineering_shakedown_authority_v0_7"]
    add("| limit | value |")
    add("| --- | ---: |")
    add("| max fix-and-rerun cycles | %d |" % shake["max_fix_and_rerun_cycles"])
    add("| max total attempts | %d |" % shake["max_total_attempts"])
    add("| max wall-clock minutes | %d |" % shake["max_wall_clock_minutes"])
    add("| max CPU core-hours | %d |" % shake["max_cpu_core_hours"])
    add("| max GPU hours | %d |" % shake["max_gpu_hours"])
    add("| max cloud jobs | %d |" % shake["max_cloud_jobs"])
    add("")
    add("These are engineering ceilings with no scientific content and no gate")
    add("effect. Any discovery that would change an estimand, interface,")
    add("threshold, item bank, answer surface, candidate ladder, task definition")
    add("or gate logic is outside shakedown authority and produces")
    add("`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`.")
    add("")
    add("The negative control is quantitative: its exact one-sided upper")
    add("confidence bound must lie strictly below `%s`."
        % constants["negative_control_equivalence_upper_bound_exact_rational"])
    add("\"Not significantly above chance\" is not an equivalence demonstration.")
    add("")

    add("## Recursive-manifest seal `[V07-D11]`")
    add("")
    add("The seal covers all decision-bearing bytes, seals both inclusion globs")
    add("and an explicit exclusion list, and includes and hashes the")
    add("manifest-generation script itself. The construction is **two-level**:")
    add("level one hashes every included byte and produces the manifest, level two")
    add("writes the root hash into the terminal record. Neither file contains its")
    add("own hash, so there is no fixed point and the construction is not")
    add("self-referential.")
    add("")

    add("## Activation and causal-claim boundary `[V07-D12]`")
    add("")
    add("Activation collection, J-lens fitting, patching, ablation and mechanism")
    add("inference remain unauthorized until every listed condition passes,")
    add("including RP-M method validation before any natural-model patch claim.")
    add("Checkpoint differences may be described only as checkpoint-level")
    add("associations; a causal claim requires a separate future design with")
    add("matched training interventions and independent seeds.")
    add("")

    add("## Deterministic deferrals `[V07-D14]`")
    add("")
    add("No decision-bearing `TBD` exists. Three values legitimately cannot exist")
    add("before the pre-execution seal, and each carries a deterministic")
    add("acquisition rule and a fail-closed absent state.")
    add("")
    add("| id | value | fail-closed absent state |")
    add("| --- | --- | --- |")
    for entry in document["deterministic_deferrals_v0_7"]["entries"]:
        add("| `%s` | %s | `%s` |"
            % (entry["id"], entry["value"], entry["fail_closed_absent_state"]))
    add("")

    add("## Boundary")
    add("")
    add("`formal_execution_authorized` is `false`. Study 3 is unfrozen,")
    add("unselected and unexecuted. No seed, bank, development result,")
    add("confirmation access, interface, positive reference or evidence row")
    add("exists. `paper/evidence_ledger.csv` still ends at `EV-0016`. The research")
    add("question remains unanswered.")
    add("")
    add("The only legal next action is one fresh independent single focused")
    add("methods review of draft-v0.7 by a party that did not draft it.")
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# The operator amendment
# ---------------------------------------------------------------------------

def build_amendment(document, legacy, bundle, constants) -> dict:
    return {
        "schema_version": AMENDMENT_SCHEMA_VERSION,
        "draft_version": DRAFT_VERSION,
        "disposition": "PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW",
        "state": STATE,
        "self_approval_prohibited":
            "the drafting party does not claim draft-v0.7 is correct; the "
            "determination belongs to a party that did not draft it",
        "authorities": {
            "successor_authority": _file_identity(REPO_ROOT / SUCCESSOR_AUTHORITY),
            "original_amendment_authority":
                _file_identity(REPO_ROOT / ORIGINAL_AUTHORITY),
            "binding_order": [
                SUCCESSOR_AUTHORITY, ORIGINAL_AUTHORITY, TERMINAL_DISPOSITION,
                "earlier Study 3 authorities and immutable history",
            ],
        },
        "operator_decision": {
            "selected": "OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL",
            "rejected": ["OPTION_A_REGISTRY_AS_OMNIBUS_HOME",
                         "OPTION_B_REGENERATE_P0_CORPUS_MANIFEST",
                         "OPTION_C_RETIRE_FROZEN_CORPUS_TEST"],
            "legacy_bundle": {"status": LEGACY_STATUS, "bytes_changed": 0,
                              "files": legacy},
            "p0_corpus_manifest_regenerated": False,
            "frozen_corpus_test_retired_or_weakened": False,
        },
        "new_bundle": bundle,
        "decisions": [
            {"marker": marker, "title": title, "json_key": key,
             "disposition": "PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW"}
            for marker, title, key in DECISIONS
        ],
        "decision_count": len(DECISIONS),
        "derived_constants": constants,
        "deterministic_deferrals": document["deterministic_deferrals_v0_7"],
        "battery_unchanged": True,
        "new_mde_registered": False,
        "four_hundred_cluster_mde_registered": False,
        "p0_r2_historical_treatment": document["p0_r2_historical_treatment_v0_7"],
        "zero_operation_boundary": document["zero_operation_boundary_v0_7"],
        "prohibited_language": list(PROHIBITED_LANGUAGE),
        "evidence_ledger_tail": "EV-0016",
        "formal_execution_authorized": False,
        "frozen": False,
        "research_question_answered": False,
        "focused_review_packet": document["focused_review_packet_v0_7"],
        "review_verdict_contained": False,
        "next_legal_action":
            "one fresh independent single focused methods review of draft-v0.7 "
            "by a party that did not draft it",
    }


def build_amendment_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Study 3 draft-v0.7 operator amendment",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "draft_version", "disposition", "state",
            "self_approval_prohibited", "authorities", "operator_decision",
            "new_bundle", "decisions", "decision_count", "derived_constants",
            "deterministic_deferrals", "battery_unchanged",
            "new_mde_registered", "four_hundred_cluster_mde_registered",
            "p0_r2_historical_treatment", "zero_operation_boundary",
            "prohibited_language", "evidence_ledger_tail",
            "formal_execution_authorized", "frozen",
            "research_question_answered", "focused_review_packet",
            "review_verdict_contained", "next_legal_action",
        ],
        "properties": {
            "schema_version": {"const": AMENDMENT_SCHEMA_VERSION},
            "draft_version": {"const": DRAFT_VERSION},
            "disposition": {"const":
                            "PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW"},
            "state": {"const": STATE},
            "self_approval_prohibited": {"type": "string"},
            "authorities": {"type": "object"},
            "operator_decision": {
                "type": "object",
                "required": ["selected", "rejected",
                             "p0_corpus_manifest_regenerated",
                             "frozen_corpus_test_retired_or_weakened"],
                "properties": {
                    "selected": {"const":
                                 "OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL"},
                    "p0_corpus_manifest_regenerated": {"const": False},
                    "frozen_corpus_test_retired_or_weakened": {"const": False},
                },
            },
            "new_bundle": {"type": "object"},
            "decisions": {"type": "array", "minItems": len(DECISIONS),
                          "items": {"type": "object",
                                    "required": ["marker", "title", "json_key",
                                                 "disposition"]}},
            "decision_count": {"const": len(DECISIONS)},
            "derived_constants": {"type": "object"},
            "deterministic_deferrals": {"type": "object"},
            "battery_unchanged": {"const": True},
            "new_mde_registered": {"const": False},
            "four_hundred_cluster_mde_registered": {"const": False},
            "p0_r2_historical_treatment": {"type": "object"},
            "zero_operation_boundary": {"type": "object"},
            "prohibited_language": {"type": "array", "minItems": 6,
                                    "items": {"type": "string"}},
            "evidence_ledger_tail": {"const": "EV-0016"},
            "formal_execution_authorized": {"const": False},
            "frozen": {"const": False},
            "research_question_answered": {"const": False},
            "focused_review_packet": {
                "type": "object",
                "required": ["contains_a_verdict",
                             "may_automatically_draft_v0_8"],
                "properties": {"contains_a_verdict": {"const": False},
                               "may_automatically_draft_v0_8": {"const": False}},
            },
            "review_verdict_contained": {"const": False},
            "next_legal_action": {"type": "string"},
        },
    }


def build_amendment_markdown(amendment, document, constants) -> bytes:
    lines = []
    add = lines.append
    add("# Study 3 draft-v0.7 operator amendment: the consolidated amendment")
    add("")
    add("> **Disposition:** every decision below is recorded")
    add("> `PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW`.")
    add(">")
    add("> The drafting party does **not** claim draft-v0.7 is correct.")
    add("> draft-v0.7 is **not** reviewed, **not** frozen, **not** selected and")
    add("> **not** formally executable.")
    add("")
    add("State: `%s`" % STATE)
    add("")
    add("Machine-readable form:"
        " [`v0_7_operator_amendment.json`](v0_7_operator_amendment.json).")
    add("")
    add("Normative protocol:")
    add("[`../protocol/interface_calibration_protocol_draft_v0_7.json`]"
        "(../protocol/interface_calibration_protocol_draft_v0_7.json).")
    add("")
    add("## 1. The operator decision this amendment executes")
    add("")
    add("The operator selected `OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL` and")
    add("explicitly rejected Options A, B and C. draft-v0.7 is therefore a new,")
    add("versioned, self-contained normative bundle, and the legacy v0.5 trio is")
    add("preserved byte-exactly as historical P0 input.")
    add("")
    add("| legacy file | sha256 | status |")
    add("| --- | --- | --- |")
    for path, entry in sorted(amendment["operator_decision"]["legacy_bundle"]
                              ["files"].items()):
        add("| `%s` | `%s…` | `%s` |"
            % (path.rsplit("/", 1)[-1], entry["sha256"][:16], LEGACY_STATUS))
    add("")
    add("The P0 corpus manifest was **not** regenerated. The frozen-corpus test")
    add("was **not** retired, weakened, waived or re-scoped.")
    add("")
    add("## 2. The new bundle")
    add("")
    add("| artifact | bytes | sha256 |")
    add("| --- | ---: | --- |")
    for label in ("protocol_json", "protocol_schema", "protocol_markdown",
                  "rendering_registry", "rendering_registry_schema",
                  "current_pointer", "current_pointer_schema"):
        entry = amendment["new_bundle"][label]
        add("| `%s` | %d | `%s…` |"
            % (entry["path"].rsplit("/", 1)[-1], entry["bytes"],
               entry["sha256"][:16]))
    add("")
    add("The current pointer fails closed: a missing, mismatched or invalid v0.7")
    add("file must not cause a loader to fall back to the legacy v0.5 protocol.")
    add("")
    add("## 3. The decisions")
    add("")
    add("| marker | decision | JSON key |")
    add("| --- | --- | --- |")
    for marker, title, key in DECISIONS:
        add("| `%s` | %s | `%s` |" % (marker, title, key))
    add("")
    add("Each is stated normatively in the protocol and its companion Markdown.")
    add("This amendment records them; it does not restate them a third time.")
    add("")
    add("## 4. What changed in the numbers, and what did not")
    add("")
    add("**Unchanged, by regeneration.** The registered I1a/I1b/I2 battery, its")
    add("nulls, alternatives, alphas, sample sizes, pass counts, `m_max` and every")
    add("power floor are byte-compared against `design_statistics.py` output. No")
    add("number is copied forward for continuity, and no new MDE is registered.")
    add("")
    add("**New, and derived rather than chosen.**")
    add("")
    add("| constant | value | derivation |")
    add("| --- | --- | --- |")
    add("| generated-CoT `theta` | `%s` | the registered I2 headroom null |"
        % constants["generated_cot_ceiling_theta_exact_rational"])
    add("| generated-CoT `k` | %d | deterministic decoding; removes the pass@1 "
        "versus majority-vote choice |" % constants["generated_cot_ceiling_k"])
    add("| negative-control bound | `%s` | restricted chance plus the registered "
        "alternative gap |"
        % constants["negative_control_equivalence_upper_bound_exact_rational"])
    add("| wrapper bandwidth | `%s` | the registered alternative gap |"
        % constants["wrapper_descriptive_bandwidth_exact_rational"])
    add("| E0 `max_new_tokens` | %d | two answer tokens plus a one-token EOS "
        "margin |" % constants["e0_max_new_tokens"])
    add("| reproducibility tolerance | %d | the decision statistic is an integer "
        "count |" % constants["reproducibility_tolerance"])
    add("")
    add("**Deterministically deferred.** Three values legitimately cannot exist")
    add("before the pre-execution seal. Each has a deterministic acquisition rule")
    add("and a fail-closed absent state, and none is a `TBD`.")
    add("")
    add("| id | value | fail-closed absent state |")
    add("| --- | --- | --- |")
    for entry in document["deterministic_deferrals_v0_7"]["entries"]:
        add("| `%s` | %s | `%s` |"
            % (entry["id"], entry["value"], entry["fail_closed_absent_state"]))
    add("")
    add("`DEFER-02` remains blocked on `OD2`, which this amendment does not")
    add("resolve: it freezes the eligibility predicate and the ordering rule, and")
    add("leaves ladder membership to the pre-execution seal.")
    add("")
    add("## 5. Inherited P0-R2 disposition")
    add("")
    add("Recorded without repair as")
    add("`P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS`: the generation-2 live")
    add("replay mechanically passed and was independently reconstructed, bounded")
    add("pilot authorization failed, no GPU job was created or started, model,")
    add("tokenizer, scoring and GPU counters remained zero, the evidence ledger")
    add("remained at `EV-0016` and the research question remained unanswered.")
    add("")
    add("The four governance audit exceptions are recorded verbatim in the")
    add("machine-readable form. This amendment does not write \"full authority")
    add("compliance verified\" or \"zero force-pushes verified\", and it treats no")
    add("P0 infrastructure result as scientific evidence.")
    add("")
    add("## 6. Boundary")
    add("")
    add("`formal_execution_authorized = false`. Study 3 is unfrozen, unselected")
    add("and unexecuted. Every prohibited operation counter is zero.")
    add("`paper/evidence_ledger.csv` is byte-identical and still ends at")
    add("`EV-0016`. The research question remains unanswered.")
    add("")
    add("## 7. The only legal next action")
    add("")
    add("One fresh, independent, single focused methods review of draft-v0.7 by a")
    add("party that did not draft it. It may return only its registered acceptance")
    add("state or `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`, and it may")
    add("not automatically draft v0.8.")
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Emit and verify
# ---------------------------------------------------------------------------

def assemble():
    legacy = verify_legacy_trio()
    stats = statistics()
    constants = derived_constants(stats)

    registry = build_registry()
    registry_schema = build_registry_schema()
    registry_bytes = canonical_bytes(registry)
    registry_identity = {
        "path": "studies/study3/protocol/"
                "interface_calibration_rendering_registry_v0_7.json",
        "bytes": len(registry_bytes),
        "sha256": _sha256(registry_bytes),
    }

    protocol = build_protocol(legacy, stats, constants, registry_identity)
    protocol_schema = build_protocol_schema(protocol)
    protocol_bytes = canonical_bytes(protocol)
    markdown_bytes = build_markdown(protocol, constants)
    schema_bytes = canonical_bytes(protocol_schema)
    registry_schema_bytes = canonical_bytes(registry_schema)

    identities = {
        "protocol_json": {"path": "studies/study3/protocol/"
                                  "interface_calibration_protocol_draft_v0_7.json",
                          "bytes": len(protocol_bytes),
                          "sha256": _sha256(protocol_bytes)},
        "protocol_schema": {"path": "studies/study3/protocol/"
                            "interface_calibration_protocol_draft_v0_7.schema.json",
                            "bytes": len(schema_bytes),
                            "sha256": _sha256(schema_bytes)},
        "protocol_markdown": {"path": "studies/study3/protocol/"
                              "interface_calibration_protocol_draft_v0_7.md",
                              "bytes": len(markdown_bytes),
                              "sha256": _sha256(markdown_bytes)},
        "rendering_registry": registry_identity,
        "rendering_registry_schema": {
            "path": "studies/study3/protocol/"
                    "interface_calibration_rendering_registry_v0_7.schema.json",
            "bytes": len(registry_schema_bytes),
            "sha256": _sha256(registry_schema_bytes)},
    }

    pointer = build_pointer(identities["protocol_json"],
                            identities["protocol_schema"],
                            identities["protocol_markdown"],
                            registry_identity, legacy)
    pointer_schema = build_pointer_schema()
    pointer_bytes = canonical_bytes(pointer)
    pointer_schema_bytes = canonical_bytes(pointer_schema)
    identities["current_pointer"] = {
        "path": "studies/study3/protocol/"
                "interface_calibration_protocol_current.json",
        "bytes": len(pointer_bytes), "sha256": _sha256(pointer_bytes)}
    identities["current_pointer_schema"] = {
        "path": "studies/study3/protocol/"
                "interface_calibration_protocol_current.schema.json",
        "bytes": len(pointer_schema_bytes),
        "sha256": _sha256(pointer_schema_bytes)}

    amendment = build_amendment(protocol, legacy, identities, constants)
    amendment_schema = build_amendment_schema()
    amendment_bytes = canonical_bytes(amendment)
    amendment_md_bytes = build_amendment_markdown(amendment, protocol, constants)
    amendment_schema_bytes = canonical_bytes(amendment_schema)

    return {
        "documents": {
            "protocol": protocol, "protocol_schema": protocol_schema,
            "registry": registry, "registry_schema": registry_schema,
            "pointer": pointer, "pointer_schema": pointer_schema,
            "amendment": amendment, "amendment_schema": amendment_schema,
        },
        "files": [
            (V0_7_JSON, protocol_bytes),
            (V0_7_SCHEMA, schema_bytes),
            (V0_7_MD, markdown_bytes),
            (V0_7_REGISTRY, registry_bytes),
            (V0_7_REGISTRY_SCHEMA, registry_schema_bytes),
            (CURRENT_POINTER, pointer_bytes),
            (CURRENT_POINTER_SCHEMA, pointer_schema_bytes),
            (AMENDMENT_JSON, amendment_bytes),
            (AMENDMENT_SCHEMA, amendment_schema_bytes),
            (AMENDMENT_MD, amendment_md_bytes),
        ],
        "identities": identities,
        "legacy": legacy,
        "constants": constants,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        built = assemble()
    except BuildDefect as exc:
        print("STUDY3_V0_7_BUILD_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    if args.write:
        for path, payload in built["files"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            print("wrote %s (%d bytes)"
                  % (path.relative_to(REPO_ROOT), len(payload)))
        print("STUDY3_V0_7_BUNDLE_WRITTEN=1")
        return 0

    differing = []
    for path, payload in built["files"]:
        if not path.exists() or path.read_bytes() != payload:
            differing.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    if differing:
        print("STUDY3_V0_7_BUILD_DIFFERS=1 %s" % ", ".join(differing),
              file=sys.stderr)
        return 3
    print("STUDY3_V0_7_BUNDLE_REPRODUCES=1 files=%d" % len(built["files"]))
    print("STUDY3_V0_7_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
