"""Synthetic tests for the frozen, lens-free S3 Stage E0 runtime."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402
import jlens_s3_e0_runtime as e0  # noqa: E402
import jlens_s3_protocol as s3  # noqa: E402


def test_frozen_surface_expansion_has_no_runtime_growth() -> None:
    multihop = {
        "name": "m",
        "prompt": "Fact: answer is ",
        "target": "Paris",
        "intermediates": ["France"],
    }
    assert [row["candidate_surface"] for row in e0.surface_specs("multihop", multihop)] == [
        "France",
        "Paris",
    ]
    order = {
        "name": "o",
        "prompt": "2 + 3 = ",
        "target": "5",
        "intermediates": ["3", "addition"],
    }
    assert [row["candidate_surface"] for row in e0.surface_specs("order_ops", order)] == [
        "3",
        "three",
        "+",
        "add",
        "addition",
        "plus",
        "5",
    ]
    unknown = dict(order)
    unknown["intermediates"] = ["unregistered"]
    with pytest.raises(e0.E0RuntimeError, match="no frozen forms"):
        e0.surface_specs("order_ops", unknown)


def test_surface_rows_apply_exact_boundary_leakage_and_target_rules() -> None:
    item = {
        "name": "item",
        "prompt": "Fact: Brazil's coast is ",
        "target": "Portuguese",
        "intermediates": ["Brazil"],
    }
    vocabulary = {
        1: " Brazil",
        2: "Brazil",
        3: " Portuguese",
        4: "  Brazil",
    }
    rows = e0.build_surface_rows(
        distribution="multihop",
        item=item,
        decoded_vocabulary=vocabulary,
    )
    intermediate = rows[0]
    assert intermediate["token_ids"] == [1, 2]
    assert intermediate["prompt_leakage"]
    assert not intermediate["target_overlap"]
    assert not intermediate["primary_retained"]
    target = rows[1]
    assert target["target_overlap"]
    assert target["token_ids"] == [3]


def test_one_removed_candidate_does_not_exclude_an_order_ops_item() -> None:
    item = {
        "name": "item",
        "prompt": "Compute addition: 2 + 3 = ",
        "target": "5",
        "intermediates": ["3", "addition"],
    }
    vocabulary = {
        1: " 3",
        2: " three",
        3: " +",
        4: " add",
        5: " addition",
        6: " plus",
        7: " 5",
        8: "safe",
        9: "final",
    }
    surfaces = e0.build_surface_rows(
        distribution="order_ops",
        item=item,
        decoded_vocabulary=vocabulary,
    )
    result = e0.mechanical_eligibility(
        distribution="order_ops",
        item=item,
        input_token_ids=[8, 9],
        decoded_position_spans=["safe", "final"],
        surface_rows=surfaces,
    )
    assert result["prompt_surface_removed_count"] >= 1
    assert result["mechanical_eligible"]
    assert result["exclusion_reasons"] == []


def test_substring_inside_alphanumeric_word_is_not_prompt_leakage() -> None:
    item = {
        "name": "item",
        "prompt": "A train is ",
        "target": "fast",
        "intermediates": ["rain"],
    }
    surfaces = e0.build_surface_rows(
        distribution="multihop",
        item=item,
        decoded_vocabulary={1: " rain", 2: " fast"},
    )
    assert surfaces[0]["prompt_leakage"] is False


def test_item_row_and_split_are_frozen_output_schema_compatible() -> None:
    item = {
        "name": "item",
        "prompt": "Fact: the result is ",
        "target": "answer",
        "intermediates": ["clue"],
    }
    surfaces = e0.build_surface_rows(
        distribution="multihop",
        item=item,
        decoded_vocabulary={1: " clue", 2: " answer"},
    )
    row = e0.build_item_row(
        distribution="multihop",
        item=item,
        input_token_ids=[10, 11],
        decoded_position_spans=["safe", "final"],
        surface_rows=surfaces,
        clean_top1_token_id=2,
        model_id=s2.MODEL_ID,
        model_revision=s2.MODEL_REVISION,
        tokenizer_revision=s2.MODEL_REVISION,
        parameter_dtype=s2.MODEL_DTYPE,
    )
    assert row["mechanical_eligible"]
    assert row["behavioral_eligible"]
    protocol = s3.load_and_validate_protocol(ROOT)
    s3.validate_output_row(protocol, "e0_item", row)
    for surface in surfaces:
        s3.validate_output_row(protocol, "e0_surface", surface)


def test_distribution_local_split_and_all_four_floors() -> None:
    raw_items = {}
    rows = []
    for distribution, count in e0.EXPECTED_ITEM_COUNTS.items():
        items = [
            {"name": f"{distribution}-{index}", "prompt": "p"}
            for index in range(count)
        ]
        raw_items[distribution] = items
        rows.extend(
            {
                "behavioral_eligible": True,
                "distribution": distribution,
                "item_id": item["name"],
                "mechanical_eligible": True,
                "split_hash": None,
                "split_role": "ineligible",
            }
            for item in items
        )
    e0.assign_sealed_splits(raw_items=raw_items, item_rows=rows)
    counts = e0.e0_counts(rows)
    assert all(
        row["development"] == 15
        for row in counts["distribution_counts"].values()
    )
    assert counts["floors_pass"]
    assert counts["floor_booleans"] == {
        "causal_swap_confirmation": True,
        "multihop_confirmation": True,
        "order_ops_confirmation": True,
        "pooled_readout_confirmation": True,
    }

    for row in rows:
        if row["distribution"] == "order_ops" and row["split_role"] == "confirmation":
            row["behavioral_eligible"] = False
            row["split_role"] = "ineligible"
    failed = e0.e0_counts(rows)
    assert failed["floor_booleans"]["order_ops_confirmation"] is False
    assert (
        failed["terminal_state"]
        == "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY"
    )


def _valid_lock() -> dict:
    return {
        "canonical_lenses": {
            lens: {
                "bytes": 1,
                "seal_sha256": digit * 64,
                "sealed": True,
                "sha256": digit * 64,
            }
            for lens, digit in (("A600", "a"), ("B600", "b"), ("M1200", "c"))
        },
        "e0_image_digest": "sha256:" + "d" * 64,
        "e0_manifest_destination": "jlens-s3/e0/run/output",
        "e0_output_schema_sha256": "e" * 64,
        "e0_source_bundle_sha256": "f" * 64,
        "expected_item_counts": dict(e0.EXPECTED_ITEM_COUNTS),
        "lens_operations_authorized": 0,
        "model": {
            "id": s2.MODEL_ID,
            "parameter_dtype": s2.MODEL_DTYPE,
            "revision": s2.MODEL_REVISION,
            "tokenizer_revision": s2.MODEL_REVISION,
        },
        "pre_lock_benchmark_model_operations": 0,
        "pre_lock_benchmark_tokenizer_operations": 0,
        "row_order": list(e0.DISTRIBUTION_ORDER),
        "s2_manifest": {"blob": "s2/manifest.json", "sha256": "1" * 64},
        "s3_protocol_sha256": s2.S3_PROTOCOL_SHA256,
        "s3_schema_sha256": s2.S3_SCHEMA_SHA256,
        "schema_version": "jlens-s3-e0-lock/v1",
        "vendored_benchmarks": {
            distribution: {
                "bytes": 1,
                "item_count": count,
                "sha256": "2" * 64,
            }
            for distribution, count in e0.EXPECTED_ITEM_COUNTS.items()
        },
    }


def test_e0_lock_rejects_prelock_operations_and_missing_seals() -> None:
    lock = _valid_lock()
    e0.validate_e0_lock(lock)
    changed = copy.deepcopy(lock)
    changed["pre_lock_benchmark_model_operations"] = 1
    with pytest.raises(s2.S2ProtocolError, match="before E0 lock"):
        e0.validate_e0_lock(changed)
    changed = copy.deepcopy(lock)
    changed["canonical_lenses"]["M1200"]["sealed"] = False
    with pytest.raises(s2.S2ProtocolError, match="not byte-sealed"):
        e0.validate_e0_lock(changed)


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/jlens_s3_e0.py",
        "scripts/jlens_s3_e0_lock.py",
        "src/jspace_observation/jlens_s3_e0_runtime.py",
    ],
)
def test_e0_sources_have_no_lens_import(relative: str) -> None:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "jlens" not in imported
    assert all(not name.startswith("phase05") for name in imported)


def test_e0_script_has_no_readout_intervention_or_e1_e2_call_path() -> None:
    source = (ROOT / "scripts" / "jlens_s3_e0.py").read_text(encoding="utf-8")
    forbidden_calls = (
        ".apply(",
        "coordinate_swap(",
        "ablate_direction(",
        "deterministic_gram_matched_pairs(",
        "paired_bootstrap(",
        "pass_at_k_auc(",
    )
    assert not any(call in source for call in forbidden_calls)
    assert '"e1_outputs": 0' in source
    assert '"e2_outputs": 0' in source
