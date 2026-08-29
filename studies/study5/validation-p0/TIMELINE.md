# Study 5-P-0 — item-validity verification

One question only: **do the multihop items oblige the model to compute an
intermediate at all?** If nothing is computed, there is nothing for any lens to
read, and EQ2's negative says nothing whatsoever about the J-lens.

EQ1 and EQ2 are untouched. EQ1's `Q-4a FAIL` stands and is not revisited. EQ2's
`NEGATIVE` stands and is neither confirmed nor weakened by anything here. Every
EQ1 and EQ2 artifact is byte-identical against `a28ae6a`, verified by diff, and
the EQ2 directory was mounted **read-only** inside every measurement container.

---

## Why this phase exists at all

EQ2 closed with a limitation heavier than its verdict: it never obtained a
passing positive control, so *"the method does not hold"* and *"we did not drive
it as its authors intended"* stayed indistinguishable. One level deeper, there
was never a known-positive object either — that `Qwen2.5-7B-Instruct` exhibits
the phenomenon was assumed and never argued.

EQ2's negative admits four explanations. Three were considered. The fourth —
**the items never forced an intermediate** — was never checked, is the cheapest
to check, and is the one sitting underneath the others. The old ordering assumed
item validity, then assumed the phenomenon, then tested the instrument; a
collapse at any level presents identically as instrument failure.

Patching imports **no part of the instrument under test**. That independence is
the whole point, and it is enforced rather than asserted: no P-0 tool contains an
import statement for it, checked statically across every file in `tools/`, and
the measurement records `sys.modules` membership at the end of each run. Both
checks are in the committed OD-017 audit.

---

## Pre-registration published before the first forward pass

Committed and pushed as `f2de9cc`, before any patching ran.

**The frame.** Ordered pairs of items that already exist in
`lens-eval-multihop.json`. No text was authored. Patching is a two-run operation
by definition, so the unit cannot be an item; pairing existing prompts
constructs the counterfactual without inventing data. Both members must tokenise
to the **same length**, which costs frame size but keeps absolute positions
identical — Qwen2.5 applies rotary position information inside attention rather
than storing it in the residual stream, so transplanting a state from position
`p` to `p'` would introduce a mismatch unrelated to the question. Equal length
removes the confound instead of arguing about its size.

93 items → 78 admissible → **190 ordered units in 95 clusters**. The 200 cap did
not bind, so the frame is exhaustive and **no sampling randomness entered it**;
it is recoverable from the evaluation file alone.

**The sites**, recovered mechanically from the token alignment and never
annotated, because a hand-marked "first-hop cue span" is a place for the
operator's expectation to enter the measurement:

| site | definition | tokens differ? |
|---|---|---|
| `PREFIX` | strictly before the first differing token | no — identical |
| `CUE` | where the token sequences differ | yes |
| `BRIDGE` | after the last `CUE` position, before the readout | **no — identical** |
| `READOUT` | the final prompt token, per EQ2's registered rule | n/a |

**The verdict rests on `BRIDGE` alone.** Its input tokens are identical in donor
and recipient, so a patch there can move nothing except state the model
*computed* from the cue and *carried forward*. A model answering by direct
retrieval holds nothing there to move. `CUE` and `READOUT` are measured and
reported but cannot decide anything: both are strongly positive whether or not
an intermediate exists, and a rule resting on them could not return the negative
verdict — the exact defect OD-011 exists to prevent.

**Both conclusion wordings were fixed verbatim before any data existed**,
including what each does *not* mean.

---

## Gates, all run before the criterion touched data

**OD-011 non-vacuity — 4/4**, on synthetic curves, before any measurement
existed. The null itself, pure noise and an all-zero curve all return
`NOT_CAUSALLY_USED`. A fourth case was added: a strong localised curve must
return `CAUSALLY_USED`. The three required cases only prove the rule cannot
manufacture a positive; without the fourth, a rule that always says *no* would
pass, and that is equally a check that cannot fail.

**OD-017 conformance — 23 entries, 0 divergences**, every one comparing a **live
imported value**, never a comment. Two entries cross into EQ2 to check that P-0's
deliberate transcriptions — the readout rule and the surface-form expansion —
have not drifted from the originals. Transcription is exactly what drifts
silently, which is why it is compared rather than trusted; importing EQ2's module
is safe in an *auditor* but would have dragged the instrument under test into the
ground-truth path of the *measurement*.

