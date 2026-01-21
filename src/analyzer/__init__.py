"""
Authoricy Intelligence System - Analysis Engine

This module implements the 4-loop analysis architecture using Claude AI:
- Loop 1: Data Interpretation (raw data → structured findings)
- Loop 2: Strategic Synthesis (findings → recommendations)
- Loop 3: SERP & Competitor Enrichment (web research)
- Loop 4: Quality Review & Executive Summary
"""

from .client import ClaudeClient
from .engine import AnalysisEngine
from .loop1 import DataInterpreter
from .loop2 import StrategicSynthesizer
from .loop3 import SERPEnricher
from .loop4 import QualityReviewer

__all__ = [
    "ClaudeClient",
    "AnalysisEngine",
    "DataInterpreter",
    "StrategicSynthesizer",
    "SERPEnricher",
    "QualityReviewer",
]
