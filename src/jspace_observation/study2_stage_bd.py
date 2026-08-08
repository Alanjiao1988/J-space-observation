"""Study 2 Stage B-D: development-only behavioral execution and Gate A.

Stage B-D runs the frozen four-option observable over the 384-item development
bank under every applicable arm, for the three registered checkpoints, and then
evaluates the pre-registered Gate A feasibility rule.  Gate A is an interface
feasibility decision, not scientific evidence: nothing here supports a claim
about reasoning, internalized chain of thought, distillation, or J-space.

What this module deliberately does not contain:

* no generation, sampling, KV-cache decoding, or chat template;
* no hidden-state retention, hook, probe, patch, ablation, or lens;
* no behavioral-confirmation, mechanistic-development, or mechanistic-
  confirmation input path -- those objects are not addressable from here;
* no infrastructure identity in a deterministic core artifact.  Run IDs are the
  registered deterministic constant; cloud execution IDs, image digests and
  timings live only in attempt receipts.

The module holds the closed contract, the deterministic writer, the registered
derived calculations and the Gate A finalizer.  The forward pass itself lives in
``scripts/run_study2_stage_bd_gpu.py``: this file never imports torch and never
touches a model class.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import study2_protocol as s2
import study2_stage_t as st

SCHEMA_VERSION = "jspace-study2-stage-bd/v1"
SHARD_MANIFEST_VERSION = "jspace-study2-stage-bd-shard-manifest/v1"
SHARD_RECEIPT_VERSION = "jspace-study2-stage-bd-shard-receipt/v1"
EXECUTION_RECEIPT_VERSION = "jspace-study2-stage-bd-execution-receipt/v1"
WEIGHT_IDENTITY_VERSION = "jspace-study2-stage-bd-weight-identity/v1"
SUMMARY_ROW_VERSION = "jspace-study2-stage-bd-summary-row/v1"
BOOTSTRAP_ROW_VERSION = "jspace-study2-stage-bd-bootstrap-row/v1"
CONFIRMATION_RECEIPT_VERSION = "jspace-study2-stage-bd-confirmation-receipt/v1"
CORE_MANIFEST_VERSION = "jspace-study2-stage-bd-core-manifest/v1"
ATTEMPT_RECEIPT_VERSION = "jspace-study2-stage-bd-attempt/v1"
SEAL_VERSION = "jspace-study2-stage-bd-preinference-seal/v1"

# The additive Stage B-D operator authority, byte-identical to the operator text.
AUTHORITY_PATH = "studies/study2/prompts/study2_stage_bd_operator_authority.md"
AUTHORITY_BYTES = 25_173
AUTHORITY_SHA256 = "f6932e50cf5692ef01df9b5b8a930a3941de9620a7404653c92ffd4e9ea7e8ed"

STAGE_BD_START_COMMIT = "a958adf4aec5736ef04f468fc3532ca7c92f7e5e"
STAGE_BD_START_TREE = "f96729c41dcbd8b20e156177e2533516cb44a1ef"
STAGE_P_HANDOFF_COMMIT = "c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1"
STAGE_P_FREEZE_COMMIT = "d5e8e19c025410fda7c9eb430f507a201a18c9cd"

STARTING_STATE_DISPOSITION = (
    "STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE"
)
GATE_A_PASS_STATE = (
    "NONTERMINAL_CHECKPOINT_STUDY2_STAGE_BD_GATE_A_PASSED_AWAITING_BC_AUTHORITY"
)
GATE_A_FAIL_STATE = "STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY"

# The one deterministic run identity carried by every core row.  Cloud execution
# identifiers never enter a deterministic artifact.
RUN_ID = "s2-bd-development-v1"
PROTOCOL_VERSION = s2.SCHEMA_VERSION

MODEL_ROLES = ("target", "lineage_base", "instruction_control")
ARMS = ("NT", "PT", "WT", "ST")
ARM_DEPTHS: dict[str, tuple[int, ...]] = {
    "NT": (1, 2, 3),
    "PT": (2, 3),
    "WT": (2, 3),
    "ST": (3,),
}
DEVELOPMENT_BANK = "studies/study2/data/development.jsonl"
DEVELOPMENT_ITEMS = 384
ROWS_PER_MODEL = 1_024
TOTAL_ROWS = 3_072
GENERATED_TOKENS = 0

# Gate A, restated from the frozen protocol so a drift is a loud failure here
# rather than a silent reinterpretation downstream.
GATE_DECISION_MODEL = "target"
GATE_DECISION_ARM = "NT"
GATE_DEPTHS = (2, 3)
GATE_ROWS_PER_DEPTH = 64
GATE_N_PER_FAMILY = 128
GATE_CRITICAL_SUCCESSES = 43
GATE_ALPHA = 0.025
GATE_NULL_ACCURACY = 0.25

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_LOWER = 0.025
BOOTSTRAP_UPPER = 0.975

# Every object Stage B-D must never open as a scientific input.  The GPU image
# context excludes them and the runner refuses to read them.
CONFIRMATION_PATHS = (
    "studies/study2/data/behavioral_confirmation.jsonl",
    "studies/study2/data/mechanistic_candidate_pairs.jsonl",
    "studies/study2/stage_t/stage_t_selected_mechanistic_confirmation.jsonl",
    "studies/study2/stage_t/stage_t_mechanistic_eligibility_instruction_control.jsonl",
    "studies/study2/stage_t/stage_t_mechanistic_eligibility_lineage_base.jsonl",
    "studies/study2/stage_t/stage_t_mechanistic_eligibility_target.jsonl",
)

# Frozen inputs Stage B-D reads.  Any drift is a starting-state stop, never a
# thing to reconcile.
FROZEN_INPUTS: dict[str, tuple[int, str]] = {
    "studies/study2/STAGE_T_FINAL_HANDOFF.md": (
        11_015,
        "e0c475c7bd826f25cd6956a531dc0d95abf7cc8478b72e623d44424a52766bef",
    ),
    "studies/study2/STAGE_T_AUTHORITY_RECEIPT.md": (
        22_416,
        "e048be75ebbd4402e62794fc7ff8558deec2f3464b449651094dd4175a0a14e5",
    ),
    "docs/decisions/study2_stage_t_tokenizer_gate.md": (
        9_542,
        "65a23e1176aff3405a4872d274512b80bb888e23f4a13bf9fc5f226dc29a6bde",
    ),
    "studies/study2/stage_t/stage_t_core_manifest.json": (
        149_948,
        "6dec7650a05533efc5d88ba9ac1e3a498ca977a091a25b52155bbdb452622815",
    ),
    "studies/study2/stage_t/stage_t_identity_receipt.json": (
        3_684,
        "abe5113d4eeef2a47ffa047e34d7a7ce3e9274ef3f86e02b494bdd6d05a4dc40",
    ),
    "studies/study2/stage_t/stage_t_prompt_tokenization_target.jsonl": (
        8_991_072,
        "e865e3c41db585a48637f92f287edbeba93fc33d53c4fa7b2aa45c869c721eb0",
    ),
    "studies/study2/stage_t/stage_t_prompt_tokenization_lineage_base.jsonl": (
        9_095_520,
        "995f89aed40bbc7031ba2bfc099d1886adc32f6de2c0b97701b6cf322753f1c7",
    ),
    "studies/study2/stage_t/stage_t_prompt_tokenization_instruction_control.jsonl": (
        9_217_376,
        "79b0c313bc27bbc1a7c5261a13fb6602cf62b975dc7764af77e5485a986d2c79",
    ),
    "studies/study2/RESEARCH_CHARTER.md": (
        4_462,
        "8b38a1d2d85845b4cee466f0428ff8389069f3cd1d08b78dd895e1db851680b7",
    ),
    "studies/study2/STAGE_P_FINAL_HANDOFF.md": (
        16_380,
        "4801d1b52622ade4d6badd9e1b4c37bb3038e7060c39e40faf7c2512e2a8a2e9",
    ),
    "studies/study2/data/task_bank_manifest.json": (
        32_337,
        "7d07db2b508136229f06a727a3deb787106e2b389bb1207ab2c2d1099b21458f",
    ),
    "studies/study2/decisions/reasoning_internalization_protocol_freeze.md": (
        5_025,
        "aa0151be87a43719ef8056b45d532281178ca5ea55480d46b0f7d484c7caff4d",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.md": (
        21_151,
        "4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.json": (
        39_357,
        "2f115e057249fb59e34ef34de2eb71ff042a449bb4ef1637ebec3181aedd7ad5",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.schema.json": (
        54_502,
        "d9f834282038f840707ea694bb5dd5422e87a3ca661eb987b2b9ce631d23b134",
    ),
    "studies/study2/prompts/stage_p_protocol_design_prompt.md": (
        53_018,
        "1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37",
    ),
    "studies/study2/prompts/stage_p_gate_a_operator_amendment.md": (
        5_836,
        "e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1",
    ),
    DEVELOPMENT_BANK: (
        752_708,
        "7dd19884cc2cb4685863cc9df768347f7cfd52c348e5117ec574b52d3b0cf1d6",
    ),
    "paper/evidence_ledger.csv": (
        25_241,
        "3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1",
    ),
    AUTHORITY_PATH: (AUTHORITY_BYTES, AUTHORITY_SHA256),
}

# Stage T prompt-identity files, one per role.  Only the development rows are
# consumed; the confirmation and mechanistic rows of these sealed files are
# never used as an inference input.
STAGE_T_PROMPT_FILES = {
    "target": "studies/study2/stage_t/stage_t_prompt_tokenization_target.jsonl",
    "lineage_base": (
        "studies/study2/stage_t/stage_t_prompt_tokenization_lineage_base.jsonl"
    ),
    "instruction_control": (
        "studies/study2/stage_t/stage_t_prompt_tokenization_instruction_control.jsonl"
    ),
}

CONFIG_FILE_ALLOWLIST = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)
WEIGHT_FILE_SUFFIXES = (".safetensors", ".safetensors.index.json")

# The seven registered Stage B-D execution reason codes.  HOOK_NOOP_MISMATCH is
# a mechanistic-stage code and is deliberately excluded: Stage B-D installs no
# hook, so it can never be a legitimate B-D retry reason.
RETRY_REASONS: tuple[str, ...] = (
    "ARTIFACT_WRITE_FAILURE",
    "CAPACITY_UNAVAILABLE",
    "HASH_MISMATCH",
    "MISSING_ROW",
    "NONFINITE_OUTPUT",
    "RUNTIME_EXCEPTION",
    "SOURCE_IMAGE_MISMATCH",
)
if not set(RETRY_REASONS) <= set(s2.EXECUTION_BLOCKER_REASONS):
    raise RuntimeError("Stage B-D retry reasons drifted from the frozen protocol")
MAX_SHARD_ATTEMPTS = 3
SHARD_COUNT = len(MODEL_ROLES) * len(s2.FAMILIES) * len(s2.DEPTHS)
BOOTSTRAP_STATISTICS = (
    "NT_MEAN_CORRECT_MARGIN",
    "SHUFFLE_DAMAGE",
    "TRACE_GAIN",
    "WRONG_TRACE_PULL",
)


class StageBDError(RuntimeError):
    """Any Stage B-D contract violation.  Always fatal, never recovered from."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json_bytes(value: Any) -> bytes:
    return s2.canonical_json_bytes(value)


