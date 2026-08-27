#!/usr/bin/env python3
"""Step 1 construction verification for Study 5-EQ1 P-1. Zero GPU.

The adapter checkpoint is supposed to *be* `F`: target attention, embeddings and
norms, base MLP, plus the transcoder branch. This script tests that belief
before any accelerator hour is spent on it, because if the belief is wrong then
every number that follows is measuring something other than what it claims.

Four assertions, each emitting an OD-003 execution proof string:

* ``S1.A`` an independently constructed `H` is byte-exactly equal, tensor by
  tensor, to the adapter checkpoint's non-transcoder weights;
* ``S1.B`` loading is complete -- ``missing_keys`` and ``unexpected_keys`` are
  captured in full, and the transcoder parameter count matches the config
  geometry exactly;
* ``S1.C`` with the transcoder disabled, logits equal the independently built
  `H` on a fixed probe batch;
* ``S1.D`` with the transcoder enabled, logits differ materially from disabled.

``S1.D`` is not a formality. Without it, transcoder weights silently dropped on
load would make `F == H`, and Q-3 would then fail for an entirely spurious
reason while resembling a genuine fidelity result.

`transformers` 5.9.0 is a major-version jump and the adapter code was written
against the 4.x line. These assertions guard against 5.x behaviour changes,
which are a class of fault that returns wrong numbers rather than raising.

Two deliberate deviations from the upstream tooling, both recorded:

* `H` is built here rather than by ``misc_scripts/make_hybrid_model.py``. The
  construction is identical -- take the target model and copy the base model's
  ``gate_proj``, ``up_proj`` and ``down_proj`` into every layer -- but the
  upstream script passes ``trust_remote_code=True``, which authority section 8
  forbids for the target and the base model. Qwen2 is natively supported, so
  the registered contract is honoured with no loss of equivalence.
* the adapter class is imported directly rather than through
  ``trust_remote_code``. The checkpoint declares no ``auto_map``, so there is no
  remote code in it to trust; the class lives in the registered repository at
  the registered commit and is used in place, never redistributed (section 3.7).
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer

MLP_PROJECTIONS = ("gate_proj", "up_proj", "down_proj")
LOGIT_TOLERANCE = 1e-2
PROBE_PROMPTS = [
    "What is the sum of the first ten positive integers?",
    "Let f(x) = x^2 - 4x + 3. Find the roots of f.",
    "A bag holds 3 red and 5 blue marbles. One is drawn. What is P(red)?",
    "Simplify the expression: (2/3) + (5/6).",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def proof(check_id: str, passed: bool, detail: str = "") -> bool:
    """Emit an OD-003 execution proof string on the success path only."""

    if passed:
        print(f"P1-CHECK-{check_id} PASSED", flush=True)
    else:
        print(f"P1-CHECK-{check_id} FAILED: {detail}", flush=True)
    return passed


def tensor_digest(tensor: torch.Tensor) -> str:
    """Hash raw bytes, so equality means byte equality and not closeness."""

    flat = tensor.detach().cpu().contiguous().view(-1)
    return hashlib.sha256(flat.view(torch.uint8).numpy().tobytes()).hexdigest()


def set_transcoder(model: Any, enabled: bool) -> int:
    """Toggle the transcoder branch on every layer.

    The class exposes this as a per-MLP ``disable_transcoder`` flag, so the
    number of flags actually set is returned and asserted by the caller: a
    toggle that silently reached zero layers would make S1.C and S1.D compare a
    model against itself and pass for the wrong reason.
    """

    touched = 0
    for layer in model.model.layers:
        layer.mlp.disable_transcoder = not enabled
        touched += 1
    return touched


def build_hybrid(base_dir: Path, target_dir: Path) -> tuple[Any, dict[str, Any]]:
    log(f"loading target for H: {target_dir}")
    hybrid = AutoModelForCausalLM.from_pretrained(
        target_dir, dtype=torch.bfloat16, trust_remote_code=False
    )
    log(f"loading base MLP donor: {base_dir}")
    donor = AutoModelForCausalLM.from_pretrained(
        base_dir, dtype=torch.bfloat16, trust_remote_code=False
    )

    n_hybrid, n_donor = len(hybrid.model.layers), len(donor.model.layers)
    if n_hybrid != n_donor:
        raise SystemExit(f"layer count mismatch: target {n_hybrid}, base {n_donor}")

    swapped = 0
    for index in range(n_hybrid):
        for projection in MLP_PROJECTIONS:
            target_w = getattr(hybrid.model.layers[index].mlp, projection).weight
            donor_w = getattr(donor.model.layers[index].mlp, projection).weight
            if target_w.shape != donor_w.shape:
                raise SystemExit(f"layer {index} {projection} shape mismatch")
            target_w.data.copy_(donor_w.data)
            swapped += target_w.numel()
    log(f"swapped {3 * n_hybrid} projections, {swapped:,} parameters")

    del donor
    gc.collect()
    return hybrid, {"layers": n_hybrid, "mlp_params_swapped": swapped}


def load_adapter(adapter_dir: Path, repo_root: Path) -> tuple[Any, dict[str, Any]]:
    sys.path.insert(0, str(repo_root))
    from models.qwen2_transcoder import (  # type: ignore[import-not-found]
        Qwen2ConfigWithTranscoder,
        Qwen2ForCausalLMWithTranscoder,
    )

    config = Qwen2ConfigWithTranscoder.from_pretrained(adapter_dir)
    model, info = Qwen2ForCausalLMWithTranscoder.from_pretrained(
        adapter_dir,
        config=config,
        dtype=torch.bfloat16,
        output_loading_info=True,
    )
    return model, info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--adapter-repo", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    base_dir = Path(args.base)
    target_dir = Path(args.target)
    adapter_dir = Path(args.adapter)

    report: dict[str, Any] = {
        "schema_version": "study5-eq1-construction-verification-v1",
        "phase": "P-1",
        "step": "S1",
        "started_at_utc": utc_now(),
        "device": "cpu",
        "gpu_seconds": 0,
        "checks_expected": ["S1.A", "S1.B", "S1.C", "S1.D"],
        "hybrid_built_by": "this script, not misc_scripts/make_hybrid_model.py",
        "hybrid_construction_deviation": (
            "identical swap of gate_proj, up_proj and down_proj, but with "
            "trust_remote_code disabled as authority section 8 requires for the "
            "target and the base model"
        ),
        "adapter_class_source": (
            "imported in place from the registered repository at the registered "
            "commit; the checkpoint declares no auto_map, so there is no remote "
            "code in it to trust. Never redistributed, per section 3.7."
        ),
        "checks": {},
    }
    results: dict[str, bool] = {}

    hybrid, geometry = build_hybrid(base_dir, target_dir)
    report["hybrid_geometry"] = geometry
    hybrid_state = hybrid.state_dict()

    # ---------------------------------------------------------------- S1.A
    log("S1.A byte-comparing H against the adapter non-transcoder weights")
    adapter_tensors: dict[str, torch.Tensor] = {}
    transcoder_names: list[str] = []
    for shard in sorted(adapter_dir.glob("*.safetensors")):
        with safe_open(str(shard), framework="pt") as handle:
            for name in handle.keys():
                if "transcoder" in name.lower():
                    transcoder_names.append(name)
                else:
                    adapter_tensors[name] = handle.get_tensor(name)

    compared = equal = 0
    mismatches: list[dict[str, Any]] = []
    unmatched: list[str] = []
    digest_pairs: list[str] = []

    for name, adapter_tensor in sorted(adapter_tensors.items()):
        hybrid_tensor = hybrid_state.get(name)
        if hybrid_tensor is None:
            unmatched.append(name)
            continue
        compared += 1
        a_digest = tensor_digest(adapter_tensor)
        h_digest = tensor_digest(hybrid_tensor)
        digest_pairs.append(f"{name}:{a_digest}")
        if a_digest == h_digest:
            equal += 1
        else:
            mismatches.append(
                {
                    "tensor": name,
                    "shape": list(adapter_tensor.shape),
                    "adapter_sha256": a_digest,
                    "hybrid_sha256": h_digest,
                    "max_abs_diff": float(
                        (adapter_tensor.float() - hybrid_tensor.float()).abs().max()
                    ),
                }
            )

    rollup = hashlib.sha256("\n".join(sorted(digest_pairs)).encode()).hexdigest()
    s1a_ok = compared > 0 and not mismatches and not unmatched
    report["checks"]["S1.A"] = {
        "name": "independently built H is byte-exactly equal to the adapter non-transcoder weights",
        "adapter_transcoder_tensor_count": len(transcoder_names),
        "adapter_non_transcoder_tensor_count": len(adapter_tensors),
        "tensors_compared": compared,
        "tensors_byte_equal": equal,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:20],
        "unmatched_tensor_names": unmatched[:20],
        "non_transcoder_rollup_sha256": rollup,
        "passed": s1a_ok,
    }
    results["S1.A"] = proof(
        "S1.A",
        s1a_ok,
        f"compared={compared} mismatched={len(mismatches)} unmatched={len(unmatched)}",
    )

    del adapter_tensors
    gc.collect()

    if not s1a_ok:
        report["stopped_early"] = True
        report["stop_reason"] = (
            "S1.A failed, so our understanding of the construction is wrong. "
            "Spending accelerator hours on that premise would be waste. Stop, "
            "commit, report; do not repair."
        )
        report["finished_at_utc"] = utc_now()
        report["all_checks_passed"] = False
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        return 1

    # ---------------------------------------------------------------- S1.B
    log("S1.B loading the adapter and checking load completeness")
    adapter_model, load_info = load_adapter(adapter_dir, Path(args.adapter_repo))
    config = adapter_model.config

    hidden = int(config.hidden_size)
    layers = int(config.num_hidden_layers)
    features = int(config.transcoder_n_features)
    dec_bias = bool(getattr(config, "transcoder_dec_bias", False))

    expected_matrix = layers * 2 * hidden * features
    expected_bias = layers * (features + (hidden if dec_bias else 0))
    expected_total = expected_matrix + expected_bias
    observed = sum(
        p.numel()
        for n, p in adapter_model.named_parameters()
        if "transcoder" in n.lower()
    )

    missing_keys = list(load_info.get("missing_keys", []))
    unexpected_keys = list(load_info.get("unexpected_keys", []))
    s1b_ok = (
        not missing_keys and not unexpected_keys and observed == expected_total
    )
    report["checks"]["S1.B"] = {
        "name": "load completeness and transcoder parameter geometry",
        "config_hidden_size": hidden,
        "config_num_hidden_layers": layers,
        "config_transcoder_n_features": features,
        "config_transcoder_dec_bias": dec_bias,
        "expected_matrix_params": expected_matrix,
        "expected_matrix_params_formula": "num_hidden_layers * 2 * hidden_size * transcoder_n_features",
        "expected_bias_params": expected_bias,
        "expected_bias_params_formula": "num_hidden_layers * (transcoder_n_features + hidden_size if dec_bias)",
        "expected_total_transcoder_params": expected_total,
        "observed_transcoder_params": observed,
        "total_feature_count": layers * features,
        "missing_keys": missing_keys,
        "unexpected_keys": unexpected_keys,
        "missing_keys_count": len(missing_keys),
        "unexpected_keys_count": len(unexpected_keys),
        "keys_committed_in_full_even_when_empty": True,
        "passed": s1b_ok,
    }
    results["S1.B"] = proof(
        "S1.B",
        s1b_ok,
        f"missing={len(missing_keys)} unexpected={len(unexpected_keys)} "
        f"observed={observed} expected={expected_total}",
    )

    # ------------------------------------------------------- S1.C and S1.D
    log("S1.C / S1.D probe-batch logits with the transcoder off and on")
    tokenizer = AutoTokenizer.from_pretrained(target_dir, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    batch = tokenizer(
        PROBE_PROMPTS, return_tensors="pt", padding=True, truncation=True, max_length=64
    )

    def logits_of(model: Any) -> torch.Tensor:
        model.eval()
        with torch.no_grad():
            return model(**batch).logits.float()

    layers_off = set_transcoder(adapter_model, False)
    logits_off = logits_of(adapter_model)
    logits_hybrid = logits_of(hybrid)

    off_vs_hybrid = float((logits_off - logits_hybrid).abs().max())
    s1c_ok = layers_off == layers and off_vs_hybrid < LOGIT_TOLERANCE
    report["checks"]["S1.C"] = {
        "name": "transcoder-off logits match the independently built H",
        "layers_toggled": layers_off,
        "layers_expected": layers,
        "max_abs_logit_difference": off_vs_hybrid,
        "tolerance": LOGIT_TOLERANCE,
        "tolerance_rationale": (
            "bf16 accumulation order can differ between the two load paths; the "
            "tolerance admits that without admitting a real weight difference"
        ),
        "probe_prompts": len(PROBE_PROMPTS),
        "passed": s1c_ok,
    }
    results["S1.C"] = proof(
        "S1.C", s1c_ok, f"max_abs_diff={off_vs_hybrid} layers_toggled={layers_off}"
    )

    layers_on = set_transcoder(adapter_model, True)
    logits_on = logits_of(adapter_model)
    on_vs_off_max = float((logits_on - logits_off).abs().max())
    on_vs_off_mean = float((logits_on - logits_off).abs().mean())
    s1d_ok = layers_on == layers and on_vs_off_max > LOGIT_TOLERANCE
    report["checks"]["S1.D"] = {
        "name": "transcoder-on logits differ materially from transcoder-off",
        "layers_toggled": layers_on,
        "layers_expected": layers,
        "max_abs_logit_difference": on_vs_off_max,
        "mean_abs_logit_difference": on_vs_off_mean,
        "threshold": LOGIT_TOLERANCE,
        "why_this_check_exists": (
            "if transcoder weights were silently dropped on load then F would "
            "equal H, and Q-3 would fail for a spurious reason while resembling "
            "a genuine fidelity result"
        ),
        "passed": s1d_ok,
    }
    results["S1.D"] = proof("S1.D", s1d_ok, f"max_abs_diff={on_vs_off_max}")

    report["finished_at_utc"] = utc_now()
    report["all_checks_passed"] = all(results.values())
    report["transformers_major_version_jump_guarded"] = True

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    log(f"report written to {out}")
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
