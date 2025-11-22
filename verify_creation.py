import asyncio
import logging
import os
from dotenv import load_dotenv
from tools import CalendarTool
from agents.calendar_agent import CalendarAgent
from data.native_mcp_client import NativeMCPClient as MCPClient
from data.http_rag_client import HttpRAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    client_name = "rogue-creamery"
    start_date = "2026-01-01"
    end_date = "2026-01-31"
    
    print(f"🚀 Starting verification for {client_name} ({start_date} to {end_date})")
    
    # Initialize components
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    mcp_client = MCPClient(client_name)
    
    # Use HTTP RAG client to call orchestrator API (no LangChain needed)
    rag_api_url = os.getenv("RAG_API_BASE_URL")
    rag_client = HttpRAGClient(rag_api_base_url=rag_api_url)
    
    firestore_client = FirestoreClient(project_id=project_id)
    mcp_cache = MCPCache()
    
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        # Try fallback key
        anthropic_api_key = os.getenv("ANTHROPIC_DOC_TO_ASANA_KEY")
        
    if not anthropic_api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        return

    calendar_agent = CalendarAgent(
        anthropic_api_key=anthropic_api_key,
        mcp_client=mcp_client,
        rag_client=rag_client,
        firestore_client=firestore_client,
        cache=mcp_cache,
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    )
    
    calendar_tool = CalendarTool(
        calendar_agent=calendar_agent,
        output_dir="outputs",
        validate_outputs=True
    )
    
    # Initialize MCP Client
    await mcp_client.initialize()
    
    # Run checkpoint workflow (Stage 1 & 2)
    try:
        result = await calendar_tool.run_checkpoint_workflow(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            review_manager=None, # Skip Firestore review state for this test
            save_outputs=True
        )
        
        if result["success"]:
            print("\n✅ Workflow completed successfully!")
            print("Check logs above for 'Successfully pushed ... events to app'")
        else:
            print("\n❌ Workflow failed or completed with issues.")
            print(result.get("error"))
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
    finally:
        await mcp_client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
