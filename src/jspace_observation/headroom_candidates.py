"""Deterministic, model-free construction of Phase 1 capability-headroom tasks."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "phase1-headroom-candidate-v1"
GENERATOR_VERSION = "phase1-headroom-generator-v1"
SEED_RULE_VERSION = "phase1-headroom-seed-v1"

TASK_FAMILIES = (
    "arithmetic",
    "synthetic_relation",
    "prompt_grounded_two_hop_factual",
    "counterfactual_entity_replacement",
    "wrong_cot_error_detection",
)
DIFFICULTY_BANDS = ("easy", "medium", "hard")
SPLITS = ("calibration", "confirmation", "mechanistic")
ITEMS_PER_CELL = 10
TEMPLATE_FAMILIES_PER_CELL = 5

TOP_LEVEL_FIELDS = (
    "task_id",
    "task_family",
    "difficulty_band",
    "split",
    "template_family_id",
    "prompt_template",
    "question",
    "registered_answer",
    "intermediate_concept",
    "concept_tokenization_requirement",
    "clean_corrupted_pair_availability",
    "jlens_suitability",
    "patching_suitability",
    "ablation_suitability",
    "ability_match_suitability",
    "clean_corrupted_pair",
    "metadata",
)

TOKENIZATION_FIELDS = (
    "surface_form",
    "required",
    "required_token_count",
    "registration_status",
    "registration_stage",
    "failure_action",
)
PAIR_AVAILABILITY_FIELDS = (
    "applicable",
    "available",
    "pair_id",
    "minimal_surface_change",
    "different_registered_answers",
)
JLENS_FIELDS = (
    "design_candidate",
    "eligibility_status",
    "evidence_role",
    "non_final_necessary_intermediate",
    "tokenizer_registered_concept_required",
    "matched_control_required",
    "prompt_echo_control_required",
    "strict_answer_only_correct_required",
    "readout_scope",
)
PATCHING_FIELDS = (
    "design_candidate",
    "eligibility_status",
    "minimal_clean_corrupt_difference",
    "different_registered_answers",
    "token_position_alignment_required",
    "both_baselines_correct_required",
    "scan",
    "controls_required",
)
ABLATION_FIELDS = (
    "design_candidate",
    "eligibility_status",
    "substantial_prompt_only_strict_headroom_required",
    "disjoint_learning_templates_required",
    "enough_baseline_correct_cases_required",
    "controls_required",
    "success_rule",
)
ABILITY_FIELDS = (
    "design_candidate",
    "eligibility_status",
    "prompt_grounded_facts_required",
    "same_evaluator_and_profile_required",
    "nonmaterial_truncation_required",
    "held_out_template_confirmation_required",
    "equivalence_rule",
)
PAIR_FIELDS = ("pair_id", "clean", "corrupted", "intervention")
PAIR_SIDE_FIELDS = ("question", "registered_answer", "intermediate_concept")
INTERVENTION_FIELDS = (
    "type",
    "clean_span",
    "corrupted_span",
    "surface_token_mismatches",
    "position_alignment",
    "target_token_alignment_status",
)
METADATA_FIELDS = (
    "schema_version",
    "generator",
    "item_index",
    "template_variant",
    "strict_answer_only",
    "facts",
    "corrupted_facts",
    "entity_ids",
    "answer_type",
    "reference",
    "corrupted_reference",
    "balance",
    "controls",
    "future_evaluation",
    "difficulty_parameters",
    "template_slots",
)

_FAMILY_CODES = {
    "arithmetic": "arith",
    "synthetic_relation": "rel",
    "prompt_grounded_two_hop_factual": "fact2",
    "counterfactual_entity_replacement": "cf",
    "wrong_cot_error_detection": "err",
}
_ENTITY_PREFIXES = {
    "calibration": "Cal",
    "confirmation": "Con",
    "mechanistic": "Mec",
}
_BAND_CODES = {"easy": "E", "medium": "M", "hard": "H"}

_SCAFFOLDS = {
    "calibration": (
        (
            "Use only the material supplied below.",
            "Supplied material",
            "Question",
            "Return only the {answer_format}; do not explain.",
        ),
        (
            "Treat this card as a closed world.",
            "Card entries",
            "Resolve",
            "Output exactly one {answer_format} and nothing else.",
        ),
        (
            "All information needed for this item follows.",
            "Given lines",
            "Task",
            "Answer with only the {answer_format}.",
        ),
        (
            "Reason from the local record, not outside knowledge.",
            "Local record",
            "Query",
            "Write only the {answer_format}; omit reasoning.",
        ),
        (
            "The statements in this block are authoritative.",
            "Statement block",
            "Requested result",
            "Provide the {answer_format} alone.",
        ),
    ),
    "confirmation": (
        (
            "Consult solely the enclosed evidence panel.",
            "Evidence panel",
            "Determine",
            "Respond with just the {answer_format}, without commentary.",
        ),
        (
            "Solve the item under the miniature world shown here.",
            "Miniature world",
            "Prompt",
            "Your entire response must be one {answer_format}.",
        ),
        (
            "Ignore background knowledge and use this dossier only.",
            "Dossier",
            "Decision",
            "Emit only the {answer_format}.",
        ),
        (
            "The following ledger fully defines the problem.",
            "Ledger",
            "Lookup",
            "Give a bare {answer_format}, with no derivation.",
        ),
        (
            "Work exclusively from the self-contained note.",
            "Self-contained note",
            "Required answer",
            "Return one {answer_format} only.",
        ),
    ),
    "mechanistic": (
        (
            "Take the compact specification below as complete.",
            "Specification",
            "Compute",
            "Print only the {answer_format}; no other tokens.",
        ),
        (
            "Apply the rules in this isolated worksheet.",
            "Worksheet",
            "Target",
            "The response is exactly the {answer_format}.",
        ),
        (
            "Use the enclosed entries as the full source of truth.",
            "Entries",
            "Find",
            "Supply only one {answer_format}.",
        ),
        (
            "Evaluate this standalone record exactly as written.",
            "Standalone record",
            "Requested output",
            "Output the {answer_format} alone, without steps.",
        ),
        (
            "No facts beyond this bounded packet are relevant.",
            "Bounded packet",
            "Answer request",
            "Reply solely with the {answer_format}.",
        ),
    ),
}

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class CandidateBankValidationError(ValueError):
    """Raised when generated or loaded candidate records violate the protocol."""


def derive_run_seed(
    task_id: str,
    condition: str,
    budget: int,
    profile: str,
    replicate_index: int = 0,
) -> int:
    """Derive a frozen unsigned 64-bit seed from canonical run coordinates."""

    canonical = "\0".join(
        (
            SEED_RULE_VERSION,
            task_id,
            condition,
            str(budget),
            profile,
            str(replicate_index),
        )
    )
    return int.from_bytes(sha256(canonical.encode("utf-8")).digest()[:8], "big")


def _task_id(
    family: str,
    band: str,
    split: str,
    item_index: int,
) -> str:
    return (
        f"p1hd-{_FAMILY_CODES[family]}-{band}-{split}-{item_index + 1:02d}"
    )


def _template_id(
    family: str,
    band: str,
    split: str,
    variant: int,
) -> str:
    return f"p1hd-tpl-{_FAMILY_CODES[family]}-{band}-{split}-{variant + 1}"


def _entity(
    split: str,
    family_code: str,
    band: str,
    item_index: int,
    role: str,
) -> str:
    return (
        f"{_ENTITY_PREFIXES[split]}{family_code}{_BAND_CODES[band]}"
        f"{item_index + 1:02d}{role}"
    )


def _render_prompt(
    split: str,
    variant: int,
    facts: Sequence[str],
    query: str,
    answer_format: str,
    fact_templates: Sequence[str],
    query_template: str,
) -> tuple[str, str]:
    intro, facts_heading, query_heading, closing_template = _SCAFFOLDS[split][
        variant
    ]
    closing = closing_template.format(answer_format=answer_format)
    question = "\n".join(
        (
            intro,
            f"{facts_heading}:",
            *(f"- {fact}" for fact in facts),
            f"{query_heading}: {query}",
            closing,
        )
    )
    prompt_template = "\n".join(
        (
            intro,
            f"{facts_heading}:",
            *(f"- {fact}" for fact in fact_templates),
            f"{query_heading}: {query_template}",
            closing,
        )
    )
    return prompt_template, question


def _token_mismatches(left: str, right: str) -> int:
    left_tokens = _TOKEN_RE.findall(left)
    right_tokens = _TOKEN_RE.findall(right)
    if len(left_tokens) != len(right_tokens):
        return max(len(left_tokens), len(right_tokens))
    return sum(a != b for a, b in zip(left_tokens, right_tokens))


def _apply_operation(left: int, operator: str, right: int) -> int:
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator in {"*", "×"}:
        return left * right
    raise ValueError(f"Unsupported operator: {operator}")


def _pipeline(start: int, operations: Sequence[tuple[str, int]]) -> list[int]:
    values = []
    current = start
    for operator, operand in operations:
        current = _apply_operation(current, operator, operand)
        values.append(current)
    return values


def _tokenization_requirement(concept: str) -> dict[str, Any]:
    return {
        "surface_form": concept,
        "required": True,
        "required_token_count": 1,
        "registration_status": "pending_frozen_tokenizer_registration",
        "registration_stage": "future_calibration_before_cell_freeze",
        "failure_action": "exclude_or_replace_candidate_before_cell_freeze",
    }


def _suitability(
    family: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    primary_rq2 = family != "arithmetic"
    jlens = {
        "design_candidate": True,
        "eligibility_status": "pending_future_calibration",
        "evidence_role": "rq2_candidate" if primary_rq2 else "sanity_only",
        "non_final_necessary_intermediate": True,
        "tokenizer_registered_concept_required": True,
        "matched_control_required": True,
        "prompt_echo_control_required": True,
        "strict_answer_only_correct_required": True,
        "readout_scope": "non_motor_non_output_layers_only",
    }
    patching = {
        "design_candidate": True,
        "eligibility_status": "pending_future_calibration",
        "minimal_clean_corrupt_difference": True,
        "different_registered_answers": True,
        "token_position_alignment_required": True,
        "both_baselines_correct_required": True,
        "scan": "layer_by_position",
        "controls_required": [
            "corrupt_to_corrupt",
            "clean_to_clean",
            "random_position",
            "motor_output_position",
        ],
    }
    ablation = {
        "design_candidate": primary_rq2,
        "eligibility_status": (
            "pending_future_calibration"
            if primary_rq2
            else "excluded_arithmetic_sanity_only"
        ),
        "substantial_prompt_only_strict_headroom_required": True,
        "disjoint_learning_templates_required": True,
        "enough_baseline_correct_cases_required": True,
        "controls_required": [
            "matched_norm",
            "random_direction",
            "non_workspace",
            "motor_output",
        ],
        "success_rule": "task_clustered_difference_in_differences_ci_excludes_zero",
    }
    ability = {
        "design_candidate": primary_rq2,
        "eligibility_status": (
            "pending_future_calibration"
            if primary_rq2
            else "excluded_arithmetic_sanity_only"
        ),
        "prompt_grounded_facts_required": True,
        "same_evaluator_and_profile_required": True,
        "nonmaterial_truncation_required": True,
        "held_out_template_confirmation_required": True,
        "equivalence_rule": "task_clustered_equivalence_ci_within_frozen_margin",
    }
    return jlens, patching, ablation, ability


def _parser_metadata(answer_type: str, maximum_step: int | None = None) -> dict[str, Any]:
    if answer_type == "numeric":
        route = "parser_v2_after_separately_authorized_locked_numeric_pass"
        codebook = None
    elif answer_type == "numeric_step_code":
        route = "parser_v2_preregistered_numeric_coding_after_locked_numeric_pass"
        codebook = {
            str(step): f"STEP_{step}" for step in range(1, (maximum_step or 0) + 1)
        }
    else:
        route = "separately_locked_typed_entity_evaluator_required"
        codebook = None
    return {
        "parser_route": route,
        "numeric_codebook": codebook,
        "semantic_review_required": True,
        "locked_evaluator_required": True,
    }


def _matched_control_id(
    family: str,
    band: str,
    split: str,
    item_index: int,
) -> str:
    matched_index = item_index + 5 if item_index < 5 else item_index - 5
    return _task_id(family, band, split, matched_index)


def _make_record(
    *,
    family: str,
    band: str,
    split: str,
    item_index: int,
    prompt_template: str,
    clean_question: str,
    corrupted_question: str,
    answer: str,
    corrupted_answer: str,
    concept: str,
    corrupted_concept: str,
    facts: Sequence[str],
    corrupted_facts: Sequence[str],
    entity_ids: Sequence[str],
    answer_type: str,
    reference: Mapping[str, Any],
    corrupted_reference: Mapping[str, Any],
    difficulty_parameters: Mapping[str, Any],
    template_slots: Mapping[str, Any],
    intervention_type: str,
    clean_span: str,
    corrupted_span: str,
    maximum_step: int | None = None,
) -> dict[str, Any]:
    task_id = _task_id(family, band, split, item_index)
    pair_id = f"{task_id}:clean-corrupt"
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    jlens, patching, ablation, ability = _suitability(family)
    mismatch_count = _token_mismatches(clean_question, corrupted_question)
    return {
        "task_id": task_id,
        "task_family": family,
        "difficulty_band": band,
        "split": split,
        "template_family_id": _template_id(family, band, split, variant),
        "prompt_template": prompt_template,
        "question": clean_question,
        "registered_answer": answer,
        "intermediate_concept": concept,
        "concept_tokenization_requirement": _tokenization_requirement(concept),
        "clean_corrupted_pair_availability": {
            "applicable": True,
            "available": True,
            "pair_id": pair_id,
            "minimal_surface_change": mismatch_count == 1,
            "different_registered_answers": answer != corrupted_answer,
        },
        "jlens_suitability": jlens,
        "patching_suitability": patching,
        "ablation_suitability": ablation,
        "ability_match_suitability": ability,
        "clean_corrupted_pair": {
            "pair_id": pair_id,
            "clean": {
                "question": clean_question,
                "registered_answer": answer,
                "intermediate_concept": concept,
            },
            "corrupted": {
                "question": corrupted_question,
                "registered_answer": corrupted_answer,
                "intermediate_concept": corrupted_concept,
            },
            "intervention": {
                "type": intervention_type,
                "clean_span": clean_span,
                "corrupted_span": corrupted_span,
                "surface_token_mismatches": mismatch_count,
                "position_alignment": "same_rendered_template_slot",
                "target_token_alignment_status": (
                    "pending_frozen_tokenizer_registration"
                ),
            },
        },
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generator": GENERATOR_VERSION,
            "item_index": item_index,
            "template_variant": variant,
            "strict_answer_only": True,
            "facts": list(facts),
            "corrupted_facts": list(corrupted_facts),
            "entity_ids": list(entity_ids),
            "answer_type": answer_type,
            "reference": dict(reference),
            "corrupted_reference": dict(corrupted_reference),
            "balance": {
                "answer_key": answer,
                "concept_key": concept,
            },
            "controls": {
                "matched_control_task_id": _matched_control_id(
                    family, band, split, item_index
                ),
                "matched_control_rule": (
                    "same cell and template family; different answer and concept"
                ),
                "prompt_echo_control": {
                    "required": True,
                    "control_id": f"{task_id}:prompt-echo",
                    "construction": (
                        "same template and answer type with the concept surface "
                        "form placed in an answer-irrelevant slot"
                    ),
                    "eligibility_status": "pending_baseline_check",
                },
            },
            "future_evaluation": _parser_metadata(answer_type, maximum_step),
            "difficulty_parameters": dict(difficulty_parameters),
            "template_slots": dict(template_slots),
        },
    }


def _generate_arithmetic(
    band: str,
    split: str,
    item_index: int,
) -> dict[str, Any]:
    band_index = DIFFICULTY_BANDS.index(band)
    split_index = SPLITS.index(split)
    start = 101 + split_index * 1000 + band_index * 300 + item_index * 17
    addend = 11 + item_index * 2
    multiplier = 2 + item_index % 4
    subtractor = 3 + item_index % 7
    final_addend = 19 + item_index
    corrupted_start = start + 7

    if band == "easy":
        operations = [("+", addend), ("*", multiplier)]
        expression = f"({start} + {addend}) × {multiplier}"
        corrupted_expression = (
            f"({corrupted_start} + {addend}) × {multiplier}"
        )
        expression_template = "({start} + {addend}) × {multiplier}"
        concept_step = 1
    elif band == "medium":
        operations = [
            ("+", addend),
            ("*", multiplier),
            ("-", subtractor),
        ]
        expression = (
            f"(({start} + {addend}) × {multiplier}) - {subtractor}"
        )
        corrupted_expression = (
            f"(({corrupted_start} + {addend}) × {multiplier}) - {subtractor}"
        )
        expression_template = (
            "(({start} + {addend}) × {multiplier}) - {subtractor}"
        )
        concept_step = 2
    else:
        operations = [
            ("+", addend),
            ("*", multiplier),
            ("-", subtractor),
            ("+", final_addend),
        ]
        expression = (
            f"((({start} + {addend}) × {multiplier}) - {subtractor}) "
            f"+ {final_addend}"
        )
        corrupted_expression = (
            f"((({corrupted_start} + {addend}) × {multiplier}) - "
            f"{subtractor}) + {final_addend}"
        )
        expression_template = (
            "((({start} + {addend}) × {multiplier}) - {subtractor}) "
            "+ {final_addend}"
        )
        concept_step = 2

    clean_values = _pipeline(start, operations)
    corrupted_values = _pipeline(corrupted_start, operations)
    facts = [f"Expression: {expression}."]
    corrupted_facts = [f"Expression: {corrupted_expression}."]
    fact_templates = [f"Expression: {expression_template}."]
    query = "What is the exact integer value of the expression?"
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    prompt_template, clean_question = _render_prompt(
        split,
        variant,
        facts,
        query,
        "integer",
        fact_templates,
        "What is the exact integer value of the expression?",
    )
    _, corrupted_question = _render_prompt(
        split,
        variant,
        corrupted_facts,
        query,
        "integer",
        fact_templates,
        "What is the exact integer value of the expression?",
    )
    reference = {
        "kind": "arithmetic_pipeline",
        "start": start,
        "operations": [[operator, value] for operator, value in operations],
        "intermediate_values": clean_values,
        "concept_step": concept_step,
        "answer": str(clean_values[-1]),
    }
    corrupted_reference = {
        "kind": "arithmetic_pipeline",
        "start": corrupted_start,
        "operations": [[operator, value] for operator, value in operations],
        "intermediate_values": corrupted_values,
        "concept_step": concept_step,
        "answer": str(corrupted_values[-1]),
    }
    return _make_record(
        family="arithmetic",
        band=band,
        split=split,
        item_index=item_index,
        prompt_template=prompt_template,
        clean_question=clean_question,
        corrupted_question=corrupted_question,
        answer=str(clean_values[-1]),
        corrupted_answer=str(corrupted_values[-1]),
        concept=str(clean_values[concept_step - 1]),
        corrupted_concept=str(corrupted_values[concept_step - 1]),
        facts=facts,
        corrupted_facts=corrupted_facts,
        entity_ids=[],
        answer_type="numeric",
        reference=reference,
        corrupted_reference=corrupted_reference,
        difficulty_parameters={
            "operation_count": len(operations),
            "parenthesized": True,
            "external_knowledge_required": False,
        },
        template_slots={
            "start": start,
            "addend": addend,
            "multiplier": multiplier,
            "subtractor": subtractor,
            "final_addend": final_addend,
        },
        intervention_type="single_operand_replacement",
        clean_span=str(start),
        corrupted_span=str(corrupted_start),
    )


def _path_facts(path: Sequence[str]) -> list[str]:
    return [
        f"{source} points to {target}."
        for source, target in zip(path, path[1:])
    ]


def _generate_synthetic_relation(
    band: str,
    split: str,
    item_index: int,
) -> dict[str, Any]:
    hops = {"easy": 2, "medium": 3, "hard": 4}[band]
    distractor_count = {"easy": 1, "medium": 2, "hard": 3}[band]
    root = _entity(split, "Rel", band, item_index, "Root")
    clean_tail = [
        _entity(split, "Rel", band, item_index, f"A{position}")
        for position in range(1, hops + 1)
    ]
    corrupted_tail = [
        _entity(split, "Rel", band, item_index, f"B{position}")
        for position in range(1, hops + 1)
    ]
    clean_path = [root, *clean_tail]
    corrupted_path = [root, *corrupted_tail]
    selected_fact = f"{root} points to {clean_tail[0]}."
    corrupted_selected_fact = f"{root} points to {corrupted_tail[0]}."
    clean_branch_facts = _path_facts(clean_tail)
    corrupted_branch_facts = _path_facts(corrupted_tail)
    distractor_paths = []
    distractor_entities = []
    for distractor_index in range(distractor_count):
        source = _entity(
            split, "Rel", band, item_index, f"D{distractor_index + 1}S"
        )
        target = _entity(
            split, "Rel", band, item_index, f"D{distractor_index + 1}T"
        )
        distractor_entities.extend((source, target))
        distractor_paths.append(f"{source} points to {target}.")

    facts = [
        selected_fact,
        *clean_branch_facts,
        *corrupted_branch_facts,
        *distractor_paths,
    ]
    corrupted_facts = [
        corrupted_selected_fact,
        *clean_branch_facts,
        *corrupted_branch_facts,
        *distractor_paths,
    ]
    fact_templates = [
        "{root} points to {selected_first}.",
        *(
            f"{{clean_{position}}} points to {{clean_{position + 1}}}."
            for position in range(1, hops)
        ),
        *(
            f"{{alternate_{position}}} points to "
            f"{{alternate_{position + 1}}}."
            for position in range(1, hops)
        ),
        *(
            f"{{distractor_{index}_source}} points to "
            f"{{distractor_{index}_target}}."
            for index in range(1, distractor_count + 1)
        ),
    ]
    query = (
        f"Starting at {root}, where do exactly {hops} successive pointers end?"
    )
    query_template = (
        f"Starting at {{root}}, where do exactly {hops} successive pointers end?"
    )
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    prompt_template, clean_question = _render_prompt(
        split,
        variant,
        facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    _, corrupted_question = _render_prompt(
        split,
        variant,
        corrupted_facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    all_entities = [
        root,
        *clean_tail,
        *corrupted_tail,
        *distractor_entities,
    ]
    reference = {
        "kind": "directed_path",
        "path": clean_path,
        "hops": hops,
        "answer": clean_tail[-1],
        "concept_index": 1,
    }
    corrupted_reference = {
        "kind": "directed_path",
        "path": corrupted_path,
        "hops": hops,
        "answer": corrupted_tail[-1],
        "concept_index": 1,
    }
    return _make_record(
        family="synthetic_relation",
        band=band,
        split=split,
        item_index=item_index,
        prompt_template=prompt_template,
        clean_question=clean_question,
        corrupted_question=corrupted_question,
        answer=clean_tail[-1],
        corrupted_answer=corrupted_tail[-1],
        concept=clean_tail[0],
        corrupted_concept=corrupted_tail[0],
        facts=facts,
        corrupted_facts=corrupted_facts,
        entity_ids=all_entities,
        answer_type="entity",
        reference=reference,
        corrupted_reference=corrupted_reference,
        difficulty_parameters={
            "relation_hops": hops,
            "distractor_edges": distractor_count,
            "external_knowledge_required": False,
        },
        template_slots={
            "root": root,
            "selected_first": clean_tail[0],
            "alternate_first": corrupted_tail[0],
            "hops": hops,
        },
        intervention_type="root_edge_target_replacement",
        clean_span=clean_tail[0],
        corrupted_span=corrupted_tail[0],
    )


def _generate_prompt_grounded_factual(
    band: str,
    split: str,
    item_index: int,
) -> dict[str, Any]:
    distractor_paths = {"easy": 0, "medium": 2, "hard": 4}[band]
    artifact = _entity(split, "Fact", band, item_index, "Artifact")
    clean_region = _entity(split, "Fact", band, item_index, "RegionA")
    corrupted_region = _entity(split, "Fact", band, item_index, "RegionB")
    clean_seat = _entity(split, "Fact", band, item_index, "SeatA")
    corrupted_seat = _entity(split, "Fact", band, item_index, "SeatB")
    selected_fact = f"{artifact} is catalogued in {clean_region}."
    corrupted_selected_fact = (
        f"{artifact} is catalogued in {corrupted_region}."
    )
    lookup_facts = [
        f"The recorded seat of {clean_region} is {clean_seat}.",
        f"The recorded seat of {corrupted_region} is {corrupted_seat}.",
    ]
    distractor_facts = []
    distractor_entities = []
    for distractor_index in range(distractor_paths):
        other_artifact = _entity(
            split, "Fact", band, item_index, f"Other{distractor_index + 1}"
        )
        other_region = _entity(
            split, "Fact", band, item_index, f"Else{distractor_index + 1}"
        )
        other_seat = _entity(
            split, "Fact", band, item_index, f"OtherSeat{distractor_index + 1}"
        )
        distractor_entities.extend(
            (other_artifact, other_region, other_seat)
        )
        distractor_facts.extend(
            (
                f"{other_artifact} is catalogued in {other_region}.",
                f"The recorded seat of {other_region} is {other_seat}.",
            )
        )
    facts = [selected_fact, *lookup_facts, *distractor_facts]
    corrupted_facts = [
        corrupted_selected_fact,
        *lookup_facts,
        *distractor_facts,
    ]
    fact_templates = [
        "{artifact} is catalogued in {selected_region}.",
        "The recorded seat of {region_a} is {seat_a}.",
        "The recorded seat of {region_b} is {seat_b}.",
        *(
            template
            for index in range(1, distractor_paths + 1)
            for template in (
                f"{{other_artifact_{index}}} is catalogued in "
                f"{{other_region_{index}}}.",
                f"The recorded seat of {{other_region_{index}}} is "
                f"{{other_seat_{index}}}.",
            )
        ),
    ]
    query = (
        f"According to this gazetteer, what is the recorded seat associated "
        f"with {artifact}?"
    )
    query_template = (
        "According to this gazetteer, what is the recorded seat associated "
        "with {artifact}?"
    )
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    prompt_template, clean_question = _render_prompt(
        split,
        variant,
        facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    _, corrupted_question = _render_prompt(
        split,
        variant,
        corrupted_facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    first_hop = {artifact: clean_region}
    corrupted_first_hop = {artifact: corrupted_region}
    second_hop = {
        clean_region: clean_seat,
        corrupted_region: corrupted_seat,
    }
    reference = {
        "kind": "two_hop_lookup",
        "start": artifact,
        "first_hop": first_hop,
        "second_hop": second_hop,
        "intermediate": clean_region,
        "answer": clean_seat,
    }
    corrupted_reference = {
        "kind": "two_hop_lookup",
        "start": artifact,
        "first_hop": corrupted_first_hop,
        "second_hop": second_hop,
        "intermediate": corrupted_region,
        "answer": corrupted_seat,
    }
    all_entities = [
        artifact,
        clean_region,
        corrupted_region,
        clean_seat,
        corrupted_seat,
        *distractor_entities,
    ]
    return _make_record(
        family="prompt_grounded_two_hop_factual",
        band=band,
        split=split,
        item_index=item_index,
        prompt_template=prompt_template,
        clean_question=clean_question,
        corrupted_question=corrupted_question,
        answer=clean_seat,
        corrupted_answer=corrupted_seat,
        concept=clean_region,
        corrupted_concept=corrupted_region,
        facts=facts,
        corrupted_facts=corrupted_facts,
        entity_ids=all_entities,
        answer_type="entity",
        reference=reference,
        corrupted_reference=corrupted_reference,
        difficulty_parameters={
            "lookup_hops": 2,
            "distractor_paths": distractor_paths,
            "external_knowledge_required": False,
        },
        template_slots={
            "artifact": artifact,
            "selected_region": clean_region,
            "alternate_region": corrupted_region,
        },
        intervention_type="first_hop_entity_replacement",
        clean_span=clean_region,
        corrupted_span=corrupted_region,
    )


def _generate_counterfactual(
    band: str,
    split: str,
    item_index: int,
) -> dict[str, Any]:
    total_hops = {"easy": 2, "medium": 3, "hard": 4}[band]
    item = _entity(split, "Cf", band, item_index, "Item")
    base_keeper = _entity(split, "Cf", band, item_index, "Base")
    clean_nodes = [
        _entity(split, "Cf", band, item_index, f"A{position}")
        for position in range(1, total_hops + 1)
    ]
    corrupted_nodes = [
        _entity(split, "Cf", band, item_index, f"B{position}")
        for position in range(1, total_hops + 1)
    ]
    base_nodes = [
        base_keeper,
        *(
            _entity(split, "Cf", band, item_index, f"Base{position}")
            for position in range(2, total_hops + 1)
        ),
    ]
    assignment_fact = f"{item} is assigned to {base_keeper}."
    clean_route_facts = _path_facts(clean_nodes)
    corrupted_route_facts = _path_facts(corrupted_nodes)
    base_route_facts = _path_facts(base_nodes)
    directive = (
        f"For this question only, replace {base_keeper} with {clean_nodes[0]} "
        f"in the assignment fact."
    )
    corrupted_directive = (
        f"For this question only, replace {base_keeper} with "
        f"{corrupted_nodes[0]} in the assignment fact."
    )
    facts = [
        assignment_fact,
        *clean_route_facts,
        *corrupted_route_facts,
        *base_route_facts,
        directive,
    ]
    corrupted_facts = [
        assignment_fact,
        *clean_route_facts,
        *corrupted_route_facts,
        *base_route_facts,
        corrupted_directive,
    ]
    fact_templates = [
        "{item} is assigned to {base_keeper}.",
        *(
            f"{{clean_{position}}} points to {{clean_{position + 1}}}."
            for position in range(1, total_hops)
        ),
        *(
            f"{{alternate_{position}}} points to "
            f"{{alternate_{position + 1}}}."
            for position in range(1, total_hops)
        ),
        *(
            f"{{base_{position}}} points to {{base_{position + 1}}}."
            for position in range(1, total_hops)
        ),
        (
            "For this question only, replace {base_keeper} with "
            "{replacement_keeper} in the assignment fact."
        ),
    ]
    query = (
        f"After applying the replacement, start at {item} and follow the "
        f"assignment plus pointers. Which terminal entity is reached?"
    )
    query_template = (
        "After applying the replacement, start at {item} and follow the "
        "assignment plus pointers. Which terminal entity is reached?"
    )
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    prompt_template, clean_question = _render_prompt(
        split,
        variant,
        facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    _, corrupted_question = _render_prompt(
        split,
        variant,
        corrupted_facts,
        query,
        "entity label",
        fact_templates,
        query_template,
    )
    clean_path = [item, *clean_nodes]
    corrupted_path = [item, *corrupted_nodes]
    reference = {
        "kind": "counterfactual_replacement_path",
        "base_entity": base_keeper,
        "replacement": clean_nodes[0],
        "path": clean_path,
        "hops": total_hops,
        "answer": clean_nodes[-1],
        "concept_index": 1,
    }
    corrupted_reference = {
        "kind": "counterfactual_replacement_path",
        "base_entity": base_keeper,
        "replacement": corrupted_nodes[0],
        "path": corrupted_path,
        "hops": total_hops,
        "answer": corrupted_nodes[-1],
        "concept_index": 1,
    }
    all_entities = [
        item,
        base_keeper,
        *clean_nodes,
        *corrupted_nodes,
        *base_nodes[1:],
    ]
    return _make_record(
        family="counterfactual_entity_replacement",
        band=band,
        split=split,
        item_index=item_index,
        prompt_template=prompt_template,
        clean_question=clean_question,
        corrupted_question=corrupted_question,
        answer=clean_nodes[-1],
        corrupted_answer=corrupted_nodes[-1],
        concept=clean_nodes[0],
        corrupted_concept=corrupted_nodes[0],
        facts=facts,
        corrupted_facts=corrupted_facts,
        entity_ids=all_entities,
        answer_type="entity",
        reference=reference,
        corrupted_reference=corrupted_reference,
        difficulty_parameters={
            "counterfactual_path_hops": total_hops,
            "scoped_replacement": True,
            "external_knowledge_required": False,
        },
        template_slots={
            "item": item,
            "base_keeper": base_keeper,
            "replacement_keeper": clean_nodes[0],
        },
        intervention_type="counterfactual_replacement_target_change",
        clean_span=clean_nodes[0],
        corrupted_span=corrupted_nodes[0],
    )


def _first_incorrect_reference(
    start: int,
    variables: Sequence[int],
    operations: Sequence[str],
    displayed: Sequence[int],
) -> tuple[int, list[int]]:
    previous = start
    first_incorrect = 0
    expected_values = []
    for step, (operator, operand, shown) in enumerate(
        zip(operations, variables, displayed),
        start=1,
    ):
        expected = _apply_operation(previous, operator, operand)
        expected_values.append(expected)
        if not first_incorrect and expected != shown:
            first_incorrect = step
        previous = shown
    if not first_incorrect:
        raise ValueError("Wrong-CoT construction unexpectedly has no error")
    return first_incorrect, expected_values


def _generate_wrong_cot(
    band: str,
    split: str,
    item_index: int,
) -> dict[str, Any]:
    operations_by_band = {
        "easy": ["+", "*", "+"],
        "medium": ["+", "*", "-", "+"],
        "hard": ["+", "*", "-", "+", "*"],
    }
    operations = operations_by_band[band]
    step_count = len(operations)
    error_index = item_index % (step_count - 1)
    start = 12 + SPLITS.index(split) * 30 + DIFFICULTY_BANDS.index(band) * 7
    start += item_index
    variable_names = [
        _entity(split, "Err", band, item_index, f"V{position}")
        for position in range(1, step_count + 1)
    ]
    variable_values = [
        2 + (item_index + position) % 5
        for position in range(step_count)
    ]
    corrupted_values = list(variable_values)
    operand_delta = 1 + item_index % 2
    corrupted_values[error_index] += operand_delta
    second_error_delta = 2 + item_index % 3

    displayed = []
    previous = start
    for position, (operator, operand) in enumerate(
        zip(operations, variable_values)
    ):
        if position < error_index:
            shown = _apply_operation(previous, operator, operand)
        elif position == error_index:
            shown = _apply_operation(
                previous, operator, corrupted_values[position]
            )
        elif position == error_index + 1:
            shown = _apply_operation(previous, operator, operand)
            shown += second_error_delta
        else:
            shown = _apply_operation(previous, operator, operand)
        displayed.append(shown)
        previous = shown

    clean_first, clean_expected = _first_incorrect_reference(
        start, variable_values, operations, displayed
    )
    corrupted_first, corrupted_expected = _first_incorrect_reference(
        start, corrupted_values, operations, displayed
    )
    start_name = _entity(split, "Err", band, item_index, "Start")
    clean_variable_facts = [
        f"{name} = {value}."
        for name, value in zip(variable_names, variable_values)
    ]
    corrupted_variable_facts = [
        f"{name} = {value}."
        for name, value in zip(variable_names, corrupted_values)
    ]
    step_facts = []
    for position, (operator, variable, shown) in enumerate(
        zip(operations, variable_names, displayed),
        start=1,
    ):
        left = start_name if position == 1 else "previous result"
        step_facts.append(
            f"STEP_{position}: {left} {operator} {variable} = {shown}."
        )
    facts = [
        f"{start_name} = {start}.",
        *clean_variable_facts,
        *step_facts,
    ]
    corrupted_facts = [
        f"{start_name} = {start}.",
        *corrupted_variable_facts,
        *step_facts,
    ]
    fact_templates = [
        "{start_name} = {start_value}.",
        *(
            f"{{variable_{position}}} = {{value_{position}}}."
            for position in range(1, step_count + 1)
        ),
        *(
            (
                f"STEP_{position}: "
                + ("{start_name}" if position == 1 else "previous result")
                + f" {{operator_{position}}} {{variable_{position}}} "
                + f"= {{shown_{position}}}."
            )
            for position in range(1, step_count + 1)
        ),
    ]
    query = (
        "Checking the proposed calculation in order, what is the number of "
        "the first incorrect step?"
    )
    query_template = query
    variant = item_index % TEMPLATE_FAMILIES_PER_CELL
    prompt_template, clean_question = _render_prompt(
        split,
        variant,
        facts,
        query,
        "integer step number",
        fact_templates,
        query_template,
    )
    _, corrupted_question = _render_prompt(
        split,
        variant,
        corrupted_facts,
        query,
        "integer step number",
        fact_templates,
        query_template,
    )
    reference = {
        "kind": "first_incorrect_step",
        "start": start,
        "variables": variable_values,
        "operations": operations,
        "displayed_values": displayed,
        "expected_values": clean_expected,
        "first_incorrect_step": clean_first,
        "answer": str(clean_first),
    }
    corrupted_reference = {
        "kind": "first_incorrect_step",
        "start": start,
        "variables": corrupted_values,
        "operations": operations,
        "displayed_values": displayed,
        "expected_values": corrupted_expected,
        "first_incorrect_step": corrupted_first,
        "answer": str(corrupted_first),
    }
    return _make_record(
        family="wrong_cot_error_detection",
        band=band,
        split=split,
        item_index=item_index,
        prompt_template=prompt_template,
        clean_question=clean_question,
        corrupted_question=corrupted_question,
        answer=str(clean_first),
        corrupted_answer=str(corrupted_first),
        concept=str(clean_expected[clean_first - 1]),
        corrupted_concept=str(corrupted_expected[corrupted_first - 1]),
        facts=facts,
        corrupted_facts=corrupted_facts,
        entity_ids=[start_name, *variable_names],
        answer_type="numeric_step_code",
        reference=reference,
        corrupted_reference=corrupted_reference,
        difficulty_parameters={
            "proposed_step_count": step_count,
            "error_candidates": step_count - 1,
            "external_knowledge_required": False,
        },
        template_slots={
            "start_name": start_name,
            "changed_variable": variable_names[error_index],
            "first_incorrect_step": clean_first,
            "corrupted_first_incorrect_step": corrupted_first,
        },
        intervention_type="single_variable_value_replacement",
        clean_span=str(variable_values[error_index]),
        corrupted_span=str(corrupted_values[error_index]),
        maximum_step=step_count,
    )


_GENERATORS = {
    "arithmetic": _generate_arithmetic,
    "synthetic_relation": _generate_synthetic_relation,
    "prompt_grounded_two_hop_factual": _generate_prompt_grounded_factual,
    "counterfactual_entity_replacement": _generate_counterfactual,
    "wrong_cot_error_detection": _generate_wrong_cot,
}


def generate_candidate_bank() -> list[dict[str, Any]]:
    """Generate all 450 candidates in a stable canonical order."""

    records = []
    for family in TASK_FAMILIES:
        generator = _GENERATORS[family]
        for band in DIFFICULTY_BANDS:
            for split in SPLITS:
                for item_index in range(ITEMS_PER_CELL):
                    records.append(generator(band, split, item_index))
    return records


def _reference_answer_and_concept(
    reference: Mapping[str, Any],
) -> tuple[str, str]:
    kind = reference.get("kind")
    if kind == "arithmetic_pipeline":
        operations = [
            (str(operator), int(operand))
            for operator, operand in reference["operations"]
        ]
        values = _pipeline(int(reference["start"]), operations)
        if values != reference["intermediate_values"]:
            raise CandidateBankValidationError(
                "Arithmetic intermediate values do not match the pipeline"
            )
        concept_step = int(reference["concept_step"])
        return str(values[-1]), str(values[concept_step - 1])
    if kind in {"directed_path", "counterfactual_replacement_path"}:
        path = reference["path"]
        hops = int(reference["hops"])
        if len(path) != hops + 1:
            raise CandidateBankValidationError(
                "Path length does not match the registered hop count"
            )
        concept_index = int(reference["concept_index"])
        return str(path[-1]), str(path[concept_index])
    if kind == "two_hop_lookup":
        start = reference["start"]
        intermediate = reference["first_hop"][start]
        answer = reference["second_hop"][intermediate]
        return str(answer), str(intermediate)
    if kind == "first_incorrect_step":
        first, expected = _first_incorrect_reference(
            int(reference["start"]),
            [int(value) for value in reference["variables"]],
            [str(operator) for operator in reference["operations"]],
            [int(value) for value in reference["displayed_values"]],
        )
        if expected != reference["expected_values"]:
            raise CandidateBankValidationError(
                "Wrong-CoT expected values do not match the proposed steps"
            )
        return str(first), str(expected[first - 1])
    raise CandidateBankValidationError(f"Unknown reference kind: {kind}")


def _require_exact_keys(
    value: Any,
    expected: Iterable[str],
    label: str,
    errors: list[str],
) -> None:
    expected_set = set(expected)
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    actual_set = set(value)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        errors.append(f"{label} key mismatch; missing={missing}, extra={extra}")


def validate_candidate_bank(
    records: Sequence[Mapping[str, Any]],
    *,
    require_complete: bool = True,
) -> None:
    """Validate exact shape, construction invariants, and reference answers."""

    errors: list[str] = []
    task_ids: list[str] = []
    cell_counts: Counter[tuple[str, str, str]] = Counter()
    cell_templates: defaultdict[
        tuple[str, str, str], set[str]
    ] = defaultdict(set)
    cell_answers: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    cell_concepts: defaultdict[
        tuple[str, str, str], set[str]
    ] = defaultdict(set)
    split_entities: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    records_by_id: dict[str, Mapping[str, Any]] = {}

    for record_index, record in enumerate(records):
        label = str(record.get("task_id", f"record[{record_index}]"))
        _require_exact_keys(record, TOP_LEVEL_FIELDS, label, errors)
        if set(record) != set(TOP_LEVEL_FIELDS):
            continue
        task_id = str(record["task_id"])
        task_ids.append(task_id)
        records_by_id[task_id] = record
        family = str(record["task_family"])
        band = str(record["difficulty_band"])
        split = str(record["split"])
        if family not in TASK_FAMILIES:
            errors.append(f"{label}: unknown task_family {family}")
        if band not in DIFFICULTY_BANDS:
            errors.append(f"{label}: unknown difficulty_band {band}")
        if split not in SPLITS:
            errors.append(f"{label}: unknown split {split}")
        cell = (family, band, split)
        cell_counts[cell] += 1
        cell_templates[cell].add(str(record["template_family_id"]))
        cell_answers[cell].add(str(record["registered_answer"]))
        cell_concepts[cell].add(str(record["intermediate_concept"]))

        _require_exact_keys(
            record["concept_tokenization_requirement"],
            TOKENIZATION_FIELDS,
            f"{label}.concept_tokenization_requirement",
            errors,
        )
        _require_exact_keys(
            record["clean_corrupted_pair_availability"],
            PAIR_AVAILABILITY_FIELDS,
            f"{label}.clean_corrupted_pair_availability",
            errors,
        )
        _require_exact_keys(
            record["jlens_suitability"],
            JLENS_FIELDS,
            f"{label}.jlens_suitability",
            errors,
        )
        _require_exact_keys(
            record["patching_suitability"],
            PATCHING_FIELDS,
            f"{label}.patching_suitability",
            errors,
        )
        _require_exact_keys(
            record["ablation_suitability"],
            ABLATION_FIELDS,
            f"{label}.ablation_suitability",
            errors,
        )
        _require_exact_keys(
            record["ability_match_suitability"],
            ABILITY_FIELDS,
            f"{label}.ability_match_suitability",
            errors,
        )
        _require_exact_keys(
            record["clean_corrupted_pair"],
            PAIR_FIELDS,
            f"{label}.clean_corrupted_pair",
            errors,
        )
        _require_exact_keys(
            record["metadata"],
            METADATA_FIELDS,
            f"{label}.metadata",
            errors,
        )

        tokenization = record["concept_tokenization_requirement"]
        if isinstance(tokenization, dict):
            if tokenization.get("surface_form") != record["intermediate_concept"]:
                errors.append(f"{label}: concept surface form mismatch")
            if tokenization.get("required_token_count") != 1:
                errors.append(f"{label}: concept token count requirement must be 1")

        pair = record["clean_corrupted_pair"]
        if isinstance(pair, dict) and set(pair) == set(PAIR_FIELDS):
            _require_exact_keys(
                pair["clean"],
                PAIR_SIDE_FIELDS,
                f"{label}.clean_corrupted_pair.clean",
                errors,
            )
            _require_exact_keys(
                pair["corrupted"],
                PAIR_SIDE_FIELDS,
                f"{label}.clean_corrupted_pair.corrupted",
                errors,
            )
            _require_exact_keys(
                pair["intervention"],
                INTERVENTION_FIELDS,
                f"{label}.clean_corrupted_pair.intervention",
                errors,
            )
            clean = pair["clean"]
            corrupted = pair["corrupted"]
            intervention = pair["intervention"]
            if clean.get("question") != record["question"]:
                errors.append(f"{label}: top-level question is not pair clean question")
            if clean.get("registered_answer") != record["registered_answer"]:
                errors.append(f"{label}: top-level answer is not pair clean answer")
            if clean.get("intermediate_concept") != record["intermediate_concept"]:
                errors.append(f"{label}: top-level concept is not pair clean concept")
            if clean.get("registered_answer") == corrupted.get("registered_answer"):
                errors.append(f"{label}: pair answers must differ")
            mismatch_count = _token_mismatches(
                str(clean.get("question", "")),
                str(corrupted.get("question", "")),
            )
            if mismatch_count != 1:
                errors.append(
                    f"{label}: pair has {mismatch_count} surface token mismatches"
                )
            if intervention.get("surface_token_mismatches") != mismatch_count:
                errors.append(f"{label}: recorded pair mismatch count is incorrect")
            availability = record["clean_corrupted_pair_availability"]
            if availability.get("pair_id") != pair.get("pair_id"):
                errors.append(f"{label}: pair IDs disagree")
            if availability.get("minimal_surface_change") is not True:
                errors.append(f"{label}: minimal pair availability is false")
            if availability.get("different_registered_answers") is not True:
                errors.append(f"{label}: different-answer availability is false")

        metadata = record["metadata"]
        if isinstance(metadata, dict) and set(metadata) == set(METADATA_FIELDS):
            if metadata["schema_version"] != SCHEMA_VERSION:
                errors.append(f"{label}: schema version mismatch")
            if metadata["generator"] != GENERATOR_VERSION:
                errors.append(f"{label}: generator version mismatch")
            if metadata["strict_answer_only"] is not True:
                errors.append(f"{label}: strict answer-only flag must be true")
            facts = metadata["facts"]
            corrupted_facts = metadata["corrupted_facts"]
            for fact in facts:
                if fact not in record["question"]:
                    errors.append(f"{label}: supplied fact missing from clean prompt")
            corrupted_question = pair["corrupted"]["question"]
            for fact in corrupted_facts:
                if fact not in corrupted_question:
                    errors.append(
                        f"{label}: supplied fact missing from corrupted prompt"
                    )
            for entity in metadata["entity_ids"]:
                split_entities[(family, split)].add(str(entity))
            try:
                answer, concept = _reference_answer_and_concept(
                    metadata["reference"]
                )
                corrupted_answer, corrupted_concept = (
                    _reference_answer_and_concept(
                        metadata["corrupted_reference"]
                    )
                )
            except (CandidateBankValidationError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{label}: invalid reference: {exc}")
            else:
                if answer != record["registered_answer"]:
                    errors.append(f"{label}: clean reference answer mismatch")
                if concept != record["intermediate_concept"]:
                    errors.append(f"{label}: clean reference concept mismatch")
                if corrupted_answer != pair["corrupted"]["registered_answer"]:
                    errors.append(f"{label}: corrupted reference answer mismatch")
                if corrupted_concept != pair["corrupted"]["intermediate_concept"]:
                    errors.append(f"{label}: corrupted reference concept mismatch")

        if record["registered_answer"] == record["intermediate_concept"]:
            errors.append(f"{label}: intermediate concept must be non-final")
        if record["patching_suitability"].get("design_candidate") is not True:
            errors.append(f"{label}: every item must be a patching design candidate")
        if record["jlens_suitability"].get("design_candidate") is not True:
            errors.append(f"{label}: every item must be a J-lens design candidate")

    duplicate_ids = sorted(
        task_id for task_id, count in Counter(task_ids).items() if count > 1
    )
    if duplicate_ids:
        errors.append(f"duplicate task IDs: {duplicate_ids}")

    if require_complete:
        expected_total = (
            len(TASK_FAMILIES)
            * len(DIFFICULTY_BANDS)
            * len(SPLITS)
            * ITEMS_PER_CELL
        )
        if len(records) != expected_total:
            errors.append(
                f"bank has {len(records)} records; expected {expected_total}"
            )
        for family in TASK_FAMILIES:
            for band in DIFFICULTY_BANDS:
                template_sets = []
                for split in SPLITS:
                    cell = (family, band, split)
                    if cell_counts[cell] != ITEMS_PER_CELL:
                        errors.append(
                            f"cell {cell} has {cell_counts[cell]} records; "
                            f"expected {ITEMS_PER_CELL}"
                        )
                    if len(cell_templates[cell]) < 3:
                        errors.append(f"cell {cell} has fewer than 3 templates")
                    if len(cell_answers[cell]) < 2:
                        errors.append(f"cell {cell} is not answer-counterbalanced")
                    if len(cell_concepts[cell]) < 2:
                        errors.append(f"cell {cell} is not concept-counterbalanced")
                    template_sets.append(cell_templates[cell])
                for left_index, left in enumerate(template_sets):
                    for right in template_sets[left_index + 1 :]:
                        if left & right:
                            errors.append(
                                f"{family}/{band} reuses templates across splits"
                            )

        for family in TASK_FAMILIES:
            entity_sets = [
                split_entities[(family, split)] for split in SPLITS
            ]
            for left_index, left in enumerate(entity_sets):
                for right in entity_sets[left_index + 1 :]:
                    overlap = left & right
                    if overlap:
                        errors.append(
                            f"{family} reuses entities across splits: "
                            f"{sorted(overlap)[:3]}"
                        )

        for task_id, record in records_by_id.items():
            control_id = record["metadata"]["controls"]["matched_control_task_id"]
            control = records_by_id.get(control_id)
            if control is None:
                errors.append(f"{task_id}: matched control is missing")
                continue
            same_fields = (
                "task_family",
                "difficulty_band",
                "split",
                "template_family_id",
            )
            if any(record[field] != control[field] for field in same_fields):
                errors.append(f"{task_id}: matched control is not template-matched")
            if record["registered_answer"] == control["registered_answer"]:
                errors.append(f"{task_id}: matched control answer is not different")
            if record["intermediate_concept"] == control["intermediate_concept"]:
                errors.append(f"{task_id}: matched control concept is not different")

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:30])
        suffix = (
            f"\n... and {len(errors) - 30} more"
            if len(errors) > 30
            else ""
        )
        raise CandidateBankValidationError(
            f"Candidate bank validation failed:\n{preview}{suffix}"
        )


def candidate_count_matrix(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, int]]]:
    """Return family -> band -> split counts."""

    counts: Counter[tuple[str, str, str]] = Counter(
        (
            str(record["task_family"]),
            str(record["difficulty_band"]),
            str(record["split"]),
        )
        for record in records
    )
    return {
        family: {
            band: {
                split: counts[(family, band, split)] for split in SPLITS
            }
            for band in DIFFICULTY_BANDS
        }
        for family in TASK_FAMILIES
    }


def method_suitability_counts(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Count preregistered design candidates, not currently eligible cases."""

    fields = {
        "jlens": "jlens_suitability",
        "patching": "patching_suitability",
        "ablation": "ablation_suitability",
        "ability_matching": "ability_match_suitability",
    }
    return {
        method: sum(
            bool(record[field]["design_candidate"]) for record in records
        )
        for method, field in fields.items()
    }


