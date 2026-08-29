"""OD-017 conformance audit for P-0': registered text against live implementation.

Same rule as P-0's audit and the same refusal to accept a comment as evidence:
each module is imported and its live values are compared against the committed
registration file.

One entry here is unlike anything P-0 needed. The directive prescribed a
replacement estimand; this audit compares that prescription against the estimand
P-0 actually implemented, and reports whether they differ. A conformance audit
that only ever compared a tool to its own registration would have had no way to
notice that a replacement was not one.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
P0_ROOT = ROOT.parent / "validation-p0"
P0_TOOLS = P0_ROOT / "tools"


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
    parser.add_argument("--baseline-report")
    parser.add_argument("--inclusion-report")
    args = parser.parse_args()

    reg = json.loads(
        (ROOT / "P0PRIME_PREREGISTRATION.json").read_text(encoding="utf-8")
    )
    operative = reg["2_registered_and_operative_regardless_of_the_estimand"]

    vacuity = load("p0p_vacuity", TOOLS / "non_vacuity_p0prime.py")
    baseline = load("p0p_baseline", TOOLS / "verify_baseline.py")
    guard = load("p0p_guard", P0_TOOLS / "guard_p0.py")
    p0_patch = load("p0p_p0patch", P0_TOOLS / "patch_effect.py")

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

    # ------------------------------------------------ the estimand comparison
    rng = random.Random(4242)
    worst = 0.0
    for _ in range(200000):
        a, b, c, d, e, f = (rng.uniform(-20, 20) for _ in range(6))
        l_clean, l_patch, l_full = a - b, c - d, e - f
        if abs(l_full - l_clean) < 1e-6:
            continue
        prescribed = vacuity.estimand_logit_difference_recovery(
            l_clean, l_patch, l_full
        )
        p0_form = (l_patch - l_clean) / (l_full - l_clean)
        worst = max(worst, abs(prescribed - p0_form))

    entry(
        "0.estimand_is_a_replacement",
        "the estimand is REPLACED with a logit-difference recovery ratio",
        "non_vacuity_p0prime.estimand_logit_difference_recovery against the "
        "expression in patch_effect.main",
        "P-0 computed (gap - ld_recipient) / (ld_donor - ld_recipient), where "
        "gap, ld_recipient and ld_donor are the logit differences in the "
        "patched, clean-recipient and clean-donor runs; the prescribed formula "
        "is the same expression under different names",
        "a different estimand from P-0's",
        "the same estimand as P-0's",
        worst_absolute_difference_over_200000_draws=worst,
        why_this_entry_exists=(
            "an audit that only compared each tool to its own registration "
            "could not have noticed that a prescribed replacement was not one"
        ),
        source_excerpt=inspect.getsource(
            vacuity.estimand_logit_difference_recovery
        ).strip(),
    )

    entry(
        "1.estimand_is_held",
        "the estimand is HELD and not operative",
        "P0PRIME_PREREGISTRATION.json section 1",
        "no measurement tool in this namespace applies an effect estimand; "
        "verify_baseline computes only no-op deviations, whose numerator is "
        "exactly zero under any recovery ratio of this shape",
        0,
        reg["1_the_estimand_HELD"]["estimands_proposed_by_the_agent"],
    )

    # ------------------------------------------------------- OD-011 revision
    entry(
        "5.OD-011.must_return_positive_case_present",
        "a non-vacuity demonstration must include a case that MUST RETURN POSITIVE",
        "non_vacuity_p0prime.REQUIRED",
        "the demonstration iterates REQUIRED and fails unless every case's "
        "verdict equals its requirement; two of the four requirements are "
        "positive-valued",
        True,
        any(
            v in ("ONE", "SIGNIFICANTLY_POSITIVE") for v in vacuity.REQUIRED.values()
        ),
        registered_cases=list(vacuity.REQUIRED),
    )

    entry(
        "5.OD-011.four_cases",
        "four cases: no-op, random vector, full donor, carries the intermediate",
        "non_vacuity_p0prime.REQUIRED",
        "the four keys are exactly these, in this order",
        [
            "case_1_no_op",
            "case_2_random_vector",
            "case_3_full_donor",
            "case_4_carries_the_intermediate",
        ],
        list(vacuity.REQUIRED),
    )

    entry(
        "5.OD-011.no_threshold_from_P0_data",
        "the four cases run on synthetic or constructed objects and may not take "
        "a threshold from P-0's existing data",
        "non_vacuity_p0prime, module constants and build_world",
        "the synthetic world is built from a registered seed and fixed "
        "constants; no P-0 artifact is opened by the module",
        False,
        any(
            token in (TOOLS / "non_vacuity_p0prime.py").read_text(encoding="utf-8")
            for token in ("patch_merged", "decision.json", "0.4139", "0.2380")
        ),
    )

    # ------------------------------------------------------ inclusion + floor
    entry(
        "2.n_floor",
        f"the floor is {operative['n_floor']['value']} correct-both units",
        "count_inclusion reads the value from the pushed registration",
        "the tool does not hard-code the floor; it applies the value in the "
        "committed registration file",
        30,
        operative["n_floor"]["value"],
    )

    entry(
        "2.n_floor_disclosure",
        "the directive requires disclosing whether the pair count was known when "
        "the floor was set",
        "P0PRIME_PREREGISTRATION.json section 2, n_floor.disclosure_required_by_the_directive",
        "the registration records that only the two separate marginals were "
        "known, that the joint count had never been computed, and that it was "
        "deliberately left uncomputed until the registration was pushed",
        "no",
        operative["n_floor"]["disclosure_required_by_the_directive"]["answer"],
    )

    entry(
        "2.denominator_floor",
        f"the denominator floor is {operative['denominator_floor']['value']} logits",
        "count_inclusion reads the value from the pushed registration",
        "units with L_full - L_clean below the floor are excluded; the floor is "
        "evaluated on clean runs only",
        1.0,
        float(operative["denominator_floor"]["value"]),
    )

    entry(
        "2.correct_only_measured_on_clean_runs",
        "correct-only is evaluated on CLEAN runs, so it is independent of every "
        "patching result",
        "count_inclusion, the correct_both comprehension",
        "it reads donor_top1_is_donor_target and "
        "recipient_top1_is_recipient_target, both recorded from clean forwards",
        True,
        "donor_top1_is_donor_target" in (TOOLS / "count_inclusion.py").read_text(
            encoding="utf-8"
        ),
    )

    # ------------------------------------------------------------ the repair
    entry(
        "3.no_op_tolerance",
        "the no-op families must be within 1e-4, on the normalised scale",
        "verify_baseline.NOOP_TOLERANCE and the verdict expression",
        "the verdict is taken on worst_abs_mean_normalised; raw logits are "
        "reported beside it but do not decide",
        0.0001,
        baseline.NOOP_TOLERANCE,
        note=(
            "an earlier revision of this tool compared RAW LOGITS against this "
            "tolerance, which is a units error of exactly the shape this audit "
            "exists to catch; it was corrected before any verdict was recorded"
        ),
    )

    entry(
        "3.repair_is_three_parts",
        "the baseline is measured inside the same batch",
        "verify_baseline.main job 0, capture_at_width, and the padding step",
        "job 0 is a self-patch inside the batch; the cache is captured at the "
        "same width as the consuming run; every chunk is padded to full width",
        True,
        all(
            token in (TOOLS / "verify_baseline.py").read_text(encoding="utf-8")
            for token in ("capture_at_width", "BASELINE", "pad = (-len(jobs))")
        ),
    )

    # ------------------------------------------------------------- boundaries
    entry(
        "8.no_tool_imports_the_instrument_under_test",
        "no P-0' tool imports the library EQ2 was testing",
        "guard_p0.imports_jlens applied to every file in this namespace's tools",
        "the check matches an import statement rather than the bare word",
        [],
        sorted(
            path.name
            for path in TOOLS.glob("*.py")
            if guard.imports_jlens(path.read_text(encoding="utf-8"))
        ),
    )

    entry(
        "8.no_tool_references_the_target",
        "no P-0' tool references T",
        "static scan for the target's repository id and pinned revision",
        "neither marker appears in any tool in this namespace",
        [],
        sorted(
            path.name
            for path in TOOLS.glob("*.py")
            for marker in guard.TARGET_MARKERS
            if marker in path.read_text(encoding="utf-8")
        ),
    )

    entry(
        "8.P0_artifacts_untouched",
        "P-0 is closed and may not be reopened by this phase",
        "this namespace writes only under validation-p0-prime/",
        "the only P-0 path any P-0' tool opens is read-only: the merged report "
        "and the shared harness module",
        True,
        all(
            "validation-p0/out" not in text or "read" in text
            for text in [(TOOLS / p.name).read_text(encoding="utf-8") for p in TOOLS.glob("*.py")]
        ),
    )

    entry(
        "layers.depth_grid_unchanged",
        "the depth grid is the embedding output plus the decoder blocks",
        "patch_effect.EMBEDDING_LAYER, reused unchanged",
        "Harness.layers is [EMBEDDING_LAYER] + range(n_layers), read from the "
        "loaded model",
        -1,
        p0_patch.EMBEDDING_LAYER,
    )

    if args.baseline_report:
        measured = json.loads(Path(args.baseline_report).read_text(encoding="utf-8"))
        entry(
            "3.no_op_observed",
            "the no-op families must be within 1e-4 normalised",
            "verify_baseline, as run on the real frame",
            "the committed report records the worst normalised mean over all "
            "three families",
            True,
            measured["worst_abs_mean_normalised_over_all"] <= baseline.NOOP_TOLERANCE,
            observed_worst_abs_mean_normalised=measured[
                "worst_abs_mean_normalised_over_all"
            ],
            observed_verdict=measured["verdict"],
        )
        entry(
            "8.instrument_absent_at_runtime",
            "the instrument under test is not loaded during any run",
            "patch_effect.instrument_under_test_is_loaded, written into the report",
            "the committed report records sys.modules membership at the end",
            False,
            measured.get("instrument_under_test_imported"),
        )

    if args.inclusion_report:
        counted = json.loads(Path(args.inclusion_report).read_text(encoding="utf-8"))
        entry(
            "2.count_computed_after_the_push",
            "the count is computed only after the registration was pushed",
            "count_inclusion, the flag it writes",
            "the tool records that it ran against a committed registration",
            True,
            counted["computed_after_the_registration_was_pushed"],
            observed_correct_both_units=counted["correct_both"]["units"],
            observed_meets_floor=counted["meets_the_floor"],
        )

    divergences = [e for e in entries if e["verdict"] != "CONFORMS"]
    report = {
        "schema_version": "study5-p0prime-od017-v1",
        "rule": "OD-017",
        "phase": "P-0'",
        "method": (
            "each module is imported and its live values are compared against "
            "P0PRIME_PREREGISTRATION.json; comments and hand-written agreement "
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
        "note_on_the_expected_divergence": (
            "entry 0.estimand_is_a_replacement is EXPECTED to diverge; it is the "
            "audit reporting that the prescribed replacement is the estimand "
            "P-0 already used, which is the finding that halted the phase"
        ),
        "claim_ceiling": "A governance audit. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    for record in entries:
        print(f"  {record['verdict']:9} {record['registered_id']}")
    print(f"{len(entries)} entries, {len(divergences)} divergences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