def ids_sha256(token_ids: Sequence[int]) -> str:
    """The Stage T token-ID digest, reused verbatim so the identity is one thing."""

    return st.ids_sha256(token_ids)


def verify_frozen_inputs(root: Path) -> dict[str, dict[str, Any]]:
    verified: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for relative, (expected_bytes, expected_sha) in sorted(FROZEN_INPUTS.items()):
        path = root / relative
        if not path.is_file():
            failures.append(f"missing frozen input: {relative}")
            continue
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        digest = sha256_bytes(raw)
        if len(raw) != expected_bytes or digest != expected_sha:
            failures.append(
                f"frozen input drift: {relative} bytes={len(raw)} "
                f"expected={expected_bytes} sha256={digest} expected={expected_sha}"
            )
            continue
        verified[relative] = {"bytes": len(raw), "sha256": digest}
    if failures:
        raise StageBDError("; ".join(failures))
    return verified


def assert_confirmation_unaddressable(
    root: Path, *, model_free_integrity_reads: int = 0
) -> dict[str, Any]:
    """Prove the confirmation objects are absent from this execution context."""

    present = sorted(
        relative for relative in CONFIRMATION_PATHS if (root / relative).exists()
    )
    if present:
        raise StageBDError(
            "confirmation objects are addressable in an inference context: "
            + ", ".join(present)
        )
    return {
        "behavioral_confirmation_forwards": 0,
        "behavioral_confirmation_output_objects": 0,
        "behavioral_confirmation_tokenizations": 0,
        "confirmation_paths": list(CONFIRMATION_PATHS),
        "confirmation_prompt_identities_loaded": 0,
        "development_only_prompt_rows": TOTAL_ROWS,
        "mechanistic_confirmation_operations": 0,
        "model_free_integrity_reads": int(model_free_integrity_reads),
        "run_id": RUN_ID,
        "schema_version": CONFIRMATION_RECEIPT_VERSION,
    }


