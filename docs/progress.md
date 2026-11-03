# Finominal Quant Challenge 2026 – Project Progress Log

## Phase 1: Environment Setup & Dataset Verification
- Inspected workspace and official PDF assignment (`Finominal_Quant Challenge_2026 06.pdf`).
- Loaded and audited `Test_price_data.csv` and `Test_mcap_data.csv`.
- Discovered and addressed date format heterogeneity (`%d-%m-%Y` in price data vs. `%Y-%m-%d` in market cap data).
- Verified 5,337 aligned rows, 30 tickers, 0 missing values, and strictly positive prices and market caps.
- Documented findings in `docs/data_findings.md`.

## Phase 2: Momentum Calculation & Ranking (`src/momentum.py`)
- Implemented pure function `calculate_momentum` matching exact formula $M_i = (P_{calc} / P_{lookback}) - 1$.
- Implemented `rank_momentum` for descending ranking with deterministic tie-breaking.
- Covered with unit tests verifying exact formula, ranking order, and error handling.

## Phase 3: Portfolio Selection & 20% Capping Algorithm (`src/portfolio.py`)
- Implemented `select_portfolio_holdings` with rank-12 retention buffer:
  - Existing holdings ranked <= 12 retained.
  - Existing holdings ranked > 12 exited.
  - Vacant positions filled by highest-ranked available stocks.
  - Exactly 10 holdings asserted at all times.
- Implemented iterative 20% weight capping algorithm:
  - Caps violating stocks at exactly 20%.
  - Collects excess weight $E = \sum (w_{orig} - 0.20)$.
  - Redistributes excess proportionally based on relative market caps of uncapped stocks.
  - Iterates until all weights <= 20% and sum equals 100%.
- Covered with comprehensive unit tests for equal weights, single mega-cap, and multi-cap cascades.

## Phase 4: Backtest Engine Architecture (`src/backtest.py`)
- Built `BacktestEngine` with zero look-ahead bias and strict execution timing:
  - Signals calculated at close of $T_{calc}$.
  - Trades executed at market close of $T_{reb}$.
  - Existing holdings earn returns up to $T_{reb}$ close.
  - New target weights become effective for subsequent intervals.
- Supports drifted share-tracking execution (realistic buy-and-hold within month).
- Audits full rebalance history and daily portfolio weights.

## Phase 5: Quantitative Metrics & Analytics (`src/metrics.py`)
- Implemented annualized Sharpe ratio with sample standard deviation (`ddof=1`) and $\sqrt{252}$ scaling.
- Implemented Cumulative Return and CAGR using exact observation counts.
- Implemented drawdown and Calmar ratio analytics.
- Validated with analytical hand calculations in unit tests.

## Phase 6: Automated Testing Suite (`tests/`)
- Created 21 automated unit tests across 5 test modules.
- Executed `pytest` with 100% pass rate (21/21 passed).
- Verified look-ahead bias prevention by perturbing future prices.

## Phase 7: Production Pipeline Execution (`main.py`, `results/`)
- Executed full backtest pipeline for lookback periods: 21, 63, 126, 189, 252 days.
- Identified **189 Days** as the optimal lookback period:
  - Annualized Sharpe Ratio: **1.4532**
  - Cumulative Return: **187,313,822.26%**
  - CAGR: **104.63%**
- Generated summary CSVs, daily returns, portfolio holdings audit, and 4 high-resolution charts.

## Phase 8: Final Submission & Documentation
- Authored professional `README.md` with complete mathematical descriptions, installation instructions, results, and critical assessment.
- Prepared 3–5-minute Loom presentation script.
