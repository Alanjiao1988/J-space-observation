# Study 5 / P-0 — Item-Validity Verification

> Transcription note. This document is a transcription of the operator's
> session prompt of 2026-08-29, made by the agent inside the session. Unlike
> the EQ1 and EQ2 authorities it was **not** extracted mechanically from a
> file, because the source was a live prompt rather than a document. It is
> recorded here so that the governing text is committed alongside the work it
> governs; readers should treat the transcription itself as agent-produced,
> and the operator's session prompt as the original.

---

## 0. Locate first, act second

1. Open the J-space-observation repository. **Final work lands on the mooncake
   lineage branch, not on `main`.**
2. Read the authority files, the method memoranda, and every EQ1 / EQ2
   artifact of Study 5, particularly the entries numbered `OD-*` (operational
   discipline), `OA-*` (adjudication), `DC-*` (discrepancy) and `HB-*` (hard
   blocker).
3. **This repository requires timestamped commits across the whole process,
   for use in writing the paper.** Do no work outside the repository.
4. Report your understanding before executing section 4.

## 1. Hard boundaries (highest priority, never to be breached)

### Azure

Resources are **to be used and never reconfigured**. `a100-vm` and `cpuserver`
stay running; the four `Standard_NC24s_v3` machines (16 × V100) in the
`TRAINING` resource group **stay running, stay idle, and receive no NSG rule
and no configuration change of any kind for access purposes**.

No resize, no reboot, no power-state change, no touching disks / NICs / RBAC,
no creating or deleting any resource or container. Existing blobs are
immutable; every upload is create-only with `If-None-Match: *`.

**No cost optimisation, no recommendation to stop anything, no discussion of
spend.** This money is being spent deliberately by the user; cost is not your
concern.

### Protected objects

* **`T` must not be touched**, not by a single byte.
* **`lens_A` / `lens_B` must not be read.** The guard must PASS throughout,
  with zero reading records.
* **EQ1 artifacts must not be modified.** Its `Q-4a FAIL` is not withdrawn, not
  rerun, and its thresholds are not relaxed.
* It is **expressly forbidden** to restart any part of EQ1 on the grounds that
  "rerunning EQ1 under convention D might PASS". EQ1's FAIL is an accomplished
  fact about that execution.

## 2. Prior state: what Study 5 has already determined

### Determinations

* **EQ1: `Q-4a FAIL`.** It was later established that it used a kurtosis
  convention on the **vocabulary axis (V)**, while the rank readout
  corresponds to the **dataset axis (D)**; the two point at opposite ends of
  the network (Jaccard 0.0000). The FAIL is therefore attributable to an
  **implementation choice**, not to a property of the model. **This is an
  explanatory footnote, not a retraction.**
* **EQ2: `NEGATIVE` (construct adjudication), D-1 returning `negative-A`.**
  The J-lens localisation method did not yield a usable band in this
  implementation at this scale. R-2 was not authorised.

### EQ2 facts that bear directly on P-0's design

On `Qwen2.5-7B-Instruct` / `Qwen3-1.7B` / `gpt2`:

* Late-layer readability is **indistinguishable from the plain logit lens**
  (J-lens / logit-lens peak ratios 1.100 / 0.986).
* The only positive residue: on the 7B, layers 13–21 give a plain logit-lens
  readrate of exactly 0.0000 while the J-lens is non-zero (0.0011–0.0132), but
  **every layer except 21 sits below the random-lens null ceiling of
  0.004204**. Layer 21 is about 12 hits. **This must not be written up as a
  discovery.**
* `J`'s identity energy share climbs monotonically with depth: layer 0 →
  0.004, 18 → 0.169, 21 → 0.469, 23 → 0.640, **26 → 0.749**, with a
  best-scaling α ≈ 1.0 over layers 23–26. **The rank readout is invariant to
  scalar scaling**, so a late `J ≈ αI` is equivalently degenerate.
* Output adjacency is negligible: intermediate = model top-1 for 0.0053 of
  items.
* Peak absolute readability is only 8.46%, and the band appears at roughly
  74–78% depth. The paper's "middle layers" prior **does not transfer to
  shallow models**. The memorandum's "layers 11–26, sixteen layers" prior is
  **void**.

### EQ2's heaviest limitation, which P-0 exists to repair

