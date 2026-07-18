#!/usr/bin/env python3
"""Validate durable ARM deployment tickets and elect the earliest claim."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEX_40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
INVOCATION = re.compile(r"^[0-9a-f]{32}$")


class ClaimValidationError(ValueError):
    pass


def _timestamp(value: Any) -> tuple[datetime, str]:
    if not isinstance(value, str) or not value.strip():
        raise ClaimValidationError("claim server timestamp is missing")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ClaimValidationError(f"invalid claim server timestamp: {text}") from error
    if parsed.tzinfo is None:
        raise ClaimValidationError("claim server timestamp has no timezone")
    normalized = parsed.astimezone(timezone.utc)
    return normalized, normalized.isoformat().replace("+00:00", "Z")


def _output_values(claim: dict[str, Any]) -> dict[str, str]:
    properties = claim.get("properties") or {}
    raw = properties.get("outputs", claim.get("outputs"))
    if not isinstance(raw, dict):
        raise ClaimValidationError("claim outputs are missing")
    values: dict[str, str] = {}
    for key, record in raw.items():
        if not isinstance(record, dict) or "value" not in record:
            raise ClaimValidationError(f"claim output {key!r} has no value")
        value = record["value"]
        if not isinstance(value, str) or not value:
            raise ClaimValidationError(f"claim output {key!r} is empty/non-string")
        values[str(key)] = value
    return values


def _validate_outputs(
    *,
    name: str,
    prefix: str,
    outputs: dict[str, str],
    fixed: dict[str, str],
) -> None:
    required = {
        "claimName",
        "claimPrefix",
        "invocationId",
        "operation",
        *fixed,
    }
    missing = sorted(required - outputs.keys())
    if missing:
        raise ClaimValidationError(f"claim {name} missing outputs: {missing}")
    if outputs["claimName"] != name or outputs["claimPrefix"] != prefix:
        raise ClaimValidationError(f"claim {name} has mismatched name/prefix outputs")
    suffix = name.removeprefix(prefix)
    if not INVOCATION.fullmatch(suffix) or outputs["invocationId"] != suffix:
        raise ClaimValidationError(f"claim {name} invocation binding is invalid")
    for key, value in fixed.items():
        if outputs.get(key) != value:
            raise ClaimValidationError(
                f"claim {name} fixed provenance mismatch for {key}"
            )

    operation = outputs["operation"]
    if operation not in {"build", "launch"}:
        raise ClaimValidationError(f"claim {name} operation is invalid")
    for key in ("projectSha", "primaryProjectSha", "launcherSha"):
        if key in outputs and not HEX_40.fullmatch(outputs[key]):
            raise ClaimValidationError(f"claim {name} has invalid {key}")
    if "imageDigest" in outputs and not DIGEST.fullmatch(outputs["imageDigest"]):
        raise ClaimValidationError(f"claim {name} has invalid image digest")
    if "runId" in outputs and not RUN_ID.fullmatch(outputs["runId"]):
        raise ClaimValidationError(f"claim {name} has invalid run ID")
    if "attempt" in outputs and outputs["attempt"] not in {
        "primary",
        "operational-fix",
    }:
        raise ClaimValidationError(f"claim {name} has invalid attempt")
    if operation == "build":
        for key in ("buildRunId", "stagingTag", "imageDigest", "projectSha"):
            if key not in outputs:
                raise ClaimValidationError(f"build claim {name} missing {key}")
        expected_staging_prefix = f"staging-{outputs['projectSha']}-"
        if not outputs["stagingTag"].startswith(expected_staging_prefix):
            raise ClaimValidationError(f"build claim {name} staging tag mismatch")
    else:
        for key in (
            "runId",
            "attempt",
            "projectSha",
            "primaryProjectSha",
            "launcherSha",
            "imageDigest",
            "jobName",
        ):
            if key not in outputs:
                raise ClaimValidationError(f"launch claim {name} missing {key}")


def elect_claim(
    claims_payload: Any,
    *,
    prefix: str,
    fixed: dict[str, str],
) -> dict[str, Any]:
    claims = (
        claims_payload.get("value")
        if isinstance(claims_payload, dict)
        else claims_payload
    )
    if not isinstance(claims, list):
        raise ClaimValidationError("deployment claim listing is not an array")
    candidates: list[dict[str, Any]] = []
    names: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ClaimValidationError("deployment claim record is not an object")
        name = claim.get("name")
        if not isinstance(name, str) or not name.startswith(prefix):
            continue
        if name in names:
            raise ClaimValidationError(f"duplicate deployment claim name: {name}")
        names.add(name)
        properties = claim.get("properties") or {}
        timestamp_value = properties.get("timestamp", claim.get("timestamp"))
        parsed_timestamp, normalized_timestamp = _timestamp(timestamp_value)
        state = properties.get(
            "provisioningState", claim.get("provisioningState")
        )
        if not isinstance(state, str) or not state:
            raise ClaimValidationError(f"claim {name} state is missing")
        outputs = _output_values(claim)
        _validate_outputs(name=name, prefix=prefix, outputs=outputs, fixed=fixed)
        candidates.append(
            {
                "name": name,
                "server_timestamp": normalized_timestamp,
                "provisioning_state": state,
                "outputs": outputs,
                "_order": (parsed_timestamp, name),
            }
        )
    if not candidates:
        raise ClaimValidationError(f"no deployment claims found for prefix {prefix}")
    ordered = sorted(candidates, key=lambda item: item["_order"])
    winner = ordered[0]
    if len(ordered) > 1 and ordered[0]["_order"] == ordered[1]["_order"]:
        raise ClaimValidationError("ambiguous deployment claim winner")
    winner = {key: value for key, value in winner.items() if key != "_order"}
    winner["candidate_count"] = len(ordered)
    return winner


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def invocation_scratch_path(
    record_dir: str | Path, operation: str, invocation_id: str
) -> Path:
    if operation not in {"build", "launch"}:
        raise ClaimValidationError("scratch operation must be build or launch")
    if not INVOCATION.fullmatch(invocation_id):
        raise ClaimValidationError("scratch invocation ID is invalid")
    return Path(record_dir).resolve() / f".p05-{operation}-{invocation_id}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_id = subparsers.add_parser("new-id")
    new_id.add_argument("--bytes", type=int, default=16)

    elect = subparsers.add_parser("elect")
    elect.add_argument("--claims-json", required=True)
    elect.add_argument("--prefix", required=True)
    elect.add_argument("--fixed-json", required=True)
    elect.add_argument("--output", required=True)

    get = subparsers.add_parser("get")
    get.add_argument("--json", required=True)
    get.add_argument("--field", required=True)

    scratch = subparsers.add_parser("scratch-path")
    scratch.add_argument("--record-dir", required=True)
    scratch.add_argument("--operation", required=True)
    scratch.add_argument("--invocation-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "new-id":
        if args.bytes < 16:
            raise ClaimValidationError("claim invocation IDs require at least 128 bits")
        print(secrets.token_hex(args.bytes))
        return 0
    if args.command == "elect":
        fixed = _read_json(args.fixed_json)
        if not isinstance(fixed, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in fixed.items()
        ):
            raise ClaimValidationError("fixed provenance must be a string map")
        winner = elect_claim(
            _read_json(args.claims_json),
            prefix=args.prefix,
            fixed=fixed,
        )
        Path(args.output).write_text(
            json.dumps(winner, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0
    if args.command == "scratch-path":
        print(
            invocation_scratch_path(
                args.record_dir, args.operation, args.invocation_id
            )
        )
        return 0

    value: Any = _read_json(args.json)
    for component in args.field.split("."):
        if not isinstance(value, dict) or component not in value:
            raise ClaimValidationError(f"winner field is missing: {args.field}")
        value = value[component]
    if not isinstance(value, (str, int)):
        raise ClaimValidationError(f"winner field is not scalar: {args.field}")
    print(value)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimValidationError, json.JSONDecodeError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(2)
