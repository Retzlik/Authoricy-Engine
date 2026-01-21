"""
Authoricy SEO Analyzer - Data Collection Package

This package handles all data collection from DataForSEO API:
- Phase 1: Foundation (domain overview, competitors, technical baseline)
- Phase 2: Keyword Intelligence (rankings, gaps, clusters)
- Phase 3: Competitive Intelligence (competitor metrics, backlinks)
- Phase 4: AI & Technical (AI visibility, brand mentions, audits)
"""

from .client import DataForSEOClient, DataForSEOError
from .orchestrator import (
    DataCollectionOrchestrator,
    CollectionConfig,
    CollectionResult,
    compile_analysis_data,
)
from .phase1 import collect_foundation_data
from .phase2 import collect_keyword_data
from .phase3 import collect_competitive_data
from .phase4 import collect_ai_technical_data

__all__ = [
    # Client
    "DataForSEOClient",
    "DataForSEOError",

    # Orchestrator
    "DataCollectionOrchestrator",
    "CollectionConfig",
    "CollectionResult",
    "compile_analysis_data",

    # Phase collectors
    "collect_foundation_data",
    "collect_keyword_data",
    "collect_competitive_data",
    "collect_ai_technical_data",
]
