#!/usr/bin/env python3
"""
KPI & Performance Matrix Collector for VZY Apps and Web/mWeb

This module collects performance KPI data from two sources:
  1. Firebase (App Performance) - DAU, crash rate, ANR rate, ratings for all apps
  2. Chrome UX Report / Lighthouse API (Web Performance) - Core Web Vitals for www.VZY.one

Output: kpi_data.json consumed by send_daily_report.py for email reports

Currently supports MANUAL data entry via kpi_data.json.
Once Firebase credentials are provided, this will auto-fetch from Firebase.
Web performance metrics will be fetched via Chrome CrUX API for www.VZY.one.

Required environment variables (when auto-fetch is enabled):
  FIREBASE_PROJECT_ID - Firebase project ID
  FIREBASE_CREDENTIALS_JSON - Firebase service account JSON (base64 encoded)
  CRUX_API_KEY - Chrome UX Report API key (optional, for web performance)
"""

import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KPI_DATA_PATH = os.path.join(BASE_DIR, 'kpi_data.json')

# ── Firebase Config ──
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', '')
FIREBASE_CREDENTIALS_JSON = os.environ.get('FIREBASE_CREDENTIALS_JSON', '')

# ── CrUX API Config ──
CRUX_API_KEY = os.environ.get('CRUX_API_KEY', '')
WEB_ORIGIN = 'https://www.vzy.one'

# ── App identifiers (Firebase) ──
APP_CONFIG = {
    'VZY Android': {
        'package': 'com.vzy.android',  # Update with actual package name
        'platform': 'ANDROID',
    },
    'VZY iOS': {
        'bundle_id': 'com.vzy.ios',  # Update with actual bundle ID
        'platform': 'IOS',
    },
    'VZY Android TV': {
        'package': 'com.vzy.atv',  # Update with actual package name
        'platform': 'ATV',
    },
    'VZY Fire TV': {
        'package': 'com.vzy.firetv',  # Update with actual package name
        'platform': 'ATV',
    },
    'VZY Samsung TV': {
        'app_id': 'vzy-samsung-tv',  # Update with actual Tizen app ID
        'platform': 'SAM_TV',
    },
    'VZY LG TV': {
        'app_id': 'vzy-lg-tv',  # Update with actual webOS app ID
        'platform': 'LG_TV',
    },
}


def fetch_firebase_app_metrics():
    """
    Fetch app performance metrics from Firebase.

    When Firebase credentials are provided, this function will use the
    Firebase Admin SDK to pull:
    - Daily Active Users (DAU)
    - Crash-free rate / Crash rate
    - ANR rate (Android only)
    - App store rating

    Returns dict keyed by app name with metrics.
    """
    if not FIREBASE_PROJECT_ID or not FIREBASE_CREDENTIALS_JSON:
        print("Firebase credentials not configured. Skipping app metrics fetch.")
        print("To enable: Set FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_JSON env vars.")
        return None

    # TODO: Implement Firebase data fetch when credentials are provided
    # The implementation will use:
    #   - firebase_admin SDK for Crashlytics data
    #   - Google Analytics Data API for DAU
    #   - Google Play Developer API / App Store Connect API for ratings
    #
    # Example implementation (uncomment when ready):
    # import firebase_admin
    # from firebase_admin import credentials, firestore
    # import base64
    #
    # cred_json = json.loads(base64.b64decode(FIREBASE_CREDENTIALS_JSON))
    # cred = credentials.Certificate(cred_json)
    # firebase_admin.initialize_app(cred, {'projectId': FIREBASE_PROJECT_ID})
    #
    # # Fetch Crashlytics data
    # # Fetch Analytics data
    # # Return structured metrics

    print("Firebase auto-fetch: Will be implemented once credentials are provided.")
    return None


