# Calendar App Import Endpoint Specification (Updated with Strategy)

## Endpoint
`POST /api/calendar/import`

## Purpose
Receives campaign calendar data from EmailPilot Simple after Stage 1-2 completion, including per-event strategy and overall send strategy for the period.

## Request Format

### Headers
```
Content-Type: application/json
```

### Request Body
```json
{
  "client_id": "client-slug",
  "send_strategy": {
    "period_overview": "Strategic overview for the calendar period",
    "key_objectives": ["Objective 1", "Objective 2"],
    "cadence_strategy": "Send frequency and timing strategy",
    "audience_strategy": "Overall audience targeting approach",
    "performance_goals": "Expected outcomes"
  },
  "events": [
    {
      "date": "YYYY-MM-DD",
      "title": "Campaign Title",
      "type": "promotional|content|engagement|product_launch|seasonal",
      "description": "promotional|educational|engagement|win_back|seasonal|product_launch|nurture|lifecycle",
      "send_time": "HH:MM",
      "segment": "segment_name",
      "strategy": {
        "send_time_rationale": "Why this time was chosen",
        "targeting_rationale": "Why this segment was selected",
        "performance_forecast": {
          "estimated_sends": 8500,
          "predicted_open_rate": 28.5,
          "predicted_click_rate": 4.2,
          "predicted_conversion_rate": 2.1,
          "estimated_revenue": 17850,
          "confidence_level": "high"
        },
        "ab_test": {
          "element": "subject_line",
          "hypothesis": "Benefit-driven will outperform seasonal by 8-12%",
          "expected_impact": "+8-12% open rate"
        },
        "offer_strategy": {
          "type": "promotional",
          "details": "New Year Collection - limited time",
          "urgency": "Available through January only",
          "expected_lift": "15-20%"
        },
        "mcp_evidence": {
          "historical_performance": "Last year: 26.8% open, $42,500 revenue",
          "segment_insights": "28.5% open rate based on 47 historical campaigns",
          "data_quality": "0.95/1.0"
        }
      }
    }
  ]
}
```

### Field Descriptions

**Root Object:**
- `client_id` (string, required): Client identifier (e.g., "chris-bean", "rogue-creamery")
- `send_strategy` (object, required): Overall strategy for the calendar period
- `events` (array, required): Array of campaign events

**Send Strategy Object:**
- `period_overview` (string): Strategic overview extracted from planning output
- `key_objectives` (array/string): Main goals for the period
- `cadence_strategy` (string): Send frequency and timing approach
- `audience_strategy` (string): Overall targeting strategy
- `performance_goals` (string): Expected outcomes

**Event Object:**
- `date` (string, required): Campaign send date in ISO format (YYYY-MM-DD)
- `title` (string, required): Campaign name/subject line (may include emoji)
- `type` (string, required): Calendar event type for UI categorization
- `description` (string, required): Campaign type for detailed classification
- `send_time` (string, required): Scheduled send time in 24-hour format (HH:MM)
- `segment` (string, optional): Target segment name
- `strategy` (object, optional): Per-event strategy details

**Event Strategy Object:**
- `send_time_rationale` (string): Explanation of why this send time was chosen
- `targeting_rationale` (string): Explanation of segment selection
- `performance_forecast` (object): Predicted performance metrics
  - `estimated_sends` (number): Expected number of sends
  - `predicted_open_rate` (number): Expected open rate percentage
  - `predicted_click_rate` (number): Expected click rate percentage
  - `predicted_conversion_rate` (number): Expected conversion rate percentage
  - `estimated_revenue` (number): Expected revenue in dollars
  - `confidence_level` (string): "high", "medium", or "low"
- `ab_test` (object): A/B test strategy
  - `element` (string): What's being tested (e.g., "subject_line")
  - `hypothesis` (string): Test hypothesis
  - `expected_impact` (string): Expected improvement
- `offer_strategy` (object): Promotional offer details
  - `type` (string): Offer type
  - `details` (string): Offer description
  - `urgency` (string): Urgency messaging
  - `expected_lift` (string): Expected performance lift
