# Production Deployment Checklist - EmailPilot Simple (Strategy Summary Feature)

**Feature:** Strategy Summary Integration for Calendar Generation
**Status:** Phase 4 Testing Complete - All 6 Tasks Passed ✅
**Deployment Target:** Google Cloud Run (us-central1)
**Date Prepared:** 2025-11-19

---

## Pre-Deployment Verification

### 1. Phase 4 Testing Status ✅
- [x] **Task 1:** Calendar generation with strategy summary (8 events, 6 insights)
- [x] **Task 2:** Backend API import successful
- [x] **Task 3:** Firestore storage verified (calendar_events + strategy_summaries)
- [x] **Task 4:** API endpoint tested (GET /api/calendar/strategy-summary/{client_id})
- [x] **Task 5:** Frontend integration verified (8/8 tests passed)
- [x] **Task 6:** Documentation complete (PHASE4_TEST_RESULTS.md)

**Reference:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/PHASE4_TEST_RESULTS.md`

### 2. Git Repository Status ✅
- [x] All Phase 4 changes committed (commit: c69e87a)
- [x] Repository synchronized with origin/master
- [x] No pending changes or uncommitted files
- [x] Schema evolution to v1.2.5 committed

**Verify with:**
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
git status
```

### 3. Code Quality ✅
- [x] Schema validation fixed (added "content" and "special" campaign types)
- [x] MCP catalog integration implemented
- [x] Native MCP client with retry logic
- [x] Calendar format validation in place
- [x] Error handling for 404 responses

---

## Google Cloud Prerequisites

### 1. Required GCP Services
Ensure these services are enabled in your Google Cloud Project:

```bash
# Enable required services
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable logging.googleapis.com
```

### 2. Secret Manager Configuration

#### ✅ ANTHROPIC_API_KEY (Configured in cloudbuild.yaml)
```bash
# Verify secret exists
gcloud secrets describe anthropic-api-key

# If not exists, create it:
gcloud secrets create anthropic-api-key \
  --data-file=- <<< "your-anthropic-api-key-here"

# Or update existing:
echo "your-anthropic-api-key-here" | gcloud secrets versions add anthropic-api-key --data-file=-
```

#### ⚠️ KLAVIYO_API_KEY (NOT CONFIGURED - ACTION REQUIRED)
**Issue:** KLAVIYO_API_KEY is listed as required in .env.example but missing from cloudbuild.yaml deployment configuration.

**Solution Option A - Add to Secret Manager (Recommended):**
```bash
# Create secret
gcloud secrets create klaviyo-api-key \
  --data-file=- <<< "your-klaviyo-api-key-here"

# Update cloudbuild.yaml line 52 to include:
# '--update-secrets'
# 'ANTHROPIC_API_KEY=anthropic-api-key:latest,KLAVIYO_API_KEY=klaviyo-api-key:latest'
```

**Solution Option B - Add as Environment Variable:**
```bash
# Update cloudbuild.yaml line 50 to include:
# '--set-env-vars'
# 'ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,KLAVIYO_API_KEY=your-key-here'
```

**Recommendation:** Use Option A (Secret Manager) for better security.

### 3. IAM Permissions
The Cloud Build service account needs these permissions:

```bash
# Get the Cloud Build service account
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Firestore Database
Ensure Firestore is initialized:

```bash
# Check if Firestore is enabled
gcloud firestore databases list

