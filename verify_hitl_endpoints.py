#!/usr/bin/env python3
"""
Simplified HITL Workflow Verification.
Tests the HITL endpoints by checking they exist and have correct signatures.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set required env vars
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
os.environ["ANTHROPIC_API_KEY"] = "test-key"

def test_hitl_endpoints():
    """Verify HITL endpoints exist in api.py"""
    print("\n=== HITL Endpoint Verification ===\n")
    
    # Read api.py and check for required endpoints
    api_file = Path(__file__).parent / "api.py"
    with open(api_file, 'r') as f:
        api_content = f.read()
    
    # Check for required endpoints
    endpoints = {
        "Checkpoint Workflow": '@app.post("/api/workflows/checkpoint")',
        "Update Calendar": '@app.put("/api/reviews/{workflow_id}/calendar")',
        "Approve Workflow": '@app.post("/api/reviews/{workflow_id}/approve")',
        "Resume Workflow": '@app.post("/api/workflows/resume/{workflow_id}")',
        "Get Status": '@app.get("/api/workflows/status/{job_id}")'
    }
    
    print("Checking for HITL endpoints:")
    all_found = True
    for name, endpoint in endpoints.items():
        if endpoint in api_content:
            print(f"  ✅ {name}: {endpoint}")
        else:
            print(f"  ❌ {name}: {endpoint} NOT FOUND")
            all_found = False
    
    # Check for ReviewStateManager usage
    print("\nChecking ReviewStateManager integration:")
    if "from data.review_state_manager import ReviewStateManager" in api_content:
        print("  ✅ ReviewStateManager imported")
    else:
        print("  ❌ ReviewStateManager NOT imported")
        all_found = False
    
    # Check CalendarAgent has required methods
    print("\nChecking CalendarAgent methods:")
    agent_file = Path(__file__).parent / "agents" / "calendar_agent.py"
    with open(agent_file, 'r') as f:
        agent_content = f.read()
    
    methods = {
        "run_workflow_with_checkpoint": "async def run_workflow_with_checkpoint(",
        "resume_workflow": "async def resume_workflow("
    }
    
    for name, signature in methods.items():
        if signature in agent_content:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} NOT FOUND")
            all_found = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_found:
        print("✅ All HITL components verified!")
        print("\nNext steps:")
        print("1. Start the server: ./start_server.sh")
        print("2. Test checkpoint workflow:")
        print('   curl -X POST http://localhost:8001/api/workflows/checkpoint \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"clientName":"rogue-creamery","startDate":"2025-01-01","endDate":"2025-01-31"}\'')
        return 0
    else:
        print("❌ Some HITL components missing!")
        return 1

if __name__ == "__main__":
    sys.exit(test_hitl_endpoints())
