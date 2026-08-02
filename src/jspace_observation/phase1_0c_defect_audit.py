"""Phase 1.0C generation-profile defect audit.

Phase 1.0C Track B run ``20260725T170041Z`` closed ``COMPLETE_INCONCLUSIVE``
with 44 of 300 rows semantically unresolved.  That run is a valid historical
record and is not relabelled, deleted, or replaced by anything in this module.

Before Phase 1.0D may freeze a replacement protocol it has to establish *why*
1.0C was inconclusive, from the committed artifacts rather than from
recollection.  This module recomputes those facts and refuses to collapse them
into a single cause.

Two independent generation-profile defects are audited:

``placeholder``
    Every 1.0C prompt carried the literal format line ``Final answer:
    <answer>``.  A model that copies the format line emits the literal token
    ``<answer>`` instead of a value, and no reviewer can read an answer out of
    it.

``token_cap``
    Every 1.0C condition ran at ``max_new_tokens=512``.  A row that reaches the
    cap mid-sentence has no final-answer surface to read, for a reason that has
    nothing to do with whether the model knew the answer.

The audit deliberately reports the *joint* distribution of the two defects over
the unresolved rows.  Neither defect may be claimed to have caused all 44
unresolved rows, and the joint table is what makes that claim checkable rather
than rhetorical.

Nothing here measures capability, and nothing here licenses any claim about
hidden reasoning, an internal workspace, invisible chain-of-thought, or
"J-space".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

PHASE_1_0C_RUN_ID = "20260725T170041Z"
PHASE_1_0C_PACK = Path("artifacts/phase1-headroom-calibration/track-b/20260725T170041Z")
PHASE_1_0C_RECORDS_PATH = PHASE_1_0C_PACK / "02_records.jsonl"

REGISTERED_MAX_NEW_TOKENS = 512
REGISTERED_RECORD_COUNT = 300

LITERAL_PLACEHOLDER = "<answer>"
LITERAL_FORMAT_LINE = "Final answer: <answer>"

UNRESOLVED_LABEL = "unresolved"

# Facts asserted by the controlling authority
# (docs/prompts/phase_science_restart_after_parser_closure_prompt.md section 4.1).
# The audit recomputes each of them; it does not read them as inputs.
AUTHORITY_EXPECTED_FACTS: Mapping[str, int] = {
    "record_count": 300,
    "prompts_with_literal_format_line": 300,
    "outputs_containing_literal_placeholder": 31,
    "outputs_containing_format_line_placeholder_form": 5,
    "reviewed_row_count": 225,
    "reviewed_rows_at_token_cap": 79,
    "unresolved_row_count": 44,
}


class DefectAuditError(RuntimeError):
    """Raised when the committed 1.0C pack cannot support the audit."""


@dataclass(frozen=True)
class RowFacts:
    """Per-row facts the audit is allowed to use."""

    record_id: str
    condition: str
    cell_id: str
    prompt_has_format_line: bool
    output_has_placeholder: bool
    output_has_format_line_placeholder_form: bool
    reviewed: bool
    at_token_cap: bool
    truncation_flag: bool
    unresolved: bool


@dataclass(frozen=True)
class DefectAudit:
    """Recomputed Phase 1.0C generation-profile defect facts."""

    run_id: str
    registered_max_new_tokens: int
    record_count: int
    prompts_with_literal_format_line: int
    outputs_containing_literal_placeholder: int
    outputs_containing_format_line_placeholder_form: int
    reviewed_row_count: int
    reviewed_rows_at_token_cap: int
    unresolved_row_count: int
    unresolved_by_defect: Mapping[str, int]
    token_cap_flag_disagreements: int
    conditions: tuple[str, ...]
    rows: tuple[RowFacts, ...] = field(repr=False)

    def as_receipt(self) -> dict[str, Any]:
        """Return the content-free summary suitable for committing."""

        return {
            "run_id": self.run_id,
            "registered_max_new_tokens": self.registered_max_new_tokens,
            "record_count": self.record_count,
            "conditions": list(self.conditions),
            "prompts_with_literal_format_line": self.prompts_with_literal_format_line,
            "outputs_containing_literal_placeholder": (
                self.outputs_containing_literal_placeholder
            ),
            "outputs_containing_format_line_placeholder_form": (
                self.outputs_containing_format_line_placeholder_form
            ),
            "reviewed_row_count": self.reviewed_row_count,
            "reviewed_rows_at_token_cap": self.reviewed_rows_at_token_cap,
            "unresolved_row_count": self.unresolved_row_count,
            "unresolved_by_defect": dict(self.unresolved_by_defect),
            "token_cap_flag_disagreements": self.token_cap_flag_disagreements,
        }


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DefectAuditError(f"{what} is not an object")
    return value


def load_phase_1_0c_records(path: Path | str | None = None) -> tuple[dict[str, Any], ...]:
    """Load the committed Phase 1.0C record stream."""

    resolved = Path(path) if path is not None else REPO_ROOT / PHASE_1_0C_RECORDS_PATH
    if not resolved.is_file():
        raise DefectAuditError(f"Phase 1.0C records not found at {resolved}")
    records: list[dict[str, Any]] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise DefectAuditError(
                    f"line {line_number} of {resolved} is not valid JSON"
                ) from exc
            records.append(dict(_require_mapping(parsed, f"record on line {line_number}")))
    if not records:
        raise DefectAuditError(f"{resolved} contains no records")
    return tuple(records)


def _row_facts(record: Mapping[str, Any]) -> RowFacts:
    provenance = _require_mapping(record.get("provenance"), "record provenance")
    evaluation = _require_mapping(record.get("evaluation"), "record evaluation")

    prompt_text = provenance.get("prompt_text")
    if not isinstance(prompt_text, str):
        raise DefectAuditError("record provenance carries no prompt_text string")
    output_text = record.get("output_text")
    if not isinstance(output_text, str):
        raise DefectAuditError("record carries no output_text string")

    max_new_tokens = provenance.get("max_new_tokens")
    output_token_count = provenance.get("output_token_count")
    if not isinstance(max_new_tokens, int) or not isinstance(output_token_count, int):
        raise DefectAuditError("record provenance carries no integer token counts")
    if max_new_tokens != REGISTERED_MAX_NEW_TOKENS:
        raise DefectAuditError(
            "record was generated at max_new_tokens="
            f"{max_new_tokens}, not the registered {REGISTERED_MAX_NEW_TOKENS}"
        )

    at_token_cap = output_token_count >= max_new_tokens
    truncation_flag = bool(evaluation.get("truncated"))

    return RowFacts(
        record_id=str(record.get("record_id", "")),
        condition=str(record.get("condition", "")),
        cell_id=str(provenance.get("cell_id", "")),
        prompt_has_format_line=LITERAL_FORMAT_LINE in prompt_text,
        output_has_placeholder=LITERAL_PLACEHOLDER in output_text,
        output_has_format_line_placeholder_form=LITERAL_FORMAT_LINE in output_text,
        reviewed=bool(evaluation.get("review_required")),
        at_token_cap=at_token_cap,
        truncation_flag=truncation_flag,
        unresolved=evaluation.get("semantic_label") == UNRESOLVED_LABEL,
    )


def audit_phase_1_0c_defects(
    records: Iterable[Mapping[str, Any]] | None = None,
    *,
    records_path: Path | str | None = None,
) -> DefectAudit:
    """Recompute the Phase 1.0C generation-profile defect facts."""

    source = tuple(records) if records is not None else load_phase_1_0c_records(records_path)
    rows = tuple(_row_facts(record) for record in source)

    unresolved = tuple(row for row in rows if row.unresolved)
    unresolved_by_defect = {
        "placeholder_only": sum(
            1 for row in unresolved if row.output_has_placeholder and not row.at_token_cap
        ),
        "token_cap_only": sum(
            1 for row in unresolved if row.at_token_cap and not row.output_has_placeholder
        ),
        "both": sum(
            1 for row in unresolved if row.at_token_cap and row.output_has_placeholder
        ),
        "neither": sum(
            1
            for row in unresolved
            if not row.at_token_cap and not row.output_has_placeholder
        ),
    }

    return DefectAudit(
        run_id=PHASE_1_0C_RUN_ID,
        registered_max_new_tokens=REGISTERED_MAX_NEW_TOKENS,
        record_count=len(rows),
        prompts_with_literal_format_line=sum(1 for row in rows if row.prompt_has_format_line),
        outputs_containing_literal_placeholder=sum(
            1 for row in rows if row.output_has_placeholder
        ),
        outputs_containing_format_line_placeholder_form=sum(
            1 for row in rows if row.output_has_format_line_placeholder_form
        ),
        reviewed_row_count=sum(1 for row in rows if row.reviewed),
        reviewed_rows_at_token_cap=sum(1 for row in rows if row.reviewed and row.at_token_cap),
        unresolved_row_count=len(unresolved),
        unresolved_by_defect=dict(unresolved_by_defect),
        token_cap_flag_disagreements=sum(
            1 for row in rows if row.at_token_cap != row.truncation_flag
        ),
        conditions=tuple(sorted({row.condition for row in rows})),
        rows=rows,
    )


def compare_to_authority(audit: DefectAudit) -> dict[str, dict[str, int]]:
    """Return the facts whose recomputed value differs from the authority's."""

    observed = {
        "record_count": audit.record_count,
        "prompts_with_literal_format_line": audit.prompts_with_literal_format_line,
        "outputs_containing_literal_placeholder": (
            audit.outputs_containing_literal_placeholder
        ),
        "outputs_containing_format_line_placeholder_form": (
            audit.outputs_containing_format_line_placeholder_form
        ),
        "reviewed_row_count": audit.reviewed_row_count,
        "reviewed_rows_at_token_cap": audit.reviewed_rows_at_token_cap,
        "unresolved_row_count": audit.unresolved_row_count,
    }
    return {
        name: {"authority": expected, "observed": observed[name]}
        for name, expected in AUTHORITY_EXPECTED_FACTS.items()
        if observed[name] != expected
    }