# If not initialized, create database in Native mode:
gcloud firestore databases create --region=us-central1
```

**Required Collections:**
- `calendar_events` - Stores individual campaign events
- `strategy_summaries` - Stores AI-generated strategy summaries

**Note:** Collections are auto-created on first write, no manual setup needed.

---

## Deployment Configuration Review

### 1. Environment Variables (cloudbuild.yaml)

**Currently Configured:**
```yaml
--set-env-vars
ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID
```

**Currently Configured Secrets:**
```yaml
--update-secrets
ANTHROPIC_API_KEY=anthropic-api-key:latest
```

### 2. Resource Configuration
```yaml
Service: emailpilot-simple
Region: us-central1
Port: 8000
Memory: 2Gi
CPU: 1
Min Instances: 0 (scales to zero)
Max Instances: 10
Timeout: 1200s (20 minutes)
Access: Public (--allow-unauthenticated)
Build Machine: N1_HIGHCPU_8
```

### 3. Python Dependencies (requirements.txt)
**Total:** 14 packages
**Python Version:** 3.10+

**Critical Dependencies:**
- `anthropic>=0.18.0` - Claude API client
- `fastapi>=0.104.0` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `google-cloud-firestore>=2.13.0` - Database
- `google-cloud-secret-manager>=2.16.0` - Secrets
- `google-cloud-storage>=2.10.0` - Persistent storage
- `google-cloud-logging>=3.8.0` - Production logging

**Full List:** See `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/requirements.txt`

### 4. Container Build (Dockerfile)
**Location:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/Dockerfile`
**Status:** ✅ Exists and referenced in cloudbuild.yaml

---

## Deployment Steps

### Step 1: Pre-Deployment Actions

#### 1.1 Address KLAVIYO_API_KEY Configuration
⚠️ **ACTION REQUIRED:** Choose and implement one of the solutions from section "Google Cloud Prerequisites > Secret Manager Configuration"

#### 1.2 Verify All Secrets Exist
```bash
# Check both secrets
gcloud secrets describe anthropic-api-key
gcloud secrets describe klaviyo-api-key  # After creating per 1.1
```

#### 1.3 Update cloudbuild.yaml (if using Secret Manager for KLAVIYO_API_KEY)
```yaml
# Edit line 52-53 in cloudbuild.yaml:
- '--update-secrets'
- 'ANTHROPIC_API_KEY=anthropic-api-key:latest,KLAVIYO_API_KEY=klaviyo-api-key:latest'
```

#### 1.4 Final Git Commit (if changes made)
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
git add cloudbuild.yaml PRODUCTION_DEPLOYMENT_CHECKLIST.md
git commit -m "Add KLAVIYO_API_KEY to production deployment configuration"
git push origin master
```

### Step 2: Trigger Cloud Build

#### Option A: Deploy from Local Machine
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple

# Submit build to Cloud Build
gcloud builds submit --config=cloudbuild.yaml
```

#### Option B: Deploy from GitHub (if connected)
```bash
# Trigger build from repository
gcloud builds triggers create github \
  --name="emailpilot-simple-deploy" \
  --repo-name="klaviyo-audit-automation" \
  --repo-owner="your-github-username" \
  --branch-pattern="^master$" \
  --build-config="emailpilot-simple/cloudbuild.yaml"
```

### Step 3: Monitor Deployment

#### 3.1 Watch Build Progress
```bash
# List recent builds
gcloud builds list --limit=5

# Get specific build details
BUILD_ID=<build-id-from-above>
gcloud builds describe $BUILD_ID

# Stream build logs
gcloud builds log $BUILD_ID --stream
```

#### 3.2 Verify Cloud Run Deployment
```bash
# Check service status
gcloud run services describe emailpilot-simple --region=us-central1

# Get service URL
gcloud run services describe emailpilot-simple \
  --region=us-central1 \
  --format="value(status.url)"
```

### Step 4: Post-Deployment Verification

#### 4.1 Health Check
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe emailpilot-simple \
  --region=us-central1 --format="value(status.url)")

# Test health endpoint (if exists)
curl -v "$SERVICE_URL/health"

# Test API endpoint
curl -v "$SERVICE_URL/api/calendar/strategy-summary/test-client-strategy"
```

#### 4.2 Check Logs
```bash
# View recent logs
gcloud run services logs read emailpilot-simple \
  --region=us-central1 \
  --limit=50

