# Study 4F-E1-Q1 invocation disclosure

Authority: `studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md`
Q1 authority commit: `8a9bb7617fcc6507aba86c4359042b5e90818ce4`
Predecessor: Study 4F-E1 at `1900aa374bf000353580b042b275a730bbad6b1f`

Exact lifecycle state for this invocation:

```
STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION
```

**No scientific result.** Azure GPU capacity remains unknown. No checkpoint
competence was tested. No RP-B candidate was identified. Nothing was established
about J-space.

---

## 1. Starting and final identity

| Item | Value |
| --- | --- |
| Starting commit | `1900aa374bf000353580b042b275a730bbad6b1f` |
| Starting tree | `a0b5d7304b6d08e55c45f927b048af01ad409126` |
| Q1 authority commit | `8a9bb7617fcc6507aba86c4359042b5e90818ce4` |
| Q1 authority tree | `f7693e3aee94ff41d1b1879b1837fa78c915cf87` |
| Q1 evidence commit | `4308e6f0359e1fc84b49354253681348f4a6c3ba` |
| Ancestry | strictly linear, merge-free, fast-forward only |

The §0 binding starting state was verified before anything was written:
`origin/main` at the registered commit, a clean worktree, zero merge commits in
the entire history, E1 lifecycle state
`STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`, the failed self-service request
`a6817961-e0f7-4cbe-a1ef-7ac4104e1089` with `QuotaNotAvailableForResource`, an
H100 family limit of zero, zero Azure resources, zero deployments, zero
accelerators, zero banks, zero seals, zero weights, zero model calls and zero
executed cells, and `paper/evidence_ledger.csv` ending at `EV-0016`.

All three authoritative predecessor artifacts were verified present and
byte-unchanged: `studies/study4f/execution-e1/STATUS.json`,
`studies/study4f/execution-e1/azure/operator_quota_request_packet.md` and
`studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md`.

## 2. Authority: newly published, not reused

The Q1 authority did **not** already exist at the starting head
(`git ls-files studies/study4f/prompts/` listed only the two earlier
authorities), so §1's first branch applied.

| Item | Value |
| --- | --- |
| Path | `studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md` |
| Byte length | 11,316 |
| SHA-256 | `ce61fd32c6546e1e98bb79d4220651fa855bca05fe2d39bf88c1089bb2cf8975` |
| Git blob | `6622504c13e479d32dfaf4002b80250616a0a1a9` |
| Parent commit | `1900aa374bf000353580b042b275a730bbad6b1f` |
| Parent tree | `a0b5d7304b6d08e55c45f927b048af01ad409126` |
| Commit | `8a9bb7617fcc6507aba86c4359042b5e90818ce4` |
| Tree | `f7693e3aee94ff41d1b1879b1837fa78c915cf87` |

It was saved byte-for-byte and committed **alone**: `git show --name-only` for
that commit lists exactly one path, and
`git ls-tree -r 8a9bb761 studies/study4f/execution-e1/quota-escalation-q1` is
empty, so no Q1 artifact and no support ticket predates it.

## 3. Quota: still zero

A read-only re-check was performed before anything else, using the already
configured Azure CLI identity.

| Metric | Value |
| --- | --- |
| `StandardNCadsH100v5Family` limit, `australiaeast` | `0` |
| `StandardNCADSA100v4Family` limit, `australiaeast` | `0` |
| Total regional `cores` | `0` used of `100` |
| Qualifying quota visible | **no** |

§2.1 therefore did not apply: quota was not already granted, so the invocation
did not skip to §6.

## 4. Support ticket: none existed, exactly one was created

`GET Microsoft.Support/supportTickets` returned an empty list, so §2.2 did not
apply and §2.3 routed to §3. Programmatic creation was authorized, so §4.1
applied and no manual portal submission was required.

| Field | Value |
| --- | --- |
| Ticket ID, salted SHA-256 | `3115437c07487a4b825eaa7b5017b570db8e38da9cd88824cc88cf8147f84021` |
| Ticket ID, final four | `3753` |
| Salt material | `STUDY4F_E1_Q1|<q1 authority commit>|<support ticket id>` |
| Resource name | `study4f-e1-q1-h100-australiaeast` |
| Created | `2026-08-18T06:25:01Z` |
| Status | `Open` |
| Severity | `Minimal` |
| Support SLA | 480 minutes, expiring `2026-08-19T05:26:00Z` |
| Issue type | Service and subscription limits (quotas) |
| Quota type | Compute-VM (cores-vCPUs) subscription limit increases |
| Subscription | ends `d32e`; full ID not committed |
| Region | `australiaeast` |
| VM family | Standard NCadsH100v5 Family vCPUs |
| Requested new limit | `40` |
| Requested instances | exactly `1` |
| Target SKU | `Standard_NC40ads_H100_v5` |
| Capacity type | standard on-demand, not Spot |

