# Strategy Summary Feature - Technical Specifications

**Version:** 1.0.0
**Date:** 2025-11-18
**Author:** EmailPilot Engineering
**Status:** Specification - Ready for Implementation

---

## 1. Overview

### Purpose
Enable the Calendar app to display an AI-generated **Strategy Summary** that provides clients with high-level insights about their campaign calendar strategy.

### Key Discovery
**The Strategy Summary is already being generated** by Claude Sonnet 4.5 in Stage 2 (Structuring) of the calendar workflow. It exists in the LLM output as `detailed_calendar.metadata.strategy_summary` but is:
- Not extracted as a separate field
- Not transmitted to the calendar app
- Not stored independently in Firestore

### Solution Approach
Extract the existing `strategy_summary` from the workflow output and expose it as a first-class entity in the API and database.

---

## 2. Data Model Specification

### 2.1 Strategy Summary Schema

```python
# Location: emailpilot-app/app/api/calendar.py

from pydantic import BaseModel, Field
from typing import List, Optional

class StrategySummary(BaseModel):
    """AI-generated strategic summary for a calendar period"""

    key_insights: List[str] = Field(
        ...,
        description="List of key strategic insights (3-6 bullet points)",
        min_items=3,
        max_items=8,
        example=[
            "MCP data-driven scheduling with :17 minute offset for optimal deliverability",
            "Premium creative content with brand-aligned messaging",
            "Segment-focused targeting avoiding over-reliance on 'All Subscribers'"
        ]
    )

    targeting_approach: str = Field(
        ...,
        description="Description of audience targeting strategy",
        min_length=50,
        max_length=500,
        example="Segment-specific campaigns based on engagement scores, RFM analysis, and product affinity"
    )

    timing_strategy: str = Field(
        ...,
        description="Description of send timing and frequency strategy",
        min_length=50,
        max_length=500,
        example="Diversified across all 7 days with :17 offset, based on historical performance data"
    )

    content_strategy: str = Field(
        ...,
        description="Mix of content types and campaign purposes",
        min_length=50,
        max_length=500,
        example="Mix of promotional (6), educational (4), product launches (2), engagement/nurture (1)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "key_insights": [
                    "MCP data-driven scheduling with :17 minute offset",
                    "Premium creative content with brand-aligned messaging",
                    "Multi-agent architecture ensuring data quality"
                ],
                "targeting_approach": "Segment-specific campaigns based on engagement scores",
                "timing_strategy": "Diversified across all 7 days with :17 offset",
                "content_strategy": "Mix of promotional (6), educational (4), product launches (2)"
            }
        }
```

### 2.2 Modified Bulk Events Creation Schema

```python
# Location: emailpilot-app/app/api/calendar.py

class BulkEventsCreate(BaseModel):
    """Request model for bulk creating calendar events with strategy summary"""

    client_id: str = Field(..., description="Client ID")
    events: List[CalendarEventCreate] = Field(..., description="List of events to create")

    # NEW FIELD - Strategy Summary
    strategy_summary: Optional[StrategySummary] = Field(
        default=None,
        description="AI-generated strategy summary for this calendar period"
    )

    # Optional metadata
    workflow_id: Optional[str] = Field(
        default=None,
        description="Workflow ID from emailpilot-simple for tracking"
    )

    start_date: Optional[str] = Field(
        default=None,
        description="Calendar period start date (YYYY-MM-DD)"
    )

    end_date: Optional[str] = Field(
        default=None,
        description="Calendar period end date (YYYY-MM-DD)"
    )
```

---

## 3. Extraction Logic (emailpilot-simple)

### 3.1 Modify CalendarAgent Workflow Output

