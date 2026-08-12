"""Study 3 P0-R1 generation-2 complete-byte transport envelope.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 6, over the two earlier P0-R1 authorities.

Generation 1 printed each replay artifact's SHA-256 and byte count and nothing
else. A digest and a byte count cannot reconstruct the preimage, so the replay
result was recoverable only by rerunning the one-shot gate, which is exactly what
the earlier authority forbade. This module closes that defect.

The envelope carries **every byte**. Each artifact is split into fixed-size raw
chunks; each chunk is emitted as one self-describing log line below the
documented platform truncation boundary; a manifest entry line per artifact is
emitted only after every chunk line; and a single completion line is emitted
last. Recovery reconstructs the exact preimage from a captured log and refuses
on a missing chunk, a conflicting duplicate, an unknown artifact, a traversing
name, a wrong attempt, a wrong count, or any hash or byte mismatch.

Recovery deliberately tolerates the three harmless things Azure log capture
actually does: it prefixes lines with a timestamp or a stream tag, it may reorder
independent lines, and it may repeat an identical line. None of those can change
a preimage, so none of them is a refusal.

This module performs zero tokenizer, checkpoint, model and GPU operations, and
imports only the standard library.
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import sys

#: The versioned envelope identity. A recovery refuses any other version rather
#: than guessing at a foreign grammar.
ENVELOPE_VERSION = "study3-p0-r1-transport-envelope-v2"

CHUNK_MARKER = "P0R1TXC"
MANIFEST_MARKER = "P0R1TXM"
COMPLETE_MARKER = "P0R1TXE"

#: The conservative per-line ceiling. Azure Container Registry and Container
#: Apps log capture truncate very long lines; every emitted line is kept below
#: this bound with headroom rather than at a platform maximum.
MAX_LINE_BYTES = 1024

#: Raw bytes per chunk. 512 raw bytes base64-encode to 684 characters, which
#: leaves well over 300 characters for the line header at the ceiling above.
RAW_CHUNK_BYTES = 512

#: The four canonical replay artifacts. Any other artifact name is unknown and
#: refuses.
REPLAY_ARTIFACTS = (
    "p0_r1_replay_result.json",
    "p0_r1_replay_receipt.json",
    "p0_r1_replay_counters.json",
    "P0_R1_REPLAY_DISPOSITION.md",
)

#: The registered projection of the maximum combined size of those four
#: artifacts. The derived replay document is under 40 KiB; this projection keeps
#: an order of magnitude of headroom so that a canary sized from it is a real
#: over-test rather than a coincidence.
MAX_PROJECTED_COMBINED_REPLAY_ARTIFACT_BYTES = 524288

#: Section 6 requires the pre-freeze canary to be at least twice the maximum
#: projected combined replay-artifact size.
CANARY_MINIMUM_TOTAL_BYTES = 2 * MAX_PROJECTED_COMBINED_REPLAY_ARTIFACT_BYTES

_FIELD_ORDER_CHUNK = ("v", "a", "n", "b", "h", "i", "c", "s", "d")
_FIELD_ORDER_MANIFEST = ("v", "a", "n", "b", "h", "c")
_FIELD_ORDER_COMPLETE = ("v", "a", "k", "h")

_HEX = "0123456789abcdef"


class TransportDefect(Exception):
    """A fail-closed transport stop. No pass authorization survives one."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _require_hex(value, label):
    if not isinstance(value, str) or len(value) != 64 \
            or any(character not in _HEX for character in value):
        raise TransportDefect("%s is not a lowercase sha256 hex digest" % label)
    return value


def validate_artifact_name(name, allowed=None):
    """Refuse an unknown or traversing artifact name.

    A recovered artifact is written to an operator-owned directory, so the name
    is an untrusted path component and is treated as one.
    """
    if not isinstance(name, str) or not name:
        raise TransportDefect("an artifact name must be a non-empty string")
    if "/" in name or "\\" in name or name in (".", "..") \
            or name.startswith(".") or ".." in name \
            or os.path.isabs(name) or ":" in name:
        raise TransportDefect(
            "artifact name %r traverses or escapes the result directory" % name)
    if any(character in name for character in "|\r\n\t "):
        raise TransportDefect(
            "artifact name %r carries an envelope or line separator" % name)
    permitted = REPLAY_ARTIFACTS if allowed is None else tuple(allowed)
    if name not in permitted:
        raise TransportDefect(
            "unknown artifact %r; the envelope carries only %s"
            % (name, ", ".join(permitted)))
    return name


