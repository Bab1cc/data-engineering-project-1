from datetime import date

import pandas as pd
import streamlit as st

from db import get_connection

st.set_page_config(page_title="FX Rates Dashboard", page_icon="💱", layout="wide")

# Returns: target_currency (list of all currency codes, sorted)
CURRENCIES_SQL = """
    SELECT DISTINCT target_currency
    FROM vw_exchange_rates
    ORDER BY target_currency;
"""

# Params: currency, start_date, end_date
# Returns: full_date, rate  (sorted by date)
RATE_HISTORY_SQL = """
    SELECT full_date, rate::float AS rate
    FROM vw_exchange_rates
    WHERE target_currency = %s
      AND full_date BETWEEN %s AND %s
    ORDER BY full_date;
"""

# Params: currency
# Returns: full_date, rate, pct_change  (only the most recent day)
LATEST_SQL = """
    SELECT full_date, rate, pct_change
    FROM vw_daily_change
    WHERE target_currency = %s
    ORDER BY full_date DESC
    LIMIT 1;
"""

# Params: currency
# Returns: year, month, avg_rate, min_rate, max_rate  (last 12 months, newest first)
MONTHLY_SQL = """
    SELECT year, month, avg_rate, min_rate, max_rate
    FROM vw_monthly_rates
    WHERE target_currency = %s
    ORDER BY year DESC, month DESC
    LIMIT 12;
"""

# Params: currency
# Returns: full_date, rate, pct_change  (5 largest daily moves, up OR down)
TOP_MOVES_SQL = """
    SELECT full_date, rate, pct_change
    FROM vw_daily_change
    WHERE target_currency = %s
      AND pct_change IS NOT NULL
    ORDER BY ABS(pct_change) DESC
    LIMIT 5;
"""

# Returns: target_currency, target_currency_name, rate  (latest rates for all currencies)
LATEST_ALL_SQL = """
    SELECT target_currency, target_currency_name, rate
    FROM vw_latest_rates
    ORDER BY target_currency;
"""


# ---------- Helper ----------
@st.cache_data(ttl=3600)
def run_query(sql, params=None):
    """Run a SQL query and return the result as a pandas DataFrame (cached for 1 hour)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [col[0] for col in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=columns)
    finally:
        conn.close()


# ---------- Layout ----------
st.title("💱 FX Rates Dashboard")
st.caption("ECB reference rates · base currency: EUR")

# Sidebar filters
currencies = run_query(CURRENCIES_SQL)["target_currency"].tolist()
default_index = currencies.index("USD") if "USD" in currencies else 0
currency = st.sidebar.selectbox("Currency", currencies, index=default_index)
start_date = st.sidebar.date_input("From", date(2020, 1, 1))
end_date = st.sidebar.date_input("To", date.today())

# Key metrics
latest = run_query(LATEST_SQL, (currency,))
col1, col2 = st.columns(2)
col1.metric(
    f"EUR/{currency} (latest)",
    f"{latest['rate'][0]:.4f}",
    f"{latest['pct_change'][0]:.2f}%",
)
col2.metric("Last update", str(latest["full_date"][0]))

# Rate history chart
st.subheader(f"EUR/{currency} over time")
history = run_query(RATE_HISTORY_SQL, (currency, start_date, end_date))
st.line_chart(history, x="full_date", y="rate")

# Monthly stats and largest moves side by side
left, right = st.columns(2)
with left:
    st.subheader("Last 12 months")
    st.dataframe(run_query(MONTHLY_SQL, (currency,)), hide_index=True)
with right:
    st.subheader("Largest daily moves")
    st.dataframe(run_query(TOP_MOVES_SQL, (currency,)), hide_index=True)

# All currencies
st.subheader("Latest rates – all currencies")
st.dataframe(run_query(LATEST_ALL_SQL), hide_index=True)