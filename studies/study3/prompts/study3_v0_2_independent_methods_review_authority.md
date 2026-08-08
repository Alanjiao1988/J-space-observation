Continue work in the existing repository Alanjiao1988/J-space-observation.

Run this authority in a fresh Copilot CLI session and a fresh platform-managed worktree. Do notcontinue the drafting session that produced draft-v0.2. The independence required here isprocedural and computational: review the already-published design from a new session, derive thestatistics through an implementation that does not import the drafting implementation, and recordthe review without editing the protocol under review.

This is a bounded independent methods-review round only. It is not a protocol-amendment round, afreeze round, a positive-reference selection round, a bank-construction round, or an executionround.

Use UTC for every timestamp. Continue in the same repository. Do not create a new repository. Donot use GitHub Actions.

The required documentation state at the end of this round is exactly:

STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION

The review must return exactly one of the three dispositions already registered by the packet:

STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED

STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES

STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED

The disposition must be earned by the review. This authority does not prescribe which one toreturn. It does prescribe fail-closed rules for unresolved questions and contradictoryspecifications.

Neither the documentation state nor any disposition is a scientific result or an executionauthority.

1. Authority hierarchy and hard boundaries

This prompt is the sole operator authority for this round.

Study 1 remains closed at INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY.

Study 2 remains closed at STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY, withdocumentation state STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE.

Study 3 remains an unfrozen design. No interface is selected, no positive reference is selected,no task bank exists, no seed has been drawn, and no experimental result exists.

The core draft-v0.2 materials are the review object. Do not repair them during the review. Areviewer who edits the object under review has ceased to be an independent reviewer.

The review may create the review record, an independent model-free recalculation, validationcode, a receipt, and mutable routing/ledger updates listed in the whitelist below. It may notedit the protocol JSON, protocol Markdown, protocol schema, review packet, drafting statistics,drafting tables, positive-reference dossier, v0.1 operator review, design receipts, or priorauthority prompts.

OD2 remains an operator decision. The reviewer may assess the statistical qualification designand the generic I4 floor, but may not select, pin, download, tokenize, load, run, prequalify, orsubstitute a positive-reference checkpoint.

OD5 and OD6 may receive explicit methods recommendations. They are not adopted into the protocolby this round. They remain blocking until a later operator authority either amends the draft orexplicitly accepts the review recommendations.

paper/evidence_ledger.csv must remain byte-identical, contain 16 rows, and still end at EV-0016.No scientific evidence row is permitted.

paper/limitations_ledger.md must not be modified. Findings about an unfrozen design are reviewfindings, not limitations of an executed measurement.

No Study 1 or Study 2 path may be modified. Every frozen Stage P, Stage T, Stage B-D, Phase1.0D, seal, manifest, bank, decision, row file, and protected rollup input remains immutable.

This authority permits zero experimental operations: zero model or tokenizer downloads, zerotokenizer constructions, zero weight loads, zero forward passes, zero generations, zeroactivation extraction, zero probes, zero patching, zero ablation, zero lens operations, zeroexperimental provider calls, zero GPU jobs, zero bank rows, zero seeds, zero gate evaluationson models, and zero confirmation accesses.

The reviewer may perform exact arithmetic, deterministic enumeration, schema validation,hashing, Git operations, and CPU-only tests in Azure ACR against a clean exact-commit clone.

Do not run pytest locally. Do not run the review calculation locally. Do not use a local GPU.All calculation and test evidence for this round must come from CPU-only ACR.

Branch and worktree names are observational metadata only. Commit identity, tree identity,ancestry, clean state, and protected-byte identity are authoritative.

No review disposition authorizes protocol freeze, P3-Q, image construction, bank construction,seed draw, development execution, confirmation, or mechanistic work. Each would require alater, separate operator authority.

If any later instruction can be read as permitting an operation prohibited here, the prohibitionwins.

2. Mandatory starting-state preflight

Fetch origin before making any change.

Expected published starting state:

repository: Alanjiao1988/J-space-observation

origin/main and expected HEAD:8a2c4a0b2a73c5d802988333f11ea6c22828f6f5

expected tree:7e9077a32903adfdaa3bede95beba8752fcb5133

parent design commit:360086db495c4c5a098e49a6e8adf73dd143eaef

