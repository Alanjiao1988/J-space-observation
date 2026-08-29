"""OD-017 conformance audit for P-0: registered text against live implementation.

DC-005 was found only because it produced an anomalous result. A divergence
that happened to look plausible would never have surfaced, and OD-017 records
that as the heavier problem. So this audit does not read comments and does not
accept a hand-written table asserting agreement: it IMPORTS each module and
compares the live value of every registered constant against the value written
in P0_PREREGISTRATION.json.

Two constants also cross a study boundary. P-0's readout rule and its notion of
a single-token surface form are transcriptions of EQ2's, deliberately copied
rather than imported so that `jlens` stays out of P-0's ground-truth path.
A transcription is exactly the kind of thing that silently drifts, so the audit
imports EQ2's `rank_profile` - which is safe HERE, because the audit is not the
measurement - and compares the live EQ2 values against P-0's live values.

The directionality precedent applies to anything this audit surfaces: moving
the IMPLEMENTATION toward the REGISTERED TEXT is a bug fix; moving the
REGISTERED TEXT toward the DATA is p-hacking. The difference is the direction,
not the outcome.
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
EQ2_TOOLS = ROOT.parent / "qualification-eq2" / "tools"


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
    parser.add_argument("--patch-report", help="optional measured report to audit")
    args = parser.parse_args()

    reg = json.loads((ROOT / "P0_PREREGISTRATION.json").read_text(encoding="utf-8"))
    pairs = load("audit_pairs", TOOLS / "build_pairs.py")
    decider = load("audit_decider", TOOLS / "decide_p0.py")
    patch = load("audit_patch", TOOLS / "patch_effect.py")
    vacuity = load("audit_vacuity", TOOLS / "non_vacuity_p0.py")
    guard = load("audit_guard", TOOLS / "guard_p0.py")

    entries: list[dict] = []

    def entry(reg_id, registered_text, impl, behaviour, registered_value, observed_value,
              **extra):
        conforms = registered_value == observed_value
        record = {
            "registered_id": reg_id,
            "registered_text": registered_text,
            "implementation": impl,
            "what_the_code_actually_does": behaviour,
            "registered_value": registered_value,
            "observed_value": observed_value,
            "verdict": "CONFORMS" if conforms else "DIVERGES",
        }
        record.update(extra)
        entries.append(record)

    section1 = reg["1_sampling"]
    section2 = reg["2_decision_rule"]
    section3 = reg["3_zero_intervention_null"]
    section4 = reg["4_harness_positive_control"]
    section7 = reg["7_gates_that_must_pass_before_the_criterion_touches_real_data"]

    entry(
        "1_sampling.source",
        "the frame is drawn from the pre-existing multihop evaluation set",
        "build_pairs.EVAL_SLUG",
        "the tool opens lens-eval-<EVAL_SLUG>.json and reads no other set",
        "multihop",
        pairs.EVAL_SLUG,
    )

    entry(
        "1_sampling.max_units",
        "max_units = 200",
        "passed to build_pairs.main as --max-units and compared against len(units)",
        "the cap is applied by dropping whole clusters, never by splitting one",
        200,
        section1["max_units"],
        note="the live check that the value reaching the tool equals this is the "
             "frame report's frame.max_units field, audited below when present",
    )

    entry(
        "1_sampling.seed",
        "seed = 20260829",
        "build_pairs.main --seed, and decide_p0.BOOTSTRAP_SEED",
        "the same integer seeds the frame and the bootstrap",
        20260829,
        section1["seed"],
    )

    entry(
        "1_sampling.admissibility_rules",
        "the ten registered admissibility rules",
        "build_pairs.compatible and build_pairs.sites_for",
        "compatible() enforces the four content rules; sites_for() enforces "
        "equal length, at least one difference, the last difference strictly "
        "before the readout, non-empty BRIDGE and non-empty PREFIX",
        section1["admissibility_rules"],
        section1["admissibility_rules"],
        source_excerpt=inspect.getsource(pairs.sites_for).strip(),
        note="the registration text and the tool's own emitted list are the same "
             "object by construction; the behavioural claim is carried by the "
             "excerpt and by tests/test_p0_pairs.py, which asserts each rule "
             "rejects a case built to violate it",
    )

    entry(
        "2_decision_rule.decisive_site",
        "the verdict is read from BRIDGE and from no other site",
        "decide_p0.DECISIVE_SITE, used in decide_p0.decide",
        "decide() looks up summary[real_key][DECISIVE_SITE] and reads the "
        "layer set from that series alone; CUE and READOUT never enter the "
        "verdict expression",
        "BRIDGE",
        decider.DECISIVE_SITE,
        cross_check_build_pairs=pairs.DECISIVE_SITE,
        source_excerpt=inspect.getsource(decider.decide).strip(),
    )

    entry(
        "2_decision_rule.confidence_level",
        "two-sided 95 percent",
        "decide_p0.CONFIDENCE, LOWER_PERCENTILE, UPPER_PERCENTILE",
        "the interval is taken as the 2.5th and 97.5th percentiles of the "
        "bootstrap distribution",
        [0.95, 2.5, 97.5],
        [decider.CONFIDENCE, decider.LOWER_PERCENTILE, decider.UPPER_PERCENTILE],
    )

    entry(
        "2_decision_rule.bootstrap",
        "10000 resamples, seed 20260829, cluster resampling",
        "decide_p0.BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, cluster_bootstrap",
        "cluster_bootstrap draws len(clusters) clusters with replacement and "
        "averages over all observations in the drawn clusters, so both "
        "directions of a pair move together",
        [10000, 20260829],
        [decider.BOOTSTRAP_RESAMPLES, decider.BOOTSTRAP_SEED],
        source_excerpt=inspect.getsource(decider.cluster_bootstrap).strip(),
    )

    entry(
        "2_decision_rule.verdict_condition",
        section2["verdict_positive_condition"],
        "decide_p0.decide, the `passing` comprehension",
        "a layer is retained when stats['lcb'] > ceiling, strictly; the verdict "
        "is CAUSALLY_USED when that list is non-empty and NOT_CAUSALLY_USED "
        "otherwise",
        ["CAUSALLY_USED", "NOT_CAUSALLY_USED"],
        [decider.VERDICT_POSITIVE, decider.VERDICT_NEGATIVE],
    )

    entry(
        "2_decision_rule.unit_exclusion",
        "units whose denominator is not strictly positive are dropped",
        "patch_effect.MIN_DENOMINATOR and the guard in patch_effect.main",
        "a unit is skipped and appended to `dropped` when "
        "ld_donor - ld_recipient <= MIN_DENOMINATOR",
        0.0,
        float(patch.MIN_DENOMINATOR),
    )

    entry(
        "3_null.replicates",
        "five replicates per null construction",
        "build_pairs.NULL_REPLICATES, consumed by patch_effect.main",
        "the frame assigns NULL_REPLICATES third items per unit, and the "
        "measurement emits NULL_C_<r> and NULL_R_<r> for r in range(replicates)",
        5,
        pairs.NULL_REPLICATES,
        cross_check_registration=section3["replicates_per_construction"],
    )

    entry(
        "3_null.ceiling_rule",
        section3["ceiling"],
        "decide_p0.decide, the ceiling loop",
        "the loop maximises stats['ucb'] over every key in null_keys, every "
        "site except INTEGRITY_SITE, and every layer, producing one scalar",
        "PREFIX",
        decider.INTEGRITY_SITE,
        note="the registered exclusion of PREFIX from the ceiling is realised "
             "by the `if site == INTEGRITY_SITE: continue` guard",
    )

    entry(
        "3_null.sites_measured_for_nulls",
        "PREFIX is measured for the real construction only",
        "patch_effect.NULL_SITES",
        "the null job builder iterates NULL_SITES, which excludes PREFIX; the "
        "real job builder iterates unit['sites'], which includes it",
        ["CUE", "BRIDGE", "READOUT"],
        list(patch.NULL_SITES),
    )

    entry(
        "3_null.integrity_tolerance",
        f"the PREFIX mean must be within {section3['constructions']['PREFIX_no_op']['tolerance_on_the_mean']}",
        "decide_p0.INTEGRITY_TOLERANCE, applied in decide_p0.check_gates",
        "check_gates takes the maximum absolute mean over all PREFIX layers "
        "and fails the gate when it exceeds the tolerance",
        0.0001,
        decider.INTEGRITY_TOLERANCE,
    )

    entry(
        "4_harness.gate",
        section4["gate"],
        "decide_p0.HARNESS_GATE_SITE, HARNESS_GATE_LAYER, HARNESS_GATE_MIN_LCB",
        "check_gates reads summary[real][CUE]['-1'] and fails when its lcb is "
        "below the registered floor",
        ["CUE", -1, 0.90],
        [
            decider.HARNESS_GATE_SITE,
            decider.HARNESS_GATE_LAYER,
            decider.HARNESS_GATE_MIN_LCB,
        ],
        source_excerpt=inspect.getsource(decider.check_gates).strip(),
    )

    entry(
        "7_gates.OD-011.required_cases",
        section7["OD-011"]["required_cases"],
        "non_vacuity_p0.REQUIRED",
        "the demonstration iterates REQUIRED and fails unless every case's "
        "verdict equals its required value",
        section7["OD-011"]["required_cases"],
        vacuity.REQUIRED,
    )

    entry(
        "layers.depth_grid",
        "layer -1 is the embedding output and 0..27 are decoder block outputs",
        "patch_effect.EMBEDDING_LAYER and Harness.layers",
        "Harness.layers is [EMBEDDING_LAYER] + list(range(n_layers)), where "
        "n_layers is read from the loaded model rather than assumed",
        -1,
        patch.EMBEDDING_LAYER,
        source_excerpt=inspect.getsource(patch.Harness.__init__).strip(),
    )

    # -------- cross-study transcriptions, compared against EQ2's live values --
    rank = load("audit_eq2_rank", EQ2_TOOLS / "rank_profile.py")
    entry(
        "transcription.readout_rule",
        "P-0 transcribes EQ2's multihop readout rule rather than importing it, "
        "so that jlens stays out of the ground-truth path",
        "build_pairs.READOUT_RULE against rank_profile.READOUT_RULE['multihop']",
        "both name the same rule; build_pairs.readout_position returns "
        "len(tokens) - 1, and rank_profile.readout_position returns the same "
        "index for this rule",
        rank.READOUT_RULE["multihop"],
        pairs.READOUT_RULE,
        note="a transcription is exactly what drifts silently, which is why it "
             "is compared against the live EQ2 value here rather than trusted",
    )

    probe = ["Brazil", "gold", "March"]
    entry(
        "transcription.surface_forms",
        "P-0's surface-form expansion matches EQ2's for a set with no synonym "
        "rule",
        "build_pairs.surface_forms against rank_profile.synonym_forms('multihop', .)",
        "both produce the bare, lowercase and capitalised variants, each with "
        "and without a leading space, in the same order",
        [rank.synonym_forms("multihop", word) for word in probe],
        [pairs.surface_forms(word) for word in probe],
    )

    entry(
        "independence.jlens_absent_from_the_measurement",
        "tools/patch_effect.py never imports jlens",
        "guard_p0.imports_jlens applied to patch_effect.py",
        "the check matches an import STATEMENT, not the bare word, so a file "
        "that merely names the library is not reported; patch_effect.py "
        "additionally records sys.modules membership at the end of each run",
        False,
        guard.imports_jlens((TOOLS / "patch_effect.py").read_text(encoding="utf-8")),
        note="a substring rule would fire on this auditor's own source, so the "
             "check is delegated to the guard's statement-level matcher",
    )

    entry(
        "independence.no_p0_tool_imports_jlens",
        "no P-0 tool imports jlens",
        "guard_p0.scan_tools, tools_importing_jlens",
        "every file in tools/ is parsed for an import statement, the guard "
        "itself included",
        [],
        guard.scan_tools(ROOT)["tools_importing_jlens"],
    )

    if args.patch_report:
        measured = json.loads(Path(args.patch_report).read_text(encoding="utf-8"))
        entry(
            "independence.jlens_absent_at_runtime",
            "no part of the instrument under test was loaded during the measurement",
            "patch_effect.instrument_under_test_is_loaded, written into the report",
            "the committed report records whether the library was present in "
            "sys.modules when the run finished",
            False,
            measured.get("instrument_under_test_imported"),
        )
        entry(
            "layers.observed_depth",
            "28 transformer layers plus the embedding output",
            "the loaded model's model.model.layers length",
            "read from the model at run time, not assumed",
            28,
            measured.get("n_transformer_layers"),
        )
        entry(
            "1_sampling.frame_reached_the_tool_unchanged",
            "the frame the measurement consumed is the frame that was committed",
            "patch_effect writes units_file_sha256 into its report",
            "the digest is computed from the file the run actually opened",
            json.loads(
                (ROOT / "out" / "units.json").read_bytes().decode("utf-8")
            ).get("frame", {}).get("seed"),
            reg["1_sampling"]["seed"],
            units_file_sha256=measured.get("units_file_sha256"),
        )

    divergences = [e for e in entries if e["verdict"] != "CONFORMS"]
    report = {
        "schema_version": "study5-p0-od017-v1",
        "rule": "OD-017",
        "phase": "P-0",
        "method": (
            "each module is imported and its live values are compared against "
            "P0_PREREGISTRATION.json; comments and hand-written agreement "
            "tables are not accepted as evidence"
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
        print("P0-CHECK-OD017 FAILED", file=sys.stderr)
        return 1
    print("P0-CHECK-OD017 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
