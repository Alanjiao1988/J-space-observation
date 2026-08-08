"""Adversarial, model-free tests for the Study 2 Stage T tokenizer gate.

Every tokenizer here is a fake.  No test downloads a checkpoint, constructs a
real tokenizer, loads a weight, or runs a forward pass; the point is to prove
that Stage T *refuses* the failure modes that would otherwise silently corrupt
a mechanistic pair set, and that its selection is a pure function of frozen
mechanics.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_t as st  # noqa: E402

SCHEMA_PATH = ROOT / "studies/study2/protocol/stage_t_pack.schema.json"

STAGE_T_SOURCES = (
    "src/jspace_observation/study2_stage_t.py",
    "scripts/run_study2_stage_t.py",
    "scripts/validate_study2_stage_t.py",
)

# Modules and symbols that would turn Stage T into a measurement stage.
FORBIDDEN_IMPORTS = (
    "torch",
    "openai",
    "anthropic",
    "google",
    "vllm",
    "accelerate",
    "datasets",
    "jspace_observation",
)
FORBIDDEN_SYMBOLS = (
    "AutoModel",
    "AutoModelForCausalLM",
    "AutoModelForSequenceClassification",
    "from_pretrained_model",
    "generate",
)

# A cl100k-style pre-tokenisation: letters may absorb one leading non-word
# character (so " A" is a single token), digits never do, and every remaining
# character is covered so that decoding is exactly the inverse of encoding.
_PATTERN = re.compile(
    r"[^\r\n\w]?[A-Za-z]+|\d{1,3}| ?[^\s\w]+|\s*[\r\n]+|\s+(?!\S)|\s+|[\s\S]"
)

PROMPT = (
    "Apply the operations to the start state.\n"
    "Start: 7\n"
    "Options:\n"
    "A) 1\nB) 2\nC) 3\nD) 4\n"
    "Answer:"
)
ANCHOR_BYTE_START = PROMPT.encode("utf-8").index(b"Start: ") + len("Start: ")
ANCHOR = {
    "byte_end": ANCHOR_BYTE_START + 1,
    "byte_start": ANCHOR_BYTE_START,
    "field": "Start:",
    "surface": "7",
}


class FakeTokenizer:
    """A deterministic, prefix-consistent, exactly invertible fake."""

    def __init__(self, bos: int | None = None, eos: int | None = None) -> None:
        self._vocab: dict[str, int] = {}
        self._inverse: dict[int, str] = {}
        self._next = 100
        self.bos = bos
        self.eos = eos
        self.all_special_ids = [value for value in (bos, eos) if value is not None]

    def pieces(self, text: str) -> list[str]:
        return _PATTERN.findall(text)

    def _id(self, piece: str) -> int:
        if piece not in self._vocab:
            self._vocab[piece] = self._next
            self._inverse[self._next] = piece
            self._next += 1
        return self._vocab[piece]

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        ids = [self._id(piece) for piece in self.pieces(text)]
        if add_special_tokens:
            if self.bos is not None:
                ids = [self.bos] + ids
            if self.eos is not None:
                ids = ids + [self.eos]
        return ids

    def decode(
        self,
        token_ids,
        skip_special_tokens: bool = False,
        clean_up_tokenization_spaces: bool = False,
    ) -> str:
        out = []
        for value in token_ids:
            if value == self.bos:
                out.append("<bos>")
            elif value == self.eos:
                out.append("<eos>")
            else:
                out.append(self._inverse[value])
        return "".join(out)


class SplitOptionTokenizer(FakeTokenizer):
    def pieces(self, text: str) -> list[str]:
        pieces = super().pieces(text)
        if pieces and pieces[-1] in (" A", " B", " C", " D"):
            pieces = pieces[:-1] + [pieces[-1][0], pieces[-1][1]]
        return pieces


class SharedOptionTokenizer(FakeTokenizer):
    """Two option surfaces collide on one ID while decode still looks correct.

    This is the dangerous case: a tokenizer that hides a collision behind a
    plausible round-trip.  Only the pairwise-distinctness rule catches it.
    """

    def __init__(self) -> None:
        super().__init__()
        self._last = ""

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        self._last = text
        ids = super().encode(text, add_special_tokens)
        if text.endswith(" C"):
            ids = ids[:-1] + [self._id(" A")]
        return ids

    def decode(self, token_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        text = super().decode(token_ids, skip_special_tokens, clean_up_tokenization_spaces)
        if self._last.endswith(" C") and text.endswith(" A"):
            return text[:-2] + " C"
        return text


class PrefixBreakingTokenizer(FakeTokenizer):
    """Retokenises the prompt's final token when an option is appended."""

    def pieces(self, text: str) -> list[str]:
        pieces = super().pieces(text)
        if len(pieces) >= 2 and pieces[-1] in (" A", " B", " C", " D"):
            pieces = pieces[:-2] + [pieces[-2] + pieces[-1][0], pieces[-1][1]]
        return pieces


