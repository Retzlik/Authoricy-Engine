"""
Data Validators

Validates data at different stages of the analysis pipeline.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    details: Dict

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None, details: Optional[Dict] = None):
        """Create successful validation result."""
        return cls(
            valid=True,
            errors=[],
            warnings=warnings or [],
            details=details or {}
        )

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None, details: Optional[Dict] = None):
        """Create failed validation result."""
        return cls(
            valid=False,
            errors=errors,
            warnings=warnings or [],
            details=details or {}
        )


class DataValidator:
    """
    Validates collected data before analysis.

    Ensures data quality and completeness from DataForSEO API.
    """

    # Minimum data thresholds
    MIN_KEYWORDS = 10
    MIN_BACKLINKS = 5
    MIN_COMPETITORS = 2

    def validate_collection_result(self, data: Dict) -> ValidationResult:
        """
        Validate complete collection result.

        Args:
            data: CollectionResult as dictionary

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []
        details = {}

        # Check Phase 1: Foundation
        phase1_result = self._validate_phase1(data)
        if not phase1_result.valid:
            errors.extend(phase1_result.errors)
        warnings.extend(phase1_result.warnings)
        details["phase1"] = phase1_result.details

        # Check Phase 2: Keywords
        phase2_result = self._validate_phase2(data)
        if not phase2_result.valid:
            errors.extend(phase2_result.errors)
        warnings.extend(phase2_result.warnings)
        details["phase2"] = phase2_result.details

        # Check Phase 3: Competitive
        phase3_result = self._validate_phase3(data)
        if not phase3_result.valid:
            errors.extend(phase3_result.errors)
        warnings.extend(phase3_result.warnings)
        details["phase3"] = phase3_result.details

        # Check Phase 4: AI & Technical
        phase4_result = self._validate_phase4(data)
        if not phase4_result.valid:
            errors.extend(phase4_result.errors)
        warnings.extend(phase4_result.warnings)
        details["phase4"] = phase4_result.details

        if errors:
            return ValidationResult.failure(errors, warnings, details)
        return ValidationResult.success(warnings, details)

    def _validate_phase1(self, data: Dict) -> ValidationResult:
        """Validate Phase 1 foundation data."""
        errors = []
        warnings = []

        # Domain overview is critical
        domain_overview = data.get("domain_overview", {})
        if not domain_overview:
            errors.append("Missing domain overview data")
        elif domain_overview.get("organic_keywords", 0) == 0:
            warnings.append("Domain has no organic keywords detected")

        # Backlink summary
        backlinks = data.get("backlink_summary", {})
        if not backlinks:
            warnings.append("Missing backlink summary")
        elif backlinks.get("total_backlinks", 0) < self.MIN_BACKLINKS:
            warnings.append(f"Very few backlinks ({backlinks.get('total_backlinks', 0)})")

        # Competitors
        competitors = data.get("competitors", [])
        if len(competitors) < self.MIN_COMPETITORS:
            warnings.append(f"Few competitors identified ({len(competitors)})")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details={
                "has_overview": bool(domain_overview),
                "has_backlinks": bool(backlinks),
                "competitor_count": len(competitors)
            }
        )

    def _validate_phase2(self, data: Dict) -> ValidationResult:
        """Validate Phase 2 keyword data."""
        errors = []
        warnings = []

        ranked_keywords = data.get("ranked_keywords", [])
        if len(ranked_keywords) < self.MIN_KEYWORDS:
            if len(ranked_keywords) == 0:
                errors.append("No ranked keywords found")
            else:
                warnings.append(f"Very few keywords ({len(ranked_keywords)})")

        keyword_gaps = data.get("keyword_gaps", [])
        if len(keyword_gaps) == 0:
            warnings.append("No keyword gaps identified")

        intent_classification = data.get("intent_classification", {})
        if not intent_classification:
            warnings.append("Missing search intent classification")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details={
                "keyword_count": len(ranked_keywords),
                "gap_count": len(keyword_gaps),
                "has_intent": bool(intent_classification)
            }
        )

    def _validate_phase3(self, data: Dict) -> ValidationResult:
        """Validate Phase 3 competitive data."""
        errors = []
        warnings = []

        competitor_metrics = data.get("competitor_metrics", {})
        if not competitor_metrics and not data.get("competitor_analysis"):
            warnings.append("Missing competitor metrics")

        backlinks = data.get("backlinks", data.get("top_backlinks", []))
        if len(backlinks) == 0:
            warnings.append("No backlinks collected")

        link_gaps = data.get("link_gap_targets", data.get("link_gaps", []))
        if len(link_gaps) == 0:
            warnings.append("No link gap targets identified")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details={
                "has_competitor_metrics": bool(competitor_metrics),
                "backlink_count": len(backlinks),
                "link_gap_count": len(link_gaps)
            }
        )

    def _validate_phase4(self, data: Dict) -> ValidationResult:
        """Validate Phase 4 AI & technical data."""
        errors = []
        warnings = []

        ai_data = data.get("ai_keyword_data", [])
        if not ai_data:
            warnings.append("Missing AI keyword data")

        technical_audits = data.get("technical_audits", [])
        if not technical_audits:
            warnings.append("No technical audits completed")

        trend_data = data.get("trend_data", [])
        if not trend_data:
            warnings.append("Missing Google Trends data")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details={
                "has_ai_data": bool(ai_data),
                "audit_count": len(technical_audits) if isinstance(technical_audits, list) else 1,
                "has_trends": bool(trend_data)
            }
        )


