"""Verify the Study 3-P0 image context from inside the image build.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
section 6, which requires the container/build definition to carry frozen
dependencies and the P0 artifacts to be identity-checked before execution.

The build calls this. If any check is false there is no image, so an image can
never exist that carries a mutated authority, a mutated frozen corpus or a
mutated protocol document. It is deliberately import-light and standard library
only, so it cannot fail for a reason unrelated to what it checks.

Usage::

    python p0_image_verify.py --project-root /workspace
"""

import argparse
import hashlib
import os
import sys

REGISTERED_AUTHORITY_SHA256 = (
    "80efc7ef8bfe5e3b5e5235f530a44730f185187aa52b85945875fe68ef1eda11")
REGISTERED_AUTHORITY_BYTES = 29282

AUTHORITY_REL = (
    "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md")
REGISTRY_REL = (
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json")
PROTOCOL_REL = (
    "studies/study3/protocol/interface_calibration_protocol_draft.json")

# Nothing about a checkpoint, a tokenizer or a result may be baked into the
# image. These names must not appear as files in the build context.
FORBIDDEN_BAKED = (
    "p0_tokenizer_gate_result.json",
    "p0_tokenizer_gate_receipt.json",
    "p0_model_pilot_result.json",
    "p0_model_pilot_receipt.json",
    "p0_descriptive_summary.json",
)


def fail(message):
    print("[FAIL] " + message)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default="/workspace")
    args = parser.parse_args(argv)
    root = args.project_root

    authority = os.path.join(root, AUTHORITY_REL)
    if not os.path.exists(authority):
        return fail("the authority copy is missing from the image context")
    with open(authority, "rb") as handle:
        raw = handle.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != REGISTERED_AUTHORITY_SHA256:
        return fail("authority sha256 %s != registered %s"
                    % (digest, REGISTERED_AUTHORITY_SHA256))
    if len(raw) != REGISTERED_AUTHORITY_BYTES:
        return fail("authority is %d bytes, not the registered %d"
                    % (len(raw), REGISTERED_AUTHORITY_BYTES))
    if b"\r" in raw:
        return fail("the authority copy carries CR; LF only is registered")

    for rel in (REGISTRY_REL, PROTOCOL_REL):
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            return fail("binding input missing from the image context: %s" % rel)

    p0_dir = os.path.join(root, "studies", "study3", "pilot", "p0")
    for dirpath, _dirnames, filenames in os.walk(p0_dir):
        for name in filenames:
            if name in FORBIDDEN_BAKED:
                return fail(
                    "a P0 result artifact is baked into the image: %s"
                    % os.path.join(dirpath, name))

    print("[OK] authority sha256 verified inside the image: %s" % digest)
    print("[OK] binding registry and protocol present")
    print("[OK] no P0 result artifact is baked into the image")
    return 0


if __name__ == "__main__":
    sys.exit(main())
