#!/usr/bin/env python
"""Independently validate a sealed Study 2 Stage T pack.

This validator never constructs a tokenizer.  It re-derives eligibility joins
and the deterministic selection from the committed row packs alone, then proves
the selected JSONL files are byte-identical slices of the frozen Stage P banks.
Because it shares no code path with the runner's tokenization logic, agreement
between the two is evidence that the sealed pack is internally consistent, not
merely that one program agreed with itself.

It also refuses any Stage T row that carries an outcome field.  Stage T is a
mechanical gate; a logit, probability, accuracy, activation, probe, lens, or
patching value appearing anywhere in the pack is a preregistration failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
# Top-level module import, not the package: importing ``jspace_observation``
# would execute its ``__init__`` and pull ``model_loader``/``AutoModel*`` in.
sys.path.insert(0, str(REPO_ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_t as st  # noqa: E402

SCHEMA_PATH = "studies/study2/protocol/stage_t_pack.schema.json"
EVIDENCE_LEDGER = "paper/evidence_ledger.csv"
EVIDENCE_TAIL = "EV-0016"

FORBIDDEN_FIELD_TOKENS = (
    "logit",
    "accuracy",
    "probability",
    "activation",
    "probe",
    "lens_output",
    "patch",
    "ablation",
    "correct",
    "margin",
    "gate_a",
)

CORE_FILES = st.PACK_FILES

SELECTED_FILE_BY_ROLE = {
    "mechanistic_development": "stage_t_selected_mechanistic_development.jsonl",
    "mechanistic_candidate_confirmation": "stage_t_selected_mechanistic_confirmation.jsonl",
}


class ValidationError(RuntimeError):
    pass


def _read(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _rows(path: Path) -> list[dict[str, Any]]:
    raw = _read(path)
    if raw and not raw.endswith(b"\n"):
        raise ValidationError(f"{path.name} does not end with a newline")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def _scan_forbidden_fields(rows: Iterable[Mapping[str, Any]], where: str) -> None:
    for row in rows:
        for key in _all_keys(row):
            lowered = key.lower()
            if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
                raise ValidationError(f"outcome field {key!r} appeared in {where}")


def _all_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def validate(root: Path, pack_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    st.verify_frozen_inputs(root)
    s2.verify_protected_anchors(root)

    schema = json.loads((root / SCHEMA_PATH).read_text(encoding="utf-8"))
    s2.verify_schema_closed(schema)
    defs = schema["$defs"]

    manifest = json.loads((pack_dir / st.CORE_MANIFEST_NAME).read_text(encoding="utf-8"))
    s2.validate_json_schema(manifest, {**defs["core_manifest"], "$defs": defs})
    declared = set(manifest["files"])
    if declared != set(CORE_FILES):
        raise ValidationError(f"core manifest file set drift: {sorted(declared)}")
    present = {
        path.name
        for path in pack_dir.iterdir()
        if path.is_file() and not path.name.startswith(st.ATTEMPT_RECEIPT_PREFIX)
    }
    if present != set(CORE_FILES) | {st.CORE_MANIFEST_NAME}:
        raise ValidationError(
            f"pack directory drift: {sorted(present ^ (set(CORE_FILES) | {st.CORE_MANIFEST_NAME}))}"
        )

    for name, row in sorted(manifest["files"].items()):
        raw = _read(pack_dir / name)
        if len(raw) != row["bytes"] or st.sha256_bytes(raw) != row["sha256"]:
            failures.append(f"file drift: {name}")

    banks = st.load_frozen_banks(root)
    prompt_rows = st.iter_prompt_rows(banks)
    expected_prompt_keys = [
        (row["bank"], row["row_id"], row["arm"]) for row in prompt_rows
    ]
    prompt_hash_by_key = {
        key: row["prompt_sha256"] for key, row in zip(expected_prompt_keys, prompt_rows)
    }

    prompt_packs: dict[str, list[dict[str, Any]]] = {}
    option_ids: dict[str, dict[str, int]] = {}
    for role in st.MODEL_ROLES:
        rows = _rows(pack_dir / f"stage_t_prompt_tokenization_{role}.jsonl")
        _scan_forbidden_fields(rows, f"prompt pack {role}")
        for row in rows:
            s2.validate_json_schema(row, {**defs["prompt_row"], "$defs": defs})
        keys = [(row["bank"], row["row_id"], row["arm"]) for row in rows]
        if keys != expected_prompt_keys:
            failures.append(f"{role}: prompt pack rows are not the frozen enumeration")
        if len(set(keys)) != len(keys):
            failures.append(f"{role}: duplicate prompt rows")
        for row, key in zip(rows, keys):
            if row["prompt_sha256"] != prompt_hash_by_key.get(key):
                failures.append(f"{role}: prompt hash drift at {key}")
                break
        bad = [row for row in rows if row["status"] != "PASS"]
        if bad:
            failures.append(f"{role}: {len(bad)} prompt rows failed the option gate")
        seen: set[tuple[int, ...]] = set()
        for row in rows:
            if row["option_token_ids"]:
                seen.add(tuple(row["option_token_ids"][label] for label in st.OPTION_LABELS))
        if len(seen) != 1:
            failures.append(f"{role}: option token IDs are not constant across prompts")
        else:
            values = next(iter(seen))
            if len(set(values)) != len(st.OPTION_LABELS):
                failures.append(f"{role}: option token IDs are not pairwise distinct")
            option_ids[role] = dict(zip(st.OPTION_LABELS, (int(v) for v in values)))
        for row in rows:
            if row["status"] == "PASS" and row["answer_position_index"] != row["input_length"] - 1:
                failures.append(f"{role}: answer position is not the final input position")
                break
        prompt_packs[role] = rows

    lookup = {
        role: {
            (row["bank"], row["row_id"], row["arm"]): row for row in prompt_packs[role]
        }
        for role in st.MODEL_ROLES
    }

    eligibility: dict[str, dict[str, dict[str, Any]]] = {}
    for role in st.MODEL_ROLES:
        rows = _rows(pack_dir / f"stage_t_mechanistic_eligibility_{role}.jsonl")
        _scan_forbidden_fields(rows, f"eligibility pack {role}")
        for row in rows:
            s2.validate_json_schema(row, {**defs["eligibility_row"], "$defs": defs})
        if len({row["pair_id"] for row in rows}) != len(rows):
            failures.append(f"{role}: duplicate eligibility rows")
        eligibility[role] = {row["pair_id"]: row for row in rows}

        for bank in st.MECHANISTIC_BANKS:
            for _, pair in banks[bank]:
                row = eligibility[role].get(pair["pair_id"])
                if row is None:
                    failures.append(f"{role}: missing eligibility row for {pair['pair_id']}")
                    break
                lengths = {
                    name: lookup[role][(bank, pair["pair_id"], name)]["input_length"]
                    for name in st.PAIR_OBJECT_KEYS
                }
                if row["object_input_lengths"] != lengths:
                    failures.append(f"{role}: eligibility lengths disagree with the prompt pack")
                    break
                aligned = len({value for value in lengths.values() if value is not None}) == 1
                if row["eligible"] != (aligned and not row["reason_codes"]):
                    failures.append(f"{role}: eligibility flag disagrees with its own evidence")
                    break
                if row["eligible"] and row["wrong_position_index"] is None:
                    failures.append(f"{role}: eligible pair has an unresolved wrong-position anchor")
                    break

    joint = _rows(pack_dir / "stage_t_pair_joint_eligibility.jsonl")
    _scan_forbidden_fields(joint, "joint eligibility")
    for row in joint:
        s2.validate_json_schema(row, {**defs["joint_row"], "$defs": defs})
    if len({row["pair_id"] for row in joint}) != len(joint):
        failures.append("duplicate joint eligibility rows")
    for row in joint:
        flags = {role: eligibility[role][row["pair_id"]]["eligible"] for role in st.MODEL_ROLES}
        if row["model_eligibility"] != flags:
            failures.append(f"joint flags drift at {row['pair_id']}")
            break
        if row["eligible_all_models"] != all(flags.values()):
            failures.append(f"joint conjunction drift at {row['pair_id']}")
            break

    recomputed = st.select_pairs(
        [
            {
                "depth": row["depth"],
                "eligible_all_models": row["eligible_all_models"],
                "family": row["family"],
                "pair_id": row["pair_id"],
                "pair_semantic_id": row["pair_semantic_id"],
                "role": row["role"],
                "selected": False,
                "selection_rank": None,
            }
            for row in joint
        ]
    )
    if not recomputed["sufficient"]:
        failures.append(f"independent selection is short: {recomputed['shortfalls']}")
    for key, cell in recomputed["cells"].items():
        recorded = manifest["selection"]["cells"].get(key)
        if recorded is None or recorded["selected_pair_ids"] != cell["selected_pair_ids"]:
            failures.append(f"selection drift in cell {key}")

    annotations = _rows(pack_dir / "stage_t_selected_annotations.jsonl")
    _scan_forbidden_fields(annotations, "selected annotations")
    for row in annotations:
        s2.validate_json_schema(row, {**defs["annotation_row"], "$defs": defs})

    for role, filename in SELECTED_FILE_BY_ROLE.items():
        source = {pair["pair_id"]: line for line, pair in banks[role]}
        payload = _read(pack_dir / filename)
        lines = payload.split(b"\n")[:-1] if payload else []
        subset = [row for row in annotations if row["role"] == role]
        if len(lines) != st.SELECTED_PER_ROLE or len(subset) != st.SELECTED_PER_ROLE:
            failures.append(
                f"{role}: selected {len(lines)} rows / {len(subset)} annotations, "
                f"expected {st.SELECTED_PER_ROLE}"
            )
            continue
        for line, annotation in zip(lines, subset):
            if line != source[annotation["pair_id"]]:
                failures.append(f"{role}: selected row is not a byte-exact frozen row")
                break
            if st.sha256_bytes(line) != annotation["source_row_sha256"]:
                failures.append(f"{role}: annotation hash drift")
                break
        chosen = {row["pair_id"] for row in subset}
        expected = {
            pair_id
            for key, cell in recomputed["cells"].items()
            if key.startswith(f"{role}|")
            for pair_id in cell["selected_pair_ids"]
        }
        if chosen != expected:
            failures.append(f"{role}: selected set differs from the independent selection")

    identity = json.loads((pack_dir / "stage_t_identity_receipt.json").read_text(encoding="utf-8"))
    s2.validate_json_schema(identity, {**defs["identity_receipt"], "$defs": defs})
    registered = {row[0]: row for row in s2.MODEL_IDENTITIES}
    for entry in identity["models"]:
        _, model_id, revision = registered[entry["role"]]
        if entry["model_id"] != model_id or entry["resolved_revision"] != revision:
            failures.append(f"identity drift for {entry['role']}")
        if entry["weight_files_present"] or st.classify_weight_files(
            item["name"] for item in entry["files"]
        ):
            failures.append(f"weight file reached the {entry['role']} snapshot")
        if entry["option_token_ids"] != option_ids.get(entry["role"]):
            failures.append(f"receipt option IDs disagree with the prompt pack for {entry['role']}")

    digits = json.loads((pack_dir / "stage_t_jlens_digit_support.json").read_text(encoding="utf-8"))
    s2.validate_json_schema(digits, {**defs["digit_support"], "$defs": defs})

    receipts = sorted(
        path
        for path in pack_dir.iterdir()
        if path.is_file() and path.name.startswith(st.ATTEMPT_RECEIPT_PREFIX)
    )
    if not receipts:
        failures.append("no Stage T attempt receipt is present")
    manifest_sha = st.sha256_bytes(_read(pack_dir / st.CORE_MANIFEST_NAME))
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        s2.validate_json_schema(receipt, {**defs["attempt_receipt"], "$defs": defs})
        if receipt["core_manifest_sha256"] != manifest_sha:
            failures.append(f"{path.name}: attempt receipt does not bind this core manifest")
        if not receipt["weight_load_interlock"]:
            failures.append(f"{path.name}: no weight-load interlock was installed")

    ledger = _read(root / EVIDENCE_LEDGER).decode("utf-8").rstrip("\n").splitlines()
    if not ledger[-1].startswith(EVIDENCE_TAIL + ","):
        failures.append("paper/evidence_ledger.csv no longer ends at EV-0016")

    for name, count in sorted(manifest["operation_counts"].items()):
        if name != "tokenizer_constructions" and count != 0:
            failures.append(f"non-zero operation count: {name}={count}")
    if manifest["operation_counts"]["tokenizer_constructions"] != len(st.MODEL_ROLES):
        failures.append("tokenizer construction count is not exactly three")
    if manifest["terminal_state"] != st.TERMINAL_STATE:
        failures.append(f"terminal state is {manifest['terminal_state']!r}")

    return {
        "core_manifest_sha256": st.sha256_bytes(_read(pack_dir / st.CORE_MANIFEST_NAME)),
        "failures": failures,
        "joint_eligible_pairs": sum(1 for row in joint if row["eligible_all_models"]),
        "option_token_ids": option_ids,
        "prompt_rows_per_model": len(prompt_rows),
        "selected_total": sum(
            len(cell["selected_pair_ids"]) for cell in recomputed["cells"].values()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--pack-dir", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    pack_dir = Path(args.pack_dir) if args.pack_dir else root / st.OUTPUT_DIR
    report = validate(root, pack_dir)

    if args.json:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        for key, value in sorted(report.items()):
            print(f"{key}={value}")
    if report["failures"]:
        print("STAGE_T_VALIDATION_FAILED=1")
        return 1
    print("STAGE_T_VALIDATION_OK=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
