import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

import airflow_client
import pipeline_viz

st.set_page_config(page_title="NewsLake", page_icon="📰", layout="wide")

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "newslake")
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_SSLMODE = os.environ.get("POSTGRES_SSLMODE")  # unset for local postgres, "require" for Neon


@st.cache_resource
def get_engine():
    url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    if POSTGRES_SSLMODE:
        url += f"?sslmode={POSTGRES_SSLMODE}"
    return create_engine(url)


@st.cache_data(ttl=60)
def run_query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


st.title("📰 NewsLake")
st.caption("A local news data lakehouse — MinIO + Spark + Airflow + dbt + Postgres")

# --- Overview ---
overview = run_query("""
    select
        (select count(*) from analytics.fct_articles) as total_articles,
        (select count(distinct source_id) from analytics.fct_articles) as active_sources,
        (select count(*) from analytics.fct_articles where published_date = current_date) as articles_today,
        (select topic from analytics.mart_topic_trends
         where date = (select max(date) from analytics.mart_topic_trends)
         order by article_count desc limit 1) as top_topic
""").iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Articles", f"{overview['total_articles']:,}")
col2.metric("Active Sources", f"{overview['active_sources']:,}")
col3.metric("Articles Today", f"{overview['articles_today']:,}")
col4.metric("Top Topic", overview["top_topic"] or "—")

st.divider()

tab_pipeline, tab_topics, tab_sources, tab_recent = st.tabs(
    ["Pipeline", "Topic Trends", "Source Analysis", "Recent News"]
)

with tab_pipeline:
    if st.button("▶ Run Pipeline Now", type="primary"):
        try:
            airflow_client.trigger_run()
            st.success("Pipeline triggered.")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                st.warning("A run is already in progress.")
            else:
                st.error(f"Failed to trigger pipeline: {e}")
        except requests.RequestException as e:
            st.error(f"Could not reach Airflow API: {e}")

    @st.fragment(run_every="3s")
    def pipeline_status():
        try:
            run = airflow_client.get_latest_run()
        except requests.RequestException as e:
            st.error(f"Could not reach Airflow API at {airflow_client.AIRFLOW_API_BASE_URL}: {e}")
            return

        if run is None:
            task_states = {t: None for t in airflow_client.TASK_ORDER}
            components.html(pipeline_viz.render(task_states, None, None), height=220)
            return

        task_states = airflow_client.get_task_states(run["dag_run_id"])
        components.html(
            pipeline_viz.render(
                task_states, run["state"], run["dag_run_id"],
                run_type=run.get("run_type"),
                triggered_by=run.get("triggering_user_name"),
            ),
            height=220,
        )

    pipeline_status()

with tab_topics:
    topic_trends = run_query("""
        select date, topic, article_count, unique_sources
        from analytics.mart_topic_trends
        order by date, article_count desc
    """)

    if topic_trends.empty:
        st.info("No topic trend data yet — run the pipeline to populate analytics.mart_topic_trends.")
    else:
        top_n = st.slider("Show top N topics (by total articles)", 5, 30, 15)
        totals = topic_trends.groupby("topic")["article_count"].sum().sort_values(ascending=False)
        top_topics = totals.head(top_n).index

        st.subheader("Top topics")
        fig_bar = px.bar(
            totals.head(top_n).reset_index(),
            x="article_count", y="topic", orientation="h",
            labels={"article_count": "Articles", "topic": "Topic"},
        )
        fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Article count over time, by topic")
        trend_subset = topic_trends[topic_trends["topic"].isin(top_topics)]
        fig_line = px.line(
            trend_subset, x="date", y="article_count", color="topic", markers=True,
            labels={"article_count": "Articles", "date": "Date"},
        )
        st.plotly_chart(fig_line, use_container_width=True)

with tab_sources:
    source_activity = run_query("""
        select date, source_id, source_name, article_count
        from analytics.mart_source_activity
        order by date, article_count desc
    """)

    if source_activity.empty:
        st.info("No source activity data yet — run the pipeline to populate analytics.mart_source_activity.")
    else:
        top_n = st.slider("Show top N publishers (by total articles)", 5, 30, 15, key="sources_top_n")
        totals = source_activity.groupby("source_name")["article_count"].sum().sort_values(ascending=False)
        top_sources = totals.head(top_n).index

        st.subheader("Articles by publisher")
        fig_bar = px.bar(
            totals.head(top_n).reset_index(),
            x="article_count", y="source_name", orientation="h",
            labels={"article_count": "Articles", "source_name": "Publisher"},
        )
        fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Publisher activity over time")
        activity_subset = source_activity[source_activity["source_name"].isin(top_sources)]
        fig_line = px.line(
            activity_subset, x="date", y="article_count", color="source_name", markers=True,
            labels={"article_count": "Articles", "date": "Date"},
        )
        st.plotly_chart(fig_line, use_container_width=True)

with tab_recent:
    limit = st.slider("Number of articles", 10, 200, 50)
    recent = run_query(f"""
        select
            a.title,
            a.source_name,
            a.published_at,
            a.url,
            string_agg(distinct t.topic, ', ') as topics
        from analytics.fct_articles a
        left join analytics.int_article_topics t on a.article_id = t.article_id
        group by a.article_id, a.title, a.source_name, a.published_at, a.url
        order by a.published_at desc
        limit {limit}
    """)

    if recent.empty:
        st.info("No articles yet — run the pipeline to populate analytics.fct_articles.")
    else:
        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
            column_config={
                "title": "Title",
                "source_name": "Source",
                "published_at": st.column_config.DatetimeColumn("Published", format="YYYY-MM-DD HH:mm"),
                "topics": "Topics",
                "url": st.column_config.LinkColumn("URL", display_text="Open ↗"),
            },
        )
