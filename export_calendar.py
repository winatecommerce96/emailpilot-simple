#!/usr/bin/env python3
"""
Export saved calendar to JSON file for manual import.
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

def export_calendar():
    workflow_id = "chris-bean_2026-01-01_20251120_115012"
    
    print(f"Exporting calendar for workflow: {workflow_id}")
    
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
    
    # Extract calendars
    simplified_calendar_str = review_data.get('simplified_calendar')
    detailed_calendar_str = review_data.get('detailed_calendar')
    planning_output = review_data.get('planning_output')
    
    # Parse JSON strings
    simplified_calendar = json.loads(simplified_calendar_str) if simplified_calendar_str else None
    detailed_calendar = json.loads(detailed_calendar_str) if detailed_calendar_str else None
    
    # Save to files
    output_dir = Path("./outputs")
    output_dir.mkdir(exist_ok=True)
    
    if simplified_calendar:
        simplified_file = output_dir / f"{workflow_id}_simplified_calendar.json"
        with open(simplified_file, 'w') as f:
            json.dump(simplified_calendar, f, indent=2)
        print(f"✅ Saved simplified calendar: {simplified_file}")
        print(f"   Events: {len(simplified_calendar.get('events', []))}")
    
    if detailed_calendar:
        detailed_file = output_dir / f"{workflow_id}_detailed_calendar.json"
        with open(detailed_file, 'w') as f:
            json.dump(detailed_calendar, f, indent=2)
        print(f"✅ Saved detailed calendar: {detailed_file}")
        print(f"   Campaigns: {len(detailed_calendar.get('campaigns', []))}")
    
    if planning_output:
        planning_file = output_dir / f"{workflow_id}_planning.txt"
        with open(planning_file, 'w') as f:
            f.write(planning_output)
        print(f"✅ Saved planning output: {planning_file}")
        print(f"   Length: {len(planning_output)} characters")
    
    return 0

if __name__ == "__main__":
    sys.exit(export_calendar())
