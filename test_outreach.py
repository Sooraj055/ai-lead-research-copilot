"""
test_outreach.py
================
Automated test suite for Phase 5: Personalised Outreach Generation.

Tests:
1. Low-Priority Token Safeguard:
   Verifies that outreach drafting is cleanly skipped ('skipped_low_priority') for disqualified
   enterprise leads (Stripe), saving LLM tokens.
2. Grounded Outreach Generation:
   Verifies that an ideal Indian B2B lead (Apex Agro & Spices) generates four anti-fluff variants,
   cites observable evidence, enforces the <= 300 character limit on the LinkedIn connection note,
   and initializes human review status to 'pending_human_review'.
3. Persistence:
   Saves the resulting drafts to data/outreach_drafts.json.
"""

import json
from pathlib import Path
from research.outreach import generate_outreach_drafts


def print_drafts_card(outreach_data: dict, title: str = "Outreach Drafts Report") -> None:
    print("\n" + "=" * 70)
    print(f" {title} ")
    print("=" * 70)
    print(f"Company:          {outreach_data.get('company_name')}")
    print(f"Priority:         {outreach_data.get('lead_priority')} ({outreach_data.get('lead_score')} pts)")
    print(f"Generation Status:{outreach_data.get('generation_status', '').upper()}")
    
    review = outreach_data.get("human_review", {})
    print(f"Approval Status:  {review.get('approval_status', '').upper()}")
    
    if outreach_data.get("generation_status") == "skipped_low_priority":
        print(f"Skip Reason:      {outreach_data.get('generation_notes')}")
        print("=" * 70)
        return

    drafts = outreach_data.get("drafts", {})
    
    # 1. Email A
    ea = drafts.get("email_variant_a", {})
    print("\n" + "-" * 70)
    print(f"1. {ea.get('variant_name', 'Email Variant A')} ({ea.get('word_count')} words)")
    print(f"   Target:   {ea.get('target_persona')}")
    print(f"   Subject:  {ea.get('subject_line')}")
    print(f"   Evidence: {ea.get('evidence_used')}")
    print("   Body:\n   " + ea.get("body_text", "").replace("\n", "\n   "))

    # 2. Email B
    eb = drafts.get("email_variant_b", {})
    print("\n" + "-" * 70)
    print(f"2. {eb.get('variant_name', 'Email Variant B')} ({eb.get('word_count')} words)")
    print(f"   Target:   {eb.get('target_persona')}")
    print(f"   Subject:  {eb.get('subject_line')}")
    print(f"   Evidence: {eb.get('evidence_used')}")
    print("   Body:\n   " + eb.get("body_text", "").replace("\n", "\n   "))

    # 3. LinkedIn A
    la = drafts.get("linkedin_variant_a", {})
    print("\n" + "-" * 70)
    print(f"3. {la.get('variant_name', 'LinkedIn Connection Note')} ({la.get('character_count')}/300 chars)")
    print(f"   Target:   {la.get('target_persona')}")
    print(f"   Evidence: {la.get('evidence_used')}")
    print(f"   Message:  \"{la.get('message_text')}\"")

    # 4. LinkedIn B
    lb = drafts.get("linkedin_variant_b", {})
    print("\n" + "-" * 70)
    print(f"4. {lb.get('variant_name', 'LinkedIn InMail Message')} ({lb.get('word_count')} words)")
    print(f"   Target:   {lb.get('target_persona')}")
    print(f"   Evidence: {lb.get('evidence_used')}")
    print("   Message:\n   " + lb.get("message_text", "").replace("\n", "\n   "))
    print("=" * 70)


def test_stripe_skipped():
    print("\n[TEST 1] Testing Low-Priority Lead Token Safeguard (Stripe)...")
    stripe_profile = {
        "company_name": "Stripe",
        "website_url": "https://stripe.com"
    }
    stripe_analysis = {
        "analysis_status": "success",
        "crm_relevance": {"classification": "Low potential"}
    }
    stripe_score = {
        "priority": "Low priority",
        "total_score": 28,
        "confidence_level": "High confidence"
    }

    result = generate_outreach_drafts(stripe_profile, stripe_analysis, stripe_score)
    print_drafts_card(result, title="Stripe Outreach (Expected: Skipped Low Priority)")

    # Assertions
    assert result["generation_status"] == "skipped_low_priority", (
        f"Expected skipped_low_priority, got: {result['generation_status']}"
    )
    assert result["human_review"]["approval_status"] == "pending_human_review"
    print("✓ Passed: Correctly skipped outreach generation for low-priority enterprise non-fit.")


def test_apex_agro_outreach():
    print("\n[TEST 2] Testing Grounded Outreach Generation (Apex Agro & Spices)...")
    
    # Load profile, analysis, and score
    profile_path = Path("data") / "company_profile.json"
    analysis_path = Path("data") / "business_analysis.json"
    score_path = Path("data") / "lead_score.json"

    assert analysis_path.exists(), "data/business_analysis.json missing! Run test_analyzer.py first."
    assert score_path.exists(), "data/lead_score.json missing! Run test_scorer.py first."

    with open(analysis_path, "r", encoding="utf-8") as f:
        apex_analysis = json.load(f)

    with open(score_path, "r", encoding="utf-8") as f:
        apex_score = json.load(f)

    apex_profile = {
        "company_name": apex_analysis["company_name"],
        "website_url": apex_analysis["website_url"],
        "industry": "Food Processing & FMCG Wholesale Distribution",
        "location": "Kochi, Kerala, India",
        "products_services": ["Bulk ground spices", "Packaged curry powders", "Commercial seasoning blends"],
        "target_customers": ["Regional grocery supermarket chains", "Wholesale food stockists"],
        "verified_facts": [
            "Supplies over 450 verified supermarket accounts across Kerala and Tamil Nadu.",
            "Employs 18 regional field sales and order-collection agents.",
            "Announced an INR 12-crore expansion to establish 3 new regional supply depots in Bengaluru, Hyderabad, and Vijayawada."
        ],
    }

    result = generate_outreach_drafts(apex_profile, apex_analysis, apex_score)
    print_drafts_card(result, title="Apex Agro Outreach Drafts (Expected: 4 Grounded Variants)")

    # Assertions
    assert result["generation_status"] == "success", f"Expected success, got: {result['generation_status']}"
    assert result["human_review"]["approval_status"] == "pending_human_review"
    
    drafts = result["drafts"]
    assert "email_variant_a" in drafts
    assert "email_variant_b" in drafts
    assert "linkedin_variant_a" in drafts
    assert "linkedin_variant_b" in drafts

    # Verify character limit safeguard
    li_a_chars = drafts["linkedin_variant_a"]["character_count"]
    assert li_a_chars <= 300, f"LinkedIn Variant A exceeded 300 characters: {li_a_chars}"
    assert len(drafts["email_variant_a"]["evidence_used"]) >= 1
    assert len(drafts["email_variant_b"]["evidence_used"]) >= 1

    # Save to data/outreach_drafts.json
    out_file = Path("data") / "outreach_drafts.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved Phase 5 outreach drafts to: {out_file}")


def main():
    print("=== Running Phase 5 Outreach Generation Test Suite ===")
    test_stripe_skipped()
    test_apex_agro_outreach()
    print("\nAll Phase 5 Outreach Generation tests completed successfully!")


if __name__ == "__main__":
    main()
