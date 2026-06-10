"""
B5 — Automated HTML Email Report: Weekly MF Performance Summary
================================================================
Generates a styled HTML email with fund performance metrics and sends it
via SMTP (Gmail / any SMTP provider).

Usage:
    # Preview HTML only (no email sent):
    python b5_email_report.py --preview

    # Send email:
    python b5_email_report.py --send --to "you@example.com"

    # Schedule weekly (every Monday 8 AM) with Python scheduler:
    python b5_email_report.py --schedule --to "you@example.com"

SMTP credentials via env vars (never hardcode):
    export SMTP_HOST=smtp.gmail.com
    export SMTP_PORT=587
    export SMTP_USER=your@gmail.com
    export SMTP_PASS=your_app_password     # Gmail app password
"""

import os
import sqlite3
import smtplib
import argparse
import warnings
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path
from time import sleep

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import schedule as _schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False

warnings.filterwarnings("ignore")

# ── Paths & Config ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DB_PATH    = BASE_DIR / "data" / "bluestock_mf.db"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRADING_DAYS    = 252
RISK_FREE_RATE  = 0.065
REPORT_TITLE    = "Bluestock MF — Weekly Performance Report"

BRAND_BLUE  = "#0057B8"
BRAND_LIGHT = "#EFF6FF"
BRAND_TEAL  = "#0D9488"
BRAND_AMBER = "#D97706"
BRAND_RED   = "#DC2626"
BRAND_GREEN = "#16A34A"


# ── Data helpers ───────────────────────────────────────────────────────────────

def load_nav(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT scheme_code, scheme_name, scheme_category, date, nav "
        "FROM nav_data ORDER BY scheme_code, date",
        conn, parse_dates=["date"]
    )
    return df