# Filter for errors
gcloud run services logs read emailpilot-simple \
  --region=us-central1 \
  --limit=100 \
  --filter="severity>=ERROR"
```

#### 4.3 Test Calendar Generation
```bash
# Test with actual client
curl -X POST "$SERVICE_URL/api/calendar/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "rogue-creamery",
    "start_date": "2026-01-02",
    "end_date": "2026-01-15"
  }'
```

#### 4.4 Verify Firestore Data
```bash
# Check calendar_events collection
gcloud firestore query \
  --collection=calendar_events \
  --filter="client_id==rogue-creamery" \
  --limit=10

# Check strategy_summaries collection
gcloud firestore query \
  --collection=strategy_summaries \
  --filter="client_id==rogue-creamery" \
  --limit=1
```

---

## Rollback Procedures

### If Deployment Fails

#### 1. Check Build Logs
```bash
# Get latest build
LATEST_BUILD=$(gcloud builds list --limit=1 --format="value(id)")

# View logs
gcloud builds log $LATEST_BUILD
```

#### 2. Rollback to Previous Revision
```bash
# List revisions
gcloud run revisions list --service=emailpilot-simple --region=us-central1

# Rollback to previous revision
PREVIOUS_REVISION=<revision-name>
gcloud run services update-traffic emailpilot-simple \
  --region=us-central1 \
  --to-revisions=$PREVIOUS_REVISION=100
```

#### 3. Common Issues and Solutions

**Issue: Secret Not Found**
```bash
# Verify secret exists and has data
gcloud secrets versions access latest --secret=anthropic-api-key
gcloud secrets versions access latest --secret=klaviyo-api-key
```

**Issue: Permission Denied**
```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:cloudbuild.gserviceaccount.com"
```

**Issue: Container Build Failed**
```bash
# Test Docker build locally
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
docker build -t emailpilot-simple:test .
docker run -p 8000:8000 emailpilot-simple:test
```

**Issue: Firestore Connection Failed**
```bash
# Verify Firestore is enabled
gcloud firestore databases list

# Check service account has Firestore access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

---

## Production Monitoring

### 1. Set Up Alerts

```bash
# Create alert for error rate
gcloud alpha monitoring policies create \
  --notification-channels=<your-channel-id> \
  --display-name="EmailPilot High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s

# Create alert for high latency
gcloud alpha monitoring policies create \
  --notification-channels=<your-channel-id> \
  --display-name="EmailPilot High Latency" \
  --condition-display-name="P95 latency > 5s" \
  --condition-threshold-value=5000 \
  --condition-threshold-duration=300s
```

### 2. Key Metrics to Monitor

**API Performance:**
- Strategy summary endpoint latency (target: <1s)
- Calendar generation latency (target: <30s)
- Error rate (target: <1%)

**Resource Usage:**
- Memory utilization (limit: 2GB)
- CPU utilization (limit: 1 CPU)
- Instance count (0-10 range)

**Data Quality:**
- Validation error rate
- Calendar events created per day
- Strategy summaries generated per day

**External Dependencies:**
- Anthropic API error rate
- Klaviyo MCP data fetch success rate
- Firestore read/write latency

### 3. Logging Configuration

**Log Levels in Production:**
- `ENVIRONMENT=production` enables structured logging
- DEBUG level logs enabled via google-cloud-logging
- Logs viewable in Cloud Console: Logging > Logs Explorer

**Useful Log Queries:**
```bash
# View all errors
resource.type="cloud_run_revision"
resource.labels.service_name="emailpilot-simple"
severity>=ERROR

# View calendar generation requests
resource.type="cloud_run_revision"
resource.labels.service_name="emailpilot-simple"
jsonPayload.event="calendar_generation_start"

# View validation errors
resource.type="cloud_run_revision"
resource.labels.service_name="emailpilot-simple"
jsonPayload.validation_errors!=""
```

---

## Testing in Production

