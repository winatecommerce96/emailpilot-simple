#!/usr/bin/env python3
"""
Run a workflow test for Christopher Bean Coffee - February 2026
"""
import os
import sys
import asyncio
import logging
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
from agents.calendar_agent import CalendarAgent
from data.native_mcp_client import NativeMCPClient
from data.http_rag_client import HttpRAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache
from data.review_state_manager import ReviewStateManager

async def run_chris_bean_test():
    """Run workflow for Christopher Bean Coffee - February 2026"""
    
    client_name = "chris-bean"
    start_date = "2026-02-01"
    end_date = "2026-02-28"
    
    print(f"\n🚀 Starting workflow for {client_name}")
    print(f"📅 Date Range: {start_date} to {end_date}")
    print("=" * 60)
    
    # Initialize components
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    rag_api_url = os.getenv("RAG_API_BASE_URL")
    
    mcp_client = NativeMCPClient(client_name)
    rag_client = HttpRAGClient(rag_api_base_url=rag_api_url)
    firestore_client = FirestoreClient(project_id=project_id)
    mcp_cache = MCPCache()
    
    # Initialize Agent
    agent = CalendarAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_client=mcp_client,
        rag_client=rag_client,
        firestore_client=firestore_client,
        cache=mcp_cache,
        model="claude-sonnet-4-5-20250929"
    )
    
    try:
        # Initialize MCP Client
        async with mcp_client:
            print("\n✅ MCP Client initialized")
            
            # Run the workflow
            result = await agent.run_workflow_with_checkpoint(
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                workflow_id=f"{client_name}_{start_date}_{end_date}_test"
            )
            
            if result["success"]:
                print("\n" + "=" * 60)
                print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"\n📋 Workflow ID: {result.get('workflow_id')}")
                print(f"🔗 Review URL: {result.get('review_url')}")
                print(f"\n📂 Output files saved to: outputs/")
                
                # List output files
                output_dir = Path("outputs")
                workflow_id = result.get("workflow_id")
                if workflow_id:
                    print(f"\n📄 Generated files:")
                    for file in sorted(output_dir.glob(f"{workflow_id}*")):
                        print(f"   - {file.name}")
                
                return 0
            else:
                print(f"\n❌ Workflow failed: {result.get('error')}")
                return 1
                
    except Exception as e:
        print(f"\n❌ Exception during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run_chris_bean_test()))
