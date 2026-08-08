"""Study 2 Stage T: pinned config/tokenizer identity and token-alignment gate.

Stage T is mechanical qualification, not empirical evidence.  Nothing in this
module loads model weights, runs a forward pass, generates a token, reads an
activation, fits a probe, patches a residual stream, or touches a lens.  The
only model-derived objects it accepts are tokenizer handles supplied by the
caller, and it uses them exclusively through two closed operations: ``encode``
and ``decode``.

The module is deliberately free of infrastructure identity.  Run IDs, image
digests, timestamps, and cache paths never enter a deterministic core artifact;
the execution entry point writes those into a separate attempt receipt that the
final handoff binds by hash.

What a passing Stage T establishes, stated narrowly: that the frozen Stage P
prompt bytes tokenize under all three pinned tokenizers with a single-token,
prefix-preserving, byte-exact round-tripping option continuation, and that the
selected mechanistic pairs are exactly length- and position-aligned within each
tokenizer.  It establishes nothing about accuracy, reasoning, distillation, or
any J-space claim.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

import study2_protocol as s2

SCHEMA_VERSION = "jspace-study2-stage-t/v1"
IDENTITY_RECEIPT_VERSION = "jspace-study2-stage-t-identity/v1"
PROMPT_ROW_VERSION = "jspace-study2-stage-t-prompt-row/v1"
ELIGIBILITY_ROW_VERSION = "jspace-study2-stage-t-eligibility-row/v1"
JOINT_ROW_VERSION = "jspace-study2-stage-t-joint-row/v1"
ANNOTATION_ROW_VERSION = "jspace-study2-stage-t-annotation-row/v1"
DIGIT_SUPPORT_VERSION = "jspace-study2-stage-t-digit-support/v1"
CORE_MANIFEST_VERSION = "jspace-study2-stage-t-core-manifest/v1"
ATTEMPT_RECEIPT_VERSION = "jspace-study2-stage-t-attempt/v1"

# The additive Stage T operator authority, byte-identical to the operator text.
AUTHORITY_PATH = "studies/study2/prompts/stage_t_tokenizer_gate_prompt.md"
AUTHORITY_BYTES = 22_229
AUTHORITY_SHA256 = "dce8c7167682b57e9a6cd8c7dbe651cbdcbfda13255ad9d434d06b7e7949b974"

# The starting-state amendment record.  It corrects execution plumbing only:
# the local branch label stopped being an admission gate, commit/tree/protected
# byte identity stayed authoritative.  No frozen scientific byte moved.
AMENDMENT_PATH = "studies/study2/prompts/stage_t_starting_state_operator_amendments.md"

STARTING_STATE_DISPOSITION = (
    "STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE"
)
TERMINAL_STATE = (
    "NONTERMINAL_CHECKPOINT_STUDY2_STAGE_T_TOKENIZER_GATE_SEALED_AWAITING_BD_AUTHORITY"
)

STAGE_T_START_COMMIT = "c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1"
STAGE_T_START_TREE = "533fb62db4db096f4f6d09eeb858a391936a28c9"
STAGE_P_FREEZE_COMMIT = "d5e8e19c025410fda7c9eb430f507a201a18c9cd"
STAGE_P_FREEZE_TREE = "b044133055c697cad8828664254143f3b83f68d5"

# Every frozen input Stage T reads.  A drift here is a starting-state failure,
# never something to reconcile.
FROZEN_INPUTS: dict[str, tuple[int, str]] = {
    "studies/study2/STAGE_P_FINAL_HANDOFF.md": (
        16_380,
        "4801d1b52622ade4d6badd9e1b4c37bb3038e7060c39e40faf7c2512e2a8a2e9",
    ),
    "studies/study2/prompts/stage_p_protocol_design_prompt.md": (
        53_018,
        "1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37",
    ),
    "studies/study2/prompts/stage_p_gate_a_operator_amendment.md": (
        5_836,
        "e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.json": (
        39_357,
        "2f115e057249fb59e34ef34de2eb71ff042a449bb4ef1637ebec3181aedd7ad5",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.schema.json": (
        54_502,
        "d9f834282038f840707ea694bb5dd5422e87a3ca661eb987b2b9ce631d23b134",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol.md": (
        21_151,
        "4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054",
    ),
    "studies/study2/protocol/reasoning_internalization_protocol_review.md": (
        9_741,
        "e84607443798d4953a2b59ab7b47e82bd9bf89fe832a3d86de7ec5ab3fd7b139",
    ),
    "studies/study2/protocol/stage_p_power_sensitivity.json": (
        9_291,
        "f2514ffe9bc5cff80ef164f5b05a3cd90bbdfb9550af49b755accd3cbc3589ff",
    ),
    "studies/study2/decisions/reasoning_internalization_protocol_freeze.md": (
        5_025,
        "aa0151be87a43719ef8056b45d532281178ca5ea55480d46b0f7d484c7caff4d",
    ),
    "studies/study2/data/task_bank_manifest.json": (
        32_337,
        "7d07db2b508136229f06a727a3deb787106e2b389bb1207ab2c2d1099b21458f",
    ),
    "studies/study2/data/development.jsonl": (
        752_708,
        "7dd19884cc2cb4685863cc9df768347f7cfd52c348e5117ec574b52d3b0cf1d6",
    ),
    "studies/study2/data/behavioral_confirmation.jsonl": (
        3_068_780,
        "cbd20d061ee5bdc8f8484b79005ad7faa018add9ef028da16cd885f2c89ea3a9",
    ),
    "studies/study2/data/mechanistic_development_candidate_pairs.jsonl": (
        8_008_776,
        "397c752162e41ff1bc83ecf4cf58b768baa6400c9e6d20dc092f317238c1ef66",
    ),
    "studies/study2/data/mechanistic_candidate_pairs.jsonl": (
        8_102_984,
        "61dfaed3b8a56be4d27083bdca5307ea326ecfaeaa26f2d43dd3c8deafd77df6",
    ),
    "src/jspace_observation/study2_protocol.py": (
        72_263,
        "852073bd125aaf119ba7897666d49075c93a660ad7701d387e5bdbbfe71dbeaa",
    ),
    "src/jspace_observation/study2_task_bank.py": (
        29_847,
        "e0053afec6a1c6abb712f292605f038263f921e34414d545876bdafe11a22d7e",
    ),
}

MODEL_ROLES = ("target", "lineage_base", "instruction_control")
BEHAVIORAL_BANKS = ("development", "behavioral_confirmation")
MECHANISTIC_BANKS = ("mechanistic_development", "mechanistic_candidate_confirmation")
OPTION_LABELS = ("A", "B", "C", "D")
OPTION_SURFACES = (" A", " B", " C", " D")
PROMPT_TERMINATOR = "Answer:"

# Fixed inspection order for the seven objects a pair unit exposes.  ``no_op``
# is the recipient object itself, which is why it appears as a donor slot.
PAIR_OBJECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("primary_donor", ("primary", "donor")),
    ("primary_recipient", ("primary", "recipient")),
    ("control_no_op_donor", ("controls", "no_op_donor")),
    ("control_random_donor", ("controls", "random_donor")),
    ("control_same_answer_donor", ("controls", "same_answer_donor")),
    ("control_same_intermediate_donor", ("controls", "same_intermediate_donor")),
)
PAIR_OBJECT_KEYS = tuple(name for name, _ in PAIR_OBJECTS)
RECIPIENT_OBJECT = "primary_recipient"

SELECTED_PER_CELL = 128
SELECTED_PER_ROLE = 512
CELL_DEPTHS = (2, 3)

# Every acquisition allowlist entry AutoConfig/AutoTokenizer can legitimately
# need.  Anything outside this set is refused before it reaches a snapshot.
TOKENIZER_FILE_ALLOWLIST = (
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "merges.txt",
    "added_tokens.json",
    "chat_template.jinja",
)

# A staged snapshot containing any of these is a hard stop, not a warning.
WEIGHT_FILE_PATTERNS = (
    r".*\.safetensors$",
    r".*\.safetensors\.index\.json$",
    r"^pytorch_model.*\.bin$",
    r".*\.gguf$",
    r".*\.pt$",
    r".*\.pth$",
    r".*\.msgpack$",
    r".*\.h5$",
    r".*\.ot$",
    r"^model.*\.bin$",
    r".*\.bin\.index\.json$",
    r"^adapter_model\..*$",
)

OPTION_GATE_REASONS = (
    "OPTION_NOT_SINGLE_TOKEN",
    "PROMPT_PREFIX_NOT_PRESERVED",
    "OPTION_IDS_NOT_DISTINCT",
    "OPTION_ROUND_TRIP_DRIFT",
    "PROMPT_ROUND_TRIP_DRIFT",
    "PROMPT_HASH_MISMATCH",
    "PROMPT_TERMINATOR_MISSING",
    "UNREGISTERED_SPECIAL_TOKEN",
    "SPECIAL_SUFFIX_PRESENT",
    "EMPTY_ENCODING",
    "INPUT_TRUNCATED",
)
ELIGIBILITY_REASONS = (
    "OPTION_GATE_FAILED",
    "UNEQUAL_INPUT_LENGTH",
    "ANSWER_POSITION_MISALIGNED",
    "WRONG_POSITION_ANCHOR_SURFACE_MISMATCH",
    "WRONG_POSITION_ANCHOR_UNRESOLVED",
    "PROMPT_HASH_MISMATCH",
)
_ALL_REASONS = frozenset(OPTION_GATE_REASONS) | frozenset(ELIGIBILITY_REASONS)

# Target-only secondary diagnostic surfaces for the future J-lens readout axis.
# Recording them can make that axis ineligible; it can never rescue, select,
# promote, or demote the lens-independent Stage T result.
DIGIT_VALUES = tuple(str(value) for value in range(10))
DIGIT_SURFACE_FORMS = ("bare", "space_prefixed")


class StageTError(RuntimeError):
    """Raised when Stage T cannot proceed under its own fail-closed rules."""


class TokenizerLike(Protocol):
    """The closed surface Stage T is allowed to use on a tokenizer."""

    def encode(self, text: str, add_special_tokens: bool = ...) -> list[int]: ...

    def decode(
        self,
        token_ids: Sequence[int],
        skip_special_tokens: bool = ...,
        clean_up_tokenization_spaces: bool = ...,
    ) -> str: ...


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical form for every Stage T artifact: sorted, compact, LF, no NaN."""

    return s2.canonical_json_bytes(value)


