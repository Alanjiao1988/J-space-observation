Study 3 draft-v0.6 scoring-boundary calibration and P0-R1 authority

1. Sole authority, purpose, and controlling baseline

This file is the sole operator authority for one fresh-session calibration andregistration round in Alanjiao1988/J-space-observation.

The required starting origin/main is exactly:

dfbe6dd6c82fbe0e8906a4aa7f4df6b676496366

Its tree must begin 7779c8fd, HEAD == origin/main, and the worktree must beclean before any write. Resolve and record the complete tree ID before acting.If any starting-state fact differs, stop without changing the repository.

This authority has two and only two purposes:

amend the unfrozen Study 3 candidate from draft-v0.5 to draft-v0.6 to repairthe demonstrated S2/S3 scoring-surface defect and the eligibility-classifierpropagation defect; and

register, but not execute in the drafting session, one isolated P0-R1 modelfeasibility continuation that uses the unchanged P0 corpus.

This is not a fourth broad methods review, not formal execution, and not aclaim-bearing research round. It does not reopen Study 1 or Study 2. It does notauthorize a bank, seed, winner, confirmation access, positive reference, OD2 orUR-22 resolution, or an evidence-ledger row.

Commit a byte-identical copy of this authority as the first new repositoryobject. Publish that authority commit by non-force fast-forward before creatingany draft-v0.6 or P0-R1 artifact. Do not execute from rendered, retyped,reformatted, summarized, or copy-pasted text. If the uploaded bytes do notmatch the operator-supplied file, stop.

2. Facts accepted from the consumed P0-T round

Treat the published P0-T artifacts as immutable historical observations. Donot edit, replace, relabel, regenerate, or rerun them.

The controlling observations are:

all 4,902 member encodes round-tripped byte-exactly;

every applicable byte-distinct presentation pair had distinct full token-IDsequences for RT, RL, and RI;

S1 label surfaces were distinct single tokens under both alphabets for allthree roles;

S2 and S3 had exact prompt/token parity and K6-SEP was structurally absent;

each S2/S3 candidate surface " 0" through " 9" encoded as exactly twotokens, [220, digit], with the same first token and ten pairwise-distinctsecond tokens 15 through 24 for all three roles;

no model download, weight load, GPU job, forward pass, decode, generation, orscored row occurred; and

the emitted historical state remainsSTUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE.

The historical state is not rewritten even though the published dispositionalso demonstrates that it was over-severe: a role-level S2 failure wasincorrectly propagated to 27 mechanically valid S1 cells, producing ineligiblerows with empty reason lists. The raw result, receipt, disposition, counters,and hashes remain historical truth about what that harness emitted. A newderived calibration view may correct the algorithm, but may never edit the oldview in place.

The 4,956 historical tokenizer encodes remain cumulative and non-resettable.No P0-T encode is repeated in this round.

3. Binding operator decision for draft-v0.6

3.1 Preserve the visible answer surface

Keep the registered S2/S3 answer cue and candidate bytes unchanged:

prompt answer cue: Answer: with no trailing whitespace;

complete candidate surfaces: " 0" through " 9", each with exactly oneleading U+0020 SPACE;

S1 rendering and scoring bytes: unchanged;

S4 rendering, wrapper, parser, and diagnostic-only status: unchanged.

Do not remove the space, move it into the global answer cue, change numericanswers to letters, or alter any question, option, instruction, contrast,nuisance state, tuple, ground truth, or candidate mapping.

3.2 Register first-discriminative-token scoring for S2/S3

For each pinned role tokenizer, factor every complete S2/S3 candidate tokensequence as:

candidate_d = common_prefix || discriminant_d

The candidate set is eligible only if all of the following hold:

every complete candidate is exactly two tokens;

the first token is identical for all ten candidates;

that common token decodes byte-exactly to the registered leading U+0020;

the second token IDs are pairwise distinct and map byte-exactly to 0 through9 in registered order; and

no BOS, EOS, chat template, normalization, padding, truncation, or implicitwhitespace transformation participates in the factorization.

For the three currently pinned roles, the recorded P0-T evidence fixes thecommon-prefix token as 220 and the discriminant token IDs as 15 through24. The implementation must derive and verify these values from the immutablepublished P0-T result rather than transcribe them as an unverified assumption.

