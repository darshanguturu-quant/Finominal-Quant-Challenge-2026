# Data Findings & Validation Audit: Finominal Quant Challenge 2026

## 1. Datasets Inspected

| Dataset | File Path | Total Rows | Columns | Date Format | Date Range | Missing Values | Non-Positive Values |
|---|---|---|---|---|---|---|---|
| Historical Closing Prices | `data/Test_price_data.csv` | 5,337 | 31 (Date + 30 Stocks) | `DD-MM-YYYY` | `2005-01-03` to `2026-06-24` | 0 | 0 |
| Historical Market Capitalization | `data/Test_mcap_data.csv` | 5,337 | 31 (Date + 30 Stocks) | `YYYY-MM-DD` | `2005-01-03` to `2026-06-24` | 0 | 0 |

---

## 2. Temporal Alignment & Monotonicity

1. **Date Format Heterogeneity**:
   - `Test_price_data.csv` uses European day-first format: `%d-%m-%Y` (e.g., `03-01-2005`).
   - `Test_mcap_data.csv` uses standard ISO format: `%Y-%m-%d` (e.g., `2005-01-03`).
   - When parsed to `pd.Timestamp`, dates match row-by-row across all 5,337 observations without a single mismatch.
2. **Burn-in History**:
   - Total rows in 2005: 253 trading days (`2005-01-03` to `2005-12-30`).
   - First rebalance date: `2006-01-02` (index 253).
   - First calculation date: `2005-12-30` (index 252).
   - Maximum lookback of 252 days: index $252 - 252 = 0$ (`2005-01-03`), ensuring complete non-trimmed signal generation.
3. **Active Backtest Period**:
   - Trading days from 2006 onwards: 5,084 days.
   - Monthly rebalance events: 246 rebalances (`2006-01-02` through `2026-06-01`).
   - Terminal trading day: `2026-06-24`.

---

## 3. Deep-Dive Data Quality & Corporate Action Anomaly Investigation

### A. Anomaly Detection & Empirical Findings

A systematic audit across all 30 tickers identified frequent extreme daily price movements (> 100% gain or < -50% decline). Across the full matrix ($5,337 \times 30$), a total of **8,493 daily returns** exceed this threshold.

Below is an audit of the top extreme single-day price movements compared against corresponding market capitalizations:

| Date | Ticker | Price (Prev) | Price (Curr) | Price % Change | Mcap (Prev) | Mcap (Curr) | Mcap % Change | Implied Share Ratio |
|---|---|---|---|---|---|---|---|---|
| `2013-11-05` | `GICH.NS` | 15.29 | 387.77 | **+2,436.1%** | 5.49B | 5.70B | **+3.9%** | 0.041 (1/25th) |
| `2008-07-01` | `THOM.NS` | 5.51 | 100.52 | **+1,724.3%** | 11.39B | 10.97B | **-3.7%** | 0.053 (1/19th) |
| `2020-08-17` | `VENK.NS` | 359.56 | 5,504.89 | **+1,431.0%** | 19.05B | 19.54B | **+2.6%** | 0.067 (1/15th) |
| `2021-02-11` | `TANE.BO` | 7.79 | 119.09 | **+1,428.8%** | 825.2M | 827.7M | **+0.3%** | 0.066 (1/15th) |
| `2013-12-17` | `XPRO.NS` | 5.45 | 69.14 | **+1,168.6%** | 312.5M | 299.1M | **-4.3%** | 0.075 (1/13th) |
| `2017-07-21` | `CHPC.NS` | 68.44 | 821.82 | **+1,100.8%** | 56.99B | 57.80B | **+1.4%** | 0.084 (1/12th) |
| `2017-01-20` | `BOB.NS` | 41.91 | 483.62 | **+1,053.9%** | 368.9B | 355.6B | **-3.6%** | 0.084 (1/12th) |
| `2015-08-18` | `WIPR.NS` | 34.50 | 363.58 | **+953.9%** | 1.413T | 1.401T | **-0.8%** | 0.094 (1/10th) |

### B. Structural Interpretation of Anomalies

1. **Observed Price Movements vs. Market Capitalization**:
   - Notice that while price jumped by **+953.9%** for `WIPR.NS` on 2015-08-18, the **market capitalization moved by only -0.8%** (normal trading noise).
   - The implied outstanding shares ratio dropped by approximately $1/10$.
   - The subsequent trading day, the price reverted back to its baseline.
   - While certain price spikes where market capitalization remains flat are consistent with unadjusted corporate actions, without official corporate filing records or exchange disclosure data, these 8,493 extreme daily movements are properly classified as **observed price-data anomalies and quote discontinuities** rather than definitively labeled as specific splits or bonus issues.

