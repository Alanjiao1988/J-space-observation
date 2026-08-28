"""Render the four kurtosis-versus-depth curves as a hand-written SVG.

No plotting library. The figure is emitted as deterministic text so its digest
is stable and reproducible from the committed curve data, which is the same
reason analyse_l0_paired.py draws its own SVG.

Linear y axis: excess kurtosis is signed and can be near zero, so the log scale
used for L0 is not applicable here.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

SERIES = (
    ("kappa_A", "#1f77b4", "J-lens A"),
    ("kappa_B", "#2ca02c", "J-lens B"),
    ("kappa_null", "#7f7f7f", "matched-norm random J (null)"),
    ("kappa_logitlens", "#d62728", "logit lens (descriptive)"),
)


def nice_step(span: float) -> float:
    if span <= 0:
        return 1.0
    raw = span / 6.0
    power = 10.0 ** math.floor(math.log10(raw))
    for multiple in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= multiple * power:
            return multiple * power
    return 10.0 * power


def render(curves: dict, band_a: list[int], band_b: list[int], out: Path) -> None:
    width, height = 980, 520
    left, right, top, bottom = 78, 210, 54, 62
    plot_w, plot_h = width - left - right, height - top - bottom

    layers = [int(p["layer"]) for p in curves["kappa_A"]]
    all_values: list[float] = []
    for key, _colour, _label in SERIES:
        all_values.extend(float(p["excess_kurtosis"]) for p in curves[key])
    lo, hi = min(all_values), max(all_values)
    pad = 0.06 * (hi - lo or 1.0)
    lo, hi = lo - pad, hi + pad

    def x_of(index: int) -> float:
        return left + plot_w * index / (len(layers) - 1)

    def y_of(value: float) -> float:
        return top + plot_h * (1 - (value - lo) / (hi - lo))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-size="16">'
        "Study 5-EQ1 P-2: excess kurtosis versus depth, 7B target</text>",
        f'<text x="{width/2}" y="42" text-anchor="middle" font-size="11" fill="#555555">'
        "readout: jlens apply() at lens.py:213, raw logits, no softmax; "
        "mean over (row, position), position 0 excluded</text>",
    ]

    # Shaded intersection of the two derived bands, drawn first so it sits
    # behind the curves.
    shared = sorted(set(band_a) & set(band_b))
    if shared:
        i0 = layers.index(shared[0])
        i1 = layers.index(shared[-1])
        x0, x1 = x_of(i0), x_of(i1)
        parts.append(
            f'<rect x="{x0:.1f}" y="{top}" width="{max(1.0, x1-x0):.1f}" '
            f'height="{plot_h}" fill="#ffd27f" fill-opacity="0.32"/>'
        )
        parts.append(
            f'<text x="{(x0+x1)/2:.1f}" y="{top+14}" text-anchor="middle" '
            f'font-size="10" fill="#8a6d1f">derived band '
            f'{shared[0]}-{shared[-1]}</text>'
        )

    step = nice_step(hi - lo)
    tick = math.ceil(lo / step) * step
    while tick <= hi:
        y = y_of(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" '
            'stroke="#e6e6e6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="11">'
            f"{tick:g}</text>"
        )
        tick += step

    if lo < 0 < hi:
        y = y_of(0.0)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" '
            'stroke="#999999" stroke-width="1" stroke-dasharray="4,3"/>'
        )

    for index, layer in enumerate(layers):
        if index % 2 == 0:
            parts.append(
                f'<text x="{x_of(index):.1f}" y="{top+plot_h+18}" '
                f'text-anchor="middle" font-size="10">{layer}</text>'
            )
    parts.append(
        f'<text x="{left+plot_w/2}" y="{height-16}" text-anchor="middle" '
        'font-size="12">source layer index</text>'
    )
    parts.append(
        f'<text x="20" y="{top+plot_h/2}" text-anchor="middle" font-size="12" '
        f'transform="rotate(-90 20 {top+plot_h/2})">excess kurtosis</text>'
    )

    legend_y = top + 6
    for key, colour, label in SERIES:
        values = [float(p["excess_kurtosis"]) for p in curves[key]]
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{x_of(i):.1f},{y_of(v):.1f}"
            for i, v in enumerate(values)
        )
        dash = ' stroke-dasharray="6,4"' if key == "kappa_null" else ""
        parts.append(
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2"{dash}/>'
        )
        for i, v in enumerate(values):
            parts.append(
                f'<circle cx="{x_of(i):.1f}" cy="{y_of(v):.1f}" r="2.2" fill="{colour}"/>'
            )
        parts.append(
            f'<line x1="{left+plot_w+16}" y1="{legend_y}" x2="{left+plot_w+40}" '
            f'y2="{legend_y}" stroke="{colour}" stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="{left+plot_w+46}" y="{legend_y+4}" font-size="11">{label}</text>'
        )
        legend_y += 20

    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curves", required=True)
    parser.add_argument("--decision", required=False, default="")
    parser.add_argument("--out-svg", required=True)
    parser.add_argument("--out-csv", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.curves).read_text(encoding="utf-8"))
    curves = data["curves"]

    band_a: list[int] = []
    band_b: list[int] = []
    if args.decision and Path(args.decision).is_file():
        decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
        band_a = decision.get("derived_band_A") or []
        band_b = decision.get("derived_band_B") or []

    render(curves, band_a, band_b, Path(args.out_svg))

    layers = [int(p["layer"]) for p in curves["kappa_A"]]
    lines = ["layer,kappa_A,kappa_B,kappa_null,kappa_logitlens"]
    for i, layer in enumerate(layers):
        lines.append(
            f"{layer},"
            f"{curves['kappa_A'][i]['excess_kurtosis']:.6f},"
            f"{curves['kappa_B'][i]['excess_kurtosis']:.6f},"
            f"{curves['kappa_null'][i]['excess_kurtosis']:.6f},"
            f"{curves['kappa_logitlens'][i]['excess_kurtosis']:.6f}"
        )
    Path(args.out_csv).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"wrote {args.out_svg} and {args.out_csv}")
    print("P2-CHECK-KURTOSIS-FIGURE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
