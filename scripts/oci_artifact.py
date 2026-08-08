#!/usr/bin/env python
"""Move a directory of artifacts through an Azure Container Registry as an OCI
artifact, using only the standard library.

Both storage accounts in this subscription are private-endpoint-only, so the
registry is the one transport reachable from an Azure Container Apps job, from an
ACR task, and from the operator workstation alike.  This module implements the
minimum of the OCI distribution spec needed for that round trip: an authenticated
blob upload, a manifest write, and the inverse reads.

Nothing here is scientific.  The payload is an opaque tarball whose SHA-256 is
printed on push and re-checked on pull, so a corrupted transfer cannot be
mistaken for a result.  Every artifact retrieved this way is additionally checked
against hashes registered in the stage receipt before it is admitted.

Authentication is attempted in this order:

1. ``--acr-refresh-token`` or ``ACR_REFRESH_TOKEN`` (the operator path: obtained
   with ``az acr login --expose-token``);
2. the container's managed identity, exchanged for an ACR refresh token (the
   in-Azure path);
3. ``ACR_ACCESS_TOKEN``, already scoped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "jspace-study2-oci-artifact/1"
ARTIFACT_TYPE = "application/vnd.jspace.study2.artifact.v1+tar"
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
CONFIG_TYPE = "application/vnd.oci.empty.v1+json"
LAYER_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"
ACCEPT = ", ".join(
    (
        MANIFEST_TYPE,
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.oci.image.index.v1+json",
    )
)


class TransportError(RuntimeError):
    pass


class _NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    """Strip ``Authorization`` across redirects.

    Registry blob reads redirect to Azure Storage, which rejects a forwarded
    registry bearer token with 401.  urllib forwards it by default, so the
    header has to be removed explicitly on the redirected request.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.remove_header("Authorization")
        return new


_OPENER = urllib.request.build_opener(_NoAuthRedirect)


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 900.0,
) -> tuple[int, bytes, dict[str, str]]:
    merged = {"User-Agent": USER_AGENT}
    if token:
        merged["Authorization"] = f"Bearer {token}"
    merged.update(headers or {})
    request = urllib.request.Request(url, data=body, method=method, headers=merged)
    try:
        with _OPENER.open(request, timeout=timeout) as response:  # noqa: S310
            return (
                response.status,
                response.read(),
                {k.lower(): v for k, v in response.headers.items()},
            )
    except urllib.error.HTTPError as error:
        return error.code, error.read(), {k.lower(): v for k, v in error.headers.items()}


def _form_post(url: str, fields: dict[str, str]) -> dict[str, Any]:
    payload = urllib.parse.urlencode(fields).encode("ascii")
    status, body, _ = _request(
        "POST",
        url,
        body=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=120.0,
    )
    if status != 200:
        raise TransportError(f"{url} returned {status}: {body[:400]!r}")
    return json.loads(body.decode("utf-8"))


def _managed_identity_token(resource: str) -> str:
    endpoint = os.environ.get("IDENTITY_ENDPOINT") or os.environ.get("MSI_ENDPOINT")
    header = os.environ.get("IDENTITY_HEADER") or os.environ.get("MSI_SECRET")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    if endpoint and header:
        query = {"api-version": "2019-08-01", "resource": resource}
        if client_id:
            query["client_id"] = client_id
        status, body, _ = _request(
            "GET",
            f"{endpoint}?{urllib.parse.urlencode(query)}",
            headers={"X-IDENTITY-HEADER": header, "Metadata": "true"},
            timeout=60.0,
        )
    else:
        query = {"api-version": "2018-02-01", "resource": resource}
        if client_id:
            query["client_id"] = client_id
        status, body, _ = _request(
            "GET",
            "http://169.254.169.254/metadata/identity/oauth2/token?"
            + urllib.parse.urlencode(query),
            headers={"Metadata": "true"},
            timeout=60.0,
        )
    if status != 200:
        raise TransportError(f"managed identity token request returned {status}")
    return str(json.loads(body.decode("utf-8"))["access_token"])