def _render(marker, fields, order):
    body = "|".join("%s=%s" % (key, fields[key]) for key in order)
    line = "%s|%s" % (marker, body)
    if len(line.encode("utf-8")) > MAX_LINE_BYTES:
        raise TransportDefect(
            "an envelope line of %d bytes exceeds the registered %d-byte "
            "truncation boundary" % (len(line.encode("utf-8")), MAX_LINE_BYTES))
    return line


def chunk_count(byte_count):
    """The exact chunk count for a payload, including the empty payload."""
    if byte_count <= 0:
        return 1
    return (byte_count + RAW_CHUNK_BYTES - 1) // RAW_CHUNK_BYTES


def encode_artifact(attempt_id, name, payload, allowed=None):
    """Every chunk line for one artifact, in index order."""
    validate_artifact_name(name, allowed=allowed)
    if not isinstance(payload, bytes):
        raise TransportDefect("an artifact payload must be raw bytes")
    total = chunk_count(len(payload))
    digest = _sha256(payload)
    lines = []
    for index in range(total):
        raw = payload[index * RAW_CHUNK_BYTES:(index + 1) * RAW_CHUNK_BYTES]
        lines.append(_render(CHUNK_MARKER, {
            "v": ENVELOPE_VERSION,
            "a": attempt_id,
            "n": name,
            "b": len(payload),
            "h": digest,
            "i": index,
            "c": total,
            "s": _sha256(raw),
            "d": base64.b64encode(raw).decode("ascii"),
        }, _FIELD_ORDER_CHUNK))
    return lines


def manifest_document(attempt_id, artifacts):
    """The canonical manifest document the completion line binds."""
    entries = []
    for name in sorted(artifacts):
        payload = artifacts[name]
        entries.append({
            "bytes": len(payload),
            "chunks": chunk_count(len(payload)),
            "name": name,
            "sha256": _sha256(payload),
        })
    return {
        "artifacts": entries,
        "attempt_id": attempt_id,
        "version": ENVELOPE_VERSION,
    }


def manifest_digest(document):
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical.encode("utf-8"))


def encode(attempt_id, artifacts, allowed=None):
    """Every envelope line for a complete artifact set, manifest last.

    ``artifacts`` maps an artifact name to its exact bytes. The returned list is
    chunk lines for every artifact, then one manifest entry line per artifact,
    then exactly one completion line. That order is the registered order and the
    recovery checks it.
    """
    if not attempt_id or not isinstance(attempt_id, str):
        raise TransportDefect("an envelope requires a non-empty attempt id")
    if "|" in attempt_id or any(character.isspace() for character in attempt_id):
        raise TransportDefect(
            "attempt id %r carries an envelope or line separator" % attempt_id)
    if not artifacts:
        raise TransportDefect("an envelope carries at least one artifact")
    lines = []
    for name in sorted(artifacts):
        lines.extend(encode_artifact(attempt_id, name, artifacts[name],
                                     allowed=allowed))
    document = manifest_document(attempt_id, artifacts)
    for entry in document["artifacts"]:
        lines.append(_render(MANIFEST_MARKER, {
            "v": ENVELOPE_VERSION,
            "a": attempt_id,
            "n": entry["name"],
            "b": entry["bytes"],
            "h": entry["sha256"],
            "c": entry["chunks"],
        }, _FIELD_ORDER_MANIFEST))
    lines.append(_render(COMPLETE_MARKER, {
        "v": ENVELOPE_VERSION,
        "a": attempt_id,
        "k": len(document["artifacts"]),
        "h": manifest_digest(document),
    }, _FIELD_ORDER_COMPLETE))
    return lines


def _parse_fields(body, order, marker):
    parts = body.split("|")
    if len(parts) != len(order):
        raise TransportDefect(
            "a %s line carries %d fields, not the registered %d"
            % (marker, len(parts), len(order)))
    fields = {}
    for part, key in zip(parts, order):
        if not part.startswith(key + "="):
            raise TransportDefect(
                "a %s line is malformed at field %r" % (marker, key))
        fields[key] = part[len(key) + 1:]
    return fields


def _integer(value, label):
    if not value or not value.isdigit():
        raise TransportDefect("%s is not a natural number" % label)
    return int(value)


