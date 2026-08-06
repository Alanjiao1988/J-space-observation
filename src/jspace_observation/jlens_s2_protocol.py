"""Model-free controls for the full-layer S2 and frozen S3-E0 round."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "jlens-s2-full-layer/v1"
CORPUS_CONTRACT_VERSION = "jlens-s2-corpus-source-contract/v1"
CORPUS_MANIFEST_VERSION = "jlens-s2-corpus-manifest/v1"
STARTING_COMMIT = "72336f822a8ffdbd2e0caf40f4a62c68cce68156"
STARTING_TREE = "d0592ae0b0edb62b4f082c0a12a9bcafe5693ee5"
AUTHORITY_PATH = "docs/prompts/jlens_s2_full_layer_and_s3_e0_execution_prompt.md"
AUTHORITY_SHA256 = (
    "4c982831bf5461f1b237ed0b6198f9cc1a6f36d330ca1960e7f8830a69b7f5ef"
)
DECISION_LOG_PREFIX_BYTES = 144_356
DECISION_LOG_PREFIX_SHA256 = (
    "e37299087788738009ad0264597c161fac536982869367916dc228cd744b3108"
)
EVIDENCE_LEDGER_PREFIX_BYTES = 21_347
EVIDENCE_LEDGER_PREFIX_SHA256 = (
    "16121192cf4ca0ee507a310356b0d9bb6cc7770323fa650867d8a4c65bb1bb85"
)

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
MODEL_DTYPE = "torch.float16"
MODEL_LAYERS = 28
MODEL_WIDTH = 1536
JLENS_REPOSITORY = "https://github.com/anthropics/jacobian-lens.git"
JLENS_COMMIT = "581d398613e5602a5af361e1c34d3a92ea82ba8e"
SOURCE_LAYERS = tuple(range(27))
TARGET_LAYER = 27
MAX_SEQ_LEN = 128
SKIP_FIRST = 16

ASSIGNMENT_SEED = "jlens-s2-wikitext-roles-2026-08-06"
ROLE_COUNTS = {"A": 600, "B": 600, "heldout": 200, "smoke": 2}
ROLE_ORDER = ("A", "B", "heldout", "smoke")
TOTAL_REGISTERED_ROWS = sum(ROLE_COUNTS.values())
CHECKPOINTS = (64, 128, 256, 600)
CHECKPOINT_INCREMENTS = (64, 64, 128, 344)
DIM_BATCH_CANDIDATES = (8, 4, 2, 1)

MERGE_MAX_ABS_TOLERANCE = 1e-5
MERGE_RELATIVE_FROBENIUS_TOLERANCE = 1e-6
DIM_BATCH_MAX_ABS_TOLERANCE = 1e-5
DIM_BATCH_RELATIVE_FROBENIUS_TOLERANCE = 1e-5
DIM_BATCH_COSINE_MINIMUM = 0.999999
PEAK_RESERVED_RATIO_MAXIMUM = 0.92
SAVE_LOAD_MAX_ABS_TOLERANCE = 0.0

CONTAINER_TIMEOUT_SECONDS = 7200
PLANNER_EXPORT_RESERVE_SECONDS = 900
PLANNER_SAFETY_FACTOR = 0.70

S3_PROTOCOL_SHA256 = (
    "bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625"
)
S3_SCHEMA_SHA256 = (
    "5d6e2fc33771b427130bd1dbe94c79cdf6d5827288b96929352c0caa793acbf1"
)
S3_SOURCE_BUNDLE_SHA256 = (
    "7e837b0cfdb0c9a12eb1b6c9067751c7cd4262cc18c5a6f17f4a6505f25b7410"
)

FROZEN_ANCHORS = {
    ".dockerignore": "c965ea6e67cb9d473aa76d57913f8976b4d7b38b59fa2bedb64dcab06df163c2",
    "artifacts/phase1-0d-semantic-review-v2-transport-capacity/20260805T180417Z/00_capacity_certificate.json": (
        "20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3"
    ),
    "artifacts/phase1-0d-semantic-review-v2-transport-capacity/20260805T180417Z/artifact_manifest.json": (
        "23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834"
    ),
    "docs/decisions/jlens_s3_validity_protocol_freeze.md": (
        "d7d9623e3668b5469b426ba45671f267b631599e44f598f710f6c16564a96b48"
    ),
    "docs/jlens_s3_validity_protocol.json": S3_PROTOCOL_SHA256,
    "docs/jlens_s3_validity_protocol.md": (
        "d2e851013037a5efa96d7ae06c3d7c9d63466b299d255c75b6c665debf862bff"
    ),
    "docs/jlens_s3_validity_protocol.schema.json": S3_SCHEMA_SHA256,
    "docs/jlens_s3_validity_protocol_review.md": (
        "3ea426e74006098ebedf28e6f71f45e0bc38cc040df652ab1632eb288b07cb6a"
    ),
    "docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md": (
        "dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b"
    ),
    "docs/prompts/phase_s3_jlens_validity_protocol_design_prompt.md": (
        "5d39859bc3d75143f3fdcb469de1d199ad7f831d474509b605569cdc9c1814b8"
    ),
    "third_party/jacobian-lens/581d398613e5602a5af361e1c34d3a92ea82ba8e/PROVENANCE.json": (
        "9af58768b200488ba28e3522c08624d8273487f6662f0dce5177a04a5f66fffc"
    ),
}
SOURCE_BUNDLE_COMPONENTS = (
    "scripts/validate_jlens_s3_protocol.py",
    "src/jspace_observation/jlens_s3_protocol.py",
    "tests/test_jlens_s3_protocol.py",
)
PROTECTED_ROLLUPS = {
    "docs/phase1_0d_protected_bytes.json": (
        "jspace-phase1-0d/protected-bytes/v1",
        152,
        "436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd",
    ),
    "docs/phase1_0d_rv2_protected_bytes.json": (
        "jspace-phase1-0d/rv2-protected-bytes/v1",
        36,
        "ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a",
    ),
}

ALLOWED_TERMINAL_STATES = (
    "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY",
    "NONTERMINAL_CHECKPOINT_JLENS_S3_E0_SEALED_AWAITING_E1_E2_EXECUTION",
    "BLOCKED_ON_S2_STARTING_STATE_INTEGRITY",
    "BLOCKED_ON_S2_CORPUS_FREEZE",
    "BLOCKED_ON_S2_RUNTIME_COMPATIBILITY",
    "BLOCKED_ON_S2_GPU_CAPACITY",
    "BLOCKED_ON_S2_EXECUTION_INTEGRITY",
    "BLOCKED_ON_S2_ARTIFACT_INTEGRITY",
    "BLOCKED_ON_JLENS_S3_E0_EXECUTION_INTEGRITY",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IMMUTABLE_REF = re.compile(r"[0-9a-f]{40}\Z")


class S2ProtocolError(ValueError):
    """Raised when a frozen S2 or E0 invariant is not satisfied."""


def _reject_json_constant(value: str) -> None:
    raise S2ProtocolError(f"non-finite JSON number is forbidden: {value}")


def load_json(path: str | Path) -> Any:
    target = Path(path)
    try:
        return json.loads(
            target.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise S2ProtocolError(f"cannot load strict JSON {target}: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise S2ProtocolError(f"value is not finite canonical JSON: {exc}") from exc


def canonical_jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    chunks = []
    for row in rows:
        try:
            chunks.append(
                (
                    json.dumps(
                        dict(row),
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("utf-8")
            )
        except (TypeError, ValueError) as exc:
            raise S2ProtocolError(f"row is not finite canonical JSON: {exc}") from exc
    return b"".join(chunks)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def token_ids_bytes(token_ids: Sequence[int]) -> bytes:
    if not token_ids or any(
        not isinstance(token_id, int) or isinstance(token_id, bool)
        for token_id in token_ids
    ):
        raise S2ProtocolError("token IDs must be a nonempty integer sequence")
    return json.dumps(list(token_ids), separators=(",", ":")).encode("ascii")


def role_key(
    *,
    seed: str,
    row_id: str,
    raw_text_sha256: str,
    token_ids_sha256: str,
) -> str:
    if not seed or not row_id:
        raise S2ProtocolError("role key seed and immutable row ID are required")
    if not _SHA256.fullmatch(raw_text_sha256) or not _SHA256.fullmatch(
        token_ids_sha256
    ):
        raise S2ProtocolError("role key inputs require lowercase SHA-256 values")
    payload = (
        seed.encode("utf-8")
        + b"\0"
        + row_id.encode("utf-8")
        + b"\0"
        + raw_text_sha256.encode("ascii")
        + b"\0"
        + token_ids_sha256.encode("ascii")
    )
    return sha256_bytes(payload)


def assign_roles(
    eligible_rows: Sequence[Mapping[str, Any]],
    *,
    seed: str = ASSIGNMENT_SEED,
) -> list[dict[str, Any]]:
    seen_rows: set[str] = set()
    seen_tokens: set[str] = set()
    keyed: list[tuple[str, str, Mapping[str, Any]]] = []
    for row in eligible_rows:
        row_id = str(row.get("row_id", ""))
        raw_hash = str(row.get("raw_text_sha256", ""))
        token_hash = str(row.get("token_ids_sha256", ""))
        if not row_id or row_id in seen_rows:
            raise S2ProtocolError("eligible corpus row IDs must be unique and nonempty")
        if token_hash in seen_tokens:
            raise S2ProtocolError("eligible token-ID sequences must be unique")
        key = role_key(
            seed=seed,
            row_id=row_id,
            raw_text_sha256=raw_hash,
            token_ids_sha256=token_hash,
        )
        seen_rows.add(row_id)
        seen_tokens.add(token_hash)
        keyed.append((key, row_id, row))
    if len(keyed) < TOTAL_REGISTERED_ROWS:
        raise S2ProtocolError(
            f"need {TOTAL_REGISTERED_ROWS} eligible unique rows, found {len(keyed)}"
        )
    keyed.sort(key=lambda item: (item[0], item[1]))
    boundaries: list[tuple[str, int, int]] = []
    offset = 0
    for role in ROLE_ORDER:
        end = offset + ROLE_COUNTS[role]
        boundaries.append((role, offset, end))
        offset = end
    assigned: list[dict[str, Any]] = []
    for role, start, end in boundaries:
        for role_index, (key, _row_id, row) in enumerate(
            keyed[start:end], start=1
        ):
            assigned.append(
                {
                    **dict(row),
                    "role": role,
                    "role_index": role_index,
                    "role_key": key,
                }
            )
    return assigned


def symmetric_prompt_overlap(candidate: bytes, protected: bytes) -> bool:
    if not candidate or not protected:
        raise S2ProtocolError("overlap operands must be nonempty exact bytes")
    return (
        candidate == protected
        or candidate in protected
        or protected in candidate
    )


def overlap_matches(
    candidate: bytes,
    protected_bank: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    matches = []
    for row in protected_bank:
        prompt_id = str(row.get("prompt_id", ""))
        prompt = row.get("prompt_bytes")
        if not prompt_id or not isinstance(prompt, bytes) or not prompt:
            raise S2ProtocolError("protected prompt rows require ID and exact bytes")
        if symmetric_prompt_overlap(candidate, prompt):
            matches.append(prompt_id)
    return tuple(matches)


def validate_corpus_manifest(
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if set(manifest) != {
        "dataset",
        "exclusion_audit",
        "library_versions",
        "protected_prompt_bank",
        "role_counts",
        "rows",
        "schema_version",
        "selection",
        "tokenizer",
    }:
        raise S2ProtocolError("corpus manifest fields are not exact")
    if manifest.get("schema_version") != CORPUS_MANIFEST_VERSION:
        raise S2ProtocolError("corpus manifest schema version drifted")
    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict) or set(dataset) != {
        "configuration",
        "files",
        "id",
        "license",
        "revision",
        "split",
    }:
        raise S2ProtocolError("corpus dataset manifest is incomplete")
    revision = str(dataset.get("revision", ""))
    if (
        dataset.get("id") != "Salesforce/wikitext"
        or dataset.get("configuration") != "wikitext-103-raw-v1"
        or dataset.get("split") != "train"
        or not _IMMUTABLE_REF.fullmatch(revision)
    ):
        raise S2ProtocolError("corpus dataset identity is not immutable and exact")
    files = dataset.get("files")
    if not isinstance(files, list) or not files:
        raise S2ProtocolError("corpus dataset file identities are missing")
    for row in files:
        if (
            not isinstance(row, dict)
            or set(row) != {"bytes", "path", "sha256"}
            or not isinstance(row.get("bytes"), int)
            or row["bytes"] <= 0
            or not str(row.get("path", ""))
            or not _SHA256.fullmatch(str(row.get("sha256", "")))
        ):
            raise S2ProtocolError("corpus dataset file identity is malformed")
    license_row = dataset.get("license")
    if (
        not isinstance(license_row, dict)
        or set(license_row)
        != {
            "attribution",
            "bytes",
            "license_id",
            "path",
            "sha256",
            "share_alike",
        }
        or not str(license_row.get("license_id", ""))
        or not str(license_row.get("attribution", ""))
        or license_row.get("share_alike") is not True
        or not isinstance(license_row.get("bytes"), int)
        or license_row["bytes"] <= 0
        or not str(license_row.get("path", ""))
        or not _SHA256.fullmatch(str(license_row.get("sha256", "")))
    ):
        raise S2ProtocolError("corpus license bytes and attribution are incomplete")
    tokenizer = manifest.get("tokenizer")
    if tokenizer != {
        "force_bos": True,
        "id": MODEL_ID,
        "revision": MODEL_REVISION,
        "trust_remote_code": False,
    }:
        raise S2ProtocolError("corpus tokenizer identity drifted")
    libraries = manifest.get("library_versions")
    if (
        not isinstance(libraries, list)
        or not libraries
        or any(
            not isinstance(row, dict)
            or set(row) != {"name", "version"}
            or not str(row.get("name", ""))
            or not str(row.get("version", ""))
            for row in libraries
        )
    ):
        raise S2ProtocolError("corpus library versions are incomplete")
    selection = manifest.get("selection")
    if (
        not isinstance(selection, dict)
        or set(selection)
        != {
            "assignment_seed",
            "eligible_unique_rows",
            "model_signals_inspected",
            "role_key_rule",
            "scanned_rows",
        }
        or selection.get("assignment_seed") != ASSIGNMENT_SEED
        or not isinstance(selection.get("eligible_unique_rows"), int)
        or selection["eligible_unique_rows"] < TOTAL_REGISTERED_ROWS
        or not isinstance(selection.get("scanned_rows"), int)
        or selection["scanned_rows"] < selection["eligible_unique_rows"]
        or selection.get("model_signals_inspected") is not False
    ):
        raise S2ProtocolError("corpus selection audit is incomplete")
    if manifest.get("role_counts") != ROLE_COUNTS:
        raise S2ProtocolError("corpus manifest role counts drifted")
    rows_ref = manifest.get("rows")
    exclusions_ref = manifest.get("exclusion_audit")
    bank_ref = manifest.get("protected_prompt_bank")
    for label, reference in (
        ("rows", rows_ref),
        ("exclusion audit", exclusions_ref),
        ("protected prompt bank", bank_ref),
    ):
        if (
            not isinstance(reference, dict)
            or set(reference) != {"bytes", "path", "sha256"}
            or not isinstance(reference.get("bytes"), int)
            or reference["bytes"] <= 0
            or not str(reference.get("path", ""))
            or not _SHA256.fullmatch(str(reference.get("sha256", "")))
        ):
            raise S2ProtocolError(f"corpus {label} reference is incomplete")
    if len(rows) != TOTAL_REGISTERED_ROWS:
        raise S2ProtocolError(
            f"corpus rows must contain exactly {TOTAL_REGISTERED_ROWS} records"
        )
    expected_fields = {
        "dataset_revision",
        "raw_text",
        "raw_text_sha256",
        "role",
        "role_index",
        "role_key",
        "row_id",
        "token_count_untruncated",
        "token_ids",
        "token_ids_sha256",
    }
    token_hashes: set[str] = set()
    row_ids: set[str] = set()
    by_role: dict[str, list[int]] = {role: [] for role in ROLE_ORDER}
    for row in rows:
        if set(row) != expected_fields:
            raise S2ProtocolError("corpus row fields are not exact")
        row_id = str(row.get("row_id", ""))
        role = str(row.get("role", ""))
        role_index = row.get("role_index")
        raw_text = row.get("raw_text")
        token_ids = row.get("token_ids")
        token_count = row.get("token_count_untruncated")
        if (
            row.get("dataset_revision") != revision
            or not row_id
            or row_id in row_ids
            or role not in ROLE_COUNTS
            or not isinstance(role_index, int)
            or isinstance(role_index, bool)
            or role_index <= 0
            or not isinstance(raw_text, str)
            or len(raw_text.strip()) < 600
            or not isinstance(token_ids, list)
            or len(token_ids) != MAX_SEQ_LEN
            or any(
                not isinstance(token_id, int) or isinstance(token_id, bool)
                for token_id in token_ids
            )
            or not isinstance(token_count, int)
            or token_count < MAX_SEQ_LEN
        ):
            raise S2ProtocolError("corpus row identity or content is invalid")
        raw_hash = sha256_bytes(raw_text.encode("utf-8"))
        token_hash = sha256_bytes(token_ids_bytes(token_ids))
        if (
            row.get("raw_text_sha256") != raw_hash
            or row.get("token_ids_sha256") != token_hash
            or token_hash in token_hashes
            or row.get("role_key")
            != role_key(
                seed=ASSIGNMENT_SEED,
                row_id=row_id,
                raw_text_sha256=raw_hash,
                token_ids_sha256=token_hash,
            )
        ):
            raise S2ProtocolError("corpus row hashes or role key are invalid")
        row_ids.add(row_id)
        token_hashes.add(token_hash)
        by_role[role].append(role_index)
    for role, count in ROLE_COUNTS.items():
        if sorted(by_role[role]) != list(range(1, count + 1)):
            raise S2ProtocolError(f"corpus role {role} indices are not exact")
    payload = canonical_jsonl_bytes(rows)
    if (
        rows_ref["bytes"] != len(payload)
        or rows_ref["sha256"] != sha256_bytes(payload)
    ):
        raise S2ProtocolError("corpus row file identity is not reconstructible")
    return {
        "dataset_revision": revision,
        "role_counts": dict(ROLE_COUNTS),
        "row_count": len(rows),
        "rows_sha256": sha256_bytes(payload),
        "unique_token_sequences": len(token_hashes),
    }


def matrix_comparison(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> dict[str, float]:
    if len(left) != len(right) or not left:
        raise S2ProtocolError("matrices must have the same nonzero row count")
    flat_left: list[float] = []
    flat_right: list[float] = []
    for left_row, right_row in zip(left, right, strict=True):
        if len(left_row) != len(right_row) or not left_row:
            raise S2ProtocolError("matrices must have the same nonzero shape")
        flat_left.extend(float(value) for value in left_row)
        flat_right.extend(float(value) for value in right_row)
    if not all(math.isfinite(value) for value in flat_left + flat_right):
        raise S2ProtocolError("matrix comparison inputs must be finite")
    differences = [
        left_value - right_value
        for left_value, right_value in zip(flat_left, flat_right, strict=True)
    ]
    difference_norm = math.sqrt(sum(value * value for value in differences))
    right_norm = math.sqrt(sum(value * value for value in flat_right))
    left_norm = math.sqrt(sum(value * value for value in flat_left))
    denominator = left_norm * right_norm
    cosine = (
        sum(
            left_value * right_value
            for left_value, right_value in zip(
                flat_left, flat_right, strict=True
            )
        )
        / denominator
        if denominator > 0
        else (1.0 if flat_left == flat_right else 0.0)
    )
    return {
        "cosine": cosine,
        "max_abs": max(abs(value) for value in differences),
        "relative_frobenius": difference_norm / max(right_norm, 1e-12),
    }


def weighted_matrix_mean(
    matrices: Sequence[Sequence[Sequence[float]]],
    weights: Sequence[int],
) -> list[list[float]]:
    if len(matrices) != len(weights) or not matrices:
        raise S2ProtocolError("weighted mean requires one positive weight per matrix")
    if any(not isinstance(weight, int) or weight <= 0 for weight in weights):
        raise S2ProtocolError("matrix weights must be positive integers")
    rows = len(matrices[0])
    columns = len(matrices[0][0]) if rows else 0
    if not rows or not columns:
        raise S2ProtocolError("weighted mean matrices must be nonempty")
    for matrix in matrices:
        if len(matrix) != rows or any(len(row) != columns for row in matrix):
            raise S2ProtocolError("weighted mean matrices must share one shape")
    total = sum(weights)
    return [
        [
            sum(
                float(matrix[row][column]) * weight
                for matrix, weight in zip(matrices, weights, strict=True)
            )
            / total
            for column in range(columns)
        ]
        for row in range(rows)
    ]


def dim_batch_passes(attempt: Mapping[str, Any], *, reference_required: bool) -> bool:
    if attempt.get("status") != "success":
        return False
    if attempt.get("source_layers") != list(SOURCE_LAYERS):
        return False
    if attempt.get("target_layer") != TARGET_LAYER:
        return False
    if attempt.get("matrix_shapes_valid") is not True:
        return False
    if attempt.get("finite_float32") is not True:
        return False
    ratio = attempt.get("peak_reserved_ratio")
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
        return False
    if not math.isfinite(float(ratio)) or float(ratio) > PEAK_RESERVED_RATIO_MAXIMUM:
        return False
    if not reference_required:
        return True
    raw_layers = attempt.get("comparison_to_dim1")
    if isinstance(raw_layers, list):
        if any(not isinstance(row, dict) for row in raw_layers):
            return False
        layers = {str(row.get("layer")): row for row in raw_layers}
    elif isinstance(raw_layers, dict):
        layers = raw_layers
    else:
        return False
    if set(layers) != {str(layer) for layer in SOURCE_LAYERS}:
        return False
    return all(
        isinstance(values, dict)
        and float(values.get("max_abs", math.inf))
        <= DIM_BATCH_MAX_ABS_TOLERANCE
        and float(values.get("relative_frobenius", math.inf))
        <= DIM_BATCH_RELATIVE_FROBENIUS_TOLERANCE
        and float(values.get("cosine", -math.inf)) >= DIM_BATCH_COSINE_MINIMUM
        for values in layers.values()
    )


def choose_dim_batch(attempts: Mapping[int, Mapping[str, Any]]) -> int:
    if set(attempts) != set(DIM_BATCH_CANDIDATES):
        raise S2ProtocolError("smoke attempts must cover dim_batch 8, 4, 2, and 1")
    if not dim_batch_passes(attempts[1], reference_required=False):
        raise S2ProtocolError("dim_batch=1 reference did not complete safely")
    for candidate in DIM_BATCH_CANDIDATES:
        if dim_batch_passes(
            attempts[candidate],
            reference_required=candidate != 1,
        ):
            return candidate
    raise S2ProtocolError("no dim_batch candidate passed")


def plan_final_increment(
    observed_seconds_per_prompt: float,
    *,
    total_prompts: int = CHECKPOINT_INCREMENTS[-1],
    timeout_seconds: int = CONTAINER_TIMEOUT_SECONDS,
    export_reserve_seconds: int = PLANNER_EXPORT_RESERVE_SECONDS,
    safety_factor: float = PLANNER_SAFETY_FACTOR,
) -> dict[str, Any]:
    if (
        not math.isfinite(observed_seconds_per_prompt)
        or observed_seconds_per_prompt <= 0
        or total_prompts <= 0
        or timeout_seconds <= 0
        or export_reserve_seconds < 0
        or export_reserve_seconds >= timeout_seconds
        or not 0 < safety_factor <= 1
    ):
        raise S2ProtocolError("invalid deterministic subshard planner input")
    fit_budget = (timeout_seconds - export_reserve_seconds) * safety_factor
    maximum = math.floor(fit_budget / observed_seconds_per_prompt)
    if maximum < 1:
        raise S2ProtocolError("one sequence cannot fit the frozen subshard budget")
    sizes = []
    remaining = total_prompts
    while remaining:
        size = min(maximum, remaining)
        sizes.append(size)
        remaining -= size
    return {
        "export_reserve_seconds": export_reserve_seconds,
        "fit_budget_seconds": fit_budget,
        "maximum_subshard_size": maximum,
        "observed_seconds_per_prompt": observed_seconds_per_prompt,
        "safety_factor": safety_factor,
        "subshard_sizes": sizes,
        "timeout_seconds": timeout_seconds,
        "total_prompts": total_prompts,
    }


def account_successful_sequences(
    expected_sequence_ids: Sequence[str],
    attempt_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected = tuple(expected_sequence_ids)
    if not expected or len(expected) != len(set(expected)):
        raise S2ProtocolError("expected sequence IDs must be unique and nonempty")
    successful: list[str] = []
    failed_completed: set[str] = set()
    for receipt in attempt_receipts:
        ids = receipt.get("completed_sequence_ids")
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise S2ProtocolError("attempt completed_sequence_ids must be a unique list")
        if receipt.get("status") == "success":
            successful.extend(str(item) for item in ids)
        else:
            failed_completed.update(str(item) for item in ids)
    duplicates = sorted(
        sequence_id
        for sequence_id in set(successful)
        if successful.count(sequence_id) > 1
    )
    missing = sorted(set(expected) - set(successful))
    unexpected = sorted(set(successful) - set(expected))
    if duplicates or missing or unexpected:
        raise S2ProtocolError(
            "exactly-once sequence accounting failed: "
            f"duplicates={duplicates}, missing={missing}, unexpected={unexpected}"
        )
    return {
        "expected_count": len(expected),
        "recomputed_after_failed_attempt": sorted(
            failed_completed.intersection(successful)
        ),
        "successful_count": len(successful),
        "successful_sequence_ids_sha256": sha256_bytes(
            canonical_jsonl_bytes({"sequence_id": item} for item in successful)
        ),
    }


def fit_scaling_law(
    checkpoints: Sequence[int],
    distances: Sequence[float],
) -> dict[str, Any]:
    if len(checkpoints) != len(distances) or len(checkpoints) < 2:
        raise S2ProtocolError("scaling fit requires paired checkpoint distances")
    if any(
        not isinstance(n, int) or n <= 0 for n in checkpoints
    ) or any(not math.isfinite(value) or value <= 0 for value in distances):
        raise S2ProtocolError("scaling fit inputs must be finite and positive")
    x = [math.log(float(n)) for n in checkpoints]
    y = [math.log(float(value)) for value in distances]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator <= 0:
        raise S2ProtocolError("scaling checkpoints must not all be equal")
    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x, y, strict=True)
    ) / denominator
    intercept = y_mean - slope * x_mean
    coefficient = math.exp(intercept)
    alpha = -slope
    predicted = [coefficient * (n ** (-alpha)) for n in checkpoints]
    residuals = [
        observed - estimate
        for observed, estimate in zip(distances, predicted, strict=True)
    ]
    return {
        "alpha": alpha,
        "coefficient_equal_fit": coefficient,
        "coefficient_c_equivalent_at_alpha_half": coefficient / math.sqrt(2.0),
        "predicted": predicted,
        "residuals": residuals,
    }


def prior_scaling_prediction(n_prompts_per_arm: int, *, c: float = 1.7) -> float:
    if n_prompts_per_arm <= 0 or not math.isfinite(c) or c <= 0:
        raise S2ProtocolError("prior scaling prediction inputs must be positive")
    return c * math.sqrt(2.0 / n_prompts_per_arm)


def validate_lens_identity(
    metadata: Mapping[str, Any],
    *,
    expected_n_prompts: int,
) -> None:
    expected = {
        "d_model": MODEL_WIDTH,
        "finite": True,
        "n_prompts": expected_n_prompts,
        "save_load_max_abs": SAVE_LOAD_MAX_ABS_TOLERANCE,
        "source_layers": list(SOURCE_LAYERS),
        "target_layer": TARGET_LAYER,
    }
    actual = {key: metadata.get(key) for key in expected}
    if actual != expected:
        raise S2ProtocolError(
            f"canonical lens identity mismatch: expected={expected}, actual={actual}"
        )


def e0_floor_decision(counts: Mapping[str, int]) -> dict[str, Any]:
    required = {
        "causal_swap_confirmation": 30,
        "multihop_confirmation": 20,
        "order_ops_confirmation": 20,
        "pooled_readout_confirmation": 50,
    }
    if set(counts) != set(required) or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts.values()
    ):
        raise S2ProtocolError("E0 confirmation counts are incomplete or invalid")
    floors = {
        key: counts[key] >= threshold for key, threshold in required.items()
    }
    passed = all(floors.values())
    return {
        "floor_booleans": floors,
        "floors_pass": passed,
        "terminal_state": (
            "NONTERMINAL_CHECKPOINT_JLENS_S3_E0_SEALED_AWAITING_E1_E2_EXECUTION"
            if passed
            else "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY"
        ),
    }


def validate_e0_preconditions(lock: Mapping[str, Any]) -> None:
    required_lenses = lock.get("canonical_lenses")
    if not isinstance(required_lenses, dict) or set(required_lenses) != {
        "A600",
        "B600",
        "M1200",
    }:
        raise S2ProtocolError("E0 lock requires exactly A600, B600, and M1200")
    for lens_id, row in required_lenses.items():
        if not isinstance(row, dict) or row.get("sealed") is not True:
            raise S2ProtocolError(f"E0 lock lens {lens_id} is not byte-sealed")
        if not _SHA256.fullmatch(str(row.get("sha256", ""))):
            raise S2ProtocolError(f"E0 lock lens {lens_id} has no SHA-256")
    if lock.get("s3_protocol_sha256") != S3_PROTOCOL_SHA256:
        raise S2ProtocolError("E0 lock frozen S3 protocol hash mismatch")
    if lock.get("s3_schema_sha256") != S3_SCHEMA_SHA256:
        raise S2ProtocolError("E0 lock frozen S3 schema hash mismatch")
    if lock.get("pre_lock_benchmark_tokenizer_operations") != 0:
        raise S2ProtocolError("benchmark tokenizer operation occurred before E0 lock")
    if lock.get("pre_lock_benchmark_model_operations") != 0:
        raise S2ProtocolError("benchmark model operation occurred before E0 lock")
    if lock.get("lens_operations_authorized") != 0:
        raise S2ProtocolError("E0 must authorize zero lens operations")


def manifest_last_order(
    paths: Sequence[str],
    *,
    manifest_name: str = "artifact_manifest.json",
) -> tuple[str, ...]:
    if not paths or len(paths) != len(set(paths)):
        raise S2ProtocolError("artifact paths must be unique and nonempty")
    if manifest_name not in paths:
        raise S2ProtocolError("artifact manifest is missing")
    return tuple(
        sorted(paths, key=lambda path: (path == manifest_name, path))
    )


def verify_protected_manifest(
    root: Path,
    manifest_path: str,
    *,
    expected_domain: str,
    expected_file_count: int,
    expected_rollup: str,
) -> dict[str, Any]:
    document = load_json(root / manifest_path)
    files = document.get("files")
    if not isinstance(files, list) or len(files) != expected_file_count:
        raise S2ProtocolError(f"{manifest_path} protected file count mismatch")
    lines = []
    differences = []
    for row in files:
        if not isinstance(row, dict):
            raise S2ProtocolError(f"{manifest_path} contains a malformed row")
        relative = str(row.get("path", ""))
        target = root / relative
        if not target.is_file():
            differences.append(f"missing:{relative}")
            continue
        raw = target.read_bytes().replace(b"\r\n", b"\n")
        digest = sha256_bytes(raw)
        if digest != row.get("sha256") or len(raw) != row.get("bytes"):
            differences.append(f"changed:{relative}")
        lines.append(f"{relative} {digest}")
    payload = f"{expected_domain}\n" + "\n".join(lines) + "\n"
    rollup = sha256_bytes(payload.encode("utf-8"))
    if rollup != expected_rollup or document.get("rollup_sha256") != expected_rollup:
        differences.append(f"rollup:{rollup}")
    return {
        "difference_count": len(differences),
        "differences": differences,
        "file_count": len(files),
        "rollup_sha256": rollup,
    }


def source_bundle_bytes(root: Path) -> bytes:
    output = io.BytesIO()
    output.write(b"jlens-s3-validator-source-bundle-v1\n")
    for relative in sorted(SOURCE_BUNDLE_COMPONENTS):
        raw = (root / relative).read_bytes()
        output.write(relative.encode("utf-8"))
        output.write(b"\0")
        output.write(str(len(raw)).encode("ascii"))
        output.write(b"\0")
        output.write(raw)
    return output.getvalue()


def verify_starting_state(
    root: Path,
    *,
    require_pre_round_ledger_tail: bool,
) -> dict[str, Any]:
    root = root.resolve()

    def git(*arguments: str, text: bool = True) -> str | bytes:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=text,
        )
        if result.returncode:
            stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
            raise S2ProtocolError(f"git {' '.join(arguments)} failed: {stderr}")
        return result.stdout

    tree = str(git("rev-parse", f"{STARTING_COMMIT}^{{tree}}", text=True)).strip()
    if tree != STARTING_TREE:
        raise S2ProtocolError(f"starting tree mismatch: {tree}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", STARTING_COMMIT, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode:
        raise S2ProtocolError("starting commit is not an ancestor of HEAD")

    anchors = {}
    for relative, expected in sorted(FROZEN_ANCHORS.items()):
        raw = git("cat-file", "blob", f"HEAD:{relative}", text=False)
        assert isinstance(raw, bytes)
        observed = sha256_bytes(raw)
        if observed != expected:
            raise S2ProtocolError(
                f"frozen anchor {relative} expected {expected}, observed {observed}"
            )
        anchors[relative] = observed
    bundle = source_bundle_bytes(root)
    if sha256_bytes(bundle) != S3_SOURCE_BUNDLE_SHA256:
        raise S2ProtocolError("frozen S3 validator source bundle mismatch")

    protected = {}
    for relative, (domain, count, rollup) in PROTECTED_ROLLUPS.items():
        result = verify_protected_manifest(
            root,
            relative,
            expected_domain=domain,
            expected_file_count=count,
            expected_rollup=rollup,
        )
        if result["difference_count"]:
            raise S2ProtocolError(f"protected-byte drift: {result['differences']}")
        protected[relative] = result

    decision_log = (root / "docs" / "decision_log.md").read_bytes()
    expected_prefix = git(
        "cat-file",
        "blob",
        f"{STARTING_COMMIT}:docs/decision_log.md",
        text=False,
    )
    assert isinstance(expected_prefix, bytes)
    if (
        len(expected_prefix) != DECISION_LOG_PREFIX_BYTES
        or sha256_bytes(expected_prefix) != DECISION_LOG_PREFIX_SHA256
        or not decision_log.startswith(expected_prefix)
    ):
        raise S2ProtocolError("D25-D30 append-only decision prefix changed")

    evidence = (root / "paper" / "evidence_ledger.csv").read_bytes()
    evidence_prefix = git(
        "cat-file",
        "blob",
        f"{STARTING_COMMIT}:paper/evidence_ledger.csv",
        text=False,
    )
    assert isinstance(evidence_prefix, bytes)
    if (
        len(evidence_prefix) != EVIDENCE_LEDGER_PREFIX_BYTES
        or sha256_bytes(evidence_prefix) != EVIDENCE_LEDGER_PREFIX_SHA256
        or not evidence.startswith(evidence_prefix)
    ):
        raise S2ProtocolError("pre-round evidence-ledger prefix changed")
    if require_pre_round_ledger_tail:
        rows = list(csv.reader(io.StringIO(evidence.decode("utf-8"))))
        if not rows or rows[-1][0] != "EV-0014":
            raise S2ProtocolError("pre-round evidence ledger does not end at EV-0014")

    return {
        "anchors": anchors,
        "decision_log_prefix_sha256": DECISION_LOG_PREFIX_SHA256,
        "evidence_ledger_prefix_sha256": EVIDENCE_LEDGER_PREFIX_SHA256,
        "phase1_protected": protected,
        "s3_source_bundle_sha256": S3_SOURCE_BUNDLE_SHA256,
        "starting_commit": STARTING_COMMIT,
        "starting_tree": STARTING_TREE,
    }


def _assert_closed_schema(schema: Any, path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise S2ProtocolError(f"{path}: schema node must be an object")
    declared = schema.get("type")
    object_typed = declared == "object" or (
        isinstance(declared, list) and "object" in declared
    )
    if object_typed:
        properties = schema.get("properties")
        required = schema.get("required")
        if schema.get("additionalProperties") is not False:
            raise S2ProtocolError(f"{path}: object schema is not closed")
        if (
            not isinstance(properties, dict)
            or not isinstance(required, list)
            or set(properties) != set(required)
            or len(required) != len(set(required))
        ):
            raise S2ProtocolError(f"{path}: every object property must be required")
    for name, child in schema.get("properties", {}).items():
        _assert_closed_schema(child, f"{path}.properties.{name}")
    for name, child in schema.get("$defs", {}).items():
        _assert_closed_schema(child, f"{path}.$defs.{name}")
    if "items" in schema:
        _assert_closed_schema(schema["items"], f"{path}.items")


def validate_protocol_semantics(protocol: Mapping[str, Any]) -> None:
    if protocol.get("schema_version") != SCHEMA_VERSION:
        raise S2ProtocolError("S2 schema version drift")
    identities = protocol.get("identities", {})
    model = identities.get("model", {})
    jlens = identities.get("j_lens", {})
    expected_model = {
        "d_model": MODEL_WIDTH,
        "eval_mode": True,
        "id": MODEL_ID,
        "n_layers": MODEL_LAYERS,
        "parameter_dtype": MODEL_DTYPE,
        "revision": MODEL_REVISION,
        "trust_remote_code": False,
        "use_cache": False,
    }
    expected_jlens = {
        "commit": JLENS_COMMIT,
        "compile": False,
        "force_bos": True,
        "repository": JLENS_REPOSITORY,
    }
    if model != expected_model or jlens != expected_jlens:
        raise S2ProtocolError("model or J-lens identity drift")
    fit = protocol.get("fit", {})
    if fit.get("source_layers") != list(SOURCE_LAYERS):
        raise S2ProtocolError("S2 source-layer set drift")
    if fit.get("target_layer") != TARGET_LAYER:
        raise S2ProtocolError("S2 target layer drift")
    if fit.get("max_seq_len") != MAX_SEQ_LEN or fit.get("skip_first") != SKIP_FIRST:
        raise S2ProtocolError("S2 token-window identity drift")
    corpus = protocol.get("corpus", {})
    if corpus.get("assignment_seed") != ASSIGNMENT_SEED:
        raise S2ProtocolError("corpus assignment seed drift")
    if corpus.get("role_counts") != ROLE_COUNTS:
        raise S2ProtocolError("corpus role counts drift")
    if protocol.get("terminal_states") != list(ALLOWED_TERMINAL_STATES):
        raise S2ProtocolError("allowed terminal states drift")
    smoke = protocol.get("smoke", {})
    if smoke.get("dim_batch_candidates") != list(DIM_BATCH_CANDIDATES):
        raise S2ProtocolError("dim_batch candidates drift")
    shards = protocol.get("shards", {})
    if shards.get("cumulative_checkpoints") != list(CHECKPOINTS):
        raise S2ProtocolError("cumulative checkpoints drift")
    if shards.get("fixed_increments") != list(CHECKPOINT_INCREMENTS):
        raise S2ProtocolError("checkpoint increments drift")
    e0 = protocol.get("e0", {})
    if e0.get("lens_operations") != 0:
        raise S2ProtocolError("E0 lens operations must remain zero")


def load_and_validate_protocol(root: Path) -> dict[str, Any]:
    from jlens_s3_protocol import validate_json_schema  # model-free frozen helper

    protocol_path = root / "docs" / "jlens_s2_protocol.json"
    schema_path = root / "docs" / "jlens_s2_protocol.schema.json"
    protocol = load_json(protocol_path)
    schema = load_json(schema_path)
    if not isinstance(protocol, dict) or not isinstance(schema, dict):
        raise S2ProtocolError("S2 protocol and schema roots must be objects")
    if protocol_path.read_bytes() != canonical_json_bytes(protocol):
        raise S2ProtocolError("S2 protocol bytes are not canonical")
    if schema_path.read_bytes() != canonical_json_bytes(schema):
        raise S2ProtocolError("S2 schema bytes are not canonical")
    _assert_closed_schema(schema)
    validate_json_schema(protocol, schema)
    validate_protocol_semantics(protocol)
    return protocol


def load_and_validate_corpus_contract(root: Path) -> dict[str, Any]:
    path = root / "docs" / "jlens_s2_corpus_source_contract.json"
    contract = load_json(path)
    if not isinstance(contract, dict):
        raise S2ProtocolError("corpus source contract root must be an object")
    if path.read_bytes() != canonical_json_bytes(contract):
        raise S2ProtocolError("corpus source contract bytes are not canonical")
    if set(contract) != {
        "dataset",
        "eligibility_order",
        "exclusion_audit",
        "protected_prompt_bank",
        "role_assignment",
        "schema_version",
        "tokenization",
    }:
        raise S2ProtocolError("corpus source contract top-level fields drifted")
    if contract.get("schema_version") != CORPUS_CONTRACT_VERSION:
        raise S2ProtocolError("corpus source contract version drifted")
    dataset = contract.get("dataset")
    expected_dataset = {
        "configuration": "wikitext-103-raw-v1",
        "id": "Salesforce/wikitext",
        "immutable_revision": (
            "resolved and sealed by S2-P1 before tokenizer construction"
        ),
        "license": (
            "resolve exact repository license bytes and retain attribution and "
            "share-alike notice before tokenizer construction"
        ),
        "row_identity": "train:<zero-based source row index>",
        "source_field": "text",
        "split": "train",
    }
    if dataset != expected_dataset:
        raise S2ProtocolError("corpus dataset source identity drifted")
    assignment = contract.get("role_assignment")
    if not isinstance(assignment, dict):
        raise S2ProtocolError("corpus role assignment contract is missing")
    if assignment.get("seed") != ASSIGNMENT_SEED:
        raise S2ProtocolError("corpus contract assignment seed drifted")
    if assignment.get("counts") != ROLE_COUNTS:
        raise S2ProtocolError("corpus contract role counts drifted")
    bank = contract.get("protected_prompt_bank")
    if not isinstance(bank, dict):
        raise S2ProtocolError("protected prompt-bank contract is missing")
    sources = bank.get("repository_sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise S2ProtocolError("protected repository prompt sources drifted")
    paths = [str(row.get("path", "")) for row in sources if isinstance(row, dict)]
    if len(paths) != len(set(paths)) or any(not path for path in paths):
        raise S2ProtocolError("protected repository prompt paths must be unique")
    blob = bank.get("phase1_0d_blob")
    if (
        not isinstance(blob, dict)
        or blob.get("manifest_sha256")
        != "76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536"
    ):
        raise S2ProtocolError("Phase 1.0D protected prompt source drifted")
    return contract


def validate_auxiliary_schemas(root: Path) -> dict[str, str]:
    from jlens_s3_protocol import (  # model-free frozen helpers
        OUTPUT_COLUMNS,
        _check_schema_definition,
    )

    digests = {}
    documents = {}
    for relative in (
        "docs/jlens_s2_artifacts.schema.json",
        "docs/jlens_s3_e0_pack.schema.json",
    ):
        path = root / relative
        document = load_json(path)
        if not isinstance(document, dict):
            raise S2ProtocolError(f"{relative} schema root must be an object")
        if path.read_bytes() != canonical_json_bytes(document):
            raise S2ProtocolError(f"{relative} bytes are not canonical")
        _check_schema_definition(document)
        _assert_closed_schema(document)
        documents[relative] = document
        digests[relative] = sha256_file(path)
    e0_schema = documents["docs/jlens_s3_e0_pack.schema.json"]
    definitions = e0_schema.get("$defs")
    if not isinstance(definitions, dict):
        raise S2ProtocolError("E0 pack schema definitions are missing")
    for table in ("e0_item", "e0_surface"):
        row_schema = definitions.get(table)
        if not isinstance(row_schema, dict):
            raise S2ProtocolError(f"E0 schema is missing {table}")
        properties = row_schema.get("properties")
        if not isinstance(properties, dict) or tuple(properties) != tuple(
            sorted(OUTPUT_COLUMNS[table])
        ):
            raise S2ProtocolError(
                f"E0 {table} schema columns differ from frozen S3 output columns"
            )
    return digests


__all__ = [
    "ALLOWED_TERMINAL_STATES",
    "ASSIGNMENT_SEED",
    "AUTHORITY_PATH",
    "AUTHORITY_SHA256",
    "CHECKPOINTS",
    "CHECKPOINT_INCREMENTS",
    "CORPUS_CONTRACT_VERSION",
    "CORPUS_MANIFEST_VERSION",
    "DIM_BATCH_CANDIDATES",
    "FROZEN_ANCHORS",
    "MAX_SEQ_LEN",
    "MODEL_ID",
    "MODEL_REVISION",
    "ROLE_COUNTS",
    "S2ProtocolError",
    "SCHEMA_VERSION",
    "SKIP_FIRST",
    "SOURCE_LAYERS",
    "STARTING_COMMIT",
    "STARTING_TREE",
    "TARGET_LAYER",
    "account_successful_sequences",
    "assign_roles",
    "canonical_json_bytes",
    "canonical_jsonl_bytes",
    "choose_dim_batch",
    "e0_floor_decision",
    "fit_scaling_law",
    "load_and_validate_protocol",
    "load_and_validate_corpus_contract",
    "load_json",
    "manifest_last_order",
    "matrix_comparison",
    "overlap_matches",
    "plan_final_increment",
    "prior_scaling_prediction",
    "role_key",
    "sha256_bytes",
    "sha256_file",
    "source_bundle_bytes",
    "symmetric_prompt_overlap",
    "token_ids_bytes",
    "validate_e0_preconditions",
    "validate_auxiliary_schemas",
    "validate_corpus_manifest",
    "validate_lens_identity",
    "validate_protocol_semantics",
    "verify_protected_manifest",
    "verify_starting_state",
    "weighted_matrix_mean",
]
