import httpx
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

async def test_rag():
    url = "https://emailpilot-orchestrator-935786836546.us-central1.run.app/api/rag/enhanced/retrieve"
    payload = {
        "client_id": "rogue-creamery",
        "query": "test",
        "top_k": 1,
        "min_relevance": 0.3
    }
    
    print(f"Testing POST to {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag())
