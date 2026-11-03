# Methodological Framework: Verified Calculations, Assumptions & Unresolved Data Limitations

## 1. Verified Calculations & Algorithmic Results

1. **Rebalance & Calculation Timeline**:
   - Rebalance Date ($T_{reb}$): First trading day of each month. Trades execute strictly at market close.
   - Calculation Date ($T_{calc}$): The immediately preceding trading day ($T_{calc} = T_{reb} - 1$).
   - Signals and weights are computed using closing prices and market capitalization data strictly on $T_{calc}$, enforcing zero look-ahead bias.
2. **Signal Generation (Momentum)**:
   - Formula: $M_i = (P_{i, T_{calc}} / P_{i, T_{calc} - L_{days}}) - 1$.
   - Descending ranking with deterministic alphabetical secondary tie-breaking.
3. **Portfolio Selection & Retention Buffer**:
   - Exactly 10 stocks held at all times.
   - Retain existing holdings with momentum rank $\le 12$.
   - Exit existing holdings with momentum rank $> 12$.
   - Vacant slots filled by highest-ranked available stocks.
4. **Market-Cap Weighting & 20% Iterative Capping**:
   - Raw weights: $w_{i, raw} = MC_{i, T_{calc}} / \sum MC_{j, T_{calc}}$.
   - Capping algorithm iteratively caps violating stocks at 20% and redistributes excess proportionally to uncapped stocks based on relative market caps.
   - Verified across all 1,230 rebalance events: exactly 10 holdings, maximum weight $\le 0.200000$, and total weight sum equals $1.000000$ (100%).
5. **Portfolio Holdings Audit Export**:
   - [`results/portfolio_holdings.csv`](file:///c:/Users/sreej/Downloads/Finominal%20Quant%20Challenge/results/portfolio_holdings.csv) contains exactly 12,300 audit rows covering all 5 strategies with `lookback_days`, `rebalance_date`, `stock`, `momentum_rank`, and `portfolio_weight`.

---

## 2. Implementation Assumptions

1. **Initial Execution & First-Day Return**:
   - The backtest execution begins on January 2, 2006 ($T_{reb, 1}$).
   - Prior to execution at market close, no equity portfolio was held; cash return is assumed to be 0.0%.
   - Target portfolio shares are purchased at January 2, 2006 close, and the first active equity return is observed from January 2 close to January 3, 2006 close ($N = 5,083$ active days).
   - Under both active days ($N=5,083$) and full period ($N=5,084$), Lookback = 189 Days is programmatically optimal.
2. **Within-Month Share Tracking**:
   - Capital is allocated to target shares $N_i = \frac{w_i V_{T_{reb}}}{P_{i, T_{reb}}}$ at $T_{reb}$ close.
   - Shares are held between monthly rebalances, and daily portfolio return tracks equity valuation:
     $$R_{p, t} = \frac{\sum_i N_i P_{i, t}}{\sum_i N_i P_{i, t-1}} - 1$$
   - **Clarification on Fixed Share Counts**: Fixed share counts alone do **not** neutralize unadjusted corporate actions or price scale jumps. If an unadjusted price drops 80% due to an unadjusted split, holding a fixed share count without receiving split shares takes an artificial 80% loss. Conversely, if an unadjusted price spikes 400%, holding fixed shares registers an artificial +300% position gain.
3. **Transaction Costs & Market Frictions**:
   - Transaction costs, execution fees, slippage, and market impact are not modelled because the assignment specification does not specify or provide parameters for them.
4. **Risk-Free Rate**:
   - Assumed to be 0.0% annualized as required by the assignment specification.

---

## 3. Unresolved External Data Limitations

1. **Observed Price-Data Anomalies**:
   - A total of 8,493 daily price movements exceed +100% or fall below -50%.
   - While certain price jumps where market cap remains flat are consistent with unadjusted corporate actions, without official corporate filing records they are properly classified as **observed price-data anomalies and quote discontinuities** rather than definitively labeled as specific splits or bonus issues.
2. **Absence of Corporate-Action Adjustment Factors**:
   - The challenge dataset provides raw closing prices without adjustment factors. Per assignment rules ("preserve original datasets; do not invent external data"), we cannot fabricate adjustment factors or arbitrarily modify prices.
3. **Material Impact on Return Metrics**:
   - These observed price anomalies materially drive the high annualized volatility (262.47%), large daily return dispersion (1,274 days with $|R| > 10\%$), and compounding metrics (CAGR 104.63%).
   - **Performance Statement**: Actual performance in live trading may differ materially due to execution frictions, split adjustments, slippage, and market liquidity dynamics.
