"""J-lens utilities for loading and checking J-lens availability."""

from typing import Optional, Dict, Any, Tuple
import sys


def check_jacobian_lens_installed() -> bool:
    """Check if jacobian-lens package is installed."""
    try:
        import jlens  # noqa: F401
        return True
    except ImportError:
        try:
            import jacobian_lens  # noqa: F401
            return True
        except ImportError:
            return False


def get_jlens_install_command() -> str:
    """Return installation command for jacobian-lens."""
    return "pip install git+https://github.com/anthropics/jacobian-lens.git"


def check_prefitted_lens_locally(
    model_name: str,
    search_paths: list = None
) -> Tuple[bool, Optional[str]]:
    """
    Check for pre-fitted lens in common locations.
    
    Args:
        model_name: HuggingFace model name
        search_paths: Paths to search in
    
    Returns:
        Tuple of (found, path_if_found)
    """
    from pathlib import Path
    
    if search_paths is None:
        search_paths = [
            Path.home() / ".cache" / "jacobian-lens",
            Path.home() / ".huggingface" / "hub" / "jacobian-lens",
            Path("./lenses"),
        ]
    
    for search_path in search_paths:
        search_path = Path(search_path)
        if not search_path.exists():
            continue
        
        # Look for model-specific lens
        for item in search_path.iterdir():
            if model_name in item.name:
                return True, str(item)
    
    return False, None


def summarize_jlens_search_results(
    model_names: list,
    installed: bool,
    locally_found: Dict[str, Optional[str]]
) -> str:
    """Create a summary of J-lens search results."""
    lines = ["## J-lens Feasibility Summary\n"]
    lines.append(f"jacobian-lens package installed: {installed}\n")
    
    if not installed:
        lines.append(f"\nTo install jacobian-lens, run:\n")
        lines.append(f"```\n{get_jlens_install_command()}\n```\n")
    
    lines.append(f"\n### Pre-fitted lens search:\n")
    for model_name, path in locally_found.items():
        if path:
            lines.append(f"- **{model_name}**: Found at {path}")
        else:
            lines.append(f"- **{model_name}**: Not found locally")
            lines.append(f"  - Hugging Face: https://huggingface.co/models?search=jacobian-lens+{model_name}")
            lines.append(f"  - Neuronpedia: https://neuronpedia.org/")
    
    lines.append("\n")
    return "\n".join(lines)


def try_import_jacobian_lens():
    """
    Safely try to import jacobian-lens.
    
    Returns:
        (success, module_or_error_msg)
    """
    try:
        import jlens
        return True, jlens
    except ImportError as e:
        jlens_error = str(e)
        try:
            import jacobian_lens
            return True, jacobian_lens
        except ImportError as fallback_error:
            return False, f"jlens: {jlens_error}; jacobian_lens: {fallback_error}"
    except Exception as e:
        return False, f"Unexpected error loading jacobian-lens: {str(e)}"


class JacobianLensWrapper:
    """Wrapper for J-lens operations with graceful fallbacks."""
    
    def __init__(self):
        self.installed = check_jacobian_lens_installed()
        self.jlens_module = None
        
        if self.installed:
            success, result = try_import_jacobian_lens()
            if success:
                self.jlens_module = result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current J-lens status."""
        return {
            "installed": self.installed,
            "loadable": self.jlens_module is not None,
            "install_command": get_jlens_install_command() if not self.installed else None,
        }
    
    def validate_requirements(self) -> Tuple[bool, str]:
        """Validate that required packages are available."""
        missing = []
        
        try:
            import torch  # noqa: F401
        except ImportError:
            missing.append("torch")
        
        try:
            import transformers  # noqa: F401
        except ImportError:
            missing.append("transformers")
        
        if self.installed and not self.jlens_module:
            missing.append("jacobian-lens (installed but not loadable)")
        elif not self.installed:
            missing.append("jacobian-lens (not installed)")
        
        if missing:
            return False, f"Missing requirements: {', '.join(missing)}"
        
        return True, "All requirements satisfied"
    
    def create_tiny_fitting_report(self, feasible: bool, error: Optional[str] = None) -> str:
        """Create a report for tiny J-lens fitting."""
        lines = ["## Tiny J-lens Fitting\n"]
        
        if not self.installed:
            lines.append("**Status**: Skipped - jacobian-lens not installed\n")
            lines.append(f"To enable J-lens fitting, run:\n```\n{get_jlens_install_command()}\n```\n")
        elif not self.jlens_module:
            lines.append("**Status**: Failed - jacobian-lens not loadable\n")
            if error:
                lines.append(f"**Error**: {error}\n")
        elif feasible:
            lines.append("**Status**: Ready - tiny fitting can proceed\n")
            lines.append("Next steps: Run phase0_5 with --skip-fit=false\n")
        else:
            lines.append("**Status**: Failed during fitting\n")
            if error:
                lines.append(f"**Error**: {error}\n")
        
        return "\n".join(lines)
