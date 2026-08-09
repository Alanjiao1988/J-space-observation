# Study 3 - positive-reference candidate dossier

- **Document class:** positive-reference candidate dossier
- **Draft version:** draft-v0.3
- **Operator decision addressed:** OD2
- **Disposition of OD2:** `UNRESOLVED_BLOCKING_OPERATOR_DECISION`
- **Selection status:** `UNSELECTED`
- **Expanded selection status:** `NO_POSITIVE_REFERENCE_IS_SELECTED_PREFERRED_PINNED_REVISION_RESOLVED_DOWNLOADED_TOKENIZED_LOADED_OR_PREQUALIFIED_IN_THIS_ROUND`
- **Amendment note:** the v0.2 independent methods review recorded finding
  `S3MR-020`, that this dossier attributed its own obligation to defect `D-07`
  when the authoritative record assigns the positive-reference circularity and
  chance-level-floor issue to `D-04` and assigns `D-07` to the separate pooling
  defect. Both back-references are corrected to `D-04` in this amendment. The
  correction is a traceability repair; it resolves nothing about OD2.

---

## 0. What this document is, and what it is not

Gate I4 requires an independently prequalified capable reference, so that a
target failure through a given interface can be attributed to the target rather
than to the interface. draft-v0.1 named that requirement without doing any
primary-source work behind it, which the operator review recorded as defect
D-04, the positive-reference circularity and chance-level-floor defect, and left
OD2 blocking. Defect `D-07` is a different defect, that pooling could mask a
failed cell, and is not the obligation this dossier discharges.

This dossier is that primary-source work. It is a **candidate evaluation** only.
Its selection status is `UNSELECTED` and remains `UNSELECTED` at the end of the
v0.3 amendment round.

**Nothing in this document selects, pins, downloads, tokenizes, loads, runs or
prequalifies any model.** Producing it involved no model operation of any kind.
The operation counters in the protocol remain at zero and are checked by the
committed test.

The dossier **may recommend** a first candidate for a future single-candidate
prequalification stage. It **may not** make that candidate authoritative. Only a
separate operator authority can do that, and only by pre-registering exactly one
candidate, one immutable revision, the runtime, the dtype, the native wrapper,
the qualification interface, the qualification bank, the capability floor, the
sample size and the stopping rule **before** any model operation occurs.

---

## 1. Hard requirements a positive reference must satisfy

These are carried forward from the protocol and are not negotiable at dossier
stage.

1. Pinned repository identity and an immutable revision hash.
2. A license permitting research use and redistribution of derived measurements.
3. It must never be qualified, tuned or selected on the Study 3 confirmation
   bank. The confirmation bank must be physically absent from the image in which
   prequalification runs.
4. It must be runnable on the registered Azure GPU route, or the route must be
   changed by a separate authority before it is used.
5. Its qualification must be run through a canonical interface **outside** the
   candidate panel, so that qualifying the reference cannot pre-judge the
   interface comparison that Gate I4 is supposed to support.

---

## 2. Compute envelope

The registered GPU route is a Tesla T4 with 16 GiB of memory, fp16 supported and
no bfloat16 tensor-core path. The relevant consequence is arithmetic, not
empirical:

| Parameter class | Approximate fp16 weight footprint | Verdict on a 16 GiB T4 |
| --- | --- | --- |
| 1.5B | ~3.1 GiB | comfortable; this is the Study 2 reference point |
| 3B-4B | ~6.2-8.0 GiB | fits with activation and KV headroom |
| 7B-8B | ~15.2 GiB and above | no dependable headroom for activations and KV cache |
| above 8B | exceeds capacity in fp16 | does not fit |

**Quantization is not a way out.** The interfaces under test read logits. int8 or
4-bit quantization changes the numerics of exactly the quantity being measured.
If a quantized checkpoint were ever used it would have to be registered as a
distinct checkpoint identity - "quantized checkpoint X", never "X" - and the
change would have to be justified on its own terms. Quantization must never be
applied merely to force a model to fit.

A larger GPU SKU on the registered Azure route removes the constraint at higher
cost. That is an operator decision, not a drafting decision.

---

## 3. Candidate 1 (`UNSELECTED`; retained for a future single-candidate stage)

### Qwen/Qwen3-4B-Instruct-2507

| Field | Value | Source |
| --- | --- | --- |
| Repository | `Qwen/Qwen3-4B-Instruct-2507` | model card |
| License | `apache-2.0` | repository metadata, read 2026-08-08 |
| Total parameters | 4.0B (3.6B non-embedding) | model card |
| Layers | 36 | model card |
| Attention | GQA, 32 query heads, 8 key/value heads | model card |
| Native context | 262144 | model card |
| Thinking mode | non-thinking only; no thinking blocks emitted | model card |
| Minimum runtime | `transformers >= 4.51.0` | model card |
| Vendor-reported MMLU-Pro | 69.6 | model card |
| Vendor-reported GPQA | 62.0 | model card |
| Vendor-reported AIME25 | 47.4 | model card |
| Vendor-reported IFEval | 83.4 | model card |

**Status: `UNSELECTED`.** Retaining a candidate in this dossier is not preferring
it. The v0.3 amendment round performed no selection, no preference ordering, no
revision resolution, no download, no tokenizer construction, no weight load and no
prequalification against this or any other repository. The paragraphs below record
why an operator resolving OD2 might consider it first; they do not choose it.