class AnalysisValidator:
    """
    Validates AI analysis output.

    Ensures analysis meets quality standards before report generation.
    """

    REQUIRED_SECTIONS = [
        "executive_summary",
        "findings",
        "recommendations",
    ]

    MINIMUM_FINDINGS = 5
    MINIMUM_RECOMMENDATIONS = 3

    def validate_analysis_result(self, analysis: Dict) -> ValidationResult:
        """
        Validate complete analysis result.

        Args:
            analysis: Analysis result from analysis engine

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        details = {}

        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in analysis or not analysis[section]:
                errors.append(f"Missing required section: {section}")

        # Validate findings
        findings = analysis.get("findings", [])
        if len(findings) < self.MINIMUM_FINDINGS:
            if len(findings) == 0:
                errors.append("No findings in analysis")
            else:
                warnings.append(f"Few findings ({len(findings)} < {self.MINIMUM_FINDINGS})")

        # Validate recommendations
        recommendations = analysis.get("recommendations", [])
        if len(recommendations) < self.MINIMUM_RECOMMENDATIONS:
            if len(recommendations) == 0:
                errors.append("No recommendations in analysis")
            else:
                warnings.append(f"Few recommendations ({len(recommendations)} < {self.MINIMUM_RECOMMENDATIONS})")

        # Check quality score if present
        quality_score = analysis.get("quality_score")
        if quality_score is not None:
            if quality_score < 8.0:
                warnings.append(f"Quality score below threshold ({quality_score} < 8.0)")
            details["quality_score"] = quality_score

        # Check executive summary length
        exec_summary = analysis.get("executive_summary", "")
        if isinstance(exec_summary, str) and len(exec_summary) < 200:
            warnings.append("Executive summary too short")
        elif isinstance(exec_summary, dict):
            summary_text = exec_summary.get("summary", exec_summary.get("text", ""))
            if len(summary_text) < 200:
                warnings.append("Executive summary too short")

        details.update({
            "finding_count": len(findings),
            "recommendation_count": len(recommendations),
            "has_executive_summary": bool(analysis.get("executive_summary"))
        })

        if errors:
            return ValidationResult.failure(errors, warnings, details)
        return ValidationResult.success(warnings, details)

    def validate_loop_output(self, loop_name: str, output: Dict) -> ValidationResult:
        """Validate output from a specific analysis loop."""
        errors = []
        warnings = []

        if not output:
            return ValidationResult.failure([f"{loop_name} produced no output"])

        # Loop-specific validation
        if loop_name == "loop1":  # Data Interpretation
            if "findings" not in output:
                errors.append("Loop 1 missing findings")
            if "domain_classification" not in output:
                warnings.append("Loop 1 missing domain classification")

        elif loop_name == "loop2":  # Strategic Synthesis
            if "recommendations" not in output:
                errors.append("Loop 2 missing recommendations")
            if "roadmap" not in output:
                warnings.append("Loop 2 missing roadmap")

        elif loop_name == "loop3":  # SERP Enrichment
            if "serp_analysis" not in output and "content_briefs" not in output:
                warnings.append("Loop 3 missing SERP analysis")

        elif loop_name == "loop4":  # Quality Review
            if "quality_score" not in output:
                warnings.append("Loop 4 missing quality score")
            if "executive_summary" not in output:
                errors.append("Loop 4 missing executive summary")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)


class ReportValidator:
    """
    Validates generated reports before delivery.

    Ensures reports meet quality and format standards.
    """

    # Size limits
    MIN_EXTERNAL_PAGES = 8   # Lead magnet should be substantial
    MAX_EXTERNAL_PAGES = 20
    MIN_INTERNAL_PAGES = 30  # Strategy guide should be comprehensive
    MAX_INTERNAL_PAGES = 80

    # Approximate bytes per page
    BYTES_PER_PAGE = 50000  # ~50KB per page estimate

    def validate_external_report(self, pdf_bytes: bytes) -> ValidationResult:
        """Validate external (lead magnet) report."""
        errors = []
        warnings = []

        if not pdf_bytes:
            return ValidationResult.failure(["Empty PDF"])

        size_bytes = len(pdf_bytes)
        estimated_pages = size_bytes / self.BYTES_PER_PAGE

        if estimated_pages < self.MIN_EXTERNAL_PAGES:
            warnings.append(f"Report may be too short (~{estimated_pages:.0f} pages)")

        if estimated_pages > self.MAX_EXTERNAL_PAGES:
            warnings.append(f"Report may be too long (~{estimated_pages:.0f} pages)")

        # Check PDF header
        if not pdf_bytes.startswith(b'%PDF'):
            errors.append("Invalid PDF format")

        if errors:
            return ValidationResult.failure(errors, warnings, {"size_bytes": size_bytes})
        return ValidationResult.success(warnings, {"size_bytes": size_bytes, "estimated_pages": estimated_pages})

    def validate_internal_report(self, pdf_bytes: bytes) -> ValidationResult:
        """Validate internal (strategy guide) report."""
        errors = []
        warnings = []

        if not pdf_bytes:
            return ValidationResult.failure(["Empty PDF"])

        size_bytes = len(pdf_bytes)
        estimated_pages = size_bytes / self.BYTES_PER_PAGE

        if estimated_pages < self.MIN_INTERNAL_PAGES:
            warnings.append(f"Report may be too short (~{estimated_pages:.0f} pages)")

        if estimated_pages > self.MAX_INTERNAL_PAGES:
            warnings.append(f"Report may be too long (~{estimated_pages:.0f} pages)")

        # Check PDF header
        if not pdf_bytes.startswith(b'%PDF'):
            errors.append("Invalid PDF format")

        if errors:
            return ValidationResult.failure(errors, warnings, {"size_bytes": size_bytes})
        return ValidationResult.success(warnings, {"size_bytes": size_bytes, "estimated_pages": estimated_pages})

    def validate_report_content(self, html_content: str, report_type: str = "external") -> ValidationResult:
        """Validate report HTML content before PDF generation."""
        errors = []
        warnings = []

        if not html_content:
            return ValidationResult.failure(["Empty HTML content"])

        # Check for required elements
        required_elements = ["<html", "<body", "</html>", "</body>"]
        for elem in required_elements:
            if elem not in html_content.lower():
                errors.append(f"Missing required HTML element: {elem}")

        # Check for key content sections
        section_markers = [
            "executive-summary",
            "findings",
            "recommendations"
        ]

        found_sections = sum(1 for marker in section_markers if marker in html_content.lower())
        if found_sections < 2:
            warnings.append(f"Only {found_sections}/3 key sections found")

        # Check minimum content length
        min_length = 10000 if report_type == "external" else 30000
        if len(html_content) < min_length:
            warnings.append(f"Content may be too short ({len(html_content)} chars)")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings, {
            "content_length": len(html_content),
            "sections_found": found_sections
        })
