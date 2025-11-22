# EmailPilot Simple Data Storage & Strategy Elements

## Where Additional Data Goes

EmailPilot Simple generates **two versions** of the calendar:

### 1. **Detailed Calendar** (Full Data)
**Storage:** Firestore via `ReviewStateManager`
**Location:** `workflow_reviews/{workflow_id}/detailed_calendar`
**Format:** JSON string (serialized)

**Contains ALL generated data:**
- Complete campaign briefs
- Subject line variants (A/B test options)
- Preview text
- Hero sections (headlines, images, descriptions)
- Body copy (main copy, supporting points)
- CTAs (primary/secondary buttons with URLs)
- Offer details (type, urgency, expected lift)
- A/B test strategies (hypothesis, expected impact, evidence)
- SMS variants (message, timing, segment)
- **Performance forecasts** (sends, open rate, click rate, conversion rate, revenue)
- **MCP evidence** (historical performance, segment insights, timing analysis)
- **Brand alignment** (voice, values, tone, messaging principles)
- Content themes and tags
- Audience targeting (segment name, size, rationale)
- Send time rationale

### 2. **Simplified Calendar** (Calendar App Display)
**Storage:** 
- Firestore via `ReviewStateManager`
- Pushed to Calendar App via `POST /api/calendar/import`

**Format:** Minimal event structure
**Contains ONLY:**
- `date` - Send date (YYYY-MM-DD)
- `title` - Subject line variant A (with emoji)
- `type` - Event type for UI categorization
- `description` - Content theme
- `send_time` - Time in HH:MM format
- `client_id` - Client identifier

## Strategy Element - MISSING from Simplified Calendar

You're correct! The **strategy/rationale** is NOT currently included in the simplified calendar sent to the Calendar App.

### What's Missing:
1. **Send Time Rationale** - Why this specific time was chosen
2. **Targeting Rationale** - Why this segment was selected
3. **A/B Test Strategy** - Test hypothesis and expected impact
4. **Performance Forecast** - Expected opens, clicks, revenue
5. **MCP Evidence** - Historical data supporting decisions
6. **Offer Strategy** - Urgency tactics, expected lift

### Where This Data Lives:
All strategy elements are in the **detailed_calendar** stored in Firestore, but the `CalendarFormatAdapter` strips them out when creating the simplified version.

## Recommendation: Enhanced Calendar App Payload

To show strategy in the Calendar App, you should modify the simplified calendar to include:

```json
{
  "events": [
    {
      "date": "2026-01-02",
      "title": "✉️ New Year, New Brew - Fresh Start Collection",
      "type": "promotional",
      "description": "product_launch",
      "send_time": "10:17",
      
      // ADD THESE STRATEGY FIELDS:
      "strategy": {
        "send_time_rationale": "Tuesday at 10:17 AM - top performing time based on MCP data",
        "targeting_rationale": "Engaged Subscribers (8,500) - 28.5% open rate historically",
        "performance_forecast": {
          "estimated_sends": 8500,
          "predicted_open_rate": 28.5,
          "predicted_revenue": 17850
        },
        "ab_test": {
          "element": "subject_line",
          "hypothesis": "Benefit-driven will outperform seasonal by 8-12%"
        }
      }
    }
  ]
}
```

## Files to Modify

1. **`tools/format_adapter.py`** - Update `_transform_event()` to include strategy fields
2. **`CALENDAR_APP_IMPORT_SPEC.md`** - Update spec to document strategy fields
3. **Calendar App** - Update UI to display strategy tooltips/modals

Would you like me to update the format adapter to include these strategy elements?
