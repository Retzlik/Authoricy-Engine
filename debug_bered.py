"""
Debug script to investigate API data for bered.nu
"""

import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()


async def debug_bered():
    """Debug API responses for bered.nu"""
    from src.collector.client import DataForSEOClient

    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")

    if not login or not password:
        print("❌ Missing credentials")
        return

    async with DataForSEOClient(login=login, password=password) as client:

        # Test 1: Domain Rank Overview
        print("\n" + "="*60)
        print("TEST 1: Domain Rank Overview (Sweden/Swedish)")
        print("="*60)

        result = await client.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": "bered.nu",
                "location_name": "Sweden",
                "language_name": "Swedish"
            }]
        )

        print(f"Status code: {result.get('status_code')}")
        tasks = result.get("tasks", [])
        if tasks:
            task = tasks[0]
            print(f"Task status: {task.get('status_code')} - {task.get('status_message')}")
            task_result = task.get("result", [])
            if task_result:
                item = task_result[0]
                print(f"Result keys: {list(item.keys())}")
                metrics = item.get("metrics", {})
                if metrics:
                    print(f"Metrics keys: {list(metrics.keys())}")
                    organic = metrics.get("organic", {})
                    print(f"Organic data: {json.dumps(organic, indent=2)}")
                else:
                    print("NO METRICS FOUND!")
                    print(f"Full result item: {json.dumps(item, indent=2)[:1000]}")

        # Test 2: Ranked Keywords
        print("\n" + "="*60)
        print("TEST 2: Ranked Keywords (Sweden/Swedish)")
        print("="*60)

        result = await client.post(
            "dataforseo_labs/google/ranked_keywords/live",
            [{
                "target": "bered.nu",
                "location_name": "Sweden",
                "language_name": "Swedish",
                "limit": 1000
            }]
        )

        tasks = result.get("tasks", [])
        if tasks:
            task = tasks[0]
            print(f"Task status: {task.get('status_code')} - {task.get('status_message')}")
            task_result = task.get("result", [])
            if task_result:
                first = task_result[0]
                print(f"Total count: {first.get('total_count')}")
                print(f"Items count: {first.get('items_count')}")
                items = first.get("items", [])
                print(f"Returned items: {len(items)}")

                if items:
                    print("\nTop 5 keywords:")
                    for kw in items[:5]:
                        kw_data = kw.get("keyword_data", {})
                        kw_info = kw_data.get("keyword_info", {})
                        serp = (kw.get("ranked_serp_element") or {}).get("serp_item", {})
                        print(f"  - {kw_data.get('keyword')}: pos={serp.get('rank_group')}, vol={kw_info.get('search_volume')}")

        # Test 3: Try US/English to compare
        print("\n" + "="*60)
        print("TEST 3: Domain Rank Overview (United States/English)")
        print("="*60)

        result = await client.post(
            "dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": "bered.nu",
                "location_name": "United States",
                "language_name": "English"
            }]
        )

        tasks = result.get("tasks", [])
        if tasks:
            task = tasks[0]
            print(f"Task status: {task.get('status_code')} - {task.get('status_message')}")
            task_result = task.get("result", [])
            if task_result:
                item = task_result[0]
                metrics = item.get("metrics", {})
                if metrics:
                    organic = metrics.get("organic", {})
                    print(f"Organic data (US): {json.dumps(organic, indent=2)}")
                else:
                    print("NO METRICS FOUND for US either!")

        # Test 4: Competitors
        print("\n" + "="*60)
        print("TEST 4: Competitors Domain (Sweden/Swedish)")
        print("="*60)

        result = await client.post(
            "dataforseo_labs/google/competitors_domain/live",
            [{
                "target": "bered.nu",
                "location_name": "Sweden",
                "language_name": "Swedish",
                "limit": 20
            }]
        )

        tasks = result.get("tasks", [])
        if tasks:
            task = tasks[0]
            task_result = task.get("result", [])
            if task_result:
                first = task_result[0]
                items = first.get("items", [])
                print(f"Found {len(items)} competitors")
                for comp in items[:10]:
                    print(f"  - {comp.get('domain')}: traffic={comp.get('metrics', {}).get('organic', {}).get('etv', 0)}")


if __name__ == "__main__":
    asyncio.run(debug_bered())
