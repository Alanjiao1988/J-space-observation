#!/usr/bin/env python3
"""Read-only, fail-closed Azure control-plane queries for P0-R2.

The single rule this module exists to enforce: **a query error is never an
absence**. A `ResourceNotFound` answer from a call that actually reached Azure
and was understood is a proof of absence. Anything else -- a network failure, a
throttle, an expired credential, a malformed answer, an unparsable payload --
is an ambiguity, and an ambiguity stops.

Every outcome is one of:

``PROVED_ABSENT``   Azure answered, and the answer means the object is not there.
``PROVED_PRESENT``  Azure answered, and the object exists.
``AMBIGUOUS``       Anything else. Exit code is non-zero; nothing may proceed.

No mode of this module creates, updates, starts, or deletes anything, and none
performs a tokenizer, checkpoint, model, GPU, scoring, or evidence operation.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys


SCHEMA_VERSION = "study3-p0-r2-azure-query-v1"
STAGE = "STUDY3-P0-R2"

GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g1"
BLOB_PREFIX_ROOT = "study3/p0_r2/g1/"

#: Roles that actually permit a blob write. Ownership of the account (a control
#: plane role such as Owner or Contributor) does not grant data plane access, so
#: it must not be accepted here.
BLOB_DATA_ROLES = (
    "Storage Blob Data Contributor",
    "Storage Blob Data Owner",
)

#: Substrings that prove Azure understood the request and reported absence.
_ABSENCE_MARKERS = (
    "ResourceNotFound",
    "was not found",
    "could not be found",
    "NotFound",
)

#: Emitted by the runner when the Azure CLI could not be started at all. A host
#: that cannot launch the CLI has learned nothing about Azure, so this must be
#: read as an ambiguity and never as an absence.
LAUNCH_FAILURE_MARKER = "P0_R2_AZURE_CLI_LAUNCH_FAILED"

#: Substrings that prove the answer is an authorization or transport problem
#: rather than an absence. These must never be read as "not there".
_AMBIGUITY_MARKERS = (
    "AuthorizationFailed",
    "ExpiredAuthenticationToken",
    "InvalidAuthenticationToken",
    "SubscriptionNotFound",
    "ResourceGroupNotFound",
    "Please run 'az login'",
    "TooManyRequests",
    "ServiceUnavailable",
    "GatewayTimeout",
    "Forbidden",
    LAUNCH_FAILURE_MARKER,
)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class AzureQueryDefect(Exception):
    """The control plane did not return a proved, unambiguous answer."""


def _require_name(value, label):
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise AzureQueryDefect("%s %r is not a safe Azure name" % (label, value))
    return value


def _default_runner(command):
    # subprocess does not apply PATHEXT, so a bare "az" cannot be launched on
    # Windows, where the Azure CLI ships as az.cmd. Resolve the program the way
    # a shell would, and keep the original name as the fallback so an absolute
    # path or a POSIX host behaves exactly as before.
    program = shutil.which(command[0]) or command[0]
    try:
        return subprocess.run(  # noqa: S603 - fixed executable
            [program] + list(command[1:]), capture_output=True, text=True,
            check=False)
    except OSError as exc:
        # A host that could not start the CLI has not observed Azure at all.
        # Returning a synthetic ambiguous answer keeps the single rule of this
        # module intact -- a query error is never an absence -- where raising
        # would abandon the receipt and report nothing at all.
        return subprocess.CompletedProcess(
            command, 127, "",
            "%s: %s" % (LAUNCH_FAILURE_MARKER, exc))


def classify(returncode: int, stdout: str, stderr: str) -> str:
    """Map one CLI answer onto a proved outcome or an explicit ambiguity."""
    combined = "%s\n%s" % (stdout or "", stderr or "")
    for marker in _AMBIGUITY_MARKERS:
        if marker in combined:
            return "AMBIGUOUS"
    if returncode == 0:
        body = (stdout or "").strip()
        if not body:
            # A success with no payload is not a proof of anything.
            return "AMBIGUOUS"
        try:
            document = json.loads(body)
        except ValueError:
            return "AMBIGUOUS"
        if document in (None, [], {}):
            return "PROVED_ABSENT"
        return "PROVED_PRESENT"
    if any(marker in combined for marker in _ABSENCE_MARKERS):
        return "PROVED_ABSENT"
    return "AMBIGUOUS"


def job_presence(name: str, *, resource_group: str, subscription: str,
                 runner=None) -> dict:
    """Prove whether one Container Apps job exists. Never mutates anything."""
    name = _require_name(name, "job name")
    resource_group = _require_name(resource_group, "resource group")
    subscription = _require_name(subscription, "subscription")
    command = [
        "az", "containerapp", "job", "show",
        "--name", name,
        "--resource-group", resource_group,
        "--subscription", subscription,
        "--output", "json",
    ]
    completed = (runner or _default_runner)(command)
    stdout = getattr(completed, "stdout", "") or ""
    stderr = getattr(completed, "stderr", "") or ""
    returncode = int(getattr(completed, "returncode", 1))
    outcome = classify(returncode, stdout, stderr)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "query": "job-presence",
        "name": name,
        "resource_group": resource_group,
        "subscription": subscription,
        "outcome": outcome,
        "exit_code": returncode,
        "read_only": True,
        "created_updated_or_started": False,
        "stderr_excerpt": stderr.strip()[:512],
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }
    if outcome == "PROVED_PRESENT":
        try:
            document = json.loads(stdout)
            receipt["observed_name"] = (document or {}).get("name")
        except ValueError:
            receipt["outcome"] = "AMBIGUOUS"
    return receipt


def repository_tag_absence(*, registry: str, repository: str, tag: str,
                           subscription: str, runner=None) -> dict:
    """Prove whether one exact image tag exists. Read-only."""
    command = [
        "az", "acr", "repository", "show",
        "--name", _require_name(registry, "registry"),
        "--image", "%s:%s" % (repository, tag),
        "--subscription", _require_name(subscription, "subscription"),
        "--output", "json",
    ]
    completed = (runner or _default_runner)(command)
    stdout = getattr(completed, "stdout", "") or ""
    stderr = getattr(completed, "stderr", "") or ""
    returncode = int(getattr(completed, "returncode", 1))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "query": "repository-tag",
        "registry": registry,
        "repository": repository,
        "tag": tag,
        "outcome": classify(returncode, stdout, stderr),
        "exit_code": returncode,
        "read_only": True,
        "stderr_excerpt": stderr.strip()[:512],
        "model_operations_performed": 0,
    }


def _json_answer(command, label, runner):
    """Run one read-only query and return its parsed payload or an ambiguity."""
    completed = (runner or _default_runner)(command)
    stdout = getattr(completed, "stdout", "") or ""
    stderr = getattr(completed, "stderr", "") or ""
    returncode = int(getattr(completed, "returncode", 1))
    outcome = classify(returncode, stdout, stderr)
    if outcome != "PROVED_PRESENT":
        return None, outcome, stderr, returncode
    try:
        return json.loads(stdout), outcome, stderr, returncode
    except ValueError:
        return None, "AMBIGUOUS", stderr, returncode


def _scope_covers(scope: str, resource_id: str) -> bool:
    """True when an assignment scope contains the storage account."""
    scope = (scope or "").rstrip("/").lower()
    resource_id = (resource_id or "").rstrip("/").lower()
    if not scope or not resource_id:
        return False
    return resource_id == scope or resource_id.startswith(scope + "/")


def blob_data_access(*, account: str, identity_name: str, resource_group: str,
                     subscription: str, roles=BLOB_DATA_ROLES,
                     runner=None) -> dict:
    """Prove the registered identity may write blobs to the account the
    transport actually uses.

    The transport decides the account; a job specification only repeats it. If
    the identity holds no blob data role at a scope covering that account, the
    first result write fails -- and that write happens after the one-shot replay
    envelope has been consumed, so it cannot be retried. This query is the only
    place that failure can be found while it is still cheap.
    """
    account = _require_name(account, "storage account")
    identity_name = _require_name(identity_name, "identity name")
    resource_group = _require_name(resource_group, "resource group")
    subscription = _require_name(subscription, "subscription")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "query": "blob-data-access",
        "account": account,
        "identity_name": identity_name,
        "resource_group": resource_group,
        "subscription": subscription,
        "accepted_roles": list(roles),
        "read_only": True,
        "created_updated_or_started": False,
        "model_operations_performed": 0,
    }

    identity, outcome, stderr, code = _json_answer(
        ["az", "identity", "show", "--name", identity_name,
         "--resource-group", resource_group, "--subscription", subscription,
         "--output", "json"], "identity", runner)
    if outcome != "PROVED_PRESENT":
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "stderr_excerpt": stderr.strip()[:512],
                        "step": "identity"})
        return receipt
    principal = (identity or {}).get("principalId")
    receipt["principal_id"] = principal
    if not principal:
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "step": "identity", "stderr_excerpt": ""})
        return receipt

    storage, outcome, stderr, code = _json_answer(
        ["az", "storage", "account", "show", "--name", account,
         "--subscription", subscription, "--output", "json"], "storage", runner)
    if outcome != "PROVED_PRESENT":
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "stderr_excerpt": stderr.strip()[:512],
                        "step": "storage-account"})
        return receipt
    account_id = (storage or {}).get("id")
    receipt["account_id"] = account_id
    if not account_id:
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "step": "storage-account", "stderr_excerpt": ""})
        return receipt

    assignments, outcome, stderr, code = _json_answer(
        ["az", "role", "assignment", "list", "--assignee", principal, "--all",
         "--subscription", subscription, "--output", "json"], "roles", runner)
    if outcome == "PROVED_ABSENT":
        # An empty list is a real answer: the identity holds no role at all.
        assignments = []
    elif outcome != "PROVED_PRESENT":
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "stderr_excerpt": stderr.strip()[:512],
                        "step": "role-assignments"})
        return receipt
    if not isinstance(assignments, list):
        receipt.update({"outcome": "AMBIGUOUS", "exit_code": code,
                        "step": "role-assignments", "stderr_excerpt": ""})
        return receipt

    granting = [
        {"role": item.get("roleDefinitionName"), "scope": item.get("scope")}
        for item in assignments
        if item.get("roleDefinitionName") in roles
        and _scope_covers(item.get("scope"), account_id)
    ]
    receipt["granting_assignments"] = granting
    receipt["exit_code"] = code
    receipt["stderr_excerpt"] = stderr.strip()[:512]
    receipt["outcome"] = "PROVED_PRESENT" if granting else "PROVED_ABSENT"
    return receipt


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_azure_query_v1.py",
        "stage": STAGE,
        "outcomes": ["PROVED_ABSENT", "PROVED_PRESENT", "AMBIGUOUS"],
        "query_error_is_absence": False,
        "read_only": True,
        "gpu_job": GPU_JOB,
        "recovery_job": RECOVERY_JOB,
        "blob_prefix_root": BLOB_PREFIX_ROOT,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--job-presence")
    mode.add_argument("--repository-tag")
    mode.add_argument("--blob-data-access", action="store_true")
    parser.add_argument("--resource-group")
    parser.add_argument("--subscription")
    parser.add_argument("--registry")
    parser.add_argument("--repository")
    parser.add_argument("--account")
    parser.add_argument("--identity-name")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.job_presence:
            receipt = job_presence(
                args.job_presence, resource_group=args.resource_group,
                subscription=args.subscription)
        elif args.blob_data_access:
            receipt = blob_data_access(
                account=args.account, identity_name=args.identity_name,
                resource_group=args.resource_group,
                subscription=args.subscription)
        else:
            receipt = repository_tag_absence(
                registry=args.registry, repository=args.repository,
                tag=args.repository_tag, subscription=args.subscription)
    except AzureQueryDefect as exc:
        print("P0_R2_AZURE_QUERY_REFUSED=1 %s" % exc, file=sys.stderr)
        return 2

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["outcome"] == "AMBIGUOUS":
        print("P0_R2_AZURE_QUERY_AMBIGUOUS=1 an error is never an absence",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
