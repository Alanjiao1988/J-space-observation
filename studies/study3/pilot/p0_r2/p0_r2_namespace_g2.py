#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 namespace and byte-verified primitive reuse.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 4, 5 and 6.1.

Section 4 requires a disjoint generation-2 namespace. Section 5 forbids changing
the reused logic. Section 6.1 permits importing an existing immutable shared
primitive **byte-for-byte** rather than authoring a new one.

The generation-1 transport, journal and blob primitives satisfy every
generation-2 requirement except one: each binds ``p0r2-g1-`` and
``study3/p0_r2/g1`` as a module constant, and generation 2 may not write into
generation 1's namespace.

This module resolves that without editing or copying a single frozen byte. It
reads the frozen source, verifies its SHA-256 against the value the caller
binds, executes those exact bytes into a **separate** module object, and rebinds
only the namespace constants. The generation-1 module object already in
``sys.modules`` is never mutated, so nothing generation 1 published can change
behaviour underneath it, and the executed logic is byte-identical by
construction.

Model-free. No tokenizer, checkpoint, model weight, GPU or scoring operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import types


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))


SCHEMA_VERSION = "study3-p0-r2-namespace-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

PREFIX_ROOT = "study3/p0_r2/g2"
ATTEMPT_ID_PREFIX = "p0r2-g2-"

GENERATION1_PREFIX_ROOT = "study3/p0_r2/g1"
GENERATION1_ATTEMPT_ID_PREFIX = "p0r2-g1-"

LIVE_ATTEMPT_PREFIX = "p0r2-g2-live-"
PILOT_ATTEMPT_PREFIX = "p0r2-g2-pilot-"
CANARY_ATTEMPT_PREFIX = "p0r2-g2-canary-"

GPU_JOB = "job-jspace-s3-p0r2-pilot-g2"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g2"
PREFIX_JOB = "job-jspace-s3-p0r2-prefix-g2"
HARD_KILL_JOB = "job-jspace-s3-p0r2-hardkill-g2"

RESULTS_ROOT = "studies/study3/pilot/p0/results/p0-r2-g2"

#: The frozen generation-1 primitives generation 2 re-executes unchanged, and
#: the module-level names rebound in each generation-2 instance. A name that
#: resolves to a module is rebound to that module's generation-2 instance, so a
#: reused primitive never reaches back into generation 1's namespace.
REUSED_PRIMITIVES = {
    "p0_r2_transport": ("ATTEMPT_ID_PREFIX",),
    "p0_r2_transport_v1": ("BASE",),
    "p0_r2_blob_transport": ("ATTEMPT_ID_PREFIX", "PREFIX_ROOT"),
    "p0_r2_blob_transport_v1": ("PREFIX_ROOT", "BLOB"),
    "p0_r2_journal_v1": ("ATTEMPT_ID_PREFIX",),
    "p0_r2_recovery_v1": ("RECOVERY_JOB", "BLOB", "JOURNAL"),
    "p0_r2_hard_kill_canary_v2": ("ATTEMPT_PREFIX", "BLOB", "JOURNAL",
                                  "RECOVERY"),
}

#: Scalar rebinds. Module rebinds are resolved by :func:`_module_override`.
_SCALAR_OVERRIDES = {
    "ATTEMPT_ID_PREFIX": ATTEMPT_ID_PREFIX,
    "PREFIX_ROOT": PREFIX_ROOT,
    "RECOVERY_JOB": RECOVERY_JOB,
    "ATTEMPT_PREFIX": CANARY_ATTEMPT_PREFIX + "hardkill-",
}

#: Names whose generation-2 value is another generation-2 instance.
_MODULE_OVERRIDES = {
    "BASE": "p0_r2_transport",
    "BLOB": "p0_r2_blob_transport",
    "JOURNAL": "p0_r2_journal_v1",
    "TRANSPORT": "p0_r2_transport",
    "RECOVERY": "p0_r2_recovery_v1",
}

_SHA256 = __import__("re").compile(r"^[0-9a-f]{64}$")

_INSTANCES: dict = {}


