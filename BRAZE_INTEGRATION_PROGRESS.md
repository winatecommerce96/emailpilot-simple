# Braze MCP Integration - Progress Report

## ✅ Phase 1: Configuration & ESP Detection (COMPLETE)

### What's Implemented

**File**: `data/mcp_client.py`

1. **ESP Platform Detection** (`_detect_esp_platform`)
   - Fetches client data from `/clients` API
   - Reads `esp_platform` field ("klaviyo" or "braze")
   - Defaults to "klaviyo" if not specified or on error
   - Includes error handling and logging

2. **Braze Credentials Fetching** (`_get_braze_credentials`)
   - Fetches `braze_api_key`, `braze_base_url`, `braze_app_id` from `/clients` API
   - Validates credentials are present
   - Raises clear errors if credentials missing
   - Includes detailed logging

3. **ESP Routing in `fetch_all_data`**
   - Detects ESP platform for each client
   - Routes to `_fetch_klaviyo_data()` or `_fetch_braze_data()`
   - Adds `esp_platform` to result metadata
   - Maintains backward compatibility

4. **Klaviyo Data Fetching** (`_fetch_klaviyo_data`)
   - Extracted existing logic into dedicated method
   - No changes to functionality
   - Maintains all existing Klaviyo workflows

5. **Braze Data Fetching Stub** (`_fetch_braze_data`)
   - Placeholder method with TODO
   - Returns empty but valid data structure
   - Logs warning that full implementation pending

### Testing Status

✅ **Code compiles** (no syntax errors)  
✅ **Backward compatible** (existing Klaviyo clients unaffected)  
⏳ **Braze integration** (stub only, needs full implementation)  

---

## 🚧 Remaining Phases

### Phase 2: Braze MCP Server & Data Fetching (NOT STARTED)

**Estimated Time**: 3-4 hours

**Tasks**:
- [ ] Implement Braze MCP server spawning (`uvx --native-tls braze-mcp-server@latest`)
- [ ] Add Braze MCP tool calling infrastructure
- [ ] Fetch segments via `list_segments`
- [ ] Fetch campaigns via `list_campaigns`
- [ ] Fetch canvases (flows) via `list_canvases`
- [ ] Fetch revenue via `/purchases/revenue_series`
- [ ] Handle Braze API limitations (per-campaign revenue not available)

### Phase 3: Data Normalization (NOT STARTED)

**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Normalize Braze segments to Klaviyo format
- [ ] Normalize Braze campaigns to Klaviyo format
- [ ] Normalize Braze canvases to Klaviyo flows format
- [ ] Create aggregate revenue metrics handler
- [ ] Add data quality flags for attribution limitations

### Phase 4: Calendar Agent Updates (NOT STARTED)

**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Update `agents/calendar_agent.py` to handle ESP differences
- [ ] Add ESP-specific notes to formatted MCP data
- [ ] Handle revenue forecasting for Braze (aggregate only)

### Phase 5: Prompt Updates (NOT STARTED)

**Estimated Time**: 1 hour

**Tasks**:
- [ ] Update `prompts/planning_v5_1_0.yaml` with ESP-agnostic language
- [ ] Add Braze-specific guidance (revenue limitations)
- [ ] Update `prompts/calendar_structuring_v1_2_2.yaml` if needed

### Phase 6: Testing (NOT STARTED)

**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Unit tests for ESP detection
- [ ] Unit tests for Braze credential fetching
- [ ] Integration test with mock Braze client
- [ ] Verify Klaviyo clients still work
- [ ] Create `BRAZE_INTEGRATION.md` documentation

---

## Current System Behavior

### For Klaviyo Clients
✅ **Fully functional** - No changes to existing behavior  
✅ **ESP detected** as "klaviyo"  
✅ **All data fetching** works as before  

### For Braze Clients
⚠️ **Partially functional**:
- ✅ ESP detected as "braze"
- ✅ Credentials can be fetched
- ❌ Returns empty data (stub implementation)
- ❌ Calendar generation will fail (no data to work with)

---

## Next Steps

### Immediate (Phase 2)
1. Implement Braze MCP server spawning logic
2. Add Braze tool calling methods
3. Fetch actual Braze data (segments, campaigns, canvases, revenue)

### After Phase 2
4. Normalize Braze data to match Klaviyo format
5. Update calendar agent to handle ESP differences
6. Update prompts for ESP-agnostic language
7. Test end-to-end with both Klaviyo and Braze clients

---

##Files Modified

1. **`data/mcp_client.py`**
   - Added: `_detect_esp_platform()` method
   - Added: `_get_braze_credentials()` method
   - Modified: `fetch_all_data()` - now routes by ESP
   - Added: `_fetch_klaviyo_data()` method (extracted logic)
   - Added: `_fetch_braze_data()` stub method

**Total Lines Added**: ~180 lines  
**Total Lines Modified**: ~50 lines  

---

## Dependencies

### Required for Full Braze Support
- `braze-mcp-server` package (installed via `uvx`)
- Python >=3.12 (for Braze MCP server)
- `uv` package manager (for `uvx` command)

### Required Fields in `/clients` API
For Braze clients, these fields must be present:
```json
{
  "esp_platform": "braze",
  "braze_api_key": "...",
  "braze_base_url": "https://rest.iad-05.braze.com",
  "braze_app_id": "..." // optional
}
```

---

## Risk Assessment

### Low Risk ✅
- ESP detection logic
- Credential fetching
- Routing infrastructure
- Backward compatibility

### Medium Risk ⚠️
- Braze MCP server spawning (new subprocess management)
- Braze tool calling (different from Klaviyo MCP structure)
- Data normalization (format differences)

### High Risk ⛔
- Revenue attribution for Braze (API limitation, no workaround)
- Per-campaign metrics accuracy (may be incomplete)
- Error handling for Braze server failures

---

## Success Criteria for Next Phase

✅ Braze MCP server spawns successfully  
✅ Can call Braze MCP tools (`list_segments`, `list_campaigns`, etc.)  
✅ Data is fetched and returned in Braze format  
✅ No errors or crashes for Klaviyo clients  
✅ Clear logging shows which ESP is being used  

---

## Estimated Completion

**Phase 1**: ✅ Complete (2 hours)  
**Phases 2-6**: 🚧 9-14 hours remaining  
**Total**: 11-16 hours (as planned)

**Current Progress**: ~15% complete
