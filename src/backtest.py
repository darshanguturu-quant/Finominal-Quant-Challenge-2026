"""Backtesting engine for Finominal Quant Challenge 2026.

Implements daily backtesting with strict execution timing:
- Rebalance Date (T_reb): First trading day of each month.
- Calculation Date (T_calc): Immediately preceding trading day.
- Signals and weights calculated strictly on T_calc.
- Trades executed at market close of T_reb.
- Existing holdings earn returns up to T_reb close.
- New weights effective after close of T_reb, applying to subsequent days.
- Zero look-ahead bias.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.data_loader import RebalanceEvent
from src.momentum import calculate_momentum, rank_momentum
from src.portfolio import construct_rebalanced_portfolio, RebalanceDecision


@dataclass
class BacktestResult:
    """Complete results from a backtest execution."""
    lookback_days: int
    execution_model: str
    dates: pd.DatetimeIndex
    daily_returns: pd.Series
    portfolio_values: pd.Series
    rebalance_history: List[Dict]
    daily_holdings: Dict[pd.Timestamp, List[str]]
    daily_weights: pd.DataFrame


class BacktestEngine:
    """Backtesting engine executing monthly-rebalanced momentum strategy."""

    def __init__(
        self,
        price_df: pd.DataFrame,
        mcap_df: pd.DataFrame,
        schedule: List[RebalanceEvent],
        portfolio_size: int = 10,
        buffer_cutoff_rank: int = 12,
        weight_cap: float = 0.20,
    ):
        """Initialize backtest engine with clean datasets and rebalance schedule.

        Args:
            price_df: Daily closing prices indexed by pd.DatetimeIndex.
            mcap_df: Daily market caps indexed by pd.DatetimeIndex.
            schedule: List of RebalanceEvent objects.
            portfolio_size: Number of stocks to hold (10).
            buffer_cutoff_rank: Retention rank threshold (12).
            weight_cap: Maximum stock weight (0.20).
        """
        self.price_df = price_df
        self.mcap_df = mcap_df
        self.schedule = schedule
        self.portfolio_size = portfolio_size
        self.buffer_cutoff_rank = buffer_cutoff_rank
        self.weight_cap = weight_cap

        # Precompute schedule lookups
        self.reb_indices = {event.reb_index: event for event in schedule}
        self.reb_dates = {event.reb_date: event for event in schedule}

    def run(
        self,
        lookback_days: int,
        execution_model: str = "drifted",
        include_day_zero: bool = False,
    ) -> BacktestResult:
        """Execute independent backtest for a specific lookback period.

        Args:
            lookback_days: Momentum lookback L in exact trading days.
            execution_model: 'drifted' (buy-and-hold within month, realistic)
                             or 'fixed' (constant daily weight rebalancing).
            include_day_zero: If True, includes first trading day (2006-01-02)
                              with return 0.0 (holding cash prior to close).
                              If False, daily return series begins on first active day.

        Returns:
            BacktestResult object containing performance series and full audit logs.
        """
        if not self.schedule:
            raise ValueError("Rebalance schedule is empty.")

        # Backtest starts at first rebalance date (first trading day of 2006)
        first_event = self.schedule[0]
        start_idx = first_event.reb_index
        total_days = len(self.price_df)

        current_holdings: Optional[List[str]] = None
        current_weights: Optional[pd.Series] = None
        current_shares: Optional[pd.Series] = None

        portfolio_val = 1.0  # Normalized initial capital
        daily_dates: List[pd.Timestamp] = []
        daily_returns: List[float] = []
        portfolio_values: List[float] = []
        rebalance_records: List[Dict] = []
        daily_holdings: Dict[pd.Timestamp, List[str]] = {}
        daily_weights_list: List[Dict] = []

        for t in range(start_idx, total_days):
            current_date = self.price_df.index[t]

            # ------------------------------------------------------------------
            # Phase 1: Morning to Close - Existing portfolio earns return
            # ------------------------------------------------------------------
            if t == start_idx:
                # First day of backtest (2006-01-02):
                # No portfolio was held prior to execution at today's close.
                if include_day_zero:
                    daily_dates.append(current_date)
                    daily_returns.append(0.0)
                    portfolio_values.append(portfolio_val)
                    daily_holdings[current_date] = []
                    daily_weights_list.append({"date": current_date})
            else:
                # Active trading day: calculate portfolio return from close(t-1) to close(t)
                prev_date = self.price_df.index[t - 1]

                if execution_model == "drifted":
                    # Value at today's close before any rebalancing
                    p_t = self.price_df.iloc[t][current_shares.index].astype(float)
                    p_prev = self.price_df.iloc[t - 1][current_shares.index].astype(float)

                    val_today = float((current_shares * p_t).sum())
                    val_yesterday = float((current_shares * p_prev).sum())
                    day_return = (val_today / val_yesterday) - 1.0
                    portfolio_val = val_today
                else:  # 'fixed'
                    p_t = self.price_df.iloc[t][current_weights.index].astype(float)
                    p_prev = self.price_df.iloc[t - 1][current_weights.index].astype(float)
                    stock_returns = (p_t / p_prev) - 1.0
                    day_return = float((current_weights * stock_returns).sum())
                    portfolio_val = portfolio_val * (1.0 + day_return)

                daily_dates.append(current_date)
                daily_returns.append(day_return)
                portfolio_values.append(portfolio_val)
                daily_holdings[current_date] = list(current_holdings)

                # Record daily weights
                if execution_model == "drifted":
                    p_t = self.price_df.iloc[t][current_shares.index].astype(float)
                    cur_drift_w = (current_shares * p_t) / portfolio_val
                    weight_row = {"date": current_date}
                    weight_row.update(cur_drift_w.to_dict())
                    daily_weights_list.append(weight_row)
                else:
                    weight_row = {"date": current_date}
                    weight_row.update(current_weights.to_dict())
                    daily_weights_list.append(weight_row)

            # ------------------------------------------------------------------
            # Phase 2: Market Close - Execute Rebalance if t is a Rebalance Date
            # ------------------------------------------------------------------
            if t in self.reb_indices:
                event = self.reb_indices[t]
                calc_idx = event.calc_index

                # 1. Calculate momentum strictly on T_calc
                p_calc = self.price_df.iloc[calc_idx].astype(float)
                p_lookback = self.price_df.iloc[calc_idx - lookback_days].astype(float)
                mom = calculate_momentum(p_calc, p_lookback)
                ranks = rank_momentum(mom)

                # 2. Market caps strictly on T_calc
                mc_calc = self.mcap_df.iloc[calc_idx].astype(float)

                # 3. Apply selection & buffer logic and 20% capping
                decision: RebalanceDecision = construct_rebalanced_portfolio(
                    ranks=ranks,
                    market_caps_calc=mc_calc,
                    current_holdings=current_holdings,
                    portfolio_size=self.portfolio_size,
                    buffer_cutoff_rank=self.buffer_cutoff_rank,
                    max_weight_cap=self.weight_cap,
                )

                # 4. Execute trades at today's close prices
                p_exec = self.price_df.iloc[t][decision.selected_holdings].astype(float)
                current_holdings = decision.selected_holdings
                current_weights = decision.capped_weights

                # Rigorous weight validation at every rebalance event
                if len(decision.selected_holdings) != self.portfolio_size:
                    raise ValueError(
                        f"Expected {self.portfolio_size} holdings on {current_date}, got {len(decision.selected_holdings)}"
                    )
                if (decision.capped_weights > self.weight_cap + 1e-6).any():
                    violators = decision.capped_weights[decision.capped_weights > self.weight_cap + 1e-6]
                    raise ValueError(f"Weight cap violated on {current_date}:\n{violators}")
                if not np.isclose(decision.capped_weights.sum(), 1.0, atol=1e-6):
                    raise ValueError(
                        f"Weights sum to {decision.capped_weights.sum():.8f} (!= 1.0) on {current_date}"
                    )

                # Target share allocation at today's close
                current_shares = (portfolio_val * current_weights) / p_exec

                # Audit record
                rebalance_records.append({
                    "rebalance_date": current_date,
                    "calculation_date": event.calc_date,
                    "selected_holdings": current_holdings,
                    "retained_holdings": decision.retained_holdings,
                    "exited_holdings": decision.exited_holdings,
                    "added_holdings": decision.added_holdings,
                    "raw_weights": decision.raw_weights.to_dict(),
                    "capped_weights": decision.capped_weights.to_dict(),
                    "momentum_ranks": decision.momentum_ranks.to_dict(),
                    "portfolio_value_at_rebalance": portfolio_val,
                })

        # Assemble final result containers
        s_returns = pd.Series(daily_returns, index=pd.DatetimeIndex(daily_dates), name="portfolio_return")
        s_values = pd.Series(portfolio_values, index=pd.DatetimeIndex(daily_dates), name="portfolio_value")
        df_weights = pd.DataFrame(daily_weights_list).set_index("date").fillna(0.0)

        return BacktestResult(
            lookback_days=lookback_days,
            execution_model=execution_model,
            dates=pd.DatetimeIndex(daily_dates),
            daily_returns=s_returns,
            portfolio_values=s_values,
            rebalance_history=rebalance_records,
            daily_holdings=daily_holdings,
            daily_weights=df_weights,
        )

