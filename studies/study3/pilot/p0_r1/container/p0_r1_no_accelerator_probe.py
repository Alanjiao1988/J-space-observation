"""Refuse to continue if any accelerator is visible to a model-free stage.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5 and 6.

Generation 1 inlined this as a Dockerfile-adjacent heredoc. A copied script file
is used instead because the ACR classic Dockerfile front end silently truncates
``RUN python - <<'PY'`` heredocs, and because a file can be hashed into the image
manifest and bound by the execution lock while a heredoc cannot.

This probe names the accelerator library only to prove its absence, and it is
carried in ``container/`` rather than the stage directory so the registered
static model-free scan over ``studies/study3/pilot/p0_r1/*.py`` stays exact.
"""

import sys


def main():
    modules = sys.modules
    try:
        import torch
    except ImportError:
        count, available = 0, False
    else:
        count = torch.cuda.device_count()
        available = torch.cuda.is_available()

    print("GPU_COUNT=%d" % count)
    print("CUDA_AVAILABLE=%s" % available)
    if count or available:
        sys.stderr.write(
            "FAIL: an accelerator is visible to a model-free stage\n")
        return 2

    for name in ("transformers", "tokenizers"):
        if name in modules:
            sys.stderr.write(
                "FAIL: %s was imported before a model-free stage\n" % name)
            return 2

    print("ACCELERATOR_VISIBLE=false")
    print("P0_R1_NO_ACCELERATOR_PROBE=passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
