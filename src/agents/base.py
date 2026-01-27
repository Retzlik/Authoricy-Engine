"""
Base Agent Class for Authoricy Intelligence Engine

All analysis agents inherit from this base class, which provides:
- Standard interface for analysis
- Quality check framework (25 checks, 23 must pass)
- Structured output parsing
- Retry logic for quality failures
- Token and cost tracking

Architecture:
    BaseAgent (abstract)
    ├── KeywordIntelligenceAgent
    ├── BacklinkIntelligenceAgent
    ├── TechnicalSEOAgent
    ├── ContentAnalysisAgent
    ├── SemanticArchitectureAgent
    ├── AIVisibilityAgent
    ├── SERPAnalysisAgent
    ├── LocalSEOAgent (conditional)
    └── MasterStrategyAgent (synthesizer)
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from ..analyzer.client import ClaudeClient

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Finding:
    """A specific finding from an agent's analysis."""
    title: str
    description: str
    evidence: str
    impact: str
    confidence: float  # 0.0 - 1.0
    priority: int  # 1 (highest) - 5 (lowest)
    category: str
    data_sources: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    """An actionable recommendation from an agent."""
    action: str
    rationale: str
    priority: int  # 1-3 (P1=Critical, P2=High, P3=Medium)
    effort: str  # "Low", "Medium", "High"
    impact: str  # "Low", "Medium", "High"
    timeline: str  # e.g., "2-4 weeks"
    dependencies: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)
    owner: str = ""  # Suggested role/team
    confidence: float = 0.8


@dataclass
class AgentOutput:
    """Standardized output from all agents."""
    agent_name: str
    timestamp: datetime

    # Core outputs
    findings: List[Finding]
    recommendations: List[Recommendation]
    metrics: Dict[str, Any]

    # Quality tracking
    quality_score: float  # 0-10 scale (need 9.2+ to pass)
    quality_checks: Dict[str, bool]  # 25 individual checks
    checks_passed: int
    checks_failed: int

    # Raw data
    raw_output: str
    structured_data: Dict[str, Any]

    # Metadata
    confidence: float
    tokens_used: int
    cost_usd: float
    processing_time_seconds: float

    @property
    def passed_quality_gate(self) -> bool:
        """Check if output passes quality gate (23/25 = 92%)."""
        return self.checks_passed >= 23

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "findings": [
                {
                    "title": f.title,
                    "description": f.description,
                    "evidence": f.evidence,
                    "impact": f.impact,
                    "confidence": f.confidence,
                    "priority": f.priority,
                    "category": f.category,
                    "data_sources": f.data_sources,
                    "metrics": f.metrics,
                }
                for f in self.findings
            ],
            "recommendations": [
                {
                    "action": r.action,
                    "rationale": r.rationale,
                    "priority": r.priority,
                    "effort": r.effort,
                    "impact": r.impact,
                    "timeline": r.timeline,
                    "dependencies": r.dependencies,
                    "success_metrics": r.success_metrics,
                    "owner": r.owner,
                    "confidence": r.confidence,
                }
                for r in self.recommendations
            ],
            "metrics": self.metrics,
            "quality_score": self.quality_score,
            "quality_checks": self.quality_checks,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "processing_time_seconds": self.processing_time_seconds,
        }


