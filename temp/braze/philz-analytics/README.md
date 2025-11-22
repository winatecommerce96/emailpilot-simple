# Philz Analytics - Automated Braze Revenue Reports

[![Weekly Analytics](https://github.com/winatecommerce96/philz-analytics/actions/workflows/weekly-analytics.yml/badge.svg)](https://github.com/winatecommerce96/philz-analytics/actions/workflows/weekly-analytics.yml)
[![Manual Report](https://github.com/winatecommerce96/philz-analytics/actions/workflows/manual-analytics.yml/badge.svg)](https://github.com/winatecommerce96/philz-analytics/actions/workflows/manual-analytics.yml)

Automated weekly revenue analytics for Philz Coffee, comparing current performance against month-ago and year-ago periods with AI-powered insights via Claude Opus 4.1.

## 🎯 Features

- **3-Period Comparison**: Current 7 days vs Month Ago vs Year Ago
- **Comprehensive Metrics**:
  - Revenue & Orders
  - AOV (Average Order Value)
  - Conversion Rate
  - Sessions & New Users
  - Revenue per Session/User
  - MAU (Monthly Active Users)
- **AI Analysis**: Claude Opus 4.1 provides:
  - 2-sentence executive summary
  - Top 3 wins (natural language)
  - Top 3 email marketing improvements
- **Slack Integration**: Beautiful formatted reports sent to your team
- **GitHub Actions**: Fully automated weekly reports

## 🚀 Quick Start

### GitHub Actions Setup (Recommended)

1. Fork/clone this repository
2. Go to Settings → Secrets and variables → Actions
3. Add these repository secrets:
   - `BRAZE_API_KEY`
   - `BRAZE_APP_ID`
   - `BRAZE_BASE_URL`
   - `CLAUDE_API_KEY`
   - `SLACK_WEBHOOK_URL`
4. The workflow runs automatically every Monday at 9 AM UTC
5. Or trigger manually from Actions tab

### Local Installation

```bash
# Clone the repository
git clone https://github.com/winatecommerce96/philz-analytics.git
cd philz-analytics

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.example .env
# Edit .env with your credentials

# Run the analytics
python braze_final_analytics.py
```

## 📊 Sample Output

```
🚀 Philz Analytics Report
Period Comparison • Nov 17, 2025

🎯 Goal Progress (LY+10%): [▓▓▓▓▓▓▓▓░░] 89.2% | $104,337 of $117,000 | 13d left

📊 METRICS SUMMARY
💰 Revenue: $104,337 (+9%/+11%)
📦 Orders: 1,833 (+4%/-5%)
💵 AOV: $56.92 (+4%/+17%)
🎯 Conv Rate: 4.20% (+30%/+1%)
📈 Rev/Session: $2.39 (+36%/+18%)
👤 Rev/User: $0.59 (+5%/-5%)
🆕 New Users: 29,988 (-25%/-7%)
📊 MAU: 178,216

Format: Current (MoM%/YoY%)

🏆 Top 3 Wins
• Your conversion rate surge of 30% month-over-month...
• Average order value climbed 17% year-over-year...
• Revenue per session increased by 36%...

📧 Email Marketing Improvements
• QUICK WIN: Set up proper email attribution tracking...
• MEDIUM EFFORT: Launch a sophisticated cart abandonment...
• STRATEGIC: Build comprehensive holiday gifting campaign...
```

## 🔧 Configuration

### Customizing for Your Brand

Edit `braze_final_analytics.py`:
- Line 564: Change report title
- Lines 241-242: Update brand context for AI
- Lines 334-345: Modify improvement focus areas

### Adjusting Metrics

Modify the `collect_period_metrics()` method to:
- Add/remove metrics
- Change comparison periods
- Update goal targets

## 📅 GitHub Actions Workflows

### Weekly Automated Report
- **Schedule**: Every Monday 9 AM UTC
- **File**: `.github/workflows/weekly-analytics.yml`
- **Artifacts**: Saves results for 30 days

### Manual Report
- **Trigger**: On-demand from Actions tab
- **File**: `.github/workflows/manual-analytics.yml`
- **Options**: Configure period and Slack posting

## 🔐 Security

All sensitive credentials are stored as GitHub Secrets:
- API keys never exposed in code
- Webhook URLs kept private
- Environment variables for all secrets

## 📈 Metrics Explained

| Metric | Description | Calculation |
|--------|-------------|-------------|
| AOV | Average Order Value | Revenue ÷ Orders |
| Conv Rate | Conversion Rate | (Orders ÷ Sessions) × 100 |
| Rev/Session | Revenue per Session | Revenue ÷ Sessions |
| Rev/User | Revenue per User | Revenue ÷ MAU |
| MAU | Monthly Active Users | Unique users in 30 days |

## 🐛 Troubleshooting

### Common Issues

1. **API 404 Errors**: Check BRAZE_APP_ID is correct
2. **Slack Not Posting**: Verify webhook URL is active
3. **Claude Errors**: Check API key and rate limits
4. **No Data**: Verify date ranges and API permissions

### Testing

```bash
# Test AOV calculation
./test_aov_calculation.sh

# Test revenue metrics
./test_revenue_call.sh

# Run with debug output
python braze_final_analytics.py 2>&1 | tee debug.log
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check Braze API docs: https://www.braze.com/docs/api
- Check Claude docs: https://docs.anthropic.com

---

Built with ❤️ for Philz Coffee by WinAt eCommerce