**Sealed-asset guard — PASS.** Zero lens reads, zero references to `T`, zero
imports of the instrument. Content-addressed as well as name-based, because a
file can be renamed but its sha256 cannot.

---

## The harness verified before spending accelerator hours

Reviewing the measurement code found four defects that would have **corrupted the
run rather than crashed it**: a seed derived from `hash()`, which Python
randomises per process, making the registered reproducibility claim simply false;
full-batch logits at roughly 9 GB per unit; per-position logits cached per item;
and an inverted independence flag.

The harness is then exercised on a small attention-free model, where every
position is independent and the properties that matter can be asserted exactly:
a patch in one batch row does not leak into another — every construction for a
unit shares one batch, so a leak would blend the real measurement with its own
nulls and nothing downstream could see it — values land at exactly the requested
positions, patching a layer with its own values is a no-op, and results are
invariant to batch size. Committed as `2f9d95e`. **70 tests pass.**

---

## The measurement

Four shards, one physical A100 each, `--network none`, EQ2 read-only.
**184 units measured, 6 dropped** on the registered denominator guard,
**92 clusters**, 29 depth sites, 11 constructions. `381.8` GPU-seconds.

### What passed — the first passing positive control in Study 5

Patching `CUE` at the embedding output makes the recipient run **token-identical**
to the donor run, so restoration must be 1.

| check | value | required |
|---|---|---|
| `CUE` @ embedding | **0.9862** (lcb 0.9523) | lcb ≥ 0.90 |
| `READOUT` @ layer 27 | **1.000000**, zero-width | structural |
| `CUE` peak, layer 5 | 1.0200 | — |

This certifies **the instrument** and nothing else. It says nothing about whether
the model computes an intermediate, nothing about `J`, nothing about the paper,
nothing about `T`.

### What failed

`PREFIX` integrity: **0.025512** against a tolerance of `1e-4`.

The diagnosis is settled by an observation stronger than the causal-masking
argument the gate was built on. `PREFIX` at **layer 27** is a no-op guaranteed by
the architecture: the last block's output at a non-final position is read by
*nothing*, since only the final position reaches the unembedding. It would read
zero even if the patched values were arbitrary. It reads `0.013754` — the same
value, **unit by unit**, as the embedding-layer no-op.

A patch that provably cannot influence the output still moved the metric, so
patching is not the source. The clean baseline was measured in a batch-of-one
forward and every patched value in a batch-of-48 forward, and bfloat16 kernels do
not select the same reduction order at both sizes. **Implementation defect; the
registered tolerance was right to refuse it.**

### Curves and ceiling

| site | peak mean | layer | role |
|---|---|---|---|
| `PREFIX` | 0.0255 | 19 | integrity gate, must be 0 |
| `CUE` | 1.0200 | 5 | descriptive, cannot decide |
| **`BRIDGE`** | **0.2380** | **22** | **decisive** |
| `READOUT` | 1.0000 | 27 | descriptive, cannot decide |

Zero-intervention ceiling **1.0030**, set by a norm-matched random patch at
`READOUT`, layer 19.

The registered rule ran unmodified and returned `NOT_CAUSALLY_USED`. **That
verdict is not reportable**, because the registration states a verdict means
nothing until the structural gates pass. Reporting it anyway would be helping
myself to the half of the registration I happen to like.

---

## The heavier problem, which is in the registration and is mine

Restoration is normalised on `logit(donor target) − logit(recipient target)`. Any
patch that merely **disrupts** the recipient's answer lowers the second term and
so raises restoration, carrying no donor information whatsoever. The estimand
cannot separate *moved toward the donor's answer* from *moved away from the
recipient's*.

This is not hypothetical:

| construction at `BRIDGE` | worst pooled \|mean\| |
|---|---|
| unrelated third donor | 0.1305 |
| norm-matched random | 0.4139 |
| **real** | **0.2380** (peak) |

**The nulls are not quiet.** A patch carrying no donor information produces
movement of the same order as the real patch, which is what the disruption
pathway predicts.

Relatedly, one scalar ceiling maximised across sites imported the `READOUT`
scale — where destroying the state the answer is read from makes the normalised
quantity unbounded — into a `BRIDGE` test.

