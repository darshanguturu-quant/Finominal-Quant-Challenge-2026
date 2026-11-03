"""Data loader and validation module for Finominal Quant Challenge 2026.

Responsible for:
1. Loading and parsing historical daily closing prices and market capitalization data.
2. Validating date format, date alignment, monotonicity, missing values, and symbol consistency.
3. Identifying monthly rebalance dates (T_reb) and corresponding calculation dates (T_calc).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import pandas as pd
import numpy as np


@dataclass(frozen=True)
class RebalanceEvent:
    """Represents a scheduled monthly rebalance event."""
    reb_date: pd.Timestamp
    reb_index: int
    calc_date: pd.Timestamp
    calc_index: int


def load_and_validate_data(
    price_path: str | Path,
    mcap_path: str | Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Load, parse, and strictly validate price and market capitalization datasets.

    Args:
        price_path: Path to Test_price_data.csv
        mcap_path: Path to Test_mcap_data.csv

    Returns:
        Tuple of (clean_price_df, clean_mcap_df, list_of_tickers)
        Both dataframes are indexed by date (pd.DatetimeIndex) and sorted chronologically.

    Raises:
        ValueError: If dates do not match, columns mismatch, or data contains NaNs/non-positives.
        FileNotFoundError: If either CSV file is missing.
    """
    price_file = Path(price_path)
    mcap_file = Path(mcap_path)

    if not price_file.exists():
        raise FileNotFoundError(f"Price data file not found at: {price_file}")
    if not mcap_file.exists():
        raise FileNotFoundError(f"Market cap data file not found at: {mcap_file}")

    # Load raw CSVs
    raw_price = pd.read_csv(price_file)
    raw_mcap = pd.read_csv(mcap_file)

    if "date" not in raw_price.columns:
        raise ValueError("Price data missing 'date' column.")
    if "date" not in raw_mcap.columns:
        raise ValueError("Market cap data missing 'date' column.")

    # Parse dates explicitly per verified formats:
    # Price data: DD-MM-YYYY (e.g., '03-01-2005')
    # Mcap data:  YYYY-MM-DD (e.g., '2005-01-03')
    price_dates = pd.to_datetime(raw_price["date"], format="%d-%m-%Y")
    mcap_dates = pd.to_datetime(raw_mcap["date"], format="%Y-%m-%d")

    # Verify 1-to-1 date alignment
    if len(price_dates) != len(mcap_dates):
        raise ValueError(
            f"Row count mismatch: price has {len(price_dates)} rows, mcap has {len(mcap_dates)} rows."
        )

    if not (price_dates == mcap_dates).all():
        mismatches = price_dates[price_dates != mcap_dates]
        raise ValueError(f"Date alignment mismatch found at {len(mismatches)} rows.")

    # Verify column sets
    price_tickers = [c for c in raw_price.columns if c != "date"]
    mcap_tickers = [c for c in raw_mcap.columns if c != "date"]

    if price_tickers != mcap_tickers:
        missing_in_mcap = set(price_tickers) - set(mcap_tickers)
        missing_in_price = set(mcap_tickers) - set(price_tickers)
        raise ValueError(
            f"Ticker mismatch between datasets. Missing in mcap: {missing_in_mcap}, missing in price: {missing_in_price}"
        )

    # Build validated DataFrames
    price_df = raw_price[price_tickers].copy()
    price_df.index = price_dates
    price_df.index.name = "date"

    mcap_df = raw_mcap[mcap_tickers].copy()
    mcap_df.index = mcap_dates
    mcap_df.index.name = "date"

    # Ensure chronological sorting
    price_df = price_df.sort_index()
    mcap_df = mcap_df.sort_index()

    # Verify monotonic increasing dates without duplicates
    if not price_df.index.is_monotonic_increasing:
        raise ValueError("Dates are not monotonically increasing.")
    if price_df.index.has_duplicates:
        duplicates = price_df.index[price_df.index.duplicated()].tolist()
        raise ValueError(f"Duplicate dates found in price data: {duplicates}")

    # Numeric conversion & integrity verification
    price_df = price_df.astype(float)
    mcap_df = mcap_df.astype(float)

    if price_df.isna().any().any():
        null_counts = price_df.isna().sum()
        raise ValueError(f"Price data contains NaNs:\n{null_counts[null_counts > 0]}")
    if mcap_df.isna().any().any():
        null_counts = mcap_df.isna().sum()
        raise ValueError(f"Market cap data contains NaNs:\n{null_counts[null_counts > 0]}")

    if (price_df <= 0).any().any():
        bad = (price_df <= 0).sum()
        raise ValueError(f"Price data contains non-positive values:\n{bad[bad > 0]}")
    if (mcap_df <= 0).any().any():
        bad = (mcap_df <= 0).sum()
        raise ValueError(f"Market cap data contains non-positive values:\n{bad[bad > 0]}")

    return price_df, mcap_df, price_tickers


def get_rebalance_schedule(
    dates: pd.DatetimeIndex,
    start_year: int = 2006,
    max_lookback: int = 252,
) -> List[RebalanceEvent]:
    """Generate the full schedule of monthly rebalances starting from start_year.

    Rebalance Date (T_reb): First trading day of each month.
    Calculation Date (T_calc): The trading day immediately preceding T_reb.

    Args:
        dates: Chronologically sorted DatetimeIndex of trading days.
        start_year: The year the backtest begins (default: 2006).
        max_lookback: Maximum lookback period in exact trading days (default: 252).

    Returns:
        List of RebalanceEvent objects containing dates and integer indices.

    Raises:
        ValueError: If insufficient historical data exists prior to the first rebalance date.
    """
    if not dates.is_monotonic_increasing:
        raise ValueError("Dates must be sorted chronologically.")

    df_dates = pd.DataFrame({"date": dates, "index": np.arange(len(dates))})
    df_dates["year_month"] = dates.to_period("M")

    # First trading day of every calendar month
    monthly_firsts = df_dates.groupby("year_month").first().reset_index()

    # Filter for backtest period: start_year onwards
    eligible_reb = monthly_firsts[monthly_firsts["date"].dt.year >= start_year].copy()

    schedule: List[RebalanceEvent] = []
    for _, row in eligible_reb.iterrows():
        reb_idx = int(row["index"])
        reb_date = row["date"]

        # Calculation date is the immediately preceding trading day (integer index reb_idx - 1)
        calc_idx = reb_idx - 1
        if calc_idx < 0:
            raise ValueError(f"No preceding trading day exists before rebalance date {reb_date}")

        calc_date = dates[calc_idx]

        # Verify sufficient history for max lookback
        if calc_idx - max_lookback < 0:
            raise ValueError(
                f"Insufficient historical data for lookback {max_lookback} at calculation date {calc_date} (index {calc_idx})"
            )

        schedule.append(
            RebalanceEvent(
                reb_date=reb_date,
                reb_index=reb_idx,
                calc_date=calc_date,
                calc_index=calc_idx,
            )
        )

    return schedule
