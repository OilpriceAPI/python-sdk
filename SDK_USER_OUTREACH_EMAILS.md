# SDK User Outreach Emails

**Date:** 2025-11-25
**Total SDK Users:** 4
**External Users to Contact:** 2 (Bracco, Stevan)

---

## User Overview

| Email | Name | Plan | Status |
|-------|------|------|--------|
| braccobaldojp@yahoo.it | Bracco | Free | Contact |
| jokicstevan@gmail.com | Stevan Jokic | Free | Contact |
| karl.waldman@gmail.com | Karl M Waldman | Free | Skip (you) |
| karl.waldman+wallet@gmail.com | KARL Michael WALDMAN | Enterprise | Skip (you) |

---

## Email #1: Bracco (braccobaldojp@yahoo.it)

**Subject:** Quick question about your use of OilPriceAPI Python SDK

**Body:**
```
Hi Bracco,

I noticed you've been using the OilPriceAPI Python SDK - thanks for trying it out!

I'm Karl, the founder of OilPriceAPI. I'm working on making the Python SDK better and would love to understand how you're using it.

Quick questions (no pressure):
- What are you building with the SDK?
- Which features are most useful to you?
- What's missing that would make it more valuable?

Just reply with your thoughts - even a quick one-liner helps!

Also, if you have any questions about the API or SDK, I'm here to help.

Best,
Karl
Founder, OilPriceAPI
karl@oilpriceapi.com
```

**Why this works:**
- Personal (uses their name)
- Brief (respects their time)
- Offers value (help with questions)
- Multiple response options (call or email)
- No sales pitch

---

## Email #2: Stevan Jokic (jokicstevan@gmail.com)

**Subject:** Quick question about your use of OilPriceAPI Python SDK

**Body:**
```
Hi Stevan,

I noticed you've been using the OilPriceAPI Python SDK - thanks for trying it out!

I'm Karl, the founder of OilPriceAPI. I'm working on making the Python SDK better and would love to understand how you're using it.

Quick questions (no pressure):
- What are you building with the SDK?
- Which features are most useful to you?
- What's missing that would make it more valuable?

Just reply with your thoughts - even a quick one-liner helps!

Also, if you have any questions about the API or SDK, I'm here to help.

Best,
Karl
Founder, OilPriceAPI
karl@oilpriceapi.com
```

**Why this works:**
- Same as above
- Personal touch
- Founder reaching out directly (increases response rate)
- Offers help, not just asking for feedback

---

## Follow-up Strategy

### If They Respond:

**Scenario A: They describe their use case**
1. Thank them for sharing
2. Ask 1-2 clarifying questions
3. Offer specific help based on use case
4. Ask if they'd be interested in beta testing new features

**Scenario B: They have feature requests**
1. Add to GitHub issues
2. Ask about priority
3. Estimate timeline
4. Invite them to track progress

**Scenario C: They're having problems**
1. Jump on call immediately to help
2. Fix any bugs they found
3. Follow up to ensure resolution
4. Ask for feedback on fix

### If They Don't Respond (After 1 Week):

**Follow-up email:**
```
Subject: Re: Quick question about your use of OilPriceAPI Python SDK

Hi [Name],

Just following up on my email below - totally understand if you're busy!

I'm gathering feedback from early SDK users to prioritize what to build next. Even a quick 1-sentence reply about what you're using it for would be super helpful.

Thanks!
Karl
```

