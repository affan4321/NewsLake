"""Thin client for Airflow 3.x's REST API -- used by the Pipeline tab to show live
DAG run status and let the user trigger a run manually.

Auth: Airflow's FAB auth manager issues short-lived JWTs from /auth/token given a
username/password (the same admin account created by airflow-init). We fetch a fresh
token on module import and re-fetch on a 401, rather than trying to track expiry.
"""
import os

import requests

AIRFLOW_API_BASE_URL = os.environ.get("AIRFLOW_API_BASE_URL", "http://airflow-apiserver:8080")
AIRFLOW_USERNAME = os.environ.get("_AIRFLOW_WWW_USER_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.environ.get("_AIRFLOW_WWW_USER_PASSWORD", "airflow")
DAG_ID = "newslake_pipeline"

# Order matters here: it's how the pipeline tab lays out the flow diagram left-to-right.
# The API's taskInstances response order doesn't match DAG topological order.
TASK_ORDER = [
    "fetch_news",
    "validate_raw_data",
    "bronze_to_silver",
    "silver_quality_checks",
    "silver_to_gold",
    "load_to_postgres",
    "dbt_transform",
    "dbt_tests",
]

_token = None


def _get_token(force_refresh=False):
    global _token
    if _token is None or force_refresh:
        resp = requests.post(
            f"{AIRFLOW_API_BASE_URL}/auth/token",
            json={"username": AIRFLOW_USERNAME, "password": AIRFLOW_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        _token = resp.json()["access_token"]
    return _token


def _request(method, path, **kwargs):
    for attempt in range(2):
        resp = requests.request(
            method, f"{AIRFLOW_API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {_get_token(force_refresh=attempt > 0)}"},
            timeout=10, **kwargs,
        )
        if resp.status_code == 401 and attempt == 0:
            continue
        return resp
    return resp


def get_latest_run():
    """Most recent DAG run (any state), or None if the DAG has never run."""
    resp = _request(
        "GET", f"/api/v2/dags/{DAG_ID}/dagRuns",
        params={"limit": 1, "order_by": "-start_date"},
    )
    resp.raise_for_status()
    runs = resp.json()["dag_runs"]
    return runs[0] if runs else None


def get_task_states(dag_run_id: str) -> dict:
    """{task_id: state} for every task in the given run, in TASK_ORDER."""
    resp = _request("GET", f"/api/v2/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances")
    resp.raise_for_status()
    by_id = {t["task_id"]: t["state"] for t in resp.json()["task_instances"]}
    return {task_id: by_id.get(task_id) for task_id in TASK_ORDER}


def trigger_run():
    """Starts a new DAG run. Raises requests.HTTPError (e.g. 409 if one's already active)."""
    resp = _request(
        "POST", f"/api/v2/dags/{DAG_ID}/dagRuns",
        json={"logical_date": None},
    )
    resp.raise_for_status()
    return resp.json()
