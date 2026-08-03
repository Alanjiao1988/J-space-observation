"""Execution wrapper for the Phase 1.0D semantic review.

Why this is a subpackage rather than
``src/jspace_observation/phase1_0d_semantic_review.py``, which is the name the
authority suggests: ``phase1_0d_build_provenance.json`` is a protected record
that hashes the bundle resolved from ``src/jspace_observation/*.py``, and its
own generator hashes itself into that bundle.  A module placed directly beside
the frozen ones would change the recorded bundle digest, and neither the record
nor its generator may be re-emitted.  A subpackage sits outside that
non-recursive pattern, so the frozen build record keeps describing exactly the
bytes that are inside the locked generation image.

Everything here is orchestration.  The scientific decisions -- selection,
eligibility, the strict-no-CoT rule, cell outcomes, the pass gate -- stay in the
frozen protected modules and are called, never reimplemented.
"""

from __future__ import annotations