def serialize_candidate_bank(records: Sequence[Mapping[str, Any]]) -> str:
    """Serialize records as stable UTF-8 JSON Lines."""

    return "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record in records
    )


def candidate_bank_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    """Return the SHA256 of canonical JSONL bytes."""

    return sha256(serialize_candidate_bank(records).encode("utf-8")).hexdigest()


def candidate_schema() -> dict[str, Any]:
    """Return the exact JSON Schema for a candidate-bank record."""

    def exact_object(
        properties: Mapping[str, Any],
        required: Sequence[str],
    ) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": dict(properties),
            "required": list(required),
            "additionalProperties": False,
        }

    string = {"type": "string", "minLength": 1}
    string_array = {"type": "array", "items": string}
    tokenization = exact_object(
        {
            "surface_form": string,
            "required": {"const": True},
            "required_token_count": {"const": 1},
            "registration_status": string,
            "registration_stage": string,
            "failure_action": string,
        },
        TOKENIZATION_FIELDS,
    )
    availability = exact_object(
        {
            "applicable": {"const": True},
            "available": {"const": True},
            "pair_id": string,
            "minimal_surface_change": {"const": True},
            "different_registered_answers": {"const": True},
        },
        PAIR_AVAILABILITY_FIELDS,
    )
    jlens = exact_object(
        {
            "design_candidate": {"type": "boolean"},
            "eligibility_status": string,
            "evidence_role": {"enum": ["sanity_only", "rq2_candidate"]},
            "non_final_necessary_intermediate": {"const": True},
            "tokenizer_registered_concept_required": {"const": True},
            "matched_control_required": {"const": True},
            "prompt_echo_control_required": {"const": True},
            "strict_answer_only_correct_required": {"const": True},
            "readout_scope": {"const": "non_motor_non_output_layers_only"},
        },
        JLENS_FIELDS,
    )
    patching = exact_object(
        {
            "design_candidate": {"type": "boolean"},
            "eligibility_status": string,
            "minimal_clean_corrupt_difference": {"const": True},
            "different_registered_answers": {"const": True},
            "token_position_alignment_required": {"const": True},
            "both_baselines_correct_required": {"const": True},
            "scan": {"const": "layer_by_position"},
            "controls_required": string_array,
        },
        PATCHING_FIELDS,
    )
    ablation = exact_object(
        {
            "design_candidate": {"type": "boolean"},
            "eligibility_status": string,
            "substantial_prompt_only_strict_headroom_required": {"const": True},
            "disjoint_learning_templates_required": {"const": True},
            "enough_baseline_correct_cases_required": {"const": True},
            "controls_required": string_array,
            "success_rule": string,
        },
        ABLATION_FIELDS,
    )
    ability = exact_object(
        {
            "design_candidate": {"type": "boolean"},
            "eligibility_status": string,
            "prompt_grounded_facts_required": {"const": True},
            "same_evaluator_and_profile_required": {"const": True},
            "nonmaterial_truncation_required": {"const": True},
            "held_out_template_confirmation_required": {"const": True},
            "equivalence_rule": string,
        },
        ABILITY_FIELDS,
    )
    pair_side = exact_object(
        {
            "question": string,
            "registered_answer": string,
            "intermediate_concept": string,
        },
        PAIR_SIDE_FIELDS,
    )
    intervention = exact_object(
        {
            "type": string,
            "clean_span": string,
            "corrupted_span": string,
            "surface_token_mismatches": {"const": 1},
            "position_alignment": {"const": "same_rendered_template_slot"},
            "target_token_alignment_status": string,
        },
        INTERVENTION_FIELDS,
    )
    pair = exact_object(
        {
            "pair_id": string,
            "clean": pair_side,
            "corrupted": pair_side,
            "intervention": intervention,
        },
        PAIR_FIELDS,
    )
    metadata = exact_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "generator": {"const": GENERATOR_VERSION},
            "item_index": {
                "type": "integer",
                "minimum": 0,
                "maximum": ITEMS_PER_CELL - 1,
            },
            "template_variant": {
                "type": "integer",
                "minimum": 0,
                "maximum": TEMPLATE_FAMILIES_PER_CELL - 1,
            },
            "strict_answer_only": {"const": True},
            "facts": string_array,
            "corrupted_facts": string_array,
            "entity_ids": string_array,
            "answer_type": {
                "enum": ["numeric", "entity", "numeric_step_code"]
            },
            "reference": {"type": "object"},
            "corrupted_reference": {"type": "object"},
            "balance": {"type": "object"},
            "controls": {"type": "object"},
            "future_evaluation": {"type": "object"},
            "difficulty_parameters": {"type": "object"},
            "template_slots": {"type": "object"},
        },
        METADATA_FIELDS,
    )
    properties = {
        "task_id": string,
        "task_family": {"enum": list(TASK_FAMILIES)},
        "difficulty_band": {"enum": list(DIFFICULTY_BANDS)},
        "split": {"enum": list(SPLITS)},
        "template_family_id": string,
        "prompt_template": string,
        "question": string,
        "registered_answer": string,
        "intermediate_concept": string,
        "concept_tokenization_requirement": tokenization,
        "clean_corrupted_pair_availability": availability,
        "jlens_suitability": jlens,
        "patching_suitability": patching,
        "ablation_suitability": ablation,
        "ability_match_suitability": ability,
        "clean_corrupted_pair": pair,
        "metadata": metadata,
    }
    schema = exact_object(properties, TOP_LEVEL_FIELDS)
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "phase1_task_headroom_candidate.schema.json",
            "title": "Phase 1 capability-headroom candidate",
        }
    )
    return schema


def write_candidate_bank(
    output_path: Path,
    schema_path: Path,
) -> tuple[int, str]:
    """Validate and write the deterministic JSONL bank and schema."""

    records = generate_candidate_bank()
    validate_candidate_bank(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_candidate_bank(records),
        encoding="utf-8",
        newline="\n",
    )
    schema_path.write_text(
        json.dumps(candidate_schema(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return len(records), candidate_bank_sha256(records)
