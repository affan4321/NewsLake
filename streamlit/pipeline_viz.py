"""Renders the newslake_pipeline DAG as an animated SVG flow diagram.

Pure string templating, no JS framework -- CSS keyframes drive the pulse/marching-ants/
traveling-dot animations, SVG <animateMotion> drives the dot following the completed path.
Returned HTML is meant for st.components.v1.html().
"""
from airflow_client import TASK_ORDER

LABELS = {
    "fetch_news": "Fetch News",
    "validate_raw_data": "Validate",
    "bronze_to_silver": "Bronze→Silver",
    "silver_quality_checks": "Quality Checks",
    "silver_to_gold": "Silver→Gold",
    "load_to_postgres": "Load to Postgres",
    "dbt_transform": "dbt Run",
    "dbt_tests": "dbt Test",
}

COLORS = {
    "success": "#22c55e",
    "running": "#3b82f6",
    "failed": "#ef4444",
    "up_for_retry": "#f59e0b",
    "upstream_failed": "#ef4444",
    "queued": "#f59e0b",
    None: "#475569",
}

WIDTH, HEIGHT = 980, 190
MARGIN = 70
NODE_R = 24
CY = 90


def _node_x(i, n):
    if n <= 1:
        return WIDTH / 2
    return MARGIN + i * (WIDTH - 2 * MARGIN) / (n - 1)


def _icon(state):
    if state == "success":
        return '<path d="M-8,0 L-2,7 L9,-8" stroke="white" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    if state in ("failed", "upstream_failed"):
        return '<path d="M-7,-7 L7,7 M7,-7 L-7,7" stroke="white" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
    if state == "running":
        return (
            '<circle r="10" fill="none" stroke="white" stroke-width="3" '
            'stroke-dasharray="40 20" stroke-linecap="round">'
            '<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1s" repeatCount="indefinite"/>'
            "</circle>"
        )
    if state in ("queued", "up_for_retry"):
        return '<circle r="4" fill="white"/>'
    return ""


def _node_svg(i, n, task_id, state):
    x = _node_x(i, n)
    color = COLORS.get(state, COLORS[None])
    pulse = ""
    if state == "running":
        pulse = f"""
        <circle cx="{x}" cy="{CY}" r="{NODE_R}" fill="none" stroke="{color}" stroke-width="2" opacity="0.7">
            <animate attributeName="r" values="{NODE_R};{NODE_R+14}" dur="1.6s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.7;0" dur="1.6s" repeatCount="indefinite"/>
        </circle>"""
    label = LABELS.get(task_id, task_id)
    return f"""
    {pulse}
    <circle cx="{x}" cy="{CY}" r="{NODE_R}" fill="{color}" opacity="{1.0 if state else 0.55}"/>
    <g transform="translate({x},{CY})">{_icon(state)}</g>
    <text x="{x}" y="{CY + NODE_R + 20}" text-anchor="middle" class="node-label">{label}</text>
    """


def _edge_svg(i, n, left_state, right_state):
    x1, x2 = _node_x(i, n), _node_x(i + 1, n)
    if left_state == "success" and right_state == "success":
        return f'<line x1="{x1+NODE_R}" y1="{CY}" x2="{x2-NODE_R}" y2="{CY}" stroke="#22c55e" stroke-width="3"/>'
    if left_state == "success" and right_state in ("running", "queued", "up_for_retry"):
        return (
            f'<line x1="{x1+NODE_R}" y1="{CY}" x2="{x2-NODE_R}" y2="{CY}" '
            'stroke="#3b82f6" stroke-width="3" stroke-dasharray="10 8" class="marching">'
            "</line>"
        )
    return f'<line x1="{x1+NODE_R}" y1="{CY}" x2="{x2-NODE_R}" y2="{CY}" stroke="#334155" stroke-width="2" stroke-dasharray="4 6"/>'


def _traveling_dot(n, task_states):
    completed = [i for i, t in enumerate(TASK_ORDER) if task_states.get(t) == "success"]
    if len(completed) < 2 or completed != list(range(completed[0], completed[-1] + 1)):
        return ""
    x1, x2 = _node_x(completed[0], n), _node_x(completed[-1], n)
    return f"""
    <circle r="5" fill="#86efac">
        <animateMotion dur="2.5s" repeatCount="indefinite"
            path="M{x1},{CY} L{x2},{CY}" />
    </circle>"""


TRIGGER_BADGES = {
    "scheduled": ("⏰ Scheduled by Airflow", "#818cf8"),
    "manual": ("▶ Manually triggered", "#38bdf8"),
    "backfill": ("⏮ Backfill", "#a78bfa"),
    "asset_triggered": ("🔗 Asset-triggered", "#a78bfa"),
}


def render(
    task_states: dict,
    run_state: str | None,
    run_id: str | None,
    run_type: str | None = None,
    triggered_by: str | None = None,
) -> str:
    n = len(TASK_ORDER)
    states = [task_states.get(t) for t in TASK_ORDER]

    nodes_svg = "".join(_node_svg(i, n, t, task_states.get(t)) for i, t in enumerate(TASK_ORDER))
    edges_svg = "".join(_edge_svg(i, n, states[i], states[i + 1]) for i in range(n - 1))
    dot_svg = _traveling_dot(n, task_states)

    status_text = "No pipeline run yet" if run_state is None else f"Latest run: {run_state}"
    status_color = {"success": "#22c55e", "running": "#3b82f6", "failed": "#ef4444"}.get(run_state, "#94a3b8")

    badge_html = ""
    if run_type is not None:
        label, badge_color = TRIGGER_BADGES.get(run_type, (run_type, "#94a3b8"))
        who = f" by {triggered_by}" if run_type == "manual" and triggered_by else ""
        badge_html = f'<span class="badge" style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}55;">{label}{who}</span>'

    return f"""
    <html>
    <head>
    <style>
        body {{ margin: 0; background: transparent; font-family: -apple-system, sans-serif; }}
        .status-row {{ display: flex; align-items: center; gap: 8px; margin: 4px 0 0 8px; }}
        .status {{ color: {status_color}; font-size: 14px; }}
        .badge {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}
        .node-label {{ fill: #cbd5e1; font-size: 11px; }}
        .marching {{ animation: dash 0.6s linear infinite; }}
        @keyframes dash {{ to {{ stroke-dashoffset: -18; }} }}
    </style>
    </head>
    <body>
        <div class="status-row">
            <div class="status">{status_text}{f' ({run_id})' if run_id else ''}</div>
            {badge_html}
        </div>
        <svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
            {edges_svg}
            {dot_svg}
            {nodes_svg}
        </svg>
    </body>
    </html>
    """
