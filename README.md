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
- **Enhanced RAG with Vector Search** - Semantic retrieval using FAISS and OpenAI embeddings with automatic file-based fallback
- **Smart Caching** - In-memory cache reduces redundant API calls across stages
- **Output Validation** - Validates planning output, calendar JSON, and briefs
- **Flexible CLI** - Run full workflow or individual stages for testing
- **YAML Prompts** - Version-controlled prompt configurations

## Enhanced RAG with Vector Search

The system integrates with the production-ready LangChain RAG orchestrator from `emailpilot-orchestrator` to provide advanced semantic search capabilities for brand intelligence documents.

### Dual-Mode Operation

**Vector Search Mode (FAISS + OpenAI):**
- Semantic similarity search using FAISS vector database
- OpenAI text-embedding-ada-002 embeddings
- Query-based retrieval with relevance scoring
- Maximum Marginal Relevance (MMR) for diverse results
- Automatic client data isolation (prevents bleed between accounts)

**File-Based Fallback Mode:**
- Automatic fallback when OpenAI API key not configured
- Direct file system access to RAG corpus
- Keyword-based retrieval patterns
- Zero external dependencies for basic operation

### Configuration

**Enable Vector Search (Optional):**
```bash
# Add to .env file
OPENAI_API_KEY=sk-...
```

**Disable Vector Search:**
```bash
# Simply omit OPENAI_API_KEY from .env
# System automatically uses file-based fallback
```

### Architecture Integration

The `EnhancedRAGClient` (`data/enhanced_rag_client.py`) provides:

1. **Backward Compatibility** - Maintains original `RAGClient` interface
   - `get_all_data(client_name)` - Fetch all brand documents
   - `format_for_prompt(client_name)` - Format for Claude prompts
   - `get_brand_voice(client_name)` - Get brand voice guidelines
   - `get_content_pillars(client_name)` - Get content pillars
   - `get_product_catalog(client_name)` - Get product catalog

2. **Enhanced Capabilities** - New methods for advanced use cases
   - `retrieve_semantic(client_name, query, top_k, score_threshold)` - Query-specific retrieval
   - `get_stats(client_name)` - RAG system statistics

3. **Resilience Patterns**
   - Automatic fallback on import failures
   - Graceful degradation when vector search unavailable
   - Clear logging of which mode is active

### Document Categories

The system retrieves seven categories of brand intelligence:

- **Brand Voice** - Tone of voice, writing style, messaging guidelines
- **Content Pillars** - Key themes and topics for content
- **Product Catalog** - Product details, descriptions, pricing
- **Design Guidelines** - Visual standards, colors, fonts, imagery
- **Previous Campaigns** - Historical campaign examples and performance
- **Target Audience** - Customer personas, demographics, preferences
- **Seasonal Themes** - Seasonal events, holidays, calendar-specific content

### How It Works

**Initialization:**
```python
# In main.py and calendar_agent.py
rag_client = EnhancedRAGClient(
    rag_base_path='/path/to/rag/corpus',
    use_vector_search=True,  # Enable vector search if OpenAI key available
    openai_api_key=config.get('openai_api_key')  # Optional
)
```

**Automatic Mode Selection:**
```
# With OPENAI_API_KEY:
✅ Enhanced RAG initialized with vector search (FAISS + OpenAI)

# Without OPENAI_API_KEY:
📁 Using file-based RAG (vector search unavailable)
WARNING: OPENAI_API_KEY not set - RAG will use file-based fallback instead of vector search
```

**Data Retrieval:**
```python
# Fetch all brand documents (async)
rag_data = await rag_client.get_all_data("rogue-creamery")

# Format for Claude prompts (async)
rag_formatted = await rag_client.format_for_prompt("rogue-creamery")

# Query-specific semantic retrieval (async, vector search only)
results = await rag_client.retrieve_semantic(
    client_name="rogue-creamery",
    query="holiday campaign messaging guidelines",
    top_k=5,
    score_threshold=0.5
)
```

