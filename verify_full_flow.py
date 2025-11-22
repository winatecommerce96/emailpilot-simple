import os
import sys
import asyncio
import logging
import json
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
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import components
from tools import CalendarTool
from agents.calendar_agent import CalendarAgent
from data.native_mcp_client import NativeMCPClient as MCPClient
from data.http_rag_client import HttpRAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache
from data.review_state_manager import ReviewStateManager, ReviewStatus

async def verify_full_flow():
    """
    Verify the full EmailPilot HIL workflow:
    1. Stage 1 & 2 (Checkpoint) -> Save to Firestore
    2. Simulate Approval
    3. Stage 3 (Resume) -> Generate Briefs
    """
    
    client_name = "rogue-creamery"
    start_date = "2026-01-01"
    end_date = "2026-01-31"
    
    print(f"\n🚀 Starting FULL HIL verification for {client_name} ({start_date} to {end_date})")
    
    # Initialize components
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    print(f"ℹ️ Using Google Cloud Project: {project_id}")
    
    mcp_client = MCPClient(client_name)
    
    # Use HTTP RAG client
    rag_api_url = os.getenv("RAG_API_BASE_URL")
    rag_client = HttpRAGClient(rag_api_base_url=rag_api_url)
    
    firestore_client = FirestoreClient(project_id=project_id)
    mcp_cache = MCPCache()
    review_manager = ReviewStateManager(firestore_client)
    
    # Initialize Agent
    agent = CalendarAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_DOC_TO_ASANA_KEY"),
        mcp_client=mcp_client,
        rag_client=rag_client,
        firestore_client=firestore_client,
        cache=mcp_cache,
        model="claude-sonnet-4-5-20250929"
    )
    
    # Initialize Tool
    calendar_tool = CalendarTool(
        calendar_agent=agent,
        validate_outputs=True
    )
    
    try:
        # Initialize MCP Client
        async with mcp_client:
            # Step 1: Run Checkpoint Workflow (Stage 1 & 2)
            print("\n🏃 Step 1: Running Checkpoint Workflow (Stage 1 & 2)...")
            checkpoint_result = await calendar_tool.run_checkpoint_workflow(
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                review_manager=review_manager
            )
            
            workflow_id = checkpoint_result.get("metadata", {}).get("workflow_id")
            if not workflow_id:
                print("❌ Failed to get workflow_id from checkpoint result")
                return

            print(f"✅ Checkpoint completed. Workflow ID: {workflow_id}")
            
            # Step 2: Simulate Approval
            print("\n👍 Step 2: Simulating Approval...")
            review_manager.update_review_status(
                workflow_id=workflow_id,
                status=ReviewStatus.APPROVED,
                reviewer_id="verify_script"
            )
            print("✅ Workflow approved.")
            
            # Step 3: Resume Workflow (Stage 3)
            print("\n▶️ Step 3: Resuming Workflow (Stage 3)...")
            final_result = await calendar_tool.resume_workflow(
                workflow_id=workflow_id,
                review_manager=review_manager,
                save_outputs=True
            )
            
            if final_result.get("success"):
                print("\n✅ Full workflow completed successfully!")
            else:
                print(f"\n❌ Workflow resume failed: {final_result.get('error')}")
                return
            
            # Verify Outputs
            output_dir = Path("outputs")
            print(f"📂 Checking outputs for workflow: {workflow_id}")
            
            expected_files = [
                f"{workflow_id}_planning.txt",
                f"{workflow_id}_calendar_detailed.json",
                f"{workflow_id}_calendar_simplified.json",
                f"{workflow_id}_calendar_app.json",
                f"{workflow_id}_calendar_import.json",
                f"{workflow_id}_enriched_context.json",
                f"{workflow_id}_briefs.txt",
                f"{workflow_id}_validation.json"
            ]
            
            all_files_exist = True
            for filename in expected_files:
                path = output_dir / filename
                if path.exists():
                    print(f"  ✅ Found {filename}")
                else:
                    print(f"  ❌ Missing {filename}")
                    all_files_exist = False
                    
            # Check Validation Results
            validation_file = output_dir / f"{workflow_id}_validation.json"
            if validation_file.exists():
                with open(validation_file, 'r') as f:
                    val_data = json.load(f)
                    if val_data.get("calendar_valid"):
                        print("  ✅ Calendar Validation PASSED")
                    else:
                        print("  ❌ Calendar Validation FAILED")
                        print(f"     Errors: {val_data.get('errors')}")
            
            # Check RAG Usage
            context_file = output_dir / f"{workflow_id}_enriched_context.json"
            if context_file.exists():
                with open(context_file, 'r') as f:
                    context_data = f.read()
                    if "Authentic real photography" in context_data or "brand guidelines" in context_data:
                         print("  ✅ RAG Data confirmed in enriched context")
                    else:
                         print("  ⚠️ RAG Data NOT explicitly found in enriched context (check manually)")

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    # Cleanup is handled by async context manager

if __name__ == "__main__":
    asyncio.run(verify_full_flow())
