#!/usr/bin/env python3
"""Three-arm measurement for Study 5-EQ1 P-1 steps 3 and 4.

Measures `T`, `H` and `F` on the development primary set under the registered
sampling contract SC-001.

**`H` is the adapter checkpoint with the transcoder disabled, not a separately
built hybrid.** That is not a shortcut, it is what step 1 established: S1.A
showed the adapter's 339 non-transcoder tensors are byte-identical to an
independently constructed hybrid, and S1.C showed the transcoder-off logits
match that hybrid with a maximum absolute difference of exactly 0.0. Sharing one
load for `H` and `F` therefore *guarantees* the two arms differ in the
transcoder and in nothing else -- a guarantee that two separate checkpoint loads
could not give, since any divergence in loading would silently become part of
the contrast.

Design points that follow from the registered contract:

* the seed depends on ``(item_id, sample_index)`` and **not** on the condition,
  so the same item draws the same seed in all three arms. This is common random
  numbers: sampling noise is shared and differences out of the paired contrast;
* one item is written to the results file, flushed and ``fsync``-ed, before the
  next item begins, so an interrupted run leaves a complete prefix rather than a
  truncated final record;
* a run is resumable and idempotent by ``(item_id, arm, sample_index)``. Work
  already recorded is skipped rather than repeated, so the smoke run's output is
  kept and continued rather than discarded and redone;
* every check emits an OD-003 execution proof string, and every record carries
  the physical GPU UUID required by OD-006, because the container's device index
  is 0 for every worker and therefore carries no information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

AUTHORITY_SHA256 = "5c45d31a2aab23ffe93bbf5f4a220fb1835c1b98e960a2588fa587efcb9b1a35"
STUDY_ID = "STUDY5_EQ1"
ARMS = ("T", "H", "F")

# SC-001, frozen.
TEMPERATURE = 0.6
TOP_P = 0.95
TOP_K = 0
NUM_BEAMS = 1
REPETITION_PENALTY = 1.0
MAX_NEW_TOKENS = 16384  # OA-002

# Registered degeneration detector. Fixed here, before any measurement.
DEGEN_WINDOW_TOKENS = 400
DEGEN_UNIQUE_RATIO = 0.15
DEGEN_NGRAM = 10


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def proof(check_id: str, passed: bool, detail: str = "") -> bool:
    if passed:
        print(f"P1-CHECK-{check_id} PASSED", flush=True)
    else:
        print(f"P1-CHECK-{check_id} FAILED: {detail}", flush=True)
    return passed


def seed_for(item_id: str, sample_index: int) -> int:
    """SC-001 seed rule. Deliberately independent of the condition."""

    payload = f"{STUDY_ID}|{AUTHORITY_SHA256}|{item_id}|{sample_index}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def physical_gpu_uuid_last_twelve() -> str:
    """Resolve the physical device identity required by OD-006.

    The container's device index is 0 for every worker, so it identifies
    nothing. nvidia-smi inside the container reports the UUID of the device that
    was actually passed through.
    """

    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip().splitlines()
    except Exception:
        return "UNRESOLVED"
    if not out:
        return "UNRESOLVED"
    return out[0].strip().replace("GPU-", "")[-12:]


# ---------------------------------------------------------------- answers


def extract_last_boxed(text: str) -> str | None:
    """Return the content of the LAST \\boxed{...}, with balanced braces.

    A regex cannot do this correctly: answers routinely contain nested braces
    such as \\boxed{\\frac{1}{2}}, and a non-greedy match would truncate at the
    first inner close brace while a greedy one would swallow trailing text.
    """

    marker = "\\boxed"
    start = text.rfind(marker)
    if start == -1:
        return None
    index = start + len(marker)
    while index < len(text) and text[index] in " \t":
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    depth = 0
    for position in range(index, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[index + 1 : position].strip()
    return None


_CLEAN = (
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\!", ""),
    (r"\\,", ""),
    (r"\\;", ""),
    (r"\\ ", " "),
    (r"\\dfrac", r"\\frac"),
    (r"\\tfrac", r"\\frac"),
    (r"\\%", ""),
    (r"\^\{\\circ\}", ""),
    (r"\^\\circ", ""),
    (r"\\\$", ""),
    (r"\\text\{[^}]*\}", ""),
    (r"\\mbox\{[^}]*\}", ""),
)


def normalise_answer(value: str) -> str:
    text = value.strip().strip("$").strip()
    for pattern, replacement in _CLEAN:
        text = re.sub(pattern, replacement, text)
    text = text.replace(" ", "").rstrip(".")
    if text.endswith("\\"):
        text = text[:-1]
    return text


def latex_to_sympy(value: str) -> str:
    """Translate the small LaTeX subset MATH-500 answers actually use."""

    text = value
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", text)
    text = re.sub(r"\\sqrt(\d)", r"sqrt(\1)", text)
    text = text.replace("\\pi", "pi").replace("\\cdot", "*").replace("\\times", "*")
    text = text.replace("^", "**")
    text = re.sub(r"(\d)\(", r"\1*(", text)
    text = re.sub(r"\)(\d)", r")*\1", text)
    text = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", text)
    return text


def answers_equivalent(predicted: str | None, reference: str) -> bool:
    """Frozen symbolic equivalence check.

    String equality first, because it is exact and cheap; symbolic comparison
    only for the cases string equality cannot settle. A symbolic failure returns
    False rather than raising, so one unparseable answer cannot abort a run.
    """

    if predicted is None:
        return False
    left, right = normalise_answer(predicted), normalise_answer(reference)
    if left == right:
        return True
    try:
        import sympy
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )

        transformations = standard_transformations + (
            implicit_multiplication_application,
        )
        a = parse_expr(latex_to_sympy(left), transformations=transformations)
        b = parse_expr(latex_to_sympy(right), transformations=transformations)
        difference = sympy.simplify(a - b)
        return bool(difference == 0)
    except Exception:
        return False


def is_degenerate(token_ids: list[int]) -> bool:
    """Registered repetition-degeneration detector, fixed before measurement."""

    tail = token_ids[-DEGEN_WINDOW_TOKENS:]
    if len(tail) < DEGEN_NGRAM * 4:
        return False
    grams = [
        tuple(tail[i : i + DEGEN_NGRAM]) for i in range(len(tail) - DEGEN_NGRAM + 1)
    ]
    if not grams:
        return False
    return (len(set(grams)) / len(grams)) < DEGEN_UNIQUE_RATIO


# ---------------------------------------------------------------- models


def load_models(target_dir: Path, adapter_dir: Path, adapter_repo: Path) -> Any:
    sys.path.insert(0, str(adapter_repo))
    from models.qwen2_transcoder import (  # type: ignore[import-not-found]
        Qwen2ConfigWithTranscoder,
        Qwen2ForCausalLMWithTranscoder,
    )

    log("loading T")
    target = AutoModelForCausalLM.from_pretrained(
        target_dir, dtype=torch.bfloat16, trust_remote_code=False
    ).to("cuda").eval()

    log("loading the adapter, which supplies both H and F")
    config = Qwen2ConfigWithTranscoder.from_pretrained(adapter_dir)
    adapter = Qwen2ForCausalLMWithTranscoder.from_pretrained(
        adapter_dir, config=config, dtype=torch.bfloat16
    )
    features = int(config.transcoder_n_features)
    for layer in adapter.model.layers:
        counters = getattr(layer.mlp, "_dead_feature_counters", None)
        if counters is None or counters.is_meta:
            layer.mlp._dead_feature_counters = torch.zeros(features)
    adapter = adapter.to("cuda").eval()
    return target, adapter


def set_transcoder(model: Any, enabled: bool) -> int:
    touched = 0
    for layer in model.model.layers:
        layer.mlp.disable_transcoder = not enabled
        touched += 1
    return touched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--adapter-repo", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--contamination", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument(
        "--resume-from",
        action="append",
        default=[],
        help=(
            "additional results files whose records count as already done. Each "
            "shard writes its own file, so concurrent workers never append to a "
            "shared one; this flag is how a shard learns what other workers, or "
            "the smoke run, have already completed."
        ),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--sample-index", type=int, default=0)
    parser.add_argument("--check-id", required=True)
    args = parser.parse_args(argv)

    if not torch.cuda.is_available():
        raise SystemExit("no CUDA device visible")
    if torch.cuda.device_count() != 1:
        raise SystemExit(
            f"{torch.cuda.device_count()} devices visible; the registered "
            "contract requires exactly one per worker"
        )
    gpu_uuid = physical_gpu_uuid_last_twelve()
    log(f"physical GPU {gpu_uuid}, container index 0")

    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    contamination = json.loads(Path(args.contamination).read_text(encoding="utf-8"))
    excluded = {f["item_id"] for f in contamination["flagged_items"]}
    development = [i for i in split["development_ids"] if i not in excluded]
    log(f"development primary set: {len(development)} items after {len(excluded)} exclusions")

    rows: dict[str, dict[str, Any]] = {}
    with open(args.benchmark, "r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            identifier = str(
                row.get("unique_id") or row.get("id") or row.get("problem_id") or index
            )
            rows[identifier] = row

    ordered = [i for i in development if i in rows]
    if len(ordered) != len(development):
        raise SystemExit(
            f"{len(development) - len(ordered)} development items are missing from "
            "the benchmark file; refusing to run a partial measurement"
        )
    if args.limit:
        ordered = ordered[args.start : args.start + args.limit]
    else:
        ordered = ordered[args.start :]
    ordered = [i for n, i in enumerate(ordered) if n % args.num_shards == args.shard]
    log(f"this worker: {len(ordered)} items (shard {args.shard}/{args.num_shards})")

    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    done: set[tuple[str, str, int]] = set()
    for source in [results_path, *(Path(p) for p in args.resume_from)]:
        if not source.exists():
            continue
        with open(source, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    # A truncated final line is expected after a kill and is not
                    # an error: the record simply counts as not done and will be
                    # regenerated. Anything else would discard good work.
                    continue
                done.add(
                    (record["item_id"], record["arm"], int(record["sample_index"]))
                )
    log(f"{len(done)} records already present; they will be skipped, not repeated")

    target, adapter = load_models(
        Path(args.target), Path(args.adapter), Path(args.adapter_repo)
    )
    tokenizer = AutoTokenizer.from_pretrained(args.target, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    gpu_seconds = 0.0
    written = 0
    nan_seen = False

    for position, item_id in enumerate(ordered):
        row = rows[item_id]
        problem = str(row.get("problem", ""))
        reference = str(row.get("answer", row.get("solution", "")))

        for arm in ARMS:
            key = (item_id, arm, args.sample_index)
            if key in done:
                continue

            if arm == "T":
                model = target
            else:
                model = adapter
                set_transcoder(adapter, arm == "F")

            messages = [{"role": "user", "content": problem}]
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

            seed = seed_for(item_id, args.sample_index)
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

            started = time.time()
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    do_sample=True,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    top_k=TOP_K,
                    num_beams=NUM_BEAMS,
                    repetition_penalty=REPETITION_PENALTY,
                    max_new_tokens=MAX_NEW_TOKENS,
                    pad_token_id=tokenizer.pad_token_id,
                )
            elapsed = time.time() - started
            gpu_seconds += elapsed

            generated = output[0][inputs["input_ids"].shape[1] :]
            token_ids = generated.tolist()
            text = tokenizer.decode(token_ids, skip_special_tokens=True)
            predicted = extract_last_boxed(text)
            correct = answers_equivalent(predicted, reference)

            record = {
                "item_id": item_id,
                "arm": arm,
                "sample_index": args.sample_index,
                "seed": seed,
                "correct": bool(correct),
                "predicted_answer": predicted,
                "reference_answer": reference,
                "has_boxed": predicted is not None,
                "completed_tokens": len(token_ids),
                "hit_ceiling": len(token_ids) >= MAX_NEW_TOKENS,
                "degenerate": is_degenerate(token_ids),
                "seconds": round(elapsed, 3),
                "gpu_uuid_last_twelve": gpu_uuid,
                "gpu_index_in_container": 0,
                "ts_utc": utc_now(),
                "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "response_chars": len(text),
            }

            # Written and fsynced before the next generation begins, so a kill
            # leaves a complete prefix rather than a truncated final record.
            with open(results_path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            written += 1

            if not math.isfinite(float(output[0].float().sum())):
                nan_seen = True

        if (position + 1) % 5 == 0:
            log(
                f"  {position + 1}/{len(ordered)} items, {written} records, "
                f"{gpu_seconds / 3600:.4f} GPU-hours"
            )

    log(f"done: {written} records, {gpu_seconds:.1f} GPU-seconds")
    proof(args.check_id, not nan_seen, "a non-finite value appeared in generation")
    return 0 if not nan_seen else 1


if __name__ == "__main__":
    raise SystemExit(main())
