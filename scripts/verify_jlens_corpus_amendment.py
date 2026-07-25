#!/usr/bin/env python3
"""Deterministic re-verification of the Phase 0.5C J-lens corpus amendment.

The Phase 0.5B corpus ``data/jlens_saturation_prompts.jsonl`` was amended by
appending ten registered ``role=reserve`` prompts (``sat-reserve-016`` through
``sat-reserve-025``) so that a 25-prompt fit set disjoint from the Phase 0.5B
fit set exists. This script re-checks every registered property of that
amendment without a GPU, a model, or a network call, and prints a report.

Engineering bookkeeping only. Nothing here is a semantic or interpretive
result of any kind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORPUS_PATH = PROJECT_ROOT / "data" / "jlens_saturation_prompts.jsonl"

# Phase 0.5B registered corpus, frozen before the amendment.
BASE_RECORDS = 50
BASE_BYTES = 13452
BASE_SHA256 = "41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b"

# Phase 0.5C amended corpus.
AMENDED_RECORDS = 60
AMENDED_BYTES = 16087
AMENDED_SHA256 = "dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa"

NEW_PROMPT_IDS = tuple(f"sat-reserve-{index:03d}" for index in range(16, 26))
EXPECTED_ROLE_COUNTS = {"fit": 25, "heldout": 10, "reserve": 25}

PROXY_TOKENIZER = "regex_word_punctuation_proxy_v1"
PROXY_TOKEN_MIN = 38
PROXY_TOKEN_MAX = 44
# Truncation to max_seq_len=32 is only deterministic if every prompt is
# comfortably longer than the window; 33 proxy units is the registered floor.
GUARANTEED_TRUNCATION_MIN = 33
CHAR_MIN = 199
CHAR_MAX = 238

FORBIDDEN_CUES = (
    "phase1",
    "phase 1",
    "evaluator",
    "locked",
    "reference answer",
    "answer-only",
)

# Every other registered prompt/text source the amendment must not overlap.
OVERLAP_SOURCES = (
    "data/phase1_task_headroom_candidates.jsonl",
    "data/jlens_feasibility_prompts.jsonl",
    "evaluator_sets",
    "tests/fixtures",
)
MIN_CANDIDATE_LENGTH = 24


class AmendmentError(AssertionError):
    """A registered property of the corpus amendment does not hold."""


def proxy_token_count(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalise(text: str) -> str:
    """Lower-cased, NFKC-folded, whitespace- and punctuation-collapsed form."""

    folded = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def load_lines(raw: bytes) -> list[str]:
    return [line for line in raw.decode("utf-8").split("\n") if line.strip()]


def iter_strings(value: Any) -> Any:
    """Yield every string reachable inside a decoded JSON value."""

    if isinstance(value, str):
        if len(value) >= MIN_CANDIDATE_LENGTH:
            yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_strings(item)


def iter_source_texts(root: Path) -> Any:
    """Yield every string that could plausibly be a prompt in another source."""

    for relative in OVERLAP_SOURCES:
        path = root / relative
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                item
                for item in path.rglob("*")
                if item.is_file()
                and item.suffix.lower() in {".jsonl", ".json", ".md", ".py", ".txt"}
            )
        else:
            continue
        for item in candidates:
            try:
                text = item.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if item.suffix.lower() in {".jsonl", ".json"}:
                blocks = (
                    text.splitlines() if item.suffix.lower() == ".jsonl" else [text]
                )
                for line in blocks:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        yield item, line
                        continue
                    for value in iter_strings(record):
                        yield item, value
            else:
                yield item, text


def verify(corpus_path: Path, root: Path) -> dict[str, Any]:
    raw = corpus_path.read_bytes()
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, bool(condition), detail))

    check("file_is_lf_only", b"\r" not in raw, "no CR byte anywhere")
    check("file_ends_with_newline", raw.endswith(b"\n"))
    check("file_is_utf8", True, "decoded below")
    text = raw.decode("utf-8")
    check("file_is_ascii", all(ord(ch) < 128 for ch in text))
    check(
        "amended_bytes",
        len(raw) == AMENDED_BYTES,
        f"{len(raw)} == {AMENDED_BYTES}",
    )
    amended_sha = hashlib.sha256(raw).hexdigest()
    check("amended_sha256", amended_sha == AMENDED_SHA256, amended_sha)

    prefix = raw[:BASE_BYTES]
    prefix_sha = hashlib.sha256(prefix).hexdigest()
    check(
        "first_50_records_byte_identical",
        prefix_sha == BASE_SHA256,
        f"sha256(first {BASE_BYTES} bytes) = {prefix_sha}",
    )
    check(
        "prefix_ends_on_a_record_boundary",
        prefix.endswith(b"\n") and len(load_lines(prefix)) == BASE_RECORDS,
    )
    check(
        "amendment_is_append_only",
        raw[:BASE_BYTES] == prefix and len(raw) > BASE_BYTES,
    )

    lines = load_lines(raw)
    check("amended_record_count", len(lines) == AMENDED_RECORDS, str(len(lines)))

    records: list[dict[str, str]] = []
    for number, line in enumerate(lines, 1):
        record = json.loads(line)
        if set(record) != {"id", "role", "text"}:
            raise AmendmentError(f"line {number} does not carry exactly id/role/text")
        if list(record) != ["id", "role", "text"]:
            raise AmendmentError(f"line {number} key order is not id/role/text")
        canonical = json.dumps(
            {"id": record["id"], "role": record["role"], "text": record["text"]},
            separators=(",", ":"),
            ensure_ascii=False,
        )
        if canonical != line:
            raise AmendmentError(f"line {number} is not compact canonical JSON")
        records.append(record)

    check(
        "every_line_is_compact_canonical_json_in_id_role_text_order",
        True,
        "checked above",
    )

    roles: dict[str, int] = {}
    for record in records:
        roles[record["role"]] = roles.get(record["role"], 0) + 1
    check("role_histogram", roles == EXPECTED_ROLE_COUNTS, json.dumps(roles, sort_keys=True))

    identifiers = [record["id"] for record in records]
    texts = [record["text"] for record in records]
    check("ids_unique", len(set(identifiers)) == len(identifiers))
    check("texts_pairwise_distinct", len(set(texts)) == len(texts))
    check(
        "normalised_texts_pairwise_distinct",
        len({normalise(item) for item in texts}) == len(texts),
    )

    new_records = [record for record in records if record["id"] in set(NEW_PROMPT_IDS)]
    check("ten_new_ids_present", len(new_records) == 10)
    check(
        "new_ids_are_the_registered_ids",
        [record["id"] for record in new_records] == list(NEW_PROMPT_IDS),
    )
    check(
        "new_records_are_the_last_ten_lines",
        [record["id"] for record in records[-10:]] == list(NEW_PROMPT_IDS),
    )
    check(
        "new_records_are_all_reserve",
        all(record["role"] == "reserve" for record in new_records),
    )
    check(
        "first_fifty_ids_unchanged_in_order",
        [record["id"] for record in records[:BASE_RECORDS]]
        == [json.loads(line)["id"] for line in load_lines(prefix)],
    )

    rows: list[dict[str, Any]] = []
    for record in new_records:
        tokens = proxy_token_count(record["text"])
        characters = len(record["text"])
        digest = sha256_text(record["text"])
        rows.append(
            {
                "id": record["id"],
                "role": record["role"],
                "proxy_tokens": tokens,
                "characters": characters,
                "text_sha256_16": digest[:16],
            }
        )
        check(
            f"{record['id']}::proxy_tokens_in_{PROXY_TOKEN_MIN}_{PROXY_TOKEN_MAX}",
            PROXY_TOKEN_MIN <= tokens <= PROXY_TOKEN_MAX,
            str(tokens),
        )
        check(
            f"{record['id']}::proxy_tokens_at_least_{GUARANTEED_TRUNCATION_MIN}",
            tokens >= GUARANTEED_TRUNCATION_MIN,
            str(tokens),
        )
        check(
            f"{record['id']}::characters_in_{CHAR_MIN}_{CHAR_MAX}",
            CHAR_MIN <= characters <= CHAR_MAX,
            str(characters),
        )
        lowered = f"{record['id']} {record['text']}".lower()
        offenders = [cue for cue in FORBIDDEN_CUES if cue in lowered]
        check(f"{record['id']}::no_forbidden_cue", not offenders, ",".join(offenders))
        check(
            f"{record['id']}::ascii_only",
            all(ord(ch) < 128 for ch in record["text"]),
        )
        check(
            f"{record['id']}::no_question_mark",
            "?" not in record["text"],
        )

    check(
        "whole_corpus_free_of_forbidden_cues",
        not [
            record["id"]
            for record in records
            if any(
                cue in f"{record['id']} {record['text']}".lower()
                for cue in FORBIDDEN_CUES
            )
        ],
    )
    all_tokens = [proxy_token_count(record["text"]) for record in records]
    check(
        "whole_corpus_proxy_token_range",
        min(all_tokens) >= PROXY_TOKEN_MIN and max(all_tokens) <= PROXY_TOKEN_MAX,
        f"{min(all_tokens)}-{max(all_tokens)}",
    )

    exact_index = {item: index for index, item in enumerate(texts)}
    normalised_index = {normalise(item): index for index, item in enumerate(texts)}
    exact_hits: list[str] = []
    normalised_hits: list[str] = []
    scanned = 0
    for source, value in iter_source_texts(root):
        scanned += 1
        stripped = value.strip()
        if stripped in exact_index:
            exact_hits.append(f"{source.as_posix()}::{exact_index[stripped]}")
        folded = normalise(stripped)
        if folded and folded in normalised_index:
            normalised_hits.append(f"{source.as_posix()}::{normalised_index[folded]}")
        for record in new_records:
            if record["text"] in value:
                exact_hits.append(f"{source.as_posix()}::substring::{record['id']}")
    check("no_exact_text_overlap_with_other_sources", not exact_hits, ";".join(exact_hits[:5]))
    check(
        "no_normalised_text_overlap_with_other_sources",
        not normalised_hits,
        ";".join(normalised_hits[:5]),
    )

    return {
        "corpus_path": corpus_path.as_posix(),
        "base": {
            "records": BASE_RECORDS,
            "bytes": BASE_BYTES,
            "sha256": BASE_SHA256,
        },
        "amended": {
            "records": len(records),
            "bytes": len(raw),
            "sha256": amended_sha,
            "prefix_sha256": prefix_sha,
        },
        "role_histogram": roles,
        "new_prompts": rows,
        "overlap_sources_scanned": len(OVERLAP_SOURCES),
        "candidate_strings_scanned": scanned,
        "checks": checks,
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "Phase 0.5C J-lens corpus amendment verification",
        "=" * 52,
        f"corpus                 : {report['corpus_path']}",
        f"base    records/bytes  : {report['base']['records']} / {report['base']['bytes']}",
        f"base    sha256         : {report['base']['sha256']}",
        f"amended records/bytes  : {report['amended']['records']} / {report['amended']['bytes']}",
        f"amended sha256         : {report['amended']['sha256']}",
        f"prefix  sha256         : {report['amended']['prefix_sha256']}",
        f"role histogram         : {json.dumps(report['role_histogram'], sort_keys=True)}",
        f"proxy tokenizer        : {PROXY_TOKENIZER}",
        f"other sources scanned  : {report['overlap_sources_scanned']} "
        f"({report['candidate_strings_scanned']} candidate strings)",
        "",
        "| ID | Role | Proxy tokens | Characters | Text SHA-256 (first 16) |",
        "|---|---|---:|---:|---|",
    ]
    for row in report["new_prompts"]:
        lines.append(
            f"| `{row['id']}` | {row['role']} | {row['proxy_tokens']} | "
            f"{row['characters']} | `{row['text_sha256_16']}` |"
        )
    failures = [item for item in report["checks"] if not item[1]]
    lines.extend(
        [
            "",
            f"checks run             : {len(report['checks'])}",
            f"checks failed          : {len(failures)}",
        ]
    )
    for name, _passed, detail in failures:
        lines.append(f"  FAIL {name} {detail}")
    lines.append("")
    lines.append("RESULT: PASS" if not failures else "RESULT: FAIL")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(CORPUS_PATH))
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--json", action="store_true", help="emit the raw report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = verify(Path(args.corpus), Path(args.root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report))
    return 0 if all(item[1] for item in report["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