Study 2 documentation terminal:783ad360030e9105e87301ac5e3af6346076596e

Study 2 measurement terminal:43411e09de425dfae0ee74ba46c68a389311e9a7

Study 1 terminal:6409d2c6d665187e4459d94d490a20d7b085e8af

Verify from committed blobs, not from CRLF-converted working-tree bytes:

HEAD equals origin/main at the exact expected commit and tree.

The expected Study 1 and Study 2 terminal commits, Stage P commit c2e2383e, and Stage T seala958adf4 are ancestors.

The worktree and index are clean, including untracked paths.

The comparison 360086db...8a2c4a0 is exactly seven commits ahead and changes exactly 23 paths:8 added and 15 modified.

paper/artifact_index.csv contains unique, contiguous records through AR-0211, and everyAR-0196 through AR-0211 path, byte count, and SHA-256 matches its committed blob.

At minimum, reverify these core review-object identities:

protocol/interface_calibration_protocol_draft.json:129382 bytes,4648e0386457f17b4d013ebe44b5f47d6ccd9c77bf87d6014eb1cd1e7b8344e8

protocol/interface_calibration_protocol_draft.md:59684 bytes,deb9238d565feea3a748e20313be8d45f8384f3bc50bb89c77caf13b23a37e5c

protocol/interface_calibration_protocol.schema.json:33167 bytes,ff60f1f2f3a8a09797c3dcfe7bb2ee6314aaece152f8cd8069fcd870865a1785

analysis/independent_methods_review_packet.md:28113 bytes,d438b5c4b0008d6afc63cf77cb5ed0858ef958fe8f18acbf97f50c32f698c5e3

analysis/design_statistics.py:28026 bytes,462a86d62e4c53d12a23c5615de2423da1ea9c49b40819bcb26f25f5e9149f94

analysis/design_statistics_tables.json:26713 bytes,48524f066b3f96cdb96b60008318294e2ee883a407ed12e1d8b7a3d0fc60b85f

references/positive_reference_dossier.md:9923 bytes,bdde6514d7431e24f6b3ad4df5e510357850c4fb9289a8b11ad62e0bea35ef39

tests/test_study3_design.py:33894 bytes,98bb923d0c835e1a816d3805930bc6319db07905d13276fb99a2f2d7c7369ebf

design_receipt_v0_2.json:14403 bytes,d7ac6aee782be8a9c9ef88bec1c2e05785e5b25d010e84665019a9ef12969b63

paper/evidence_ledger.csv is still 25241 bytes with SHA-2563821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1,contains 16 rows, and ends at EV-0016.

The protected rollups remain:

436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51ddover 152 files

ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82aover 36 files

Every Study 3 operation counter is zero, and Study 2 cumulative counts remain unchanged.

The current protocol declares draft-only state, no winner, no selected positive reference,OD2/OD5/OD6 blocking, and bounded independent methods review as the only next action.

Record the observed branch/worktree name, but do not use it as a gate.

If origin/main is not exactly the expected commit, do not reset, rebase, cherry-pick, force-push,or silently replay this authority. Stop at:

BLOCKED_ON_STUDY3_METHODS_REVIEW_STARTING_STATE

Report the exact discrepancy.

On success, record:

STUDY3_METHODS_REVIEW_STARTING_STATE_ACCEPTED_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE

3. Required reading

Read every file below in full before implementing the independent calculation or writing adisposition:

README.md

studies/README.md

reports/current_status.md

studies/study3/README.md

studies/study3/RESEARCH_CHARTER_DRAFT.md

studies/study3/NEXT_THREAD_HANDOFF.md

studies/study3/protocol/interface_calibration_protocol_draft.json

studies/study3/protocol/interface_calibration_protocol_draft.md

studies/study3/protocol/interface_calibration_protocol.schema.json

studies/study3/analysis/independent_methods_review_packet.md

studies/study3/analysis/design_statistics.py

studies/study3/analysis/design_statistics_tables.json

studies/study3/analysis/study2_to_study3_design_traceability.md

studies/study3/references/methods_sources.md

studies/study3/references/positive_reference_dossier.md

studies/study3/reviews/v0_1_operator_review.md

studies/study3/design_receipt.json

studies/study3/design_receipt_v0_2.json

studies/study3/prompts/study3_interface_calibration_design_authority.md

studies/study3/prompts/study3_v0_2_design_amendment_authority.md

