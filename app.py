"""
app.py
======
Main entry point for AI Lead-Research and Outreach Copilot.

Stage 4 Milestone:
CLI interface connecting:
- Stage 1: Website Scraping
- Stage 2: Company Information Extraction
- Stage 3: AI Business Analysis (SalesFlow CRM Fit, Pain Points, Buying Triggers)
- Stage 4: Deterministic Lead Scoring & Priority Classification
(Streamlit UI will be connected in Stage 7 as planned in the roadmap).
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website
from research.extractor import extract_company_info
from research.analyzer import analyze_company_crm_fit
from research.scorer import score_lead


def run_cli_copilot():
    print("\n" + "=" * 70)
    print("   AI Lead-Research & Outreach Copilot - Phase 4 Pipeline")
    print("=" * 70)
    
    while True:
        url_input = input("\nEnter company website URL (or 'q' to quit): ").strip()
        if not url_input or url_input.lower() == "q":
            print("\nExiting Copilot. See you in Phase 5!")
            break
            
        # STAGE 1: SCRAPING
        print(f"\n[Stage 1] Scraping & cleaning website: {url_input} ...")
        scraped_data = scrape_website(url_input)
        
        if scraped_data["status"] == "error":
            print(f"[-] Scraping Failed: {scraped_data['error_message']}")
            continue
            
        print(f"[+] Scraped {scraped_data['char_count']} clean characters. Title: '{scraped_data['title']}'")
        
        # STAGE 2: EXTRACTION
        print("\n[Stage 2] Extracting structured company profile...")
        profile = extract_company_info(scraped_data)
        
        print("-" * 70)
        print(f"Company:        {profile['company_name'] or '[Unknown]'}")
        print(f"Industry:       {profile['industry'] or '[Unknown]'}")
        print(f"Business Model: {profile['business_model']}")
        print(f"Summary:        {profile['company_summary'] or '[No summary available]'}")
        print("-" * 70)
        
        profile_file = Path("data") / "company_profile.json"
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"[Saved Stage 2 profile to: {profile_file}]")
        
        # STAGE 3: BUSINESS ANALYSIS
        print("\nOptional: Add supplemental research for buying triggers (e.g. news, hiring).")
        extra_research = input("Paste text or press ENTER to skip: ").strip()
        
        print("\n[Stage 3] Running AI Business Analysis against SalesFlow CRM...")
        analysis = analyze_company_crm_fit(
            profile,
            additional_research=extra_research if extra_research else None,
        )
        
        crm_rel = analysis.get("crm_relevance", {})
        print("-" * 70)
        print(f"CRM Fit:        {crm_rel.get('classification', '').upper()}")
        print(f"Reasoning:      {crm_rel.get('reasoning')}")
        print("-" * 70)
        
        analysis_file = Path("data") / "business_analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[Saved Stage 3 business analysis to: {analysis_file}]")
        
        # STAGE 4: LEAD SCORING
        print("\n[Stage 4] Calculating Deterministic ICP Lead Score...")
        score_data = score_lead(analysis)
        
        print("\n" + "=" * 70)
        print(" LEAD SCORE & PRIORITY CARD ")
        print("=" * 70)
        print(f"Total Score:      {score_data['total_score']} / {score_data['max_score']} Points")
        print(f"Priority Tier:    {score_data['priority'].upper()}")
        print(f"Confidence:       {score_data['confidence_level'].upper()}")
        print(f"Recommendation:   {score_data['summary_recommendation']}")
        
        print("\nRubric Breakdown:")
        for criterion, details in score_data.get("scoring_breakdown", {}).items():
            print(f"  • {criterion.replace('_', ' ').title():<22}: {details['score']:>2}/{details['max']} pts ({details['signal']}) - {details['reasoning']}")
        print("=" * 70)
        
        score_file = Path("data") / "lead_score.json"
        with open(score_file, "w", encoding="utf-8") as f:
            json.dump(score_data, f, indent=2, ensure_ascii=False)
        print(f"\n[Saved Stage 4 lead score to: {score_file}]")


if __name__ == "__main__":
    run_cli_copilot()
