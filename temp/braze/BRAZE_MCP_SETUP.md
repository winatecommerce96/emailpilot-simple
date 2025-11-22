# Braze MCP Server Setup Guide

## Package Information

**Package:** `braze-mcp-server`
**Current Version:** 1.0.4
**Python Requirement:** >=3.12

### Installation
```bash
pip install braze-mcp-server
```

---

## API Credentials

### Required Environment Variables

| Variable | Value |
|----------|-------|
| `BRAZE_API_KEY` | `3e644a50-e0ba-4d63-a6ab-a5a38653b77f` |
| `BRAZE_BASE_URL` | `https://rest.iad-05.braze.com` |

### Additional Project Credentials

| Service | Key | Value |
|---------|-----|-------|
| Braze | `BRAZE_APP_ID` | `ab94e59e-a93a-4f2a-8409-a87b838efb7c` |
| Claude | `CLAUDE_API_KEY` | `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` |
| Slack | `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/services/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` |

---

## MCP Client Configuration

### Claude Desktop
Add to Settings > Developer > Edit Config:
```json
{
  "mcpServers": {
    "braze": {
      "command": "uvx",
      "args": ["--native-tls", "braze-mcp-server@latest"],
      "env": {
        "BRAZE_API_KEY": "3e644a50-e0ba-4d63-a6ab-a5a38653b77f",
        "BRAZE_BASE_URL": "https://rest.iad-05.braze.com"
      }
    }
  }
}
```

### Cursor
Add via Settings > Tools and Integrations > MCP Tools (same config as above).

---

## Available MCP Tools (38 Read-Only Endpoints)

### Core Functions
- `list_functions` — List all available Braze API functions with descriptions
- `call_function` — Execute a specific Braze API function with parameters

### Campaigns & Canvases
- List campaigns and campaign details
- Campaign analytics data
- Export Canvas information
- Canvas performance metrics

### Segments
- List all segments
- Segment analytics
- Detailed segment information

### Custom Data
- Export custom attributes
- Export custom events
- Event analytics with time series

### Purchases & Revenue
- Product lists
- Revenue trends (`/purchases/revenue_series`)
- Quantity trends

### KPIs
- New users (time series)
- Daily active users (DAU)
- Monthly active users (MAU)
- App uninstalls

### Sessions & Sends
- App session counts
- Campaign send analytics

### Catalogs
- List catalogs
- Retrieve catalog items (with pagination)
- Catalog item details

### Templates & Content
- Content blocks
- Email templates
- Preference center information

### Other
- Cloud Data Ingestion (CDI) integrations
- Subscription group status
- SDK Authentication keys

---

## Braze vs Klaviyo Data Structure Differences

| Aspect | Braze | Klaviyo |
|--------|-------|---------|
| **User Identifier** | `external_id` or `braze_id` | `email` or `$id` |
| **Events** | Custom events with properties | Metrics with properties |
| **Segments** | Filter-based, real-time evaluation | List-based + segments |
| **Automation** | Campaigns + Canvases (flows) | Campaigns + Flows |
| **Revenue Tracking** | `purchases` array with products | `Placed Order` metric |
| **Attribution** | Limited via API (no per-campaign revenue) | Full revenue attribution per campaign |
| **User Profiles** | Custom attributes on user object | Custom properties on profile |
| **Data Export** | Currents, BI Connector, Dashboard | Data Warehouse sync, API |

---

## Conversion Tracking in Braze

### How Conversions Work
1. Conversions are defined at the **campaign or canvas level**
2. Set a primary conversion event (e.g., "Purchase", "App Open", custom event)
3. Define conversion deadline (1-30 days from message receipt)
4. Braze tracks users who complete the event within the window

### API Limitations

**What WORKS:**
- Total revenue via `/purchases/revenue_series`
- Filter by product (e.g., `"eComm Order"`)
- Split requests into 90-day chunks to stay under API limits

**What DOESN'T WORK:**
- `/campaigns/revenue_series` — Returns 404 (endpoint not supported)
- Per-campaign revenue attribution — Not available via REST API
- Per-campaign engagement metrics — Often returns zero for historical data

### Recommended Alternatives for Campaign Attribution
1. **Braze Dashboard Exports** — CSV exports with full attribution
2. **Currents** — Real-time data streaming to your warehouse
3. **BI Connector** — Direct integration with BI tools
4. **Custom UTM Tracking** — Link-level attribution via Google Analytics

---

## Troubleshooting

### Common Issues

1. **API 404 Errors**
   - Verify `BRAZE_APP_ID` is correct
   - Check API key has required permissions

2. **No Data Returned**
   - Confirm date ranges are valid
   - Check if campaigns were actually sent (not just scheduled)
   - Try Canvas endpoints if using flows

3. **Rate Limits**
   - Braze has rate limits per endpoint
   - Split large date ranges into chunks (max 90 days)

4. **MCP Connection Issues**
   - Ensure Python >=3.12
   - Install `uv` package manager
   - Verify environment variables are set

---

## Resources

- [Braze MCP Server Documentation](https://www.braze.com/docs/user_guide/brazeai/mcp_server)
- [Available API Functions](https://www.braze.com/docs/user_guide/brazeai/mcp_server/available_api_functions)
- [braze-mcp-server on PyPI](https://pypi.org/project/braze-mcp-server/)
- [Braze REST API Documentation](https://www.braze.com/docs/api)

---

## Security Note

These credentials should be stored as environment variables or GitHub Secrets in production. Rotate API keys periodically and use read-only permissions for MCP access.
