#!/usr/bin/env python3
"""
Fix Invalid Event Types in Calendar Database

Reads all events from the calendar API, identifies invalid event types,
and updates them to valid types using the PUT /events/{event_id} endpoint.
"""

import json
import sys
import argparse
import requests
from typing import List, Dict, Any

# Type mappings: invalid → valid
TYPE_MAPPINGS = {
    "content": "educational",
    "special": "product_spotlight",
    "email_campaign": "promotional",  # Best guess for generic email campaigns
    "email": "promotional"  # Best guess for generic emails
}

# Valid event types per schema
VALID_TYPES = [
    "promotional", "educational", "seasonal", "product_launch",
    "product_spotlight", "engagement", "win_back", "nurture",
    "resend", "lifecycle"
]

def get_all_events(api_url: str, client_id: str) -> List[Dict[str, Any]]:
    """Fetch all events for a client from the API."""
    try:
        response = requests.get(
            f"{api_url}/events",
            params={"client_id": client_id},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch events: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        sys.exit(1)


def update_event_type(api_url: str, event_id: str, new_type: str) -> bool:
    """Update an event's type using the PUT endpoint."""
    try:
        response = requests.put(
            f"{api_url}/events/{event_id}",
            json={"event_type": new_type},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed to update event {event_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text}")
        return False


def main():
    """Main execution."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Fix invalid event types in calendar database")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm updates without prompting")
    args = parser.parse_args()

    print("=" * 80)
    print("Fix Invalid Event Types in Calendar Database")
    print("=" * 80)

    # Configuration
    api_url = "http://localhost:8008/api/calendar"
    client_id = "rogue-creamery"

    print(f"\n📂 Fetching events for client: {client_id}")
    events = get_all_events(api_url, client_id)
    print(f"✅ Fetched {len(events)} events")

    # Identify invalid events
    invalid_events = []
    for event in events:
        event_type = event.get("event_type", "")
        if event_type and event_type not in VALID_TYPES:
            invalid_events.append({
                "id": event.get("id"),
                "title": event.get("title", "Untitled"),
                "current_type": event_type,
                "new_type": TYPE_MAPPINGS.get(event_type, "promotional")  # Default to promotional
            })

    if not invalid_events:
        print("\n✅ No invalid event types found. All events are valid!")
        return 0

    # Report invalid events
    print(f"\n🔍 Found {len(invalid_events)} events with invalid types:")

    # Group by type for summary
    type_counts = {}
    for event in invalid_events:
        current = event["current_type"]
        type_counts[current] = type_counts.get(current, 0) + 1

    for invalid_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        valid_type = TYPE_MAPPINGS.get(invalid_type, "promotional")
        print(f"   • '{invalid_type}' ({count} events) → '{valid_type}'")

    # Confirm before proceeding
    print(f"\n⚠️  About to update {len(invalid_events)} events")

    if not args.yes:
        response = input("Proceed with updates? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("❌ Update cancelled by user")
            return 1
    else:
        print("✅ Auto-confirming (--yes flag provided)")

    # Update events
    print("\n🔄 Updating events...")
    success_count = 0
    failed_count = 0

    for i, event in enumerate(invalid_events, 1):
        event_id = event["id"]
        current_type = event["current_type"]
        new_type = event["new_type"]
        title = event["title"][:50]  # Truncate long titles

        print(f"   [{i}/{len(invalid_events)}] Updating '{title}' ({event_id})")
        print(f"       '{current_type}' → '{new_type}'")

        if update_event_type(api_url, event_id, new_type):
            success_count += 1
            print(f"       ✅ Success")
        else:
            failed_count += 1
            print(f"       ❌ Failed")

    # Summary
    print("\n" + "=" * 80)
    print("Update Summary")
    print("=" * 80)
    print(f"✅ Successfully updated: {success_count} events")
    if failed_count > 0:
        print(f"❌ Failed to update: {failed_count} events")
    print("=" * 80)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
