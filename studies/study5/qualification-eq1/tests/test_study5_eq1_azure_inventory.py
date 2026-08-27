"""Tests for the Study 5-EQ1 read-only Azure inventory tool.

Two properties are load-bearing and are therefore tested rather than assumed:

* the tool **cannot** issue an Azure write, because authority section 2 freezes
  every resource for this invocation;
* the tool **cannot** commit a raw identity, because section 2.8 permits only
  salted hashes and the already-published safe names.

The third group covers the section 2 drift rule, which decides between carrying
on and stopping at ``STUDY5_EQ1_RESOURCE_INVENTORY_DRIFT_DETECTED``.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_azure_inventory", _TOOLS / "azure_inventory.py"
)
assert _SPEC is not None and _SPEC.loader is not None
inventory = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_azure_inventory"] = inventory
_SPEC.loader.exec_module(inventory)

SALT = "test-salt"

MUTATING_COMMANDS = [
    ["vm", "start"],
    ["vm", "stop"],
    ["vm", "deallocate"],
    ["vm", "restart"],
    ["vm", "delete"],
    ["vm", "resize"],
    ["vm", "update"],
    ["vm", "redeploy"],
    ["group", "delete"],
    ["group", "create"],
    ["storage", "account", "create"],
    ["storage", "account", "delete"],
    ["storage", "container", "create"],
    ["storage", "container", "delete"],
    ["storage", "blob", "upload"],
    ["storage", "blob", "delete"],
    ["storage", "account", "keys", "list"],
    ["storage", "container", "generate-sas"],
    ["role", "assignment", "create"],
    ["role", "assignment", "delete"],
    ["rest", "--method", "put"],
    ["rest", "--method", "post"],
    ["rest", "--method", "patch"],
    ["rest", "--method", "delete"],
]


@pytest.mark.parametrize("args", MUTATING_COMMANDS, ids=lambda a: " ".join(a))
def test_every_mutating_command_is_refused(args: list[str]) -> None:
    with pytest.raises(inventory.ReadOnlyViolation):
        inventory._assert_read_only(args)


@pytest.mark.parametrize(
    "args",
    [
        ["cloud", "show"],
        ["account", "show"],
        ["group", "list"],
        ["vm", "list", "-d"],
        ["storage", "account", "list"],
        ["rest", "--method", "get", "--url", "https://example.invalid"],
    ],
    ids=lambda a: " ".join(a),
)
def test_the_registered_reads_are_allowed(args: list[str]) -> None:
    inventory._assert_read_only(args)


def test_a_read_verb_cannot_smuggle_a_write_after_it() -> None:
    with pytest.raises(inventory.ReadOnlyViolation):
        inventory._assert_read_only(["vm", "list-skus", "delete"])


def test_published_safe_names_pass_through_in_the_clear() -> None:
    for name in ("a100-vm", "cpuserver", "s4fm11ca457e105b29b7", "models"):
        assert inventory.salted(name, SALT) == name


def test_published_names_are_matched_case_insensitively() -> None:
    """`az group list` says `J-space`; `az vm list` says `J-SPACE`."""

    assert inventory.salted("J-SPACE", SALT) == "J-space"
    assert inventory.salted("J-space", SALT) == "J-space"


def test_an_unpublished_name_never_appears_in_the_output() -> None:
    hashed = inventory.salted("t123_1fa1eb74", SALT)
    assert hashed is not None
    assert hashed.startswith("salted:")
    assert "t123" not in hashed


def test_a_subscription_id_never_appears_in_the_output() -> None:
    """A synthetic id is used deliberately.

    Authority §2.8 forbids committing a subscription id, and a test fixture is
    a committed artifact like any other. The shape is what matters here, not
    the value.
    """

    subscription = "00000000-1111-2222-3333-444444444444"
    hashed = inventory.salted(subscription, SALT)
    assert hashed is not None
    assert subscription not in hashed
    assert "00000000" not in hashed


def test_a_different_salt_gives_a_different_hash() -> None:
    assert inventory.salted("x", "salt-a") != inventory.salted("x", "salt-b")


def test_the_same_salt_is_stable_so_snapshots_are_comparable() -> None:
    assert inventory.salted("x", SALT) == inventory.salted("x", SALT)


def test_a_missing_salt_is_refused_rather_than_defaulted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(inventory.SALT_ENV, raising=False)
    with pytest.raises(SystemExit):
        inventory._salt()


def _snapshot() -> dict:
    return json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "inventory"
            / "opening_snapshot.json"
        ).read_text(encoding="utf-8")
    )


def test_an_identical_snapshot_is_not_drift() -> None:
    snap = _snapshot()
    result = inventory.compare(snap, copy.deepcopy(snap))
    assert result["hard_blocker"] is False
    assert result["blocking_differences"] == 0


def test_a_changed_power_state_is_a_hard_blocker() -> None:
    opening = _snapshot()
    closing = copy.deepcopy(opening)
    closing["vms"][0]["power_state"] = "VM deallocated"
    result = inventory.compare(opening, closing)
    assert result["hard_blocker"] is True
    assert (
        result["terminal_state_if_blocking"]
        == "STUDY5_EQ1_RESOURCE_INVENTORY_DRIFT_DETECTED"
    )


def test_a_changed_vm_size_is_a_hard_blocker() -> None:
    opening = _snapshot()
    closing = copy.deepcopy(opening)
    closing["vms"][0]["size"] = "Standard_NC24ads_A100_v4"
    assert inventory.compare(opening, closing)["hard_blocker"] is True


def test_a_new_container_is_a_hard_blocker() -> None:
    opening = _snapshot()
    closing = copy.deepcopy(opening)
    account = closing["storage_accounts"][0]
    account["containers"].append(
        {
            "name": "sneaky",
            "public_access": "None",
            "has_immutability_policy": False,
            "has_legal_hold": False,
            "deleted": False,
        }
    )
    account["container_count"] += 1
    assert inventory.compare(opening, closing)["hard_blocker"] is True


def test_a_disappeared_vm_is_a_hard_blocker() -> None:
    opening = _snapshot()
    closing = copy.deepcopy(opening)
    closing["vms"].pop()
    closing["vm_count"] -= 1
    assert inventory.compare(opening, closing)["hard_blocker"] is True


def test_blob_count_and_byte_totals_are_the_only_tolerated_drift() -> None:
    opening = _snapshot()
    opening["storage_accounts"][0]["blob_count"] = 47
    opening["storage_accounts"][0]["blob_bytes"] = 117045201262
    closing = copy.deepcopy(opening)
    closing["storage_accounts"][0]["blob_count"] = 61
    closing["storage_accounts"][0]["blob_bytes"] = 130000000000
    result = inventory.compare(opening, closing)
    assert result["hard_blocker"] is False
    assert result["tolerated_differences"] == 2


def test_the_capture_timestamp_alone_is_not_drift() -> None:
    opening = _snapshot()
    closing = copy.deepcopy(opening)
    closing["captured_at_utc"] = "2027-01-01T00:00:00Z"
    assert inventory.compare(opening, closing)["differences"] == []


def test_the_committed_opening_snapshot_matches_the_registered_identities() -> None:
    """Authority section 14 and hard blocker 1: the roles resolve uniquely."""

    snap = _snapshot()
    assert snap["cloud"] == "AzureChinaCloud"
    assert snap["subscription_last_four"] == "8845"
    assert snap["subscription_id_committed"] is False
    assert snap["tenant_id_committed"] is False

    in_scope = {vm["name"]: vm for vm in snap["vms"] if vm["in_registered_scope"]}
    assert set(in_scope) == {"a100-vm", "cpuserver"}
    assert in_scope["a100-vm"]["size"] == "Standard_NC96ads_A100_v4"
    assert in_scope["a100-vm"]["location"] == "chinaeast3"
    assert in_scope["cpuserver"]["size"] == "Standard_D16ds_v5"
    assert in_scope["cpuserver"]["location"] == "chinanorth3"
    for vm in in_scope.values():
        assert vm["power_state"] == "VM running", "section 2.2: both stay running"

    assert snap["storage_account_count"] == 1
    account = snap["storage_accounts"][0]
    assert account["name"] == "s4fm11ca457e105b29b7"
    assert {c["name"] for c in account["containers"]} == {
        "models",
        "oci",
        "runs",
        "logs",
        "seals",
        "handoff",
    }
    assert all(c["public_access"] == "None" for c in account["containers"])


def test_no_raw_identity_leaked_into_the_committed_snapshot() -> None:
    """A structural check, so the test needs no secret of its own.

    Asserting "the real subscription id is absent" would require committing the
    real subscription id, which §2.8 forbids. Instead this asserts that the
    snapshot contains no bare GUID at all, which is the shape every Azure
    subscription id, tenant id and resource GUID takes, plus the obvious
    credential markers.
    """

    text = (
        Path(__file__).resolve().parent.parent / "inventory" / "opening_snapshot.json"
    ).read_text(encoding="utf-8")

    guid = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    assert guid.search(text) is None, "a GUID-shaped identity reached the snapshot"

    for forbidden in (
        "SharedAccessSignature",
        "AccountKey=",
        "sig=",
        "/subscriptions/",
        "BEGIN PRIVATE KEY",
    ):
        assert forbidden not in text
