#!/usr/bin/env python3
"""
Push saved calendar to Calendar App.
Retrieves calendar from Firestore and pushes to localhost:8000
"""

import os
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.review_state_manager import ReviewStateManager

async def push_calendar():
    workflow_id = "chris-bean_2026-01-01_20251120_115012"
    
    print(f"Fetching calendar for workflow: {workflow_id}")
    
    # Initialize ReviewStateManager with project_id
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set")
        return 1
    
    print(f"Using project: {project_id}")
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
    
    # Extract simplified calendar
    simplified_calendar_str = review_data.get('simplified_calendar')
    
    if not simplified_calendar_str:
        print("❌ No simplified calendar found")
        return 1
    
    # Parse JSON string
    simplified_calendar = json.loads(simplified_calendar_str)
    
    print(f"📅 Calendar has {len(simplified_calendar.get('events', []))} events")
    
    # Push to Calendar App
    calendar_app_url = "http://localhost:8000/api/calendar/import"
    
    print(f"Pushing to Calendar App: {calendar_app_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                calendar_app_url,
                json=simplified_calendar
            )
            response.raise_for_status()
            
            print(f"✅ Successfully pushed calendar to app!")
            print(f"Response: {response.status_code}")
            result = response.json()
            print(f"Data: {json.dumps(result, indent=2)}")
            
            return 0
            
        except httpx.HTTPError as e:
            print(f"❌ Failed to push calendar: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            return 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(push_calendar()))
