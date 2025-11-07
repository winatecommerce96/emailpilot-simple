#!/usr/bin/env python3
"""
EmailPilot Simple - FastAPI Backend

Serves the HTML UI and provides API endpoints for the calendar generation workflow.

Usage:
    uvicorn api:app --reload --port 8000
    # or
    python api.py
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from tools import CalendarTool
from agents.calendar_agent import CalendarAgent
from data.mcp_client import MCPClient
from data.rag_client import RAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache
from data.secret_manager_client import SecretManagerClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
app_state = {
    'calendar_agent': None,
    'calendar_tool': None,
    'mcp_client': None,
    'cache': None,
    'workflow_status': {},
    'initialized': False
}


# Request/Response Models
class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""
    stage: str  # 'validate', 'stage-1', 'stage-2', 'stage-3', 'full'
    clientName: str
    startDate: str
    endDate: str


class PromptUpdateRequest(BaseModel):
    """Request model for prompt updates."""
    content: str


class RAGDataRequest(BaseModel):
    """Request model for RAG data."""
    clientName: str


class MCPDataRequest(BaseModel):
    """Request model for MCP data."""
    clientName: str
    startDate: str
    endDate: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application components."""
    logger.info("Starting EmailPilot Simple API...")

    # Validate environment variables
    required_vars = ['ANTHROPIC_API_KEY', 'GOOGLE_CLOUD_PROJECT']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(f"Missing environment variables: {', '.join(missing_vars)}")

    # Initialize data layer clients
    logger.info("Initializing data layer clients...")

    secret_manager_client = SecretManagerClient(
        project_id=os.getenv('GOOGLE_CLOUD_PROJECT')
    )

    rag_client = RAGClient(
        rag_base_path='/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-orchestrator/rag'
    )

    firestore_client = FirestoreClient(
        project_id=os.getenv('GOOGLE_CLOUD_PROJECT')
    )

    cache = MCPCache()

    # Initialize MCP client (async context manager)
    mcp_client = MCPClient(secret_manager_client=secret_manager_client)
    await mcp_client.__aenter__()

    logger.info("Data layer clients initialized")

    # Initialize Calendar Agent
    model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
    logger.info(f"Initializing CalendarAgent with model: {model}")

    calendar_agent = CalendarAgent(
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        mcp_client=mcp_client,
        rag_client=rag_client,
        firestore_client=firestore_client,
        cache=cache,
        model=model
    )

    logger.info("CalendarAgent initialized")

    # Initialize Calendar Tool
    output_dir = './outputs'
    calendar_tool = CalendarTool(
        calendar_agent=calendar_agent,
        output_dir=output_dir,
        validate_outputs=True
    )

    logger.info("CalendarTool initialized")

    # Store in global state
    app_state['calendar_agent'] = calendar_agent
    app_state['calendar_tool'] = calendar_tool
    app_state['mcp_client'] = mcp_client
    app_state['rag_client'] = rag_client
    app_state['cache'] = cache
    app_state['initialized'] = True

    logger.info("EmailPilot Simple API ready")

    yield

    # Cleanup
    logger.info("Shutting down EmailPilot Simple API...")
    await mcp_client.__aexit__(None, None, None)
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="EmailPilot Simple API",
    description="API for EmailPilot Simple calendar generation workflow",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Helper functions
def standard_response(success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
    """Create a standard API response."""
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }

    if data is not None:
        response["data"] = data

    if error is not None:
        response["error"] = error

    return response


# Root endpoint - serve UI
@app.get("/")
async def root():
    """Serve the main UI."""
    index_path = static_dir / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")

    return FileResponse(index_path)


# Health check
@app.get("/api/health")
async def health_check():
    """Check API health and component status."""
    return standard_response(
        success=True,
        data={
            "status": "healthy",
            "initialized": app_state['initialized'],
            "components": {
                "calendar_agent": app_state['calendar_agent'] is not None,
                "calendar_tool": app_state['calendar_tool'] is not None,
                "mcp_client": app_state['mcp_client'] is not None,
                "rag_client": app_state['rag_client'] is not None,
                "cache": app_state['cache'] is not None
            }
        }
    )


