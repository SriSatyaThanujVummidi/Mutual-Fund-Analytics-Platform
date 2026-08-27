import sqlite3
import warnings
from pathlib import Path
from html import escape

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "bluestock_mf.db"

st.set_page_config(
    page_title="Bluestock MF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM DARK FINANCE UI
# ============================================================

st.html(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --bg: #0A0F1C;
    --surface: #111A2C;
    --surface2: #16223A;
    --border: #22304C;
    --text: #E7ECF7;
    --muted: #8B96AE;
    --blue: #2E6FF2;
    --teal: #14B8A6;
    --amber: #F5A524;
    --red: #F0533D;
}

/* ---------------------------------------------------------
   GLOBAL
--------------------------------------------------------- */

html,
body,
[class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1380px;
    padding-top: 1rem;
    padding-bottom: 4rem;
}

h1,
h2,
h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text) !important;
}

p,
label,
span {
    color: var(--text);
}


/* ---------------------------------------------------------
   HIDE DEFAULT STREAMLIT CHROME
--------------------------------------------------------- */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    background: transparent !important;
}


/* ---------------------------------------------------------
   TOP BRAND BAR
--------------------------------------------------------- */

.brand-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 15px 4px 14px;

    border-bottom: 1px solid var(--border);

    margin-bottom: 0;
}

.brand-left {
    display: flex;
    align-items: center;
    gap: 11px;
}

.brand-dot {
    width: 11px;
    height: 11px;

    background: var(--blue);

    border-radius: 3px;

    box-shadow: 0 0 12px rgba(46,111,242,.65);
}

.brand-name {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 1.05rem;

    font-weight: 700;

    color: var(--text);

    letter-spacing: .01em;
}

.brand-status {
    font-size: .72rem;

    color: var(--teal);

    border: 1px solid rgba(20,184,166,.3);

    background: rgba(20,184,166,.08);

    padding: 5px 10px;

    border-radius: 20px;
}


/* ---------------------------------------------------------
   NAVIGATION
--------------------------------------------------------- */

div[data-testid="stHorizontalBlock"] .nav-radio {
    margin-top: 0;
}

div[role="radiogroup"] {
    gap: 5px !important;

    background: transparent;

    padding: 8px 0;

    border-bottom: 1px solid var(--border);
}

div[role="radiogroup"] label {
    background: transparent !important;

    border: 1px solid transparent !important;

    border-radius: 8px !important;

    padding: 7px 13px !important;

    color: var(--muted) !important;

    transition: all .15s ease;
}

div[role="radiogroup"] label:hover {
    background: var(--surface2) !important;

    color: var(--text) !important;
}

div[role="radiogroup"] label {
    background: transparent !important;
}

div[role="radiogroup"] label:hover {
    background: var(--surface2) !important;
}

div[role="radiogroup"] label p {
    color: var(--muted) !important;
}

div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label:focus-within {
    background: var(--blue) !important;
    border-color: var(--blue) !important;
}

div[role="radiogroup"] label:focus-within p {
    color: white !important;
}


/* ---------------------------------------------------------
   MARKET TICKER
--------------------------------------------------------- */

.ticker {
    width: 100%;

    overflow: hidden;

    white-space: nowrap;

    background: var(--surface);

    border-bottom: 1px solid var(--border);

    padding: 8px 0;

    margin-bottom: 25px;
}

.ticker-inner {
    display: flex;

    gap: 38px;

    width: max-content;

    animation: ticker-scroll 38s linear infinite;
}

.ticker:hover .ticker-inner {
    animation-play-state: paused;
}

.tick {
    display: flex;

    align-items: baseline;

    gap: 7px;

    font-size: .76rem;
}

.tick-name {
    color: var(--text);

    font-weight: 600;
}

.tick-value {
    color: var(--muted);

    font-family: 'IBM Plex Mono', monospace;
}

.tick-up {
    color: var(--teal);

    font-family: 'IBM Plex Mono', monospace;
}

.tick-down {
    color: var(--red);

    font-family: 'IBM Plex Mono', monospace;
}

