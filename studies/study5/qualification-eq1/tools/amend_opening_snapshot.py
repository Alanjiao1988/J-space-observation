#!/usr/bin/env python3
"""Amend the Study 5-EQ1 opening inventory snapshot with its NSG baseline.

The opening snapshot was captured before network security groups were part of
the snapshot field table. They were added only after OA-001 authorised one
additive rule, so the opening snapshot has no NSG subtree to compare against and
the closing check would otherwise report every existing rule as an addition.

That omission cannot be fixed by re-capturing, because the authorised rule now
exists. It is instead repaired **by reconstruction from evidence recorded before
the change was applied**: step `P-0/P0-005` recorded the full rule listing of
both in-scope NSGs immediately before the rule was created.

This tool makes that reconstruction explicit rather than hand-edited:

1. it reads the original opening snapshot, which is never modified;
2. it takes the NSG subtree from a snapshot captured after the change;
3. it removes exactly the rules registered as ``nsg_rule_added`` in the
   expected-deltas file;
4. it checks the result against the independently recorded pre-change listing,
   and refuses to write anything if the two disagree;
5. it writes a new artifact that is clearly labelled as reconstructed, carrying
   its own provenance.

The original opening snapshot stays byte-identical, so the reconstruction can
always be audited against it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The rule listing observed at P-0/P0-005 immediately BEFORE the OA-001 rule was
# created, expressed as {nsg: {rule_name: priority}}. This is the independent
# check: if removing the registered additions does not reproduce exactly this,
# the reconstruction is wrong and nothing is written.
PRE_CHANGE_LISTING: dict[str, dict[str, int]] = {
    "a100-nsg": {"allow-ssh": 1000},
    "cpuserver-nsg": {"SSH": 300},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reconstruct(
    current_nsgs: list[dict[str, Any]], expected: dict[str, Any]
) -> list[dict[str, Any]]:
    additions = {
        (str(d["nsg"]), str(d["rule"]))
        for d in expected.get("expected_deltas", [])
        if d.get("kind") == "nsg_rule_added"
    }

    rebuilt: list[dict[str, Any]] = []
    for nsg in current_nsgs:
        kept = [
            rule
            for rule in nsg.get("rules", [])
            if (str(nsg["name"]), str(rule["name"])) not in additions
        ]
        rebuilt.append({**nsg, "rule_count": len(kept), "rules": kept})
    return rebuilt


def verify(rebuilt: list[dict[str, Any]]) -> list[str]:
    """Check the reconstruction against the recorded pre-change listing."""

    problems: list[str] = []
    observed = {
        str(nsg["name"]): {
            str(rule["name"]): rule.get("priority") for rule in nsg.get("rules", [])
        }
        for nsg in rebuilt
    }
    for nsg_name, rules in PRE_CHANGE_LISTING.items():
        if nsg_name not in observed:
            problems.append(f"{nsg_name} is absent from the reconstruction")
            continue
        if observed[nsg_name] != rules:
            problems.append(
                f"{nsg_name} reconstructs to {observed[nsg_name]}, but the "
                f"pre-change listing recorded {rules}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opening", required=True)
    parser.add_argument("--nsg-from", required=True)
    parser.add_argument("--expected-deltas", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    opening_text = Path(args.opening).read_text(encoding="utf-8")
    opening = json.loads(opening_text)
    current = json.loads(Path(args.nsg_from).read_text(encoding="utf-8"))
    expected = json.loads(Path(args.expected_deltas).read_text(encoding="utf-8"))

    rebuilt = reconstruct(current.get("network_security_groups", []), expected)
    problems = verify(rebuilt)
    if problems:
        for problem in problems:
            print(f"RECONSTRUCTION REJECTED: {problem}")
        return 1

    amended = {
        **opening,
        "network_security_group_count": len(rebuilt),
        "network_security_groups": rebuilt,
        "amended": True,
        "amended_at_utc": utc_now(),
        "amendment_reason": (
            "The opening snapshot predates the inclusion of network security "
            "groups in the snapshot field table. The NSG subtree here is "
            "reconstructed, not captured: it is the post-change listing with "
            "the rules registered in expected_deltas.json removed, checked "
            "against the rule listing independently recorded at P-0/P0-005 "
            "immediately before the change was applied."
        ),
        "nsg_subtree_is_reconstructed_not_captured": True,
        "reconstruction_verified_against_pre_change_listing": True,
        "original_opening_snapshot": args.opening,
        "original_opening_snapshot_sha256": sha256_text(opening_text),
        "original_opening_snapshot_unmodified": True,
        "expected_deltas_artifact": args.expected_deltas,
        "expected_deltas_sha256": sha256_text(
            Path(args.expected_deltas).read_text(encoding="utf-8")
        ),
    }

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(amended, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print(f"{args.out}  sha256 {sha256_text(text)}")
    for nsg in rebuilt:
        names = [r["name"] for r in nsg["rules"]]
        print(f"  {nsg['name']}: {nsg['rule_count']} rule(s) {names}")
    print("reconstruction verified against the P-0/P0-005 pre-change listing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