tests/test_study3_design.py

paper/artifact_index.csv

paper/methods_ledger.md

paper/evidence_ledger.csv

docs/decision_log.md

docs/run_log.md

studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md

studies/study2/decisions/study2_stage_bd_interpretation_erratum.md

studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md

The prior authority prompts are provenance, not evidence. Study 1/2 results and the Study 2post-hoc diagnostic are out of scope for statistical calibration and must not be used as Study 3pilot data.

4. Independence protocol

The review must not merely rerun the drafting script and call matching output independent.

Create a new implementation namedstudies/study3/analysis/independent_methods_recalculation.py.

It must not import, execute, copy functions from, or dynamically loadstudies/study3/analysis/design_statistics.py.

Re-derive the formulas from the cited primary sources and the protocol definitions.

Use a separately structured implementation and separately named internal functions.

The script must have:

an emit mode that writes only its own review table;

a check mode that recomputes its own committed table value-for-value;

fail-closed source/parameter validation;

deterministic output and stable JSON ordering;

no network access, model import, tokenizer import, bank access, or prior result access.

Only after independent values exist may the review compare them withdesign_statistics_tables.json.

For every difference, determine whether it is:

a drafting defect;

a different but defensible statistical choice;

a harmless rounding difference; or

an error in the independent implementation.

Include at least one independent closed-form or published-example check for each implementedstatistical family. Agreement only with the drafting implementation is not validation.

Keep all values classified as proposed design parameters. Do not call them observations,measurements, results, evidence, or model performance.

Use English-language primary statistical sources. At minimum verify:

Tango (1998), Statistics in Medicine 17:891-908, PMID 9595618.

Hsueh, Liu and Chen (2001), Biometrics 57:478-483, PMID 11414572.

Berger and Hsu (1996), Statistical Science, on intersection-union tests and equivalenceconfidence sets.

Any additional primary source used to replace, calibrate, or qualify the paired procedure.

For model-card facts in the positive-reference dossier, use only the official model repository orofficial technical report. Those facts may support a feasibility comment but may not select acheckpoint.

5. Mandatory audit targets

The review must answer the packet's 22 checklist items and the additional targets below. Treatthese as questions to verify independently, not as predetermined findings.

5.1 Cross-artifact semantic consistency

For every decision-bearing statement, compare the authoritative JSON, companion Markdown, reviewpacket, derivation tables, README, and handoff.

At minimum adjudicate:

The authoritative JSON defines the I3 primary item indicator as the answer being identicalacross every applicable variant. The review packet describes it as every variant being scoredcorrect. Determine whether these are the same estimand. Explicitly analyze whether a stable butwrong answer passes either definition. A review may not silently choose one.

The JSON gate-hierarchy verification text says exact enumeration of the paired method does notexceed the nominal one-sided level. The same draft's packet and methods ledger disclose oneconfiguration with realised level 0.025501 against nominal 0.025. Determine whether this is adirect contradiction and whether it invalidates acceptance as specified.

Confirm that every hypothesis with gate authority is stated in packet section 2, includinglabel-uniformity, confirmation, and any profile-selection decision.

Confirm that every sample-size symbol has one unambiguous unit: base items per atomic cell,derived variants, or total calls. No symbol may change units between files.

Confirm that the three permitted review dispositions are operationally distinguishable. Adesign with unresolved parameter values cannot be accepted as specified merely because thereviewer can imagine values that would work.

Every candidate inconsistency must receive one status in the review JSON:

CONFIRMED_BLOCKING

CONFIRMED_NONBLOCKING

NOT_CONFIRMED

QUALIFIED

with file paths, exact quoted field names, and a concise rationale.

5.2 Estimands, atomic cells, and pooling

Decide whether I3 is intended to measure invariance of the chosen content, correctness underevery variant, or both.

If both are required, specify two indicators and their conjunction rather than overloading oneindicator.

Examine whether different numbers of applicable variants across S1, S2, and S3 make theall-variants indicator materially different across profiles.

Confirm whether the base item is the independent unit for every repeated presentation.

Confirm that the six listed pooling prohibitions close every rescue path. Add any missing pathas a required change rather than editing the draft.

Check whether checkpoint roles are conjunctive because the future claim needs all roles, andwhether the null family matches that logic.

