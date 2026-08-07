"""Lens-free mechanical Stage E0 helpers over the frozen S3 protocol."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import jlens_s2_protocol as s2
import jlens_s3_protocol as s3


DISTRIBUTION_ORDER = ("multihop", "order_ops", "causal_swap")
EXPECTED_ITEM_COUNTS = {"multihop": 93, "order_ops": 55, "causal_swap": 90}
MAXIMUM_INPUT_TOKENS = 512
E0_PACK_SCHEMA_SHA256 = (
    "9fdb9a45b78bae98ab72e1ffb9eb5b757de889e27b05f799e175f67a82dfbb7c"
)
BENCHMARK_IDENTITIES = {
    "causal_swap": {
        "bytes": 26567,
        "item_count": 90,
        "path": "data/experiments/probe-swap.json",
        "sha256": "a0edd27ca23f7b4d0fbe90448c2ddcc7457a3d812121bf024ed12a032ff86796",
    },
    "multihop": {
        "bytes": 21869,
        "item_count": 93,
        "path": "data/evaluations/lens-eval-multihop.json",
        "sha256": "50b7e4c9255291c0ca2a8e94615be9f44531fa57bb1a844e4f9616056d987416",
    },
    "order_ops": {
        "bytes": 9589,
        "item_count": 55,
        "path": "data/evaluations/lens-eval-order-ops.json",
        "sha256": "b203206d16ff628152cc86f3838604e06cb54776f3e14fa1c34f150db8bc7560",
    },
}
E0_SOURCE_BUNDLE_COMPONENTS = (
    "scripts/jlens_s3_e0.py",
    "scripts/jlens_s3_e0_lock.py",
    "src/jspace_observation/jlens_s3_e0_runtime.py",
    "src/jspace_observation/jlens_s3_protocol.py",
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IMAGE_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class E0RuntimeError(RuntimeError):
    """Raised when frozen E0 mechanics or operation boundaries fail."""


def e0_source_bundle_bytes(project_root: Path) -> bytes:
    output = bytearray(b"jlens-s3-e0-source-bundle-v1\n")
    for relative in sorted(E0_SOURCE_BUNDLE_COMPONENTS):
        raw = (project_root / relative).read_bytes()
        output.extend(relative.encode("utf-8"))
        output.extend(b"\0")
        output.extend(str(len(raw)).encode("ascii"))
        output.extend(b"\0")
        output.extend(raw)
    return bytes(output)


def actual_benchmark_identities(project_root: Path) -> dict[str, dict[str, Any]]:
    vendored = (
        project_root / "third_party" / "jacobian-lens" / s2.JLENS_COMMIT
    )
    observed = {}
    for distribution, expected in BENCHMARK_IDENTITIES.items():
        path = vendored / expected["path"]
        raw = path.read_bytes()
        document = json.loads(raw)
        observed[distribution] = {
            "bytes": len(raw),
            "item_count": len(document["items"]),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    return observed


def verify_locked_local_bytes(
    project_root: Path,
    lock: Mapping[str, Any],
) -> dict[str, Any]:
    observed = {
        "e0_output_schema_sha256": hashlib.sha256(
            (project_root / "docs" / "jlens_s3_e0_pack.schema.json").read_bytes()
        ).hexdigest(),
        "e0_source_bundle_sha256": hashlib.sha256(
            e0_source_bundle_bytes(project_root)
        ).hexdigest(),
        "s3_protocol_sha256": hashlib.sha256(
            (project_root / "docs" / "jlens_s3_validity_protocol.json").read_bytes()
        ).hexdigest(),
        "s3_schema_sha256": hashlib.sha256(
            (
                project_root / "docs" / "jlens_s3_validity_protocol.schema.json"
            ).read_bytes()
        ).hexdigest(),
        "vendored_benchmarks": actual_benchmark_identities(project_root),
    }
    for key in (
        "e0_output_schema_sha256",
        "e0_source_bundle_sha256",
        "s3_protocol_sha256",
        "s3_schema_sha256",
    ):
        if observed[key] != lock[key]:
            raise E0RuntimeError(f"E0 lock local byte mismatch: {key}")
    if observed["vendored_benchmarks"] != lock["vendored_benchmarks"]:
        raise E0RuntimeError("E0 lock vendored benchmark byte mismatch")
    return observed


def surface_specs(distribution: str, item: Mapping[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if distribution in {"multihop", "order_ops"}:
        intermediates = item.get("intermediates")
        if not isinstance(intermediates, list) or not intermediates:
            raise E0RuntimeError("readout item has no official intermediates")
        for index, raw in enumerate(intermediates):
            key = str(raw)
            if distribution == "multihop":
                candidates = (key,)
            elif key in s3.NUMERIC_FORMS:
                candidates = s3.NUMERIC_FORMS[key]
            elif key in s3.OPERATION_FORMS:
                candidates = s3.OPERATION_FORMS[key]
            else:
                raise E0RuntimeError(
                    f"order-ops intermediate has no frozen forms: {key}"
                )
            for candidate in candidates:
                specs.append(
                    {
                        "candidate_surface": candidate,
                        "intermediate_index": index,
                        "raw_key": f"intermediates[{index}]",
                        "surface_role": "intermediate",
                    }
                )
        specs.append(
            {
                "candidate_surface": str(item["target"]),
                "intermediate_index": None,
                "raw_key": "target",
                "surface_role": "target",
            }
        )
        return specs
    if distribution == "causal_swap":
        for raw_key, role in (
            ("intermediate", "intermediate"),
            ("swap_to", "swap_to"),
            ("answer", "target"),
            ("swap_answer", "swap_answer"),
        ):
            specs.append(
                {
                    "candidate_surface": str(item[raw_key]),
                    "intermediate_index": 0 if role == "intermediate" else None,
                    "raw_key": raw_key,
                    "surface_role": role,
                }
            )
        return specs
    raise E0RuntimeError(f"unknown E0 distribution: {distribution}")


def build_surface_rows(
    *,
    distribution: str,
    item: Mapping[str, Any],
    decoded_vocabulary: Mapping[int, str],
) -> list[dict[str, Any]]:
    prompt = str(item["prompt"])
    target = str(item["target"] if distribution != "causal_swap" else item["answer"])
    specs = surface_specs(distribution, item)
    resolved = s3.resolve_single_token_ids(
        [spec["candidate_surface"] for spec in specs],
        decoded_vocabulary,
    )
    rows = []
    for spec in specs:
        candidate = spec["candidate_surface"]
        token_ids = list(resolved[candidate])
        prompt_leakage = s3.token_bounded_literal(prompt, candidate)
        target_overlap = s3.normalize_surface(
            candidate, casefold=True
        ) == s3.normalize_surface(target, casefold=True)
        single_token = bool(token_ids)
        primary_scope = (
            distribution in {"multihop", "order_ops"}
            and spec["surface_role"] == "intermediate"
        )
        rows.append(
            {
                "candidate_surface": candidate,
                "distribution": distribution,
                "intermediate_index": spec["intermediate_index"],
                "item_id": str(item["name"]),
                "normalized_surface": s3.normalize_surface(candidate),
                "official_inclusive_retained": single_token,
                "primary_retained": bool(
                    primary_scope
                    and not prompt_leakage
                    and not target_overlap
                    and single_token
                ),
                "prompt_leakage": prompt_leakage,
                "raw_key": spec["raw_key"],
                "single_token": single_token,
                "surface_role": spec["surface_role"],
                "target_overlap": target_overlap,
                "token_ids": token_ids,
            }
        )
    keys = [
        (
            row["distribution"],
            row["item_id"],
            row["surface_role"],
            row["intermediate_index"],
            row["candidate_surface"],
        )
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise E0RuntimeError("E0 surface primary keys are not unique")
    return rows


def mechanical_eligibility(
    *,
    distribution: str,
    item: Mapping[str, Any],
    input_token_ids: Sequence[int],
    decoded_position_spans: Sequence[str],
    surface_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    registered_surfaces = [row["candidate_surface"] for row in surface_rows]
    control_candidates = list(
        s3.eligible_control_positions(
            decoded_position_spans,
            registered_surfaces,
        )
    )
    over_length = len(input_token_ids) > MAXIMUM_INPUT_TOKENS
    prompt_removed = sum(
        row["surface_role"] == "intermediate" and row["prompt_leakage"]
        for row in surface_rows
    )
    target_removed = sum(
        row["surface_role"] == "intermediate" and row["target_overlap"]
        for row in surface_rows
    )
    multi_removed = sum(not row["single_token"] for row in surface_rows)
    target_rows = [row for row in surface_rows if row["surface_role"] == "target"]
    target_token_ids = sorted(
        {
            token_id
            for row in target_rows
            for token_id in row["token_ids"]
        }
    )
    reasons: list[str] = []
    if over_length:
        reasons.append("over_length")
    if not control_candidates:
        reasons.append("no_control_position")
    if not target_token_ids:
        reasons.append("multi_token")
    if distribution in {"multihop", "order_ops"}:
        indexes = sorted(
            {
                int(row["intermediate_index"])
                for row in surface_rows
                if row["surface_role"] == "intermediate"
            }
        )
        for index in indexes:
            candidates = [
                row
                for row in surface_rows
                if row["surface_role"] == "intermediate"
                and row["intermediate_index"] == index
            ]
            if not any(row["primary_retained"] for row in candidates):
                if any(row["prompt_leakage"] for row in candidates):
                    reasons.append("prompt_surface")
                if any(row["target_overlap"] for row in candidates):
                    reasons.append("target_overlap")
                if any(not row["single_token"] for row in candidates):
                    reasons.append("multi_token")
    else:
        required_roles = {"intermediate", "swap_to", "target", "swap_answer"}
        for role in required_roles:
            if not any(
                row["surface_role"] == role and row["single_token"]
                for row in surface_rows
            ):
                reasons.append("multi_token")
    reasons = sorted(set(reasons))
    eligible = not reasons
    controls = (
        list(s3.deterministic_position_controls(item, control_candidates))
        if control_candidates
        else []
    )
    return {
        "control_position_candidates": control_candidates,
        "control_positions": controls,
        "mechanical_eligible": eligible,
        "multi_token_removed_count": int(multi_removed),
        "prompt_surface_removed_count": int(prompt_removed),
        "target_overlap_removed_count": int(target_removed),
        "target_token_ids": target_token_ids,
        "exclusion_reasons": reasons,
    }


def build_item_row(
    *,
    distribution: str,
    item: Mapping[str, Any],
    input_token_ids: Sequence[int],
    decoded_position_spans: Sequence[str],
    surface_rows: Sequence[Mapping[str, Any]],
    clean_top1_token_id: int,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    parameter_dtype: str,
) -> dict[str, Any]:
    mechanical = mechanical_eligibility(
        distribution=distribution,
        item=item,
        input_token_ids=input_token_ids,
        decoded_position_spans=decoded_position_spans,
        surface_rows=surface_rows,
    )
    targets = mechanical["target_token_ids"]
    behavioral = bool(
        mechanical["mechanical_eligible"]
        and targets
        and s3.clean_behavior_eligible(clean_top1_token_id, targets)
    )
    raw_prompt = str(item["prompt"]).encode("utf-8")
    item_bytes = s3.canonical_item_bytes(item)
    return {
        "behavioral_eligible": behavioral,
        "canonical_item_sha256": hashlib.sha256(item_bytes).hexdigest(),
        "clean_top1_token_id": clean_top1_token_id,
        "control_position_candidates": mechanical[
            "control_position_candidates"
        ],
        "control_positions": mechanical["control_positions"],
        "distribution": distribution,
        "exclusion_reasons": mechanical["exclusion_reasons"],
        "input_length": len(input_token_ids),
        "input_token_ids": list(input_token_ids),
        "item_id": str(item["name"]),
        "mechanical_eligible": mechanical["mechanical_eligible"],
        "model_id": model_id,
        "model_revision": model_revision,
        "multi_token_removed_count": mechanical["multi_token_removed_count"],
        "parameter_dtype": parameter_dtype,
        "prompt_sha256": hashlib.sha256(raw_prompt).hexdigest(),
        "prompt_surface_removed_count": mechanical[
            "prompt_surface_removed_count"
        ],
        "raw_prompt_utf8_sha256": hashlib.sha256(raw_prompt).hexdigest(),
        "split_hash": None,
        "split_role": "ineligible",
        "target_overlap_removed_count": mechanical[
            "target_overlap_removed_count"
        ],
        "target_token_ids": targets,
        "tokenizer_revision": tokenizer_revision,
    }


def assign_sealed_splits(
    *,
    raw_items: Mapping[str, Sequence[Mapping[str, Any]]],
    item_rows: list[dict[str, Any]],
) -> None:
    by_key = {
        (row["distribution"], row["item_id"]): row for row in item_rows
    }
    for distribution in DISTRIBUTION_ORDER:
        eligible_items = [
            item
            for item in raw_items[distribution]
            if by_key[(distribution, str(item["name"]))][
                "mechanical_eligible"
            ]
            and by_key[(distribution, str(item["name"]))][
                "behavioral_eligible"
            ]
        ]
        assignments = s3.assign_hash_split(eligible_items)
        for assignment in assignments:
            row = by_key[(distribution, assignment["item_id"])]
            row["split_hash"] = assignment["split_hash"]
            row["split_role"] = assignment["split_role"]


def e0_counts(item_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {}
    for distribution in DISTRIBUTION_ORDER:
        rows = [row for row in item_rows if row["distribution"] == distribution]
        counts[distribution] = {
            "behavioral_eligible": sum(row["behavioral_eligible"] for row in rows),
            "confirmation": sum(
                row["split_role"] == "confirmation" for row in rows
            ),
            "development": sum(
                row["split_role"] == "development" for row in rows
            ),
            "mechanical_eligible": sum(
                row["mechanical_eligible"] for row in rows
            ),
            "official": len(rows),
        }
    confirmation = {
        "causal_swap_confirmation": counts["causal_swap"]["confirmation"],
        "multihop_confirmation": counts["multihop"]["confirmation"],
        "order_ops_confirmation": counts["order_ops"]["confirmation"],
        "pooled_readout_confirmation": (
            counts["multihop"]["confirmation"]
            + counts["order_ops"]["confirmation"]
        ),
    }
    return {
        "confirmation_counts": confirmation,
        "distribution_counts": counts,
        **s2.e0_floor_decision(confirmation),
    }


def validate_e0_lock(lock: Mapping[str, Any]) -> None:
    required = {
        "canonical_lenses",
        "e0_image_digest",
        "e0_manifest_destination",
        "e0_output_schema_sha256",
        "e0_source_bundle_sha256",
        "expected_item_counts",
        "lens_operations_authorized",
        "model",
        "pre_lock_benchmark_model_operations",
        "pre_lock_benchmark_tokenizer_operations",
        "row_order",
        "s2_manifest",
        "s3_protocol_sha256",
        "s3_schema_sha256",
        "schema_version",
        "vendored_benchmarks",
    }
    if set(lock) != required:
        raise E0RuntimeError("E0 lock fields are not exact")
    if lock.get("schema_version") != "jlens-s3-e0-lock/v1":
        raise E0RuntimeError("E0 lock schema version drifted")
    s2.validate_e0_preconditions(lock)
    if lock.get("expected_item_counts") != EXPECTED_ITEM_COUNTS:
        raise E0RuntimeError("E0 lock item counts drifted")
    if lock.get("row_order") != list(DISTRIBUTION_ORDER):
        raise E0RuntimeError("E0 lock row order drifted")
    model = lock.get("model")
    if model != {
        "id": s2.MODEL_ID,
        "parameter_dtype": s2.MODEL_DTYPE,
        "revision": s2.MODEL_REVISION,
        "tokenizer_revision": s2.MODEL_REVISION,
    }:
        raise E0RuntimeError("E0 lock model/tokenizer identity drifted")
    if not str(lock.get("e0_image_digest", "")).startswith("sha256:"):
        raise E0RuntimeError("E0 image digest is invalid")
    if (
        not _IMAGE_DIGEST.fullmatch(str(lock["e0_image_digest"]))
        or not _SHA256.fullmatch(str(lock["e0_output_schema_sha256"]))
        or lock["e0_output_schema_sha256"] != E0_PACK_SCHEMA_SHA256
        or not _SHA256.fullmatch(str(lock["e0_source_bundle_sha256"]))
        or not _SHA256.fullmatch(str(lock["s2_manifest"].get("sha256", "")))
    ):
        raise E0RuntimeError("E0 lock hash identity is invalid")
    if set(lock["canonical_lenses"]) != {"A600", "B600", "M1200"}:
        raise E0RuntimeError("E0 canonical lens lock set drifted")
    for row in lock["canonical_lenses"].values():
        if (
            not isinstance(row, Mapping)
            or set(row) != {"bytes", "seal_sha256", "sealed", "sha256"}
            or not isinstance(row["bytes"], int)
            or row["bytes"] <= 0
            or row["sealed"] is not True
            or not _SHA256.fullmatch(str(row["seal_sha256"]))
            or not _SHA256.fullmatch(str(row["sha256"]))
        ):
            raise E0RuntimeError("E0 canonical lens byte seal is invalid")
    if set(lock["vendored_benchmarks"]) != set(EXPECTED_ITEM_COUNTS):
        raise E0RuntimeError("E0 benchmark distributions drifted")
    for name, row in lock["vendored_benchmarks"].items():
        expected = {
            key: value
            for key, value in BENCHMARK_IDENTITIES[name].items()
            if key != "path"
        }
        if row != expected:
            raise E0RuntimeError("E0 benchmark lock is incomplete")


__all__ = [
    "DISTRIBUTION_ORDER",
    "BENCHMARK_IDENTITIES",
    "E0_PACK_SCHEMA_SHA256",
    "E0RuntimeError",
    "EXPECTED_ITEM_COUNTS",
    "MAXIMUM_INPUT_TOKENS",
    "assign_sealed_splits",
    "actual_benchmark_identities",
    "build_item_row",
    "build_surface_rows",
    "e0_counts",
    "e0_source_bundle_bytes",
    "mechanical_eligibility",
    "surface_specs",
    "validate_e0_lock",
    "verify_locked_local_bytes",
]
