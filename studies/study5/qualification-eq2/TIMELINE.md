# Study 5-EQ2 — construct adjudication

One question only: **is the excess-kurtosis readout convention EQ1 used the same
one this method's own authors use?** If not, does the target show a mid-depth
band under the convention that external evidence validates?

EQ1 is untouched. Its `Q-4a FAIL` stands, is not revisited, and every EQ1
artifact stays byte-identical. Its branch pointer remains at `a6a5afc`.

---

## Authority published alone

Branched from EQ1's terminal commit `a6a5afc`, committed as the **sole path** in
`4ec6b35`, before any other EQ2 write and before any curve was computed.

The text was never retyped. A script anchors to the document's own structure —
the instruction note, the separator that follows it, the closing
`*End of authority.*` — slices the body out, writes it, then reads it **back off
disk** and compares it to the source line for line: **313 lines, 0 mismatches**,
15300 bytes, LF, UTF-8 without BOM,
sha256 `63e4751573586d5ed7c8242d7fcaf1b1d6cb3f3232eb60ec46b0bcde795df894`.

Anchoring to structure rather than to hard-coded line numbers matters: a paste
that shifted by a line would otherwise have produced a quietly truncated
governing document.

---

## R-0 — establish the external standard, commit the rule before computing

### Rung A-1: does the official library provide a kurtosis path?

**Readout: PROVIDED. Kurtosis: NOT PROVIDED.**

Established five ways, not one:

1. every `.py` in the installed wheel searched for `kurt|moment|excess|skew|scipy.stats` — **0 matches**;
2. the full public API enumerated — nine names, none statistical;
3. every `def` and `class` in every module listed;
4. the **repository tree** at the registered commit listed, to catch anything in
   the repo but absent from the wheel;
5. `README.md`, `walkthrough.ipynb` and both data READMEs fetched at that commit
   and searched — **0 matches**.

The readout path itself is confirmed twice over and is not in dispute:
`JacobianLens.apply` (`lens.py:146`, readout at `:213`) returns **raw logits, no
softmax**, and the library's own analysis helper inside `vis.compute_slice`
(`vis.py:255-260`) travels the identical path. EQ1 used this correctly.

**A-1 therefore does not end adjudication.** It could only do so if it resolved
the convention, and the library computes no moments at all — so the
vocabulary-versus-dataset axis question is left exactly where it was. Proceed to
A-2. Recording A-1 as a flat "no" would have been simpler and less accurate.

### The external method, recovered from primary sources

The decisive find is in the method's **own repository** at the registered commit.
`data/evaluations/README.md` and `data/experiments/README.md` define, verbatim:

> **Lens readout** — at each (layer, token position) the Jacobian lens returns a
> ranked list of vocabulary tokens.
> **Workspace band** — the contiguous mid-network layer range where workspace
> content is read.
> **Hit** — a target token is a *hit* if it appears at **lens rank 1** at any
> (layer, position) in the band.
> **Metric** — pass@k = mean over items of the fraction of `intermediates` whose
> min-over-layers lens rank ≤ k.

**The external method does not locate the band with kurtosis at all.** It locates
it by *where labelled content is readable*, using vocabulary **ranks**.

That is a far better adjudicator than A-3's three-landmark prose, because the
band gets a **numeric location** on the same checkpoint we hold, computed rather
than judged by eye. Six labelled eval sets — **551 items**, each carrying
ground-truth `intermediates` and a source-fixed readout position — were acquired
to make that computation possible.

### Artifacts acquired, byte-verified, VM-side only

Nine files from `neuronpedia/jacobian-lens` at the pinned revision:
**933,184,004 bytes, 0 failures**. The three lens tensors are anchored by
**LFS SHA-256**, the six config/convergence files by **git blob SHA-1**, and the
two anchor kinds are kept in separate fields and never conflated. Zero bytes
were fetched by the operator's workstation.

`huggingface.co` is unreachable from the GPU host and `raw.githubusercontent.com`
times out; `hf-mirror.com` and `api.github.com` are used instead. This is safe
for a specific reason: every file is checked against the digest the **origin**
published at the pinned revision, so the transport cannot substitute bytes
without detection.