class DecodeDriftTokenizer(FakeTokenizer):
    def decode(self, token_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        text = super().decode(token_ids, skip_special_tokens, clean_up_tokenization_spaces)
        return text.replace("Answer:", "Answer :")


class MergedAnchorTokenizer(FakeTokenizer):
    """Merges 'Start:' with the space and digit into a single token."""

    def pieces(self, text: str) -> list[str]:
        pieces = super().pieces(text)
        merged: list[str] = []
        index = 0
        while index < len(pieces):
            if (
                pieces[index] == "Start"
                and index + 3 < len(pieces)
                and pieces[index + 1] == ":"
                and pieces[index + 3].isdigit()
            ):
                merged.append("".join(pieces[index : index + 4]))
                index += 4
            else:
                merged.append(pieces[index])
                index += 1
        return merged


def profile_of(tokenizer):
    return st.special_token_profile(tokenizer)


def gate(tokenizer, prompt=PROMPT, sha=None):
    return st.gate_prompt(
        tokenizer, profile_of(tokenizer), prompt, sha or st.sha256_text(prompt)
    )


# --------------------------------------------------------------------------
# Option and prompt gate
# --------------------------------------------------------------------------


def test_well_formed_tokenizer_passes_the_option_gate() -> None:
    tokenizer = FakeTokenizer()
    row = gate(tokenizer)
    assert row["status"] == "PASS"
    assert row["failure_reasons"] == []
    assert sorted(row["option_token_ids"]) == ["A", "B", "C", "D"]
    assert len(set(row["option_token_ids"].values())) == 4
    assert row["answer_position_index"] == row["input_length"] - 1
    assert row["input_ids_sha256"] == st.ids_sha256(row["token_ids"])


def test_prompt_hash_mismatch_fails_closed() -> None:
    row = gate(FakeTokenizer(), sha="0" * 64)
    assert row["status"] == "FAIL"
    assert row["failure_reasons"] == ["PROMPT_HASH_MISMATCH"]
    assert row["input_length"] is None
    assert row["option_token_ids"] is None


def test_missing_answer_terminator_fails_closed() -> None:
    mutated = PROMPT + " "
    row = gate(FakeTokenizer(), prompt=mutated)
    assert row["status"] == "FAIL"
    assert "PROMPT_TERMINATOR_MISSING" in row["failure_reasons"]


def test_option_split_into_two_tokens_is_refused() -> None:
    row = gate(SplitOptionTokenizer())
    assert row["status"] == "FAIL"
    assert "OPTION_NOT_SINGLE_TOKEN" in row["failure_reasons"]


def test_options_sharing_a_token_id_are_refused() -> None:
    row = gate(SharedOptionTokenizer())
    assert row["status"] == "FAIL"
    assert "OPTION_IDS_NOT_DISTINCT" in row["failure_reasons"]


def test_prompt_prefix_retokenisation_is_refused() -> None:
    row = gate(PrefixBreakingTokenizer())
    assert row["status"] == "FAIL"
    assert "PROMPT_PREFIX_NOT_PRESERVED" in row["failure_reasons"]


def test_decode_drift_is_refused() -> None:
    tokenizer = DecodeDriftTokenizer()
    row = st.gate_prompt(tokenizer, profile_of(tokenizer), PROMPT, st.sha256_text(PROMPT))
    assert row["status"] == "FAIL"
    assert "PROMPT_ROUND_TRIP_DRIFT" in row["failure_reasons"]


def test_bos_behaviour_is_measured_not_assumed() -> None:
    plain = FakeTokenizer()
    with_bos = FakeTokenizer(bos=1)
    assert profile_of(plain)["adds_bos"] is False
    assert profile_of(with_bos)["adds_bos"] is True
    assert profile_of(with_bos)["prefix_token_ids"] == [1]

    plain_row = gate(plain)
    bos_row = gate(with_bos)
    assert bos_row["status"] == "PASS"
    assert bos_row["input_length"] == plain_row["input_length"] + 1
    assert bos_row["answer_position_index"] == bos_row["input_length"] - 1
    assert bos_row["input_ids_sha256"] != plain_row["input_ids_sha256"]


def test_trailing_special_token_is_refused_outright() -> None:
    row = gate(FakeTokenizer(eos=2))
    assert row["status"] == "FAIL"
    assert row["failure_reasons"] == ["SPECIAL_SUFFIX_PRESENT"]


def test_truncating_tokenizer_is_refused() -> None:
    tokenizer = FakeTokenizer()
    tokenizer.model_max_length = 4
    row = gate(tokenizer)
    assert row["status"] == "FAIL"
    assert "INPUT_TRUNCATED" in row["failure_reasons"]


def test_every_registered_failure_reason_is_closed() -> None:
    with pytest.raises(st.StageTError):
        st._failed_prompt_row(["NOT_A_REGISTERED_REASON"])


# --------------------------------------------------------------------------
# Wrong-position anchor resolution
# --------------------------------------------------------------------------


def test_anchor_resolves_to_exactly_one_token() -> None:
    tokenizer = FakeTokenizer()
    index = st.resolve_anchor_token_index(tokenizer, profile_of(tokenizer), PROMPT, ANCHOR)
    assert isinstance(index, int)
    ids = tokenizer.encode(PROMPT, add_special_tokens=True)
    assert tokenizer.decode([ids[index]]) == "7"


def test_anchor_resolution_survives_a_bos_prefix() -> None:
    tokenizer = FakeTokenizer(bos=1)
    index = st.resolve_anchor_token_index(tokenizer, profile_of(tokenizer), PROMPT, ANCHOR)
    ids = tokenizer.encode(PROMPT, add_special_tokens=True)
    assert tokenizer.decode([ids[index]]) == "7"


def test_anchor_surface_mismatch_is_unresolved() -> None:
    tokenizer = FakeTokenizer()
    bad = dict(ANCHOR, surface="9")
    assert st.resolve_anchor_token_index(tokenizer, profile_of(tokenizer), PROMPT, bad) is None


def test_anchor_merged_into_a_neighbour_is_unresolved() -> None:
    tokenizer = MergedAnchorTokenizer()
    assert (
        st.resolve_anchor_token_index(tokenizer, profile_of(tokenizer), PROMPT, ANCHOR)
        is None
    )


def test_out_of_range_anchor_is_unresolved() -> None:
    tokenizer = FakeTokenizer()
    for bad in (
        dict(ANCHOR, byte_start=-1),
        dict(ANCHOR, byte_end=ANCHOR["byte_start"]),
        dict(ANCHOR, byte_end=len(PROMPT.encode("utf-8")) + 5),
    ):
        assert (
            st.resolve_anchor_token_index(tokenizer, profile_of(tokenizer), PROMPT, bad)
            is None
        )


# --------------------------------------------------------------------------
# Pair eligibility
# --------------------------------------------------------------------------


def _pair(pair_id: str, semantic_id: str, family: str = "permutation_chain", depth: int = 2) -> dict:
    return {
        "depth": depth,
        "family": family,
        "pair_id": pair_id,
        "pair_semantic_id": semantic_id,
        "role": "mechanistic_development",
        "template_id": "T-A",
    }


def _gate_rows(lengths: dict[str, int], status: str = "PASS") -> dict[str, dict]:
    rows = {}
    for name in st.PAIR_OBJECT_KEYS:
        if status == "PASS":
            rows[name] = {
                "answer_position_index": lengths[name] - 1,
                "failure_reasons": [],
                "input_length": lengths[name],
                "status": "PASS",
            }
        else:
            rows[name] = {
                "answer_position_index": None,
                "failure_reasons": ["OPTION_NOT_SINGLE_TOKEN"],
                "input_length": None,
                "status": "FAIL",
            }
    return rows


def test_aligned_pair_is_eligible() -> None:
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    row = st.evaluate_pair(_pair("p1", "a" * 64), _gate_rows(lengths), 12, True)
    assert row["eligible"] is True
    assert row["reason_codes"] == []
    assert row["input_length"] == 40
    assert row["answer_position_index"] == 39
    assert row["wrong_position_index"] == 12


def test_unequal_pair_lengths_are_ineligible() -> None:
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    lengths["primary_donor"] = 41
    row = st.evaluate_pair(_pair("p1", "a" * 64), _gate_rows(lengths), 12, True)
    assert row["eligible"] is False
    assert "UNEQUAL_INPUT_LENGTH" in row["reason_codes"]
    assert row["input_length"] is None


def test_unresolved_anchor_is_ineligible() -> None:
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    row = st.evaluate_pair(_pair("p1", "a" * 64), _gate_rows(lengths), None, True)
    assert row["eligible"] is False
    assert row["reason_codes"] == ["WRONG_POSITION_ANCHOR_UNRESOLVED"]


def test_anchor_surface_disagreement_is_ineligible() -> None:
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    row = st.evaluate_pair(_pair("p1", "a" * 64), _gate_rows(lengths), None, False)
    assert row["eligible"] is False
    assert row["reason_codes"] == ["WRONG_POSITION_ANCHOR_SURFACE_MISMATCH"]


def test_option_gate_failure_propagates_to_the_pair() -> None:
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    row = st.evaluate_pair(_pair("p1", "a" * 64), _gate_rows(lengths, status="FAIL"), 12, True)
    assert row["eligible"] is False
    assert row["reason_codes"] == ["OPTION_GATE_FAILED"]


def test_joint_eligibility_is_a_strict_conjunction() -> None:
    pair = _pair("p1", "a" * 64)
    banks = {
        "mechanistic_development": [(b"{}", pair)],
        "mechanistic_candidate_confirmation": [],
    }
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    eligible = st.evaluate_pair(pair, _gate_rows(lengths), 12, True)
    ineligible = st.evaluate_pair(pair, _gate_rows(lengths), None, True)
    results = {
        "target": {"eligibility": [eligible]},
        "lineage_base": {"eligibility": [eligible]},
        "instruction_control": {"eligibility": [ineligible]},
    }
    joint = st.join_eligibility(banks, results)
    assert len(joint) == 1
    assert joint[0]["eligible_all_models"] is False
    assert joint[0]["model_eligibility"] == {
        "instruction_control": False,
        "lineage_base": True,
        "target": True,
    }
    assert joint[0]["reason_codes"] == ["WRONG_POSITION_ANCHOR_UNRESOLVED"]


# --------------------------------------------------------------------------
# Selection mechanics
# --------------------------------------------------------------------------


def _joint_row(index: int, role: str, family: str, depth: int, eligible: bool = True) -> dict:
    semantic = hashlib.sha256(f"{role}|{family}|{depth}|{index}".encode()).hexdigest()
    return {
        "depth": depth,
        "eligible_all_models": eligible,
        "family": family,
        "model_eligibility": {role_name: eligible for role_name in st.MODEL_ROLES},
        "pair_id": f"{role}-{family}-d{depth}-{index:04d}",
        "pair_semantic_id": semantic,
        "reason_codes": [],
        "role": role,
        "schema_version": st.JOINT_ROW_VERSION,
        "selected": False,
        "selection_rank": None,
    }


def _synthetic_joint(per_cell: int = 6, eligible: int | None = None) -> list[dict]:
    rows = []
    for role in st.MECHANISTIC_BANKS:
        for family in s2.FAMILIES:
            for depth in st.CELL_DEPTHS:
                for index in range(per_cell):
                    ok = True if eligible is None else index < eligible
                    rows.append(_joint_row(index, role, family, depth, ok))
    return rows


def test_selection_takes_the_first_n_by_ascending_semantic_id(monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 3)
    rows = _synthetic_joint(per_cell=6)
    result = st.select_pairs(rows)
    assert result["sufficient"] is True
    assert result["shortfalls"] == []
    for key, cell in result["cells"].items():
        assert cell["selected"] == 3
        assert cell["selected_pair_semantic_ids"] == sorted(cell["selected_pair_semantic_ids"])
        pool = sorted(
            row["pair_semantic_id"]
            for row in rows
            if st.cell_key(row["role"], row["family"], row["depth"]) == key
        )
        assert cell["selected_pair_semantic_ids"] == pool[:3]
    assert sorted(result["cells"]) == sorted(st.expected_cells())


def test_selection_is_order_independent(monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 3)
    rows = _synthetic_joint(per_cell=6)
    forward = st.select_pairs(copy.deepcopy(rows))
    reversed_rows = list(reversed(copy.deepcopy(rows)))
    backward = st.select_pairs(reversed_rows)
    assert forward["cells"] == backward["cells"]


def test_selection_ignores_any_outcome_shaped_field(monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 3)
    baseline = st.select_pairs(_synthetic_joint(per_cell=6))
    contaminated = _synthetic_joint(per_cell=6)
    for index, row in enumerate(contaminated):
        row["accuracy"] = 1.0 - index
        row["logit_margin"] = float(index)
    assert st.select_pairs(contaminated)["cells"] == baseline["cells"]


def test_shortfall_is_reported_and_never_backfilled(monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 3)
    result = st.select_pairs(_synthetic_joint(per_cell=6, eligible=2))
    assert result["sufficient"] is False
    assert len(result["shortfalls"]) == len(st.expected_cells())
    for cell in result["cells"].values():
        assert cell["selected"] == 2
        assert cell["eligible"] == 2


def test_a_pair_outside_the_eight_cells_is_refused() -> None:
    row = _joint_row(0, "mechanistic_development", "permutation_chain", 4)
    with pytest.raises(st.StageTError):
        st.select_pairs([row])


# --------------------------------------------------------------------------
# Pack writing
# --------------------------------------------------------------------------


def _synthetic_result(per_cell: int) -> dict:
    joint = _synthetic_joint(per_cell=per_cell)
    banks: dict[str, list] = {role: [] for role in st.MECHANISTIC_BANKS}
    for row in joint:
        pair = {
            "depth": row["depth"],
            "family": row["family"],
            "pair_id": row["pair_id"],
            "pair_semantic_id": row["pair_semantic_id"],
            "role": row["role"],
            "template_id": "T-A",
        }
        banks[row["role"]].append((s2.canonical_json_bytes(pair).rstrip(b"\n"), pair))
    lengths = {name: 40 for name in st.PAIR_OBJECT_KEYS}
    eligibility = {
        role: [
            st.evaluate_pair(
                {
                    "depth": row["depth"],
                    "family": row["family"],
                    "pair_id": row["pair_id"],
                    "pair_semantic_id": row["pair_semantic_id"],
                    "role": row["role"],
                    "template_id": "T-A",
                },
                _gate_rows(lengths),
                12,
                True,
            )
            for row in joint
        ]
        for role in st.MODEL_ROLES
    }
    tokenizer = FakeTokenizer()
    profile = profile_of(tokenizer)
    prompt_row = gate(tokenizer)
    model_results = {
        role: {
            "eligibility": eligibility[role],
            "option_token_ids": {
                label: [value] for label, value in prompt_row["option_token_ids"].items()
            },
            "profile": profile,
            "prompt_failure_counts": {
                code: 0 for code in sorted(st.OPTION_GATE_REASONS)
            },
            "prompt_pass_count": 1,
            "prompt_pack": [
                {
                    "answer_position_index": prompt_row["answer_position_index"],
                    "arm": "NT",
                    "bank": "development",
                    "failure_reasons": [],
                    "input_ids_sha256": prompt_row["input_ids_sha256"],
                    "input_length": prompt_row["input_length"],
                    "model_role": role,
                    "option_token_ids": prompt_row["option_token_ids"],
                    "prompt_sha256": st.sha256_text(PROMPT),
                    "row_id": "S2-DEV-0001",
                    "schema_version": st.PROMPT_ROW_VERSION,
                    "status": "PASS",
                }
            ],
            "prompt_row_count": 1,
            "role": role,
            "unique_prompt_count": 1,
        }
        for role in st.MODEL_ROLES
    }
    selection = st.select_pairs(joint)
    return {
        "banks": banks,
        "frozen_inputs": {
            name: {"bytes": size, "sha256": digest}
            for name, (size, digest) in st.FROZEN_INPUTS.items()
        },
        "joint": joint,
        "model_results": model_results,
        "prompt_rows": [{"bank": "development"}],
        "selection": selection,
        "target_digit_support": st.digit_support(tokenizer, profile),
    }


def _snapshots() -> dict:
    return {
        role: {
            "config_model_type": "qwen2",
            "files": [{"bytes": 3, "name": "tokenizer.json", "sha256": "0" * 64}],
            "model_id": model_id,
            "requested_revision": revision,
            "resolved_revision": revision,
        }
        for role, model_id, revision in s2.MODEL_IDENTITIES
    }


def test_pack_is_complete_deterministic_and_manifest_last(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 2)
    monkeypatch.setattr(st, "SELECTED_PER_ROLE", 8)
    environment = {"base_image_reference": "python:3.11-bookworm"}

    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    first = st.write_pack(first_dir, _synthetic_result(4), environment, _snapshots())
    second = st.write_pack(second_dir, _synthetic_result(4), environment, _snapshots())

    written = {path.name for path in first_dir.iterdir()}
    assert written == set(st.PACK_FILES) | {st.CORE_MANIFEST_NAME}
    assert set(first["manifest"]["files"]) == set(st.PACK_FILES)
    assert st.CORE_MANIFEST_NAME not in first["manifest"]["files"]

    for name in st.PACK_FILES:
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()
    assert first["manifest_entry"]["sha256"] == second["manifest_entry"]["sha256"]
    assert first["manifest"]["terminal_state"] == st.TERMINAL_STATE
    assert first["manifest"]["operation_counts"]["forward_passes"] == 0
    assert first["manifest"]["operation_counts"]["weight_loads"] == 0
    assert first["manifest"]["operation_counts"]["scientific_evidence_rows"] == 0
    assert first["manifest"]["operation_counts"]["tokenizer_constructions"] == 3


def test_selected_rows_are_byte_exact_and_annotations_stay_separate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 2)
    monkeypatch.setattr(st, "SELECTED_PER_ROLE", 8)
    result = _synthetic_result(4)
    st.write_pack(tmp_path, result, {"base_image_reference": "x"}, _snapshots())

    source = {
        pair["pair_id"]: line
        for role in st.MECHANISTIC_BANKS
        for line, pair in result["banks"][role]
    }
    annotations = [
        json.loads(line)
        for line in (tmp_path / "stage_t_selected_annotations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    selected = (
        (tmp_path / "stage_t_selected_mechanistic_development.jsonl")
        .read_bytes()
        .split(b"\n")[:-1]
    )
    subset = [row for row in annotations if row["role"] == "mechanistic_development"]
    assert len(selected) == len(subset) == 8
    for line, annotation in zip(selected, subset):
        assert line == source[annotation["pair_id"]]
        assert st.sha256_bytes(line) == annotation["source_row_sha256"]
        payload = json.loads(line)
        assert "selection_rank" not in payload
        assert "cell" not in payload


def test_manifest_refuses_an_incomplete_file_set() -> None:
    with pytest.raises(st.StageTError):
        st.build_core_manifest(
            _synthetic_result(4), {}, {"models": []}, {"only_one.json": {}}, {}
        )


# --------------------------------------------------------------------------
# Identity, weights, and the secondary digit axis
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "model.safetensors",
        "model-00001-of-00002.safetensors",
        "model.safetensors.index.json",
        "pytorch_model.bin",
        "pytorch_model-00001-of-00002.bin",
        "model.gguf",
        "weights.pt",
        "weights.pth",
        "flax_model.msgpack",
        "tf_model.h5",
        "rust_model.ot",
        "adapter_model.safetensors",
        "nested/dir/model.safetensors",
    ],
)
def test_weight_files_are_detected(name: str) -> None:
    assert st.classify_weight_files([name]) == [name]


