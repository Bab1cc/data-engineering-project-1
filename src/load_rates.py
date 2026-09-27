from decimal import Decimal

import requests

from db import get_connection

BASE_URL = "https://api.frankfurter.dev/v1"


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
                    f"WARNING: Skipped {skipped_rows} rows with unknown currencies: "
                    f"{sorted(unknown_currencies)}"
                )

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO fact_exchange_rate
                        (date_id, base_currency_id, target_currency_id, rate)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (date_id, base_currency_id, target_currency_id)
                    DO UPDATE SET rate = EXCLUDED.rate, loaded_at = NOW();
                    """,
                    fact_rows,
                )
            return len(fact_rows)
    finally:
        conn.close()


if __name__ == "__main__":
    data = extract_rates("2025-01-01", "2025-12-31")
    rows = transform_rates(data)
    loaded = load_rates(rows)
    print(f"Loaded {loaded} rows into fact_exchange_rate.")