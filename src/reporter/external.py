"""
External Report Builder - Lead Magnet (10-15 pages)

Generates executive-focused, sales-enabling PDF report.
Structure:
1. Cover
2. Executive Summary (2 pages)
3. Current Position (2 pages)
4. Competitive Landscape (2 pages)
5. The Opportunity (2 pages)
6. Authority & AI Visibility (1 page)
7. 90-Day Roadmap (2 pages)
8. Next Steps (1 page)
9. Methodology (1 page)
"""

import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import html

logger = logging.getLogger(__name__)


class ExternalReportBuilder:
    """
    Builds external report HTML for PDF generation.
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir

    def build(
        self,
        analysis_result: Any,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        Build complete HTML for external report.

        Args:
            analysis_result: Analysis result from engine
            analysis_data: Original compiled data

        Returns:
            Complete HTML document
        """
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        phase1 = analysis_data.get("phase1_foundation", {})

        domain = metadata.get("domain", "Unknown")
        market = metadata.get("market", "Unknown")

        # Build sections
        sections = [
            self._build_cover(domain, market),
            self._build_executive_summary(analysis_result, metadata),
            self._build_current_position(analysis_data, analysis_result),
            self._build_competitive_landscape(analysis_data, analysis_result),
            self._build_opportunity(analysis_data, analysis_result),
            self._build_ai_visibility(analysis_data, analysis_result),
            self._build_roadmap(analysis_result),
            self._build_next_steps(domain),
            self._build_methodology(),
        ]

        # Combine into full document
        return self._wrap_html(sections, domain)

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

    def _build_executive_summary(self, analysis_result: Any, metadata: Dict) -> str:
        """Build executive summary pages."""
        exec_summary = getattr(analysis_result, 'executive_summary', '')

        # Parse executive summary or use default
        if not exec_summary:
            exec_summary = "Analysis summary pending."

        # Clean up markdown for HTML
        exec_summary = exec_summary.replace("## ", "<h2>").replace("\n\n", "</p><p>")

        return f"""
        <div class="page">
            <h1>Executive Summary</h1>

            <div class="highlight-box">
                <strong>The Headline:</strong><br>
                {html.escape(exec_summary[:500]) if len(exec_summary) > 0 else 'Analysis complete. Key opportunities identified.'}
            </div>

            <h2>Key Findings</h2>
            <div class="finding">
                <div class="finding-title">1. Current Organic Position</div>
                <p>Based on comprehensive analysis of your domain's organic visibility.</p>
            </div>
            <div class="finding">
                <div class="finding-title">2. Competitive Landscape</div>
                <p>Your position relative to key competitors in the market.</p>
            </div>
            <div class="finding">
                <div class="finding-title">3. Growth Opportunity</div>
                <p>Identified opportunities for organic traffic growth.</p>
            </div>

            <h2>Recommended Next Step</h2>
            <p>Schedule a strategy session to discuss implementing the prioritized roadmap.</p>
        </div>
        """

    def _build_current_position(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build current position section."""
        summary = analysis_data.get("summary", {})
        phase1 = analysis_data.get("phase1_foundation", {})
        overview = phase1.get("domain_overview", {})
        backlinks = phase1.get("backlink_summary", {})
        technical = phase1.get("technical_baseline", {})

        keywords = summary.get("total_organic_keywords", 0)
        traffic = summary.get("total_organic_traffic", 0)
        dr = backlinks.get("domain_rank", 0)
        rds = backlinks.get("referring_domains", 0)
        perf_score = technical.get("performance_score", 0)

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
                    <th>Industry Avg</th>
                </tr>
                <tr>
                    <td>Organic Keywords</td>
                    <td>{keywords:,}</td>
                    <td>Varies</td>
                </tr>
                <tr>
                    <td>Domain Rating</td>
                    <td>{dr}</td>
                    <td>30-50</td>
                </tr>
                <tr>
                    <td>Referring Domains</td>
                    <td>{rds:,}</td>
                    <td>Varies</td>
                </tr>
                <tr>
                    <td>Performance Score</td>
                    <td>{perf_score:.0%}</td>
                    <td>0.70</td>
                </tr>
            </table>

            <h2>12-Month Trend</h2>
            <p>Historical performance analysis shows the trajectory of your organic visibility over the past year.</p>
        </div>
        """

    def _build_competitive_landscape(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build competitive landscape section."""
        phase1 = analysis_data.get("phase1_foundation", {})
        competitors = phase1.get("competitors", [])[:5]

        competitor_rows = ""
        for comp in competitors:
            competitor_rows += f"""
            <tr>
                <td>{html.escape(comp.get('domain', 'Unknown'))}</td>
                <td>{comp.get('common_keywords', 0):,}</td>
                <td>{comp.get('organic_traffic', 0):,.0f}</td>
            </tr>
            """

        return f"""
        <div class="page">
            <h1>Competitive Landscape</h1>

            <h2>Your Top Competitors</h2>
            <table>
                <tr>
                    <th>Competitor</th>
                    <th>Shared Keywords</th>
                    <th>Est. Traffic</th>
                </tr>
                {competitor_rows}
            </table>

            <h2>Competitive Position</h2>
            <div class="highlight-box">
                <p>Analysis of {len(competitors)} key competitors reveals opportunities for differentiation and growth.</p>
            </div>

            <h2>Who's Gaining, Who's Losing</h2>
            <p>Trajectory analysis of competitor performance over time helps identify market trends and opportunities.</p>
        </div>
        """

    def _build_opportunity(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build opportunity section."""
        phase2 = analysis_data.get("phase2_keywords", {})
        gaps = phase2.get("keyword_gaps", [])[:10]
        summary = analysis_data.get("summary", {})

        gap_count = len(gaps)
        total_opportunity = sum(g.get("search_volume", 0) for g in gaps)

        gap_rows = ""
        for gap in gaps[:5]:
            gap_rows += f"""
            <tr>
                <td>{html.escape(gap.get('keyword', 'Unknown'))}</td>
                <td>{gap.get('search_volume', 0):,}</td>
                <td>{gap.get('difficulty', 0):.0f}</td>
            </tr>
            """

        return f"""
        <div class="page">
            <h1>The Opportunity</h1>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{gap_count}+</div>
                    <div class="label">Keyword Opportunities</div>
                </div>
                <div class="metric-card">
                    <div class="value">{total_opportunity:,}</div>
                    <div class="label">Combined Search Volume</div>
                </div>
                <div class="metric-card">
                    <div class="value">High</div>
                    <div class="label">Growth Potential</div>
                </div>
            </div>

            <h2>Top Keyword Opportunities</h2>
            <table>
                <tr>
                    <th>Keyword</th>
                    <th>Monthly Volume</th>
                    <th>Difficulty</th>
                </tr>
                {gap_rows}
            </table>

            <div class="highlight-box success">
                <strong>Quick Wins Identified:</strong> Several high-volume, low-difficulty keywords where competitors rank but you don't.
            </div>
        </div>
        """

    def _build_ai_visibility(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build AI visibility section."""
        phase4 = analysis_data.get("phase4_ai_technical", {})
        ai_data = phase4.get("ai_visibility", {})

        return f"""
        <div class="page">
            <h1>Authority & AI Visibility</h1>

            <h2>Why AI Visibility Matters</h2>
            <p>As AI-powered search and assistants become more prevalent, being cited and referenced by these systems is increasingly important for brand visibility.</p>

            <h2>Your AI Visibility Assessment</h2>
            <div class="highlight-box">
                <p>AI visibility analysis examines how your brand appears in AI-generated responses and citations.</p>
            </div>

            <h2>Competitive AI Landscape</h2>
            <p>Understanding which competitors dominate AI citations helps identify opportunities for improvement.</p>

            <h2>Recommendations</h2>
            <ul>
                <li>Structure content for AI comprehension</li>
                <li>Build authoritative, cited content</li>
                <li>Improve entity recognition</li>
            </ul>
        </div>
        """

    def _build_roadmap(self, analysis_result: Any) -> str:
        """Build 90-day roadmap section."""
        return f"""
        <div class="page">
            <h1>90-Day Roadmap Overview</h1>

            <h2>Phase 1: Foundation</h2>
            <div class="finding">
                <div class="finding-title">Quick Wins & Technical Fixes</div>
                <ul>
                    <li>Address critical technical issues</li>
                    <li>Optimize existing high-potential pages</li>
                    <li>Implement tracking improvements</li>
                </ul>
            </div>

            <h2>Phase 2: Acceleration</h2>
            <div class="finding">
                <div class="finding-title">Content & Link Building</div>
                <ul>
                    <li>Create priority content pieces</li>
                    <li>Launch link acquisition campaign</li>
                    <li>Expand keyword coverage</li>
                </ul>
            </div>

            <h2>Phase 3: Scale</h2>
            <div class="finding">
                <div class="finding-title">Expand & Optimize</div>
                <ul>
                    <li>Scale successful strategies</li>
                    <li>Enter new keyword territories</li>
                    <li>Build competitive moats</li>
                </ul>
            </div>

            <h2>Expected Outcomes</h2>
            <p>Implementation of this roadmap is designed to improve organic visibility, increase qualified traffic, and strengthen competitive position.</p>
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
                <li>Detailed 40-60 page strategy guide</li>
                <li>Implementation support and consulting</li>
                <li>Monthly progress tracking</li>
                <li>Ongoing optimization recommendations</li>
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
            <p>This report was generated using automated data collection and AI-powered analysis.</p>

            <h2>Data Sources</h2>
            <ul>
                <li><strong>Organic Rankings:</strong> DataForSEO API</li>
                <li><strong>Backlink Data:</strong> DataForSEO Backlinks API</li>
                <li><strong>Technical Audits:</strong> Lighthouse & On-Page Analysis</li>
                <li><strong>AI Analysis:</strong> Claude AI (Anthropic)</li>
            </ul>

            <h2>Data Freshness</h2>
            <p>All data collected on {date}. Rankings and traffic estimates may fluctuate.</p>

            <h2>Limitations</h2>
            <ul>
                <li>Traffic estimates are approximations based on ranking positions</li>
                <li>Competitive data limited to publicly available information</li>
                <li>Historical trends based on monthly snapshots</li>
            </ul>

            <h2>About Authoricy</h2>
            <p>Authoricy provides AI-powered SEO intelligence and strategy services.</p>

            <div class="confidential" style="margin-top: 40px; text-align: center;">
                © {datetime.now().year} Authoricy. All rights reserved.
            </div>
        </div>
        """
