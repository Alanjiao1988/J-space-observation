"""P-0c step 2b: prove the object, or fail to.

Two registered requirements are settled here, both on CLEAN runs and both
before anything is patched:

  requirement 3  the ablation probe removes the FIRST hop's input while leaving
                 the second hop's clue intact. If the model still answers, it is
                 retrieving rather than composing, and the object is not a
                 two-hop object.
  requirement 4  the model must answer the full items above the registered
                 accuracy floor. P-0 measured 32.61 percent on a borrowed set
                 and 18 usable pairs, which is what ended P-0'; an object the
                 model cannot do makes the question about its intermediate
                 close to moot.

Both criteria and both thresholds are read from the pushed registration rather
than hard-coded, so this tool cannot silently disagree with the text it applies.

It also records, per item, whether the model's top-1 is the ANSWER digit and
whether it is the INTERMEDIATE letter. The second is reported only: if the model
were emitting the letter, requirement 2 would be satisfied on paper while the
object behaved differently in practice, and that is worth seeing rather than
assuming away.

No patching. No estimand. Nothing from the instrument EQ2 was testing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


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


def batched_last_logits(model, sequences, batch_size, torch):
    """Last-position logits for a list of equal-or-unequal length sequences.

    Sequences are grouped by length so no padding is needed; padding would
    introduce attention-mask handling that has nothing to do with the question
    and could differ between the full and ablated runs.
    """
    results: dict[int, "torch.Tensor"] = {}
    by_length: dict[int, list[int]] = {}
    for index, ids in enumerate(sequences):
        by_length.setdefault(len(ids), []).append(index)

    for length, indices in sorted(by_length.items()):
        for start in range(0, len(indices), batch_size):
            chunk = indices[start : start + batch_size]
            batch = torch.tensor(
                [sequences[i] for i in chunk], dtype=torch.long, device="cuda:0"
            )
            with torch.no_grad():
                logits = model(input_ids=batch).logits[:, -1, :].float()
            for row, index in enumerate(chunk):
                results[index] = logits[row].cpu()
    return [results[i] for i in range(len(sequences))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.time()
    reg = json.loads(Path(args.registration).read_text(encoding="utf-8"))
    requirements = reg["1_the_object"]["the_seven_requirements"]
    accuracy_floor = float(requirements["4_model_accuracy"]["floor"])
    ablation = reg["2_the_anti_retrieval_proof"]
    chance = float(ablation["chance_rate"])
    ablation_ceiling = float(ablation["ceiling"])
    required_drop = 0.50

    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    items = obj["items"]

    AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=False, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()

    full = batched_last_logits(model, [it["ids"] for it in items], args.batch, torch)
    ablated = batched_last_logits(
        model, [it["ablated_ids"] for it in items], args.batch, torch
    )

    per_item = []
    n_correct = 0
    n_ablated_correct = 0
    n_top1_is_letter = 0
    for item, row_full, row_ablated in zip(items, full, ablated):
        answer_ids = set(item["answer_token_ids"])
        letter_ids = set(item["intermediate_token_ids"])
        top1_full = int(row_full.argmax().item())
        top1_ablated = int(row_ablated.argmax().item())
        correct = top1_full in answer_ids
        ablated_correct = top1_ablated in answer_ids
        is_letter = top1_full in letter_ids
        n_correct += correct
        n_ablated_correct += ablated_correct
        n_top1_is_letter += is_letter
        per_item.append(
            {
                "item_id": item["item_id"],
                "pair_index": item["pair_index"],
                "role": item["role"],
                "correct": bool(correct),
                "ablated_correct": bool(ablated_correct),
                "top1_is_the_intermediate_letter": bool(is_letter),
            }
        )

    n = len(items)
    accuracy = n_correct / n
    ablated_accuracy = n_ablated_correct / n
    drop = accuracy - ablated_accuracy

    accuracy_ok = accuracy >= accuracy_floor
    ablation_ok = ablated_accuracy <= ablation_ceiling
    drop_ok = drop > required_drop
    established = accuracy_ok and ablation_ok and drop_ok

    report = {
        "schema_version": "study5-p0c-object-proof-v1",
        "phase": "P-0c",
        "registration_applied": args.registration,
        "registration_sha256": sha256_file(Path(args.registration)),
        "object_sha256": sha256_file(Path(args.object)),
        "model_dir": args.model_dir,
        "dtype": "bfloat16",
        "measured_on_clean_runs_only": True,
        "nothing_was_patched": True,
        "n_items": n,

        "requirement_4_accuracy": {
            "observed": accuracy,
            "floor": accuracy_floor,
            "chance": chance,
            "passed": accuracy_ok,
        },
        "requirement_3_anti_retrieval": {
            "probe": ablation["probe"],
            "why_it_is_the_right_probe": ablation["why_it_is_the_right_probe"],
            "observed_ablated_accuracy": ablated_accuracy,
            "chance": chance,
            "ceiling": ablation_ceiling,
            "at_or_below_chance": ablation_ok,
            "drop": drop,
            "required_drop": required_drop,
            "drop_is_unambiguous": drop_ok,
            "passed": ablation_ok and drop_ok,
        },
        "reported_only_no_criterion_adjusted": {
            "top1_is_the_intermediate_letter": n_top1_is_letter,
            "fraction": n_top1_is_letter / n,
            "why_it_is_recorded": (
                "requirement 2 is a statement about vocabularies; this is a "
                "statement about behaviour. If the model were emitting the "
                "letter, the requirement would hold on paper while the object "
                "behaved differently in practice"
            ),
        },

        "determination": "OBJECT_ESTABLISHED" if established else "OBJECT_NOT_ESTABLISHED",
        "verbatim": (
            reg["3_conclusion_wordings_fixed_before_any_measurement"][
                "OBJECT_ESTABLISHED" if established else "OBJECT_NOT_ESTABLISHED"
            ]["verbatim"]
        ),
        "per_item": per_item,
        "wall_seconds": round(time.time() - started, 3),
        "claim_ceiling": (
            "A property of a constructed object. It is a SELECTION SET and "
            "nothing measured on it is a conclusion about real items."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"items                     : {n}")
    print(f"accuracy                  : {accuracy:.4f}  floor {accuracy_floor}  -> {'PASS' if accuracy_ok else 'FAIL'}")
    print(f"ablated accuracy          : {ablated_accuracy:.4f}  ceiling {ablation_ceiling:.4f}  chance {chance:.4f}  -> {'PASS' if ablation_ok else 'FAIL'}")
    print(f"drop                      : {drop:.4f}  required > {required_drop}  -> {'PASS' if drop_ok else 'FAIL'}")
    print(f"top1 is the letter (reported only): {n_top1_is_letter}/{n} = {n_top1_is_letter/n:.4f}")
    print(f"determination             : {report['determination']}")
    if not established:
        print("P0C-CHECK-OBJECT-PROOF FAILED", file=sys.stderr)
        return 1
    print("P0C-CHECK-OBJECT-PROOF PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
