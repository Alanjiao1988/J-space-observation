Study 3 P0-R1 pre-replay execution-completion supplemental authority — revision 2

This revision supersedes the unused external supplemental draft with SHA-2567609bca3a30d53ee6f9c8272c8c30370ac9ec4a347549d0ef3d5ab303621e26a.The operator reports that the superseded draft was not executed or committed.

1. Sole authority, baseline, and purpose

This file is the sole operator authority for one fresh-session, model-freeexecution-completion round in Alanjiao1988/J-space-observation.

The required starting origin/main is exactly:

167d3067d7d9a2866999a51ec49c3c57c1d31546

The required starting tree is exactly:

f7166f0441780bf0d034eb88a03c0d61e9049a2a

Before any write, fetch origin/main, require HEAD == origin/main, require thecomplete commit and tree above, and require a clean worktree. If any fact differs,stop without changing the repository.

Commit a byte-identical copy of this authority as the first new repository objectand publish that authority commit by non-force fast-forward before creating orediting any other object in this round. Use the supplied file bytes directly. Donot execute from rendered, retyped, reformatted, summarized, or copy-pasted text.

This round has one purpose: complete the already-registered P0-R1 replay and modelexecution machinery so that a later fresh session can actually run the immutablereplay gate and, only if it passes, the bounded GPU feasibility pilot. It repairsimplementation and provenance defects demonstrated in the published registration.

This round is not a methods review, not a new protocol amendment, not P0-R1execution, and not formal Study 3 execution. It authorizes zero replay-gateevaluations, zero tokenizer constructions or encodes, zero checkpoint downloads,zero model loads, zero GPU allocations or jobs, zero forward passes, zerogenerations, zero scored rows, zero seeds, zero bank operations, zero providercalls, and zero evidence-ledger rows.

The committed 19,632-byte P0-R1 authority remains the controlling scientific andoperational boundary except where this supplement expressly corrects thepre-replay implementation and sequencing defects below. No scoring rule, corpus,allocation, cap, model identity, tokenizer identity, rendering, parser, statistic,claim boundary, or terminal-state meaning is changed.

The round must stop after publishingSTUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE. It must not run the replaygate or model pilot.

2. Findings accepted as the reason for this supplement

Treat the following as verified defects in the published registration, not asquestions for another broad review.

Accept the independently reproduced cmfj result at the required baseline(4,340 passed, 15 skipped, with only the two registered historical failures),the protected-byte audit, and the zero-operation counters as valid evidence thatthe calibration and registration round was internally consistent. Those factsdo not establish execution readiness: the live gate transition, result/receiptwriter, model executor, and GPU launch path were outside what that registrationrun actually exercised.

2.1 The registered replay gate has no executable gate path

At the required baseline:

p0_r1_replay_gate.py --gate unconditionally prints a refusal and returns 3;

p0_r1_replay.sh imports and calls derive() rather than the registered gate;

the shell prints a summary but creates no replay result, receipt, disposition,state transition, or attempt-counter record;

the image makes /workspace/studies read-only, while no live gate path isregistered to write complete result bytes to the writable runtime resultdirectory; and

p0_r1_acr_task.yaml therefore cannot produce the registered pass or stopdisposition required by authority section 7.

2.2 The registered model pilot has no executable model path

At the required baseline:

p0_r1_model_runner.run() always raises ExecutionRefused with the explicitstatement that the model pilot is not implemented;

no P0-R1 model-pilot container entry point exists;

no P0-R1 Azure Container Apps GPU job launcher or immutable job definitionexists; and

the only P0-R1 task manifest runs the replay derivation and cannot run the GPUpilot.

Consequently, a replay pass could not legally or physically advance to the modelpilot. Running the current handoff command would call a derivation helper ratherthan the registered live gate; treating its successful exit as a replay-gate passwould therefore be invalid. Starting any actual one-shot replay measurement beforethe complete successor path is frozen is forbidden in this round.

2.3 Image sequencing is incomplete