@pytest.mark.parametrize("name", list(st.TOKENIZER_FILE_ALLOWLIST))
def test_allowlisted_tokenizer_files_are_not_weights(name: str) -> None:
    assert st.classify_weight_files([name]) == []


def test_identity_entry_refuses_a_weight_file() -> None:
    tokenizer = FakeTokenizer()
    model_result = {
        "profile": profile_of(tokenizer),
        "option_token_ids": {label: [index] for index, label in enumerate(st.OPTION_LABELS)},
    }
    snapshot = dict(
        _snapshots()["target"],
        files=[{"bytes": 1, "name": "model.safetensors", "sha256": "0" * 64}],
    )
    with pytest.raises(st.StageTError):
        st._identity_entry("target", model_result, snapshot)


def test_identity_entry_refuses_a_revision_swap() -> None:
    tokenizer = FakeTokenizer()
    model_result = {
        "profile": profile_of(tokenizer),
        "option_token_ids": {label: [index] for index, label in enumerate(st.OPTION_LABELS)},
    }
    snapshot = dict(_snapshots()["target"], resolved_revision="f" * 40)
    with pytest.raises(st.StageTError):
        st._identity_entry("target", model_result, snapshot)


def test_unstable_option_ids_collapse_to_none() -> None:
    assert st.stable_option_token_ids({"option_token_ids": {"A": [1, 2]}}) is None
    assert st.stable_option_token_ids(
        {"option_token_ids": {"A": [1], "B": [2], "C": [3], "D": [4]}}
    ) == {"A": 1, "B": 2, "C": 3, "D": 4}


