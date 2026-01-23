"""
External Report Builder - Lead Magnet (10-15 pages)

Generates executive-focused, sales-enabling PDF report.
Now uses REAL DATA from agent outputs, not placeholders.

v6: CONFIDENCE TRACKING - Makes missing data VISIBLE instead of silent fallbacks.

Structure:
1. Cover
2. Data Confidence Banner (if score < 80%)
3. Executive Summary (2 pages) - From Master Strategy Agent
4. Current Position (2 pages) - From Technical + Backlink Agents
5. Competitive Landscape (2 pages) - From SERP + Backlink Agents
6. The Opportunity (2 pages) - From Keyword Intelligence Agent
7. Authority & AI Visibility (1 page) - From AI Visibility Agent
8. 90-Day Roadmap (2 pages) - From Master Strategy Agent
9. Next Steps (1 page)
10. Methodology (1 page)
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
import html

from .confidence import ReportConfidence, data_missing_html

# Type hints for agent outputs (actual import would cause circular dependency issues)
if TYPE_CHECKING:
    from ..agents.base import AgentOutput, Finding, Recommendation

logger = logging.getLogger(__name__)


class ExternalReportBuilder:
    """
    Builds external report HTML for PDF generation.

    v6: Confidence tracking - makes missing data VISIBLE.
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.confidence = ReportConfidence()

    def build(
        self,
        analysis_result: Any,
        analysis_data: Dict[str, Any],
    ) -> Tuple[str, ReportConfidence]:
        """
        Build complete HTML for external report.

        Args:
            analysis_result: Analysis result from engine (contains agent_outputs dict)
            analysis_data: Original compiled data

        Returns:
            Tuple of (HTML document, ReportConfidence)
        """
        # Reset confidence tracking for this build
        self.confidence = ReportConfidence()

        metadata = analysis_data.get("metadata", {})
        domain = metadata.get("domain", "Unknown")
        market = metadata.get("market", "Unknown")

        # Extract agent outputs from analysis result
        agent_outputs = self._extract_agent_outputs(analysis_result)

        # Track if we have agent outputs at all
        self.confidence.track("agent_outputs", "global", "agent", bool(agent_outputs), required=True)

        # Build sections with real agent data
        sections = [
            self._build_cover(domain, market),
            self._build_executive_summary(agent_outputs, metadata),
            self._build_current_position(agent_outputs, analysis_data),
            self._build_competitive_landscape(agent_outputs, analysis_data),
            self._build_opportunity(agent_outputs, analysis_data),
            self._build_ai_visibility(agent_outputs, analysis_data),
            self._build_roadmap(agent_outputs),
            self._build_next_steps(domain),
            self._build_methodology(),
        ]

        # Add confidence warning banner after cover if score is low
        confidence_warning = self.confidence.generate_warning_html()
        if confidence_warning:
            sections.insert(1, f'<div class="page">{confidence_warning}</div>')

        # Log confidence report
        conf_data = self.confidence.to_dict()
        logger.info(
            f"Report confidence: {conf_data['confidence_level']} ({conf_data['confidence_score']:.0f}%), "
            f"fallbacks: {conf_data['fallback_count']}, missing: {len(conf_data['missing_required'])}"
        )
        if conf_data['missing_required']:
            logger.warning(f"Missing data: {conf_data['missing_required'][:5]}")

        # Combine into full document
        return self._wrap_html(sections, domain), self.confidence

    def _extract_agent_outputs(self, analysis_result: Any) -> Dict[str, Any]:
        """Extract agent outputs from analysis result."""
        if analysis_result is None:
            return {}

        # Handle both dict and object formats
        if isinstance(analysis_result, dict):
            return analysis_result.get("agent_outputs", {})
        elif hasattr(analysis_result, "agent_outputs"):
            return analysis_result.agent_outputs
        return {}

    def _get_agent(self, outputs: Dict[str, Any], name: str) -> Optional[Any]:
        """Safely get an agent output."""
        return outputs.get(name)

    def _wrap_html(self, sections: list, domain: str) -> str:
        """Wrap sections in full HTML document."""
        content = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(domain)} - SEO Analysis Report</title>
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    {content}
</body>
</html>"""

    def _get_styles(self) -> str:
        """Get CSS styles for the report."""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page) " / " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }

        .page {
            page-break-after: always;
            min-height: 100vh;
            padding: 20px 0;
        }

        .page:last-child {
            page-break-after: avoid;
        }

        .cover {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            min-height: 100vh;
        }

        .cover h1 {
            font-size: 32pt;
            color: #1a1a2e;
            margin-bottom: 10px;
        }

        .cover .subtitle {
            font-size: 14pt;
            color: #666;
            margin-bottom: 40px;
        }

        .cover .meta {
            font-size: 10pt;
            color: #888;
            margin-top: 60px;
        }

        h1 { font-size: 24pt; color: #1a1a2e; margin-bottom: 20px; }
        h2 { font-size: 18pt; color: #2d3436; margin: 25px 0 15px; }
        h3 { font-size: 14pt; color: #2d3436; margin: 20px 0 10px; }

        p { margin-bottom: 12px; }

        .highlight-box {
            background: #f8f9fa;
            border-left: 4px solid #4361ee;
            padding: 15px 20px;
            margin: 20px 0;
        }

        .highlight-box.warning {
            border-left-color: #f72585;
        }

        .highlight-box.success {
            border-left-color: #06d6a0;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }

        .metric-card {
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            border-radius: 8px;
        }

        .metric-card .value {
            font-size: 24pt;
            font-weight: bold;
            color: #4361ee;
        }

        .metric-card .label {
            font-size: 10pt;
            color: #666;
            margin-top: 5px;
        }

        .metric-card.warning .value {
            color: #f72585;
        }

        .metric-card.success .value {
            color: #06d6a0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10pt;
        }

        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2d3436;
        }

        tr:hover {
            background: #fafafa;
        }

        .finding {
            margin: 15px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
        }

        .finding-title {
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 8px;
        }

        .finding-evidence {
            font-size: 10pt;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }

        .finding-impact {
            font-size: 10pt;
            color: #4361ee;
            margin-top: 4px;
            font-weight: 500;
        }

        .priority-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: 600;
            margin-left: 8px;
        }

        .priority-1 { background: #f72585; color: white; }
        .priority-2 { background: #4361ee; color: white; }
        .priority-3 { background: #06d6a0; color: white; }

        .cta-box {
            background: #4361ee;
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px;
            margin: 30px 0;
        }

        .cta-box h3 {
            color: white;
            margin-bottom: 15px;
        }

        .logo {
            font-size: 14pt;
            font-weight: bold;
            color: #4361ee;
        }

        .confidential {
            font-size: 9pt;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .roadmap-phase {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .roadmap-phase h3 {
            color: #4361ee;
            margin-bottom: 10px;
        }

        .roadmap-item {
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }

        .roadmap-item:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #4361ee;
        }

        ul {
            margin: 10px 0;
            padding-left: 20px;
        }

        li {
            margin: 5px 0;
        }
        """

    def _build_cover(self, domain: str, market: str) -> str:
        """Build cover page."""
        date = datetime.now().strftime("%B %Y")
        return f"""
        <div class="page cover">
            <div class="logo">AUTHORICY</div>
            <h1>{html.escape(domain)}</h1>
            <div class="subtitle">Organic Visibility Analysis</div>
            <div class="meta">
                <p>Prepared exclusively for {html.escape(domain)}</p>
                <p>Market: {html.escape(market)}</p>
                <p>{date}</p>
            </div>
            <div class="confidential" style="margin-top: 60px;">Confidential</div>
        </div>
        """

    def _build_executive_summary(self, agent_outputs: Dict[str, Any], metadata: Dict) -> str:
        """
        Build executive summary from Master Strategy Agent output.

        v6: Tracks confidence and shows explicit warnings for missing data.
        """
        master = self._get_agent(agent_outputs, "master_strategy")

        # Track master agent presence
        has_master = self.confidence.track(
            "master_strategy_agent", "executive_summary", "agent", master
        )

        # Get headline metric - NO SILENT FALLBACK
        headline = None
        if master and hasattr(master, 'metrics') and master.metrics:
            if "headline_metric" in master.metrics:
                headline = master.metrics["headline_metric"]
            elif "total_opportunity_value" in master.metrics:
                value = master.metrics["total_opportunity_value"]
                headline = f"Estimated ${value:,.0f} annual opportunity in untapped organic traffic."

        # Track headline
        has_headline = self.confidence.track(
            "headline_metric", "executive_summary", "agent", headline
        )

        if not headline:
            # Show explicit warning instead of generic text
            self.confidence.track_fallback("headline_metric", "executive_summary", "generic")
            headline_html = data_missing_html("Headline Metric", "Executive Summary")
        else:
            headline_html = f"""
            <div class="highlight-box">
                <strong>The Headline:</strong><br>
                {html.escape(headline)}
            </div>
            """

        # Get top 3 findings from master agent
        findings_html = ""
        findings = []
        if master and hasattr(master, 'findings') and master.findings:
            findings = master.findings[:3]

        # Track findings
        has_findings = self.confidence.track(
            "key_findings", "executive_summary", "agent", findings
        )

        if findings:
            for i, finding in enumerate(findings, 1):
                title = self._get_finding_attr(finding, "title", f"Finding {i}")
                description = self._get_finding_attr(finding, "description", "")
                evidence = self._get_finding_attr(finding, "evidence", "")
                impact = self._get_finding_attr(finding, "impact", "")

                findings_html += f"""
                <div class="finding">
                    <div class="finding-title">{i}. {html.escape(title)}</div>
                    <p>{html.escape(description[:300])}</p>
                    {f'<div class="finding-evidence">Evidence: {html.escape(evidence[:150])}</div>' if evidence else ''}
                    {f'<div class="finding-impact">Impact: {html.escape(impact[:100])}</div>' if impact else ''}
                </div>
                """
        else:
            # Try fallback to other agents
            findings_html = self._build_fallback_findings(agent_outputs)
            if "DATA UNAVAILABLE" in findings_html or not findings_html.strip():
                self.confidence.track_fallback("key_findings", "executive_summary", "no findings")

        # Get top recommendation - NO SILENT FALLBACK
        recommendation_html = ""
        has_recommendation = False
        if master and hasattr(master, 'recommendations') and master.recommendations:
            rec = master.recommendations[0]
            action = self._get_rec_attr(rec, "action", "")
            impact = self._get_rec_attr(rec, "impact", "")
            timeline = self._get_rec_attr(rec, "timeline", "")

            if action:
                has_recommendation = True
                recommendation_html = f"""
                <p><strong>Primary Action:</strong> {html.escape(action)}</p>
                <p><strong>Expected Impact:</strong> {html.escape(impact)}</p>
                {f'<p><strong>Timeline:</strong> {html.escape(timeline)}</p>' if timeline else ''}
                """

        # Track recommendation
        self.confidence.track(
            "primary_recommendation", "executive_summary", "agent", has_recommendation
        )

        if not recommendation_html:
            self.confidence.track_fallback("primary_recommendation", "executive_summary", "generic")
            recommendation_html = data_missing_html("Primary Recommendation", "Executive Summary")

        return f"""
        <div class="page">
            <h1>Executive Summary</h1>

            {headline_html}

            <h2>Key Findings</h2>
            {findings_html}

            <h2>Recommended Path Forward</h2>
            {recommendation_html}
        </div>
        """

    def _build_fallback_findings(self, agent_outputs: Dict[str, Any]) -> str:
        """Build findings from individual agents if master isn't available."""
        findings_html = ""
        finding_num = 1

        # Technical SEO findings
        tech = self._get_agent(agent_outputs, "technical_seo")
        if tech and hasattr(tech, 'findings') and tech.findings:
            finding = tech.findings[0]
            title = self._get_finding_attr(finding, "title", "Technical Health")
            desc = self._get_finding_attr(finding, "description", "")
            if desc:  # Only add if we have actual content
                findings_html += f"""
                <div class="finding">
                    <div class="finding-title">{finding_num}. {html.escape(title)}</div>
                    <p>{html.escape(desc[:250])}</p>
                </div>
                """
                finding_num += 1

        # Keyword findings
        kw = self._get_agent(agent_outputs, "keyword_intelligence")
        if kw and hasattr(kw, 'findings') and kw.findings:
            finding = kw.findings[0]
            title = self._get_finding_attr(finding, "title", "Keyword Opportunity")
            desc = self._get_finding_attr(finding, "description", "")
            if desc:  # Only add if we have actual content
                findings_html += f"""
                <div class="finding">
                    <div class="finding-title">{finding_num}. {html.escape(title)}</div>
                    <p>{html.escape(desc[:250])}</p>
            </div>
            """
            finding_num += 1

        # Backlink findings
        bl = self._get_agent(agent_outputs, "backlink_intelligence")
        if bl and hasattr(bl, 'findings') and bl.findings:
            finding = bl.findings[0]
            title = self._get_finding_attr(finding, "title", "Link Profile")
            desc = self._get_finding_attr(finding, "description", "")
            if desc:  # Only add if we have actual content
                findings_html += f"""
                <div class="finding">
                    <div class="finding-title">{finding_num}. {html.escape(title)}</div>
                    <p>{html.escape(desc[:250])}</p>
                </div>
                """

        # NO GENERIC FALLBACK - show explicit data missing warning
        if not findings_html:
            findings_html = data_missing_html("Agent Findings", "Key Findings")

        return findings_html

    def _build_current_position(self, agent_outputs: Dict[str, Any], analysis_data: Dict) -> str:
        """
        Build current position from Technical + Backlink agents.
        """
        # Get data from analysis_data (raw metrics)
        summary = analysis_data.get("summary", {})
        phase1 = analysis_data.get("phase1_foundation", {})
        backlinks = phase1.get("backlink_summary", {})
        technical = phase1.get("technical_baseline", {})

        keywords = summary.get("total_organic_keywords") or 0
        traffic = summary.get("total_organic_traffic") or 0
        dr = backlinks.get("domain_rank") or 0
        rds = backlinks.get("referring_domains") or 0

        # Get agent-specific metrics
        tech_agent = self._get_agent(agent_outputs, "technical_seo")
        bl_agent = self._get_agent(agent_outputs, "backlink_intelligence")

        # Core Web Vitals from technical agent
        lcp = "N/A"
        inp = "N/A"
        cls = "N/A"
        tech_health = "N/A"

        if tech_agent and tech_agent.metrics:
            lcp = tech_agent.metrics.get("lcp_score", "N/A")
            inp = tech_agent.metrics.get("inp_score", "N/A")
            cls = tech_agent.metrics.get("cls_score", "N/A")
            tech_health = tech_agent.metrics.get("technical_health_score", "N/A")
            if isinstance(lcp, (int, float)):
                lcp = f"{lcp:.1f}s"
            if isinstance(inp, (int, float)):
                inp = f"{inp:.0f}ms"
            if isinstance(cls, (int, float)):
                cls = f"{cls:.2f}"
            if isinstance(tech_health, (int, float)):
                tech_health = f"{tech_health:.0f}/100"

        # Link velocity from backlink agent
        link_velocity = "N/A"
        if bl_agent and bl_agent.metrics:
            lv = bl_agent.metrics.get("link_velocity", 0)
            if isinstance(lv, (int, float)):
                link_velocity = f"+{lv:.0f}/mo"

        # Technical finding
        tech_finding = ""
        if tech_agent and tech_agent.findings:
            finding = tech_agent.findings[0]
            title = self._get_finding_attr(finding, "title", "")
            desc = self._get_finding_attr(finding, "description", "")
            if title:
                tech_finding = f"""
                <div class="highlight-box">
                    <strong>{html.escape(title)}</strong><br>
                    {html.escape(desc[:200])}
                </div>
                """

        return f"""
        <div class="page">
            <h1>Your Current Position</h1>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{keywords:,}</div>
                    <div class="label">Ranking Keywords</div>
                </div>
                <div class="metric-card">
                    <div class="value">{traffic:,.0f}</div>
                    <div class="label">Est. Monthly Traffic</div>
                </div>
                <div class="metric-card">
                    <div class="value">{dr}</div>
                    <div class="label">Domain Rating</div>
                </div>
            </div>

            <h2>Domain Health Scorecard</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Your Score</th>
                    <th>Target</th>
                </tr>
                <tr>
                    <td>Technical Health</td>
                    <td>{tech_health}</td>
                    <td>80+</td>
                </tr>
                <tr>
                    <td>Domain Rating</td>
                    <td>{dr}</td>
                    <td>50+</td>
                </tr>
                <tr>
                    <td>Referring Domains</td>
                    <td>{rds:,}</td>
                    <td>Varies by industry</td>
                </tr>
                <tr>
                    <td>Link Velocity</td>
                    <td>{link_velocity}</td>
                    <td>Positive growth</td>
                </tr>
            </table>

            <h2>Core Web Vitals (2025 Thresholds)</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Your Score</th>
                    <th>Good</th>
                    <th>Needs Work</th>
                </tr>
                <tr>
                    <td>LCP (Largest Contentful Paint)</td>
                    <td>{lcp}</td>
                    <td>&lt; 2.5s</td>
                    <td>&gt; 4.0s</td>
                </tr>
                <tr>
                    <td>INP (Interaction to Next Paint)</td>
                    <td>{inp}</td>
                    <td>&lt; 200ms</td>
                    <td>&gt; 500ms</td>
                </tr>
                <tr>
                    <td>CLS (Cumulative Layout Shift)</td>
                    <td>{cls}</td>
                    <td>&lt; 0.1</td>
                    <td>&gt; 0.25</td>
                </tr>
            </table>

            {tech_finding}
        </div>
        """

    def _build_competitive_landscape(self, agent_outputs: Dict[str, Any], analysis_data: Dict) -> str:
        """
        Build competitive landscape from SERP + Backlink agents.
        """
        phase1 = analysis_data.get("phase1_foundation", {})
        competitors = phase1.get("competitors", [])[:5]

        # Get SERP agent insights
        serp_agent = self._get_agent(agent_outputs, "serp_analysis")
        bl_agent = self._get_agent(agent_outputs, "backlink_intelligence")

        # Competitor table
        competitor_rows = ""
        for comp in competitors:
            common_kw = comp.get('common_keywords') or 0
            org_traffic = comp.get('organic_traffic') or 0
            comp_dr = comp.get('domain_rating') or comp.get('dr') or "N/A"
            competitor_rows += f"""
            <tr>
                <td>{html.escape(str(comp.get('domain', 'Unknown')))}</td>
                <td>{comp_dr}</td>
                <td>{common_kw:,}</td>
                <td>{org_traffic:,.0f}</td>
            </tr>
            """

        # SERP feature insights
        serp_insight = ""
        if serp_agent and serp_agent.findings:
            finding = serp_agent.findings[0]
            title = self._get_finding_attr(finding, "title", "")
            desc = self._get_finding_attr(finding, "description", "")
            if title:
                serp_insight = f"""
                <h2>SERP Feature Analysis</h2>
                <div class="highlight-box">
                    <strong>{html.escape(title)}</strong><br>
                    {html.escape(desc[:250])}
                </div>
                """

        # Link gap insights
        link_gap = ""
        if bl_agent and bl_agent.metrics:
            gap_count = bl_agent.metrics.get("competitor_link_gap", 0)
            if gap_count:
                link_gap = f"""
                <div class="highlight-box warning">
                    <strong>Link Gap Identified:</strong> {gap_count:,} referring domains link to competitors but not to you.
                </div>
                """

        return f"""
        <div class="page">
            <h1>Competitive Landscape</h1>

            <h2>Your Top Competitors</h2>
            <table>
                <tr>
                    <th>Competitor</th>
                    <th>Domain Rating</th>
                    <th>Shared Keywords</th>
                    <th>Est. Traffic</th>
                </tr>
                {competitor_rows}
            </table>

            {link_gap}

            {serp_insight}

            <h2>Competitive Position</h2>
            <p>Analysis of {len(competitors)} key competitors reveals opportunities for differentiation through targeted content and link building strategies.</p>
        </div>
        """

    def _build_opportunity(self, agent_outputs: Dict[str, Any], analysis_data: Dict) -> str:
        """
        Build opportunity section from Keyword Intelligence agent.
        """
        kw_agent = self._get_agent(agent_outputs, "keyword_intelligence")

        # Get metrics
        quick_wins = 0
        total_opportunity = 0
        keyword_gaps = 0

        if kw_agent and kw_agent.metrics:
            quick_wins = kw_agent.metrics.get("quick_win_count", 0)
            total_opportunity = kw_agent.metrics.get("estimated_traffic_opportunity", 0)
            keyword_gaps = kw_agent.metrics.get("keyword_gap_count", 0)

        # Fall back to analysis_data if no agent metrics
        if not total_opportunity:
            phase2 = analysis_data.get("phase2_keywords", {})
            gaps = phase2.get("keyword_gaps", [])
            total_opportunity = sum(g.get("search_volume") or 0 for g in gaps[:50])
            keyword_gaps = len(gaps)

        # Get keyword recommendations from agent
        keyword_table = ""
        if kw_agent and kw_agent.recommendations:
            # Find quick wins recommendation
            for rec in kw_agent.recommendations:
                action = self._get_rec_attr(rec, "action", "")
                if "quick" in action.lower() or "opportunity" in action.lower():
                    # This might have keyword data
                    break

        # Fall back to analysis_data for keyword table
        phase2 = analysis_data.get("phase2_keywords", {})
        gaps = phase2.get("keyword_gaps", [])[:7]

        gap_rows = ""
        for gap in gaps:
            volume = gap.get('search_volume') or 0
            difficulty = gap.get('difficulty') or gap.get('keyword_difficulty') or 0
            gap_rows += f"""
            <tr>
                <td>{html.escape(str(gap.get('keyword', 'Unknown')))}</td>
                <td>{volume:,}</td>
                <td>{difficulty:.0f}</td>
            </tr>
            """

        # Keyword finding
        kw_finding = ""
        if kw_agent and kw_agent.findings:
            finding = kw_agent.findings[0]
            title = self._get_finding_attr(finding, "title", "")
            desc = self._get_finding_attr(finding, "description", "")
            if title:
                kw_finding = f"""
                <div class="highlight-box success">
                    <strong>{html.escape(title)}</strong><br>
                    {html.escape(desc[:200])}
                </div>
                """

        return f"""
        <div class="page">
            <h1>The Opportunity</h1>

            <div class="metric-grid">
                <div class="metric-card success">
                    <div class="value">{quick_wins if quick_wins else keyword_gaps}+</div>
                    <div class="label">Keyword Opportunities</div>
                </div>
                <div class="metric-card">
                    <div class="value">{total_opportunity:,}</div>
                    <div class="label">Combined Search Volume</div>
                </div>
                <div class="metric-card success">
                    <div class="value">High</div>
                    <div class="label">Growth Potential</div>
                </div>
            </div>

            {kw_finding}

            <h2>Top Keyword Opportunities</h2>
            <table>
                <tr>
                    <th>Keyword</th>
                    <th>Monthly Volume</th>
                    <th>Difficulty</th>
                </tr>
                {gap_rows}
            </table>

            <p><em>Difficulty score 0-100: Lower is easier to rank for.</em></p>
        </div>
        """

    def _build_ai_visibility(self, agent_outputs: Dict[str, Any], analysis_data: Dict) -> str:
        """
        Build AI visibility section from AI Visibility agent.

        v6: Tracks confidence and shows explicit warnings for missing data.
        """
        ai_agent = self._get_agent(agent_outputs, "ai_visibility")

        # Track agent presence
        has_ai_agent = self.confidence.track(
            "ai_visibility_agent", "ai_visibility", "agent", ai_agent
        )

        # Get metrics
        ai_score = "N/A"
        presence_rate = "N/A"
        geo_readiness = "N/A"
        has_metrics = False

        if ai_agent and hasattr(ai_agent, 'metrics') and ai_agent.metrics:
            score = ai_agent.metrics.get("ai_visibility_score", 0)
            presence = ai_agent.metrics.get("ai_overview_presence", 0)
            geo = ai_agent.metrics.get("geo_readiness_score", 0)

            if isinstance(score, (int, float)) and score > 0:
                ai_score = f"{score:.0f}/100"
                has_metrics = True
            if isinstance(presence, (int, float)) and presence > 0:
                presence_rate = f"{presence:.0f}%"
                has_metrics = True
            if isinstance(geo, (int, float)) and geo > 0:
                geo_readiness = f"{geo:.0f}/100"
                has_metrics = True

        # Track metrics
        self.confidence.track(
            "ai_visibility_metrics", "ai_visibility", "agent", has_metrics
        )

        # Get AI visibility finding
        ai_finding = ""
        has_finding = False
        if ai_agent and hasattr(ai_agent, 'findings') and ai_agent.findings:
            finding = ai_agent.findings[0]
            title = self._get_finding_attr(finding, "title", "")
            desc = self._get_finding_attr(finding, "description", "")
            if title and desc:
                has_finding = True
                ai_finding = f"""
                <div class="finding">
                    <div class="finding-title">{html.escape(title)}</div>
                    <p>{html.escape(desc[:250])}</p>
                </div>
                """

        # Track finding
        self.confidence.track(
            "ai_visibility_finding", "ai_visibility", "agent", has_finding
        )

        if not ai_finding:
            self.confidence.track_fallback("ai_visibility_finding", "ai_visibility", "generic")
            ai_finding = data_missing_html("AI Visibility Analysis", "AI Visibility")

        # Get recommendations - NO GENERIC FALLBACK
        ai_recs = ""
        has_recs = False
        if ai_agent and hasattr(ai_agent, 'recommendations') and ai_agent.recommendations:
            rec_items = ""
            for rec in ai_agent.recommendations[:3]:
                action = self._get_rec_attr(rec, "action", "")
                if action:
                    rec_items += f"<li>{html.escape(action[:100])}</li>"
                    has_recs = True

            if rec_items:
                ai_recs = f"""
                <h2>AI Visibility Recommendations</h2>
                <ul>
                    {rec_items}
                </ul>
                """

        # Track recommendations
        self.confidence.track(
            "ai_visibility_recommendations", "ai_visibility", "agent", has_recs
        )

        if not ai_recs:
            self.confidence.track_fallback("ai_visibility_recommendations", "ai_visibility", "generic")
            ai_recs = data_missing_html("AI Visibility Recommendations", "AI Visibility")

        return f"""
        <div class="page">
            <h1>Authority & AI Visibility</h1>

            <h2>Why AI Visibility Matters</h2>
            <p>As AI-powered search (Google AI Overviews, ChatGPT, Perplexity) becomes more prevalent, being cited in AI-generated responses is increasingly critical for brand visibility.</p>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{ai_score}</div>
                    <div class="label">AI Visibility Score</div>
                </div>
                <div class="metric-card">
                    <div class="value">{presence_rate}</div>
                    <div class="label">AI Overview Presence</div>
                </div>
                <div class="metric-card">
                    <div class="value">{geo_readiness}</div>
                    <div class="label">GEO Readiness</div>
                </div>
            </div>

            {ai_finding}

            {ai_recs}
        </div>
        """

    def _build_roadmap(self, agent_outputs: Dict[str, Any]) -> str:
        """
        Build 90-day roadmap from Master Strategy agent.
        """
        master = self._get_agent(agent_outputs, "master_strategy")

        # Try to get structured roadmap from master agent
        phases = []
        if master and master.structured_data:
            phases = master.structured_data.get("roadmap", [])

        # Build phase content
        if phases:
            phases_html = ""
            for phase in phases[:3]:
                phase_num = phase.get("phase", "1")
                goal = phase.get("goal", "")
                initiatives = phase.get("initiatives", [])

                initiatives_html = ""
                for init in initiatives[:4]:
                    if isinstance(init, str):
                        initiatives_html += f'<div class="roadmap-item">{html.escape(init)}</div>'
                    elif isinstance(init, dict):
                        initiatives_html += f'<div class="roadmap-item">{html.escape(init.get("description", str(init)))}</div>'

                phases_html += f"""
                <div class="roadmap-phase">
                    <h3>Phase {phase_num}: {html.escape(goal)}</h3>
                    {initiatives_html}
                </div>
                """
        else:
            # Use recommendations to build roadmap
            phases_html = self._build_roadmap_from_recommendations(agent_outputs)

        # Get expected outcomes from master metrics
        outcomes = ""
        if master and master.metrics:
            traffic_uplift = master.metrics.get("estimated_traffic_uplift", 0)
            if traffic_uplift:
                outcomes = f"""
                <div class="highlight-box success">
                    <strong>Expected Outcome:</strong> {traffic_uplift:.0f}% organic traffic increase over 90 days with full implementation.
                </div>
                """

        return f"""
        <div class="page">
            <h1>90-Day Roadmap Overview</h1>

            {phases_html}

            {outcomes}

            <h2>Implementation Approach</h2>
            <p>This roadmap prioritizes high-impact, lower-effort initiatives first, building momentum before tackling larger strategic projects.</p>
        </div>
        """

    def _build_roadmap_from_recommendations(self, agent_outputs: Dict[str, Any]) -> str:
        """Build roadmap from agent recommendations if no structured roadmap exists."""
        # Collect P1, P2, P3 recommendations from all agents
        p1_items = []
        p2_items = []
        p3_items = []

        for agent_name, agent in agent_outputs.items():
            if agent and hasattr(agent, 'recommendations') and agent.recommendations:
                for rec in agent.recommendations[:2]:
                    priority = self._get_rec_attr(rec, "priority", 2)
                    action = self._get_rec_attr(rec, "action", "")
                    if action:
                        if priority == 1:
                            p1_items.append(action[:80])
                        elif priority == 2:
                            p2_items.append(action[:80])
                        else:
                            p3_items.append(action[:80])

        # Build phase HTML
        phase1_items = "".join(f'<div class="roadmap-item">{html.escape(item)}</div>' for item in p1_items[:4])
        phase2_items = "".join(f'<div class="roadmap-item">{html.escape(item)}</div>' for item in p2_items[:4])
        phase3_items = "".join(f'<div class="roadmap-item">{html.escape(item)}</div>' for item in p3_items[:4])

        # Track confidence for each phase - NO GENERIC FALLBACKS
        has_p1 = bool(phase1_items)
        has_p2 = bool(phase2_items)
        has_p3 = bool(phase3_items)

        self.confidence.track("phase1_recommendations", "roadmap", "agent", has_p1)
        self.confidence.track("phase2_recommendations", "roadmap", "agent", has_p2)
        self.confidence.track("phase3_recommendations", "roadmap", "agent", has_p3)

        # Show explicit data missing instead of generic content
        if not phase1_items:
            self.confidence.track_fallback("phase1_recommendations", "roadmap", "generic")
            phase1_items = data_missing_html("Phase 1 Recommendations", "Roadmap")

        if not phase2_items:
            self.confidence.track_fallback("phase2_recommendations", "roadmap", "generic")
            phase2_items = data_missing_html("Phase 2 Recommendations", "Roadmap")

        if not phase3_items:
            self.confidence.track_fallback("phase3_recommendations", "roadmap", "generic")
            phase3_items = data_missing_html("Phase 3 Recommendations", "Roadmap")

        return f"""
        <div class="roadmap-phase">
            <h3>Phase 1 (Days 1-30): Quick Wins & Foundation</h3>
            {phase1_items}
        </div>

        <div class="roadmap-phase">
            <h3>Phase 2 (Days 31-60): Strategic Growth</h3>
            {phase2_items}
        </div>

        <div class="roadmap-phase">
            <h3>Phase 3 (Days 61-90): Scale & Optimize</h3>
            {phase3_items}
        </div>
        """

    def _build_next_steps(self, domain: str) -> str:
        """Build next steps/CTA section."""
        return f"""
        <div class="page">
            <h1>Next Steps</h1>

            <div class="cta-box">
                <h3>Ready to Accelerate Your Organic Growth?</h3>
                <p>This analysis provides a foundation for strategic action. Let's discuss how to implement these recommendations.</p>
            </div>

            <h2>What's Included in a Full Engagement</h2>
            <ul>
                <li>Detailed 40-60 page strategy guide with implementation playbook</li>
                <li>Prioritized action items with assigned owners</li>
                <li>Implementation support and consulting</li>
                <li>Monthly progress tracking and optimization</li>
            </ul>

            <h2>Contact Us</h2>
            <p>Schedule a strategy session to discuss next steps for {html.escape(domain)}.</p>

            <div class="highlight-box">
                <strong>Email:</strong> hello@authoricy.com<br>
                <strong>Web:</strong> authoricy.com
            </div>
        </div>
        """

    def _build_methodology(self) -> str:
        """Build methodology section."""
        date = datetime.now().strftime("%B %d, %Y")
        return f"""
        <div class="page">
            <h1>Methodology & Data Sources</h1>

            <h2>How This Analysis Was Conducted</h2>
            <p>This report was generated using automated data collection combined with AI-powered analysis through our 9-agent intelligence system.</p>

            <h2>Data Sources</h2>
            <ul>
                <li><strong>Organic Rankings:</strong> DataForSEO API</li>
                <li><strong>Backlink Data:</strong> DataForSEO Backlinks API</li>
                <li><strong>Technical Audits:</strong> Lighthouse & On-Page Analysis</li>
                <li><strong>AI Analysis:</strong> Claude AI (Anthropic) - 9 specialized agents</li>
            </ul>

            <h2>Analysis Agents</h2>
            <table>
                <tr><th>Agent</th><th>Focus Area</th></tr>
                <tr><td>Keyword Intelligence</td><td>Opportunity scoring, gaps, quick wins</td></tr>
                <tr><td>Backlink Intelligence</td><td>Link profile, building strategy</td></tr>
                <tr><td>Technical SEO</td><td>Core Web Vitals, crawlability</td></tr>
                <tr><td>Content Analysis</td><td>Content decay, KUCK recommendations</td></tr>
                <tr><td>Semantic Architecture</td><td>Topic clusters, internal linking</td></tr>
                <tr><td>AI Visibility</td><td>GEO optimization, AI overview presence</td></tr>
                <tr><td>SERP Analysis</td><td>Feature opportunities, content formats</td></tr>
                <tr><td>Master Strategy</td><td>Synthesis, prioritization, roadmap</td></tr>
            </table>

            <h2>Data Freshness</h2>
            <p>All data collected on {date}. Rankings and traffic estimates may fluctuate.</p>

            <div class="confidential" style="margin-top: 40px; text-align: center;">
                © {datetime.now().year} Authoricy. All rights reserved.
            </div>
        </div>
        """

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_finding_attr(self, finding: Any, attr: str, default: str = "") -> str:
        """Safely get attribute from finding (handles both dict and object)."""
        if isinstance(finding, dict):
            return str(finding.get(attr, default))
        return str(getattr(finding, attr, default))

    def _get_rec_attr(self, rec: Any, attr: str, default: Any = "") -> Any:
        """Safely get attribute from recommendation (handles both dict and object)."""
        if isinstance(rec, dict):
            return rec.get(attr, default)
        return getattr(rec, attr, default)
