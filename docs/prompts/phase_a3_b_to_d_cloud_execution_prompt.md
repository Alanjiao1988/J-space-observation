Take over this repository and continue the existing parser-v3 validationexperiment:

repository: https://github.com/Alanjiao1988/J-space-observation.git
branch: main
verified remote HEAD: a99d1e8341af85b8db32cb97a46ed5095c3f7978
verified local candidate HEAD: 6faa1045fbf580ce4ab867d9e3aaf6aa90c03616
verified local candidate tree: 183dc7f4d8b1b07411db03f154f49bc24edf47c6
local commits not yet on origin/main: 13
last Azure validation: ACR run cm2m
last Azure result: 2493 passed / 15 skipped / 2 failed
candidate worktree at cm2m: DIRTY=0

The two failures are the same disclosed sealed-input environmental failurespresent at starting commit a99d1e8; the verified delta is +258 passing testsand zero new failures. Do not convert those failures to skips, xfail, or weakassertions.

The current scientific state is still:

BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY
sealed semantic input reads = 0
sealed semantic label reads = 0
candidate v2 cases = 0
labels opened for scoring = 0
private parser runs = 0
predictions = 0
formal evaluations = 0
formal evaluation ordinal = 0

This prompt supersedes earlier starting-state and Phase-A work lists whereverthey conflict with the facts above. All scientific, privacy, immutability,independence, one-shot, parser-isolation, protected-file, and zero-tolerancerules registered in the repository remain binding.

1. Operator authorization and required outcome

The operator explicitly approves the project-owned Azure expenditure neededfor this round. Do not stop to ask again merely because the design requires:

a new Premium private runtime ACR;

Azure Firewall Standard, UDRs, NSGs, private DNS, and private endpoints;

a dedicated VNet and internal Container Apps workload-profiles environment;

one or more Consumption-GPU-NC8as-T4 profiles and sufficient T4 runtime;

private storage for model weights and role lanes;

additional regional CPU/GPU capacity or a stronger Southeast Asia backendwhen live evidence shows T4 is inadequate.

Cost must be measured, tagged, reported, and scaled to zero when idle, but costis not an acceptance gate. Do not select a weaker review model, weaker networkboundary, or undersized runner merely to minimize spend. Do not move privatecase content outside Southeast Asia without separate operator authorization.

The primary success state for this round is:

SEALED_READY_FOR_PREREGISTRATION

It requires all of the following:

the exact 13-commit chain ending at 6faa1045... is fast-forward pushed andverified on origin/main;

all remaining public Phase A artifacts are complete, independently audited,frozen, pushed, and Azure-validated;

the actual private review boundary is deployed from committed IaC and passespositive and negative runtime qualification on public synthetic data;

the authoritative retired-v1 source is accessed semantically only after theprospective freeze and boundary qualification;

exactly one eligible 120-case parser-v3-v2 set is constructed under thefrozen rules, independently reviewed, arbitrated, audited, and verified;

that set is sealed create-only with an authenticated real listing witnessand one-time final contract;

the remote Git branch and all public, content-free receipts are current.

Do not run formal Stage P or Stage E in this round. Do not invoke parser v3,parser v2, or the legacy parser on retired-v1, candidate-v2, or sealed-v2material. Do not generate predictions or open labels for scoring. The nextround will independently freeze post-seal preregistration and authorize thesingle formal launch.

Anticipated effort, cost, context-window length, or a statement that laterphases may take weeks is not a scientific blocker. If the product session mustend before the authorized outcome, create and push the largest honestnonterminal checkpoint and report:

NONTERMINAL_CHECKPOINT_<EXACT_NEXT_GATE>

Do not mislabel a session boundary as BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY.

2. Four hard operating rules

2.1 Azure executes; the laptop only edits and orchestrates

Permitted on the laptop:

read and edit tracked public source, tests, documentation, schemas, IaC, andprompts;

lightweight git status, git log, git diff, git rev-parse,git ls-files, git fetch, commit, and non-force push operations;

repair Git transport authentication through the OS credential manager;

submit Azure control-plane operations and poll bounded status fields;

read short, closed, content-free receipts and bounded diagnostic tails;

create one exact tracked-only archive or bundle in a round-specific temporarydirectory when Azure cannot clone the exact commit, then remove it afterAzure has accepted and verified it.

Forbidden on the laptop:

every pytest invocation, even one focused test;

