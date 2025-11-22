# SMS SLA Test Results - November 21, 2025

## Test Summary

**Test Date**: November 21, 2025  
**Client**: Christopher Bean Coffee (`chris-bean`)  
**Period**: January 1-31, 2026  
**SLA Requirement**: Minimum 4 emails + 3 SMS per month

---

## Test Execution History

### Test 1: Early Morning Success ✅
**Workflow ID**: `chris-bean_2026-01-01_20251121_063349`  
**Timestamp**: 2025-11-21 06:41:41  
**Result**: **PASSED**

```
✅ SLA Compliance: Email 13/4, SMS 3/3
```

**Campaign Breakdown**:
- Total Campaigns: 16
- Email Campaigns: 13
- SMS Campaigns: 3 ✅
- **SLA Met**: YES

**Status**: This test demonstrates that the SMS generation fix CAN work correctly.

---

### Test 2: Mid-Morning Regression ❌
**Workflow ID**: `chris-bean_2026-01-01_20251121_080204`  
**Timestamp**: 2025-11-21 08:10:17  
**Result**: **FAILED**

```
❌ SLA VIOLATION: Generated 1 SMS campaigns but SLA requires minimum 3
```

**Campaign Breakdown**:
- Total Campaigns: 14
- Email Campaigns: 13
- SMS Campaigns: 1 ❌
- **SLA Met**: NO

**Error**:
```
ValueError: ❌ SLA VIOLATION: Generated 1 SMS campaigns but SLA requires minimum 3
```

**Status**: This test shows a regression - the same workflow that worked earlier now fails.

---

## Root Cause Analysis

### Hypothesis 1: Non-Deterministic LLM Behavior
The LLM (Claude Sonnet 4.5) is not consistently following the prompt instructions despite:
- Few-shot examples with SMS campaigns
- Explicit SLA requirements in the prompt
- Negative constraints against SMS variants
- Pre-generation checklist

**Evidence**: Same prompt, same client, same date range → Different results

### Hypothesis 2: Prompt Not Strong Enough
While the prompt has been strengthened, the LLM may still be:
- Treating SMS as optional
- Prioritizing email campaigns
- Not fully understanding the mandatory nature of SMS SLA

### Hypothesis 3: Temperature/Randomness
The LLM's temperature setting may be too high, causing inconsistent outputs.

### Hypothesis 4: Context Window Issues
With all the RAG data, MCP data, and examples, the prompt may be too long, causing the LLM to:
- Miss critical instructions
- Forget the SMS requirement by the time it generates the calendar
- Prioritize earlier context over later requirements

---

## What's Working

✅ **SLA Validation Logic**: Correctly detects when SMS count is insufficient  
✅ **Client ID Resolution**: Successfully maps `chris-bean` → `christopher-bean-coffee`  
✅ **SLA Fetching**: Retrieves correct SLA requirements (4 emails, 3 SMS)  
✅ **RAG Integration**: Successfully fetches 7/7 categories of brand data  
✅ **MCP Integration**: Fetches segments, campaigns, and flows  
✅ **Error Handling**: Workflow fails gracefully with clear error message  

---

## What's NOT Working

❌ **Consistent SMS Generation**: LLM generates 1-3 SMS campaigns unpredictably  
❌ **Prompt Adherence**: LLM doesn't consistently follow SMS requirements  
❌ **Deterministic Behavior**: Same inputs produce different outputs  

---

## Recommendations

### Immediate Actions

#### 1. **Lower LLM Temperature**
Reduce temperature to increase determinism:
```python
# In calendar_agent.py
temperature=0.3  # Currently might be higher
```

#### 2. **Add Explicit SMS Count Check in Prompt**
Add a final validation step in the planning prompt:
```yaml
BEFORE YOU OUTPUT THE CALENDAR:
1. Count the number of campaigns with campaign_type: "sms"
2. If count < 3, ADD MORE SMS CAMPAIGNS until you have exactly 3
3. Verify: Do you have 3 SMS campaigns? If NO, go back to step 2
```

