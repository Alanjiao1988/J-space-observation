"""Model-free controls for the Phase 0.5C J-lens disjoint-replication run.

Phase 0.5B fitted a 25-prompt J-lens ("25A") on ``role=fit`` prompts. Phase
0.5C fits a second, prompt-disjoint 25-prompt lens ("25B") on the amended
``role=reserve`` block, merges the two with the official weighted merge into a
50-prompt lens ("50M"), and measures how far two independently-fitted same-size
linear operators differ numerically.

This module holds every deterministic control that does not need a GPU, the
official ``jlens`` package, or the target model: corpus registration, the fit
plan, pure numeric comparisons, the preregistered decision rules, and the
artifact-pack writer/validator wiring.

Everything here is **engineering numerics only**. Top-k overlap and rank
correlation are technical stability statistics comparing two fitted linear
operators. They are never semantic evidence and never support a workspace,
hidden-reasoning, internal chain-of-thought, or J-space claim.
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_HELPER_ROOT = str(Path(__file__).resolve().parent)
if _HELPER_ROOT not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, _HELPER_ROOT)

import phase05_jlens as base  # noqa: E402
import phase05_jlens_saturation as sat  # noqa: E402

PHASE = "phase05c-jlens-disjoint"
TRACK = "track-a1"
SCHEMA_VERSION = "phase05c-jlens-disjoint-v1"

# ---------------------------------------------------------------------------
# frozen technical settings, inherited unchanged from Phase 0.5A/0.5B
# ---------------------------------------------------------------------------
MODEL_ID = sat.MODEL_ID
MODEL_REVISION = sat.MODEL_REVISION
MODEL_LAYERS = sat.MODEL_LAYERS
MODEL_WIDTH = sat.MODEL_WIDTH
RUNTIME_DTYPE = sat.RUNTIME_DTYPE
LENS_SERIALIZATION_DTYPE = sat.LENS_SERIALIZATION_DTYPE
OFFICIAL_REPOSITORY = sat.OFFICIAL_REPOSITORY
OFFICIAL_COMMIT = sat.OFFICIAL_COMMIT
MAX_SEQ_LEN = sat.MAX_SEQ_LEN
SKIP_FIRST = sat.SKIP_FIRST
SOURCE_LAYERS = sat.SOURCE_LAYERS
TARGET_LAYER = sat.TARGET_LAYER
DEFAULT_DIM_BATCH = sat.DEFAULT_DIM_BATCH
ALLOWED_DIM_BATCH = sat.ALLOWED_DIM_BATCH
DIM_BATCH_2_JUSTIFICATION = sat.DIM_BATCH_2_JUSTIFICATION
SEEDS = dict(sat.SEEDS)
TOP_K = sat.TOP_K
TOP_K_SECONDARY = sat.TOP_K_SECONDARY
MIN_PROXY_TOKENS = sat.MIN_PROXY_TOKENS
APPLY_RTOL = sat.APPLY_RTOL
APPLY_ATOL = sat.APPLY_ATOL

# ---------------------------------------------------------------------------
# corpus and fit plan
# ---------------------------------------------------------------------------
CORPUS_REVISION = "r2-60"
CORPUS_TOTAL = 60
FIT_A_PROMPTS = 25
FIT_B_PROMPTS = 25
MERGED_PROMPTS = 50
HELDOUT_PROMPTS = 10
FIT_B_SHARDS = (10, 10, 5)
MERGE_WEIGHTS = (FIT_A_PROMPTS, FIT_B_PROMPTS)

LENS_A = "lens_25a"
LENS_B = "lens_25b"
LENS_M = "lens_50m"
LENS_LABELS = (LENS_A, LENS_B, LENS_M)
LENS_DISPLAY = {LENS_A: "25A", LENS_B: "25B", LENS_M: "50M"}

PAIR_AB = "25A_vs_25B"
PAIR_AM = "25A_vs_50M"
PAIR_BM = "25B_vs_50M"
APPLY_PAIRS = (
    (PAIR_AB, LENS_A, LENS_B),
    (PAIR_AM, LENS_A, LENS_M),
    (PAIR_BM, LENS_B, LENS_M),
)
PAIRS_BY_LENS = {
    LENS_A: (PAIR_AB, PAIR_AM),
    LENS_B: (PAIR_AB, PAIR_BM),
    LENS_M: (PAIR_AM, PAIR_BM),
}

# ---------------------------------------------------------------------------
# the already-executed Phase 0.5B 25A lens that this run loads and never refits
# ---------------------------------------------------------------------------
EXISTING_RUN_ID = "20260725T122016Z"
# The Blob prefix is phase05-jlens-saturation/<run id>. The string "05b" appears
# only in the local artifact path artifacts/phase05b-jlens-saturation/track-a/,
# so the Blob prefix must never be inferred from the local directory name.
EXISTING_PHASE = "phase05-jlens-saturation"
EXISTING_STORAGE_ACCOUNT = "stjspacefiles0709085305"
EXISTING_RESOURCE_GROUP = "rg-jspace-observation-sea"
EXISTING_BLOB_CONTAINER = "jspace-results"
EXISTING_LENS_FILENAME = "fit_b_merged_lens.pt"
EXISTING_LENS_BLOB = (
    f"{EXISTING_PHASE}/{EXISTING_RUN_ID}"
    f"/attempts/primary/01-lens-binaries/{EXISTING_LENS_FILENAME}"
)
EXISTING_LENS_SHA256 = (
    "cb17a634e46e4b219b6dc16b98662ba82e986abbcc154fd650e5a8a5b828949d"
)
EXISTING_LENS_BYTES = 28314032
EXISTING_PROMPT_ORDER_SHA256 = (
    "99e097f32b81cadca4964f710580bce73432b5378793872815fb87329e049df7"
)
EXISTING_CODE_COMMIT = "408cd00540d5ded2b94ba75fc3616f8702e85465"
EXISTING_IMAGE_DIGEST = (
    "sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f"
)
# Phase 0.5B measured the official merge against an official direct fit on the
# same prompts. That control is NOT repeated here.
EXISTING_MERGE_CONTROL = {
    "run_id": EXISTING_RUN_ID,
    "shard_merge_vs_direct_max_abs": 2.384185791015625e-07,
    "shard_merge_vs_direct_max_abs_limit": 1e-5,
    "shard_merge_vs_direct_relative_frobenius": 4.861504957758501e-08,
    "shard_merge_vs_direct_relative_frobenius_limit": 1e-6,
    "weighted_recombination_vs_direct_max_abs": 0.0,
}

# Registered provenance of the 25A artifact this run consumes. The job reads the
# blob itself with its own user-assigned managed identity over the private
# endpoint; there is no workstation staging hop, no account key and no SAS.
EXISTING_LENS_PROVENANCE = {
    "source_run_id": EXISTING_RUN_ID,
    "source_phase": EXISTING_PHASE,
    "storage_account": EXISTING_STORAGE_ACCOUNT,
    "resource_group": EXISTING_RESOURCE_GROUP,
    "container": EXISTING_BLOB_CONTAINER,
    "blob": EXISTING_LENS_BLOB,
    "sha256": EXISTING_LENS_SHA256,
    "bytes": EXISTING_LENS_BYTES,
    "prompt_order_sha256": EXISTING_PROMPT_ORDER_SHA256,
    "source_code_commit": EXISTING_CODE_COMMIT,
    "source_image_digest": EXISTING_IMAGE_DIGEST,
    "access": "user_assigned_managed_identity_private_endpoint",
    "integrity_gate": "sha256 and byte count verified before the file is loaded",
    "refit_permitted": False,
}

# ---------------------------------------------------------------------------
# tolerances and registered thresholds
# ---------------------------------------------------------------------------
FINITE_RATE_MIN = 1.0
SAVE_LOAD_MAX_ABS_TOLERANCE = 0.0
APPLY_CONSISTENCY_MIN = 1.0
REPLICATE_RELATIVE_FROBENIUS_MAX = 0.10
REPLICATE_COSINE_MIN = 0.99
MERGE_WEIGHTING_MAX_ABS_TOLERANCE = sat.MERGE_MAX_ABS_TOLERANCE

# "Merged-50 held-out apply stability improves" is frozen here, before the run.
# Let a = the held-out statistic for the pair (25A, 25B), b = for (25A, 50M),
# and c = for (25B, 50M). The merged lens improves when it agrees with each
# single fit by more than the two single fits agree with each other, by at
# least the registered margin: mean(b, c) - a >= margin.
MERGED_IMPROVEMENT_TOPK_MARGIN = 0.02
MERGED_IMPROVEMENT_RANK_MARGIN = 0.005
MERGED_IMPROVEMENT_MARGINS: dict[str, float] = {
    "heldout_topk_overlap": MERGED_IMPROVEMENT_TOPK_MARGIN,
    "heldout_rank_correlation": MERGED_IMPROVEMENT_RANK_MARGIN,
}

STAGES = (
    "S0_environment",
    "S1_model",
    "S2_load_existing_25a",
    "S3_fit_25b_sharded_merge",
    "S4_merge_50",
    "S5_serialization",
    "S6_heldout_apply",
    "S7_replicate_variability",
)
REQUIRED_PREDECESSOR = {
    "S0_environment": None,
    "S1_model": "S0_environment",
    "S2_load_existing_25a": "S1_model",
    "S3_fit_25b_sharded_merge": "S2_load_existing_25a",
    "S4_merge_50": "S3_fit_25b_sharded_merge",
    "S5_serialization": "S4_merge_50",
    "S6_heldout_apply": "S5_serialization",
    "S7_replicate_variability": "S6_heldout_apply",
}
TERMINAL_STAGE_STATUSES = set(sat.TERMINAL_STAGE_STATUSES)

CONDITIONS = (
    "corpus_registration",
    "existing_lens_25a",
    "fit_25b_shard_1",
    "fit_25b_shard_2",
    "fit_25b_shard_3",
    "fit_25b_merged",
    "merge_50",
    "merge_weighting_cross_check",
    "serialization",
    "heldout_apply",
    "apply_stability",
    "replicate_variability",
    "not_applicable",
)

DECISIONS = (
    "REPLICATE_STABLE",
    "REPLICATE_IMPROVING",
    "REPLICATE_UNSTABLE",
    "FAILED",
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
    "any lens produced here described as scientifically usable",
)
SCIENTIFIC_CLAIM_BOUNDARY = (
    "Engineering numerics only. This run measures how far two independently "
    "fitted same-size (n=25) Jacobian lenses differ on disjoint prompt "
    "samples, and whether the official weighted merge of the two behaves "
    "numerically like a well-formed lens on held-out apply. Top-k overlap and "
    "rank correlation are technical stability statistics for fitted linear "
    "operators. They are not semantic evidence and support no claim about a "
    "workspace, hidden reasoning, an internal chain-of-thought, J-space, "
    "semantic convergence, or any lens being scientifically usable."
)
OBJECTIVE = (
    "Measure independent-fit estimator variability: fit a 25-prompt J-lens on "
    "a prompt set disjoint from the executed Phase 0.5B 25-prompt fit, merge "
    "the two with the official weighted merge into a 50-prompt lens, and "
    "record the numerical difference between all three operators on held-out "
    "apply."
)
HYPOTHESIS = (
    "Engineering hypothesis only: a second 25-prompt sharded fit completes "
    "inside the T4 time and memory envelope, the official weighted merge of "
    "the two 25-prompt lenses is a well-formed 50-prompt lens, every matrix "
    "stays finite, fp32 serialization stays exact, and the disagreement "
    "between the two independent fits is measurable."
)
RESEARCH_QUESTION = (
    "How much do two independently fitted same-size (n=25) J-lenses, fitted "
    "on disjoint prompt samples from the same corpus, differ numerically, and "
    "does the official weighted merge of the two behave numerically like a "
    "well-formed lens on held-out apply?"
)
SCOPE = (
    "load-and-verify the already-fitted Phase 0.5B 25-prompt lens (25A)",
    "25-prompt sharded fit on the disjoint reserve block (25B) with official "
    "merge",
    "official weighted merge of 25A and 25B into a 50-prompt lens (50M)",
    "matrix-level 25A/25B/50M comparison: relative Frobenius and cosine",
    "held-out apply comparison for all three lens pairs",
    "fp32 save/load exactness and apply save/load consistency",
    "wall-clock per prompt and peak GPU memory measurement",
)
OUT_OF_SCOPE = (
    "any semantic, interpretive, or scientific validity claim",
    "any claim that a lens produced here is scientifically usable",
    "hidden reasoning, internal workspace, invisible chain-of-thought, "
    "J-space, or semantic convergence claims",
    "lens quality, calibration, or behavioral evaluation",
    "re-fitting the Phase 0.5B 25-prompt lens",
    "a direct 50-prompt fit; the Phase 0.5B direct-subset merge control "
    "already demonstrated merge/direct numerical equivalence",
    "parser, evaluator-set, or locked-artifact material",
)

ARTIFACT_FILENAMES = sat.ARTIFACT_FILENAMES
MANIFEST_FILENAME = sat.MANIFEST_FILENAME
STAGE_MANIFEST_FIELDS = sat.STAGE_MANIFEST_FIELDS
PROTOCOL_SNAPSHOT_FIELDS = sat.PROTOCOL_SNAPSHOT_FIELDS
RECORD_FIELDS = sat.RECORD_FIELDS
METRICS_COLUMNS = sat.METRICS_COLUMNS
PAPER_TABLE_COLUMNS = sat.PAPER_TABLE_COLUMNS
FIGURE_DATA_COLUMNS = sat.FIGURE_DATA_COLUMNS
DECISION_FIELDS = sat.DECISION_FIELDS
SUMMARY_SECTIONS = sat.SUMMARY_SECTIONS

NEXT_GATE = (
    "Main-agent review of the executed independent-fit variability numbers. "
    "No behavioral, semantic, or scientific gate is opened by any outcome of "
    "this run."
)

# ---------------------------------------------------------------------------
# registered metrics
# ---------------------------------------------------------------------------
PRIMARY_METRIC = "25A_vs_25B_relative_frobenius"
REGISTERED_METRICS = (
    "25A_vs_25B_relative_frobenius",
    "25A_vs_25B_cosine",
    "25A_vs_50M_relative_frobenius",
    "25B_vs_50M_relative_frobenius",
    "25A_vs_50M_cosine",
    "25B_vs_50M_cosine",
    "heldout_apply_logit_cosine",
    "heldout_topk_overlap",
    "heldout_rank_correlation",
    "matrix_finite_rate",
    "save_load_max_abs",
    "wall_clock_per_prompt",
    "peak_gpu_memory",
)
SECONDARY_METRICS = tuple(
    name for name in REGISTERED_METRICS if name != PRIMARY_METRIC
)
# Recorded for auditability; none of these is a registered criterion.
SUPPORTING_OBSERVATIONS = (
    "apply_save_load_consistency",
    "merge_weighting_cross_check_max_abs",
    "merged_apply_improvement_topk",
    "merged_apply_improvement_rank_correlation",
    "heldout_topk_overlap_secondary",
    "matrix_norm",
    "lens_bytes",
    "checkpoint_bytes",
    "merge_seconds",
    "fit_wall_clock_seconds",
    "gpu_peak_allocated_bytes",
    "gpu_peak_reserved_bytes",
    "corpus_proxy_token_count",
    "corpus_token_count",
)

CRITERIA: dict[str, dict[str, Any]] = {
    "matrix_finite_rate": {
        "family": "transport",
        "direction": "min",
        "threshold": FINITE_RATE_MIN,
        "unit": "ratio",
        "description": (
            "Every fitted, loaded and merged Jacobian matrix must be finite."
        ),
    },
    "save_load_max_abs": {
        "family": "transport",
        "direction": "max",
        "threshold": SAVE_LOAD_MAX_ABS_TOLERANCE,
        "unit": "abs",
        "description": "fp32 lens save/load must be exact for every layer.",
    },
    "apply_save_load_consistency": {
        "family": "transport",
        "direction": "min",
        "threshold": APPLY_CONSISTENCY_MIN,
        "unit": "boolean",
        "description": (
            "Reloaded-lens held-out apply output must match the in-memory lens "
            "within rtol = atol = 5e-3 for every lens, prompt and layer."
        ),
    },
    "25A_vs_25B_relative_frobenius": {
        "family": "replication",
        "direction": "max",
        "threshold": REPLICATE_RELATIVE_FROBENIUS_MAX,
        "unit": "ratio",
        "description": (
            "Worst layer-wise relative Frobenius difference between the two "
            "independently fitted 25-prompt lenses."
        ),
    },
    "25A_vs_25B_cosine": {
        "family": "replication",
        "direction": "min",
        "threshold": REPLICATE_COSINE_MIN,
        "unit": "cosine",
        "description": (
            "Smallest layer-wise flattened cosine between the two "
            "independently fitted 25-prompt lenses."
        ),
    },
}
TRANSPORT_CRITERIA = tuple(
    name for name, spec in CRITERIA.items() if spec["family"] == "transport"
)
REPLICATION_CRITERIA = tuple(
    name for name, spec in CRITERIA.items() if spec["family"] == "replication"
)

DECISION_RULES = (
    "FAILED when any numerical transport gate fails (finite rate, fp32 "
    "save/load exactness, or apply save/load consistency).",
    "INCONCLUSIVE when the run is a self-test, a required stage did not "
    "complete, or any registered criterion is not applicable.",
    "REPLICATE_STABLE when the transport gates pass and both replicate "
    "criteria pass: 25A_vs_25B_relative_frobenius <= 0.10 and "
    "25A_vs_25B_cosine >= 0.99.",
    "REPLICATE_IMPROVING when the transport gates pass, a replicate criterion "
    "fails, and merged-50 held-out apply stability improves: "
    "mean(heldout_topk_overlap[25A_vs_50M], heldout_topk_overlap"
    "[25B_vs_50M]) - heldout_topk_overlap[25A_vs_25B] >= 0.02 AND the same "
    "difference for heldout_rank_correlation >= 0.005.",
    "REPLICATE_UNSTABLE when the transport gates pass, a replicate criterion "
    "fails, and the merged-50 improvement condition does not hold.",
    "All four outcomes are engineering decisions about numerics. None of them "
    "licenses any scientific, semantic, or interpretive claim.",
)
INCLUSION_RULES = (
    "Only prompts registered in data/jlens_saturation_prompts.jsonl corpus "
    "revision r2-60 are used.",
    "25A is role=fit in declared file order and is loaded from the Phase 0.5B "
    "checkpoint; it is never re-fitted.",
    "25B is role=reserve in declared file order and is provably disjoint from "
    "25A.",
    "Held-out apply prompts are role=heldout and are disjoint from both fits.",
    "Every fit uses source layers [6,13,20] and target layer 27.",
)
EXCLUSION_RULES = (
    "No behavioral candidate-bank prompt, parser fixture, evaluator-set item, "
    "or answer label may enter any fit or apply set.",
    "No direct 50-prompt fit is performed; the Phase 0.5B direct-subset merge "
    "control already demonstrated merge/direct equivalence "
    "(max_abs 2.384e-07 against a 1e-05 limit, relative Frobenius 4.862e-08 "
    "against a 1e-06 limit).",
    "The Phase 0.5B 25-prompt lens is not re-fitted under any circumstance.",
)
STOPPING_RULES = (
    "A stage that cannot finish inside the registered planning budget is "
    "recorded as skipped_time_guard and the run exports what it measured.",
    "A stop-classified memory measurement blocks further fitting.",
    "The application watchdog fires before the platform timeout so the "
    "artifact pack is always exported.",
    "A stage whose predecessor did not succeed is recorded blocked.",
)
RETRY_RULES = (
    "Official checkpoint/resume only; one job re-execution may resume from the "
    "newest manifest-complete Blob snapshot.",
    "No corpus, threshold, metric definition, or interpretation may change on "
    "retry.",
    "A retry may not re-fit 25A and may not introduce a direct 50-prompt fit.",
)


class DisjointValidationError(sat.SaturationValidationError):
    """A preregistered Phase 0.5C control was violated."""


class ExistingLensValidationError(DisjointValidationError):
    """The staged Phase 0.5B 25-prompt lens is not the registered lens."""


# ---------------------------------------------------------------------------
# reused deterministic helpers
# ---------------------------------------------------------------------------
canonical_json_bytes = base.canonical_json_bytes
sha256_bytes = base.sha256_bytes
sha256_file = base.sha256_file
sha256_text = sat.sha256_text
proxy_token_count = sat.proxy_token_count
relative_frobenius = sat.relative_frobenius
cosine_from_flat = sat.cosine_from_flat
vector_cosine = sat.vector_cosine
top_k_indices = sat.top_k_indices
top_k_overlap = sat.top_k_overlap
spearman_correlation = sat.spearman_correlation
mean = sat.mean
PureLensMath = sat.PureLensMath
TorchLensMath = sat.TorchLensMath
compare_lens_matrices = sat.compare_lens_matrices
compare_logit_vectors = sat.compare_logit_vectors
read_records = sat.read_records
empty_deviations = sat.empty_deviations
csv_bytes = sat.csv_bytes


def load_disjoint_corpus(path: str | Path) -> dict[str, Any]:
    """Load the amended 60-record corpus and refuse any other revision."""

    corpus = sat.load_saturation_corpus(path)
    if corpus["revision"] != CORPUS_REVISION:
        raise sat.CorpusValidationError(
            f"Phase 0.5C requires corpus revision {CORPUS_REVISION}, found "
            f"{corpus['revision']}"
        )
    return corpus


def build_disjoint_fit_plan(corpus: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the 25A / 25B / held-out prompt sets and the 25B shards."""

    by_id = {record["id"]: record for record in corpus["records"]}
    lens_a_ids = list(corpus["roles"]["fit"])
    lens_b_ids = list(corpus["roles"]["reserve"])
    heldout_ids = list(corpus["roles"]["heldout"])
    if len(lens_a_ids) != FIT_A_PROMPTS:
        raise DisjointValidationError("25A must be exactly 25 role=fit prompts")
    if len(lens_b_ids) != FIT_B_PROMPTS:
        raise DisjointValidationError("25B must be exactly 25 role=reserve prompts")
    if len(heldout_ids) != HELDOUT_PROMPTS:
        raise DisjointValidationError("the held-out set must be exactly 10 prompts")
    if sum(FIT_B_SHARDS) != FIT_B_PROMPTS:
        raise DisjointValidationError("25B shard accounting is invalid")

    def unit(name: str, ids: Sequence[str]) -> dict[str, Any]:
        return {
            "unit": name,
            "prompt_ids": list(ids),
            "prompt_count": len(ids),
            "prompt_order_sha256": base.canonical_jsonl_sha256(
                [{"id": item, "text": by_id[item]["text"]} for item in ids]
            ),
            "texts": [by_id[item]["text"] for item in ids],
        }

    shards = []
    start = 0
    for index, size in enumerate(FIT_B_SHARDS, 1):
        shards.append(unit(f"fit_25b_shard_{index}", lens_b_ids[start : start + size]))
        start += size

    set_a = set(lens_a_ids)
    set_b = set(lens_b_ids)
    set_h = set(heldout_ids)
    if set_a & set_b:
        raise DisjointValidationError("25A and 25B prompt sets must be disjoint")
    if (set_a | set_b) & set_h:
        raise DisjointValidationError("held-out prompts must be disjoint from both fits")
    if len(set_a | set_b | set_h) != FIT_A_PROMPTS + FIT_B_PROMPTS + HELDOUT_PROMPTS:
        raise DisjointValidationError("prompt accounting is not a clean partition")

    collected: list[str] = []
    for shard in shards:
        collected.extend(shard["prompt_ids"])
    if collected != lens_b_ids:
        raise DisjointValidationError("25B shards must partition 25B in file order")

    plan = {
        "lens_25a": unit("lens_25a", lens_a_ids),
        "lens_25b": unit("lens_25b", lens_b_ids),
        "lens_25b_shards": shards,
        "heldout": unit("heldout_apply", heldout_ids),
        "merge_weights": list(MERGE_WEIGHTS),
        "merged_prompt_count": MERGED_PROMPTS,
        "source_layers": list(SOURCE_LAYERS),
        "target_layer": TARGET_LAYER,
    }
    plan["lens_25a_matches_phase05b_order"] = (
        plan["lens_25a"]["prompt_order_sha256"] == EXISTING_PROMPT_ORDER_SHA256
    )
    return plan


