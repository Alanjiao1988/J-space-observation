"""Preregistered, model-free helpers for the all-45 semantic parser audit."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .no_cot import (
    construct_prefill_answer_prompt,
    construct_r1_style_thinking_prompt,
    construct_visible_cot_prompt,
)
from .phase1_branches import get_phase1_branch_metadata
from .prompt_sets import ArithmeticPromptSet
from .record_audit import (
    AuditInputError,
    audit_field_consistency,
    audit_membership,
    audit_pairing,
    audit_transformation_consistency,
    expected_record_keys,
    recompute_branch_classifications,
    recompute_metric_rows,
    record_key,
    sha256_bytes,
    validate_audit_prefixes,
)


PROTOCOL_VERSION = "v1"
SEMANTIC_AUDIT_SCHEMA_VERSION = "phase1-all45-semantic-audit/v1"
STAGE1_SCHEMA_VERSION = "phase1-all45-semantic-review-stage1/v1"
STAGE2_SCHEMA_VERSION = "phase1-all45-semantic-review-stage2/v1"
UNBLINDED_SCHEMA_VERSION = "phase1-all45-semantic-review-unblinded/v1"
JUDGMENT_SCHEMA_VERSION = "phase1-all45-semantic-judgment/v1"
STAGE1_JUDGMENT_SCHEMA_VERSION = "phase1-all45-semantic-judgment-stage1/v1"
STAGE2_JUDGMENT_SCHEMA_VERSION = "phase1-all45-semantic-judgment-stage2/v1"
ARBITRATION_JUDGMENT_SCHEMA_VERSION = (
    "phase1-all45-semantic-judgment-arbitration/v1"
)
SUBMISSION_SEAL_SCHEMA_VERSION = "phase1-all45-semantic-submission-seal/v1"
RELEASE_MANIFEST_SCHEMA_VERSION = "phase1-all45-semantic-release-manifest/v1"
ARBITRATION_PACKET_SCHEMA_VERSION = "phase1-all45-arbitration-packet/v1"
FINAL_ADJUDICATION_SCHEMA_VERSION = "phase1-all45-final-adjudication/v1"

EXPERIMENTAL_TARGET_MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
REVIEWER_MODEL_ID = "gpt-5.6-sol"
REVIEWER_REASONING_EFFORT = "max"
SOURCE_WRITER_COMMIT = "359643b7b5eb8f95c13cca2e60fa753df8701282"
EXPECTED_RECORD_COUNT = 45
FROZEN_SHUFFLE_SEED = 20260711
DEFAULT_SHUFFLE_SEED = FROZEN_SHUFFLE_SEED
SHUFFLE_HASH_DOMAIN = b"jspace-semantic-audit/shuffle/v1\0"
SHUFFLE_ALGORITHM = (
    "sha256(domain || ascii(seed) || NUL || canonical_pairing_key_json); "
    "sort by (hash,key_json)"
)
PROTOCOL_BUNDLE_HASH_DOMAIN = b"jspace-semantic-audit/protocol-bundle/v1\0"
PROTOCOL_COMMIT_ENV = "JSPACE_SEMANTIC_PROTOCOL_COMMIT"
BUILD_ATTESTATION_SCHEMA_VERSION = "phase1-semantic-audit-build-provenance/v1"
BUILD_ATTESTATION_FILENAME = ".semantic_audit_build_provenance.json"
BAKED_BUILD_ATTESTATION_PATH = Path(
    "/opt/jspace/semantic-audit-build-provenance.json"
)
PROTOCOL_RUNTIME_FILES = (
    "Dockerfile",
    "docs/phase1_semantic_review_protocol.md",
    "infra/azure/scripts/00_check_prereqs.ps1",
    "infra/azure/scripts/00_check_prereqs.sh",
    "infra/azure/scripts/01_build_and_push_image.sh",
    "infra/azure/scripts/02_run_phase0_5.sh",
    "infra/azure/scripts/03_run_phase1.sh",
    "infra/azure/scripts/04_run_phase1_pilot.sh",
    "infra/azure/scripts/05_run_job_ghcr.sh",
    "infra/azure/scripts/06_run_job_acr_mi.sh",
    "requirements.txt",
    "scripts/audit_phase1_blob_run.py",
    "scripts/blob_export_smoke.py",
    "scripts/export_phase1_semantic_review_pack.py",
    "scripts/finalize_phase1_semantic_audit.py",
    "scripts/prepare_semantic_audit_build_context.py",
    "src/jspace_observation/__init__.py",
    "src/jspace_observation/blob_export.py",
    "src/jspace_observation/config.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/jlens_utils.py",
    "src/jspace_observation/model_loader.py",
    "src/jspace_observation/no_cot.py",
    "src/jspace_observation/phase1_branches.py",
    "src/jspace_observation/postprocess.py",
    "src/jspace_observation/prompt_sets.py",
    "src/jspace_observation/record_audit.py",
    "src/jspace_observation/run_logging.py",
    "src/jspace_observation/semantic_audit.py",
    "src/jspace_observation/stats.py",
)
PROTOCOL_BEHAVIOR_ROOTS = (
    "src",
    "scripts",
    "infra/azure/scripts",
    "Dockerfile",
    "requirements.txt",
    "docs/phase1_semantic_review_protocol.md",
)

SOURCE_ARTIFACT_HASHES = {
    "phase1_generations.jsonl": (
        "b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0"
    ),
    "phase1_eval_records.jsonl": (
        "57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b"
    ),
}
VERIFIED_SOURCE_EVIDENCE_MODE = "verified_source_bytes"
SYNTHETIC_TEST_SOURCE_MODE = "synthetic_test_only"

STAGE1_PACKET_FILENAME = "all45_review_packet_blinded.jsonl"
STAGE2_PACKET_FILENAME = "all45_review_packet_stage2.jsonl"
RESTRICTED_PACKET_FILENAME = "all45_review_packet_unblinded.jsonl"
PACKET_FILENAMES = (STAGE1_PACKET_FILENAME, STAGE2_PACKET_FILENAME)
RELEASE_RESERVATION_FILENAME = ".semantic_audit_release_reservation.json"
RELEASE_RESERVATION_SCHEMA_VERSION = (
    "phase1-all45-semantic-release-reservation/v1"
)
STAGE1_RELEASE_MANIFEST_FILENAME = "all45_stage1_release_manifest.json"
STAGE2_RELEASE_MANIFEST_FILENAME = "all45_stage2_release_manifest.json"
RELEASE_MANIFEST_FILENAMES = {
    "stage1": STAGE1_RELEASE_MANIFEST_FILENAME,
    "stage2": STAGE2_RELEASE_MANIFEST_FILENAME,
}
RELEASE_MANIFEST_FIELDS = frozenset(
    {
        "release_manifest_schema_version",
        "release_stage",
        "release_complete",
        "manifest_uploaded_last",
        "audit_schema_version",
        "protocol_version",
        "protocol_path",
        "protocol_commit",
        "protocol_bundle_sha256",
        "protocol_provenance",
        "experimental_target_model_id",
        "reviewer",
        "source_writer_commit",
        "source_prefix",
        "output_prefix",
        "source_artifacts",
        "source_immutability",
        "source_evidence_mode",
        "source_evidence_sha256",
        "expected_record_count",
        "task_family",
        "depths",
        "registered_conditions",
        "shuffle",
        "packet_files",
        "reservation",
        "stage1_gate",
        "model_inference_performed",
        "new_observations_generated",
        "new_behavioral_observations_generated",
        "source_artifacts_modified",
        "official_stored_metrics_or_classifications_modified",
        "mandatory_boundary",
    }
)
PROTOCOL_PROVENANCE_FIELDS = frozenset(
    {
        "protocol_commit",
        "protocol_bundle_sha256",
        "bundle_hash_domain",
        "runtime_files",
        "file_sha256",
        "attestation_schema_version",
        "generated_from_clean_git",
        "verification_mode",
        "git_checks_performed",
        "verified",
    }
)
PACKET_METADATA_FIELDS = frozenset(
    {"sha256", "record_count", "canonical_json"}
)
STAGE1_GATE_FIELDS = frozenset(
    {
        "stage1_packet_sha256",
        "stage1_release_manifest_sha256",
        "complete",
        "reviewers",
    }
)
STAGE1_GATE_REVIEWER_FIELDS = frozenset(
    {
        "reviewer_id",
        "reviewer_model_id",
        "reviewer_reasoning_effort",
        "submission_sha256",
        "seal_sha256",
    }
)
REVIEW_MANIFEST_FILENAME = "all45_review_manifest.json"
FINAL_MACHINE_FILENAMES = (
    REVIEW_MANIFEST_FILENAME,
    "all45_reviewer_a.jsonl",
    "all45_reviewer_b.jsonl",
    "all45_arbitration.jsonl",
    "all45_final_semantic_adjudication.jsonl",
    "all45_ambiguity_confusion_matrix.json",
    "all45_correctness_confusion_matrix.json",
    "all45_semantic_audit_metrics.csv",
    "all45_material_impact.json",
)

MANDATORY_BOUNDARY_TEXT = (
    "The all-45 semantic audit is a read-only, post hoc review of already-stored "
    "outputs from deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B. Reviewing 45 records "
    "adds no behavioral observations, does not make behavioral n=45, and leaves "
    "every experimental cell at n=3, the registered minimum only—not evidence of "
    "stability, robustness, reliability, or generalizability. Evaluator "
    "consistency establishes reproducibility of stored parser/metric/classification "
    "logic, not semantic correctness. Judgments, agreement, and arbitration by "
    "reviewer gpt-5.6-sol with reasoning effort max are audit opinion, not human "
    "ground truth. Official stored metrics/classifications remain unchanged. "
    "Reviewer-derived quantities are labeled audit-only semantic alternative "
    "estimates: post hoc, noncanonical sensitivity estimates, never corrected, "
    "replacement, true, or official metrics. stopped_intervention remains "
    "intervention-controlled, not spontaneous no-CoT. postprocessed_utility remains "
    "answer-recovery utility, not raw no-CoT. Parser or answer-extraction "
    "disagreement is a surface-measurement issue and provides no evidence of hidden "
    "reasoning, internal workspace, invisible CoT, genuine no-CoT, or J-space."
)

SEMANTIC_CATEGORIES = (
    "unambiguous_single_answer",
    "true_multiple_candidate_ambiguity",
    "no_answer",
    "incomplete_or_truncated",
    "malformed_but_answer_recoverable",
    "malformed_no_reliable_answer",
    "review_inconclusive",
)
ANSWER_PRESENCE_LABELS = (
    "answer_present",
    "ambiguous",
    "no_answer",
    "inconclusive",
)
ANSWER_STATUS_LABELS = (
    "correct",
    "incorrect",
    "ambiguous",
    "no_answer",
    "inconclusive",
)
ISSUE_TAGS = (
    "explicit_answer_marker_missed",
    "boxed_answer_missed",
    "last_number_selection_risk",
    "multiple_numeric_candidates",
    "intermediate_number_selected",
    "reasoning_continuation_after_answer",
    "incomplete_or_truncated_output",
    "placeholder_output",
    "malformed_output",
    "answer_present_but_parser_invalid",
    "parser_selected_wrong_span",
    "parser_flagged_benign_multiple_numbers",
    "no_reliable_answer",
    "other",
)
CONFIDENCE_LABELS = ("low", "medium", "high")
CONFIDENCE_SCORES = {"low": 1, "medium": 2, "high": 3}
DERIVED_PARSER_LABELS = (
    "correct_flag",
    "parser_overflag",
    "parser_underflag",
    "correct_non_flag",
    "not_assessable",
)
PARSED_ANSWER_CONSISTENCY_CATEGORIES = (
    "stored_matches_semantic_best",
    "stored_differs_from_semantic_best",
    "stored_answer_semantic_no_answer",
    "stored_no_answer_semantic_answer",
    "semantic_ambiguous",
    "inconclusive",
)
STORED_CORRECTNESS_STATES = ("true", "false", "null", "missing", "invalid")

STAGE1_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "review_id",
        "experimental_target_model_id",
        "task",
        "outputs",
        "intervention",
        "generation_config",
    }
)
STAGE1_TASK_FIELDS = frozenset(
    {"task_family", "depth", "condition", "task_id", "question", "parse_type"}
)
STAGE1_OUTPUT_FIELDS = frozenset(
    {
        "raw_output",
        "stopped_output",
        "postprocessed_output",
        "eval_output_used",
        "eval_output",
    }
)
STAGE1_INTERVENTION_FIELDS = frozenset(
    {
        "stop_control_enabled",
        "stop_triggered",
        "stop_string",
        "stop_reason",
        "stop_mode",
        "postprocessing_applied",
        "postprocessing_strategy",
        "postprocessing_reason",
    }
)
STAGE1_GENERATION_CONFIG_FIELDS = frozenset(
    {
        "max_new_tokens",
        "temperature",
        "top_p",
        "do_sample",
        "decoding_profile",
    }
)
STAGE2_FIELDS = frozenset(
    {
        "schema_version",
        "review_id",
        "experimental_target_model_id",
        "registered_reference_answer",
    }
)
UNBLINDED_FIELDS = frozenset(
    {
        "schema_version",
        "review_id",
        "experimental_target_model_id",
        "pairing_key",
        "stage1_record",
        "registered_reference_answer",
        "stored_generation_fields",
        "stored_evaluation_fields",
    }
)
PAIRING_KEY_PACKET_FIELDS = frozenset(
    {"model_name", "task_family", "depth", "condition", "task_id"}
)

STORED_GENERATION_ALLOWLIST = (
    "no_cot_applicable",
    "no_cot_validity",
    "generation_time_s",
    "phase1_branch",
    "stop_string",
)
STORED_EVALUATION_ALLOWLIST = (
    "parsed_answer",
    "parse_valid",
    "parse_ambiguous",
    "parse_strategy",
    "candidate_answers",
    "parse_error_type",
    "answer_format_warning",
    "correctness",
    "error_type",
    "raw_correctness",
    "eval_correctness",
    "stopped_correctness",
    "postprocessed_correctness",
    "raw_parse_valid",
    "raw_parsed_answer",
    "stopped_no_cot_valid",
    "raw_no_cot_valid",
    "postprocessed_no_cot_valid",
    "postprocessed_answer_like",
    "stop_warning",
    "postprocessing_warning",
)

_FROZEN_ARITHMETIC_REGISTRY = (
    {
        "id": "arith_1op_001",
        "task_family": "arithmetic",
        "depth": 1,
        "prompt_base": "What is 7 + 5?",
        "expected_answer": "12",
        "parse_type": "numeric",
    },
    {
        "id": "arith_1op_002",
        "task_family": "arithmetic",
        "depth": 1,
        "prompt_base": "What is 23 - 8?",
        "expected_answer": "15",
        "parse_type": "numeric",
    },
    {
        "id": "arith_1op_003",
        "task_family": "arithmetic",
        "depth": 1,
        "prompt_base": "What is 6 * 4?",
        "expected_answer": "24",
        "parse_type": "numeric",
    },
    {
        "id": "arith_2op_001",
        "task_family": "arithmetic",
        "depth": 2,
        "prompt_base": "What is (5 + 3) * 2?",
        "expected_answer": "16",
        "parse_type": "numeric",
    },
    {
        "id": "arith_2op_002",
        "task_family": "arithmetic",
        "depth": 2,
        "prompt_base": "What is 20 - 7 + 3?",
        "expected_answer": "16",
        "parse_type": "numeric",
    },
    {
        "id": "arith_2op_003",
        "task_family": "arithmetic",
        "depth": 2,
        "prompt_base": "What is (10 + 2) / 3?",
        "expected_answer": "4",
        "parse_type": "numeric",
    },
    {
        "id": "arith_3op_001",
        "task_family": "arithmetic",
        "depth": 3,
        "prompt_base": "What is ((8 + 4) * 2) - 6?",
        "expected_answer": "18",
        "parse_type": "numeric",
    },
    {
        "id": "arith_3op_002",
        "task_family": "arithmetic",
        "depth": 3,
        "prompt_base": "What is (10 + 5) * 2 + 4?",
        "expected_answer": "34",
        "parse_type": "numeric",
    },
    {
        "id": "arith_3op_003",
        "task_family": "arithmetic",
        "depth": 3,
        "prompt_base": "What is ((9 - 3) * 4) + 2?",
        "expected_answer": "26",
        "parse_type": "numeric",
    },
)

FROZEN_RUBRIC = {
    "protocol_version": PROTOCOL_VERSION,
    "semantic_categories": list(SEMANTIC_CATEGORIES),
    "semantic_ambiguity_positive": "true_multiple_candidate_ambiguity",
    "answer_presence": list(ANSWER_PRESENCE_LABELS),
    "answer_status": list(ANSWER_STATUS_LABELS),
    "issue_tags": list(ISSUE_TAGS),
    "confidence": {
        "high": "Clear evidence supports the judgment with no material interpretive doubt.",
        "medium": "The judgment is more likely than alternatives but has a meaningful caveat.",
        "low": "Material uncertainty remains; arbitration should not treat the judgment as settled.",
    },
    "best_answer": (
        "A finite numeric answer normalized with Decimal, or null. Commas, arithmetic "
        "expressions, repairs, and tolerance-based comparisons are prohibited."
    ),
    "review_target": (
        "Judge only the selected eval_output. Raw output shown beside stopped or "
        "postprocessed output is context and is not independently rescored."
    ),
    "boundary": MANDATORY_BOUNDARY_TEXT,
}

_MISSING = object()
_DECIMAL_PATTERN = re.compile(
    r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?\Z"
)
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_REVIEW_ID_PATTERN = re.compile(r"R\d{3}\Z")
_BUILD_ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "bundle_hash_domain",
        "runtime_files",
        "file_sha256",
        "generated_from_clean_git",
    }
)


class SemanticAuditError(AuditInputError):
    """Raised when semantic-audit input violates the preregistered contract."""


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SemanticAuditError(f"non-finite JSON number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SemanticAuditError(f"non-string JSON key at {path}")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise SemanticAuditError(
        f"unsupported JSON value type at {path}: {type(value).__name__}"
    )


def canonical_json_text(value: Any) -> str:
    """Serialize one value as compact, sorted-key ASCII JSON."""
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SemanticAuditError(f"value is not canonical-JSON serializable: {exc}") from exc


def canonical_json_bytes(value: Any, *, final_newline: bool = True) -> bytes:
    suffix = "\n" if final_newline else ""
    return (canonical_json_text(value) + suffix).encode("ascii")


def canonical_jsonl_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    """Serialize records one per physical line with a final LF."""
    if not records:
        return b""
    return (
        "\n".join(canonical_json_text(dict(record)) for record in records) + "\n"
    ).encode("ascii")


def _validate_commit(commit: str, name: str) -> str:
    if (
        not isinstance(commit, str)
        or not _COMMIT_PATTERN.fullmatch(commit)
        or commit == "0" * 40
    ):
        raise SemanticAuditError(
            f"{name} must be a nonzero lowercase 40-character Git commit"
        )
    return commit


def _validate_sha256(digest: str, name: str) -> str:
    if (
        not isinstance(digest, str)
        or not _SHA256_PATTERN.fullmatch(digest)
        or digest == "0" * 64
    ):
        raise SemanticAuditError(f"{name} must be a nonzero lowercase SHA-256 digest")
    return digest


def protocol_bundle_sha256(project_root: str | Path) -> str:
    """Hash the exact frozen protocol/tooling byte bundle without newline rewriting."""
    root = Path(project_root).resolve()
    digest = hashlib.sha256()
    digest.update(PROTOCOL_BUNDLE_HASH_DOMAIN)
    for relative in PROTOCOL_RUNTIME_FILES:
        path = root.joinpath(*relative.split("/"))
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise SemanticAuditError(
                f"protocol runtime file is unavailable: {relative}"
            ) from exc
        encoded_path = relative.encode("ascii")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _protocol_file_sha256(project_root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative in PROTOCOL_RUNTIME_FILES:
        try:
            data = project_root.joinpath(*relative.split("/")).read_bytes()
        except OSError as exc:
            raise SemanticAuditError(
                f"protocol runtime file is unavailable: {relative}"
            ) from exc
        digests[relative] = hashlib.sha256(data).hexdigest()
    return dict(sorted(digests.items()))


def _listed_behavior_files(project_root: Path) -> set[str]:
    files: set[str] = set()
    for relative_root in ("src", "scripts", "infra/azure/scripts"):
        directory = project_root.joinpath(*relative_root.split("/"))
        if not directory.is_dir():
            raise SemanticAuditError(
                f"protocol behavior root is unavailable: {relative_root}"
            )
        for path in directory.rglob("*"):
            if path.is_file():
                files.add(path.relative_to(project_root).as_posix())
    for relative in (
        "Dockerfile",
        "requirements.txt",
        "docs/phase1_semantic_review_protocol.md",
    ):
        if project_root.joinpath(*relative.split("/")).is_file():
            files.add(relative)
    return files


def _run_git(
    project_root: Path,
    arguments: Sequence[str],
    *,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        capture_output=True,
        text=text,
        check=False,
    )


def _git_lines(project_root: Path, arguments: Sequence[str], label: str) -> list[str]:
    result = _run_git(project_root, arguments)
    if result.returncode != 0:
        raise SemanticAuditError(f"{label} failed")
    return result.stdout.splitlines()


def _verified_provenance_record(
    *,
    commit: str,
    bundle: str,
    file_sha256: Mapping[str, str],
    verification_mode: str,
    git_checks_performed: bool,
) -> dict[str, Any]:
    return {
        "protocol_commit": commit,
        "protocol_bundle_sha256": bundle,
        "bundle_hash_domain": PROTOCOL_BUNDLE_HASH_DOMAIN.decode("ascii").rstrip(
            "\0"
        ),
        "runtime_files": list(PROTOCOL_RUNTIME_FILES),
        "file_sha256": dict(sorted(file_sha256.items())),
        "attestation_schema_version": BUILD_ATTESTATION_SCHEMA_VERSION,
        "generated_from_clean_git": True,
        "verification_mode": verification_mode,
        "git_checks_performed": git_checks_performed,
        "verified": True,
    }


def _validate_baked_build_attestation(
    project_root: Path, attestation_path: Path
) -> dict[str, Any]:
    try:
        data = attestation_path.read_bytes()
    except OSError as exc:
        raise SemanticAuditError("baked build attestation is missing") from exc
    attestation = parse_json_object_strict(data, "baked build attestation")
    if canonical_json_bytes(attestation) != data:
        raise SemanticAuditError("baked build attestation is not canonical JSON")
    if set(attestation) != set(_BUILD_ATTESTATION_FIELDS):
        raise SemanticAuditError("baked build attestation fields must match exactly")
    if attestation.get("schema_version") != BUILD_ATTESTATION_SCHEMA_VERSION:
        raise SemanticAuditError("baked build attestation schema mismatch")
    commit = _validate_commit(
        attestation.get("protocol_commit"), "baked protocol_commit"
    )
    expected_bundle = _validate_sha256(
        attestation.get("protocol_bundle_sha256"),
        "baked protocol_bundle_sha256",
    )
    if attestation.get("bundle_hash_domain") != PROTOCOL_BUNDLE_HASH_DOMAIN.decode(
        "ascii"
    ).rstrip("\0"):
        raise SemanticAuditError("baked build attestation domain mismatch")
    if attestation.get("runtime_files") != list(PROTOCOL_RUNTIME_FILES):
        raise SemanticAuditError("baked build attestation runtime file list mismatch")
    if attestation.get("generated_from_clean_git") is not True:
        raise SemanticAuditError("baked build attestation is not clean-Git generated")
    expected_file_sha256 = attestation.get("file_sha256")
    if (
        not isinstance(expected_file_sha256, Mapping)
        or set(expected_file_sha256) != set(PROTOCOL_RUNTIME_FILES)
    ):
        raise SemanticAuditError("baked build attestation file digest list mismatch")
    for relative in PROTOCOL_RUNTIME_FILES:
        _validate_sha256(
            expected_file_sha256.get(relative), f"baked digest for {relative}"
        )
    if _listed_behavior_files(project_root) != set(PROTOCOL_RUNTIME_FILES):
        raise SemanticAuditError("baked behavior file membership mismatch")
    actual_file_sha256 = _protocol_file_sha256(project_root)
    if dict(expected_file_sha256) != actual_file_sha256:
        raise SemanticAuditError("baked runtime file digest mismatch")
    actual_bundle = protocol_bundle_sha256(project_root)
    if actual_bundle != expected_bundle:
        raise SemanticAuditError("baked runtime bundle digest mismatch")
    return _verified_provenance_record(
        commit=commit,
        bundle=actual_bundle,
        file_sha256=actual_file_sha256,
        verification_mode="baked_image_attestation",
        git_checks_performed=False,
    )


def verify_protocol_provenance(
    project_root: str | Path,
    protocol_commit: str | None = None,
    protocol_bundle_digest: str | None = None,
    *,
    baked_attestation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Verify local Git or the immutable build attestation before any release."""
    root = Path(project_root).resolve()
    git_metadata_present = (root / ".git").exists()
    if git_metadata_present:
        requested_commit = (
            _validate_commit(protocol_commit, "protocol_commit")
            if protocol_commit is not None
            else None
        )
        head = _run_git(root, ["rev-parse", "HEAD"])
        if head.returncode != 0:
            raise SemanticAuditError("failed to read local Git HEAD")
        commit = _validate_commit(head.stdout.strip(), "Git HEAD")
        if requested_commit is not None and requested_commit != commit:
            raise SemanticAuditError("HEAD differs from the requested protocol_commit")
        exists = _run_git(root, ["cat-file", "-e", f"{commit}^{{commit}}"])
        if exists.returncode != 0:
            raise SemanticAuditError("protocol_commit does not exist in the local Git repo")
        for arguments, label in (
            (["diff", "--quiet", "--exit-code"], "tracked working tree"),
            (["diff", "--cached", "--quiet", "--exit-code"], "Git index"),
        ):
            result = _run_git(root, arguments)
            if result.returncode != 0:
                raise SemanticAuditError(
                    f"{label} must be clean at the frozen protocol commit"
                )
        tracked = set(
            _git_lines(
                root,
                ["ls-files", "--", *PROTOCOL_BEHAVIOR_ROOTS],
                "listing tracked behavior files",
            )
        )
        if tracked != set(PROTOCOL_RUNTIME_FILES):
            raise SemanticAuditError(
                "tracked behavior file list differs from the frozen runtime list"
            )
        untracked: set[str] = set()
        for arguments in (
            [
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                *PROTOCOL_BEHAVIOR_ROOTS,
            ],
            [
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--",
                *PROTOCOL_BEHAVIOR_ROOTS,
            ],
        ):
            untracked.update(
                _git_lines(root, arguments, "checking untracked behavior files")
            )
        if untracked:
            raise SemanticAuditError(
                "untracked files are forbidden in behavior/import roots: "
                + ", ".join(sorted(untracked))
            )
        for relative in PROTOCOL_RUNTIME_FILES:
            committed = _run_git(root, ["show", f"{commit}:{relative}"], text=False)
            if committed.returncode != 0:
                raise SemanticAuditError(
                    f"protocol runtime file is absent from protocol_commit: {relative}"
                )
            working = root.joinpath(*relative.split("/")).read_bytes()
            if committed.stdout != working:
                raise SemanticAuditError(
                    f"protocol runtime file differs from protocol_commit: {relative}"
                )
        actual_bundle = protocol_bundle_sha256(root)
        if protocol_bundle_digest is not None:
            expected_bundle = _validate_sha256(
                protocol_bundle_digest, "protocol_bundle_sha256"
            )
            if actual_bundle != expected_bundle:
                raise SemanticAuditError(
                    "protocol runtime bundle SHA-256 differs from the requested digest"
                )
        return _verified_provenance_record(
            commit=commit,
            bundle=actual_bundle,
            file_sha256=_protocol_file_sha256(root),
            verification_mode="local_git_and_bundle",
            git_checks_performed=True,
        )

    attestation = _validate_baked_build_attestation(
        root,
        (
            Path(baked_attestation_path)
            if baked_attestation_path is not None
            else BAKED_BUILD_ATTESTATION_PATH
        ).resolve(),
    )
    if protocol_commit is not None and (
        _validate_commit(protocol_commit, "requested protocol_commit")
        != attestation["protocol_commit"]
    ):
        raise SemanticAuditError(
            "requested protocol_commit differs from the baked attestation"
        )
    if protocol_bundle_digest is not None and (
        _validate_sha256(
            protocol_bundle_digest, "requested protocol_bundle_sha256"
        )
        != attestation["protocol_bundle_sha256"]
    ):
        raise SemanticAuditError(
            "requested protocol bundle differs from the baked attestation"
        )
    return attestation