@keyframes ticker-scroll {
    from {
        transform: translateX(0);
    }

    to {
        transform: translateX(-50%);
    }
}


/* ---------------------------------------------------------
   PAGE HEADER
--------------------------------------------------------- */

.page-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 1.65rem;

    font-weight: 700;

    margin: 0 0 3px;

    color: var(--text);
}

.page-subtitle {
    color: var(--muted);

    font-size: .84rem;

    margin-bottom: 22px;
}


/* ---------------------------------------------------------
   KPI CARDS
--------------------------------------------------------- */

.kpi-card {
    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    padding: 16px 18px;

    min-height: 108px;

    transition: border-color .15s ease,
                transform .15s ease;
}

.kpi-card:hover {
    border-color: #34466B;

    transform: translateY(-1px);
}

.kpi-label {
    color: var(--muted);

    font-size: .69rem;

    font-weight: 600;

    text-transform: uppercase;

    letter-spacing: .07em;
}

.kpi-value {
    font-family: 'IBM Plex Mono', monospace;

    font-size: 1.45rem;

    font-weight: 600;

    margin-top: 7px;

    color: var(--text);

    line-height: 1.25;
}

.kpi-positive {
    color: var(--teal);
}

.kpi-negative {
    color: var(--red);
}

.kpi-small {
    color: var(--muted);

    font-size: .72rem;

    margin-top: 5px;
}


/* ---------------------------------------------------------
   PANELS
--------------------------------------------------------- */

.panel {
    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    padding: 18px 20px;

    margin-bottom: 18px;
}

.panel-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 1rem;

    font-weight: 600;

    color: var(--text);

    margin-bottom: 14px;
}

.panel-caption {
    color: var(--muted);

    font-size: .75rem;
}


/* ---------------------------------------------------------
   STREAMLIT METRIC OVERRIDE
--------------------------------------------------------- */

[data-testid="stMetric"] {
    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    padding: 15px 17px;
}

[data-testid="stMetricLabel"] p {
    color: var(--muted) !important;

    font-size: .69rem !important;

    text-transform: uppercase;

    letter-spacing: .06em;

    font-weight: 600 !important;
}

[data-testid="stMetricValue"] {
    color: var(--text) !important;

    font-family: 'IBM Plex Mono', monospace !important;

    font-size: 1.4rem !important;
}

[data-testid="stMetricDelta"] {
    font-size: .76rem !important;
}


/* ---------------------------------------------------------
   INPUTS
--------------------------------------------------------- */

div[data-baseweb="select"] > div {
    background: var(--surface2) !important;

    border-color: var(--border) !important;

    color: var(--text) !important;

    border-radius: 7px !important;
}

div[data-baseweb="select"] span {
    color: var(--text) !important;
}

input {
    background: var(--surface2) !important;

    color: var(--text) !important;
}

.stSlider {
    padding-top: 5px;
}

.stSlider [data-baseweb="slider"] div {
    color: var(--text);
}


/* ---------------------------------------------------------
   BUTTONS
--------------------------------------------------------- */

.stButton > button {
    background: var(--surface2);

    color: var(--text);

    border: 1px solid var(--border);

    border-radius: 7px;

    font-weight: 600;
}

.stButton > button:hover {
    border-color: var(--blue);

    color: white;
}


/* ---------------------------------------------------------
   TABS
--------------------------------------------------------- */

button[data-baseweb="tab"] {
    color: var(--muted) !important;

    font-weight: 600 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--blue) !important;
}

div[data-baseweb="tab-highlight"] {
    background: var(--blue) !important;
}


/* ---------------------------------------------------------
   TABLE
--------------------------------------------------------- */

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);

    border-radius: 8px;

    overflow: hidden;
}


/* ---------------------------------------------------------
   EXPANDERS
--------------------------------------------------------- */

[data-testid="stExpander"] {
    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 9px;

    margin-bottom: 8px;
}

[data-testid="stExpander"] summary {
    color: var(--text) !important;
}


/* ---------------------------------------------------------
   PROGRESS
--------------------------------------------------------- */

.stProgress > div > div > div {
    background: var(--blue) !important;
}


