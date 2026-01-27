"""
Precomputation Pipeline

The most impactful optimization: compute expensive dashboard data ONCE
after analysis completes, not on every page load.

This pipeline:
1. Runs automatically when analysis completes
2. Computes all dashboard aggregations
3. Stores results in PostgreSQL precomputed_dashboard table
4. Reduces dashboard load from 2-5s to <100ms

Key insight: Most dashboard data only changes when a new analysis runs
(weekly/monthly). We're re-computing data that hasn't changed on every
page load - this eliminates that waste.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy import func, and_, or_, case, desc, asc
from sqlalchemy.orm import Session

from src.cache.postgres_cache import PostgresCache
from src.cache.headers import generate_etag


logger = logging.getLogger(__name__)


class PrecomputationPipeline:
    """
    Precomputes all expensive dashboard data after analysis completion.

    Run this as a background job when analysis finishes.
    All dashboard queries become simple cache lookups.
    """

    def __init__(self, db: Session):
        self.db = db
        self._cache = PostgresCache(db)

    def precompute_all(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Precompute all dashboard data for an analysis.

        This is the main entry point, called after analysis completes.

        Args:
            analysis_id: The completed analysis ID

        Returns:
            Dict with precomputation results and timing
        """
        logger.info(f"Starting precomputation for analysis: {analysis_id}")
        start_time = datetime.utcnow()

        # Import models here to avoid circular imports
        from src.database.models import AnalysisRun

        analysis = self.db.query(AnalysisRun).filter(
            AnalysisRun.id == analysis_id
        ).first()

        if not analysis:
            raise ValueError(f"Analysis not found: {analysis_id}")

        domain_id = str(analysis.domain_id)
        analysis_id_str = str(analysis_id)

        # Invalidate old cache for this domain
        self._cache.invalidate_domain(domain_id)

        # Run all precomputations
        errors = []
        component_names = [
            "overview", "sparklines", "sov", "battleground",
            "clusters", "content_audit", "opportunities"
        ]

        for component in component_names:
            try:
                method_name = f"_precompute_{component}"
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    method(domain_id, analysis_id_str, analysis)
                    logger.debug(f"Precomputed {component} for analysis {analysis_id_str}")
            except Exception as e:
                errors.append(f"{component}: {str(e)}")
                logger.error(f"Precomputation error for {component}: {e}")

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Precomputation complete for {analysis_id} in {elapsed:.2f}s"
            + (f" with {len(errors)} errors" if errors else "")
        )

        return {
            "analysis_id": analysis_id_str,
            "domain_id": domain_id,
            "duration_seconds": elapsed,
            "components_computed": len(component_names) - len(errors),
            "errors": errors,
        }

    def _precompute_overview(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute dashboard overview."""
        from src.database.models import (
            Keyword, DomainMetricsHistory, TechnicalMetrics,
            KeywordGap, AIVisibility, AnalysisStatus, AnalysisRun
        )

        # Get current metrics
        current_metrics = self.db.query(DomainMetricsHistory).filter(
            DomainMetricsHistory.analysis_run_id == analysis_id
        ).first()

        # Get previous analysis for comparison
        previous_analysis = self.db.query(AnalysisRun).filter(
            AnalysisRun.domain_id == domain_id,
            AnalysisRun.status == AnalysisStatus.COMPLETED,
            AnalysisRun.id != analysis_id
        ).order_by(desc(AnalysisRun.completed_at)).first()

        previous_metrics = None
        if previous_analysis:
            previous_metrics = self.db.query(DomainMetricsHistory).filter(
                DomainMetricsHistory.analysis_run_id == previous_analysis.id
            ).first()

        # Keyword stats (single query)
        keyword_stats = self.db.query(
            func.count(Keyword.id).label("total"),
            func.sum(case((Keyword.current_position <= 10, 1), else_=0)).label("top_10"),
            func.sum(case((Keyword.current_position <= 3, 1), else_=0)).label("top_3"),
            func.sum(case((Keyword.current_position.between(4, 10), 1), else_=0)).label("pos_4_10"),
            func.sum(case((Keyword.current_position.between(11, 20), 1), else_=0)).label("pos_11_20"),
            func.sum(case((Keyword.current_position.between(21, 50), 1), else_=0)).label("pos_21_50"),
            func.sum(case((Keyword.current_position > 50, 1), else_=0)).label("pos_51_plus"),
            func.avg(Keyword.opportunity_score).label("avg_opportunity"),
            func.sum(Keyword.estimated_traffic).label("total_traffic"),
        ).filter(
            Keyword.analysis_run_id == analysis_id
        ).first()

        # Quick wins count
        quick_wins = self.db.query(func.count(Keyword.id)).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.opportunity_score >= 70,
            Keyword.current_position.between(11, 30)
        ).scalar() or 0

        # At-risk keywords
        at_risk = self.db.query(func.count(Keyword.id)).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.position_change < -3,
            Keyword.current_position <= 20
        ).scalar() or 0

        # Content gaps
        content_gaps = self.db.query(func.count(KeywordGap.id)).filter(
            KeywordGap.analysis_run_id == analysis_id,
            KeywordGap.target_position == None
        ).scalar() or 0

        # AI mentions
        ai_mentions = self.db.query(func.count(AIVisibility.id)).filter(
            AIVisibility.analysis_run_id == analysis_id,
            AIVisibility.is_mentioned == True
        ).scalar() or 0

        # Technical metrics
        technical = self.db.query(TechnicalMetrics).filter(
            TechnicalMetrics.analysis_run_id == analysis_id
        ).first()

        # Calculate health scores
        total = keyword_stats.total or 1
        top_10 = keyword_stats.top_10 or 0
        keyword_health = min(100, (top_10 / total * 200) + (keyword_stats.avg_opportunity or 0))
        backlink_health = min(100, ((current_metrics.referring_domains or 0) / 100 * 50 + 50)) if current_metrics else 50
        technical_health = (technical.seo_score or 50) if technical else 50
        content_health = min(100, (total / 100) * 30 + 70 - (content_gaps / total) * 100)
        ai_health = min(100, ai_mentions * 10) if ai_mentions else 0
        overall_health = (keyword_health * 0.3 + backlink_health * 0.2 +
                         technical_health * 0.2 + content_health * 0.2 + ai_health * 0.1)

        # Build metric changes
        def metric_change(current, previous):
            if previous is None:
                return {"current": current or 0, "trend": "stable"}
            change = (current or 0) - (previous or 0)
            pct = (change / previous * 100) if previous else 0
            trend = "up" if pct > 5 else "down" if pct < -5 else "stable"
            return {
                "current": current or 0,
                "previous": previous,
                "change": change,
                "change_percent": round(pct, 1),
                "trend": trend,
            }

        overview = {
            "domain": analysis.domain.domain,
            "analysis_id": analysis_id,
            "analysis_date": (analysis.completed_at or analysis.created_at).isoformat(),
            "health": {
                "overall": round(overall_health, 1),
                "keyword_health": round(keyword_health, 1),
                "backlink_health": round(backlink_health, 1),
                "technical_health": round(technical_health, 1),
                "content_health": round(content_health, 1),
                "ai_visibility": round(ai_health, 1),
            },
            "organic_traffic": metric_change(
                current_metrics.organic_traffic if current_metrics else 0,
                previous_metrics.organic_traffic if previous_metrics else None
            ),
            "organic_keywords": metric_change(
                current_metrics.organic_keywords if current_metrics else 0,
                previous_metrics.organic_keywords if previous_metrics else None
            ),
            "domain_rating": metric_change(
                int(current_metrics.domain_rating or 0) if current_metrics else 0,
                int(previous_metrics.domain_rating or 0) if previous_metrics else None
            ),
            "referring_domains": metric_change(
                current_metrics.referring_domains if current_metrics else 0,
                previous_metrics.referring_domains if previous_metrics else None
            ),
            "backlinks": metric_change(
                current_metrics.backlinks_total if current_metrics else 0,
                previous_metrics.backlinks_total if previous_metrics else None
            ),
            "positions": {
                "top_3": keyword_stats.top_3 or 0,
                "4_10": keyword_stats.pos_4_10 or 0,
                "11_20": keyword_stats.pos_11_20 or 0,
                "21_50": keyword_stats.pos_21_50 or 0,
                "51_plus": keyword_stats.pos_51_plus or 0,
            },
            "quick_wins_count": quick_wins,
            "at_risk_keywords": at_risk,
            "content_gaps": content_gaps,
            "ai_mentions": ai_mentions,
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "overview")
        self._cache.set_dashboard(domain_id, "overview", overview, analysis_id, etag)
        return True

    def _precompute_sparklines(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute sparkline data for top keywords."""
        from src.database.models import Keyword, RankingHistory, DomainMetricsHistory

        # Get top 50 keywords by traffic
        keywords = self.db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.current_position <= 50
        ).order_by(desc(Keyword.estimated_traffic)).limit(50).all()

        cutoff_date = datetime.utcnow() - timedelta(days=30)
        sparkline_keywords = []

        for kw in keywords:
            # Get ranking history
            history = self.db.query(RankingHistory).filter(
                RankingHistory.domain_id == domain_id,
                RankingHistory.keyword_normalized == kw.keyword_normalized,
                RankingHistory.recorded_at >= cutoff_date
            ).order_by(asc(RankingHistory.recorded_at)).all()

            sparkline = [
                {"date": h.recorded_at.strftime("%Y-%m-%d"), "value": float(h.position or 100)}
                for h in history
            ]

            # Determine trend
            if len(sparkline) >= 2:
                first_val = sparkline[0]["value"]
                last_val = sparkline[-1]["value"]
                diff = first_val - last_val
                values = [p["value"] for p in sparkline]
                volatility = max(values) - min(values) if values else 0

                if volatility > 20:
                    trend = "volatile"
                elif diff > 5:
                    trend = "improving"
                elif diff < -5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            sparkline_keywords.append({
                "keyword_id": str(kw.id),
                "keyword": kw.keyword,
                "current_position": kw.current_position,
                "search_volume": kw.search_volume or 0,
                "opportunity_score": kw.opportunity_score or 0,
                "sparkline": sparkline,
                "trend": trend,
            })

        # Domain traffic sparkline
        traffic_history = self.db.query(DomainMetricsHistory).filter(
            DomainMetricsHistory.domain_id == domain_id,
            DomainMetricsHistory.recorded_at >= cutoff_date
        ).order_by(asc(DomainMetricsHistory.recorded_at)).all()

        domain_sparkline = [
            {"date": h.recorded_at.strftime("%Y-%m-%d"), "value": float(h.organic_traffic or 0)}
            for h in traffic_history
        ]

        sparklines_data = {
            "keywords": sparkline_keywords,
            "domain_traffic_sparkline": domain_sparkline,
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "sparklines")
        self._cache.set_dashboard(domain_id, "sparklines", sparklines_data, analysis_id, etag)
        return True

    def _precompute_sov(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute Share of Voice data."""
        from src.database.models import Keyword, Competitor, CompetitorType, Domain

        domain = self.db.query(Domain).filter(Domain.id == domain_id).first()

        # Get target domain's traffic
        target_stats = self.db.query(
            func.sum(Keyword.estimated_traffic).label("traffic"),
            func.count(Keyword.id).label("keyword_count"),
            func.avg(Keyword.current_position).label("avg_position")
        ).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.current_position <= 20,
            Keyword.current_position > 0
        ).first()

        target_traffic = target_stats.traffic or 0

        entries = [{
            "domain": domain.domain,
            "is_target": True,
            "estimated_traffic": int(target_traffic),
            "keyword_count": int(target_stats.keyword_count or 0),
            "avg_position": round(target_stats.avg_position or 0, 1),
            "share_percent": 0,
        }]

        # Get competitors
        competitors = self.db.query(Competitor).filter(
            Competitor.analysis_run_id == analysis_id,
            Competitor.competitor_type == CompetitorType.TRUE_COMPETITOR,
            Competitor.is_active == True
        ).limit(10).all()

        total_traffic = target_traffic
        for comp in competitors:
            comp_traffic = comp.organic_traffic or 0
            total_traffic += comp_traffic
            entries.append({
                "domain": comp.competitor_domain,
                "is_target": False,
                "estimated_traffic": comp_traffic,
                "keyword_count": comp.organic_keywords or 0,
                "avg_position": comp.avg_position or 0,
                "share_percent": 0,
            })

        # Calculate percentages
        for entry in entries:
            entry["share_percent"] = round(
                (entry["estimated_traffic"] / total_traffic * 100) if total_traffic > 0 else 0,
                1
            )

        entries.sort(key=lambda x: x["share_percent"], reverse=True)
        target_share = next((e["share_percent"] for e in entries if e["is_target"]), 0)

        sov_data = {
            "total_market_traffic": int(total_traffic),
            "target_share": target_share,
            "entries": entries,
            "trend_30d": None,
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "sov")
        self._cache.set_dashboard(domain_id, "sov", sov_data, analysis_id, etag)
        return True

    def _precompute_battleground(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute Attack/Defend battleground data."""
        from src.database.models import Keyword, KeywordGap

        limit = 25

        # ATTACK: Keyword gaps
        gaps = self.db.query(KeywordGap).filter(
            KeywordGap.analysis_run_id == analysis_id,
            or_(
                KeywordGap.target_position == None,
                KeywordGap.target_position > 20
            ),
            KeywordGap.best_competitor_position <= 10
        ).order_by(desc(KeywordGap.opportunity_score)).limit(limit * 2).all()

        attack_easy = []
        attack_hard = []

        for gap in gaps:
            difficulty = gap.keyword_difficulty or 50
            traffic_gain = gap.estimated_traffic_potential or self._estimate_traffic(5, gap.search_volume or 0)

            kw = {
                "keyword_id": str(gap.id),
                "keyword": gap.keyword,
                "search_volume": gap.search_volume or 0,
                "keyword_difficulty": difficulty,
                "opportunity_score": gap.opportunity_score or 0,
                "our_position": gap.target_position,
                "our_position_change": None,
                "best_competitor": gap.best_competitor or "Unknown",
                "best_competitor_position": gap.best_competitor_position or 0,
                "category": "attack_easy" if difficulty < 40 else "attack_hard",
                "priority_score": gap.difficulty_adjusted_score or gap.opportunity_score or 0,
                "action": "Create content targeting this keyword" if gap.target_position is None else "Optimize existing content",
                "estimated_traffic_gain": traffic_gain,
            }

            if difficulty < 40:
                attack_easy.append(kw)
            else:
                attack_hard.append(kw)

        # DEFEND: Declining keywords
        defend_keywords = self.db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.current_position <= 20,
            Keyword.current_position > 0,
            or_(
                Keyword.position_change < -2,
                Keyword.current_position.between(4, 10)
            )
        ).order_by(desc(Keyword.estimated_traffic)).limit(limit * 2).all()

        defend_priority = []
        defend_watch = []

        for kw in defend_keywords:
            is_declining = (kw.position_change or 0) < -2
            bkw = {
                "keyword_id": str(kw.id),
                "keyword": kw.keyword,
                "search_volume": kw.search_volume or 0,
                "keyword_difficulty": kw.keyword_difficulty or 50,
                "opportunity_score": kw.opportunity_score or 0,
                "our_position": kw.current_position,
                "our_position_change": kw.position_change,
                "best_competitor": "Competitors",
                "best_competitor_position": (kw.current_position or 5) - 1,
                "category": "defend_priority" if is_declining else "defend_watch",
                "priority_score": float(kw.estimated_traffic or 0),
                "action": "Urgent: Refresh content and build links" if is_declining else "Monitor and prepare defensive content",
                "estimated_traffic_gain": 0,
            }

            if is_declining:
                defend_priority.append(bkw)
            else:
                defend_watch.append(bkw)

        battleground_data = {
            "attack_easy": attack_easy[:limit],
            "attack_hard": attack_hard[:limit],
            "defend_priority": defend_priority[:limit],
            "defend_watch": defend_watch[:limit],
            "total_attack_opportunity": sum(k["estimated_traffic_gain"] for k in attack_easy + attack_hard),
            "total_at_risk_traffic": self._estimate_traffic(5, sum(k["search_volume"] for k in defend_priority)),
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "battleground")
        self._cache.set_dashboard(domain_id, "battleground", battleground_data, analysis_id, etag)
        return True

    def _precompute_clusters(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute topical authority clusters."""
        from src.database.models import ContentCluster

        clusters = self.db.query(ContentCluster).filter(
            ContentCluster.analysis_run_id == analysis_id
        ).order_by(desc(ContentCluster.topical_authority_score)).all()

        cluster_responses = []
        total_gaps = 0

        for cluster in clusters:
            total_gaps += cluster.content_gap_count or 0
            cluster_responses.append({
                "cluster_id": str(cluster.id),
                "cluster_name": cluster.cluster_name,
                "pillar_keyword": cluster.pillar_keyword,
                "authority_score": cluster.topical_authority_score or 0,
                "content_completeness": cluster.content_completeness or 0,
                "avg_position": cluster.avg_position or 0,
                "total_keywords": cluster.total_keywords or 0,
                "ranking_keywords": cluster.ranking_keywords or 0,
                "content_gaps": cluster.content_gap_count or 0,
                "total_traffic": cluster.total_traffic or 0,
                "total_search_volume": cluster.total_search_volume or 0,
                "top_competitor": cluster.top_competitor,
                "competitor_authority": None,
                "priority": cluster.priority or "medium",
                "recommended_action": (
                    f"Create {cluster.content_gap_count or 0} pieces of content to fill gaps"
                    if (cluster.content_gap_count or 0) > 0
                    else "Optimize existing content for better rankings"
                ),
            })

        overall = sum(c["authority_score"] for c in cluster_responses) / len(cluster_responses) if cluster_responses else 0

        clusters_data = {
            "clusters": cluster_responses,
            "overall_authority": round(overall, 1),
            "strongest_cluster": max(cluster_responses, key=lambda x: x["authority_score"])["cluster_name"] if cluster_responses else None,
            "weakest_cluster": min(cluster_responses, key=lambda x: x["authority_score"])["cluster_name"] if cluster_responses else None,
            "total_content_gaps": total_gaps,
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "clusters")
        self._cache.set_dashboard(domain_id, "clusters", clusters_data, analysis_id, etag)
        return True

    def _precompute_content_audit(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute content audit (KUCK) data."""
        from src.database.models import Page

        pages = self.db.query(Page).filter(
            Page.analysis_run_id == analysis_id
        ).all()

        keep = []
        update = []
        consolidate = []
        kill = []

        for page in pages:
            rec = (page.kuck_recommendation or "keep").lower()
            page_data = {
                "page_id": str(page.id),
                "url": page.url,
                "title": page.title,
                "organic_traffic": page.organic_traffic or 0,
                "organic_keywords": page.organic_keywords or 0,
                "backlinks": page.backlink_count or 0,
                "content_score": page.content_score or 50,
                "freshness_score": page.freshness_score or 50,
                "decay_score": page.decay_score or 0,
                "recommendation": rec,
                "reason": self._get_kuck_reason(page),
                "priority": self._get_kuck_priority(page),
                "traffic_potential": self._estimate_traffic_potential(page),
                "consolidate_with": None,
            }

            if rec == "keep":
                keep.append(page_data)
            elif rec == "update":
                update.append(page_data)
            elif rec == "consolidate":
                consolidate.append(page_data)
            elif rec == "kill":
                kill.append(page_data)
            else:
                keep.append(page_data)

        # Sort
        keep.sort(key=lambda x: -x["organic_traffic"])
        update.sort(key=lambda x: x["priority"])
        consolidate.sort(key=lambda x: x["priority"])
        kill.sort(key=lambda x: -x["decay_score"])

        content_audit_data = {
            "pages_analyzed": len(pages),
            "keep_count": len(keep),
            "update_count": len(update),
            "consolidate_count": len(consolidate),
            "kill_count": len(kill),
            "keep": keep[:50],
            "update": update[:50],
            "consolidate": consolidate[:50],
            "kill": kill[:50],
            "potential_traffic_recovery": sum(p["traffic_potential"] or 0 for p in update),
            "pages_to_consolidate": len(consolidate),
            "pages_to_remove": len(kill),
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "content-audit")
        self._cache.set_dashboard(domain_id, "content-audit", content_audit_data, analysis_id, etag)
        return True

    def _precompute_opportunities(
        self,
        domain_id: str,
        analysis_id: str,
        analysis,
    ) -> bool:
        """Precompute ranked opportunities."""
        from src.database.models import Keyword, KeywordGap, Page, SERPFeature

        limit = 20
        opportunities = []

        # Quick win keywords
        quick_wins = self.db.query(Keyword).filter(
            Keyword.analysis_run_id == analysis_id,
            Keyword.opportunity_score >= 70,
            Keyword.current_position.between(11, 30)
        ).order_by(desc(Keyword.opportunity_score)).limit(limit // 4).all()

        for kw in quick_wins:
            traffic_potential = self._estimate_traffic(5, kw.search_volume or 0) - (kw.estimated_traffic or 0)
            opportunities.append({
                "rank": 0,
                "opportunity_type": "keyword",
                "title": f"Push '{kw.keyword}' into top 10",
                "description": f"Currently ranking #{kw.current_position}. Optimize content to reach top 10.",
                "impact_score": kw.opportunity_score or 0,
                "effort": "low",
                "confidence": 0.8,
                "keywords": [kw.keyword],
                "target_url": kw.ranking_url,
                "estimated_traffic": traffic_potential,
                "time_to_impact": "short_term",
            })

        # Keyword gaps
        gaps = self.db.query(KeywordGap).filter(
            KeywordGap.analysis_run_id == analysis_id,
            KeywordGap.target_position == None,
            KeywordGap.search_volume >= 500
        ).order_by(desc(KeywordGap.opportunity_score)).limit(limit // 4).all()

        for gap in gaps:
            traffic_potential = self._estimate_traffic(5, gap.search_volume or 0)
            difficulty = gap.keyword_difficulty or 50
            opportunities.append({
                "rank": 0,
                "opportunity_type": "content",
                "title": f"Create content for '{gap.keyword}'",
                "description": f"Competitors rank for this {gap.search_volume:,} volume keyword. You don't.",
                "impact_score": gap.opportunity_score or 0,
                "effort": "medium" if difficulty < 50 else "high",
                "confidence": 0.7,
                "keywords": [gap.keyword],
                "target_url": None,
                "estimated_traffic": traffic_potential,
                "time_to_impact": "medium_term",
            })

        # Content to update
        update_pages = self.db.query(Page).filter(
            Page.analysis_run_id == analysis_id,
            Page.decay_score > 40,
            Page.organic_traffic > 100
        ).order_by(desc(Page.organic_traffic)).limit(limit // 4).all()

        for page in update_pages:
            recovery = int((page.organic_traffic or 0) * (page.decay_score or 0) / 100)
            opportunities.append({
                "rank": 0,
                "opportunity_type": "content",
                "title": f"Refresh: {page.title or page.url}",
                "description": f"Content decay detected. Update to recover {recovery:,} estimated traffic.",
                "impact_score": min(100, (page.decay_score or 0) + (page.organic_traffic or 0) / 100),
                "effort": "low",
                "confidence": 0.75,
                "keywords": None,
                "target_url": page.url,
                "estimated_traffic": recovery,
                "time_to_impact": "immediate",
            })

        # Sort by impact/effort
        effort_weights = {"low": 1, "medium": 2, "high": 3}
        opportunities.sort(
            key=lambda x: x["impact_score"] / effort_weights.get(x["effort"], 2),
            reverse=True
        )

        for i, opp in enumerate(opportunities[:limit]):
            opp["rank"] = i + 1

        opportunities_data = {
            "opportunities": opportunities[:limit],
            "total_traffic_potential": sum(o["estimated_traffic"] or 0 for o in opportunities[:limit]),
            "quick_wins_count": len([o for o in opportunities[:limit] if o["effort"] == "low"]),
            "precomputed_at": datetime.utcnow().isoformat(),
        }

        etag = generate_etag(analysis_id, "opportunities")
        self._cache.set_dashboard(domain_id, "opportunities", opportunities_data, analysis_id, etag)
        return True

    def _estimate_traffic(self, position: int, search_volume: int) -> int:
        """Estimate traffic from position and volume."""
        ctr_map = {
            1: 0.32, 2: 0.18, 3: 0.11, 4: 0.08, 5: 0.06,
            6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.02
        }
        if position <= 0:
            return 0
        elif position <= 10:
            ctr = ctr_map.get(position, 0.02)
        elif position <= 20:
            ctr = 0.01
        elif position <= 50:
            ctr = 0.005
        else:
            ctr = 0.001
        return int(search_volume * ctr)

    def _get_kuck_reason(self, page) -> str:
        """Generate reason for KUCK recommendation."""
        rec = (page.kuck_recommendation or "keep").lower()
        if rec == "keep":
            return f"Performing well with {page.organic_traffic or 0} monthly traffic"
        elif rec == "update":
            decay = page.decay_score or 0
            if decay > 50:
                return f"Content decay detected (score: {decay:.0f}). Refresh needed."
            else:
                return f"Good potential but underperforming. Freshness score: {page.freshness_score or 0:.0f}"
        elif rec == "consolidate":
            return "Similar content exists. Consider merging to strengthen authority."
        elif rec == "kill":
            return f"Low traffic ({page.organic_traffic or 0}), high decay ({page.decay_score or 0:.0f}). Remove or noindex."
        return "Needs review"

    def _get_kuck_priority(self, page) -> int:
        """Get KUCK priority 1-5."""
        traffic = page.organic_traffic or 0
        decay = page.decay_score or 0
        if traffic > 1000 and decay > 30:
            return 1
        elif traffic > 500:
            return 2
        elif traffic > 100:
            return 3
        elif traffic > 10:
            return 4
        return 5

    def _estimate_traffic_potential(self, page) -> int:
        """Estimate traffic potential if page is updated."""
        current = page.organic_traffic or 0
        decay = page.decay_score or 0
        recovery_multiplier = 1 + (decay / 100)
        return int(current * recovery_multiplier)


def trigger_precomputation(analysis_id: UUID, db: Session) -> Dict[str, Any]:
    """
    Trigger precomputation after analysis completes.

    This should be called from the analysis pipeline when an analysis
    transitions to COMPLETED status.
    """
    pipeline = PrecomputationPipeline(db)
    return pipeline.precompute_all(analysis_id)