**Send:** 7 days after initial email
**Max follow-ups:** 1 (don't be pushy)

---

## Research Before Sending

### Bracco (braccobaldojp@yahoo.it)

**Email domain:** yahoo.it (personal email)
**Name:** Bracco (Italian name)
**Likely location:** Italy

**Pre-send research:**
1. Search LinkedIn: "Bracco Italy Python"
2. Search GitHub: braccobaldojp
3. Check if company email exists

**Hypothesis:** Individual developer or researcher

### Stevan Jokic (jokicstevan@gmail.com)

**Email domain:** gmail.com (personal email)
**Name:** Stevan Jokic (Serbian/Croatian name)
**Likely location:** Serbia, Croatia, or diaspora

**Pre-send research:**
1. Search LinkedIn: "Stevan Jokic Python"
2. Search GitHub: jokicstevan or stevan-jokic
3. Check if company affiliation

**Hypothesis:** Individual developer, possibly building trading bot or analysis tool

---

## Expected Responses

### Optimistic Scenario (75% response rate):
- 2 responses out of 2 emails
- 1-2 willing to have call
- Learn 2 different use cases
- Get 2-3 feature requests

### Realistic Scenario (50% response rate):
- 1 response out of 2 emails
- Learn 1 use case
- Get 1-2 feature requests
- Build relationship with 1 user

### Pessimistic Scenario (25% response rate):
- 0-1 responses
- Limited feedback
- Try different outreach method

---

## What to Do With Responses

### 1. Document Use Cases

Create file: `SDK_USER_PERSONAS.md`

**Template for each user:**
```markdown
## Persona: [Name]

**Use Case:** [What they're building]
**Industry:** [Energy, Finance, Research, etc.]
**Pain Points:** [What they struggle with]
**Feature Requests:** [What they need]
**Willing to Pay:** [Yes/No/Maybe]
**TAM Opportunity:** [Similar companies/individuals]
```

### 2. Prioritize Features

Based on responses, rank features by:
1. Number of users requesting
2. Impact on TAM
3. Development effort
4. Strategic value

### 3. Build Roadmap

Example:
```markdown
## Q1 2026 Roadmap (Based on User Feedback)

**User-Requested Features:**
1. Bulk historical download (Requested by: Bracco, Stevan)
2. Pandas DataFrame integration (Requested by: Stevan)
3. Caching layer (Requested by: Bracco)

**Priority:** Build #1 first (most requested)
**Timeline:** Ship in 2 weeks
**Beta testers:** Bracco, Stevan
```

### 4. Close the Loop

After building requested feature:
```
Subject: We built the feature you requested!

Hi [Name],

Remember when you mentioned needing [feature]? We just shipped it!

Here's how to use it:
[code example]

Would love your feedback on whether this solves your use case.

Thanks for helping make the SDK better!

Karl
```

---

## Sending the Emails

### Option 1: Manual (Recommended for 2 emails)

**From:** karl@oilpriceapi.com
**When:** Tomorrow (Nov 26) morning
**Tool:** Gmail/Email client

**Steps:**
1. Open email client
2. Compose new email to braccobaldojp@yahoo.it
3. Copy/paste subject and body from above
4. Send
5. Repeat for jokicstevan@gmail.com

### Option 2: Track in CRM

If you want to track responses:
1. Add both to HubSpot/Salesforce/Notion
2. Tag as "SDK Early Adopter"
3. Set reminder for 1-week follow-up
4. Track response and use case

---

## Success Metrics

**Goal:** Understand use cases to inform product roadmap

**Success = Any of these outcomes:**
- ✅ Learn 1+ use case
- ✅ Identify 1+ TAM opportunity
- ✅ Get 1+ feature request
- ✅ Build relationship with 1+ user
- ✅ Convert 1+ user to paid plan

**Measurement:**
- Response rate: X/2 (target: 50%+)
- Use cases discovered: X (target: 1+)
- Features requested: X (target: 2+)
- Paid conversions: X (target: 0-1)

---

## Next Actions

### This Week (Before Saturday):

1. ✅ **Research users on LinkedIn/GitHub** (30 min)
   - Find Bracco's profile
   - Find Stevan's profile
   - Identify companies/projects

2. ✅ **Send emails** (15 min)
   - Send to braccobaldojp@yahoo.it
   - Send to jokicstevan@gmail.com

3. ⏳ **Monitor responses** (ongoing)
   - Check email 2x/day
   - Respond within 2 hours

### Next Week (After Responses):

4. ⏳ **Have calls** (if they agree) (1-2 hours)
   - 15-20 min per call
   - Take notes on use cases
   - Ask about pain points

5. ⏳ **Create personas** (1 hour)
   - Document use cases
   - Identify TAM opportunities
   - Prioritize features

6. ⏳ **Update roadmap** (30 min)
   - Rank features by demand
   - Estimate effort
   - Set timeline

---

## Email Templates for Different Scenarios

### If They're a Company (Not Individual):

```
Subject: Quick question about your team's use of OilPriceAPI Python SDK

Hi [Name],

I noticed your team at [Company] has been using the OilPriceAPI Python SDK.

I'm Karl, the founder of OilPriceAPI. I'd love to understand:
- What use case are you solving?
- Is the SDK working well for your team?
- What would make it more valuable?

Happy to jump on a quick call or just reply here. Either way, I'm here to help ensure the SDK meets your needs.

Best,
Karl
```

### If They're Academic/Researcher:

```
Subject: Research using OilPriceAPI Python SDK?

Hi [Name],

I noticed you've been using the OilPriceAPI Python SDK - are you working on research in energy economics or commodities?

I'm Karl, the founder. I'd love to:
- Understand your research area
- Ensure the SDK supports your needs
- Potentially feature your work (with permission)

Academic pricing is also available if budget is a constraint.

Best,
Karl
```

### If They're Building a Product:

```
Subject: Building something cool with OilPriceAPI Python SDK?

Hi [Name],

I noticed you've been using the OilPriceAPI Python SDK - looks like you might be building something interesting!

I'm Karl, the founder. I'd love to:
- Learn about what you're building
- Make sure the SDK supports your use case
- Potentially feature you as a user story

No pressure - just genuinely curious what people are creating with the API!

Best,
Karl
```

---

**Status:** Ready to send emails
**Timeline:** Send tomorrow (Nov 26)
**Expected responses:** 1-2 within 3-7 days
**Follow-up:** 1 week if no response
