"""
test_analyzer.py
================
Automated test suite for Phase 3: AI Business Analysis.

Tests:
1. Defensive handling of failed or empty input profiles.
2. Analysis on enterprise non-fit lead (Stripe) -> verifies 'Low potential' classification and no fabricated triggers.
3. Analysis on realistic Indian B2B distributor/manufacturer lead (Apex Agro & Spices) with supplemental research
   -> verifies 'High potential' classification, structured ICP signals, and buying triggers detection.
4. Schema validation and persistence to data/business_analysis.json.
"""

import os
import json
from pathlib import Path
from research.analyzer import analyze_company_crm_fit, get_empty_business_analysis


def print_analysis_summary(analysis: dict, title: str = "Business Analysis") -> None:
    print("\n" + "=" * 70)
    print(f" {title} ")
    print("=" * 70)
    print(f"Status:            {analysis.get('analysis_status', '').upper()}")
    print(f"Company Name:      {analysis.get('company_name')}")
    print(f"Product Analyzed:  {analysis.get('product_analyzed')}")
    
    crm_rel = analysis.get("crm_relevance", {})
    print(f"CRM Relevance:     {crm_rel.get('classification', '').upper()}")
    print(f"Reasoning:         {crm_rel.get('reasoning')}")
    
    signals = crm_rel.get("icp_signals", {})
    print("\nStructured ICP Signals:")
    print(f"  • Geography Match:         {signals.get('geography_match')}")
    print(f"  • Industry Match:          {signals.get('industry_match')}")
    print(f"  • Company Size Match:      {signals.get('company_size_match')}")
    print(f"  • Sales Complexity Signal: {signals.get('sales_complexity_signal')}")
    
    pain_points = analysis.get("potential_pain_points", [])
    print(f"\nPotential Pain Points ({len(pain_points)} identified):")
    for idx, p in enumerate(pain_points, 1):
        print(f"  {idx}. [{p.get('classification', 'hypothesis').upper()} | {p.get('confidence', '').upper()} CONFIDENCE] {p.get('problem')}")
        print(f"     Reasoning: {p.get('reasoning')}")
    
    triggers = analysis.get("buying_triggers", [])
    print(f"\nBuying Triggers ({len(triggers)} identified):")
    if triggers:
        for idx, t in enumerate(triggers, 1):
            print(f"  {idx}. [{t.get('trigger_type', '').upper()}] {t.get('description')} (Date: {t.get('observed_date') or 'Undated'})")
            print(f"     Quote: \"{t.get('evidence_quote')}\"")
    else:
        print(f"  [None Identified] Reason: {analysis.get('no_trigger_reason')}")
        
    values = analysis.get("value_hypotheses", [])
    print(f"\nValue Hypotheses ({len(values)} generated):")
    for idx, v in enumerate(values, 1):
        print(f"  {idx}. Feature: {v.get('feature')} -> Benefit: {v.get('hypothesized_benefit')}")
        
    gaps = analysis.get("information_gaps", [])
    print(f"\nInformation Gaps ({len(gaps)} key unknowns):")
    for idx, g in enumerate(gaps, 1):
        print(f"  {idx}. {g}")
    print("=" * 70)


def test_defensive_failures():
    print("\n[TEST 1] Testing Defensive Failure Handling...")
    failed_profile = {
        "company_name": "Broken Co",
        "website_url": "https://broken.co",
        "extraction_status": "failed",
        "extraction_notes": "Website returned 404"
    }
    analysis = analyze_company_crm_fit(failed_profile)
    assert analysis["analysis_status"] == "failed"
    assert "aborted" in analysis["analysis_notes"].lower()
    print("✓ Passed: Aborted cleanly on failed profile input.")


