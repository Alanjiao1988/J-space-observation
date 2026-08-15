#!/usr/bin/env python3
"""Render the exact P0-R2 job specifications. Never talk to Azure.

This module only produces YAML/JSON documents. It cannot create, update or
start anything, which is why it is safe to exercise fully in a preparation
session: rendering the GPU specification proves the specification without
creating the job.

Two shapes exist:

``--gpu``       the single bounded pilot job ``job-jspace-s3-p0r2-pilot-g1``.
                ``replicaRetryLimit`` is 0 and parallelism is 1, so the job
                cannot silently perform a second model execution.
``--recovery``  the CPU-only job ``job-jspace-s3-p0r2-recover-g1`` in either
                ``prefix-preflight`` or ``recover`` mode. It never requests an
                accelerator.

A GPU specification is refused unless a built authorization document is
supplied, so no code path renders a launchable model job from nothing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


SCHEMA_VERSION = "study3-p0-r2-job-spec-v1"
STAGE = "STUDY3-P0-R2"

GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g1"
BLOB_PREFIX_ROOT = "study3/p0_r2/g1/"
RECOVERY_MODES = ("prefix-preflight", "recover")

SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"
RESOURCE_GROUP = "rg-jspace-observation-sea"
ENVIRONMENT = "cae-jspace-observation-sea-vnet2"
IDENTITY = (
    "/subscriptions/%s/resourcegroups/%s/providers/Microsoft.ManagedIdentity"
    "/userAssignedIdentities/id-jspace-aca-acrpull-sea"
    % (SUBSCRIPTION, RESOURCE_GROUP))
STORAGE_ACCOUNT = "stjspaceobssea0708231738"
BLOB_CONTAINER = "jspace-study3-runtime"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_ATTEMPT = re.compile(r"^p0r2-g1-[0-9A-Za-z-]{1,96}$")


class JobSpecDefect(Exception):
    """The requested specification is not one this stage may render."""


def _require_image(image):
    if not isinstance(image, str) or "@" not in image:
        raise JobSpecDefect("the image must be digest-pinned")
    _, _, digest = image.partition("@")
    if not _DIGEST.fullmatch(digest):
        raise JobSpecDefect("the image digest %r is malformed" % digest)
    return image, digest


def _require_attempt(attempt):
    if not isinstance(attempt, str) or not _ATTEMPT.fullmatch(attempt):
        raise JobSpecDefect(
            "attempt %r is not in the p0r2-g1-* namespace" % attempt)
    return attempt


def _load(path, label):
    try:
        return json.loads(Path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise JobSpecDefect("%s is unreadable: %s" % (label, exc))


def recovery_spec(mode: str, *, name: str = RECOVERY_JOB, image: str,
                  attempt: str, lock_sha256: str | None = None) -> dict:
    if mode not in RECOVERY_MODES:
        raise JobSpecDefect(
            "recovery mode must be one of %r" % (RECOVERY_MODES,))
    image, digest = _require_image(image)
    attempt = _require_attempt(attempt)
    if name != RECOVERY_JOB:
        raise JobSpecDefect(
            "the CPU recovery job must be named %r" % RECOVERY_JOB)
    env = [
        {"name": "P0_R2_RECOVERY_MODE", "value": mode},
        {"name": "P0_R2_ATTEMPT", "value": attempt},
        {"name": "P0_R2_IMAGE_DIGEST", "value": digest},
        {"name": "P0_R2_BLOB_ACCOUNT", "value": STORAGE_ACCOUNT},
        {"name": "P0_R2_BLOB_CONTAINER", "value": BLOB_CONTAINER},
        {"name": "P0_R2_BLOB_PREFIX",
         "value": "%s%s/" % (BLOB_PREFIX_ROOT, attempt)},
        {"name": "P0_R2_REQUIRE_CPU_ONLY", "value": "1"},
    ]
    if lock_sha256:
        env.append({"name": "P0_R2_LOCK_SHA256", "value": lock_sha256})
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "kind": "cpu-recovery",
        "mode": mode,
        "requests_accelerator": False,
        "identity": {"type": "UserAssigned",
                     "userAssignedIdentities": {IDENTITY: {}}},
        "properties": {
            "environmentId": ENVIRONMENT,
            "configuration": {
                "triggerType": "Manual",
                "replicaTimeout": 3600,
                "replicaRetryLimit": 0,
                "manualTriggerConfig": {"parallelism": 1,
                                        "replicaCompletionCount": 1},
                "registries": [{"server": "acrjspaceobssea0708231738.azurecr.io",
                                "identity": IDENTITY}],
            },
            "template": {
                "containers": [{
                    "name": "recover",
                    "image": image,
                    "command": ["/usr/local/bin/p0_r2_recovery_v1.sh"],
                    "resources": {"cpu": 2.0, "memory": "4Gi"},
                    "env": env,
                }],
            },
        },
    }


def gpu_spec(*, name: str = GPU_JOB, image: str, attempt: str,
             authorization: dict) -> dict:
    """Render the one bounded pilot job. Requires a built authorization."""
    if name != GPU_JOB:
        raise JobSpecDefect("the GPU job must be named %r" % GPU_JOB)
    image, digest = _require_image(image)
    attempt = _require_attempt(attempt)
    if not isinstance(authorization, dict) \
            or authorization.get("outcome") != "AUTHORIZED":
        raise JobSpecDefect(
            "a GPU specification requires a built pilot authorization; "
            "rendering one from nothing is refused")
    if authorization.get("image_digest") != digest:
        raise JobSpecDefect(
            "the authorization binds digest %r, not %r"
            % (authorization.get("image_digest"), digest))
    if authorization.get("attempt_id") != attempt:
        raise JobSpecDefect(
            "the authorization binds attempt %r, not %r"
            % (authorization.get("attempt_id"), attempt))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "kind": "gpu-pilot",
        "authorized_executions": 1,
        "identity": {"type": "UserAssigned",
                     "userAssignedIdentities": {IDENTITY: {}}},
        "properties": {
            "environmentId": ENVIRONMENT,
            "configuration": {
                "triggerType": "Manual",
                "replicaTimeout": 7200,
                # Zero retries: a failed replica is a stop, never a silent
                # second model execution.
                "replicaRetryLimit": 0,
                "manualTriggerConfig": {"parallelism": 1,
                                        "replicaCompletionCount": 1},
                "registries": [{"server": "acrjspaceobssea0708231738.azurecr.io",
                                "identity": IDENTITY}],
            },
            "template": {
                "containers": [{
                    "name": "pilot",
                    "image": image,
                    "command": ["/usr/local/bin/p0_r2_model_pilot_v1.sh"],
                    "resources": {"cpu": 8.0, "memory": "56Gi"},
                    "env": [
                        {"name": "P0_R2_ATTEMPT", "value": attempt},
                        {"name": "P0_R2_IMAGE_DIGEST", "value": digest},
                        {"name": "P0_R2_EXECUTABLE_COMMIT",
                         "value": authorization.get("executable_commit")},
                        {"name": "P0_R2_REPLAY_ATTEMPT",
                         "value": authorization.get("replay_attempt_id")},
                        {"name": "P0_R2_BLOB_ACCOUNT",
                         "value": STORAGE_ACCOUNT},
                        {"name": "P0_R2_BLOB_CONTAINER",
                         "value": BLOB_CONTAINER},
                        {"name": "P0_R2_BLOB_PREFIX",
                         "value": "%s%s/" % (BLOB_PREFIX_ROOT, attempt)},
                        {"name": "P0_R2_REQUIRE_ACCELERATOR", "value": "1"},
                    ],
                }],
            },
        },
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_job_spec_v1.py",
        "stage": STAGE,
        "gpu_job": GPU_JOB,
        "recovery_job": RECOVERY_JOB,
        "recovery_modes": list(RECOVERY_MODES),
        "creates_or_starts_azure_objects": False,
        "gpu_spec_requires_authorization": True,
        "gpu_replica_retry_limit": 0,
        "blob_prefix_root": BLOB_PREFIX_ROOT,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--gpu", action="store_true")
    mode.add_argument("--recovery", choices=RECOVERY_MODES)
    parser.add_argument("--name")
    parser.add_argument("--image")
    parser.add_argument("--attempt")
    parser.add_argument("--authorization")
    parser.add_argument("--lock-sha256")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    try:
        if args.gpu:
            if not args.authorization:
                raise JobSpecDefect("--gpu requires --authorization")
            document = gpu_spec(
                name=args.name or GPU_JOB, image=args.image,
                attempt=args.attempt,
                authorization=_load(args.authorization, "authorization"))
        else:
            document = recovery_spec(
                args.recovery, name=args.name or RECOVERY_JOB,
                image=args.image, attempt=args.attempt,
                lock_sha256=args.lock_sha256)
    except JobSpecDefect as exc:
        print("P0_R2_JOB_SPEC_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
