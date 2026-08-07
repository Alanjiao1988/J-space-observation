"""Model-free and tiny-tensor tests for the full-layer S2 runtime."""

from __future__ import annotations

import ast
import io
import json
import os
import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402
import jlens_s2_runtime as runtime  # noqa: E402
import jlens_s3_protocol as s3  # noqa: E402


class FakeDownloader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def readall(self) -> bytes:
        return self.payload

    def chunks(self):
        yield self.payload


class FakeContainer:
    def __init__(self) -> None:
        self.objects = {}

    def upload_blob(self, *, name, data, overwrite):
        assert not overwrite
        if name in self.objects:
            raise RuntimeError("exists")
        self.objects[name] = data.read() if hasattr(data, "read") else bytes(data)

    def download_blob(self, name):
        return FakeDownloader(self.objects[name])

    def list_blobs(self, name_starts_with):
        return [
            type("Blob", (), {"name": name})
            for name in sorted(self.objects)
            if name.startswith(name_starts_with)
        ]


def test_registered_corpus_role_slices_are_exact() -> None:
    pack = runtime.load_registered_corpus(ROOT / "data" / "jlens_s2_wikitext")
    assert {role: len(rows) for role, rows in pack["by_role"].items()} == {
        "A": 600,
        "B": 600,
        "heldout": 200,
        "smoke": 2,
    }
    rows = runtime.role_slice(pack, "A", 65, 128)
    assert len(rows) == 64
    assert [row["role_index"] for row in rows] == list(range(65, 129))
    with pytest.raises(runtime.S2RuntimeError, match="exceeds"):
        runtime.role_slice(pack, "smoke", 1, 3)


def test_heldout_metric_keys_require_exact_cartesian_coverage() -> None:
    expected_ids = ["heldout-a", "heldout-b"]
    rows = [
        {
            "finite": True,
            "layer": layer,
            "pair": pair,
            "sequence_id": sequence_id,
        }
        for sequence_id in expected_ids
        for pair in runtime.HELDOUT_PAIRS
        for layer in s2.SOURCE_LAYERS
    ]
    report = runtime.validate_heldout_metric_rows(rows, expected_ids)
    assert report["metric_row_count"] == 2 * 3 * 27
    with pytest.raises(runtime.S2RuntimeError, match="exactly cover"):
        runtime.validate_heldout_metric_rows(rows[:-1], expected_ids)
    duplicate = [*rows[:-1], rows[0]]
    with pytest.raises(runtime.S2RuntimeError, match="exactly cover"):
        runtime.validate_heldout_metric_rows(duplicate, expected_ids)


