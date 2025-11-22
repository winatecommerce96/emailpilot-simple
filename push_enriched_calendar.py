#!/usr/bin/env python3
"""
Push enriched calendar to Calendar App.
"""

import os
import sys
import json
import httpx
from pathlib import Path

async def push_enriched_calendar():
    workflow_id = "chris-bean_2026-01-01_20251120_115012"
    enriched_file = Path("./outputs") / f"{workflow_id}_enriched_calendar.json"
    
    if not enriched_file.exists():
        print(f"❌ Enriched calendar not found: {enriched_file}")
        return 1
    
    # Load enriched calendar
    with open(enriched_file, 'r') as f:
        enriched_calendar = json.load(f)
    
    print(f"📅 Loaded enriched calendar with {len(enriched_calendar['events'])} events")
    print(f"   Has send_strategy: {('send_strategy' in enriched_calendar)}")
    
    # Push to Calendar App
    calendar_app_url = "http://localhost:8000/api/calendar/import"
    
    print(f"\n🚀 Pushing to Calendar App: {calendar_app_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                calendar_app_url,
                json=enriched_calendar
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"\n✅ Successfully pushed calendar to app!")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            return 0
            
        except httpx.HTTPError as e:
            print(f"\n❌ Failed to push calendar: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            return 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(push_enriched_calendar()))
