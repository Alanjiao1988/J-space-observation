"""Stage P0-M: the capped Study 3-P0 model pilot.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
section 8.

This module runs only inside an Azure containerized GPU job, bound to the exact
commit and tree published by the tokenizer gate. It never runs on the
workstation and never in GitHub Actions.

Fixed inference behaviour (section 8.1):

* the exact checkpoint is loaded once, in evaluation mode and fp16;
* ``torch.inference_mode()`` wraps every forward;
* no sampling, stochastic layer, adapter, gradient, training, calibration,
  fine-tuning, prompt search, or output-conditioned retry;
* S1 reads the next-token logits only for the four registered label token IDs;
* S2 reads the same next-token logit vector only for the ten registered content
  token IDs;
* S3 rescores on CPU from the already captured S2 vector and adds exactly zero
  prefill, decode, model-load or forward operations;
* S4 uses the registered pre-wrapper bytes and each role's registered
  native-wrapper policy, greedy decoding, ``do_sample=False`` and
  ``max_new_tokens=4``, with no sampling temperature passed;
* every S4 completion is retained and mapped through the pinned deterministic
  parser, and ``unparseable`` stays an explicit value;
* no hidden state, activation, attention, gradient, hook, lens output, probe,
  patch or ablation is ever collected.

Correctness, accuracy, response diversity and discordance are **not** smoke pass
criteria. The smoke gate is mechanical only.
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_corpus import build_rows, canonical_bytes  # noqa: E402
from p0_counters import CapExceeded, P0Counters  # noqa: E402
from p0_parser import parse_s4_completion  # noqa: E402
from p0_protocol import ROLES  # noqa: E402
from p0_renderer import P0Renderer, load_protocol, load_registry  # noqa: E402

RESULT_SCHEMA_VERSION = "study3-p0-model-pilot-result-v1"
RECEIPT_SCHEMA_VERSION = "study3-p0-model-pilot-receipt-v1"

SMOKE_TUPLE_CLASS = "K2-none-0"
STOP_SMOKE = "STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE"
COMPLETE = "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE"
COMPLETE_LOW_INFO = (
    "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE_EMPIRICALLY_LOW_INFORMATION")
MAX_NEW_TOKENS = 4


class SmokeMechanicalFailure(Exception):
    """The smoke mechanical gate failed after a model operation occurred."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def device_identity():
    import torch

    info = {
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    if torch.cuda.is_available():
        info.update({
            "device_name": torch.cuda.get_device_name(0),
            "device_capability": list(torch.cuda.get_device_capability(0)),
            "cuda_runtime_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version(),
            "device_count": torch.cuda.device_count(),
            "total_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
        })
    return info


def _candidate_token_ids(tokenizer, surfaces):
    ids = []
    for surface in surfaces:
        encoded = tokenizer.encode(surface, add_special_tokens=False)
        if len(encoded) != 1:
            raise SmokeMechanicalFailure(
                "candidate surface %r is not a single token" % surface)
        ids.append(int(encoded[0]))
    if len(set(ids)) != len(ids):
        raise SmokeMechanicalFailure("candidate token IDs are not pairwise distinct")
    return ids


def _restricted_argmax(logits, candidate_ids, surfaces):
    """Deterministic restricted argmax with registered tie breaking."""
    import math

    values = []
    for token_id in candidate_ids:
        value = float(logits[token_id])
        if not math.isfinite(value):
            raise SmokeMechanicalFailure(
                "a registered candidate logit is not finite")
        values.append(value)
    best = 0
    for index in range(1, len(values)):
        if values[index] > values[best]:
            best = index
    return surfaces[best].strip(), values


def run_role(role, corpus_rows, registry, counters, out_records, offline):
    """Execute every authorized model operation for one role, then release it."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(
        role["repository_identity"], revision=role["immutable_revision"],
        trust_remote_code=False, local_files_only=offline)
    counters.add("distinct_tokenizer_identities_constructed", 1)
    model = AutoModelForCausalLM.from_pretrained(
        role["repository_identity"], revision=role["immutable_revision"],
        trust_remote_code=False, local_files_only=offline,
        dtype=torch.float16)
    counters.add("distinct_checkpoint_identities_downloaded", 1)
    counters.add("model_weight_loads", 1)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    renderer = P0Renderer(registry)
    profiles = {entry["profile"]: entry for entry in registry["profiles"]}
    s1_surfaces = profiles["S1"]["candidate_surfaces"]["by_label_alphabet"]
    s2_surfaces = profiles["S2"]["candidate_surfaces"]["answer_domain"]
    s2_ids = _candidate_token_ids(tokenizer, s2_surfaces)

    s2_vectors = {}

    with torch.inference_mode():
        for row in corpus_rows:
            for member in row["members"]:
                prompt = member["prompt"]
                key = (row["tuple_class_id"], row["contrast"],
                       member["role_in_pair"])
                record = {
                    "role": role["role"],
                    "row_id": row["row_id"],
                    "base_item_id": row["base_item_id"],
                    "tuple_class_id": row["tuple_class_id"],
                    "profile": row["profile"],
                    "contrast": row["contrast"],
                    "rendering": member["rendering"],
                    "role_in_pair": member["role_in_pair"],
                    "prompt_sha256": member["prompt_sha256"],
                    "ground_truth": row["ground_truth"],
                }
                if row["profile"] == "S3":
                    vector = s2_vectors.get(key)
                    if vector is None:
                        raise SmokeMechanicalFailure(
                            "an S3 row has no captured S2 logit vector to reuse")
                    prediction, values = _restricted_argmax(
                        vector["logits"], s2_ids, s2_surfaces)
                    counters.add("s3_cpu_only_reuse_scored_rows", 1)
                    counters.add("restricted_logit_reads", len(s2_ids))
                    record.update({
                        "scoring": "cpu_only_reuse_of_the_s2_logit_vector",
                        "model_evaluations_added": 0,
                        "candidate_surfaces": list(s2_surfaces),
                        "candidate_token_ids": s2_ids,
                        "restricted_logits": values,
                        "prediction": prediction,
                        "token_count": vector["token_count"],
                        "reused_from_row_id": vector["row_id"],
                    })
                    record["correct"] = prediction == row["ground_truth"]
                    out_records.append(record)
                    continue

                ids = tokenizer.encode(prompt, add_special_tokens=False)
                counters.add("tokenizer_encoded_sequences", 1)
                input_ids = torch.tensor([ids], device=device)

                if row["profile"] in ("S1", "S2"):
                    tick = time.time()
                    outputs = model(input_ids=input_ids)
                    counters.add("non_generative_prefill_evaluations", 1)
                    counters.add("runtime_batched_forward_calls", 1)
                    logits = outputs.logits[0, -1, :].float().cpu()
                    latency = round(time.time() - tick, 6)
                    if row["profile"] == "S1":
                        alphabet = member["nuisance_state"]["label_alphabet"]
                        surfaces = s1_surfaces[alphabet]
                        candidate_ids = _candidate_token_ids(tokenizer, surfaces)
                        prediction, values = _restricted_argmax(
                            logits, candidate_ids, surfaces)
                        counters.add("s1_scored_rows", 1)
                        expected = member["displayed_labels"][
                            member["nuisance_state"]["content_position"]]
                    else:
                        candidate_ids = s2_ids
                        surfaces = s2_surfaces
                        prediction, values = _restricted_argmax(
                            logits, candidate_ids, surfaces)
                        counters.add("s2_scored_rows", 1)
                        expected = row["ground_truth"]
                        s2_vectors[key] = {
                            "logits": logits, "token_count": len(ids),
                            "row_id": row["row_id"],
                        }
                    counters.add("restricted_logit_reads", len(candidate_ids))
                    record.update({
                        "scoring": "restricted_next_token_logits",
                        "model_evaluations_added": 1,
                        "candidate_surfaces": list(surfaces),
                        "candidate_token_ids": candidate_ids,
                        "restricted_logits": values,
                        "prediction": prediction,
                        "expected_surface": expected,
                        "token_count": len(ids),
                        "latency_seconds": latency,
                    })
                    record["correct"] = prediction == expected
                    out_records.append(record)
                    continue

                # S4: the never-selectable generative diagnostic.
                wrapped = _apply_role_native_wrapper(tokenizer, prompt)
                wrapped_ids = tokenizer.encode(wrapped, add_special_tokens=False)
                counters.add("tokenizer_encoded_sequences", 1)
                gen_input = torch.tensor([wrapped_ids], device=device)
                tick = time.time()
                generated = model.generate(
                    input_ids=gen_input, do_sample=False,
                    max_new_tokens=MAX_NEW_TOKENS,
                    pad_token_id=tokenizer.eos_token_id)
                latency = round(time.time() - tick, 6)
                counters.add("s4_generation_calls", 1)
                counters.add("s4_prefill_evaluations", 1)
                new_ids = [int(i) for i in generated[0][len(wrapped_ids):]]
                counters.add("generated_tokens", len(new_ids))
                counters.add(
                    "s4_incremental_decode_evaluations", max(len(new_ids) - 1, 0))
                completion = tokenizer.decode(new_ids, skip_special_tokens=True)
                parsed = parse_s4_completion(
                    completion, member["displayed_labels"])
                counters.add("parser_calls", 1)
                counters.add("s4_scored_generation_rows", 1)
                expected = member["displayed_labels"][
                    member["nuisance_state"]["content_position"]]
                record.update({
                    "scoring": "pinned_deterministic_parser_over_greedy_generation",
                    "model_evaluations_added": 1 + max(len(new_ids) - 1, 0),
                    "wrapper_applied": True,
                    "registered_message_sha256": member["prompt_sha256"],
                    "wrapped_prompt_sha256": hashlib.sha256(
                        wrapped.encode("utf-8")).hexdigest(),
                    "raw_completion": completion,
                    "generated_token_ids": new_ids,
                    "generated_token_count": len(new_ids),
                    "parser_result": parsed["value"],
                    "unparseable": parsed["unparseable"],
                    "expected_surface": expected,
                    "token_count": len(wrapped_ids),
                    "latency_seconds": latency,
                })
                record["correct"] = (
                    None if parsed["unparseable"] else parsed["value"] == expected)
                out_records.append(record)

    peak = {}
    if torch.cuda.is_available():
        peak = {
            "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        }
        del model
        torch.cuda.empty_cache()
    else:
        del model
    return {
        "role": role["role"],
        "repository_identity": role["repository_identity"],
        "immutable_revision": role["immutable_revision"],
        "wall_seconds": round(time.time() - started, 6),
        "device": device,
        "peak_memory": peak,
    }


def _apply_role_native_wrapper(tokenizer, message_content):
    """Apply the role's registered native chat wrapper around the message bytes.

    The wrapper is role-specific and lives outside the rendering registry. Its
    bytes are wrapper bytes, never registered message bytes, and no cross-role
    byte parity is claimed. A role that publishes no chat template contributes no
    wrapper, and the registered message content is then the complete prompt.
    """
    template = getattr(tokenizer, "chat_template", None)
    if not template:
        return message_content
    wrapped = tokenizer.apply_chat_template(
        [{"role": "user", "content": message_content}],
        tokenize=False, add_generation_prompt=True)
    if message_content not in wrapped:
        raise SmokeMechanicalFailure(
            "the role-native wrapper altered the registered message bytes")
    return wrapped


def smoke_gate(records, counters):
    """The mechanical smoke gate of section 8.2. Correctness is not a criterion."""
    failures = []
    smoke = [r for r in records if r["tuple_class_id"] == SMOKE_TUPLE_CLASS
             and r["profile"] in ("S1", "S2", "S3")]
    seen = set()
    for record in smoke:
        key = (record["role"], record["row_id"], record["role_in_pair"])
        if key in seen:
            failures.append("duplicate scored row %s" % (key,))
        seen.add(key)
        if record.get("restricted_logits") is None:
            failures.append("missing restricted logits for %s" % (key,))
    expected_rows = 66
    if len(smoke) != expected_rows:
        failures.append(
            "the smoke produced %d scored rows, not the registered %d"
            % (len(smoke), expected_rows))
    prefill = sum(r["model_evaluations_added"] for r in smoke)
    if prefill != 60:
        failures.append(
            "the smoke performed %d model evaluations, not the registered 60"
            % prefill)
    for record in smoke:
        if record["profile"] == "S3" and record["model_evaluations_added"] != 0:
            failures.append("an S3 row added a model evaluation")
    counters.reconcile_totals()
    return failures


def descriptive_summary(records):
    """Descriptive only. No p-value, gate, rank, winner or effect-size estimate."""
    summary = {}
    for record in records:
        key = "%s|%s|%s|%s" % (record["role"], record["profile"],
                               record["contrast"], record["tuple_class_id"])
        cell = summary.setdefault(key, {
            "role": record["role"], "profile": record["profile"],
            "contrast": record["contrast"],
            "tuple_class_id": record["tuple_class_id"],
            "rows": 0, "predictions": {}, "correct": 0, "unparseable": 0,
            "prompt_token_lengths": [],
        })
        cell["rows"] += 1
        prediction = record.get("prediction") or record.get("parser_result")
        cell["predictions"][str(prediction)] = \
            cell["predictions"].get(str(prediction), 0) + 1
        if record.get("correct") is True:
            cell["correct"] += 1
        if record.get("unparseable"):
            cell["unparseable"] += 1
        if record.get("token_count") is not None:
            cell["prompt_token_lengths"].append(record["token_count"])
    pairs = {}
    for record in records:
        key = (record["role"], record["profile"], record["contrast"],
               record["tuple_class_id"], record["row_id"])
        pairs.setdefault(key, {})[record["role_in_pair"]] = record
    discordance = {"pairs": 0, "joint_correct": 0, "discordant": 0}
    for members in pairs.values():
        if len(members) != 2:
            continue
        discordance["pairs"] += 1
        a = members.get("baseline", {}).get("correct")
        b = members.get("variant", {}).get("correct")
        if a is True and b is True:
            discordance["joint_correct"] += 1
        if a is not None and b is not None and a != b:
            discordance["discordant"] += 1
    for cell in summary.values():
        lengths = cell.pop("prompt_token_lengths")
        cell["prompt_token_length_min"] = min(lengths) if lengths else None
        cell["prompt_token_length_max"] = max(lengths) if lengths else None
        cell["output_support_size"] = len(cell["predictions"])
    return {"by_cell": summary, "pairwise": discordance,
            "interpretation_boundary": (
                "descriptive at this sample size. Zero observed discordance is "
                "not proof of invariance and is not by itself a mechanical "
                "failure. These numbers may never choose or justify a threshold, "
                "sample size, alpha, seed, bank, profile or confirmation rule.")}


def run(out_dir, offline=False, smoke_only=False):
    started = time.time()
    run_id = utc_now()
    counters = P0Counters()
    registry = load_registry()
    protocol = load_protocol()
    rows = build_rows(registry, protocol)
    if smoke_only:
        rows = [r for r in rows if r["tuple_class_id"] == SMOKE_TUPLE_CLASS
                and r["profile"] in ("S1", "S2", "S3")]
    records = []
    roles_meta = []
    state = COMPLETE
    stop_reason = None
    try:
        for role in ROLES:
            roles_meta.append(
                run_role(role, rows, registry, counters, records, offline))
        failures = smoke_gate(records, counters)
        if failures:
            state = STOP_SMOKE
            stop_reason = "; ".join(failures)
    except (SmokeMechanicalFailure, CapExceeded) as exc:
        state = STOP_SMOKE
        stop_reason = str(exc)

    summary = descriptive_summary(records)
    if state == COMPLETE and summary["pairwise"]["discordant"] == 0:
        state = COMPLETE_LOW_INFO
        stop_reason = (
            "no pairwise discordance was observed anywhere in this deliberately "
            "tiny corpus. This is a descriptive low-information observation, not "
            "a mechanical failure and not evidence of invariance.")

    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "document_class": "study3_p0_model_pilot_result",
        "run_id": run_id,
        "stage": "P0-M",
        "state": state,
        "stop_reason": stop_reason,
        "roles": roles_meta,
        "device_identity": device_identity(),
        "max_new_tokens": MAX_NEW_TOKENS,
        "records": records,
        "descriptive_summary": summary,
        "counters": counters.snapshot(),
        "wall_seconds": round(time.time() - started, 6),
        "formal_execution_authorized": False,
        "evidence_status": (
            "methods-feasibility observations only; never Study 3 evidence and "
            "never an entry in paper/evidence_ledger.csv"),
    }
    os.makedirs(out_dir, exist_ok=True)
    payload = canonical_bytes(result)
    with open(os.path.join(out_dir, "p0_model_pilot_result.json"), "wb") as handle:
        handle.write(payload)
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_model_pilot_receipt",
        "run_id": run_id,
        "stage": "P0-M",
        "state": state,
        "stop_reason": stop_reason,
        "result_document": {
            "path": "p0_model_pilot_result.json",
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "counters": counters.snapshot(),
        "device_identity": device_identity(),
        "claim_boundary": (
            "a methods-feasibility observation. It selects no interface, passes "
            "no formal gate, estimates no confirmatory effect, answers no "
            "research question and is not Study 3 evidence."),
    }
    with open(os.path.join(out_dir, "p0_model_pilot_receipt.json"), "wb") as handle:
        handle.write(canonical_bytes(receipt))
    print("state: %s" % state)
    return 0 if state in (COMPLETE, COMPLETE_LOW_INFO) else 4


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args(argv)
    return run(args.out_dir, offline=args.offline, smoke_only=args.smoke_only)


if __name__ == "__main__":
    sys.exit(main())
