# SDK Telemetry & TAM Expansion Strategy

**Date:** 2025-11-25
**Current State:** 4 users, 113 API requests, 1.56% activation rate
**Goal:** Understand user behavior to expand TAM and improve product

---

## Current Telemetry (What We Know)

### From Production Database (`api_requests` table)

**We currently track:**
```sql
-- Available fields
user_id                 -- Which user
client_type             -- "sdk-python"
data->>'user_agent'     -- "OilPriceAPI-Python/1.0.0"
data->>'path'           -- "/v1/prices/past_year"
created_at              -- When
response_status         -- Success/failure
response_time_ms        -- Performance
ip_address              -- Geographic data
country, city, region   -- Location
```

**What we learned:**
- ✅ 68% use historical data (`/past_year`)
- ✅ 32% use latest prices
- ✅ Batch processing use case (67 requests in one day)
- ✅ 4 unique users across 4 days
- ❌ Don't know: Why they need the data
- ❌ Don't know: What they're building
- ❌ Don't know: If they're sync or async
- ❌ Don't know: If they hit errors

---

## The Big Questions (For TAM Expansion)

### 1. Who Are These Users?

**What we need to know:**
- Industry? (Energy trading, research, fintech, academia?)
- Use case? (Trading bot, research paper, portfolio analysis?)
- Company size? (Individual, startup, enterprise?)
- Geographic market? (US energy companies vs international?)

**Why it matters for TAM:**
- If users are researchers → TAM = Academic institutions
- If users are traders → TAM = Hedge funds, prop trading firms
- If users are analysts → TAM = Financial services firms
- If users are developers → TAM = Fintech startups

### 2. What Are They Building?

**What we need to know:**
- Trading algorithms?
- Research dashboards?
- Price alerts/notifications?
- Data analysis pipelines?
- Historical trend analysis?

**Why it matters for TAM:**
- Different use cases = different buyer personas
- Can build targeted features for each segment
- Can price differently for different use cases
- Can market to similar companies in same vertical

### 3. What Problems Do They Hit?

**What we need to know:**
- Which commodities fail most often?
- Which endpoints have errors?
- Do they retry? How many times?
- Do they abandon after errors?
- Performance issues?

**Why it matters for TAM:**
- Fix blockers preventing activation (1.56% → 10%+)
- Reduce churn from technical issues
- Improve onboarding based on common errors

---

## Proposed Telemetry Enhancements

### Phase 1: Better Backend Tracking (No SDK Changes)

**Already have this data, just need to query it better:**

```sql
-- Create analytics views in production DB

-- 1. SDK User Cohort Analysis
CREATE VIEW sdk_user_cohorts AS
SELECT
  user_id,
  MIN(created_at) as first_request_date,
  MAX(created_at) as last_request_date,
  COUNT(*) as total_requests,
  COUNT(DISTINCT DATE(created_at)) as active_days,
  COUNT(DISTINCT data->>'path') as unique_endpoints,
  AVG(response_time_ms) as avg_response_time,
  -- Segment by usage pattern
  CASE
    WHEN COUNT(*) >= 50 THEN 'power_user'
    WHEN COUNT(*) >= 10 THEN 'regular_user'
    ELSE 'trial_user'
  END as user_segment
FROM api_requests
WHERE client_type = 'sdk-python'
GROUP BY user_id;

-- 2. SDK Error Analysis
CREATE VIEW sdk_error_analysis AS
SELECT
  data->>'path' as endpoint,
  response_status,
  COUNT(*) as error_count,
  COUNT(DISTINCT user_id) as affected_users,
  AVG(response_time_ms) as avg_response_time
FROM api_requests
WHERE client_type = 'sdk-python'
  AND response_status >= 400
GROUP BY endpoint, response_status
ORDER BY error_count DESC;

-- 3. SDK Commodity Popularity
CREATE VIEW sdk_commodity_usage AS
SELECT
  data->>'commodity' as commodity,
  COUNT(*) as request_count,
  COUNT(DISTINCT user_id) as unique_users,
  AVG(response_time_ms) as avg_response_time
FROM api_requests
WHERE client_type = 'sdk-python'
GROUP BY commodity
ORDER BY request_count DESC;
```