def verify_confirmation_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Re-check a confirmation receipt produced in an inference context.

    Only the GPU execution context can honestly assert that the confirmation
    objects were unaddressable, because only there are they absent from the
    filesystem.  Downstream model-free stages therefore carry that receipt
    forward rather than recomputing it against a full checkout.
    """

    expected = {
        "behavioral_confirmation_forwards",
        "behavioral_confirmation_output_objects",
        "behavioral_confirmation_tokenizations",
        "confirmation_prompt_identities_loaded",
        "mechanistic_confirmation_operations",
        "model_free_integrity_reads",
    }
    for field in sorted(expected):
        if receipt.get(field) != 0:
            raise StageBDError(f"confirmation receipt reports {field}={receipt.get(field)}")
    if list(receipt.get("confirmation_paths", ())) != list(CONFIRMATION_PATHS):
        raise StageBDError("confirmation receipt does not cover the registered paths")
    if receipt.get("development_only_prompt_rows") != TOTAL_ROWS:
        raise StageBDError("confirmation receipt does not cover the development row space")
    if receipt.get("run_id") != RUN_ID or receipt.get("schema_version") != (
        CONFIRMATION_RECEIPT_VERSION
    ):
        raise StageBDError("confirmation receipt is not this run's registered receipt")
    return dict(receipt)


def _reject_constant(literal: str) -> Any:
    raise StageBDError(f"non-finite JSON literal in a frozen input: {literal}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if not raw.endswith(b"\n"):
        raise StageBDError(f"jsonl does not end with a newline: {path.name}")
    rows: list[dict[str, Any]] = []
    for line in raw.split(b"\n")[:-1]:
        document = json.loads(
            line.decode("utf-8"),
            object_pairs_hook=s2._pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
        if not isinstance(document, dict):
            raise StageBDError(f"jsonl row is not an object: {path.name}")
        rows.append(document)
    return rows


def load_development_bank(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / DEVELOPMENT_BANK)
    if len(rows) != DEVELOPMENT_ITEMS:
        raise StageBDError(
            f"development bank has {len(rows)} rows, expected {DEVELOPMENT_ITEMS}"
        )
    for row in rows:
        if row.get("role") != "development":
            raise StageBDError(f"development bank row has role {row.get('role')!r}")
        s2.verify_task_row(row)
        for arm in sorted(row["prompts"]):
            if arm not in ARMS or row["depth"] not in ARM_DEPTHS[arm]:
                raise StageBDError(
                    f"{row['item_id']} carries arm {arm} at depth {row['depth']}"
                )
        expected_arms = {arm for arm in ARMS if row["depth"] in ARM_DEPTHS[arm]}
        if set(row["prompts"]) != expected_arms:
            raise StageBDError(
                f"{row['item_id']} arms {sorted(row['prompts'])} != {sorted(expected_arms)}"
            )
    ids = [row["item_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise StageBDError("development bank contains a duplicate item_id")
    return rows


def load_stage_t_identity(root: Path) -> dict[str, dict[str, Any]]:
    """The sealed Stage T config/tokenizer identity, keyed by model role."""

    receipt = json.loads(
        (root / "studies/study2/stage_t/stage_t_identity_receipt.json")
        .read_bytes()
        .replace(b"\r\n", b"\n")
        .decode("utf-8"),
        object_pairs_hook=s2._pairs_without_duplicates,
        parse_constant=_reject_constant,
    )
    identity = {entry["role"]: entry for entry in receipt["models"]}
    if set(identity) != set(MODEL_ROLES):
        raise StageBDError("Stage T identity receipt does not cover the three roles")
    for role, model_id, revision in s2.MODEL_IDENTITIES:
        entry = identity[role]
        if entry["model_id"] != model_id or entry["resolved_revision"] != revision:
            raise StageBDError(f"Stage T identity for {role} is not the pinned model")
        if entry["requested_revision"] != revision:
            raise StageBDError(f"Stage T requested revision for {role} is not pinned")
        if entry["trust_remote_code"] is not False:
            raise StageBDError(f"Stage T identity for {role} allowed remote code")
    return identity


def load_development_prompts(root: Path) -> dict[tuple[str, str], str]:
    """Every development prompt string, keyed by (item_id, arm).

    The bank carries its own registered ``prompt_hashes``; each prompt is
    checked against that value here so a corrupted read cannot reach a
    tokenizer, and the sealed Stage T ``prompt_sha256`` is checked again at
    forward time.  Only development rows are ever returned.
    """

    prompts: dict[tuple[str, str], str] = {}
    for item in load_development_bank(root):
        for arm in item_arms(item):
            prompt = item["prompts"][arm]
            if sha256_text(prompt) != item["prompt_hashes"][arm]:
                raise StageBDError(
                    f"development prompt {item['item_id']}/{arm} does not match its "
                    "registered hash"
                )
            prompts[(item["item_id"], arm)] = prompt
    if len(prompts) != TOTAL_ROWS // len(MODEL_ROLES):
        raise StageBDError(f"loaded {len(prompts)} development prompts")
    return prompts


def load_stage_t_development_index(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Development-only prompt identities from the sealed Stage T pack.

    The sealed files also carry confirmation and mechanistic rows.  Those rows
    are dropped here and never returned, so no confirmation prompt identity can
    reach an inference path through this index.
    """

    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for role in MODEL_ROLES:
        rows = _read_jsonl(root / STAGE_T_PROMPT_FILES[role])
        kept = 0
        for row in rows:
            if row["bank"] != "development":
                continue
            if row["model_role"] != role:
                raise StageBDError(f"Stage T row model_role {row['model_role']} != {role}")
            if row["status"] != "PASS" or row["failure_reasons"]:
                raise StageBDError(
                    f"Stage T development row {row['row_id']}/{row['arm']} is not PASS"
                )
            key = (role, row["row_id"], row["arm"])
            if key in index:
                raise StageBDError(f"duplicate Stage T development row: {key}")
            index[key] = {
                "answer_position": row["answer_position_index"],
                "input_ids_sha256": row["input_ids_sha256"],
                "input_length": row["input_length"],
                "option_token_ids": dict(row["option_token_ids"]),
                "prompt_sha256": row["prompt_sha256"],
            }
            kept += 1
        if kept != ROWS_PER_MODEL:
            raise StageBDError(
                f"Stage T carries {kept} development rows for {role}, expected {ROWS_PER_MODEL}"
            )
    return index


def option_token_ids(index: Mapping[tuple[str, str, str], Mapping[str, Any]]) -> dict[str, int]:
    """The single option token-ID mapping every development row must share."""

    distinct = {
        canonical_json_bytes(entry["option_token_ids"]) for entry in index.values()
    }
    if len(distinct) != 1:
        raise StageBDError("Stage T development rows disagree on option token IDs")
    mapping = json.loads(next(iter(distinct)).decode("utf-8"))
    if sorted(mapping) != list(s2.LABELS):
        raise StageBDError("option token IDs are not exactly A/B/C/D")
    return {label: int(mapping[label]) for label in s2.LABELS}


def item_arms(item: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(arm for arm in ARMS if item["depth"] in ARM_DEPTHS[arm])


def expected_row_keys(items: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str]]:
    """Every logical row, once, in the one fixed order Stage B-D uses."""

    keys: list[tuple[str, str, str]] = []
    for role in MODEL_ROLES:
        for item in sorted(items, key=lambda row: row["item_id"]):
            for arm in item_arms(item):
                keys.append((role, item["item_id"], arm))
    if len(set(keys)) != len(keys):
        raise StageBDError("expected row keys contain a duplicate")
    if len(keys) != TOTAL_ROWS:
        raise StageBDError(f"expected {TOTAL_ROWS} rows, planned {len(keys)}")
    return keys


def shard_id(role: str, family: str, depth: int) -> str:
    return f"{role}/{family}/d{depth}"


