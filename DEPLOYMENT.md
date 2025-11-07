# EmailPilot Simple - Google Cloud Deployment Guide

This guide provides step-by-step instructions for deploying EmailPilot Simple to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured ([Install Guide](https://cloud.google.com/sdk/docs/install))
3. **Git** installed
4. **Anthropic API Key** for Claude AI integration

## Initial Setup

### 1. Set Your Project ID

```bash
# Replace with your actual GCP project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable Cloud Run, Cloud Build, Container Registry, Firestore, and Secret Manager
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Create Anthropic API Key Secret

```bash
# Store your Anthropic API key securely in Secret Manager
echo -n "your-anthropic-api-key-here" | \
  gcloud secrets create anthropic-api-key \
  --data-file=-

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Initialize Firestore Database

```bash
# Create Firestore database in native mode
gcloud firestore databases create --location=us-central1
```

## Deployment Methods

### Method 1: Automated Deployment with Cloud Build (Recommended)

This method uses the included `cloudbuild.yaml` for automated builds.

```bash
# Submit build from local directory
gcloud builds submit --config=cloudbuild.yaml

# Or trigger from GitHub repository (if connected)
gcloud builds submit --config=cloudbuild.yaml \
  https://github.com/winatecommerce96/emailpilot-simple
```

The Cloud Build process will:
1. Build the Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run with production settings

### Method 2: Manual Deployment

If you prefer manual control over each step:

```bash
# 1. Build the Docker image locally
docker build -t gcr.io/$PROJECT_ID/emailpilot-simple:latest .

# 2. Push to Container Registry
docker push gcr.io/$PROJECT_ID/emailpilot-simple:latest

# 3. Deploy to Cloud Run
gcloud run deploy emailpilot-simple \
  --image gcr.io/$PROJECT_ID/emailpilot-simple:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --update-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest
```

## Configuration

### Environment Variables

The following environment variables are automatically configured:

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Sets production mode (disables auto-reload) |
| `GOOGLE_CLOUD_PROJECT` | Your project ID | Required for Firestore/Secret Manager |
| `ANTHROPIC_API_KEY` | From Secret Manager | Claude API authentication |
| `RAG_BASE_PATH` | `./rag` (default) | Path to RAG documents directory |
| `PORT` | Set by Cloud Run | HTTP server port |

### Optional: Custom RAG Path

If you want to use a custom RAG documents path:

```bash
gcloud run services update emailpilot-simple \
  --region us-central1 \
  --update-env-vars RAG_BASE_PATH=/custom/path
```

## Verification

### 1. Get Service URL

```bash
# Get the deployed service URL
gcloud run services describe emailpilot-simple \
  --region us-central1 \
  --format 'value(status.url)'
```

### 2. Test Health Endpoint

```bash
# Replace SERVICE_URL with the URL from previous command
curl https://SERVICE_URL/api/health

# Expected response:
# {
#   "success": true,
#   "timestamp": "2025-11-07T21:56:32.947578",
#   "data": {
#     "status": "healthy",
#     "initialized": true,
#     "components": {
#       "calendar_agent": true,
#       "calendar_tool": true,
#       "mcp_client": true,
#       "rag_client": true,
#       "cache": true
#     }
#   }
# }
```

### 3. Test API Endpoints

```bash
# Test calendar generation
curl -X POST https://SERVICE_URL/generate-calendar \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "test-client",
    "month": "2025-01",
    "campaign_count": 8
  }'
```

## Monitoring and Logs

### View Logs

```bash
# Stream logs in real-time
gcloud run services logs tail emailpilot-simple --region us-central1

# View recent logs
gcloud run services logs read emailpilot-simple --region us-central1 --limit 100
```

### View Metrics

```bash
# Open Cloud Console metrics dashboard
gcloud run services describe emailpilot-simple \
  --region us-central1 \
  --format 'value(status.url)' | \
  xargs -I {} echo "Metrics: https://console.cloud.google.com/run/detail/us-central1/emailpilot-simple/metrics"
```

## Updating the Service

### Deploy New Version

```bash
# Option 1: Using Cloud Build (recommended)
gcloud builds submit --config=cloudbuild.yaml

# Option 2: Manual update
gcloud run deploy emailpilot-simple \
  --image gcr.io/$PROJECT_ID/emailpilot-simple:latest \
  --region us-central1
```

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service emailpilot-simple --region us-central1

# Rollback to specific revision
gcloud run services update-traffic emailpilot-simple \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

## Troubleshooting

### Issue: Firestore Permission Denied

```bash
# Grant Firestore access to default service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Issue: Secret Manager Access Denied

```bash
# Grant Secret Manager access
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: Container Build Fails

```bash
# Check build logs
gcloud builds list --limit 5

# View specific build
gcloud builds log BUILD_ID
```

### Issue: Service Won't Start

```bash
# Check service logs for errors
gcloud run services logs read emailpilot-simple \
  --region us-central1 \
  --limit 50

# Check service status
gcloud run services describe emailpilot-simple \
  --region us-central1
```

## Cost Optimization

### Configure Autoscaling

```bash
# Set minimum instances (0 = scale to zero when idle)
gcloud run services update emailpilot-simple \
  --region us-central1 \
  --min-instances 0

# Set maximum instances
gcloud run services update emailpilot-simple \
  --region us-central1 \
  --max-instances 10
```

### Reduce Memory/CPU for Lower Traffic

```bash
# Use smaller instance size if traffic is low
gcloud run services update emailpilot-simple \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1
```

## Security Best Practices

1. **Never commit secrets** - Use Secret Manager for sensitive data
2. **Use least privilege** - Grant minimal required IAM permissions
3. **Enable authentication** - Remove `--allow-unauthenticated` for production
4. **Monitor logs** - Set up log-based metrics and alerts
5. **Use VPC** - Configure VPC connector for private resources

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit --config=cloudbuild.yaml
```

## Support

For issues or questions:
- Check logs: `gcloud run services logs tail emailpilot-simple --region us-central1`
- Review Cloud Console: https://console.cloud.google.com/run
- Check service health: `curl https://SERVICE_URL/api/health`

## API Endpoints

Once deployed, the following endpoints are available:

### Core Endpoints
- `GET /` - Serves the HTML user interface
- `GET /api/health` - Health check endpoint with component status

### Workflow Endpoints
- `POST /api/workflow/run` - Execute calendar generation workflow
- `GET /api/jobs/{job_id}` - Get job status and results

### Data Access Endpoints
- `POST /api/rag/data` - Retrieve RAG (brand intelligence) data
- `POST /api/mcp/data` - Retrieve MCP (Klaviyo) data
- `GET /api/outputs/{output_type}` - Get workflow outputs (planning, calendar, briefs)

### Configuration Endpoints
- `GET /api/prompts/{prompt_name}` - Get prompt template
- `PUT /api/prompts/{prompt_name}` - Update prompt template

### Cache Management
- `GET /api/cache` - Get cache statistics
- `DELETE /api/cache` - Clear cache

Full API documentation available at: `https://SERVICE_URL/` (interactive UI)
