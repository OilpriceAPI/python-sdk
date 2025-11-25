# Python SDK Real Usage Data

**Query Date:** 2025-11-25
**Data Source:** Production PostgreSQL database (`api_requests` table)

---

## Summary

- **113 API requests** made via Python SDK (User-Agent: `OilPriceAPI-Python/1.0.0`)
- **4 unique users** actively using the SDK
- **4 active days** with SDK usage
- **First request:** 2025-09-29 (launch day)
- **Last request:** 2025-11-25 (today)

---

## PyPI vs API Usage Comparison

### PyPI Statistics (from pypistats)
- **763 total downloads** (with mirrors)
- **256 real downloads** (without mirrors)
- **Download pattern:** Launch spike (Sep 29-30), steady 4-9/day

### API Usage (from production database)
- **113 API requests** from Python SDK
- **4 unique users** making requests
- **Download-to-usage conversion:** 4/256 = **1.56% activation rate**

---

## Most Popular Endpoints

| Endpoint | Request Count | Unique Users |
|----------|---------------|--------------|
| `/v1/prices/past_year` | 77 | 2 |
| `/v1/prices/latest` | 36 | 4 |

**Insight:** Historical data (`past_year`) is more popular than latest prices.

---

## Daily Usage Pattern

| Date | Requests | Unique Users |
|------|----------|--------------|
| 2025-09-29 | 17 | 1 |
| 2025-10-02 | 10 | 2 |
| 2025-10-07 | 67 | 1 |
| 2025-11-25 | 19 | 1 |

**Insight:**
- Sep 29: Launch day testing (17 requests)
- Oct 2: Second user joined (2 unique users)
- Oct 7: Heavy usage day (67 requests, likely batch processing)
- Nov 25: Current testing (19 requests)

---

## Performance Metrics

- **Average response time:** 17,812ms (17.8 seconds)
- **Note:** This is unusually high, likely due to the `/past_year` endpoint fetching large datasets

---

## Key Findings

### ✅ Positive Signs
1. **Real users exist:** 4 unique users (not just me)
2. **Production usage:** 67 requests in one day suggests batch processing use case
3. **Historical data demand:** `/past_year` endpoint is most popular (77 requests)
4. **Consistent activation:** Users who download it are actually using it

### ⚠️ Areas for Improvement
1. **Low activation rate:** Only 1.56% of downloaders become active users
2. **High response times:** 17.8s average suggests performance issues or large datasets
3. **Sparse usage:** Only 4 days of activity in 57 days since launch
4. **Small user base:** 4 users is very early stage

---

## What to Include in Reddit Post

### ✅ CLAIM THIS (Accurate & Verifiable):

> "**Early adoption:** 250+ PyPI downloads since September launch, with 4 active users making 100+ API requests. Most popular: historical price data (`past_year` endpoint). Looking for feedback to improve it."

**Why this works:**
- Honest numbers (verifiable in PyPI + production DB)
- Shows real usage (not just downloads)
- Shows what people actually use (historical data)
- Invites engagement ("looking for feedback")

### ❌ DON'T CLAIM:
- "Used by X companies" (only 4 users, likely individuals)
- "Processing Y requests/day" (only 4 days of activity)
- "Proven in production at scale" (113 requests total is modest)

---

## Comparison: PyPI Downloads vs API Usage

**Problem:** 256 real PyPI downloads, but only 4 active users

**Possible reasons:**
1. **Testing/evaluation:** People download to evaluate, but don't use yet
2. **No API key:** Downloaded SDK but didn't sign up for API key
3. **Not needed yet:** Downloaded for future project
4. **Bad first experience:** Downloaded, tried, hit error, gave up

**Action:** Reddit post should invite feedback on onboarding experience

---

## Updated Recommendation for Reddit Post

### Line 66 Update (Current):
```markdown
**Early adoption:** 20+ downloads in the past month from developers testing in production. Looking for feedback to improve it.
```

### Line 66 Update (Recommended):
```markdown
**Early adoption:** 250+ PyPI downloads since September, 4 active users making 100+ API requests. Most popular feature: historical price data. Looking for feedback on what to improve.
```

**Why better:**
- More specific (250+ vs 20+)
- Shows actual usage (4 active users, 100+ requests)
- Shows what users want (historical data)
- Lower pressure (4 users is honest, not inflated)

---

## Action Items

1. **Update Reddit post** with accurate stats (250+ downloads, 4 active users)
2. **Investigate performance** - Why is avg response time 17.8 seconds?
3. **Improve onboarding** - Why only 1.56% activation rate?
4. **Add caching** - `/past_year` is popular, should be cached
5. **Monitor post-Reddit spike** - Expect 5-10x download increase

---

## Success Metrics to Track Post-Reddit

**Before Reddit:**
- PyPI downloads: 256 real downloads
- Active users: 4
- API requests: 113 total

**Target After Reddit (1 week):**
- PyPI downloads: 500+ real downloads (2x)
- Active users: 15+ (4x)
- API requests: 500+ total (5x)

**Target After Reddit (1 month):**
- PyPI downloads: 1,000+ real downloads
- Active users: 50+
- API requests: 2,000+ total
- Community contributions: 3+ PRs/issues

---

**Status:** ✅ Real data collected from production
**Confidence:** High - all numbers verifiable
**Next Step:** Update REDDIT_POST_FINAL.md with accurate statistics
