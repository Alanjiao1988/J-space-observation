"""P-0 step 1: enumerate the patching units and their null counterparts.

Activation patching is a two-run operation by definition, so the unit of
analysis cannot be an item; it is an ORDERED PAIR of items (donor, recipient).
No text is authored here. Every unit is two prompts that already exist in
`lens-eval-multihop.json`, which is a file EQ2 measured and which this tool
opens read-only.

Admissible units must tokenise to the SAME LENGTH. That is a strong constraint
and it costs frame size, but it is the constraint that keeps absolute positions
identical between donor and recipient. Qwen2.5 applies rotary position
information inside attention rather than storing it in the residual stream, so
transplanting a state from absolute position p to p' would introduce a
positional mismatch that has nothing to do with the question being asked.
Equal length removes that confound instead of arguing about its size.

Positions are then recovered mechanically, never annotated:

  PREFIX   positions strictly before the first differing token. Causal masking
           makes donor and recipient states here IDENTICAL, so patching is a
           guaranteed no-op. This is the literal zero-intervention null and
           simultaneously a harness-integrity check.
  CUE      positions where the two token sequences differ.
  BRIDGE   positions strictly after the last CUE position and strictly before
           the readout position. The tokens here are IDENTICAL in donor and
           recipient.
  READOUT  the position the registered EQ2 rule reads multihop out at, which is
           the final prompt token.

BRIDGE is the site the verdict rests on, and the reason is structural. Its
input tokens are identical in donor and recipient, so a patch there can move
nothing except state the model COMPUTED from the cue and CARRIED forward. A
model that answers by retrieving straight from the cue at the readout position
holds nothing there to move and the measurement returns zero; a model that
computes an intermediate and carries it does not. CUE and READOUT are measured
and reported, but they cannot decide anything: both are strongly positive under
either account, so a criterion resting on them could not fail, which is the
precise defect OD-011 exists to prevent.

This tool performs NO forward passes and imports NO part of `jlens`.

OD-011: failing cases in tests/test_p0_pairs.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

#: The set EQ2 measured, and the only set P-0 draws from.
EVAL_SLUG = "multihop"

#: Transcribed from `rank_profile.READOUT_RULE["multihop"]`. The prompts stop
#: immediately before the answer, so the token preceding `target` IS the final
#: prompt token. Reproduced rather than imported, because importing EQ2's tool
#: would drag `jlens` into P-0's ground truth. The OD-017 audit compares this
#: constant against EQ2's live value.
READOUT_RULE = "token_before_target"

#: Reproduces `jlens.from_hf(..., force_bos=True)` encoding without importing
#: `jlens`: encode with add_special_tokens=False, then prepend exactly one BOS
#: id when the tokenizer defines one.
ADD_SPECIAL_TOKENS = False
FORCE_BOS = True

MAX_SEQ_LEN = 2048

#: Registered site names. Order is fixed so that reports sort identically.
SITES = ("PREFIX", "CUE", "BRIDGE", "READOUT")

#: The site whose curve the verdict is read from.
DECISIVE_SITE = "BRIDGE"

#: Independent unrelated-donor null replicates per unit.
NULL_REPLICATES = 5


class PairBuildError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def normalise(text: str) -> str:
    return text.strip().lower()


def surface_forms(word: str) -> list[str]:
    """Casing and leading-space variants.

    Deliberately the same shape as `rank_profile.synonym_forms` for a set with
    no synonym expansion, so a form judged single-token here is judged
    single-token there too. multihop carries no synonym rule, so nothing is
    expanded.
    """
    forms: list[str] = []
    for variant in (word, word.lower(), word.capitalize()):
        for form in (variant, " " + variant):
            if form not in forms:
                forms.append(form)
    return forms


def single_token_ids(tokenizer, forms: list[str]) -> list[int]:
    ids: list[int] = []
    for form in forms:
        encoded = tokenizer(form, add_special_tokens=False)["input_ids"]
        if len(encoded) == 1 and int(encoded[0]) not in ids:
            ids.append(int(encoded[0]))
    return ids


def encode(tokenizer, prompt: str) -> list[int]:
    ids = tokenizer(
        prompt, add_special_tokens=ADD_SPECIAL_TOKENS, truncation=True,
        max_length=MAX_SEQ_LEN,
    )["input_ids"]
    if FORCE_BOS and tokenizer.bos_token_id is not None:
        if not ids or ids[0] != tokenizer.bos_token_id:
            ids = [int(tokenizer.bos_token_id)] + [int(i) for i in ids]
    return [int(i) for i in ids]


def readout_position(n_tokens: int) -> int:
    if READOUT_RULE != "token_before_target":
        raise PairBuildError(f"unregistered readout rule {READOUT_RULE}")
    return n_tokens - 1


def sites_for(ids_a: list[int], ids_b: list[int]) -> dict[str, list[int]] | None:
    """The four patch sites, or None if this pair cannot support them.

    None rather than an empty site, so an unusable pair is dropped at
    construction time instead of contributing a structural zero to the very
    quantity the verdict is read from.
    """
    if len(ids_a) != len(ids_b):
        return None
    cue = [i for i, (x, y) in enumerate(zip(ids_a, ids_b)) if x != y]
    if not cue:
        return None
    readout = readout_position(len(ids_b))
    if cue[-1] >= readout:
        return None
    bridge = list(range(cue[-1] + 1, readout))
    if not bridge:
        return None
    prefix = list(range(0, cue[0]))
    if not prefix:
        return None
    return {"PREFIX": prefix, "CUE": cue, "BRIDGE": bridge, "READOUT": [readout]}


def prepare_items(tokenizer, items: list[dict]) -> tuple[list[dict], dict]:
    prepared: list[dict] = []
    rejected = {"no_single_token_target": 0, "no_single_token_intermediate": 0}
    for index, item in enumerate(items):
        target = item.get("target")
        intermediates = item.get("intermediates") or []
        target_ids = (
            single_token_ids(tokenizer, surface_forms(target)) if target else []
        )
        if not target_ids:
            rejected["no_single_token_target"] += 1
            continue
        inter_ids: list[int] = []
        for intermediate in intermediates:
            inter_ids.extend(single_token_ids(tokenizer, surface_forms(intermediate)))
        if not inter_ids:
            rejected["no_single_token_intermediate"] += 1
            continue
        prepared.append(
            {
                "index": index,
                "name": item["name"],
                "prompt": item["prompt"],
                "target": target,
                "intermediates": list(intermediates),
                "ids": encode(tokenizer, item["prompt"]),
                "target_token_ids": target_ids,
                "intermediate_token_ids": sorted(set(inter_ids)),
            }
        )
    return prepared, rejected


def compatible(donor: dict, recipient: dict) -> bool:
    """Every registered admissibility rule that is not about alignment."""
    if donor["index"] == recipient["index"]:
        return False
    if normalise(donor["target"]) == normalise(recipient["target"]):
        return False
    if {normalise(x) for x in donor["intermediates"]} & {
        normalise(x) for x in recipient["intermediates"]
    }:
        return False
    if set(donor["target_token_ids"]) & set(recipient["target_token_ids"]):
        return False
    return True


def build(tokenizer, items: list[dict]) -> tuple[list[dict], list[dict], dict]:
    prepared, rejected = prepare_items(tokenizer, items)

    units: list[dict] = []
    for donor in prepared:
        for recipient in prepared:
            if not compatible(donor, recipient):
                continue
            sites = sites_for(donor["ids"], recipient["ids"])
            if sites is None:
                continue
            units.append(
                {
                    "unit_id": f"{donor['name']}->{recipient['name']}",
                    "cluster_id": "|".join(sorted((donor["name"], recipient["name"]))),
                    "donor": donor["name"],
                    "recipient": recipient["name"],
                    "n_tokens": len(donor["ids"]),
                    "sites": sites,
                    "donor_ids": donor["ids"],
                    "recipient_ids": recipient["ids"],
                    "donor_target": donor["target"],
                    "recipient_target": recipient["target"],
                    "donor_target_token_ids": donor["target_token_ids"],
                    "recipient_target_token_ids": recipient["target_token_ids"],
                    "donor_intermediate_token_ids": donor["intermediate_token_ids"],
                    "recipient_intermediate_token_ids": recipient[
                        "intermediate_token_ids"
                    ],
                }
            )
    units.sort(key=lambda unit: unit["unit_id"])

    stats = {
        "items_in_set": len(items),
        "items_admissible": len(prepared),
        "items_rejected": rejected,
        "ordered_units": len(units),
        "unordered_clusters": len({unit["cluster_id"] for unit in units}),
    }
    return units, prepared, stats


def assign_null_donors(
    units: list[dict], prepared: list[dict], seed: int, replicates: int
) -> dict:
    """For each unit, `replicates` third items C that carry nothing about the donor.

    C must align with the recipient exactly as the donor does, and must be
    incompatible with neither member: its target and its intermediates must
    differ from both the donor's and the recipient's. Scoring a C-patch on the
    DONOR-versus-RECIPIENT contrast then has no route to a systematic effect,
    which is what makes it a null rather than a weak signal - the mistake EQ2
    recorded when a null carrying a small real signal produced a band.
    """
    by_name = {item["name"]: item for item in prepared}
    assignment: dict[str, list[str]] = {}
    exhausted: list[str] = []
    for unit in units:
        donor = by_name[unit["donor"]]
        recipient = by_name[unit["recipient"]]
        pool = sorted(
            candidate["name"]
            for candidate in prepared
            if candidate["name"] not in (donor["name"], recipient["name"])
            and compatible(candidate, recipient)
            and compatible(candidate, donor)
            and sites_for(candidate["ids"], recipient["ids"]) is not None
        )
        if not pool:
            exhausted.append(unit["unit_id"])
            assignment[unit["unit_id"]] = []
            continue
        rng = random.Random(f"{seed}:{unit['unit_id']}")
        assignment[unit["unit_id"]] = [
            pool[rng.randrange(len(pool))] for _ in range(replicates)
        ]
    return {
        "seed": seed,
        "replicates": replicates,
        "assignment": assignment,
        "units_with_no_admissible_third_item": exhausted,
        "rule": (
            "C must align with the recipient, and must be compatible with BOTH "
            "the donor and the recipient under the same admissibility test used "
            "to form units; draws are with replacement from the sorted pool, "
            "seeded per unit id"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--max-units", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    eval_path = Path(args.eval_dir) / f"lens-eval-{EVAL_SLUG}.json"
    raw = eval_path.read_bytes()
    items = json.loads(raw.decode("utf-8"))["items"]

    units, prepared, stats = build(tokenizer, items)

    # Registered: take every admissible unit up to the cap. The cap is a cost
    # control, not a selection rule; when it does not bind, no randomness enters
    # the frame at all and the frame is recoverable from the eval file alone.
    if len(units) > args.max_units:
        rng = random.Random(args.seed)
        clusters = sorted({unit["cluster_id"] for unit in units})
        rng.shuffle(clusters)
        selected: list[dict] = []
        for cluster in clusters:
            members = [unit for unit in units if unit["cluster_id"] == cluster]
            if len(selected) + len(members) > args.max_units:
                continue
            selected.extend(members)
        units = sorted(selected, key=lambda unit: unit["unit_id"])
        frame_is_exhaustive = False
    else:
        frame_is_exhaustive = True

    nulls = assign_null_donors(units, prepared, args.seed, NULL_REPLICATES)

    report = {
        "schema_version": "study5-p0-units-v1",
        "phase": "P-0",
        "eval_set": EVAL_SLUG,
        "eval_file_sha256": sha256_bytes(raw),
        "model_dir": args.model_dir,
        "readout_rule": READOUT_RULE,
        "sites": list(SITES),
        "decisive_site": DECISIVE_SITE,
        "encoding": {
            "add_special_tokens": ADD_SPECIAL_TOKENS,
            "force_bos": FORCE_BOS,
            "max_seq_len": MAX_SEQ_LEN,
            "jlens_imported": False,
        },
        "admissibility_rules": [
            "both members tokenise to the same length",
            "the token sequences differ in at least one position",
            "targets differ after case and whitespace normalisation",
            "the two targets share no single-token surface form",
            "the intermediate sets are disjoint after normalisation",
            "at least one single-token surface form exists for each target",
            "at least one single-token surface form exists for each intermediate",
            "the last differing position is strictly before the readout position",
            "BRIDGE is non-empty",
            "PREFIX is non-empty",
        ],
        "frame": {
            "max_units": args.max_units,
            "seed": args.seed,
            "frame_is_exhaustive": frame_is_exhaustive,
            "both_directions_retained": True,
            "why_both_directions": (
                "the two directions of one unordered pair are correlated, so "
                "they are kept together in a CLUSTER and the bootstrap resamples "
                "clusters rather than units; that uses the whole frame without "
                "pretending the two observations are independent"
            ),
        },
        "statistics": stats,
        "n_units": len(units),
        "n_clusters": len({unit["cluster_id"] for unit in units}),
        "units": units,
        "null_donors": nulls,
        "claim_ceiling": "A sampling frame. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(json.dumps(stats, indent=1))
    print(
        f"units={len(units)} clusters={report['n_clusters']} "
        f"exhaustive={frame_is_exhaustive}"
    )
    for site in SITES:
        sizes = [len(unit["sites"][site]) for unit in units]
        if sizes:
            print(
                f"  {site:8} positions/unit min={min(sizes)} max={max(sizes)} "
                f"mean={sum(sizes)/len(sizes):.2f}"
            )
    print(
        "  units with no admissible third item: "
        f"{len(nulls['units_with_no_admissible_third_item'])}"
    )
    print("P0-CHECK-UNITS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
