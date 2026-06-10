"""
B4 — Markowitz Efficient Frontier Portfolio Optimisation
=========================================================
Selects 5 funds from the DB, computes the efficient frontier,
identifies the Max-Sharpe and Min-Variance portfolios, and saves:
  - outputs/b4_efficient_frontier.png
  - outputs/b4_portfolio_weights.csv
  - outputs/b4_efficient_frontier_points.csv
"""

import sqlite3
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy.optimize import minimize

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "data" / "bluestock_mf.db"
OUTPUT_DIR  = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Parameters ─────────────────────────────────────────────────────────────────
N_FUNDS         = 5
TRADING_DAYS    = 252
RISK_FREE_RATE  = 0.065
N_MC_PORTFOLIOS = 8_000      # random portfolios for scatter
N_FRONTIER_PTS  = 100        # points along the efficient frontier

# ── Colour palette ─────────────────────────────────────────────────────────────
CLR_BG       = "#F8FAFF"
CLR_SCATTER  = "#93C5FD"
CLR_FRONTIER = "#0057B8"
CLR_MAXSHARPE= "#F59E0B"
CLR_MINVAR   = "#10B981"
CLR_EW       = "#8B5CF6"
CLR_GRID     = "#E5E7EB"


# ── Data loading ───────────────────────────────────────────────────────────────

