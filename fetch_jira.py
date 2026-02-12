#!/usr/bin/env python3
"""
Fetches VZY bug data from Jira and writes data.json + detailed_data.json for the dashboard & chatbot.
Runs via GitHub Actions on a cron schedule.

Enhanced version: Also generates detailed_data.json with individual bug info for chatbot queries.
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Config from environment variables (GitHub Secrets)
JIRA_DOMAIN = os.environ.get('JIRA_DOMAIN', 'hbeindia.atlassian.net')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL', '')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', '')
PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY', 'VZY')

PLATFORMS = ['ANDROID', 'ATV', 'CMS', 'CMS Adaptor', 'CMS Dashboard', 'DishIT', 'IOS', 'Kaltura', 'LG_TV', 'Mobile', 'SAM_TV', 'WEB']
STATUSES = ['OPEN', 'IN PROGRESS', 'REOPENED', 'IN REVIEW', 'ISSUE ACCEPTED', 'PARKED']

def fetch_jira_data():
    """Fetch bug data from Jira Cloud REST API v3 (new /search/jql endpoint with cursor pagination)."""
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    jql = f'project = {PROJECT_KEY} ORDER BY updated DESC'
    url = f'https://{JIRA_DOMAIN}/rest/api/3/search/jql'

    all_issues = []
    next_page_token = None

    while True:
        payload = {
            'jql': jql,
            'maxResults': 100,
            'fields': ['*all']
        }
        if next_page_token:
            payload['nextPageToken'] = next_page_token

        response = requests.post(url, headers=headers, auth=auth, json=payload)
        response.raise_for_status()
        data = response.json()

        issues = data.get('issues', [])
        all_issues.extend(issues)

        total = data.get('total', len(all_issues))
        print(f"Fetched {len(all_issues)} of {total} issues...")

        next_page_token = data.get('nextPageToken')
        if not next_page_token or len(issues) == 0:
            break

    print(f"Total issues fetched: {len(all_issues)}")
    return all_issues


def detect_platform(issue):
    """Detect platform from summary, labels, components, and custom fields."""
    fields = issue.get('fields', {})
    labels = [l.upper() for l in fields.get('labels', [])]
    components = [c.get('name', '').upper() for c in fields.get('components', [])]
    summary = (fields.get('summary') or '').upper()

    custom_vals = []
    for key, val in fields.items():
        if key.startswith('customfield_') and val:
            if isinstance(val, str):
                custom_vals.append(val.upper())
            elif isinstance(val, dict):
                custom_vals.append((val.get('value', '') or val.get('name', '')).upper())
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        custom_vals.append(item.upper())
                    elif isinstance(item, dict):
                        custom_vals.append((item.get('value', '') or item.get('name', '')).upper())

    all_text = ' '.join(labels + components + custom_vals + [summary])

    platform_patterns = {
        'CMS Adaptor': ['CMS ADAPTOR', 'CMS_ADAPTOR', 'CMSADAPTOR'],
        'CMS Dashboard': ['CMS DASHBOARD', 'CMS_DASHBOARD', 'CMSDASHBOARD'],
        'Kaltura': ['KALTURA'],
        'DishIT': ['DISHIT', 'DISH IT', 'DISH_IT'],
        'LG_TV': ['LG_TV', 'LGTV', 'LG TV', 'WEBOS', 'LG-TV'],
        'SAM_TV': ['SAM_TV', 'SAMTV', 'SAM TV', 'SAMSUNG TV', 'SAMSUNG_TV', 'TIZEN', 'SAM-TV'],
        'ATV': ['ATV', 'ANDROID TV', 'ANDROID_TV', 'ANDROIDTV', 'FIRE TV', 'FIRETV', 'FIRE_TV'],
        'Mobile': ['MOBILE'],
        'ANDROID': ['ANDROID'],
        'IOS': ['IOS', 'APPLE', 'IPHONE', 'IPAD'],
        'WEB': ['WEB'],
        'CMS': ['CMS'],
    }

    for platform, patterns in platform_patterns.items():
        for pattern in patterns:
            if pattern in all_text:
                return platform

    return None


def build_dashboard_data(issues):
    """Build the platform x status matrix (dynamically includes all detected platforms)."""
    # Start with known platforms, then add any new ones found dynamically
    matrix = {}
    for p in PLATFORMS:
        matrix[p] = {s: 0 for s in STATUSES}

    total_bugs = 0
    matched_counted = 0
    unmatched_platforms = 0
    unmatched_status = 0
    bug_status_breakdown = {}

    for issue in issues:
        fields = issue.get('fields', {})
        status_name = fields.get('status', {}).get('name', '')
        issue_type = fields.get('issuetype', {}).get('name', '')

        platform = detect_platform(issue)
        status_upper = status_name.upper()

        if issue_type.upper() == 'BUG':
            total_bugs += 1
            bug_status_breakdown[status_name] = bug_status_breakdown.get(status_name, 0) + 1

            if status_upper in STATUSES:
                actual_platform = platform if platform else 'Unknown'
                if actual_platform not in matrix:
                    matrix[actual_platform] = {s: 0 for s in STATUSES}
                matrix[actual_platform][status_upper] += 1
                matched_counted += 1
            elif platform and status_upper not in STATUSES:
                unmatched_status += 1
            elif not platform:
                unmatched_platforms += 1

    print(f"\n=== FETCH SUMMARY ===")
    print(f"Total issues: {len(issues)}")
    print(f"Total bugs: {total_bugs}")
    print(f"Matched & counted: {matched_counted}")
    print(f"Platform matched but status not tracked: {unmatched_status}")
    print(f"Platform unmatched: {unmatched_platforms}")
    print(f"Bug statuses: {bug_status_breakdown}")
    print(f"=====================\n")

    return matrix


def build_detailed_data(issues):
    """Build detailed issue list for chatbot queries (bugs + tasks + stories)."""
    detailed = {
        'bugs': [],
        'tasks': [],
        'subtasks': [],
        'stories': [],
        'sprints': {},
        'releases': {},
        'assignee_workload': {},
        'priority_breakdown': {},
    }

    for issue in issues:
        fields = issue.get('fields', {})
        issue_type = fields.get('issuetype', {}).get('name', '')
        status_name = fields.get('status', {}).get('name', '')
        summary = fields.get('summary', '')
        key = issue.get('key', '')
        priority = fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None'
        assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
        created = fields.get('created', '')
        updated = fields.get('updated', '')
        duedate = fields.get('duedate', '')
        fix_versions = fields.get('fixVersions', []) or []
        fix_version_names = [v.get('name', '') for v in fix_versions if v.get('name')]
        platform = detect_platform(issue)

        # Extract sprint info
        sprint_name = None
        for fkey, val in fields.items():
            if fkey.startswith('customfield_') and val:
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and 'name' in item and 'state' in item:
                            sprint_name = item.get('name')
                elif isinstance(val, dict) and 'name' in val and 'state' in val:
                    sprint_name = val.get('name')

        item = {
            'key': key,
            'summary': summary,
            'status': status_name,
            'priority': priority,
            'assignee': assignee,
            'platform': platform or 'Unknown',
            'created': created[:10] if created else '',
            'updated': updated[:10] if updated else '',
            'duedate': duedate[:10] if duedate else '',
            'sprint': sprint_name or 'No Sprint',
            'type': issue_type,
            'fixversion': ', '.join(fix_version_names) if fix_version_names else '',
        }

        type_upper = issue_type.upper()
        if type_upper == 'BUG':
            detailed['bugs'].append(item)
        elif type_upper == 'TASK':
            detailed['tasks'].append(item)
        elif type_upper == 'SUB-TASK':
            detailed['subtasks'].append(item)
        elif type_upper == 'STORY':
            detailed['stories'].append(item)

        # Assignee workload
        if assignee not in detailed['assignee_workload']:
            detailed['assignee_workload'][assignee] = {'bugs': 0, 'tasks': 0, 'subtasks': 0, 'stories': 0, 'total': 0}
        if type_upper == 'BUG':
            detailed['assignee_workload'][assignee]['bugs'] += 1
        elif type_upper == 'TASK':
            detailed['assignee_workload'][assignee]['tasks'] += 1
        elif type_upper == 'SUB-TASK':
            detailed['assignee_workload'][assignee]['subtasks'] += 1
        elif type_upper == 'STORY':
            detailed['assignee_workload'][assignee]['stories'] += 1
        detailed['assignee_workload'][assignee]['total'] += 1

        # Priority breakdown
        if type_upper == 'BUG':
            if priority not in detailed['priority_breakdown']:
                detailed['priority_breakdown'][priority] = 0
            detailed['priority_breakdown'][priority] += 1

        # Sprint tracking
        if sprint_name:
            if sprint_name not in detailed['sprints']:
                detailed['sprints'][sprint_name] = {'bugs': 0, 'tasks': 0, 'subtasks': 0, 'stories': 0, 'total': 0, 'statuses': {}}
            if type_upper == 'BUG':
                detailed['sprints'][sprint_name]['bugs'] += 1
            elif type_upper == 'TASK':
                detailed['sprints'][sprint_name]['tasks'] += 1
            elif type_upper == 'SUB-TASK':
                detailed['sprints'][sprint_name]['subtasks'] += 1
            elif type_upper == 'STORY':
                detailed['sprints'][sprint_name]['stories'] += 1
            detailed['sprints'][sprint_name]['total'] += 1
            detailed['sprints'][sprint_name]['statuses'][status_name] = \
                detailed['sprints'][sprint_name]['statuses'].get(status_name, 0) + 1

        # Release / fixVersion tracking
        for fv in fix_versions:
            vname = fv.get('name', '')
            if not vname:
                continue
            if vname not in detailed['releases']:
                detailed['releases'][vname] = {
                    'released': fv.get('released', False),
                    'releaseDate': fv.get('releaseDate', ''),
                    'description': fv.get('description', ''),
                    'bugs': 0, 'tasks': 0, 'subtasks': 0, 'stories': 0, 'total': 0,
                    'statuses': {},
                    'issues': []
                }
            rel = detailed['releases'][vname]
            if type_upper == 'BUG':
                rel['bugs'] += 1
            elif type_upper == 'TASK':
                rel['tasks'] += 1
            elif type_upper == 'SUB-TASK':
                rel['subtasks'] += 1
            elif type_upper == 'STORY':
                rel['stories'] += 1
            rel['total'] += 1
            rel['statuses'][status_name] = rel['statuses'].get(status_name, 0) + 1
            rel['issues'].append({
                'key': key, 'summary': summary, 'status': status_name,
                'type': issue_type, 'priority': priority, 'assignee': assignee,
                'platform': platform or 'Unknown'
            })

    return detailed


def main():
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN environment variables required.")
        print("Set these as GitHub Secrets.")
        exit(1)

    print(f"Fetching data from {JIRA_DOMAIN} for project {PROJECT_KEY}...")
    issues = fetch_jira_data()
    matrix = build_dashboard_data(issues)

    # Standard dashboard data
    output = {
        'data': matrix,
        'updated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_issues_fetched': len(issues),
        'project': PROJECT_KEY
    }

    base_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = os.path.join(base_dir, 'data.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Written to {output_path}")

    # Detailed data for chatbot
    detailed = build_detailed_data(issues)
    detailed['updated_at'] = output['updated_at']
    detailed['total_issues'] = len(issues)

    detailed_path = os.path.join(base_dir, 'detailed_data.json')
    with open(detailed_path, 'w') as f:
        json.dump(detailed, f, indent=2)
    print(f"Written detailed data to {detailed_path}")

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
