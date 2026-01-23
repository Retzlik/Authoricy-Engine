"""
Data Quality Validation Layer

Validates data BEFORE it goes to AI agents.
Ensures we never feed garbage to expensive AI calls.

Design Philosophy:
- Fail fast with clear error messages
- Distinguish between "no data" (API issue) and "bad data" (quality issue)
- Provide actionable validation reports
- Gate AI analysis on minimum data quality
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .models import DataQualityLevel, CompetitorType
from src.utils.domain_filter import is_excluded_domain

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================

@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: str  # critical, warning, info
    category: str  # data_missing, data_invalid, data_incomplete, data_suspicious
    field: str     # Which field has the issue
    message: str   # Human-readable description
    value: Any = None  # The problematic value (for debugging)


@dataclass
class DataQualityReport:
    """Comprehensive data quality assessment"""
    # Overall assessment
    quality_level: DataQualityLevel = DataQualityLevel.POOR
    quality_score: float = 0.0  # 0-100
    is_sufficient_for_analysis: bool = False

    # Issue tracking
    issues: List[ValidationIssue] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    # Data coverage
    coverage: Dict[str, float] = field(default_factory=dict)  # category -> % complete

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def add_issue(self, severity: str, category: str, field: str, message: str, value: Any = None):
        """Add a validation issue"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            field=field,
            message=message,
            value=value
        )
        self.issues.append(issue)

        if severity == "critical":
            self.critical_count += 1
        elif severity == "warning":
            self.warning_count += 1
        else:
            self.info_count += 1

    def calculate_quality_level(self):
        """Calculate overall quality level from score"""
        if self.quality_score >= 90:
            self.quality_level = DataQualityLevel.EXCELLENT
        elif self.quality_score >= 70:
            self.quality_level = DataQualityLevel.GOOD
        elif self.quality_score >= 50:
            self.quality_level = DataQualityLevel.FAIR
        elif self.quality_score > 0:
            self.quality_level = DataQualityLevel.POOR
        else:
            self.quality_level = DataQualityLevel.INVALID

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "quality_level": self.quality_level.value,
            "quality_score": self.quality_score,
            "is_sufficient_for_analysis": self.is_sufficient_for_analysis,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "field": i.field,
                    "message": i.message,
                }
                for i in self.issues
            ],
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "coverage": self.coverage,
            "recommendations": self.recommendations,
        }


# =============================================================================
# MINIMUM THRESHOLDS
# =============================================================================

# Minimum data requirements for meaningful analysis
MIN_REQUIREMENTS = {
    # Keywords
    "keywords_total": 10,           # Need at least 10 keywords
    "keywords_with_volume": 5,      # At least 5 with search volume
    "keywords_with_position": 3,    # At least 3 where we know position

    # Competitors
    "competitors_true": 2,          # At least 2 TRUE competitors (not platforms)
    "competitors_total": 3,         # At least 3 total

    # Backlinks
    "backlinks_total": 10,          # At least 10 backlinks
    "backlinks_quality": 3,         # At least 3 quality backlinks

    # Domain metrics
    "domain_rating": True,          # Must have domain rating
    "organic_traffic": True,        # Must have traffic estimate
}

# Thresholds for quality scoring
QUALITY_WEIGHTS = {
    "keywords": 0.30,       # 30% of quality score
    "competitors": 0.25,    # 25% of quality score
    "backlinks": 0.20,      # 20% of quality score
    "domain_metrics": 0.15, # 15% of quality score
    "technical": 0.10,      # 10% of quality score
}


# =============================================================================
# CORE VALIDATION FUNCTION
# =============================================================================

