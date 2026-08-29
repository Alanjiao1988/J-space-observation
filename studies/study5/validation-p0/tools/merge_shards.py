"""P-0 step 3: merge the per-GPU shards into one curves file.

The shards partition the units, so merging is a concatenation per
(construction, site, layer, cluster). The merge refuses to run if the shards
disagree about anything they should agree about - the frame digest, the layer
grid, the replicate count - because a silent mismatch there would blend two
different measurements into one curve and nothing downstream could tell.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


AGREE_ON = (
    "units_file_sha256",
    "layers",
    "n_transformer_layers",
    "null_replicates",
    "null_sites",
    "model_dir",
    "shards",
)


class MergeError(RuntimeError):
    pass


def merge(reports: list[dict]) -> dict:
    if not reports:
        raise MergeError("no shard reports given")
    first = reports[0]
    for field in AGREE_ON:
        values = {json.dumps(r.get(field), sort_keys=True) for r in reports}
        if len(values) != 1:
            raise MergeError(f"shards disagree on {field}: {sorted(values)}")

    seen = [r["shard"] for r in reports]
    if sorted(seen) != list(range(first["shards"])):
        raise MergeError(f"expected shards 0..{first['shards']-1}, got {sorted(seen)}")

    curves: dict = {}
    for report in reports:
        for construction, by_site in report["curves"].items():
            for site, by_layer in by_site.items():
                for layer, by_cluster in by_layer.items():
                    bucket = (
                        curves.setdefault(construction, {})
                        .setdefault(site, {})
                        .setdefault(layer, {})
                    )
                    for cluster, values in by_cluster.items():
                        bucket.setdefault(cluster, []).extend(values)

    per_unit = [row for report in reports for row in report["per_unit"]]
    dropped = [row for report in reports for row in report["dropped"]]
    ids = [row["unit_id"] for row in per_unit]
    if len(ids) != len(set(ids)):
        raise MergeError("the same unit appears in more than one shard")

    return {
        "schema_version": "study5-p0-merged-v1",
        "phase": "P-0",
        "model_dir": first["model_dir"],
        "units_file_sha256": first["units_file_sha256"],
        "layers": first["layers"],
        "n_transformer_layers": first["n_transformer_layers"],
        "null_replicates": first["null_replicates"],
        "null_sites": first["null_sites"],
        "shards_merged": sorted(seen),
        "n_units_measured": len(per_unit),
        "n_units_dropped": len(dropped),
        "n_clusters": len({row["cluster_id"] for row in per_unit}),
        "dropped": dropped,
        "instrument_under_test_imported": any(
            r.get("instrument_under_test_imported") for r in reports
        ),
        "gpu_uuids": sorted({r.get("gpu_uuid_last_twelve") for r in reports}),
        "wall_seconds_per_shard": {
            str(r["shard"]): r["wall_seconds"] for r in reports
        },
        "wall_seconds_max": max(r["wall_seconds"] for r in reports),
        "wall_seconds_sum": sum(r["wall_seconds"] for r in reports),
        "per_unit": per_unit,
        "curves": curves,
        "claim_ceiling": (
            "A merged causal-effect measurement. It is not a scientific finding."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    reports = [
        json.loads(Path(path).read_text(encoding="utf-8")) for path in args.shard
    ]
    merged = merge(reports)
    Path(args.out).write_bytes(canonical_json_bytes(merged))
    print(
        f"merged {len(reports)} shards: {merged['n_units_measured']} units, "
        f"{merged['n_clusters']} clusters, {merged['n_units_dropped']} dropped"
    )
    print(
        "  constructions: "
        + ", ".join(sorted(merged["curves"]))
    )
    print(f"  max shard wall seconds: {merged['wall_seconds_max']:.1f}")
    print("P0-CHECK-MERGE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
