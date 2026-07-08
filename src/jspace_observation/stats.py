"""Statistical utilities for hypothesis testing and confidence intervals."""

import numpy as np
from typing import Tuple, List, Optional
from scipy import stats


def wilson_ci(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate Wilson score confidence interval for a proportion.
    
    Args:
        successes: Number of successes
        total: Total number of trials
        confidence: Confidence level (e.g., 0.95 for 95%)
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if total == 0:
        return 0.0, 0.0
    
    p = successes / total
    z = stats.norm.ppf((1 + confidence) / 2)
    
    denominator = 1 + z**2 / total
    center_adjusted_success = p + z**2 / (2 * total)
    adjusted_std = np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    
    margin = z * adjusted_std
    
    lower = (center_adjusted_success - margin) / denominator
    upper = (center_adjusted_success + margin) / denominator
    
    lower = max(0.0, lower)
    upper = min(1.0, upper)
    
    return lower, upper


def bootstrap_ci(
    values: np.ndarray,
    statistic_fn=np.mean,
    n_bootstrap: int = 10000,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate bootstrap confidence interval.
    
    Args:
        values: Array of values
        statistic_fn: Function to compute statistic (default: mean)
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    values = np.asarray(values)
    bootstrap_stats = []
    
    np.random.seed(42)  # For reproducibility
    for _ in range(n_bootstrap):
        sample = np.random.choice(values, size=len(values), replace=True)
        bootstrap_stats.append(statistic_fn(sample))
    
    alpha = 1 - confidence
    lower_percentile = alpha / 2 * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    lower = np.percentile(bootstrap_stats, lower_percentile)
    upper = np.percentile(bootstrap_stats, upper_percentile)
    
    return float(lower), float(upper)


def compute_slope(
    depths: List[int],
    accuracies: List[float]
) -> Tuple[float, float, float]:
    """
    Compute linear regression slope for depth vs accuracy.
    
    Args:
        depths: List of reasoning depths
        accuracies: List of corresponding accuracies
    
    Returns:
        Tuple of (slope, intercept, r_squared)
    """
    depths_arr = np.array(depths)
    accuracies_arr = np.array(accuracies)
    
    # Remove NaN values
    valid_idx = ~(np.isnan(depths_arr) | np.isnan(accuracies_arr))
    depths_arr = depths_arr[valid_idx]
    accuracies_arr = accuracies_arr[valid_idx]
    
    if len(depths_arr) < 2:
        return 0.0, 0.0, 0.0
    
    # Linear regression
    coeffs = np.polyfit(depths_arr, accuracies_arr, 1)
    slope, intercept = coeffs[0], coeffs[1]
    
    # R-squared
    predictions = np.polyval(coeffs, depths_arr)
    ss_res = np.sum((accuracies_arr - predictions) ** 2)
    ss_tot = np.sum((accuracies_arr - np.mean(accuracies_arr)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return slope, intercept, r_squared


def cot_gain_by_depth(
    answer_only_accuracies: List[float],
    visible_cot_accuracies: List[float],
    depths: List[int]
) -> Tuple[List[float], float, float]:
    """
    Compute CoT gain (visible_cot - answer_only) by depth.
    
    Args:
        answer_only_accuracies: Accuracies for answer-only condition
        visible_cot_accuracies: Accuracies for visible-CoT condition
        depths: Reasoning depths
    
    Returns:
        Tuple of (gains_by_depth, slope, r_squared)
    """
    gains = [
        cot - ao
        for ao, cot in zip(answer_only_accuracies, visible_cot_accuracies)
    ]
    
    slope, _, r_squared = compute_slope(depths, gains)
    
    return gains, slope, r_squared


class ConfidenceIntervalReport:
    """Report for confidence intervals and statistics."""
    
    def __init__(self, label: str):
        self.label = label
        self.data = {}
    
    def add_rate(self, name: str, successes: int, total: int, confidence: float = 0.95):
        """Add rate with Wilson CI."""
        rate = successes / total if total > 0 else 0.0
        lower, upper = wilson_ci(successes, total, confidence)
        self.data[name] = {
            "type": "rate",
            "value": rate,
            "lower": lower,
            "upper": upper,
            "successes": successes,
            "total": total,
        }
    
    def add_continuous(self, name: str, values: np.ndarray, confidence: float = 0.95):
        """Add continuous statistic with bootstrap CI."""
        mean_val = float(np.mean(values))
        lower, upper = bootstrap_ci(values, confidence=confidence)
        self.data[name] = {
            "type": "continuous",
            "value": mean_val,
            "lower": lower,
            "upper": upper,
            "n": len(values),
        }
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "label": self.label,
            "metrics": self.data,
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown table."""
        lines = [f"## {self.label}\n"]
        lines.append("| Metric | Value | CI Lower | CI Upper |")
        lines.append("|--------|-------|----------|----------|")
        
        for name, data in self.data.items():
            value = data["value"]
            lower = data["lower"]
            upper = data["upper"]
            lines.append(f"| {name} | {value:.4f} | {lower:.4f} | {upper:.4f} |")
        
        return "\n".join(lines)
