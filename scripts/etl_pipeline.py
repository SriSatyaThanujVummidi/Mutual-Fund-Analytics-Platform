"""
etl_pipeline.py
Bluestock Fintech — Mutual Fund Analytics Capstone
================================================
Master ETL script: Extract → Transform → Load
Reads all 10 raw CSVs, cleans them, and loads into SQLite (bluestock_mf.db).

Usage:
    python etl_pipeline.py

Outputs:
    data/processed/   — 10 cleaned CSV files
    data/db/bluestock_mf.db — SQLite database with star schema
"""

import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
RAW_DIR       = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")
DB_DIR        = os.path.join("data", "db")
DB_PATH       = os.path.join(DB_DIR, "bluestock_mf.db")

def setup_folders():
    """Create output directories if they don't exist."""
    for folder in [PROCESSED_DIR, DB_DIR]:
        os.makedirs(folder, exist_ok=True)
    print("✅ Folders ready")


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACT — Load all raw CSVs
# ─────────────────────────────────────────────────────────────────────────────
def extract():
    """Load all 10 raw CSVs into a dictionary of DataFrames."""
    print("\n── EXTRACT ──────────────────────────────────")
    files = {
        "fund_master"       : "01_fund_master.csv",
        "nav_history"       : "02_nav_history.csv",
        "aum"               : "03_aum_by_fund_house.csv",
        "sip_inflows"       : "04_monthly_sip_inflows.csv",
        "category_inflows"  : "05_category_inflows.csv",
        "folio_count"       : "06_industry_folio_count.csv",
        "scheme_performance": "07_scheme_performance.csv",
        "transactions"      : "08_investor_transactions.csv",
        "portfolio_holdings": "09_portfolio_holdings.csv",
        "benchmark_indices" : "10_benchmark_indices.csv",
    }

    raw = {}
    for key, fname in files.items():
        path = os.path.join(RAW_DIR, fname)
        raw[key] = pd.read_csv(path)
        print(f"  Loaded {fname:<40} shape={raw[key].shape}")

    return raw


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORM — Clean each dataset
# ─────────────────────────────────────────────────────────────────────────────
def transform_nav(df):
    """
    Clean NAV history:
      - Parse dates, sort, forward-fill gaps, remove dupes/negatives
      - Compute daily_return_pct
    """
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["amfi_code", "date"])
    df["nav"] = df.groupby("amfi_code")["nav"].ffill()
    df = df.drop_duplicates(subset=["amfi_code", "date"])
    df = df[df["nav"] > 0]
    df["daily_return_pct"] = df.groupby("amfi_code")["nav"].pct_change() * 100
    return df


def transform_transactions(df):
    """
    Clean investor transactions:
      - Title-case transaction_type, positive amounts only, parse dates
    """
    df["transaction_type"] = df["transaction_type"].str.strip().str.title()
    df = df[df["amount_inr"] > 0]
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df = df.dropna(subset=["investor_id", "amfi_code", "transaction_date"])
    return df


def transform_scheme_performance(df):
    """
    Clean scheme performance:
      - Coerce numerics, flag negative Sharpe, validate expense ratio range
    """
    return_cols = [
        "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
        "sharpe_ratio", "sortino_ratio", "alpha", "beta",
        "max_drawdown_pct", "std_dev_ann_pct",
    ]
    for col in return_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["low_sharpe_flag"] = df["sharpe_ratio"] < 0

    bad = df[
        (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)
    ]
    if len(bad):
        print(f"  ⚠️  {len(bad)} rows with suspicious expense_ratio")

    return df


