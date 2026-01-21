"""
Authoricy Intelligence System - Data Models

Shared data models used across the system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class DomainInfo:
    """Basic domain information."""
    domain: str
    market: str
    language: str
    industry: str = "General"


@dataclass
class AnalysisRequest:
    """Request to analyze a domain."""
    domain: str
    email: str
    market: str = "Sweden"
    language: str = "sv"
    company_name: Optional[str] = None
    industry: Optional[str] = None
    competitors: Optional[List[str]] = None
    skip_ai_analysis: bool = False


@dataclass
class QualityMetrics:
    """Quality metrics for analysis."""
    data_completeness: int = 0
    evidence_quality: int = 0
    actionability: int = 0
    business_relevance: int = 0
    prioritization: int = 0
    internal_consistency: int = 0
    ai_visibility_coverage: int = 0
    technical_depth: int = 0

    @property
    def overall_score(self) -> float:
        """Calculate overall quality score."""
        scores = [
            self.data_completeness,
            self.evidence_quality,
            self.actionability,
            self.business_relevance,
            self.prioritization,
            self.internal_consistency,
            self.ai_visibility_coverage,
            self.technical_depth,
        ]
        return sum(scores) / len(scores)

    @property
    def passed(self) -> bool:
        """Check if quality gate passed (≥8.0)."""
        return self.overall_score >= 8.0
