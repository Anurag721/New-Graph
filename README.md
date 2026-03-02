# Middle East Conflict Dashboard (2023–2026)

An interactive web dashboard that visualizes the Middle East conflict timeline with live news updates.

Built with **Dash + Plotly** and styled with a dark Bootstrap theme.

## Features

- **Interactive Timeline** — Major conflict events plotted as a Gantt chart with hover details
- **Conflict Intensity Chart** — Monthly intensity area chart showing escalation patterns
- **Key Parties** — Horizontal bar chart of countries/groups by involvement
- **Live News Feed** — Auto-refreshing headlines from BBC, Al Jazeera, and Google News RSS
- **Auto-updates every 15 minutes** — no page reload needed

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python app.py
```

Then open **http://localhost:8050** in your browser.

## Data Sources

- Pre-loaded timeline of ~18 major events (Oct 2023 – Mar 2026)
- Live news from free RSS feeds (no API keys required):
  - BBC Middle East
  - Al Jazeera
  - Google News (multiple conflict-focused queries)

## Tech Stack

- [Dash](https://dash.plotly.com/) — Python web framework
- [Plotly](https://plotly.com/python/) — Interactive charts
- [dash-bootstrap-components](https://dash-bootstrap-components.opensource.faculty.ai/) — UI layout & dark theme
- [feedparser](https://github.com/kurtmckee/feedparser) — RSS feed parsing
- [pandas](https://pandas.pydata.org/) — Data manipulation
