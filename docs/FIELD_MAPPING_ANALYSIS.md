# EmailPilot Simple → Calendar Import Field Mapping Analysis

**Date**: 2025-11-16
**Purpose**: Comprehensive mapping between EmailPilot Simple output and Calendar Import Specification
**Goal**: Identify enriched data requiring preservation for post-review brief generation

---

## Executive Summary

EmailPilot Simple generates **13 enriched fields** beyond the Calendar Import Specification's schema. These fields contain critical strategic context, creative direction, and rationales essential for final brief generation. This document maps all fields, identifies gaps, and recommends a dual-storage architecture.

---

## Field Mapping Matrix

### ✅ Direct Mappings (Fully Compatible)

| EmailPilot Simple Field | Calendar Import Spec Field | Type | Notes |
|------------------------|---------------------------|------|-------|
| `title` | `name` | string | Direct mapping |
| `date` | `date` | ISO 8601 | Requires transformation to full datetime |
| `type` | `type` | enum | Compatible (promotional, newsletter, etc.) |
| `description` | `description` | string | Max 2000 chars in spec |
| `segment` | `audience_segments[0].name` | string | Maps to first segment in array |
| `send_time` | `time` | string | Human-readable format compatible |

### ⚠️ Transformable Mappings (Require Field Restructuring)

| EmailPilot Simple Field | Calendar Import Spec Field | Transformation Required |
|------------------------|---------------------------|------------------------|
| `subject_line_a` | `content.subject_line` | Choose variant A as primary |
| `subject_line_b` | `custom_fields.subject_line_b` | Store variant B in custom fields |
| `preview_text` | `content.preview_text` | Direct mapping to nested field |
| `cta_copy` | `content.call_to_action.text` | Map to CTA text field |
| N/A | `channel` | **Missing** - Default to "email" |
| N/A | `status` | **Missing** - Default to "draft" |

### ❌ Unmappable Enriched Fields (Require Separate Storage)

These fields contain strategic context, creative direction, and rationales **not present** in the Calendar Import Specification:

| Field | Type | Why Unmappable | Preservation Strategy |
|-------|------|----------------|----------------------|
| `ab_test_idea` | string | No equivalent field for test hypotheses | Store in enriched context DB |
| `hero_image` | string | Spec wants URL (`thumbnail_url`), we have description | Extract to creative brief storage |
| `offer` | string | Detailed offer text vs. structured custom fields | Store in enriched context DB |
| `secondary_message` | string | Cross-channel message variants | Store in enriched context DB |
| `week_number` | integer | Strategic planning context not in spec | Store in metadata/custom fields |
| `hero_h1` | string | Detailed creative direction | Extract to creative brief storage |
| `sub_head` | string | Detailed creative direction | Extract to creative brief storage |

### 📊 Detailed Calendar Output Extended Fields (v4.0.0)

The **detailed calendar** output contains additional strategic fields also requiring preservation:

| Field | Location | Why Critical |
|-------|----------|--------------|
| `send_time_rationale` | `campaigns[].send_time_rationale` | Explains timing strategy |
| `targeting_rationale` | `campaigns[].audience.targeting_rationale` | Explains segment selection |
| `test_hypothesis` | `campaigns[].content.subject_lines.test_hypothesis` | A/B test strategy |
| `hero_image.description` | `campaigns[].content.hero_section.hero_image.description` | Full creative brief |
| `supporting_points` | `campaigns[].content.body.supporting_points` | Content structure |
| `secondary_text/url` | `campaigns[].content.cta.secondary_*` | Secondary CTAs |

---

## Calendar Import Specification Analysis

### Required Fields (Must Include)
```json
{
  "id": "string",           // ✅ Can generate from campaign name + date
  "name": "string",         // ✅ Maps from title
  "date": "ISO 8601",       // ⚠️ Must transform from YYYY-MM-DD to full datetime
  "channel": "enum",        // ❌ Missing - default to "email"
  "type": "enum"            // ✅ Maps from type
}
```

