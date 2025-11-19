#!/usr/bin/env python3
"""
Phase 4 Task 5: Verify Frontend Integration

This script simulates the frontend integration tests by:
1. Verifying API endpoint accessibility
2. Checking JSON structure and required fields
3. Validating data types and formats
4. Confirming frontend-ready data structure
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8008"
API_ENDPOINT = f"{BASE_URL}/api/calendar/strategy-summary"
TEST_CLIENT = "rogue-creamery"
STATIC_FILES = [
    "/static/js/strategy-summary-api.js",
    "/static/js/strategy-summary-component.js",
    "/static/js/strategy-summary-types.js",
    "/static/css/strategy-summary.css"
]

def print_header(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)

def test_api_endpoint():
    """Test 1: Verify API endpoint is accessible and returns data"""
    print_header("TEST 1: API Endpoint Accessibility")

    try:
        url = f"{API_ENDPOINT}/{TEST_CLIENT}"
        print(f"Fetching: {url}")

        response = requests.get(url, timeout=10)
        print(f"✓ HTTP Status: {response.status_code}")

        if response.status_code == 200:
            print("✓ API endpoint accessible")
            return True, response.json()
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"✗ Error: {e}")
        return False, None

def test_json_structure(data):
    """Test 2: Verify JSON structure and required fields"""
    print_header("TEST 2: JSON Structure Validation")

    required_fields = [
        'client_id',
        'start_date',
        'end_date',
        'key_insights',
        'targeting_approach',
        'timing_strategy',
        'content_strategy',
        'created_at',
        'updated_at',
        'generated_by',
        'event_count'
    ]

    missing_fields = []
    for field in required_fields:
        if field in data:
            print(f"✓ Field present: {field}")
        else:
            print(f"✗ Field missing: {field}")
            missing_fields.append(field)

    if missing_fields:
        print(f"\n✗ Missing {len(missing_fields)} required fields")
        return False
    else:
        print(f"\n✓ All {len(required_fields)} required fields present")
        return True

def test_strategy_fields(data):
    """Test 3: Verify the 4 core strategy fields"""
    print_header("TEST 3: Strategy Fields Validation")

    strategy_fields = {
        'key_insights': list,
        'targeting_approach': str,
        'timing_strategy': str,
        'content_strategy': str
    }

    all_valid = True

    for field, expected_type in strategy_fields.items():
        value = data.get(field)

        if value is None:
            print(f"✗ {field}: Missing")
            all_valid = False
        elif not isinstance(value, expected_type):
            print(f"✗ {field}: Wrong type (expected {expected_type.__name__}, got {type(value).__name__})")
            all_valid = False
        elif expected_type == list and len(value) == 0:
            print(f"✗ {field}: Empty array")
            all_valid = False
        elif expected_type == str and len(value.strip()) == 0:
            print(f"✗ {field}: Empty string")
            all_valid = False
        else:
            if expected_type == list:
                print(f"✓ {field}: {len(value)} items")
            else:
                preview = value[:60] + "..." if len(value) > 60 else value
                print(f"✓ {field}: {preview}")

    return all_valid

def test_key_insights_detail(data):
    """Test 4: Verify key insights array structure"""
    print_header("TEST 4: Key Insights Detail")

    insights = data.get('key_insights', [])

    if not insights:
        print("✗ No insights found")
        return False

    print(f"✓ Found {len(insights)} key insights:")
    for i, insight in enumerate(insights, 1):
        if isinstance(insight, str) and len(insight) > 0:
            preview = insight[:70] + "..." if len(insight) > 70 else insight
            print(f"  {i}. {preview}")
        else:
            print(f"  ✗ Insight {i}: Invalid (not a non-empty string)")
            return False

    return True

def test_metadata_fields(data):
    """Test 5: Verify metadata fields"""
    print_header("TEST 5: Metadata Fields")

    all_valid = True

    # Client ID
    if data.get('client_id') == TEST_CLIENT:
        print(f"✓ client_id: {data['client_id']}")
    else:
        print(f"✗ client_id: Expected '{TEST_CLIENT}', got '{data.get('client_id')}'")
        all_valid = False

    # Event count
    event_count = data.get('event_count')
    if isinstance(event_count, int) and event_count > 0:
        print(f"✓ event_count: {event_count}")
    else:
        print(f"✗ event_count: Invalid (expected positive integer, got {event_count})")
        all_valid = False

    # Date range
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    if start_date and end_date:
        print(f"✓ date_range: {start_date} to {end_date}")
    else:
        print(f"✗ date_range: Missing dates")
        all_valid = False

    # Timestamps
    try:
        created = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        updated = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        print(f"✓ created_at: {created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"✓ updated_at: {updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    except Exception as e:
        print(f"✗ Timestamp parsing failed: {e}")
        all_valid = False

    # Model
    model = data.get('generated_by')
    if model:
        print(f"✓ generated_by: {model}")
    else:
        print(f"✗ generated_by: Missing")
        all_valid = False

    return all_valid

def test_static_files():
    """Test 6: Verify static files are accessible"""
    print_header("TEST 6: Static Files Accessibility")

    all_accessible = True

    for file_path in STATIC_FILES:
        url = f"{BASE_URL}{file_path}"
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {file_path}: HTTP 200")
            else:
                print(f"✗ {file_path}: HTTP {response.status_code}")
                all_accessible = False
        except Exception as e:
            print(f"✗ {file_path}: {e}")
            all_accessible = False

    return all_accessible

def test_test_page():
    """Test 7: Verify test page is accessible"""
    print_header("TEST 7: Test Page Accessibility")

    url = f"{BASE_URL}/static/test-strategy-summary.html"
    try:
        response = requests.head(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ Test page accessible: {url}")
            return True
        else:
            print(f"✗ Test page returned HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error accessing test page: {e}")
        return False

def test_404_handling():
    """Test 8: Verify API returns 404 for non-existent client"""
    print_header("TEST 8: 404 Handling")

    url = f"{API_ENDPOINT}/non-existent-client-12345"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 404:
            print(f"✓ API correctly returns 404 for non-existent client")
            return True
        else:
            print(f"✗ Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("\n" + "=" * 80)
    print("PHASE 4 TASK 5: FRONTEND INTEGRATION VERIFICATION")
    print("=" * 80)
    print(f"Target: {BASE_URL}")
    print(f"Test Client: {TEST_CLIENT}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Test 1: API endpoint
    results['api_endpoint'], data = test_api_endpoint()

    if results['api_endpoint'] and data:
        # Test 2: JSON structure
        results['json_structure'] = test_json_structure(data)

        # Test 3: Strategy fields
        results['strategy_fields'] = test_strategy_fields(data)

        # Test 4: Key insights
        results['key_insights'] = test_key_insights_detail(data)

        # Test 5: Metadata
        results['metadata'] = test_metadata_fields(data)
    else:
        print("\n⚠ Skipping data validation tests due to API failure")
        results['json_structure'] = False
        results['strategy_fields'] = False
        results['key_insights'] = False
        results['metadata'] = False

    # Test 6: Static files
    results['static_files'] = test_static_files()

    # Test 7: Test page
    results['test_page'] = test_test_page()

    # Test 8: 404 handling
    results['404_handling'] = test_404_handling()

    # Summary
    print_header("VERIFICATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")
    print("\nTest Results:")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")

    print("\n" + "=" * 80)

    if all(results.values()):
        print("✅ PHASE 4 TASK 5: PASSED")
        print("Frontend integration verified - all components ready for display")
    else:
        print("❌ PHASE 4 TASK 5: FAILED")
        print("Some integration tests failed")

    print("=" * 80 + "\n")

    return all(results.values())

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
