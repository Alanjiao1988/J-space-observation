"""Validate every generation-2 launch input before a model operation is possible.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5, 8 and 9.

Generation 1 discovered its binding defects only after the container had started,
which is the most expensive moment to discover them: a GPU replica is already
allocated and the operator is already paying for it. Worse, the failure looked
like an infrastructure hiccup, which is exactly the shape that invites a retry.

This guard moves the whole decision earlier. It runs before the accelerator probe
and before any model library is imported, and it delegates to
:func:`p0_r1_runtime_binding.validate_launch_inputs` so the launcher on the
outside and the entry point on the inside apply one identical rule rather than
two drifting approximations of it.

It performs zero tokenizer, checkpoint, model and GPU operations.
"""

import argparse
import json
import os
import sys


def _load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-file")
    parser.add_argument("--receipt-file", required=True)
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    parser.add_argument("--src")
    parser.add_argument("--print-attempt-id", action="store_true")
    args = parser.parse_args(argv)

    src = args.src or os.environ.get("P0_R1_SRC", "/opt/jspace/src")
    sys.path.insert(0, os.path.join(src, "studies", "study3", "pilot", "p0_r1"))
    import p0_r1_runtime_binding as RUNTIME

    receipt = _load(args.receipt_file)

    if args.print_attempt_id:
        sys.stdout.write(receipt["attempt_id"])
        return 0

    if not args.lock_file:
        sys.stderr.write("FAIL: --lock-file is required\n")
        return 2

    lock = _load(args.lock_file)
    lock_bytes = _read_bytes(args.lock_file)
    receipt_bytes = _read_bytes(args.receipt_file)
    try:
        report = RUNTIME.validate_launch_inputs(
            lock, receipt, args.image_digest, args.ready_commit,
            lock_bytes=lock_bytes, receipt_bytes=receipt_bytes, root=src)
    except RUNTIME.RuntimeBindingDefect as exc:
        print("P0_R1_LAUNCH_REFUSED=1")
        print("  FAIL %s" % exc)
        return 1

    for key in sorted(report):
        print("  %-40s %s" % (key, report[key]))
    print("P0_R1_LAUNCH_INPUTS_VALIDATED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
