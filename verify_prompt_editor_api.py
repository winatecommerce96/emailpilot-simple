#!/usr/bin/env python3
"""
Verification script for Prompt Editor API endpoints.
"""

import requests
import sys
import json
import time
from subprocess import Popen, PIPE
import os
import signal

# Configuration
API_URL = "http://localhost:9000"
PYTHON_CMD = ".venv/bin/python"

def start_server():
    """Start the API server in the background."""
    print("🚀 Starting API server...")
    env = os.environ.copy()
    env["PORT"] = "9000"
    process = Popen([PYTHON_CMD, "api.py"], stdout=PIPE, stderr=PIPE, env=env)
    
    # Wait for server to start
    print("⏳ Waiting for server to initialize...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_URL}/api/health")
            if response.status_code == 200:
                print("✅ Server is up and running!")
                return process
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        print(f"   ... waiting ({i+1}/{max_retries})")
    
    print("❌ Server failed to start.")
    process.kill()
    sys.exit(1)

def test_list_prompts():
    """Test listing prompts."""
    print("\n🧪 Testing GET /api/prompts...")
    try:
        response = requests.get(f"{API_URL}/api/prompts")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        prompts = data["data"]
        print(f"   Found {len(prompts)} prompts.")
        
        # Verify expected prompts exist
        prompt_names = [p["name"] for p in prompts]
        expected = ["sms_generation_v1_0_0", "calendar_structuring_v1_2_2"]
        for name in expected:
            if name in prompt_names:
                print(f"   ✅ Found expected prompt: {name}")
            else:
                print(f"   ❌ Missing expected prompt: {name}")
                return False
        return True
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def test_get_prompt(prompt_name):
    """Test getting a specific prompt."""
    print(f"\n🧪 Testing GET /api/prompts/{prompt_name}...")
    try:
        response = requests.get(f"{API_URL}/api/prompts/{prompt_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        content = data["data"]["content"]
        print(f"   ✅ Successfully retrieved prompt content ({len(content)} bytes).")
        return True
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def test_get_variables(prompt_name):
    """Test getting variables for a prompt."""
    print(f"\n🧪 Testing GET /api/prompts/{prompt_name}/variables...")
    try:
        response = requests.get(f"{API_URL}/api/prompts/{prompt_name}/variables")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        variables = data["data"]["variables"]
        print(f"   Found {len(variables)} variables.")
        
        # Check for specific variables
        var_names = [v["name"] for v in variables]
        if "client_name" in var_names:
            print("   ✅ Found 'client_name' variable")
        else:
            print("   ❌ Missing 'client_name' variable")
            return False
            
        return True
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def main():
    # Start server
    server_process = start_server()
    
    try:
        # Run tests
        success = True
        success &= test_list_prompts()
        success &= test_get_prompt("sms_generation_v1_0_0")
        success &= test_get_variables("sms_generation_v1_0_0")
        
        if success:
            print("\n🎉 All API tests passed!")
        else:
            print("\n⚠️ Some tests failed.")
            
    finally:
        # Cleanup
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