This is the EQ2 lesson recurring one level down. EQ2 recorded that a null
carrying a small real signal produced a band under a rule assuming the null was
empty. Here the nulls were built correctly and the ceiling absorbed the
disruption, so the rule did **not** manufacture a positive — the conservative
direction held. The same underlying error is present in the *estimand* rather
than in the null.

The OD-011 demonstration used synthetic nulls at σ 0.05 and 0.15. It proved the
rule cannot manufacture a positive from a **quiet** null, which remains true. It
did not prove the ceiling is on the right scale, and I did not think to require
that it should.

---

## Nothing was repaired

The `BRIDGE` curve is already in hand. Choosing a per-site ceiling or a new
estimand now would move the **registered text toward the data**, which the
directionality precedent calls p-hacking regardless of whether the replacement is
better in the abstract. The difference is the direction, not the outcome. The
registration lists *"any situation in which the operator wishes to revise a
pre-registered criterion"* as stop-and-ask.

**0 criterion revisions. 0 verdict recomputations under any alternative rule.**

`OD-018`, `OD-019` and `OD-020` are filed **PROPOSED and explicitly not in
force**, with the motivation asymmetry disclosed as the authority requires: I
would not have thought of any of them had the gates passed. Their legitimacy
would come from being fixed *before* a successor measurement exists, so their
content cannot be tuned to a result. That decoupling has not happened, which is
why they are proposals and why the operator decides.

---

## Reported only, no criterion adjusted

The model produces the labelled target as its top-1 continuation for **32.61%**
of the admissible multihop items. EQ2 measured lens readability on these items
without ever establishing this number. It is not the verdict, it does not
establish that the items are invalid, and nothing was adjusted from it.

---

## Accounting

| quantity | value |
|---|---|
| actively used GPU-hours, this phase | **0.106056** |
| J-lens route | 0.106056 / 15 |
| cumulative | **39.171895 / 240** |
| hard stop | 54.065839, not approached |
| a100-vm wall-clock attributable | 0.047 h |
| allocated GPU-hours | 0.188 |

Azure: 0 reconfigurations, 0 power-state changes, 0 resizes, 0 reboots, 0 NSG
rules, 0 containers created, 0 blobs written, 0 SAS tokens, 0 storage keys read.
All four `TRAINING` `Standard_NC24s_v3` machines remained **running, idle and
untouched**. No cost-reduction action proposed, performed or discussed. Only
read-only `az` calls were made.

`T` untouched. Sealed lenses unread, 0 reading records. The instrument under test
never imported, verified statically and at runtime.

---

## State

`STUDY5_P0_HALTED_AT_A_REGISTERED_STOP_CONDITION_AWAITING_OPERATOR`, under
`HB-004`. P-0b is **not** entered. Two decisions are reserved for the operator:
whether to re-run with the baseline measured inside the patched batch, and
whether the estimand should isolate movement toward the donor from generic
disruption.

**P-0 is item-validity verification. No state it can reach is a scientific
result, and this state is a halt rather than a determination.**

---

## Closure

P-0 is closed **`UNINTERPRETABLE`** by operator ruling of 2026-08-29,
recorded in `P0_CLOSURE.json`, sha256
`60d8c257896408cc9d1879f336e4ef97eacab0f3540ec87f9d5c9befd932548b`.

Not a negative and not a positive. The distinction that matters:

> This is not a case of overturning a negative result. The pre-registration
> voided it.

The withheld direction is recorded verbatim in the closure file, for one
specific reason — so that any later replacement of the estimand can be seen to
move toward one side or the other:

> Had the gates passed, P-0's registered rule would have returned
> `NOT_CAUSALLY_USED`. That verdict was withheld because the PREFIX gate
> failed, and it was never published. THIS DIRECTION IS RECORDED SO THAT ANY
> LATER REPLACEMENT OF THE ESTIMAND CAN BE SEEN TO MOVE TOWARD ONE SIDE OR THE
> OTHER.

It may not be cited as a published conclusion.

Every P-0 artifact, tool and decision file is preserved unchanged. `OD-018`,
`OD-019` and `OD-020` remain `PROPOSED, not in force`. The successor is a
new independent pre-registration, following the D-1 precedent that a new
question gets its own registration rather than reopening a closed one.
