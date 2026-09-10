import streamlit as st

import ui_helpers

ui_helpers.inject_global_css()
st.title("📖 Pipeline Guide")
st.caption("What actually happens to a news article between the API and this dashboard.")

st.markdown(
    """
    <div style="text-align:center; padding: 16px 0 24px; font-size: 14px; color:#8b949e;">
        <b style="color:#f59e0b;">Bronze</b> &nbsp;→&nbsp;
        <b style="color:#94a3b8;">Silver</b> &nbsp;→&nbsp;
        <b style="color:#eab308;">Gold</b> &nbsp;→&nbsp;
        <b style="color:#38bdf8;">Postgres (raw)</b> &nbsp;→&nbsp;
        <b style="color:#a78bfa;">dbt → Postgres (analytics)</b> &nbsp;→&nbsp;
        <b style="color:#ef4444;">this dashboard</b>
    </div>
    """,
    unsafe_allow_html=True,
)

ui_helpers.layer_card(
    "🥉", "Bronze — Raw Ingestion", "#f59e0b",
    "The article exactly as the API returned it. Nothing is cleaned, filtered, or reshaped here — "
    "Bronze exists to preserve the original response for replay/debugging, even if later stages have bugs.",
    [
        "Two API calls per article: <code>/v1/news</code> (lightweight listing) then "
        "<code>/v1/details</code> (full body, authors, topics, original URL)",
        "Stored as one JSON file per article, tagged with <code>run_id</code>, <code>ingested_at</code>, and <code>source</code>",
        "Partitioned by ingestion time (year/month/day/hour) — not publish time — so a given pipeline run's "
        "output is always findable as one folder",
        "Rate-limited to 2 requests/sec to respect the API's daily quota",
    ],
)

ui_helpers.layer_card(
    "🥈", "Silver — Cleaned &amp; Validated", "#94a3b8",
    "Apache Spark turns the raw, nested JSON into a validated, deduplicated table. This is where "
    "\"filtering\" actually happens — bad records don't reach anything downstream.",
    [
        "Nested JSON flattened into columns: title, description, content, url, source, published_at, language, topics...",
        "<b>Validation</b>: article_id, title, url, and published_at must all be present — records missing any of "
        "these are <b>quarantined</b>, not silently dropped, so they can still be inspected later",
        "<b>Deduplication</b>: if the same article_id appears more than once (e.g. re-fetched on a later run), "
        "only the most recently ingested copy is kept",
        "<b>Source normalization</b>: publisher names are slugified into a stable source_id — with a hash suffix, "
        "so publishers in non-Latin scripts (Cyrillic, Arabic, Korean...) still get a unique ID instead of colliding",
        "Timestamps parsed and normalized to UTC",
        "Written as Snappy-compressed Parquet, partitioned by publish date",
    ],
)

ui_helpers.layer_card(
    "🥇", "Gold — Aggregated Analytics", "#eab308",
    "Spark pre-computes the daily/hourly rollups so the dashboard never has to rescan article-level "
    "data just to draw a trend chart.",
    [
        "daily_article_metrics — articles per day, distinct sources, distinct topics",
        "daily_source_metrics — articles per publisher per day",
        "topic_trends — articles and unique sources per topic per day",
        "article_activity — publishing volume by hour of day",
        "Unpartitioned: daily-grain aggregates stay small even over years, so partitioning would just add overhead",
    ],
)

ui_helpers.layer_card(
    "📥", "Postgres — Raw Landing Zone", "#38bdf8",
    "dbt can't read Parquet files sitting in MinIO directly, so this step lands article-grain Silver "
    "data into Postgres for dbt to build on — deliberately not the Gold aggregates.",
    [
        "silver/articles and silver/sources loaded via Spark's JDBC writer",
        "topics (an array in Silver) is exploded into a proper article_topics bridge table here, sidestepping "
        "database array-type complications entirely",
        "authors is dropped — no dashboard view needs it, so it stays lake-only",
        "Full replace each run, not an incremental upsert (that's planned future work)",
    ],
)

ui_helpers.layer_card(
    "🔧", "dbt → Postgres (analytics)", "#a78bfa",
    "dbt builds its own SQL transformation layer on top of the raw landing zone — deliberately "
    "independent of Spark's Gold aggregates, so this is a second, SQL-native way of deriving the same "
    "kind of analytics, not just a copy of the first.",
    [
        "staging models (stg_articles, stg_sources, stg_article_topics) — light renaming/typing, one-to-one with the source",
        "intermediate model (int_article_topics) — joins articles to their topics and source",
        "marts: fct_articles (article-grain fact table), mart_topic_trends, mart_source_activity — dbt's own "
        "SQL <code>GROUP BY</code> aggregations, not a passthrough of Gold",
        "22 automated tests run after every build: uniqueness, not-null, referential integrity, accepted-value checks",
        "This is the exact schema the dashboard and Data Explorer's \"analytics\" tab query",
    ],
)

st.divider()
st.subheader("Data quality &amp; reliability")

col1, col2 = st.columns(2)
with col1:
    ui_helpers.layer_card(
        "🚧", "Nothing silently disappears", "#ef4444",
        "Two independent layers of validation, on top of each other.",
        [
            "Records failing Silver's required-field checks go to a quarantine path, not the trash",
            "A separate silver_quality_checks step re-verifies row counts, null checks, duplicate article_ids, "
            "and the quarantine ratio — independent of, and in addition to, dbt's own 22 tests",
        ],
    )
with col2:
    ui_helpers.layer_card(
        "🔁", "Retries &amp; idempotency", "#22c55e",
        "Built to survive real failures, not just the happy path.",
        [
            "Airflow automatically retries failed tasks — verified live during development: a genuine API "
            "disconnect mid-run was caught, retried after the configured delay, and the pipeline completed",
            "Bronze files are keyed by article_id, so re-running ingestion can never create duplicates",
        ],
    )

st.caption("Curious what the data actually looks like at each of these stages? Check the **Data Explorer** tab.")
