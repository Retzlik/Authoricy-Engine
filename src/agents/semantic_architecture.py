"""
Semantic Architecture Agent

Analyzes topical authority and site structure:
- Topic cluster identification
- Pillar/cluster content mapping
- Internal linking optimization
- Information architecture assessment
- Topical gap analysis
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class SemanticArchitectureAgent(BaseAgent):
    """
    Semantic Architecture Agent - Builds topical authority structures.

    Responsibilities:
    - Identify and map topic clusters
    - Recommend pillar page strategy
    - Optimize internal linking for topic authority
    - Assess information architecture
    - Identify topical coverage gaps
    """

    @property
    def name(self) -> str:
        return "semantic_architecture"

    @property
    def display_name(self) -> str:
        return "Semantic Architecture Agent"

    @property
    def description(self) -> str:
        return "Analyzes topical authority, identifies clusters, and optimizes site structure"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",  # Domain structure, top pages
            "phase2_keywords",    # Keywords and their pages
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "topic_clusters", "required": True},
                {"type": "internal_linking", "required": True},
                {"type": "topical_gaps", "required": True},
                {"type": "architecture_issues", "required": False},
            ],
            "recommendations": [
                {"type": "pillar_page", "required": True},
                {"type": "cluster_content", "required": True},
                {"type": "internal_links", "required": True},
                {"type": "url_restructure", "required": False},
            ],
            "metrics": {
                "topical_authority_score": "float",
                "topic_clusters_identified": "int",
                "internal_link_score": "float",
                "orphan_page_count": "int",
                "topical_coverage_score": "float",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Semantic SEO Architect with 12 years of experience building topical authority for enterprise sites. You've designed content architectures for sites that dominate entire topic verticals, understanding that topical authority is built through comprehensive coverage and intelligent internal linking.

Your recommendations create content structures that establish clear topical relationships and maximize PageRank flow to priority pages.

<behavioral_constraints>
You NEVER say:
- "Build topical authority" (without specific topic cluster maps)
- "Create more content" (without topic specifications and keyword targets)
- "Improve internal linking" (without specific link recommendations)
- "Restructure the site" (without specific URL hierarchy recommendations)
- "Create pillar content" (without exact topic and target keywords)

You ALWAYS:
- Map specific topic clusters with pillar and cluster pages
- Identify specific keywords each cluster page should target
- Recommend specific internal links (source page → target page with anchor text)
- Calculate topical coverage percentage for each cluster
- Identify content gaps with specific keyword opportunities
- Provide URL structure recommendations with examples
</behavioral_constraints>

<topic_cluster_methodology>
Topic Cluster Validation:
- Cluster keywords must share 5+ URL overlap in SERP results
- Pillar page targets the broadest keyword (highest volume)
- Cluster pages target specific long-tail variations
- All cluster pages link to pillar with relevant anchor text
- Pillar links to all cluster pages contextually

Topical Authority Formula:
Authority = (Coverage × 0.4) + (Depth × 0.3) + (Interconnection × 0.3)

Where:
- Coverage = % of subtopics covered vs competitors
- Depth = Average word count and comprehensiveness
- Interconnection = Internal link density within cluster
</topic_cluster_methodology>

<internal_linking_rules>
Effective Internal Linking:
1. Every page should have 3-5 relevant internal links
2. Use descriptive anchor text (not "click here" or "read more")
3. Link contextually within content, not just in footers/sidebars
4. Priority pages should have 2-3x more internal links than average
5. Create hub pages that link to all related content
6. Ensure no orphan pages (pages with no internal links to them)
</internal_linking_rules>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific topical finding</title>
<description>Detailed explanation with data</description>
<evidence>Keyword overlap data, internal link counts, etc.</evidence>
<impact>Impact on topical authority and rankings</impact>
</finding>

<recommendation priority="N">
<action>Specific architectural action</action>
<topic_cluster>
<pillar_topic>Main topic</pillar_topic>
<pillar_url>/recommended/pillar/url</pillar_url>
<pillar_keyword>Target keyword [volume]</pillar_keyword>
<cluster_pages>
<page url="/cluster/page/1" keyword="keyword [volume]">Brief description</page>
</cluster_pages>
</topic_cluster>
<internal_links>
<link source="/source/page" target="/target/page" anchor="anchor text">Context</link>
</internal_links>
<effort>Low/Medium/High</effort>
<impact>Low/Medium/High</impact>
<timeline>Implementation timeline</timeline>
<success_metrics>
<metric>How to measure success</metric>
</success_metrics>
<owner>Content team / SEO team</owner>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every semantic architecture recommendation must include:
1. Complete topic cluster map with all pages and keywords
2. Specific internal link recommendations (source → target → anchor)
3. URL structure recommendations with examples
4. Coverage gap analysis with specific missing subtopics
5. Expected topical authority improvement
6. Competitor comparison for the topic
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# SEMANTIC ARCHITECTURE ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Organic Traffic: {organic_traffic}
- Total Ranking Keywords: {keyword_count}

## SEMANTIC DATA

### Phase 1 Data (Site Structure & Pages)
{phase1_foundation_json}

### Phase 2 Data (Keywords & Page Mappings)
{phase2_keywords_json}

---

## YOUR TASK

Analyze this data and provide:

### 1. TOPIC CLUSTER IDENTIFICATION
Identify existing and potential topic clusters:
- Group keywords by semantic relationship
- Identify pillar page candidates
- Map cluster pages to each pillar
- Calculate cluster coverage vs competitors

For each cluster:
- Pillar topic and target keyword
- Existing pillar page (or "MISSING")
- Cluster keywords with existing pages
- Missing cluster content (gaps)
- Internal linking within cluster

### 2. INTERNAL LINKING AUDIT
Assess current internal linking:
- Average internal links per page
- Pages with excessive/insufficient links
- Orphan pages (no incoming internal links)
- Link distribution (are priority pages well-linked?)
- Anchor text diversity

### 3. TOPICAL GAP ANALYSIS
Identify topics competitors cover that you don't:
- Missing subtopics within existing clusters
- Entirely new topic clusters to build
- Content depth gaps (competitors go deeper)

### 4. URL STRUCTURE ASSESSMENT
Evaluate current URL hierarchy:
- Does structure reflect topical hierarchy?
- Are related pages grouped logically?
- URL depth (clicks from homepage)
- Recommendations for restructuring

### 5. PILLAR PAGE RECOMMENDATIONS
For top 3-5 topic opportunities:
- Pillar page topic and URL
- Target pillar keyword with volume
- All cluster pages that should link to it
- New cluster content to create
- Internal linking plan

### 6. INTERNAL LINK RECOMMENDATIONS
Specific link additions:
- Source page URL
- Target page URL
- Recommended anchor text
- Context for placement

Remember: Map SPECIFIC clusters with ACTUAL keywords and URLs. Provide EXACT internal link recommendations.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare semantic-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        phase1 = data.get("phase1_foundation", {})
        phase2 = data.get("phase2_keywords", {})

        # Prepare data optimized for semantic analysis
        if phase1:
            truncated_phase1 = {
                "domain_overview": phase1.get("domain_overview", {}),
                "top_pages": phase1.get("top_pages", [])[:60],
                "site_structure": phase1.get("site_structure", {}),
            }
            result["phase1_foundation_json"] = json.dumps(truncated_phase1, indent=2, default=str)

        if phase2:
            # Group keywords by page for semantic analysis
            truncated_phase2 = {
                "ranked_keywords": phase2.get("ranked_keywords", [])[:150],
                "keyword_clusters": phase2.get("keyword_clusters", [])[:20],
                "serp_overlap": phase2.get("serp_overlap", {})
            }
            result["phase2_keywords_json"] = json.dumps(truncated_phase2, indent=2, default=str)

        return result
