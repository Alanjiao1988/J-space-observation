"""Mechanical current-state consistency check.

Phase 1.2F added this because Phase 1.2E authored a false blocking dependency
into a policy artifact after reading a stale current-state summary that had
never been updated when the experiment it described actually ran.

The check asserts one thing: no *current-state* section may simultaneously
claim that Phase 1.0C was never run and cite the committed finalized Phase 1.0C
result, and no current-state section may name Phase 1.0C as a source of parser
acceptance thresholds. Historical, dated, point-in-time entries are exempt,
because preserving them is required.

Audit findings B1-B4 rebuilt the matcher. The first version scanned line by
line with patterns forbidding a newline, so the actual Phase 1.2E defect -
hard-wrapped across three lines at roughly 76 columns - matched nothing at all.
Exemption was a substring test against common words, so writing "corrected"
anywhere on a line disabled the check for that line. Matching now runs over
whitespace-collapsed paragraph windows, and exemption is structural: a
paragraph must be anchored as historical or corrective, not merely contain a
reassuring word.

Run standalone::

    python scripts/check_current_state_consistency.py

Exit code 0 when consistent, 1 when a contradiction is found or when the
Phase 1.0C ground truth cannot be established.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]


class GroundTruthError(RuntimeError):
    """The committed Phase 1.0C result pack could not be read.

    Audit finding B4. The first version returned ``False`` here, which silently
    disabled the not-run half of the check while still printing ``OK``.
    """


#: Primary committed evidence that Phase 1.0C executed and was finalized.
#: Using the result pack rather than prose makes the ground truth a repository
#: fact instead of a per-document opinion, so a uniformly stale document cannot
#: pass by simply never mentioning the outcome.
PHASE_1_0C_DECISION = (
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/04_decision.json"
)

#: Documents and artifacts that describe the *present* state of the project.
#: Append-only ledgers and run logs are excluded on purpose: their dated entries
#: are supposed to record what was true when written.
#:
#: Audit finding B3: the first version omitted the artifact class in which the
#: Phase 1.2E defect actually occurred. A prospective policy states a present
#: blocking dependency, so it is a current-state document whatever its suffix.
CURRENT_STATE_FILES: tuple[str, ...] = (
    "reports/current_status.md",
    "docs/thread_handoff.md",
    "docs/phase1_parser_v3_v2_evaluation_policy.json",
    "docs/phase1_2f_threshold_dispositions.json",
)

#: Phrases asserting that Phase 1.0C never executed. Applied to
#: whitespace-collapsed paragraph windows, so ``[^.]`` spans line wraps.
NOT_RUN_PATTERNS: tuple[str, ...] = (
    r"1\.0C[^.]{0,160}\bNOT[ _]RUN\b",
    r"1\.0C[^.]{0,160}\bno model (?:was )?run\b",
    r"1\.0C[^.]{0,160}\b(?:has|had) not been (?:run|executed)\b",
    r"1\.0C[^.]{0,160}\b(?:was|is|were) not (?:run|executed)\b",
    r"1\.0C[^.]{0,160}\bnever (?:been )?(?:run|executed)\b",
    r"1\.0C[^.]{0,160}\bunexecuted\b",
    r"1\.0C[^.]{0,160}\bnot yet (?:been )?(?:run|executed)\b",
    r"1\.0C[^.]{0,160}\bpending execution\b",
    r"1\.0C[^.]{0,160}\bawaiting execution\b",
    r"1\.0C[^.]{0,160}\bremains blocked before model\b",
    r"1\.0C[^.]{0,160}\bBLOCKED with no model\b",
    r"\bnever (?:been )?(?:run|executed)[^.]{0,160}1\.0C",
    r"\b(?:has|had) not been (?:run|executed)[^.]{0,160}1\.0C",
    r"headroom calibration[^.]{0,160}\bNOT[ _]RUN\b",
    r"headroom calibration[^.]{0,160}\b(?:has|had) not been (?:run|executed)\b",
    r"headroom calibration[^.]{0,160}\bnever (?:been )?(?:run|executed)\b",
)

#: Phrases that only make sense if Phase 1.0C did execute. A paragraph that
#: pairs one of these with a not-run claim is self-contradictory on its face,
#: independently of the repository ground truth.
EXECUTED_PATTERNS: tuple[str, ...] = (
    r"\bINCONCLUSIVE\b",
    r"\b300\s*/\s*300\b",
    r"\b44 unresolved\b",
    r"06eec993",
)

#: A statement that Phase 1.0C supplies parser acceptance thresholds is a
#: category error regardless of where it appears.
#:
#: Audit finding B2: the first version required the literal word "parser" on
#: the same line, so "run Phase 1.0C to derive the acceptance thresholds"
#: evaded it entirely.
PARSER_DEPENDENCY_PATTERNS: tuple[str, ...] = (
    r"1\.0C[^.]{0,200}\bparser (?:acceptance |accuracy )?threshold",
    r"parser (?:acceptance |accuracy )?threshold[^.]{0,200}\b1\.0C",
    r"1\.0C[^.]{0,200}\bparser calibration\b",
    r"1\.0C[^.]{0,200}\b(?:derive|determine|supply|set|fix|choose|select)\w*"
    r"[^.]{0,80}\bthreshold",
    r"\bthreshold[^.]{0,200}\b(?:depends?|dependent|contingent|blocked) on"
    r"[^.]{0,80}1\.0C",
    r"headroom calibration is a parser[- ]accuracy calibration",
    r"headroom[^.]{0,120}calibrat\w*[^.]{0,120}\bparser (?:acceptance )?threshold",
)

#: Clauses that state the corrected fact rather than the defect. A sentence
#: whose whole point is that Phase 1.0C supplies no threshold must not be
#: reported as claiming that it does. This is deliberately narrow: it is
#: sentence-scoped and requires an explicit negation, so it cannot be satisfied
#: by a reassuring word elsewhere in the paragraph the way the first version's
#: exemption list could.
NEGATION_PATTERNS: tuple[str, ...] = (
    r"\bno\b[^.]{0,60}1\.0C[^.]{0,120}\b(?:can|could|may|does|do|will)\b",
    r"1\.0C[^.]{0,120}\b(?:is|was|are|were) not\b(?!\s*(?:yet\b|run\b|executed\b))",
    r"1\.0C[^.]{0,120}\b(?:does|do|did|can|could|will|would|must|may) not\b"
    r"(?!\s*(?:yet\b|run\b|be\s+run\b|been\s+run\b|execute\b|executed\b))",
    r"1\.0C[^.]{0,120}\b(?:cannot|neither|nor)\b",
    r"\b(?:cannot|can not|must not|may not|never|does not|do not|no)\b"
    r"[^.]{0,120}\b(?:supply|supplies|determine|determines|derive|derives|bound|"
    r"bounds|unblock|unblocks|calibrate|calibrates)\b[^.]{0,120}\bthreshold",
    r"not (?:a )?parser[- ]accuracy calibration",
    r"is not (?:a )?parser calibration",
    r"\bneither validates\b",
)

#: Anchored markers that make a paragraph historical or corrective. Audit
#: finding B2: exemption must be a property of the paragraph's structure, not a
#: reassuring word that happens to appear somewhere inside it. Matched against
#: the start of any line in the paragraph, after optional list bullets, heading
#: hashes, blockquote markers and bold delimiters.
EXEMPT_ANCHORS: tuple[str, ...] = (
    r"errat(?:um|a)\b",
    r"supersed(?:ed|es)\b",
    r"historical(?:ly)?\b",
    r"point[- ]in[- ]time\b",
    r"correction\b",
    r"as[- ]written\b",
    r"quoted (?:defect|text|claim)\b",
    r"was false when written\b",
    r"no longer true\b",
)

_ANCHOR_PREFIX = r"^[ \t]*(?:[>#*+\-]+[ \t]*)*(?:\*\*|__|`)*[ \t]*"

_EXEMPT_ANCHOR_RE = re.compile(
    "|".join(_ANCHOR_PREFIX + anchor for anchor in EXEMPT_ANCHORS),
    re.IGNORECASE | re.MULTILINE,
)

#: JSON keys whose subtree records corrected history rather than present state.
EXEMPT_JSON_KEYS: tuple[str, ...] = (
    "errata",
    "erratum",
    "superseded",
    "supersedes",
    "historical",
    "correction",
    "corrected_statement",
    "withdrawn_argument",
    "as_written",
    "quoted_defect",
)


@dataclass(frozen=True)
class Contradiction:
    """One current-state contradiction."""

    path: str
    line_number: int
    kind: str
    line: str

    def render(self) -> str:
        return f"{self.path}:{self.line_number}: [{self.kind}] {self.line.strip()[:200]}"


@dataclass(frozen=True)
class _Window:
    """A whitespace-collapsed paragraph plus a map back to line numbers."""

    text: str
    line_of: tuple[int, ...]
    start_line: int

    def line_at(self, offset: int) -> int:
        if not self.line_of:
            return self.start_line
        index = min(max(offset, 0), len(self.line_of) - 1)
        return self.line_of[index]


def _is_blockquote(block: str) -> bool:
    lines = [line for line in block.splitlines() if line.strip()]
    return bool(lines) and all(line.lstrip().startswith(">") for line in lines)


#: Markdown emphasis and code-span delimiters, elided before pattern matching.
#:
#: These carry no content, but they break contiguous phrase patterns: a
#: paragraph reading ``Phase 1.0C has **not** been run`` does not match
#: ``\b(?:has|had) not been run\b`` while the asterisks are present. That cuts
#: both ways, so eliding them removes a false positive on corrective prose *and*
#: closes an evasion in which a stale claim is emphasised into invisibility.
#: ``_`` is deliberately not elided: it is load-bearing inside identifiers such
#: as ``NOT_RUN`` and ``sealed_object_count``.
_ELIDED_MARKUP = frozenset("*`")


def _elide_markup(text: str) -> str:
    return "".join(char for char in text if char not in _ELIDED_MARKUP)


def _is_exempt(block: str) -> bool:
    """True when the paragraph is structurally marked historical or corrective."""
    if _is_blockquote(block):
        return True
    return bool(_EXEMPT_ANCHOR_RE.search(block))


def _collapse(block_lines: Sequence[tuple[int, str]]) -> _Window:
    chars: list[str] = []
    line_of: list[int] = []
    for number, line in block_lines:
        for char in line:
            if char in _ELIDED_MARKUP:
                continue
            if char.isspace():
                if chars and chars[-1] == " ":
                    continue
                chars.append(" ")
            else:
                chars.append(char)
            line_of.append(number)
        if chars and chars[-1] != " ":
            chars.append(" ")
            line_of.append(number)
    return _Window("".join(chars), tuple(line_of), block_lines[0][0])


def _windows(text: str) -> list[_Window]:
    """Split ``text`` into whitespace-collapsed paragraph windows.

    Paragraphs are separated by blank lines. Collapsing whitespace is what lets
    a pattern span a hard line wrap, which is the failure mode audit finding B1
    identified.
    """
    windows: list[_Window] = []
    block_lines: list[tuple[int, str]] = []

    def flush() -> None:
        if not block_lines:
            return
        block = "\n".join(line for _, line in block_lines)
        if not _is_exempt(block):
            windows.append(_collapse(block_lines))
        block_lines.clear()

    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            block_lines.append((number, line))
        else:
            flush()
    flush()
    return windows


def _search(window: _Window, patterns: Sequence[str]) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, window.text, re.IGNORECASE)
        if match and not _is_negated(window.text, match):
            return match
    return None


def _enclosing_sentence(text: str, match: re.Match[str]) -> str:
    """Return the sentence containing ``match``.

    Every pattern in this module forbids a full stop inside the match, so the
    sentence boundaries are simply the nearest full stops on either side.
    """
    left = text.rfind(".", 0, match.start())
    right = text.find(".", match.end())
    start = 0 if left < 0 else left + 1
    end = len(text) if right < 0 else right
    return text[start:end]


def _is_negated(text: str, match: re.Match[str]) -> bool:
    """True when the enclosing sentence states the corrected fact."""
    sentence = _enclosing_sentence(text, match)
    return any(
        re.search(pattern, sentence, re.IGNORECASE) for pattern in NEGATION_PATTERNS
    )


def _json_windows(text: str) -> list[_Window]:
    """Yield one window per leaf string of a JSON document.

    A pretty-printed JSON artifact contains no blank lines, so paragraph
    splitting would collapse the whole file into a single window and pair an
    errata quotation with an unrelated present-state claim. Walking the parsed
    structure instead keeps each statement separate and lets an errata subtree
    be exempted by key.
    """
    try:
        payload = json.loads(text)
    except ValueError:
        return []

    lines = text.splitlines()

    def line_of(value: str) -> int:
        needle = json.dumps(value, ensure_ascii=False)[1:-1][:60]
        for number, line in enumerate(lines, start=1):
            if needle and needle in line:
                return number
        return 1

    windows: list[_Window] = []

    def walk(node: object, exempt: bool) -> None:
        if isinstance(node, str):
            if exempt:
                return
            collapsed = re.sub(r"\s+", " ", _elide_markup(node))
            number = line_of(node)
            windows.append(
                _Window(collapsed, tuple([number] * len(collapsed)), number)
            )
        elif isinstance(node, dict):
            for key, value in node.items():
                key_exempt = exempt or any(
                    marker in str(key).lower() for marker in EXEMPT_JSON_KEYS
                )
                walk(value, key_exempt)
        elif isinstance(node, list):
            for value in node:
                walk(value, exempt)

    walk(payload, False)
    return windows


def phase_1_0c_was_finalized(root: Path | None = None) -> bool:
    """True when the committed Phase 1.0C result pack records a final decision.

    This is the repository-level ground truth the current-state documents are
    checked against. It raises rather than returning ``False`` when the pack is
    missing or unreadable, so a broken checkout cannot silently disable half of
    the check (audit finding B4).
    """
    base = root or REPO_ROOT
    decision = base / PHASE_1_0C_DECISION
    if not decision.exists():
        raise GroundTruthError(
            f"Phase 1.0C decision pack is missing at {PHASE_1_0C_DECISION}; the "
            "current-state check cannot establish its ground truth"
        )
    try:
        payload = json.loads(decision.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GroundTruthError(
            f"Phase 1.0C decision pack at {PHASE_1_0C_DECISION} is unreadable: {exc}"
        ) from exc
    verdict = payload.get("track_b_decision")
    if verdict not in {
        "CONTROLS_ONLY",
        "HEADROOM_CELLS_SELECTED",
        "INCONCLUSIVE",
        "NO_USABLE_CELLS",
    }:
        raise GroundTruthError(
            f"Phase 1.0C decision pack records an unrecognised verdict {verdict!r}"
        )
    return True


def scan_text(path: str, text: str, *, executed: bool) -> list[Contradiction]:
    """Return every current-state contradiction in ``text``.

    ``executed`` is the repository-level fact that Phase 1.0C ran and was
    finalized.
    """
    found: list[Contradiction] = []

    windows = _json_windows(text) if path.endswith(".json") else _windows(text)
    for window in windows:
        dependency = _search(window, PARSER_DEPENDENCY_PATTERNS)
        if dependency is not None:
            found.append(
                Contradiction(
                    path,
                    window.line_at(dependency.start()),
                    "PARSER_THRESHOLD_DEPENDENCY",
                    dependency.group(0),
                )
            )
        not_run = _search(window, NOT_RUN_PATTERNS)
        if not_run is None:
            continue
        if executed:
            found.append(
                Contradiction(
                    path,
                    window.line_at(not_run.start()),
                    "NOT_RUN_VS_FINALIZED",
                    not_run.group(0),
                )
            )
        elif _search(window, EXECUTED_PATTERNS) is not None:
            found.append(
                Contradiction(
                    path,
                    window.line_at(not_run.start()),
                    "NOT_RUN_VS_CITED_RESULT",
                    not_run.group(0),
                )
            )
    return found


def scan_files(
    paths: Iterable[str] = CURRENT_STATE_FILES, root: Path | None = None
) -> list[Contradiction]:
    """Scan the registered current-state documents."""
    base = root or REPO_ROOT
    executed = phase_1_0c_was_finalized(base)
    found: list[Contradiction] = []
    for relative in paths:
        target = base / relative
        if not target.exists():
            continue
        found.extend(
            scan_text(
                relative,
                target.read_text(encoding="utf-8", errors="replace"),
                executed=executed,
            )
        )
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=None, help="repository root (defaults to this checkout)"
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else REPO_ROOT

    try:
        found = scan_files(root=root)
    except GroundTruthError as exc:
        print(f"current-state consistency: FAILED\n  {exc}", file=sys.stderr)
        return 1

    if not found:
        print("current-state consistency: OK")
        return 0

    print("current-state consistency: FAILED", file=sys.stderr)
    for item in found:
        print("  " + item.render(), file=sys.stderr)
    print(
        "\nPhase 1.0C is recorded in this repository as executed and finalized. "
        "A current-state section must not claim it was never run, and must not "
        "name it as a source of parser acceptance thresholds.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