Comparability with EQ1's own fit, from the published configs: same library, same
commit, same corpus (`Salesforce/wikitext` `wikitext-103-raw-v1` train), same
`max_seq_len` 128, same target-layer rule. The external `convergence.csv` records
`n_valid_positions: 111` for `seq_len 128` — exactly `128 − 16 − 1`, the library's
`skip_first` of 16 with the final position dropped, **identical to EQ1**.

Differences recorded rather than smoothed over: external used `dim_batch` 128 vs
our 8 (affects only how many output dimensions share a backward pass, not the
estimator), `compile=true`, and early-stopped at 485 prompts vs our fixed 600 per
half. External fitted **one** lens per model; EQ1 fitted **two independent
halves**, which is why EQ1 has a cross-fit stability check and the external work
does not.

`final_identity_distance` for the positive control is **0.578094**. Our
corresponding value is **not computed**, deliberately: it would require reading
`lens_A`, which OD-012 forbids until the convention is committed. Deferred to
R-2 and reported there beside the external number.

### The rule, committed before any curve exists

`r0/adjudication_ladder.json`, sha256 `bd8be7e0…`, fixes A-1/A-2/A-3, both
candidate conventions including the exact implementation of D, and **every R-2
threshold**, before a single curve was computed.

The R-2 thresholds are **calibrated on the positive control, not on `T`**, and
notably are **not** EQ1's values: `C3` becomes the positive control's own band
length minus 2 (floored at 3) rather than 7, and `C5` becomes half the positive
control's own margin rather than 1.0. Which direction that moves them is not
predictable in advance, and both directions were accepted in writing before
anything was measured. EQ1's thresholds are not relaxed — they governed a
different question under a different convention, and that verdict stands.

### OD-011 in practice, including one correction

Every check carries a demonstrated failing case. **25 tests**, of which 15 are
negative tests that feed wrong input and prove the check reports FAIL — including
that a git blob id passed in the SHA-256 slot is rejected, that an
**unanchored** file is a stop rather than waved through, and that empty or
truncated bytes are refused.

The OD-012 ordering guard then caught something real: it flagged the ladder
record itself, because that record's note *says* "lens_A and lens_B have **not**
been read". A prose mention is not a read. The fix was to correct the **checker**,
not to reword the evidence to suit it — a read is now identified in the
structured provenance fields, and matched on the lenses' **immutable sha256**
rather than their filenames, so copying a lens to another path does not evade the
guard. Prose mentions are surfaced separately instead of being silently dropped.

Current guard state: **0 lens-reading records**. The verdict reads FAIL only
because the convention-commit boundary does not exist yet — it is written at R-1,
when the convention is chosen. That is the intended closing check, not a
violation.

### R-0 resource use

**0 actively used GPU-hours**, as the phase plan requires. Both VMs and the four
`TRAINING`-group V100 machines remain running, idle and untouched; **0** NSG
rules added, **0** containers created, **0** SAS tokens, **0** storage keys.

### Control weights acquired

27 files, **19,873,171,263 bytes**, **0 failures**, all byte-verified against
origin-published anchors: 8 by LFS SHA-256, 19 by git blob SHA-1.
`Qwen2.5-7B-Instruct` @ `a09a3545` (positive control), `Qwen3-1.7B` @ `70d244cc`
(depth test), `gpt2` @ `607a30d7` (negative control), `trust_remote_code=false`.
Again **0 bytes** fetched by the operator's workstation.

**R-0 is complete at 0 actively used GPU-hours**, as its phase plan requires.

### New DC / IMG / HB entries in R-0

**None.** No disclosed correction, no image defect, no hard blocker. The one
thing worth flagging is not a defect but a design choice recorded above: the
OD-012 guard's first version treated a prose mention as a read, and the checker
was corrected rather than the evidence reworded.

---

## R-1 — stopped at step 3, stop condition 1 fired

### Step 1 — external identity-distance distribution (0 GPU)

**37** published convergence traces, not 39. The prompt said 39; the pinned
revision publishes 37, and 37 is what was used. Recorded rather than rounded.

| n | min | Q1 | median | Q3 | max | IQR |
|---|---|---|---|---|---|---|
| 37 | 0.130071 | 0.441750 | **0.578094** | 0.843554 | 3.649054 | 0.401804 |