> This study **never obtained a passing positive control**. Consequently "the
> J-lens method does not hold" and "we did not drive the lens as its authors
> intended" **cannot be distinguished**. The negative conclusion is strong
> about **our execution** and weak about **the method itself**.

And one level deeper: **we never had a known-positive object at all.** A
positive control needs ground truth, and we merely **assumed** that
Qwen2.5-7B-Instruct exhibits the phenomenon — an assumption never argued for.
Under the original design this ambiguity **could never be closed**.

## 3. What P-0 answers, and why it comes before checking the instrument

EQ2's negative admits four explanations; only three were ever considered.

1. The phenomenon does not exist (**we have no standing to assert this, see
   section 8**).
2. The phenomenon exists but only at larger scale; 1.7B / 7B are too small.
3. Our instrument, or our use of it, is wrong.
4. **Those items never forced the model to compute an intermediate at all.**

**The fourth was never checked, is the cheapest to check, and is the most
likely to be true.** A model may well answer a multi-hop item by direct
retrieval, skipping the intermediate. If the intermediate is never computed
there is nothing to read, and the J-lens's failure to read it says nothing
about the lens.

The old ordering was: assume the items are valid → assume the model exhibits
the phenomenon → test the instrument. **Three assumptions stacked; a collapse
at any level presents identically as "the instrument failed", and the levels
cannot be told apart.** P-0 detaches the bottom one and tests it alone.

## 4. Executing P-0

### Method: causal patching (activation patching)

**Crucial property: patching uses no part of `J`.** Ground truth must be
established by a method **independent of the instrument under test** — the very
thing that has been missing. **Nothing that uses `J` may enter P-0's
ground-truth path.**

Procedure: a clean input versus an input whose intermediate has been
destroyed; patch the residual stream layer by layer; measure the change in
output. If the intermediate really is computed and used, there will be a clear
causal-effect curve at specific layers.

* Use the **existing** multihop items; author no new data.
* **Roughly 200 items suffice** for localisation; there is no need to run all
  937. The sampling method must be pre-registered.
* About 27 layers × 200 items × 2 forward passes ≈ 10,000 forward passes,
  expected to cost 1–2 GPU-hours.

### The threshold must be calibrated against a zero-intervention null, never chosen

EQ2's lesson: using a weak model as the null produces a small signal rather
than a null hypothesis, and the criterion then manufactures a band out of that
small signal. **The same lesson transfers directly.**

The threshold for "the causal effect is significant" must be calibrated by a
**zero-intervention null** — patching an object that by construction should
have no effect (an irrelevant position, a random layer, norm-matched random
activations). Run **at least 5 independent replicates**, and take the
**maximum** of the per-replicate confidence bounds as the ceiling
(the conservative direction). The confidence level is 95% (statistical
convention, not a fitted value).

### What must be committed before anything is run

**Nothing may be patched until all of the following are committed and pushed.**

1. The item sampling method and its random seed.
2. The decision rule for "the intermediate is causally used", including the
   construction of the zero-intervention null and its replicate count.
3. **The wording of both conclusions, fixed verbatim** — how "there is a causal
   effect" and "there is no causal effect" will each be recorded, and what each
   would mean. **Fixed before any data is seen.**
4. **An OD-011 non-vacuity demonstration**: feed the zero-intervention null
   itself, pure noise, and an all-zero effect curve into the decision
   procedure; all three must return "no causal effect". **Real data may not be
   touched until this passes.**
5. **An OD-017 conformance audit**: a line-by-line comparison of
   [registered text vs implemented behaviour]. The audit must **compare the
   live values of imported modules**; it may not rely on comments or a
   hand-written "they agree" table, since such a check could never fail.

### The two roads out

* **No causal effect** → **EQ2's negative is fully explained**: the items
  failed, not the method. The conclusions of the past 39 hours need rewriting.
  **This is good news, because it is repairable.** Stop and report; do not
  repair the items yourself.
* **A causal effect** → we hold, **for the first time**, independently
  established ground truth, and we know which layers carry the intermediate.
  Proceed to P-0b.

## 5. P-0b (entered only if P-0 finds a causal effect)

At the layers patching points to, ask: **can the J-lens read the intermediate?
Can the plain logit lens?**

All three outcomes need their wording pre-registered:

* **J reads it, logit does not** → the instrument works; EQ2's negative is a
  substantive result about those models and it stands.