def validate_protocol_provenance_record(
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a previously verified provenance record at pure-builder boundaries."""
    if not isinstance(provenance, Mapping):
        raise SemanticAuditError("protocol_provenance must be an object")
    if set(provenance) != set(PROTOCOL_PROVENANCE_FIELDS):
        raise SemanticAuditError("protocol provenance fields must match exactly")
    commit = _validate_commit(
        str(provenance.get("protocol_commit", "")), "protocol_commit"
    )
    bundle = _validate_sha256(
        str(provenance.get("protocol_bundle_sha256", "")),
        "protocol_bundle_sha256",
    )
    if provenance.get("verified") is not True:
        raise SemanticAuditError("protocol provenance must be explicitly verified")
    if provenance.get("runtime_files") != list(PROTOCOL_RUNTIME_FILES):
        raise SemanticAuditError("protocol provenance runtime file list mismatch")
    file_sha256 = provenance.get("file_sha256")
    if (
        not isinstance(file_sha256, Mapping)
        or set(file_sha256) != set(PROTOCOL_RUNTIME_FILES)
    ):
        raise SemanticAuditError("protocol provenance file digest list mismatch")
    for relative in PROTOCOL_RUNTIME_FILES:
        _validate_sha256(file_sha256.get(relative), f"provenance digest for {relative}")
    if (
        provenance.get("attestation_schema_version")
        != BUILD_ATTESTATION_SCHEMA_VERSION
        or provenance.get("generated_from_clean_git") is not True
    ):
        raise SemanticAuditError("protocol provenance attestation binding mismatch")
    if provenance.get("bundle_hash_domain") != PROTOCOL_BUNDLE_HASH_DOMAIN.decode(
        "ascii"
    ).rstrip("\0"):
        raise SemanticAuditError("protocol provenance bundle hash domain mismatch")
    if provenance.get("verification_mode") not in {
        "local_git_and_bundle",
        "baked_image_attestation",
        "synthetic_test_fixture",
    }:
        raise SemanticAuditError("protocol provenance verification mode is invalid")
    if type(provenance.get("git_checks_performed")) is not bool:
        raise SemanticAuditError("protocol provenance Git-check flag must be boolean")
    return {
        "protocol_commit": commit,
        "protocol_bundle_sha256": bundle,
        "bundle_hash_domain": provenance["bundle_hash_domain"],
        "runtime_files": list(PROTOCOL_RUNTIME_FILES),
        "file_sha256": dict(sorted(file_sha256.items())),
        "attestation_schema_version": BUILD_ATTESTATION_SCHEMA_VERSION,
        "generated_from_clean_git": True,
        "verification_mode": provenance["verification_mode"],
        "git_checks_performed": provenance["git_checks_performed"],
        "verified": True,
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticAuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise SemanticAuditError(f"non-finite JSON value: {value}")


def parse_jsonl_strict(data: bytes, artifact_name: str) -> list[dict[str, Any]]:
    """Parse UTF-8 JSONL without blank lines, duplicate keys, or non-finite values."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SemanticAuditError(f"{artifact_name} is not UTF-8: {exc}") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise SemanticAuditError(
                f"{artifact_name} contains a blank physical line at {line_number}"
            )
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite_constant,
            )
        except (json.JSONDecodeError, SemanticAuditError) as exc:
            raise SemanticAuditError(
                f"{artifact_name} has invalid JSON on physical line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise SemanticAuditError(
                f"{artifact_name} line {line_number} must be a JSON object"
            )
        _validate_json_value(value)
        records.append(value)
    if data and not data.endswith(b"\n"):
        raise SemanticAuditError(f"{artifact_name} must end with LF")
    return records


def normalize_blob_prefix(prefix: str) -> str:
    """Return a normalized relative Blob prefix or fail closed."""
    if not isinstance(prefix, str):
        raise SemanticAuditError("Blob prefix must be a string")
    if "\\" in prefix or "\x00" in prefix:
        raise SemanticAuditError("Blob prefix must use normalized forward-slash segments")
    normalized = prefix.strip("/")
    if not normalized:
        raise SemanticAuditError("Blob prefix must be non-empty")
    if "//" in normalized:
        raise SemanticAuditError("Blob prefix contains an empty path segment")
    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise SemanticAuditError("Blob prefix contains a non-normalized path segment")
    if any(any(ord(character) < 32 for character in segment) for segment in segments):
        raise SemanticAuditError("Blob prefix contains a control character")
    return normalized


def validate_semantic_audit_prefixes(
    source_prefix: str, output_prefix: str
) -> tuple[str, str]:
    """Normalize prefixes and reject overlap in either direction."""
    source = normalize_blob_prefix(source_prefix)
    output = normalize_blob_prefix(output_prefix)
    try:
        validate_audit_prefixes(source, output)
    except AuditInputError as exc:
        raise SemanticAuditError(str(exc)) from exc
    return source, output


