"""Tests for backtesting engine and look-ahead bias validation."""

import pytest
import pandas as pd
import numpy as np
from src.data_loader import RebalanceEvent
from src.backtest import BacktestEngine


def make_synthetic_market_data(n_days=300, n_stocks=15):
    """Generate clean synthetic price and mcap data for engine testing."""
    dates = pd.date_range("2005-01-01", periods=n_days, freq="B")
    tickers = [f"STK_{i:02d}" for i in range(1, n_stocks + 1)]

    # Deterministic price series
    np.random.seed(42)
    daily_rets = np.random.normal(0.0005, 0.015, size=(n_days, n_stocks))
    price_matrix = 100.0 * np.cumprod(1.0 + daily_rets, axis=0)
    mcap_matrix = price_matrix * 1_000_000.0

    price_df = pd.DataFrame(price_matrix, index=dates, columns=tickers)
    mcap_df = pd.DataFrame(mcap_matrix, index=dates, columns=tickers)

    # Schedule: monthly rebalances
    df_dates = pd.DataFrame({"date": dates, "index": np.arange(len(dates))})
    df_dates["ym"] = dates.to_period("M")
    monthly_firsts = df_dates.groupby("ym").first().reset_index()

    # Drop first month to allow lookback
    eligible = monthly_firsts.iloc[2:].copy()
    schedule = []
    for _, row in eligible.iterrows():
        idx = int(row["index"])
        schedule.append(
            RebalanceEvent(
                reb_date=row["date"],
                reb_index=idx,
                calc_date=dates[idx - 1],
                calc_index=idx - 1,
            )
        )

    return price_df, mcap_df, schedule


def test_backtest_engine_synthetic_run():
    """Verify engine runs without error, generates 10 holdings, and valid returns."""
    price_df, mcap_df, schedule = make_synthetic_market_data(n_days=150, n_stocks=15)

    engine = BacktestEngine(
        price_df=price_df,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )

    res = engine.run(lookback_days=21, execution_model="drifted")

    assert len(res.daily_returns) > 0
    assert not res.daily_returns.isna().any()
    assert (res.portfolio_values > 0).all()

    # Verify all rebalance records have exactly 10 holdings
    for record in res.rebalance_history:
        assert len(record["selected_holdings"]) == 10
        weights = pd.Series(record["capped_weights"])
        assert len(weights) == 10
        assert np.isclose(weights.sum(), 1.0)
        assert (weights <= 0.20 + 1e-6).all()


def test_no_look_ahead_bias_validation():
    """Strict test to prove signals and weights do NOT use prices from T_reb or future.

    We alter the prices on T_reb and after T_reb in a copy of the dataset.
    The portfolio selection decisions (holdings and weights) on T_reb MUST be 100% identical.
    """
    price_df, mcap_df, schedule = make_synthetic_market_data(n_days=150, n_stocks=15)

    engine_clean = BacktestEngine(
        price_df=price_df,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )
    res_clean = engine_clean.run(lookback_days=21, execution_model="drifted")

    # Now create modified data where prices on and after first rebalance are modified
    price_df_mod = price_df.copy()
    first_reb_idx = schedule[0].reb_index
    # Multiply future prices by 10x
    price_df_mod.iloc[first_reb_idx:] *= 10.0

    engine_mod = BacktestEngine(
        price_df=price_df_mod,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )
    res_mod = engine_mod.run(lookback_days=21, execution_model="drifted")

    # The first rebalance decisions MUST be completely identical because they depend only on T_calc
    clean_first_reb = res_clean.rebalance_history[0]
    mod_first_reb = res_mod.rebalance_history[0]

    assert clean_first_reb["selected_holdings"] == mod_first_reb["selected_holdings"]
    assert clean_first_reb["capped_weights"] == mod_first_reb["capped_weights"]


def test_execution_timing_and_weights_application():
    """Verify that trades executed at T_reb close apply returns starting on day T_reb + 1."""
    price_df, mcap_df, schedule = make_synthetic_market_data(n_days=150, n_stocks=15)

    engine = BacktestEngine(
        price_df=price_df,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )

    res = engine.run(lookback_days=21, execution_model="drifted", include_day_zero=True)

    # Day 0 return must be 0.0 (holding cash prior to close)
    assert res.daily_returns.iloc[0] == 0.0

    # Day 1 return must match the return of the portfolio formed at Day 0 close
    first_reb = res.rebalance_history[0]
    holdings = first_reb["selected_holdings"]
    target_weights = pd.Series(first_reb["capped_weights"])

    day0_date = schedule[0].reb_date
    day1_idx = schedule[0].reb_index + 1
    day1_date = price_df.index[day1_idx]

    p0 = price_df.loc[day0_date, holdings]
    p1 = price_df.loc[day1_date, holdings]
    stock_rets = (p1 / p0) - 1.0
    expected_day1_return = float((target_weights * stock_rets).sum())

    assert np.isclose(res.daily_returns.loc[day1_date], expected_day1_return, atol=1e-7)
