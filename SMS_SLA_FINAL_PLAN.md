# SMS SLA Fix - Final Implementation Plan

## Problem Summary
The workflow was failing to generate the required number of SMS campaigns (SLA: 3 SMS/month) because:
1. **Stage 1 (Planning)**: LLM preferred creating SMS variants of email campaigns instead of standalone SMS campaigns, despite instructions.
2. **Stage 2 (Structuring)**: LLM was filtering out any standalone SMS campaigns that *were* generated because the prompt didn't explicitly handle JSON input or SMS preservation.

## Implemented Solution

### 1. Stage 1: Planning Prompt (`prompts/planning_v5_1_0.yaml`)
- **Few-Shot Examples**: Added complete JSON examples of calendars with standalone SMS campaigns.
- **Negative Constraint**: Added explicit instruction: `⛔ NEGATIVE CONSTRAINT: Do NOT count "sms_variant" towards this SLA.`
- **Schema Update**: Added `sms` to `campaign_mix` and `campaign_type` allowed values.
- **Pre-Generation Checklist**: Added a checklist forcing the LLM to verify SMS count before outputting.

### 2. Stage 2: Structuring Prompt (`prompts/calendar_structuring_v1_2_2.yaml`)
- **Input Handling**: Added instruction to handle JSON input directly (since Stage 1 now outputs JSON).
- **Preservation Rule**: Added `🚨 PRESERVE ALL SMS CAMPAIGNS` section to ensure SMS events are not dropped or converted.
- **Structure Definition**: Explicitly defined the JSON structure for SMS campaigns in the output.

### 3. Code Logic (`agents/calendar_agent.py`)
- **SLA Validation**: Fixed client ID resolution to correctly fetch SLA requirements.
- **Validation Logic**: Implemented strict counting of `campaign_type: "sms"` events against the SLA.

## Verification Plan
Running test workflow `chris-bean_2026-01-01` (Jan 2026).
Success criteria:
- Stage 1 output contains 3 events with `campaign_type: "sms"`.
- Stage 2 output preserves these 3 events.
- SLA validation passes (found 3 SMS campaigns).
- Final `simplified_calendar.json` contains 3 SMS events.

## Monitoring
Log file: `server_sms_fix_v3.log`
Workflow ID: `chris-bean_2026-01-01_20251121_XXXXXX`
