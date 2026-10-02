import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # loads data from .env file

API_URL = "https://api.frankfurter.dev/v1/currencies"


def extract_currencies():
    """EXTRACT: fetches the list of currencies from the API.""" 
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()  # ERROR if API doesn't response
    return response.json()       # eg. {"AUD": "Australian Dollar", ...}


def transform_currencies(data):
    """TRANSFORM: converts a dictionary into a list of lines (code, name)."""
    return [(code.strip().upper(), name.strip()) for code, name in data.items()]


def load_currencies(rows):
    """LOAD: writes currencies u dim_currency."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        with conn:  # Automatic COMMIT if everything is fine, ROLLBACK if an error occurs.

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO dim_currency (currency_code, currency_name)
                    VALUES (%s, %s)
                    ON CONFLICT (currency_code)
                    DO UPDATE SET currency_name = EXCLUDED.currency_name;
                    """,
                    rows,
                )
    finally:
        conn.close()

def run_currencies_load():
    """Run the full ETL for currencies: extract, transform, load."""
    data = extract_currencies()
    rows = transform_currencies(data)
    load_currencies(rows)
    print(f"Loaded {len(rows)} currencies into dim_currency.")


if __name__ == "__main__":
    run_currencies_load()