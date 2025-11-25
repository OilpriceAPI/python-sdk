# Python SDK Usage Analysis

**Date:** 2025-11-25
**Period:** Sep 29, 2025 - Nov 25, 2025 (57 days)

---

## PyPI Download Statistics

### Total Downloads
- **763 total downloads** (with mirrors)
- **256 real user downloads** (without mirrors)
- **507 mirror/CI downloads** (automated systems)

### Download Pattern Analysis

**Initial Launch (Sep 29-30):**
- 186 downloads in 2 days (128 + 58)
- Likely your own testing + early adopters

**Second Spike (Oct 2):**
- 164 downloads in 1 day
- Possibly CI/CD testing or automated deployment

**Steady State (Oct 7 - Nov 25):**
- 4-9 downloads per day
- Consistent, organic growth
- **~200 downloads/month** current rate

### Key Insights

✅ **Real Users Exist:** 256 real downloads (not just mirrors)
✅ **Sustained Interest:** Consistent 4-9 downloads/day for 7 weeks
✅ **Early Stage:** Still pre-viral, perfect time for Reddit push

---

## Telemetry & Tracking

### What the SDK Tracks

**User-Agent Headers:**
```python
# Sync client
"User-Agent": "OilPriceAPI-Python/1.0.0"

# Async client
"User-Agent": "OilPriceAPI-Python-Async/1.0.0"
```

### What the API Backend Tracks

From `api_requests` table:
- `user_agent` - Client identification
- `client_type` - Parsed from User-Agent
- `user_id` - Which user made the request
- `commodity_requested` - What data they accessed
- `created_at` - When
- `ip_address` - Where from
- `status_code` - Success/failure

### Available Analytics

**We can query production DB for:**
1. How many requests from Python SDK users
2. Which commodities are most popular
3. Unique users using Python SDK
4. Python SDK vs curl vs Postman usage
5. Geographic distribution (from IP)
6. Time-based usage patterns

---

## What We DON'T Know (Yet)

❌ **Usage Patterns:**
- Are they using sync or async client?
- Are they hitting errors? Which ones?
- Are they using Pandas integration?
- Which methods are most called?

❌ **User Segments:**
- Who are these 256 downloaders?
- Are they individuals or companies?
- Which industries?
- What problem are they solving?

❌ **Success Metrics:**
- How many downloads lead to API usage?
- Conversion rate: download → signup → paid?
- Retention: do they keep using it?

---

## Recommendations for Better Telemetry

### Phase 1: Basic Analytics (No Code Change)

**Query production DB:**
```sql
-- Python SDK usage in last 30 days
SELECT
  COUNT(*) as total_requests,
  COUNT(DISTINCT user_id) as unique_users,
  AVG(response_time_ms) as avg_latency
FROM api_requests
WHERE user_agent LIKE '%OilPriceAPI-Python%'
  AND created_at >= NOW() - INTERVAL '30 days';

-- Most popular commodities
SELECT
  commodity_requested,
  COUNT(*) as request_count
FROM api_requests
WHERE user_agent LIKE '%OilPriceAPI-Python%'
GROUP BY commodity_requested
ORDER BY request_count DESC
LIMIT 10;

-- SDK version distribution
SELECT
  CASE
    WHEN user_agent LIKE '%Python/1.0.0%' THEN 'v1.0.0'
    WHEN user_agent LIKE '%Python/1.0.1%' THEN 'v1.0.1'
    ELSE 'Other'
  END as version,
  COUNT(*) as request_count
FROM api_requests
WHERE user_agent LIKE '%OilPriceAPI-Python%'
GROUP BY version;
```

**Action:** Run these queries NOW to understand current usage

---

### Phase 2: Enhanced User-Agent (Optional)

**Current:**
```
User-Agent: OilPriceAPI-Python/1.0.0
```

**Enhanced (Optional):**
```
User-Agent: OilPriceAPI-Python/1.0.1 (Python/3.12; httpx/0.24.0; sync)
```

**Pros:**
- Track Python version distribution
- See sync vs async usage
- Identify httpx version issues

**Cons:**
- More verbose
- Privacy concerns (leaks environment info)
- Not standard practice

**Verdict:** Skip this unless you need it for debugging

---

### Phase 3: Error Telemetry (Future)

