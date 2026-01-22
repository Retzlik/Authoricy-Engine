"""
Agent Output Converter

Converts raw agent output into validated, structured data ready for report generation.
Integrates parsing, quality validation, and schema enforcement.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .parser import OutputParser, ParseResult, ParsedFinding, ParsedRecommendation
from .schemas import get_schema, validate_output, AGENT_SCHEMAS
from ..quality.checks import AgentQualityChecker, CheckResult
from ..agents.base import AgentOutput, Finding, Recommendation

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of converting raw output to structured data."""
    success: bool
    agent_output: Optional[AgentOutput]
    quality_score: float
    quality_passed: bool
    checks_passed: int
    checks_failed: int
    failed_checks: List[str]
    parse_method: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AgentOutputConverter:
    """
    Converts raw agent output to validated, structured AgentOutput.

    Workflow:
    1. Parse raw text using OutputParser (XML/JSON/Markdown)
    2. Extract agent-specific structures (executive_summary, priority_stack, etc.)
    3. Run 25 quality checks
    4. Convert to AgentOutput data class
    5. Validate against schema

    Usage:
        converter = AgentOutputConverter()
        result = converter.convert(
            agent_name="keyword_intelligence",
            raw_output="<finding>...</finding>",
            context={"domain": "example.com"}
        )
        if result.success:
            agent_output = result.agent_output
    """

    def __init__(self):
        """Initialize converter with parser and quality checker."""
        self.parser = OutputParser()
        self.quality_checker = AgentQualityChecker()

    def convert(
        self,
        agent_name: str,
        raw_output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ConversionResult:
        """
        Convert raw agent output to structured AgentOutput.

        Args:
            agent_name: Agent identifier (e.g., "keyword_intelligence")
            raw_output: Raw text output from Claude
            context: Optional context (domain, etc.) for quality checks

        Returns:
            ConversionResult with AgentOutput if successful
        """
        errors = []
        warnings = []
        context = context or {}

        # Step 1: Parse raw output
        parse_result = self.parser.parse(raw_output)

        if not parse_result.success:
            errors.append(f"Parsing failed: {parse_result.errors}")
            logger.warning(f"Failed to parse {agent_name} output")

        # Step 2: Extract agent-specific structures
        agent_data = self._extract_agent_specific(agent_name, raw_output, parse_result)

        # Step 3: Run quality checks
        check_results = self.quality_checker.run_all_checks(
            raw_output,
            {"parsed": parse_result, "agent_data": agent_data, **context}
        )
        quality_score = self.quality_checker.calculate_score(check_results)
        quality_passed = self.quality_checker.passes_gate(check_results)
        failed_checks = [r.name for r in check_results if not r.passed]

        if not quality_passed:
            warnings.append(f"Quality gate failed: {len(failed_checks)} checks failed")

        # Step 4: Convert to AgentOutput
        findings = self._convert_findings(parse_result.findings, agent_data)
        recommendations = self._convert_recommendations(parse_result.recommendations, agent_data)
        metrics = self._merge_metrics(parse_result.metrics, agent_data)

        agent_output = AgentOutput(
            agent_name=agent_name,
            display_name=self._get_display_name(agent_name),
            timestamp=datetime.now(),
            findings=findings,
            recommendations=recommendations,
            metrics=metrics,
            quality_score=quality_score,
            quality_checks={r.name: r.passed for r in check_results},
            checks_passed=sum(1 for r in check_results if r.passed),
            checks_failed=sum(1 for r in check_results if not r.passed),
            raw_output=raw_output,
            structured_data=agent_data,
            confidence=self._calculate_confidence(parse_result, check_results),
            tokens_used=0,  # Set by caller
            cost_usd=0.0,  # Set by caller
            processing_time_seconds=0.0,  # Set by caller
        )

        # Step 5: Validate against schema
        schema_valid, schema_errors = validate_output(agent_name, {
            "findings": [f.__dict__ for f in findings],
            "recommendations": [r.__dict__ for r in recommendations],
            "metrics": metrics,
        })

        if not schema_valid:
            warnings.extend(schema_errors)

        return ConversionResult(
            success=parse_result.success or bool(findings) or bool(recommendations),
            agent_output=agent_output,
            quality_score=quality_score,
            quality_passed=quality_passed,
            checks_passed=sum(1 for r in check_results if r.passed),
            checks_failed=sum(1 for r in check_results if not r.passed),
            failed_checks=failed_checks,
            parse_method=parse_result.parse_method,
            errors=errors,
            warnings=warnings,
        )

    # =========================================================================
    # AGENT-SPECIFIC EXTRACTION
    # =========================================================================

    def _extract_agent_specific(
        self,
        agent_name: str,
        raw_output: str,
        parse_result: ParseResult
    ) -> Dict[str, Any]:
        """Extract agent-specific structured data."""
        extractors = {
            "keyword_intelligence": self._extract_keyword_data,
            "backlink_intelligence": self._extract_backlink_data,
            "technical_seo": self._extract_technical_data,
            "content_analysis": self._extract_content_data,
            "semantic_architecture": self._extract_semantic_data,
            "ai_visibility": self._extract_ai_visibility_data,
            "serp_analysis": self._extract_serp_data,
            "local_seo": self._extract_local_data,
            "master_strategy": self._extract_master_data,
        }

        extractor = extractors.get(agent_name)
        if extractor:
            return extractor(raw_output, parse_result)
        return {}

    def _extract_keyword_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract keyword intelligence specific data."""
        data = {}

        # Extract opportunity keywords
        opportunities = self._extract_xml_list(text, "opportunity")
        if opportunities:
            data["opportunities"] = [self._parse_keyword_opportunity(o) for o in opportunities]

        # Extract quick wins
        quick_wins = self._extract_xml_list(text, "quick_win")
        if quick_wins:
            data["quick_wins"] = [self._parse_keyword_opportunity(q) for q in quick_wins]

        # Extract portfolio health
        portfolio = self._extract_xml_block(text, "portfolio_health")
        if portfolio:
            data["portfolio_health"] = self._parse_portfolio_health(portfolio)

        return data

    def _extract_backlink_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract backlink intelligence specific data."""
        data = {}

        # Extract link profile health
        profile = self._extract_xml_block(text, "link_profile")
        if profile:
            data["link_profile"] = self._parse_link_profile(profile)

        # Extract target domains
        targets = self._extract_xml_list(text, "target_domain")
        if targets:
            data["target_domains"] = [self._parse_target_domain(t) for t in targets]

        # Extract anchor distribution
        anchors = self._extract_xml_block(text, "anchor_distribution")
        if anchors:
            data["anchor_distribution"] = self._parse_anchor_distribution(anchors)

        return data

    def _extract_technical_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract technical SEO specific data."""
        data = {}

        # Extract Core Web Vitals
        cwv = self._extract_xml_block(text, "core_web_vitals")
        if cwv:
            data["core_web_vitals"] = self._parse_cwv(cwv)

        # Extract critical issues
        issues = self._extract_xml_list(text, "critical_issue")
        if issues:
            data["critical_issues"] = [self._parse_technical_issue(i) for i in issues]

        # Extract crawl issues
        crawl = self._extract_xml_block(text, "crawl_analysis")
        if crawl:
            data["crawl_analysis"] = self._parse_crawl_data(crawl)

        return data

    def _extract_content_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract content analysis specific data."""
        data = {}

        # Extract decay items
        decay_items = self._extract_xml_list(text, "decay_item")
        if decay_items:
            data["decay_items"] = [self._parse_decay_item(d) for d in decay_items]

        # Extract KUCK recommendations
        kuck = self._extract_xml_list(text, "kuck_recommendation")
        if kuck:
            data["kuck_recommendations"] = [self._parse_kuck_item(k) for k in kuck]

        # Extract content inventory
        inventory = self._extract_xml_block(text, "content_inventory")
        if inventory:
            data["content_inventory"] = self._parse_content_inventory(inventory)

        return data

    def _extract_semantic_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract semantic architecture specific data."""
        data = {}

        # Extract topic clusters
        clusters = self._extract_xml_list(text, "topic_cluster")
        if clusters:
            data["topic_clusters"] = [self._parse_topic_cluster(c) for c in clusters]

        # Extract internal linking opportunities
        links = self._extract_xml_list(text, "internal_link")
        if links:
            data["internal_links"] = [self._parse_internal_link(l) for l in links]

        return data

    def _extract_ai_visibility_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract AI visibility specific data."""
        data = {}

        # Extract GEO recommendations
        geo = self._extract_xml_list(text, "geo_recommendation")
        if geo:
            data["geo_recommendations"] = [self._parse_geo_rec(g) for g in geo]

        # Extract AI overview presence
        ai_overview = self._extract_xml_block(text, "ai_overview_analysis")
        if ai_overview:
            data["ai_overview"] = self._parse_ai_overview(ai_overview)

        return data

    def _extract_serp_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract SERP analysis specific data."""
        data = {}

        # Extract feature opportunities
        features = self._extract_xml_list(text, "serp_feature")
        if features:
            data["serp_features"] = [self._parse_serp_feature(f) for f in features]

        # Extract content format recommendations
        formats = self._extract_xml_list(text, "content_format")
        if formats:
            data["content_formats"] = [self._parse_content_format(f) for f in formats]

        return data

    def _extract_local_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract local SEO specific data."""
        data = {}

        # Extract GBP analysis
        gbp = self._extract_xml_block(text, "gbp_analysis")
        if gbp:
            data["gbp_analysis"] = self._parse_gbp(gbp)

        # Extract citations
        citations = self._extract_xml_list(text, "citation")
        if citations:
            data["citations"] = [self._parse_citation(c) for c in citations]

        return data

    def _extract_master_data(self, text: str, parse_result: ParseResult) -> Dict[str, Any]:
        """Extract master strategy specific data."""
        data = {}

        # Extract executive summary
        exec_summary = self._extract_xml_block(text, "executive_summary")
        if exec_summary:
            data["executive_summary"] = self._parse_executive_summary(exec_summary)

        # Extract priority stack
        priority_items = self._extract_xml_list(text, "priority_stack")
        if priority_items:
            data["priority_stack"] = [self._parse_priority_item(p) for p in priority_items]

        # Extract roadmap phases
        roadmap = self._extract_xml_list(text, "roadmap")
        if roadmap:
            data["roadmap"] = [self._parse_roadmap_phase(r) for r in roadmap]

        # Extract patterns
        patterns = self._extract_xml_list(text, "pattern")
        if patterns:
            data["patterns"] = [self._parse_pattern(p) for p in patterns]

        return data

    # =========================================================================
    # HELPER PARSERS
    # =========================================================================

    def _extract_xml_block(self, text: str, tag: str) -> Optional[str]:
        """Extract content of a single XML block."""
        pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_xml_list(self, text: str, tag: str) -> List[str]:
        """Extract all instances of an XML tag."""
        pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [m.strip() for m in matches]

    def _get_nested_tag(self, text: str, tag: str) -> str:
        """Get content of a nested tag."""
        pattern = rf'<{tag}>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _get_attr(self, text: str, attr: str, default: Any = None) -> Any:
        """Get attribute value from XML tag."""
        pattern = rf'{attr}=["\']([^"\']+)["\']'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else default

    # =========================================================================
    # DATA STRUCTURE PARSERS
    # =========================================================================

    def _parse_keyword_opportunity(self, text: str) -> Dict[str, Any]:
        """Parse a keyword opportunity structure."""
        return {
            "keyword": self._get_nested_tag(text, "keyword"),
            "volume": int(self._get_nested_tag(text, "volume") or 0),
            "difficulty": int(self._get_nested_tag(text, "difficulty") or 0),
            "opportunity_score": int(self._get_nested_tag(text, "opportunity_score") or 0),
            "current_position": self._get_nested_tag(text, "current_position") or None,
            "recommended_action": self._get_nested_tag(text, "action"),
        }

    def _parse_portfolio_health(self, text: str) -> Dict[str, Any]:
        """Parse portfolio health structure."""
        return {
            "total_keywords": int(self._get_nested_tag(text, "total") or 0),
            "health_score": float(self._get_nested_tag(text, "score") or 0),
            "trend": self._get_nested_tag(text, "trend") or "stable",
        }

    def _parse_link_profile(self, text: str) -> Dict[str, Any]:
        """Parse link profile structure."""
        return {
            "domain_rating": int(self._get_nested_tag(text, "dr") or 0),
            "referring_domains": int(self._get_nested_tag(text, "rd") or 0),
            "total_backlinks": int(self._get_nested_tag(text, "backlinks") or 0),
        }

    def _parse_target_domain(self, text: str) -> Dict[str, Any]:
        """Parse target domain for link building."""
        return {
            "domain": self._get_nested_tag(text, "domain"),
            "dr": int(self._get_nested_tag(text, "dr") or 0),
            "traffic": int(self._get_nested_tag(text, "traffic") or 0),
            "contact": self._get_nested_tag(text, "contact"),
            "strategy": self._get_nested_tag(text, "strategy"),
        }

    def _parse_anchor_distribution(self, text: str) -> Dict[str, float]:
        """Parse anchor text distribution."""
        return {
            "branded": float(self._get_nested_tag(text, "branded") or 0),
            "exact_match": float(self._get_nested_tag(text, "exact") or 0),
            "partial_match": float(self._get_nested_tag(text, "partial") or 0),
            "generic": float(self._get_nested_tag(text, "generic") or 0),
        }

    def _parse_cwv(self, text: str) -> Dict[str, Any]:
        """Parse Core Web Vitals data."""
        return {
            "lcp": float(self._get_nested_tag(text, "lcp") or 0),
            "inp": float(self._get_nested_tag(text, "inp") or 0),
            "cls": float(self._get_nested_tag(text, "cls") or 0),
            "status": self._get_nested_tag(text, "status") or "unknown",
        }

    def _parse_technical_issue(self, text: str) -> Dict[str, Any]:
        """Parse a technical issue."""
        return {
            "issue": self._get_nested_tag(text, "issue"),
            "severity": self._get_nested_tag(text, "severity") or "medium",
            "affected_pages": int(self._get_nested_tag(text, "affected") or 0),
            "fix": self._get_nested_tag(text, "fix"),
        }

    def _parse_crawl_data(self, text: str) -> Dict[str, Any]:
        """Parse crawl analysis data."""
        return {
            "pages_crawled": int(self._get_nested_tag(text, "crawled") or 0),
            "blocked_pages": int(self._get_nested_tag(text, "blocked") or 0),
            "errors": int(self._get_nested_tag(text, "errors") or 0),
        }

    def _parse_decay_item(self, text: str) -> Dict[str, Any]:
        """Parse a content decay item."""
        return {
            "url": self._get_nested_tag(text, "url"),
            "decay_score": float(self._get_nested_tag(text, "score") or 0),
            "traffic_loss": int(self._get_nested_tag(text, "loss") or 0),
            "action": self._get_nested_tag(text, "action"),
        }

    def _parse_kuck_item(self, text: str) -> Dict[str, Any]:
        """Parse a KUCK recommendation."""
        return {
            "url": self._get_nested_tag(text, "url"),
            "action": self._get_nested_tag(text, "action"),  # keep/update/consolidate/kill
            "rationale": self._get_nested_tag(text, "rationale"),
            "merge_target": self._get_nested_tag(text, "merge_target"),
        }

    def _parse_content_inventory(self, text: str) -> Dict[str, Any]:
        """Parse content inventory summary."""
        return {
            "total_pages": int(self._get_nested_tag(text, "total") or 0),
            "blog_posts": int(self._get_nested_tag(text, "blogs") or 0),
            "landing_pages": int(self._get_nested_tag(text, "landing") or 0),
            "avg_word_count": int(self._get_nested_tag(text, "avg_words") or 0),
        }

    def _parse_topic_cluster(self, text: str) -> Dict[str, Any]:
        """Parse a topic cluster."""
        return {
            "topic": self._get_nested_tag(text, "topic"),
            "pillar_page": self._get_nested_tag(text, "pillar"),
            "cluster_pages": self._get_nested_tag(text, "pages").split(",") if self._get_nested_tag(text, "pages") else [],
            "coverage": float(self._get_nested_tag(text, "coverage") or 0),
            "gaps": self._get_nested_tag(text, "gaps").split(",") if self._get_nested_tag(text, "gaps") else [],
        }

    def _parse_internal_link(self, text: str) -> Dict[str, Any]:
        """Parse an internal link recommendation."""
        return {
            "source": self._get_nested_tag(text, "source"),
            "target": self._get_nested_tag(text, "target"),
            "anchor": self._get_nested_tag(text, "anchor"),
            "context": self._get_nested_tag(text, "context"),
        }

    def _parse_geo_rec(self, text: str) -> Dict[str, Any]:
        """Parse a GEO recommendation."""
        return {
            "page": self._get_nested_tag(text, "page"),
            "optimization": self._get_nested_tag(text, "optimization"),
            "impact": self._get_nested_tag(text, "impact"),
        }

    def _parse_ai_overview(self, text: str) -> Dict[str, Any]:
        """Parse AI overview analysis."""
        return {
            "presence_rate": float(self._get_nested_tag(text, "presence") or 0),
            "keywords_with_overview": int(self._get_nested_tag(text, "keywords") or 0),
            "citation_rate": float(self._get_nested_tag(text, "citations") or 0),
        }

    def _parse_serp_feature(self, text: str) -> Dict[str, Any]:
        """Parse a SERP feature opportunity."""
        return {
            "keyword": self._get_nested_tag(text, "keyword"),
            "feature": self._get_nested_tag(text, "feature"),
            "current_holder": self._get_nested_tag(text, "holder"),
            "opportunity": self._get_nested_tag(text, "opportunity"),
        }

    def _parse_content_format(self, text: str) -> Dict[str, Any]:
        """Parse a content format recommendation."""
        return {
            "keyword_group": self._get_nested_tag(text, "group"),
            "recommended_format": self._get_nested_tag(text, "format"),
            "word_count": int(self._get_nested_tag(text, "words") or 0),
            "elements": self._get_nested_tag(text, "elements").split(",") if self._get_nested_tag(text, "elements") else [],
        }

    def _parse_gbp(self, text: str) -> Dict[str, Any]:
        """Parse GBP analysis."""
        return {
            "completeness": float(self._get_nested_tag(text, "completeness") or 0),
            "categories": self._get_nested_tag(text, "categories").split(",") if self._get_nested_tag(text, "categories") else [],
            "reviews": int(self._get_nested_tag(text, "reviews") or 0),
            "rating": float(self._get_nested_tag(text, "rating") or 0),
        }

    def _parse_citation(self, text: str) -> Dict[str, Any]:
        """Parse a citation item."""
        return {
            "source": self._get_nested_tag(text, "source"),
            "status": self._get_nested_tag(text, "status"),
            "nap_consistent": self._get_nested_tag(text, "nap") == "true",
        }

    def _parse_executive_summary(self, text: str) -> Dict[str, Any]:
        """Parse executive summary."""
        return {
            "headline_metric": self._get_nested_tag(text, "headline_metric"),
            "key_findings": [
                self._get_nested_tag(text, f"key_finding")
                for _ in range(3)
            ],
            "strategic_direction": self._get_nested_tag(text, "strategic_direction"),
        }

    def _parse_priority_item(self, text: str) -> Dict[str, Any]:
        """Parse a priority stack item."""
        rank = self._get_attr(text, "rank")
        return {
            "rank": int(rank) if rank else 0,
            "initiative": self._get_nested_tag(text, "initiative"),
            "source_agent": self._get_nested_tag(text, "source_agent"),
            "impact_score": int(self._get_nested_tag(text, "impact_score") or 0),
            "effort_score": int(self._get_nested_tag(text, "effort_score") or 0),
            "expected_outcome": self._get_nested_tag(text, "expected_outcome"),
            "timeline": self._get_nested_tag(text, "timeline"),
            "owner": self._get_nested_tag(text, "owner"),
        }

    def _parse_roadmap_phase(self, text: str) -> Dict[str, Any]:
        """Parse a roadmap phase."""
        phase = self._get_attr(text, "phase")
        return {
            "phase": phase or "1",
            "goal": self._get_nested_tag(text, "phase_goal"),
            "initiatives": self._extract_xml_list(text, "initiative"),
            "milestones": self._extract_xml_list(text, "milestone"),
        }

    def _parse_pattern(self, text: str) -> Dict[str, Any]:
        """Parse a cross-agent pattern."""
        pattern_type = self._get_attr(text, "type")
        return {
            "type": pattern_type or "synergy",
            "agents": self._get_nested_tag(text, "agents"),
            "description": self._get_nested_tag(text, "description"),
            "resolution": self._get_nested_tag(text, "resolution"),
            "impact": self._get_nested_tag(text, "impact"),
        }

    # =========================================================================
    # CONVERSION HELPERS
    # =========================================================================

    def _convert_findings(
        self,
        parsed_findings: List[ParsedFinding],
        agent_data: Dict[str, Any]
    ) -> List[Finding]:
        """Convert parsed findings to Finding objects."""
        findings = []
        for pf in parsed_findings:
            findings.append(Finding(
                title=pf.title,
                description=pf.description,
                evidence=pf.evidence,
                impact=pf.impact,
                confidence=pf.confidence,
                priority=pf.priority,
                category=pf.category,
                data_sources=pf.data_sources,
                metrics=pf.metrics,
            ))
        return findings

    def _convert_recommendations(
        self,
        parsed_recs: List[ParsedRecommendation],
        agent_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Convert parsed recommendations to Recommendation objects."""
        recommendations = []
        for pr in parsed_recs:
            recommendations.append(Recommendation(
                action=pr.action,
                rationale=pr.rationale,
                priority=pr.priority,
                effort=pr.effort,
                impact=pr.impact,
                timeline=pr.timeline,
                dependencies=pr.dependencies,
                success_metrics=pr.success_metrics,
                owner=pr.owner,
                confidence=pr.confidence,
            ))
        return recommendations

    def _merge_metrics(
        self,
        parsed_metrics: Dict[str, Any],
        agent_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge metrics from parsing and agent-specific extraction."""
        metrics = dict(parsed_metrics)

        # Add any metrics from agent-specific data
        for key, value in agent_data.items():
            if isinstance(value, dict) and any(k.endswith("_score") for k in value):
                for k, v in value.items():
                    if k.endswith("_score") or k.endswith("_count"):
                        metrics[k] = v

        return metrics

    def _calculate_confidence(
        self,
        parse_result: ParseResult,
        check_results: List[CheckResult]
    ) -> float:
        """Calculate overall confidence in the output."""
        # Base confidence from parsing method
        parse_confidence = {
            "xml": 0.9,
            "json": 0.85,
            "markdown": 0.7,
            "fallback": 0.5,
            "none": 0.3,
        }.get(parse_result.parse_method, 0.5)

        # Adjust based on quality checks
        passed_ratio = sum(1 for r in check_results if r.passed) / len(check_results) if check_results else 0

        # Weighted average
        return round((parse_confidence * 0.4) + (passed_ratio * 0.6), 2)

    def _get_display_name(self, agent_name: str) -> str:
        """Get display name for agent."""
        display_names = {
            "keyword_intelligence": "Keyword Intelligence",
            "backlink_intelligence": "Backlink Intelligence",
            "technical_seo": "Technical SEO",
            "content_analysis": "Content Analysis",
            "semantic_architecture": "Semantic Architecture",
            "ai_visibility": "AI Visibility",
            "serp_analysis": "SERP Analysis",
            "local_seo": "Local SEO",
            "master_strategy": "Master Strategy",
        }
        return display_names.get(agent_name, agent_name.replace("_", " ").title())


# ============================================================================
# BATCH CONVERTER
# ============================================================================

class BatchOutputConverter:
    """
    Converts multiple agent outputs in a batch.

    Useful for processing all agent outputs before report generation.
    """

    def __init__(self):
        """Initialize batch converter."""
        self.converter = AgentOutputConverter()

    def convert_all(
        self,
        agent_outputs: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ConversionResult]:
        """
        Convert all agent outputs.

        Args:
            agent_outputs: Dict mapping agent_name to raw_output
            context: Optional shared context

        Returns:
            Dict mapping agent_name to ConversionResult
        """
        results = {}
        for agent_name, raw_output in agent_outputs.items():
            results[agent_name] = self.converter.convert(
                agent_name=agent_name,
                raw_output=raw_output,
                context=context,
            )
        return results

    def get_summary(self, results: Dict[str, ConversionResult]) -> Dict[str, Any]:
        """Get summary of all conversion results."""
        total = len(results)
        successful = sum(1 for r in results.values() if r.success)
        quality_passed = sum(1 for r in results.values() if r.quality_passed)
        avg_quality = sum(r.quality_score for r in results.values()) / total if total else 0

        return {
            "total_agents": total,
            "successful_conversions": successful,
            "quality_gate_passed": quality_passed,
            "average_quality_score": round(avg_quality, 2),
            "agents_failed": [
                name for name, r in results.items()
                if not r.success
            ],
            "agents_below_quality": [
                name for name, r in results.items()
                if not r.quality_passed
            ],
        }
