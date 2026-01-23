"""
SEO Strategy Report Builder (40-60 pages)

THE ONLY REPORT - Comprehensive tactical playbook with confidence tracking.

v7: Single report with confidence tracking - makes missing data VISIBLE.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING
from datetime import datetime
import html

from .confidence import ReportConfidence, data_missing_html

if TYPE_CHECKING:
    from ..agents.base import AgentOutput

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Builds THE report - comprehensive strategy guide with confidence tracking.

    This is the ONLY report we generate. No more external vs internal.
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
        Build complete HTML report with confidence tracking.

        Returns:
            Tuple of (HTML document, ReportConfidence)
        """
        # Reset confidence tracking
        self.confidence = ReportConfidence()

        metadata = analysis_data.get("metadata", {})
        domain = metadata.get("domain", "Unknown")
        market = metadata.get("market", "Unknown")

        # Track basic data presence
        self.confidence.track("metadata", "global", "raw_data", bool(metadata))
        self.confidence.track("analysis_result", "global", "agent", analysis_result is not None)

        sections = [
            self._build_cover(domain, market),
            self._build_executive_summary(analysis_result, analysis_data),
            self._build_domain_analysis(analysis_data),
            self._build_keyword_analysis(analysis_data),
            self._build_competitive_analysis(analysis_data, analysis_result),
            self._build_backlink_analysis(analysis_data, analysis_result),
            self._build_content_strategy(analysis_result, analysis_data),
            self._build_technical_analysis(analysis_data, analysis_result),
            self._build_ai_visibility(analysis_data, analysis_result),
            self._build_strategic_roadmap(analysis_result),
            self._build_methodology(domain),
        ]

        # Add confidence warning banner after cover if score is low
        confidence_warning = self.confidence.generate_warning_html()
        if confidence_warning:
            sections.insert(1, f'<div class="page">{confidence_warning}</div>')

        # Log confidence
        conf_data = self.confidence.to_dict()
        logger.info(
            f"Report confidence: {conf_data['confidence_level']} ({conf_data['confidence_score']:.0f}%), "
            f"fallbacks: {conf_data['fallback_count']}, missing: {len(conf_data['missing_required'])}"
        )
        if conf_data['missing_required']:
            logger.warning(f"Missing data: {conf_data['missing_required'][:5]}")

        return self._wrap_html(sections, domain), self.confidence

    def _wrap_html(self, sections: list, domain: str) -> str:
        """Wrap sections in HTML document."""
        content = "\n".join(sections)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(domain)} - SEO Strategy Report</title>
    <style>{self._get_styles()}</style>
</head>
<body>
    {content}
