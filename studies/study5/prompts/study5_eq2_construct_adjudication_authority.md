# Study 5-EQ2 — construct adjudication authority

This authority is published alone, as the sole path in its commit, before any
EQ2 write and before any curve is computed. It governs one invocation only.

It authorizes **construct adjudication**. It does not authorize confirmation, it
does not authorize any Study 5 causal measurement, and no state it can reach is
a scientific result.

---

# 0. Provenance

| Field | Value |
| --- | --- |
| Approved by | operator, in session, 2026-08-28 |
| Predecessor study | `STUDY5_EQ1` |
| Predecessor terminal state | `STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE` |
| Predecessor branch | `alanjiao1988-study5-eq1-qualification` |
| Evidence ledger at start | `EV-0016` |
| Confirmation authorized | **false** |

---

# 1. Why this authority exists

EQ1's Q-4a failed under criteria frozen before measurement. That failure stands
and is not revisited. But the failure is **diagnosable**, and two facts
external to our data point at the construct implementation rather than at the
model:

1. The paper computes excess kurtosis "of the logit distribution for the readout
   of a single (position, layer) **across a large data set of activations**",
   and reports the profile as *"near zero through the first third of the layers,
   increases beginning around a third of the way through the depth, and falls in
   the last few layers."* EQ1's measured profile is inverted at all three
   landmarks: its maximum is at the first layer, its minimum at mid-depth, and it
   is near-maximal in the last layers. EQ1's `DC-004` reasoning shows the
   statistic was taken over the **vocabulary axis**; the paper's wording admits a
   **dataset axis** reading.
2. Pre-fitted Jacobian lenses for 39 models — produced with the same official
   `anthropics/jacobian-lens` library, most of them on the same
   `Salesforce/wikitext` corpus — are publicly available, and a mid-depth
   workspace band has been reported across that sweep at scales including 8B.

Fact 2 makes "no band at 28 layers / 7B" an unlikely explanation and makes the
fitting corpus an unlikely explanation. Fact 1 names a specific, checkable
alternative.

This authority resolves the convention question **using evidence we do not
control**, and then re-runs the band criteria once.

---

# 2. What this authority is not

* It is **not** a relaxation of EQ1's margin, threshold, or any frozen
  criterion. No EQ1 criterion is loosened anywhere in this authority.
* It is **not** a re-fit. EQ1's `lens_A` and `lens_B` are reused byte-identically.
* It is **not** a corpus experiment. The corpus stays exactly as EQ1 fixed it.
* It is **not** a continuation of EQ1's phase plan. EQ1's P-3 terminated with
  EQ1 and is not reachable from here.
* It is **not** a scientific study. No estimand is measured.

---

# 3. Operator resource decisions

Identical to EQ1 §2, and extended:

1. Do not change the configuration of any existing VM. No resize, SKU change,
   redeploy, replace, clone or migrate.
2. Do not start, stop, deallocate, restart or reboot any VM. Every VM that is
   running stays running. A step requiring a reboot, driver change or resize is
   a hard blocker, not a fix.
3. Do not modify any disk, NIC, public IP, VM extension, managed identity, RBAC
   assignment, VNet, subnet or NSG.
4. Do not create or delete any Azure resource, and do not create or delete a
   blob container. New bytes go to new **paths** in the existing containers of
   `s4fm11ca457e105b29b7`.
5. Every existing blob is immutable. All uploads are create-only with
   `If-None-Match: *`. A precondition failure is a stop, never a retry with
   overwrite.
6. **The four `Standard_NC24s_v3` machines in resource group `TRAINING`
   (16× V100) remain running, remain idle, and remain untouched.** No NSG rule
   or any other configuration change may be made in order to reach them. They
   are in the frozen inventory; their correct role in this study is to stay
   unchanged.
7. No SAS token, no storage key, no subscription id, tenant id, full resource id
   or credential in any committed artifact.
8. Cost accrual is expected and intended. The invocation must not propose,
   imply or perform any cost-reduction action.

Opening and closing read-only inventory snapshots are taken and committed, with
the closing check being `closing == opening + registered deltas`, exactly and
only.

---

# 4. Registered external artifacts

All are MIT or Apache-2.0. None is encumbered.

### 4.1 Pre-fitted external lenses

Repository `neuronpedia/jacobian-lens`, revision
`0731326edff4ae730ffc5356fe1a4728c748b3a6`, licence MIT. Fitted with
`anthropics/jacobian-lens` (Apache-2.0) via Neuronpedia's `run-all-fit-lens.py`.

| Role | Path |
| --- | --- |
| Positive control | `qwen2.5-7b-it/jlens/Salesforce-wikitext/Qwen2.5-7B-Instruct_jacobian_lens.pt` (+ `config.yaml`, `_convergence.csv`) |
| Negative control | `gpt2-small/jlens/Salesforce-wikitext/gpt2_jacobian_lens.pt` (+ `config.yaml`, `_convergence.csv`) |
| Depth test | `qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_jacobian_lens.pt` (+ `config.yaml`, `_convergence.csv`) |

