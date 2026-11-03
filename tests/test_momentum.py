"""Tests for momentum calculation and ranking."""

import pytest
import pandas as pd
import numpy as np
from src.momentum import calculate_momentum, rank_momentum


def test_momentum_formula_synthetic():
    """Verify exact formula: M_i = (P_calc / P_lookback) - 1."""
    p_calc = pd.Series({"A": 120.0, "B": 100.0, "C": 80.0})
    p_lookback = pd.Series({"A": 100.0, "B": 100.0, "C": 100.0})

    mom = calculate_momentum(p_calc, p_lookback)

    assert np.isclose(mom["A"], 0.20)
    assert np.isclose(mom["B"], 0.00)
    assert np.isclose(mom["C"], -0.20)


def test_momentum_ranking_order_synthetic():
    """Verify descending ranking order: Rank 1 = highest momentum."""
    mom = pd.Series({
        "STOCK_LOW": -0.15,
        "STOCK_MID": 0.05,
        "STOCK_HIGH": 0.40,
        "STOCK_SUPER": 1.20,
    })

    ranks = rank_momentum(mom)

    assert ranks["STOCK_SUPER"] == 1.0
    assert ranks["STOCK_HIGH"] == 2.0
    assert ranks["STOCK_MID"] == 3.0
    assert ranks["STOCK_LOW"] == 4.0


def test_momentum_deterministic_tie_breaking():
    """Verify stable tie-breaking when two stocks have identical momentum."""
    mom = pd.Series({"ZETA": 0.10, "ALPHA": 0.10, "BETA": 0.20})

    ranks = rank_momentum(mom)

    assert ranks["BETA"] == 1.0
    # Because of deterministic alphabetical secondary sort:
    assert ranks["ALPHA"] == 2.0
    assert ranks["ZETA"] == 3.0


def test_momentum_non_positive_prices():
    """Verify exception on non-positive prices."""
    with pytest.raises(ValueError, match="Non-positive prices"):
        calculate_momentum(pd.Series({"A": -10.0}), pd.Series({"A": 100.0}))

    with pytest.raises(ValueError, match="Non-positive prices"):
        calculate_momentum(pd.Series({"A": 10.0}), pd.Series({"A": 0.0}))
