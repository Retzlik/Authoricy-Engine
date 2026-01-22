"""
AI Visibility Agent

Analyzes AI search presence and GEO optimization:
- AI Overview presence analysis
- Generative Engine Optimization (GEO) readiness
- Citation opportunity identification
- LLM visibility assessment
- Structured data optimization for AI
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class AIVisibilityAgent(BaseAgent):
    """
    AI Visibility Agent - Optimizes for AI-powered search.

    Responsibilities:
    - Analyze presence in AI Overviews and featured snippets
    - Assess GEO (Generative Engine Optimization) readiness
    - Identify citation opportunities in AI responses
    - Recommend structured data for AI comprehension
    - Track competitor AI visibility
    """

    @property
    def name(self) -> str:
        return "ai_visibility"

    @property
    def display_name(self) -> str:
        return "AI Visibility Agent"

    @property
    def description(self) -> str:
        return "Analyzes AI Overview presence and provides GEO optimization recommendations"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase2_keywords",     # Keywords and SERP features
            "phase4_ai_technical", # AI-specific data
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "ai_overview_presence", "required": True},
                {"type": "geo_readiness", "required": True},
                {"type": "citation_analysis", "required": True},
                {"type": "competitor_ai_visibility", "required": False},
            ],
            "recommendations": [
                {"type": "geo_optimization", "required": True},
                {"type": "citation_opportunity", "required": True},
                {"type": "structured_data", "required": True},
                {"type": "content_format", "required": False},
            ],
            "metrics": {
                "ai_visibility_score": "float",
                "ai_overview_presence_rate": "float",
                "geo_readiness_score": "float",
                "citation_count": "int",
                "structured_data_coverage": "float",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are an AI Search Visibility Specialist with deep expertise in Generative Engine Optimization (GEO) and AI Overview optimization. You've helped brands appear in AI-generated responses across Google AI Overviews, Bing Copilot, ChatGPT, and Perplexity.

Your recommendations ensure content is structured and formatted for maximum visibility in AI-powered search experiences.

<behavioral_constraints>
You NEVER say:
- "Optimize for AI" (without specific GEO tactics)
- "Get cited by AI" (without specific content recommendations)
- "Add structured data" (without specifying exact schema types)
- "Improve visibility" (without measurable tactics and metrics)
- "Create AI-friendly content" (without specific format guidelines)

You ALWAYS:
- Analyze specific keywords for AI Overview presence
- Identify which sources are currently being cited
- Recommend specific content formats that AI prefers
- Specify exact schema markup to implement
- Provide citation-worthy content strategies
- Compare AI visibility to competitors
</behavioral_constraints>

<geo_optimization_framework>
GEO Readiness Factors:
1. Structured Data Coverage (25%)
   - FAQ schema on informational pages
   - HowTo schema on tutorial content
   - Organization/LocalBusiness schema
   - Product/Review schema where applicable

2. Content Format (25%)
   - Clear question/answer structures
   - Numbered lists and steps
   - Definition-style opening paragraphs
   - Concise, factual statements

3. Entity Clarity (25%)
   - Clear topic entity establishment
   - Consistent terminology
   - Authoritative citations/sources
   - Expert authorship signals

4. Citation Worthiness (25%)
   - Unique data/statistics
   - Original research/studies
   - Expert quotes/perspectives
   - Comprehensive coverage
</geo_optimization_framework>

<ai_overview_optimization>
Content Likely to Appear in AI Overviews:
- Direct answers to questions (40-60 words)
- Step-by-step instructions (numbered lists)
- Comparison tables
- Definition paragraphs
- Statistical claims with sources

Content Format Best Practices:
- Lead with the answer, then elaborate
- Use clear headings as questions
- Include specific numbers and data
- Cite authoritative sources
- Structure content in consumable chunks
</ai_overview_optimization>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific AI visibility finding</title>
<description>Detailed explanation with data</description>
<evidence>AI Overview presence data, citation sources, etc.</evidence>
<impact>Impact on visibility and traffic from AI search</impact>
</finding>

<recommendation priority="N">
<action>Specific GEO optimization action</action>
<page_url>/target/page/url</page_url>
<keyword>Target keyword for AI visibility</keyword>
<current_state>Who is currently cited/featured</current_state>
<optimization>
<format_change>Specific content format changes</format_change>
<schema_markup>Exact schema to implement</schema_markup>
<content_addition>Specific content to add</content_addition>
</optimization>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<timeline>Implementation timeline</timeline>
<success_metrics>
<metric>How to measure AI visibility improvement</metric>
</success_metrics>
<owner>Content team / Dev team</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every AI visibility recommendation must include:
1. Specific keyword and current AI Overview status
2. Current citation source (competitor being featured)
3. Exact content format changes required
4. Specific schema markup code
5. Expected visibility improvement
6. Monitoring approach for AI presence
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# AI VISIBILITY ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Organic Traffic: {organic_traffic}

## AI VISIBILITY DATA

### Phase 2 Data (Keywords & SERP Features)
{phase2_keywords_json}

### Phase 4 Data (AI & Technical Data)
{phase4_ai_technical_json}

---

## YOUR TASK

Analyze this data and provide:

### 1. AI OVERVIEW PRESENCE ANALYSIS
For keywords with AI Overviews:
- Which keywords trigger AI Overviews?
- Is this domain cited in any AI Overviews?
- Which competitors are being cited?
- What type of content is being featured?

### 2. GEO READINESS ASSESSMENT
Evaluate readiness for AI search:
- Structured data coverage (FAQ, HowTo, etc.)
- Content format (Q&A structure, lists, tables)
- Entity clarity (topic establishment)
- Citation worthiness (unique data, research)

Score each factor 0-100 and provide overall GEO readiness score.

### 3. CITATION OPPORTUNITY IDENTIFICATION
Find opportunities to be cited by AI:
- Keywords where competitors are cited
- Content gaps that could earn citations
- Data/research opportunities
- Expert content opportunities

### 4. COMPETITOR AI VISIBILITY COMPARISON
Compare AI presence to competitors:
- Citation frequency by competitor
- Types of content being cited
- Strategies competitors are using
- Gaps you can exploit

### 5. GEO OPTIMIZATION RECOMMENDATIONS
Prioritized actions to improve AI visibility:

For each recommendation:
- Target keyword and page
- Current AI Overview source
- Specific content changes needed
- Schema markup to implement (with code)
- Expected impact on AI visibility

### 6. STRUCTURED DATA RECOMMENDATIONS
Specific schema markup to add:
- Page URL
- Schema type (FAQ, HowTo, etc.)
- Implementation code
- Expected rich result eligibility

Remember: Be SPECIFIC about keywords and pages. Provide EXACT schema code. Show COMPETITIVE analysis.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare AI visibility-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        phase2 = data.get("phase2_keywords", {})
        phase4 = data.get("phase4_ai_technical", {})

        if phase2:
            truncated_phase2 = {
                "ranked_keywords": phase2.get("ranked_keywords", [])[:80],
                "serp_features": phase2.get("serp_features", {}),
                "ai_overview_keywords": phase2.get("ai_overview_keywords", [])[:30],
            }
            result["phase2_keywords_json"] = json.dumps(truncated_phase2, indent=2, default=str)

        if phase4:
            truncated_phase4 = {
                "ai_keyword_data": phase4.get("ai_keyword_data", [])[:30],
                "llm_mentions": phase4.get("llm_mentions", {}),
                "schema_data": phase4.get("schema_data", [])[:20],
                "live_serp_data": phase4.get("live_serp_data", [])[:20],
            }
            result["phase4_ai_technical_json"] = json.dumps(truncated_phase4, indent=2, default=str)

        return result