Optional extension, only if R-1 is inconclusive without it:
`qwen3-8b/…/Qwen3-8B_jacobian_lens.pt`, `qwen3-14b/…/Qwen3-14B_jacobian_lens.pt`.

**Comparability, recorded from the published configs:** the positive control was
fitted with `--dataset Salesforce/wikitext --dataset_config wikitext-103-raw-v1
--dataset_split train --max_seq_len 128 --dtype bfloat16 --n_prompts 1000
--stop_at_delta 0.002`, early-stopping at `prompts_fitted: 485`, with
`final_identity_distance: 0.578094` and `final_mean_rel_change: 0.00181395`.
EQ1's own fit used the same library, the same corpus family and the same
sequence length, with 600 rows per half. These are directly comparable; the
comparison must be stated explicitly in the R-0 report.

### 4.2 Control model weights

| Model | Revision | Licence |
| --- | --- | --- |
| `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` | apache-2.0 |
| `Qwen/Qwen3-1.7B` | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | apache-2.0 |
| `openai-community/gpt2` | `607a30d783dfa663caf39e06633721c8d4cfcd7e` | mit |

Acquired and byte-verified through the same content-addressed, create-only path
EQ1 used. No substitution. `trust_remote_code = false`.

### 4.3 Inherited, unchanged

`lens_A` and `lens_B` from EQ1, by their committed SHA-256. Read-only.
The heldout corpus rows from EQ1, by their committed hashes. Read-only.

---

# 5. Registered standing rules

### OD-011 — a check must be able to fail

Every check and every assertion carries a **demonstrated failing case**: a
negative test that feeds wrong input and proves the check reports FAIL. OD-003
guarantees a check *ran*; it cannot guarantee a check *can fail*. `IMG-001`
(heredoc reading empty stdin, exit 0, zero assertions executed) and `DC-003`
(`applied = bool(tokenizer.add_bos_token)`, an assertion that cannot fail) are
the same class and have now occurred twice.

**A check without a demonstrated failing case counts as not implemented.**

### OD-012 — commit before compute, enforced structurally

The adjudication rule, the chosen convention and every threshold are committed
before any curve is computed. Because both lenses already exist and
recomputation is cheap, "compute both conventions and keep the one with a band"
is trivially available and must be blocked by construction, not by intention:

* adjudication runs **only** on external control models;
* `lens_A` and `lens_B` **may not be read** until the convention is committed and
  its hash recorded;
* a committed check proves that every journal record referencing `lens_A` or
  `lens_B` carries a timestamp later than the convention-commit record.

### OD-013 — one variable at a time, order frozen now

Candidate explanations are tested in this order, which may not be changed,
parallelised or combined:

1. **readout convention** — specific evidence exists that it diverges;
2. **corpus** — Neuronpedia used the same `Salesforce/wikitext`, so this is
   already unlikely;
3. **scale / depth** — the external scale ladder answers this for free.

**EQ2 tests item 1 only.** Items 2 and 3, if still needed, belong to a successor
authority. Registering several candidates at once degrades into trying
combinations.

---

# 6. The adjudication ladder

Committed at R-0, before any curve is computed, and not changed thereafter.

* **A-1** — if `anthropics/jacobian-lens` @ `581d398613e5602a5af361e1c34d3a92ea82ba8e`
  provides an official readout / kurtosis path, adopt it. Record function name
  and source line. Adjudication ends.
* **A-2** — otherwise, adopt the convention that **reproduces the externally
  published band on the positive control** and **produces no band on the
  negative control**.
* **A-3** — if A-2 cannot discriminate, adopt the convention that reproduces the
  paper's published qualitative signature: *near zero through the first third,
  rising from about a third of the way through the depth, falling in the last
  few layers*. This signature is external and independent of any threshold we
  choose, and therefore cannot be tuned by us.

The two candidate conventions are:

* **V — vocabulary axis.** For a fixed `(position, layer)`, excess kurtosis over
  the vocabulary dimension of that readout. This is what EQ1 computed.
* **D — dataset axis.** For a fixed `(position, layer)`, excess kurtosis of the
  readout logit collected across a large set of activations.

If neither convention reproduces the external band on the positive control, the
readout path has a deeper defect: return to R-0 and **do not proceed to `T`**.

Band criteria and thresholds for R-2 must come from the external method and be
**calibrated on the positive control**, never on `T`.

---

# 7. Phase plan and budget

| Phase | Work | Budget |
| --- | --- | --- |
| **R-0** | Read official source. Acquire external lenses and control weights. Recover the external band method from primary sources. **Commit the adjudication ladder and thresholds.** | 0 h |
| **R-1** | Compute κ-vs-depth under conventions V and D on positive, negative and depth-test controls. Select and commit the single convention. | ≤ 6 h |
| **R-2** | Apply the committed convention to EQ1's sealed `lens_A` / `lens_B`. Re-run C1–C5 with externally defined, externally calibrated thresholds. | ≤ 4 h |
| **R-3** | Verdict, dossier, disclosure. | 0 h |

