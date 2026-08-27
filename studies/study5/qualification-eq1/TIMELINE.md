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

## P-0 — acquisition and freeze (in progress)

Gates Q-1 and Q-2. Registered accelerator budget 0 h.

### 2026-08-27T00:31:00Z → 00:40:00Z — `P0-001` — opening read-only Azure inventory

Authority §2 requires a read-only inventory before the first write. It is
captured by `tools/azure_inventory.py`, which is built so the freeze is enforced
by the tool rather than by intent:

* every Azure invocation passes through a whitelist and any mutating verb —
  `start`, `stop`, `deallocate`, `resize`, `delete`, `create`, `update`,
  `role assignment create`, `keys list`, `generate-sas`, or a non-GET
  `az rest` — raises **before** the subprocess is spawned;
* containers are listed through the **management-plane** read, not a data-plane
  call, so no storage key and no SAS is ever needed (§2.8) and no role
  assignment is consulted, let alone changed (§2.9);
* only salted hashes and the §14 published safe names are written. The salt is
  32 fresh random bytes generated outside the repository and is never committed.

**Result — hard blocker 1 does not fire.** Both registered roles resolve
uniquely and both are running, as §2.2 requires:

| Role | Name | Size | Region | Power |
| --- | --- | --- | --- | --- |
| GPU host | `a100-vm` | `Standard_NC96ads_A100_v4` | chinaeast3 | VM running |
| CPU host | `cpuserver` | `Standard_D16ds_v5` | chinanorth3 | VM running |

Cloud `AzureChinaCloud`, subscription ending `8845`, resource group `J-space` —
all matching §14. Exactly one storage account, `s4fm11ca457e105b29b7`, carrying
exactly the six registered containers `models`, `oci`, `runs`, `logs`, `seals`,
`handoff`, every one of them private, with no immutability policy and no legal
hold.

Four unowned `Standard_NC24s_v3` VMs exist in a separate resource group. They
are **not** ours and are not touched. They are recorded as salted hashes rather
than omitted, because a snapshot that ignored them could not detect drift in
them at close, and rather than by name, because they are not published safe
names.

Counters for this step: 0 control-plane writes, 0 data-plane writes, 0 blobs,
0 SAS tokens, 0 storage keys read, 0 role assignments changed, 0 GPU seconds.

One correction, recorded rather than quietly amended: the first capture salted
the resource group of both in-scope VMs, because `az group list` reports
`J-space` while `az vm list` reports `J-SPACE`, and the exact-match redaction
treated the two spellings as different names. Matching is now case-insensitive
and returns the canonical published spelling. The snapshot was re-captured
before being committed, so no superseded snapshot was ever published. The
regression is pinned by a test. Had this survived to the closing snapshot it
would have looked like drift in a resource that had not moved.

The inventory tool carries 47 tests. They assert the two load-bearing
properties directly: that all 24 sampled mutating commands are refused, and
that no raw subscription id, unowned VM name, SAS or account key can reach the
committed snapshot. The §2 drift rule is tested in both directions — a changed
power state, a changed VM size, a new container and a disappeared VM each raise
a hard blocker, while blob count and byte totals are the only tolerated
differences.

**A second correction, and a near-miss worth recording.** The first version of
the leak test asserted that the *real* subscription id was absent from the
snapshot — by embedding the real subscription id in the test file. A test
fixture is a committed artifact like any other, so that would itself have
violated §2.8, which forbids committing a subscription id. A pre-commit scan
across every Study 5 file caught it before anything was staged.

Both tests were rewritten so that neither needs a secret: the salting test uses
a synthetic GUID, and the leak test is now structural, asserting that the
snapshot contains **no GUID-shaped string at all** plus none of the usual
credential markers. That is a stronger check than the original — it would also
catch a tenant id or a resource GUID, which the original would have missed —
and it holds no secret of its own. Recorded rather than silently fixed, because
"the check that enforces the rule broke the rule" is exactly the kind of thing
§9.2 exists to surface.