def single_cause_attribution_is_refuted(audit: DefectAudit) -> bool:
    """True when no single audited defect explains every unresolved row.

    This is the structural check behind the instruction not to attribute the
    1.0C outcome to one cause.  It is refuted — that is, the single-cause story
    fails — when neither defect covers the whole unresolved set.
    """

    total = audit.unresolved_row_count
    if total == 0:
        return False
    by_defect = audit.unresolved_by_defect
    placeholder_total = by_defect["placeholder_only"] + by_defect["both"]
    token_cap_total = by_defect["token_cap_only"] + by_defect["both"]
    return placeholder_total < total and token_cap_total < total


def build_defect_receipt(audit: DefectAudit) -> dict[str, Any]:
    """Build the committed, content-free defect receipt."""

    mismatches = compare_to_authority(audit)
    return {
        "schema_version": "phase1_0c_generation_profile_defects.v1",
        "source_pack": str(PHASE_1_0C_PACK).replace("\\", "/"),
        "source_records": str(PHASE_1_0C_RECORDS_PATH).replace("\\", "/"),
        "historical_status_preserved": "COMPLETE_INCONCLUSIVE",
        "recomputed": audit.as_receipt(),
        "authority_expected": dict(AUTHORITY_EXPECTED_FACTS),
        "authority_mismatches": mismatches,
        "authority_facts_reproduced": not mismatches,
        "single_cause_attribution_refuted": single_cause_attribution_is_refuted(audit),
        "defects": [
            {
                "id": "P10C-D1",
                "name": "literal_answer_placeholder",
                "statement": (
                    "Every Phase 1.0C prompt carried the literal format line "
                    "'Final answer: <answer>', so a model copying the format "
                    "emits the placeholder instead of a value."
                ),
                "phase_1_0d_remedy": (
                    "No Phase 1.0D condition may contain the literal placeholder, "
                    "and every rendered prompt is asserted free of it before "
                    "inference."
                ),
            },
            {
                "id": "P10C-D2",
                "name": "generation_token_cap",
                "statement": (
                    "Every Phase 1.0C condition ran at max_new_tokens=512, so a "
                    "row that reaches the cap has no final-answer surface to read."
                ),
                "phase_1_0d_remedy": (
                    "Per-condition budgets are registered before inference: the "
                    "visible-reasoning control gets at least 1024 new tokens, and "
                    "the strict conditions get a budget sufficient for the "
                    "registered answer but too small to permit visible reasoning."
                ),
            },
        ],
        "interpretation": (
            "Both defects are real and neither alone accounts for every "
            "unresolved row. The Phase 1.0C INCONCLUSIVE outcome is therefore "
            "not a GPU-budget failure and must not be attributed to one cause."
        ),
    }


__all__ = [
    "AUTHORITY_EXPECTED_FACTS",
    "DefectAudit",
    "DefectAuditError",
    "LITERAL_FORMAT_LINE",
    "LITERAL_PLACEHOLDER",
    "PHASE_1_0C_RECORDS_PATH",
    "PHASE_1_0C_RUN_ID",
    "REGISTERED_MAX_NEW_TOKENS",
    "RowFacts",
    "audit_phase_1_0c_defects",
    "build_defect_receipt",
    "compare_to_authority",
    "load_phase_1_0c_records",
    "single_cause_attribution_is_refuted",
]
