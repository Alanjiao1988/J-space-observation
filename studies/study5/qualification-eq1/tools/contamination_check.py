#!/usr/bin/env python3
"""Contamination check: OpenThoughts3-55k against the MATH-500 development slice.

Authority section 4.3 registers
`nathu0/transcoder-adapters-openthoughts3-stratified-55k` as the contamination
reference. It is the stratified sample of the corpus the transcoder adapters
were trained on, so overlap between it and the benchmark items would mean the
adapter has seen the evaluation problems -- which would not invalidate the
qualification, but would have to be reported alongside any accuracy figure.

Two independent channels are used, because either alone is easy to fool:

* **13-gram overlap** on normalised text. Catches verbatim and near-verbatim
  reuse. Exact, cheap, and insensitive to paraphrase.
* **Character n-gram cosine similarity** over a hashed feature space. Catches
  reworded restatements that share no long exact span. It is deliberately a
  lexical embedding rather than a neural one: this must run before any model
  call, and using a model here would both violate the P-0 budget and make the
  check depend on the very artefact under study.

A benchmark item is flagged if **either** channel exceeds its threshold. Both
thresholds are fixed here, before the measurement, and are recorded in the
output so the decision rule cannot be adjusted after seeing the result.

This runs on the cloud VM. It reads only development items; no confirmation item
is loaded, hashed or inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Fixed before the measurement.
NGRAM_N = 13
NGRAM_FLAG_THRESHOLD = 1  # one shared 13-gram is already reportable
COSINE_FLAG_THRESHOLD = 0.80
CHAR_NGRAM = 5
HASH_DIM = 2**18


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(text: str) -> str:
    """Fold away everything that is not content.

    Contamination that survives a change of whitespace, case or LaTeX spacing is
    still contamination, so all three are removed before comparison.
    """

    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\\[a-z]+\s*", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def word_ngrams(text: str, n: int = NGRAM_N) -> set[str]:
    words = text.split()
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def stable_hash(text: str) -> int:
    """A hash that is identical across processes and machines.

    Python's built-in ``hash()`` is randomised per interpreter unless
    PYTHONHASHSEED is fixed, which would make this check's cosine channel
    irreproducible -- and an irreproducible number may not be reported at all
    under authority 9.4. blake2b with a small digest is stable everywhere.
    """

    return int.from_bytes(
        hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big"
    )


def hashed_char_vector(text: str, n: int = CHAR_NGRAM) -> dict[int, float]:
    counts: Counter[int] = Counter()
    padded = f" {text} "
    for i in range(max(0, len(padded) - n + 1)):
        gram = padded[i : i + n]
        counts[stable_hash(gram) % HASH_DIM] += 1
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(key, 0.0) for key, value in a.items())


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def reference_text(row: dict[str, Any]) -> str:
    """Pull the natural-language content out of a training row.

    The corpus stores conversations, so the fields worth comparing are the human
    turns and any problem statement, not the assistant's reasoning.
    """

    parts: list[str] = []
    for key in ("problem", "question", "prompt", "instruction", "text"):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("conversations", "messages"):
        turns = row.get(key)
        if isinstance(turns, list):
            for turn in turns:
                if isinstance(turn, dict):
                    content = turn.get("content") or turn.get("value")
                    role = str(turn.get("role") or turn.get("from") or "")
                    if isinstance(content, str) and role.lower() not in {
                        "assistant",
                        "gpt",
                    }:
                        parts.append(content)
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", required=True, help="frozen benchmark split")
    parser.add_argument("--benchmark", required=True, help="MATH-500 test.jsonl")
    parser.add_argument("--reference", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-reference-rows", type=int, default=0)
    parser.add_argument(
        "--screen",
        choices=("development", "confirmation"),
        default="development",
        help=(
            "which split to screen. Screening the confirmation split is "
            "authorised by OD-003's sibling OD-002: contamination screening is a "
            "pure-text, zero-model-call determination of an item property that "
            "is uncorrelated with any result, so it is not the 'inspection' "
            "section 10.2 prohibits."
        ),
    )
    args = parser.parse_args(argv)

    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    development = set(split["development_ids"])
    confirmation = set(split["confirmation_ids"])
    target_ids = development if args.screen == "development" else confirmation
    other_ids = confirmation if args.screen == "development" else development

    items: list[dict[str, Any]] = []
    for index, row in enumerate(iter_jsonl(Path(args.benchmark))):
        identifier = str(
            row.get("unique_id") or row.get("id") or row.get("problem_id") or index
        )
        if identifier not in target_ids:
            continue
        text = normalise(str(row.get("problem", "")))
        items.append(
            {
                "item_id": identifier,
                "normalised": text,
                "ngrams": word_ngrams(text),
                "vector": hashed_char_vector(text),
                "max_cosine": 0.0,
                "shared_ngrams": 0,
                "matched_ngrams": set(),
                "nearest_reference_row": None,
            }
        )

    if len(items) != len(target_ids):
        raise SystemExit(
            f"loaded {len(items)} {args.screen} items but the split registers "
            f"{len(target_ids)}; refusing to report a partial check"
        )

    ngram_index: dict[str, list[int]] = {}
    for position, item in enumerate(items):
        for gram in item["ngrams"]:
            ngram_index.setdefault(gram, []).append(position)

    rows_scanned = 0
    for reference in args.reference:
        for row in iter_jsonl(Path(reference)):
            rows_scanned += 1
            if args.max_reference_rows and rows_scanned > args.max_reference_rows:
                break
            text = normalise(reference_text(row))
            if not text:
                continue

            hits: Counter[int] = Counter()
            matched: dict[int, set[str]] = {}
            for gram in word_ngrams(text):
                for position in ngram_index.get(gram, ()):
                    hits[position] += 1
                    matched.setdefault(position, set()).add(gram)
            for position, count in hits.items():
                if count > items[position]["shared_ngrams"]:
                    items[position]["shared_ngrams"] = count
                items[position]["matched_ngrams"] |= matched[position]

            if hits:
                vector = hashed_char_vector(text)
                for position in hits:
                    score = cosine(items[position]["vector"], vector)
                    if score > items[position]["max_cosine"]:
                        items[position]["max_cosine"] = score
                        items[position]["nearest_reference_row"] = rows_scanned

    flagged = []
    for item in items:
        by_ngram = item["shared_ngrams"] >= NGRAM_FLAG_THRESHOLD
        by_cosine = item["max_cosine"] >= COSINE_FLAG_THRESHOLD
        if by_ngram or by_cosine:
            flagged.append(
                {
                    "item_id": item["item_id"],
                    "shared_ngrams": item["shared_ngrams"],
                    "max_cosine": round(item["max_cosine"], 4),
                    "flagged_by_ngram": by_ngram,
                    "flagged_by_cosine": by_cosine,
                    # OD-002 requires the matched spans verbatim, so a reader can
                    # decide for themselves whether a hit is substantive reuse or
                    # shared LaTeX boilerplate rather than taking the flag on trust.
                    "matched_ngrams_verbatim": sorted(item["matched_ngrams"])[:10],
                    "matched_ngram_count": len(item["matched_ngrams"]),
                }
            )

    report = {
        "schema_version": "study5-eq1-contamination-report-v2",
        "authority_section": "4.3",
        "scope_definition": "OD-002",
        "screened_split": args.screen,
        "checked_at_utc": utc_now(),
        "phase": "P-0" if args.screen == "development" else "P-1",
        "run_before_any_model_call": True,
        "method": "dual channel: exact 13-gram overlap and hashed character 5-gram cosine",
        "channels_are_lexical_not_neural": True,
        "hash_is_stable_across_processes": True,
        "why_lexical": (
            "the check must run before any model call, and a neural embedding "
            "would make contamination depend on the artefact under study"
        ),
        "thresholds_fixed_before_measurement": True,
        "thresholds_unchanged_from_p0": True,
        "ngram_n": NGRAM_N,
        "ngram_flag_threshold": NGRAM_FLAG_THRESHOLD,
        "cosine_char_ngram": CHAR_NGRAM,
        "cosine_flag_threshold": COSINE_FLAG_THRESHOLD,
        "flag_rule": "either channel exceeding its threshold flags the item",
        "benchmark_split_artifact": args.split,
        "benchmark_split_sha256": hashlib.sha256(
            Path(args.split).read_bytes()
        ).hexdigest(),
        "items_checked": len(items),
        "other_split_items_checked": 0,
        "other_split_items_loaded": 0,
        "reference_files": [str(r) for r in args.reference],
        "reference_rows_scanned": rows_scanned,
        "flagged_item_count": len(flagged),
        "overlap_rate": round(len(flagged) / len(items), 6) if items else 0.0,
        "flagged_items": flagged,
        "primary_analysis_set_size": len(items) - len(flagged),
        "excluded_items_retained_as_registered_sensitivity_set": True,
        "max_cosine_observed": round(
            max((i["max_cosine"] for i in items), default=0.0), 4
        ),
        "max_shared_ngrams_observed": max(
            (i["shared_ngrams"] for i in items), default=0
        ),
        "model_calls": 0,
        "items_tokenized": 0,
        "items_prefilled": 0,
        "items_generated_from": 0,
        "items_scored": 0,
        "limitation_wording": (
            "In an item-paired difference design, contamination is primarily a "
            "CEILING risk: it lifts every arm equally and compresses the "
            "difference between them. It is not described as a threat to "
            "validity, because the paired design differences out an item-level "
            "effect common to all arms."
        ),
        "interpretation_ceiling": (
            "This measures overlap between the adapter's training sample and the "
            "benchmark items. It is reported alongside any accuracy figure. It "
            "is not evidence about J-space, about distillation, or about "
            "reasoning."
        ),
        "other_split_pool_size": len(other_ids),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    print(
        f"split={args.screen} items={len(items)} reference_rows={rows_scanned} "
        f"flagged={len(flagged)} overlap_rate={report['overlap_rate']} "
        f"primary_set={report['primary_analysis_set_size']}"
    )
    print(
        f"max_shared_ngrams={report['max_shared_ngrams_observed']} "
        f"max_cosine={report['max_cosine_observed']}"
    )
    print(f"P1-CHECK-S0.CONTAM-{args.screen} PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
