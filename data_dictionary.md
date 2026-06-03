# Data Dictionary — Bluestock MF Capstone

## dim_fund (40 rows)
| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT | Unique AMFI scheme code — Primary Key |
| fund_house | TEXT | AMC name e.g. SBI Mutual Fund |
| scheme_name | TEXT | Full official fund name |
| category | TEXT | Equity / Debt / Hybrid |
| sub_category | TEXT | Large Cap / Mid Cap / Liquid etc. |
| plan | TEXT | Regular or Direct |
| benchmark | TEXT | Index fund is measured against |
| expense_ratio_pct | REAL | Annual expense ratio % |
| exit_load_pct | REAL | Penalty % for early redemption |
| fund_manager | TEXT | Primary fund manager name |
| risk_category | TEXT | SEBI grade: Low / Moderate / High / Very High |

## fact_nav (46,000 rows)
| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT | FK to dim_fund |
| date | DATE | Business day of NAV |
| nav | REAL | NAV value in Rs. |
| daily_return_pct | REAL | Day-on-day % change |

## fact_transactions (32,778 rows)
| Column | Type | Description |
|---|---|---|
| investor_id | TEXT | Unique investor ID |
| amfi_code | TEXT | FK to dim_fund |
| transaction_date | DATE | Date of transaction |
| transaction_type | TEXT | SIP / Lumpsum / Redemption |
| amount_inr | INTEGER | Amount in Rs. |
| state | TEXT | Investor state |
| city | TEXT | Investor city |
| city_tier | TEXT | T30 = Top 30 cities, B30 = Beyond Top 30 |
| age_group | TEXT | 18-25 / 26-35 / 36-45 / 46-55 / 56+ |
| gender | TEXT | Male / Female |
| kyc_status | TEXT | Verified / Pending |

## fact_performance (40 rows)
| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT | FK to dim_fund |
| return_1yr_pct | REAL | 1-year return % |
| return_3yr_pct | REAL | 3-year CAGR % |
| return_5yr_pct | REAL | 5-year CAGR % |
| sharpe_ratio | REAL | Risk-adjusted return — above 1 is good |
| sortino_ratio | REAL | Sharpe but only penalises downside risk |
| alpha | REAL | Extra return vs benchmark — positive = outperforming |
| beta | REAL | Market sensitivity — 1.0 = moves with market |
| max_drawdown_pct | REAL | Worst peak-to-trough drop % |
| std_dev_ann_pct | REAL | Annualised volatility % |

## fact_aum (90 rows)
| Column | Type | Description |
|---|---|---|
| fund_house | TEXT | AMC name |
| date | DATE | Quarter end date |
| aum_crore | REAL | AUM in Rs. crore |
| num_schemes | INTEGER | Number of schemes run by that AMC |

## fact_sip_industry (48 rows)
| Column | Type | Description |
|---|---|---|
| month | TEXT | YYYY-MM format |
| sip_inflow_crore | REAL | Total SIP collected that month in crore |
| active_sip_accounts_crore | REAL | Active SIP accounts in crore |
| new_sip_accounts_lakh | REAL | New SIPs registered in lakh |
| sip_aum_lakh_crore | REAL | Total SIP portfolio value in lakh crore |