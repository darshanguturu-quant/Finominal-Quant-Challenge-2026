"""Tests for data loading and schedule generation."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.data_loader import load_and_validate_data, get_rebalance_schedule


def test_load_and_validate_real_data():
    """Verify loading and validation on real workspace data files."""
    price_path = Path("data/Test_price_data.csv")
    mcap_path = Path("data/Test_mcap_data.csv")

    price_df, mcap_df, tickers = load_and_validate_data(price_path, mcap_path)

    assert len(tickers) == 30
    assert price_df.shape == (5337, 30)
    assert mcap_df.shape == (5337, 30)
    assert price_df.index.equals(mcap_df.index)
    assert price_df.index[0] == pd.Timestamp("2005-01-03")
    assert price_df.index[-1] == pd.Timestamp("2026-06-24")
    assert not price_df.isna().any().any()
    assert not mcap_df.isna().any().any()
    assert (price_df > 0).all().all()
    assert (mcap_df > 0).all().all()


def test_rebalance_schedule_real_data():
    """Verify monthly rebalance schedule generation on real data."""
    price_path = Path("data/Test_price_data.csv")
    mcap_path = Path("data/Test_mcap_data.csv")

    price_df, _, _ = load_and_validate_data(price_path, mcap_path)
    schedule = get_rebalance_schedule(price_df.index, start_year=2006, max_lookback=252)

    assert len(schedule) == 246  # Jan 2006 through Jun 2026

    # Verify first rebalance event
    first_event = schedule[0]
    assert first_event.reb_date == pd.Timestamp("2006-01-02")
    assert first_event.calc_date == pd.Timestamp("2005-12-30")
    assert first_event.reb_index == 253
    assert first_event.calc_index == 252

    # Verify max lookback check at first calculation date
    assert first_event.calc_index - 252 == 0
    assert price_df.index[first_event.calc_index - 252] == pd.Timestamp("2005-01-03")

    # Verify every calc_date immediately precedes reb_date
    for event in schedule:
        assert event.calc_index == event.reb_index - 1
        assert event.calc_date < event.reb_date


def test_synthetic_data_loader_validations(tmp_path):
    """Test validation failure modes on corrupt synthetic datasets."""
    # Mismatched rows
    p_path = tmp_path / "p.csv"
    m_path = tmp_path / "m.csv"

    p_df = pd.DataFrame({"date": ["03-01-2005", "04-01-2005"], "A": [10.0, 11.0]})
    m_df = pd.DataFrame({"date": ["2005-01-03"], "A": [100.0]})
    p_df.to_csv(p_path, index=False)
    m_df.to_csv(m_path, index=False)

    with pytest.raises(ValueError, match="Row count mismatch"):
        load_and_validate_data(p_path, m_path)

