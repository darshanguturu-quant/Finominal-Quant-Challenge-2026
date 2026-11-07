# Finominal Quant Challenge 2026: Momentum Factor Optimization

**Role:** Junior Quantitative Analyst  
**Author:** Shri Dharshan Guturu  

A monthly-rebalanced, market-capitalization-weighted momentum strategy across a 30-stock equity universe evaluated across five lookback periods (21, 63, 126, 189, and 252 trading days) from January 2006 through June 2026.

---

## Performance Summary

Across the 5,083 active trading days (246 monthly rebalances), **189 trading days** produces the programmatic maximum Sharpe ratio.

| Lookback Period | Annualized Sharpe Ratio | Cumulative Return | CAGR | Annualized Volatility | Max Drawdown | Calmar Ratio |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **21 Days** | 1.3530 | 1,874,179.92% | 62.87% | 260.52% | -76.21% | 0.82 |
| **63 Days** | 1.3946 | 4,109,999.03% | 69.33% | 266.55% | -73.12% | 0.95 |
| **126 Days** | 1.3972 | 5,424,022.83% | 71.68% | 265.33% | -71.04% | 1.01 |
| **189 Days** | **1.4532** | **187,313,822.26%** | **104.63%** | **262.47%** | **-72.07%** | **1.45** |
| **252 Days** | 1.4523 | 134,489,606.03% | 101.30% | 262.92% | -69.18% | 1.46 |

### Mandatory Outputs
- **Optimal Lookback Period:** 189 trading days
- **Maximum Annualized Sharpe Ratio:** 1.4532
- **Cumulative Return:** 187,313,822.26% ($1 invested grows to ~$1.87 million)
- **CAGR:** 104.63%

*Note on Parameter Selection:* The Sharpe difference between 189 days (1.4532) and 252 days (1.4523) is only 0.0009. The 189-day period is the programmatic maximum, but performance is essentially tied between ~9-month and 12-month lookbacks.

---

## Project Structure

```text
.
├── data/
│   ├── Finominal_Quant Challenge_2026 06.pdf   # Challenge brief
│   ├── Test_mcap_data.csv                     # Historical daily market cap (30 stocks)
│   └── Test_price_data.csv                    # Historical daily close prices (30 stocks)
├── src/
│   ├── __init__.py
│   ├── backtest.py                            # Backtest engine with execution timing
│   ├── data_loader.py                         # Data parsing, alignment, rebalance dates
│   ├── metrics.py                             # Sharpe, Cumulative Return, CAGR, drawdowns
│   ├── momentum.py                            # Momentum score calculation and ranking
│   └── portfolio.py                           # 10-stock buffer logic and 20% capping
├── tests/
│   ├── test_backtest.py                       # Timing, look-ahead bias, CSV checks
│   ├── test_data_loader.py                    # Alignment, parsing, schedule validation
│   ├── test_metrics.py                        # Analytical metric formula tests
│   ├── test_momentum.py                       # Ranking, tie-breaking, lookback indexing
│   └── test_portfolio.py                      # Buffer rule, iterative capping, 10 holdings
├── results/
│   ├── cumulative_returns.png                 # Log-scale equity curves
│   ├── daily_returns.csv                      # Daily portfolio returns for all 5 lookbacks
│   ├── drawdowns.png                          # 2-panel underwater drawdown plot
│   ├── performance_summary.csv                # Full metrics comparison table
│   ├── portfolio_holdings.csv                 # 12,300 audit rows (holdings, ranks, weights)
│   ├── risk_return_scatter.png                # Annualized return vs. volatility scatter
│   └── sharpe_comparison.png                  # Bar chart of Sharpe ratios across lookbacks
├── docs/
│   ├── assumptions.md                         # Detailed methodology and conventions
│   ├── conversation_history.html              # Interactive browser chat transcript
│   ├── conversation_history.md                # Markdown conversation transcript for GitHub
│   ├── data_findings.md                       # Data audit and price anomaly analysis
│   ├── loom_script.md                         # Narration script for walkthrough video
│   └── progress.md                            # Phase-by-phase implementation log
├── main.py                                    # End-to-end execution script
├── requirements.txt                           # Project dependencies
└── README.md
```

---

## Data

- **Universe:** 30 equities across 5,337 trading days from `2005-01-03` to `2026-06-24`.
- **Date Formats:** `Test_price_data.csv` uses `DD-MM-YYYY`; `Test_mcap_data.csv` uses `YYYY-MM-DD`. Both parse and align row-by-row to identical timestamps.
- **Burn-In Period (2005):** 253 trading days (`2005-01-03` to `2005-12-30`) are used exclusively for initial momentum calculation. The first calculation date (`2005-12-30`, index 252) provides the full 252-day lookback back to index 0 (`2005-01-03`) without trimming.
- **Data Integrity:** Zero missing values, zero duplicates, all prices and market capitalizations strictly positive.

---

## Strategy Methodology

### 1. Momentum Signal
On each calculation date $T_{calc}$, calculate the momentum score for all 30 stocks:
$$M_i = \frac{P_{i, T_{calc}}}{P_{i, T_{calc} - L_{days}}} - 1$$
Stocks are ranked in descending order (Rank 1 = highest momentum). Ties are broken deterministically by ticker alphabetical order.