**Add optional error reporting:**
```python
client = OilPriceAPI(
    send_error_telemetry=False,  # Opt-in only
)
```

**Would track:**
- Which exceptions users hit
- Retry patterns (how many retries needed?)
- Performance issues (slow responses?)

**Privacy:**
- Must be opt-in
- No sensitive data (API keys, prices, etc.)
- Only error types and counts

**Verdict:** Consider for v2.0 if users ask for it

---

## What to Include in Reddit Post

### ✅ CLAIM THIS:
> "250+ downloads since launch in September, with 4-9 downloads per day in recent weeks. Early users testing in production."

**Why this works:**
- Honest numbers (verifiable)
- Shows traction (not zero)
- Shows consistency (not one-time spike)
- Invites more users ("early users")

### ❌ DON'T CLAIM:
- "Used by X companies" (we don't know)
- "Processing Y requests/day" (need to query DB)
- "Proven in production at scale" (too bold)

---

## Action Items

### Before Reddit Post:

**1. Query Production DB (High Priority)**
```bash
# Get actual usage stats
export PGPASSWORD=<YOUR_DB_PASSWORD>
psql -h <YOUR_DB_HOST> \
     -p 25060 -U doadmin -d defaultdb \
     -f /tmp/check_sdk_usage.sql
```

**Why:** Can claim "X requests from Python SDK users in last 30 days"

**2. Update Reddit Post with Real Numbers**

Instead of:
> "20+ downloads in the past month"

Say:
> "250+ downloads since September launch, with 4-9 downloads per day in recent weeks. [X unique users] making [Y API requests] via Python SDK."

**3. Create Usage Dashboard (Optional)**

Simple page showing:
- PyPI downloads/month
- Active SDK users
- Most popular commodities
- SDK vs other clients

**Benefits:**
- Transparency builds trust
- Shows growth over time
- Attracts more users ("look, people use this!")

---

## Reddit Post Updates Based on Data

### Current Line (Line 66):
> "**Early adoption:** 20+ downloads in the past month from developers testing in production. Looking for feedback to improve it."

### Proposed Update:
> "**Early adoption:** 250+ PyPI downloads since September launch, averaging 4-9 downloads per day. [X unique users] actively using it. Looking for feedback to improve it."

### Even Better (After DB Query):
> "**Early adoption:** 250+ PyPI downloads, [X] active users making [Y] API requests/month via Python SDK. Most popular: [Top 3 commodities]. Looking for feedback on what to build next."

**Why this works:**
- Shows real traction (250+ is better than 20+)
- Shows it's being used (not just downloaded)
- Shows what people actually do (top commodities)
- Invites engagement ("what to build next")

---

## Next Steps

1. **Query production DB** to get real usage numbers
2. **Update Reddit post** with accurate stats
3. **Post to r/Python** Tuesday-Thursday 9-11am EST
4. **Monitor PyPI downloads** post-Reddit (expect 5-10x spike)
5. **Query DB again in 1 week** to see Reddit impact

---

## Success Metrics to Track

**Before Reddit Post:**
- PyPI downloads: 250+ total, ~8/day
- GitHub stars: 0
- Active SDK users: [Query DB]

**Target After Reddit Post (1 week):**
- PyPI downloads: 500+ total, ~40/day (5x increase)
- GitHub stars: 20+
- Active SDK users: 2x increase

**Target After Reddit Post (1 month):**
- PyPI downloads: 1,000+ total, ~30/day sustained
- GitHub stars: 50+
- Active SDK users: 5x increase
- 3+ PRs/issues from community

---

## The Big Question

**You asked:** "Is there any telemetry to tell what people are doing with it?"

**Answer:**
- ✅ **Yes:** API backend tracks every request with User-Agent
- ✅ **We can query:** Which commodities, how many requests, unique users
- ❌ **Need to run query:** Don't have the numbers yet
- ❌ **Limited visibility:** Can't see if they're using Pandas, async, CLI

**Recommendation:**
Run the DB query NOW before updating Reddit post. Having real numbers like "50 unique SDK users making 2,000+ requests/month" is WAY more credible than "20+ downloads."

---

**Status:** Ready to query production DB for real usage stats
**Impact:** Will make Reddit post 10x more credible
**Effort:** 5 minutes to run SQL query
