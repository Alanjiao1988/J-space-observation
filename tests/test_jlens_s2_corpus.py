"""Model-free tests for deterministic S2 corpus acquisition."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_corpus as corpus  # noqa: E402
import jlens_s2_protocol as s2  # noqa: E402


class FakeTokenizer:
    bos_token_id = 1
    add_bos_token = True

    def __call__(self, texts, **kwargs):
        assert kwargs == {
            "add_special_tokens": True,
            "return_attention_mask": False,
            "truncation": False,
        }
        rows = []
        for text in texts:
            index = int(text.split(" ", 1)[0].split("-", 1)[1])
            rows.append([1, index + 10] + list(range(2, 148)))
        return {"input_ids": rows}


class FakeDownloader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def readall(self) -> bytes:
        return self.payload

    def chunks(self):
        yield self.payload[: len(self.payload) // 2]
        yield self.payload[len(self.payload) // 2 :]


class FakeContainerClient:
    def __init__(self, initial=None) -> None:
        self.objects = dict(initial or {})

    def upload_blob(self, *, name, data, overwrite):
        assert overwrite is False
        if name in self.objects:
            raise RuntimeError("exists")
        self.objects[name] = data.read() if hasattr(data, "read") else bytes(data)

    def download_blob(self, name):
        return FakeDownloader(self.objects[name])


def _source_row(index: int, suffix: str = "") -> dict[str, str]:
    return {"text": f"row-{index} " + ("x" * 600) + suffix}


def test_repository_prompt_contract_extracts_every_declared_source() -> None:
    contract = s2.load_and_validate_corpus_contract(ROOT)
    entries = list(corpus.repository_prompt_entries(ROOT, contract))
    rows = corpus.prompt_bank_rows(entries)
    assert len(entries) > 500
    assert len(rows) > 100
    roles = {
        source["role"]
        for row in rows
        for source in row["sources"]
    }
    assert "official S3 benchmark" in roles
    assert "Phase 1 bank and RQ2 candidate material" in roles
    assert "public parser fixtures" in roles
    assert "prior J-lens fit and heldout material" in roles


def test_prompt_bank_deduplicates_exact_bytes_but_retains_coordinates() -> None:
    rows = corpus.prompt_bank_rows(
        [
            ("one", "a:1", "same"),
            ("two", "b:2", "same"),
            ("one", "a:3", "different"),
        ]
    )
    assert len(rows) == 2
    same = next(row for row in rows if row["prompt_text"] == "same")
    assert same["prompt_sha256"] == hashlib.sha256(b"same").hexdigest()
    assert same["sources"] == [
        {"coordinate": "a:1", "role": "one"},
        {"coordinate": "b:2", "role": "two"},
    ]


def test_phase1_blob_source_fails_closed_on_manifest_or_object_drift() -> None:
    manifest = (
        ROOT
        / "artifacts"
        / "phase1-0d-confirmation"
        / "20260804T154518Z"
        / "artifact_manifest.json"
    ).read_bytes()
    assert s2.sha256_bytes(manifest) == corpus.PHASE1_SOURCE_MANIFEST_SHA256
    with pytest.raises(corpus.CorpusAcquisitionError, match="review-form SHA"):
        list(
            corpus.phase1_blob_prompt_entries(
                manifest,
                b'{"prompt_text":"synthetic"}\n',
            )
        )
    with pytest.raises(corpus.CorpusAcquisitionError, match="manifest SHA"):
        list(corpus.phase1_blob_prompt_entries(manifest + b"x", b""))


def test_scan_assigns_exact_roles_and_reconstructs_exclusion_rollups(
    tmp_path: Path,
) -> None:
    dataset = [_source_row(index) for index in range(1405)]
    protected = corpus.prompt_bank_rows(
        [("test", "fixture:1", "never appears in source")]
    )
    audit = tmp_path / "exclusion.jsonl"
    result = corpus.scan_and_assign(
        dataset,
        tokenizer=FakeTokenizer(),
        protected_bank=protected,
        exclusion_path=audit,
        dataset_revision="1" * 40,
        expected_rows=len(dataset),
        batch_size=37,
    )
    assert len(result["assigned_rows"]) == 1402
    assert result["eligible_unique_rows"] == 1405
    assert result["scanned_rows"] == 1405
    summary = result["exclusion_audit"]["category_summary"]
    assert summary["eligible_unassigned_after_first_1402"]["count"] == 3
    assert sum(row["count"] for row in summary.values()) == 3
    assert result["exclusion_audit"]["sha256"] == s2.sha256_file(audit)


def test_scan_rejects_short_overlap_underlength_and_duplicate_rows(
    tmp_path: Path,
) -> None:
    dataset = [_source_row(index) for index in range(1406)]
    dataset[0] = {"text": "short"}
    dataset[1] = {"text": "row-1 " + ("protected" * 80)}
    protected = corpus.prompt_bank_rows(
        [("test", "fixture:1", "protected")]
    )

    class EdgeTokenizer(FakeTokenizer):
        def __call__(self, texts, **kwargs):
            result = super().__call__(texts, **kwargs)
            for text, ids in zip(texts, result["input_ids"], strict=True):
                index = int(text.split(" ", 1)[0].split("-", 1)[1])
                if index == 2:
                    ids[:] = ids[:127]
                elif index == 3:
                    ids[1] = 14
            return result

    result = corpus.scan_and_assign(
        dataset,
        tokenizer=EdgeTokenizer(),
        protected_bank=protected,
        exclusion_path=tmp_path / "audit.jsonl",
        dataset_revision="1" * 40,
        expected_rows=len(dataset),
        batch_size=41,
    )
    summary = result["exclusion_audit"]["category_summary"]
    assert summary["short_raw_text"]["count"] == 1
    assert summary["protected_prompt_overlap"]["count"] == 1
    assert summary["under_128_tokens"]["count"] == 1
    assert summary["duplicate_128_token_ids"]["count"] == 1
    assert len(result["assigned_rows"]) == 1402


def test_build_corpus_manifest_validates_exact_rows(tmp_path: Path) -> None:
    dataset = [_source_row(index) for index in range(1402)]
    scan = corpus.scan_and_assign(
        dataset,
        tokenizer=FakeTokenizer(),
        protected_bank=corpus.prompt_bank_rows(
            [("test", "fixture", "not present")]
        ),
        exclusion_path=tmp_path / "exclusion_audit.jsonl",
        dataset_revision="1" * 40,
        expected_rows=len(dataset),
    )
    rows_path = tmp_path / "corpus_rows.jsonl"
    bank_path = tmp_path / "protected_prompt_bank.jsonl"
    corpus.write_canonical_jsonl(rows_path, scan["assigned_rows"])
    corpus.write_canonical_jsonl(
        bank_path,
        corpus.prompt_bank_rows([("test", "fixture", "not present")]),
    )
    manifest, rows = corpus.build_corpus_manifest(
        dataset_revision="1" * 40,
        dataset_files=[
            {"bytes": 1, "path": "train.parquet", "sha256": "2" * 64}
        ],
        license_file={
            "attribution": "attribution",
            "bytes": 1,
            "license_id": "cc-by-sa-3.0,gfdl",
            "path": "upstream_README.md",
            "sha256": "3" * 64,
            "share_alike": True,
        },
        rows_path=rows_path,
        exclusion_path=tmp_path / "exclusion_audit.jsonl",
        protected_bank_path=bank_path,
        eligible_unique_rows=1402,
        scanned_rows=1402,
    )
    assert manifest["rows"]["sha256"] == s2.sha256_file(rows_path)
    assert len(rows) == 1402


def test_create_only_blob_store_verifies_readback_and_manifest_last(
    tmp_path: Path,
) -> None:
    client = FakeContainerClient({"historical/object": b"old"})
    store = corpus.CreateOnlyBlobStore(
        account="account",
        container="container",
        prefix="new/run",
        client_id=None,
        container_client=client,
    )
    assert store.download_absolute("historical/object") == b"old"
    (tmp_path / "a.json").write_bytes(b"a")
    (tmp_path / "artifact_manifest.json").write_bytes(b"manifest")
    result = store.upload_pack(
        subprefix="pack",
        files=[tmp_path / "artifact_manifest.json", tmp_path / "a.json"],
        root=tmp_path,
    )
    assert result["manifest_written_last"]
    assert result["uploaded"][-1]["blob"].endswith("/artifact_manifest.json")
    with pytest.raises(RuntimeError, match="exists"):
        store.upload_bytes("pack/a.json", b"replacement")


def test_license_notice_is_revision_and_hash_bound() -> None:
    notice = corpus.license_notice(
        dataset_revision="1" * 40,
        upstream_readme_sha256="2" * 64,
    ).decode("utf-8")
    assert "CC BY-SA" not in notice
    assert "Creative Commons Attribution-ShareAlike 3.0" in notice
    assert "GNU Free Documentation License" in notice
    assert "1" * 40 in notice
    assert "2" * 64 in notice


def test_acquisition_script_has_no_top_level_tokenizer_or_dataset_import() -> None:
    source = (
        ROOT / "scripts" / "jlens_s2_corpus_acquisition.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"datasets", "tokenizers", "transformers"}
    top_level = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level.add(node.module.split(".", 1)[0])
    assert top_level.isdisjoint(forbidden)


def test_source_contract_remains_unchanged_after_protocol_freeze() -> None:
    assert s2.sha256_file(
        ROOT / "docs" / "jlens_s2_corpus_source_contract.json"
    ) == "bde80360e5f0dda1701ebc41341bdc777416efcae43a4764493180e185008e6d"
    assert s2.sha256_file(
        ROOT / "docs" / "jlens_s2_protocol.json"
    ) == "e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2"
