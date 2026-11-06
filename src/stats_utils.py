"""
Statistical and Visualization Utilities for A/B Testing & Funnel Analysis.
Includes:
- Power analysis & sample size estimation (from first principles)
- Sample Ratio Mismatch (SRM) Chi-square check
- Two-proportion Z-test for Conversion Rates
- Non-parametric Mann-Whitney U test & Bootstrapping for Revenue/ARPU
- Funnel drop-off breakdown
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Tuple, Dict, Any

def calculate_sample_size_per_variant(
    baseline_cr: float,
    mde_relative: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> int:
    """
    Calculates required sample size per variant for a two-tailed test of two proportions.
    
    Formula based on standard normal approximation:
    n = (Z_alpha/2 * sqrt(2 * p_bar * (1 - p_bar)) + Z_beta * sqrt(p1*(1-p1) + p2*(1-p2)))^2 / (p2 - p1)^2
    """
    p1 = baseline_cr
    p2 = baseline_cr * (1 + mde_relative)
    p_bar = (p1 + p2) / 2
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    
    term1 = z_alpha * np.sqrt(2 * p_bar * (1 - p_bar))
    term2 = z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    
    n = ((term1 + term2) ** 2) / ((p2 - p1) ** 2)
    return int(np.ceil(n))

def check_srm(control_count: int, treatment_count: int, expected_ratio: float = 0.5) -> Dict[str, Any]:
    """
    Performs Chi-Square Goodness-of-Fit test to detect Sample Ratio Mismatch (SRM).
    Returns chi2 stat, p-value, and flag whether SRM is detected (p < 0.01).
    """
    total = control_count + treatment_count
    expected = [total * expected_ratio, total * (1 - expected_ratio)]
    observed = [control_count, treatment_count]
    
    chi2_stat, p_val = stats.chisquare(observed, f_exp=expected)
    srm_detected = p_val < 0.01
    
    return {
        "control_observed": control_count,
        "treatment_observed": treatment_count,
        "expected_split": f"{int(expected_ratio*100)}:{int((1-expected_ratio)*100)}",
        "chi2_stat": round(float(chi2_stat), 4),
        "p_value": float(p_val),
        "srm_detected": srm_detected,
        "status": "PASSED (No SRM)" if not srm_detected else "FAILED (SRM Detected - Investigate Traffic Assignment)"
    }

def two_proportion_z_test(
    conv_control: int, n_control: int,
    conv_treatment: int, n_treatment: int,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Performs pooled two-proportion Z-test and computes 95% Confidence Interval of the absolute difference.
    """
    p_ctrl = conv_control / n_control
    p_treat = conv_treatment / n_treatment
    diff = p_treat - p_ctrl
    relative_uplift = (diff / p_ctrl) * 100
    
    # Pooled standard error for hypothesis test
    p_pool = (conv_control + conv_treatment) / (n_control + n_treatment)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_treatment))
    z_stat = diff / se_pool
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    # Unpooled standard error for Confidence Interval
    se_diff = np.sqrt((p_ctrl * (1 - p_ctrl) / n_control) + (p_treat * (1 - p_treat) / n_treatment))
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff
    
    return {
        "control_cr": round(p_ctrl * 100, 2),
        "treatment_cr": round(p_treat * 100, 2),
        "absolute_difference_pct": round(diff * 100, 3),
        "relative_uplift_pct": round(relative_uplift, 2),
        "z_statistic": round(float(z_stat), 4),
        "p_value": float(p_value),
        "significant": bool(p_value < alpha),
        "ci_95_diff": [round(ci_lower * 100, 3), round(ci_upper * 100, 3)]
    }

def analyze_revenue(
    control_orders: pd.Series,
    treatment_orders: pd.Series,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Analyzes non-zero order values using Mann-Whitney U test (handles non-normality/skewness).
    """
    ctrl_mean = float(control_orders.mean())
    treat_mean = float(treatment_orders.mean())
    ctrl_median = float(control_orders.median())
    treat_median = float(treatment_orders.median())
    
    # Mann-Whitney U test
    stat, p_val = stats.mannwhitneyu(treatment_orders, control_orders, alternative="two-sided")
    
    return {
        "control_aov_mean": round(ctrl_mean, 2),
        "treatment_aov_mean": round(treat_mean, 2),
        "control_aov_median": round(ctrl_median, 2),
        "treatment_aov_median": round(treat_median, 2),
        "aov_uplift_pct": round(((treat_mean - ctrl_mean) / ctrl_mean) * 100, 2),
        "mann_whitney_u_stat": float(stat),
        "p_value": float(p_val),
        "significant": bool(p_val < alpha)
    }
