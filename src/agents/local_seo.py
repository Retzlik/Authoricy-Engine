"""
Local SEO Agent (Conditional)

Analyzes local SEO factors when local signals are detected:
- Google Business Profile optimization
- Citation analysis and NAP consistency
- Local keyword opportunity identification
- Review management strategy
- Local pack ranking factors
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class LocalSEOAgent(BaseAgent):
    """
    Local SEO Agent - Optimizes local search presence (conditional).

    Responsibilities:
    - Audit Google Business Profile completeness and optimization
    - Analyze NAP (Name, Address, Phone) consistency across citations
    - Identify local keyword opportunities
    - Assess local pack ranking factors
    - Recommend review acquisition strategies
    - Map local competitor presence

    Activation: Only runs when local signals are detected (GBP, local keywords).
    """

    @property
    def name(self) -> str:
        return "local_seo"

    @property
    def display_name(self) -> str:
        return "Local SEO Agent"

    @property
    def description(self) -> str:
        return "Analyzes local SEO factors including GBP, citations, and local rankings"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",  # Domain overview, GBP data
            "phase2_keywords",    # Keywords including local terms
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "gbp_analysis", "required": True},
                {"type": "citation_analysis", "required": True},
                {"type": "local_keyword_opportunities", "required": True},
                {"type": "review_analysis", "required": False},
                {"type": "competitor_local_presence", "required": False},
            ],
            "recommendations": [
                {"type": "gbp_optimization", "required": True},
                {"type": "citation_building", "required": True},
                {"type": "local_content", "required": True},
                {"type": "review_strategy", "required": False},
            ],
            "metrics": {
                "local_visibility_score": "float",
                "gbp_completeness_score": "float",
                "nap_consistency_score": "float",
                "review_score": "float",
                "local_pack_presence": "float",
                "citation_count": "int",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Local SEO Expert with 10 years of experience optimizing local businesses across multiple verticals (legal, medical, home services, retail). You've managed Google Business Profiles for franchises with 500+ locations and helped single-location businesses dominate their local markets.

Your expertise spans GBP optimization, citation management, review strategy, and local content creation. You understand the nuances of local pack ranking factors and how they interact with organic rankings.

<behavioral_constraints>
You NEVER say:
- "Optimize your GBP" (without specific fields and content to add)
- "Build more citations" (without listing specific directories and priority)
- "Get more reviews" (without a specific acquisition strategy)
- "Create local content" (without specific topics and keywords)
- "Improve local visibility" (without specific ranking factors to address)

You ALWAYS:
- Audit specific GBP fields with completion status
- List exact citation sources to build (with DA and relevance)
- Analyze competitor GBP profiles for gaps
- Provide specific review response templates
- Recommend exact local keywords with search volume
- Include NAP format specifications
</behavioral_constraints>

<gbp_optimization_framework>
GBP Completeness Checklist (% weight):
1. Business Name (5%) - Exact match, no keyword stuffing
2. Primary Category (15%) - Most specific relevant category
3. Secondary Categories (10%) - Up to 9 additional categories
4. Address (10%) - Full street address, verified
5. Phone Number (5%) - Local number preferred
6. Website (5%) - Tracking parameters recommended
7. Hours (5%) - Regular + special hours
8. Business Description (10%) - 750 chars, keywords natural
9. Products/Services (10%) - Complete catalog
10. Photos (10%) - 10+ high-quality, geotagged
11. Posts (5%) - Weekly updates minimum
12. Q&A (5%) - Seed 10+ common questions
13. Reviews (5%) - Quantity, recency, responses

Local Pack Ranking Factors:
- Relevance (category/keyword match)
- Distance (proximity to searcher)
- Prominence (reviews, citations, links)
</gbp_optimization_framework>

<citation_building_priorities>
Tier 1 (Must-Have):
- Google Business Profile
- Apple Maps
- Bing Places
- Yelp
- Facebook Business

Tier 2 (Important):
- Industry-specific directories
- Chamber of Commerce
- BBB
- Yellow Pages
- Foursquare

Tier 3 (Nice-to-Have):
- Local news/blogs
- Local event sponsors
- Community organization sites
- Niche directories

NAP Consistency Rules:
- Business name must be EXACTLY the same everywhere
- Address format must be consistent (St. vs Street, etc.)
- Phone number format must match (with/without area code)
- Track variations and consolidate
</citation_building_priorities>

<review_strategy>
Review Acquisition Best Practices:
1. Request timing: 24-48 hours after service completion
2. Request method: Email with direct link preferred
3. Response time: Within 24 hours for all reviews
4. Response tone: Professional, personalized, not templated
5. Negative review handling: Acknowledge, apologize, take offline

Review Response Templates:
- Positive: Thank by name, mention specific service, invite return
- Neutral: Thank, address concerns, offer resolution
- Negative: Apologize, take responsibility, provide contact
</review_strategy>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific local SEO finding</title>
<description>Detailed analysis with data</description>
<evidence>GBP data, citation counts, review metrics</evidence>
<impact>Impact on local visibility and rankings</impact>
</finding>

<recommendation priority="N">
<action>Specific local SEO action</action>
<location>GBP / Citations / Website / etc.</location>
<current_state>What exists now</current_state>
<target_state>What should exist</target_state>
<implementation>
<step>Step-by-step instructions</step>
<example>Specific content or format to use</example>
</implementation>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<timeline>Implementation timeline</timeline>
<success_metrics>
<metric>How to measure success</metric>
</success_metrics>
<owner>Marketing / Owner / Agency</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every local SEO recommendation must include:
1. Specific GBP field or citation source
2. Current state vs recommended state
3. Exact content to add (not generic suggestions)
4. Competitor comparison for context
5. Expected impact on local visibility
6. Monitoring approach
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# LOCAL SEO ANALYSIS

## BUSINESS CONTEXT
- Domain: {domain}
- Market: {market}
- Business Type: {business_type}
- Service Areas: {service_areas}

## LOCAL SEO DATA

### Phase 1 Data (Domain & GBP Information)
{phase1_foundation_json}

### Phase 2 Data (Keywords Including Local Terms)
{phase2_keywords_json}

---

## YOUR TASK

Analyze this data and provide:

### 1. GOOGLE BUSINESS PROFILE AUDIT
Evaluate GBP completeness:
- Profile completion score (0-100%)
- Missing required fields
- Optimization opportunities
- Category analysis (primary + secondary)
- Photo/media assessment
- Post activity evaluation
- Q&A section analysis

### 2. NAP CONSISTENCY ANALYSIS
Check name/address/phone consistency:
- Current NAP format
- Variations found across web
- Inconsistencies to fix
- Priority corrections

### 3. CITATION ANALYSIS
Assess citation presence:
- Tier 1 citation presence (must-have directories)
- Tier 2 citation gaps
- Industry-specific directories
- Competitor citation comparison

### 4. LOCAL KEYWORD OPPORTUNITIES
Identify local search terms:
- "[service] near me" keywords
- "[service] in [city]" keywords
- Local intent modifiers
- Search volume by service area
- Current rankings vs opportunities

### 5. REVIEW ANALYSIS
Evaluate review profile:
- Review count vs competitors
- Average rating
- Review velocity (reviews per month)
- Response rate and quality
- Sentiment analysis
- Platform distribution (Google, Yelp, Facebook)

### 6. LOCAL PACK PRESENCE
Analyze map pack rankings:
- Keywords triggering local pack
- Current local pack positions
- Competitor local pack presence
- Factors affecting local rankings

### 7. COMPETITOR LOCAL ANALYSIS
Compare to local competitors:
- GBP completeness comparison
- Review count and rating comparison
- Citation count comparison
- Local content comparison

### 8. PRIORITIZED RECOMMENDATIONS
For each recommendation:
- Specific action (not generic advice)
- Exact content or changes to implement
- Expected impact on local visibility
- Timeline and effort required

Remember: Be SPECIFIC about GBP fields. List ACTUAL citation sources. Provide EXACT content recommendations.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare local SEO-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        phase1 = data.get("phase1_foundation", {})
        phase2 = data.get("phase2_keywords", {})

        # Extract business-specific info
        domain_overview = phase1.get("domain_overview", {})
        result["business_type"] = domain_overview.get("business_type", "Unknown")
        result["service_areas"] = ", ".join(domain_overview.get("service_areas", ["Not specified"]))

        # Prepare GBP and local data
        if phase1:
            truncated_phase1 = {
                "domain_overview": domain_overview,
                "google_business_profile": phase1.get("google_business_profile", {}),
                "citations": phase1.get("citations", [])[:30],
                "local_competitors": phase1.get("local_competitors", [])[:10],
            }
            result["phase1_foundation_json"] = json.dumps(truncated_phase1, indent=2, default=str)

        if phase2:
            # Filter for local keywords
            all_keywords = phase2.get("ranked_keywords", [])
            local_keywords = [
                kw for kw in all_keywords
                if any(term in str(kw).lower() for term in ["near me", "local", "nearby", "in my area"])
            ][:50]

            truncated_phase2 = {
                "local_keywords": local_keywords,
                "all_keywords_sample": all_keywords[:50],
                "local_intent_keywords": phase2.get("local_intent_keywords", [])[:30],
            }
            result["phase2_keywords_json"] = json.dumps(truncated_phase2, indent=2, default=str)

        return result

    @staticmethod
    def should_activate(collected_data: Dict[str, Any]) -> bool:
        """
        Determine if local SEO analysis is needed.

        Checks for local signals:
        - Presence of Google Business Profile
        - Local keywords in ranking data
        - Physical address in domain data
        - Local intent keywords

        Returns:
            True if local signals detected, False otherwise
        """
        phase1 = collected_data.get("phase1_foundation", {})
        phase2 = collected_data.get("phase2_keywords", {})

        domain_overview = phase1.get("domain_overview", {})

        # Check for GBP presence
        has_gbp = bool(phase1.get("google_business_profile")) or bool(domain_overview.get("google_business_profile"))

        # Check for physical address
        has_address = bool(domain_overview.get("address")) or bool(domain_overview.get("physical_location"))

        # Check for local keywords
        keywords = phase2.get("ranked_keywords", [])[:100]
        local_terms = ["near me", "near by", "nearby", "local", "in my area", "[city]", "closest"]
        has_local_keywords = any(
            any(term in str(kw).lower() for term in local_terms)
            for kw in keywords
        )

        # Check for service area indicators
        has_service_area = bool(domain_overview.get("service_areas"))

        # Activate if any strong local signal
        return has_gbp or has_local_keywords or (has_address and has_service_area)
