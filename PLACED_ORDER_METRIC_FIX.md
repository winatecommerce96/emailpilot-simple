# Placed Order Metric ID Fix

## Issue

The MCP client was **searching** for the "Placed Order" metric by iterating through all available metrics, instead of using the **authoritative `placed_order_metric_id`** from the Clients API.

**Old Code**:
```python
# Search through all metrics
metrics = await self._fetch_metrics(server)
for metric in metrics:
    if metric.get("attributes", {}).get("name") == "Placed Order":
        conversion_metric_id = metric.get("id")
        break
```

**Problems**:
- ❌ Inefficient (fetches all metrics unnecessarily)
- ❌ Could fail if metric is named differently
- ❌ Could pick wrong metric if multiple "Placed Order" variants exist
- ❌ Ignores the authoritative source (`placed_order_metric_id` in Clients API)

---

## Solution

**Now fetches `placed_order_metric_id` directly from Clients API** before falling back to search.

**New Code** (`data/native_mcp_client.py` lines 494-534):
```python
# 1. Fetch from Clients API (authoritative)
try:
    response = httpx.get("https://emailpilot.ai/api/clients", timeout=10.0)
    clients = response.json()
    
    for client in clients:
        if client.get("id") == client_name:
            conversion_metric_id = client.get("placed_order_metric_id") or client.get("metric_id")
            logger.info(f"✅ Using placed_order_metric_id from Clients API: {conversion_metric_id}")
            break
except Exception as e:
    logger.warning(f"Failed to fetch from API: {e}")

# 2. Fallback to search (backward compatible)
if not conversion_metric_id:
    logger.info("Falling back to searching for 'Placed Order' metric")
    metrics = await self._fetch_metrics(server)
    # ... search logic
```

---

## Benefits

✅ **Uses authoritative metric ID** from Clients API  
✅ **Faster** - No need to fetch all metrics if API has the ID  
✅ **More reliable** - Client-specific metric ID guaranteed correct  
✅ **Backward compatible** - Falls back to search if API call fails  
✅ **Better logging** - Shows which method was used  

---

## How It Works

### Flow Diagram

```
START: _fetch_campaign_report()
  |
  v
Try: Fetch placed_order_metric_id from /clients API
  |
  ├─ SUCCESS ✅
  |   └─> Use conversion_metric_id from API
  |       └─> Log: "✅ Using placed_order_metric_id from Clients API: {id}"
  |
  └─ FAIL ❌
      └─> Fall back to searching Klaviyo metrics
          |
          ├─ Found "Placed Order" metric
          |   └─> Log: "Found 'Placed Order' metric by search: {id}"
          |
          ├─ Not found, but other metrics exist
          |   └─> Use first metric
          |       └─> Log: "⚠️No 'Placed Order' found, using first metric"
          |
          └─ No metrics at all
              └─> Skip value statistics
                  └─> Log: "⚠️ No conversion metric found"
```

### Clients API Field

The system looks for **either**:
1. `placed_order_metric_id` (primary)
2. `metric_id` (fallback)

**Example Clients API response**:
```json
{
  "id": "christopher-bean-coffee",
  "placed_order_metric_id": "UVBrHm",
  "metric_id": "UVBrHm",  // fallback if placed_order_metric_id missing
  "klaviyo_company_id": "V6RWq9",
  ...
}
```

---

## Logging

### Success Case (API)
```
INFO: Fetching placed_order_metric_id from Clients API for christopher-bean-coffee
INFO: ✅ Using placed_order_metric_id from Clients API: UVBrHm
```

### Fallback Case (Search)
```
INFO: Fetching placed_order_metric_id from Clients API for christopher-bean-coffee
WARNING: Failed to fetch placed_order_metric_id from Clients API: Connection timeout
INFO: Falling back to searching for 'Placed Order' metric
INFO: Found 'Placed Order' metric by search: XYZ123
```

### Error Case (No Metric Found)
```
INFO: Falling back to searching for 'Placed Order' metric
WARNING: No 'Placed Order' metric found, using first metric: ABC456
```

---

## Testing

### Verify API Method is Used
1. **Trigger a workflow** that fetches MCP data
2. **Check logs** for:
   ```
   INFO: ✅ Using placed_order_metric_id from Clients API: UVBrHm
   ```
3. **Verify** no "Falling back to searching" message appears (means API worked)

### Verify Fallback Still Works
1. **Temporarily break API** (e.g., change URL to invalid)
2. **Trigger workflow**
3. **Check logs** for:
   ```
   WARNING: Failed to fetch placed_order_metric_id from Clients API: ...
   INFO: Falling back to searching for 'Placed Order' metric
   ```

### Verify Revenue Calculations
- Revenue should use the **client-specific metric**
- Check `campaign_report` data has `avg_order_value`, `conversion_rate`, etc.
- Verify numbers match Klaviyo's campaign performance reports

---

## Impact on Revenue Calculations

### Before Fix
- Could use wrong metric if multiple "Placed Order" variants exist
- Inefficient (fetches all metrics every time)
- No guarantee of using client-specific metric

### After Fix
- ✅ Always uses client-specific `placed_order_metric_id`
- ✅ Faster (single API call vs. fetching all metrics)
- ✅ More accurate revenue/AOV calculations
- ✅ Consistent across clients (each uses their designated metric)

---

## Related Files

- **Modified**: `data/native_mcp_client.py` (lines 494-534)
- **Uses**: `/clients` API endpoint
- **Affects**: Revenue calculations in campaign reports
- **Used by**: `_extract_performance_metrics()` in `calendar_agent.py`

---

## Backward Compatibility

✅ **Fully backward compatible**:
- If `placed_order_metric_id` is missing → searches for "Placed Order"
- If API call fails → searches for "Placed Order"
- If search fails → uses first available metric
- If no metrics → skips value statistics (graceful degradation)

No breaking changes for existing clients.

---

## Next Steps

1. **Verify API response** includes `placed_order_metric_id`:
   ```bash
   curl https://emailpilot.ai/api/clients | jq '.[] | select(.id=="christopher-bean-coffee") | .placed_order_metric_id'
   ```

2. **Trigger workflow** and check logs for:
   ```
   ✅ Using placed_order_metric_id from Clients API: UVBrHm
   ```

3. **Verify revenue calculations** are accurate and match Klaviyo

4. **Monitor** for any fallback cases (shouldn't happen if API is healthy)

---

## Success Criteria

✅ All workflows use `placed_order_metric_id` from Clients API  
✅ No fallback to search method (unless API fails)  
✅ Revenue calculations accurate and client-specific  
✅ Logs show "✅ Using placed_order_metric_id from Clients API"  
✅ No performance degradation (should be faster)
