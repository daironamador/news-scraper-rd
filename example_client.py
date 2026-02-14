"""
Example client for the News Scraper RD API.
Requires the API to be running: python -m uvicorn api.main:app --reload
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def start_scraping(spider_name):
    """Starts a scraping job"""
    print(f"\nStarting scraping with spider: {spider_name}")
    response = requests.post(f"{BASE_URL}/scrape", json={"spider_name": spider_name})

    if response.status_code == 200:
        data = response.json()
        print(f"  Job ID: {data['job_id']}")
        return data['job_id']
    else:
        print(f"  Error: {response.text}")
        return None


def wait_for_completion(job_id, max_wait=600):
    """Waits for a job to complete"""
    print(f"Waiting for job {job_id} completion...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if response.status_code == 200:
            status = response.json()
            if status['status'] == 'completed':
                print(f"  Completed: {status.get('total_items', 0)} news items")
                return True
            elif status['status'] == 'failed':
                print(f"  Failed: {status.get('error', 'Unknown error')}")
                return False
        time.sleep(10)

    print("  Wait time exceeded")
    return False


def get_categories():
    """Lists available categories"""
    print("\nCategories:")
    response = requests.get(f"{BASE_URL}/news/categories")
    if response.status_code == 200:
        for cat in response.json():
            print(f"  {cat['category']:30s} {cat['count']:4d} articles")


def get_sources():
    """Lists available sources"""
    print("\nSources:")
    response = requests.get(f"{BASE_URL}/news/sources")
    if response.status_code == 200:
        for src in response.json():
            print(f"  {src['source']:30s} {src['count']:4d} articles")


def filter_news(category=None, source=None, date_from=None, date_to=None, limit=5):
    """Filters news"""
    params = {"limit": limit}
    if category:
        params["category"] = category
    if source:
        params["source"] = source
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    print(f"\nFiltering news: {params}")
    response = requests.get(f"{BASE_URL}/news/filter", params=params)

    if response.status_code == 200:
        news = response.json()
        print(f"  Found: {len(news)} news items\n")
        for i, article in enumerate(news[:5], 1):
            print(f"  {i}. {article.get('title', 'No title')}")
            print(f"     Source: {article.get('source')} | Category: {article.get('category')}")
            print(f"     Date: {article.get('published_date', 'N/A')}")
            print()
        return news
    else:
        print(f"  Error: {response.text}")
        return []


def list_spiders():
    """Lists available spiders"""
    print("\nAvailable spiders:")
    response = requests.get(f"{BASE_URL}/spiders")
    if response.status_code == 200:
        for spider in response.json().get('spiders', []):
            print(f"  - {spider}")


def main():
    print("=" * 50)
    print("  News Scraper RD API - Example Client")
    print("=" * 50)

    # List spiders
    list_spiders()

    # View sources and categories
    get_sources()
    get_categories()

    # Filter by category
    filter_news(category="deportes", limit=3)

    # Filter by source and date
    filter_news(source="Diario Libre", date_from="2026-02-11", limit=3)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\nError: Cannot connect to API")
        print("Ensure the API is running: python -m uvicorn api.main:app --reload")
