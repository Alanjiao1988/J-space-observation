# draft-v0.7 review-head test-count reconciliation

> **State:** `STUDY3_V0_7_REVIEW_HEAD_TEST_COUNT_RECONCILED`
>
> This is a **provenance reconciliation**, not a revision of the methods verdict.
> The governing verdict remains `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`
> with **12 BLOCKING, 3 MAJOR and 2 MINOR** findings. No committed
> independent-review artifact — report, JSON, schema, recalculation, receipt or
> tests — was edited, and **zero** review artifacts were modified.

| item | value |
| --- | --- |
| machine-readable form | [`v0_7_review_head_test_count_reconciliation.json`](v0_7_review_head_test_count_reconciliation.json) |
| schema | [`v0_7_review_head_test_count_reconciliation.schema.json`](v0_7_review_head_test_count_reconciliation.schema.json) |
| authority | [`../prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`](../prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md) |

## 1. The two counts, and what each describes

Two different full-suite counts appear in the draft-v0.7 review record. They are
not in conflict; they describe **two different commits**.

| count | commit | total collected | quoted from |
| --- | --- | ---: | --- |
| `7 failed, 4,926 passed, 16 skipped` | `459d002442641039196ac3880d47a45a3b79a4c8` — the **reviewed target** | **4,949** | the committed independent-review artifacts (`v0_7_single_focused_methods_review.json` → `full_suite_differential.review_head_result`, the review report §4, and `methods_review_receipt_v0_7.json`) |
| `7 failed, 4,958 passed, 16 skipped` | `a08ec1462f023da49247cac0756b7af5f32ba75a` — the **final review head** | **4,981** | the review's terminal disclosure |

The committed artifacts label their count `review_head_result`. That label is
imprecise: the run it records was executed against the reviewed target
`459d002…`, before the review's own test module existed. The number is correct
for the commit it was measured on; only the label is loose. That label lives
inside an immutable independent-review artifact which this authority forbids
editing, so it is reconciled here rather than corrected there.

## 2. Independent rerun

Executed for this reconciliation in a clean detached `git worktree` checked out
at exactly `a08ec1462f023da49247cac0756b7af5f32ba75a`, with `git status` empty
before and after:

```
python -m pytest -q -p no:randomly
```

| property | value |
| --- | --- |
| commit under test | `a08ec1462f023da49247cac0756b7af5f32ba75a` |
| Python | 3.13.15 |
| pytest | 9.0.2 |
| OS | Windows |
| random-order plugin | disabled with `-p no:randomly` |

Verbatim result:

```
8 failed, 4957 passed, 16 skipped, 2 warnings in 1392.72s (0:23:12)
```

**Total collected: 8 + 4,957 + 16 = 4,981.** This matches the terminal
disclosure's total collected exactly. The pass/fail split differs by one test;
§4 disposes of that difference.

## 3. Accounting for the 32-test difference

The reconciliation subject is the **count** difference between the two commits,
which is a property of the collected total and is unaffected by which tests pass.

| quantity | value |
| --- | ---: |
| total collected at the reviewed target `459d002…` | 4,949 |
| total collected at the review head `a08ec146…`, as disclosed | 4,981 |
| total collected at the review head `a08ec146…`, independently rerun | **4,981** |
| **Δ total collected** | **+32** |

The reviewed target and the review head differ by three commits that add eight
paths and modify none. Exactly one of those paths is a test module:

* `tests/test_study3_v0_7_focused_review.py`, added in `a08ec146…`.

Independently collected:

```
python -m pytest --collect-only -q tests/test_study3_v0_7_focused_review.py
32 tests collected
```

**32 collected − 32 delta = 0 residual.** No other test module was added,
removed, renamed, reparametrized, skipped or unskipped between the two commits.

The 32-test difference is therefore **fully and exactly accounted for**, on both
the disclosed and the independently rerun totals.

## 4. The one extra failure, disclosed and disposed

The rerun reported eight failures rather than seven. Seven are the registered
standing failures, byte-identical at the reviewed target, at the review head and
at the base commit `5b961cb42bada34a88a7895f83ccb2af4e5690e5`:

* `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
* `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix`
* `tests/test_phase1_0d_build_provenance.py::test_the_bundle_digest_ignores_the_checkout_line_endings`
* `tests/test_phase1_0d_generation_launcher_rp_compat.py::test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline`
* `tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup`
* `tests/test_phase1_0d_review_image.py::test_v2_refuses_a_rehashed_record_with_moved_metadata`
* `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only`

All seven are host-checkout line-ending artifacts and none touches a v0.7 path.

The eighth is **`tests/test_study2_stage_bd.py::test_pack_writes_the_core_manifest_last`**,
which is **unstable on this host**, not a new failure:

| probe, same byte-clean worktree at `a08ec146…` | result |
| --- | --- |
| isolated run of the single node id | **1 passed** in 34.22 s |
| isolated run again | **1 passed** in 34.07 s |
| its whole module `tests/test_study2_stage_bd.py` | **54 passed** in 168.52 s |
| inside the loaded full suite | failed |

Mechanism, read from the committed test:

```python
newest = max(tmp_path.iterdir(), key=lambda path: path.stat().st_mtime_ns)
assert newest.name == bd.CORE_MANIFEST_NAME
```

Under a loaded full-suite run several pack files can land inside a single
filesystem timestamp tick, so the manifest ties with an earlier file and `max`
returns whichever entry the directory iterator yields first. This is a host
filesystem timestamp-resolution race, not a defect in the packed bytes.

It belongs to **Study 2**, not Study 3. It does not change the total collected
count, it does not touch any v0.7 path, and it has no bearing on the v0.7
verdict. **This session did not repair it**, because repairing an unrelated
Study 2 test is outside this authority.

## 5. What this addendum does not do

It does not revise, soften, reopen or reweight any finding. It does not change
the severity counts, the verdict or the next legal action. It changes no byte of
the reviewed candidate, of any historical protected path, or of any
independent-review artifact.

`STUDY3_V0_7_REVIEW_HEAD_TEST_COUNT_RECONCILED`
