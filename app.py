"""
app.py
======
Main entry point for AI Lead-Research and Outreach Copilot.

Stage 2 Milestone:
CLI interface connecting Stage 1 (Website Scraping) to Stage 2 (Company Information Extraction).
(Streamlit UI will be connected in Stage 7 as planned in the roadmap).
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website
from research.extractor import extract_company_info


def run_cli_copilot():
    print("\n" + "=" * 65)
    print("   AI Lead-Research & Outreach Copilot - Stage 2 Pipeline")
    print("=" * 65)
    
    while True:
        url_input = input("\nEnter company website URL (or 'q' to quit): ").strip()
        if not url_input or url_input.lower() == "q":
            print("\nExiting Copilot. See you in Stage 3!")
            break
            
        print(f"\n[Stage 1] Scraping & cleaning website: {url_input} ...")
        scraped_data = scrape_website(url_input)
        
        if scraped_data["status"] == "error":
            print(f"[-] Scraping Failed: {scraped_data['error_message']}")
            continue
            
        print(f"[+] Scraped {scraped_data['char_count']} clean characters. Title: '{scraped_data['title']}'")
        
        print("\n[Stage 2] Extracting structured company profile...")
        profile = extract_company_info(scraped_data)
        
        print("\n" + "-" * 65)
        print(" EXTRACTED COMPANY PROFILE ")
        print("-" * 65)
        print(f"Extraction Status: {profile['extraction_status'].upper()}")
        print(f"Company Name:      {profile['company_name'] or '[Unknown]'}")
        print(f"Industry:          {profile['industry'] or '[Unknown]'}")
        print(f"Location:          {profile['location'] or '[Not Disclosed]'}")
        print(f"Business Model:    {profile['business_model']}")
        print(f"Company Size:      {profile['company_size'] or '[Not Disclosed]'}")
        print(f"\nSummary:\n  {profile['company_summary'] or '[No summary available]'}")
        
        if profile["products_services"]:
            print("\nProducts & Services:")
            for p in profile["products_services"]:
                print(f"  • {p}")
                
        if profile["target_customers"]:
            print("\nTarget Customers:")
            for c in profile["target_customers"]:
                print(f"  • {c}")
                
        if profile["verified_facts"]:
            print("\nVerified Facts (from website text):")
            for f in profile["verified_facts"]:
                print(f"  ✓ {f}")
                
        if profile["uncertain_information"]:
            print("\nUncertain Information (inferences/unverified):")
            for u in profile["uncertain_information"]:
                print(f"  ? {u}")
                
        if profile["extraction_notes"]:
            print(f"\nNotes: {profile['extraction_notes']}")
        print("-" * 65)
        
        # Save structured profile
        out_file = Path("data") / "company_profile.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"\n[Saved profile to: {out_file}]")


if __name__ == "__main__":
    run_cli_copilot()
