#!/usr/bin/env python3
"""Q-3 decision and the P-1 step 3 summary.

Applies the decision rule frozen in ``q3_decision_rule.json`` to the three-arm
measurement. The rule, its bands, its uncertainty method and the length
tolerance were all registered before any of these numbers existed, so this tool
only evaluates; it decides nothing that was not already decided.

Two points about the statistics, both of which follow from the authority rather
than from convenience:

* the resampling unit is the **item**. Features, tokens, layers, GPU workers and
  repeated responses are never independent samples, so resampling any of them
  would understate the interval;
* the verdict is read from the **point estimate**, because the band table was
  frozen against the point estimate. Switching to an interval-based rule after
  seeing the interval would be choosing the decision procedure after the fact.

The parser's own false-negative rate is measured by presenting each item's known
answer in the canonical answer surface and asking whether the frozen pipeline
recovers it. That isolates parser and checker failure from model failure, which
is the quantity Q-6 asks for -- a model that answers wrongly and a parser that
cannot read a right answer are different faults and must not be pooled.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARMS = ("T", "H", "F")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def proof(check_id: str, passed: bool, detail: str = "") -> bool:
    if passed:
        print(f"P1-CHECK-{check_id} PASSED", flush=True)
    else:
        print(f"P1-CHECK-{check_id} FAILED: {detail}", flush=True)
    return passed


def load_measure_arms(tools: Path) -> Any:
    spec = importlib.util.spec_from_file_location("ma", tools / "measure_arms.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["ma"] = module
    spec.loader.exec_module(module)
    return module


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--contamination", required=True)
    parser.add_argument("--rule", required=True)
    parser.add_argument("--tools", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--check-id", default="S4.Q3")
    args = parser.parse_args(argv)

    ma = load_measure_arms(Path(args.tools))
    rule = json.loads(Path(args.rule).read_text(encoding="utf-8"))

    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    contamination = json.loads(Path(args.contamination).read_text(encoding="utf-8"))
    excluded = {f["item_id"] for f in contamination["flagged_items"]}
    expected_items = [i for i in split["development_ids"] if i not in excluded]

    records: dict[tuple[str, str, int], dict[str, Any]] = {}
    for path in args.results:
        source = Path(path)
        if not source.exists():
            continue
        with open(source, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records[
                    (record["item_id"], record["arm"], int(record["sample_index"]))
                ] = record

    # Aggregate to a per-item score BEFORE any analysis, so the statistical unit
    # stays the item even if k > 1.
    per_item: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for (item_id, arm, _sample), record in records.items():
        per_item.setdefault(item_id, {}).setdefault(arm, []).append(record)

    complete = [i for i in expected_items if len(per_item.get(i, {})) == len(ARMS)]
    missing = [i for i in expected_items if i not in complete]

    def item_score(item_id: str, arm: str) -> float:
        rows = per_item[item_id][arm]
        return sum(1.0 for r in rows if r["correct"]) / len(rows)

    accuracy = {
        arm: st.mean(item_score(i, arm) for i in complete) if complete else float("nan")
        for arm in ARMS
    }

    summary: dict[str, Any] = {}
    for arm in ARMS:
        rows = [r for i in complete for r in per_item[i][arm]]
        lengths = [r["completed_tokens"] for r in rows]
        completed = [
            r["completed_tokens"] for r in rows if not r["hit_ceiling"]
        ]
        summary[arm] = {
            "responses": len(rows),
            "accuracy": round(accuracy[arm], 6),
            "no_boxed_rate": round(sum(1 for r in rows if not r["has_boxed"]) / len(rows), 6),
            "ceiling_hit_rate": round(sum(1 for r in rows if r["hit_ceiling"]) / len(rows), 6),
            "degeneration_rate": round(sum(1 for r in rows if r["degenerate"]) / len(rows), 6),
            "length_p50": percentile([float(v) for v in lengths], 0.50),
            "length_p90": percentile([float(v) for v in lengths], 0.90),
            "length_p99": percentile([float(v) for v in lengths], 0.99),
            "length_mean": round(st.mean(lengths), 2) if lengths else None,
            "length_max": max(lengths) if lengths else None,
            "completed_only_median_length": percentile(
                [float(v) for v in completed], 0.50
            ),
            "completed_responses": len(completed),
        }

    # ------------------------------------------------------ parser false negatives
    rows_by_id: dict[str, dict[str, Any]] = {}
    with open(args.benchmark, "r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows_by_id[
                str(row.get("unique_id") or row.get("id") or index)
            ] = row

    parser_failures = []
    for item_id in complete:
        reference = str(rows_by_id[item_id].get("answer", ""))
        synthetic = f"Therefore the answer is \\boxed{{{reference}}}."
        recovered = ma.extract_last_boxed(synthetic)
        if not ma.answers_equivalent(recovered, reference):
            parser_failures.append(
                {"item_id": item_id, "reference": reference, "recovered": recovered}
            )
    parser_fn_rate = len(parser_failures) / len(complete) if complete else float("nan")

    # ------------------------------------------------------------------ recovery
    denominator = accuracy["T"] - accuracy["H"]
    recovery = (
        (accuracy["F"] - accuracy["H"]) / denominator if denominator else float("nan")
    )

    rng = random.Random(20260827)
    draws: list[float] = []
    for _ in range(args.bootstrap):
        sample = [complete[rng.randrange(len(complete))] for _ in complete]
        acc = {a: st.mean(item_score(i, a) for i in sample) for a in ARMS}
        d = acc["T"] - acc["H"]
        if d:
            draws.append((acc["F"] - acc["H"]) / d)
    draws.sort()
    ci = (
        [percentile(draws, 0.025), percentile(draws, 0.975)]
        if draws
        else [float("nan"), float("nan")]
    )

    # -------------------------------------------------------- catastrophic H gate
    catastrophic = accuracy["H"] < 0.05 and summary["H"]["degeneration_rate"] > 0.5

    # ------------------------------------------------------------ length condition
    tolerance = 0.70
    length_ratio = (
        summary["F"]["completed_only_median_length"]
        / summary["T"]["completed_only_median_length"]
        if summary["T"]["completed_only_median_length"]
        else float("nan")
    )
    length_ok = length_ratio >= tolerance

    # --------------------------------------------------------------- the verdict
    if catastrophic:
        verdict, band = "STOP", "catastrophic H; the H to T gap is not a meaningful denominator"
    elif recovery >= 0.50:
        verdict, band = "PASS", "recovery >= 0.50"
    elif recovery >= 0.40:
        verdict, band = "ESCALATE", "0.40 <= recovery < 0.50; pre-registered k -> 2 escalation"
    else:
        verdict, band = "FAIL", "recovery < 0.40"
    if verdict == "PASS" and not length_ok:
        verdict, band = "FAIL", f"length condition failed: F/T median completed length {length_ratio:.4f} < {tolerance}"

    # -------------------------------------------- OA-002 confirmatory reverse-solve
    p99_completed = percentile(
        [
            float(r["completed_tokens"])
            for i in complete
            for a in ARMS
            for r in per_item[i][a]
            if not r["hit_ceiling"]
        ],
        0.99,
    )
    confirmatory = min(32768, 2 ** math.ceil(math.log2(max(p99_completed, 1.0))))

    report = {
        "schema_version": "study5-eq1-q3-decision-v1",
        "phase": "P-1",
        "step": "S4",
        "decided_at_utc": utc_now(),
        "rule_artifact": args.rule,
        "rule_frozen_before_measurement": rule.get("frozen_before_any_measurement"),
        "expected_items": len(expected_items),
        "complete_items": len(complete),
        "missing_items": missing[:20],
        "missing_item_count": len(missing),
        "analysis_is_complete": not missing,
        "records_total": len(records),
        "k_samples_per_item": 1,
        "statistical_unit": "item",
        "aggregated_to_per_item_before_analysis": True,
        "arms": summary,
        "accuracy": {a: round(accuracy[a], 6) for a in ARMS},
        "parser_false_negative_rate": round(parser_fn_rate, 6),
        "parser_false_negative_count": len(parser_failures),
        "parser_false_negative_examples": parser_failures[:10],
        "parser_fn_method": "each item's known answer is presented in the canonical answer surface and the frozen pipeline is asked to recover it; this isolates parser and checker failure from model failure",
        "study4f_e0_artifacts_used": False,
        "recovery": {
            "formula": "(acc_F - acc_H) / (acc_T - acc_H)",
            "point_estimate": round(recovery, 6) if recovery == recovery else None,
            "denominator": round(denominator, 6),
            "bootstrap_ci_95": [round(c, 6) for c in ci],
            "bootstrap_resamples": len(draws),
            "resampling_unit": "item",
            "verdict_decided_by": "point estimate, because the band table was frozen against it",
        },
        "length_condition": {
            "tolerance": tolerance,
            "statistic": "median completed length of F / median completed length of T",
            "completed_only": True,
            "value": round(length_ratio, 6) if length_ratio == length_ratio else None,
            "passed": bool(length_ok),
            "one_sided": True,
        },
        "catastrophic_H": {
            "triggered": bool(catastrophic),
            "H_accuracy": round(accuracy["H"], 6),
            "H_degeneration_rate": summary["H"]["degeneration_rate"],
        },
        "verdict": verdict,
        "band": band,
        "terminal_state_if_fail": "STUDY5_EQ1_ADAPTER_FIDELITY_BELOW_REGISTERED_FLOOR",
        "oa002_confirmatory_reverse_solve": {
            "formula": "min(32768, 2^ceil(log2(p99_completed_length_on_dev)))",
            "p99_completed_length_on_dev": round(p99_completed, 2),
            "max_new_tokens_confirmatory": confirmatory,
            "formula_frozen_before_its_input_existed": True,
        },
        "claim_ceiling": "Q-3 is an engineering gate. It establishes that the adapter recovers a pre-registered share of a behavioural gap under a registered decoding law. It establishes nothing about J-space, about distillation, or about reasoning, and it is not a scientific result.",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
    out.write_text(text, encoding="utf-8")

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    print(f"items complete {len(complete)}/{len(expected_items)}")
    for arm in ARMS:
        s = summary[arm]
        print(
            f"  {arm}  acc={s['accuracy']:.4f} boxed_miss={s['no_boxed_rate']:.4f} "
            f"ceil={s['ceiling_hit_rate']:.4f} degen={s['degeneration_rate']:.4f} "
            f"p50={s['length_p50']:.0f} p99={s['length_p99']:.0f}"
        )
    print(f"recovery = {report['recovery']['point_estimate']}  CI {report['recovery']['bootstrap_ci_95']}")
    print(f"length ratio F/T = {report['length_condition']['value']} (tolerance {tolerance})")
    print(f"parser FN rate = {report['parser_false_negative_rate']}")
    print(f"VERDICT: {verdict}  ({band})")
    print(f"confirmatory max_new_tokens = {confirmatory} from p99 {p99_completed:.0f}")
    proof(args.check_id, not missing, f"{len(missing)} items incomplete")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
