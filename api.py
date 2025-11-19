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
import uuid
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
from data.native_mcp_client import NativeMCPClient as MCPClient
from data.enhanced_rag_client import EnhancedRAGClient as RAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache
from data.secret_manager_client import SecretManagerClient
from data.review_state_manager import ReviewStateManager, ReviewStatus

# Load environment variables
load_dotenv()

# Configure logging
if os.getenv('ENVIRONMENT') == 'production':
    # Use Google Cloud Logging in production for DEBUG level support
    import google.cloud.logging
    client = google.cloud.logging.Client()
    client.setup_logging(log_level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("Cloud Logging configured for production with DEBUG level")
else:
    # Use basic logging for local development
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Basic logging configured for development with DEBUG level")

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


class JobResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str  # queued, stage-1, stage-2, stage-3, completed, failed
    client_name: str
    start_date: str
    end_date: str
    created_at: str
    updated_at: str
    current_stage: Optional[int] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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


class CheckpointWorkflowRequest(BaseModel):
    """Request model for checkpoint workflow execution (Stage 1-2 only)."""
    clientName: str
    startDate: str
    endDate: str


class ReviewUpdateRequest(BaseModel):
    """Request model for review approval/rejection."""
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


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

    # RAG base path - defaults to local rag directory, configurable via env var
    rag_base_path = os.getenv('RAG_BASE_PATH', './rag')
    rag_client = RAGClient(rag_base_path=rag_base_path)

    firestore_client = FirestoreClient(
        project_id=os.getenv('GOOGLE_CLOUD_PROJECT')
    )

    cache = MCPCache()

    # Initialize MCP client (async context manager)
    mcp_client = MCPClient(project_id=os.getenv('GOOGLE_CLOUD_PROJECT'))
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

    # Initialize StorageClient for production persistent storage
    storage_client = None
    if os.getenv('ENVIRONMENT') == 'production':
        try:
            from data.storage_client import StorageClient
            storage_client = StorageClient(
                project_id=os.getenv('GOOGLE_CLOUD_PROJECT')
            )
            logger.info("StorageClient initialized for production")
        except Exception as e:
            logger.warning(f"Failed to initialize StorageClient: {str(e)}")
    else:
        logger.info("Development mode - using local file storage only")

    # Initialize Calendar Tool
    output_dir = './outputs'
    calendar_tool = CalendarTool(
        calendar_agent=calendar_agent,
        output_dir=output_dir,
        validate_outputs=True,
        storage_client=storage_client
    )

    logger.info("CalendarTool initialized")

    # Store in global state
    app_state['calendar_agent'] = calendar_agent
    app_state['calendar_tool'] = calendar_tool
    app_state['mcp_client'] = mcp_client
    app_state['rag_client'] = rag_client
    app_state['cache'] = cache
    app_state['storage_client'] = storage_client

    # Initialize ReviewStateManager for review checkpoint workflow
    review_manager = ReviewStateManager(project_id=os.getenv('GOOGLE_CLOUD_PROJECT'))
    app_state['review_manager'] = review_manager
    logger.info("ReviewStateManager initialized")

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


# Background task functions
async def execute_workflow_background(
    job_id: str,
    client_name: str,
    start_date: str,
    end_date: str,
    calendar_tool: CalendarTool
):
    """
    Execute workflow in background and update job state.

    This function runs asynchronously after the HTTP response is returned,
    preventing Cloud Run timeout issues during long-running AI generation.
    """
    try:
        logger.info(f"Starting background workflow execution for job {job_id}")

        # Update status to stage-1
        app_state['workflow_status'][job_id]['status'] = 'stage-1'
        app_state['workflow_status'][job_id]['current_stage'] = 1
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()

        # Execute complete workflow
        result = await calendar_tool.run_workflow(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            save_outputs=True
        )

        # Check if workflow succeeded
        if result.get('success', False):
            # Update to completed
            app_state['workflow_status'][job_id]['status'] = 'completed'
            app_state['workflow_status'][job_id]['results'] = result
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.info(f"Workflow job {job_id} completed successfully")
        else:
            # Update to failed with error
            app_state['workflow_status'][job_id]['status'] = 'failed'
            app_state['workflow_status'][job_id]['error'] = result.get('error', 'Unknown error')
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.error(f"Workflow job {job_id} failed: {result.get('error')}")

    except Exception as e:
        # Update to failed on exception
        app_state['workflow_status'][job_id]['status'] = 'failed'
        app_state['workflow_status'][job_id]['error'] = str(e)
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
        logger.error(f"Workflow job {job_id} failed with exception: {str(e)}", exc_info=True)


async def execute_checkpoint_workflow_background(
    job_id: str,
    client_name: str,
    start_date: str,
    end_date: str,
    calendar_agent: 'CalendarAgent',
    review_manager: 'ReviewStateManager'
):
    """
    Execute checkpoint workflow (Stage 1-2) in background and save for review.

    This function runs asynchronously, executing Stage 1 (planning) and
    Stage 2 (calendar structuring), then saving the results to Firestore
    for manual review before Stage 3 (brief generation).
    """
    try:
        logger.info(f"Starting checkpoint workflow for job {job_id}")

        # Update status to stage-1
        app_state['workflow_status'][job_id]['status'] = 'stage-1'
        app_state['workflow_status'][job_id]['current_stage'] = 1
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()

        # Execute checkpoint workflow (Stage 1-2)
        result = await calendar_agent.run_workflow_with_checkpoint(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            review_manager=review_manager
        )

        # Check if workflow succeeded
        if result.get('success', False):
            # Update to pending_review status
            app_state['workflow_status'][job_id]['status'] = 'pending_review'
            app_state['workflow_status'][job_id]['workflow_id'] = result.get('workflow_id')
            app_state['workflow_status'][job_id]['results'] = result
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.info(f"Checkpoint workflow {job_id} completed, awaiting review")
        else:
            # Update to failed with error
            app_state['workflow_status'][job_id]['status'] = 'failed'
            app_state['workflow_status'][job_id]['error'] = result.get('error', 'Unknown error')
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.error(f"Checkpoint workflow {job_id} failed: {result.get('error')}")

    except Exception as e:
        # Update to failed on exception
        app_state['workflow_status'][job_id]['status'] = 'failed'
        app_state['workflow_status'][job_id]['error'] = str(e)
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
        logger.error(f"Checkpoint workflow {job_id} failed with exception: {str(e)}", exc_info=True)


async def execute_resume_workflow_background(
    job_id: str,
    workflow_id: str,
    calendar_agent: 'CalendarAgent',
    review_manager: 'ReviewStateManager'
):
    """
    Resume an approved workflow to execute Stage 3 (brief generation) in background.

    This function loads the approved Stage 1-2 outputs from Firestore and
    executes Stage 3 to generate campaign briefs.
    """
    try:
        logger.info(f"Starting resume workflow for job {job_id}, workflow {workflow_id}")

        # Update status to stage-3
        app_state['workflow_status'][job_id]['status'] = 'stage-3'
        app_state['workflow_status'][job_id]['current_stage'] = 3
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()

        # Load review state from Firestore
        review_state = review_manager.get_review_state(workflow_id)
        if not review_state:
            raise ValueError(f"Review state not found for workflow: {workflow_id}")

        # Verify review is approved
        if review_state.get('review_status') != ReviewStatus.APPROVED.value:
            raise ValueError(
                f"Review must be approved before resuming. Current status: {review_state.get('review_status')}"
            )

        # Execute Stage 3 using the resume method
        result = await calendar_agent.resume_workflow_from_review(
            review_state=review_state,
            workflow_id=workflow_id
        )

        # Check if workflow succeeded
        if result.get('success', False):
            # Update to completed status
            app_state['workflow_status'][job_id]['status'] = 'completed'
            app_state['workflow_status'][job_id]['results'] = result
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.info(f"Resume workflow {job_id} completed successfully")
        else:
            # Update to failed with error
            app_state['workflow_status'][job_id]['status'] = 'failed'
            app_state['workflow_status'][job_id]['error'] = result.get('error', 'Unknown error')
            app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
            logger.error(f"Resume workflow {job_id} failed: {result.get('error')}")

    except Exception as e:
        # Update to failed on exception
        app_state['workflow_status'][job_id]['status'] = 'failed'
        app_state['workflow_status'][job_id]['error'] = str(e)
        app_state['workflow_status'][job_id]['updated_at'] = datetime.utcnow().isoformat()
        logger.error(f"Resume workflow {job_id} failed with exception: {str(e)}", exc_info=True)


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
            # Generate unique job ID
            job_id = str(uuid.uuid4())

            # Initialize job state
            app_state['workflow_status'][job_id] = {
                'job_id': job_id,
                'status': 'queued',
                'client_name': client_name,
                'start_date': start_date,
                'end_date': end_date,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'current_stage': None,
                'results': None,
                'error': None
            }

            # Schedule background task (runs after response is sent)
            background_tasks.add_task(
                execute_workflow_background,
                job_id,
                client_name,
                start_date,
                end_date,
                calendar_tool
            )

            logger.info(f"Created workflow job {job_id} for {client_name}")

            # Return job ID immediately
            return standard_response(
                success=True,
                data={
                    'job_id': job_id,
                    'status': 'queued',
                    'message': 'Workflow started in background. Poll /api/jobs/{job_id} for status.'
                }
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


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status and results for a workflow job.

    Poll this endpoint after receiving a job_id from POST /api/workflow/run
    to check job status and retrieve results when completed.

    Returns:
        - status: queued, stage-1, stage-2, stage-3, completed, failed
        - current_stage: Current stage number (1-3) or None
        - results: Full workflow results when status=completed
        - error: Error message when status=failed
    """
    if job_id not in app_state['workflow_status']:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job_data = app_state['workflow_status'][job_id]

    return standard_response(
        success=True,
        data=job_data
    )


# Review endpoints
@app.post("/api/workflows/checkpoint", status_code=202)
async def checkpoint_workflow(request: CheckpointWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Execute checkpoint workflow (Stage 1-2 only) and save for manual review.

    This endpoint starts a workflow that executes Stage 1 (planning) and
    Stage 2 (calendar structuring), then saves the results to Firestore
    for manual review before Stage 3 (brief generation).

    Returns a job_id for tracking the checkpoint workflow status.
    """
    # Verify required components
    if 'calendar_agent' not in app_state or app_state['calendar_agent'] is None:
        raise HTTPException(status_code=503, detail="CalendarAgent not initialized")

    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available for review state management")

    # Generate job ID
    job_id = f"{request.clientName}_{request.startDate}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Initialize job status
    app_state['workflow_status'][job_id] = {
        'job_id': job_id,
        'status': 'queued',
        'client_name': request.clientName,
        'start_date': request.startDate,
        'end_date': request.endDate,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'workflow_type': 'checkpoint'
    }

    # Start background task
    background_tasks.add_task(
        execute_checkpoint_workflow_background,
        job_id=job_id,
        client_name=request.clientName,
        start_date=request.startDate,
        end_date=request.endDate,
        calendar_agent=app_state['calendar_agent'],
        review_manager=app_state['review_manager']
    )

    return standard_response(
        success=True,
        data={
            'job_id': job_id,
            'message': 'Checkpoint workflow started (Stage 1-2). Results will be saved for review.',
            'status_url': f'/api/workflows/status/{job_id}'
        }
    )


@app.get("/api/reviews/pending")
async def list_pending_reviews(client_name: Optional[str] = None, limit: int = 50):
    """
    List workflows pending review.

    Query Parameters:
        client_name: Optional filter by client slug
        limit: Maximum number of results (default: 50, max: 100)

    Returns list of workflows awaiting manual review.
    """
    # Verify review manager
    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available")

    # Validate limit
    if limit > 100:
        limit = 100

    # Fetch pending reviews
    try:
        pending_reviews = app_state['review_manager'].list_pending_reviews(
            client_name=client_name,
            limit=limit
        )

        return standard_response(
            success=True,
            data={
                'count': len(pending_reviews),
                'reviews': pending_reviews
            }
        )
    except Exception as e:
        logger.error(f"Failed to list pending reviews: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reviews: {str(e)}")


@app.get("/api/reviews/{workflow_id}")
async def get_review_details(workflow_id: str):
    """
    Get detailed review state for a specific workflow.

    Path Parameters:
        workflow_id: Workflow identifier

    Returns full review state including planning output, calendar JSON,
    validation results, and review status.
    """
    # Verify review manager
    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available")

    # Fetch review state
    try:
        review_state = app_state['review_manager'].get_review_state(workflow_id)

        if not review_state:
            raise HTTPException(status_code=404, detail=f"Review not found: {workflow_id}")

        return standard_response(
            success=True,
            data=review_state
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review: {str(e)}")


@app.post("/api/reviews/{workflow_id}/approve")
async def approve_review(workflow_id: str, request: ReviewUpdateRequest):
    """
    Approve a workflow review.

    Path Parameters:
        workflow_id: Workflow identifier

    Request Body:
        reviewed_by: Optional email/ID of reviewer
        review_notes: Optional approval notes

    Marks the review as approved. The workflow can then be resumed
    via POST /api/workflows/resume/{workflow_id} to execute Stage 3.
    """
    # Verify review manager
    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available")

    # Verify review exists
    review_state = app_state['review_manager'].get_review_state(workflow_id)
    if not review_state:
        raise HTTPException(status_code=404, detail=f"Review not found: {workflow_id}")

    # Update review status to approved
    try:
        success = app_state['review_manager'].update_review_status(
            workflow_id=workflow_id,
            status=ReviewStatus.APPROVED,
            reviewed_by=request.reviewed_by,
            review_notes=request.review_notes
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update review status")

        return standard_response(
            success=True,
            data={
                'workflow_id': workflow_id,
                'review_status': 'approved',
                'message': 'Review approved. Use POST /api/workflows/resume/{workflow_id} to execute Stage 3.',
                'resume_url': f'/api/workflows/resume/{workflow_id}'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve review: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve review: {str(e)}")


@app.post("/api/reviews/{workflow_id}/reject")
async def reject_review(workflow_id: str, request: ReviewUpdateRequest):
    """
    Reject a workflow review.

    Path Parameters:
        workflow_id: Workflow identifier

    Request Body:
        reviewed_by: Optional email/ID of reviewer
        review_notes: Optional rejection reason/notes

    Marks the review as rejected. The workflow will not proceed to Stage 3.
    """
    # Verify review manager
    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available")

    # Verify review exists
    review_state = app_state['review_manager'].get_review_state(workflow_id)
    if not review_state:
        raise HTTPException(status_code=404, detail=f"Review not found: {workflow_id}")

    # Update review status to rejected
    try:
        success = app_state['review_manager'].update_review_status(
            workflow_id=workflow_id,
            status=ReviewStatus.REJECTED,
            reviewed_by=request.reviewed_by,
            review_notes=request.review_notes
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update review status")

        return standard_response(
            success=True,
            data={
                'workflow_id': workflow_id,
                'review_status': 'rejected',
                'message': 'Review rejected. Workflow will not proceed to Stage 3.'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject review: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reject review: {str(e)}")


@app.post("/api/workflows/resume/{workflow_id}", status_code=202)
async def resume_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """
    Resume an approved workflow to execute Stage 3 (brief generation).

    Path Parameters:
        workflow_id: Workflow identifier (must have approved review)

    Loads the approved Stage 1-2 outputs from Firestore and executes
    Stage 3 to generate campaign briefs.

    Returns a job_id for tracking the resume workflow status.
    """
    # Verify required components
    if 'calendar_agent' not in app_state or app_state['calendar_agent'] is None:
        raise HTTPException(status_code=503, detail="CalendarAgent not initialized")

    if 'review_manager' not in app_state or app_state['review_manager'] is None:
        raise HTTPException(status_code=503, detail="ReviewStateManager not initialized")

    if not app_state['review_manager'].is_available():
        raise HTTPException(status_code=503, detail="Firestore not available")

    # Verify review exists and is approved
    review_state = app_state['review_manager'].get_review_state(workflow_id)
    if not review_state:
        raise HTTPException(status_code=404, detail=f"Review not found: {workflow_id}")

    if review_state.get('review_status') != ReviewStatus.APPROVED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Review must be approved before resuming. Current status: {review_state.get('review_status')}"
        )

    # Generate job ID for resume
    job_id = f"{workflow_id}_resume_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Initialize job status
    app_state['workflow_status'][job_id] = {
        'job_id': job_id,
        'status': 'queued',
        'workflow_id': workflow_id,
        'workflow_type': 'resume',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    # Start background task for Stage 3
    background_tasks.add_task(
        execute_resume_workflow_background,
        job_id=job_id,
        workflow_id=workflow_id,
        calendar_agent=app_state['calendar_agent'],
        review_manager=app_state['review_manager']
    )

    return standard_response(
        success=True,
        data={
            'job_id': job_id,
            'workflow_id': workflow_id,
            'message': 'Resume workflow started (Stage 3 - brief generation).',
            'status_url': f'/api/workflows/status/{job_id}'
        }
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
    Retrieve workflow outputs from GCS or local files.

    Types:
    - planning: Campaign planning document
    - calendar-detailed: Detailed v4.0.0 format calendar (for brief generation)
    - calendar-simplified: Simplified upload format calendar
    - calendar-app: App-specific format calendar
    - calendar: All calendar files (backward compatibility)
    - briefs: Campaign briefs document
    """
    try:
        # Try GCS first if available (production)
        if app_state.get('storage_client'):
            logger.debug(f"Attempting to retrieve {output_type} from GCS")
            result = app_state['storage_client'].get_latest_output(output_type)

            if result:
                logger.info(f"Retrieved {output_type} from GCS: {result['filename']}")
                return standard_response(
                    success=True,
                    data={
                        "type": output_type,
                        "filename": result["filename"],
                        "content": result["content"],
                        "modified": result["modified"]
                    }
                )
            else:
                logger.debug(f"No {output_type} found in GCS")

        # Fallback to local file system (development)
        logger.debug(f"Attempting to retrieve {output_type} from local file system")
        outputs_dir = Path(__file__).parent / "outputs"

        if not outputs_dir.exists():
            logger.debug("No local outputs directory found")
            return standard_response(
                success=True,
                data={
                    "type": output_type,
                    "content": None,
                    "message": f"No {output_type} outputs found"
                }
            )

        # Find latest output file of the requested type
        if output_type == "planning":
            pattern = f"*_{output_type}_*.txt"
        elif output_type == "briefs":
            pattern = f"*_{output_type}_*.txt"
        elif output_type == "calendar-detailed":
            pattern = "*_calendar_detailed_*.json"
        elif output_type == "calendar-simplified":
            pattern = "*_calendar_simplified_*.json"
        elif output_type == "calendar-app":
            pattern = "*_calendar_app_*.json"
        elif output_type == "calendar":
            # Backward compatibility - matches any calendar file
            pattern = "*_calendar*.json"
        else:
            # Generic fallback
            pattern = f"*_{output_type}_*.*"

        output_files = list(outputs_dir.glob(pattern))

        if not output_files:
            logger.debug(f"No {output_type} files found locally")
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

        logger.info(f"Retrieved {output_type} from local file: {latest_file.name}")
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

    # Use reload only in development
    is_development = os.getenv('ENVIRONMENT', 'production') == 'development'

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=is_development,
        log_level="info"
    )
