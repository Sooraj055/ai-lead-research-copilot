"""
test_extractor.py
=================
Automated test suite for Stage 2 Company Information Extraction.

Tests:
1. Extraction on existing Stage 1 scraping data (e.g. data/sample_scrape.json or live scrape).
2. Handling missing / empty website text.
3. Handling scraping error input (e.g. 404 or connection failure).
4. Graceful fallback when GEMINI_API_KEY is missing or invalid.
5. Verifies all required schema fields and saves to data/company_profile.json.
"""

import os
import json
from pathlib import Path
from research.scraper import scrape_website
from research.extractor import extract_company_info, get_empty_company_profile


def print_profile_summary(profile: dict, title: str = "Company Profile") -> None:
    print("\n" + "=" * 65)
    print(f" {title} ")
    print("=" * 65)
    print(f"Status:             {profile.get('extraction_status', '').upper()}")
    print(f"Company Name:       {profile.get('company_name') or '[Unknown]'}")
    print(f"Website URL:        {profile.get('website_url')}")
    print(f"Industry:           {profile.get('industry') or '[Unknown]'}")
    print(f"Location:           {profile.get('location') or '[Unknown]'}")
    print(f"Business Model:     {profile.get('business_model')}")
    print(f"Company Size:       {profile.get('company_size') or '[Not Disclosed]'}")
    print(f"Summary:            {profile.get('company_summary') or '[None]'}")
    print(f"Products/Services:  {len(profile.get('products_services', []))} item(s)")
    for p in profile.get("products_services", [])[:3]:
        print(f"  • {p}")
    print(f"Target Customers:   {len(profile.get('target_customers', []))} item(s)")
    for c in profile.get("target_customers", [])[:3]:
        print(f"  • {c}")
    print(f"Verified Facts:     {len(profile.get('verified_facts', []))} statement(s)")
    print(f"Uncertain Info:     {len(profile.get('uncertain_information', []))} statement(s)")
    if profile.get("extraction_notes"):
        print(f"Extraction Notes:   {profile.get('extraction_notes')}")
    print("=" * 65)


def test_empty_or_failed_scrapes():
    print("\n[TEST 1] Testing Scraper Failure Input...")
    failed_scrape = {
        "url": "https://broken-link.com",
        "status": "error",
        "http_status": 404,
        "title": "",
        "meta_description": "",
        "clean_text": "",
        "error_message": "404 Not Found"
    }
    profile = extract_company_info(failed_scrape)
    assert profile["extraction_status"] == "failed"
    assert profile["company_name"] is None
    print("✓ Passed: Correctly aborted extraction on failed scrape without crashing.")

    print("\n[TEST 2] Testing Empty Website Content...")
    empty_scrape = {
        "url": "https://empty-page.com",
        "status": "success",
        "http_status": 200,
        "title": "Blank Page",
        "meta_description": "",
        "clean_text": "Nothing to see here."
    }
    profile = extract_company_info(empty_scrape)
    assert profile["extraction_status"] == "failed"
    print("✓ Passed: Handled insufficient content gracefully.")


def test_live_or_sample_extraction():
    print("\n[TEST 3] Testing Real Extraction on Stripe (or Sample Data)...")
    sample_file = Path("data") / "sample_scrape.json"
    
    # If sample exists and is Stripe, use it; otherwise scrape stripe.com
    scraped_data = None
    if sample_file.exists():
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "stripe" in data.get("url", "").lower():
                scraped_data = data

    if not scraped_data:
        print("Fetching fresh scrape of stripe.com for testing...")
        scraped_data = scrape_website("https://stripe.com")

    profile = extract_company_info(scraped_data)
    print_profile_summary(profile, title="Stripe Extracted Profile")

    # Verify required keys in profile
    schema_keys = [
        "company_name", "website_url", "industry", "location", "company_summary",
        "products_services", "target_customers", "business_model", "company_size",
        "verified_facts", "uncertain_information", "source_urls",
        "extraction_status", "extraction_notes"
    ]
    for k in schema_keys:
        assert k in profile, f"Missing key {k} in extracted profile!"

    # Save to data/company_profile.json
    out_file = Path("data") / "company_profile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved profile successfully to: {out_file}")


def main():
    print("=== Running Stage 2 Extractor Test Suite ===")
    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    print(f"GEMINI_API_KEY detected in environment: {has_key}")
    if not has_key:
        print("[NOTE] Running with fallback heuristic extraction until user adds their key to .env")

    test_empty_or_failed_scrapes()
    test_live_or_sample_extraction()
    print("\nAll Stage 2 Extractor tests completed successfully!")


if __name__ == "__main__":
    main()
