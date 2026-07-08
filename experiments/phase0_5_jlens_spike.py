#!/usr/bin/env python3
"""
Phase 0.5: J-lens feasibility and saturation spike.

Objective: Determine if Plan A (real J-lens) is feasible.
- Search for pre-fitted lenses
- Attempt tiny fitting if jacobian-lens is available
- Measure cost/saturation across layer/prompt count sweeps
- Report feasibility for Phase 2
"""

import argparse
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import jspace_observation as jso
from jspace_observation import (
    ModelConfig,
    ExperimentConfig,
    RunLogger,
    SummaryBuilder,
    create_run_metadata,
    JacobianLensWrapper,
    load_model_and_tokenizer,
    log_model_info,
)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 0.5: J-lens feasibility and saturation spike"
    )
    parser.add_argument(
        "--model",
        default="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        help="Primary model to test",
    )
    parser.add_argument(
        "--baseline-model",
        default="Qwen/Qwen2.5-Math-1.5B",
        help="Baseline model for comparison",
    )
    parser.add_argument(
        "--prompt-counts",
        default="10,25,50",
        help="Comma-separated prompt counts to sweep",
    )
    parser.add_argument(
        "--sequence-lengths",
        default="64,128",
        help="Comma-separated sequence lengths to test",
    )
    parser.add_argument(
        "--layer-mode",
        choices=["single", "selected", "all"],
        default="selected",
        help="Which layers to fit J-lens on",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without executing",
    )
    parser.add_argument(
        "--skip-fit",
        action="store_true",
        help="Skip actual J-lens fitting, only check availability",
    )
    parser.add_argument(
        "--search-prefitted-only",
        action="store_true",
        help="Only search for pre-fitted lenses, don't attempt fitting",
    )
    
    args = parser.parse_args()
    
    # Parse sweep parameters
    prompt_counts = [int(x.strip()) for x in args.prompt_counts.split(",")]
    sequence_lengths = [int(x.strip()) for x in args.sequence_lengths.split(",")]
    models = [args.model]
    if args.baseline_model:
        models.append(args.baseline_model)
    
    # Setup output directory
    config = ExperimentConfig()
    if args.output_dir:
        run_dir = Path(args.output_dir)
    else:
        logger = RunLogger(config.results_dir)
        run_dir = logger.create_run_directory("phase0_5")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Phase 0.5: J-lens Feasibility Spike")
    print(f"=" * 60)
    print(f"Run directory: {run_dir}")
    print()
    
    # Initialize J-lens wrapper
    jlens = JacobianLensWrapper()
    jlens_status = jlens.get_status()
    
    print("J-lens Status:")
    print(f"  Installed: {jlens_status['installed']}")
    print(f"  Loadable: {jlens_status['loadable']}")
    print()
    
    # Phase 0.5a: Search for pre-fitted lenses
    print("Phase 0.5a: Searching for pre-fitted lenses...")
    print("-" * 60)
    
    prefitted_results = {}
    for model_name in models:
        found, path = jso.check_prefitted_lens_locally(model_name)
        prefitted_results[model_name] = (found, path)
        status = f"Found at {path}" if found else "Not found locally"
        print(f"  {model_name}: {status}")
    
    search_summary = jso.summarize_jlens_search_results(
        models,
        jlens_status['installed'],
        {m: p for m, (_, p) in prefitted_results.items()}
    )
    print()
    print(search_summary)
    
    # Phase 0.5b: Check tiny fitting feasibility
    print("\nPhase 0.5b: Checking tiny fitting feasibility...")
    print("-" * 60)
    
    valid_reqs, req_msg = jlens.validate_requirements()
    print(f"Requirements check: {req_msg}")
    
    can_fit = jlens_status['loadable'] and not args.skip_fit and not args.search_prefitted_only
    
    if can_fit:
        print("✓ J-lens fitting is theoretically possible")
        print("  (Not actually executing fitting in dry-run/scope mode)")
    else:
        if args.skip_fit:
            print("⊘ Fitting skipped (--skip-fit flag)")
        elif args.search_prefitted_only:
            print("⊘ Only searching for pre-fitted lenses (--search-prefitted-only flag)")
        elif not jlens_status['loadable']:
            print("✗ jacobian-lens not loadable. Install with:")
            print(f"  {jso.get_jlens_install_command()}")
        print()
    
    # Phase 0.5c: Create cost sweep plan
    print("\nPhase 0.5c: Cost sweep plan")
    print("-" * 60)
    print("Planned sweeps:")
    print(f"  Prompt counts: {prompt_counts}")
    print(f"  Sequence lengths: {sequence_lengths}")
    print(f"  Layer mode: {args.layer_mode}")
    
    sweep_configs = []
    for prompt_count in prompt_counts:
        for seq_len in sequence_lengths:
            sweep_configs.append({
                "prompt_count": prompt_count,
                "sequence_length": seq_len,
                "layer_mode": args.layer_mode,
            })
    print(f"  Total configs: {len(sweep_configs)}")
    print()
    
    # Phase 0.5d: Model loading check
    print("Phase 0.5d: Model loading check")
    print("-" * 60)
    
    model_infos = {}
    for model_name in models:
        try:
            config_obj = ModelConfig(model_name=model_name, dtype="float16")
            model, tokenizer, device, info = load_model_and_tokenizer(config_obj)
            model_infos[model_name] = info
            print(f"✓ {model_name}")
            log_model_info(info, verbose=True)
            print()
            # Clean up
            del model, tokenizer
        except Exception as e:
            print(f"✗ {model_name}: {str(e)}")
            print()
    
    # Generate summary
    summary_builder = SummaryBuilder("Phase 0.5: J-lens Feasibility Spike")
    
    summary_builder.add_section(
        "Objective",
        "Determine if Plan A (real J-lens) is feasible for mechanistic interpretation."
    )
    
    summary_builder.add_section(
        "Key Findings",
        search_summary
    )
    
    prefitted_summary = "\n".join([
        f"- {m}: {'✓ Found' if found else '✗ Not found'}"
        for m, (found, _) in prefitted_results.items()
    ])
    summary_builder.add_section("Pre-fitted Lens Status", prefitted_summary)
    
    fitting_status = jlens.create_tiny_fitting_report(can_fit)
    summary_builder.add_section("Tiny Fitting Status", fitting_status)
    
    # Decision summary
    decision_lines = []
    if any(found for _, (found, _) in prefitted_results.items()):
        decision_lines.append("- ✓ Pre-fitted lens found - Plan A partially unblocked")
    else:
        decision_lines.append("- Pre-fitted lens not found")
    
    if jlens_status['loadable']:
        decision_lines.append("- ✓ jacobian-lens installed - can attempt fitting")
    else:
        decision_lines.append(f"- jacobian-lens not available")
        decision_lines.append(f"  Install: `{jso.get_jlens_install_command()}`")
    
    decision_lines.append("")
    decision_lines.append("**Next Steps:**")
    decision_lines.append("1. If pre-fitted lens found: Load and validate (Phase 2)")
    decision_lines.append("2. If jacobian-lens available: Run tiny fitting in Phase 0.5 proper")
    decision_lines.append("3. Otherwise: Prepare Plan B (logit lens + probing)")
    
    summary_builder.add_section("Decision", "\n".join(decision_lines))
    
    # Save outputs
    summary = summary_builder.build()
    summary_path = Path(run_dir) / "phase0_5_summary.md"
    with open(summary_path, "w") as f:
        f.write(summary)
    
    print("\n" + "=" * 60)
    print("Phase 0.5 Summary")
    print("=" * 60)
    print(summary)
    print(f"\nSummary saved to: {summary_path}")
    
    # Save sweep configs
    sweep_path = Path(run_dir) / "phase0_5_sweep_configs.json"
    with open(sweep_path, "w") as f:
        json.dump({
            "prompt_counts": prompt_counts,
            "sequence_lengths": sequence_lengths,
            "layer_mode": args.layer_mode,
            "total_configs": len(sweep_configs),
            "configs": sweep_configs,
        }, f, indent=2)
    
    # Save metadata
    metadata = create_run_metadata(
        phase="phase0_5",
        model_names=models,
        experiment_config={
            "prompt_counts": prompt_counts,
            "sequence_lengths": sequence_lengths,
            "layer_mode": args.layer_mode,
            "skip_fit": args.skip_fit,
            "search_prefitted_only": args.search_prefitted_only,
        },
        notes="J-lens feasibility spike and pre-fitted lens search"
    )
    
    metadata_path = Path(run_dir) / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump({
            "timestamp": metadata.timestamp,
            "run_id": metadata.run_id,
            "phase": metadata.phase,
            "model_names": metadata.model_names,
            "experiment_config": metadata.experiment_config,
            "notes": metadata.notes,
        }, f, indent=2)
    
    print(f"Metadata saved to: {metadata_path}")
    print(f"Sweep configs saved to: {sweep_path}")
    
    # Update decision log
    decision_log_path = config.docs_dir / "decision_log.md"
    with open(decision_log_path, "a") as f:
        f.write(f"\n## Phase 0.5 Run - {datetime.now().isoformat()}\n")
        f.write(f"- Jacobian-lens installed: {jlens_status['installed']}\n")
        f.write(f"- Pre-fitted lens found: {any(found for _, (found, _) in prefitted_results.items())}\n")
        f.write(f"- Results: {run_dir}\n")


if __name__ == "__main__":
    main()
