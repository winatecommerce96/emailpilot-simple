#!/usr/bin/env python3
"""
Test script to verify SMS generation stage integration.

This script tests:
1. Loading the SMS generation prompt
2. Checking calendar agent has stage_1_5_sms_generation method
3. Verifying the method signature is correct
"""

import sys
import inspect
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_sms_prompt_exists():
    """Test that SMS generation prompt file exists."""
    prompt_path = Path(__file__).parent / "prompts" / "sms_generation_v1_0_0.yaml"
    assert prompt_path.exists(), f"SMS prompt not found at {prompt_path}"
    print("✅ SMS generation prompt exists")
    
    # Check file size (should be ~9KB)
    size_kb = prompt_path.stat().st_size / 1024
    print(f"   Size: {size_kb:.1f} KB")
    return True

def test_calendar_agent_has_sms_method():
    """Test that CalendarAgent has stage_1_5_sms_generation method."""
    try:
        from agents.calendar_agent import CalendarAgent
        
        # Check method exists
        assert hasattr(CalendarAgent, 'stage_1_5_sms_generation'), \
            "CalendarAgent missing stage_1_5_sms_generation method"
        print("✅ CalendarAgent has stage_1_5_sms_generation method")
        
        # Check method signature
        method = getattr(CalendarAgent, 'stage_1_5_sms_generation')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        expected_params = [
            'self', 'client_name', 'start_date', 'end_date', 
            'workflow_id', 'email_campaigns_summary', 'sms_count_required'
        ]
        
        assert params == expected_params, \
            f"Method signature mismatch. Expected {expected_params}, got {params}"
        print(f"   Parameters: {', '.join(params[1:])}")  # Skip 'self'
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import CalendarAgent: {e}")
        return False

def test_structuring_method_signature():
    """Test that stage_2_structuring accepts sms_output parameter."""
    try:
        from agents.calendar_agent import CalendarAgent
        
        method = getattr(CalendarAgent, 'stage_2_structuring')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        assert 'sms_output' in params, \
            "stage_2_structuring missing sms_output parameter"
        print("✅ stage_2_structuring has sms_output parameter")
        
        # Check it's optional
        param = sig.parameters['sms_output']
        assert param.default is not inspect.Parameter.empty, \
            "sms_output should be optional with default value"
        print(f"   Default value: {param.default}")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import CalendarAgent: {e}")
        return False

def test_prompt_load():
    """Test that CalendarAgent can load the SMS prompt."""
    try:
        from agents.calendar_agent import CalendarAgent
        
        # Create a minimal agent instance (without actual clients)
        # We'll just test the load_prompt method
        agent = CalendarAgent.__new__(CalendarAgent)
        agent.prompts_dir = Path(__file__).parent / "prompts"
        
        # Test loading SMS prompt
        prompt_config = agent.load_prompt("sms_generation_v1_0_0.yaml")
        
        assert prompt_config is not None, "Failed to load SMS prompt"
        assert 'system_prompt' in prompt_config, "Missing system_prompt"
        assert 'user_prompt' in prompt_config, "Missing user_prompt"
        assert 'variables' in prompt_config, "Missing variables"
        
        print("✅ SMS prompt loads successfully")
        print(f"   Variables: {len(prompt_config['variables'])} defined")
        
        # Check for required variables
        var_names = [v['name'] for v in prompt_config['variables']]
        required_vars = ['client_name', 'sms_count_required', 'email_campaigns_summary']
        
        for var in required_vars:
            assert var in var_names, f"Missing required variable: {var}"
        
        print(f"   Required variables present: {', '.join(required_vars)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load prompt: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("SMS Generation Stage - Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("SMS Prompt File Exists", test_sms_prompt_exists),
        ("CalendarAgent Has SMS Method", test_calendar_agent_has_sms_method),
        ("Structuring Method Updated", test_structuring_method_signature),
        ("SMS Prompt Loads Correctly", test_prompt_load),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 60)
        try:
            result = test_func()
            results.append((test_name, result))
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            results.append((test_name, False))
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! SMS generation stage is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
