# Universal Segments Integration

## Overview

The system now supports **two types of segments** for campaign targeting:

1. **Affinity Segments** (Client-Specific)
   - Unique to each client
   - Based on product preferences, purchase behavior, customer value
   - Example: "Flavored Coffee Lovers", "Decaf Enthusiasts", "Cold Brew Fans"

2. **Universal Segments** (Cross-Client)
   - Standard behavioral/demographic segments
   - Available for all clients
   - Example: "Active 30 Days", "VIP Customers", "Lapsed 90+ Days"

## Segment Layering

The AI can **combine multiple segments** using AND logic for precision targeting:

### Examples
- `"Flavored Coffee Lovers AND Active 30 Days"` → Engaged customers who love flavored coffee
- `"VIP Customers AND Lapsed 90 Days"` → High-value customers who haven't engaged recently (winback)
- `"Cold Brew Enthusiasts AND First-Time Buyers"` → New customers interested in cold brew
- `"Decaf Lovers AND Active 30 Days"` → Engaged decaf customers (for decaf promotions)

## Implementation Details

### 1. Data Source
**File**: `agents/calendar_agent.py` - `_extract_segment_list()` method

Fetches from `/clients` API:
```python
affinity_segments = client_data.get("affinity_segments", [])
universal_segments = client_data.get("universal_segments", [])
```

**Expected API Structure**:
```json
{
  "id": "christopher-bean-coffee",
  "affinity_segments": [
    {
      "name": "Flavored Coffee Lovers",
      "description": "Customers primarily interested in flavored coffee..."
    },
    {
      "name": "Decaf Flavored Coffee Lovers",
      "description": "Customers who prefer decaffeinated coffee..."
    }
  ],
  "universal_segments": [
    {
      "name": "Active Subscribers (30 days)",
      "description": "Opened or clicked in last 30 days",
      "use_cases": "High-engagement campaigns, new product launches"
    },
    {
      "name": "Lapsed Subscribers (90+ days)",
      "description": "No opens/clicks in 90+ days",
      "use_cases": "Win-back campaigns, re-engagement offers"
    },
    {
      "name": "VIP Customers (Top 10%)",
      "description": "Top 10% by lifetime revenue",
      "use_cases": "Exclusive offers, early access, premium content"
    }
  ]
}
```

### 2. Prompt Formatting
**File**: `agents/calendar_agent.py` - Lines 1164-1210

The segment list is formatted into two sections:

```
🎯 CLIENT-SPECIFIC AFFINITY SEGMENTS:

1. **Flavored Coffee Lovers**
   High CLV customers driven by new taste experiences...

2. **Decaf Flavored Coffee Lovers**
   High WinScore (766) customers seeking decaf options...

🌍 UNIVERSAL SEGMENTS (AVAILABLE FOR ALL CLIENTS):

1. **Active Subscribers (30 days)**
   Definition: Opened or clicked in last 30 days
   Use Cases: High-engagement campaigns, new products

2. **Lapsed Subscribers (90+ days)**
   Definition: No engagement in 90+ days
   Use Cases: Win-back campaigns, special offers

📋 SEGMENT TARGETING RULES:
1. ✅ USE client-specific affinity segments for product targeting
2. ✅ USE universal segments for behavioral targeting
3. ✅ LAYER segments for precision
4. ✅ Examples: 'VIP AND Lapsed' = High-value winback
5. ❌ DO NOT use 'All Subscribers' (<10% of campaigns)
6. 💡 TIP: Layer affinity + universal for best results
```

### 3. JSON Schema Update
**File**: `prompts/calendar_structuring_v1_2_2.yaml` - Lines 197-208

Updated the example to show layering:

```yaml
"audience": {
  "segment_name": "Flavored Coffee Lovers AND Active 30 Days",
  "segment_size": 8500,
  "targeting_rationale": "Combining affinity segment with behavioral..."
}

// SEGMENT LAYERING EXAMPLES:
// Single: "VIP Customers" 
// Layered: "VIP Customers AND Lapsed 90 Days"
// Layered: "Cold Brew Enthusiasts AND First-Time Buyers"
```

## Backward Compatibility

