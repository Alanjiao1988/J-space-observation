"""R-1b step B: does the intermediate coincide with the model's own output?

A late band raises a specific confounder: what the lens reads at layers 21-26
may not be an intermediate held in a workspace, but the answer about to be
emitted. If an item's labelled `intermediate` is also the token the model
actually predicts at the readout position, then reading it late is unremarkable.

Two things are counted, and they answer different questions:

  1. intermediate == target, purely from the published item text. `target` is
     the continuation the item is built around. This needs no model at all.
  2. intermediate == the model's own argmax at the readout position. This is
     what actually matters, because it is the model's output, not the label.

Per the instruction this is REPORTED ONLY. No criterion is adjusted from it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SETS = ("association", "multihop", "multilingual", "order-ops", "poetry", "typo")
MAX_SEQ_LEN = 2048


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def normalise(text: str) -> str:
    return text.strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--model-dir")
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--text-only", action="store_true")
    args = parser.parse_args()

    # ---- part 1: text-only, no model required -----------------------------
    text_stats = {}
    total_items = 0
    total_intermediates = 0
    total_equal_to_target = 0
    items_with_target = 0

    for slug in SETS:
        items = json.loads(
            (Path(args.eval_dir) / f"lens-eval-{slug}.json").read_text(encoding="utf-8")
        )["items"]
        n_int = 0
        n_eq = 0
        has_target = 0
        for item in items:
            target = item.get("target")
            if target is not None:
                has_target += 1
            for intermediate in item["intermediates"]:
                n_int += 1
                if target is not None and normalise(intermediate) == normalise(target):
                    n_eq += 1
        text_stats[slug] = {
            "items": len(items),
            "items_with_a_target_field": has_target,
            "intermediates": n_int,
            "intermediate_equals_target": n_eq,
            "fraction": (n_eq / n_int) if n_int else 0.0,
        }
        total_items += len(items)
        total_intermediates += n_int
        total_equal_to_target += n_eq
        items_with_target += has_target
        print(
            f"  {slug:14} items={len(items):<4} intermediates={n_int:<5} "
            f"== target: {n_eq}  ({text_stats[slug]['fraction']:.4f})"
        )

    report = {
        "schema_version": "study5-eq2-item-construction-v1",
        "phase": "R-1b",
        "step": "B",
        "purpose": (
            "quantify output-adjacency confounding for the late band; REPORTED "
            "ONLY, no criterion is adjusted from it"
        ),
        "part_1_text_only": {
            "question": "is the labelled intermediate literally the item's own target continuation?",
            "per_set": text_stats,
            "total_items": total_items,
            "total_intermediates": total_intermediates,
            "total_intermediate_equals_target": total_equal_to_target,
            "overall_fraction": (
                total_equal_to_target / total_intermediates if total_intermediates else 0.0
            ),
            "note": (
                "association, poetry and typo publish no target field, so for those "
                "sets this question is answered by part 2 only"
            ),
        },
    }

    # ---- part 2: against the model's own prediction ------------------------
    if not args.text_only:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        import jlens
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ic_rank", Path(__file__).resolve().parent / "rank_profile.py"
        )
        assert spec is not None and spec.loader is not None
        rank = importlib.util.module_from_spec(spec)
        sys.modules["ic_rank"] = rank
        spec.loader.exec_module(rank)

        tokenizer = AutoTokenizer.from_pretrained(
            args.model_dir, trust_remote_code=False, use_fast=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
            attn_implementation="eager",
        )
        model.to("cuda:0")
        model.eval()
        lens_model = jlens.from_hf(model, tokenizer, force_bos=True)

        model_stats = {}
        grand_int = 0
        grand_eq = 0
        for slug in SETS:
            items = json.loads(
                (Path(args.eval_dir) / f"lens-eval-{slug}.json").read_text(encoding="utf-8")
            )["items"]
            n_int = 0
            n_eq = 0
            for item in items:
                ids = lens_model.encode(item["prompt"], max_length=MAX_SEQ_LEN)
                token_strings = [
                    tokenizer.decode([int(t)], clean_up_tokenization_spaces=False)
                    for t in ids[0]
                ]
                position = rank.readout_position(slug, token_strings)
                with torch.no_grad():
                    out = lens_model.forward(ids)
                    hidden = (
                        out.last_hidden_state
                        if hasattr(out, "last_hidden_state")
                        else out[0]
                    )
                    logits = lens_model.unembed(hidden[0, position : position + 1].float())
                top1 = int(logits[0].argmax().item())
                for intermediate in item["intermediates"]:
                    n_int += 1
                    ids_for = rank.single_token_ids(
                        tokenizer, rank.synonym_forms(slug, intermediate)
                    )
                    if top1 in ids_for:
                        n_eq += 1
            model_stats[slug] = {
                "intermediates": n_int,
                "intermediate_is_the_models_own_top1": n_eq,
                "fraction": (n_eq / n_int) if n_int else 0.0,
            }
            grand_int += n_int
            grand_eq += n_eq
            print(
                f"  {slug:14} == model top1: {n_eq}/{n_int}  "
                f"({model_stats[slug]['fraction']:.4f})"
            )

        report["part_2_against_the_models_own_prediction"] = {
            "question": (
                "is the labelled intermediate the token the model itself predicts "
                "at the readout position?"
            ),
            "why_this_is_the_one_that_matters": (
                "if the intermediate IS the model's output, then reading it in the "
                "last quarter of the network is unremarkable and does not evidence a "
                "workspace intermediate"
            ),
            "model": args.model_dir,
            "per_set": model_stats,
            "total_intermediates": grand_int,
            "total_equal": grand_eq,
            "overall_fraction": (grand_eq / grand_int) if grand_int else 0.0,
        }

    report["reported_only_no_criterion_adjusted"] = True
    report["claim_ceiling"] = "An item-construction statistic. It licenses no claim of any kind."
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    p1 = report["part_1_text_only"]["overall_fraction"]
    print(f"\npart 1, intermediate == target      : {p1:.4f}")
    if "part_2_against_the_models_own_prediction" in report:
        p2 = report["part_2_against_the_models_own_prediction"]["overall_fraction"]
        print(f"part 2, intermediate == model top1  : {p2:.4f}")
    print("EQ2-CHECK-ITEM-CONSTRUCTION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
