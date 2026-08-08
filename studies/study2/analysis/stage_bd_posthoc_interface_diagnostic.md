# Stage B-D post-hoc interface diagnostic

**`POST_HOC_DESCRIPTIVE_ZERO_AUTHORITY_NOT_SCIENTIFIC_EVIDENCE`**

This document is a descriptive re-aggregation of already-committed Stage B-D
development rows. It was computed after Gate A failed, it was not pre-registered, it
is not a hypothesis test, it is not an evidence row, and it changes no decision. It
carries zero authority. Nothing here may be cited as a result, a finding, or support
for any claim about the model, the interface, or J-space.

## 1. Why this exists

The Gate A decision document and the Stage B-D final handoff assert that the outcome
is not a measurement artifact. `studies/study2/decisions/study2_stage_bd_interpretation_erratum.md`
narrows that assertion: the frozen analysis excluded execution and bookkeeping
artifacts, not interface or construct-validity artifacts.

This diagnostic exists only to record, in one place, the descriptive response-pattern
facts a future separately authorized protocol would want to see before reusing the
same interface. It does not resolve the erratum's open question. It cannot: protocol
v1 never measured interface adequacy.

## 2. Source and procedure

Single source, read only:

| field | value |
| --- | --- |
| path | `studies/study2/stage_bd/stage_bd_behavioral_development_target.jsonl` |
| bytes | 1002446 |
| sha256 | `9ada004f1c9c25f940e00de7753dd6563e3898153c66099f7b84360aaa8ea34e` |
| rows | 1024 (all `model_role = target`) |
| commit | `43411e09de425dfae0ee74ba46c68a389311e9a7` |
| tree | `c393f395fd499716f5caae6515045483745975bb` |

Counts were **recomputed from these row bytes**, not copied from any summary,
manifest, decision object, or prior document.

The exact procedure was a standard-library re-aggregation over the committed blob.
It reads bytes with `git cat-file blob HEAD:<path>`, verifies the SHA-256 above,
parses each line as JSON, selects rows by the `arm` and `depth` fields, counts
`correct == true`, and tallies the `restricted_prediction` field with
`collections.Counter`:

```python
import collections, hashlib, json, subprocess

raw = subprocess.run(
    ["git", "cat-file", "blob",
     "HEAD:studies/study2/stage_bd/stage_bd_behavioral_development_target.jsonl"],
    capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == (
    "9ada004f1c9c25f940e00de7753dd6563e3898153c66099f7b84360aaa8ea34e")
rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]

def tally(predicate):
    selected = [r for r in rows if predicate(r)]
    counter = collections.Counter(r["restricted_prediction"] for r in selected)
    return (len(selected),
            sum(1 for r in selected if r["correct"]),
            counter["A"], counter["B"], counter["C"], counter["D"])
```

No model was loaded, no tokenizer was constructed, no forward pass was run, no
generation was produced, no activation was extracted, no probe, patch, ablation or
lens operation occurred, no GPU was used, no provider was called, no confirmation
path was read, and no file under `studies/study2/stage_bd/` was modified. The source
rows are byte-identical to their registered state.

## 3. Recomputed counts

`n` is rows in the slice, `correct` is `correct == true`, and A/B/C/D are counts of
`restricted_prediction`.

| slice | n | correct | A | B | C | D |
| --- | --- | --- | --- | --- | --- | --- |
| Gate A decision slice: target, NT, depths 2+3 | 256 | 58 | 106 | 66 | 0 | 84 |
| All target NT, depths 1+2+3 | 384 | 92 | 162 | 99 | 0 | 123 |
| Target PT | 256 | 67 | 12 | 162 | 5 | 77 |
| Target ST | 128 | 34 | 2 | 77 | 4 | 45 |
| Target WT | 256 | 70 | 16 | 158 | 6 | 76 |

Supporting values, recomputed the same way:

| quantity | value |
| --- | --- |
| depth-1 NT correctness | 34 / 128 |
| Gate A slice correctness | 58 / 256 = 0.2265625 |
| NT arm accuracy | 92 / 384 = 0.23958333333333334 |
| PT arm accuracy | 67 / 256 = 0.26171875 |
| ST arm accuracy | 34 / 128 = 0.265625 |
| WT arm accuracy | 70 / 256 = 0.2734375 |

All recomputed values matched the registered expected values exactly, with zero
discrepancies.

## 4. Descriptive observations

These are observations about the recorded response distribution. They are not
findings, not tests, and not effects. No p-value, confidence interval, or inferential
statement is offered or implied, and none may be inferred.

**4.1 Option C was never selected in the no-trace arm.** Across all 384 target NT
rows, at every depth, in both families, the restricted prediction is C exactly zero
times. Under the balanced four-option design, C is the correct label in a quarter of
items, so the interface produced a correct response on those items zero times by
construction.

**4.2 The no-trace arm concentrates on A; the trace-conditioned arms concentrate on
B.** In the NT arm the modal option is A (162 of 384). In PT (162 of 256), ST (77 of
128) and WT (158 of 256) the modal option is B. The shift is large and is associated
with the presence of trace conditioning.

**4.3 The shift does not come with an accuracy gain.** Arm accuracies are 0.2396
(NT), 0.2617 (PT), 0.2656 (ST) and 0.2734 (WT). Every arm sits near the 0.25
restricted-choice chance level. Trace conditioning moved which letter is emitted
without moving accuracy meaningfully.

**4.4 What this is consistent with, and what it is not.** A response distribution
that is strongly non-uniform over option letters, that never emits one of the four
letters in the decision arm, and that reorganizes under trace conditioning without
accuracy change, is consistent with weak or failed binding between the option letters
and the task content - that is, with an interface-level or label-binding concern
rather than a purely capability-level one.

It is also consistent with other explanations, including position or token-level
preference, template interaction, prompt-format effects, and genuine inability at
this model scale. **The cause is not identified and cannot be identified from these
data.** Protocol v1 contains no manipulation that isolates label binding, no
interface-adequacy condition, and no calibration arm. Nothing here distinguishes an
incapable checkpoint from an inadequate instrument.

## 5. What this does not do

- It does not reverse, weaken, qualify, or reopen Gate A. `overall_gate_pass` remains
  `false` and `gate_inputs_sha256` remains
  `1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7`.
- It does not change the primary terminal state
  `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.
- It does not establish that the interface was inadequate, and it does not establish
  that the model was incapable.
- It is not evidence about internal computation, causal mechanism, distillation, or
  J-space validity, none of which was measured.
- It does not authorize protocol v2, interface calibration, a label-binding study,
  Stage B-C, or any mechanistic stage.
- It does not add an evidence row. `paper/evidence_ledger.csv` still ends at
  `EV-0016` and gains nothing from this document.
- It must never be cited as a result. Its only permitted uses are as a limitation and
  as exploratory context for a future, separately authorized protocol.

## 6. Related records

- `studies/study2/decisions/study2_stage_bd_interpretation_erratum.md`
- `studies/study2/decisions/study2_stage_bd_gate_a_decision.md` (frozen)
- `studies/study2/terminal_manifest.json`
- `paper/limitations_ledger.md` - L-89, and L-85 for the pre-existing statement of
  the same boundary
