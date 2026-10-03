import sys
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

# Make the project code (mounted from ./src) importable inside the container
sys.path.append("/opt/airflow/project/src")


@dag(
    dag_id="fx_rates_pipeline",
    schedule="0 17 * * 1-5",  # 17:00, Monday to Friday
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Belgrade"),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["fx", "etl"],
)
def fx_rates_pipeline():

    @task
    def load_currencies_task():
        from load_currencies import run_currencies_load
        run_currencies_load()

    @task
    def load_rates_task():
        from load_rates import run_incremental_load
        run_incremental_load()

    @task
    def quality_checks_task():
        from data_quality_checks import run_checks
        failed = run_checks()
        if failed:
            raise ValueError(f"Data quality checks failed: {', '.join(failed)}")

    load_currencies_task() >> load_rates_task() >> quality_checks_task()


fx_rates_pipeline()