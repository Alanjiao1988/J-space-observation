"""Offline, model-free primitives for the J-lens S3 validity protocol.

This module deliberately uses only the Python standard library.  It validates
the preregistration and its public vendored inputs; it cannot load a tokenizer,
model, lens, activation pack, provider SDK, or prior scientific result.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import unicodedata
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "jlens-s3-validity-protocol/v1"
UPSTREAM_COMMIT = "581d398613e5602a5af361e1c34d3a92ea82ba8e"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
SPLIT_SEED = "jlens-s3-v1-split-2026-08-06"
LABEL_SEED = "jlens-s3-v1-label-permutation-2026-08-06"
POSITION_SEED = "jlens-s3-v1-position-shuffle-2026-08-06"
RANDOM_DIRECTION_SEED = "jlens-s3-v1-random-direction-2026-08-06"
BOOTSTRAP_SEED = "jlens-s3-v1-bootstrap-2026-08-06"
K_GRID = (1, 2, 5, 10, 20, 50, 100)
BOOTSTRAP_REPLICATES = 10_000
GRAM_TOLERANCE = 1e-9

NUMERIC_FORMS = MappingProxyType({
    "3": ("3", "three"),
    "4": ("4", "four"),
    "5": ("5", "five"),
    "6": ("6", "six"),
    "7": ("7", "seven"),
    "8": ("8", "eight"),
    "9": ("9", "nine"),
    "10": ("10", "ten"),
    "11": ("11", "eleven"),
    "12": ("12", "twelve"),
    "13": ("13", "thirteen"),
    "15": ("15", "fifteen"),
    "16": ("16", "sixteen"),
    "20": ("20", "twenty"),
    "24": ("24", "twenty-four"),
})
OPERATION_FORMS = MappingProxyType({
    "addition": ("+", "add", "addition", "plus"),
    "division": ("/", "divide", "divided", "division", "\N{DIVISION SIGN}"),
    "mod": ("%", "mod", "modulo", "remainder"),
    "multiplication": (
        "*",
        "multiplication",
        "multiply",
        "times",
        "\N{MULTIPLICATION SIGN}",
    ),
    "squared": ("^2", "square", "squared", "\N{SUPERSCRIPT TWO}"),
    "subtraction": ("-", "minus", "subtract", "subtraction"),
})

EXPECTED_UPSTREAM_FILES = {
    "LICENSE": (
        11358,
        "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        None,
        "Apache-2.0 license text",
    ),
    "data/evaluations/README.md": (
        3815,
        "e061d9cce02a1cc651d58a81927833b760d3cef65bf4995126ecbe372a0ebe07",
        None,
        "upstream evaluation definitions",
    ),
    "data/experiments/README.md": (
        8570,
        "1d78c702fa22ba610990d545b4c9c96839cc75cd4e451f2badb1cab23e04ad0f",
        None,
        "upstream intervention definitions",
    ),
    "data/evaluations/lens-eval-multihop.json": (
        21869,
        "50b7e4c9255291c0ca2a8e94615be9f44531fa57bb1a844e4f9616056d987416",
        93,
        "primary multihop readout benchmark",
    ),
    "data/evaluations/lens-eval-order-ops.json": (
        9589,
        "b203206d16ff628152cc86f3838604e06cb54776f3e14fa1c34f150db8bc7560",
        55,
        "primary order-of-operations readout benchmark",
    ),
    "data/experiments/probe-swap.json": (
        26567,
        "a0edd27ca23f7b4d0fbe90448c2ddcc7457a3d812121bf024ed12a032ff86796",
        90,
        "separate causal-swap benchmark",
    ),
}

TERMINAL_VALUES = (
    "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY",
    "JLENS_NOT_VALIDATED",
    "JLENS_PARTIALLY_VALIDATED",
    "JLENS_VALIDATED_FOR_RQ2_PILOT",
)
FLOORS = {
    "causal_swap_confirmation": 30,
    "multihop_confirmation": 20,
    "order_ops_confirmation": 20,
    "pooled_readout_confirmation": 50,
}
BANDS = {
    "early_control": (0, 8),
    "primary_middle": (9, 22),
    "motor_output_adjacent_control": (23, 26),
    "target_final_block": (27, 27),
}
HARD_GATES = (
    "lower95(M1200 true-label minus label-permuted readout effect) > 0",
    "lower95(M1200 true-position minus position-shuffled readout effect) > 0",
    "lower95(C_leakage) > 0",
    "no forbidden surface or final-answer synonym enters the primary readout",
)
INTEGRITY_PRECONDITIONS = (
    "all required source hashes, model and lens identities, source layers, and confirmation rows are complete",
    "all primary computations are finite",
    "alpha-zero and no-op logits retain the clean-hook top-1 and have maximum absolute logit difference <= 1e-5",
)
EXPECTED_REVIEW_QUESTIONS = (
    "Are fit, development, confirmation, Phase 1 bank, and official benchmark "
    "roles non-overlapping where the protocol claims they are?",
    "Can any item, synonym, layer, position, comparator, or exclusion depend on "
    "a lens, intervention, or confirmation outcome?",
    "Are token eligibility, pass@k AUC, bootstrap, coordinate swap, ablation, "
    "random control, answer-leakage control, patching, and classification "
    "computable exactly from the registered fields?",
    "Do the controls distinguish a known intermediate from prompt echo, "
    "final-answer leakage, motor preparation, and arbitrary perturbation?",
    "Are development and confirmation operationally separated?",
    "Can every stated result be reconstructed from the planned row-level pack?",
)

OUTPUT_COLUMNS = {
    "e0_item": (
        "distribution",
        "item_id",
        "canonical_item_sha256",
        "prompt_sha256",
        "raw_prompt_utf8_sha256",
        "input_token_ids",
        "input_length",
        "model_id",
        "model_revision",
        "tokenizer_revision",
        "parameter_dtype",
        "clean_top1_token_id",
        "target_token_ids",
        "control_position_candidates",
        "control_positions",
        "mechanical_eligible",
        "behavioral_eligible",
        "prompt_surface_removed_count",
        "target_overlap_removed_count",
        "multi_token_removed_count",
        "exclusion_reasons",
        "split_hash",
        "split_role",
    ),
    "e0_surface": (
        "distribution",
        "item_id",
        "surface_role",
        "intermediate_index",
        "raw_key",
        "candidate_surface",
        "normalized_surface",
        "token_ids",
        "prompt_leakage",
        "target_overlap",
        "single_token",
        "primary_retained",
        "official_inclusive_retained",
    ),
    "readout_rank": (
        "distribution",
        "item_id",
        "canonical_item_sha256",
        "lens_id",
        "control_kind",
        "control_replicate",
        "position",
        "layer",
        "intermediate_index",
        "registered_token_ids",
        "minimum_vocabulary_rank",
        "finite",
    ),
    "readout_item": (
        "distribution",
        "item_id",
        "lens_id",
        "control_kind",
        "control_replicate",
        "band",
        "k",
        "intermediate_pass_fraction",
        "normalized_auc",
    ),
    "causal_item": (
        "item_id",
        "canonical_item_sha256",
        "lens_id",
        "method",
        "random_draw",
        "alpha",
        "band",
        "positions",
        "source_layers",
        "source_token_ids",
        "target_token_ids",
        "clean_answer_token_ids",
        "swap_answer_token_ids",
        "clean_top1_token_id",
        "intervened_top1_token_id",
        "swap_success",
        "clean_logits_sha256",
        "intervened_logits_sha256",
        "max_abs_logit_difference",
        "kl_clean_intervened",
        "correct_answer_logit_change",
        "swap_answer_logprob_change",
        "log_odds_gain_G",
        "condition_number",
        "finite",
    ),
    "causal_direction": (
        "item_id",
        "lens_id",
        "method",
        "random_draw",
        "layer",
        "source_token_ids",
        "target_token_ids",
        "source_direction_sha256",
        "target_direction_sha256",
        "gram_00",
        "gram_01",
        "gram_11",
        "condition_number",
        "finite",
    ),
    "patching_cell": (
        "unordered_pair_id",
        "donor_item_id",
        "recipient_item_id",
        "layer",
        "position",
        "donor_input_length",
        "recipient_input_length",
        "donor_clean_answer_token_ids",
        "recipient_clean_answer_token_ids",
        "recipient_clean_logits_sha256",
        "patched_logits_sha256",
        "causal_recovery_log_odds",
        "donor_intermediate_rank_donor",
        "donor_intermediate_rank_recipient",
        "true_rank_contrast",
        "position_shuffled_rank_contrast",
        "finite",
    ),
    "patching_alignment": (
        "unordered_pair_id",
        "rho_true",
        "rho_position_shuffled",
        "rho_difference",
        "pair_cell_count",
        "finite",
    ),
    "bootstrap_replicate": (
        "endpoint",
        "replicate",
        "sampling_unit",
        "multihop_draw_ids",
        "order_ops_draw_ids",
        "causal_draw_ids",
        "pair_draw_ids",
        "effect",
    ),
    "bootstrap_summary": (
        "endpoint",
        "point_estimate",
        "lower95",
        "upper95",
        "replicates",
        "seed",
        "percentile_method",
        "finite",
    ),
    "classification": (
        "protocol_sha256",
        "e0_manifest_sha256",
        "confirmation_manifest_sha256",
        "floor_multihop",
        "floor_order_ops",
        "floor_pooled",
        "floor_causal",
        "integrity_complete",
        "integrity_finite",
        "integrity_noop",
        "hard_label",
        "hard_position",
        "hard_leakage",
        "hard_surface",
        "readout_pass",
        "causal_pass",
        "patching_status",
        "operational_status",
        "classification",
    ),
    "artifact_manifest": (
        "artifact_id",
        "stage",
        "relative_path",
        "bytes",
        "sha256",
        "schema_sha256",
        "protocol_sha256",
        "source_commit",
        "image_digest",
        "create_only",
        "complete",
        "written_order",
        "opened_at_utc",
    ),
}
OUTPUT_PRIMARY_KEYS = {
    "e0_item": ("distribution", "item_id"),
    "e0_surface": (
        "distribution",
        "item_id",
        "surface_role",
        "intermediate_index",
        "candidate_surface",
    ),
    "readout_rank": (
        "distribution",
        "item_id",
        "lens_id",
        "control_kind",
        "control_replicate",
        "position",
        "layer",
        "intermediate_index",
    ),
    "readout_item": (
        "distribution",
        "item_id",
        "lens_id",
        "control_kind",
        "control_replicate",
        "band",
        "k",
    ),
    "causal_item": ("item_id", "lens_id", "method", "random_draw", "alpha", "band"),
    "causal_direction": ("item_id", "lens_id", "method", "random_draw", "layer"),
    "patching_cell": (
        "unordered_pair_id",
        "donor_item_id",
        "recipient_item_id",
        "layer",
        "position",
    ),
    "patching_alignment": ("unordered_pair_id",),
    "bootstrap_replicate": ("endpoint", "replicate"),
    "bootstrap_summary": ("endpoint",),
    "classification": (
        "protocol_sha256",
        "e0_manifest_sha256",
        "confirmation_manifest_sha256",
    ),
    "artifact_manifest": ("artifact_id",),
}
_OUTPUT_ENUM_TYPES = {
    ("e0_item", "distribution"): "enum[multihop,order_ops,causal_swap]",
    ("e0_item", "split_role"): "enum[ineligible,development,confirmation]",
    ("e0_surface", "surface_role"): "enum[intermediate,swap_to,target,swap_answer]",
    ("readout_rank", "distribution"): "enum[multihop,order_ops]",
    ("readout_rank", "lens_id"): "enum[M1200,A600,B600,logit_lens]",
    ("readout_rank", "control_kind"): "enum[true,label_permutation,position_shuffle]",
    ("readout_item", "distribution"): "enum[multihop,order_ops]",
    ("readout_item", "lens_id"): "enum[M1200,A600,B600,logit_lens]",
    ("readout_item", "control_kind"): "enum[true,label_permutation,position_shuffle]",
    ("readout_item", "band"): "enum[early_control,primary_middle,motor_output_adjacent_control]",
    ("causal_item", "lens_id"): "enum[M1200,A600,B600,logit_lens,none]",
    ("causal_item", "band"): "enum[early_control,primary_middle,motor_output_adjacent_control]",
    ("causal_direction", "lens_id"): "enum[M1200,logit_lens,random]",
    (
        "bootstrap_replicate",
        "endpoint",
    ): "enum[R,label_control,position_control,C_logit,C_random,C_leakage,patching_alignment]",
    ("bootstrap_replicate", "sampling_unit"): "enum[item,unordered_pair_id]",
    (
        "classification",
        "patching_status",
    ): "enum[PATCHING_ALIGNMENT_SUPPORTED,PATCHING_ALIGNMENT_NOT_SUPPORTED,PATCHING_ALIGNMENT_NOT_ESTIMABLE]",
    ("classification", "operational_status"): "enum[COMPLETE,OPERATIONAL_BLOCKER]",
    (
        "classification",
        "classification",
    ): "null_or_enum[INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY,JLENS_NOT_VALIDATED,JLENS_PARTIALLY_VALIDATED,JLENS_VALIDATED_FOR_RQ2_PILOT]",
    ("artifact_manifest", "stage"): "enum[P,E0,E1,E2]",
}
_OUTPUT_NULLABLE_TYPES = {
    ("e0_item", "clean_top1_token_id"): "null_or_integer",
    ("e0_item", "split_hash"): "null_or_sha256",
    ("e0_surface", "intermediate_index"): "null_or_integer",
    ("readout_rank", "control_replicate"): "null_or_integer",
    ("readout_item", "control_replicate"): "null_or_integer",
    ("causal_item", "random_draw"): "null_or_integer",
    ("causal_direction", "random_draw"): "null_or_integer",
    ("artifact_manifest", "opened_at_utc"): "null_or_string",
}
_OUTPUT_ARRAY_INTEGER_FIELDS = {
    "clean_answer_token_ids",
    "control_position_candidates",
    "control_positions",
    "donor_clean_answer_token_ids",
    "input_token_ids",
    "positions",
    "recipient_clean_answer_token_ids",
    "registered_token_ids",
    "source_layers",
    "source_token_ids",
    "swap_answer_token_ids",
    "target_token_ids",
    "token_ids",
}
_OUTPUT_ARRAY_STRING_FIELDS = {
    "causal_draw_ids",
    "exclusion_reasons",
    "multihop_draw_ids",
    "order_ops_draw_ids",
    "pair_draw_ids",
}
_OUTPUT_BOOLEAN_FIELDS = {
    "behavioral_eligible",
    "causal_pass",
    "complete",
    "create_only",
    "finite",
    "floor_causal",
    "floor_multihop",
    "floor_order_ops",
    "floor_pooled",
    "hard_label",
    "hard_leakage",
    "hard_position",
    "hard_surface",
    "integrity_complete",
    "integrity_finite",
    "integrity_noop",
    "mechanical_eligible",
    "official_inclusive_retained",
    "primary_retained",
    "prompt_leakage",
    "readout_pass",
    "single_token",
    "target_overlap",
}
_OUTPUT_INTEGER_FIELDS = {
    "bytes",
    "clean_top1_token_id",
    "donor_input_length",
    "donor_intermediate_rank_donor",
    "donor_intermediate_rank_recipient",
    "input_length",
    "intermediate_index",
    "intervened_top1_token_id",
    "k",
    "layer",
    "minimum_vocabulary_rank",
    "multi_token_removed_count",
    "pair_cell_count",
    "position",
    "prompt_surface_removed_count",
    "random_draw",
    "recipient_input_length",
    "replicate",
    "replicates",
    "swap_success",
    "target_overlap_removed_count",
    "written_order",
}
_OUTPUT_NUMBER_FIELDS = {
    "alpha",
    "causal_recovery_log_odds",
    "condition_number",
    "correct_answer_logit_change",
    "effect",
    "gram_00",
    "gram_01",
    "gram_11",
    "intermediate_pass_fraction",
    "kl_clean_intervened",
    "log_odds_gain_G",
    "lower95",
    "max_abs_logit_difference",
    "normalized_auc",
    "point_estimate",
    "position_shuffled_rank_contrast",
    "rho_difference",
    "rho_position_shuffled",
    "rho_true",
    "swap_answer_logprob_change",
    "true_rank_contrast",
    "upper95",
}

REQUIRED_CROSSWALK_PATHS = (
    "$.artifact_semantics",
    "$.authority",
    "$.upstream.files",
    "$.upstream.counterparts",
    "$.stages.P",
    "$.stages.E0",
    "$.stages.E1",
    "$.stages.E2",
    "$.identities.target_model",
    "$.identities.tokenizer",
    "$.identities.j_lens_code",
    "$.identities.lens_artifacts",
    "$.layers",
    "$.normalization",
    "$.eligibility.multihop",
    "$.eligibility.order_ops",
    "$.eligibility.primary_leakage_filter",
    "$.eligibility.clean_behavior",
    "$.eligibility.targets",
    "$.split",
    "$.readout",
    "$.causal",
    "$.patching",
    "$.statistics",
    "$.classification",
    "$.outputs",
    "$.review",
    "$.role_separation",
    "$.verification",
)

_SUPPORTED_SCHEMA_KEYS = {
    "$defs",
    "$id",
    "$ref",
    "$schema",
    "additionalProperties",
    "const",
    "description",
    "enum",
    "items",
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "title",
    "type",
    "uniqueItems",
}
_PLACEHOLDER = re.compile(r"(?i)(?:\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|\?\?\?|<[^>]+>)")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IMMUTABLE = re.compile(r"[0-9a-f]{40}\Z")


class ProtocolError(ValueError):
    """Raised when a protocol, schema, source, or output fails closed."""


def _reject_json_constant(value: str) -> None:
    raise ProtocolError(f"non-finite JSON number is forbidden: {value}")


def load_json(path: Path) -> Any:
    """Load strict UTF-8 JSON while rejecting NaN and infinities."""

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"cannot load strict JSON {path}: {exc}") from exc


def canonical_item_bytes(item: Mapping[str, Any]) -> bytes:
    """Return the frozen canonical bytes of one raw upstream item."""

    try:
        text = json.dumps(
            item,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"item is not finite canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def canonical_json_bytes(document: Any) -> bytes:
    """Return repository-canonical sorted, indented, ASCII JSON plus LF."""

    try:
        return (
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"document is not finite canonical JSON: {exc}") from exc


def canonical_item_hash(item: Mapping[str, Any], seed: str = SPLIT_SEED) -> str:
    """Hash canonical item bytes followed immediately by the literal seed."""

    return hashlib.sha256(canonical_item_bytes(item) + seed.encode("utf-8")).hexdigest()


def assign_hash_split(
    items: Sequence[Mapping[str, Any]],
    development_count: int = 15,
    seed: str = SPLIT_SEED,
) -> list[dict[str, str]]:
    """Assign an already-eligible distribution by immutable hash order."""

    if development_count < 0:
        raise ProtocolError("development_count must be nonnegative")
    seen: set[str] = set()
    ordered: list[tuple[str, str, Mapping[str, Any]]] = []
    for item in items:
        item_id = str(item.get("name", ""))
        if not item_id or item_id in seen:
            raise ProtocolError("eligible items require distinct nonempty names")
        seen.add(item_id)
        ordered.append((canonical_item_hash(item, seed), item_id, item))
    ordered.sort(key=lambda row: (row[0], row[1]))
    return [
        {
            "item_id": item_id,
            "split_hash": digest,
            "split_role": "development" if index < development_count else "confirmation",
        }
        for index, (digest, item_id, _item) in enumerate(ordered)
    ]


def normalize_surface(text: str, *, casefold: bool = False) -> str:
    """Apply NFKC and the exact registered whitespace rule."""

    if not isinstance(text, str):
        raise ProtocolError("surface must be a string")
    folded = unicodedata.normalize("NFKC", text)
    out: list[str] = []
    pending_space = False
    for char in folded:
        if char.isspace():
            if out:
                pending_space = True
            continue
        if pending_space:
            out.append(" ")
            pending_space = False
        out.append(char)
    normalized = "".join(out)
    return normalized.casefold() if casefold else normalized


def normalize_decoded_token(decoded: str, *, casefold: bool = True) -> str | None:
    """Normalize a token decode, rejecting an invalid boundary-space prefix."""

    if not isinstance(decoded, str) or not decoded:
        return None
    if decoded.startswith("  ") or (decoded[0].isspace() and decoded[0] != " "):
        return None
    body = decoded[1:] if decoded.startswith(" ") else decoded
    if body and body[0].isspace():
        return None
    return normalize_surface(body, casefold=casefold)


def token_matches_surface(decoded: str, surface: str) -> bool:
    token = normalize_decoded_token(decoded, casefold=True)
    return token is not None and token == normalize_surface(surface, casefold=True)


def _is_word_character(char: str) -> bool:
    return char == "_" or char.isalnum()


def token_bounded_literal(prompt: str, surface: str) -> bool:
    """Test exact normalized/case-folded literal occurrence with frozen bounds."""

    haystack = normalize_surface(prompt, casefold=True)
    needle = normalize_surface(surface, casefold=True)
    if not needle:
        return False
    offset = 0
    while True:
        index = haystack.find(needle, offset)
        if index < 0:
            return False
        end = index + len(needle)
        left_ok = index == 0 or not _is_word_character(haystack[index - 1])
        right_ok = end == len(haystack) or not _is_word_character(haystack[end])
        if left_ok and right_ok:
            return True
        offset = index + 1


def filter_leaking_surfaces(
    surfaces: Iterable[str],
    prompt: str,
    target: str,
) -> dict[str, tuple[str, ...]]:
    """Mechanically partition primary surfaces by leakage reason."""

    kept: list[str] = []
    prompt_removed: list[str] = []
    target_removed: list[str] = []
    target_norm = normalize_surface(target, casefold=True)
    seen: set[str] = set()
    for surface in surfaces:
        normalized = normalize_surface(surface, casefold=True)
        if normalized in seen:
            continue
        seen.add(normalized)
        if token_bounded_literal(prompt, surface):
            prompt_removed.append(surface)
        elif normalized == target_norm:
            target_removed.append(surface)
        else:
            kept.append(surface)
    return {
        "kept": tuple(kept),
        "prompt_surface": tuple(prompt_removed),
        "target_overlap": tuple(target_removed),
    }


def resolve_single_token_ids(
    surfaces: Iterable[str],
    decoded_vocabulary: Mapping[int, str],
) -> dict[str, tuple[int, ...]]:
    """Resolve complete surfaces without importing or constructing a tokenizer."""

    result: dict[str, tuple[int, ...]] = {}
    for surface in surfaces:
        matches = tuple(
            sorted(
                token_id
                for token_id, decoded in decoded_vocabulary.items()
                if isinstance(token_id, int) and token_matches_surface(decoded, surface)
            )
        )
        result[surface] = matches
    return result


def eligible_control_positions(
    decoded_position_spans: Sequence[str],
    registered_surfaces: Iterable[str],
) -> tuple[int, ...]:
    """Return non-final positions containing no registered complete surface."""

    if len(decoded_position_spans) < 2:
        return ()
    surfaces = tuple(registered_surfaces)
    return tuple(
        index
        for index, span in enumerate(decoded_position_spans[:-1])
        if not any(token_bounded_literal(span, surface) for surface in surfaces)
    )


def clean_behavior_eligible(top1_token_id: int, target_token_ids: Iterable[int]) -> bool:
    """Apply the exact clean greedy-next-token membership rule."""

    if not isinstance(top1_token_id, int) or isinstance(top1_token_id, bool):
        raise ProtocolError("clean top-1 token ID must be an integer")
    targets = tuple(target_token_ids)
    if not targets or any(
        not isinstance(token_id, int) or isinstance(token_id, bool) for token_id in targets
    ):
        raise ProtocolError("target token IDs must be nonempty integers")
    return top1_token_id in targets


def deterministic_position_controls(
    item: Mapping[str, Any],
    positions: Sequence[int],
    draws: int = 5,
    seed: str = POSITION_SEED,
) -> tuple[int, ...]:
    """Select each frozen position control without inspecting ranks."""

    if not positions:
        raise ProtocolError("no eligible non-final control position")
    raw = canonical_item_bytes(item)
    selected: list[int] = []
    for draw in range(draws):
        ordered = sorted(
            positions,
            key=lambda position: hashlib.sha256(
                seed.encode("utf-8")
                + b"\0"
                + str(draw).encode("ascii")
                + b"\0"
                + raw
                + b"\0"
                + str(position).encode("ascii")
            ).digest(),
        )
        selected.append(int(ordered[0]))
    return tuple(selected)


def deterministic_label_derangement(
    items: Sequence[Mapping[str, Any]],
    distribution: str,
    replicate: int,
    seed: str = LABEL_SEED,
) -> dict[str, str]:
    """Return a complete within-distribution cyclic label derangement."""

    if len(items) < 2 or replicate not in range(5):
        raise ProtocolError("derangement needs >=2 items and replicate 0..4")
    prefix = (
        seed.encode("utf-8")
        + b"\0"
        + distribution.encode("utf-8")
        + b"\0"
        + str(replicate).encode("ascii")
    )
    ordered = sorted(
        items,
        key=lambda item: (
            hashlib.sha256(prefix + b"\0" + canonical_item_bytes(item)).digest(),
            str(item.get("name", "")),
        ),
    )
    names = [str(item.get("name", "")) for item in ordered]
    if not all(names) or len(set(names)) != len(names):
        raise ProtocolError("derangement items need distinct nonempty names")
    offset = 1 + int.from_bytes(hashlib.sha256(prefix).digest(), "big") % (len(names) - 1)
    return {name: names[(index + offset) % len(names)] for index, name in enumerate(names)}


def pass_at_k_auc(
    band_minimum_ranks: Sequence[float],
    k_grid: Sequence[int] = K_GRID,
) -> tuple[dict[int, float], float]:
    """Compute fractional pass@k and normalized log-k trapezoid AUC."""

    if not band_minimum_ranks:
        raise ProtocolError("an item requires at least one intermediate rank")
    if tuple(k_grid) != K_GRID:
        raise ProtocolError(f"k grid must be exactly {list(K_GRID)}")
    ranks = [float(rank) for rank in band_minimum_ranks]
    if any(not math.isfinite(rank) or rank < 1 for rank in ranks):
        raise ProtocolError("ranks must be finite and >= 1")
    curve = {
        int(k): sum(rank <= k for rank in ranks) / len(ranks)
        for k in k_grid
    }
    area = 0.0
    for left, right in zip(k_grid, k_grid[1:]):
        width = math.log(right) - math.log(left)
        area += width * (curve[int(left)] + curve[int(right)]) / 2.0
    return curve, area / math.log(100.0)


def equal_distribution_pool(
    multihop_values: Sequence[float],
    order_ops_values: Sequence[float],
) -> float:
    """Pool distributions at exactly 0.5/0.5 regardless of sample count."""

    if not multihop_values or not order_ops_values:
        raise ProtocolError("both readout distributions must be nonempty")
    left = _finite_mean(multihop_values)
    right = _finite_mean(order_ops_values)
    return 0.5 * left + 0.5 * right


def _finite_mean(values: Sequence[float]) -> float:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise ProtocolError("mean inputs must be nonempty and finite")
    return sum(numbers) / len(numbers)


def paired_bootstrap(
    paired_by_distribution: Mapping[str, Sequence[tuple[float, float]]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: str = BOOTSTRAP_SEED,
) -> tuple[float, ...]:
    """Deterministically resample paired items and equal-weight distributions."""

    if replicates <= 0 or not paired_by_distribution:
        raise ProtocolError("bootstrap needs positive replicates and distributions")
    prepared: dict[str, tuple[tuple[float, float], ...]] = {}
    for distribution, pairs in paired_by_distribution.items():
        converted = tuple((float(left), float(right)) for left, right in pairs)
        if not converted:
            raise ProtocolError(f"bootstrap distribution is empty: {distribution}")
        if any(not math.isfinite(value) for pair in converted for value in pair):
            raise ProtocolError("bootstrap values must be finite")
        prepared[str(distribution)] = converted
    random_seed = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest(), "big")
    generator = random.Random(random_seed)
    output: list[float] = []
    names = sorted(prepared)
    for _replicate in range(replicates):
        effects: list[float] = []
        for name in names:
            pairs = prepared[name]
            draws = [pairs[generator.randrange(len(pairs))] for _ in pairs]
            effects.append(sum(left - right for left, right in draws) / len(draws))
        output.append(sum(effects) / len(effects))
    return tuple(output)


def percentile_interval(
    replicates: Sequence[float],
    bounds: tuple[float, float] = (2.5, 97.5),
) -> tuple[float, float]:
    """Frozen percentile interval with linear interpolation."""

    values = sorted(float(value) for value in replicates)
    if not values or any(not math.isfinite(value) for value in values):
        raise ProtocolError("percentile values must be nonempty and finite")

    def percentile(percent: float) -> float:
        index = (len(values) - 1) * percent / 100.0
        lower = int(math.floor(index))
        upper = int(math.ceil(index))
        fraction = index - lower
        return values[lower] * (1.0 - fraction) + values[upper] * fraction

    return percentile(bounds[0]), percentile(bounds[1])


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ProtocolError("vector dimensions differ")
    value = sum(float(a) * float(b) for a, b in zip(left, right))
    if not math.isfinite(value):
        raise ProtocolError("non-finite vector arithmetic")
    return value


def _symmetric_2x2_pinv(
    a: float,
    b: float,
    d: float,
    rtol: float,
    atol: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    trace_half = (a + d) / 2.0
    radius = math.hypot((a - d) / 2.0, b)
    eigenvalues = (max(0.0, trace_half + radius), max(0.0, trace_half - radius))
    theta = 0.5 * math.atan2(2.0 * b, a - d)
    vectors = ((math.cos(theta), math.sin(theta)), (-math.sin(theta), math.cos(theta)))
    max_sigma = math.sqrt(max(eigenvalues))
    threshold = max(float(atol), float(rtol) * max_sigma)
    result = [[0.0, 0.0], [0.0, 0.0]]
    for eigenvalue, vector in zip(eigenvalues, vectors):
        if math.sqrt(eigenvalue) <= threshold:
            continue
        scale = 1.0 / eigenvalue
        for row in range(2):
            for column in range(2):
                result[row][column] += scale * vector[row] * vector[column]
    return (tuple(result[0]), tuple(result[1]))  # type: ignore[return-value]


def coordinate_swap(
    h: Sequence[float],
    source: Sequence[float],
    target: Sequence[float],
    *,
    alpha: float = 1.0,
    rtol: float = 1e-6,
    atol: float = 0.0,
) -> tuple[float, ...]:
    """Swap fixed Moore-Penrose coordinates using test-sized stdlib vectors."""

    if len(h) != len(source) or len(h) != len(target) or not h:
        raise ProtocolError("h, source, and target require one shared dimension")
    vectors = tuple(tuple(float(value) for value in vector) for vector in (h, source, target))
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise ProtocolError("coordinate swap inputs must be finite")
    if not math.isfinite(alpha):
        raise ProtocolError("alpha must be finite")
    if alpha == 0.0:
        return vectors[0]
    gram = (
        _dot(vectors[1], vectors[1]),
        _dot(vectors[1], vectors[2]),
        _dot(vectors[2], vectors[2]),
    )
    gram_pinv = _symmetric_2x2_pinv(*gram, rtol, atol)
    projections = (_dot(vectors[1], vectors[0]), _dot(vectors[2], vectors[0]))
    coordinates = (
        gram_pinv[0][0] * projections[0] + gram_pinv[0][1] * projections[1],
        gram_pinv[1][0] * projections[0] + gram_pinv[1][1] * projections[1],
    )
    delta0 = alpha * (coordinates[1] - coordinates[0])
    delta1 = alpha * (coordinates[0] - coordinates[1])
    result = tuple(
        value + delta0 * first + delta1 * second
        for value, first, second in zip(vectors[0], vectors[1], vectors[2])
    )
    if any(not math.isfinite(value) for value in result):
        raise ProtocolError("coordinate swap produced a non-finite value")
    return result


def ablate_direction(h: Sequence[float], direction: Sequence[float]) -> tuple[float, ...]:
    """Remove the component of h along one registered direction."""

    norm_squared = _dot(direction, direction)
    if norm_squared <= 0.0:
        raise ProtocolError("cannot ablate a zero-norm direction")
    scale = _dot(direction, h) / norm_squared
    return tuple(float(value) - scale * float(axis) for value, axis in zip(h, direction))


def gram_matrix(
    first: Sequence[float],
    second: Sequence[float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (_dot(first, first), _dot(first, second)),
        (_dot(first, second), _dot(second, second)),
    )


def _orthonormal_frame(dimension: int, generator: random.Random) -> tuple[list[float], list[float]]:
    for _attempt in range(100):
        first = [generator.gauss(0.0, 1.0) for _ in range(dimension)]
        first_norm = math.sqrt(_dot(first, first))
        if first_norm <= 1e-12:
            continue
        q1 = [value / first_norm for value in first]
        second = [generator.gauss(0.0, 1.0) for _ in range(dimension)]
        projection = _dot(second, q1)
        second = [value - projection * axis for value, axis in zip(second, q1)]
        second_norm = math.sqrt(_dot(second, second))
        if second_norm > 1e-12:
            return q1, [value / second_norm for value in second]
    raise ProtocolError("could not construct a deterministic orthonormal frame")


def deterministic_gram_matched_pairs(
    source: Sequence[float],
    target: Sequence[float],
    *,
    draws: int = 5,
    seed: str = RANDOM_DIRECTION_SEED,
    context: str = "",
) -> tuple[tuple[tuple[float, ...], tuple[float, ...]], ...]:
    """Create deterministic randomly oriented pairs with the exact source Gram."""

    if len(source) != len(target) or len(source) < 2 or draws <= 0:
        raise ProtocolError("Gram matching needs equal dimension >=2 and positive draws")
    gram = gram_matrix(source, target)
    first_norm = math.sqrt(max(0.0, gram[0][0]))
    if first_norm <= 0.0:
        raise ProtocolError("source direction must have positive norm")
    coefficient = gram[0][1] / first_norm
    remainder_squared = gram[1][1] - coefficient * coefficient
    if remainder_squared < -GRAM_TOLERANCE:
        raise ProtocolError("source Gram matrix is not positive semidefinite")
    remainder = math.sqrt(max(0.0, remainder_squared))
    output: list[tuple[tuple[float, ...], tuple[float, ...]]] = []
    for draw in range(draws):
        material = f"{seed}\0{context}\0{draw}".encode("utf-8")
        generator = random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))
        q1, q2 = _orthonormal_frame(len(source), generator)
        first = tuple(first_norm * value for value in q1)
        second = tuple(
            coefficient * left + remainder * right for left, right in zip(q1, q2)
        )
        candidate = gram_matrix(first, second)
        if any(
            abs(candidate[row][column] - gram[row][column]) > GRAM_TOLERANCE
            for row in range(2)
            for column in range(2)
        ):
            raise ProtocolError("Gram-matched construction exceeded frozen tolerance")
        output.append((first, second))
    return tuple(output)


def build_counterparts(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build exact model-free oriented and unique probe-swap counterparts."""

    source_index: dict[tuple[str, str, str], list[str]] = {}
    by_name: dict[str, Mapping[str, Any]] = {}
    fields = ("name", "category", "intermediate", "answer", "swap_to", "swap_answer")
    for item in items:
        if any(not isinstance(item.get(field), str) or not item[field] for field in fields):
            raise ProtocolError("probe-swap item lacks an exact required string")
        name = str(item["name"])
        if name in by_name:
            raise ProtocolError(f"duplicate probe-swap name: {name}")
        by_name[name] = item
        key = tuple(str(item[field]).casefold() for field in ("category", "intermediate", "answer"))
        source_index.setdefault(key, []).append(name)

    oriented: list[dict[str, str]] = []
    unique: dict[str, dict[str, str]] = {}
    for source_name in sorted(by_name):
        item = by_name[source_name]
        key = tuple(str(item[field]).casefold() for field in ("category", "swap_to", "swap_answer"))
        for counterpart_name in sorted(source_index.get(key, ())):
            if counterpart_name == source_name:
                continue
            names = sorted((source_name, counterpart_name), key=lambda value: value.encode("utf-8"))
            pair_id = hashlib.sha256((names[0] + "\n" + names[1]).encode("utf-8")).hexdigest()
            oriented.append(
                {
                    "source_item_id": source_name,
                    "counterpart_item_id": counterpart_name,
                    "unordered_pair_id": pair_id,
                }
            )
            unique[pair_id] = {
                "first_item_id": names[0],
                "second_item_id": names[1],
                "unordered_pair_id": pair_id,
            }
    oriented.sort(
        key=lambda row: (
            row["source_item_id"],
            row["counterpart_item_id"],
            row["unordered_pair_id"],
        )
    )
    return {
        "oriented_matches": tuple(oriented),
        "unordered_pairs": tuple(unique[key] for key in sorted(unique)),
    }


