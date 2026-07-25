"""Model-free controls for the Phase 0.5B J-lens saturation and merge run.

This module holds every deterministic control that does not need a GPU, the
official ``jlens`` package, or the target model: corpus registration, the fit
plan, pure numeric comparisons, the preregistered decision rules, and the
standard artifact pack writer/validator.

The measurements this module supports are **engineering feasibility only**.
Top-k overlap and rank correlation are transport/apply stability evidence.
They are never semantic evidence and never support a workspace, hidden
reasoning, internal chain-of-thought, or J-space claim.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

_HELPER_ROOT = str(Path(__file__).resolve().parent)
if _HELPER_ROOT not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, _HELPER_ROOT)

import phase05_jlens as base  # noqa: E402

PHASE = "phase05-jlens-saturation"
TRACK = "track-a"
SCHEMA_VERSION = "phase05-jlens-saturation-v1"

MODEL_ID = base.MODEL_ID
MODEL_REVISION = base.MODEL_REVISION
MODEL_LAYERS = base.MODEL_LAYERS
MODEL_WIDTH = base.MODEL_WIDTH
RUNTIME_DTYPE = base.RUNTIME_DTYPE
LENS_SERIALIZATION_DTYPE = "float32"
OFFICIAL_REPOSITORY = base.OFFICIAL_REPOSITORY
OFFICIAL_COMMIT = base.OFFICIAL_COMMIT
MAX_SEQ_LEN = base.MAX_SEQ_LEN
SKIP_FIRST = base.SKIP_FIRST

SOURCE_LAYERS = (6, 13, 20)
TARGET_LAYER = 27

DEFAULT_DIM_BATCH = 1
ALLOWED_DIM_BATCH = (1, 2)
# Phase 0.5A F2 measured 3,808,428,032 peak reserved bytes of 16,704,405,504
# (ratio 0.2280) with 11.8727 GiB free and a green classification. That is the
# only recorded memory-headroom justification allowed to raise dim_batch to 2.
DIM_BATCH_2_JUSTIFICATION = (
    "phase05A-F2-green: peak_reserved_ratio=0.2280, free=11.8727GiB, "
    "dim_batch=2 already executed successfully in phase05A F3"
)

CORPUS_TOTAL = 50
FIT_PROMPTS = 25
HELDOUT_PROMPTS = 10
RESERVE_PROMPTS = 15
FIT_A_PROMPTS = 10
FIT_B_PROMPTS = 25
FIT_B_SHARDS = (10, 10, 5)
CONTROL_SUBSET_SIZE = 5
CONTROL_SUBSET_SHARDS = (3, 2)
MIN_PROXY_TOKENS = 33

TOP_K = 10
TOP_K_SECONDARY = 50
SEEDS = {"python": 0, "numpy": 0, "torch": 0}

MERGE_MAX_ABS_TOLERANCE = 1e-5
MERGE_RELATIVE_TOLERANCE = 1e-6
SAVE_LOAD_MAX_ABS_TOLERANCE = 0.0
APPLY_RTOL = 5e-3
APPLY_ATOL = 5e-3
CONVERGENCE_RELATIVE_FROBENIUS_MAX = 0.10
CONVERGENCE_COSINE_MIN = 0.99
TOPK_OVERLAP_MIN = 0.80
RANK_CORRELATION_MIN = 0.95
FINITE_RATE_MIN = 1.0

STAGES = (
    "S0_environment",
    "S1_model",
    "S2_fit_a10",
    "S3_fit_b25_sharded_merge",
    "S4_merge_control",
    "S5_convergence",
    "S6_apply_stability",
)
REQUIRED_PREDECESSOR = {
    "S0_environment": None,
    "S1_model": "S0_environment",
    "S2_fit_a10": "S1_model",
    "S3_fit_b25_sharded_merge": "S2_fit_a10",
    "S4_merge_control": "S3_fit_b25_sharded_merge",
    "S5_convergence": "S3_fit_b25_sharded_merge",
    "S6_apply_stability": "S3_fit_b25_sharded_merge",
}
TERMINAL_STAGE_STATUSES = {
    "success",
    "failed",
    "blocked",
    "skipped_time_guard",
    "skipped_memory_guard",
}

CONDITIONS = (
    "fit_a_direct",
    "fit_b_shard_1",
    "fit_b_shard_2",
    "fit_b_shard_3",
    "fit_b_merged",
    "control_direct",
    "control_shard_1",
    "control_shard_2",
    "control_merged",
    "convergence_10_vs_25",
    "shard_merge_vs_direct",
    "weighted_recombination_vs_direct",
    "fit_repeatability",
    "apply_stability",
    "heldout_apply",
    "corpus_registration",
    "not_applicable",
)

DECISIONS = (
    "ENGINEERING_STABLE",
    "ENGINEERING_IMPROVING",
    "ENGINEERING_UNSTABLE",
    "INCONCLUSIVE",
)
DECISION_STATUSES = ("PASS", "FAIL", "COMPLETE", "INCONCLUSIVE", "BLOCKED")

PROHIBITED_INTERPRETATIONS = (
    "workspace found",
    "J-space validated",
    "hidden reasoning observed",
    "internal workspace",
    "invisible chain-of-thought",
    "top-k overlap treated as semantic evidence",
)
SCIENTIFIC_CLAIM_BOUNDARY = (
    "Engineering feasibility only. This run measures whether the pinned "
    "official Jacobian lens can be fit at 10 and 25 prompts, sharded, merged, "
    "serialized, reloaded, and applied with stable numerics on one T4. "
    "Top-k overlap and rank correlation are technical stability evidence about "
    "transport and serialization. They are not semantic evidence and support "
    "no claim about a workspace, hidden reasoning, an internal "
    "chain-of-thought, or J-space."
)
OBJECTIVE = (
    "Advance Phase 0.5 from a 2-prompt technical feasibility result to an "
    "executed 10-prompt fit, an executed 25-prompt sharded fit with merge, a "
    "direct-subset merge control, and measured convergence and apply "
    "stability."
)
HYPOTHESIS = (
    "Engineering hypothesis only: a 10-prompt and a sharded 25-prompt J-lens "
    "fit complete inside the T4 time and memory envelope, the merged sharded "
    "lens reproduces a direct fit on the same prompts within tolerance, and "
    "the fitted matrices and applied logits stay finite and numerically "
    "stable across save/load."
)
RESEARCH_QUESTION = (
    "Can the pinned official J-lens be fit at 10 prompts and at 25 prompts "
    "via [10,10,5] shards plus merge on one T4 within the registered time and "
    "memory envelope, and how do the resulting matrices and applied logits "
    "compare numerically?"
)
SCOPE = (
    "10-prompt direct fit",
    "25-prompt sharded fit with official merge",
    "direct-subset merge control",
    "shard weighting cross-check",
    "10-vs-25 matrix comparison",
    "held-out apply stability, top-k overlap, rank correlation",
    "wall-clock, memory, checkpoint and lens size measurement",
)
OUT_OF_SCOPE = (
    "any semantic or interpretability claim",
    "lens quality validation",
    "behavioral evaluation or parser work",
    "locked evaluator material",
    "Plan B",
    "hidden reasoning, internal workspace, or J-space claims",
)

ARTIFACT_FILENAMES = (
    "00_stage_manifest.json",
    "01_protocol_snapshot.json",
    "02_records.jsonl",
    "03_metrics.csv",
    "04_decision.json",
    "05_summary.md",
    "06_paper_table.csv",
    "07_figure_data.csv",
    "08_deviations.json",
    "artifact_manifest.json",
)
MANIFEST_FILENAME = "artifact_manifest.json"

STAGE_MANIFEST_FIELDS = (
    "schema_version",
    "phase",
    "track",
    "run_id",
    "status",
    "start_time_utc",
    "end_time_utc",
    "objective",
    "hypothesis",
    "scope",
    "out_of_scope",
    "model_id",
    "model_revision",
    "code_commit",
    "image_digest",
    "hardware",
    "subagents",
    "inputs",
    "protocol_hash",
    "output_files",
)
PROTOCOL_SNAPSHOT_FIELDS = (
    "research_question",
    "primary_metric",
    "secondary_metrics",
    "decision_rules",
    "sample_size",
    "seeds",
    "conditions",
    "inclusion_rules",
    "exclusion_rules",
    "stopping_rules",
    "retry_rules",
    "scientific_claim_boundary",
)
RECORD_FIELDS = (
    "record_id",
    "run_id",
    "phase",
    "track",
    "source_item_id",
    "condition",
    "status",
    "input_hash",
    "output_hash",
    "evaluation",
)
METRICS_COLUMNS = (
    "run_id",
    "phase",
    "track",
    "metric",
    "stratum",
    "condition",
    "n",
    "numerator",
    "denominator",
    "value",
    "ci_lower",
    "ci_upper",
    "threshold",
    "passed",
    "not_applicable_reason",
)
PAPER_TABLE_COLUMNS = (
    "run_id",
    "phase",
    "track",
    "row_label",
    "condition",
    "n_prompts",
    "metric",
    "value",
    "unit",
    "status",
    "not_applicable_reason",
)
FIGURE_DATA_COLUMNS = (
    "run_id",
    "phase",
    "track",
    "figure_id",
    "series",
    "x_label",
    "x_value",
    "y_label",
    "y_value",
    "status",
    "not_applicable_reason",
)
DECISION_FIELDS = (
    "status",
    "decision",
    "criteria_passed",
    "criteria_failed",
    "criteria_not_applicable",
    "deviations",
    "scientific_interpretation",
    "prohibited_interpretations",
    "next_gate",
)
SUMMARY_SECTIONS = (
    "# Summary",
    "## Objective",
    "## Scope",
    "## Provenance",
    "## Execution",
    "## Results",
    "## Decision",
    "## Deviations and errors",
    "## Scientific interpretation",
    "## Limitations",
    "## Paper relevance",
    "## Next gate",
)

NEXT_GATE = (
    "Main-agent review of the executed saturation measurements before any "
    "larger fit is authorized. No behavioral or semantic gate is opened."
)

FORBIDDEN_CORPUS_CUES = (
    "phase1",
    "phase 1",
    "evaluator",
    "locked",
    "reference answer",
    "answer-only",
)

CRITERIA: dict[str, dict[str, Any]] = {
    "matrix_finite_rate": {
        "family": "stability",
        "direction": "min",
        "threshold": FINITE_RATE_MIN,
        "unit": "ratio",
        "description": "Every fitted/merged Jacobian matrix must be finite.",
    },
    "lens_save_load_max_abs": {
        "family": "stability",
        "direction": "max",
        "threshold": SAVE_LOAD_MAX_ABS_TOLERANCE,
        "unit": "abs",
        "description": "fp32 lens save/load must be exact for every layer.",
    },
    "shard_merge_vs_direct_max_abs": {
        "family": "stability",
        "direction": "max",
        "threshold": MERGE_MAX_ABS_TOLERANCE,
        "unit": "abs",
        "description": "Merged shards must match the direct-subset fit.",
    },
    "shard_merge_vs_direct_relative_frobenius": {
        "family": "stability",
        "direction": "max",
        "threshold": MERGE_RELATIVE_TOLERANCE,
        "unit": "ratio",
        "description": "Relative Frobenius merge/direct-subset difference.",
    },
    "apply_save_load_consistency": {
        "family": "stability",
        "direction": "min",
        "threshold": 1.0,
        "unit": "boolean",
        "description": "Reloaded lens apply output must match the in-memory lens.",
    },
    "convergence_relative_frobenius_10_vs_25": {
        "family": "convergence",
        "direction": "max",
        "threshold": CONVERGENCE_RELATIVE_FROBENIUS_MAX,
        "unit": "ratio",
        "description": "Relative Frobenius change from the 10- to the 25-prompt lens.",
    },
    "convergence_cosine_10_vs_25": {
        "family": "convergence",
        "direction": "min",
        "threshold": CONVERGENCE_COSINE_MIN,
        "unit": "cosine",
        "description": "Flattened cosine between the 10- and 25-prompt lens matrices.",
    },
    "heldout_topk_overlap_mean": {
        "family": "convergence",
        "direction": "min",
        "threshold": TOPK_OVERLAP_MIN,
        "unit": "ratio",
        "description": (
            "Mean held-out top-k overlap between the 10- and 25-prompt lens "
            "logits; technical stability only, never semantic evidence."
        ),
    },
    "heldout_rank_correlation_mean": {
        "family": "convergence",
        "direction": "min",
        "threshold": RANK_CORRELATION_MIN,
        "unit": "rho",
        "description": (
            "Mean held-out Spearman rank correlation between the 10- and "
            "25-prompt lens logits; technical stability only."
        ),
    },
}
STABILITY_CRITERIA = tuple(
    name for name, spec in CRITERIA.items() if spec["family"] == "stability"
)
CONVERGENCE_CRITERIA = tuple(
    name for name, spec in CRITERIA.items() if spec["family"] == "convergence"
)

DECISION_RULES = (
    "ENGINEERING_UNSTABLE when any stability criterion fails.",
    "INCONCLUSIVE when the run is a self-test, a required stage did not "
    "complete, or any criterion is not applicable.",
    "ENGINEERING_STABLE when every stability and convergence criterion passes.",
    "ENGINEERING_IMPROVING when stability passes but a convergence criterion "
    "is not yet met, meaning more fit prompts are still changing the lens.",
)
INCLUSION_RULES = (
    "Only prompts registered in data/jlens_saturation_prompts.jsonl are used.",
    "Fit prompts are role=fit in declared file order; apply-stability prompts "
    "are role=heldout and are disjoint from every fit set.",
    "Every fit uses source layers [6,13,20] and target layer 27.",
)
EXCLUSION_RULES = (
    "No behavioral candidate-bank prompt, parser fixture, evaluator-set item, "
    "or answer label may enter any fit or apply set.",
    "role=reserve prompts are not used by this run.",
)
STOPPING_RULES = (
    "A stage that cannot finish inside the registered planning budget is "
    "recorded as skipped_time_guard and the run exports what it measured.",
    "A stop-classified memory measurement blocks further fitting.",
    "The application watchdog fires before the platform timeout so the "
    "artifact pack is always exported.",
)
RETRY_RULES = (
    "Official checkpoint/resume only; one job re-execution may resume from the "
    "newest manifest-complete Blob snapshot.",
    "No parser, corpus, threshold, or interpretation may change on retry.",
)
PRIMARY_METRIC = "convergence_relative_frobenius_10_vs_25"
SECONDARY_METRICS = (
    "convergence_cosine_10_vs_25",
    "shard_merge_vs_direct_max_abs",
    "shard_merge_vs_direct_relative_frobenius",
    "weighted_recombination_vs_direct_max_abs",
    "fit_repeatability_max_abs",
    "matrix_finite_rate",
    "matrix_norm",
    "lens_save_load_max_abs",
    "apply_save_load_consistency",
    "heldout_topk_overlap_mean",
    "heldout_rank_correlation_mean",
    "heldout_logit_cosine_mean",
    "fit_wall_clock_seconds",
    "fit_wall_clock_seconds_per_prompt",
    "gpu_peak_allocated_bytes",
    "gpu_peak_reserved_bytes",
    "checkpoint_bytes",
    "lens_bytes",
)


class SaturationValidationError(base.Phase05ValidationError):
    """A preregistered Phase 0.5B control was violated."""


class CorpusValidationError(SaturationValidationError):
    """The saturation fit corpus is not the registered corpus."""


class ArtifactValidationError(SaturationValidationError):
    """The standard artifact pack is incomplete or malformed."""


canonical_json_bytes = base.canonical_json_bytes
sha256_bytes = base.sha256_bytes
sha256_file = base.sha256_file


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def proxy_token_count(text: str) -> int:
    """Deterministic tokenizer-free proxy: word and punctuation units.

    The real Hugging Face tokenizer is unavailable off-container, so corpus
    registration records this proxy. The container run records the guarded
    tokenizer length for every prompt in ``02_records.jsonl``.
    """

    return len(re.findall(r"\w+|[^\w\s]", text))


def load_saturation_corpus(path: str | Path) -> dict[str, Any]:
    """Load and validate the registered 50-prompt saturation corpus."""

    corpus_path = Path(path)
    raw = corpus_path.read_bytes()
    if b"\r" in raw:
        raise CorpusValidationError("corpus must use LF newlines")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if set(record) != {"id", "role", "text"}:
            raise CorpusValidationError(
                f"corpus line {line_number} must contain only id/role/text"
            )
        if not all(
            isinstance(record[key], str) and record[key].strip() for key in record
        ):
            raise CorpusValidationError(
                f"corpus line {line_number} contains an empty value"
            )
        if record["role"] not in {"fit", "heldout", "reserve"}:
            raise CorpusValidationError(
                f"corpus line {line_number} has an unregistered role"
            )
        lowered = f"{record['id']} {record['text']}".lower()
        if any(cue in lowered for cue in FORBIDDEN_CORPUS_CUES):
            raise CorpusValidationError(
                f"corpus line {line_number} contains a forbidden fixture cue"
            )
        tokens = proxy_token_count(record["text"])
        if tokens < MIN_PROXY_TOKENS:
            raise CorpusValidationError(
                f"corpus line {line_number} is shorter than the registered "
                f"minimum of {MIN_PROXY_TOKENS} proxy tokens"
            )
        records.append(
            {
                "id": record["id"],
                "role": record["role"],
                "text": record["text"],
                "proxy_token_count": tokens,
                "char_count": len(record["text"]),
                "text_sha256": sha256_text(record["text"]),
            }
        )
    if len(records) != CORPUS_TOTAL:
        raise CorpusValidationError(
            f"saturation corpus must contain exactly {CORPUS_TOTAL} prompts"
        )
    if len({record["id"] for record in records}) != len(records):
        raise CorpusValidationError("corpus IDs must be unique")
    if len({record["text"] for record in records}) != len(records):
        raise CorpusValidationError("corpus prompt texts must be unique")
    roles = {
        role: [record["id"] for record in records if record["role"] == role]
        for role in ("fit", "heldout", "reserve")
    }
    expected_counts = {
        "fit": FIT_PROMPTS,
        "heldout": HELDOUT_PROMPTS,
        "reserve": RESERVE_PROMPTS,
    }
    actual_counts = {role: len(ids) for role, ids in roles.items()}
    if actual_counts != expected_counts:
        raise CorpusValidationError(
            f"corpus role counts {actual_counts} do not match {expected_counts}"
        )
    canonical = base.canonical_jsonl_sha256(
        [
            {"id": record["id"], "role": record["role"], "text": record["text"]}
            for record in records
        ]
    )
    return {
        "path": corpus_path.as_posix(),
        "file_sha256": sha256_bytes(raw),
        "canonical_sha256": canonical,
        "bytes": len(raw),
        "records": records,
        "roles": roles,
        "counts": actual_counts,
        "proxy_tokenizer": "regex_word_punctuation_proxy_v1",
        "proxy_token_min": min(record["proxy_token_count"] for record in records),
        "proxy_token_max": max(record["proxy_token_count"] for record in records),
    }


def build_fit_plan(corpus: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the deterministic fit/shard/control/held-out prompt sets."""

    by_id = {record["id"]: record for record in corpus["records"]}
    fit_ids = list(corpus["roles"]["fit"])
    heldout_ids = list(corpus["roles"]["heldout"])
    if len(fit_ids) != FIT_B_PROMPTS or sum(FIT_B_SHARDS) != FIT_B_PROMPTS:
        raise SaturationValidationError("fit plan prompt accounting is invalid")

    def unit(name: str, ids: Sequence[str]) -> dict[str, Any]:
        texts = [by_id[item]["text"] for item in ids]
        return {
            "unit": name,
            "prompt_ids": list(ids),
            "prompt_count": len(ids),
            "prompt_order_sha256": base.canonical_jsonl_sha256(
                [{"id": item, "text": by_id[item]["text"]} for item in ids]
            ),
            "texts": texts,
        }

    shards = []
    start = 0
    for index, size in enumerate(FIT_B_SHARDS, 1):
        shards.append(unit(f"fit_b_shard_{index}", fit_ids[start : start + size]))
        start += size
    control_ids = fit_ids[FIT_B_PROMPTS - CONTROL_SUBSET_SIZE :]
    control_shards = []
    offset = 0
    for index, size in enumerate(CONTROL_SUBSET_SHARDS, 1):
        control_shards.append(
            unit(f"control_shard_{index}", control_ids[offset : offset + size])
        )
        offset += size
    plan = {
        "fit_a": unit("fit_a_direct", fit_ids[:FIT_A_PROMPTS]),
        "fit_b_shards": shards,
        "fit_b_prompt_ids": fit_ids,
        "fit_b_prompt_order_sha256": base.canonical_jsonl_sha256(
            [{"id": item, "text": by_id[item]["text"]} for item in fit_ids]
        ),
        "control_direct": unit("control_direct", control_ids),
        "control_shards": control_shards,
        "heldout": unit("heldout_apply", heldout_ids),
        "source_layers": list(SOURCE_LAYERS),
        "target_layer": TARGET_LAYER,
    }
    fit_a_set = set(plan["fit_a"]["prompt_ids"])
    heldout_set = set(heldout_ids)
    if fit_a_set & heldout_set or set(fit_ids) & heldout_set:
        raise SaturationValidationError("held-out prompts must be disjoint from fits")
    if plan["control_direct"]["prompt_ids"] != shards[-1]["prompt_ids"]:
        raise SaturationValidationError(
            "the merge control subset must equal the final 25-prompt shard"
        )
    return plan


