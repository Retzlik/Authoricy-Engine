"""
Report Confidence Tracking

Tracks what data is actually present vs missing in reports.
Makes generic fallbacks VISIBLE so we can fix them.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """A single data point that should be in the report."""
    name: str
    section: str
    source: str  # "agent" or "raw_data"
    required: bool = True
    present: bool = False
    value: Any = None
    fallback_used: bool = False


@dataclass
class ReportConfidence:
    """
    Tracks confidence level of a report.

    This makes it IMPOSSIBLE to generate a garbage report silently.
    """
    data_points: List[DataPoint] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def track(self, name: str, section: str, source: str, value: Any,
              required: bool = True) -> Any:
        """
        Track a data point and return the value.

        Returns None if value is empty/missing.
        """
        is_present = self._has_value(value)

        self.data_points.append(DataPoint(
            name=name,
            section=section,
            source=source,
            required=required,
            present=is_present,
            value=value if is_present else None,
            fallback_used=False,
        ))

        if not is_present and required:
            self.warnings.append(f"MISSING: {name} in {section}")
            logger.warning(f"Report data missing: {name} in {section}")

        return value if is_present else None

    def track_fallback(self, name: str, section: str, fallback_value: str) -> None:
        """Track when a fallback value is used."""
        self.data_points.append(DataPoint(
            name=name,
            section=section,
            source="fallback",
            required=True,
            present=False,
            value=None,
            fallback_used=True,
        ))
        self.warnings.append(f"FALLBACK USED: {name} in {section}")
        logger.warning(f"Report using fallback: {name} in {section} -> '{fallback_value[:50]}...'")

    def _has_value(self, value: Any) -> bool:
        """Check if value is present and meaningful."""
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        return True

    @property
    def confidence_score(self) -> float:
        """
        Calculate confidence score 0-100.

        Higher = more real data, lower = more fallbacks.
        """
        if not self.data_points:
            return 0.0

        required_points = [dp for dp in self.data_points if dp.required]
        if not required_points:
            return 100.0

        present_count = sum(1 for dp in required_points if dp.present)
        return (present_count / len(required_points)) * 100

    @property
    def confidence_level(self) -> str:
        """Human-readable confidence level."""
        score = self.confidence_score
        if score >= 80:
            return "HIGH"
        elif score >= 50:
            return "MEDIUM"
        elif score >= 20:
            return "LOW"
        else:
            return "VERY LOW"

    @property
    def fallback_count(self) -> int:
        """Count of fallbacks used."""
        return sum(1 for dp in self.data_points if dp.fallback_used)

    @property
    def missing_required(self) -> List[str]:
        """List of missing required data points."""
        return [
            f"{dp.name} ({dp.section})"
            for dp in self.data_points
            if dp.required and not dp.present
        ]

    def get_section_confidence(self, section: str) -> float:
        """Get confidence for a specific section."""
        section_points = [dp for dp in self.data_points if dp.section == section and dp.required]
        if not section_points:
            return 100.0
        present = sum(1 for dp in section_points if dp.present)
        return (present / len(section_points)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "fallback_count": self.fallback_count,
            "total_data_points": len(self.data_points),
            "present_data_points": sum(1 for dp in self.data_points if dp.present),
            "missing_required": self.missing_required,
            "warnings": self.warnings,
            "sections": {
                section: self.get_section_confidence(section)
                for section in set(dp.section for dp in self.data_points)
            }
        }

    def generate_warning_html(self) -> str:
        """Generate HTML warning banner if confidence is low."""
        score = self.confidence_score
        level = self.confidence_level

        if score >= 80:
            return ""  # No warning needed

        color = "#f72585" if score < 50 else "#ff9500"

        missing_list = "".join(
            f"<li>{item}</li>"
            for item in self.missing_required[:5]
        )

        return f"""
        <div style="background: {color}; color: white; padding: 20px; margin: 20px 0; border-radius: 8px;">
            <strong>⚠️ Report Confidence: {level} ({score:.0f}%)</strong>
            <p style="margin-top: 10px;">Some data was unavailable. The following sections use estimated or generic content:</p>
            <ul style="margin-top: 10px;">{missing_list}</ul>
            <p style="margin-top: 10px; font-size: 10pt;">This may indicate issues with data collection. Contact support if this persists.</p>
        </div>
        """


# =============================================================================
# ANTI-GENERIC DETECTION
# =============================================================================

GENERIC_PHRASES = [
    "key opportunities identified",
    "comprehensive analysis has been completed",
    "schedule a strategy session",
    "opportunities have been identified",
    "analysis complete",
    "contact us for more",
    "varies by industry",
    "based on analysis",
    "significant opportunity",
    "strategic improvement",
    "optimize your",
    "enhance your",
    "improve your",
    "boost your",
    "increase your",
    "grow your",
    "expand your",
]

PLACEHOLDER_PATTERNS = [
    r"\[.*?\]",  # [INSERT DATA HERE]
    r"\{.*?\}",  # {PLACEHOLDER}
    r"N/A",
    r"TBD",
    r"TODO",
    r"FIXME",
    r"XXX",
]


def detect_generic_content(text: str) -> List[str]:
    """
    Detect generic/placeholder content in text.

    Returns list of detected issues.
    """
    import re

    issues = []
    text_lower = text.lower()

    # Check for generic phrases
    for phrase in GENERIC_PHRASES:
        if phrase in text_lower:
            issues.append(f"Generic phrase detected: '{phrase}'")

    # Check for placeholder patterns
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            issues.append(f"Placeholder detected: '{match}'")

    return issues


def is_data_driven(text: str, min_numbers: int = 3) -> bool:
    """
    Check if text contains real data (numbers, percentages, etc.)

    Data-driven content should have specific numbers, not generic advice.
    """
    import re

    # Count numbers (but not just single digits in common text)
    numbers = re.findall(r'\b\d{2,}\b', text)  # 2+ digit numbers
    percentages = re.findall(r'\d+%', text)
    currencies = re.findall(r'\$[\d,]+', text)

    total_data_points = len(numbers) + len(percentages) + len(currencies)

    return total_data_points >= min_numbers


# =============================================================================
# EXPLICIT DATA MISSING INDICATORS
# =============================================================================

def data_missing_html(data_name: str, section: str) -> str:
    """
    Generate explicit "DATA MISSING" indicator instead of silent fallback.

    This makes it OBVIOUS when reports are missing data.
    """
    return f"""
    <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 10px 0; border-radius: 4px;">
        <strong>📊 Data Unavailable: {data_name}</strong>
        <p style="margin-top: 5px; font-size: 10pt; color: #856404;">
            This section requires data that wasn't collected or analyzed.
            The analysis may need to be re-run with complete data.
        </p>
    </div>
    """


def partial_data_html(data_name: str, available: str, missing: str) -> str:
    """
    Show what data we have and what's missing.
    """
    return f"""
    <div style="background: #e7f5ff; border: 1px solid #74c0fc; padding: 15px; margin: 10px 0; border-radius: 4px;">
        <strong>ℹ️ Partial Data: {data_name}</strong>
        <p style="margin-top: 5px; font-size: 10pt;">
            <strong>Available:</strong> {available}<br>
            <strong>Missing:</strong> {missing}
        </p>
    </div>
    """
