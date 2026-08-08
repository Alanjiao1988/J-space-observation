# Study 3 - next thread handoff

**State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW`**

**The only legal next action is operator review of the draft. Not model execution.**

---

## 1. What this round did

- Corrected a clerical changed-path undercount in the Study 2 terminal run-log entry, in a
  separate single-file commit. That correction changed no frozen artifact, no Gate A value, no
  operation count, no evidence row, no interpretation, and neither Study 2 terminal state.
- Created the `studies/study3` namespace with a reviewable interface-calibration design draft,
  a machine-readable twin, a fail-closed structural schema, a traceability analysis, a primary
  source review, this handoff, a design receipt, and the operator authority preserved verbatim.
- Derived every statistical number in the draft by model-free arithmetic using only the Python
  standard library. The formulas are printed in the draft so any reviewer can recompute them.

## 2. What this round did not do

| operation | count |
| --- | --- |
| `model_downloads` | 0 |
| `weight_loads` | 0 |
| `tokenizer_constructions` | 0 |
| `forward_passes` | 0 |
| `generations` | 0 |
| `activation_operations` | 0 |
| `probe_fits` | 0 |
| `patching_operations` | 0 |
| `ablation_operations` | 0 |
| `lens_loads` | 0 |
| `lens_fits` | 0 |
| `lens_applies` | 0 |
| `gpu_jobs` | 0 |
| `provider_calls` | 0 |
| `bank_rows_generated` | 0 |
| `seeds_drawn` | 0 |
| `scientific_evidence_rows` | 0 |

No interface was selected. No threshold was frozen. No bank exists. No seed was drawn. No new
repository was created. Study 1 and Study 2 were not modified in any way.

## 3. Decisions the operator must make

Eight decisions are open. Each has a recommendation and a trade-off. None is buried as a silent
default in the JSON twin.

| id | decision | recommendation | blocking |
| --- | --- | --- | --- |
| `OD1` | Should Study 3 retain all three Study 2 checkpoint roles? | retain all three | no |
| `OD2` | Which positive-capability reference model is defensible and T4-feasible? | do not select one on paper; authorize the separate Stage P3-Q prequalification with a 3B-class candidate first and a ... | **yes - blocks Gate I4** |
| `OD3` | Does bounded final-answer generation (S4) belong in the calibration panel? | keep it, but strictly as a calibration reference and never as the default later surface | no |
| `OD4` | Which prompt-rendering variants are methodologically necessary? | exactly three: the registered baseline plus one separator change and one instruction-wording change | no |
| `OD5` | What accuracy, robustness, equivalence and multiplicity thresholds are acceptable? | I1 null p<=0.90, I2 null p<=0.50, I4 null p<=0.25, equivalence margin 0.05, per-cell alpha 0.005 with Bonferroni with... | yes - blocks freeze |
| `OD6` | What development and confirmation sample sizes should be used? | 192 per cell for development and confirmation, 128 for Gate I4 | yes - blocks freeze |
| `OD7` | Is a bounded independent methods review required before freeze? | yes, bounded to the statistical design and the gate logic, before any bank is generated | no |
| `OD8` | Should a chat template be applied, and to which roles? | no chat template for S1, S2 and S3 on any role; for S4, apply each role's native template or record its absence | no |

### OD1 - Should Study 3 retain all three Study 2 checkpoint roles?

**Recommendation.** retain all three

**Trade-off.** retaining all three roughly triples measurement cost and widens the multiplicity correction, but dropping the lineage base or the instruction control removes the only available contrast for distinguishing an interface effect from an instruction-tuning effect. Dropping the target is not an option if a later study is target-centered.

### OD2 - Which positive-capability reference model is defensible and T4-feasible?

**Recommendation.** do not select one on paper; authorize the separate Stage P3-Q prequalification with a 3B-class candidate first and a 7B-class fallback

**Trade-off.** a 3B-class model fits a T4 comfortably but may itself fail the compositional strata, which would stop the study; a 7B-class model is far more likely to clear them but is tight in fp16 on 16 GiB and may require quantization that alters the logits the interfaces read. Selecting without prequalification risks discovering the failure only after the gate matters.

> Blocking: yes - blocks Gate I4

### OD3 - Does bounded final-answer generation (S4) belong in the calibration panel?

**Recommendation.** keep it, but strictly as a calibration reference and never as the default later surface

**Trade-off.** S4 is the only surface that can express abstention and the only one that measures what the model would actually write, and Wang et al. give a direct reason to care about that divergence. Against it: it cannot be made fair across base and instruction-tuned checkpoints, it is the most expensive surface, and any relaxation of its normalization would reproduce the parser dependence that ended Study 1.

### OD4 - Which prompt-rendering variants are methodologically necessary?

**Recommendation.** exactly three: the registered baseline plus one separator change and one instruction-wording change

**Trade-off.** more renderings give a better robustness estimate and a stronger claim, but each one multiplies both cost and the multiplicity correction, and an over-large set invites the appearance of prompt shopping. Fewer than three cannot distinguish a rendering effect from noise.

### OD5 - What accuracy, robustness, equivalence and multiplicity thresholds are acceptable?

**Recommendation.** I1 null p<=0.90, I2 null p<=0.50, I4 null p<=0.25, equivalence margin 0.05, per-cell alpha 0.005 with Bonferroni within each gate family

**Trade-off.** stricter thresholds reduce the chance of certifying an inadequate interface but raise the chance of discarding a usable one and increase required sample sizes. The proposed values are deliberately conservative because the cost of a false pass is an uninterpretable later study.

> Blocking: yes - blocks freeze

### OD6 - What development and confirmation sample sizes should be used?

**Recommendation.** 192 per cell for development and confirmation, 128 for Gate I4

**Trade-off.** 192 gives power 0.98 at Gate I1 against a true rate of 0.98 and permits exact four-way and three-way counterbalancing; 128 drops I1 power to 0.885, which risks discarding an adequate interface; 256 buys little additional power at substantially higher cost.

> Blocking: yes - blocks freeze

### OD7 - Is a bounded independent methods review required before freeze?

**Recommendation.** yes, bounded to the statistical design and the gate logic, before any bank is generated

**Trade-off.** a review costs calendar time and must be scoped tightly to avoid becoming an open-ended redesign. Against that, both prior studies terminated on instrument-level problems that a design-stage reviewer could plausibly have flagged, which is a strong argument for paying that cost once.

### OD8 - Should a chat template be applied, and to which roles?

**Recommendation.** no chat template for S1, S2 and S3 on any role; for S4, apply each role's native template or record its absence

**Trade-off.** uniform treatment is cleaner for comparability but disadvantages the instruction-tuned role on generation; native templates are fairer per role but make cross-role comparison partly a comparison of templates. This asymmetry cannot be fully resolved and must be declared either way.

## 4. The one decision that can stop the study before it starts

`OD2`, the positive-capability reference model.

Gate `I4` exists because Study 2 had no checkpoint that was independently expected to succeed on
its compositional tasks, and therefore could not distinguish an interface failure from a
competence shortfall. If Study 3 cannot name such a checkpoint within the Tesla T4 envelope, Gate
`I4` cannot be evaluated and a Study 3 null would be exactly as uninterpretable as Study 2's was.

The constraint is concrete:

- Tesla T4, 16 GiB, no bfloat16 tensor-core path, fp16 supported
- a 1.5B checkpoint in fp16 needs roughly 3.1 GiB of weights and runs comfortably
- 3B class: roughly 6.2 GiB in fp16; fits with ample activation headroom; lowest risk
- 7B class: roughly 15.2 GiB in fp16, which does not leave dependable headroom for activations and KV cache on a 16 GiB T4; would require either short sequences and small batches with measured margin, or quantization
- 8B class and above: does not fit in fp16 on a T4

> int8 or 4-bit quantization changes the numerics of the very logits the interfaces read. If quantization is used it must be registered as part of the checkpoint identity and the positive control must be described as 'quantized checkpoint X', not as X.

**Proposed resolution: Stage P3-Q, positive-reference prequalification.** separate operator authority, not granted by this draft. Its isolation rule: runs only on K4-shaped items drawn from a prequalification seed that is disjoint from both the development and the confirmation seeds; the confirmation bank is physically absent from the image. Its only output: a pass or fail per candidate on a pre-registered capability floor, and nothing else. And explicitly: may not be reported as a Study 3 result and may not influence interface selection.

## 5. What operator review should check

1. Is the research question the right one to ask before any further substantive work?
2. Are the four candidate surfaces the right panel, and is anything important missing?
3. Is the gate hierarchy strict enough, and is Gate `I4` correctly separated from target capability?
4. Are the proposed thresholds, margins and sample sizes acceptable, or should they change?
5. Is the claim ceiling tight enough in both directions?
6. Is the traceability document's separation of sealed facts from zero-authority observations correct?
7. Should a bounded independent methods review happen before freeze (`OD7`)?

## 6. What a future authorized execution would need, in order

1. Operator resolution of the eight open decisions, at minimum `OD2`, `OD5` and `OD6`.
2. Amendment and freeze of the protocol under a separate authority, with thresholds fixed and
   hashed before any bank exists.
3. Seed draw and bank generation under that authority, with the confirmation bank sealed and
   physically excluded from the execution image.
4. Gate `I0` on fixtures, with no model involved.
5. Development-phase measurement, gates `I1` through `I4`.
6. Publication of the selection record, then a hard stop.
7. A further separate authority for the one-shot confirmation, Gate `I5`.

Each step needs its own authority. This draft grants none of them.

## 7. Boundaries that remain in force

A future pass would permit only only a new operator decision about whether to design a later substantive protocol.

It would not permit:

- reopening Study 2
- authorizing Study 4 or Study 2 v2
- behavioral confirmation
- activation extraction
- patching
- probes
- ablations
- lens work

Prohibited claims in either direction:

- any claim that the model does or does not reason
- any claim about internalized chain of thought
- any claim that distillation did or did not transfer a causal mechanism
- any claim about the existence of a task-defined intermediate variable
- any claim for or against J-space or J-lens validity
- any claim that Study 2 Gate A should or should not have passed
- any claim of model incapability derived from an interface failure
- any claim that a passing interface validates a later experimental design

## 8. Status of the other studies

- **Study 1** remains closed at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Unmodified.
- **Study 2** remains closed at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`, with
  documentation state `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`. Its scientific
  artifacts are unmodified; only the clerical changed-path count in the run-log prose was
  corrected, in its own commit.
- **Study 3** is a design draft only.

---

**`STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW`**
