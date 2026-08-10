"""Descriptive summarization for the Study 3-P0 feasibility pilot.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
section 9.

What this tool may produce
--------------------------
Descriptive summaries by role, profile, contrast, tuple class and rendering:
output support size, prediction diversity, correctness, pairwise joint
correctness, pairwise discordance, S4 parseability, prompt-token lengths,
latency, memory and exact operation cost.

What this tool may never produce
--------------------------------
A p-value, a confidence decision, a formal gate outcome, a profile rank, a
winner, a confirmatory effect-size estimate or a revised sample-size
recommendation. Those are all outside the P0 claim ceiling, and this module
contains no code that could compute one.

Observed correctness, response variance and discordance are descriptive at this
sample size. Zero observed discordance is not proof of invariance and is not by
itself a mechanical failure.

Usage::

    python p0_summarize.py --result <p0_model_pilot_result.json> --out <dir>
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_corpus import canonical_bytes  # noqa: E402

SCHEMA_VERSION = "study3-p0-descriptive-summary-v1"

FORBIDDEN_OUTPUTS = (
    "p_value", "confidence_decision", "formal_gate", "profile_rank", "winner",
    "confirmatory_effect_size", "revised_sample_size", "interface_preference",
)


def load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _group(records, keys):
    grouped = {}
    for record in records:
        key = "|".join(str(record.get(k)) for k in keys)
        grouped.setdefault(key, []).append(record)
    return grouped


def _cell_summary(records):
    predictions = {}
    correct = 0
    scored = 0
    unparseable = 0
    lengths = []
    latencies = []
    for record in records:
        value = record.get("prediction")
        if value is None:
            value = record.get("parser_result")
        predictions[str(value)] = predictions.get(str(value), 0) + 1
        if record.get("correct") is not None:
            scored += 1
            if record["correct"]:
                correct += 1
        if record.get("unparseable"):
            unparseable += 1
        if record.get("token_count") is not None:
            lengths.append(record["token_count"])
        if record.get("latency_seconds") is not None:
            latencies.append(record["latency_seconds"])
    return {
        "rows": len(records),
        "scored_rows": scored,
        "correct_rows": correct,
        "unparseable_rows": unparseable,
        "prediction_counts": predictions,
        "output_support_size": len(predictions),
        "prediction_diversity": (
            "degenerate" if len(predictions) <= 1 else "varied"),
        "prompt_token_length_min": min(lengths) if lengths else None,
        "prompt_token_length_max": max(lengths) if lengths else None,
        "latency_seconds_min": min(latencies) if latencies else None,
        "latency_seconds_max": max(latencies) if latencies else None,
    }


def _pairwise(records):
    pairs = {}
    for record in records:
        key = (record["role"], record["profile"], record["contrast"],
               record["tuple_class_id"], record["row_id"])
        pairs.setdefault(key, {})[record["role_in_pair"]] = record
    complete = 0
    joint_correct = 0
    discordant = 0
    incomplete = 0
    for members in pairs.values():
        if len(members) != 2:
            incomplete += 1
            continue
        complete += 1
        a = members["baseline"].get("correct")
        b = members["variant"].get("correct")
        if a is True and b is True:
            joint_correct += 1
        if a is not None and b is not None and a != b:
            discordant += 1
    return {
        "complete_pairs": complete,
        "incomplete_pairs": incomplete,
        "joint_correct_pairs": joint_correct,
        "discordant_pairs": discordant,
    }


def summarize(result):
    records = result.get("records", [])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_descriptive_summary",
        "run_id": result.get("run_id"),
        "state": result.get("state"),
        "by_role": {},
        "by_profile": {},
        "by_contrast": {},
        "by_tuple_class": {},
        "by_rendering": {},
        "by_cell": {},
        "pairwise": {},
        "operation_cost": result.get("counters", {}),
        "device_identity": result.get("device_identity", {}),
        "forbidden_outputs_absent": list(FORBIDDEN_OUTPUTS),
        "claim_boundary": (
            "descriptive at this sample size. P0 computes no p-value, confidence "
            "decision, formal gate, profile rank, winner, confirmatory "
            "effect-size estimate or revised sample-size recommendation. Zero "
            "observed discordance is not proof of invariance and is not by "
            "itself a mechanical failure. These numbers may never choose or "
            "justify a threshold, sample size, alpha, seed, bank, profile or "
            "confirmation rule."),
    }
    for name, keys in (
            ("by_role", ["role"]),
            ("by_profile", ["profile"]),
            ("by_contrast", ["contrast"]),
            ("by_tuple_class", ["tuple_class_id"]),
            ("by_rendering", ["rendering"]),
            ("by_cell", ["role", "profile", "contrast", "tuple_class_id"])):
        for key, rows in sorted(_group(records, keys).items()):
            summary[name][key] = _cell_summary(rows)
    for key, rows in sorted(_group(records, ["role"]).items()):
        summary["pairwise"][key] = _pairwise(rows)
    summary["pairwise"]["all_roles"] = _pairwise(records)
    total_discordance = summary["pairwise"]["all_roles"]["discordant_pairs"]
    summary["empirical_information"] = (
        "low_information_no_observed_discordance" if total_discordance == 0
        else "some_pairwise_discordance_observed")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = load(args.result)
    summary = summarize(result)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "p0_descriptive_summary.json")
    with open(path, "wb") as handle:
        handle.write(canonical_bytes(summary))
    print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
