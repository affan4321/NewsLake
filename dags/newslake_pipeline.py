"""NewsLake main pipeline: freenewsapi.io -> MinIO bronze -> Spark silver -> Spark gold.

Each task shells out to `docker compose run` against the HOST Docker daemon (this
worker only has a socket, not the images/jobs baked in) -- see HOST_PROJECT_DIR in
.env and the "Docker-outside-of-Docker" note in the README for why paths must be
the real host paths, not container-internal ones.

Schedule is controlled by PIPELINE_SCHEDULE_CRON in .env, not hardcoded here, per the
project's daily-batch (not hourly) cadence.
"""
import os
from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

COMPOSE = 'docker compose -f "$HOST_PROJECT_DIR/docker-compose.yml"'
RUN_JOB = 'bash "$HOST_PROJECT_DIR/spark/run_job.sh"'

default_args = {
    "owner": "newslake",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="newslake_pipeline",
    description="Ingest news, land in MinIO bronze, transform through Spark to silver/gold",
    default_args=default_args,
    schedule=os.environ.get("PIPELINE_SCHEDULE_CRON", "0 6 * * *"),
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["newslake"],
) as dag:

    fetch_news = BashOperator(
        task_id="fetch_news",
        bash_command=f"{COMPOSE} run --rm ingestion python fetch_news.py",
    )

    validate_raw_data = BashOperator(
        task_id="validate_raw_data",
        bash_command=f"{COMPOSE} run --rm ingestion python validate_bronze.py",
    )

    bronze_to_silver = BashOperator(
        task_id="bronze_to_silver",
        bash_command=f"{RUN_JOB} bronze_to_silver.py",
    )

    silver_quality_checks = BashOperator(
        task_id="silver_quality_checks",
        bash_command=f"{RUN_JOB} silver_quality_checks.py",
    )

    silver_to_gold = BashOperator(
        task_id="silver_to_gold",
        bash_command=f"{RUN_JOB} silver_to_gold.py",
    )

    fetch_news >> validate_raw_data >> bronze_to_silver >> silver_quality_checks >> silver_to_gold
