"""V2 Blob downloads that preserve evidence bytes and managed-identity auth."""

from __future__ import annotations

import urllib.error
import urllib.request

from jspace_observation.semantic_review import transport as base_transport


def blob_bytes(
    method: str,
    url: str,
    token: str,
    *,
    timeout: float = 120.0,
) -> tuple[int, bytes]:
    """Read exact Blob bytes with the supplied Entra bearer token."""

    headers = {
        "Authorization": f"Bearer {token}",
        "x-ms-version": base_transport.STORAGE_API_VERSION,
        "User-Agent": base_transport.USER_AGENT,
    }
    request = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class BlobClient(base_transport.BlobClient):
    """Use the frozen v1 client surface except for authenticated byte downloads."""

    def get(self, name: str) -> bytes:
        status, payload = blob_bytes(
            "GET",
            self._url(name),
            self._tokens.token(self.RESOURCE),
        )
        if status != 200:
            raise base_transport.TransportError(f"reading {name} failed: {status}")
        return payload
