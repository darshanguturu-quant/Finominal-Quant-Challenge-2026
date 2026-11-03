"""Tests for performance metrics calculations."""

import pytest
import numpy as np
import pandas as pd
from src.metrics import (
    calculate_annualized_sharpe_ratio,
    calculate_cumulative_return,
    calculate_cagr,
    calculate_drawdown_series,
    calculate_all_metrics,
)


def test_annualized_sharpe_ratio_analytical():
    """Verify Sharpe ratio against analytical hand calculation.
    Daily returns: [0.01, -0.005, 0.015, -0.002, 0.008]
    Mean = (0.01 - 0.005 + 0.015 - 0.002 + 0.008) / 5 = 0.026 / 5 = 0.0052
    Sample std (ddof=1):
    diffs = [0.0048, -0.0102, 0.0098, -0.0072, 0.0028]
    sq_diffs = [2.304e-5, 10.404e-5, 9.604e-5, 5.184e-5, 0.784e-5] = 28.28e-5
    var = 28.28e-5 / 4 = 7.07e-5
    std = sqrt(7.07e-5) = 0.008408329
    Sharpe = (0.0052 / 0.008408329) * sqrt(252) = 0.618434 * 15.87450787 = 9.81734
    """
    rets = np.array([0.01, -0.005, 0.015, -0.002, 0.008])
    expected_mean = np.mean(rets)
    expected_std = np.std(rets, ddof=1)
    expected_sharpe = (expected_mean / expected_std) * np.sqrt(252)

    sharpe = calculate_annualized_sharpe_ratio(rets)
    assert np.isclose(sharpe, expected_sharpe)
    assert np.isclose(sharpe, 9.81734, atol=1e-3)


def test_cumulative_return_analytical():
    """Verify Cumulative Return: prod(1 + R) - 1.
    rets = [0.10, -0.05, 0.20]
    prod = 1.10 * 0.95 * 1.20 = 1.254
    CR = 0.254 (25.4%)
    """
    rets = np.array([0.10, -0.05, 0.20])
    cr = calculate_cumulative_return(rets)
    assert np.isclose(cr, 0.254)


def test_cagr_analytical():
    """Verify CAGR = (1 + CR)**(252 / N) - 1.
    CR = 1.0 (100% gain), N = 504 trading days (exactly 2 years of 252 days).
    CAGR = (1 + 1.0)**(252 / 504) - 1 = 2**0.5 - 1 = 1.41421356 - 1 = 41.421356%
    """
    cagr = calculate_cagr(cumulative_return=1.0, n_observations=504, periods_per_year=252)
    assert np.isclose(cagr, np.sqrt(2.0) - 1.0)


def test_drawdown_series():
    """Verify drawdown calculation."""
    rets = np.array([0.10, -0.20, 0.05])
    # Wealth: 1.10, 1.10 * 0.80 = 0.88, 0.88 * 1.05 = 0.924
    # Peaks: 1.10, 1.10, 1.10
    # Drawdowns: 0.0, (0.88 - 1.10)/1.10 = -0.20, (0.924 - 1.10)/1.10 = -0.16
    dd = calculate_drawdown_series(rets)
    assert np.isclose(dd.iloc[0], 0.0)
    assert np.isclose(dd.iloc[1], -0.20)
    assert np.isclose(dd.iloc[2], (0.924 - 1.10) / 1.10)


def test_calculate_all_metrics_structure():
    """Verify calculate_all_metrics returns all required dictionary keys."""
    rets = np.array([0.001, -0.0005, 0.002, 0.0001, -0.001])
    res = calculate_all_metrics(rets, lookback_days=63)

    assert res["lookback_days"] == 63
    assert res["n_observations"] == 5
    assert "annualized_sharpe_ratio" in res
    assert "cumulative_return_pct" in res
    assert "cagr_pct" in res
    assert "max_drawdown_pct" in res

