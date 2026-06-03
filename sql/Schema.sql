-- DIMENSION TABLES
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code       TEXT PRIMARY KEY,
    fund_house      TEXT,
    scheme_name     TEXT,
    category        TEXT,
    sub_category    TEXT,
    plan            TEXT,
    benchmark       TEXT,
    expense_ratio_pct REAL,
    exit_load_pct   REAL,
    fund_manager    TEXT,
    risk_category   TEXT
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     INTEGER PRIMARY KEY,
    date        DATE,
    year        INTEGER,
    month       INTEGER,
    quarter     INTEGER,
    is_weekday  INTEGER   -- 1 = weekday, 0 = weekend
);

-- FACT TABLES
CREATE TABLE IF NOT EXISTS fact_nav (
    amfi_code           TEXT,
    nav_date            DATE,
    nav                 REAL,
    daily_return_pct    REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    tx_id               TEXT PRIMARY KEY,
    investor_id         TEXT,
    amfi_code           TEXT,
    transaction_date    DATE,
    transaction_type    TEXT,
    amount_inr          INTEGER,
    state               TEXT,
    city                TEXT,
    city_tier           TEXT,
    age_group           TEXT,
    gender              TEXT,
    kyc_status          TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code           TEXT,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    alpha               REAL,
    beta                REAL,
    max_drawdown_pct    REAL,
    std_dev_ann_pct     REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_aum (
    fund_house      TEXT,
    date            DATE,
    aum_crore       REAL,
    num_schemes     INTEGER
);

CREATE TABLE IF NOT EXISTS fact_sip_industry (
    month                   TEXT,
    sip_inflow_crore        REAL,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh   REAL,
    sip_aum_lakh_crore      REAL
);