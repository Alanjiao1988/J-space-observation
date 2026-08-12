"""Verify a generation-2 replay receipt and its transport receipt together.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 6 and 10.

Generation 1 checked the replay receipt's zero counters and stopped there. That
left the actual defect unexamined: the receipt could be perfectly valid while the
result bytes the successor needs never left the container intact.

This checker therefore refuses unless *both* hold. The scientific counters must
all be zero, and every artifact the gate produced must have been transported and
verified byte-for-byte at rest. A pass authorization that is not backed by a
verified transport is rejected here, before it can reach the model pilot.
"""

import argparse
import hashlib
import json
import os
import sys

SCIENTIFIC_ZERO_FIELDS = (
    "tokenizer_encodes",
    "tokenizer_constructions",
    "checkpoint_downloads",
    "model_weight_loads",
    "model_operations_performed",
)

GATE_ARTIFACTS = (
    "p0_r1_replay_result.json",
    "p0_r1_replay_receipt.json",
    "p0_r1_replay_counters.json",
    "P0_R1_REPLAY_DISPOSITION.md",
)


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    receipt = json.loads(
        _read(os.path.join(args.out_dir, "p0_r1_replay_receipt.json"))
        .decode("utf-8"))

    for field in SCIENTIFIC_ZERO_FIELDS:
        if receipt.get(field):
            sys.stderr.write(
                "FAIL: the replay receipt records %s=%r\n"
                % (field, receipt[field]))
            return 2
    if receipt.get("gpu_allocated"):
        sys.stderr.write(
            "FAIL: the replay receipt records a GPU allocation\n")
        return 2

    transport = json.loads(
        _read(os.path.join(args.out_dir,
                           "p0_r1_replay_transport_receipt.json"))
        .decode("utf-8"))

    if not transport.get("verified"):
        sys.stderr.write(
            "FAIL: the replay artifacts were not verified at rest\n")
        return 2

    objects = {entry["name"]: entry for entry in transport.get("objects", [])}
    for name in GATE_ARTIFACTS:
        if name not in objects:
            sys.stderr.write(
                "FAIL: %s was not transported; a log line is not a result\n"
                % name)
            return 2
        local = _read(os.path.join(args.out_dir, name))
        entry = objects[name]
        if entry["bytes"] != len(local) \
                or entry["sha256"] != hashlib.sha256(local).hexdigest():
            sys.stderr.write(
                "FAIL: %s at rest does not reproduce the bytes the gate wrote\n"
                % name)
            return 2
        print("TRANSPORTED=%s BYTES=%d SHA256=%s"
              % (name, entry["bytes"], entry["sha256"]))

    if receipt.get("authorizes_model_pilot") \
            and not transport.get("authorizes_model_pilot"):
        sys.stderr.write(
            "FAIL: a pass authorization is not backed by a verified transport\n")
        return 2

    print("REPLAY_STATE=%s" % receipt["state"])
    print("REPLAY_PASSED=%s" % receipt["passed"])
    print("REPLAY_ATTEMPT_ID=%s" % receipt["attempt_id"])
    print("AUTHORIZES_MODEL_PILOT=%s" % receipt["authorizes_model_pilot"])
    print("TRANSPORT_VERIFIED=%s" % transport["verified"])
    print("P0_R1_REPLAY_RECEIPT_VERIFIED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
