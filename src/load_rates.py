from datetime import date, timedelta
from decimal import Decimal

import requests
from psycopg2.extras import execute_values

from db import get_connection

BASE_URL = "https://api.frankfurter.dev/v1"
HISTORY_START_DATE = date(1999, 1, 4)  # first day of ECB euro reference rates


def extract_rates(start_date, end_date):
    """
    Fetch exchange rates for the period from start_date to end_date (format "YYYY-MM-DD").
    Return the full JSON response as a dictionary.
    """
    response = requests.get(f"{BASE_URL}/{start_date}..{end_date}", timeout=30)
    response.raise_for_status()  # fail loudly if the API returns an error
    return response.json(parse_float=Decimal)  # Decimal avoids float rounding errors


def transform_rates(data):
    """
    Convert the JSON response into a list of tuples:
    (date_id, base_code, target_code, rate)
    Example: (20250102, "EUR", "USD", Decimal("1.0321"))
    """
    base_code = data["base"]
    rows = []
    for full_date, rates in data["rates"].items():
        date_id = int(full_date.replace("-", ""))
        for target_code, rate in rates.items():
            rows.append((date_id, base_code, target_code, rate))
    return rows


def get_currency_ids(conn):
    """
    Return a dictionary {currency_code: currency_id} from the dim_currency table.
    Example: {"AUD": 1, "BGN": 2, ...}
    """
    with conn.cursor() as cur:
        cur.execute("SELECT currency_code, currency_id FROM dim_currency;")
        return dict(cur.fetchall())


def get_last_loaded_date(conn):
    """
    Return the latest date in fact_exchange_rate (the watermark),
    or None if the table is empty.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(d.full_date)
            FROM fact_exchange_rate f
            JOIN dim_date d ON f.date_id = d.date_id;
            """
        )
        return cur.fetchone()[0]


def load_rates(rows):
    """
    Load rows into fact_exchange_rate, replacing currency codes with their IDs.
    Rows with unknown currencies are skipped and reported.
    Safe to run multiple times (upsert on the unique key).
    Return the number of loaded rows.
    """
    conn = get_connection()
    try:
        with conn:
            currency_ids = get_currency_ids(conn)

            fact_rows = []
            skipped_rows = 0
            unknown_currencies = set()

            for date_id, base_code, target_code, rate in rows:
                if base_code in currency_ids and target_code in currency_ids:
                    base_id = currency_ids[base_code]
                    target_id = currency_ids[target_code]
                    fact_rows.append((date_id, base_id, target_id, rate))
                else:
                    skipped_rows += 1
                    for code in (base_code, target_code):
                        if code not in currency_ids:
                            unknown_currencies.add(code)

            if skipped_rows > 0:
                print(
                    f"  WARNING: Skipped {skipped_rows} rows with unknown currencies: "
                    f"{sorted(unknown_currencies)}"
                )

            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO fact_exchange_rate
                        (date_id, base_currency_id, target_currency_id, rate)
                    VALUES %s
                    ON CONFLICT (date_id, base_currency_id, target_currency_id)
                    DO UPDATE SET rate = EXCLUDED.rate, loaded_at = NOW();
                    """,
                    fact_rows,
                    page_size=1000,
                )
            return len(fact_rows)
    finally:
        conn.close()


def run_incremental_load():
    """
    Load only the data that is missing from the database.
    First run (empty table): load full history from 1999.
    Later runs: load from the day after the last loaded date until today.
    """
    conn = get_connection()
    try:
        last_date = get_last_loaded_date(conn)
    finally:
        conn.close()

    if last_date is None:
        start = HISTORY_START_DATE
    else:
        start = last_date + timedelta(days=1)
    end = date.today()

    if start > end:
        print("Data is already up to date.")
        return

    print(f"Loading rates from {start} to {end}...")
    total = 0
    for year in range(start.year, end.year + 1):
        chunk_start = max(start, date(year, 1, 1))
        chunk_end = min(end, date(year, 12, 31))

        data = extract_rates(chunk_start.isoformat(), chunk_end.isoformat())
        rows = transform_rates(data)

        start_id = int(chunk_start.isoformat().replace("-", ""))
        rows = [row for row in rows if row[0] >= start_id] # row[0] is date_id

        loaded = load_rates(rows)

        total += loaded
        print(f"{year}: loaded {loaded} rows")

    print(f"Done. Total rows loaded: {total}")


if __name__ == "__main__":
    run_incremental_load()