#### 3. **Separate SMS Generation Stage**
Create a dedicated Stage 1.5 for SMS generation:
- Stage 1: Generate email campaigns
- Stage 1.5: Generate required SMS campaigns (separate LLM call)
- Stage 2: Structure and combine

#### 4. **Use Structured Output (Tool Use)**
Instead of asking the LLM to output JSON, use Claude's tool use feature to enforce structure:
```python
tools = [{
    "name": "create_calendar",
    "parameters": {
        "campaigns": {
            "type": "array",
            "minItems": 7,  # 4 emails + 3 SMS
            "items": {
                "campaign_type": {"enum": ["email", "sms"]}
            }
        }
    }
}]
```

#### 5. **Post-Generation SMS Injection**
If LLM fails to generate enough SMS, automatically inject SMS campaigns:
```python
def ensure_sms_compliance(calendar_json, sms_required):
    sms_count = count_sms_campaigns(calendar_json)
    if sms_count < sms_required:
        # Generate missing SMS campaigns using a separate, focused prompt
        missing_sms = sms_required - sms_count
        inject_sms_campaigns(calendar_json, missing_sms)
```

### Medium-Term Improvements

1. **Fine-tune Model**: Fine-tune Claude on SMS campaign examples
2. **Prompt Optimization**: A/B test different prompt structures
3. **Validation Loop**: If SLA fails, retry with stronger prompt
4. **SMS Templates**: Provide pre-built SMS templates for common scenarios

---

## Next Steps

### Option A: Quick Fix (Post-Generation Injection)
1. Implement SMS injection logic in `calendar_agent.py`
2. If SLA validation fails, automatically add missing SMS campaigns
3. Re-validate and save

**Pros**: Guaranteed to meet SLA  
**Cons**: SMS campaigns may be lower quality (not integrated into strategy)

### Option B: Retry with Stronger Prompt
1. If SLA validation fails, retry Stage 1 with enhanced prompt
2. Enhanced prompt explicitly states: "YOU FAILED TO GENERATE ENOUGH SMS. TRY AGAIN."
3. Limit to 2-3 retries

**Pros**: Better quality SMS campaigns  
**Cons**: Higher cost, longer execution time

### Option C: Separate SMS Stage
1. Implement Stage 1.5 for dedicated SMS generation
2. Use a focused prompt that ONLY generates SMS campaigns
3. Merge with email campaigns in Stage 2

**Pros**: Most reliable, best quality  
**Cons**: More complex workflow, higher cost

---

## Recommended Approach

**Implement Option A (Quick Fix) + Option C (Long-term)**

### Phase 1: Immediate (Today)
- Implement post-generation SMS injection as a safety net
- This ensures SLA is always met

### Phase 2: Next Week
- Implement separate SMS generation stage
- Disable injection once SMS stage is proven reliable

---

## Test Data

### Successful Run (06:41:41)
- Planning output: ~30KB
- Structured calendar: ~77KB
- Total campaigns: 16 (13 email + 3 SMS)
- SLA: PASSED

### Failed Run (08:10:17)
- Planning output: ~30KB (similar size)
- Structured calendar: ~83KB
- Total campaigns: 14 (13 email + 1 SMS)
- SLA: FAILED

**Observation**: Similar planning output size suggests similar prompt execution, but different SMS generation results.

---

## Conclusion

The SMS generation fix has been **partially successful**:
- ✅ It CAN generate the required 3 SMS campaigns
- ❌ It does NOT consistently generate 3 SMS campaigns

**Root Cause**: LLM non-determinism  
**Recommended Fix**: Post-generation SMS injection (Option A)  
**Long-term Solution**: Separate SMS generation stage (Option C)

**Status**: 🟡 **PARTIAL SUCCESS** - Requires additional safety mechanisms

---

**Test Conducted By**: Antigravity AI  
**Date**: November 21, 2025  
**Next Test**: After implementing Option A (SMS injection)