def test_digit_support_is_secondary_and_cannot_select_or_rescue() -> None:
    tokenizer = FakeTokenizer()
    support = st.digit_support(tokenizer, profile_of(tokenizer))
    assert support["role"] == "target_only_secondary_axis"
    assert support["rescue_prohibited"] is True
    assert support["selection_prohibited"] is True
    assert support["surface_count"] == 20
    assert len(support["surfaces"]) == 20
    assert support["bare_all_single_token"] is True


# --------------------------------------------------------------------------
# Frozen inputs, schema, and source hygiene
# --------------------------------------------------------------------------


def test_frozen_inputs_match_the_repository() -> None:
    verified = st.verify_frozen_inputs(ROOT)
    assert set(verified) == set(st.FROZEN_INPUTS)
    for relative, row in verified.items():
        assert row["sha256"] == st.FROZEN_INPUTS[relative][1]


def test_frozen_input_drift_is_a_hard_stop(tmp_path) -> None:
    with pytest.raises(st.StageTError):
        st.verify_frozen_inputs(tmp_path)


def test_prompt_enumeration_covers_every_frozen_prompt() -> None:
    banks = st.load_frozen_banks(ROOT)
    rows = st.iter_prompt_rows(banks)
    keys = [(row["bank"], row["row_id"], row["arm"]) for row in rows]
    assert len(keys) == len(set(keys))

    expected = 0
    for bank in st.BEHAVIORAL_BANKS:
        expected += sum(len(row["prompts"]) for _, row in banks[bank])
    for bank in st.MECHANISTIC_BANKS:
        expected += len(banks[bank]) * len(st.PAIR_OBJECT_KEYS)
    assert len(rows) == expected

    for row in rows:
        assert st.sha256_text(row["prompt"]) == row["prompt_sha256"]
        assert row["prompt"].endswith(st.PROMPT_TERMINATOR)