### Benefits of Vector Search

**Semantic Understanding:**
- Finds documents by meaning, not just keywords
- "holiday campaigns" matches "seasonal messaging," "festive content," "end-of-year promotions"
- Better context for Claude's planning stage

**Relevance Ranking:**
- Returns most relevant chunks based on similarity scores
- Reduces noise in prompts
- Improves Claude's output quality

**Query-Specific Retrieval:**
- Calendar agent can ask targeted questions
- "What are the brand's color palette guidelines?"
- "Show me successful promotional campaign examples"

### Migration Notes

The enhanced RAG system is **fully backward compatible**:
- Existing code using `RAGClient` works without changes
- All original methods have the same signatures (now async)
- File-based mode provides identical functionality to original implementation
- Vector search is purely additive - no breaking changes

### Performance

**Vector Search Mode:**
- First query: ~200-500ms (embedding generation + FAISS search)
- Cached queries: ~50-100ms (FAISS search only)
- Benefits from LangChain's built-in caching

**File-Based Mode:**
- All queries: ~10-50ms (direct file system access)
- No external API calls
- Suitable for development and testing

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
- MCP data validation failures (new)
- Claude API errors
- JSON parsing failures
- Validation failures

### MCP Data Validation

**Critical Requirement:** The workflow MUST retrieve real Klaviyo data before generating any calendar output. As of the latest update, the system implements fail-fast validation that immediately halts the workflow if MCP returns empty or missing data.

**What Gets Validated:**
- **Segments** - Must have at least one segment for audience targeting
- **Historical Data** - Must have either campaigns or flows for performance analysis
- **Campaign Reports** - Must have performance data for ROI calculations

**Validation Error Example:**
```
❌ MCP Data Validation Failed for rogue-creamery (2025-01-01 to 2025-01-31)

Critical Issues:
  • No segments retrieved from Klaviyo - cannot generate audience-targeted campaigns
  • No historical campaigns or flows found - cannot base recommendations on past performance
  • No campaign performance data - cannot calculate ROI or optimize send times

Warnings:
  ⚠️  No flows found - this may be expected for newer accounts

🛑 WORKFLOW HALTED - Cannot generate calendar without real Klaviyo data
```

**When Validation Fails:**
- Workflow stops at Stage 1 (Planning)
- No calendar JSON is generated
- No output files are created
- Clear error message explains what data is missing

**When Validation Succeeds:**
```
✅ MCP data validation passed: 15 segments, 28 campaigns, 8 flows
```

**Note:** This validation prevents the generation of calendars based solely on industry benchmarks or generic recommendations. All calendars MUST be based on actual client performance data from Klaviyo.

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

### "MCP Data Validation Failed"
**Symptoms:** Workflow halts at Stage 1 with message about missing segments/campaigns/data

**Common Causes:**
1. **Empty Klaviyo Account** - Client account has no historical data
   - Check if client account is newly created
   - Verify account has sent campaigns in the specified date range

2. **Invalid Date Range** - No data exists for the specified period
   - Try a different date range with known campaign activity
   - Check Klaviyo dashboard for actual campaign send dates

3. **MCP Service Access Issues** - MCP server cannot access Klaviyo API
   - Verify API key has correct permissions
   - Check MCP server logs for API errors
   - Test MCP service directly: `curl http://localhost:3334/api/health`

4. **Client Name Mapping Issues** - Client slug doesn't match MCP account name
   - Verify client name mapping in `data/mcp_client.py:74-82`
   - Check that MCP account name is correct (e.g., "Rogue_Creamery_Klaviyo")

**Resolution:**
- If account truly has no data, validation is working correctly - calendar generation requires real historical data
- If data should exist, verify MCP service configuration and API access
- For testing purposes only, you can temporarily modify validation logic in `data/mcp_client.py`

### "Calendar validation failed"
- Check Stage 2 output for JSON formatting errors
- Verify prompt is generating valid v4.0.0 schema
- Use `--no-validate` to skip validation for testing

