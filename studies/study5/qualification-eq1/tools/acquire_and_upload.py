#!/usr/bin/env python3
"""Acquire, byte-verify and content-address the Study 5-EQ1 model bytes.

This runs **on the Mooncake GPU host**. It uses only the Python standard
library, because the host has no ``az`` and no ``azcopy``.

Gate Q-2 requires every acquired file to be hashed on the execution host,
matched against its authoritative value *before use*, content-addressed into
``models/sha256/<aa>/<full>``, and round-trip re-hashed after upload. Authority
2.7 additionally requires every upload to be create-only under ``If-None-Match:
*``, with a precondition failure treated as a stop rather than a retry.

Three design points follow directly from those rules and are worth stating,
because each is somewhere a careless implementation goes wrong:

**The mirror is never trusted.** The GPU host cannot reach the HuggingFace
origin, so bytes arrive through a mirror. A mirror is only safe if its bytes are
checked against an authority computed elsewhere, so a hash mismatch aborts that
file immediately and the bytes are discarded rather than uploaded.

**A pre-existing content-addressed blob is not a precondition failure.** The
blob name *is* its SHA-256, so an existing blob at the same path already holds
the same content. The tool checks with a HEAD first and, if the blob exists,
verifies it by re-reading and re-hashing rather than issuing a PUT at all. That
respects 2.7 without inventing an overwrite and without tripping 12.6 over a
benign deduplication.

**No SAS, no storage key.** Every data-plane call is authenticated with a bearer
token from the VM's system-assigned managed identity, as 2.8 and 2.9 require.

The tool is idempotent and resumable: a file already on disk with the right hash
is not downloaded again, and a blob already present and verified is not
uploaded again.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F"
)
BLOB_API_VERSION = "2021-12-02"
CONTAINER = "models"
# Azure caps a single Put Blob at 256 MiB; anything larger must be staged as
# blocks. 64 MiB blocks match what the predecessor study used.
BLOCK_SIZE = 64 * 1024 * 1024
SINGLE_PUT_CEILING = 200 * 1024 * 1024
CHUNK = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


class AcquisitionError(RuntimeError):
    """A condition that must stop the file, not be retried around."""


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------


class ManagedIdentity:
    """Bearer tokens from the VM's system-assigned managed identity."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def token(self) -> str:
        if self._token and time.time() < self._expires_at - 300:
            return self._token
        req = urllib.request.Request(IMDS_TOKEN_URL, headers={"Metadata": "true"})
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = json.load(response)
        self._token = str(payload["access_token"])
        self._expires_at = float(payload.get("expires_on") or (time.time() + 3000))
        return self._token


# --------------------------------------------------------------------------
# blob data plane
# --------------------------------------------------------------------------


class BlobClient:
    def __init__(self, account: str, identity: ManagedIdentity) -> None:
        self.endpoint = f"https://{account}.blob.core.chinacloudapi.cn"
        self.identity = identity

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.identity.token()}",
            "x-ms-version": BLOB_API_VERSION,
            "x-ms-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        extra: dict[str, str] | None = None,
        timeout: int = 900,
    ) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(
            url, data=data, headers=self._headers(extra), method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers or {}), exc.read()

    def blob_url(self, name: str) -> str:
        return f"{self.endpoint}/{CONTAINER}/{name}"

    def exists(self, name: str) -> tuple[bool, int | None]:
        status, headers, _ = self._request("HEAD", self.blob_url(name), timeout=120)
        if status == 200:
            return True, int(headers.get("Content-Length") or 0)
        if status == 404:
            return False, None
        raise AcquisitionError(f"HEAD {name} returned unexpected status {status}")

    def download_sha256(self, name: str) -> tuple[str, int]:
        req = urllib.request.Request(
            self.blob_url(name), headers=self._headers(), method="GET"
        )
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(req, timeout=3600) as response:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
        return digest.hexdigest(), total

    def put_small(self, name: str, payload: bytes) -> None:
        """Create-only single-shot upload."""

        status, _, body = self._request(
            "PUT",
            self.blob_url(name),
            data=payload,
            extra={
                "x-ms-blob-type": "BlockBlob",
                "Content-Length": str(len(payload)),
                "If-None-Match": "*",
            },
        )
        if status in (201, 202):
            return
        if status in (409, 412):
            raise AcquisitionError(
                f"create-only precondition failure on {name} (HTTP {status}); "
                "authority 12.6 makes this a stop, never a retry with overwrite"
            )
        raise AcquisitionError(f"PUT {name} failed with {status}: {body[:300]!r}")

    def put_blocks(self, name: str, path: Path, size: int) -> int:
        """Create-only staged block upload for a large file."""

        block_ids: list[str] = []
        with open(path, "rb") as handle:
            index = 0
            while True:
                block = handle.read(BLOCK_SIZE)
                if not block:
                    break
                # Every block id must decode to the same byte length, so a
                # fixed-width ordinal is used rather than the raw index.
                block_id = base64.b64encode(
                    f"{index:08d}".encode("ascii")
                ).decode("ascii")
                url = f"{self.blob_url(name)}?comp=block&blockid={urllib.parse.quote(block_id)}"
                status, _, body = self._request(
                    "PUT",
                    url,
                    data=block,
                    extra={"Content-Length": str(len(block))},
                )
                if status not in (201, 202):
                    raise AcquisitionError(
                        f"stage block {index} of {name} failed with {status}: {body[:200]!r}"
                    )
                block_ids.append(block_id)
                index += 1

        body_xml = (
            '<?xml version="1.0" encoding="utf-8"?><BlockList>'
            + "".join(f"<Latest>{b}</Latest>" for b in block_ids)
            + "</BlockList>"
        ).encode("utf-8")
        status, _, resp = self._request(
            "PUT",
            f"{self.blob_url(name)}?comp=blocklist",
            data=body_xml,
            extra={
                "Content-Length": str(len(body_xml)),
                "Content-Type": "application/xml",
                "If-None-Match": "*",
            },
        )
        if status in (409, 412):
            raise AcquisitionError(
                f"create-only precondition failure committing {name} (HTTP {status}); "
                "authority 12.6 makes this a stop"
            )
        if status not in (201, 202):
            raise AcquisitionError(
                f"commit block list for {name} failed with {status}: {resp[:300]!r}"
            )
        return len(block_ids)