**Action:** Create these views this week, add to weekly analytics dashboard

---

### Phase 2: Optional Error Telemetry (SDK Changes - Opt-in)

**Add to SDK (user must opt-in):**

```python
from oilpriceapi import OilPriceAPI

# Opt-in to error telemetry
client = OilPriceAPI(
    send_error_telemetry=True,  # Default: False (privacy-first)
    telemetry_tags={
        "environment": "production",
        "use_case": "trading_bot",  # Optional user-provided context
    }
)
```

**What we'd track (only if opted in):**
- Exception types hit (but not exception messages)
- Retry attempts needed
- Which methods called (not parameters)
- Python version, OS (for compatibility)

**Privacy guarantees:**
- ❌ NO API keys tracked
- ❌ NO price data tracked
- ❌ NO commodity codes tracked
- ❌ NO user data tracked
- ✅ ONLY error types and counts

**Implementation:**
```python
# In oilpriceapi/telemetry.py (new file)
import httpx
from typing import Optional, Dict

class TelemetryClient:
    """Optional error telemetry (opt-in only)."""

    def __init__(self, enabled: bool = False, tags: Optional[Dict] = None):
        self.enabled = enabled
        self.tags = tags or {}

    def track_error(self, error_type: str, context: Dict):
        """Send error telemetry if enabled."""
        if not self.enabled:
            return

        # Send to telemetry endpoint (async, fire-and-forget)
        data = {
            "error_type": error_type,
            "sdk_version": "1.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "tags": self.tags,
            # NO user data, NO API keys, NO prices
        }

        try:
            httpx.post(
                "https://telemetry.oilpriceapi.com/sdk/errors",
                json=data,
                timeout=1.0  # Don't slow down user's app
            )
        except:
            pass  # Never fail user's app due to telemetry
```

**Benefit:** Would tell us which errors are most common, help prioritize fixes

**Risk:** Privacy concerns, adds complexity, most users won't opt-in

**Recommendation:** Skip this for now, focus on Phase 1 and Phase 3

---

### Phase 3: User Discovery Survey (Proactive Outreach)

**Instead of passive telemetry, actively reach out to users:**

**Action Plan:**

1. **Identify SDK users from DB:**
   ```sql
   SELECT DISTINCT u.email, u.company_domain, COUNT(*) as requests
   FROM api_requests ar
   JOIN users u ON ar.user_id = u.id
   WHERE ar.client_type = 'sdk-python'
   GROUP BY u.email, u.company_domain
   ORDER BY requests DESC;
   ```

2. **Send personalized email:**
   ```
   Subject: Quick question about your use of OilPriceAPI Python SDK

   Hi [Name],

   I noticed you've been using the OilPriceAPI Python SDK (thanks!).

   I'm working on making it better and would love to understand:
   - What are you building with it?
   - Which features matter most to you?
   - What's missing that would make it more useful?

   Quick 5-minute call this week? Or just reply with your thoughts.

   Karl
   Founder, OilPriceAPI
   ```

3. **Track responses in CRM:**
   - Use case
   - Industry
   - Company size
   - Feature requests
   - Willingness to upgrade

**Benefits:**
- ✅ Direct feedback on use cases
- ✅ Identify TAM opportunities
- ✅ Build relationships with users
- ✅ Get testimonials/case studies
- ✅ Convert free → paid

**Effort:** 1 hour to send 4 emails, 2-3 hours for calls

**Expected response rate:** 50-75% (only 4 users, easy to reach)

---

### Phase 4: Company Domain Analysis (Already Available)

**We already track `company_domain` in users table.**

**Query current SDK users:**
```sql
SELECT
  u.email,
  u.company_domain,
  COUNT(*) as api_requests,
  MAX(ar.created_at) as last_active
FROM users u
JOIN api_requests ar ON u.id = ar.user_id
WHERE ar.client_type = 'sdk-python'
GROUP BY u.email, u.company_domain;
```

**For each company domain, research:**
- Company size (LinkedIn, Crunchbase)
- Industry (Energy? Fintech? Research?)
- Funding status (if startup)
- Likely use case based on industry

