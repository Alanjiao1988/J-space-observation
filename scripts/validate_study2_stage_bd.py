#!/usr/bin/env python
"""Independently validate a candidate Study 2 Stage B-D pack.

This validator shares no code path with the writer beyond the frozen protocol
helpers: it reconstructs the expected primary keys from the frozen bank, re-reads
every emitted row, re-derives every derived field, re-checks every identity
against the sealed Stage T pack, re-runs the balance invariants, recomputes the
Gate A counts and tails, and re-validates every artifact against the closed
schema.  It loads no model, no weights and no tokenizer, and it certifies only a
complete 3,072-row pack.

Exit code 0 means certified.  Any other exit code means the pack must not enter
the Gate A finalizer.
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

SCHEMA_PATH = REPO_ROOT / "studies/study2/protocol/stage_bd_pack.schema.json"
FORBIDDEN_MODULES = ("torch", "transformers", "jlens", "jacobian_lens", "sklearn")


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def report(certified: bool, failures: list[str], **extra: object) -> int:
    print(
        json.dumps(
            {"certified": certified, "failures": failures, **extra}, indent=2, sort_keys=True
        )
    )
    return 0 if certified else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, help="directory holding the pack")
    args = parser.parse_args()
    failures: list[str] = []
    try:
        return validate(Path(args.pack), failures)
    except Exception as error:  # any unexpected condition is a refusal, never a pass
        failures.append(f"{type(error).__name__}: {error}")
        return report(False, failures)


def validate(pack: Path, failures: list[str]) -> int:
    leaked = sorted(name for name in FORBIDDEN_MODULES if name in sys.modules)
    check(not leaked, f"validator is not model-free: {leaked}", failures)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    s2.verify_schema_closed(schema)
    defs = schema["$defs"]

    bd.verify_frozen_inputs(REPO_ROOT)
    items = bd.load_development_bank(REPO_ROOT)
    by_id = {item["item_id"]: item for item in items}
    index = bd.load_stage_t_development_index(REPO_ROOT)
    tokens = bd.option_token_ids(index)
    expected = bd.expected_row_keys(items)
    manifest = bd.build_shard_manifest(items)

    manifest_path = pack / bd.CORE_MANIFEST_NAME
    check(manifest_path.exists(), "core manifest is missing", failures)
    core = json.loads(manifest_path.read_text(encoding="utf-8"))
    s2.validate_json_schema(core, {**defs["core_manifest"], "$defs": defs})

    for entry in core["files"]:
        blob = (pack / entry["path"]).read_bytes()
        check(
            len(blob) == entry["bytes"] and bd.sha256_bytes(blob) == entry["sha256"],
            f"{entry['path']} does not match its manifest entry",
            failures,
        )
    check(
        sorted(entry["path"] for entry in core["files"]) == sorted(bd.PACK_FILES),
        "the pack file set is not the registered set",
        failures,
    )

    rows: list[dict] = []
    for role in bd.MODEL_ROLES:
        payload = (pack / bd.BEHAVIORAL_FILES[role]).read_text(encoding="utf-8")
        subset = [json.loads(line) for line in payload.splitlines()]
        check(
            len(subset) == bd.ROWS_PER_MODEL,
            f"{role} contributed {len(subset)} rows, expected {bd.ROWS_PER_MODEL}",
            failures,
        )
        rows.extend(subset)

    observed = [(row["model_role"], row["item_id"], row["arm"]) for row in rows]
    check(len(observed) == len(set(observed)), "the pack repeats a primary key", failures)
    check(set(observed) == set(expected), "the pack is not the expected row space", failures)
    if failures:
        # The recomputations below assume a complete, deduplicated row space; a
        # violated primary key must fail closed here rather than surface as an
        # incidental lookup error further down.
        return report(False, failures)

    identities = {
        role: {"model_id": model_id, "resolved_revision": revision}
        for role, model_id, revision in s2.MODEL_IDENTITIES
    }
    for row in rows:
        s2.validate_json_schema(row, {**defs["behavioral_row"], "$defs": defs})
        try:
            bd.verify_behavioral_row(
                row,
                item=by_id[row["item_id"]],
                identity=identities[row["model_role"]],
                prompt_identity=index[(row["model_role"], row["item_id"], row["arm"])],
                tokens=tokens,
            )
        except bd.StageBDError as error:
            failures.append(f"{row['model_role']}/{row['item_id']}/{row['arm']}: {error}")

    recomputed_summaries = bd.summarize(rows)
    emitted_summaries = [
        json.loads(line)
        for line in (pack / "stage_bd_development_summaries.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    check(
        recomputed_summaries == emitted_summaries,
        "the emitted summaries are not the recomputed summaries",
        failures,
    )

    recomputed_diag = bd.bootstrap_diagnostics(rows, by_id)
    emitted_diag = [
        json.loads(line)
        for line in (pack / "stage_bd_bootstrap_diagnostics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    check(
        recomputed_diag == emitted_diag,
        "the emitted bootstrap diagnostics are not reproducible",
        failures,
    )

    recomputed_gate = bd.gate_a(rows, items)
    emitted_gate = [
        json.loads(line)
        for line in (pack / "stage_bd_feasibility_gate.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    check(
        recomputed_gate["feasibility_rows"] == emitted_gate,
        "the emitted feasibility rows are not the recomputed rows",
        failures,
    )
    decision = json.loads((pack / "stage_bd_gate_a_decision.json").read_text("utf-8"))
    s2.validate_json_schema(decision, {**defs["gate_a_decision"], "$defs": defs})
    check(
        decision["overall_gate_pass"] == recomputed_gate["overall_gate_pass"],
        "the recorded Gate A decision is not the recomputed decision",
        failures,
    )
    check(
        decision["gate_inputs_sha256"] == recomputed_gate["gate_inputs_sha256"],
        "the Gate A inputs digest does not bind the emitted rows",
        failures,
    )
    check(
        decision["confirmation_opened_before_decision"] is False,
        "Gate A recorded an opened confirmation object",
        failures,
    )

    shard = json.loads((pack / bd.SHARD_MANIFEST_NAME).read_text(encoding="utf-8"))
    s2.validate_json_schema(shard, {**defs["shard_manifest"], "$defs": defs})
    check(
        shard["shard_manifest_sha256"] == manifest["shard_manifest_sha256"],
        "the emitted shard manifest is not the reconstructed manifest",
        failures,
    )

    weights = json.loads((pack / "stage_bd_weight_identity_receipt.json").read_text("utf-8"))
    s2.validate_json_schema(weights, {**defs["weight_identity_receipt"], "$defs": defs})
    for model in weights["models"]:
        expected_revision = next(
            revision for role, _, revision in s2.MODEL_IDENTITIES if role == model["role"]
        )
        check(
            model["resolved_revision"] == expected_revision,
            f"{model['role']} weight receipt is not the pinned revision",
            failures,
        )
        check(
            model["trust_remote_code"] is False and model["use_cache"] is False,
            f"{model['role']} was not loaded under the registered flags",
            failures,
        )

    confirmation = json.loads(
        (pack / "stage_bd_confirmation_unopened_receipt.json").read_text("utf-8")
    )
    s2.validate_json_schema(
        confirmation, {**defs["confirmation_unopened_receipt"], "$defs": defs}
    )
    for field in (
        "behavioral_confirmation_forwards",
        "behavioral_confirmation_output_objects",
        "behavioral_confirmation_tokenizations",
        "confirmation_prompt_identities_loaded",
        "mechanistic_confirmation_operations",
    ):
        check(confirmation[field] == 0, f"{field} is not zero", failures)

    counts = core["operation_counts"]
    for field, value in counts.items():
        if field in {
            "forward_passes",
            "model_downloads",
            "tokenizer_constructions",
            "weight_loads",
        }:
            continue
        check(value == 0, f"operation count {field} is {value}, expected 0", failures)
    check(counts["forward_passes"] == bd.TOTAL_ROWS, "forward count is wrong", failures)

    ledger = REPO_ROOT / "paper/evidence_ledger.csv"
    text = ledger.read_text(encoding="utf-8")
    check(text.rstrip("\n").splitlines()[-1].startswith("EV-0016"), "ledger moved", failures)

    if failures:
        return report(False, failures)
    return report(
        True,
        failures,
        core_manifest_sha256=bd.sha256_bytes(manifest_path.read_bytes()),
        gate_inputs_sha256=recomputed_gate["gate_inputs_sha256"],
        overall_gate_pass=recomputed_gate["overall_gate_pass"],
        rows=len(rows),
        terminal_state=recomputed_gate["terminal_state"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