✅ **Gracefully handles missing `universal_segments` field**:
```python
if universal_segments:
    # Format universal segments
else:
    logger.info(f"No universal_segments in API yet (field may not be deployed)")
```

If `universal_segments` doesn't exist, the system:
- Still uses affinity segments
- Logs a message (not an error)
- Continues workflow normally

## Logging

The system logs segment extraction:
```
INFO: Extracted segments for christopher-bean-coffee: 3 affinity, 5 universal
```

Or if `universal_segments` not deployed yet:
```
INFO: No universal_segments in API yet (field may not be deployed)
INFO: Extracted segments for christopher-bean-coffee: 3 affinity, 0 universal
```

## Testing

### Before `universal_segments` is deployed
- ✅ System uses affinity segments only
- ✅ No errors, just logs "No universal_segments in API yet"
- ✅ Calendars generate normally

### After `universal_segments` is deployed
1. **Verify API Response**:
   ```bash
   curl https://emailpilot.ai/api/clients | jq '.[] | select(.id=="christopher-bean-coffee") | .universal_segments'
   ```

2. **Check Logs**:
   ```
   INFO: Extracted segments for christopher-bean-coffee: 3 affinity, 5 universal
   ```

3. **Verify Workflow Output**:
   - Campaigns should use layered segments
   - Examples: "Flavored Coffee Lovers AND Active 30 Days"
   - Targeting rationale should explain the layering logic

## Expected Behavior

### Without Universal Segments (Current State)
- Uses affinity segments only
- Segment names: "Flavored Coffee Lovers", "Decaf Lovers", etc.
- No layering (single segments only)

### With Universal Segments (After Deployment)
- Uses both affinity + universal
- Segment names can be layered: "Flavored Coffee Lovers AND Active 30 Days"
- More precision targeting
- Better explained rationale ("Combining affinity segment X with behavioral segment Y...")

## Benefits of Segment Layering

1. **Precision Targeting**: Reach exactly the right audience
   - "Flavored Coffee Lovers AND Lapsed 90 Days" = Winback for flavor customers
   - "VIP Customers AND Active 30 Days" = Most valuable engaged customers

2. **Better ROI**: Higher relevance = better performance
   - Layered segments typically have 20-30% higher engagement
   - More efficient ad spend (smaller, more targeted audiences)

3. **Strategic Flexibility**: Mix product affinity with behavior
   - Product-focused campaigns: Affinity segment only
   - Behavioral campaigns: Universal segment only
   - Hybrid campaigns: Layer both for maximum precision

## Universal Segment Schema (Recommended)

When deploying `universal_segments`, use this structure:

```json
{
  "name": "Active Subscribers (30 days)",
  "description": "Subscribers who opened or clicked in the last 30 days",
  "use_cases": "High-engagement campaigns, new product launches, time-sensitive offers",
  "estimated_size_percentage": "20-30%",
  "typical_performance": {
    "open_rate": "35-45%",
    "click_rate": "4-6%"
  }
}
```

Optional fields help the AI make better targeting decisions.

## Files Modified

1. **`agents/calendar_agent.py`** (lines 1127-1226)
   - `_extract_segment_list()`: Fetches both affinity + universal segments
   - Formats instructions for layering
   - Backward compatible

2. **`prompts/calendar_structuring_v1_2_2.yaml`** (lines 197-208)
   - Updated JSON schema example to show layering
   - Added segment layering examples
   - Clarified when to use single vs. layered

## Next Steps

1. **Deploy `universal_segments` to `/clients` API**
2. **Trigger test workflow** to verify segment extraction
3. **Review output** to ensure layering is working
4. **Monitor logs** for segment extraction counts
5. **Iterate on universal segment definitions** based on results

---

## Quick Reference

**Single Segment Use Cases**:
- Product-specific promotions → Affinity segment only
- Broad announcements → Universal segment only

**Layered Segment Use Cases**:
- Win-back with product focus → "Affinity AND Lapsed"
- VIP product launch → "Affinity AND VIP"  
- New customer onboarding → "Affinity AND First-Time Buyer"

**Segment Priority**:
1. Layered (Affinity + Universal) for campaigns
2. Single Affinity for product-focused
3. Single Universal for behavioral
4. "All Subscribers" for <10% of campaigns only
