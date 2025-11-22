import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_clients_api(client_slug="chris-bean"):
    try:
        print(f"Fetching clients from https://emailpilot.ai/api/clients...")
        response = httpx.get("https://emailpilot.ai/api/clients", timeout=10.0)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return

        clients = response.json()
        print(f"Found {len(clients)} clients.")
        
        # Debug matching logic
        print(f"\nDebugging matching for '{client_slug}':")
        
        # 1. Exact match
        for client in clients:
            c_id = client.get("id")
            c_slug = client.get("slug")
            if c_id == client_slug or c_slug == client_slug:
                print(f"✅ Exact match found: {c_id}")
                return c_id
        
        print("❌ No exact match found.")
        
        # 2. Partial match
        slug_parts = client_slug.lower().replace("-", " ").replace("_", " ").split()
        print(f"Slug parts: {slug_parts}")
        
        for client in clients:
            client_id = client.get("id", "").lower()
            if all(part in client_id for part in slug_parts):
                print(f"✅ Partial match found: {client.get('id')}")
                return client.get("id")
        
        print("❌ No partial match found.")
        
        # List all available IDs for reference
        print("\nAvailable Client IDs:")
        for client in clients:
            print(f"- {client.get('id')}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_clients_api()
