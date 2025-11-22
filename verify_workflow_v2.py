#!/usr/bin/env python3
"""
Full Workflow Verification Script (v2)
--------------------------------------
Verifies the complete workflow including the new SMS generation stage.
Mocks the external SLA API to ensure deterministic SMS requirements.
"""

import os
import sys
import asyncio
import logging
import json
from unittest.mock import MagicMock, patch
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure GOOGLE_CLOUD_PROJECT is set
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import components
# (We need to mock some imports if dependencies are missing/hard to setup)
try:
    from agents.calendar_agent import CalendarAgent
    from data.mcp_client import MCPClient
    from data.http_rag_client import HttpRAGClient
    from data.firestore_client import FirestoreClient
    from data.mcp_cache import MCPCache
    from data.review_state_manager import ReviewStateManager
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

async def verify_workflow():
    print("\n🚀 Starting Full Workflow Verification (SMS Stage Included)")
    print("=" * 60)

    client_name = "rogue-creamery"
    start_date = "2026-01-01"
    end_date = "2026-01-31"
    workflow_id = f"verify_sms_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Mock dependencies
    mock_mcp_client = MagicMock(spec=MCPClient)
    # Return serializable data for MCP
    mock_mcp_client.fetch_all_data.return_value = {
        "segments": [{"name": "VIP", "id": "123"}],
        "campaigns": [],
        "flows": []
    }
    
    mock_rag_client = MagicMock(spec=HttpRAGClient)
    mock_firestore = MagicMock(spec=FirestoreClient)
    mock_cache = MagicMock(spec=MCPCache)
    mock_cache.get.return_value = None # Force fetch
    
    # Setup RAG mock
    mock_rag_client.get_all_data.return_value = {
        "brand_voice": {"content": "Friendly, artisanal, premium cheese maker voice."},
        "product_catalog": {"content": "Blue cheese, cheddar, organic products."},
        "target_audience": {"content": "Foodies, cheese lovers, gift buyers."}
    }

    # Initialize Agent
    agent = CalendarAgent(
        anthropic_api_key="dummy_key", # We will mock the client anyway
        mcp_client=mock_mcp_client,
        rag_client=mock_rag_client,
        firestore_client=mock_firestore,
        cache=mock_cache,
        model="claude-sonnet-4-5-20250929"
    )

    # Mock the Anthropic client (not used if we mock _call_claude)
    agent.client = MagicMock()
    
    # Mock _call_claude directly to avoid client complexity
    async def mock_call_claude(system, user, **kwargs):
        print(f"   🤖 Mocking _call_claude response")
        print(f"      System (first 200 chars): {system[:200]}")
        print(f"      Kwargs keys: {list(kwargs.keys())}")
        
        if "email marketing strategist" in system.lower():
            return """
Email Campaign 1: New Year Cheese Board
Date: 2026-01-05
Theme: Start the year with artisanal cheese
Segment: All Active Profiles

Email Campaign 2: Winter Warmers
Date: 2026-01-15
Theme: Cozy recipes for cold nights
Segment: VIP Customers
"""
        elif "sms marketing specialist" in system.lower():
            return json.dumps([
                {
                    "campaign_name": "SMS 1: Flash Sale",
                    "scheduled_date": "2026-01-10",
                    "message_content": "Flash Sale! Get 20% off all blue cheese this weekend only. Shop now: [LINK]",
                    "target_audience": "VIP",
                    "channel": "SMS"
                },
                {
                    "campaign_name": "SMS 2: Restock Alert",
                    "scheduled_date": "2026-01-20",
                    "message_content": "Back in stock! Your favorite cheddar is available again. Grab yours: [LINK]",
                    "target_audience": "Engaged 30 Days",
                    "channel": "SMS"
                },
                {
                    "campaign_name": "SMS 3: Last Chance",
                    "scheduled_date": "2026-01-30",
                    "message_content": "Last chance for January specials! Don't miss out on these pairings. Shop: [LINK]",
                    "target_audience": "All SMS Subscribers",
                    "channel": "SMS"
                }
            ])
            
        elif "data structuring specialist" in system.lower():
            return json.dumps({
                "campaigns": [
                    {
                        "campaign_name": "New Year Cheese Board",
                        "scheduled_date": "2026-01-05",
                        "email_subject_line": "Start 2026 with the Best Cheese",
                        "preview_text": "Curated boards for your New Year celebration.",
                        "segment_name": "All Active Profiles",
                        "channel": "EMAIL"
                    },
                    {
                        "campaign_name": "SMS 1: Flash Sale",
                        "scheduled_date": "2026-01-10",
                        "message_content": "Flash Sale! Get 20% off all blue cheese this weekend only. Shop now: [LINK]",
                        "segment_name": "VIP",
                        "channel": "SMS"
                    },
                    {
                        "campaign_name": "Winter Warmers",
                        "scheduled_date": "2026-01-15",
                        "email_subject_line": "Cozy Recipes for Cold Nights",
                        "preview_text": "Warm up with our favorite cheese recipes.",
                        "segment_name": "VIP Customers",
                        "channel": "EMAIL"
                    },
                    {
                        "campaign_name": "SMS 2: Restock Alert",
                        "scheduled_date": "2026-01-20",
                        "message_content": "Back in stock! Your favorite cheddar is available again. Grab yours: [LINK]",
                        "segment_name": "Engaged 30 Days",
                        "channel": "SMS"
                    },
                    {
                        "campaign_name": "SMS 3: Last Chance",
                        "scheduled_date": "2026-01-30",
                        "message_content": "Last chance for January specials! Don't miss out on these pairings. Shop: [LINK]",
                        "segment_name": "All SMS Subscribers",
                        "channel": "SMS"
                    }
                ]
            })
        else:
            # Fallback for unexpected stages
            return "{}"



    agent._call_claude = MagicMock(side_effect=mock_call_claude)

    # Mock the _get_client_id_from_api method to return the client name
    agent._get_client_id_from_api = MagicMock(return_value=client_name)
    
    # Mock _push_to_calendar_app to be awaitable
    async def mock_push(*args, **kwargs):
        return True
    agent._push_to_calendar_app = MagicMock(side_effect=mock_push)
    
    # Mock ReviewStateManager to avoid Firestore writes
    with patch('agents.calendar_agent.ReviewStateManager') as MockReviewManager:
        mock_review_instance = MockReviewManager.return_value
        mock_review_instance.save_review_state.return_value = True

        # Mock httpx.get to return SLA with SMS requirements
        with patch('httpx.get') as mock_get:
            print("\n🔧 Setting up mocks...")
            
            # Mock response for SLA check
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{
                "id": client_name,
                "slug": client_name,
                "metadata": {
                    "sla_email_sends_per_month": 8,
                    "sla_sms_sends_per_month": 3  # REQUIRE 3 SMS CAMPAIGNS
                }
            }]
            mock_get.return_value = mock_response
            print("   ✅ SLA Mocked: 8 Emails, 3 SMS")

            # Run the workflow
            print(f"\n🏃 Running workflow for {client_name}...")
            try:
                result = await agent.run_workflow_with_checkpoint(
                    client_name=client_name,
                    start_date=start_date,
                    end_date=end_date,
                    workflow_id=workflow_id
                )
                
                if result["success"]:
                    print("\n✅ Workflow execution successful!")
                    
                    # Verify ReviewStateManager was called with correct data
                    call_args = mock_review_instance.save_review_state.call_args
                    if call_args:
                        kwargs = call_args[1]
                        detailed_calendar_json = kwargs.get('detailed_calendar')
                        detailed_calendar = json.loads(detailed_calendar_json)
                        
                        print("\n📊 Analyzing Output:")
                        
                        # Count campaigns
                        campaigns = detailed_calendar.get("campaigns", [])
                        email_count = sum(1 for c in campaigns if c.get("channel") == "EMAIL")
                        sms_count = sum(1 for c in campaigns if c.get("channel") == "SMS")
                        
                        print(f"   Total Campaigns: {len(campaigns)}")
                        print(f"   Email Campaigns: {email_count}")
                        print(f"   SMS Campaigns:   {sms_count}")
                        
                        # Validation
                        success = True
                        if sms_count == 3:
                            print("   ✅ SMS Count matches SLA (3)")
                        else:
                            print(f"   ❌ SMS Count mismatch! Expected 3, got {sms_count}")
                            success = False
                            
                        if email_count > 0:
                            print(f"   ✅ Generated {email_count} Email campaigns")
                        else:
                            print("   ❌ No Email campaigns generated")
                            success = False
                            
                        # Check merging
                        if len(campaigns) == email_count + sms_count:
                            print("   ✅ Merging looks correct (Total = Email + SMS)")
                        else:
                            print("   ❌ Merging issue: Total != Email + SMS")
                            success = False
                            
                        if success:
                            print("\n🎉 VERIFICATION PASSED: SMS Generation & Merging works!")
                            return 0
                        else:
                            print("\n⚠️ VERIFICATION FAILED: Output validation failed")
                            return 1
                    else:
                        print("❌ Failed to capture save_review_state arguments")
                        return 1
                else:
                    print(f"\n❌ Workflow failed: {result.get('error')}")
                    return 1
                    
            except Exception as e:
                print(f"\n❌ Exception during workflow execution: {e}")
                import traceback
                traceback.print_exc()
                return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(verify_workflow()))