def load_returns(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load daily NAV, pivot to wide format, forward-fill, compute log returns.
    Returns DataFrame of daily log-returns, columns = short fund labels.
    """
    nav_df = pd.read_sql(
        "SELECT scheme_code, scheme_name, date, nav FROM nav_data",
        conn, parse_dates=["date"]
    )
    nav_df.sort_values(["scheme_code", "date"], inplace=True)

    # Select N_FUNDS with most data
    counts = nav_df.groupby("scheme_code").size().sort_values(ascending=False)
    top_codes = counts.head(N_FUNDS).index.tolist()
    nav_df = nav_df[nav_df["scheme_code"].isin(top_codes)]

    # Build code → short label map
    name_map = (
        nav_df.drop_duplicates("scheme_code")
              .set_index("scheme_code")["scheme_name"]
              .str.split("Fund").str[0]
              .str.strip()
              .str[:22]
    )

    pivot = nav_df.pivot(index="date", columns="scheme_code", values="nav").ffill()
    pivot.columns = [name_map.get(c, str(c)) for c in pivot.columns]

    # Drop funds that are missing more than 20% of dates (sparse history)
    thresh = int(len(pivot) * 0.80)
    pivot.dropna(axis=1, thresh=thresh, inplace=True)

    # Only keep the common date range where ALL remaining funds have data
    pivot.dropna(axis=0, how="any", inplace=True)

    if pivot.shape[1] < 2:
        raise ValueError("Not enough funds with overlapping NAV history. Check your DB.")
    if len(pivot) < 60:
        raise ValueError(f"Only {len(pivot)} overlapping rows — too few for optimisation.")

    print(f"NAV matrix: {len(pivot)} trading days × {pivot.shape[1]} funds")

    # Log returns
    log_ret = np.log(pivot / pivot.shift(1)).dropna()
    return log_ret


# ── Portfolio math ─────────────────────────────────────────────────────────────

def portfolio_stats(
    weights: np.ndarray,
    mean_ret: np.ndarray,
    cov_mat: np.ndarray,
) -> tuple[float, float, float]:
    """Annual return, annual std, Sharpe ratio for a weight vector."""
    ret  = (weights @ mean_ret) * TRADING_DAYS
    var  = (weights @ cov_mat @ weights) * TRADING_DAYS
    std  = np.sqrt(var)
    sharpe = (ret - RISK_FREE_RATE) / std if std > 0 else 0
    return ret, std, sharpe


def neg_sharpe(weights, mean_ret, cov_mat):
    ret, std, _ = portfolio_stats(weights, mean_ret, cov_mat)
    return -(ret - RISK_FREE_RATE) / std if std > 0 else 0


def portfolio_variance(weights, cov_mat):
    return (weights @ cov_mat @ weights) * TRADING_DAYS


def optimise_portfolio(
    target_ret: float,
    mean_ret: np.ndarray,
    cov_mat: np.ndarray,
    n: int,
) -> np.ndarray | None:
    """Minimise variance subject to: weights sum to 1, E[R] = target_ret, w≥0."""
    constraints = [
        {"type": "eq",  "fun": lambda w: np.sum(w) - 1},
        {"type": "eq",  "fun": lambda w: (w @ mean_ret) * TRADING_DAYS - target_ret},
    ]
    bounds  = [(0.0, 1.0)] * n
    w0      = np.ones(n) / n
    result  = minimize(
        portfolio_variance, w0, args=(cov_mat,),
        method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    return result.x if result.success else None


# ── Random portfolio MC scatter ────────────────────────────────────────────────

def random_portfolios(
    mean_ret: np.ndarray,
    cov_mat: np.ndarray,
    n: int,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(N_MC_PORTFOLIOS):
        w = rng.random(n)
        w /= w.sum()
        r, s, sh = portfolio_stats(w, mean_ret, cov_mat)
        rows.append({"ret": r * 100, "std": s * 100, "sharpe": sh,
                     **{f"w{i}": wi for i, wi in enumerate(w)}})
    return pd.DataFrame(rows)


# ── Efficient Frontier ────────────────────────────────────────────────────────

def efficient_frontier(
    mean_ret: np.ndarray,
    cov_mat: np.ndarray,
    n: int,
) -> pd.DataFrame:
    rets_min = mean_ret.min() * TRADING_DAYS
    rets_max = mean_ret.max() * TRADING_DAYS

    target_rets = np.linspace(rets_min * 1.01, rets_max * 0.99, N_FRONTIER_PTS)
    frontier = []
    for tr in target_rets:
        w = optimise_portfolio(tr, mean_ret, cov_mat, n)
        if w is not None:
            r, s, sh = portfolio_stats(w, mean_ret, cov_mat)
            frontier.append({"ret": r * 100, "std": s * 100, "sharpe": sh})
    return pd.DataFrame(frontier)


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_frontier(
    mc_df: pd.DataFrame,
    ef_df: pd.DataFrame,
    portfolios: dict,
    fund_labels: list[str],
) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6),
                             gridspec_kw={"width_ratios": [2, 1]})
    fig.patch.set_facecolor(CLR_BG)

    # ── Left: Frontier chart ──────────────────────────────────────────────────
    ax = axes[0]
    ax.set_facecolor(CLR_BG)

    sc = ax.scatter(mc_df["std"], mc_df["ret"],
                    c=mc_df["sharpe"], cmap="coolwarm_r",
                    s=6, alpha=0.5, zorder=2)
    plt.colorbar(sc, ax=ax, label="Sharpe Ratio", fraction=0.03, pad=0.02)

    # ── FIX: corrected indentation for if/else block ──────────────────────────
    if not ef_df.empty and "std" in ef_df.columns:
        ax.plot(ef_df["std"], ef_df["ret"], color=CLR_FRONTIER, lw=2.5, zorder=5, label="Efficient Frontier")
    else:
        print("WARNING: Efficient frontier is empty — skipping frontier line.")

    markers = {
        "Max Sharpe":   (CLR_MAXSHARPE, "*", 280),
        "Min Variance": (CLR_MINVAR,    "D", 120),
        "Equal Weight": (CLR_EW,        "^", 120),
    }
    for label, (clr, mk, sz) in markers.items():
        p = portfolios[label]
        ax.scatter(p["std"] * 100, p["ret"] * 100,
                   color=clr, marker=mk, s=sz, zorder=8, label=label,
                   edgecolors="white", linewidths=0.8)
        ax.annotate(
            f" {label}\n Ret={p['ret']*100:.1f}%  Sharpe={p['sharpe']:.2f}",
            xy=(p["std"] * 100, p["ret"] * 100),
            xytext=(12, -18), textcoords="offset points",
            fontsize=7.5, color=clr, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=clr, lw=0.7),
        )

    ax.set_xlabel("Annualised Volatility (%)", fontsize=9)
    ax.set_ylabel("Annualised Return (%)", fontsize=9)
    ax.set_title("Markowitz Efficient Frontier\n"
                 f"({N_FUNDS} Funds · {N_MC_PORTFOLIOS:,} Random Portfolios)",
                 fontsize=11, fontweight="bold", color="#1E3A5F")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.grid(color=CLR_GRID, linewidth=0.7, zorder=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, framealpha=0.9, edgecolor="#CBD5E1")

    # ── Right: Weight bar charts ───────────────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor(CLR_BG)
    ax2.axis("off")

    portfolio_names = ["Max Sharpe", "Min Variance", "Equal Weight"]
    clrs_right      = [CLR_MAXSHARPE, CLR_MINVAR, CLR_EW]
    n_labels        = len(fund_labels)
    x               = np.arange(n_labels)
    bar_w           = 0.25
    offsets         = [-bar_w, 0, bar_w]

    ax3 = fig.add_axes([0.66, 0.12, 0.30, 0.72])
    ax3.set_facecolor(CLR_BG)

    for i, (pname, clr, off) in enumerate(zip(portfolio_names, clrs_right, offsets)):
        weights = portfolios[pname]["weights"]
        ax3.bar(x + off, weights * 100, bar_w * 0.9,
                label=pname, color=clr, alpha=0.85, edgecolor="white")

    short_labels = [lbl[:14] for lbl in fund_labels]
    ax3.set_xticks(x)
    ax3.set_xticklabels(short_labels, rotation=30, ha="right", fontsize=7)
    ax3.set_ylabel("Weight (%)", fontsize=8)
    ax3.set_title("Portfolio Allocations", fontsize=9, fontweight="bold", color="#1E3A5F")
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax3.grid(axis="y", color=CLR_GRID, linewidth=0.7)
    ax3.spines[["top", "right"]].set_visible(False)
    ax3.legend(fontsize=7, loc="upper right", framealpha=0.9)

    plt.suptitle("Bluestock MF — Portfolio Optimisation", fontsize=13,
                 fontweight="bold", color="#0057B8", y=1.01)

    out_path = OUTPUT_DIR / "b4_efficient_frontier.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ── Save CSVs ──────────────────────────────────────────────────────────────────

def save_outputs(
    portfolios: dict,
    ef_df: pd.DataFrame,
    fund_labels: list[str],
) -> None:
    # Weights CSV
    rows = []
    for pname, p in portfolios.items():
        row = {"portfolio": pname,
               "annual_return_%": round(p["ret"] * 100, 4),
               "annual_std_%": round(p["std"] * 100, 4),
               "sharpe_ratio": round(p["sharpe"], 4)}
        for label, w in zip(fund_labels, p["weights"]):
            row[label] = round(w, 6)
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "b4_portfolio_weights.csv", index=False)

    # Frontier points CSV
    ef_df.to_csv(OUTPUT_DIR / "b4_efficient_frontier_points.csv", index=False)
    print("Saved → b4_portfolio_weights.csv")
    print("Saved → b4_efficient_frontier_points.csv")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("B4 — Markowitz Efficient Frontier Optimisation")
    print("=" * 65)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run ETL pipeline first."
        )

    conn    = sqlite3.connect(DB_PATH)
    ret_df  = load_returns(conn)
    conn.close()

    fund_labels = ret_df.columns.tolist()
    n           = len(fund_labels)
    print(f"Funds selected: {fund_labels}\n")

    mean_ret = ret_df.mean().values
    cov_mat  = ret_df.cov().values

    # ── Optimise Max Sharpe ──────────────────────────────────────────────────
    print("Optimising Max Sharpe portfolio…")
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds      = [(0.0, 1.0)] * n
    w0          = np.ones(n) / n
    res_sharpe  = minimize(
        neg_sharpe, w0, args=(mean_ret, cov_mat),
        method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    w_ms  = res_sharpe.x
    r_ms, s_ms, sh_ms = portfolio_stats(w_ms, mean_ret, cov_mat)

    # ── Optimise Min Variance ────────────────────────────────────────────────
    print("Optimising Min Variance portfolio…")
    res_minvar = minimize(
        portfolio_variance, w0, args=(cov_mat,),
        method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    w_mv  = res_minvar.x
    r_mv, s_mv, sh_mv = portfolio_stats(w_mv, mean_ret, cov_mat)

    # ── Equal Weight ─────────────────────────────────────────────────────────
    w_ew  = np.ones(n) / n
    r_ew, s_ew, sh_ew = portfolio_stats(w_ew, mean_ret, cov_mat)

    portfolios = {
        "Max Sharpe":   {"weights": w_ms,  "ret": r_ms,  "std": s_ms,  "sharpe": sh_ms},
        "Min Variance": {"weights": w_mv,  "ret": r_mv,  "std": s_mv,  "sharpe": sh_mv},
        "Equal Weight": {"weights": w_ew,  "ret": r_ew,  "std": s_ew,  "sharpe": sh_ew},
    }

    print("\n── Portfolio Summary ───────────────────────────────────────")
    for pname, p in portfolios.items():
        print(f"  {pname:15s}  Return={p['ret']*100:.2f}%  "
              f"Std={p['std']*100:.2f}%  Sharpe={p['sharpe']:.3f}")
        for lbl, w in zip(fund_labels, p["weights"]):
            if w > 0.005:
                print(f"    ├─ {lbl[:30]:<30s} {w*100:.1f}%")
    print()

    # ── Monte Carlo scatter & Frontier ───────────────────────────────────────
    print(f"Generating {N_MC_PORTFOLIOS:,} random portfolios…")
    mc_df  = random_portfolios(mean_ret, cov_mat, n)

    print(f"Computing efficient frontier ({N_FRONTIER_PTS} points)…")
    ef_df  = efficient_frontier(mean_ret, cov_mat, n)

    # ── Plot ──────────────────────────────────────────────────────────────────
    out_path = plot_frontier(mc_df, ef_df, portfolios, fund_labels)
    print(f"Saved → {out_path.name}")

    save_outputs(portfolios, ef_df, fund_labels)
    print("\nAll done.\n")


if __name__ == "__main__":
    main()
