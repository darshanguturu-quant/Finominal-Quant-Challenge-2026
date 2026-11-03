"""Portfolio selection, buffer rules, and 20% market-cap capping algorithm.

Strictly adheres to Section 4 of the Finominal Quant Challenge specification:
- Portfolio holds exactly 10 stocks.
- Retention buffer: existing holdings ranked <= 12 are retained; ranked > 12 are exited.
- Vacant slots filled by highest-ranked available stocks.
- Market-cap weighting with iterative 20% capping and redistribution.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np


@dataclass
class RebalanceDecision:
    """Record of portfolio transition decisions at a rebalance date."""
    selected_holdings: List[str]
    retained_holdings: List[str]
    exited_holdings: List[str]
    added_holdings: List[str]
    raw_weights: pd.Series
    capped_weights: pd.Series


def select_portfolio_holdings(
    ranks: pd.Series,
    current_holdings: Optional[List[str]] = None,
    portfolio_size: int = 10,
    buffer_cutoff_rank: int = 12,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Apply the 10-stock selection logic with rank-12 retention buffer.

    Sequence:
    1. Evaluate: Check new momentum ranks of existing portfolio stocks.
    2. Exit: Remove any existing portfolio stock if its new rank is > 12.
    3. Retain: Keep any existing portfolio stock if its new rank is <= 12.
    4. Addition: Fill all vacant slots (to reach exactly 10 stocks) with
       the highest-ranked stocks not currently held in the portfolio.
    5. Verify exactly 10 holdings.

    Args:
        ranks: pd.Series of momentum ranks (Rank 1 = highest momentum).
        current_holdings: List of stock tickers currently held, or None/empty for initial formation.
        portfolio_size: Target portfolio size (must be exactly 10).
        buffer_cutoff_rank: Retention rank threshold (default 12).

    Returns:
        Tuple of (selected_10, retained, exited, added)

    Raises:
        ValueError: If fewer than portfolio_size stocks are available or invalid inputs.
    """
    if len(ranks) < portfolio_size:
        raise ValueError(
            f"Universe has only {len(ranks)} stocks, but target portfolio size is {portfolio_size}."
        )

    # Initial formation (no prior holdings)
    if not current_holdings:
        top_stocks = ranks.sort_values(ascending=True).head(portfolio_size).index.tolist()
        if len(top_stocks) != portfolio_size:
            raise ValueError(f"Failed to select {portfolio_size} stocks for initial portfolio.")
        return top_stocks, [], [], top_stocks

    # Step 1 & 2 & 3: Evaluate, Exit, Retain
    retained: List[str] = []
    exited: List[str] = []

    for stock in current_holdings:
        if stock not in ranks.index:
            exited.append(stock)
            continue
        stock_rank = ranks[stock]
        if stock_rank <= buffer_cutoff_rank:
            retained.append(stock)
        else:
            exited.append(stock)

    # Step 4: Addition - Fill vacant slots with highest-ranked stocks not held
    vacant_slots = portfolio_size - len(retained)
    if vacant_slots < 0:
        raise ValueError(f"Retained stocks ({len(retained)}) exceeds portfolio size ({portfolio_size}).")

    added: List[str] = []
    if vacant_slots > 0:
        sorted_candidates = ranks.sort_values(ascending=True).index
        for candidate in sorted_candidates:
            if candidate not in retained:
                added.append(candidate)
                if len(added) == vacant_slots:
                    break

        if len(added) < vacant_slots:
            raise ValueError(
                f"Could not find enough candidates to fill {vacant_slots} vacant slots."
            )

    selected = retained + added

    # Step 5: Verify exactly portfolio_size holdings
    if len(selected) != portfolio_size:
        raise ValueError(
            f"Portfolio selection failed: expected exactly {portfolio_size} holdings, got {len(selected)}."
        )
    if len(set(selected)) != portfolio_size:
        raise ValueError("Selected portfolio contains duplicate stock tickers.")

    return selected, retained, exited, added


