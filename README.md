# NewsLake

A containerized, continuously updated news data lakehouse. Ingests raw news data into MinIO, processes it with Apache Spark into Parquet, orchestrates the pipeline with Airflow, applies analytical transformations and tests with dbt, and serves curated datasets through PostgreSQL to a public Next.js site (with an AI chatbot) and a companion Streamlit dashboard.

## Architecture

```
freenewsapi.io -> Python ingestion -> MinIO (bronze, raw JSON)
                                    -> PySpark -> MinIO (silver, Parquet)
                                    -> PySpark -> MinIO (gold, Parquet)
                                    -> load -> PostgreSQL (staging)
                                    -> dbt -> PostgreSQL (marts) -> Next.js (public site, web/)
                                                                 -> Streamlit (companion dashboard)

Airflow (CeleryExecutor) orchestrates every stage above. Schedule is PIPELINE_SCHEDULE_CRON
in .env (default once daily), not hardcoded in the DAG.
```

Two independent frontends read the same `analytics` marts: **`web/`** is the public-facing site
(Next.js, server-rendered, includes an AI chatbot — see [Web app](#web-app-public-site) below);
**`streamlit/`** is a companion dashboard that also doubles as a local operational cockpit (live
Airflow pipeline view, raw storage browser) when running the full stack locally.

## Build stages

- [x] Stage 1 — Python ingestion -> MinIO bronze (fetches /v1/news listing + /v1/details per article)
- [x] Stage 2 — Bronze -> PySpark -> Silver Parquet (silver/articles, silver/sources, quarantine/silver_validation)
- [x] Stage 3 — Silver -> PySpark -> Gold Parquet (daily_article_metrics, daily_source_metrics, topic_trends, article_activity; entity_trends deferred, needs NER)
- [x] Stage 4 — Airflow orchestration (newslake_pipeline DAG: fetch_news -> validate_raw_data -> bronze_to_silver -> silver_quality_checks -> silver_to_gold)
- [x] Stage 5 — Gold -> dbt -> PostgreSQL (load_to_postgres lands article-grain Silver data in `raw`; dbt builds staging/intermediate/marts in `analytics`, dbt_transform + dbt_tests added to the DAG)
- [x] Stage 6 — PostgreSQL -> Streamlit (Overview KPIs, Topic Trends, Source Analysis, Recent News, plus a live animated Pipeline tab with a manual trigger button)
- [x] Stage 7 — PostgreSQL -> Next.js public site (`web/`): server-rendered hero, KPIs, topics, sources, latest articles, and pipeline story, all queried live from `analytics.*` at request time (revalidated hourly)
- [x] Stage 8 — AI chatbot embedded in the public site: text-to-SQL over `analytics.*` via tool calling (Groq + Vercel AI SDK), not RAG — see [Web app](#web-app-public-site)

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

## Web app (public site)

`web/` is a separate Next.js 16 + React 19 + Tailwind 4 app — the actual public face of the
project (Streamlit above is the companion/internal one). It reads `analytics.*` straight from
Neon at request time via `web/src/lib/db.ts` (no separate API layer), and the page revalidates
hourly since the pipeline only publishes once a day.

```bash
cd web
cp .env.example .env.local   # fill in DATABASE_URL, CHATBOT_DATABASE_URL, GROQ_API_KEY, REVALIDATE_SECRET (see below)
npm install
npm run dev
```

http://localhost:3000 — hero, KPI strip, topics/sources/latest-articles sections, a pipeline
story section, and a floating chat widget (bottom-right, on every page).

### Getting fresh data to the site without waiting an hour

The homepage's hourly cache (`revalidate = 3600`) is fine for the normal once-daily schedule,
but it means a manual/off-schedule pipeline run wouldn't show up on the site until that cache
happened to expire — the underlying Postgres data is correct immediately, only the site's
cached HTML lags. (This doesn't affect Streamlit at all, since it queries fresh on every page
load with no caching layer — that mismatch is exactly what surfaces this if you don't know
about it.)

The DAG's last task (`revalidate_site` in `dags/newslake_pipeline.py`) closes this gap: right
after `dbt_tests` passes, it `POST`s to `web/src/app/api/revalidate/route.ts` with a shared
secret, which calls Next.js's `revalidatePath("/")` to force the cache to refresh immediately —
no waiting, no lowering the cache window for normal traffic. Wiring:

- `NEXTJS_SITE_URL` (root `.env`) — where the DAG sends the request. Point this at your
  deployed site (e.g. the Vercel URL) once it's live; `http://localhost:3000` only works if
  you're running the site locally alongside a local pipeline run.
- `REVALIDATE_SECRET` — must be the exact same value in root `.env` (read by the Airflow
  worker) and wherever the site itself is running (`web/.env.local` locally, or your
  deployment platform's env vars in production) — the route rejects any request whose
  `Authorization: Bearer <value>` doesn't match.
- If the request fails (site unreachable, secret mismatch), the task fails and retries per
  `default_args` (2 retries, 5 min apart) like every other task — but the pipeline's actual
  data is already committed and tested by this point, so a failure here only delays the
  site's refresh, it never risks the data itself.

### The chatbot: text-to-SQL, not RAG

The chat widget lets a visitor ask questions in plain English ("which topics have the most
articles?", "who are the top sources?") and get answers computed from the live warehouse. This
is deliberately **not** RAG (no embeddings, no vector search) — the data is relational, not a
pile of documents, so the model instead **writes SQL directly** and we execute it. Architecture:

- **Model**: Groq's free tier running `openai/gpt-oss-120b`, a reasoning-and-tool-calling-capable
  open-weight model. Picked over the Claude API specifically to keep the whole project free to
  run. Groq's model catalog changes over time — if `openai/gpt-oss-120b` ever 404s, check
  `GET https://api.groq.com/openai/v1/models` for the current tool-calling-capable lineup.
- **Framework**: [Vercel AI SDK](https://ai-sdk.dev) (`ai` + `@ai-sdk/groq` + `@ai-sdk/react`) —
  gives one provider-agnostic API for streaming (`streamText`), tool/function calling (`tool()`),
  and a ready-made React hook (`useChat`) that manages message state and renders the stream as it
  arrives. See `web/src/app/api/chat/route.ts` (the streaming endpoint) and
  `web/src/components/Chat.tsx` / `ChatWidget.tsx` (the UI).
- **The one tool** (`web/src/lib/chat-tools.ts`, `queryMarts`): takes a SQL string from the model,
  runs it, returns the rows. The model calls it, reads the result in a second step, then answers
  in words — a multi-step loop (`stopWhen: stepCountIs(5)`), since the SDK's default is to stop
  right after a tool call.
- **The system prompt** (same file) is the model's *only* knowledge of the schema — it describes
  `fct_articles`, `mart_topic_trends`, `mart_source_activity` column-by-column, plus a short
  "About NewsLake" section so questions about the project itself (what it is, how the pipeline
  works) get answered conversationally without touching the database at all.
- **Guardrails, three layers deep** (code doesn't rely on any single one):
  1. Code-level regex rejects anything that isn't a single `SELECT` (`validateSelectOnly`).
  2. A dedicated Postgres role, `chatbot_reader`, has `SELECT`-only grants scoped to the
     `analytics` schema — no `raw`, no writes — enforced by the database itself, not the app.
  3. That role also carries an 8-second `statement_timeout` so a runaway query can't hang.

  To recreate the role on a fresh Neon database:

  ```sql
  CREATE ROLE chatbot_reader WITH LOGIN PASSWORD '<generate one, do not commit it>';
  GRANT USAGE ON SCHEMA analytics TO chatbot_reader;
  GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO chatbot_reader;
  ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO chatbot_reader;
  ALTER ROLE chatbot_reader SET search_path TO analytics;
  ALTER ROLE chatbot_reader SET statement_timeout = '8s';
  ```

  The `search_path` line matters: the system prompt tells the model to query tables unqualified
  (`fct_articles`, not `analytics.fct_articles`) — without it, every query fails with
  "relation does not exist." Put the resulting connection string in `CHATBOT_DATABASE_URL`.
- **A gotcha worth knowing if you touch this code**: Postgres `timestamp` columns (like
  `published_at`) come back from the Neon driver as native JS `Date` objects. Those are fine to
  send to the browser (`JSON.stringify` auto-converts them), but the AI SDK also replays a tool's
  raw return value into the *next* model step as a structured value — and a `Date` isn't valid
  there, so the whole response fails silently with no error surfaced to the user. The tool
  round-trips its result through `JSON.parse(JSON.stringify(rows))` before returning, specifically
  to avoid this.

### Env vars (`web/.env.local`, gitignored)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string the site's pages read from (direct endpoint, not `-pooler`) |
| `CHATBOT_DATABASE_URL` | Connection string for the `chatbot_reader` role above — analytics-only, read-only |
| `GROQ_API_KEY` | Free API key from [console.groq.com](https://console.groq.com) |