For S2, form the scoring context as the registered prompt token IDs followed bythe verified common-prefix token. Perform one ordinary prefill evaluation onthat context and read the next-token logit vector only at the ten verifieddiscriminant token IDs. Map the deterministic restricted argmax back to thecomplete registered candidate surface. The common prefix is a teacher-forcedcandidate prefix; it is not a prompt-rendering change and is not a generatedtoken.

For S3, reuse the exact S2 discriminant-position logit vector on CPU. S3 addszero model evaluations, model loads, prefills, decodes, or generations.

Do not score the shared first token, pretend the two-token candidate is onetoken, sum unrelated positions, use free generation, or introduce a newcalibration parameter.

3.3 Required equivalence proof

Register and mechanically assert the following identity for every prompt xand candidate digit d, where u is the common token and v_d is the uniquedigit token:

P(u, v_d | x) = P(u | x) * P(v_d | x, u)

Because P(u | x) is common to every candidate, the restricted ranking isexactly:

argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)

This is an exact factor cancellation, not an approximation. It is valid herebecause the registered decision statistic is deterministic candidate argmaxand all ten candidates have the same two-token structure and common prefix.Preserve the registered digit-order tie break.

The v0.6 claim must not extend this equivalence to arbitrary multi-tokencandidates, unequal lengths, non-common prefixes, summed log probabilities,free generation, or any tokenizer not separately pinned and verified.

4. Eligibility classifier repair

Create a versioned successor classifier. Do not overwrite the historical P0-Tresult or rely on its role-level eligibility flag.

Eligibility must be computed at the narrowest applicable key:

candidate-surface eligibility: role × profile;

presentation-pair distinctness: role × profile × contrast;

structural absence: profile × contrast;

target-role executability: existence of at least one eligible, genuine,gate-bearing I3 contrast among selectable S1, S2, and S3 for that role.

S4 is diagnostic-only and can never satisfy target-role executability.not_applicable can never become eligible, ineligible, a pass, a zero, adenominator row, or robustness evidence.

An ineligible row must contain at least one exact, local reason. An ineligiblerow with an empty reason list is a validator failure. A failure in S1 must notpropagate to S2/S3; a failure in S2/S3 must not propagate to S1; a failure inone role must not propagate to another role; and one contrast's collision mustnot propagate to an unrelated contrast.

Use an unambiguous future stop label whose registered semantics are "one or moretarget roles has no executable genuine I3 contrast." Preserve the old terminallabel only as historical text attached to the consumed P0-T result.

5. Draft-v0.6 amendment scope

Produce a compact, versioned draft-v0.6 amendment that:

records the operator decision in section 3;

adds the scoring-context/common-prefix/discriminant-token distinction to thenormative protocol and schemas;

creates a v0.6 rendering/scoring registry while preserving the v0.5 registrybyte-for-byte as history;

keeps the visible rendering registry unchanged except for the new normativescoring-boundary fields;

records both registered_prompt_token_count andscoring_context_token_count for S2/S3;

declares the teacher-forced common-prefix token neither a generation nor aseparate sequence-level model evaluation;

keeps S1, S4, RT/RL/RI, K5/K6 applicability, K6-SEP structural absence forS2/S3, and J_joint_correct unchanged;

re-derives every affected operation and token-accounting field from code;

verifies whether the 31,065 sequence-level development projection, m_max =
43, 413/214/448 sample sizes, and registered pass counts remain unchanged;and

changes no statistical value unless the new scoring boundary mathematicallyrequires it. Any change must be derived, explained, and separately surfaced;it may not be silently absorbed.

The amendment may state that the surface and classifier defects arePROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW. It may not declaredraft-v0.6 reviewed, frozen, selected, or formally executable.

6. P0-R1 registration

Register one repaired feasibility continuation under a new, versioned path suchas studies/study3/pilot/p0_r1/. The consumedstudies/study3/pilot/p0/ namespace and all of its result bytes remainimmutable.

P0-R1 must reuse the exact frozen 35-cell/70-member P0 corpus and its hashes. Norow, member, tuple, prompt, rendering, answer, nuisance state, allocation, orground truth may be added, removed, replaced, or edited. The entire namespaceremains pilot-only and permanently excluded from every formal bank.

The registered package must contain:

a concise state machine and counter ontology;

a replay-only tokenizer/factorization verifier that reads the immutable P0-Tresult and performs zero tokenizer encodes;

the versioned eligibility classifier from section 4;

