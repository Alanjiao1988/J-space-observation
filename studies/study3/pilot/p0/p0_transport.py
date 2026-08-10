"""Deterministic artifact transport for the Study 3-P0 feasibility pilot.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
sections 7.2 and 11.

Why this exists
---------------
Stage P0-T runs in the registered Azure container route. Its result and receipt
must come back to the repository without editing a scientific value, and the
return path must be *checkable* rather than trusted: section 11 requires the
returned artifacts to be materialized and then validated.

The stage is also effectively single-shot. Every encode increments a cumulative,
non-resettable counter, so a transport that silently truncated and forced a
rerun would spend the tokenizer budget a second time. The channel is therefore
self-verifying: the packed bytes carry their own SHA-256 and byte count, and
``unpack`` refuses anything that does not reproduce both.

The channel is the job log, which needs no key, no SAS and no secret, matching
the image's registered authentication policy.

Standard library only, by design.
"""

import argparse
import base64
import hashlib
import io
import os
import sys
import tarfile

BEGIN = "-----BEGIN STUDY3-P0 TRANSPORT-----"
END = "-----END STUDY3-P0 TRANSPORT-----"
DIGEST_PREFIX = "STUDY3_P0_TRANSPORT_SHA256="
BYTES_PREFIX = "STUDY3_P0_TRANSPORT_BYTES="
NAMES_PREFIX = "STUDY3_P0_TRANSPORT_NAMES="
LINE_WIDTH = 100


class TransportDefect(Exception):
    """Raised when a packed payload does not reproduce its declared identity."""


def pack(source_dir, stream=None):
    """Emit ``source_dir`` as a self-describing base64 block on stdout."""
    stream = stream if stream is not None else sys.stdout
    names = sorted(
        name for name in os.listdir(source_dir)
        if os.path.isfile(os.path.join(source_dir, name)))
    if not names:
        raise TransportDefect("there is nothing to transport in %r" % source_dir)

    buffer = io.BytesIO()
    # mtime is forced to 0 so the packed bytes depend only on the artifacts.
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=9) as archive:
        for name in names:
            path = os.path.join(source_dir, name)
            with open(path, "rb") as handle:
                payload = handle.read()
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(payload))
    raw = buffer.getvalue()

    stream.write("%s%s\n" % (NAMES_PREFIX, ",".join(names)))
    stream.write("%s%d\n" % (BYTES_PREFIX, len(raw)))
    stream.write("%s%s\n" % (DIGEST_PREFIX, hashlib.sha256(raw).hexdigest()))
    stream.write(BEGIN + "\n")
    encoded = base64.b64encode(raw).decode("ascii")
    for start in range(0, len(encoded), LINE_WIDTH):
        stream.write(encoded[start:start + LINE_WIDTH] + "\n")
    stream.write(END + "\n")
    stream.flush()
    return len(raw)


def unpack(log_text, destination):
    """Materialize a packed payload from a job log, refusing any mismatch."""
    lines = log_text.splitlines()

    def _single(prefix):
        found = [line.split(prefix, 1)[1].strip()
                 for line in lines if prefix in line]
        if len(found) != 1:
            raise TransportDefect(
                "expected exactly one %s marker, found %d" % (prefix, len(found)))
        return found[0]

    declared_names = [n for n in _single(NAMES_PREFIX).split(",") if n]
    declared_bytes = int(_single(BYTES_PREFIX))
    declared_digest = _single(DIGEST_PREFIX)

    starts = [i for i, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise TransportDefect(
            "the log does not carry exactly one complete transport block")

    encoded = "".join(line.strip() for line in lines[starts[0] + 1:ends[0]])
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != declared_bytes:
        raise TransportDefect(
            "transport is %d bytes, not the declared %d"
            % (len(raw), declared_bytes))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != declared_digest:
        raise TransportDefect(
            "transport sha256 %s != declared %s" % (digest, declared_digest))

    os.makedirs(destination, exist_ok=True)
    written = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = archive.getmembers()
        if sorted(m.name for m in members) != sorted(declared_names):
            raise TransportDefect(
                "the payload does not carry exactly the declared artifacts")
        for member in members:
            if member.name != os.path.basename(member.name) \
                    or not member.isfile():
                raise TransportDefect("unsafe payload member %r" % member.name)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise TransportDefect("unreadable payload member %r" % member.name)
            target = os.path.join(destination, member.name)
            with open(target, "wb") as handle:
                handle.write(extracted.read())
            written.append(target)
    return written, digest, len(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    packer = sub.add_parser("pack")
    packer.add_argument("--source-dir", required=True)
    unpacker = sub.add_parser("unpack")
    unpacker.add_argument("--log", required=True)
    unpacker.add_argument("--dest", required=True)
    args = parser.parse_args(argv)

    if args.mode == "pack":
        size = pack(args.source_dir)
        print("STUDY3_P0_TRANSPORT_COMPLETE=1 packed_bytes=%d" % size,
              file=sys.stderr)
        return 0

    with open(args.log, "rb") as handle:
        text = handle.read().decode("utf-8", errors="replace")
    written, digest, size = unpack(text, args.dest)
    print("verified transport sha256 %s (%d bytes)" % (digest, size))
    for path in written:
        print("materialized %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