The published pre-execution receipt has image_digest = null, while the handoff'sclaimed first command requires an immutable image digest. Building and resolvingthe image must therefore precede the replay measurement. This supplement classifiesthe image build and publication of an execution lock as pre-measurement preparation,provided they perform no replay-gate evaluation, tokenizer operation, checkpointdownload, model load, or GPU operation.

2.4 Two provenance statements require scoped clarification

The source artifact delivered before the registration session was 20,217 bytes,SHA-256db42214e37e9b44feab5c36c8ca4359b0d269cba3b9f0444c60b8837bc59975f,430 LF, zero CR, with a trailing newline. The committed authority is 19,632 bytes,SHA-256f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2,zero CR, without a trailing newline. They are not byte-identical end to end.

The independent report establishes a narrower and compatible fact: the19,632-byte file received and staged by the registration executor was committedbyte-identically. Record the provenance as two separate hops:

source delivery to executor-received attachment: bytes changed from the20,217-byte identity to the 19,632-byte identity; and

executor-received attachment to repository commit: byte-identical, with nofurther normalization.

Do not accuse the registration executor of rewriting the file, and do not claimthat the end-to-end source-delivery chain was byte-identical. The committed19,632-byte file is the operative repository authority. Preserve both identitiesas provenance and do not edit any historical object. This clarification is not ascientific or scoring change and does not by itself block execution readiness.

The actual comparison from dfbe6dd6c82fbe0e8906a4aa7f4df6b676496366 to167d3067d7d9a2866999a51ec49c3c57c1d31546 contains exactly 40 changed paths:9 modified and 31 added. This is the repository-object count returned by theexact baseline-to-head comparison; a staged durable copy outside the committedtree is not an additional changed repository path. Any 41 paths prose statementis a one-count registration erratum. Correct active governance surfaces to 40while preserving the historical commit and failed-run record.

2.5 The next-action ordering is overstated

NEXT_THREAD_HANDOFF.md currently presents the final focused methods review andP0-R1 execution as two interchangeable immediate successors. The controllingauthority requires the final focused review only after P0-R1 reaches a terminalmechanically feasible disposition. Correct the active handoff ordering to:

execution-completion publication;

fresh-session replay gate;

if replay passes, the single bounded GPU pilot in that execution session;

only after a mechanically feasible terminal P0-R1 disposition, one fresh,focused final methods review.

This correction does not waive the final focused review and does not begin it.

3. Immutable scientific boundary

Preserve byte-for-byte:

every path under studies/study3/pilot/p0/;

tests/test_study3_p0_feasibility_pilot.py;

the frozen 35-cell, 70-member P0 corpus and every member hash;

the immutable P0-T result, receipt, disposition, and 4,956-encode snapshot;

the draft-v0.6 rendering/scoring registry and its schema;

the draft-v0.5 protocol JSON, Markdown, and schema bound by the P0 manifest;

every v0.5 artifact, third-review artifact, prior authority, and prior rawresult;

every Study 1 and Study 2 path;

every RP, OD2, UR-22, P3-Q, seed, bank, confirmation, positive-reference, andselection object; and

paper/evidence_ledger.csv, which must remain byte-identical through EV-0016.

The following remain exactly as registered:

S2/S3 complete visible candidates are " 0" through " 9";

token 220 is the verified common U+0020 prefix and tokens 15 through 24 arethe ten discriminants, derived from immutable P0-T evidence rather than newlyencoded;

S2 appends the verified common-prefix token to the registered prompt-tokensequence and reads one next-token vector at the discriminant position;

S3 reuses that exact S2 vector on CPU with zero model evaluations;

S1 and S4 are unchanged;

the digit-order tie break is unchanged;

smoke is exactly 60 non-generative prefills and 66 scored rows;

the complete caps remain at most 180 non-generative prefills, 12 S4 generationcalls with at most 4 new tokens each, 228 sequence-level model-evaluationequivalents, and 210 scored rows comprising 162 S1, 18 S2, 18 S3 CPU reuse,and 12 S4;

exactly three pinned role identities and immutable revisions are used;

fp16, evaluation mode, no sampling, no gradients, no adapters, noquantization, no hosted inference, no local workstation model execution, andno hidden-state or intervention operation; and