### Recommended Fields (Should Include)
```json
{
  "time": "string",         // ✅ Maps from send_time
  "description": "string",  // ✅ Maps from description
  "status": "enum",         // ❌ Missing - default to "draft"
  "client_id": "string",    // ⚠️ Must extract from client_name
  "client_name": "string"   // ⚠️ Must derive from context (rogue-creamery)
}
```

### Optional Enrichment Fields (Can Include)
The spec provides 45+ optional fields under these categories:
- **Campaign Performance**: `goal`, `estimated_reach`, `priority`
- **Audience**: `audience_segments[]`, `audience_size`, `exclusion_segments`
- **Content**: `subject_line`, `preview_text`, `message_body`, `call_to_action`
- **Visual**: `thumbnail_url`, `creative_assets[]`
- **Tracking**: `tags[]`, `tracking_parameters`, `custom_fields`

**Strategy**: Use `custom_fields` object for mappable enriched data.

---

## Data Architecture Gaps

### Missing in EmailPilot Simple Output:
1. **Event ID**: Need to generate unique IDs (e.g., `{client_name}-{date}-{slug}`)
2. **Channel**: Always email, but not explicitly in simplified output
3. **Status**: Default to "draft" for human review workflow
4. **Client ID/Name**: Present in filename but not in JSON structure
5. **ISO 8601 Full DateTime**: Only have date (YYYY-MM-DD) and time (HH:MM)

### Enriched Data Categories Requiring Preservation:

#### 1. **Strategic Rationales** (Detailed Calendar Only)
- Send time rationale
- Targeting rationale
- A/B test hypotheses
- Campaign sequencing logic

#### 2. **Creative Direction** (Both Outputs)
- Hero image descriptions (not URLs)
- Headline/subheadline copy
- CTA copy variations
- Body copy supporting points

#### 3. **Cross-Channel Content** (Simplified Calendar)
- Secondary messages (SMS/push)
- Offer details
- A/B test ideas

#### 4. **Planning Metadata** (Simplified Calendar)
- Week numbers
- Campaign sequencing
- Seasonal timing strategy

---

## Recommended Dual-Storage Architecture

### Storage Tier 1: Calendar Import JSON (Public, Reviewable)

**Purpose**: Human-editable calendar events for scheduling and basic details
**Format**: Calendar Import Specification compliant JSON
**Storage**: Import directly into calendar application
**Fields**: Required + Recommended + Selected Optional (via custom_fields)

```json
{
  "metadata": {
    "source": "emailpilot-simple",
    "version": "1.0",
    "generated_at": "2025-11-16T01:34:24.000Z",
    "client_id": "rogue-creamery",
    "import_mode": "merge",
    "enriched_context_available": true,
    "enriched_context_key": "rogue-creamery_2025-12-01_2025-12-31_20251116_013424"
  },
  "events": [
    {
      "id": "rogue-creamery-2025-12-02-holiday-gift-guide",
      "name": "The 2025 Holiday Gift Guide",
      "date": "2025-12-02T10:17:00.000Z",
      "channel": "email",
      "type": "promotional",
      "time": "10:17",
      "description": "December kickoff campaign introducing curated holiday gift guide...",
      "status": "draft",
      "client_id": "rogue-creamery",
      "client_name": "Rogue Creamery",
      "content": {
        "subject_line": "🎁 Your December Gift Guide Is Here (Free Shipping Inside)",
        "preview_text": "Curated picks for everyone on your list + free shipping on $75+",
        "call_to_action": {
          "text": "Shop The Gift Guide",
          "url": "https://www.roguecreamery.com/holiday-gift-guide-2025"
        }
      },
      "audience_segments": [
        {
          "name": "Engaged Subscribers (90-day activity)",
          "size": 10000
        }
      ],
      "custom_fields": {
        "week_number": 49,
        "subject_line_b": "The Gifts They'll Actually Love - Holiday Guide 2025",
        "offer_details": "Free standard shipping on orders $75+ through December 10th",
        "secondary_message": "🎁 Your Holiday Gift Guide just dropped! Free shipping on $75+ through 12/10. Shop now: [link]"
      },
      "tags": ["holiday", "gift-guide", "december", "promotional"]
    }
  ]
}
```

### Storage Tier 2: Enriched Context Database (Private, Reference)

