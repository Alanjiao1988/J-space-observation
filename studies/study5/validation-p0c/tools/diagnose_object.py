"""P-0c diagnostic: where the accuracy went, on an object that did not establish.

This tool CHANGES NOTHING. It does not re-decide, it does not rebuild the object,
it does not touch a threshold, and its output is consumed by nothing. The
registered determination is OBJECT_NOT_ESTABLISHED and it stands.

Motivation asymmetry, disclosed as the standing rule requires: this file would
not have been written had the accuracy floor been met. Its admissibility rests
on the fact that it cannot change the outcome - the registered criterion has
already run, its determination is committed, and the pre-registration forbids
weakening a requirement or adjusting the object to pass.

The question it answers is the one the operator needs in order to decide what to
do next, and it is a question about WHERE a two-hop chain breaks:

  hop 1   NAME -> letter, read from the registration lines
  hop 2   letter -> digit, read from the rules table

An error whose top-1 is the digit belonging to a DIFFERENT letter in the same
table is a hop-1 error: the second lookup was performed correctly on the wrong
key. An error whose top-1 is not a digit in the table at all is a different kind
of failure. An error whose top-1 is not a digit at all is a formatting failure
and says nothing about the chain.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--proof", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
    items = obj["items"]
    digit_ids = obj["digit_token_ids"]
    letter_ids = obj["letter_token_ids"]

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()

    by_length: dict[int, list[int]] = {}
    for index, item in enumerate(items):
        by_length.setdefault(len(item["ids"]), []).append(index)

    top1: dict[int, int] = {}
    for length, indices in sorted(by_length.items()):
        for start in range(0, len(indices), args.batch):
            chunk = indices[start : start + args.batch]
            batch = torch.tensor(
                [items[i]["ids"] for i in chunk], dtype=torch.long, device="cuda:0"
            )
            with torch.no_grad():
                logits = model(input_ids=batch).logits[:, -1, :]
            for row, index in enumerate(chunk):
                top1[index] = int(logits[row].argmax().item())

    id_to_digit = {i: d for d, ids in digit_ids.items() for i in ids}
    all_letter_ids = {i for ids in letter_ids.values() for i in ids}

    buckets = {
        "correct": 0,
        "hop1_error_digit_of_another_letter_in_this_table": 0,
        "digit_not_in_this_table": 0,
        "emitted_a_letter": 0,
        "not_a_digit_at_all": 0,
    }
    examples: list[dict] = []
    per_role = {"donor": {"n": 0, "correct": 0}, "recipient": {"n": 0, "correct": 0}}
    by_registration_position = {}

    for index, item in enumerate(items):
        predicted = top1[index]
        answer_ids = set(item["answer_token_ids"])
        table = item["table"]
        position = [n for n, _ in item["registrations"]].index(item["query_name"])
        slot = by_registration_position.setdefault(
            position, {"n": 0, "correct": 0}
        )
        slot["n"] += 1
        role = per_role[item["role"]]
        role["n"] += 1

        if predicted in answer_ids:
            buckets["correct"] += 1
            slot["correct"] += 1
            role["correct"] += 1
            continue

        digit = id_to_digit.get(predicted)
        if digit is not None and digit in set(table.values()):
            buckets["hop1_error_digit_of_another_letter_in_this_table"] += 1
            kind = "hop1_error"
        elif digit is not None:
            buckets["digit_not_in_this_table"] += 1
            kind = "digit_not_in_table"
        elif predicted in all_letter_ids:
            buckets["emitted_a_letter"] += 1
            kind = "emitted_a_letter"
        else:
            buckets["not_a_digit_at_all"] += 1
            kind = "not_a_digit"

        if len(examples) < 12:
            examples.append(
                {
                    "item_id": item["item_id"],
                    "query_name": item["query_name"],
                    "intermediate_letter": item["intermediate_letter"],
                    "answer_digit": item["answer_digit"],
                    "predicted_token": tokenizer.decode([predicted]),
                    "kind": kind,
                    "registration_position": position,
                }
            )

    n = len(items)
    errors = n - buckets["correct"]
    report = {
        "schema_version": "study5-p0c-diagnostic-v1",
        "phase": "P-0c",
        "status": "DIAGNOSTIC ONLY. No criterion is changed, no determination is recomputed, and the object is not rebuilt.",
        "motivation_asymmetry": (
            "this file would not have been written had the accuracy floor been "
            "met; it is admissible because it cannot change the outcome, which "
            "was produced by the registered criterion and is already committed"
        ),
        "the_determination_it_cannot_change": {
            "determination": proof["determination"],
            "accuracy": proof["requirement_4_accuracy"]["observed"],
            "floor": proof["requirement_4_accuracy"]["floor"],
            "ablated_accuracy": proof["requirement_3_anti_retrieval"][
                "observed_ablated_accuracy"
            ],
            "chance": proof["requirement_3_anti_retrieval"]["chance"],
        },
        "what_passed_and_is_worth_recording": {
            "the_anti_retrieval_proof": "PASSED, and not narrowly",
            "ablated_accuracy": proof["requirement_3_anti_retrieval"][
                "observed_ablated_accuracy"
            ],
            "chance_rate": proof["requirement_3_anti_retrieval"]["chance"],
            "reading": (
                "removing the first hop's input drops the model to essentially "
                "exactly chance, so the task genuinely requires composing two "
                "lookups and cannot be answered by retrieval. The two-hop "
                "STRUCTURE is established even though the object as a whole is "
                "not, because the object also requires an accuracy the model did "
                "not reach"
            ),
            "requirement_2_holds_behaviourally_as_well_as_on_paper": {
                "top1_is_the_intermediate_letter": proof[
                    "reported_only_no_criterion_adjusted"
                ]["top1_is_the_intermediate_letter"],
                "of": n,
            }
        },
        "where_the_errors_fall": {
            "counts": buckets,
            "errors_total": errors,
            "fractions_of_errors": {
                k: (v / errors if errors else 0.0)
                for k, v in buckets.items()
                if k != "correct"
            },
            "how_to_read_it": {
                "hop1_error_digit_of_another_letter_in_this_table": "the second lookup was performed correctly on the WRONG key, so hop 2 works and hop 1 is where it breaks",
                "digit_not_in_this_table": "a digit that no letter in this table maps to",
                "emitted_a_letter": "the model emitted the intermediate rather than the answer",
                "not_a_digit_at_all": "a formatting failure, which says nothing about the chain"
            },
        },
        "accuracy_by_role": {
            role: {"n": v["n"], "correct": v["correct"],
                   "accuracy": v["correct"] / v["n"] if v["n"] else 0.0}
            for role, v in per_role.items()
        },
        "accuracy_by_registration_line_position": {
            str(position): {
                "n": v["n"],
                "correct": v["correct"],
                "accuracy": v["correct"] / v["n"] if v["n"] else 0.0,
            }
            for position, v in sorted(by_registration_position.items())
        },
        "example_errors": examples,
        "what_this_does_not_authorise": [
            "lowering the accuracy floor, which would move the registered text toward the data",
            "rebuilding the object to make it pass, which is the same move by another route",
            "proceeding to any estimand work",
            "any claim about real items, the J-lens, the paper, or T"
        ],
        "claim_ceiling": (
            "A diagnostic record for a halted phase. It licenses no claim of any "
            "kind."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"determination (unchanged): {proof['determination']}")
    print(f"errors: {errors} of {n}")
    for key, value in buckets.items():
        if key == "correct":
            continue
        share = value / errors if errors else 0.0
        print(f"  {key:52} {value:4}  ({share:.3f} of errors)")
    print("accuracy by registration-line position:")
    for position, stats in sorted(by_registration_position.items()):
        print(
            f"  position {position}: {stats['correct']:3}/{stats['n']:3} = "
            f"{stats['correct']/stats['n']:.4f}"
        )
    print("P0C-DIAGNOSTIC WRITTEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