def normalize_numeric_answer(value: str) -> str:
    """Canonicalize one finite decimal; comma-separated forms are rejected."""
    if not isinstance(value, str):
        raise SemanticAuditError("best_answer must be a string or null")
    stripped = value.strip()
    if not stripped:
        raise SemanticAuditError("best_answer must not be empty")
    if "," in stripped:
        raise SemanticAuditError("commas are prohibited in numeric best answers")
    if not _DECIMAL_PATTERN.fullmatch(stripped):
        raise SemanticAuditError(
            "best_answer must be one numeric literal, not an expression or repaired value"
        )
    try:
        number = Decimal(stripped)
    except InvalidOperation as exc:
        raise SemanticAuditError("best_answer is not a valid decimal") from exc
    if not number.is_finite():
        raise SemanticAuditError("best_answer must be finite")
    if number == 0:
        return "0"
    rendered = format(number, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if rendered.startswith("+"):
        rendered = rendered[1:]
    return rendered


def _registered_arithmetic_registry() -> dict[str, dict[str, Any]]:
    actual = [
        {
            "id": item.id,
            "task_family": item.task_family,
            "depth": item.depth,
            "prompt_base": item.prompt_base,
            "expected_answer": item.expected_answer,
            "parse_type": item.parse_type,
        }
        for item in ArithmeticPromptSet.generate_pilot_set()
    ]
    frozen = [dict(item) for item in _FROZEN_ARITHMETIC_REGISTRY]
    if actual != frozen:
        raise SemanticAuditError(
            "ArithmeticPromptSet registry differs from the writer-commit-pinned registry"
        )
    expected_task_ids = {key[4] for key in expected_record_keys()}
    if {item["id"] for item in actual} != expected_task_ids:
        raise SemanticAuditError(
            "writer registry does not match the registered all-45 membership"
        )
    return {item["id"]: item for item in actual}


def reconstruct_generation_prompt(condition: str, question: str) -> str:
    """Reconstruct the condition-specific writer prompt using existing constructors."""
    if condition in {
        "strict_answer_only_prefill_answer",
        "strict_answer_only_stopped",
        "strict_answer_only_postprocessed",
    }:
        return construct_prefill_answer_prompt(question)
    if condition == "visible_cot":
        return construct_visible_cot_prompt(question)
    if condition == "r1_style_thinking":
        return construct_r1_style_thinking_prompt(question)
    raise SemanticAuditError(f"unregistered all-45 condition: {condition}")


def _require_pass(report: Mapping[str, Any], name: str) -> None:
    if report.get("result") != "PASS":
        raise SemanticAuditError(f"{name} failed closed")


def _require_exact_int(value: Any, expected: int, name: str) -> int:
    if type(value) is not int or value != expected:
        raise SemanticAuditError(f"{name} must be the integer {expected}")
    return value


def _property_snapshots_equal(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    fields = ("content_length", "etag", "last_modified", "version_id")
    return all(
        type(left.get(field)) is type(right.get(field))
        and left.get(field) == right.get(field)
        for field in fields
    )


def _validate_recorded_verified_source_evidence(
    source_artifacts: Sequence[Mapping[str, Any]] | None,
    source_immutability: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(source_artifacts, Sequence) or isinstance(
        source_artifacts, (str, bytes)
    ):
        raise SemanticAuditError("verified source property evidence is required")
    artifacts = [dict(item) for item in source_artifacts if isinstance(item, Mapping)]
    if len(artifacts) != len(SOURCE_ARTIFACT_HASHES) or [
        item.get("name") for item in artifacts
    ] != list(SOURCE_ARTIFACT_HASHES):
        raise SemanticAuditError("source property evidence names/order mismatch")
    detailed_fields = {
        "name",
        "sha256",
        "before_read",
        "after_read",
        "conditional_etag_read",
        "unchanged",
        "after_all_source_reads",
    }
    property_fields = {"content_length", "etag", "last_modified", "version_id"}
    for item in artifacts:
        name = item["name"]
        if (
            set(item) != detailed_fields
            or item.get("sha256") != SOURCE_ARTIFACT_HASHES[name]
        ):
            raise SemanticAuditError("source property evidence fields/hash mismatch")
        if (
            type(item.get("conditional_etag_read")) is not bool
            or item.get("unchanged") is not True
        ):
            raise SemanticAuditError("source read evidence is not confirmed unchanged")
        snapshots: list[Mapping[str, Any]] = []
        for field in ("before_read", "after_read", "after_all_source_reads"):
            snapshot = item.get(field)
            if not isinstance(snapshot, Mapping) or set(snapshot) != property_fields:
                raise SemanticAuditError("source Blob property evidence is malformed")
            if (
                type(snapshot.get("content_length")) is not int
                or snapshot["content_length"] < 0
                or not isinstance(snapshot.get("etag"), str)
                or not snapshot["etag"]
                or (
                    snapshot.get("last_modified") is not None
                    and not isinstance(snapshot.get("last_modified"), str)
                )
                or (
                    snapshot.get("version_id") is not None
                    and not isinstance(snapshot.get("version_id"), str)
                )
            ):
                raise SemanticAuditError("source Blob property values are invalid")
            snapshots.append(snapshot)
        if not _property_snapshots_equal(
            snapshots[0], snapshots[1]
        ) or not _property_snapshots_equal(snapshots[0], snapshots[2]):
            raise SemanticAuditError("source Blob properties changed across the read")
    required_immutability = {
        "confirmed_unchanged",
        "comparison_fields",
        "source_write_attempted",
        "evidence_mode",
    }
    if (
        not isinstance(source_immutability, Mapping)
        or set(source_immutability) != required_immutability
        or source_immutability.get("confirmed_unchanged") is not True
        or source_immutability.get("comparison_fields")
        != ["content_length", "etag", "last_modified", "version_id"]
        or source_immutability.get("source_write_attempted") is not False
        or source_immutability.get("evidence_mode")
        != VERIFIED_SOURCE_EVIDENCE_MODE
    ):
        raise SemanticAuditError("verified source immutability evidence is required")
    return artifacts, dict(source_immutability)


def _source_evidence_bytes(
    source_artifacts: Sequence[Mapping[str, Any]],
    source_immutability: Mapping[str, Any],
) -> bytes:
    return canonical_json_bytes(
        {
            "source_artifacts": [dict(item) for item in source_artifacts],
            "source_immutability": dict(source_immutability),
        }
    )


def _validate_recorded_source_evidence_binding(
    source_artifacts: Sequence[Mapping[str, Any]] | None,
    source_immutability: Mapping[str, Any] | None,
    source_evidence_sha256: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifacts, immutability = _validate_recorded_verified_source_evidence(
        source_artifacts, source_immutability
    )
    expected = _validate_sha256(
        source_evidence_sha256, "source_evidence_sha256"
    )
    actual = sha256_bytes(_source_evidence_bytes(artifacts, immutability))
    if actual != expected:
        raise SemanticAuditError("source evidence SHA-256 binding mismatch")
    return artifacts, immutability


def _validate_verified_source_evidence(
    source_bytes: Mapping[str, bytes],
    source_artifacts: Sequence[Mapping[str, Any]] | None,
    source_immutability: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if set(source_bytes) != set(SOURCE_ARTIFACT_HASHES) or any(
        type(value) is not bytes for value in source_bytes.values()
    ):
        raise SemanticAuditError("both exact source byte strings are required")
    computed_hashes = {
        name: sha256_bytes(source_bytes[name]) for name in SOURCE_ARTIFACT_HASHES
    }
    if computed_hashes != SOURCE_ARTIFACT_HASHES:
        raise SemanticAuditError(
            "source bytes failed the two hard-coded preregistered SHA-256 checks"
        )
    artifacts, immutability = _validate_recorded_verified_source_evidence(
        source_artifacts, source_immutability
    )
    for item in artifacts:
        name = str(item["name"])
        for field in ("before_read", "after_read", "after_all_source_reads"):
            if item[field]["content_length"] != len(source_bytes[name]):
                raise SemanticAuditError(
                    "source byte count differs from Blob property evidence"
                )
    return artifacts, immutability


_SOURCE_EVIDENCE_CAPABILITY = object()


class _VerifiedSourceEvidence:
    __slots__ = ("_capability", "_evidence_bytes", "_source_hashes")

    def __init__(
        self,
        capability: object,
        evidence_bytes: bytes,
        source_hashes: tuple[tuple[str, str], ...],
    ) -> None:
        if capability is not _SOURCE_EVIDENCE_CAPABILITY:
            raise SemanticAuditError(
                "verified source evidence can only be minted by the exporter"
            )
        self._capability = capability
        self._evidence_bytes = evidence_bytes
        self._source_hashes = source_hashes

    def __deepcopy__(self, memo: dict[int, Any]) -> _VerifiedSourceEvidence:
        return self


def _mint_verified_source_evidence_for_exporter(
    source_bytes: Mapping[str, bytes],
    source_artifacts: Sequence[Mapping[str, Any]],
    source_immutability: Mapping[str, Any],
) -> _VerifiedSourceEvidence:
    artifacts, immutability = _validate_verified_source_evidence(
        source_bytes, source_artifacts, source_immutability
    )
    evidence_bytes = _source_evidence_bytes(artifacts, immutability)
    source_hashes = tuple(
        (name, sha256_bytes(source_bytes[name])) for name in SOURCE_ARTIFACT_HASHES
    )
    return _VerifiedSourceEvidence(
        _SOURCE_EVIDENCE_CAPABILITY, evidence_bytes, source_hashes
    )


def _consume_verified_source_evidence(
    source_bytes: Mapping[str, bytes], evidence: Any
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    if (
        type(evidence) is not _VerifiedSourceEvidence
        or evidence._capability is not _SOURCE_EVIDENCE_CAPABILITY
    ):
        raise SemanticAuditError(
            "production pack requires exporter-minted verified source evidence"
        )
    source_hashes = tuple(
        (name, sha256_bytes(source_bytes.get(name, b"")))
        for name in SOURCE_ARTIFACT_HASHES
    )
    if source_hashes != evidence._source_hashes:
        raise SemanticAuditError("source bytes differ from verified evidence capability")
    try:
        document = json.loads(evidence._evidence_bytes.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticAuditError("verified source evidence capability is corrupt") from exc
    if (
        not isinstance(document, dict)
        or set(document) != {"source_artifacts", "source_immutability"}
        or canonical_json_bytes(document) != evidence._evidence_bytes
    ):
        raise SemanticAuditError("verified source evidence capability is corrupt")
    artifacts, immutability = _validate_verified_source_evidence(
        source_bytes,
        document["source_artifacts"],
        document["source_immutability"],
    )
    return (
        artifacts,
        immutability,
        sha256_bytes(evidence._evidence_bytes),
    )


def validate_source_records(
    generation_records: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
    *,
    expected_records: int = EXPECTED_RECORD_COUNT,
) -> tuple[
    list[tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]],
    dict[str, Any],
]:
    """Run all preregistered integrity gates before constructing any packet."""
    _require_exact_int(expected_records, EXPECTED_RECORD_COUNT, "expected record count")
    if expected_records != EXPECTED_RECORD_COUNT:
        raise SemanticAuditError("the preregistered audit requires exactly 45 records")
    if len(generation_records) != expected_records:
        raise SemanticAuditError(
            f"generation record count must be 45, got {len(generation_records)}"
        )
    if len(evaluation_records) != expected_records:
        raise SemanticAuditError(
            f"evaluation record count must be 45, got {len(evaluation_records)}"
        )

    pairing, pairs = audit_pairing(generation_records, evaluation_records)
    generation_membership = audit_membership(generation_records)
    evaluation_membership = audit_membership(evaluation_records)
    field_consistency = audit_field_consistency(pairs)
    transformation_consistency, _ = audit_transformation_consistency(pairs)
    reports = {
        "pairing": pairing,
        "generation_membership": generation_membership,
        "evaluation_membership": evaluation_membership,
        "field_consistency": field_consistency,
        "transformation_consistency": transformation_consistency,
    }
    for name, report in reports.items():
        _require_pass(report, name)
    if len(pairs) != expected_records:
        raise SemanticAuditError(f"exact pairing produced {len(pairs)} rather than 45 pairs")

    registry = _registered_arithmetic_registry()
    prompt_mismatches: list[dict[str, Any]] = []
    for key, generation, evaluation in pairs:
        model, task_family, depth, condition, task_id = key
        item = registry.get(str(task_id))
        if item is None:
            prompt_mismatches.append({"key": list(key), "field": "task_id"})
            continue
        expected_prompt = reconstruct_generation_prompt(
            str(condition), str(item["prompt_base"])
        )
        checks = {
            "model": (model, EXPERIMENTAL_TARGET_MODEL_ID),
            "task_family": (task_family, item["task_family"]),
            "depth": (depth, item["depth"]),
            "generation.prompt": (generation.get("prompt", _MISSING), expected_prompt),
            "evaluation.parse_type": (
                evaluation.get("parse_type", _MISSING),
                item["parse_type"],
            ),
            "generation.ground_truth": (
                generation.get("ground_truth", _MISSING),
                item["expected_answer"],
            ),
            "evaluation.expected_answer": (
                evaluation.get("expected_answer", _MISSING),
                item["expected_answer"],
            ),
        }
        for field, (actual, expected) in checks.items():
            if type(actual) is not type(expected) or actual != expected:
                prompt_mismatches.append(
                    {
                        "key": list(key),
                        "field": field,
                        "expected": expected,
                        "actual": (
                            {"state": "missing"} if actual is _MISSING else actual
                        ),
                    }
                )
    if prompt_mismatches:
        raise SemanticAuditError(
            "writer-registry prompt/reference verification failed closed: "
            f"{len(prompt_mismatches)} mismatch(es)"
        )
    reports["writer_registry"] = {
        "result": "PASS",
        "source_writer_commit": SOURCE_WRITER_COMMIT,
        "records_checked": len(pairs),
        "stored_ground_truth_used_for_release": False,
    }
    return list(pairs), reports


def _pairing_key_dict(key: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "model_name": key[0],
        "task_family": key[1],
        "depth": key[2],
        "condition": key[3],
        "task_id": key[4],
    }


def deterministic_review_mapping(
    keys: Iterable[tuple[Any, ...]], seed: int = DEFAULT_SHUFFLE_SEED
) -> tuple[dict[tuple[Any, ...], str], str]:
    """Assign stable blinded IDs by domain-separated hash ordering."""
    if type(seed) is not int:
        raise SemanticAuditError("shuffle seed must be an integer")
    if seed != FROZEN_SHUFFLE_SEED:
        raise SemanticAuditError(
            f"shuffle seed must be the frozen value {FROZEN_SHUFFLE_SEED}"
        )
    unique_keys = set(keys)
    if len(unique_keys) != EXPECTED_RECORD_COUNT:
        raise SemanticAuditError("review mapping requires exactly 45 unique pairing keys")
    ranked: list[tuple[str, str, tuple[Any, ...]]] = []
    for key in unique_keys:
        key_json = canonical_json_text(_pairing_key_dict(key))
        digest = hashlib.sha256(
            SHUFFLE_HASH_DOMAIN
            + str(seed).encode("ascii")
            + b"\0"
            + key_json.encode("ascii")
        ).hexdigest()
        ranked.append((digest, key_json, key))
    ranked.sort(key=lambda item: (item[0], item[1]))
    mapping = {
        key: f"R{ordinal:03d}"
        for ordinal, (_, _, key) in enumerate(ranked, start=1)
    }
    mapping_payload = {
        "hash_domain": SHUFFLE_HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "seed": seed,
        "mapping": [
            {
                "pairing_key": _pairing_key_dict(key),
                "review_id": mapping[key],
            }
            for _, _, key in ranked
        ],
    }
    mapping_hash = sha256_bytes(canonical_json_bytes(mapping_payload))
    return mapping, mapping_hash


def _copy_fields(source: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: source[field] for field in fields if field in source}


def _build_stage1_record(
    review_id: str,
    key: tuple[Any, ...],
    generation: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _, task_family, depth, condition, task_id = key
    item = registry[str(task_id)]
    outputs = {
        "raw_output": evaluation.get("raw_output"),
        "stopped_output": evaluation.get("stopped_output"),
        "postprocessed_output": evaluation.get("postprocessed_output"),
        "eval_output_used": evaluation.get("eval_output_used"),
        "eval_output": evaluation.get("output"),
    }
    if not isinstance(outputs["raw_output"], str):
        raise SemanticAuditError(f"{review_id} raw_output must be a string")
    if not isinstance(outputs["eval_output"], str):
        raise SemanticAuditError(f"{review_id} eval_output must be a string")
    if outputs["eval_output_used"] not in {"raw", "stopped", "postprocessed"}:
        raise SemanticAuditError(f"{review_id} has invalid eval_output_used")
    for field in ("stopped_output", "postprocessed_output"):
        if outputs[field] is not None and not isinstance(outputs[field], str):
            raise SemanticAuditError(f"{review_id} {field} must be a string or null")

    record: dict[str, Any] = {
        "schema_version": STAGE1_SCHEMA_VERSION,
        "review_id": review_id,
        "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
        "task": {
            "task_family": task_family,
            "depth": depth,
            "condition": condition,
            "task_id": task_id,
            "question": item["prompt_base"],
            "parse_type": item["parse_type"],
        },
        "outputs": outputs,
        "intervention": {
            "stop_control_enabled": evaluation.get("stop_control_enabled"),
            "stop_triggered": evaluation.get("stop_triggered"),
            "stop_string": evaluation.get("stop_string"),
            "stop_reason": evaluation.get("stop_reason"),
            "stop_mode": evaluation.get("stop_mode"),
            "postprocessing_applied": evaluation.get("postprocessing_applied"),
            "postprocessing_strategy": evaluation.get("postprocessing_strategy"),
            "postprocessing_reason": evaluation.get("postprocessing_reason"),
        },
    }
    config_aliases = {
        "max_new_tokens": "condition_max_new_tokens",
        "temperature": "condition_temperature",
        "top_p": "condition_top_p",
        "do_sample": "condition_do_sample",
        "decoding_profile": "decoding_profile",
    }
    if any(alias in generation for alias in config_aliases.values()):
        missing = [
            alias for alias in config_aliases.values() if alias not in generation
        ]
        if missing:
            raise SemanticAuditError(
                f"{review_id} has incomplete generation configuration: {missing}"
            )
        record["generation_config"] = {
            field: generation[alias] for field, alias in config_aliases.items()
        }
    validate_blinded_record(record)
    return record


_FORBIDDEN_EXACT_FIELDS = frozenset(
    {
        "stored_correct",
        "correct",
        "correctness",
        "stored_correctness",
        "parsed_answer",
        "stored_parsed_answer",
        "parse_ambiguous",
        "parse_strategy",
        "parse_valid",
        "candidate_answers",
        "parse_error_type",
        "error_type",
        "error",
        "answer_format_warning",
        "ground_truth",
        "expected_answer",
        "reference",
        "reference_answer",
        "registered_reference_answer",
        "branch",
        "phase1_branch",
        "classification",
        "baseline",
        "metrics",
        "metric",
        "rates",
        "rate",
        "mechanical",
        "reviewer_decision",
        "reviewer_judgment",
    }
)


def _forbidden_blinded_field(key: str) -> bool:
    snake_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    normalized = snake_case.lower().replace("-", "_")
    if normalized in {"parse_type", "review_id"}:
        return False
    if normalized in _FORBIDDEN_EXACT_FIELDS:
        return True
    tokens = set(normalized.split("_"))
    if tokens.intersection({"correct", "correctness", "classification"}):
        return True
    if normalized.startswith("stored_"):
        return True
    if normalized.startswith("parse_") and normalized != "parse_type":
        return True
    if "error" in normalized:
        return True
    if (
        "ground_truth" in normalized
        or "reference_answer" in normalized
        or "expected_answer" in normalized
        or "candidate_answer" in normalized
    ):
        return True
    if tokens.intersection(
        {
            "branch",
            "baseline",
            "metric",
            "metrics",
            "rate",
            "rates",
            "mechanical",
            "reviewer",
            "reference",
        }
    ):
        return True
    return False


def scan_blinded_forbidden_fields(value: Any, path: str = "$") -> list[str]:
    """Recursively return forbidden field paths from a blinded payload."""
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if _forbidden_blinded_field(key):
                findings.append(child)
            findings.extend(scan_blinded_forbidden_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                scan_blinded_forbidden_fields(item, f"{path}[{index}]")
            )
    return findings


def _require_exact_fields(
    value: Mapping[str, Any], allowed: frozenset[str], path: str
) -> None:
    extra = set(value) - allowed
    if extra:
        raise SemanticAuditError(f"{path} contains non-allowlisted fields: {sorted(extra)}")


def validate_blinded_record(record: Mapping[str, Any]) -> None:
    """Enforce the stage-1 structural allowlist and leakage scan."""
    _require_exact_fields(record, STAGE1_TOP_LEVEL_FIELDS, "$")
    required_top = STAGE1_TOP_LEVEL_FIELDS - {"generation_config"}
    missing_top = required_top - set(record)
    if missing_top:
        raise SemanticAuditError(
            f"stage-1 record is missing fields: {sorted(missing_top)}"
        )
    nested = (
        ("task", STAGE1_TASK_FIELDS),
        ("outputs", STAGE1_OUTPUT_FIELDS),
        ("intervention", STAGE1_INTERVENTION_FIELDS),
    )
    for field, allowed in nested:
        value = record.get(field)
        if not isinstance(value, dict):
            raise SemanticAuditError(f"stage-1 {field} must be an object")
        _require_exact_fields(value, allowed, f"$.{field}")
        if set(value) != set(allowed):
            raise SemanticAuditError(
                f"stage-1 {field} must contain its complete allowlist"
            )
    if "generation_config" in record:
        value = record["generation_config"]
        if not isinstance(value, dict) or set(value) != set(
            STAGE1_GENERATION_CONFIG_FIELDS
        ):
            raise SemanticAuditError(
                "stage-1 generation_config must contain its complete allowlist"
            )
        if (
            isinstance(value["max_new_tokens"], bool)
            or type(value["max_new_tokens"]) is not int
            or value["max_new_tokens"] <= 0
            or isinstance(value["temperature"], bool)
            or not isinstance(value["temperature"], (int, float))
            or isinstance(value["top_p"], bool)
            or not isinstance(value["top_p"], (int, float))
            or type(value["do_sample"]) is not bool
            or not isinstance(value["decoding_profile"], str)
        ):
            raise SemanticAuditError("stage-1 generation_config values are invalid")
    if record.get("schema_version") != STAGE1_SCHEMA_VERSION:
        raise SemanticAuditError("stage-1 record has the wrong schema version")
    if record.get("experimental_target_model_id") != EXPERIMENTAL_TARGET_MODEL_ID:
        raise SemanticAuditError("stage-1 record has the wrong experimental target")
    if not _REVIEW_ID_PATTERN.fullmatch(str(record.get("review_id", ""))):
        raise SemanticAuditError("stage-1 record has an invalid review_id")
    task = record["task"]
    if (
        task["task_family"] != "arithmetic"
        or isinstance(task["depth"], bool)
        or type(task["depth"]) is not int
        or task["depth"] not in {1, 2, 3}
        or not isinstance(task["condition"], str)
        or not isinstance(task["task_id"], str)
        or not isinstance(task["question"], str)
        or not isinstance(task["parse_type"], str)
    ):
        raise SemanticAuditError("stage-1 task values are invalid")
    outputs = record["outputs"]
    if (
        not isinstance(outputs["raw_output"], str)
        or outputs["stopped_output"] is not None
        and not isinstance(outputs["stopped_output"], str)
        or outputs["postprocessed_output"] is not None
        and not isinstance(outputs["postprocessed_output"], str)
        or not isinstance(outputs["eval_output_used"], str)
        or outputs["eval_output_used"] not in {"raw", "stopped", "postprocessed"}
        or not isinstance(outputs["eval_output"], str)
    ):
        raise SemanticAuditError("stage-1 output values are invalid")
    selected_field = {
        "raw": "raw_output",
        "stopped": "stopped_output",
        "postprocessed": "postprocessed_output",
    }[outputs["eval_output_used"]]
    if outputs[selected_field] != outputs["eval_output"]:
        raise SemanticAuditError("stage-1 selected eval output does not match its variant")
    intervention = record["intervention"]
    if any(
        type(intervention[field]) is not bool
        for field in (
            "stop_control_enabled",
            "stop_triggered",
            "postprocessing_applied",
        )
    ) or any(
        intervention[field] is not None
        and not isinstance(intervention[field], str)
        for field in (
            "stop_string",
            "stop_reason",
            "stop_mode",
            "postprocessing_strategy",
            "postprocessing_reason",
        )
    ):
        raise SemanticAuditError("stage-1 intervention values are invalid")
    findings = scan_blinded_forbidden_fields(record)
    if findings:
        raise SemanticAuditError(
            f"forbidden blinded field leakage detected: {', '.join(findings)}"
        )
    canonical_json_text(dict(record))


def build_review_pack(
    generation_source_bytes: bytes,
    evaluation_source_bytes: bytes,
    *,
    source_prefix: str,
    output_prefix: str | None = None,
    protocol_provenance: Mapping[str, Any],
    source_evidence: Any,
    expected_records: int = EXPECTED_RECORD_COUNT,
    shuffle_seed: int = DEFAULT_SHUFFLE_SEED,
) -> dict[str, Any]:
    """Build a production pack from bytes plus exporter-minted Blob evidence."""
    if type(generation_source_bytes) is not bytes or type(
        evaluation_source_bytes
    ) is not bytes:
        raise SemanticAuditError("production pack construction requires exact bytes")
    generation_records = parse_jsonl_strict(
        generation_source_bytes, "phase1_generations.jsonl"
    )
    evaluation_records = parse_jsonl_strict(
        evaluation_source_bytes, "phase1_eval_records.jsonl"
    )
    return _build_review_pack_from_records(
        generation_records,
        evaluation_records,
        source_prefix=source_prefix,
        output_prefix=output_prefix,
        protocol_provenance=protocol_provenance,
        source_artifacts=None,
        source_immutability=None,
        source_bytes={
            "phase1_generations.jsonl": generation_source_bytes,
            "phase1_eval_records.jsonl": evaluation_source_bytes,
        },
        verified_source_evidence=source_evidence,
        source_evidence_mode=VERIFIED_SOURCE_EVIDENCE_MODE,
        expected_records=expected_records,
        shuffle_seed=shuffle_seed,
    )


def _build_synthetic_review_pack_for_tests(
    generation_records: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
    *,
    source_prefix: str,
    output_prefix: str | None = None,
    protocol_provenance: Mapping[str, Any],
    expected_records: int = EXPECTED_RECORD_COUNT,
    shuffle_seed: int = DEFAULT_SHUFFLE_SEED,
) -> dict[str, Any]:
    """Build a test-only pack that every production release boundary rejects."""
    return _build_review_pack_from_records(
        generation_records,
        evaluation_records,
        source_prefix=source_prefix,
        output_prefix=output_prefix,
        protocol_provenance=protocol_provenance,
        source_artifacts=None,
        source_immutability=None,
        source_bytes=None,
        verified_source_evidence=None,
        source_evidence_mode=SYNTHETIC_TEST_SOURCE_MODE,
        expected_records=expected_records,
        shuffle_seed=shuffle_seed,
    )


def _build_review_pack_from_records(
    generation_records: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
    *,
    source_prefix: str,
    output_prefix: str | None,
    protocol_provenance: Mapping[str, Any],
    source_artifacts: Sequence[Mapping[str, Any]] | None,
    source_immutability: Mapping[str, Any] | None,
    source_bytes: Mapping[str, bytes] | None,
    verified_source_evidence: Any,
    source_evidence_mode: str,
    expected_records: int,
    shuffle_seed: int,
) -> dict[str, Any]:
    """Validate sources and build the two reviewer packets in private memory."""
    normalized_source = normalize_blob_prefix(source_prefix)
    normalized_output = None
    if output_prefix is not None:
        normalized_source, normalized_output = validate_semantic_audit_prefixes(
            normalized_source, output_prefix
        )
    provenance = validate_protocol_provenance_record(protocol_provenance)
    _require_exact_int(expected_records, EXPECTED_RECORD_COUNT, "expected record count")
    _require_exact_int(shuffle_seed, FROZEN_SHUFFLE_SEED, "shuffle seed")
    if source_evidence_mode == VERIFIED_SOURCE_EVIDENCE_MODE:
        if provenance["verification_mode"] not in {
            "local_git_and_bundle",
            "baked_image_attestation",
        }:
            raise SemanticAuditError(
                "production source pack requires trusted protocol provenance"
            )
        artifact_manifest, immutability, source_evidence_sha256 = (
            _consume_verified_source_evidence(
                source_bytes or {}, verified_source_evidence
            )
        )
    elif source_evidence_mode == SYNTHETIC_TEST_SOURCE_MODE:
        if (
            source_bytes is not None
            or source_artifacts is not None
            or source_immutability is not None
            or verified_source_evidence is not None
        ):
            raise SemanticAuditError("synthetic test mode cannot claim source evidence")
        artifact_manifest = [
            {
                "name": name,
                "sha256": sha256_bytes(
                    canonical_jsonl_bytes(
                        generation_records
                        if name == "phase1_generations.jsonl"
                        else evaluation_records
                    )
                ),
            }
            for name in SOURCE_ARTIFACT_HASHES
        ]
        immutability = {
            "confirmed_unchanged": False,
            "evidence_mode": SYNTHETIC_TEST_SOURCE_MODE,
        }
        source_evidence_sha256 = None
    else:
        raise SemanticAuditError("source evidence mode is invalid")
    pairs, validation_reports = validate_source_records(
        generation_records,
        evaluation_records,
        expected_records=expected_records,
    )
    mapping, mapping_hash = deterministic_review_mapping(
        (key for key, _, _ in pairs), seed=shuffle_seed
    )
    registry = _registered_arithmetic_registry()
    stage1_records: list[dict[str, Any]] = []
    stage2_records: list[dict[str, Any]] = []
    for key, generation, evaluation in pairs:
        review_id = mapping[key]
        stage1 = _build_stage1_record(
            review_id, key, generation, evaluation, registry
        )
        stage2 = {
            "schema_version": STAGE2_SCHEMA_VERSION,
            "review_id": review_id,
            "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
            "registered_reference_answer": registry[str(key[4])]["expected_answer"],
        }
        canonical_json_text(stage2)
        stage1_records.append(stage1)
        stage2_records.append(stage2)

    order = lambda item: item["review_id"]
    stage1_records.sort(key=order)
    stage2_records.sort(key=order)
    expected_ids = [f"R{index:03d}" for index in range(1, expected_records + 1)]
    for records, name in (
        (stage1_records, "stage1"),
        (stage2_records, "stage2"),
    ):
        if [record["review_id"] for record in records] != expected_ids:
            raise SemanticAuditError(f"{name} packet review IDs are not exactly R001-R045")

    packet_records = {
        STAGE1_PACKET_FILENAME: stage1_records,
        STAGE2_PACKET_FILENAME: stage2_records,
    }
    packet_bytes = {
        name: canonical_jsonl_bytes(records)
        for name, records in packet_records.items()
    }
    manifest = {
        "audit_schema_version": SEMANTIC_AUDIT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_path": "docs/phase1_semantic_review_protocol.md",
        "protocol_commit": provenance["protocol_commit"],
        "protocol_bundle_sha256": provenance["protocol_bundle_sha256"],
        "protocol_provenance": provenance,
        "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
        "reviewer": {
            "model_id": REVIEWER_MODEL_ID,
            "reasoning_effort": REVIEWER_REASONING_EFFORT,
            "role": "engineering_audit_only",
        },
        "source_writer_commit": SOURCE_WRITER_COMMIT,
        "source_prefix": normalized_source,
        "output_prefix": normalized_output,
        "source_artifacts": artifact_manifest,
        "source_immutability": immutability,
        "source_evidence_mode": source_evidence_mode,
        "source_evidence_sha256": source_evidence_sha256,
        "expected_record_count": expected_records,
        "task_family": "arithmetic",
        "depths": [1, 2, 3],
        "registered_conditions": sorted({key[3] for key, _, _ in pairs}),
        "shuffle": {
            "seed": shuffle_seed,
            "hash_domain": SHUFFLE_HASH_DOMAIN.decode("ascii").rstrip("\0"),
            "algorithm": SHUFFLE_ALGORITHM,
            "mapping_sha256": mapping_hash,
        },
        "packet_files": {
            name: {
                "sha256": sha256_bytes(data),
                "record_count": len(packet_records[name]),
                "canonical_json": (
                    "ensure_ascii=true,sort_keys=true,separators=(',',':'),"
                    "allow_nan=false,LF"
                ),
            }
            for name, data in packet_bytes.items()
        },
        "validation": {
            name: {
                "result": report["result"],
                "records_checked": report.get(
                    "pairs_checked",
                    report.get("actual_observations", report.get("records_checked")),
                ),
            }
            for name, report in validation_reports.items()
        },
        "model_inference_performed": False,
        "new_observations_generated": False,
        "new_behavioral_observations_generated": False,
        "stored_ground_truth_used_for_packet_reference": False,
        "source_artifacts_modified": False,
        "official_stored_metrics_or_classifications_modified": False,
        "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    return {
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "packet_records": packet_records,
        "packet_bytes": packet_bytes,
        "source_bytes": (
            dict(source_bytes)
            if source_evidence_mode == VERIFIED_SOURCE_EVIDENCE_MODE
            else None
        ),
        "_verified_source_evidence": (
            verified_source_evidence
            if source_evidence_mode == VERIFIED_SOURCE_EVIDENCE_MODE
            else None
        ),
        "validation_reports": validation_reports,
    }


def _rebuild_verified_pack_for_release(pack: Mapping[str, Any]) -> dict[str, Any]:
    manifest = pack.get("manifest")
    source_bytes = pack.get("source_bytes")
    source_evidence = pack.get("_verified_source_evidence")
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("source_evidence_mode") != VERIFIED_SOURCE_EVIDENCE_MODE
        or not isinstance(source_bytes, Mapping)
    ):
        raise SemanticAuditError(
            "production release requires verified_source_bytes source evidence"
        )
    rebuilt = build_review_pack(
        source_bytes.get("phase1_generations.jsonl"),
        source_bytes.get("phase1_eval_records.jsonl"),
        source_prefix=manifest.get("source_prefix"),
        output_prefix=manifest.get("output_prefix"),
        protocol_provenance=manifest.get("protocol_provenance", {}),
        source_evidence=source_evidence,
        expected_records=manifest.get("expected_record_count"),
        shuffle_seed=(
            manifest.get("shuffle", {}).get("seed")
            if isinstance(manifest.get("shuffle"), Mapping)
            else None
        ),
    )
    if (
        pack.get("manifest") != rebuilt["manifest"]
        or pack.get("packet_bytes") != rebuilt["packet_bytes"]
        or pack.get("packet_records") != rebuilt["packet_records"]
    ):
        raise SemanticAuditError("review pack differs from verified source reconstruction")
    return rebuilt


def _release_reservation_bytes(
    release_stage: str, output_prefix: str
) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": RELEASE_RESERVATION_SCHEMA_VERSION,
            "release_stage": release_stage,
            "output_prefix": normalize_blob_prefix(output_prefix),
            "state": "immutable_exclusive_reservation",
        }
    )


_RELEASE_CHAIN_COMMON_FIELDS = (
    "audit_schema_version",
    "protocol_version",
    "protocol_path",
    "protocol_commit",
    "protocol_bundle_sha256",
    "protocol_provenance",
    "experimental_target_model_id",
    "reviewer",
    "source_writer_commit",
    "source_prefix",
    "source_artifacts",
    "source_immutability",
    "source_evidence_mode",
    "source_evidence_sha256",
    "expected_record_count",
    "task_family",
    "depths",
    "registered_conditions",
    "shuffle",
    "model_inference_performed",
    "new_observations_generated",
    "new_behavioral_observations_generated",
    "source_artifacts_modified",
    "official_stored_metrics_or_classifications_modified",
    "mandatory_boundary",
)


def _validate_release_chain_common_fields(
    stage1_manifest: Mapping[str, Any],
    stage2_manifest: Mapping[str, Any],
) -> None:
    for field in _RELEASE_CHAIN_COMMON_FIELDS:
        if stage1_manifest.get(field) != stage2_manifest.get(field):
            raise SemanticAuditError(
                f"Stage-1 and Stage-2 releases disagree on {field}"
            )
    stage1_output = stage1_manifest.get("output_prefix")
    stage2_output = stage2_manifest.get("output_prefix")
    if not isinstance(stage1_output, str) or not isinstance(stage2_output, str):
        raise SemanticAuditError("staged release output prefixes are missing")
    validate_semantic_audit_prefixes(stage1_output, stage2_output)


def build_release_files(
    pack: Mapping[str, Any],
    release_stage: str,
    *,
    stage1_submission_artifacts: Sequence[tuple[bytes, bytes]] = (),
    stage1_release_files: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Build one reviewer release containing exactly one packet and its marker."""
    if release_stage not in {"stage1", "stage2"}:
        raise SemanticAuditError("release_stage must be stage1 or stage2")
    verified_pack = _rebuild_verified_pack_for_release(pack)
    manifest = verified_pack.get("manifest")
    packet_bytes = verified_pack.get("packet_bytes")
    packet_records = verified_pack.get("packet_records")
    if not all(
        isinstance(value, Mapping)
        for value in (manifest, packet_bytes, packet_records)
    ):
        raise SemanticAuditError("review pack has an invalid private structure")
    packet_name = (
        STAGE1_PACKET_FILENAME if release_stage == "stage1" else STAGE2_PACKET_FILENAME
    )
    data = packet_bytes.get(packet_name)
    records = packet_records.get(packet_name)
    if not isinstance(data, bytes) or not isinstance(records, Sequence):
        raise SemanticAuditError(f"private pack lacks {packet_name}")
    if canonical_jsonl_bytes(records) != data:
        raise SemanticAuditError(f"{packet_name} is not canonical")

    stage1_gate: dict[str, Any] | None = None
    if release_stage == "stage1":
        if stage1_submission_artifacts or stage1_release_files is not None:
            raise SemanticAuditError(
                "stage-1 release cannot include prior release/submission bindings"
            )
    else:
        if stage1_release_files is None:
            raise SemanticAuditError(
                "stage-2 release requires exact validated Stage-1 release bytes"
            )
        validated_stage1_release = validate_stage_release_files(
            stage1_release_files, expected_stage="stage1"
        )
        stage1_release_files = validated_stage1_release["files"]
        stage1_manifest = validated_stage1_release["manifest"]
        released_stage1_packet = validated_stage1_release["packet_bytes"]
        expected_stage1_packet = packet_bytes.get(STAGE1_PACKET_FILENAME)
        if released_stage1_packet != expected_stage1_packet:
            raise SemanticAuditError(
                "validated Stage-1 release packet differs from source reconstruction"
            )
        _validate_release_chain_common_fields(stage1_manifest, manifest)
        if len(stage1_submission_artifacts) != 2:
            raise SemanticAuditError(
                "stage-2 release requires two sealed Stage-1 submissions"
            )
        expected_hash = sha256_bytes(released_stage1_packet)
        if (
            expected_hash
            != manifest["packet_files"][STAGE1_PACKET_FILENAME]["sha256"]
        ):
            raise SemanticAuditError(
                "validated Stage-1 packet hash differs from source reconstruction"
            )
        validated_stage1: list[SealedSubmission] = []
        seal_hashes: list[str] = []
        for submission_bytes, seal_bytes in stage1_submission_artifacts:
            validated_stage1.append(
                validate_submission_artifact(
                    submission_bytes,
                    seal_bytes,
                    expected_stage="stage1",
                    expected_packet_sha256=expected_hash,
                )
            )
            seal_hashes.append(sha256_bytes(seal_bytes))
        reviewer_a, reviewer_b = validated_stage1
        ensure_distinct_reviewer_identities(reviewer_a, reviewer_b)
        for submission in validated_stage1:
            if (
                submission.review_stage != "stage1"
                or submission.packet_sha256 != expected_hash
                or len(submission.rows) != EXPECTED_RECORD_COUNT
            ):
                raise SemanticAuditError(
                    "stage-2 release received an invalid Stage-1 seal"
                )
        stage1_release_hash = sha256_bytes(
            validated_stage1_release["manifest_bytes"]
        )
        stage1_gate = {
            "stage1_packet_sha256": expected_hash,
            "stage1_release_manifest_sha256": stage1_release_hash,
            "complete": True,
            "reviewers": [
                {
                    "reviewer_id": submission.reviewer_id,
                    "reviewer_model_id": submission.reviewer_model_id,
                    "reviewer_reasoning_effort": (
                        submission.reviewer_reasoning_effort
                    ),
                    "submission_sha256": submission.submission_sha256,
                    "seal_sha256": seal_hash,
                }
                for submission, seal_hash in zip(validated_stage1, seal_hashes)
            ],
        }

    reservation_bytes = _release_reservation_bytes(
        release_stage, str(manifest["output_prefix"])
    )
    release_manifest = {
        "release_manifest_schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "release_stage": release_stage,
        "release_complete": True,
        "manifest_uploaded_last": True,
        "audit_schema_version": manifest["audit_schema_version"],
        "protocol_version": manifest["protocol_version"],
        "protocol_path": manifest["protocol_path"],
        "protocol_commit": manifest["protocol_commit"],
        "protocol_bundle_sha256": manifest["protocol_bundle_sha256"],
        "protocol_provenance": deepcopy(manifest["protocol_provenance"]),
        "experimental_target_model_id": manifest["experimental_target_model_id"],
        "reviewer": deepcopy(manifest["reviewer"]),
        "source_writer_commit": manifest["source_writer_commit"],
        "source_prefix": manifest["source_prefix"],
        "output_prefix": manifest["output_prefix"],
        "source_artifacts": deepcopy(manifest["source_artifacts"]),
        "source_immutability": deepcopy(manifest["source_immutability"]),
        "source_evidence_mode": manifest["source_evidence_mode"],
        "source_evidence_sha256": manifest["source_evidence_sha256"],
        "expected_record_count": manifest["expected_record_count"],
        "task_family": manifest["task_family"],
        "depths": deepcopy(manifest["depths"]),
        "registered_conditions": deepcopy(manifest["registered_conditions"]),
        "shuffle": deepcopy(manifest["shuffle"]),
        "packet_files": {
            packet_name: deepcopy(manifest["packet_files"][packet_name])
        },
        "reservation": {
            "filename": RELEASE_RESERVATION_FILENAME,
            "schema_version": RELEASE_RESERVATION_SCHEMA_VERSION,
            "state": "immutable_exclusive_reservation",
            "sha256": sha256_bytes(reservation_bytes),
        },
        "stage1_gate": stage1_gate,
        "model_inference_performed": False,
        "new_observations_generated": False,
        "new_behavioral_observations_generated": False,
        "source_artifacts_modified": False,
        "official_stored_metrics_or_classifications_modified": False,
        "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
    }
    manifest_name = RELEASE_MANIFEST_FILENAMES[release_stage]
    manifest_bytes = canonical_json_bytes(release_manifest)
    files = {
        RELEASE_RESERVATION_FILENAME: reservation_bytes,
        packet_name: data,
        manifest_name: manifest_bytes,
    }
    validated_release = validate_stage_release_files(
        files,
        expected_stage=release_stage,
        stage1_release_files=stage1_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
    )
    if validated_release["records"] != list(records):
        raise SemanticAuditError("constructed release failed exact record validation")
    return {
        "release_stage": release_stage,
        "packet_name": packet_name,
        "manifest_name": manifest_name,
        "manifest": release_manifest,
        "manifest_bytes": manifest_bytes,
        "packet_records": validated_release["records"],
        "files": files,
    }


def expected_review_ids(count: int = EXPECTED_RECORD_COUNT) -> list[str]:
    if type(count) is not int or count < 0:
        raise SemanticAuditError("review ID count must be a non-negative integer")
    return [f"R{index:03d}" for index in range(1, count + 1)]


def _validate_judgment_semantics(judgment: Mapping[str, Any]) -> str | None:
    category = judgment.get("semantic_category")
    presence = judgment.get("answer_presence")
    status = judgment.get("answer_status")
    best_answer = judgment.get("best_answer")
    if category not in SEMANTIC_CATEGORIES:
        raise SemanticAuditError(f"invalid semantic_category: {category!r}")
    if presence not in ANSWER_PRESENCE_LABELS:
        raise SemanticAuditError(f"invalid answer_presence: {presence!r}")
    if status not in ANSWER_STATUS_LABELS:
        raise SemanticAuditError(f"invalid answer_status: {status!r}")

    normalized: str | None
    if best_answer is None:
        normalized = None
    elif isinstance(best_answer, str):
        normalized = normalize_numeric_answer(best_answer)
    else:
        raise SemanticAuditError("best_answer must be a numeric string or null")

    compatibility = {
        "answer_present": ({"correct", "incorrect"}, True),
        "ambiguous": ({"ambiguous"}, False),
        "no_answer": ({"no_answer"}, False),
        "inconclusive": ({"inconclusive"}, False),
    }
    statuses, requires_answer = compatibility[str(presence)]
    if status not in statuses:
        raise SemanticAuditError(
            f"answer_presence {presence!r} is incompatible with answer_status {status!r}"
        )
    if requires_answer != (normalized is not None):
        requirement = "non-null" if requires_answer else "null"
        raise SemanticAuditError(
            f"best_answer must be {requirement} when answer_presence is {presence}"
        )

    category_constraints = {
        "unambiguous_single_answer": "answer_present",
        "true_multiple_candidate_ambiguity": "ambiguous",
        "no_answer": "no_answer",
        "malformed_but_answer_recoverable": "answer_present",
        "malformed_no_reliable_answer": "no_answer",
        "review_inconclusive": "inconclusive",
    }
    required_presence = category_constraints.get(str(category))
    if required_presence is not None and presence != required_presence:
        raise SemanticAuditError(
            f"semantic_category {category!r} requires answer_presence "
            f"{required_presence!r}"
        )
    if category == "incomplete_or_truncated" and presence not in {
        "answer_present",
        "no_answer",
        "inconclusive",
    }:
        raise SemanticAuditError(
            "incomplete_or_truncated requires a conclusive answer/no-answer state "
            "or an explicitly inconclusive state"
        )
    return normalized


_SUBMISSION_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "review_id",
        "reviewer_id",
        "reviewer_model_id",
        "reviewer_reasoning_effort",
        "review_stage",
        "packet_sha256",
    }
)
_STAGE1_SUBMISSION_FIELDS = _SUBMISSION_BINDING_FIELDS | frozenset(
    {
        "stage1_answer_presence",
        "semantic_ambiguity_category",
        "best_answer_if_any",
        "issue_tags",
        "confidence",
        "notes",
    }
)
_STAGE2_SUBMISSION_FIELDS = _SUBMISSION_BINDING_FIELDS | frozenset(
    {"answer_status", "notes"}
)
_ARBITRATION_SUBMISSION_FIELDS = _SUBMISSION_BINDING_FIELDS | frozenset(
    {
        "semantic_category",
        "answer_presence",
        "answer_status",
        "best_answer",
        "issue_tags",
        "confidence",
        "notes",
    }
)
_SUBMISSION_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "review_stage",
        "submission_schema_version",
        "reviewer_id",
        "reviewer_model_id",
        "reviewer_reasoning_effort",
        "packet_sha256",
        "submission_sha256",
        "record_count",
        "review_ids",
    }
)


@dataclass(frozen=True)
class SealedSubmission:
    review_stage: str
    reviewer_id: str
    reviewer_model_id: str
    reviewer_reasoning_effort: str
    packet_sha256: str
    submission_sha256: str
    rows: tuple[dict[str, Any], ...]
    seal: dict[str, Any]


def _required_submission_ids(
    rows: Sequence[Mapping[str, Any]], expected_ids: Sequence[str]
) -> list[str]:
    required_ids = list(expected_ids)
    if len(set(required_ids)) != len(required_ids):
        raise SemanticAuditError("expected review IDs contain duplicates")
    if len(rows) != len(required_ids):
        raise SemanticAuditError(
            f"submission must contain exactly {len(required_ids)} rows, got {len(rows)}"
        )
    actual = [str(row.get("review_id")) for row in rows if isinstance(row, Mapping)]
    if len(actual) != len(rows) or set(actual) != set(required_ids):
        raise SemanticAuditError("submission review IDs do not match exactly")
    if len(actual) != len(set(actual)):
        raise SemanticAuditError("submission review IDs contain duplicates")
    return required_ids


def _validate_row_binding(
    source: Mapping[str, Any],
    *,
    review_stage: str,
    schema_version: str,
    packet_sha256: str,
) -> tuple[str, str, str]:
    if source.get("schema_version") != schema_version:
        raise SemanticAuditError("submission schema_version mismatch")
    if source.get("review_stage") != review_stage:
        raise SemanticAuditError("submission review_stage mismatch")
    reviewer_id = source.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise SemanticAuditError("submission reviewer_id must be a non-empty string")
    if source.get("reviewer_model_id") != REVIEWER_MODEL_ID:
        raise SemanticAuditError("reviewer model must be exactly gpt-5.6-sol")
    if source.get("reviewer_reasoning_effort") != REVIEWER_REASONING_EFFORT:
        raise SemanticAuditError("reviewer reasoning effort must be exactly max")
    expected_hash = _validate_sha256(packet_sha256, "packet_sha256")
    if source.get("packet_sha256") != expected_hash:
        raise SemanticAuditError("submission packet_sha256 binding mismatch")
    return reviewer_id, REVIEWER_MODEL_ID, REVIEWER_REASONING_EFFORT


def _validate_issue_confidence_notes(
    source: Mapping[str, Any], review_id: str
) -> tuple[list[str], str, str | None]:
    issue_tags = source.get("issue_tags")
    if not isinstance(issue_tags, list) or any(
        not isinstance(tag, str) for tag in issue_tags
    ):
        raise SemanticAuditError(f"{review_id} issue_tags must be a string list")
    if len(issue_tags) != len(set(issue_tags)):
        raise SemanticAuditError(f"{review_id} issue_tags contain duplicates")
    invalid_tags = set(issue_tags) - set(ISSUE_TAGS)
    if invalid_tags:
        raise SemanticAuditError(
            f"{review_id} has invalid issue tags: {sorted(invalid_tags)}"
        )
    confidence = source.get("confidence")
    if confidence not in CONFIDENCE_LABELS:
        raise SemanticAuditError(f"{review_id} has invalid confidence")
    notes = source.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise SemanticAuditError(f"{review_id} notes must be a string or null")
    return sorted(issue_tags), str(confidence), notes


def validate_stage1_submission(
    rows: Sequence[Mapping[str, Any]],
    *,
    packet_sha256: str,
    expected_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Validate mandatory row-level Stage-1 bindings without synthesizing metadata."""
    required_ids = _required_submission_ids(
        rows, expected_ids or expected_review_ids()
    )
    identities: set[tuple[str, str, str]] = set()
    canonical_rows: list[dict[str, Any]] = []
    for source in rows:
        review_id = str(source.get("review_id"))
        if set(source) != set(_STAGE1_SUBMISSION_FIELDS):
            raise SemanticAuditError(
                f"{review_id} Stage-1 fields must match the exact schema"
            )
        identities.add(
            _validate_row_binding(
                source,
                review_stage="stage1",
                schema_version=STAGE1_JUDGMENT_SCHEMA_VERSION,
                packet_sha256=packet_sha256,
            )
        )
        presence = source["stage1_answer_presence"]
        category = source["semantic_ambiguity_category"]
        placeholder_status = {
            "answer_present": "correct",
            "ambiguous": "ambiguous",
            "no_answer": "no_answer",
            "inconclusive": "inconclusive",
        }.get(presence)
        normalized = _validate_judgment_semantics(
            {
                "semantic_category": category,
                "answer_presence": presence,
                "answer_status": placeholder_status,
                "best_answer": source["best_answer_if_any"],
            }
        )
        issue_tags, confidence, notes = _validate_issue_confidence_notes(
            source, review_id
        )
        canonical_rows.append(
            {
                "schema_version": STAGE1_JUDGMENT_SCHEMA_VERSION,
                "review_id": review_id,
                "reviewer_id": source["reviewer_id"],
                "reviewer_model_id": REVIEWER_MODEL_ID,
                "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
                "review_stage": "stage1",
                "packet_sha256": packet_sha256,
                "stage1_answer_presence": presence,
                "semantic_ambiguity_category": category,
                "best_answer_if_any": normalized,
                "issue_tags": issue_tags,
                "confidence": confidence,
                "notes": notes,
            }
        )
    if len(identities) != 1:
        raise SemanticAuditError("one submission must have one immutable reviewer identity")
    canonical_rows.sort(key=lambda row: required_ids.index(str(row["review_id"])))
    return canonical_rows


def validate_stage2_submission(
    rows: Sequence[Mapping[str, Any]],
    *,
    packet_sha256: str,
    stage1_rows: Sequence[Mapping[str, Any]],
    stage2_records: Sequence[Mapping[str, Any]],
    expected_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Validate Stage-2-only answers and immutable continuity with Stage 1."""
    required_ids = _required_submission_ids(
        rows, expected_ids or expected_review_ids()
    )
    _required_submission_ids(stage1_rows, required_ids)
    stage1_index = {str(row["review_id"]): row for row in stage1_rows}
    references = {
        str(row.get("review_id")): normalize_numeric_answer(
            str(row.get("registered_reference_answer"))
        )
        for row in stage2_records
    }
    if set(references) != set(required_ids):
        raise SemanticAuditError("Stage-2 packet review IDs do not match exactly")
    identities: set[tuple[str, str, str]] = set()
    canonical_rows: list[dict[str, Any]] = []
    for source in rows:
        review_id = str(source.get("review_id"))
        if set(source) != set(_STAGE2_SUBMISSION_FIELDS):
            raise SemanticAuditError(
                f"{review_id} Stage-2 fields must match the exact schema"
            )
        identity = _validate_row_binding(
            source,
            review_stage="stage2",
            schema_version=STAGE2_JUDGMENT_SCHEMA_VERSION,
            packet_sha256=packet_sha256,
        )
        identities.add(identity)
        stage1 = stage1_index[review_id]
        expected_identity = (
            stage1["reviewer_id"],
            stage1["reviewer_model_id"],
            stage1["reviewer_reasoning_effort"],
        )
        if identity != expected_identity:
            raise SemanticAuditError(
                f"{review_id} Stage-2 reviewer identity differs from Stage 1"
            )
        status = source.get("answer_status")
        allowed_statuses = {
            "answer_present": {"correct", "incorrect"},
            "ambiguous": {"ambiguous"},
            "no_answer": {"no_answer"},
            "inconclusive": {"inconclusive"},
        }.get(stage1["stage1_answer_presence"], set())
        if status not in allowed_statuses:
            raise SemanticAuditError(
                f"{review_id} answer_status is incompatible with Stage 1"
            )
        best_answer = stage1["best_answer_if_any"]
        if status == "correct" and best_answer != references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is correct but differs from the registered reference"
            )
        if status == "incorrect" and best_answer == references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is incorrect but equals the registered reference"
            )
        notes = source.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise SemanticAuditError(f"{review_id} notes must be a string or null")
        canonical_rows.append(
            {
                "schema_version": STAGE2_JUDGMENT_SCHEMA_VERSION,
                "review_id": review_id,
                "reviewer_id": source["reviewer_id"],
                "reviewer_model_id": REVIEWER_MODEL_ID,
                "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
                "review_stage": "stage2",
                "packet_sha256": packet_sha256,
                "answer_status": status,
                "notes": notes,
            }
        )
    if len(identities) != 1:
        raise SemanticAuditError("one submission must have one immutable reviewer identity")
    canonical_rows.sort(key=lambda row: required_ids.index(str(row["review_id"])))
    return canonical_rows


def validate_arbiter_submission(
    rows: Sequence[Mapping[str, Any]],
    *,
    packet_sha256: str,
    expected_ids: Sequence[str],
    reviewer_ids: Sequence[str],
    stage2_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate the distinct arbiter and its exact arbitration-packet binding."""
    required_ids = _required_submission_ids(rows, expected_ids)
    references = {
        str(row["review_id"]): normalize_numeric_answer(
            str(row["registered_reference_answer"])
        )
        for row in stage2_records
    }
    identities: set[tuple[str, str, str]] = set()
    canonical_rows: list[dict[str, Any]] = []
    for source in rows:
        review_id = str(source.get("review_id"))
        if set(source) != set(_ARBITRATION_SUBMISSION_FIELDS):
            raise SemanticAuditError(
                f"{review_id} arbitration fields must match the exact schema"
            )
        identity = _validate_row_binding(
            source,
            review_stage="arbitration",
            schema_version=ARBITRATION_JUDGMENT_SCHEMA_VERSION,
            packet_sha256=packet_sha256,
        )
        if identity[0] in set(reviewer_ids):
            raise SemanticAuditError("arbiter identity must differ from both reviewers")
        identities.add(identity)
        normalized = _validate_judgment_semantics(source)
        issue_tags, confidence, notes = _validate_issue_confidence_notes(
            source, review_id
        )
        status = source["answer_status"]
        if status == "correct" and normalized != references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is correct but differs from the registered reference"
            )
        if status == "incorrect" and normalized == references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is incorrect but equals the registered reference"
            )
        canonical_rows.append(
            {
                "schema_version": ARBITRATION_JUDGMENT_SCHEMA_VERSION,
                "review_id": review_id,
                "reviewer_id": source["reviewer_id"],
                "reviewer_model_id": REVIEWER_MODEL_ID,
                "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
                "review_stage": "arbitration",
                "packet_sha256": packet_sha256,
                "semantic_category": source["semantic_category"],
                "answer_presence": source["answer_presence"],
                "answer_status": status,
                "best_answer": normalized,
                "issue_tags": issue_tags,
                "confidence": confidence,
                "notes": notes,
            }
        )
    if len(identities) != 1:
        raise SemanticAuditError("arbiter submission must have one immutable identity")
    canonical_rows.sort(key=lambda row: required_ids.index(str(row["review_id"])))
    return canonical_rows


def build_submission_seal(
    rows: Sequence[Mapping[str, Any]], review_stage: str
) -> dict[str, Any]:
    """Create the canonical hash manifest that makes a validated submission sealed."""
    if review_stage not in {"stage1", "stage2", "arbitration"} or not rows:
        raise SemanticAuditError("cannot seal an empty or unsupported submission")
    schema_versions = {str(row.get("schema_version")) for row in rows}
    reviewer_ids = {str(row.get("reviewer_id")) for row in rows}
    model_ids = {str(row.get("reviewer_model_id")) for row in rows}
    efforts = {str(row.get("reviewer_reasoning_effort")) for row in rows}
    stages = {str(row.get("review_stage")) for row in rows}
    packet_hashes = {str(row.get("packet_sha256")) for row in rows}
    if any(
        len(values) != 1
        for values in (
            schema_versions,
            reviewer_ids,
            model_ids,
            efforts,
            stages,
            packet_hashes,
        )
    ) or stages != {review_stage}:
        raise SemanticAuditError("submission bindings are not immutable")
    data = canonical_jsonl_bytes(rows)
    return {
        "schema_version": SUBMISSION_SEAL_SCHEMA_VERSION,
        "review_stage": review_stage,
        "submission_schema_version": next(iter(schema_versions)),
        "reviewer_id": next(iter(reviewer_ids)),
        "reviewer_model_id": next(iter(model_ids)),
        "reviewer_reasoning_effort": next(iter(efforts)),
        "packet_sha256": next(iter(packet_hashes)),
        "submission_sha256": sha256_bytes(data),
        "record_count": len(rows),
        "review_ids": [str(row["review_id"]) for row in rows],
    }


def validate_sealed_submission(
    submission_bytes: bytes,
    seal: Mapping[str, Any],
    *,
    expected_stage: str,
    expected_packet_sha256: str,
    stage1_submission: SealedSubmission | None = None,
    stage2_records: Sequence[Mapping[str, Any]] = (),
    expected_ids: Sequence[str] | None = None,
    reviewer_ids: Sequence[str] = (),
) -> SealedSubmission:
    """Validate canonical rows and their mandatory immutable seal."""
    rows = parse_jsonl_strict(submission_bytes, f"{expected_stage} submission")
    if canonical_jsonl_bytes(rows) != submission_bytes:
        raise SemanticAuditError("submission JSONL is not canonically serialized")
    ids = list(expected_ids or expected_review_ids())
    if expected_stage == "stage1":
        canonical_rows = validate_stage1_submission(
            rows, packet_sha256=expected_packet_sha256, expected_ids=ids
        )
        schema_version = STAGE1_JUDGMENT_SCHEMA_VERSION
    elif expected_stage == "stage2":
        if not isinstance(stage1_submission, SealedSubmission):
            raise SemanticAuditError("Stage-2 seal requires the corresponding Stage-1 seal")
        canonical_rows = validate_stage2_submission(
            rows,
            packet_sha256=expected_packet_sha256,
            stage1_rows=stage1_submission.rows,
            stage2_records=stage2_records,
            expected_ids=ids,
        )
        schema_version = STAGE2_JUDGMENT_SCHEMA_VERSION
    elif expected_stage == "arbitration":
        canonical_rows = validate_arbiter_submission(
            rows,
            packet_sha256=expected_packet_sha256,
            expected_ids=ids,
            reviewer_ids=reviewer_ids,
            stage2_records=stage2_records,
        )
        schema_version = ARBITRATION_JUDGMENT_SCHEMA_VERSION
    else:
        raise SemanticAuditError("unsupported submission review stage")
    if canonical_jsonl_bytes(canonical_rows) != submission_bytes:
        raise SemanticAuditError("submission rows are not in canonical normalized form")
    expected_seal = build_submission_seal(canonical_rows, expected_stage)
    if not isinstance(seal, Mapping) or type(seal.get("record_count")) is not int:
        raise SemanticAuditError("submission seal record_count must be an integer")
    if set(seal) != set(_SUBMISSION_SEAL_FIELDS) or dict(seal) != expected_seal:
        raise SemanticAuditError("submission seal is missing, stale, or mismatched")
    if seal.get("submission_schema_version") != schema_version:
        raise SemanticAuditError("submission seal schema binding mismatch")
    return SealedSubmission(
        review_stage=expected_stage,
        reviewer_id=str(seal["reviewer_id"]),
        reviewer_model_id=str(seal["reviewer_model_id"]),
        reviewer_reasoning_effort=str(seal["reviewer_reasoning_effort"]),
        packet_sha256=str(seal["packet_sha256"]),
        submission_sha256=str(seal["submission_sha256"]),
        rows=tuple(deepcopy(canonical_rows)),
        seal=dict(seal),
    )


def validate_submission_artifact(
    submission_bytes: bytes,
    seal_bytes: bytes,
    *,
    expected_stage: str,
    expected_packet_sha256: str,
    stage1_submission: SealedSubmission | None = None,
    stage2_records: Sequence[Mapping[str, Any]] = (),
    expected_ids: Sequence[str] | None = None,
    reviewer_ids: Sequence[str] = (),
) -> SealedSubmission:
    """Parse canonical immutable bytes and then validate the complete seal."""
    if type(submission_bytes) is not bytes or type(seal_bytes) is not bytes:
        raise SemanticAuditError("submission and seal must be exact immutable bytes")
    seal = parse_json_object_strict(seal_bytes, f"{expected_stage} submission seal")
    if canonical_json_bytes(seal) != seal_bytes:
        raise SemanticAuditError("submission seal is not canonically serialized")
    return validate_sealed_submission(
        submission_bytes,
        seal,
        expected_stage=expected_stage,
        expected_packet_sha256=expected_packet_sha256,
        stage1_submission=stage1_submission,
        stage2_records=stage2_records,
        expected_ids=expected_ids,
        reviewer_ids=reviewer_ids,
    )


def ensure_distinct_reviewer_identities(
    reviewer_a: SealedSubmission, reviewer_b: SealedSubmission
) -> None:
    if not all(isinstance(value, SealedSubmission) for value in (reviewer_a, reviewer_b)):
        raise SemanticAuditError("two sealed reviewer submissions are required")
    if reviewer_a.reviewer_id == reviewer_b.reviewer_id:
        raise SemanticAuditError("reviewer A and B identities must be distinct")


def combine_staged_submission(
    stage1: SealedSubmission, stage2: SealedSubmission
) -> list[dict[str, Any]]:
    """Join immutable Stage-1 and Stage-2 rows for downstream adjudication only."""
    if (
        not isinstance(stage1, SealedSubmission)
        or not isinstance(stage2, SealedSubmission)
        or stage1.review_stage != "stage1"
        or stage2.review_stage != "stage2"
        or stage1.reviewer_id != stage2.reviewer_id
        or len(stage1.rows) != EXPECTED_RECORD_COUNT
        or len(stage2.rows) != EXPECTED_RECORD_COUNT
    ):
        raise SemanticAuditError("invalid Stage-1/Stage-2 submission transition")
    stage2_index = {str(row["review_id"]): row for row in stage2.rows}
    combined: list[dict[str, Any]] = []
    for first in stage1.rows:
        review_id = str(first["review_id"])
        second = stage2_index.get(review_id)
        if second is None:
            raise SemanticAuditError("Stage-2 submission is missing a review ID")
        combined.append(
            {
                "schema_version": JUDGMENT_SCHEMA_VERSION,
                "review_id": review_id,
                "reviewer_id": stage1.reviewer_id,
                "reviewer_model_id": stage1.reviewer_model_id,
                "reviewer_reasoning_effort": stage1.reviewer_reasoning_effort,
                "stage1_packet_sha256": stage1.packet_sha256,
                "stage2_packet_sha256": stage2.packet_sha256,
                "semantic_category": first["semantic_ambiguity_category"],
                "answer_presence": first["stage1_answer_presence"],
                "answer_status": second["answer_status"],
                "best_answer": first["best_answer_if_any"],
                "issue_tags": deepcopy(first["issue_tags"]),
                "confidence": first["confidence"],
                "stage1_notes": first["notes"],
                "stage2_notes": second["notes"],
            }
        )
    return combined


def validate_reviewer_submission(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Reject legacy combined rows; staged submissions must carry their own bindings."""
    raise SemanticAuditError(
        "bare combined reviewer rows are prohibited; validate sealed Stage-1 and "
        "Stage-2 submissions separately"
    )


def validate_review_status_against_references(
    rows: Sequence[Mapping[str, Any]],
    stage2_records: Sequence[Mapping[str, Any]],
) -> None:
    """Require correct/incorrect labels to agree with the registered reference."""
    references: dict[str, str] = {}
    for record in stage2_records:
        review_id = str(record.get("review_id"))
        reference = record.get("registered_reference_answer")
        if not isinstance(reference, str):
            raise SemanticAuditError(f"{review_id} has an invalid registered reference")
        references[review_id] = normalize_numeric_answer(reference)
    if {str(row["review_id"]) for row in rows} - set(references):
        raise SemanticAuditError("judgment IDs are absent from the stage-2 packet")
    for row in rows:
        review_id = str(row["review_id"])
        status = row["answer_status"]
        best = row["best_answer"]
        if status == "correct" and best != references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is labeled correct but differs from the registered reference"
            )
        if status == "incorrect" and best == references[review_id]:
            raise SemanticAuditError(
                f"{review_id} is labeled incorrect but equals the registered reference"
            )


def _na_measure(reason: str, *, numerator: int | None = None, denominator: int = 0) -> dict[str, Any]:
    result: dict[str, Any] = {
        "value": None,
        "display": "NA",
        "reason": reason,
        "denominator": denominator,
    }
    if numerator is not None:
        result["numerator"] = numerator
    return result


def _rate_measure(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator == 0:
        return _na_measure(
            "zero_denominator", numerator=numerator, denominator=denominator
        )
    value = numerator / denominator
    return {
        "value": value,
        "display": f"{value:.4f}",
        "reason": None,
        "numerator": numerator,
        "denominator": denominator,
    }


def nominal_cohen_kappa(
    left: Sequence[Any], right: Sequence[Any]
) -> dict[str, Any]:
    """Compute nominal Cohen's kappa with preregistered NA guards."""
    if len(left) != len(right):
        raise SemanticAuditError("kappa inputs must have equal length")
    n = len(left)
    if n == 0:
        return _na_measure("n_zero")
    if len(set(left)) < 2 or len(set(right)) < 2:
        return _na_measure("constant_marginal", denominator=n)
    labels = set(left) | set(right)
    observed = sum(a == b for a, b in zip(left, right)) / n
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        (left_counts[label] / n) * (right_counts[label] / n) for label in labels
    )
    denominator = 1.0 - expected
    if denominator == 0:
        return _na_measure("zero_kappa_denominator", denominator=n)
    value = (observed - expected) / denominator
    return {
        "value": value,
        "display": f"{value:.4f}",
        "reason": None,
        "n": n,
        "observed_agreement": observed,
        "expected_agreement": expected,
    }


def quadratic_confidence_kappa(
    left: Sequence[str], right: Sequence[str]
) -> dict[str, Any]:
    """Compute quadratic weighted kappa for low/medium/high confidence."""
    if len(left) != len(right):
        raise SemanticAuditError("confidence kappa inputs must have equal length")
    if any(label not in CONFIDENCE_LABELS for label in [*left, *right]):
        raise SemanticAuditError("confidence kappa received an invalid label")
    n = len(left)
    if n == 0:
        return _na_measure("n_zero")
    if len(set(left)) < 2 or len(set(right)) < 2:
        return _na_measure("constant_marginal", denominator=n)
    indices = {label: index for index, label in enumerate(CONFIDENCE_LABELS)}
    maximum_distance = len(CONFIDENCE_LABELS) - 1

    def weight(a: str, b: str) -> float:
        return 1.0 - (
            (indices[a] - indices[b]) / maximum_distance
        ) ** 2

    observed = sum(weight(a, b) for a, b in zip(left, right)) / n
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = 0.0
    for a in CONFIDENCE_LABELS:
        for b in CONFIDENCE_LABELS:
            expected += (
                left_counts[a] / n
                * right_counts[b]
                / n
                * weight(a, b)
            )
    denominator = 1.0 - expected
    if denominator == 0:
        return _na_measure("zero_kappa_denominator", denominator=n)
    value = (observed - expected) / denominator
    return {
        "value": value,
        "display": f"{value:.4f}",
        "reason": None,
        "n": n,
        "observed_weighted_agreement": observed,
        "expected_weighted_agreement": expected,
    }


def _exact_agreement(left: Sequence[Any], right: Sequence[Any]) -> dict[str, Any]:
    matches = sum(a == b for a, b in zip(left, right))
    return {"matches": matches, **_rate_measure(matches, len(left))}


def compute_reviewer_agreement(
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compute the complete preregistered inter-reviewer agreement report."""
    if len(reviewer_a) != len(reviewer_b):
        raise SemanticAuditError("reviewer submissions have different lengths")
    a_index = {str(row["review_id"]): row for row in reviewer_a}
    b_index = {str(row["review_id"]): row for row in reviewer_b}
    if set(a_index) != set(b_index) or len(a_index) != len(reviewer_a):
        raise SemanticAuditError("reviewer submissions have mismatched or duplicate IDs")
    ids = sorted(a_index)

    fields = ("semantic_category", "answer_presence", "answer_status")
    exact = {}
    kappas = {}
    for field in fields:
        left = [a_index[review_id][field] for review_id in ids]
        right = [b_index[review_id][field] for review_id in ids]
        exact[field] = _exact_agreement(left, right)
        kappas[field] = nominal_cohen_kappa(left, right)

    left_answers = [a_index[review_id]["best_answer"] for review_id in ids]
    right_answers = [b_index[review_id]["best_answer"] for review_id in ids]
    both_null = sum(
        left is None and right is None
        for left, right in zip(left_answers, right_answers)
    )
    one_null = sum(
        (left is None) != (right is None)
        for left, right in zip(left_answers, right_answers)
    )
    non_null_pairs = [
        (left, right)
        for left, right in zip(left_answers, right_answers)
        if left is not None and right is not None
    ]
    conditional_matches = sum(left == right for left, right in non_null_pairs)
    best_answer = {
        "overall_exact": _exact_agreement(left_answers, right_answers),
        "both_null": {"count": both_null, **_rate_measure(both_null, len(ids))},
        "one_null": {"count": one_null, **_rate_measure(one_null, len(ids))},
        "conditional_non_null_exact": {
            "matches": conditional_matches,
            **_rate_measure(conditional_matches, len(non_null_pairs)),
        },
        "nominal_kappa": nominal_cohen_kappa(left_answers, right_answers),
    }

    exact_issue_matches = 0
    jaccards: list[float] = []
    issue_sets_a: list[str] = []
    issue_sets_b: list[str] = []
    for review_id in ids:
        a_set = set(a_index[review_id]["issue_tags"])
        b_set = set(b_index[review_id]["issue_tags"])
        exact_issue_matches += a_set == b_set
        union = a_set | b_set
        jaccards.append(1.0 if not union else len(a_set & b_set) / len(union))
        issue_sets_a.append(canonical_json_text(sorted(a_set)))
        issue_sets_b.append(canonical_json_text(sorted(b_set)))

    confidence_a = [str(a_index[review_id]["confidence"]) for review_id in ids]
    confidence_b = [str(b_index[review_id]["confidence"]) for review_id in ids]
    confidence_mae = (
        None
        if not ids
        else sum(
            abs(CONFIDENCE_SCORES[a] - CONFIDENCE_SCORES[b])
            for a, b in zip(confidence_a, confidence_b)
        )
        / len(ids)
    )
    return {
        "n": len(ids),
        "exact_agreement": exact,
        "best_answer": best_answer,
        "issue_tags": {
            "exact": {
                "matches": exact_issue_matches,
                **_rate_measure(exact_issue_matches, len(ids)),
            },
            "mean_jaccard": (
                _na_measure("n_zero")
                if not jaccards
                else {
                    "value": sum(jaccards) / len(jaccards),
                    "display": f"{sum(jaccards) / len(jaccards):.4f}",
                    "reason": None,
                    "denominator": len(jaccards),
                }
            ),
            "nominal_exact_set_kappa": nominal_cohen_kappa(
                issue_sets_a, issue_sets_b
            ),
        },
        "confidence": {
            "exact": _exact_agreement(confidence_a, confidence_b),
            "mean_absolute_error": (
                _na_measure("n_zero")
                if confidence_mae is None
                else {
                    "value": confidence_mae,
                    "display": f"{confidence_mae:.4f}",
                    "reason": None,
                    "denominator": len(ids),
                }
            ),
            "quadratic_weighted_kappa": quadratic_confidence_kappa(
                confidence_a, confidence_b
            ),
        },
        "nominal_cohen_kappa": kappas,
    }


def _stored_correctness_state(stored: Mapping[str, Any]) -> str:
    if "correctness" not in stored:
        return "missing"
    value = stored["correctness"]
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return "invalid"


def _stored_correctness_relation(
    judgment: Mapping[str, Any], stored: Mapping[str, Any]
) -> str:
    return f"{judgment['answer_status']}_vs_stored_{_stored_correctness_state(stored)}"


def determine_arbitration_triggers(
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    unblinded_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply the prospectively frozen, field-level arbitration triggers."""
    a_index = {str(row["review_id"]): row for row in reviewer_a}
    b_index = {str(row["review_id"]): row for row in reviewer_b}
    stored_index = {str(row["review_id"]): row for row in unblinded_records}
    if set(a_index) != set(b_index) or set(a_index) != set(stored_index):
        raise SemanticAuditError("reviewer and unblinded IDs must match exactly")
    triggers: list[dict[str, Any]] = []
    for review_id in sorted(a_index):
        a = a_index[review_id]
        b = b_index[review_id]
        reasons: list[str] = []
        for field in (
            "semantic_category",
            "answer_presence",
            "best_answer",
            "answer_status",
        ):
            if a[field] != b[field]:
                reasons.append(f"{field}_difference")
        if set(a["issue_tags"]) != set(b["issue_tags"]):
            reasons.append("issue_set_difference")
        if {a["confidence"], b["confidence"]} == {"high", "low"}:
            reasons.append("high_low_confidence_difference")
        if (
            a["semantic_category"] == b["semantic_category"]
            == "review_inconclusive"
            or a["answer_presence"] == b["answer_presence"] == "inconclusive"
            or a["answer_status"] == b["answer_status"] == "inconclusive"
        ):
            reasons.append("agreed_inconclusive")
        stored = stored_index[review_id].get("stored_evaluation_fields")
        if not isinstance(stored, Mapping):
            raise SemanticAuditError(
                f"{review_id} lacks stored_evaluation_fields after unblinding"
            )
        if _stored_correctness_relation(a, stored) != _stored_correctness_relation(
            b, stored
        ):
            reasons.append("stored_correctness_relation_difference")
        if reasons:
            triggers.append({"review_id": review_id, "reasons": reasons})
    return triggers


def _judgment_for_arbitration(row: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "review_id",
        "reviewer_id",
        "reviewer_model_id",
        "reviewer_reasoning_effort",
        "stage1_packet_sha256",
        "stage2_packet_sha256",
        "semantic_category",
        "answer_presence",
        "answer_status",
        "best_answer",
        "issue_tags",
        "confidence",
        "stage1_notes",
        "stage2_notes",
    )
    return _copy_fields(row, fields)


def build_blinded_arbitration_packet(
    stage1_records: Sequence[Mapping[str, Any]],
    stage2_records: Sequence[Mapping[str, Any]],
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    triggers: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build the stored-field-free packet for only prospectively triggered IDs."""
    indexes = [
        {str(row["review_id"]): row for row in records}
        for records in (stage1_records, stage2_records, reviewer_a, reviewer_b)
    ]
    ids = [str(trigger["review_id"]) for trigger in triggers]
    if len(ids) != len(set(ids)):
        raise SemanticAuditError("arbitration trigger IDs contain duplicates")
    records: list[dict[str, Any]] = []
    for review_id in sorted(ids):
        try:
            stage1, stage2, a, b = (index[review_id] for index in indexes)
        except KeyError as exc:
            raise SemanticAuditError(
                f"arbitration trigger {review_id} is absent from an input packet"
            ) from exc
        validate_blinded_record(stage1)
        record = {
            "schema_version": ARBITRATION_PACKET_SCHEMA_VERSION,
            "review_id": review_id,
            "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
            "stage1_record": dict(stage1),
            "stage2_record": dict(stage2),
            "reviewer_a_judgment": _judgment_for_arbitration(a),
            "reviewer_b_judgment": _judgment_for_arbitration(b),
            "frozen_rubric": FROZEN_RUBRIC,
        }
        canonical_json_text(record)
        records.append(record)
    return records


def _is_inconclusive(judgment: Mapping[str, Any]) -> bool:
    if (
        judgment.get("semantic_category") == "review_inconclusive"
        or judgment.get("answer_presence") == "inconclusive"
        or judgment.get("answer_status") == "inconclusive"
    ):
        return True
    try:
        _validate_judgment_semantics(judgment)
    except (KeyError, SemanticAuditError):
        return True
    issue_tags = judgment.get("issue_tags")
    if (
        not isinstance(issue_tags, list)
        or any(tag not in ISSUE_TAGS for tag in issue_tags)
        or len(issue_tags) != len(set(issue_tags))
        or judgment.get("confidence") not in CONFIDENCE_LABELS
    ):
        return True
    return False


def _is_unresolved(judgment: Mapping[str, Any]) -> bool:
    if _is_inconclusive(judgment):
        return True
    if judgment.get("derived_parser_label") == "not_assessable":
        return True
    if "stored_parse_ambiguous" in judgment and type(
        judgment.get("stored_parse_ambiguous")
    ) is not bool:
        return True
    return False


def merge_final_judgments(
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    arbiter: Sequence[Mapping[str, Any]],
    trigger_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Use shared nontrigger judgments and arbiter judgments for triggered rows."""
    a_index = {str(row["review_id"]): row for row in reviewer_a}
    b_index = {str(row["review_id"]): row for row in reviewer_b}
    arbiter_index = {str(row["review_id"]): row for row in arbiter}
    triggers = set(trigger_ids)
    if set(arbiter_index) != triggers:
        raise SemanticAuditError("arbiter IDs must equal arbitration trigger IDs exactly")
    if set(a_index) != set(b_index):
        raise SemanticAuditError("reviewer IDs do not match")

    judgment_fields = (
        "semantic_category",
        "answer_presence",
        "answer_status",
        "best_answer",
        "issue_tags",
        "confidence",
    )
    final: list[dict[str, Any]] = []
    for review_id in sorted(a_index):
        if review_id in triggers:
            source = arbiter_index[review_id]
            final.append(
                {
                    "review_id": review_id,
                    "adjudication_source": "arbiter",
                    "adjudicator_id": source["reviewer_id"],
                    **{field: deepcopy(source[field]) for field in judgment_fields},
                }
            )
            continue
        a = a_index[review_id]
        b = b_index[review_id]
        for field in judgment_fields[:-1]:
            left = set(a[field]) if field == "issue_tags" else a[field]
            right = set(b[field]) if field == "issue_tags" else b[field]
            if left != right:
                raise SemanticAuditError(
                    f"nontrigger {review_id} has a disagreement in {field}"
                )
        confidence_distance = abs(
            CONFIDENCE_SCORES[str(a["confidence"])]
            - CONFIDENCE_SCORES[str(b["confidence"])]
        )
        if confidence_distance > 1:
            raise SemanticAuditError(
                f"nontrigger {review_id} has non-adjacent confidence"
            )
        confidence = min(
            (str(a["confidence"]), str(b["confidence"])),
            key=lambda value: CONFIDENCE_SCORES[value],
        )
        final.append(
            {
                "review_id": review_id,
                "adjudication_source": "shared_reviewers",
                "adjudicator_id": None,
                "semantic_category": a["semantic_category"],
                "answer_presence": a["answer_presence"],
                "answer_status": a["answer_status"],
                "best_answer": a["best_answer"],
                "issue_tags": sorted(a["issue_tags"]),
                "confidence": confidence,
            }
        )
    return final


def derive_parser_label(
    stored_parse_ambiguous: Any,
    semantic_category: str,
    answer_presence: str | None = None,
    answer_status: str | None = None,
) -> str:
    """Derive TP/FP/FN/TN-style parser label without treating no-answer as ambiguity."""
    if (
        semantic_category == "review_inconclusive"
        or answer_presence == "inconclusive"
        or answer_status == "inconclusive"
    ):
        return "not_assessable"
    if semantic_category not in SEMANTIC_CATEGORIES:
        raise SemanticAuditError(f"invalid semantic category: {semantic_category}")
    if type(stored_parse_ambiguous) is not bool:
        return "not_assessable"
    semantic_positive = semantic_category == "true_multiple_candidate_ambiguity"
    if stored_parse_ambiguous and semantic_positive:
        return "correct_flag"
    if stored_parse_ambiguous and not semantic_positive:
        return "parser_overflag"
    if not stored_parse_ambiguous and semantic_positive:
        return "parser_underflag"
    return "correct_non_flag"


def parsed_answer_consistency(
    stored_parsed_answer: Any,
    semantic_category: str,
    semantic_best_answer: str | None,
    answer_presence: str | None = None,
    answer_status: str | None = None,
) -> str:
    """Classify stored parsed-answer agreement without calculation or repair."""
    if (
        semantic_category == "review_inconclusive"
        or answer_presence == "inconclusive"
        or answer_status == "inconclusive"
    ):
        return "inconclusive"
    if semantic_category == "true_multiple_candidate_ambiguity":
        return "semantic_ambiguous"
    semantic_has_answer = semantic_best_answer is not None
    stored_normalized: str | None = None
    stored_has_answer = isinstance(stored_parsed_answer, str) and bool(
        stored_parsed_answer.strip()
    )
    if stored_has_answer:
        try:
            stored_normalized = normalize_numeric_answer(stored_parsed_answer)
        except SemanticAuditError:
            stored_normalized = None
    if semantic_has_answer:
        if not stored_has_answer:
            return "stored_no_answer_semantic_answer"
        if stored_normalized == semantic_best_answer:
            return "stored_matches_semantic_best"
        return "stored_differs_from_semantic_best"
    if stored_has_answer:
        return "stored_answer_semantic_no_answer"
    return "stored_matches_semantic_best"


def _confusion_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels: Counter[str] = Counter()
    for row in rows:
        if _is_inconclusive(row):
            labels["not_assessable"] += 1
            continue
        labels[
            derive_parser_label(
                row.get("stored_parse_ambiguous"),
                str(row.get("semantic_category")),
                str(row.get("answer_presence")),
                str(row.get("answer_status")),
            )
        ] += 1
    return {
        "tp": labels["correct_flag"],
        "fp": labels["parser_overflag"],
        "fn": labels["parser_underflag"],
        "tn": labels["correct_non_flag"],
        "unresolved": labels["not_assessable"],
        "total": len(rows),
    }


def compute_ambiguity_confusion_matrix(
    rows: Sequence[Mapping[str, Any]],
    *,
    force_rates_unavailable: bool = False,
) -> dict[str, Any]:
    """Compute ambiguity confusion and preserve an unresolved stratum."""
    counts = _confusion_counts(rows)
    tp, fp, fn, tn = (
        counts["tp"],
        counts["fp"],
        counts["fn"],
        counts["tn"],
    )
    definitions = {
        "precision": (tp, tp + fp),
        "recall": (tp, tp + fn),
        "specificity": (tn, tn + fp),
        "fpr": (fp, fp + tn),
        "fnr": (fn, fn + tp),
        "npv": (tn, tn + fn),
        "false_positive_rate": (fp, fp + tn),
        "false_negative_rate": (fn, fn + tp),
        "negative_predictive_value": (tn, tn + fn),
        "accuracy": (tp + tn, tp + fp + fn + tn),
    }
    if counts["unresolved"] or force_rates_unavailable:
        reason = (
            "global_unresolved_or_inconclusive_records"
            if force_rates_unavailable
            else "unresolved_or_inconclusive_records"
        )
        rates = {
            name: _na_measure(
                reason,
                numerator=numerator,
                denominator=denominator,
            )
            for name, (numerator, denominator) in definitions.items()
        }
    else:
        rates = {
            name: _rate_measure(numerator, denominator)
            for name, (numerator, denominator) in definitions.items()
        }
    return {
        "counts": counts,
        "rates_available": counts["unresolved"] == 0
        and not force_rates_unavailable,
        "rates": rates,
    }


def _grouped_confusion(
    rows: Sequence[Mapping[str, Any]],
    field: str,
    *,
    force_rates_unavailable: bool,
) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field))].append(row)
    return {
        key: compute_ambiguity_confusion_matrix(
            group, force_rates_unavailable=force_rates_unavailable
        )
        for key, group in sorted(groups.items())
    }


def build_ambiguity_confusion_report(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    any_unresolved = _confusion_counts(rows)["unresolved"] > 0
    return {
        "schema_version": SEMANTIC_AUDIT_SCHEMA_VERSION,
        "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
        "semantic_ambiguity_positive": "true_multiple_candidate_ambiguity",
        "overall": compute_ambiguity_confusion_matrix(
            rows, force_rates_unavailable=any_unresolved
        ),
        "by_condition": _grouped_confusion(
            rows, "condition", force_rates_unavailable=any_unresolved
        ),
        "by_branch": _grouped_confusion(
            rows, "branch", force_rates_unavailable=any_unresolved
        ),
        "by_depth": _grouped_confusion(
            rows, "depth", force_rates_unavailable=any_unresolved
        ),
        "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
    }


def build_correctness_confusion_table(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Cross-tab five semantic statuses against five stored correctness states."""
    def counts_for(group: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
        table = {
            semantic: {stored: 0 for stored in STORED_CORRECTNESS_STATES}
            for semantic in ANSWER_STATUS_LABELS
        }
        for row in group:
            semantic = (
                "inconclusive" if _is_inconclusive(row) else row.get("answer_status")
            )
            stored = row.get("stored_correctness_state")
            if semantic not in table:
                raise SemanticAuditError(
                    f"invalid semantic answer status: {semantic}"
                )
            if stored not in STORED_CORRECTNESS_STATES:
                raise SemanticAuditError(
                    f"invalid stored correctness state: {stored}"
                )
            table[str(semantic)][str(stored)] += 1
        return table

    def grouped(field: str) -> dict[str, dict[str, dict[str, int]]]:
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get(field))].append(row)
        return {key: counts_for(group) for key, group in sorted(groups.items())}

    table = counts_for(rows)
    return {
        "schema_version": SEMANTIC_AUDIT_SCHEMA_VERSION,
        "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
        "semantic_status_rows": list(ANSWER_STATUS_LABELS),
        "stored_state_columns": list(STORED_CORRECTNESS_STATES),
        "counts": table,
        "by_condition": grouped("condition"),
        "by_branch": grouped("branch"),
        "by_depth": grouped("depth"),
        "total": len(rows),
        "binary_collapse_prohibited": True,
        "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
    }


def material_evaluator_error(
    stored_correctness: Any, semantic_answer_status: str
) -> bool | None:
    """Return whether semantic adjudication could change stored correctness."""
    if semantic_answer_status == "inconclusive":
        return None
    if type(stored_correctness) is not bool:
        return None
    if semantic_answer_status == "correct":
        semantic_correctness = True
    elif semantic_answer_status in {"incorrect", "no_answer", "ambiguous"}:
        semantic_correctness = False
    else:
        raise SemanticAuditError(
            f"invalid semantic answer status: {semantic_answer_status}"
        )
    return stored_correctness != semantic_correctness


def validate_completed_two_stage_transition(
    stage1_a: SealedSubmission,
    stage1_b: SealedSubmission,
    stage2_a: SealedSubmission,
    stage2_b: SealedSubmission,
    *,
    stage1_packet_sha256: str,
    stage2_packet_sha256: str,
) -> None:
    """Require two complete, distinct, identity-continuous staged submissions."""
    expected_stage1 = _validate_sha256(
        stage1_packet_sha256, "stage1_packet_sha256"
    )
    expected_stage2 = _validate_sha256(
        stage2_packet_sha256, "stage2_packet_sha256"
    )
    ensure_distinct_reviewer_identities(stage1_a, stage1_b)
    for first, second in ((stage1_a, stage2_a), (stage1_b, stage2_b)):
        if (
            first.review_stage != "stage1"
            or second.review_stage != "stage2"
            or first.packet_sha256 != expected_stage1
            or second.packet_sha256 != expected_stage2
            or first.reviewer_id != second.reviewer_id
            or first.reviewer_model_id != second.reviewer_model_id
            or first.reviewer_reasoning_effort
            != second.reviewer_reasoning_effort
            or len(first.rows) != EXPECTED_RECORD_COUNT
            or len(second.rows) != EXPECTED_RECORD_COUNT
        ):
            raise SemanticAuditError(
                "private integration requires two complete identity-matched Stage-2 seals"
            )
    ensure_distinct_reviewer_identities(stage2_a, stage2_b)


def _build_restricted_records(
    generation_records: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
    pack: Mapping[str, Any],
    *,
    stage1_a: SealedSubmission,
    stage1_b: SealedSubmission,
    stage2_a: SealedSubmission,
    stage2_b: SealedSubmission,
) -> list[dict[str, Any]]:
    """Finalizer-private construction; unavailable before both Stage-2 seals."""
    manifest = pack.get("manifest")
    packet_records = pack.get("packet_records")
    if not isinstance(manifest, Mapping) or not isinstance(packet_records, Mapping):
        raise SemanticAuditError("private review pack structure is invalid")
    stage1_records = packet_records.get(STAGE1_PACKET_FILENAME)
    stage2_records = packet_records.get(STAGE2_PACKET_FILENAME)
    if not isinstance(stage1_records, Sequence) or not isinstance(
        stage2_records, Sequence
    ):
        raise SemanticAuditError("private review pack lacks staged packets")
    stage1_hash = str(
        manifest["packet_files"][STAGE1_PACKET_FILENAME]["sha256"]
    )
    stage2_hash = str(
        manifest["packet_files"][STAGE2_PACKET_FILENAME]["sha256"]
    )
    validate_completed_two_stage_transition(
        stage1_a,
        stage1_b,
        stage2_a,
        stage2_b,
        stage1_packet_sha256=stage1_hash,
        stage2_packet_sha256=stage2_hash,
    )

    pairs, _ = validate_source_records(generation_records, evaluation_records)
    mapping, _ = deterministic_review_mapping(
        (key for key, _, _ in pairs), FROZEN_SHUFFLE_SEED
    )
    stage1_index = {str(row["review_id"]): row for row in stage1_records}
    stage2_index = {str(row["review_id"]): row for row in stage2_records}
    if set(stage1_index) != set(expected_review_ids()) or set(stage2_index) != set(
        expected_review_ids()
    ):
        raise SemanticAuditError("staged packet IDs must be exactly R001-R045")
    registry = _registered_arithmetic_registry()
    restricted: list[dict[str, Any]] = []
    for key, generation, evaluation in pairs:
        review_id = mapping[key]
        expected_stage1 = _build_stage1_record(
            review_id, key, generation, evaluation, registry
        )
        expected_stage2 = {
            "schema_version": STAGE2_SCHEMA_VERSION,
            "review_id": review_id,
            "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
            "registered_reference_answer": registry[str(key[4])]["expected_answer"],
        }
        if stage1_index[review_id] != expected_stage1:
            raise SemanticAuditError(
                f"{review_id} Stage-1 packet differs from the private source"
            )
        if stage2_index[review_id] != expected_stage2:
            raise SemanticAuditError(
                f"{review_id} Stage-2 packet differs from the private source"
            )
        restricted.append(
            {
                "schema_version": UNBLINDED_SCHEMA_VERSION,
                "review_id": review_id,
                "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
                "pairing_key": _pairing_key_dict(key),
                "stage1_record": deepcopy(expected_stage1),
                "registered_reference_answer": expected_stage2[
                    "registered_reference_answer"
                ],
                "stored_generation_fields": _copy_fields(
                    generation, STORED_GENERATION_ALLOWLIST
                ),
                "stored_evaluation_fields": _copy_fields(
                    evaluation, STORED_EVALUATION_ALLOWLIST
                ),
            }
        )
    restricted.sort(key=lambda row: str(row["review_id"]))
    if [row["review_id"] for row in restricted] != expected_review_ids():
        raise SemanticAuditError("restricted private integration IDs are incomplete")
    return restricted


def _source_copies_from_unblinded(
    unblinded_records: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]],
]:
    generations: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    for packet_record in unblinded_records:
        stage1 = packet_record.get("stage1_record")
        pairing_key = packet_record.get("pairing_key")
        stored_generation = packet_record.get("stored_generation_fields")
        stored_evaluation = packet_record.get("stored_evaluation_fields")
        if not all(
            isinstance(value, Mapping)
            for value in (
                stage1,
                pairing_key,
                stored_generation,
                stored_evaluation,
            )
        ):
            raise SemanticAuditError("restricted unblinded record has invalid structure")
        validate_blinded_record(stage1)
        task = stage1["task"]
        outputs = stage1["outputs"]
        intervention = stage1["intervention"]
        expected_key = {
            "model_name": EXPERIMENTAL_TARGET_MODEL_ID,
            "task_family": task["task_family"],
            "depth": task["depth"],
            "condition": task["condition"],
            "task_id": task["task_id"],
        }
        if dict(pairing_key) != expected_key:
            raise SemanticAuditError(
                f"{stage1['review_id']} pairing key does not match stage-1 fields"
            )
        branch = get_phase1_branch_metadata(str(task["condition"]))["phase1_branch"]
        generation = {
            **expected_key,
            "output": outputs["raw_output"],
            "raw_output": outputs["raw_output"],
            "eval_output": outputs["eval_output"],
            "eval_output_used": outputs["eval_output_used"],
            "stopped_output": outputs["stopped_output"],
            "postprocessed_output": outputs["postprocessed_output"],
            "stop_control_enabled": intervention["stop_control_enabled"],
            "stop_triggered": intervention["stop_triggered"],
            "stop_reason": intervention["stop_reason"],
            "stop_string": intervention["stop_string"],
            "stop_mode": intervention["stop_mode"],
            "postprocessing_applied": intervention["postprocessing_applied"],
            "postprocessing_strategy": intervention["postprocessing_strategy"],
            "postprocessing_reason": intervention["postprocessing_reason"],
            "phase1_branch": branch,
            **dict(stored_generation),
        }
        evaluation = {
            **expected_key,
            "output": outputs["eval_output"],
            "parse_type": task["parse_type"],
            "expected_answer": packet_record["registered_reference_answer"],
            "eval_output_used": outputs["eval_output_used"],
            "raw_output": outputs["raw_output"],
            "stopped_output": outputs["stopped_output"],
            "postprocessed_output": outputs["postprocessed_output"],
            **dict(intervention),
            "phase1_branch": branch,
            **dict(stored_evaluation),
        }
        generations.append(generation)
        evaluations.append(evaluation)
    pairing_report, pairs = audit_pairing(generations, evaluations)
    _require_pass(pairing_report, "unblinded source reconstruction pairing")
    if len(pairs) != len(unblinded_records):
        raise SemanticAuditError("unblinded source reconstruction lost records")
    return generations, evaluations, [
        (key, dict(generation), dict(evaluation))
        for key, generation, evaluation in pairs
    ]


def enrich_final_adjudications(
    final_judgments: Sequence[Mapping[str, Any]],
    unblinded_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Join final judgments to restricted stored fields for audit comparisons."""
    judgment_index = {
        str(row["review_id"]): row for row in final_judgments
    }
    unblinded_index = {
        str(row["review_id"]): row for row in unblinded_records
    }
    if set(judgment_index) != set(unblinded_index):
        raise SemanticAuditError("final and unblinded review IDs do not match")
    enriched: list[dict[str, Any]] = []
    for review_id in sorted(judgment_index):
        judgment = judgment_index[review_id]
        packet = unblinded_index[review_id]
        stage1 = packet["stage1_record"]
        stored = packet["stored_evaluation_fields"]
        stored_ambiguous = stored.get("parse_ambiguous", _MISSING)
        stored_parsed = stored.get("parsed_answer", _MISSING)
        stored_correct = stored.get("correctness", _MISSING)
        parser_label = derive_parser_label(
            stored_ambiguous,
            str(judgment["semantic_category"]),
            str(judgment["answer_presence"]),
            str(judgment["answer_status"]),
        )
        consistency = parsed_answer_consistency(
            stored_parsed,
            str(judgment["semantic_category"]),
            judgment.get("best_answer"),
            str(judgment["answer_presence"]),
            str(judgment["answer_status"]),
        )
        material = material_evaluator_error(
            stored_correct,
            str(judgment["answer_status"]),
        )
        task = stage1["task"]
        branch = get_phase1_branch_metadata(str(task["condition"]))[
            "phase1_branch"
        ]
        semantic_parse_valid = judgment["answer_presence"] in {
            "answer_present",
            "ambiguous",
        }
        semantic_parse_ambiguous = (
            judgment["semantic_category"]
            == "true_multiple_candidate_ambiguity"
        )
        stored_parse_valid = stored.get("parse_valid", _MISSING)
        parse_valid_disagreement = (
            type(stored_parse_valid) is not bool
            or stored_parse_valid != semantic_parse_valid
        )
        parse_ambiguity_disagreement = (
            type(stored_ambiguous) is not bool
            or stored_ambiguous != semantic_parse_ambiguous
        )
        gate_measurement_error = (
            (
                branch in {"raw_strict", "stopped_intervention"}
                and parse_valid_disagreement
            )
            or (branch == "raw_strict" and parse_ambiguity_disagreement)
            or (
                task["condition"] == "visible_cot"
                and parse_valid_disagreement
            )
        )
        parser_metric_measurement_error = (
            parse_valid_disagreement or parse_ambiguity_disagreement
        )
        material_evaluator = (
            None
            if _is_inconclusive(judgment) or parser_label == "not_assessable"
            else bool(material) or parser_metric_measurement_error
        )
        record = {
            "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
            "review_id": review_id,
            "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "depth": task["depth"],
            "condition": task["condition"],
            "branch": branch,
            "eval_output_used": stage1["outputs"]["eval_output_used"],
            "adjudication_source": judgment["adjudication_source"],
            "adjudicator_id": judgment["adjudicator_id"],
            "semantic_category": judgment["semantic_category"],
            "answer_presence": judgment["answer_presence"],
            "answer_status": judgment["answer_status"],
            "best_answer": judgment["best_answer"],
            "issue_tags": sorted(judgment["issue_tags"]),
            "confidence": judgment["confidence"],
            "derived_parser_label": parser_label,
            "parsed_answer_consistency": consistency,
            "stored_parse_ambiguous": (
                stored_ambiguous if stored_ambiguous is not _MISSING else None
            ),
            "stored_parse_ambiguous_state": (
                "missing"
                if stored_ambiguous is _MISSING
                else "valid"
                if type(stored_ambiguous) is bool
                else "invalid"
            ),
            "stored_parse_valid": (
                stored_parse_valid if stored_parse_valid is not _MISSING else None
            ),
            "stored_parse_valid_state": (
                "missing"
                if stored_parse_valid is _MISSING
                else "valid"
                if type(stored_parse_valid) is bool
                else "invalid"
            ),
            "stored_parsed_answer": (
                stored_parsed if stored_parsed is not _MISSING else None
            ),
            "stored_parsed_answer_state": (
                "missing"
                if stored_parsed is _MISSING
                else "null"
                if stored_parsed is None
                else "value"
                if isinstance(stored_parsed, str)
                else "invalid"
            ),
            "stored_correctness": (
                stored_correct if stored_correct is not _MISSING else None
            ),
            "stored_correctness_state": _stored_correctness_state(stored),
            "material_correctness_error": material,
            "potential_branch_gate_measurement_error": gate_measurement_error,
            "material_parser_metric_error": parser_metric_measurement_error,
            "material_evaluator_error": material_evaluator,
            "judgment_target": "selected_eval_output_only",
        }
        canonical_json_text(record)
        enriched.append(record)
    return enriched


def _apply_semantic_judgments_to_pairs(
    pairs: Sequence[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]],
    final_records: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]],
]:
    final_by_task_key = {
        (
            row["experimental_target_model_id"],
            row["task_family"],
            row["depth"],
            row["condition"],
            row["task_id"],
        ): row
        for row in final_records
    }
    generations: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    alternative_pairs: list[
        tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]
    ] = []
    for key, source_generation, source_evaluation in pairs:
        if key not in final_by_task_key:
            raise SemanticAuditError("final adjudication is missing a paired source key")
        final = final_by_task_key[key]
        if _is_unresolved(final):
            raise SemanticAuditError(
                "audit-only alternative metrics require zero unresolved judgments"
            )
        generation = deepcopy(source_generation)
        evaluation = deepcopy(source_evaluation)
        status = str(final["answer_status"])
        semantic_correctness = status == "correct"
        semantic_ambiguity = (
            final["semantic_category"] == "true_multiple_candidate_ambiguity"
        )
        semantic_parse_valid = final["answer_presence"] in {
            "answer_present",
            "ambiguous",
        }
        evaluation.update(
            {
                "parsed_answer": final["best_answer"],
                "parse_valid": semantic_parse_valid,
                "parse_ambiguous": semantic_ambiguity,
                "correctness": semantic_correctness,
                "eval_correctness": semantic_correctness,
            }
        )
        generation.update(
            {
                "parsed_answer": final["best_answer"],
                "parse_valid": semantic_parse_valid,
                "parse_ambiguous": semantic_ambiguity,
                "correct": semantic_correctness,
                "eval_correct": semantic_correctness,
                "eval_correctness": semantic_correctness,
            }
        )
        selected = evaluation["eval_output_used"]
        if selected == "raw":
            evaluation["raw_correctness"] = semantic_correctness
            generation["raw_correctness"] = semantic_correctness
            generation["raw_correct"] = semantic_correctness
        elif selected == "stopped":
            evaluation["stopped_correctness"] = semantic_correctness
            generation["stopped_correctness"] = semantic_correctness
            generation["stopped_correct"] = semantic_correctness
        elif selected == "postprocessed":
            evaluation["postprocessed_correctness"] = semantic_correctness
            generation["postprocessed_correctness"] = semantic_correctness
            generation["postprocessed_correct"] = semantic_correctness
        else:
            raise SemanticAuditError(f"invalid selected output: {selected}")
        generations.append(generation)
        evaluations.append(evaluation)
        alternative_pairs.append((key, generation, evaluation))
    return generations, evaluations, alternative_pairs


def compute_audit_only_alternatives(
    unblinded_records: Sequence[Mapping[str, Any]],
    final_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Recompute stored and semantic sensitivity rows without mutating either."""
    source_generations, _, source_pairs = _source_copies_from_unblinded(
        unblinded_records
    )
    stored_metric_rows, stored_latency_limitations = recompute_metric_rows(
        source_pairs
    )
    stored_classifications = recompute_branch_classifications(
        stored_metric_rows, source_generations
    )
    alternative_generations, _, alternative_pairs = (
        _apply_semantic_judgments_to_pairs(source_pairs, final_records)
    )
    alternative_metric_rows, alternative_latency_limitations = (
        recompute_metric_rows(alternative_pairs)
    )
    alternative_classifications = recompute_branch_classifications(
        alternative_metric_rows, alternative_generations
    )
    return {
        "estimate_label": (
            "audit-only semantic alternative estimate: post hoc, noncanonical "
            "sensitivity estimate"
        ),
        "stored_recomputed_metric_rows": stored_metric_rows,
        "audit_only_semantic_alternative_metric_rows": alternative_metric_rows,
        "stored_recomputed_classifications": stored_classifications,
        "audit_only_semantic_alternative_classifications": (
            alternative_classifications
        ),
        "stored_latency_limitations": stored_latency_limitations,
        "alternative_latency_limitations": alternative_latency_limitations,
        "selected_eval_output_only": True,
        "auxiliary_outputs_independently_rescored": False,
    }


def _metric_row_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["model"]),
        str(row["task_family"]),
        str(row["depth"]),
        str(row["condition"]),
    )


def _classification_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["model"]),
        str(row["task_family"]),
        str(row["depth"]),
        str(row["condition"]),
    )


def _breakdown_counts(
    rows: Sequence[Mapping[str, Any]], field: str, predicate
) -> dict[str, int]:
    result: Counter[str] = Counter({str(row[field]): 0 for row in rows})
    for row in rows:
        if predicate(row):
            result[str(row[field])] += 1
    return dict(sorted(result.items()))


def _three_way_breakdowns(
    rows: Sequence[Mapping[str, Any]], predicate
) -> dict[str, dict[str, int]]:
    return {
        "by_condition": _breakdown_counts(rows, "condition", predicate),
        "by_branch": _breakdown_counts(rows, "branch", predicate),
        "by_depth": _breakdown_counts(rows, "depth", predicate),
    }


def build_material_impact_report(
    final_records: Sequence[Mapping[str, Any]],
    alternatives: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Separate parser risks, observed extraction errors, and metric-changing errors."""
    last_number_ids = [
        str(row["review_id"])
        for row in final_records
        if "last_number_selection_risk" in row["issue_tags"]
    ]
    extraction_ids = [
        str(row["review_id"])
        for row in final_records
        if row["parsed_answer_consistency"]
        in {
            "stored_differs_from_semantic_best",
            "stored_answer_semantic_no_answer",
            "stored_no_answer_semantic_answer",
        }
    ]
    material_ids = [
        str(row["review_id"])
        for row in final_records
        if row["material_evaluator_error"] is True
    ]
    material_correctness_ids = [
        str(row["review_id"])
        for row in final_records
        if row.get("material_correctness_error") is True
    ]
    unresolved_ids = [
        str(row["review_id"])
        for row in final_records
        if row["material_evaluator_error"] is None or _is_unresolved(row)
    ]

    metric_changes: list[dict[str, Any]] = []
    classification_changes: list[dict[str, Any]] = []
    if alternatives is not None:
        stored_metrics = {
            _metric_row_key(row): row
            for row in alternatives["stored_recomputed_metric_rows"]
        }
        alternative_metrics = {
            _metric_row_key(row): row
            for row in alternatives[
                "audit_only_semantic_alternative_metric_rows"
            ]
        }
        for key in sorted(stored_metrics):
            stored = stored_metrics[key]
            alternative = alternative_metrics[key]
            changed_fields = [
                field
                for field in (
                    "accuracy",
                    "eval_accuracy",
                    "parse_valid_rate",
                    "parse_ambiguous_rate",
                    "accuracy_raw",
                    "accuracy_stopped",
                    "accuracy_postprocessed",
                )
                if stored.get(field) != alternative.get(field)
            ]
            if changed_fields:
                metric_changes.append(
                    {
                        "cell": {
                            "model": key[0],
                            "task_family": key[1],
                            "depth": key[2],
                            "condition": key[3],
                        },
                        "changed_fields": changed_fields,
                        "stored_recomputed": {
                            field: stored.get(field) for field in changed_fields
                        },
                        "audit_only_semantic_alternative": {
                            field: alternative.get(field)
                            for field in changed_fields
                        },
                    }
                )
        stored_classes = {
            _classification_key(row): row
            for row in alternatives["stored_recomputed_classifications"]
        }
        alternative_classes = {
            _classification_key(row): row
            for row in alternatives[
                "audit_only_semantic_alternative_classifications"
            ]
        }
        for key in sorted(stored_classes):
            stored = stored_classes[key]
            alternative = alternative_classes[key]
            changed_fields = [
                field
                for field in (
                    "classification",
                    "absolute_accuracy_passed",
                    "visible_cot_baseline_valid",
                    "relative_accuracy_gate",
                )
                if stored.get(field) != alternative.get(field)
            ]
            if changed_fields:
                classification_changes.append(
                    {
                        "cell": {
                            "model": key[0],
                            "task_family": key[1],
                            "depth": key[2],
                            "condition": key[3],
                        },
                        "changed_fields": changed_fields,
                        "stored_recomputed": {
                            field: stored.get(field) for field in changed_fields
                        },
                        "audit_only_semantic_alternative": {
                            field: alternative.get(field)
                            for field in changed_fields
                        },
                    }
                )

    risk_predicate = lambda row: "last_number_selection_risk" in row["issue_tags"]
    extraction_predicate = lambda row: row["parsed_answer_consistency"] in {
        "stored_differs_from_semantic_best",
        "stored_answer_semantic_no_answer",
        "stored_no_answer_semantic_answer",
    }
    material_correctness_predicate = (
        lambda row: row.get("material_correctness_error") is True
    )
    material_predicate = lambda row: row["material_evaluator_error"] is True
    return {
        "schema_version": SEMANTIC_AUDIT_SCHEMA_VERSION,
        "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
        "definition": (
            "A material evaluator error is a stored-versus-semantic disagreement "
            "that could change correctness, condition-depth accuracy, a branch "
            "absolute or relative gate, visible-CoT baseline validity, or branch "
            "classification."
        ),
        "distinctions": {
            "last_number_risk_tag": {
                "meaning": "Prospective extraction risk; not itself an observed error.",
                "count": len(last_number_ids),
                "review_ids": last_number_ids,
            },
            "observed_extraction_error": {
                "meaning": (
                    "Observed selected-span or answer-presence disagreement; not "
                    "automatically metric-changing."
                ),
                "count": len(extraction_ids),
                "review_ids": extraction_ids,
            },
            "material_correctness_error": {
                "meaning": "A disagreement that changes selected-output correctness.",
                "count": len(material_correctness_ids),
                "review_ids": material_correctness_ids,
            },
            "material_metric_changing_issue": {
                "meaning": (
                    "A correctness or parser-measurement disagreement that could "
                    "change a preregistered metric, gate, baseline, or classification."
                ),
                "count": len(material_ids),
                "review_ids": material_ids,
            },
        },
        "unresolved_review_ids": unresolved_ids,
        "full_metric_comparison_available": not unresolved_ids,
        "material_breakdowns": {
            "last_number_selection_risk": _three_way_breakdowns(
                final_records, risk_predicate
            ),
            "observed_extraction_error": _three_way_breakdowns(
                final_records, extraction_predicate
            ),
            "material_correctness_error": _three_way_breakdowns(
                final_records, material_correctness_predicate
            ),
            "material_evaluator_error": _three_way_breakdowns(
                final_records, material_predicate
            ),
        },
        "condition_depth_metric_changes": metric_changes,
        "branch_or_baseline_classification_changes": classification_changes,
        "audit_only_semantic_alternative_classifications": (
            None
            if alternatives is None
            else alternatives[
                "audit_only_semantic_alternative_classifications"
            ]
        ),
        "official_stored_metrics_or_classifications_modified": False,
        "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
    }


def render_semantic_audit_metrics_csv(
    final_records: Sequence[Mapping[str, Any]],
    alternatives: Mapping[str, Any] | None,
) -> bytes:
    """Render condition-depth audit-only sensitivity rows with LF endings."""
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in final_records:
        grouped[
            (
                str(row["depth"]),
                str(row["condition"]),
                str(row["branch"]),
            )
        ].append(row)
    stored_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    alternative_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    if alternatives is not None:
        stored_by_key = {
            (str(row["depth"]), str(row["condition"])): row
            for row in alternatives["stored_recomputed_metric_rows"]
        }
        alternative_by_key = {
            (str(row["depth"]), str(row["condition"])): row
            for row in alternatives[
                "audit_only_semantic_alternative_metric_rows"
            ]
        }
    fieldnames = [
        "estimate_label",
        "experimental_target_model_id",
        "task_family",
        "depth",
        "condition",
        "branch",
        "n",
        "semantic_correct",
        "semantic_incorrect",
        "semantic_no_answer",
        "semantic_ambiguous",
        "semantic_inconclusive",
        "stored_recomputed_accuracy",
        "audit_only_semantic_alternative_accuracy",
        "accuracy_delta",
        "audit_only_parse_valid_rate",
        "audit_only_parse_ambiguous_rate",
        "audit_only_accuracy_raw",
        "audit_only_accuracy_stopped",
        "audit_only_accuracy_postprocessed",
        "full_metrics_available",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for (depth, condition, branch), records in sorted(grouped.items()):
        statuses = Counter(
            "inconclusive" if _is_inconclusive(row) else str(row["answer_status"])
            for row in records
        )
        key = (depth, condition)
        stored = stored_by_key.get(key)
        alternative = alternative_by_key.get(key)
        stored_accuracy = None if stored is None else stored.get("accuracy")
        alternative_accuracy = (
            None if alternative is None else alternative.get("accuracy")
        )
        delta = "NA"
        try:
            if (
                stored_accuracy is not None
                and alternative_accuracy is not None
                and str(stored_accuracy).upper() != "NA"
                and str(alternative_accuracy).upper() != "NA"
            ):
                delta = f"{float(alternative_accuracy) - float(stored_accuracy):.4f}"
        except (TypeError, ValueError):
            delta = "NA"
        writer.writerow(
            {
                "estimate_label": (
                    "audit-only semantic alternative estimate; post hoc; "
                    "noncanonical sensitivity estimate"
                ),
                "experimental_target_model_id": EXPERIMENTAL_TARGET_MODEL_ID,
                "task_family": "arithmetic",
                "depth": depth,
                "condition": condition,
                "branch": branch,
                "n": len(records),
                "semantic_correct": statuses["correct"],
                "semantic_incorrect": statuses["incorrect"],
                "semantic_no_answer": statuses["no_answer"],
                "semantic_ambiguous": statuses["ambiguous"],
                "semantic_inconclusive": statuses["inconclusive"],
                "stored_recomputed_accuracy": (
                    "NA" if stored_accuracy is None else stored_accuracy
                ),
                "audit_only_semantic_alternative_accuracy": (
                    "NA" if alternative_accuracy is None else alternative_accuracy
                ),
                "accuracy_delta": delta,
                "audit_only_parse_valid_rate": (
                    "NA" if alternative is None else alternative["parse_valid_rate"]
                ),
                "audit_only_parse_ambiguous_rate": (
                    "NA"
                    if alternative is None
                    else alternative["parse_ambiguous_rate"]
                ),
                "audit_only_accuracy_raw": (
                    "NA" if alternative is None else alternative["accuracy_raw"]
                ),
                "audit_only_accuracy_stopped": (
                    "NA"
                    if alternative is None
                    else alternative["accuracy_stopped"]
                ),
                "audit_only_accuracy_postprocessed": (
                    "NA"
                    if alternative is None
                    else alternative["accuracy_postprocessed"]
                ),
                "full_metrics_available": str(alternatives is not None).lower(),
            }
        )
    return output.getvalue().encode("utf-8")


def parse_json_object_strict(data: bytes, artifact_name: str) -> dict[str, Any]:
    """Parse one UTF-8 JSON object with duplicate/non-finite rejection."""
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, SemanticAuditError) as exc:
        raise SemanticAuditError(f"{artifact_name} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SemanticAuditError(f"{artifact_name} must contain one JSON object")
    _validate_json_value(value)
    return value


def validate_review_pack(
    manifest: Mapping[str, Any],
    packet_bytes: Mapping[str, bytes],
) -> dict[str, list[dict[str, Any]]]:
    """Validate packet hashes, counts, IDs, schemas, target, and stage-1 blinding."""
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise SemanticAuditError("review manifest protocol version mismatch")
    provenance = validate_protocol_provenance_record(
        manifest.get("protocol_provenance", {})
    )
    if provenance["verification_mode"] not in {
        "local_git_and_bundle",
        "baked_image_attestation",
    }:
        raise SemanticAuditError("review manifest provenance is test-only")
    if (
        manifest.get("protocol_commit") != provenance["protocol_commit"]
        or manifest.get("protocol_bundle_sha256")
        != provenance["protocol_bundle_sha256"]
    ):
        raise SemanticAuditError("review manifest protocol provenance mismatch")
    if (
        manifest.get("audit_schema_version") != SEMANTIC_AUDIT_SCHEMA_VERSION
        or manifest.get("protocol_version") != PROTOCOL_VERSION
        or manifest.get("protocol_path")
        != "docs/phase1_semantic_review_protocol.md"
        or manifest.get("experimental_target_model_id")
        != EXPERIMENTAL_TARGET_MODEL_ID
    ):
        raise SemanticAuditError("review manifest experimental target mismatch")
    if manifest.get("source_writer_commit") != SOURCE_WRITER_COMMIT:
        raise SemanticAuditError("review manifest writer commit mismatch")
    source_prefix_value = manifest.get("source_prefix")
    if not isinstance(source_prefix_value, str):
        raise SemanticAuditError("review manifest source prefix is missing")
    source_prefix = normalize_blob_prefix(source_prefix_value)
    output_prefix = manifest.get("output_prefix")
    if output_prefix is not None:
        if not isinstance(output_prefix, str):
            raise SemanticAuditError("review manifest output prefix is invalid")
        validate_semantic_audit_prefixes(source_prefix, output_prefix)
    if manifest.get("mandatory_boundary") != MANDATORY_BOUNDARY_TEXT:
        raise SemanticAuditError("review manifest mandatory boundary mismatch")
    _require_exact_int(
        manifest.get("expected_record_count"),
        EXPECTED_RECORD_COUNT,
        "review manifest expected_record_count",
    )
    depths = manifest.get("depths")
    if (
        not isinstance(depths, list)
        or len(depths) != 3
        or any(type(value) is not int for value in depths)
        or depths != [1, 2, 3]
    ):
        raise SemanticAuditError("review manifest depth bindings are invalid")
    validation = manifest.get("validation")
    if not isinstance(validation, Mapping) or not validation:
        raise SemanticAuditError("review manifest validation summary is missing")
    for name, summary in validation.items():
        if (
            not isinstance(name, str)
            or not isinstance(summary, Mapping)
            or summary.get("result") != "PASS"
        ):
            raise SemanticAuditError("review manifest validation summary is invalid")
        _require_exact_int(
            summary.get("records_checked"),
            EXPECTED_RECORD_COUNT,
            f"review validation count for {name}",
        )
    if manifest.get("model_inference_performed") is not False:
        raise SemanticAuditError("review manifest inference boundary mismatch")
    if manifest.get("new_behavioral_observations_generated") is not False:
        raise SemanticAuditError("review manifest observation boundary mismatch")
    if manifest.get("new_observations_generated") is not False:
        raise SemanticAuditError("review manifest new-observation boundary mismatch")
    reviewer = manifest.get("reviewer")
    if not isinstance(reviewer, Mapping) or (
        reviewer.get("model_id"),
        reviewer.get("reasoning_effort"),
    ) != (REVIEWER_MODEL_ID, REVIEWER_REASONING_EFFORT):
        raise SemanticAuditError("review manifest reviewer identity mismatch")
    if manifest.get("source_evidence_mode") != VERIFIED_SOURCE_EVIDENCE_MODE:
        raise SemanticAuditError(
            "review manifest requires verified_source_bytes evidence"
        )
    _validate_recorded_source_evidence_binding(
        manifest.get("source_artifacts"),
        manifest.get("source_immutability"),
        manifest.get("source_evidence_sha256"),
    )
    packet_manifest = manifest.get("packet_files")
    if not isinstance(packet_manifest, Mapping):
        raise SemanticAuditError("review manifest lacks packet_files")
    if set(packet_bytes) != set(PACKET_FILENAMES):
        raise SemanticAuditError(
            "private review pack must contain exactly the two staged packet files"
        )

    parsed: dict[str, list[dict[str, Any]]] = {}
    for name in PACKET_FILENAMES:
        metadata = packet_manifest.get(name)
        if not isinstance(metadata, Mapping):
            raise SemanticAuditError(f"manifest lacks metadata for {name}")
        data = packet_bytes[name]
        if sha256_bytes(data) != metadata.get("sha256"):
            raise SemanticAuditError(f"{name} SHA-256 mismatch")
        records = parse_jsonl_strict(data, name)
        if canonical_jsonl_bytes(records) != data:
            raise SemanticAuditError(f"{name} is not canonically serialized")
        if type(metadata.get("record_count")) is not int:
            raise SemanticAuditError(f"{name} record_count must be an integer")
        if len(records) != metadata.get("record_count"):
            raise SemanticAuditError(f"{name} count differs from manifest")
        if len(records) != EXPECTED_RECORD_COUNT:
            raise SemanticAuditError(f"{name} must contain exactly 45 rows")
        ids = [str(row.get("review_id")) for row in records]
        if ids != expected_review_ids():
            raise SemanticAuditError(f"{name} IDs must be exactly R001-R045 in order")
        if any(
            row.get("experimental_target_model_id")
            != EXPERIMENTAL_TARGET_MODEL_ID
            for row in records
        ):
            raise SemanticAuditError(f"{name} contains a wrong target model ID")
        parsed[name] = records

    for record in parsed[PACKET_FILENAMES[0]]:
        if record.get("schema_version") != STAGE1_SCHEMA_VERSION:
            raise SemanticAuditError("stage-1 schema version mismatch")
        validate_blinded_record(record)
    stage1_index = {
        row["review_id"]: row for row in parsed[PACKET_FILENAMES[0]]
    }
    stage2_index = {
        row["review_id"]: row for row in parsed[PACKET_FILENAMES[1]]
    }
    for stage2 in parsed[PACKET_FILENAMES[1]]:
        if set(stage2) != set(STAGE2_FIELDS):
            raise SemanticAuditError("stage-2 record violates its strict allowlist")
        if stage2.get("schema_version") != STAGE2_SCHEMA_VERSION:
            raise SemanticAuditError("stage-2 schema version mismatch")
        normalize_numeric_answer(stage2["registered_reference_answer"])
    registry = _registered_arithmetic_registry()
    mapping_keys: list[tuple[Any, ...]] = []
    mapping_by_key: dict[tuple[Any, ...], str] = {}
    for review_id, stage1 in stage1_index.items():
        task = stage1["task"]
        key = (
            EXPERIMENTAL_TARGET_MODEL_ID,
            task.get("task_family"),
            task.get("depth"),
            task.get("condition"),
            task.get("task_id"),
        )
        try:
            record_key(_pairing_key_dict(key))
        except AuditInputError as exc:
            raise SemanticAuditError(
                f"{review_id} has an invalid typed pairing key: {exc}"
            ) from exc
        mapping_keys.append(key)
        mapping_by_key[key] = review_id
        item = registry.get(str(task.get("task_id")))
        stage2 = stage2_index[review_id]
        if item is None or {
            "task_family": task.get("task_family"),
            "depth": task.get("depth"),
            "question": task.get("question"),
            "parse_type": task.get("parse_type"),
            "registered_reference_answer": stage2.get(
                "registered_reference_answer"
            ),
        } != {
            "task_family": item["task_family"],
            "depth": item["depth"],
            "question": item["prompt_base"],
            "parse_type": item["parse_type"],
            "registered_reference_answer": item["expected_answer"],
        }:
            raise SemanticAuditError(
                f"{review_id} differs from the writer-commit-pinned registry"
            )
    shuffle = manifest.get("shuffle")
    if not isinstance(shuffle, Mapping):
        raise SemanticAuditError("review manifest lacks shuffle provenance")
    if shuffle.get("hash_domain") != SHUFFLE_HASH_DOMAIN.decode("ascii").rstrip(
        "\0"
    ):
        raise SemanticAuditError("review manifest shuffle domain mismatch")
    _require_exact_int(
        shuffle.get("seed"), FROZEN_SHUFFLE_SEED, "review manifest shuffle seed"
    )
    if set(mapping_keys) != set(expected_record_keys()):
        raise SemanticAuditError("review packet membership is not the exact all-45 design")
    recomputed_mapping, mapping_hash = deterministic_review_mapping(
        mapping_keys, seed=FROZEN_SHUFFLE_SEED
    )
    if recomputed_mapping != mapping_by_key:
        raise SemanticAuditError("review ID mapping does not match the frozen shuffle")
    if mapping_hash != shuffle.get("mapping_sha256"):
        raise SemanticAuditError("review mapping SHA-256 mismatch")
    return parsed


def validate_stage_release(
    manifest: Mapping[str, Any],
    packet_bytes: Mapping[str, bytes],
    *,
    expected_stage: str,
    stage1_release_files: Mapping[str, bytes] | None = None,
    stage1_submission_artifacts: Sequence[tuple[bytes, bytes]] = (),
) -> list[dict[str, Any]]:
    """Validate one manifest-last release without accepting co-released packets."""
    if expected_stage not in {"stage1", "stage2"}:
        raise SemanticAuditError("expected_stage must be stage1 or stage2")
    if set(manifest) != set(RELEASE_MANIFEST_FIELDS):
        raise SemanticAuditError("release manifest fields must match the exact schema")
    if (
        manifest.get("release_manifest_schema_version")
        != RELEASE_MANIFEST_SCHEMA_VERSION
        or manifest.get("release_stage") != expected_stage
        or manifest.get("release_complete") is not True
        or manifest.get("manifest_uploaded_last") is not True
    ):
        raise SemanticAuditError("release manifest stage/marker mismatch")
    provenance = validate_protocol_provenance_record(
        manifest.get("protocol_provenance", {})
    )
    if provenance["verification_mode"] not in {
        "local_git_and_bundle",
        "baked_image_attestation",
    }:
        raise SemanticAuditError("release protocol provenance is test-only")
    if (
        manifest.get("protocol_commit") != provenance["protocol_commit"]
        or manifest.get("protocol_bundle_sha256")
        != provenance["protocol_bundle_sha256"]
    ):
        raise SemanticAuditError("release protocol provenance mismatch")
    if (
        manifest.get("audit_schema_version") != SEMANTIC_AUDIT_SCHEMA_VERSION
        or manifest.get("protocol_version") != PROTOCOL_VERSION
        or manifest.get("protocol_path")
        != "docs/phase1_semantic_review_protocol.md"
        or manifest.get("experimental_target_model_id")
        != EXPERIMENTAL_TARGET_MODEL_ID
        or manifest.get("source_writer_commit") != SOURCE_WRITER_COMMIT
        or manifest.get("mandatory_boundary") != MANDATORY_BOUNDARY_TEXT
        or manifest.get("model_inference_performed") is not False
        or manifest.get("new_observations_generated") is not False
        or manifest.get("new_behavioral_observations_generated") is not False
        or manifest.get("source_artifacts_modified") is not False
        or manifest.get(
            "official_stored_metrics_or_classifications_modified"
        )
        is not False
        or manifest.get("task_family") != "arithmetic"
        or manifest.get("registered_conditions")
        != sorted({key[3] for key in expected_record_keys()})
    ):
        raise SemanticAuditError("release manifest scientific boundary mismatch")
    _require_exact_int(
        manifest.get("expected_record_count"),
        EXPECTED_RECORD_COUNT,
        "release expected_record_count",
    )
    depths = manifest.get("depths")
    if (
        not isinstance(depths, list)
        or len(depths) != 3
        or any(type(value) is not int for value in depths)
        or depths != [1, 2, 3]
    ):
        raise SemanticAuditError("release depth bindings must be exact integers")
    reviewer = manifest.get("reviewer")
    if (
        not isinstance(reviewer, Mapping)
        or set(reviewer) != {"model_id", "reasoning_effort", "role"}
        or (
            reviewer.get("model_id"),
            reviewer.get("reasoning_effort"),
            reviewer.get("role"),
        )
        != (
            REVIEWER_MODEL_ID,
            REVIEWER_REASONING_EFFORT,
            "engineering_audit_only",
        )
    ):
        raise SemanticAuditError("release manifest reviewer model binding mismatch")
    if manifest.get("source_evidence_mode") != VERIFIED_SOURCE_EVIDENCE_MODE:
        raise SemanticAuditError(
            "release requires verified_source_bytes source evidence"
        )
    _validate_recorded_source_evidence_binding(
        manifest.get("source_artifacts"),
        manifest.get("source_immutability"),
        manifest.get("source_evidence_sha256"),
    )
    source_prefix = manifest.get("source_prefix")
    output_prefix = manifest.get("output_prefix")
    if not isinstance(source_prefix, str) or not isinstance(output_prefix, str):
        raise SemanticAuditError("release prefixes are missing")
    validate_semantic_audit_prefixes(source_prefix, output_prefix)
    shuffle = manifest.get("shuffle")
    if (
        not isinstance(shuffle, Mapping)
        or set(shuffle)
        != {"seed", "hash_domain", "algorithm", "mapping_sha256"}
        or shuffle.get("hash_domain")
        != SHUFFLE_HASH_DOMAIN.decode("ascii").rstrip("\0")
        or shuffle.get("algorithm") != SHUFFLE_ALGORITHM
    ):
        raise SemanticAuditError("release shuffle provenance mismatch")
    _require_exact_int(
        shuffle.get("seed"), FROZEN_SHUFFLE_SEED, "release shuffle seed"
    )

    packet_name = (
        STAGE1_PACKET_FILENAME if expected_stage == "stage1" else STAGE2_PACKET_FILENAME
    )
    if set(packet_bytes) != {RELEASE_RESERVATION_FILENAME, packet_name}:
        raise SemanticAuditError(
            f"{expected_stage} release must contain only its reservation and packet"
        )
    reservation = manifest.get("reservation")
    reservation_bytes = packet_bytes[RELEASE_RESERVATION_FILENAME]
    expected_reservation_bytes = _release_reservation_bytes(
        expected_stage, str(manifest.get("output_prefix", ""))
    )
    if (
        not isinstance(reservation, Mapping)
        or set(reservation)
        != {"filename", "schema_version", "state", "sha256"}
        or reservation.get("filename") != RELEASE_RESERVATION_FILENAME
        or reservation.get("schema_version") != RELEASE_RESERVATION_SCHEMA_VERSION
        or reservation.get("state") != "immutable_exclusive_reservation"
        or reservation.get("sha256") != sha256_bytes(reservation_bytes)
        or reservation_bytes != expected_reservation_bytes
    ):
        raise SemanticAuditError("release reservation binding mismatch")
    packet_manifest = manifest.get("packet_files")
    if not isinstance(packet_manifest, Mapping) or set(packet_manifest) != {
        packet_name
    }:
        raise SemanticAuditError("release manifest lists a forbidden packet set")
    if RESTRICTED_PACKET_FILENAME in canonical_json_text(dict(manifest)):
        raise SemanticAuditError("restricted packet must never appear in a release")
    metadata = packet_manifest[packet_name]
    data = packet_bytes[packet_name]
    if (
        not isinstance(metadata, Mapping)
        or set(metadata) != set(PACKET_METADATA_FIELDS)
        or sha256_bytes(data) != metadata.get("sha256")
    ):
        raise SemanticAuditError("release packet hash mismatch")
    if metadata.get("canonical_json") != (
        "ensure_ascii=true,sort_keys=true,separators=(',',':'),"
        "allow_nan=false,LF"
    ):
        raise SemanticAuditError("release packet canonicalization contract mismatch")
    records = parse_jsonl_strict(data, packet_name)
    if canonical_jsonl_bytes(records) != data:
        raise SemanticAuditError("release packet is not canonically serialized")
    if (
        len(records) != EXPECTED_RECORD_COUNT
        or [str(row.get("review_id")) for row in records] != expected_review_ids()
    ):
        raise SemanticAuditError("release packet IDs/count must be exactly R001-R045")
    _require_exact_int(
        metadata.get("record_count"),
        EXPECTED_RECORD_COUNT,
        "release packet record_count",
    )
    if any(
        row.get("experimental_target_model_id") != EXPERIMENTAL_TARGET_MODEL_ID
        for row in records
    ):
        raise SemanticAuditError("release packet target model mismatch")

    if expected_stage == "stage1":
        if (
            manifest.get("stage1_gate") is not None
            or stage1_submission_artifacts
            or stage1_release_files is not None
        ):
            raise SemanticAuditError("Stage-1 release cannot claim a Stage-1 gate")
        registry = _registered_arithmetic_registry()
        mapping_keys: list[tuple[Any, ...]] = []
        mapping_by_key: dict[tuple[Any, ...], str] = {}
        for row in records:
            validate_blinded_record(row)
            task = row["task"]
            item = registry.get(str(task.get("task_id")))
            if item is None or {
                "task_family": task.get("task_family"),
                "depth": task.get("depth"),
                "question": task.get("question"),
                "parse_type": task.get("parse_type"),
            } != {
                "task_family": item["task_family"],
                "depth": item["depth"],
                "question": item["prompt_base"],
                "parse_type": item["parse_type"],
            }:
                raise SemanticAuditError(
                    f"{row['review_id']} Stage-1 question registry mismatch"
                )
            key = (
                EXPERIMENTAL_TARGET_MODEL_ID,
                task["task_family"],
                task["depth"],
                task["condition"],
                task["task_id"],
            )
            mapping_keys.append(key)
            mapping_by_key[key] = str(row["review_id"])
        if set(mapping_keys) != set(expected_record_keys()):
            raise SemanticAuditError("Stage-1 release membership is not all-45")
        mapping, mapping_hash = deterministic_review_mapping(mapping_keys)
        if (
            mapping != mapping_by_key
            or mapping_hash != shuffle.get("mapping_sha256")
        ):
            raise SemanticAuditError("Stage-1 release mapping mismatch")
    else:
        if stage1_release_files is None or len(stage1_submission_artifacts) != 2:
            raise SemanticAuditError(
                "Stage-2 validation requires the Stage-1 release bytes and two seals"
            )
        validated_release = validate_stage_release_files(
            stage1_release_files, expected_stage="stage1"
        )
        stage1_manifest = validated_release["manifest"]
        stage1_records = validated_release["records"]
        stage1_packet_sha256 = sha256_bytes(validated_release["packet_bytes"])
        stage1_release_manifest_sha256 = sha256_bytes(
            validated_release["manifest_bytes"]
        )
        _validate_release_chain_common_fields(stage1_manifest, manifest)
        if [str(row.get("review_id")) for row in stage1_records] != expected_review_ids():
            raise SemanticAuditError("validated Stage-1 records are incomplete")
        validated_stage1 = [
            validate_submission_artifact(
                submission_bytes,
                seal_bytes,
                expected_stage="stage1",
                expected_packet_sha256=stage1_packet_sha256,
            )
            for submission_bytes, seal_bytes in stage1_submission_artifacts
        ]
        ensure_distinct_reviewer_identities(*validated_stage1)
        expected_reviewer_bindings = [
            {
                "reviewer_id": submission.reviewer_id,
                "reviewer_model_id": submission.reviewer_model_id,
                "reviewer_reasoning_effort": submission.reviewer_reasoning_effort,
                "submission_sha256": submission.submission_sha256,
                "seal_sha256": sha256_bytes(seal_bytes),
            }
            for submission, (_, seal_bytes) in zip(
                validated_stage1, stage1_submission_artifacts
            )
        ]
        gate = manifest.get("stage1_gate")
        reviewers = gate.get("reviewers") if isinstance(gate, Mapping) else None
        if (
            not isinstance(gate, Mapping)
            or set(gate) != set(STAGE1_GATE_FIELDS)
            or gate.get("complete") is not True
            or gate.get("stage1_packet_sha256")
            != _validate_sha256(stage1_packet_sha256, "stage1_packet_sha256")
            or gate.get("stage1_release_manifest_sha256")
            != _validate_sha256(
                stage1_release_manifest_sha256,
                "stage1_release_manifest_sha256",
            )
            or not isinstance(reviewers, list)
            or reviewers != expected_reviewer_bindings
        ):
            raise SemanticAuditError("Stage-2 release lacks two distinct Stage-1 seals")
        for reviewer_binding in reviewers:
            if (
                not isinstance(reviewer_binding, Mapping)
                or set(reviewer_binding) != set(STAGE1_GATE_REVIEWER_FIELDS)
                or reviewer_binding.get("reviewer_model_id") != REVIEWER_MODEL_ID
                or reviewer_binding.get("reviewer_reasoning_effort")
                != REVIEWER_REASONING_EFFORT
            ):
                raise SemanticAuditError("Stage-1 release-gate identity mismatch")
            _validate_sha256(
                str(reviewer_binding.get("submission_sha256", "")),
                "stage1_submission_sha256",
            )
            _validate_sha256(
                str(reviewer_binding.get("seal_sha256", "")),
                "stage1_seal_sha256",
            )
        registry = _registered_arithmetic_registry()
        for first, second in zip(stage1_records, records):
            if set(second) != set(STAGE2_FIELDS) or second.get(
                "schema_version"
            ) != STAGE2_SCHEMA_VERSION:
                raise SemanticAuditError("Stage-2 release record schema mismatch")
            item = registry.get(str(first["task"]["task_id"]))
            if (
                first["review_id"] != second["review_id"]
                or item is None
                or second["registered_reference_answer"] != item["expected_answer"]
            ):
                raise SemanticAuditError("Stage-2 reference registry mismatch")
    return records


def validate_stage_release_files(
    files: Mapping[str, bytes],
    *,
    expected_stage: str,
    stage1_release_files: Mapping[str, bytes] | None = None,
    stage1_submission_artifacts: Sequence[tuple[bytes, bytes]] = (),
) -> dict[str, Any]:
    """Validate all and only the exact canonical bytes of one staged release."""
    if expected_stage not in {"stage1", "stage2"}:
        raise SemanticAuditError("expected_stage must be stage1 or stage2")
    packet_name = (
        STAGE1_PACKET_FILENAME
        if expected_stage == "stage1"
        else STAGE2_PACKET_FILENAME
    )
    manifest_name = RELEASE_MANIFEST_FILENAMES[expected_stage]
    expected_names = {
        RELEASE_RESERVATION_FILENAME,
        packet_name,
        manifest_name,
    }
    if not isinstance(files, Mapping):
        raise SemanticAuditError("release artifacts must be supplied as a mapping")
    exact_files = dict(files)
    if set(exact_files) != expected_names:
        raise SemanticAuditError(
            f"{expected_stage} release bytes must contain exactly its reservation, "
            "packet, and manifest"
        )
    if any(type(value) is not bytes for value in exact_files.values()):
        raise SemanticAuditError("release artifacts must be supplied as exact bytes")
    manifest_bytes = exact_files[manifest_name]
    manifest = parse_json_object_strict(manifest_bytes, manifest_name)
    if canonical_json_bytes(manifest) != manifest_bytes:
        raise SemanticAuditError("release manifest is not canonically serialized")
    packet_bytes = exact_files[packet_name]
    records = validate_stage_release(
        manifest,
        {
            RELEASE_RESERVATION_FILENAME: exact_files[
                RELEASE_RESERVATION_FILENAME
            ],
            packet_name: packet_bytes,
        },
        expected_stage=expected_stage,
        stage1_release_files=stage1_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
    )
    return {
        "files": exact_files,
        "manifest_name": manifest_name,
        "manifest_bytes": manifest_bytes,
        "manifest": manifest,
        "packet_name": packet_name,
        "packet_bytes": packet_bytes,
        "records": records,
    }


def build_final_machine_outputs(
    *,
    manifest_bytes: bytes,
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    arbiter: Sequence[Mapping[str, Any]],
    final_records: Sequence[Mapping[str, Any]],
    agreement: Mapping[str, Any],
    triggers: Sequence[Mapping[str, Any]],
    unblinded_records: Sequence[Mapping[str, Any]],
) -> dict[str, bytes]:
    """Build all required final files after trigger-complete arbitration."""
    if len(final_records) != EXPECTED_RECORD_COUNT:
        raise SemanticAuditError("final adjudication must contain exactly 45 records")
    if [str(row.get("review_id")) for row in final_records] != expected_review_ids():
        raise SemanticAuditError("final adjudication IDs must be exactly R001-R045")
    if any(
        row.get("experimental_target_model_id") != EXPERIMENTAL_TARGET_MODEL_ID
        for row in final_records
    ):
        raise SemanticAuditError("final adjudication target model mismatch")
    unresolved = [row["review_id"] for row in final_records if _is_unresolved(row)]
    alternatives = (
        None
        if unresolved
        else compute_audit_only_alternatives(unblinded_records, final_records)
    )
    ambiguity_report = build_ambiguity_confusion_report(final_records)
    correctness_table = build_correctness_confusion_table(final_records)
    material = build_material_impact_report(final_records, alternatives)
    material["reviewer_agreement"] = dict(agreement)
    material["arbitration"] = {
        "trigger_count": len(triggers),
        "trigger_ids": [trigger["review_id"] for trigger in triggers],
        "unresolved_count": len(unresolved),
        "unresolved_ids": unresolved,
        "full_metrics_require_zero_unresolved": True,
    }
    outputs = {
        REVIEW_MANIFEST_FILENAME: manifest_bytes,
        "all45_reviewer_a.jsonl": canonical_jsonl_bytes(reviewer_a),
        "all45_reviewer_b.jsonl": canonical_jsonl_bytes(reviewer_b),
        "all45_arbitration.jsonl": canonical_jsonl_bytes(arbiter),
        "all45_final_semantic_adjudication.jsonl": canonical_jsonl_bytes(
            final_records
        ),
        "all45_ambiguity_confusion_matrix.json": canonical_json_bytes(
            ambiguity_report
        ),
        "all45_correctness_confusion_matrix.json": canonical_json_bytes(
            correctness_table
        ),
        "all45_semantic_audit_metrics.csv": render_semantic_audit_metrics_csv(
            final_records, alternatives
        ),
        "all45_material_impact.json": canonical_json_bytes(material),
    }
    if set(outputs) != set(FINAL_MACHINE_FILENAMES):
        raise SemanticAuditError("internal final output filename mismatch")
    return outputs