all P0-R1 outputs remain methods-feasibility observations permanently excludedfrom formal banks, selection, thresholds, sample-size setting, confirmation,and the evidence ledger.

4. Authorized paths

Writes are limited to:

a new committed copy of this supplemental authority;

files under studies/study3/pilot/p0_r1/, including versioned execution-lock,replay, model-runner, schemas, container entry points, launch definitions,receipts, and handoff artifacts;

new or additive P0-R1 execution-readiness tests under tests/;

the existing P0-R1 registration tests only when adding assertions withoutremoving, weakening, renaming, skipping, or changing the meaning of anypublished node;

a P0-R1-specific Azure launcher underinfra/azure/scripts/ only if reusing the existing Azure Container Appsgpu-t4 route cannot be expressed safely inside the P0-R1 container namespace;

README.md, studies/study3/README.md,studies/study3/RESEARCH_CHARTER_DRAFT.md,studies/study3/NEXT_THREAD_HANDOFF.md, reports/current_status.md,docs/decision_log.md, docs/run_log.md, paper/methods_ledger.md, andpaper/artifact_index.csv for the narrow state, provenance, and path-countcorrections in this authority.

No deletion, rename, copy, symlink, submodule, binary artifact, workflow, merge,rebase, force push, or branch-label operation is authorized. If a necessary pathfalls outside this list, stop and request supplemental authority before touchingit.

5. Required replay implementation

Implement a real successor-session gate without executing it in this round.

The production replay entry point must:

require the exact published execution lock, code commit/tree, immutable imagedigest, operative authority identity, frozen corpus hashes, and P0-T sourcehashes;

read the immutable P0-T artifacts and perform zero tokenizer constructions,zero encodes, zero checkpoint or model operations, and zero GPU operations;

verify all five factorization conditions, the 39-cell corrected eligibilitymatrix, zero empty-reason ineligible rows, 39 eligible cells, and 11 executablegenuine I3 contrasts per role;

increment replay_gate_evaluations exactly once in the P0-R1 attempt view andleave every tokenizer/model/GPU/scoring counter at zero;

write canonical result, receipt, counters, and disposition bytes to a writableruntime result directory before returning;

on pass, emit onlySTUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT;

on a factorization or corrected-matrix failure, preserve the partial evidence,emit the applicable registered stop, and authorize no model operation; and

never repair, substitute, regenerate, or rerun an observed replay result.

p0_r1_replay_gate.py --gate must no longer be an unconditional refusal. It mustrequire explicit successor-mode authorization and an output directory. Calibrationand build-time modes must remain unable to call the live gate accidentally.

p0_r1_replay.sh must call the live --gate entry point, not derive(), and mustpass the writable runtime result directory. It must assert no GPU is visible andmust preserve a non-zero gate exit only after result and receipt bytes have beenwritten.

The ACR replay task must consume an immutable image digest and the publishedexecution lock. It must not contain, download, or launch any model. Resulttransport must be content-addressed and recoverable without rerunning the gate;the published SHA-256 and byte counts must match the in-container files exactly.

6. Required model-pilot implementation

Implement the complete P0-R1 model executor and its Azure Container Apps GPU jobentry point without launching them in this round.

The executor must refuse unless it receives a valid, unconsumed execution lockand a byte-valid replay-pass receipt from the same authorized attempt. A prose logline is not sufficient authorization.

The implementation must:

reuse the frozen P0 corpus and the existing read-only renderer/parser inputs;

construct exactly the three pinned tokenizers and load exactly the three pinnedcheckpoints, with actual construction/load events and distinct identitiescounted separately;

encode only runtime prompts/wrappers authorized for P0-R1 and count everysequence; never repeat the consumed P0-T census;

for S2, concatenate the verified common-prefix token ID to the encoded promptIDs without re-encoding the concatenated text, run one ordinary prefill, andread only the ten discriminant logits at the next position;

for S3, reuse the exact captured S2 vector and add zero model evaluations;

preserve the registered S1 restricted-logit rule and the S4 greedy parserdiagnostic with max_new_tokens = 4;

