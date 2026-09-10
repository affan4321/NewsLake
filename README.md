# NewsLake

A containerized, continuously updated news data lakehouse. Ingests raw news data into MinIO, processes it with Apache Spark into Parquet, orchestrates the pipeline with Airflow, applies analytical transformations and tests with dbt, and serves curated datasets through PostgreSQL and Streamlit.

## Architecture

```
freenewsapi.io -> Python ingestion -> MinIO (bronze, raw JSON)
                                    -> PySpark -> MinIO (silver, Parquet)
                                    -> PySpark -> MinIO (gold, Parquet)
                                    -> load -> PostgreSQL (staging)
                                    -> dbt -> PostgreSQL (marts)
                                    -> Streamlit (dashboard)

Airflow (CeleryExecutor) orchestrates every stage above. Schedule is PIPELINE_SCHEDULE_CRON
in .env (default once daily), not hardcoded in the DAG.
```

## Build stages

- [x] Stage 1 — Python ingestion -> MinIO bronze (fetches /v1/news listing + /v1/details per article)
- [x] Stage 2 — Bronze -> PySpark -> Silver Parquet (silver/articles, silver/sources, quarantine/silver_validation)
- [x] Stage 3 — Silver -> PySpark -> Gold Parquet (daily_article_metrics, daily_source_metrics, topic_trends, article_activity; entity_trends deferred, needs NER)
- [x] Stage 4 — Airflow orchestration (newslake_pipeline DAG: fetch_news -> validate_raw_data -> bronze_to_silver -> silver_quality_checks -> silver_to_gold)
- [x] Stage 5 — Gold -> dbt -> PostgreSQL (load_to_postgres lands article-grain Silver data in `raw`; dbt builds staging/intermediate/marts in `analytics`, dbt_transform + dbt_tests added to the DAG)
- [x] Stage 6 — PostgreSQL -> Streamlit (Overview KPIs, Topic Trends, Source Analysis, Recent News, plus a live animated Pipeline tab with a manual trigger button)

## Setup

```bash
cp .env.example .env   # fill in NEWS_API_KEY and HOST_PROJECT_DIR (absolute path to this repo)
docker compose up -d minio spark-master spark-worker

python3 -m venv .venv && source .venv/bin/activate
pip install -r ingestion/requirements.txt
python ingestion/fetch_news.py       # bronze, manual/dev run

./spark/run_job.sh bronze_to_silver.py   # silver
./spark/run_job.sh silver_to_gold.py     # gold

./spark/run_job.sh load_to_postgres.py   # silver articles/sources/topics -> raw schema
docker compose run --rm dbt run          # raw -> analytics staging/intermediate/marts
docker compose run --rm dbt test         # 22 data tests: unique, not_null, relationships, accepted_values
```

MinIO console: http://localhost:9001 (credentials from `.env`)
Spark master UI: http://localhost:8080 · worker UI: http://localhost:8081

**Postgres is hosted on Neon** (`POSTGRES_HOST`/credentials in `.env`), not the local `postgres`
service in docker-compose.yml (kept as an unused local-dev fallback — see below to switch back).
`raw` schema is Spark-loaded article-grain data, `analytics` schema is what dbt builds (query
`analytics.fct_articles`, `analytics.mart_topic_trends`, `analytics.mart_source_activity` for the
dashboard-ready tables).

**Neon gotcha:** use the DIRECT connection host, not the `-pooler` one, for `POSTGRES_HOST`. The
pooled endpoint runs PgBouncer in transaction-pooling mode, which hangs Spark's JDBC writer
indefinitely on its TRUNCATE+batch-INSERT sequence — confirmed by testing, no error, it just never
returns. The direct endpoint doesn't have this problem. (If you want a pooled connection for
Streamlit's read traffic specifically, that's fine — just don't use it for the Spark loader or dbt.)

To switch back to fully local Postgres instead of Neon: set `POSTGRES_HOST=postgres` in `.env`,
remove `POSTGRES_SSLMODE`, and `docker compose up -d postgres` (schemas auto-created from
`postgres/init/` on first startup against an empty volume).

### Running the full pipeline via Airflow

```bash
docker compose up -d airflow-postgres redis
docker compose up airflow-init          # one-time: migrates DB, creates admin user
docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker
```

Airflow UI: http://localhost:8082 (note: 8080 is taken by the Spark master UI). Login with
`_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD` from `.env` (default `airflow`/`airflow`
— change this if you ever expose the UI beyond localhost). The `newslake_pipeline` DAG is paused
by default; unpause it in the UI or via `airflow dags unpause newslake_pipeline`.