def validate_run_data(data: Dict[str, Any]) -> DataQualityReport:
    """
    Validate all collected data before AI analysis.

    This is THE GATE that prevents garbage-in-garbage-out.

    Args:
        data: Collected data from all phases
            Expected structure:
            {
                "domain_info": {...},
                "keywords": [...],
                "competitors": [...],
                "backlinks": [...],
                "pages": [...],
                "technical": {...},
            }

    Returns:
        DataQualityReport with comprehensive quality assessment
    """
    report = DataQualityReport()

    # Validate each category
    keywords_score = _validate_keywords(data.get("keywords", []), report)
    competitors_score = _validate_competitors(data.get("competitors", []), report)
    backlinks_score = _validate_backlinks(data.get("backlinks", []), report)
    domain_score = _validate_domain_metrics(data.get("domain_info", {}), report)
    technical_score = _validate_technical(data.get("technical", {}), report)

    # Store coverage
    report.coverage = {
        "keywords": keywords_score,
        "competitors": competitors_score,
        "backlinks": backlinks_score,
        "domain_metrics": domain_score,
        "technical": technical_score,
    }

    # Calculate weighted quality score
    report.quality_score = (
        keywords_score * QUALITY_WEIGHTS["keywords"] +
        competitors_score * QUALITY_WEIGHTS["competitors"] +
        backlinks_score * QUALITY_WEIGHTS["backlinks"] +
        domain_score * QUALITY_WEIGHTS["domain_metrics"] +
        technical_score * QUALITY_WEIGHTS["technical"]
    )

    report.calculate_quality_level()

    # Determine if sufficient for analysis
    report.is_sufficient_for_analysis = (
        report.critical_count == 0 and
        report.quality_score >= 40  # Minimum 40% quality
    )

    # Generate recommendations
    _generate_recommendations(report)

    logger.info(
        f"Data validation complete: {report.quality_level.value} "
        f"(score: {report.quality_score:.1f}%, "
        f"critical: {report.critical_count}, "
        f"warnings: {report.warning_count})"
    )

    return report


# =============================================================================
# CATEGORY VALIDATORS
# =============================================================================

def _validate_keywords(keywords: List[Dict], report: DataQualityReport) -> float:
    """Validate keyword data. Returns quality score 0-100."""
    if not keywords:
        report.add_issue(
            "critical", "data_missing", "keywords",
            "No keywords found - cannot perform SEO analysis"
        )
        return 0.0

    total = len(keywords)
    score = 0.0

    # Check minimum count
    if total < MIN_REQUIREMENTS["keywords_total"]:
        report.add_issue(
            "warning", "data_incomplete", "keywords",
            f"Only {total} keywords found, recommend at least {MIN_REQUIREMENTS['keywords_total']}"
        )
        score += 20 * (total / MIN_REQUIREMENTS["keywords_total"])
    else:
        score += 20

    # Check search volume coverage
    with_volume = sum(1 for k in keywords if k.get("search_volume") and k["search_volume"] > 0)
    volume_pct = (with_volume / total) * 100 if total > 0 else 0

    if with_volume < MIN_REQUIREMENTS["keywords_with_volume"]:
        report.add_issue(
            "warning", "data_incomplete", "keywords.search_volume",
            f"Only {with_volume} keywords have search volume data ({volume_pct:.0f}%)"
        )
    score += min(30, 30 * (volume_pct / 70))  # Full points at 70% coverage

    # Check position data
    with_position = sum(1 for k in keywords if k.get("current_position") or k.get("position"))
    position_pct = (with_position / total) * 100 if total > 0 else 0

    if with_position < MIN_REQUIREMENTS["keywords_with_position"]:
        report.add_issue(
            "warning", "data_incomplete", "keywords.position",
            f"Only {with_position} keywords have ranking position"
        )
    score += min(30, 30 * (position_pct / 50))  # Full points at 50% coverage

    # Check for suspicious data
    zero_volume_count = sum(1 for k in keywords if k.get("search_volume") == 0)
    if zero_volume_count > total * 0.5:
        report.add_issue(
            "warning", "data_suspicious", "keywords.search_volume",
            f"{zero_volume_count} keywords have zero search volume - may indicate API issue"
        )

    # Check for duplicates
    unique_keywords = set(k.get("keyword", "").lower().strip() for k in keywords)
    duplicate_count = total - len(unique_keywords)
    if duplicate_count > 5:
        report.add_issue(
            "info", "data_invalid", "keywords",
            f"{duplicate_count} duplicate keywords found"
        )
    score += 20 - min(20, duplicate_count)  # Lose points for duplicates

    return min(100, score)


