#!/usr/bin/env python
"""Merge the sealed Stage B-D shards, compute the registered development
statistics, evaluate the frozen Gate A rule, and write the closed pack.

This entry point is model-free by construction: it imports no model class, no
torch, and no tokenizer, and it never reads a prompt string.  It consumes the
row-level shard outputs produced by the GPU runner and nothing else.

Gate A is evaluated only after the complete 3,072-row pack exists and has been
re-verified row by row.  The counts are never computed on a partial pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_bd as bd  # noqa: E402

FORBIDDEN_MODULES = ("torch", "transformers", "jlens", "jacobian_lens", "sklearn")


def assert_model_free() -> None:
    leaked = sorted(name for name in FORBIDDEN_MODULES if name in sys.modules)
    if leaked:
        raise bd.StageBDError(f"the finalizer is not model-free: {leaked}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", required=True, help="directory of shard artifacts")
    parser.add_argument("--output", required=True, help="directory for the sealed pack")
    args = parser.parse_args()

    assert_model_free()
    shard_dir = Path(args.shards)

    frozen = bd.verify_frozen_inputs(REPO_ROOT)
    items = bd.load_development_bank(REPO_ROOT)
    by_id = {item["item_id"]: item for item in items}
    index = bd.load_stage_t_development_index(REPO_ROOT)
    tokens = bd.option_token_ids(index)
    manifest = bd.build_shard_manifest(items)

    execution_receipt = json.loads(
        (shard_dir / "stage_bd_execution_receipt.json").read_text(encoding="utf-8")
    )
    if execution_receipt["shard_manifest_sha256"] != manifest["shard_manifest_sha256"]:
        raise bd.StageBDError("the executed shard manifest is not the sealed manifest")

    shard_rows: dict[str, list[dict]] = {}
    for shard in manifest["shards"]:
        slug = shard["shard_id"].replace("/", "_")
        receipt = json.loads(
            (shard_dir / f"{bd.SHARD_RECEIPT_PREFIX}{slug}.json").read_text(encoding="utf-8")
        )
        if receipt["attempt"]["row_keys_sha256"] != shard["row_keys_sha256"]:
            raise bd.StageBDError(f"shard {shard['shard_id']} covers unexpected rows")
        payload = (shard_dir / f"stage_bd_rows_{slug}.jsonl").read_bytes()
        if bd.sha256_bytes(payload) != receipt["rows_file"]["sha256"]:
            raise bd.StageBDError(f"shard {shard['shard_id']} rows differ from its receipt")
        shard_rows[shard["shard_id"]] = [
            json.loads(line) for line in payload.decode("utf-8").splitlines()
        ]

    rows = bd.merge_shard_rows(shard_rows, manifest)
    for row in rows:
        bd.verify_behavioral_row(
            row,
            item=by_id[row["item_id"]],
            identity={
                "model_id": next(
                    model_id
                    for role, model_id, _ in s2.MODEL_IDENTITIES
                    if role == row["model_role"]
                ),
                "resolved_revision": next(
                    revision
                    for role, _, revision in s2.MODEL_IDENTITIES
                    if role == row["model_role"]
                ),
            },
            prompt_identity=index[(row["model_role"], row["item_id"], row["arm"])],
            tokens=tokens,
        )

    summaries = bd.summarize(rows)
    diagnostics = bd.bootstrap_diagnostics(rows, by_id)
    gate = bd.gate_a(rows, items)

    result = bd.write_pack(
        Path(args.output),
        rows=rows,
        items=items,
        shard_manifest=manifest,
        weight_identity=execution_receipt["weight_identity"],
        confirmation=bd.verify_confirmation_receipt(
            execution_receipt["confirmation_unopened"]
        ),
        gate=gate,
        summaries=summaries,
        diagnostics=diagnostics,
        frozen=frozen,
        environment=execution_receipt["environment"],
        execution=execution_receipt["execution"],
    )
    assert_model_free()
    print(json.dumps({
        "core_manifest_sha256": result["manifest_entry"]["sha256"],
        "overall_gate_pass": gate["overall_gate_pass"],
        "rows": len(rows),
        "terminal_state": gate["terminal_state"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