def _scan(log_text):
    """Yield (order, marker, fields) for every envelope line in a raw log.

    The scan tolerates an arbitrary Azure prefix before the marker, trailing
    carriage returns and trailing whitespace. It records the first position at
    which each *distinct* line was seen, so a later duplicate of an identical
    line can never disturb the ordering check.
    """
    seen = {}
    records = []
    for position, raw_line in enumerate(log_text.splitlines()):
        line = raw_line.rstrip("\r\n\t ")
        for marker, order in ((CHUNK_MARKER, _FIELD_ORDER_CHUNK),
                              (MANIFEST_MARKER, _FIELD_ORDER_MANIFEST),
                              (COMPLETE_MARKER, _FIELD_ORDER_COMPLETE)):
            needle = marker + "|v="
            index = line.find(needle)
            if index < 0:
                continue
            candidate = line[index:]
            if candidate in seen:
                break
            seen[candidate] = position
            fields = _parse_fields(candidate[len(marker) + 1:], order, marker)
            if fields["v"] != ENVELOPE_VERSION:
                raise TransportDefect(
                    "envelope version %r is not the registered %r"
                    % (fields["v"], ENVELOPE_VERSION))
            records.append((position, marker, fields))
            break
    return records


def recover(log_text, attempt_id=None, allowed=None):
    """Reconstruct every exact artifact from a captured raw log.

    Returns a mapping of artifact name to exact bytes. Raises
    :class:`TransportDefect` on every registered refusal condition.
    """
    records = _scan(log_text)
    if not records:
        raise TransportDefect(
            "the captured log carries no %s envelope" % ENVELOPE_VERSION)

    attempts = {fields["a"] for _, _, fields in records}
    if len(attempts) != 1:
        raise TransportDefect(
            "the captured log mixes attempt ids %s; one envelope carries one "
            "attempt" % ", ".join(sorted(attempts)))
    observed_attempt = attempts.pop()
    if attempt_id is not None and observed_attempt != attempt_id:
        raise TransportDefect(
            "the captured log carries attempt %r, not the required %r"
            % (observed_attempt, attempt_id))

    chunks = {}
    declared = {}
    manifest = {}
    complete = None
    last_chunk_position = -1
    first_manifest_position = None
    last_marker_position = -1
    last_marker = None

    for position, marker, fields in records:
        if position > last_marker_position:
            last_marker_position = position
            last_marker = marker
        if marker == CHUNK_MARKER:
            name = validate_artifact_name(fields["n"], allowed=allowed)
            index = _integer(fields["i"], "chunk index")
            total = _integer(fields["c"], "chunk count")
            byte_count = _integer(fields["b"], "artifact byte count") \
                if fields["b"] != "0" else 0
            _require_hex(fields["h"], "artifact digest")
            _require_hex(fields["s"], "chunk digest")
            if index >= total:
                raise TransportDefect(
                    "chunk index %d of %s is outside its declared count %d"
                    % (index, name, total))
            try:
                raw = base64.b64decode(fields["d"].encode("ascii"),
                                       validate=True)
            except (binascii.Error, ValueError, UnicodeEncodeError):
                raise TransportDefect(
                    "chunk %d of %s does not carry a lossless encoding"
                    % (index, name))
            if _sha256(raw) != fields["s"]:
                raise TransportDefect(
                    "chunk %d of %s fails its own chunk digest" % (index, name))
            signature = (byte_count, fields["h"], total)
            if name in declared and declared[name] != signature:
                raise TransportDefect(
                    "conflicting duplicate: %s is declared as %r and as %r"
                    % (name, declared[name], signature))
            declared[name] = signature
            existing = chunks.setdefault(name, {})
            if index in existing and existing[index] != raw:
                raise TransportDefect(
                    "conflicting duplicate chunk %d of %s" % (index, name))
            existing[index] = raw
            last_chunk_position = max(last_chunk_position, position)
        elif marker == MANIFEST_MARKER:
            name = validate_artifact_name(fields["n"], allowed=allowed)
            entry = {
                "bytes": _integer(fields["b"], "manifest byte count")
                if fields["b"] != "0" else 0,
                "chunks": _integer(fields["c"], "manifest chunk count"),
                "name": name,
                "sha256": _require_hex(fields["h"], "manifest digest"),
            }
            if name in manifest and manifest[name] != entry:
                raise TransportDefect(
                    "conflicting duplicate manifest entry for %s" % name)
            manifest[name] = entry
            if first_manifest_position is None \
                    or position < first_manifest_position:
                first_manifest_position = position
        else:
            entry = {
                "k": _integer(fields["k"], "manifest artifact count"),
                "h": _require_hex(fields["h"], "manifest document digest"),
            }
            if complete is not None and complete != entry:
                raise TransportDefect(
                    "the captured log carries conflicting completion lines")
            complete = entry

    if complete is None:
        raise TransportDefect(
            "the captured log carries no completion line; the envelope is "
            "truncated and no artifact may be treated as recovered")
    if last_marker != COMPLETE_MARKER:
        raise TransportDefect(
            "an envelope line follows the completion line; the manifest must be "
            "emitted after every artifact chunk and the completion line last")
    if not manifest:
        raise TransportDefect("the captured log carries no manifest entry")
    if first_manifest_position is not None \
            and first_manifest_position < last_chunk_position:
        raise TransportDefect(
            "a manifest entry precedes an artifact chunk; manifest-last "
            "ordering is a registered requirement")
    if complete["k"] != len(manifest):
        raise TransportDefect(
            "the completion line declares %d artifacts but %d manifest entries "
            "were captured" % (complete["k"], len(manifest)))
    if sorted(manifest) != sorted(chunks):
        missing = sorted(set(manifest) - set(chunks))
        extra = sorted(set(chunks) - set(manifest))
        raise TransportDefect(
            "the manifest and the chunk stream disagree; missing=%s extra=%s"
            % (missing, extra))

    recovered = {}
    for name in sorted(manifest):
        entry = manifest[name]
        present = chunks[name]
        byte_count, digest, total = declared[name]
        if entry["chunks"] != total or entry["bytes"] != byte_count \
                or entry["sha256"] != digest:
            raise TransportDefect(
                "the manifest entry for %s disagrees with its chunk stream"
                % name)
        gaps = [index for index in range(total) if index not in present]
        if gaps:
            raise TransportDefect(
                "missing chunk(s) %s of %s; a partial envelope recovers nothing"
                % (gaps, name))
        payload = b"".join(present[index] for index in range(total))
        if len(payload) != byte_count:
            raise TransportDefect(
                "%s recovered %d bytes, not the declared %d"
                % (name, len(payload), byte_count))
        if _sha256(payload) != digest:
            raise TransportDefect(
                "%s fails its declared sha256 after reassembly" % name)
        recovered[name] = payload

    document = manifest_document(observed_attempt, recovered)
    if manifest_digest(document) != complete["h"]:
        raise TransportDefect(
            "the recovered artifact set does not reproduce the completion "
            "line's manifest digest")
    return recovered