**Tool: Clearbit Enrichment API:**
```bash
curl "https://company.clearbit.com/v2/companies/find?domain=company.com" \
  -H "Authorization: Bearer sk_..."
```

**Returns:**
- Company name
- Industry
- Employee count
- Revenue estimate
- Tech stack
- Funding

**Action:** Run this analysis on all 4 SDK users this week

---

## TAM Expansion Opportunities

### Based on Current Data (68% historical, 32% latest)

**Hypothesis:** Users are doing **historical analysis**, not real-time trading

**Potential TAM segments:**

1. **Financial Research Firms**
   - Use case: Energy sector equity research
   - Need: Historical commodity prices for valuation models
   - TAM: 500+ equity research firms globally
   - Pricing: $200-500/month (higher limits, more commodities)

2. **Academic Researchers**
   - Use case: Energy economics research papers
   - Need: Historical data for econometric analysis
   - TAM: 1,000+ universities with energy programs
   - Pricing: $50/month academic tier

3. **Portfolio Managers**
   - Use case: Energy commodity exposure analysis
   - Need: Historical correlations, risk metrics
   - TAM: 5,000+ RIAs, family offices
   - Pricing: $100-300/month

4. **Energy Trading Firms** (if we add real-time)
   - Use case: Algorithmic trading, arbitrage
   - Need: Low-latency real-time prices
   - TAM: 200+ energy trading desks
   - Pricing: $1,000-5,000/month (enterprise)

### New Features to Unlock TAM

**Based on user behavior (historical data = 68%):**

1. **Bulk Historical Download**
   ```python
   # Add to SDK
   client.prices.get_historical_bulk(
       commodities=["BRENT", "WTI", "NATGAS"],
       start_date="2020-01-01",
       end_date="2024-12-31",
       format="parquet"  # Or CSV, JSON
   )
   ```
   **Unlocks:** Research firms, data scientists

2. **Statistical Analysis Methods**
   ```python
   # Built into SDK
   df = client.prices.get_historical("BRENT", days=365)
   stats = df.describe()  # Summary statistics
   corr = df.correlation("WTI")  # Cross-commodity correlation
   ```
   **Unlocks:** Quant researchers, portfolio managers

3. **Pandas DataFrame Integration**
   ```python
   # First-class DataFrame support
   df = client.prices.to_dataframe("BRENT", days=90)
   # Already Pandas-ready for analysis
   ```
   **Unlocks:** Data analysts, Jupyter notebook users

4. **Historical Data Caching**
   ```python
   # Cache historical data locally
   client = OilPriceAPI(cache_historical=True, cache_ttl=86400)
   # Historical data cached 24h, reduces API calls
   ```
   **Unlocks:** Free tier users doing repeated analysis

---

## Recommended Action Plan

### This Week (Immediate)

**1. Query Production DB for SDK Users (30 min):**
```sql
SELECT
  u.email,
  u.company_domain,
  u.created_at as signup_date,
  COUNT(ar.id) as total_requests,
  MIN(ar.created_at) as first_api_call,
  MAX(ar.created_at) as last_api_call
FROM users u
JOIN api_requests ar ON u.id = ar.user_id
WHERE ar.client_type = 'sdk-python'
GROUP BY u.id, u.email, u.company_domain, u.created_at
ORDER BY total_requests DESC;
```

**2. Research Each User's Company (1 hour):**
- Look up company domain on LinkedIn
- Check Crunchbase if startup
- Identify industry and likely use case
- Document in spreadsheet

**3. Send Personalized Outreach Emails (1 hour):**
- 4 users = 4 emails
- Ask about use case and needs
- Offer 15-min call
- Track responses

**Expected outcome:** 2-3 responses, understand use cases, identify TAM

---

### Next Week (After User Conversations)

**4. Create User Personas (2 hours):**
Based on responses, create 2-3 personas:
- Persona A: Financial Analyst (historical analysis)
- Persona B: Energy Trader (real-time prices)
- Persona C: Academic Researcher (bulk historical)

