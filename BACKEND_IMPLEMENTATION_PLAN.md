# Backend Implementation Plan: Greenfield Intelligence

**Status:** Implementation Required
**Priority:** High
**Estimated Effort:** 4-6 weeks engineering time

---

## Executive Summary

The Greenfield Domain Brief (5,700+ lines) is a comprehensive specification, but the backend currently does NOT implement it. This document provides the exact implementation steps to make greenfield intelligence operational.

**Current State:** Greenfield domains detected → abbreviated analysis returned → user gets empty dashboard
**Target State:** Greenfield domains detected → competitor-first collection → rich intelligence dashboard

---

## Table of Contents

1. [Database Schema Changes](#1-database-schema-changes)
2. [Orchestrator Modifications](#2-orchestrator-modifications)
3. [Greenfield Collection Pipeline](#3-greenfield-collection-pipeline)
4. [API Endpoints](#4-api-endpoints)
5. [Scoring Module Integration](#5-scoring-module-integration)
6. [Strategy Builder Updates](#6-strategy-builder-updates)
7. [Testing Requirements](#7-testing-requirements)
8. [Migration Strategy](#8-migration-strategy)
9. [Implementation Phases](#9-implementation-phases)

---

## 1. Database Schema Changes

### 1.1 Modify AnalysisRun Model

**File:** `src/database/models.py`

```python
class AnalysisMode(enum.Enum):
    """Analysis mode based on domain maturity"""
    STANDARD = "standard"        # Established domain (DR>35, KW>200)
    GREENFIELD = "greenfield"    # New domain (DR<20, KW<50)
    HYBRID = "hybrid"            # Emerging domain (DR 20-35)


class AnalysisRun(Base):
    # ... existing fields ...

    # NEW: Analysis mode tracking
    analysis_mode = Column(Enum(AnalysisMode), default=AnalysisMode.STANDARD)
    domain_maturity_at_analysis = Column(String(20))  # greenfield, emerging, established
    domain_rating_at_analysis = Column(Integer)
    organic_keywords_at_analysis = Column(Integer)
    organic_traffic_at_analysis = Column(Integer)

    # NEW: Greenfield context (user-provided)
    greenfield_context = Column(JSONB, nullable=True)
    """
    {
        "business_name": "CloudInvoice",
        "business_description": "...",
        "primary_offering": "Invoice software",
        "target_market": "United States",
        "industry_vertical": "saas",
        "seed_keywords": ["invoice software", "billing automation", ...],
        "known_competitors": ["freshbooks.com", "zoho.com/invoice", ...]
    }
    """
```

### 1.2 Extend Keyword Model

**File:** `src/database/models.py`

```python
class Keyword(Base):
    # ... existing fields ...

    # NEW: Greenfield-specific fields
    winnability_score = Column(Float)           # 0-100, likelihood of ranking
    winnability_components = Column(JSONB)      # Breakdown of score factors
    personalized_difficulty = Column(Integer)   # Adjusted KD for this domain

    # NEW: Beachhead tracking
    is_beachhead = Column(Boolean, default=False)
    beachhead_priority = Column(Integer)        # 1-10 ranking among beachheads
    beachhead_score = Column(Float)             # Combined winnability + opportunity

    # NEW: SERP analysis for winnability
    serp_avg_dr = Column(Float)                 # Average DR of top 10
    serp_min_dr = Column(Integer)               # Lowest DR in top 10
    serp_has_low_dr = Column(Boolean)           # Any DR<30 in top 10?
    serp_weak_signals = Column(JSONB)           # ["outdated_content", "thin_content", ...]

    # NEW: AI/AEO tracking
    has_ai_overview = Column(Boolean, default=False)
    aio_source_count = Column(Integer)
    aio_optimization_potential = Column(Float)  # 0-100

    # NEW: Source tracking for greenfield
    source_competitor = Column(String(255))     # Which competitor this came from
    competitor_position = Column(Integer)       # Their position for this keyword
```

### 1.3 New GreenfieldAnalysis Model

**File:** `src/database/models.py`

```python
class GreenfieldAnalysis(Base):
    """Greenfield-specific analysis results"""
    __tablename__ = "greenfield_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=False)

    # Market Opportunity
    total_addressable_market = Column(Integer)      # Total search volume
    serviceable_addressable_market = Column(Integer) # Relevant keywords volume
    serviceable_obtainable_market = Column(Integer)  # Winnable keywords volume

    market_opportunity_score = Column(Float)        # 0-100
    competition_intensity = Column(Float)           # 0-100

    # Competitor Landscape
    competitor_count = Column(Integer)
    avg_competitor_dr = Column(Float)
    competitor_dr_range = Column(JSONB)             # {"min": 15, "max": 65}

    # Beachhead Summary
    beachhead_keyword_count = Column(Integer)
    total_beachhead_volume = Column(Integer)
    avg_beachhead_winnability = Column(Float)

    # Traffic Projections
    projection_conservative = Column(JSONB)
    projection_expected = Column(JSONB)
    projection_aggressive = Column(JSONB)
    """
    {
        "month_6": 500,
        "month_12": 2500,
        "month_18": 8000,
        "month_24": 15000,
        "confidence": 0.75
    }
    """

    # Growth Roadmap
    growth_roadmap = Column(JSONB)
    """
    [
        {"phase": "Foundation", "months": "1-3", "keywords": 10, "traffic": "50-200"},
        {"phase": "Traction", "months": "4-6", "keywords": 25, "traffic": "500-1500"},
        ...
    ]
    """

    # Validation Warnings
    competitor_validation_warnings = Column(JSONB)
    data_completeness_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_greenfield_analysis_run", "analysis_run_id"),
    )
```

### 1.4 New ValidatedCompetitor Model (Enhanced)

**File:** `src/database/models.py`

```python
class GreenfieldCompetitor(Base):
    """Competitors discovered/validated for greenfield analysis"""
    __tablename__ = "greenfield_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    # Competitor info
    domain = Column(String(255), nullable=False)
    domain_rating = Column(Integer)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)

    # Discovery
    discovery_source = Column(String(50))  # "user_provided", "serp_discovered", "traffic_share"
    user_provided = Column(Boolean, default=False)
    serp_overlap_count = Column(Integer)   # Keywords where they rank

    # Validation
    validation_status = Column(String(20))  # "valid", "warning", "replaced"
    validation_warnings = Column(JSONB)
    suggested_replacement = Column(String(255))

    # Usage in analysis
    keywords_extracted = Column(Integer)
    used_for_market_sizing = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
```

### 1.5 Migration Script

**File:** `migrations/versions/xxx_add_greenfield_support.py`

```python
"""Add greenfield intelligence support

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

def upgrade():
    # 1. Add AnalysisMode enum
    op.execute("CREATE TYPE analysismode AS ENUM ('standard', 'greenfield', 'hybrid')")

    # 2. Extend analysis_runs
    op.add_column('analysis_runs', sa.Column('analysis_mode', sa.Enum('standard', 'greenfield', 'hybrid', name='analysismode'), default='standard'))
    op.add_column('analysis_runs', sa.Column('domain_maturity_at_analysis', sa.String(20)))
    op.add_column('analysis_runs', sa.Column('domain_rating_at_analysis', sa.Integer()))
    op.add_column('analysis_runs', sa.Column('organic_keywords_at_analysis', sa.Integer()))
    op.add_column('analysis_runs', sa.Column('greenfield_context', JSONB))

    # 3. Extend keywords
    op.add_column('keywords', sa.Column('winnability_score', sa.Float()))
    op.add_column('keywords', sa.Column('winnability_components', JSONB))
    op.add_column('keywords', sa.Column('personalized_difficulty', sa.Integer()))
    op.add_column('keywords', sa.Column('is_beachhead', sa.Boolean(), default=False))
    op.add_column('keywords', sa.Column('beachhead_priority', sa.Integer()))
    op.add_column('keywords', sa.Column('beachhead_score', sa.Float()))
    op.add_column('keywords', sa.Column('serp_avg_dr', sa.Float()))
    op.add_column('keywords', sa.Column('serp_min_dr', sa.Integer()))
    op.add_column('keywords', sa.Column('serp_has_low_dr', sa.Boolean()))
    op.add_column('keywords', sa.Column('serp_weak_signals', JSONB))
    op.add_column('keywords', sa.Column('has_ai_overview', sa.Boolean(), default=False))
    op.add_column('keywords', sa.Column('aio_optimization_potential', sa.Float()))
    op.add_column('keywords', sa.Column('source_competitor', sa.String(255)))

    # 4. Create greenfield_analyses table
    op.create_table(
        'greenfield_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_run_id', UUID(as_uuid=True), sa.ForeignKey('analysis_runs.id'), nullable=False),
        sa.Column('domain_id', UUID(as_uuid=True), sa.ForeignKey('domains.id'), nullable=False),
        sa.Column('total_addressable_market', sa.Integer()),
        sa.Column('serviceable_addressable_market', sa.Integer()),
        sa.Column('serviceable_obtainable_market', sa.Integer()),
        sa.Column('market_opportunity_score', sa.Float()),
        sa.Column('competition_intensity', sa.Float()),
        sa.Column('competitor_count', sa.Integer()),
        sa.Column('avg_competitor_dr', sa.Float()),
        sa.Column('competitor_dr_range', JSONB),
        sa.Column('beachhead_keyword_count', sa.Integer()),
        sa.Column('total_beachhead_volume', sa.Integer()),
        sa.Column('avg_beachhead_winnability', sa.Float()),
        sa.Column('projection_conservative', JSONB),
        sa.Column('projection_expected', JSONB),
        sa.Column('projection_aggressive', JSONB),
        sa.Column('growth_roadmap', JSONB),
        sa.Column('competitor_validation_warnings', JSONB),
        sa.Column('data_completeness_score', sa.Float()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    op.create_index('idx_greenfield_analysis_run', 'greenfield_analyses', ['analysis_run_id'])

    # 5. Create greenfield_competitors table
    op.create_table(
        'greenfield_competitors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_run_id', UUID(as_uuid=True), sa.ForeignKey('analysis_runs.id'), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('domain_rating', sa.Integer()),
        sa.Column('organic_traffic', sa.Integer()),
        sa.Column('organic_keywords', sa.Integer()),
        sa.Column('discovery_source', sa.String(50)),
        sa.Column('user_provided', sa.Boolean(), default=False),
        sa.Column('serp_overlap_count', sa.Integer()),
        sa.Column('validation_status', sa.String(20)),
        sa.Column('validation_warnings', JSONB),
        sa.Column('suggested_replacement', sa.String(255)),
        sa.Column('keywords_extracted', sa.Integer()),
        sa.Column('used_for_market_sizing', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )

    # 6. Add indexes for greenfield queries
    op.create_index('idx_keyword_winnability', 'keywords', ['analysis_run_id', 'winnability_score'])
    op.create_index('idx_keyword_beachhead', 'keywords', ['analysis_run_id', 'is_beachhead'])


def downgrade():
    op.drop_index('idx_keyword_beachhead')
    op.drop_index('idx_keyword_winnability')
    op.drop_table('greenfield_competitors')
    op.drop_table('greenfield_analyses')
    op.drop_column('keywords', 'source_competitor')
    op.drop_column('keywords', 'aio_optimization_potential')
    op.drop_column('keywords', 'has_ai_overview')
    op.drop_column('keywords', 'serp_weak_signals')
    op.drop_column('keywords', 'serp_has_low_dr')
    op.drop_column('keywords', 'serp_min_dr')
    op.drop_column('keywords', 'serp_avg_dr')
    op.drop_column('keywords', 'beachhead_score')
    op.drop_column('keywords', 'beachhead_priority')
    op.drop_column('keywords', 'is_beachhead')
    op.drop_column('keywords', 'personalized_difficulty')
    op.drop_column('keywords', 'winnability_components')
    op.drop_column('keywords', 'winnability_score')
    op.drop_column('analysis_runs', 'greenfield_context')
    op.drop_column('analysis_runs', 'organic_keywords_at_analysis')
    op.drop_column('analysis_runs', 'domain_rating_at_analysis')
    op.drop_column('analysis_runs', 'domain_maturity_at_analysis')
    op.drop_column('analysis_runs', 'analysis_mode')
    op.execute("DROP TYPE analysismode")
```

---

## 2. Orchestrator Modifications

### 2.1 Update CollectionConfig

**File:** `src/collector/orchestrator.py`

```python
@dataclass
class CollectionConfig:
    """Configuration for data collection."""
    domain: str
    market: str = "United States"
    language: str = "English"
    brand_name: Optional[str] = None
    industry: str = "General"
    competitors: Optional[List[str]] = None

    # ... existing fields ...

    # NEW: Greenfield context
    greenfield_context: Optional[GreenfieldContext] = None
    """
    Required when domain is detected as greenfield.
    Contains seed_keywords, known_competitors, business_description, etc.
    """

    # NEW: Force analysis mode (optional override)
    force_analysis_mode: Optional[str] = None  # "greenfield", "hybrid", "standard"


@dataclass
class GreenfieldContext:
    """User-provided context for greenfield analysis."""
    business_name: str
    business_description: str
    primary_offering: str
    target_market: str
    industry_vertical: str
    seed_keywords: List[str]          # Minimum 5
    known_competitors: List[str]       # Minimum 3

    # Optional
    target_audience: Optional[str] = None
    unique_value_prop: Optional[str] = None
    content_budget: Optional[str] = None  # low, medium, high
```

### 2.2 Replace _should_abbreviate with Domain Classification

**File:** `src/collector/orchestrator.py`

```python
from src.scoring.greenfield import (
    DomainMaturity, classify_domain_maturity, DomainMetrics
)

class DataCollectionOrchestrator:

    async def collect_all(self, config: CollectionConfig) -> CollectionResult:
        """Execute full data collection across all phases."""
        start_time = datetime.utcnow()

        # Phase 1: Foundation (always runs)
        logger.info("Phase 1: Collecting foundation data...")
        foundation = await collect_foundation_data(
            self.client, config.domain, config.market, config.language
        )

        # NEW: Classify domain maturity
        maturity = self._classify_domain(foundation, config)
        logger.info(f"Domain classified as: {maturity.value}")

        # NEW: Route based on maturity
        if maturity == DomainMaturity.GREENFIELD:
            return await self._collect_greenfield(config, foundation, start_time)
        elif maturity == DomainMaturity.EMERGING:
            return await self._collect_hybrid(config, foundation, start_time)
        else:
            return await self._collect_standard(config, foundation, start_time)

    def _classify_domain(
        self,
        foundation: Dict,
        config: CollectionConfig
    ) -> DomainMaturity:
        """Classify domain into maturity tier."""

        # Allow forced override
        if config.force_analysis_mode:
            return DomainMaturity(config.force_analysis_mode)

        # Extract metrics
        overview = foundation.get("domain_overview", {})
        backlinks = foundation.get("backlink_summary", {})

        metrics = DomainMetrics(
            domain_rating=overview.get("rank", 0),
            organic_keywords=overview.get("organic_keywords", 0),
            organic_traffic=overview.get("organic_traffic", 0),
            referring_domains=backlinks.get("referring_domains", 0)
        )

        return classify_domain_maturity(metrics)

    async def _collect_greenfield(
        self,
        config: CollectionConfig,
        foundation: Dict,
        start_time: datetime
    ) -> CollectionResult:
        """
        Greenfield collection: competitor-first approach.

        Instead of analyzing the target domain (which has no data),
        we analyze competitors to understand the market opportunity.
        """
        from src.collector.greenfield_pipeline import collect_greenfield_data

        # Require greenfield context
        if not config.greenfield_context:
            raise ValueError(
                "Greenfield analysis requires business context. "
                "Please provide seed_keywords and known_competitors."
            )

        logger.info("Starting GREENFIELD collection pipeline...")

        return await collect_greenfield_data(
            client=self.client,
            config=config,
            foundation=foundation,
            start_time=start_time
        )

    async def _collect_hybrid(
        self,
        config: CollectionConfig,
        foundation: Dict,
        start_time: datetime
    ) -> CollectionResult:
        """
        Hybrid collection: domain data + competitor supplementation.

        Use whatever domain data exists, but supplement with
        competitor analysis for gaps and opportunities.
        """
        from src.collector.hybrid_pipeline import collect_hybrid_data

        logger.info("Starting HYBRID collection pipeline...")

        return await collect_hybrid_data(
            client=self.client,
            config=config,
            foundation=foundation,
            start_time=start_time
        )

    async def _collect_standard(
        self,
        config: CollectionConfig,
        foundation: Dict,
        start_time: datetime
    ) -> CollectionResult:
        """Standard collection for established domains (existing logic)."""
        # ... existing Phase 2, 3, 4 logic ...
        pass
```

---

## 3. Greenfield Collection Pipeline

### 3.1 New File: greenfield_pipeline.py

**File:** `src/collector/greenfield_pipeline.py`

```python
"""
Greenfield Collection Pipeline

Competitor-first data collection for domains with insufficient SEO data.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.scoring.greenfield import (
    calculate_winnability_full,
    select_beachhead_keywords,
    calculate_market_opportunity,
    project_traffic_scenarios,
    get_industry_from_string,
)

logger = logging.getLogger(__name__)


async def collect_greenfield_data(
    client,
    config: "CollectionConfig",
    foundation: Dict,
    start_time: datetime
) -> "CollectionResult":
    """
    Execute greenfield collection pipeline.

    Phases:
    G1: Competitor Discovery & Validation
    G2: Keyword Universe Construction (from competitors)
    G3: SERP Analysis & Winnability Scoring
    G4: Market Sizing
    G5: Beachhead Selection & Roadmap
    """

    ctx = config.greenfield_context
    errors = []
    warnings = []

    # =========================================================================
    # Phase G1: Competitor Discovery & Validation
    # =========================================================================
    logger.info("Phase G1: Discovering and validating competitors...")

    try:
        competitors = await discover_greenfield_competitors(
            client=client,
            seed_keywords=ctx.seed_keywords,
            known_competitors=ctx.known_competitors,
            market=config.market,
            language=config.language
        )

        # Validate user-provided competitors
        validation_result = await validate_user_competitors(
            client=client,
            user_provided=ctx.known_competitors,
            serp_discovered=competitors,
            target_dr=foundation.get("domain_overview", {}).get("rank", 10)
        )

        if validation_result.warnings:
            warnings.extend([w.issue for w in validation_result.warnings])

        validated_competitors = validation_result.validated_competitors[:15]

    except Exception as e:
        logger.error(f"Phase G1 failed: {e}")
        errors.append(f"Competitor discovery failed: {str(e)}")
        validated_competitors = []

    # =========================================================================
    # Phase G2: Keyword Universe Construction
    # =========================================================================
    logger.info("Phase G2: Building keyword universe from competitors...")

    try:
        keyword_universe = await build_greenfield_keyword_universe(
            client=client,
            competitors=validated_competitors,
            seed_keywords=ctx.seed_keywords,
            market=config.market,
            language=config.language,
            depth=config.get_depth()
        )
    except Exception as e:
        logger.error(f"Phase G2 failed: {e}")
        errors.append(f"Keyword universe construction failed: {str(e)}")
        keyword_universe = []

    # =========================================================================
    # Phase G3: SERP Analysis & Winnability Scoring
    # =========================================================================
    logger.info("Phase G3: Analyzing SERPs and calculating winnability...")

    try:
        # Analyze SERPs for top 200 keywords
        keywords_to_analyze = keyword_universe[:200]

        analyzed_keywords = await analyze_serps_for_winnability(
            client=client,
            keywords=keywords_to_analyze,
            target_dr=foundation.get("domain_overview", {}).get("rank", 10),
            market=config.market,
            language=config.language,
            industry=ctx.industry_vertical
        )
    except Exception as e:
        logger.error(f"Phase G3 failed: {e}")
        errors.append(f"SERP analysis failed: {str(e)}")
        analyzed_keywords = keyword_universe[:200]  # Fallback without winnability

    # =========================================================================
    # Phase G4: Market Sizing
    # =========================================================================
    logger.info("Phase G4: Calculating market opportunity...")

    try:
        market_opportunity = calculate_market_opportunity(
            keyword_universe=analyzed_keywords,
            competitors=validated_competitors,
            industry=get_industry_from_string(ctx.industry_vertical)
        )
    except Exception as e:
        logger.error(f"Phase G4 failed: {e}")
        errors.append(f"Market sizing failed: {str(e)}")
        market_opportunity = None

    # =========================================================================
    # Phase G5: Beachhead Selection & Roadmap
    # =========================================================================
    logger.info("Phase G5: Selecting beachhead keywords and building roadmap...")

    try:
        beachhead_keywords = select_beachhead_keywords(
            keywords=analyzed_keywords,
            max_beachheads=20,
            min_winnability=60,
            industry=get_industry_from_string(ctx.industry_vertical)
        )

        # Generate traffic projections
        traffic_projections = project_traffic_scenarios(
            beachhead_keywords=beachhead_keywords,
            all_keywords=analyzed_keywords,
            target_dr=foundation.get("domain_overview", {}).get("rank", 10),
            industry=get_industry_from_string(ctx.industry_vertical)
        )

        # Build growth roadmap
        growth_roadmap = build_growth_roadmap(
            beachhead_keywords=beachhead_keywords,
            analyzed_keywords=analyzed_keywords,
            target_dr=foundation.get("domain_overview", {}).get("rank", 10)
        )

    except Exception as e:
        logger.error(f"Phase G5 failed: {e}")
        errors.append(f"Beachhead selection failed: {str(e)}")
        beachhead_keywords = []
        traffic_projections = None
        growth_roadmap = None

    # =========================================================================
    # Compile Result
    # =========================================================================
    duration = (datetime.utcnow() - start_time).total_seconds()

    return CollectionResult(
        domain=config.domain,
        timestamp=start_time,
        market=config.market,
        language=config.language,
        industry=ctx.industry_vertical,
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        duration_seconds=duration,

        # Standard fields (mostly empty for greenfield)
        domain_overview=foundation.get("domain_overview", {}),
        backlink_summary=foundation.get("backlink_summary", {}),

        # Greenfield-specific data
        analysis_mode="greenfield",
        greenfield_data={
            "competitors": [_competitor_to_dict(c) for c in validated_competitors],
            "competitor_validation": {
                "warnings": [w.__dict__ for w in validation_result.warnings] if validation_result else [],
                "suggestions": validation_result.suggested_replacements if validation_result else []
            },
            "keyword_universe": [_keyword_to_dict(k) for k in analyzed_keywords],
            "beachhead_keywords": [_keyword_to_dict(k) for k in beachhead_keywords],
            "market_opportunity": market_opportunity.__dict__ if market_opportunity else None,
            "traffic_projections": traffic_projections.__dict__ if traffic_projections else None,
            "growth_roadmap": growth_roadmap,
        }
    )


async def discover_greenfield_competitors(
    client,
    seed_keywords: List[str],
    known_competitors: List[str],
    market: str,
    language: str
) -> List["ValidatedCompetitor"]:
    """Discover competitors from seed keywords and validate user-provided ones."""

    all_competitors = {}

    # 1. SERP-based discovery
    for keyword in seed_keywords[:10]:
        try:
            serp = await client.get_serp_results(
                keyword=keyword,
                location_name=market,
                language_name=language,
                depth=20
            )
            for result in serp:
                domain = result.get("domain", "")
                if domain and domain not in PLATFORM_DOMAINS:
                    if domain not in all_competitors:
                        all_competitors[domain] = {
                            "domain": domain,
                            "serp_appearances": 0,
                            "source": "serp"
                        }
                    all_competitors[domain]["serp_appearances"] += 1
        except Exception as e:
            logger.warning(f"SERP fetch failed for '{keyword}': {e}")

    # 2. Add user-provided competitors
    for domain in known_competitors:
        if domain not in all_competitors:
            all_competitors[domain] = {
                "domain": domain,
                "serp_appearances": 0,
                "source": "user_provided"
            }
        all_competitors[domain]["user_provided"] = True

    # 3. Enrich with domain metrics
    enriched = []
    for domain, data in all_competitors.items():
        try:
            metrics = await client.get_domain_rank_overview(domain, market)
            enriched.append(ValidatedCompetitor(
                domain=domain,
                domain_rating=metrics.get("rank", 0),
                organic_traffic=metrics.get("organic_traffic", 0),
                organic_keywords=metrics.get("organic_keywords", 0),
                serp_overlap_count=data["serp_appearances"],
                user_provided=data.get("user_provided", False),
                discovery_source=data["source"]
            ))
        except Exception as e:
            logger.warning(f"Failed to enrich competitor {domain}: {e}")

    # 4. Sort by relevance (SERP appearances + traffic)
    enriched.sort(
        key=lambda c: (c.serp_overlap_count * 1000) + c.organic_traffic,
        reverse=True
    )

    return enriched[:20]


async def analyze_serps_for_winnability(
    client,
    keywords: List[Dict],
    target_dr: int,
    market: str,
    language: str,
    industry: str
) -> List[Dict]:
    """Analyze SERPs and calculate winnability for each keyword."""

    analyzed = []

    for kw in keywords:
        keyword_text = kw.get("keyword", kw) if isinstance(kw, dict) else kw

        try:
            # Fetch SERP
            serp = await client.get_serp_results(
                keyword=keyword_text,
                location_name=market,
                language_name=language,
                depth=10
            )

            # Extract SERP metrics
            serp_drs = [r.get("domain_rating", 50) for r in serp if r.get("domain_rating")]
            avg_dr = sum(serp_drs) / len(serp_drs) if serp_drs else 50
            min_dr = min(serp_drs) if serp_drs else 50
            has_low_dr = any(dr < 30 for dr in serp_drs)

            # Detect weak content signals (simplified)
            weak_signals = []
            # In production, analyze content age, word count, etc.

            # Check for AI Overview
            has_ai_overview = any(r.get("type") == "ai_overview" for r in serp)

            # Calculate winnability
            winnability = calculate_winnability_full(
                target_dr=target_dr,
                avg_serp_dr=avg_dr,
                min_serp_dr=min_dr,
                has_low_dr_rankings=has_low_dr,
                weak_content_signals=weak_signals,
                has_ai_overview=has_ai_overview,
                keyword_difficulty=kw.get("keyword_difficulty", 50) if isinstance(kw, dict) else 50,
                industry=industry
            )

            analyzed.append({
                **(kw if isinstance(kw, dict) else {"keyword": kw}),
                "winnability_score": winnability.score,
                "winnability_components": winnability.components,
                "serp_avg_dr": avg_dr,
                "serp_min_dr": min_dr,
                "serp_has_low_dr": has_low_dr,
                "has_ai_overview": has_ai_overview,
                "personalized_difficulty": winnability.personalized_difficulty
            })

        except Exception as e:
            logger.warning(f"SERP analysis failed for '{keyword_text}': {e}")
            # Add without winnability
            analyzed.append({
                **(kw if isinstance(kw, dict) else {"keyword": kw}),
                "winnability_score": None,
                "data_incomplete": True
            })

    return analyzed


def build_growth_roadmap(
    beachhead_keywords: List[Dict],
    analyzed_keywords: List[Dict],
    target_dr: int
) -> List[Dict]:
    """Build phased growth roadmap."""

    # Phase 1: Foundation (beachheads only)
    phase1_keywords = beachhead_keywords[:10]
    phase1_traffic = sum(k.get("search_volume", 0) * 0.02 for k in phase1_keywords)

    # Phase 2: Expansion (more beachheads + adjacent)
    phase2_keywords = [k for k in analyzed_keywords if k.get("winnability_score", 0) >= 60][:25]
    phase2_traffic = sum(k.get("search_volume", 0) * 0.05 for k in phase2_keywords)

    # Phase 3: Growth (medium difficulty)
    phase3_keywords = [k for k in analyzed_keywords if 40 <= k.get("winnability_score", 0) < 60][:30]
    phase3_traffic = sum(k.get("search_volume", 0) * 0.08 for k in phase3_keywords)

    # Phase 4: Competitive (harder keywords)
    phase4_keywords = [k for k in analyzed_keywords if k.get("winnability_score", 0) < 40][:20]
    phase4_traffic = sum(k.get("search_volume", 0) * 0.05 for k in phase4_keywords)

    return [
        {
            "phase": "Foundation",
            "timeline": "Months 1-3",
            "description": "Establish presence with high-winnability beachhead keywords",
            "keyword_count": len(phase1_keywords),
            "target_keywords": [k.get("keyword") for k in phase1_keywords[:5]],
            "estimated_traffic_range": f"{int(phase1_traffic * 0.5)}-{int(phase1_traffic * 1.5)}",
            "priority": "critical"
        },
        {
            "phase": "Early Traction",
            "timeline": "Months 4-6",
            "description": "Expand to adjacent keywords, build topical authority",
            "keyword_count": len(phase2_keywords),
            "estimated_traffic_range": f"{int(phase2_traffic * 0.5)}-{int(phase2_traffic * 1.5)}",
            "priority": "high"
        },
        {
            "phase": "Growth",
            "timeline": "Months 7-12",
            "description": "Target medium-difficulty keywords with established authority",
            "keyword_count": len(phase3_keywords),
            "estimated_traffic_range": f"{int(phase3_traffic * 0.5)}-{int(phase3_traffic * 1.5)}",
            "priority": "medium"
        },
        {
            "phase": "Competitive",
            "timeline": "Year 2+",
            "description": "Challenge for competitive keywords with built authority",
            "keyword_count": len(phase4_keywords),
            "estimated_traffic_range": f"{int(phase4_traffic * 0.5)}-{int(phase4_traffic * 1.5)}",
            "priority": "long-term"
        }
    ]


# Platform domains to filter out
PLATFORM_DOMAINS = {
    'wikipedia.org', 'reddit.com', 'quora.com', 'medium.com',
    'youtube.com', 'facebook.com', 'twitter.com', 'linkedin.com',
    'amazon.com', 'ebay.com', 'yelp.com', 'tripadvisor.com',
    'forbes.com', 'businessinsider.com', 'nytimes.com'
}
```

---

## 4. API Endpoints

### 4.1 New Greenfield Dashboard Endpoints

**File:** `api/greenfield.py` (NEW FILE)

```python
"""
Greenfield Intelligence API

Endpoints for greenfield domain analysis and dashboard.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import (
    Domain, AnalysisRun, Keyword, GreenfieldAnalysis,
    GreenfieldCompetitor, AnalysisMode
)

router = APIRouter(prefix="/api/greenfield", tags=["Greenfield Intelligence"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class GreenfieldContextInput(BaseModel):
    """Input for greenfield analysis context"""
    business_name: str
    business_description: str
    primary_offering: str
    target_market: str = "United States"
    industry_vertical: str
    seed_keywords: List[str] = Field(..., min_items=5)
    known_competitors: List[str] = Field(..., min_items=3)
    target_audience: Optional[str] = None
    unique_value_prop: Optional[str] = None


class MarketOpportunityResponse(BaseModel):
    """Market opportunity analysis"""
    total_addressable_market: int
    serviceable_addressable_market: int
    serviceable_obtainable_market: int
    market_opportunity_score: float
    competition_intensity: float
    competitor_landscape: Dict[str, Any]


class BeachheadKeyword(BaseModel):
    """Beachhead keyword with winnability"""
    keyword: str
    search_volume: int
    keyword_difficulty: int
    winnability_score: float
    winnability_components: Dict[str, float]
    personalized_difficulty: int
    serp_avg_dr: float
    has_ai_overview: bool
    beachhead_priority: int
    recommended_content_type: str
    estimated_time_to_rank: str


class BeachheadResponse(BaseModel):
    """Beachhead keywords response"""
    beachhead_count: int
    total_beachhead_volume: int
    avg_winnability: float
    keywords: List[BeachheadKeyword]


class TrafficProjection(BaseModel):
    """Traffic projection for a scenario"""
    month_6: int
    month_12: int
    month_18: int
    month_24: int
    confidence: float


class ProjectionsResponse(BaseModel):
    """Traffic projections response"""
    conservative: TrafficProjection
    expected: TrafficProjection
    aggressive: TrafficProjection
    assumptions: List[str]


class RoadmapPhase(BaseModel):
    """Growth roadmap phase"""
    phase: str
    timeline: str
    description: str
    keyword_count: int
    target_keywords: List[str]
    estimated_traffic_range: str
    priority: str


class RoadmapResponse(BaseModel):
    """Growth roadmap response"""
    phases: List[RoadmapPhase]
    total_keywords: int
    total_estimated_traffic: str


class CompetitorValidationWarning(BaseModel):
    """Warning about competitor selection"""
    severity: str
    domain: str
    issue: str
    recommendation: str


class ValidatedCompetitorResponse(BaseModel):
    """Validated competitor"""
    domain: str
    domain_rating: int
    organic_traffic: int
    organic_keywords: int
    discovery_source: str
    user_provided: bool
    serp_overlap_count: int
    validation_status: str
    warnings: List[CompetitorValidationWarning]


class GreenfieldOverview(BaseModel):
    """Greenfield dashboard overview"""
    domain: str
    analysis_id: str
    analysis_mode: str
    analysis_date: datetime

    # Market opportunity summary
    market_opportunity_score: float
    total_market_volume: int

    # Beachhead summary
    beachhead_count: int
    avg_winnability: float

    # Competitor summary
    competitor_count: int
    avg_competitor_dr: float

    # Projections summary
    expected_traffic_month_12: int

    # Validation
    data_completeness: float
    warnings_count: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/{domain_id}/overview", response_model=GreenfieldOverview)
async def get_greenfield_overview(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> GreenfieldOverview:
    """
    Get greenfield dashboard overview.

    Returns summary metrics for a greenfield domain analysis.
    """
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.analysis_mode == AnalysisMode.GREENFIELD
    ).order_by(AnalysisRun.completed_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No greenfield analysis found")

    greenfield = db.query(GreenfieldAnalysis).filter(
        GreenfieldAnalysis.analysis_run_id == analysis.id
    ).first()

    if not greenfield:
        raise HTTPException(status_code=404, detail="Greenfield data not found")

    return GreenfieldOverview(
        domain=domain.domain,
        analysis_id=str(analysis.id),
        analysis_mode="greenfield",
        analysis_date=analysis.completed_at or analysis.created_at,
        market_opportunity_score=greenfield.market_opportunity_score or 0,
        total_market_volume=greenfield.total_addressable_market or 0,
        beachhead_count=greenfield.beachhead_keyword_count or 0,
        avg_winnability=greenfield.avg_beachhead_winnability or 0,
        competitor_count=greenfield.competitor_count or 0,
        avg_competitor_dr=greenfield.avg_competitor_dr or 0,
        expected_traffic_month_12=(greenfield.projection_expected or {}).get("month_12", 0),
        data_completeness=greenfield.data_completeness_score or 0,
        warnings_count=len(greenfield.competitor_validation_warnings or [])
    )


@router.get("/{domain_id}/market-opportunity", response_model=MarketOpportunityResponse)
async def get_market_opportunity(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> MarketOpportunityResponse:
    """
    Get market opportunity analysis.

    Shows TAM, SAM, SOM and competitive landscape for greenfield domain.
    """
    greenfield = _get_greenfield_analysis(domain_id, db)

    return MarketOpportunityResponse(
        total_addressable_market=greenfield.total_addressable_market or 0,
        serviceable_addressable_market=greenfield.serviceable_addressable_market or 0,
        serviceable_obtainable_market=greenfield.serviceable_obtainable_market or 0,
        market_opportunity_score=greenfield.market_opportunity_score or 0,
        competition_intensity=greenfield.competition_intensity or 0,
        competitor_landscape={
            "competitor_count": greenfield.competitor_count,
            "avg_dr": greenfield.avg_competitor_dr,
            "dr_range": greenfield.competitor_dr_range
        }
    )


@router.get("/{domain_id}/beachhead-keywords", response_model=BeachheadResponse)
async def get_beachhead_keywords(
    domain_id: UUID,
    limit: int = Query(20, le=50),
    min_winnability: float = Query(0, ge=0, le=100),
    db: Session = Depends(get_db)
) -> BeachheadResponse:
    """
    Get beachhead keywords with winnability scores.

    Beachhead keywords are high-winnability, strategic entry points
    for a greenfield domain to start building SEO presence.
    """
    analysis = _get_greenfield_analysis_run(domain_id, db)

    # Query beachhead keywords
    keywords = db.query(Keyword).filter(
        Keyword.analysis_run_id == analysis.id,
        Keyword.is_beachhead == True,
        Keyword.winnability_score >= min_winnability
    ).order_by(Keyword.beachhead_priority).limit(limit).all()

    beachhead_list = []
    for kw in keywords:
        beachhead_list.append(BeachheadKeyword(
            keyword=kw.keyword,
            search_volume=kw.search_volume or 0,
            keyword_difficulty=kw.keyword_difficulty or 0,
            winnability_score=kw.winnability_score or 0,
            winnability_components=kw.winnability_components or {},
            personalized_difficulty=kw.personalized_difficulty or kw.keyword_difficulty or 0,
            serp_avg_dr=kw.serp_avg_dr or 0,
            has_ai_overview=kw.has_ai_overview or False,
            beachhead_priority=kw.beachhead_priority or 0,
            recommended_content_type=_get_content_recommendation(kw),
            estimated_time_to_rank=_estimate_time_to_rank(kw)
        ))

    total_volume = sum(k.search_volume for k in beachhead_list)
    avg_winnability = sum(k.winnability_score for k in beachhead_list) / len(beachhead_list) if beachhead_list else 0

    return BeachheadResponse(
        beachhead_count=len(beachhead_list),
        total_beachhead_volume=total_volume,
        avg_winnability=round(avg_winnability, 1),
        keywords=beachhead_list
    )


@router.get("/{domain_id}/projections", response_model=ProjectionsResponse)
async def get_traffic_projections(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> ProjectionsResponse:
    """
    Get traffic projections for greenfield domain.

    Returns conservative, expected, and aggressive scenarios.
    """
    greenfield = _get_greenfield_analysis(domain_id, db)

    return ProjectionsResponse(
        conservative=TrafficProjection(**(greenfield.projection_conservative or {
            "month_6": 0, "month_12": 0, "month_18": 0, "month_24": 0, "confidence": 0
        })),
        expected=TrafficProjection(**(greenfield.projection_expected or {
            "month_6": 0, "month_12": 0, "month_18": 0, "month_24": 0, "confidence": 0
        })),
        aggressive=TrafficProjection(**(greenfield.projection_aggressive or {
            "month_6": 0, "month_12": 0, "month_18": 0, "month_24": 0, "confidence": 0
        })),
        assumptions=[
            "Consistent content production (4-8 pieces/month)",
            "Basic on-page SEO implementation",
            "No major algorithm changes",
            "5-10 quality backlinks acquired monthly"
        ]
    )


@router.get("/{domain_id}/roadmap", response_model=RoadmapResponse)
async def get_growth_roadmap(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> RoadmapResponse:
    """
    Get phased growth roadmap for greenfield domain.

    Returns strategic phases with keyword targets and traffic estimates.
    """
    greenfield = _get_greenfield_analysis(domain_id, db)

    roadmap = greenfield.growth_roadmap or []
    phases = [RoadmapPhase(**phase) for phase in roadmap]

    total_keywords = sum(p.keyword_count for p in phases)

    return RoadmapResponse(
        phases=phases,
        total_keywords=total_keywords,
        total_estimated_traffic="Varies by execution"
    )


@router.get("/{domain_id}/competitors", response_model=List[ValidatedCompetitorResponse])
async def get_validated_competitors(
    domain_id: UUID,
    db: Session = Depends(get_db)
) -> List[ValidatedCompetitorResponse]:
    """
    Get validated competitors with warnings.

    Shows which competitors were discovered vs user-provided,
    and any validation warnings about competitor selection.
    """
    analysis = _get_greenfield_analysis_run(domain_id, db)

    competitors = db.query(GreenfieldCompetitor).filter(
        GreenfieldCompetitor.analysis_run_id == analysis.id
    ).order_by(GreenfieldCompetitor.organic_traffic.desc()).all()

    return [
        ValidatedCompetitorResponse(
            domain=c.domain,
            domain_rating=c.domain_rating or 0,
            organic_traffic=c.organic_traffic or 0,
            organic_keywords=c.organic_keywords or 0,
            discovery_source=c.discovery_source or "unknown",
            user_provided=c.user_provided or False,
            serp_overlap_count=c.serp_overlap_count or 0,
            validation_status=c.validation_status or "valid",
            warnings=[
                CompetitorValidationWarning(**w)
                for w in (c.validation_warnings or [])
            ]
        )
        for c in competitors
    ]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_greenfield_analysis(domain_id: UUID, db: Session) -> GreenfieldAnalysis:
    """Get greenfield analysis or raise 404."""
    analysis = _get_greenfield_analysis_run(domain_id, db)

    greenfield = db.query(GreenfieldAnalysis).filter(
        GreenfieldAnalysis.analysis_run_id == analysis.id
    ).first()

    if not greenfield:
        raise HTTPException(status_code=404, detail="Greenfield analysis data not found")

    return greenfield


def _get_greenfield_analysis_run(domain_id: UUID, db: Session) -> AnalysisRun:
    """Get greenfield analysis run or raise 404."""
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.domain_id == domain_id,
        AnalysisRun.analysis_mode == AnalysisMode.GREENFIELD
    ).order_by(AnalysisRun.completed_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No greenfield analysis found for this domain")

    return analysis


def _get_content_recommendation(keyword: Keyword) -> str:
    """Get content type recommendation based on keyword characteristics."""
    if keyword.has_ai_overview:
        return "structured_guide"  # Format for AIO citation
    elif keyword.keyword_difficulty and keyword.keyword_difficulty < 30:
        return "comprehensive_article"
    else:
        return "pillar_content"


def _estimate_time_to_rank(keyword: Keyword) -> str:
    """Estimate time to rank based on winnability and difficulty."""
    winnability = keyword.winnability_score or 50

    if winnability >= 80:
        return "4-8 weeks"
    elif winnability >= 60:
        return "2-4 months"
    elif winnability >= 40:
        return "4-6 months"
    else:
        return "6+ months"
```

### 4.2 Register New Router

**File:** `api/main.py` (or wherever routers are registered)

```python
from api.greenfield import router as greenfield_router

app.include_router(greenfield_router)
```

---

## 5. Scoring Module Integration

### 5.1 Update src/scoring/greenfield.py

The existing `src/scoring/greenfield.py` is mostly complete. Minor updates needed:

```python
# Add to existing file

@dataclass
class WinnabilityResult:
    """Full winnability calculation result."""
    score: float
    components: Dict[str, float]
    personalized_difficulty: int
    confidence: float
    data_completeness: str


def calculate_winnability_full(
    target_dr: int,
    avg_serp_dr: float,
    min_serp_dr: float,
    has_low_dr_rankings: bool,
    weak_content_signals: List[str],
    has_ai_overview: bool,
    keyword_difficulty: int,
    industry: str = "saas",
    has_geo_modifier: bool = False,
) -> WinnabilityResult:
    """
    Calculate full winnability result with all metadata.

    Returns WinnabilityResult with score, components, and confidence.
    """
    score, components = calculate_winnability(
        target_dr=target_dr,
        avg_serp_dr=avg_serp_dr,
        min_serp_dr=min_serp_dr,
        has_low_dr_rankings=has_low_dr_rankings,
        weak_content_signals=weak_content_signals,
        has_ai_overview=has_ai_overview,
        keyword_difficulty=keyword_difficulty,
        industry=industry,
        has_geo_modifier=has_geo_modifier
    )

    personalized_kd = calculate_personalized_difficulty_greenfield(
        base_kd=keyword_difficulty,
        target_dr=target_dr,
        avg_serp_dr=avg_serp_dr
    )

    # Calculate confidence based on data completeness
    data_points = [avg_serp_dr, min_serp_dr, keyword_difficulty]
    completeness = sum(1 for d in data_points if d is not None and d > 0) / len(data_points)

    return WinnabilityResult(
        score=score,
        components=components,
        personalized_difficulty=personalized_kd,
        confidence=completeness,
        data_completeness="full" if completeness == 1 else "partial"
    )
```

---

## 6. Strategy Builder Updates

### 6.1 Update Thread Suggestions for Greenfield

**File:** `api/strategy.py` - Add greenfield-aware suggestions

```python
@router.get("/{strategy_id}/suggested-threads")
async def get_suggested_threads(
    strategy_id: UUID,
    db: Session = Depends(get_db)
) -> List[SuggestedThread]:
    """
    Get AI-suggested threads based on analysis type.

    For greenfield: Suggests beachhead-based threads
    For established: Suggests based on opportunity scores
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == strategy.analysis_run_id
    ).first()

    # Check analysis mode
    if analysis.analysis_mode == AnalysisMode.GREENFIELD:
        return await _suggest_greenfield_threads(analysis.id, db)
    else:
        return await _suggest_standard_threads(analysis.id, db)


async def _suggest_greenfield_threads(
    analysis_run_id: UUID,
    db: Session
) -> List[SuggestedThread]:
    """Suggest threads based on beachhead keyword clusters."""

    # Get beachhead keywords
    beachheads = db.query(Keyword).filter(
        Keyword.analysis_run_id == analysis_run_id,
        Keyword.is_beachhead == True
    ).order_by(Keyword.beachhead_priority).all()

    # Cluster by parent_topic
    clusters = {}
    for kw in beachheads:
        topic = kw.parent_topic or "General"
        if topic not in clusters:
            clusters[topic] = []
        clusters[topic].append(kw)

    suggestions = []
    for topic, keywords in clusters.items():
        if len(keywords) >= 2:  # Only suggest if cluster has multiple keywords
            avg_winnability = sum(k.winnability_score or 0 for k in keywords) / len(keywords)
            total_volume = sum(k.search_volume or 0 for k in keywords)

            # Determine AIO optimization level
            aio_keywords = [k for k in keywords if k.has_ai_overview]
            if len(aio_keywords) > len(keywords) * 0.5:
                aio_level = "aio_priority"
            elif aio_keywords:
                aio_level = "aio_optimized"
            else:
                aio_level = "standard"

            suggestions.append(SuggestedThread(
                name=f"Beachhead: {topic}",
                description=f"High-winnability keywords in {topic} cluster",
                keyword_count=len(keywords),
                total_volume=total_volume,
                avg_winnability=round(avg_winnability, 1),
                priority=1,  # Beachheads are always high priority
                recommended=True,
                reason=f"Avg winnability {avg_winnability:.0f}, total volume {total_volume:,}",
                aio_optimization_level=aio_level,
                keywords=[k.keyword for k in keywords[:10]]
            ))

    # Sort by winnability
    suggestions.sort(key=lambda x: x.avg_winnability, reverse=True)

    return suggestions[:10]
```

### 6.2 Update Monok Export with AIO Context

**File:** `api/strategy.py` - Enhance export

```python
class MonokExportWithAIO(BaseModel):
    """Enhanced Monok export with AI optimization context."""
    thread_name: str
    topics: List[MonokTopic]
    ai_optimization: Optional[AIOptimizationContext] = None


class AIOptimizationContext(BaseModel):
    """AI optimization instructions for content creation."""
    optimization_level: str  # standard, aio_optimized, aio_priority
    primary_format: str
    format_instructions: str
    aio_optimization_tips: List[str]
    aio_priority_keywords: List[str]


@router.post("/{strategy_id}/export-monok")
async def export_to_monok(
    strategy_id: UUID,
    include_aio_context: bool = Query(True),
    db: Session = Depends(get_db)
) -> List[MonokExportWithAIO]:
    """Export strategy to Monok format with optional AIO optimization context."""

    # ... existing export logic ...

    if include_aio_context:
        for thread_export in exports:
            # Get AIO keywords in this thread
            aio_keywords = [
                k for k in thread.keywords
                if k.has_ai_overview or k.aio_optimization_potential > 60
            ]

            if aio_keywords:
                thread_export.ai_optimization = AIOptimizationContext(
                    optimization_level="aio_priority" if len(aio_keywords) > 3 else "aio_optimized",
                    primary_format=_determine_aio_format(aio_keywords),
                    format_instructions=_get_format_instructions(aio_keywords),
                    aio_optimization_tips=_get_aio_tips(aio_keywords),
                    aio_priority_keywords=[k.keyword for k in aio_keywords[:5]]
                )

    return exports
```

---

## 7. Testing Requirements

### 7.1 Unit Tests

**File:** `tests/test_greenfield_pipeline.py`

```python
"""Tests for greenfield collection pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collector.greenfield_pipeline import (
    discover_greenfield_competitors,
    analyze_serps_for_winnability,
    build_growth_roadmap
)


class TestCompetitorDiscovery:
    """Test competitor discovery for greenfield."""

    @pytest.mark.asyncio
    async def test_discovers_from_serp(self):
        """Should discover competitors from SERP results."""
        mock_client = AsyncMock()
        mock_client.get_serp_results.return_value = [
            {"domain": "competitor1.com", "domain_rating": 45},
            {"domain": "competitor2.com", "domain_rating": 38},
        ]
        mock_client.get_domain_rank_overview.return_value = {
            "rank": 40,
            "organic_traffic": 5000,
            "organic_keywords": 500
        }

        competitors = await discover_greenfield_competitors(
            client=mock_client,
            seed_keywords=["test keyword"],
            known_competitors=["known.com"],
            market="United States",
            language="English"
        )

        assert len(competitors) >= 1
        assert any(c.domain == "competitor1.com" for c in competitors)

    @pytest.mark.asyncio
    async def test_filters_platform_domains(self):
        """Should filter out Wikipedia, Reddit, etc."""
        mock_client = AsyncMock()
        mock_client.get_serp_results.return_value = [
            {"domain": "wikipedia.org", "domain_rating": 95},
            {"domain": "reddit.com", "domain_rating": 91},
            {"domain": "realcompetitor.com", "domain_rating": 45},
        ]
        mock_client.get_domain_rank_overview.return_value = {"rank": 40}

        competitors = await discover_greenfield_competitors(
            client=mock_client,
            seed_keywords=["test"],
            known_competitors=[],
            market="United States",
            language="English"
        )

        domains = [c.domain for c in competitors]
        assert "wikipedia.org" not in domains
        assert "reddit.com" not in domains


class TestWinnabilityAnalysis:
    """Test SERP analysis for winnability."""

    @pytest.mark.asyncio
    async def test_calculates_winnability(self):
        """Should calculate winnability scores."""
        mock_client = AsyncMock()
        mock_client.get_serp_results.return_value = [
            {"domain_rating": 30, "position": 1},
            {"domain_rating": 25, "position": 2},
            {"domain_rating": 35, "position": 3},
        ]

        keywords = [{"keyword": "test keyword", "keyword_difficulty": 30}]

        analyzed = await analyze_serps_for_winnability(
            client=mock_client,
            keywords=keywords,
            target_dr=15,
            market="United States",
            language="English",
            industry="saas"
        )

        assert len(analyzed) == 1
        assert "winnability_score" in analyzed[0]
        assert analyzed[0]["winnability_score"] > 0


class TestGrowthRoadmap:
    """Test growth roadmap generation."""

    def test_builds_four_phases(self):
        """Should build roadmap with 4 phases."""
        beachheads = [
            {"keyword": f"kw{i}", "search_volume": 1000, "winnability_score": 75}
            for i in range(10)
        ]
        analyzed = beachheads + [
            {"keyword": f"other{i}", "search_volume": 500, "winnability_score": 50}
            for i in range(20)
        ]

        roadmap = build_growth_roadmap(
            beachhead_keywords=beachheads,
            analyzed_keywords=analyzed,
            target_dr=15
        )

        assert len(roadmap) == 4
        assert roadmap[0]["phase"] == "Foundation"
        assert roadmap[1]["phase"] == "Early Traction"
        assert roadmap[2]["phase"] == "Growth"
        assert roadmap[3]["phase"] == "Competitive"
```

### 7.2 Integration Tests

**File:** `tests/test_greenfield_integration.py`

```python
"""Integration tests for greenfield flow."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


class TestGreenfieldAPIFlow:
    """Test complete greenfield API flow."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_greenfield_overview_endpoint(self, client, greenfield_domain_id):
        """Should return greenfield overview."""
        response = client.get(f"/api/greenfield/{greenfield_domain_id}/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_mode"] == "greenfield"
        assert "market_opportunity_score" in data
        assert "beachhead_count" in data

    def test_beachhead_keywords_endpoint(self, client, greenfield_domain_id):
        """Should return beachhead keywords with winnability."""
        response = client.get(f"/api/greenfield/{greenfield_domain_id}/beachhead-keywords")

        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data

        if data["keywords"]:
            kw = data["keywords"][0]
            assert "winnability_score" in kw
            assert "personalized_difficulty" in kw

    def test_projections_endpoint(self, client, greenfield_domain_id):
        """Should return three projection scenarios."""
        response = client.get(f"/api/greenfield/{greenfield_domain_id}/projections")

        assert response.status_code == 200
        data = response.json()
        assert "conservative" in data
        assert "expected" in data
        assert "aggressive" in data
```

---

## 8. Migration Strategy

### 8.1 Rollout Plan

1. **Phase A: Database Migration** (Day 1-2)
   - Run migration script to add new columns/tables
   - Backfill `analysis_mode = 'standard'` for existing analyses
   - Test database constraints

2. **Phase B: Backend Code Deployment** (Day 3-5)
   - Deploy orchestrator changes (greenfield routing)
   - Deploy greenfield pipeline
   - Deploy new API endpoints
   - Feature flag: `GREENFIELD_ENABLED=false` initially

3. **Phase C: Internal Testing** (Day 6-10)
   - Enable greenfield for test domains
   - Run end-to-end tests
   - Verify data quality

4. **Phase D: Gradual Rollout** (Day 11-15)
   - Enable for 10% of new analyses
   - Monitor error rates
   - Scale to 100%

### 8.2 Feature Flags

```python
# config.py
GREENFIELD_ENABLED = os.getenv("GREENFIELD_ENABLED", "false").lower() == "true"
GREENFIELD_ROLLOUT_PERCENT = int(os.getenv("GREENFIELD_ROLLOUT_PERCENT", "0"))
```

### 8.3 Rollback Plan

If issues occur:
1. Set `GREENFIELD_ENABLED=false` - immediate disable
2. New analyses route to standard mode
3. Existing greenfield analyses remain accessible (read-only)

---

## 9. Implementation Phases

### Phase 1: Database & Models (Week 1)
- [ ] Create migration script
- [ ] Add new models to `models.py`
- [ ] Run migration on staging
- [ ] Test model relationships

### Phase 2: Orchestrator & Pipeline (Week 2)
- [ ] Implement domain classification
- [ ] Create `greenfield_pipeline.py`
- [ ] Create `hybrid_pipeline.py`
- [ ] Wire scoring module

### Phase 3: API Endpoints (Week 3)
- [ ] Create `api/greenfield.py`
- [ ] Implement all 6 endpoints
- [ ] Register router
- [ ] Write endpoint tests

### Phase 4: Strategy Builder (Week 4)
- [ ] Update thread suggestions
- [ ] Add AIO context to export
- [ ] Test Monok export

### Phase 5: Testing & QA (Week 5)
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance testing

### Phase 6: Rollout (Week 6)
- [ ] Deploy to staging
- [ ] Internal testing
- [ ] Gradual production rollout
- [ ] Monitor and fix issues

---

## Summary

| Component | Files to Create/Modify | Estimated LOC |
|-----------|----------------------|---------------|
| Database Schema | `models.py`, migration | ~400 |
| Orchestrator | `orchestrator.py` | ~200 |
| Greenfield Pipeline | `greenfield_pipeline.py` (NEW) | ~600 |
| Hybrid Pipeline | `hybrid_pipeline.py` (NEW) | ~300 |
| API Endpoints | `api/greenfield.py` (NEW) | ~500 |
| Strategy Builder | `api/strategy.py` | ~200 |
| Scoring Integration | `src/scoring/greenfield.py` | ~100 |
| Tests | Multiple test files | ~800 |
| **Total** | | **~3,100 LOC** |

**Timeline:** 4-6 weeks with 1-2 engineers
**Risk Level:** Medium (new data pipeline, but isolated from existing flows)

---

**End of Implementation Plan**
