import sys
from datetime import datetime

from load_currencies import run_currencies_load
from load_rates import run_incremental_load
from data_quality_checks import run_checks


def main():
    print(f"Pipeline started at {datetime.now():%Y-%m-%d %H:%M:%S}")

    print("=== Step 1/3: Load currencies ===")
    run_currencies_load()

    print("=== Step 2/3: Load exchange rates ===")
    run_incremental_load()

    print("=== Step 3/3: Data quality checks ===")
    failed = run_checks()
    if failed:
        print(f"Pipeline failed: {len(failed)} check(s) failed: {', '.join(failed)}")
        sys.exit(1)

    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()