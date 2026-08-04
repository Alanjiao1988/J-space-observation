"""Tests for the additive ARM readback shim around the frozen launcher."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
NORMALIZER_PATH = REPO_ROOT / "scripts/normalize_phase1_0d_job_readback.py"
SHIM_PATH = (
    REPO_ROOT
    / "infra/azure/scripts/24_run_phase1_0d_confirmation_rp_compat.sh"
)
FROZEN_LAUNCHER_PATH = (
    REPO_ROOT / "infra/azure/scripts/19_run_phase1_0d_confirmation.sh"
)

spec = importlib.util.spec_from_file_location("generation_readback", NORMALIZER_PATH)
assert spec is not None and spec.loader is not None
generation_readback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generation_readback)


def _job(resources, *, name="job-jspace-p10d-confirmation", profile="gpu-t4"):
    return {
        "name": name,
        "properties": {
            "workloadProfileName": profile,
            "template": {"containers": [{"resources": resources}]},
        },
    }


def test_normalizer_removes_only_empty_platform_ephemeral_storage():
    document = _job({"cpu": 8.0, "memory": "56Gi", "ephemeralStorage": ""})

    normalized, changed = generation_readback.normalize_job_readback(document)

    assert changed is True
    assert normalized["properties"]["template"]["containers"][0]["resources"] == {
        "cpu": 8.0,
        "memory": "56Gi",
    }


def test_normalizer_accepts_the_exact_resource_shape_without_platform_noise():
    document = _job({"cpu": 8.0, "memory": "56Gi"})

    normalized, changed = generation_readback.normalize_job_readback(document)

    assert changed is False
    assert normalized == document


@pytest.mark.parametrize(
    "document",
    [
        _job({"cpu": 8.0, "memory": "56Gi", "ephemeralStorage": "1Gi"}),
        _job({"cpu": 4.0, "memory": "56Gi", "ephemeralStorage": ""}),
        _job({"cpu": 8.0, "memory": "32Gi", "ephemeralStorage": ""}),
        _job({"cpu": 8.0, "memory": "56Gi", "other": ""}),
        _job({"cpu": 8.0, "memory": "56Gi"}, name="another-job"),
        _job({"cpu": 8.0, "memory": "56Gi"}, profile="Consumption"),
    ],
)
def test_normalizer_rejects_every_other_job_or_resource_shape(document):
    with pytest.raises(generation_readback.ReadbackNormalizationError):
        generation_readback.normalize_job_readback(document)


def test_normalizer_cli_fails_closed_on_nonempty_ephemeral_storage():
    result = subprocess.run(
        [sys.executable, "-I", str(NORMALIZER_PATH)],
        input=json.dumps(
            _job({"cpu": 8.0, "memory": "56Gi", "ephemeralStorage": "1Gi"})
        ),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "absent-or-empty platform ephemeral storage" in result.stderr


def test_shim_executes_the_frozen_launcher_and_nothing_else_scientific():
    text = SHIM_PATH.read_text(encoding="utf-8")

    assert 'exec /usr/bin/bash "$FROZEN_LAUNCHER"' in text
    assert 'EXPECTED_FROZEN_LAUNCHER_SHA256="ce448d818b3f8d24' in text
    assert "job-jspace-p10d-confirmation" in text
    assert "api-version=2024-03-01" in text
    assert "normalize_phase1_0d_job_readback.py" in text
    assert "run_phase1_0d_confirmation.py" not in text


def test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline():
    subprocess.run(
        ["/usr/bin/bash", "-n", str(SHIM_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
    baseline = json.loads(
        (REPO_ROOT / "docs/phase1_0d_rv2_protected_bytes.json").read_text(
            encoding="utf-8"
        )
    )
    entry = next(
        item
        for item in baseline["files"]
        if item["path"] == "infra/azure/scripts/19_run_phase1_0d_confirmation.sh"
    )
    payload = FROZEN_LAUNCHER_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
