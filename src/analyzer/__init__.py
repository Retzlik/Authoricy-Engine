"""
Authoricy Intelligence System - Analysis Engine

Two architectures available:

v4 (Legacy): 4-Loop Architecture
- Loop 1: Data Interpretation
- Loop 2: Strategic Synthesis
- Loop 3: SERP & Competitor Enrichment
- Loop 4: Quality Review & Executive Summary

v5 (Current): 9-Agent Architecture
- 7 Primary Agents (run in parallel)
- 1 Conditional Agent (Local SEO)
- 1 Synthesis Agent (Master Strategy)
- 25-point quality gate (23/25 required)

Recommended: Use AnalysisEngineV5 for new implementations.
"""

from .client import ClaudeClient

# v4 Legacy (4-loop architecture)
from .engine import AnalysisEngine, AnalysisResult, DomainClassification
from .loop1 import DataInterpreter
from .loop2 import StrategicSynthesizer
from .loop3 import SERPEnricher
from .loop4 import QualityReviewer

# v5 Current (9-agent architecture)
from .engine_v5 import AnalysisEngineV5, AnalysisResultV5, create_analysis_engine

__all__ = [
    # Client
    "ClaudeClient",

    # v5 Engine (recommended)
    "AnalysisEngineV5",
    "AnalysisResultV5",
    "create_analysis_engine",

    # v4 Legacy Engine
    "AnalysisEngine",
    "AnalysisResult",
    "DomainClassification",

    # v4 Loop Components
    "DataInterpreter",
    "StrategicSynthesizer",
    "SERPEnricher",
    "QualityReviewer",
]
