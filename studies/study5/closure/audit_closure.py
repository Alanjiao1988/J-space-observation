"""Audit STUDY5_CLOSURE.md against the closure specification's sections 5.3 and 5.4.

Two questions, kept separate because they have different answers and different
remedies:

  presence     is every required item verbatim in the file?
  position     is the methodological output JUXTAPOSED with the failure map, or
               placed after it where a reader meets three failure sections first?

The presence check is mechanical: each required item is identified by a distinctive
phrase that must appear in the relevant section. Checking by eye is exactly the
kind of verification OD-017 exists to refuse.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
DOC = ROOT / "STUDY5_CLOSURE.md"

# Required items of specification 5.3, each with a phrase that must be present.
REQUIRED_5_3 = {
    "directionality_rule": "the direction, not the outcome",
    "post_hoc_tightening_vs_loosening": "Post-hoc tightening vs loosening",
    "asymmetric_motivation_disclosure": "Asymmetric-motivation disclosure",
    "OD-011_rev_2_must_return_positive": "must-return-positive",
    "OD-017_live_imported_values": "live imported values",
    "OD-021_adjudicator_not_exempt": "is not exempt from",
    "OD-022_zero_gpu_precondition": "zero-GPU precondition gate",
    "push_the_rule_before_the_number": "Push the rule before computing the number",
    "commit_failed_repairs": "Commit failed repairs",
    "sweep_and_rev2_complementary": "two ends of the nuisance",
}

# Required items of specification 5.4.
REQUIRED_5_4 = {
    "no_passing_positive_control": "never obtained a passing positive control",
    "bf16_reduction_order": "0.476 / 0.110937 logits",
    "bf16_uninterpretable": "no-ops is uninterpretable",
    "object_is_a_selection_set": "is a selection set",
    "hop2_not_a_representation": "not* an internal intermediate",
    "hop1_not_a_finding": "not a finding of this project",
}


def sections(text: str) -> list[dict]:
    """Split into the preamble and the `## ` sections, keeping every byte."""
    parts = re.split(r"(?m)^(## .*)$", text)
    out = [{"heading": None, "body": parts[0]}]
    for index in range(1, len(parts), 2):
        out.append({"heading": parts[index], "body": parts[index + 1]})
    return out


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    blocks = sections(text)
    headings = [b["heading"] for b in blocks if b["heading"]]

    def find(pattern):
        for position, block in enumerate(blocks):
            if block["heading"] and pattern in block["heading"]:
                return position
        return None

    failure_map = find("Failure map") or find("failure map")
    methodology = find("Methodological output")
    limitations = find("Limitations")

    method_body = blocks[methodology]["body"] if methodology else ""
    limits_body = blocks[limitations]["body"] if limitations else ""

    present_5_3 = {k: (v in method_body) for k, v in REQUIRED_5_3.items()}
    present_5_4 = {k: (v in limits_body) for k, v in REQUIRED_5_4.items()}

    missing_5_3 = sorted(k for k, ok in present_5_3.items() if not ok)
    missing_5_4 = sorted(k for k, ok in present_5_4.items() if not ok)

    sections_between = methodology - failure_map - 1 if methodology and failure_map else None
    adjacent = sections_between == 0

    if missing_5_3 or missing_5_4:
        case = 3
        case_name = "MISSING_OR_INCOMPLETE"
    elif adjacent:
        case = 1
        case_name = "PRESENT_AND_CORRECTLY_POSITIONED"
    else:
        case = 2
        case_name = "PRESENT_BUT_PLACED_AFTER_THE_FAILURE_MAP"

    report = {
        "schema_version": "study5-closure-audit-v1",
        "document": "STUDY5_CLOSURE.md",
        "method": (
            "each required item is located by a distinctive phrase that must "
            "appear in the relevant section; checking by eye is the kind of "
            "verification OD-017 exists to refuse"
        ),
        "headings_in_order": headings,
        "presence": {
            "spec_5_3_methodological_output": present_5_3,
            "spec_5_3_all_present": not missing_5_3,
            "spec_5_3_missing": missing_5_3,
            "spec_5_4_limitations": present_5_4,
            "spec_5_4_all_present": not missing_5_4,
            "spec_5_4_missing": missing_5_4,
        },
        "position": {
            "failure_map_index": failure_map,
            "methodological_output_index": methodology,
            "sections_between": sections_between,
            "adjacent_to_the_failure_map": adjacent,
            "the_requirement": (
                "juxtaposed with the failure map, not placed after it as an "
                "appendix"
            ),
            "what_a_reader_meets_before_it": [
                blocks[i]["heading"]
                for i in range(failure_map + 1, methodology)
            ] if (failure_map is not None and methodology is not None) else [],
        },
        "case": case,
        "case_name": case_name,
        "remedy_permitted_by_the_specification": {
            1: "report only; do not modify the file and the hash is unchanged",
            2: "a PURE REORDER moving it up is permitted; the diff must be a pure rearrangement with zero verbatim content change, and that must be proven",
            3: "complete it; this fills in an already-issued specification and is not a new conclusion",
        }[case],
        "claim_ceiling": "An audit record. It licenses no claim of any kind.",
    }
    (ROOT / "CLOSURE_AUDIT.json").write_bytes(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )

    print("spec 5.3 methodological output:")
    for key, ok in present_5_3.items():
        print(f"  {'PRESENT' if ok else 'MISSING':8} {key}")
    print("spec 5.4 limitations:")
    for key, ok in present_5_4.items():
        print(f"  {'PRESENT' if ok else 'MISSING':8} {key}")
    print()
    print(f"failure map at section index      : {failure_map}")
    print(f"methodological output at index    : {methodology}")
    print(f"sections between them             : {sections_between}")
    print(f"reader meets first                : "
          f"{[blocks[i]['heading'] for i in range(failure_map + 1, methodology)]}")
    print()
    print(f"CASE {case}: {case_name}")
    print(f"remedy: {report['remedy_permitted_by_the_specification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
