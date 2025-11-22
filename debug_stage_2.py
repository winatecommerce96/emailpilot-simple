import asyncio
import os
import sys
import logging
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.calendar_agent import CalendarAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    load_dotenv()
    
    logger.info("Starting Stage 2 Targeted Test")
    
    try:
        # Read planning output
        if not os.path.exists("debug_planning_output.txt"):
            logger.error("debug_planning_output.txt not found. Run debug_stage_1.py first.")
            return

        with open("debug_planning_output.txt", "r") as f:
            planning_output = f.read()
            
        from data.native_mcp_client import NativeMCPClient
        from data.http_rag_client import HttpRAGClient
        from data.firestore_client import FirestoreClient
        from data.mcp_cache import MCPCache
        
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Mock MCP Client
        class MockMCPClient:
            async def fetch_all_data(self, client_name, start_date, end_date):
                return {}
        
        # Mock Firestore Client
        class MockFirestoreClient:
            def __init__(self, project_id=None): pass
            def get_all_data(self, client_name): return {}
            def format_for_prompt(self, client_name): return "No historical data."
            
        mcp_client = MockMCPClient()
        rag_client = HttpRAGClient()
        firestore_client = MockFirestoreClient()
        cache = MCPCache()

        
        agent = CalendarAgent(anthropic_api_key, mcp_client, rag_client, firestore_client, cache)

        
        # Run Stage 2
        calendar_json = await agent.stage_2_structuring(
            client_name="chris-bean",
            start_date="2026-01-01",
            end_date="2026-01-31",
            workflow_id="test_stage_2_recovery",
            planning_output=planning_output
        )
        
        print("\n" + "="*50)
        print("STAGE 2 OUTPUT ANALYSIS")
        print("="*50)
        
        events = calendar_json.get('events', [])
        print(f"Total events: {len(events)}")
        
        sms_events = [e for e in events if e.get('type') == 'sms' or e.get('channel') == 'sms']
        print(f"SMS Events found: {len(sms_events)}")
        
        for i, event in enumerate(sms_events):
            print(f"SMS Event {i+1}: {event.get('title', 'No Title')} (Type: {event.get('type')}, Channel: {event.get('channel')})")
            
        if len(sms_events) >= 3:
            print("\n✅ SUCCESS: Stage 2 preserved required SMS campaigns!")
        else:
            print(f"\n❌ FAILURE: Stage 2 preserved only {len(sms_events)} SMS campaigns (required: 3)")
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