### 2. Portfolio Selection & Rank-12 Retention Buffer
The portfolio holds exactly 10 stocks. On each monthly rebalance date $T_{reb}$:
1. Evaluate current holdings using new momentum ranks from $T_{calc}$.
2. Retain existing holdings ranked $\le 12$.
3. Exit existing holdings ranked $> 12$.
4. Fill vacant positions using the highest-ranked candidates not currently held.
5. Verify exactly 10 unique stocks.

### 3. Market-Cap Weighting & Iterative 20% Cap
Raw weights are calculated from market caps on $T_{calc}$:
$$w_{i, raw} = \frac{MC_{i, T_{calc}}}{\sum_{j=1}^{10} MC_{j, T_{calc}}}$$
If any stock exceeds 20% ($0.20$), apply iterative capping:
1. Cap violating stocks at exactly 20%.
2. Sum the excess weight: $E = \sum (w_{orig} - 0.20)$.
3. Redistribute $E$ proportionally among uncapped stocks according to relative market capitalization.
4. Repeat until all individual weights $\le 20\%$ and total portfolio weight equals $100\%$.

### 4. Execution Timing & Look-Ahead Bias Prevention
- **Schedule:** Monthly rebalance date $T_{reb}$ is the first trading day of each month. Calculation date $T_{calc}$ is the immediately preceding trading day ($T_{calc} = T_{reb} - 1$).
- **Execution:** Target weights are calculated from $T_{calc}$ data. Portfolio adjustments execute at $T_{reb}$ close.
- **Return Accounting:** Existing holdings earn returns through $T_{reb}$ close. New target weights take effect after $T_{reb}$ close, applying to subsequent return intervals ($T_{reb} \to T_{reb} + 1$).
- **First Day:** Execution begins at `2006-01-02` close. Uninvested cash return prior to close is 0.0%. Active equity returns begin `2006-01-03` ($N = 5,083$).
- **Risk-Free Rate:** 0.0% annualized as specified in the assignment.

---

## How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Tests (24 Tests)
```bash
pytest tests -v
```
All 24 unit tests cover momentum formulas, rank-12 buffer selection, 20% iterative capping, weight constraints across all 1,230 rebalance events, execution timing, and look-ahead bias prevention.

### 3. Run Pipeline
```bash
python main.py
```
This loads and validates the raw CSV files, executes all 5 strategies, and generates:
- `results/performance_summary.csv` — Full performance metrics table
- `results/daily_returns.csv` — Daily portfolio returns for all 5 strategies
- `results/portfolio_holdings.csv` — Full audit trail of 12,300 rows (holdings, momentum ranks, weights)
- `results/*.png` — Four visualization charts

---

## Charts

The backtest outputs 4 charts in `results/`:
- **[results/cumulative_returns.png](results/cumulative_returns.png):** Log-scale equity growth of $1 invested from 2006 to 2026 across all five lookback strategies.
- **[results/sharpe_comparison.png](results/sharpe_comparison.png):** Bar chart comparing Annualized Sharpe Ratios across lookback windows.
- **[results/drawdowns.png](results/drawdowns.png):** Two-panel underwater drawdown chart highlighting the optimal 189-day strategy alongside comparative curves.
- **[results/risk_return_scatter.png](results/risk_return_scatter.png):** Annualized return versus annualized volatility scatter plot showing the risk-return profile of each lookback.

---

## Limitations & Critical Assessment

1. **Observed Price-Data Anomalies:**
   - The dataset contains 8,493 daily price movements exceeding $+100\%$ or falling below $-50\%$.
   - Notable examples: `GICH.NS` on 2013-11-05 rose $+2,436.1\%$ while its market cap moved $+3.9\%$; `WIPR.NS` on 2015-08-18 rose $+953.9\%$ while its market cap moved $-0.8\%$.
   - The mean Pearson correlation between daily price returns and daily market-cap returns across all 30 tickers is only **0.0021**, confirming that price spikes occurred without corresponding market capitalization adjustments.

2. **Mechanical Backtest vs. Corporate Actions:**
   - Holding fixed share quantities between monthly rebalances applied to unadjusted prices represents a **mechanical backtest**, not economically adjusted physical holdings through corporate actions.
   - An unadjusted 5:1 stock split registers an artificial $-80\%$ loss on that position, while an unadjusted quote spike registers an artificial gain.
   - Because the challenge dataset provides no official corporate-action adjustment factors, raw datasets are preserved 100% without arbitrary modification.

3. **Material Impact on Strategy Volatility:**
   - These raw price spikes drive high annualized volatility (262.47%), 1,274 trading days with $|R| > 10\%$, a maximum drawdown of $-72.07\%$ (trough on 2020-03-18), and inflated compounding (CAGR 104.63%).

4. **Fragility of Optimal Lookback:**
   - The Sharpe difference between 189 days (1.4532) and 252 days (1.4523) is only 0.0009. The 189-day period is the programmatic maximum under the mandate, but should be viewed as essentially tied with 252 days rather than a distinct regime.

5. **Frictions Not Modelled:**
   - Transaction costs, execution slippage, commissions, and market impact are not modelled because the assignment specification did not provide parameters for them. In live trading, performance would differ materially.
