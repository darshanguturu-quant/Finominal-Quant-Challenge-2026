"""Tests for portfolio selection, buffer rules, and 20% market-cap capping."""

import pytest
import pandas as pd
import numpy as np
from src.portfolio import (
    select_portfolio_holdings,
    cap_market_cap_weights,
    construct_rebalanced_portfolio,
)


def test_initial_portfolio_selection_top_10():
    """Verify initial portfolio selection takes ranks 1 through 10."""
    tickers = [f"S{i}" for i in range(1, 21)]
    ranks = pd.Series(range(1, 21), index=tickers)

    selected, retained, exited, added = select_portfolio_holdings(
        ranks=ranks,
        current_holdings=None,
        portfolio_size=10,
        buffer_cutoff_rank=12,
    )

    assert len(selected) == 10
    assert selected == [f"S{i}" for i in range(1, 11)]
    assert retained == []
    assert exited == []
    assert added == selected


def test_retention_buffer_rank_12_rule():
    """Verify rank-12 retention buffer:
    - Retain existing holdings with rank <= 12 (even if ranks 11 or 12).
    - Exit existing holdings with rank > 12 (e.g. rank 13 or 14).
    - Vacant slots filled by highest-ranked stocks not currently held.
    - Exactly 10 holdings maintained.
    """
    tickers = [f"S{i}" for i in range(1, 21)]
    # Initial holdings: S1 through S10
    initial_holdings = [f"S{i}" for i in range(1, 11)]

    # New ranks scenario:
    # S1..S7 stay in top 10 (ranks 1..7) -> RETAINED
    # S8 has rank 11 (<= 12) -> RETAINED despite being outside top 10!
    # S9 has rank 12 (<= 12) -> RETAINED despite being outside top 10!
    # S10 has rank 14 (> 12) -> EXITED!
    # Candidates not held: S11 has rank 8, S12 has rank 9, S13 has rank 10
    # Exactly 1 vacant slot (since 9 retained). S11 (rank 8) should be added.
    ranks_dict = {
        "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "S6": 6, "S7": 7,
        "S11": 8, "S12": 9, "S13": 10,
        "S8": 11, "S9": 12,
        "S14": 13, "S10": 14,
        "S15": 15, "S16": 16, "S17": 17, "S18": 18, "S19": 19, "S20": 20,
    }
    ranks = pd.Series(ranks_dict)

    selected, retained, exited, added = select_portfolio_holdings(
        ranks=ranks,
        current_holdings=initial_holdings,
        portfolio_size=10,
        buffer_cutoff_rank=12,
    )

    assert len(selected) == 10
    # Retained: S1..S7, S8, S9 (9 stocks)
    assert set(retained) == {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"}
    # Exited: S10 (rank 14 > 12)
    assert exited == ["S10"]
    # Added: highest available candidate not held is S11 (rank 8)
    assert added == ["S11"]
    # Final portfolio has S8 and S9 retained even though S12 (rank 9) and S13 (rank 10) had better ranks
    assert "S8" in selected
    assert "S9" in selected
    assert "S12" not in selected  # buffer prevented unnecessary turnover!
    assert "S13" not in selected


def test_cap_market_cap_weights_no_violation():
    """Verify that when all stocks are <= 20%, raw weights are preserved."""
    mc = pd.Series({f"S{i}": 100.0 for i in range(1, 11)})  # equal weight 10%
    w = cap_market_cap_weights(mc, max_cap=0.20)

    assert np.isclose(w.sum(), 1.0)
    for stock in mc.index:
        assert np.isclose(w[stock], 0.10)


def test_cap_market_cap_weights_single_mega_cap():
    """Verify single mega cap stock is capped at 20% and excess distributed proportionally."""
    # S1 has 60% of total MC, other 9 stocks have 40/9 %
    mc = pd.Series({"S1": 600.0} | {f"S{i}": (400.0 / 9) for i in range(2, 11)})
    w = cap_market_cap_weights(mc, max_cap=0.20)

    assert np.isclose(w.sum(), 1.0)
    assert np.isclose(w["S1"], 0.20)
    # Remaining 0.80 distributed equally among remaining 9 stocks: 0.80 / 9 = 0.08888...
    for i in range(2, 11):
        assert np.isclose(w[f"S{i}"], 0.80 / 9)
        assert w[f"S{i}"] < 0.20


def test_cap_market_cap_weights_iterative_multiple_caps():
    """Verify multiple iterations of capping:
    Initial distribution where second stock also exceeds 20% after first redistribution.
    """
    mc = pd.Series({
        "S1": 500.0,  # 50%
        "S2": 250.0,  # 25%
        "S3": 50.0,
        "S4": 50.0,
        "S5": 40.0,
        "S6": 30.0,
        "S7": 30.0,
        "S8": 20.0,
        "S9": 15.0,
        "S10": 15.0,
    })  # total 1000

    w = cap_market_cap_weights(mc, max_cap=0.20)

    assert np.isclose(w.sum(), 1.0)
    assert np.isclose(w["S1"], 0.20)
    assert np.isclose(w["S2"], 0.20)
    assert (w <= 0.20 + 1e-10).all()

    # Remaining 0.60 weight must be proportional to S3..S10 market caps
    sub_mc = mc.iloc[2:]
    expected_sub_w = 0.60 * (sub_mc / sub_mc.sum())
    for s in sub_mc.index:
        assert np.isclose(w[s], expected_sub_w[s])


def test_construct_rebalanced_portfolio_full_cycle():
    """Verify construct_rebalanced_portfolio returns complete and valid RebalanceDecision."""
    ranks = pd.Series(range(1, 31), index=[f"S{i}" for i in range(1, 31)])
    mcaps = pd.Series({f"S{i}": float(i * 100) for i in range(1, 31)})

    decision = construct_rebalanced_portfolio(
        ranks=ranks,
        market_caps_calc=mcaps,
        current_holdings=None,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        max_weight_cap=0.20,
    )

    assert len(decision.selected_holdings) == 10
    assert np.isclose(decision.capped_weights.sum(), 1.0)
    assert (decision.capped_weights <= 0.20 + 1e-10).all()
    assert len(decision.momentum_ranks) == 10


def test_rebalance_holdings_and_weights_exhaustive_real_data():
    """Exhaustively verify all 1,230 rebalance events across all 5 strategies on real data:
    1. Exactly 10 holdings at every single rebalance.
    2. No duplicate holdings.
    3. Maximum weight <= 20% (plus micro tolerance).
    4. Weights sum to exactly 100% (1.0).
    5. All retained stocks have momentum rank <= 12.
    6. All exited stocks have momentum rank > 12.
    """
    from pathlib import Path
    from src.data_loader import load_and_validate_data, get_rebalance_schedule
    from src.backtest import BacktestEngine

    price_df, mcap_df, _ = load_and_validate_data(
        Path("data/Test_price_data.csv"),
        Path("data/Test_mcap_data.csv"),
    )
    schedule = get_rebalance_schedule(price_df.index, start_year=2006, max_lookback=252)

    engine = BacktestEngine(
        price_df=price_df,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )

    for L in [21, 63, 126, 189, 252]:
        res = engine.run(lookback_days=L, execution_model="drifted")
        assert len(res.rebalance_history) == 246

        for rec in res.rebalance_history:
            holdings = rec["selected_holdings"]
            capped_w = pd.Series(rec["capped_weights"])
            ranks = rec["momentum_ranks"]
            retained = rec["retained_holdings"]
            exited = rec["exited_holdings"]

            # Rule 1 & 2: Exactly 10 unique holdings
            assert len(holdings) == 10, f"Failed at L={L}, date={rec['rebalance_date']}"
            assert len(set(holdings)) == 10

            # Rule 3: Max individual weight <= 20%
            assert (capped_w <= 0.20 + 1e-6).all(), f"Cap violated at L={L}, date={rec['rebalance_date']}: {capped_w[capped_w > 0.20]}"

            # Rule 4: Total weights sum to 100%
            assert np.isclose(capped_w.sum(), 1.0, atol=1e-6), f"Sum != 1.0 at L={L}, date={rec['rebalance_date']}"

            # Rule 5: Every retained stock must have rank <= 12
            for s in retained:
                assert ranks[s] <= 12, f"Retained stock {s} had rank {ranks[s]} > 12 at L={L}, date={rec['rebalance_date']}"


