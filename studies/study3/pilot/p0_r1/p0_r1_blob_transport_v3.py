#!/usr/bin/env python3
"""Generation-3 private-Blob addressing, layered over the bound v2 transport.

``p0_r1_blob_transport.py`` is a bound generation-2 executable byte: its exact
contents are hashed into the generation-2 lock and re-hashed into the
generation-3 lock as a preserved historical object. It must not be edited, so
generation 3 does not change it -- it wraps it.

Only one thing actually needs to differ. The generation-2 module addresses
objects under ``study3/p0_r1/gen2/<attempt>/``. Generation-3 attempts must not
share a namespace with the two superseded generations, both so an operator can
tell at a glance which generation wrote an object and so a stale generation-2
canary artifact can never satisfy a generation-3 prefix-absence check. This
module supplies the ``gen3`` root and reuses every byte of the transport,
verification, manifest and backend logic underneath.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_blob_transport as BLOB  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-blob-addressing-v3"

PREFIX_ROOT = "study3/p0_r1/gen3"

ACCOUNT = BLOB.ACCOUNT
CONTAINER = BLOB.CONTAINER
MANIFEST_NAME = BLOB.MANIFEST_NAME
IDENTITY_CLIENT_ID = BLOB.IDENTITY_CLIENT_ID

BlobTransportDefect = BLOB.BlobTransportDefect
InMemoryBackend = BLOB.InMemoryBackend


def attempt_prefix(attempt_id):
    """The generation-3 attempt-bound prefix.

    Delegates validation to the bound generation-2 implementation, then
    re-roots the result so generations never share a namespace.
    """
    prefix = BLOB.attempt_prefix(attempt_id)
    if not prefix.startswith(BLOB.PREFIX_ROOT + "/"):
        raise BlobTransportDefect(
            "the generation-2 prefix root changed unexpectedly: %r" % prefix)
    return PREFIX_ROOT + prefix[len(BLOB.PREFIX_ROOT):]


class PrivateBlobTransportV3(BLOB.PrivateBlobTransport):
    """The bound transport, addressed under the generation-3 root."""

    def __init__(self, attempt_id, backend=None, prefix=None):
        super(PrivateBlobTransportV3, self).__init__(
            attempt_id, backend=backend,
            prefix=prefix or attempt_prefix(attempt_id))
        if not self.prefix.startswith(PREFIX_ROOT + "/"):
            raise BlobTransportDefect(
                "a generation-3 attempt refuses to write outside %s/"
                % PREFIX_ROOT)


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_blob_transport_v3.py",
        "prefix_root": PREFIX_ROOT,
        "generation_2_prefix_root": BLOB.PREFIX_ROOT,
        "account": ACCOUNT,
        "container": CONTAINER,
        "wraps_without_editing": "p0_r1_blob_transport.py",
        "shares_a_namespace_with_earlier_generations": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--prefix")
    args = parser.parse_args(argv)
    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    if args.prefix:
        print(attempt_prefix(args.prefix))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