</body>
</html>"""

    def _get_styles(self) -> str:
        """CSS styles for the report."""
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

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
        }

        .page {
            page-break-after: always;
            min-height: 100vh;
            padding: 20px 0;
        }
        .page:last-child { page-break-after: avoid; }

        .cover {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            min-height: 100vh;
        }

        h1 { font-size: 22pt; color: #1a1a2e; margin-bottom: 20px; }
        h2 { font-size: 16pt; color: #2d3436; margin: 25px 0 15px; }
        h3 { font-size: 12pt; color: #2d3436; margin: 20px 0 10px; }

        p { margin-bottom: 12px; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 9pt;
        }

        th, td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th { background: #f8f9fa; font-weight: 600; }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
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
            font-size: 20pt;
            font-weight: bold;
            color: #4361ee;
        }

        .metric-card .label {
            font-size: 9pt;
            color: #666;
            margin-top: 5px;
        }

        .highlight-box {
            background: #f8f9fa;
            border-left: 4px solid #4361ee;
            padding: 15px 20px;
            margin: 20px 0;
        }

        .highlight-box.warning { border-left-color: #f72585; }
        .highlight-box.success { border-left-color: #06d6a0; }

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

        ul, ol { margin: 10px 0 10px 20px; }
        li { margin: 5px 0; }

        .data-box {
            background: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            white-space: pre-wrap;
            font-size: 9pt;
        }

        .roadmap-phase {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .roadmap-phase h3 { color: #4361ee; margin-bottom: 10px; }

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

        .logo { font-size: 14pt; font-weight: bold; color: #4361ee; }
        .confidential {
            font-size: 9pt;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        """

    # =========================================================================
    # COVER
    # =========================================================================

    def _build_cover(self, domain: str, market: str) -> str:
        """Build cover page."""
        date = datetime.now().strftime("%B %Y")
        return f"""
        <div class="page cover">
            <div class="logo">AUTHORICY</div>
            <h1 style="font-size: 32pt; margin-top: 20px;">{html.escape(domain)}</h1>
            <p style="font-size: 16pt; color: #666;">SEO Strategy Report</p>
            <p style="margin-top: 40px; color: #888;">Market: {html.escape(market)}</p>
            <p style="color: #888;">{date}</p>
            <div class="confidential" style="margin-top: 60px;">Confidential</div>
        </div>
        """

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================

    def _build_executive_summary(self, analysis_result: Any, analysis_data: Dict) -> str:
        """Build executive summary with real AI analysis."""
        summary = analysis_data.get("summary", {})

        # Get executive summary from AI
        exec_summary = None
        if analysis_result:
            exec_summary = getattr(analysis_result, 'executive_summary', None)

        has_exec_summary = self.confidence.track(
            "executive_summary", "executive_summary", "agent", bool(exec_summary)
        )

        if exec_summary:
            summary_html = f'<div class="data-box">{html.escape(exec_summary[:4000])}</div>'
        else:
            self.confidence.track_fallback("executive_summary", "executive_summary", "missing")
            summary_html = data_missing_html("AI Executive Summary", "Executive Summary")

        # Key metrics from raw data
        keywords = summary.get("total_organic_keywords") or 0
        traffic = summary.get("total_organic_traffic") or 0
        dr = summary.get("domain_rank") or 0
        competitors = summary.get("competitor_count") or 0

        self.confidence.track("summary_metrics", "executive_summary", "raw_data",
                             keywords > 0 or traffic > 0)

        return f"""
        <div class="page">
            <h1>Executive Summary</h1>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{keywords:,}</div>
                    <div class="label">Ranking Keywords</div>
                </div>
                <div class="metric-card">
                    <div class="value">{traffic:,.0f}</div>
                    <div class="label">Monthly Traffic</div>
                </div>
                <div class="metric-card">
                    <div class="value">{dr}</div>
                    <div class="label">Domain Rating</div>
                </div>
                <div class="metric-card">
                    <div class="value">{competitors}</div>
                    <div class="label">Competitors</div>
                </div>
            </div>

            <h2>Analysis Overview</h2>
            {summary_html}
        </div>
        """

    # =========================================================================
    # DOMAIN ANALYSIS
    # =========================================================================

    def _build_domain_analysis(self, analysis_data: Dict) -> str:
        """Build domain analysis with real data."""
        phase1 = analysis_data.get("phase1_foundation", {})
        overview = phase1.get("domain_overview", {})
        historical = phase1.get("historical_data", [])
        top_pages = phase1.get("top_pages", [])[:20]
        tech = phase1.get("technologies", [])

        # Track data presence
        has_overview = self.confidence.track("domain_overview", "domain_analysis", "raw_data", bool(overview))
        has_historical = self.confidence.track("historical_data", "domain_analysis", "raw_data", len(historical) > 0)
        has_pages = self.confidence.track("top_pages", "domain_analysis", "raw_data", len(top_pages) > 0)

        # Domain metrics
        org_kw = overview.get('organic_keywords') or 0
        org_traffic = overview.get('organic_traffic') or 0
        paid_kw = overview.get('paid_keywords') or 0

        # Historical trend
        hist_rows = ""
        if historical:
            for h in historical[-12:]:
                h_kw = h.get('organic_keywords') or 0
                h_traffic = h.get('organic_traffic') or 0
                hist_rows += f"<tr><td>{h.get('date', 'N/A')}</td><td>{h_kw:,}</td><td>{h_traffic:,.0f}</td></tr>"
        else:
            hist_rows = f'<tr><td colspan="3">{data_missing_html("Historical Data", "Domain Analysis")}</td></tr>'

        # Top pages
        page_rows = ""
        if top_pages:
            for p in top_pages:
                p_kw = p.get('organic_keywords') or 0
                p_traffic = p.get('organic_traffic') or 0
                page_rows += f"<tr><td>{html.escape(str(p.get('page', ''))[:60])}</td><td>{p_kw:,}</td><td>{p_traffic:,.0f}</td></tr>"
        else:
            page_rows = f'<tr><td colspan="3">{data_missing_html("Top Pages", "Domain Analysis")}</td></tr>'

        # Technologies
        tech_html = ""
        if tech:
            tech_items = "".join(f"<li>{html.escape(t.get('name', 'Unknown'))} ({html.escape(t.get('category', ''))})</li>" for t in tech[:15])
            tech_html = f"<ul>{tech_items}</ul>"
        else:
            tech_html = data_missing_html("Technology Stack", "Domain Analysis")

        return f"""
        <div class="page">
            <h1>Domain Analysis</h1>

            <h2>Current Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Organic Keywords</td><td>{org_kw:,}</td></tr>
                <tr><td>Organic Traffic (monthly)</td><td>{org_traffic:,.0f}</td></tr>
                <tr><td>Paid Keywords</td><td>{paid_kw:,}</td></tr>
            </table>

            <h2>12-Month Historical Trend</h2>
            <table>
                <tr><th>Date</th><th>Keywords</th><th>Traffic</th></tr>
                {hist_rows}
            </table>
        </div>

        <div class="page">
            <h2>Top Performing Pages</h2>
            <table>
                <tr><th>Page</th><th>Keywords</th><th>Traffic</th></tr>
                {page_rows}
            </table>

            <h2>Technology Stack</h2>
            {tech_html}
        </div>
        """

    # =========================================================================
    # KEYWORD ANALYSIS
    # =========================================================================

    def _build_keyword_analysis(self, analysis_data: Dict) -> str:
        """Build keyword analysis with real data."""
        phase2 = analysis_data.get("phase2_keywords", {})
        ranked = phase2.get("ranked_keywords", [])[:50]
        gaps = phase2.get("keyword_gaps", [])[:30]
        clusters = phase2.get("keyword_clusters", [])

        # Track data
        has_ranked = self.confidence.track("ranked_keywords", "keywords", "raw_data", len(ranked) > 0)
        has_gaps = self.confidence.track("keyword_gaps", "keywords", "raw_data", len(gaps) > 0)

        # Ranked keywords table
        ranked_rows = ""
        if ranked:
            for kw in ranked:
                pos = kw.get('position') or kw.get('rank_absolute') or '-'
                vol = kw.get('search_volume') or 0
                traffic = kw.get('etv') or kw.get('traffic') or 0
                ranked_rows += f"""<tr>
                    <td>{html.escape(str(kw.get('keyword', '')))}</td>
                    <td>{pos}</td>
                    <td>{vol:,}</td>
                    <td>{traffic:,.0f}</td>
                </tr>"""
        else:
            self.confidence.track_fallback("ranked_keywords", "keywords", "missing")
            ranked_rows = f'<tr><td colspan="4">{data_missing_html("Ranked Keywords", "Keyword Analysis")}</td></tr>'

        # Gap keywords table
        gap_rows = ""
        if gaps:
            for g in gaps:
                vol = g.get('search_volume') or 0
                diff = g.get('difficulty') or g.get('keyword_difficulty') or 0
                gap_rows += f"""<tr>
                    <td>{html.escape(str(g.get('keyword', '')))}</td>
                    <td>{vol:,}</td>
                    <td>{diff:.0f}</td>
                </tr>"""
        else:
            self.confidence.track_fallback("keyword_gaps", "keywords", "missing")
            gap_rows = f'<tr><td colspan="3">{data_missing_html("Keyword Gaps", "Keyword Analysis")}</td></tr>'

        return f"""
        <div class="page">
            <h1>Keyword Analysis</h1>

            <h2>Current Keyword Portfolio</h2>
            <p>Top 50 ranking keywords by traffic value:</p>
            <table>
                <tr><th>Keyword</th><th>Position</th><th>Volume</th><th>Traffic</th></tr>
                {ranked_rows}
            </table>
        </div>

        <div class="page">
            <h2>Keyword Gap Opportunities</h2>
            <p>High-opportunity keywords where competitors rank but you don't:</p>
            <table>
                <tr><th>Keyword</th><th>Volume</th><th>Difficulty</th></tr>
                {gap_rows}
            </table>

            <h2>Keyword Clusters</h2>
            <p><strong>{len(clusters)}</strong> topical clusters identified for content strategy.</p>
        </div>
        """

    # =========================================================================
    # COMPETITIVE ANALYSIS
    # =========================================================================

    def _build_competitive_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build competitive analysis with real data."""
        phase1 = analysis_data.get("phase1_foundation", {})
        phase3 = analysis_data.get("phase3_competitive", {})
        competitors = phase1.get("competitors", [])[:10]

        # Track data
        has_competitors = self.confidence.track("competitors", "competitive", "raw_data", len(competitors) > 0)

        # Competitor table
        comp_rows = ""
        if competitors:
            for c in competitors:
                comp_type = c.get('competitor_type', 'unknown')
                common_kw = c.get('common_keywords') or c.get('se_keywords') or 0
                traffic = c.get('organic_traffic') or c.get('etv') or 0
                dr = c.get('domain_rating') or c.get('rank') or '-'
                comp_rows += f"""<tr>
                    <td>{html.escape(str(c.get('domain', '')))}</td>
                    <td>{comp_type}</td>
                    <td>{common_kw:,}</td>
                    <td>{traffic:,.0f}</td>
                    <td>{dr}</td>
                </tr>"""
        else:
            self.confidence.track_fallback("competitors", "competitive", "missing")
            comp_rows = f'<tr><td colspan="5">{data_missing_html("Competitor Data", "Competitive Analysis")}</td></tr>'

        # AI competitive insights
        comp_insights = ""
        if analysis_result and hasattr(analysis_result, 'loop1_findings'):
            findings = analysis_result.loop1_findings
            if findings and len(findings) > 100:
                comp_insights = f'<div class="data-box">{html.escape(findings[:2000])}</div>'
                self.confidence.track("competitive_insights", "competitive", "agent", True)
            else:
                self.confidence.track("competitive_insights", "competitive", "agent", False)
                comp_insights = data_missing_html("AI Competitive Insights", "Competitive Analysis")
        else:
            self.confidence.track("competitive_insights", "competitive", "agent", False)
            comp_insights = data_missing_html("AI Competitive Insights", "Competitive Analysis")

        return f"""
        <div class="page">
            <h1>Competitive Analysis</h1>

            <h2>Competitor Profiles</h2>
            <table>
                <tr><th>Competitor</th><th>Type</th><th>Shared Keywords</th><th>Traffic</th><th>DR</th></tr>
                {comp_rows}
            </table>

            <h2>Competitive Position Analysis</h2>
            {comp_insights}
        </div>
        """

    # =========================================================================
    # BACKLINK ANALYSIS
    # =========================================================================

    def _build_backlink_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build backlink analysis with real data."""
        phase1 = analysis_data.get("phase1_foundation", {})
        phase3 = analysis_data.get("phase3_competitive", {})
        backlinks = phase1.get("backlink_summary", {})
        top_links = phase3.get("top_backlinks", [])[:15]
        referring_domains = phase3.get("referring_domains", [])[:15]

        # Track data
        has_backlinks = self.confidence.track("backlink_summary", "backlinks", "raw_data", bool(backlinks))
        has_top_links = self.confidence.track("top_backlinks", "backlinks", "raw_data", len(top_links) > 0)

        # Summary metrics
        total_bl = backlinks.get('total_backlinks') or 0
        ref_domains = backlinks.get('referring_domains') or 0
        domain_rank = backlinks.get('domain_rank') or 0

        # Top backlinks table
        link_rows = ""
        if top_links:
            for bl in top_links:
                source = bl.get('domain_from') or bl.get('source_domain') or ''
                dr = bl.get('domain_from_rank') or bl.get('rank') or '-'
                anchor = bl.get('anchor') or ''
                link_rows += f"""<tr>
                    <td>{html.escape(str(source)[:40])}</td>
                    <td>{dr}</td>
                    <td>{html.escape(str(anchor)[:30])}</td>
                </tr>"""
        else:
            link_rows = f'<tr><td colspan="3">{data_missing_html("Top Backlinks", "Backlink Analysis")}</td></tr>'

        return f"""
        <div class="page">
            <h1>Backlink Analysis</h1>

            <h2>Link Profile Summary</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{total_bl:,}</div>
                    <div class="label">Total Backlinks</div>
                </div>
                <div class="metric-card">
                    <div class="value">{ref_domains:,}</div>
                    <div class="label">Referring Domains</div>
                </div>
                <div class="metric-card">
                    <div class="value">{domain_rank}</div>
                    <div class="label">Domain Rating</div>
                </div>
            </div>

            <h2>Top Referring Domains</h2>
            <table>
                <tr><th>Source Domain</th><th>DR</th><th>Anchor Text</th></tr>
                {link_rows}
            </table>
        </div>
        """

    # =========================================================================
    # CONTENT STRATEGY
    # =========================================================================

    def _build_content_strategy(self, analysis_result: Any, analysis_data: Dict) -> str:
        """Build content strategy from AI analysis."""
        # Get Loop 3 enrichment (content strategy)
        content_strategy = None
        if analysis_result:
            content_strategy = getattr(analysis_result, 'loop3_enrichment', None)

        has_strategy = self.confidence.track(
            "content_strategy", "content", "agent", bool(content_strategy) and len(str(content_strategy)) > 100
        )

        if content_strategy and len(str(content_strategy)) > 100:
            strategy_html = f'<div class="data-box">{html.escape(str(content_strategy)[:4000])}</div>'
        else:
            self.confidence.track_fallback("content_strategy", "content", "missing")
            strategy_html = data_missing_html("AI Content Strategy", "Content Strategy")

        return f"""
        <div class="page">
            <h1>Content Strategy</h1>

            <h2>Strategic Content Recommendations</h2>
            {strategy_html}
        </div>
        """

    # =========================================================================
    # TECHNICAL ANALYSIS
    # =========================================================================

    def _build_technical_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build technical SEO analysis."""
        phase1 = analysis_data.get("phase1_foundation", {})
        phase4 = analysis_data.get("phase4_ai_technical", {})
        technical = phase1.get("technical_baseline", {})

        # Track data
        has_technical = self.confidence.track("technical_baseline", "technical", "raw_data", bool(technical))

        # Scores
        perf = technical.get('performance_score') or 0
        access = technical.get('accessibility_score') or 0
        bp = technical.get('best_practices_score') or 0
        seo = technical.get('seo_score') or 0

        # Core Web Vitals
        lcp = technical.get('lcp') or 'N/A'
        fid = technical.get('fid') or 'N/A'
        cls_val = technical.get('cls') or 'N/A'

        if isinstance(lcp, (int, float)):
            lcp = f"{lcp:.1f}s"
        if isinstance(fid, (int, float)):
            fid = f"{fid:.0f}ms"
        if isinstance(cls_val, (int, float)):
            cls_val = f"{cls_val:.3f}"

        def status(score):
            if score >= 0.9:
                return "✓ Good"
            elif score >= 0.5:
                return "⚠ Needs Work"
            else:
                return "✗ Poor"

        return f"""
        <div class="page">
            <h1>Technical SEO Analysis</h1>

            <h2>Lighthouse Scores</h2>
            <table>
                <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
                <tr><td>Performance</td><td>{perf:.0%}</td><td>{status(perf)}</td></tr>
                <tr><td>Accessibility</td><td>{access:.0%}</td><td>{status(access)}</td></tr>
                <tr><td>Best Practices</td><td>{bp:.0%}</td><td>{status(bp)}</td></tr>
                <tr><td>SEO</td><td>{seo:.0%}</td><td>{status(seo)}</td></tr>
            </table>

            <h2>Core Web Vitals</h2>
            <table>
                <tr><th>Metric</th><th>Value</th><th>Good</th><th>Needs Work</th></tr>
                <tr><td>LCP (Largest Contentful Paint)</td><td>{lcp}</td><td>&lt; 2.5s</td><td>&gt; 4.0s</td></tr>
                <tr><td>FID (First Input Delay)</td><td>{fid}</td><td>&lt; 100ms</td><td>&gt; 300ms</td></tr>
                <tr><td>CLS (Cumulative Layout Shift)</td><td>{cls_val}</td><td>&lt; 0.1</td><td>&gt; 0.25</td></tr>
            </table>
        </div>
        """

    # =========================================================================
    # AI VISIBILITY
    # =========================================================================

    def _build_ai_visibility(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build AI visibility analysis."""
        phase4 = analysis_data.get("phase4_ai_technical", {})
        ai_visibility = phase4.get("ai_visibility", {})

        # Track data
        has_ai_data = self.confidence.track("ai_visibility_data", "ai_visibility", "raw_data", bool(ai_visibility))

        # Extract metrics if available
        ai_score = ai_visibility.get("visibility_score") or ai_visibility.get("ai_visibility_score") or "N/A"
        mentions = ai_visibility.get("mention_count") or 0

        return f"""
        <div class="page">
            <h1>AI Visibility Analysis</h1>

            <h2>Why AI Visibility Matters</h2>
            <p>As AI-powered search (Google AI Overviews, ChatGPT, Perplexity) becomes more prevalent,
            being cited in AI-generated responses is increasingly critical for brand visibility.</p>

            <div class="metric-grid" style="grid-template-columns: repeat(2, 1fr);">
                <div class="metric-card">
                    <div class="value">{ai_score}</div>
                    <div class="label">AI Visibility Score</div>
                </div>
                <div class="metric-card">
                    <div class="value">{mentions}</div>
                    <div class="label">AI Mentions Detected</div>
                </div>
            </div>

            <h2>GEO (Generative Engine Optimization)</h2>
            <p>To improve AI visibility, focus on:</p>
            <ul>
                <li>Creating comprehensive, factual content that AI can cite</li>
                <li>Structuring content with clear headings and FAQ sections</li>
                <li>Building topical authority in your niche</li>
                <li>Implementing schema markup for entity recognition</li>
            </ul>
        </div>
        """

    # =========================================================================
    # STRATEGIC ROADMAP
    # =========================================================================

    def _build_strategic_roadmap(self, analysis_result: Any) -> str:
        """Build strategic roadmap from AI analysis."""
        # Get Loop 2 strategy
        strategy = None
        if analysis_result:
            strategy = getattr(analysis_result, 'loop2_strategy', None)

        has_strategy = self.confidence.track(
            "strategic_roadmap", "roadmap", "agent", bool(strategy) and len(str(strategy)) > 100
        )

        if strategy and len(str(strategy)) > 100:
            strategy_html = f'<div class="data-box">{html.escape(str(strategy)[:5000])}</div>'
        else:
            self.confidence.track_fallback("strategic_roadmap", "roadmap", "missing")
            strategy_html = data_missing_html("AI Strategic Recommendations", "Strategic Roadmap")

        return f"""
        <div class="page">
            <h1>Strategic Roadmap</h1>

            <h2>AI-Generated Strategy</h2>
            {strategy_html}
        </div>
        """

    # =========================================================================
    # METHODOLOGY
    # =========================================================================

    def _build_methodology(self, domain: str) -> str:
        """Build methodology section."""
        date = datetime.now().strftime("%B %d, %Y")
        return f"""
        <div class="page">
            <h1>Methodology</h1>

            <h2>Data Sources</h2>
            <ul>
                <li><strong>Organic Rankings:</strong> DataForSEO API</li>
                <li><strong>Backlink Data:</strong> DataForSEO Backlinks API</li>
                <li><strong>Technical Audits:</strong> Lighthouse & On-Page Analysis</li>
                <li><strong>AI Analysis:</strong> Claude AI (Anthropic)</li>
            </ul>

            <h2>Analysis Pipeline</h2>
            <table>
                <tr><th>Phase</th><th>Description</th></tr>
                <tr><td>Data Collection</td><td>60+ API endpoints across 4 phases</td></tr>
                <tr><td>Quality Validation</td><td>Data quality scoring before AI analysis</td></tr>
                <tr><td>AI Analysis</td><td>4-loop analysis architecture</td></tr>
                <tr><td>Report Generation</td><td>Confidence-tracked report building</td></tr>
            </table>

            <h2>Data Freshness</h2>
            <p>Data collected on {date}. Rankings and traffic estimates may fluctuate.</p>

            <div class="confidential" style="margin-top: 40px; text-align: center;">
                © {datetime.now().year} Authoricy. All rights reserved.
            </div>
        </div>
        """