**5. Build TAM Model (2 hours):**
For each persona:
- Market size (number of potential users)
- Willingness to pay
- Feature requirements
- Go-to-market strategy

**6. Prioritize Features (1 hour):**
- What features unlock which personas?
- What's the ROI of building each?
- What can we ship this month?

---

### Month 2 (After Feature Prioritization)

**7. Ship Top 1-2 Features:**
- Bulk historical download (if researchers)
- DataFrame integration (if analysts)
- Caching (if free users)

**8. Create Targeted Marketing:**
- Case study from first user
- Blog post: "How [Company] uses OilPriceAPI for [Use Case]"
- Reddit post to r/algotrading or r/finance (targeted to persona)

**9. Experiment with Pricing:**
- Research tier: $50/month
- Professional tier: $200/month
- Enterprise tier: Custom pricing

---

## Privacy-First Telemetry Principles

**If we add any telemetry, follow these rules:**

1. **Opt-in only** - Default: OFF
2. **No sensitive data** - Never track API keys, prices, commodities
3. **Transparent** - Document exactly what we track
4. **User control** - Easy to disable
5. **Open source** - Show telemetry code in SDK repo

**Example documentation:**
```markdown
## Optional Error Telemetry

To help us improve the SDK, you can opt-in to anonymous error reporting:

```python
client = OilPriceAPI(send_error_telemetry=True)
```

**What we track:**
- Error types (e.g., "TimeoutError", "RateLimitError")
- SDK version
- Python version

**What we DON'T track:**
- Your API key
- Price data
- Commodity codes
- Personal information

You can disable this at any time by setting `send_error_telemetry=False`.
```

---

## Quick Wins vs Long-term Strategy

### Quick Wins (This Week)

1. ✅ **Query production DB** - See what we already have
2. ✅ **Email 4 SDK users** - Direct feedback
3. ✅ **Research company domains** - Understand industries
4. ✅ **Create analytics dashboard** - Track SDK metrics weekly

**Effort:** 4-5 hours
**Impact:** High - understand current users, identify TAM

### Long-term Strategy (Next 3 Months)

1. ⏳ **Build user personas** - Based on conversations
2. ⏳ **Ship top-requested features** - Unlock new segments
3. ⏳ **Create vertical marketing** - Target specific industries
4. ⏳ **Experiment with pricing** - Capture willingness to pay

**Effort:** 40-60 hours
**Impact:** Very high - expand TAM, increase revenue

---

## Success Metrics

### Current State
- 4 SDK users
- 113 API requests total
- 1.56% activation rate (4/256 downloads)
- $0 MRR from SDK users

### 1-Month Goal (After User Discovery)
- 10 SDK users (2.5x growth)
- 500+ API requests/month
- 5% activation rate
- 2 users on paid tier = $100-400 MRR

### 3-Month Goal (After Feature Expansion)
- 30 SDK users (7.5x growth)
- 2,000+ API requests/month
- 10% activation rate
- 10 users on paid tier = $500-2,000 MRR

### 6-Month Goal (TAM Expansion)
- 100 SDK users
- 10,000+ API requests/month
- 15% activation rate
- 30 users on paid tier = $1,500-6,000 MRR
- 3 enterprise customers = $3,000-15,000 MRR

---

## Recommendation: Start with User Discovery

**Best approach for TAM expansion:**

1. ✅ **This week:** Email all 4 SDK users, ask about use case
2. ✅ **Next week:** Build personas based on responses
3. ✅ **Week 3:** Ship 1-2 features for top persona
4. ✅ **Week 4:** Create case study, post to relevant subreddit
5. ⏳ **Month 2:** Repeat for next persona

**Why this works:**
- Low cost (just time)
- Direct feedback from real users
- Identify highest-value segments
- Build features users actually want
- Get testimonials for marketing

**Alternative (passive telemetry):**
- High development cost
- Privacy concerns
- Low opt-in rate
- Slow feedback loop
- No direct relationship with users

**Verdict:** Active user discovery >> Passive telemetry

---

**Status:** Ready to start user discovery this week
**First action:** Query production DB for SDK user emails
**Expected outcome:** Understand 2-3 use cases, identify TAM opportunities
