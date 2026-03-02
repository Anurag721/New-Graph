"""
Middle East Conflict Dashboard (2023-2026)
==========================================
Interactive Dash + Plotly web dashboard showing a timeline of major events,
conflict intensity, key parties involved, and a live news feed that
auto-refreshes every 15 minutes from RSS sources.

Run:
    pip install -r requirements.txt
    python app.py

Then open http://localhost:8050 in your browser.
"""

import json
import datetime
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape
from pathlib import Path

import dash
from dash import dcc, html, Output, Input
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests


# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
app.title = "Middle East Conflict Dashboard (2023–2026)"
server = app.server

# Load the Plotly figure template matching the Bootstrap dark theme
load_figure_template("darkly")

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# RSS feed configuration
# ---------------------------------------------------------------------------

RSS_FEEDS = {
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Google News — Middle East": (
        "https://news.google.com/rss/search?"
        "q=Middle+East+conflict+OR+Gaza+OR+Israel+Iran&hl=en-US&gl=US&ceid=US:en"
    ),
    "Google News — Gaza": (
        "https://news.google.com/rss/search?"
        "q=Gaza+war+ceasefire&hl=en-US&gl=US&ceid=US:en"
    ),
    "Google News — Iran Israel": (
        "https://news.google.com/rss/search?"
        "q=Iran+Israel+strikes+war&hl=en-US&gl=US&ceid=US:en"
    ),
}

CONFLICT_KEYWORDS = [
    "gaza", "israel", "hamas", "hezbollah", "iran", "yemen", "houthi",
    "ceasefire", "hostage", "airstrike", "idf", "netanyahu", "tehran",
    "west bank", "palestinian", "beirut", "missile", "drone strike",
    "middle east", "conflict", "war crime", "military operation",
    "epic fury", "khamenei", "nasrallah", "syria", "lebanon",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_timeline_events() -> pd.DataFrame:
    """Load pre-built historical events from the JSON data file."""
    with open(DATA_DIR / "timeline_events.json", "r", encoding="utf-8") as f:
        events = json.load(f)
    df = pd.DataFrame(events)
    df["date"] = pd.to_datetime(df["date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    # Make single-day events visible on the timeline
    mask = df["date"] == df["end_date"]
    df.loc[mask, "end_date"] += pd.Timedelta(days=5)
    return df


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML into a list of entry dicts."""
    entries: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return entries
    # Standard RSS 2.0: channel/item
    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "#")
        desc = item.findtext("description", "")
        pub_date = item.findtext("pubDate", "")
        entries.append({
            "title": unescape(title),
            "link": link.strip(),
            "description": unescape(desc),
            "published": pub_date,
        })
    return entries


def fetch_news() -> list[dict]:
    """Fetch recent conflict news from multiple RSS feeds."""
    articles: list[dict] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ConflictDashboard/1.0; "
            "+https://github.com)"
        )
    }
    for source_name, url in RSS_FEEDS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            entries = _parse_rss(resp.text)
            for entry in entries[:20]:
                title = entry["title"]
                desc = entry["description"]
                combined = (title + " " + desc).lower()
                if any(kw in combined for kw in CONFLICT_KEYWORDS):
                    articles.append({
                        "source": source_name,
                        "title": title,
                        "link": entry["link"],
                        "published": entry["published"],
                        "summary": (
                            desc[:200] + "…" if len(desc) > 200 else desc
                        ),
                    })
        except Exception:
            continue  # Skip failing feeds silently
    # Deduplicate by exact title
    seen: set[str] = set()
    unique: list[dict] = []
    for article in articles:
        if article["title"] not in seen:
            seen.add(article["title"])
            unique.append(article)
    return unique[:30]


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

CATEGORY_COLORS = {
    "Escalation": "#e74c3c",
    "Military Operation": "#e67e22",
    "Ceasefire": "#2ecc71",
    "Diplomatic": "#3498db",
}


def build_timeline(df: pd.DataFrame) -> go.Figure:
    """Interactive Gantt-style timeline of major conflict events."""
    fig = px.timeline(
        df,
        x_start="date",
        x_end="end_date",
        y="title",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        hover_data=["description", "region", "intensity"],
        title="Conflict Timeline: Major Events (Oct 2023 – Mar 2026)",
    )
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_layout(
        height=max(450, len(df) * 32),
        template="darkly",
        legend_title_text="Event Type",
        xaxis_title="Date",
        hoverlabel=dict(bgcolor="rgba(0,0,0,0.85)", font_size=13),
        margin=dict(l=10, r=10, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_intensity_chart(df: pd.DataFrame) -> go.Figure:
    """Monthly conflict-intensity area chart."""
    df_sorted = df.sort_values("date")
    date_range = pd.date_range(start="2023-10-01", end="2026-03-31", freq="MS")
    monthly: list[dict] = []
    for month_start in date_range:
        month_end = month_start + pd.offsets.MonthEnd(1)
        active = df_sorted[
            (df_sorted["date"] <= month_end) & (df_sorted["end_date"] >= month_start)
        ]
        max_intensity = int(active["intensity"].max()) if len(active) > 0 else 0
        monthly.append({"month": month_start, "intensity": max_intensity})
    intensity_df = pd.DataFrame(monthly)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=intensity_df["month"],
        y=intensity_df["intensity"],
        fill="tozeroy",
        mode="lines+markers",
        line=dict(color="#e74c3c", width=2.5),
        fillcolor="rgba(231, 76, 60, 0.25)",
        marker=dict(size=6),
        hovertemplate="<b>%{x|%B %Y}</b><br>Intensity: %{y}/10<extra></extra>",
    ))
    fig.update_layout(
        title="Conflict Intensity Over Time",
        yaxis_title="Intensity (1–10)",
        xaxis_title="",
        template="darkly",
        height=350,
        yaxis=dict(range=[0, 11]),
        margin=dict(l=10, r=10, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_parties_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of key parties by involvement count."""
    counter: Counter[str] = Counter()
    for parties in df["parties"]:
        for party in parties:
            counter[party] += 1
    parties_df = pd.DataFrame(
        counter.most_common(), columns=["Party", "Involvement"]
    )
    fig = px.bar(
        parties_df,
        x="Involvement",
        y="Party",
        orientation="h",
        color="Involvement",
        color_continuous_scale="RdYlGn_r",
        title="Key Parties by Event Involvement",
    )
    fig.update_layout(
        template="darkly",
        height=350,
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app.layout = dbc.Container(
    [
        # Hidden interval component — fires every 15 minutes (900 000 ms)
        dcc.Interval(id="interval-component", interval=900_000, n_intervals=0),

        # ── Header ──────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                [
                    html.H1(
                        "Middle East Conflict Dashboard",
                        className="dashboard-title text-center mt-4 mb-1",
                    ),
                    html.P(
                        "Interactive timeline & live news tracker  •  2023 – 2026",
                        className="dashboard-subtitle text-center mb-4",
                    ),
                ],
                width=12,
            )
        ),

        # ── Row 1: Timeline (full width) ───────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Graph(
                            id="timeline-chart",
                            config={"displayModeBar": True, "scrollZoom": True},
                        )
                    ),
                ),
                width=12,
                className="mb-4",
            )
        ),

        # ── Row 2: Intensity (left) + Parties (right) ─────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(dbc.CardBody(dcc.Graph(id="intensity-chart"))),
                    lg=7,
                    md=12,
                    className="mb-4",
                ),
                dbc.Col(
                    dbc.Card(dbc.CardBody(dcc.Graph(id="parties-chart"))),
                    lg=5,
                    md=12,
                    className="mb-4",
                ),
            ]
        ),

        # ── Row 3: Live News Feed ──────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            [
                                html.H4(
                                    [
                                        "Live News Feed  ",
                                        dbc.Badge(
                                            "AUTO-UPDATING",
                                            color="success",
                                            className="badge-pulse ms-2 align-middle",
                                        ),
                                    ],
                                    className="d-inline mb-0",
                                ),
                                html.Small(
                                    id="last-updated",
                                    className="float-end text-muted mt-1",
                                ),
                            ]
                        ),
                        dbc.CardBody(
                            id="news-feed-container",
                            className="news-scroll",
                            style={"maxHeight": "520px", "overflowY": "auto"},
                        ),
                    ]
                ),
                width=12,
                className="mb-4",
            )
        ),

        # ── Footer ─────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                [
                    html.Hr(style={"borderColor": "rgba(255,255,255,0.1)"}),
                    html.P(
                        [
                            "Data: BBC, Al Jazeera, Google News RSS  •  "
                            "Auto-refreshes every 15 min  •  ",
                            html.Span(id="footer-timestamp"),
                        ],
                        className="footer-text text-center",
                    ),
                ],
                width=12,
            )
        ),
    ],
    fluid=True,
    className="px-4",
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("timeline-chart", "figure"),
    Output("intensity-chart", "figure"),
    Output("parties-chart", "figure"),
    Input("interval-component", "n_intervals"),
)
def update_charts(_n_intervals):
    """Rebuild charts on page load and every 15-min interval."""
    df = load_timeline_events()
    return build_timeline(df), build_intensity_chart(df), build_parties_chart(df)


