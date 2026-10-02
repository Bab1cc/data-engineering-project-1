import sys

from db import get_connection

# Each check is a SQL query that returns ONE number: the count of "bad" rows.
# 0 means the check passed; anything else means it failed.
CHECKS = {
    "no_non_positive_rates": """
        SELECT COUNT(*)
        FROM fact_exchange_rate
        WHERE rate <= 0;
    """,
    "no_duplicate_rates": """
        SELECT COUNT(*)
        FROM (
            SELECT date_id, base_currency_id, target_currency_id
            FROM fact_exchange_rate
            GROUP BY date_id, base_currency_id, target_currency_id
            HAVING COUNT(*) > 1
        ) dup;
    """,
    "data_is_fresh": """
        SELECT CASE
            WHEN MAX(d.full_date) IS NULL
            OR MAX(d.full_date) < CURRENT_DATE - INTERVAL '5 days' THEN 1
            ELSE 0
        END
        FROM fact_exchange_rate f
        JOIN dim_date d ON f.date_id = d.date_id;
    """,
    "no_large_date_gaps": """
    WITH loaded_dates AS (
        SELECT DISTINCT d.full_date
        FROM fact_exchange_rate f
        JOIN dim_date d ON f.date_id = d.date_id
    ),
    gaps AS (
        SELECT full_date - LAG(full_date) OVER (ORDER BY full_date) AS gap
        FROM loaded_dates
    )
    SELECT COUNT(*)
    FROM gaps
    WHERE gap > 5;
""",
}


def run_checks():
    """Run all checks and return a list of names of the checks that failed."""
    conn = get_connection()
    failed = []
    try:
        with conn.cursor() as cur:
            for name, sql in CHECKS.items():
                cur.execute(sql)
                bad_rows = cur.fetchone()[0]
                if bad_rows == 0:
                    print(f"PASS  {name}")
                else:
                    print(f"FAIL  {name}: {bad_rows} problem(s) found")
                    failed.append(name)
    finally:
        conn.close()
    return failed


if __name__ == "__main__":
    failed = run_checks()
    if failed:
        print(f"{len(failed)} check(s) failed.")
        sys.exit(1)  # exit code 1 = failure
    print("All checks passed.")