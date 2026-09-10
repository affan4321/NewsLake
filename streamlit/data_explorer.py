import json

import streamlit as st

import data_layer
import ui_helpers

ui_helpers.inject_global_css()
st.title("🔍 Data Explorer")
st.caption("Read-only browser for every storage layer — Bronze/Silver/Gold in MinIO, raw/analytics in Postgres.")

MINIO_LOCKED_MESSAGE = (
    "This tab reads directly from MinIO, the local object store backing the data lake. "
    "MinIO only runs in the local development environment, so this view isn't available "
    "from this deployment — the main dashboard and the Postgres tabs here still show live data."
)

tab_bronze, tab_silver, tab_gold, tab_raw, tab_analytics = st.tabs(
    ["Bronze (JSON)", "Silver (Parquet)", "Gold (Parquet)", "Postgres: raw", "Postgres: analytics"]
)

with tab_bronze:
    if not data_layer.IS_LOCAL_ENV:
        ui_helpers.locked_feature_card("🔒", "Live Bronze browsing isn't available here", MINIO_LOCKED_MESSAGE)
        st.divider()
        ui_helpers.render_bronze_sample()
    else:
        try:
            st.write("Drill into a partition to preview a raw bronze object as landed by ingestion.")
            base = "bronze/source=freenewsapi/"

            years = data_layer.list_prefixes(base)
            if not years:
                st.info("No bronze data yet — run the pipeline's fetch_news step first.")
            else:
                year = st.selectbox("Year", years, format_func=lambda p: p.rstrip("/").split("=")[-1])
                months = data_layer.list_prefixes(year)
                month = st.selectbox("Month", months, format_func=lambda p: p.rstrip("/").split("=")[-1])
                days = data_layer.list_prefixes(month)
                day = st.selectbox("Day", days, format_func=lambda p: p.rstrip("/").split("=")[-1])
                hours = data_layer.list_prefixes(day)
                hour = st.selectbox("Hour", hours, format_func=lambda p: p.rstrip("/").split("=")[-1])

                objects = data_layer.list_objects(hour)
                st.caption(f"{len(objects)} object(s) in this partition")
                if objects:
                    keys = [o["Key"] for o in objects]
                    selected_key = st.selectbox("File", keys, format_func=lambda k: k.split("/")[-1])
                    content = json.loads(data_layer.read_object_text(selected_key))
                    st.json(content)
        except Exception as e:
            st.error(f"Couldn't reach MinIO: {e}")

with tab_silver:
    if not data_layer.IS_LOCAL_ENV:
        ui_helpers.locked_feature_card("🔒", "Live Silver browsing isn't available here", MINIO_LOCKED_MESSAGE)
        st.divider()
        table = st.selectbox("Table", ["articles", "sources"], key="silver_table_static")
        ui_helpers.render_tabular_sample(f"silver_{table}")
    else:
        try:
            table = st.selectbox("Table", ["articles", "sources"], key="silver_table")
            df = data_layer.read_parquet_table(f"silver/{table}/")
            st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
            st.dataframe(df.dtypes.astype(str).rename("dtype"))
            st.dataframe(df)
        except Exception as e:
            st.error(f"Couldn't reach MinIO: {e}")

with tab_gold:
    if not data_layer.IS_LOCAL_ENV:
        ui_helpers.locked_feature_card("🔒", "Live Gold browsing isn't available here", MINIO_LOCKED_MESSAGE)
        st.divider()
        table = st.selectbox(
            "Table",
            ["daily_article_metrics", "daily_source_metrics", "topic_trends", "article_activity"],
            key="gold_table_static",
        )
        ui_helpers.render_tabular_sample(f"gold_{table}")
    else:
        try:
            table = st.selectbox(
                "Table",
                ["daily_article_metrics", "daily_source_metrics", "topic_trends", "article_activity"],
                key="gold_table",
            )
            df = data_layer.read_parquet_table(f"gold/{table}/")
            st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Couldn't reach MinIO: {e}")

with tab_raw:
    ui_helpers.postgres_source_badge()
    try:
        tables = data_layer.list_pg_tables("raw")
        table = st.selectbox("Table", tables, key="raw_table")
        if table:
            count = data_layer.pg_row_count("raw", table)
            limit = st.slider("Rows to show", 10, 500, 100, key="raw_limit")
            st.caption(f"{count:,} total rows — showing up to {limit}")
            st.dataframe(data_layer.read_pg_table("raw", table, limit))
    except Exception as e:
        st.error(f"Couldn't reach Postgres: {e}")

with tab_analytics:
    ui_helpers.postgres_source_badge()
    try:
        tables = data_layer.list_pg_tables("analytics")
        table = st.selectbox("Table", tables, key="analytics_table")
        if table:
            count = data_layer.pg_row_count("analytics", table)
            limit = st.slider("Rows to show", 10, 500, 100, key="analytics_limit")
            st.caption(f"{count:,} total rows — showing up to {limit}")
            st.dataframe(data_layer.read_pg_table("analytics", table, limit))
    except Exception as e:
        st.error(f"Couldn't reach Postgres: {e}")
