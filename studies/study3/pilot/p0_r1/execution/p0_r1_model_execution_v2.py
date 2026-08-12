"""The Study 3 P0-R1 generation-2 model execution shell. GPU session only.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 8, over ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

Like its generation-1 predecessor, this is the only place in the P0-R1 package
that names a model or tokenizer library, and it lives in its own subpackage so
that the replay path, the scoring contract, the counter ontology and the
eligibility classifier remain importable with no model library present.

Three defects of the generation-1 shell are closed here, and nothing else
changes. The scoring plan construction, the restricted-logit read, the tie
break, the S3 reuse, the exact 60-prefill smoke boundary, the caps and the S4
diagnostic are all the registered generation-1 implementations, imported and
called unchanged.

1. **Counting happens at admission.** Every irreversible operation -- tokenizer
   construction, prompt encode, checkpoint download or load, prefill, generation
   or decode, parser call and scored row -- is journalled and counted *before*
   the call it describes. An interruption can therefore over-report an operation
   that may have started, and can never under-report one that did.

2. **Partial results live outside this stack.** Rows, raw completions,
   exceptions and resource records are appended to the caller's collector as
   they are produced, so an exception here cannot destroy them.

3. **A row-level exception stops the attempt without discarding it.** The
   generation-1 shell re-raised past every artifact write, which lost the run.
   Here the exception is recorded, the attempt stops exactly as before, and the
   caller's boundary writes the conservative counters and every preserved
   partial result.

Nothing in this module executes at import time.
"""

import os
import sys