Check whether operation family, depth, rendering, label set, label position, role, profile, andsplit are separated at the correct level without producing undefined or empty cells.

Check that not_applicable is never converted into pass, zero effect, a denominator entry, or areduction in a multiplicity denominator after data are observed.

5.3 Multiplicity and selection

Provide a formal null/alternative set for:

the conjunction of cells within one profile;

the union over selectable profiles;

development selection;

the single selected confirmation profile;

the label-uniformity nuisance check;

the positive-reference cells;

all retained roles, families, depths, and renderings.

At minimum adjudicate:

Whether the Family A intersection-union argument is valid for the actual profile claim.

Whether the Family B Bonferroni statement is implemented. The draft states per-profile alpha0.001666666667 while retained component rules use alpha 0.005. Show mathematically how thestated per-profile level is achieved, or record a required change.

Whether S3 counts in the selection denominator when its registered selectability condition isnot activated. The rule must be fixed before any data and may be conservative, but it may notbe chosen after outcomes.

Whether the development screen needs confirmatory family-wise error control at all if thescientific calibration claim is made only on an independent one-shot confirmation bank.

If development and confirmation use different error roles, specify both rather than applyingone alpha statement to both.

Whether the never-selectable S4 is correctly excluded from every success union while stillreceiving diagnostic checks with zero selection authority.

Return one explicit multiplicity decision graph that another implementation could execute withoutinterpretation.

5.4 Exact-binomial gates and power

Independently reproduce exact upper tails, rejection counts, and power for I1a, I1b, I2, I3primary, and I4.

The review must:

Define p0, the smallest alternative of interest p1, alpha, target power, n, and rejection countfor each gate and each split.

State why each p0 and p1 is substantively meaningful. Do not choose a floor or margin becauseit makes a preferred sample size pass.

Account for discreteness. Exact-binomial power is not necessarily monotone in n when therejection count changes. Search the full admissible n grid implied by counterbalancing, notonly 128, 192, 256, and 384.

State the counterbalancing divisor that makes an n admissible.

Decide whether the disclosed I1a/I1b power of 0.87425 at n 192, p1 0.97, and alpha 0.005 isacceptable. If not, return the smallest admissible n meeting the reviewed target.

If the multiplicity review changes component alpha, recompute every affected threshold andsample size. Do not retain tables computed at alpha 0.005 while claiming control at0.001666666667.

5.5 I3 robustness and paired equivalence

Resolve the I3 primary estimand before reviewing its threshold.

Decide whether aggregate paired equivalence has gate authority, secondary inferential status,or descriptive status only.

A non-significant difference is not equivalence.

A margin must represent the largest presentation effect considered practically irrelevant. Itmay not be widened to fit n.

If Tango's asymptotic score rule is retained, independently reproduce its rejection region andverify type-I behavior.

The phrase exact enumeration must never be used as if it made an asymptotic decision ruleexact or conservative.

The four discordance values 0.05, 0.10, 0.20, and 0.30 are a sensitivity grid, not proof ofglobal size control. Either:

supply a justified nuisance-parameter maximization over the feasible null boundary;

calibrate a conservative critical value over the full registered parameter domain;

use a conservative-by-construction exact procedure; or

leave the method unresolved and return a non-accepting disposition.

If numerical optimization is used for a continuous nuisance parameter, register its domain,tolerance, bracketing rule, convergence failure behavior, and an independent validation.

Determine whether the 0.025501 exceedance is acceptable under the claimed study alpha. Ifaccepted, state the inferential consequence precisely; if not, return the corrected rule andrecomputed power.

Return an explicit development and confirmation sample-size recommendation for I3, or statethat the current information cannot justify one.

5.6 I4 and the positive reference

Review the generic competence floor p0 0.80 and at least one predeclared alternative p1.

Review the I4 sample size and multiplicity-adjusted alpha per operation family and depth.

State whether passing p greater than 0.80 is sufficient for the claim that the positivereference is capable on the registered K4 construct.

Separate:

P3-Q prequalification of the checkpoint through an external canonical qualificationinterface; and

I4 demonstration that the already-qualified checkpoint succeeds through each candidateStudy 3 interface.

Check that the same bank, same model observation, or same candidate-panel outcome cannot qualifythe reference and validate the interface circularly.

