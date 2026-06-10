"""
B2 — Streamlit Web App: Mutual Fund Analytics Dashboard
=========================================================
Run:  streamlit run b2_streamlit_app.py
"""

import sqlite3
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "data" / "bluestock_mf.db"

BRAND_BLUE   = "#0057B8"
BRAND_TEAL   = "#00B4A6"
BRAND_AMBER  = "#F59E0B"
BRAND_RED    = "#EF4444"
BRAND_LIGHT  = "#F0F4FF"
PALETTE      = px.colors.qualitative.Bold

st.set_page_config(
    page_title="Bluestock MF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stMetric {{ background: {BRAND_LIGHT}; border-radius: 10px; padding: 1rem; }}
    .stMetric label {{ color: #555; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
    .block-container {{ padding-top: 1.5rem; }}
    h1, h2, h3 {{ color: {BRAND_BLUE}; }}
    .sidebar .sidebar-content {{ background: #f8fafc; }}
</style>
""", unsafe_allow_html=True)


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading data…")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)

    nav_df = pd.read_sql(
        "SELECT scheme_code, scheme_name, scheme_category, date, nav FROM nav_data",
        conn, parse_dates=["date"]
    )

    aum_df = pd.DataFrame()
    sip_df = pd.DataFrame()

    for tbl, target in [("aum_data", "aum_df"), ("sip_data", "sip_df")]:
        try:
            df = pd.read_sql(f"SELECT * FROM {tbl}", conn)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            if target == "aum_df":
                aum_df = df
            else:
                sip_df = df
        except Exception:
            pass

    conn.close()
    return nav_df, aum_df, sip_df


@st.cache_data(ttl=600, show_spinner=False)
def compute_metrics(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Per-fund: CAGR, volatility, Sharpe, max drawdown, latest NAV."""
    records = []
    for code, grp in nav_df.groupby("scheme_code"):
        grp = grp.sort_values("date").copy()
        if len(grp) < 30:
            continue
        grp["ret"] = grp["nav"].pct_change()
        n_years   = (grp["date"].iloc[-1] - grp["date"].iloc[0]).days / 365.25
        cagr      = (grp["nav"].iloc[-1] / grp["nav"].iloc[0]) ** (1 / max(n_years, 0.01)) - 1
        vol       = grp["ret"].std() * np.sqrt(252)
        sharpe    = (cagr - 0.065) / vol if vol > 0 else 0
        roll_max  = grp["nav"].cummax()
        drawdown  = (grp["nav"] - roll_max) / roll_max
        max_dd    = drawdown.min()
        records.append({
            "scheme_code": code,
            "scheme_name": grp["scheme_name"].iloc[-1],
            "category":    grp["scheme_category"].iloc[-1],
            "latest_nav":  grp["nav"].iloc[-1],
            "cagr_%":      round(cagr * 100, 2),
            "volatility_%":round(vol * 100, 2),
            "sharpe_ratio":round(sharpe, 3),
            "max_drawdown_%": round(max_dd * 100, 2),
        })
    return pd.DataFrame(records)


# ── Sidebar ────────────────────────────────────────────────────────────────────
def sidebar(nav_df: pd.DataFrame) -> tuple[list, pd.Timestamp, pd.Timestamp]:
    st.sidebar.markdown("## 📊 Bluestock MF")

    st.sidebar.markdown("---")

    categories = ["All"] + sorted(nav_df["scheme_category"].dropna().unique().tolist())
    sel_cat = st.sidebar.selectbox("Fund Category", categories)

    if sel_cat != "All":
        filtered = nav_df[nav_df["scheme_category"] == sel_cat]
    else:
        filtered = nav_df

    fund_options = filtered["scheme_name"].dropna().unique().tolist()
    sel_funds = st.sidebar.multiselect(
        "Select Funds (max 6)",
        fund_options,
        default=fund_options[:min(5, len(fund_options))],
        max_selections=6,
    )

    min_d = nav_df["date"].min().date()
    max_d = nav_df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(max_d - pd.DateOffset(years=3), max_d),
        min_value=min_d,
        max_value=max_d,
    )
    start = pd.Timestamp(date_range[0]) if len(date_range) > 0 else pd.Timestamp(min_d)
    end   = pd.Timestamp(date_range[1]) if len(date_range) > 1 else pd.Timestamp(max_d)

    st.sidebar.markdown("---")
    st.sidebar.caption("Data: mfapi.in · Built for Bluestock Capstone")
    return sel_funds, start, end


# ── Pages ──────────────────────────────────────────────────────────────────────

def page_overview(nav_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    st.title("📈 Fund Overview")

    if metrics_df.empty:
        st.warning("No metrics available. Run the ETL pipeline first.")
        return

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Funds Tracked", len(metrics_df))
    c2.metric("Avg CAGR", f"{metrics_df['cagr_%'].mean():.2f}%")
    c3.metric("Avg Sharpe Ratio", f"{metrics_df['sharpe_ratio'].mean():.3f}")
    c4.metric("Best Sharpe Fund", metrics_df.loc[metrics_df['sharpe_ratio'].idxmax(), 'scheme_name'].split('Fund')[0].strip())

    st.markdown("---")

    # Scatter: CAGR vs Volatility
    fig = px.scatter(
        metrics_df,
        x="volatility_%", y="cagr_%",
        size=metrics_df["sharpe_ratio"].clip(lower=0.1),
        color="category",
        hover_name="scheme_name",
        hover_data={"sharpe_ratio": True, "max_drawdown_%": True},
        title="Risk–Return Map (bubble size = Sharpe Ratio)",
        labels={"volatility_%": "Annualised Volatility (%)", "cagr_%": "CAGR (%)"},
        color_discrete_sequence=PALETTE,
        template="plotly_white",
    )
    fig.update_layout(height=420, title_font_size=15)
    st.plotly_chart(fig, use_container_width=True)

    # Metrics table
    st.subheader("All Funds — Performance Summary")
    fmt_df = metrics_df[["scheme_name", "category", "latest_nav", "cagr_%",
                          "volatility_%", "sharpe_ratio", "max_drawdown_%"]].copy()
    fmt_df.columns = ["Fund Name", "Category", "NAV (₹)", "CAGR %", "Volatility %", "Sharpe", "Max Drawdown %"]
    st.dataframe(
        fmt_df.style
            .background_gradient(subset=["CAGR %"], cmap="Greens")
            .background_gradient(subset=["Sharpe"], cmap="Blues")
            .background_gradient(subset=["Max Drawdown %"], cmap="Reds_r")
            .format({"NAV (₹)": "₹{:.2f}", "CAGR %": "{:.2f}%",
                     "Volatility %": "{:.2f}%", "Sharpe": "{:.3f}",
                     "Max Drawdown %": "{:.2f}%"}),
        use_container_width=True,
        height=360,
    )


def page_nav_trends(nav_df: pd.DataFrame, sel_funds: list,
                    start: pd.Timestamp, end: pd.Timestamp) -> None:
    st.title("📉 NAV Trends")

    if not sel_funds:
        st.info("Select at least one fund from the sidebar.")
        return

    filtered = nav_df[
        nav_df["scheme_name"].isin(sel_funds) &
        nav_df["date"].between(start, end)
    ].copy()

    # Normalise to 100
    def normalise(grp):
        grp = grp.sort_values("date")
        base = grp["nav"].iloc[0]
        grp["nav_idx"] = grp["nav"] / base * 100
        return grp

    norm_df = filtered.groupby("scheme_name", group_keys=False).apply(normalise)

    tab1, tab2 = st.tabs(["Absolute NAV", "Indexed (Base = 100)"])

    with tab1:
        fig = px.line(filtered, x="date", y="nav", color="scheme_name",
                      title="NAV (₹) Over Time", labels={"nav": "NAV (₹)", "date": ""},
                      color_discrete_sequence=PALETTE, template="plotly_white")
        fig.update_layout(height=420, legend_title="Fund")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = px.line(norm_df, x="date", y="nav_idx", color="scheme_name",
                       title="Indexed NAV (start=100) — Relative Performance",
                       labels={"nav_idx": "Indexed NAV", "date": ""},
                       color_discrete_sequence=PALETTE, template="plotly_white")
        fig2.add_hline(y=100, line_dash="dash", line_color="grey", opacity=0.5)
        fig2.update_layout(height=420, legend_title="Fund")
        st.plotly_chart(fig2, use_container_width=True)

    # Rolling 1-year return heatmap
    st.subheader("Rolling 1-Year Returns (%)")
    pivot_data = []
    for name, grp in filtered.groupby("scheme_name"):
        grp = grp.sort_values("date").set_index("date")
        grp["roll1y"] = grp["nav"].pct_change(252) * 100
        monthly = grp["roll1y"].resample("ME").last().dropna()
        for dt, val in monthly.items():
            pivot_data.append({"Fund": name.split("Fund")[0].strip()[:30],
                                "Month": dt.strftime("%b-%y"), "Return": round(val, 2)})

    if pivot_data:
        pivot_df = pd.DataFrame(pivot_data).pivot_table(
            index="Fund", columns="Month", values="Return"
        )
        fig3 = px.imshow(
            pivot_df, color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0, aspect="auto",
            title="Monthly 1-Year Rolling Return Heatmap (%)",
        )
        fig3.update_layout(height=300)
        st.plotly_chart(fig3, use_container_width=True)


def page_sip_calculator(nav_df: pd.DataFrame) -> None:
    st.title("💰 SIP Calculator")

    fund_options = nav_df["scheme_name"].dropna().unique().tolist()
    fund = st.selectbox("Choose Fund", fund_options)
    col1, col2, col3 = st.columns(3)
    sip_amt  = col1.number_input("Monthly SIP (₹)", 500, 500000, 5000, step=500)
    years    = col2.slider("Investment Period (years)", 1, 30, 10)
    exp_ret  = col3.slider("Expected Annual Return (%)", 1.0, 30.0, 12.0, 0.5)

    # Historical SIP simulation
    grp = nav_df[nav_df["scheme_name"] == fund].sort_values("date").copy()
    if not grp.empty:
        grp = grp.set_index("date").resample("ME").last()["nav"].ffill()
        n_months = min(years * 12, len(grp))
        grp = grp.iloc[-n_months:]

        units = 0.0
        invested = 0.0
        history  = []
        for dt, price in grp.items():
            units_bought = sip_amt / price
            units += units_bought
            invested += sip_amt
            history.append({"Date": dt, "Invested": invested,
                             "Portfolio Value": round(units * price, 2)})

        hist_df = pd.DataFrame(history)
        final_val = hist_df["Portfolio Value"].iloc[-1]
        gain      = final_val - invested
        xirr_approx = (final_val / invested) ** (1 / (n_months / 12)) - 1

        r1, r2, r3 = st.columns(3)
        r1.metric("Total Invested", f"₹{invested:,.0f}")
        r2.metric("Portfolio Value (Historical)", f"₹{final_val:,.0f}")
        r3.metric("Gain / XIRR (approx)", f"₹{gain:,.0f} / {xirr_approx*100:.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["Portfolio Value"],
                                 fill="tozeroy", name="Portfolio Value",
                                 line=dict(color=BRAND_BLUE)))
        fig.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["Invested"],
                                 name="Total Invested", line=dict(color=BRAND_AMBER, dash="dash")))
        fig.update_layout(title="Historical SIP Simulation", template="plotly_white",
                          height=380, yaxis_title="₹ Value")
        st.plotly_chart(fig, use_container_width=True)

    # Theoretical projection
    st.markdown("---")
    st.subheader("Projected Growth (Theoretical)")
    r  = exp_ret / 100 / 12
    n  = years * 12
    fv = sip_amt * ((((1 + r) ** n) - 1) / r) * (1 + r)
    inv = sip_amt * n
    st.metric(
        label=f"Future Value @ {exp_ret}% p.a. for {years} yrs",
        value=f"₹{fv:,.0f}",
        delta=f"+₹{fv - inv:,.0f} gain on ₹{inv:,.0f} invested",
    )


def page_fund_recommender(metrics_df: pd.DataFrame) -> None:
    st.title("🤖 Fund Recommender")

    st.markdown("""
    Answer a few questions and we'll suggest the best-fit funds from the universe.
    """)

    col1, col2 = st.columns(2)
    risk_profile = col1.selectbox(
        "Risk Appetite",
        ["Conservative (Low Volatility)", "Moderate (Balanced)", "Aggressive (High Growth)"]
    )
    horizon = col2.selectbox(
        "Investment Horizon",
        ["< 1 Year", "1–3 Years", "3–5 Years", "5+ Years"]
    )
    goal = st.selectbox(
        "Primary Goal",
        ["Wealth Creation", "Regular Income", "Capital Preservation", "Tax Saving (ELSS)"]
    )

    if metrics_df.empty:
        st.warning("Run ETL pipeline first to populate fund data.")
        return

    df = metrics_df.copy()

    # Score each fund
    df["score"] = 0.0

    # Risk mapping
    if "Conservative" in risk_profile:
        df["score"] += (df["volatility_%"].rank(ascending=True) / len(df)) * 40
    elif "Moderate" in risk_profile:
        mid_vol = df["volatility_%"].median()
        df["score"] += (1 - abs(df["volatility_%"] - mid_vol) / df["volatility_%"].max()) * 40
    else:  # Aggressive
        df["score"] += (df["cagr_%"].rank(ascending=True) / len(df)) * 40

    # Sharpe weight
    df["score"] += (df["sharpe_ratio"].clip(lower=0).rank(ascending=True) / len(df)) * 30

    # Drawdown penalty
    df["score"] += (df["max_drawdown_%"].rank(ascending=False) / len(df)) * 30

    top5 = df.nlargest(5, "score")

    st.subheader("Top 5 Recommended Funds for Your Profile")
    for i, row in top5.iterrows():
        with st.expander(f"#{list(top5.index).index(i)+1}  {row['scheme_name']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("CAGR", f"{row['cagr_%']:.2f}%")
            c2.metric("Sharpe", f"{row['sharpe_ratio']:.3f}")
            c3.metric("Volatility", f"{row['volatility_%']:.2f}%")
            c4.metric("Max Drawdown", f"{row['max_drawdown_%']:.2f}%")
            st.progress(min(row["score"] / 100, 1.0), text=f"Match Score: {row['score']:.1f}/100")

    # Bar chart
    fig = px.bar(
        top5.sort_values("score"), x="score", y="scheme_name",
        orientation="h", title="Recommendation Score (Higher = Better Fit)",
        color="score", color_continuous_scale="Blues",
        labels={"score": "Recommendation Score", "scheme_name": ""},
        template="plotly_white",
    )
    fig.update_layout(height=320, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    nav_df, aum_df, sip_df = load_data()

    if nav_df.empty:
        st.error(
            f"Database not found at `{DB_PATH}`. "
            "Please run the ETL pipeline first (`python b1_cron_etl.py`)."
        )
        st.stop()

    sel_funds, start, end = sidebar(nav_df)
    metrics_df = compute_metrics(nav_df)

    pages = {
        "📊 Overview":         lambda: page_overview(nav_df, metrics_df),
        "📉 NAV Trends":       lambda: page_nav_trends(nav_df, sel_funds, start, end),
        "💰 SIP Calculator":   lambda: page_sip_calculator(nav_df),
        "🤖 Fund Recommender": lambda: page_fund_recommender(metrics_df),
    }

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate", list(pages.keys()))
    pages[page]()


if __name__ == "__main__":
    main()