def verify_existing_lens_file(
    path: str | Path,
    *,
    require_registered_digest: bool = True,
) -> dict[str, Any]:
    """Gate the staged 25A artifact on disk *before* anything deserialises it.

    This runs ahead of the load so a wrong or truncated object can never reach
    the backend. A mismatch raises, the stage is recorded ``failed``, and the
    run stops: re-fitting 25A is not an available fallback.
    """

    target = Path(path)
    if not target.is_file():
        raise ExistingLensValidationError(
            f"the staged Phase 0.5B lens is missing at {target.as_posix()}"
        )
    file_bytes = target.stat().st_size
    file_sha256 = sat.sha256_file(target)
    result = {
        "path": target.as_posix(),
        "file_bytes": file_bytes,
        "file_sha256": file_sha256,
        "registered_bytes": EXISTING_LENS_BYTES,
        "registered_sha256": EXISTING_LENS_SHA256,
        "bytes_match_registered": file_bytes == EXISTING_LENS_BYTES,
        "digest_matches_registered": file_sha256 == EXISTING_LENS_SHA256,
        "verified_before_load": True,
        "enforced": bool(require_registered_digest),
    }
    if require_registered_digest:
        if not result["bytes_match_registered"]:
            raise ExistingLensValidationError(
                f"the staged Phase 0.5B lens is {file_bytes} bytes, expected "
                f"{EXISTING_LENS_BYTES}; refusing to load and refusing to refit"
            )
        if not result["digest_matches_registered"]:
            raise ExistingLensValidationError(
                f"the staged Phase 0.5B lens SHA-256 {file_sha256} is not the "
                f"registered {EXISTING_LENS_SHA256}; refusing to load and "
                "refusing to refit"
            )
    return result


