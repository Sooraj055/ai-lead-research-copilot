"""
test_scraper.py
===============
Interactive and automated test runner for the website scraper module.

Usage:
    # Test with a specific URL:
    python test_scraper.py https://example.com

    # Run default test suite (tests valid, invalid, and edge-case URLs):
    python test_scraper.py
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website

def print_result(result: dict) -> None:
    print("\n" + "=" * 60)
    print(f"URL:             {result['url']}")
    print(f"Status:          {result['status'].upper()}")
    print(f"HTTP Code:       {result['http_status']}")
    print(f"Title:           {result['title']}")
    print(f"Meta Desc:       {result['meta_description'][:100]}..." if result['meta_description'] else "Meta Desc:       [None]")
    print(f"Extracted Chars: {result['char_count']}")
    
    if result["status"] == "error":
        print(f"Error Message:   {result['error_message']}")
    else:
        print("-" * 60)
        print("Text Preview (First 300 characters):")
        preview = result["clean_text"][:300].replace("\n", " ")
        print(f'"{preview}..."')
    print("=" * 60)

def main():
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        print(f"\n[Scraping single URL]: {target_url}")
        res = scrape_website(target_url)
        print_result(res)
        
        # Save output to data/ folder for inspection
        output_file = Path("data") / "sample_scrape.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"\nSaved structured output to: {output_file}")
    else:
        print("\n=== Running Scraper Test Suite ===")
        test_urls = [
            "https://example.com",                  # Simple, valid site
            "stripe.com",                           # Valid site without https:// prefix
            "https://this-is-a-fake-domain-123xyz456.com", # Non-existent domain (Connection error)
            "https://httpstat.us/404",              # 404 Not Found error
        ]
        
        for url in test_urls:
            print(f"\nTesting: {url}")
            res = scrape_website(url)
            print_result(res)

if __name__ == "__main__":
    main()
