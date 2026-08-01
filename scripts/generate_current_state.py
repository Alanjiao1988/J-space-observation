#!/usr/bin/env python3
"""Generate the machine-checked current-state block from the canonical policy.

Phase 1.2F relied on a prose scanner (``check_current_state_consistency.py``)
to keep the current-state documents honest. Phase 1.2G's seed defects showed
why that is not enough: a scanner can only reject sentences it was told to look
for, so every new figure needs a new pattern, and any figure nobody thought to
pattern-match drifts silently. Six of the ten Phase 1.2G seed defects were
stale figures in prose that no scanner pattern covered.

This script closes that gap for the facts that matter most. It does not scan.
It *renders* the current-state block from the canonical policy JSON and from
the production coverage derivation, and writes the rendered bytes into each
consuming document between sentinel comments. ``--check`` re-renders and
compares; if a human edits the block by hand, or the policy changes without the
documents being regenerated, the comparison fails and prints a diff.

The rendered block is a pure function of:

* ``docs/phase1_parser_v3_v2_evaluation_policy.json`` (the canonical source of
  truth), and
* ``jspace_observation.parser_v3_repair_contract.derive_gate_coverage`` (the
  single production derivation of exact-typed-decision coverage).

Nothing is hard-coded here that the policy already states. In particular the
80/40 split, the residual stratum list and every execution-state zero are read
or derived, never typed. That is the point: a figure that cannot be typed
cannot go stale.

Usage::

    python scripts/generate_current_state.py --check
    python scripts/generate_current_state.py --write

The script reads no private data, runs no parser and generates no prediction.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ledger_validator():
    """Load the ledger validator *by file path*, not through the package.

    ``jspace_observation/__init__.py`` eagerly imports the legacy parser, so a
    package-level import would pull parser code into this generator's process
    and cost roughly thirty seconds. The ledger module imports only ``hashlib``,
    ``json`` and ``typing``, so loading it directly is both faithful and free of
    any parser dependency.
    """

    path = REPO_ROOT / "src" / "jspace_observation" / "parser_v3_v2_access_ledger.py"
    spec = importlib.util.spec_from_file_location("_p12h_access_ledger", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load the ledger validator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_LEDGER = _load_ledger_validator()
validate_ledger = _LEDGER.validate_ledger
LedgerError = _LEDGER.LedgerError

POLICY_PATH = REPO_ROOT / "docs" / "phase1_parser_v3_v2_evaluation_policy.json"
LEDGER_PATH = REPO_ROOT / "docs" / "phase1_2h_execution_access_ledger.json"

BEGIN_MARKER = "<!-- BEGIN GENERATED CURRENT STATE -->"
END_MARKER = "<!-- END GENERATED CURRENT STATE -->"

#: Documents that carry the generated block. Each must contain both sentinels.
TARGET_FILES: tuple[str, ...] = (
    "reports/current_status.md",
    "docs/thread_handoff.md",
)

#: Statements Phase 1.2G requires every current-state document to make. They are
#: constants rather than derived values because they are *negative* facts: there
#: is no artifact recording a sealed read that did not happen, so nothing can be
#: read to confirm it. They are kept here, in one place, so that the wording
#: cannot drift between documents.
INVARIANT_STATEMENTS: tuple[str, ...] = (
    "Phase 1.0C was executed and finalized `INCONCLUSIVE`. It is target-model "
    "task/headroom screening, not parser calibration, and no Phase 1.0C result "
    "can supply, bound, or unblock any parser acceptance threshold.",
    "No private holdout, sealed input, sealed label or private curator file was "
    "accessed.",
    "No prediction was generated and no parser was run against any evaluation "
    "or calibration corpus.",
    "No formal parser-v3 evaluation has occurred. Parser v3 remains "
    "**unvalidated**.",
    "`parser-v3-v1` remains `SEALED / UNSPENT / UNSCORABLE / "
    "RETIRED_AS_INELIGIBLE`, byte-unchanged.",
    "Phase 1.2H terminated `BLOCKED_ON_PRIVATE_SOURCE_ACCESS` before any "
    "private access. No `parser-v3-v2` set was constructed or sealed, and none "
    "exists.",
    "No J-space, hidden-reasoning, invisible-CoT or internal-workspace "
    "conclusion follows from any of this.",
)


def _load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _load_ledger() -> dict[str, Any]:
    """Load the ledger and refuse to render an invalid one.

    Audit G showed the generator faithfully rendering a fabricated sealed
    successor set --- ``exists true``, ``sealed true``, ``sealed_object_count
    120`` --- because loading and rendering never asked whether the record was
    coherent. Validating here means the current-state documents cannot publish a
    claim the ledger's own validator would reject.
    """

    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    policy = _load_policy()
    policy_sha256 = hashlib.sha256(
        POLICY_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()
    validate_ledger(ledger, policy=policy, policy_sha256=policy_sha256)
    return ledger


def _render_ledger_lines(ledger: dict[str, Any]) -> list[str]:
    """Render the live access state from the ledger, deriving every figure.

    Phase 1.2H. The policy's ``execution_state`` block is a finalization
    snapshot, not live state. The live state lives in the ledger, and rendering
    it here from the file means a current-state document cannot restate an
    access count that the ledger does not carry.
    """

    repair = ledger["live_counters"]["retired_v1_repair_access"]
    execution = ledger["live_counters"]["parser_execution"]
    azure = ledger["live_counters"]["azure"]
    successor = ledger["successor_set_state"]
    retired = ledger["retired_v1_state"]
    count = successor["sealed_object_count"]
    return [
        f"- Live access ledger: `{LEDGER_PATH.name}`, phase "
        f"**{ledger['phase']}**, status **{ledger['status']}**.",
        f"- Retired `{retired['set_id']}` repair access: sealed inputs read "
        f"**{repair['sealed_input_semantic_reads']}**, sealed labels read "
        f"**{repair['sealed_label_semantic_reads']}**, private curator files "
        f"read **{repair['private_curator_files_read']}**, byte-only integrity "
        f"verifications **{repair['byte_only_integrity_verifications']}** "
        f"(a digest of a file is not a read of its content). State: "
        f"**{retired['current_state_label']}**.",
        f"- Successor `{successor['set_id']}`: exists "
        f"**{str(successor['exists']).lower()}**, cases constructed "
        f"**{successor['cases_constructed']}**, sealed "
        f"**{str(successor['sealed']).lower()}**, `sealed_object_count` "
        f"**{'null' if count is None else count}** "
        f"(undefined under `L-32` without an authenticated seal-time "
        f"observation; not measured to be zero).",
        f"- Parser execution: invocations on private or locked data "
        f"**{execution['parser_invocations_on_private_or_locked_data']}**, "
        f"candidate predictions "
        f"**{execution['candidate_predictions_generated']}**, comparator "
        f"predictions **{execution['comparator_predictions_generated']}**. "
        f"Azure: data-plane content reads "
        f"**{azure['data_plane_content_reads']}**, data-plane writes "
        f"**{azure['data_plane_writes']}**, resource creations or changes "
        f"**{azure['resource_creations_or_changes']}**.",
    ]


def _coverage() -> Any:
    """Import the production derivation.

    Imported lazily, and inside the function, so that ``--help`` does not pay
    the package import cost.
    """

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from jspace_observation.parser_v3_repair_contract import (  # noqa: PLC0415
        derive_gate_coverage,
    )

    return derive_gate_coverage(_load_policy())


def _residual_limits(policy: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy["acceptance_thresholds"]["items"]
    for item in thresholds:
        if item.get("threshold_id") == "residual_critical_exact_budget":
            return item
    raise SystemExit("residual_critical_exact_budget is missing from the policy")


def render_block(policy: dict[str, Any] | None = None) -> str:
    """Return the generated block, sentinels included, as a ``\\n`` string."""

    policy = policy if policy is not None else _load_policy()
    coverage = _coverage()
    residual = _residual_limits(policy)
    execution = policy["execution_state"]
    limits = residual["limits"]

    pinned = ", ".join(coverage.pinned_strata)
    residual_strata = ", ".join(coverage.residual_strata)
    per_stratum = limits["per_stratum_max_errors"]
    per_stratum_text = ", ".join(
        f"{stratum} \u2264 {per_stratum[stratum]}" for stratum in sorted(per_stratum)
    )

    lines: list[str] = [
        BEGIN_MARKER,
        "",
        "<!-- Generated by scripts/generate_current_state.py from the canonical",
        "     policy. Do not edit by hand; run the script with --write. CI runs",
        "     it with --check. -->",
        "",
        "### Machine-generated current state",
        "",
        f"- Acceptance policy: `{policy['policy_id']}`, status "
        f"**{policy['status']}**, schema `{policy['schema_version']}`, "
        f"settled in phase **{policy['phase']}**.",
        f"- Acceptance thresholds: **{policy['acceptance_thresholds']['status']}**.",
        f"- Exact-typed-decision coverage, derived: **{coverage.pinned_case_count} "
        f"of {coverage.total_case_count}** cases pinned by mandatory gates "
        f"({pinned}); **{coverage.residual_case_count}** residual "
        f"({residual_strata}).",
        f"- `residual_critical_exact_budget`: {residual['disposition']}, binding "
        f"**{str(residual['binding']).lower()}**, pooled maximum errors "
        f"**{limits['pooled_max_errors']}**, per stratum {per_stratum_text}, "
        f"basis `{residual['basis_type']}`.",
        f"- Formal parser-v3 evaluation: "
        f"**{execution['formal_evaluation_execution_state']}**, ordinal "
        f"**{execution['formal_evaluation_ordinal']}**.",
        f"- Predictions generated: **{execution['predictions_generated']}**. "
        f"Locked-label reads: **{execution['locked_label_reads']}**. Parser-v3 "
        f"runs against any locked set: "
        f"**{execution['parser_v3_runs_against_any_locked_set']}**. Sealed "
        f"`parser-v3-v2` sets constructed: "
        f"**{execution['parser_v3_v2_sealed_sets_constructed']}** "
        f"(`parser-v3-v1` was sealed and is retired; this counter is scoped to "
        f"the successor set).",
        "",
        "The block above is the policy's own finalization snapshot. The live",
        "execution and access state is carried by the ledger, and is rendered",
        "from it:",
        "",
        *_render_ledger_lines(_load_ledger()),
        "",
        "A `FINAL` policy is not a result. It records that the rule for judging",
        "a future evaluation is settled, and records nothing whatever about any",
        "parser. Specifically:",
        "",
    ]
    lines.extend(f"- {statement}" for statement in INVARIANT_STATEMENTS)
    lines.extend(["", END_MARKER])
    return "\n".join(lines)


def _splice(text: str, block: str, path: Path) -> str:
    start = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1:
        raise SystemExit(
            f"{path}: missing {BEGIN_MARKER} / {END_MARKER} sentinels; add them "
            f"before running the generator"
        )
    if end < start:
        raise SystemExit(f"{path}: end sentinel precedes begin sentinel")
    return text[:start] + block + text[end + len(END_MARKER) :]


def _extract(text: str, path: Path) -> str:
    start = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1:
        raise SystemExit(
            f"{path}: missing {BEGIN_MARKER} / {END_MARKER} sentinels; add them "
            f"before running the generator"
        )
    return text[start : end + len(END_MARKER)]


def run(write: bool, root: Path | None = None) -> int:
    root = root if root is not None else REPO_ROOT
    block = render_block()
    failures: list[str] = []
    for relative in TARGET_FILES:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        current = _extract(text, path)
        if current == block:
            continue
        if write:
            path.write_text(_splice(text, block, path), encoding="utf-8", newline="\n")
            print(f"rewrote {relative}")
            continue
        diff = "\n".join(
            difflib.unified_diff(
                current.splitlines(),
                block.splitlines(),
                fromfile=f"{relative} (committed)",
                tofile=f"{relative} (generated)",
                lineterm="",
            )
        )
        failures.append(f"{relative}: generated block is stale\n{diff}")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        print(
            "\nRun: python scripts/generate_current_state.py --write",
            file=sys.stderr,
        )
        return 1
    print("current-state generation: OK" if not write else "current-state: written")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="fail if any target document's generated block is stale",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="regenerate the block in every target document",
    )
    args = parser.parse_args(argv)
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
