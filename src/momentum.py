"""Momentum calculation and ranking module for Finominal Quant Challenge 2026.

Formula:
    M_i = (P_{i, T_calc} / P_{i, T_calc - L_days}) - 1

Stocks are ranked in descending order based on calculated M_i:
    Rank 1 = highest momentum score.
"""

from typing import Union
import pandas as pd
import numpy as np


def calculate_momentum(
    price_calc: Union[pd.Series, np.ndarray],
    price_lookback: Union[pd.Series, np.ndarray],
) -> pd.Series:
    """Calculate momentum scores for all stocks over an exact trading day lookback.

    Args:
        price_calc: Closing prices on calculation date T_calc.
        price_lookback: Closing prices on trading day (T_calc - L_days).

    Returns:
        pd.Series of momentum scores indexed by stock ticker.

    Raises:
        ValueError: If prices contain non-positive values or indices mismatch.
    """
    if isinstance(price_calc, np.ndarray):
        price_calc = pd.Series(price_calc)
    if isinstance(price_lookback, np.ndarray):
        price_lookback = pd.Series(price_lookback, index=price_calc.index)

    if not price_calc.index.equals(price_lookback.index):
        # Align indices if possible
        price_lookback = price_lookback.reindex(price_calc.index)

    if (price_calc <= 0).any():
        bad = price_calc[price_calc <= 0]
        raise ValueError(f"Non-positive prices found at T_calc:\n{bad}")
    if (price_lookback <= 0).any():
        bad = price_lookback[price_lookback <= 0]
        raise ValueError(f"Non-positive prices found at T_calc - L_days:\n{bad}")

    momentum = (price_calc / price_lookback) - 1.0
    return momentum


def rank_momentum(
    momentum_scores: pd.Series,
    tie_method: str = "first",
) -> pd.Series:
    """Rank stocks in descending order based on momentum score.

    Rank 1 represents the stock with the highest momentum.
    Uses deterministic tie-breaking (alphabetical order by ticker symbol)
    to guarantee 100% reproducible results.

    Args:
        momentum_scores: pd.Series of momentum scores indexed by stock ticker.
        tie_method: Tie-breaking method for pandas rank ('first' by default).

    Returns:
        pd.Series of integer or float ranks (1 to N), where 1 = highest momentum.
    """
    # Sort deterministically by index (ticker) first to guarantee stable tie-breaking
    sorted_scores = momentum_scores.sort_index(ascending=True)

    # Rank descending: highest momentum gets rank 1
    ranks = sorted_scores.rank(ascending=False, method=tie_method)

    # Reindex back to original order
    return ranks.reindex(momentum_scores.index)
