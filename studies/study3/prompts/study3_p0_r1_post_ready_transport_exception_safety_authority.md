Study 3 P0-R1 post-ready transport and exception-safety completion authority

1. Sole authority, required baseline, and stop boundary

This file is the sole operator authority for one fresh-session, model-free repairround in Alanjiao1988/J-space-observation.

The required starting origin/main is exactly:

71f4ab903295d1320881b654bda2d49cf1808794

The required starting tree is exactly:

65f87e310a883495af5c3d926fceaa192411a27d

Before any write, fetch origin/main; require HEAD == origin/main; require thecomplete commit and tree above; require a clean worktree; and verify that no P0-R1replay result directory, replay-gate execution, P0-R1 GPU-job execution, tokenizeroperation, checkpoint access, or model operation has appeared since that commit.If any fact differs, stop without changing the repository.

Commit a byte-identical copy of this authority as the first new repository objectand publish that authority commit by non-force fast-forward before creating orediting any other object in this round. Use the uploaded file bytes directly. Donot execute from rendered, retyped, reformatted, summarized, or copy-pasted text.

This round repairs runtime binding, complete-byte result transport, replay-receiptinjection, durable partial-result preservation, and production-bound validation.It does not run the replay gate or the model pilot. It authorizes zero livereplay-gate evaluations, zero tokenizer constructions or encodes, zero checkpointdownloads, zero model loads, zero GPU allocations or executions, zero forwardpasses, zero generations, zero scored rows, zero seeds, zero bank operations,zero provider calls, and zero evidence-ledger rows.

The round must publish a new active generation of the execution image, lock, andhandoff, then stop in:

STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE

The state label is intentionally unchanged, but the active handoff must identifythis as ready generation 2 and mark the unconsumed generation-1 lock and image assuperseded and inert. Superseding generation 1 does not consume, re-arm, duplicate,or add an execution envelope. Exactly one P0-R1 replay attempt and, only after apass, one bounded model-operating GPU job remain authorized overall.

Do not run the live replay gate, construct or encode with a tokenizer, download orload a checkpoint, allocate or start a GPU job, perform a model operation, beginthe final focused methods review, or touch OD2, UR-22, RP, a seed, a bank, formaldevelopment, confirmation, selection, or the evidence ledger in this round.

2. Accepted history and controlling scientific boundary

Accept the following published facts as historical records; verify them but donot reopen or rewrite them:

registration commit 167d3067d7d9a2866999a51ec49c3c57c1d31546;

operative P0-R1 authority: 19,632 bytes, SHA-256f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2;

revision-2 execution-completion authority: 23,486 bytes, SHA-256ffe75ba42c023e959f3beb23927604c3ae72c07fb4b25be346f504c8ea2930de;

generation-1 executable-code commitaad14c45e9681a34f382aa95c55ac875d2ca98ce and image digestsha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176;

published ready checkpoint 71f4ab903295d1320881b654bda2d49cf1808794;

the 29-path census, 119-object protected-byte audit, disclosed amend/resetnear-miss, and clean append-only published lineage;

clean exact-commit ACR validation cmg6: 4,387 passed, 15 skipped, with onlythe two registered historical test_parser_v3_seal_job failures;

immutable P0-T counters remain 4,956 encodes and three tokenizer identities;every P0-R1 replay/model counter remains zero; and

paper/evidence_ledger.csv remains byte-identical through EV-0016, with noEV-0017.

The generation-1 image and lock are valid evidence of a model-free implementationround, but they are not sufficient to consume the one-shot envelope. Preservetheir bytes, digest, tests, and handoff record as history. Do not delete, edit,retag, or relabel them as an executed attempt.

The two earlier authorities remain the controlling scientific and operationalboundary except where this authority narrows execution further to close thedemonstrated transport and runtime defects below. No scoring rule, corpus,allocation, cap, model or tokenizer identity, rendering, parser, statistic,claim boundary, role meaning, smoke criterion, or terminal-state meaning changes.

Preserve exactly:

the frozen 35-cell, 70-member P0 corpus and all member hashes;

every byte under studies/study3/pilot/p0/ andtests/test_study3_p0_feasibility_pilot.py;

every immutable P0-T result, receipt, disposition, and counter snapshot;

the draft-v0.6 rendering/scoring registry and its schema;

the P0-manifest-bound draft-v0.5 protocol JSON, Markdown, and schema;