def test_mechanistic_banks_expose_the_registered_anchor() -> None:
    banks = st.load_frozen_banks(ROOT)
    for bank in st.MECHANISTIC_BANKS:
        for _, pair in banks[bank]:
            recipient = pair["primary"]["recipient"]
            assert pair["wrong_position_anchor"] == recipient["start_anchor"]
            raw = recipient["nt_prompt"].encode("utf-8")
            anchor = recipient["start_anchor"]
            assert (
                raw[anchor["byte_start"] : anchor["byte_end"]].decode("utf-8")
                == anchor["surface"]
            )


def test_stage_t_schema_is_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    s2.verify_schema_closed(schema)
    assert SCHEMA_PATH.read_bytes().replace(b"\r\n", b"\n").endswith(b"\n")


def test_emitted_rows_validate_against_the_closed_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(st, "SELECTED_PER_CELL", 2)
    monkeypatch.setattr(st, "SELECTED_PER_ROLE", 8)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    result = _synthetic_result(4)
    st.write_pack(tmp_path, result, {"base_image_reference": "x"}, _snapshots())

    named = {
        "stage_t_prompt_tokenization_target.jsonl": "prompt_row",
        "stage_t_mechanistic_eligibility_target.jsonl": "eligibility_row",
        "stage_t_pair_joint_eligibility.jsonl": "joint_row",
        "stage_t_selected_annotations.jsonl": "annotation_row",
    }
    for name, definition in named.items():
        for line in (tmp_path / name).read_text(encoding="utf-8").splitlines():
            s2.validate_json_schema(json.loads(line), {**defs[definition], "$defs": defs})

    identity = json.loads((tmp_path / "stage_t_identity_receipt.json").read_text("utf-8"))
    s2.validate_json_schema(identity, {**defs["identity_receipt"], "$defs": defs})
    digits = json.loads((tmp_path / "stage_t_jlens_digit_support.json").read_text("utf-8"))
    s2.validate_json_schema(digits, {**defs["digit_support"], "$defs": defs})


