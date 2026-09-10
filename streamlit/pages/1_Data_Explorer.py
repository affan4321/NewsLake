import json

import streamlit as st

import data_layer

st.set_page_config(page_title="NewsLake · Data Explorer", page_icon="🔍", layout="wide")
st.title("🔍 Data Explorer")
st.caption("Read-only browser for every storage layer — Bronze/Silver/Gold in MinIO, raw/analytics in Postgres.")

tab_bronze, tab_silver, tab_gold, tab_raw, tab_analytics = st.tabs(
    ["Bronze (JSON)", "Silver (Parquet)", "Gold (Parquet)", "Postgres: raw", "Postgres: analytics"]
)

# Each tab is independently guarded: MinIO (Bronze/Silver/Gold) is local-only and won't be
# reachable from a cloud deployment of this app, so a connection failure there should only
# disable that tab, not crash the whole page.

with tab_bronze:
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
    try:
        table = st.selectbox("Table", ["articles", "sources"], key="silver_table")
        df = data_layer.read_parquet_table(f"silver/{table}/")
        st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
        st.dataframe(df.dtypes.astype(str).rename("dtype"), use_container_width=True)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't reach MinIO: {e}")

with tab_gold:
    try:
        table = st.selectbox(
            "Table",
            ["daily_article_metrics", "daily_source_metrics", "topic_trends", "article_activity"],
            key="gold_table",
        )
        df = data_layer.read_parquet_table(f"gold/{table}/")
        st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't reach MinIO: {e}")

with tab_raw:
    try:
        tables = data_layer.list_pg_tables("raw")
        table = st.selectbox("Table", tables, key="raw_table")
        if table:
            count = data_layer.pg_row_count("raw", table)
            limit = st.slider("Rows to show", 10, 500, 100, key="raw_limit")
            st.caption(f"{count:,} total rows — showing up to {limit}")
            st.dataframe(data_layer.read_pg_table("raw", table, limit), use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't reach Postgres: {e}")

with tab_analytics:
    try:
        tables = data_layer.list_pg_tables("analytics")
        table = st.selectbox("Table", tables, key="analytics_table")
        if table:
            count = data_layer.pg_row_count("analytics", table)
            limit = st.slider("Rows to show", 10, 500, 100, key="analytics_limit")
            st.caption(f"{count:,} total rows — showing up to {limit}")
            st.dataframe(data_layer.read_pg_table("analytics", table, limit), use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't reach Postgres: {e}")
