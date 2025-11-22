# Few-Shot Learning Implementation for SMS SLA Compliance

## Approach
Implemented **Option 1: Few-Shot Examples** to teach the LLM how to generate standalone SMS campaigns.

## What Was Added

### Location
`prompts/planning_v5_1_0.yaml` - Lines 61-136

### Content
Added a complete JSON example showing:
- **Total campaigns**: 13 (10 emails + 3 SMS)
- **Campaign mix**: Explicitly shows `"sms": 3` in the mix
- **Event structure**: 3 complete SMS campaign examples with:
  - `campaign_type: "sms"` (the critical field)
  - Proper segment targeting
  - SMS message in `sms_variant` field
  - Content theme classification

### Key Takeaways Section
Added explicit bullet points reinforcing:
- SMS campaigns must have `campaign_type: "sms"`
- SMS campaigns are SEPARATE events (not variants of email campaigns)
- Each SMS campaign counts toward total_campaigns
- campaign_mix must include the SMS count

## Why This Should Work

### Pattern Matching
LLMs excel at pattern recognition. By showing a complete, working example, the LLM can:
1. See the exact JSON structure required
2. Understand how SMS campaigns fit into the overall calendar
3. Match the pattern when generating new calendars

### Concrete vs Abstract
Previous approach: Abstract instructions ("generate SMS campaigns")
New approach: Concrete example ("here's exactly what it looks like")

### Minimal Cost
- Added ~800 tokens to the prompt
- No additional API calls
- Single-pass generation (no retries needed)

## Testing

### Test Workflow
- Client: `chris-bean` (Christopher Bean Coffee)
- Period: January 2026
- SLA: 4 emails minimum, 3 SMS minimum
- Workflow ID: `chris-bean_2026-01-01_20251120_220924`

### Success Criteria
✅ Planning output contains 3 events with `campaign_type: "sms"`
✅ Structuring output maintains 3 SMS campaigns
✅ SLA validation passes
✅ Final calendar has 3 SMS campaigns

### Expected Timeline
- Stage 1 (Planning): ~2-3 minutes
- Stage 2 (Structuring): ~5-6 minutes
- Total: ~8-10 minutes

## Fallback Plan
If few-shot examples don't work, next steps:
1. Add a second example showing holiday month (15 campaigns with 3 SMS)
2. Move examples closer to the output schema section
3. Consider Option 2 (two-stage approach) as last resort