The positive control's `final_identity_distance` is **exactly the median**. That
was observed, not arranged.

`OD-016` registers the tolerance *from* this data: Tukey inner fence
`[Q1−1.5·IQR, Q3+1.5·IQR]` = `[−0.160956, 1.446260]`, clamped at 0.

Stated rather than papered over: the raw lower fence is negative, so the primary
rule is **non-binding below**. It can only catch a Jacobian unusually *far* from
identity — not one unusually *close*, which would mean the lens had collapsed
into an ordinary logit lens. A secondary lower gate is therefore registered at
the observed external minimum `0.130071`, kept as a separate item so its weaker
basis (one observed minimum, not a quantile fence) stays visible.

### Steps 2–3 — rank profiles on the three controls

Pooled pass@1 readrate, ~900 scored intermediates per model:

| | positive (Qwen2.5-7B-It) | depth (Qwen3-1.7B) | negative (gpt2) |
|---|---|---|---|
| peak | **0.0846** @ L25 | **0.0758** @ L24 | **0.0078** @ L9 |
| band | [23, 24, 25] | [21…25] | **[9]** |
| pass@10 peak | 0.1901 | 0.1923 | 0.0323 |

**The positive control partially reproduces the published signature**, measured
with no kurtosis anywhere: readrate is *exactly* 0.0000 through layers 0–12,
first non-zero at 13, rises steeply from 20 → 21 → 22 → 23 → 24 → 25, then
**falls at the last layer** to 0.0319. The near-zero early region, the rise and
the terminal fall are all present. The rise begins *later* than "a third of the
way through" — about layer 20 of 27 — so this is reported as **partial**
qualitative agreement, not a match.

**The depth question is answered: "28 layers is too shallow" is externally
refuted.** Qwen3-1.7B reaches peak 0.0758 against the 7B's 0.0846, with a
**longer** band (21–25 vs 23–25) and a slightly higher pass@10 peak. This says
nothing about whether the target has a band, and does not support the shallowness
explanation either.

### HB-002 — stop condition 1 fired, not repaired

Under the frozen `OD-015` rule the **negative control yields a band**, `[9]`,
length 1, peak `0.0078` — **7 of 898** intermediates. Registered stop condition 1
fired, so this invocation stopped, committed and reported.

**The defect is in my own registered rule, not necessarily in the method.**
`OD-015` defines the band as the longest run at or above *half of the maximum*.
That is scale-free by construction — deliberately, to avoid inventing an absolute
threshold. The negative control has now shown the cost: because the rule
normalises by the profile's own maximum, **any** profile with an interior peak
yields a band, including pure noise. There is no absolute floor on peak readrate
and no minimum band length. This is precisely what a negative control is for, and
it worked.

The underlying rank measurement *does* discriminate: **10.85×** between the
positive and negative peaks, 9.73× for the depth test. **That observation does
not rescue the verdict.** Declaring the negative control clean would require an
absolute floor or a minimum band length, neither of which was registered, and
choosing one now would be choosing a threshold with the answer already visible —
the exact failure mode this governance exists to prevent. The operator decides,
not this invocation.

### What was deliberately not done

Step 4 (V vs D kurtosis adjudication) **was not run**. No convention was
selected. `lens_A` and `lens_B` were **not read** — the OD-012 guard reports
**0 lens-reading records** and the boundary record was never written. The target
was not touched.

### R-1 resources

**1.0 actively used GPU-hours** of the R-1 ceiling of 10 (OA-003); cumulative
**32.583 of 240**. Both VMs and the four `TRAINING`-group V100 machines remain
running, idle and untouched; 0 NSG rules, 0 containers, 0 SAS, 0 storage keys.

New entries: **HB-002**. No DC, no IMG.

---

## R-1 續 — OA-004 lifts HB-002, convention **D** committed

### Step A — non-vacuity, proven before any real profile was judged

All three OA-004 revision-3 cases pass: a random lens's own profile, pure noise,
and an all-zero profile each yield **no band**. The gate runs on every invocation
of the tool, not only when asked for.

### Step B — the matched-norm null changes everything

The five random-lens replicates per model read **essentially nothing**: peak
pass@1 of `0.000000` on every positive and negative replicate, and `0.001099`
(one hit in 910) on two of five depth replicates. That is a far cleaner null than
gpt2, exactly as the diagnosis predicted.