def spearman_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    """Spearman correlation with deterministic average ranks for ties."""

    if len(left) != len(right) or len(left) < 2:
        raise ProtocolError("Spearman inputs need equal length >=2")

    def ranks(values: Sequence[float]) -> list[float]:
        numbers = [float(value) for value in values]
        if any(not math.isfinite(value) for value in numbers):
            raise ProtocolError("Spearman inputs must be finite")
        ordered = sorted(range(len(numbers)), key=lambda index: (numbers[index], index))
        output = [0.0] * len(numbers)
        cursor = 0
        while cursor < len(ordered):
            end = cursor + 1
            while end < len(ordered) and numbers[ordered[end]] == numbers[ordered[cursor]]:
                end += 1
            average = (cursor + 1 + end) / 2.0
            for index in ordered[cursor:end]:
                output[index] = average
            cursor = end
        return output

    left_ranks, right_ranks = ranks(left), ranks(right)
    left_mean, right_mean = _finite_mean(left_ranks), _finite_mean(right_ranks)
    numerator = sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left_ranks, right_ranks)
    )
    left_scale = math.sqrt(sum((value - left_mean) ** 2 for value in left_ranks))
    right_scale = math.sqrt(sum((value - right_mean) ** 2 for value in right_ranks))
    if left_scale == 0.0 or right_scale == 0.0:
        raise ProtocolError("Spearman correlation is undefined for a constant trajectory")
    return numerator / (left_scale * right_scale)