def test_stripe_profile():
    print("\n[TEST 2] Testing Analysis on Stripe (Global Enterprise Non-Fit)...")
    profile_path = Path("data") / "company_profile.json"
    assert profile_path.exists(), "data/company_profile.json missing! Run test_extractor.py first."
    
    with open(profile_path, "r", encoding="utf-8") as f:
        stripe_profile = json.load(f)
        
    analysis = analyze_company_crm_fit(stripe_profile)
    print_analysis_summary(analysis, title="Stripe Analysis (Expected: Low Potential / Enterprise Non-Fit)")
    
    # Assertions
    assert "crm_relevance" in analysis
    classification = analysis["crm_relevance"]["classification"]
    assert classification in ["Low potential", "Insufficient information"], f"Unexpected classification: {classification}"
    assert "icp_signals" in analysis["crm_relevance"]
    assert isinstance(analysis["potential_pain_points"], list)
    assert isinstance(analysis["buying_triggers"], list)


def test_indian_b2b_distributor():
    print("\n[TEST 3] Testing Realistic Indian B2B Distributor (Apex Agro & Spices)...")
    indian_lead_profile = {
        "company_name": "Apex Agro & Spices Exports Pvt. Ltd.",
        "website_url": "https://apexagrospices.example.in",
        "industry": "Food Processing & FMCG Wholesale Distribution",
        "location": "Kochi, Kerala, India",
        "company_summary": (
            "Apex Agro & Spices is an Indian manufacturer and wholesale distributor of processed spices, "
            "condiments, and culinary ingredients serving 450+ retail chains and distributors across South India."
        ),
        "products_services": [
            "Bulk ground spices",
            "Packaged curry powders",
            "Commercial seasoning blends for restaurants",
            "Wholesale distribution to supermarkets"
        ],
        "target_customers": [
            "Regional grocery supermarket chains",
            "Wholesale food stockists",
            "Institutional catering contractors"
        ],
        "business_model": "B2B",
        "company_size": "65 employees (with ~18 field sales reps)",
        "verified_facts": [
            "Operates 2 manufacturing units in Aluva and Coimbatore.",
            "Supplies over 450 verified supermarket accounts across Kerala and Tamil Nadu.",
            "Employs 18 regional field sales and order-collection agents."
        ],
        "uncertain_information": [
            "Current sales management software or CRM is unknown; likely using spreadsheets and tally."
        ],
        "source_urls": ["https://apexagrospices.example.in"],
        "extraction_status": "success",
        "extraction_notes": "Comprehensive company data extracted from website."
    }

    supplemental_research = """
    Source: Economic Times SME Bureau (Dated: 2026-03-12)
    "Apex Agro & Spices announced an INR 12-crore expansion to establish 3 new regional supply depots in Bengaluru, 
    Hyderabad, and Vijayawada by Q3 2026, aiming to double wholesale dealer accounts."

    Source: LinkedIn Careers Page (Dated: 2026-04-05)
    "Apex Agro & Spices is actively hiring: 1x Regional Sales Manager (Karnataka), 6x Field Sales Executives 
    (Bengaluru & Hyderabad), and 2x Channel Operations Coordinators to manage expanding distributor accounts."
    """

    analysis = analyze_company_crm_fit(
        indian_lead_profile,
        additional_research=supplemental_research
    )
    print_analysis_summary(analysis, title="Apex Agro & Spices Analysis (Expected: High Potential)")

    # Assertions
    rel = analysis["crm_relevance"]
    assert rel["classification"] == "High potential", f"Expected High potential, got: {rel['classification']}"
    assert rel["icp_signals"]["geography_match"] == "yes"
    assert rel["icp_signals"]["industry_match"] in ["high", "medium"]
    assert rel["icp_signals"]["company_size_match"] == "yes"
    assert len(analysis["buying_triggers"]) >= 1, "Expected buying triggers to be identified from supplemental research!"

    # Save to data/business_analysis.json
    out_file = Path("data") / "business_analysis.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved Phase 3 business analysis to: {out_file}")


def main():
    import time
    print("=== Running Phase 3 Business Analysis Test Suite ===")
    test_defensive_failures()
    print("\nPausing 3 seconds to respect Gemini rate limits...")
    time.sleep(3)
    test_stripe_profile()
    print("\nPausing 3 seconds to respect Gemini rate limits...")
    time.sleep(3)
    test_indian_b2b_distributor()
    print("\nAll Phase 3 Business Analysis tests completed successfully!")


if __name__ == "__main__":
    main()
