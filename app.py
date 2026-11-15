"""
app.py
======
Main entry point for AI Lead-Research and Outreach Copilot.

Stage 6 Milestone:
Full end-to-end CLI pipeline with Human-in-the-Loop review and CRM Sync:
- Stage 1: Website Scraping
- Stage 2: Company Information Extraction
- Stage 3: AI Business Analysis (SalesFlow CRM Fit, Pain Points, Buying Triggers)
- Stage 4: Deterministic Lead Scoring & Priority Classification
- Stage 5: Personalised Outreach Drafting (Human Review Pending)
- Stage 6: Human Approval Gate & HubSpot CRM Sync (with Dry-Run Fallback)
(Streamlit UI will be connected in Stage 7 as planned in the roadmap).
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website
from research.extractor import extract_company_info
from research.analyzer import analyze_company_crm_fit
from research.scorer import score_lead
from research.outreach import generate_outreach_drafts
from research.crm_sync import review_outreach_draft, sync_lead_to_crm


def run_cli_copilot():
    print("\n" + "=" * 75)
    print("   AI Lead-Research & Outreach Copilot - End-to-End Pipeline (Stages 1-6)")
    print("=" * 75)
    
    while True:
        url_input = input("\nEnter company website URL (or 'q' to quit): ").strip()
        if not url_input or url_input.lower() == "q":
            print("\nExiting Copilot. See you in Phase 7!")
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
        
        print("-" * 75)
        print(f"Company:        {profile['company_name'] or '[Unknown]'}")
        print(f"Industry:       {profile['industry'] or '[Unknown]'}")
        print(f"Business Model: {profile['business_model']}")
        print(f"Summary:        {profile['company_summary'] or '[No summary available]'}")
        print("-" * 75)
        
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
        print("-" * 75)
        print(f"CRM Fit:        {crm_rel.get('classification', '').upper()}")
        print(f"Reasoning:      {crm_rel.get('reasoning')}")
        print("-" * 75)
        
        analysis_file = Path("data") / "business_analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[Saved Stage 3 business analysis to: {analysis_file}]")
        
        # STAGE 4: LEAD SCORING
        print("\n[Stage 4] Calculating Deterministic ICP Lead Score...")
        score_data = score_lead(analysis)
        
        print("-" * 75)
        print(f"Lead Score:     {score_data['total_score']} / {score_data['max_score']} Points")
        print(f"Priority Tier:  {score_data['priority'].upper()}")
        print(f"Confidence:     {score_data['confidence_level'].upper()}")
        print(f"Recommendation: {score_data['summary_recommendation']}")
        print("-" * 75)
        
        score_file = Path("data") / "lead_score.json"
        with open(score_file, "w", encoding="utf-8") as f:
            json.dump(score_data, f, indent=2, ensure_ascii=False)
        print(f"[Saved Stage 4 lead score to: {score_file}]")
        
        # STAGE 5: OUTREACH DRAFTING
        print("\n[Stage 5] Generating Personalized Outreach Drafts...")
        outreach_data = generate_outreach_drafts(profile, analysis, score_data)
        
        print("\n" + "=" * 75)
        print(" PERSONALISED OUTREACH DRAFTS (HUMAN REVIEW REQUIRED) ")
        print("=" * 75)
        
        if outreach_data["generation_status"] == "skipped_low_priority":
            print(f"Note: {outreach_data['generation_notes']}")
        else:
            drafts = outreach_data.get("drafts", {})
            ea = drafts.get("email_variant_a", {})
            eb = drafts.get("email_variant_b", {})
            la = drafts.get("linkedin_variant_a", {})
            lb = drafts.get("linkedin_variant_b", {})
            
            print(f"\n[1] EMAIL VARIANT A (Direct): \"{ea.get('subject_line')}\"")
            print("    " + ea.get("body_text", "").replace("\n", "\n    "))
            
            print(f"\n[2] EMAIL VARIANT B (Consultative): \"{eb.get('subject_line')}\"")
            print("    " + eb.get("body_text", "").replace("\n", "\n    "))
            
            print(f"\n[3] LINKEDIN CONNECTION NOTE ({la.get('character_count')}/300 chars):")
            print(f"    \"{la.get('message_text')}\"")
            
            print(f"\n[4] LINKEDIN INMAIL MESSAGE ({lb.get('word_count')} words):")
            print("    " + lb.get("message_text", "").replace("\n", "\n    "))
            print("=" * 75)
            
            # STAGE 6: HUMAN APPROVAL & CRM SYNC
            print("\n[Stage 6] HUMAN APPROVAL GATE - Action Required:")
            print("  1. Approve Email Variant A")
            print("  2. Approve Email Variant B")
            print("  3. Approve LinkedIn Connection Note")
            print("  4. Approve LinkedIn InMail")
            print("  5. Edit Copy & Approve")
            print("  6. Reject Lead (Blocks CRM Sync)")
            print("  7. Save for Later (Defers Sync)")
            
            choice = input("\nEnter your decision (1-7): ").strip()
            
            var_map = {
                "1": ("approve", "email_variant_a"),
                "2": ("approve", "email_variant_b"),
                "3": ("approve", "linkedin_variant_a"),
                "4": ("approve", "linkedin_variant_b"),
            }
            
            if choice in var_map:
                dec, var_name = var_map[choice]
                reviewed_outreach = review_outreach_draft(
                    outreach_data, decision=dec, selected_variant=var_name, reviewer_name="Sales Rep (CLI User)"
                )
            elif choice == "5":
                edited_copy = input("\nPaste your customized outreach copy: ").strip()
                reviewed_outreach = review_outreach_draft(
                    outreach_data, decision="edit", selected_variant="custom", custom_text=edited_copy, reviewer_name="Sales Rep (CLI User)"
                )
            elif choice == "6":
                reason = input("Enter rejection reason (e.g. competitor, duplicate): ").strip()
                reviewed_outreach = review_outreach_draft(
                    outreach_data, decision="reject", reviewer_name="Sales Rep (CLI User)", notes=reason
                )
            else:
                reviewed_outreach = review_outreach_draft(
                    outreach_data, decision="save_for_later", reviewer_name="Sales Rep (CLI User)"
                )
                
            outreach_file = Path("data") / "outreach_drafts.json"
            with open(outreach_file, "w", encoding="utf-8") as f:
                json.dump(reviewed_outreach, f, indent=2, ensure_ascii=False)
            print(f"[Saved reviewed outreach to: {outreach_file}]")
            
            print("\n[Stage 6] Executing CRM Synchronization...")
            sync_log = sync_lead_to_crm(profile, analysis, score_data, reviewed_outreach)
            
            print("-" * 75)
            print(f"CRM Sync Status:   {sync_log['sync_status'].upper()}")
            print(f"Sync Mode:         {sync_log['sync_mode'].upper()}")
            print(f"Action Taken:      {sync_log['action_taken']}")
            print(f"HubSpot ID:        {sync_log['hubspot_company_id'] or '[None]'}")
            print(f"Notes:             {sync_log['sync_notes']}")
            print("-" * 75)
            
            crm_log_file = Path("data") / "crm_sync_log.json"
            with open(crm_log_file, "w", encoding="utf-8") as f:
                json.dump(sync_log, f, indent=2, ensure_ascii=False)
            print(f"[Saved CRM sync log to: {crm_log_file}]")


if __name__ == "__main__":
    run_cli_copilot()