**Why an OD2 authority might consider it first.**

- It is the smallest checkpoint examined here that is plausibly capable on
  depth-2 and depth-3 arithmetic compositions while fitting the registered T4
  route in fp16 with real headroom.
- Its license permits research use and redistribution of derived measurements.
- It is documented as non-thinking, so there is no hidden reasoning-budget
  parameter that would silently change what the interface observes between runs.
  A model that sometimes emits a thinking block and sometimes does not would make
  output-validity scoring depend on an uncontrolled latent mode.

**Disqualifying-risk register.**

| Risk | Status |
| --- | --- |
| Requires `transformers >= 4.51.0`, so the Study 2 image at transformers 4.46.3 **cannot be reused unchanged** | confirmed from the model card; a new registered image would be required |
| Exact repository revision | unpinned; an observed revision hash was recorded in the session log purely as an observation and is explicitly **not** a pin |
| Tokenizer behaviour on the frozen answer domain | unmeasured; single-token eligibility for the required roles is unverified |
| Short-sequence fp16 margin on a T4 | unmeasured; the footprint arithmetic above is not a measurement |
| Whether it clears a K4-shaped capability floor | unmeasured; this is the entire point of a prequalification stage |
| Vendor-reported scores | vendor claims on the vendor's harness; not reproduced here and not usable as evidence about this repository |

---

## 4. Candidate 2 (`UNSELECTED`; stronger, but not feasible on the registered route)

### Qwen/Qwen2.5-Math-7B-Instruct

| Field | Value | Source |
| --- | --- | --- |
| Repository | `Qwen/Qwen2.5-Math-7B-Instruct` | model card |
| License | `apache-2.0` | repository metadata, read 2026-08-08 |
| Minimum runtime | `transformers >= 4.37.0` | model card |
| Vendor-reported MATH (7B, tool-integrated reasoning) | 85.3 | release note and model card |
| Scope warning | mainly supports English and Chinese mathematics via chain-of-thought and tool-integrated reasoning; not recommended for other tasks | model card |

**Why it is not recommended for the registered route.**

- Its approximately 8B-parameter weights are not a safe fp16 fit on a 16 GiB T4
  once activations and KV cache are accounted for. It would require a larger GPU.
- Quantizing it to fit is prohibited for the reason given in section 2.
- Its strongest published numbers are obtained with tool-integrated reasoning.
  A positive reference that needs an external tool to reach its headline
  capability is a poor control for an interface study, because the tool sits
  between the model and the interface being tested.
- The card's own scope warning narrows it to mathematics. A positive reference
  whose competence is domain-restricted makes an I4 failure ambiguous between
  "the interface is inadequate" and "the reference was outside its domain".

It is retained in the dossier as the stronger same-generation alternative, for an
operator who is prepared to change the GPU SKU.

---

## 5. What is deliberately not concluded

- No candidate is selected.
- No revision is pinned. Any revision hash observed while reading a model card is
  an observation with a timestamp, not a registration, and must be re-resolved and
  registered by the authority that pins it.
- No runtime, dtype or wrapper is registered.
- No capability floor is set for any specific candidate. The floor arithmetic in
  `studies/study3/analysis/design_statistics.py` is generic and model-free.
- No claim is made that either candidate would pass Gate I4.
- No candidate is preferred, prequalified or prioritised in a way that binds the
  authority that resolves OD2. Both candidates are `UNSELECTED`.
- No candidate has been downloaded, revision-resolved by downloading, tokenized,
  loaded, run, scored, generated from or measured in any way.

---

## 6. Rules that bind whatever authority resolves OD2

1. **Exactly one candidate.** The prequalification stage P3-Q must preregister a
   single candidate. A panel of candidates reintroduces selection.
2. **No automatic fallback.** There is no 3B-to-7B escalation. If the
   preregistered candidate fails its floor, P3-Q stops. Trying a different
   candidate requires a new authority **and** a fresh qualification bank.
   This is what removes adaptive reference shopping: without it, the reference
   would be chosen by whichever model happened to pass, which is a selection
   effect dressed up as a control.
3. **Bank isolation.** Prequalification runs only on items drawn from a
   prequalification seed disjoint from both the development and the confirmation
   seeds, in an image from which the confirmation bank is physically absent.
4. **Output restriction.** P3-Q emits a pass or fail against a pre-registered
   floor, and nothing else. It may not be reported as a Study 3 result and may
   not influence interface selection.
5. **Interface isolation.** The qualification interface is a separate canonical
   interface outside the candidate panel.
6. **Image registration.** Because the recommended candidate needs a newer
   transformers than the Study 2 image provides, the authority that resolves OD2
   must also register the new image. Silently upgrading the existing image would
   change the runtime under previously registered work.

---

## 7. Disposition

OD2 remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. Unresolved item `UR-22`,
the external qualification interface for the positive reference, likewise remains
`UNRESOLVED_BLOCKING_OPERATOR_DECISION` after the v0.3 amendment round.

This dossier discharges the drafting obligation attached to defect D-04: the
positive-reference requirement is now backed by primary-source evaluation of
named candidates against the registered compute envelope, with an explicit
feasibility verdict and an explicit risk register. It does not, and must not,
discharge OD2 itself.

The remaining authority required is an operator decision that preregisters a
single candidate and its complete qualification specification. No such authority
exists.
