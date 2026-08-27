#!/usr/bin/env python3
"""Read-only Azure inventory snapshot for Study 5-EQ1.

Authority section 2 requires a read-only inventory to be recorded before the
first write and again at the end, and registers any difference between the two
snapshots -- other than blob count and byte totals -- as a hard blocker.

Two properties matter more than convenience here:

**It cannot write.** Every Azure invocation goes through :func:`_az`, which
refuses any argument vector that is not on ``READ_ONLY_COMMANDS``. A verb such
as ``create``, ``delete``, ``start`` or ``update`` is rejected before the
subprocess is spawned, so the freeze in section 2 is enforced by the tool and
not only by intent. Container listing deliberately uses the *management-plane*
read rather than a data-plane call, so no storage key and no SAS is ever
required (section 2.8) and no role assignment is consulted or changed
(section 2.9).

**It cannot leak an identity.** Section 2.8 permits only salted identity hashes
and the already-published safe names to be committed. Names registered in
authority section 14 pass through in the clear; every other name, and every
subscription or tenant id, is replaced by a salted SHA-256. The salt is read
from the environment, is generated fresh per invocation, and is never written
to the snapshot (section 14).

Usage::

    python tools/azure_inventory.py --out inventory/opening_snapshot.json
    python tools/azure_inventory.py --out inventory/closing_snapshot.json
    python tools/azure_inventory.py --compare inventory/opening_snapshot.json \
                                    inventory/closing_snapshot.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SALT_ENV = "STUDY5_EQ1_INVENTORY_SALT"

# Names already published in authority section 14 and in the Study 4F-M1
# record. These may appear in a committed artifact in the clear.
PUBLISHED_SAFE_NAMES = frozenset(
    {
        "J-space",
        "s4fm11ca457e105b29b7",
        "a100-vm",
        "cpuserver",
        "models",
        "oci",
        "runs",
        "logs",
        "seals",
        "handoff",
        "a100-nsg",
        "cpuserver-nsg",
        "allow-ssh",
        "allow-ssh-study5-eq1",
        "SSH",
    }
)

_PUBLISHED_BY_CASEFOLD = {name.casefold(): name for name in PUBLISHED_SAFE_NAMES}

# The complete set of Azure invocations this tool is permitted to make. Each
# entry is matched as a prefix of the argument vector. Nothing that mutates
# state appears here, and nothing outside this list can be executed.
READ_ONLY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("cloud", "show"),
    ("account", "show"),
    ("group", "list"),
    ("vm", "list"),
    ("storage", "account", "list"),
    ("network", "nsg", "list"),
    ("rest", "--method", "get"),
)

# Differences that authority section 2 explicitly tolerates between the opening
# and the closing snapshot. Everything else is drift unless it is registered in
# an expected-deltas file bound to an operator amendment.
TOLERATED_DRIFT_KEYS = frozenset({"blob_count", "blob_bytes"})

# The NSG subtree is diffed structurally, by rule identity, rather than through
# the generic flattener. One added rule would otherwise produce a dozen
# unrelated-looking flattened differences, which is unreadable and impossible to
# register precisely as an expected delta.
STRUCTURAL_SUBTREES = ("network_security_groups",)

# Keys that describe the *artifact* rather than the *resources*. The closing
# check compares resource state, so provenance bookkeeping must not register as
# drift -- otherwise the amended opening snapshot would fail against its own
# successor purely because it carries an explanation of how it was built.
ARTIFACT_METADATA_KEYS = frozenset(
    {
        "captured_at_utc",
        "amended",
        "amended_at_utc",
        "amendment_reason",
        "nsg_subtree_is_reconstructed_not_captured",
        "reconstruction_verified_against_pre_change_listing",
        "original_opening_snapshot",
        "original_opening_snapshot_sha256",
        "original_opening_snapshot_unmodified",
        "expected_deltas_artifact",
        "expected_deltas_sha256",
    }
)


class ReadOnlyViolation(RuntimeError):
    """Raised when a non-read-only Azure invocation is attempted."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _salt() -> str:
    salt = os.environ.get(SALT_ENV)
    if not salt:
        raise SystemExit(
            f"{SALT_ENV} is not set. Authority section 14 requires a fresh salt "
            "per invocation, and it must never be committed."
        )
    return salt


