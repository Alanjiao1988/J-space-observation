"""Emit the Study 3 P0-R1 image self-manifest at image-build time.

Authority:
``studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md``
section 7, which requires verifying that the built image contains the exact
executable code blobs and the operative committed authority.

Why this is a real file rather than an inline heredoc. An ``az acr run`` step
mounts its uploaded source context over ``/workspace``, so a post-build check
that read ``/workspace/studies`` would be reading the task context, not the
image. The identities are therefore recorded under ``/opt``, which the mount
cannot shadow.

The first attempt at this used a ``RUN python - <<'PY'`` heredoc. The ACR
classic Dockerfile front end truncated the instruction at the heredoc opener, so
``python -`` ran with no stdin and the body was silently discarded: the build
reported success while producing nothing. A step that appears to succeed while
doing nothing is worse than a failing one, so the emitter is a copied file that
either runs or fails loudly.
"""

import hashlib
import json
import os
import sys

WORKSPACE = "/workspace"
OUTPUT = "/opt/jspace/p0_r1_image_manifest.json"

BOUND_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_counters.py",
    "studies/study3/pilot/p0_r1/p0_r1_eligibility.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock.py",
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner.py",
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_schemas.py",
    "studies/study3/pilot/p0_r1/p0_r1_summarize.py",
    "studies/study3/pilot/p0_r1/p0_r1_validate.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution.py",
    "studies/study3/pilot/p0_r1/container/requirements-study3-p0-r1.txt",
    "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
    "studies/study3/prompts/"
    "study3_p0_r1_pre_replay_execution_completion_authority_rev2.md",
)


def main():
    manifest = {}
    missing = []
    for relative in BOUND_PATHS:
        full = os.path.join(WORKSPACE, *relative.split("/"))
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
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
    print("wrote %s with %d blob identities" % (OUTPUT, len(manifest)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
