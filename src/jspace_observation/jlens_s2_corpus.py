"""Deterministic WikiText acquisition and role-freeze helpers for S2."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import os
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jlens_s2_protocol as s2


DATASET_ID = "Salesforce/wikitext"
DATASET_CONFIG = "wikitext-103-raw-v1"
DATASET_SPLIT = "train"
EXPECTED_TRAIN_ROWS = 1_801_350
TRAIN_FILE_PREFIX = "wikitext-103-raw-v1/train-"
PHASE1_SOURCE_MANIFEST_OBJECT = (
    "phase1-headroom-confirmation/20260804T154518Z/artifact_manifest.json"
)
PHASE1_SOURCE_MANIFEST_SHA256 = (
    "76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536"
)
PHASE1_REVIEW_FORM_SHA256 = (
    "f808ce2148ee7c5a898c367783fd23584a368601daa5de944dbd9a4e21a801bc"
)


class CorpusAcquisitionError(RuntimeError):
    """Raised when corpus acquisition cannot satisfy the frozen contract."""


@dataclass
class CategoryAudit:
    count: int
    digest: Any

    @classmethod
    def create(cls) -> "CategoryAudit":
        return cls(count=0, digest=hashlib.sha256())

    def add(self, payload: bytes) -> None:
        self.count += 1
        self.digest.update(payload)

    def summary(self) -> dict[str, Any]:
        return {"count": self.count, "ordered_rows_sha256": self.digest.hexdigest()}


def _strict_json_line(raw: str, source: str) -> Any:
    try:
        return json.loads(
            raw,
            parse_constant=lambda value: (_ for _ in ()).throw(
                CorpusAcquisitionError(
                    f"{source}: non-finite JSON constant {value}"
                )
            ),
        )
    except json.JSONDecodeError as exc:
        raise CorpusAcquisitionError(f"{source}: invalid JSON: {exc}") from exc


def _selector_values(value: Any, selector: str) -> list[str]:
    parts = selector.split(".")
    current = [value]
    for part in parts:
        next_values = []
        wildcard = part.endswith("[*]")
        key = part[:-3] if wildcard else part
        for item in current:
            if not isinstance(item, Mapping) or key not in item:
                continue
            selected = item[key]
            if wildcard:
                if isinstance(selected, list):
                    next_values.extend(selected)
            else:
                next_values.append(selected)
        current = next_values
    return [item for item in current if isinstance(item, str) and item]


def _recursive_key_values(value: Any, keys: set[str]) -> Iterator[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in keys and isinstance(child, str) and child:
                yield key, child
            yield from _recursive_key_values(child, keys)
    elif isinstance(value, list):
        for child in value:
            yield from _recursive_key_values(child, keys)


def _repository_source_values(
    root: Path,
    source: Mapping[str, Any],
) -> Iterator[tuple[str, str]]:
    relative = str(source["path"])
    target = root / relative
    format_name = str(source["format"])
    selectors = [str(selector) for selector in source["selectors"]]
    if format_name == "jsonl":
        for line_number, raw in enumerate(
            target.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                continue
            document = _strict_json_line(raw, f"{relative}:{line_number}")
            for selector in selectors:
                for value_index, value in enumerate(
                    _selector_values(document, selector), start=1
                ):
                    yield f"{relative}:{line_number}:{selector}:{value_index}", value
        return
    if format_name == "json":
        document = s2.load_json(target)
        for selector in selectors:
            for value_index, value in enumerate(
                _selector_values(document, selector), start=1
            ):
                yield f"{relative}:{selector}:{value_index}", value
        return
    if format_name == "python_ast":
        if selectors != ["PromptItem.prompt_base keyword string literals"]:
            raise CorpusAcquisitionError(
                f"{relative}: unsupported Python selector contract"
            )
        tree = ast.parse(target.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            name = (
                function.id
                if isinstance(function, ast.Name)
                else function.attr
                if isinstance(function, ast.Attribute)
                else ""
            )
            if name != "PromptItem":
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "prompt_base"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                    and keyword.value.value
                ):
                    yield (
                        f"{relative}:{keyword.value.lineno}:PromptItem.prompt_base",
                        keyword.value.value,
                    )
        return
    raise CorpusAcquisitionError(f"{relative}: unsupported source format {format_name}")


def prompt_bank_rows(
    entries: Iterable[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    """Deduplicate exact prompt bytes while retaining all source coordinates."""

    by_bytes: dict[bytes, dict[str, Any]] = {}
    for role, coordinate, text in entries:
        if not role or not coordinate or not isinstance(text, str) or not text:
            raise CorpusAcquisitionError("prompt-bank entries must be complete")
        raw = text.encode("utf-8")
        row = by_bytes.setdefault(
            raw,
            {
                "prompt_id": "",
                "prompt_sha256": s2.sha256_bytes(raw),
                "prompt_text": text,
                "sources": [],
            },
        )
        row["sources"].append({"coordinate": coordinate, "role": role})
    rows = []
    for raw, row in by_bytes.items():
        row["sources"] = sorted(
            row["sources"],
            key=lambda source: (source["role"], source["coordinate"]),
        )
        identity = {
            "prompt_sha256": row["prompt_sha256"],
            "sources": row["sources"],
        }
        row["prompt_id"] = s2.sha256_bytes(s2.canonical_json_bytes(identity))
        rows.append(row)
    rows.sort(
        key=lambda row: (
            row["prompt_sha256"],
            row["prompt_text"].encode("utf-8"),
        )
    )
    if len({row["prompt_id"] for row in rows}) != len(rows):
        raise CorpusAcquisitionError("prompt-bank IDs are not unique")
    return rows


def repository_prompt_entries(
    root: Path,
    contract: Mapping[str, Any],
) -> Iterator[tuple[str, str, str]]:
    bank = contract["protected_prompt_bank"]
    for source in bank["repository_sources"]:
        role = str(source["role"])
        for coordinate, text in _repository_source_values(root, source):
            yield role, coordinate, text


def phase1_blob_prompt_entries(
    manifest_bytes: bytes,
    review_form_bytes: bytes,
    *,
    selector_keys: Sequence[str],
    expected_manifest_sha256: str = PHASE1_SOURCE_MANIFEST_SHA256,
    expected_review_form_sha256: str = PHASE1_REVIEW_FORM_SHA256,
) -> Iterator[tuple[str, str, str]]:
    if (
        not selector_keys
        or any(not isinstance(key, str) or not key for key in selector_keys)
    ):
        raise CorpusAcquisitionError("Phase 1.0D selectors must be nonempty strings")
    if s2.sha256_bytes(manifest_bytes) != expected_manifest_sha256:
        raise CorpusAcquisitionError("Phase 1.0D source manifest SHA-256 mismatch")
    manifest = _strict_json_line(
        manifest_bytes.decode("utf-8"),
        PHASE1_SOURCE_MANIFEST_OBJECT,
    )
    files = manifest.get("files") if isinstance(manifest, Mapping) else None
    expected = {
        str(row.get("name")): str(row.get("sha256"))
        for row in files or []
        if isinstance(row, Mapping)
    }
    if expected.get("03_review_form.jsonl") != expected_review_form_sha256:
        raise CorpusAcquisitionError("Phase 1.0D review-form manifest binding drifted")
    if s2.sha256_bytes(review_form_bytes) != expected_review_form_sha256:
        raise CorpusAcquisitionError("Phase 1.0D review-form SHA-256 mismatch")
    found = 0
    for line_number, raw in enumerate(
        review_form_bytes.decode("utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        document = _strict_json_line(raw, f"Phase1.0D:{line_number}")
        for key, value in _recursive_key_values(document, set(selector_keys)):
            found += 1
            yield (
                "sealed Phase 1.0D prompt bank",
                f"{PHASE1_SOURCE_MANIFEST_OBJECT}:03_review_form.jsonl:"
                f"{line_number}:{key}",
                value,
            )
    if found == 0:
        raise CorpusAcquisitionError("Phase 1.0D review form exposed no prompt strings")


def bank_for_overlap(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "prompt_bytes": str(row["prompt_text"]).encode("utf-8"),
            "prompt_id": str(row["prompt_id"]),
        }
        for row in rows
    ]


def license_notice(
    *,
    dataset_revision: str,
    upstream_readme_sha256: str,
) -> bytes:
    text = f"""# WikiText corpus license and attribution