# Workflow endpoints
@app.post("/api/workflow/run")
async def run_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """
    Execute workflow stage or full workflow.

    Stages:
    - validate: Validate inputs only
    - stage-1: Planning stage
    - stage-2: Calendar structuring stage
    - stage-3: Brief generation stage
    - full: Complete workflow
    """
    if not app_state['initialized']:
        raise HTTPException(status_code=503, detail="System not initialized")

    calendar_tool = app_state['calendar_tool']
    stage = request.stage
    client_name = request.clientName
    start_date = request.startDate
    end_date = request.endDate

    logger.info(f"Workflow request: stage={stage}, client={client_name}, dates={start_date} to {end_date}")

    try:
        if stage == 'validate':
            # Just validate inputs
            # TODO: Add proper validation logic
            return standard_response(
                success=True,
                data={
                    "validated": True,
                    "message": "Inputs are valid"
                }
            )

        elif stage == 'full':
            # Run complete workflow
            result = await calendar_tool.run_workflow(
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                save_outputs=True
            )

            return standard_response(
                success=result.get('success', False),
                data=result,
                error=result.get('error')
            )

        elif stage in ['stage-1', 'stage-2', 'stage-3']:
            # Run specific stage
            stage_num = int(stage.split('-')[1])

            # For stages 2 and 3, we need previous outputs
            # This is a simplified version - in production, you'd need to handle
            # loading previous stage outputs
            if stage_num > 1:
                return standard_response(
                    success=False,
                    error=f"Stage {stage_num} requires output from previous stage. Please run full workflow."
                )

            result = await calendar_tool.run_stage(
                stage=stage_num,
                client_name=client_name,
                start_date=start_date,
                end_date=end_date
            )

            return standard_response(
                success=result.get('success', False),
                data=result,
                error=result.get('error')
            )

        else:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
        return standard_response(
            success=False,
            error=str(e)
        )