| | positive (7B-It) | depth (1.7B) | negative (gpt2) |
|---|---|---|---|
| significant layers | 21–26 | 20–26 | **none** |
| band (registered rule) | **[21…26]** | **[20…26]** | **[]** |
| peak | 0.0846 @ L25 | 0.0758 @ L24 | 0.0078 @ L9 |
| null ceiling | 0.004204 | 0.006198 | 0.004260 |

**The negative control now holds.** gpt2's best lower bound is `0.003781` against
a null ceiling of `0.004260` — it does **not** clear the null at any layer. HB-002
is lifted on the merits, not by moving a threshold.

### DC-005 — I had silently substituted a stricter rule of my own

All three models first returned "no band", which was inconsistent enough to look
at the code rather than the data. OD-015 registered that **the band's argmax**
must not sit on an endpoint. My implementation required **the band's entire
extent** not to touch an endpoint — strictly stronger, and never registered.

Under my unregistered rule the positive control gets no band, which fires
registered stop condition 2 and would have **terminated the invocation for a
reason I invented**.

Corrected to the registered rule, with the stricter reading kept as a labelled
secondary diagnostic. This is not cherry-picking, for a checkable reason: **the
negative control is clean under both readings** — zero significant layers either
way — so the correction does not rescue it. It only restores the committed
criterion for the positive and depth models.

**A concern the correction does not resolve, stated plainly:** the positive
band is layers 21–26 of source layers 0–26 — the **last quarter** of the network.
It is a *late* band, not a mid-depth one. With a near-zero null, anything above
≈0.4% readrate is significant, so the run extends to wherever readability has not
yet collapsed. Readrate does fall sharply at L26 (0.0846 → 0.0319) but still
clears 0.0042. The published description says the rise begins "about a third of
the way through"; observed onset is ≈¾ of depth. Whether a late band satisfies
the intent of "mid-depth" is the operator's call, not mine.

### Step C — **convention D wins decisively**

| convention | band | Jaccard vs rank band [21–26] |
|---|---|---|
| **V** — vocabulary axis, *EQ1's* | [2, 3] | **0.0000** |
| **D** — dataset axis | [20…25] | **0.7143** |

The two conventions do not merely differ in degree — they point at **opposite
ends of the network**. Convention D's curve is near zero or negative through
layers 8–17, rises from 18, peaks at **2.3820 @ L25**, and falls sharply to
**0.1289 @ L26**.

Honest note: D's flat region sits in the **middle** (layers 8–17), not in the
first third as the published text describes; layers 0–7 run 0.5–1.6. The rise
and the terminal fall are reproduced, the position of the flat region is not.
Reported as **partial** agreement.

Adjudicated **entirely on the external positive control**. The target played no
part.

**What this means for EQ1**, in the authority's own words: EQ1 reconstructed the
paper's footnote incorrectly, and its `Q-4a FAIL` is attributable to an
**implementation defect rather than to the model**. It is **not** a retraction —
EQ1's record stands unchanged and its artifacts stay byte-identical.

### OD-012 boundary

`convention_commitment.json`, sha256 `a58be822…`, is the boundary record. The
guard now reports **PASS** with **0 lens-reading records** — `lens_A` and
`lens_B` have still never been read, and the target has not been touched.

### R-1 resources

**6.0** actively used GPU-hours of the R-1 ceiling of 10; cumulative **37.583 of
240**. Both VMs and the four `TRAINING`-group V100 machines remain running, idle
and untouched.

New entries: **DC-005**. HB-002 lifted. 53 tests passing.

---

## R-1b — OA-005 tightens the criterion, and the band does not survive

### Rulings recorded

**The directionality criterion**, fixed as precedent in `OD-017`: *changing the
implementation to match the registered text is a bug fix; changing the registered
text to match the data is p-hacking.* The distinguishing feature is **direction**,
not outcome. DC-005 was a bug fix by that test, and the supporting check — the
negative control was clean under both readings — made it verifiable rather than
merely assertable.

