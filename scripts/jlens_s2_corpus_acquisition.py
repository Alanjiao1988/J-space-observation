#!/usr/bin/env python3
"""Resolve, select, seal, and export the exact full-layer S2 corpus."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_corpus as corpus  # noqa: E402
import jlens_s2_protocol as s2  # noqa: E402


EXPECTED_PROTOCOL_SHA256 = (
    "e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2"
)
EXPECTED_CORPUS_CONTRACT_SHA256 = (
    "d1eccb2eb35da65f5c3cbb98ee4b6fbbe58de434fc5e6d420981367071706775"
)
EXPECTED_ARTIFACT_SCHEMA_SHA256 = (
    "36a5a5df70d859bfabc808ffb926bf61bc1738106650a58b9e62951966b3a2da"
)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def strict_environment() -> dict[str, str]:
    values = {
        "account": os.getenv("JSPACE_BLOB_ACCOUNT", "").strip(),
        "client_id": os.getenv("AZURE_CLIENT_ID", "").strip(),
        "container": os.getenv("JSPACE_BLOB_CONTAINER", "").strip(),
        "image_digest": os.getenv("JSPACE_IMAGE_DIGEST", "").strip(),
        "prefix": os.getenv("JSPACE_BLOB_PREFIX", "").strip("/"),
        "run_id": os.getenv("JSPACE_S2_CORPUS_RUN_ID", "").strip(),
        "source_commit": os.getenv("JSPACE_CODE_COMMIT", "").strip(),
    }
    missing = sorted(key for key, value in values.items() if not value)
    if missing:
        raise corpus.CorpusAcquisitionError(
            "required execution environment is missing: " + ", ".join(missing)
        )
    if not s2._IMMUTABLE_REF.fullmatch(values["source_commit"]):
        raise corpus.CorpusAcquisitionError("source commit must be a full SHA-1")
    if not values["image_digest"].startswith("sha256:") or len(
        values["image_digest"]
    ) != 71:
        raise corpus.CorpusAcquisitionError("image digest must be sha256:<64 hex>")
    if values["prefix"] != f"jlens-s2/corpus/{values['run_id']}":
        raise corpus.CorpusAcquisitionError("corpus Blob prefix is not run-specific")
    return values


def card_data_dict(info: Any) -> dict[str, Any]:
    card = getattr(info, "card_data", None)
    if card is None:
        return {}
    if isinstance(card, dict):
        return dict(card)
    if hasattr(card, "to_dict"):
        return dict(card.to_dict())
    try:
        return dict(card)
    except (TypeError, ValueError) as exc:
        raise corpus.CorpusAcquisitionError(
            "dataset card metadata is not reconstructible"
        ) from exc


def resolve_dataset_source(source_dir: Path) -> dict[str, Any]:
    """Resolve and download source/license bytes before tokenizer construction."""

    corpus.assert_tokenizer_not_loaded()
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    floating = api.dataset_info(corpus.DATASET_ID, revision="main", files_metadata=True)
    revision = str(getattr(floating, "sha", ""))
    if not s2._IMMUTABLE_REF.fullmatch(revision):
        raise corpus.CorpusAcquisitionError("Hugging Face returned no immutable commit")
    info = api.dataset_info(
        corpus.DATASET_ID,
        revision=revision,
        files_metadata=True,
    )
    if str(getattr(info, "sha", "")) != revision:
        raise corpus.CorpusAcquisitionError("immutable dataset readback revision drifted")
    card = card_data_dict(info)
    licenses = card.get("license")
    if isinstance(licenses, str):
        licenses = [licenses]
    if sorted(licenses or []) != ["cc-by-sa-3.0", "gfdl"]:
        raise corpus.CorpusAcquisitionError(
            f"unexpected dataset license declaration: {licenses!r}"
        )
    siblings = sorted(
        str(getattr(row, "rfilename", ""))
        for row in getattr(info, "siblings", [])
        if str(getattr(row, "rfilename", "")).startswith(corpus.TRAIN_FILE_PREFIX)
        and str(getattr(row, "rfilename", "")).endswith(".parquet")
    )
    if siblings != [
        "wikitext-103-raw-v1/train-00000-of-00002.parquet",
        "wikitext-103-raw-v1/train-00001-of-00002.parquet",
    ]:
        raise corpus.CorpusAcquisitionError(
            f"immutable train file set drifted: {siblings}"
        )
    source_dir.mkdir(parents=True, exist_ok=True)
    readme_cache = Path(
        hf_hub_download(
            repo_id=corpus.DATASET_ID,
            filename="README.md",
            revision=revision,
            repo_type="dataset",
        )
    )
    readme_bytes = readme_cache.read_bytes()
    upstream_readme = source_dir / "upstream_README.md"
    upstream_readme.write_bytes(readme_bytes)
    readme_hash = s2.sha256_bytes(readme_bytes)
    notice = corpus.license_notice(
        dataset_revision=revision,
        upstream_readme_sha256=readme_hash,
    )
    license_path = source_dir / "LICENSE.md"
    license_path.write_bytes(notice)
    files = []
    local_paths = []
    for sibling in siblings:
        local = Path(
            hf_hub_download(
                repo_id=corpus.DATASET_ID,
                filename=sibling,
                revision=revision,
                repo_type="dataset",
            )
        )
        local_paths.append(local)
        files.append(
            {
                "bytes": local.stat().st_size,
                "path": sibling,
                "sha256": s2.sha256_file(local),
            }
        )
    resolution = {
        "card_license_values": sorted(licenses),
        "configuration": corpus.DATASET_CONFIG,
        "dataset_id": corpus.DATASET_ID,
        "dataset_revision": revision,
        "expected_train_rows": corpus.EXPECTED_TRAIN_ROWS,
        "files": files,
        "huggingface_hub_version": importlib.metadata.version("huggingface_hub"),
        "license_notice": {
            "bytes": len(notice),
            "path": license_path.name,
            "sha256": s2.sha256_bytes(notice),
        },
        "resolved_at_utc": utc_now(),
        "split": corpus.DATASET_SPLIT,
        "tokenizer_modules_loaded_before_resolution": 0,
        "upstream_readme": {
            "bytes": len(readme_bytes),
            "path": upstream_readme.name,
            "sha256": readme_hash,
        },
    }
    corpus.write_canonical_json(source_dir / "source_resolution.json", resolution)
    corpus.assert_tokenizer_not_loaded()
    resolution["local_train_paths"] = [path.as_posix() for path in local_paths]
    return resolution


def seal_source_resolution(
    store: corpus.CreateOnlyBlobStore,
    source_dir: Path,
    *,
    source_commit: str,
    image_digest: str,
) -> dict[str, Any]:
    nonmanifest = [
        source_dir / "LICENSE.md",
        source_dir / "source_resolution.json",
        source_dir / "upstream_README.md",
    ]
    manifest = corpus.package_manifest(
        stage="S2-P1-source-resolution",
        files=nonmanifest,
        root=source_dir,
        protocol_sha256=EXPECTED_PROTOCOL_SHA256,
        source_commit=source_commit,
        image_digest=image_digest,
    )
    corpus.write_canonical_json(source_dir / "artifact_manifest.json", manifest)
    return store.upload_pack(
        subprefix="source-resolution",
        files=[*nonmanifest, source_dir / "artifact_manifest.json"],
        root=source_dir,
    )


def build_and_seal_protected_bank(
    store: corpus.CreateOnlyBlobStore,
    bank_dir: Path,
    *,
    source_commit: str,
    image_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contract = s2.load_and_validate_corpus_contract(PROJECT_ROOT)
    phase1_manifest = store.download_absolute(corpus.PHASE1_SOURCE_MANIFEST_OBJECT)
    review_object = str(
        contract["protected_prompt_bank"]["phase1_0d_blob"]["object"]
    )
    review_form = store.download_absolute(review_object)
    entries = list(corpus.repository_prompt_entries(PROJECT_ROOT, contract))
    entries.extend(
        corpus.phase1_blob_prompt_entries(
            phase1_manifest,
            review_form,
            selector_keys=contract["protected_prompt_bank"]["phase1_0d_blob"][
                "selectors"
            ],
        )
    )
    rows = corpus.prompt_bank_rows(entries)
    bank_dir.mkdir(parents=True, exist_ok=True)
    bank_path = bank_dir / "protected_prompt_bank.jsonl"
    corpus.write_canonical_jsonl(bank_path, rows)
    summary = {
        "deduplicated_prompt_count": len(rows),
        "exact_source_coordinate_count": sum(len(row["sources"]) for row in rows),
        "phase1_manifest_sha256": s2.sha256_bytes(phase1_manifest),
        "phase1_review_form_sha256": s2.sha256_bytes(review_form),
        "prompt_bank_bytes": bank_path.stat().st_size,
        "prompt_bank_sha256": s2.sha256_file(bank_path),
        "symmetric_rule": contract["protected_prompt_bank"]["rule"],
    }
    corpus.write_canonical_json(bank_dir / "protected_prompt_bank_summary.json", summary)
    nonmanifest = [
        bank_path,
        bank_dir / "protected_prompt_bank_summary.json",
    ]
    manifest = corpus.package_manifest(
        stage="S2-P1-protected-bank",
        files=nonmanifest,
        root=bank_dir,
        protocol_sha256=EXPECTED_PROTOCOL_SHA256,
        source_commit=source_commit,
        image_digest=image_digest,
    )
    corpus.write_canonical_json(bank_dir / "artifact_manifest.json", manifest)
    upload = store.upload_pack(
        subprefix="protected-bank",
        files=[*nonmanifest, bank_dir / "artifact_manifest.json"],
        root=bank_dir,
    )
    return rows, upload


def load_tokenizer(dataset_revision: str) -> tuple[Any, dict[str, Any]]:
    del dataset_revision
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        s2.MODEL_ID,
        revision=s2.MODEL_REVISION,
        trust_remote_code=False,
    )
    applied = False
    if (
        getattr(tokenizer, "bos_token_id", None) is not None
        and hasattr(tokenizer, "add_bos_token")
    ):
        tokenizer.add_bos_token = True
        applied = bool(tokenizer.add_bos_token)
    if not applied:
        raise corpus.CorpusAcquisitionError(
            "pinned adapter force_bos=true could not be applied"
        )
    resolved = (
        getattr(tokenizer, "_commit_hash", None)
        or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    )
    if resolved != s2.MODEL_REVISION:
        raise corpus.CorpusAcquisitionError(
            f"tokenizer revision {resolved!r} differs from pinned revision"
        )
    return tokenizer, {
        "add_bos_token": True,
        "bos_token_id": int(tokenizer.bos_token_id),
        "id": s2.MODEL_ID,
        "revision": resolved,
        "trust_remote_code": False,
    }


def load_exact_dataset(local_paths: list[str]) -> Any:
    from datasets import load_dataset

    dataset = load_dataset(
        "parquet",
        data_files={"train": local_paths},
        split="train",
    )
    if int(dataset.num_rows) != corpus.EXPECTED_TRAIN_ROWS:
        raise corpus.CorpusAcquisitionError(
            f"loaded dataset has {dataset.num_rows} rows"
        )
    if list(dataset.column_names) != ["text"]:
        raise corpus.CorpusAcquisitionError(
            f"loaded dataset columns drifted: {dataset.column_names}"
        )
    return dataset


def final_pack(
    *,
    output_dir: Path,
    source_dir: Path,
    bank_dir: Path,
    scan: dict[str, Any],
    resolution: dict[str, Any],
    tokenizer_receipt: dict[str, Any],
    source_commit: str,
    image_digest: str,
) -> tuple[Path, list[Path], dict[str, Any]]:
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    rows_path = final_dir / "corpus_rows.jsonl"
    corpus.write_canonical_jsonl(rows_path, scan["assigned_rows"])
    source_exclusion_path = Path(scan["exclusion_audit"]["path"])
    exclusion_path = final_dir / "exclusion_audit.jsonl"
    os.replace(source_exclusion_path, exclusion_path)
    bank_path = bank_dir / "protected_prompt_bank.jsonl"
    for source, destination in (
        (source_dir / "LICENSE.md", final_dir / "LICENSE.md"),
        (source_dir / "source_resolution.json", final_dir / "source_resolution.json"),
        (source_dir / "upstream_README.md", final_dir / "upstream_README.md"),
        (bank_path, final_dir / bank_path.name),
    ):
        shutil.copyfile(source, destination)
    license_file = {
        "attribution": "WikiText by Salesforce Research, derived from Wikipedia contributors",
        "bytes": (final_dir / "upstream_README.md").stat().st_size,
        "license_id": "cc-by-sa-3.0,gfdl",
        "path": "upstream_README.md",
        "sha256": s2.sha256_file(final_dir / "upstream_README.md"),
        "share_alike": True,
    }
    manifest, rows = corpus.build_corpus_manifest(
        dataset_revision=resolution["dataset_revision"],
        dataset_files=resolution["files"],
        license_file=license_file,
        rows_path=rows_path,
        exclusion_path=exclusion_path,
        protected_bank_path=final_dir / "protected_prompt_bank.jsonl",
        eligible_unique_rows=scan["eligible_unique_rows"],
        scanned_rows=scan["scanned_rows"],
    )
    corpus.write_canonical_json(final_dir / "corpus_manifest.json", manifest)
    exclusion_summary = {
        **scan["exclusion_audit"],
        "path": "exclusion_audit.jsonl",
    }
    corpus.write_canonical_json(
        final_dir / "exclusion_audit_summary.json",
        exclusion_summary,
    )
    execution_receipt = {
        "benchmark_model_operations": 0,
        "benchmark_tokenizer_operations": 0,
        "corpus_model_operations": 0,
        "dataset_revision": resolution["dataset_revision"],
        "eligible_unique_rows": scan["eligible_unique_rows"],
        "lens_operations": 0,
        "model_signals_inspected": False,
        "role_counts": dict(s2.ROLE_COUNTS),
        "scanned_rows": scan["scanned_rows"],
        "source_and_license_sealed_before_tokenizer": True,
        "tokenizer": tokenizer_receipt,
        "tokenizer_constructions": 1,
    }
    corpus.write_canonical_json(final_dir / "execution_receipt.json", execution_receipt)
    nonmanifest = [
        final_dir / "LICENSE.md",
        final_dir / "corpus_manifest.json",
        rows_path,
        exclusion_path,
        final_dir / "exclusion_audit_summary.json",
        final_dir / "execution_receipt.json",
        final_dir / "protected_prompt_bank.jsonl",
        final_dir / "source_resolution.json",
        final_dir / "upstream_README.md",
    ]
    manifest_document = corpus.package_manifest(
        stage="S2-P1-corpus-freeze",
        files=nonmanifest,
        root=final_dir,
        protocol_sha256=EXPECTED_PROTOCOL_SHA256,
        source_commit=source_commit,
        image_digest=image_digest,
    )
    corpus.write_canonical_json(final_dir / "artifact_manifest.json", manifest_document)
    return final_dir, [*nonmanifest, final_dir / "artifact_manifest.json"], {
        "corpus_manifest": manifest,
        "execution_receipt": execution_receipt,
        "rows": rows,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=os.getenv("RESULTS_DIR", "/workspace/runtime/results"),
    )
    parser.add_argument("--batch-size", type=int, default=256)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    environment = strict_environment()
    if s2.sha256_file(PROJECT_ROOT / "docs" / "jlens_s2_protocol.json") != (
        EXPECTED_PROTOCOL_SHA256
    ):
        raise corpus.CorpusAcquisitionError("frozen S2 protocol SHA-256 mismatch")
    if s2.sha256_file(
        PROJECT_ROOT / "docs" / "jlens_s2_corpus_source_contract.json"
    ) != EXPECTED_CORPUS_CONTRACT_SHA256:
        raise corpus.CorpusAcquisitionError("frozen corpus contract SHA-256 mismatch")
    if s2.sha256_file(
        PROJECT_ROOT / "docs" / "jlens_s2_artifacts.schema.json"
    ) != EXPECTED_ARTIFACT_SCHEMA_SHA256:
        raise corpus.CorpusAcquisitionError("frozen artifact schema SHA-256 mismatch")
    output_dir = Path(args.output_dir)
    source_dir = output_dir / "source-resolution"
    bank_dir = output_dir / "protected-bank"
    work_dir = output_dir / "work"
    for directory in (source_dir, bank_dir, work_dir):
        directory.mkdir(parents=True, exist_ok=True)
    store = corpus.CreateOnlyBlobStore(
        account=environment["account"],
        container=environment["container"],
        prefix=environment["prefix"],
        client_id=environment["client_id"],
    )
    resolution = resolve_dataset_source(source_dir)
    source_upload = seal_source_resolution(
        store,
        source_dir,
        source_commit=environment["source_commit"],
        image_digest=environment["image_digest"],
    )
    protected_rows, bank_upload = build_and_seal_protected_bank(
        store,
        bank_dir,
        source_commit=environment["source_commit"],
        image_digest=environment["image_digest"],
    )
    corpus.assert_tokenizer_not_loaded()
    tokenizer, tokenizer_receipt = load_tokenizer(resolution["dataset_revision"])
    dataset = load_exact_dataset(list(resolution.pop("local_train_paths")))
    scan = corpus.scan_and_assign(
        dataset,
        tokenizer=tokenizer,
        protected_bank=protected_rows,
        exclusion_path=work_dir / "exclusion_audit.jsonl",
        dataset_revision=resolution["dataset_revision"],
        batch_size=args.batch_size,
    )
    final_dir, files, pack = final_pack(
        output_dir=output_dir,
        source_dir=source_dir,
        bank_dir=bank_dir,
        scan=scan,
        resolution=resolution,
        tokenizer_receipt=tokenizer_receipt,
        source_commit=environment["source_commit"],
        image_digest=environment["image_digest"],
    )
    final_upload = store.upload_pack(
        subprefix="final",
        files=files,
        root=final_dir,
    )
    result = {
        "bank_upload_count": bank_upload["uploaded_count"],
        "corpus_manifest_sha256": s2.sha256_file(
            final_dir / "corpus_manifest.json"
        ),
        "dataset_revision": resolution["dataset_revision"],
        "eligible_unique_rows": scan["eligible_unique_rows"],
        "final_blob_prefix": f"{environment['prefix']}/final",
        "final_upload_count": final_upload["uploaded_count"],
        "model_operations": 0,
        "protected_prompt_count": len(protected_rows),
        "role_counts": dict(s2.ROLE_COUNTS),
        "rows_sha256": pack["corpus_manifest"]["rows"]["sha256"],
        "run_id": environment["run_id"],
        "source_upload_count": source_upload["uploaded_count"],
        "status": "S2-P1-CORPUS-SEALED",
        "tokenizer_constructions": 1,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
