# Project Assumptions, Methodological Decisions & Unresolved Data Limitations

## 1. Execution & Rebalancing Timeline

- **Rebalance Date ($T_{reb}$)**: The first trading day of each calendar month. Trades to establish target portfolio weights are executed at the **market close** on this date.
- **Calculation Date ($T_{calc}$)**: The trading day immediately preceding $T_{reb}$ ($T_{calc} = T_{reb} - 1$ in exact trading-day space).
- **Look-Ahead Bias Prevention**:
  - Momentum scores $M_i$ and market-cap weights $w_{i}$ are strictly derived from prices and market capitalizations on $T_{calc}$.
  - Zero information from $T_{reb}$ or future dates is used in signal generation or portfolio construction.

## 2. Initial Formation & Return Period Conventions

- **Initial Formation Date**: `2006-01-02` (the first trading day of 2006).
- **First Day Return**:
  - The backtest execution begins on `2006-01-02`. Prior to market close, no equity portfolio was held (100% cash, return = 0.0).
  - Target portfolio shares are purchased at the closing prices on `2006-01-02`.
  - The first active equity portfolio return is observed over the interval from `2006-01-02` close to `2006-01-03` close:
    $$R_{p, \text{2006-01-03}} = \sum_i w_{i, \text{2006-01-02}} \left(\frac{P_{i, \text{2006-01-03}}}{P_{i, \text{2006-01-02}}} - 1\right)$$
  - **Return Observations Count**:
    - Active equity return intervals: $N = 5,083$ trading days (`2006-01-03` to `2026-06-24`).
    - Full period including Day 1 cash return (0.0): $N = 5,084$ trading days (`2006-01-02` to `2026-06-24`).
    - Both metrics are calculated and reported with complete mathematical transparency; in both cases, **189 Days** is the optimal lookback.

## 3. Within-Month Valuation: Share-Tracking vs. Fixed Daily Weights

- **Monthly Share Tracking (Buy-and-Hold within Month)**:
  - Capital is allocated to target shares $N_i = \frac{w_i V_{T_{reb}}}{P_{i, T_{reb}}}$ at $T_{reb}$ close.
  - Between rebalances, shares are held. Daily portfolio return reflects equity valuation:
    $$R_{p, t} = \frac{\sum_i N_i P_{i, t}}{\sum_i N_i P_{i, t-1}} - 1$$
- **Important Correction on Fixed Share Counts**:
  - **Fixed share counts alone do NOT neutralize stock splits or unadjusted price movements.**
  - If a stock undergoes an unadjusted 5-for-1 split (price drops 80%), a fixed share count backtest takes an artificial 80% loss on that position because the share quantity is not multiplied by the split ratio.
  - Conversely, if an unadjusted price jumps 400% due to an exchange data artifact, holding fixed shares experiences an artificial 300% gain.
  - Therefore, fixed share tracking does not eliminate or neutralize corporate actions. It simply reflects direct, unadulterated execution on the provided raw price series without inventing external adjustment factors.

## 4. Material Impact of Data Anomalies on Performance Metrics

An empirical audit reveals that anomalies in the raw closing price data **materially affect every single performance metric**:
- **Daily Volatility**: Individual stocks exhibit annualized volatilities of 600%–800% due to frequent single-day price scale spikes. As a result, the portfolio's annualized volatility is **262.47%** (compared to 15%–25% for standard equity portfolios).
- **Return Dispersion**:
  - Out of 5,083 return days, **1,274 days (25.1%)** experience daily portfolio moves exceeding $\pm 10\%$.
  - **687 days (13.5%)** exceed $\pm 20\%$.
  - **139 days (2.7%)** exceed $\pm 50\%$.
  - The maximum 1-day gain is **+140.29%**; the worst 1-day drop is **-57.91%**.
- **Sharpe Ratio & CAGR**:
  - Mean daily return is inflated to **+1.51% per day**.
  - Daily standard deviation is **16.53% per day**.
  - The annualized Sharpe ratio is $\frac{0.0151}{0.1653} \times \sqrt{252} \approx 1.4532$.
  - Compounding over 5,083 days with high positive mean yields a Cumulative Return of **187,313,822.26%** (CAGR **104.63%**).
- **Conclusion**: These exceptional performance numbers are directly and materially driven by the raw, unadjusted price series in the challenge dataset.

## 5. Unresolved External Data Limitations

Per quantitative research standards, the following **unresolved limitations** must be explicitly recognized:
1. **Absence of Corporate-Action Adjustment Factors**: The challenge provides raw closing prices without dividend, split, or bonus adjustment factors. Under the challenge constraints ("preserve original datasets; do not invent external data"), we cannot fabricate adjustment factors.
2. **Transient Quote/Scale Anomaly Inconsistencies**: The daily correlation between price returns and market-cap returns is virtually zero ($0.0021$), showing that market cap did not track price scale changes.
3. **Official Raw Data Preservation**: All official results reported herein are generated strictly on the raw, unmodified datasets as supplied by Finominal.