retain every valid row, raw S4 completion, exception, partial result, andcumulative counter; and

generate canonical raw result, receipt, counter, resource, and dispositionartifacts in the writable runtime result namespace.

The 60-prefill mechanical smoke must complete and pass before any extension-onlyprefill or S4 generation occurs. Correctness, accuracy, diversity, and discordancemust not be smoke criteria. The code must enforce the smoke/extension boundary,not merely inspect smoke rows after the full run.

The implementation must also reconcile the one-job, three-load, andsmoke-before-extension constraints. At most one checkpoint may reside on the GPUat a time. If the implementation retains already-loaded fp16 checkpoints in CPUmemory so that all three role-smoke slices can complete before extension without asecond model load, record and test that schedule explicitly. It may not reload acheckpoint after observing smoke, exceed three model-weight loads, or perform asecond model-operating GPU job.

One additional infrastructure attempt remains permitted only when a signed Azurereceipt proves zero tokenizer constructions/encodes, checkpoint downloads, modelloads, GPU model operations, prefills, decodes, generations, and scored rows inthe failed attempt. No output-conditioned retry or row replacement is authorized.

The Azure launcher must use the repository's existing managed-identity ACR pulland Azure Container Apps T4 workload-profile route, bind the image by digest, bindthe execution lock and replay-pass receipt, set replica retry to zero, and startat most one model-operating execution. Merely creating or updating the dormant jobdefinition in a later execution session is not a model operation; this round mayonly commit and validate the launcher, not create, update, start, or allocate thejob.

7. Image build and execution-lock sequence

Use this exact order, with zero measurement operations:

Complete the replay and model implementations and their tests.

Commit the final executable bytes as an EXECUTABLE_CODE_COMMIT; publish it bynon-force fast-forward.

Build the P0-R1 image from exactly that commit in ACR. The build may run onlystatic validation and already-authorized --check derivations. It must not runthe live replay gate, construct a tokenizer, download a model, load weights, orrequest a GPU.

Resolve and read back the immutable image manifest digest. Verify that the imagecontains the exact executable code blobs and operative committed authority.

Create a versioned p0_r1_execution_lock.json and schema that bind at least:the original registration commit, this supplemental-authority commit, theexecutable code commit/tree, the final ready commit/tree relationship, imagedigest, base-image digest, code-blob hashes, dependency lock, corpus and P0-Thashes, role revisions, caps, zero counters, and the permitted replay then GPUstate transition.

Commit and publish the execution lock and corrected handoff as the finalP0_R1_READY_COMMIT. No executable byte may change after the image build. Ifone changes, discard the unexecuted image, rebuild from the new code commit,and create a new lock before any measurement. This is pre-observation builditeration, not a replay or model retry.

Re-fetch and require HEAD == origin/main, a clean worktree, and a strictfirst-parent fast-forward lineage from the required baseline.

Enter STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE and stop.

The live replay command in the next session must bind both the ready commit andthe executable code/image commit recorded in the lock. Do not pretend that adigest can be embedded in the same image whose digest it defines.

8. Required tests and validation

Add non-vacuous production-bound tests that fail at the required baseline andpass only after the execution gaps are closed. At minimum prove that:

--gate reaches live gate logic only with successor authorization and no longerunconditionally returns 3;

calibration/build modes still cannot consume the live gate;

the replay shell invokes --gate, not derive();

pass and failure fixtures both write complete result/receipt/disposition bytesbefore exit;

replay outputs go to the writable runtime result directory;

replay imports neither transformers nor tokenizers and leaves every modelcounter at zero;

the replay pass cannot authorize the model runner unless the receipt, lock,image digest, commit, tree, hashes, and attempt ID agree;

the model runner is not an unconditional refusal or a synthetic-logit-onlyshell;

the S2 scoring context appends the prefix ID by tensor/ID concatenation andreads the discriminant-position vector;

S3 uses the same captured vector and performs zero model operations;

the global 60-prefill smoke boundary is enforced before extension or S4;

the three-load, one-GPU-at-a-time, one-model-operating-job caps are enforced;

