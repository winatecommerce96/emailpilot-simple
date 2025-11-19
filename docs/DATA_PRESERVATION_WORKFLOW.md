# EmailPilot Simple - Complete Data Preservation Workflow

**Version**: 2.0
**Last Updated**: 2025-11-16
**Status**: Production Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Complete Workflow](#complete-workflow)
4. [Data Storage Tiers](#data-storage-tiers)
5. [File Outputs Reference](#file-outputs-reference)
6. [Enriched Context Structure](#enriched-context-structure)
7. [Integration Points](#integration-points)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)

---

## Executive Summary

EmailPilot Simple now implements a **dual-storage architecture** that preserves 100% of AI-generated strategic, creative, and planning data throughout the workflow:

- **Tier 1**: Calendar Import JSON (human-editable, import-compliant)
- **Tier 2**: Enriched Context JSON (AI-generated insights preserved for brief generation)

This architecture ensures that:
- ✅ Calendars can be imported into external calendar apps with full spec compliance
- ✅ Strategic rationales and creative direction are never lost
- ✅ Human edits in the calendar UI are preserved
- ✅ Final brief generation has access to complete AI-generated context
- ✅ All data flows automatically without manual intervention

---

## Architecture Overview

### Dual-Storage Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    EmailPilot Simple Workflow                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │      Planning Agent (RAG-Enhanced)      │
         │  • Strategic plan generation            │
         │  • Client brand voice analysis          │
         │  • Campaign sequencing logic            │
         └────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │     Calendar Agent (Dual Output)        │
         │                                         │
         │  Generates THREE formats:               │
         │  1. Detailed Calendar (full context)    │
         │  2. Simplified Calendar (import spec)   │
         │  3. Enriched Context (preserved data)   │
         └────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────────┐       ┌─────────────────────┐
    │  TIER 1: Calendar   │       │  TIER 2: Enriched   │
    │  Import JSON        │       │  Context JSON       │
    │                     │       │                     │
    │  • Import-compliant │       │  • Strategic data   │
    │  • Human-editable   │       │  • Creative briefs  │
    │  • Calendar UI      │       │  • Rationales       │
    │  • Custom fields    │       │  • Planning context │
    └─────────────────────┘       └─────────────────────┘
              │                               │
              │    ┌─────────────────┐       │
              └───▶│  Calendar App   │       │
                   │  Human Review   │       │
                   │  & Editing      │       │
                   └─────────────────┘       │
                            │                 │
                            ▼                 │
                   ┌─────────────────┐       │
                   │ Reviewed        │       │
                   │ Calendar Export │       │
                   └─────────────────┘       │
                            │                 │
                            └────┬────────────┘
                                 ▼
                   ┌──────────────────────────┐
                   │   Brief Agent (Merge)    │
                   │                          │
                   │  Merges:                 │
                   │  • Human edits (Tier 1)  │
                   │  • AI context (Tier 2)   │
                   │                          │
                   │  Generates:              │
                   │  • Comprehensive briefs  │
                   └──────────────────────────┘
```

---

## Complete Workflow

### Phase 1: Planning & Strategy

**Triggers**: User runs workflow with client name and date range

```bash
python main.py --client rogue-creamery --start-date 2025-12-01 --end-date 2025-12-31
```

**Planning Agent Tasks**:
1. Loads client brand voice from RAG system
2. Analyzes seasonal context and marketing calendar
3. Generates strategic plan with campaign sequencing
4. Outputs: `{workflow_id}_planning.txt`

**Data Generated** (Planning Phase):
- Client brand voice guidelines
- Campaign calendar structure
- Strategic rationales for timing and sequencing

---

### Phase 2: Calendar Generation (Triple Output)

**Calendar Agent Tasks**:

1. **Generate Detailed Calendar** (Full Context)
   - Complete campaign specifications
   - Strategic rationales for every decision
   - Creative briefs with full direction
   - Outputs: `{workflow_id}_calendar_detailed.json`

2. **Generate Simplified Calendar** (Import Format)
   - Calendar Import Specification compliant
   - Essential campaign details
   - Transformed for human review
   - Outputs: `{workflow_id}_calendar_simplified.json`

3. **Generate Enriched Context** ← NEW AUTOMATIC STEP
   - Extracts unmappable strategic data from both calendars
   - Preserves creative direction and rationales
   - Links to calendar events via unique event IDs
   - Outputs: `{workflow_id}_enriched_context.json`

4. **Generate App Format Calendar**
   - Alternative transformation of detailed calendar
   - Outputs: `{workflow_id}_calendar_app.json`

**Automatic Enriched Context Generation** (lines 671-704 in `tools/calendar_tool.py`):

```python
# Extract client name from workflow_id
client_name = workflow_id.split('_')[0]

# Instantiate enriched context manager
enriched_manager = EnrichedContextManager(output_dir=str(self.output_dir))

# Create enriched context from both calendar formats
enriched_context = enriched_manager.create_enriched_context(
    client_name=client_name,
    simplified_calendar=result["simplified_calendar"],
    detailed_calendar=result["detailed_calendar"],
    context_key=workflow_id  # Links calendars to enriched context
)

# Save to GCS and local storage
enriched_manager.save_enriched_context(enriched_context)
```

**Event ID Linkage**:
Each calendar event gets a unique ID: `{client_name}-{date}-{slug}`

Example: `rogue-creamery-2025-12-02-holiday-gift-guide`

This ID links:
- Calendar import event → Enriched context event
- Enables retrieval of preserved data for brief generation

---

### Phase 3: Human Review & Editing

**Calendar App Import**:

1. Import `{workflow_id}_calendar_simplified.json` into calendar application
2. Human reviewer can:
   - Edit campaign names, dates, descriptions
   - Adjust send times
   - Add/remove campaigns
   - Modify subject lines and preview text
   - Change audience segments

**Enriched Context Metadata** (in calendar JSON):

```json
{
  "metadata": {
    "enriched_context_available": true,
    "enriched_context_key": "rogue-creamery_2025-12-01_2025-12-31_20251116_013424"
  }
}
```

This metadata tells the brief generation system where to find preserved context.

**Human Edits Are Preserved**:
- All changes made in the calendar UI are saved
- Export reviewed calendar as `{workflow_id}_calendar_reviewed.json`
- Enriched context remains untouched in separate file

---

### Phase 4: Final Brief Generation

**Brief Agent Tasks** (Future Enhancement):

1. Load reviewed calendar (human edits)
2. Load enriched context by key
3. Merge both sources using `EnrichedContextManager.merge_with_reviewed_calendar()`
4. Generate comprehensive briefs with:
   - Human-approved campaign details (from reviewed calendar)
   - AI-generated strategic rationales (from enriched context)
   - Complete creative direction (from enriched context)
   - Cross-channel content (from enriched context)

**Merge Logic** (implemented in `data/enriched_context_manager.py`):

```python
def merge_with_reviewed_calendar(
    self,
    reviewed_calendar: Dict[str, Any],
    context_key: str
) -> List[Dict[str, Any]]:
    """
    Merge human-reviewed calendar with enriched context

    Returns:
        List of merged event objects ready for brief generation
    """
    # For each event in reviewed calendar:
    # 1. Find matching enriched context by event_id
    # 2. Merge: reviewed data takes precedence, enriched fills gaps
    # 3. Return complete event with both sources
```

**Current Brief Generation** (Checkpoint Workflow):
- Currently generates briefs from detailed calendar only
- **Future**: Will integrate enriched context merge for complete data

---

## Data Storage Tiers

### Tier 1: Calendar Import JSON

**Purpose**: Human-reviewable, editable calendar events

**Location**: `outputs/{workflow_id}_calendar_simplified.json`

**Schema Compliance**: Fully compliant with Calendar Import Specification v4.0.0

**Contents**:
- Required fields: id, name, date, channel, type
- Recommended fields: time, description, status, client_id, client_name
- Content fields: subject_line, preview_text, call_to_action
- Audience: audience_segments array
- Custom fields: subject_line_b, offer_details, secondary_message, week_number
- Tags array

**Example Event**:

```json
{
  "id": "rogue-creamery-2025-12-02-holiday-gift-guide",
  "name": "The 2025 Holiday Gift Guide",
  "date": "2025-12-02T10:17:00.000Z",
  "channel": "email",
  "type": "promotional",
  "time": "10:17",
  "description": "December kickoff campaign introducing curated holiday gift guide...",
  "status": "draft",
  "content": {
    "subject_line": "🎁 Your December Gift Guide Is Here (Free Shipping Inside)",
    "preview_text": "Curated picks for everyone on your list + free shipping on $75+",
    "call_to_action": {
      "text": "Shop The Gift Guide"
    }
  },
  "audience_segments": [
    {
      "name": "Engaged Subscribers (90-day activity)"
    }
  ],
  "custom_fields": {
    "week_number": 49,
    "subject_line_b": "The Gifts They'll Actually Love - Holiday Guide 2025"
  },
  "tags": ["holiday", "gift-guide", "december"]
}
```

---

### Tier 2: Enriched Context JSON

**Purpose**: Preserve strategic, creative, and planning data not compatible with import spec

**Location**: `outputs/{workflow_id}_enriched_context.json`

**Schema**: Custom EmailPilot Simple enriched context schema

**Contents** (per event):

1. **Strategic Context**
   - `send_time_rationale`: Why this send time was chosen
   - `targeting_rationale`: Why this audience segment was selected
   - `ab_test_hypothesis`: A/B test strategy and expected outcomes
   - `campaign_sequence_rationale`: How this fits in campaign sequence
   - `seasonal_timing_strategy`: Seasonal context

2. **Creative Brief**
   - `hero_section`: Headline, subheadline, hero image description/filename
   - `body_copy`: Main message and supporting points
   - `cta_strategy`: Primary and secondary CTAs with URLs
   - `visual_assets`: Detailed creative direction
   - `brand_guidelines`: Brand voice application

3. **Cross-Channel Content**
   - `sms_message`: SMS variant of campaign
   - `push_notification`: Push notification text
   - `in_app_message`: In-app message content
   - `social_media_copy`: Social media variants

4. **Planning Metadata**
   - `week_number`: Calendar week for planning
   - `campaign_sequence_position`: Position in sequence (1 of 13)
   - `total_campaigns_in_period`: Total campaigns in date range
   - `dependencies`: Dependent campaigns
   - `related_campaigns`: Related campaign IDs

5. **Raw Data**
   - `raw_simplified_event`: Original simplified calendar event
   - `raw_detailed_campaign`: Original detailed calendar campaign

**Example Enriched Event**:

```json
{
  "rogue-creamery-2025-12-02-holiday-gift-guide": {
    "event_id": "rogue-creamery-2025-12-02-holiday-gift-guide",
    "calendar_event_name": "The 2025 Holiday Gift Guide",
    "strategic_context": {
      "send_time_rationale": "Tuesday mid-morning optimal for e-commerce promotional emails (industry benchmarks show 24-28% open rates). :17 offset improves deliverability by avoiding ESP maintenance windows and competitor clustering.",
      "targeting_rationale": "Broad reach for December kickoff to maximize holiday shopping awareness. No historical segment data available - using standard engaged subscriber definition (90-day activity window).",
      "ab_test_hypothesis": "Emoji + explicit offer (Variant A) will outperform benefit-focused emotional appeal (Variant B) by 8-12% open rate due to visual attention grab and immediate value signal."
    },
    "creative_brief": {
      "hero_section": {
        "headline": "The 2025 Holiday Gift Guide",
        "subheadline": "Thoughtfully Curated Picks For Everyone On Your List",
        "hero_image_description": "Overhead flat-lay shot of 5-7 wrapped gifts in coordinated wrapping paper (deep reds, forest greens, metallic golds) arranged on white marble or rustic wood surface...",
        "hero_image_filename": "2025-12-holiday-gift-guide-hero.jpg"
      },
      "body_copy": {
        "main_message": "Finding the perfect gift shouldn't be stressful. We've curated our favorite artisan selections...",
        "supporting_points": [
          "Hand-selected artisan cheeses and gourmet accompaniments",
          "Beautifully packaged gift sets ready to impress",
          "Free standard shipping on orders $75+ through December 10th"
        ]
      },
      "cta_strategy": {
        "primary": {
          "text": "Shop The Gift Guide",
          "url": "https://www.roguecreamery.com/holiday-gift-guide-2025"
        }
      }
    },
    "cross_channel_content": {
      "sms_message": "🎁 Your Holiday Gift Guide just dropped! Free shipping on $75+ through 12/10. Shop now: [link]"
    },
    "planning_metadata": {
      "week_number": 49,
      "campaign_sequence_position": 1,
      "total_campaigns_in_period": 13
    }
  }
}
```

---

## File Outputs Reference

### Standard Workflow Outputs

When you run: `python main.py --client {client} --start-date {date} --end-date {date}`

**Generated Files** (all prefixed with workflow_id):

1. **`{workflow_id}_planning.txt`**
   - Strategic plan text
   - Size: ~30KB
   - Format: Plain text

2. **`{workflow_id}_calendar_detailed.json`**
   - Complete campaign specifications with rationales
   - Size: ~80KB for 13 campaigns
   - Format: JSON

3. **`{workflow_id}_calendar_simplified.json`**
   - Calendar Import Specification compliant
   - Size: ~19KB for 13 campaigns
   - Format: JSON

4. **`{workflow_id}_enriched_context.json`** ← NEW
   - Preserved strategic and creative context
   - Size: ~50-100KB depending on detail
   - Format: JSON

5. **`{workflow_id}_calendar_app.json`**
   - Alternative calendar transformation
   - Size: ~3KB
   - Format: JSON

6. **`{workflow_id}_briefs.txt`**
   - Generated campaign briefs
   - Size: ~12KB
   - Format: Plain text

7. **`{workflow_id}_validation.json`**
   - Validation results
   - Size: ~112B
   - Format: JSON

**Storage Locations**:
- **Local**: `./outputs/` directory
- **GCS**: `gs://{bucket}/outputs/` (if configured)

---

## Enriched Context Structure

### Top-Level Structure

```json
{
  "enriched_context_key": "rogue-creamery_2025-12-01_2025-12-31_20251116_013424",
  "generated_at": "2025-11-16T01:34:24.000Z",
  "client_name": "rogue-creamery",
  "date_range": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "total_events": 13,
  "source_files": {
    "simplified_calendar": "Loaded from memory",
    "detailed_calendar": "Loaded from memory"
  },
  "events": {
    "{event_id}": { /* EnrichedEventContext */ },
    "{event_id}": { /* EnrichedEventContext */ }
  }
}
```

### Event Structure (EnrichedEventContext)

See Tier 2 example above for complete event structure.

**Python Dataclasses** (defined in `data/enriched_context_manager.py`):

```python
@dataclass
class StrategicContext:
    send_time_rationale: Optional[str] = None
    targeting_rationale: Optional[str] = None
    ab_test_hypothesis: Optional[str] = None
    campaign_sequence_rationale: Optional[str] = None
    seasonal_timing_strategy: Optional[str] = None

@dataclass
class CreativeBrief:
    hero_section: Optional[Dict[str, Any]] = None
    body_copy: Optional[Dict[str, Any]] = None
    cta_strategy: Optional[Dict[str, Any]] = None
    visual_assets: Optional[Dict[str, Any]] = None
    brand_guidelines: Optional[Dict[str, str]] = None

@dataclass
class CrossChannelContent:
    sms_message: Optional[str] = None
    push_notification: Optional[str] = None
    in_app_message: Optional[str] = None
    social_media_copy: Optional[str] = None

@dataclass
class PlanningMetadata:
    week_number: Optional[int] = None
    campaign_sequence_position: Optional[int] = None
    total_campaigns_in_period: Optional[int] = None
    dependencies: Optional[List[str]] = None
    related_campaigns: Optional[List[str]] = None

@dataclass
class EnrichedEventContext:
    event_id: str
    calendar_event_name: str
    strategic_context: StrategicContext
    creative_brief: CreativeBrief
    cross_channel_content: CrossChannelContent
    planning_metadata: PlanningMetadata
    raw_simplified_event: Optional[Dict[str, Any]] = None
    raw_detailed_campaign: Optional[Dict[str, Any]] = None
```

---

## Integration Points

### 1. Calendar Agent → Enriched Context Manager

**Location**: `tools/calendar_tool.py`, lines 671-704 in `_save_outputs()` method

**Trigger**: Automatically after simplified and detailed calendars are generated

**Process**:
1. Extract client_name from workflow_id
2. Instantiate EnrichedContextManager
3. Call `create_enriched_context()` with both calendar formats
4. Save enriched context to GCS and local storage
5. Log success/errors

**Code Reference**: See Phase 2 workflow section above

---

### 2. Enriched Context Manager → Brief Agent (Future)

**Location**: `agents/brief_agent.py` (enhancement pending)

**Trigger**: Manual or automatic after calendar review/export

**Process**:
1. Load reviewed calendar JSON
2. Extract enriched_context_key from metadata
3. Call `EnrichedContextManager.load_enriched_context(context_key)`
4. Call `EnrichedContextManager.merge_with_reviewed_calendar(reviewed_calendar, context_key)`
5. Generate briefs from merged data

**Current State**: Brief agent currently uses detailed calendar directly. Enriched context merge integration is planned but not yet implemented.

---

### 3. Calendar App → Enriched Context (Metadata Link)

**Location**: Calendar Import JSON metadata section

**Purpose**: Link imported calendar to preserved enriched context

**Implementation**:

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
  }
}
```

**Calendar App Requirements**: See `docs/CALENDAR_APP_ENHANCEMENTS.md` for details on:
- Import metadata support
- Event ID preservation
- Custom fields support
- Export format specifications

---

## Usage Examples

### Example 1: Run Full Workflow with Automatic Enriched Context

```bash
# Navigate to emailpilot-simple directory
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple

# Activate virtual environment
source .venv/bin/activate

# Run workflow
python main.py \
  --client rogue-creamery \
  --start-date 2025-12-01 \
  --end-date 2025-12-31

# Files generated:
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_planning.txt
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_calendar_detailed.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_calendar_simplified.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_enriched_context.json ← NEW
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_calendar_app.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_briefs.txt
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_validation.json
```

---

### Example 2: Checkpoint Workflow (Calendar Only, for Review)

```bash
# Generate calendar for human review, skip brief generation
python main.py \
  --client rogue-creamery \
  --start-date 2025-12-01 \
  --end-date 2025-12-31 \
  --checkpoint calendar

# Files generated (no briefs):
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_planning.txt
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_calendar_detailed.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_calendar_simplified.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_enriched_context.json
# - rogue-creamery_2025-12-01_2025-12-31_{timestamp}_validation.json

# Import simplified calendar into calendar app for review
# Enriched context is preserved for later brief generation
```

---

### Example 3: Load and Use Enriched Context (Python)

```python
from data.enriched_context_manager import EnrichedContextManager

# Initialize manager
manager = EnrichedContextManager(output_dir="./outputs")

# Load enriched context by key
context_key = "rogue-creamery_2025-12-01_2025-12-31_20251116_013424"
enriched_context = manager.load_enriched_context(context_key)

# Get specific event enriched context
event_id = "rogue-creamery-2025-12-02-holiday-gift-guide"
event_context = manager.get_event_enriched_context(context_key, event_id)

print(event_context['strategic_context']['send_time_rationale'])
# Output: "Tuesday mid-morning optimal for e-commerce promotional emails..."

print(event_context['creative_brief']['hero_section']['headline'])
# Output: "The 2025 Holiday Gift Guide"
```

---

### Example 4: Merge Reviewed Calendar with Enriched Context (Python)

```python
from data.enriched_context_manager import EnrichedContextManager
import json

# Load reviewed calendar (after human edits in calendar app)
with open('outputs/reviewed_calendar.json', 'r') as f:
    reviewed_calendar = json.load(f)

# Initialize manager
manager = EnrichedContextManager(output_dir="./outputs")

# Merge reviewed calendar with enriched context
context_key = "rogue-creamery_2025-12-01_2025-12-31_20251116_013424"
merged_events = manager.merge_with_reviewed_calendar(
    reviewed_calendar=reviewed_calendar,
    context_key=context_key
)

# merged_events contains:
# - calendar_data: Human-reviewed/edited data (takes precedence)
# - enriched_context: Preserved AI-generated strategic/creative data
# - event_id: Unique identifier linking both sources

# Use merged_events for comprehensive brief generation
for event in merged_events:
    print(f"Campaign: {event['calendar_data']['name']}")
    print(f"Rationale: {event['enriched_context']['strategic_context']['send_time_rationale']}")
```

---

## Troubleshooting

### Issue 1: Enriched Context File Not Generated

**Symptoms**:
- Workflow completes successfully
- Simplified and detailed calendars are generated
- No `{workflow_id}_enriched_context.json` file in outputs

**Diagnosis**:

```bash
# Check workflow logs for enriched context errors
grep -i "enriched context" outputs/{workflow_id}_*.log

# Check if EnrichedContextManager import is present
grep "from data.enriched_context_manager" tools/calendar_tool.py

# Verify enriched context generation code exists
grep -A 10 "Generate and save enriched context" tools/calendar_tool.py
```

**Common Causes**:
1. EnrichedContextManager import missing (line 17 of calendar_tool.py)
2. Enriched context generation code not present (lines 671-704 of calendar_tool.py)
3. Exception during enriched context generation (check logs)
4. Workflow ran before integration was deployed

**Solutions**:
1. Ensure `calendar_tool.py` has import: `from data.enriched_context_manager import EnrichedContextManager`
2. Ensure `_save_outputs()` method includes enriched context generation code
3. Check exception logs and fix underlying issue (e.g., missing data fields)
4. Re-run workflow to test integration

---

### Issue 2: Event ID Mismatch Between Calendar and Enriched Context

**Symptoms**:
- Cannot find enriched context for specific event
- Event IDs don't match between calendar and enriched context

**Diagnosis**:

```bash
# Compare event IDs in both files
jq '.events[].id' outputs/{workflow_id}_calendar_simplified.json

jq '.events | keys[]' outputs/{workflow_id}_enriched_context.json
```

**Common Causes**:
1. Event title changed during calendar generation
2. Date format mismatch
3. Client name extraction issue

**Solutions**:
1. Ensure event IDs use consistent slug generation algorithm
2. Use same workflow_id as enriched_context_key
3. Verify client_name extraction: `workflow_id.split('_')[0]`

---

### Issue 3: Missing Strategic Context in Enriched Data

**Symptoms**:
- Enriched context file exists
- Strategic rationales are null or empty

**Diagnosis**:

```bash
# Check if detailed calendar contains rationales
jq '.campaigns[0] | keys' outputs/{workflow_id}_calendar_detailed.json

# Check enriched context for null fields
jq '.events[] | .strategic_context' outputs/{workflow_id}_enriched_context.json
```

**Common Causes**:
1. Detailed calendar doesn't contain rationales (Calendar Agent issue)
2. Field extraction logic incorrect
3. Field names changed in calendar schema

**Solutions**:
1. Verify detailed calendar contains strategic fields (see `prompts/calendar_structuring_v1_2_2.yaml`)
2. Update field extraction logic in `EnrichedContextManager.extract_strategic_context()`
3. Regenerate calendar with correct prompt version

---

### Issue 4: Calendar Import Missing Custom Fields

**Symptoms**:
- Enriched context preserved successfully
- Calendar import JSON missing custom_fields

**Diagnosis**:

```bash
# Check if custom_fields exist in simplified calendar
jq '.events[0].custom_fields' outputs/{workflow_id}_calendar_simplified.json
```

**Common Causes**:
1. Custom fields not mapped in calendar transformation
2. Calendar Import Spec version doesn't support custom_fields

**Solutions**:
1. Verify Calendar Agent includes custom_fields in simplified output
2. Check `tools/calendar_format_validator.py` for custom_fields support
3. Update calendar transformation logic if needed

---

### Issue 5: Cannot Merge Reviewed Calendar with Enriched Context

**Symptoms**:
- Reviewed calendar loads successfully
- `merge_with_reviewed_calendar()` fails or returns empty list

**Diagnosis**:

```python
from data.enriched_context_manager import EnrichedContextManager

manager = EnrichedContextManager(output_dir="./outputs")

# Check if enriched context exists
context = manager.load_enriched_context(context_key)
print(f"Found {len(context.get('events', {}))} events in enriched context")

# Check if reviewed calendar has event IDs
print(f"Event IDs in reviewed calendar: {[e.get('id') for e in reviewed_calendar.get('events', [])]}")
```

**Common Causes**:
1. Event IDs removed during calendar review/export
2. Wrong enriched_context_key used
3. Enriched context file not found

**Solutions**:
1. Ensure calendar app preserves event IDs during export (see CALENDAR_APP_ENHANCEMENTS.md)
2. Verify enriched_context_key matches workflow_id
3. Check file paths and context_key spelling

---

## Related Documentation

- **Field Mapping Analysis**: `docs/FIELD_MAPPING_ANALYSIS.md`
- **Calendar App Enhancements**: `docs/CALENDAR_APP_ENHANCEMENTS.md`
- **Calendar Import Specification**: `docs/calendar_import_spec_v4.0.0.md`
- **EnrichedContextManager API**: `data/enriched_context_manager.py` (inline documentation)
- **Calendar Tool Integration**: `tools/calendar_tool.py` (lines 671-704)

---

## Appendix: Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PLANNING AGENT                                 │
│                                                                       │
│  Input:                                                               │
│  • Client name (e.g., 'rogue-creamery')                              │
│  • Date range (2025-12-01 to 2025-12-31)                            │
│  • RAG-retrieved brand voice                                         │
│                                                                       │
│  Output:                                                              │
│  • Strategic plan text file                                          │
│  • Campaign sequencing logic                                         │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        CALENDAR AGENT                                 │
│                                                                       │
│  Input:                                                               │
│  • Strategic plan                                                     │
│  • Client brand voice                                                │
│  • Date range                                                         │
│                                                                       │
│  Generates:                                                           │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ 1. Detailed Calendar (80KB)                            │         │
│  │    • Complete campaign specifications                   │         │
│  │    • Strategic rationales for all decisions            │         │
│  │    • Creative briefs with full direction               │         │
│  │    • A/B test hypotheses                               │         │
│  └────────────────────────────────────────────────────────┘         │
│                             │                                         │
│                             ▼                                         │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ 2. Simplified Calendar (19KB)                          │         │
│  │    • Calendar Import Spec compliant                    │         │
│  │    • Essential campaign details                        │         │
│  │    • Custom fields for partial enrichment              │         │
│  └────────────────────────────────────────────────────────┘         │
│                             │                                         │
│                             ▼                                         │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ 3. Enriched Context (50-100KB) ← NEW                  │         │
│  │    • Extracted from BOTH calendars                     │         │
│  │    • Strategic rationales preserved                    │         │
│  │    • Creative briefs preserved                         │         │
│  │    • Cross-channel content preserved                   │         │
│  │    • Planning metadata preserved                       │         │
│  │    • Linked via event IDs                              │         │
│  └────────────────────────────────────────────────────────┘         │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    DUAL STORAGE LAYER                                 │
│                                                                       │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │ TIER 1: Calendar Import │    │ TIER 2: Enriched Context│        │
│  │                         │    │                         │        │
│  │ • GCS Bucket            │    │ • GCS Bucket            │        │
│  │ • Local ./outputs/      │    │ • Local ./outputs/      │        │
│  │                         │    │                         │        │
│  │ Files:                  │    │ Files:                  │        │
│  │ • *_simplified.json     │    │ • *_enriched_context.json│       │
│  │ • *_app.json            │    │                         │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    CALENDAR APP (Human Review)                        │
│                                                                       │
│  Imports:                                                             │
│  • {workflow_id}_calendar_simplified.json                            │
│                                                                       │
│  Human Actions:                                                       │
│  • Review campaign details                                           │
│  • Edit names, dates, times, descriptions                           │
│  • Modify subject lines and preview text                            │
│  • Adjust audience segments                                          │
│  • Add/remove campaigns                                              │
│                                                                       │
│  Exports:                                                             │
│  • {workflow_id}_calendar_reviewed.json                              │
│    (preserves event IDs for enriched context linkage)               │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BRIEF AGENT (Merge & Generate)                     │
│                                                                       │
│  Inputs:                                                              │
│  1. Reviewed Calendar (human edits)                                  │
│  2. Enriched Context (preserved AI data)                             │
│                                                                       │
│  Process:                                                             │
│  • Load reviewed calendar                                            │
│  • Load enriched context by key                                      │
│  • Merge via EnrichedContextManager.merge_with_reviewed_calendar()  │
│  • For each event:                                                   │
│    - Use human-edited details (takes precedence)                    │
│    - Enrich with AI-generated rationales                            │
│    - Include complete creative direction                            │
│    - Add cross-channel content                                      │
│                                                                       │
│  Outputs:                                                             │
│  • Comprehensive campaign briefs                                     │
│  • Strategic rationales for all decisions                            │
│  • Complete creative direction                                       │
│  • Cross-channel messaging guidelines                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

**End of Documentation**

For questions or issues, please refer to:
- GitHub Issues: [Project Repository]
- Documentation: `/docs/` directory
- Code Comments: Inline documentation in source files