* **Neither reads it** → the instrument does not work, and this time
  **definitively**; the ambiguity closes.
* **Both read it** → this rank readout cannot isolate `J`'s contribution.
  **This failure mode was never previously considered**, and it calls for a
  different readout, not a different model.

## 6. P-0c (fallback, only if neither P-0 nor P-0b decides)

Train a small transformer on a two-step task with an intermediate we define, so
ground truth is exact. **Transfer is poor, so this is a fallback and not the
main line.** The design must keep the intermediate **out of every item's output
tokens**, or the logit lens reads it directly and `J` has no room to prove
anything.

## 7. Stop-loss (fixed before the run; not modifiable during it)

* Budget used: **39.066 / 240** GPU-hours.
* **The J-lens route gets at most 15 further hours** (P-0 + P-0b + any
  necessary P-0c), i.e. a cumulative ceiling of **54.066**.
* On reaching it without a passing positive control → **abandon the J-lens
  route**; P-4 localises on some other basis. **This needs no further
  consultation; it is already decided.**

## 8. Mechanisms already shown to work; continue to use them

1. **The directionality criterion (precedent).** Moving the implementation
   toward the registered text is **fixing a bug**; moving the registered text
   toward the data is **p-hacking**. **The difference is the direction, not the
   outcome.**
2. **Post-hoc is not automatically illegitimate; the direction decides.**
   Precedent: OA-005 was a post-hoc **tightening**, and it stopped a false
   positive — had it loosened instead, an instrument whose readout is
   indistinguishable from the logit lens would have gone on to spend `T`'s
   budget.
3. **Asymmetric motivation must be labelled.** If a check would only have
   occurred to you on an unfavourable result, say so plainly, and explain that
   its legitimacy comes from **decoupling the result from the go/no-go
   decision in advance**.
4. **Every criterion must pass an OD-011 non-vacuity demonstration and an
   OD-017 conformance audit before it runs.** DC-005 was found only because it
   produced an anomalous result; had it produced a plausible one it would never
   have been found — **and that is heavier than DC-005 itself**.

## 9. Stop conditions

Any of the following means **stop, commit, report** — do not self-repair and do
not self-amend a criterion:

1. Any OD-011 non-vacuity case fails.
2. The OD-017 audit finds any registered criterion diverging from its
   implementation.
3. Continuing would require reading `lens_A` / `lens_B` or touching `T`.
4. Continuing would require modifying EQ1's criteria, estimand, thresholds,
   splits or interpretation.
5. A create-only upload hits an `If-None-Match` precondition failure.
6. Anything that would require a reboot / resize / configuration change / NSG
   rule in order to continue.
7. Cumulative usage reaches 54.066 GPU-hours.
8. Any situation in which you want to revise a pre-registered criterion —
   **stop and ask; do not change it yourself**.

## 10. Reporting

* Every OD-017 conformance entry; all three OD-011 demonstration results.
* The per-layer causal-effect curve from patching, and the zero-intervention
  null ceiling.
* **Whether the intermediate is causally used, and if so at which layers.**
* If P-0b is entered: which of the three outcomes obtains.
* Resource counts (this route x/15, cumulative x/240), VM wall-clock, and
  allocated GPU-hours.
* Any new DC / IMG / HB / OD / OA entries.

## 11. Claims that may not be made

Nothing may state, imply, or let a reader infer:

* that **J-space exists or does not exist**;
* that **the paper is wrong** — it measured Sonnet 4.5, we measure open models
  an order of magnitude smaller, and absolute readability already differs by an
  order of magnitude;
* that **the published lenses are defective** — what we measure is **the result
  of our use** of those external artifacts, and a problem with the artifacts
  cannot be distinguished from a problem with our usage;
* **how `T` would behave** — `T` has never been measured;
* that internal causal reasoning machinery exists; any training-causal effect
  of distillation; that attention / embeddings / normalisation or whole-model
  differences have been explained;
* anything about consciousness.

Additionally: **gpt2's J-lens / logit-lens ratio of 1.750 is counting noise**
(about 7 hits against 4 at n ≈ 910) and must not be read as "the Jacobian
contributes most strongly on gpt2", nor as any pattern at all.

**P-0 is item-validity verification. No result it produces is a scientific
discovery.**
