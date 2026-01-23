#!/usr/bin/env python3
"""
Full Analysis Runner

Runs a complete SEO analysis with:
1. Context Intelligence (business understanding)
2. Data Collection (DataForSEO)
3. AI Analysis (Claude)
4. Report Generation (PDF)
5. Email Delivery (Resend)

Usage:
    # Set environment variables first:
    export DATAFORSEO_LOGIN=your_login
    export DATAFORSEO_PASSWORD=your_password
    export ANTHROPIC_API_KEY=your_key
    export RESEND_API_KEY=your_key

    # Run analysis:
    python scripts/run_full_analysis.py bered.nu retzlik.a@gmail.com

    # With options:
    python scripts/run_full_analysis.py bered.nu retzlik.a@gmail.com \
        --market se \
        --goal balanced \
        --company "Bered"
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_full_analysis(
    domain: str,
    email: str,
    company_name: str = None,
    market: str = "se",
    goal: str = "balanced",
    skip_email: bool = False,
):
    """Run complete analysis pipeline."""

    load_dotenv()

    # Check required env vars
    dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
    dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    resend_key = os.getenv("RESEND_API_KEY")

    missing = []
    if not dataforseo_login:
        missing.append("DATAFORSEO_LOGIN")
    if not dataforseo_password:
        missing.append("DATAFORSEO_PASSWORD")
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if not resend_key and not skip_email:
        missing.append("RESEND_API_KEY (or use --skip-email)")

    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nSet them with:")
        print("  export DATAFORSEO_LOGIN=your_login")
        print("  export DATAFORSEO_PASSWORD=your_password")
        print("  export ANTHROPIC_API_KEY=your_key")
        print("  export RESEND_API_KEY=your_key")
        return

    print(f"\n{'='*70}")
    print(f"AUTHORICY SEO ANALYZER - FULL ANALYSIS")
    print(f"{'='*70}")
    print(f"Domain:       {domain}")
    print(f"Email:        {email}")
    print(f"Company:      {company_name or '(not specified)'}")
    print(f"Market:       {market}")
    print(f"Goal:         {goal}")
    print(f"Skip Email:   {skip_email}")
    print(f"{'='*70}\n")

    start_time = datetime.now()

    # Import here to avoid import errors if deps missing
    from src.collector import (
        DataForSEOClient,
        DataCollectionOrchestrator,
        CollectionConfig,
        compile_analysis_data,
    )
    from src.analyzer import AnalysisEngine
    from src.analyzer.client import ClaudeClient
    from src.reporter import ReportGenerator
    from src.delivery import EmailDelivery
    from src.context import PrimaryGoal, gather_context_intelligence
    from src.database import init_db

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init failed (continuing): {e}")

    # Map goal string to enum
    goal_map = {
        "traffic": PrimaryGoal.TRAFFIC,
        "leads": PrimaryGoal.LEADS,
        "authority": PrimaryGoal.AUTHORITY,
        "balanced": PrimaryGoal.BALANCED,
    }
    primary_goal = goal_map.get(goal.lower(), PrimaryGoal.BALANCED)

    # Market to language mapping (use full language names for DataForSEO Labs API)
    market_language = {
        "se": ("Sweden", "Swedish"),
        "us": ("United States", "English"),
        "uk": ("United Kingdom", "English"),
        "de": ("Germany", "German"),
        "no": ("Norway", "Norwegian"),
        "dk": ("Denmark", "Danish"),
        "fi": ("Finland", "Finnish"),
        "fr": ("France", "French"),
        "nl": ("Netherlands", "Dutch"),
    }
    market_name, language = market_language.get(market.lower(), ("Sweden", "Swedish"))

    context_result = None

    # =========================================================================
    # PHASE 0: Context Intelligence
    # =========================================================================
    print("\n" + "="*70)
    print("PHASE 0: Context Intelligence")
    print("="*70)

    try:
        claude_client = ClaudeClient(api_key=anthropic_key)

        context_result = await gather_context_intelligence(
            domain=domain,
            primary_market=market,
            primary_goal=primary_goal,
            primary_language=language,
            claude_client=claude_client,
        )

        print(f"✓ Website analyzed: {context_result.website_analysis.business_model.value if context_result.website_analysis else 'N/A'}")
        print(f"✓ Competitors discovered: {len(context_result.competitor_validation.discovered) if context_result.competitor_validation else 0}")
        print(f"✓ Market opportunities: {len(context_result.market_validation.discovered_opportunities) if context_result.market_validation else 0}")
        print(f"✓ Overall confidence: {context_result.overall_confidence:.1%}")

        if context_result.business_context and context_result.business_context.goal_validation:
            gv = context_result.business_context.goal_validation
            if not gv.goal_fits_business:
                print(f"⚠ Goal mismatch: '{goal}' may not fit. Suggested: {gv.suggested_goal.value if gv.suggested_goal else 'N/A'}")

    except Exception as e:
        logger.error(f"Context Intelligence failed: {e}")
        print(f"✗ Context Intelligence failed: {e}")
        print("  Continuing with basic analysis...")

    # =========================================================================
    # PHASE 1-4: Data Collection
    # =========================================================================
    print("\n" + "="*70)
    print("PHASES 1-4: Data Collection")
    print("="*70)

    async with DataForSEOClient(
        login=dataforseo_login,
        password=dataforseo_password
    ) as client:

        orchestrator = DataCollectionOrchestrator(client)

        result = await orchestrator.collect(CollectionConfig(
            domain=domain,
            market=market_name,
            language=language,
            brand_name=company_name or domain.split(".")[0],
        ))

        print(f"✓ Phase 1 (Foundation): Complete")
        print(f"✓ Phase 2 (Keywords): {len(result.ranked_keywords)} ranked keywords")
        print(f"✓ Phase 3 (Competitive): {len(result.competitors)} competitors")
        print(f"✓ Phase 4 (Technical): Complete")

        if result.errors:
            for err in result.errors[:3]:
                print(f"  ⚠ {err}")

        # Compile analysis data
        analysis_data = compile_analysis_data(result)

        # Add context intelligence to analysis data
        if context_result:
            analysis_data["context_intelligence"] = context_result.to_analysis_context()

    # =========================================================================
    # AI Analysis
    # =========================================================================
    print("\n" + "="*70)
    print("AI ANALYSIS")
    print("="*70)

    engine = AnalysisEngine(api_key=anthropic_key)

    analysis_result = await engine.analyze(
        analysis_data,
        skip_enrichment=False,
    )

    print(f"✓ Loop 1 (Data Interpretation): Complete")
    print(f"✓ Loop 2 (Strategic Synthesis): Complete")
    print(f"✓ Loop 3 (SERP Enrichment): Complete")
    print(f"✓ Loop 4 (Quality Review): Complete")
    print(f"✓ Quality Score: {analysis_result.quality_score}/10")
    print(f"✓ Total Cost: ${analysis_result.total_cost:.2f}")

    # =========================================================================
    # Report Generation
    # =========================================================================
    print("\n" + "="*70)
    print("REPORT GENERATION")
    print("="*70)

    generator = ReportGenerator()

    report_data = {
        "metadata": analysis_data.get("metadata", {}),
        "summary": analysis_data.get("summary", {}),
        "analysis": {
            "findings": analysis_result.loop1_findings,
            "strategy": analysis_result.loop2_strategy,
            "enrichment": analysis_result.loop3_enrichment,
            "executive_summary": analysis_result.executive_summary,
        },
        "context_intelligence": analysis_data.get("context_intelligence", {}),
    }

    pdf_bytes, pdf_filename = generator.generate(
        analysis_data=report_data,
        domain=domain,
        company_name=company_name,
    )

    print(f"✓ PDF Generated: {pdf_filename}")
    print(f"✓ Size: {len(pdf_bytes) / 1024:.1f} KB")

    # Save PDF locally
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / pdf_filename

    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"✓ Saved to: {pdf_path}")

    # =========================================================================
    # Email Delivery
    # =========================================================================
    if not skip_email:
        print("\n" + "="*70)
        print("EMAIL DELIVERY")
        print("="*70)

        delivery = EmailDelivery()

        email_result = await delivery.send_report(
            to_email=email,
            domain=domain,
            company_name=company_name or domain,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
        )

        if email_result.success:
            print(f"✓ Email sent to: {email}")
            print(f"✓ Message ID: {email_result.message_id}")
        else:
            print(f"✗ Email failed: {email_result.error}")
    else:
        print("\n(Email delivery skipped)")

    # =========================================================================
    # Summary
    # =========================================================================
    duration = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"Domain: {domain}")
    print(f"Report: {pdf_path}")
    print(f"Quality: {analysis_result.quality_score}/10")
    print(f"Cost: ${analysis_result.total_cost:.2f}")
    print("="*70 + "\n")

    return {
        "success": True,
        "pdf_path": str(pdf_path),
        "quality_score": analysis_result.quality_score,
        "cost": analysis_result.total_cost,
        "duration": duration,
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run full SEO analysis with report generation and email delivery"
    )
    parser.add_argument(
        "domain",
        help="Domain to analyze (e.g., bered.nu)"
    )
    parser.add_argument(
        "email",
        help="Email address to send report to"
    )
    parser.add_argument(
        "--company",
        default=None,
        help="Company name (optional)"
    )
    parser.add_argument(
        "--market",
        default="se",
        choices=["se", "us", "uk", "de", "no", "dk", "fi", "fr", "nl"],
        help="Target market (default: se)"
    )
    parser.add_argument(
        "--goal",
        default="balanced",
        choices=["traffic", "leads", "authority", "balanced"],
        help="Primary goal (default: balanced)"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip email delivery (just generate PDF)"
    )

    args = parser.parse_args()

    result = asyncio.run(run_full_analysis(
        domain=args.domain,
        email=args.email,
        company_name=args.company,
        market=args.market,
        goal=args.goal,
        skip_email=args.skip_email,
    ))

    if result:
        print(f"\nReport saved to: {result['pdf_path']}")


if __name__ == "__main__":
    main()
