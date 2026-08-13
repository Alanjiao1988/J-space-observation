#!/usr/bin/env python3
"""Fail-closed Azure read-only queries for the Study 3 P0-R1 generation-3 path.

This module exists because of a specific published defect. The generation-2
launcher evaluated its execution-history precondition as::

    EXISTING=$(az containerapp job execution list ... 2>/dev/null || echo "absent")

Under that expression an authentication failure, an expired token, a network
partition, a missing role assignment, a throttled control plane, malformed
output and a genuinely absent job all produce the identical string ``absent``.
The launcher could therefore create and start a one-shot GPU job on the
strength of a failure it never saw.

The rule this module enforces is that every query has exactly three outcomes:

``PROVED_ABSENT``
    the control plane answered successfully and the object is not there;
``PROVED_PRESENT``
    the control plane answered successfully and the object is there;
``ERROR``
    anything else at all.

Only ``PROVED_ABSENT`` may authorize a create or a start. ``ERROR`` is never
silently converted into either of the other two, and the complete command,
exit status, stdout and stderr are preserved so the operator sees exactly what
failed rather than a sanitized summary.

The module performs no write of any kind. It cannot create, start, update,
delete or scale anything: it builds read-only ``az`` argument vectors and
refuses to run a vector that is not on the read-only allowlist.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

SCHEMA_VERSION = "study3-p0-r1-azure-query-v3"

PROVED_ABSENT = "PROVED_ABSENT"
PROVED_PRESENT = "PROVED_PRESENT"
ERROR = "ERROR"

OUTCOMES = (PROVED_ABSENT, PROVED_PRESENT, ERROR)

# Only these leading verbs may ever be executed by this module. The tuple is
# checked against the exact head of the argument vector, so `job start`,
# `job create`, `job update` and `job delete` cannot be smuggled through a
# caller-supplied vector.
READ_ONLY_VERBS = (
    ("containerapp", "job", "list"),
    ("containerapp", "job", "show"),
    ("containerapp", "job", "execution", "list"),
    ("containerapp", "job", "execution", "show"),
    ("containerapp", "job", "logs", "show"),
    ("acr", "task", "list-runs"),
    ("acr", "task", "logs"),
    ("acr", "repository", "show"),
    ("acr", "manifest", "show-metadata"),
    ("storage", "blob", "list"),
    ("storage", "blob", "show"),
    ("account", "show"),
)

FORBIDDEN_VERBS = (
    "create", "start", "update", "delete", "restart", "stop", "set", "add",
    "remove", "upload", "purge", "untag", "import",
)


class AzureQueryError(Exception):
    """A query did not return a usable answer.

    Raising is the point. There is no ``.unwrap_or("absent")`` on this type.
    """

    def __init__(self, message, detail=None):
        super(AzureQueryError, self).__init__(message)
        self.detail = detail or {}


class WriteAttemptRefused(Exception):
    """A caller tried to route a mutating command through the read-only path."""


def _is_read_only(argv):
    """True only when argv starts with an allowlisted read-only verb."""
    for verb in READ_ONLY_VERBS:
        if tuple(argv[:len(verb)]) == verb:
            return True
    return False


def assert_read_only(argv):
    """Refuse any vector that is not an allowlisted read-only query.

    Checked before the subprocess is built, so a mutating command never
    reaches the Azure control plane through this module even by accident.
    """
    argv = list(argv)
    if not argv:
        raise WriteAttemptRefused("an empty Azure command is not a query")
    if not _is_read_only(argv):
        raise WriteAttemptRefused(
            "%r is not on the read-only allowlist; this module performs no "
            "control-plane or data-plane writes" % (" ".join(argv[:4]),))
    head = tuple(argv[:5])
    for token in head:
        if token in FORBIDDEN_VERBS:
            raise WriteAttemptRefused(
                "the verb %r mutates Azure state and is refused by the "
                "read-only query path" % (token,))
    return argv


def _default_runner(argv, timeout):
    completed = subprocess.run(  # noqa: S603 - fixed executable, allowlisted verb
        ["az"] + list(argv),
        capture_output=True, text=True, timeout=timeout)
    return completed.returncode, completed.stdout, completed.stderr


def query(argv, runner=None, timeout=300, expect_json=True):
    """Run one read-only query and return its complete, unsummarized result.

    Never returns a sentinel string. Raises :class:`AzureQueryError` carrying
    the exact exit code, stdout and stderr on any failure, timeout, or
    unparsable payload.
    """
    argv = assert_read_only(argv)
    runner = runner or _default_runner
    try:
        code, out, err = runner(argv, timeout)
    except Exception as exc:  # noqa: BLE001 - every failure mode is an error
        raise AzureQueryError(
            "the Azure query %r did not complete: %s" % (" ".join(argv), exc),
            {"argv": argv, "exception": repr(exc)})

    detail = {"argv": argv, "exit_code": code, "stdout": out, "stderr": err}
    if code != 0:
        raise AzureQueryError(
            "the Azure query %r exited %s; an error is not evidence of "
            "absence" % (" ".join(argv), code), detail)
    if not expect_json:
        return out, detail
    text = (out or "").strip()
    if text == "":
        raise AzureQueryError(
            "the Azure query %r returned an empty body where a JSON document "
            "was required; an empty answer is ambiguous, not absent"
            % (" ".join(argv),), detail)
    try:
        return json.loads(text), detail
    except ValueError as exc:
        raise AzureQueryError(
            "the Azure query %r returned output that is not JSON (%s); "
            "malformed output is an error, not an absence"
            % (" ".join(argv), exc), detail)


def job_presence(job_name, resource_group, subscription, runner=None,
                 timeout=300):
    """Prove a Container Apps job absent or present. Never guesses.

    ``az containerapp job show`` on a missing job exits non-zero, which is
    indistinguishable from an auth failure, so presence is decided from a
    successful *list* of the resource group instead.
    """
    names, detail = query(
        ["containerapp", "job", "list",
         "--resource-group", resource_group,
         "--subscription", subscription,
         "--query", "[].name", "-o", "json"],
        runner=runner, timeout=timeout)
    if not isinstance(names, list):
        raise AzureQueryError(
            "the job list did not return an array; refusing to interpret %r"
            % (type(names).__name__,), detail)
    outcome = PROVED_PRESENT if job_name in names else PROVED_ABSENT
    return {
        "schema_version": SCHEMA_VERSION,
        "check": "container_apps_job_presence",
        "job": job_name,
        "outcome": outcome,
        "jobs_returned": len(names),
        "resource_group": resource_group,
        "exit_code": detail["exit_code"],
    }


def job_executions(job_name, resource_group, subscription, runner=None,
                   timeout=300):
    """Return the complete execution history of a job, or raise.

    An empty history is only returned when the query itself succeeded.
    """
    executions, detail = query(
        ["containerapp", "job", "execution", "list",
         "--name", job_name,
         "--resource-group", resource_group,
         "--subscription", subscription,
         "--query", "[].{name:name,status:properties.status}", "-o", "json"],
        runner=runner, timeout=timeout)
    if not isinstance(executions, list):
        raise AzureQueryError(
            "the execution list did not return an array", detail)
    return {
        "schema_version": SCHEMA_VERSION,
        "check": "container_apps_job_executions",
        "job": job_name,
        "outcome": PROVED_ABSENT if not executions else PROVED_PRESENT,
        "executions": executions,
        "count": len(executions),
        "exit_code": detail["exit_code"],
    }


def require_absent(report):
    """Continue only on a proved absence.

    ``PROVED_PRESENT`` and ``ERROR`` both stop. This is the only function a
    caller should use immediately before a create or a start.
    """
    outcome = report.get("outcome")
    if outcome == PROVED_ABSENT:
        return report
    if outcome == PROVED_PRESENT:
        raise AzureQueryError(
            "%s is proved present; a one-shot attempt refuses to reuse or "
            "overwrite an existing object" % (report.get("check"),), report)
    raise AzureQueryError(
        "%s did not reach a proved outcome; no create or start is authorized"
        % (report.get("check"),), report)


def implementation_identity(root=None):
    """Identity block for the lock and the image manifest."""
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_azure_query_v3.py",
        "outcomes": list(OUTCOMES),
        "read_only_verbs": [" ".join(v) for v in READ_ONLY_VERBS],
        "forbidden_verbs": list(FORBIDDEN_VERBS),
        "collapses_errors_into_absence": False,
        "closes": "G2-05",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--job-presence")
    parser.add_argument("--job-executions")
    parser.add_argument("--resource-group", default="rg-jspace-observation-sea")
    parser.add_argument("--subscription")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.job_presence or args.job_executions:
        if not args.subscription:
            print("FAIL: --subscription is required", file=sys.stderr)
            return 2
        try:
            if args.job_presence:
                report = job_presence(
                    args.job_presence, args.resource_group, args.subscription)
            else:
                report = job_executions(
                    args.job_executions, args.resource_group,
                    args.subscription)
        except AzureQueryError as exc:
            print("P0_R1_AZURE_QUERY_ERROR=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            print(json.dumps(exc.detail, indent=2, sort_keys=True)[:4000],
                  file=sys.stderr)
            return 3
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
