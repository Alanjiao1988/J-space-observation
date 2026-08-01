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

#: Leading decoration that may precede an anchor word: indentation, blockquote
#: markers, list bullets, heading hashes, bold and code delimiters.
#:
#: This must be a single character class under a single quantifier. The earlier
#: nested form ``(?:[>#*+\-]+[ \t]*)*`` is ambiguous: a run of N dashes can be
#: partitioned among the inner ``+`` and the outer ``*`` in exponentially many
#: ways, so a line such as a ``# ----------------`` section separator that then
#: fails to match any anchor sends the engine into catastrophic backtracking.
#: The defect was latent until Phase 1.2G widened the scanned file list to
#: include a Python module full of such separators, at which point the checker
#: stopped terminating in practical time.
_ANCHOR_PREFIX = r"^[ \t>#*+\-_`]*"

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


def _is_exempt_json_key(key: object) -> bool:
    """True when a JSON key marks its subtree as quoted or historical.

    The match is on whole underscore-separated words at the **start** of the
    key, not on substrings and not anywhere in the key. Second re-review
    finding R2-R-01 found substring matching too permissive: a key such as
    ``not_historical_current_state`` contains ``historical`` and silently
    exempted a live claim. Matching the marker anywhere in the word sequence
    has the same defect, because the negation still precedes it. A leading
    match accepts ``historical_note`` and ``as_written`` while rejecting
    ``not_historical_current_state``, and it reflects how the convention is
    actually used: the marker names what the subtree *is*.
    """
    words = [word for word in re.split(r"[^a-z0-9]+", str(key).lower()) if word]
    if not words:
        return False
    return any(
        words[: len(marker_words)] == marker_words
        for marker_words in (marker.split("_") for marker in EXEMPT_JSON_KEYS)
    )

#: Phase 1.2G. Documents scanned for superseded coverage figures and for
#: statements that a later round falsified.
#:
#: This is a separate registry from :data:`CURRENT_STATE_FILES` because the
#: two checks have different scopes. The Phase 1.0C check asks whether a
#: document contradicts a repository ground truth. This check asks whether a
#: document restates a figure that a later round corrected. The public stratum
#: policy is a design artifact rather than a current-state summary, but it is
#: where the 90/30 split survived the Phase 1.2F correction, so it is scanned.
SUPERSEDED_FIGURE_FILES: tuple[str, ...] = (
    "reports/current_status.md",
    "docs/thread_handoff.md",
    "docs/phase1_parser_v3_v2_evaluation_policy.json",
    "docs/phase1_2f_threshold_dispositions.json",
    "docs/phase1_parser_v3_v2_stratum_policy.md",
    "docs/phase1_2g_conformance_policy_protocol.md",
    "reports/phase1_2g_conformance_policy.md",
    "reports/phase1_2g_audit_findings.md",
    "reports/phase1_2f_parser_acceptance_policy.md",
    "tests/test_parser_v3_repair.py",
    "paper/methods_ledger.md",
)

