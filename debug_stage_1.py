import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.calendar_agent import CalendarAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    load_dotenv()
    
    logger.info("Starting Stage 1 Targeted Test")
    
    try:
        from data.native_mcp_client import NativeMCPClient
        from data.http_rag_client import HttpRAGClient
        from data.firestore_client import FirestoreClient
        from data.mcp_cache import MCPCache
        
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Mock MCP Client
        class MockMCPClient:
            async def fetch_all_data(self, client_name, start_date, end_date):
                return {
                    "campaigns": [],
                    "flows": [],
                    "segments": [{"name": "Engaged 30 Days", "count": 5000, "id": "S1"}],
                    "catalog": []
                }
        
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

        
        # Run Stage 1
        planning_output = await agent.stage_1_planning(
            client_name="chris-bean",
            start_date="2026-01-01",
            end_date="2026-01-31",
            workflow_id="test_stage_1_recovery"
        )
        
        print("\n" + "="*50)
        print("STAGE 1 OUTPUT ANALYSIS")
        print("="*50)
        
        # Analyze SMS counts
        sms_type_count = planning_output.lower().count('"campaign_type": "sms"')
        sms_channel_count = planning_output.lower().count('"channel": "sms"')
        sms_variant_count = planning_output.lower().count('"sms_variant"')
        
        print(f"campaign_type: 'sms' count: {sms_type_count}")
        print(f"channel: 'sms' count: {sms_channel_count}")
        print(f"sms_variant count: {sms_variant_count}")
        
        if sms_type_count >= 3:
            print("\n✅ SUCCESS: Stage 1 generated required SMS campaigns!")
        else:
            print(f"\n❌ FAILURE: Stage 1 generated only {sms_type_count} SMS campaigns (required: 3)")
            
        # Save output for Stage 2 testing
        with open("debug_planning_output.txt", "w") as f:
            f.write(planning_output)
        print("\nSaved planning output to debug_planning_output.txt")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
