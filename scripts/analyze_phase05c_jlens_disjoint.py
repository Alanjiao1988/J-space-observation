#!/usr/bin/env python3
"""Deterministic post-run analysis for the Phase 0.5C disjoint-replication pack.

Reads an executed artifact pack (`02_records.jsonl` plus `03_metrics.csv`) and
regenerates the derived files against the pre-registered rules:

- `03_metrics.csv` rollups (pair means, per-lens means, overall means)
- `04_decision.json` per the frozen decision-rule table
- `06_paper_table.csv`
- `07_figure_data.csv`

Nothing here re-fits, re-merges, or re-applies anything: it is pure arithmetic
over the numbers the job already recorded, so it is safe to re-run and it is
byte-deterministic. `02_records.jsonl`, `00_stage_manifest.json`,
`01_protocol_snapshot.json`, `05_summary.md` and `08_deviations.json` are read
but never rewritten; `artifact_manifest.json` is regenerated last.

Engineering numerics only. Top-k overlap and rank correlation are technical
stability statistics; they are not semantic evidence and support no claim
about a workspace, hidden reasoning, an internal chain-of-thought, J-space,
semantic convergence, or any lens being scientifically usable.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import phase05_jlens as base  # noqa: E402
import phase05_jlens_saturation as sat  # noqa: E402
import phase05c_jlens_disjoint as protocol  # noqa: E402

APPLY_STATISTICS = (
    "heldout_apply_logit_cosine",
    "heldout_topk_overlap",
    "heldout_topk_overlap_secondary",
    "heldout_rank_correlation",
)

PLACEHOLDER_NOTE = (
    "Every number in this pack is a placeholder until the container job has "
    "executed. A pre-run pack carries status = not_applicable rows and "
    "decision = INCONCLUSIVE; only a pack whose 00_stage_manifest.json reports "
    "eight successful stages contains measured values."
)


class AnalysisError(RuntimeError):
    """Raised when the executed pack cannot be analysed as registered."""


def read_records(pack_dir: Path) -> list[dict[str, Any]]:
    path = pack_dir / "02_records.jsonl"
    if not path.is_file():
        raise AnalysisError(f"missing {path}")
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def read_metrics(pack_dir: Path) -> list[dict[str, str]]:
    path = pack_dir / "03_metrics.csv"
    if not path.is_file():
        raise AnalysisError(f"missing {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and tuple(rows[0]) != sat.METRICS_COLUMNS:
        raise AnalysisError("03_metrics.csv columns are not the registered schema")
    return rows


def _read_csv(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise AnalysisError(f"missing {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and tuple(rows[0]) != columns:
        raise AnalysisError(f"{path.name} columns are not the registered schema")
    return rows


def is_measured(records: list[dict[str, Any]]) -> bool:
    return any(
        record.get("status") != "not_applicable"
        and record.get("condition") != "not_applicable"
        for record in records
    )


def collect_apply_values(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, list[float]]]:
    """Rebuild the per-pair statistic series from the apply:: records."""

    series: dict[str, dict[str, list[float]]] = {
        name: {statistic: [] for statistic in APPLY_STATISTICS}
        for name, _left, _right in protocol.APPLY_PAIRS
    }
    for record in sorted(records, key=lambda item: str(item.get("record_id", ""))):
        if not str(record.get("record_id", "")).startswith("apply::"):
            continue
        pairs = (record.get("evaluation") or {}).get("pairs") or {}
        for name, payload in pairs.items():
            if name not in series:
                raise AnalysisError(f"unregistered apply pair {name!r}")
            for statistic in APPLY_STATISTICS:
                if statistic in payload:
                    series[name][statistic].append(float(payload[statistic]))
    return series


def collect_comparisons(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    comparisons = {}
    for record in records:
        record_id = str(record.get("record_id", ""))
        if record_id.startswith("comparison::"):
            comparisons[record_id.split("::", 1)[1]] = record.get("evaluation") or {}
    return comparisons


def collect_finite(records: list[dict[str, Any]]) -> tuple[int, int]:
    numerator = 0
    denominator = 0
    for record in records:
        evaluation = record.get("evaluation") or {}
        if "matrix_finite_layers" in evaluation and "matrix_layers" in evaluation:
            numerator += int(evaluation["matrix_finite_layers"])
            denominator += int(evaluation["matrix_layers"])
    return numerator, denominator


def collect_serialization(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for record in records:
        record_id = str(record.get("record_id", ""))
        if record_id.startswith("serialization::"):
            out[record_id.split("::", 1)[1]] = record.get("evaluation") or {}
    return out


def collect_apply_consistency(records: list[dict[str, Any]]) -> float | None:
    seen = False
    consistent = True
    for record in records:
        evaluation = record.get("evaluation") or {}
        flags = evaluation.get("save_load_apply_consistent")
        if isinstance(flags, dict):
            seen = True
            consistent = consistent and all(bool(value) for value in flags.values())
    return (1.0 if consistent else 0.0) if seen else None


def collect_fit_cost(records: list[dict[str, Any]]) -> dict[str, Any]:
    for record in records:
        if str(record.get("record_id", "")) == "fit::lens_25b":
            evaluation = record.get("evaluation") or {}
            return {
                "wall_clock_per_prompt": evaluation.get("fit_seconds_per_prompt"),
                "fit_wall_clock_seconds": evaluation.get("fit_seconds"),
                "peak_gpu_memory": evaluation.get("shard_peak_reserved_bytes"),
                "checkpoint_bytes": evaluation.get("checkpoint_bytes"),
            }
    return {}


def rollups(records: list[dict[str, Any]]) -> dict[str, Any]:
    apply_series = collect_apply_values(records)
    pair_means = {
        name: {
            statistic: protocol.mean(values)
            for statistic, values in statistics.items()
        }
        for name, statistics in apply_series.items()
    }
    lens_means = {
        label: {
            statistic: protocol.mean(
                [
                    pair_means[name][statistic]
                    for name in pair_names
                    if pair_means[name][statistic] is not None
                ]
            )
            for statistic in APPLY_STATISTICS
        }
        for label, pair_names in protocol.PAIRS_BY_LENS.items()
    }
    overall = {
        statistic: protocol.mean(
            [
                pair_means[name][statistic]
                for name, _left, _right in protocol.APPLY_PAIRS
                if pair_means[name][statistic] is not None
            ]
        )
        for statistic in APPLY_STATISTICS
    }
    numerator, denominator = collect_finite(records)
    serialization = collect_serialization(records)
    save_load_values = [
        float(item["save_load_max_abs"])
        for item in serialization.values()
        if item.get("save_load_max_abs") is not None
    ]
    comparisons = collect_comparisons(records)
    return {
        "pair_means": pair_means,
        "lens_means": lens_means,
        "overall": overall,
        "matrix_finite_numerator": numerator,
        "matrix_finite_denominator": denominator,
        "matrix_finite_rate": protocol.finite_rate(numerator, denominator),
        "serialization": serialization,
        "save_load_max_abs": max(save_load_values) if save_load_values else None,
        "apply_save_load_consistency": collect_apply_consistency(records),
        "comparisons": comparisons,
        "fit_cost": collect_fit_cost(records),
        "prompts_per_pair": {
            name: len(statistics["heldout_topk_overlap"])
            for name, statistics in apply_series.items()
        },
    }


def registered_values(summary: dict[str, Any]) -> dict[str, Any]:
    comparisons = summary["comparisons"]
    values: dict[str, Any] = {}
    for pair, frobenius_metric, cosine_metric in (
        (protocol.PAIR_AB, "25A_vs_25B_relative_frobenius", "25A_vs_25B_cosine"),
        (protocol.PAIR_AM, "25A_vs_50M_relative_frobenius", "25A_vs_50M_cosine"),
        (protocol.PAIR_BM, "25B_vs_50M_relative_frobenius", "25B_vs_50M_cosine"),
    ):
        comparison = comparisons.get(pair) or {}
        if "max_relative_frobenius" in comparison:
            values[frobenius_metric] = comparison["max_relative_frobenius"]
        if "min_cosine" in comparison:
            values[cosine_metric] = comparison["min_cosine"]
    for statistic in ("heldout_apply_logit_cosine", "heldout_topk_overlap",
                      "heldout_rank_correlation"):
        if summary["overall"].get(statistic) is not None:
            values[statistic] = summary["overall"][statistic]
    for key in ("matrix_finite_rate", "save_load_max_abs",
                "apply_save_load_consistency"):
        if summary.get(key) is not None:
            values[key] = summary[key]
    for key in ("wall_clock_per_prompt", "peak_gpu_memory"):
        if summary["fit_cost"].get(key) is not None:
            values[key] = summary["fit_cost"][key]
    return values


def build_metric_rows(run_id: str, summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(metric: str, value: Any, **kwargs: Any) -> None:
        rows.append(
            protocol.make_metric_row(run_id=run_id, metric=metric, value=value, **kwargs)
        )

    for pair, frobenius_metric, cosine_metric in (
        (protocol.PAIR_AB, "25A_vs_25B_relative_frobenius", "25A_vs_25B_cosine"),
        (protocol.PAIR_AM, "25A_vs_50M_relative_frobenius", "25A_vs_50M_cosine"),
        (protocol.PAIR_BM, "25B_vs_50M_relative_frobenius", "25B_vs_50M_cosine"),
    ):
        comparison = summary["comparisons"].get(pair) or {}
        if not comparison:
            continue
        for metric, key, criterion_key in (
            (frobenius_metric, "max_relative_frobenius", frobenius_metric),
            (cosine_metric, "min_cosine", cosine_metric),
        ):
            threshold = protocol.CRITERIA.get(criterion_key, {}).get("threshold", "")
            observed = comparison.get(key)
            passed: Any = ""
            if threshold != "" and observed is not None:
                passed = protocol.evaluate_criterion(criterion_key, observed)["passed"]
            add(
                metric,
                observed,
                condition="replicate_variability",
                stratum="all",
                n=protocol.FIT_A_PROMPTS,
                threshold=threshold,
                passed=passed,
            )
        for layer, layer_values in sorted((comparison.get("layers") or {}).items()):
            add(
                frobenius_metric,
                layer_values.get("relative_frobenius"),
                condition="replicate_variability",
                stratum=f"layer_{layer}",
            )
            add(
                cosine_metric,
                layer_values.get("cosine"),
                condition="replicate_variability",
                stratum=f"layer_{layer}",
            )
    for name, statistics in sorted(summary["pair_means"].items()):
        for statistic, value in sorted(statistics.items()):
            add(
                statistic,
                value,
                condition="apply_stability",
                stratum=f"pair::{name}",
                n=summary["prompts_per_pair"].get(name, ""),
            )
    for label, statistics in sorted(summary["lens_means"].items()):
        for statistic, value in sorted(statistics.items()):
            add(
                statistic,
                value,
                condition="apply_stability",
                stratum=f"lens::{protocol.LENS_DISPLAY[label]}",
                n=protocol.HELDOUT_PROMPTS,
            )
    for statistic, value in sorted(summary["overall"].items()):
        add(
            statistic,
            value,
            condition="apply_stability",
            stratum="all",
            n=len(protocol.APPLY_PAIRS),
        )
    if summary.get("matrix_finite_rate") is not None:
        add(
            "matrix_finite_rate",
            summary["matrix_finite_rate"],
            condition="replicate_variability",
            stratum="all",
            n=summary["matrix_finite_denominator"],
            numerator=summary["matrix_finite_numerator"],
            denominator=summary["matrix_finite_denominator"],
            threshold=protocol.FINITE_RATE_MIN,
            passed=summary["matrix_finite_rate"] >= protocol.FINITE_RATE_MIN,
        )
    for label, item in sorted(summary["serialization"].items()):
        if item.get("save_load_max_abs") is not None:
            add(
                "save_load_max_abs",
                item["save_load_max_abs"],
                condition="serialization",
                stratum=label,
                threshold=protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
                passed=float(item["save_load_max_abs"])
                <= protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
            )
        if item.get("lens_bytes") is not None:
            add("lens_bytes", item["lens_bytes"], condition="serialization",
                stratum=label)
    if summary.get("save_load_max_abs") is not None:
        add(
            "save_load_max_abs",
            summary["save_load_max_abs"],
            condition="serialization",
            stratum="all",
            n=len(summary["serialization"]),
            threshold=protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
            passed=float(summary["save_load_max_abs"])
            <= protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
        )
    if summary.get("apply_save_load_consistency") is not None:
        add(
            "apply_save_load_consistency",
            summary["apply_save_load_consistency"],
            condition="apply_stability",
            stratum="all",
            threshold=protocol.APPLY_CONSISTENCY_MIN,
            passed=float(summary["apply_save_load_consistency"])
            >= protocol.APPLY_CONSISTENCY_MIN,
        )
    for metric in ("wall_clock_per_prompt", "peak_gpu_memory",
                   "fit_wall_clock_seconds", "checkpoint_bytes"):
        if summary["fit_cost"].get(metric) is not None:
            add(
                metric,
                summary["fit_cost"][metric],
                condition="fit_25b_merged",
                stratum=protocol.LENS_B,
                n=protocol.FIT_B_PROMPTS,
            )
    return rows


def build_paper_rows(run_id: str, summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(**kwargs: Any) -> None:
        rows.append(protocol.make_paper_row(run_id=run_id, **kwargs))

    for pair in (protocol.PAIR_AB, protocol.PAIR_AM, protocol.PAIR_BM):
        comparison = summary["comparisons"].get(pair) or {}
        if not comparison:
            continue
        add(
            row_label=pair,
            condition="replicate_variability",
            n_prompts=protocol.FIT_A_PROMPTS,
            metric="relative_frobenius",
            value=comparison.get("max_relative_frobenius"),
            unit="ratio",
        )
        add(
            row_label=pair,
            condition="replicate_variability",
            n_prompts=protocol.FIT_A_PROMPTS,
            metric="cosine",
            value=comparison.get("min_cosine"),
            unit="cosine",
        )
    for statistic in ("heldout_apply_logit_cosine", "heldout_topk_overlap",
                      "heldout_rank_correlation"):
        if summary["overall"].get(statistic) is None:
            continue
        add(
            row_label=statistic,
            condition="apply_stability",
            n_prompts=protocol.HELDOUT_PROMPTS,
            metric=f"{statistic}_mean",
            value=summary["overall"][statistic],
            unit="ratio",
        )
    for label, statistics in sorted(summary["lens_means"].items()):
        for statistic in ("heldout_topk_overlap", "heldout_rank_correlation"):
            if statistics.get(statistic) is None:
                continue
            add(
                row_label=f"lens::{protocol.LENS_DISPLAY[label]}",
                condition="apply_stability",
                n_prompts=protocol.HELDOUT_PROMPTS,
                metric=statistic,
                value=statistics[statistic],
                unit="ratio",
            )
    for metric, unit in (("wall_clock_per_prompt", "seconds"),
                         ("fit_wall_clock_seconds", "seconds"),
                         ("peak_gpu_memory", "bytes"),
                         ("checkpoint_bytes", "bytes")):
        if summary["fit_cost"].get(metric) is None:
            continue
        add(
            row_label=metric,
            condition="fit_25b_merged",
            n_prompts=protocol.FIT_B_PROMPTS,
            metric=metric,
            value=summary["fit_cost"][metric],
            unit=unit,
        )
    if summary.get("save_load_max_abs") is not None:
        add(
            row_label="save_load_max_abs",
            condition="serialization",
            n_prompts=protocol.MERGED_PROMPTS,
            metric="save_load_max_abs",
            value=summary["save_load_max_abs"],
            unit="abs",
        )
    return rows


def build_figure_rows(run_id: str, summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(**kwargs: Any) -> None:
        rows.append(protocol.make_figure_row(run_id=run_id, **kwargs))

    for pair in (protocol.PAIR_AB, protocol.PAIR_AM, protocol.PAIR_BM):
        comparison = summary["comparisons"].get(pair) or {}
        for layer, layer_values in sorted((comparison.get("layers") or {}).items()):
            add(
                figure_id="fig_replicate_variability",
                series=f"{pair}::layer_{layer}",
                x_label="lens_pair",
                x_value=pair,
                y_label="relative_frobenius",
                y_value=layer_values.get("relative_frobenius"),
            )
            add(
                figure_id="fig_replicate_cosine",
                series=f"{pair}::layer_{layer}",
                x_label="lens_pair",
                x_value=pair,
                y_label="cosine",
                y_value=layer_values.get("cosine"),
            )
    for name, statistics in sorted(summary["pair_means"].items()):
        for statistic in ("heldout_topk_overlap", "heldout_rank_correlation"):
            if statistics.get(statistic) is None:
                continue
            add(
                figure_id="fig_heldout_apply_stability",
                series=name,
                x_label="lens_pair",
                x_value=name,
                y_label=statistic,
                y_value=statistics[statistic],
            )
    return rows


def _merge_rows(
    existing: list[dict[str, str]],
    computed: list[dict[str, Any]],
    key_columns: tuple[str, ...],
    columns: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Replace executed rows in place by key, then append genuinely new rows.

    The executed pack is evidence, so nothing recorded by the job is dropped:
    a recomputed row overwrites the row with the same key and keeps its
    position, and rollups the job did not emit are appended in a deterministic
    order.
    """

    def key(row: Any) -> tuple[str, ...]:
        return tuple(str(row.get(column, "")) for column in key_columns)

    by_key = {key(row): row for row in computed}
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in existing:
        row_key = key(row)
        if str(row.get("not_applicable_reason", "")) and row_key not in by_key:
            continue
        replacement = by_key.get(row_key)
        merged.append(replacement if replacement is not None else row)
        seen.add(row_key)
    for row in computed:
        if key(row) not in seen:
            merged.append(row)
            seen.add(key(row))
    for row in merged:
        for column in columns:
            row.setdefault(column, "")
    return merged


