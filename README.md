# EmailPilot Simple

A simplified, single-agent workflow for generating campaign calendars and execution briefs using Claude Sonnet 4.5.

## Overview

EmailPilot Simple is a streamlined calendar generation system that orchestrates a three-stage workflow:

1. **Planning** - Strategic calendar generation using historical data and brand intelligence
2. **Structuring** - Conversion of creative planning to v4.0.0 JSON schema
3. **Brief Generation** - Detailed execution briefs for each campaign

### Architecture

```
emailpilot-simple/
├── main.py                 # CLI entry point
├── agents/
│   └── calendar_agent.py   # Single-agent workflow orchestrator
├── tools/
│   ├── calendar_tool.py    # Workflow wrapper with validation
│   └── validator.py        # v4.0.0 JSON schema validator
├── data/
│   ├── mcp_client.py       # Klaviyo data via MCP service
│   ├── rag_client.py       # Brand documents (file-based)
│   ├── firestore_client.py # Client metadata
│   └── mcp_cache.py        # In-memory cache with TTL
└── prompts/
    ├── planning_v5_1_0.yaml
    ├── calendar_structuring_v1_2_1.yaml
    └── brief_generation_v2_2_0.yaml
```

## Features

- **Single-Agent Design** - One CalendarAgent orchestrates all three stages
- **Data Integration** - Combines Klaviyo data (MCP), brand documents (RAG), and client metadata (Firestore)
- **Smart Caching** - In-memory cache reduces redundant API calls across stages
- **Output Validation** - Validates planning output, calendar JSON, and briefs
- **Flexible CLI** - Run full workflow or individual stages for testing
- **YAML Prompts** - Version-controlled prompt configurations

## Installation

### Prerequisites

- Python 3.10 or higher
- Access to:
  - Anthropic API (Claude)
  - Klaviyo API (via MCP service running on localhost:3334)
  - Google Cloud Firestore
  - RAG directory with brand documents

### Install Dependencies

