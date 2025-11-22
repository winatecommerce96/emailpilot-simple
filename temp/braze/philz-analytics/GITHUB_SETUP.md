# GitHub Setup Guide for Philz Analytics

## Step-by-Step GitHub Actions Setup

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `philz-analytics`
3. Make it Private (recommended for business data)
4. Don't initialize with README (we have one)
5. Click "Create repository"

### 2. Push Code to GitHub

```bash
# In your local directory
cd /Users/Damon/klaviyo/klaviyo-audit-automation

# Add remote repository
git remote add origin https://github.com/winatecommerce96/philz-analytics.git

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Philz Analytics automation with GitHub Actions"

# Push to GitHub
git push -u origin main
```

### 3. Configure GitHub Secrets

#### Navigate to Secrets Page
1. Go to your repository: https://github.com/winatecommerce96/philz-analytics
2. Click **Settings** tab
3. In left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** for each secret below

#### Required Secrets

##### BRAZE_API_KEY
```
Name: BRAZE_API_KEY
Value: 3e644a50-e0ba-4d63-a6ab-a5a38653b77f
```

##### BRAZE_APP_ID
```
Name: BRAZE_APP_ID
Value: ab94e59e-a93a-4f2a-8409-a87b838efb7c
```

##### BRAZE_BASE_URL
```
Name: BRAZE_BASE_URL
Value: https://rest.iad-05.braze.com
```

##### CLAUDE_API_KEY
```
Name: CLAUDE_API_KEY
Value: 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
```

##### SLACK_WEBHOOK_URL
```
Name: SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/services/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
```

### 4. Test the Workflows

#### Manual Test
1. Go to **Actions** tab in your repository
2. Click **Manual Analytics Report** workflow
3. Click **Run workflow** button
4. Select branch: `main`
5. Keep default options or customize
6. Click **Run workflow** (green button)
7. Watch the progress - should take ~1 minute

#### Verify Scheduled Workflow
1. Go to **Actions** tab
2. Click **Weekly Philz Analytics Report**
3. Verify it shows "This workflow has a schedule trigger"
4. Next run: Monday 9:00 AM UTC

### 5. Monitor Workflow Runs

#### View Results
- Each run creates an artifact with the JSON results
- Download from the workflow run page
- Artifacts retained for 30 days (weekly) or 7 days (manual)

#### Check Slack
- Verify the message appears in your Slack channel
- Ensure formatting looks correct
- Check all metrics are displayed

#### Troubleshooting Failed Runs
1. Click on the failed workflow run
2. Click on the job name
3. Expand failed step to see error details
4. Common issues:
   - Invalid API keys (check secrets)
   - API rate limits (wait and retry)
   - Network issues (re-run workflow)

### 6. Customization Options

#### Change Schedule
Edit `.github/workflows/weekly-analytics.yml`:
```yaml
schedule:
  # Examples:
  - cron: '0 9 * * 1'    # Monday 9 AM UTC
  - cron: '0 14 * * 1'   # Monday 2 PM UTC (6 AM PST)
  - cron: '0 9 * * 1,4'  # Monday & Thursday
  - cron: '0 9 1 * *'    # First of month
```

#### Add Notifications
Add to workflow for email notifications:
```yaml
- name: Send email on success
  if: success()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: Philz Analytics Report Success
    to: team@company.com
    from: GitHub Actions
    body: The weekly analytics report completed successfully!
```

### 7. Best Practices

#### Security
- ✅ Never commit API keys to code
- ✅ Use GitHub Secrets for all credentials
- ✅ Keep repository private for business data
- ✅ Rotate API keys periodically
- ✅ Review workflow permissions

#### Monitoring
- Set up GitHub notifications for failed workflows
- Review artifacts periodically
- Monitor Slack channel for reports
- Check API usage/limits monthly

#### Maintenance
- Update dependencies monthly: `pip list --outdated`
- Review and optimize queries quarterly
- Archive old artifacts to reduce storage
- Document any customizations

### 8. Advanced Features

#### Multiple Environments
Create separate workflows for staging/production:
```yaml
# .github/workflows/analytics-staging.yml
env:
  ENVIRONMENT: staging
  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_STAGING }}
```

#### Conditional Execution
Skip holidays or specific dates:
```yaml
- name: Check if holiday
  id: holiday
  run: |
    TODAY=$(date +%m-%d)
    if [[ "$TODAY" == "12-25" || "$TODAY" == "01-01" ]]; then
      echo "skip=true" >> $GITHUB_OUTPUT
    fi

- name: Run analytics
  if: steps.holiday.outputs.skip != 'true'
  run: python braze_final_analytics.py
```

#### Multi-Brand Support
Use matrix strategy for multiple brands:
```yaml
strategy:
  matrix:
    brand: [philz, brand2, brand3]
env:
  BRAND: ${{ matrix.brand }}
  BRAZE_APP_ID: ${{ secrets[format('BRAZE_APP_ID_{0}', matrix.brand)] }}
```

## 📋 Checklist

- [ ] Repository created at winatecommerce96/philz-analytics
- [ ] Code pushed to main branch
- [ ] All 5 secrets configured
- [ ] Manual workflow tested successfully
- [ ] Slack message received
- [ ] Weekly schedule verified
- [ ] Team notified of new automation

## 🚨 Important Notes

1. **First Run**: The scheduled workflow won't run until the scheduled time after pushing
2. **Time Zones**: GitHub Actions uses UTC time
3. **Rate Limits**: Be aware of API rate limits for Braze and Claude
4. **Costs**: Claude API has usage costs - monitor consumption
5. **Secrets**: Never share or expose the secret values

## 🆘 Need Help?

1. Check workflow logs in Actions tab
2. Verify all secrets are set correctly
3. Test with manual workflow first
4. Check Slack webhook is active
5. Open an issue in the repository

---

Setup completed? Your analytics will now run automatically every Monday! 🎉