def analyse(pack_dir: Path) -> dict[str, Any]:
    records = read_records(pack_dir)
    executed_metrics = read_metrics(pack_dir)
    executed_paper = _read_csv(pack_dir / "06_paper_table.csv",
                               protocol.PAPER_TABLE_COLUMNS)
    executed_figures = _read_csv(pack_dir / "07_figure_data.csv",
                                 protocol.FIGURE_DATA_COLUMNS)
    manifest_path = pack_dir / "00_stage_manifest.json"
    if not manifest_path.is_file():
        raise AnalysisError(f"missing {manifest_path}")
    stage_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = str(stage_manifest.get("run_id", "")) or pack_dir.name
    stages = {
        name: {"status": payload.get("status", "not_run")}
        for name, payload in (stage_manifest.get("stages") or {}).items()
    }
    measured = is_measured(records)
    if not measured:
        return {
            "run_id": run_id,
            "measured": False,
            "note": PLACEHOLDER_NOTE,
            "summary": {},
            "values": {},
            "decision": protocol.evaluate_decision(
                {},
                stages=stages,
                blocked_reason="pack contains no measured records",
            ),
            "metric_rows": [protocol.not_applicable_metric_row(run_id, PLACEHOLDER_NOTE)],
            "paper_rows": [protocol.not_applicable_paper_row(run_id, PLACEHOLDER_NOTE)],
            "figure_rows": [protocol.not_applicable_figure_row(run_id, PLACEHOLDER_NOTE)],
        }
    summary = rollups(records)
    values = registered_values(summary)
    improvement = protocol.merged_apply_improvement(summary["pair_means"])
    self_test = bool(
        (stage_manifest.get("inputs") or {}).get("mode") == "self_test"
    )
    decision = protocol.evaluate_decision(
        values,
        stages=stages,
        self_test=self_test,
        merged_improvement=improvement,
        deviations=(
            json.loads((pack_dir / "08_deviations.json").read_text(encoding="utf-8"))
            .get("deviations", [])
            if (pack_dir / "08_deviations.json").is_file()
            else []
        ),
    )
    return {
        "run_id": run_id,
        "measured": True,
        "note": "",
        "summary": summary,
        "values": values,
        "merged_apply_improvement": improvement,
        "decision": decision,
        "metric_rows": _merge_rows(
            executed_metrics,
            build_metric_rows(run_id, summary),
            ("metric", "stratum", "condition"),
            sat.METRICS_COLUMNS,
        ),
        "paper_rows": _merge_rows(
            executed_paper,
            build_paper_rows(run_id, summary),
            ("row_label", "condition", "metric"),
            protocol.PAPER_TABLE_COLUMNS,
        ),
        "figure_rows": _merge_rows(
            executed_figures,
            build_figure_rows(run_id, summary),
            ("figure_id", "series", "x_value", "y_label"),
            protocol.FIGURE_DATA_COLUMNS,
        ),
    }


