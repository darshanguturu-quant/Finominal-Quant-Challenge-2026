# Data Findings & Validation Audit

## 1. Datasets Inspected

| Dataset | File Path | Total Rows | Columns | Date Format | Date Range | Missing Values | Non-Positive Values |
|---|---|---|---|---|---|---|---|
| Historical Closing Prices | `data/Test_price_data.csv` | 5,337 | 31 (Date + 30 Stocks) | `DD-MM-YYYY` | `2005-01-03` to `2026-06-24` | 0 | 0 |
| Historical Market Capitalization | `data/Test_mcap_data.csv` | 5,337 | 31 (Date + 30 Stocks) | `YYYY-MM-DD` | `2005-01-03` to `2026-06-24` | 0 | 0 |

## 2. Key Data Discoveries

1. **Date Format Heterogeneity**:
   - `Test_price_data.csv` uses European day-first format: `%d-%m-%Y`.
   - `Test_mcap_data.csv` uses ISO format: `%Y-%m-%d`.
   - When parsed to `pd.Timestamp`, dates match row-by-row with zero discrepancies across all 5,337 rows.

2. **Temporal Alignment & Monotonicity**:
   - Both datasets are strictly monotonic increasing with no duplicate dates.
   - Total rows in 2005 (pre-2006 burn-in): 253 trading days (`2005-01-03` to `2005-12-30`).
   - The first calculation date is `2005-12-30` (index 252).
   - Maximum lookback of 252 days: index $252 - 252 = 0$ (`2005-01-03`), which exists in the dataset.

3. **Active Backtest Period**:
   - Starts on the first trading day of 2006: `2006-01-02` (index 253).
   - Total trading days from 2006 onwards: 5,084 days.
   - Total monthly rebalance dates: 246 rebalances (`2006-01-02` through `2026-06-01`).
   - Terminal trading day: `2026-06-24`.

4. **Stock Universe (30 Tickers)**:
   `AEGS.NS`, `ARTI.NS`, `ASHT.NS`, `BOB.NS`, `BRIT.NS`, `CEMI.NS`, `CHPC.NS`, `GENS.NS`, `GICH.NS`, `HEGL.NS`, `HLVL.NS`, `IMCL.NS`, `JAAO.NS`, `JKIN.NS`, `KAMT.NS`, `MDRD.BO`, `NALU.NS`, `OSGL.NS`, `SEAM.NS`, `TAJG.NS`, `TANE.BO`, `THOM.NS`, `TVEL.NS`, `VENK.NS`, `VSTI.NS`, `WHEL.NS`, `WIPR.NS`, `WRRN.BO`, `WSTC.NS`, `XPRO.NS`.

5. **Corporate Actions & Raw Price Dynamics**:
   - Historical closing prices contain raw corporate actions (e.g. stock splits/bonuses/special sessions), visible as sharp single-day spikes followed by reversals (e.g. `GICH.NS` on 2013-11-05).
   - In monthly buy-and-hold execution (share-tracking between monthly rebalances), these prices revert naturally without generating artificial transaction profits.