Total registered ceiling: **≤ 12 actively used GPU-hours**, denominated per
`OD-001`. VM wall-clock and allocated GPU-hours are reported separately and are
not bounded by this ceiling.

`batch_size = 1` for anything feeding a registered statistic. One isolated
worker per visible GPU, `CUDA_DEVICE_ORDER=PCI_BUS_ID`, single-device
`CUDA_VISIBLE_DEVICES`, bf16, no TP/PP/MIG/device_map auto/offload. Journal
records carry both container GPU index and physical GPU UUID (`OD-006`).

---

# 8. Result-to-claim truth table

| Result | Permitted reading | Forbidden reading |
| --- | --- | --- |
| Convention D reproduces the external band on the positive control, V does not | EQ1 reconstructed the paper's footnote incorrectly. EQ1's Q-4a FAIL is attributed to an **implementation defect**, not to the model | Not a retraction of EQ1's FAIL; EQ1's record stands unchanged |
| Neither V nor D reproduces the external band on the positive control | Our readout path has a deeper defect. **Return to R-0.** | Nothing whatsoever about `T`, which must not be touched |
| Correct convention yields a band on the positive control but **not** on `T` | Same architecture, same scale, same corpus, same library — and the distilled model shows no band. **This is a finding, not an instrument failure**, and it lands directly on Study 5's subject | Not "J-space does not exist at 7B"; not a training-causal claim about distillation |
| Correct convention yields a band on `T` | The Q-4a obstacle is removed. A successor authority may reopen the qualification path | No causal claim; no confirmation; no successor is automatic |
| `qwen3-1.7b` shows a band under the correct convention | "28 layers is too shallow" is externally refuted | Says nothing about whether `T` has a band |
| Negative control `gpt2-small` shows a band under the selected convention | The convention is not discriminative. **Adjudication fails**; do not proceed to `T` | Not a licence to pick the other convention on the basis of `T`'s result |

---

# 9. Hard blockers

Stop fail-closed, commit everything, report — do not repair:

1. Any VM configuration difference between opening and closing snapshots;
2. Any step requiring a reboot, driver change, resize or any §3 prohibited action;
3. A registered external artifact cannot be acquired byte-exactly;
4. A create-only upload hits an `If-None-Match` precondition failure;
5. `lens_A` or `lens_B` is read before the convention-commit record;
6. A check is found without a demonstrated failing case (`OD-011`);
7. Neither convention discriminates on the external controls;
8. The negative control shows a band under the selected convention;
9. Proceeding would require changing an EQ1 criterion, an estimand, a threshold,
   a split or an interpretation;
10. A protected historical artifact would have to be edited, or publication
    would require rewriting published Git history;
11. The registered accelerator ceiling is reached.

---

# 10. Publication discipline

* This authority is committed alone, as the sole path in its commit, on a new
  branch off EQ1's terminal commit, before any other EQ2 write.
* Fast-forward only. No merge into `main`, no rebase, no force-push, no history
  rewrite.
* Every EQ1, Study 4F, Study 4F-M1, Study 3R and Phase 1.0D artifact stays
  byte-identical.
* `paper/evidence_ledger.csv` stays at `EV-0016`.
* No GitHub Actions run is triggered.
* The predecessor branch and `origin/main` are refetched immediately before every
  publication; unexpected advancement stops the invocation.
* Full run record — journal, TIMELINE, resource accounting, traceability — is
  committed per `OD-003` / `OD-011` / EQ1 §9, at every phase boundary.

---

# 11. Registered terminal states

None of these is a scientific result.

* `STUDY5_EQ2_EXTERNAL_ARTIFACT_ACQUISITION_FAILED`
* `STUDY5_EQ2_NO_OFFICIAL_READOUT_AND_NEITHER_CONVENTION_DISCRIMINATES`
* `STUDY5_EQ2_NEGATIVE_CONTROL_CONTAMINATED`
* `STUDY5_EQ2_CONVENTION_ADJUDICATED_BAND_ABSENT_ON_TARGET`
* `STUDY5_EQ2_CONVENTION_ADJUDICATED_BAND_PRESENT_ON_TARGET`
* `STUDY5_EQ2_BUDGET_CEILING_REACHED_NO_REINTERPRETATION`
* `STUDY5_EQ2_EXECUTION_INTERRUPTED_NO_REINTERPRETATION`

`STUDY5_EQ2_CONVENTION_ADJUDICATED_BAND_ABSENT_ON_TARGET` means: under a
convention validated on an external positive control of the same architecture,
scale and corpus, the distilled target shows no mid-depth band. It is a finding
about **this checkpoint under this construct**. It is **not** evidence that
J-space is absent at 7B, and it may not be written up as such.

Only `STUDY5_EQ2_CONVENTION_ADJUDICATED_BAND_PRESENT_ON_TARGET` permits a
successor authority to reopen the qualification path, and no state reachable
here authorizes that successor automatically.

---

*End of authority. Nothing below this line is normative.*