```bash
# Clone or navigate to the emailpilot-simple directory
cd /path/to/klaviyo-audit-automation/emailpilot-simple

# Install Python dependencies
pip install -r requirements.txt
```

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-...
   KLAVIYO_API_KEY=pk_...
   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   ```

3. Source the environment variables:
   ```bash
   source .env  # or use direnv, python-dotenv, etc.
   ```

## Usage

### Basic Usage

Run the full three-stage workflow:

```bash
python main.py --client rogue-creamery --start-date 2025-01-01 --end-date 2025-01-31
```

### Command-Line Arguments

**Required Arguments:**
- `-c, --client` - Client name/slug (e.g., "rogue-creamery")
- `-s, --start-date` - Start date in YYYY-MM-DD format
- `-e, --end-date` - End date in YYYY-MM-DD format

**Optional Arguments:**
- `-o, --output-dir` - Directory to save outputs (default: ./outputs)
- `--no-validate` - Skip output validation
- `--stage {1,2,3}` - Run specific stage only (1=Planning, 2=Structuring, 3=Briefs)
- `--no-save` - Do not save outputs to files
- `--model` - Claude model to use (default: claude-sonnet-4-5-20250929)
- `--prompts-dir` - Path to prompts directory (default: ./prompts)

### Examples

**Full workflow with custom output directory:**
```bash
python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --output-dir ./outputs
```

**Run only Stage 1 (Planning) for testing:**
```bash
python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --stage 1
```

**Skip validation and file saving:**
```bash
python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --no-validate --no-save
```

**Use specific Claude model:**
```bash
python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --model claude-sonnet-4-5-20250929
```

## Client Configuration

### Client Name Mapping

The system maps client slugs to different formats for each data source:

**Example: "rogue-creamery"**
- **MCP Account**: `Rogue_Creamery_Klaviyo` (see mcp_client.py:74-82)
- **RAG Directory**: `rag/rogue_creamery/` (see rag_client.py)
- **Firestore Document**: `clients/rogue_creamery` (see firestore_client.py)

### Adding a New Client

1. **MCP**: Add account mapping in `data/mcp_client.py`
2. **RAG**: Create directory at `../shared_modules/rag/{client_name}/`
3. **Firestore**: Create client document in `clients/{client_name}`

## Output Files

When the workflow completes successfully, it generates:

1. **{workflow_id}_{timestamp}_planning.txt** - Strategic planning output
2. **{workflow_id}_{timestamp}_calendar.json** - v4.0.0 calendar JSON
3. **{workflow_id}_{timestamp}_briefs.txt** - Detailed execution briefs
4. **{workflow_id}_{timestamp}_validation.json** - Validation report

Example: `rogue-creamery_2025-01-01_2025-01-31_20250104_153045_calendar.json`

## Workflow Details

### Stage 1: Planning

**Input:**
- Client name, start date, end date
- MCP data (segments, campaigns, flows, performance)
- RAG data (brand voice, content pillars, product catalog)
- Firestore data (revenue goals, send caps, timezone)

**Process:**
- Fetches all data in parallel
- Caches MCP data for reuse in later stages
- Calls Claude with planning_v5_1_0.yaml prompt
- Generates strategic campaign calendar

**Output:**
- Text-based strategic calendar with campaign ideas, themes, and timing

### Stage 2: Structuring

**Input:**
- Planning output from Stage 1
- Client configuration

**Process:**
- Calls Claude with calendar_structuring_v1_2_1.yaml prompt
- Converts creative planning to structured JSON
- Validates against v4.0.0 schema

**Output:**
- Structured calendar JSON following v4.0.0 schema
- Each campaign includes: campaign_id, name, send_date, channel, type, audience

### Stage 3: Brief Generation

**Input:**
- Calendar JSON from Stage 2
- Cached MCP data (performance, segments)
- RAG data (design guidelines, product info)

**Process:**
- Calls Claude with brief_generation_v2_2_0.yaml prompt
- Generates execution briefs for each campaign
- Includes subject lines, preview text, audience specs, send times

**Output:**
- Detailed execution briefs for each campaign
- Ready for copywriting and design teams

## Validation

The system validates outputs at each stage:

**Planning Output:**
- Minimum length (500 characters)
- Presence of key sections (strategic, campaign, audience, timing)
- Date references

**Calendar JSON:**
- v4.0.0 schema compliance
- Required fields (version, client_name, campaigns, metadata)
- Valid date formats (YYYY-MM-DD)
- Valid channels (email, sms)
- Valid campaign types (promotional, educational, seasonal, etc.)

**Briefs Output:**
- Minimum length (300 chars per campaign)
- Presence of key elements (subject, preview, audience, send time)

## Error Handling

The system provides detailed error messages for:
- Missing environment variables
- Invalid date ranges (max 90 days)
- MCP service connection failures
- Claude API errors
- JSON parsing failures
- Validation failures

## Development

### Running Tests

```bash
# Test with a sample client
python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --stage 1
```

### Logging

The system uses Python's logging framework:
- Logs to stdout with timestamps
- Log level: INFO (configurable in main.py)
- Each component logs initialization, API calls, and results

### Modifying Prompts

1. Edit YAML files in `prompts/` directory
2. Each prompt has `system_prompt` and `user_prompt` sections
3. Use `{{variable}}` syntax for variable substitution
4. Test changes by running specific stages with `--stage` flag

## Troubleshooting

### "Missing required environment variables"
- Ensure `.env` file exists with all three required variables
- Source the file: `source .env`

### "MCP service connection failed"
- Verify MCP service is running on localhost:3334
- Check Klaviyo API key is valid

### "Calendar validation failed"
- Check Stage 2 output for JSON formatting errors
- Verify prompt is generating valid v4.0.0 schema
- Use `--no-validate` to skip validation for testing

### "Workflow failed at Stage X"
- Check logs for specific error messages
- Run individual stage with `--stage X` for debugging
- Verify all data sources are accessible

## License

Internal use only. Part of the Klaviyo Audit Automation project.

## Support

For issues or questions, contact the development team.
