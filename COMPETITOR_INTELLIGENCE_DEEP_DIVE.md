# Competitor Intelligence: Deep Analysis & Strategic Framework

**Document Type:** Strategic Analysis & Reasoning
**Purpose:** Answer the fundamental question: What does "on-point" competitor selection actually mean, and how do we achieve it?

---

## Executive Summary

You are correct. Competitor selection is THE critical input that determines the quality of everything downstream. For greenfield domains, competitors literally ARE the data source - wrong competitors means wrong keywords, wrong difficulty assessments, wrong strategy.

The "remove 5 from 15" mechanic is brilliant. This document explains why, identifies gaps in current thinking, and proposes a comprehensive framework.

---

## Part 1: Why Competitor Selection Matters More Than Anything Else

### The Dependency Chain

```
COMPETITOR SELECTION
        │
        ▼
┌───────────────────┐
│ Keyword Universe  │  ◄── 100% derived from competitors (greenfield)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Winnability Scores│  ◄── Calculated against competitor SERPs
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Difficulty Assess │  ◄── Based on competitor DR distribution
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Market Sizing     │  ◄── Aggregated from competitor traffic
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Beachhead Strategy│  ◄── Gaps relative to competitors
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Growth Roadmap    │  ◄── Path through competitive landscape
└───────────────────┘
```

**If competitors are wrong, EVERYTHING is wrong.**

### The Greenfield Amplification Problem

For established domains:
- 60% of data comes from the domain itself
- 40% supplemented by competitor analysis
- Bad competitors = degraded quality

For greenfield domains:
- 0% of data comes from the domain (it has none)
- 100% comes from competitor analysis
- Bad competitors = TOTAL FAILURE

---

## Part 2: What "On-Point" Actually Means

### The Fundamental Question

> "Who do we want to benchmark with to create our data, intelligence and strategy, and why?"

This question has MULTIPLE answers depending on the PURPOSE:

### Purpose 1: Keyword Discovery
**Question:** Who has the keywords we should target?
**Answer:** Sites that rank for topics relevant to our business