every Study 1, Study 2, review, prior authority, prior raw-result, OD2, UR-22,RP, P3-Q, seed, bank, confirmation, selection, and positive-reference object;and

paper/evidence_ledger.csv byte-for-byte through EV-0016.

The registered P0-R1 scientific limits remain: three pinned role identities;fp16; evaluation mode; no sampling, gradients, adapters, quantization, hostedinference, local workstation model execution, hidden-state operation, orintervention; exactly 60 smoke prefills before any extension; at most 180non-generative prefills, 12 S4 generation calls, 228 model-evaluationequivalents, and 210 scored rows; S2 first-discriminative-token scoring; S3 CPUreuse of the same vector; S1 and S4 unchanged. Every output remains pilot-onlymethods-feasibility material and cannot enter a formal bank, threshold, selection,sample-size decision, confirmation, or evidence-ledger row.

3. Demonstrated generation-1 execution defects

Treat these as verified implementation defects, not as invitations to anotherbroad methods review.

3.1 Replay artifacts are not recoverable from the ACR run

The live gate writes four canonical files only inside the ACR task's ephemeral/workspace/runtime/results. p0_r1_replay.sh prints each file's SHA-256 andbyte count, but it does not print, export, upload, or otherwise return the filebytes. p0_r1_acr_task.yaml has no output volume, result artifact, Blob export,or complete-byte log envelope. A digest and a byte count cannot reconstruct thepreimage. Therefore revision-2 section 5's requirement that result transport becontent-addressed and recoverable without rerunning the one-shot gate is unmet.

3.2 The GPU container cannot receive the replay-pass receipt

p0_r1_launch_gpu_pilot.sh accepts only an image digest and a commit. It neitheraccepts nor validates the recovered replay receipt or execution lock and passesneither object into the job. A Container Apps job starts with a fresh filesystem.p0_r1_model_pilot.sh requires/workspace/runtime/results/p0_r1_replay_receipt.json, but no step creates thatfile. A prose pass line or SHA-256 printed by ACR is not a byte-valid receipt.

3.3 The GPU container has neither the addressed entry point nor the final lock

The job command is /workspace/p0_r1_model_pilot.sh, while the image copies thatfile only under/workspace/studies/study3/pilot/p0_r1/container/p0_r1_model_pilot.sh.The script defaults SRC=/workspace/src, but the standalone image contains therepository subset under /workspace/studies; /workspace/src exists only whenthe ACR checkout step mounts it. The GPU job has no such checkout or mount.

The generation-1 image was built from aad14c45...; the final execution lock wasadded later and is absent from that image. The model entry point neverthelesscalls LOCK.load_lock(root=src) and no launcher injects the later lock. Thus thestandalone GPU job cannot reach authorization validation even if a receipt wereavailable.

3.4 Model artifacts are ephemeral and only their hashes are printed

The model pilot writes its canonical artifacts only under the GPU container'sephemeral runtime directory. The entry point prints hashes and byte counts butdoes not export the bytes. The job definition has no Azure Files mount, privateBlob export, or complete-byte log envelope. A terminal P0-R1 disposition couldtherefore not be published from the actual emitted bytes.

3.5 Exception and partial-result preservation is not production-bound

execution/p0_r1_model_execution.py calls the canonical artifact writer onlyafter all tokenizer constructions, model loads, smoke, extension, and S4 workcomplete. A tokenizer failure, checkpoint failure, CUDA/OOM error, scoringexception, upload failure, or process interruption can exit before a result,receipt, disposition, or durable counter snapshot exists. Row-level exceptionsare appended in memory and immediately re-raised before the final writer. Thecurrent code therefore does not satisfy revision-2 section 6's requirement toretain every valid row, raw S4 completion, exception, partial result, andcumulative counter.

The launcher also produces no byte-valid zero-operation infrastructure receiptwhen it fails before the model runner. Such a failure cannot justify the solepermitted infrastructure retry.

3.6 Existing tests do not close these gaps

The production-readiness tests check for strings such as a receipt filename,verify_binding, and replicaRetryLimit: 0; they do not execute the standaloneimage layout, transport full bytes across an ACR/ACA boundary, inject a reallock and receipt, recover a Blob/log artifact, or force production-path failuresand inspect the durable partial record. The 4,387-pass suite is accepted as thehistorical baseline, not as evidence that these missing boundaries work.

4. Authorized writes and external preparation

Repository writes are limited to:

a new committed copy of this authority;

