"""
SERP Analysis Agent

Analyzes SERP features and content format requirements:
- SERP feature distribution analysis
- Featured snippet opportunities
- Content format analysis
- Competitor SERP performance
- Rich result opportunities
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class SERPAnalysisAgent(BaseAgent):
    """
    SERP Analysis Agent - Optimizes for SERP features.

    Responsibilities:
    - Analyze SERP feature distribution for target keywords
    - Identify featured snippet opportunities
    - Determine winning content formats per keyword group
    - Recommend content structure for SERP success
    - Track competitor SERP feature ownership
    """

    @property
    def name(self) -> str:
        return "serp_analysis"

    @property
    def display_name(self) -> str:
        return "SERP Analysis Agent"

    @property
    def description(self) -> str:
        return "Analyzes SERP features, content formats, and identifies opportunities"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase2_keywords",     # Keywords with SERP data
            "phase4_ai_technical", # Live SERP data
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "serp_feature_distribution", "required": True},
                {"type": "content_format_analysis", "required": True},
                {"type": "featured_snippet_opportunities", "required": True},
                {"type": "competitor_serp_presence", "required": False},
            ],
            "recommendations": [
                {"type": "featured_snippet_target", "required": True},
                {"type": "content_format", "required": True},
                {"type": "rich_result_optimization", "required": False},
            ],
            "metrics": {
                "serp_feature_opportunity_score": "float",
                "featured_snippet_opportunities": "int",
                "people_also_ask_opportunities": "int",
                "current_feature_ownership": "float",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a SERP Features Specialist with expertise in featured snippet optimization and content format strategy. You've helped sites capture featured snippets, People Also Ask boxes, and other SERP features for competitive keywords.

Your analysis reveals the content formats and structures that win SERP real estate for specific keyword categories.

<behavioral_constraints>
You NEVER say:
- "Target featured snippets" (without specific keywords and format recommendations)
- "Optimize content structure" (without exact format specifications)
- "Create comprehensive content" (without specific word counts and elements)
- "Improve SERP visibility" (without feature-specific tactics)

You ALWAYS:
- Identify specific keywords with SERP feature opportunities
- Analyze the current featured snippet holder and their format
- Recommend exact content formats (list, table, paragraph, etc.)
- Provide specific word counts and structural elements
- Calculate win probability based on current competition
- Include competitor SERP feature analysis
</behavioral_constraints>

<serp_features_reference>
Common SERP Features and Win Strategies:

Featured Snippet Types:
- Paragraph: 40-60 word direct answer, definition-style
- List: 5-8 items with clear headers
- Table: Comparison or data tables
- Video: Step-by-step tutorials

People Also Ask (PAA):
- Question-style headers
- 40-50 word concise answers
- Follow-up questions addressed

Image Pack:
- Optimized images with descriptive alt text
- Infographics for how-to queries
- Product images for commercial queries

Local Pack:
- GBP optimization
- NAP consistency
- Reviews and ratings
</serp_features_reference>

<content_format_analysis>
Analyze winning content by:
1. Content length (word count)
2. Header structure (H2/H3 distribution)
3. Media usage (images, videos, tables)
4. List vs prose ratio
5. FAQ presence
6. Schema markup usage
</content_format_analysis>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific SERP feature finding</title>
<description>Detailed analysis with data</description>
<evidence>SERP feature data, competitor analysis</evidence>
<impact>Traffic/visibility impact</impact>
</finding>

<recommendation priority="N">
<action>Specific SERP optimization action</action>
<keyword>Target keyword</keyword>
<serp_feature>Featured snippet / PAA / Image pack / etc.</serp_feature>
<current_holder>Who currently owns this feature</current_holder>
<content_requirements>
<format>Paragraph / List / Table</format>
<word_count>Optimal word count</word_count>
<structure>Required structural elements</structure>
<example>Example of winning format</example>
</content_requirements>
<target_url>Page to optimize or create</target_url>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<win_probability>Estimated % chance to capture feature</win_probability>
<timeline>Implementation timeline</timeline>
<success_metrics>
<metric>How to measure success</metric>
</success_metrics>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every SERP recommendation must include:
1. Specific keyword and current SERP feature status
2. Current feature holder analysis
3. Exact content format requirements
4. Word count and structure specifications
5. Win probability assessment
6. Before/after content example
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# SERP ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Organic Traffic: {organic_traffic}

## SERP DATA

### Phase 2 Data (Keywords & SERP Features)
{phase2_keywords_json}

### Phase 4 Data (Live SERP Data)
{phase4_ai_technical_json}

---

## YOUR TASK

Analyze SERP features and provide:

### 1. SERP FEATURE DISTRIBUTION
For target keywords, analyze:
- Featured snippet presence (% of keywords)
- People Also Ask presence
- Image pack presence
- Video carousel presence
- Local pack presence
- Knowledge panel presence

### 2. CURRENT FEATURE OWNERSHIP
What SERP features does this domain currently own?
- Featured snippets captured
- PAA questions answered
- Image pack appearances
- Compare to competitors

### 3. FEATURED SNIPPET OPPORTUNITIES
High-value snippets to target:
- Keyword
- Search volume
- Current snippet holder
- Snippet type (paragraph/list/table)
- Content gap to close
- Win probability

### 4. CONTENT FORMAT ANALYSIS
For major keyword groups, analyze what wins:
- Average word count of top 10
- Common content formats
- Header structures used
- Media elements present
- Schema types implemented

### 5. PEOPLE ALSO ASK OPPORTUNITIES
Questions you should answer:
- PAA questions for target keywords
- Current sources being cited
- Your relevant pages (if any)
- Content to create/update

### 6. CONTENT FORMAT RECOMMENDATIONS
For each opportunity:
- Target keyword
- Recommended content format
- Specific word count
- Required elements (lists, tables, images)
- Example structure
- Win probability

Remember: Be SPECIFIC about formats. Provide EXACT word counts. Analyze ACTUAL competitors.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare SERP-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        phase2 = data.get("phase2_keywords", {})
        phase4 = data.get("phase4_ai_technical", {})

        if phase2:
            truncated_phase2 = {
                "ranked_keywords": phase2.get("ranked_keywords", [])[:100],
                "serp_features": phase2.get("serp_features", {}),
                "featured_snippets": phase2.get("featured_snippets", [])[:20],
            }
            result["phase2_keywords_json"] = json.dumps(truncated_phase2, indent=2, default=str)

        if phase4:
            truncated_phase4 = {
                "live_serp_data": phase4.get("live_serp_data", [])[:30],
                "serp_competitor_data": phase4.get("serp_competitor_data", [])[:20],
            }
            result["phase4_ai_technical_json"] = json.dumps(truncated_phase4, indent=2, default=str)

        return result