def _refresh_token(registry: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    aad = _managed_identity_token("https://management.azure.com/")
    claims = aad.split(".")[1]
    claims += "=" * (-len(claims) % 4)
    import base64

    tenant = json.loads(base64.urlsafe_b64decode(claims).decode("utf-8"))["tid"]
    payload = _form_post(
        f"https://{registry}/oauth2/exchange",
        {
            "grant_type": "access_token",
            "service": registry,
            "tenant": tenant,
            "access_token": aad,
        },
    )
    return str(payload["refresh_token"])


def access_token(registry: str, repository: str, actions: str, refresh: str | None) -> str:
    preset = os.environ.get("ACR_ACCESS_TOKEN")
    if preset:
        return preset
    token = _refresh_token(registry, refresh or os.environ.get("ACR_REFRESH_TOKEN"))
    payload = _form_post(
        f"https://{registry}/oauth2/token",
        {
            "grant_type": "refresh_token",
            "service": registry,
            "scope": f"repository:{repository}:{actions}",
            "refresh_token": token,
        },
    )
    return str(payload["access_token"])


def _digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _blob_exists(registry: str, repository: str, digest: str, token: str) -> bool:
    status, _, _ = _request(
        "HEAD", f"https://{registry}/v2/{repository}/blobs/{digest}", token=token
    )
    return status == 200


def put_blob(registry: str, repository: str, blob: bytes, token: str) -> dict[str, Any]:
    digest = _digest(blob)
    if not _blob_exists(registry, repository, digest, token):
        status, body, headers = _request(
            "POST", f"https://{registry}/v2/{repository}/blobs/uploads/", token=token
        )
        if status != 202:
            raise TransportError(f"upload session refused: {status} {body[:300]!r}")
        location = headers["location"]
        if location.startswith("/"):
            location = f"https://{registry}{location}"
        joiner = "&" if "?" in location else "?"
        status, body, _ = _request(
            "PUT",
            f"{location}{joiner}digest={urllib.parse.quote(digest)}",
            token=token,
            body=blob,
            headers={"Content-Type": "application/octet-stream"},
        )
        if status != 201:
            raise TransportError(f"blob upload failed: {status} {body[:300]!r}")
    return {"digest": digest, "mediaType": LAYER_TYPE, "size": len(blob)}


def get_blob(registry: str, repository: str, digest: str, token: str) -> bytes:
    status, body, _ = _request(
        "GET", f"https://{registry}/v2/{repository}/blobs/{digest}", token=token
    )
    if status != 200:
        raise TransportError(f"blob download failed: {status}")
    if _digest(body) != digest:
        raise TransportError("downloaded blob does not match its digest")
    return body


def pack_directory(source: Path) -> bytes:
    """Deterministically tar a directory: sorted, no owner, no mtime."""

    import gzip
    import io

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            info = tarfile.TarInfo(path.relative_to(source).as_posix())
            data = path.read_bytes()
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=0)


def unpack_directory(payload: bytes, dest: Path) -> list[str]:
    import gzip
    import io

    dest.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(payload)), mode="r") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name.startswith(("/", "..")):
                raise TransportError(f"refusing tar member {member.name!r}")
            target = dest / member.name
            if not target.resolve().is_relative_to(dest.resolve()):
                raise TransportError(f"tar member escapes destination: {member.name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                raise TransportError(f"unreadable tar member {member.name!r}")
            target.write_bytes(extracted.read())
            names.append(member.name)
    return names


def push(args: argparse.Namespace) -> int:
    source = Path(args.source)
    token = access_token(args.registry, args.repository, "pull,push", args.acr_refresh_token)
    payload = pack_directory(source)
    layer = put_blob(args.registry, args.repository, payload, token)
    config = json.dumps({}, separators=(",", ":")).encode("ascii")
    config_descriptor = put_blob(args.registry, args.repository, config, token)
    config_descriptor["mediaType"] = CONFIG_TYPE
    manifest = {
        "annotations": {
            "org.opencontainers.image.title": args.tag,
            "sha256.tar.gz": hashlib.sha256(payload).hexdigest(),
        },
        "artifactType": ARTIFACT_TYPE,
        "config": config_descriptor,
        "layers": [layer],
        "mediaType": MANIFEST_TYPE,
        "schemaVersion": 2,
    }
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    status, response, _ = _request(
        "PUT",
        f"https://{args.registry}/v2/{args.repository}/manifests/{args.tag}",
        token=token,
        body=body,
        headers={"Content-Type": MANIFEST_TYPE},
    )
    if status != 201:
        raise TransportError(f"manifest push failed: {status} {response[:400]!r}")
    print(
        json.dumps(
            {
                "files": sum(1 for p in source.rglob("*") if p.is_file()),
                "layer_digest": layer["digest"],
                "manifest_digest": _digest(body),
                "reference": f"{args.registry}/{args.repository}:{args.tag}",
                "size": len(payload),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def pull(args: argparse.Namespace) -> int:
    token = access_token(args.registry, args.repository, "pull", args.acr_refresh_token)
    status, body, _ = _request(
        "GET",
        f"https://{args.registry}/v2/{args.repository}/manifests/{args.reference}",
        token=token,
        headers={"Accept": ACCEPT},
    )
    if status != 200:
        raise TransportError(f"manifest fetch failed: {status} {body[:300]!r}")
    manifest = json.loads(body.decode("utf-8"))
    layers = manifest["layers"]
    if len(layers) != 1:
        raise TransportError(f"expected exactly one layer, found {len(layers)}")
    payload = get_blob(args.registry, args.repository, layers[0]["digest"], token)
    names = unpack_directory(payload, Path(args.dest))
    print(
        json.dumps(
            {
                "files": len(names),
                "layer_digest": layers[0]["digest"],
                "manifest_digest": _digest(body),
                "sha256_tar_gz": hashlib.sha256(payload).hexdigest(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, help="registry login server")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--acr-refresh-token", default=None)
    sub = parser.add_subparsers(dest="mode", required=True)
    push_parser = sub.add_parser("push")
    push_parser.add_argument("--source", required=True)
    push_parser.add_argument("--tag", required=True)
    push_parser.set_defaults(func=push)
    pull_parser = sub.add_parser("pull")
    pull_parser.add_argument("--reference", required=True)
    pull_parser.add_argument("--dest", required=True)
    pull_parser.set_defaults(func=pull)
    args = parser.parse_args()
    try:
        return args.func(args)
    except TransportError as error:
        print(f"OCI_TRANSPORT_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