# ============================================================================
# BASE AGENT CLASS
# ============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all analysis agents.

    Each agent must implement:
    - name: Unique identifier
    - system_prompt: Full prompt with persona and constraints
    - analysis_prompt_template: Template with {placeholders} for data
    - output_schema: Expected structure for validation
    - required_data: List of required data keys
    """

    # Quality gate threshold (23/25 checks = 92%)
    QUALITY_THRESHOLD = 23
    TOTAL_CHECKS = 25

    # Default token limits
    MAX_OUTPUT_TOKENS = 8000
    TEMPERATURE = 0.3

    def __init__(self, client: "ClaudeClient"):
        """
        Initialize agent with Claude client.

        Args:
            client: ClaudeClient instance for API calls
        """
        self.client = client
        self._last_output: Optional[AgentOutput] = None

    # =========================================================================
    # ABSTRACT PROPERTIES - Must be implemented by each agent
    # =========================================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique agent identifier (e.g., 'keyword_intelligence')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Keyword Intelligence Agent')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of agent's purpose."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """
        Full system prompt including:
        - Expert persona
        - Behavioral constraints (NEVER/ALWAYS rules)
        - Quality standards
        - Output format requirements
        """
        pass

    @property
    @abstractmethod
    def analysis_prompt_template(self) -> str:
        """
        User prompt template with {placeholders} for data injection.

        Example:
            '''
            # KEYWORD DATA
            Domain: {domain}
            Total Keywords: {keyword_count}

            ## Ranked Keywords
            {ranked_keywords_json}
            ...
            '''
        """
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """
        Expected output structure for validation.

        Example:
            {
                "findings": [{"title": str, "evidence": str, ...}],
                "recommendations": [{"action": str, "priority": int, ...}],
                "metrics": {"keyword_health_score": float, ...}
            }
        """
        pass

    @property
    @abstractmethod
    def required_data(self) -> List[str]:
        """
        List of required data keys from collected data.

        Example: ["ranked_keywords", "keyword_gaps", "competitors"]
        """
        pass

    # =========================================================================
    # MAIN ANALYSIS METHOD
    # =========================================================================

    async def analyze(
        self,
        collected_data: Dict[str, Any],
        retry_on_quality_failure: bool = True,
        max_retries: int = 2
    ) -> AgentOutput:
        """
        Run analysis and return structured output.

        Args:
            collected_data: Data from collection phase
            retry_on_quality_failure: Whether to retry if quality gate fails
            max_retries: Maximum retry attempts

        Returns:
            AgentOutput with findings, recommendations, and quality metrics
        """
        start_time = datetime.now()
        logger.info(f"[{self.name}] Starting analysis...")

        # 1. Validate required data is present
        self._validate_data(collected_data)

        # 2. Prepare prompt with data interpolation
        prompt = self._prepare_prompt(collected_data)

        # 3. Call Claude API
        response = await self.client.analyze_with_retry(
            prompt=prompt,
            system=self.system_prompt,
            max_tokens=self.MAX_OUTPUT_TOKENS,
            temperature=self.TEMPERATURE,
        )

        if not response.success:
            logger.error(f"[{self.name}] API call failed: {response.error}")
            return self._create_error_output(response.error, start_time)

        # 4. Parse structured output
        parsed = self._parse_output(response.content)

        # 5. Run quality checks
        quality_score, quality_checks = self._run_quality_checks(parsed, response.content)
        checks_passed = sum(1 for v in quality_checks.values() if v)

        # 6. Create output object
        output = AgentOutput(
            agent_name=self.name,
            timestamp=datetime.now(),
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            metrics=parsed.get("metrics", {}),
            quality_score=quality_score,
            quality_checks=quality_checks,
            checks_passed=checks_passed,
            checks_failed=self.TOTAL_CHECKS - checks_passed,
            raw_output=response.content,
            structured_data=parsed,
            confidence=parsed.get("overall_confidence", 0.7),
            tokens_used=response.tokens_used,
            cost_usd=response.cost,
            processing_time_seconds=(datetime.now() - start_time).total_seconds(),
        )

        # 7. Retry if quality gate not met
        if not output.passed_quality_gate and retry_on_quality_failure:
            for attempt in range(max_retries):
                logger.warning(
                    f"[{self.name}] Quality gate failed ({checks_passed}/{self.TOTAL_CHECKS}). "
                    f"Retry {attempt + 1}/{max_retries}..."
                )
                output = await self._retry_with_feedback(
                    collected_data, output, quality_checks
                )
                if output.passed_quality_gate:
                    break

        self._last_output = output
        logger.info(
            f"[{self.name}] Complete. Quality: {output.quality_score:.1f}/10 "
            f"({output.checks_passed}/{self.TOTAL_CHECKS} checks passed)"
        )

        return output

    # =========================================================================
    # DATA VALIDATION
    # =========================================================================

    def _validate_data(self, data: Dict[str, Any]) -> None:
        """
        Validate that required data fields are present.

        Raises:
            ValueError: If required data is missing
        """
        missing = []
        for key in self.required_data:
            if key not in data or data[key] is None:
                missing.append(key)

        if missing:
            raise ValueError(
                f"[{self.name}] Missing required data: {', '.join(missing)}"
            )

    # =========================================================================
    # PROMPT PREPARATION
    # =========================================================================

    def _prepare_prompt(self, data: Dict[str, Any]) -> str:
        """
        Prepare analysis prompt by interpolating data into template.

        Args:
            data: Collected data dictionary

        Returns:
            Formatted prompt string
        """
        # Get base template
        template = self.analysis_prompt_template

        # Prepare data for interpolation
        prompt_data = self._prepare_prompt_data(data)

        # Interpolate
        try:
            return template.format(**prompt_data)
        except KeyError as e:
            logger.warning(f"[{self.name}] Missing template key: {e}")
            # Return template with available data
            return template.format_map(SafeDict(prompt_data))

    def _prepare_prompt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data dictionary for prompt interpolation.

        Override in subclasses to customize data preparation.

        Args:
            data: Raw collected data

        Returns:
            Processed data ready for template interpolation
        """
        import json

        result = {}

        # Add metadata
        metadata = data.get("metadata", {})
        result["domain"] = metadata.get("domain", "unknown")
        result["market"] = metadata.get("market", "unknown")
        result["language"] = metadata.get("language", "unknown")

        # Add summary stats
        summary = data.get("summary", {})
        result["keyword_count"] = summary.get("total_organic_keywords", 0)
        result["competitor_count"] = summary.get("competitor_count", 0)
        result["backlink_count"] = summary.get("total_backlinks", 0)

        # Domain Rating (DR) comes from backlink_summary, NOT domain_overview
        # The domain_rank_overview API returns keyword counts, not DR
        domain_overview = data.get("phase1_foundation", {}).get("domain_overview", {})
        backlink_summary = data.get("phase1_foundation", {}).get("backlink_summary", {})
        result["domain_rank"] = backlink_summary.get("domain_rank", 0)
        result["organic_traffic"] = domain_overview.get("organic_traffic", 0)

        # Add JSON data for each phase (truncated for token management)
        for phase_key in ["phase1_foundation", "phase2_keywords", "phase3_competitive", "phase4_ai_technical"]:
            phase_data = data.get(phase_key, {})
            # Truncate large arrays
            truncated = self._truncate_data(phase_data, max_items=50)
            result[f"{phase_key}_json"] = json.dumps(truncated, indent=2, default=str)

        return result

    def _truncate_data(self, data: Any, max_items: int = 50) -> Any:
        """Truncate large arrays in data structure."""
        if isinstance(data, dict):
            return {
                k: self._truncate_data(v, max_items)
                for k, v in data.items()
            }
        elif isinstance(data, list) and len(data) > max_items:
            return data[:max_items]
        return data

    # =========================================================================
    # OUTPUT PARSING
    # =========================================================================

    def _parse_output(self, raw_output: str) -> Dict[str, Any]:
        """
        Parse raw Claude output into structured data.

        Handles both XML-tagged output and JSON blocks.

        Args:
            raw_output: Raw text from Claude

        Returns:
            Parsed dictionary with findings, recommendations, metrics
        """
        result = {
            "findings": [],
            "recommendations": [],
            "metrics": {},
            "overall_confidence": 0.7,
        }

        # Try XML parsing first
        try:
            result["findings"] = self._parse_xml_findings(raw_output)
            result["recommendations"] = self._parse_xml_recommendations(raw_output)
            result["metrics"] = self._parse_xml_metrics(raw_output)
        except Exception as e:
            logger.debug(f"XML parsing failed, trying JSON: {e}")

        # Fall back to JSON parsing if XML didn't yield results
        if not result["findings"]:
            try:
                result = self._parse_json_output(raw_output)
            except Exception as e:
                logger.debug(f"JSON parsing failed: {e}")

        # Extract overall confidence if present
        conf_match = re.search(r'confidence["\s:]+([0-9.]+)', raw_output, re.I)
        if conf_match:
            result["overall_confidence"] = float(conf_match.group(1))

        return result

    def _parse_xml_findings(self, output: str) -> List[Finding]:
        """Parse XML-tagged findings."""
        findings = []

        # Pattern for <finding> tags
        pattern = r'<finding\s+(?:[^>]*?)>(.*?)</finding>'
        matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)

        for match in matches:
            finding = self._parse_finding_content(match)
            if finding:
                findings.append(finding)

        return findings

    def _parse_finding_content(self, content: str) -> Optional[Finding]:
        """Parse content within a finding tag."""
        try:
            title = self._extract_tag_content(content, "title") or "Untitled Finding"
            description = self._extract_tag_content(content, "description") or content[:200]
            evidence = self._extract_tag_content(content, "evidence") or ""
            impact = self._extract_tag_content(content, "impact") or ""

            # Extract attributes
            confidence = float(self._extract_attribute(content, "confidence") or 0.7)
            priority = int(self._extract_attribute(content, "priority") or 3)
            category = self._extract_attribute(content, "category") or "general"

            return Finding(
                title=title,
                description=description,
                evidence=evidence,
                impact=impact,
                confidence=confidence,
                priority=priority,
                category=category,
            )
        except Exception as e:
            logger.debug(f"Failed to parse finding: {e}")
            return None

    def _parse_xml_recommendations(self, output: str) -> List[Recommendation]:
        """Parse XML-tagged recommendations."""
        recommendations = []

        pattern = r'<recommendation\s+(?:[^>]*?)>(.*?)</recommendation>'
        matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)

        for match in matches:
            rec = self._parse_recommendation_content(match)
            if rec:
                recommendations.append(rec)

        return recommendations

    def _parse_recommendation_content(self, content: str) -> Optional[Recommendation]:
        """Parse content within a recommendation tag."""
        try:
            action = self._extract_tag_content(content, "action") or content[:200]
            rationale = self._extract_tag_content(content, "rationale") or ""
            timeline = self._extract_tag_content(content, "timeline") or "4-8 weeks"

            priority = int(self._extract_attribute(content, "priority") or 2)
            effort = self._extract_attribute(content, "effort") or "Medium"
            impact = self._extract_attribute(content, "impact") or "Medium"

            return Recommendation(
                action=action,
                rationale=rationale,
                priority=priority,
                effort=effort,
                impact=impact,
                timeline=timeline,
            )
        except Exception as e:
            logger.debug(f"Failed to parse recommendation: {e}")
            return None

    def _parse_xml_metrics(self, output: str) -> Dict[str, Any]:
        """Parse XML-tagged metrics."""
        metrics = {}

        pattern = r'<metric\s+name=["\']([^"\']+)["\']\s+value=["\']([^"\']+)["\']'
        matches = re.findall(pattern, output, re.IGNORECASE)

        for name, value in matches:
            try:
                metrics[name] = float(value)
            except ValueError:
                metrics[name] = value

        return metrics

    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """Parse JSON blocks from output."""
        import json

        # Find JSON blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, output, re.DOTALL)

        for match in matches:
            try:
                parsed = json.loads(match)
                if "findings" in parsed or "recommendations" in parsed:
                    return self._convert_json_to_dataclasses(parsed)
            except json.JSONDecodeError:
                continue

        return {"findings": [], "recommendations": [], "metrics": {}}

    def _convert_json_to_dataclasses(self, data: Dict) -> Dict[str, Any]:
        """Convert JSON data to Finding/Recommendation dataclasses."""
        result = {
            "findings": [],
            "recommendations": [],
            "metrics": data.get("metrics", {}),
            "overall_confidence": data.get("confidence", 0.7),
        }

        for f in data.get("findings", []):
            if isinstance(f, dict):
                result["findings"].append(Finding(
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    evidence=f.get("evidence", ""),
                    impact=f.get("impact", ""),
                    confidence=f.get("confidence", 0.7),
                    priority=f.get("priority", 3),
                    category=f.get("category", "general"),
                ))

        for r in data.get("recommendations", []):
            if isinstance(r, dict):
                result["recommendations"].append(Recommendation(
                    action=r.get("action", ""),
                    rationale=r.get("rationale", ""),
                    priority=r.get("priority", 2),
                    effort=r.get("effort", "Medium"),
                    impact=r.get("impact", "Medium"),
                    timeline=r.get("timeline", "4-8 weeks"),
                ))

        return result

    def _extract_tag_content(self, text: str, tag: str) -> Optional[str]:
        """Extract content from an XML tag."""
        pattern = rf'<{tag}>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_attribute(self, text: str, attr: str) -> Optional[str]:
        """Extract an attribute value."""
        pattern = rf'{attr}=["\']([^"\']+)["\']'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    # =========================================================================
    # QUALITY CHECKS (25 total, need 23 to pass)
    # =========================================================================

    def _run_quality_checks(
        self,
        parsed: Dict[str, Any],
        raw_output: str
    ) -> tuple[float, Dict[str, bool]]:
        """
        Run all 25 quality checks on agent output.

        Returns:
            Tuple of (quality_score 0-10, dict of check results)
        """
        checks = {}

        # ===== SPECIFICITY CHECKS (7) =====
        checks["has_specific_numbers"] = self._check_specific_numbers(raw_output)
        checks["has_specific_urls"] = self._check_specific_urls(raw_output)
        checks["has_competitor_comparisons"] = self._check_competitors(raw_output)
        checks["has_measurable_targets"] = self._check_targets(parsed)
        checks["uses_precise_terminology"] = self._check_terminology(raw_output)
        checks["avoids_weasel_words"] = self._check_weasel_words(raw_output)
        checks["has_timeframes"] = self._check_timeframes(parsed)

        # ===== ACTIONABILITY CHECKS (6) =====
        checks["has_clear_actions"] = self._check_actions(parsed)
        checks["has_priorities"] = self._check_priorities(parsed)
        checks["has_effort_estimates"] = self._check_effort(parsed)
        checks["has_dependencies"] = self._check_dependencies(parsed)
        checks["has_success_metrics"] = self._check_success_metrics(parsed)
        checks["has_owners"] = self._check_owners(parsed)

        # ===== DATA-GROUNDING CHECKS (6) =====
        checks["cites_source_data"] = self._check_citations(raw_output)
        checks["has_benchmarks"] = self._check_benchmarks(raw_output)
        checks["consistent_time_periods"] = self._check_time_consistency(raw_output)
        checks["notes_significance"] = self._check_significance(raw_output)
        checks["acknowledges_limitations"] = self._check_limitations(raw_output)
        checks["has_confidence_levels"] = self._check_confidence(parsed)

        # ===== NON-GENERIC CHECKS (6) =====
        checks["no_placeholder_text"] = self._check_no_placeholders(raw_output)
        checks["customized_advice"] = self._check_customization(raw_output)
        checks["industry_specific"] = self._check_industry_context(raw_output)
        checks["considers_history"] = self._check_history_context(raw_output)
        checks["reflects_competition"] = self._check_competition_reflection(raw_output)
        checks["unique_opportunities"] = self._check_unique_opps(parsed)

        # Calculate score (0-10 scale)
        passed = sum(1 for v in checks.values() if v)
        score = (passed / self.TOTAL_CHECKS) * 10

        return round(score, 2), checks

    # ----- Specificity Checks -----

    def _check_specific_numbers(self, output: str) -> bool:
        """Check for specific numbers (not vague qualifiers)."""
        # Look for numeric patterns
        number_patterns = [
            r'\d+(?:,\d{3})*(?:\.\d+)?%',  # Percentages
            r'\d+(?:,\d{3})+',  # Large numbers with commas
            r'(?:position|rank)\s+\d+',  # Rankings
            r'\$\d+(?:,\d{3})*',  # Dollar amounts
            r'\d+\s*(?:keywords?|pages?|links?|visits?)',  # Counts
        ]
        matches = sum(1 for p in number_patterns if re.search(p, output, re.I))
        return matches >= 5

    def _check_specific_urls(self, output: str) -> bool:
        """Check for specific URLs/pages mentioned."""
        url_pattern = r'(?:/[a-z0-9\-_/]+|https?://[^\s]+)'
        matches = re.findall(url_pattern, output, re.I)
        return len(matches) >= 3

    def _check_competitors(self, output: str) -> bool:
        """Check for competitor-specific comparisons."""
        comparison_patterns = [
            r'compared to',
            r'versus',
            r'competitor[s]?\s+(?:like|such as|including)',
            r'outranks?|outperforms?',
            r'behind|ahead of',
        ]
        return any(re.search(p, output, re.I) for p in comparison_patterns)

    def _check_targets(self, parsed: Dict) -> bool:
        """Check for measurable targets."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return False

        targets_found = 0
        for rec in recs:
            if isinstance(rec, Recommendation):
                if rec.success_metrics:
                    targets_found += 1
            elif isinstance(rec, dict) and rec.get("success_metrics"):
                targets_found += 1

        return targets_found >= len(recs) * 0.5

    def _check_terminology(self, output: str) -> bool:
        """Check for precise SEO terminology."""
        terms = [
            r'\bDR\b', r'\bDA\b', r'keyword difficulty', r'search volume',
            r'CTR', r'impressions', r'SERP', r'backlink',
            r'anchor text', r'referring domain', r'organic traffic',
        ]
        matches = sum(1 for t in terms if re.search(t, output, re.I))
        return matches >= 5

    def _check_weasel_words(self, output: str) -> bool:
        """Check that weasel words are avoided."""
        weasel_patterns = [
            r'\b(?:might|could|potentially)\s+(?:want to|need to|should)\b',
            r'\bperhaps\b',
            r'\bpossibly\b',
            r'\bsomewhat\b',
            r'\bfairly\b',
        ]
        weasel_count = sum(len(re.findall(p, output, re.I)) for p in weasel_patterns)
        return weasel_count < 5

    def _check_timeframes(self, parsed: Dict) -> bool:
        """Check for timeframes in recommendations."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return False

        with_timeline = 0
        for rec in recs:
            timeline = rec.timeline if isinstance(rec, Recommendation) else rec.get("timeline", "")
            if timeline and timeline not in ["", "TBD", "N/A"]:
                with_timeline += 1

        return with_timeline >= len(recs) * 0.5

    # ----- Actionability Checks -----

    def _check_actions(self, parsed: Dict) -> bool:
        """Check for clear action items."""
        recs = parsed.get("recommendations", [])
        return len(recs) >= 3

    def _check_priorities(self, parsed: Dict) -> bool:
        """Check for priority assignments."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return False

        with_priority = sum(
            1 for r in recs
            if (isinstance(r, Recommendation) and r.priority) or
               (isinstance(r, dict) and r.get("priority"))
        )
        return with_priority >= len(recs) * 0.8

    def _check_effort(self, parsed: Dict) -> bool:
        """Check for effort estimates."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return False

        with_effort = sum(
            1 for r in recs
            if (isinstance(r, Recommendation) and r.effort) or
               (isinstance(r, dict) and r.get("effort"))
        )
        return with_effort >= len(recs) * 0.5

    def _check_dependencies(self, parsed: Dict) -> bool:
        """Check for dependency identification."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return True  # No recs = pass by default

        # At least some recommendations should note dependencies
        with_deps = sum(
            1 for r in recs
            if (isinstance(r, Recommendation) and r.dependencies) or
               (isinstance(r, dict) and r.get("dependencies"))
        )
        return with_deps >= 1

    def _check_success_metrics(self, parsed: Dict) -> bool:
        """Check for success metrics."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return False

        with_metrics = sum(
            1 for r in recs
            if (isinstance(r, Recommendation) and r.success_metrics) or
               (isinstance(r, dict) and r.get("success_metrics"))
        )
        return with_metrics >= len(recs) * 0.3

    def _check_owners(self, parsed: Dict) -> bool:
        """Check for suggested owners/roles."""
        recs = parsed.get("recommendations", [])
        if not recs:
            return True  # Pass by default

        with_owner = sum(
            1 for r in recs
            if (isinstance(r, Recommendation) and r.owner) or
               (isinstance(r, dict) and r.get("owner"))
        )
        return with_owner >= 1

    # ----- Data-Grounding Checks -----

    def _check_citations(self, output: str) -> bool:
        """Check for data citations."""
        citation_patterns = [
            r'\[.*?:\s*\d+.*?\]',  # [Metric: Value]
            r'according to',
            r'based on.*data',
            r'shows that',
            r'indicates',
        ]
        matches = sum(1 for p in citation_patterns if re.search(p, output, re.I))
        return matches >= 3

    def _check_benchmarks(self, output: str) -> bool:
        """Check for benchmark comparisons."""
        benchmark_patterns = [
            r'industry average',
            r'benchmark',
            r'compared to.*average',
            r'typical',
            r'median',
        ]
        return any(re.search(p, output, re.I) for p in benchmark_patterns)

    def _check_time_consistency(self, output: str) -> bool:
        """Check for consistent time period references."""
        # Simple check - at least mentions time periods
        time_patterns = [
            r'\d+\s*(?:day|week|month|year)s?',
            r'Q[1-4]\s*\d{4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        ]
        return any(re.search(p, output, re.I) for p in time_patterns)

    def _check_significance(self, output: str) -> bool:
        """Check for statistical significance notes."""
        significance_patterns = [
            r'significant',
            r'notable',
            r'substantial',
            r'meaningful',
            r'material',
        ]
        return any(re.search(p, output, re.I) for p in significance_patterns)

    def _check_limitations(self, output: str) -> bool:
        """Check for acknowledgment of limitations."""
        limitation_patterns = [
            r'limitation',
            r'caveat',
            r'note that',
            r'however',
            r'incomplete',
            r'insufficient data',
        ]
        return any(re.search(p, output, re.I) for p in limitation_patterns)

    def _check_confidence(self, parsed: Dict) -> bool:
        """Check for confidence levels."""
        findings = parsed.get("findings", [])
        if not findings:
            return True

        with_confidence = sum(
            1 for f in findings
            if (isinstance(f, Finding) and f.confidence) or
               (isinstance(f, dict) and f.get("confidence"))
        )
        return with_confidence >= len(findings) * 0.5

    # ----- Non-Generic Checks -----

    def _check_no_placeholders(self, output: str) -> bool:
        """Check for absence of placeholder text."""
        placeholder_patterns = [
            r'based on (?:comprehensive|thorough|detailed) analysis',
            r'according to (?:our|the) analysis',
            r'\[.*?placeholder.*?\]',
            r'lorem ipsum',
            r'TBD|TODO|FIXME',
        ]
        return not any(re.search(p, output, re.I) for p in placeholder_patterns)

    def _check_customization(self, output: str) -> bool:
        """Check for customized (not generic) advice."""
        generic_patterns = [
            r'follow\s+(?:SEO\s+)?best practices',
            r'implement\s+industry\s+standards',
            r'optimize\s+your\s+(?:website|content)',  # Too vague
        ]
        generic_count = sum(len(re.findall(p, output, re.I)) for p in generic_patterns)
        return generic_count < 3

    def _check_industry_context(self, output: str) -> bool:
        """Check for industry-specific context."""
        # Should mention industry, vertical, or market specifics
        industry_patterns = [
            r'in (?:this|the|your) (?:industry|sector|vertical|market|niche)',
            r'(?:B2B|B2C|SaaS|e-commerce|ecommerce)',
            r'competitors in',
        ]
        return any(re.search(p, output, re.I) for p in industry_patterns)

    def _check_history_context(self, output: str) -> bool:
        """Check for consideration of historical context."""
        history_patterns = [
            r'historically',
            r'over (?:the past|time)',
            r'trend',
            r'previously',
            r'growth|decline',
        ]
        return any(re.search(p, output, re.I) for p in history_patterns)

    def _check_competition_reflection(self, output: str) -> bool:
        """Check that competitive landscape is reflected."""
        competition_patterns = [
            r'competitor',
            r'competitive',
            r'market share',
            r'outrank',
            r'competing',
        ]
        matches = sum(len(re.findall(p, output, re.I)) for p in competition_patterns)
        return matches >= 3

    def _check_unique_opps(self, parsed: Dict) -> bool:
        """Check for unique opportunities identified."""
        findings = parsed.get("findings", [])
        recs = parsed.get("recommendations", [])
        return len(findings) >= 3 and len(recs) >= 3

    # =========================================================================
    # RETRY LOGIC
    # =========================================================================

    async def _retry_with_feedback(
        self,
        collected_data: Dict[str, Any],
        previous_output: AgentOutput,
        failed_checks: Dict[str, bool]
    ) -> AgentOutput:
        """
        Retry analysis with feedback on failed quality checks.

        Args:
            collected_data: Original data
            previous_output: Output that failed quality gate
            failed_checks: Dict of check names -> pass/fail

        Returns:
            New AgentOutput (hopefully passing)
        """
        # Build feedback prompt
        failed = [k for k, v in failed_checks.items() if not v]
        feedback = f"""
## QUALITY IMPROVEMENT REQUIRED

Your previous response failed the following quality checks:
{chr(10).join(f'- {check}' for check in failed[:10])}

Please regenerate your analysis addressing these issues:
1. Be MORE SPECIFIC - use exact numbers, URLs, and metrics
2. Be MORE ACTIONABLE - every recommendation needs effort/impact/timeline
3. CITE YOUR DATA - reference specific data points
4. AVOID GENERIC ADVICE - make it specific to this domain

Previous response excerpt (first 2000 chars):
{previous_output.raw_output[:2000]}...

Now provide an IMPROVED analysis:
"""

        # Prepare enhanced prompt
        base_prompt = self._prepare_prompt(collected_data)
        enhanced_prompt = base_prompt + "\n\n" + feedback

        # Call API again
        response = await self.client.analyze_with_retry(
            prompt=enhanced_prompt,
            system=self.system_prompt,
            max_tokens=self.MAX_OUTPUT_TOKENS,
            temperature=self.TEMPERATURE,
        )

        if not response.success:
            return previous_output  # Return previous if retry fails

        # Parse and check again
        parsed = self._parse_output(response.content)
        quality_score, quality_checks = self._run_quality_checks(parsed, response.content)
        checks_passed = sum(1 for v in quality_checks.values() if v)

        return AgentOutput(
            agent_name=self.name,
            timestamp=datetime.now(),
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            metrics=parsed.get("metrics", {}),
            quality_score=quality_score,
            quality_checks=quality_checks,
            checks_passed=checks_passed,
            checks_failed=self.TOTAL_CHECKS - checks_passed,
            raw_output=response.content,
            structured_data=parsed,
            confidence=parsed.get("overall_confidence", 0.7),
            tokens_used=previous_output.tokens_used + response.tokens_used,
            cost_usd=previous_output.cost_usd + response.cost,
            processing_time_seconds=previous_output.processing_time_seconds,
        )

    # =========================================================================
    # ERROR HANDLING
    # =========================================================================

    def _create_error_output(self, error: str, start_time: datetime) -> AgentOutput:
        """Create error output when analysis fails."""
        return AgentOutput(
            agent_name=self.name,
            timestamp=datetime.now(),
            findings=[],
            recommendations=[],
            metrics={},
            quality_score=0.0,
            quality_checks={},
            checks_passed=0,
            checks_failed=self.TOTAL_CHECKS,
            raw_output=f"Error: {error}",
            structured_data={},
            confidence=0.0,
            tokens_used=0,
            cost_usd=0.0,
            processing_time_seconds=(datetime.now() - start_time).total_seconds(),
        )


# ============================================================================
# HELPER CLASSES
# ============================================================================

class SafeDict(dict):
    """Dict that returns placeholder for missing keys during format."""

    def __missing__(self, key):
        return f"{{{key}}}"  # Return placeholder