def write_outputs(pack_dir: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    written = {}
    for name, rows, columns in (
        ("03_metrics.csv", analysis["metric_rows"], sat.METRICS_COLUMNS),
        ("06_paper_table.csv", analysis["paper_rows"], protocol.PAPER_TABLE_COLUMNS),
        ("07_figure_data.csv", analysis["figure_rows"], protocol.FIGURE_DATA_COLUMNS),
    ):
        payload = sat.csv_bytes(columns, rows)
        (pack_dir / name).write_bytes(payload)
        written[name] = base.sha256_bytes(payload)
    decision_bytes = base.canonical_json_bytes(analysis["decision"])
    (pack_dir / "04_decision.json").write_bytes(decision_bytes)
    written["04_decision.json"] = base.sha256_bytes(decision_bytes)
    manifest = protocol.rebuild_artifact_manifest(pack_dir)
    written[protocol.MANIFEST_FILENAME] = base.sha256_file(
        pack_dir / protocol.MANIFEST_FILENAME
    )
    protocol.validate_artifact_pack(pack_dir)
    return {"written": written, "artifacts": len(manifest["artifacts"])}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pack-dir",
        required=True,
        help="Directory holding the executed ten-file artifact pack.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Rewrite 03_metrics.csv, 04_decision.json, 06_paper_table.csv, "
            "07_figure_data.csv and artifact_manifest.json in place. Without "
            "this flag the analysis is printed and nothing is modified."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pack_dir = Path(args.pack_dir).resolve()
    if not pack_dir.is_dir():
        raise SystemExit(f"[FAIL] not a directory: {pack_dir}")
    analysis = analyse(pack_dir)
    report: dict[str, Any] = {
        "pack_dir": pack_dir.as_posix(),
        "run_id": analysis["run_id"],
        "measured": analysis["measured"],
        "status": analysis["decision"]["status"],
        "decision": analysis["decision"]["decision"],
        "values": analysis["values"],
        "merged_apply_improvement": analysis.get("merged_apply_improvement"),
        "rows": {
            "03_metrics.csv": len(analysis["metric_rows"]),
            "06_paper_table.csv": len(analysis["paper_rows"]),
            "07_figure_data.csv": len(analysis["figure_rows"]),
        },
        "written": False,
    }
    if analysis["note"]:
        report["note"] = analysis["note"]
    if args.write:
        report.update(write_outputs(pack_dir, analysis))
        report["written"] = True
    print(base.canonical_json_bytes(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
