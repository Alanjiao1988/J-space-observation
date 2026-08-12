"""Emit the Study 3 P0-R1 generation-2 image self-manifest at build time.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5 and 11.

The generation-1 emitter recorded blob identities under ``/workspace``. That was
correct as far as it went, but it proved nothing about whether the image could
actually *run*: it never checked that the job command was a real path, and the
source root it recorded was the one an ``az acr run`` context mount shadows.

This emitter records the standalone source root instead, and it fails the build
unless :func:`p0_r1_runtime_binding.verify_standalone_layout` accepts the image:
every bound source file present, every installed entry point present and
executable, and no result or outcome-conditioned byte anywhere inside. An image
that cannot invoke its own job command does not get built.
"""

import hashlib
import json
import os
import sys

SRC = os.environ.get("P0_R1_SRC", "/opt/jspace/src")
OUTPUT = "/opt/jspace/p0_r1_image_manifest_v2.json"

sys.path.insert(0, os.path.join(SRC, "studies", "study3", "pilot", "p0_r1"))

import p0_r1_execution_lock_v2 as LOCK  # noqa: E402
import p0_r1_runtime_binding as RUNTIME  # noqa: E402

BOUND_PATHS = tuple(sorted(
    set(LOCK.EXECUTABLE_CODE_PATHS)
    | {entry["path"] for entry in LOCK.AUTHORITIES}
    | {"studies/study3/pilot/p0/corpus/p0_corpus.json"}))


def main():
    manifest = {}
    missing = []
    for relative in BOUND_PATHS:
        full = os.path.join(SRC, *relative.split("/"))
        if not os.path.exists(full):
            missing.append(relative)
            continue
        with open(full, "rb") as handle:
            raw = handle.read()
        manifest[relative] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    if missing:
        sys.stderr.write(
            "FAIL: the image does not carry %s\n" % ", ".join(missing))
        return 2

    for entry in LOCK.AUTHORITIES:
        observed = manifest[entry["path"]]
        if observed["sha256"] != entry["sha256"] \
                or observed["bytes"] != entry["bytes"]:
            sys.stderr.write(
                "FAIL: %s inside the image does not reproduce its registered "
                "identity\n" % entry["path"])
            return 2

    try:
        layout = RUNTIME.verify_standalone_layout(src=SRC)
    except RUNTIME.RuntimeBindingDefect as exc:
        sys.stderr.write("FAIL: %s\n" % exc)
        return 2

    document = {
        "schema_version": "study3-p0-r1-image-manifest-v2",
        "standalone_source_root": SRC,
        "layout": layout,
        "authorities": [dict(entry) for entry in LOCK.AUTHORITIES],
        "blobs": manifest,
        "carries_no_result_and_no_outcome_conditioned_byte": True,
        "depends_on_the_acr_workspace_mount": False,
    }
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as handle:
        json.dump(document, handle, indent=1, sort_keys=True)
    print("wrote %s with %d blob identities" % (OUTPUT, len(manifest)))
    print("standalone source root %s; %d entry points verified"
          % (SRC, len(layout["entrypoints"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