def ids_sha256(token_ids: Sequence[int]) -> str:
    """Closed row-level representation of a full input token-ID sequence."""

    payload = ",".join(str(int(value)) for value in token_ids)
    return sha256_text(f"jspace-study2-stage-t/input-ids/v1\n{payload}\n")


def verify_frozen_inputs(root: Path) -> dict[str, dict[str, Any]]:
    """Rehash every frozen Stage T input; any drift is a starting-state stop."""

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
                f"frozen input drift: {relative} "
                f"bytes={len(raw)} expected={expected_bytes} "
                f"sha256={digest} expected={expected_sha}"
            )
            continue
        verified[relative] = {"bytes": len(raw), "sha256": digest}
    if failures:
        raise StageTError("; ".join(failures))
    return verified


def _read_bank_lines(path: Path) -> list[tuple[bytes, dict[str, Any]]]:
    """Return each frozen row with its exact source bytes preserved."""

    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if not raw.endswith(b"\n"):
        raise StageTError(f"bank does not end with a newline: {path.name}")
    rows: list[tuple[bytes, dict[str, Any]]] = []
    for line in raw.split(b"\n")[:-1]:
        document = json.loads(
            line.decode("utf-8"),
            object_pairs_hook=s2._pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
        if not isinstance(document, dict):
            raise StageTError(f"bank row is not an object: {path.name}")
        rows.append((line, document))
    return rows


def _reject_constant(literal: str) -> Any:
    raise StageTError(f"non-finite JSON literal in a frozen bank: {literal}")


def load_frozen_banks(root: Path) -> dict[str, list[tuple[bytes, dict[str, Any]]]]:
    data = root / "studies" / "study2" / "data"
    banks: dict[str, list[tuple[bytes, dict[str, Any]]]] = {}
    for role, filename in s2.BANK_FILES.items():
        banks[role] = _read_bank_lines(data / filename)
        expected = s2.EXPECTED_ROLE_COUNTS[role]
        if len(banks[role]) != expected:
            raise StageTError(
                f"bank {role} has {len(banks[role])} rows, expected {expected}"
            )
    return banks


def _pair_object(pair: Mapping[str, Any], path: Sequence[str]) -> Mapping[str, Any]:
    node: Any = pair
    for key in path:
        node = node[key]
    return node


def iter_prompt_rows(
    banks: Mapping[str, list[tuple[bytes, dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """Enumerate every prompt Stage T must cover, in one fixed order.

    Behavioral banks contribute every stored arm of every row.  Mechanistic
    banks contribute the NT prompt of the primary donor, the primary recipient,
    and all four registered donor controls.
    """

    rows: list[dict[str, Any]] = []
    for bank in BEHAVIORAL_BANKS:
        for line_index, (_, row) in enumerate(banks[bank]):
            for arm in sorted(row["prompts"]):
                rows.append(
                    {
                        "bank": bank,
                        "row_id": row["item_id"],
                        "arm": arm,
                        "prompt": row["prompts"][arm],
                        "prompt_sha256": row["prompt_hashes"][arm],
                        "source_line_index": line_index,
                    }
                )
    for bank in MECHANISTIC_BANKS:
        for line_index, (_, pair) in enumerate(banks[bank]):
            for name, path in PAIR_OBJECTS:
                task = _pair_object(pair, path)
                rows.append(
                    {
                        "bank": bank,
                        "row_id": pair["pair_id"],
                        "arm": name,
                        "prompt": task["nt_prompt"],
                        "prompt_sha256": task["prompt_sha256"],
                        "source_line_index": line_index,
                    }
                )
    return rows


def special_token_profile(tokenizer: TokenizerLike) -> dict[str, Any]:
    """Measure, never assume, what the tokenizer adds around a plain string.

    Stage T allows exactly one model-specific prompt-transport difference:
    tokenizer-required BOS behavior.  A trailing special token would move the
    answer position and is refused outright.
    """

    probe = "Answer:"
    bare = list(tokenizer.encode(probe, add_special_tokens=False))
    decorated = list(tokenizer.encode(probe, add_special_tokens=True))
    if not bare:
        raise StageTError("tokenizer produced an empty encoding for the probe string")

    prefix: list[int] = []
    suffix: list[int] = []
    if decorated != bare:
        head = 0
        while head < len(decorated) - len(bare) + 1 and decorated[head : head + len(bare)] != bare:
            head += 1
        if decorated[head : head + len(bare)] != bare:
            raise StageTError(
                "tokenizer special-token behavior does not wrap the plain encoding"
            )
        prefix = decorated[:head]
        suffix = decorated[head + len(bare) :]

    special_ids = sorted({int(value) for value in getattr(tokenizer, "all_special_ids", [])})
    return {
        "adds_bos": bool(prefix),
        "all_special_ids": special_ids,
        "prefix_token_ids": [int(value) for value in prefix],
        "prefix_decoded": tokenizer.decode(
            prefix, skip_special_tokens=False, clean_up_tokenization_spaces=False
        )
        if prefix
        else "",
        "suffix_token_ids": [int(value) for value in suffix],
        "tokenizer_class": type(tokenizer).__name__,
    }


def gate_prompt(
    tokenizer: TokenizerLike,
    profile: Mapping[str, Any],
    prompt: str,
    expected_prompt_sha256: str,
) -> dict[str, Any]:
    """Run the exact prompt and option-token gate for one prompt.

    Returns a closed row.  ``status`` is ``PASS`` only when the prompt bytes
    match their frozen hash, the canonical encoding round-trips byte-exactly,
    every option surface adds exactly one token while preserving the complete
    prompt-token prefix, and the four option IDs are pairwise distinct.
    """

    reasons: list[str] = []
    if sha256_text(prompt) != expected_prompt_sha256:
        reasons.append("PROMPT_HASH_MISMATCH")
    if not prompt.endswith(PROMPT_TERMINATOR):
        reasons.append("PROMPT_TERMINATOR_MISSING")
    if profile["suffix_token_ids"]:
        reasons.append("SPECIAL_SUFFIX_PRESENT")
    if reasons:
        return _failed_prompt_row(reasons)

    prefix = list(profile["prefix_token_ids"])
    prefix_text = str(profile["prefix_decoded"])
    special_ids = set(int(value) for value in profile["all_special_ids"])

    base = [int(value) for value in tokenizer.encode(prompt, add_special_tokens=True)]
    if not base:
        return _failed_prompt_row(["EMPTY_ENCODING"])
    if base[: len(prefix)] != prefix:
        reasons.append("UNREGISTERED_SPECIAL_TOKEN")
    if special_ids.intersection(base[len(prefix) :]):
        reasons.append("UNREGISTERED_SPECIAL_TOKEN")
    decoded = tokenizer.decode(
        base, skip_special_tokens=False, clean_up_tokenization_spaces=False
    )
    if decoded != prefix_text + prompt:
        reasons.append("PROMPT_ROUND_TRIP_DRIFT")
    limit = getattr(tokenizer, "model_max_length", None)
    if isinstance(limit, int) and 0 < limit < 10**6 and len(base) > limit:
        reasons.append("INPUT_TRUNCATED")
    if reasons:
        return _failed_prompt_row(sorted(set(reasons)))

    option_ids: dict[str, int] = {}
    for label, surface in zip(OPTION_LABELS, OPTION_SURFACES):
        full = [
            int(value)
            for value in tokenizer.encode(prompt + surface, add_special_tokens=True)
        ]
        if len(full) != len(base) + 1:
            reasons.append("OPTION_NOT_SINGLE_TOKEN")
            continue
        if full[: len(base)] != base:
            reasons.append("PROMPT_PREFIX_NOT_PRESERVED")
            continue
        if int(full[-1]) in special_ids:
            reasons.append("UNREGISTERED_SPECIAL_TOKEN")
            continue
        round_trip = tokenizer.decode(
            full, skip_special_tokens=False, clean_up_tokenization_spaces=False
        )
        if round_trip != prefix_text + prompt + surface:
            reasons.append("OPTION_ROUND_TRIP_DRIFT")
            continue
        option_ids[label] = int(full[-1])

    if len(option_ids) == len(OPTION_LABELS) and len(set(option_ids.values())) != len(
        OPTION_LABELS
    ):
        reasons.append("OPTION_IDS_NOT_DISTINCT")
    if reasons:
        return _failed_prompt_row(sorted(set(reasons)))

    return {
        "answer_position_index": len(base) - 1,
        "failure_reasons": [],
        "input_ids_sha256": ids_sha256(base),
        "input_length": len(base),
        "option_token_ids": dict(sorted(option_ids.items())),
        "status": "PASS",
        "token_ids": base,
    }


def _failed_prompt_row(reasons: Sequence[str]) -> dict[str, Any]:
    unknown = sorted(set(reasons) - _ALL_REASONS)
    if unknown:
        raise StageTError(f"unregistered failure reason: {unknown}")
    return {
        "answer_position_index": None,
        "failure_reasons": sorted(set(reasons)),
        "input_ids_sha256": None,
        "input_length": None,
        "option_token_ids": None,
        "status": "FAIL",
        "token_ids": None,
    }


def resolve_anchor_token_index(
    tokenizer: TokenizerLike,
    profile: Mapping[str, Any],
    prompt: str,
    anchor: Mapping[str, Any],
) -> int | None:
    """Resolve a frozen UTF-8 byte span to exactly one token index, or fail.

    The span must land on both an opening and a closing token boundary and must
    cover exactly one token.  A span that merges into a neighbouring token, or
    whose prefix retokenizes, resolves to ``None`` and makes the pair
    ineligible.  No fallback and no nearest-match are permitted.
    """

    raw = prompt.encode("utf-8")
    byte_start = int(anchor["byte_start"])
    byte_end = int(anchor["byte_end"])
    if not 0 <= byte_start < byte_end <= len(raw):
        return None
    try:
        head = raw[:byte_start].decode("utf-8")
        span = raw[byte_start:byte_end].decode("utf-8")
        through = raw[:byte_end].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if span != str(anchor["surface"]):
        return None

    base = [int(value) for value in tokenizer.encode(prompt, add_special_tokens=True)]
    before = [int(value) for value in tokenizer.encode(head, add_special_tokens=True)]
    upto = [int(value) for value in tokenizer.encode(through, add_special_tokens=True)]
    if len(upto) != len(before) + 1:
        return None
    if base[: len(before)] != before or base[: len(upto)] != upto:
        return None
    return len(before)


def evaluate_pair(
    pair: Mapping[str, Any],
    gate_rows: Mapping[str, Mapping[str, Any]],
    wrong_position_index: int | None,
    anchor_surface_ok: bool,
) -> dict[str, Any]:
    """Decide one pair's eligibility under one tokenizer."""

    reasons: list[str] = []
    lengths: dict[str, int | None] = {}
    positions: dict[str, int | None] = {}
    for name in PAIR_OBJECT_KEYS:
        row = gate_rows[name]
        lengths[name] = row["input_length"]
        positions[name] = row["answer_position_index"]
        if row["status"] != "PASS":
            if "PROMPT_HASH_MISMATCH" in row["failure_reasons"]:
                reasons.append("PROMPT_HASH_MISMATCH")
            reasons.append("OPTION_GATE_FAILED")

    distinct_lengths = {value for value in lengths.values() if value is not None}
    distinct_positions = {value for value in positions.values() if value is not None}
    if not reasons:
        if len(distinct_lengths) != 1:
            reasons.append("UNEQUAL_INPUT_LENGTH")
        if len(distinct_positions) != 1:
            reasons.append("ANSWER_POSITION_MISALIGNED")
        if not anchor_surface_ok:
            reasons.append("WRONG_POSITION_ANCHOR_SURFACE_MISMATCH")
        elif wrong_position_index is None:
            reasons.append("WRONG_POSITION_ANCHOR_UNRESOLVED")

    reasons = sorted(set(reasons))
    unknown = sorted(set(reasons) - _ALL_REASONS)
    if unknown:
        raise StageTError(f"unregistered eligibility reason: {unknown}")
    shared_position = (
        next(iter(distinct_positions)) if len(distinct_positions) == 1 else None
    )
    shared_length = next(iter(distinct_lengths)) if len(distinct_lengths) == 1 else None
    return {
        "answer_position_index": shared_position,
        "depth": int(pair["depth"]),
        "eligible": not reasons,
        "family": pair["family"],
        "input_length": shared_length,
        "object_answer_positions": dict(sorted(positions.items())),
        "object_input_lengths": dict(sorted(lengths.items())),
        "pair_id": pair["pair_id"],
        "pair_semantic_id": pair["pair_semantic_id"],
        "reason_codes": reasons,
        "role": pair["role"],
        "schema_version": ELIGIBILITY_ROW_VERSION,
        "template_id": pair["template_id"],
        "wrong_position_index": wrong_position_index,
    }


def evaluate_model(
    role: str,
    tokenizer: TokenizerLike,
    banks: Mapping[str, list[tuple[bytes, dict[str, Any]]]],
    prompt_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Run the complete Stage T gate for one pinned tokenizer."""

    if role not in MODEL_ROLES:
        raise StageTError(f"unregistered model role: {role}")
    profile = special_token_profile(tokenizer)

    cache: dict[str, dict[str, Any]] = {}
    prompt_pack: list[dict[str, Any]] = []
    failure_counts: dict[str, int] = {}
    option_ids_seen: dict[str, set[int]] = {label: set() for label in OPTION_LABELS}
    passed = 0

    for row in prompt_rows:
        prompt = row["prompt"]
        result = cache.get(prompt)
        if result is None:
            result = gate_prompt(tokenizer, profile, prompt, row["prompt_sha256"])
            cache[prompt] = result
        if result["status"] == "PASS":
            passed += 1
            for label, value in result["option_token_ids"].items():
                option_ids_seen[label].add(int(value))
        else:
            for reason in result["failure_reasons"]:
                failure_counts[reason] = failure_counts.get(reason, 0) + 1
        prompt_pack.append(
            {
                "answer_position_index": result["answer_position_index"],
                "arm": row["arm"],
                "bank": row["bank"],
                "failure_reasons": result["failure_reasons"],
                "input_ids_sha256": result["input_ids_sha256"],
                "input_length": result["input_length"],
                "model_role": role,
                "option_token_ids": result["option_token_ids"],
                "prompt_sha256": row["prompt_sha256"],
                "row_id": row["row_id"],
                "schema_version": PROMPT_ROW_VERSION,
                "status": result["status"],
            }
        )

    eligibility: list[dict[str, Any]] = []
    for bank in MECHANISTIC_BANKS:
        for _, pair in banks[bank]:
            gate_rows: dict[str, Mapping[str, Any]] = {}
            for name, path in PAIR_OBJECTS:
                task = _pair_object(pair, path)
                gate_rows[name] = cache[task["nt_prompt"]]
            recipient = _pair_object(pair, ("primary", "recipient"))
            anchor = pair["wrong_position_anchor"]
            recipient_anchor = recipient["start_anchor"]
            anchor_ok = dict(anchor) == dict(recipient_anchor)
            index = None
            if anchor_ok and gate_rows[RECIPIENT_OBJECT]["status"] == "PASS":
                index = resolve_anchor_token_index(
                    tokenizer, profile, recipient["nt_prompt"], anchor
                )
            eligibility.append(evaluate_pair(pair, gate_rows, index, anchor_ok))

    return {
        "eligibility": eligibility,
        "option_token_ids": {
            label: sorted(values) for label, values in sorted(option_ids_seen.items())
        },
        "profile": profile,
        "prompt_failure_counts": {
            code: failure_counts.get(code, 0) for code in sorted(OPTION_GATE_REASONS)
        },
        "prompt_pack": prompt_pack,
        "prompt_pass_count": passed,
        "prompt_row_count": len(prompt_pack),
        "role": role,
        "unique_prompt_count": len(cache),
    }


def stable_option_token_ids(model_result: Mapping[str, Any]) -> dict[str, int] | None:
    """Collapse per-prompt option IDs to one map, or ``None`` if they varied."""

    collapsed: dict[str, int] = {}
    for label, values in model_result["option_token_ids"].items():
        if len(values) != 1:
            return None
        collapsed[label] = int(values[0])
    if len(collapsed) != len(OPTION_LABELS):
        return None
    return dict(sorted(collapsed.items()))


def join_eligibility(
    banks: Mapping[str, list[tuple[bytes, dict[str, Any]]]],
    model_results: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Conjoin per-tokenizer eligibility across all three pinned tokenizers."""

    by_role: dict[str, dict[str, Mapping[str, Any]]] = {}
    for role in MODEL_ROLES:
        by_role[role] = {
            row["pair_id"]: row for row in model_results[role]["eligibility"]
        }

    joint: list[dict[str, Any]] = []
    for bank in MECHANISTIC_BANKS:
        for _, pair in banks[bank]:
            pair_id = pair["pair_id"]
            flags: dict[str, bool] = {}
            reasons: set[str] = set()
            for role in MODEL_ROLES:
                row = by_role[role][pair_id]
                flags[role] = bool(row["eligible"])
                reasons.update(row["reason_codes"])
            joint.append(
                {
                    "depth": int(pair["depth"]),
                    "eligible_all_models": all(flags.values()),
                    "family": pair["family"],
                    "model_eligibility": dict(sorted(flags.items())),
                    "pair_id": pair_id,
                    "pair_semantic_id": pair["pair_semantic_id"],
                    "reason_codes": sorted(reasons),
                    "role": pair["role"],
                    "schema_version": JOINT_ROW_VERSION,
                    "selected": False,
                    "selection_rank": None,
                }
            )
    return joint


def cell_key(role: str, family: str, depth: int) -> str:
    return f"{role}|{family}|d{depth}"


def expected_cells() -> tuple[str, ...]:
    return tuple(
        cell_key(role, family, depth)
        for role in MECHANISTIC_BANKS
        for family in s2.FAMILIES
        for depth in CELL_DEPTHS
    )


def select_pairs(joint_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic mechanics-only selection: sort, then take the first 128.

    No outcome field, no balance optimisation, no backfill, and no substitution
    for a favourable property is available here, because nothing but the frozen
    sort key and the joint eligibility boolean is in scope.
    """

    buckets: dict[str, list[dict[str, Any]]] = {key: [] for key in expected_cells()}
    for row in joint_rows:
        key = cell_key(row["role"], row["family"], int(row["depth"]))
        if key not in buckets:
            raise StageTError(f"pair fell outside the eight fixed cells: {key}")
        if row["eligible_all_models"]:
            buckets[key].append(row)

    cells: dict[str, dict[str, Any]] = {}
    shortfalls: list[str] = []
    for key in expected_cells():
        ordered = sorted(buckets[key], key=lambda item: item["pair_semantic_id"])
        chosen = ordered[:SELECTED_PER_CELL]
        for rank, row in enumerate(chosen):
            row["selected"] = True
            row["selection_rank"] = rank
        cells[key] = {
            "eligible": len(ordered),
            "selected": len(chosen),
            "selected_pair_ids": [row["pair_id"] for row in chosen],
            "selected_pair_semantic_ids": [row["pair_semantic_id"] for row in chosen],
        }
        if len(chosen) != SELECTED_PER_CELL:
            shortfalls.append(f"{key}: eligible={len(ordered)} < {SELECTED_PER_CELL}")

    return {
        "cells": dict(sorted(cells.items())),
        "shortfalls": shortfalls,
        "sufficient": not shortfalls,
    }


def digit_support(tokenizer: TokenizerLike, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Target-only secondary diagnostic; never selects, rescues, or blocks."""

    prefix = len(profile["prefix_token_ids"])
    surfaces: list[dict[str, Any]] = []
    for form in DIGIT_SURFACE_FORMS:
        for value in DIGIT_VALUES:
            surface = value if form == "bare" else f" {value}"
            ids = [
                int(item)
                for item in tokenizer.encode(surface, add_special_tokens=True)
            ][prefix:]
            surfaces.append(
                {
                    "form": form,
                    "single_token": len(ids) == 1,
                    "surface": surface,
                    "token_count": len(ids),
                    "token_ids": ids,
                    "value": value,
                }
            )
    single = [row for row in surfaces if row["single_token"]]
    bare = [row for row in single if row["form"] == "bare"]
    spaced = [row for row in single if row["form"] == "space_prefixed"]
    return {
        "bare_all_single_token": len(bare) == len(DIGIT_VALUES),
        "bare_ids_pairwise_distinct": len({row["token_ids"][0] for row in bare}) == len(bare),
        "role": "target_only_secondary_axis",
        "rescue_prohibited": True,
        "schema_version": DIGIT_SUPPORT_VERSION,
        "selection_prohibited": True,
        "single_token_surface_count": len(single),
        "space_prefixed_all_single_token": len(spaced) == len(DIGIT_VALUES),
        "space_prefixed_ids_pairwise_distinct": len({row["token_ids"][0] for row in spaced})
        == len(spaced),
        "surface_count": len(surfaces),
        "surfaces": surfaces,
    }


def classify_weight_files(names: Iterable[str]) -> list[str]:
    """Return every staged filename that looks like a model or adapter weight."""

    compiled = [re.compile(pattern) for pattern in WEIGHT_FILE_PATTERNS]
    hits = [
        name
        for name in sorted(names)
        if any(rule.match(Path(name).name) for rule in compiled)
    ]
    return hits


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_json_bytes(row) for row in rows)
    path.write_bytes(payload)
    return {"bytes": len(payload), "rows": len(rows), "sha256": sha256_bytes(payload)}


def write_json(path: Path, document: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(document)
    path.write_bytes(payload)
    return {"bytes": len(payload), "rows": None, "sha256": sha256_bytes(payload)}


def write_raw(path: Path, payload: bytes, rows: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"bytes": len(payload), "rows": rows, "sha256": sha256_bytes(payload)}


OUTPUT_DIR = "studies/study2/stage_t"
CORE_MANIFEST_NAME = "stage_t_core_manifest.json"

# Every file the core manifest must account for.  The manifest itself is not a
# member: a JSON document cannot contain its own hash, so the manifest is bound
# to the pack by being written last and by naming exactly this set.
PACK_FILES: tuple[str, ...] = (
    "stage_t_identity_receipt.json",
    "stage_t_jlens_digit_support.json",
    "stage_t_mechanistic_eligibility_instruction_control.jsonl",
    "stage_t_mechanistic_eligibility_lineage_base.jsonl",
    "stage_t_mechanistic_eligibility_target.jsonl",
    "stage_t_pair_joint_eligibility.jsonl",
    "stage_t_prompt_tokenization_instruction_control.jsonl",
    "stage_t_prompt_tokenization_lineage_base.jsonl",
    "stage_t_prompt_tokenization_target.jsonl",
    "stage_t_selected_annotations.jsonl",
    "stage_t_selected_mechanistic_confirmation.jsonl",
    "stage_t_selected_mechanistic_development.jsonl",
)
ATTEMPT_RECEIPT_PREFIX = "stage_t_attempt_receipt_"


def _identity_entry(role: str, model_result: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    registered = {item[0]: item for item in s2.MODEL_IDENTITIES}
    if role not in registered:
        raise StageTError(f"unregistered model role: {role}")
    _, model_id, revision = registered[role]
    if snapshot["model_id"] != model_id:
        raise StageTError(
            f"{role} model identity drift: {snapshot['model_id']} != {model_id}"
        )
    if snapshot["requested_revision"] != revision or snapshot["resolved_revision"] != revision:
        raise StageTError(
            f"{role} revision drift: requested={snapshot['requested_revision']} "
            f"resolved={snapshot['resolved_revision']} registered={revision}"
        )
    weights = classify_weight_files(entry["name"] for entry in snapshot["files"])
    if weights:
        raise StageTError(f"{role} snapshot contains weight files: {weights}")
    profile = model_result["profile"]
    return {
        "adds_bos": bool(profile["adds_bos"]),
        "bos_prefix_decoded": profile["prefix_decoded"],
        "bos_prefix_token_ids": profile["prefix_token_ids"],
        "config_model_type": snapshot["config_model_type"],
        "files": [dict(sorted(entry.items())) for entry in snapshot["files"]],
        "model_id": model_id,
        "option_token_ids": stable_option_token_ids(model_result),
        "requested_revision": revision,
        "resolved_revision": revision,
        "role": role,
        "special_token_ids": profile["all_special_ids"],
        "special_suffix_token_ids": profile["suffix_token_ids"],
        "tokenizer_class": profile["tokenizer_class"],
        "trust_remote_code": False,
        "weight_files_present": [],
    }


def run_gate(
    root: Path,
    tokenizers: Mapping[str, TokenizerLike],
) -> dict[str, Any]:
    """Execute the complete Stage T gate over the frozen banks."""

    missing = sorted(set(MODEL_ROLES) - set(tokenizers))
    if missing:
        raise StageTError(f"missing pinned tokenizers: {missing}")
    frozen = verify_frozen_inputs(root)
    banks = load_frozen_banks(root)
    prompt_rows = iter_prompt_rows(banks)

    model_results = {
        role: evaluate_model(role, tokenizers[role], banks, prompt_rows)
        for role in MODEL_ROLES
    }
    joint = join_eligibility(banks, model_results)
    selection = select_pairs(joint)
    digits = digit_support(tokenizers["target"], model_results["target"]["profile"])
    return {
        "banks": banks,
        "frozen_inputs": frozen,
        "joint": joint,
        "model_results": model_results,
        "prompt_rows": prompt_rows,
        "selection": selection,
        "target_digit_support": digits,
    }


def _selected_payload(
    banks: Mapping[str, list[tuple[bytes, dict[str, Any]]]],
    joint: Sequence[Mapping[str, Any]],
    role: str,
) -> tuple[bytes, list[dict[str, Any]], list[str]]:
    """Emit selected rows byte-exactly, plus their separate annotation table."""

    source: dict[str, tuple[int, bytes, dict[str, Any]]] = {}
    for index, (line, pair) in enumerate(banks[role]):
        source[pair["pair_id"]] = (index, line, pair)

    by_pair = {row["pair_id"]: row for row in joint if row["role"] == role}
    ordered: list[Mapping[str, Any]] = []
    for family in s2.FAMILIES:
        for depth in CELL_DEPTHS:
            cell = [
                row
                for row in by_pair.values()
                if row["selected"]
                and row["family"] == family
                and int(row["depth"]) == depth
            ]
            ordered.extend(sorted(cell, key=lambda item: item["selection_rank"]))

    lines: list[bytes] = []
    annotations: list[dict[str, Any]] = []
    pair_ids: list[str] = []
    for row in ordered:
        index, line, pair = source[row["pair_id"]]
        lines.append(line)
        pair_ids.append(row["pair_id"])
        annotations.append(
            {
                "cell": cell_key(role, row["family"], int(row["depth"])),
                "depth": int(row["depth"]),
                "family": row["family"],
                "pair_id": row["pair_id"],
                "pair_semantic_id": row["pair_semantic_id"],
                "role": role,
                "schema_version": ANNOTATION_ROW_VERSION,
                "selection_rank": int(row["selection_rank"]),
                "source_line_index": index,
                "source_row_sha256": sha256_bytes(line),
                "template_id": pair["template_id"],
            }
        )
    payload = b"".join(line + b"\n" for line in lines)
    return payload, annotations, pair_ids


def write_pack(
    output_dir: Path,
    result: Mapping[str, Any],
    environment: Mapping[str, Any],
    snapshots: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Write every Stage T artifact deterministically, manifest last."""

    banks = result["banks"]
    joint = result["joint"]
    files: dict[str, dict[str, Any]] = {}

    identity = {
        "models": [
            _identity_entry(role, result["model_results"][role], snapshots[role])
            for role in MODEL_ROLES
        ],
        "schema_version": IDENTITY_RECEIPT_VERSION,
        "trust_remote_code": False,
        "weight_files_present": [],
    }
    files["stage_t_identity_receipt.json"] = write_json(
        output_dir / "stage_t_identity_receipt.json", identity
    )

    for role in MODEL_ROLES:
        name = f"stage_t_prompt_tokenization_{role}.jsonl"
        files[name] = write_jsonl(
            output_dir / name, result["model_results"][role]["prompt_pack"]
        )
        name = f"stage_t_mechanistic_eligibility_{role}.jsonl"
        files[name] = write_jsonl(
            output_dir / name, result["model_results"][role]["eligibility"]
        )

    files["stage_t_pair_joint_eligibility.jsonl"] = write_jsonl(
        output_dir / "stage_t_pair_joint_eligibility.jsonl", joint
    )

    annotations: list[dict[str, Any]] = []
    selected_files = {
        "mechanistic_development": "stage_t_selected_mechanistic_development.jsonl",
        "mechanistic_candidate_confirmation": "stage_t_selected_mechanistic_confirmation.jsonl",
    }
    selected_ids: dict[str, list[str]] = {}
    for role, name in selected_files.items():
        payload, rows, pair_ids = _selected_payload(banks, joint, role)
        files[name] = write_raw(output_dir / name, payload, len(pair_ids))
        annotations.extend(rows)
        selected_ids[role] = pair_ids
    files["stage_t_selected_annotations.jsonl"] = write_jsonl(
        output_dir / "stage_t_selected_annotations.jsonl", annotations
    )

    files["stage_t_jlens_digit_support.json"] = write_json(
        output_dir / "stage_t_jlens_digit_support.json", result["target_digit_support"]
    )

    manifest = build_core_manifest(result, environment, identity, files, selected_ids)
    entry = write_json(output_dir / CORE_MANIFEST_NAME, manifest)
    return {"manifest": manifest, "manifest_entry": entry}


def build_core_manifest(
    result: Mapping[str, Any],
    environment: Mapping[str, Any],
    identity: Mapping[str, Any],
    files: Mapping[str, Mapping[str, Any]],
    selected_ids: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Bind every Stage T obligation into one deterministic core manifest."""

    if set(files) != set(PACK_FILES):
        raise StageTError(
            f"core manifest file set drift: {sorted(set(files) ^ set(PACK_FILES))}"
        )
    selection = result["selection"]
    models = {
        role: {
            "eligible_pairs": sum(
                1 for row in result["model_results"][role]["eligibility"] if row["eligible"]
            ),
            "eligibility_reason_counts": _reason_counts(
                result["model_results"][role]["eligibility"]
            ),
            "option_token_ids": stable_option_token_ids(result["model_results"][role]),
            "prompt_failure_counts": result["model_results"][role]["prompt_failure_counts"],
            "prompt_pass_count": result["model_results"][role]["prompt_pass_count"],
            "prompt_row_count": result["model_results"][role]["prompt_row_count"],
            "unique_prompt_count": result["model_results"][role]["unique_prompt_count"],
        }
        for role in MODEL_ROLES
    }
    joint_eligible = sum(1 for row in result["joint"] if row["eligible_all_models"])
    total_selected = sum(len(values) for values in selected_ids.values())
    complete = (
        selection["sufficient"]
        and all(entry["prompt_pass_count"] == entry["prompt_row_count"] for entry in models.values())
        and total_selected == SELECTED_PER_ROLE * len(MECHANISTIC_BANKS)
    )
    return {
        "authority": {
            "amendment_path": AMENDMENT_PATH,
            "path": AUTHORITY_PATH,
            "sha256": AUTHORITY_SHA256,
            "starting_state_disposition": STARTING_STATE_DISPOSITION,
            "bytes": AUTHORITY_BYTES,
        },
        "environment": dict(sorted(environment.items())),
        "files": {name: dict(sorted(row.items())) for name, row in sorted(files.items())},
        "frozen_inputs": {
            name: dict(sorted(row.items()))
            for name, row in sorted(result["frozen_inputs"].items())
        },
        "identities": identity["models"],
        "joint_eligible_pairs": joint_eligible,
        "models": dict(sorted(models.items())),
        "operation_counts": {
            "activation_operations": 0,
            "forward_passes": 0,
            "generations": 0,
            "gpu_jobs": 0,
            "lens_operations": 0,
            "model_downloads": 0,
            "patching_operations": 0,
            "probe_fits": 0,
            "scientific_evidence_rows": 0,
            "semantic_review_provider_calls": 0,
            "tokenizer_constructions": len(MODEL_ROLES),
            "weight_loads": 0,
        },
        "prompt_row_count_per_model": len(result["prompt_rows"]),
        "schema_version": CORE_MANIFEST_VERSION,
        "selection": {
            "cells": selection["cells"],
            "selected_per_cell": SELECTED_PER_CELL,
            "selected_per_role": SELECTED_PER_ROLE,
            "selected_total": total_selected,
            "shortfalls": selection["shortfalls"],
            "sort": "ascending pair_semantic_id",
            "sufficient": selection["sufficient"],
        },
        "stage_p": {
            "freeze_commit": STAGE_P_FREEZE_COMMIT,
            "freeze_tree": STAGE_P_FREEZE_TREE,
            "start_commit": STAGE_T_START_COMMIT,
            "start_tree": STAGE_T_START_TREE,
        },
        "target_digit_support": {
            "bare_all_single_token": result["target_digit_support"]["bare_all_single_token"],
            "role": "target_only_secondary_axis",
            "rescue_prohibited": True,
            "selection_prohibited": True,
            "space_prefixed_all_single_token": result["target_digit_support"][
                "space_prefixed_all_single_token"
            ],
        },
        "terminal_state": TERMINAL_STATE if complete else None,
    }


def _reason_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Count eligibility reasons densely.

    The key set is fixed by ``ELIGIBILITY_REASONS`` rather than by whichever
    reasons happen to occur, because a sparse map cannot be expressed in a
    closed schema whose ``required`` equals its ``properties``.
    """

    counts = {code: 0 for code in sorted(ELIGIBILITY_REASONS)}
    for row in rows:
        for reason in row["reason_codes"]:
            if reason not in counts:
                raise StageTError(f"unregistered eligibility reason: {reason}")
            counts[reason] += 1
    return counts