def test_core_manifest_validates_against_the_closed_schema() -> None:
    """The manifest is built with the real thresholds, so the ``const`` gates bite."""

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    result = _synthetic_result(4)
    snapshots = _snapshots()
    identity = {
        "models": [
            st._identity_entry(role, result["model_results"][role], snapshots[role])
            for role in st.MODEL_ROLES
        ],
        "schema_version": st.IDENTITY_RECEIPT_VERSION,
        "trust_remote_code": False,
        "weight_files_present": [],
    }
    files = {
        name: {
            "bytes": 1,
            "rows": 1 if name.endswith(".jsonl") else None,
            "sha256": "0" * 64,
        }
        for name in st.PACK_FILES
    }
    environment = {
        "base_image_reference": "python:3.11-bookworm",
        "dependency_lock_sha256": "0" * 64,
        "huggingface_hub_pin": "1.26.0",
        "tokenizers_pin": "0.22.2",
        "transformers_pin": "5.14.1",
    }
    manifest = st.build_core_manifest(
        result, environment, identity, files, {role: [] for role in st.MECHANISTIC_BANKS}
    )
    s2.validate_json_schema(manifest, {**defs["core_manifest"], "$defs": defs})
    # The synthetic banks cannot reach 128 pairs per cell, so the gate must stay
    # open rather than declaring the sealed terminal state.
    assert manifest["terminal_state"] is None
    assert manifest["selection"]["sufficient"] is False
    with pytest.raises(s2.ProtocolError):
        s2.validate_json_schema(
            dict(manifest, accuracy=1.0), {**defs["core_manifest"], "$defs": defs}
        )