def write_recovered(recovered, out_dir, allowed=None):
    """Write the exact canonical files into an operator-owned directory."""
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name in sorted(recovered):
        validate_artifact_name(name, allowed=allowed)
        path = os.path.join(out_dir, name)
        with open(path, "wb") as handle:
            handle.write(recovered[name])
        written.append({
            "name": name,
            "bytes": len(recovered[name]),
            "sha256": _sha256(recovered[name]),
            "path": path,
        })
    return written


def reconstruction_receipt(attempt_id, recovered, log_identity=None,
                           run_id=None):
    """The publishable proof that the bytes, not the hashes, were recovered."""
    document = manifest_document(attempt_id, recovered)
    return {
        "schema_version": "study3-p0-r1-transport-reconstruction-receipt-v2",
        "document_class": "study3_p0_r1_transport_reconstruction_receipt",
        "envelope_version": ENVELOPE_VERSION,
        "attempt_id": attempt_id,
        "acr_run_id": run_id,
        "captured_log": log_identity,
        "artifacts": document["artifacts"],
        "manifest_sha256": manifest_digest(document),
        "recovered_without_rerunning_the_gate": True,
        "hashes_alone_do_not_make_bytes_recoverable": True,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
    }


def canary_fixture(attempt_id, total_bytes=None, names=None):
    """Deterministic synthetic fixture artifacts for the pre-freeze canary.

    The bytes are derived from the attempt id by a hash chain, so the canary is
    reproducible, carries no scientific content, and cannot be confused with a
    replay artifact.
    """
    names = tuple(names) if names else REPLAY_ARTIFACTS
    total = CANARY_MINIMUM_TOTAL_BYTES if total_bytes is None else total_bytes
    if total < CANARY_MINIMUM_TOTAL_BYTES:
        raise TransportDefect(
            "a transport canary of %d bytes is below the registered minimum of "
            "%d, which is twice the maximum projected combined replay-artifact "
            "size" % (total, CANARY_MINIMUM_TOTAL_BYTES))
    per_artifact = total // len(names)
    fixtures = {}
    for position, name in enumerate(sorted(names)):
        seed = ("%s|%s|%d" % (attempt_id, name, position)).encode("utf-8")
        block = bytearray()
        state = hashlib.sha256(seed).digest()
        while len(block) < per_artifact:
            block.extend(state)
            state = hashlib.sha256(state).digest()
        fixtures[name] = bytes(block[:per_artifact])
    return fixtures


