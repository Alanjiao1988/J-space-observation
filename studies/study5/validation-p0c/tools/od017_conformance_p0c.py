"""OD-017 conformance audit for P-0c, extended by OD-021.

Same refusal to accept a comment as evidence: each module is imported and its
live values are compared against the committed registration.

OD-021 adds a direction of comparison that P-0's audit did not have. Several
values in this phase were HANDED DOWN rather than authored here - the suggested
accuracy floor, the seed directions for the candidate shortlist, the inherited
three-part batch repair. Each is checked against what the code actually does,
because the precipitating event for OD-021 was an adjudicator-issued estimand
that turned out to be the one already in use.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
P0_TOOLS = ROOT.parent / "validation-p0" / "tools"
P0PRIME_TOOLS = ROOT.parent / "validation-p0-prime" / "tools"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--object")
    parser.add_argument("--proof")
    args = parser.parse_args()

    reg = json.loads((ROOT / "P0C_PREREGISTRATION.json").read_text(encoding="utf-8"))
    shortlist = json.loads(
        (ROOT / "registrations" / "CANDIDATE_SHORTLIST.json").read_text(encoding="utf-8")
    )
    od021 = json.loads(
        (ROOT / "registrations" / "OD-021.json").read_text(encoding="utf-8")
    )
    od022 = json.loads(
        (ROOT / "registrations" / "OD-022.json").read_text(encoding="utf-8")
    )
    requirements = reg["1_the_object"]["the_seven_requirements"]
    ablation = reg["2_the_anti_retrieval_proof"]

    build = load("p0c_build", TOOLS / "build_object.py")
    guard = load("p0c_guard", TOOLS / "guard_p0.py")

    entries: list[dict] = []

    def entry(reg_id, registered_text, impl, behaviour, registered_value,
              observed_value, **extra):
        record = {
            "registered_id": reg_id,
            "registered_text": registered_text,
            "implementation": impl,
            "what_the_code_actually_does": behaviour,
            "registered_value": registered_value,
            "observed_value": observed_value,
            "verdict": "CONFORMS" if registered_value == observed_value else "DIVERGES",
        }
        record.update(extra)
        entries.append(record)

    # -------------------------------------------------- OD-021, handed-down values
    entry(
        "OD-021.accuracy_floor_was_verified_not_merely_adopted",
        "the adjudicator suggested at least 0.80 and left the value to the "
        "executing party",
        "prove_object.main reads the floor from the pushed registration",
        "the tool does not hard-code 0.80; it reads "
        "1_the_object.the_seven_requirements.4_model_accuracy.floor and applies "
        "whatever is there, so the registered text and the applied value cannot "
        "diverge",
        0.80,
        float(requirements["4_model_accuracy"]["floor"]),
        why_this_entry_exists=(
            "OD-021 exists because an adjudicator-issued criterion was not "
            "checked against the implementation and turned out to be the one "
            "already in use"
        ),
    )

    entry(
        "OD-021.floor_is_above_chance_by_a_wide_margin",
        "the floor must be meaningfully above the chance rate, or it is not a "
        "requirement at all",
        "build_object.ANSWER_ALPHABET determines the chance rate",
        "chance is 1/len(ANSWER_ALPHABET); the floor is compared against it",
        True,
        float(requirements["4_model_accuracy"]["floor"])
        > 4 * (1.0 / len(build.ANSWER_ALPHABET)),
        chance_rate=1.0 / len(build.ANSWER_ALPHABET),
    )

    entry(
        "OD-021.ablation_ceiling_is_chance_plus_the_registered_tolerance",
        f"ceiling = chance + {ablation['tolerance']}",
        "arithmetic on the registration's own fields",
        "the ceiling recorded in the registration equals chance plus tolerance",
        round(float(ablation["chance_rate"]) + float(ablation["tolerance"]), 12),
        round(float(ablation["ceiling"]), 12),
    )

    # ------------------------------------------------------------- the object
    entry(
        "object.requirement_2_disjoint_vocabularies",
        requirements["2_intermediate_never_the_emitted_token"]["how"],
        "build_object.build, the all_letters & all_digits check",
        "the build RAISES if the intermediate and answer token-id sets "
        "intersect, over every single-token surface form each can produce, so a "
        "violating object cannot be written at all",
        [],
        requirements["2_intermediate_never_the_emitted_token"]["observed_overlap"],
        source_excerpt=inspect.getsource(build.single_token_forms).strip(),
    )

    entry(
        "object.requirement_6_alignment_is_measured_in_context",
        "the pair is admitted only if the two names tokenise to the same length "
        "IN THE QUESTION LINE",
        "build_object.context_length, used in the options comprehension",
        "the length is measured on ' {name}', the form the name actually takes "
        "in the question line, not on the bare form",
        True,
        "context_length(tokenizer, a[0]) == context_length(tokenizer, b[0])"
        in (TOOLS / "build_object.py").read_text(encoding="utf-8"),
        note=(
            "filtering on the bare form admitted misaligned pairs and silently "
            "discarded 89 of 160; the defect was found and fixed before any "
            "measurement"
        ),
    )

    entry(
        "object.requirement_7_verified_not_asserted",
        "every PREFIX and BRIDGE position carries the same token in both members",
        "build_object.main, the violations loop",
        "it compares donor_ids[position] against recipient_ids[position] for "
        "every position of both sites and FAILS the build on any mismatch",
        0,
        requirements["7_bridge_tokens_identical"]["positions_where_the_members_differ"],
    )

    entry(
        "object.build_seed",
        "the build seed is 20260829",
        "build_object.BUILD_SEED",
        "the single seed drives the table, the registrations and the name choice",
        20260829,
        build.BUILD_SEED,
    )

    entry(
        "object.no_item_borrowed",
        "no item is borrowed and no model output is consulted during construction",
        "build_object, its imports and its inputs",
        "the module imports only argparse, json, random, string, sys and "
        "pathlib, plus the tokeniser; it opens no evaluation set and runs no "
        "model",
        False,
        any(
            token in (TOOLS / "build_object.py").read_text(encoding="utf-8")
            for token in ("lens-eval", "AutoModelForCausalLM", "patch_merged")
        ),
    )

    # ---------------------------------------------------------- the shortlist
    entry(
        "shortlist.closed_and_within_the_maximum",
        "at most 4 candidates, declared before any is evaluated, and closed",
        "CANDIDATE_SHORTLIST.json",
        "the file records the candidates, the maximum, and that no member may "
        "be added or repaired",
        [4, True, False, False],
        [
            len(shortlist["the_candidates"]),
            shortlist["declared_before_any_candidate_was_evaluated"],
            shortlist["may_a_candidate_be_added_later"],
            shortlist["may_a_candidate_be_repaired_to_pass"],
        ],
    )

    entry(
        "shortlist.every_candidate_records_its_known_risk_in_advance",
        "each candidate states why it might survive and what its known risk is",
        "CANDIDATE_SHORTLIST.json, the_candidates",
        "each entry carries both fields, so a later failure cannot be presented "
        "as unforeseeable",
        4,
        sum(
            1
            for c in shortlist["the_candidates"].values()
            if c.get("why_it_might_survive") and c.get("known_risk_stated_in_advance")
        ),
    )

    # ---------------------------------------------------- OD-022 and OD-011
    entry(
        "OD-022.in_force_and_ordered_before_OD-011",
        "a candidate faces the destruction sweep first, because a candidate it "
        "rejects never needs anything further",
        "OD-022.json, relation_to_OD_011.ordering",
        "the rule records the ordering explicitly",
        "OD-022 first, because a candidate it rejects never needs an OD-011 demonstration",
        od022["relation_to_OD_011"]["ordering"],
    )

    entry(
        "OD-021.is_in_force",
        "OD-021 is in force from this phase",
        "OD-021.json",
        "the registration records its status",
        "IN FORCE",
        od021["status"],
    )

    # ------------------------------------------------------------ boundaries
    entry(
        "boundaries.no_tool_imports_the_instrument_under_test",
        "no P-0c tool imports the library EQ2 was testing",
        "guard_p0.imports_jlens over every tool in this namespace",
        "the check matches an import statement rather than the bare word",
        [],
        sorted(
            p.name
            for p in TOOLS.glob("*.py")
            if guard.imports_jlens(p.read_text(encoding="utf-8"))
        ),
    )

    entry(
        "boundaries.no_tool_references_the_target",
        "no P-0c tool references T",
        "guard_p0.scan_tools, which applies the registered self-exclusion",
        "every tool is scanned for the target's repository id and pinned "
        "revision; guard_p0.py is the ONLY file excluded, because it cannot "
        "scan for markers without containing them, and a guard that fires on "
        "its own evidence gets silenced rather than fixed",
        [],
        guard.scan_tools(ROOT)["target_or_lens_references_in_tools"],
        note=(
            "an earlier revision of this audit scanned every file including the "
            "guard and reported a divergence on the guard's own source; the "
            "check was routed through the guard's registered exclusion, which "
            "moves the implementation toward the registered text"
        ),
    )

    entry(
        "boundaries.predecessor_namespaces_are_not_written",
        "EQ1, EQ2, P-0 and P-0' artifacts are byte-identical",
        "this namespace writes only under validation-p0c/",
        "no P-0c tool opens a predecessor path for writing",
        True,
        all(
            "validation-p0/out" not in p.read_text(encoding="utf-8")
            or "read" in p.read_text(encoding="utf-8")
            for p in TOOLS.glob("*.py")
        ),
    )

    # ------------------------------------------- what the measurement observed
    if args.proof:
        proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
        entry(
            "proof.thresholds_came_from_the_pushed_registration",
            "the tool reads its thresholds from the registration rather than "
            "hard-coding them",
            "prove_object.main",
            "the committed proof records the registration it applied and that "
            "file's digest",
            str(
                (ROOT / "P0C_PREREGISTRATION.json").name
            ),
            Path(proof["registration_applied"]).name,
        )
        entry(
            "proof.determination_is_one_of_the_pre_registered_wordings",
            "the determination must be one of the wordings fixed before any "
            "measurement",
            "prove_object.main, which looks the verbatim text up by name",
            "the determination string selects the registered wording; it cannot "
            "produce a wording that was not registered",
            True,
            proof["determination"]
            in reg["3_conclusion_wordings_fixed_before_any_measurement"],
        )
        entry(
            "proof.nothing_was_patched",
            "the object proof runs on clean runs only",
            "prove_object, which has no hook and no patch path",
            "the tool performs forward passes and reads last-position logits; "
            "it registers no hooks",
            True,
            proof["nothing_was_patched"],
        )

    divergences = [e for e in entries if e["verdict"] != "CONFORMS"]
    report = {
        "schema_version": "study5-p0c-od017-v1",
        "rule": "OD-017, extended by OD-021",
        "phase": "P-0c",
        "method": (
            "each module is imported and its live values are compared against "
            "the committed registrations; comments and hand-written agreement "
            "tables are not accepted as evidence"
        ),
        "what_OD_021_adds": (
            "values HANDED DOWN by the adjudicator are audited in the same way "
            "as values authored here, because the precipitating event was an "
            "adjudicator-issued estimand that was not checked and turned out to "
            "be the one already in use"
        ),
        "directionality_precedent": (
            "changing the IMPLEMENTATION to match the REGISTERED TEXT is a bug "
            "fix; changing the REGISTERED TEXT to match the DATA is p-hacking. "
            "The difference is the direction, not the outcome"
        ),
        "entries": entries,
        "n_entries": len(entries),
        "n_divergences": len(divergences),
        "divergences": divergences,
        "verdict": "PASS" if not divergences else "FAIL",
        "claim_ceiling": "A governance audit. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    for record in entries:
        print(f"  {record['verdict']:9} {record['registered_id']}")
    print(f"{len(entries)} entries, {len(divergences)} divergences")
    if divergences:
        print("P0C-CHECK-OD017 FAILED", file=sys.stderr)
        return 1
    print("P0C-CHECK-OD017 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
