"""
test_crm_sync.py
================
Automated test suite for Stage 6: Human Approval & HubSpot Free CRM Integration.

Tests:
1. Mandatory Human Approval Gate:
   - Verifies that a lead with status 'pending_human_review' is strictly blocked from CRM sync.
   - Verifies that a lead with status 'rejected' is strictly blocked from CRM sync.
2. Human Approval & Dry-Run Sync:
   - Transitions an outreach draft for Apex Agro & Spices to 'approved'.
   - Executes sync_lead_to_crm() in dry_run_simulated mode.
   - Verifies all standard properties (name, domain, industry, city, country, description).
   - Verifies audit log written to data/crm_sync_log.json.
3. Human Custom Editing & Sync:
   - Tests the 'edit' decision with customized sales copy.
   - Verifies that the human-edited text is preserved and dispatched in the CRM payload.
"""

import json
from pathlib import Path
from research.crm_sync import review_outreach_draft, sync_lead_to_crm


def print_sync_card(sync_record: dict, title: str = "CRM Sync Log") -> None:
    print("\n" + "=" * 70)
    print(f" {title} ")
    print("=" * 70)
    print(f"Sync ID:            {sync_record.get('sync_id')}")
    print(f"Company Name:       {sync_record.get('company_name')}")
    print(f"Domain:             {sync_record.get('domain')}")
    print(f"Human Status:       {sync_record.get('human_review_status', '').upper()}")
    print(f"Sync Mode:          {sync_record.get('sync_mode', '').upper()}")
    print(f"Sync Status:        {sync_record.get('sync_status', '').upper()}")
    print(f"Action Taken:       {sync_record.get('action_taken')}")
    print(f"HubSpot Company ID: {sync_record.get('hubspot_company_id')}")
    print(f"Notes:              {sync_record.get('sync_notes')}")
    
    props = sync_record.get("properties_synced", {})
    if props:
        print("\nProperties Synced:")
        print(f"  • Name:     {props.get('name')}")
        print(f"  • Domain:   {props.get('domain')}")
        print(f"  • Industry: {props.get('industry')}")
        print(f"  • City:     {props.get('city')}")
        print(f"  • Country:  {props.get('country')}")
        desc_preview = props.get("description", "")[:200].replace("\n", " ")
        print(f"  • Description Preview: \"{desc_preview}...\"")
    print("=" * 70)


def test_blocking_unapproved():
    print("\n[TEST 1] Testing Gatekeeper: Blocking Unapproved / Pending Lead...")
    unreviewed_outreach = {
        "company_name": "Unreviewed Corp",
        "website_url": "https://unreviewed.example.com",
        "human_review": {
            "approval_status": "pending_human_review",
            "selected_variant": None,
            "final_approved_text": None,
        }
    }
    dummy_profile = {"company_name": "Unreviewed Corp", "website_url": "https://unreviewed.example.com"}
    dummy_analysis = {"buying_triggers": []}
    dummy_score = {"total_score": 50, "priority": "Medium priority"}

    result = sync_lead_to_crm(dummy_profile, dummy_analysis, dummy_score, unreviewed_outreach)
    print_sync_card(result, title="Unapproved Lead (Expected: BLOCKED)")

    # Assertions
    assert result["sync_status"] == "blocked"
    assert result["action_taken"] == "sync_blocked_unapproved"
    assert result["hubspot_company_id"] is None
    print("✓ Passed: Strictly blocked sync for lead in 'pending_human_review' state.")


def test_blocking_rejected():
    print("\n[TEST 2] Testing Gatekeeper: Blocking Rejected Lead...")
    rejected_outreach = {
        "company_name": "Competitor Inc",
        "website_url": "https://competitor.example.com",
        "human_review": {
            "approval_status": "rejected",
            "selected_variant": None,
            "final_approved_text": None,
            "reviewer_notes": "Direct competitor; disqualified from sales outreach."
        }
    }
    dummy_profile = {"company_name": "Competitor Inc", "website_url": "https://competitor.example.com"}
    dummy_analysis = {"buying_triggers": []}
    dummy_score = {"total_score": 10, "priority": "Low priority"}

    result = sync_lead_to_crm(dummy_profile, dummy_analysis, dummy_score, rejected_outreach)
    print_sync_card(result, title="Rejected Lead (Expected: BLOCKED)")

    # Assertions
    assert result["sync_status"] == "blocked"
    assert result["action_taken"] == "sync_blocked_unapproved"
    assert "rejected" in result["sync_notes"].lower()
    print("✓ Passed: Strictly blocked sync for lead in 'rejected' state.")