def classify(
    *,
    floors_pass: bool,
    integrity_pass: bool,
    hard_gates_pass: bool,
    readout_pass: bool,
    causal_pass: bool,
) -> dict[str, str | None]:
    """Apply the exact operational ordering and scientific truth table."""

    if not floors_pass:
        return {
            "operational_status": "COMPLETE",
            "classification": "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY",
        }
    if not integrity_pass:
        return {"operational_status": "OPERATIONAL_BLOCKER", "classification": None}
    if not hard_gates_pass or not (readout_pass or causal_pass):
        result = "JLENS_NOT_VALIDATED"
    elif readout_pass and causal_pass:
        result = "JLENS_VALIDATED_FOR_RQ2_PILOT"
    else:
        result = "JLENS_PARTIALLY_VALIDATED"
    return {"operational_status": "COMPLETE", "classification": result}


def _check_schema_definition(schema: Any, path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise ProtocolError(f"{path}: schema node must be an object")
    unsupported = set(schema) - _SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise ProtocolError(f"{path}: unsupported schema keywords {sorted(unsupported)}")
    declared_type = schema.get("type")
    object_typed = declared_type == "object" or (
        isinstance(declared_type, list) and "object" in declared_type
    )
    if object_typed:
        if schema.get("additionalProperties") is not False:
            raise ProtocolError(f"{path}: object schema is not closed")
        properties = schema.get("properties")
        required = schema.get("required")
        if (
            not isinstance(properties, dict)
            or not isinstance(required, list)
            or len(required) != len(set(required))
            or set(required) != set(properties)
        ):
            raise ProtocolError(f"{path}: every closed object property must be required")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise ProtocolError(f"{path}.properties must be an object")
        for key, child in schema["properties"].items():
            _check_schema_definition(child, f"{path}.properties.{key}")
    if "$defs" in schema:
        if not isinstance(schema["$defs"], dict):
            raise ProtocolError(f"{path}.$defs must be an object")
        for key, child in schema["$defs"].items():
            _check_schema_definition(child, f"{path}.$defs.{key}")
    if "items" in schema:
        _check_schema_definition(schema["items"], f"{path}.items")
    ref = schema.get("$ref")
    if ref is not None and (
        not isinstance(ref, str) or not ref.startswith("#/$defs/") or "/" in ref[8:]
    ):
        raise ProtocolError(f"{path}: only direct local $defs references are supported")


def _resolve_ref(schema: Mapping[str, Any], root_schema: Mapping[str, Any]) -> Mapping[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    name = str(ref)[8:]
    definitions = root_schema.get("$defs")
    if not isinstance(definitions, dict) or name not in definitions:
        raise ProtocolError(f"unresolved schema reference: {ref}")
    resolved = definitions[name]
    if not isinstance(resolved, dict):
        raise ProtocolError(f"schema reference is not an object: {ref}")
    return resolved


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise ProtocolError(f"unsupported schema type: {expected}")


def validate_json_schema(
    value: Any,
    schema: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any] | None = None,
    path: str = "$",
) -> None:
    """Validate the supported closed subset of JSON Schema 2020-12."""

    root = schema if root_schema is None else root_schema
    current = _resolve_ref(schema, root)
    expected = current.get("type")
    if expected is not None:
        choices = [expected] if isinstance(expected, str) else expected
        if not isinstance(choices, list) or not all(isinstance(item, str) for item in choices):
            raise ProtocolError(f"{path}: invalid schema type declaration")
        if not any(_matches_type(value, choice) for choice in choices):
            raise ProtocolError(f"{path}: expected type {choices}, got {type(value).__name__}")
    if "const" in current and value != current["const"]:
        raise ProtocolError(f"{path}: value differs from const")
    if "enum" in current and value not in current["enum"]:
        raise ProtocolError(f"{path}: value is outside enum")
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocolError(f"{path}: non-finite number")
    if isinstance(value, dict) and current.get("type") == "object":
        properties = current["properties"]
        missing = set(current["required"]) - set(value)
        extra = set(value) - set(properties)
        if missing:
            raise ProtocolError(f"{path}: missing fields {sorted(missing)}")
        if extra:
            raise ProtocolError(f"{path}: extra fields {sorted(extra)}")
        for key, child in value.items():
            validate_json_schema(
                child,
                properties[key],
                root_schema=root,
                path=f"{path}.{key}",
            )
    if isinstance(value, list):
        if "minItems" in current and len(value) < current["minItems"]:
            raise ProtocolError(f"{path}: too few array items")
        if "maxItems" in current and len(value) > current["maxItems"]:
            raise ProtocolError(f"{path}: too many array items")
        if current.get("uniqueItems"):
            markers = [
                json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)
                for item in value
            ]
            if len(markers) != len(set(markers)):
                raise ProtocolError(f"{path}: array items are not unique")
        if "items" in current:
            for index, item in enumerate(value):
                validate_json_schema(
                    item,
                    current["items"],
                    root_schema=root,
                    path=f"{path}[{index}]",
                )
    if isinstance(value, str):
        if "minLength" in current and len(value) < current["minLength"]:
            raise ProtocolError(f"{path}: string is too short")
        if "maxLength" in current and len(value) > current["maxLength"]:
            raise ProtocolError(f"{path}: string is too long")
        if "pattern" in current and re.search(current["pattern"], value) is None:
            raise ProtocolError(f"{path}: string does not match pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in current and value < current["minimum"]:
            raise ProtocolError(f"{path}: number is below minimum")
        if "maximum" in current and value > current["maximum"]:
            raise ProtocolError(f"{path}: number exceeds maximum")


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _column_names(table: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(column).split(":", 1)[0] for column in table["columns"])


def _expected_output_type(table_name: str, column_name: str) -> str:
    keyed = (table_name, column_name)
    if keyed in _OUTPUT_ENUM_TYPES:
        return _OUTPUT_ENUM_TYPES[keyed]
    if keyed in _OUTPUT_NULLABLE_TYPES:
        return _OUTPUT_NULLABLE_TYPES[keyed]
    if column_name in {"model_revision", "source_commit", "tokenizer_revision"}:
        return "immutable_ref"
    if column_name == "sha256" or column_name.endswith("_sha256"):
        return "sha256"
    if column_name in _OUTPUT_ARRAY_INTEGER_FIELDS:
        return "array_integer"
    if column_name in _OUTPUT_ARRAY_STRING_FIELDS:
        return "array_string"
    if column_name in _OUTPUT_BOOLEAN_FIELDS:
        return "boolean"
    if column_name in _OUTPUT_INTEGER_FIELDS:
        return "integer"
    if column_name in _OUTPUT_NUMBER_FIELDS:
        return "number"
    return "string"


def _expected_truth_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hard in (True, False):
        for causal, readout in ((False, False), (False, True), (True, False), (True, True)):
            result = classify(
                floors_pass=True,
                integrity_pass=True,
                hard_gates_pass=hard,
                readout_pass=readout,
                causal_pass=causal,
            )["classification"]
            rows.append(
                {
                    "causal_pass": causal,
                    "hard_gates_pass": hard,
                    "readout_pass": readout,
                    "result": result,
                }
            )
    return rows


def validate_protocol_semantics(protocol: Mapping[str, Any]) -> None:
    """Reject every frozen semantic drift not expressible in structural schema."""

    for path, value in _walk(protocol):
        if isinstance(value, float) and not math.isfinite(value):
            raise ProtocolError(f"{path}: non-finite number")
        if isinstance(value, str) and _PLACEHOLDER.search(value):
            raise ProtocolError(f"{path}: placeholder-like text is forbidden")

    if protocol["schema_version"] != SCHEMA_VERSION:
        raise ProtocolError("schema_version drift")
    upstream = protocol["upstream"]
    if (
        upstream["repository"] != "https://github.com/anthropics/jacobian-lens.git"
        or upstream["commit"] != UPSTREAM_COMMIT
        or upstream["license"] != "Apache-2.0"
        or upstream["modifications"] != "none"
    ):
        raise ProtocolError("upstream identity is mutable or incorrect")
    registered_files = {
        row["path"]: (row["bytes"], row["sha256"], row["item_count"], row["role"])
        for row in upstream["files"]
    }
    if registered_files != EXPECTED_UPSTREAM_FILES:
        raise ProtocolError("upstream file identity, count, or role drift")
    if upstream["counterparts"]["oriented_matches"] != 29:
        raise ProtocolError("oriented counterpart count drift")
    if upstream["counterparts"]["unique_unordered_pairs"] != 24:
        raise ProtocolError("unordered counterpart count drift")

    identities = protocol["identities"]
    model = identities["target_model"]
    if model != {
        "evaluation_mode": True,
        "id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "maximum_input_tokens": 512,
        "number_of_transformer_blocks": 28,
        "parameter_dtype": "torch.float16",
        "revision": MODEL_REVISION,
        "trust_remote_code": False,
        "use_cache": False,
    }:
        raise ProtocolError("target model identity drift")
    if identities["tokenizer"] != {
        "chat_template": False,
        "input_truncation": False,
        "revision": MODEL_REVISION,
    }:
        raise ProtocolError("tokenizer identity drift")
    if identities["j_lens_code"]["commit"] != UPSTREAM_COMMIT:
        raise ProtocolError("J-lens code commit drift")
    if identities["j_lens_code"]["hf_adapter_force_bos"] is not True:
        raise ProtocolError("force_bos must remain true")
    for key in ("A600", "B600", "M1200"):
        if key not in identities["lens_artifacts"]:
            raise ProtocolError(f"missing lens identity {key}")
    if identities["lens_artifacts"]["M1200"]["role"] != "only primary lens":
        raise ProtocolError("M1200 must remain the only primary lens")

    layers = protocol["layers"]
    observed_bands = {
        name: (value["start"], value["end"]) for name, value in layers["bands"].items()
    }
    if observed_bands != BANDS or layers["j_lens_source_layers"] != {"start": 0, "end": 26}:
        raise ProtocolError("layer band drift")
    if layers["j_lens_target_layer"] != 27:
        raise ProtocolError("target layer drift")

    order_ops = protocol["eligibility"]["order_ops"]
    if order_ops["numeric_keys"] != list(NUMERIC_FORMS):
        raise ProtocolError("numeric key order or coverage drift")
    if order_ops["operation_keys"] != list(OPERATION_FORMS):
        raise ProtocolError("operation key order or coverage drift")
    if {
        key: tuple(value) for key, value in order_ops["numeric_forms"].items()
    } != dict(NUMERIC_FORMS):
        raise ProtocolError("numeric synonym drift")
    if {
        key: tuple(value) for key, value in order_ops["operation_forms"].items()
    } != dict(OPERATION_FORMS):
        raise ProtocolError("operation synonym drift")
    if protocol["eligibility"]["targets"] != {
        "causal": "Use only the exact official answer and swap_answer strings with casing-equivalent and tokenizer-boundary variants.",
        "primary_readout": "Use only the exact official target string with casing-equivalent and tokenizer-boundary variants; target semantic synonyms and generated numeric word variants are forbidden.",
        "single_token_rule": "Each required target surface must resolve to at least one complete vocabulary token under the registered direction-token rule.",
    }:
        raise ProtocolError("target surface rule drift")

    split = protocol["split"]
    if split["seed"] != SPLIT_SEED:
        raise ProtocolError("split seed drift")
    if split["floors"] != FLOORS:
        raise ProtocolError("confirmation floor drift")
    expected_assignment = {
        "causal_swap_development": 15,
        "multihop_development": 15,
        "order_ops_development": 15,
        "remainder": "confirmation",
    }
    if split["assignment"] != expected_assignment:
        raise ProtocolError("development assignment drift")
    if not split["no_backfill"] or not split["no_replacement_batch"]:
        raise ProtocolError("backfill or replacement batch is forbidden")
    if split["replacement_authority_spent"]:
        raise ProtocolError("replacement authority must remain unspent")

    readout = protocol["readout"]
    if tuple(readout["auc"]["k_grid"]) != K_GRID:
        raise ProtocolError("k-grid drift")
    controls = readout["controls"]
    if (
        controls["label_derangements"]["seed"] != LABEL_SEED
        or controls["position_shuffle"]["seed"] != POSITION_SEED
        or controls["label_derangements"]["draws"] != 5
        or controls["position_shuffle"]["draws"] != 5
    ):
        raise ProtocolError("readout control seed or draw drift")
    causal = protocol["causal"]
    if causal["random_controls"]["seed"] != RANDOM_DIRECTION_SEED:
        raise ProtocolError("random-direction seed drift")
    if causal["random_controls"]["draws"] != 5:
        raise ProtocolError("random-direction draw drift")
    if causal["random_controls"]["gram_tolerance_absolute"] != GRAM_TOLERANCE:
        raise ProtocolError("Gram tolerance drift")
    if causal["coordinate_swap"]["alphas"] != {
        "integrity": 0.0,
        "primary": 1.0,
        "secondary": 0.5,
    }:
        raise ProtocolError("intervention alpha drift")
    if causal["coordinate_swap"]["pseudoinverse"] != {
        "atol": 0.0,
        "implementation": "torch.linalg.pinv",
        "rtol": 1e-06,
    }:
        raise ProtocolError("pseudoinverse drift")

    bootstrap = protocol["statistics"]["bootstrap"]
    if bootstrap["seed"] != BOOTSTRAP_SEED or bootstrap["replicates"] != 10_000:
        raise ProtocolError("bootstrap seed or replicate drift")
    if protocol["patching"]["minimum_confirmation_pairs"] != 12:
        raise ProtocolError("patching pair floor drift")

    classification = protocol["classification"]
    if tuple(classification["terminal_values"]) != TERMINAL_VALUES:
        raise ProtocolError("terminal classification drift")
    if classification["truth_table"] != _expected_truth_table():
        raise ProtocolError("classification truth-table drift")
    if classification["core_gates"] != {
        "CAUSAL_PASS": "lower95(C_logit) > 0 and lower95(C_random) > 0",
        "READOUT_PASS": "lower95(R) > 0",
    }:
        raise ProtocolError("core gate drift")
    if tuple(classification["hard_scientific_gates"]) != HARD_GATES:
        raise ProtocolError("hard gate drift")
    if tuple(classification["integrity_preconditions"]) != INTEGRITY_PRECONDITIONS:
        raise ProtocolError("integrity gate drift")

    role = protocol["role_separation"]
    forbidden = set(role["selection_signals_forbidden"])
    if not {
        "J-lens output",
        "rank",
        "intervention result",
        "patching result",
        "confirmation outcome",
        "best layer",
        "best replicate",
    }.issubset(forbidden):
        raise ProtocolError("outcome-dependent selector is not forbidden")
    allowed = tuple(role["allowed_selection_signals"])
    if allowed != (
        "vendored public item bytes",
        "registered mechanical token eligibility",
        "registered clean greedy next-token correctness",
        "registered deterministic split hash",
    ):
        raise ProtocolError("outcome-dependent or unregistered selection signal")
    pairs = {frozenset(pair) for pair in role["required_disjoint_pairs"]}
    required_pairs = {
        frozenset(("S2 fit A600", "S2 fit B600")),
        frozenset(("S2 fit sequences", "official benchmark items")),
        frozenset(("development items", "confirmation items")),
        frozenset(("Phase 1 bank", "official benchmark items")),
        frozenset(("primary readout benchmark", "causal swap benchmark")),
    }
    if pairs != required_pairs:
        raise ProtocolError("role non-overlap drift")

    review = protocol["review"]
    if review["rounds"] != 1 or tuple(review["questions"]) != EXPECTED_REVIEW_QUESTIONS:
        raise ProtocolError("bounded-review policy drift")
    if review["result_in_candidate"] != "none; this candidate registers review policy only":
        raise ProtocolError("candidate must not contain a review result")

    outputs = protocol["outputs"]
    if tuple(outputs["required_tables"]) != tuple(OUTPUT_COLUMNS):
        raise ProtocolError("required output table order or coverage drift")
    if set(outputs) != set(OUTPUT_COLUMNS) | {"required_tables"}:
        raise ProtocolError("output table set drift")
    for table_name, expected_columns in OUTPUT_COLUMNS.items():
        table = outputs[table_name]
        if _column_names(table) != expected_columns:
            raise ProtocolError(f"output column drift: {table_name}")
        expected_specs = tuple(
            f"{name}:{_expected_output_type(table_name, name)}" for name in expected_columns
        )
        if tuple(table["columns"]) != expected_specs:
            raise ProtocolError(f"output column type drift: {table_name}")
        if table["additional_fields"] or not table["all_or_nothing"] or not table["create_only"]:
            raise ProtocolError(f"output closure/create-only drift: {table_name}")
        if tuple(table["primary_key"]) != OUTPUT_PRIMARY_KEYS[table_name]:
            raise ProtocolError(f"invalid output primary key: {table_name}")

    stages = protocol["stages"]
    if set(stages) != {"P", "E0", "E1", "E2"}:
        raise ProtocolError("P/E0/E1/E2 boundary drift")
    if stages["P"]["target_or_lens_operations"] != 0 or stages["E0"]["lens_operations"] != 0:
        raise ProtocolError("design or E0 lens operation is forbidden")
    if not stages["E2"]["all_or_nothing"]:
        raise ProtocolError("confirmation must be all-or-nothing")

    for path, value in _walk(protocol):
        leaf = path.rsplit(".", 1)[-1]
        if leaf in {"commit", "revision"}:
            if not isinstance(value, str) or not _IMMUTABLE.fullmatch(value):
                raise ProtocolError(f"{path}: mutable reference")


def validate_role_sets(
    role_sets: Mapping[str, Iterable[str]],
    disjoint_pairs: Iterable[Sequence[str]],
) -> None:
    """Fail if any registered role pair shares an identifier."""

    materialized = {name: set(values) for name, values in role_sets.items()}
    for pair in disjoint_pairs:
        if len(pair) != 2 or pair[0] not in materialized or pair[1] not in materialized:
            raise ProtocolError(f"unknown or malformed role pair: {pair}")
        overlap = materialized[pair[0]] & materialized[pair[1]]
        if overlap:
            raise ProtocolError(f"role overlap {pair[0]} / {pair[1]}: {sorted(overlap)}")


def verify_vendored_sources(project_root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute all vendored hashes, byte/item counts, and counterpart facts."""

    vendored = project_root / str(protocol["upstream"]["vendored_root"])
    registered = {entry["path"]: entry for entry in protocol["upstream"]["files"]}
    report: dict[str, Any] = {"files": {}}
    for relative, expected in EXPECTED_UPSTREAM_FILES.items():
        path = vendored.joinpath(*relative.split("/"))
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ProtocolError(f"missing vendored source {relative}: {exc}") from exc
        digest = hashlib.sha256(raw).hexdigest()
        expected_bytes, expected_hash, expected_count, expected_role = expected
        if len(raw) != expected_bytes or digest != expected_hash:
            raise ProtocolError(f"vendored byte identity mismatch: {relative}")
        if registered.get(relative) != {
            "bytes": expected_bytes,
            "item_count": expected_count,
            "path": relative,
            "role": expected_role,
            "sha256": expected_hash,
        }:
            raise ProtocolError(f"protocol upstream row mismatch: {relative}")
        count = None
        if expected_count is not None:
            document = load_json(path)
            if not isinstance(document, dict) or not isinstance(document.get("items"), list):
                raise ProtocolError(f"vendored item shape mismatch: {relative}")
            count = len(document["items"])
            if count != expected_count:
                raise ProtocolError(f"vendored item count mismatch: {relative}")
        report["files"][relative] = {"bytes": len(raw), "sha256": digest, "item_count": count}

    probe = load_json(vendored / "data" / "experiments" / "probe-swap.json")
    counterparts = build_counterparts(probe["items"])
    oriented = len(counterparts["oriented_matches"])
    unordered = len(counterparts["unordered_pairs"])
    if oriented != 29 or unordered != 24:
        raise ProtocolError(f"counterpart facts drifted: {oriented} oriented, {unordered} unique")
    report["counterparts"] = {"oriented_matches": oriented, "unique_unordered_pairs": unordered}
    return report


def validate_markdown_crosswalk(markdown_path: Path) -> None:
    """Require every registered scientific section's exact JSON path."""

    try:
        text = markdown_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProtocolError(f"cannot read Markdown crosswalk: {exc}") from exc
    missing = [path for path in REQUIRED_CROSSWALK_PATHS if f"`{path}`" not in text]
    if missing:
        raise ProtocolError(f"Markdown crosswalk is missing paths: {missing}")
    if _PLACEHOLDER.search(text):
        raise ProtocolError("Markdown crosswalk contains placeholder-like text")


def _parse_column_spec(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise ProtocolError(f"invalid output column specification: {spec}")
    return tuple(spec.split(":", 1))  # type: ignore[return-value]


def _validate_output_value(value: Any, specification: str, path: str) -> None:
    nullable = specification.startswith("null_or_")
    base = specification[8:] if nullable else specification
    if value is None:
        if nullable:
            return
        raise ProtocolError(f"{path}: null is forbidden")
    if base.startswith("enum[") and base.endswith("]"):
        if value not in base[5:-1].split(","):
            raise ProtocolError(f"{path}: value outside output enum")
        return
    if base == "sha256" and isinstance(value, str) and _SHA256.fullmatch(value):
        return
    if base == "immutable_ref" and isinstance(value, str) and _IMMUTABLE.fullmatch(value):
        return
    if base == "string" and isinstance(value, str) and value:
        return
    if base == "boolean" and isinstance(value, bool):
        return
    if base == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return
    if (
        base == "number"
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ):
        return
    if base == "array_string" and isinstance(value, list) and all(
        isinstance(item, str) for item in value
    ):
        return
    if base == "array_integer" and isinstance(value, list) and all(
        isinstance(item, int) and not isinstance(item, bool) for item in value
    ):
        return
    raise ProtocolError(f"{path}: value does not match {specification}")


def validate_output_row(
    protocol: Mapping[str, Any],
    table_name: str,
    row: Mapping[str, Any],
) -> None:
    """Validate one reconstructible row against its frozen closed table."""

    tables = protocol["outputs"]
    if table_name not in tables["required_tables"]:
        raise ProtocolError(f"unknown output table: {table_name}")
    table = tables[table_name]
    specifications = dict(_parse_column_spec(spec) for spec in table["columns"])
    missing = set(specifications) - set(row)
    extra = set(row) - set(specifications)
    if missing or extra:
        raise ProtocolError(
            f"{table_name}: output row missing={sorted(missing)} extra={sorted(extra)}"
        )
    for name, specification in specifications.items():
        _validate_output_value(row[name], specification, f"{table_name}.{name}")


def validate_output_pack(
    protocol: Mapping[str, Any],
    pack: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    """Reject partial, extra, malformed, or duplicate-key output packs."""

    required = tuple(protocol["outputs"]["required_tables"])
    if set(pack) != set(required):
        raise ProtocolError("output pack is partial or carries an extra table")
    for table_name in required:
        rows = pack[table_name]
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            raise ProtocolError(f"{table_name}: all-or-nothing table is empty")
        primary_key = protocol["outputs"][table_name]["primary_key"]
        seen: set[str] = set()
        for row in rows:
            validate_output_row(protocol, table_name, row)
            marker = json.dumps(
                [row[name] for name in primary_key],
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            if marker in seen:
                raise ProtocolError(f"{table_name}: duplicate primary key")
            seen.add(marker)


def load_and_validate_protocol(
    project_root: Path,
    *,
    verify_sources: bool = True,
    verify_crosswalk: bool = True,
) -> dict[str, Any]:
    """Load and fully validate the canonical protocol package."""

    protocol_path = project_root / "docs" / "jlens_s3_validity_protocol.json"
    schema_path = project_root / "docs" / "jlens_s3_validity_protocol.schema.json"
    protocol = load_json(protocol_path)
    schema = load_json(schema_path)
    if not isinstance(protocol, dict) or not isinstance(schema, dict):
        raise ProtocolError("protocol and schema roots must be objects")
    if protocol_path.read_bytes() != canonical_json_bytes(protocol):
        raise ProtocolError("canonical protocol bytes are not sorted repository JSON plus LF")
    _check_schema_definition(schema)
    validate_json_schema(protocol, schema)
    validate_protocol_semantics(protocol)
    if verify_sources:
        verify_vendored_sources(project_root, protocol)
    if verify_crosswalk:
        validate_markdown_crosswalk(project_root / "docs" / "jlens_s3_validity_protocol.md")
    return protocol


__all__ = [
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "BANDS",
    "FLOORS",
    "GRAM_TOLERANCE",
    "HARD_GATES",
    "INTEGRITY_PRECONDITIONS",
    "K_GRID",
    "LABEL_SEED",
    "NUMERIC_FORMS",
    "OPERATION_FORMS",
    "POSITION_SEED",
    "ProtocolError",
    "RANDOM_DIRECTION_SEED",
    "REQUIRED_CROSSWALK_PATHS",
    "SCHEMA_VERSION",
    "SPLIT_SEED",
    "TERMINAL_VALUES",
    "ablate_direction",
    "assign_hash_split",
    "build_counterparts",
    "canonical_item_bytes",
    "canonical_item_hash",
    "canonical_json_bytes",
    "classify",
    "clean_behavior_eligible",
    "coordinate_swap",
    "deterministic_gram_matched_pairs",
    "deterministic_label_derangement",
    "deterministic_position_controls",
    "eligible_control_positions",
    "equal_distribution_pool",
    "filter_leaking_surfaces",
    "gram_matrix",
    "load_and_validate_protocol",
    "load_json",
    "normalize_decoded_token",
    "normalize_surface",
    "paired_bootstrap",
    "pass_at_k_auc",
    "percentile_interval",
    "resolve_single_token_ids",
    "spearman_correlation",
    "token_bounded_literal",
    "token_matches_surface",
    "validate_json_schema",
    "validate_markdown_crosswalk",
    "validate_output_pack",
    "validate_output_row",
    "validate_protocol_semantics",
    "validate_role_sets",
    "verify_vendored_sources",
]
