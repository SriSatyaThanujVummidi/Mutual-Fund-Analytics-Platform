# Bluestock MF Capstone — Bonus Challenges (+10 marks each)

Place all files in: `bluestock_mf_capstone/scripts/`

---

## B1 — Scheduled ETL (`b1_cron_etl.py`)
Auto-fetches live NAV from **mfapi.in** for 10 funds and upserts into SQLite.

### Install
```bash
pip install requests schedule
```

### Run once
```bash
python b1_cron_etl.py
```

### Python scheduler (weekdays 20:00)
```bash
python b1_cron_etl.py --schedule
```

### System cron (add via `crontab -e`)
```
0 20 * * 1-5 /usr/bin/python3 /full/path/to/b1_cron_etl.py >> /full/path/to/logs/etl.log 2>&1
```

**What it does:**
- Hits `https://api.mfapi.in/mf/<scheme_code>` for 10 funds
- Upserts rows into `nav_data` (PRIMARY KEY = scheme_code + date, no duplicates)
- Writes an audit row to `etl_log` table after each run
- Logs to `logs/etl_cron.log`

---

## B2 — Streamlit Dashboard (`b2_streamlit_app.py`)
4-page interactive analytics web app as a Power BI alternative.

### Install
```bash
pip install streamlit plotly
```

### Run
```bash
streamlit run b2_streamlit_app.py
```

**Pages:**
| Page | Content |
|------|---------|
| 📊 Overview | KPI cards, Risk–Return scatter, styled metrics table |
| 📉 NAV Trends | Absolute + indexed NAV lines, rolling 1Y heatmap |
| 💰 SIP Calculator | Historical simulation + theoretical projection |
| 🤖 Fund Recommender | Rule-based scoring by risk appetite, horizon, goal |

---

## B3 — Monte Carlo Simulation (`b3_monte_carlo.py`)
Projects NAV over 5 years using **Geometric Brownian Motion (GBM)**.

### Install
```bash
pip install matplotlib numpy pandas
```

### Run
```bash
python b3_monte_carlo.py
```

**Outputs:**
- `outputs/b3_monte_carlo_<code>.png` — fan chart per fund
- `outputs/b3_monte_carlo_summary.csv` — P5/P25/P50/P75/P95, CAGR, prob(2x)

**Methodology:**
- Calibrates daily μ and σ from historical log-returns
- Simulates **1,000 paths** per fund over 5 × 252 = 1,260 steps
- Plots P5/P10/P25–P75/P90/P95 uncertainty bands
- Reports median CAGR and probability of doubling

---

## B4 — Efficient Frontier (`b4_efficient_frontier.py`)
**Markowitz Mean-Variance Optimisation** for 5 selected funds.

### Install
```bash
pip install matplotlib numpy pandas scipy
```

### Run
```bash
python b4_efficient_frontier.py
```

**Outputs:**
- `outputs/b4_efficient_frontier.png` — scatter + frontier + weight bars
- `outputs/b4_portfolio_weights.csv` — weights for 3 optimal portfolios
- `outputs/b4_efficient_frontier_points.csv` — frontier (ret, std, sharpe)

**Portfolios computed:**
| Portfolio | Objective |
|-----------|-----------|
| Max Sharpe | Maximise (Return − Rf) / σ via SLSQP |
| Min Variance | Minimise σ² via SLSQP |
| Equal Weight | 1/N baseline |

---

## B5 — HTML Email Report (`b5_email_report.py`)
Generates a styled HTML email with fund performance and sends via SMTP.

### Install
```bash
pip install matplotlib numpy pandas schedule
```

### Environment variables (never hardcode credentials)
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your@gmail.com
export SMTP_PASS=your_app_password    # Gmail → Settings → App Passwords
```

### Preview HTML (no email)
```bash
python b5_email_report.py --preview
# Opens outputs/b5_email_preview.html in browser to inspect
```

### Send immediately
```bash
python b5_email_report.py --send --to recipient@example.com
```

### Weekly scheduler (every Monday 08:00)
```bash
python b5_email_report.py --schedule --to recipient@example.com
```

**Email contents:**
- KPI header: funds tracked, avg CAGR, best fund
- Bar charts: Top 5 by CAGR, Top 5 by 1Y Return (embedded as base64 PNG)
- Full performance table: NAV, 1W/1M/1Y/CAGR, volatility, 90-day sparklines
- All images are **inline base64** — no external links, works in all clients

---

## Dependency Summary

```bash
pip install requests schedule streamlit plotly matplotlib numpy pandas scipy
```

