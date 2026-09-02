#!/usr/bin/env python3
"""Recompute the descriptive quantities used in REPORT.md.

This script reads only committed, post-execution artifacts.  It never reads model
weights, never mutates source data, and performs no model inference.  The default
mode writes a canonical JSON summary and two SVG figures; ``--check`` recomputes
the summary in memory and verifies that the committed JSON is current.

The inferential boundary is intentionally narrow:

* Study 2 exact binomial tails reproduce its preregistered feasibility gate.
* Wilson intervals for Study 4F-M1 are descriptive uncertainty intervals added by
  this report; they are not new protocol decisions.
* Study 5 precision ratios describe two committed objects and are not estimates of
  a population-level effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "analysis" / "report_metrics.json"
FIGURE_DIR = ROOT / "figures"
SCRIPT_VERSION = "1.0"


def read_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_jsonl(relative: str) -> list[dict[str, Any]]:
    path = ROOT / relative
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256_file(relative: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_binomial_upper_tail(n: int, successes: int, p: float) -> float:
    return sum(
        math.comb(n, k) * p**k * (1.0 - p) ** (n - k)
        for k in range(successes, n + 1)
    )


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    proportion = successes / n
    denominator = 1.0 + z * z / n
    centre = (proportion + z * z / (2.0 * n)) / denominator
    half_width = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / n + z * z / (4.0 * n * n))
        / denominator
    )
    return [centre - half_width, centre + half_width]


def ensure_close(actual: float, expected: float, label: str, tolerance: float = 1e-12) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise RuntimeError(f"{label}: expected {expected!r}, recomputed {actual!r}")


def study1_summary() -> dict[str, Any]:
    relative = "studies/study1/terminal_manifest.json"
    manifest = read_json(relative)
    e0 = manifest["s3_e0"]
    if e0["lens_operations"] != 0:
        raise RuntimeError("Study 1 terminal manifest unexpectedly reports lens operations")
    return {
        "source": relative,
        "source_sha256": sha256_file(relative),
        "scientific_disposition": manifest["scientific_disposition"],
        "tokenizer_calls": e0["tokenizer_calls"],
        "model_forwards": e0["model_forwards"],
        "lens_operations": e0["lens_operations"],
        "development_counts": e0["development_counts"],
        "confirmation_counts": e0["confirmation_counts"],
        "claim_boundary": manifest["claim_boundary"],
    }


def study2_summary() -> dict[str, Any]:
    rows_relative = "studies/study2/stage_bd/stage_bd_development_summaries.jsonl"
    decision_relative = "studies/study2/stage_bd/stage_bd_gate_a_decision.json"
    rows = read_jsonl(rows_relative)
    decision = read_json(decision_relative)
    families: dict[str, Any] = {}
    for family in ("permutation_chain", "affine_mod10"):
        selected = [
            row
            for row in rows
            if row["model_role"] == "target"
            and row["arm"] == "NT"
            and row["family"] == family
            and row["depth"] in (2, 3)
        ]
        successes = sum(row["correct"] for row in selected)
        n = sum(row["n"] for row in selected)
        upper_tail = exact_binomial_upper_tail(n, successes, 0.25)
        expected = {
            "permutation_chain": (25, 128, 0.9403523926144965),
            "affine_mod10": (33, 128, 0.4526854444021635),
        }[family]
        if (successes, n) != expected[:2]:
            raise RuntimeError(f"Study 2 {family} count drift: {(successes, n)}")
        ensure_close(upper_tail, expected[2], f"Study 2 {family} upper tail")
        families[family] = {
            "correct": successes,
            "n": n,
            "accuracy": successes / n,
            "exact_binomial_upper_tail": upper_tail,
            "pass_threshold_correct": 43,
            "additional_correct_needed": 43 - successes,
            "passed": successes >= 43,
        }
    return {
        "sources": [rows_relative, decision_relative],
        "source_sha256": {
            rows_relative: sha256_file(rows_relative),
            decision_relative: sha256_file(decision_relative),
        },
        "registered_null_accuracy": 0.25,
        "registered_alpha_one_sided": 0.025,
        "registered_conjunctive_rule": "both target families must pass",
        "families": families,
        "overall_gate_pass": decision["overall_gate_pass"],
        "development_rows_total": 3072,
        "generated_tokens": 0,
    }


def study4_summary() -> dict[str, Any]:
    relative = "studies/study4f/execution-m1/cell_results.json"
    frame = read_json(relative)
    cells: list[dict[str, Any]] = []
    for source in frame["cells"]:
        cells.append(
            {
                "cell_id": source["cell_id"],
                "checkpoint_role": source["checkpoint_role"],
                "checkpoint_repository": source["checkpoint_repository"],
                "depth": source["depth"],
                "route": source["route"],
                "correct": source["correct"],
                "n": source["n"],
                "accuracy": source["correct"] / source["n"],
                "unparseable": source["unparseable"],
                "wilson_95": wilson_interval(source["correct"], source["n"]),
                "pass_boundary": source["pass_boundary"],
                "passed": source["passes"],
            }
        )
    paired_e0 = [cell for cell in cells if cell["route"] == "W1_RAW_DIRECT"]
    if sum(cell["n"] for cell in paired_e0) != 240:
        raise RuntimeError("Study 4 paired E0 total drifted from 240")
    if sum(cell["unparseable"] for cell in paired_e0) != 240:
        raise RuntimeError("Study 4 paired E0 rows are no longer all unparseable")
    return {
        "source": relative,
        "source_sha256": sha256_file(relative),
        "cells_executed": frame["cells_executed"],
        "cells_skipped": frame["cells_skipped"],
        "cells": cells,
        "paired_7b_14b_raw_direct_total": 240,
        "paired_7b_14b_raw_direct_unparseable": 240,
        "target_checkpoint_run": False,
        "interval_note": "Wilson 95% intervals are report-level descriptive additions, not registered gate inputs.",
    }


def load_object_proof(phase: str) -> dict[str, Any]:
    relative = f"studies/study5/{phase}/out/object_proof.json"
    proof = read_json(relative)
    return {
        "source": relative,
        "source_sha256": sha256_file(relative),
        "determination": proof["determination"],
        "n_items": proof["n_items"],
        "full_accuracy": proof["requirement_4_accuracy"]["observed"],
        "ablated_accuracy": proof["requirement_3_anti_retrieval"][
            "observed_ablated_accuracy"
        ],
        "accuracy_drop": proof["requirement_3_anti_retrieval"]["drop"],
        "accuracy_floor": proof["requirement_4_accuracy"]["floor"],
        "chance_accuracy": proof["requirement_4_accuracy"]["chance"],
    }


def load_baseline_pair(phase: str) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    source_sha256: dict[str, str] = {}
    for dtype, filename in (("bfloat16", "baseline_bf16.json"), ("float32", "baseline_fp32.json")):
        relative = f"studies/study5/{phase}/out/{filename}"
        frame = read_json(relative)
        source_sha256[relative] = sha256_file(relative)
        outputs[dtype] = {
            "source": relative,
            "n_units": frame["n_units"],
            "old_batch_of_one_baseline_shift_mean_logits": frame[
                "old_batch_of_one_baseline_shift_logits"
            ]["mean"],
            "old_batch_of_one_baseline_shift_worst_abs_logits": frame[
                "old_batch_of_one_baseline_shift_logits"
            ]["worst_abs"],
            "repaired_worst_abs_mean_logits": frame["worst_abs_mean_logits_over_all"],
            "repaired_worst_abs_mean_normalised": frame[
                "worst_abs_mean_normalised_over_all"
            ],
            "verdict": frame["verdict"],
        }
    ratio = (
        outputs["bfloat16"]["old_batch_of_one_baseline_shift_mean_logits"]
        / outputs["float32"]["old_batch_of_one_baseline_shift_mean_logits"]
    )
    return {
        "source_sha256": source_sha256,
        "bfloat16": outputs["bfloat16"],
        "float32": outputs["float32"],
        "mean_shift_ratio_bfloat16_over_float32": ratio,
    }


def study5_summary() -> dict[str, Any]:
    p0c = load_object_proof("validation-p0c")
    p0c2 = load_object_proof("validation-p0c2")
    ensure_close(p0c["full_accuracy"], 0.75625, "P-0c clean accuracy")
    ensure_close(p0c2["full_accuracy"], 0.840625, "P-0c-2 clean accuracy")
    prime = load_baseline_pair("validation-p0-prime")
    p0c2_baseline = load_baseline_pair("validation-p0c2")
    ensure_close(
        prime["bfloat16"]["old_batch_of_one_baseline_shift_mean_logits"],
        0.62373046875,
        "P-0-prime bfloat16 batch-width shift",
    )
    ensure_close(
        p0c2_baseline["bfloat16"]["old_batch_of_one_baseline_shift_mean_logits"],
        0.1109375,
        "P-0c-2 bfloat16 batch-width shift",
    )
    nonvacuity_relative = (
        "studies/study5/validation-p0c2/measurement/out/c1_nonvacuity.json"
    )
    nonvacuity = read_json(nonvacuity_relative)
    cases = {
        key: {
            "passed": value["passed"],
            "max_mean": value["max_mean"],
            "worst_abs_mean": value["worst_abs_mean"],
        }
        for key, value in nonvacuity["cases"].items()
    }
    return {
        "object_proofs": {"P-0c": p0c, "P-0c-2": p0c2},
        "batch_width_numeric_checks": {"P-0-prime": prime, "P-0c-2": p0c2_baseline},
        "C1_real_pipeline_nonvacuity": {
            "source": nonvacuity_relative,
            "source_sha256": sha256_file(nonvacuity_relative),
            "n_units": nonvacuity["n_units"],
            "all_passed": nonvacuity["all_passed"],
            "cases": cases,
        },
    }


def build_metrics() -> dict[str, Any]:
    return {
        "schema_version": "jspace-report-derived-metrics/v1",
        "script_version": SCRIPT_VERSION,
        "derivation_scope": "descriptive recomputation from committed artifacts only",
        "no_model_execution": True,
        "study1": study1_summary(),
        "study2": study2_summary(),
        "study4f_m1": study4_summary(),
        "study5": study5_summary(),
    }


def canonical_json(metrics: dict[str, Any]) -> str:
    return json.dumps(metrics, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def normalise_svg(path: Path) -> None:
    """Remove generator-only line-end spaces so ``git diff --check`` stays clean."""
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def render_figures(metrics: dict[str, Any]) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Figure generation requires the pinned packages in "
            "analysis/requirements-report.txt"
        ) from exc

    matplotlib.rcParams.update(
        {
            "svg.hashsalt": "jspace-report-v1",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "figure.dpi": 150,
        }
    )
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    # Figure 1: every executed Study 4F-M1 cell, with explicit missing E0 cells.
    cells = metrics["study4f_m1"]["cells"]
    labels = ["7B D2", "7B D3", "14B D2", "14B D3", "32B D2", "32B D3"]
    roles = ["RP_B1", "RP_B1", "RP_B2", "RP_B2", "RP_B3", "RP_B3"]
    depths = ["D2", "D3", "D2", "D3", "D2", "D3"]

    def find_cell(role: str, depth: str, route: str) -> dict[str, Any] | None:
        for cell in cells:
            if (
                cell["checkpoint_role"] == role
                and cell["depth"] == depth
                and cell["route"] == route
            ):
                return cell
        return None

    cot = [
        100.0 * find_cell(role, depth, "C1_LONG_GENERATED_COT_HEADROOM")["accuracy"]
        for role, depth in zip(roles, depths)
    ]
    raw = []
    for role, depth in zip(roles, depths):
        cell = find_cell(role, depth, "W1_RAW_DIRECT")
        raw.append(None if cell is None else 100.0 * cell["accuracy"])

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10.4, 4.9))
    cot_bars = ax.bar(
        x - width / 2,
        cot,
        width,
        label="Generated CoT headroom",
        color="#2F6B8A",
    )
    raw_positions = [index for index, value in enumerate(raw) if value is not None]
    raw_values = [raw[index] for index in raw_positions]
    raw_bars = ax.bar(
        np.array(raw_positions) + width / 2,
        raw_values,
        width,
        label="Raw direct (exact answer + EOS)",
        color="#D28E2D",
    )
    ax.set_ylim(0, 105)
    ax.set_ylabel("Correct continuations (%)")
    ax.set_xticks(x, labels)
    ax.set_title("Study 4F-M1 developmental interface qualification")
    ax.grid(axis="y", alpha=0.25, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    for bar, value in zip(cot_bars, cot):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.2,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    for bar in raw_bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            1.5,
            "0/60\nunparseable",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )
    for index in (4, 5):
        ax.text(index + width / 2, 1.5, "not run", ha="center", va="bottom", fontsize=8)
    ax.text(
        0.01,
        -0.19,
        "Rates are developmental gate observations, not evidence about J-space or hidden reasoning.",
        transform=ax.transAxes,
        fontsize=8.5,
    )
    fig.tight_layout()
    interface_svg = FIGURE_DIR / "interface_gate_results.svg"
    fig.savefig(
        interface_svg,
        format="svg",
        bbox_inches="tight",
        metadata={"Creator": "analysis/reproduce_report.py", "Date": None},
    )
    normalise_svg(interface_svg)
    fig.savefig(
        FIGURE_DIR / "interface_gate_results.png",
        format="png",
        dpi=180,
        bbox_inches="tight",
        metadata={"Software": "analysis/reproduce_report.py"},
    )
    plt.close(fig)

    # Figure 2: two independently committed objects, shown on a log scale.
    checks = metrics["study5"]["batch_width_numeric_checks"]
    phase_labels = ["P-0-prime\n(40 units bf16 / 40 fp32)", "P-0c-2\n(160 units bf16 / 60 fp32)"]
    bf16 = [
        checks[phase]["bfloat16"]["old_batch_of_one_baseline_shift_mean_logits"]
        for phase in ("P-0-prime", "P-0c-2")
    ]
    fp32 = [
        checks[phase]["float32"]["old_batch_of_one_baseline_shift_mean_logits"]
        for phase in ("P-0-prime", "P-0c-2")
    ]
    ratios = [
        checks[phase]["mean_shift_ratio_bfloat16_over_float32"]
        for phase in ("P-0-prime", "P-0c-2")
    ]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    bf_bars = ax.bar(x - width / 2, bf16, width, label="bfloat16", color="#A23B3B")
    fp_bars = ax.bar(x + width / 2, fp32, width, label="float32", color="#4C7A57")
    ax.set_yscale("log")
    ax.set_ylim(1e-6, 2.0)
    ax.set_ylabel("Mean batch-width baseline shift (logits; log scale)")
    ax.set_xticks(x, phase_labels)
    ax.set_title("Batch-width-dependent baseline shift before repair")
    ax.grid(axis="y", which="both", alpha=0.22, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    for bar, value, ratio in zip(bf_bars, bf16, ratios):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 1.35,
            f"{value:.3g}\n{ratio:,.0f}x fp32",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    for bar, value in zip(fp_bars, fp32):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 1.5,
            f"{value:.2e}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.text(
        0.01,
        -0.22,
        "After the three-part batch-matched repair, maximum mean no-op deviation was exactly 0\n"
        "for both dtypes on both objects. Ratios are descriptive; unit counts differ in P-0c-2.",
        transform=ax.transAxes,
        fontsize=8.5,
    )
    fig.tight_layout()
    numeric_svg = FIGURE_DIR / "batch_width_numeric_shift.svg"
    fig.savefig(
        numeric_svg,
        format="svg",
        bbox_inches="tight",
        metadata={"Creator": "analysis/reproduce_report.py", "Date": None},
    )
    normalise_svg(numeric_svg)
    fig.savefig(
        FIGURE_DIR / "batch_width_numeric_shift.png",
        format="png",
        dpi=180,
        bbox_inches="tight",
        metadata={"Software": "analysis/reproduce_report.py"},
    )
    plt.close(fig)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify analysis/report_metrics.json without writing any file",
    )
    args = parser.parse_args(argv)
    metrics = build_metrics()
    rendered = canonical_json(metrics)
    if args.check:
        if not METRICS_PATH.exists():
            raise RuntimeError(f"missing derived summary: {METRICS_PATH}")
        committed = METRICS_PATH.read_text(encoding="utf-8")
        if committed != rendered:
            raise RuntimeError(
                "analysis/report_metrics.json is stale; run analysis/reproduce_report.py"
            )
        print("PASS: report metrics reproduce exactly; no model execution performed")
        return 0

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(rendered, encoding="utf-8")
    render_figures(metrics)
    print(f"WROTE: {METRICS_PATH.relative_to(ROOT)}")
    print("WROTE: figures/interface_gate_results.svg")
    print("WROTE: figures/interface_gate_results.png")
    print("WROTE: figures/batch_width_numeric_shift.svg")
    print("WROTE: figures/batch_width_numeric_shift.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