def transform_generic(df):
    """Strip whitespace from string columns, drop fully-empty rows."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    df = df.dropna(how="all")
    return df


def transform(raw):
    """Apply all cleaning functions and return a dict of clean DataFrames."""
    print("\n── TRANSFORM ────────────────────────────────")
    clean = {}

    clean["nav"]                = transform_nav(raw["nav_history"])
    print(f"  clean_nav               shape={clean['nav'].shape}")

    clean["transactions"]       = transform_transactions(raw["transactions"])
    print(f"  clean_transactions      shape={clean['transactions'].shape}")

    clean["scheme_performance"] = transform_scheme_performance(raw["scheme_performance"])
    print(f"  clean_scheme_performance shape={clean['scheme_performance'].shape}")

    for key in ["fund_master", "aum", "sip_inflows", "category_inflows",
                "folio_count", "portfolio_holdings", "benchmark_indices"]:
        clean[key] = transform_generic(raw[key].copy())
        print(f"  clean_{key:<22} shape={clean[key].shape}")

    return clean


# ─────────────────────────────────────────────────────────────────────────────
# SAVE PROCESSED CSVs
# ─────────────────────────────────────────────────────────────────────────────
CSV_MAP = {
    "nav"               : "clean_nav.csv",
    "transactions"      : "clean_transactions.csv",
    "scheme_performance": "clean_schema_performance.csv",
    "fund_master"       : "clean_fund_master.csv",
    "aum"               : "clean_aum.csv",
    "sip_inflows"       : "clean_sip_inflows.csv",
    "category_inflows"  : "clean_category_inflows.csv",
    "folio_count"       : "clean_folio_count.csv",
    "portfolio_holdings": "clean_portfolio_holdings.csv",
    "benchmark_indices" : "clean_benchmark_indices.csv",
}

def save_processed(clean):
    """Write all cleaned DataFrames to data/processed/."""
    print("\n── SAVE PROCESSED CSVs ──────────────────────")
    for key, fname in CSV_MAP.items():
        out = os.path.join(PROCESSED_DIR, fname)
        clean[key].to_csv(out, index=False)
        print(f"  ✓ {fname}")


# ─────────────────────────────────────────────────────────────────────────────
# LOAD — Write to SQLite star schema
# ─────────────────────────────────────────────────────────────────────────────
def build_dim_date(nav_df, bench_df):
    """Build a dim_date dimension from all dates in NAV + benchmark data."""
    all_dates = pd.concat([
        nav_df["date"],
        pd.to_datetime(bench_df["date"]),
    ]).drop_duplicates().dropna().sort_values()

    dim = pd.DataFrame({"date": all_dates})
    dim["date_id"]    = dim["date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"]       = dim["date"].dt.year
    dim["month"]      = dim["date"].dt.month
    dim["quarter"]    = dim["date"].dt.quarter
    dim["month_name"] = dim["date"].dt.strftime("%b")
    dim["is_weekday"] = dim["date"].dt.weekday < 5
    return dim


def load(clean):
    """
    Load cleaned data into SQLite using a star schema:
      dim_fund, dim_date, fact_nav, fact_transactions,
      fact_performance, fact_portfolio, fact_aum, fact_sip_industry
    """
    print("\n── LOAD → SQLite ────────────────────────────")
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # ── dim_fund ──────────────────────────────────────────────────────────
    dim_fund = clean["fund_master"][[
        "amfi_code", "fund_house", "scheme_name", "category",
        "sub_category", "plan", "benchmark", "expense_ratio_pct",
        "exit_load_pct", "fund_manager", "risk_category", "sebi_category_code",
    ]].copy()
    dim_fund.to_sql("dim_fund", engine, if_exists="replace", index=False)
    print(f"  ✓ dim_fund           rows={len(dim_fund)}")

    # ── dim_date ──────────────────────────────────────────────────────────
    dim_date = build_dim_date(clean["nav"], clean["benchmark_indices"])
    dim_date.to_sql("dim_date", engine, if_exists="replace", index=False)
    print(f"  ✓ dim_date           rows={len(dim_date)}")

    # ── fact_nav ──────────────────────────────────────────────────────────
    fact_nav = clean["nav"][["amfi_code", "date", "nav", "daily_return_pct"]].copy()
    fact_nav.to_sql("fact_nav", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_nav           rows={len(fact_nav)}")

    # ── fact_transactions ─────────────────────────────────────────────────
    fact_tx = clean["transactions"].copy()
    fact_tx.to_sql("fact_transactions", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_transactions  rows={len(fact_tx)}")

    # ── fact_performance ──────────────────────────────────────────────────
    fact_perf = clean["scheme_performance"].copy()
    fact_perf.to_sql("fact_performance", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_performance   rows={len(fact_perf)}")

    # ── fact_portfolio ────────────────────────────────────────────────────
    fact_port = clean["portfolio_holdings"].copy()
    fact_port.to_sql("fact_portfolio", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_portfolio     rows={len(fact_port)}")

    # ── fact_aum ──────────────────────────────────────────────────────────
    fact_aum = clean["aum"].copy()
    fact_aum.to_sql("fact_aum", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_aum           rows={len(fact_aum)}")

    # ── fact_sip_industry ─────────────────────────────────────────────────
    fact_sip = clean["sip_inflows"].copy()
    fact_sip.to_sql("fact_sip_industry", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_sip_industry  rows={len(fact_sip)}")

    # ── fact_category_inflows ─────────────────────────────────────────────
    fact_cat = clean["category_inflows"].copy()
    fact_cat.to_sql("fact_category_inflows", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_category_inflows rows={len(fact_cat)}")

    # ── fact_folio_count ──────────────────────────────────────────────────
    fact_folio = clean["folio_count"].copy()
    fact_folio.to_sql("fact_folio_count", engine, if_exists="replace", index=False)
    print(f"  ✓ fact_folio_count   rows={len(fact_folio)}")

    # ── Quick verification ────────────────────────────────────────────────
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    print(f"\n  DB tables: {[t[0] for t in tables]}")
    print(f"  DB saved → {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline():
    print("=" * 52)
    print("  Bluestock MF Capstone — ETL Pipeline")
    print("=" * 52)
    setup_folders()
    raw   = extract()
    clean = transform(raw)
    save_processed(clean)
    load(clean)
    print("\n✅ ETL Pipeline complete!")
    print(f"   Processed CSVs → {PROCESSED_DIR}/")
    print(f"   SQLite DB      → {DB_PATH}")


if __name__ == "__main__":
    run_pipeline()
