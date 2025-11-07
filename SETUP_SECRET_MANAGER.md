# Google Cloud Secret Manager Setup Guide

This guide covers how to set up and test Google Cloud Secret Manager integration for per-client Klaviyo API keys in EmailPilot Simple.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Creating Secrets in Google Cloud](#creating-secrets-in-google-cloud)
- [IAM Permissions](#iam-permissions)
- [Running the Test Suite](#running-the-test-suite)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before setting up Secret Manager integration, ensure you have:

1. **Python 3.10+** installed
2. **Google Cloud account** with a project created
3. **gcloud CLI** installed and configured
4. **Secret Manager API** enabled in your Google Cloud project
5. **Klaviyo API keys** for each client you want to configure

### Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com
```

---

## Environment Setup

### Required Environment Variables

Set the following environment variables in your shell or `.env` file:

```bash
# Google Cloud project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Anthropic API key for Claude
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### Google Cloud Authentication

Authenticate with Google Cloud using Application Default Credentials:

```bash
gcloud auth application-default login
```

This command will open a browser window for authentication and store credentials locally for use by the Python client libraries.

---

## Creating Secrets in Google Cloud

### Secret Naming Convention

Secrets must follow this naming pattern:

```
klaviyo-api-{client-slug}
```

### Special Client Mappings

Some clients have special mappings where the secret name differs from the client slug:

| Client Slug | Secret Name |
|------------|-------------|
| `rogue-creamery` | `klaviyo-api-rogue-creamery` |
| `vlasic` | `klaviyo-api-vlasic-labs` |
| `milagro` | `klaviyo-api-milagro-mushrooms` |
| `chris-bean` | `klaviyo-api-christopher-bean-coffee` |
| `colorado-hemp-honey` | `klaviyo-api-colorado-hemp-honey` |
| `wheelchair-getaways` | `klaviyo-api-wheelchair-getaways` |
| `faso` | `klaviyo-api-faso` |

### Creating Secrets via gcloud CLI

For each client, create a secret and add the Klaviyo API key:

```bash
# Example: Create secret for rogue-creamery
echo -n "pk_your_klaviyo_api_key_here" | \
  gcloud secrets create klaviyo-api-rogue-creamery \
    --data-file=- \
    --replication-policy="automatic"

# Example: Create secret for vlasic (note the special mapping)
echo -n "pk_your_klaviyo_api_key_here" | \
  gcloud secrets create klaviyo-api-vlasic-labs \
    --data-file=- \
    --replication-policy="automatic"
```

### Creating Secrets via Google Cloud Console

1. Navigate to **Security > Secret Manager** in Google Cloud Console
2. Click **Create Secret**
3. Enter the secret name (e.g., `klaviyo-api-rogue-creamery`)
4. Paste the Klaviyo API key in the **Secret value** field
5. Click **Create Secret**

### Updating Existing Secrets

To add a new version of a secret:

```bash
echo -n "pk_new_api_key_here" | \
  gcloud secrets versions add klaviyo-api-rogue-creamery \
    --data-file=-
```

---

## IAM Permissions

### Required Role

The service account or user running the application needs the following IAM role:

```
roles/secretmanager.secretAccessor
```

### Grant Permissions to Service Account

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Grant Permissions to User (for local development)

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Running the Test Suite

### Test Script Overview

The test suite (`test_secret_manager.py`) validates:

1. **Environment Variables** - Checks that `GOOGLE_CLOUD_PROJECT` and `ANTHROPIC_API_KEY` are set
2. **SecretManagerClient Instantiation** - Verifies the client can be created
3. **Secret Name Mapping** - Tests conversion of client slugs to secret names
4. **API Key Fetch** - Retrieves an actual API key from Secret Manager
5. **MCPClient Integration** - Tests end-to-end integration with MCP service
6. **Error Handling** - Validates proper error handling for missing secrets

### Basic Usage

Run tests with the default client (rogue-creamery):

```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-simple
python test_secret_manager.py
```

### Test Specific Client

```bash
python test_secret_manager.py --client vlasic
python test_secret_manager.py --client milagro
python test_secret_manager.py --client chris-bean
```

### Expected Output

**Successful Test Run:**

```
================================================================================
SECRET MANAGER INTEGRATION TEST SUITE
================================================================================

================================================================================
Test 1: Environment Variables
================================================================================
✅ GOOGLE_CLOUD_PROJECT: your-project-id
✅ ANTHROPIC_API_KEY: sk-ant-your-key...

✅ All environment variables are set

================================================================================
Test 2: SecretManagerClient Instantiation
================================================================================
✅ SecretManagerClient instantiated successfully
   Project ID: your-project-id

================================================================================
Test 3: Secret Name Mapping
================================================================================
✅ rogue-creamery → klaviyo-api-rogue-creamery
✅ vlasic → klaviyo-api-vlasic-labs
✅ milagro → klaviyo-api-milagro-mushrooms
✅ chris-bean → klaviyo-api-christopher-bean-coffee
✅ colorado-hemp-honey → klaviyo-api-colorado-hemp-honey
✅ wheelchair-getaways → klaviyo-api-wheelchair-getaways
✅ faso → klaviyo-api-faso

✅ All secret name mappings are correct

================================================================================
Test 4: Fetch API Key for rogue-creamery
================================================================================
✅ Successfully fetched API key: pk_1234567...890abcdef
   Length: 73 characters
   Format: Valid Klaviyo private key (starts with 'pk_')

================================================================================
Test 5: MCPClient Integration
================================================================================
✅ SecretManagerClient initialized for MCP test
✅ MCPClient initialized with SecretManagerClient
✅ MCPClient context manager opened
   Attempting to fetch segments for rogue-creamery...
✅ Successfully fetched 15 segments
   First segment: VIP Customers

================================================================================
Test 6: Error Handling for Missing Secrets
================================================================================
✅ Correctly raised exception for missing secret
   Exception type: NotFound
   Message: Secret [projects/your-project/secrets/klaviyo-api-nonexistent-client-12345] not found

================================================================================
TEST SUMMARY
================================================================================
✅ PASS: environment
✅ PASS: instantiation
✅ PASS: mapping
✅ PASS: api_key_fetch
✅ PASS: mcp_integration
✅ PASS: error_handling

================================================================================
Results: 6/6 tests passed
================================================================================
```

### Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

---

## Troubleshooting

### Issue: Environment Variables Not Set

**Error:**
```
❌ GOOGLE_CLOUD_PROJECT: NOT SET
❌ Cannot continue tests without environment variables
```

**Solution:**
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Issue: Secret Not Found

**Error:**
```
❌ Failed to fetch API key: Secret [projects/.../secrets/klaviyo-api-vlasic] not found
```

**Solution:**
1. Verify the secret exists in Google Cloud Console
2. Check that you're using the correct secret name (note special mappings for vlasic, milagro, chris-bean)
3. Create the secret if it doesn't exist:
   ```bash
   echo -n "pk_your_api_key" | gcloud secrets create klaviyo-api-vlasic-labs --data-file=-
   ```

### Issue: Permission Denied

**Error:**
```
❌ Failed to fetch API key: Permission denied
```

**Solution:**
Grant Secret Manager Secret Accessor role:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: MCP Service Not Running

**Error:**
```
❌ MCPClient integration test failed: Connection refused
   This could indicate:
   - MCP service is not running on localhost:3334
```

**Solution:**
1. Start the MCP service on port 3334
2. Verify it's running:
   ```bash
   curl http://localhost:3334/health
   ```
3. Check for port conflicts:
   ```bash
   lsof -i :3334
   ```

### Issue: Invalid API Key Format

**Error:**
```
⚠️  Format: Unexpected format (doesn't start with 'pk_')
```

**Solution:**
1. Verify the Klaviyo API key is a **private key** (not a public key)
2. Private keys start with `pk_`
3. Update the secret with the correct API key format

### Issue: Google Cloud Authentication Failed

**Error:**
```
❌ Failed to instantiate SecretManagerClient: DefaultCredentialsError
```

**Solution:**
Authenticate with Google Cloud:
```bash
gcloud auth application-default login
```

---

## Klaviyo API Key Format

Valid Klaviyo private keys follow this format:
- Start with `pk_`
- Typically 73 characters long
- Example: `pk_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12345`

To find your Klaviyo API keys:
1. Log in to Klaviyo
2. Navigate to **Settings > API Keys**
3. Use a **Private API Key** (not a Public API Key)

---

## Additional Resources

- [Google Cloud Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Klaviyo API Documentation](https://developers.klaviyo.com/en/docs)
- [Python Client Library for Secret Manager](https://googleapis.dev/python/secretmanager/latest/)

---

## Next Steps

After successfully running the test suite:

1. **Configure all 7 clients** with their respective Klaviyo API keys
2. **Run the full workflow** using `main.py`:
   ```bash
   python main.py --client rogue-creamery --start-date 2025-01-01 --end-date 2025-01-31
   ```
3. **Monitor logs** for any Secret Manager related issues during production runs
4. **Set up secret rotation** for enhanced security (optional but recommended)

---

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment-specific secrets** for dev/staging/production
3. **Enable secret version management** for rollback capability
4. **Set up audit logging** to track secret access
5. **Implement secret rotation** on a regular schedule (e.g., every 90 days)
6. **Use service accounts** with minimal required permissions in production
