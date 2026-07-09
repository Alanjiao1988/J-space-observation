"""J-space observation package."""

from .config import (
    ModelConfig,
    NoCoTConfig,
    ExperimentConfig,
    get_default_config,
)
from .model_loader import (
    load_model_and_tokenizer,
    log_model_info,
)
from .no_cot import (
    construct_empty_think_prefill_prompt,
    construct_answer_only_prompt,
    construct_prefill_answer_prompt,
    construct_visible_cot_prompt,
    construct_r1_style_thinking_prompt,
    get_generation_config_for_condition,
    validate_no_cot_output,
    extract_answer_from_output,
    create_generation_record,
    NoCoTValidationResult,
)
from .prompt_sets import (
    PromptItem,
    ArithmeticPromptSet,
    SyntheticRelationPromptSet,
    FactualCounterfactualPromptSet,
    generate_all_pilot_prompt_sets,
    save_prompt_sets,
    load_prompt_sets,
)
from .eval_parsing import (
    parse_numeric_answer,
    parse_entity_answer,
    parse_yes_no_answer,
    parse_answer,
    evaluate_answer,
    create_eval_record,
    ParseResult,
)
from .stats import (
    wilson_ci,
    bootstrap_ci,
    compute_slope,
    cot_gain_by_depth,
    ConfidenceIntervalReport,
)
from .run_logging import (
    RunLogger,
    SummaryBuilder,
    RunMetadata,
    create_run_metadata,
    record_resource_usage,
)
from .jlens_utils import (
    check_jacobian_lens_installed,
    get_jlens_install_command,
    check_prefitted_lens_locally,
    summarize_jlens_search_results,
    try_import_jacobian_lens,
    JacobianLensWrapper,
)
from .blob_export import upload_directory_to_blob
from .postprocess import postprocess_answer_only, PostprocessResult

__version__ = "0.1.0"

__all__ = [
    # Config
    "ModelConfig",
    "NoCoTConfig",
    "ExperimentConfig",
    "get_default_config",
    # Model loading
    "load_model_and_tokenizer",
    "log_model_info",
    # No-CoT
    "construct_empty_think_prefill_prompt",
    "construct_answer_only_prompt",
    "construct_prefill_answer_prompt",
    "construct_visible_cot_prompt",
    "construct_r1_style_thinking_prompt",
    "get_generation_config_for_condition",
    "validate_no_cot_output",
    "extract_answer_from_output",
    "create_generation_record",
    "NoCoTValidationResult",
    # Prompt sets
    "PromptItem",
    "ArithmeticPromptSet",
    "SyntheticRelationPromptSet",
    "FactualCounterfactualPromptSet",
    "generate_all_pilot_prompt_sets",
    "save_prompt_sets",
    "load_prompt_sets",
    # Evaluation
    "parse_numeric_answer",
    "parse_entity_answer",
    "parse_yes_no_answer",
    "parse_answer",
    "evaluate_answer",
    "create_eval_record",
    "ParseResult",
    # Statistics
    "wilson_ci",
    "bootstrap_ci",
    "compute_slope",
    "cot_gain_by_depth",
    "ConfidenceIntervalReport",
    # Run logging
    "RunLogger",
    "SummaryBuilder",
    "RunMetadata",
    "create_run_metadata",
    "record_resource_usage",
    # J-lens utilities
    "check_jacobian_lens_installed",
    "get_jlens_install_command",
    "check_prefitted_lens_locally",
    "summarize_jlens_search_results",
    "try_import_jacobian_lens",
    "JacobianLensWrapper",
    # Blob export
    "upload_directory_to_blob",
    # Postprocess
    "postprocess_answer_only",
    "PostprocessResult",
]
