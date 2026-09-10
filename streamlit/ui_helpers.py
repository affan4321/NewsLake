"""Shared visual components used across the main dashboard and Data Explorer pages."""
import streamlit as st


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
        ">
            <div style="font-size: 34px; margin-bottom: 10px;">{icon}</div>
            <div style="font-size: 16px; font-weight: 600; color: #e6edf3; margin-bottom: 8px;">{title}</div>
            <div style="font-size: 13px; line-height: 1.6; color: #8b949e; max-width: 520px; margin: 0 auto;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, icon: str = ""):
    """A bordered KPI tile -- st.metric alone reads as plain text; this gives it visual weight."""
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size: 12px; color: #8b949e; text-transform: uppercase; '
            f'letter-spacing: 0.04em; margin-bottom: 4px;">{icon} {label}</div>'
            f'<div style="font-size: 28px; font-weight: 700; color: #e6edf3;">{value}</div>',
            unsafe_allow_html=True,
        )
