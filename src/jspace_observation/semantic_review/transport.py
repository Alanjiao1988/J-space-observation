"""Transport for the semantic-review job: Entra tokens, HTTP, Blob, retry.

Deliberately built on the standard library.  Every dependency added to a
scientific image is another thing whose version has to be pinned, recorded and
defended, and the two protocols needed here -- the container's managed-identity
token endpoint and a plain JSON POST -- are a few lines each.

The retry policy is the authority's, not a library's: only transport and
service failures are retried, at most eight attempts, byte-identical content
every time, same pinned deployment.  Nothing here can turn a failure into a
label; the two error types are raised for the orchestrator to stop on.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .addendum import (
    Addendum,
    MalformedResponseError,
    RoleProfile,
    TransportError,
    request_bytes,
    request_url,
)

STORAGE_API_VERSION = "2021-12-02"
USER_AGENT = "jspace-phase1-0d-semantic-review/1"


class TokenProvider:
    """Bearer tokens for a resource, from the container's managed identity."""

    def __init__(self, client_id: str | None = None) -> None:
        self._client_id = client_id or os.environ.get("AZURE_CLIENT_ID") or None
        self._cache: dict[str, tuple[str, float]] = {}

    def token(self, resource: str) -> str:
        cached = self._cache.get(resource)
        if cached and cached[1] - time.time() > 120:
            return cached[0]
        payload = self._fetch(resource)
        expires = float(payload.get("expires_on") or payload.get("expiresOn") or 0)
        token = str(payload["access_token"])
        self._cache[resource] = (token, expires)
        return token

    def _fetch(self, resource: str) -> Mapping[str, Any]:
        identity_endpoint = os.environ.get("IDENTITY_ENDPOINT")
        identity_header = os.environ.get("IDENTITY_HEADER")
        if identity_endpoint and identity_header:
            url = (
                f"{identity_endpoint}?api-version=2019-08-01&resource={resource}"
            )
            headers = {"X-IDENTITY-HEADER": identity_header}
        else:  # IMDS, for a VM-hosted runner
            url = (
                "http://169.254.169.254/metadata/identity/oauth2/token"
                f"?api-version=2018-02-01&resource={resource}"
            )
            headers = {"Metadata": "true"}
        if self._client_id:
            url = f"{url}&client_id={self._client_id}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


def resource_for(scope: str) -> str:
    return scope[: -len("/.default")] if scope.endswith("/.default") else scope


@dataclass
class HttpResult:
    status: int
    body: str
    headers: Mapping[str, str] = field(default_factory=dict)


def http_post_json(
    url: str, token: str, payload: bytes, timeout: float
) -> HttpResult:
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return HttpResult(
                status=response.status,
                body=response.read().decode("utf-8"),
                headers={k.lower(): v for k, v in response.headers.items()},
            )
    except urllib.error.HTTPError as error:  # a served response with a status
        return HttpResult(
            status=error.code,
            body=error.read().decode("utf-8", "replace"),
            headers={k.lower(): v for k, v in (error.headers or {}).items()},
        )


@dataclass
class Attempt:
    attempt: int
    status: int
    error: str | None


@dataclass
class Response:
    """One completed provider exchange, with everything a receipt needs."""

    status: int
    payload: Mapping[str, Any]
    raw_body: str
    request_sha256: str
    response_sha256: str
    latency_seconds: float
    retries: int
    attempts: list[Attempt]
    url: str
    api_version: str
    path: str


def call_row(
    *,
    profile: RoleProfile,
    addendum: Addendum,
    body: Mapping[str, Any],
    path: str,
    api_version: str,
    tokens: TokenProvider,
    poster: Callable[[str, str, bytes, float], HttpResult] = http_post_json,
    sleeper: Callable[[float], None] = time.sleep,
    timeout: float = 180.0,
    rng: random.Random | None = None,
) -> Response:
    """Send one row, retrying only transport failures with identical bytes."""

    from .addendum import sha256_text  # local import keeps the module import cheap

    retry = addendum.retry
    max_attempts = int(retry["max_attempts"])
    retry_codes = set(int(code) for code in retry["retry_status_codes"])
    backoff = float(retry["backoff_initial_seconds"])
    multiplier = float(retry["backoff_multiplier"])
    backoff_max = float(retry["backoff_max_seconds"])
    random_source = rng or random.Random(0)

    payload = request_bytes(body)
    request_hash = sha256_text(payload.decode("utf-8"))
    url = request_url(profile, path, api_version or None)
    resource = resource_for(profile.token_scope)

    attempts: list[Attempt] = []
    started = time.monotonic()
    for attempt in range(1, max_attempts + 1):
        try:
            result = poster(url, tokens.token(resource), payload, timeout)
            status, raw = result.status, result.body
            failure: str | None = None
        except Exception as error:  # noqa: BLE001 - connection reset/timeout
            status, raw, failure = 0, "", f"{type(error).__name__}: {error}"

        attempts.append(Attempt(attempt=attempt, status=status, error=failure))
        transport_failure = failure is not None or status in retry_codes
        if not transport_failure:
            if status != 200:
                # A 4xx that is not in the retry set is a configuration or
                # authorization defect, never a semantic outcome.
                raise TransportError(
                    f"{profile.role} received HTTP {status} from {path}: {raw[:400]}"
                )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as error:
                raise MalformedResponseError(
                    f"{profile.role} returned a non-JSON envelope: {error}"
                ) from error
            return Response(
                status=status,
                payload=parsed,
                raw_body=raw,
                request_sha256=request_hash,
                response_sha256=sha256_text(raw),
                latency_seconds=time.monotonic() - started,
                retries=attempt - 1,
                attempts=attempts,
                url=url,
                api_version=api_version,
                path=path,
            )
        if attempt < max_attempts:
            delay = min(backoff * (multiplier ** (attempt - 1)), backoff_max)
            sleeper(random_source.uniform(0.0, delay))

    last = attempts[-1]
    raise TransportError(
        f"{profile.role} exhausted {max_attempts} identical attempts; "
        f"last status {last.status} error {last.error}"
    )