Two limitations recorded verbatim. **gpt2's non-significance is
power-dependent**: `0.003781` against a ceiling of `0.004260` is a ~12% miss,
about 7 hits in 910, and with more items it would quite possibly cross. It must
not be read as "gpt2 has no readout". **The band's upper edge is right-censored
by the end of the network**, not determined by the phenomenon — only the lower
edge and the argmax carry information.

**EQ1 boundary**: its record stands, and restarting any part of EQ1 on the
grounds that convention D might PASS is forbidden. EQ1's FAIL is an accomplished
fact about that execution.

### Step A — OD-017 conformance audit: **19 entries, 0 divergences**

The audit imports the modules and compares **live values**, not comments — a
hand-written table asserting agreement would be precisely the check that cannot
fail. One honest flag: for multihop / multilingual / order-ops, "token before
target" and "final prompt token" resolve to the same index because these prompts
stop immediately before the answer. That is a property of the data, not a
harmonisation of the rules.

### Step B — output-adjacency is **not** the explanation

| | fraction |
|---|---|
| intermediate == the item's own `target` | 0.0032 |
| intermediate == the **model's own top-1** at the readout position | **0.0053** (5/937) |

Worst set is order-ops at 1.82%. The late band is **not** simply the lens reading
the answer. Reported only; no criterion adjusted.

### Step C — **condition (ii) removes almost the entire band**

| | J-lens peak | plain logit lens peak | ratio |
|---|---|---|---|
| positive (7B-It) | 0.084615 | 0.076923 | **1.100** |
| depth (1.7B) | 0.075824 | 0.076923 | **0.986** |
| negative (gpt2) | 0.007795 | 0.004454 | 1.750 |

Positive control, layer by layer inside the condition-(i) band:

| layer | J-lens | logit lens | (ii) passes |
|---|---|---|---|
| 21 | 0.0132 | **0.0000** | **yes** |
| 22 | 0.0319 | 0.0132 | no |
| 23 | 0.0791 | 0.0637 | no |
| 24 | 0.0835 | 0.0769 | no |
| 25 | 0.0846 | 0.0703 | no |
| 26 | 0.0319 | 0.0253 | no |

**The band collapses from six layers to one.** On the depth test **no layer
passes at all** — and the plain logit lens is very slightly *better* than the
J-lens at peak.

**What this means as a measurement:** the late region's readability is a property
of the residual stream at those depths that the unembedding alone already
exposes. It is not information the Jacobian transport contributes. That is
exactly the confounder OA-005 was written to catch, and the diagnosis behind it
was right.

**The one genuine positive, stated precisely:** at layers 13–21 the plain logit
lens reads *exactly* 0.0000 while the J-lens reads 0.0011–0.0132 — there is a
real region where the Jacobian adds what the unembedding alone cannot. But layers
13–20 sit at or below the null ceiling of 0.004204, so **exactly one layer, 21,
clears both the null and the logit lens**.

### HB-003 — stopped, nothing repaired, no criterion revised

Under the literal text of OA-005 the positive band `[21]` satisfies (i), (ii) and
(iii). I am **not** acting on that reading, for three stated reasons: a one-layer
"band" is a point, not the "layer range" OD-015 registered; the R-0 ladder
(committed at `bd8be7e0`, before any measurement) sets the R-2 coverage floor to
*the positive control's own band length minus 2, floored at 3* — which the
positive control itself would then fail, so the calibration is self-contradictory
at this length; and the depth test lost its band entirely, so the two models that
were meant to corroborate each other do not.

The substance of stop condition 2 is met even though its literal text is
arguable. **I did not revise the criterion in either direction** — the
instruction is explicit that revision stops here pending approval.

`lens_A` / `lens_B` still **never read** (guard PASS, 0 records); target untouched.

### R-1b resources

R-1 + R-1b: **7.483 of 10**; EQ2 **7.483 of 24**; cumulative **39.066 of 240**.
New entries: **HB-003**, **OD-017**, **OA-005**. No DC, no IMG.

---

# EQ2 terminal — **NEGATIVE**, and D-1 says it is negative-**A**

## The ruling that closed it