class NamespaceDefect(Exception):
    """A generation-2 namespace or reuse stop."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_identity(module_name: str) -> dict:
    path = P0_R2_DIR / (module_name + ".py")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise NamespaceDefect("%s is unreadable: %s" % (module_name, exc))
    return {
        "module": module_name,
        "path": "studies/study3/pilot/p0_r2/%s.py" % module_name,
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }


def instantiate(module_name: str, *, expected_sha256=None):
    """Execute a frozen generation-1 primitive as a generation-2 instance.

    The bytes executed are exactly the committed bytes. Only the namespace
    constants named in :data:`REUSED_PRIMITIVES` are rebound afterwards, and
    only to generation-2 values.
    """
    if module_name not in REUSED_PRIMITIVES:
        raise NamespaceDefect(
            "%r is not a registered reusable primitive" % module_name)
    cached = _INSTANCES.get(module_name)
    if cached is not None:
        return cached

    path = P0_R2_DIR / (module_name + ".py")
    payload = path.read_bytes()
    actual = _sha256(payload)
    if expected_sha256 is not None:
        if not _SHA256.match(str(expected_sha256)):
            raise NamespaceDefect(
                "the expected SHA-256 for %s is malformed" % module_name)
        if actual != expected_sha256:
            raise NamespaceDefect(
                "%s is sha256 %s, not the bound %s; generation 2 refuses to "
                "execute a primitive whose bytes are not the bound bytes"
                % (module_name, actual, expected_sha256))

    instance = types.ModuleType("%s__g2" % module_name)
    instance.__file__ = str(path)
    instance.__dict__["__name__"] = "%s__g2" % module_name
    exec(compile(payload, str(path), "exec"), instance.__dict__)  # noqa: S102

    rebound = {}
    for constant in REUSED_PRIMITIVES[module_name]:
        if not hasattr(instance, constant):
            raise NamespaceDefect(
                "%s does not define %s; the reuse contract is broken"
                % (module_name, constant))
        previous = getattr(instance, constant)
        if constant in _MODULE_OVERRIDES:
            target = _MODULE_OVERRIDES[constant]
            replacement = instantiate(target)
            if getattr(previous, "__name__", None) not in (
                    target, "%s__g2" % target):
                raise NamespaceDefect(
                    "%s.%s does not reference %s; the reuse contract is broken"
                    % (module_name, constant, target))
            setattr(instance, constant, replacement)
            rebound[constant] = {
                "generation1": target,
                "generation2": "%s__g2" % target,
            }
            continue
        replacement = _SCALAR_OVERRIDES[constant]
        if previous == replacement:
            raise NamespaceDefect(
                "%s.%s is already the generation-2 value; the frozen "
                "generation-1 primitive was expected" % (module_name, constant))
        setattr(instance, constant, replacement)
        rebound[constant] = {"generation1": previous, "generation2": replacement}

    instance.__p0_r2_generation__ = GENERATION
    instance.__p0_r2_source_sha256__ = actual
    instance.__p0_r2_rebound__ = rebound
    _INSTANCES[module_name] = instance
    return instance


def transport():
    return instantiate("p0_r2_transport")


def strict_decoder():
    return instantiate("p0_r2_transport_v1")


def blob_transport():
    return instantiate("p0_r2_blob_transport")


def journal():
    return instantiate("p0_r2_journal_v1")


def recovery():
    return instantiate("p0_r2_recovery_v1")


def hard_kill_canary():
    return instantiate("p0_r2_hard_kill_canary_v2")


def attempt_prefix(attempt_id: str) -> str:
    if not isinstance(attempt_id, str) or not attempt_id:
        raise NamespaceDefect("an attempt prefix requires an attempt id")
    if attempt_id.startswith(GENERATION1_ATTEMPT_ID_PREFIX):
        raise NamespaceDefect(
            "attempt id %r belongs to the closed generation 1" % attempt_id)
    if not attempt_id.startswith(ATTEMPT_ID_PREFIX):
        raise NamespaceDefect(
            "attempt id %r does not begin with %r"
            % (attempt_id, ATTEMPT_ID_PREFIX))
    return "%s/%s/" % (PREFIX_ROOT, attempt_id)


def assert_disjoint_from_generation1(values) -> bool:
    """Refuse any generation-1 identifier reaching a generation-2 path."""
    for value in values:
        if not isinstance(value, str):
            continue
        if GENERATION1_ATTEMPT_ID_PREFIX in value \
                or GENERATION1_PREFIX_ROOT in value:
            raise NamespaceDefect(
                "%r carries a generation-1 identifier; the namespaces are "
                "disjoint" % value)
    return True


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_namespace_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "prefix_root": PREFIX_ROOT,
        "attempt_id_prefix": ATTEMPT_ID_PREFIX,
        "live_attempt_prefix": LIVE_ATTEMPT_PREFIX,
        "pilot_attempt_prefix": PILOT_ATTEMPT_PREFIX,
        "canary_attempt_prefix": CANARY_ATTEMPT_PREFIX,
        "gpu_job": GPU_JOB,
        "recovery_job": RECOVERY_JOB,
        "prefix_job": PREFIX_JOB,
        "hard_kill_job": HARD_KILL_JOB,
        "results_root": RESULTS_ROOT,
        "reused_primitives": sorted(REUSED_PRIMITIVES),
        "reused_primitive_identities": [source_identity(name)
                                        for name in sorted(REUSED_PRIMITIVES)],
        "edits_generation1_bytes": False,
        "mutates_generation1_modules": False,
        "generation1_prefix_root": GENERATION1_PREFIX_ROOT,
        "generation1_attempt_id_prefix": GENERATION1_ATTEMPT_ID_PREFIX,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        import p0_r2_transport as G1TX  # noqa: E402

        g2 = transport()
        if g2.ATTEMPT_ID_PREFIX != ATTEMPT_ID_PREFIX:
            raise NamespaceDefect("the generation-2 transport was not rebound")
        if G1TX.ATTEMPT_ID_PREFIX != GENERATION1_ATTEMPT_ID_PREFIX:
            raise NamespaceDefect(
                "the generation-1 transport module was mutated")
        blob = blob_transport()
        if blob.PREFIX_ROOT != PREFIX_ROOT:
            raise NamespaceDefect("the generation-2 blob root was not rebound")
        jour = journal()
        if jour.ATTEMPT_ID_PREFIX != ATTEMPT_ID_PREFIX:
            raise NamespaceDefect("the generation-2 journal was not rebound")
        probe = "%slive-selfcheck" % ATTEMPT_ID_PREFIX
        g2.validate_attempt_id(probe)
        if blob.attempt_prefix(probe) != attempt_prefix(probe):
            raise NamespaceDefect("the two prefix derivations disagree")
        decoder = strict_decoder()
        if decoder.BASE is not g2:
            raise NamespaceDefect(
                "the strict decoder is not bound to the generation-2 transport")
        fixture = g2.canary_fixture(probe)
        recovered, repairs = decoder.recover_with_report(
            "\n".join(g2.encode(probe, fixture)), probe)
        if repairs or any(recovered[name] != payload
                          for name, payload in fixture.items()):
            raise NamespaceDefect(
                "the generation-2 envelope did not round trip byte-exactly")
        recover = recovery()
        if recover.RECOVERY_JOB != RECOVERY_JOB:
            raise NamespaceDefect("the recovery job was not rebound")
        hardkill = hard_kill_canary()
        if not hardkill.ATTEMPT_PREFIX.startswith(CANARY_ATTEMPT_PREFIX):
            raise NamespaceDefect("the hard-kill attempt prefix was not rebound")
        try:
            G1TX.validate_attempt_id(probe)
        except G1TX.TransportDefect:
            pass
        else:
            raise NamespaceDefect(
                "the generation-1 transport accepted a generation-2 attempt")
    except NamespaceDefect as exc:
        print("P0_R2_G2_NAMESPACE_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    print("P0_R2_G2_NAMESPACE_SELF_CHECK=1")
    print("P0_R2_G2_PREFIX_ROOT=%s" % PREFIX_ROOT)
    print("P0_R2_G2_ATTEMPT_ID_PREFIX=%s" % ATTEMPT_ID_PREFIX)
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
