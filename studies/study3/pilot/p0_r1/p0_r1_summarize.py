"""Deterministic summarization for the Study 3 P0-R1 continuation.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 6
and 7.

Summarization is deterministic and lossless with respect to the registered
observations: every valid row, raw S4 completion, exception, partial result and
counter is preserved. Correctness, accuracy, diversity and discordance are
computed as *descriptive* quantities only; section 7 forbids them from acting as
smoke-pass criteria, and no row is ever dropped, imputed, replaced or reordered
on the basis of its own output.
"""

import json

SCHEMA_VERSION = "study3-p0-r1-summary-v1"

DESCRIPTIVE_ONLY = (
    "correctness, accuracy, diversity and discordance are descriptive only. "
    "They are not smoke-pass criteria, they select nothing, and they estimate "
    "no effect.")


class SummaryDefect(Exception):
    """A fail-closed summarization stop."""


def _sorted_rows(rows):
    """A deterministic order that does not depend on execution order."""
    return sorted(rows, key=lambda row: (row.get("role", ""),
                                         row.get("profile", ""),
                                         str(row.get("row_id", ""))))


def summarize(scored_rows, s4_completions=None, exceptions=None,
              counters=None, aggregate=None):
    rows = _sorted_rows(list(scored_rows))
    seen = set()
    for row in rows:
        key = (row.get("role"), row.get("profile"), row.get("row_id"))
        if key in seen:
            raise SummaryDefect(
                "duplicate scored row %s/%s/%s" % key)
        seen.add(key)

    by_profile = {}
    for row in rows:
        bucket = by_profile.setdefault(row["profile"], {
            "scored_rows": 0,
            "sequence_level_model_evaluations": 0,
            "registered_prompt_tokens": 0,
            "common_prefix_tokens": 0,
            "scoring_context_tokens": 0,
            "selected_surfaces": {},
        })
        bucket["scored_rows"] += 1
        bucket["sequence_level_model_evaluations"] += row.get(
            "sequence_level_model_evaluations", 0)
        bucket["registered_prompt_tokens"] += row.get(
            "registered_prompt_token_count", 0)
        bucket["common_prefix_tokens"] += row.get("common_prefix_token_count", 0)
        bucket["scoring_context_tokens"] += row.get(
            "scoring_context_token_count", 0)
        surface = row.get("selected_complete_candidate_surface")
        bucket["selected_surfaces"][surface] = \
            bucket["selected_surfaces"].get(surface, 0) + 1

    for profile, bucket in by_profile.items():
        expected = (bucket["registered_prompt_tokens"]
                    + bucket["common_prefix_tokens"])
        if bucket["scoring_context_tokens"] != expected:
            raise SummaryDefect(
                "profile %s does not reconcile registered prompt tokens plus "
                "common-prefix tokens with its scoring-context tokens"
                % profile)
        if profile == "S3" and bucket["sequence_level_model_evaluations"]:
            raise SummaryDefect(
                "S3 recorded %d sequence-level model evaluations; it adds zero"
                % bucket["sequence_level_model_evaluations"])

    completions = list(s4_completions or [])
    failures = list(exceptions or [])
    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_summary",
        "deterministic": True,
        "rows_preserved": len(rows),
        "raw_s4_completions_preserved": len(completions),
        "exceptions_preserved": len(failures),
        "no_output_conditioned_retry_or_row_replacement": True,
        "by_profile": by_profile,
        "descriptive_only": DESCRIPTIVE_ONLY,
        "counters": dict(counters or {}),
        "aggregate_counter_view": aggregate,
        "rows": rows,
        "s4_completions": completions,
        "exceptions": failures,
        "evidence_status": (
            "methods-feasibility observations only. They do not enter "
            "paper/evidence_ledger.csv, choose an interface, estimate a "
            "confirmatory effect, set a threshold or sample size, or answer the "
            "research question."),
    }


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
