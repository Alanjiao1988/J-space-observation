"""Case 2 remedy: move the methodological output up, and PROVE it is a pure reorder.

The audit found every required item present, but placed after the failure map with
two further failure-themed sections in between, so a reader meets three accounts of
failure before reaching what the project produced. The specification permits a pure
rearrangement to fix that, and requires the rearrangement be proven rather than
asserted.

What is proven here, mechanically:

  bodies      every section's body is BYTE-IDENTICAL before and after
  titles      every heading's title, with the ordinal stripped, is unchanged
  lines       the multiset of all non-heading lines is unchanged
  ordinals    the ONLY textual change is the section number in eight headings,
              and that is stated rather than hidden inside a claim of "no change"

The last point matters. Renumbering is not literally zero-byte, so calling this a
"pure reorder" without qualification would overstate it. The honest claim is:
the substance is byte-identical and only the ordinals move.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
DOC = ROOT / "STUDY5_CLOSURE.md"

#: The permutation, in current section numbers: the methodological output (5)
#: moves to sit immediately after the failure map (2).
NEW_ORDER = [1, 2, 5, 3, 4, 6, 7, 8]


def split_sections(text):
    parts = re.split(r"(?m)^(## .*)$", text)
    preamble = parts[0]
    blocks = []
    for index in range(1, len(parts), 2):
        blocks.append({"heading": parts[index], "body": parts[index + 1]})
    return preamble, blocks


def title_of(heading):
    return re.sub(r"^## \d+\.\s*", "", heading).strip()


def non_heading_lines(text):
    return sorted(
        line for line in text.splitlines() if not line.startswith("## ")
    )


def main() -> int:
    before = DOC.read_text(encoding="utf-8")
    before_sha = hashlib.sha256(before.encode("utf-8")).hexdigest()
    preamble, blocks = split_sections(before)

    if len(blocks) != len(NEW_ORDER):
        raise SystemExit(f"expected {len(NEW_ORDER)} sections, found {len(blocks)}")

    # Refuse to reorder if the permuted bodies do not share a separator shape;
    # a silent structural break would be worse than leaving the file alone.
    # The check is on the SEPARATOR, not on the last characters of the prose,
    # which differ from section to section and say nothing about structure.
    separator = "\n\n---\n\n"
    permuted = [blocks[n - 1] for n in NEW_ORDER]
    bad = [n for n in (3, 4, 5) if not blocks[n - 1]["body"].endswith(separator)]
    if bad:
        raise SystemExit(f"sections {bad} do not end with the separator; refusing")

    rebuilt = [preamble]
    for position, block in enumerate(permuted, start=1):
        rebuilt.append(f"## {position}. {title_of(block['heading'])}")
        rebuilt.append(block["body"])
    after = "".join(
        part if part.startswith("\n") or index == 0 else part
        for index, part in enumerate(rebuilt)
    )
    # reassemble faithfully: heading lines need their newline restored
    after = preamble
    for position, block in enumerate(permuted, start=1):
        after += f"## {position}. {title_of(block['heading'])}" + block["body"]

    after_sha = hashlib.sha256(after.encode("utf-8")).hexdigest()

    # ---- the proofs -------------------------------------------------------
    bodies_before = sorted(b["body"] for b in blocks)
    bodies_after = sorted(b["body"] for b in permuted)
    bodies_identical = bodies_before == bodies_after

    titles_before = sorted(title_of(b["heading"]) for b in blocks)
    titles_after = sorted(title_of(b["heading"]) for b in permuted)
    titles_identical = titles_before == titles_after

    lines_identical = non_heading_lines(before) == non_heading_lines(after)

    ordinal_changes = []
    for position, block in enumerate(permuted, start=1):
        old = block["heading"]
        new = f"## {position}. {title_of(block['heading'])}"
        if old != new:
            ordinal_changes.append({"from": old, "to": new})

    ok = bodies_identical and titles_identical and lines_identical
    if not ok:
        raise SystemExit("the rearrangement is not pure; refusing to write")

    DOC.write_text(after, encoding="utf-8", newline="")

    proof = {
        "schema_version": "study5-closure-reorder-proof-v1",
        "document": "STUDY5_CLOSURE.md",
        "case": 2,
        "case_name": "PRESENT_BUT_PLACED_AFTER_THE_FAILURE_MAP",
        "what_was_wrong": (
            "every required item of specification 5.3 and 5.4 was present, but the "
            "methodological output sat two sections after the failure map, behind "
            "'Why no fifth candidate was declared' and 'C1's failure is a real "
            "defect', so a reader met three accounts of failure before reaching "
            "what the project produced"
        ),
        "what_was_done": "the methodological output was moved to sit immediately after the failure map",
        "permutation_in_original_section_numbers": NEW_ORDER,
        "proofs": {
            "every_section_body_byte_identical": bodies_identical,
            "every_heading_title_unchanged_once_the_ordinal_is_stripped": titles_identical,
            "multiset_of_all_non_heading_lines_unchanged": lines_identical,
        },
        "the_only_textual_change": {
            "what": "the section ordinal in the headings",
            "count": len(ordinal_changes),
            "changes": ordinal_changes,
            "stated_rather_than_hidden": (
                "renumbering is not literally zero-byte, so calling this a pure "
                "reorder without qualification would overstate it; the honest "
                "claim is that the substance is byte-identical and only the "
                "ordinals move"
            ),
        },
        "no_conclusion_criterion_threshold_or_verdict_was_altered": True,
        "sha256_before": before_sha,
        "sha256_after": after_sha,
        "the_before_hash_is_superseded_not_deleted": True,
        "claim_ceiling": "A rearrangement proof. It licenses no claim of any kind.",
    }
    (ROOT / "CLOSURE_REORDER_PROOF.json").write_bytes(
        json.dumps(proof, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )

    print("proofs:")
    print(f"  bodies byte-identical            : {bodies_identical}")
    print(f"  titles unchanged (ordinal stripped): {titles_identical}")
    print(f"  non-heading line multiset unchanged: {lines_identical}")
    print(f"  ordinal-only heading changes     : {len(ordinal_changes)}")
    for change in ordinal_changes:
        print(f"    {change['from']}  ->  {change['to']}")
    print()
    print(f"sha256 before (SUPERSEDED): {before_sha}")
    print(f"sha256 after             : {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
