"""
SEO Strategy Report Builder - Premium Edition

Enterprise-grade PDF report with visual data storytelling.

Features:
- Premium cover page with gradient branding
- SVG trend charts for historical data
- Visual score gauges and progress bars
- Professional metric cards
- AI content sections with visual badges
- Confidence tracking with visual indicators
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, TYPE_CHECKING
from datetime import datetime
import html

from .confidence import ReportConfidence, data_missing_html
from .charts import ChartGenerator

if TYPE_CHECKING:
    from ..agents.base import AgentOutput

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Builds premium SEO strategy reports with visual data storytelling.
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.confidence = ReportConfidence()
        self.charts = ChartGenerator()
        self.section_num = 0

    def build(
        self,
        analysis_result: Any,
        analysis_data: Dict[str, Any],
    ) -> Tuple[str, ReportConfidence]:
        """
        Build complete HTML report with premium design.

        Returns:
            Tuple of (HTML document, ReportConfidence)
        """
        self.confidence = ReportConfidence()
        self.section_num = 0

        metadata = analysis_data.get("metadata", {})
        domain = metadata.get("domain", "Unknown")
        market = metadata.get("market", "Unknown")

        # Track basic data presence
        self.confidence.track("metadata", "global", "raw_data", bool(metadata))
        self.confidence.track("analysis_result", "global", "agent", analysis_result is not None)

        sections = [
            self._build_cover(domain, market, analysis_data),
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

        # Add confidence warning after cover if score is low
        confidence_warning = self.confidence.generate_warning_html()
        if confidence_warning:
            sections.insert(1, f'<div class="page">{confidence_warning}</div>')

        # Log confidence
        conf_data = self.confidence.to_dict()
        logger.info(
            f"Report confidence: {conf_data['confidence_level']} ({conf_data['confidence_score']:.0f}%), "
            f"fallbacks: {conf_data['fallback_count']}, missing: {len(conf_data['missing_required'])}"
        )

        return self._wrap_html(sections, domain), self.confidence

    def _wrap_html(self, sections: list, domain: str) -> str:
        """Wrap sections in HTML document."""
        content = "\n".join(sections)
        css_path = self.template_dir / "components" / "styles.css"

        # Read external CSS
        css_content = ""
        if css_path.exists():
            css_content = css_path.read_text()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(domain)} - SEO Strategy Report</title>
    <style>{css_content}</style>
</head>
<body>
    {content}
</body>
</html>"""

    def _next_section(self) -> int:
        """Get next section number."""
        self.section_num += 1
        return self.section_num

    def _section_header(self, title: str) -> str:
        """Create a visual section header."""
        num = self._next_section()
        return f'''
        <div class="section-header">
            <h1><span class="section-number">{num}</span>{html.escape(title)}</h1>
        </div>
        '''

    def _progress_bar(self, value: float, max_val: float = 100, color_class: str = "") -> str:
        """Generate a progress bar HTML."""
        pct = min(100, (value / max_val) * 100) if max_val > 0 else 0
        fill_class = color_class if color_class else ("success" if pct >= 70 else "warning" if pct >= 40 else "danger")
        return f'''
        <div class="progress-bar">
            <div class="fill {fill_class}" style="width: {pct:.0f}%"></div>
        </div>
        '''

    def _score_badge(self, score: float) -> str:
        """Generate a status badge based on score."""
        if score >= 0.9:
            return '<span class="status-badge good">Excellent</span>'
        elif score >= 0.7:
            return '<span class="status-badge good">Good</span>'
        elif score >= 0.5:
            return '<span class="status-badge warning">Fair</span>'
        else:
            return '<span class="status-badge poor">Poor</span>'

    def _format_number(self, num: Any) -> str:
        """Format number with commas and appropriate precision."""
        if num is None:
            return "N/A"
        try:
            num = float(num)
            if num >= 1_000_000:
                return f"{num/1_000_000:.1f}M"
            elif num >= 1_000:
                return f"{num/1_000:.1f}K"
            elif num == int(num):
                return f"{int(num):,}"
            else:
                return f"{num:,.1f}"
        except (TypeError, ValueError):
            return str(num)

    # =========================================================================
    # COVER PAGE - Premium Design
    # =========================================================================

    def _build_cover(self, domain: str, market: str, analysis_data: Dict) -> str:
        """Build premium cover page with gradient and branding."""
        date = datetime.now().strftime("%B %Y")
        summary = analysis_data.get("summary", {})

        # Quick stats for cover
        keywords = summary.get("total_organic_keywords") or summary.get("ranked_keywords_count") or 0
        traffic = summary.get("total_organic_traffic") or 0

        return f"""
        <div class="page cover">
            <div class="cover-content">
                <div class="logo">AUTHORICY</div>
                <div class="domain-title">{html.escape(domain)}</div>
                <div class="report-type">SEO Strategy Report</div>

                <div class="cover-meta">
                    <div class="meta-item">
                        <div class="meta-label">Market</div>
                        <div class="meta-value">{html.escape(market.upper())}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Date</div>
                        <div class="meta-value">{date}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Keywords</div>
                        <div class="meta-value">{self._format_number(keywords)}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Traffic</div>
                        <div class="meta-value">{self._format_number(traffic)}/mo</div>
                    </div>
                </div>

                <div class="confidential-badge">Confidential</div>
            </div>
        </div>
        """

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================

    def _build_executive_summary(self, analysis_result: Any, analysis_data: Dict) -> str:
        """Build executive summary with key metrics and AI insights."""
        summary = analysis_data.get("summary", {})

        # Get executive summary from AI
        exec_summary = None
        if analysis_result:
            exec_summary = getattr(analysis_result, 'executive_summary', None)

        has_exec_summary = self.confidence.track(
            "executive_summary", "executive_summary", "agent", bool(exec_summary)
        )

        if exec_summary:
            summary_html = f'''
            <div class="ai-content">
                <div class="ai-content-header">
                    <span class="ai-badge">AI Analysis</span>
                    <span style="color: #7c3aed; font-weight: 600;">Executive Summary</span>
                </div>
                <div style="white-space: pre-wrap; line-height: 1.7;">{html.escape(exec_summary[:4000])}</div>
            </div>
            '''
        else:
            self.confidence.track_fallback("executive_summary", "executive_summary", "missing")
            summary_html = data_missing_html("AI Executive Summary", "Executive Summary")

        # Key metrics
        keywords = summary.get("total_organic_keywords") or summary.get("ranked_keywords_count") or 0
        traffic = summary.get("total_organic_traffic") or 0
        dr = summary.get("domain_rank") or 0
        competitors = summary.get("competitor_count") or 0
        backlinks = summary.get("total_backlinks") or 0
        ref_domains = summary.get("referring_domains_count") or 0

        has_any_metrics = (keywords > 0 or traffic > 0 or backlinks > 0 or ref_domains > 0)
        self.confidence.track("summary_metrics", "executive_summary", "raw_data", has_any_metrics)

        return f"""
        <div class="page">
            {self._section_header("Executive Summary")}

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value">{self._format_number(keywords)}</div>
                    <div class="label">Ranking Keywords</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self._format_number(traffic)}</div>
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

            <div class="metric-grid metric-grid-3" style="margin-top: 10px;">
                <div class="metric-card">
                    <div class="value">{self._format_number(backlinks)}</div>
                    <div class="label">Total Backlinks</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self._format_number(ref_domains)}</div>
                    <div class="label">Referring Domains</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self.confidence.confidence_score:.0f}%</div>
                    <div class="label">Data Confidence</div>
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
        """Build domain analysis with trend charts."""
        phase1 = analysis_data.get("phase1_foundation", {})
        overview = phase1.get("domain_overview", {})
        historical = phase1.get("historical_data", [])
        top_pages = phase1.get("top_pages", [])[:15]
        tech = phase1.get("technologies", [])

        # Domain metrics
        org_kw = overview.get('organic_keywords') or 0
        org_traffic = overview.get('organic_traffic') or 0
        paid_kw = overview.get('paid_keywords') or 0

        has_overview_data = bool(overview) and (org_kw > 0 or org_traffic > 0)
        self.confidence.track("domain_overview", "domain_analysis", "raw_data", has_overview_data or len(top_pages) > 0)
        self.confidence.track("historical_data", "domain_analysis", "raw_data", len(historical) > 0)
        self.confidence.track("top_pages", "domain_analysis", "raw_data", len(top_pages) > 0)

        # Generate trend chart if we have historical data
        chart_html = ""
        if historical and len(historical) >= 3:
            chart_data = [
                {"date": h.get('date', ''), "value": h.get('organic_traffic') or h.get('organic_keywords') or 0}
                for h in historical[-12:]
            ]
            chart_svg = self.charts.generate_trend_chart(
                chart_data, x_key="date", y_key="value",
                width=550, height=200, color="#4361ee"
            )
            chart_html = f'''
            <div class="chart-container">
                <div class="chart-title">Organic Traffic Trend (12 Months)</div>
                {chart_svg}
            </div>
            '''
        else:
            chart_html = data_missing_html("Historical Trend Data", "Domain Analysis")

        # Top pages table
        page_rows = ""
        if top_pages:
            for p in top_pages:
                p_kw = p.get('organic_keywords') or 0
                p_traffic = p.get('organic_traffic') or 0
                page_url = str(p.get('page', ''))[:55]
                page_rows += f"""<tr>
                    <td class="keyword">{html.escape(page_url)}</td>
                    <td class="num">{p_kw:,}</td>
                    <td class="num">{p_traffic:,.0f}</td>
                </tr>"""
        else:
            page_rows = f'<tr><td colspan="3">{data_missing_html("Top Pages", "Domain Analysis")}</td></tr>'

        # Technologies
        tech_html = ""
        if tech:
            tech_items = "".join(
                f"<li><strong>{html.escape(t.get('name', 'Unknown'))}</strong> ({html.escape(t.get('category', ''))})</li>"
                for t in tech[:12]
            )
            tech_html = f"<ul>{tech_items}</ul>"
        else:
            tech_html = data_missing_html("Technology Stack", "Domain Analysis")

        return f"""
        <div class="page">
            {self._section_header("Domain Analysis")}

            <h2>Current Organic Performance</h2>
            <div class="metric-grid metric-grid-3">
                <div class="metric-card">
                    <div class="value">{self._format_number(org_kw)}</div>
                    <div class="label">Organic Keywords</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self._format_number(org_traffic)}</div>
                    <div class="label">Organic Traffic</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self._format_number(paid_kw)}</div>
                    <div class="label">Paid Keywords</div>
                </div>
            </div>

            <h2>Historical Performance</h2>
            {chart_html}
        </div>

        <div class="page">
            <h2>Top Performing Pages</h2>
            <table>
                <thead>
                    <tr><th>Page URL</th><th class="num">Keywords</th><th class="num">Traffic</th></tr>
                </thead>
                <tbody>
                    {page_rows}
                </tbody>
            </table>

            <h2>Technology Stack</h2>
            {tech_html}
        </div>
        """

    # =========================================================================
    # KEYWORD ANALYSIS
    # =========================================================================

    def _build_keyword_analysis(self, analysis_data: Dict) -> str:
        """Build keyword analysis with visual indicators."""
        phase2 = analysis_data.get("phase2_keywords", {})
        ranked = phase2.get("ranked_keywords", [])[:40]
        gaps = phase2.get("keyword_gaps", [])[:25]
        clusters = phase2.get("keyword_clusters", [])

        self.confidence.track("ranked_keywords", "keywords", "raw_data", len(ranked) > 0)
        self.confidence.track("keyword_gaps", "keywords", "raw_data", len(gaps) > 0)

        # Ranked keywords table with position indicators
        ranked_rows = ""
        if ranked:
            for kw in ranked:
                pos = kw.get('position') or kw.get('rank_absolute') or 0
                vol = kw.get('search_volume') or 0
                traffic = kw.get('etv') or kw.get('traffic') or 0
                keyword = str(kw.get('keyword', ''))[:45]

                # Position color coding
                if pos <= 3:
                    pos_badge = '<span class="status-badge good">Top 3</span>'
                elif pos <= 10:
                    pos_badge = f'<span class="status-badge good">#{pos}</span>'
                elif pos <= 20:
                    pos_badge = f'<span class="status-badge warning">#{pos}</span>'
                else:
                    pos_badge = f'<span class="status-badge poor">#{pos}</span>'

                ranked_rows += f"""<tr>
                    <td class="keyword">{html.escape(keyword)}</td>
                    <td>{pos_badge}</td>
                    <td class="num">{vol:,}</td>
                    <td class="num">{traffic:,.0f}</td>
                </tr>"""
        else:
            self.confidence.track_fallback("ranked_keywords", "keywords", "missing")
            ranked_rows = f'<tr><td colspan="4">{data_missing_html("Ranked Keywords", "Keyword Analysis")}</td></tr>'

        # Gap keywords with difficulty bar
        gap_rows = ""
        if gaps:
            for g in gaps:
                vol = g.get('search_volume') or 0
                diff = g.get('difficulty') or g.get('keyword_difficulty') or 0
                keyword = str(g.get('keyword', ''))[:45]

                # Difficulty color
                diff_class = "success" if diff < 30 else "warning" if diff < 60 else "danger"

                gap_rows += f"""<tr>
                    <td class="keyword">{html.escape(keyword)}</td>
                    <td class="num">{vol:,}</td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span>{diff:.0f}</span>
                            {self._progress_bar(diff, 100, diff_class)}
                        </div>
                    </td>
                </tr>"""
        else:
            self.confidence.track_fallback("keyword_gaps", "keywords", "missing")
            gap_rows = f'<tr><td colspan="3">{data_missing_html("Keyword Gaps", "Keyword Analysis")}</td></tr>'

        return f"""
        <div class="page">
            {self._section_header("Keyword Analysis")}

            <h2>Current Keyword Portfolio</h2>
            <p>Top ranking keywords by traffic value:</p>
            <table>
                <thead>
                    <tr><th>Keyword</th><th>Position</th><th class="num">Volume</th><th class="num">Traffic</th></tr>
                </thead>
                <tbody>
                    {ranked_rows}
                </tbody>
            </table>
        </div>

        <div class="page">
            <h2>Keyword Gap Opportunities</h2>
            <p>High-opportunity keywords where competitors rank but you don't:</p>
            <table>
                <thead>
                    <tr><th>Keyword</th><th class="num">Volume</th><th>Difficulty</th></tr>
                </thead>
                <tbody>
                    {gap_rows}
                </tbody>
            </table>

            <div class="highlight-box info" style="margin-top: 25px;">
                <div class="highlight-title">Topical Clusters Identified</div>
                <p><strong>{len(clusters)}</strong> content clusters identified for strategic content planning.
                Targeting topical clusters helps build authority and capture more search traffic.</p>
            </div>
        </div>
        """

    # =========================================================================
    # COMPETITIVE ANALYSIS
    # =========================================================================

    def _build_competitive_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build competitive analysis with visual competitor comparison."""
        phase1 = analysis_data.get("phase1_foundation", {})
        competitors = phase1.get("competitors", [])[:10]

        self.confidence.track("competitors", "competitive", "raw_data", len(competitors) > 0)

        # Competitor table with type badges
        comp_rows = ""
        if competitors:
            type_colors = {
                'direct': 'danger',
                'seo': 'warning',
                'content': 'good',
                'emerging': 'warning',
                'aspirational': 'good',
            }
            for c in competitors:
                comp_type = str(c.get('competitor_type', 'unknown')).lower()
                common_kw = c.get('common_keywords') or c.get('se_keywords') or 0
                traffic = c.get('organic_traffic') or c.get('etv') or 0
                dr = c.get('domain_rating') or c.get('rank') or '-'
                domain = str(c.get('domain', ''))[:35]

                badge_class = type_colors.get(comp_type, 'warning')
                type_badge = f'<span class="status-badge {badge_class}">{comp_type.upper()}</span>'

                comp_rows += f"""<tr>
                    <td class="keyword">{html.escape(domain)}</td>
                    <td>{type_badge}</td>
                    <td class="num">{common_kw:,}</td>
                    <td class="num">{self._format_number(traffic)}</td>
                    <td class="num">{dr}</td>
                </tr>"""
        else:
            self.confidence.track_fallback("competitors", "competitive", "missing")
            comp_rows = f'<tr><td colspan="5">{data_missing_html("Competitor Data", "Competitive Analysis")}</td></tr>'

        # AI competitive insights
        comp_insights = ""
        if analysis_result and hasattr(analysis_result, 'loop1_findings'):
            findings = analysis_result.loop1_findings
            if findings and len(findings) > 100:
                comp_insights = f'''
                <div class="ai-content">
                    <div class="ai-content-header">
                        <span class="ai-badge">AI Analysis</span>
                        <span style="color: #7c3aed; font-weight: 600;">Competitive Intelligence</span>
                    </div>
                    <div style="white-space: pre-wrap; line-height: 1.7;">{html.escape(findings[:2500])}</div>
                </div>
                '''
                self.confidence.track("competitive_insights", "competitive", "agent", True)
            else:
                self.confidence.track("competitive_insights", "competitive", "agent", False)
                comp_insights = data_missing_html("AI Competitive Insights", "Competitive Analysis")
        else:
            self.confidence.track("competitive_insights", "competitive", "agent", False)
            comp_insights = data_missing_html("AI Competitive Insights", "Competitive Analysis")

        return f"""
        <div class="page">
            {self._section_header("Competitive Analysis")}

            <h2>Competitor Landscape</h2>
            <table>
                <thead>
                    <tr><th>Competitor</th><th>Type</th><th class="num">Shared KW</th><th class="num">Traffic</th><th class="num">DR</th></tr>
                </thead>
                <tbody>
                    {comp_rows}
                </tbody>
            </table>

            <div class="highlight-box" style="margin-top: 25px;">
                <div class="highlight-title">Competitor Type Legend</div>
                <p>
                    <span class="status-badge danger">DIRECT</span> Same product/service offering &nbsp;
                    <span class="status-badge warning">SEO</span> Competing for keywords &nbsp;
                    <span class="status-badge good">CONTENT</span> Content overlap
                </p>
            </div>

            <h2>Competitive Position Analysis</h2>
            {comp_insights}
        </div>
        """

    # =========================================================================
    # BACKLINK ANALYSIS
    # =========================================================================

    def _build_backlink_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build backlink analysis with visual metrics."""
        phase1 = analysis_data.get("phase1_foundation", {})
        phase3 = analysis_data.get("phase3_competitive", {})
        backlinks = phase1.get("backlink_summary", {})
        top_links = phase3.get("top_backlinks", [])[:12]

        self.confidence.track("backlink_summary", "backlinks", "raw_data", bool(backlinks))
        self.confidence.track("top_backlinks", "backlinks", "raw_data", len(top_links) > 0)

        # Summary metrics
        total_bl = backlinks.get('total_backlinks') or 0
        ref_domains = backlinks.get('referring_domains') or 0
        domain_rank = backlinks.get('domain_rank') or 0

        # Top backlinks table
        link_rows = ""
        if top_links:
            for bl in top_links:
                source = bl.get('domain_from') or bl.get('source_domain') or ''
                dr = bl.get('domain_from_rank') or bl.get('rank') or 0
                anchor = bl.get('anchor') or ''

                # DR badge
                dr_class = "good" if dr >= 50 else "warning" if dr >= 20 else "poor"

                link_rows += f"""<tr>
                    <td class="keyword">{html.escape(str(source)[:40])}</td>
                    <td><span class="status-badge {dr_class}">DR {dr}</span></td>
                    <td>{html.escape(str(anchor)[:35])}</td>
                </tr>"""
        else:
            link_rows = f'<tr><td colspan="3">{data_missing_html("Top Backlinks", "Backlink Analysis")}</td></tr>'

        # Calculate link quality score (if we have data)
        quality_score = min(100, (domain_rank * 1.5)) if domain_rank else 0

        return f"""
        <div class="page">
            {self._section_header("Backlink Analysis")}

            <h2>Link Profile Summary</h2>
            <div class="metric-grid metric-grid-3">
                <div class="metric-card">
                    <div class="value">{self._format_number(total_bl)}</div>
                    <div class="label">Total Backlinks</div>
                </div>
                <div class="metric-card">
                    <div class="value">{self._format_number(ref_domains)}</div>
                    <div class="label">Referring Domains</div>
                </div>
                <div class="metric-card">
                    <div class="value">{domain_rank}</div>
                    <div class="label">Domain Rating</div>
                    {self._progress_bar(quality_score, 100)}
                </div>
            </div>

            <h2>Top Referring Domains</h2>
            <table>
                <thead>
                    <tr><th>Source Domain</th><th>Authority</th><th>Anchor Text</th></tr>
                </thead>
                <tbody>
                    {link_rows}
                </tbody>
            </table>

            <div class="insight-box" style="margin-top: 25px;">
                <h3>Link Building Opportunity</h3>
                <p>Focus on acquiring links from domains with DR 40+ for maximum impact.
                Quality over quantity - one link from a DR 60+ site is worth 10+ low-quality links.</p>
            </div>
        </div>
        """

    # =========================================================================
    # CONTENT STRATEGY
    # =========================================================================

    def _build_content_strategy(self, analysis_result: Any, analysis_data: Dict) -> str:
        """Build content strategy from AI analysis."""
        content_strategy = None
        if analysis_result:
            content_strategy = getattr(analysis_result, 'loop3_enrichment', None)

        has_strategy = self.confidence.track(
            "content_strategy", "content", "agent", bool(content_strategy) and len(str(content_strategy)) > 100
        )

        if content_strategy and len(str(content_strategy)) > 100:
            strategy_html = f'''
            <div class="ai-content">
                <div class="ai-content-header">
                    <span class="ai-badge">AI Analysis</span>
                    <span style="color: #7c3aed; font-weight: 600;">Content Strategy Recommendations</span>
                </div>
                <div style="white-space: pre-wrap; line-height: 1.7;">{html.escape(str(content_strategy)[:4000])}</div>
            </div>
            '''
        else:
            self.confidence.track_fallback("content_strategy", "content", "missing")
            strategy_html = data_missing_html("AI Content Strategy", "Content Strategy")

        return f"""
        <div class="page">
            {self._section_header("Content Strategy")}

            <h2>Strategic Content Recommendations</h2>
            {strategy_html}

            <div class="highlight-box success" style="margin-top: 25px;">
                <div class="highlight-title">Content Pillars</div>
                <p>Build topical authority by creating comprehensive content pillars around your core topics.
                Each pillar should link to related cluster content to maximize internal linking value.</p>
            </div>
        </div>
        """

    # =========================================================================
    # TECHNICAL ANALYSIS
    # =========================================================================

    def _build_technical_analysis(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build technical SEO analysis with visual scores."""
        phase1 = analysis_data.get("phase1_foundation", {})
        technical = phase1.get("technical_baseline", {})

        self.confidence.track("technical_baseline", "technical", "raw_data", bool(technical))

        # Scores (normalize to 0-1 if needed)
        perf = technical.get('performance_score') or 0
        access = technical.get('accessibility_score') or 0
        bp = technical.get('best_practices_score') or 0
        seo = technical.get('seo_score') or 0

        # Core Web Vitals
        lcp = technical.get('lcp') or 'N/A'
        fid = technical.get('fid') or 'N/A'
        cls_val = technical.get('cls') or 'N/A'

        def format_cwv(val, suffix=""):
            if isinstance(val, (int, float)):
                return f"{val:.2f}{suffix}"
            return str(val)

        def score_to_class(score):
            if score >= 0.9:
                return "excellent"
            elif score >= 0.7:
                return "good"
            elif score >= 0.5:
                return "fair"
            return "poor"

        return f"""
        <div class="page">
            {self._section_header("Technical SEO Analysis")}

            <h2>Performance Scores</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="value {score_to_class(perf)}">{perf:.0%}</div>
                    <div class="label">Performance</div>
                    {self._progress_bar(perf * 100, 100)}
                </div>
                <div class="metric-card">
                    <div class="value {score_to_class(access)}">{access:.0%}</div>
                    <div class="label">Accessibility</div>
                    {self._progress_bar(access * 100, 100)}
                </div>
                <div class="metric-card">
                    <div class="value {score_to_class(bp)}">{bp:.0%}</div>
                    <div class="label">Best Practices</div>
                    {self._progress_bar(bp * 100, 100)}
                </div>
                <div class="metric-card">
                    <div class="value {score_to_class(seo)}">{seo:.0%}</div>
                    <div class="label">SEO</div>
                    {self._progress_bar(seo * 100, 100)}
                </div>
            </div>

            <h2>Core Web Vitals</h2>
            <table>
                <thead>
                    <tr><th>Metric</th><th>Value</th><th>Target (Good)</th><th>Status</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>LCP</strong> (Largest Contentful Paint)</td>
                        <td class="num">{format_cwv(lcp, 's') if isinstance(lcp, (int, float)) else lcp}</td>
                        <td class="num">&lt; 2.5s</td>
                        <td>{self._score_badge(0.9 if isinstance(lcp, (int, float)) and lcp < 2.5 else 0.5 if isinstance(lcp, (int, float)) and lcp < 4 else 0.3)}</td>
                    </tr>
                    <tr>
                        <td><strong>FID</strong> (First Input Delay)</td>
                        <td class="num">{format_cwv(fid, 'ms') if isinstance(fid, (int, float)) else fid}</td>
                        <td class="num">&lt; 100ms</td>
                        <td>{self._score_badge(0.9 if isinstance(fid, (int, float)) and fid < 100 else 0.5 if isinstance(fid, (int, float)) and fid < 300 else 0.3)}</td>
                    </tr>
                    <tr>
                        <td><strong>CLS</strong> (Cumulative Layout Shift)</td>
                        <td class="num">{format_cwv(cls_val)}</td>
                        <td class="num">&lt; 0.1</td>
                        <td>{self._score_badge(0.9 if isinstance(cls_val, (int, float)) and cls_val < 0.1 else 0.5 if isinstance(cls_val, (int, float)) and cls_val < 0.25 else 0.3)}</td>
                    </tr>
                </tbody>
            </table>

            <div class="highlight-box warning" style="margin-top: 25px;">
                <div class="highlight-title">Technical SEO Priority</div>
                <p>Core Web Vitals are now a ranking factor. Focus on improving LCP and CLS for better user experience and search visibility.</p>
            </div>
        </div>
        """

    # =========================================================================
    # AI VISIBILITY
    # =========================================================================

    def _build_ai_visibility(self, analysis_data: Dict, analysis_result: Any) -> str:
        """Build AI visibility analysis."""
        phase4 = analysis_data.get("phase4_ai_technical", {})
        ai_visibility = phase4.get("ai_visibility", {})

        self.confidence.track("ai_visibility_data", "ai_visibility", "raw_data", bool(ai_visibility))

        ai_score = ai_visibility.get("visibility_score") or ai_visibility.get("ai_visibility_score") or "N/A"
        mentions = ai_visibility.get("mention_count") or 0

        return f"""
        <div class="page">
            {self._section_header("AI Visibility & GEO")}

            <h2>Why AI Visibility Matters</h2>
            <div class="highlight-box info">
                <p>As AI-powered search (Google AI Overviews, ChatGPT, Perplexity, Claude) becomes more prevalent,
                being cited in AI-generated responses is increasingly critical for brand visibility and traffic.</p>
            </div>

            <div class="metric-grid metric-grid-2">
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
            <div class="roadmap-phase">
                <h3>Key Optimization Strategies</h3>
                <div class="roadmap-item">Create comprehensive, factual content that AI systems can confidently cite</div>
                <div class="roadmap-item">Structure content with clear headings, FAQ sections, and schema markup</div>
                <div class="roadmap-item">Build topical authority through content depth and internal linking</div>
                <div class="roadmap-item">Implement structured data for enhanced entity recognition</div>
                <div class="roadmap-item">Optimize for featured snippets and knowledge panels</div>
            </div>

            <div class="insight-box" style="margin-top: 25px;">
                <h3>Future-Proof Your SEO</h3>
                <p>Traditional SEO and GEO work together. Content optimized for search engines
                is more likely to be cited by AI systems. Focus on E-E-A-T (Experience, Expertise,
                Authoritativeness, Trustworthiness) to succeed in both paradigms.</p>
            </div>
        </div>
        """

    # =========================================================================
    # STRATEGIC ROADMAP
    # =========================================================================

    def _build_strategic_roadmap(self, analysis_result: Any) -> str:
        """Build strategic roadmap from AI analysis."""
        strategy = None
        if analysis_result:
            strategy = getattr(analysis_result, 'loop2_strategy', None)

        has_strategy = self.confidence.track(
            "strategic_roadmap", "roadmap", "agent", bool(strategy) and len(str(strategy)) > 100
        )

        if strategy and len(str(strategy)) > 100:
            strategy_html = f'''
            <div class="ai-content">
                <div class="ai-content-header">
                    <span class="ai-badge">AI Analysis</span>
                    <span style="color: #7c3aed; font-weight: 600;">Strategic Recommendations</span>
                </div>
                <div style="white-space: pre-wrap; line-height: 1.7;">{html.escape(str(strategy)[:5000])}</div>
            </div>
            '''
        else:
            self.confidence.track_fallback("strategic_roadmap", "roadmap", "missing")
            strategy_html = data_missing_html("AI Strategic Recommendations", "Strategic Roadmap")

        return f"""
        <div class="page">
            {self._section_header("Strategic Roadmap")}

            <h2>AI-Generated Strategy</h2>
            {strategy_html}

            <div class="cta-box" style="margin-top: 40px;">
                <h3>Ready to Implement?</h3>
                <p>Contact Authoricy to discuss how we can help execute this strategy
                and drive measurable improvements in your organic search performance.</p>
            </div>
        </div>
        """

    # =========================================================================
    # METHODOLOGY
    # =========================================================================

    def _build_methodology(self, domain: str) -> str:
        """Build methodology section."""
        date = datetime.now().strftime("%B %d, %Y")
        year = datetime.now().year

        return f"""
        <div class="page">
            {self._section_header("Methodology")}

            <h2>Data Sources</h2>
            <table>
                <thead>
                    <tr><th>Data Type</th><th>Source</th><th>Coverage</th></tr>
                </thead>
                <tbody>
                    <tr><td>Organic Rankings</td><td>DataForSEO API</td><td>Real-time SERP data</td></tr>
                    <tr><td>Backlink Data</td><td>DataForSEO Backlinks API</td><td>Web-scale link index</td></tr>
                    <tr><td>Technical Audits</td><td>Lighthouse & On-Page Analysis</td><td>Full site crawl</td></tr>
                    <tr><td>AI Analysis</td><td>Claude AI (Anthropic)</td><td>Strategic insights</td></tr>
                </tbody>
            </table>

            <h2>Analysis Pipeline</h2>
            <div class="roadmap-phase">
                <div class="roadmap-item"><span class="phase-badge">Phase 1</span> Foundation data collection (domain overview, backlinks, competitors)</div>
                <div class="roadmap-item"><span class="phase-badge">Phase 2</span> Keyword intelligence (rankings, gaps, opportunities)</div>
                <div class="roadmap-item"><span class="phase-badge">Phase 3</span> Competitive deep-dive (SERP analysis, content gaps)</div>
                <div class="roadmap-item"><span class="phase-badge">Phase 4</span> Technical & AI visibility assessment</div>
                <div class="roadmap-item"><span class="phase-badge">AI Loop</span> 4-stage AI analysis with quality validation</div>
            </div>

            <h2>Report Confidence</h2>
            <div class="highlight-box">
                <div class="highlight-title">Data Quality Score: {self.confidence.confidence_score:.0f}%</div>
                <p>This report's confidence level is <strong>{self.confidence.confidence_level}</strong>.
                Confidence is calculated based on data completeness, freshness, and AI analysis quality.</p>
            </div>

            <div style="margin-top: 50px; text-align: center; color: #94a3b8;">
                <p>Data collected on {date}</p>
                <p style="margin-top: 30px; font-size: 9pt;">
                    &copy; {year} Authoricy. All rights reserved.<br>
                    This report is confidential and intended solely for the recipient.
                </p>
            </div>
        </div>
        """
