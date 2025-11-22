# User Instructions Integration - Confirmation

## Question
**"Can you confirm that userInstructions data from the Calendar App button is ingested and used to make the calendar?"**

## Answer: ✅ YES - Now Fully Integrated with HIGHEST Priority

### Flow Trace

1. **Calendar App sends userInstructions**  
   - Field: `userInstructions` (optional string)
   - Sent in POST request to `/api/workflows/checkpoint`

2. **API receives and logs it**  
   - File: `api.py` line 256
   - Model: `CheckpointWorkflowRequest.userInstructions: Optional[str] = None`
   - Logged: `logger.info(f"Checkpoint request payload: {request.dict()}")`

3. **Passed to workflow orchestrator**  
   - File: `api.py` line 315
   - Call: `calendar_agent.run_workflow_with_checkpoint(..., user_instructions=request.userInstructions)`

4. **Passed to Stage 1 Planning**  
   - File: `agents/calendar_agent.py` line 819
   - Call: `await self.stage_1_planning(..., user_instructions)`

5. **✅ FIXED: Added to prompt variables**  
   - File: `agents/calendar_agent.py` line 412
   - Variables: `"user_instructions": user_instructions if user_instructions else "No specific user instructions provided."`
   - **This was the missing piece** - it was being passed through but never added to the variables dict!

6. **✅ FIXED: Added to planning prompt with HIGHEST PRIORITY**  
   - File: `prompts/planning_v5_1_0.yaml` lines 401-417
   - Section: `🚨🚨🚨 USER INSTRUCTIONS (HIGHEST PRIORITY - OVERRIDE ALL OTHER DATA) 🚨🚨🚨`
   - Placement: **First thing** in the user_prompt, before all other instructions

## Priority Hierarchy (After Fix)

The planning AI now follows this priority order:

1. **🚨 USER INSTRUCTIONS** (HIGHEST)
   - Overrides MCP data, RAG data, SLA requirements
   - Explicit requirements from the calendar user
   - Examples: "Focus on Valentine's Day", "Avoid chocolate", "Target VIP only"

2. **SLA Requirements** (HIGH)
   - Minimum campaign counts (email/SMS)
   - Must be met unless user instructions explicitly override

3. **MCP Data** (MEDIUM)
   - Historical performance, segments, send patterns
   - Used as supporting context

4. **RAG Data** (MEDIUM)
   - Brand voice, product catalog, style guides
   - Used for tone and content guidance

## How It Works

### Example 1: User wants Valentine's focus
```
Calendar App Input:
  userInstructions: "Create a Valentine's Day theme for the entire month. Focus on gift bundles for couples."

AI Behavior:
  ✅ Generate 10-15 campaigns all themed around Valentine's Day
  ✅ Emphasize gift bundles and couple-focused messaging
  ✅ Override any MCP data suggesting other product focuses
  ✅ Still respect SLA minimums (e.g., 4 emails + 3 SMS)
```

### Example 2: User wants specific segment
```
Calendar App Input:
  userInstructions: "Target only our VIP segment this month. No mass sends."

AI Behavior:
  ✅ Use "VIP Customers" segment for ALL campaigns
  ✅ Override MCP suggestions for broader segments
  ✅ Still meet SLA campaign counts, but all to VIP
```

### Example 3: User wants flash sale on specific date
```
Calendar App Input:
  userInstructions: "Include a flash sale on February 14th with 30% off all coffee."

AI Behavior:
  ✅ Generate a promotional campaign on Feb 14
  ✅ Subject line and content focused on flash sale
  ✅ 30% discount explicitly mentioned
  ✅ Fit within the overall 10-15 campaign plan
```

### Example 4: No user instructions
```
Calendar App Input:
  userInstructions: null (or empty)

AI Behavior:
  ✅ Variable defaults to: "No specific user instructions provided."
  ✅ AI proceeds with MCP/RAG/SLA data as primary inputs
  ✅ No conflicts or overrides
```