def validate_existing_lens(
    *,
    path: str | Path,
    metadata: Mapping[str, Any],
    file_sha256: str | None = None,
    file_bytes: int | None = None,
    require_registered_digest: bool = True,
    expected_d_model: int | None = MODEL_WIDTH,
) -> dict[str, Any]:
    """Check the staged Phase 0.5B lens before anything else uses it."""

    n_prompts = int(metadata.get("n_prompts", -1))
    source_layers = [int(layer) for layer in metadata.get("source_layers", [])]
    d_model = int(metadata.get("d_model", -1))
    if n_prompts != FIT_A_PROMPTS:
        raise ExistingLensValidationError(
            f"the staged lens reports {n_prompts} prompts, expected {FIT_A_PROMPTS}"
        )
    if source_layers != list(SOURCE_LAYERS):
        raise ExistingLensValidationError(
            f"the staged lens source layers {source_layers} are not "
            f"{list(SOURCE_LAYERS)}"
        )
    if expected_d_model is not None and d_model != int(expected_d_model):
        raise ExistingLensValidationError(
            f"the staged lens d_model {d_model} is not {int(expected_d_model)}"
        )
    if require_registered_digest:
        if file_sha256 is not None and file_sha256 != EXISTING_LENS_SHA256:
            raise ExistingLensValidationError(
                "the staged lens SHA-256 is not the registered Phase 0.5B lens"
            )
        if file_bytes is not None and file_bytes != EXISTING_LENS_BYTES:
            raise ExistingLensValidationError(
                "the staged lens byte count is not the registered Phase 0.5B lens"
            )
    return {
        "path": Path(path).as_posix(),
        "file_sha256": file_sha256,
        "file_bytes": file_bytes,
        "registered_sha256": EXISTING_LENS_SHA256,
        "registered_bytes": EXISTING_LENS_BYTES,
        "digest_matches_registered": file_sha256 == EXISTING_LENS_SHA256,
        "bytes_match_registered": file_bytes == EXISTING_LENS_BYTES,
        "n_prompts": n_prompts,
        "source_layers": source_layers,
        "d_model": d_model,
        "source_run_id": EXISTING_RUN_ID,
        "source_phase": EXISTING_PHASE,
        "source_container": EXISTING_BLOB_CONTAINER,
        "source_blob": EXISTING_LENS_BLOB,
        "source_storage_account": EXISTING_STORAGE_ACCOUNT,
        "refitted": False,
    }


