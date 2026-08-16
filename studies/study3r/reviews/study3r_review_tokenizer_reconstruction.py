"""Independent Study 3R tokenizer and rendering reconstruction.

Authority:
``studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md``

This module is a *review* artifact. It reconstructs every registered Study 3R
byte and token surface from the four registered immutable revisions without
importing ``studies/study3r/analysis/study3r_tokenizer_probe.py`` and without
importing the candidate task generators. Every rendering rule it uses is
re-typed here from the frozen registry text so that a disagreement between the
candidate and this module is visible rather than absorbed.

Permitted operations only: metadata retrieval, allow-listed tokenizer/config
file download at a pinned immutable revision, tokenizer construction with
``trust_remote_code=False``, chat-template rendering and ``encode``. No model
weight is requested, no model is constructed, no forward pass, logit read,
scoring or generation is performed, and no scientific bank is realized.

Run::

    python studies/study3r/reviews/study3r_review_tokenizer_reconstruction.py

It writes ``study3r_review_tokenizer_reconstruction.json`` beside this module.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Dict, List, Sequence, Tuple

OUT = pathlib.Path(__file__).with_suffix(".json")

# --- registered immutable revisions, re-typed from the acquisition record ----
REVISIONS: Tuple[Tuple[str, str, str], ...] = (
    ("RT", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
     "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"),
    ("RP_B1", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
     "916b56a44061fd5cd7d6a8fb632557ed4f724f60"),
    ("RP_B2", "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
     "1df8507178afcc1bef68cd8c393f61a886323761"),
    ("RP_B3", "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
     "711ad2ea6aa40cfca18895e8aca02ab92df1a746"),
)

ALLOW_LIST: Tuple[str, ...] = (
    "config.json",
    "generation_config.json",
    "tokenizer_config.json",
    "tokenizer.json",
)

WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".h5",
                   ".msgpack", ".gguf", ".onnx", ".npz", ".pkl")

# --- rendering rules, re-typed from the frozen registry ---------------------
ITEM_BODY_TEMPLATE = (
    "You are answering a multiple-choice item.\n"
    "Reply with exactly one option label and nothing else.\n"
    "\n"
    "Item: {stem}\n"
    "A) {option_a}\n"
    "B) {option_b}\n"
    "C) {option_c}\n"
    "D) {option_d}"
)
ANSWER_CUE = "Answer:\n"
RAW_ENVELOPE_SEPARATOR = "\n\n"
FROZEN_REASONING_CLOSURE = "</think>\n\n"
LABELS = ("A", "B", "C", "D")
COT_INSTRUCTION = (
    "Reason step by step. Finish with a final line of exactly the form\n"
    "Final answer: X\n"
    "where X is exactly one option label."
)

STEM_TEMPLATES = {
    "REC": "The stored value is {value}. Report the stored value.",
    "BIND": "Report the label bound to the value {value}.",
    "PRIM": "Compute {a} {op1} {b}.",
    "D2": "Compute ({a} {op1} {b}) {op2} {c}.",
    "D3": "Compute (({a} {op1} {b}) {op2} {c}) {op3} {d}.",
    "NEG": "Compute ({a} {op1} {b}) {op2} {c}.",
}
OPERATION_SYMBOLS = {"ADD": "+", "SUB": "-", "MUL": "*"}
FAMILY_DEPTH = {"REC": 0, "BIND": 0, "PRIM": 1, "D2": 2, "NEG": 2, "D3": 3}


class Counters:
    def __init__(self) -> None:
        self.chat_template_renders = 0
        self.encode_calls = 0
        self.execution_seeds_drawn = 0
        self.forward_passes = 0
        self.generations = 0
        self.logit_reads = 0
        self.metadata_requests = 0
        self.model_constructions = 0
        self.network_file_downloads = 0
        self.scientific_items_realized = 0
        self.scoring_operations = 0
        self.tokenizer_constructions = 0
        self.weight_files_requested = 0

    def as_dict(self) -> Dict[str, int]:
        return dict(sorted(vars(self).items()))


COUNTERS = Counters()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item_key(family: str, stem: str, options: Sequence[int]) -> str:
    canonical = "|".join([family, stem] + [str(option) for option in options])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_stem(family: str, operands: Sequence[int],
                operations: Sequence[str], value: int) -> str:
    template = STEM_TEMPLATES[family]
    if family in ("REC", "BIND"):
        return template.format(value=value)
    fields: Dict[str, object] = {"a": operands[0], "b": operands[1],
                                 "op1": OPERATION_SYMBOLS[operations[0]]}
    if len(operands) > 2:
        fields["c"] = operands[2]
        fields["op2"] = OPERATION_SYMBOLS[operations[1]]
    if len(operands) > 3:
        fields["d"] = operands[3]
        fields["op3"] = OPERATION_SYMBOLS[operations[2]]
    return template.format(**fields)


def render_body(stem: str, options: Sequence[int]) -> str:
    return ITEM_BODY_TEMPLATE.format(
        stem=stem, option_a=options[0], option_b=options[1],
        option_c=options[2], option_d=options[3])


def raw_prompt(body: str) -> str:
    return body + RAW_ENVELOPE_SEPARATOR + ANSWER_CUE


def make_item(family: str, operands: Sequence[int], operations: Sequence[str],
              value: int, options: Sequence[int],
              correct_index: int) -> Dict[str, object]:
    stem = render_stem(family, operands, operations, value)
    return {
        "family": family,
        "depth": FAMILY_DEPTH[family],
        "operands": list(operands),
        "operations": list(operations),
        "value": value,
        "options": list(options),
        "correct_index": correct_index,
        "correct_label": LABELS[correct_index],
        "stem": stem,
        "item_body": render_body(stem, options),
        "item_key": item_key(family, stem, options),
        "is_scientific_item": False,
    }


def fixtures() -> List[Dict[str, object]]:
    """The six registered tokenizer fixtures, re-typed as literal constants."""
    specs = (
        ("REC", (), (), 47, (12, 47, 5, 88), 1),
        ("BIND", (), (), 9, (3, 21, 9, 40), 2),
        ("PRIM", (7, 6), ("MUL",), 42, (36, 48, 42, 40), 2),
        ("D2", (8, 3, 4), ("ADD", "MUL"), 44, (44, 33, 51, 38), 0),
        ("D3", (9, 2, 5, 3), ("MUL", "SUB", "ADD"), 16, (16, 22, 9, 31), 0),
        ("NEG", (6, 5, 2), ("ADD", "MUL"), 22, (14, 27, 35, 8), 3),
    )
    return [make_item(*spec) for spec in specs]


def adversarial_grid() -> List[Dict[str, object]]:
    """A bounded synthetic grid of explicitly *non-scientific* renderings.

    Every item is a literal constant chosen by the reviewer to exercise
    operand/result digit widths, every registered operation, depth 1/2/3, every
    option-label position and newline/spacing boundaries. No PRNG is used, no
    execution seed is drawn, and nothing here is or can become a scientific
    item: every entry carries ``is_scientific_item = False``.
    """
    specs = [
        # depth 1, every operation, one/two-digit operands and results
        ("PRIM", (0, 0), ("ADD",), 0, (0, 1, 2, 3), 0),
        ("PRIM", (9, 9), ("MUL",), 81, (81, 80, 79, 91), 0),
        ("PRIM", (9, 0), ("SUB",), 9, (8, 9, 10, 7), 1),
        ("PRIM", (5, 4), ("ADD",), 9, (7, 8, 9, 19), 2),
        ("PRIM", (8, 8), ("MUL",), 64, (54, 74, 63, 64), 3),
        ("PRIM", (0, 0), ("MUL",), 0, (0, 5, 6, 7), 0),
        # depth 2, one/two/three-digit results, every label position
        ("D2", (0, 0, 0), ("ADD", "ADD"), 0, (0, 1, 2, 3), 0),
        ("D2", (9, 9, 9), ("MUL", "MUL"), 729, (729, 728, 730, 719), 0),
        ("D2", (8, 3, 4), ("ADD", "MUL"), 44, (44, 33, 51, 38), 0),
        ("D2", (9, 9, 9), ("ADD", "MUL"), 162, (152, 162, 172, 161), 1),
        ("D2", (7, 2, 3), ("SUB", "MUL"), 15, (13, 14, 15, 16), 2),
        ("D2", (9, 8, 7), ("MUL", "SUB"), 65, (63, 64, 66, 65), 3),
        ("D2", (1, 1, 1), ("SUB", "ADD"), 1, (0, 1, 2, 3), 1),
        ("D2", (9, 9, 1), ("MUL", "SUB"), 80, (80, 81, 82, 79), 0),
        # depth 3, every label position, one/two/three-digit results
        ("D3", (9, 2, 5, 3), ("MUL", "SUB", "ADD"), 16, (16, 22, 9, 31), 0),
        ("D3", (0, 0, 0, 0), ("ADD", "ADD", "ADD"), 0, (0, 1, 2, 3), 0),
        ("D3", (9, 9, 9, 9), ("MUL", "MUL", "SUB"), 720, (710, 720, 730, 719), 1),
        ("D3", (5, 5, 5, 5), ("ADD", "MUL", "SUB"), 45, (43, 44, 45, 46), 2),
        ("D3", (2, 3, 4, 5), ("ADD", "MUL", "ADD"), 25, (22, 23, 24, 25), 3),
        ("D3", (9, 9, 9, 1), ("MUL", "MUL", "MUL"), 729, (729, 728, 730, 727), 0),
        ("D3", (1, 1, 1, 1), ("SUB", "ADD", "ADD"), 2, (0, 1, 2, 3), 2),
        # depth-0 recovery/binding, one/two/three-digit stored values
        ("REC", (), (), 999, (999, 998, 997, 989), 0),
        ("REC", (), (), 0, (0, 1, 2, 10), 0),
        ("REC", (), (), 47, (12, 47, 5, 88), 1),
        ("BIND", (), (), 100, (99, 100, 101, 110), 1),
        ("BIND", (), (), 7, (5, 6, 7, 17), 2),
        ("BIND", (), (), 500, (498, 499, 501, 500), 3),
        # negative control: no option carries the derivable value
        ("NEG", (6, 5, 2), ("ADD", "MUL"), 22, (14, 27, 35, 8), 3),
        ("NEG", (0, 0, 0), ("ADD", "ADD"), 0, (1, 2, 3, 4), 0),
        ("NEG", (9, 9, 9), ("MUL", "MUL"), 729, (700, 710, 720, 740), 2),
    ]
    return [make_item(*spec) for spec in specs]


def acquire(repo: str, revision: str, cache: pathlib.Path) -> Dict[str, object]:
    """Metadata + allow-listed file retrieval at one immutable revision."""
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    info = api.model_info(repo, revision=revision, files_metadata=False)
    COUNTERS.metadata_requests += 1
    repo_paths = sorted(sibling.rfilename for sibling in (info.siblings or ()))

    files: Dict[str, Dict[str, object]] = {}
    for name in ALLOW_LIST:
        if any(name.endswith(suffix) for suffix in WEIGHT_SUFFIXES):
            raise RuntimeError("allow-list contains a weight-bearing suffix")
        local = hf_hub_download(repo_id=repo, filename=name, revision=revision,
                                cache_dir=str(cache))
        COUNTERS.network_file_downloads += 1
        path = pathlib.Path(local)
        files[name] = {"bytes": path.stat().st_size,
                       "sha256": sha256_file(path),
                       "local": str(path)}
    return {"repository_id": repo, "requested_revision": revision,
            "resolved_revision": info.sha,
            "repository_paths_at_revision": repo_paths,
            "acquired_files": files}


def reconstruct(role: str, repo: str, revision: str, acq: Dict[str, object],
                fixture_items: List[Dict[str, object]],
                grid_items: List[Dict[str, object]]) -> Dict[str, object]:
    from transformers import AutoTokenizer

    local_dir = pathlib.Path(
        acq["acquired_files"]["tokenizer.json"]["local"]).parent
    tokenizer = AutoTokenizer.from_pretrained(str(local_dir),
                                              trust_remote_code=False)
    COUNTERS.tokenizer_constructions += 1

    def encode(text: str) -> List[int]:
        COUNTERS.encode_calls += 1
        return list(tokenizer.encode(text, add_special_tokens=False))

    config = json.loads((local_dir / "config.json").read_text("utf-8"))
    tok_config = json.loads(
        (local_dir / "tokenizer_config.json").read_text("utf-8"))
    gen_config = json.loads(
        (local_dir / "generation_config.json").read_text("utf-8"))
    chat_template = tok_config.get("chat_template") or ""

    surfaces = {}
    for label in LABELS:
        ids = encode(label)
        surfaces[label] = {"text": label, "token_ids": ids,
                           "token_count": len(ids),
                           "utf8_bytes": len(label.encode("utf-8")),
                           "utf8_sha256": sha256_text(label)}
    longest = max(len(surfaces[label]["token_ids"]) for label in LABELS)

    with_special = list(tokenizer.encode("A", add_special_tokens=True))
    COUNTERS.encode_calls += 1
    prepended = with_special[:len(with_special) - len(surfaces["A"]["token_ids"])]

    def render_chat(user_text: str) -> str:
        COUNTERS.chat_template_renders += 1
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": user_text}],
            tokenize=False, add_generation_prompt=True)

    def surfaces_for(item: Dict[str, object]) -> Dict[str, object]:
        body = str(item["item_body"])
        w1 = raw_prompt(body)
        w1_ids = encode(w1)
        generation_prompt = render_chat(body)
        w2 = generation_prompt + FROZEN_REASONING_CLOSURE + ANSWER_CUE
        w2_ids = encode(w2)
        gp_ids = encode(generation_prompt)
        cot = render_chat(body + RAW_ENVELOPE_SEPARATOR + COT_INSTRUCTION)
        cot_ids = encode(cot)
        return {
            "item_key": item["item_key"],
            "family": item["family"],
            "depth": item["depth"],
            "correct_label": item["correct_label"],
            "stem": item["stem"],
            "W1_RAW_DIRECT": {
                "utf8_bytes": len(w1.encode("utf-8")),
                "utf8_sha256": sha256_text(w1),
                "token_count": len(w1_ids),
                "token_ids": w1_ids,
                "d0_common_prefix_token_length": len(w1_ids),
                "d0_discriminant_position": len(w1_ids),
            },
            "W2_ROLE_CANONICAL": {
                "utf8_bytes": len(w2.encode("utf-8")),
                "utf8_sha256": sha256_text(w2),
                "token_count": len(w2_ids),
                "token_ids": w2_ids,
                "generation_prompt_utf8_bytes":
                    len(generation_prompt.encode("utf-8")),
                "generation_prompt_utf8_sha256": sha256_text(generation_prompt),
                "generation_prompt_token_count": len(gp_ids),
                "d0_common_prefix_token_length": len(w2_ids),
                "d0_discriminant_position": len(w2_ids),
            },
            "C1_CANONICAL_GENERATED_COT": {
                "utf8_bytes": len(cot.encode("utf-8")),
                "utf8_sha256": sha256_text(cot),
                "token_count": len(cot_ids),
            },
        }

    fixture_surfaces = [surfaces_for(item) for item in fixture_items]
    grid_surfaces = [surfaces_for(item) for item in grid_items]

    positions_w1 = sorted({s["W1_RAW_DIRECT"]["d0_discriminant_position"]
                           for s in fixture_surfaces + grid_surfaces})
    positions_w2 = sorted({s["W2_ROLE_CANONICAL"]["d0_discriminant_position"]
                           for s in fixture_surfaces + grid_surfaces})

    return {
        "role": role,
        "repository_id": repo,
        "immutable_revision": revision,
        "resolved_revision": acq["resolved_revision"],
        "revision_resolves_to_itself":
            acq["resolved_revision"] == revision,
        "tokenizer_class": type(tokenizer).__name__,
        "trust_remote_code": False,
        "model_type": config.get("model_type"),
        "max_position_embeddings": config.get("max_position_embeddings"),
        "vocab_size_from_config": config.get("vocab_size"),
        "tokenizer_vocab_size": tokenizer.vocab_size,
        "chat_template_sha256": sha256_text(chat_template),
        "chat_template_bytes": len(chat_template.encode("utf-8")),
        "chat_template_opens_reasoning_span": "<think>" in chat_template,
        "chat_template_emits_the_closure_itself": "</think>" in
            render_chat("PROBE"),
        "special_tokens": {
            "bos_token": tokenizer.bos_token,
            "bos_token_id": tokenizer.bos_token_id,
            "eos_token": tokenizer.eos_token,
            "eos_token_id": tokenizer.eos_token_id,
            "pad_token": tokenizer.pad_token,
            "pad_token_id": tokenizer.pad_token_id,
            "unk_token": tokenizer.unk_token,
            "generation_config_bos_token_id": gen_config.get("bos_token_id"),
            "generation_config_eos_token_id": gen_config.get("eos_token_id"),
        },
        "add_special_tokens_prepends": prepended,
        "e0_legal_answer_surfaces": surfaces,
        "e0_longest_legal_answer_surface_tokens": longest,
        "e0_max_new_tokens_recomputed": longest + 1,
        "acquired_file_hashes": {
            name: meta["sha256"]
            for name, meta in acq["acquired_files"].items()},
        "acquired_file_bytes": {
            name: meta["bytes"]
            for name, meta in acq["acquired_files"].items()},
        "weight_paths_present_in_repository": [
            p for p in acq["repository_paths_at_revision"]
            if any(p.endswith(s) for s in WEIGHT_SUFFIXES)],
        "distinct_d0_discriminant_positions_W1_RAW_DIRECT": positions_w1,
        "distinct_d0_discriminant_positions_W2_ROLE_CANONICAL": positions_w2,
        "fixture_surfaces": fixture_surfaces,
        "adversarial_grid_surfaces": grid_surfaces,
    }


def _surface_tuple(entry: Dict[str, object], arm: str) -> Tuple:
    rows = []
    for group in ("fixture_surfaces", "adversarial_grid_surfaces"):
        for surface in entry[group]:
            arm_surface = surface[arm]
            rows.append((surface["item_key"], arm_surface["utf8_sha256"],
                         tuple(arm_surface["token_ids"]),
                         arm_surface["d0_common_prefix_token_length"],
                         arm_surface["d0_discriminant_position"]))
    return tuple(rows)


def run() -> Dict[str, object]:
    import tempfile

    fixture_items = fixtures()
    grid_items = adversarial_grid()
    cache = pathlib.Path(tempfile.gettempdir()) / "study3r_review_tok_cache"
    cache.mkdir(parents=True, exist_ok=True)

    reconstructions = []
    for role, repo, revision in REVISIONS:
        acq = acquire(repo, revision, cache)
        reconstructions.append(
            reconstruct(role, repo, revision, acq, fixture_items, grid_items))

    strata: Dict[str, object] = {}
    for arm in ("W1_RAW_DIRECT", "W2_ROLE_CANONICAL"):
        buckets: Dict[str, List[str]] = {}
        for entry in reconstructions:
            key = hashlib.sha256(
                repr(_surface_tuple(entry, arm)).encode("utf-8")).hexdigest()
            buckets.setdefault(key, []).append(str(entry["role"]))
        strata[arm] = {"distinct_stratum_count": len(buckets),
                       "strata": buckets}

    joint: Dict[str, List[str]] = {}
    for entry in reconstructions:
        key = hashlib.sha256(repr((
            _surface_tuple(entry, "W1_RAW_DIRECT"),
            _surface_tuple(entry, "W2_ROLE_CANONICAL"),
            entry["chat_template_sha256"],
            tuple((label, tuple(entry["e0_legal_answer_surfaces"][label]
                                ["token_ids"])) for label in LABELS),
        )).encode("utf-8")).hexdigest()
        joint.setdefault(key, []).append(str(entry["role"]))

    return {
        "authority": ("studies/study3r/prompts/"
                      "study3r_protocol_v1_single_focused_review_authority.md"),
        "schema_version": "study3r-review-tokenizer-reconstruction-v1",
        "imported_the_candidate_probe": False,
        "imported_the_candidate_task_generators": False,
        "fixture_count": len(fixture_items),
        "adversarial_grid_size": len(grid_items),
        "adversarial_grid_is_scientific": False,
        "surfaces_rendered_per_checkpoint":
            (len(fixture_items) + len(grid_items)),
        "checkpoints": reconstructions,
        "per_arm_strata": strata,
        "joint_strata": {"distinct_stratum_count": len(joint),
                         "strata": joint},
        "counters": COUNTERS.as_dict(),
    }


if __name__ == "__main__":
    payload = run()
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("wrote", OUT)
    print("counters", json.dumps(payload["counters"], sort_keys=True))
    print("joint strata",
          payload["joint_strata"]["distinct_stratum_count"])
    sys.exit(0)
