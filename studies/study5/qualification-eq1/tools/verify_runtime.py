#!/usr/bin/env python3
"""Verify that the Study 5-EQ1 runtime can do what the phase plan needs.

This runs as a build layer, so a missing capability breaks the image rather than
a phase. It exists as a file, deliberately: the first version of this check was
written as a ``RUN python - <<'PY'`` heredoc, and the classic Docker builder
does not support heredocs, so ``python -`` ran with empty stdin, exited 0 and
the build passed without executing a single assertion. A check that cannot fail
is worse than no check, because it manufactures confidence. Keeping it in a
COPY-ed file makes that failure mode impossible.

It asserts the registered versions, the jlens API surface named in authority
4.2, and the two capabilities later phases depend on.
"""

from __future__ import annotations

import importlib.metadata as metadata
import inspect
import sys

EXPECTED_VERSIONS = {
    "jlens": "0.1.0",
    "torch": "2.12.0",
    "transformers": "5.9.0",
    "numpy": "2.4.6",
    "sympy": "1.14.0",
    "safetensors": "0.7.0",
}


def main() -> int:
    failures: list[str] = []

    for package, expected in EXPECTED_VERSIONS.items():
        actual = metadata.version(package)
        if actual != expected:
            failures.append(f"{package} is {actual}, expected {expected}")

    import jlens

    # Authority 4.2 names fit(), apply() and merge(). They are not all in the
    # same place: fit() is module level, apply() is an instance method and
    # merge() is a classmethod. `callable()` over `vars()` misses a classmethod
    # on Python 3.11, so membership is tested with getattr rather than by
    # filtering a namespace -- an earlier probe using the latter reported
    # merge() as absent when it is present.
    if not callable(getattr(jlens, "fit", None)):
        failures.append("jlens.fit is missing")
    for name in ("apply", "merge", "transport"):
        if not callable(getattr(jlens.JacobianLens, name, None)):
            failures.append(f"jlens.JacobianLens.{name} is missing")

    merge = getattr(jlens.JacobianLens, "merge", None)
    if merge is not None:
        params = list(inspect.signature(merge).parameters)
        if not params:
            failures.append("JacobianLens.merge takes no lenses to merge")

    # Authority 6.3 matches controls by one-to-one optimal assignment.
    try:
        from scipy.optimize import linear_sum_assignment  # noqa: F401
    except Exception as exc:  # pragma: no cover - build-time guard
        failures.append(f"scipy.optimize.linear_sum_assignment unavailable: {exc}")

    # Authority 3.6 decides answer equivalence with a frozen symbolic checker.
    import sympy

    if sympy.simplify(sympy.sympify("2*(x+1)") - sympy.sympify("2*x+2")) != 0:
        failures.append("sympy failed to decide a trivial equivalence")

    # Authority 8 requires bf16 and forbids quantisation; the dtype must exist
    # even when the build host exposes no GPU.
    import torch

    if not hasattr(torch, "bfloat16"):
        failures.append("torch has no bfloat16 dtype")

    # Authority 8 forbids trust_remote_code, so the target architecture must be
    # supported natively by the pinned transformers.
    from transformers import AutoConfig, AutoModelForCausalLM  # noqa: F401
    from transformers.models.qwen2 import Qwen2Config  # noqa: F401

    if failures:
        for failure in failures:
            print(f"RUNTIME VERIFICATION FAILED: {failure}", file=sys.stderr)
        return 1

    print("jlens", metadata.version("jlens"))
    print("torch", metadata.version("torch"))
    print("transformers", metadata.version("transformers"))
    print("numpy", metadata.version("numpy"))
    print("scipy", metadata.version("scipy"))
    print("sympy", metadata.version("sympy"))
    print("jlens api: fit, JacobianLens.apply, JacobianLens.merge, .transport")
    print("RUNTIME VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