def self_check(attempt_id="p0-r1-transport-self-check"):
    """A deterministic in-process round trip. Used by the image build."""
    fixtures = canary_fixture(attempt_id)
    lines = encode(attempt_id, fixtures)
    for line in lines:
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            raise TransportDefect("an emitted line exceeded the line ceiling")
    noisy = []
    for position, line in enumerate(lines):
        noisy.append("2026-08-12T00:00:%02dZ stdout F %s" % (position % 60, line))
        if position % 997 == 0:
            noisy.append("2026-08-12T00:00:00Z stdout F %s" % line)
    recovered = recover("\n".join(noisy), attempt_id=attempt_id)
    if recovered != fixtures:
        raise TransportDefect("the transport self-check did not round trip")
    return {
        "attempt_id": attempt_id,
        "artifacts": len(fixtures),
        "total_bytes": sum(len(value) for value in fixtures.values()),
        "lines": len(lines),
        "max_line_bytes": max(len(line.encode("utf-8")) for line in lines),
    }


def implementation_identity(root=None):
    """The transport implementation's own byte identity, for the v2 lock."""
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_transport.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_transport.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "envelope_version": ENVELOPE_VERSION,
        "max_line_bytes": MAX_LINE_BYTES,
        "raw_chunk_bytes": RAW_CHUNK_BYTES,
        "max_projected_combined_replay_artifact_bytes":
            MAX_PROJECTED_COMBINED_REPLAY_ARTIFACT_BYTES,
        "canary_minimum_total_bytes": CANARY_MINIMUM_TOTAL_BYTES,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", action="store_true",
                        help="emit the envelope for a result directory")
    parser.add_argument("--recover", action="store_true",
                        help="recover exact bytes from a captured raw log")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--canary-fixture", action="store_true")
    parser.add_argument("--attempt")
    parser.add_argument("--in-dir")
    parser.add_argument("--out-dir")
    parser.add_argument("--log")
    parser.add_argument("--receipt")
    parser.add_argument("--run-id")
    parser.add_argument("--bytes", type=int)
    args = parser.parse_args(argv)

    try:
        if args.self_check:
            report = self_check()
            print("P0_R1_TRANSPORT_SELF_CHECK=1")
            for key in sorted(report):
                print("  %-16s %s" % (key, report[key]))
            return 0

        if args.canary_fixture:
            if not args.attempt or not args.out_dir:
                raise TransportDefect(
                    "--canary-fixture requires --attempt and --out-dir")
            fixtures = canary_fixture(args.attempt, total_bytes=args.bytes)
            written = write_recovered(fixtures, args.out_dir)
            for entry in written:
                print("FIXTURE=%s BYTES=%d SHA256=%s"
                      % (entry["name"], entry["bytes"], entry["sha256"]))
            return 0

        if args.emit:
            if not args.attempt or not args.in_dir:
                raise TransportDefect("--emit requires --attempt and --in-dir")
            artifacts = {}
            for name in REPLAY_ARTIFACTS:
                path = os.path.join(args.in_dir, name)
                if not os.path.exists(path):
                    raise TransportDefect(
                        "%s is missing from %s; the envelope carries every "
                        "canonical artifact or none" % (name, args.in_dir))
                with open(path, "rb") as handle:
                    artifacts[name] = handle.read()
            for line in encode(args.attempt, artifacts):
                print(line)
            return 0

        if args.recover:
            if not args.log or not args.out_dir:
                raise TransportDefect("--recover requires --log and --out-dir")
            with open(args.log, "rb") as handle:
                raw = handle.read()
            recovered = recover(raw.decode("utf-8", "replace"),
                                attempt_id=args.attempt)
            written = write_recovered(recovered, args.out_dir)
            receipt = reconstruction_receipt(
                args.attempt or manifest_document("", recovered)["attempt_id"],
                recovered,
                log_identity={"path": args.log, "bytes": len(raw),
                              "sha256": _sha256(raw)},
                run_id=args.run_id)
            if args.receipt:
                with open(args.receipt, "wb") as handle:
                    handle.write((json.dumps(receipt, indent=1, sort_keys=True,
                                             ensure_ascii=True) + "\n")
                                 .encode("utf-8"))
            for entry in written:
                print("RECOVERED=%s BYTES=%d SHA256=%s"
                      % (entry["name"], entry["bytes"], entry["sha256"]))
            print("P0_R1_TRANSPORT_RECOVERY_COMPLETE=1")
            return 0

        parser.print_help()
        return 2
    except TransportDefect as exc:
        print("TRANSPORT REFUSED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