def relative_frobenius(difference_l2: float, reference_l2: float) -> float:
    """Relative Frobenius difference with a stable zero-reference guard."""

    if not math.isfinite(difference_l2) or not math.isfinite(reference_l2):
        raise base.NumericalValidationError("relative Frobenius inputs are non-finite")
    return difference_l2 / max(reference_l2, 1e-12)


def cosine_from_flat(dot: float, norm_a: float, norm_b: float) -> float:
    if not all(math.isfinite(value) for value in (dot, norm_a, norm_b)):
        raise base.NumericalValidationError("cosine inputs are non-finite")
    denominator = norm_a * norm_b
    if denominator <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / denominator))


def vector_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise base.NumericalValidationError("cosine vectors have different lengths")
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right, strict=True):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    return cosine_from_flat(dot, math.sqrt(left_norm), math.sqrt(right_norm))


def vector_l2_difference(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise base.NumericalValidationError("vectors have different lengths")
    total = 0.0
    for a, b in zip(left, right, strict=True):
        delta = a - b
        total += delta * delta
    return math.sqrt(total)


def top_k_indices(values: Sequence[float], k: int) -> list[int]:
    """Deterministic top-k: descending value, ascending index on ties."""

    if k <= 0:
        raise SaturationValidationError("top-k requires a positive k")
    order = sorted(range(len(values)), key=lambda index: (-values[index], index))
    return order[: min(k, len(values))]


def top_k_overlap(left: Sequence[int], right: Sequence[int]) -> dict[str, Any]:
    """Technical top-k overlap. Never semantic evidence."""

    left_set = set(left)
    right_set = set(right)
    denominator = max(len(left_set), 1)
    union = len(left_set | right_set)
    overlap = len(left_set & right_set)
    return {
        "k": len(left_set),
        "overlap": overlap,
        "fraction": overlap / denominator,
        "jaccard": overlap / union if union else 0.0,
        "interpretation": "technical_stability_only_no_semantic_claim",
    }


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while (
            end + 1 < len(order) and values[order[end + 1]] == values[order[position]]
        ):
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[order[index]] = average
        position = end + 1
    return ranks


def spearman_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    """Spearman rank correlation with average ranks for ties."""

    if len(left) != len(right):
        raise base.NumericalValidationError("rank vectors have different lengths")
    if len(left) < 2:
        raise base.NumericalValidationError("rank correlation needs at least two items")
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    n = len(left_ranks)
    mean_left = sum(left_ranks) / n
    mean_right = sum(right_ranks) / n
    covariance = 0.0
    left_variance = 0.0
    right_variance = 0.0
    for a, b in zip(left_ranks, right_ranks, strict=True):
        da = a - mean_left
        db = b - mean_right
        covariance += da * db
        left_variance += da * da
        right_variance += db * db
    denominator = math.sqrt(left_variance * right_variance)
    if denominator <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, covariance / denominator))