def test_manifest_row_counts_follow_the_writer_convention(tmp_path: Path) -> None:
    """``write_json`` reports ``rows: null``; the schema must accept it.

    Attempt ``t1a`` (ACR run ``cmcq``) produced a valid pack and was then
    rejected by the validator because ``file_entry.rows`` had been declared
    integer-only while the real JSON writer reports ``null``.  This test binds
    the schema to the writers so the two can never drift again.
    """

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    entry_schema = {**defs["file_entry"], "$defs": defs}

    json_entry = st.write_json(tmp_path / "doc.json", {"a": 1})
    jsonl_entry = st.write_jsonl(tmp_path / "rows.jsonl", [{"a": 1}, {"a": 2}])

    assert json_entry["rows"] is None
    assert jsonl_entry["rows"] == 2
    s2.validate_json_schema(json_entry, entry_schema)
    s2.validate_json_schema(jsonl_entry, entry_schema)

    # A row count is still a count: negatives and non-integers stay rejected.
    for bad in (-1, "2", 1.5):
        with pytest.raises(s2.ProtocolError):
            s2.validate_json_schema(dict(jsonl_entry, rows=bad), entry_schema)

    # Every pack file name implies its own row-count shape.
    for name in st.PACK_FILES:
        assert name.endswith((".json", ".jsonl"))


def test_attempt_receipt_shape_is_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    receipt = {
        "attempt_id": "a1",
        "core_manifest_sha256": "0" * 64,
        "elapsed_seconds_bucket": 3,
        "image_digest": "sha256:" + "0" * 64,
        "platform_machine": "x86_64",
        "python_version": "3.11.14",
        "pythonhashseed": "20240917",
        "run_id": "cmcg",
        "schema_version": st.ATTEMPT_RECEIPT_VERSION,
        "source_commit": "0" * 40,
        "source_tree": "0" * 40,
        "torch_imported": False,
        "weight_load_interlock": [
            "transformers.modeling_utils.PreTrainedModel.from_pretrained"
        ],
        "weight_path_modules_imported": [],
    }
    s2.validate_json_schema(receipt, {**defs["attempt_receipt"], "$defs": defs})
    # The interlock is the guarantee; an empty interlock must be rejected.
    with pytest.raises(s2.ProtocolError):
        s2.validate_json_schema(
            dict(receipt, weight_load_interlock=[]),
            {**defs["attempt_receipt"], "$defs": defs},
        )
    # Recording a transitively imported registry module is allowed, because
    # transformers resolves its auto-class registry without reading a tensor.
    s2.validate_json_schema(
        dict(receipt, weight_path_modules_imported=["transformers.modeling_utils"]),
        {**defs["attempt_receipt"], "$defs": defs},
    )
    with pytest.raises(s2.ProtocolError):
        s2.validate_json_schema(
            dict(receipt, unexpected_field=1),
            {**defs["attempt_receipt"], "$defs": defs},
        )


