# Study 4F-E1-Q1R ticket reconciliation and routing disclosure

Authority: `studies/study4f/prompts/study4f_e1_q1_ticket_identity_reconciliation_and_global_routing_authority.md`

Final registered lifecycle state:

```
STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION
```

**No scientific result.** No model cell executed, physical Azure GPU capacity was not tested, and nothing in this invocation establishes anything about the existence, non-existence, observability or unobservability of J-space.

---

## 1. Repository and publication identity

| Item | Value |
| --- | --- |
| Starting commit | `01c07d83e8be3dd9ba2bebb31869af944ae2a21b` |
| Starting tree | `cca35c2178bd1c2b8688468a888eab8cd9d5b2ed` |
| Starting condition | clean; `HEAD == origin/main`; merge-free |
| Q1R authority commit | `6e38543a68acffc4014fda7beff79d675a51d44a` |
| Q1R authority tree | `328d2c281dfd87f9cbae71c4ee0838a0c0b85e2a` |
| Q1R evidence commit | `8e07901efc20dc4553e1848c6fb957e16c76b9be` |
| Q1R evidence tree | `862cd0a49fa2de43077cb2d91d97c039ac16914d` |
| Final disclosure commit/tree | reported by the terminal result after this file is published, avoiding a circular self-hash |

The authority is 8,544 bytes, SHA-256 `b395c91d3db0e48134e8cf4c9546bdfc7f35dfd6e440ea22e3d986cca354cc17`, Git blob `fb0ad4691b44e94fbe7694fd8dd0b65535b9d7a4`. It was committed alone as the first child of the verified starting head and pushed before any Azure read.

The original Q1 authority, receipt, disclosure and status retain their starting Git blobs and SHA-256 hashes. The historical `3753` suffix therefore remains visible as protected historical evidence; no old byte was corrected in place.

## 2. Ticket identity reconciliation

| Field | Result |
| --- | --- |
| Classification | `Q1_REGISTERED_REDACTED_TICKET_IDENTITY_TRANSCRIPTION_ERROR_CONFIRMED` |
| Mismatch type | suffix transcription only |
| Wrong API field comparison | no |
| Governing customer identity field | `properties.supportTicketId` |
| Separate ARM resource identity field | `name` |
| Corrected customer-facing suffix | `1753` |
| Historical incorrect suffix | `3753` |
| Customer-facing ID salted SHA-256 | `91638bfadf1b15b017bcdc7fd84488b1bc817ac5d4179d03cd781770912c73a5` |
| ARM resource-name salted SHA-256 | `4a8a1e91733a04f30c23d7097bcf40a22e666c93396eef6474073ac279a737f6` |
| Full customer-facing ID committed by Q1R | no |
| Full ARM resource name committed by Q1R | no |

The complete in-memory tuple matched: customer-facing identifier, suffix, creation time `2026-08-18T06:25:01Z`, Australia East, NCadsH100v5 family, requested limit 40, quota-request classification, title/service and the existing salted subscription binding. The historical salted hash matches the customer-facing identifier and does not match the ARM resource name, mechanically distinguishing a transcription error from field confusion.

## 3. Support and current quota observation

| Observation | Value |
| --- | --- |
| Support ticket GETs | 1, read-only, no retry |
| Live API ticket status | `Open` |
| Correspondence classification | `BACKLOG_PENDING_NO_APPROVAL_NO_FINAL_DENIAL` |
| Approval / quota grant / final denial | false / false / false |
| Request remains pending | true |
| Additional information required | false |
| Australia East H100 quota queries | 1 |
| `StandardNCadsH100v5Family` usage / limit | `0 / 0` vCPUs |
| Required visible family limit | `40` vCPUs |
| Total regional vCPU usage / limit | `0 / 100` |
| H100 execution authorized | no |
| A100 fallback authorized | no |
| Duplicate ticket authorized | no |

Backlog/pending is neither approval nor final denial. The quota gate remains unsatisfied because the authoritative family limit is zero.

## 4. Read-only Global Azure routing survey

The survey enumerated 63 subscription-visible physical regions and classified 126 region/SKU pairs. It performed one location query, two target-SKU queries, reused the single Australia East H100 observation, made 28 additional regional usage reads and one Australia East A100-specific quota read. There were no retries or polling loops.

| Route | R0 | R1 | R2 | R3 |
| --- | ---: | ---: | ---: | ---: |
| H100 | 0 | 23 | 0 | 40 |
| A100 | 0 | 14 | 10 | 39 |

Classification legend: `R0` quota already sufficient; `R1` SKU allowed but quota insufficient; `R2` `NotAvailableForSubscription`; `R3` not offered or unresolvable. Physical capacity is `UNKNOWN_NOT_TESTED` for every row.