Review the statistical fields that a later OD2 authority must freeze: qualification floor,p1, alpha, n, rejection count, family/depth treatment, stopping rule, and bank isolation.

Do not choose Qwen3-4B-Instruct-2507, Qwen2.5-Math-7B-Instruct, or any other model in thisreview. Candidate identity, immutable revision, runtime, dtype, and wrappers remain OD2.

5.7 Confirmation and one-shot lifecycle

Specify what I5 confirms: each gate-bearing construct for the single development-selectedprofile, including RP/I4/K4.

Specify confirmation n, alpha, thresholds, and multiplicity treatment.

Determine whether development selection on an independent bank permits one-profileconfirmation without an across-profile correction, and state the conditions required.

Confirm that a confirmation error or ambiguity spends the split and cannot be retried.

Confirm that no confirmation result can select a different interface.

Confirm that a confirmation pass still creates only interface-calibration evidence and nomechanistic authority.

5.8 Feasibility and operation accounting

Produce a model-free projected cell and operation table. It must distinguish:

base items per atomic cell;

derived presentation variants per base item;

rows scored per role, profile, stratum, family, depth, rendering, and split;

RP prequalification work;

RP I4 work;

target development work;

selected-profile confirmation work;

S4 diagnostic work;

total forward passes and total generations, while keeping both at zero in this round.

The table is planning arithmetic, not an execution authorization. Cost may be reported, but costmust not be used to weaken a required scientific contrast.

6. Required review outputs

Create these eight files and no other new path:

studies/study3/reviews/v0_2_independent_methods_review.md

studies/study3/reviews/v0_2_independent_methods_review.json

studies/study3/reviews/v0_2_independent_methods_review.schema.json

studies/study3/analysis/independent_methods_recalculation.py

studies/study3/analysis/independent_methods_recalculation_tables.json

tests/test_study3_methods_review.py

studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md

studies/study3/methods_review_receipt_v0_2.json

The authority file must be byte-identical to this prompt: no header, footer, commentary,normalization, or added trailing newline.

6.1 Human-readable review

The Markdown review must:

bind the reviewed commit, tree, and every core artifact hash;

declare the independence procedure;

answer all 22 registered checklist questions in order;

answer every mandatory audit target above;

list stable review finding IDs beginning S3MR-001 with severity BLOCKING, MAJOR, or MINOR;

state CONFIRMED_BLOCKING, CONFIRMED_NONBLOCKING, NOT_CONFIRMED, or QUALIFIED for each candidateinconsistency;

provide one reviewed parameter table with gate, estimand, unit, p0 or margin, p1, alpha, n,rejection rule, power, split, applicability, and authority status;

provide the executable multiplicity decision graph;

provide the projected cell/operation table;

distinguish reviewer recommendation from adopted protocol;

state OD2, OD5, and OD6 after review;

return exactly one permitted disposition;

state the next legal action under that disposition;

repeat the claim ceiling and all zero-operation boundaries.

6.2 Machine-readable review

The JSON review must include at least:

schema_version;

state;

reviewed_commit and reviewed_tree;

reviewed_artifact_identities;

reviewer_independence;

disposition;

checklist_answers containing exactly IDs 1 through 22;

mandatory_audit_answers;

findings with stable IDs and severity;

cross_artifact_consistency;

estimand_decisions;

multiplicity_decision;

gate_parameter_recommendations;

paired_method_decision;

positive_reference_statistical_requirements;

confirmation_decision;

projected_operation_accounting;

operator_decisions with OD2, OD5, and OD6;

unresolved_items;

claim_ceiling;

absence_of_execution_authority;

operation_counts, all zero;

next_legal_action.

The schema must reject:

an unknown disposition;

fewer or more than 22 registered checklist answers;

an unanswered checklist item;

a finding without evidence paths or severity;

a binding parameter with no unit;

a selected interface or selected positive reference;

any frozen or execution-authorized state;

any non-zero operation counter;

any result row, bank row, seed, model output, or evidence row;

an accepted-as-specified disposition with an unresolved blocking methods item;

a next action that jumps directly to freeze or execution when required changes exist.

6.3 Independent recalculation tables

The committed review table must include:

exact-binomial thresholds and power over the full admissible n grid reviewed;

the admissible-n rule;

drafting-table comparison;

the paired rejection-rule definition;

type-I and power results with a clear distinction between enumeration accuracy and test size;