@app.callback(
    Output("news-feed-container", "children"),
    Output("last-updated", "children"),
    Output("footer-timestamp", "children"),
    Input("interval-component", "n_intervals"),
)
def update_news_feed(_n_intervals):
    """Fetch fresh news from RSS feeds on page load and every 15-min interval."""
    articles = fetch_news()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not articles:
        news_content = dbc.Alert(
            "No recent conflict-related news found. Will retry in 15 minutes.",
            color="warning",
            className="mb-0",
        )
    else:
        news_items = []
        for article in articles:
            news_items.append(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6(
                                html.A(
                                    article["title"],
                                    href=article["link"],
                                    target="_blank",
                                    className="news-link",
                                ),
                                className="mb-1",
                            ),
                            html.Div(
                                [
                                    dbc.Badge(
                                        article["source"],
                                        color="info",
                                        className="me-2",
                                    ),
                                    html.Small(
                                        article["published"],
                                        className="text-muted",
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.P(
                                article["summary"],
                                className="mb-0 small text-muted",
                            ),
                        ]
                    ),
                    className="news-card mb-2",
                )
            )
        news_content = html.Div(news_items)

    return (
        news_content,
        f"Last updated: {now}",
        f"Built with Dash + Plotly  •  Last refresh: {now}",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Middle East Conflict Dashboard...")
    print("Open http://localhost:8050 in your browser.")
    app.run(debug=True, host="0.0.0.0", port=8050)
