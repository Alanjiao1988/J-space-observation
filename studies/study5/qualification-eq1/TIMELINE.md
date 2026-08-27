# Study 5-EQ1 — execution timeline

Authority: `studies/study5/prompts/study5_eq1_qualification_authority.md`
Branch: `alanjiao1988-study5-eq1-qualification`, off
`dac07a695e9cf820fcf3546ccff24826d3e47a30`.

All times are UTC. This file is the human-readable half of the run record
required by authority §9.2. Every failure, retry, degraded condition and skipped
step appears here. Suppressing one is a governance violation, so nothing is
omitted for being unflattering.

Machine-readable counterpart: `journal/*.jsonl` (§9.1). The exact command text
behind each journal record is committed under `journal/commands/`, so
`command_sha256` in a record can be recomputed rather than trusted.

Nothing in this file is a scientific result.

---

## P-BOOT — authority publication and run-record instrument

Pre-P-0 bootstrap. Zero Azure API calls, zero model calls, zero GPU seconds.

### 2026-08-27T00:13:51Z → 00:17:21Z — `BOOT-001` — establish the branch, publish the authority alone

Refetched all remotes and resolved the registered predecessor.
`origin/alanjiao1988-azure-mooncake-a100-vm` was at
`dac07a695e9cf820fcf3546ccff24826d3e47a30`, exactly the commit registered in
authority §0, and `origin/main` was at `ddf592010cd8788b637a90a998724f7ccdce4383`.
Neither had advanced, so hard blocker 11 did not fire.

The session's worktree branch had been created off `main`, not off the Mooncake
branch. It was reset to the predecessor commit before anything was written. This
is recorded rather than glossed: the branch was local-only with no upstream and
had no commits of its own, so repointing it rewrote no published history and
touched no other worktree. Had it been published, this would have been a stop.

The authority text was **not retyped**. Lines 114–712 of the operator-approved
message were sliced mechanically, joined with LF, and written as UTF-8 without
BOM with a single trailing newline. The result was then read back and compared
line-for-line against the source slice: 599 lines, **0 mismatches**. A separate
check confirmed that the operator's Chinese framing text around the authority
(the covering instructions and the `附：authority 全文` header) did not leak into
the normative file.

    bytes   29,485
    lines   599
    sha256  5c45d31a2aab23ffe93bbf5f4a220fb1835c1b98e960a2588fa587efcb9b1a35

Staged the single path and confirmed the staged set contained exactly one entry
before committing, per authority §13.

    commit  d8467e8854398f69e1de894e7a3d0663d38f7582
    parent  dac07a695e9cf820fcf3546ccff24826d3e47a30
    paths   1

### 2026-08-27T00:17:21Z → 00:18:36Z — `BOOT-002` — publish, re-verifying non-advancement

Authority §13 requires the predecessor branch and `origin/main` to be refetched
immediately before every publication. Refetched: predecessor still
`dac07a6…`, `origin/main` still `ddf5920…`. Neither advanced.

Pushed as a new remote branch. No merge, no rebase, no force-push, no history
rewrite, and `main` was not advanced. Remote head verified as
`d8467e8854398f69e1de894e7a3d0663d38f7582`.

### 2026-08-27T00:18:36Z → 00:22:00Z — `BOOT-003` — build the run-record instrument

Built `tools/journal.py`, the append-only journal required by §9.1, and its test
suite. Gate Q-7 requires create-only journaling to be *demonstrated*, so the
tests assert the failure modes and not only the happy path:

* a repeated journal key raises and appends **nothing** to the file;
* the same `step_id` under a different phase is a distinct key, so phases do not
  collide by accident;
* a duplicate key smuggled into a second phase file is still detected, because
  uniqueness is checked across the whole namespace and not per file;
* an earlier record is byte-identical after later appends — records are never
  rewritten;
* a truncated journal still verifies as a complete prefix, which is the property
  that makes an interrupted run analysable;
* malformed JSON is an integrity error, never a silent skip;
* `gpu_seconds` roll up into accelerator-hours against the 240 h ceiling;
* `blocker_id` values are surfaced by `verify`, so a blocker cannot be recorded
  and then quietly lost.

Records are `fsync`-ed before the next step is allowed to begin.

    10 passed in 0.22s

Journal state after P-BOOT: 3 records, 3 unique keys, 0 duplicates, rollup
`bf5533e69bf689730e31e48c60d9db399859a4d8513ece95eb45e7f1760c73aa`.

### 2026-08-27T00:22:00Z → 00:31:00Z — `BOOT-004` — inherited governance tests, and one disclosed pre-existing failure

Ran the inherited governance tests that could plausibly be disturbed by a new
namespace and a new `.gitattributes` block, together with the new journal tests:

    tests/test_paper_registries.py
    tests/test_phase1_0d_protected_bytes.py
    tests/test_phase1_0d_rv2_protected_bytes.py
    studies/study5/qualification-eq1/tests/

    62 passed, 1 failed

**The failure is disclosed rather than fixed, and it is not caused by this
invocation.**

`tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup`
fails on the operator workstation. The same test was then run on a clean
detached checkout of the predecessor commit `dac07a6…`, with no Study 5 byte
present, and it failed there identically, producing byte-identical hashes
(`ff7e1b97…` vs `24999528…`) in both runs. The temporary checkout was removed
afterwards.

Cause: the test's `_tiny_tree` fixture writes with `Path.write_text(...,
encoding="utf-8")` and no `newline=""`. On Windows, Python's text mode already
translates `\n` to `\r\n`, so the tree the test calls "lf" is CRLF on disk;
the test then rewrites `\n` as `\r\n` in the second tree, yielding `\r\r\n`.
The two trees therefore differ in bytes and the rollup correctly differs. The
test's own premise is violated by the platform. It is a Windows-only test
defect, not a repository defect and not a protected-bytes regression.

Not repaired, deliberately. Authority §13 forbids weakening a historical test,
and §11 forbids modifying Phase 1.0D bytes. Fixing it would also be outside this
authority's scope. Recorded here as a degraded condition per §12, which requires
everything short of a hard blocker to be worked around and recorded rather than
escalated.

The governance-relevant assertion in the same file,
`test_the_committed_baseline_still_describes_this_repository`, **passed**:
protected bytes have not moved. `tests/test_paper_registries.py` passed, so the
evidence ledger is intact at `EV-0016`.

### Environment observed during P-BOOT

Local operator workstation only; the Mooncake hosts were not contacted.

    python  3.13.15
    az      2.83.0
    gh      2.96.0

### P-BOOT outcome

No gate is decided by P-BOOT. Q-7 is in progress: the journaling half of it is
demonstrated, the confirmation-split isolation half cannot be until the split is
frozen at P-0.

No hard blocker. One disclosed degraded condition (`BOOT-004`, a pre-existing
Windows-only failure in an inherited Phase 1.0D test). No Azure call. No model
call. 0 GPU seconds. 0 of 240 accelerator hours consumed.

---

## P-0 — pending

Not started. Requires: read-only opening Azure inventory snapshot, GPQA access
resolution before any model call, acquisition and byte-verification of
`Qwen2.5-Math-7B` and both adapters into content-addressed paths, container
image build with a frozen digest, frozen benchmark development/confirmation
split, and the contamination check against OpenThoughts3-55k. Gates Q-1 and Q-2.
Accelerator budget 0 h.