### 1. Smoke Tests

After deployment, run these basic tests to verify core functionality:

```bash
SERVICE_URL=$(gcloud run services describe emailpilot-simple \
  --region=us-central1 --format="value(status.url)")

# Test 1: Strategy summary endpoint
echo "Test 1: Strategy Summary Endpoint"
curl -s "$SERVICE_URL/api/calendar/strategy-summary/test-client-strategy" | jq '.client_id'

# Test 2: 404 handling
echo "Test 2: 404 Handling"
curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/api/calendar/strategy-summary/non-existent-client"

# Test 3: Static files
echo "Test 3: Static Files"
curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/static/test-strategy-summary.html"
```

### 2. Integration Tests

Run the automated test suite against production:

```bash
# Update verify_frontend_integration.py with production URL
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
sed "s|http://localhost:8008|$SERVICE_URL|g" verify_frontend_integration.py > verify_production.py

# Run tests
python3 verify_production.py
```

### 3. Load Testing (Optional)

```bash
# Install Apache Bench
brew install httpd

# Test with 100 concurrent requests
ab -n 1000 -c 100 "$SERVICE_URL/api/calendar/strategy-summary/test-client-strategy"
```

---

## Success Criteria

Deployment is considered successful when:

### Functional Requirements ✅
- [ ] All smoke tests pass (3/3)
- [ ] Strategy summary endpoint returns 200 with valid JSON
- [ ] 404 handling works for non-existent clients
- [ ] Static files accessible
- [ ] Calendar generation produces valid strategy summaries
- [ ] Firestore persistence confirmed

### Performance Requirements ✅
- [ ] P50 latency < 1s for strategy summary endpoint
- [ ] P95 latency < 3s for strategy summary endpoint
- [ ] Error rate < 1%
- [ ] Service can handle 100 concurrent requests

### Monitoring Requirements ✅
- [ ] Logs appearing in Cloud Logging
- [ ] Metrics visible in Cloud Monitoring
- [ ] Alerts configured and tested
- [ ] No ERROR level logs after initial requests

### Security Requirements ✅
- [ ] API keys stored in Secret Manager (not environment variables)
- [ ] Public endpoints working (health, static files)
- [ ] Firestore access controlled via service account
- [ ] No credentials in logs

---

## Post-Deployment Actions

### 1. Documentation Updates
- [ ] Update README.md with production URL
- [ ] Document production API endpoints
- [ ] Create user guide for strategy summary feature
- [ ] Update architecture diagrams

### 2. Team Communication
- [ ] Notify stakeholders of successful deployment
- [ ] Share production URL with team
- [ ] Schedule demo of strategy summary feature
- [ ] Collect initial user feedback

### 3. Monitoring Setup
- [ ] Add production URL to status page
- [ ] Configure uptime monitoring
- [ ] Set up error notifications
- [ ] Create dashboard for key metrics

### 4. Backup and Disaster Recovery
- [ ] Document rollback procedures
- [ ] Set up automated Firestore backups
- [ ] Test disaster recovery process
- [ ] Create incident response playbook

---

## Known Issues and Limitations

### 1. MCP Configuration Security Issue (Hardcoded API Keys) 🚨 BLOCKING
**Status:** **CRITICAL - MUST BE RESOLVED BEFORE PRODUCTION DEPLOYMENT**
**Severity:** High - Security Vulnerability
**Discovered:** 2025-11-19 (Deployment Configuration Review)

**Issue Description:**
The `.mcp.json` configuration file contains 7 hardcoded Klaviyo `PRIVATE_API_KEY` values that are committed to the repository. This violates security best practices and exposes client API credentials in version control.