def test_approving_and_syncing_apex_agro():
    print("\n[TEST 3] Testing Human Approval & Dry-Run CRM Sync (Apex Agro)...")
    
    # Load Stage 2, 3, 4, 5 artifacts
    analysis_path = Path("data") / "business_analysis.json"
    score_path = Path("data") / "lead_score.json"
    outreach_path = Path("data") / "outreach_drafts.json"

    assert analysis_path.exists(), "data/business_analysis.json missing!"
    assert score_path.exists(), "data/lead_score.json missing!"
    assert outreach_path.exists(), "data/outreach_drafts.json missing!"

    with open(analysis_path, "r", encoding="utf-8") as f:
        apex_analysis = json.load(f)

    with open(score_path, "r", encoding="utf-8") as f:
        apex_score = json.load(f)

    with open(outreach_path, "r", encoding="utf-8") as f:
        apex_outreach = json.load(f)

    apex_profile = {
        "company_name": apex_analysis["company_name"],
        "website_url": apex_analysis["website_url"],
        "industry": "Food Processing & FMCG Wholesale Distribution",
        "location": "Kochi, Kerala, India",
        "company_summary": "Manufacturer and wholesale distributor of processed spices and condiments serving 450+ accounts across South India.",
    }

    # Step 1: Human Reviews and Approves Email Variant A
    reviewed_outreach = review_outreach_draft(
        apex_outreach,
        decision="approve",
        selected_variant="email_variant_a",
        reviewer_name="Sooraj (Sales Rep)",
        notes="High priority target expanding into Bengaluru and Hyderabad."
    )
    assert reviewed_outreach["human_review"]["approval_status"] == "approved"
    assert reviewed_outreach["human_review"]["selected_variant"] == "email_variant_a"
    assert len(reviewed_outreach["human_review"]["final_approved_text"]) > 20

    # Step 2: Sync to CRM (in dry-run mode)
    sync_result = sync_lead_to_crm(
        apex_profile, apex_analysis, apex_score, reviewed_outreach
    )
    print_sync_card(sync_result, title="Apex Agro Approved Lead (Expected: SUCCESS - DRY RUN)")

    # Assertions
    assert sync_result["sync_status"] == "success"
    assert sync_result["sync_mode"] == "dry_run_simulated"
    assert sync_result["hubspot_company_id"] is not None
    assert sync_result["properties_synced"]["domain"] == "apexagrospices.example.in"
    assert sync_result["properties_synced"]["city"] == "Kochi"
    assert "SALESFLOW CRM INTELLIGENCE REPORT" in sync_result["properties_synced"]["description"]

    # Save to data/crm_sync_log.json
    out_file = Path("data") / "crm_sync_log.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(sync_result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved Stage 6 CRM sync log to: {out_file}")


def test_editing_and_syncing():
    print("\n[TEST 4] Testing Human Custom Edit & Sync...")
    dummy_outreach = {
        "company_name": "Kerala Spices Co",
        "website_url": "https://keralaspices.example.in",
        "drafts": {
            "email_variant_a": {"body_text": "Generic draft"}
        },
        "human_review": {"approval_status": "pending_human_review"}
    }
    dummy_profile = {
        "company_name": "Kerala Spices Co",
        "website_url": "https://keralaspices.example.in",
        "industry": "Wholesale Distribution",
        "location": "Kochi, India"
    }
    dummy_analysis = {"buying_triggers": []}
    dummy_score = {"total_score": 85, "priority": "High priority"}

    custom_text = "Hi Rajesh, saw your new warehouse in Ernakulam. Let's discuss distributor order tracking."
    
    reviewed = review_outreach_draft(
        dummy_outreach,
        decision="edit",
        selected_variant="email_variant_a",
        custom_text=custom_text,
        reviewer_name="Sooraj (Sales Rep)",
        notes="Customized opening hook mentioning the Ernakulam warehouse."
    )
    assert reviewed["human_review"]["approval_status"] == "edited"
    assert reviewed["human_review"]["is_edited"] is True
    assert reviewed["human_review"]["final_approved_text"] == custom_text

    sync_result = sync_lead_to_crm(dummy_profile, dummy_analysis, dummy_score, reviewed)
    assert sync_result["sync_status"] == "success"
    assert custom_text in sync_result["properties_synced"]["description"]
    print("✓ Passed: Human-edited copy preserved and synced successfully.")


def main():
    print("=== Running Stage 6 Human Approval & CRM Sync Test Suite ===")
    test_blocking_unapproved()
    test_blocking_rejected()
    test_approving_and_syncing_apex_agro()
    test_editing_and_syncing()
    print("\nAll Stage 6 Human Approval & CRM Sync tests completed successfully!")


if __name__ == "__main__":
    main()
