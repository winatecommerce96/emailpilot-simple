# Calendar Output Quality Improvements

## Issues Identified

Based on the Christopher Bean Coffee February 2026 output, the following issues were identified:

1. **All events on Tuesday, Thursday, or Saturday only** - No day-of-week diversity
2. **No resends** - Despite prompt instructions to create them
3. **Segment "ALL" for every campaign** - Not using real Klaviyo segments
4. **Flat $5000 revenue for all campaigns** - Not calculated from real metrics
5. **Open rate 0.3%, Click rate 0.1%** - Percentage formatting error (should be 30% and 3%)
6. **No strategy data** - send_strategy field not populated in Calendar App

## Root Cause

**The structuring stage (Stage 2) was NOT receiving MCP data.** 

The `stage_2_structuring` method only passed:
- `planning_output` (markdown from Stage 1)
- `sms_output` (optional SMS campaigns)

But it was missing:
- **MCP segments** - No list of real Klaviyo segments to choose from
- **MCP performance metrics** - No open rates, click rates, AOV, conversion rates
- **MCP historical campaigns** - No send day patterns to learn from
- **RAG brand guidelines** - No brand voice/visual guidelines

Without this data, the AI defaulted to:
- Generic "All Subscribers" segment
- Arbitrary $5000 revenue
- Decimal rates (0.003) instead of percentages (30%)
- Clustering on 2-3 days
- Skipping resends

## Fixes Implemented

### 1. Updated `stage_2_structuring` Method  
**File**: `/agents/calendar_agent.py` (lines 514-608)

Now fetches and passes to the structuring prompt:
- **MCP data from cache** (already fetched in Stage 1)
- **Segment list** - Formatted list of all available Klaviyo segments with sizes
- **Performance metrics** - Extracted avg open rate, click rate, AOV, conversion rate (with percentage conversion fix)
- **Historical send day analysis** - Day-of-week distribution from past campaigns
- **Brand guidelines** - Voice, tone, visual style from RAG data
- **Revenue calculation formula** - Client-specific formula with real metrics

### 2. Added Helper Methods
**File**: `/agents/calendar_agent.py` (lines 1126-1334)

Four new methods:
- `_extract_segment_list()` - Formats MCP segments for prompt
- `_extract_performance_metrics()` - Extracts rates and AOV with **percentage conversion fix**
  - Converts decimals (0.003) to percentages (0.3%) by checking if value < 1
- `_analyze_historical_send_days()` - Analyzes past send day patterns and builds recommendations
- `_extract_brand_guidelines()` - Pulls brand voice/visual guidelines from RAG

### 3. Strengthened Structuring Prompt Rules
**File**: `/prompts/calendar_structuring_v1_2_2.yaml` (lines 42-89)

**Segment Targeting (lines 42-62)**:
- Changed header to "🚨 CRITICAL - ZERO TOLERANCE🚨"
- Made "All Subscribers" explicitly **FORBIDDEN** except for <10% of campaigns
- Required using **ONLY** segments from `{segment_list}` provided by MCP
- Added requirement to use AT LEAST 8 different segments if 15 are available
- Added concrete examples of good targeting

**Day-of-Week Distribution (lines 64-71)**:
- Added header "📊 USE HISTORICAL DATA 📊"
- Required **ANALYZING** the `{historical_send_days}` data
- Required **DIVERSIFYING** beyond historical patterns
- Made all 7 days mandatory (Mon-Sun)
- Added minimum 1 weekend send for consumer brands

**Resend Strategy (lines 73-89)**:
- Changed header to "🚨 MANDATORY - NOT OPTIONAL 🚨"
- Emphasized "YOU MUST CREATE RESENDS"
- Required resends for **EVERY** promotional/product_launch/seasonal campaign
- Added detailed specifications (timing, segment, revenue calculation)
- Added rationale template
- Added warning "⚠️ DO NOT SKIP RESENDS"

### 4. Percentage Conversion Fix
**File**: `/agents/calendar_agent.py` `_extract_performance_metrics()` method (lines 1192-1201)

```python
# Open rate - convert from decimal to percentage
if "avg_open_rate" in email_metrics:
    rate = email_metrics["avg_open_rate"]
    # Check if it's already a percentage (>1) or decimal (<1)
    metrics["avg_open_rate"] = rate if rate > 1 else rate * 100
```

This fixes the 0.3% issue - if the rate comes from Klaviyo as 0.30 (decimal), it's converted to 30% (percentage).

## Expected Improvements

With these fixes, the next workflow run should produce:

✅ **Diverse segments** - Using real Klaviyo segments like "VIP Customers", "Engaged Subscribers", "Lapsed 90 Days"  
✅ **Resend campaigns** - Automatically generated for all promotional campaigns (2-3 days after original)  
✅ **Day-of-week diversity** - Campaigns spread across Mon-Sun based on historical patterns  
✅ **Accurate revenue estimates** - Calculated using real open rates (30%), click rates (3%), AOV, conversion rates  
✅ **Proper performance metrics** - Open rates like 30%, not 0.3%  
✅ **Strategy data** - Overall send_strategy populated from planning output  

## Testing

To test these improvements:

1. **Clear the cache** (if needed) to force fresh MCP data fetch
2. **Trigger a new workflow** from the Calendar App for any client
3. **Check the output** for:
   - Variety of segments used (not "All")
   - Presence of resend events (should see `[RESEND]` prefix)
   - Send days distributed across Monday-Sunday
   - Revenue estimates varying by campaign (not flat $5000)
   - Open/click rates in normal range (20-40%, 2-5%)

## Next Steps

1. **Run a test workflow** for Christopher Bean Coffee or another client
2. **Verify the output** meets all 6 criteria above
3. **If issues persist**, check:
   - MCP data is being fetched correctly (check server logs)
   - Segments are in the `segment_list` variable
   - Performance metrics are extracted correctly
   - AI is following the strengthened prompt rules

## Files Modified

- `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/agents/calendar_agent.py`
  - Updated `stage_2_structuring` method (lines 514-608)
  - Added 4 helper methods (lines 1126-1334)

- `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/prompts/calendar_structuring_v1_2_2.yaml`
  - Strengthened segment targeting rules (lines 42-62)
  - Enhanced day-of-week distribution rules (lines 64-71)
  - Made resend strategy mandatory (lines 73-89)

## Strategy Field

Regarding the "Strategy" field not appearing in the Calendar App:

The `send_strategy` field is populated by the `CalendarFormatAdapter` in the `_extract_send_strategy` method. It looks for strategy in:
1. Calendar metadata (`metadata.send_strategy`)
2. Planning output text (extracts key sections)

**To enable strategy display**:
- The planning output from Stage 1 should contain sections like "Strategic Overview", "Key Objectives", "Send Cadence"
- The adapter will parse these and include them in the `send_strategy` object
- This object should contain: `period_overview`, `key_objectives`, `cadence_strategy`, `audience_strategy`

If the field is still not showing, check:
- The planning prompt is generating strategic sections
- The `_parse_planning_strategy` method is correctly extracting them
- The Calendar App is displaying the `send_strategy` field from the imported JSON
