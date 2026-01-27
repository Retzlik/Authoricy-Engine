"""
Simple Test Script for Authoricy Analyzer

Tests the basic data collection functionality.
Run: python3 test_system.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_basic_collection():
    """Test basic data collection with Phase 1 only."""
    
    # Import after loading env
    from src.collector.client import DataForSEOClient
    from src.collector.orchestrator import DataCollectionOrchestrator, CollectionConfig
    
    # Get credentials from environment
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    
    if not login or not password:
        print("❌ Error: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set in .env")
        return
    
    print(f"✅ Credentials loaded: {login[:3]}***")
    
    # Create client
    client = DataForSEOClient(
        login=login,
        password=password
    )
    
    # Create orchestrator
    orchestrator = DataCollectionOrchestrator(client)
    
    # Create config - only Phase 1 for testing
    config = CollectionConfig(
        domain="apple.com",
        market="Sweden",
        language="sv",
        skip_phases=[2, 3, 4]  # Skip all phases except Phase 1
    )

    print("🚀 Starting data collection for apple.com...")
    print("   (Only Phase 1 - Foundation data)")

    try:
        result = await orchestrator.collect_all(config)

        print("\n✅ Collection successful!")
        print(f"   Domain: {result.domain}")
        print(f"   Timestamp: {result.timestamp}")
        
        # Display Phase 1 results
        if result.domain_overview:
            print(f"\n📊 Domain Overview:")
            print(f"   Organic Keywords: {result.domain_overview.get('organic_keywords', 'N/A')}")
            print(f"   Organic Traffic: {result.domain_overview.get('organic_traffic', 'N/A')}")
            print(f"   Keywords in Position 1: {result.domain_overview.get('keywords_position_1', 'N/A')}")

        if result.backlink_summary:
            print(f"\n🔗 Backlink Summary:")
            print(f"   Domain Rating (DR): {result.backlink_summary.get('domain_rank', 'N/A')}")
            print(f"   Total Backlinks: {result.backlink_summary.get('total_backlinks', 'N/A')}")
            print(f"   Referring Domains: {result.backlink_summary.get('referring_domains', 'N/A')}")
        
        if result.competitors:
            print(f"\n🏆 Top Competitors:")
            for comp in result.competitors[:3]:
                print(f"   - {comp.get('domain', 'Unknown')}")
        
        if result.technologies:
            print(f"\n⚙️ Technologies Detected: {len(result.technologies)}")
            for tech in result.technologies[:5]:
                print(f"   - {tech.get('name', 'Unknown')} ({tech.get('category', '')})")

    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_basic_collection())
