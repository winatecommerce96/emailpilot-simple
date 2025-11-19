#!/usr/bin/env python3
"""
Push Calendar Events to EmailPilot-App

Reads calendar_import.json and pushes events to the emailpilot-app calendar API.
Fixes validation errors during transformation.
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


# Type mappings: invalid → valid
TYPE_MAPPINGS = {
    "content": "educational",
    "special": "product_spotlight"
}


def load_calendar_data(file_path: str) -> Dict[str, Any]:
    """Load calendar data from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def fix_event_type(event_type: str) -> str:
    """Fix invalid event types."""
    return TYPE_MAPPINGS.get(event_type, event_type)


def transform_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform calendar_import.json event to CalendarEventCreate format.

    Mapping:
    - name → title
    - date → event_date
    - type → event_type (with validation fixes)
    - time → send_time
    - status → status
    - description → description
    - custom_fields → metadata
    - tags → metadata (add to metadata dict)
    - client_id → client_id
    """
    # Fix event type if needed
    event_type = fix_event_type(event.get("type", "campaign"))

    # Prepare metadata
    metadata = event.get("custom_fields", {}).copy() if event.get("custom_fields") else {}

    # Add tags to metadata
    if event.get("tags"):
        metadata["tags"] = event["tags"]

    # Add client_name to metadata
    if event.get("client_name"):
        metadata["client_name"] = event["client_name"]

    # Transform to CalendarEventCreate schema
    transformed = {
        "client_id": event["client_id"],
        "title": event["name"],
        "event_date": event["date"],
        "description": event.get("description", ""),
        "event_type": event_type,
        "status": event.get("status", "draft"),
        "send_time": event.get("time"),
        "metadata": metadata
    }

    return transformed


def create_bulk_request(events: List[Dict[str, Any]], client_id: str) -> Dict[str, Any]:
    """Create BulkEventsCreate request payload."""
    return {
        "client_id": client_id,
        "events": events
    }


def push_to_api(bulk_request: Dict[str, Any], api_url: str) -> Dict[str, Any]:
    """
    Push events to emailpilot-app API.

    Args:
        bulk_request: BulkEventsCreate payload
        api_url: API endpoint URL

    Returns:
        API response data
    """
    try:
        response = requests.post(
            api_url,
            json=bulk_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise


def main():
    """Main execution."""
    print("=" * 80)
    print("Push Calendar Events to EmailPilot-App")
    print("=" * 80)

    # Configuration
    calendar_file = "outputs/rogue-creamery_2026-01-01_2026-01-31_20251118_194816_calendar_import.json"
    api_url = "http://localhost:8000/api/calendar/create-bulk-events"

    # Check if calendar file exists
    if not Path(calendar_file).exists():
        print(f"❌ Calendar file not found: {calendar_file}")
        sys.exit(1)

    print(f"\n📂 Loading calendar data from: {calendar_file}")

    # Load calendar data
    calendar_data = load_calendar_data(calendar_file)

    events = calendar_data.get("events", [])
    client_id = calendar_data.get("metadata", {}).get("client_id", "rogue-creamery")

    print(f"✅ Loaded {len(events)} events for client: {client_id}")

    # Transform events
    print("\n🔄 Transforming events...")
    transformed_events = []
    validation_fixes = []

    for i, event in enumerate(events, 1):
        original_type = event.get("type")
        transformed = transform_event(event)
        transformed_events.append(transformed)

        # Track validation fixes
        if original_type != transformed["event_type"]:
            validation_fixes.append(
                f"  Event {i}: '{event['name']}' - type '{original_type}' → '{transformed['event_type']}'"
            )

    print(f"✅ Transformed {len(transformed_events)} events")

    if validation_fixes:
        print(f"\n🔧 Applied {len(validation_fixes)} validation fixes:")
        for fix in validation_fixes:
            print(fix)

    # Create bulk request
    bulk_request = create_bulk_request(transformed_events, client_id)

    print(f"\n📤 Pushing events to API: {api_url}")

    # Push to API
    try:
        result = push_to_api(bulk_request, api_url)

        print("\n✅ Events pushed successfully!")
        print(f"   - Created: {result.get('count', 0)} events")

        if result.get('events'):
            print("\n📋 Created event IDs:")
            for event in result['events']:
                print(f"   - {event['id']}: {event['title']} ({event['event_date']})")

        print("\n" + "=" * 80)
        print("Integration complete!")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n❌ Failed to push events: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
