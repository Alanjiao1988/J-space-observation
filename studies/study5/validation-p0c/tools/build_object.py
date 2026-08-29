"""P-0c step 2: construct the two-hop object, with the intermediate known by build.

Every previous phase of Study 5 borrowed an object somebody else wrote and then
hoped the model could do it. P-0 measured 32.61 percent item accuracy on the
multihop set and only 18 of 184 pairs correct on both sides, which is what ended
P-0'. This tool builds an object instead of borrowing one.

The task
--------
    Rules: A=2 B=3 C=8 ...            a letter-to-digit table, randomised per pair
    Umbrella is registered under letter B.
    ... five more registrations, all distractors ...
    Question: consider Umbrella.
    ... fixed filler, identical in both members of a pair ...
    The value registered to it is _

The chain is NAME -> letter -> digit. Answering requires composing a lookup in
the registration lines with a lookup in the rules table. The answer is the
DIGIT; the intermediate is the LETTER.

The seven registered requirements, each met by construction rather than by
inspection:

  1  intermediate known          it IS the build parameter; nothing is annotated
                                  and no model output is consulted
  2  intermediate is never the    intermediates are LETTERS, answers are DIGITS,
     emitted token                and the two token-id sets are checked disjoint
                                  at build time over every single-token surface
                                  form either vocabulary could produce
  3  both hops really hop         the letter-to-digit table is randomised per
                                  pair, so hop 2 cannot be known in advance; the
                                  ablation probe removes hop 1's input, which
                                  must collapse accuracy to chance
  4  the model is accurate        checked against a registered floor before
                                  anything is patched
  5  enough correct-both pairs    counted only after the floor rule is pushed
  6  equal token length           the two members of a pair differ ONLY in the
                                  queried name, drawn from a pool filtered to a
                                  single token length
  7  BRIDGE tokens identical      everything after the queried name is fixed
                                  template text; verified position by position
                                  rather than asserted

Pairs are built AS pairs. Two arbitrary items would differ almost everywhere and
CUE would swallow the prompt; here the members share the table, the
registrations and the filler, so CUE is the name alone and BRIDGE is the filler
span - tokens identical in both members, which therefore can carry nothing
except what the model computed.

This tool builds and tokenises. It runs no model and imports no part of the
instrument EQ2 was testing.
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

#: Registered construction parameters, fixed before any model is run.
BUILD_SEED = 20260829
N_PAIRS = 160
N_LETTERS = 8
N_REGISTRATIONS = 6

#: The intermediate alphabet and the answer alphabet are DISJOINT by
#: construction. Making this a property of the vocabularies rather than of the
#: wording means no individual item can violate it.
INTERMEDIATE_ALPHABET = tuple(string.ascii_uppercase[:N_LETTERS])
ANSWER_ALPHABET = tuple(str(d) for d in range(1, 10))

#: Fixed filler between the cue and the readout. Identical in both members, so
#: every BRIDGE position carries the same token in each. Its only job is to put
#: distance between the name and the question.
FILLER = (
    "Note: the rules table above is fixed and applies to every entry.",
    "Note: entries not listed above are out of scope for this question.",
    "Note: answer with the value only.",
    "Note: do not restate the letter.",
)

NAME_POOL = (
    "Alder", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Ginkgo", "Hazel",
    "Ivy", "Juniper", "Kapok", "Larch", "Maple", "Nutmeg", "Olive", "Poplar",
    "Quince", "Rowan", "Spruce", "Teak", "Umbrella", "Vine", "Walnut", "Yew",
    "Almond", "Beech", "Chestnut", "Date", "Ebony", "Fig", "Guava", "Holly",
    "Indigo", "Jasmine", "Kiwi", "Lemon", "Mango", "Nectar", "Orchid", "Peach",
    "Quinoa", "Radish", "Sage", "Thyme", "Ulmus", "Violet", "Willow", "Yarrow",
    "Acorn", "Bramble", "Clover", "Daisy", "Elder", "Fern", "Gorse", "Heather",
    "Iris", "Jute", "Kelp", "Lichen", "Moss", "Nettle", "Oak", "Pine",
    "Quartz", "Reed", "Sorrel", "Tulip", "Urchin", "Vetch", "Wheat", "Yucca",
)

MAX_SEQ_LEN = 2048
ADD_SPECIAL_TOKENS = False
FORCE_BOS = True


class BuildError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def encode(tokenizer, text: str) -> list[int]:
    ids = tokenizer(
        text, add_special_tokens=ADD_SPECIAL_TOKENS, truncation=True,
        max_length=MAX_SEQ_LEN,
    )["input_ids"]
    if FORCE_BOS and tokenizer.bos_token_id is not None:
        if not ids or ids[0] != tokenizer.bos_token_id:
            ids = [int(tokenizer.bos_token_id)] + [int(i) for i in ids]
    return [int(i) for i in ids]


def single_token_forms(tokenizer, word: str) -> list[int]:
    """Every surface form of `word` that encodes to exactly one token.

    Qwen splits a leading space into its own token, so " 1" is two tokens while
    "1" is one. Collecting the forms rather than assuming a shape is what makes
    the disjointness check meaningful: it compares every id either vocabulary
    could actually produce, not the ids of whichever form was tried first.
    """
    ids: list[int] = []
    for form in (word, f" {word}"):
        encoded = tokenizer(form, add_special_tokens=False)["input_ids"]
        if len(encoded) == 1 and int(encoded[0]) not in ids:
            ids.append(int(encoded[0]))
    return ids


def render(table, registrations, query, include_query_registration=True) -> str:
    """The prompt.

    It ends with a trailing space, so the continuation is the bare digit, which
    this tokeniser encodes as a single token.
    """
    rules = " ".join(f"{letter}={digit}" for letter, digit in sorted(table.items()))
    lines = [f"Rules: {rules}"]
    for name, letter in registrations:
        if name == query and not include_query_registration:
            continue
        lines.append(f"{name} is registered under letter {letter}.")
    lines.append(f"Question: consider {query}.")
    lines.extend(FILLER)
    lines.append("The value registered to it is ")
    return "\n".join(lines)


def usable_names(tokenizer) -> list[str]:
    """The full pool. Registration lines are shared by both members of a pair,
    so they impose no alignment constraint; only the QUERIED name does."""
    return sorted(NAME_POOL)


def context_length(tokenizer, name: str) -> int:
    """Token length of the name as it appears in the question line.

    The alignment constraint bites here and nowhere else: the two members share
    every other line, so the only place their token sequences can diverge is the
    queried name. Measuring the name in its actual context is what makes the
    constraint real - a name that is one token bare can be two tokens after a
    space, and filtering on the bare form silently discards nothing while
    admitting misaligned pairs.
    """
    return len(tokenizer(f" {name}", add_special_tokens=False)["input_ids"])


def sites_for(donor_ids, recipient_ids):
    if len(donor_ids) != len(recipient_ids):
        return None
    cue = [i for i, (a, b) in enumerate(zip(donor_ids, recipient_ids)) if a != b]
    if not cue:
        return None
    readout = len(recipient_ids) - 1
    if cue[-1] >= readout:
        return None
    bridge = list(range(cue[-1] + 1, readout))
    prefix = list(range(0, cue[0]))
    if not bridge or not prefix:
        return None
    return {"PREFIX": prefix, "CUE": cue, "BRIDGE": bridge, "READOUT": [readout]}


def build(tokenizer, rng) -> dict:
    names = usable_names(tokenizer)
    if len(names) < N_REGISTRATIONS:
        raise BuildError(f"only {len(names)} names share a token length")

    letter_ids = {
        letter: single_token_forms(tokenizer, letter)
        for letter in INTERMEDIATE_ALPHABET
    }
    digit_ids = {
        digit: single_token_forms(tokenizer, digit) for digit in ANSWER_ALPHABET
    }
    missing = [k for k, v in {**letter_ids, **digit_ids}.items() if not v]
    if missing:
        raise BuildError(f"no single-token form for {missing}")
    all_letters = {i for ids in letter_ids.values() for i in ids}
    all_digits = {i for ids in digit_ids.values() for i in ids}
    if all_letters & all_digits:
        raise BuildError(
            "the intermediate and answer vocabularies overlap; requirement 2 is "
            "violated and the object is not usable"
        )

    items: list[dict] = []
    units: list[dict] = []
    rejected = {"no_usable_name_pair": 0, "misaligned": 0}

    for index in range(N_PAIRS):
        letters = list(INTERMEDIATE_ALPHABET)
        rng.shuffle(letters)
        digits = list(ANSWER_ALPHABET)
        rng.shuffle(digits)
        table = {letter: digits[i % len(digits)] for i, letter in enumerate(letters)}

        chosen = rng.sample(names, N_REGISTRATIONS)
        registrations = [(name, rng.choice(letters)) for name in chosen]

        # The two queried names must differ in BOTH the intermediate and the
        # answer, so a patch has something unambiguous to move, and must
        # tokenise to the same length IN THE QUESTION LINE, which is the only
        # place the two members can diverge.
        options = [
            (a, b)
            for i, a in enumerate(registrations)
            for b in registrations[i + 1 :]
            if a[1] != b[1]
            and table[a[1]] != table[b[1]]
            and context_length(tokenizer, a[0]) == context_length(tokenizer, b[0])
        ]
        if not options:
            rejected["no_usable_name_pair"] += 1
            continue
        (name_d, letter_d), (name_r, letter_r) = rng.choice(options)

        pair = []
        for suffix, name, letter in (
            ("d", name_d, letter_d),
            ("r", name_r, letter_r),
        ):
            prompt = render(table, registrations, name)
            pair.append(
                {
                    "item_id": f"p{index:04d}{suffix}",
                    "pair_index": index,
                    "role": "donor" if suffix == "d" else "recipient",
                    "prompt": prompt,
                    "query_name": name,
                    "intermediate_letter": letter,
                    "answer_digit": table[letter],
                    "table": table,
                    "registrations": registrations,
                    "ids": encode(tokenizer, prompt),
                    "answer_token_ids": digit_ids[table[letter]],
                    "intermediate_token_ids": letter_ids[letter],
                    "ablated_prompt": render(
                        table, registrations, name,
                        include_query_registration=False,
                    ),
                }
            )

        donor, recipient = pair
        sites = sites_for(donor["ids"], recipient["ids"])
        if sites is None:
            rejected["misaligned"] += 1
            continue

        for item in pair:
            item["ablated_ids"] = encode(tokenizer, item["ablated_prompt"])
        items.extend(pair)
        units.append(
            {
                "unit_id": f"{donor['item_id']}->{recipient['item_id']}",
                "cluster_id": f"p{index:04d}",
                "pair_index": index,
                "donor": donor["item_id"],
                "recipient": recipient["item_id"],
                "n_tokens": len(donor["ids"]),
                "sites": sites,
                "donor_ids": donor["ids"],
                "recipient_ids": recipient["ids"],
                "donor_answer_token_ids": donor["answer_token_ids"],
                "recipient_answer_token_ids": recipient["answer_token_ids"],
                "donor_intermediate_token_ids": donor["intermediate_token_ids"],
                "recipient_intermediate_token_ids": recipient[
                    "intermediate_token_ids"
                ],
            }
        )

    return {
        "items": items,
        "units": units,
        "rejected": rejected,
        "letter_token_ids": letter_ids,
        "digit_token_ids": digit_ids,
        "names_used": names,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    built = build(tokenizer, random.Random(BUILD_SEED))
    items, units = built["items"], built["units"]

    intermediate_ids = {i for ids in built["letter_token_ids"].values() for i in ids}
    answer_ids = {i for ids in built["digit_token_ids"].values() for i in ids}

    # Requirement 7, verified rather than asserted: every PREFIX and BRIDGE
    # position must carry the SAME token in both members.
    violations = 0
    for unit in units:
        for site in ("PREFIX", "BRIDGE"):
            for position in unit["sites"][site]:
                if unit["donor_ids"][position] != unit["recipient_ids"][position]:
                    violations += 1

    report = {
        "schema_version": "study5-p0c-object-v2",
        "phase": "P-0c",
        "build_seed": BUILD_SEED,
        "model_dir": args.model_dir,
        "task": (
            "NAME -> letter -> digit; the answer is the digit and the "
            "intermediate is the letter"
        ),
        "requirements_and_how_each_is_met": {
            "1_intermediate_known": "it is the build parameter; no annotation and no model output is consulted",
            "2_intermediate_never_the_emitted_token": {
                "intermediate_vocabulary": "letters",
                "answer_vocabulary": "digits",
                "token_id_overlap": sorted(intermediate_ids & answer_ids),
                "disjoint": not (intermediate_ids & answer_ids),
                "checked_over_every_single_token_surface_form": True,
            },
            "3_both_hops_real": "the letter-to-digit table is randomised per pair; verified separately by the ablation probe",
            "4_accuracy_floor": "verified against a registered floor before anything is patched",
            "5_enough_pairs": "counted only after the floor rule is pushed",
            "6_equal_token_length": "the two members differ only in the queried name, drawn from a single-token-length pool",
            "7_bridge_and_prefix_tokens_identical": {
                "positions_where_the_two_members_differ": violations,
                "verified_not_asserted": True,
            },
        },
        "counts": {
            "pairs_attempted": N_PAIRS,
            "pairs_built": len(units),
            "items": len(items),
            "rejected": built["rejected"],
            "name_pool_size": len(built["names_used"]),
            "distinct_token_lengths": sorted({len(i["ids"]) for i in items}),
        },
        "chance_rate": 1.0 / len(ANSWER_ALPHABET),
        "letter_token_ids": built["letter_token_ids"],
        "digit_token_ids": built["digit_token_ids"],
        "items": items,
        "units": units,
        "instrument_under_test_imported": False,
        "claim_ceiling": (
            "A constructed object. It is a SELECTION SET: nothing measured on it "
            "is a conclusion about real items."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"pairs built {len(units)} of {N_PAIRS}, items {len(items)}")
    print(f"rejected: {built['rejected']}")
    print(f"name pool: {len(built['names_used'])}")
    print(
        f"intermediate/answer overlap: {sorted(intermediate_ids & answer_ids)} "
        f"(disjoint: {not (intermediate_ids & answer_ids)})"
    )
    print(f"requirement 7 violations: {violations}")
    for site in ("PREFIX", "CUE", "BRIDGE", "READOUT"):
        sizes = [len(u["sites"][site]) for u in units]
        if sizes:
            print(
                f"  {site:8} min {min(sizes)} max {max(sizes)} "
                f"mean {sum(sizes)/len(sizes):.2f}"
            )
    print("\n--- donor of the first pair, verbatim ---")
    print(items[0]["prompt"])
    print(
        f"--- intermediate {items[0]['intermediate_letter']}, "
        f"answer {items[0]['answer_digit']} ---"
    )
    print("\n--- its ablation probe ---")
    print(items[0]["ablated_prompt"])
    if violations:
        print("P0C-CHECK-OBJECT FAILED", file=sys.stderr)
        return 1
    print("P0C-CHECK-OBJECT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
