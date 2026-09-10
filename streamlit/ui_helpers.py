"""Shared visual components used across the main dashboard and Data Explorer pages."""
import json
import os
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import data_layer

_SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "sample_data.json")
_sample_data_cache = None


def format_relative_time(iso_timestamp: str) -> str:
    """'2026-09-12T06:00:00Z' -> 'in 17h 23m' (or 'Xd Yh' beyond a day, or 'any moment now'
    once past due -- the DAG run just hasn't been picked up by the scheduler yet)."""
    target = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    delta = target - datetime.now(timezone.utc)
    total_seconds = delta.total_seconds()
    if total_seconds <= 0:
        return "any moment now"
    days, rem = divmod(int(total_seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days > 0:
        return f"in {days}d {hours}h"
    if hours > 0:
        return f"in {hours}h {minutes}m"
    return f"in {minutes}m"


def inject_global_css():
    """Call once per page. Page-load entrance fade (plays once on mount, not on every
    Streamlit rerun/interaction since stAppViewContainer persists across those) plus
    hover interactions for the custom card components below."""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            animation: nl-fade-in 0.5s ease-out;
        }
        @keyframes nl-fade-in {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        [data-testid="stTabs"] button[role="tab"] {
            transition: color 0.2s ease;
        }

        /* Top page navigation (st.navigation(position="top")): centered, larger, styled
           as plain text links (underline on hover/active) instead of Streamlit's default
           pill/tab chrome. Selectors confirmed by walking the LIVE DOM at runtime -- the
           real nav flex row is an .rc-overflow div (from the rc-overflow library
           Streamlit uses for the nav's "collapse into a ... menu" overflow behavior),
           which has no data-testid of its own.
           Centering: confirmed via computed-style diagnostics that .rc-overflow's own
           width is already 100% of the viewport (rect: x=0, width=1912px on a 1912px
           screen) -- so absolute-positioning + transform (an earlier attempt) correctly
           computed left=50% but had zero visible effect, since centering a box that's
           already exactly viewport-width doesn't move it anywhere. The actual fix is
           just centering its *contents*, since it's already a full-width flex row. */
        .rc-overflow {
            display: flex !important;
            justify-content: center !important;
            gap: 4px;
        }
        [data-testid="stTopNavLink"] {
            font-size: 16px !important;
            padding: 12px 22px !important;
            background: transparent !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            transition: border-color 0.2s ease, color 0.2s ease;
            position: relative !important;
        }
        [data-testid="stTopNavLink"]:hover {
            border-bottom-color: #ef4444 !important;
            color: #ef4444 !important;
        }
        [data-testid="stTopNavLink"][aria-current="page"] {
            background: transparent !important;
            font-weight: 600;
        }
        /* Selected page: a small gradient pill below the link instead of the hover underline,
           so the two states read as visually distinct (transient hover vs. persistent selection). */
        [data-testid="stTopNavLink"][aria-current="page"]::after {
            content: "";
            position: absolute;
            bottom: 4px;
            left: 50%;
            transform: translateX(-50%);
            width: 26px;
            height: 4px;
            border-radius: 2px;
            background: linear-gradient(90deg, #ef4444, #f59e0b);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def postgres_source_badge():
    """Tells visitors whether they're looking at live cloud data or a local dev instance --
    driven by the actual POSTGRES_HOST, so it can't go stale if the backend ever changes."""
    if data_layer.POSTGRES_IS_NEON:
        st.caption("🟢 Live data — served directly from Neon (cloud-hosted PostgreSQL), not a static export.")
    else:
        st.caption("💻 Served from a local PostgreSQL instance.")


def _load_sample_data() -> dict:
    global _sample_data_cache
    if _sample_data_cache is None:
        with open(_SAMPLE_DATA_PATH) as f:
            _sample_data_cache = json.load(f)
    return _sample_data_cache


def _sample_caption():
    st.caption("📎 Static example captured from a real pipeline run — not live data, but the real shape of it.")


def render_bronze_sample():
    """Bronze has no fixed schema (raw JSON) -- just show one real captured object."""
    _sample_caption()
    st.json(_load_sample_data()["bronze"])


def render_tabular_sample(key: str):
    """For Silver/Gold: a schema table (column names + dtypes) plus a couple of real sample rows."""
    data = _load_sample_data()[key]
    _sample_caption()
    st.write("**Columns**")
    st.dataframe(pd.DataFrame(data["columns"]), hide_index=True)
    st.write("**Sample rows**")
    st.dataframe(pd.DataFrame(data["sample_rows"]), hide_index=True)


def locked_feature_card(icon: str, title: str, message: str):
    """A calm, intentional 'not available here' card -- not an error, a designed state."""
    st.markdown(
        f"""
        <div style="
            border: 1px solid #30363d;
            background: linear-gradient(135deg, rgba(56,189,248,0.06), rgba(129,140,248,0.06));
            border-radius: 14px;
            padding: 36px 32px;
            text-align: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 10px 28px rgba(0,0,0,0.3)';"
          onmouseout="this.style.transform='none'; this.style.boxShadow='none';">
            <div style="font-size: 34px; margin-bottom: 10px;">{icon}</div>
            <div style="font-size: 16px; font-weight: 600; color: #e6edf3; margin-bottom: 8px;">{title}</div>
            <div style="font-size: 13px; line-height: 1.6; color: #8b949e; max-width: 520px; margin: 0 auto;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def layer_card(icon: str, title: str, accent_color: str, description: str, points: list[str]):
    """A left-accented card describing one pipeline stage -- used on the Pipeline Guide page."""
    points_html = "".join(f"<li>{p}</li>" for p in points)
    st.markdown(
        f"""
        <div style="
            border: 1px solid #30363d;
            border-left: 4px solid {accent_color};
            border-radius: 10px;
            padding: 20px 24px;
            margin-bottom: 16px;
            background: linear-gradient(135deg, {accent_color}14, transparent 60%);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        " onmouseover="this.style.transform='translateX(4px)'; this.style.boxShadow='0 6px 18px rgba(0,0,0,0.25)';"
          onmouseout="this.style.transform='none'; this.style.boxShadow='none';">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <span style="font-size:24px;">{icon}</span>
                <span style="font-size:17px; font-weight:700; color:#e6edf3;">{title}</span>
            </div>
            <div style="font-size:13px; color:#8b949e; margin-bottom:10px; line-height:1.5;">{description}</div>
            <ul style="margin:0; padding-left:20px; color:#c9d1d9; font-size:13px; line-height:1.85;">
                {points_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, icon: str = ""):
    """A bordered KPI tile. Numeric values animate as a count-up on load; non-numeric
    values (e.g. a topic name) fade in as-is. Built as a components.html() iframe rather
    than st.markdown because inline <script> tags injected via st.markdown never execute
    (React sets innerHTML, which browsers don't run scripts from) -- components.html()
    renders a real srcdoc document that does."""
    is_numeric = isinstance(value, (int, float))
    target = value if is_numeric else 0
    display_text = f"{value:,}" if is_numeric else str(value)
    node_id = f"kpi-{uuid.uuid4().hex[:8]}"

    counter_script = f"""
        <script>
        (function() {{
            var el = document.getElementById("{node_id}");
            var target = {target};
            var duration = 900;
            var start = null;
            function step(ts) {{
                if (!start) start = ts;
                var progress = Math.min((ts - start) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = Math.round(eased * target).toLocaleString();
                if (progress < 1) requestAnimationFrame(step);
            }}
            requestAnimationFrame(step);
        }})();
        </script>
    """ if is_numeric else ""

    html = f"""
    <html>
    <head>
    <style>
        body {{ margin: 0; background: transparent; font-family: -apple-system, sans-serif; }}
        .card {{
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 18px 20px;
            background: linear-gradient(135deg, rgba(239,68,68,0.05), rgba(56,189,248,0.03));
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 24px rgba(0,0,0,0.35);
            border-color: #ef4444aa;
        }}
        .label {{
            font-size: 12px; color: #8b949e; text-transform: uppercase;
            letter-spacing: 0.04em; margin-bottom: 6px;
        }}
        .value {{ font-size: 28px; font-weight: 700; color: #e6edf3; }}
    </style>
    </head>
    <body>
        <div class="card">
            <div class="label">{icon} {label}</div>
            <div class="value" id="{node_id}">{'0' if is_numeric else display_text}</div>
        </div>
        {counter_script}
    </body>
    </html>
    """
    components.html(html, height=90)
