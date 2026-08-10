"""The pinned deterministic parser for the Study 3-P0 S4 diagnostic.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
sections 8.1 and 9.

draft-v0.5 registers that S4 maps a bounded greedy completion to a member of the
answer domain or to the explicit value ``unparseable``, using a deterministic,
version-pinned parser. It does not name a module, so P0 pins one here, inside
the P0 namespace, and freezes it before the first model operation.

Two properties matter and are both testable without a model:

*Determinism.* The same completion bytes always yield the same result. There is
no locale, no regex backtracking on unbounded input, no normalization table and
no dependency outside the standard library.

*Unparseable is first class.* It is never dropped, never imputed, never silently
mapped to a domain member and never treated as incorrect without being reported
separately. A row whose completion cannot be read is retained with
``unparseable = true`` and a null value.

The parser is deliberately strict. S4 is the never-selectable diagnostic profile;
a permissive parser would quietly convert a rendering or wrapper defect into an
apparent success, which is exactly the failure mode P0 exists to detect.
"""

PARSER_ID = "study3-p0-s4-parser-v1"
UNPARSEABLE = "unparseable"

ANSWER_DOMAIN = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")

# Bytes that may surround a candidate surface without changing what was said.
_STRIPPABLE = " \t\n\r.,:;!?'\"()[]{}*`"


def parse_s4_completion(completion, displayed_labels):
    """Map one raw S4 completion to a displayed label symbol or to unparseable.

    ``displayed_labels`` is the row's four registered label symbols, in displayed
    order. S4 renders an option list and its registered instruction asks for the
    letter of the correct option, so the parser reads a label symbol, not a
    mod-10 residue.

    Returns a dict with ``value`` (a displayed label symbol or ``None``),
    ``unparseable`` (bool), ``parser_id`` and ``reason``.
    """
    if completion is None:
        return _result(None, True, "the completion is absent")
    if not isinstance(completion, str):
        return _result(None, True, "the completion is not text")
    if any(ord(ch) == 0 for ch in completion):
        return _result(None, True, "the completion carries a NUL byte")

    candidates = [label for label in displayed_labels]
    if len(set(candidates)) != len(candidates):
        return _result(None, True, "the displayed label symbols are not distinct")

    stripped = completion.strip(_STRIPPABLE)
    if stripped == "":
        return _result(None, True, "the completion carries no readable surface")

    # A bare, complete label symbol is the only accepted form. The first
    # whitespace-delimited token is read; anything longer than one symbol, or a
    # symbol outside the displayed set, stays unparseable rather than being
    # rescued by a substring search that could match commentary.
    first = stripped.split()[0].strip(_STRIPPABLE)
    if first in candidates:
        return _result(first, False, "a bare displayed label symbol was read")
    if len(first) == 1 and first.upper() in candidates:
        return _result(
            first.upper(), False,
            "a bare displayed label symbol was read after case folding")
    return _result(
        None, True,
        "the completion does not begin with a bare displayed label symbol")


def parse_s2_completion(completion):
    """Map one raw completion to a mod-10 residue surface or to unparseable.

    Registered for completeness of the parser surface. P0's S2 profile is scored
    from restricted logits and does not generate, so this path is exercised only
    by the P0 test module.
    """
    if not isinstance(completion, str):
        return _result(None, True, "the completion is not text")
    stripped = completion.strip(_STRIPPABLE)
    if stripped == "":
        return _result(None, True, "the completion carries no readable surface")
    first = stripped.split()[0].strip(_STRIPPABLE)
    if first in ANSWER_DOMAIN:
        return _result(first, False, "a bare mod-10 residue surface was read")
    return _result(
        None, True,
        "the completion does not begin with a bare mod-10 residue surface")


def _result(value, unparseable, reason):
    if unparseable and value is not None:
        raise AssertionError("an unparseable result may not carry a value")
    if not unparseable and value is None:
        raise AssertionError("a parsed result must carry a value")
    return {
        "parser_id": PARSER_ID,
        "value": value,
        "unparseable": bool(unparseable),
        "reason": reason,
    }
