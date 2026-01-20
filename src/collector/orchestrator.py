"""
Data Collection Orchestrator

Coordinates the multi-phase data collection process.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for data collection."""
    domain: str
    market: str = "Sweden"
    language: str = "sv"
    brand_name: Optional[str] = None
    industry: str = "General"
    competitors: Optional[List[str]] = None
    
    # Limits
    max_seed_keywords: int = 5
    max_competitors: int = 5
    max_backlinks: int = 500
    
    # Options
    skip_ai_analysis: bool = False
    skip_technical_audits: bool = False
    skip_phases: Optional[List[int]] = None
    early_termination_threshold: int = 10  # Min keywords to continue


@dataclass
class CollectionResult:
    """Result of data collection."""
    domain: str
    timestamp: datetime
    market: str
    language: str
    industry: str = "General"
    
    # Phase 1: Foundation
    domain_overview: Dict[str, Any] = field(default_factory=dict)
    historical_data: List[Dict] = field(default_factory=list)
    subdomains: List[Dict] = field(default_factory=list)
    top_pages: List[Dict] = field(default_factory=list)
    competitors: List[Dict] = field(default_factory=list)
    backlink_summary: Dict[str, Any] = field(default_factory=dict)
    technical_baseline: Dict[str, Any] = field(default_factory=dict)
    technologies: List[Dict] = field(default_factory=list)
    
    # Phase 2: Keywords
    ranked_keywords: List[Dict] = field(default_factory=list)
    keyword_gaps: List[Dict] = field(default_factory=list)
    keyword_clusters: List[Dict] = field(default_factory=list)
    
    # Phase 3: Competitive
    competitor_analysis: List[Dict] = field(default_factory=list)
    link_gaps: List[Dict] = field(default_factory=list)
    
    # Phase 4: AI & Technical
    ai_visibility: Dict[str, Any] = field(default_factory=dict)
    technical_audit: Dict[str, Any] = field(default_factory=dict)


class DataCollectionOrchestrator:
    """
    Orchestrates the multi-phase data collection process.
    
    Phases:
    1. Foundation - Domain basics, competitors, backlinks overview
    2. Keywords - Rankings, gaps, clusters
    3. Competitive - Detailed competitor analysis, link gaps
    4. AI & Technical - AI visibility, deep technical audit
    """
    
    def __init__(self, client):
        """
        Initialize orchestrator with DataForSEO client.
        
        Args:
            client: DataForSEOClient instance
        """
        self.client = client
    
    async def collect_all(self, config: CollectionConfig) -> CollectionResult:
        """
        Execute full data collection across all phases.
        
        Args:
            config: CollectionConfig with domain and settings
            
        Returns:
            CollectionResult with all collected data
        """
        start_time = datetime.utcnow()
        skip = config.skip_phases or []
        
        logger.info(f"Starting collection for {config.domain}")
        
        # Import phase collectors
        from src.collector.phase1 import collect_foundation_data
        
        # Phase 1: Foundation (always runs)
        logger.info("Phase 1: Collecting foundation data...")
        foundation = await collect_foundation_data(
            self.client, 
            config.domain, 
            config.market, 
            config.language
        )
        
        # Check for minimal domain
        if self._should_abbreviate(foundation):
            logger.info("Domain has minimal data - abbreviated analysis")
            return CollectionResult(
                domain=config.domain,
                timestamp=start_time,
                market=config.market,
                language=config.language,
                industry=config.industry,
                **foundation
            )
        
        # Extract competitors for later phases
        detected_competitors = config.competitors or self._extract_top_competitors(
            foundation, limit=config.max_competitors
        )
        
        # Phase 2: Keywords (if not skipped)
        keywords_data = {}
        if 2 not in skip:
            try:
                from src.collector.phase2 import collect_keyword_data
                logger.info("Phase 2: Collecting keyword data...")
                keywords_data = await collect_keyword_data(
                    self.client,
                    config.domain,
                    config.market,
                    config.language,
                    seed_keywords=self._extract_seed_keywords(foundation)
                )
            except ImportError:
                logger.warning("Phase 2 module not available, skipping...")
            except Exception as e:
                logger.error(f"Phase 2 failed: {e}")
        
        # Phase 3: Competitive (if not skipped)
        competitive_data = {}
        if 3 not in skip:
            try:
                from src.collector.phase3 import collect_competitive_data
                logger.info("Phase 3: Collecting competitive data...")
                competitive_data = await collect_competitive_data(
                    self.client,
                    config.domain,
                    detected_competitors,
                    config.market,
                    config.language,
                    priority_keywords=self._extract_priority_keywords(keywords_data)
                )
            except ImportError:
                logger.warning("Phase 3 module not available, skipping...")
            except Exception as e:
                logger.error(f"Phase 3 failed: {e}")
        
        # Phase 4: AI & Technical (if not skipped)
        ai_tech_data = {}
        if 4 not in skip:
            try:
                from src.collector.phase4 import collect_ai_technical_data
                logger.info("Phase 4: Collecting AI & technical data...")
                ai_tech_data = await collect_ai_technical_data(
                    self.client,
                    config.domain,
                    config.market,
                    config.language
                )
            except ImportError:
                logger.warning("Phase 4 module not available, skipping...")
            except Exception as e:
                logger.error(f"Phase 4 failed: {e}")
        
        collection_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Collection complete in {collection_time:.1f}s")
        
        # Merge all data
        all_data = {**foundation, **keywords_data, **competitive_data, **ai_tech_data}
        
        return CollectionResult(
            domain=config.domain,
            timestamp=start_time,
            market=config.market,
            language=config.language,
            industry=config.industry,
            **all_data
        )
    
    def _should_abbreviate(self, foundation: Dict) -> bool:
        """Check if domain has enough data for full analysis."""
        keywords = foundation.get("domain_overview", {}).get("organic_keywords", 0)
        backlinks = foundation.get("backlink_summary", {}).get("total_backlinks", 0)
        return keywords < 10 and backlinks < 50
    
    def _extract_top_competitors(self, foundation: Dict, limit: int = 5) -> List[str]:
        """Extract top competitor domains from foundation data."""
        competitors = foundation.get("competitors", [])
        return [c.get("domain") for c in competitors[:limit] if c.get("domain")]
    
    def _extract_seed_keywords(self, foundation: Dict) -> List[str]:
        """Extract seed keywords from top pages."""
        pages = foundation.get("top_pages", [])
        keywords = []
        for page in pages[:10]:
            if kw := page.get("main_keyword"):
                keywords.append(kw)
        return keywords[:5]
    
    def _extract_priority_keywords(self, keywords_data: Dict) -> List[str]:
        """Extract priority keywords for competitive analysis."""
        ranked = keywords_data.get("ranked_keywords", [])
        # Get keywords where we rank 4-20 (opportunity zone)
        priority = [
            kw.get("keyword") 
            for kw in ranked 
            if kw.get("keyword") and 4 <= kw.get("position", 100) <= 20
        ]
        return priority[:20]