EXECUTION_DIR = os.path.dirname(os.path.abspath(__file__))
P0_R1_DIR = os.path.abspath(os.path.join(EXECUTION_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

for _path in (P0_R1_DIR,
              os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import p0_r1_model_runner as RUNNER  # noqa: E402
import p0_r1_model_runner_v2 as RUNNER2  # noqa: E402
import p0_r1_summarize as SUMMARIZE  # noqa: E402
from p0_r1_counters import CapExceeded, SMOKE_EXACT  # noqa: E402


class AttemptStopped(Exception):
    """A recorded scientific stop. The caller preserves everything observed."""


def _load_parser():
    """The pinned deterministic S4 parser. ``unparseable`` stays first class."""
    import p0_parser
    return p0_parser


def execute(authorized, counters, partial, journal, out_dir=None, root=None,
            device=None, corpus_rows=None, identities=None):
    """Run the bounded P0-R1 model pilot. Never called without authorization.

    Returns the terminal state. Raises only to hand a stop to the caller's
    exception boundary, which has already been installed and which owns
    ``partial``.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    lock = authorized["lock"]
    parser = _load_parser()

    token = journal.admit("checkpoint_download_or_load", detail={
        "phase": "runtime_probe"})
    if device is None:
        if not torch.cuda.is_available():
            journal.failed(token, RUNNER.ExecutionRefused("no CUDA device"))
            raise RUNNER.ExecutionRefused(
                "the P0-R1 model pilot runs in one Azure containerized GPU job; "
                "no CUDA device is visible")
        device = "cuda"
    journal.complete(token, outcome={"device": str(device)})

    residency = RUNNER.GpuResidency(counters)
    boundary = RUNNER.SmokeBoundary(counters)

    tokenizers = {}
    for role in sorted(lock["roles"]):
        identity = lock["roles"][role]
        handle = "%s@%s" % (identity["repository"], identity["revision"])
        admission = journal.admit(
            "tokenizer_construction",
            counter_updates={"tokenizer_construction_events": 1},
            identity_updates={
                "distinct_tokenizer_identities_constructed": handle},
            detail={"role": role, "identity": handle})
        tokenizers[role] = AutoTokenizer.from_pretrained(
            identity["repository"], revision=identity["revision"],
            trust_remote_code=False)
        journal.complete(admission, outcome={"role": role})

    def loader_for(role):
        identity = lock["roles"][role]
        handle = "%s@%s" % (identity["repository"], identity["revision"])

        def _load():
            admission = journal.admit(
                "checkpoint_download_or_load",
                identity_updates={
                    "distinct_checkpoint_identities_downloaded": handle},
                detail={"role": role, "identity": handle})
            model = AutoModelForCausalLM.from_pretrained(
                identity["repository"], revision=identity["revision"],
                torch_dtype=torch.float16, trust_remote_code=False)
            model.eval()
            journal.complete(admission, outcome={"role": role})
            return model

        return _load

    corpus = (corpus_rows if corpus_rows is not None
              else RUNNER.load_corpus(root=root))
    plan = RUNNER.build_execution_plan(corpus, sorted(lock["roles"]), root=root)

    def _prefill(model, token_ids, role, row_id, phase):
        admission = journal.admit(
            "prefill", counter_updates={"runtime_batched_forward_calls": 1},
            detail={"role": role, "row_id": row_id, "phase": phase})
        tensor = torch.tensor([token_ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            output = model(tensor)
        journal.complete(admission, outcome={"row_id": row_id})
        return output.logits[0, -1, :]

    def _restricted(logits, token_ids):
        return {int(token): float(logits[int(token)].item())
                for token in token_ids}

    def _generate(model, tokenizer, prompt_ids, role, row_id):
        admission = journal.admit(
            "generation_or_decode",
            counter_updates={"s4_generation_calls": 1,
                             "s4_prefill_evaluations": 1},
            detail={"role": role, "row_id": row_id})
        tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            output = model.generate(
                tensor, do_sample=False, max_new_tokens=4,
                pad_token_id=tokenizer.eos_token_id)
        produced = [int(token) for token in output[0][len(prompt_ids):]]
        counters.add("generated_tokens", len(produced))
        counters.add("s4_incremental_decode_evaluations",
                     max(0, len(produced) - 1))
        journal.complete(admission, outcome={"generated_tokens": len(produced)})

        text = tokenizer.decode(produced, skip_special_tokens=True)
        parse_admission = journal.admit(
            "parser_call", counter_updates={"parser_calls": 1},
            detail={"role": role, "row_id": row_id})
        parsed = parser.parse(text)
        journal.complete(parse_admission, outcome={"unparseable": parsed is None})

        row_admission = journal.admit(
            "scored_row", counter_updates={"s4_scored_generation_rows": 1,
                                           "total_scored_rows": 1},
            detail={"role": role, "row_id": row_id, "profile": "S4"})
        record = {
            "raw_completion": text,
            "generated_token_ids": produced,
            "generated_token_count": len(produced),
            "parser_result": parsed,
            "unparseable": parsed is None,
            "scored_row": {
                "schema_version": RUNNER.SCHEMA_VERSION,
                "profile": "S4",
                "diagnostic_only": True,
                "raw_completion": text,
                "parser_result": parsed,
                "unparseable": parsed is None,
            },
        }
        journal.complete(row_admission, outcome={"row_id": row_id})
        return record

    def _execute_slice(role, phase, rows):
        model = residency.to_gpu(role, device)
        tokenizer = tokenizers[role]
        for entry in rows:
            try:
                encode = journal.admit(
                    "prompt_encode",
                    counter_updates={"tokenizer_encoded_sequences": 1,
                                     "runtime_batched_tokenizer_calls": 1},
                    detail={"role": role, "row_id": entry["row_id"],
                            "phase": phase})
                prompt_ids = tokenizer(
                    entry["prompt"], add_special_tokens=False)["input_ids"]
                journal.complete(encode, outcome={"tokens": len(prompt_ids)})

                if entry["profile"] == "S4":
                    boundary.admit("s4")
                    generated = _generate(model, tokenizer, prompt_ids, role,
                                          entry["row_id"])
                    partial.s4_completions.append(generated)
                    partial.scored_rows.append(generated["scored_row"])
                    continue

                boundary.admit(phase)
                scoring = RUNNER.build_scoring_plan(
                    entry["profile"], role, entry["row_id"], prompt_ids,
                    entry["candidate_token_ids"], entry["candidate_surfaces"],
                    common_prefix_token=entry.get("common_prefix_token"),
                    tie_break_order=entry.get("tie_break_order"))
                RUNNER.validate_scoring_plan(scoring)
                logits = _prefill(model, scoring["scoring_context_token_ids"],
                                  role, entry["row_id"], phase)
                vector = _restricted(logits, scoring["discriminant_token_ids"])

                row_admission = journal.admit(
                    "scored_row", detail={"role": role,
                                          "row_id": entry["row_id"],
                                          "profile": entry["profile"]})
                partial.scored_rows.append(
                    RUNNER.score_from_logits(scoring, vector, counters=counters))
                if entry.get("s3_reuse"):
                    partial.scored_rows.append(
                        RUNNER.reuse_for_s3(scoring, vector, counters=counters))
                journal.complete(row_admission,
                                 outcome={"row_id": entry["row_id"]})
            except (RUNNER.ScoringDefect, CapExceeded) as exc:
                counters.add("exceptions_observed", 1)
                record = {
                    "row_id": entry["row_id"],
                    "role": role,
                    "profile": entry["profile"],
                    "phase": phase,
                    "exception": type(exc).__name__,
                    "detail": str(exc),
                }
                partial.exceptions.append(record)
                journal.record("row_exception", payload=record)
                partial.stop_reason = (
                    "the attempt stopped on %s at row %s; every row observed "
                    "before it is retained exactly as observed"
                    % (type(exc).__name__, entry["row_id"]))
                # The attempt stops, exactly as it did in generation 1. What
                # differs is that nothing observed is thrown away with it.
                raise AttemptStopped(partial.stop_reason)

    for role in sorted(lock["roles"]):
        residency.load(role, loader_for(role))

    stopped = False
    try:
        # 1. the exact 60-prefill K2 smoke, across all three roles.
        for role in sorted(lock["roles"]):
            _execute_slice(role, "smoke", plan["smoke"][role])
        partial.smoke_passed = boundary.close_smoke(
            counters["non_generative_prefill_evaluations"]
            == SMOKE_EXACT["non_generative_prefill_evaluations"]
            and not partial.exceptions)
        partial.smoke_closed = True

        # 2. only on a mechanical smoke pass, the bounded extension and the S4
        #    diagnostic. The boundary object refuses either one otherwise.
        if partial.smoke_passed:
            for role in sorted(lock["roles"]):
                _execute_slice(role, "extension", plan["extension"][role])
            for role in sorted(lock["roles"]):
                _execute_slice(role, "s4", plan["s4"][role])
    except AttemptStopped:
        stopped = True
    finally:
        try:
            residency.evict()
        except Exception as exc:
            journal.record("eviction_exception", payload={
                "exception": type(exc).__name__, "detail": str(exc)})

    snapshot = counters.snapshot()
    partial.resources.append({
        "device": str(device),
        "gpu_resident_checkpoints_at_a_time": 1,
        "checkpoint_moves_between_cpu_and_gpu": residency.moves,
        "model_weight_loads": snapshot["model_weight_loads"],
        "torch_version": torch.__version__,
    })

    if stopped or partial.exceptions:
        return RUNNER2.STATE_STOPPED_WITH_PARTIAL_RESULT
    if not partial.smoke_passed:
        return RUNNER2.STATE_STOPPED_ON_SMOKE
    return RUNNER2.STATE_COMPLETE


def summarize(partial):
    """The registered generation-1 summary, over whatever was observed."""
    return SUMMARIZE.summarize(
        partial.scored_rows, s4_completions=partial.s4_completions,
        exceptions=partial.exceptions)
