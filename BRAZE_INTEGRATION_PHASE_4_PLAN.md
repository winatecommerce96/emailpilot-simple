# Braze Integration - Phase 4 Implementation Plan

## Status Overview
**Phase 1 (ESP Detection):** ✅ Complete
**Phase 2 (Braze Server):** ✅ Complete
**Phase 3 (Data Normalization):** ✅ Complete
**Phase 4 (Prompt Integration):** ✅ Complete (Code & Prompt Updated)

## Changes Implemented

### 1. MCP Client (`data/mcp_client.py`)
- Added `_detect_esp_platform` to route requests based on client configuration.
- Added `_spawn_braze_server` to run `braze-mcp-server` via `uvx`.
- Added `_call_braze_tool` for JSON-RPC communication.
- Implemented `_fetch_braze_data` to retrieve Segments, Campaigns, Canvases (Flows), and Revenue.
- Added normalization methods to map Braze data to the unified schema.
- **Crucial Feature:** Added `_extract_braze_revenue_metrics` to handle Braze's lack of per-campaign revenue attribution by providing aggregate trends.

### 2. Calendar Agent (`agents/calendar_agent.py`)
- Updated `stage_1_planning` to:
    - Accept `user_instructions` (restoring missing feature).
    - Determine `esp_platform` from fetched data.
    - Inject `esp_platform_context` into prompt variables (handling Braze revenue limitations).
- Updated `run_workflow` to pass `user_instructions`.

### 3. Planning Prompt (`prompts/planning_v5_1_0.yaml`)
- Refactored `user_prompt` to use aggregated variables (`brand_intelligence`, `mcp_data`) instead of granular ones, matching the code structure.
- Added `user_instructions` section with "HIGHEST PRIORITY" warning.
- Added `esp_platform_context` section to guide the LLM on platform-specific constraints (e.g., Braze revenue).

## Verification Plan

### 1. Unit/Integration Testing
- **Test 1: Klaviyo Client (Regression)**
    - Run `test_workflow.py` for a Klaviyo client (e.g., `rogue-creamery`).
    - Verify `esp_platform` is "klaviyo".
    - Verify data fetching works as before.
- **Test 2: Braze Client (New)**
    - Run `test_workflow.py` for a Braze client (e.g., `philz-coffee` - need to mock or use real creds if available).
    - Verify `esp_platform` is "braze".
    - Verify `braze-mcp-server` spawns.
    - Verify prompt receives Braze context.

### 2. Manual Verification
- Check logs for "Spawning Braze MCP server".
- Check logs for "Using Braze MCP for...".
- Inspect generated calendar for Braze-specific nuances (e.g., aggregate revenue mentions).

## Rollback Plan
- All changes are staged for commit.
- If issues arise, revert to `master` branch state before these edits.