new generation-2 files under studies/study3/pilot/p0_r1/, including anexplicit v2 execution lock and schema, transport utilities, wrappers,container entry points, launch definitions, result schemas, receipts, andhandoff artifacts;

modifications to existing P0-R1 implementation files under that directoryonly where required by sections 5 through 9;

new or additive P0-R1 transport/readiness tests under tests/, withoutremoving, weakening, renaming, skipping, or changing any published node;

a P0-R1-specific launcher under infra/azure/scripts/ only if the completeorchestration cannot be kept safely inside the P0-R1 namespace; and

active governance surfaces: README.md, studies/study3/README.md,studies/study3/RESEARCH_CHARTER_DRAFT.md,studies/study3/NEXT_THREAD_HANDOFF.md, reports/current_status.md,docs/decision_log.md, docs/run_log.md, paper/methods_ledger.md, andpaper/artifact_index.csv.

No deletion, rename, symlink, submodule, binary repository artifact, GitHubworkflow, merge, rebase, force push, branch-label operation, or change outsidethis list is authorized. Preserve the generation-1 lock and handoff either attheir current paths with new generation-2 paths, or as byte-identical explicitlyversioned historical objects. Do not silently replace the only copy of an oldlock. If a necessary write falls outside this list, stop and request authority.

This round may perform model-free external preparation only:

CPU-only ACR image builds and exact-commit validation;

read-only Azure control-plane queries for the registry, Container Apps jobhistory, identity, and storage route;

one no-tokenizer, no-model, no-GPU transport canary in the existing ContainerApps environment if required to prove managed-identity Blob write/readback;and

creation of unique canary objects under the registered private transportprefix, with no overwrite and no deletion. Record their hashes and retainthem as transport-preflight artifacts.

Do not change storage public-network access, create or disclose a shared key orSAS, grant a new broad role, create a GPU execution, or access any checkpoint.The existing private transport isstjspacefiles0709085305/jspace-results, reached through the existing privateendpoint by id-jspace-aca-acrpull-sea, whose documented role is Storage BlobData Contributor. If the active configuration does not reproduce those facts,stop; do not repair infrastructure by widening access.

5. Required standalone image and runtime binding

Create one canonical standalone runtime root and use it consistently in theDockerfile, shell entry points, launcher, tests, and handoff. The GPU job must notdepend on the ACR task's /workspace source mount. Either install the entrypoints at stable absolute paths such as /usr/local/bin/ or invoke their exactpaths inside the image. Set SRC to the actual immutable source root in thestandalone image and verify it before any job can be created or started.

The generation-2 image must contain the exact executable code commit and everyimmutable scientific input required at runtime, but it must contain no result,model weight, replay receipt, final execution lock, storage credential, sharedkey, SAS, or secret. The final execution lock necessarily postdates the imagedigest. Treat that as an explicit runtime-injection requirement, not as a reasonto pretend the lock is baked into the image.

The launcher must receive, as separate exact-byte inputs:

the generation-2 immutable image digest;

the generation-2 ready commit;

the active generation-2 execution-lock file; and

the recovered byte-valid replay-pass receipt from the same attempt.

Before creating or starting any GPU job, the launcher must validate locally thatthe lock is active and unconsumed, the receipt passes, the attempt IDs agree, thereceipt and lock bind the same image digest, executable commit/tree, authorityhashes, corpus/P0-T hashes, and ready relationship, and all replay tokenizer,model, and GPU counters are zero. A missing, prose-only, hash-only, malformed,wrong-attempt, wrong-image, wrong-lock, superseded-lock, or failure receipt mustrefuse before az containerapp job create, update, or start.

Pass the exact lock and receipt bytes into the standalone container through alossless, size-checked encoding or an immutable private-Blob object with exactSHA-256 and byte count. The container must reconstruct them in its writableruntime namespace and independently validate every binding before importingtransformers, constructing a tokenizer, accessing a checkpoint, or performinga model operation. Do not bake outcome-conditioned bytes into an image.

The ready-commit argument must be used and validated; it may not remain anignored shell argument. The model container must record the ready commit, lockidentity, replay attempt ID, image digest, Azure job execution name, and outputprefix in every result and receipt.

6. Required replay complete-byte transport

Keep the registered CPU-only ACR replay route. Do not switch the scientific gateto a different environment. Add a deterministic, production-bound complete-bytetransport envelope around the four canonical replay artifacts.

At minimum, the transport must:

carry every byte of the replay result, receipt, counters, and disposition;