# Prompt management endpoints
@app.get("/api/prompts/{prompt_name}")
async def get_prompt(prompt_name: str):
    """Fetch a prompt YAML file."""
    prompts_dir = Path(__file__).parent / "prompts"

    # Map friendly names to actual filenames
    prompt_files = {
        "planning": "planning_v5_1_0.yaml",
        "structuring": "calendar_structuring_v1_2_2.yaml",
        "briefs": "brief_generation_v2_2_0.yaml"
    }

    if prompt_name not in prompt_files:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_name}")

    prompt_file = prompts_dir / prompt_files[prompt_name]

    if not prompt_file.exists():
        raise HTTPException(status_code=404, detail=f"Prompt file not found: {prompt_file}")

    try:
        with open(prompt_file, 'r') as f:
            content = f.read()

        return standard_response(
            success=True,
            data={
                "name": prompt_name,
                "filename": prompt_files[prompt_name],
                "content": content
            }
        )

    except Exception as e:
        logger.error(f"Failed to read prompt {prompt_name}: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


@app.put("/api/prompts/{prompt_name}")
async def update_prompt(prompt_name: str, request: PromptUpdateRequest):
    """Update a prompt YAML file."""
    prompts_dir = Path(__file__).parent / "prompts"

    prompt_files = {
        "planning": "planning_v5_1_0.yaml",
        "structuring": "calendar_structuring_v1_2_2.yaml",
        "briefs": "brief_generation_v2_2_0.yaml"
    }

    if prompt_name not in prompt_files:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_name}")

    prompt_file = prompts_dir / prompt_files[prompt_name]

    try:
        # Backup existing file
        if prompt_file.exists():
            backup_file = prompt_file.with_suffix(f'.yaml.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            prompt_file.rename(backup_file)
            logger.info(f"Created backup: {backup_file}")

        # Write new content
        with open(prompt_file, 'w') as f:
            f.write(request.content)

        logger.info(f"Updated prompt: {prompt_name}")

        return standard_response(
            success=True,
            data={
                "name": prompt_name,
                "filename": prompt_files[prompt_name],
                "updated": True
            }
        )

    except Exception as e:
        logger.error(f"Failed to update prompt {prompt_name}: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


# RAG data endpoint
@app.post("/api/rag/data")
async def get_rag_data(request: RAGDataRequest):
    """Fetch RAG documents for a client."""
    if not app_state['initialized']:
        raise HTTPException(status_code=503, detail="System not initialized")

    rag_client = app_state['rag_client']
    client_name = request.clientName

    try:
        # Fetch RAG documents
        rag_data = rag_client.get_all_data(client_name)

        return standard_response(
            success=True,
            data={
                "client": client_name,
                "rag_data": rag_data,
                "document_count": len(rag_data.get("metadata", {}).get("available_documents", [])) if rag_data else 0
            }
        )

    except Exception as e:
        logger.error(f"Failed to fetch RAG data for {client_name}: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


# MCP data endpoint
@app.post("/api/mcp/data")
async def get_mcp_data(request: MCPDataRequest):
    """Fetch MCP data (segments, campaigns, flows, reports)."""
    if not app_state['initialized']:
        raise HTTPException(status_code=503, detail="System not initialized")

    mcp_client = app_state['mcp_client']
    client_name = request.clientName
    start_date = request.startDate
    end_date = request.endDate

    try:
        # Fetch all MCP data
        data = await mcp_client.fetch_all_data(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date
        )

        return standard_response(
            success=True,
            data=data
        )

    except Exception as e:
        logger.error(f"Failed to fetch MCP data for {client_name}: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


# Outputs endpoint
@app.get("/api/outputs/{output_type}")
async def get_output(output_type: str):
    """
    Retrieve workflow outputs.

    Types: planning, calendar, briefs
    """
    outputs_dir = Path(__file__).parent / "outputs"

    if not outputs_dir.exists():
        raise HTTPException(status_code=404, detail="No outputs directory found")

    try:
        # Find latest output file of the requested type
        pattern = f"*_{output_type}_*.txt" if output_type == "planning" else \
                  f"*_{output_type}_*.json" if output_type == "calendar" else \
                  f"*_{output_type}_*.md"

        output_files = list(outputs_dir.glob(pattern))

        if not output_files:
            return standard_response(
                success=True,
                data={
                    "type": output_type,
                    "content": None,
                    "message": f"No {output_type} outputs found"
                }
            )

        # Get most recent file
        latest_file = max(output_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, 'r') as f:
            content = f.read()

        return standard_response(
            success=True,
            data={
                "type": output_type,
                "filename": latest_file.name,
                "content": content,
                "modified": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Failed to fetch output {output_type}: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


# Cache endpoints
@app.get("/api/cache")
async def get_cache():
    """View cache contents."""
    if not app_state['initialized']:
        raise HTTPException(status_code=503, detail="System not initialized")

    cache = app_state['cache']

    try:
        # Get all cache entries
        cache_data = {}

        # MCPCache stores data in _cache dict
        if hasattr(cache, '_cache'):
            for key, entry in cache._cache.items():
                cache_data[key] = {
                    "value": entry.get('value'),
                    "expires_at": entry.get('expires_at').isoformat() if entry.get('expires_at') else None
                }

        return standard_response(
            success=True,
            data={
                "entries": cache_data,
                "count": len(cache_data)
            }
        )

    except Exception as e:
        logger.error(f"Failed to fetch cache data: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


@app.delete("/api/cache")
async def clear_cache():
    """Clear all cache entries."""
    if not app_state['initialized']:
        raise HTTPException(status_code=503, detail="System not initialized")

    cache = app_state['cache']

    try:
        # Clear cache
        if hasattr(cache, 'clear'):
            cache.clear()
        elif hasattr(cache, '_cache'):
            cache._cache.clear()

        logger.info("Cache cleared")

        return standard_response(
            success=True,
            data={
                "cleared": True
            }
        )

    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return standard_response(
            success=False,
            error=str(e)
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=standard_response(
            success=False,
            error=exc.detail
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=standard_response(
            success=False,
            error=f"Internal server error: {str(exc)}"
        )
    )


# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Starting EmailPilot Simple API on port {port}")

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