I had reported a split between OA-005's literal text and its substance. **The
split does not exist**, and settling it needs no criterion to move: the R-0
ladder — committed at `bd8be7e0` *before any measurement* — sets the R-2 coverage
threshold to *the positive control's own band length minus 2, floored at 3*. At
band length 1 the positive control **cannot pass the threshold derived from
itself**. A "valid band" therefore means one **usable for its registered
downstream purpose**, and all of that was already in `bd8be7e0`. Stop condition 2
is triggered. My reason ② was the decisive one.

```
EQ2 determination: NEGATIVE
The J-lens locator method did not yield a usable locating band
under this implementation at this scale.
R-2 not authorised.  lens_A / lens_B not read.  T not touched.
```

**This is the answer EQ2 was built to be able to give.** Its whole function was
to adjudicate the construct *before* spending budget on the target. It
adjudicated: the construct does not hold. The protocol worked.

### A precedent, recorded beside OD-017's directionality criterion

**OA-005 was a post-hoc *tightening*, and it saved the study.** Had the relaxed
reading been accepted — that a late band satisfies "mid-depth" — we would have
entered R-2 with a method whose readout is **indistinguishable from a plain logit
lens**, and spent the target's budget on an instrument that measures nothing.
A post-hoc tightening prevented a false positive. Post-hoc is not automatically
illegitimate; **direction** decides.

## D-1 — negative-**A**: EQ2 *did* adjudicate

Registered, with its decision rule and asymmetric-motivation labelling committed,
**before** it was run.

| | median ‖J−I‖/‖I‖ | identity energy share | effective rank |
|---|---|---|---|
| positive (7B-It) | **1.2765** | 4.9% | 689 / 3584 |
| depth (1.7B) | **3.2050** | 9.8% | 486 / 2048 |
| negative (gpt2) | **1.1800** | 27.8% | 389 / 768 |

Registered thresholds: below **0.5** → negative-B, at/above **1.0** → negative-A
(uncorrelated matched-norm reference ≈ 1.414). **All three sit at or above 1.0.**

**`J` is nowhere near the identity**, so the J-lens is *not* a plain logit lens by
construction. **Negative-B is excluded, and EQ2 genuinely adjudicated** — the
negative is informative, not vacuous.

### The depth-dependence that makes both findings cohere

The identity share is not constant — it climbs monotonically:

| layer | 0 | 9 | 18 | 21 | 23 | 25 | 26 |
|---|---|---|---|---|---|---|---|
| identity share | 0.004 | 0.021 | 0.169 | 0.469 | 0.640 | 0.729 | **0.749** |

with the best scaled-identity α ≈ **1.0** at layers 23–26. So **in the late
layers, where condition (ii) failed, `J` really has approached the identity**;
in the early and middle layers, where the plain logit lens read *exactly* 0.0000,
`J` is far from it (<5% identity energy at layers 0–12). The J-lens matches the
logit lens precisely where `J` has become the identity, and differs precisely
where it has not. Internally consistent — and a **description of the fitted
Jacobians**, not a mechanistic account. These are the **external** lenses, fitted
by an independent party; we did not fit them.

### OD-016 retrospective — the answer is **no**

Even with an effective lower gate, OD-016 would **not** have fired: all three
published `final_identity_distance` values (0.578094 / 0.524690 / 1.305569) sit
comfortably inside the registered `[0.130071, 1.446260]`. **That is the correct
outcome**, since D-1 has just shown these lenses are not collapsed. OD-016's
non-binding lower fence remains a real weakness worth fixing in any successor —
it simply was not what mattered here.

## Close

`lens_A` / `lens_B` **never read** across the entire invocation (guard PASS,
**0** lens-reading records). Target never touched. EQ1 artifacts byte-identical.
**0** criterion revisions in the closing steps.

Closing inventory: **closing == opening + registered deltas**, no drift, no hard
blocker. All six VMs still `VM running`, including the four `TRAINING` V100
machines — **0** control-plane writes, **0** data-plane writes, **0** SAS, **0**
storage keys.

Budget: EQ2 **7.483 of 24**; cumulative **39.066 of 240**. **16.5 GPU-hours were
not spent**, because the instrument was disqualified before the target run.

New entries: **HB-003** (terminal), **OD-017**, **OA-005**, **D-1**. 65 tests.

---

# Closing addenda — recorded before sealing

Documentation only. **No computation, no lens read, no GPU.** Every number below
is read from artifacts already committed. The terminal determination is
unchanged: **EQ2 NEGATIVE, D-1 negative-A, R-2 not authorised.**

