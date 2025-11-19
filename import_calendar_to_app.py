#!/usr/bin/env python3
"""
Import calendar from emailpilot-simple output to emailpilot-app Firestore.

This script:
1. Loads the calendar_app.json from emailpilot-simple outputs
2. Transforms the data to match emailpilot-app's BulkEventsCreate schema
3. POSTs to the /api/calendar/create-bulk-events endpoint
"""

import json
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List


# Color mapping for event types
EVENT_TYPE_COLORS = {
    "promotional": "bg-red-100 text-red-800",
    "engagement": "bg-blue-100 text-blue-800",
    "content": "bg-green-100 text-green-800",
    "special": "bg-purple-100 text-purple-800",
    "default": "bg-gray-200 text-gray-800"
}


def load_calendar_file(file_path: str) -> Dict:
    """Load the calendar JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def load_strategy_summary(calendar_file_path: str) -> Dict | None:
    """Load the strategy summary JSON file if it exists.

    Derives the strategy_summary filename from the calendar_app.json filename
    by replacing '_calendar_app.json' with '_strategy_summary.json'.

    Returns None if the file doesn't exist (e.g., older workflows).
    """
    strategy_file_path = calendar_file_path.replace('_calendar_app.json', '_strategy_summary.json')

    try:
        with open(strategy_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠ Strategy summary not found: {strategy_file_path}")
        print("  (This is normal for workflows run before strategy_summary feature)")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠ Error parsing strategy summary JSON: {e}")
        return None


def transform_event(event: Dict, client_id: str) -> Dict:
    """Transform an event from emailpilot-simple format to emailpilot-app format."""
    event_type = event.get('type', 'default')

    return {
        "client_id": client_id,
        "title": event.get('title', ''),
        "content": event.get('description', ''),
        "event_date": event.get('date'),
        "event_type": event_type,
        "send_time": event.get('send_time'),
        "color": EVENT_TYPE_COLORS.get(event_type, EVENT_TYPE_COLORS['default']),
        # Optional fields
        "segment": event.get('segment'),
        "subject_a": event.get('subject_a'),
        "subject_b": event.get('subject_b'),
        "preview_text": event.get('preview_text'),
        "main_cta": event.get('main_cta'),
        "offer": event.get('offer'),
        "ab_test": event.get('ab_test')
    }


def create_bulk_request(calendar_data: Dict, strategy_summary: Dict | None = None) -> Dict:
    """Create the BulkEventsCreate request payload.

    Args:
        calendar_data: Calendar data from emailpilot-simple
        strategy_summary: Optional strategy summary from Claude Sonnet 4.5

    Returns:
        BulkEventsCreate payload for emailpilot-app API
    """
    client_id = calendar_data.get('client_id')
    events = calendar_data.get('events', [])

    transformed_events = [
        transform_event(event, client_id)
        for event in events
    ]

    payload = {
        "client_id": client_id,
        "events": transformed_events
    }

    # Include strategy_summary if available
    if strategy_summary:
        payload["strategy_summary"] = strategy_summary

    return payload


def import_to_app(api_url: str, bulk_request: Dict) -> Dict:
    """Send the bulk import request to emailpilot-app API."""
    endpoint = f"{api_url}/api/calendar/create-bulk-events"

    print(f"Importing {len(bulk_request['events'])} events to {endpoint}...")
    print(f"Client: {bulk_request['client_id']}")

    response = requests.post(endpoint, json=bulk_request)
    response.raise_for_status()

    return response.json()


def main():
    # Configuration
    CALENDAR_FILE = "/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/outputs/rogue-creamery_2026-01-01_2026-01-31_20251118_194816_calendar_app.json"
    API_URL = "http://localhost:8008"

    # Allow override from command line
    if len(sys.argv) > 1:
        CALENDAR_FILE = sys.argv[1]
    if len(sys.argv) > 2:
        API_URL = sys.argv[2]

    print("=" * 60)
    print("Calendar Import to EmailPilot App")
    print("=" * 60)
    print(f"Source file: {CALENDAR_FILE}")
    print(f"Target API: {API_URL}")
    print()

    # Load calendar data
    print("Loading calendar data...")
    calendar_data = load_calendar_file(CALENDAR_FILE)
    print(f"✓ Loaded {len(calendar_data.get('events', []))} events")
    print(f"✓ Client: {calendar_data.get('client_id')}")
    print()

    # Load strategy summary
    print("Loading strategy summary...")
    strategy_summary = load_strategy_summary(CALENDAR_FILE)
    if strategy_summary:
        insights_count = len(strategy_summary.get('key_insights', []))
        print(f"✓ Loaded Strategy Summary with {insights_count} insights")
        print(f"  • {strategy_summary.get('targeting_approach', 'N/A')[:60]}...")
    else:
        print("  (No strategy summary found - normal for older workflows)")
    print()

    # Transform to bulk request
    print("Transforming data...")
    bulk_request = create_bulk_request(calendar_data, strategy_summary)
    print(f"✓ Transformed {len(bulk_request['events'])} events")
    if strategy_summary:
        print(f"✓ Included Strategy Summary in payload")
    print()

    # Show sample event
    if bulk_request['events']:
        print("Sample transformed event:")
        sample = bulk_request['events'][0]
        print(f"  Date: {sample['event_date']}")
        print(f"  Title: {sample['title']}")
        print(f"  Type: {sample['event_type']}")
        print(f"  Send Time: {sample['send_time']}")
        print(f"  Color: {sample['color']}")
        print()

    # Import to app
    try:
        result = import_to_app(API_URL, bulk_request)

        print("=" * 60)
        print("IMPORT SUCCESSFUL!")
        print("=" * 60)
        print(f"✓ Created {result.get('count')} events")
        print(f"✓ Client: {bulk_request['client_id']}")
        print()

        if result.get('events'):
            print("Sample created events:")
            for event in result['events'][:3]:
                print(f"  • {event.get('event_date')}: {event.get('title')}")

        print()
        print(f"View in app: {API_URL}/dashboard/calendar")

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to emailpilot-app API")
        print(f"Make sure the API is running on {API_URL}")
        print("Try: cd emailpilot-app && source .venv/bin/activate && python3 api.py")
        sys.exit(1)

    except requests.exceptions.HTTPError as e:
        print(f"ERROR: API request failed: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        sys.exit(1)


if __name__ == "__main__":
    main()
