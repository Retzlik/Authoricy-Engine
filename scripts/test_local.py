#!/usr/bin/env python3
"""
Local Test Script

Run a full analysis locally for testing purposes.

Usage:
    python scripts/test_local.py example.com
    python scripts/test_local.py example.com --market "United States" --language en
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.collector import (
    DataForSEOClient,
    DataCollectionOrchestrator,
    CollectionConfig,
    compile_analysis_data,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )


async def run_test(
    domain: str,
    market: str,
    language: str,
    skip_ai: bool,
    output_file: str = None,
):
    """Run full analysis test."""
    
    load_dotenv()
    
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    
    if not login or not password:
        print("ERROR: Missing DATAFORSEO_LOGIN or DATAFORSEO_PASSWORD in .env")
        print("\nCreate a .env file with:")
        print("  DATAFORSEO_LOGIN=your_login")
        print("  DATAFORSEO_PASSWORD=your_password")
        return
    
    print(f"\n{'='*60}")
    print(f"AUTHORICY SEO ANALYZER - LOCAL TEST")
    print(f"{'='*60}")
    print(f"Domain: {domain}")
    print(f"Market: {market}")
    print(f"Language: {language}")
    print(f"Skip AI Analysis: {skip_ai}")
    print(f"{'='*60}\n")
    
    start_time = datetime.now()
    
    async with DataForSEOClient(login=login, password=password) as client:
        
        orchestrator = DataCollectionOrchestrator(client)
        
        result = await orchestrator.collect(CollectionConfig(
            domain=domain,
            market=market,
            language=language,
            skip_ai_analysis=skip_ai,
        ))
        
        # Compile results
        analysis_data = compile_analysis_data(result)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Success: {result.success}")
    print(f"Early Terminated: {result.early_terminated}")
    
    if result.errors:
        print(f"\nErrors:")
        for err in result.errors:
            print(f"  - {err}")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warn in result.warnings:
            print(f"  - {warn}")
    
    # Print summary metrics
    summary = analysis_data.get("summary", {})
    print(f"\n{'='*60}")
    print(f"SUMMARY METRICS")
    print(f"{'='*60}")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Print Phase 2 highlights
    phase2 = analysis_data.get("keywords", {})
    if phase2:
        print(f"\n{'='*60}")
        print(f"KEYWORD HIGHLIGHTS")
        print(f"{'='*60}")
        
        ranked = phase2.get("ranked_keywords", [])
        print(f"\nTop 10 Ranked Keywords:")
        for kw in ranked[:10]:
            print(f"  #{kw.get('position', '?'):3d} | {kw.get('keyword', '')[:40]:40s} | vol: {kw.get('search_volume', 0):,}")
        
        gaps = phase2.get("keyword_gaps", [])
        print(f"\nTop 10 Keyword Gaps (Opportunities):")
        for gap in gaps[:10]:
            print(f"  {gap.get('keyword', '')[:40]:40s} | vol: {gap.get('search_volume', 0):,} | opp: {gap.get('opportunity_score', 0):.0f}")
    
    # Print Phase 3 highlights
    phase3 = analysis_data.get("competitive", {})
    if phase3:
        print(f"\n{'='*60}")
        print(f"COMPETITIVE HIGHLIGHTS")
        print(f"{'='*60}")
        
        competitors = phase3.get("competitor_metrics", [])
        print(f"\nCompetitor Metrics:")
        for comp in competitors[:5]:
            print(f"  {comp.get('domain', '')[:30]:30s} | traffic: {comp.get('organic_traffic', 0):,} | keywords: {comp.get('organic_keywords', 0):,}")
        
        print(f"\nBacklink Profile:")
        print(f"  Total Backlinks: {phase3.get('total_backlinks', 0):,}")
        print(f"  Referring Domains: {phase3.get('total_referring_domains', 0):,}")
        print(f"  Dofollow %: {phase3.get('dofollow_percentage', 0)}%")
    
    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(analysis_data, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"Results saved to: {output_path}")
        print(f"{'='*60}")
    
    return analysis_data


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run SEO analysis locally for testing"
    )
    parser.add_argument(
        "domain",
        help="Domain to analyze (e.g., example.com)"
    )
    parser.add_argument(
        "--market",
        default="Sweden",
        help="Target market (default: Sweden)"
    )
    parser.add_argument(
        "--language",
        default="sv",
        help="Language code (default: sv)"
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI visibility analysis (faster)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    asyncio.run(run_test(
        domain=args.domain,
        market=args.market,
        language=args.language,
        skip_ai=args.skip_ai,
        output_file=args.output,
    ))


if __name__ == "__main__":
    main()
