"""R-1 step 2/3: per-layer lens rank profile on an external control model.

Implements the official evaluation method recovered in R-0, verbatim:

  Lens readout  at each (layer, position) the lens returns a ranked list of
                vocabulary tokens
  Hit           a target token is a hit if it appears at lens rank 1
  Metric        pass@k = mean over items of the fraction of `intermediates`
                whose min-over-layers lens rank <= k

Readout positions are per-set and are NOT unified, because the official README
specifies a different position for each set and harmonising them would be a
silent change of method.

Ranking uses the official readout path, jlens.JacobianLens.apply, so nothing
about the readout is reimplemented here.

OD-011: failing cases in tests/test_eq2_rank_profile.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Registered per-set readout rules, transcribed from data/evaluations/README.md.
READOUT_RULE = {
    "multihop": "token_before_target",
    "multilingual": "token_before_target",
    "order-ops": "token_before_target",
    "poetry": "last_newline_token",
    "association": "final_prompt_token",
    "typo": "final_prompt_token",
}

# order-ops: "each intermediate is a key expanded to a synonym set (numbers ->
# digit and word forms; operations -> symbol and word forms)". The rule is
# published; the explicit lists are not, so this expansion is a RECONSTRUCTION
# of the stated rule and is recorded as such in the report.
NUMBER_WORDS = {
    "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
    "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve",
    "13": "thirteen", "15": "fifteen", "16": "sixteen", "20": "twenty",
    "24": "twenty-four",
}
OPERATION_SYMBOLS = {
    "addition": ["+", "plus", "add"],
    "subtraction": ["-", "minus", "subtract"],
    "multiplication": ["*", "times", "multiply"],
    "division": ["/", "divide", "divided"],
    "mod": ["%", "modulo", "remainder"],
    "squared": ["^", "square", "power"],
}

REGISTERED_GPU_UUIDS = {
    "e85524f36fdf", "b29579ca41a6", "0ec45dca0dfc", "5767cc3ad060",
}


class RankProfileError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def physical_gpu_uuid_last_twelve() -> str:
    import torch

    uuid = None
    try:
        import pynvml

        pynvml.nvmlInit()
        raw = pynvml.nvmlDeviceGetUUID(pynvml.nvmlDeviceGetHandleByIndex(0))
        uuid = raw.decode() if isinstance(raw, bytes) else str(raw)
    except Exception:
        attr = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        if attr is not None:
            uuid = str(attr)
    if not uuid:
        raise RankProfileError("could not resolve the physical GPU UUID (OD-006)")
    last12 = uuid.replace("-", "")[-12:].lower()
    if last12 not in REGISTERED_GPU_UUIDS:
        raise RankProfileError(f"physical GPU {last12} is not registered")
    return last12


def synonym_forms(slug: str, intermediate: str) -> list[str]:
    """Surface forms to try for one intermediate.

    Casing and leading-space variants are always included, because a rank taken
    only on the bare lowercase form would understate readability for tokenizers
    that prefix a space.
    """
    base = [intermediate]
    if slug == "order-ops":
        if intermediate in NUMBER_WORDS:
            base.append(NUMBER_WORDS[intermediate])
        base.extend(OPERATION_SYMBOLS.get(intermediate, []))

    forms: list[str] = []
    for word in base:
        for variant in (word, word.lower(), word.capitalize()):
            for form in (variant, " " + variant):
                if form not in forms:
                    forms.append(form)
    return forms


def single_token_ids(tokenizer, forms: list[str]) -> list[int]:
    """Token ids for those surface forms that encode to exactly one token.

    The official order-ops rule says the rank is the min over SINGLE TOKEN
    synonyms, so multi-token forms are excluded rather than scored on a prefix.
    """
    ids: list[int] = []
    for form in forms:
        encoded = tokenizer(form, add_special_tokens=False)["input_ids"]
        if len(encoded) == 1 and encoded[0] not in ids:
            ids.append(int(encoded[0]))
    return ids


def readout_position(slug: str, token_strings: list[str]) -> int:
    """Index of the position this set reads out at."""
    rule = READOUT_RULE[slug]
    if rule in ("final_prompt_token", "token_before_target"):
        # The prompts stop immediately before the answer, so the token
        # preceding `target` IS the final prompt token.
        return len(token_strings) - 1
    if rule == "last_newline_token":
        for index in range(len(token_strings) - 1, -1, -1):
            if "\n" in token_strings[index]:
                return index
        raise RankProfileError("poetry item has no newline token")
    raise RankProfileError(f"unknown readout rule {rule}")


def score_with_lens(
    lens_model,
    tokenizer,
    lens,
    eval_dir: str,
    max_seq_len: int,
    limit: int = 0,
) -> dict:
    """Score every evaluation set with one lens and return the profile report.

    Factored out so the real measurement and the matched-norm null measurement
    run through LITERALLY the same code. If the null had its own copy of this
    loop, the two could drift apart and the comparison would quietly stop being
    like-for-like.
    """
    import torch

    layers = list(lens.source_layers)
    per_set: dict[str, dict] = {}
    pooled_hits = {k: {layer: 0 for layer in layers} for k in (1, 5, 10)}
    pooled_total = 0
    unrankable: list[dict] = []

    for slug in sorted(READOUT_RULE):
        path = Path(eval_dir) / f"lens-eval-{slug}.json"
        items = json.loads(path.read_text(encoding="utf-8"))["items"]
        if limit:
            items = items[:limit]

        hits = {k: {layer: 0 for layer in layers} for k in (1, 5, 10)}
        min_rank_over_layers: list[int] = []
        scored = 0

        for item in items:
            prompt = item["prompt"]
            ids = lens_model.encode(prompt, max_length=max_seq_len)
            n_tokens = int(ids.shape[1])
            if n_tokens >= max_seq_len:
                raise RankProfileError(
                    f"{slug}/{item['name']}: prompt hit the truncation limit, "
                    "which would move the readout position"
                )
            token_strings = [
                tokenizer.decode([int(t)], clean_up_tokenization_spaces=False)
                for t in ids[0]
            ]
            position = readout_position(slug, token_strings)

            lens_logits, _model_logits, _ = lens.apply(
                lens_model,
                prompt,
                layers=layers,
                positions=[position],
                max_seq_len=max_seq_len,
                use_jacobian=True,
            )

            for intermediate in item["intermediates"]:
                token_ids = single_token_ids(
                    tokenizer, synonym_forms(slug, intermediate)
                )
                if not token_ids:
                    unrankable.append(
                        {
                            "set": slug,
                            "item": item["name"],
                            "intermediate": intermediate,
                            "reason": "no single-token surface form",
                        }
                    )
                    continue

                scored += 1
                pooled_total += 1
                best_rank_any_layer = None
                for layer in layers:
                    row = lens_logits[layer][0]
                    targets = torch.tensor(token_ids, dtype=torch.long)
                    target_logits = row[targets]
                    rank_here = int(
                        (row.unsqueeze(0) > target_logits.unsqueeze(1))
                        .sum(dim=1)
                        .min()
                        .item()
                    )
                    for k in (1, 5, 10):
                        if rank_here < k:
                            hits[k][layer] += 1
                            pooled_hits[k][layer] += 1
                    if best_rank_any_layer is None or rank_here < best_rank_any_layer:
                        best_rank_any_layer = rank_here
                min_rank_over_layers.append(int(best_rank_any_layer))

            del lens_logits

        per_set[slug] = {
            "readout_rule": READOUT_RULE[slug],
            "items": len(items),
            "scored_intermediates": scored,
            "profile": {
                str(k): [
                    {
                        "layer": layer,
                        "readrate": (hits[k][layer] / scored) if scored else 0.0,
                        "hits": hits[k][layer],
                    }
                    for layer in layers
                ]
                for k in (1, 5, 10)
            },
            "pass_at_k": {
                str(k): (
                    sum(1 for r in min_rank_over_layers if r < k)
                    / len(min_rank_over_layers)
                    if min_rank_over_layers
                    else 0.0
                )
                for k in (1, 5, 10)
            },
        }
        print(
            f"  {slug:14} scored={scored:<5} "
            f"pass@1={per_set[slug]['pass_at_k']['1']:.4f}",
            flush=True,
        )

    pooled = {
        str(k): [
            {
                "layer": layer,
                "readrate": (pooled_hits[k][layer] / pooled_total)
                if pooled_total
                else 0.0,
                "hits": pooled_hits[k][layer],
            }
            for layer in layers
        ]
        for k in (1, 5, 10)
    }

    return {
        "layers": layers,
        "per_set": per_set,
        "pooled_profile": pooled,
        "pooled_scored_intermediates": pooled_total,
        "unrankable": unrankable,
        "unrankable_count": len(unrankable),
        "lens_n_prompts": lens.n_prompts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--lens", required=True)
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    import torch

    if torch.cuda.device_count() != 1:
        raise RankProfileError(
            f"exactly one GPU must be visible; saw {torch.cuda.device_count()}"
        )
    gpu_uuid = physical_gpu_uuid_last_twelve()

    from transformers import AutoModelForCausalLM, AutoTokenizer

    import jlens
    from jlens.lens import JacobianLens

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir,
        dtype=torch.bfloat16,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    lens_model = jlens.from_hf(model, tokenizer, force_bos=True)
    lens = JacobianLens.load(args.lens)

    scored_report = score_with_lens(
        lens_model, tokenizer, lens, args.eval_dir, args.max_seq_len, args.limit
    )
    layers = scored_report["layers"]
    pooled = scored_report["pooled_profile"]
    pooled_total = scored_report["pooled_scored_intermediates"]

    report = {
        "schema_version": "study5-eq2-rank-profile-v1",
        "phase": "R-1",
        "role": args.role,
        "model_dir": args.model_dir,
        "lens": args.lens,
        "lens_sha256": sha256_file(Path(args.lens)),
        "method": {
            "source": "anthropics/jacobian-lens data/evaluations/README.md at 581d398",
            "hit_definition": "target token at lens rank 1",
            "readout_path": "jlens.JacobianLens.apply, official, not reimplemented",
            "positions_per_set_not_unified": True,
            "order_ops_synonym_expansion_is_a_reconstruction": (
                "the README states the RULE (numbers to digit and word forms, "
                "operations to symbol and word forms) but does not publish the "
                "explicit lists; the expansion used here is recorded in the tool "
                "and is a reconstruction of that stated rule"
            ),
            "single_token_synonyms_only": True,
            "scoring_shared_with_the_null": (
                "the null profiles run through this same score_with_lens "
                "function, so the two measurements cannot drift apart"
            ),
        },
        "gpu_index_in_container": 0,
        "gpu_uuid_last_twelve": gpu_uuid,
        "claim_ceiling": "A rank profile. It licenses no claim of any kind.",
    }
    report.update(scored_report)
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    print(f"\npooled scored intermediates: {pooled_total}")
    print("layer  pass@1 readrate")
    for entry in pooled["1"]:
        print(f"{entry['layer']:5d}  {entry['readrate']:.4f}")
    print(f"EQ2-CHECK-RANK-PROFILE-{args.role} PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