### "Workflow failed at Stage X"
- Check logs for specific error messages
- Run individual stage with `--stage X` for debugging
- Verify all data sources are accessible

## Production Deployment

### Google Cloud Run Service

The application is deployed and running at:
```
https://emailpilot-simple-935786836546.us-central1.run.app
```

**Features:**
- FastAPI-based REST API
- Interactive web UI for calendar generation
- Native MCP client architecture (child process model)
- Automatic Secret Manager integration for API keys
- 8 pre-configured Klaviyo client accounts

### Production Architecture

**Native MCP Client:**
- MCP servers spawn as child processes via `uvx klaviyo-mcp-server@latest`
- stdio-based JSON-RPC communication using MCP protocol
- API keys retrieved from Google Secret Manager at runtime
- Each client has dedicated MCP server instance

**Container Details:**
- Image: `us-central1-docker.pkg.dev/emailpilot-438321/emailpilot-simple/native-mcp-v3-amd64`
- Runtime: Python 3.11 + Node.js 20.x
- Security: Non-root user `emailpilot` (UID 1000)
- Scaling: Automatic via Cloud Run

### API Endpoints

**Web UI:**
```
GET / - Interactive calendar generation interface
```

**Health Check:**
```
GET /api/health - Service health and component status
```

**MCP Data (Raw Klaviyo Data):**
```
POST /api/mcp/data
Body: {
  "clientName": "rogue-creamery",
  "startDate": "2025-01-01",
  "endDate": "2025-01-31"
}
```

**Calendar Generation Workflow:**
```
POST /api/workflow/run
Body: {
  "client_name": "rogue-creamery",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31"
}
```

**Additional Endpoints:**
```
GET /api/jobs/{job_id} - Get job status and results
GET /api/prompts/{prompt_name} - Get prompt template
PUT /api/prompts/{prompt_name} - Update prompt template
POST /api/rag/data - Retrieve RAG (brand intelligence) data
GET /api/outputs/{output_type} - Get workflow outputs
GET /api/cache - Get cache statistics
DELETE /api/cache - Clear cache
```

### Testing Production

**Test via Web UI:**
1. Visit `https://emailpilot-simple-935786836546.us-central1.run.app`
2. Fill in client name, start date, end date
3. Click "Generate Calendar"
4. View results in the UI

**Test via curl:**
```bash
# Health check
curl https://emailpilot-simple-935786836546.us-central1.run.app/api/health

# Generate calendar
curl -X POST 'https://emailpilot-simple-935786836546.us-central1.run.app/api/generate' \
  -H 'Content-Type: application/json' \
  -d '{"clientName": "rogue-creamery", "startDate": "2025-01-01", "endDate": "2025-01-31"}'
```

### Available Clients

- Vlasic Labs
- Rogue Creamery
- Colorado Hemp Honey
- Wheelchair Getaways
- Milagro Mushrooms
- First Aid Supplies Online (FASO)
- Christopher Bean Coffee
- Consumer Law Attorneys

### Deployment Management

**Rebuild and Deploy:**
```bash
# Build for Cloud Run (AMD64 architecture)
docker build --platform linux/amd64 -t native-mcp-v3-amd64 .

# Tag for Artifact Registry
docker tag native-mcp-v3-amd64 us-central1-docker.pkg.dev/emailpilot-438321/emailpilot-simple/native-mcp-v3-amd64

# Push to registry
docker push us-central1-docker.pkg.dev/emailpilot-438321/emailpilot-simple/native-mcp-v3-amd64

# Deploy to Cloud Run
gcloud run deploy emailpilot-simple \
  --image us-central1-docker.pkg.dev/emailpilot-438321/emailpilot-simple/native-mcp-v3-amd64 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**View Logs:**
```bash
gcloud run services logs read emailpilot-simple --region us-central1 --limit 50
```

## License

Internal use only. Part of the Klaviyo Audit Automation project.

## Support

For issues or questions, contact the development team.
