# Smart Mode - Quick Reference Guide

## 🎯 Quick Start

### 1. Open the App
```
http://127.0.0.1:5001
```

### 2. Select Processing Mode

| Mode | When to Use | Cost | Accuracy |
|------|-------------|------|----------|
| ⚡ **Local** | Simple, well-formatted PDFs | FREE | 70% |
| 🧠 **Smart** ⭐ | **Most PDFs (Recommended)** | **$0-0.20** | **85-95%** |
| 🤖 **AI Only** | Complex/scanned PDFs | $0.20+ | 95% |

### 3. Configure Settings

**API Key** (for Smart/AI modes):
- Get from: https://platform.openai.com/api-keys
- Format: `sk-...`
- Never stored, only used for this request

**Page Limit** (for Smart/AI modes):
- **5 pages:** Cheaper (~$0.10), good for quarterly results
- **10 pages:** Balanced (default, ~$0.20)
- **15 pages:** More thorough (~$0.30)
- **20 pages:** Maximum accuracy (~$0.40)

### 4. Upload PDF
- Drag & drop OR
- Browse to select OR
- Paste BSE/NSE URL

### 5. Analyze
Click "Analyze Result" and wait 5-20 seconds

---

## 🧠 Smart Mode Explained

### How It Works:

```
1. Try Local Extraction (FREE)
   ↓
2. Check Confidence
   ↓
   ├─ ✅ High Confidence → Use Local Results (SAVE $0.20)
   │
   └─ ❌ Low Confidence → Fallback to AI (COST $0.20)
```

### Confidence Criteria:

✅ **High Confidence (Use Local):**
- Revenue found and > 0
- Profit metrics present
- Clean table extraction
- No errors

❌ **Low Confidence (Use AI):**
- Revenue = 0 or missing
- No profit data
- Table extraction failed
- Errors detected

---

## 💰 Cost Comparison

### Example: 100 PDFs per month

| Mode | Cost per PDF | Total Cost | Savings |
|------|--------------|------------|---------|
| AI Only | $0.20 | $20.00 | - |
| Smart Mode | $0.06* | $6.00 | **$14.00 (70%)** |
| Local Only | $0.00 | $0.00 | $20.00 (100%)** |

*Assumes 70% success rate with local extraction  
**May have lower accuracy

---

## 🎨 Visual Indicators

### Processing Method Badges:

| Badge | Color | Meaning | Cost |
|-------|-------|---------|------|
| **Local** | 🟢 Green | Processed locally | $0.00 |
| **AI (Fallback)** | 🟠 Orange | Local failed, used AI | ~$0.20 |
| **AI** | 🔵 Blue | Direct AI processing | ~$0.20 |

### Result Type Badge:

| Badge | Meaning |
|-------|---------|
| **Consolidated** | Main results (preferred) |
| **Standalone** | Individual entity results |

---

## 📊 Understanding Results

### Financial Table:
- **QoQ %:** Quarter-over-Quarter growth
- **YoY %:** Year-over-Year growth
- **Green numbers:** Positive growth ✅
- **Red numbers:** Negative growth/losses ⚠️

### Growth Metrics:
- Revenue growth (QoQ & YoY)
- Net Profit growth (QoQ & YoY)

### Corporate Actions:
- 💰 Dividend declarations
- 🏗️ Capex/expansion plans
- 👔 Management changes
- 🚀 New projects/orders
- 📢 Special announcements

### Key Observations:
- 🚨 Critical red flags
- ⚠️ Warning signs
- 📉 Negative trends

### Recommendation:
- **BUY / ACCUMULATE** (Green): Strong fundamentals
- **HOLD / NEUTRAL** (Orange): Mixed signals
- **STRONG AVOID / SELL** (Red): Major concerns

---

## 🔧 Troubleshooting

### "No valid financial data found"
**Solution:**
1. Try AI mode instead of Local
2. Increase page limit to 15-20
3. Check if PDF is readable (not password-protected)

### "Invalid API key"
**Solution:**
1. Verify key starts with `sk-`
2. Check for extra spaces
3. Generate new key from OpenAI dashboard

### "Rate limit exceeded"
**Solution:**
1. Wait 1 minute
2. Upgrade OpenAI plan
3. Use Local mode temporarily

### "Insufficient quota"
**Solution:**
1. Add credits to OpenAI account
2. Use Local mode
3. Reduce page limit to 5

---

## 💡 Pro Tips

### Maximize Cost Savings:
1. ✅ Use **Smart mode** as default
2. ✅ Start with **10 pages**, reduce to 5 if budget-tight
3. ✅ Use **Local mode** for simple quarterly results
4. ✅ Reserve **AI mode** for complex annual reports

### Maximize Accuracy:
1. ✅ Use **AI mode** for critical analysis
2. ✅ Set page limit to **15-20** for complex PDFs
3. ✅ Verify results against original PDF
4. ✅ Check processing method badge

### Best Practices:
1. ✅ Keep API key secure (never share)
2. ✅ Test with sample PDF first
3. ✅ Monitor which method is being used
4. ✅ Adjust page limit based on PDF complexity

---

## 📈 Optimization Strategy

### For Regular Use (100+ PDFs/month):

**Week 1:** Use Smart mode, track success rate
```
If Local success rate > 70%:
  → Continue with Smart mode
  → Expected savings: 60-80%

If Local success rate < 50%:
  → Your PDFs are complex
  → Consider AI mode with 10 pages
  → Or improve PDF quality
```

**Week 2-4:** Optimize based on results
```
High accuracy needed:
  → AI mode, 15 pages

Cost-sensitive:
  → Smart mode, 5 pages
  → Accept 80-90% accuracy
```

---

## 🆘 Support

### Common Questions:

**Q: Which mode should I use?**  
A: Start with **Smart mode** - it's the best balance.

**Q: How much does AI cost?**  
A: ~$0.02 per page. 10 pages = $0.20 per PDF.

**Q: Can I use without API key?**  
A: Yes! Use **Local mode** (free, 70% accurate).

**Q: Why did it use AI when I selected Smart?**  
A: Local extraction had low confidence. Check the badge for details.

**Q: How to reduce costs?**  
A: Use Smart mode + reduce page limit to 5.

**Q: How to improve accuracy?**  
A: Use AI mode + increase page limit to 15-20.

---

## 📝 Changelog

### Version 2.1 (December 24, 2025)
- ✅ Added Smart hybrid mode
- ✅ Added configurable page limits
- ✅ Added processing method indicators
- ✅ Added confidence evaluation
- ✅ Added cost tracking
- ✅ Improved UI with mode descriptions

### Version 2.0 (Previous)
- AI-powered analysis
- Local extraction
- Corporate actions tracking

---

**Need Help?** Check the full documentation in `DOCUMENTATION.md`

**Want Details?** See implementation summary in `IMPLEMENTATION_SUMMARY.md`
