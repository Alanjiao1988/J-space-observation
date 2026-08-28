"""Hand-written SVG of the pooled pass@1 rank profiles for the three controls.

No plotting library, so the figure is deterministic text reproducible from the
committed profile data.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

SERIES = (
    ("positive", "#1f77b4", "Qwen2.5-7B-Instruct (positive control)"),
    ("depth", "#2ca02c", "Qwen3-1.7B (depth test)"),
    ("negative", "#d62728", "gpt2-small (negative control)"),
)

R1 = Path("studies/study5/qualification-eq2/r1")


def main() -> None:
    profiles = {}
    for role, _c, _l in SERIES:
        d = json.loads((R1 / f"rank_{role}.json").read_text(encoding="utf-8"))
        profiles[role] = [
            (int(p["layer"]), float(p["readrate"])) for p in d["pooled_profile"]["1"]
        ]

    bands = json.loads((R1 / "band_derivation.json").read_text(encoding="utf-8"))["results"]

    width, height = 980, 540
    left, right, top, bottom = 78, 250, 58, 62
    plot_w, plot_h = width - left - right, height - top - bottom

    max_layers = max(len(v) for v in profiles.values())
    hi = max(v for series in profiles.values() for _l, v in series)
    hi = hi * 1.1 if hi > 0 else 1.0

    def x_of(layer_index: int) -> float:
        return left + plot_w * layer_index / (max_layers - 1)

    def y_of(value: float) -> float:
        return top + plot_h * (1 - value / hi)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-size="16">'
        "Study 5-EQ2 R-1: official rank profile, pooled pass@1 readrate by layer</text>",
        f'<text x="{width/2}" y="43" text-anchor="middle" font-size="11" fill="#555555">'
        "readrate = fraction of labelled intermediates at lens rank 1; "
        "six official eval sets, 898-910 scored intermediates per model</text>",
    ]

    pb = bands["positive"]["band"]
    if pb:
        x0, x1 = x_of(pb[0]), x_of(pb[-1])
        parts.append(
            f'<rect x="{x0:.1f}" y="{top}" width="{max(2.0, x1-x0):.1f}" '
            f'height="{plot_h}" fill="#ffd27f" fill-opacity="0.35"/>'
        )
        parts.append(
            f'<text x="{(x0+x1)/2:.1f}" y="{top+14}" text-anchor="middle" '
            f'font-size="10" fill="#8a6d1f">positive band {pb[0]}-{pb[-1]}</text>'
        )

    step = 0.02
    tick = 0.0
    while tick <= hi:
        y = y_of(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" '
            'stroke="#e6e6e6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="11">'
            f"{tick:.2f}</text>"
        )
        tick += step

    for i in range(0, max_layers, 2):
        parts.append(
            f'<text x="{x_of(i):.1f}" y="{top+plot_h+18}" text-anchor="middle" '
            f'font-size="10">{i}</text>'
        )
    parts.append(
        f'<text x="{left+plot_w/2}" y="{height-16}" text-anchor="middle" '
        'font-size="12">source layer index</text>'
    )
    parts.append(
        f'<text x="20" y="{top+plot_h/2}" text-anchor="middle" font-size="12" '
        f'transform="rotate(-90 20 {top+plot_h/2})">pass@1 readrate</text>'
    )

    legend_y = top + 8
    for role, colour, label in SERIES:
        series = profiles[role]
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{x_of(l):.1f},{y_of(v):.1f}"
            for i, (l, v) in enumerate(series)
        )
        parts.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2"/>')
        for l, v in series:
            parts.append(
                f'<circle cx="{x_of(l):.1f}" cy="{y_of(v):.1f}" r="2.4" fill="{colour}"/>'
            )
        peak = bands[role]["peak_readrate"]
        parts.append(
            f'<line x1="{left+plot_w+16}" y1="{legend_y}" x2="{left+plot_w+40}" '
            f'y2="{legend_y}" stroke="{colour}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{left+plot_w+46}" y="{legend_y+4}" font-size="10">{label}</text>'
        )
        parts.append(
            f'<text x="{left+plot_w+46}" y="{legend_y+17}" font-size="10" '
            f'fill="#666666">peak {peak:.4f}, band {bands[role]["band"]}</text>'
        )
        legend_y += 38

    parts.append("</svg>")
    out = R1 / "rank_profiles.svg"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")

    csv_lines = ["layer,positive,negative,depth"]
    for i in range(max_layers):
        row = [str(i)]
        for role in ("positive", "negative", "depth"):
            series = profiles[role]
            row.append(f"{series[i][1]:.6f}" if i < len(series) else "")
        csv_lines.append(",".join(row))
    (R1 / "rank_profiles.csv").write_text(
        "\n".join(csv_lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {out} and rank_profiles.csv")
    print("EQ2-CHECK-RANK-FIGURE PASSED")


if __name__ == "__main__":
    main()