def test_production_attempt_manifest_binds_failed_progress_to_exact_resume() -> None:
    client = FakeContainer()
    store = runtime.BlobStore(
        account="account",
        container="container",
        prefix="production",
        client_id=None,
        container_client=client,
    )
    checkpoint_blob = (
        "production/shards/A-001-064/attempts/primary/checkpoints/n0032.pt"
    )
    checkpoint_sha = "a" * 64
    checkpoint_manifest_blob = (
        "production/shards/A-001-064/attempts/primary/checkpoints/n0032.json"
    )
    checkpoint_manifest = {
        "checkpoint": {
            "blob": checkpoint_blob,
            "bytes": 1,
            "sha256": checkpoint_sha,
        },
        "n_done": 32,
        "next_idx": 32,
        "source_layers": list(s2.SOURCE_LAYERS),
        "target_layer": s2.TARGET_LAYER,
    }
    checkpoint_manifest_bytes = s2.canonical_json_bytes(checkpoint_manifest)
    client.objects[checkpoint_manifest_blob] = checkpoint_manifest_bytes
    reference = {"blob": "production/success.json", "sha256": "b" * 64}
    resume = {
        "checkpoint_blob": checkpoint_blob,
        "checkpoint_manifest_blob": checkpoint_manifest_blob,
        "checkpoint_manifest_sha256": s2.sha256_bytes(
            checkpoint_manifest_bytes
        ),
        "checkpoint_sha256": checkpoint_sha,
        "n_done": 32,
    }
    attempts = [
        {
            "artifact_prefix": "production/shards/A-001-064/attempts/primary",
            "attempt_id": "primary",
            "end_time_utc": "2026-01-01T01:00:00Z",
            "execution": "execution-primary",
            "failure_reason": "platform_timeout",
            "job": "job-primary",
            "last_checkpoint": {
                "checkpoint_blob": checkpoint_blob,
                "checkpoint_sha256": checkpoint_sha,
            },
            "processed_count": 32,
            "resume_source": None,
            "shard_id": "A-001-064",
            "start_time_utc": "2026-01-01T00:00:00Z",
            "status": "infrastructure_failed",
            "success_receipt": None,
        },
        {
            "artifact_prefix": "production/shards/A-001-064/attempts/resume-1",
            "attempt_id": "resume-1",
            "end_time_utc": "2026-01-01T02:00:00Z",
            "execution": "execution-resume",
            "failure_reason": None,
            "job": "job-resume",
            "last_checkpoint": None,
            "processed_count": 64,
            "resume_source": resume,
            "shard_id": "A-001-064",
            "start_time_utc": "2026-01-01T01:00:00Z",
            "status": "success",
            "success_receipt": reference,
        },
    ]
    plan = {
        "blob_prefix": "production",
        "run_id": "run",
        "shards": [{"id": "A-001-064", "size": 64}],
    }
    manifest = {
        "attempts": attempts,
        "fit_image_digest": "sha256:" + "2" * 64,
        "fit_source_commit": "1" * 40,
        "production_plan_sha256": "3" * 64,
        "run_id": "run",
        "schema_version": "jlens-s2-production-attempts/v1",
        "sequence_recomputed": False,
        "successful_shards": {"A-001-064": reference},
    }
    report = runtime.validate_production_attempt_manifest(
        store,
        manifest,
        production_plan=plan,
        success_receipts={"A-001-064": reference},
        success_documents={
            "A-001-064": {
                "initial_next_idx": 32,
                "resumed": True,
            }
        },
        expected_fit_source_commit="1" * 40,
        expected_fit_image_digest="sha256:" + "2" * 64,
        production_plan_sha256="3" * 64,
    )
    assert report["partial_attempt_count"] == 1
    assert report["sequence_recomputed"] is False
    changed = json.loads(json.dumps(manifest))
    changed["attempts"][1]["resume_source"]["checkpoint_sha256"] = "c" * 64
    with pytest.raises(runtime.S2RuntimeError, match="resume manifest"):
        runtime.validate_production_attempt_manifest(
            store,
            changed,
            production_plan=plan,
            success_receipts={"A-001-064": reference},
            success_documents={
                "A-001-064": {
                    "initial_next_idx": 32,
                    "resumed": True,
                }
            },
            expected_fit_source_commit="1" * 40,
            expected_fit_image_digest="sha256:" + "2" * 64,
            production_plan_sha256="3" * 64,
        )


def test_blob_store_is_create_only_and_exact() -> None:
    client = FakeContainer()
    store = runtime.BlobStore(
        account="account",
        container="container",
        prefix="round",
        client_id=None,
        container_client=client,
    )
    row = store.upload_bytes("pack/a.json", b"payload")
    assert row == {
        "blob": "round/pack/a.json",
        "bytes": 7,
        "sha256": s2.sha256_bytes(b"payload"),
    }
    assert store.download_bytes("pack/a.json") == b"payload"
    assert store.list_absolute("round/") == ["round/pack/a.json"]
    with pytest.raises(RuntimeError, match="exists"):
        store.upload_bytes("pack/a.json", b"replacement")


