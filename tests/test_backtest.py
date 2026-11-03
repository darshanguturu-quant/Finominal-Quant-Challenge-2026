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


def test_portfolio_holdings_export_csv_schema_and_integrity():
    """Verify that results/portfolio_holdings.csv satisfies all challenge requirements:
    1. Contains exact columns: lookback_days, rebalance_date, stock, momentum_rank, portfolio_weight.
    2. Contains exactly 12,300 rows (5 lookbacks * 246 rebalances * 10 holdings).
    3. Has zero missing values.
    4. All weights are > 0 and <= 0.20 + 1e-6.
    5. All ranks are between 1 and 12.
    """
    from pathlib import Path
    csv_path = Path("results/portfolio_holdings.csv")
    assert csv_path.exists(), "results/portfolio_holdings.csv does not exist. Run main.py first."

    df = pd.read_csv(csv_path)

    # Required columns
    required_cols = ["lookback_days", "rebalance_date", "stock", "momentum_rank", "portfolio_weight"]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Row count: 5 * 246 * 10 = 12,300
    assert len(df) == 12300, f"Expected 12,300 rows, got {len(df)}"

    # Zero nulls
    assert not df[required_cols].isna().any().any(), "Found null values in holdings export."

    # Weight constraints
    assert (df["portfolio_weight"] > 0).all(), "Found non-positive weights."
    assert (df["portfolio_weight"] <= 0.20 + 1e-6).all(), "Found weights exceeding 20% cap."

    # Rank constraints (must be in top 12 due to retention buffer and selection)
    assert (df["momentum_rank"] >= 1.0).all()
    assert (df["momentum_rank"] <= 12.0).all()

    # Per-rebalance weight sums must equal 1.0
    weight_sums = df.groupby(["lookback_days", "rebalance_date"])["portfolio_weight"].sum()
    assert np.isclose(weight_sums, 1.0, atol=1e-5).all()

    # Per-rebalance holding counts must equal exactly 10
    holding_counts = df.groupby(["lookback_days", "rebalance_date"])["stock"].count()
    assert (holding_counts == 10).all()


def test_performance_validation_recalculation_and_optimal():
    """Directly recalculate Sharpe, CR, and CAGR from daily_returns.csv:
    1. Annualized Sharpe = (mean / sample_std) * sqrt(252).
    2. Cumulative Return = prod(1 + R) - 1.
    3. CAGR = (1 + CR)**(252 / N) - 1.
    4. Programmatically confirm 189 days is optimal lookback.
    """
    from pathlib import Path
    from src.metrics import (
        calculate_annualized_sharpe_ratio,
        calculate_cumulative_return,
        calculate_cagr,
    )

    returns_path = Path("results/daily_returns.csv")
    assert returns_path.exists(), "results/daily_returns.csv missing. Run main.py first."

    df_rets = pd.read_csv(returns_path)
    sharpes = {}

    for L in [21, 63, 126, 189, 252]:
        col = f"return_L{L}"
        assert col in df_rets.columns
        rets = df_rets[col].values

        sr = calculate_annualized_sharpe_ratio(rets)
        cr = calculate_cumulative_return(rets)
        cagr = calculate_cagr(cr, len(rets))

        sharpes[L] = sr
        assert not np.isnan(sr)
        assert cr > 0
        assert cagr > 0

    # Programmatic optimal check
    optimal_L = max(sharpes, key=sharpes.get)
    assert optimal_L == 189, f"Expected 189 days as optimal lookback, got {optimal_L}"
    assert np.isclose(sharpes[189], 1.4532, atol=1e-3)