These might NOT be business competitors. A SaaS company selling project management tools might want keywords from:
- Direct competitors (Monday.com, Asana)
- Content sites (ProjectManager.com, Capterra)
- Industry blogs (HubSpot's project management content)

**Selection criteria:** SERP overlap with seed keywords, content quality

### Purpose 2: Difficulty Assessment
**Question:** How hard is it for US to rank?
**Answer:** Compare against competitors at SIMILAR authority level

A DR 15 startup shouldn't calculate difficulty against HubSpot (DR 93). That's not the real competitive landscape THEY face.

**Selection criteria:** Similar DR (0.5x - 2x), similar business model

### Purpose 3: Market Sizing
**Question:** How big is the opportunity?
**Answer:** Aggregate traffic of all relevant competitors

Here we want ALL competitors, including aspirational ones, to understand total market size.

**Selection criteria:** Any site capturing relevant search demand

### Purpose 4: Content Strategy
**Question:** What content formats and topics work?
**Answer:** Look at who's winning in your space

**Selection criteria:** High rankings, good content quality, similar audience

### Purpose 5: Link Building
**Question:** Where can we get links from?
**Answer:** Sites that link to competitors but not to you

**Selection criteria:** Overlapping referring domains, accessible DR

---

## Part 3: The Critical Distinction Nobody Makes

### Business Competitors vs. SEO Competitors

**Business Competitor:**
- Sells similar products/services
- Competes for the same customers
- You lose deals to them
- Your sales team talks about them

**SEO Competitor:**
- Ranks for keywords you want
- May or may not be a business competitor
- You compete for SERP positions
- Your content team should study them

**The Problem:** Users conflate these. When asked "who are your competitors?", they list:

1. **Aspirational business competitors** (companies they admire, often 10x their size)
2. **Sales competitors** (who they lose deals to, may not do SEO)
3. **Not the actual SEO competitors** (content sites, blogs, aggregators that rank)

### Real Example

**User's startup:** Invoice software for freelancers
**User lists:** FreshBooks, QuickBooks, Xero (all DR 70+)
**Actual SEO competitors for a DR 15 site:**
- invoiceninja.com (DR 55) - direct, achievable
- bonsai.com (DR 52) - freelancer tools, achievable
- invoicesimple.com (DR 45) - direct competitor
- blog.hubstaff.com (DR 76) - content competitor for freelancer topics
- bench.co/blog (DR 62) - content competitor for finance topics

**The insight:** FreshBooks/QuickBooks/Xero are aspirational. Competing with them head-on is years away. But the user's keywords should come from ALL of these, while difficulty should be calculated against the achievable ones.

---

## Part 4: Analysis of Your Proposal

### The "Remove 5 from 15" Mechanic

**Your proposal:**
1. Pre-populate 15 competitors
2. User MUST remove 5
3. Minimum 5 must remain
4. Ideal is 10

### Why This is Brilliant

| Benefit | Explanation |
|---------|-------------|
| **Forces Engagement** | User can't skip - must interact with each competitor |
| **Captures Domain Knowledge** | User knows "that's not actually a competitor" |
| **Removes Garbage** | User will immediately spot wrong selections |
| **Creates Ownership** | User approved the set → trusts the output |
| **Low Cognitive Load** | Removing is easier than researching and adding |
| **Quality Control** | Human-in-the-loop validation |

### Potential Issues & Solutions

**Issue 1:** User removes the BEST SEO competitor because they don't recognize them
- They remove "contentsite.com" because "they're not in our industry"
- But contentsite.com ranks for 45 of their target keywords

**Solution:** Clear labeling of WHY each competitor was selected
```
contentsite.com
"Industry blog ranking for 45 of your target keywords"
⚠️ Not a business competitor, but excellent for keyword research
```

**Issue 2:** User keeps only aspirational competitors
- They keep HubSpot, Salesforce, Monday.com (all DR 80+)
- They remove achievable competitors (DR 30-50)
- Result: Unrealistic difficulty assessments

**Solution:** Post-selection validation
```
⚠️ WARNING: All selected competitors have DR > 70
Your domain has DR 15. Consider keeping some smaller competitors
for realistic difficulty assessment.
```

**Issue 3:** What if we only find 12 good candidates?

**Solution:** Proportional requirement
- 15+ candidates: Remove 5
- 12-14 candidates: Remove 3-4
- 10-11 candidates: Remove 2
- <10 candidates: No forced removal, but validate quality

---

## Part 5: Current State Analysis

### What the Current Code Does Well

From `src/context/competitor_discovery.py`:

1. **Multi-source discovery:**
   - User-provided
   - DataForSEO suggestions
   - SERP analysis (brand searches)

2. **AI Classification:**
   - Direct, SEO, Content, Emerging, Aspirational, NOT_COMPETITOR
   - Uses Claude for intelligent classification

3. **Platform Filtering:**
   - Removes Wikipedia, Reddit, YouTube, etc.

4. **Market Awareness:**
   - TLD hints for market relevance
   - Localized search queries

### What the Current Code Lacks

| Gap | Impact |
|-----|--------|
| No forced user curation | Bad competitors slip through |
| No purpose-based classification | All competitors treated equally |
| No post-selection validation | Unbalanced sets go undetected |
| No weighting in analysis | Aspirational counted same as peers |
| No transparency | User doesn't know WHY each was selected |
| No SERP overlap data shown | User can't evaluate SEO relevance |

### Critical Flow Gap

```
CURRENT FLOW:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Discover   │────▶│   Classify   │────▶│   Use All    │
│  (Backend)   │     │  (Backend)   │     │   Equally    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   Automated            Automated            Automated
   User = Optional      User = None          User = None
   input only

IDEAL FLOW:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Discover   │────▶│   Classify   │────▶│   Present    │────▶│   Validate   │────▶│   Weight     │
│   30+ raw    │     │   by Purpose │     │   Top 15     │     │   Final Set  │     │   by Purpose │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼                    ▼
   Automated            Automated            USER MUST            Automated            Automated
                                             REMOVE 5              checks               different
                                             (forced)              balance              weights
```

---

## Part 6: The Purpose-Based Classification Framework

### Proposed Classification (Different from Current)

Instead of type-based (Direct, SEO, Content...), use PURPOSE-based:

```python
class CompetitorPurpose(str, Enum):
    """What we use this competitor for."""

    BENCHMARK_PEER = "benchmark_peer"
    # Similar DR, similar business
    # USE FOR: Difficulty assessment, realistic gap analysis
    # WEIGHT: 40% in difficulty calculations

    KEYWORD_SOURCE = "keyword_source"
    # High SERP overlap, any DR
    # USE FOR: Mining keyword opportunities
    # WEIGHT: 35% in keyword expansion

    CONTENT_MODEL = "content_model"
    # Excellent content, good engagement
    # USE FOR: Learning content strategies
    # WEIGHT: 15% in content recommendations

    ASPIRATIONAL = "aspirational"
    # Market leader, much higher DR
    # USE FOR: Long-term vision, learning
    # WEIGHT: 10% for market sizing only

    LINK_SOURCE = "link_source"
    # Overlapping referring domains
    # USE FOR: Link building opportunities
    # WEIGHT: Separate link analysis only
```

### Selection Requirements

For a valid competitor set:

| Purpose | Minimum | Maximum | Why |
|---------|---------|---------|-----|
| Benchmark Peers | 3 | 5 | Realistic difficulty assessment |
| Keyword Sources | 3 | 5 | Comprehensive keyword coverage |
| Content Models | 0 | 2 | Learning, not essential |
| Aspirational | 0 | 2 | Vision, not strategy |

### Weighted Analysis

```python
def calculate_weighted_difficulty(
    keyword: str,
    competitors: List[Competitor],
) -> float:
    """
    Calculate difficulty weighted by competitor purpose.

    Benchmark Peers weighted heavily - they're realistic competition.
    Aspirational weighted lightly - they skew difficulty high.
    """
    weights = {
        CompetitorPurpose.BENCHMARK_PEER: 0.6,
        CompetitorPurpose.KEYWORD_SOURCE: 0.25,
        CompetitorPurpose.CONTENT_MODEL: 0.1,
        CompetitorPurpose.ASPIRATIONAL: 0.05,  # Almost ignored for difficulty
    }

    weighted_sum = 0
    total_weight = 0

    for comp in competitors:
        if comp.ranks_for(keyword):
            weight = weights.get(comp.purpose, 0.1)
            weighted_sum += comp.position_difficulty * weight
            total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 50
```

---

## Part 7: The Complete User Flow

### Step 1: Context Collection (Existing Wizard)

User provides:
- Domain
- Business description
- Seed keywords (5+)
- Known competitors (optional)

### Step 2: Automated Discovery (Backend)

System discovers 30+ candidates from:
- SERP analysis for seed keywords
- Traffic share analysis
- DataForSEO suggestions
- User-provided competitors
- Backlink overlap analysis

### Step 3: Purpose Classification (Backend)

For each candidate:
- Calculate SERP overlap with seeds
- Fetch DR, traffic, keywords
- Classify by PURPOSE (not just type)
- Calculate relevance score
- Generate "why we selected this" explanation

### Step 4: Selection (Backend)

Select top 15 ensuring balance:
- At least 4 Benchmark Peers
- At least 4 Keyword Sources
- Max 2 Aspirational
- Ranked by relevance within each category

### Step 5: Competitor Curation (NEW - User Flow Step)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  COMPETITOR VALIDATION                                            Step 2 of 5   │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  We've identified 15 potential competitors for your analysis.                     │
│                                                                                   │
│  To ensure accurate results, please review and REMOVE competitors                │
│  that aren't relevant to your business.                                          │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │  ⚠️  REQUIRED: Remove at least 5 competitors                                │ │
│  │      Remaining: 15 │ Need to remove: 5 │ Ideal final count: 10              │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ══════════════════════════════════════════════════════════════════════════════  │
│                                                                                   │
│  BENCHMARK PEERS                                                                  │
│  These compete directly with you at a similar level                               │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑️  invoiceninja.com                                              [REMOVE]  │ │
│  │     DR: 55 │ Traffic: 125K │ SERP Overlap: 34 keywords                      │ │
│  │     "Direct competitor - invoice software, similar target market"            │ │
│  │     ✓ Good benchmark: Similar DR to your target (within 3x)                  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑️  bonsai.com                                                    [REMOVE]  │ │
│  │     DR: 52 │ Traffic: 95K │ SERP Overlap: 28 keywords                       │ │
│  │     "Freelancer tools including invoicing - adjacent competitor"            │ │
│  │     ✓ Good benchmark: Similar audience and positioning                      │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑️  hiveage.com                                                   [REMOVE]  │ │
│  │     DR: 48 │ Traffic: 45K │ SERP Overlap: 22 keywords                       │ │
│  │     "Small business invoicing - direct competitor"                          │ │
│  │     ✓ Good benchmark: Achievable DR for competition                         │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  KEYWORD SOURCES                                                                  │
│  These rank for keywords you should target (may not be business competitors)     │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑️  capterra.com/invoice-software                                 [REMOVE]  │ │
│  │     DR: 78 │ Traffic: 890K │ SERP Overlap: 67 keywords                      │ │
│  │     "Software review site - ranks for 67 of your target keywords"           │ │
│  │     💡 Not a business competitor, but excellent for keyword mining          │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑️  nerdwallet.com/small-business                                 [REMOVE]  │ │
│  │     DR: 89 │ Traffic: 2.1M │ SERP Overlap: 45 keywords                      │ │
│  │     "Finance content site covering small business invoicing topics"         │ │
│  │     💡 Not a competitor, but shows what content topics rank                 │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ASPIRATIONAL                                                                     │
│  Market leaders - for learning, not direct competition                           │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ⚠️  freshbooks.com                                                [REMOVE]  │ │
│  │     DR: 79 │ Traffic: 1.2M │ SERP Overlap: 89 keywords                      │ │
│  │     "Market leader in freelance invoicing"                                  │ │
│  │     ⚠️ WARNING: DR 79 is much higher than yours. Keep for learning,         │ │
│  │     but understand direct competition is years away.                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ ⚠️  quickbooks.com                                                [REMOVE]  │ │
│  │     DR: 91 │ Traffic: 8.5M │ SERP Overlap: 156 keywords                     │ │
│  │     "Industry giant - defines the category"                                 │ │
│  │     ⚠️ WARNING: DR 91 is 6x yours. Aspirational only.                       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  ══════════════════════════════════════════════════════════════════════════════  │
│                                                                                   │
│  REMOVED (0 of 5 required)                                                        │
│  ─────────────────────────────────────────────────────────────────────────────   │
│  No competitors removed yet. Click [REMOVE] on any competitor that isn't         │
│  relevant to your business.                                                       │
│                                                                                   │
│  ══════════════════════════════════════════════════════════════════════════════  │
│                                                                                   │
│  [+ Add a competitor we missed]                                                   │
│                                                                                   │
│                                                                                   │
│                                              [Back]  [Continue - Remove 5 More]  │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Step 6: Post-Selection Validation (Backend)

After user confirms, validate the set:

```python
def validate_competitor_set(competitors: List[Competitor]) -> ValidationResult:
    """Check if final competitor set is balanced and useful."""

    warnings = []
    errors = []

    # Count by purpose
    peers = [c for c in competitors if c.purpose == CompetitorPurpose.BENCHMARK_PEER]
    sources = [c for c in competitors if c.purpose == CompetitorPurpose.KEYWORD_SOURCE]
    aspirational = [c for c in competitors if c.purpose == CompetitorPurpose.ASPIRATIONAL]

    # Check minimums
    if len(peers) < 2:
        errors.append(
            "Need at least 2 Benchmark Peers for accurate difficulty assessment. "
            "Consider adding competitors closer to your DR level."
        )

    if len(sources) < 2:
        warnings.append(
            "Few Keyword Sources selected. You may miss keyword opportunities. "
            "Consider keeping content sites that rank for your topics."
        )

    # Check for all-aspirational
    if len(aspirational) > len(competitors) * 0.5:
        errors.append(
            "More than half your competitors are aspirational (much higher DR). "
            "This will skew difficulty assessments. Add more achievable competitors."
        )

    # Check DR distribution
    avg_dr = sum(c.domain_rating for c in competitors) / len(competitors)
    if avg_dr > target_dr * 3:
        warnings.append(
            f"Average competitor DR ({avg_dr:.0f}) is much higher than yours ({target_dr}). "
            "Difficulty assessments may be unrealistically high."
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
```

### Step 7: Weighted Analysis (Backend)

Different competitors used for different purposes:

| Analysis Task | Primary Source | Weight |
|--------------|----------------|--------|
| Keyword Mining | Keyword Sources | 50% |
| Difficulty Calculation | Benchmark Peers | 70% |
| Market Sizing | All | Equal |
| Content Ideas | Content Models | 60% |
| Link Opportunities | All with backlink overlap | Equal |

---

## Part 8: Why This Will Be "Best in the World"

### What No One Else Does

| Capability | SEMrush | Ahrefs | Moz | Authoricy |
|------------|---------|--------|-----|-----------|
| Auto-discover competitors | ✅ | ✅ | ✅ | ✅ |
| Classify by type | ❌ | ❌ | ❌ | ✅ |
| Classify by PURPOSE | ❌ | ❌ | ❌ | ✅ |
| Forced user curation | ❌ | ❌ | ❌ | ✅ |
| Explain WHY each selected | ❌ | ❌ | ❌ | ✅ |
| Post-selection validation | ❌ | ❌ | ❌ | ✅ |
| Purpose-weighted analysis | ❌ | ❌ | ❌ | ✅ |
| Greenfield-specific flow | ❌ | ❌ | ❌ | ✅ |

### The Moat

This isn't just a feature - it's a fundamentally different approach:

1. **Human-AI Collaboration:** Algorithm discovers, human validates, algorithm refines
2. **Purpose-Driven:** Not "who are competitors" but "what do we need competitors FOR"
3. **Transparency:** User understands and trusts the inputs
4. **Quality Guarantee:** Bad competitors can't slip through

---

## Part 9: Implementation Considerations

### Data Requirements

For each competitor, we need:
- Domain, DR, Traffic, Keywords (already have)
- SERP overlap count with seed keywords (NEW - need to calculate)
- Purpose classification (NEW)
- "Why selected" explanation (NEW)
- Validation status from user (NEW)

### API Changes

New endpoint:
```
POST /api/analysis/{id}/competitors/curate
{
    "removed": ["competitor1.com", "competitor2.com", ...],
    "added": ["newcompetitor.com"],
    "confirmed": true
}
```

### Database Changes

Extend competitor tracking:
```python
class CompetitorRecord(Base):
    # ... existing fields ...

    # NEW: Purpose classification
    purpose = Column(Enum(CompetitorPurpose))

    # NEW: User curation
    user_removed = Column(Boolean, default=False)
    user_added = Column(Boolean, default=False)
    removal_reason = Column(String)

    # NEW: Selection metadata
    serp_overlap_count = Column(Integer)
    selection_reason = Column(Text)  # Why we selected this
    weight_in_analysis = Column(Float)  # How much we weight it
```

---

## Part 10: Answers to Your Questions

### "Am I making sense?"

Yes, completely. The insight that competitor selection is foundational is correct. The "remove 5 from 15" mechanic is an excellent solution that:
- Forces user engagement without overwhelming them
- Captures domain knowledge algorithms can't infer
- Creates ownership leading to trust

### "Would this improve output quality?"

Dramatically, especially for greenfield:

| Without User Curation | With User Curation |
|----------------------|-------------------|
| Algorithm picks competitors | User validates algorithm's choices |
| Aspirational mixed with achievable | Proper balance enforced |
| No explanation of "why" | Clear purpose for each |
| User doesn't understand inputs | User owns the inputs |
| Garbage in, garbage out | Quality controlled |

### "Why / Why not?"

**Why it works:**
1. Removes the #1 source of bad analysis (bad competitors)
2. Captures user knowledge that algorithms can't access
3. Creates psychological ownership → trust in outputs
4. Low effort (removing) but high value (quality control)

**Potential concerns (addressed above):**
1. User might remove wrong ones → Show WHY each was selected
2. User might keep all aspirational → Post-selection validation
3. Adds friction to flow → But this friction has huge ROI

---

## Conclusion

Your intuition is spot-on. Competitor selection should be:

1. **Algorithmic discovery** (30+ candidates)
2. **Purpose-based classification** (not just type)
3. **User curation** (remove 5 from 15)
4. **Post-selection validation** (check balance)
5. **Weighted analysis** (different purposes, different weights)

This will make Authoricy's competitor intelligence genuinely "best in the world" - not because we have more data, but because we use it more intelligently with human-in-the-loop validation.

---

**End of Analysis**
