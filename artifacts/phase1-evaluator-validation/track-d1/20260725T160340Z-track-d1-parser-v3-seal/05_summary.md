# Summary

Run id: `20260725T160340Z-track-d1-parser-v3-seal`  
Phase: phase-1.2C  
Track: D (`track-d1`)  
Code commit: `661eff7803d33d3be7be516f76eaf8dcb9e50d4f`  
Final state: **SEALED**

## Objective

Execute the one outstanding registered pre-seal cross-check, the new
`parser-v3-v1` locked set against the **retired** `parser-v2-v1` locked
inputs, and seal the holdout if and only if that check passes.

## Scope

* the container job payload that performs the cross-check and the gated seal
* the Azure Container Apps job specification and the minimum temporary grants
* the honest record of what was and was not executed

Out of scope, and not done: any parser-v3 evaluation, any parser-v3
prediction, any scoring, any parser change, any re-opening of the retired
parser-v2 holdout, and any read of parser-v2 labels, scores or the scoring
ledger.

## Provenance

* the new set's identity comes from the committed
  `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json`, which carries
  fingerprints and no case text
* the fingerprint functions are imported from
  `scripts/build_parser_v3_validation_set.py` and are never reimplemented
* the retired source is `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/`, read for diagnosis only

## Execution

* Container Apps job executed; parent prefix `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z`
* objects sealed: 12
* closure record written last: `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/manifests/set_manifest.json`
* every write used `overwrite=false`; size, SHA-256 and ETag verified for all 12 objects
* membership was also verified independently, by listing the sealed
  parent under a separate identity rather than trusting the job's own
  record: 12 objects in the parent, 2 in the sibling runlog
* this pack is built from the two durable Blob artifacts
  `crosscheck_report.json` and `seal_record.json`, not from the
  in-container summary, which was ephemeral and is gone

## Results

* cross-check 1 verdict: **PASS**
* collision counts: exact 0, normalised 0, numeric-normalised 0
* new set records: 120
* retired records compared: 120
* cross-check 2, the parser-v3 public adversarial development set: 0
  collisions on all three fingerprints, already executed locally
* cross-check 3, the 18-record historical audit extract: **VACUOUS**, that
  extract has no output-bearing field, so it cannot collide and must never
  be reported as passed

## Decision

SEALED: the cross-check passed and all twelve objects sealed

## Deviations and errors

* the check moved from the orchestrator VM to a Container Apps job after the
  VM Run Command extension wedged; the VM was later repaired but the
  Container Apps job stays the authoritative path and the VM is a fallback
  transport only
* the cross-check report and the seal record are written to a sibling
  `-runlog` prefix, because the sealed prefix has an exact twelve-object
  membership rule that extra objects would violate
* the first seal attempt aborted on its own `overwrite=false` guard,
  because the recommended dry pass had already written the cross-check
  report under that timestamp. The guard worked; the timestamp was
  rotated and the seal ran once under the new one
* the rotated timestamp reused the identical image digest by retag, so
  the bytes that sealed the set are the bytes that were reviewed
* **the ABAC grants enforced nothing.** The sealing identity already held
  an unconditioned account-scope blob-write role created sixteen days
  earlier, so the two prefix-conditioned grants did not narrow its
  effective permissions. Isolation of the retired label, score and ledger
  material rests on the payload code path, the Track D tests and the
  report's own attestations, not on RBAC. See deviation D13

## Scientific interpretation

This is a gate, not a measurement. A passing cross-check shows only that the
new instrument does not reuse retired holdout text under three registered
fingerprints. It licenses no claim about parser-v3 accuracy. Sealing fixes
the instrument in time; it does not validate anything.

## Limitations

* the sealed labels are an LLM operational consensus, not human ground truth
* zero overlap is proven only against the corpora actually compared
* isolation between set construction and parser-v3 development is procedural
  and hash-audited, not security-enforced, and this round produced a concrete
  instance of that: the temporary ABAC conditions were not the enforcement
  mechanism, the code path and its tests were
* the retired holdout is spent and retired; it was fingerprinted for overlap
  diagnosis only and was neither re-run nor re-scored
* no parser-v3 evaluation was run, no parser-v3 prediction exists, and
  nothing here supports any parser-v3 accuracy claim

## Paper relevance

The seal, plus this record, is what would make a later parser-v3 evaluation a
genuine pre-registered holdout evaluation rather than a retrospective one.
Until the seal exists, no such claim is available.

## Next gate

Teardown is done and measured: both temporary grants deleted, container-scope assignments 0, job reset to the base image with /bin/true, job secrets 0, storage public network access Disabled, single-use image deleted. One expectation was NOT met and is disclosed rather than restated as met: subscription-wide blob roles for the sealing identity are 1, not 0, because of a pre-existing unconditioned account-scope assignment. Next: update the paper ledgers so EV-0007 is sealed and CL-06 records holdout sealed = yes while parser-v3 formal validation stays unsupported, then schedule the one-shot parser-v3 locked evaluation as a separate, later round.
