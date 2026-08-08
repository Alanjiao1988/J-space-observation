# Study 3 - methods sources

Primary sources consulted while drafting the Study 3 interface-calibration protocol.

Every entry below was retrieved from its publisher record (ACL Anthology or arXiv) during the
design round and its title, author list and venue were read from that record rather than from a
secondary summary. Nothing here is a blog post, a leaderboard, or a survey restatement.

**Scope note.** These sources motivate the *risks* Study 3 is designed to detect. None of them is
evidence about this repository's checkpoints, and none of them is used to predict what Study 3
would find. They constrain the design; they do not anticipate the result.

**Citation correction.** The design authority named the fourth source below as "Lyu et al.". The
publisher record gives the authors as Wenjie Zhou, Qiang Wang, Mingzhou Xu, Ming Chen and
Xiangyu Duan. The verified attribution is used here. The paper identity, venue and URL named in
the authority are otherwise correct.

---

## S-01 - Option order changes accuracy

- **Title.** Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions
- **Authors.** Pouya Pezeshkpour, Estevam Hruschka
- **Venue.** Findings of the Association for Computational Linguistics: NAACL 2024, pages 2006-2017
- **URL.** https://aclanthology.org/2024.findings-naacl.130/
- **DOI.** 10.18653/v1/2024.findings-naacl.130

**Methodological point taken.** Reordering the answer options - a transformation that changes
nothing about the question - moves benchmark accuracy by roughly 13 to 85 percent depending on
model and benchmark, and the effect survives few-shot demonstrations. The authors attribute the
sensitivity to cases where the model is uncertain between its top two or three candidates, where
placement then decides the outcome. They further report that placing the top two candidates first
and last amplifies the bias while placing them adjacently mitigates it.

**How Study 3 uses it.** This is the direct justification for stratum `K5` and Gate `I3`. It is
why option position is counterbalanced by construction rather than randomized and hoped for, why
the four cyclic permutations are the registered default, and why a maximum position-or-permutation
effect is pre-specified instead of being estimated after the fact.

**Limitation of application.** The reported magnitudes come from large general benchmarks and much
larger models than the 1.5B checkpoints registered here. The *existence* of the risk transfers; the
*size* does not, and no numeric expectation was imported from this paper into any Study 3 threshold.

---

## S-02 - Label tokens carry token and position preferences

- **Title.** Large Language Models Are Not Robust Multiple Choice Selectors
- **Authors.** Chujie Zheng, Hao Zhou, Fandong Meng, Jie Zhou, Minlie Huang
- **Venue.** arXiv:2309.03882 (ICLR 2024)
- **URL.** https://arxiv.org/abs/2309.03882

**Methodological point taken.** Across 20 models and three benchmarks the authors isolate a
"selection bias": a prior preference for particular option-ID tokens such as A. They attribute it
primarily to *token bias* - the model assigns more probability mass to specific option-ID tokens a
priori, before the content is taken into account. Their debiasing method estimates that prior by
permuting option contents on a small subset and then removes it.

**How Study 3 uses it.** This is the specific mechanism that makes a restricted A/B/C/D logit read
(`S1`) risky as a measurement device, and it is why the panel contains three surfaces that do not
read option-ID tokens at all. It also motivates the selected-label uniformity band in Gate `I3`:
on a bank balanced by construction, a strongly non-uniform selected-label distribution is evidence
about the instrument.

**Limitation of application.** Study 3 deliberately does **not** adopt a debiasing correction. The
question is whether an interface is adequate as-is, not whether a post-hoc correction can rescue
it. Importing a debiasing step would change the object under study. This source also cannot be
used to explain any past result in this repository.

---

## S-03 - First-token probability can disagree with generated text

- **Title.** Look at the Text: Instruction-Tuned Language Models are More Robust Multiple Choice
  Selectors than You Think
- **Authors.** Xinpeng Wang, Chengzhi Hu, Bolei Ma, Paul Roettger, Barbara Plank
- **Venue.** arXiv:2404.08382
- **URL.** https://arxiv.org/abs/2404.08382

**Methodological point taken.** Ranking candidates by the log probability of the first token and
reading the model's actual text answer are different measurements, and for instruction-tuned models
they disagree. Crucially, where they disagree, the *text* answer is the more robust of the two under
question perturbation - and the robustness advantage grows with the mismatch rate, exceeding even
first-token probabilities that have been debiased by a state-of-the-art method.

**How Study 3 uses it.** This is why `S4`, bounded minimal-answer generation, is in the panel at all
despite its cost and its unfairness across checkpoint types, and why surface *disagreement* is a
named validation target (`VT8`) rather than a nuisance. It is also why `S1` is described as the
legacy comparator rather than the default.

**Limitation of application.** The finding is strongest for instruction-tuned models; two of the
three registered 1.5B roles are not instruction-tuned. It therefore cannot be assumed that the text
answer is more robust for the base or distilled checkpoints, which is precisely why Study 3 measures
rather than assumes. This source also does not license treating `S4` as the surface a later causal
study should use.

---

## S-04 - Knowledge-equivalent rewrites destabilize individual-item accuracy

- **Title.** Revisiting the Self-Consistency Challenges in Multi-Choice Question Formats for Large
  Language Model Evaluation
- **Authors.** Wenjie Zhou, Qiang Wang, Mingzhou Xu, Ming Chen, Xiangyu Duan
- **Venue.** Proceedings of LREC-COLING 2024, pages 14103-14110
- **URL.** https://aclanthology.org/2024.lrec-main.1229/

