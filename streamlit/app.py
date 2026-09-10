"""Entrypoint. Just wires up navigation -- actual page content lives in dashboard.py and
data_explorer.py. position="top" renders the switcher as tabs in the header instead of a
sidebar list, and gives real titles/icons instead of Streamlit's filename-derived labels
("app", "1 Data Explorer") from the legacy pages/ auto-discovery convention.
"""
import streamlit as st

st.set_page_config(page_title="NewsLake", page_icon="📰", layout="wide")

dashboard = st.Page("dashboard.py", title="Dashboard", icon="📰", default=True)
explorer = st.Page("data_explorer.py", title="Data Explorer", icon="🔍")

pg = st.navigation([dashboard, explorer], position="top")
pg.run()