nuisance-parameter optimization or calibration results if used;

multiplicity-adjusted alternatives;

reviewed candidate parameter sets;

projected cell and operation counts;

a status that says these are proposed design parameters, not measurements.

6.4 Committed test

tests/test_study3_methods_review.py must:

validate the review JSON against the committed schema without adding a new dependency;

run the independent recalculation in check mode;

assert that the independent script does not import or execute design_statistics.py;

bind the reviewed artifact identities;

enforce the exact 22 checklist IDs;

enforce the disposition rules;

enforce zero counters and all prohibited authority flags;

enforce no interface/model selection;

enforce OD2 remains operator-controlled;

enforce that required changes cannot route to freeze;

check every reviewed parameter carries an unambiguous unit;

check Markdown/JSON parity for disposition, reviewed commit, finding IDs, OD statuses, and nextaction;

include a negative-mutation battery that proves each fail-closed rule can reject a corruptedreview;

accept the unmutated committed review.

Do not modify tests/test_study3_design.py merely to make the review pass. If the existing testexposes a defect, record it.

7. Disposition rules

Return STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED only if:

all 22 checklist questions are answered affirmatively or with a nonblocking qualification;

every U1 through U8 issue is resolved without changing a decision-bearing statement;

no cross-artifact contradiction remains;

every gate has an executable hypothesis, unit, alpha, n, rejection rule, and power basis;

the multiplicity statement is actually implemented;

OD5 and OD6 can be adopted mechanically without substantive amendment.

Do not use this disposition merely because the reviewer supplies values the draft omitted.

Return STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES only if:

the core design is methodologically salvageable;

every required change is explicit, bounded, internally compatible, and sufficient for a lateramendment;

no unresolved issue requires observing model data;

a later draft-v0.3 amendment can implement the review without inventing a new design.

Return STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED if:

the estimand is not identifiable from the current structure;

valid type-I or power control cannot be specified from the current design;

required changes would alter the core design rather than repair it;

a blocking issue remains unresolved after the review; or

the reviewer cannot independently validate a decision-bearing method.

An unresolved checklist item is never acceptance. A disagreement between the human andmachine-readable review is a validation failure, not a reason to choose the friendlier text.

Conditional next actions:

Accepted as specified: operator review of the recommendation, separate OD2 resolution, then aseparate freeze decision. Still no freeze authority here.

Accepted with required changes: a separately authorized draft-v0.3 amendment, then anotherbounded conformance review. No freeze.

Rejected: redesign under a new authority. No freeze.

Do not provide a freeze prompt, P3-Q prompt, bank prompt, Azure GPU prompt, or experiment prompt inthe repository or final response.

8. Mutation whitelist and registries

New paths are exactly the eight paths in section 6.

The only existing paths that may be modified are:

README.md

studies/README.md

studies/study3/README.md

studies/study3/NEXT_THREAD_HANDOFF.md

reports/current_status.md

docs/decision_log.md

docs/run_log.md

paper/methods_ledger.md

paper/artifact_index.csv

That is a maximum whitelist of 17 changed paths: 8 added and 9 modified.

The two Study 3 README/handoff files are mutable routing surfaces. Their edits must be limited tothe completed review state, the disposition, and the correct next legal action. They must bind thereviewed v0.2 commit and must not rewrite the v0.2 protocol, packet, statistics, or historicalrationale.

Do not modify:

any Study 1 or Study 2 path;

any Study 3 protocol, schema, packet, drafting statistics/table, source dossier, prior review,receipt, prior authority, or traceability path;

paper/evidence_ledger.csv;

paper/limitations_ledger.md;

paper/claim_evidence_matrix.md;

dependencies, lockfiles, containers, runtime source, or GitHub workflows.

Register:

decision D40 for the independent methods-review disposition;

method M-28 for the independent recalculation and review method;

contiguous artifact IDs beginning AR-0212.

Register AR-0212 through AR-0219 for the eight new files in section 6, in that order. Re-registerthe updated Study 3 README and NEXT_THREAD_HANDOFF as AR-0220 and AR-0221. Each record must use thecommitted blob's exact byte count and SHA-256 and must classify the artifact as design review,provenance, validation, or review method, never scientific result.

Do not alter D39, M-27, or AR-0196 through AR-0211.

The review receipt must bind:

starting commit and tree;

