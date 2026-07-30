#!/usr/bin/env python3
"""Read-only repair tooling for the parser-v3 evaluation ontology (Phase 1.2E).

Subcommands:

``facts``
    Derive a set-facts manifest mechanically from a candidate set.

``check``
    Read-only agreement check between a prospective policy and a facts
    manifest. Prints every disagreement and exits non-zero if any exists.

``normalize``
    Apply the registered ``N1``-``N6`` representational normalisations and emit
    a content-free receipt. Quarantines any case a rule cannot decide.

``compile``
    Emit the final acceptance contract. Refuses to overwrite, refuses a policy
    with unresolved thresholds, and refuses any disagreement.

``verify``
    Re-derive an existing contract and require byte-for-byte reproduction.

The tool refuses to operate on the retired ``parser_v3_v1`` namespace: that set
is SEALED, UNSPENT, UNSCORABLE and RETIRED_AS_INELIGIBLE, and no tooling in
this repository may reopen it.

The repair tooling references no parser symbol and calls no parser entry point.
It does **not** follow that no parser module is present in the process:
``jspace_observation/__init__`` eagerly imports the legacy parser, so importing
any submodule through the package already places parser code in ``sys.modules``.
The supportable claim, and the one the tests actually prove, is that the repair
modules introduce **no additional** parser dependency and invoke no parser.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from jspace_observation.parser_v3_repair_contract import (  # noqa: E402
    ContractError,
    SetCounts,
    SetSource,
    build_set_facts,
    check_agreement,
    check_contract,
    compile_contract,
    validate_policy,
    write_contract,
)
from jspace_observation.parser_v3_repair_normalization import (  # noqa: E402
    NormalizationError,
    normalize_set,
)

RETIRED_NAMESPACES: tuple[str, ...] = ("parser_v3_v1",)


class CliError(RuntimeError):
    """A command cannot proceed."""


def _refuse_retired_namespace(path: Path) -> Path:
    resolved = Path(path).resolve()
    for part in resolved.parts:
        normalised = part.casefold().replace("-", "_")
        if normalised in RETIRED_NAMESPACES:
            raise CliError(
                f"{resolved} lies in the retired namespace {part!r}; that set is "
                "SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE and this "
                "tooling will not read or rewrite it"
            )
    return resolved


def _safe(value: str | None) -> Path | None:
    """Guard an optional path argument. Every path the CLI touches goes here."""
    if value is None:
        return None
    return _refuse_retired_namespace(Path(value))


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records


def _write_json(path: Path, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_inputs(path: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for record in _read_jsonl(path):
        case_id = record.get("case_id")
        output_text = record.get("output_text")
        if not isinstance(case_id, str) or not isinstance(output_text, str):
            raise CliError(f"{path} holds a record without a case_id and output_text")
        texts[case_id] = output_text
    return texts


def cmd_facts(args: argparse.Namespace) -> int:
    labels = _refuse_retired_namespace(Path(args.labels))
    inputs = _refuse_retired_namespace(Path(args.inputs))
    policy = validate_policy(_read_json(_refuse_retired_namespace(Path(args.policy))))
    records = _read_jsonl(labels)
    texts = _load_inputs(inputs)
    members_path = _safe(args.members)
    members = _read_json(members_path) if members_path else []
    counts = SetCounts(
        sealed_object_count=args.sealed_object_count,
        total_case_count=len(records),
        residual_semantic_case_count=args.residual_semantic_case_count,
    )
    facts = build_set_facts(
        records,
        texts,
        set_id=args.set_id,
        members=members,
        counts=counts,
        gates=policy["gates"],
    )
    out = _safe(args.out)
    if out:
        _write_json(out, facts)
    else:
        print(json.dumps(facts, sort_keys=True, indent=2))
    return 0


def _set_source(args: argparse.Namespace, policy: dict[str, Any]) -> SetSource:
    """Load the set itself, so declared facts can be re-derived from it.

    Every entry point that consumes a facts manifest needs this. A manifest on
    its own is an unverifiable claim.
    """
    labels = _refuse_retired_namespace(Path(args.labels))
    inputs = _refuse_retired_namespace(Path(args.inputs))
    records = _read_jsonl(labels)
    texts = _load_inputs(inputs)
    members_path = _safe(args.members)
    members = _read_json(members_path) if members_path else []
    return SetSource(
        set_id=args.set_id,
        counts=SetCounts(
            sealed_object_count=args.sealed_object_count,
            total_case_count=len(records),
            residual_semantic_case_count=args.residual_semantic_case_count,
        ),
        records=tuple(records),
        output_texts=texts,
        members=tuple(members),
        gates=tuple(policy["gates"]),
    )


def cmd_check(args: argparse.Namespace) -> int:
    policy = _read_json(_refuse_retired_namespace(Path(args.policy)))
    facts = _read_json(_refuse_retired_namespace(Path(args.facts)))
    expected_path = _safe(args.expect_members)
    expected = _read_json(expected_path) if expected_path else None
    findings = check_agreement(
        policy,
        facts,
        set_source=_set_source(args, validate_policy(policy)),
        expected_members=expected,
    )
    if not findings:
        print("agreement: OK")
        return 0
    for finding in findings:
        print(f"{finding.code}\t{finding.subject}\t{finding.message}")
    print(f"agreement: {len(findings)} disagreement(s)")
    return 1


def cmd_normalize(args: argparse.Namespace) -> int:
    labels = _refuse_retired_namespace(Path(args.labels))
    inputs = _refuse_retired_namespace(Path(args.inputs))
    records = _read_jsonl(labels)
    texts = _load_inputs(inputs)
    normalized, quarantined, receipt = normalize_set(records, texts)
    out = _safe(args.out)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "".join(
                json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
                for record in normalized
            ),
            encoding="utf-8",
        )
    receipt_path = _safe(args.receipt)
    if receipt_path:
        _write_json(receipt_path, receipt.to_dict())
    else:
        print(json.dumps(receipt.to_dict(), sort_keys=True, indent=2))
    if quarantined:
        print(f"quarantined: {len(quarantined)} case(s)")
        # A partially quarantined migration is not a success. Reporting zero
        # would let an incomplete set advance on an unread exit code.
        return 0 if args.permissive else 1
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    policy = _read_json(_refuse_retired_namespace(Path(args.policy)))
    facts = _read_json(_refuse_retired_namespace(Path(args.facts)))
    expected_path = _safe(args.expect_members)
    expected = _read_json(expected_path) if expected_path else None
    contract = compile_contract(
        policy,
        facts,
        set_source=_set_source(args, validate_policy(policy)),
        expected_members=expected,
    )
    write_contract(_refuse_retired_namespace(Path(args.out)), contract)
    print(f"contract written: {args.out}")
    print(f"contract_sha256: {contract['contract_sha256']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    policy = _read_json(_refuse_retired_namespace(Path(args.policy)))
    facts = _read_json(_refuse_retired_namespace(Path(args.facts)))
    expected_path = _safe(args.expect_members)
    expected = _read_json(expected_path) if expected_path else None
    check_contract(
        _refuse_retired_namespace(Path(args.contract)),
        policy,
        facts,
        set_source=_set_source(args, validate_policy(policy)),
        expected_members=expected,
    )
    print("contract: byte-identical to a fresh compilation")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parser_v3_repair_cli", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    facts = sub.add_parser("facts", help="derive a set-facts manifest")
    facts.add_argument("--labels", required=True)
    facts.add_argument("--inputs", required=True)
    facts.add_argument("--policy", required=True)
    facts.add_argument("--set-id", required=True)
    facts.add_argument("--members")
    facts.add_argument("--sealed-object-count", type=int, default=0)
    facts.add_argument("--residual-semantic-case-count", type=int, default=0)
    facts.add_argument("--out")
    facts.set_defaults(func=cmd_facts)

    check = sub.add_parser("check", help="read-only policy/set agreement check")
    check.add_argument("--policy", required=True)
    check.add_argument("--facts", required=True)
    check.add_argument("--labels", required=True)
    check.add_argument("--inputs", required=True)
    check.add_argument("--set-id", required=True)
    check.add_argument("--members")
    check.add_argument("--sealed-object-count", type=int, default=0)
    check.add_argument("--residual-semantic-case-count", type=int, default=0)
    check.add_argument("--expect-members")
    check.set_defaults(func=cmd_check)

    normalize = sub.add_parser("normalize", help="apply N1-N6 and emit a receipt")
    normalize.add_argument("--labels", required=True)
    normalize.add_argument("--inputs", required=True)
    normalize.add_argument("--out")
    normalize.add_argument("--receipt")
    normalize.add_argument(
        "--permissive",
        action="store_true",
        help="exit 0 even when cases were quarantined",
    )
    normalize.set_defaults(func=cmd_normalize)

    compile_cmd = sub.add_parser("compile", help="compile the final contract")
    compile_cmd.add_argument("--policy", required=True)
    compile_cmd.add_argument("--facts", required=True)
    compile_cmd.add_argument("--labels", required=True)
    compile_cmd.add_argument("--inputs", required=True)
    compile_cmd.add_argument("--set-id", required=True)
    compile_cmd.add_argument("--members")
    compile_cmd.add_argument("--sealed-object-count", type=int, default=0)
    compile_cmd.add_argument("--residual-semantic-case-count", type=int, default=0)
    compile_cmd.add_argument("--expect-members")
    compile_cmd.add_argument("--out", required=True)
    compile_cmd.set_defaults(func=cmd_compile)

    verify = sub.add_parser("verify", help="re-derive a contract and compare bytes")
    verify.add_argument("--policy", required=True)
    verify.add_argument("--facts", required=True)
    verify.add_argument("--labels", required=True)
    verify.add_argument("--inputs", required=True)
    verify.add_argument("--set-id", required=True)
    verify.add_argument("--members")
    verify.add_argument("--sealed-object-count", type=int, default=0)
    verify.add_argument("--residual-semantic-case-count", type=int, default=0)
    verify.add_argument("--expect-members")
    verify.add_argument("--contract", required=True)
    verify.set_defaults(func=cmd_verify)

    return parser


_PATH_DESTS: frozenset[str] = frozenset(
    {
        "labels",
        "inputs",
        "policy",
        "facts",
        "members",
        "expect_members",
        "contract",
        "out",
        "receipt",
    }
)


def _guard_every_path(args: argparse.Namespace) -> None:
    """Refuse the retired namespace on *every* path argument, before any read.

    The guard runs as a pre-pass rather than inside each command so that a
    retired path cannot slip through on an argument the command happens to
    consume late, or not at all when an earlier read fails first.
    """
    for dest, value in sorted(vars(args).items()):
        if dest in _PATH_DESTS and isinstance(value, str):
            _refuse_retired_namespace(Path(value))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        _guard_every_path(args)
        return int(args.func(args))
    except (CliError, ContractError, NormalizationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
