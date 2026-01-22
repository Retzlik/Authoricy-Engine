"""
Anti-Pattern Detection for Agent Outputs (v5 Specification)

Detects 6 key anti-patterns that indicate low-quality, generic output:

1. Hedge Everything - Excessive weasel words
2. Generic Best Practice - Non-customized advice
3. Data Dump Without Analysis - Lists without prioritization
4. Missing "So What" - Metrics without interpretation
5. Placeholder Text - Template/filler content
6. Contradictory Recommendations - Conflicting advice
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AntiPatternSeverity(Enum):
    """Severity of detected anti-pattern."""
    LOW = "low"          # Minor issue, doesn't fail
    MEDIUM = "medium"    # Concerning, should be addressed
    HIGH = "high"        # Major issue, likely fails quality
    CRITICAL = "critical"  # Immediate failure


@dataclass
class AntiPatternMatch:
    """A detected anti-pattern instance."""
    pattern_name: str
    severity: AntiPatternSeverity
    description: str
    location: str  # Excerpt where found
    suggestion: str


@dataclass
class AntiPatternResult:
    """Result of anti-pattern scan."""
    total_matches: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    matches: List[AntiPatternMatch]
    passes: bool  # True if no critical/high issues


class AntiPatternDetector:
    """
    Detects anti-patterns in agent output that indicate generic,
    low-quality content.

    Usage:
        detector = AntiPatternDetector()
        result = detector.scan(raw_output)
        if not result.passes:
            print(f"Found {result.critical_count} critical issues")
    """

    def __init__(self):
        """Initialize detector with pattern definitions."""
        self._patterns = self._define_patterns()

    def _define_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Define all anti-patterns with their detection rules."""
        return {
            # =================================================================
            # 1. HEDGE EVERYTHING
            # =================================================================
            "hedge_everything": {
                "name": "Hedge Everything",
                "description": "Excessive use of weasel words that undermine recommendations",
                "patterns": [
                    (r'\b(?:might|may|could)\s+(?:want to|need to|consider)\b', AntiPatternSeverity.MEDIUM),
                    (r'\b(?:potentially|possibly|perhaps)\s+\w+', AntiPatternSeverity.MEDIUM),
                    (r'\bit\s+(?:might|may|could)\s+be\s+(?:worth|beneficial|helpful)\b', AntiPatternSeverity.HIGH),
                    (r'\byou\s+(?:might|may|could)\s+(?:want|consider|try)\b', AntiPatternSeverity.MEDIUM),
                    (r'\bsomewhat|fairly|rather|quite\b', AntiPatternSeverity.LOW),
                ],
                "threshold": 10,  # Max acceptable occurrences
                "suggestion": "Replace hedging language with confident, specific recommendations. Instead of 'you might want to consider', use 'implement X to achieve Y'.",
            },

            # =================================================================
            # 2. GENERIC BEST PRACTICE
            # =================================================================
            "generic_best_practice": {
                "name": "Generic Best Practice",
                "description": "Non-specific advice that could apply to any website",
                "patterns": [
                    (r'\bfollow\s+(?:SEO\s+)?best\s+practices\b', AntiPatternSeverity.HIGH),
                    (r'\bimplement\s+industry\s+standards\b', AntiPatternSeverity.HIGH),
                    (r'\boptimize\s+(?:your\s+)?(?:website|content|pages)\b(?!\s+(?:for|by|to))', AntiPatternSeverity.MEDIUM),
                    (r'\bcreate\s+(?:quality|valuable|engaging)\s+content\b', AntiPatternSeverity.HIGH),
                    (r'\bbuild\s+(?:quality\s+)?(?:back)?links\b(?!\s+(?:from|to|by))', AntiPatternSeverity.MEDIUM),
                    (r'\bimprove\s+(?:your\s+)?(?:SEO|rankings|visibility)\b(?!\s+(?:for|by|through))', AntiPatternSeverity.MEDIUM),
                    (r'\bfocus\s+on\s+(?:user\s+)?experience\b', AntiPatternSeverity.MEDIUM),
                    (r'\bensure\s+(?:mobile|technical)\s+(?:optimization|friendliness)\b', AntiPatternSeverity.MEDIUM),
                ],
                "threshold": 3,
                "suggestion": "Replace generic advice with specific, actionable items. Specify WHICH content, WHICH keywords, WHICH pages, and HOW to optimize.",
            },

            # =================================================================
            # 3. DATA DUMP WITHOUT ANALYSIS
            # =================================================================
            "data_dump": {
                "name": "Data Dump Without Analysis",
                "description": "Lists of data without prioritization or interpretation",
                "patterns": [
                    # Long bullet lists without priority markers
                    (r'(?:^|\n)[\s]*[-•]\s*[^\n]+(?:\n[\s]*[-•]\s*[^\n]+){15,}', AntiPatternSeverity.HIGH),
                    # Numbered lists >20 items without P1/P2/P3
                    (r'(?:^|\n)\d+\.\s*[^\n]+(?:\n\d+\.\s*[^\n]+){20,}', AntiPatternSeverity.HIGH),
                    # Tables without analysis
                    (r'\|[^\n]+\|(?:\n\|[^\n]+\|){10,}(?!\n\n.*(?:priority|recommend|focus|suggest))', AntiPatternSeverity.MEDIUM),
                ],
                "threshold": 2,
                "suggestion": "Prioritize data into P1/P2/P3 categories. Add interpretation explaining significance and recommended action for top items.",
            },

            # =================================================================
            # 4. MISSING "SO WHAT"
            # =================================================================
            "missing_so_what": {
                "name": "Missing 'So What'",
                "description": "Metrics stated without context or business interpretation",
                "patterns": [
                    # Metric without comparison
                    (r'(?:DR|DA)\s+(?:is\s+)?\d+(?!\s*(?:compared|versus|vs|above|below|higher|lower))', AntiPatternSeverity.MEDIUM),
                    # Traffic number without context
                    (r'organic\s+traffic\s+(?:is\s+)?[\d,]+(?!\s*(?:compared|versus|vs|which|representing))', AntiPatternSeverity.MEDIUM),
                    # Keyword count without interpretation
                    (r'(?:ranking|ranks)\s+for\s+[\d,]+\s+keywords?(?!\s*(?:but|however|which|representing|compared))', AntiPatternSeverity.LOW),
                    # Standalone percentages
                    (r'\b\d+(?:\.\d+)?%(?!\s*(?:compared|versus|vs|increase|decrease|change|growth|decline|of\s+\w+\s+(?:comes?|is|are)))', AntiPatternSeverity.LOW),
                ],
                "threshold": 8,
                "suggestion": "Always explain metrics in context: compare to benchmark, explain trend, state business impact. 'DR 45' should become 'DR 45, which is 10 points below the SERP average of 55, indicating a link building opportunity'.",
            },

            # =================================================================
            # 5. PLACEHOLDER TEXT
            # =================================================================
            "placeholder_text": {
                "name": "Placeholder Text",
                "description": "Template or filler content not customized to the domain",
                "patterns": [
                    (r'based\s+on\s+(?:comprehensive|thorough|detailed|our)\s+analysis', AntiPatternSeverity.CRITICAL),
                    (r'according\s+to\s+(?:our|the)\s+(?:comprehensive|detailed|thorough)\s+(?:analysis|review|assessment)', AntiPatternSeverity.CRITICAL),
                    (r'\[.*?(?:placeholder|insert|your\s+\w+\s+here).*?\]', AntiPatternSeverity.CRITICAL),
                    (r'lorem\s+ipsum', AntiPatternSeverity.CRITICAL),
                    (r'\bTBD\b|\bTODO\b|\bFIXME\b|\bXXX\b', AntiPatternSeverity.CRITICAL),
                    (r'analysis\s+(?:shows|reveals|indicates)\s+that\s+(?:your|the)\s+(?:website|domain|site)\s+(?:has|needs|requires)', AntiPatternSeverity.HIGH),
                    (r'(?:key|main|primary)\s+(?:findings?|takeaways?|insights?)\s+(?:include|are)', AntiPatternSeverity.MEDIUM),
                ],
                "threshold": 0,  # Zero tolerance for critical
                "suggestion": "Replace template language with specific observations. Never say 'comprehensive analysis shows' - instead state the specific finding with data.",
            },

            # =================================================================
            # 6. CONTRADICTORY RECOMMENDATIONS
            # =================================================================
            "contradictory_recommendations": {
                "name": "Contradictory Recommendations",
                "description": "Conflicting advice within the same output",
                "patterns": [
                    # Focus vs don't focus contradictions
                    (r'focus\s+on\s+([^.]+)\..*?(?:don\'t|do\s+not|avoid)\s+(?:focus(?:ing)?|prioritiz(?:e|ing))\s+\1', AntiPatternSeverity.CRITICAL),
                    # Build vs don't build
                    (r'build\s+(?:more\s+)?([^.]+)\..*?(?:don\'t|avoid)\s+build(?:ing)?\s+\1', AntiPatternSeverity.HIGH),
                    # Conflicting priority signals
                    (r'(?:low|lower)\s+priority.*?same.*?(?:high|top|critical)\s+priority', AntiPatternSeverity.HIGH),
                ],
                "threshold": 0,
                "suggestion": "Review recommendations for conflicts. Ensure consistent prioritization and resolve any contradictions with clear rationale.",
            },
        }

    def scan(self, text: str, context: Optional[Dict[str, Any]] = None) -> AntiPatternResult:
        """
        Scan text for all anti-patterns.

        Args:
            text: Raw output text to scan
            context: Optional context for smarter detection

        Returns:
            AntiPatternResult with all matches
        """
        all_matches: List[AntiPatternMatch] = []

        for pattern_key, pattern_def in self._patterns.items():
            matches = self._detect_pattern(text, pattern_key, pattern_def)
            all_matches.extend(matches)

        # Count by severity
        critical = sum(1 for m in all_matches if m.severity == AntiPatternSeverity.CRITICAL)
        high = sum(1 for m in all_matches if m.severity == AntiPatternSeverity.HIGH)
        medium = sum(1 for m in all_matches if m.severity == AntiPatternSeverity.MEDIUM)
        low = sum(1 for m in all_matches if m.severity == AntiPatternSeverity.LOW)

        # Pass if no critical issues and high issues < 3
        passes = critical == 0 and high < 3

        return AntiPatternResult(
            total_matches=len(all_matches),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            matches=all_matches,
            passes=passes,
        )

    def _detect_pattern(
        self,
        text: str,
        pattern_key: str,
        pattern_def: Dict[str, Any]
    ) -> List[AntiPatternMatch]:
        """Detect a specific anti-pattern in text."""
        matches = []

        for regex, severity in pattern_def["patterns"]:
            found = re.finditer(regex, text, re.IGNORECASE | re.MULTILINE)

            for match in found:
                # Get context around match
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                location = "..." + text[start:end].replace("\n", " ") + "..."

                matches.append(AntiPatternMatch(
                    pattern_name=pattern_def["name"],
                    severity=severity,
                    description=pattern_def["description"],
                    location=location,
                    suggestion=pattern_def["suggestion"],
                ))

        return matches

    def get_summary(self, result: AntiPatternResult) -> Dict[str, Any]:
        """
        Get a summary of anti-pattern scan results.

        Args:
            result: AntiPatternResult from scan()

        Returns:
            Summary dict for reporting
        """
        by_pattern = {}
        for match in result.matches:
            if match.pattern_name not in by_pattern:
                by_pattern[match.pattern_name] = {
                    "count": 0,
                    "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                }
            by_pattern[match.pattern_name]["count"] += 1
            by_pattern[match.pattern_name]["severity_counts"][match.severity.value] += 1

        return {
            "passes": result.passes,
            "total_issues": result.total_matches,
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
            "by_pattern": by_pattern,
            "top_issues": [
                {
                    "pattern": m.pattern_name,
                    "severity": m.severity.value,
                    "location": m.location[:100] + "..." if len(m.location) > 100 else m.location,
                }
                for m in result.matches[:5]
                if m.severity in [AntiPatternSeverity.CRITICAL, AntiPatternSeverity.HIGH]
            ],
        }

    def get_improvement_suggestions(self, result: AntiPatternResult) -> List[str]:
        """
        Get prioritized improvement suggestions.

        Args:
            result: AntiPatternResult from scan()

        Returns:
            List of suggestions ordered by severity
        """
        suggestions = set()

        # Sort matches by severity
        sorted_matches = sorted(
            result.matches,
            key=lambda m: ["critical", "high", "medium", "low"].index(m.severity.value)
        )

        for match in sorted_matches:
            suggestions.add(f"[{match.severity.value.upper()}] {match.pattern_name}: {match.suggestion}")

        return list(suggestions)[:10]  # Return top 10


def quick_scan(text: str) -> Tuple[bool, int, List[str]]:
    """
    Quick utility function for anti-pattern scanning.

    Args:
        text: Text to scan

    Returns:
        Tuple of (passes, issue_count, suggestions)
    """
    detector = AntiPatternDetector()
    result = detector.scan(text)
    suggestions = detector.get_improvement_suggestions(result)

    return result.passes, result.total_matches, suggestions