every terminal or partial path preserves counters and artifacts;

the launcher cannot start twice and has platform retry disabled;

an infrastructure retry is rejected unless all registered operation countersin the first attempt are zero;

the image/ready-lock two-commit relationship is internally consistent;

the immutable P0 namespace, v0.6 science registry, and evidence ledger cannotchange; and

the provenance record reports 40 committed repository paths and distinguishesthe source-delivery-to-received-file hop from the byte-identicalreceived-file-to-commit hop, without rewriting historical bytes.

Synthetic tokenizers, models, and logits may be used for CPU-only tests, but eachmutation must alter live production input or code. No test may invoke a realtokenizer, download a checkpoint, expose a GPU, or run the live replay gate.

Run all authoritative validation in clean exact-commit CPU-only ACR clones.Require GPU_COUNT=0, CUDA_AVAILABLE=False, zero tokenizer encodes, zerocheckpoint/model operations, and zero P0-R1 attempt counters. Retain all publishedtargeted node IDs and pass counts: 240 design, 36 v0.5 rendering, 88 v0.4 review,122 historical P0, 46 P0-R1 registration, and 31 v0.6 registry. Do not weaken,rename, skip, or delete any existing test.

Run the full suite. The required baseline is 4,340 passed, 15 skipped, and onlythe same two registered historical test_parser_v3_seal_job failures. Reconcilethe final pass total as 4,340 plus the exact net-new node IDs. Any new failure,changed historical failure signature, unexplained skip, local-only validation, orunreconciled total is a stop.

Treat ACR run cmfj as an independent confirmation of the 4,340-pass startingbaseline only. It does not test or waive the net-new execution-readiness work.

9. Publication and state rules

Publish only by non-force fast-forward to refs/heads/main. Do not merge, rebase,force push, or work around a moved remote. Every failed build or validation runmust remain in the run log with its operation counters; a failed pre-observationbuild may be corrected, but it must never be relabelled as a replay or modelattempt.

At close, require:

the operative P0-R1 authority and all prior artifacts unchanged;

the two-hop authority provenance clarification and 40-path correction visiblein active governance;

a real immutable image digest and execution lock;

a real replay result/receipt path and a real GPU model-runner/launcher path;

every P0-R1 execution counter still zero;

the immutable P0-T counters unchanged;

p0_r1_pilot_execution_authorized = true and not consumed;

frozen = false and formal_execution_authorized = false;

no selected interface or positive reference;

OD2, UR-22, and RP unresolved;

no seed, bank, development, confirmation, winner, or evidence row; and

the research question unanswered.

The only legal successor is one fresh P0-R1 execution session starting from thepublished ready commit. It must run the replay gate first. If replay fails, itpublishes the registered stop and performs no model operation. If replay passes,the same execution session may launch the one bounded GPU pilot and must thenpublish a terminal P0-R1 disposition. It must not begin the final focused review.

Only after a mechanically feasible terminal P0-R1 disposition may a separatefresh session perform the one focused final methods review of draft-v0.6. Nofurther broad review loop is authorized by this supplement.

10. Required handoff

Report all of the following:

exact starting, supplemental-authority, executable-code, image-build, execution-lock, final-ready commits and trees;

supplemental-authority bytes, SHA-256, LF/CR, BOM, and trailing-newline status;

exact changed-path census and protected-byte audit;

the two provenance clarifications and their corrected active surfaces;

the concrete replay defects and model-runner defects closed, with entry points;

proof that the live gate and model pilot were not executed;

image repository, immutable digest, base digest, dependency versions, codecommit/tree, and execution-lock hash;

every ACR validation/build run ID, failed run, exact node-ID count, full-suitereconciliation, and the two unchanged historical failure signatures;

all P0-R1 counters at zero and immutable P0-T counters unchanged;

the final stateSTUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE; and

the exact next-session replay command, pass/fail boundary, and single GPU-jobcommand without running either command in this round.

Do not begin replay, tokenizer access, model access, GPU execution, the finalfocused review, OD2/UR-22/RP work, a freeze, a bank, a seed, formal development,or confirmation in this session.