The files in this directory that contain WikiText source text are derived
from `Salesforce/wikitext`, configuration `wikitext-103-raw-v1`, immutable
dataset revision `{dataset_revision}`.

The dataset repository identifies the material with both `cc-by-sa-3.0` and
`gfdl` license tags and describes it as extracted from verified Good and
Featured Wikipedia articles. The exact upstream dataset-card bytes are
retained as `upstream_README.md` with SHA-256
`{upstream_readme_sha256}`.

Attribution: WikiText by Salesforce Research, derived from Wikipedia
contributors. The source text and derived corpus rows remain subject to the upstream
Creative Commons Attribution-ShareAlike 3.0 and GNU Free Documentation License
terms; they are not relicensed under the repository's code license.
Preserve this notice and the upstream dataset card when
redistributing these corpus files.

References:

- https://creativecommons.org/licenses/by-sa/3.0/
- https://www.gnu.org/licenses/fdl-1.3.html
- https://huggingface.co/datasets/Salesforce/wikitext
"""
    return text.encode("utf-8")


def library_versions(names: Sequence[str]) -> list[dict[str, str]]:
    rows = []
    for name in sorted(names):
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise CorpusAcquisitionError(f"required package is missing: {name}") from exc
        rows.append({"name": name, "version": version})
    return rows


def _audit_row(
    *,
    row_id: str,
    raw_text_sha256: str,
    category: str,
    detail_ids: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "category": category,
        "detail_ids": sorted(set(detail_ids)),
        "raw_text_sha256": raw_text_sha256,
        "row_id": row_id,
    }


def _write_audit(
    handle: Any,
    category_audits: Mapping[str, CategoryAudit],
    row: Mapping[str, Any],
) -> None:
    payload = s2.canonical_jsonl_bytes([row])
    handle.write(payload)
    category = str(row["category"])
    audit = category_audits.get(category)
    if audit is None:
        raise CorpusAcquisitionError(f"unregistered exclusion category: {category}")
    audit.add(payload)


def scan_and_assign(
    dataset: Iterable[Mapping[str, Any]],
    *,
    tokenizer: Any,
    protected_bank: Sequence[Mapping[str, Any]],
    exclusion_path: Path,
    dataset_revision: str,
    expected_rows: int = EXPECTED_TRAIN_ROWS,
    batch_size: int = 256,
) -> dict[str, Any]:
    """Scan every immutable source row without any model-dependent signal."""

    if not s2._IMMUTABLE_REF.fullmatch(dataset_revision):
        raise CorpusAcquisitionError("dataset revision must be a 40-hex commit")
    if batch_size <= 0:
        raise CorpusAcquisitionError("tokenizer batch size must be positive")
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    categories = {
        category: CategoryAudit.create()
        for category in (
            "short_raw_text",
            "protected_prompt_overlap",
            "under_128_tokens",
            "duplicate_128_token_ids",
            "eligible_unassigned_after_first_1402",
        )
    }
    overlap_bank = bank_for_overlap(protected_bank)
    eligible: list[dict[str, Any]] = []
    seen_token_hash: dict[str, str] = {}
    pending: list[tuple[str, str, str]] = []
    scanned_rows = 0

    with exclusion_path.open("wb") as audit_handle:

        def process_pending() -> None:
            if not pending:
                return
            texts = [text for _row_id, text, _raw_hash in pending]
            encoded = tokenizer(
                texts,
                add_special_tokens=True,
                return_attention_mask=False,
                truncation=False,
            )
            input_ids = (
                encoded["input_ids"]
                if isinstance(encoded, Mapping)
                else encoded.input_ids
            )
            if len(input_ids) != len(pending):
                raise CorpusAcquisitionError("tokenizer batch cardinality changed")
            for (row_id, text, raw_hash), ids in zip(
                pending, input_ids, strict=True
            ):
                ids = [int(token_id) for token_id in ids]
                if len(ids) < s2.MAX_SEQ_LEN:
                    _write_audit(
                        audit_handle,
                        categories,
                        _audit_row(
                            row_id=row_id,
                            raw_text_sha256=raw_hash,
                            category="under_128_tokens",
                        ),
                    )
                    continue
                sequence = ids[: s2.MAX_SEQ_LEN]
                token_hash = s2.sha256_bytes(s2.token_ids_bytes(sequence))
                if token_hash in seen_token_hash:
                    _write_audit(
                        audit_handle,
                        categories,
                        _audit_row(
                            row_id=row_id,
                            raw_text_sha256=raw_hash,
                            category="duplicate_128_token_ids",
                            detail_ids=[seen_token_hash[token_hash]],
                        ),
                    )
                    continue
                seen_token_hash[token_hash] = row_id
                eligible.append(
                    {
                        "dataset_revision": dataset_revision,
                        "raw_text": text,
                        "raw_text_sha256": raw_hash,
                        "row_id": row_id,
                        "token_count_untruncated": len(ids),
                        "token_ids": sequence,
                        "token_ids_sha256": token_hash,
                    }
                )
            pending.clear()

        for index, source_row in enumerate(dataset):
            scanned_rows += 1
            row_id = f"train:{index}"
            if not isinstance(source_row, Mapping) or set(source_row) != {"text"}:
                raise CorpusAcquisitionError(
                    f"{row_id}: source row must contain only text"
                )
            text = source_row["text"]
            if not isinstance(text, str):
                raise CorpusAcquisitionError(f"{row_id}: source text is not a string")
            raw_hash = s2.sha256_bytes(text.encode("utf-8"))
            if len(text.strip()) < 600:
                _write_audit(
                    audit_handle,
                    categories,
                    _audit_row(
                        row_id=row_id,
                        raw_text_sha256=raw_hash,
                        category="short_raw_text",
                    ),
                )
                continue
            matches = s2.overlap_matches(text.encode("utf-8"), overlap_bank)
            if matches:
                _write_audit(
                    audit_handle,
                    categories,
                    _audit_row(
                        row_id=row_id,
                        raw_text_sha256=raw_hash,
                        category="protected_prompt_overlap",
                        detail_ids=matches,
                    ),
                )
                continue
            pending.append((row_id, text, raw_hash))
            if len(pending) >= batch_size:
                process_pending()
        process_pending()

        if scanned_rows != expected_rows:
            raise CorpusAcquisitionError(
                f"dataset row count {scanned_rows} differs from {expected_rows}"
            )
        assigned = s2.assign_roles(eligible)
        selected_ids = {str(row["row_id"]) for row in assigned}
        for row in eligible:
            if row["row_id"] not in selected_ids:
                _write_audit(
                    audit_handle,
                    categories,
                    _audit_row(
                        row_id=str(row["row_id"]),
                        raw_text_sha256=str(row["raw_text_sha256"]),
                        category="eligible_unassigned_after_first_1402",
                    ),
                )

    exclusion_bytes = exclusion_path.stat().st_size
    exclusion_sha256 = s2.sha256_file(exclusion_path)
    category_summary = {
        category: audit.summary() for category, audit in sorted(categories.items())
    }
    excluded_count = sum(audit.count for audit in categories.values())
    if excluded_count + len(assigned) != scanned_rows:
        raise CorpusAcquisitionError(
            "selection accounting does not partition the exact dataset rows"
        )
    return {
        "assigned_rows": assigned,
        "eligible_unique_rows": len(eligible),
        "exclusion_audit": {
            "bytes": exclusion_bytes,
            "category_summary": category_summary,
            "excluded_rows": excluded_count,
            "path": exclusion_path.as_posix(),
            "sha256": exclusion_sha256,
        },
        "scanned_rows": scanned_rows,
    }


def build_corpus_manifest(
    *,
    dataset_revision: str,
    dataset_files: Sequence[Mapping[str, Any]],
    license_file: Mapping[str, Any],
    rows_path: Path,
    exclusion_path: Path,
    protected_bank_path: Path,
    eligible_unique_rows: int,
    scanned_rows: int,
    versions: Sequence[Mapping[str, str]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []
    for line_number, raw in enumerate(
        rows_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if raw.strip():
            row = _strict_json_line(raw, f"{rows_path}:{line_number}")
            if not isinstance(row, dict):
                raise CorpusAcquisitionError("corpus row is not an object")
            rows.append(row)
    manifest = {
        "dataset": {
            "configuration": DATASET_CONFIG,
            "files": [dict(row) for row in dataset_files],
            "id": DATASET_ID,
            "license": dict(license_file),
            "revision": dataset_revision,
            "split": DATASET_SPLIT,
        },
        "exclusion_audit": {
            "bytes": exclusion_path.stat().st_size,
            "path": exclusion_path.name,
            "sha256": s2.sha256_file(exclusion_path),
        },
        "library_versions": (
            [dict(row) for row in versions]
            if versions is not None
            else library_versions(
                (
                    "datasets",
                    "huggingface_hub",
                    "pyarrow",
                    "tokenizers",
                    "transformers",
                )
            )
        ),
        "protected_prompt_bank": {
            "bytes": protected_bank_path.stat().st_size,
            "path": protected_bank_path.name,
            "sha256": s2.sha256_file(protected_bank_path),
        },
        "role_counts": dict(s2.ROLE_COUNTS),
        "rows": {
            "bytes": rows_path.stat().st_size,
            "path": rows_path.name,
            "sha256": s2.sha256_file(rows_path),
        },
        "schema_version": s2.CORPUS_MANIFEST_VERSION,
        "selection": {
            "assignment_seed": s2.ASSIGNMENT_SEED,
            "eligible_unique_rows": eligible_unique_rows,
            "model_signals_inspected": False,
            "role_key_rule": (
                "SHA-256(UTF8(seed)||NUL||UTF8(row_id)||NUL||"
                "ASCII(raw_text_sha256)||NUL||ASCII(token_ids_sha256))"
            ),
            "scanned_rows": scanned_rows,
        },
        "tokenizer": {
            "force_bos": True,
            "id": s2.MODEL_ID,
            "revision": s2.MODEL_REVISION,
            "trust_remote_code": False,
        },
    }
    s2.validate_corpus_manifest(manifest, rows)
    return manifest, rows


def write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(s2.canonical_json_bytes(value))


def write_canonical_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(s2.canonical_jsonl_bytes(rows))


class CreateOnlyBlobStore:
    """Managed-identity create-only Blob persistence with exact readback."""

    def __init__(
        self,
        *,
        account: str,
        container: str,
        prefix: str,
        client_id: str | None,
        container_client: Any = None,
    ) -> None:
        if not account or not container or not prefix.strip("/"):
            raise CorpusAcquisitionError("Blob account/container/prefix are required")
        forbidden = sorted(
            name
            for name in (
                "AZURE_STORAGE_CONNECTION_STRING",
                "AZURE_STORAGE_KEY",
                "AZURE_STORAGE_SAS_TOKEN",
                "AZURE_STORAGE_ACCOUNT_KEY",
                "JSPACE_BLOB_ACCOUNT_KEY",
                "JSPACE_BLOB_SAS",
            )
            if os.getenv(name)
        )
        if forbidden:
            raise CorpusAcquisitionError(
                "managed identity is required; forbidden Blob secret environment: "
                + ", ".join(forbidden)
            )
        self.account = account
        self.container = container
        self.prefix = prefix.strip("/")
        if container_client is None:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient

            credential = DefaultAzureCredential(
                managed_identity_client_id=client_id or None
            )
            service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=credential,
            )
            container_client = service.get_container_client(container)
        self.client = container_client

    def name(self, relative: str) -> str:
        clean = relative.strip("/")
        if not clean or ".." in clean.split("/"):
            raise CorpusAcquisitionError("invalid Blob relative path")
        return f"{self.prefix}/{clean}"

    def download(self, relative: str) -> bytes:
        return self.client.download_blob(self.name(relative)).readall()

    def download_absolute(self, blob_name: str) -> bytes:
        clean = blob_name.strip("/")
        if not clean or ".." in clean.split("/"):
            raise CorpusAcquisitionError("invalid absolute Blob name")
        return self.client.download_blob(clean).readall()

    def upload_bytes(self, relative: str, payload: bytes) -> dict[str, Any]:
        name = self.name(relative)
        self.client.upload_blob(name=name, data=payload, overwrite=False)
        observed = self.client.download_blob(name).readall()
        if observed != payload:
            raise CorpusAcquisitionError(f"Blob readback mismatch: {name}")
        return {
            "blob": name,
            "bytes": len(payload),
            "sha256": s2.sha256_bytes(payload),
        }

    def upload_file(self, relative: str, path: Path) -> dict[str, Any]:
        name = self.name(relative)
        with path.open("rb") as handle:
            self.client.upload_blob(name=name, data=handle, overwrite=False)
        digest = hashlib.sha256()
        size = 0
        downloader = self.client.download_blob(name)
        for chunk in downloader.chunks():
            digest.update(chunk)
            size += len(chunk)
        if size != path.stat().st_size or digest.hexdigest() != s2.sha256_file(path):
            raise CorpusAcquisitionError(f"Blob file readback mismatch: {name}")
        return {"blob": name, "bytes": size, "sha256": digest.hexdigest()}

    def upload_pack(
        self,
        *,
        subprefix: str,
        files: Sequence[Path],
        root: Path,
        manifest_name: str = "artifact_manifest.json",
    ) -> dict[str, Any]:
        relative_paths = [path.relative_to(root).as_posix() for path in files]
        if manifest_name not in relative_paths:
            raise CorpusAcquisitionError("pack artifact manifest is missing")
        order = s2.manifest_last_order(relative_paths, manifest_name=manifest_name)
        uploaded = []
        by_relative = {path.relative_to(root).as_posix(): path for path in files}
        for index, relative in enumerate(order, start=1):
            record = self.upload_file(
                f"{subprefix.strip('/')}/{relative}",
                by_relative[relative],
            )
            record["written_order"] = index
            uploaded.append(record)
        if not uploaded[-1]["blob"].endswith(f"/{manifest_name}"):
            raise CorpusAcquisitionError("artifact manifest was not uploaded last")
        return {
            "manifest_written_last": True,
            "uploaded": uploaded,
            "uploaded_count": len(uploaded),
        }


def package_manifest(
    *,
    stage: str,
    files: Sequence[Path],
    root: Path,
    protocol_sha256: str,
    source_commit: str,
    image_digest: str,
) -> dict[str, Any]:
    ordered = sorted(
        files,
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return {
        "complete": True,
        "create_only": True,
        "files": [
            {
                "bytes": path.stat().st_size,
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": s2.sha256_file(path),
                "written_order": index,
            }
            for index, path in enumerate(ordered, start=1)
        ],
        "image_digest": image_digest,
        "manifest_written_last": True,
        "protocol_sha256": protocol_sha256,
        "schema_version": "jlens-s2-corpus-package-manifest/v1",
        "source_commit": source_commit,
        "stage": stage,
    }


def assert_tokenizer_not_loaded() -> None:
    loaded = sorted(
        name
        for name in sys.modules
        if name == "transformers"
        or name.startswith("transformers.")
        or name == "tokenizers"
        or name.startswith("tokenizers.")
    )
    if loaded:
        raise CorpusAcquisitionError(
            "tokenizer libraries loaded before source/license seal: "
            + ", ".join(loaded[:10])
        )


__all__ = [
    "CorpusAcquisitionError",
    "CreateOnlyBlobStore",
    "DATASET_CONFIG",
    "DATASET_ID",
    "DATASET_SPLIT",
    "EXPECTED_TRAIN_ROWS",
    "PHASE1_REVIEW_FORM_SHA256",
    "PHASE1_SOURCE_MANIFEST_OBJECT",
    "PHASE1_SOURCE_MANIFEST_SHA256",
    "TRAIN_FILE_PREFIX",
    "assert_tokenizer_not_loaded",
    "bank_for_overlap",
    "build_corpus_manifest",
    "license_notice",
    "package_manifest",
    "phase1_blob_prompt_entries",
    "prompt_bank_rows",
    "repository_prompt_entries",
    "scan_and_assign",
    "write_canonical_json",
    "write_canonical_jsonl",
]