**Purpose**: Preserve strategic rationales, creative briefs, and AI-generated insights
**Format**: Extended JSON with full context preservation
**Storage**: Separate file or database keyed by event IDs
**Access**: Available to final brief generation after calendar review

```json
{
  "enriched_context_key": "rogue-creamery_2025-12-01_2025-12-31_20251116_013424",
  "generated_at": "2025-11-16T01:34:24.000Z",
  "client_name": "rogue-creamery",
  "date_range": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "source_files": {
    "detailed_calendar": "outputs/rogue-creamery_2025-12-01_2025-12-31_20251116_013424_calendar_detailed.json",
    "simplified_calendar": "outputs/rogue-creamery_2025-12-01_2025-12-31_20251116_013424_calendar_simplified.json"
  },
  "events": {
    "rogue-creamery-2025-12-02-holiday-gift-guide": {
      "event_id": "rogue-creamery-2025-12-02-holiday-gift-guide",
      "calendar_event_name": "The 2025 Holiday Gift Guide",
      "strategic_context": {
        "send_time_rationale": "Tuesday mid-morning optimal for e-commerce promotional emails (industry benchmarks show 24-28% open rates). :17 offset improves deliverability by avoiding ESP maintenance windows and competitor clustering.",
        "targeting_rationale": "Broad reach for December kickoff to maximize holiday shopping awareness. No historical segment data available - using standard engaged subscriber definition (90-day activity window).",
        "ab_test_hypothesis": "Emoji + explicit offer (Variant A) will outperform benefit-focused emotional appeal (Variant B) by 8-12% open rate due to visual attention grab and immediate value signal. Industry data suggests emoji usage increases opens 5-10% in retail."
      },
      "creative_brief": {
        "hero_section": {
          "headline": "The 2025 Holiday Gift Guide",
          "subheadline": "Thoughtfully Curated Picks For Everyone On Your List",
          "hero_image_description": "Overhead flat-lay shot of 5-7 wrapped gifts in coordinated wrapping paper (deep reds, forest greens, metallic golds) arranged on white marble or rustic wood surface. Incorporate fresh evergreen sprigs, cinnamon sticks, and soft twinkle lights. Warm, inviting lighting (golden hour quality). Leave 40% negative space top-center for H1 text overlay. High-end lifestyle aesthetic matching premium artisan brand positioning.",
          "hero_image_filename": "2025-12-holiday-gift-guide-hero.jpg"
        },
        "body_copy": {
          "main_message": "Finding the perfect gift shouldn't be stressful. We've curated our favorite artisan selections for every person on your list - from cheese connoisseurs to culinary adventurers. Each gift tells a story of craft, quality, and care.",
          "supporting_points": [
            "Hand-selected artisan cheeses and gourmet accompaniments",
            "Beautifully packaged gift sets ready to impress",
            "Free standard shipping on orders $75+ through December 10th",
            "Expert pairing guides included with every order"
          ]
        },
        "cta_strategy": {
          "primary": {
            "text": "Shop The Gift Guide",
            "url": "https://www.roguecreamery.com/holiday-gift-guide-2025"
          },
          "secondary": {
            "text": "Explore Gift Sets",
            "url": "https://www.roguecreamery.com/gift-sets"
          }
        }
      },
      "cross_channel_content": {
        "sms_message": "🎁 Your Holiday Gift Guide just dropped! Free shipping on $75+ through 12/10. Shop now: [link]",
        "push_notification": null
      },
      "planning_metadata": {
        "week_number": 49,
        "campaign_sequence_position": 1,
        "total_campaigns_in_period": 13
      }
    }
  }
}
```

---

## Implementation Recommendations

### 1. **Create Enriched Context Preservation Module**

**File**: `data/enriched_context_manager.py`

**Responsibilities**:
- Extract enriched fields from simplified calendar
- Extract strategic rationales from detailed calendar
- Generate enriched context JSON keyed by event IDs
- Store enriched context alongside calendar imports
- Provide retrieval API for final brief generation

### 2. **Enhance Calendar Output Generation**

**File**: `tools/calendar_tool.py`

