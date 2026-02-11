# VF Bug Health - Dashboard & Chatbot

## Project: Webpage display Jira dashboard with chatbot

Enhanced version of the VF Bug Health Dashboard with an interactive chatbot and insights panel.

## What's New (vs Master Code)

| Feature | Master | This Project |
|---------|--------|-------------|
| Bug Dashboard | Yes | Yes |
| Interactive Chatbot | No | Yes |
| Insights Tab | No | Yes |
| Detailed Data (detailed_data.json) | No | Yes |
| Sprint/Task/Story tracking | No | Yes |
| Assignee workload data | No | Yes |

## Architecture

```
index.html              → Single-page app with 3 tabs (Dashboard, Chatbot, Insights)
fetch_jira.py           → Enhanced fetcher: generates data.json + detailed_data.json
data.json               → Bug matrix (same as Master)
detailed_data.json      → Individual bugs, tasks, stories, sprints, assignees
.github/workflows/      → GitHub Actions (hourly fetch + deploy)
```

## Tabs

### 1. Dashboard
Same as Master code - summary cards, status distribution, platform bar chart, platform x status table.

### 2. Chatbot
Interactive Q&A interface. Users can ask:
- **Bug summary** - Total overview
- **Platform bugs** - e.g. "Android bugs", "WEB bugs"
- **Status queries** - e.g. "open bugs", "in progress", "parked"
- **Compare platforms** - Full comparison table
- **Critical platforms** - Platforms with 4+ bugs
- **Healthy platforms** - Platforms with 0-1 bugs
- **Reopened bugs** - Reopen analysis
- **Top platform** - Platform ranking

Quick action buttons provided for common queries.

### 3. Insights
Auto-generated insights including:
- Alert banners for critical platforms and high reopen rates
- Bug overview (active, in review, parked)
- Platform ranking
- Status hotspots
- Healthy platforms

## Setup

Same as Master code. Copy GitHub Secrets:
- `JIRA_DOMAIN` → hbeindia.atlassian.net
- `JIRA_EMAIL` → Service account email
- `JIRA_API_TOKEN` → Jira API token
- `JIRA_PROJECT_KEY` → VZY

## Local Testing

```bash
python -m http.server 8080 --directory .
```

## Merge Plan

Once this project is tested and approved:
1. Copy `index.html` → Master code
2. Copy `fetch_jira.py` → Master code
3. Update GitHub Actions in Master
4. Deploy