def compute_metrics(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Per-fund performance metrics for the email report."""
    records = []
    today   = nav_df["date"].max()
    one_wk  = today - timedelta(days=7)
    one_mo  = today - timedelta(days=30)
    one_yr  = today - timedelta(days=365)
    three_yr= today - timedelta(days=365 * 3)

    for code, grp in nav_df.groupby("scheme_code"):
        grp = grp.sort_values("date").set_index("date")["nav"]
        if len(grp) < 30:
            continue

        def ret_since(since_date):
            past = grp[grp.index <= since_date]
            if past.empty:
                return None
            return (grp.iloc[-1] / past.iloc[-1] - 1) * 100

        ret_1w  = ret_since(one_wk)
        ret_1m  = ret_since(one_mo)
        ret_1y  = ret_since(one_yr)
        ret_3y  = ret_since(three_yr)

        # Annualised metrics
        daily_ret = grp.pct_change().dropna()
        vol = daily_ret.std() * np.sqrt(TRADING_DAYS) * 100
        n_years = (grp.index[-1] - grp.index[0]).days / 365.25
        cagr = ((grp.iloc[-1] / grp.iloc[0]) ** (1 / max(n_years, 0.01)) - 1) * 100

        roll_max = grp.cummax()
        max_dd   = ((grp - roll_max) / roll_max).min() * 100

        # 52-week high / low
        yr_slice = grp[grp.index >= one_yr]
        hi_52    = yr_slice.max() if not yr_slice.empty else None
        lo_52    = yr_slice.min() if not yr_slice.empty else None

        name = nav_df[nav_df["scheme_code"] == code]["scheme_name"].iloc[0]
        cat  = nav_df[nav_df["scheme_code"] == code]["scheme_category"].iloc[0]

        records.append({
            "scheme_code": code,
            "scheme_name": name,
            "category":    cat,
            "latest_nav":  round(grp.iloc[-1], 4),
            "1W_%":        round(ret_1w,  2) if ret_1w  is not None else None,
            "1M_%":        round(ret_1m,  2) if ret_1m  is not None else None,
            "1Y_%":        round(ret_1y,  2) if ret_1y  is not None else None,
            "3Y_%":        round(ret_3y,  2) if ret_3y  is not None else None,
            "cagr_%":      round(cagr, 2),
            "volatility_%":round(vol, 2),
            "max_dd_%":    round(max_dd, 2),
            "52w_high":    round(hi_52, 4) if hi_52 is not None else None,
            "52w_low":     round(lo_52, 4) if lo_52 is not None else None,
        })
    return pd.DataFrame(records).sort_values("cagr_%", ascending=False).reset_index(drop=True)


# ── Inline chart generators ────────────────────────────────────────────────────

def sparkline_base64(series: pd.Series, colour: str = BRAND_BLUE) -> str:
    """Return a tiny sparkline as a base64 PNG."""
    fig, ax = plt.subplots(figsize=(2.2, 0.55))
    ax.plot(series.values, color=colour, lw=1.5)
    ax.fill_between(range(len(series)), series.values,
                    series.values.min(), alpha=0.15, color=colour)
    ax.axis("off")
    fig.patch.set_alpha(0)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight",
                transparent=True, pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def top5_bar_base64(metrics_df: pd.DataFrame, col: str, title: str) -> str:
    top5 = metrics_df.nlargest(5, col)[["scheme_name", col]].copy()
    top5["label"] = top5["scheme_name"].str.split("Fund").str[0].str.strip().str[:25]
    clrs = [BRAND_BLUE if v >= 0 else BRAND_RED for v in top5[col]]

    fig, ax = plt.subplots(figsize=(5.5, 2.4))
    fig.patch.set_facecolor("#FFFFFF")
    bars = ax.barh(top5["label"], top5[col], color=clrs, height=0.55, edgecolor="white")
    for bar, val in zip(bars, top5[col]):
        ax.text(bar.get_width() + (0.3 if val >= 0 else -0.3),
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", ha="left" if val >= 0 else "right",
                fontsize=7.5, color="#374151")
    ax.set_xlabel("%", fontsize=7)
    ax.set_title(title, fontsize=8.5, fontweight="bold", color="#1E3A5F")
    ax.axvline(0, color="#9CA3AF", lw=0.7)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=7)
    ax.tick_params(axis="x", labelsize=7)
    ax.invert_yaxis()
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ── HTML builder ───────────────────────────────────────────────────────────────

def _colour_cell(val: float | None, decimals: int = 2) -> str:
    """Return an HTML <td> coloured green/red based on sign."""
    if val is None:
        return '<td style="color:#9CA3AF;">N/A</td>'
    clr = BRAND_GREEN if val >= 0 else BRAND_RED
    arrow = "▲" if val >= 0 else "▼"
    return (f'<td style="color:{clr};font-weight:600;text-align:right;">'
            f'{arrow} {val:.{decimals}f}%</td>')


def build_html(metrics_df: pd.DataFrame, nav_df: pd.DataFrame) -> str:
    today_str   = datetime.now().strftime("%d %B %Y")
    week_start  = (datetime.now() - timedelta(days=7)).strftime("%d %b")
    week_end    = datetime.now().strftime("%d %b %Y")
    n_funds     = len(metrics_df)
    avg_cagr    = metrics_df["cagr_%"].mean()
    best_fund   = metrics_df.iloc[0]["scheme_name"].split("Fund")[0].strip()
    best_cagr   = metrics_df.iloc[0]["cagr_%"]

    # Charts
    bar_b64_cagr = top5_bar_base64(metrics_df, "cagr_%",  "Top 5 Funds by CAGR")
    bar_b64_1y   = top5_bar_base64(metrics_df, "1Y_%",    "Top 5 Funds — 1-Year Return")

    # Sparklines for top 5 by CAGR
    top5_codes = metrics_df.head(5)["scheme_code"].tolist()
    sparklines  = {}
    for code in top5_codes:
        series = (nav_df[nav_df["scheme_code"] == code]
                  .sort_values("date")
                  .tail(90)["nav"]
                  .reset_index(drop=True))
        sparklines[code] = sparkline_base64(series, BRAND_BLUE)

    # Table rows
    table_rows = ""
    for i, row in metrics_df.iterrows():
        bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFF"
        spark_html = ""
        if row["scheme_code"] in sparklines:
            spark_html = (f'<img src="data:image/png;base64,{sparklines[row["scheme_code"]]}" '
                          f'height="28" style="vertical-align:middle;"/>')
        short_name = row["scheme_name"][:50] + ("…" if len(row["scheme_name"]) > 50 else "")

        table_rows += f"""
        <tr style="background:{bg};">
          <td style="padding:7px 10px;font-size:12px;max-width:220px;">{short_name}</td>
          <td style="padding:7px 4px;font-size:11px;color:#6B7280;text-align:center;">{row['category'][:18]}</td>
          <td style="padding:7px 8px;text-align:right;font-weight:600;">₹{row['latest_nav']:.2f}</td>
          {_colour_cell(row["1W_%"])}
          {_colour_cell(row["1M_%"])}
          {_colour_cell(row["1Y_%"])}
          {_colour_cell(row["cagr_%"])}
          <td style="padding:7px 8px;text-align:right;color:#6B7280;">{row['volatility_%']:.1f}%</td>
          <td style="padding:7px 8px;">{spark_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{REPORT_TITLE}</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:'Segoe UI',Arial,sans-serif;">

<!-- Wrapper -->
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#F3F4F6;padding:24px 0;">
<tr><td align="center">
<table width="660" cellpadding="0" cellspacing="0"
       style="background:#FFFFFF;border-radius:12px;
              box-shadow:0 4px 20px rgba(0,0,0,0.08);overflow:hidden;">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,{BRAND_BLUE} 0%,#1D4ED8 100%);
               padding:28px 32px;text-align:center;">
      <div style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:0.5px;">
        📊 {REPORT_TITLE}
      </div>
      <div style="font-size:13px;color:#BFDBFE;margin-top:6px;">
        Week: {week_start} — {week_end}
      </div>
    </td>
  </tr>

  <!-- KPI Row -->
  <tr>
    <td style="padding:20px 32px 10px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:{BRAND_LIGHT};border-radius:8px;padding:14px 16px;
                     text-align:center;width:33%;">
            <div style="font-size:22px;font-weight:700;color:{BRAND_BLUE};">{n_funds}</div>
            <div style="font-size:11px;color:#6B7280;margin-top:4px;font-weight:600;">
              FUNDS TRACKED</div>
          </td>
          <td width="16"></td>
          <td style="background:{BRAND_LIGHT};border-radius:8px;padding:14px 16px;
                     text-align:center;width:33%;">
            <div style="font-size:22px;font-weight:700;color:{BRAND_GREEN};">
              {avg_cagr:.1f}%</div>
            <div style="font-size:11px;color:#6B7280;margin-top:4px;font-weight:600;">
              AVG CAGR</div>
          </td>
          <td width="16"></td>
          <td style="background:{BRAND_LIGHT};border-radius:8px;padding:14px 16px;
                     text-align:center;width:33%;">
            <div style="font-size:13px;font-weight:700;color:{BRAND_TEAL};">
              {best_fund[:20]}</div>
            <div style="font-size:11px;color:#6B7280;margin-top:4px;font-weight:600;">
              BEST CAGR: {best_cagr:.1f}%</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Charts row -->
  <tr>
    <td style="padding:10px 32px 20px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="text-align:center;">
            <img src="data:image/png;base64,{bar_b64_cagr}"
                 width="290" style="border-radius:8px;border:1px solid #E5E7EB;"/>
          </td>
          <td width="12"></td>
          <td style="text-align:center;">
            <img src="data:image/png;base64,{bar_b64_1y}"
                 width="290" style="border-radius:8px;border:1px solid #E5E7EB;"/>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Table header -->
  <tr>
    <td style="padding:0 32px 0;">
      <div style="font-size:14px;font-weight:700;color:#1E3A5F;
                  padding-bottom:8px;border-bottom:2px solid {BRAND_BLUE};">
        All Fund Performance (as of {today_str})
      </div>
    </td>
  </tr>

  <!-- Performance table -->
  <tr>
    <td style="padding:8px 20px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="font-size:12px;border-collapse:collapse;">
        <thead>
          <tr style="background:{BRAND_BLUE};color:#FFFFFF;">
            <th style="padding:8px 10px;text-align:left;">Fund</th>
            <th style="padding:8px 4px;text-align:center;">Category</th>
            <th style="padding:8px 8px;text-align:right;">NAV</th>
            <th style="padding:8px 8px;text-align:right;">1W</th>
            <th style="padding:8px 8px;text-align:right;">1M</th>
            <th style="padding:8px 8px;text-align:right;">1Y</th>
            <th style="padding:8px 8px;text-align:right;">CAGR</th>
            <th style="padding:8px 8px;text-align:right;">Vol</th>
            <th style="padding:8px 8px;text-align:center;">90d Trend</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background:#F8FAFF;border-top:1px solid #E5E7EB;
               padding:16px 32px;text-align:center;">
      <div style="font-size:11px;color:#9CA3AF;">
        Generated automatically by Bluestock MF Analytics Pipeline &nbsp;·&nbsp;
        Data source: mfapi.in &nbsp;·&nbsp; {today_str}<br/>
        <span style="font-size:10px;">
          Disclaimer: This is for educational purposes only.
          Past performance is not indicative of future results.
        </span>
      </div>
    </td>
  </tr>

</table>
</td></tr>
</table>

</body>
</html>"""
    return html


# ── Email sender ───────────────────────────────────────────────────────────────

def send_email(html_body: str, to_addr: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        raise EnvironmentError(
            "SMTP credentials not set.\n"
            "Export SMTP_USER and SMTP_PASS environment variables."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"📊 Bluestock MF Weekly Report — "
        f"{datetime.now().strftime('%d %b %Y')}"
    )
    msg["From"]    = smtp_user
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addr, msg.as_string())

    print(f"✅  Email sent to {to_addr}")


# ── Core report job ────────────────────────────────────────────────────────────

def generate_and_send(to_addr: str | None = None, preview: bool = False) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Generating weekly report…")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run ETL pipeline first."
        )

    conn       = sqlite3.connect(DB_PATH)
    nav_df     = load_nav(conn)
    conn.close()

    metrics_df = compute_metrics(nav_df)
    html_body  = build_html(metrics_df, nav_df)

    # Always save preview HTML
    preview_path = OUTPUT_DIR / "b5_email_preview.html"
    preview_path.write_text(html_body, encoding="utf-8")
    print(f"Preview saved → {preview_path}")

    if not preview and to_addr:
        send_email(html_body, to_addr)
    elif preview:
        print("Preview mode — no email sent. Open b5_email_preview.html in a browser.")


# ── Scheduler ──────────────────────────────────────────────────────────────────

def run_scheduler(to_addr: str) -> None:
    if not HAS_SCHEDULE:
        raise ImportError("Run: pip install schedule")

    def job():
        try:
            generate_and_send(to_addr=to_addr)
        except Exception as exc:
            print(f"[ERROR] {exc}")

    _schedule.every().monday.at("08:00").do(job)
    print("Scheduler active — email every Monday at 08:00. (Ctrl+C to stop)")
    while True:
        _schedule.run_pending()
        sleep(30)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B5 Bluestock HTML Email Report")
    parser.add_argument("--preview",  action="store_true",
                        help="Generate HTML preview only (no email)")
    parser.add_argument("--send",     action="store_true",
                        help="Build and send the email")
    parser.add_argument("--schedule", action="store_true",
                        help="Run as weekly scheduler (every Monday 08:00)")
    parser.add_argument("--to", type=str, default=None,
                        help="Recipient email address")
    args = parser.parse_args()

    if args.schedule:
        if not args.to:
            parser.error("--to is required with --schedule")
        run_scheduler(args.to)
    elif args.send:
        if not args.to:
            parser.error("--to is required with --send")
        generate_and_send(to_addr=args.to, preview=False)
    else:
        generate_and_send(preview=True)