def finite_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def merged_apply_improvement(
    pair_means: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Frozen definition of "merged-50 held-out apply stability improves".

    ``pair_means`` maps each of ``25A_vs_25B``/``25A_vs_50M``/``25B_vs_50M`` to
    the held-out means of ``heldout_topk_overlap`` and
    ``heldout_rank_correlation``. The merged lens improves when it agrees with
    each single fit by more than the two single fits agree with each other, by
    at least the registered margin.
    """

    result: dict[str, Any] = {
        "definition": (
            "mean(pair(25A,50M), pair(25B,50M)) - pair(25A,25B) >= margin, "
            "required simultaneously for heldout_topk_overlap (margin 0.02) "
            "and heldout_rank_correlation (margin 0.005)"
        ),
        "margins": {
            "heldout_topk_overlap": MERGED_IMPROVEMENT_TOPK_MARGIN,
            "heldout_rank_correlation": MERGED_IMPROVEMENT_RANK_MARGIN,
        },
        "interpretation": "technical_stability_only_no_semantic_claim",
    }
    margins: dict[str, Any] = {}
    satisfied: list[bool] = []
    for metric, margin in (
        ("heldout_topk_overlap", MERGED_IMPROVEMENT_TOPK_MARGIN),
        ("heldout_rank_correlation", MERGED_IMPROVEMENT_RANK_MARGIN),
    ):
        baseline = pair_means.get(PAIR_AB, {}).get(metric)
        left = pair_means.get(PAIR_AM, {}).get(metric)
        right = pair_means.get(PAIR_BM, {}).get(metric)
        if baseline is None or left is None or right is None:
            margins[metric] = None
            satisfied.append(False)
            result["improved"] = None
            result["margins_measured"] = margins
            result["not_applicable_reason"] = (
                "held-out apply means are missing for at least one lens pair"
            )
            return result
        observed = (float(left) + float(right)) / 2.0 - float(baseline)
        if not math.isfinite(observed):
            margins[metric] = observed
            result["improved"] = False
            result["margins_measured"] = margins
            return result
        margins[metric] = observed
        satisfied.append(observed >= margin)
    result["margins_measured"] = margins
    result["improved"] = bool(all(satisfied))
    return result


def evaluate_criterion(name: str, value: Any) -> dict[str, Any]:
    spec = CRITERIA.get(name)
    if spec is None:
        raise DisjointValidationError(f"unregistered criterion: {name}")
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
    merged_improvement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the preregistered Phase 0.5C engineering decision rules."""

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
    transport_failed = [name for name in failed if name in TRANSPORT_CRITERIA]
    replication_failed = [name for name in failed if name in REPLICATION_CRITERIA]
    improvement = dict(merged_improvement or {})
    improved = improvement.get("improved")

    if blocked_reason:
        status = "BLOCKED"
        decision = "INCONCLUSIVE"
        interpretation = (
            f"The run was blocked before a complete measurement: {blocked_reason}. "
            "No engineering conclusion about independent-fit variability is "
            "available."
        )
    elif transport_failed:
        status = "FAIL"
        decision = "FAILED"
        interpretation = (
            "At least one numerical transport gate failed "
            f"({', '.join(transport_failed)}). The fit, merge, serialization or "
            "apply path is not numerically sound; no further engineering "
            "conclusion follows and no scientific conclusion is licensed."
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
            "conclusion about independent-fit variability is drawn."
        )
    elif not replication_failed:
        status = "PASS"
        decision = "REPLICATE_STABLE"
        interpretation = (
            "The numerical transport gates passed and the two independently "
            "fitted 25-prompt lenses agree inside the registered engineering "
            "thresholds. This is an engineering numerics observation only and "
            "licenses no scientific claim."
        )
    elif improved is None:
        status = "INCONCLUSIVE"
        decision = "INCONCLUSIVE"
        interpretation = (
            "The replicate thresholds were not met and the merged-50 held-out "
            "apply improvement condition could not be evaluated "
            f"({improvement.get('not_applicable_reason', 'not measured')}). No "
            "engineering conclusion is drawn."
        )
        not_applicable = not_applicable + [
            {
                "criterion": "merged_apply_improvement",
                "reason": improvement.get(
                    "not_applicable_reason", "not measured"
                ),
            }
        ]
    elif improved:
        status = "COMPLETE"
        decision = "REPLICATE_IMPROVING"
        interpretation = (
            "The numerical transport gates passed, the two independent "
            f"25-prompt fits did not meet the registered replicate thresholds "
            f"({', '.join(replication_failed)}), and the merged 50-prompt lens "
            "met the preregistered held-out apply improvement margin against "
            "both single fits. This is an engineering numerics observation "
            "only and licenses no scientific claim."
        )
    else:
        status = "COMPLETE"
        decision = "REPLICATE_UNSTABLE"
        interpretation = (
            "The numerical transport gates passed, but the two independent "
            f"25-prompt fits disagree beyond the registered thresholds "
            f"({', '.join(replication_failed)}) and the merged 50-prompt lens "
            "did not meet the preregistered held-out apply improvement margin. "
            "This is an engineering numerics observation only and licenses no "
            "scientific claim."
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
        "merged_apply_improvement": improvement,
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
        "registered_metrics": list(REGISTERED_METRICS),
        "supporting_observations": list(SUPPORTING_OBSERVATIONS),
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
            "merged_apply_improvement": {
                "definition": (
                    "mean(pair(25A,50M), pair(25B,50M)) - pair(25A,25B) >= "
                    "margin, required simultaneously for both statistics"
                ),
                "heldout_topk_overlap_margin": MERGED_IMPROVEMENT_TOPK_MARGIN,
                "heldout_rank_correlation_margin": MERGED_IMPROVEMENT_RANK_MARGIN,
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
        "reused_controls": dict(EXISTING_MERGE_CONTROL),
        "reused_lens_25a": dict(EXISTING_LENS_PROVENANCE),
        "scientific_claim_boundary": SCIENTIFIC_CLAIM_BOUNDARY,
    }
    missing = [field for field in PROTOCOL_SNAPSHOT_FIELDS if field not in snapshot]
    if missing:
        raise sat.ArtifactValidationError(f"protocol snapshot is missing {missing}")
    return snapshot


def default_sample_size() -> dict[str, Any]:
    return {
        "corpus_prompts": CORPUS_TOTAL,
        "corpus_revision": CORPUS_REVISION,
        "lens_25a_prompts": FIT_A_PROMPTS,
        "lens_25b_prompts": FIT_B_PROMPTS,
        "lens_25b_shards": list(FIT_B_SHARDS),
        "merged_prompts": MERGED_PROMPTS,
        "merge_weights": list(MERGE_WEIGHTS),
        "heldout_prompts": HELDOUT_PROMPTS,
        "apply_pairs": [name for name, _left, _right in APPLY_PAIRS],
        "source_layers": list(SOURCE_LAYERS),
        "target_layer": TARGET_LAYER,
        "top_k": TOP_K,
        "top_k_secondary": TOP_K_SECONDARY,
    }


def protocol_hash() -> str:
    """The registered protocol hash: sha256 of the canonical snapshot bytes.

    This is the same construction Phase 0.5B used, so the value equals the
    SHA-256 of ``01_protocol_snapshot.json`` in the exported artifact pack.
    """

    return sha256_bytes(
        canonical_json_bytes(build_protocol_snapshot(sample_size=default_sample_size()))
    )


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
        raise sat.ArtifactValidationError(f"stage manifest is missing {missing}")
    return manifest


def make_record(**kwargs: Any) -> dict[str, Any]:
    return sat.make_record(phase=PHASE, track=TRACK, conditions=CONDITIONS, **kwargs)


def make_metric_row(**kwargs: Any) -> dict[str, str]:
    return sat.make_metric_row(phase=PHASE, track=TRACK, **kwargs)


def make_paper_row(**kwargs: Any) -> dict[str, str]:
    return sat.make_paper_row(phase=PHASE, track=TRACK, **kwargs)


def make_figure_row(**kwargs: Any) -> dict[str, str]:
    return sat.make_figure_row(phase=PHASE, track=TRACK, **kwargs)


def not_applicable_record(run_id: str, reason: str) -> dict[str, Any]:
    return sat.not_applicable_record(run_id, reason, phase=PHASE, track=TRACK)


def not_applicable_metric_row(run_id: str, reason: str) -> dict[str, str]:
    return sat.not_applicable_metric_row(run_id, reason, phase=PHASE, track=TRACK)


def not_applicable_paper_row(run_id: str, reason: str) -> dict[str, str]:
    return sat.not_applicable_paper_row(run_id, reason, phase=PHASE, track=TRACK)


def not_applicable_figure_row(run_id: str, reason: str) -> dict[str, str]:
    return sat.not_applicable_figure_row(run_id, reason, phase=PHASE, track=TRACK)


LIMITATIONS = (
    "One GPU, one model, one revision, one prompt corpus, one pair of fits.",
    "The two fits are disjoint prompt samples of size 25 from the same "
    "corpus; two samples give one difference measurement, not a distribution.",
    "25A was fitted in a previous run and is loaded from its fp32 checkpoint; "
    "this run re-verifies its metadata and digest but does not re-fit it.",
    "No direct 50-prompt fit is performed, so the merged lens is compared "
    "against its own inputs and against the Phase 0.5B merge control only.",
    "Held-out apply uses 10 generic prompts at the final position only.",
    "No lens-quality, calibration, or semantic validation was attempted and "
    "none of these numbers supports any scientific claim.",
)
PAPER_RELEVANCE = (
    "Supplies the independent-fit estimator variability row: how far two "
    "same-size J-lenses fitted on disjoint prompt samples differ numerically.",
    "Supplies the engineering cost row for a second 25-prompt fit: wall-clock "
    "per prompt, peak GPU memory, checkpoint and lens sizes.",
    "Supplies no behavioral, semantic, or workspace result of any kind.",
)


def render_summary_markdown(context: Mapping[str, Any]) -> str:
    """Render 05_summary.md through the shared renderer with 0.5C text."""

    payload = dict(context)
    payload.setdefault("phase", PHASE)
    payload.setdefault("track", TRACK)
    payload.setdefault("stage_names", STAGES)
    payload.setdefault("objective", OBJECTIVE)
    payload.setdefault("hypothesis", HYPOTHESIS)
    payload.setdefault("scope", SCOPE)
    payload.setdefault("out_of_scope", OUT_OF_SCOPE)
    payload.setdefault("claim_boundary", SCIENTIFIC_CLAIM_BOUNDARY)
    payload.setdefault("prohibited_interpretations", PROHIBITED_INTERPRETATIONS)
    payload.setdefault("limitations", LIMITATIONS)
    payload.setdefault("paper_relevance", PAPER_RELEVANCE)
    payload.setdefault("next_gate", NEXT_GATE)
    return sat.render_summary_markdown(payload)


def write_artifact_pack(pack_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    return sat.write_artifact_pack(
        pack_dir,
        phase=PHASE,
        track=TRACK,
        schema_version=SCHEMA_VERSION,
        **kwargs,
    )


def validate_artifact_pack(pack_dir: str | Path) -> dict[str, Any]:
    return sat.validate_artifact_pack(
        pack_dir,
        phase=PHASE,
        track=TRACK,
        decisions=DECISIONS,
        decision_statuses=DECISION_STATUSES,
        summary_sections=SUMMARY_SECTIONS,
    )


def rebuild_artifact_manifest(
    pack_dir: str | Path, *, generated_at_utc: str | None = None
) -> dict[str, Any]:
    """Regenerate artifact_manifest.json last over an existing pack directory."""

    directory = Path(pack_dir)
    manifest_path = directory / MANIFEST_FILENAME
    previous: dict[str, Any] = {}
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = []
    for name in sat.ARTIFACT_FILENAMES:
        if name == MANIFEST_FILENAME:
            continue
        path = directory / name
        if not path.is_file():
            raise sat.ArtifactValidationError(f"artifact {name} is missing")
        artifacts.append(
            {
                "path": name,
                "bytes": path.stat().st_size,
                "sha256": base.sha256_file(path),
            }
        )
    manifest = {
        "schema_version": f"{SCHEMA_VERSION}-artifact-manifest",
        "phase": PHASE,
        "track": TRACK,
        "run_id": str(previous.get("run_id", directory.name)),
        "generated_at_utc": (
            generated_at_utc
            if generated_at_utc is not None
            else str(previous.get("generated_at_utc", ""))
        ),
        "manifest_written_last": True,
        "artifacts": artifacts,
        "manifest_order": [entry["path"] for entry in artifacts],
    }
    manifest_path.write_bytes(base.canonical_json_bytes(manifest))
    return manifest


PRERUN_REASON = (
    "pre-run scaffold: the Phase 0.5C container job has not executed, so no "
    "measured value exists yet"
)


def build_prerun_scaffold(pack_dir: str | Path) -> dict[str, Any]:
    """Write the deterministic pre-run artifact pack skeleton (deliverable D4).

    Every registered file exists. Files that cannot carry a measured value
    before the job runs carry ``status = not_applicable`` and a ``reason``.
    ``artifact_manifest.json`` is written last. Re-running this is idempotent
    and reproduces the pack byte for byte.
    """

    directory = Path(pack_dir)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = build_protocol_snapshot(sample_size=default_sample_size())
    record = {
        "record_id": "not-applicable",
        "run_id": "PENDING",
        "phase": PHASE,
        "track": TRACK,
        "source_item_id": "not_applicable",
        "condition": "not_applicable",
        "status": "not_applicable",
        "input_hash": base.sha256_bytes(PRERUN_REASON.encode("utf-8")),
        "output_hash": base.sha256_bytes(
            base.canonical_json_bytes({"reason": PRERUN_REASON})
        ),
        "evaluation": {"status": "not_applicable", "reason": PRERUN_REASON},
    }
    metric_row = {column: "" for column in METRICS_COLUMNS}
    metric_row.update(
        {
            "run_id": "PENDING",
            "phase": PHASE,
            "track": TRACK,
            "metric": "not_applicable",
            "stratum": "all",
            "condition": "not_applicable",
            "not_applicable_reason": PRERUN_REASON,
        }
    )
    paper_row = {column: "" for column in PAPER_TABLE_COLUMNS}
    paper_row.update(
        {
            "run_id": "PENDING",
            "phase": PHASE,
            "track": TRACK,
            "row_label": "not_applicable",
            "condition": "not_applicable",
            "metric": "not_applicable",
            "status": "not_applicable",
            "not_applicable_reason": PRERUN_REASON,
        }
    )
    figure_row = {column: "" for column in FIGURE_DATA_COLUMNS}
    figure_row.update(
        {
            "run_id": "PENDING",
            "phase": PHASE,
            "track": TRACK,
            "figure_id": "not_applicable",
            "series": "not_applicable",
            "x_label": "not_applicable",
            "status": "not_applicable",
            "not_applicable_reason": PRERUN_REASON,
        }
    )
    decision = evaluate_decision({}, blocked_reason=PRERUN_REASON)
    stage_manifest = build_stage_manifest(
        run_id="PENDING",
        status=decision["status"],
        start_time_utc="",
        end_time_utc="",
        code_commit="PENDING",
        image_digest=None,
        hardware={},
        inputs={
            "scaffold": True,
            "reason": PRERUN_REASON,
            "corpus_revision": CORPUS_REVISION,
            "existing_lens_blob": EXISTING_LENS_BLOB,
            "existing_lens_container": EXISTING_BLOB_CONTAINER,
            "existing_lens_storage_account": EXISTING_STORAGE_ACCOUNT,
            "existing_lens_expected_sha256": EXISTING_LENS_SHA256,
            "existing_lens_expected_bytes": EXISTING_LENS_BYTES,
            "existing_lens_refitted": False,
            "direct_50_fit_performed": False,
        },
        protocol_hash=protocol_hash(),
        subagents=[
            {
                "name": "agent-a-track-a1",
                "role": "phase 0.5C disjoint-replication implementation",
                "model_access": "none",
            }
        ],
    )
    stage_manifest["stages"] = {
        name: {
            "status": "not_run",
            "duration_seconds": None,
            "started_at_utc": None,
            "finished_at_utc": None,
        }
        for name in STAGES
    }
    stage_manifest["stage_details"] = {name: {} for name in STAGES}
    stage_manifest["errors"] = []
    summary = render_summary_markdown(
        {
            "run_id": "PENDING",
            "mode": "pre_run_scaffold",
            "dim_batch": DEFAULT_DIM_BATCH,
            "corpus_path": "data/jlens_saturation_prompts.jsonl",
            "corpus_file_sha256": sat.CORPUS_REVISIONS[CORPUS_REVISION][
                "file_sha256"
            ],
            "corpus_canonical_sha256": "",
            "code_commit": "PENDING",
            "image_digest": None,
            "extra_provenance": [
                f"Corpus revision: `{CORPUS_REVISION}`",
                f"Existing 25A lens: `{EXISTING_BLOB_CONTAINER}/"
                f"{EXISTING_LENS_BLOB}` from run `{EXISTING_RUN_ID}`; "
                "re-fitted: no",
                "Direct 50-prompt fit: not performed; the Phase 0.5B "
                "direct-subset merge control is reused",
                PRERUN_REASON,
            ],
            "stages": {},
            "decision": decision,
            "deviations": {
                "deviations": [],
                "unregistered_changes": [],
                "effect_on_interpretation": "none",
            },
            "errors": [],
            "result_notes": [PRERUN_REASON],
        }
    )
    result = write_artifact_pack(
        directory,
        run_id="PENDING",
        stage_manifest=stage_manifest,
        protocol_snapshot=snapshot,
        records=[record],
        metrics=[metric_row],
        decision=decision,
        summary_markdown=summary,
        paper_rows=[paper_row],
        figure_rows=[figure_row],
        deviations={
            "deviations": [],
            "unregistered_changes": [],
            "effect_on_interpretation": "none",
        },
        generated_at_utc="",
    )
    validate_artifact_pack(directory)
    return result


class DisjointSelfTestBackend(sat.SelfTestBackend):
    """Torch-free backend that can also *load* a previously saved lens.

    Phase 0.5C never re-fits 25A, so the self-test needs a load path. The
    numbers this backend produces are synthetic and every run that uses it is
    forced to INCONCLUSIVE.
    """

    name = "self_test_disjoint"

    def load_lens(self, path: str | Path) -> sat.SelfTestLens:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return sat.SelfTestLens.from_payload(payload)