## 1. Negative-A is a conclusion about the **median**; inside the band, B is real

The pre-registered rule decides on the median `‖J−I‖/‖I‖`, all three models are
≥ 1.0, so **negative-A stands and the determination does not change**. But the
depth profile must be printed beside it, or a reader will take "negative-A" to
mean B was excluded *at every depth*, which is not what was measured.

| layer | 0 | 18 | 21 | 23 | 26 |
|---|---|---|---|---|---|
| identity energy share | 0.004 | 0.169 | 0.469 | 0.640 | **0.749** |

α ≈ **1.0** at layers 23–26 — and **the rank readout is invariant to scalar
scaling**, so `J ≈ αI` and `J ≈ I` are equivalently degenerate here.

> The determination is negative-A, on the basis of the per-layer median. But the
> identity energy share climbs monotonically with depth, reaching 0.749 at the
> final layer with α ≈ 1.0. **The layers at which condition (ii) failed are
> precisely the layers at which `J` is closest to a scaled identity.** So this
> negative is A in aggregate, while **within the band the degenerate mechanism of
> B is genuinely operating**. The two do not conflict: the J-lens coincides with
> the logit lens exactly where `J` approaches the identity, and differs from it
> exactly where it does not. This is a description of the fitted Jacobians, not a
> mechanistic explanation of the models.

## 2. The third explanation D-1 did not — and could not — exclude

D-1 excluded "`J ≈ I`, so it degenerates by construction". It did **not** exclude
**that our way of applying `J` diverges from what the lens's authors intended.**

The gap is narrow but real, because both ends of the pipeline are pinned:

- it **can** read — the plain logit lens reached 0.0769, so the pipeline is not dead;
- it **does not fabricate** — the matched-norm random-lens null is essentially zero;
- **the unverified step is exactly the one under test** — how the Jacobian is applied.

And the control that should have closed this **never passed**: the positive band
was `[21]`, length 1, unusable against the R-0 ladder's floor of 3; the depth
band was empty.

> This study **never obtained a passing positive control**. Consequently "the
> J-lens method does not hold" and "we did not drive the lens as its authors
> intended" **are indistinguishable within this study**. The negative conclusion
> is **strong about our execution and weak about the method itself.** Any
> successor should first obtain a passing positive control before attempting to
> adjudicate the method.

**This corrects something I wrote.** I reported that "EQ2 *did* adjudicate; the
negative is informative rather than vacuous." That overstated it: D-1 established
only that the lenses are not identity-collapsed, not that our application of them
was faithful. The accurate statement is **EQ2 adjudicated *our execution* of the
construct, not the construct itself.**

## 3. The gpt2 ratio of 1.750 is noise — sealed off now

gpt2 has the **highest** identity energy share (27.8%) yet the **highest**
J-over-logit ratio (1.750). Verified against the committed artifacts: that ratio
is `0.007795` vs `0.004454` at n = **898**, i.e. **7 hits against 4**.
(The note said n ≈ 910; 910 is the two Qwen models, gpt2's n is 898. The hit
counts, 7 and 4, are exactly as stated.)

> This must **not** be read as "the Jacobian contributes most strongly on gpt2",
> nor as any pattern whatsoever. It is counting noise: seven hits against four.

## Additional prohibition

> It must not be claimed that the **published lenses are defective**. What was
> measured is the result of **our use** of those external artifacts, and addendum
> 2 explains that we cannot distinguish a problem with the artifacts from a
> problem with our usage.

## Reserved for successor studies — not in scope here

1. **Layer-21 residual** — on the 7B, layers 13–21 have a plain logit lens
   readrate of exactly 0.0000 while the J-lens is non-zero; only layer 21 clears
   both the null and the logit lens, at ~12 hits. A candidate requiring
   independent pre-registration; **not a finding of this study**.
2. **OD-016's lower fence** — the retrospective confirmed its not firing was
   *correct* here, since the lenses are not collapsed; but non-binding-below
   remains a real weakness, and any study reusing that guard must fix it first.
3. **A passing positive control** — see addendum 2; a precondition for any
   adjudication of the method.

---

**EQ2 sealed. No further rounds.**
