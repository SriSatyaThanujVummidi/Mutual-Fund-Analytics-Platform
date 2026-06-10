"""
B3 — Monte Carlo Simulation: 5-Year NAV Projection with Uncertainty Bands
==========================================================================
Uses Geometric Brownian Motion (GBM) calibrated to historical daily returns.

Output:
  - outputs/b3_monte_carlo_<scheme_code>.png  (one chart per selected fund)
  - outputs/b3_monte_carlo_summary.csv
"""

import sqlite3
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "data" / "bluestock_mf.db"
OUTPUT_DIR  = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Parameters ─────────────────────────────────────────────────────────────────
N_SIMULATIONS  = 1_000      # number of Monte Carlo paths
HORIZON_YEARS  = 5
TRADING_DAYS   = 252
TOTAL_STEPS    = HORIZON_YEARS * TRADING_DAYS
RISK_FREE_RATE = 0.065       # 6.5% RBI repo rate proxy
RANDOM_SEED    = 42

PERCENTILE_BANDS = [5, 10, 25, 50, 75, 90, 95]

# Colour scheme
CLR_MEDIAN  = "#0057B8"
CLR_BANDS   = {
    (5,  95): "#BFDBFE",   # lightest blue
    (10, 90): "#93C5FD",
    (25, 75): "#60A5FA",
}
CLR_ACTUAL  = "#1D4ED8"
CLR_GRID    = "#E5E7EB"


# ── Data loading ───────────────────────────────────────────────────────────────

def load_nav(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT scheme_code, scheme_name, date, nav FROM nav_data",
        conn, parse_dates=["date"]
    )
    df.sort_values(["scheme_code", "date"], inplace=True)
    return df


def select_funds(nav_df: pd.DataFrame, n: int = 5) -> list[int]:
    """Select top-N funds by data length for simulation."""
    counts = nav_df.groupby("scheme_code")["date"].count().sort_values(ascending=False)
    return counts.head(n).index.tolist()


# ── GBM Simulation ─────────────────────────────────────────────────────────────

def calibrate_gbm(nav_series: pd.Series) -> tuple[float, float]:
    """
    Calibrate mu (drift) and sigma (volatility) from historical daily log-returns.
    Returns annualised mu, annualised sigma.
    """
    log_ret = np.log(nav_series / nav_series.shift(1)).dropna()
    mu_daily    = log_ret.mean()
    sigma_daily = log_ret.std()
    mu_annual    = mu_daily * TRADING_DAYS
    sigma_annual = sigma_daily * np.sqrt(TRADING_DAYS)
    return mu_annual, sigma_annual