imports used as tests, compileall, lint, type checks, schema validation,Bicep build/what-if, generators, scanners, coverage, mutation runs, benchmarks,or repository-wide analyses;

package installation, Docker/Podman/buildah, compilation, model download,model loading, inference, CUDA work, or GPU work;

private Blob listing, hashing, streaming, decoding, migration, review,arbitration, sealing, scoring, or case-level output reading;

local auditor or subagent workloads;

any sustained computation expected to use more than two CPU cores or runlonger than two minutes.

All such work must run through ACR Tasks, Azure Container Apps Jobs, thequalified in-VNet GPU jobs, or another committed and explicitly qualifiedAzure runner. If a command crosses the local boundary accidentally, terminateit, record the operational deviation, and rerun it in Azure. Do not reinterpretan operational deviation as a scientific breach unless a scientific invariantwas actually crossed.

2.2 Minimize local files without deleting unknown user data

At the start, record only the names/status of untracked and ignored paths. Donot open ignored or private material.

After every Azure source upload, remove the exact local archive/bundle and itsround-specific temporary directory once remote acceptance is proved. At finalremote verification, retain only:

.git and tracked repository files;

required Git/Azure/Copilot configuration;

pre-existing untracked/ignored/private items whose safe removal has not beenaffirmatively established.

Delete only exact, verified, regenerable artifacts created by this round,including bounded downloaded logs and known cache/build directories. Resolveeach target, reject symlinks, display a dry-run list, and then delete exactpaths. Never run git clean -fd, git clean -fdx, wildcard recursive removal,or cleanup against the workspace root, user profile, home directory, or anunresolved environment variable. Preserve .env, credentials, Azure profiles,locked inputs/labels, curator files, and unknown ignored material unless theoperator separately names an exact target.

2.3 Handoff-first and repository-complete

Save this prompt verbatim in the repository at:

docs/prompts/phase_a3_b_to_d_cloud_execution_prompt.md

Commit every public program, test, schema, lock, IaC definition, roleentrypoint, synthetic fixture, audit prompt/report, runbook, content-freereceipt, decision record, status generator, and handoff required to reproduceor understand the round.

Private case-bearing inputs, labels, review packets, model outputs,arbitrations, candidate sets, facts, manifests, listing witnesses, and finalcontracts stay in private Azure storage. Git contains only public definitionsand approved content-free hashes, counts, resource IDs, aggregate results, andreceipts. This is the necessary exception to “all experiment content is savedin GitHub.” A live Azure resource without committed reproducible IaC and aread-back receipt is not a deliverable.

2.4 GitHub is only Git transport and the repository tree

Allowed GitHub use:

ordinary clone/fetch/push transport;

reading the repository tree at an exact commit.

Forbidden GitHub use:

Actions, workflow files, workflow dispatch, checks, or status APIs;

PRs, issues, discussions, projects, releases, Pages, Packages, GHCR,artifacts, caches, Codespaces, or any GitHub runner;

GitHub API/App automation for writes or workflow-related reads.

