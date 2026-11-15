"""
test_scorer.py
==============
Automated test suite for Phase 4: Deterministic ICP Lead Scoring.

Tests:
1. Enterprise non-fit case (Stripe) -> Verifies 'Low priority' classification.
2. Realistic Indian B2B distributor case (Apex Agro & Spices) -> Verifies 'High priority' and high confidence.
3. Synthetic 'Insufficient evidence' company -> Verifies 'Insufficient evidence' flag when 2+ ICP signals are unknown.
4. Schema validation and persistence to data/lead_score.json.
"""

import json
from pathlib import Path
from research.scorer import score_lead


def print_score_card(score_data: dict, title: str = "Lead Score Card") -> None:
    print("\n" + "=" * 70)
    print(f" {title} ")
    print("=" * 70)
    print(f"Company Name:       {score_data.get('company_name')}")
    print(f"Total Score:        {score_data.get('total_score')}/{score_data.get('max_score')} Points")
    print(f"Priority Tier:      {score_data.get('priority', '').upper()}")
    print(f"Confidence Level:   {score_data.get('confidence_level', '').upper()}")
    print(f"Recommendation:     {score_data.get('summary_recommendation')}")
    
    breakdown = score_data.get("scoring_breakdown", {})
    print("\nDetailed Rubric Breakdown:")
    for criterion, details in breakdown.items():
        print(f"  • {criterion.replace('_', ' ').title():<22}: {details['score']:>2}/{details['max']} pts | Signal: {details['signal']:<12} | {details['reasoning']}")
    print("=" * 70)


def test_stripe_scoring():
    print("\n[TEST 1] Testing Stripe (Enterprise Non-Fit)...")
    stripe_analysis = {
        "company_name": "Stripe",
        "website_url": "https://stripe.com",
        "product_analyzed": "SalesFlow CRM",
        "crm_relevance": {
            "classification": "Low potential",
            "reasoning": "Massive global enterprise exceeding Indian SMB scale.",
            "icp_signals": {
                "geography_match": "unknown",
                "industry_match": "low",
                "company_size_match": "no",
                "sales_complexity_signal": "high"
            }
        },
        "potential_pain_points": [
            {
                "problem": "Multi-product pipeline tracking",
                "classification": "hypothesis",
                "confidence": "low"
            }
        ],
        "buying_triggers": [],
        "analysis_status": "success"
    }

    score_result = score_lead(stripe_analysis)
    print_score_card(score_result, title="Stripe Score Card (Expected: Low Priority)")

    # Assertions
    assert score_result["priority"] == "Low priority", f"Expected Low priority, got: {score_result['priority']}"
    assert score_result["total_score"] < 45, f"Expected score < 45, got: {score_result['total_score']}"
    print("✓ Passed: Stripe accurately scored as Low priority non-fit.")


def test_apex_agro_scoring():
    print("\n[TEST 2] Testing Apex Agro & Spices (Ideal Indian B2B Lead)...")
    analysis_file = Path("data") / "business_analysis.json"
    assert analysis_file.exists(), "data/business_analysis.json missing! Run test_analyzer.py first."

    with open(analysis_file, "r", encoding="utf-8") as f:
        apex_analysis = json.load(f)

    score_result = score_lead(apex_analysis)
    print_score_card(score_result, title="Apex Agro & Spices Score Card (Expected: High Priority)")

    # Assertions
    assert score_result["priority"] == "High priority", f"Expected High priority, got: {score_result['priority']}"
    assert score_result["total_score"] >= 70, f"Expected score >= 70, got: {score_result['total_score']}"
    assert score_result["confidence_level"] == "High confidence"
    
    # Save output to data/lead_score.json
    out_file = Path("data") / "lead_score.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(score_result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved Phase 4 lead score to: {out_file}")


def test_insufficient_evidence_scoring():
    print("\n[TEST 3] Testing Synthetic 'Insufficient Evidence' Lead...")
    synthetic_sparse_analysis = {
        "company_name": "Mystery Logistics Ltd.",
        "website_url": "https://mysterylogistics.example.com",
        "product_analyzed": "SalesFlow CRM",
        "crm_relevance": {
            "classification": "Medium potential",
            "reasoning": "Logistics operations may need inquiry tracking, but scale is unverified.",
            "icp_signals": {
                "geography_match": "unknown",       # Unknown signal 1
                "industry_match": "medium",
                "company_size_match": "unknown",    # Unknown signal 2
                "sales_complexity_signal": "unknown" # Unknown signal 3
            }
        },
        "potential_pain_points": [
            {
                "problem": "Fleet shipment tracking",
                "classification": "hypothesis",
                "confidence": "medium"
            }
        ],
        "buying_triggers": [],
        "analysis_status": "success"
    }

    score_result = score_lead(synthetic_sparse_analysis)
    print_score_card(score_result, title="Mystery Logistics (Expected: Insufficient Evidence Flag)")

    # Assertions
    assert score_result["confidence_level"] == "Insufficient evidence", (
        f"Expected 'Insufficient evidence', got: {score_result['confidence_level']}"
    )
    assert "manual qualification required" in score_result["summary_recommendation"].lower()
    print("✓ Passed: Correctly flagged Insufficient Evidence when 2+ ICP signals are unknown.")


def main():
    print("=== Running Phase 4 Lead Scoring Test Suite ===")
    test_stripe_scoring()
    test_apex_agro_scoring()
    test_insufficient_evidence_scoring()
    print("\nAll Phase 4 Lead Scoring tests completed successfully!")


if __name__ == "__main__":
    main()