def salted(value: str | None, salt: str) -> str | None:
    """Return a committable identifier for ``value``.

    A published safe name is returned in its canonical published spelling.
    Matching is case-insensitive because the Azure APIs are inconsistent: the
    same resource group is reported as ``J-space`` by ``az group list`` and as
    ``J-SPACE`` by ``az vm list``, and salting one spelling but not the other
    would make the two snapshots look like drift when nothing had moved.

    Anything else becomes a salted SHA-256, so an unowned resource can still be
    compared across the two snapshots without its name entering the repository.
    """

    if value is None:
        return None
    canonical = _PUBLISHED_BY_CASEFOLD.get(value.casefold())
    if canonical is not None:
        return canonical
    return "salted:" + hashlib.sha256(f"{salt}|{value}".encode("utf-8")).hexdigest()


def _assert_read_only(args: list[str]) -> None:
    for allowed in READ_ONLY_COMMANDS:
        if tuple(args[: len(allowed)]) == allowed:
            return
    raise ReadOnlyViolation(
        "refusing to run a non-read-only Azure command: az "
        + " ".join(args)
        + " -- authority section 2 freezes every resource for this invocation"
    )


def _az_executable() -> str:
    """Resolve the Azure CLI entry point.

    On Windows the CLI is installed as ``az.CMD``, which bare ``"az"`` does not
    resolve under ``shell=False``. Resolving it explicitly keeps the subprocess
    call shell-free, so no argument is ever re-parsed by a command processor.
    """

    resolved = shutil.which("az")
    if not resolved:
        raise RuntimeError("the Azure CLI ('az') was not found on PATH")
    return resolved


def _az(args: list[str]) -> Any:
    _assert_read_only(args)
    completed = subprocess.run(
        [_az_executable(), *args, "-o", "json"],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"az {' '.join(args)} failed with {completed.returncode}: "
            f"{completed.stderr.strip()[:600]}"
        )
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def _management_endpoint() -> str:
    cloud = _az(["cloud", "show"])
    return str(cloud["endpoints"]["resourceManager"]).rstrip("/")