a model runner implementing section 3 without importing or mutating thehistorical buggy classifier;

schemas, validators, negative mutations, and deterministic summarization;

an Azure container definition with exact dependency and base-image pinning;

a pre-execution receipt that binds the authority, draft-v0.6 candidate,corpus, P0-T source artifacts, model/tokenizer revisions, container digest,code blobs, counters, and caps; and

a cross-session handoff that explicitly permits continuation from thepublished P0-R1 registration commit rather than requiring a return to thebaseline of section 1.

No tokenizer, checkpoint, GPU, model, provider, seed, bank, confirmation, RP,or evidence operation may occur in the calibration/registration session.

7. P0-R1 execution envelope for the successor session

After registration is published and only in a new session, the same committedauthority may be continued from the exact published P0-R1 registration commit.The successor must first run the replay-only factorization gate. It performs nonew encode and must verify, from immutable source artifacts, all five conditionsin section 3.2 and the corrected eligibility matrix.

If replay fails, publish a registered stop and perform no model operation. Donot repair and rerun.

If replay passes, run the repaired model pilot in one Azure containerized GPUjob, one checkpoint at a time, fp16, evaluation mode, no sampling, no gradients,no adapters, no quantization, no hosted inference, and no local workstationmodel execution. Use the exact RT/RL/RI model and tokenizer repository identitiesand immutable revisions recorded by P0-T.

Retain the original P0-M allocation and maxima unless code-derived accountingshows a strictly smaller maximum:

60 non-generative prefill evaluations in the K2 smoke;

automatic extension to at most 180 non-generative prefills after a mechanicalsmoke pass;

12 S4 diagnostic generations with at most 4 new tokens each;

at most 228 total sequence-level model-evaluation equivalents;

162 S1, 18 S2, 18 S3 CPU-reuse, and 12 S4 scored rows, 210 total; and

zero provider calls, seeds, bank rows, positive-reference operations,activations, lenses, probes, patches, interventions, or ablations.

The extra S2/S3 common-prefix token changes token processing, not the number ofsequence-level prefill evaluations. Count and report it explicitly. Maintain:

the immutable historical P0-T counter snapshot;

P0-R1 attempt counters; and

an aggregate view where additive counters are summed and identity counts areset cardinalities, not load-event counts.

Add an explicit tokenizer_construction_events counter so reloading the samethree pinned identities is not hidden and is not confused with the cardinalityof distinct tokenizer identities.

Correctness, accuracy, diversity, and discordance are descriptive only and arenot smoke-pass criteria. Preserve every valid row, raw S4 completion, exception,partial result, and counter. No output-conditioned retry or row replacement isauthorized. One infrastructure retry is allowed only when a signed receiptproves zero new tokenizer, model-load, prefill, decode, scoring, and generationoperations.

P0-R1 data remain methods-feasibility observations. They do not enterpaper/evidence_ledger.csv, choose an interface, estimate a confirmatory effect,set a threshold or sample size, or answer the research question.

8. Required negative tests

At minimum, commit non-vacuous mutations that fail for each of the following:

one S2/S3 candidate lacks the common prefix;

one candidate has a different prefix;

one candidate has a third token;

two discriminant token IDs collide;

the prefix does not decode to exactly one U+0020;

a digit token maps to the wrong complete candidate surface;

scoring reads logits before rather than after the common prefix;

S3 performs an additional model evaluation;

the registered tie-break order changes;

an S2 failure propagates to S1;

an S1 failure propagates to S2/S3;

one role's failure propagates to another;

an ineligible row has no reason;

S4 satisfies target-role executability;

a not_applicable row is instantiated or counted;

the historical result, receipt, disposition, or P0 counter is edited;

the full-sequence ranking equivalence assertion is weakened or removed;

the frozen corpus or any member hash changes;

a cumulative counter is reset or a construction event is omitted; and

a formal evidence, seed, bank, OD2, UR-22, RP, selection, or confirmationflag becomes non-null or true.

Each mutation must be shown to alter live input and to be rejected by theproduction validator. A test that perturbs only a test-local copy no productioncode reads is vacuous and does not count.

9. Authorized paths and protected history

Writes are limited to:

the committed copy of this authority;

the active Study 3 draft protocol JSON/Markdown/schema;

a new v0.6 rendering/scoring registry and schema;

new v0.6 operator-calibration record, design receipt, derived tables, andfinal-focused-review packet;

