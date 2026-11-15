"""
app.py
======
Main entry point for AI Lead-Research and Outreach Copilot.

Stage 3 Milestone:
CLI interface connecting:
- Stage 1: Website Scraping
- Stage 2: Company Information Extraction
- Stage 3: AI Business Analysis (SalesFlow CRM Fit, Pain Points, Buying Triggers)
(Streamlit UI will be connected in Stage 7 as planned in the roadmap).
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website
from research.extractor import extract_company_info
from research.analyzer import analyze_company_crm_fit


def run_cli_copilot():
    print("\n" + "=" * 70)
    print("   AI Lead-Research & Outreach Copilot - Phase 3 Pipeline")
    print("=" * 70)
    
    while True:
        url_input = input("\nEnter company website URL (or 'q' to quit): ").strip()
        if not url_input or url_input.lower() == "q":
            print("\nExiting Copilot. See you in Phase 4!")
            break
            
        print(f"\n[Stage 1] Scraping & cleaning website: {url_input} ...")
        scraped_data = scrape_website(url_input)
        
        if scraped_data["status"] == "error":
            print(f"[-] Scraping Failed: {scraped_data['error_message']}")
            continue
            
        print(f"[+] Scraped {scraped_data['char_count']} clean characters. Title: '{scraped_data['title']}'")
        
        print("\n[Stage 2] Extracting structured company profile...")
        profile = extract_company_info(scraped_data)
        
        print("-" * 70)
        print(f"Company:        {profile['company_name'] or '[Unknown]'}")
        print(f"Industry:       {profile['industry'] or '[Unknown]'}")
        print(f"Business Model: {profile['business_model']}")
        print(f"Summary:        {profile['company_summary'] or '[No summary available]'}")
        print("-" * 70)
        
        # Save profile
        profile_file = Path("data") / "company_profile.json"
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"[Saved Stage 2 profile to: {profile_file}]")
        
        # Optional supplemental research for triggers
        print("\nOptional: Add supplemental research for buying triggers (e.g. news, hiring).")
        extra_research = input("Paste text or press ENTER to skip: ").strip()
        
        print("\n[Stage 3] Running AI Business Analysis against SalesFlow CRM...")
        analysis = analyze_company_crm_fit(
            profile,
            additional_research=extra_research if extra_research else None,
        )
        
        print("\n" + "=" * 70)
        print(" BUSINESS ANALYSIS & CRM FIT REPORT ")
        print("=" * 70)
        crm_rel = analysis.get("crm_relevance", {})
        print(f"CRM Relevance:  {crm_rel.get('classification', '').upper()}")
        print(f"Reasoning:      {crm_rel.get('reasoning')}")
        
        signals = crm_rel.get("icp_signals", {})
        print("\nICP Signals:")
        print(f"  • Geography Match:         {signals.get('geography_match')}")
        print(f"  • Industry Match:          {signals.get('industry_match')}")
        print(f"  • Company Size Match:      {signals.get('company_size_match')}")
        print(f"  • Sales Complexity Signal: {signals.get('sales_complexity_signal')}")
        
        print(f"\nPotential Pain Points ({len(analysis.get('potential_pain_points', []))}):")
        for idx, p in enumerate(analysis.get("potential_pain_points", []), 1):
            print(f"  {idx}. [{p.get('classification', 'hypothesis').upper()} | {p.get('confidence', '').upper()}] {p.get('problem')}")
            print(f"     Reasoning: {p.get('reasoning')}")
            
        triggers = analysis.get("buying_triggers", [])
        print(f"\nBuying Triggers ({len(triggers)}):")
        if triggers:
            for idx, t in enumerate(triggers, 1):
                print(f"  {idx}. [{t.get('trigger_type', '').upper()}] {t.get('description')} (Date: {t.get('observed_date') or 'Undated'})")
        else:
            print(f"  [None Identified] Reason: {analysis.get('no_trigger_reason')}")
            
        print(f"\nValue Hypotheses ({len(analysis.get('value_hypotheses', []))}):")
        for idx, v in enumerate(analysis.get("value_hypotheses", []), 1):
            print(f"  {idx}. Feature: {v.get('feature')} -> Benefit: {v.get('hypothesized_benefit')}")
            
        print(f"\nInformation Gaps ({len(analysis.get('information_gaps', []))}):")
        for idx, g in enumerate(analysis.get("information_gaps", []), 1):
            print(f"  {idx}. {g}")
        print("=" * 70)
        
        # Save analysis
        analysis_file = Path("data") / "business_analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"\n[Saved Stage 3 business analysis to: {analysis_file}]")


if __name__ == "__main__":
    run_cli_copilot()
