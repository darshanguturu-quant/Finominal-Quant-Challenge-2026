# Project Assumptions & Methodology Documentation

## 1. Execution & Rebalancing Timeline

- **Rebalance Date ($T_{reb}$)**: The first trading day of each calendar month. Trades to establish target portfolio weights are executed at the market close on this date.
- **Calculation Date ($T_{calc}$)**: The trading day immediately preceding $T_{reb}$ ($T_{calc} = T_{reb} - 1$ in trading-day space).
- **Look-Ahead Bias Prevention**:
  - Momentum scores $M_i$ and market-cap weights $w_{i}$ are strictly derived from prices and market capitalizations on $T_{calc}$.
  - Zero information from $T_{reb}$ or future dates is used in signal generation or portfolio construction.

## 2. Initial Formation & Return Period Conventions

- **Initial Formation Date**: `2006-01-02` (the first trading day of 2006).
- **First Day Return**:
  - Prior to market close of `2006-01-02`, no equity portfolio was held. The portfolio was in cash (return = 0.0).
  - The first active equity portfolio return is observed over the interval from `2006-01-02` close to `2006-01-03` close.
  - Number of active return observations: $N = 5,083$ trading days.
  - If including the cash execution day with return 0.0, $N = 5,084$ trading days. Both metrics are reported with full mathematical transparency.

## 3. Within-Month Portfolio Valuation (Drifted vs. Daily Fixed Weights)

- **Primary Production Model (Drifted Weights / Share Tracking)**:
  - Since rebalancing occurs strictly on the first trading day of each month, the strategy purchases exact share counts at $T_{reb}$ close.
  - Between rebalance dates, shares are held. Daily portfolio returns reflect the change in total portfolio equity value:
    $$R_{p, t} = \frac{\sum_i N_i P_{i, t}}{\sum_i N_i P_{i, t-1}} - 1$$
  - This accurately models real-world systematic execution without artificial daily turnover.
- **Alternative Naive Model (Fixed Daily Weights)**:
  - Static application of monthly target weights each day ($R_{p, t} = \sum w_i R_{i, t}$) implies unmodeled daily rebalancing back to initial weights. We document this distinction to highlight why buy-and-hold share tracking is standard institutional quantitative practice.

## 4. Tie-Breaking Protocol

- If two stocks have identical momentum scores, ranking breaks ties deterministically using alphabetical ordering of ticker symbols (`method='first'`).
- Empirical check confirmed that only 1 rebalance date across all 5 lookbacks had a tie (Lookback 21 on 2009-04-01), where both tied stocks were ranked 20 and 21 (far below the rank-12 retention cutoff), resulting in identical portfolio composition regardless of tie-breaker.

## 5. Risk-Free Rate & Trading Costs

- Risk-free rate is assumed to be 0.0% per the assignment specification.
- No transaction costs, execution slippage, short selling, or leverage are assumed.

