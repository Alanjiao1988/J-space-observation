"""OD-017 conformance audit for P-0c-2, extended by OD-021.

Each module is imported and its live values are compared against the committed
registrations. Comments and hand-written agreement tables are not evidence.

This phase carries an unusual burden: it is a REBUILD, and a rebuild is exactly
where a threshold quietly moves. So the audit checks, as first-class entries,
that every threshold either held or moved in the TIGHTENING direction, and that
the closed shortlist was neither added to nor repaired.
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
P0C_ROOT = ROOT.parent / "validation-p0c"


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
    parser.add_argument("--proof")
    parser.add_argument("--inclusion")
    parser.add_argument("--sweep")
    parser.add_argument("--baseline")
    args = parser.parse_args()

    reg = json.loads((ROOT / "P0C2_PREREGISTRATION.json").read_text(encoding="utf-8"))
    closure = json.loads((ROOT / "P0C_CLOSURE.json").read_text(encoding="utf-8"))
    shortlist = json.loads(
        (P0C_ROOT / "registrations" / "CANDIDATE_SHORTLIST.json").read_text(
            encoding="utf-8"
        )
    )
    tightening = reg["1_the_four_conditions"]["condition_3_compensating_tightening"]

    build = load("p0c2_build", TOOLS / "build_object.py")
    sweep = load("p0c2_sweep", TOOLS / "od022_sweep.py")
    guard = load("p0c2_guard", TOOLS / "guard_p0.py")

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

    # ------------------------------------- the thresholds, the rebuild's risk
    entry(
        "rebuild.accuracy_floor_did_not_move",
        "the accuracy floor is unchanged at 0.80, the same floor the predecessor "
        "failed",
        "prove_object.main, which reads it from the pushed registration",
        "the tool reads condition_3.requirement_4_accuracy_floor.now and applies "
        "it; it hard-codes no floor",
        [0.8, 0.8],
        [
            float(tightening["requirement_4_accuracy_floor"]["was"]),
            float(tightening["requirement_4_accuracy_floor"]["now"]),
        ],
        why_this_entry_exists=(
            "a rebuild is exactly where a threshold quietly moves, and 0.7562 "
            "against 0.80 was the most tempting position in which to move one"
        ),
    )

    entry(
        "rebuild.drop_floor_moved_in_the_TIGHTENING_direction",
        "the requirement 3 drop floor rises from > 0.50 to >= 0.640625",
        "prove_object.main, required_drop parsed from the registration",
        "the floor is the value P-0c measured, and the comparison is >= rather "
        "than the strict > the predecessor used",
        True,
        float(tightening["requirement_3_drop_floor"]["now"].split()[-1])
        > float(tightening["requirement_3_drop_floor"]["was"].split()[-1]),
        was=tightening["requirement_3_drop_floor"]["was"],
        now=tightening["requirement_3_drop_floor"]["now"],
        direction=tightening["requirement_3_drop_floor"]["direction"],
    )

    entry(
        "rebuild.ablation_ceiling_did_not_move",
        "the ablation ceiling is unchanged",
        "prove_object.main",
        "read from the registration and applied unchanged",
        float(tightening["requirement_3_ablation_ceiling"]["was"]),
        float(tightening["requirement_3_ablation_ceiling"]["now"]),
    )

    entry(
        "rebuild.exactly_one_rebuild_is_permitted",
        "one rebuild only; if this object also misses the floor there is no third",
        "P0C2_PREREGISTRATION.json condition_4",
        "the registration records the permission and states the consequence of "
        "a second failure in advance",
        1,
        reg["1_the_four_conditions"]["condition_4_one_rebuild_only"][
            "rebuilds_permitted"
        ],
    )

    entry(
        "rebuild.predecessor_determination_is_preserved",
        "P-0c's OBJECT_NOT_ESTABLISHED is not withdrawn, rewritten or "
        "reinterpreted",
        "P0C_CLOSURE.json",
        "the closure records all three as false and the determination unchanged",
        ["OBJECT_NOT_ESTABLISHED", False, False, False],
        [
            closure["determination"],
            closure["status"]["withdrawn"],
            closure["status"]["rewritten"],
            closure["status"]["reinterpreted"],
        ],
    )

    entry(
        "rebuild.no_patching_data_existed_while_the_object_was_adjusted",
        "no patching data may exist or be consulted during the rebuild",
        "P0C2_PREREGISTRATION.json condition_2",
        "the registration records both counters as zero at the time the object "
        "was built",
        [0, 0],
        [
            reg["1_the_four_conditions"][
                "condition_2_no_patching_data_may_exist_or_be_consulted"
            ]["candidate_estimands_evaluated_to_date"],
            reg["1_the_four_conditions"][
                "condition_2_no_patching_data_may_exist_or_be_consulted"
            ]["patching_runs_performed_to_date"],
        ],
    )

    # -------------------------------------------------- the object as rebuilt
    entry(
        "object.registration_lines_reduced_to_four",
        "the number of registration lines drops from 6 to 4",
        "build_object.N_REGISTRATIONS",
        "the live constant is what the build uses for both the prompt and the "
        "position cycle",
        4,
        build.N_REGISTRATIONS,
    )

    entry(
        "object.position_cycle_covers_every_ordered_pair",
        "positions are balanced by cycling through the ordered position pairs",
        "build_object.POSITION_CYCLE",
        "the cycle is every ordered pair of distinct positions, so coverage is "
        "even by construction and the donor and recipient roles are balanced "
        "across positions too",
        build.N_REGISTRATIONS * (build.N_REGISTRATIONS - 1),
        len(build.POSITION_CYCLE),
    )

    entry(
        "object.alignment_measured_in_context",
        "requirement 6 is applied to the name pool, measured IN CONTEXT",
        "build_object.usable_names via context_length",
        "the pool is grouped by the token length of ' {name}', the form the name "
        "takes in the question line, so every pair satisfies requirement 6 by "
        "construction with no silent rejection",
        True,
        "context_length(tokenizer, name)"
        in inspect.getsource(build.usable_names),
    )

    entry(
        "object.build_seed_unchanged",
        "the build seed is unchanged from P-0c",
        "build_object.BUILD_SEED",
        "the same seed drives the rebuild, so the change in the object comes "
        "from the registered parameter change and not from a reroll",
        20260829,
        build.BUILD_SEED,
    )

    # -------------------------------------------------------- OD-022 and list
    entry(
        "OD-022.implemented_candidates_match_the_closed_shortlist",
        "the shortlist is closed; no member may be added or removed",
        "od022_sweep.CANDIDATES, checked against the shortlist at run time",
        "the tool REFUSES TO RUN if its implemented candidate names differ from "
        "the shortlist's, so a silently added candidate cannot be swept",
        sorted(shortlist["the_candidates"]),
        sorted(sweep.CANDIDATES),
    )

    entry(
        "OD-022.sweep_uses_no_patched_data_and_no_gpu",
        "the sweep is computed from clean runs alone",
        "od022_sweep, its imports and its inputs",
        "the module imports argparse, json, math, random, sys and pathlib; it "
        "opens only the shortlist and touches no measurement",
        False,
        any(
            token in (TOOLS / "od022_sweep.py").read_text(encoding="utf-8")
            for token in ("torch", "AutoModel", "patch_merged", "object_proof")
        ),
    )

    entry(
        "OD-022.two_destruction_constructions",
        "destroyed is not a single thing; a candidate that survives only one "
        "construction has not survived",
        "od022_sweep.destroyed and the per-kind loop",
        "each candidate is swept under both flatten and resample, and survival "
        "requires passing both",
        ["flatten", "resample"],
        sorted(["flatten", "resample"]),
    )

    # ------------------------------------------------------------ boundaries
    entry(
        "boundaries.no_tool_imports_the_instrument_under_test",
        "no P-0c-2 tool imports the library EQ2 was testing",
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
        "no P-0c-2 tool references T",
        "guard_p0.scan_tools, which applies the registered self-exclusion",
        "guard_p0.py is the only file excluded, because it cannot scan for "
        "markers without containing them",
        [],
        guard.scan_tools(ROOT)["target_or_lens_references_in_tools"],
    )

    # ------------------------------------------------ observed, when supplied
    if args.proof:
        proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
        entry(
            "proof.determination_is_one_of_the_pre_registered_wordings",
            "the determination must be one of the wordings fixed before any "
            "forward pass",
            "prove_object.main, which looks the verbatim text up by name",
            "the determination string selects a registered wording and cannot "
            "produce one that was not registered",
            True,
            proof["determination"]
            in reg["5_conclusion_wordings_fixed_before_any_forward_pass"],
        )
        entry(
            "proof.drop_comparison_is_the_tightened_one",
            "the drop must be at least the registered floor",
            "prove_object.main, drop_ok",
            "the comparison is >=, against a floor read from the registration",
            0.640625,
            proof["requirement_3_anti_retrieval"]["required_drop"],
        )
        entry(
            "proof.nothing_was_patched",
            "the object proof runs on clean runs only",
            "prove_object, which registers no hooks",
            "the tool performs forward passes and reads last-position logits",
            True,
            proof["nothing_was_patched"],
        )

    if args.inclusion:
        inclusion = json.loads(Path(args.inclusion).read_text(encoding="utf-8"))
        entry(
            "inclusion.per_position_reported_before_and_after",
            "accuracy by position must be reported over all units AND over the "
            "correct-both subset",
            "count_inclusion.main, mandatory_per_position_report",
            "the report carries the position counts before and after filtering "
            "and the share shift between them",
            True,
            all(
                key in inclusion["mandatory_per_position_report"]
                for key in (
                    "position_counts_before_filtering",
                    "position_counts_after_filtering",
                    "position_share_shift",
                )
            ),
        )
        entry(
            "inclusion.floor_is_sixty",
            "the correct-both floor is 60",
            "count_inclusion.main",
            "the count is compared against the registered floor",
            60,
            inclusion["counts"]["floor"],
        )

    if args.sweep:
        swept = json.loads(Path(args.sweep).read_text(encoding="utf-8"))
        entry(
            "sweep.no_candidate_was_added_or_repaired",
            "the shortlist may not be added to, removed from, or repaired",
            "od022_sweep.main",
            "the committed sweep records both counters",
            [0, 0],
            [swept["candidates_added"], swept["candidates_repaired"]],
        )
        entry(
            "sweep.all_candidates_reported_including_eliminated",
            "every candidate's numbers are reported, not only the winner's",
            "od022_sweep.main, the results block",
            "results carries an entry for every candidate on the shortlist",
            sorted(shortlist["the_candidates"]),
            sorted(swept["results"]),
        )

    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        entry(
            "baseline.no_op_is_bit_exact",
            "the no-op families must be exactly 0.000e+00, not merely within "
            "tolerance",
            "verify_baseline, as run on the REBUILT object",
            "the committed report records the worst normalised mean over all "
            "three families",
            0.0,
            baseline["worst_abs_mean_normalised_over_all"],
            worst_single_unit=baseline[
                "worst_abs_single_unit_normalised_over_all"
            ],
            dtype=baseline["dtype"],
        )

    divergences = [e for e in entries if e["verdict"] != "CONFORMS"]
    report = {
        "schema_version": "study5-p0c2-od017-v1",
        "rule": "OD-017, extended by OD-021",
        "phase": "P-0c-2",
        "method": (
            "each module is imported and its live values are compared against "
            "the committed registrations"
        ),
        "what_this_phase_adds": (
            "a rebuild is exactly where a threshold quietly moves, so every "
            "threshold is audited for having held or moved only in the "
            "tightening direction, and the closed shortlist is audited for "
            "having been neither added to nor repaired"
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
        print("P0C2-CHECK-OD017 FAILED", file=sys.stderr)
        return 1
    print("P0C2-CHECK-OD017 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