def mean(values: Sequence[float]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


class PureLensMath:
    """Dependency-free matrix math over nested float sequences."""

    name = "pure_python"

    @staticmethod
    def _shape(matrix: Sequence[Sequence[float]]) -> list[int]:
        return [len(matrix), len(matrix[0]) if matrix else 0]

    def matrix_stats(self, matrix: Sequence[Sequence[float]]) -> dict[str, Any]:
        total = 0.0
        finite = True
        for row in matrix:
            for value in row:
                if not math.isfinite(value):
                    finite = False
                    continue
                total += value * value
        return {
            "shape": self._shape(matrix),
            "dtype": "float32",
            "finite": finite,
            "norm": math.sqrt(total) if finite else float("nan"),
        }

    def matrix_difference(
        self, left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
    ) -> dict[str, Any]:
        if self._shape(left) != self._shape(right):
            raise base.NumericalValidationError("matrix shapes differ")
        max_abs = 0.0
        total = 0.0
        for left_row, right_row in zip(left, right, strict=True):
            for a, b in zip(left_row, right_row, strict=True):
                delta = a - b
                max_abs = max(max_abs, abs(delta))
                total += delta * delta
        return {"max_abs": max_abs, "l2_norm": math.sqrt(total)}

    def matrix_flat_dot(
        self, left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
    ) -> float:
        if self._shape(left) != self._shape(right):
            raise base.NumericalValidationError("matrix shapes differ")
        total = 0.0
        for left_row, right_row in zip(left, right, strict=True):
            for a, b in zip(left_row, right_row, strict=True):
                total += a * b
        return total

    def matrix_weighted_mean(
        self, pairs: Sequence[tuple[Sequence[Sequence[float]], int]]
    ) -> list[list[float]]:
        if not pairs:
            raise base.NumericalValidationError("weighted mean needs at least one term")
        weight_total = sum(weight for _, weight in pairs)
        if weight_total <= 0:
            raise base.NumericalValidationError("weighted mean needs positive weights")
        first = pairs[0][0]
        rows, columns = self._shape(first)
        result = [[0.0] * columns for _ in range(rows)]
        for matrix, weight in pairs:
            if self._shape(matrix) != [rows, columns]:
                raise base.NumericalValidationError("weighted mean shape mismatch")
            for row_index, row in enumerate(matrix):
                for column_index, value in enumerate(row):
                    result[row_index][column_index] += value * weight
        return [[value / weight_total for value in row] for row in result]

    def matrices_equal(
        self, left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
    ) -> bool:
        if self._shape(left) != self._shape(right):
            return False
        return all(
            a == b
            for left_row, right_row in zip(left, right, strict=True)
            for a, b in zip(left_row, right_row, strict=True)
        )

    def to_list(self, vector: Sequence[float]) -> list[float]:
        return [float(value) for value in vector]

    def allclose(
        self,
        left: Sequence[float],
        right: Sequence[float],
        *,
        rtol: float = APPLY_RTOL,
        atol: float = APPLY_ATOL,
    ) -> bool:
        if len(left) != len(right):
            return False
        return all(
            abs(a - b) <= atol + rtol * abs(b)
            for a, b in zip(left, right, strict=True)
        )


class TorchLensMath:
    """Torch-backed matrix math with identical semantics to PureLensMath."""

    name = "torch"

    def __init__(self, torch_module: Any) -> None:
        self.torch = torch_module

    def matrix_stats(self, matrix: Any) -> dict[str, Any]:
        return {
            "shape": list(matrix.shape),
            "dtype": str(matrix.dtype),
            "finite": bool(self.torch.isfinite(matrix).all().item()),
            "norm": float(matrix.float().norm().item()),
        }

    def matrix_difference(self, left: Any, right: Any) -> dict[str, Any]:
        if tuple(left.shape) != tuple(right.shape):
            raise base.NumericalValidationError("matrix shapes differ")
        difference = left.float() - right.float()
        return {
            "max_abs": float(difference.abs().max().item()),
            "l2_norm": float(difference.norm().item()),
        }

    def matrix_flat_dot(self, left: Any, right: Any) -> float:
        if tuple(left.shape) != tuple(right.shape):
            raise base.NumericalValidationError("matrix shapes differ")
        return float(
            self.torch.dot(
                left.float().reshape(-1).double(), right.float().reshape(-1).double()
            ).item()
        )

    def matrix_weighted_mean(self, pairs: Sequence[tuple[Any, int]]) -> Any:
        if not pairs:
            raise base.NumericalValidationError("weighted mean needs at least one term")
        weight_total = float(sum(weight for _, weight in pairs))
        if weight_total <= 0:
            raise base.NumericalValidationError("weighted mean needs positive weights")
        accumulator = None
        for matrix, weight in pairs:
            scaled = matrix.float() * float(weight)
            accumulator = scaled if accumulator is None else accumulator + scaled
        return accumulator / weight_total

    def matrices_equal(self, left: Any, right: Any) -> bool:
        return bool(self.torch.equal(left, right))

    def to_list(self, vector: Any) -> list[float]:
        return [float(value) for value in vector.detach().float().reshape(-1).tolist()]

    def allclose(
        self,
        left: Sequence[float],
        right: Sequence[float],
        *,
        rtol: float = APPLY_RTOL,
        atol: float = APPLY_ATOL,
    ) -> bool:
        if len(left) != len(right):
            return False
        return all(
            abs(a - b) <= atol + rtol * abs(b)
            for a, b in zip(left, right, strict=True)
        )


def compare_lens_matrices(
    math_backend: Any,
    left_jacobians: Mapping[int, Any],
    right_jacobians: Mapping[int, Any],
    *,
    source_layers: Sequence[int] = SOURCE_LAYERS,
) -> dict[str, Any]:
    """Layer-wise max-abs, relative Frobenius, and flattened cosine."""

    layers: dict[str, Any] = {}
    for layer in source_layers:
        left = left_jacobians[layer]
        right = right_jacobians[layer]
        difference = math_backend.matrix_difference(left, right)
        left_stats = math_backend.matrix_stats(left)
        right_stats = math_backend.matrix_stats(right)
        dot = math_backend.matrix_flat_dot(left, right)
        layers[str(layer)] = {
            "max_abs": difference["max_abs"],
            "l2_norm": difference["l2_norm"],
            "relative_frobenius": relative_frobenius(
                difference["l2_norm"], right_stats["norm"]
            ),
            "cosine": cosine_from_flat(dot, left_stats["norm"], right_stats["norm"]),
            "left_norm": left_stats["norm"],
            "right_norm": right_stats["norm"],
            "left_finite": left_stats["finite"],
            "right_finite": right_stats["finite"],
        }
    return {
        "layers": layers,
        "max_abs": max(item["max_abs"] for item in layers.values()),
        "max_relative_frobenius": max(
            item["relative_frobenius"] for item in layers.values()
        ),
        "mean_relative_frobenius": mean(
            [item["relative_frobenius"] for item in layers.values()]
        ),
        "min_cosine": min(item["cosine"] for item in layers.values()),
        "mean_cosine": mean([item["cosine"] for item in layers.values()]),
    }


def compare_logit_vectors(
    left: Sequence[float],
    right: Sequence[float],
    *,
    top_k: int = TOP_K,
    secondary_top_k: int = TOP_K_SECONDARY,
) -> dict[str, Any]:
    """Technical apply-stability comparison of two logit vectors."""

    left_top = top_k_indices(left, top_k)
    right_top = top_k_indices(right, top_k)
    left_top_secondary = top_k_indices(left, secondary_top_k)
    right_top_secondary = top_k_indices(right, secondary_top_k)
    return {
        "cosine": vector_cosine(left, right),
        "l2_difference": vector_l2_difference(left, right),
        "rank_correlation": spearman_correlation(left, right),
        "top_k": top_k_overlap(left_top, right_top),
        "top_k_secondary": top_k_overlap(left_top_secondary, right_top_secondary),
        "top1_match": bool(left_top[0] == right_top[0]),
        "interpretation": "technical_stability_only_no_semantic_claim",
    }


def evaluate_criterion(name: str, value: Any) -> dict[str, Any]:
    spec = CRITERIA.get(name)
    if spec is None:
        raise SaturationValidationError(f"unregistered criterion: {name}")
    threshold = float(spec["threshold"])
    if value is None:
        return {
            "criterion": name,
            "family": spec["family"],
            "value": None,
            "threshold": threshold,
            "passed": None,
            "not_applicable_reason": "metric was not measured",
        }
    numeric = float(bool(value)) if isinstance(value, bool) else float(value)
    if not math.isfinite(numeric):
        passed = False
    elif spec["direction"] == "max":
        passed = numeric <= threshold
    else:
        passed = numeric >= threshold
    return {
        "criterion": name,
        "family": spec["family"],
        "value": numeric,
        "threshold": threshold,
        "passed": bool(passed),
        "not_applicable_reason": None,
    }


def evaluate_decision(
    values: Mapping[str, Any],
    *,
    stages: Mapping[str, Mapping[str, Any]] | None = None,
    self_test: bool = False,
    blocked_reason: str | None = None,
    deviations: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Apply the preregistered engineering decision rules."""

    evaluations = [evaluate_criterion(name, values.get(name)) for name in CRITERIA]
    passed = [item["criterion"] for item in evaluations if item["passed"] is True]
    failed = [item["criterion"] for item in evaluations if item["passed"] is False]
    not_applicable = [
        {
            "criterion": item["criterion"],
            "reason": item["not_applicable_reason"] or "not measured",
        }
        for item in evaluations
        if item["passed"] is None
    ]
    stage_map = dict(stages or {})
    incomplete_stages = sorted(
        stage
        for stage in STAGES
        if stage_map.get(stage, {}).get("status") != "success"
    )
    stability_failed = [name for name in failed if name in STABILITY_CRITERIA]

    if blocked_reason:
        status = "BLOCKED"
        decision = "INCONCLUSIVE"
        interpretation = (
            f"The run was blocked before a complete measurement: {blocked_reason}. "
            "No engineering stability conclusion is available."
        )
    elif stability_failed:
        status = "FAIL"
        decision = "ENGINEERING_UNSTABLE"
        interpretation = (
            "At least one numerical stability control failed "
            f"({', '.join(stability_failed)}). The pipeline is not yet a "
            "reliable engineering base; no scientific conclusion follows."
        )
    elif self_test or incomplete_stages or not_applicable:
        status = "INCONCLUSIVE"
        decision = "INCONCLUSIVE"
        reason = (
            "synthetic self-test backend"
            if self_test
            else f"incomplete stages/metrics: {incomplete_stages or not_applicable}"
        )
        interpretation = (
            f"The measurement set is incomplete ({reason}). No engineering "
            "stability or convergence conclusion is drawn."
        )
    elif failed:
        status = "COMPLETE"
        decision = "ENGINEERING_IMPROVING"
        interpretation = (
            "Numerics, sharding, merge, serialization, and apply were stable, "
            "but the 10-to-25-prompt comparison has not yet reached the "
            "registered convergence thresholds "
            f"({', '.join(failed)}). More fit prompts still change the lens. "
            "This is an engineering observation only."
        )
    else:
        status = "PASS"
        decision = "ENGINEERING_STABLE"
        interpretation = (
            "The 10-prompt fit, the sharded 25-prompt fit with merge, the "
            "direct-subset merge control, serialization, and held-out apply "
            "were numerically stable and the registered convergence thresholds "
            "were met. This is engineering feasibility evidence only."
        )

    return {
        "status": status,
        "decision": decision,
        "criteria_passed": passed,
        "criteria_failed": failed,
        "criteria_not_applicable": not_applicable,
        "deviations": [dict(item) for item in deviations],
        "scientific_interpretation": interpretation,
        "prohibited_interpretations": list(PROHIBITED_INTERPRETATIONS),
        "next_gate": NEXT_GATE,
        "criteria_detail": evaluations,
        "incomplete_stages": incomplete_stages,
        "claim_boundary": SCIENTIFIC_CLAIM_BOUNDARY,
    }


def build_protocol_snapshot(
    *,
    sample_size: Mapping[str, Any],
    conditions: Sequence[str] = CONDITIONS,
    seeds: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = {
        "schema_version": f"{SCHEMA_VERSION}-protocol-snapshot",
        "phase": PHASE,
        "track": TRACK,
        "research_question": RESEARCH_QUESTION,
        "primary_metric": PRIMARY_METRIC,
        "secondary_metrics": list(SECONDARY_METRICS),
        "decision_rules": {
            "rules": list(DECISION_RULES),
            "criteria": {
                name: {
                    "family": spec["family"],
                    "direction": spec["direction"],
                    "threshold": spec["threshold"],
                    "unit": spec["unit"],
                    "description": spec["description"],
                }
                for name, spec in CRITERIA.items()
            },
            "decisions": list(DECISIONS),
            "statuses": list(DECISION_STATUSES),
        },
        "sample_size": dict(sample_size),
        "seeds": dict(seeds or SEEDS),
        "conditions": list(conditions),
        "inclusion_rules": list(INCLUSION_RULES),
        "exclusion_rules": list(EXCLUSION_RULES),
        "stopping_rules": list(STOPPING_RULES),
        "retry_rules": list(RETRY_RULES),
        "scientific_claim_boundary": SCIENTIFIC_CLAIM_BOUNDARY,
    }
    missing = [field for field in PROTOCOL_SNAPSHOT_FIELDS if field not in snapshot]
    if missing:
        raise ArtifactValidationError(f"protocol snapshot is missing {missing}")
    return snapshot


def build_stage_manifest(
    *,
    run_id: str,
    status: str,
    start_time_utc: str,
    end_time_utc: str,
    code_commit: str | None,
    image_digest: str | None,
    hardware: Mapping[str, Any],
    inputs: Mapping[str, Any],
    protocol_hash: str,
    subagents: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-stage-manifest",
        "phase": PHASE,
        "track": TRACK,
        "run_id": run_id,
        "status": status,
        "start_time_utc": start_time_utc,
        "end_time_utc": end_time_utc,
        "objective": OBJECTIVE,
        "hypothesis": HYPOTHESIS,
        "scope": list(SCOPE),
        "out_of_scope": list(OUT_OF_SCOPE),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "code_commit": code_commit,
        "image_digest": image_digest,
        "hardware": dict(hardware),
        "subagents": [dict(item) for item in subagents],
        "inputs": dict(inputs),
        "protocol_hash": protocol_hash,
        "output_files": list(ARTIFACT_FILENAMES),
    }
    missing = [field for field in STAGE_MANIFEST_FIELDS if field not in manifest]
    if missing:
        raise ArtifactValidationError(f"stage manifest is missing {missing}")
    return manifest


def make_record(
    *,
    record_id: str,
    run_id: str,
    source_item_id: str,
    condition: str,
    status: str,
    input_payload: Any,
    evaluation: Mapping[str, Any],
    output_hash: str | None = None,
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ArtifactValidationError(f"unregistered record condition: {condition}")
    evaluation_payload = dict(evaluation)
    return {
        "record_id": record_id,
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "source_item_id": source_item_id,
        "condition": condition,
        "status": status,
        "input_hash": sha256_bytes(canonical_json_bytes(input_payload)),
        "output_hash": output_hash
        or sha256_bytes(canonical_json_bytes(evaluation_payload)),
        "evaluation": evaluation_payload,
    }


def make_metric_row(
    *,
    run_id: str,
    metric: str,
    value: Any,
    stratum: str = "all",
    condition: str = "not_applicable",
    n: Any = "",
    numerator: Any = "",
    denominator: Any = "",
    threshold: Any = "",
    passed: Any = "",
    not_applicable_reason: str = "",
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "metric": metric,
        "stratum": stratum,
        "condition": condition,
        "n": _render_cell(n),
        "numerator": _render_cell(numerator),
        "denominator": _render_cell(denominator),
        "value": _render_cell(value),
        "ci_lower": "",
        "ci_upper": "",
        "threshold": _render_cell(threshold),
        "passed": _render_cell(passed),
        "not_applicable_reason": not_applicable_reason,
    }


def _render_cell(item: Any) -> str:
    if item is None or item == "":
        return ""
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, float):
        return format(item, ".12g")
    return str(item)


def make_paper_row(
    *,
    run_id: str,
    row_label: str,
    condition: str,
    n_prompts: Any,
    metric: str,
    value: Any,
    unit: str,
    status: str = "measured",
    not_applicable_reason: str = "",
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "row_label": row_label,
        "condition": condition,
        "n_prompts": _render_cell(n_prompts),
        "metric": metric,
        "value": _render_cell(value),
        "unit": unit,
        "status": status,
        "not_applicable_reason": not_applicable_reason,
    }


def make_figure_row(
    *,
    run_id: str,
    figure_id: str,
    series: str,
    x_label: str,
    x_value: Any,
    y_label: str,
    y_value: Any,
    status: str = "measured",
    not_applicable_reason: str = "",
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "figure_id": figure_id,
        "series": series,
        "x_label": x_label,
        "x_value": _render_cell(x_value),
        "y_label": y_label,
        "y_value": _render_cell(y_value),
        "status": status,
        "not_applicable_reason": not_applicable_reason,
    }


def empty_deviations() -> dict[str, Any]:
    return {
        "deviations": [],
        "unregistered_changes": [],
        "effect_on_interpretation": "none",
    }


def not_applicable_record(run_id: str, reason: str) -> dict[str, Any]:
    return make_record(
        record_id="not-applicable",
        run_id=run_id,
        source_item_id="not_applicable",
        condition="not_applicable",
        status="not_applicable",
        input_payload={"reason": reason},
        evaluation={"status": "not_applicable", "reason": reason},
    )


def not_applicable_metric_row(run_id: str, reason: str) -> dict[str, str]:
    return make_metric_row(
        run_id=run_id,
        metric="not_applicable",
        value="",
        stratum="all",
        condition="not_applicable",
        not_applicable_reason=reason,
    )


def not_applicable_paper_row(run_id: str, reason: str) -> dict[str, str]:
    return make_paper_row(
        run_id=run_id,
        row_label="not_applicable",
        condition="not_applicable",
        n_prompts=None,
        metric="not_applicable",
        value=None,
        unit="",
        status="not_applicable",
        not_applicable_reason=reason,
    )


def not_applicable_figure_row(run_id: str, reason: str) -> dict[str, str]:
    return make_figure_row(
        run_id=run_id,
        figure_id="not_applicable",
        series="not_applicable",
        x_label="not_applicable",
        x_value=None,
        y_label="not_applicable",
        y_value=None,
        status="not_applicable",
        not_applicable_reason=reason,
    )


def render_summary_markdown(context: Mapping[str, Any]) -> str:
    """Render 05_summary.md with the registered sections in order."""

    def block(items: Sequence[str]) -> list[str]:
        return [f"- {item}" for item in items] or ["- not_applicable"]

    decision = context["decision"]
    lines: list[str] = [
        SUMMARY_SECTIONS[0],
        "",
        f"- Phase: `{PHASE}` / track `{TRACK}`",
        f"- Run: `{context['run_id']}`",
        f"- Status: **{decision['status']}**",
        f"- Decision: **{decision['decision']}**",
        f"- Mode: {context.get('mode', 'container')}",
        "",
        SUMMARY_SECTIONS[1],
        "",
        OBJECTIVE,
        "",
        HYPOTHESIS,
        "",
        SUMMARY_SECTIONS[2],
        "",
        "In scope:",
        *block(list(SCOPE)),
        "",
        "Out of scope:",
        *block(list(OUT_OF_SCOPE)),
        "",
        SUMMARY_SECTIONS[3],
        "",
        f"- Official source: `{OFFICIAL_REPOSITORY}@{OFFICIAL_COMMIT}`",
        f"- Target model: `{MODEL_ID}@{MODEL_REVISION}` in {RUNTIME_DTYPE}",
        f"- Lens serialization dtype: `{LENS_SERIALIZATION_DTYPE}`",
        f"- Source layers: `{list(SOURCE_LAYERS)}`; target layer: `{TARGET_LAYER}`",
        f"- max_seq_len: `{MAX_SEQ_LEN}`; skip_first: `{SKIP_FIRST}`; "
        f"dim_batch: `{context.get('dim_batch')}`",
        f"- Fit corpus: `{context.get('corpus_path')}` "
        f"(file SHA-256 `{context.get('corpus_file_sha256')}`, "
        f"canonical SHA-256 `{context.get('corpus_canonical_sha256')}`)",
        f"- Code commit: `{context.get('code_commit')}`; image digest: "
        f"`{context.get('image_digest')}`",
        "",
        SUMMARY_SECTIONS[4],
        "",
        "| Stage | Status | Duration (s) |",
        "|---|---|---:|",
    ]
    for stage in STAGES:
        result = context.get("stages", {}).get(stage, {})
        duration = result.get("duration_seconds")
        rendered = "" if duration is None else format(float(duration), ".2f")
        lines.append(f"| {stage} | {result.get('status', 'not_run')} | {rendered} |")
    lines.extend(
        [
            "",
            SUMMARY_SECTIONS[5],
            "",
            "| Metric | Value | Threshold | Passed |",
            "|---|---:|---:|:--:|",
        ]
    )
    for item in decision.get("criteria_detail", []):
        value = item["value"]
        rendered_value = "not_applicable" if value is None else format(value, ".6g")
        passed = (
            "n/a"
            if item["passed"] is None
            else ("yes" if item["passed"] else "no")
        )
        lines.append(
            f"| {item['criterion']} | {rendered_value} | "
            f"{format(float(item['threshold']), '.6g')} | {passed} |"
        )
    for line in context.get("result_notes", []):
        lines.extend(["", line])
    lines.extend(
        [
            "",
            SUMMARY_SECTIONS[6],
            "",
            f"- Status: **{decision['status']}**",
            f"- Decision: **{decision['decision']}**",
            f"- Reason: {decision['scientific_interpretation']}",
            f"- Next gate: {decision['next_gate']}",
            "",
            SUMMARY_SECTIONS[7],
            "",
            *block(
                [
                    f"{item.get('id', 'deviation')}: {item.get('description', '')}"
                    for item in context.get("deviations", {}).get("deviations", [])
                ]
                + [
                    f"{item.get('stage', 'error')}: {item.get('error', '')}"
                    for item in context.get("errors", [])
                ]
            ),
            "",
            SUMMARY_SECTIONS[8],
            "",
            SCIENTIFIC_CLAIM_BOUNDARY,
            "",
            "Prohibited interpretations of this artifact pack:",
            *block(list(PROHIBITED_INTERPRETATIONS)),
            "",
            SUMMARY_SECTIONS[9],
            "",
            *block(
                [
                    "One GPU, one model, one revision, one prompt corpus.",
                    "Fit sets are nested (the 10-prompt set is a subset of the "
                    "25-prompt set), so the 10-vs-25 comparison measures "
                    "estimator movement, not independent replication.",
                    "Held-out apply stability uses 10 generic prompts at the "
                    "final position only.",
                    "No lens-quality, calibration, or semantic validation was "
                    "attempted.",
                ]
            ),
            "",
            SUMMARY_SECTIONS[10],
            "",
            *block(
                [
                    "Supplies the engineering feasibility row for J-lens "
                    "scaling: measured wall-clock, memory, checkpoint and lens "
                    "sizes at 10 and 25 prompts.",
                    "Supplies the sharded-fit-plus-merge equivalence control.",
                    "Supplies no behavioral, semantic, or workspace result.",
                ]
            ),
            "",
            SUMMARY_SECTIONS[11],
            "",
            NEXT_GATE,
            "",
        ]
    )
    return "\n".join(lines)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _csv_bytes(columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue().encode("utf-8")


def write_artifact_pack(
    pack_dir: str | Path,
    *,
    run_id: str,
    stage_manifest: Mapping[str, Any],
    protocol_snapshot: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    metrics: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
    summary_markdown: str,
    paper_rows: Sequence[Mapping[str, Any]],
    figure_rows: Sequence[Mapping[str, Any]],
    deviations: Mapping[str, Any] | None = None,
    generated_at_utc: str = "",
    writer: Callable[[Path, bytes], None] | None = None,
) -> dict[str, Any]:
    """Write the standard artifact pack with artifact_manifest.json last."""

    directory = Path(pack_dir)
    directory.mkdir(parents=True, exist_ok=True)
    emit = writer or _write_bytes

    payload_records = list(records) or [
        not_applicable_record(run_id, "no per-item record was produced")
    ]
    payload_metrics = list(metrics) or [
        not_applicable_metric_row(run_id, "no metric was produced")
    ]
    payload_paper = list(paper_rows) or [
        not_applicable_paper_row(run_id, "no paper row was produced")
    ]
    payload_figures = list(figure_rows) or [
        not_applicable_figure_row(run_id, "no figure series was produced")
    ]

    emit(directory / "00_stage_manifest.json", canonical_json_bytes(stage_manifest))
    emit(
        directory / "01_protocol_snapshot.json", canonical_json_bytes(protocol_snapshot)
    )
    emit(
        directory / "02_records.jsonl",
        b"".join(canonical_json_bytes(record) for record in payload_records),
    )
    emit(directory / "03_metrics.csv", _csv_bytes(METRICS_COLUMNS, payload_metrics))
    emit(directory / "04_decision.json", canonical_json_bytes(decision))
    emit(directory / "05_summary.md", summary_markdown.encode("utf-8"))
    emit(
        directory / "06_paper_table.csv",
        _csv_bytes(PAPER_TABLE_COLUMNS, payload_paper),
    )
    emit(
        directory / "07_figure_data.csv",
        _csv_bytes(FIGURE_DATA_COLUMNS, payload_figures),
    )
    emit(
        directory / "08_deviations.json",
        canonical_json_bytes(dict(deviations or empty_deviations())),
    )

    artifacts = []
    for name in ARTIFACT_FILENAMES:
        if name == MANIFEST_FILENAME:
            continue
        path = directory / name
        if not path.is_file():
            raise ArtifactValidationError(f"artifact {name} was not written")
        artifacts.append(
            {
                "path": name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-artifact-manifest",
        "phase": PHASE,
        "track": TRACK,
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "manifest_written_last": True,
        "artifacts": artifacts,
        "manifest_order": [entry["path"] for entry in artifacts],
    }
    emit(directory / MANIFEST_FILENAME, canonical_json_bytes(manifest))
    return manifest


def read_records(pack_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(pack_dir) / "02_records.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_artifact_pack(pack_dir: str | Path) -> dict[str, Any]:
    """Validate presence, required fields, and manifest completeness."""

    directory = Path(pack_dir)
    missing = [
        name for name in ARTIFACT_FILENAMES if not (directory / name).is_file()
    ]
    if missing:
        raise ArtifactValidationError(f"artifact pack is missing {missing}")
    unexpected = sorted(
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path.name not in ARTIFACT_FILENAMES
    )
    if unexpected:
        raise ArtifactValidationError(f"artifact pack contains extra files {unexpected}")

    stage_manifest = json.loads(
        (directory / "00_stage_manifest.json").read_text(encoding="utf-8")
    )
    absent = [field for field in STAGE_MANIFEST_FIELDS if field not in stage_manifest]
    if absent:
        raise ArtifactValidationError(f"00_stage_manifest.json is missing {absent}")
    if stage_manifest["phase"] != PHASE or stage_manifest["track"] != TRACK:
        raise ArtifactValidationError("stage manifest phase/track mismatch")

    snapshot = json.loads(
        (directory / "01_protocol_snapshot.json").read_text(encoding="utf-8")
    )
    absent = [field for field in PROTOCOL_SNAPSHOT_FIELDS if field not in snapshot]
    if absent:
        raise ArtifactValidationError(f"01_protocol_snapshot.json is missing {absent}")

    records = read_records(directory)
    if not records:
        raise ArtifactValidationError("02_records.jsonl must not be empty")
    for index, record in enumerate(records, 1):
        absent = [field for field in RECORD_FIELDS if field not in record]
        if absent:
            raise ArtifactValidationError(
                f"02_records.jsonl line {index} is missing {absent}"
            )

    with (directory / "03_metrics.csv").open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != METRICS_COLUMNS:
            raise ArtifactValidationError("03_metrics.csv header is invalid")
        metric_rows = list(reader)
    if not metric_rows:
        raise ArtifactValidationError("03_metrics.csv must contain at least one row")

    decision = json.loads((directory / "04_decision.json").read_text(encoding="utf-8"))
    absent = [field for field in DECISION_FIELDS if field not in decision]
    if absent:
        raise ArtifactValidationError(f"04_decision.json is missing {absent}")
    if decision["status"] not in DECISION_STATUSES:
        raise ArtifactValidationError(f"invalid decision status: {decision['status']}")
    if decision["decision"] not in DECISIONS:
        raise ArtifactValidationError(f"invalid decision: {decision['decision']}")

    summary = (directory / "05_summary.md").read_text(encoding="utf-8")
    position = -1
    for section in SUMMARY_SECTIONS:
        found = summary.find(f"\n{section}\n" if position >= 0 else f"{section}\n")
        if found <= position:
            raise ArtifactValidationError(
                f"05_summary.md section out of order or missing: {section}"
            )
        position = found

    for name, columns in (
        ("06_paper_table.csv", PAPER_TABLE_COLUMNS),
        ("07_figure_data.csv", FIGURE_DATA_COLUMNS),
    ):
        with (directory / name).open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if tuple(reader.fieldnames or ()) != columns:
                raise ArtifactValidationError(f"{name} header is invalid")
            if not list(reader):
                raise ArtifactValidationError(f"{name} must contain at least one row")

    deviations = json.loads(
        (directory / "08_deviations.json").read_text(encoding="utf-8")
    )
    absent = [
        field
        for field in ("deviations", "unregistered_changes", "effect_on_interpretation")
        if field not in deviations
    ]
    if absent:
        raise ArtifactValidationError(f"08_deviations.json is missing {absent}")

    manifest = json.loads(
        (directory / MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    declared = {entry["path"]: entry for entry in manifest.get("artifacts", [])}
    expected = [name for name in ARTIFACT_FILENAMES if name != MANIFEST_FILENAME]
    if sorted(declared) != sorted(expected):
        raise ArtifactValidationError("artifact manifest does not declare the pack")
    for name in expected:
        path = directory / name
        entry = declared[name]
        if entry.get("bytes") != path.stat().st_size or entry.get(
            "sha256"
        ) != sha256_file(path):
            raise ArtifactValidationError(f"artifact manifest is stale for {name}")
    manifest_mtime = (directory / MANIFEST_FILENAME).stat().st_mtime_ns
    stale = [
        name
        for name in expected
        if (directory / name).stat().st_mtime_ns > manifest_mtime
    ]
    if stale:
        raise ArtifactValidationError(
            f"artifact_manifest.json was not written last: {stale}"
        )
    return {
        "files": list(ARTIFACT_FILENAMES),
        "records": len(records),
        "metric_rows": len(metric_rows),
        "status": decision["status"],
        "decision": decision["decision"],
        "manifest_written_last": True,
    }


class SelfTestLens:
    """Deterministic synthetic lens used by ``--self-test``. Never a result."""

    def __init__(
        self,
        jacobians: Mapping[int, Sequence[Sequence[float]]],
        *,
        n_prompts: int,
        d_model: int,
    ) -> None:
        self.jacobians = {
            int(layer): [list(row) for row in matrix]
            for layer, matrix in jacobians.items()
        }
        self.source_layers = sorted(self.jacobians)
        self.n_prompts = int(n_prompts)
        self.d_model = int(d_model)

    def to_payload(self) -> dict[str, Any]:
        return {
            "J": {str(layer): self.jacobians[layer] for layer in self.source_layers},
            "n_prompts": self.n_prompts,
            "source_layers": list(self.source_layers),
            "d_model": self.d_model,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "SelfTestLens":
        return cls(
            {int(layer): matrix for layer, matrix in payload["J"].items()},
            n_prompts=payload["n_prompts"],
            d_model=payload["d_model"],
        )


class SelfTestBackend:
    """Torch-free deterministic backend for CPU self-tests and unit tests.

    It reproduces the interface the container runner needs so that the whole
    stage sequence, artifact pack, and decision logic can execute without a
    GPU, ``torch``, ``jlens``, or the target model. Its numbers are synthetic
    and every run that uses it is forced to INCONCLUSIVE.
    """

    is_synthetic = True
    name = "self_test"

    def __init__(
        self,
        *,
        d_model: int = 8,
        vocab_size: int = 32,
        source_layers: Sequence[int] = SOURCE_LAYERS,
        target_layer: int = TARGET_LAYER,
    ) -> None:
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.source_layers = list(source_layers)
        self.target_layer = target_layer
        self.math = PureLensMath()
        self.fit_calls: list[dict[str, Any]] = []

    @staticmethod
    def _unit(text: str, layer: int, row: int, column: int) -> float:
        seed = sha256_text(f"{text}|{layer}|{row}|{column}")
        return (int(seed[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0

    def _prompt_matrix(self, text: str, layer: int) -> list[list[float]]:
        return [
            [self._unit(text, layer, row, column) for column in range(self.d_model)]
            for row in range(self.d_model)
        ]

    def token_count(self, text: str) -> int:
        return min(MAX_SEQ_LEN, proxy_token_count(text))

    def fit(
        self,
        prompts: Sequence[str],
        *,
        checkpoint_path: Path | None = None,
        dim_batch: int = DEFAULT_DIM_BATCH,
        resume: bool = False,
    ) -> SelfTestLens:
        if not prompts:
            raise SaturationValidationError("a fit needs at least one prompt")
        self.fit_calls.append(
            {"prompts": list(prompts), "dim_batch": dim_batch, "resume": bool(resume)}
        )
        jacobians = {}
        for layer in self.source_layers:
            accumulator = [[0.0] * self.d_model for _ in range(self.d_model)]
            for prompt in prompts:
                matrix = self._prompt_matrix(prompt, layer)
                for row in range(self.d_model):
                    for column in range(self.d_model):
                        accumulator[row][column] += matrix[row][column]
            jacobians[layer] = [
                [value / len(prompts) for value in row] for row in accumulator
            ]
        lens = SelfTestLens(
            jacobians, n_prompts=len(prompts), d_model=self.d_model
        )
        if checkpoint_path is not None:
            _write_bytes(
                Path(checkpoint_path),
                canonical_json_bytes(
                    {
                        "jacobian_sum": lens.to_payload()["J"],
                        "n_done": len(prompts),
                        "next_idx": len(prompts),
                        "source_layers": self.source_layers,
                        "target_layer": self.target_layer,
                        "skip_first": SKIP_FIRST,
                    }
                ),
            )
        return lens

    def merge(self, lenses: Sequence[SelfTestLens]) -> SelfTestLens:
        total = sum(lens.n_prompts for lens in lenses)
        jacobians = {}
        for layer in self.source_layers:
            jacobians[layer] = self.math.matrix_weighted_mean(
                [(lens.jacobians[layer], lens.n_prompts) for lens in lenses]
            )
        return SelfTestLens(jacobians, n_prompts=total, d_model=self.d_model)

    def save_lens(
        self, lens: SelfTestLens, path: Path
    ) -> tuple[SelfTestLens, dict[str, Any]]:
        target = Path(path)
        _write_bytes(target, canonical_json_bytes(lens.to_payload()))
        payload = json.loads(target.read_text(encoding="utf-8"))
        reloaded = SelfTestLens.from_payload(payload)
        max_abs = max(
            self.math.matrix_difference(
                reloaded.jacobians[layer], lens.jacobians[layer]
            )["max_abs"]
            for layer in self.source_layers
        )
        audit = {
            "path": target.as_posix(),
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
            "lens_save_dtype": LENS_SERIALIZATION_DTYPE,
            "exact_max_abs": {
                str(layer): max_abs for layer in self.source_layers
            },
            "torch_equal_all_layers": max_abs == 0.0,
        }
        return reloaded, audit

    def apply(
        self, lens: SelfTestLens, text: str
    ) -> tuple[dict[int, list[float]], list[float], int]:
        logits: dict[int, list[float]] = {}
        for layer in self.source_layers:
            matrix = lens.jacobians[layer]
            source = [
                self._unit(text, self.target_layer, index, index)
                for index in range(self.d_model)
            ]
            projected = [
                sum(row[index] * source[index] for index in range(self.d_model))
                for row in matrix
            ]
            logits[layer] = [
                sum(
                    projected[index]
                    * self._unit(f"unembed-{token}", layer, index, 0)
                    for index in range(self.d_model)
                )
                for token in range(self.vocab_size)
            ]
        model_logits = [
            self._unit(f"model-{text}", self.target_layer, token, 0)
            for token in range(self.vocab_size)
        ]
        return logits, model_logits, self.token_count(text)

    def start_memory(self) -> None:
        return None

    def finish_memory(self) -> dict[str, Any]:
        return {
            "classification": "not_applicable",
            "reason": "self-test backend does not measure GPU memory",
            "gpu_peak_allocated_bytes": 0,
            "gpu_peak_reserved_bytes": 0,
            "gpu_total_bytes": 0,
            "gpu_free_bytes": 0,
            "host_rss_bytes": 0,
            "host_total_bytes": 0,
        }