def run_gbm_simulation(
    s0: float, mu: float, sigma: float, n_steps: int, n_sims: int, seed: int
) -> np.ndarray:
    """
    Simulate n_sims paths of GBM using:
        S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
    Returns array of shape (n_steps+1, n_sims).
    """
    rng  = np.random.default_rng(seed)
    dt   = 1 / TRADING_DAYS
    Z    = rng.standard_normal((n_steps, n_sims))
    drift   = (mu - 0.5 * sigma ** 2) * dt
    diffuse = sigma * np.sqrt(dt) * Z
    log_ret = drift + diffuse                  # shape (n_steps, n_sims)
    log_path = np.vstack([np.zeros(n_sims), np.cumsum(log_ret, axis=0)])
    return s0 * np.exp(log_path)               # shape (n_steps+1, n_sims)


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_simulation(
    code: int,
    name: str,
    hist_series: pd.Series,
    sim_matrix: np.ndarray,
    mu: float,
    sigma: float,
) -> Path:
    """
    Plot historical NAV + MC simulation fan chart.
    sim_matrix shape: (TOTAL_STEPS+1, N_SIMULATIONS)
    """
    # Time axes
    hist_dates  = hist_series.index
    last_date   = hist_dates[-1]
    future_days = pd.bdate_range(start=last_date, periods=TOTAL_STEPS + 1)[1:]
    all_future  = np.array([last_date] + list(future_days))

    # Percentile fan
    pcts = np.percentile(sim_matrix, PERCENTILE_BANDS, axis=1)   # (7, steps+1)
    pct_map = {p: pcts[i] for i, p in enumerate(PERCENTILE_BANDS)}

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor("#FAFBFF")
    ax.set_facecolor("#FAFBFF")

    # Historical line — last 2 years for readability
    lookback = min(504, len(hist_series))
    hist_plot = hist_series.iloc[-lookback:]
    ax.plot(hist_plot.index, hist_plot.values,
            color=CLR_ACTUAL, lw=1.8, label="Historical NAV", zorder=5)

    # Uncertainty fans
    legend_patches = []
    for (lo, hi), clr in sorted(CLR_BANDS.items()):
        ax.fill_between(all_future, pct_map[lo], pct_map[hi],
                        alpha=0.55, color=clr, zorder=2)
        legend_patches.append(Patch(color=clr, alpha=0.7,
                                    label=f"P{lo}–P{hi} band"))

    # Median path
    ax.plot(all_future, pct_map[50],
            color=CLR_MEDIAN, lw=2.2, ls="-", label="Median (P50)", zorder=6)

    # 5 sample paths (thin)
    rng_vis = np.random.default_rng(0)
    sample_idx = rng_vis.choice(N_SIMULATIONS, size=5, replace=False)
    for i in sample_idx:
        ax.plot(all_future, sim_matrix[:, i], color="#94A3B8",
                lw=0.6, alpha=0.5, zorder=3)

    # Vertical divider at projection start
    ax.axvline(last_date, color="#6B7280", lw=1.2, ls="--", zorder=7)
    ax.text(last_date, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
            " Projection →", va="top", ha="left", fontsize=8, color="#6B7280")

    # Final value annotations
    s0 = hist_series.iloc[-1]
    p5_final  = pct_map[5][-1]
    p50_final = pct_map[50][-1]
    p95_final = pct_map[95][-1]
    ax.annotate(f"P50: ₹{p50_final:.2f}", xy=(all_future[-1], p50_final),
                xytext=(-60, 8), textcoords="offset points",
                fontsize=8, color=CLR_MEDIAN, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=CLR_MEDIAN, lw=0.8))

    # Labels & formatting
    short_name = name[:55] + "…" if len(name) > 55 else name
    ax.set_title(
        f"Monte Carlo NAV Projection — {short_name}\n"
        f"μ={mu*100:.1f}% p.a.  σ={sigma*100:.1f}% p.a.  "
        f"n={N_SIMULATIONS:,} paths  Horizon={HORIZON_YEARS}yr",
        fontsize=11, fontweight="bold", color="#1E3A5F", pad=12,
    )
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("NAV (₹)", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("₹{x:,.0f}"))
    ax.grid(color=CLR_GRID, linewidth=0.7, zorder=1)
    ax.spines[["top", "right"]].set_visible(False)

    # Legend
    all_handles = [
        plt.Line2D([0], [0], color=CLR_ACTUAL, lw=2, label="Historical NAV"),
        plt.Line2D([0], [0], color=CLR_MEDIAN, lw=2, label="Median (P50)"),
    ] + legend_patches
    ax.legend(handles=all_handles, loc="upper left", fontsize=8,
              framealpha=0.85, edgecolor="#CBD5E1")

    # Stats box
    cagr_median = (p50_final / s0) ** (1 / HORIZON_YEARS) - 1
    stats_txt = (
        f"Current NAV : ₹{s0:.2f}\n"
        f"P5  Final    : ₹{p5_final:.2f}\n"
        f"P50 Final    : ₹{p50_final:.2f}  ({cagr_median*100:.1f}% CAGR)\n"
        f"P95 Final    : ₹{p95_final:.2f}"
    )
    ax.text(0.02, 0.97, stats_txt, transform=ax.transAxes, fontsize=7.5,
            verticalalignment="top", family="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="#CBD5E1", alpha=0.9))

    plt.tight_layout()
    out_path = OUTPUT_DIR / f"b3_monte_carlo_{code}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ── Summary CSV ────────────────────────────────────────────────────────────────

def build_summary(results: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_DIR / "b3_monte_carlo_summary.csv", index=False)
    return df


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("B3 — Monte Carlo 5-Year NAV Projection")
    print("=" * 65)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run the ETL pipeline first (b1_cron_etl.py)."
        )

    conn    = sqlite3.connect(DB_PATH)
    nav_df  = load_nav(conn)
    conn.close()

    fund_codes = select_funds(nav_df, n=5)
    print(f"Selected {len(fund_codes)} funds for simulation\n")

    summary_rows = []

    for code in fund_codes:
        grp  = nav_df[nav_df["scheme_code"] == code].set_index("date")["nav"].sort_index()
        name = nav_df[nav_df["scheme_code"] == code]["scheme_name"].iloc[0]

        if len(grp) < 252:
            print(f"  SKIP [{code}] — insufficient history ({len(grp)} days)")
            continue

        mu, sigma = calibrate_gbm(grp)
        s0        = grp.iloc[-1]

        print(f"  Simulating [{code}] {name[:50]}")
        print(f"    μ={mu*100:.2f}%  σ={sigma*100:.2f}%  S₀=₹{s0:.2f}")

        sim = run_gbm_simulation(s0, mu, sigma, TOTAL_STEPS, N_SIMULATIONS, RANDOM_SEED)

        out_path = plot_simulation(code, name, grp, sim, mu, sigma)

        final_vals  = sim[-1, :]
        cagr_median = (np.median(final_vals) / s0) ** (1 / HORIZON_YEARS) - 1
        prob_double = (final_vals >= 2 * s0).mean()

        summary_rows.append({
            "scheme_code":  code,
            "scheme_name":  name,
            "current_nav":  round(s0, 4),
            "mu_annual_%":  round(mu * 100, 4),
            "sigma_annual_%": round(sigma * 100, 4),
            "p5_5yr":       round(np.percentile(final_vals, 5), 4),
            "p25_5yr":      round(np.percentile(final_vals, 25), 4),
            "p50_5yr":      round(np.percentile(final_vals, 50), 4),
            "p75_5yr":      round(np.percentile(final_vals, 75), 4),
            "p95_5yr":      round(np.percentile(final_vals, 95), 4),
            "cagr_median_%": round(cagr_median * 100, 4),
            "prob_double_%": round(prob_double * 100, 2),
            "chart_path":   str(out_path),
        })
        print(f"    P50 in {HORIZON_YEARS}yr: ₹{np.median(final_vals):.2f}  "
              f"({cagr_median*100:.1f}% CAGR)  "
              f"Prob(2x): {prob_double*100:.1f}%")
        print(f"    Saved → {out_path.name}\n")

    df = build_summary(summary_rows)
    print("Summary saved → outputs/b3_monte_carlo_summary.csv")
    print("\nAll done.\n")


if __name__ == "__main__":
    main()
