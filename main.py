"""Main execution script for Finominal Quant Challenge 2026.

Orchestrates:
1. Data loading and strict validation.
2. Monthly rebalance schedule generation (2006-01-02 to 2026-06-24).
3. Independent execution of all 5 lookback strategies (21, 63, 126, 189, 252 days).
4. Performance metrics computation (Sharpe, Cumulative Return, CAGR, Volatility, Drawdowns).
5. Programmatic identification of the Optimal Lookback Period.
6. Exporting results to CSV:
   - results/performance_summary.csv
   - results/daily_returns.csv
   - results/portfolio_holdings.csv
7. Generating publication-quality charts:
   - results/cumulative_returns.png
   - results/sharpe_comparison.png
   - results/drawdowns.png
   - results/risk_return_scatter.png
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# Ensure project-local cache directory for matplotlib
os.environ["MPLCONFIGDIR"] = str(Path(".mpl_cache").resolve())

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from src.backtest import BacktestEngine, BacktestResult
from src.data_loader import load_and_validate_data, get_rebalance_schedule
from src.metrics import calculate_all_metrics, calculate_drawdown_series


LOOKBACK_PERIODS: List[int] = [21, 63, 126, 189, 252]
DATA_DIR = Path("data")
RESULTS_DIR = Path("results")


def generate_charts(
    results_dict: Dict[int, BacktestResult],
    summary_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Generate high-resolution professional quantitative performance charts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    colors = {
        21: "#1f77b4",   # Blue
        63: "#ff7f0e",   # Orange
        126: "#2ca02c",  # Green
        189: "#d62728",  # Red (Highlighting Optimal)
        252: "#9467bd",  # Purple
    }

    # ----------------------------------------------------
    # Chart 1: Cumulative Return (Log Scale)
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    for L in LOOKBACK_PERIODS:
        res = results_dict[L]
        cum_ret = (1.0 + res.daily_returns).cumprod()
        label = f"L = {L} days (CAGR: {summary_df.loc[L, 'cagr_pct']:.1f}%)"
        linewidth = 2.5 if L == 189 else 1.5
        ax.plot(res.dates, cum_ret, label=label, color=colors[L], linewidth=linewidth, alpha=0.9)

    ax.set_yscale("log")
    ax.set_title("Cumulative Growth of $1 Invested (2006 - 2026, Log Scale)", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=11, fontweight="bold")
    ax.set_ylabel("Portfolio Wealth (Log Scale, $1 Base)", fontsize=11, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=10, loc="upper left")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
    fig.tight_layout()
    fig.savefig(output_dir / "cumulative_returns.png")
    plt.close(fig)

    # ----------------------------------------------------
    # Chart 2: Annualized Sharpe Ratio Comparison
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    bars = ax.bar(
        [f"{L} Days" for L in LOOKBACK_PERIODS],
        [summary_df.loc[L, "annualized_sharpe_ratio"] for L in LOOKBACK_PERIODS],
        color=[colors[L] for L in LOOKBACK_PERIODS],
        width=0.55,
        edgecolor="#333333",
        linewidth=1.0,
    )

    # Annotate bar values
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.4f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title("Annualized Sharpe Ratio Across Lookback Periods (0% Risk-Free Rate)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Lookback Period (Exact Trading Days)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Annualized Sharpe Ratio", fontsize=11, fontweight="bold")
    ax.set_ylim(0, max(summary_df["annualized_sharpe_ratio"]) * 1.15)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.7)
    fig.tight_layout()
    fig.savefig(output_dir / "sharpe_comparison.png")
    plt.close(fig)

    # ----------------------------------------------------
    # Chart 3: Underwater Drawdown Chart (2-Panel Enhanced Readability)
    # ----------------------------------------------------
    fig, (ax_opt, ax_comp) = plt.subplots(2, 1, figsize=(13, 8.5), dpi=300, sharex=True)

    # Panel 1: Optimal Strategy (189 Days) Focus with Fill & Key Events
    opt_L = 189
    opt_res = results_dict[opt_L]
    opt_dd = calculate_drawdown_series(opt_res.daily_returns) * 100.0
    ax_opt.plot(opt_res.dates, opt_dd, color=colors[opt_L], linewidth=2.0, label=f"Optimal Strategy L = {opt_L} Days")
    ax_opt.fill_between(opt_res.dates, opt_dd, 0, color=colors[opt_L], alpha=0.25)
    ax_opt.axhline(0, color="#333333", linestyle="-", linewidth=0.8, alpha=0.7)

    # Annotate Maximum Drawdown
    min_dd_val = opt_dd.min()
    min_dd_date = opt_dd.idxmin()
    ax_opt.scatter([min_dd_date], [min_dd_val], color="black", s=60, zorder=5)
    ax_opt.annotate(
        f"Max Drawdown: {min_dd_val:.1f}%\n({min_dd_date.strftime('%Y-%m-%d')})",
        xy=(min_dd_date, min_dd_val),
        xytext=(30, -15),
        textcoords="offset points",
        fontsize=9.5,
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="#fffae6", ec="#cccccc", lw=0.8),
    )

    # Annotate 2008 Global Financial Crisis & 2020 COVID Shock
    ax_opt.axvspan(pd.Timestamp("2008-01-01"), pd.Timestamp("2009-03-31"), color="#cccccc", alpha=0.2, label="2008 GFC Period")
    ax_opt.axvspan(pd.Timestamp("2020-02-01"), pd.Timestamp("2020-04-30"), color="#e6f2ff", alpha=0.35, label="2020 COVID Shock")

    ax_opt.set_title("Optimal Momentum Strategy (L = 189 Days) - Historical Drawdown Profile", fontsize=13, fontweight="bold", pad=10)
    ax_opt.set_ylabel("Drawdown (%)", fontsize=11, fontweight="bold")
    ax_opt.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax_opt.set_ylim(-85, 5)
    ax_opt.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9, loc="lower left")
    ax_opt.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

    # Panel 2: Comparative Curves Across All 5 Lookback Periods
    for L in LOOKBACK_PERIODS:
        res = results_dict[L]
        dd = calculate_drawdown_series(res.daily_returns) * 100.0
        lw = 2.2 if L == opt_L else 1.2
        alpha = 0.95 if L == opt_L else 0.75
        label = f"L = {L:3d}d (Max DD: {summary_df.loc[L, 'max_drawdown_pct']:.1f}%)"
        ax_comp.plot(res.dates, dd, label=label, color=colors[L], linewidth=lw, alpha=alpha)

    ax_comp.axhline(0, color="#333333", linestyle="-", linewidth=0.8, alpha=0.7)
    ax_comp.set_title("Comparative Drawdown Profiles Across All 5 Lookback Periods (2006 - 2026)", fontsize=13, fontweight="bold", pad=10)
    ax_comp.set_xlabel("Date", fontsize=11, fontweight="bold")
    ax_comp.set_ylabel("Drawdown (%)", fontsize=11, fontweight="bold")
    ax_comp.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax_comp.set_ylim(-85, 5)
    ax_comp.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9, loc="lower left", ncol=3)
    ax_comp.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

    fig.tight_layout()
    fig.savefig(output_dir / "drawdowns.png")
    plt.close(fig)

    # ----------------------------------------------------
    # Chart 4: Risk-Return Profile (Ann. Return vs Ann. Vol)
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
    for L in LOOKBACK_PERIODS:
        vol = summary_df.loc[L, "annualized_volatility_pct"]
        cagr = summary_df.loc[L, "cagr_pct"]
        sharpe = summary_df.loc[L, "annualized_sharpe_ratio"]
        ax.scatter(vol, cagr, color=colors[L], s=160, edgecolor="black", zorder=5)
        ax.annotate(
            f"L={L}d\n(SR={sharpe:.2f})",
            xy=(vol, cagr),
            xytext=(6, -6),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title("Risk-Return Profile Across Lookback Periods", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Annualized Volatility (%)", fontsize=11, fontweight="bold")
    ax.set_ylabel("CAGR (%)", fontsize=11, fontweight="bold")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
    fig.tight_layout()
    fig.savefig(output_dir / "risk_return_scatter.png")
    plt.close(fig)


def main() -> None:
    """Execute complete Finominal Quant Challenge pipeline."""
    # Ensure stdout handles UTF-8 gracefully if supported
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 80)
    print("FINOMINAL QUANT CHALLENGE 2026 - PRODUCTION PIPELINE")
    print("Monthly-Rebalanced Market-Cap Weighted Momentum Strategy")
    print("=" * 80)

    # Step 1: Data Loading & Validation
    print("\n[1/6] Loading and validating historical datasets...")
    price_path = DATA_DIR / "Test_price_data.csv"
    mcap_path = DATA_DIR / "Test_mcap_data.csv"

    price_df, mcap_df, tickers = load_and_validate_data(price_path, mcap_path)
    print(f"  [OK] Verified {len(tickers)} stock symbols across {len(price_df)} trading days.")
    print(f"  [OK] Date Range: {price_df.index[0].strftime('%Y-%m-%d')} to {price_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"  [OK] Integrity: 0 nulls, 0 duplicate dates, 100% positive prices and market capitalizations.")

    # Step 2: Schedule Generation
    print("\n[2/6] Generating monthly rebalance schedule...")
    schedule = get_rebalance_schedule(price_df.index, start_year=2006, max_lookback=max(LOOKBACK_PERIODS))
    print(f"  [OK] Total monthly rebalances: {len(schedule)}")
    print(f"  [OK] First Rebalance: T_reb = {schedule[0].reb_date.strftime('%Y-%m-%d')}, T_calc = {schedule[0].calc_date.strftime('%Y-%m-%d')}")
    print(f"  [OK] Terminal Rebalance: T_reb = {schedule[-1].reb_date.strftime('%Y-%m-%d')}, T_calc = {schedule[-1].calc_date.strftime('%Y-%m-%d')}")

    # Step 3: Backtest Engine Execution
    print("\n[3/6] Running independent backtests across all 5 lookback periods...")
    engine = BacktestEngine(
        price_df=price_df,
        mcap_df=mcap_df,
        schedule=schedule,
        portfolio_size=10,
        buffer_cutoff_rank=12,
        weight_cap=0.20,
    )

    results_drifted: Dict[int, BacktestResult] = {}
    metrics_list: List[Dict] = []
    daily_returns_dict: Dict[str, pd.Series] = {}

    for L in LOOKBACK_PERIODS:
        res = engine.run(lookback_days=L, execution_model="drifted", include_day_zero=False)
        results_drifted[L] = res
        daily_returns_dict[f"return_L{L}"] = res.daily_returns

        metrics = calculate_all_metrics(res.daily_returns, lookback_days=L)
        metrics_list.append(metrics)
        print(f"  [OK] Lookback {L:3d} Days: Sharpe = {metrics['annualized_sharpe_ratio']:.4f}, CAGR = {metrics['cagr_pct']:8.2f}%, CR = {metrics['cumulative_return_pct']:12.2f}%")

    # Step 4: Summary & Optimal Identification
    summary_df = pd.DataFrame(metrics_list).set_index("lookback_days")
    optimal_lookback = int(summary_df["annualized_sharpe_ratio"].idxmax())
    max_sharpe = float(summary_df.loc[optimal_lookback, "annualized_sharpe_ratio"])
    opt_cum_ret = float(summary_df.loc[optimal_lookback, "cumulative_return_pct"])
    opt_cagr = float(summary_df.loc[optimal_lookback, "cagr_pct"])

    print("\n" + "=" * 80)
    print("MANDATORY FINAL DELIVERABLE OUTPUTS:")
    print("=" * 80)
    print(f"  1. Optimal Lookback Period (Days):  {optimal_lookback}")
    print(f"  2. Maximum Annualized Sharpe Ratio: {max_sharpe:.4f}")
    print(f"  3. Cumulative Return (%):           {opt_cum_ret:.2f}%")
    print(f"  4. CAGR (%):                        {opt_cagr:.2f}%")
    print("=" * 80)

    # Step 5: Export Data to CSV
    print("\n[4/6] Exporting results to results/ directory...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Summary table
    summary_export = summary_df[[
        "annualized_sharpe_ratio",
        "cumulative_return_pct",
        "cagr_pct",
        "annualized_volatility_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "n_observations",
    ]].copy()
    summary_export.columns = [
        "Annualized Sharpe Ratio",
        "Cumulative Return (%)",
        "CAGR (%)",
        "Annualized Volatility (%)",
        "Max Drawdown (%)",
        "Calmar Ratio",
        "N (Return Days)",
    ]
    summary_export.to_csv(RESULTS_DIR / "performance_summary.csv")
    print(f"  [OK] Saved performance summary -> {RESULTS_DIR / 'performance_summary.csv'}")

    # Daily returns
    df_daily_returns = pd.DataFrame(daily_returns_dict)
    df_daily_returns.index.name = "date"
    df_daily_returns.to_csv(RESULTS_DIR / "daily_returns.csv")
    print(f"  [OK] Saved daily returns -> {RESULTS_DIR / 'daily_returns.csv'}")

    # Portfolio holdings export for ALL FIVE lookback strategies (Official Requirement 2)
    # Schema: lookback_days, rebalance_date, stock, momentum_rank, portfolio_weight
    all_holdings_records = []
    for L in LOOKBACK_PERIODS:
        res = results_drifted[L]
        for rec in res.rebalance_history:
            reb_str = rec["rebalance_date"].strftime("%Y-%m-%d")
            calc_str = rec["calculation_date"].strftime("%Y-%m-%d")
            for stock in rec["selected_holdings"]:
                all_holdings_records.append({
                    "lookback_days": L,
                    "rebalance_date": reb_str,
                    "stock": stock,
                    "momentum_rank": rec["momentum_ranks"][stock],
                    "portfolio_weight": rec["capped_weights"][stock],
                    "calculation_date": calc_str,
                    "raw_weight": rec["raw_weights"][stock],
                    "action": "RETAINED" if stock in rec["retained_holdings"] else "ADDED",
                })

    df_all_holdings = pd.DataFrame(all_holdings_records)
    df_all_holdings.to_csv(RESULTS_DIR / "portfolio_holdings.csv", index=False)
    print(f"  [OK] Saved all 5 strategies portfolio holdings ({len(df_all_holdings)} rows) -> {RESULTS_DIR / 'portfolio_holdings.csv'}")

    # Step 6: Generate Charts
    print("\n[5/6] Generating visualization charts...")
    generate_charts(results_drifted, summary_df, RESULTS_DIR)
    print(f"  [OK] Saved cumulative returns chart -> {RESULTS_DIR / 'cumulative_returns.png'}")
    print(f"  [OK] Saved Sharpe comparison chart  -> {RESULTS_DIR / 'sharpe_comparison.png'}")
    print(f"  [OK] Saved drawdowns chart          -> {RESULTS_DIR / 'drawdowns.png'}")
    print(f"  [OK] Saved risk-return scatter      -> {RESULTS_DIR / 'risk_return_scatter.png'}")

    # Complete Summary Table Print
    print("\n[6/6] Full Strategy Comparison Table:")
    print("-" * 105)
    print(f"{'Lookback (Days)':<16} | {'Sharpe Ratio':<14} | {'Cumulative Return':<20} | {'CAGR (%)':<12} | {'Ann. Vol (%)':<14} | {'Max DD (%)':<12}")
    print("-" * 105)
    for L in LOOKBACK_PERIODS:
        row = summary_df.loc[L]
        print(f"{L:<16d} | {row['annualized_sharpe_ratio']:<14.4f} | {row['cumulative_return_pct']:<18.2f}% | {row['cagr_pct']:<10.2f}% | {row['annualized_volatility_pct']:<12.2f}% | {row['max_drawdown_pct']:<10.2f}%")
    print("-" * 105)

    print("\nPipeline execution complete! All artifacts generated successfully.\n")


if __name__ == "__main__":
    main()
