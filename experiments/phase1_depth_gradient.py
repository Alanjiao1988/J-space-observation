#!/usr/bin/env python3
"""
Phase 1: Behavioral reasoning-depth gradient.

Objective: Characterize how accuracy and CoT gain vary with reasoning depth.

For each model × task_family × depth × condition:
- Generate completions
- Parse answers
- Evaluate correctness
- Record metrics and latency

Output:
- generation records (JSONL)
- metrics (CSV)
- depth gradient plots
- summary report
"""

import argparse
import json
import csv
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import jspace_observation as jso
from jspace_observation import (
    ModelConfig,
    ExperimentConfig,
    RunLogger,
    SummaryBuilder,
    create_run_metadata,
    load_model_and_tokenizer,
    log_model_info,
    generate_all_pilot_prompt_sets,
    construct_empty_think_prefill_prompt,
    construct_answer_only_prompt,
    construct_visible_cot_prompt,
    construct_r1_style_thinking_prompt,
    parse_answer,
    evaluate_answer,
    create_generation_record,
    create_eval_record,
    wilson_ci,
    cot_gain_by_depth,
    compute_slope,
)


def run_generation(
    model,
    tokenizer,
    prompt: str,
    model_name: str,
    max_new_tokens: int = 128,
    device = None
) -> Tuple[str, float]:
    """
    Generate response and measure latency.
    
    Returns:
        Tuple of (output_text, generation_time_seconds)
    """
    import torch
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    
    start_time = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=1.0,
            top_p=1.0,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    
    gen_time = time.time() - start_time
    
    # Decode
    output_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    # Remove input from output
    input_text = tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=False)
    if output_text.startswith(input_text):
        output_text = output_text[len(input_text):]
    
    return output_text.strip(), gen_time


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: Behavioral reasoning-depth gradient"
    )
    parser.add_argument(
        "--models",
        default="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B,Qwen/Qwen2.5-Math-1.5B",
        help="Comma-separated model names to test",
    )
    parser.add_argument(
        "--task-families",
        default="arithmetic,synthetic_relation,factual_counterfactual",
        help="Comma-separated task families to run",
    )
    parser.add_argument(
        "--depths",
        default="1,2,3",
        help="Comma-separated depths to run",
    )
    parser.add_argument(
        "--conditions",
        default="strict_answer_only,visible_cot,r1_style_thinking",
        help="Comma-separated conditions to test",
    )
    parser.add_argument(
        "--items-per-cell",
        type=int,
        default=None,
        help="Number of items per model/task/depth/condition cell (default: all pilot items)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=128,
        help="Max tokens for generation",
    )
    parser.add_argument(
        "--dtype",
        default="float16",
        choices=["float16", "bfloat16", "float32"],
        help="Dtype for model",
    )
    parser.add_argument(
        "--device-map",
        default="auto",
        help="Device map for model",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without executing",
    )
    
    args = parser.parse_args()
    
    # Parse arguments
    models = [m.strip() for m in args.models.split(",")]
    task_families = [t.strip() for t in args.task_families.split(",")]
    depths = [int(d.strip()) for d in args.depths.split(",")]
    conditions = [c.strip() for c in args.conditions.split(",")]
    
    # Setup
    config = ExperimentConfig()
    if args.output_dir:
        run_dir = Path(args.output_dir)
    else:
        logger = RunLogger(config.results_dir)
        run_dir = logger.create_run_directory("phase1")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("Phase 1: Behavioral Reasoning-Depth Gradient")
    print("=" * 60)
    print(f"Run directory: {run_dir}")
    print(f"Models: {models}")
    print(f"Task families: {task_families}")
    print(f"Depths: {depths}")
    print(f"Conditions: {conditions}")
    print()
    
    if args.dry_run:
        total_cells = len(models) * len(task_families) * len(depths) * len(conditions)
        print(f"[DRY RUN] Total cells: {total_cells}")
        print("[DRY RUN] Not running actual experiments")
        return
    
    # Load prompt sets
    print("Loading prompt sets...")
    prompt_sets = generate_all_pilot_prompt_sets()
    print(f"Loaded {len(prompt_sets)} task families")
    for family, items in prompt_sets.items():
        print(f"  {family}: {len(items)} items")
    print()
    
    # Generate records
    generation_records = []
    eval_records = []
    metrics_rows = [["model", "task_family", "depth", "condition", 
                      "accuracy", "parse_valid", "no_cot_valid", "avg_latency_s"]]
    
    # Process each cell
    for model_name in models:
        print(f"\nLoading model: {model_name}...")
        try:
            config_obj = ModelConfig(model_name=model_name, dtype=args.dtype)
            model, tokenizer, device, info = load_model_and_tokenizer(config_obj)
            print("[OK] Model loaded")
            log_model_info(info, verbose=True)
        except Exception as e:
            print(f"[FAIL] Failed to load: {str(e)}")
            traceback.print_exc()
            continue
        
        for task_family in task_families:
            if task_family not in prompt_sets:
                print(f"[SKIP] Task family not found: {task_family}")
                continue
            
            items_by_depth = {}
            for item in prompt_sets[task_family]:
                if item.depth not in items_by_depth:
                    items_by_depth[item.depth] = []
                items_by_depth[item.depth].append(item)
            
            for depth in depths:
                if depth not in items_by_depth:
                    print(f"[SKIP] No items for {task_family} depth {depth}")
                    continue
                
                items = items_by_depth[depth]
                if args.items_per_cell:
                    items = items[:args.items_per_cell]
                
                for condition in conditions:
                    print(f"\n{model_name} | {task_family} | depth={depth} | {condition}")
                    print("-" * 50)
                    
                    cell_records = []
                    correct_count = 0
                    parse_valid_count = 0
                    no_cot_valid_count = 0
                    latencies = []
                    
                    for item in items:
                        # Construct prompt
                        if condition == "strict_answer_only":
                            if "R1-Distill" in model_name or "deepseek" in model_name.lower():
                                full_prompt = construct_empty_think_prefill_prompt(item.prompt_base)
                                no_cot_method = "empty_think_prefill"
                            else:
                                full_prompt = construct_answer_only_prompt(item.prompt_base)
                                no_cot_method = "answer_only_prompt"
                        elif condition == "visible_cot":
                            full_prompt = construct_visible_cot_prompt(item.prompt_base)
                            no_cot_method = "visible_cot"
                        else:  # r1_style_thinking
                            full_prompt = construct_r1_style_thinking_prompt(item.prompt_base)
                            no_cot_method = "r1_style_thinking"
                        
                        # Generate
                        try:
                            output, gen_time = run_generation(
                                model, tokenizer, full_prompt, model_name,
                                max_new_tokens=args.max_new_tokens,
                                device=device
                            )
                            latencies.append(gen_time)
                        except Exception as e:
                            print(f"  [FAIL] Generation failed: {str(e)}")
                            output = ""
                            gen_time = 0
                        
                        # Create generation record
                        gen_record = create_generation_record(
                            prompt=full_prompt,
                            output=output,
                            no_cot_method=no_cot_method,
                            model_name=model_name,
                            task_id=item.id,
                            ground_truth=item.expected_answer,
                            task_family=task_family,
                            depth=depth,
                            condition=condition,
                            generation_time_s=gen_time,
                        )
                        generation_records.append(gen_record)
                        cell_records.append(gen_record)
                        
                        # Parse and evaluate
                        eval_record = create_eval_record(
                            output=output,
                            parse_type=item.parse_type,
                            expected_answer=item.expected_answer,
                            task_id=item.id,
                            model_name=model_name,
                            task_family=task_family,
                            depth=depth,
                            condition=condition,
                        )
                        eval_records.append(eval_record)
                        
                        # Count metrics
                        if eval_record["parse_valid"]:
                            parse_valid_count += 1
                        if eval_record["correctness"]:
                            correct_count += 1
                        if gen_record["no_cot_validity"]:
                            no_cot_valid_count += 1
                    
                    # Compute metrics
                    n_items = len(items)
                    accuracy = correct_count / n_items if n_items > 0 else 0
                    parse_valid_rate = parse_valid_count / n_items if n_items > 0 else 0
                    no_cot_valid_rate = no_cot_valid_count / n_items if n_items > 0 else 0
                    avg_latency = sum(latencies) / len(latencies) if latencies else 0
                    
                    print(f"  Accuracy: {accuracy:.3f}")
                    print(f"  Parse valid: {parse_valid_rate:.3f}")
                    print(f"  No-CoT valid: {no_cot_valid_rate:.3f}")
                    print(f"  Avg latency: {avg_latency:.2f}s")
                    
                    # Add to metrics
                    metrics_rows.append([
                        model_name,
                        task_family,
                        depth,
                        condition,
                        f"{accuracy:.4f}",
                        f"{parse_valid_rate:.4f}",
                        f"{no_cot_valid_rate:.4f}",
                        f"{avg_latency:.4f}",
                    ])
        
        # Clean up model
        del model, tokenizer
    
    # Save generation records
    gen_path = run_dir / "phase1_generations.jsonl"
    with open(gen_path, "w") as f:
        for record in generation_records:
            f.write(json.dumps(record) + "\n")
    print(f"\nGeneration records saved: {gen_path}")
    
    # Save eval records
    eval_path = run_dir / "phase1_eval_records.jsonl"
    with open(eval_path, "w") as f:
        for record in eval_records:
            f.write(json.dumps(record) + "\n")
    print(f"Eval records saved: {eval_path}")
    
    # Save metrics
    metrics_path = run_dir / "phase1_metrics.csv"
    with open(metrics_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(metrics_rows)
    print(f"Metrics saved: {metrics_path}")
    
    # Generate summary
    summary_builder = SummaryBuilder("Phase 1: Behavioral Reasoning-Depth Gradient")
    
    summary_builder.add_section(
        "Objective",
        "Characterize behavioral performance (accuracy, CoT gain) as a function of reasoning depth."
    )
    
    summary_builder.add_section(
        "Experimental Design",
        f"- Models: {', '.join(models)}\n"
        f"- Task families: {', '.join(task_families)}\n"
        f"- Depths: {depths}\n"
        f"- Conditions: {', '.join(conditions)}\n"
        f"- Generation records: {len(generation_records)}"
    )
    
    summary_builder.add_section(
        "Outputs",
        f"- Generations: {gen_path}\n"
        f"- Evaluations: {eval_path}\n"
        f"- Metrics: {metrics_path}"
    )
    
    summary_builder.add_section(
        "Next Steps",
        "1. Analyze depth gradients and CoT gain slopes\n"
        "2. Identify ability floors for each task/model cell\n"
        "3. Mark cells with sufficient headroom for Phase 5 ablations\n"
        "4. Prepare Phase 1.5 layer taxonomy if J-lens feasible"
    )
    
    summary = summary_builder.build()
    summary_path = run_dir / "phase1_summary.md"
    with open(summary_path, "w") as f:
        f.write(summary)
    
    print("\n" + "=" * 60)
    print("Phase 1 Complete")
    print("=" * 60)
    print(f"Results in: {run_dir}")


if __name__ == "__main__":
    main()