use a versioned envelope with attempt ID, artifact name, byte count, fileSHA-256, chunk index/count, chunk SHA-256, and lossless encoded chunk bytes;

keep each log line below the documented platform truncation boundary;

tolerate harmless Azure log prefixes, ordering changes, and duplicateidentical lines, while rejecting a missing chunk, conflicting duplicate,unknown artifact, path traversal, wrong attempt, wrong count, or any hash orbyte mismatch;

emit a complete manifest after all artifact chunks and emit no passauthorization until recovery verifies all four exact files;

be recoverable from the captured ACR run log without invoking --gate again;and

retain the raw ACR run log, run ID, recovered files, transport manifest, andreconstruction receipt for publication.

Implement a production recovery command that takes a captured raw ACR log andwrites the exact canonical files to an operator-owned local result directory.The successor orchestration must capture the full streamed log from the firstbyte, not rely on a digest line or on an implicit last-N-lines default.

Before freezing generation 2, exercise this transport only with deterministicsynthetic fixture artifacts through the same container/task path. The canarymust be at least twice the maximum projected combined replay-artifact size andmust prove byte-exact recovery. It must never call the live gate or import atokenizer/model library. A canary failure is pre-observation build iteration;record it, repair before image lock, and do not call it a replay attempt.

In the later execution session, recover and validate the replay artifacts beforeany GPU job is created. Publish the replay artifacts and pass/stop state bynon-force fast-forward. On a replay failure, stop with no model operation. On areplay pass, the exact recovered receipt, not a regenerated equivalent, is theonly receipt the launcher may consume.

7. Required GPU artifact persistence and readback

Use the existing private Azure Blob route as the primary durable transport forthe GPU pilot. Do not use the container filesystem or console hashes as the solerecord.

The launcher must derive one unique, attempt-bound prefix underjspace-results, bind it into the lock/receipt/job definition, and prove beforestart that no target final-artifact name already exists. The job must useid-jspace-aca-acrpull-sea through Microsoft Entra managed identity; use noshared key, SAS, public endpoint, anonymous access, or embedded credential.

The model job must upload with overwrite = false, download/read back everyuploaded byte through the same authenticated private route, verify SHA-256 andbyte count, and write an immutable artifact manifest last. The final manifestmust enumerate every canonical result, receipt, counters, resource record,disposition, exception/partial record, and journal object required by theattempt. A manifest is valid only after all listed objects read back exactly.

Console output must also carry a bounded complete-byte or manifest envelope as asecondary recovery route, but console hashes alone are not sufficient. Theoperator must retrieve the Blob manifest and every listed object, verify themagainst the in-container hashes, and only then publish the terminal P0-R1artifacts. If direct operator data-plane access is unavailable because thestorage account is private, use a separately named CPU-only, managed-identityrecovery job that downloads the immutable objects and emits the same verifiedcomplete-byte envelope. That recovery job performs no tokenizer, checkpoint,model, or GPU operation and does not constitute a retry.

Before the image is locked, run one model-free transport canary through theactual private endpoint and identity, using deterministic fixture bytes and aunique no-overwrite prefix. Require upload, readback, manifest-last ordering,operator recovery, and byte-exact verification. Do not run the real model entrypoint or allocate the GPU workload profile for this canary.

8. Required durable counters, partial results, and retry evidence

Refactor the production model path so canonical evidence survives every ordinaryfailure path. Authorization validation and durable-attempt initialization mustcomplete before any tokenizer/model import or operation.

Maintain an append-only or immutable-sequence attempt journal in the private Blobprefix. At minimum, durably record and read back:

attempt start and all bound identities;

before/after admission of every tokenizer construction, prompt encode,checkpoint download/load, prefill, generation/decode, parser call, and scoredrow;

every valid row, S2 vector reuse, raw S4 completion, exception, smoke state,resource observation, and cumulative counter snapshot; and

terminal or partial disposition and the final artifact manifest.

Count an irreversible operation at admission, before calling the externaltokenizer/model/GPU operation, so a crash cannot make a possibly-startedoperation appear as zero. Use immutable sequence numbers or conditional ETags;never overwrite an earlier observation. A process restart may inspect and reportthe journal but may not resume, repair, replace, or rerun scientific operations.

