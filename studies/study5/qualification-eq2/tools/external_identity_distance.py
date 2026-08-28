"""R-1 step 1: recover the external empirical distribution of final_identity_distance.

Zero GPU. Reads the published convergence traces for every model in the external
sweep and extracts the last row's identity_distance, which is the value the
external configs report as `final_identity_distance`.

The point is to derive OUR comparability tolerance from EXTERNAL data rather
than choosing it. Our own lens's corresponding value cannot be computed here:
that requires reading lens_A, which OD-012 forbids until the convention is
committed. The tolerance is therefore committed now and applied in R-2.

OD-011: failing cases in tests/test_eq2_identity_distance.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = "neuronpedia/jacobian-lens"
REVISION = "0731326edff4ae730ffc5356fe1a4728c748b3a6"
ENDPOINT = "https://hf-mirror.com"

POSITIVE_CONTROL_VALUE = 0.578094


class ExtractionError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def http_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode("ascii") + payload
    ).hexdigest()


def final_identity_distance(csv_text: str) -> tuple[float, int]:
    """Last row's identity_distance, plus the number of data rows.

    The header is located by name rather than by column index, because a column
    reordering upstream would otherwise silently yield the wrong quantity.
    """
    lines = [line for line in csv_text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ExtractionError("convergence csv has no data rows")
    header = [h.strip() for h in lines[0].split(",")]
    if "identity_distance" not in header:
        raise ExtractionError(
            f"no identity_distance column; header is {header}"
        )
    index = header.index("identity_distance")
    fields = lines[-1].split(",")
    if len(fields) <= index:
        raise ExtractionError("final row is short of the identity_distance column")
    raw = fields[index].strip()
    value = float(raw)
    if value != value:
        raise ExtractionError("final identity_distance is NaN")
    return value, len(lines) - 1


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ExtractionError("no values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = q * (len(sorted_values) - 1)
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    frac = position - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tree = http_json(f"{ENDPOINT}/api/models/{REPO}/tree/{REVISION}?recursive=1")
    csv_paths = sorted(
        entry["path"]
        for entry in tree  # type: ignore[union-attr]
        if entry.get("type") == "file" and entry["path"].endswith("_convergence.csv")
    )
    if not csv_paths:
        raise ExtractionError("no convergence csv found in the external repo")

    anchors = {
        entry["path"]: entry.get("oid")
        for entry in tree  # type: ignore[union-attr]
        if entry.get("type") == "file"
    }

    records = []
    for path in csv_paths:
        payload = http_bytes(f"{ENDPOINT}/{REPO}/resolve/{REVISION}/{path}")
        observed = git_blob_sha1(payload)
        expected = anchors.get(path)
        if expected and observed != expected:
            raise ExtractionError(
                f"{path}: git blob {observed} does not match origin-published {expected}"
            )
        value, rows = final_identity_distance(payload.decode("utf-8"))
        model_slug = path.split("/")[0]
        dataset = path.split("/")[2] if len(path.split("/")) > 2 else ""
        records.append(
            {
                "path": path,
                "model_slug": model_slug,
                "dataset": dataset,
                "final_identity_distance": value,
                "convergence_rows": rows,
                "git_blob_sha1": observed,
                "verified_against_origin": bool(expected),
            }
        )
        (out_dir / path.replace("/", "__")).write_bytes(payload)
        print(f"  {value:9.6f}  {rows:>5} rows  {path}", flush=True)

    values = sorted(r["final_identity_distance"] for r in records)
    n = len(values)
    q1 = quantile(values, 0.25)
    q3 = quantile(values, 0.75)
    median = quantile(values, 0.50)
    iqr = q3 - q1

    pc = [r for r in records if r["model_slug"] == "qwen2.5-7b-it"]
    pc_value = pc[0]["final_identity_distance"] if pc else None

    report = {
        "schema_version": "study5-eq2-identity-distance-distribution-v1",
        "phase": "R-1",
        "step": "R1-001",
        "repo": REPO,
        "revision": REVISION,
        "models_with_a_convergence_trace": n,
        "distribution": {
            "n": n,
            "min": values[0],
            "q1": q1,
            "median": median,
            "q3": q3,
            "max": values[-1],
            "iqr": iqr,
            "mean": sum(values) / n,
        },
        "positive_control": {
            "model_slug": "qwen2.5-7b-it",
            "final_identity_distance": pc_value,
            "matches_the_published_config_value": pc_value == POSITIVE_CONTROL_VALUE,
            "published_config_value": POSITIVE_CONTROL_VALUE,
        },
        "records": records,
        "our_own_value": {
            "status": "NOT COMPUTED",
            "why": (
                "computing it requires reading lens_A, which OD-012 forbids until "
                "the convention is committed; hard blocker 5 makes an early read a stop"
            ),
            "when": "R-2, as its first action, and it is a gate",
        },
        "claim_ceiling": "An external empirical distribution. It licenses no claim of any kind.",
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    d = report["distribution"]
    print(
        f"\nn={d['n']}  min={d['min']:.6f}  q1={d['q1']:.6f}  median={d['median']:.6f}  "
        f"q3={d['q3']:.6f}  max={d['max']:.6f}  iqr={d['iqr']:.6f}"
    )
    print("EQ2-CHECK-IDENTITY-DISTRIBUTION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
