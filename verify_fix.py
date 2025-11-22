import sys
import inspect
from fastapi.testclient import TestClient
from api import app
from data.review_state_manager import ReviewStateManager

def verify_changes():
    print("🔍 Verifying changes...")
    
    # 1. Check ReviewStateManager
    print("\n1. Checking ReviewStateManager...")
    if hasattr(ReviewStateManager, 'update_review_data'):
        print("✅ ReviewStateManager.update_review_data exists")
        sig = inspect.signature(ReviewStateManager.update_review_data)
        print(f"   Signature: {sig}")
    else:
        print("❌ ReviewStateManager.update_review_data MISSING")
        return False

    # 2. Check API Endpoint
    print("\n2. Checking API Endpoint...")
    client = TestClient(app)
    
    # We expect 503 because ReviewStateManager is not initialized in the test app state
    # or 404 if the endpoint doesn't exist.
    # But TestClient startup might fail if env vars are missing.
    
    # Let's just check the app routes
    routes = [route.path for route in app.routes]
    target_route = "/api/reviews/{workflow_id}/calendar"
    
    if target_route in routes:
        print(f"✅ Endpoint {target_route} exists")
        
        # Find the route object to check method
        for route in app.routes:
            if route.path == target_route:
                methods = route.methods
                if "PUT" in methods:
                    print("✅ Endpoint supports PUT method")
                else:
                    print(f"❌ Endpoint does not support PUT (found {methods})")
                    return False
    else:
        print(f"❌ Endpoint {target_route} MISSING")
        print("Available routes:", routes)
        return False

    print("\n✅ Verification Successful!")
    return True

if __name__ == "__main__":
    try:
        success = verify_changes()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification failed with exception: {e}")
        sys.exit(1)
