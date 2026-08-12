"""The Study 3 P0-R1 model execution shell. GPU execution session only.

Authority:
``studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md``
section 6, over ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

This module is deliberately the **only** place in the P0-R1 package that names a
model or tokenizer library, and it deliberately lives in its own subpackage
rather than beside the replay code.

The registration published a static guard asserting that no module in the
top-level P0-R1 directory imports ``torch`` or ``transformers`` or names
``AutoTokenizer``/``AutoModel``, because the replay and registration path
performs zero tokenizer and model operations. That guard is a published node and
is not weakened here. The execution-completion supplement then requires a real
model executor, which must name those APIs. Both hold at once because the
model-free boundary is made structural: the replay gate, the scoring contract,
the counter ontology and the eligibility classifier stay in the top-level package
and remain importable with no model library present, while every byte that can
touch a checkpoint lives here, behind an authorization check that runs first.

Nothing in this module executes at import time. ``execute`` is reached only after
``p0_r1_model_runner.validate_execution_authorization`` has accepted an
unconsumed execution lock together with a byte-valid replay-pass receipt from the
same authorized attempt.
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
import p0_r1_summarize as SUMMARIZE  # noqa: E402
from p0_r1_counters import CapExceeded, SMOKE_EXACT  # noqa: E402


def _load_parser():
    """The pinned deterministic S4 parser. ``unparseable`` stays first class."""
    import p0_parser
    return p0_parser


def execute(authorized, counters, out_dir, root=None, device=None,
            corpus_rows=None):
    """Run the bounded P0-R1 model pilot. Never called without authorization."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    lock = authorized["lock"]
    parser = _load_parser()

    if device is None:
        if not torch.cuda.is_available():
            raise RUNNER.ExecutionRefused(
                "the P0-R1 model pilot runs in one Azure containerized GPU job; "
                "no CUDA device is visible")
        device = "cuda"

    residency = RUNNER.GpuResidency(counters)
    boundary = RUNNER.SmokeBoundary(counters)

    tokenizers = {}
    for role in sorted(lock["roles"]):
        identity = lock["roles"][role]
        counters.add("tokenizer_construction_events", 1)
        tokenizers[role] = AutoTokenizer.from_pretrained(
            identity["repository"], revision=identity["revision"],
            trust_remote_code=False)
        counters.observe_identity(
            "distinct_tokenizer_identities_constructed",
            "%s@%s" % (identity["repository"], identity["revision"]))

    def loader_for(role):
        identity = lock["roles"][role]

        def _load():
            counters.observe_identity(
                "distinct_checkpoint_identities_downloaded",
                "%s@%s" % (identity["repository"], identity["revision"]))
            model = AutoModelForCausalLM.from_pretrained(
                identity["repository"], revision=identity["revision"],
                torch_dtype=torch.float16, trust_remote_code=False)
            model.eval()
            return model

        return _load

    corpus = (corpus_rows if corpus_rows is not None
              else RUNNER.load_corpus(root=root))
    plan = RUNNER.build_execution_plan(corpus, sorted(lock["roles"]), root=root)

    scored_rows = []
    s4_completions = []
    exceptions = []

    def _prefill(model, token_ids):
        tensor = torch.tensor([token_ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            output = model(tensor)
        counters.add("runtime_batched_forward_calls", 1)
        return output.logits[0, -1, :]

    def _restricted(logits, token_ids):
        return {int(token): float(logits[int(token)].item())
                for token in token_ids}

    def _generate(model, tokenizer, prompt_ids):
        counters.add("s4_generation_calls", 1)
        counters.add("s4_prefill_evaluations", 1)
        tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            output = model.generate(
                tensor, do_sample=False, max_new_tokens=4,
                pad_token_id=tokenizer.eos_token_id)
        produced = [int(token) for token in output[0][len(prompt_ids):]]
        counters.add("generated_tokens", len(produced))
        counters.add("s4_incremental_decode_evaluations",
                     max(0, len(produced) - 1))
        counters.add("s4_scored_generation_rows", 1)
        counters.add("total_scored_rows", 1)
        counters.add("parser_calls", 1)
        text = tokenizer.decode(produced, skip_special_tokens=True)
        parsed = parser.parse(text)
        return {
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

    def _execute_slice(role, phase, rows):
        model = residency.to_gpu(role, device)
        tokenizer = tokenizers[role]
        for entry in rows:
            try:
                prompt_ids = tokenizer(
                    entry["prompt"], add_special_tokens=False)["input_ids"]
                counters.add("tokenizer_encoded_sequences", 1)
                counters.add("runtime_batched_tokenizer_calls", 1)
                if entry["profile"] == "S4":
                    boundary.admit("s4")
                    generated = _generate(model, tokenizer, prompt_ids)
                    s4_completions.append(generated)
                    scored_rows.append(generated["scored_row"])
                    continue
                boundary.admit(phase)
                scoring = RUNNER.build_scoring_plan(
                    entry["profile"], role, entry["row_id"], prompt_ids,
                    entry["candidate_token_ids"], entry["candidate_surfaces"],
                    common_prefix_token=entry.get("common_prefix_token"),
                    tie_break_order=entry.get("tie_break_order"))
                RUNNER.validate_scoring_plan(scoring)
                logits = _prefill(model, scoring["scoring_context_token_ids"])
                vector = _restricted(logits, scoring["discriminant_token_ids"])
                scored_rows.append(
                    RUNNER.score_from_logits(scoring, vector, counters=counters))
                if entry.get("s3_reuse"):
                    scored_rows.append(
                        RUNNER.reuse_for_s3(scoring, vector, counters=counters))
            except (RUNNER.ScoringDefect, CapExceeded) as exc:
                counters.add("exceptions_observed", 1)
                exceptions.append({
                    "row_id": entry["row_id"],
                    "role": role,
                    "profile": entry["profile"],
                    "phase": phase,
                    "exception": type(exc).__name__,
                    "detail": str(exc),
                })
                raise

    # All three checkpoints are loaded once, up front. Section 6 permits keeping
    # the non-resident ones in CPU memory precisely so that every role-smoke
    # slice can complete before extension without a second model load.
    for role in sorted(lock["roles"]):
        residency.load(role, loader_for(role))

    # 1. the exact 60-prefill K2 smoke, across all three roles.
    for role in sorted(lock["roles"]):
        _execute_slice(role, "smoke", plan["smoke"][role])
    smoke_passed = boundary.close_smoke(
        counters["non_generative_prefill_evaluations"]
        == SMOKE_EXACT["non_generative_prefill_evaluations"]
        and not exceptions)

    # 2. only on a mechanical smoke pass, the bounded extension and the S4
    #    diagnostic. The boundary object refuses either one otherwise.
    if smoke_passed:
        for role in sorted(lock["roles"]):
            _execute_slice(role, "extension", plan["extension"][role])
        for role in sorted(lock["roles"]):
            _execute_slice(role, "s4", plan["s4"][role])
    residency.evict()

    counters.reconcile_totals()
    snapshot = counters.snapshot()
    resources = [{
        "device": str(device),
        "gpu_resident_checkpoints_at_a_time": 1,
        "checkpoint_moves_between_cpu_and_gpu": residency.moves,
        "model_weight_loads": snapshot["model_weight_loads"],
        "torch_version": torch.__version__,
    }]

    summary = SUMMARIZE.summarize(scored_rows, s4_completions=s4_completions,
                                  exceptions=exceptions)
    state = (RUNNER.STATE_COMPLETE if smoke_passed and not exceptions
             else RUNNER.STATE_STOPPED_ON_SMOKE)
    return RUNNER.write_pilot_artifacts(
        out_dir, state=state, attempt_id=authorized["attempt_id"], lock=lock,
        scored_rows=scored_rows, s4_completions=s4_completions,
        exceptions=exceptions, counters=snapshot, resources=resources,
        summary=summary, smoke_passed=smoke_passed)
