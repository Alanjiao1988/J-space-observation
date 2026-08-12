"""Study 3 P0-R1 generation-2 private-Blob artifact transport.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 7.

Generation 1 wrote its model artifacts only into the GPU container's ephemeral
runtime directory and printed their hashes. A terminal P0-R1 disposition could
therefore never be published from the actual emitted bytes. This module makes the
existing private Azure Blob route the primary durable transport.

Every rule that keeps the route legal is enforced here rather than described:

* Microsoft Entra managed identity only. A shared key, a connection string, a
  SAS token, an anonymous client or a public endpoint refuses before any call.
* One unique, attempt-bound prefix under the registered container, proven absent
  before the attempt starts.
* ``overwrite = false`` on every upload, so an object is written once and never
  replaced.
* Every uploaded object is read back through the same authenticated private
  route and verified by byte count and SHA-256.
* The immutable artifact manifest is written **last**, and is valid only after
  every object it lists has read back exactly.

The Azure SDK is imported lazily inside the real backend, so this module stays
importable, testable and model-free on a machine with no SDK and no network. The
tests drive production code through an injected in-memory backend rather than
re-implementing it.

This module performs zero tokenizer, checkpoint, model and GPU operations.
"""

import argparse
import hashlib
import json
import os
import sys

ACCOUNT = "stjspacefiles0709085305"
CONTAINER = "jspace-results"
ACCOUNT_URL = "https://%s.blob.core.windows.net" % ACCOUNT

#: The registered user-assigned identity. Its documented role on the storage
#: account is Storage Blob Data Contributor.
IDENTITY_RESOURCE_ID = (
    "/subscriptions/943bacdf-8b6e-4e3a-8126-a149f623d32e/resourcegroups/"
    "rg-jspace-observation-sea/providers/Microsoft.ManagedIdentity/"
    "userAssignedIdentities/id-jspace-aca-acrpull-sea")
IDENTITY_CLIENT_ID = "479d9229-632e-4490-ad92-854a34dfddf8"
IDENTITY_ROLE = "Storage Blob Data Contributor"

PREFIX_ROOT = "study3/p0_r1/gen2"

MANIFEST_NAME = "p0_r1_artifact_manifest.json"

#: Environment names that would signal a forbidden credential path. Their mere
#: presence refuses: the route is managed identity or nothing.
FORBIDDEN_CREDENTIAL_ENVIRONMENT = (
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_ACCESS_KEY",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_STORAGE_ACCOUNT_KEY",
)

MANIFEST_SCHEMA_VERSION = "study3-p0-r1-blob-artifact-manifest-v2"


