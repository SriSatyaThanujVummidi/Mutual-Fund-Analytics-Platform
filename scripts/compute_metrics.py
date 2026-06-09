"""
compute_metrics.py
Bluestock Fintech — Mutual Fund Analytics Capstone
================================================
Computes all fund performance & risk metrics from cleaned NAV data:
  - Daily returns + CAGR (1yr / 3yr / 5yr)
  - Sharpe Ratio
  - Sortino Ratio
  - Alpha & Beta (OLS vs NIFTY100 benchmark)
  - Maximum Drawdown
  - Fund Scorecard (composite 0–100 score)

Usage:
    python compute_metrics.py

Requires (in data/processed/):
    clean_nav.csv
    clean_benchmark_indices.csv   (columns: date, index_name, close_value)

Outputs (all in data/processed/):
    returns_computed.csv
    cagr_report.csv
    sharpe_values.csv
    sortino_values.csv
    alpha_beta.csv
    max_drawdown.csv
    fund_scorecard.csv
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

PROCESSED_DIR    = os.path.join("data", "processed")
RISK_FREE_ANNUAL = 0.065          # RBI repo-rate proxy
Rf_DAILY         = RISK_FREE_ANNUAL / 252

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save(df, fname):
    path = os.path.join(PROCESSED_DIR, fname)
    df.to_csv(path, index=False)
    print(f"  ✓ Saved {fname}  ({len(df)} rows)")
    return df


def load_nav():
    path = os.path.join(PROCESSED_DIR, "clean_nav.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df.sort_values(["amfi_code", "date"], inplace=True)
    return df


def load_benchmark():
    path = os.path.join(PROCESSED_DIR, "clean_benchmark_indices.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 1. DAILY RETURNS
# ─────────────────────────────────────────────────────────────────────────────

def compute_daily_returns(nav):
    """
    Adds 'daily_return' column (decimal, e.g. 0.0123 = 1.23%).
    Drops the first NaN row per fund (no previous day to compare).
    """
    print("\n[1] Daily Returns")
    nav = nav.copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    nav.dropna(subset=["daily_return"], inplace=True)

    outliers = (nav["daily_return"].abs() > 0.15).sum()
    print(f"    Rows after NaN drop : {len(nav)}")
    print(f"    Outliers |r| > 15%  : {outliers}")

    save(nav, "returns_computed.csv")
    return nav


# ─────────────────────────────────────────────────────────────────────────────
# 2. CAGR (1yr / 3yr / 5yr)
# ─────────────────────────────────────────────────────────────────────────────

def _cagr(nav_end, nav_start, n_trading_days):
    """CAGR using trading-day count (252 per year)."""
    if nav_start <= 0 or n_trading_days <= 0:
        return np.nan
    years = n_trading_days / 252
    return (nav_end / nav_start) ** (1 / years) - 1


def compute_cagr(nav):
    """Compute 1yr, 3yr, 5yr CAGR for every fund that has enough history."""
    print("\n[2] CAGR")
    results = []

    for code, grp in nav.groupby("amfi_code"):
        grp = grp.sort_values("date").reset_index(drop=True)
        latest = grp["nav"].iloc[-1]
        n      = len(grp)
        row    = {"amfi_code": code}

        if n >= 252:   # 1yr ≈ 252 trading days
            row["cagr_1yr"] = _cagr(latest, grp["nav"].iloc[-252], 252)
        if n >= 756:   # 3yr
            row["cagr_3yr"] = _cagr(latest, grp["nav"].iloc[-756], 756)
        if n >= 1260:  # 5yr
            row["cagr_5yr"] = _cagr(latest, grp["nav"].iloc[-1260], 1260)

        results.append(row)

    cagr_df = pd.DataFrame(results)
    save(cagr_df, "cagr_report.csv")

    # Display top 10 by 3yr CAGR
    if "cagr_3yr" in cagr_df.columns:
        top = (cagr_df.sort_values("cagr_3yr", ascending=False)
                      .head(10)
                      .assign(cagr_3yr_pct=lambda d: (d["cagr_3yr"] * 100).round(2)))
        print("    Top 10 by 3yr CAGR (%):")
        print(top[["amfi_code", "cagr_3yr_pct"]].to_string(index=False))

    return cagr_df


# ─────────────────────────────────────────────────────────────────────────────
# 3. SHARPE RATIO
# ─────────────────────────────────────────────────────────────────────────────

def compute_sharpe(nav):
    """
    Sharpe = (mean_daily_return - Rf_daily) / std_daily * sqrt(252)
    Rf = 6.5% annual (RBI repo-rate proxy)
    """
    print("\n[3] Sharpe Ratio")
    rows = []

    for code, grp in nav.groupby("amfi_code"):
        returns = grp["daily_return"].dropna()
        if len(returns) < 60:
            continue
        std = returns.std()
        if std == 0:
            continue
        sharpe = (returns.mean() - Rf_DAILY) / std * np.sqrt(252)
        rows.append({"amfi_code": code, "sharpe_ratio": round(sharpe, 4)})

    sharpe_df = pd.DataFrame(rows)
    save(sharpe_df, "sharpe_values.csv")

    print("    Top 10 by Sharpe:")
    print(sharpe_df.sort_values("sharpe_ratio", ascending=False)
                   .head(10).to_string(index=False))

    return sharpe_df


# ─────────────────────────────────────────────────────────────────────────────
# 4. SORTINO RATIO
# ─────────────────────────────────────────────────────────────────────────────

def compute_sortino(nav, sharpe_df):
    """
    Sortino = (mean_daily_return - Rf_daily) / downside_std * sqrt(252)
    downside_std = std of negative-return days only
    """
    print("\n[4] Sortino Ratio")
    rows = []

    for code, grp in nav.groupby("amfi_code"):
        returns  = grp["daily_return"].dropna()
        negative = returns[returns < 0]
        if len(returns) < 60 or len(negative) < 5:
            continue
        dstd = negative.std()
        if dstd == 0:
            continue
        sortino = (returns.mean() - Rf_DAILY) / dstd * np.sqrt(252)
        rows.append({"amfi_code": code, "sortino_ratio": round(sortino, 4)})

    sortino_df = pd.DataFrame(rows)
    save(sortino_df, "sortino_values.csv")

    # Side-by-side comparison
    comparison = sharpe_df.merge(sortino_df, on="amfi_code")
    print("    Top 10 Sharpe vs Sortino:")
    print(comparison.sort_values("sortino_ratio", ascending=False)
                    .head(10).to_string(index=False))

    return sortino_df


# ─────────────────────────────────────────────────────────────────────────────
# 5. ALPHA & BETA (OLS regression vs NIFTY100)
# ─────────────────────────────────────────────────────────────────────────────

def compute_alpha_beta(nav, benchmark):
    """
    OLS: Rp = α + β × Rm
      Beta  = slope  (market sensitivity)
      Alpha = intercept × 252  (annualised excess return)
    Benchmark: NIFTY100 from benchmark_indices file
    """
    print("\n[5] Alpha & Beta")

    bench_nifty = (benchmark[benchmark["index_name"] == "NIFTY100"]
                   .copy()
                   .sort_values("date"))
    bench_nifty["nifty100_return"] = bench_nifty["close_value"].pct_change()
    bench_ret = bench_nifty[["date", "nifty100_return"]].dropna()
    print(f"    Benchmark rows (NIFTY100): {len(bench_ret)}")

    rows = []
    for code, grp in nav.groupby("amfi_code"):
        fund_ret = grp[["date", "daily_return"]].dropna()
        merged   = fund_ret.merge(bench_ret, on="date", how="inner")
        if len(merged) < 60:
            continue

        slope, intercept, r, p, _ = stats.linregress(
            merged["nifty100_return"], merged["daily_return"]
        )
        rows.append({
            "amfi_code" : code,
            "beta"      : round(slope, 4),
            "alpha"     : round(intercept * 252, 4),   # annualised
            "r_squared" : round(r ** 2, 4),
        })

    ab_df = pd.DataFrame(rows)
    save(ab_df, "alpha_beta.csv")

    print("    Top 10 by Alpha:")
    print(ab_df.sort_values("alpha", ascending=False)
               .head(10).to_string(index=False))

    return ab_df, bench_ret


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAXIMUM DRAWDOWN
# ─────────────────────────────────────────────────────────────────────────────

def compute_max_drawdown(nav):
    """
    Max Drawdown = min(NAV / running_max − 1)
    Returns a negative value (e.g. -0.32 means -32% worst drop).
    """
    print("\n[6] Maximum Drawdown")
    rows = []

    for code, grp in nav.groupby("amfi_code"):
        prices       = grp.sort_values("date")["nav"]
        running_max  = prices.cummax()
        drawdown     = prices / running_max - 1
        max_dd       = drawdown.min()
        worst_date   = grp.sort_values("date").iloc[drawdown.argmin()]["date"]
        rows.append({
            "amfi_code"       : code,
            "max_drawdown_pct": round(max_dd * 100, 2),
            "worst_date"      : worst_date,
        })

    dd_df = pd.DataFrame(rows)
    save(dd_df, "max_drawdown.csv")

    print("    Worst 10 drawdowns:")
    print(dd_df.sort_values("max_drawdown_pct").head(10).to_string(index=False))

    return dd_df


# ─────────────────────────────────────────────────────────────────────────────
# 7. FUND SCORECARD  (composite 0–100)
# ─────────────────────────────────────────────────────────────────────────────

def compute_scorecard(cagr_df, sharpe_df, ab_df, dd_df):
    """
    Composite score (0–100):
      30% × 3yr-CAGR rank
      25% × Sharpe rank
      20% × Alpha rank
      15% × Expense ratio rank (inverse — lower = better)
      10% × Max-drawdown rank (inverse — less negative = better)

    Expense ratio is taken from clean_fund_master.csv.
    """
    print("\n[7] Fund Scorecard")

    # Load expense ratios from fund master
    master_path = os.path.join(PROCESSED_DIR, "clean_fund_master.csv")
    if os.path.exists(master_path):
        master = pd.read_csv(master_path)[["amfi_code", "expense_ratio_pct",
                                           "scheme_name", "fund_house",
                                           "category", "risk_category"]]
    else:
        master = pd.DataFrame(columns=["amfi_code", "expense_ratio_pct"])

    # Merge all metric tables
    sc = (cagr_df[["amfi_code", "cagr_3yr"]].dropna()
          .merge(sharpe_df[["amfi_code", "sharpe_ratio"]], on="amfi_code", how="inner")
          .merge(ab_df[["amfi_code", "alpha"]], on="amfi_code", how="inner")
          .merge(dd_df[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="inner"))

    if not master.empty:
        sc = sc.merge(master, on="amfi_code", how="left")

    n = len(sc)
    if n == 0:
        print("    ⚠️  No data to score.")
        return pd.DataFrame()

    # Rank columns (higher rank = better)
    sc["rank_cagr"]    = sc["cagr_3yr"].rank(ascending=True)
    sc["rank_sharpe"]  = sc["sharpe_ratio"].rank(ascending=True)
    sc["rank_alpha"]   = sc["alpha"].rank(ascending=True)

    # Inverse ranks (lower value = better)
    if "expense_ratio_pct" in sc.columns:
        sc["rank_expense"] = sc["expense_ratio_pct"].rank(ascending=False)
    else:
        sc["rank_expense"] = n / 2  # neutral if missing

    sc["rank_dd"] = sc["max_drawdown_pct"].rank(ascending=False)  # less negative = higher rank

    # Composite score (normalised to 0–100)
    sc["composite_score"] = (
        0.30 * sc["rank_cagr"]    +
        0.25 * sc["rank_sharpe"]  +
        0.20 * sc["rank_alpha"]   +
        0.15 * sc["rank_expense"] +
        0.10 * sc["rank_dd"]
    )
    sc["composite_score"] = (
        (sc["composite_score"] - sc["composite_score"].min()) /
        (sc["composite_score"].max() - sc["composite_score"].min()) * 100
    ).round(2)

    sc.sort_values("composite_score", ascending=False, inplace=True)
    sc.reset_index(drop=True, inplace=True)
    sc.index += 1   # rank starts at 1
    sc.index.name = "rank"

    # Drop raw rank columns from output
    drop_cols = ["rank_cagr", "rank_sharpe", "rank_alpha", "rank_expense", "rank_dd"]
    sc.drop(columns=[c for c in drop_cols if c in sc.columns], inplace=True)

    save(sc.reset_index(), "fund_scorecard.csv")

    print("    Top 10 funds:")
    display_cols = ["amfi_code", "composite_score"]
    if "scheme_name" in sc.columns:
        display_cols.insert(1, "scheme_name")
    print(sc.reset_index().head(10)[display_cols].to_string(index=False))

    return sc


# ─────────────────────────────────────────────────────────────────────────────
# 8. TRACKING ERROR  (printed, not saved separately)
# ─────────────────────────────────────────────────────────────────────────────

def compute_tracking_error(nav, bench_ret, scorecard):
    """Print tracking error for the top 5 funds vs NIFTY100."""
    print("\n[8] Tracking Error vs NIFTY100 (top 5 funds)")

    if scorecard.empty:
        print("    Scorecard empty — skipping.")
        return

    top5 = scorecard.reset_index()["amfi_code"].head(5).tolist()
    for code in top5:
        fr  = nav[nav["amfi_code"] == code][["date", "daily_return"]]
        mg  = fr.merge(bench_ret, on="date", how="inner")
        te  = (mg["daily_return"] - mg["nifty100_return"]).std() * np.sqrt(252) * 100
        print(f"    amfi_code {code}  TE: {te:.2f}%")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_metrics():
    print("=" * 52)
    print("  Bluestock MF Capstone — Compute Metrics")
    print("=" * 52)

    # Load
    nav       = load_nav()
    benchmark = load_benchmark()

    # Compute
    nav_with_returns = compute_daily_returns(nav)
    cagr_df          = compute_cagr(nav_with_returns)
    sharpe_df        = compute_sharpe(nav_with_returns)
    sortino_df       = compute_sortino(nav_with_returns, sharpe_df)
    ab_df, bench_ret = compute_alpha_beta(nav_with_returns, benchmark)
    dd_df            = compute_max_drawdown(nav_with_returns)
    scorecard        = compute_scorecard(cagr_df, sharpe_df, ab_df, dd_df)
    compute_tracking_error(nav_with_returns, bench_ret, scorecard)

    print("\n✅ All metrics computed!")
    print(f"   Output folder → {PROCESSED_DIR}/")
    print("   Files: returns_computed.csv, cagr_report.csv, sharpe_values.csv,")
    print("          sortino_values.csv, alpha_beta.csv, max_drawdown.csv,")
    print("          fund_scorecard.csv")


if __name__ == "__main__":
    run_metrics()