reviewed artifact identities;

review disposition;

new artifact identities, excluding its own self-hash in the body;

changed-path whitelist and observed changed paths;

validation runs;

zero operation counts;

protected rollups and evidence-ledger identity;

publication ancestry;

remaining authority.

9. Commit and validation sequence

Use intentional, reviewable commits. A suggested sequence is:

Preserve this authority prompt verbatim.

Add the independent recalculation, table, schema, review JSON/Markdown, and committed test.

Add the receipt and update the mutable routers and registries.

Add the final ACR validation record to docs/run_log.md.

Do not squash away the distinction between the independent calculation and the publicationbookkeeping.

All validation must run in CPU-only Azure ACR using python:3.11-bookworm or the exact alreadyregistered CPU validation image. Build from a clean exact-commit clone supplied through theregistered Git bundle or equivalent source-binding route. Report:

BOUND_COMMIT;

BOUND_TREE;

DIRTY=0;

Python version;

CPU-only and zero GPU;

exact commands;

exit codes;

complete pass/skip/registered-historical-failure counts.

At minimum run:

tests/test_study3_methods_review.py;

tests/test_study3_design.py;

the Study 2 focused regression set used in the prior round;

the full repository test suite;

design_statistics.py --check, only as regression of the reviewed bytes, not as independentvalidation;

independent_methods_recalculation.py --check;

the Study 2 Stage T and Stage B-D model-free validators;

an exact artifact-index uniqueness/contiguity and blob-digest check;

both protected rollup checks;

evidence-ledger byte/hash/row/tail check;

a static zero-operation and zero-authority check;

a changed-path whitelist check.

Run focused and full validation on the final commit that will be published. If a final validationrecord is added after a validation commit, run at least the focused review tests, registry checks,protected-byte checks, and clean-state check again on the actual publication commit. Do not claim acommit was validated by a run bound to its parent.

Any validation helper carrying decision authority must be committed. A purely supplementaloperator-side checker may be ephemeral only if it is fully disclosed and no conclusion depends onit.

The two accepted historical test_parser_v3_seal_job failures may remain only if they are exactlythe same registered failures and no new failure appears.

10. Publication rules

Before push:

Fetch origin.

Confirm origin/main still equals the exact starting commit.

Confirm the review branch is a strict descendant.

Confirm the worktree/index are clean after the final commit.

Confirm the diff from the starting commit is wholly inside the whitelist.

Confirm every protected byte and counter.

Publish only by fast-forward:

git push origin HEAD/heads/main

Never force-push.

After push, verify:

HEAD equals origin/main;

the final tree;

strict ancestry from the starting commit and all Study 1/2 terminals;

clean worktree and index;

all review artifact bytes and SHA-256 values against committed blobs;

artifact registry uniqueness and contiguity through AR-0221;

evidence ledger unchanged at EV-0016;

both protected rollups unchanged;

all experimental operation counts zero.

If remote main moves before publication, stop. Do not replay or merge this review without a newoperator decision.

11. Required final handoff

Lead with the exact review disposition and documentation state. Report:

starting and final commit/tree;

ancestry and fast-forward publication proof;

changed paths, split into added and modified;

reviewed artifact identities;

independence procedure and independent calculation identity;

answers to the most consequential checklist items;

every BLOCKING and MAJOR finding;

the exact adjudication of:

I3 identical-answer versus all-variants-correct semantics;

the 0.025501 versus 0.025 statement;

Family B per-profile alpha versus component alpha;

I1a/I1b power and admissible n;

I3 method/margin/sample size;

I4 floor/sample size;

confirmation alpha/sample size;

projected operation count.

the reviewed parameter recommendation table;

OD2, OD5, and OD6 status;

D40, M-28, and AR-0212 through AR-0221;

ACR validation runs and exact results;

evidence-ledger and protected-rollup identities;

operation counts, all zero;

the only legal next action under the returned disposition.

State explicitly:

Study 1 remains closed.

Study 2 remains closed.

Study 3 remains unfrozen.

No interface or positive reference is selected.

No bank, seed, model operation, gate result, or evidence row exists.

The original research question remains unanswered.

No freeze or execution authority was created.

Stop after publishing and reporting the independent review. Do not continue into amendment,freeze, P3-Q, bank construction, Azure GPU execution, confirmation, or mechanistic work.