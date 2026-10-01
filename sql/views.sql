CREATE OR REPLACE VIEW vw_exchange_rates as
SELECT
    d.full_date AS full_date,
	d.year AS year,
	d.month AS month,
	base_curr.currency_code AS base_currency,
	target_curr.currency_code AS target_currency,
	target_curr.currency_name AS target_currency_name,
	f.rate AS rate
FROM fact_exchange_rate f
JOIN dim_date d 
    ON f.date_id = d.date_id
JOIN dim_currency base_curr 
    ON f.base_currency_id = base_curr.currency_id
JOIN dim_currency target_curr 
    ON f.target_currency_id = target_curr.currency_id;

CREATE OR REPLACE VIEW vw_latest_rates AS
SELECT full_date, base_currency, target_currency, target_currency_name, rate
FROM vw_exchange_rates
WHERE full_date = (
    SELECT MAX(full_date)
    FROM vw_exchange_rates
);

CREATE OR REPLACE VIEW vw_monthly_rates AS
SELECT
    target_currency,
    year,
    month,
    ROUND(AVG(rate), 4) AS avg_rate,
    MIN(rate) AS min_rate,
    MAX(rate) AS max_rate
FROM vw_exchange_rates
GROUP BY year, month, target_currency;

CREATE OR REPLACE VIEW vw_daily_change AS
WITH rates_with_prev AS (
    SELECT
        full_date,
        target_currency,
        rate,
        LAG(rate) OVER (PARTITION BY target_currency ORDER BY full_date) AS prev_rate
    FROM vw_exchange_rates
)
SELECT
    full_date,
    target_currency,
    rate,
    prev_rate,
    ROUND((rate - prev_rate) / prev_rate * 100, 4) AS pct_change
FROM rates_with_prev;