"""Unit tests for statistics utilities."""

import pytest
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation import (
    wilson_ci,
    bootstrap_ci,
    compute_slope,
    cot_gain_by_depth,
    ConfidenceIntervalReport,
)


def test_wilson_ci_perfect():
    """Test Wilson CI with perfect rate."""
    lower, upper = wilson_ci(10, 10, confidence=0.95)
    # Wilson CI is conservative; even with perfect rate, lower bound < 1
    assert 0.7 <= lower  # Lower bound for 10/10
    assert upper >= 0.95
    assert lower <= upper


def test_wilson_ci_half():
    """Test Wilson CI with 50% rate."""
    lower, upper = wilson_ci(5, 10, confidence=0.95)
    assert 0 < lower < 0.5 < upper < 1
    assert lower <= upper


def test_wilson_ci_zero():
    """Test Wilson CI with zero rate."""
    lower, upper = wilson_ci(0, 10, confidence=0.95)
    assert lower >= 0
    # Wilson CI is conservative; upper bound for 0/10 is around 0.28
    assert upper <= 0.3
    assert lower <= upper


def test_wilson_ci_bounds():
    """Test Wilson CI stays within [0,1]."""
    for successes in [0, 5, 10]:
        lower, upper = wilson_ci(successes, 10, confidence=0.95)
        assert 0 <= lower <= 1
        assert 0 <= upper <= 1


def test_bootstrap_ci_mean():
    """Test bootstrap CI for mean."""
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    lower, upper = bootstrap_ci(values, statistic_fn=np.mean, n_bootstrap=1000)
    true_mean = np.mean(values)
    assert lower <= true_mean <= upper


def test_bootstrap_ci_std():
    """Test bootstrap CI works with different statistics."""
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    lower, upper = bootstrap_ci(values, statistic_fn=np.std, n_bootstrap=1000)
    true_std = np.std(values)
    assert lower <= true_std <= upper


def test_compute_slope_increasing():
    """Test slope computation with increasing values."""
    depths = [1, 2, 3, 4]
    accuracies = [0.5, 0.6, 0.7, 0.8]
    slope, intercept, r2 = compute_slope(depths, accuracies)
    assert slope > 0  # Should be positive
    assert r2 > 0.9  # Should fit well


def test_compute_slope_decreasing():
    """Test slope computation with decreasing values."""
    depths = [1, 2, 3, 4]
    accuracies = [0.8, 0.7, 0.6, 0.5]
    slope, intercept, r2 = compute_slope(depths, accuracies)
    assert slope < 0  # Should be negative


def test_compute_slope_flat():
    """Test slope computation with flat values."""
    depths = [1, 2, 3, 4]
    accuracies = [0.5, 0.5, 0.5, 0.5]
    slope, intercept, r2 = compute_slope(depths, accuracies)
    assert abs(slope) < 0.01  # Should be near zero


def test_compute_slope_insufficient_data():
    """Test slope computation with insufficient data."""
    depths = [1]
    accuracies = [0.5]
    slope, intercept, r2 = compute_slope(depths, accuracies)
    assert slope == 0.0


def test_cot_gain_computation():
    """Test CoT gain computation."""
    answer_only = [0.5, 0.4, 0.3]
    visible_cot = [0.8, 0.8, 0.9]
    depths = [1, 2, 3]
    
    gains, slope, r2 = cot_gain_by_depth(answer_only, visible_cot, depths)
    
    assert len(gains) == 3
    assert all(g > 0 for g in gains)  # All gains should be positive
    assert slope >= 0  # Slope should be non-negative (gain increases with depth)


def test_confidence_interval_report():
    """Test ConfidenceIntervalReport."""
    report = ConfidenceIntervalReport("Test Metrics")
    
    # Add rate
    report.add_rate("accuracy", 8, 10, confidence=0.95)
    
    # Add continuous
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    report.add_continuous("latency", values, confidence=0.95)
    
    data = report.to_dict()
    assert "label" in data
    assert "metrics" in data
    assert "accuracy" in data["metrics"]
    assert "latency" in data["metrics"]


def test_confidence_interval_report_markdown():
    """Test ConfidenceIntervalReport markdown output."""
    report = ConfidenceIntervalReport("Test")
    report.add_rate("metric1", 5, 10)
    
    markdown = report.to_markdown()
    assert "## Test" in markdown
    assert "metric1" in markdown
    assert "|" in markdown  # Table format