**Azure's response so far is an acknowledgement, not a decision.** Microsoft
Support confirmed receipt, restated the request (Australia East,
`standardNCadsH100v5Family`, new limit 40) and stated a two-business-day review
window. That is recorded as `azure_acknowledgement.kind =
receipt_acknowledgement_only` with `is_an_approval`, `is_a_denial` and
`grants_quota` all false. It grants no quota and moves no gate.

## 5. What was deliberately not done

* **No second `Microsoft.Quota/quotas` PUT.** The self-service path was
  exhausted under the E1 authority and §3 forbids retrying it.
* **No duplicate ticket.** Existing tickets were enumerated first.
* **No enlarged request.** Not more than 40 H100-family vCPUs, not multiple
  instances, not Spot quota, not another GPU family in the same ticket, not
  multiple regions simultaneously.
* **No A100 fallback.** §4.3 authorizes it only after Azure explicitly
  determines that H100 cannot be enabled in any eligible region, and it may
  never coexist with an unresolved H100 request. The H100 request is unresolved,
  so the fallback is neither authorized nor submitted.
* **No RBAC bypass** and no reuse of credentials outside their configured
  purpose.
* **No polling loop** and no session held open awaiting a decision.

## 6. Azure resource counters

| Item | Count |
| --- | --- |
| Resource groups created | 0 |
| VMs provisioned | 0 |
| Deployment attempts | 0 |
| Checkpoint downloads | 0 |
| Model calls | 0 |
| Executed cells | 0 |
| Billable accelerators remaining | 0 |
| Resources remaining | 0 |

Nothing was provisioned, so §8 cleanup is not applicable and there is nothing to
deallocate or delete.

## 7. E1 execution reachability

E1 execution did **not** become reachable and no conditional resumption was
entered. §5 defines approval as *visible* quota — an H100 family limit of at
least 40 in the approved region, or, after a registered H100 denial and A100
fallback approval, an A100 family limit of at least 24 in its approved region.
The ARM API reports `0`.

An approval message without visible quota is explicitly not sufficient, and this
invocation treats the acknowledgement accordingly.

The remaining shakedown allowance is carried forward unconsumed: two attempts
and six accelerator-hours.

## 8. Test differential

| Item | Value |
| --- | --- |
| Registered starting baseline | `9 failed, 5,119 passed, 16 skipped` |
| Suite at this head | `9 failed, 5,119 passed, 16 skipped` |
| Failure node IDs | identical to the starting nine |
| New non-scope failures | 0 |
| Historical failures edited or suppressed | 0 |
| Q1 tests | 76 passed |
| Study 4F tests | passed |
| E1 tests | 121 passed, 1 failed — the recorded scope expiry below |

### The one recorded scope expiry

`studies/study4f/execution-e1/tests/test_study4f_e1_qualifying_accelerator_execution.py::test_the_successor_added_paths_only_inside_its_own_namespace`
expired. It is **recorded, not repaired and not suppressed**, and §7's five
conditions are proved mechanically by
`...::test_the_one_new_scope_expiry_is_mechanically_scope_only`:

1. **the module is byte-identical** to the predecessor head, verified by
   comparing `git rev-parse 1900aa3:<module>` with `git rev-parse HEAD:<module>`;
2. **it is solely a scope predicate** over `git diff --name-status <commit> HEAD`
   — the assertion body contains no hash, no quota value, no counter and no
   lifecycle claim;
3. **no substantive protected byte moved** — the diff since the E1 head is
   purely additive, every added path is either inside
   `studies/study4f/execution-e1/quota-escalation-q1/` or is the Q1 authority,
   and the single path outside the E1 namespace is exactly that authority;
4. **the guarantee is carried forward** by
   `...::test_q1_added_paths_only_inside_its_own_namespace_and_the_authority`
   and `...::test_no_predecessor_byte_moved`;
5. **there are zero new non-scope failures.**

It is unavoidable. The assertion admits only paths under
`studies/study4f/execution-e1/` plus the E1 authority; §1 of the Q1 authority
fixes the Q1 authority path at `studies/study4f/prompts/…` — outside that set —
while also forbidding any modification to an existing Study 4F-E1 byte. No
publication of Q1 leaves the assertion passing and no repair avoids changing a
protected byte.

It sits **outside the registered repository baseline**: `pyproject.toml` sets
`testpaths = ["tests"]`, and the module lives under `studies/`. The nine standing
repository failure node IDs are therefore unchanged, which the full-suite run at
this head confirms.

## 9. Evidence ledger

`paper/evidence_ledger.csv` is byte-unchanged and still ends at `EV-0016`. This
invocation wrote zero rows.

## 10. Claim ceiling

This invocation opened a support case. That is an administrative act, not a
measurement.

It establishes only that the self-service quota path was not retried, that
exactly one correctly parameterised support request exists, and that the H100
family quota was still zero at the time of this record.

It establishes nothing about whether Azure will approve the request, nothing
about Azure GPU capacity, nothing about the capability of any registered
checkpoint, nothing about whether a natural positive-reference candidate exists,
and nothing about the existence, non-existence, observability or unobservability
of J-space. No RP-B was identified and none was confirmed. Nothing authorizes
confirmation, D0, activation capture, patching or Study 3M.