#: Figures and claims that later rounds superseded. Each entry is
#: ``(pattern, reason, negatable)``.
#:
#: These are *not* forbidden words. Every one of them may appear inside an
#: erratum, a supersession record, or an explicitly historical paragraph; the
#: same anchor and JSON-key exemptions used by the Phase 1.0C check apply. What
#: they may not do is appear as a live assertion.
#:
#: ``negatable`` says whether the sentence-level negation guard applies. It is
#: ``False`` for claims that contain a negation as part of the claim itself.
#: The withdrawn comparator argument is the case in point: "not worse than it
#: is not evidence of fitness" is the assertion, so a guard that looks for the
#: word "not" would exempt exactly the sentence it exists to catch.
SUPERSEDED_FIGURE_PATTERNS: tuple[tuple[str, str, bool], ...] = (
    (
        r"\b90 of 120\b",
        "the mandatory gates pin 80 of 120 cases, not 90; S06 is not pinned",
        True,
    ),
    (
        r"\bninety of a hundred and twenty\b",
        "the mandatory gates pin eighty of a hundred and twenty cases, not "
        "ninety; a spelled-out figure is the same claim as a numeric one",
        True,
    ),
    (
        r"\bthirty that are free\b",
        "forty cases are free of a pinning gate, not thirty",
        True,
    ),
    (
        r"\bresidual (?:critical )?strata are[^.]{0,40}S04,? S05 and S09\b",
        "the residual strata are S04, S05, S06 and S09",
        True,
    ),
    (
        r"\bS04,? S05,? (?:and )?S09\b(?![^.]{0,20}S06)[^.]{0,60}\b(?:30|thirty) cases\b",
        "the residual population is 40 cases across four strata",
        True,
    ),
    (
        r"\bthree (?:adversarial |residual |critical )*strata\b",
        "four strata are residual, not three",
        True,
    ),
    (
        r"\bS06\b[^.]{0,60}\b(?:is|are|was|were|remains?|stays?)\s+pinn?ed\b",
        "S06 carries a zero-error gate but its registered error definition does "
        "not pin exact typed-decision agreement",
        True,
    ),
    (
        r"\bpinn?ed strata\b[^.]{0,80}\bS06\b",
        "S06 is not among the pinned strata",
        True,
    ),
    (
        r"\bexecute\b[^.]{0,80}\bcalibration protocol\b",
        "the parser-error-budget calibration protocol is SUPERSEDED_UNEXECUTED "
        "and is not the next gate",
        True,
    ),
    (
        r"\bregister a downstream parser-error budget\b",
        "the downstream error budget was the secondary dependency and is moot; "
        "Phase 1.2G resolved the primary one",
        True,
    ),
    (
        r"\b(?:11\s*/\s*11|11 of 11)\b[^.]{0,40}digest",
        "the protected-digest registry holds 12 entries",
        True,
    ),
    (
        r"\bparser-v3 holdout constructed but NOT SEALED\b",
        "parser-v3-v1 was sealed and is now SEALED / UNSPENT / UNSCORABLE / "
        "RETIRED_AS_INELIGIBLE; no eligible sealed parser-v3 set exists",
        False,
    ),
    (
        r"\b(?:overall_exact_typed_decision_minimum|critical_stratum_floor)\b"
        r"[^.]{0,120}\bREMOVE_REDUNDANT\b",
        "the canonical dispositions are REPLACE_HARD and "
        "MERGE_WITH_EXISTING_GATE; neither metric was deleted",
        False,
    ),
    (
        r"\bfailed its own locked evaluation\b[^.]{0,140}"
        r"\bnot evidence of fitness\b",
        "this comparator argument was withdrawn as unsound in Phase 1.2F "
        "finding A4",
        False,
    ),
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
    """True when the whole paragraph is structurally marked as quoted material.

    Only a blockquote qualifies. A blockquote is a block-level Markdown
    construct whose entire content is quotation, so exempting all of it is as
    narrow as the structure that justifies it, which is the principle audit
    finding B2 established and re-review finding R-01 sharpened.

    An inline anchor such as ``Erratum:`` does **not** exempt its paragraph.
    Second re-review finding R2-R-01 found that it did, so a live claim on the
    third line of a paragraph whose first line began ``Erratum:`` was never
    scanned. Anchored *lines* are redacted individually instead; see
    :func:`_redact_anchored_lines`.
    """
    return _is_blockquote(block)


#: A markdown table's delimiter row, e.g. ``| --- | --- |``.
#:
#: Deliberately not a regular expression. The earlier pattern
#: ``^[ \t]*\|?[ \t:|-]*-{2,}[ \t:|-]*\|?[ \t]*$`` has two quantified
#: sub-expressions that both match ``-``, so a long dash run followed by a
#: non-matching character backtracks over every partition of the run. Second
#: re-review finding R2-NEW-02 measured 10.6 s on a 1,000-dash row. This
#: character-set test is linear.
_TABLE_DELIMITER_CHARS = frozenset(" \t:|-")


def _is_table_delimiter(line: str, columns: int | None = None) -> bool:
    """True when ``line`` is a Markdown delimiter row of ``columns`` cells.

    Third re-review finding R3-NEW-03: the earlier test accepted any
    dash-containing line, so a bare ``---`` under a two-column header was read
    as that table's delimiter and enabled column redaction on text that is not
    a table at all. Every cell must itself be a delimiter, and when the header's
    column count is supplied the counts must agree.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if not set(stripped) <= _TABLE_DELIMITER_CHARS:
        return False
    cells, lead = _split_row(line)
    cells = cells[lead:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    if not cells:
        return False
    if not all("--" in cell for cell in cells):
        return False
    return columns is None or len(cells) == columns


#: An exempt anchor at the start of a single table cell.
_CELL_ANCHOR_RE = re.compile(
    "|".join(_ANCHOR_PREFIX + anchor for anchor in EXEMPT_ANCHORS),
    re.IGNORECASE,
)


def _split_row(line: str) -> tuple[list[str], int]:
    """Split a markdown table row into raw parts plus the first cell's index."""
    parts = line.split("|")
    lead = 1 if parts and not parts[0].strip() else 0
    return parts, lead


def _quoted_columns(block_lines: Sequence[tuple[int, str]]) -> set[int]:
    """Indices of table columns whose header cell is an exempt anchor.

    A defect register is a table of quotations: one column restates a figure or
    a claim precisely because a later round retired it. Labelling a *column* is
    a structural signal in the sense audit finding B2 required, unlike a
    reassuring word buried in prose.

    Only that column is exempt. Post-remediation re-review finding R-01 found
    the earlier rule exempting the whole table, so a "Remediation" cell in the
    same table could assert a superseded figure and go unreported. The header
    must be a real table header: a row containing a cell delimiter, immediately
    followed by a delimiter row.
    """
    lines = [line for _, line in block_lines if line.strip()]
    if len(lines) < 2:
        return set()
    header, delimiter = lines[0], lines[1]
    if "|" not in header:
        return set()
    parts, lead = _split_row(header)
    cells = parts[lead:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    if not _is_table_delimiter(delimiter, columns=len(cells)):
        return set()
    return {
        index
        for index, cell in enumerate(cells)
        if _CELL_ANCHOR_RE.search(cell.strip())
    }


def _redact_anchored_lines(
    block_lines: Sequence[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Blank each line that opens with an exempt anchor, keeping the others.

    Second re-review finding R2-R-01: an anchor anywhere in a paragraph used to
    exempt the entire paragraph, so a live claim two lines below an ``Erratum:``
    opener was never scanned. The anchor marks the statement it introduces, not
    everything that follows it, so the redaction is line-scoped. A correction
    that genuinely spans several lines should be a blockquote, which is the
    repository's existing structural convention for quoted material.
    """
    return [
        (number, " " * len(line) if _EXEMPT_ANCHOR_RE.search(line) else line)
        for number, line in block_lines
    ]


def _redact_quoted_columns(
    block_lines: Sequence[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Blank the cells of any exempt column, leaving the rest of the table."""
    exempt = _quoted_columns(block_lines)
    if not exempt:
        return list(block_lines)
    redacted: list[tuple[int, str]] = []
    for number, line in block_lines:
        if "|" not in line:
            redacted.append((number, line))
            continue
        parts, lead = _split_row(line)
        for index in exempt:
            position = lead + index
            if position < len(parts):
                parts[position] = " " * len(parts[position])
        redacted.append((number, "|".join(parts)))
    return redacted


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
            windows.append(
                _collapse(_redact_anchored_lines(_redact_quoted_columns(block_lines)))
            )
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


def _search_raw(window: _Window, pattern: str) -> re.Match[str] | None:
    """Match without applying the Phase 1.0C negation guard.

    Third re-review finding R3-NEW-02: :func:`scan_superseded_figures` called
    :func:`_search`, which applies the Phase 1.0C guard unconditionally. A
    superseded-figure pattern registered ``negatable=False`` was therefore still
    suppressed whenever its sentence happened to contain an unrelated Phase 1.0C
    denial, so the non-negatable registration bought nothing. The two checks ask
    different questions and must not share a guard.
    """
    return re.search(pattern, window.text, re.IGNORECASE)


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
    """Yield one window per leaf string, plus one per flat record, of a JSON doc.

    A pretty-printed JSON artifact contains no blank lines, so paragraph
    splitting would collapse the whole file into a single window and pair an
    errata quotation with an unrelated present-state claim. Walking the parsed
    structure instead keeps each statement separate and lets an errata subtree
    be exempted by key.

    Third re-review finding R3-NEW-04: leaf-only windows cannot see a claim that
    is spread across sibling fields. A record such as
    ``{"threshold_id": "critical_stratum_floor", "disposition":
    "REMOVE_REDUNDANT"}`` asserts a retired disposition, but no single leaf
    contains both halves, so a two-part pattern could never match. Each mapping
    therefore also contributes a window joining its own scalar fields as
    ``key: value`` pairs, separated by ``;`` rather than ``.`` so that a
    sentence-scoped pattern can span two fields of one record. Nested mappings
    are not flattened into the parent, so the join cannot manufacture an
    adjacency the document does not have.
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

    def add(collapsed: str, number: int) -> None:
        windows.append(_Window(collapsed, tuple([number] * len(collapsed)), number))

    def walk(node: object, exempt: bool) -> None:
        if isinstance(node, str):
            if exempt:
                return
            add(re.sub(r"\s+", " ", _elide_markup(node)), line_of(node))
        elif isinstance(node, dict):
            if not exempt:
                fields = [
                    f"{key}: {value}"
                    for key, value in node.items()
                    if isinstance(value, (str, int, float, bool))
                    and not _is_exempt_json_key(key)
                ]
                if len(fields) > 1:
                    joined = re.sub(r"\s+", " ", _elide_markup("; ".join(fields)))
                    anchor = next(
                        (
                            line_of(value)
                            for value in node.values()
                            if isinstance(value, str)
                        ),
                        1,
                    )
                    add(joined, anchor)
            for key, value in node.items():
                key_exempt = exempt or _is_exempt_json_key(key)
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


def scan_superseded_figures(path: str, text: str) -> list[Contradiction]:
    """Return every live restatement of a superseded figure in ``text``.

    Phase 1.2G. Phase 1.2F corrected the gate-coverage split in the policy JSON
    and then left the old figures standing in the public stratum policy, the
    calibration protocol, and the surviving criterion's own prose. A prose
    review had already passed on each of those files.

    The same exemption machinery as the Phase 1.0C check applies, so an
    erratum, a supersession record, or an explicitly historical paragraph may
    still quote the old figure. Without that, the record could not be
    corrected, which is the failure mode that produced the false Phase 1.2E
    account in the first place.
    """
    found: list[Contradiction] = []
    windows = _json_windows(text) if path.endswith(".json") else _windows(text)
    for window in windows:
        for pattern, reason, negatable in SUPERSEDED_FIGURE_PATTERNS:
            match = _search_raw(window, pattern)
            if match is None:
                continue
            # A sentence whose point is that the old figure is wrong must not
            # be reported as asserting it.
            if negatable and _is_superseded_negated(window.text, match):
                continue
            found.append(
                Contradiction(
                    path,
                    window.line_at(match.start()),
                    "SUPERSEDED_FIGURE",
                    f"{match.group(0)} - {reason}",
                )
            )
    return found


#: Sentence-scoped clauses that state a superseded figure in order to deny it.
#: Deliberately narrow, and required to sit in the same sentence as the match,
#: so a reassuring word elsewhere in the paragraph cannot buy an exemption.
#:
#: Third re-review finding R3-NEW-02 narrowed these further. A bare ``not`` or
#: ``does not`` anywhere in the sentence used to exempt the match, so
#: "The gates pin 90 of 120 cases, which does not meet the target" — a live
#: assertion of the retired figure — was suppressed by a negation aimed at
#: something else entirely. A denial now qualifies only when it is *about the
#: figure*: a corrective contrast, an explicit falsity verb, or a supersession
#: marker.
SUPERSEDED_NEGATION_PATTERNS: tuple[str, ...] = (
    r"\bnot\s+(?:\*\*)?(?:\d+|ninety|thirty|three|S\d\d)\b",
    r"\b(?:was|is|were|are)\s+(?:already\s+)?"
    r"(?:wrong|false|incorrect|superseded|corrected|retired|withdrawn)\b",
    r"\bno longer\b",
    r"\b(?:rather than|instead of)\b",
    r"\bpreviously\s+(?:listed|gave|recorded|said|stated|read)\b",
    r"\bused to\s+(?:say|read|state|record)\b",
    r"\bsupersed(?:ed|es)\b",
)


def _is_superseded_negated(text: str, match: re.Match[str]) -> bool:
    """True when the enclosing sentence denies the superseded figure."""
    sentence = _enclosing_sentence(text, match)
    return any(
        re.search(pattern, sentence, re.IGNORECASE)
        for pattern in SUPERSEDED_NEGATION_PATTERNS
    )


def scan_files(
    paths: Iterable[str] = CURRENT_STATE_FILES, root: Path | None = None
) -> list[Contradiction]:
    """Scan the registered current-state documents.

    A registered file that does not exist is itself reported. Audit finding
    B11 observed that silently skipping a missing path lets the effective
    coverage of this checker shrink without any test failing: delete or rename
    a scanned document and the checker keeps reporting success over a smaller
    set. Registration is a claim that the document is scanned, so an
    unscannable registration is a defect in the checker's own contract.
    """
    base = root or REPO_ROOT
    executed = phase_1_0c_was_finalized(base)
    found: list[Contradiction] = []
    for relative in paths:
        target = base / relative
        if not target.exists():
            found.append(
                Contradiction(
                    path=relative,
                    line_number=0,
                    kind="MISSING_REGISTERED_FILE",
                    line=(
                        "registered for the Phase 1.0C current-state scan but "
                        "not present in the repository"
                    ),
                )
            )
            continue
        found.extend(
            scan_text(
                relative,
                target.read_text(encoding="utf-8", errors="replace"),
                executed=executed,
            )
        )
    for relative in SUPERSEDED_FIGURE_FILES:
        target = base / relative
        if not target.exists():
            found.append(
                Contradiction(
                    path=relative,
                    line_number=0,
                    kind="MISSING_REGISTERED_FILE",
                    line=(
                        "registered for the superseded-figure scan but not "
                        "present in the repository"
                    ),
                )
            )
            continue
        found.extend(
            scan_superseded_figures(
                relative, target.read_text(encoding="utf-8", errors="replace")
            )
        )
    found.extend(check_calibration_protocol_is_superseded(base))
    return found


#: The calibration protocol's own status line. Phase 1.2G marked it superseded
#: and unexecuted; a later edit must not quietly restore it to pending work.
CALIBRATION_PROTOCOL = "docs/phase1_2f_parser_error_budget_calibration_protocol.md"


def check_calibration_protocol_is_superseded(
    root: Path | None = None,
) -> list[Contradiction]:
    """Require the calibration protocol to stay marked superseded and unrun.

    A protocol that is merely "registered, not executed" reads as pending work.
    Phase 1.2G resolved the criterion it existed to unblock, so its status must
    say so, and its execution count must stay zero.
    """
    base = root or REPO_ROOT
    target = base / CALIBRATION_PROTOCOL
    if not target.exists():
        # Deleting the protocol must not be a way to satisfy the check that
        # governs it. Post-remediation re-review finding B-10: this branch
        # returned an empty list, so a missing target reported clean while the
        # two loops in ``scan_files`` reported their missing targets.
        return [
            Contradiction(
                CALIBRATION_PROTOCOL,
                0,
                "MISSING_REGISTERED_FILE",
                (
                    "registered for the calibration-protocol supersession check "
                    "but not present in the repository"
                ),
            )
        ]
    text = target.read_text(encoding="utf-8", errors="replace")
    found: list[Contradiction] = []
    if "SUPERSEDED_UNEXECUTED" not in text:
        found.append(
            Contradiction(
                CALIBRATION_PROTOCOL,
                1,
                "CALIBRATION_PROTOCOL_NOT_SUPERSEDED",
                "status must be SUPERSEDED_UNEXECUTED",
            )
        )
    if "**Times executed:** 0" not in text:
        found.append(
            Contradiction(
                CALIBRATION_PROTOCOL,
                1,
                "CALIBRATION_PROTOCOL_EXECUTION_COUNT",
                "the protocol must record that it has been executed 0 times",
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