def _validate_competitors(competitors: List[Dict], report: DataQualityReport) -> float:
    """Validate competitor data. Returns quality score 0-100."""
    if not competitors:
        report.add_issue(
            "critical", "data_missing", "competitors",
            "No competitors found - cannot perform competitive analysis"
        )
        return 0.0

    total = len(competitors)
    score = 0.0

    # Count TRUE competitors (not platforms, media, etc.)
    true_competitors = [
        c for c in competitors
        if c.get("competitor_type") in [
            "true_competitor",
            CompetitorType.TRUE_COMPETITOR.value if hasattr(CompetitorType, 'TRUE_COMPETITOR') else None,
            None,  # Unknown = potential competitor
        ] and c.get("competitor_type") not in ["platform", "media", "government"]
    ]

    true_count = len(true_competitors)

    if true_count < MIN_REQUIREMENTS["competitors_true"]:
        report.add_issue(
            "warning", "data_incomplete", "competitors.true",
            f"Only {true_count} true competitors identified (need {MIN_REQUIREMENTS['competitors_true']})"
        )
        score += 30 * (true_count / MIN_REQUIREMENTS["competitors_true"])
    else:
        score += 30

    # Check for minimum total
    if total < MIN_REQUIREMENTS["competitors_total"]:
        report.add_issue(
            "warning", "data_incomplete", "competitors",
            f"Only {total} total competitors found"
        )
    score += min(20, 20 * (total / MIN_REQUIREMENTS["competitors_total"]))

    # Check competitor metrics coverage
    with_traffic = sum(1 for c in competitors if c.get("organic_traffic"))
    with_keywords = sum(1 for c in competitors if c.get("organic_keywords"))
    with_rating = sum(1 for c in competitors if c.get("domain_rating"))

    metrics_coverage = (
        (with_traffic / total if total else 0) +
        (with_keywords / total if total else 0) +
        (with_rating / total if total else 0)
    ) / 3

    score += 30 * metrics_coverage

    # Check for platform pollution (Facebook, YouTube, etc. as "competitors")
    # Use both type-based check AND domain filter for defense in depth
    platforms_by_type = [c for c in competitors if c.get("competitor_type") == "platform"]
    platforms_by_domain = [c for c in competitors if is_excluded_domain(c.get("competitor_domain", ""))]
    platforms = list(set([c.get("competitor_domain", "") for c in platforms_by_type + platforms_by_domain]))

    if len(platforms) > 0:
        platform_ratio = len(platforms) / total if total else 0
        if platform_ratio > 0.2:  # More than 20% platforms = CRITICAL
            report.add_issue(
                "critical", "data_suspicious", "competitors",
                f"{len(platforms)} platforms ({platform_ratio:.0%}) detected as competitors: {', '.join(platforms[:5])}"
            )
            score -= 40  # Heavy penalty
        elif platform_ratio > 0.1:  # 10-20% = WARNING
            report.add_issue(
                "warning", "data_suspicious", "competitors",
                f"{len(platforms)} platforms detected as competitors - data quality impacted"
            )
            score -= 20

    # Bonus for keyword overlap data
    with_overlap = sum(1 for c in competitors if c.get("keyword_overlap_count"))
    score += min(20, 20 * (with_overlap / total if total else 0))

    return min(100, max(0, score))


def _validate_backlinks(backlinks: List[Dict], report: DataQualityReport) -> float:
    """Validate backlink data. Returns quality score 0-100."""
    if not backlinks:
        report.add_issue(
            "warning", "data_missing", "backlinks",
            "No backlinks found - limited link analysis possible"
        )
        return 20.0  # Not critical, but impacts analysis

    total = len(backlinks)
    score = 20.0  # Base score for having data

    # Check minimum count
    if total < MIN_REQUIREMENTS["backlinks_total"]:
        report.add_issue(
            "info", "data_incomplete", "backlinks",
            f"Only {total} backlinks found"
        )
    score += min(30, 30 * (total / MIN_REQUIREMENTS["backlinks_total"]))

    # Check source domain coverage
    with_source_domain = sum(1 for b in backlinks if b.get("source_domain"))
    score += min(20, 20 * (with_source_domain / total if total else 0))

    # Check quality metrics
    with_dr = sum(1 for b in backlinks if b.get("source_domain_rating") or b.get("domain_rating"))
    quality_pct = (with_dr / total) * 100 if total else 0
    score += min(20, 20 * (quality_pct / 50))

    # Check for anchor text
    with_anchor = sum(1 for b in backlinks if b.get("anchor_text"))
    score += min(10, 10 * (with_anchor / total if total else 0))

    return min(100, score)


def _validate_domain_metrics(domain_info: Dict, report: DataQualityReport) -> float:
    """Validate domain-level metrics. Returns quality score 0-100."""
    if not domain_info:
        report.add_issue(
            "critical", "data_missing", "domain_info",
            "No domain metrics found - cannot assess domain strength"
        )
        return 0.0

    score = 20.0  # Base score for having data

    # Check required metrics
    if not domain_info.get("domain_rating") and not domain_info.get("domain_rank"):
        report.add_issue(
            "warning", "data_missing", "domain_info.domain_rating",
            "Domain rating/rank not available"
        )
    else:
        score += 20

    if not domain_info.get("organic_traffic"):
        report.add_issue(
            "warning", "data_missing", "domain_info.organic_traffic",
            "Organic traffic estimate not available"
        )
    else:
        score += 20

    if not domain_info.get("organic_keywords"):
        report.add_issue(
            "info", "data_missing", "domain_info.organic_keywords",
            "Organic keywords count not available"
        )
    else:
        score += 15

    if not domain_info.get("referring_domains"):
        report.add_issue(
            "info", "data_missing", "domain_info.referring_domains",
            "Referring domains count not available"
        )
    else:
        score += 15

    # Check for technologies
    if domain_info.get("technologies"):
        score += 10

    return min(100, score)