def test_reason_counts_are_dense_and_reject_unregistered_codes() -> None:
    counts = st._reason_counts([{"reason_codes": ["UNEQUAL_INPUT_LENGTH"]}])
    assert set(counts) == set(st.ELIGIBILITY_REASONS)
    assert counts["UNEQUAL_INPUT_LENGTH"] == 1
    assert counts["ANSWER_POSITION_MISALIGNED"] == 0
    with pytest.raises(st.StageTError):
        st._reason_counts([{"reason_codes": ["NOT_A_REGISTERED_REASON"]}])


def test_an_extra_row_field_is_rejected_by_the_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    row = {
        "depth": 2,
        "eligible_all_models": True,
        "family": "permutation_chain",
        "model_eligibility": {"instruction_control": True, "lineage_base": True, "target": True},
        "pair_id": "p1",
        "pair_semantic_id": "a" * 64,
        "reason_codes": [],
        "role": "mechanistic_development",
        "schema_version": st.JOINT_ROW_VERSION,
        "selected": True,
        "selection_rank": 0,
    }
    s2.validate_json_schema(row, {**defs["joint_row"], "$defs": defs})
    with pytest.raises(s2.ProtocolError):
        s2.validate_json_schema(
            dict(row, accuracy=1.0), {**defs["joint_row"], "$defs": defs}
        )


@pytest.mark.parametrize("relative", list(STAGE_T_SOURCES))
def test_stage_t_sources_import_no_model_or_provider_surface(relative: str) -> None:
    source = (ROOT / relative).read_text(encoding="utf-8")
    tree = ast.parse(source, relative)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(f"{node.module or ''}.{alias.name}" for alias in node.names)
    for name in imported:
        root_module = name.split(".")[0]
        assert root_module not in FORBIDDEN_IMPORTS, f"{relative} imports {name}"
    for symbol in FORBIDDEN_SYMBOLS:
        assert f"{symbol}." not in source and f"{symbol}(" not in source


def test_the_weight_load_interlock_is_installed_before_any_acquisition() -> None:
    """The interlock must precede the first network call, not follow it."""

    source = (ROOT / "scripts/run_study2_stage_t.py").read_text(encoding="utf-8")
    tree = ast.parse(source, "run_study2_stage_t.py")
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    calls = [
        (node.lineno, node.func.id)
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"_install_weight_load_interlock", "stage_snapshot", "build_tokenizer"}
    ]
    ordered = [name for _, name in sorted(calls)]
    assert ordered[0] == "_install_weight_load_interlock", ordered
    assert "stage_snapshot" in ordered and "build_tokenizer" in ordered

    # The interlock must replace loaders rather than merely observe them.
    interlock = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_install_weight_load_interlock"
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "setattr"
        for node in ast.walk(interlock)
    )
    assert "raise st.StageTError" in source


def test_stage_t_module_uses_the_top_level_import_convention() -> None:
    source = (ROOT / "src/jspace_observation/study2_stage_t.py").read_text(encoding="utf-8")
    assert "import study2_protocol as s2" in source
    assert "from . import" not in source


def test_registered_constants_match_the_frozen_protocol() -> None:
    document = s2.load_json(
        ROOT / "studies/study2/protocol/reasoning_internalization_protocol.json"
    )
    assert list(st.OPTION_SURFACES) == document["task_design"]["option_candidate_surfaces"]
    stage_t = document["pair_design"]["stage_t"]
    assert st.SELECTED_PER_ROLE == stage_t["selected_pairs_per_mechanistic_role"]
    assert st.SELECTED_PER_CELL == stage_t["selected_pairs_per_role_family_depth"]
    assert stage_t["sort"] == "ascending pair_semantic_id"
    assert stage_t["replacement_after_inference"] is False
    assert stage_t["insufficient_action"] == "BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT"
    assert list(st.MODEL_ROLES) == [row[0] for row in s2.MODEL_IDENTITIES]
    assert st.CELL_DEPTHS == s2.COMPOSITIONAL_DEPTHS
    assert tuple(sorted(st.MECHANISTIC_BANKS)) == tuple(
        sorted(role for role in s2.EXPECTED_ROLE_COUNTS if role.startswith("mechanistic"))
    )
