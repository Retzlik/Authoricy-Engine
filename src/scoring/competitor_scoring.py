"""
Competitor Strategic Value Scoring

Scores competitors based on signals available BEFORE deep analysis:
- Domain Rating (DR)
- Organic Traffic
- Organic Keyword COUNT (not the keywords themselves)
- Discovery source and confidence
- SERP frequency

This scoring is used to:
1. Assign competitors to tiers (Benchmark, Keyword Source, Market Intel)
2. Rank competitors within tiers
3. Generate explanations for tier assignments
4. Support auto-curation recommendations

The actual keyword mining happens AFTER user confirmation, not here.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class CompetitorTier(Enum):
    """Competitor tier classification."""
    BENCHMARK = "benchmark"           # Strategic benchmarks (3-5)
    KEYWORD_SOURCE = "keyword_source" # Keyword mining sources (10-15)
    MARKET_INTEL = "market_intel"     # Market intelligence (10-15)
    REJECTED = "rejected"             # Didn't pass filtering/scoring


class RejectionGate(Enum):
    """Which filtering gate rejected the competitor."""
    HARD_EXCLUSION = "hard_exclusion"       # Platform, social media, tech giants
    TOOL_SERVICE = "tool_service"           # Payment, analytics, infrastructure
    INVALID_TLD = "invalid_tld"             # Not a valid TLD
    TARGET_DOMAIN = "target_domain"         # User's own domain
    MINIMUM_VIABILITY = "minimum_viability" # No organic presence
    LOW_CONFIDENCE = "low_confidence"       # AI discovery too uncertain
    LOW_SCORE = "low_score"                 # Score below threshold


# Scoring thresholds
TIER_THRESHOLDS = {
    "benchmark_min_score": 60,
    "benchmark_min_relevance": 20,
    "benchmark_min_authority_proximity": 15,
    "keyword_source_min_score": 40,
    "keyword_source_min_data_richness": 10,
    "market_intel_min_score": 20,
}

# Tier limits
TIER_LIMITS = {
    "max_benchmarks": 5,
    "max_keyword_sources": 15,
    "max_market_intel": 15,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ScoreBreakdown:
    """Breakdown of strategic value score components."""
    relevance_score: float = 0.0          # 0-35: Business match
    authority_proximity_score: float = 0.0 # 0-25: DR comparison
    data_richness_score: float = 0.0      # 0-25: Keyword count
    market_presence_score: float = 0.0    # 0-15: Traffic

    @property
    def total(self) -> float:
        """Total strategic value score (0-100)."""
        return min(100, (
            self.relevance_score +
            self.authority_proximity_score +
            self.data_richness_score +
            self.market_presence_score
        ))

    def to_dict(self) -> Dict[str, float]:
        return {
            "relevance_score": round(self.relevance_score, 1),
            "authority_proximity_score": round(self.authority_proximity_score, 1),
            "data_richness_score": round(self.data_richness_score, 1),
            "market_presence_score": round(self.market_presence_score, 1),
            "total": round(self.total, 1),
        }


@dataclass
class ScoredCompetitor:
    """Competitor with strategic value scoring and tier assignment."""
    domain: str

    # Original discovery data
    discovery_source: str = ""          # perplexity, serp, dataforseo, user_provided
    discovery_reason: str = ""          # Why discovered
    discovery_confidence: float = 0.0   # 0-1 confidence from Perplexity
    serp_frequency: int = 0             # Found in N seed keyword SERPs

    # Metrics (from basic API calls)
    domain_rating: int = 0
    organic_traffic: int = 0
    organic_keywords: int = 0
    referring_domains: int = 0

    # Scoring
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)

    # Tier assignment
    tier: CompetitorTier = CompetitorTier.REJECTED
    tier_rank: int = 0                  # Rank within tier (1 = highest)
    tier_reason: str = ""               # Why assigned to this tier
    recommendation: str = ""            # What to do with this competitor

    # Selection
    is_auto_selected: bool = False      # Pre-selected for tier
    is_user_provided: bool = False      # User-provided competitor

    @property
    def strategic_value_score(self) -> float:
        """Alias for total score."""
        return self.score_breakdown.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "discovery_source": self.discovery_source,
            "discovery_reason": self.discovery_reason,
            "discovery_confidence": self.discovery_confidence,
            "serp_frequency": self.serp_frequency,
            "domain_rating": self.domain_rating,
            "organic_traffic": self.organic_traffic,
            "organic_keywords": self.organic_keywords,
            "referring_domains": self.referring_domains,
            "strategic_value_score": round(self.strategic_value_score, 1),
            "score_breakdown": self.score_breakdown.to_dict(),
            "tier": self.tier.value,
            "tier_rank": self.tier_rank,
            "tier_reason": self.tier_reason,
            "recommendation": self.recommendation,
            "is_auto_selected": self.is_auto_selected,
            "is_user_provided": self.is_user_provided,
        }


@dataclass
class RejectedCompetitor:
    """Competitor that was filtered out."""
    domain: str
    rejection_gate: RejectionGate
    rejection_reason: str
    discovery_source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "rejection_gate": self.rejection_gate.value,
            "rejection_reason": self.rejection_reason,
            "discovery_source": self.discovery_source,
        }


@dataclass
class TieredCompetitorSet:
    """Complete tiered competitor set with scoring."""
    # Tiered competitors (auto-selected)
    benchmarks: List[ScoredCompetitor] = field(default_factory=list)
    keyword_sources: List[ScoredCompetitor] = field(default_factory=list)
    market_intel: List[ScoredCompetitor] = field(default_factory=list)

    # Rejected with reasons
    rejected: List[RejectedCompetitor] = field(default_factory=list)

    # Stats
    total_discovered: int = 0
    total_after_filtering: int = 0

    # Target domain DR (for reference)
    target_dr: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmarks": [c.to_dict() for c in self.benchmarks],
            "keyword_sources": [c.to_dict() for c in self.keyword_sources],
            "market_intel": [c.to_dict() for c in self.market_intel],
            "rejected": [r.to_dict() for r in self.rejected],
            "total_discovered": self.total_discovered,
            "total_after_filtering": self.total_after_filtering,
            "target_dr": self.target_dr,
            "counts": {
                "benchmarks": len(self.benchmarks),
                "keyword_sources": len(self.keyword_sources),
                "market_intel": len(self.market_intel),
                "rejected": len(self.rejected),
            },
        }


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_relevance_score(
    discovery_source: str,
    discovery_confidence: float,
    serp_frequency: int,
    is_user_provided: bool,
) -> float:
    """
    Calculate relevance score (0-35 points).

    Based on discovery metadata - how confident are we this is a real competitor?

    Args:
        discovery_source: Where the competitor was discovered
        discovery_confidence: AI confidence score (0-1)
        serp_frequency: Found in N seed keyword SERPs
        is_user_provided: User explicitly listed this competitor

    Returns:
        Relevance score (0-35)
    """
    # User-provided gets highest trust
    if is_user_provided:
        return 35.0

    # Perplexity AI discovery with confidence
    if discovery_source == "perplexity":
        if discovery_confidence >= 0.85:
            return 32.0
        elif discovery_confidence >= 0.7:
            return 26.0
        elif discovery_confidence >= 0.6:
            return 20.0
        else:
            return 12.0

    # SERP-based discovery - frequency matters
    if discovery_source == "serp":
        if serp_frequency >= 4:
            return 28.0  # Found in 4+ SERPs
        elif serp_frequency >= 3:
            return 24.0
        elif serp_frequency >= 2:
            return 18.0
        else:
            return 12.0  # Found in just 1 SERP

    # DataForSEO Competitors API
    if discovery_source == "dataforseo_competitors":
        return 22.0  # API explicitly says they compete

    # Unknown source
    return 10.0


def calculate_authority_proximity_score(
    competitor_dr: int,
    target_dr: int,
) -> float:
    """
    Calculate authority proximity score (0-25 points).

    How close is their DR to ours? Closer = better for benchmarking.

    Args:
        competitor_dr: Competitor's Domain Rating (0-100)
        target_dr: Target domain's DR (0-100)

    Returns:
        Authority proximity score (0-25)
    """
    if competitor_dr == 0 and target_dr == 0:
        # Both are new domains - perfect peers
        return 25.0

    dr_diff = abs(competitor_dr - target_dr)

    if dr_diff <= 5:
        return 25.0   # Perfect peer
    elif dr_diff <= 10:
        return 22.0   # Very close
    elif dr_diff <= 15:
        return 18.0   # Close enough
    elif dr_diff <= 20:
        return 15.0   # Reachable
    elif dr_diff <= 30:
        return 10.0   # Stretch goal
    elif competitor_dr > target_dr:
        return 8.0    # Aspirational (they're much bigger)
    else:
        return 5.0    # Too weak to benchmark against


def calculate_data_richness_score(organic_keywords: int) -> float:
    """
    Calculate data richness score (0-25 points).

    How many keywords do they have? More = more mining potential.

    Args:
        organic_keywords: Keyword COUNT (not the keywords themselves)

    Returns:
        Data richness score (0-25)
    """
    if organic_keywords >= 10000:
        return 25.0   # Goldmine
    elif organic_keywords >= 5000:
        return 22.0   # Very rich
    elif organic_keywords >= 2000:
        return 18.0   # Rich
    elif organic_keywords >= 1000:
        return 15.0   # Good
    elif organic_keywords >= 500:
        return 12.0   # Decent
    elif organic_keywords >= 200:
        return 8.0    # Limited
    elif organic_keywords >= 50:
        return 5.0    # Sparse
    else:
        return 2.0    # Minimal


def calculate_market_presence_score(organic_traffic: int) -> float:
    """
    Calculate market presence score (0-15 points).

    How significant is this player in the market?

    Args:
        organic_traffic: Monthly organic traffic estimate

    Returns:
        Market presence score (0-15)
    """
    if organic_traffic >= 500000:
        return 15.0   # Major player
    elif organic_traffic >= 100000:
        return 13.0   # Significant
    elif organic_traffic >= 50000:
        return 11.0   # Notable
    elif organic_traffic >= 20000:
        return 9.0    # Moderate
    elif organic_traffic >= 10000:
        return 7.0    # Small but real
    elif organic_traffic >= 5000:
        return 5.0    # Emerging
    elif organic_traffic >= 1000:
        return 3.0    # Small
    else:
        return 1.0    # Minimal


def calculate_strategic_value(
    discovery_source: str,
    discovery_confidence: float,
    serp_frequency: int,
    is_user_provided: bool,
    competitor_dr: int,
    target_dr: int,
    organic_keywords: int,
    organic_traffic: int,
) -> ScoreBreakdown:
    """
    Calculate complete strategic value score breakdown.

    Args:
        discovery_source: Where discovered
        discovery_confidence: AI confidence (0-1)
        serp_frequency: SERP appearance count
        is_user_provided: User listed this competitor
        competitor_dr: Competitor's DR
        target_dr: Target's DR
        organic_keywords: Keyword count
        organic_traffic: Traffic estimate

    Returns:
        ScoreBreakdown with all components
    """
    return ScoreBreakdown(
        relevance_score=calculate_relevance_score(
            discovery_source, discovery_confidence, serp_frequency, is_user_provided
        ),
        authority_proximity_score=calculate_authority_proximity_score(
            competitor_dr, target_dr
        ),
        data_richness_score=calculate_data_richness_score(organic_keywords),
        market_presence_score=calculate_market_presence_score(organic_traffic),
    )


# =============================================================================
# TIER ASSIGNMENT
# =============================================================================

def assign_tier(
    competitor: ScoredCompetitor,
    target_dr: int,
) -> Tuple[CompetitorTier, str, str]:
    """
    Assign a tier to a scored competitor.

    Args:
        competitor: Scored competitor
        target_dr: Target domain's DR

    Returns:
        (tier, tier_reason, recommendation)
    """
    score = competitor.score_breakdown
    total = score.total

    # Check for benchmark tier
    if (total >= TIER_THRESHOLDS["benchmark_min_score"] and
        score.relevance_score >= TIER_THRESHOLDS["benchmark_min_relevance"] and
        score.authority_proximity_score >= TIER_THRESHOLDS["benchmark_min_authority_proximity"]):

        # Determine specific reason
        dr_diff = competitor.domain_rating - target_dr
        if abs(dr_diff) <= 10:
            tier_reason = f"Similar authority (DR {competitor.domain_rating} vs your DR {target_dr})"
        elif dr_diff > 10:
            tier_reason = f"Aspirational benchmark (DR {competitor.domain_rating})"
        else:
            tier_reason = f"Emerging competitor (DR {competitor.domain_rating})"

        if competitor.is_user_provided:
            tier_reason = f"User-identified competitor. {tier_reason}"
        elif competitor.discovery_confidence >= 0.8:
            tier_reason = f"High-confidence match. {tier_reason}"

        recommendation = "Benchmark for gap analysis, feature comparison, and positioning"
        return (CompetitorTier.BENCHMARK, tier_reason, recommendation)

    # Check for keyword source tier
    if (total >= TIER_THRESHOLDS["keyword_source_min_score"] and
        score.data_richness_score >= TIER_THRESHOLDS["keyword_source_min_data_richness"]):

        kw_count = competitor.organic_keywords
        if kw_count >= 5000:
            tier_reason = f"Keyword goldmine ({kw_count:,} keywords to mine)"
        elif kw_count >= 1000:
            tier_reason = f"Rich keyword source ({kw_count:,} keywords)"
        else:
            tier_reason = f"Keyword source ({kw_count:,} keywords)"

        recommendation = f"Mine their {kw_count:,} keywords for opportunities"
        return (CompetitorTier.KEYWORD_SOURCE, tier_reason, recommendation)

    # Check for market intel tier
    if total >= TIER_THRESHOLDS["market_intel_min_score"]:
        tier_reason = "Part of competitive landscape"

        if competitor.organic_traffic >= 50000:
            tier_reason = f"Notable market player ({competitor.organic_traffic:,} monthly traffic)"

        recommendation = "Include in market sizing and competitive density"
        return (CompetitorTier.MARKET_INTEL, tier_reason, recommendation)

    # Below all thresholds
    tier_reason = f"Score too low ({total:.0f}/100)"
    recommendation = "Consider excluding - low strategic value"
    return (CompetitorTier.REJECTED, tier_reason, recommendation)


def generate_tier_explanation(
    competitor: ScoredCompetitor,
    target_dr: int,
) -> str:
    """
    Generate a human-readable explanation for why competitor is in their tier.

    Args:
        competitor: Scored competitor
        target_dr: Target domain's DR

    Returns:
        Explanation string
    """
    score = competitor.score_breakdown
    parts = []

    # Authority explanation
    dr_diff = competitor.domain_rating - target_dr
    if abs(dr_diff) <= 10:
        parts.append(f"Similar authority level (DR {competitor.domain_rating})")
    elif dr_diff > 20:
        parts.append(f"Market leader (DR {competitor.domain_rating})")
    elif dr_diff > 0:
        parts.append(f"Slightly stronger (DR {competitor.domain_rating})")
    elif dr_diff < -20:
        parts.append(f"Emerging player (DR {competitor.domain_rating})")

    # Relevance explanation
    if competitor.is_user_provided:
        parts.append("You identified them as a competitor")
    elif competitor.discovery_confidence >= 0.8:
        parts.append(f"AI identified as direct competitor")
    elif competitor.serp_frequency >= 3:
        parts.append(f"Ranks for {competitor.serp_frequency} of your target keywords")

    # Data richness explanation
    if competitor.organic_keywords >= 5000:
        parts.append(f"Rich data source ({competitor.organic_keywords:,} keywords)")
    elif competitor.organic_keywords >= 1000:
        parts.append(f"Good data source ({competitor.organic_keywords:,} keywords)")

    return ". ".join(parts) if parts else "Relevant to your market"


# =============================================================================
# MAIN SCORING AND TIERING FUNCTION
# =============================================================================

def score_and_tier_competitors(
    candidates: List[Dict[str, Any]],
    target_dr: int,
    rejected_domains: Optional[List[Dict[str, Any]]] = None,
) -> TieredCompetitorSet:
    """
    Score all candidates and assign to tiers.

    This is the main entry point for the competitor scoring system.

    Args:
        candidates: List of candidate dicts with:
            - domain
            - discovery_source
            - discovery_reason
            - discovery_confidence (optional)
            - serp_frequency (optional)
            - domain_rating
            - organic_traffic
            - organic_keywords
            - referring_domains (optional)
            - is_user_provided (optional)
        target_dr: Target domain's Domain Rating
        rejected_domains: Pre-rejected domains with reasons (from filtering)

    Returns:
        TieredCompetitorSet with all competitors scored and tiered
    """
    result = TieredCompetitorSet(
        total_discovered=len(candidates) + len(rejected_domains or []),
        target_dr=target_dr,
    )

    # Add pre-rejected domains
    if rejected_domains:
        for r in rejected_domains:
            result.rejected.append(RejectedCompetitor(
                domain=r.get("domain", ""),
                rejection_gate=RejectionGate(r.get("rejection_gate", "hard_exclusion")),
                rejection_reason=r.get("rejection_reason", "Unknown"),
                discovery_source=r.get("discovery_source", ""),
            ))

    # Score all candidates
    scored_competitors: List[ScoredCompetitor] = []

    for candidate in candidates:
        domain = candidate.get("domain", "")
        if not domain:
            continue

        is_user_provided = candidate.get("discovery_source") == "user_provided"

        # Calculate score breakdown
        score_breakdown = calculate_strategic_value(
            discovery_source=candidate.get("discovery_source", ""),
            discovery_confidence=candidate.get("discovery_confidence", candidate.get("relevance_score", 0.5)),
            serp_frequency=candidate.get("serp_frequency", 1),
            is_user_provided=is_user_provided,
            competitor_dr=candidate.get("domain_rating", 0),
            target_dr=target_dr,
            organic_keywords=candidate.get("organic_keywords", 0),
            organic_traffic=candidate.get("organic_traffic", 0),
        )

        # Create scored competitor
        scored = ScoredCompetitor(
            domain=domain,
            discovery_source=candidate.get("discovery_source", ""),
            discovery_reason=candidate.get("discovery_reason", ""),
            discovery_confidence=candidate.get("discovery_confidence", candidate.get("relevance_score", 0.5)),
            serp_frequency=candidate.get("serp_frequency", 1),
            domain_rating=candidate.get("domain_rating", 0),
            organic_traffic=candidate.get("organic_traffic", 0),
            organic_keywords=candidate.get("organic_keywords", 0),
            referring_domains=candidate.get("referring_domains", 0),
            score_breakdown=score_breakdown,
            is_user_provided=is_user_provided,
        )

        # Assign tier
        tier, tier_reason, recommendation = assign_tier(scored, target_dr)
        scored.tier = tier
        scored.tier_reason = tier_reason
        scored.recommendation = recommendation

        scored_competitors.append(scored)

    # Gate: Minimum viability check (no organic presence)
    viable_competitors = []
    for scored in scored_competitors:
        if (scored.domain_rating == 0 and
            scored.organic_traffic == 0 and
            scored.organic_keywords == 0 and
            not scored.is_user_provided):
            # No organic presence at all - reject
            result.rejected.append(RejectedCompetitor(
                domain=scored.domain,
                rejection_gate=RejectionGate.MINIMUM_VIABILITY,
                rejection_reason="No organic presence (0 DR, 0 traffic, 0 keywords)",
                discovery_source=scored.discovery_source,
            ))
        else:
            viable_competitors.append(scored)

    # Sort within each tier by strategic value score (descending)
    benchmarks = sorted(
        [c for c in viable_competitors if c.tier == CompetitorTier.BENCHMARK],
        key=lambda x: x.strategic_value_score,
        reverse=True,
    )
    keyword_sources = sorted(
        [c for c in viable_competitors if c.tier == CompetitorTier.KEYWORD_SOURCE],
        key=lambda x: x.strategic_value_score,
        reverse=True,
    )
    market_intel = sorted(
        [c for c in viable_competitors if c.tier == CompetitorTier.MARKET_INTEL],
        key=lambda x: x.strategic_value_score,
        reverse=True,
    )
    low_score = [c for c in viable_competitors if c.tier == CompetitorTier.REJECTED]

    # Apply tier limits and assign ranks
    for i, comp in enumerate(benchmarks[:TIER_LIMITS["max_benchmarks"]]):
        comp.tier_rank = i + 1
        comp.is_auto_selected = True
        result.benchmarks.append(comp)

    # Overflow benchmarks go to keyword_sources
    for comp in benchmarks[TIER_LIMITS["max_benchmarks"]:]:
        comp.tier = CompetitorTier.KEYWORD_SOURCE
        comp.tier_reason = f"Overflow from benchmarks. {comp.tier_reason}"
        keyword_sources.insert(0, comp)

    for i, comp in enumerate(keyword_sources[:TIER_LIMITS["max_keyword_sources"]]):
        comp.tier_rank = i + 1
        comp.is_auto_selected = True
        result.keyword_sources.append(comp)

    # Overflow keyword_sources go to market_intel
    for comp in keyword_sources[TIER_LIMITS["max_keyword_sources"]:]:
        comp.tier = CompetitorTier.MARKET_INTEL
        comp.tier_reason = f"Overflow from keyword sources. {comp.tier_reason}"
        market_intel.insert(0, comp)

    for i, comp in enumerate(market_intel[:TIER_LIMITS["max_market_intel"]]):
        comp.tier_rank = i + 1
        comp.is_auto_selected = True
        result.market_intel.append(comp)

    # Overflow market_intel and low_score go to rejected
    for comp in market_intel[TIER_LIMITS["max_market_intel"]:]:
        result.rejected.append(RejectedCompetitor(
            domain=comp.domain,
            rejection_gate=RejectionGate.LOW_SCORE,
            rejection_reason=f"Exceeded tier limit (score: {comp.strategic_value_score:.0f})",
            discovery_source=comp.discovery_source,
        ))

    for comp in low_score:
        result.rejected.append(RejectedCompetitor(
            domain=comp.domain,
            rejection_gate=RejectionGate.LOW_SCORE,
            rejection_reason=comp.tier_reason,
            discovery_source=comp.discovery_source,
        ))

    result.total_after_filtering = (
        len(result.benchmarks) +
        len(result.keyword_sources) +
        len(result.market_intel)
    )

    logger.info(
        f"Scored and tiered {len(candidates)} candidates: "
        f"{len(result.benchmarks)} benchmarks, "
        f"{len(result.keyword_sources)} keyword sources, "
        f"{len(result.market_intel)} market intel, "
        f"{len(result.rejected)} rejected"
    )

    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tier_summary(tiered_set: TieredCompetitorSet) -> str:
    """Generate a summary message for the tiered competitor set."""
    total = tiered_set.total_discovered
    filtered = total - tiered_set.total_after_filtering

    message_parts = [
        f"Discovered {total} potential competitors.",
    ]

    if filtered > 0:
        message_parts.append(f"Filtered {filtered} (platforms, tools, irrelevant).")

    message_parts.append(
        f"Presenting {tiered_set.total_after_filtering} ranked by strategic value:"
    )

    if tiered_set.benchmarks:
        message_parts.append(
            f"• {len(tiered_set.benchmarks)} strategic benchmarks (for gap analysis)"
        )

    if tiered_set.keyword_sources:
        message_parts.append(
            f"• {len(tiered_set.keyword_sources)} keyword sources (for opportunity mining)"
        )

    if tiered_set.market_intel:
        message_parts.append(
            f"• {len(tiered_set.market_intel)} market intelligence (for landscape)"
        )

    return " ".join(message_parts)
