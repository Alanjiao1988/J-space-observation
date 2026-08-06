"""Model-free tests for the full-layer S2 and frozen S3-E0 protocol."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _eligible_rows(count: int = s2.TOTAL_REGISTERED_ROWS) -> list[dict]:
    rows = []
    for index in range(count):
        text = f"row-{index:04d} " + ("x" * 600)
        token_ids = [index] + list(range(1, s2.MAX_SEQ_LEN))
        rows.append(
            {
                "dataset_revision": "1" * 40,
                "raw_text": text,
                "raw_text_sha256": s2.sha256_bytes(text.encode("utf-8")),
                "row_id": f"train:{index}",
                "token_count_untruncated": 150,
                "token_ids": token_ids,
                "token_ids_sha256": s2.sha256_bytes(
                    s2.token_ids_bytes(token_ids)
                ),
            }
        )
    return rows


def _valid_corpus_pack() -> tuple[dict, list[dict]]:
    rows = s2.assign_roles(_eligible_rows())
    payload = s2.canonical_jsonl_bytes(rows)
    reference = {
        "bytes": 1,
        "path": "audit.jsonl",
        "sha256": "2" * 64,
    }
    manifest = {
        "dataset": {
            "configuration": "wikitext-103-raw-v1",
            "files": [
                {
                    "bytes": 123,
                    "path": "wikitext-train.parquet",
                    "sha256": "3" * 64,
                }
            ],
            "id": "Salesforce/wikitext",
            "license": {
                "attribution": "WikiText derived from Wikipedia",
                "bytes": 456,
                "license_id": "CC-BY-SA-3.0",
                "path": "LICENSE",
                "sha256": "4" * 64,
                "share_alike": True,
            },
            "revision": "1" * 40,
            "split": "train",
        },
        "exclusion_audit": dict(reference),
        "library_versions": [
            {"name": "datasets", "version": "4.0.0"},
            {"name": "transformers", "version": "5.9.0"},
        ],
        "protected_prompt_bank": {
            **reference,
            "path": "protected_prompt_bank.jsonl",
        },
        "role_counts": dict(s2.ROLE_COUNTS),
        "rows": {
            "bytes": len(payload),
            "path": "rows.jsonl",
            "sha256": s2.sha256_bytes(payload),
        },
        "schema_version": s2.CORPUS_MANIFEST_VERSION,
        "selection": {
            "assignment_seed": s2.ASSIGNMENT_SEED,
            "eligible_unique_rows": len(rows),
            "model_signals_inspected": False,
            "role_key_rule": "frozen",
            "scanned_rows": len(rows) + 100,
        },
        "tokenizer": {
            "force_bos": True,
            "id": s2.MODEL_ID,
            "revision": s2.MODEL_REVISION,
            "trust_remote_code": False,
        },
    }
    return manifest, rows


def _smoke_attempt(candidate: int) -> dict:
    comparison = [
        {
            "cosine": 1.0,
            "layer": layer,
            "max_abs": 0.0,
            "relative_frobenius": 0.0,
        }
        for layer in s2.SOURCE_LAYERS
    ]
    return {
        "comparison_to_dim1": comparison,
        "finite_float32": True,
        "matrix_shapes_valid": True,
        "peak_reserved_ratio": 0.5,
        "source_layers": list(s2.SOURCE_LAYERS),
        "status": "success",
        "target_layer": s2.TARGET_LAYER,
    }


def test_complete_protocol_package_is_canonical_and_closed() -> None:
    protocol = s2.load_and_validate_protocol(ROOT)
    contract = s2.load_and_validate_corpus_contract(ROOT)
    schemas = s2.validate_auxiliary_schemas(ROOT)
    assert protocol["schema_version"] == s2.SCHEMA_VERSION
    assert contract["schema_version"] == s2.CORPUS_CONTRACT_VERSION
    assert set(schemas) == {
        "docs/jlens_s2_artifacts.schema.json",
        "docs/jlens_s3_e0_pack.schema.json",
    }


def test_starting_receipt_and_live_frozen_prefixes_validate() -> None:
    receipt_path = ROOT / "docs" / "jlens_s2_starting_state_receipt.json"
    receipt = s2.load_json(receipt_path)
    assert receipt_path.read_bytes() == s2.canonical_json_bytes(receipt)
    assert receipt["status"] == "S2-G0-PASS"
    assert receipt["git"]["origin_main_commit"] == s2.STARTING_COMMIT
    assert receipt["git"]["origin_main_tree"] == s2.STARTING_TREE
    assert receipt["evidence_ledger"]["last_row"] == "EV-0014"
    report = s2.verify_starting_state(
        ROOT,
        require_pre_round_ledger_tail=False,
    )
    assert report["starting_commit"] == s2.STARTING_COMMIT
    assert report["starting_tree"] == s2.STARTING_TREE
    assert all(
        row["difference_count"] == 0
        for row in report["phase1_protected"].values()
    )


def test_role_key_has_exact_domain_separation() -> None:
    raw_hash = _sha("raw")
    token_hash = _sha("tokens")
    expected = hashlib.sha256(
        s2.ASSIGNMENT_SEED.encode()
        + b"\0"
        + b"train:7"
        + b"\0"
        + raw_hash.encode()
        + b"\0"
        + token_hash.encode()
    ).hexdigest()
    assert s2.role_key(
        seed=s2.ASSIGNMENT_SEED,
        row_id="train:7",
        raw_text_sha256=raw_hash,
        token_ids_sha256=token_hash,
    ) == expected


def test_deterministic_role_assignment_is_exact_disjoint_and_stable() -> None:
    source = _eligible_rows()
    first = s2.assign_roles(source)
    second = s2.assign_roles(list(reversed(source)))
    projection = lambda rows: [
        (row["row_id"], row["role"], row["role_index"], row["role_key"])
        for row in rows
    ]
    assert projection(first) == projection(second)
    counts = {
        role: sum(row["role"] == role for row in first)
        for role in s2.ROLE_ORDER
    }
    assert counts == s2.ROLE_COUNTS
    assert len({row["row_id"] for row in first}) == s2.TOTAL_REGISTERED_ROWS
    assert (
        len({row["token_ids_sha256"] for row in first})
        == s2.TOTAL_REGISTERED_ROWS
    )
    assert [row["role_index"] for row in first if row["role"] == "A"] == list(
        range(1, 601)
    )
    assert [row["role_index"] for row in first if row["role"] == "B"] == list(
        range(1, 601)
    )


def test_role_assignment_fails_closed_on_short_or_duplicate_input() -> None:
    with pytest.raises(s2.S2ProtocolError, match="need 1402"):
        s2.assign_roles(_eligible_rows(1401))
    duplicate = _eligible_rows()
    duplicate[1]["token_ids_sha256"] = duplicate[0]["token_ids_sha256"]
    with pytest.raises(s2.S2ProtocolError, match="token-ID"):
        s2.assign_roles(duplicate)


def test_exact_symmetric_prompt_overlap_has_no_normalization() -> None:
    assert s2.symmetric_prompt_overlap(b"abc", b"abc")
    assert s2.symmetric_prompt_overlap(b"abc", b"--abc--")
    assert s2.symmetric_prompt_overlap(b"--abc--", b"abc")
    assert not s2.symmetric_prompt_overlap(b"ABC", b"abc")
    assert s2.overlap_matches(
        b"long protected prompt",
        [
            {"prompt_id": "a", "prompt_bytes": b"protected"},
            {"prompt_id": "b", "prompt_bytes": b"different"},
        ],
    ) == ("a",)


def test_corpus_manifest_reconstructs_every_registered_identity() -> None:
    manifest, rows = _valid_corpus_pack()
    report = s2.validate_corpus_manifest(manifest, rows)
    assert report["row_count"] == 1402
    assert report["unique_token_sequences"] == 1402
    assert report["role_counts"] == s2.ROLE_COUNTS

    changed = copy.deepcopy(rows)
    changed[0]["token_ids"][0] += 1
    with pytest.raises(s2.S2ProtocolError, match="hashes or role key"):
        s2.validate_corpus_manifest(manifest, changed)

    floating = copy.deepcopy(manifest)
    floating["dataset"]["revision"] = "main"
    with pytest.raises(s2.S2ProtocolError, match="immutable"):
        s2.validate_corpus_manifest(floating, rows)


def test_full_layer_identity_and_lossless_gate_are_exact() -> None:
    valid = {
        "d_model": 1536,
        "finite": True,
        "n_prompts": 600,
        "save_load_max_abs": 0.0,
        "source_layers": list(range(27)),
        "target_layer": 27,
    }
    s2.validate_lens_identity(valid, expected_n_prompts=600)
    changed = dict(valid)
    changed["source_layers"] = list(range(1, 27))
    with pytest.raises(s2.S2ProtocolError, match="identity mismatch"):
        s2.validate_lens_identity(changed, expected_n_prompts=600)


def test_weighted_merge_and_matrix_diagnostics_are_reconstructible() -> None:
    left = [[1.0, 2.0], [3.0, 4.0]]
    right = [[3.0, 4.0], [5.0, 6.0]]
    merged = s2.weighted_matrix_mean([left, right], [1, 3])
    assert merged == [[2.5, 3.5], [4.5, 5.5]]
    exact = s2.matrix_comparison(merged, merged)
    assert exact == {
        "cosine": pytest.approx(1.0),
        "max_abs": 0.0,
        "relative_frobenius": 0.0,
    }
    changed = s2.matrix_comparison(left, right)
    assert changed["max_abs"] == 2.0
    assert changed["relative_frobenius"] > 0
    assert 0 < changed["cosine"] < 1


def test_dim_batch_selection_is_descending_and_reference_bound() -> None:
    attempts = {
        candidate: _smoke_attempt(candidate)
        for candidate in s2.DIM_BATCH_CANDIDATES
    }
    assert s2.choose_dim_batch(attempts) == 8
    attempts[8]["comparison_to_dim1"][0]["max_abs"] = 2e-5
    assert s2.choose_dim_batch(attempts) == 4
    attempts[4]["peak_reserved_ratio"] = 0.9200001
    assert s2.choose_dim_batch(attempts) == 2
    attempts[1]["status"] = "failed"
    with pytest.raises(s2.S2ProtocolError, match="reference"):
        s2.choose_dim_batch(attempts)


def test_final_increment_planner_is_deterministic_and_order_preserving() -> None:
    plan = s2.plan_final_increment(100.0)
    assert plan["fit_budget_seconds"] == pytest.approx(4410.0)
    assert plan["maximum_subshard_size"] == 44
    assert plan["subshard_sizes"] == [44, 44, 44, 44, 44, 44, 44, 36]
    assert sum(plan["subshard_sizes"]) == 344
    with pytest.raises(s2.S2ProtocolError, match="one sequence"):
        s2.plan_final_increment(5000.0)


def test_exactly_once_accounting_discloses_failed_attempt_recomputation() -> None:
    expected = ["a", "b", "c"]
    result = s2.account_successful_sequences(
        expected,
        [
            {
                "status": "infrastructure_failed",
                "completed_sequence_ids": ["a"],
            },
            {"status": "success", "completed_sequence_ids": ["a", "b"]},
            {"status": "success", "completed_sequence_ids": ["c"]},
        ],
    )
    assert result["successful_count"] == 3
    assert result["recomputed_after_failed_attempt"] == ["a"]
    with pytest.raises(s2.S2ProtocolError, match="duplicates"):
        s2.account_successful_sequences(
            expected,
            [
                {"status": "success", "completed_sequence_ids": ["a", "b"]},
                {"status": "success", "completed_sequence_ids": ["a", "c"]},
            ],
        )


def test_free_exponent_scaling_fit_and_registered_prior() -> None:
    checkpoints = [64, 128, 256, 600]
    coefficient = 2.4
    alpha = 0.6
    distances = [coefficient * n ** (-alpha) for n in checkpoints]
    fit = s2.fit_scaling_law(checkpoints, distances)
    assert fit["alpha"] == pytest.approx(alpha)
    assert fit["coefficient_equal_fit"] == pytest.approx(coefficient)
    assert fit["residuals"] == pytest.approx([0.0] * 4)
    assert s2.prior_scaling_prediction(600) == pytest.approx(
        1.7 * math.sqrt(2 / 600)
    )


def test_e0_lock_requires_three_sealed_lenses_and_zero_prelock_operations() -> None:
    lock = {
        "canonical_lenses": {
            lens: {"sealed": True, "sha256": index * 64}
            for lens, index in (("A600", "a"), ("B600", "b"), ("M1200", "c"))
        },
        "lens_operations_authorized": 0,
        "pre_lock_benchmark_model_operations": 0,
        "pre_lock_benchmark_tokenizer_operations": 0,
        "s3_protocol_sha256": s2.S3_PROTOCOL_SHA256,
        "s3_schema_sha256": s2.S3_SCHEMA_SHA256,
    }
    s2.validate_e0_preconditions(lock)
    changed = copy.deepcopy(lock)
    changed["pre_lock_benchmark_tokenizer_operations"] = 1
    with pytest.raises(s2.S2ProtocolError, match="before E0 lock"):
        s2.validate_e0_preconditions(changed)
    changed = copy.deepcopy(lock)
    changed["canonical_lenses"]["M1200"]["sealed"] = False
    with pytest.raises(s2.S2ProtocolError, match="not byte-sealed"):
        s2.validate_e0_preconditions(changed)


def test_e0_floor_pass_and_fail_are_the_only_scientific_branches() -> None:
    passing = s2.e0_floor_decision(
        {
            "causal_swap_confirmation": 30,
            "multihop_confirmation": 20,
            "order_ops_confirmation": 20,
            "pooled_readout_confirmation": 50,
        }
    )
    assert passing["floors_pass"]
    assert passing["terminal_state"].startswith("NONTERMINAL_CHECKPOINT")
    failing = s2.e0_floor_decision(
        {
            "causal_swap_confirmation": 29,
            "multihop_confirmation": 100,
            "order_ops_confirmation": 100,
            "pooled_readout_confirmation": 200,
        }
    )
    assert not failing["floors_pass"]
    assert (
        failing["terminal_state"]
        == "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY"
    )


def test_manifest_order_is_create_only_manifest_last() -> None:
    assert s2.manifest_last_order(
        ["z.json", "artifact_manifest.json", "a.json"]
    ) == ("a.json", "z.json", "artifact_manifest.json")
    with pytest.raises(s2.S2ProtocolError, match="missing"):
        s2.manifest_last_order(["a.json"])


def test_s2_module_cannot_import_model_dataset_or_lens_packages() -> None:
    source = (HELPER_ROOT / "jlens_s2_protocol.py").read_text(encoding="utf-8")
    forbidden = {"datasets", "jlens", "torch", "transformers"}
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden)