def fetch_web_performance():
    """
    Fetch web performance metrics for www.VZY.one using Chrome UX Report API.

    Collects Core Web Vitals:
    - LCP (Largest Contentful Paint)
    - FID (First Input Delay) / INP (Interaction to Next Paint)
    - CLS (Cumulative Layout Shift)
    - TTFB (Time to First Byte)
    - Page Load Time

    Returns dict with web/mWeb performance data.
    """
    if not CRUX_API_KEY:
        print("CrUX API key not configured. Skipping web performance fetch.")
        print("To enable: Set CRUX_API_KEY env var (get key from Google Cloud Console).")
        return None

    try:
        import requests

        url = f'https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={CRUX_API_KEY}'

        # Fetch desktop metrics
        desktop_payload = {
            'origin': WEB_ORIGIN,
            'formFactor': 'DESKTOP',
        }
        desktop_resp = requests.post(url, json=desktop_payload)

        # Fetch mobile metrics (mWeb)
        mobile_payload = {
            'origin': WEB_ORIGIN,
            'formFactor': 'PHONE',
        }
        mobile_resp = requests.post(url, json=mobile_payload)

        web_data = {}

        if desktop_resp.status_code == 200:
            record = desktop_resp.json().get('record', {}).get('metrics', {})
            web_data['VZY Web (Desktop)'] = {
                'lcp': _extract_p75(record.get('largest_contentful_paint', {})),
                'fid': _extract_p75(record.get('first_input_delay', {})),
                'cls': _extract_p75(record.get('cumulative_layout_shift', {})),
                'inp': _extract_p75(record.get('interaction_to_next_paint', {})),
                'ttfb': _extract_p75(record.get('experimental_time_to_first_byte', {})),
                'page_load': 'N/A',
            }

        if mobile_resp.status_code == 200:
            record = mobile_resp.json().get('record', {}).get('metrics', {})
            web_data['VZY mWeb (Mobile)'] = {
                'lcp': _extract_p75(record.get('largest_contentful_paint', {})),
                'fid': _extract_p75(record.get('first_input_delay', {})),
                'cls': _extract_p75(record.get('cumulative_layout_shift', {})),
                'inp': _extract_p75(record.get('interaction_to_next_paint', {})),
                'ttfb': _extract_p75(record.get('experimental_time_to_first_byte', {})),
                'page_load': 'N/A',
            }

        return web_data if web_data else None

    except Exception as e:
        print(f"Error fetching CrUX data: {e}")
        return None


def _extract_p75(metric_data):
    """Extract p75 value from CrUX metric data."""
    percentiles = metric_data.get('percentiles', {})
    p75 = percentiles.get('p75')
    if p75 is not None:
        # Format based on metric type
        if isinstance(p75, float) and p75 < 1:
            return f"{p75:.3f}"  # CLS
        elif isinstance(p75, (int, float)):
            if p75 > 1000:
                return f"{p75/1000:.1f}s"  # Convert ms to seconds
            return f"{int(p75)}ms"
    return 'N/A'


def load_manual_data():
    """Load manually entered KPI data from kpi_data.json if it exists."""
    if os.path.exists(KPI_DATA_PATH):
        with open(KPI_DATA_PATH, 'r') as f:
            return json.load(f)
    return None


def create_template():
    """Create a template kpi_data.json for manual data entry."""
    template = {
        '_comment': 'Fill in KPI data manually. This will be included in daily email reports. Once Firebase credentials are configured, app data will be auto-fetched.',
        'updated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'apps': {
            'VZY Android': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': '',
                'rating': '',
                'version': '',
            },
            'VZY iOS': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': 'N/A',
                'rating': '',
                'version': '',
            },
            'VZY Android TV': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': '',
                'rating': '',
                'version': '',
            },
            'VZY Fire TV': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': '',
                'rating': '',
                'version': '',
            },
            'VZY Samsung TV (Tizen)': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': 'N/A',
                'rating': '',
                'version': '',
            },
            'VZY LG TV (webOS)': {
                'dau': '',
                'crash_rate': '',
                'anr_rate': 'N/A',
                'rating': '',
                'version': '',
            },
        },
        'web': {
            'VZY Web (Desktop)': {
                'lcp': '',
                'fid': '',
                'cls': '',
                'page_load': '',
                'bounce_rate': '',
            },
            'VZY mWeb (Mobile)': {
                'lcp': '',
                'fid': '',
                'cls': '',
                'page_load': '',
                'bounce_rate': '',
            },
        },
    }
    return template


def main():
    print("=== VZY KPI Collector ===")

    # Try auto-fetch from Firebase
    app_metrics = fetch_firebase_app_metrics()

    # Try auto-fetch web performance
    web_metrics = fetch_web_performance()

    # Load existing manual data
    existing_data = load_manual_data()

    if app_metrics or web_metrics:
        # Merge auto-fetched data with existing
        kpi_data = existing_data or create_template()
        kpi_data['updated_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        if app_metrics:
            kpi_data['apps'] = app_metrics
            print("App metrics updated from Firebase.")

        if web_metrics:
            kpi_data['web'] = web_metrics
            print("Web metrics updated from CrUX API.")

        with open(KPI_DATA_PATH, 'w') as f:
            json.dump(kpi_data, f, indent=2)
        print(f"KPI data saved to {KPI_DATA_PATH}")

    elif existing_data:
        print("Using existing manual KPI data.")
        print(f"  Last updated: {existing_data.get('updated_at', 'unknown')}")
        apps = existing_data.get('apps', {})
        web = existing_data.get('web', {})
        print(f"  Apps tracked: {len(apps)} ({', '.join(apps.keys())})")
        print(f"  Web properties: {len(web)} ({', '.join(web.keys())})")

    else:
        print("No KPI data available. Creating template for manual entry...")
        template = create_template()
        with open(KPI_DATA_PATH, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"Template created at {KPI_DATA_PATH}")
        print("Please fill in the KPI data manually, or configure Firebase/CrUX credentials for auto-fetch.")


if __name__ == '__main__':
    main()