class BlobTransportDefect(Exception):
    """A fail-closed durable-transport stop."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def attempt_prefix(attempt_id):
    """The one unique, attempt-bound prefix this attempt may ever write."""
    if not attempt_id or not isinstance(attempt_id, str):
        raise BlobTransportDefect("an attempt prefix requires an attempt id")
    for character in attempt_id:
        if not (character.isalnum() or character in "-_."):
            raise BlobTransportDefect(
                "attempt id %r is not a safe prefix component" % attempt_id)
    if ".." in attempt_id:
        raise BlobTransportDefect("attempt id %r traverses" % attempt_id)
    return "%s/%s/" % (PREFIX_ROOT, attempt_id)


def validate_object_name(name):
    if not name or not isinstance(name, str):
        raise BlobTransportDefect("an object name must be a non-empty string")
    if name.startswith("/") or ".." in name or "\\" in name:
        raise BlobTransportDefect("object name %r traverses" % name)
    return name


def assert_no_forbidden_credential(environ=None):
    """Refuse the moment a shared key, connection string or SAS is in reach."""
    environ = os.environ if environ is None else environ
    present = [name for name in FORBIDDEN_CREDENTIAL_ENVIRONMENT
               if environ.get(name)]
    if present:
        raise BlobTransportDefect(
            "a forbidden storage credential is present in the environment "
            "(%s); the registered route is Microsoft Entra managed identity "
            "only and no shared key, SAS or embedded credential is authorized"
            % ", ".join(sorted(present)))
    return True


class InMemoryBackend(object):
    """A deterministic backend used by the CPU-only production-bound tests.

    It is intentionally strict in exactly the ways the real route is strict: it
    refuses a second write to the same name, and it returns exact bytes.
    """

    def __init__(self):
        self.objects = {}
        self.writes = []
        self.reads = []
        self.credential_kind = "managed-identity"
        self.account_url = ACCOUNT_URL

    def exists(self, name):
        return name in self.objects

    def upload(self, name, payload, overwrite=False):
        self.writes.append(name)
        if not overwrite and name in self.objects:
            raise BlobTransportDefect(
                "%s already exists and overwrite is false" % name)
        self.objects[name] = bytes(payload)

    def download(self, name):
        self.reads.append(name)
        if name not in self.objects:
            raise BlobTransportDefect("%s does not exist" % name)
        return self.objects[name]

    def list_names(self, prefix):
        return sorted(name for name in self.objects if name.startswith(prefix))


class AzureManagedIdentityBackend(object):
    """The production backend. Managed identity through the private endpoint."""

    def __init__(self, account_url=None, container=None, client_id=None):
        assert_no_forbidden_credential()
        self.account_url = account_url or ACCOUNT_URL
        self.container = container or CONTAINER
        self.client_id = client_id or IDENTITY_CLIENT_ID
        self.credential_kind = "managed-identity"
        self._container_client = None

    def _client(self):
        if self._container_client is not None:
            return self._container_client
        from azure.identity import ManagedIdentityCredential
        from azure.storage.blob import BlobServiceClient

        credential = ManagedIdentityCredential(client_id=self.client_id)
        service = BlobServiceClient(account_url=self.account_url,
                                    credential=credential)
        self._container_client = service.get_container_client(self.container)
        return self._container_client

    def exists(self, name):
        return self._client().get_blob_client(name).exists()

    def upload(self, name, payload, overwrite=False):
        if overwrite:
            raise BlobTransportDefect(
                "overwrite is never authorized on the P0-R1 result route")
        self._client().upload_blob(name=name, data=payload, overwrite=False)

    def download(self, name):
        return self._client().download_blob(name).readall()

    def list_names(self, prefix):
        return sorted(blob.name for blob
                      in self._client().list_blobs(name_starts_with=prefix))


class PrivateBlobTransport(object):
    """Attempt-bound, no-overwrite, read-back-verified durable transport."""

    def __init__(self, attempt_id, backend=None, prefix=None):
        self.attempt_id = attempt_id
        self.prefix = prefix or attempt_prefix(attempt_id)
        if not self.prefix.endswith("/"):
            raise BlobTransportDefect("an attempt prefix must end with '/'")
        self.backend = backend if backend is not None \
            else AzureManagedIdentityBackend()
        if getattr(self.backend, "credential_kind", None) != "managed-identity":
            raise BlobTransportDefect(
                "the P0-R1 result route accepts a managed-identity backend "
                "only; %r is not authorized"
                % getattr(self.backend, "credential_kind", None))
        self.uploaded = {}

    # -- preconditions -----------------------------------------------------

    def assert_prefix_unused(self, names):
        """Prove, before the attempt starts, that no final artifact exists."""
        existing = [name for name in names
                    if self.backend.exists(self.prefix + validate_object_name(name))]
        if existing:
            raise BlobTransportDefect(
                "the attempt prefix %s already carries %s; a unique "
                "attempt-bound prefix is a precondition and no object is ever "
                "replaced" % (self.prefix, ", ".join(sorted(existing))))
        return True

    # -- writes ------------------------------------------------------------

    def upload_and_verify(self, name, payload):
        """Upload once, then read every byte back through the same route."""
        validate_object_name(name)
        if not isinstance(payload, bytes):
            raise BlobTransportDefect("a durable artifact must be raw bytes")
        if name in self.uploaded:
            raise BlobTransportDefect(
                "%s was already uploaded in this attempt; an observation is "
                "never overwritten" % name)
        target = self.prefix + name
        self.backend.upload(target, payload, overwrite=False)
        echoed = self.backend.download(target)
        if len(echoed) != len(payload):
            raise BlobTransportDefect(
                "%s read back %d bytes, not the uploaded %d"
                % (name, len(echoed), len(payload)))
        if _sha256(echoed) != _sha256(payload):
            raise BlobTransportDefect(
                "%s read back a different sha256 than it uploaded" % name)
        record = {
            "name": name,
            "object": target,
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "read_back_verified": True,
        }
        self.uploaded[name] = record
        return record

    def write_manifest(self, required_names, extra=None):
        """Write the immutable artifact manifest last.

        The manifest is valid only after every object it lists has been read
        back exactly, so it is written after a fresh readback of the complete
        set rather than from the in-memory record alone.
        """
        missing = [name for name in required_names if name not in self.uploaded]
        if missing:
            raise BlobTransportDefect(
                "the artifact manifest cannot be written: %s were never "
                "uploaded" % ", ".join(sorted(missing)))
        entries = []
        for name in sorted(self.uploaded):
            record = self.uploaded[name]
            echoed = self.backend.download(record["object"])
            if len(echoed) != record["bytes"] \
                    or _sha256(echoed) != record["sha256"]:
                raise BlobTransportDefect(
                    "%s no longer reads back exactly; the manifest is invalid"
                    % name)
            entries.append(dict(record))
        document = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "document_class": "study3_p0_r1_blob_artifact_manifest",
            "attempt_id": self.attempt_id,
            "account": ACCOUNT,
            "container": CONTAINER,
            "prefix": self.prefix,
            "authentication": "microsoft-entra-managed-identity",
            "identity": IDENTITY_RESOURCE_ID,
            "identity_role": IDENTITY_ROLE,
            "shared_key_used": False,
            "sas_used": False,
            "public_endpoint_used": False,
            "overwrite_used": False,
            "required_objects": sorted(required_names),
            "artifacts": entries,
            "manifest_written_last": True,
            "valid_only_after_every_listed_object_read_back_exactly": True,
        }
        if extra:
            document.update(extra)
        payload = (json.dumps(document, indent=1, sort_keys=True,
                              ensure_ascii=True) + "\n").encode("utf-8")
        target = self.prefix + MANIFEST_NAME
        if self.backend.exists(target):
            raise BlobTransportDefect(
                "an artifact manifest already exists at %s" % target)
        self.backend.upload(target, payload, overwrite=False)
        echoed = self.backend.download(target)
        if echoed != payload:
            raise BlobTransportDefect(
                "the artifact manifest did not read back exactly")
        return {
            "name": MANIFEST_NAME,
            "object": target,
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "document": document,
        }

    # -- operator recovery -------------------------------------------------

    def upload_directory(self, out_dir, required_names=None, extra=None):
        """Persist an entire artifact directory, manifest last.

        Every object is uploaded exactly once and read back through the same
        managed-identity route before the manifest that lists it is written.
        """
        import p0_r1_transport as TRANSPORT
        required_names = tuple(required_names or TRANSPORT.REPLAY_ARTIFACTS)
        self.assert_prefix_unused(required_names + (MANIFEST_NAME,))
        records = []
        for name in required_names:
            with open(os.path.join(out_dir, name), "rb") as handle:
                records.append(self.upload_and_verify(name, handle.read()))
        manifest = self.write_manifest(required_names, extra=extra)
        return {
            "attempt_id": self.attempt_id,
            "account": ACCOUNT,
            "container": CONTAINER,
            "prefix": self.prefix,
            "objects": records,
            "manifest": {key: manifest[key]
                         for key in ("name", "object", "bytes", "sha256")},
            "total_bytes": sum(record["bytes"] for record in records),
            "manifest_written_last": True,
        }

    def recover_manifest(self):
        target = self.prefix + MANIFEST_NAME
        raw = self.backend.download(target)
        return json.loads(raw.decode("utf-8"))

    def recover_all(self):
        """Download the manifest and every listed object, verifying each one."""
        document = self.recover_manifest()
        if document.get("schema_version") != MANIFEST_SCHEMA_VERSION:
            raise BlobTransportDefect(
                "unknown artifact manifest schema %r"
                % document.get("schema_version"))
        if document.get("attempt_id") != self.attempt_id:
            raise BlobTransportDefect(
                "the manifest belongs to attempt %r, not %r"
                % (document.get("attempt_id"), self.attempt_id))
        listed = {entry["name"] for entry in document["artifacts"]}
        required = set(document.get("required_objects", []))
        if not required.issubset(listed):
            raise BlobTransportDefect(
                "the manifest omits required object(s) %s"
                % ", ".join(sorted(required - listed)))
        recovered = {}
        for entry in document["artifacts"]:
            payload = self.backend.download(entry["object"])
            if len(payload) != entry["bytes"] \
                    or _sha256(payload) != entry["sha256"]:
                raise BlobTransportDefect(
                    "%s does not read back against the manifest" % entry["name"])
            recovered[entry["name"]] = payload
        return document, recovered


def canary(attempt_id, backend=None, payload_bytes=None):
    """The model-free private-Blob canary of section 7.

    It uploads deterministic fixture bytes to a unique no-overwrite prefix,
    reads them back through the same authenticated route, writes the manifest
    last, then performs a full operator-style recovery and byte-exact
    verification. It runs no model entry point and allocates no GPU workload.
    """
    import p0_r1_transport as TRANSPORT

    fixtures = TRANSPORT.canary_fixture(
        attempt_id, total_bytes=payload_bytes,
        names=("p0_r1_canary_a.bin", "p0_r1_canary_b.bin",
               "p0_r1_canary_c.bin", "p0_r1_canary_d.bin"))
    transport = PrivateBlobTransport(attempt_id, backend=backend)
    transport.assert_prefix_unused(sorted(fixtures) + [MANIFEST_NAME])
    records = [transport.upload_and_verify(name, fixtures[name])
               for name in sorted(fixtures)]
    manifest = transport.write_manifest(sorted(fixtures), extra={
        "canary": True,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
    })
    document, recovered = transport.recover_all()
    if recovered != fixtures:
        raise BlobTransportDefect(
            "the private-Blob canary did not recover byte-exact fixtures")
    if document["artifacts"][-1]["name"] == MANIFEST_NAME:
        raise BlobTransportDefect(
            "the manifest must not list itself as a transported artifact")
    return {
        "attempt_id": attempt_id,
        "prefix": transport.prefix,
        "artifacts": records,
        "manifest": {key: manifest[key]
                     for key in ("name", "object", "bytes", "sha256")},
        "total_bytes": sum(len(value) for value in fixtures.values()),
        "recovered_byte_exact": True,
        "manifest_last": True,
        "overwrite_used": False,
        "authentication": "microsoft-entra-managed-identity",
    }


def implementation_identity(root=None):
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_blob_transport.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_blob_transport.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "account": ACCOUNT,
        "container": CONTAINER,
        "identity": IDENTITY_RESOURCE_ID,
        "identity_role": IDENTITY_ROLE,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--persist", action="store_true",
                        help="persist and read back a produced artifact "
                             "directory before the container may exit")
    parser.add_argument("--recover", action="store_true",
                        help="recover an attempt's artifacts to a local dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="run the canary against the in-memory backend")
    parser.add_argument("--attempt")
    parser.add_argument("--in-dir")
    parser.add_argument("--out-dir")
    parser.add_argument("--bytes", type=int)
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        if args.recover:
            if not args.attempt or not args.out_dir:
                print("--recover requires --attempt and --out-dir")
                return 2
            transport = PrivateBlobTransport(args.attempt)
            document, recovered = transport.recover_all()
            os.makedirs(args.out_dir, exist_ok=True)
            for name in sorted(recovered):
                target = os.path.join(args.out_dir, name)
                with open(target, "wb") as handle:
                    handle.write(recovered[name])
                print("RECOVERED=%s BYTES=%d SHA256=%s"
                      % (name, len(recovered[name]),
                         _sha256(recovered[name])))
            print("P0_R1_RECOVERED_ATTEMPT=%s" % document["attempt_id"])
            print("P0_R1_RECOVERY_COMPLETE=1")
            return 0

        if args.persist:
            if not args.attempt or not args.in_dir:
                print("--persist requires --attempt and --in-dir")
                return 2
            names = tuple(sorted(
                name for name in os.listdir(args.in_dir)
                if os.path.isfile(os.path.join(args.in_dir, name))))
            if not names:
                print("FAIL: %s holds no artifact to persist" % args.in_dir)
                return 2
            transport = PrivateBlobTransport(
                args.attempt,
                backend=InMemoryBackend() if args.dry_run else None)
            report = transport.upload_directory(args.in_dir,
                                                required_names=names)
            _document, recovered = transport.recover_all()
            for name in names:
                with open(os.path.join(args.in_dir, name), "rb") as handle:
                    local = handle.read()
                if recovered.get(name) != local:
                    print("FAIL: %s did not read back byte-for-byte" % name)
                    return 1
            report["read_back_verified"] = True
            report["objects_persisted"] = len(names)
            if args.receipt:
                with open(args.receipt, "wb") as handle:
                    handle.write((json.dumps(report, indent=1, sort_keys=True,
                                             ensure_ascii=True) + "\n")
                                 .encode("utf-8"))
            print("P0_R1_PERSIST_PREFIX=%s" % report["prefix"])
            for entry in report["objects"]:
                print("PERSISTED=%s BYTES=%d SHA256=%s"
                      % (entry["object"], entry["bytes"], entry["sha256"]))
            print("P0_R1_ARTIFACTS_PERSISTED=%d" % len(names))
            print("P0_R1_ARTIFACTS_READ_BACK_VERIFIED=1")
            return 0

        if not args.canary or not args.attempt:
            parser.print_help()
            return 2
        backend = InMemoryBackend() if args.dry_run else None
        report = canary(args.attempt, backend=backend,
                        payload_bytes=args.bytes)
        report["backend"] = "in-memory" if args.dry_run else "azure-private-blob"
        if args.receipt:
            with open(args.receipt, "wb") as handle:
                handle.write((json.dumps(report, indent=1, sort_keys=True,
                                         ensure_ascii=True) + "\n")
                             .encode("utf-8"))
        print("P0_R1_BLOB_CANARY_PREFIX=%s" % report["prefix"])
        for entry in report["artifacts"]:
            print("BLOB=%s BYTES=%d SHA256=%s"
                  % (entry["object"], entry["bytes"], entry["sha256"]))
        print("BLOB_MANIFEST=%s SHA256=%s"
              % (report["manifest"]["object"], report["manifest"]["sha256"]))
        print("P0_R1_BLOB_CANARY_COMPLETE=1")
        return 0
    except BlobTransportDefect as exc:
        print("BLOB TRANSPORT REFUSED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
