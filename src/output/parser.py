"""
Output Parser for Agent Responses

Parses structured output from Claude agents in multiple formats:
- XML tags (preferred)
- JSON blocks
- Markdown sections

Handles graceful degradation when parsing fails.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParsedFinding:
    """Parsed finding from agent output."""
    title: str
    description: str
    evidence: str = ""
    impact: str = ""
    confidence: float = 0.7
    priority: int = 3
    category: str = "general"
    data_sources: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedRecommendation:
    """Parsed recommendation from agent output."""
    action: str
    rationale: str = ""
    priority: int = 2
    effort: str = "Medium"
    impact: str = "Medium"
    timeline: str = "4-8 weeks"
    dependencies: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)
    owner: str = ""
    confidence: float = 0.8


@dataclass
class ParseResult:
    """Complete result of parsing agent output."""
    success: bool
    findings: List[ParsedFinding]
    recommendations: List[ParsedRecommendation]
    metrics: Dict[str, Any]
    raw_sections: Dict[str, str]
    parse_method: str  # "xml", "json", "markdown", "fallback"
    errors: List[str] = field(default_factory=list)


class OutputParser:
    """
    Parses structured output from agent responses.

    Supports multiple formats with fallback chain:
    1. XML tags (<finding>, <recommendation>, etc.)
    2. JSON blocks (```json ... ```)
    3. Markdown sections (## Finding 1:)
    4. Fallback heuristics
    """

    def parse(self, raw_output: str) -> ParseResult:
        """
        Parse raw agent output into structured data.

        Args:
            raw_output: Raw text from Claude

        Returns:
            ParseResult with findings, recommendations, metrics
        """
        # Try each parsing method in order
        methods = [
            ("xml", self._parse_xml),
            ("json", self._parse_json),
            ("markdown", self._parse_markdown),
            ("fallback", self._parse_fallback),
        ]

        for method_name, parser_fn in methods:
            try:
                result = parser_fn(raw_output)
                if result.success and (result.findings or result.recommendations):
                    logger.debug(f"Successfully parsed with {method_name}")
                    return result
            except Exception as e:
                logger.debug(f"{method_name} parsing failed: {e}")
                continue

        # Return empty result if all methods fail
        return ParseResult(
            success=False,
            findings=[],
            recommendations=[],
            metrics={},
            raw_sections={},
            parse_method="none",
            errors=["All parsing methods failed"],
        )

    # =========================================================================
    # XML PARSING
    # =========================================================================

    def _parse_xml(self, text: str) -> ParseResult:
        """Parse XML-tagged output."""
        findings = self._extract_xml_findings(text)
        recommendations = self._extract_xml_recommendations(text)
        metrics = self._extract_xml_metrics(text)
        sections = self._extract_xml_sections(text)

        return ParseResult(
            success=bool(findings or recommendations),
            findings=findings,
            recommendations=recommendations,
            metrics=metrics,
            raw_sections=sections,
            parse_method="xml",
        )

    def _extract_xml_findings(self, text: str) -> List[ParsedFinding]:
        """Extract findings from XML tags."""
        findings = []

        # Pattern for <finding> with attributes
        pattern = r'<finding\s*([^>]*)>(.*?)</finding>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for attrs, content in matches:
            finding = self._parse_finding_xml(attrs, content)
            if finding:
                findings.append(finding)

        return findings

    def _parse_finding_xml(self, attrs: str, content: str) -> Optional[ParsedFinding]:
        """Parse a single finding from XML."""
        try:
            # Extract attributes
            confidence = self._get_attr(attrs, "confidence", 0.7)
            priority = int(self._get_attr(attrs, "priority", 3))
            category = self._get_attr(attrs, "category", "general")

            # Extract nested tags
            title = self._get_tag_content(content, "title") or self._get_first_line(content)
            description = self._get_tag_content(content, "description") or content[:500]
            evidence = self._get_tag_content(content, "evidence") or ""
            impact = self._get_tag_content(content, "impact") or ""

            return ParsedFinding(
                title=title.strip(),
                description=description.strip(),
                evidence=evidence.strip(),
                impact=impact.strip(),
                confidence=float(confidence),
                priority=priority,
                category=str(category),
            )
        except Exception as e:
            logger.debug(f"Failed to parse finding: {e}")
            return None

    def _extract_xml_recommendations(self, text: str) -> List[ParsedRecommendation]:
        """Extract recommendations from XML tags."""
        recommendations = []

        pattern = r'<recommendation\s*([^>]*)>(.*?)</recommendation>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for attrs, content in matches:
            rec = self._parse_recommendation_xml(attrs, content)
            if rec:
                recommendations.append(rec)

        return recommendations

    def _parse_recommendation_xml(self, attrs: str, content: str) -> Optional[ParsedRecommendation]:
        """Parse a single recommendation from XML."""
        try:
            priority = int(self._get_attr(attrs, "priority", 2))
            effort = self._get_attr(attrs, "effort", "Medium")
            impact = self._get_attr(attrs, "impact", "Medium")

            action = self._get_tag_content(content, "action") or self._get_first_line(content)
            rationale = self._get_tag_content(content, "rationale") or ""
            timeline = self._get_tag_content(content, "timeline") or "4-8 weeks"
            owner = self._get_tag_content(content, "owner") or ""

            # Extract lists
            dependencies = self._get_tag_list(content, "dependencies", "dependency")
            success_metrics = self._get_tag_list(content, "success_metrics", "metric")

            return ParsedRecommendation(
                action=action.strip(),
                rationale=rationale.strip(),
                priority=priority,
                effort=str(effort),
                impact=str(impact),
                timeline=timeline.strip(),
                dependencies=dependencies,
                success_metrics=success_metrics,
                owner=owner.strip(),
            )
        except Exception as e:
            logger.debug(f"Failed to parse recommendation: {e}")
            return None

    def _extract_xml_metrics(self, text: str) -> Dict[str, Any]:
        """Extract metrics from XML tags."""
        metrics = {}

        # Pattern for <metric name="x" value="y"/>
        pattern = r'<metric\s+name=["\']([^"\']+)["\']\s+value=["\']([^"\']+)["\']'
        matches = re.findall(pattern, text, re.IGNORECASE)

        for name, value in matches:
            try:
                # Try to convert to number
                if '.' in value:
                    metrics[name] = float(value)
                else:
                    metrics[name] = int(value)
            except ValueError:
                metrics[name] = value

        return metrics

    def _extract_xml_sections(self, text: str) -> Dict[str, str]:
        """Extract named sections from XML."""
        sections = {}

        pattern = r'<section\s+name=["\']([^"\']+)["\']>(.*?)</section>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for name, content in matches:
            sections[name] = content.strip()

        return sections

    # =========================================================================
    # JSON PARSING
    # =========================================================================

    def _parse_json(self, text: str) -> ParseResult:
        """Parse JSON blocks from output."""
        # Find JSON blocks
        pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if "findings" in data or "recommendations" in data:
                    return self._convert_json_result(data)
            except json.JSONDecodeError:
                continue

        # Try finding raw JSON object
        try:
            json_match = re.search(r'\{[\s\S]*"findings"[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return self._convert_json_result(data)
        except (json.JSONDecodeError, AttributeError):
            pass

        return ParseResult(
            success=False,
            findings=[],
            recommendations=[],
            metrics={},
            raw_sections={},
            parse_method="json",
            errors=["No valid JSON found"],
        )

    def _convert_json_result(self, data: Dict[str, Any]) -> ParseResult:
        """Convert JSON data to ParseResult."""
        findings = []
        for f in data.get("findings", []):
            if isinstance(f, dict):
                findings.append(ParsedFinding(
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    evidence=f.get("evidence", ""),
                    impact=f.get("impact", ""),
                    confidence=f.get("confidence", 0.7),
                    priority=f.get("priority", 3),
                    category=f.get("category", "general"),
                ))

        recommendations = []
        for r in data.get("recommendations", []):
            if isinstance(r, dict):
                recommendations.append(ParsedRecommendation(
                    action=r.get("action", ""),
                    rationale=r.get("rationale", ""),
                    priority=r.get("priority", 2),
                    effort=r.get("effort", "Medium"),
                    impact=r.get("impact", "Medium"),
                    timeline=r.get("timeline", "4-8 weeks"),
                    dependencies=r.get("dependencies", []),
                    success_metrics=r.get("success_metrics", []),
                    owner=r.get("owner", ""),
                ))

        return ParseResult(
            success=bool(findings or recommendations),
            findings=findings,
            recommendations=recommendations,
            metrics=data.get("metrics", {}),
            raw_sections={},
            parse_method="json",
        )

    # =========================================================================
    # MARKDOWN PARSING
    # =========================================================================

    def _parse_markdown(self, text: str) -> ParseResult:
        """Parse markdown-formatted output."""
        findings = self._extract_markdown_findings(text)
        recommendations = self._extract_markdown_recommendations(text)
        sections = self._extract_markdown_sections(text)

        return ParseResult(
            success=bool(findings or recommendations),
            findings=findings,
            recommendations=recommendations,
            metrics={},
            raw_sections=sections,
            parse_method="markdown",
        )

    def _extract_markdown_findings(self, text: str) -> List[ParsedFinding]:
        """Extract findings from markdown headers."""
        findings = []

        # Pattern for ## Finding N: Title or ## N. Title
        pattern = r'(?:^|\n)##\s*(?:Finding\s*\d+[:\s]*|(\d+)\.\s*)([^\n]+)([\s\S]*?)(?=\n##|\n#\s|\Z)'
        matches = re.findall(pattern, text, re.IGNORECASE)

        for num, title, content in matches:
            priority = int(num) if num else 3
            evidence = ""
            impact = ""

            # Extract evidence/impact from content
            evidence_match = re.search(r'\*\*Evidence[:\s]*\*\*([^\n]+)', content, re.I)
            if evidence_match:
                evidence = evidence_match.group(1).strip()

            impact_match = re.search(r'\*\*Impact[:\s]*\*\*([^\n]+)', content, re.I)
            if impact_match:
                impact = impact_match.group(1).strip()

            findings.append(ParsedFinding(
                title=title.strip(),
                description=content.strip()[:500],
                evidence=evidence,
                impact=impact,
                priority=min(priority, 5),
            ))

        return findings

    def _extract_markdown_recommendations(self, text: str) -> List[ParsedRecommendation]:
        """Extract recommendations from markdown."""
        recommendations = []

        # Pattern for ## Recommendation N: or numbered lists under recommendations header
        pattern = r'(?:^|\n)##\s*(?:Recommendation\s*\d+[:\s]*|Action\s*\d+[:\s]*)([^\n]+)([\s\S]*?)(?=\n##|\n#\s|\Z)'
        matches = re.findall(pattern, text, re.IGNORECASE)

        for title, content in matches:
            effort = "Medium"
            impact = "Medium"
            timeline = "4-8 weeks"

            # Extract structured data from content
            effort_match = re.search(r'\*\*Effort[:\s]*\*\*\s*(\w+)', content, re.I)
            if effort_match:
                effort = effort_match.group(1)

            impact_match = re.search(r'\*\*Impact[:\s]*\*\*\s*(\w+)', content, re.I)
            if impact_match:
                impact = impact_match.group(1)

            timeline_match = re.search(r'\*\*Timeline[:\s]*\*\*\s*([^\n]+)', content, re.I)
            if timeline_match:
                timeline = timeline_match.group(1).strip()

            recommendations.append(ParsedRecommendation(
                action=title.strip(),
                rationale=content.strip()[:300],
                effort=effort,
                impact=impact,
                timeline=timeline,
            ))

        return recommendations

    def _extract_markdown_sections(self, text: str) -> Dict[str, str]:
        """Extract named sections from markdown headers."""
        sections = {}

        pattern = r'(?:^|\n)##\s*([^\n]+)([\s\S]*?)(?=\n##|\n#\s|\Z)'
        matches = re.findall(pattern, text)

        for header, content in matches:
            key = header.strip().lower().replace(" ", "_")
            sections[key] = content.strip()

        return sections

    # =========================================================================
    # FALLBACK PARSING
    # =========================================================================

    def _parse_fallback(self, text: str) -> ParseResult:
        """Fallback parsing using heuristics."""
        findings = []
        recommendations = []

        # Try to extract anything that looks like findings
        lines = text.split("\n")
        current_finding = None
        current_rec = None

        for line in lines:
            line = line.strip()

            # Look for numbered items or bullet points
            if re.match(r'^(?:\d+\.|[-•*])\s+\*\*', line):
                # Looks like a bold finding/recommendation
                content = re.sub(r'^(?:\d+\.|[-•*])\s+\*\*', '', line)
                content = content.replace("**", "")

                if any(kw in line.lower() for kw in ["recommend", "action", "implement", "create"]):
                    recommendations.append(ParsedRecommendation(
                        action=content[:200],
                        rationale="Extracted from output",
                    ))
                else:
                    findings.append(ParsedFinding(
                        title=content[:100],
                        description=content,
                    ))

        return ParseResult(
            success=bool(findings or recommendations),
            findings=findings,
            recommendations=recommendations,
            metrics={},
            raw_sections={},
            parse_method="fallback",
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_attr(self, attrs: str, name: str, default: Any = None) -> Any:
        """Extract attribute value from attribute string."""
        pattern = rf'{name}=["\']([^"\']+)["\']'
        match = re.search(pattern, attrs, re.IGNORECASE)
        return match.group(1) if match else default

    def _get_tag_content(self, text: str, tag: str) -> Optional[str]:
        """Extract content from a tag."""
        pattern = rf'<{tag}>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _get_tag_list(self, text: str, container: str, item: str) -> List[str]:
        """Extract list items from nested tags."""
        items = []

        # Try container/item pattern
        container_match = re.search(
            rf'<{container}>(.*?)</{container}>',
            text, re.DOTALL | re.IGNORECASE
        )
        if container_match:
            item_pattern = rf'<{item}>(.*?)</{item}>'
            items = re.findall(item_pattern, container_match.group(1), re.DOTALL | re.IGNORECASE)
            items = [i.strip() for i in items]

        return items

    def _get_first_line(self, text: str) -> str:
        """Get first non-empty line of text."""
        for line in text.split("\n"):
            line = line.strip()
            if line:
                return line
        return text[:100]