def test_receipt_transport_binds_receipt_related_file_and_provenance() -> None:
    client = FakeContainer()
    store = runtime.BlobStore(
        account="account",
        container="container",
        prefix="run",
        client_id=None,
        container_client=client,
    )
    receipt = b'{"status":"success"}\n'
    lens = b"lens"
    manifest = {
        "complete": True,
        "create_only": True,
        "files": [
            {
                "bytes": len(lens),
                "relative_path": "lens.pt",
                "sha256": s2.sha256_bytes(lens),
                "written_order": 1,
            },
            {
                "bytes": len(receipt),
                "relative_path": "shard_receipt.json",
                "sha256": s2.sha256_bytes(receipt),
                "written_order": 2,
            },
        ],
        "image_digest": "sha256:" + "2" * 64,
        "manifest_written_last": True,
        "protocol_sha256": (
            "e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2"
        ),
        "schema_version": "jlens-s2-runtime-pack/v1",
        "source_commit": "1" * 40,
        "stage": "S2-F0-fit-shard",
    }
    client.objects = {
        "run/shard/artifact_manifest.json": s2.canonical_json_bytes(manifest),
        "run/shard/lens.pt": lens,
        "run/shard/shard_receipt.json": receipt,
    }
    result = runtime.validate_receipt_transport(
        store,
        receipt_blob="run/shard/shard_receipt.json",
        receipt_sha256=s2.sha256_bytes(receipt),
        receipt_bytes=receipt,
        related_files=[
            {
                "blob": "run/shard/lens.pt",
                "bytes": len(lens),
                "sha256": s2.sha256_bytes(lens),
            }
        ],
        expected_source_commit="1" * 40,
        expected_image_digest="sha256:" + "2" * 64,
    )
    assert result["stage"] == "S2-F0-fit-shard"
    changed = json.loads(json.dumps(manifest))
    changed["files"][0]["sha256"] = "3" * 64
    client.objects["run/shard/artifact_manifest.json"] = s2.canonical_json_bytes(
        changed
    )
    with pytest.raises(runtime.S2RuntimeError, match="related artifact"):
        runtime.validate_receipt_transport(
            store,
            receipt_blob="run/shard/shard_receipt.json",
            receipt_sha256=s2.sha256_bytes(receipt),
            receipt_bytes=receipt,
            related_files=[
                {
                    "blob": "run/shard/lens.pt",
                    "bytes": len(lens),
                    "sha256": s2.sha256_bytes(lens),
                }
            ],
        )


def test_pack_manifest_binds_source_image_and_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JSPACE_CODE_COMMIT", "1" * 40)
    monkeypatch.setenv("JSPACE_IMAGE_DIGEST", "sha256:" + "2" * 64)
    protocol = tmp_path / "docs" / "jlens_s2_protocol.json"
    protocol.parent.mkdir()
    protocol.write_bytes((ROOT / "docs" / "jlens_s2_protocol.json").read_bytes())
    file_path = tmp_path / "result.json"
    file_path.write_bytes(b"{}\n")
    original = runtime.Path
    try:
        runtime.Path = lambda value: (
            protocol
            if value == "/workspace/repo/docs/jlens_s2_protocol.json"
            else original(value)
        )
        manifest = runtime.pack_manifest(
            stage="S2-T0-selection",
            files=[file_path],
            root=tmp_path,
            complete=True,
        )
    finally:
        runtime.Path = original
    assert manifest["source_commit"] == "1" * 40
    assert manifest["image_digest"] == "sha256:" + "2" * 64
    assert manifest["files"][0]["sha256"] == s2.sha256_file(file_path)
    s3.validate_json_schema(
        manifest,
        s2.load_json(ROOT / "docs" / "jlens_s2_runtime_pack.schema.json"),
    )
    assert runtime.validate_runtime_pack_manifest(manifest)["file_count"] == 1


def test_tiny_tensor_merge_comparison_and_logit_metrics() -> None:
    left = {layer: torch.eye(2) for layer in s2.SOURCE_LAYERS}
    right = {layer: torch.eye(2) * 3 for layer in s2.SOURCE_LAYERS}
    first = type(
        "Lens",
        (),
        {"jacobians": left, "n_prompts": 1},
    )()
    second = type(
        "Lens",
        (),
        {"jacobians": right, "n_prompts": 3},
    )()
    mean = runtime.independent_weighted_mean(torch, [first, second])
    assert torch.equal(mean[0], torch.eye(2) * 2.5)
    comparison = runtime.compare_tensor_matrices(torch, mean, mean)
    assert comparison["max_abs"] == 0.0
    assert comparison["max_relative_frobenius"] == 0.0
    assert comparison["min_cosine"] == pytest.approx(1.0)

    metrics = runtime.logit_pair_metrics(
        torch,
        torch.arange(100, dtype=torch.float32),
        torch.arange(100, dtype=torch.float32),
    )
    assert metrics == {
        "logit_cosine": pytest.approx(1.0),
        "rank_correlation": pytest.approx(1.0),
        "top10_overlap": 1.0,
        "top50_overlap": 1.0,
    }


