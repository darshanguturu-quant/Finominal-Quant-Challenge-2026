"""Performance metrics calculation module for Finominal Quant Challenge 2026.

Formulas:
- Annualized Sharpe Ratio:
    SR = (mu_{p, daily} / sigma_{p, daily}) * sqrt(252)
    where mu is the sample mean daily return, sigma is sample standard deviation (ddof=1),
    and risk-free rate is 0.0%.

- Cumulative Return:
    CR = prod_{t=1}^N (1 + R_{p, t, daily}) - 1

- CAGR:
    CAGR = (1 + CR)**(252 / N) - 1
"""

from typing import Dict, Union
import numpy as np
import pandas as pd


def calculate_annualized_sharpe_ratio(
    daily_returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Calculate the annualized Sharpe ratio using sample standard deviation.

    Args:
        daily_returns: 1D array or Series of daily portfolio returns.
        risk_free_rate: Annualized or daily risk-free rate (assumed 0.0).
        periods_per_year: Trading days in a year (252).

    Returns:
        Annualized Sharpe ratio as a float.
    """
    arr = np.asarray(daily_returns, dtype=float)
    if len(arr) < 2:
        return 0.0

    mean_ret = np.mean(arr) - risk_free_rate
    std_ret = np.std(arr, ddof=1)

    if std_ret == 0.0 or np.isnan(std_ret):
        return 0.0

    return float((mean_ret / std_ret) * np.sqrt(periods_per_year))


def calculate_cumulative_return(
    daily_returns: Union[pd.Series, np.ndarray],
) -> float:
    """Calculate the total cumulative return over N observations.

    CR = prod_{t=1}^N (1 + R_{p, t, daily}) - 1

    Args:
        daily_returns: 1D array or Series of daily portfolio returns.

    Returns:
        Cumulative return as a decimal (e.g., 1.50 = 150%).
    """
    arr = np.asarray(daily_returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float(np.prod(1.0 + arr) - 1.0)


def calculate_cagr(
    cumulative_return: float,
    n_observations: int,
    periods_per_year: int = 252,
) -> float:
    """Calculate Compound Annual Growth Rate (CAGR).

    CAGR = (1 + Cumulative Return)**(252 / N) - 1

    Args:
        cumulative_return: Total cumulative return as decimal.
        n_observations: Total number of observations N.
        periods_per_year: Trading days in a year (252).

    Returns:
        CAGR as a decimal (e.g., 0.15 = 15%).
    """
    if n_observations <= 0:
        return 0.0
    base = 1.0 + cumulative_return
    if base <= 0:
        return -1.0
    exponent = float(periods_per_year) / float(n_observations)
    return float(base ** exponent - 1.0)


def calculate_drawdown_series(
    daily_returns: Union[pd.Series, np.ndarray],
) -> pd.Series:
    """Calculate the drawdown series from daily returns.

    Args:
        daily_returns: Daily portfolio returns.

    Returns:
        pd.Series of drawdowns (non-positive decimals, where 0.0 = at peak).
    """
    arr = np.asarray(daily_returns, dtype=float)
    wealth_index = np.cumprod(1.0 + arr)
    peaks = np.maximum.accumulate(wealth_index)
    drawdowns = (wealth_index - peaks) / peaks
    if isinstance(daily_returns, pd.Series):
        return pd.Series(drawdowns, index=daily_returns.index)
    return pd.Series(drawdowns)


def calculate_all_metrics(
    daily_returns: Union[pd.Series, np.ndarray],
    lookback_days: int,
    periods_per_year: int = 252,
) -> Dict[str, Union[float, int]]:
    """Compute the full suite of mandatory and auxiliary performance metrics.

    Mandatory Metrics:
    - Optimal Lookback Period (Days)
    - Maximum Annualized Sharpe Ratio
    - Cumulative Return (%)
    - CAGR (%)

    Auxiliary Metrics:
    - Sample Mean Daily Return (%)
    - Sample Daily Volatility (%)
    - Annualized Volatility (%)
    - Maximum Drawdown (%)
    - Calmar Ratio
    - Total Observations (N)

    Args:
        daily_returns: Array or Series of daily returns.
        lookback_days: Lookback period L in exact trading days.
        periods_per_year: 252.

    Returns:
        Dictionary of formatted metrics.
    """
    arr = np.asarray(daily_returns, dtype=float)
    n_obs = len(arr)

    sharpe = calculate_annualized_sharpe_ratio(arr, periods_per_year=periods_per_year)
    cum_ret = calculate_cumulative_return(arr)
    cagr = calculate_cagr(cum_ret, n_obs, periods_per_year=periods_per_year)

    mean_daily = float(np.mean(arr)) if n_obs > 0 else 0.0
    std_daily = float(np.std(arr, ddof=1)) if n_obs > 1 else 0.0
    ann_vol = std_daily * np.sqrt(periods_per_year)

    dd_series = calculate_drawdown_series(arr)
    max_dd = float(dd_series.min()) if len(dd_series) > 0 else 0.0

    calmar = (cagr / abs(max_dd)) if max_dd < 0 else 0.0

    return {
        "lookback_days": lookback_days,
        "n_observations": n_obs,
        "annualized_sharpe_ratio": sharpe,
        "cumulative_return": cum_ret,
        "cumulative_return_pct": cum_ret * 100.0,
        "cagr": cagr,
        "cagr_pct": cagr * 100.0,
        "mean_daily_return_pct": mean_daily * 100.0,
        "daily_volatility_pct": std_daily * 100.0,
        "annualized_volatility_pct": ann_vol * 100.0,
        "max_drawdown_pct": max_dd * 100.0,
        "calmar_ratio": calmar,
    }