Wrap tokenizer construction, checkpoint access, CUDA initialization, modelloading, smoke, extension, S4, serialization, and upload with a top-levelexception boundary that writes the most conservative counter snapshot, allavailable partial rows/completions/exceptions, and a canonical stopped orinfrastructure-failure receipt before exit whenever the process can still write.Do not catch an exception merely to reset a counter or continue with a repairedrow.

The shell entry point must also produce a byte-valid infrastructure receipt whenit fails after the Azure job starts but before the Python runner begins. Thatreceipt must distinguish GPU allocation/job start from tokenizer/model operations;an allocated job is not silently reported as a zero-event non-attempt.

One additional infrastructure attempt remains allowed only after a separateoperator decision and only when the recovered, byte-valid journal/receipt plusAzure execution record demonstrate zero tokenizer constructions, encodes,checkpoint accesses, model loads, forward passes, prefills, decodes, generations,parser calls, and scored rows. No automatic retry, platform retry, output-conditioned retry, row replacement, or re-arming is authorized. If durableevidence is missing or ambiguous, the conservative value is nonzero/unknown andno retry is authorized.

9. Required launcher and successor orchestration

Provide one production successor wrapper and one handoff. The wrapper must makethe legal sequence mechanically difficult to violate:

require a fresh session, exact generation-2 ready commit/tree, clean worktree,active v2 lock, immutable image digest, zero attempt counters, and no priorP0-R1 replay or GPU execution;

build the ACR context from the exact ready commit and capture the full ACRstreamed log while running the live replay gate exactly once;

reconstruct and verify all replay bytes from that log without rerunning;

publish the replay result and registered pass/stop state by non-forcefast-forward;

on failure, stop and perform no model operation;

on pass, validate and inject the exact recovered receipt and active v2 lock,create/start at most one digest-bound Container Apps T4 execution withplatform retry zero, and capture the returned Azure execution name;

monitor that exact execution, recover the private-Blob manifest and allcanonical bytes, preserve every partial or terminal outcome, reconcilecounters, and publish by non-force fast-forward; and

stop after the terminal P0-R1 disposition without beginning the final focusedreview.

The wrapper must not hide an irreversible command behind an ambiguous default.It must have distinct explicit modes for preflight/check, live replay, andconditional model launch. Only the fresh execution session may pass the explicitlive authorization flag. The model launch command must require the recoveredreceipt path and active lock path as mandatory arguments.

The launcher must query the exact job name's existing execution history beforecreate/update/start and refuse if any model-operating execution already exists.Set replicaRetryLimit = 0, parallelism = 1, andreplicaCompletionCount = 1. Do not delete an old execution to make the countappear zero. The launcher must capture and publish every failed Azure CLI commandand its pre-operation counters.

10. Required non-vacuous validation

Add production-bound tests that fail at 71f4ab9... and pass only after thedemonstrated defects are closed. At minimum prove:

the standalone image, with no ACR /workspace/src mount, contains and caninvoke the exact model entry point and immutable source root;

the actual GPU job command path exists inside the built image;

the final lock is deliberately absent from the executable-code commit/imageand is successfully injected and byte-validated at runtime;

missing, wrong, failure, wrong-attempt, wrong-image, wrong-ready-commit,superseded-lock, or hash-only receipt/lock input refuses before any job createor start command;

the ready-commit argument is checked rather than ignored;

synthetic replay result, receipt, counters, and disposition bytes survive theexact chunk/manifest transport and recover byte-for-byte;

missing, truncated, reordered, duplicated-identical, conflicting-duplicate,prefixed, and wrong-attempt log fixtures have the registered accept/refusebehavior;

the private-Blob writer uses managed identity, no overwrite, readback, exacthashes, and manifest-last ordering;

a production launcher fixture injects exact receipt and lock bytes and thecorrect Blob prefix/environment into the job;

forced failures before tokenizer import, during tokenizer construction,checkpoint access, model load, smoke prefill, extension, S4, serialization,and upload retain the conservative counters and all available partial bytes;

a hard-terminated subprocess leaves a durable last-admitted-operation journalthat cannot be interpreted as a zero-operation retry receipt;

the model runner and shell emit a canonical partial/infrastructure receipt onevery recoverable exit path;

the launcher cannot start twice and the platform retry limit remains zero;

the generation-1 lock, image digest, authorities, immutable P0 namespace,v0.6 science registry, and evidence ledger remain unchanged; and

no test or image-build check calls the live gate, imports a real tokenizer,downloads a checkpoint, exposes a GPU, or performs a model operation.