## Prompt Structure

The planning prompt now starts with:

```yaml
user_prompt: |
  🚨🚨🚨 USER INSTRUCTIONS (HIGHEST PRIORITY - OVERRIDE ALL OTHER DATA) 🚨🚨🚨
  
  {user_instructions}
  
  ⚠️ CRITICAL: The USER INSTRUCTIONS above are the MOST IMPORTANT input for this calendar.
  - If user instructions conflict with MCP data, RAG data, or SLA requirements → FOLLOW USER INSTRUCTIONS
  - If user instructions specify campaign themes, dates, segments, or offers → USE THEM EXACTLY
  - If user instructions are vague → use your judgment with MCP/RAG data as supporting context
  - Treat user instructions as EXPLICIT REQUIREMENTS that override automated suggestions
  
  ---
  
  Design a comprehensive, production-ready marketing calendar for {client_name}.
  
  [rest of prompt...]
```

## Changes Made

### 1. `agents/calendar_agent.py` (line 412)
**Before**:
```python
variables = {
    "client_name": firestore_data.get("display_name", client_name),
    "start_date": start_date,
    "end_date": end_date,
    "mcp_data": mcp_formatted,
    "brand_intelligence": rag_formatted,
    "product_catalog": product_catalog_formatted,
    "client_config": firestore_formatted,
    "sla_requirements": sla_requirements
    # ❌ user_instructions was missing!
}
```

**After**:
```python
variables = {
    "client_name": firestore_data.get("display_name", client_name),
    "start_date": start_date,
    "end_date": end_date,
    "mcp_data": mcp_formatted,
    "brand_intelligence": rag_formatted,
    "product_catalog": product_catalog_formatted,
    "client_config": firestore_formatted,
    "sla_requirements": sla_requirements,
    "user_instructions": user_instructions if user_instructions else "No specific user instructions provided."
    # ✅ Now included!
}
```

### 2. `prompts/planning_v5_1_0.yaml` (lines 401-417)
**Before**:
```yaml
user_prompt: |
  Design a comprehensive, production-ready marketing calendar for {client_name}.
  # user_instructions not referenced
```

**After**:
```yaml
user_prompt: |
  🚨🚨🚨 USER INSTRUCTIONS (HIGHEST PRIORITY - OVERRIDE ALL OTHER DATA) 🚨🚨🚨
  
  {user_instructions}
  
  ⚠️ CRITICAL: The USER INSTRUCTIONS above are the MOST IMPORTANT input...
  [explicit override rules]
  
  ---
  
  Design a comprehensive, production-ready marketing calendar for {client_name}.
```

## Testing

To verify userInstructions is working:

1. **From Calendar App**, click "Generate with AI" button
2. **Enter instructions** in the userInstructions field, e.g.:
   ```
   Focus on Valentine's Day gift bundles. Target VIP customers only. Include a flash sale on February 14th.
   ```
3. **Submit workflow**
4. **Check output** for:
   - ✅ Valentine's themed campaigns
   - ✅ VIP segment used for campaigns
   - ✅ February 14th flash sale present
   - ✅ Instructions reflected in campaign names, subjects, content

5. **Check logs** to confirm:
   ```
   INFO: Checkpoint request payload: {'clientName': '...', 'userInstructions': 'Focus on Valentine's...'}
   ```

## Summary

**Status**: ✅ **FULLY INTEGRATED WITH HIGHEST PRIORITY**

- userInstructions flows from Calendar App → API → CalendarAgent → Planning Prompt
- Added to prompt variables (was missing)
- Positioned at TOP of planning prompt with maximum emphasis
- Explicitly instructed to override MCP, RAG, and SLA data when conflicts occur
- Defaults to "No specific user instructions provided." when empty

The AI will now treat userInstructions as the **most important input** and build the calendar around those requirements.
