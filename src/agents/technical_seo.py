"""
Technical SEO Agent

Analyzes technical SEO health and Core Web Vitals:
- Core Web Vitals assessment (LCP, INP, CLS)
- Crawlability and indexation analysis
- Site architecture evaluation
- Schema markup assessment
- Mobile usability analysis
"""

import json
import logging
from typing import Dict, Any, List

from .base import BaseAgent

logger = logging.getLogger(__name__)


class TechnicalSEOAgent(BaseAgent):
    """
    Technical SEO Agent - Audits technical health and performance.

    Responsibilities:
    - Assess Core Web Vitals against 2025 thresholds
    - Identify crawlability and indexation issues
    - Analyze site architecture and URL structure
    - Evaluate schema markup implementation
    - Check mobile usability and responsiveness
    - Prioritize technical fixes by impact
    """

    @property
    def name(self) -> str:
        return "technical_seo"

    @property
    def display_name(self) -> str:
        return "Technical SEO Agent"

    @property
    def description(self) -> str:
        return "Audits technical SEO issues, Core Web Vitals, and site architecture"

    @property
    def required_data(self) -> List[str]:
        return [
            "phase1_foundation",     # Domain overview, technologies
            "phase4_ai_technical",   # Technical audits, lighthouse data
        ]

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"type": "core_web_vitals", "required": True},
                {"type": "crawl_issues", "required": True},
                {"type": "indexation", "required": True},
                {"type": "schema_markup", "required": False},
                {"type": "mobile_usability", "required": False},
            ],
            "recommendations": [
                {"type": "critical_fix", "required": True},
                {"type": "performance_optimization", "required": True},
                {"type": "architecture_improvement", "required": False},
            ],
            "metrics": {
                "technical_health_score": "float",
                "lcp_score": "float",
                "inp_score": "float",
                "cls_score": "float",
                "crawlability_score": "float",
                "mobile_usability_score": "float",
                "critical_issues_count": "int",
            },
        }

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Technical SEO Engineer with 10 years of experience at enterprise-level agencies and in-house teams (Merkle, Conductor, Shopify). You have audited sites with 1M+ pages and resolved complex technical issues for Fortune 500 companies.

Your technical recommendations must be specific, implementable, and prioritized by impact. You understand the difference between critical issues that block indexing and minor optimizations.

<behavioral_constraints>
You NEVER say:
- "Improve page speed" (without specific recommendations and expected improvement)
- "Fix technical issues" (without naming specific issues and affected URLs)
- "Optimize for mobile" (without specific mobile-related fixes)
- "Implement structured data" (without specifying which schema types and where)
- "Improve crawlability" (without specific crawl budget recommendations)

You ALWAYS:
- Reference specific metrics with thresholds (e.g., "LCP 3.2s exceeds 2.5s threshold")
- List affected URLs with issue counts
- Provide specific fix instructions with code examples where applicable
- Estimate impact of each fix (traffic lift, crawl efficiency, etc.)
- Assign priority levels (Critical/High/Medium/Low) based on SEO impact
- Include effort estimates (dev hours, dependencies)
</behavioral_constraints>

<core_web_vitals_thresholds_2025>
Good performance thresholds:
- LCP (Largest Contentful Paint): ≤2.5 seconds
- INP (Interaction to Next Paint): ≤200 milliseconds
- CLS (Cumulative Layout Shift): ≤0.1

Needs Improvement:
- LCP: 2.5s - 4.0s
- INP: 200ms - 500ms
- CLS: 0.1 - 0.25

Poor:
- LCP: >4.0s
- INP: >500ms
- CLS: >0.25
</core_web_vitals_thresholds_2025>

<issue_priority_framework>
CRITICAL (Fix within 24-48 hours):
- Robots.txt blocking important pages
- Noindex on important pages
- Site-wide 5xx errors
- Complete SSL/HTTPS issues
- Canonical loops or chains

HIGH (Fix within 1-2 weeks):
- Core Web Vitals failures affecting >30% of pages
- Broken internal links on key pages
- Missing or duplicate title tags on important pages
- Mobile usability errors
- Redirect chains >3 hops

MEDIUM (Fix within 1 month):
- Minor CWV improvements
- Schema markup gaps
- Image optimization
- URL structure inconsistencies
- Thin meta descriptions

LOW (Address when resources allow):
- Minor duplicate content
- Image alt text gaps
- Minor redirect optimizations
- Pagination improvements
</issue_priority_framework>

<output_format>
Structure your response using these XML tags:

<finding confidence="0.X" priority="N" category="category_name">
<title>Specific technical issue title</title>
<description>Detailed explanation with metrics and affected URLs</description>
<evidence>Specific data points (metrics, URL counts, error codes)</evidence>
<impact>SEO impact (crawl budget, indexing, rankings, UX)</impact>
</finding>

<recommendation priority="N">
<action>Specific technical fix with implementation details</action>
<rationale>Why this fix matters with expected impact</rationale>
<affected_urls>
<url count="N">/path/pattern/* - issue description</url>
</affected_urls>
<effort>Low/Medium/High + estimated dev hours</effort>
<impact>Low/Medium/High + expected improvement</impact>
<timeline>Specific implementation timeline</timeline>
<implementation>
<step>Step-by-step fix instructions</step>
<code>Code example if applicable</code>
</implementation>
<success_metrics>
<metric>How to verify the fix worked</metric>
</success_metrics>
<owner>Dev team / SEO team / DevOps</owner>
<dependencies>What must be done first</dependencies>
</recommendation>

<metric name="metric_name" value="X"/>
</output_format>

<quality_standard>
Every technical recommendation must include:
1. Specific issue with affected URL count/pattern
2. Current metric vs target threshold
3. Step-by-step fix instructions
4. Code snippet or configuration example (where applicable)
5. Expected improvement (quantified)
6. Dependencies and prerequisites
7. Verification method
</quality_standard>"""

    @property
    def analysis_prompt_template(self) -> str:
        return """# TECHNICAL SEO ANALYSIS

## DOMAIN CONTEXT
- Domain: {domain}
- Market: {market}
- Domain Rating: {domain_rank}
- Organic Traffic: {organic_traffic}
- Technologies Detected: {technologies}

## TECHNICAL DATA

### Phase 1 Data (Foundation - Domain Overview & Technologies)
{phase1_foundation_json}

### Phase 4 Data (Technical Audits & Performance)
{phase4_ai_technical_json}

---

## YOUR TASK

Analyze this technical data and provide:

### 1. CORE WEB VITALS ASSESSMENT
For each metric (LCP, INP, CLS):
- Current score vs 2025 threshold
- Percentage of pages passing/failing
- Primary causes of failures
- Specific fix recommendations with expected improvement

### 2. CRAWLABILITY ANALYSIS
- Robots.txt issues
- XML sitemap health
- Crawl budget efficiency
- Internal linking depth
- Orphan pages

### 3. INDEXATION AUDIT
- Indexed vs total pages
- Pages blocked from indexing (and whether intentional)
- Duplicate content issues
- Canonical tag implementation
- Noindex/nofollow usage

### 4. SITE ARCHITECTURE EVALUATION
- URL structure consistency
- Navigation depth (clicks from homepage)
- Internal link distribution
- Redirect chains and loops

### 5. SCHEMA MARKUP ASSESSMENT
- Current schema implementation
- Missing high-value schema types
- Schema errors or warnings
- Rich result eligibility

### 6. MOBILE USABILITY
- Mobile-friendly status
- Touch target sizing
- Viewport configuration
- Mobile-specific issues

### 7. PRIORITIZED RECOMMENDATIONS
Provide fixes in priority order:
- CRITICAL: Issues blocking indexing or causing site failures
- HIGH: Issues significantly impacting SEO performance
- MEDIUM: Optimization opportunities
- LOW: Nice-to-have improvements

For each recommendation:
- Specific URLs or URL patterns affected
- Current metric → target metric
- Step-by-step fix instructions
- Expected SEO impact
- Development effort estimate

Remember: Be SPECIFIC. Reference ACTUAL metrics and URLs. Provide IMPLEMENTABLE code examples. Prioritize by REAL impact.

Begin your analysis:"""

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare technical-specific data for the prompt."""
        result = super()._prepare_prompt_data(data)

        # Add technical-specific stats
        phase1 = data.get("phase1_foundation", {})
        phase4 = data.get("phase4_ai_technical", {})

        # Technologies
        technologies = phase1.get("technologies", [])
        if technologies:
            tech_names = [t.get("name", "") for t in technologies[:20]]
            result["technologies"] = ", ".join(tech_names)
        else:
            result["technologies"] = "Not detected"

        # Truncate large arrays for token management
        if phase4:
            truncated_phase4 = {
                "technical_audits": phase4.get("technical_audits", [])[:20],
                "lighthouse_data": phase4.get("lighthouse_data", {}),
                "core_web_vitals": phase4.get("core_web_vitals", {}),
                "crawl_stats": phase4.get("crawl_stats", {}),
                "schema_data": phase4.get("schema_data", [])[:10],
            }
            result["phase4_ai_technical_json"] = json.dumps(truncated_phase4, indent=2, default=str)

        return result
