import httpx
import asyncio
import json
import sys

async def run_workflow():
    url = "http://localhost:9000/api/workflows/checkpoint"
    payload = {
        "clientName": "chris-bean",
        "startDate": "2026-01-01",
        "endDate": "2026-01-31",
        "userInstructions": "Focus on post-holiday retention and new year resolutions. Ensure SLA requirements for SMS are met."
    }
    
    print(f"Triggering workflow for {payload['clientName']} ({payload['startDate']} to {payload['endDate']})...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print("\n✅ Workflow started successfully!")
                print(f"Response Data: {data}")
                job_id = data.get('data', {}).get('job_id')
                print(f"Workflow ID: {job_id}")
                print(f"Status: {data.get('data', {}).get('status')}")
                
                # Poll for completion (optional, but good for verification)
                workflow_id = job_id
                if workflow_id:
                    print(f"\nPolling status for workflow {workflow_id}...")
                    for _ in range(60):  # Poll for up to 5 minutes
                        status_url = f"http://localhost:9000/api/workflows/{workflow_id}"
                        status_resp = await client.get(status_url)
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            state = status_data.get("state")
                            print(f"Current state: {state}")
                            
                            if state == "WAITING_FOR_REVIEW":
                                print("\n🎉 Workflow reached WAITING_FOR_REVIEW state!")
                                print("You can now proceed to review the calendar.")
                                break
                            elif state == "FAILED":
                                print("\n❌ Workflow FAILED.")
                                print(f"Error: {status_data.get('error')}")
                                break
                        
                        await asyncio.sleep(5)
            else:
                print(f"\n❌ Failed to start workflow. Status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(run_workflow())