**Docker-outside-of-Docker note:** `airflow-worker` runs task shell commands (`docker compose run
...`) against the HOST's Docker daemon via a mounted socket, not a daemon of its own. That means
any path it passes to `docker compose` has to be a real host path — the container mounts the repo
at the *same absolute path* it has on the host (`${HOST_PROJECT_DIR}:${HOST_PROJECT_DIR}:ro`) so
that both the container's view and the host daemon's view of build contexts/volumes agree. If you
move the repo, update `HOST_PROJECT_DIR` in `.env` and restart `airflow-worker`.

**Gotcha to remember:** any `.env` value containing spaces or shell-special characters (a path
with a space, a cron string like `0 6 * * *`) must be quoted (`KEY="value with spaces"`). Docker
Compose's own `.env` parser tolerates unquoted values fine, but `run_job.sh` and the ingestion
scripts `source .env` directly in bash, which does not.

### Dashboard (Streamlit)

```bash
docker compose up -d streamlit
```

http://localhost:8501 — three pages, switched via top tabs (`st.navigation(..., position="top")`
in `streamlit/app.py`, the thin entrypoint; actual page content lives in `streamlit/dashboard.py`,
`streamlit/pipeline_guide.py`, and `streamlit/data_explorer.py`):

**Dashboard**: Overview KPIs, Topic Trends, Source Analysis, Recent News, and a **Pipeline** tab
showing the `newslake_pipeline` DAG as a live animated flow diagram (polls the Airflow REST API
every 3s via `streamlit/airflow_client.py` + `streamlit/pipeline_viz.py`), with a button to
trigger a run directly from the dashboard, a badge on the latest run showing whether it was
triggered by you (manual) or by Airflow's own schedule, and the next scheduled run time
(`GET /api/v2/dags/{dag_id}` → `next_dagrun_run_after` + `timetable_description`).

**Pipeline Guide**: static, always-available explainer (no live connection needed, works
identically local or deployed) walking through what actually happens at each stage — Bronze
ingestion, Silver cleaning/validation/dedup, Gold aggregation, the Postgres raw landing zone, dbt's
staging→intermediate→marts build, plus the quality-gate and retry/idempotency story. Content lives
in `streamlit/pipeline_guide.py`, rendered via `ui_helpers.layer_card()`.

**Data Explorer**: a read-only browser for every storage layer directly — not just the curated
visualizations: Bronze JSON (drill into year/month/day/hour partitions in MinIO and preview a raw
object), Silver/Gold Parquet (schema + full contents, read straight from MinIO via `s3fs`/`pyarrow`),
and both Postgres schemas (`raw` and `analytics`) via a generic table-picker + `SELECT * LIMIT N`.
Shared read logic lives in `streamlit/data_layer.py`.

**Local vs. deployed behavior is deliberate, not a fallback.** `data_layer.IS_LOCAL_ENV` (true
whenever MinIO credentials are configured — MinIO and Airflow are only ever set up together, in
the local stack) gates the UI *before* attempting any MinIO/Airflow call:
- **Locally**: Pipeline tab is fully live (diagram + trigger button); Data Explorer's Bronze/Silver/Gold
  tabs work normally.
- **Deployed** (e.g. Streamlit Community Cloud): those same views show a designed "locked feature"
  card (`streamlit/ui_helpers.py::locked_feature_card`) explaining why, instead of an error — this
  isn't a transient failure that might resolve if your Docker happens to be running; `airflow-apiserver`
  and `minio` are Docker-internal network hostnames with no route from the public internet at all,
  regardless of local Docker state. Below the locked card, Bronze/Silver/Gold tabs also show a
  **static sample** (`streamlit/sample_data.json` — one real captured Bronze record, schema + a
  couple of real sample rows for each Silver/Gold table, generated once from an actual pipeline
  run via `ui_helpers.render_bronze_sample()`/`render_tabular_sample()`) so a visitor can still see
  real column names and real data shape — clearly labeled as a static snapshot, not live data.
  Postgres-backed views (main dashboard, Data Explorer's `raw`/`analytics`
  tabs) work identically in both environments since Neon is cloud-hosted. Tab order also flips:
  locally Pipeline is first (dev-focused default); deployed, it's last, so a visitor's first
  impression is real data, not a locked card.

**Deploying to Streamlit Community Cloud:** push to GitHub, create an app pointed at
`streamlit/app.py`, set Python version to **3.12** in Advanced settings (Streamlit Cloud has
defaulted new apps to a much newer Python with no prebuilt wheels yet for `psycopg2-binary`/`pandas`
at our pinned versions — `psycopg2-binary` fails outright without `pg_config`, which the build image
doesn't have), and set the `POSTGRES_*` values from `.env` as Streamlit Cloud secrets (Settings →
Secrets, TOML format — these are exposed as both `st.secrets` and `os.environ`, no code changes
needed). Do not set `MINIO_*`/`AIRFLOW_*` secrets — those services don't exist in the cloud
deployment at all, and the app is designed to show the locked-feature state cleanly without them.