**File:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/agents/calendar_agent.py`

**Location:** `CalendarAgent.run_workflow()` method (around line 1100-1200)

**Current Output Structure:**
```python
result = {
    "planning": planning_output,
    "detailed_calendar": detailed_calendar,
    "simplified_calendar": simplified_calendar,
    "calendar_json": detailed_calendar,
    "briefs": briefs_output,
    "stage_2_validation": stage_2_validation,
    "metadata": {...}
}
```

**Required Modification:**
```python
# After Stage 2 (Structuring) completes successfully
async def run_workflow(self, client_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Run complete 3-stage calendar workflow."""

    # ... existing Stage 1 and Stage 2 code ...

    # EXTRACT STRATEGY SUMMARY from detailed_calendar.metadata
    strategy_summary = None
    if detailed_calendar and "metadata" in detailed_calendar:
        strategy_summary = detailed_calendar["metadata"].get("strategy_summary")

        if strategy_summary:
            logger.info(f"✓ Extracted Strategy Summary with {len(strategy_summary.get('key_insights', []))} insights")
        else:
            logger.warning("⚠ Strategy Summary not found in detailed_calendar.metadata")

    # ... existing Stage 3 code ...

    # Modified result to include strategy_summary as top-level field
    result = {
        "planning": planning_output,
        "detailed_calendar": detailed_calendar,
        "simplified_calendar": simplified_calendar,
        "calendar_json": detailed_calendar,  # Backward compatibility
        "briefs": briefs_output,
        "stage_2_validation": stage_2_validation,

        # NEW: Extract strategy_summary as separate field
        "strategy_summary": strategy_summary,

        "metadata": {
            "client_name": client_name,
            "start_date": start_date,
            "end_date": end_date,
            "model": self.model,
            "workflow_id": workflow_id,
            "has_strategy_summary": strategy_summary is not None
        }
    }

    return result
```

### 3.2 Modify CalendarTool to Include Strategy Summary in Outputs

**File:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/tools/calendar_tool.py`

**Location:** `run_workflow()` method (around line 400-500)

```python
async def run_workflow(
    self,
    client_name: str,
    start_date: str,
    end_date: str,
    save_outputs: bool = True
) -> Dict[str, Any]:
    """Run the complete calendar workflow with validation."""

    # ... existing code ...

    # Extract strategy_summary from workflow result
    strategy_summary = result.get("strategy_summary")

    # Save strategy_summary as separate JSON file
    if save_outputs and strategy_summary:
        summary_file = os.path.join(
            output_dir,
            f"{client_slug}_{start_date}_{end_date}_{timestamp}_strategy_summary.json"
        )
        with open(summary_file, 'w') as f:
            json.dump(strategy_summary, f, indent=2)
        logger.info(f"✓ Saved strategy summary: {summary_file}")

    # Include strategy_summary in final result
    final_result = {
        "success": all_valid,
        "planning": result.get("planning"),
        "calendar_json": result.get("calendar_json"),
        "briefs": result.get("briefs"),
        "strategy_summary": strategy_summary,  # NEW
        "validation": validation_results,
        "metadata": result.get("metadata", {})
    }

    return final_result
```

### 3.3 Update Import Script to Include Strategy Summary

**File:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/import_calendar_to_app.py`

**Modification:**
```python
def create_bulk_request(calendar_data: Dict, strategy_summary: Dict = None) -> Dict:
    """Create the BulkEventsCreate request payload."""
    client_id = calendar_data.get('client_id')
    events = calendar_data.get('events', [])

    transformed_events = [
        transform_event(event, client_id)
        for event in events
    ]

    bulk_request = {
        "client_id": client_id,
        "events": transformed_events
    }

    # Add strategy_summary if available
    if strategy_summary:
        bulk_request["strategy_summary"] = strategy_summary

    return bulk_request

def main():
    # ... existing code ...

    # Check if strategy_summary file exists alongside calendar file
    strategy_file = CALENDAR_FILE.replace("_calendar_app.json", "_strategy_summary.json")
    strategy_summary = None

    if os.path.exists(strategy_file):
        print(f"Loading strategy summary from: {strategy_file}")
        with open(strategy_file, 'r') as f:
            strategy_summary = json.load(f)
        print(f"✓ Loaded strategy summary with {len(strategy_summary.get('key_insights', []))} insights")

    # Transform to bulk request with strategy_summary
    bulk_request = create_bulk_request(calendar_data, strategy_summary)

    # ... rest of import logic ...
```

---

## 4. API Implementation (emailpilot-app)

### 4.1 Extended Bulk Events Creation Endpoint

**File:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/app/api/calendar.py`

**Endpoint:** `POST /api/calendar/create-bulk-events`

```python
from app.deps.firestore import get_db
from google.cloud.firestore import Client as FirestoreClient
from datetime import datetime

@router.post("/create-bulk-events")
async def create_bulk_events(
    bulk_data: BulkEventsCreate,
    db: FirestoreClient = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create multiple calendar events in bulk with optional strategy summary.

    New in v2.0: Accepts and stores strategy_summary alongside events.
    """
    client_id = bulk_data.client_id
    events_data = bulk_data.events
    strategy_summary = bulk_data.strategy_summary

    created_events = []

    try:
        # Create all events
        for event_data in events_data:
            event_dict = event_data.dict()
            event_dict["created_at"] = datetime.utcnow().isoformat()
            event_dict["updated_at"] = datetime.utcnow().isoformat()

            doc_ref = db.collection("calendar_events").add(event_dict)
            event_dict["id"] = doc_ref[1].id
            created_events.append(event_dict)

        # Store strategy_summary if provided
        summary_id = None
        if strategy_summary:
            summary_dict = strategy_summary.dict()
            summary_dict.update({
                "client_id": client_id,
                "start_date": bulk_data.start_date,
                "end_date": bulk_data.end_date,
                "workflow_id": bulk_data.workflow_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })

            # Store in dedicated collection
            summary_ref = db.collection("calendar_strategy_summaries").add(summary_dict)
            summary_id = summary_ref[1].id

            logger.info(f"✓ Stored strategy summary: {summary_id} for {client_id}")

        return {
            "success": True,
            "count": len(created_events),
            "client_id": client_id,
            "events": created_events,
            "strategy_summary_id": summary_id,
            "message": f"Created {len(created_events)} events" +
                      (f" with strategy summary" if summary_id else "")
        }

    except Exception as e:
        logger.error(f"Failed to create bulk events: {e}")

        # HALT ON FAILURE: Rollback any created events
        for event in created_events:
            try:
                db.collection("calendar_events").document(event["id"]).delete()
            except:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create calendar events: {str(e)}"
        )