- `mcp_evidence` (object): Historical data supporting decisions
  - `historical_performance` (string): Past campaign performance
  - `segment_insights` (string): Segment-specific insights
  - `data_quality` (string): Data quality score

## Example Request

```json
{
  "client_id": "chris-bean",
  "send_strategy": {
    "period_overview": "January 2026 strategy focuses on New Year momentum with product launches and educational content to drive Q1 revenue growth.",
    "key_objectives": [
      "Launch New Year coffee collection",
      "Increase subscription sign-ups by 25%",
      "Maintain 28%+ open rates"
    ],
    "cadence_strategy": "2-3 emails per week with strategic resends to non-openers",
    "audience_strategy": "Primary focus on Engaged Subscribers segment (8,500 contacts) with targeted win-back campaigns for lapsed customers"
  },
  "events": [
    {
      "date": "2026-01-02",
      "title": "✉️ New Year, New Brew - Fresh Start Collection",
      "type": "promotional",
      "description": "product_launch",
      "send_time": "10:17",
      "segment": "Engaged Subscribers",
      "strategy": {
        "send_time_rationale": "Tuesday at 10:17 AM - top performing time based on MCP data showing 28.5% open rate for this segment",
        "targeting_rationale": "Engaged Subscribers (8,500 contacts) - highest engagement segment with 0.85+ engagement score",
        "performance_forecast": {
          "estimated_sends": 8500,
          "predicted_open_rate": 28.5,
          "predicted_click_rate": 4.2,
          "predicted_conversion_rate": 2.1,
          "estimated_revenue": 17850,
          "confidence_level": "high"
        },
        "ab_test": {
          "element": "subject_line",
          "hypothesis": "Benefit-driven subject line will outperform seasonal framing by 8-12%",
          "expected_impact": "+8-12% open rate improvement"
        },
        "offer_strategy": {
          "type": "promotional",
          "details": "New Year Collection - three exclusive roasts",
          "urgency": "Limited-time collection available through January only",
          "expected_lift": "15-20%"
        },
        "mcp_evidence": {
          "historical_performance": "Last year same period: 26.8% open, 3.9% click, $42,500 revenue from 3 January campaigns",
          "segment_insights": "Engaged Subscribers shows 28.5% open rate based on 47 historical campaigns",
          "data_quality": "0.95/1.0"
        }
      }
    }
  ]
}
```

## Expected Response

### Success (200 OK)
```json
{
  "success": true,
  "message": "Calendar imported successfully with strategy",
  "events_imported": 13,
  "client_id": "chris-bean",
  "has_send_strategy": true
}
```

### Error (400 Bad Request)
```json
{
  "success": false,
  "error": "Invalid request format",
  "details": "Missing required field: send_strategy"
}
```

## Implementation Notes

1. **Send Strategy Display**: Show overall send strategy in a prominent header/summary section
2. **Per-Event Strategy**: Display strategy details in tooltips, modals, or expandable sections for each event
3. **Performance Forecasts**: Highlight predicted metrics to help users understand expected outcomes
4. **MCP Evidence**: Show historical data to build confidence in AI recommendations
5. **A/B Test Visibility**: Clearly indicate which campaigns have A/B tests planned
6. **Data Validation**: Validate all required fields and nested objects

## UI Recommendations

1. **Strategy Summary Panel**: Display `send_strategy` at the top of the calendar view
2. **Event Cards**: Show basic info (date, title, type) with a "View Strategy" button
3. **Strategy Modal**: When clicked, show full strategy details including:
   - Send time rationale
   - Targeting rationale
   - Performance forecast (as a chart/table)
   - A/B test details
   - Historical evidence
4. **Performance Indicators**: Use visual indicators (icons, colors) to show confidence levels
5. **Edit Capability**: Allow users to edit strategy fields along with event details

## Sample Data
See: `outputs/chris-bean_2026-01-01_20251120_115012_simplified_calendar.json`
