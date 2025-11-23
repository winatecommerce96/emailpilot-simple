#!/usr/bin/env python3
"""
Verification script to check if the calendar generation fixes are working.
Checks for:
1. SMS campaigns (count >= 4)
2. First of Month campaign (Jan 1st)
3. Campaign distribution (no clustering)
"""
import requests
import json
import sys
from collections import Counter
from datetime import datetime

API_URL = "http://localhost:9000/api/workflow/run"

payload = {
    "stage": "full",
    "clientName": "rogue-creamery",
    "startDate": "2026-01-01",
    "endDate": "2026-01-31",
    "userInstructions": "Test run for verification of SMS and distribution fixes."
}

print(f"🚀 Sending request to {API_URL}...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(API_URL, json=payload, timeout=600) # 10 minute timeout
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        calendar_json = data.get('calendar_json')
        
        if calendar_json:
            campaigns = calendar_json.get('events', [])
            print(f"\n✅ Calendar JSON found with {len(campaigns)} total events")
            
            # 1. Verify SMS Campaigns
            sms_campaigns = [c for c in campaigns if c.get('channel') == 'sms' or c.get('campaign_type') == 'sms']
            print(f"\n📱 SMS Campaigns: {len(sms_campaigns)}")
            if len(sms_campaigns) >= 4:
                print("✅ SMS count requirement met (>= 4)")
            else:
                print(f"❌ SMS count requirement NOT met (Found {len(sms_campaigns)}, expected >= 4)")
                
            # 2. Verify First of Month
            first_of_month = [c for c in campaigns if c.get('send_date') == '2026-01-01']
            print(f"\n📅 First of Month Campaigns: {len(first_of_month)}")
            if first_of_month:
                print("✅ First of Month rule met")
                print(f"   - Campaign: {first_of_month[0].get('content_theme')}")
            else:
                print("❌ First of Month rule NOT met (No campaign on 2026-01-01)")
                
            # 3. Verify Distribution
            dates = [c.get('send_date') for c in campaigns if c.get('channel') != 'sms'] # Only check email distribution
            date_counts = Counter(dates)
            clustered_days = [date for date, count in date_counts.items() if count > 1]
            
            print(f"\n📊 Distribution Analysis (Email Only):")
            if not clustered_days:
                print("✅ No clustering found (max 1 email per day)")
            else:
                print(f"⚠️  Clustering found on {len(clustered_days)} days: {clustered_days}")
                
            # Print day of week distribution
            days_of_week = [datetime.strptime(d, "%Y-%m-%d").strftime("%A") for d in dates]
            day_counts = Counter(days_of_week)
            print("\nDay of Week Distribution:")
            for day, count in day_counts.items():
                print(f"   - {day}: {count}")

            # 4. Verify Segmentation
            print(f"\n🎯 Segmentation Analysis:")
            segments_used = []
            all_targeting_count = 0
            for c in campaigns:
                if c.get('channel') == 'sms': continue
                
                seg = c.get('segments', {}).get('primary', 'Unknown')
                segments_used.append(seg)
                
                if seg.lower() in ['all', 'all subscribers', 'everyone', 'master list']:
                    all_targeting_count += 1
            
            unique_segments = set(segments_used)
            print(f"   - Unique Segments Used: {len(unique_segments)}")
            print(f"   - 'All' Targeting Count: {all_targeting_count}")
            
            if all_targeting_count == 0:
                print("✅ Segmentation check passed (No 'All' targeting)")
            else:
                print(f"❌ Segmentation check FAILED ({all_targeting_count} campaigns target 'All')")
                
            print("   - Segments List:")
            for s in unique_segments:
                print(f"     * {s}")
            
        else:
            print("\n❌ NO calendar_json found in response data!")
            
    else:
        print(f"\n❌ Error Response ({response.status_code}):")
        print(response.text)

except Exception as e:
    print(f"\n❌ Exception: {e}")