def _validate_technical(technical: Dict, report: DataQualityReport) -> float:
    """Validate technical metrics. Returns quality score 0-100."""
    if not technical:
        report.add_issue(
            "info", "data_missing", "technical",
            "No technical metrics available - limited technical analysis"
        )
        return 30.0  # Not critical

    score = 30.0  # Base score

    # Check Lighthouse scores
    lighthouse_fields = ["performance_score", "accessibility_score", "seo_score", "best_practices_score"]
    lighthouse_present = sum(1 for f in lighthouse_fields if technical.get(f) is not None)
    score += 30 * (lighthouse_present / len(lighthouse_fields))

    # Check Core Web Vitals
    cwv_fields = ["lcp", "fid", "cls", "inp"]
    cwv_present = sum(1 for f in cwv_fields if technical.get(f) is not None)
    score += 20 * (cwv_present / len(cwv_fields))

    # Check for issues data
    if technical.get("issues") or technical.get("issues_detail"):
        score += 20

    return min(100, score)


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

def _generate_recommendations(report: DataQualityReport):
    """Generate actionable recommendations based on validation results"""

    if report.coverage.get("keywords", 0) < 50:
        report.recommendations.append(
            "Collect more keyword data - consider expanding seed keywords or using keyword suggestions API"
        )

    if report.coverage.get("competitors", 0) < 50:
        report.recommendations.append(
            "Competitor identification needs improvement - review filtering logic or expand SERP analysis"
        )

    if report.coverage.get("backlinks", 0) < 40:
        report.recommendations.append(
            "Limited backlink data - analysis may not reflect true link profile"
        )

    if report.coverage.get("domain_metrics", 0) < 60:
        report.recommendations.append(
            "Core domain metrics missing - check API responses for domain overview calls"
        )

    if report.critical_count > 0:
        report.recommendations.append(
            "CRITICAL: Fix data collection issues before running AI analysis"
        )

    if report.quality_score < 50:
        report.recommendations.append(
            "Overall data quality is low - consider re-running data collection or checking API limits"
        )


# =============================================================================
# QUICK VALIDATORS (for specific checks)
# =============================================================================

def validate_keyword(keyword_data: Dict) -> Tuple[bool, List[str]]:
    """Quick validation for a single keyword"""
    errors = []

    if not keyword_data.get("keyword"):
        errors.append("Missing keyword text")
        return False, errors

    if len(keyword_data["keyword"]) > 500:
        errors.append("Keyword too long (max 500 chars)")

    return len(errors) == 0, errors


def validate_competitor(competitor_data: Dict) -> Tuple[bool, List[str]]:
    """Quick validation for a single competitor"""
    errors = []

    if not competitor_data.get("competitor_domain"):
        errors.append("Missing competitor domain")
        return False, errors

    domain = competitor_data["competitor_domain"]

    # Basic domain validation
    if not "." in domain:
        errors.append(f"Invalid domain format: {domain}")

    return len(errors) == 0, errors


def validate_backlink(backlink_data: Dict) -> Tuple[bool, List[str]]:
    """Quick validation for a single backlink"""
    errors = []

    if not backlink_data.get("source_url") and not backlink_data.get("source_domain"):
        errors.append("Missing source URL or domain")
        return False, errors

    return len(errors) == 0, errors


# =============================================================================
# QUALITY GATE
# =============================================================================

class QualityGate:
    """
    Quality gate for AI analysis.

    Use this to decide whether to proceed with (expensive) AI analysis.
    """

    def __init__(self, min_score: float = 40.0, allow_warnings: bool = True):
        self.min_score = min_score
        self.allow_warnings = allow_warnings

    def check(self, report: DataQualityReport) -> Tuple[bool, str]:
        """
        Check if data passes quality gate.

        Returns:
            (passed, reason)
        """
        if report.critical_count > 0:
            return False, f"Critical issues found: {report.critical_count}"

        if report.quality_score < self.min_score:
            return False, f"Quality score {report.quality_score:.1f}% below minimum {self.min_score}%"

        if not self.allow_warnings and report.warning_count > 0:
            return False, f"Warnings not allowed: {report.warning_count} warnings"

        return True, f"Quality gate passed (score: {report.quality_score:.1f}%)"


# Default quality gate for production
default_quality_gate = QualityGate(min_score=40.0, allow_warnings=True)