# --------------------------------------------------------------------------
# acquisition
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def git_blob_sha1(path: Path, size: int) -> str:
    """Recompute git's blob object id: SHA-1 over b"blob <len>\\0" + content.

    Non-LFS files on the origin publish only this id, so it is the only
    origin-anchored authority available for them. It is deliberately kept
    distinct from the content SHA-256 used for addressing.
    """

    digest = hashlib.sha1()
    digest.update(f"blob {size}\0".encode("ascii"))
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_against_authority(
    path: Path, entry: dict[str, Any], size: int
) -> dict[str, Any]:
    """Check mirrored bytes against whichever authority the origin published.

    An LFS file is checked against the origin's content SHA-256 directly. A
    non-LFS file is checked by recomputing git's blob id, because that is the
    only integrity value the origin publishes for it. Either way the content
    SHA-256 is also computed, because that is what the blob is addressed by.
    """

    computed_sha256, actual_size = sha256_file(path)
    kind = entry.get("authority_kind")
    result: dict[str, Any] = {
        "authority_kind": kind,
        "computed_sha256": computed_sha256,
        "computed_size_bytes": actual_size,
    }

    if kind == "lfs_sha256":
        expected = entry["authoritative_sha256"]
        result["authoritative_sha256"] = expected
        result["authority_matches"] = computed_sha256 == expected
        result["authority_detail"] = (
            f"content sha256 {computed_sha256} vs origin LFS oid {expected}"
        )
    elif kind == "git_blob_sha1":
        expected = entry["authoritative_git_blob_sha1"]
        computed_blob = git_blob_sha1(path, actual_size)
        result["authoritative_git_blob_sha1"] = expected
        result["computed_git_blob_sha1"] = computed_blob
        result["authority_matches"] = computed_blob == expected
        result["authority_detail"] = (
            f"git blob sha1 {computed_blob} vs origin oid {expected}"
        )
    else:
        result["authority_matches"] = False
        result["authority_detail"] = "no origin-published authority for this file"

    if size and actual_size != size:
        result["authority_matches"] = False
        result["size_mismatch"] = f"{actual_size} on disk vs {size} in manifest"
    return result