Synthetic tokenizers, models, logits, Azure CLI shims, Blob transports, andforced failures may be used in CPU-only tests, but each mutation must reachproduction code. String-presence-only tests are insufficient for runtime layout,receipt injection, transport, persistence, or exception safety.

Run authoritative validation only in clean exact-commit CPU-only ACR clones.Retain all published targeted nodes and pass counts. The required starting fullsuite is 4,387 passed, 15 skipped, with only the same two registered historicalfailures. Reconcile the final total as 4,387 plus the exact net-new node IDs.Any new failure, changed historical failure signature, unexplained skip,local-only validation, or unreconciled total is a stop.

After building the generation-2 image, run a standalone no-context-mount imagepreflight and the model-free private-Blob canary. Record every build and canaryrun, including failures, with zero tokenizer/model/GPU counters. A pre-observationfailure may be corrected only before the new image and lock are frozen; it isnever a replay or model attempt.

11. Image, lock, and publication order

Use this order and do not observe the live gate:

commit and publish this authority alone;

implement transport, standalone runtime binding, receipt/lock injection,durable journaling, exception-safe artifacts, launcher, wrapper, and tests;

commit and publish final executable bytes as a new executable-code commit;

build the generation-2 image from exactly that commit; perform only static,CPU-only, synthetic/preflight validation; resolve its immutable manifestdigest; and prove it contains the exact executable blobs and authorities;

run the standalone-layout preflight and one model-free private-Blob transportcanary; no live gate, tokenizer, checkpoint, model, or GPU operation;

create a new versioned generation-2 execution lock and schema binding theregistration, all three authorities, generation-1 supersession, new executablecommit/tree, new image/base digests, code hashes, dependency lock, transportimplementation and canary receipt, corpus/P0-T hashes, model revisions, caps,zero counters, and the single replay-then-conditional-GPU sequence;

publish the lock and corrected handoff as strict descendants; no executablebyte may change after the image build; if one changes, discard the unexecutedgeneration-2 image, rebuild from the new code commit, and create a new lock;

run clean exact-commit CPU-only ACR validation, changed-path census, andprotected-byte audit; and

publish by non-force fast-forward, require HEAD == origin/main and a cleanworktree, enter STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE, and stop.

The active handoff must state unambiguously that generation 1 is supersededwithout consumption and cannot be launched. It must give the exact generation-2ready commit/tree, executable commit/tree, image reference/digest, active lockpath/hash, transport-canary identity, replay command, recovery command, mandatoryreceipt/lock-aware GPU command, Blob prefix rule, pass/fail boundary, and terminalpublication boundary. It must not claim that hashes alone make bytes recoverable.

12. Closeout invariants and report

At close require and report:

exact starting, authority, executable-code, image-build, lock, canary, andfinal-ready commits/trees or Azure run identities as applicable;

this authority's bytes, SHA-256, LF/CR count, BOM, and trailing-newline status;

exact changed-path census and protected-byte audit, with generation-1 objectsunchanged;

every concrete generation-1 defect and the production path that closes it;

standalone image-layout proof and explicit final-lock/replay-receipt injection;

replay complete-byte canary, private-Blob canary, hashes, sizes, prefixes, andrecovery proof;

new image repository, immutable digest, base digest, dependencies, executablecommit/tree, active lock identity, and generation-1 supersession record;

every validation/build/canary run ID, failure, exact node-ID count, full-suitereconciliation, and the unchanged historical failure signatures;

all P0-R1 live counters at zero and the immutable P0-T snapshot unchanged;

no P0-R1 results directory, live replay evaluation, tokenizer/model access,GPU execution, seed, bank, selection, positive reference, or evidence row;

p0_r1_pilot_execution_authorized = true, consumed = false, and exactly oneoverall envelope rather than one per lock generation;

frozen = false, formal_execution_authorized = false, interface and positivereference null, OD2/UR-22/RP unresolved, and the research question unanswered;and

the exact fresh-session successor instruction, beginning with the replay gateand allowing the single GPU pilot only after recovered-byte replay pass.

Stop after publication. The sole successor is a fresh P0-R1 execution sessionusing only generation 2. If replay fails, publish the registered stop and performno model operation. If replay passes, consume the exact recovered receipt in thesame execution session, run at most one bounded GPU pilot, recover and publishthe actual emitted bytes, enter a terminal P0-R1 disposition, and stop. Onlyafter a mechanically feasible terminal P0-R1 disposition may a separate freshsession perform the one focused final methods review of draft-v0.6.