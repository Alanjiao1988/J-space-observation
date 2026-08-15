#!/usr/bin/env python3
"""The guarded host wrapper for the one-shot P0-R2 live replay submission.

The envelope is consumed the moment the authorized Azure CLI live submission is
invoked -- even if the invocation fails before an ACR run id comes back. Every
check this wrapper makes therefore has to happen *before* that call, and the
call has to happen exactly once.

The wrapper refuses unless, in one transaction immediately before invoking:

* a published Phase-B admission document says ``phase_b_authorized`` is true and
  lists no failed condition;
* the v2 host preflight proves, from this checkout, every fact it is required to
  prove;
* ``HEAD`` equals ``origin/main`` and equals the exact admitted head and tree;
* the worktree is clean;
* the two-file ``acrctx`` has just been rebuilt from committed Git objects and
  contains exactly ``task.yaml`` and ``context_manifest.json``;
* the context embeds the exact active authority, lock and admission bytes;
* the image reference carries ``@sha256:<active digest>``;
* the measured native path maximum is within budget;
* no canonical replay artifact and no prior submission receipt exists.

``P0_R2_LIVE_REPLAY_AUTHORIZED`` is never exported into the wrapper's own
environment. It is passed to exactly one child invocation and to nothing else,
so it cannot leak into a later command in the same shell.

After the single invocation this wrapper never retries, never regenerates,
never substitutes another attempt and never repairs the gate in place. A missing
or duplicated ACR run id is a terminal stop, not a retry condition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent.parent
VALIDATION_DIR = Path(__file__).resolve().parent
for candidate in (P0_R2_DIR, VALIDATION_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import p0_r2_acr_submission as SUBMISSION  # noqa: E402
import p0_r2_closure_binding_v2 as CB2  # noqa: E402
import p0_r2_host_preflight_v2 as HOST  # noqa: E402
import p0_r2_submission_context as CONTEXT  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-guarded-host-submission-v2"
STAGE = "STUDY3-P0-R2"
AUTHORIZED_ENV = "P0_R2_LIVE_REPLAY_AUTHORIZED"


class SubmissionRefused(Exception):
    """The one-shot envelope may not be opened."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root, *args):
    done = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False)
    if done.returncode:
        raise SubmissionRefused("git %s failed: %s"
                                % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip()


def guard(root, *, lock_path, admission_path, preflight_report_path,
          context_dir, expect_head, expect_tree, image, digest) -> dict:
    """Every refusal that must precede the irreversible call."""
    root = Path(root).resolve()
    checks = []

    def require(name, ok, detail):
        checks.append({"check": name, "outcome": "PROVED" if ok else "REFUSED",
                       "detail": detail})
        if not ok:
            raise SubmissionRefused("%s: %s" % (name, json.dumps(detail)[:400]))

    if os.environ.get(AUTHORIZED_ENV):
        require("live_replay_authorization_is_not_set_globally", False,
                {"variable": AUTHORIZED_ENV,
                 "reason": "the guarded wrapper sets it for one child "
                           "invocation only; finding it already set in the "
                           "ambient environment means something else could "
                           "spend the envelope"})

    admission = json.loads(Path(admission_path).read_bytes().decode("utf-8"))
    require("phase_b_admission_authorizes_segment_b",
            admission.get("phase_b_authorized") is True
            and not admission.get("failed_conditions"),
            {"authorized": admission.get("phase_b_authorized"),
             "failed": admission.get("failed_conditions")})

    report = json.loads(
        Path(preflight_report_path).read_bytes().decode("utf-8"))
    require("host_preflight_proved",
            report.get("outcome") == "HOST_PREFLIGHT_PROVED",
            {"outcome": report.get("outcome"),
             "refusals": report.get("refusals")})

    head = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    published = _git(root, "rev-parse", "origin/main")
    require("head_equals_origin_main_and_the_admitted_head",
            head == published == expect_head and tree == expect_tree,
            {"head": head, "tree": tree, "origin_main": published,
             "expected_head": expect_head, "expected_tree": expect_tree})

    status = _git(root, "status", "--porcelain")
    require("worktree_clean", not status.strip(),
            {"dirty": status.splitlines()[:16]})

    context_dir = Path(context_dir).resolve()
    entries = sorted(path.name for path in context_dir.iterdir())
    require("context_is_exactly_the_two_registered_files",
            entries == ["context_manifest.json", "task.yaml"],
            {"entries": entries})

    manifest = json.loads(
        (context_dir / "context_manifest.json").read_bytes().decode("utf-8"))
    embedded = {entry["label"]: entry
                for entry in (manifest.get("embedded_governance_objects") or [])}
    lock_raw = Path(lock_path).read_bytes()
    require("context_embeds_the_exact_active_lock_bytes",
            "execution_lock" in embedded
            and embedded["execution_lock"]["sha256"] == _sha256(lock_raw)
            and embedded["execution_lock"]["bytes"] == len(lock_raw),
            {"embedded": {key: {"bytes": value["bytes"],
                                "sha256": value["sha256"]}
                          for key, value in embedded.items()},
             "lock": {"bytes": len(lock_raw), "sha256": _sha256(lock_raw)}})
    for label, path in (("corrective_authority", None),
                        ("phase_b_admission", admission_path)):
        if label == "corrective_authority":
            ok = label in embedded
            detail = {"present": ok}
        else:
            raw = Path(path).read_bytes()
            ok = (label in embedded
                  and embedded[label]["sha256"] == _sha256(raw))
            detail = {"present": label in embedded,
                      "sha256": _sha256(raw)}
        require("context_embeds_the_exact_%s_bytes" % label, ok, detail)

    require("image_is_pinned_by_the_active_digest",
            isinstance(image, str) and image.endswith("@" + digest),
            {"image": image, "digest": digest})

    longest = max(len(str(path)) for path in
                  [context_dir, *context_dir.rglob("*")])
    require("native_path_maximum_within_budget",
            longest <= HOST.MAX_NATIVE_PATH_CHARS,
            {"maximum": longest, "limit": HOST.MAX_NATIVE_PATH_CHARS})

    return {"checks": checks, "admission": admission, "preflight": report,
            "head": head, "tree": tree}


def submit_once(root, *, lock_path, admission_path, preflight_report_path,
                context_dir, context_admission, work_dir, registry,
                subscription, image, digest, ready_anchor, attempt,
                packing_canary_receipt, executable_commit, executable_tree,
                azure_cli_version, expect_head, expect_tree,
                governance_proof=None) -> dict:
    """Guard, then invoke the live submission exactly once."""
    guarded = guard(root, lock_path=lock_path, admission_path=admission_path,
                    preflight_report_path=preflight_report_path,
                    context_dir=context_dir, expect_head=expect_head,
                    expect_tree=expect_tree, image=image, digest=digest)

    if governance_proof is not None:
        document = json.loads(
            Path(governance_proof).read_bytes().decode("utf-8"))
        CB2.validate_proof(document, image_executable=executable_commit,
                           ready_anchor=ready_anchor,
                           governance_commit=expect_head,
                           task_blob=None, digest=digest)

    # The envelope is spent from here. Nothing below may be retried.
    child_env = dict(os.environ)
    child_env[AUTHORIZED_ENV] = "1"
    previous = os.environ.pop(AUTHORIZED_ENV, None)

    def runner(command, context):
        return subprocess.run(  # noqa: S603 - fixed executable
            command, cwd=str(context), capture_output=True, check=False,
            env=child_env)

    try:
        receipt = SUBMISSION.submit(
            root=root, source_commit=expect_head,
            task_path=(json.loads(Path(lock_path).read_bytes().decode("utf-8"))
                       .get("transport") or {}).get("task_path"),
            context_dir=context_dir, context_admission=context_admission,
            work_dir=work_dir, registry=registry, subscription=subscription,
            image=image, digest=digest, ready_anchor=ready_anchor, mode="live",
            attempt=attempt, packing_canary_receipt=packing_canary_receipt,
            executable_commit=executable_commit,
            executable_tree=executable_tree,
            azure_cli_version=azure_cli_version, runner=runner)
    finally:
        if previous is not None:
            os.environ[AUTHORIZED_ENV] = previous
        os.environ.pop(AUTHORIZED_ENV, None)

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "LIVE_SUBMISSION_INVOKED_ONCE",
        "guard": guarded["checks"],
        "invocations": 1,
        "envelope_consumed": True,
        "submission_receipt": receipt,
        "authorization_env_set_globally": False,
        "rerunnable": False,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_host_submission_v2.py",
        "stage": STAGE,
        "authorization_env": AUTHORIZED_ENV,
        "sets_authorization_env_globally": False,
        "invocations_permitted": 1,
        "retries_permitted": 0,
        "consumed_on_invocation_even_without_a_run_id": True,
        "repairs_the_gate_in_place": False,
        "substitutes_another_attempt": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--guard-only", action="store_true")
    mode.add_argument("--submit-once", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--lock-file")
    parser.add_argument("--admission")
    parser.add_argument("--preflight-report")
    parser.add_argument("--context-dir")
    parser.add_argument("--context-admission")
    parser.add_argument("--work-dir")
    parser.add_argument("--registry")
    parser.add_argument("--subscription")
    parser.add_argument("--image")
    parser.add_argument("--digest")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--attempt")
    parser.add_argument("--packing-canary-receipt")
    parser.add_argument("--executable-commit")
    parser.add_argument("--executable-tree")
    parser.add_argument("--governance-proof")
    parser.add_argument("--azure-cli-version")
    parser.add_argument("--expect-head")
    parser.add_argument("--expect-tree")
    parser.add_argument("--out")
    parser.add_argument("--i-am-sure", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.guard_only:
            document = {"schema_version": SCHEMA_VERSION, "mode": "guard-only",
                        "envelope_consumed": False,
                        **guard(args.root, lock_path=args.lock_file,
                                admission_path=args.admission,
                                preflight_report_path=args.preflight_report,
                                context_dir=args.context_dir,
                                expect_head=args.expect_head,
                                expect_tree=args.expect_tree,
                                image=args.image, digest=args.digest)}
            document.pop("admission", None)
            document.pop("preflight", None)
        else:
            if not args.i_am_sure:
                print("P0_R2_HOST_SUBMISSION_REFUSED=1 --i-am-sure is required "
                      "to spend the one-shot envelope", file=sys.stderr)
                return 2
            document = submit_once(
                args.root, lock_path=args.lock_file,
                admission_path=args.admission,
                preflight_report_path=args.preflight_report,
                context_dir=args.context_dir,
                context_admission=args.context_admission,
                work_dir=args.work_dir, registry=args.registry,
                subscription=args.subscription, image=args.image,
                digest=args.digest, ready_anchor=args.ready_anchor,
                attempt=args.attempt,
                packing_canary_receipt=args.packing_canary_receipt,
                executable_commit=args.executable_commit,
                executable_tree=args.executable_tree,
                azure_cli_version=args.azure_cli_version,
                expect_head=args.expect_head, expect_tree=args.expect_tree,
                governance_proof=args.governance_proof)
    except (SubmissionRefused, SUBMISSION.SubmissionDefect,
            CB2.ClosureBindingDefect, CONTEXT.ContextDefect, OSError,
            ValueError) as exc:
        print("P0_R2_HOST_SUBMISSION_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    print(payload, end="")
    if args.guard_only:
        print("P0_R2_HOST_SUBMISSION_GUARD_PROVED=1")
    else:
        print("P0_R2_LIVE_SUBMISSION_INVOCATIONS=1")
        print("P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