def cap_market_cap_weights(
    market_caps: pd.Series,
    max_cap: float = 0.20,
    tolerance: float = 1e-10,
    max_iterations: int = 100,
) -> pd.Series:
    """Calculate market-cap weights and iteratively enforce the 20% maximum weight constraint.

    Algorithm (Official Specification):
    1. Initial Weight: w_{i, raw} = MC_{i, T_calc} / sum_{j=1}^10 MC_{j, T_calc}
    2. Capping & Scaling:
       a. Cap any stock where w_i > 0.20 at exactly 0.20.
       b. Calculate total excess weight: E = sum(w_original - 0.20) from capped stocks.
       c. Distribute E among remaining uncapped stocks proportionally based on relative MC.
       d. Repeat until no single stock's weight exceeds 0.20 and sum equals 1.00 (100%).

    Args:
        market_caps: pd.Series of positive market capitalizations for the selected stocks.
        max_cap: Maximum individual stock weight (0.20 = 20%).
        tolerance: Numerical tolerance for convergence and sum checks.
        max_iterations: Safety ceiling for iteration count.

    Returns:
        pd.Series of capped weights summing to 1.00.

    Raises:
        ValueError: If market_caps are non-positive, empty, or cannot satisfy constraint.
    """
    if len(market_caps) == 0:
        raise ValueError("Market caps series cannot be empty.")
    if (market_caps <= 0).any():
        bad = market_caps[market_caps <= 0]
        raise ValueError(f"Non-positive market caps found:\n{bad}")

    n_stocks = len(market_caps)
    min_possible_cap = 1.0 / n_stocks
    if max_cap < min_possible_cap - tolerance:
        raise ValueError(
            f"Impossible constraint: max_cap={max_cap:.4f} is less than equal-weight minimum 1/{n_stocks}={min_possible_cap:.4f}"
        )

    # Initial raw weights
    total_mcap = market_caps.sum()
    weights = (market_caps / total_mcap).astype(float).copy()

    # If no stock violates the cap, return immediately
    if (weights <= max_cap + tolerance).all():
        return weights / weights.sum()

    capped_mask = pd.Series(False, index=weights.index)

    for _ in range(max_iterations):
        # Identify newly violating stocks among currently uncapped stocks
        violating = (~capped_mask) & (weights > max_cap + tolerance)
        if not violating.any():
            break

        # Calculate excess collected from newly capped stocks
        excess = 0.0
        for stock in weights.index[violating]:
            excess += (weights[stock] - max_cap)
            weights[stock] = max_cap
            capped_mask[stock] = True

        uncapped = ~capped_mask
        if not uncapped.any():
            # All stocks capped (can only happen if n_stocks * max_cap == 1.0)
            break

        # Distribute E among remaining uncapped stocks proportionally based on relative market caps
        uncapped_mcap_sum = market_caps[uncapped].sum()
        if uncapped_mcap_sum <= 0:
            raise ValueError("Remaining uncapped stocks have non-positive total market cap.")

        mcap_proportions = market_caps[uncapped] / uncapped_mcap_sum
        weights[uncapped] += excess * mcap_proportions

    # Validate output
    sum_weights = weights.sum()
    if not np.isclose(sum_weights, 1.0, atol=1e-5):
        # Final numerical normalization if microscopic floating point residue remains
        weights = weights / sum_weights

    # Programmatic assertions
    if (weights > max_cap + 1e-5).any():
        bad = weights[weights > max_cap + 1e-5]
        raise ValueError(f"Weight capping failed; some stocks exceed cap:\n{bad}")
    if (weights < 0).any():
        raise ValueError("Negative weights generated by capping algorithm.")
    if not np.isclose(weights.sum(), 1.0, atol=1e-5):
        raise ValueError(f"Final weights do not sum to 1.0 (sum={weights.sum()})")

    return weights


def construct_rebalanced_portfolio(
    ranks: pd.Series,
    market_caps_calc: pd.Series,
    current_holdings: Optional[List[str]] = None,
    portfolio_size: int = 10,
    buffer_cutoff_rank: int = 12,
    max_weight_cap: float = 0.20,
) -> RebalanceDecision:
    """Execute complete portfolio selection and weighting on calculation date data.

    Args:
        ranks: Momentum ranks on T_calc.
        market_caps_calc: Market capitalizations on T_calc.
        current_holdings: Current portfolio holdings, or None for initial rebalance.
        portfolio_size: Target portfolio size (10).
        buffer_cutoff_rank: Retention buffer cutoff rank (12).
        max_weight_cap: Maximum weight cap (0.20).

    Returns:
        RebalanceDecision object with complete audit trail.
    """
    selected, retained, exited, added = select_portfolio_holdings(
        ranks=ranks,
        current_holdings=current_holdings,
        portfolio_size=portfolio_size,
        buffer_cutoff_rank=buffer_cutoff_rank,
    )

    selected_mcaps = market_caps_calc[selected].astype(float)
    raw_weights = selected_mcaps / selected_mcaps.sum()
    capped_weights = cap_market_cap_weights(
        market_caps=selected_mcaps,
        max_cap=max_weight_cap,
    )

    return RebalanceDecision(
        selected_holdings=selected,
        retained_holdings=retained,
        exited_holdings=exited,
        added_holdings=added,
        raw_weights=raw_weights,
        capped_weights=capped_weights,
    )
