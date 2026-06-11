# Bluestock MF Analytics Capstone

**Bluestock Fintech | Mutual Fund Analytics | Capstone Project**

A complete end-to-end mutual fund analytics system — ETL pipeline, performance metrics engine, interactive Streamlit dashboard, Monte Carlo simulation, and portfolio optimisation — built on real AMFI/mfapi.in data.

---

## Project Overview

This capstone analyses 40 mutual fund schemes across 10 fund houses, covering equity and debt categories. It ingests raw NAV and transaction data, cleans and stores it in a SQLite star schema, computes risk/return metrics, and surfaces insights through an interactive dashboard and automated email reports.

**Tech Stack:** Python · Pandas · SQLite · SQLAlchemy · Streamlit · Plotly · Matplotlib · SciPy · mfapi.in API

---

## Repository Structure

```
bluestock_mf_capstone/
├── data/
│   ├── raw/           ← original downloaded files
│   ├── processed/     ← cleaned, merged CSVs
│   └── db/            ← bluestock_mf.db (SQLite)
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda_analysis.ipynb
│   ├── 04_performance_analytics.ipynb
│   └── 05_advanced_analytics.ipynb
├── scripts/
│   ├── etl_pipeline.py
│   ├── live_nav_fetch.py
│   ├── compute_metrics.py
│   └── recommender.py
├── sql/
│   ├── schema.sql
│   └── queries.sql
├── dashboard/
│   └── bluestock_mf.pbix
├── reports/
│   ├── Final_Report.pdf
│   └── Presentation.pptx
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/bluestock-mf-capstone.git
cd bluestock-mf-capstone
```

### 2. Install dependencies

```bash
pip install pandas numpy sqlalchemy scipy matplotlib plotly streamlit requests schedule
```

### 3. Verify raw data

Ensure all 10 CSVs are present in `data/raw/`:

```
01_fund_master.csv
02_nav_history.csv
03_aum_by_fund_house.csv
04_monthly_sip_inflows.csv
05_category_inflows.csv
06_industry_folio_count.csv
07_scheme_performance.csv
08_investor_transactions.csv
09_portfolio_holdings.csv
10_benchmark_indices.csv
```

---

## How to Run

### Option A — Full pipeline (recommended)

Runs all steps in sequence: DB creation → ETL → Metrics → SQL queries.

```bash
python run_pipeline.py
```

### Option B — Run steps individually

```bash
# Step 1: Create database tables
python create_db.py

# Step 2: Run ETL pipeline
python etl_pipeline.py

# Step 3: Compute performance metrics
python compute_metrics.py

# Step 4: Run analytical SQL queries
python run_queries.py
```

---

## How to Open the Dashboard

After the pipeline completes:

```bash
streamlit run b2_streamlit_app.py
```

Opens at `http://localhost:8501` with four pages:
- **Overview** — Risk-return scatter, KPI cards, fund summary table
- **NAV Trends** — Line charts, indexed performance, rolling return heatmap
- **SIP Calculator** — Historical simulation + projected growth
- **Fund Recommender** — Personalised fund suggestions by risk profile

---

## Bonus Modules

| Script | Purpose | Command |
|---|---|---|
| `b1_cron_etl.py` | Scheduled daily NAV fetch from mfapi.in | `python b1_cron_etl.py` |
| `b3_monte_carlo.py` | 5-year NAV projection (Geometric Brownian Motion) | `python b3_monte_carlo.py` |
| `b4_efficient_frontier.py` | Markowitz portfolio optimisation | `python b4_efficient_frontier.py` |
| `b5_email_report.py` | Weekly HTML performance email | `python b5_email_report.py --preview` |

---

## Dataset Description

| File | Rows | Description |
|---|---|---|
| 01_fund_master.csv | 40 | Scheme metadata: fund house, category, expense ratio, benchmark |
| 02_nav_history.csv | 46,000 | Daily NAV for 40 schemes (3+ years) |
| 03_aum_by_fund_house.csv | 90 | Monthly AUM by fund house |
| 04_monthly_sip_inflows.csv | 48 | Industry-level monthly SIP flows |
| 05_category_inflows.csv | 144 | Net inflows by SEBI category |
| 06_industry_folio_count.csv | 21 | Monthly industry folio count |
| 07_scheme_performance.csv | 40 | Risk/return metrics per scheme |
| 08_investor_transactions.csv | 32,778 | Simulated investor buy/sell/SIP transactions |
| 09_portfolio_holdings.csv | 322 | Top stock holdings per fund |
| 10_benchmark_indices.csv | 8,050 | Daily closing prices for benchmark indices |

---

## Database Schema (Star Schema)

**Dimension tables:** `dim_fund`, `dim_date`

**Fact tables:** `fact_nav`, `fact_transactions`, `fact_performance`, `fact_portfolio`, `fact_aum`, `fact_sip_industry`, `fact_category_inflows`, `fact_folio_count`

---

## Key Outputs

| File | Description |
|---|---|
| `data/processed/fund_scorecard.csv` | Composite 0–100 score ranking all funds |
| `data/processed/alpha_beta.csv` | Alpha and Beta vs NIFTY100 per fund |
| `outputs/b3_monte_carlo_<code>.png` | 5-year NAV projection charts |
| `outputs/b4_efficient_frontier.png` | Markowitz frontier visualisation |
| `outputs/b5_email_preview.html` | Preview of weekly email report |

---


## Author
 
**Sri Satya Thanuj Vummidi** — End-to-end development: ETL Pipeline, EDA, Performance Analytics, Dashboard, Bonus Modules
**Client:** Bluestock Fintech | **Data Source:** AMFI / mfapi.in

---

## Disclaimer

This project is for educational purposes only. Past performance of mutual funds is not indicative of future results. Nothing in this project constitutes financial advice.