Do not add, change, delete, enable, or trigger .github/workflows/*. Existingworkflow files are historical and out of scope.

3. Work package 0 — resolve D-03 before new development

The repository itself is not read-only. The wrong cached accountalanjiao_microsoft was used by the previous CLI session. Resolve Git transportauthentication without exposing a password, PAT, browser cookie, or token inchat, logs, commits, Azure commands, or shell history.

From the existing worktree, read repository instructions and preserve alluser work.

Confirm:

origin URL = https://github.com/Alanjiao1988/J-space-observation.git
origin/main = a99d1e8341af85b8db32cb97a46ed5095c3f7978
HEAD = 6faa1045fbf580ce4ab867d9e3aaf6aa90c03616
HEAD^{tree} = 183dc7f4d8b1b07411db03f154f49bc24edf47c6
git rev-list --count origin/main..HEAD = 13
worktree = clean
origin/main is an ancestor of HEAD

If origin/main differs, do not rebase, amend, reset, force-push, or rewritethe already Azure-bound 13 commits. Report BLOCKED_ON_GIT_DIVERGENCE withboth SHAs and the smallest reconciliation needed.

Configure credential selection for this repository/path rather thansilently reusing the wrong GitHub account. Use the installed Git CredentialManager/OS browser flow. Clear only the credential selected for thisrepository when possible. Pause for the operator to complete browser/deviceauthentication as Alanjiao1988; never ask the operator to paste a secret.

Push the exact commit, without amending it:

6faa1045fbf580ce4ab867d9e3aaf6aa90c03616:refs/heads/main

Fetch and prove origin/main equals the full 6faa1045... SHA and the sametree. From Azure, clone/fetch that exact remote SHA and re-check the commit,tree, protected digests, DIRTY=0, and the committed cm2m receipt. Do notrerun the suite merely to repair authentication unless a binding check fails.

If Git authentication still returns 403 after the correct interactive accountis selected, stop with BLOCKED_ON_GIT_CREDENTIAL. Do not continue developinganother local-only chain and do not use a Git bundle as a permanent substitutefor the required GitHub history.

4. Starting implementation that must be preserved

Treat the following as the already Azure-validated scientific core, not a newdesign exercise:

parser_v3_v2_lifecycle.py: ordered lifecycle, exclusive states, create-onlyobjects, one-time ordinal, role-channel isolation, and one-time final contract;

parser_v3_v2_construction.py: strata and decision quotas, blinded A/B reviewand arbitration, closed isolation reasons, bounded replacement ending inBLOCKED_ON_SET_REPAIR, order-independent content-hash selection, fourcollision rules, and refusal to target the historical 105/15 split;

parser_v3_v2_evaluation.py: create-only preregistration over a closed bindingset, Stage P, create-only prediction sealing, and Stage E that recomputesPASS/FAIL from gates;

test_parser_v3_v2_rehearsal.py: public synthetic end-to-end rehearsal throughthe real entrypoints;

requirements.lock.txt: 94-package Azure-generated dependency lock;

all 258 additional passing controls through cm2m, including PA-01 throughPA-06 remediations.

Preserve these registered properties:

Stage E refuses any sealed case marked ineligible; it never skips it orshrinks the 120-case denominator;

template_family does not mask every alphanumeric segment and recreate thePA-03 false-positive defect;

fixtures do not use “one template plus case ID” to defeat the registeredcollision rule;

new tests remain import-order independent;

the §7.4 lane matrix wins over any looser prose;

tests drive production entrypoints, not simplified replicas;

each mutation control demonstrates that changing the module's own policytable/constant changes live behavior;

no existing test is weakened, removed, skipped, or xfailed.

Modify this core only if the remaining integration work demonstrates a realdefect. A fix requires a failing positive/negative control, an Azure-onlybaseline/candidate comparison, a decision record, and independent re-review.Once the prospective Phase A freeze is pushed, no bound scientific byte maychange in this lineage.

5. Work package 1 — finish and freeze all public Phase A material

Complete these four remaining deliverable groups using public synthetic dataonly.

5.1 Closed machine-readable schemas

Add closed JSON Schemas for every cross-role and lifecycle artifact actuallyconsumed by production entrypoints, including at minimum:

blinded case packet;

reviewer decision;

disagreement and arbitration packet/result;

admission, quarantine, and replacement record;

construction plan and set-facts projection;

planned seal members, terminal manifest, authenticated-listing projection,listing-witness receipt, and final-contract receipt;

preregistration lock, prediction member/manifest/receipt, Stage-E result, andterminal-state receipt;

deployment/read-back evidence, runtime canary result, access event, andcontent-free public receipt.

Schemas are public; instances containing case content are private. Use explicitschema versions, required fields, enums, cardinalities, length/range constraints,and additionalProperties: false at every object boundary unless a preciselydocumented extension object is required. Bind schema IDs and hashes in thelifecycle. Production entrypoints must call the same validators the testsexercise. Reject unknown fields, wrong versions, duplicate IDs, partial sets,and schema/entrypoint substitution.

5.2 Per-role production container entrypoints

Create small, noninteractive, fail-closed entrypoints for the exact role matrix.At minimum cover:

source custodian and normalizer;

reviewer A and reviewer B;

disagreement broker and arbiter;

selector/replacement coordinator and private set auditor;

facts/compiler and seal custodian;

preregistration compiler;

Stage P, prediction sealer, Stage E, and receipt exporter.

Each entrypoint must:

invoke the real lifecycle/construction/evaluation implementation;

declare exactly one role and explicit UAMI client ID;

accept only registered private endpoints, containers, prefixes, schema IDs,image digests, and config hashes;

forbid ambient credential fallback, keys, SAS, connection strings, and clientsecrets;

verify the role's actual read/write lanes before payload access;

log only closed event IDs/statuses and never raw values, prompts, responses,object names under private prefixes, or exceptions containing content;

refuse parser imports/calls in construction/review/sealing roles;

refuse label access in Stage P and parser access in Stage E;

make the executable call graph mechanically inspectable.

Container commands in IaC must name these exact entrypoints. Tests must mutatethe configured command, module binding, role, identity, and lane to prove thatthe deployed path—not merely a similarly named function—is constrained.

5.3 Reproducible Azure IaC under infra/azure/

Commit Bicep modules, parameter templates, deployment/read-back scripts, andwhat-if/check tooling for every Phase B resource. No portal-only state or shellhistory is a deliverable.

Use a dedicated project boundary rather than modifying the existing shared ACAsubnet. Prefer a new non-overlapping VNet in southeastasia with separate:

AzureFirewallSubnet of valid size;

Container Apps infrastructure subnet sized for workload profiles and GPUreplica IP use;

private-endpoint subnet;

any exact management/staging subnet that the frozen design proves necessary.

The modules must cover:

VNet, subnets, NSGs, route table, Azure Firewall Standard and policy;

internal workload-profiles Container Apps environment;

T4 workload profile discovered from live regional inventory;

a new Premium runtime ACR, private endpoint, dedicated data endpoints whenused, and privatelink.azurecr.io DNS/linkage;

a new Blob private endpoint in the dedicated VNet forstjspacefiles0709085305 and privatelink.blob.core.windows.net linkage;

model-weight storage lanes/mounts;

private role containers and create-only evidence lanes;

distinct UAMIs and least-privilege RBAC/custom roles;

diagnostic settings that cannot emit semantic payloads;

resource locks/tags where appropriate;

exact outputs needed for content-free deployment receipts.

Do not assume an address prefix. Query the live subscription/VNet addressspaces in Azure, choose a non-overlapping range mechanically, freeze it in adecision record, and make Bicep refuse overlap.

5.4 Public synthetic rehearsal and two independent audits

Rerun the public synthetic rehearsal through the new schemas, exact containerentrypoints, role configuration, and lifecycle. It must include:

a clean 12x10 construction;

blinded A/B agreement;

deterministic disagreement and arbitration;

quarantine and bounded replacement;

every collision rule;

create-only set seal and listing witness;

preregistration, Stage P, prediction sealing, and Stage E on public syntheticmaterial only;

the PASS, FAIL, INVALID, partial-upload, partial-prediction, wrong-role,wrong-entrypoint, ineligible-sealed-case, and second-launch paths.

Obtain two separate read-only public audits against one exact candidate commit:

methodology/lifecycle/admission/blinding/replacement/sealing audit;

repository/entrypoint/schema/IaC/runtime-binding/security audit.

Auditors must run remotely, receive no private content, not see one another'sdrafts, and return finding IDs, severity, evidence, reproduction, disposition,and residual limitation. Use distinct model families/backends when liveavailability permits; otherwise use isolated contexts and disclose the sharedmodel limitation without claiming statistical independence. Every BLOCKER andMAJOR must be remediated and re-reviewed against the exact final commit. Thelast remediation must be re-reviewed. Limit the audit/remediation loop to twobounded cycles; if material BLOCKER/MAJOR findings remain, stopBLOCKED_ON_PUBLIC_PROTOCOL_FREEZE rather than declaring convergence.

After all public gates pass, create and push a prospective freeze commit. Bindits commit, tree, protected raw-byte digests, policy full-file and semantichashes, schema hashes, lock hash, image inputs, entrypoints, Bicep, role matrix,and retry rules. No private semantic read may precede remote verification ofthis freeze.

6. Canonical Phase B architecture and deployment

6.1 Separate public build ACR from private runtime ACR

Do not upgrade and then repeatedly reopen the same ACR around private runs.Use two roles:

existing Basic ACR acrjspaceobssea0708231738: public-code build/test only;it may run ACR Tasks but may never receive private data, model prompts,reviews, candidate sets, predictions, or scoring output;

new Premium ACR: frozen private-runtime images only; populate it beforelockdown, create a private endpoint, disable public network access, and neverreopen it after the first private semantic read.

This separation is deliberate: Microsoft documents that az acr build failswhen public access is disabled unless a suitable dedicated agent pool or publictask IP route is available, while dedicated ACR task agent pools are notcurrently listed for Southeast Asia. Keep ACR Tasks on the build registry andruntime pulls on the private registry. Prove the private worker has no role ornetwork path to the public build registry.

Build every final runtime image from the pushed prospective freeze, pin bydigest, scan the payload, copy/import it into the Premium runtime ACR beforelockdown, and verify the copied manifest/layer digests. Mutable tags are notexecution bindings.

6.2 Dedicated private worker boundary

Deploy an internal workload-profiles Container Apps environment in the newdedicated VNet. Route external egress from the ACA subnet through AzureFirewall using a UDR. NSGs must prevent direct bypass. Private endpoints andprivate DNS serve Blob and the runtime ACR.

Allow only the documented Container Apps platform dependencies and exactproject destinations needed by the frozen design. Record every service tag,FQDN, IP, port, priority, and residual surface. NAT, UDR, NSG, firewall, DNS,or a private endpoint existing is not proof; the actual deployed job must passruntime probes.

6.3 Self-hosted regional review backend

Prefer self-hosted open-weight review jobs onConsumption-GPU-NC8as-T4 inside the private environment so case content neverleaves the role container boundary. Query live Southeast Asia profile supportand quota rather than assuming it. Stage model weights and licenses before anyprivate case read using a separate staging identity/path. Verify license,provenance, size, SHA-256/content manifest, malware scan, tokenizer/config, andruntime compatibility. Store weights privately; never put weights or privatemodel outputs in Git or the public build ACR.

Freeze model selection before observing any private case. Reviewer A and Bshould use distinct eligible model families where they both pass the publicstructured-output and semantic qualification suite. The arbiter must beseparately initialized and isolated. If only one family qualifies, record thelimitation and do not call the judgments statistically independent.

If T4 memory or measured public qualification is inadequate, do not reduce thereview gate. Discover a stronger qualifying Southeast Asia GPU VM/workloadprofile or a project-owned regional managed model with private endpoint,managed-identity authentication, public/key access disabled, and acceptablegovernance. This cost is authorized. Do not move private content to anotherregion merely to obtain A100.

Use deterministic structured generation where supported: frozen model andtokenizer revisions, API/runtime image digest, decoding parameters, seed,maximum tokens, timeout, retry rule, schema repair rule, and refusal behavior.Do not treat model agreement as human ground truth.

6.4 Exact identities and lanes

Use separate UAMIs and containers/prefixes for source custodian, reviewer A,reviewer B, broker, arbiter, selector/replacement coordinator, set auditor,seal custodian, preregistration compiler, Stage P, prediction sealer, Stage E,and receipt exporter.

Mechanically enumerate direct and inherited effective permissions. RejectOwner, Contributor, storage-account-wide data access, keys, SAS, or deleterights where the role does not need them. Cross-lane negative tests must provedenial. The construction roles must not have parser image/code/results access;Stage P must not have label access; Stage E must not be able to invoke/importthe parser.

6.5 Runtime qualification on public synthetic data

Bind the real deployed resource IDs, images, revisions, commands, UAMIs,RBAC, private IPs, DNS answers, routes, firewall/NSG rules, model revisions,weight hashes, storage lanes, and executions.

Required positive probes:

managed-identity token acquisition by the exact role;

private DNS resolution for Blob and runtime ACR;

frozen image pull from the private ACR;

exact permitted synthetic-lane reads and create-only writes;

reviewer A/B structured calls, forced disagreement, broker, arbiter,selector, audit, fake seal, and receipt export;

restart-safe recovery of content-free run status.

Required negative probes must make real short-timeout attempts and fail:

example.com:443, github.com:443, api.openai.com:443,chatgpt.com:443, and one fixed public test IP;

public endpoints for the private ACR and Blob account;

the existing Basic build ACR from a private role;

an unrelated storage account, unrelated VNet IP, andaj-gpt56-25-943b-southeastasia;

literal-IP, alternate-DNS, host-header, endpoint-override, and direct-publicendpoint bypasses;

every forbidden cross-lane read/write and role substitution.

Receipts may contain closed test IDs, PASS/FAIL, hashes, resource/run IDs,durations, counts, GPU seconds, and cost only. They must not contain raw URLs,private object names, prompt/response text, case fragments, values, spans,labels, exception payloads, or environment dumps.

Run a separate remote security/runtime audit against the exact final deployedrevision. Any successful negative canary, unknown/NOT_ASSESSABLE condition, orunresolved BLOCKER/MAJOR keeps the stateBLOCKED_ON_PRIVATE_REVIEW_BOUNDARY.

7. Conditional Work packages 3–4 — private set construction and sealing

Continue automatically only when all of these are mechanically true:

prospective public freeze is pushed and remotely verified;

protected bytes and FINAL policy semantics are unchanged;

both pre-private public audits have no unresolved BLOCKER/MAJOR and theirfinal remediations were re-reviewed;

the exact production boundary passes every positive/negative probe;

model selection, images, identities, lanes, retry rules, and schemas arefrozen;

all semantic/scoring/parser/prediction counters remain zero.

7.1 Authoritative private access and state transition

Authenticate the exact authoritative retired-v1 source in:

subscription: 943bacdf-8b6e-4e3a-8126-a149f623d32e
resource group: rg-jspace-observation-sea
storage account: stjspacefiles0709085305
container: jspace-results
prefix: phase1-evaluator-validation/parser-v3-v1/20260725T160340Z
expected objects: 12

Reverify the registered byte-only receipt before semantic reading. Use only thesource-custodian identity and exact prefix. Append the access event beforedecoding. The first authorized semantic repair read changes current v1 stateto the repository's registered equivalent of:

SEALED / REPAIR_ACCESSED / NEVER_FORMALLY_SCORED /
UNSCORABLE / RETIRED_AS_INELIGIBLE

Preserve the historical UNSPENT record as historical truth; do not continueusing it as current truth after semantic access. Retired-v1 bytes, namespace,manifest, and historical invalid contract remain unchanged. Formal scoring,predictions, and parser runs against v1 remain zero.

7.2 Construct exactly one eligible 120-case v2 set

Execute the frozen production construction entrypoints—not a notebook, ad hocscript, or simplified copy. Preserve the registered rules inparser_v3_v2_construction.py:

the historical 105 repairable / 15 residual split is diagnostic only andnever a target;

every proposed final case receives blinded reviewer A and reviewer B review;

old/migrated labels, reuse status, parser behavior, and the other review arehidden from each reviewer;

disagreements alone reach the isolated arbiter under the frozen disclosurerule;

unresolved or ineligible cases are quarantined and replaced within thefrozen bounded batch limit;

selection is order-independent and uses the registered content-hash tie-break;

all four registered collision rules execute on actual candidate bytes;

parser behavior never influences eligibility, repair, replacement, orselection.

Final facts must be derived from private bytes and satisfy all registeredinvariants, including:

120 unique eligible adjudicable mandatory cases
S01..S12 = exactly 10 each
present / no_answer / ambiguous = 80 / 30 / 10
pinned coverage = 80
residual exact-conformance coverage = 40
unresolved decisions = 0
ineligible sealed cases = 0
prohibited collisions = 0

Derive every subtype and lane-specific requirement from the FINAL policy andstratum matrix; do not rely on this summary if the canonical machine record ismore specific. S06 and S11 special requirements remain binding. Complete allregistered overlap checks against public development corpora and the retiredparser-v2 holdout using isolated custodians or authenticated non-contentfingerprints. Private case/review content stays in Azure.

If the frozen batch limit cannot fill every slot, terminateBLOCKED_ON_SET_REPAIR. Do not loosen a quota, relabel a case, extend thebatch, or inspect parser behavior.

7.3 Independent private audits and create-only sealing

Run two private audits inside the qualified boundary:

all 120 cases, provenance, admission, adjudicability, blind reviews,arbitration, replacement, quotas, ontology, and collisions;

parser isolation, lane containment, facts derivation, deterministiccompilation, seal layout, create-only lifecycle, and listing-witnessprovenance.

Private auditors may write private findings only to their assigned lanes. Gitreceives aggregate counts/hashes and closed dispositions. An already-frozenrule may quarantine and replace a rejected case through the same bounded path,followed by affected re-review and re-audit. A finding that requires a frozenrule/executable change terminates BLOCKED_ON_PROTOCOL_INTEGRITY.

Use the acyclic create-only sequence:

final set bytes + derived facts + planned members
  -> terminal sealed-set manifest
  -> authenticated actual Azure listing witness
  -> one-time final contract binding manifest and witness
  -> public content-free seal receipt

Requirements:

allocate one never-used v2 identity/prefix;

prove all target members, terminal manifest, external witness, and finalcontract paths do not exist;

upload members create-only and the terminal manifest last;

never overwrite, resume, rename, patch, or delete a terminal identity;

list using the exact seal-custodian identity;

re-download and verify every member by size, SHA-256, ETag, schema, and theregistered stronger checks;

create the listing witness from the real authenticated listing and persistit create-only outside sealed membership;

compile the final contract exactly once outside sealed membership, bindingthe manifest and listing-witness hashes;

regenerate only to a temporary path and require byte equality withoutoverwriting the final contract;

publish only the approved content-free receipt.

After successful sealing, stop at SEALED_READY_FOR_PREREGISTRATION. Do notpreregister, run Stage P, create a prediction namespace, open scoring labels,or run Stage E in this round.

8. Azure-only validation and required controls

Use the existing Basic build ACR for public validation. Source binding mustinclude exact commit and tree. Because earlier ACR source contexts stripped.git/.gitignore, use an Azure-side exact Git clone or the repository'salready validated bundle/source-manifest method. Do not weaken Git-aware teststo accommodate a damaged build context.

Run, at minimum, entirely in Azure:

the exact 6faa1045... baseline and the final Phase A candidate;

full suite and every focused lifecycle/construction/evaluation/schema/entrypoint/IaC/boundary suite;

public synthetic end-to-end rehearsal through production entrypoints;

compile/static/type/lint checks already established by the repo;

JSON Schema and deterministic-generator checks;

Bicep build, lint, what-if, parameter validation, and deployed drift/read-back;

protected raw-byte and policy semantic-hash checks;

dependency-lock installation from scratch;

source-tree and image-payload manifests;

secret, private-path/content, diagnostic, and large-file scans;

call-graph/runtime-command binding and parser-isolation checks;

effective RBAC, storage-lane, DNS, PE, firewall, UDR, NSG, and canary checks;

remote set/facts/manifest/witness/contract deterministic regeneration;

git diff --check, changed-file allowlist, and final diff review.

Required mutation controls include:

schema accepted by tests but not invoked by the live entrypoint;

configured command calling a safe dead function while a different functionexecutes;

role/UAMI/container/prefix substitution and ambient-credential fallback;

public endpoint or direct-IP bypass;

firewall/route/NSG shadowing and unexpected rule priority;

model/tokenizer/weight/config revision substitution;

reviewer cross-talk, old-label leakage, reuse disclosure, and parser-proxyselection;

order-dependent selection and every collision-rule regression;

ineligible sealed-case skip or denominator shrink;

unbounded replacement and post-observation rule change;

partial/resumed/overwritten seal, manifest-first write, fabricated listingwitness, circular contract binding, and second final-contract creation;

parser import/call in construction or Stage E, label access in Stage P, andordinal reset/second launch—even though formal evaluation is not run here.

Every rejection needs a valid positive control. Do not weaken, remove, skip,rename away, or xfail an existing test. Report every substantive Azurefailure, diagnosis, fix, and rerun, not only the last green result.

9. Commit, push, and freeze sequence

Use honest, non-force, non-amended commits on main while it remains a cleanfast-forward lineage.

Fast-forward push the existing 13 commits ending at 6faa1045....

Commit/push the Phase A completion candidate: schemas, role entrypoints,Bicep, validation, and audit tooling.

Commit/push bounded audit remediations and the prospective public freeze.

Deploy/qualify Phase B from that exact freeze; commit/push only public,content-free infrastructure/read-back/audit receipts.

After conditional private construction and sealing, commit/push thecontent-free set/seal/current-state receipts.

The prospective freeze must be remote before the first private semantic read.Fetch before every push and verify no divergence. Never force-push, amend apublished freeze, reset, rewrite, discard remote/user work, or use a PR as asubstitute. Final report claims about a commit are valid only afterorigin/main is read back and equals it.

10. Azure resource and scientific ledgers

Append events; never reset or rewrite history. Separate control-plane,byte-only, semantic-repair, construction, sealing, prediction, scoring, andformal-evaluation events.

Report actual counts for:

Azure resources created/changed/deleted and role assignments;

ACR builds/tests, CPU jobs, GPU jobs, model calls, tokens, GPU-seconds,build minutes, estimated cost, and retained monthly cost;

positive/negative network probes;

Blob reads/writes per synthetic/private lane;

retired-v1 byte-only and semantic repair reads;

reviewer A/B, arbitration, replacement, and private-audit operations;

v2 candidates, quarantines, replacements, admitted cases, facts, manifests,listing witnesses, contracts, and seals;

parser invocations, predictions, labels opened for scoring, comparator runs,formal evaluations, and evaluation ordinal.

At successful end of this round the last five counters remain exactly zero.Do not call repair access scoring, and do not call byte hashing semantic review.

11. Safe cleanup and retained Azure state

Stop executions and scale all idle CPU/GPU workloads to zero. Remove only exactephemeral staging identities/assignments, mutable tags, failed orphan jobs, andtemporary model-download paths that the frozen evidence no longer requires.Retain the private VNet/firewall/PE/DNS/runtime ACR, frozen images/model weights,role identities needed for preregistration/evaluation, sealed v2 set, listingwitness, final contract, and immutable evidence. Never delete or alter retiredv1 or sealed v2.

Then perform §2.2 local cleanup only after remote Git verification. Report exactremoved paths and retained categories without printing protected private-prefixmembers.

12. Valid blocked states

Use only the most specific truthful state:

BLOCKED_ON_GIT_DIVERGENCE

BLOCKED_ON_GIT_CREDENTIAL

BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE

BLOCKED_ON_MODEL_AVAILABILITY_OR_QUOTA

BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY

BLOCKED_ON_PRIVATE_SOURCE_ACCESS

BLOCKED_ON_INDEPENDENCE

BLOCKED_ON_SET_REPAIR

BLOCKED_ON_SEALING

BLOCKED_ON_PROTOCOL_INTEGRITY

Budget, T4 cost, Azure Firewall cost, or expected calendar duration is not ablocked state. A control-plane resource existing is not evidence that its gatepassed. If no scientific/technical blocker has occurred and only the sessionmust end, use the nonterminal checkpoint form defined in §1.

13. Final report

Return no private case content. Include:

exact terminal or nonterminal checkpoint state;

remote starting SHA and recovered 13-commit chain/final remote SHA;

proof that GitHub was used only as Git transport/repository tree;

Phase A candidate/freeze SHAs and trees;

protected count/digests and policy full-file/semantic hashes before/after;

schema, entrypoint, lock, IaC, image, and synthetic-rehearsal hashes/results;

every public audit finding, remediation, residual, and final re-review;

all Azure validation run IDs and baseline/candidate/final test counts;

all created/changed/deleted/retained Azure resources and tags;

build versus runtime ACR separation and private runtime image digests;

VNet/subnets/DNS/PE/firewall/UDR/NSG read-back and configuration hashes;

positive and negative runtime canary results;

model family/revision/license/weight/tokenizer/runtime hashes, quota,qualification, GPU-seconds, tokens, and costs;

exact role/UAMI/RBAC/lane matrix and cross-lane denial results;

first private semantic-access event and honest retired-v1 current state;

expected versus actual repair/quarantine/replacement aggregates;

120-case strata/subtype/ontology/coverage/adjudicability aggregates;

A/B agreement, arbitration, unresolved, provenance, and private-audit counts;

collision/overlap aggregate results;

set facts, manifest, listing witness, final contract, remote-member count,and byte-verification verdict;

confirmation that parser runs, predictions, scoring-label access,comparator runs, formal evaluations, and ordinal all remain zero;

exact local work performed, exact cleanup, and confirmation that no localtests/imports/builds/scans/private reads ran;

limitations and the smallest exact next gate.

If successful, the exact next gate is:

Post-seal preregistration and independent single-launch readiness audit forthe already sealed parser-v3-v2 set, followed—only if every immutablebinding passes—by Stage P prediction sealing and the one formal Stage Eevaluation. No construction or label repair is permitted after this seal.

14. Official references to re-check at execution time

Use current English Microsoft/GitHub primary documentation and record retrievaldates. At minimum re-check:

ACR SKU/private-link support and in-place SKU behavior:https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus

ACR private endpoints and the az acr build public-access limitation:https://learn.microsoft.com/en-us/azure/container-registry/container-registry-private-endpoints

ACR dedicated task agent-pool regional limitations:https://learn.microsoft.com/en-us/azure/container-registry/tasks-agent-pools

Container Apps networking and firewall/UDR controls:https://learn.microsoft.com/en-us/azure/container-apps/networkinghttps://learn.microsoft.com/en-us/azure/container-apps/firewall-integrationhttps://learn.microsoft.com/en-us/azure/container-apps/user-defined-routes

workload-profile discovery and serverless GPU support:https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-manage-clihttps://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview

GitHub HTTPS credential management and multiple accounts:https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-githttps://docs.github.com/en/account-and-profile/how-tos/account-management/managing-multiple-accounts

Documentation proves supported mechanisms. Only live Azure/Git read-back,content-addressed bindings, production-entrypoint execution, and runtimepositive/negative probes prove this project's actual stat