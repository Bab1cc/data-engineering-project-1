-- Dimension - currencies
CREATE TABLE dim_currency (
    currency_id    SERIAL PRIMARY KEY,
    currency_code  CHAR(3) NOT NULL UNIQUE,
    currency_name  VARCHAR(100)
);

-- Dimension - dates
CREATE TABLE dim_date (
    date_id      INT PRIMARY KEY,          -- eg. 20260924
    full_date    DATE NOT NULL UNIQUE,
    year         INT NOT NULL,
    quarter      INT NOT NULL,
    month        INT NOT NULL,
    month_name   VARCHAR(20) NOT NULL,
    day          INT NOT NULL,
    day_of_week  INT NOT NULL,             -- 1 = monday, 7 = sunday
    is_weekend   BOOLEAN NOT NULL
);

-- Fact table - exchanges
CREATE TABLE fact_exchange_rate (
    rate_id             BIGSERIAL PRIMARY KEY,
    date_id             INT NOT NULL REFERENCES dim_date(date_id),
    base_currency_id    INT NOT NULL REFERENCES dim_currency(currency_id),
    target_currency_id  INT NOT NULL REFERENCES dim_currency(currency_id),
    rate                NUMERIC(18,6) NOT NULL,
    loaded_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (date_id, base_currency_id, target_currency_id)
);

INSERT INTO dim_date
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INT,
    d::DATE,
    EXTRACT(YEAR FROM d),
    EXTRACT(QUARTER FROM d),
    EXTRACT(MONTH FROM d),
    TRIM(TO_CHAR(d, 'Month')),
    EXTRACT(DAY FROM d),
    EXTRACT(ISODOW FROM d),
    EXTRACT(ISODOW FROM d) IN (6, 7)
FROM generate_series('1999-01-01'::DATE, '2030-12-31'::DATE, '1 day') AS d;

SELECT * FROM dim_date WHERE year = 2026 AND month = 9 LIMIT 10;