new studies/study3/pilot/p0_r1/ artifacts and tests;

directly affected Study 3 analysis code and tests needed to derive the v0.6fields;

README.md, Study 3 README/charter/handoff, current status, decision log, runlog, methods ledger, and artifact index.

Do not edit:

any Study 1 or Study 2 path;

any byte under studies/study3/pilot/p0/;

tests/test_study3_p0_feasibility_pilot.py;

the v0.5 rendering registry, v0.5 amendment record, v0.5 design receipt, orthird-review artifacts;

any prior authority or prior raw/result/receipt artifact;

any RP, OD2, UR-22, P3-Q, bank, seed, confirmation, or positive-referenceobject; or

paper/evidence_ledger.csv.

No deletion, rename, copy, symlink, submodule, binary artifact, merge commit,rebase, force push, workflow, or branch-label authority is permitted. If anecessary path falls outside this list, stop and request supplemental authoritybefore touching it.

10. Validation and publication

All authoritative validation is CPU-only in the registered Azure containerroute on clean exact-commit checkouts. Calibration validation must showGPU_COUNT=0, CUDA_AVAILABLE=False, zero tokenizer encodes, and zero modeloperations.

Before publication:

reproduce the draft-v0.6 normative documents and derived tables from code;

replay the immutable P0-T evidence through the new classifier and scoringfactorization without calling a tokenizer;

verify all section 8 mutations are live and rejected;

retain the published targeted baselines: 240 design tests, 36 v0.5 renderingtests, 88 v0.4-review tests, and 122 historical P0 tests;

run every new v0.6/P0-R1 test and record its exact node-ID set;

run the full repository suite and reconcile exactly:4,263 historical passes + net-new calibration passes = final passes;

retain 15 skips and only the same two registered historicaltest_parser_v3_seal_job failures with unchanged node IDs/signatures;

verify every protected byte, P0 artifact hash, corpus hash, counter, and theEV-0016 ledger ending; and

verify all authority flags remain false except the narrow, not-yet-consumedp0_r1_pilot_execution_authorized flag recorded in the P0-R1 package.

Publish only by non-force fast-forward with:

git push origin HEAD:refs/heads/main

Fetch again and require HEAD == origin/main, the recorded tree, a cleanworktree, and a strict descendant of the baseline. Stop if remote main moves;do not merge or rebase around it.

The drafting session must stop after entering:

STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE

It must not perform the replay gate, construct a tokenizer, download acheckpoint, allocate a GPU, or begin the model pilot.

11. State after P0-R1 and the remaining review boundary

After P0-R1 reaches a terminal disposition, stop. Preserve:

frozen = false;

formal_execution_authorized = false;

no selected interface or positive reference;

unresolved OD2, UR-22, and RP wrappers;

no formal seed, bank, development result, confirmation access, winner, orevidence row; and

the original research question as unanswered.

If P0-R1 is mechanically feasible, the sole next design action is one fresh,focused final methods review of draft-v0.6. That review is limited to thefirst-discriminative-token factorization, classifier repair, affected accounting,and consistency of the resulting candidate. It is not another general reviewof every historical artifact and must not reopen unrelated resolved findingswithout a concrete contradiction in live v0.6 bytes.

If that focused review accepts v0.6 and P0-R1 disclosed no design-changingmechanical defect, no further general methods-review cycle is required beforean operator freeze decision. If P0-R1 fails mechanically, the successor mustchoose a narrowly demonstrated repair or stop this Study 3 route; it may notsilently widen the pilot.

12. Required handoff

The calibration/registration handoff must report:

exact starting, authority, candidate, registration, and published commits andtrees;

authority bytes, SHA-256, LF/CR and trailing-newline status;

authority-before-drafting and corpus-before-operation proofs;

complete changed-path census and protected-byte audit;

the exact draft-v0.6 scoring rule and equivalence proof;

the corrected eligibility matrix derived from immutable P0-T bytes;

all derived statistical, operation, token, and counter changes or proofs ofno change;

every test/run ID, exact node-ID reconciliation, and failed run;

the new image digest and pinned environment;

confirmation that every tokenizer/model/GPU/formal counter remained zero inthe drafting session and historical P0-T counters were untouched; and

the exact cross-session command and boundary for P0-R1 execution.

Do not begin the final focused review, an OD2 decision, a freeze, a bank, a seed,formal model execution, or any confirmation operation in the calibrationsession.