**Enhancements**:
- Generate unique event IDs from campaign data
- Add `channel`, `status`, `client_id`, `client_name` defaults
- Transform date + time to ISO 8601 full datetime
- Create both import-compliant JSON AND enriched context JSON
- Link enriched context to import via metadata key

### 3. **Create Calendar Import Transformer**

**File**: `tools/calendar_format_validator.py` (already exists)

**Enhancements**:
- Validate against import specification schema
- Transform EmailPilot Simple → Import format
- Preserve custom_fields for compatible enriched data
- Generate enriched_context reference key in metadata

### 4. **Final Brief Generation Enhancement**

**File**: `agents/brief_agent.py`

**Enhancements**:
- Accept calendar import JSON (human-reviewed/edited)
- Load enriched context by key from enriched context store
- Merge human edits with preserved strategic context
- Generate comprehensive briefs with full creative direction

---

## Workflow Integration

### Current Workflow:
```
1. Planning Agent → Strategic Plan
2. Calendar Agent → Simplified Calendar JSON
3. Brief Agent → Campaign Briefs
```

### Enhanced Workflow with Dual Storage:
```
1. Planning Agent → Strategic Plan
2. Calendar Agent →
   - Import-Compliant Calendar JSON (for human review)
   - Enriched Context JSON (for brief generation)
3. Human Review → Edit Calendar in UI
4. Export Reviewed Calendar → calendar_reviewed.json
5. Brief Agent →
   - Load reviewed calendar (human edits)
   - Load enriched context (preserved AI insights)
   - Merge both sources
   - Generate comprehensive briefs
```

---

## Field Mapping Quick Reference

### EmailPilot Simple → Calendar Import

```python
FIELD_MAPPING = {
    # Direct mappings
    "title": "name",
    "type": "type",
    "description": "description",
    "send_time": "time",

    # Nested mappings
    "subject_line_a": "content.subject_line",
    "preview_text": "content.preview_text",
    "cta_copy": "content.call_to_action.text",
    "segment": "audience_segments[0].name",

    # Custom fields (partial mappings)
    "subject_line_b": "custom_fields.subject_line_b",
    "offer": "custom_fields.offer_details",
    "secondary_message": "custom_fields.secondary_message",
    "week_number": "custom_fields.week_number",

    # Generated fields
    "GENERATED_id": lambda campaign: generate_event_id(campaign),
    "GENERATED_date": lambda campaign: to_iso8601(campaign["date"], campaign["send_time"]),
    "DEFAULT_channel": "email",
    "DEFAULT_status": "draft",
    "CONTEXT_client_id": "from_filename",
    "CONTEXT_client_name": "from_client_mapping",

    # Enriched context (separate storage)
    "ab_test_idea": "ENRICHED_CONTEXT.strategic_context.ab_test_hypothesis",
    "hero_image": "ENRICHED_CONTEXT.creative_brief.hero_section.hero_image_description",
    "hero_h1": "ENRICHED_CONTEXT.creative_brief.hero_section.headline",
    "sub_head": "ENRICHED_CONTEXT.creative_brief.hero_section.subheadline"
}
```

---

## Next Steps

1. ✅ Create `data/enriched_context_manager.py`
2. ✅ Enhance `tools/calendar_tool.py` to generate dual outputs
3. ✅ Update `tools/calendar_format_validator.py` for import spec compliance
4. ✅ Document integration points for brief generation
5. ⏳ Test with Rogue Creamery December 2025 output

---

## Appendix: Calendar Display Issue (9 vs 13 Events)

**Observed**: User reports seeing only 9 events in calendar UI
**Expected**: 13 events in simplified calendar JSON
**Possible Causes**:
1. Calendar import filter rejecting 4 events due to missing required fields
2. Date range filter in UI excluding events outside visible range
3. Campaign type filter in UI (e.g., only showing promotional)
4. Validation errors during import (silent failures)

**Diagnosis Required**:
- Compare visible events in screenshot to JSON event list
- Check calendar import logs for validation errors
- Verify UI date range and filters
- Test import with single event to isolate issue

**Recommendation**: Create import-compliant version first, then re-test calendar display to isolate whether issue is data format or UI filtering.