```

### 4.2 New Get Strategy Summary Endpoint

```python
@router.get("/strategy-summary/{client_id}")
async def get_strategy_summary(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: FirestoreClient = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve strategy summary for a client and date range.

    Query params:
    - start_date: Filter by start_date (YYYY-MM-DD)
    - end_date: Filter by end_date (YYYY-MM-DD)

    Returns most recent summary if no dates specified.
    """
    query = db.collection("calendar_strategy_summaries").where("client_id", "==", client_id)

    if start_date:
        query = query.where("start_date", "==", start_date)
    if end_date:
        query = query.where("end_date", "==", end_date)

    # Order by created_at descending to get most recent
    query = query.order_by("created_at", direction="DESCENDING").limit(1)

    docs = query.stream()

    for doc in docs:
        summary_data = doc.to_dict()
        summary_data["id"] = doc.id
        return {
            "success": True,
            "strategy_summary": summary_data
        }

    raise HTTPException(
        status_code=404,
        detail=f"No strategy summary found for client {client_id}"
    )
```

---

## 5. Firestore Storage Schema

### 5.1 New Collection: `calendar_strategy_summaries`

**Collection Path:** `/calendar_strategy_summaries/{summary_id}`

**Document Schema:**
```json
{
  "id": "auto-generated-firestore-id",
  "client_id": "rogue-creamery",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "workflow_id": "rogue-creamery_2026-01-01_2026-01-31_20251118_194816",

  "key_insights": [
    "MCP data-driven scheduling with :17 minute offset for optimal deliverability",
    "Premium creative content with brand-aligned messaging",
    "Multi-agent architecture ensuring data quality and strategic targeting",
    "Segment-focused targeting avoiding over-reliance on 'All Subscribers'"
  ],

  "targeting_approach": "Segment-specific campaigns based on engagement scores, RFM analysis, and product affinity",

  "timing_strategy": "Diversified across all 7 days with :17 offset, based on historical performance data from MCP",

  "content_strategy": "Mix of promotional (6), educational (4), product launches (2), engagement/nurture (1)",

  "created_at": "2025-11-18T19:48:16Z",
  "updated_at": "2025-11-18T19:48:16Z"
}
```

### 5.2 Firestore Indexes Required

```javascript
// Required composite indexes for efficient querying
db.collection("calendar_strategy_summaries").createIndex({
  "client_id": 1,
  "start_date": 1,
  "created_at": -1
});

db.collection("calendar_strategy_summaries").createIndex({
  "client_id": 1,
  "created_at": -1
});
```

---

## 6. Calendar App Frontend Integration

### 6.1 API Request to Fetch Strategy Summary

**When:** Calendar app loads calendar for a client

**Endpoint:** `GET /api/calendar/strategy-summary/{client_id}?start_date=2026-01-01&end_date=2026-01-31`

**Example Request:**
```javascript
// Frontend TypeScript/JavaScript
async function fetchStrategySummary(clientId, startDate, endDate) {
  const response = await fetch(
    `/api/calendar/strategy-summary/${clientId}?start_date=${startDate}&end_date=${endDate}`
  );

  if (!response.ok) {
    console.warn('No strategy summary available for this calendar');
    return null;
  }

  const data = await response.json();
  return data.strategy_summary;
}
```

**Example Response:**
```json
{
  "success": true,
  "strategy_summary": {
    "id": "abc123def456",
    "client_id": "rogue-creamery",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "key_insights": [
      "MCP data-driven scheduling with :17 minute offset for optimal deliverability",
      "Premium creative content with brand-aligned messaging",
      "Multi-agent architecture ensuring data quality and strategic targeting"
    ],
    "targeting_approach": "Segment-specific campaigns based on engagement scores, RFM analysis, and product affinity",
    "timing_strategy": "Diversified across all 7 days with :17 offset, based on historical performance data",
    "content_strategy": "Mix of promotional (6), educational (4), product launches (2), engagement/nurture (1)",
    "created_at": "2025-11-18T19:48:16Z"
  }
}
```

### 6.2 Frontend Display Recommendations

**Component Structure:**
```jsx
// React component example
function StrategySummaryPanel({ summary }) {
  if (!summary) return null;

  return (
    <div className="strategy-summary-panel bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold text-blue-900 mb-4">
        📊 Strategy Summary
      </h2>

      {/* Key Insights */}
      <div className="mb-4">
        <h3 className="font-semibold text-gray-800 mb-2">Key Insights</h3>
        <ul className="list-disc list-inside space-y-1">
          {summary.key_insights.map((insight, idx) => (
            <li key={idx} className="text-gray-700">{insight}</li>
          ))}
        </ul>
      </div>

      {/* Targeting Approach */}
      <div className="mb-4">
        <h3 className="font-semibold text-gray-800 mb-2">Targeting Approach</h3>
        <p className="text-gray-700">{summary.targeting_approach}</p>
      </div>

      {/* Timing Strategy */}
      <div className="mb-4">
        <h3 className="font-semibold text-gray-800 mb-2">Timing Strategy</h3>
        <p className="text-gray-700">{summary.timing_strategy}</p>
      </div>

      {/* Content Strategy */}
      <div>
        <h3 className="font-semibold text-gray-800 mb-2">Content Strategy</h3>
        <p className="text-gray-700">{summary.content_strategy}</p>
      </div>
    </div>
  );
}
```

**Placement:** Display above the calendar grid, collapsible for space efficiency

---

## 7. Error Handling (Halt-on-Failure)

### 7.1 emailpilot-simple Workflow

**If strategy_summary extraction fails:**
```python
# In CalendarAgent.run_workflow()
strategy_summary = detailed_calendar.get("metadata", {}).get("strategy_summary")

if not strategy_summary:
    error_msg = "CRITICAL: Strategy Summary not found in LLM output"
    logger.error(error_msg)

    # HALT: Raise exception to stop workflow
    raise ValueError(
        f"{error_msg}. This indicates the structuring prompt failed to generate "
        f"the required metadata.strategy_summary field. Workflow halted."
    )
```

### 7.2 emailpilot-app API

**If strategy_summary storage fails:**
```python
# In create_bulk_events endpoint
try:
    # Store strategy summary
    summary_ref = db.collection("calendar_strategy_summaries").add(summary_dict)
    summary_id = summary_ref[1].id
except Exception as e:
    logger.error(f"CRITICAL: Failed to store strategy summary: {e}")

    # ROLLBACK: Delete any created events
    for event in created_events:
        db.collection("calendar_events").document(event["id"]).delete()

    # HALT: Return error response
    raise HTTPException(
        status_code=500,
        detail=f"Strategy summary storage failed: {str(e)}. All events rolled back."
    )
```

### 7.3 Backward Compatibility

**If strategy_summary is missing (optional behavior):**
```python
# Allow workflows without strategy_summary to continue
if strategy_summary:
    logger.info("✓ Strategy Summary included in workflow")
else:
    logger.warning("⚠ Strategy Summary not available (backward compatibility mode)")
    # Continue without halting for older workflows
```

---

## 8. Implementation Steps

### Phase 1: emailpilot-simple Modifications (Estimated: 2 hours)

1. **Modify CalendarAgent** (`agents/calendar_agent.py`)
   - Extract `strategy_summary` from `detailed_calendar.metadata`
   - Add as top-level field in workflow result
   - Add validation to ensure it exists
   - Test: `pytest tests/test_calendar_agent.py`

2. **Modify CalendarTool** (`tools/calendar_tool.py`)
   - Save strategy_summary as separate JSON file
   - Include in final workflow result
   - Test: `pytest tests/test_calendar_tool.py`

3. **Update Import Script** (`import_calendar_to_app.py`)
   - Load strategy_summary JSON file if exists
   - Include in BulkEventsCreate payload
   - Test: Manual import with sample data

### Phase 2: emailpilot-app API (Estimated: 3 hours)

4. **Add Pydantic Models** (`app/api/calendar.py`)
   - Create `StrategySummary` model
   - Modify `BulkEventsCreate` to include strategy_summary
   - Test: Model validation with pytest

5. **Extend Bulk Events Endpoint** (`app/api/calendar.py`)
   - Accept strategy_summary in request
   - Store in `calendar_strategy_summaries` collection
   - Return summary_id in response
   - Add rollback logic on failure
   - Test: API integration tests

6. **Create Get Strategy Summary Endpoint** (`app/api/calendar.py`)
   - Implement query by client_id + date range
   - Return most recent if no dates specified
   - Test: API integration tests

### Phase 3: Frontend Integration (Estimated: 2 hours)

7. **Calendar App Frontend** (location TBD by frontend team)
   - Add API client function to fetch strategy summary
   - Create StrategySummaryPanel React component
   - Display above calendar grid
   - Make collapsible for UX
   - Test: Manual testing with real calendar data

### Phase 4: End-to-End Testing (Estimated: 1 hour)

8. **Execute Production Workflow for Rogue Creamery January 2026**
   - Run: `python3 main.py --client rogue-creamery --start-date 2026-01-01 --end-date 2026-01-31`
   - Verify strategy_summary extracted
   - Import to emailpilot-app
   - Verify strategy_summary stored in Firestore
   - Verify frontend displays summary correctly

---

## 9. Testing Checklist

### Unit Tests
- [ ] CalendarAgent extracts strategy_summary correctly
- [ ] CalendarTool saves strategy_summary JSON file
- [ ] StrategySummary Pydantic model validates correctly
- [ ] BulkEventsCreate accepts optional strategy_summary

### Integration Tests
- [ ] POST /api/calendar/create-bulk-events with strategy_summary
- [ ] POST /api/calendar/create-bulk-events without strategy_summary (backward compat)
- [ ] GET /api/calendar/strategy-summary/{client_id} returns correct data
- [ ] GET /api/calendar/strategy-summary/{client_id} with date filters
- [ ] Firestore storage and retrieval of strategy summaries

### End-to-End Tests
- [ ] Run workflow for Rogue Creamery January 2026
- [ ] Verify strategy_summary in output files
- [ ] Import to emailpilot-app successfully
- [ ] Retrieve strategy_summary via API
- [ ] Display in calendar frontend

### Error Handling Tests
- [ ] Workflow halts if strategy_summary extraction fails
- [ ] API rolls back events if summary storage fails
- [ ] Graceful degradation if summary not available

---

## 10. Success Metrics

1. **Strategy Summary Extraction Rate:** 100% of workflows should extract strategy_summary
2. **API Storage Success Rate:** 100% of imports with strategy_summary should store successfully
3. **Frontend Display:** Strategy Summary displayed within 500ms of calendar load
4. **Error Recovery:** All failures should trigger rollback with clear error messages
5. **Backward Compatibility:** Existing workflows without strategy_summary continue to work

---

## 11. Calendar App Team Notification

### For Calendar App Frontend Team

**New API Endpoint Available:**
```
GET /api/calendar/strategy-summary/{client_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

**Response Format:**
```typescript
interface StrategySummaryResponse {
  success: boolean;
  strategy_summary: {
    id: string;
    client_id: string;
    start_date: string;
    end_date: string;
    key_insights: string[];        // 3-8 bullet points
    targeting_approach: string;    // 50-500 chars
    timing_strategy: string;       // 50-500 chars
    content_strategy: string;      // 50-500 chars
    created_at: string;            // ISO datetime
  }
}
```

**Integration Instructions:**
1. Fetch strategy summary when loading calendar
2. Display in collapsible panel above calendar grid
3. Show all 4 sections: key_insights (bullet list), targeting_approach, timing_strategy, content_strategy
4. Gracefully handle 404 if no summary exists (older calendars)
5. Use blue/info styling to differentiate from calendar events

**Example Implementation:** See Section 6.2 for React component example

---

## 12. Appendix: Sample Strategy Summary

```json
{
  "id": "abc123def456",
  "client_id": "rogue-creamery",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "workflow_id": "rogue-creamery_2026-01-01_2026-01-31_20251118_194816",

  "key_insights": [
    "MCP data-driven scheduling with :17 minute offset for optimal deliverability based on historical open rates",
    "Premium creative content with brand-aligned messaging focused on artisanal cheese craftsmanship",
    "Multi-agent architecture ensuring data quality through RAG + MCP + Firestore integration",
    "Segment-focused targeting avoiding over-reliance on 'All Subscribers' - 92% of campaigns target specific segments",
    "January planning includes early Valentine's Day prep (January 8 global insight)"
  ],

  "targeting_approach": "Segment-specific campaigns based on engagement scores, RFM analysis, and product affinity. High-value customers receive exclusive previews, engaged subscribers get educational content, and at-risk customers receive re-engagement campaigns. 'All Subscribers' used only for major announcements.",

  "timing_strategy": "Diversified across all 7 days of the week with :17 minute offset (e.g., 10:17 AM, 2:17 PM) based on historical performance data from MCP. Peak send days are Tuesday (4 campaigns), Wednesday (3 campaigns), and Thursday (3 campaigns) to maximize engagement during mid-week attention peaks.",

  "content_strategy": "Mix of promotional (6 campaigns - 46%), educational/nurture (4 campaigns - 31%), product launches (2 campaigns - 15%), and engagement campaigns (1 campaign - 8%). Promotional focus on January clearance and new year planning themes, educational content on cheese pairing and storage, product launches for seasonal offerings.",

  "created_at": "2025-11-18T19:48:16Z",
  "updated_at": "2025-11-18T19:48:16Z"
}
```

---

**END OF TECHNICAL SPECIFICATION**

**Next Step:** Notify Calendar App team and begin Phase 1 implementation.
