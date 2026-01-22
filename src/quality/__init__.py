"""
Quality Gates

Enforces quality standards throughout the analysis pipeline.

Components:
- QualityGate: Base quality gate framework
- AgentQualityChecker: 25-point quality check system (23/25 required)
- AntiPatternDetector: Detects 6 anti-patterns in agent output
- Validators: Data, Analysis, and Report validation
"""

from .gates import QualityGate, QualityResult, QualityEnforcer
from .validators import DataValidator, AnalysisValidator, ReportValidator
from .checks import AgentQualityChecker, QualityCheck, CheckResult, CheckCategory
from .anti_patterns import AntiPatternDetector, AntiPatternMatch, AntiPatternResult, AntiPatternSeverity

__all__ = [
    # Gates
    "QualityGate",
    "QualityResult",
    "QualityEnforcer",
    # Validators
    "DataValidator",
    "AnalysisValidator",
    "ReportValidator",
    # Agent Quality Checks (25-point system)
    "AgentQualityChecker",
    "QualityCheck",
    "CheckResult",
    "CheckCategory",
    # Anti-Pattern Detection
    "AntiPatternDetector",
    "AntiPatternMatch",
    "AntiPatternResult",
    "AntiPatternSeverity",
]
