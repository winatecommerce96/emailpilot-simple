#!/usr/bin/env python3
"""
Verification script for HITL (Human-in-the-Loop) Workflow.
Uses FastAPI TestClient to verify endpoints without running a full server.
Mocks CalendarAgent to avoid LLM calls.
"""

import os
import sys
import json
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock environment variables before importing api
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["MCP_AUTH_TOKEN"] = "test-token"

# Mock dependencies that api.py imports
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.secretmanager"] = MagicMock()
sys.modules["google.cloud.firestore"] = MagicMock()

# Patch NativeMCPClient to avoid spawning processes
with patch("data.native_mcp_client.NativeMCPClient") as MockNativeMCP:
    # Configure the mock to return an async context manager
    mock_instance = AsyncMock()
    mock_instance.__aenter__.return_value = mock_instance
    mock_instance.__aexit__.return_value = None
    MockNativeMCP.return_value = mock_instance
    
    # Import api after mocking
    from api import app, app_state

# Create TestClient
client = TestClient(app)

def test_hitl_workflow():
    print("\n=== Starting HITL Workflow Verification ===")
    
    # 1. Initialize App State (simulate startup)
    print("\n1. Initializing App State...")
    app_state['initialized'] = True
    
    # Mock CalendarAgent
    mock_agent = MagicMock()
    app_state['calendar_agent'] = mock_agent
    
    # Mock run_workflow_with_checkpoint
    workflow_id = "test_workflow_123"
    mock_agent.run_workflow_with_checkpoint = AsyncMock(return_value={
        "success": True,
        "workflow_id": workflow_id,
        "review_url": f"http://localhost:8000/review/{workflow_id}",
        "message": "Calendar generated and saved for review"
    })
    
    # Mock resume_workflow
    mock_agent.resume_workflow = AsyncMock(return_value={
        "success": True,
        "workflow_id": workflow_id,
        "briefs": "Generated Briefs Content",
        "message": "Workflow completed successfully"
    })
    
    # Mock ReviewStateManager (which is used inside api.py endpoints)
    # We need to patch where it's used in api.py
    with patch("api.ReviewStateManager") as MockReviewManager:
        mock_review_manager = MockReviewManager.return_value
        mock_review_manager.save_review_state.return_value = True
        mock_review_manager.update_calendar.return_value = True
        mock_review_manager.update_status.return_value = True
        
        # 2. Start Workflow (Checkpoint)
        print("\n2. Starting Workflow (Checkpoint)...")
        response = client.post("/api/workflows/checkpoint", json={
            "clientName": "rogue-creamery",
            "startDate": "2025-01-01",
            "endDate": "2025-01-31",
            "userInstructions": "Focus on cheese."
        })
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 200
        job_data = response.json()["data"]
        job_id = job_data["job_id"]
        print(f"Job ID: {job_id}")
        
        # Note: The background task won't run automatically in TestClient unless we trigger it
        # But for this test, we are mainly testing the endpoints.
        # Let's manually simulate the background task completion by setting the state
        app_state['workflow_status'][job_id] = {
            "status": "pending_review",
            "workflow_id": workflow_id,
            "review_url": f"http://localhost:8000/review/{workflow_id}"
        }
        
        # 3. Get Review Status
        print("\n3. Checking Status...")
        response = client.get(f"/api/workflows/status/{job_id}")
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "pending_review"
        
        # 4. Update Calendar (Push Back)
        print("\n4. Updating Calendar (Push Back)...")
        updated_calendar = {"campaigns": [{"id": "1", "name": "Updated Campaign"}]}
        response = client.put(f"/api/reviews/{workflow_id}/calendar", json={
            "detailed_calendar": updated_calendar
        })
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 200
        
        # Verify ReviewStateManager.update_calendar was called
        mock_review_manager.update_calendar.assert_called_once()
        
        # 5. Approve Workflow
        print("\n5. Approving Workflow...")
        response = client.post(f"/api/reviews/{workflow_id}/approve", json={
            "reviewer_id": "user_test"
        })
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 200
        
        # Verify ReviewStateManager.update_status was called
        mock_review_manager.update_status.assert_called_with(workflow_id, "approved", "user_test")
        
        # 6. Resume Workflow
        print("\n6. Resuming Workflow...")
        response = client.post(f"/api/workflows/resume/{workflow_id}")
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 200
        
        # Verify CalendarAgent.resume_workflow was called
        mock_agent.resume_workflow.assert_called_with(workflow_id)
        
    print("\n=== HITL Workflow Verification Successful ===")

if __name__ == "__main__":
    try:
        test_hitl_workflow()
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