def download(url: str, dest: Path, expected_bytes: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq1-acquire"})
    with urllib.request.urlopen(req, timeout=3600) as response, open(
        partial, "wb"
    ) as handle:
        written = 0
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
    if expected_bytes and written != expected_bytes:
        partial.unlink(missing_ok=True)
        raise AcquisitionError(
            f"short read: got {written} bytes, manifest says {expected_bytes}"
        )
    partial.replace(dest)


def content_address(sha: str) -> str:
    return f"sha256/{sha[:2]}/{sha}"


def process_file(
    blob: BlobClient,
    repo: str,
    revision: str,
    entry: dict[str, Any],
    staging: Path,
    mirror: str,
    dry_run: bool,
) -> dict[str, Any]:
    path = entry["path"]
    size = int(entry["size_bytes"])
    started = utc_now()

    record: dict[str, Any] = {
        "repo": repo,
        "revision": revision,
        "path": path,
        "size_bytes": size,
        "authority_kind": entry.get("authority_kind"),
        "authoritative_sha256": entry.get("authoritative_sha256"),
        "authoritative_git_blob_sha1": entry.get("authoritative_git_blob_sha1"),
        "ts_start_utc": started,
    }

    local = staging / repo.replace("/", "__") / path
    verification: dict[str, Any] | None = None

    if local.exists():
        verification = verify_against_authority(local, entry, size)
        if not verification["authority_matches"]:
            record["stale_local_discarded"] = True
            local.unlink()
            verification = None
        else:
            record["reused_local_bytes"] = True

    if verification is None:
        if dry_run:
            record["dry_run"] = True
            record["ts_end_utc"] = utc_now()
            return record
        url = f"{mirror}/{repo}/resolve/{revision}/{urllib.parse.quote(path)}"
        download(url, local, size)
        verification = verify_against_authority(local, entry, size)

    record.update(verification)
    record["hash_matches_authority"] = bool(verification["authority_matches"])

    if not verification["authority_matches"]:
        local.unlink(missing_ok=True)
        record["status"] = "AUTHORITY_MISMATCH"
        record["ts_end_utc"] = utc_now()
        raise AcquisitionError(
            f"{repo}/{path}: mirrored bytes fail the origin authority "
            f"({verification['authority_detail']}); bytes discarded, not uploaded"
        )

    actual = verification["computed_sha256"]
    actual_size = verification["computed_size_bytes"]
    name = content_address(actual)
    record["blob_path"] = f"{CONTAINER}/{name}"

    present, present_size = blob.exists(name)
    if present:
        record["blob_pre_existing"] = True
        record["blob_pre_existing_size"] = present_size
        record["uploaded"] = False
        if present_size == actual_size:
            round_trip, _ = blob.download_sha256(name)
            record["round_trip_sha256"] = round_trip
            record["round_trip_matches"] = round_trip == actual
            if round_trip != actual:
                raise AcquisitionError(
                    f"{name} already exists but its bytes hash {round_trip}, "
                    f"not {actual}; not overwritten, stopping"
                )
            record["status"] = "already_present_verified"
        else:
            raise AcquisitionError(
                f"{name} already exists with size {present_size}, expected "
                f"{actual_size}; not overwritten, stopping"
            )
    else:
        record["blob_pre_existing"] = False
        if size > SINGLE_PUT_CEILING:
            blocks = blob.put_blocks(name, local, actual_size)
            record["upload_mode"] = "staged_blocks"
            record["blocks"] = blocks
        else:
            blob.put_small(name, local.read_bytes())
            record["upload_mode"] = "single_put"
        record["uploaded"] = True
        round_trip, round_trip_size = blob.download_sha256(name)
        record["round_trip_sha256"] = round_trip
        record["round_trip_size_bytes"] = round_trip_size
        record["round_trip_matches"] = round_trip == actual
        if round_trip != actual:
            raise AcquisitionError(
                f"round-trip verification failed for {name}: {round_trip} != {actual}"
            )
        record["status"] = "uploaded_verified"

    record["ts_end_utc"] = utc_now()
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--mirror", default="https://hf-mirror.com")
    parser.add_argument("--report", required=True)
    parser.add_argument("--roles", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    staging = Path(args.staging)
    blob = BlobClient(args.account, ManagedIdentity())

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    started = utc_now()

    for target in manifest["targets"]:
        if args.roles and target["role"] not in args.roles:
            continue
        log(f"=== {target['role']}  {target['repo']}  {target['file_count']} files")
        for entry in target["files"]:
            try:
                record = process_file(
                    blob,
                    target["repo"],
                    target["revision"],
                    entry,
                    staging,
                    args.mirror,
                    args.dry_run,
                )
                results.append(record)
                log(
                    f"  {record.get('status', 'dry_run'):<26} "
                    f"{record['size_bytes']:>14,}  {entry['path']}"
                )
            except (AcquisitionError, urllib.error.URLError, OSError) as exc:
                failures.append(f"{target['repo']}/{entry['path']}: {exc}")
                results.append(
                    {
                        "repo": target["repo"],
                        "path": entry["path"],
                        "status": "FAILED",
                        "error": str(exc)[:500],
                        "ts_end_utc": utc_now(),
                    }
                )
                log(f"  FAILED                     {entry['path']}: {exc}")

    uploaded = [r for r in results if r.get("uploaded")]
    report = {
        "schema_version": "study5-eq1-acquisition-report-v1",
        "ts_start_utc": started,
        "ts_end_utc": utc_now(),
        "manifest_sha256": hashlib.sha256(
            Path(args.manifest).read_bytes()
        ).hexdigest(),
        "mirror": args.mirror,
        "origin_reachable_from_this_host": False,
        "auth": "system-assigned managed identity bearer token",
        "sas_tokens_issued": 0,
        "storage_keys_used": 0,
        "existing_blobs_overwritten": 0,
        "containers_created": 0,
        "files_processed": len(results),
        "files_uploaded": len(uploaded),
        "files_already_present_verified": len(
            [r for r in results if r.get("status") == "already_present_verified"]
        ),
        "files_failed": len(failures),
        "bytes_uploaded": sum(int(r.get("size_bytes") or 0) for r in uploaded),
        "all_hashes_match_authority": all(
            r.get("hash_matches_authority", False)
            for r in results
            if r.get("status") != "FAILED"
        ),
        "all_round_trips_verified": all(
            r.get("round_trip_matches", False)
            for r in results
            if r.get("status") in ("uploaded_verified", "already_present_verified")
        ),
        "failures": failures,
        "files": results,
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    log(
        f"report written: processed={len(results)} uploaded={len(uploaded)} "
        f"failed={len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
