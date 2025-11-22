import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data.review_state_manager import ReviewStateManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_sms(workflow_id):
    load_dotenv()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT not set")
        return

    logger.info(f"Analyzing workflow: {workflow_id}")
    
    try:
        manager = ReviewStateManager(project_id=project_id)
        state = manager.get_review_state(workflow_id)
        
        if not state:
            logger.error(f"No state found for workflow {workflow_id}")
            return

        # Analyze Planning Output
        planning = state.get('planning_output', '')
        if planning:
            sms_type_count = planning.lower().count('"campaign_type": "sms"')
            sms_channel_count = planning.lower().count('"channel": "sms"')
            sms_variant_count = planning.lower().count('"sms_variant"')
            
            print("\n--- Stage 1: Planning Analysis ---")
            print(f"Length: {len(planning)} chars")
            print(f"campaign_type: 'sms' count: {sms_type_count}")
            print(f"channel: 'sms' count: {sms_channel_count}")
            print(f"sms_variant count: {sms_variant_count}")
            
            # Check for specific SMS events
            if sms_type_count > 0:
                print("\nSMS Events found in Planning:")
                lines = planning.split('\n')
                for i, line in enumerate(lines):
                    if '"campaign_type": "sms"' in line.lower():
                        print(f"Line {i+1}: {line.strip()}")
        else:
            print("\n❌ No planning output found")

        # Analyze Structuring Output (Calendar JSON)
        calendar = state.get('calendar_json')
        if calendar:
            print("\n--- Stage 2: Structuring Analysis ---")
            events = calendar.get('events', [])
            print(f"Total events: {len(events)}")
            
            sms_events = [e for e in events if e.get('type') == 'sms' or e.get('channel') == 'sms']
            print(f"SMS Events found: {len(sms_events)}")
            
            for i, event in enumerate(sms_events):
                print(f"SMS Event {i+1}: {event.get('title', 'No Title')} (Type: {event.get('type')}, Channel: {event.get('channel')})")
        else:
            print("\n❌ No calendar JSON found (Stage 2 might not be complete)")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        workflow_id = sys.argv[1]
    else:
        # Default to the ID found in logs
        workflow_id = "chris-bean_2026-01-01_20251121_063349"
    
    analyze_sms(workflow_id)
