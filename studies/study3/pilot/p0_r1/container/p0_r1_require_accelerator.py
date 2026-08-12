"""Require exactly one accelerator before the P0-R1 model pilot proceeds.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5 and 9.

The mirror image of ``p0_r1_no_accelerator_probe.py``: the replay gate refuses to
run *with* an accelerator, and the model pilot refuses to run *without* one. A
CPU-only fallback would silently change what the pilot measures, so it is refused
rather than tolerated.

This file lives in ``container/`` rather than the stage directory so the
registered static model-free scan over ``studies/study3/pilot/p0_r1/*.py``
remains exact. Reaching it already requires a passed replay gate, a validated
lock and a validated receipt.
"""

import sys


def main():
    import torch

    count = torch.cuda.device_count()
    available = torch.cuda.is_available()
    print("GPU_COUNT=%d" % count)
    print("CUDA_AVAILABLE=%s" % available)
    print("TORCH_VERSION=%s" % torch.__version__)

    if not available or count < 1:
        sys.stderr.write(
            "FAIL: the P0-R1 model pilot requires one Azure GPU; a CPU fallback "
            "would not measure what the pilot registered\n")
        return 2
    if count != 1:
        sys.stderr.write(
            "FAIL: the registered pilot allocates exactly one GPU, not %d\n"
            % count)
        return 2

    print("DEVICE_NAME=%s" % torch.cuda.get_device_name(0))
    print("P0_R1_ACCELERATOR_PRESENT=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
