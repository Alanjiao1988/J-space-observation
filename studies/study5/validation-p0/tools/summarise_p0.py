"""P-0 reporting: per-layer curves as CSV and SVG, beside the null ceiling.

The addendum EQ2 had to write at its close is the reason this exists. A verdict
read from a median, printed without the profile it was taken from, let a reader
believe something stronger than what was measured. So the decisive curve is
always printed next to the ceiling that judged it, and the non-decisive sites
are printed next to both, clearly marked as unable to decide anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SITES = ("PREFIX", "CUE", "BRIDGE", "READOUT")
COLOURS = {
    "PREFIX": "#8a8a8a",
    "CUE": "#3b6fb6",
    "BRIDGE": "#c1440e",
    "READOUT": "#2e8b57",
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def svg(rows, ceiling, passing, out_path: Path, layers):
    width, height = 960, 460
    left, right, top, bottom = 70, 20, 40, 60
    plot_w = width - left - right
    plot_h = height - top - bottom

    values = [v for row in rows.values() for v in row.values()] + [ceiling, 0.0]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    lo -= 0.05 * span
    hi += 0.05 * span

    def x_of(layer):
        index = layers.index(layer)
        return left + plot_w * index / max(1, len(layers) - 1)

    def y_of(value):
        return top + plot_h * (1.0 - (value - lo) / (hi - lo))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="24" font-family="sans-serif" font-size="15" '
        f'font-weight="bold">P-0 normalised restoration by layer '
        f'(BRIDGE decides; CUE and READOUT cannot)</text>',
    ]
    for value in (0.0, ceiling):
        y = y_of(value)
        dash = "" if value == 0.0 else ' stroke-dasharray="6,4"'
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" '
            f'stroke="#999" stroke-width="1"{dash}/>'
        )
    parts.append(
        f'<text x="{left+plot_w-4}" y="{y_of(ceiling)-5:.1f}" text-anchor="end" '
        f'font-family="sans-serif" font-size="11" fill="#555">'
        f'zero-intervention ceiling {ceiling:.4f}</text>'
    )

    for layer in layers:
        x = x_of(layer)
        if layer % 2 == 0 or layer == -1:
            parts.append(
                f'<text x="{x:.1f}" y="{top+plot_h+16}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="10" fill="#333">'
                f'{"emb" if layer == -1 else layer}</text>'
            )
    for layer in passing:
        x = x_of(layer)
        parts.append(
            f'<rect x="{x-3:.1f}" y="{top}" width="6" height="{plot_h}" '
            f'fill="#c1440e" opacity="0.12"/>'
        )

    for site in SITES:
        if site not in rows:
            continue
        points = " ".join(
            f"{x_of(layer):.1f},{y_of(rows[site][str(layer)]):.1f}"
            for layer in layers
            if str(layer) in rows[site]
        )
        parts.append(
            f'<polyline points="{points}" fill="none" '
            f'stroke="{COLOURS[site]}" stroke-width="{3 if site == "BRIDGE" else 1.6}"/>'
        )

    for index, site in enumerate(s for s in SITES if s in rows):
        y = top + plot_h + 42
        x = left + index * 150
        parts.append(
            f'<line x1="{x}" y1="{y-4}" x2="{x+22}" y2="{y-4}" '
            f'stroke="{COLOURS[site]}" stroke-width="{3 if site == "BRIDGE" else 1.6}"/>'
        )
        label = site + (" (decides)" if site == "BRIDGE" else "")
        parts.append(
            f'<text x="{x+28}" y="{y}" font-family="sans-serif" font-size="11" '
            f'fill="#333">{label}</text>'
        )

    for tick in range(6):
        value = lo + (hi - lo) * tick / 5
        parts.append(
            f'<text x="{left-8}" y="{y_of(value)+4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="10" fill="#333">{value:.2f}</text>'
        )
    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", required=True)
    parser.add_argument("--merged", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-svg", required=True)
    parser.add_argument("--out-summary", required=True)
    args = parser.parse_args()

    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    summary = decision["summary"]["REAL"]
    layers = merged["layers"]
    ceiling = decision["ceiling"]
    passing = decision["layers_above_ceiling"]

    lines = ["site,layer,mean,lcb,ucb,n_observations,n_clusters,above_ceiling"]
    means: dict[str, dict[str, float]] = {}
    for site in SITES:
        if site not in summary:
            continue
        means[site] = {}
        for layer in layers:
            stats = summary[site].get(str(layer))
            if stats is None:
                continue
            means[site][str(layer)] = stats["mean"]
            lines.append(
                f'{site},{layer},{stats["mean"]:.6f},{stats["lcb"]:.6f},'
                f'{stats["ucb"]:.6f},{stats["n_observations"]},'
                f'{stats["n_clusters"]},'
                f'{"yes" if site == "BRIDGE" and layer in passing else "no"}'
            )
    Path(args.out_csv).write_text("\n".join(lines) + "\n", encoding="utf-8")
    svg(means, ceiling, passing, Path(args.out_svg), layers)

    accuracy = merged["per_unit"]
    donor_ok = sum(1 for r in accuracy if r["donor_top1_is_donor_target"])
    recip_ok = sum(1 for r in accuracy if r["recipient_top1_is_recipient_target"])
    bridge = summary.get("BRIDGE", {})
    peak_layer, peak = None, None
    for layer in layers:
        stats = bridge.get(str(layer))
        if stats and (peak is None or stats["mean"] > peak):
            peak, peak_layer = stats["mean"], layer

    out = {
        "schema_version": "study5-p0-summary-v1",
        "verdict": decision["verdict"],
        "decisive_site": decision["decisive_site"],
        "layers_above_ceiling": passing,
        "ceiling": ceiling,
        "ceiling_source": decision["ceiling_source"],
        "gates": decision["gates"],
        "bridge_peak_layer": peak_layer,
        "bridge_peak_mean": peak,
        "n_units_measured": merged["n_units_measured"],
        "n_units_dropped": merged["n_units_dropped"],
        "n_clusters": merged["n_clusters"],
        "reported_only_item_accuracy": {
            "note": (
                "reported only; no criterion is adjusted from it. EQ2 never "
                "checked whether the model answers these items at all"
            ),
            "units": len(accuracy),
            "donor_top1_equals_donor_target": donor_ok,
            "recipient_top1_equals_recipient_target": recip_ok,
            "donor_fraction": donor_ok / len(accuracy) if accuracy else 0.0,
            "recipient_fraction": recip_ok / len(accuracy) if accuracy else 0.0,
        },
        "site_peaks": {
            site: max(
                ((v["mean"], int(k)) for k, v in summary[site].items()),
                default=(None, None),
            )
            for site in SITES
            if site in summary
        },
        "claim_ceiling": (
            "An item-validity summary. It is not a scientific finding."
        ),
    }
    Path(args.out_summary).write_bytes(canonical_json_bytes(out))

    print(f"verdict            : {out['verdict']}")
    print(f"ceiling            : {ceiling:.6f} from {decision['ceiling_source']}")
    print(f"BRIDGE peak        : layer {peak_layer}, mean {peak:.6f}")
    print(f"layers above       : {passing}")
    for site in SITES:
        if site in out["site_peaks"]:
            value, layer = out["site_peaks"][site]
            print(f"  {site:8} peak mean {value: .6f} at layer {layer}")
    acc = out["reported_only_item_accuracy"]
    print(
        f"item accuracy (reported only): donor "
        f"{acc['donor_fraction']:.4f}, recipient {acc['recipient_fraction']:.4f}"
    )
    print("P0-CHECK-SUMMARY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
