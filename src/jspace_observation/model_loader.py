"""Model loading utilities for Hugging Face models."""

import torch
from pathlib import Path
from typing import Tuple, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
from .config import ModelConfig


def load_model_and_tokenizer(
    config: ModelConfig,
    cache_dir: Optional[str] = None,
    trust_remote_code: bool = True
) -> Tuple:
    """
    Load a causal language model and tokenizer from Hugging Face.
    
    Args:
        config: Model configuration
        cache_dir: Optional cache directory for model weights
        trust_remote_code: Whether to trust remote code
    
    Returns:
        Tuple of (model, tokenizer, device, info_dict)
    """
    # Determine dtype
    dtype_map = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }
    torch_dtype = dtype_map.get(config.dtype, torch.float16)
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config.model_name,
        cache_dir=cache_dir,
        trust_remote_code=trust_remote_code,
    )
    
    # Ensure pad token is set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Prepare model loading arguments
    model_kwargs = {
        "torch_dtype": torch_dtype,
        "device_map": config.device_map,
        "trust_remote_code": trust_remote_code,
        "output_hidden_states": config.output_hidden_states,
    }
    
    if cache_dir:
        model_kwargs["cache_dir"] = cache_dir
    
    if config.load_in_8bit:
        model_kwargs["load_in_8bit"] = True
    if config.load_in_4bit:
        model_kwargs["load_in_4bit"] = True
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        **model_kwargs
    )
    
    # Get device info
    device = next(model.parameters()).device
    
    # Collect info
    info = {
        "model_name": config.model_name,
        "dtype": config.dtype,
        "device": str(device),
        "num_parameters": sum(p.numel() for p in model.parameters()),
        "device_map": config.device_map,
    }
    
    # Try to add architecture info
    if hasattr(model, "config"):
        config_obj = model.config
        if hasattr(config_obj, "num_hidden_layers"):
            info["num_hidden_layers"] = config_obj.num_hidden_layers
        if hasattr(config_obj, "hidden_size"):
            info["hidden_size"] = config_obj.hidden_size
        if hasattr(config_obj, "num_attention_heads"):
            info["num_attention_heads"] = config_obj.num_attention_heads
    
    # Try to get GPU name
    if "cuda" in str(device):
        try:
            info["gpu_name"] = torch.cuda.get_device_name(device)
            info["gpu_memory_total"] = torch.cuda.get_device_properties(device).total_memory / 1e9
        except Exception:
            pass
    
    return model, tokenizer, device, info


def log_model_info(info: dict, verbose: bool = True) -> str:
    """Format and optionally print model info."""
    lines = ["Model Information:"]
    lines.append(f"  Model: {info.get('model_name', 'unknown')}")
    lines.append(f"  Device: {info.get('device', 'unknown')}")
    lines.append(f"  Dtype: {info.get('dtype', 'unknown')}")
    if "num_hidden_layers" in info:
        lines.append(f"  Layers: {info['num_hidden_layers']}")
    if "hidden_size" in info:
        lines.append(f"  Hidden size: {info['hidden_size']}")
    if "num_parameters" in info:
        params_b = info["num_parameters"] / 1e9
        lines.append(f"  Parameters: {params_b:.2f}B")
    if "gpu_name" in info:
        lines.append(f"  GPU: {info['gpu_name']}")
    if "gpu_memory_total" in info:
        lines.append(f"  GPU memory: {info['gpu_memory_total']:.2f} GB")
    
    result = "\n".join(lines)
    if verbose:
        print(result)
    return result
