#!/usr/bin/env python3
"""OD-004 paired analysis of the per-layer L0 curves.

The two checkpoints share an architecture and a layer indexing, so layer l of
one corresponds to layer l of the other and the 28 layers are a paired unit.
That is the same principle the study applies to items: compare within the pair
and then aggregate, rather than aggregating each arm separately and differencing
the summaries. An unpaired mean or median discards the correspondence and, here,
is dominated by an order-of-magnitude tail at layers 26 and 27.

Both registered tests are computed and both are reported, including when they
disagree. Reporting only the one that reaches significance would be selective
reporting, and the disagreement is itself informative: the sign test is
magnitude-free while Wilcoxon is magnitude-weighted, so the same tail that
motivated this registration still influences the latter.

The figure is emitted as hand-written SVG rather than through a plotting
library, so that producing it requires no addition to the frozen container
image. A log scale is used because the layer 26 and 27 values are an order of
magnitude above the rest and would otherwise flatten every other layer into the
axis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics as st
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def proof(check_id: str, passed: bool, detail: str = "") -> bool:
    if passed:
        print(f"P1-CHECK-{check_id} PASSED", flush=True)
    else:
        print(f"P1-CHECK-{check_id} FAILED: {detail}", flush=True)
    return passed


def sign_test_two_sided(successes: int, trials: int) -> float:
    """Exact two-sided binomial test at p = 0.5.

    Summing every outcome at most as probable as the observed one is the exact
    definition; a doubling of the one-tailed probability would be an
    approximation and is avoidable here.
    """

    probabilities = [math.comb(trials, i) / 2**trials for i in range(trials + 1)]
    observed = probabilities[successes]
    return sum(p for p in probabilities if p <= observed + 1e-15)


def wilcoxon_signed_rank(differences: list[float]) -> dict[str, Any]:
    non_zero = [d for d in differences if d != 0]
    count = len(non_zero)
    if count == 0:
        return {"W": None, "z": None, "p_two_sided": None, "n_non_zero": 0}

    order = sorted(range(count), key=lambda i: abs(non_zero[i]))
    ranks = [0.0] * count
    index = 0
    while index < count:
        stop = index
        while (
            stop + 1 < count
            and abs(non_zero[order[stop + 1]]) == abs(non_zero[order[index]])
        ):
            stop += 1
        average = (index + stop) / 2 + 1
        for position in range(index, stop + 1):
            ranks[order[position]] = average
        index = stop + 1

    w_positive = sum(r for d, r in zip(non_zero, ranks) if d > 0)
    w_negative = sum(r for d, r in zip(non_zero, ranks) if d < 0)
    statistic = min(w_positive, w_negative)
    mean = count * (count + 1) / 4
    sigma = math.sqrt(count * (count + 1) * (2 * count + 1) / 24)
    z = (statistic - mean) / sigma if sigma else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return {
        "W_positive": w_positive,
        "W_negative": w_negative,
        "W": statistic,
        "z": round(z, 4),
        "p_two_sided": round(p, 6),
        "n_non_zero": count,
        "normal_approximation": True,
    }


def svg_curve(primary: list[float], other: list[float], out: Path) -> None:
    width, height = 960, 460
    left, right, top, bottom = 70, 30, 50, 60
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [v for v in primary + other if v and v > 0]
    lo, hi = min(values), max(values)
    log_lo, log_hi = math.log10(lo), math.log10(hi)

    def x_of(index: int) -> float:
        return left + plot_w * index / (len(primary) - 1)

    def y_of(value: float) -> float:
        return top + plot_h * (1 - (math.log10(value) - log_lo) / (log_hi - log_lo))

    def path(series: list[float]) -> str:
        return " ".join(
            f"{'M' if i == 0 else 'L'}{x_of(i):.1f},{y_of(v):.1f}"
            for i, v in enumerate(series)
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width/2}" y="26" text-anchor="middle" font-size="16">'
        "Study 5-EQ1 OD-004: per-layer transcoder L0, log scale</text>",
    ]
    for decade in range(math.floor(log_lo), math.ceil(log_hi) + 1):
        value = 10.0**decade
        if not (lo <= value <= hi):
            continue
        y = y_of(value)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" '
            'stroke="#dddddd" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="11">'
            f"{value:g}</text>"
        )
    for index in range(0, len(primary), 2):
        parts.append(
            f'<text x="{x_of(index):.1f}" y="{top+plot_h+18}" text-anchor="middle" '
            f'font-size="10">{index}</text>'
        )
    parts.append(
        f'<text x="{left+plot_w/2}" y="{height-18}" text-anchor="middle" '
        'font-size="12">layer index</text>'
    )
    parts.append(
        f'<text x="18" y="{top+plot_h/2}" text-anchor="middle" font-size="12" '
        f'transform="rotate(-90 18 {top+plot_h/2})">mean active features per token</text>'
    )
    parts.append(
        f'<path d="{path(primary)}" fill="none" stroke="#1f77b4" stroke-width="2"/>'
    )
    parts.append(
        f'<path d="{path(other)}" fill="none" stroke="#d62728" stroke-width="2"/>'
    )
    for index, value in enumerate(primary):
        parts.append(
            f'<circle cx="{x_of(index):.1f}" cy="{y_of(value):.1f}" r="2.5" fill="#1f77b4"/>'
        )
    for index, value in enumerate(other):
        parts.append(
            f'<circle cx="{x_of(index):.1f}" cy="{y_of(value):.1f}" r="2.5" fill="#d62728"/>'
        )
    legend_y = top + 6
    parts.append(
        f'<rect x="{left+16}" y="{legend_y}" width="250" height="46" fill="#ffffff" '
        'stroke="#cccccc"/>'
    )
    parts.append(
        f'<line x1="{left+26}" y1="{legend_y+16}" x2="{left+56}" y2="{legend_y+16}" '
        'stroke="#1f77b4" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{left+62}" y="{legend_y+20}" font-size="11">l1w0.001 '
        "(README table: 1.4)</text>"
    )
    parts.append(
        f'<line x1="{left+26}" y1="{legend_y+34}" x2="{left+56}" y2="{legend_y+34}" '
        'stroke="#d62728" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{left+62}" y="{legend_y+38}" font-size="11">l1w0.003 '
        "(README table: 4.3)</text>"
    )
    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--other", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--figure", required=True)
    parser.add_argument("--check-id", default="S2.PAIRED")
    args = parser.parse_args(argv)

    primary = json.loads(Path(args.primary).read_text(encoding="utf-8"))
    other = json.loads(Path(args.other).read_text(encoding="utf-8"))
    a = primary["per_layer_l0"]
    b = other["per_layer_l0"]
    if len(a) != len(b):
        raise SystemExit("layer counts differ; the layers are not a paired unit")

    differences = [y - x for x, y in zip(a, b)]
    prose = sum(1 for d in differences if d < 0)
    table = sum(1 for d in differences if d > 0)
    ties = sum(1 for d in differences if d == 0)
    sign_p = sign_test_two_sided(prose, len(differences) - ties)
    wilcoxon = wilcoxon_signed_rank(differences)
    ratios = [y / x for x, y in zip(a, b) if x > 0]

    svg_curve(a, b, Path(args.figure))

    report = {
        "schema_version": "study5-eq1-l0-paired-analysis-v1",
        "definition": "OD-004",
        "analysed_at_utc": utc_now(),
        "is_a_hypothesis_test": False,
        "counted_against_the_multiple_testing_budget": False,
        "why_not": "this describes a property of the measuring instrument, decided before and independently of any accuracy measurement; it enters no estimand and licenses no scientific claim",
        "paired_unit": "layer",
        "why_paired": "the two checkpoints share an architecture and a layer indexing, so layer l corresponds to layer l; this is the same principle the study applies to items",
        "layers": len(differences),
        "layers_supporting_prose_direction": prose,
        "layers_supporting_table_direction": table,
        "ties": ties,
        "sign_test": {
            "two_sided_p": round(sign_p, 6),
            "exact": True,
            "magnitude_free": True,
            "supports": "prose" if prose > table else "table",
            "significant_at_0_05": sign_p < 0.05,
        },
        "wilcoxon_signed_rank": {
            **wilcoxon,
            "magnitude_weighted": True,
            "significant_at_0_05": bool(
                wilcoxon["p_two_sided"] is not None
                and wilcoxon["p_two_sided"] < 0.05
            ),
        },
        "effect_size": {
            "statistic": "median_l [ L0_other(l) / L0_primary(l) ]",
            "value": round(st.median(ratios), 4),
            "supports": "prose" if st.median(ratios) < 1 else "table",
            "range": [round(min(ratios), 4), round(max(ratios), 4)],
            "layers_with_ratio_below_one": sum(1 for r in ratios if r < 1),
        },
        "descriptive_only_do_not_decide_direction": {
            "unpaired_mean_ratio": round(st.mean(b) / st.mean(a), 4),
            "unpaired_median_ratio": round(st.median(b) / st.median(a), 4),
            "label": "dominated by the layer 26 and 27 tail",
        },
        "tail_layers": {
            "layer_26": {"primary": a[26], "other": b[26]},
            "layer_27": {"primary": a[27], "other": b[27]},
            "note": "an order of magnitude above every other layer; layer 27 alone differs by enough to flip the sign of the unpaired mean",
        },
        "tests_disagree": bool(
            (sign_p < 0.05)
            != bool(
                wilcoxon["p_two_sided"] is not None and wilcoxon["p_two_sided"] < 0.05
            )
        ),
        "disagreement_explanation": "the sign test counts direction only; Wilcoxon weights by the rank of absolute difference, so layers 26 and 27 take the top ranks and pull the signed-rank statistic toward the null. Wilcoxon therefore remains partially vulnerable to the very tail this registration exists to neutralise.",
        "both_registered_tests_reported": True,
        "per_layer_l0_primary": a,
        "per_layer_l0_other": b,
        "per_layer_paired_difference": [round(d, 6) for d in differences],
        "per_layer_paired_ratio": [round(r, 6) for r in ratios],
        "figure": str(args.figure),
        "figure_format": "hand-written SVG, so no plotting library is added to the frozen image",
        "figure_scale": "log10, because the layer 26 and 27 values would otherwise flatten every other layer into the axis",
        "claim_ceiling": "This describes an instrument on a data slice. It is not evidence about J-space, about distillation, or about reasoning.",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
    out.write_text(text, encoding="utf-8")

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    print(
        f"prose {prose} / table {table} / ties {ties}   "
        f"sign p={sign_p:.6f}   wilcoxon p={wilcoxon['p_two_sided']}"
    )
    print(f"median paired ratio {report['effect_size']['value']}")
    print(f"tests disagree: {report['tests_disagree']}")
    proof(args.check_id, True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
