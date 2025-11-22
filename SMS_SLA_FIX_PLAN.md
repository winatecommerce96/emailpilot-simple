# SMS SLA Fix Implementation Plan

## Objective
Ensure the EmailPilot workflow correctly generates standalone SMS campaigns when required by the Client SLA (e.g., "3 SMS per month"), and validates this compliance before finalizing the calendar.

## Diagnosis
1.  **Validation Failure**: The SLA validation logic was skipping checks because it couldn't match the client name `chris-bean` to the canonical ID `christopher-bean-coffee` where the metadata (SLA) is stored.
2.  **Generation Failure**: The LLM was failing to generate standalone SMS campaigns because the prompt schemas (both Planning and Structuring) explicitly restricted `campaign_type` to a specific list (promotional, educational, etc.) that *excluded* "sms". This forced the LLM to treat SMS only as a "variant" of email campaigns, which the structuring stage then collapsed into email-only events.

## Implemented Fixes

### 1. Fix Validation Logic (`agents/calendar_agent.py`)
-   **Change**: Updated `_validate_sla_compliance` and the calling logic in `run_checkpoint_workflow`.
-   **Detail**: Added a step to resolve the canonical client ID (e.g., `chris-bean` -> `christopher-bean-coffee`) via the API before looking up SLA requirements.
-   **Status**: ✅ Implemented. Verified via unit test that validation now correctly fails when SMS count is 0.

### 2. Update Planning Prompt (`prompts/planning_v5_1_0.yaml`)
-   **Change**: Updated the JSON schema definitions.
-   **Detail**: 
    -   Added `"sms": "number"` to the `campaign_mix` object.
    -   Added `sms` to the allowed values for `campaign_type`.
-   **Status**: ✅ Implemented.

### 3. Update Structuring Prompt (`prompts/calendar_structuring_v1_2_2.yaml`)
-   **Change**: Updated the "CRITICAL RULES" and schema instructions.
-   **Detail**:
    -   Explicitly added `"sms"` to the allowed `type` list.
    -   Added instructions for **STANDALONE SMS**: "Use 'channel': 'sms' and 'type': 'sms' for SMS-only campaigns".
    -   Clarified that each event can be an email campaign OR a standalone SMS campaign.
-   **Status**: ✅ Implemented.

### 4. Update Format Adapter (`tools/format_adapter.py`)
-   **Change**: Updated `TYPE_MAPPING`.
-   **Detail**: Added mapping `'sms': 'sms'` to ensure the app correctly interprets the new campaign type.
-   **Status**: ✅ Implemented.

## Verification Plan

We will execute the following steps to verify the fix:

1.  **Restart Server**: Ensure all code and prompt changes are loaded. (✅ Done)
2.  **Run Workflow**: Execute `run_jan_2026_workflow.py` for `chris-bean`. (✅ Done, Running)
3.  **Monitor Logs**:
    -   Confirm "Resolved client ID for SLA check: chris-bean -> christopher-bean-coffee". (Pending)
    -   Confirm "Found SLA requirements... sms_sla=3". (✅ Confirmed in logs)
    -   Confirm "SLA Validation passed" (or failed if generation is still broken). (Pending)
4.  **Inspect Output**:
    -   Check `simplified_calendar.json` to verify it contains events with `type: "sms"`. (Pending)

## Next Steps
Upon user approval, we will proceed with the **Verification Plan**.