def collect(salt: str) -> dict[str, Any]:
    cloud = _az(["cloud", "show"])
    account = _az(["account", "show"])
    subscription_id = str(account["id"])

    groups = _az(["group", "list"])
    vms = _az(["vm", "list", "-d"])
    accounts = _az(["storage", "account", "list"])

    endpoint = _management_endpoint()

    storage: list[dict[str, Any]] = []
    for item in sorted(accounts, key=lambda a: str(a["name"])):
        url = (
            f"{endpoint}/subscriptions/{subscription_id}/resourceGroups/"
            f"{item['resourceGroup']}/providers/Microsoft.Storage/storageAccounts/"
            f"{item['name']}/blobServices/default/containers?api-version=2023-05-01"
        )
        listed = _az(["rest", "--method", "get", "--url", url])
        containers = [
            {
                "name": salted(str(c["name"]), salt),
                "public_access": (c.get("properties") or {}).get("publicAccess")
                or "None",
                "has_immutability_policy": bool(
                    (c.get("properties") or {}).get("hasImmutabilityPolicy")
                ),
                "has_legal_hold": bool(
                    (c.get("properties") or {}).get("hasLegalHold")
                ),
                "deleted": bool((c.get("properties") or {}).get("deleted")),
            }
            for c in sorted(listed.get("value", []), key=lambda c: str(c["name"]))
        ]
        storage.append(
            {
                "name": salted(str(item["name"]), salt),
                "resource_group": salted(str(item["resourceGroup"]), salt),
                "location": item.get("primaryLocation"),
                "kind": item.get("kind"),
                "sku": (item.get("sku") or {}).get("name"),
                "access_tier": item.get("accessTier"),
                "https_only": item.get("enableHttpsTrafficOnly"),
                "min_tls_version": item.get("minimumTlsVersion"),
                "allow_blob_public_access": item.get("allowBlobPublicAccess"),
                "status_of_primary": item.get("statusOfPrimary"),
                "container_count": len(containers),
                "containers": containers,
            }
        )

    machines = [
        {
            "name": salted(str(vm["name"]), salt),
            "resource_group": salted(str(vm["resourceGroup"]), salt),
            "size": (vm.get("hardwareProfile") or {}).get("vmSize"),
            "location": vm.get("location"),
            "power_state": vm.get("powerState"),
            "in_registered_scope": str(vm["name"]) in {"a100-vm", "cpuserver"},
        }
        for vm in sorted(vms, key=lambda v: str(v["name"]))
    ]

    # Network security groups are part of the snapshot because OA-001 authorised
    # a rule change. Recording them is what makes that change auditable instead
    # of invisible: a real configuration change that never appears in either
    # snapshot would be a hole in the paper record.
    nsgs_raw = _az(["network", "nsg", "list"])
    nsgs: list[dict[str, Any]] = []
    for item in sorted(nsgs_raw, key=lambda n: str(n["name"])):
        rules = []
        for rule in sorted(
            item.get("securityRules") or [], key=lambda r: int(r.get("priority") or 0)
        ):
            source = rule.get("sourceAddressPrefix") or rule.get(
                "sourceAddressPrefixes"
            )
            if isinstance(source, list):
                source_repr = [salted(str(s), salt) for s in sorted(source)]
            else:
                source_repr = salted(str(source), salt) if source else None
            ports = rule.get("destinationPortRange") or rule.get(
                "destinationPortRanges"
            )
            rules.append(
                {
                    "name": salted(str(rule["name"]), salt),
                    "priority": rule.get("priority"),
                    "direction": rule.get("direction"),
                    "access": rule.get("access"),
                    "protocol": rule.get("protocol"),
                    "source_prefix_salted": source_repr,
                    "destination_port": ports,
                }
            )
        nsgs.append(
            {
                "name": salted(str(item["name"]), salt),
                "location": item.get("location"),
                "rule_count": len(rules),
                "rules": rules,
            }
        )

    return {
        "schema_version": "study5-eq1-azure-inventory-v1",
        "captured_at_utc": utc_now(),
        "read_only": True,
        "control_plane_writes": 0,
        "data_plane_writes": 0,
        "sas_tokens_issued": 0,
        "storage_keys_read": False,
        "role_assignments_read_or_changed": 0,
        "cloud": cloud.get("name"),
        "subscription_last_four": subscription_id[-4:],
        "subscription_salted_sha256": salted(subscription_id, salt),
        "tenant_salted_sha256": salted(str(account.get("tenantId")), salt),
        "subscription_id_committed": False,
        "tenant_id_committed": False,
        "full_resource_ids_committed": False,
        "resource_groups": [
            {"name": salted(str(g["name"]), salt), "location": g.get("location")}
            for g in sorted(groups, key=lambda g: str(g["name"]))
        ],
        "resource_group_count": len(groups),
        "vm_count": len(machines),
        "vms": machines,
        "storage_account_count": len(storage),
        "storage_accounts": storage,
        "network_security_group_count": len(nsgs),
        "network_security_groups": nsgs,
    }


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            flat.update(_flatten(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            flat.update(_flatten(value, f"{prefix}[{index}]"))
    else:
        flat[prefix] = node
    return flat


def _nsg_rule_index(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index every NSG rule by (nsg name, rule name).

    Identity is the pair of names rather than the priority, so that a rule which
    is merely re-prioritised still reads as *modified* and not as one removal
    plus one unrelated addition.
    """

    index: dict[tuple[str, str], dict[str, Any]] = {}
    for nsg in snapshot.get("network_security_groups", []) or []:
        for rule in nsg.get("rules", []) or []:
            index[(str(nsg["name"]), str(rule["name"]))] = rule
    return index


def _nsg_deltas(
    opening: dict[str, Any], closing: dict[str, Any]
) -> list[dict[str, Any]]:
    before = _nsg_rule_index(opening)
    after = _nsg_rule_index(closing)
    deltas: list[dict[str, Any]] = []

    for key in sorted(set(before) | set(after)):
        nsg_name, rule_name = key
        if key not in before:
            kind = "nsg_rule_added"
        elif key not in after:
            kind = "nsg_rule_removed"
        elif before[key] != after[key]:
            kind = "nsg_rule_modified"
        else:
            continue
        deltas.append(
            {
                "kind": kind,
                "nsg": nsg_name,
                "rule": rule_name,
                "opening": before.get(key),
                "closing": after.get(key),
            }
        )
    return deltas


def _delta_identity(delta: dict[str, Any]) -> tuple[str, str, str]:
    return (str(delta["kind"]), str(delta["nsg"]), str(delta["rule"]))


def compare(
    opening: dict[str, Any],
    closing: dict[str, Any],
    expected_deltas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diff two snapshots under the authority section 2 tolerance rule.

    Section 2 permits only blob count and byte totals to differ. Where the
    operator has authorised a specific change, it is registered in an
    expected-deltas file bound to the amendment that authorised it, and the
    check becomes:

        closing == opening + exactly the registered deltas

    An observed delta that is not registered is drift. A registered delta that
    is not observed is *also* drift, because the register would then no longer
    describe the resources. One more or one fewer either way fails.
    """

    volatile = ARTIFACT_METADATA_KEYS

    # The NSG subtree is compared structurally below, so it is removed before
    # the generic flatten to keep one rule change from exploding into a dozen
    # unreadable key differences.
    left_tree = {k: v for k, v in opening.items() if k not in STRUCTURAL_SUBTREES}
    right_tree = {k: v for k, v in closing.items() if k not in STRUCTURAL_SUBTREES}
    left = _flatten(left_tree)
    right = _flatten(right_tree)

    differences = []
    for key in sorted(set(left) | set(right)):
        leaf = key.split(".")[-1].split("[")[0]
        if leaf in volatile:
            continue
        if left.get(key) != right.get(key):
            differences.append(
                {
                    "key": key,
                    "opening": left.get(key),
                    "closing": right.get(key),
                    "tolerated": leaf in TOLERATED_DRIFT_KEYS,
                }
            )

    blocking = [d for d in differences if not d["tolerated"]]

    registered = list((expected_deltas or {}).get("expected_deltas", []))
    registered_ids = {_delta_identity(d) for d in registered}
    observed = _nsg_deltas(opening, closing)
    observed_ids = {_delta_identity(d) for d in observed}

    unregistered = [d for d in observed if _delta_identity(d) not in registered_ids]
    missing = [d for d in registered if _delta_identity(d) not in observed_ids]

    hard_blocker = bool(blocking or unregistered or missing)
    return {
        "schema_version": "study5-eq1-azure-inventory-diff-v2",
        "compared_at_utc": utc_now(),
        "differences": differences,
        "tolerated_differences": len(differences) - len(blocking),
        "blocking_differences": len(blocking),
        "structural_deltas_observed": observed,
        "structural_deltas_registered": registered,
        "structural_deltas_unregistered": unregistered,
        "structural_deltas_registered_but_absent": missing,
        "expected_deltas_source": (expected_deltas or {}).get("artifact"),
        "authorizing_commits": sorted(
            {str(d.get("authorizing_commit")) for d in registered if d.get("authorizing_commit")}
        ),
        "closing_equals_opening_plus_registered_deltas": not hard_blocker,
        "hard_blocker": hard_blocker,
        "terminal_state_if_blocking": "STUDY5_EQ1_RESOURCE_INVENTORY_DRIFT_DETECTED",
    }


def _write(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write a snapshot to this path")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("OPENING", "CLOSING"),
        help="diff two snapshots under the section 2 tolerance rule",
    )
    parser.add_argument(
        "--expected-deltas",
        help="registered expected-delta file, bound to the amendment authorising it",
    )
    parser.add_argument("--diff-out", help="write the diff to this path")
    args = parser.parse_args(argv)

    if args.compare:
        opening = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        closing = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        expected = (
            json.loads(Path(args.expected_deltas).read_text(encoding="utf-8"))
            if args.expected_deltas
            else None
        )
        diff = compare(opening, closing, expected)
        if args.diff_out:
            digest = _write(Path(args.diff_out), diff)
            print(f"{args.diff_out}  sha256 {digest}")
        json.dump(diff, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return 1 if diff["hard_blocker"] else 0

    snapshot = collect(_salt())
    if args.out:
        digest = _write(Path(args.out), snapshot)
        print(f"{args.out}  sha256 {digest}")
    else:
        json.dump(snapshot, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