2. **Price-Return vs. Market-Cap-Return Correlation Methodology (0.0021)**:
   - **Step-by-Step Mathematical Formulation**:
     1. For each ticker $i \in \{1, \dots, 30\}$ and each trading day $t \in \{2, \dots, 5337\}$, compute daily percentage returns:
        $$r_{P, i, t} = \frac{P_{i, t}}{P_{i, t-1}} - 1, \quad r_{MC, i, t} = \frac{MC_{i, t}}{MC_{i, t-1}} - 1$$
     2. Calculate the Pearson correlation coefficient between the daily price return series and daily market-cap return series for each stock:
        $$\rho_i = \mathrm{Corr}(r_{P, i}, r_{MC, i}) = \frac{\sum_{t=2}^{5337} (r_{P, i, t} - \bar{r}_{P, i})(r_{MC, i, t} - \bar{r}_{MC, i})}{\sqrt{\sum_{t=2}^{5337} (r_{P, i, t} - \bar{r}_{P, i})^2 \sum_{t=2}^{5337} (r_{MC, i, t} - \bar{r}_{MC, i})^2}}$$
     3. Take the arithmetic mean across all 30 individual ticker Pearson correlations:
        $$\bar{\rho} = \frac{1}{30} \sum_{i=1}^{30} \rho_i = 0.002107 \approx \mathbf{0.0021}$$
     - (Note: Pooling all $30 \times 5,336 = 160,080$ paired observation pairs into a single panel correlation yields $\rho_{\text{pooled}} = 0.001962 \approx 0.0020$).
   - **Economic Interpretation**: In standard equity markets, absent significant share issuance or buybacks, daily price returns and market-cap returns have correlation near $+1.0$. A near-zero correlation of $0.0021$ empirically demonstrates that the price series contains severe unadjusted quote spikes and anomalies that did not co-occur in the market capitalization series.

3. **Per-Stock Volatility Metrics**:
   - Annualized price volatility for all 30 stocks ranges between **580% and 830%**, with roughly 270 to 350 days of returns exceeding 50% per stock.
   - Market capitalization volatility closely mirrors price volatility across all names (volatility ratio $\approx 0.8\text{x}$ to $1.3\text{x}$).

### C. Methodological Handling, Share Count Clarification & Limitations

1. **Strict Data Preservation**:
   - Per official challenge instructions, the original datasets (`Test_price_data.csv` and `Test_mcap_data.csv`) are preserved 100% without arbitrary modification, outlier deletion, or synthetic corporate-action fabrication.
2. **Clarification on Fixed Share Quantities as a Mechanical Backtest**:
   - Holding fixed share quantities applied to unadjusted prices represents a **mechanical backtest**, not economically adjusted physical holdings through corporate actions.
   - In a true physical portfolio experiencing a corporate action (such as a 5:1 stock split), an investor's share count would be multiplied by 5, neutralizing the price decline.
   - In contrast, applying fixed (unadjusted) share quantities directly to raw unadjusted prices means the backtest mechanically tracks the arithmetic of the supplied numbers without corporate-action adjustments:
     - If an unadjusted price drops 80% due to an unadjusted 5:1 stock split, holding a fixed share count without receiving the 5x new shares registers an artificial -80% position loss.
     - Conversely, if an unadjusted price jumps 400%, holding fixed shares registers an artificial +300% position gain.
   - Fixed share quantities simply reflect the strict mechanical execution rule required by the challenge specification on the supplied raw closing prices, rather than economically adjusted physical holdings.
3. **Transaction Costs & Market Frictions**:
   - Transaction costs, execution commissions, slippage, and market impact are not modelled because the assignment specification does not specify or provide parameters for them.
4. **Material Impact on Strategy Performance**:
   - These raw data anomalies directly drive the portfolio's high annualized volatility (262.47%), extreme 1-day return tails (1,274 days with $|R| > 10\%$), and compounding metrics (CAGR 104.63%).
   - The strategy's Sharpe Ratio of 1.4532 reflects the ratio of high mean daily return (+1.51%/day) to high daily volatility (16.53%/day).
   - **Real-World Performance Disclosure**: Actual performance in live trading may differ materially due to execution frictions, split adjustments, slippage, borrowing fees, and liquidity constraints.
5. **Unresolved External Data Limitation**:
   - The absence of official corporate-action adjustment factors in the Finominal challenge dataset is an inherent external data limitation. All official results presented in this project are derived strictly from the supplied raw data as mandated.