# ---------------------------------------------------------------------------
# Blob, with create-only semantics
# ---------------------------------------------------------------------------


def blob_request(
    method: str,
    url: str,
    token: str,
    *,
    body: bytes | None = None,
    extra_headers: Mapping[str, str] | None = None,
    timeout: float = 120.0,
) -> HttpResult:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-ms-version": STORAGE_API_VERSION,
        "User-Agent": USER_AGENT,
    }
    headers.update(extra_headers or {})
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return HttpResult(
                status=response.status,
                body=response.read().decode("utf-8", "replace"),
                headers={k.lower(): v for k, v in response.headers.items()},
            )
    except urllib.error.HTTPError as error:
        return HttpResult(
            status=error.code,
            body=error.read().decode("utf-8", "replace"),
            headers={k.lower(): v for k, v in (error.headers or {}).items()},
        )


def blob_bytes(
    method: str,
    url: str,
    token: str,
    *,
    timeout: float = 120.0,
) -> tuple[int, bytes]:
    """Read a blob as bytes.

    ``blob_request`` decodes to text with ``errors="replace"``, which is right
    for XML listings and fatal for a payload that is about to be hashed: a
    replacement character would silently change the bytes.  Downloads therefore
    go through this function instead.
    """

    headers = {
        "Authorization": f"******",
        "x-ms-version": STORAGE_API_VERSION,
        "User-Agent": USER_AGENT,
    }
    request = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class BlobClient:
    """The narrowest Blob surface this job needs, over Entra tokens only."""

    RESOURCE = "https://storage.azure.com"

    def __init__(self, account: str, container: str, tokens: TokenProvider) -> None:
        self.account = account
        self.container = container
        self._tokens = tokens

    def _url(self, name: str) -> str:
        return f"https://{self.account}.blob.core.windows.net/{self.container}/{name}"

    def list_prefix(self, prefix: str) -> list[str]:
        """List every blob under a prefix, following continuation markers.

        A truncated listing would produce a pack that is short some files and
        still internally consistent, so the marker loop is not optional.
        """

        names: list[str] = []
        marker = ""
        for _ in range(1000):
            url = (
                f"https://{self.account}.blob.core.windows.net/{self.container}"
                f"?restype=container&comp=list"
                f"&prefix={urllib.parse.quote(prefix, safe='/')}"
            )
            if marker:
                url = f"{url}&marker={urllib.parse.quote(marker, safe='')}"
            result = blob_request("GET", url, self._tokens.token(self.RESOURCE))
            if result.status != 200:
                raise TransportError(f"listing {prefix} failed: {result.status}")
            for chunk in result.body.split("<Name>")[1:]:
                names.append(chunk.split("</Name>")[0])
            marker = ""
            if "<NextMarker>" in result.body:
                marker = result.body.split("<NextMarker>")[1].split("</NextMarker>")[0]
            if not marker:
                return names
        raise TransportError(f"listing {prefix} did not terminate")

    def get(self, name: str) -> bytes:
        status, payload = blob_bytes("GET", self._url(name), self._tokens.token(self.RESOURCE))
        if status != 200:
            raise TransportError(f"reading {name} failed: {status}")
        return payload

    def put_create_only(self, name: str, payload: bytes) -> None:
        """Upload, refusing to overwrite anything that already exists."""

        result = blob_request(
            "PUT",
            self._url(name),
            self._tokens.token(self.RESOURCE),
            body=payload,
            extra_headers={
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "application/octet-stream",
                "If-None-Match": "*",
            },
        )
        if result.status == 409 or result.status == 412:
            raise TransportError(f"{name} already exists; this run refuses to overwrite")
        if result.status not in (201, 202):
            raise TransportError(f"uploading {name} failed: {result.status} {result.body[:200]}")