def test_checkpoint_mirror_uploads_checkpoint_then_receipt(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.pt"
    state = {
        "jacobian_sum": {},
        "n_done": 8,
        "next_idx": 8,
        "skip_first": s2.SKIP_FIRST,
        "source_layers": list(s2.SOURCE_LAYERS),
        "target_layer": s2.TARGET_LAYER,
    }
    torch.save(state, checkpoint)
    client = FakeContainer()
    store = runtime.BlobStore(
        account="account",
        container="container",
        prefix="fit",
        client_id=None,
        container_client=client,
    )
    mirror = runtime.CheckpointMirror(
        torch_module=torch,
        path=checkpoint,
        store=store,
        subprefix="A-001",
        minimum_next_idx=0,
    )
    mirror.start()
    uploaded = mirror.finish()
    assert len(uploaded) == 1
    assert sorted(client.objects) == [
        "fit/A-001/checkpoints/n0008.json",
        "fit/A-001/checkpoints/n0008.pt",
    ]
    receipt = json.loads(client.objects["fit/A-001/checkpoints/n0008.json"])
    assert receipt["n_done"] == receipt["next_idx"] == 8


def test_checkpoint_loader_rejects_metadata_drift(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.pt"
    state = {
        "jacobian_sum": {},
        "n_done": 1,
        "next_idx": 1,
        "skip_first": s2.SKIP_FIRST,
        "source_layers": list(s2.SOURCE_LAYERS),
        "target_layer": s2.TARGET_LAYER,
    }
    torch.save(state, path)
    assert runtime.load_checkpoint_state(torch, path)["next_idx"] == 1
    state["target_layer"] = 26
    torch.save(state, path)
    with pytest.raises(runtime.S2RuntimeError, match="metadata"):
        runtime.load_checkpoint_state(torch, path)


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/jlens_s2_runtime.py",
        "scripts/jlens_s2_analysis.py",
        "scripts/jlens_s2_model_snapshot.py",
    ],
)
def test_runtime_scripts_do_not_import_heavy_packages_at_module_scope(
    relative: str,
) -> None:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    forbidden = {"jlens", "torch", "transformers"}
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden)


def test_runtime_source_does_not_change_frozen_s3_bytes() -> None:
    expected = {
        "docs/jlens_s3_validity_protocol.json": s2.S3_PROTOCOL_SHA256,
        "docs/jlens_s3_validity_protocol.schema.json": s2.S3_SCHEMA_SHA256,
    }
    assert {
        path: s2.sha256_file(ROOT / path) for path in expected
    } == expected


def test_production_plan_partitions_each_arm_once_and_preserves_checkpoints() -> None:
    plan = s2.load_json(ROOT / "docs" / "jlens_s2_production_plan.json")
    assert plan["dim_batch"] == 1
    assert plan["image"]["digest"] == (
        "sha256:403522b9a7a59b6db5d96fc211bdb3bdb80c6a9fcfa9d630541014c55587edc1"
    )
    for role in ("A", "B"):
        shards = [row for row in plan["shards"] if row["role"] == role]
        covered = [
            index
            for row in shards
            for index in range(row["start_index"], row["end_index"] + 1)
        ]
        assert covered == list(range(1, 601))
        assert all(
            row["size"] == row["end_index"] - row["start_index"] + 1
            for row in shards
        )
        assert [row["size"] for row in shards[3:]] == [59, 59, 59, 59, 59, 49]
        assert plan["cumulative_lenses"][f"{role}64"] == [f"{role}-001-064"]
        assert plan["cumulative_lenses"][f"{role}128"][-1] == f"{role}-065-128"
        assert plan["cumulative_lenses"][f"{role}256"][-1] == f"{role}-129-256"
        assert len(plan["cumulative_lenses"][f"{role}600"]) == 9
