# Loom Presentation Script (3–5 Minutes)

*Below is the complete narration script for the recorded Loom walkthrough video.*

### [0:00 – 0:45] Introduction & Executive Overview
> "Hello everyone. My name is Shri Dharshan Guturu, and today I am walking you through the complete implementation of the Finominal Quant Challenge 2026 for the Junior Quantitative Analyst role.
>
> The challenge asks us to construct a monthly-rebalanced, market-capitalization-weighted momentum strategy across a 30-stock equity universe, test five exact lookback periods—21, 63, 126, 189, and 252 trading days—and determine the optimal lookback that maximizes the Annualized Sharpe Ratio.
>
> Right upfront, our programmatic results show that **189 Trading Days (~9 months)** is the optimal lookback parameter, delivering an **Annualized Sharpe Ratio of 1.4532**, a **CAGR of 104.63%**, and a **Cumulative Return of over 187 million percent** across the 20.5-year backtest."

### [0:45 – 1:45] Data Architecture & Observed Price Anomalies
> "Let’s look at the data architecture. We were provided with historical daily closing prices and market capitalization data from January 2005 to June 2026.
>
> In our data quality audit, we addressed date format differences (`DD-MM-YYYY` vs `YYYY-MM-DD`) and aligned all 5,337 trading days with zero missing values.
>
> We also conducted an in-depth data anomaly investigation: we observed 8,493 extreme price movements where prices shifted dramatically while market capitalizations remained relatively flat. Without official corporate filing records, these are properly classified as observed price-data anomalies and quote discontinuities. We clarify that fixed share quantities applied to unadjusted prices represent a mechanical backtest, not economically adjusted physical holdings through corporate actions; rather, without official adjustment factors in the dataset, our backtest preserves the raw data without arbitrary modification. We note transparently that actual performance in live trading may differ materially.
>
> Crucially, our backtest engine enforces **zero look-ahead bias**:
> - Rebalances occur on the first trading day of the month ($T_{reb}$).
> - All momentum signals and market-cap weights are computed using data strictly from the immediately preceding trading day ($T_{calc}$).
> - Trades execute at the close of $T_{reb}$, meaning new portfolio weights only apply to returns starting the following morning."

### [1:45 – 2:45] Portfolio Construction & 20% Capping Algorithm
> "Now let's examine the portfolio construction logic in `src/portfolio.py`:
> 1. We enforce the mandatory **rank-12 retention buffer**. Instead of simply picking the top 10 stocks every month, any currently held stock ranked 1 through 12 is retained. Only stocks falling below rank 12 are exited, and vacant slots are filled by the highest-ranked candidates not currently held. This reduces unnecessary turnover.
> 2. Once the 10 stocks are selected, we apply the **iterative 20% weight capping algorithm**. Stocks exceeding 20% are capped at exactly 0.20, their excess weight is summed, and redistributed proportionally to the uncapped stocks based on relative market caps. We repeat this until no stock exceeds 20% and the weights sum to exactly 100%. We validated this with unit tests across equal-weight, single mega-cap, and cascading multi-cap scenarios."

### [2:45 – 3:45] Backtest Results & Comparative Analysis
> "Moving to the backtest results across all five lookback periods:
> - Lookback 21 days yielded a Sharpe of 1.3530.
> - Lookback 63 days yielded a Sharpe of 1.3946.
> - Lookback 126 days yielded a Sharpe of 1.3972.
> - Lookback 189 days peaked at our maximum Sharpe of **1.4532**.
> - Lookback 252 days came in just behind at 1.4523.
>
> We have exported full portfolio holdings and weights for all five strategies into `results/portfolio_holdings.csv`, comprising exactly 12,300 audit rows with stock names, momentum ranks, and portfolio weights."

### [3:45 – 4:30] Code Quality, Testing & Critical Conclusion
> "To guarantee production quality:
> - We built 24 automated unit tests in `pytest` covering momentum formulas, rank buffers, capping edge cases, weight validation across all 1,230 rebalance events, and look-ahead bias perturbation tests. All 24 tests pass with 100% success.
> - We improved our drawdown visualization with a 2-panel chart highlighting the optimal strategy alongside comparative curves.
> - Transaction costs and market impact were not modelled because the assignment specification did not provide parameters for them.
>
> In conclusion, our solution strictly satisfies every rule of the assignment, uses zero synthetic data for final results, and establishes **189 Trading Days** as the optimal momentum lookback. Thank you for your time and consideration."