**File Location:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/.mcp.json`

**Affected Clients:**
1. Vlasic Klaviyo - `pk_419ce5f004d140f0d8f2ebd614bb0db654`
2. Rogue Creamery Klaviyo - `pk_41705a9abacbf2c7810c20129005c4b6b3`
3. Colorado Hemp Honey Klaviyo - `pk_0bbc2e242a19b2533115389ac7fcc266b5`
4. Wheelchair Getaways Klaviyo - `pk_7a8235b857e95c803455abce32abf44f69` (READ_ONLY: false)
5. Milagro Klaviyo - `pk_ba86433b068ccbb87e4b09de66a26559fc`
6. FASO Klaviyo - `pk_2206f367852b8f54c834d3030e69919468`
7. Chris Bean Klaviyo - `pk_0382b7440c7d660c40bb8a2621c561e4ec`

**Security Impact:**
- ❌ API keys exposed in Git history
- ❌ Keys visible to anyone with repository access
- ❌ Violates principle of least privilege
- ❌ Cannot rotate keys without code changes
- ❌ Risk of unauthorized access to client Klaviyo accounts

**Current Dockerfile Handling:**
The Dockerfile (lines 37-43) copies `.mcp.json` to `/home/emailpilot/.mcp.json` and translates paths:
```dockerfile
COPY .mcp.json /home/emailpilot/.mcp.json.tmp
RUN sed 's|/opt/anaconda3/bin/uvx|/usr/local/bin/uvx|g; s|/opt/anaconda3/bin/python3|/usr/local/bin/python3|g' \
    /home/emailpilot/.mcp.json.tmp > /home/emailpilot/.mcp.json && \
    rm /home/emailpilot/.mcp.json.tmp && \
    chown emailpilot:emailpilot /home/emailpilot/.mcp.json
```

**Recommended Solution: Dynamic .mcp.json Generation from Secret Manager**

**Step 1: Create Secrets in Google Secret Manager**
```bash
# Create individual secrets for each client
gcloud secrets create klaviyo-mcp-vlasic --data-file=- <<< "pk_419ce5f004d140f0d8f2ebd614bb0db654"
gcloud secrets create klaviyo-mcp-rogue-creamery --data-file=- <<< "pk_41705a9abacbf2c7810c20129005c4b6b3"
gcloud secrets create klaviyo-mcp-colorado-hemp-honey --data-file=- <<< "pk_0bbc2e242a19b2533115389ac7fcc266b5"
gcloud secrets create klaviyo-mcp-wheelchair-getaways --data-file=- <<< "pk_7a8235b857e95c803455abce32abf44f69"
gcloud secrets create klaviyo-mcp-milagro --data-file=- <<< "pk_ba86433b068ccbb87e4b09de66a26559fc"
gcloud secrets create klaviyo-mcp-faso --data-file=- <<< "pk_2206f367852b8f54c834d3030e69919468"
gcloud secrets create klaviyo-mcp-chris-bean --data-file=- <<< "pk_0382b7440c7d660c40bb8a2621c561e4ec"
```

**Step 2: Grant Secret Access to Cloud Run Service Account**
```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to all MCP secrets
for SECRET in klaviyo-mcp-vlasic klaviyo-mcp-rogue-creamery klaviyo-mcp-colorado-hemp-honey \
               klaviyo-mcp-wheelchair-getaways klaviyo-mcp-milagro klaviyo-mcp-faso klaviyo-mcp-chris-bean
do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

**Step 3: Create Startup Script to Generate .mcp.json Dynamically**
Create `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple/scripts/generate_mcp_config.py`:

```python
#!/usr/bin/env python3
"""
Generate .mcp.json dynamically from Google Secret Manager at container startup.
This ensures API keys are never committed to the repository.
"""
import json
import os
from pathlib import Path
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    """Fetch secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

def generate_mcp_config():
    """Generate .mcp.json from Secret Manager secrets."""

    # Fetch all API keys from Secret Manager
    secrets = {
        'vlasic': get_secret('klaviyo-mcp-vlasic'),
        'rogue-creamery': get_secret('klaviyo-mcp-rogue-creamery'),
        'colorado-hemp-honey': get_secret('klaviyo-mcp-colorado-hemp-honey'),
        'wheelchair-getaways': get_secret('klaviyo-mcp-wheelchair-getaways'),
        'milagro': get_secret('klaviyo-mcp-milagro'),
        'faso': get_secret('klaviyo-mcp-faso'),
        'chris-bean': get_secret('klaviyo-mcp-chris-bean'),
    }

    # Build configuration
    config = {
        "mcpServers": {
            "Vlasic Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['vlasic'],
                    "READ_ONLY": "true"
                }
            },
            "Rogue Creamery Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['rogue-creamery'],
                    "READ_ONLY": "true"
                }
            },
            "Colorado Hemp Honey Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['colorado-hemp-honey'],
                    "READ_ONLY": "true"
                }
            },
            "Wheelchair Getaways Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['wheelchair-getaways'],
                    "READ_ONLY": "false"
                }
            },
            "Milagro Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['milagro'],
                    "READ_ONLY": "true"
                }
            },
            "FASO Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['faso'],
                    "READ_ONLY": "true"
                }
            },
            "Chris Bean Klaviyo": {
                "command": "/usr/local/bin/uvx",
                "args": ["klaviyo-mcp-server@latest"],
                "env": {
                    "PRIVATE_API_KEY": secrets['chris-bean'],
                    "READ_ONLY": "true"
                }
            },
            "Wise": {
                "command": "/usr/local/bin/python3",
                "args": ["-m", "wise_mcp.main"]
            }
        }
    }

    # Write to correct location for emailpilot user
    output_path = Path.home() / ".mcp.json"
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✓ Generated .mcp.json at {output_path}")

if __name__ == "__main__":
    generate_mcp_config()
```

**Step 4: Update Dockerfile to Generate Config at Startup**
Replace lines 37-43 in Dockerfile with:
```dockerfile
# Copy MCP configuration generation script
COPY scripts/generate_mcp_config.py /app/scripts/
RUN chown emailpilot:emailpilot /app/scripts/generate_mcp_config.py

# Switch to non-root user
USER emailpilot

# Generate .mcp.json from Secret Manager at container startup
# This happens before CMD runs api.py
ENTRYPOINT ["sh", "-c", "python3 /app/scripts/generate_mcp_config.py && exec python api.py"]
```

**Step 5: Remove .mcp.json from Repository**
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple

# Add to .gitignore
echo ".mcp.json" >> .gitignore

# Remove from git (but keep local copy for development)
git rm --cached .mcp.json

# Commit the security fix
git add .gitignore Dockerfile scripts/generate_mcp_config.py
git commit -m "Security: Move MCP API keys to Secret Manager

- Remove hardcoded API keys from .mcp.json
- Generate configuration dynamically from Secret Manager at startup
- Add .mcp.json to .gitignore
- Update Dockerfile to run generation script before api.py

SECURITY FIX: Resolves hardcoded API key exposure in version control"
```

**Alternative Approach: Environment Variable Substitution**
If dynamic generation is too complex, use environment variable substitution:

1. Create `.mcp.json.template` with placeholders:
```json
{
  "mcpServers": {
    "Vlasic Klaviyo": {
      "command": "/usr/local/bin/uvx",
      "args": ["klaviyo-mcp-server@latest"],
      "env": {
        "PRIVATE_API_KEY": "${KLAVIYO_MCP_VLASIC}",
        "READ_ONLY": "true"
      }
    }
    // ... etc
  }
}
```

2. Use `envsubst` to substitute values at startup
3. Pass secrets as environment variables via cloudbuild.yaml

**Verification After Fix:**
```bash
# Verify secrets exist
gcloud secrets list --filter="name:klaviyo-mcp-"

# Test in development
python3 scripts/generate_mcp_config.py
cat ~/.mcp.json  # Should contain populated API keys

