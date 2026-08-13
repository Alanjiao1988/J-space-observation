#!/usr/bin/env python3
"""Generate exact Container Apps job specs without command-line payloads."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_authorization_v3 as AUTHZ  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-container-apps-job-spec-v3"
SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"
RESOURCE_GROUP = "rg-jspace-observation-sea"
ENVIRONMENT = "cae-jspace-observation-sea-vnet2"
REGISTRY = "acrjspaceobssea0708231738.azurecr.io"
IDENTITY_NAME = "id-jspace-aca-acrpull-sea"
IDENTITY_CLIENT_ID = "479d9229-632e-4490-ad92-854a34dfddf8"

ENVIRONMENT_ID = (
    "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.App/"
    "managedEnvironments/%s" % (SUBSCRIPTION, RESOURCE_GROUP, ENVIRONMENT))
IDENTITY_ID = (
    "/subscriptions/%s/resourcegroups/%s/providers/"
    "Microsoft.ManagedIdentity/userAssignedIdentities/%s"
    % (SUBSCRIPTION, RESOURCE_GROUP, IDENTITY_NAME))


class JobSpecDefect(Exception):
    """The job spec inputs are incomplete or unsafe."""


def _read(path, label):
    if not path or not os.path.isfile(path):
        raise JobSpecDefect("%s must name an existing file" % label)
    with open(path, "rb") as handle:
        return handle.read()


def _env(mapping):
    return [{"name": name, "value": value}
            for name, value in sorted(mapping.items())]


def build_spec(name, image, command, env, workload_profile, cpu, memory,
               timeout):
    if not name or not image.startswith(REGISTRY + "/") \
            or "@sha256:" not in image:
        raise JobSpecDefect("the job requires a name and digest-pinned image")
    return {
        "name": name,
        "location": "Southeast Asia",
        "identity": {
            "type": "UserAssigned",
            "userAssignedIdentities": {IDENTITY_ID: {}},
        },
        "properties": {
            "environmentId": ENVIRONMENT_ID,
            "workloadProfileName": workload_profile,
            "configuration": {
                "triggerType": "Manual",
                "replicaTimeout": timeout,
                "replicaRetryLimit": 0,
                "manualTriggerConfig": {
                    "parallelism": 1,
                    "replicaCompletionCount": 1,
                },
                "registries": [{
                    "server": REGISTRY,
                    "identity": IDENTITY_ID,
                }],
            },
            "template": {
                "containers": [{
                    "name": name,
                    "image": image,
                    "command": [command],
                    "env": _env(env),
                    "resources": {"cpu": cpu, "memory": memory},
                }],
            },
        },
    }


def gpu_spec(name, image, attempt, lock_file, replay_receipt,
             reconstruction_receipt, head_proof, sentinel=False):
    payloads = {
        "P0_R1_LOCK_V3_B64": _read(lock_file, "--lock-file"),
        "P0_R1_REPLAY_RECEIPT_V3_B64":
            _read(replay_receipt, "--replay-receipt"),
        "P0_R1_RECONSTRUCTION_RECEIPT_V3_B64":
            _read(reconstruction_receipt, "--reconstruction-receipt"),
        "P0_R1_HEAD_PROOF_V3_B64": _read(head_proof, "--head-proof"),
    }
    env = {
        key: AUTHZ.encode_injection(value) for key, value in payloads.items()}
    env.update({
        "P0_R1_SRC": "/opt/jspace/src",
        "P0_R1_RUNTIME_ROOT": "/workspace/runtime",
        "P0_R1_OUT_DIR": "/workspace/runtime/result",
        "P0_R1_EXECUTOR": "sentinel" if sentinel else "production",
        "P0_R1_ATTEMPT": attempt,
        "P0_R1_IMAGE_DIGEST": image.rsplit("@", 1)[1],
        "AZURE_CLIENT_ID": IDENTITY_CLIENT_ID,
    })
    if sentinel:
        env["P0_R1_CANARY_IN_MEMORY_BLOB"] = "1"
    return build_spec(
        name, image, "/usr/local/bin/p0_r1_model_pilot_v3.sh", env,
        "Consumption" if sentinel else "gpu-t4",
        2.0 if sentinel else 4.0, "4Gi" if sentinel else "28Gi",
        1800 if sentinel else 7200)


def recovery_spec(name, image, mode, attempt, lock_file=None):
    if mode not in ("prefix-preflight", "recover"):
        raise JobSpecDefect("recovery mode must be prefix-preflight or recover")
    env = {
        "P0_R1_SRC": "/opt/jspace/src",
        "P0_R1_RUNTIME_ROOT": "/workspace/runtime",
        "P0_R1_RECOVERY_MODE": mode,
        "P0_R1_ATTEMPT": attempt,
        "AZURE_CLIENT_ID": IDENTITY_CLIENT_ID,
    }
    if mode == "recover":
        env["P0_R1_LOCK_V3_B64"] = AUTHZ.encode_injection(
            _read(lock_file, "--lock-file"))
    return build_spec(
        name, image, "/usr/local/bin/p0_r1_recovery_v3.sh", env,
        "Consumption", 1.0, "2Gi", 1800)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gpu", action="store_true")
    mode.add_argument("--cli-canary", action="store_true")
    mode.add_argument("--recovery", choices=("prefix-preflight", "recover"))
    parser.add_argument("--name")
    parser.add_argument("--image")
    parser.add_argument("--attempt")
    parser.add_argument("--lock-file")
    parser.add_argument("--replay-receipt")
    parser.add_argument("--reconstruction-receipt")
    parser.add_argument("--head-proof")
    parser.add_argument("--out")
    parser.add_argument("--identity", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "module": "p0_r1_job_spec_v3.py",
            "payload_carrier": "generated JSON/YAML file, not command line",
            "profiles": ["Consumption", "gpu-t4"],
            "replica_retry_limit": 0,
        }, indent=2, sort_keys=True))
        return 0
    if not args.name or not args.image or not args.attempt or not args.out:
        print("FAIL: mode, --name, --image, --attempt and --out are required",
              file=sys.stderr)
        return 2
    try:
        if args.gpu or args.cli_canary:
            document = gpu_spec(
                args.name, args.image, args.attempt, args.lock_file,
                args.replay_receipt, args.reconstruction_receipt,
                args.head_proof, sentinel=args.cli_canary)
        elif args.recovery:
            document = recovery_spec(
                args.name, args.image, args.recovery, args.attempt,
                lock_file=args.lock_file)
        else:
            raise JobSpecDefect("one job-spec mode is required")
    except (AUTHZ.AuthorizationRefused, JobSpecDefect) as exc:
        print("P0_R1_JOB_SPEC_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    with open(args.out, "wb") as handle:
        handle.write((json.dumps(document, indent=2, sort_keys=True) + "\n")
                     .encode("utf-8"))
    print("P0_R1_JOB_SPEC_WRITTEN=%s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