**Methodological point taken.** The authors construct three knowledge-equivalent variants - option
position shuffle, option label replacement, and conversion to a True/False format - and test models
from 6B to 70B across pretrained, supervised-fine-tuned and RLHF types. Accuracy on *individual
questions* is not robust to these variants, and instability is most pronounced in smaller models
(below roughly 30B) and in pretrained checkpoints. They argue consistent accuracy across variants
is the more reliable evaluation metric.

**How Study 3 uses it.** Two design consequences. First, it justifies the label-set replacement
condition inside `K5` as a distinct transformation from position shuffling. Second, and more
importantly, it is the reason the robustness gate is stated as *equivalence* over conditions rather
than as a single pooled accuracy: consistency across variants is the quantity of interest.

**Limitation of application.** Every model the authors tested is at least four times the size of
the registered 1.5B checkpoints, and their smallest bracket already shows the worst instability.
Extrapolating downward would predict severe instability here - so the draft explicitly does **not**
extrapolate, and no Study 3 threshold was set from this paper's numbers.

---

## S-05 - Multiple-choice and open-response surfaces measure different behavior

- **Title.** Can Multiple-choice Questions Really Be Useful in Detecting the Abilities of LLMs?
- **Authors.** Wangyue Li, Liangzhi Li, Tong Xiang, Xiao Liu, Wei Deng, Noa Garcia
- **Venue.** Proceedings of LREC-COLING 2024, pages 2819-2834
- **URL.** https://aclanthology.org/2024.lrec-main.251/

**Methodological point taken.** Evaluating nine models on four QA datasets in two languages, the
authors find order sensitivity favouring the first position in bilingual multiple-choice settings,
and - the point that matters most here - a relatively low correlation between answers to
multiple-choice questions and answers to long-form generation questions *for identical questions*,
measured over direct outputs, token logits and embeddings. They also report that multiple choice is
less reliable than long-form generation by expected calibration error, and that higher consistency
does not imply higher accuracy.

**How Study 3 uses it.** This is the basis for treating the four surfaces as genuinely different
instruments that may not be pooled, and for the explicit statement in `VT8` that agreement among
surfaces is descriptive and must not by itself become a selection rule. It is also why `S1` and `S2`
are never pooled even though both are single-position logit reads: one shows the options and one
does not, so they pose different tasks.

**Limitation of application.** Their long-form setting is knowledge-intensive open generation,
whereas `S4` here is deliberately bounded to a final answer with no rationale. The finding that the
two formats diverge transfers; the specific magnitude of divergence does not, and a divergence
observed in Study 3 would need its own explanation rather than a citation.

---

## S-06 - Binding an answer to its symbol is a distinct ability

- **Title.** Leveraging Large Language Models for Multiple Choice Question Answering
- **Authors.** Joshua Robinson, Christopher Michael Rytting, David Wingate
- **Venue.** arXiv:2210.12353 (ICLR 2023)
- **URL.** https://arxiv.org/abs/2210.12353

**Methodological point taken.** The authors name and isolate *multiple choice symbol binding*
(MCSB): the ability to associate an answer option with the symbol that denotes it. Presenting
question and options jointly and having the model emit the symbol only works if the model has this
ability, and the ability *varies greatly by model*. Where it is present, the symbol-emitting format
substantially outperforms the traditional cloze-style scoring across 20 datasets.

**How Study 3 uses it.** This source supplies the study's central construct. Stratum `K1` -
explicit-answer binding, where the correct content is stated outright and the only remaining task
is to map it to a label - exists specifically to measure MCSB in isolation from task competence,
and Gate `I1` is the gate that tests it. It is also the reason the draft insists that a label-read
failure and a task failure are different things that a pooled accuracy cannot separate.

**Limitation of application.** The paper's demonstration that MCSB varies by model was established
on models of a different generation and scale, and the direction of its headline finding - that the
symbol format is *better* where MCSB is present - must not be read as a prediction that `S1` will
perform well here. In this repository MCSB is an open question, not a background assumption.

---

## Synthesis: the five risks the design must address

| # | Risk established in the literature | Where Study 3 addresses it |
| --- | --- | --- |
| 1 | Option order changes accuracy, sometimes drastically (S-01, S-04, S-05) | stratum `K5`, Gate `I3` maximum position-or-permutation effect |
| 2 | Label tokens carry token and position preferences independent of content (S-02, S-06) | surfaces `S2` and `S3` avoid label tokens entirely; Gate `I3` selected-label uniformity band |
| 3 | First-token probability can disagree with what the model would write (S-03) | surface `S4` in the panel; `VT8` surface-agreement target |
| 4 | Multiple-choice and open surfaces measure different behavior (S-05) | strata and surfaces are never pooled; per-cell gate evaluation |
| 5 | A non-significant difference is not invariance (S-01, S-04) | Gate `I3` is an equivalence test with a pre-specified margin, never an absence-of-evidence argument |

## What this literature does not license

- It does not license any expectation about how the registered checkpoints will behave.
- It does not license any explanation of Study 1's or Study 2's outcomes. Those studies are closed
  and their results are frozen; citing a mechanism from this literature as the cause of a past
  result here would be an unregistered post-hoc claim.
- It does not license importing a debiasing or calibration correction into the measurement itself.
- It does not license any claim about reasoning, chain-of-thought internalization, distillation, or
  mechanistic interpretability. Every source above is about measurement instruments, which is
  exactly and only what Study 3 is about.
