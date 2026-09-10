import copy
import os

import pandas as pd
import plotly.express as px
import plotly.io as pio
import requests
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

import airflow_client
import data_layer
import pipeline_viz
import ui_helpers

# Transparent backgrounds so charts blend into the app's own dark theme instead of
# plotly_dark's slightly different gray. copy.deepcopy avoids mutating the shared
# built-in "plotly_dark" template object.
_nl_template = copy.deepcopy(pio.templates["plotly_dark"])
_nl_template.layout.paper_bgcolor = "rgba(0,0,0,0)"
_nl_template.layout.plot_bgcolor = "rgba(0,0,0,0)"
pio.templates["newslake"] = _nl_template
px.defaults.template = "newslake"
px.defaults.color_discrete_sequence = [
    "#ef4444", "#38bdf8", "#a78bfa", "#22c55e", "#f59e0b", "#f472b6", "#2dd4bf", "#fb923c",
]

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


ui_helpers.inject_global_css()

st.title("📰 NewsLake")
st.caption("A news data lakehouse — MinIO + Spark + Airflow + dbt + Postgres")
ui_helpers.postgres_source_badge()

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
with col1:
    ui_helpers.kpi_card("Total Articles", int(overview["total_articles"]), "📰")
with col2:
    ui_helpers.kpi_card("Active Sources", int(overview["active_sources"]), "📡")
with col3:
    ui_helpers.kpi_card("Articles Today", int(overview["articles_today"]), "📅")
with col4:
    ui_helpers.kpi_card("Top Topic", overview["top_topic"] or "—", "🔥")

st.divider()


def render_pipeline_tab():
    if data_layer.IS_LOCAL_ENV:
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
    else:
        # No live Airflow connection from this deployment (see README) -- show the
        # pipeline's shape as a static illustration instead of attempting (and failing)
        # a live connection every few seconds.
        idle_states = {t: None for t in airflow_client.TASK_ORDER}
        components.html(pipeline_viz.render(idle_states, None, None), height=220)
        ui_helpers.locked_feature_card(
            "🔒",
            "Live pipeline status isn't available here",
            "The orchestration layer (Airflow) runs in a local development environment, separate "
            "from this deployment. The diagram above shows the pipeline's shape — ingest, "
            "transform, load, test — but live run status and manual triggering only work when "
            "running the full stack locally.",
        )


def render_topics_tab():
    topic_trends = run_query("""
        select date, topic, article_count, unique_sources
        from analytics.mart_topic_trends
        order by date, article_count desc
    """)

    if topic_trends.empty:
        st.info("No topic trend data yet — run the pipeline to populate analytics.mart_topic_trends.")
        return

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


def render_sources_tab():
    source_activity = run_query("""
        select date, source_id, source_name, article_count
        from analytics.mart_source_activity
        order by date, article_count desc
    """)

    if source_activity.empty:
        st.info("No source activity data yet — run the pipeline to populate analytics.mart_source_activity.")
        return

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


def render_recent_tab():
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
        return

    st.dataframe(
        recent,
        hide_index=True,
        column_config={
            "title": "Title",
            "source_name": "Source",
            "published_at": st.column_config.DatetimeColumn("Published", format="YYYY-MM-DD HH:mm"),
            "topics": "Topics",
            "url": st.column_config.LinkColumn("URL", display_text="Open ↗"),
        },
    )


TAB_RENDERERS = {
    "Pipeline": render_pipeline_tab,
    "Topic Trends": render_topics_tab,
    "Source Analysis": render_sources_tab,
    "Recent News": render_recent_tab,
}

# Pipeline is only fully interactive locally -- lead with the data tabs on a public
# deployment instead of opening on a locked-feature card.
tab_order = (
    ["Pipeline", "Topic Trends", "Source Analysis", "Recent News"]
    if data_layer.IS_LOCAL_ENV
    else ["Topic Trends", "Source Analysis", "Recent News", "Pipeline"]
)

for tab, name in zip(st.tabs(tab_order), tab_order):
    with tab:
        TAB_RENDERERS[name]()