| Region | H100 | H100 deficit family / regional | A100 | A100 deficit family / regional | Capacity |
| --- | --- | ---: | --- | ---: | --- |
| `australiacentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `australiacentral2` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `australiaeast` | `R1` | 40 / 0 | `R2` | — / 0 | `UNKNOWN_NOT_TESTED` |
| `australiasoutheast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `austriaeast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `belgiumcentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `brazilsouth` | `R3` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `brazilsoutheast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `canadacentral` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `canadaeast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `centralindia` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `centralus` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `centraluseuap` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `chilecentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `denmarkeast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `eastasia` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `eastus` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `eastus2` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `eastus2euap` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `eastusstg` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `francecentral` | `R3` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `francesouth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `germanynorth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `germanywestcentral` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `indiasouthcentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `indonesiacentral` | `R1` | 40 / 0 | `R3` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `israelcentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `italynorth` | `R3` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `japaneast` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `japanwest` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `jioindiacentral` | `R3` | — / — | `R2` | — / — | `UNKNOWN_NOT_TESTED` |
| `jioindiawest` | `R1` | 40 / 0 | `R3` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `koreacentral` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `koreasouth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `malaysiawest` | `R1` | 40 / 0 | `R3` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `mexicocentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `newzealandnorth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `northcentralus` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `northeurope` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `norwayeast` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `norwaywest` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `polandcentral` | `R3` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `qatarcentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `southafricanorth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `southafricawest` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `southcentralus` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `southcentralusstg` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `southeastasia` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `southindia` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `spaincentral` | `R1` | 40 / 0 | `R3` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `swedencentral` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `switzerlandnorth` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `switzerlandwest` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `uaecentral` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `uaenorth` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `uksouth` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `ukwest` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `westcentralus` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `westeurope` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `westindia` | `R3` | — / — | `R3` | — / — | `UNKNOWN_NOT_TESTED` |
| `westus` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `westus2` | `R1` | 40 / 0 | `R2` | 24 / 0 | `UNKNOWN_NOT_TESTED` |
| `westus3` | `R1` | 40 / 0 | `R1` | 24 / 0 | `UNKNOWN_NOT_TESTED` |

### Top five rankings

Ranking is by class R0–R3, then smallest family deficit, smallest regional deficit, then region name.

| Rank | H100 region / class / deficits | A100 region / class / deficits |
| ---: | --- | --- |
| 1 | `australiaeast` / `R1` / 40 / 0 | `brazilsouth` / `R1` / 24 / 0 |
| 2 | `canadacentral` / `R1` / 40 / 0 | `canadacentral` / `R1` / 24 / 0 |
| 3 | `centralindia` / `R1` / 40 / 0 | `centralus` / `R1` / 24 / 0 |
| 4 | `centralus` / `R1` / 40 / 0 | `eastus2` / `R1` / 24 / 0 |
| 5 | `eastus` / `R1` / 40 / 0 | `francecentral` / `R1` / 24 / 0 |

No R0 route exists. The single future H100 quota candidate is `australiaeast`—the already pending route, not authorization for a duplicate request. The single future A100 candidate is `brazilsouth`; it remains inactive and cannot be requested unless the registered final-denial condition and a later operator authorization are both satisfied.

Three read outcomes were explicitly retained rather than retried: the Australia East A100-specific read was unresolved while that route was already subscription-restricted, and regional usage reads for `centraluseuap` and `jioindiacentral` returned HTTP 400. Their affected pairs remain R2 or R3 according to SKU restriction/resolve state; no physical-capacity inference was made.

## 5. Writes, execution counters and allowance

| Counter | Value |
| --- | ---: |
| Git publications | 3 (authority, evidence, this disclosure) |
| Historical Git bytes modified | 0 |
| Azure writes | 0 |
| Quota PUTs | 0 |
| Support creates / updates / communications | 0 / 0 / 0 |
| Resource groups / VMs / disks / NICs / deployments | 0 / 0 / 0 / 0 / 0 |
| Model loads / calls | 0 / 0 |
| Banks / scoring / generations / generated tokens | 0 / 0 / 0 / 0 |
| D0 / activation collections / patches | 0 / 0 / 0 |
| Executed cells / accelerator-hours | 0 / 0 |
| Remaining shakedown allowance | 2 attempts; 6 accelerator-hours |

## 6. Validation and unavoidable scope expiries

* Q1R reconciliation/routing tests: **22 passed**.
* Protected E1 tests: **128 passed, 1 failed**. The sole failure is the already recorded HEAD-relative namespace predicate `test_the_successor_added_paths_only_inside_its_own_namespace`; no new E1 failure node was introduced.
* Protected Q1 tests: **83 passed, 2 failed**. Both failures are HEAD-relative scope predicates caused solely by the separately required Q1R authority path:
  * `test_q1_added_paths_only_inside_its_own_namespace_and_the_authority`;
  * `test_the_one_new_scope_expiry_is_mechanically_scope_only`.
* The protected Q1 module is byte-identical to `01c07d8`. Its assertions were not edited or suppressed; the Q1R tests mechanically carry their preservation and scope guarantees forward.
* These tests live under `studies/` and remain outside the configured default `testpaths = ["tests"]` baseline.

## 7. Final state and next legal action

The exact state remains `STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`. The operator's selected bi-monthly status preference remains a manual Reply All action; this invocation sent no e-mail and performed no support write.

The next execution transition is legal only when Australia East visibly reports at least 40 H100-family vCPUs. A later unambiguous final H100 denial may instead permit only the already registered A100 fallback path, after operator authorization. The routing survey itself authorizes neither a new request nor fallback activation.