/* ---------------------------------------------------------
   FOOTER
--------------------------------------------------------- */

.custom-footer {
    text-align: center;

    color: var(--muted);

    font-size: .7rem;

    border-top: 1px solid var(--border);

    padding-top: 20px;

    margin-top: 40px;
}

</style>
""",
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(ttl=600, show_spinner="Loading market data...")
def load_data():

    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)

    try:

        nav_df = pd.read_sql(
            """
            SELECT
                scheme_code,
                scheme_name,
                scheme_category,
                date,
                nav
            FROM nav_data
            """,
            conn,
            parse_dates=["date"],
        )

    except Exception:
        nav_df = pd.DataFrame()

    try:

        aum_df = pd.read_sql(
            "SELECT * FROM aum_data",
            conn,
        )

        if "date" in aum_df.columns:
            aum_df["date"] = pd.to_datetime(aum_df["date"])

    except Exception:
        aum_df = pd.DataFrame()

    try:

        sip_df = pd.read_sql(
            "SELECT * FROM sip_data",
            conn,
        )

        if "date" in sip_df.columns:
            sip_df["date"] = pd.to_datetime(sip_df["date"])

    except Exception:
        sip_df = pd.DataFrame()

    conn.close()

    # Defensive cleanup for deployment environments.
    if not nav_df.empty:
        nav_df["date"] = pd.to_datetime(nav_df["date"], errors="coerce")
        nav_df["nav"] = pd.to_numeric(nav_df["nav"], errors="coerce")
        nav_df = nav_df.dropna(subset=["date", "nav", "scheme_name"])
        nav_df = nav_df.sort_values(["scheme_code", "date"])

    return nav_df, aum_df, sip_df


# ============================================================
# METRICS
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def compute_metrics(nav_df):

    records = []

    if nav_df.empty:
        return pd.DataFrame()

    for code, grp in nav_df.groupby("scheme_code"):

        grp = grp.sort_values("date").copy()

        if len(grp) < 30:
            continue

        grp["ret"] = grp["nav"].pct_change()

        n_years = (
            grp["date"].iloc[-1] -
            grp["date"].iloc[0]
        ).days / 365.25

        if n_years <= 0:
            continue

        first_nav = grp["nav"].iloc[0]
        last_nav = grp["nav"].iloc[-1]

        cagr = (
            last_nav / first_nav
        ) ** (1 / n_years) - 1

        vol = (
            grp["ret"].std() *
            np.sqrt(252)
        )

        sharpe = (
            (cagr - 0.065) / vol
            if vol > 0
            else 0
        )

        roll_max = grp["nav"].cummax()

        drawdown = (
            grp["nav"] - roll_max
        ) / roll_max

        max_dd = drawdown.min()

        records.append(
            {
                "scheme_code": code,
                "scheme_name": grp["scheme_name"].iloc[-1],
                "category": grp["scheme_category"].iloc[-1],
                "latest_nav": last_nav,
                "cagr_%": round(cagr * 100, 2),
                "volatility_%": round(vol * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "max_drawdown_%": round(max_dd * 100, 2),
            }
        )

    return pd.DataFrame(records)


# ============================================================
# TOP BAR
# ============================================================

def render_header():

    st.html(
        """
        <div class="brand-bar">

            <div class="brand-left">

                <span class="brand-dot"></span>

                <span class="brand-name">
                    Bluestock MF Analytics
                </span>

            </div>

            <div class="brand-status">
                ● LIVE ANALYTICS
            </div>

        </div>
        """
    )


# ============================================================
# TICKER
# ============================================================

def render_ticker(metrics_df):

    if metrics_df.empty:
        return

    items = []

    sample = metrics_df.nlargest(
        min(10, len(metrics_df)),
        "cagr_%",
    )

    for _, row in sample.iterrows():

        name = escape(str(row["scheme_name"]))

        if len(name) > 25:
            name = name[:25] + "..."

        cagr = row["cagr_%"]

        cls = "tick-up" if cagr >= 0 else "tick-down"

        sign = "+" if cagr >= 0 else ""

        items.append(
            f"""
            <div class="tick">
                <span class="tick-name">{name}</span>
                <span class="tick-value">NAV ₹{row["latest_nav"]:.2f}</span>
                <span class="{cls}">{sign}{cagr:.2f}%</span>
            </div>
            """
        )

    html = "".join(items)

    st.html(
        f"""
        <div class="ticker">

            <div class="ticker-inner">

                {html}
                {html}

            </div>

        </div>
        """
    )


# ============================================================
# KPI CARD
# ============================================================

def kpi_card(label, value, subtitle=""):

    return f"""
    <div class="kpi-card">

        <div class="kpi-label">
            {label}
        </div>

        <div class="kpi-value">
            {value}
        </div>

        <div class="kpi-small">
            {subtitle}
        </div>

    </div>
    """


# ============================================================
# OVERVIEW
# ============================================================

def page_overview(nav_df, metrics_df):

    st.html(
        """
        <div class="page-title">
            Fund Overview
        </div>

        <div class="page-subtitle">
            Risk, return and performance across the mutual fund universe
        </div>
        """
    )

    if metrics_df.empty:

        st.error(
            "No fund metrics available. "
            "Please run the ETL pipeline first."
        )

        return

    best = metrics_df.loc[
        metrics_df["sharpe_ratio"].idxmax()
    ]

    avg_cagr = metrics_df["cagr_%"].mean()

    avg_sharpe = metrics_df["sharpe_ratio"].mean()

    max_return = metrics_df["cagr_%"].max()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.html(
            kpi_card(
                "Funds Tracked",
                f"{len(metrics_df):,}",
                "Across available schemes",
            )
        )

    with c2:
        st.html(
            kpi_card(
                "Average CAGR",
                f"{avg_cagr:.2f}%",
                "Historical annualised return",
            )
        )

    with c3:
        st.html(
            kpi_card(
                "Average Sharpe",
                f"{avg_sharpe:.3f}",
                "Risk-adjusted performance",
            )
        )

    with c4:
        best_name = best["scheme_name"]

        if "Fund" in best_name:
            best_name = best_name.split("Fund")[0] + "Fund"

        if len(best_name) > 24:
            best_name = best_name[:24] + "..."

        st.html(
            kpi_card(
                "Top Sharpe Fund",
                best_name,
                f"Sharpe {best['sharpe_ratio']:.3f}",
            )
        )

    st.html("<br>")

    # Risk return chart

    st.html(
        """
        <div class="panel-title">
            Risk – Return Map
            <span style="color:#8B96AE;font-weight:400;">
                · bubble size represents Sharpe ratio
            </span>
        </div>
        """
    )

    fig = px.scatter(
        metrics_df,
        x="volatility_%",
        y="cagr_%",
        size=metrics_df["sharpe_ratio"].clip(lower=0.1),
        color="category",
        hover_name="scheme_name",
        hover_data={
            "latest_nav": ":.2f",
            "sharpe_ratio": ":.3f",
            "max_drawdown_%": ":.2f",
        },
        labels={
            "volatility_%": "Annualised Volatility (%)",
            "cagr_%": "CAGR (%)",
            "category": "Category",
        },
        template="plotly_dark",
    )

    fig.update_layout(
        height=430,
        paper_bgcolor="#111A2C",
        plot_bgcolor="#111A2C",
        font=dict(
            family="Inter",
            color="#E7ECF7",
        ),
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    fig.update_xaxes(
        gridcolor="#22304C",
        zerolinecolor="#22304C",
    )

    fig.update_yaxes(
        gridcolor="#22304C",
        zerolinecolor="#22304C",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # Table

    st.html(
        """
        <div class="panel-title">
            All Funds — Performance Summary
        </div>
        """
    )

    display_df = metrics_df[
        [
            "scheme_name",
            "category",
            "latest_nav",
            "cagr_%",
            "volatility_%",
            "sharpe_ratio",
            "max_drawdown_%",
        ]
    ].copy()

    display_df.columns = [
        "Fund Name",
        "Category",
        "NAV (₹)",
        "CAGR %",
        "Volatility %",
        "Sharpe",
        "Max Drawdown %",
    ]

    st.dataframe(
        display_df.style.format(
            {
                "NAV (₹)": "₹{:.2f}",
                "CAGR %": "{:.2f}%",
                "Volatility %": "{:.2f}%",
                "Sharpe": "{:.3f}",
                "Max Drawdown %": "{:.2f}%",
            }
        ),
        width="stretch",
        height=420,
        hide_index=True,
    )


# ============================================================
# NAV TRENDS
# ============================================================

def page_nav_trends(nav_df, metrics_df):

    st.html(
        """
        <div class="page-title">
            NAV Trends
        </div>

        <div class="page-subtitle">
            Compare historical NAV performance across selected funds
        </div>
        """
    )

    if nav_df.empty:
        st.warning("NAV data is not available.")
        return

    categories = [
        "All"
    ] + sorted(
        nav_df["scheme_category"]
        .dropna()
        .unique()
        .tolist()
    )

    col1, col2 = st.columns([1, 2])

    with col1:

        selected_category = st.selectbox(
            "Fund Category",
            categories,
        )

    if selected_category == "All":

        available = (
            nav_df["scheme_name"]
            .dropna()
            .unique()
            .tolist()
        )

    else:

        available = (
            nav_df[
                nav_df["scheme_category"]
                == selected_category
            ]["scheme_name"]
            .dropna()
            .unique()
            .tolist()
        )

    with col2:

        selected_funds = st.multiselect(
            "Funds — maximum 6",
            available,
            default=available[:min(4, len(available))],
            max_selections=6,
        )

    if not selected_funds:

        st.info("Select at least one fund to display the charts.")

        return

    min_date = nav_df["date"].min().date()

    max_date = nav_df["date"].max().date()

    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:

        start = pd.Timestamp(date_range[0])

        end = pd.Timestamp(date_range[1])

    else:

        start = pd.Timestamp(min_date)

        end = pd.Timestamp(max_date)

    filtered = nav_df[
        nav_df["scheme_name"].isin(selected_funds)
        & nav_df["date"].between(start, end)
    ].copy()

    if filtered.empty:

        st.warning("No NAV data found for this selection.")

        return

    tab1, tab2, tab3 = st.tabs(
        [
            "Absolute NAV",
            "Indexed Performance",
            "Rolling Returns",
        ]
    )

    # --------------------------------------------------------
    # ABSOLUTE NAV
    # --------------------------------------------------------

    with tab1:

        fig = px.line(
            filtered,
            x="date",
            y="nav",
            color="scheme_name",
            labels={
                "nav": "NAV (₹)",
                "date": "",
                "scheme_name": "Fund",
            },
            template="plotly_dark",
        )

        fig.update_layout(
            height=440,
            paper_bgcolor="#111A2C",
            plot_bgcolor="#111A2C",
            font=dict(
                family="Inter",
                color="#E7ECF7",
            ),
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        fig.update_xaxes(
            gridcolor="#22304C"
        )

        fig.update_yaxes(
            gridcolor="#22304C"
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # --------------------------------------------------------
    # INDEXED
    # --------------------------------------------------------

    with tab2:

        def normalize(group):

            group = group.sort_values("date").copy()

            base = group["nav"].iloc[0]

            group["indexed"] = (
                group["nav"] / base
            ) * 100

            return group

        indexed_df = (
            filtered
            .groupby(
                "scheme_name",
                group_keys=False,
            )
            .apply(normalize)
        )

        fig = px.line(
            indexed_df,
            x="date",
            y="indexed",
            color="scheme_name",
            labels={
                "indexed": "Indexed NAV",
                "date": "",
                "scheme_name": "Fund",
            },
            template="plotly_dark",
        )

        fig.add_hline(
            y=100,
            line_dash="dash",
            line_color="#8B96AE",
            opacity=.5,
        )

        fig.update_layout(
            height=440,
            paper_bgcolor="#111A2C",
            plot_bgcolor="#111A2C",
            font=dict(
                family="Inter",
                color="#E7ECF7",
            ),
        )

        fig.update_xaxes(
            gridcolor="#22304C"
        )

        fig.update_yaxes(
            gridcolor="#22304C"
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # --------------------------------------------------------
    # ROLLING RETURN
    # --------------------------------------------------------

    with tab3:

        pivot_data = []

        for name, grp in filtered.groupby(
            "scheme_name"
        ):

            grp = (
                grp
                .sort_values("date")
                .set_index("date")
            )

            grp["rolling_return"] = (
                grp["nav"]
                .pct_change(252)
                * 100
            )

            monthly = (
                grp["rolling_return"]
                .resample("ME")
                .last()
                .dropna()
            )

            for dt, value in monthly.items():

                pivot_data.append(
                    {
                        "Fund": name[:35],
                        "Month": dt.strftime("%b-%y"),
                        "Return": round(
                            value,
                            2,
                        ),
                    }
                )

        if pivot_data:

            pivot_df = (
                pd.DataFrame(pivot_data)
                .pivot_table(
                    index="Fund",
                    columns="Month",
                    values="Return",
                )
            )

            fig = px.imshow(
                pivot_df,
                color_continuous_scale=[
                    "#F0533D",
                    "#16223A",
                    "#14B8A6",
                ],
                color_continuous_midpoint=0,
                aspect="auto",
            )

            fig.update_layout(
                height=380,
                paper_bgcolor="#111A2C",
                plot_bgcolor="#111A2C",
                font=dict(
                    family="Inter",
                    color="#E7ECF7",
                ),
                coloraxis_colorbar=dict(
                    title="Return %",
                ),
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        else:

            st.info(
                "Not enough historical data to calculate rolling returns."
            )


# ============================================================
# SIP CALCULATOR
# ============================================================

def page_sip_calculator(nav_df):

    st.html(
        """
        <div class="page-title">
            SIP Calculator
        </div>

        <div class="page-subtitle">
            Simulate historical SIP performance and project future growth
        </div>
        """
    )

    fund_options = (
        nav_df["scheme_name"]
        .dropna()
        .unique()
        .tolist()
    )

    if not fund_options:

        st.warning("No fund data available.")

        return

    col1, col2, col3 = st.columns(3)

    with col1:

        fund = st.selectbox(
            "Choose Fund",
            fund_options,
        )

    with col2:

        sip_amt = st.number_input(
            "Monthly SIP (₹)",
            min_value=500,
            max_value=500000,
            value=5000,
            step=500,
        )

    with col3:

        years = st.slider(
            "Investment Period",
            min_value=1,
            max_value=30,
            value=10,
        )

    exp_ret = st.slider(
        "Expected Annual Return (%)",
        min_value=1.0,
        max_value=30.0,
        value=12.0,
        step=.5,
    )

    grp = (
        nav_df[
            nav_df["scheme_name"] == fund
        ]
        .sort_values("date")
        .copy()
    )

    if grp.empty:

        st.warning(
            "No NAV history found for this fund."
        )

        return

    monthly_nav = (
        grp
        .set_index("date")
        .resample("ME")
        .last()["nav"]
        .ffill()
    )

    n_months = min(
        years * 12,
        len(monthly_nav),
    )

    monthly_nav = monthly_nav.iloc[-n_months:]

    units = 0.0

    invested = 0.0

    history = []

    for dt, price in monthly_nav.items():

        units += sip_amt / price

        invested += sip_amt

        portfolio_value = units * price

        history.append(
            {
                "Date": dt,
                "Invested": invested,
                "Portfolio Value": portfolio_value,
            }
        )

    hist_df = pd.DataFrame(history)

    final_value = hist_df[
        "Portfolio Value"
    ].iloc[-1]

    gain = final_value - invested

    period_years = n_months / 12

    xirr_approx = (
        (final_value / invested)
        ** (1 / max(period_years, .01))
        - 1
    )

    st.html("<br>")

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "Total Invested",
            f"₹{invested:,.0f}",
        )

    with b:
        st.metric(
            "Portfolio Value",
            f"₹{final_value:,.0f}",
        )

    with c:
        st.metric(
            "Gain",
            f"₹{gain:,.0f}",
            delta=f"{gain / invested * 100:.1f}%",
        )

    with d:
        st.metric(
            "Approx. XIRR",
            f"{xirr_approx * 100:.2f}%",
        )

    st.html(
        """
        <br>

        <div class="panel-title">
            Historical SIP Simulation
        </div>
        """
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=hist_df["Date"],
            y=hist_df["Portfolio Value"],
            name="Portfolio Value",
            fill="tozeroy",
            line=dict(
                color="#2E6FF2",
                width=2,
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hist_df["Date"],
            y=hist_df["Invested"],
            name="Total Invested",
            line=dict(
                color="#F5A524",
                width=2,
                dash="dash",
            ),
        )
    )

    fig.update_layout(
        height=420,
        template="plotly_dark",
        paper_bgcolor="#111A2C",
        plot_bgcolor="#111A2C",
        font=dict(
            family="Inter",
            color="#E7ECF7",
        ),
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
    )

    fig.update_xaxes(
        gridcolor="#22304C"
    )

    fig.update_yaxes(
        gridcolor="#22304C"
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # --------------------------------------------------------
    # PROJECTION
    # --------------------------------------------------------

    st.html(
        """
        <div class="panel-title">
            Projected Growth
            <span style="color:#8B96AE;font-weight:400;">
                · theoretical projection
            </span>
        </div>
        """
    )

    monthly_rate = exp_ret / 100 / 12

    total_months = years * 12

    future_value = (
        sip_amt
        * (
            (
                (1 + monthly_rate)
                ** total_months
            ) - 1
        )
        / monthly_rate
        * (1 + monthly_rate)
    )

    total_investment = (
        sip_amt * total_months
    )

    projected_gain = (
        future_value - total_investment
    )

    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "Future Value",
            f"₹{future_value:,.0f}",
        )

    with p2:

        st.metric(
            "Investment",
            f"₹{total_investment:,.0f}",
        )

    with p3:

        st.metric(
            "Projected Gain",
            f"₹{projected_gain:,.0f}",
        )


# ============================================================
# FUND RECOMMENDER
# ============================================================

def page_fund_recommender(metrics_df):

    st.html(
        """
        <div class="page-title">
            Fund Recommender
        </div>

        <div class="page-subtitle">
            Build a profile and rank funds based on risk, return and
            risk-adjusted performance
        </div>
        """
    )

    if metrics_df.empty:

        st.warning(
            "Fund metrics are not available."
        )

        return

    col1, col2, col3 = st.columns(3)

    with col1:

        risk_profile = st.selectbox(
            "Risk Appetite",
            [
                "Conservative (Low Volatility)",
                "Moderate (Balanced)",
                "Aggressive (High Growth)",
            ],
        )

    with col2:

        horizon = st.selectbox(
            "Investment Horizon",
            [
                "< 1 Year",
                "1–3 Years",
                "3–5 Years",
                "5+ Years",
            ],
        )

    with col3:

        goal = st.selectbox(
            "Primary Goal",
            [
                "Wealth Creation",
                "Regular Income",
                "Capital Preservation",
                "Tax Saving (ELSS)",
            ],
        )

    df = metrics_df.copy()

    df["score"] = 0.0

    # --------------------------------------------------------
    # RISK SCORE
    # --------------------------------------------------------

    if "Conservative" in risk_profile:

        df["score"] += (
            df["volatility_%"]
            .rank(ascending=True)
            / len(df)
        ) * 40

    elif "Moderate" in risk_profile:

        median_vol = (
            df["volatility_%"].median()
        )

        df["score"] += (
            1
            - (
                abs(
                    df["volatility_%"]
                    - median_vol
                )
                / max(
                    df["volatility_%"].max(),
                    1,
                )
            )
        ) * 40

    else:

        df["score"] += (
            df["cagr_%"]
            .rank(ascending=True)
            / len(df)
        ) * 40

    # --------------------------------------------------------
    # SHARPE
    # --------------------------------------------------------

    df["score"] += (
        df["sharpe_ratio"]
        .clip(lower=0)
        .rank(ascending=True)
        / len(df)
    ) * 30

    # --------------------------------------------------------
    # DRAWDOWN
    # --------------------------------------------------------

    df["score"] += (
        df["max_drawdown_%"]
        .rank(ascending=False)
        / len(df)
    ) * 30

    # --------------------------------------------------------
    # GOAL ADJUSTMENT
    # --------------------------------------------------------

    if goal == "Tax Saving (ELSS)":

        elss_mask = df["scheme_name"].str.contains(
            "Tax Saver|ELSS",
            case=False,
            na=False,
        )

        df.loc[elss_mask, "score"] += 15

    top5 = df.nlargest(
        5,
        "score",
    ).copy()

    st.html("<br>")

    st.html(
        """
        <div class="panel-title">
            Top 5 Recommended Funds
        </div>
        """
    )

    for rank, (_, row) in enumerate(
        top5.iterrows(),
        start=1,
    ):

        with st.expander(
            f"#{rank}  {row['scheme_name']}"
        ):

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "CAGR",
                    f"{row['cagr_%']:.2f}%",
                )

            with c2:
                st.metric(
                    "Sharpe",
                    f"{row['sharpe_ratio']:.3f}",
                )

            with c3:
                st.metric(
                    "Volatility",
                    f"{row['volatility_%']:.2f}%",
                )

            with c4:
                st.metric(
                    "Max Drawdown",
                    f"{row['max_drawdown_%']:.2f}%",
                )

            score = min(
                max(row["score"], 0),
                100,
            )

            st.progress(
                score / 100,
                text=f"Match Score: {score:.1f}/100",
            )

    # --------------------------------------------------------
    # SCORE CHART
    # --------------------------------------------------------

    st.html(
        "<br>"
    )

    st.html(
        """
        <div class="panel-title">
            Recommendation Score
        </div>
        """
    )

    chart_df = (
        top5
        .sort_values("score")
        .copy()
    )

    chart_df["display_name"] = (
        chart_df["scheme_name"]
        .str.replace(
            " Fund",
            "",
            regex=False,
        )
        .str.slice(0, 32)
    )

    fig = px.bar(
        chart_df,
        x="score",
        y="display_name",
        orientation="h",
        labels={
            "score": "Recommendation Score",
            "display_name": "",
        },
        template="plotly_dark",
    )

    fig.update_traces(
        marker_color="#2E6FF2",
    )

    fig.update_layout(
        height=350,
        paper_bgcolor="#111A2C",
        plot_bgcolor="#111A2C",
        font=dict(
            family="Inter",
            color="#E7ECF7",
        ),
        showlegend=False,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
    )

    fig.update_xaxes(
        gridcolor="#22304C",
        range=[0, 100],
    )

    fig.update_yaxes(
        gridcolor="#22304C"
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        f"Profile: {risk_profile} · "
        f"Horizon: {horizon} · "
        f"Goal: {goal}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    nav_df, aum_df, sip_df = load_data()

    if nav_df.empty:

        st.error(
            f"Database not found or NAV data is empty:\n\n"
            f"`{DB_PATH}`\n\n"
            "Please run the ETL pipeline first."
        )

        st.stop()

    metrics_df = compute_metrics(
        nav_df
    )

    # Header

    render_header()

    # Ticker

    render_ticker(
        metrics_df
    )

    # Navigation

    page = st.radio(
        "Navigation",
        [
            "📊 Overview",
            "📉 NAV Trends",
            "💰 SIP Calculator",
            "🤖 Fund Recommender",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.html(
        "<br>"
    )

    # Pages

    if page == "📊 Overview":

        page_overview(
            nav_df,
            metrics_df,
        )

    elif page == "📉 NAV Trends":

        page_nav_trends(
            nav_df,
            metrics_df,
        )

    elif page == "💰 SIP Calculator":

        page_sip_calculator(
            nav_df,
        )

    elif page == "🤖 Fund Recommender":

        page_fund_recommender(
            metrics_df,
        )

    # Footer

    st.html(
        """
        <div class="custom-footer">

            Data: AMFI / mfapi.in ·
            Bluestock Mutual Fund Analytics Capstone ·
            Not financial advice

        </div>
        """
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