# Verify .mcp.json not in git
git status  # Should not show .mcp.json
git log --all --full-history -- .mcp.json  # Shows removal commit
```

**Timeline:**
- **Blocking:** Cannot deploy to production until resolved
- **Estimated Implementation:** 2-4 hours
- **Priority:** CRITICAL - Address before any deployment

### 2. KLAVIYO_API_KEY Configuration ⚠️
**Status:** Missing from cloudbuild.yaml
**Impact:** MCP catalog fetch may fail if KLAVIYO_API_KEY not available
**Resolution:** Add to Secret Manager and update cloudbuild.yaml (see Pre-Deployment Actions)

### 2. Campaign Type Validation
**Status:** Resolved in v1.2.5
**History:** Previous schema version rejected "content" type campaigns
**Current:** Now supports all business campaign types including "content" and "special"

### 3. MCP Catalog Limitations
**Status:** Known behavior
**Issue:** Catalog may be empty for new clients without historical data
**Workaround:** System generates calendar based on industry benchmarks when catalog unavailable
**Reference:** key_insights includes "CRITICAL DATA LIMITATION" warning when applicable

### 4. Cold Start Latency
**Status:** Expected behavior with min-instances=0
**Impact:** First request after idle period may take 5-10 seconds
**Mitigation:** Consider setting min-instances=1 for production if cold starts are problematic

---

## Contacts and Support

### Development Team
- **Primary Contact:** [Your Name/Team]
- **Repository:** `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple`
- **Documentation:** `PHASE4_TEST_RESULTS.md`, `PRODUCTION_DEPLOYMENT_CHECKLIST.md`

### GCP Resources
- **Project:** Check with `gcloud config get-value project`
- **Region:** us-central1
- **Service:** emailpilot-simple
- **Cloud Console:** https://console.cloud.google.com/run

### External Dependencies
- **Anthropic (Claude):** https://console.anthropic.com/
- **Klaviyo API:** https://www.klaviyo.com/settings/account/api-keys
- **Firestore:** https://console.cloud.google.com/firestore

---

## Appendix

### A. File Locations

**Configuration Files:**
- `.env.example` - Environment variable template
- `cloudbuild.yaml` - CI/CD deployment configuration
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build instructions

**Test Files:**
- `verify_frontend_integration.py` - Frontend integration test suite
- `verify_firestore_storage.py` - Database verification script
- `PHASE4_TEST_RESULTS.md` - Complete test documentation

**Application Files:**
- `api.py` - Main FastAPI application
- `agents/calendar_agent.py` - Calendar generation logic
- `tools/calendar_tool.py` - Calendar workflow tools
- `data/native_mcp_client.py` - MCP data client
- `prompts/calendar_structuring_v1_2_2.yaml` - AI prompt configuration

### B. API Endpoints

**Strategy Summary:**
- `GET /api/calendar/strategy-summary/{client_id}` - Fetch strategy summary

**Static Files:**
- `/static/test-strategy-summary.html` - Integration test page
- `/static/js/strategy-summary-api.js` - API client
- `/static/js/strategy-summary-component.js` - UI component
- `/static/js/strategy-summary-types.js` - Type definitions
- `/static/css/strategy-summary.css` - Styling

### C. Useful Commands Reference

```bash
# Quick deployment
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
gcloud builds submit --config=cloudbuild.yaml

# Get service URL
gcloud run services describe emailpilot-simple --region=us-central1 --format="value(status.url)"

# View logs
gcloud run services logs read emailpilot-simple --region=us-central1 --limit=50

# Check service health
curl $(gcloud run services describe emailpilot-simple --region=us-central1 --format="value(status.url)")/health

# Rollback to previous version
gcloud run services update-traffic emailpilot-simple --region=us-central1 --to-revisions=PREVIOUS_REVISION=100
```

---

**Checklist Version:** 1.0
**Last Updated:** 2025-11-19
**Next Review:** After first production deployment
