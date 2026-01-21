"""
Internal Report Builder - Strategy Guide (40-60 pages)

Generates comprehensive tactical playbook for implementation.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import html
import json

logger = logging.getLogger(__name__)


class InternalReportBuilder:
    """
    Builds internal strategy guide HTML for PDF generation.

    Comprehensive 40-60 page tactical playbook.
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir

    def build(
        self,
        analysis_result: Any,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        Build complete HTML for internal report.

        Args:
            analysis_result: Analysis result from engine
            analysis_data: Original compiled data

        Returns:
            Complete HTML document
        """
        metadata = analysis_data.get("metadata", {})
        domain = metadata.get("domain", "Unknown")

        sections = [
            self._build_cover(domain, metadata),
            self._build_toc(),
            self._build_executive_summary(analysis_result),
            self._build_domain_analysis(analysis_data),
            self._build_keyword_universe(analysis_data),
            self._build_competitive_intelligence(analysis_data),
            self._build_backlink_strategy(analysis_data),
            self._build_ai_visibility_playbook(analysis_data),
            self._build_content_strategy(analysis_result),
            self._build_technical_register(analysis_data),
            self._build_implementation_plan(analysis_result),
            self._build_measurement_framework(),
            self._build_appendix(analysis_data),
        ]

        return self._wrap_html(sections, domain)

    def _wrap_html(self, sections: list, domain: str) -> str:
        """Wrap sections in full HTML document."""
        content = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(domain)} - Strategy Guide</title>
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    {content}
</body>
</html>"""

    def _get_styles(self) -> str:
        """Get CSS styles for internal report."""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page);
                font-size: 10px;
            }
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
        }

        .page { page-break-after: always; }
        .page:last-child { page-break-after: avoid; }

        h1 { font-size: 22pt; color: #1a1a2e; margin: 0 0 20px; }
        h2 { font-size: 16pt; color: #2d3436; margin: 25px 0 15px; }
        h3 { font-size: 12pt; color: #2d3436; margin: 20px 0 10px; }
        h4 { font-size: 11pt; color: #555; margin: 15px 0 8px; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 9pt;
        }

        th, td {
            padding: 8px 10px;
            text-align: left;
            border: 1px solid #ddd;
        }

        th { background: #f5f5f5; font-weight: 600; }

        .data-box {
            background: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }

        .metric { font-size: 24pt; font-weight: bold; color: #4361ee; }
        .label { font-size: 9pt; color: #666; }

        pre {
            background: #f5f5f5;
            padding: 10px;
            overflow-x: auto;
            font-size: 8pt;
        }

        .toc a { text-decoration: none; color: #333; }
        .toc-item { margin: 8px 0; }

        ul, ol { margin: 10px 0 10px 20px; }
        li { margin: 5px 0; }
        """

    def _build_cover(self, domain: str, metadata: Dict) -> str:
        """Build cover page."""
        date = datetime.now().strftime("%B %Y")
        return f"""
        <div class="page" style="display: flex; flex-direction: column; justify-content: center; min-height: 100vh; text-align: center;">
            <h1 style="font-size: 28pt;">{html.escape(domain)}</h1>
            <p style="font-size: 16pt; color: #666;">SEO Strategy Guide</p>
            <p style="margin-top: 40px; color: #888;">Complete Tactical Playbook</p>
            <p style="color: #888;">{date}</p>
            <p style="margin-top: 60px; font-size: 9pt; color: #aaa;">CONFIDENTIAL - INTERNAL USE ONLY</p>
        </div>
        """

    def _build_toc(self) -> str:
        """Build table of contents."""
        return """
        <div class="page">
            <h1>Table of Contents</h1>
            <div class="toc">
                <div class="toc-item">1. Executive Summary</div>
                <div class="toc-item">2. Complete Domain Analysis</div>
                <div class="toc-item">3. Keyword Universe</div>
                <div class="toc-item">4. Competitive Intelligence</div>
                <div class="toc-item">5. Backlink Strategy</div>
                <div class="toc-item">6. AI Visibility Playbook</div>
                <div class="toc-item">7. Content Strategy</div>
                <div class="toc-item">8. Technical SEO Register</div>
                <div class="toc-item">9. Implementation Plan</div>
                <div class="toc-item">10. Measurement Framework</div>
                <div class="toc-item">Appendices</div>
            </div>
        </div>
        """

    def _build_executive_summary(self, analysis_result: Any) -> str:
        """Build executive summary section."""
        summary = getattr(analysis_result, 'executive_summary', 'Analysis summary.')
        return f"""
        <div class="page">
            <h1>1. Executive Summary</h1>
            <div class="data-box">
                {html.escape(summary[:3000])}
            </div>
        </div>
        """

    def _build_domain_analysis(self, analysis_data: Dict) -> str:
        """Build complete domain analysis section."""
        phase1 = analysis_data.get("phase1_foundation", {})
        overview = phase1.get("domain_overview", {})
        historical = phase1.get("historical_data", [])
        subdomains = phase1.get("subdomains", [])
        top_pages = phase1.get("top_pages", [])[:20]
        tech = phase1.get("technologies", [])

        # Historical trend table
        hist_rows = ""
        for h in historical[-12:]:
            hist_rows += f"<tr><td>{h.get('date', 'N/A')}</td><td>{h.get('organic_keywords', 0):,}</td><td>{h.get('organic_traffic', 0):,.0f}</td></tr>"

        # Top pages table
        page_rows = ""
        for p in top_pages:
            page_rows += f"<tr><td>{html.escape(str(p.get('page', ''))[:50])}</td><td>{p.get('organic_keywords', 0):,}</td><td>{p.get('organic_traffic', 0):,.0f}</td></tr>"

        return f"""
        <div class="page">
            <h1>2. Complete Domain Analysis</h1>

            <h2>2.1 Domain Metrics Overview</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Organic Keywords</td><td>{overview.get('organic_keywords', 0):,}</td></tr>
                <tr><td>Organic Traffic</td><td>{overview.get('organic_traffic', 0):,.0f}</td></tr>
                <tr><td>Paid Keywords</td><td>{overview.get('paid_keywords', 0):,}</td></tr>
            </table>

            <h2>2.2 24-Month Historical Trend</h2>
            <table>
                <tr><th>Date</th><th>Keywords</th><th>Traffic</th></tr>
                {hist_rows}
            </table>
        </div>

        <div class="page">
            <h2>2.3 Top Performing Pages</h2>
            <table>
                <tr><th>Page</th><th>Keywords</th><th>Traffic</th></tr>
                {page_rows}
            </table>

            <h2>2.4 Technology Stack</h2>
            <ul>
                {''.join(f"<li>{html.escape(t.get('name', 'Unknown'))} ({html.escape(t.get('category', 'Unknown'))})</li>" for t in tech[:15])}
            </ul>
        </div>
        """

    def _build_keyword_universe(self, analysis_data: Dict) -> str:
        """Build keyword universe section."""
        phase2 = analysis_data.get("phase2_keywords", {})
        ranked = phase2.get("ranked_keywords", [])[:50]
        gaps = phase2.get("keyword_gaps", [])[:30]
        clusters = phase2.get("keyword_clusters", [])

        ranked_rows = ""
        for kw in ranked:
            ranked_rows += f"""<tr>
                <td>{html.escape(str(kw.get('keyword', '')))}</td>
                <td>{kw.get('position', 0)}</td>
                <td>{kw.get('search_volume', 0):,}</td>
                <td>{kw.get('traffic', 0):,.0f}</td>
            </tr>"""

        gap_rows = ""
        for g in gaps:
            gap_rows += f"""<tr>
                <td>{html.escape(str(g.get('keyword', '')))}</td>
                <td>{g.get('search_volume', 0):,}</td>
                <td>{g.get('difficulty', 0):.0f}</td>
            </tr>"""

        return f"""
        <div class="page">
            <h1>3. Keyword Universe</h1>

            <h2>3.1 Current Keyword Portfolio</h2>
            <p>Top 50 ranking keywords by traffic value:</p>
            <table>
                <tr><th>Keyword</th><th>Position</th><th>Volume</th><th>Traffic</th></tr>
                {ranked_rows}
            </table>
        </div>

        <div class="page">
            <h2>3.2 Keyword Gap Analysis</h2>
            <p>High-opportunity keywords where competitors rank:</p>
            <table>
                <tr><th>Keyword</th><th>Volume</th><th>Difficulty</th></tr>
                {gap_rows}
            </table>

            <h2>3.3 Keyword Clusters</h2>
            <p>{len(clusters)} topical clusters identified for content strategy.</p>
        </div>
        """

    def _build_competitive_intelligence(self, analysis_data: Dict) -> str:
        """Build competitive intelligence section."""
        phase3 = analysis_data.get("phase3_competitive", {})
        phase1 = analysis_data.get("phase1_foundation", {})
        competitors = phase1.get("competitors", [])[:5]

        comp_rows = ""
        for c in competitors:
            comp_rows += f"""<tr>
                <td>{html.escape(str(c.get('domain', '')))}</td>
                <td>{c.get('common_keywords', 0):,}</td>
                <td>{c.get('organic_traffic', 0):,.0f}</td>
            </tr>"""

        return f"""
        <div class="page">
            <h1>4. Competitive Intelligence</h1>

            <h2>4.1 Competitor Profiles</h2>
            <table>
                <tr><th>Competitor</th><th>Shared Keywords</th><th>Traffic</th></tr>
                {comp_rows}
            </table>

            <h2>4.2 Competitive Position Analysis</h2>
            <p>Analysis of keyword overlap and competitive positioning.</p>

            <h2>4.3 Strategic Recommendations</h2>
            <ul>
                <li>Focus on differentiation in underserved areas</li>
                <li>Target competitor weakness keywords</li>
                <li>Build authority in contested topics</li>
            </ul>
        </div>
        """

    def _build_backlink_strategy(self, analysis_data: Dict) -> str:
        """Build backlink strategy section."""
        phase1 = analysis_data.get("phase1_foundation", {})
        phase3 = analysis_data.get("phase3_competitive", {})
        backlinks = phase1.get("backlink_summary", {})
        top_links = phase3.get("top_backlinks", [])[:20]
        anchors = phase3.get("anchor_distribution", [])[:15]
        rds = phase3.get("referring_domains", [])[:15]

        return f"""
        <div class="page">
            <h1>5. Backlink Strategy</h1>

            <h2>5.1 Current Link Profile</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Backlinks</td><td>{backlinks.get('total_backlinks', 0):,}</td></tr>
                <tr><td>Referring Domains</td><td>{backlinks.get('referring_domains', 0):,}</td></tr>
                <tr><td>Domain Rating</td><td>{backlinks.get('domain_rank', 0)}</td></tr>
            </table>

            <h2>5.2 Link Building Targets</h2>
            <p>Based on link gap analysis, prioritize outreach to domains linking to competitors but not to us.</p>

            <h2>5.3 Anchor Text Strategy</h2>
            <p>Maintain natural anchor text distribution to avoid over-optimization penalties.</p>
        </div>
        """

    def _build_ai_visibility_playbook(self, analysis_data: Dict) -> str:
        """Build AI visibility playbook."""
        phase4 = analysis_data.get("phase4_ai_technical", {})

        return f"""
        <div class="page">
            <h1>6. AI Visibility Playbook</h1>

            <h2>6.1 Current AI Visibility</h2>
            <p>Assessment of brand presence in AI-generated content and responses.</p>

            <h2>6.2 Optimization Strategies</h2>
            <ul>
                <li>Structure content for AI comprehension</li>
                <li>Build entity associations</li>
                <li>Create authoritative, citable content</li>
                <li>Implement proper schema markup</li>
            </ul>

            <h2>6.3 Content Formatting Guidelines</h2>
            <ul>
                <li>Use clear headers and structure</li>
                <li>Include factual, verifiable claims</li>
                <li>Provide comprehensive topic coverage</li>
                <li>Update content regularly for freshness</li>
            </ul>
        </div>
        """

    def _build_content_strategy(self, analysis_result: Any) -> str:
        """Build content strategy section."""
        strategy = getattr(analysis_result, 'loop3_enrichment', '')

        return f"""
        <div class="page">
            <h1>7. Content Strategy</h1>

            <h2>7.1 Priority Content Pieces</h2>
            <p>Based on keyword opportunity analysis, the following content should be prioritized:</p>

            <h2>7.2 Content Briefs</h2>
            <div class="data-box">
                {html.escape(strategy[:2000]) if strategy else 'Content briefs available in analysis output.'}
            </div>

            <h2>7.3 Content Refresh Priorities</h2>
            <p>Existing content that should be updated for improved performance.</p>
        </div>
        """

    def _build_technical_register(self, analysis_data: Dict) -> str:
        """Build technical SEO register."""
        phase1 = analysis_data.get("phase1_foundation", {})
        technical = phase1.get("technical_baseline", {})

        return f"""
        <div class="page">
            <h1>8. Technical SEO Register</h1>

            <h2>8.1 Core Web Vitals</h2>
            <table>
                <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
                <tr><td>Performance</td><td>{technical.get('performance_score', 0):.0%}</td><td>{'Pass' if technical.get('performance_score', 0) > 0.5 else 'Needs Work'}</td></tr>
                <tr><td>Accessibility</td><td>{technical.get('accessibility_score', 0):.0%}</td><td>{'Pass' if technical.get('accessibility_score', 0) > 0.5 else 'Needs Work'}</td></tr>
                <tr><td>Best Practices</td><td>{technical.get('best_practices_score', 0):.0%}</td><td>{'Pass' if technical.get('best_practices_score', 0) > 0.5 else 'Needs Work'}</td></tr>
                <tr><td>SEO</td><td>{technical.get('seo_score', 0):.0%}</td><td>{'Pass' if technical.get('seo_score', 0) > 0.5 else 'Needs Work'}</td></tr>
            </table>

            <h2>8.2 Technical Issue Priorities</h2>
            <p>Address critical technical issues to improve crawling and indexing.</p>
        </div>
        """

    def _build_implementation_plan(self, analysis_result: Any) -> str:
        """Build implementation plan."""
        strategy = getattr(analysis_result, 'loop2_strategy', '')

        return f"""
        <div class="page">
            <h1>9. Implementation Plan</h1>

            <h2>9.1 Phased Approach</h2>

            <h3>Phase 1: Foundation</h3>
            <ul>
                <li>Technical fixes</li>
                <li>Quick win optimizations</li>
                <li>Tracking setup</li>
            </ul>

            <h3>Phase 2: Acceleration</h3>
            <ul>
                <li>Content creation</li>
                <li>Link building initiation</li>
                <li>Competitive targeting</li>
            </ul>

            <h3>Phase 3: Scale</h3>
            <ul>
                <li>Expand coverage</li>
                <li>Automate processes</li>
                <li>Build moats</li>
            </ul>

            <h2>9.2 Resource Requirements</h2>
            <p>Implementation requires coordinated effort across content, technical, and outreach teams.</p>
        </div>
        """

    def _build_measurement_framework(self) -> str:
        """Build measurement framework."""
        return """
        <div class="page">
            <h1>10. Measurement Framework</h1>

            <h2>10.1 KPI Definitions</h2>
            <table>
                <tr><th>KPI</th><th>Definition</th><th>Target</th></tr>
                <tr><td>Organic Traffic</td><td>Monthly organic sessions</td><td>+20%</td></tr>
                <tr><td>Keyword Rankings</td><td>Top 10 positions</td><td>+50</td></tr>
                <tr><td>Domain Rating</td><td>Ahrefs DR metric</td><td>+5</td></tr>
                <tr><td>Referring Domains</td><td>Unique linking domains</td><td>+100</td></tr>
            </table>

            <h2>10.2 Reporting Cadence</h2>
            <ul>
                <li>Weekly: Rankings check, traffic review</li>
                <li>Monthly: Full performance report</li>
                <li>Quarterly: Strategy review and adjustment</li>
            </ul>
        </div>
        """

    def _build_appendix(self, analysis_data: Dict) -> str:
        """Build appendix with raw data."""
        return """
        <div class="page">
            <h1>Appendices</h1>

            <h2>A. Complete Keyword Lists</h2>
            <p>Available as CSV export upon request.</p>

            <h2>B. Full Backlink Data</h2>
            <p>Complete backlink profile available as CSV export.</p>

            <h2>C. Competitor Raw Data</h2>
            <p>Detailed competitor metrics available upon request.</p>

            <h2>D. Technical Audit Details</h2>
            <p>Full Lighthouse reports available as separate documents.</p>

            <h2>E. Methodology Notes</h2>
            <p>This analysis was conducted using DataForSEO API for data collection and Claude AI for analysis and recommendations.</p>
        </div>
        """
