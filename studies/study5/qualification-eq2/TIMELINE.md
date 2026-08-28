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
