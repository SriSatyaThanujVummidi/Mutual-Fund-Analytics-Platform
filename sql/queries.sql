-- Q1: Top 5 funds by 3-year return
SELECT amfi_code, return_3yr_pct
FROM fact_performance
ORDER BY return_3yr_pct DESC
LIMIT 5;

-- Q2: Average NAV per month for HDFC Top 100 (amfi_code = 125497)
SELECT strftime('%Y-%m', date) AS month, ROUND(AVG(nav), 2) AS avg_nav
FROM fact_nav
WHERE amfi_code = '125497'
GROUP BY month
ORDER BY month
LIMIT 5;

-- Q3: SIP inflow year-on-year
SELECT substr(month, 1, 4) AS year, ROUND(SUM(sip_inflow_crore), 2) AS total_sip
FROM fact_sip_industry
GROUP BY year
ORDER BY year;

-- Q4: Transaction amount by state
SELECT state, ROUND(SUM(amount_inr) / 1e7, 2) AS total_crore
FROM fact_transactions
GROUP BY state
ORDER BY total_crore DESC;

-- Q5: Funds with expense ratio less than 1%
SELECT scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct;

-- Q6: Count of transactions by type
SELECT transaction_type, COUNT(*) AS count,
       ROUND(SUM(amount_inr)/1e7, 2) AS total_crore
FROM fact_transactions
GROUP BY transaction_type;

-- Q7: Funds with Sharpe ratio greater than 1
SELECT f.scheme_name, p.sharpe_ratio
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
WHERE p.sharpe_ratio > 1
ORDER BY p.sharpe_ratio DESC;

-- Q8: Total AUM by fund house
SELECT fund_house, ROUND(SUM(aum_crore), 2) AS total_aum
FROM fact_aum
GROUP BY fund_house
ORDER BY total_aum DESC;

-- Q9: Age group vs average SIP amount
SELECT age_group, COUNT(DISTINCT investor_id) AS investors,
       ROUND(AVG(amount_inr), 0) AS avg_amount
FROM fact_transactions
WHERE transaction_type = 'Sip'
GROUP BY age_group
ORDER BY age_group;

-- Q10: T30 vs B30 city tier comparison
SELECT city_tier, COUNT(*) AS tx_count,
       ROUND(SUM(amount_inr)/1e7, 2) AS total_crore
FROM fact_transactions
GROUP BY city_tier;