def build_shard_manifest(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """An immutable, outcome-independent partition of all 3,072 logical rows.

    Boundaries are role x family x depth.  Every arm of an item stays inside one
    shard, so model/item/arm pairing is never split across a checkpoint.
    """

    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for role, item_id, arm in expected_row_keys(items):
        item = next(row for row in items if row["item_id"] == item_id)
        grouped[shard_id(role, item["family"], item["depth"])].append((role, item_id, arm))

    shards: list[dict[str, Any]] = []
    for index, key in enumerate(sorted(grouped)):
        rows = grouped[key]
        payload = "\n".join("|".join(row) for row in rows)
        shards.append(
            {
                "depth": int(key.rsplit("/d", 1)[1]),
                "family": key.split("/")[1],
                "model_role": key.split("/")[0],
                "row_count": len(rows),
                "row_keys_sha256": sha256_text(
                    f"jspace-study2-stage-bd/shard-rows/v1\n{payload}\n"
                ),
                "shard_id": key,
                "shard_index": index,
            }
        )
    total = sum(shard["row_count"] for shard in shards)
    if total != TOTAL_ROWS:
        raise StageBDError(f"shard manifest covers {total} rows, expected {TOTAL_ROWS}")
    if len({shard["shard_id"] for shard in shards}) != len(shards):
        raise StageBDError("shard manifest contains a duplicate shard_id")
    manifest = {
        "expected_rows_per_model": ROWS_PER_MODEL,
        "max_shard_attempts": MAX_SHARD_ATTEMPTS,
        "retry_reason_codes": list(RETRY_REASONS),
        "run_id": RUN_ID,
        "schema_version": SHARD_MANIFEST_VERSION,
        "shard_count": len(shards),
        "shards": shards,
        "total_rows": total,
    }
    manifest["shard_manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    return manifest


def attempt_id(shard: str, attempt: int) -> str:
    """Idempotent, content-derived attempt identity for one shard try."""

    if attempt < 1 or attempt > MAX_SHARD_ATTEMPTS:
        raise StageBDError(f"attempt {attempt} is outside the registered retry bound")
    digest = sha256_text(f"jspace-study2-stage-bd/attempt/v1\n{RUN_ID}\n{shard}\n{attempt}\n")
    return f"bd-{digest[:16]}"


def full_vocab_ranks(
    logits: Sequence[float], tokens: Mapping[str, int]
) -> tuple[list[int], int]:
    """One-based descending ranks of the four option tokens, plus the top-1 id."""

    values = list(logits)
    if not values:
        raise StageBDError("full-vocabulary logits are empty")
    if any(not math.isfinite(float(value)) for value in values):
        raise StageBDError("full-vocabulary logits contain a non-finite value")
    ranks: list[int] = []
    for label in s2.LABELS:
        token = tokens[label]
        if not 0 <= token < len(values):
            raise StageBDError(f"option token {token} is outside the vocabulary")
        target = values[token]
        ranks.append(sum(1 for value in values if value > target) + 1)
    top1 = max(range(len(values)), key=lambda index: (values[index], -index))
    return ranks, int(top1)


def behavioral_row(
    *,
    item: Mapping[str, Any],
    role: str,
    arm: str,
    identity: Mapping[str, Any],
    prompt_identity: Mapping[str, Any],
    tokens: Mapping[str, int],
    option_logits: Mapping[str, float],
    option_ranks: Sequence[int],
    top1_token_id: int,
) -> dict[str, Any]:
    """One closed behavioral row, exactly the frozen future-table field set."""

    if arm not in ARMS or item["depth"] not in ARM_DEPTHS[arm]:
        raise StageBDError(f"arm {arm} is not applicable at depth {item['depth']}")
    if sorted(option_logits) != list(s2.LABELS):
        raise StageBDError("option logits must be exactly A/B/C/D")
    values = {label: float(option_logits[label]) for label in s2.LABELS}
    if any(not math.isfinite(value) for value in values.values()):
        raise StageBDError("option logits contain a non-finite value")
    if len(option_ranks) != len(s2.LABELS):
        raise StageBDError("full-vocabulary option ranks must have four entries")

    probabilities = s2.restricted_probabilities(values)
    prediction = s2.restricted_prediction(values)
    correct_label = item["correct_label"]
    margin = s2.correct_margin(values, correct_label)
    return {
        "answer_position": int(prompt_identity["answer_position"]),
        "arm": arm,
        "correct": prediction == correct_label,
        "correct_label": correct_label,
        "correct_margin": margin,
        "depth": int(item["depth"]),
        "execution_status": "complete",
        "family": item["family"],
        "finite": True,
        "full_vocab_option_ranks": [int(value) for value in option_ranks],
        "full_vocab_top1_token_id": int(top1_token_id),
        "input_ids_sha256": prompt_identity["input_ids_sha256"],
        "input_length": int(prompt_identity["input_length"]),
        "item_id": item["item_id"],
        "model_id": identity["model_id"],
        "model_revision": identity["resolved_revision"],
        "model_role": role,
        "option_logits": [values[label] for label in s2.LABELS],
        "option_token_ids": [int(tokens[label]) for label in s2.LABELS],
        "prompt_sha256": prompt_identity["prompt_sha256"],
        "restricted_prediction": prediction,
        "restricted_probabilities": [probabilities[label] for label in s2.LABELS],
        "run_id": RUN_ID,
        "semantic_id": item["semantic_id"],
        "template_id": item["template_id"],
    }


BEHAVIORAL_ROW_KEYS = frozenset(
    {
        "answer_position",
        "arm",
        "correct",
        "correct_label",
        "correct_margin",
        "depth",
        "execution_status",
        "family",
        "finite",
        "full_vocab_option_ranks",
        "full_vocab_top1_token_id",
        "input_ids_sha256",
        "input_length",
        "item_id",
        "model_id",
        "model_revision",
        "model_role",
        "option_logits",
        "option_token_ids",
        "prompt_sha256",
        "restricted_prediction",
        "restricted_probabilities",
        "run_id",
        "semantic_id",
        "template_id",
    }
)


def verify_behavioral_row(
    row: Mapping[str, Any],
    *,
    item: Mapping[str, Any],
    identity: Mapping[str, Any],
    prompt_identity: Mapping[str, Any],
    tokens: Mapping[str, int],
) -> None:
    """Recompute every derived field from the raw logits and demand equality."""

    if set(row) != BEHAVIORAL_ROW_KEYS:
        unexpected = sorted(set(row) - BEHAVIORAL_ROW_KEYS)
        missing = sorted(BEHAVIORAL_ROW_KEYS - set(row))
        raise StageBDError(
            f"behavioral row field set drift: unexpected={unexpected} missing={missing}"
        )
    if row["run_id"] != RUN_ID:
        raise StageBDError("behavioral row carries an unregistered run identity")
    if row["execution_status"] != "complete" or row["finite"] is not True:
        raise StageBDError(f"incomplete behavioral row: {row['item_id']}/{row['arm']}")
    for field in ("item_id", "semantic_id", "family", "template_id", "correct_label"):
        if row[field] != item[field]:
            raise StageBDError(f"behavioral row {field} disagrees with the frozen bank")
    if row["depth"] != item["depth"]:
        raise StageBDError("behavioral row depth disagrees with the frozen bank")
    if row["model_id"] != identity["model_id"]:
        raise StageBDError("behavioral row model_id is not the pinned checkpoint")
    if row["model_revision"] != identity["resolved_revision"]:
        raise StageBDError("behavioral row revision is not the pinned immutable revision")
    for field in ("prompt_sha256", "input_ids_sha256", "input_length", "answer_position"):
        if row[field] != prompt_identity[field]:
            raise StageBDError(
                f"behavioral row {field} differs from the sealed Stage T identity"
            )
    if row["option_token_ids"] != [int(tokens[label]) for label in s2.LABELS]:
        raise StageBDError("behavioral row option token IDs are not the sealed IDs")
    if row["input_length"] != row["answer_position"] + 1:
        raise StageBDError("answer position is not the final input position")

    logits = {label: float(row["option_logits"][index]) for index, label in enumerate(s2.LABELS)}
    if any(not math.isfinite(value) for value in logits.values()):
        raise StageBDError("behavioral row logits are not finite")
    probabilities = s2.restricted_probabilities(logits)
    expected = [probabilities[label] for label in s2.LABELS]
    if row["restricted_probabilities"] != expected:
        raise StageBDError("restricted probabilities are not the registered softmax")
    if row["restricted_prediction"] != s2.restricted_prediction(logits):
        raise StageBDError("restricted prediction is not the registered argmax")
    if row["correct"] is not (row["restricted_prediction"] == item["correct_label"]):
        raise StageBDError("correctness disagrees with the restricted prediction")
    if row["correct_margin"] != s2.correct_margin(logits, item["correct_label"]):
        raise StageBDError("correct margin is not the registered margin")
    ranks = row["full_vocab_option_ranks"]
    if len(ranks) != 4 or any(value < 1 for value in ranks):
        raise StageBDError("full-vocabulary option ranks are malformed")
    if row["full_vocab_top1_token_id"] < 0:
        raise StageBDError("full-vocabulary top-1 token id is malformed")


def merge_shard_rows(
    shard_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Complete merge only: no duplicate, missing, or out-of-shard contribution."""

    expected_by_shard = {shard["shard_id"]: shard for shard in manifest["shards"]}
    if set(shard_rows) != set(expected_by_shard):
        missing = sorted(set(expected_by_shard) - set(shard_rows))
        extra = sorted(set(shard_rows) - set(expected_by_shard))
        raise StageBDError(f"shard set drift: missing={missing} unexpected={extra}")

    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for shard, rows in sorted(shard_rows.items()):
        declared = expected_by_shard[shard]
        if len(rows) != declared["row_count"]:
            raise StageBDError(
                f"shard {shard} contributed {len(rows)} rows, expected {declared['row_count']}"
            )
        for row in rows:
            if (
                row["model_role"] != declared["model_role"]
                or row["family"] != declared["family"]
                or row["depth"] != declared["depth"]
            ):
                raise StageBDError(f"out-of-shard row in {shard}: {row['item_id']}")
            key = (row["model_role"], row["item_id"], row["arm"])
            if key in merged:
                raise StageBDError(f"duplicate behavioral row: {key}")
            merged[key] = dict(row)
    if len(merged) != TOTAL_ROWS:
        raise StageBDError(f"merged pack has {len(merged)} rows, expected {TOTAL_ROWS}")
    return [merged[key] for key in sorted(merged)]


def _cell_rows(
    rows: Sequence[Mapping[str, Any]], **selectors: Any
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in rows
        if all(row[field] == value for field, value in selectors.items())
    ]


def final_position(input_length: int, padded_length: int, *, left_padded: bool) -> int:
    """Index of the registered final input position inside a padded sequence.

    Stage T sealed ``answer_position_index == input_length - 1``.  With left
    padding the final real token is always the last column; with right padding
    it is ``input_length - 1``.  Padding is execution plumbing and must never
    move the observable, so both routes are computed here and the caller is
    required to agree with the single-sequence answer.
    """

    if input_length < 1 or padded_length < input_length:
        raise StageBDError(
            f"input length {input_length} does not fit padded length {padded_length}"
        )
    return padded_length - 1 if left_padded else input_length - 1


def attention_mask(input_length: int, padded_length: int, *, left_padded: bool) -> list[int]:
    """The only attention mask Stage B-D may build for a padded sequence."""

    pad = padded_length - input_length
    if pad < 0:
        raise StageBDError("padded length is shorter than the input length")
    real = [1] * input_length
    return [0] * pad + real if left_padded else real + [0] * pad


def position_ids(mask: Sequence[int]) -> list[int]:
    """Cumulative-sum position ids so left padding cannot shift a position."""

    running = 0
    out: list[int] = []
    for value in mask:
        if value not in (0, 1):
            raise StageBDError("attention mask must be binary")
        running += int(value)
        out.append(max(running - 1, 0))
    return out


def read_option_logits(
    row_logits: Sequence[Sequence[float]],
    *,
    input_length: int,
    tokens: Mapping[str, int],
    left_padded: bool,
) -> tuple[dict[str, float], list[int], int]:
    """Exactly one final-input-position logit vector per logical row.

    Returns the four option logits, the four full-vocabulary option ranks and
    the full-vocabulary top-1 token id.  No other position is ever read, and no
    hidden state is returned, so this function cannot express an activation,
    probe, lens, patching or ablation observable.
    """

    padded_length = len(row_logits)
    index = final_position(input_length, padded_length, left_padded=left_padded)
    vector = list(row_logits[index])
    ranks, top1 = full_vocab_ranks(vector, tokens)
    logits = {label: float(vector[tokens[label]]) for label in s2.LABELS}
    if any(not math.isfinite(value) for value in logits.values()):
        raise StageBDError("option logits contain a non-finite value")
    return logits, ranks, top1


def _rank_of(row: Mapping[str, Any], label: str) -> int:
    return int(row["full_vocab_option_ranks"][s2.LABELS.index(label)])


def _probability_of(row: Mapping[str, Any], label: str) -> float:
    return float(row["restricted_probabilities"][s2.LABELS.index(label)])


def summarize(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Every registered per-cell development summary, in one fixed order."""

    grouped: dict[tuple[str, str, int, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (row["model_role"], row["family"], row["depth"], row["template_id"], row["arm"])
        ].append(row)

    summaries: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda value: (MODEL_ROLES.index(value[0]), *value[1:])):
        role, family, depth, template, arm = key
        cell = grouped[key]
        n = len(cell)
        correct = sum(1 for row in cell if row["correct"])
        lower, upper = s2.wilson_interval(correct, n)
        confusion = {
            label: {inner: 0 for inner in s2.LABELS} for label in s2.LABELS
        }
        for row in cell:
            confusion[row["correct_label"]][row["restricted_prediction"]] += 1
        lengths = sorted(int(row["input_length"]) for row in cell)
        correct_ranks = [_rank_of(row, row["correct_label"]) for row in cell]
        summaries.append(
            {
                "arm": arm,
                "correct": correct,
                "correct_label_confusion": confusion,
                "depth": depth,
                "execution_complete": sum(
                    1 for row in cell if row["execution_status"] == "complete"
                ),
                "family": family,
                "finite_rows": sum(1 for row in cell if row["finite"]),
                "full_vocab_correct_rank_max": max(correct_ranks),
                "full_vocab_correct_rank_mean": math.fsum(correct_ranks) / n,
                "full_vocab_correct_rank_min": min(correct_ranks),
                "input_length_max": lengths[-1],
                "input_length_min": lengths[0],
                "mean_correct_margin": math.fsum(
                    float(row["correct_margin"]) for row in cell
                )
                / n,
                "mean_correct_restricted_probability": math.fsum(
                    _probability_of(row, row["correct_label"]) for row in cell
                )
                / n,
                "model_role": role,
                "n": n,
                "restricted_accuracy": correct / n,
                "schema_version": SUMMARY_ROW_VERSION,
                "template_id": template,
                "wilson_lower_95": lower,
                "wilson_upper_95": upper,
            }
        )
    return summaries


def _paired_interval(
    left: Sequence[float], right: Sequence[float], *, domain: str
) -> dict[str, Any]:
    replicates = s2.paired_bootstrap_mean_differences(
        list(left), list(right), seed=s2.SEEDS["bootstrap"], domain=domain,
        replicates=BOOTSTRAP_REPLICATES,
    )
    observed = math.fsum(
        left_value - right_value for left_value, right_value in zip(left, right)
    ) / len(left)
    return {
        "bootstrap_lower_95": s2.finite_quantile(replicates, BOOTSTRAP_LOWER),
        "bootstrap_upper_95": s2.finite_quantile(replicates, BOOTSTRAP_UPPER),
        "domain": domain,
        "n_units": len(left),
        "observed": observed,
        "replicates": BOOTSTRAP_REPLICATES,
        "schema_version": BOOTSTRAP_ROW_VERSION,
    }


def bootstrap_diagnostics(
    rows: Sequence[Mapping[str, Any]], items: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """The registered 10,000-replicate paired development diagnostics.

    These are development diagnostics.  They cannot change any task, depth,
    template, arm, threshold, option, sample size, control, confirmation rule,
    mechanistic selection or claim.
    """

    by_key = {
        (row["model_role"], row["item_id"], row["arm"]): row for row in rows
    }
    diagnostics: list[dict[str, Any]] = []
    for role in MODEL_ROLES:
        for family in s2.FAMILIES:
            for depth in s2.DEPTHS:
                unit_ids = sorted(
                    item["item_id"]
                    for item in items.values()
                    if item["family"] == family and item["depth"] == depth
                )
                unit_ids.sort(key=lambda item_id: items[item_id]["semantic_id"])
                nt = [by_key[(role, item_id, "NT")] for item_id in unit_ids]
                base = f"study2/bd/{role}/{family}/d{depth}"

                diagnostics.append(
                    {
                        "depth": depth,
                        "family": family,
                        "model_role": role,
                        "statistic": "NT_MEAN_CORRECT_MARGIN",
                        **_paired_interval(
                            [float(row["correct_margin"]) for row in nt],
                            [0.0] * len(nt),
                            domain=f"{base}/nt-mean-correct-margin",
                        ),
                    }
                )
                if depth in ARM_DEPTHS["PT"]:
                    pt = [by_key[(role, item_id, "PT")] for item_id in unit_ids]
                    wt = [by_key[(role, item_id, "WT")] for item_id in unit_ids]
                    diagnostics.append(
                        {
                            "depth": depth,
                            "family": family,
                            "model_role": role,
                            "statistic": "TRACE_GAIN",
                            **_paired_interval(
                                [
                                    _probability_of(row, items[row["item_id"]]["correct_label"])
                                    for row in pt
                                ],
                                [
                                    _probability_of(row, items[row["item_id"]]["correct_label"])
                                    for row in nt
                                ],
                                domain=f"{base}/trace-gain",
                            ),
                        }
                    )
                    diagnostics.append(
                        {
                            "depth": depth,
                            "family": family,
                            "model_role": role,
                            "statistic": "WRONG_TRACE_PULL",
                            **_paired_interval(
                                [
                                    _probability_of(
                                        row,
                                        items[row["item_id"]]["counterfactual"]["implied_label"],
                                    )
                                    for row in wt
                                ],
                                [
                                    _probability_of(
                                        row,
                                        items[row["item_id"]]["counterfactual"]["implied_label"],
                                    )
                                    for row in nt
                                ],
                                domain=f"{base}/wrong-trace-pull",
                            ),
                        }
                    )
                if depth in ARM_DEPTHS["ST"]:
                    pt = [by_key[(role, item_id, "PT")] for item_id in unit_ids]
                    stt = [by_key[(role, item_id, "ST")] for item_id in unit_ids]
                    diagnostics.append(
                        {
                            "depth": depth,
                            "family": family,
                            "model_role": role,
                            "statistic": "SHUFFLE_DAMAGE",
                            **_paired_interval(
                                [
                                    _probability_of(row, items[row["item_id"]]["correct_label"])
                                    for row in pt
                                ],
                                [
                                    _probability_of(row, items[row["item_id"]]["correct_label"])
                                    for row in stt
                                ],
                                domain=f"{base}/shuffle-damage",
                            ),
                        }
                    )
    return diagnostics


def _balance_entries(report: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Flatten the registered balance report into closed, dynamic-key-free rows."""

    counts = [
        {"count": int(count), "field": field, "value": str(value)}
        for field, table in report["counts"].items()
        for value, count in table.items()
    ]
    conditional = [
        {"count": int(count), "field": field, "label": label, "value": str(value)}
        for field, table in report["conditional_label_tables"].items()
        for value, labels in table.items()
        for label, count in labels.items()
    ]
    counts.sort(key=lambda entry: (entry["field"], entry["value"]))
    conditional.sort(
        key=lambda entry: (entry["field"], entry["value"], entry["label"])
    )
    return {"conditional": conditional, "counts": counts}


def gate_balance(items: Sequence[Mapping[str, Any]], family: str) -> dict[str, Any]:
    """Every registered balance invariant on the exact Gate A row population.

    The registered balance invariant is defined on a family x depth cell of 64
    items, so it is applied here at exactly that granularity for both pooled
    depths.  The pooled 128-item population is checked only for the structural
    facts the protocol registers for it (population size, per-depth size, one
    row per distinct semantic item).  No balance rule is invented, relaxed or
    transplanted onto a population the protocol never registered it for.
    """

    tables: dict[str, Any] = {}
    pooled: list[Mapping[str, Any]] = []
    for depth in GATE_DEPTHS:
        cell = [item for item in items if item["family"] == family and item["depth"] == depth]
        if len(cell) != GATE_ROWS_PER_DEPTH:
            raise StageBDError(
                f"{family} depth {depth} has {len(cell)} items, expected {GATE_ROWS_PER_DEPTH}"
            )
        tables[f"d{depth}"] = _balance_entries(s2._validate_cell_balance(cell, pair_rows=False))
        pooled.extend(cell)
    if len(pooled) != GATE_N_PER_FAMILY:
        raise StageBDError(
            f"{family} Gate A population is {len(pooled)}, expected {GATE_N_PER_FAMILY}"
        )
    semantic_ids = {item["semantic_id"] for item in pooled}
    item_ids = {item["item_id"] for item in pooled}
    if len(semantic_ids) != GATE_N_PER_FAMILY or len(item_ids) != GATE_N_PER_FAMILY:
        raise StageBDError(f"{family} Gate A population repeats an item or semantic id")
    tables["pooled_structure"] = {
        "distinct_item_ids": len(item_ids),
        "distinct_semantic_ids": len(semantic_ids),
        "n": len(pooled),
        "rows_per_depth": {f"d{depth}": GATE_ROWS_PER_DEPTH for depth in GATE_DEPTHS},
    }
    return tables


def gate_inputs_digest(gate_rows: Sequence[Mapping[str, Any]]) -> str:
    payload = [
        {
            "arm": row["arm"],
            "correct": row["correct"],
            "correct_label": row["correct_label"],
            "depth": row["depth"],
            "family": row["family"],
            "input_ids_sha256": row["input_ids_sha256"],
            "item_id": row["item_id"],
            "model_revision": row["model_revision"],
            "model_role": row["model_role"],
            "prompt_sha256": row["prompt_sha256"],
            "restricted_prediction": row["restricted_prediction"],
            "run_id": row["run_id"],
            "semantic_id": row["semantic_id"],
        }
        for row in gate_rows
    ]
    payload.sort(
        key=lambda row: (row["model_role"], row["family"], row["depth"], row["item_id"])
    )
    return sha256_bytes(canonical_json_bytes(payload))


def gate_a(
    rows: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    *,
    confirmation_opened_before_decision: bool = False,
) -> dict[str, Any]:
    """The exact registered Gate A decision.

    Controls are executed and reported in full and have zero authority: the
    overall decision is derived from the two target-family decisions only.  There
    is no pooling, depth fallback, subgroup, multiplicity rescue, control rescue
    or prior-result rescue anywhere in this function.
    """

    if confirmation_opened_before_decision:
        raise StageBDError("Gate A ran after a behavioral-confirmation object was opened")

    by_item = {item["item_id"]: item for item in items}
    feasibility: list[dict[str, Any]] = []
    balances = {family: gate_balance(items, family) for family in s2.FAMILIES}
    target_pass: dict[str, bool] = {}
    all_gate_rows: list[Mapping[str, Any]] = []

    for role in MODEL_ROLES:
        for family in s2.FAMILIES:
            selected = [
                row
                for row in rows
                if row["model_role"] == role
                and row["family"] == family
                and row["arm"] == GATE_DECISION_ARM
                and row["depth"] in GATE_DEPTHS
            ]
            selected.sort(key=lambda row: (row["depth"], row["item_id"]))
            per_depth = Counter(row["depth"] for row in selected)
            depth_ok = all(
                per_depth.get(depth, 0) == GATE_ROWS_PER_DEPTH for depth in GATE_DEPTHS
            )
            n = len(selected)
            if n != GATE_N_PER_FAMILY or not depth_ok:
                raise StageBDError(
                    f"Gate A population for {role}/{family} is {n} "
                    f"({dict(per_depth)}), expected {GATE_N_PER_FAMILY} as 64+64"
                )
            finite_complete = all(
                row["finite"] is True
                and row["execution_status"] == "complete"
                and row["correct_label"] == by_item[row["item_id"]]["correct_label"]
                for row in selected
            )
            balance_ok = bool(balances[family])
            correct = sum(1 for row in selected if row["correct"])
            tail = s2.binomial_upper_tail(n, GATE_NULL_ACCURACY, correct)
            family_pass = bool(
                finite_complete
                and balance_ok
                and correct >= GATE_CRITICAL_SUCCESSES
            )
            if role == GATE_DECISION_MODEL:
                target_pass[family] = family_pass
                all_gate_rows.extend(selected)
            feasibility.append(
                {
                    "alpha": GATE_ALPHA,
                    "balance_ok": balance_ok,
                    "confirmation_opened_before_decision": False,
                    "critical_successes": GATE_CRITICAL_SUCCESSES,
                    "exact_binomial_upper_tail": tail,
                    "family": family,
                    "family_gate_pass": family_pass,
                    "finite_complete": finite_complete,
                    "gate_inputs_sha256": gate_inputs_digest(selected),
                    "model_role": role,
                    "n_nt_compositional": n,
                    "nt_correct": correct,
                    "overall_gate_pass": False,
                    "protocol_version": PROTOCOL_VERSION,
                    "run_id": RUN_ID,
                }
            )

    overall = s2.feasibility_gate_pass(
        permutation_correct=next(
            row["nt_correct"]
            for row in feasibility
            if row["model_role"] == GATE_DECISION_MODEL and row["family"] == "permutation_chain"
        ),
        affine_correct=next(
            row["nt_correct"]
            for row in feasibility
            if row["model_role"] == GATE_DECISION_MODEL and row["family"] == "affine_mod10"
        ),
        n_per_family=GATE_N_PER_FAMILY,
        execution_complete=all(
            row["finite_complete"]
            for row in feasibility
            if row["model_role"] == GATE_DECISION_MODEL
        ),
        balance_ok=all(
            row["balance_ok"]
            for row in feasibility
            if row["model_role"] == GATE_DECISION_MODEL
        ),
        confirmation_unopened=True,
    )
    if overall != all(target_pass.get(family, False) for family in s2.FAMILIES):
        raise StageBDError("Gate A overall decision disagrees with the family decisions")
    for row in feasibility:
        row["overall_gate_pass"] = overall

    return {
        "balance_tables": balances,
        "feasibility_rows": feasibility,
        "gate_inputs_sha256": gate_inputs_digest(all_gate_rows),
        "overall_gate_pass": overall,
        "terminal_state": GATE_A_PASS_STATE if overall else GATE_A_FAIL_STATE,
    }


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = b"".join(canonical_json_bytes(row) for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"bytes": len(payload), "rows": len(rows), "sha256": sha256_bytes(payload)}


def write_json(path: Path, document: Mapping[str, Any]) -> dict[str, Any]:
    payload = canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"bytes": len(payload), "rows": None, "sha256": sha256_bytes(payload)}


OUTPUT_DIR = "studies/study2/stage_bd"
CORE_MANIFEST_NAME = "stage_bd_core_manifest.json"
SHARD_MANIFEST_NAME = "stage_bd_shard_manifest.json"
SEAL_NAME = "stage_bd_preinference_seal.json"
BEHAVIORAL_FILES = {
    role: f"stage_bd_behavioral_development_{role}.jsonl" for role in MODEL_ROLES
}
PACK_FILES: tuple[str, ...] = (
    "stage_bd_behavioral_development_instruction_control.jsonl",
    "stage_bd_behavioral_development_lineage_base.jsonl",
    "stage_bd_behavioral_development_target.jsonl",
    "stage_bd_bootstrap_diagnostics.jsonl",
    "stage_bd_confirmation_unopened_receipt.json",
    "stage_bd_development_summaries.jsonl",
    "stage_bd_feasibility_gate.jsonl",
    "stage_bd_gate_a_decision.json",
    "stage_bd_shard_manifest.json",
    "stage_bd_weight_identity_receipt.json",
)
SHARD_RECEIPT_PREFIX = "stage_bd_shard_receipt_"
ATTEMPT_RECEIPT_PREFIX = "stage_bd_attempt_receipt_"


def _file_entries(mapping: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """A dynamic-key map of path -> {bytes, sha256} as closed, sorted rows."""

    return [
        {
            "bytes": int(entry["bytes"]),
            "path": name,
            "rows": None if entry.get("rows") is None else int(entry["rows"]),
            "sha256": entry["sha256"],
        }
        for name, entry in sorted(mapping.items())
    ]


def weight_identity_receipt(snapshots: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Complete weight/config/tokenizer manifests for the three loaded roles."""

    models: list[dict[str, Any]] = []
    for role, model_id, revision in s2.MODEL_IDENTITIES:
        snapshot = snapshots[role]
        if snapshot["model_id"] != model_id:
            raise StageBDError(f"{role} snapshot is {snapshot['model_id']}, not {model_id}")
        if snapshot["resolved_revision"] != revision or snapshot["requested_revision"] != revision:
            raise StageBDError(f"{role} snapshot revision is not the pinned revision")
        names = [entry["name"] for entry in snapshot["files"]]
        if len(set(names)) != len(names):
            raise StageBDError(f"{role} snapshot lists a duplicate file")
        weights = sorted(
            name for name in names if name.endswith(WEIGHT_FILE_SUFFIXES)
        )
        if not weights:
            raise StageBDError(f"{role} snapshot carries no weight file")
        configs = sorted(name for name in names if name in CONFIG_FILE_ALLOWLIST)
        models.append(
            {
                "config_files": configs,
                "dtype_inventory": [
                    {"count": int(count), "dtype": dtype}
                    for dtype, count in sorted(snapshot["dtype_inventory"].items())
                ],
                "files": sorted(
                    (
                        {
                            "bytes": int(entry["bytes"]),
                            "name": entry["name"],
                            "sha256": entry["sha256"],
                        }
                        for entry in snapshot["files"]
                    ),
                    key=lambda entry: entry["name"],
                ),
                "model_class": snapshot["model_class"],
                "model_id": model_id,
                "parameter_count": int(snapshot["parameter_count"]),
                "parameter_dtype": snapshot["parameter_dtype"],
                "requested_revision": revision,
                "resolved_revision": revision,
                "role": role,
                "tokenizer_class": snapshot["tokenizer_class"],
                "trust_remote_code": False,
                "use_cache": False,
                "weight_files": weights,
            }
        )
    return {
        "generated_tokens": GENERATED_TOKENS,
        "models": models,
        "run_id": RUN_ID,
        "schema_version": WEIGHT_IDENTITY_VERSION,
    }


def build_preinference_seal(
    *,
    frozen: Mapping[str, Mapping[str, Any]],
    shard_manifest: Mapping[str, Any],
    expected_keys: Sequence[tuple[str, str, str]],
    source: Mapping[str, Any],
    schema: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    tokens: Mapping[str, int],
) -> dict[str, Any]:
    """The pre-inference seal.  Written before the first real weight load."""

    payload = "\n".join("|".join(key) for key in expected_keys)
    return {
        "authority": {
            "bytes": AUTHORITY_BYTES,
            "path": AUTHORITY_PATH,
            "sha256": AUTHORITY_SHA256,
        },
        "confirmation_unopened": dict(confirmation),
        "expected_primary_keys_sha256": sha256_text(
            f"jspace-study2-stage-bd/expected-keys/v1\n{payload}\n"
        ),
        "expected_row_count": len(expected_keys),
        "frozen_inputs": _file_entries(frozen),
        "gate_a": {
            "alpha": GATE_ALPHA,
            "critical_successes": GATE_CRITICAL_SUCCESSES,
            "decision_arm": GATE_DECISION_ARM,
            "decision_model": GATE_DECISION_MODEL,
            "depths": list(GATE_DEPTHS),
            "n_per_family": GATE_N_PER_FAMILY,
            "null_accuracy": GATE_NULL_ACCURACY,
        },
        "model_identities": [
            {"model_id": model_id, "revision": revision, "role": role}
            for role, model_id, revision in s2.MODEL_IDENTITIES
        ],
        "option_token_ids": [
            {"label": label, "token_id": int(tokens[label])} for label in s2.LABELS
        ],
        "protocol_version": PROTOCOL_VERSION,
        "run_id": RUN_ID,
        "schema": dict(schema),
        "schema_version": SEAL_VERSION,
        "shard_manifest_sha256": shard_manifest["shard_manifest_sha256"],
        "source": dict(source),
        "starting_commit": STAGE_BD_START_COMMIT,
        "starting_tree": STAGE_BD_START_TREE,
    }


def write_pack(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    shard_manifest: Mapping[str, Any],
    weight_identity: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    gate: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    diagnostics: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Mapping[str, Any]],
    environment: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    """Write the closed Stage B-D pack with the core manifest written last."""

    if len(rows) != TOTAL_ROWS:
        raise StageBDError(f"pack carries {len(rows)} rows, expected {TOTAL_ROWS}")
    incomplete = [
        (row["model_role"], row["item_id"], row["arm"])
        for row in rows
        if row["execution_status"] != "complete" or row["finite"] is not True
    ]
    if incomplete:
        raise StageBDError(
            f"{len(incomplete)} row(s) are not complete and finite: {incomplete[:3]}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, Any]] = {}

    for role in MODEL_ROLES:
        subset = [row for row in rows if row["model_role"] == role]
        if len(subset) != ROWS_PER_MODEL:
            raise StageBDError(f"{role} contributed {len(subset)} rows")
        files[BEHAVIORAL_FILES[role]] = write_jsonl(
            output_dir / BEHAVIORAL_FILES[role], subset
        )
    files["stage_bd_development_summaries.jsonl"] = write_jsonl(
        output_dir / "stage_bd_development_summaries.jsonl", summaries
    )
    files["stage_bd_bootstrap_diagnostics.jsonl"] = write_jsonl(
        output_dir / "stage_bd_bootstrap_diagnostics.jsonl", diagnostics
    )
    files["stage_bd_feasibility_gate.jsonl"] = write_jsonl(
        output_dir / "stage_bd_feasibility_gate.jsonl", gate["feasibility_rows"]
    )
    files["stage_bd_gate_a_decision.json"] = write_json(
        output_dir / "stage_bd_gate_a_decision.json",
        {
            "balance_tables": gate["balance_tables"],
            "confirmation_opened_before_decision": False,
            "controls_are_descriptive_only": True,
            "gate_inputs_sha256": gate["gate_inputs_sha256"],
            "overall_gate_pass": gate["overall_gate_pass"],
            "run_id": RUN_ID,
            "schema_version": SCHEMA_VERSION,
            "target_family_decisions": {
                row["family"]: {
                    "exact_binomial_upper_tail": row["exact_binomial_upper_tail"],
                    "family_gate_pass": row["family_gate_pass"],
                    "n_nt_compositional": row["n_nt_compositional"],
                    "nt_correct": row["nt_correct"],
                }
                for row in gate["feasibility_rows"]
                if row["model_role"] == GATE_DECISION_MODEL
            },
            "terminal_state": gate["terminal_state"],
        },
    )
    files[SHARD_MANIFEST_NAME] = write_json(output_dir / SHARD_MANIFEST_NAME, shard_manifest)
    files["stage_bd_weight_identity_receipt.json"] = write_json(
        output_dir / "stage_bd_weight_identity_receipt.json", weight_identity
    )
    files["stage_bd_confirmation_unopened_receipt.json"] = write_json(
        output_dir / "stage_bd_confirmation_unopened_receipt.json", confirmation
    )

    if sorted(files) != sorted(PACK_FILES):
        raise StageBDError(
            f"pack file set drift: {sorted(files)} != {sorted(PACK_FILES)}"
        )

    manifest = build_core_manifest(
        files=files,
        rows=rows,
        items=items,
        shard_manifest=shard_manifest,
        weight_identity=weight_identity,
        confirmation=confirmation,
        gate=gate,
        summaries=summaries,
        diagnostics=diagnostics,
        frozen=frozen,
        environment=environment,
        execution=execution,
    )
    entry = write_json(output_dir / CORE_MANIFEST_NAME, manifest)
    return {"files": files, "manifest": manifest, "manifest_entry": entry}


def build_core_manifest(
    *,
    files: Mapping[str, Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    shard_manifest: Mapping[str, Any],
    weight_identity: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    gate: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    diagnostics: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Mapping[str, Any]],
    environment: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind everything Stage B-D depended on into one deterministic manifest."""

    payload = "\n".join(
        "|".join((row["model_role"], row["item_id"], row["arm"])) for row in rows
    )
    counts: list[dict[str, Any]] = []
    for field in ("model_role", "family", "depth", "template_id", "arm"):
        counter = Counter(str(row[field]) for row in rows)
        counts.extend(
            {"count": int(count), "field": field, "value": value}
            for value, count in sorted(counter.items())
        )
    cells = [
        {
            "arm": arm,
            "count": count,
            "depth": depth,
            "family": family,
            "model_role": role,
            "template_id": template,
        }
        for (role, family, depth, template, arm), count in sorted(
            Counter(
                (
                    row["model_role"],
                    row["family"],
                    int(row["depth"]),
                    row["template_id"],
                    row["arm"],
                )
                for row in rows
            ).items()
        )
    ]
    return {
        "authority": {
            "bytes": AUTHORITY_BYTES,
            "path": AUTHORITY_PATH,
            "sha256": AUTHORITY_SHA256,
        },
        "bootstrap": {
            "quantiles": [BOOTSTRAP_LOWER, BOOTSTRAP_UPPER],
            "replicates": BOOTSTRAP_REPLICATES,
            "rows": len(diagnostics),
            "seed": s2.SEEDS["bootstrap"],
        },
        "confirmation_unopened": dict(confirmation),
        "development_items": len(items),
        "environment": dict(environment),
        "execution": dict(execution),
        "expected_primary_keys_sha256": sha256_text(
            f"jspace-study2-stage-bd/expected-keys/v1\n{payload}\n"
        ),
        "files": _file_entries(files),
        "frozen_inputs": _file_entries(frozen),
        "gate_a": {
            "alpha": GATE_ALPHA,
            "controls_affect_decision": False,
            "critical_successes": GATE_CRITICAL_SUCCESSES,
            "decision_arm": GATE_DECISION_ARM,
            "decision_model": GATE_DECISION_MODEL,
            "depths": list(GATE_DEPTHS),
            "feasibility_rows": [dict(row) for row in gate["feasibility_rows"]],
            "gate_inputs_sha256": gate["gate_inputs_sha256"],
            "n_per_family": GATE_N_PER_FAMILY,
            "null_accuracy": GATE_NULL_ACCURACY,
            "overall_gate_pass": gate["overall_gate_pass"],
        },
        "observed_row_count": len(rows),
        "operation_counts": {
            "ablation_operations": 0,
            "activation_operations": 0,
            "behavioral_confirmation_forwards": 0,
            "behavioral_confirmation_tokenizations": 0,
            "forward_passes": len(rows),
            "generations": 0,
            "lens_applies": 0,
            "lens_fits": 0,
            "lens_loads": 0,
            "mechanistic_confirmation_operations": 0,
            "mechanistic_development_operations": 0,
            "model_downloads": len(MODEL_ROLES),
            "patching_operations": 0,
            "phase1_0d_operations": 0,
            "probe_fits": 0,
            "rq2_s4_runs": 0,
            "scientific_evidence_rows": 0,
            "semantic_review_provider_calls": 0,
            "tokenizer_constructions": len(MODEL_ROLES),
            "weight_loads": len(MODEL_ROLES),
        },
        "protocol_version": PROTOCOL_VERSION,
        "row_counts": counts,
        "row_cells": cells,
        "rows_per_model": ROWS_PER_MODEL,
        "run_id": RUN_ID,
        "schema_version": CORE_MANIFEST_VERSION,
        "shard_manifest_sha256": shard_manifest["shard_manifest_sha256"],
        "stage_p_freeze_commit": STAGE_P_FREEZE_COMMIT,
        "stage_p_handoff_commit": STAGE_P_HANDOFF_COMMIT,
        "starting_commit": STAGE_BD_START_COMMIT,
        "starting_tree": STAGE_BD_START_TREE,
        "summary_rows": len(summaries),
        "terminal_state": gate["terminal_state"],
        "total_rows": TOTAL_ROWS,
        "weight_identity": dict(weight_identity),
    }

