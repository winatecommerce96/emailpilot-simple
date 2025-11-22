#!/usr/bin/env python3
"""
Re-process latest workflow to test enriched data.
Fetches from Firestore and regenerates simplified calendar with new fields.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.review_state_manager import ReviewStateManager
from tools.format_adapter import CalendarFormatAdapter

def reprocess_workflow():
    workflow_id = "chris-bean_2026-01-01_20251120_115012"
    
    print(f"Re-processing workflow: {workflow_id}")
    
    # Initialize ReviewStateManager
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    review_manager = ReviewStateManager(project_id=project_id)
    
    if not review_manager.is_available():
        print("❌ Firestore not available")
        return 1
    
    # Get review state
    review_data = review_manager.get_review_state(workflow_id)
    
    if not review_data:
        print(f"❌ No review data found for {workflow_id}")
        return 1
    
    print(f"✅ Found review data")
    
    # Extract data
    detailed_calendar_str = review_data.get('detailed_calendar')
    planning_output = review_data.get('planning_output')
    client_name = review_data.get('client_name', 'chris-bean')
    
    if not detailed_calendar_str:
        print("❌ No detailed calendar found")
        return 1
    
    # Parse JSON
    detailed_calendar = json.loads(detailed_calendar_str)
    
    print(f"📅 Detailed calendar has {len(detailed_calendar.get('campaigns', []))} campaigns")
    
    # Re-generate simplified calendar with NEW fields
    adapter = CalendarFormatAdapter()
    enriched_calendar = adapter.transform_to_app_format(
        detailed_calendar,
        client_name,
        planning_output=planning_output
    )
    
    # Save enriched calendar
    output_file = Path("./outputs") / f"{workflow_id}_enriched_calendar.json"
    with open(output_file, 'w') as f:
        json.dump(enriched_calendar, f, indent=2)
    
    print(f"✅ Saved enriched calendar: {output_file}")
    print(f"   Events: {len(enriched_calendar.get('events', []))}")
    print(f"   Has send_strategy: {('send_strategy' in enriched_calendar)}")
    
    # Show sample event with new fields
    if enriched_calendar.get('events'):
        sample_event = enriched_calendar['events'][0]
        print(f"\n📋 Sample Event Fields:")
        for key in sample_event.keys():
            if key == 'strategy':
                print(f"   - {key}: (object with {len(sample_event[key])} fields)")
            else:
                value = str(sample_event[key])[:50]
                print(f"   - {key}: {value}...")
    
    # Check for new Calendar App fields
    new_fields = ['subject_a', 'subject_b', 'preview_text', 'main_cta', 'offer', 'content_brief', 'template_type']
    print(f"\n🔍 New Calendar App Fields:")
    if enriched_calendar.get('events'):
        first_event = enriched_calendar['events'][0]
        for field in new_fields:
            status = "✅" if field in first_event else "❌"
            print(f"   {status} {field}")
    
    return 0

if __name__ == "__main__":
    sys.exit(reprocess_workflow())
