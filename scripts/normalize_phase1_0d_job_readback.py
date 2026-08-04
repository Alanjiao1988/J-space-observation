#!/usr/bin/env python3
"""Remove only Azure's empty, platform-owned ephemeral-storage readback field."""

from __future__ import annotations

import json
import sys
from typing import Any


EXPECTED_JOB_NAME = "job-jspace-p10d-confirmation"
EXPECTED_PROFILE = "gpu-t4"
EXPECTED_RESOURCES = {"cpu": 8.0, "memory": "56Gi"}


class ReadbackNormalizationError(RuntimeError):
    """The ARM response is not the one narrow compatibility case."""


def normalize_job_readback(document: Any) -> tuple[dict[str, Any], bool]:
    """Validate the generation Job identity/resources and remove one empty field."""

    if not isinstance(document, dict):
        raise ReadbackNormalizationError("ARM Job response is not an object")
    if document.get("name") != EXPECTED_JOB_NAME:
        raise ReadbackNormalizationError("ARM Job response has an unexpected name")

    properties = document.get("properties")
    if not isinstance(properties, dict):
        raise ReadbackNormalizationError("ARM Job response has no properties object")
    if properties.get("workloadProfileName") != EXPECTED_PROFILE:
        raise ReadbackNormalizationError(
            "ARM Job response has an unexpected workload profile"
        )

    template = properties.get("template")
    containers = template.get("containers") if isinstance(template, dict) else None
    if not isinstance(containers, list) or len(containers) != 1:
        raise ReadbackNormalizationError(
            "ARM Job response does not contain exactly one container"
        )
    container = containers[0]
    if not isinstance(container, dict):
        raise ReadbackNormalizationError("ARM Job container is not an object")

    resources = container.get("resources")
    if resources == EXPECTED_RESOURCES:
        return document, False
    expected_with_empty_ephemeral = {
        **EXPECTED_RESOURCES,
        "ephemeralStorage": "",
    }
    if resources != expected_with_empty_ephemeral:
        raise ReadbackNormalizationError(
            "ARM Job resources are not exact 8 CPU/56Gi with only absent-or-empty "
            "platform ephemeral storage"
        )

    del resources["ephemeralStorage"]
    return document, True


def main() -> int:
    try:
        document = json.load(sys.stdin)
        normalized, changed = normalize_job_readback(document)
    except ReadbackNormalizationError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1

    if changed:
        print(
            "[NOTE] Removed only the empty platform-injected "
            "resources.ephemeralStorage readback field",
            file=sys.stderr,
        )
    json.dump(normalized, sys.stdout, separators=(",", ":"), sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
