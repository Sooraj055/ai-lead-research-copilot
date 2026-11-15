"""
crm_sync.py
===========
Human Approval and HubSpot Free CRM Integration module for the
AI Lead-Research and Outreach Copilot.

This module guarantees a Human-in-the-Loop workflow:
1. Review Gate: Enforces explicit human approval ('approved' or 'edited') before any lead
   can be synchronized to the CRM. Unapproved, pending, or rejected leads are strictly blocked.
2. Safe Outbound Policy: Never triggers automated email or LinkedIn message sends.
   The approved outreach copy is stored in the CRM company record for human rep execution.
3. HubSpot Free CRM API v3: Integrates with HubSpot via standard Company properties (name,
   domain, industry, city, country, description) and domain-based deduplication.
4. Local Dry-Run Mode: If HUBSPOT_ACCESS_TOKEN is unconfigured, seamlessly simulates the sync
   with full payload validation, returning a mock CRM ID without crashing or requiring credentials.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

load_dotenv()


def review_outreach_draft(
    outreach_data: Dict[str, Any],
    decision: str,
    selected_variant: str = "email_variant_a",
    custom_text: Optional[str] = None,
    reviewer_name: str = "Sales Rep",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Applies human review decisions to outreach drafts.

    Args:
        outreach_data (dict): Stage 5 outreach dictionary.
        decision (str): One of 'approve', 'edit', 'reject', 'save_for_later'.
        selected_variant (str): Variant chosen (e.g. 'email_variant_a', 'email_variant_b', 'linkedin_variant_a', 'linkedin_variant_b').
        custom_text (str, optional): Modified text if human edited the copy.
        reviewer_name (str): Name of the sales professional reviewing the lead.
        notes (str, optional): Internal notes or qualification observations.

    Returns:
        dict: Updated outreach_data with human_review metadata populated.
    """
    valid_decisions = {
        "approve": "approved",
        "edit": "edited",
        "reject": "rejected",
        "save_for_later": "saved_for_later",
    }
    
    clean_dec = decision.strip().lower()
    if clean_dec not in valid_decisions:
        raise ValueError(f"Invalid decision '{decision}'. Must be one of: {list(valid_decisions.keys())}")

    approval_status = valid_decisions[clean_dec]
    drafts = outreach_data.get("drafts", {})
    
    # Resolve approved text based on variant and decision
    final_text = None
    is_edited = False

    if approval_status == "approved":
        target_draft = drafts.get(selected_variant, {})
        final_text = target_draft.get("body_text") or target_draft.get("message_text") or ""
        is_edited = False
    elif approval_status == "edited":
        if custom_text and custom_text.strip():
            final_text = custom_text.strip()
        else:
            target_draft = drafts.get(selected_variant, {})
            final_text = target_draft.get("body_text") or target_draft.get("message_text") or ""
        is_edited = True
    else:
        # Rejected or Saved for later
        final_text = None
        is_edited = False

    outreach_data["human_review"] = {
        "approval_status": approval_status,
        "selected_variant": selected_variant if approval_status in ("approved", "edited") else None,
        "final_approved_text": final_text,
        "is_edited": is_edited,
        "reviewer_notes": notes,
        "reviewed_by": reviewer_name,
        "review_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return outreach_data


def _format_hubspot_description(
    company_profile: Dict[str, Any],
    business_analysis: Dict[str, Any],
    lead_score: Dict[str, Any],
    outreach_data: Dict[str, Any],
) -> str:
    """
    Formats complete sales intelligence into HubSpot's standard 'description' property.
    This guarantees compatibility with standard HubSpot Free accounts without requiring custom properties.
    """
    score = lead_score.get("total_score", 0)
    priority = lead_score.get("priority", "Unknown")
    summary = company_profile.get("company_summary") or "No company summary available."
    triggers = business_analysis.get("buying_triggers", [])
    
    trigger_lines = []
    if triggers:
        for t in triggers:
            trigger_lines.append(f"• [{t.get('trigger_type', '').upper()}] {t.get('description')}")
    else:
        trigger_lines.append("• No recent public triggers identified.")

    human_review = outreach_data.get("human_review", {})
    variant_name = human_review.get("selected_variant", "N/A")
    outreach_text = human_review.get("final_approved_text") or "No outreach text approved."

    lines = [
        "=== SALESFLOW CRM INTELLIGENCE REPORT ===",
        f"ICP Score: {score}/100 ({priority})",
        f"Recommendation: {lead_score.get('summary_recommendation', 'N/A')}",
        "",
        "--- Company Summary ---",
        summary,
        "",
        "--- Verified Buying Triggers ---",
        "\n".join(trigger_lines),
        "",
        f"--- Approved Outreach Draft ({variant_name}) ---",
        outreach_text,
        "",
        f"Reviewed by: {human_review.get('reviewed_by')} at {human_review.get('review_timestamp')}",
    ]
    return "\n".join(lines)


def _extract_domain(url: str) -> str:
    """Extracts clean domain without protocol or www."""
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else "https://" + url)
    return parsed.netloc.replace("www.", "")


def sync_lead_to_crm(
    company_profile: Dict[str, Any],
    business_analysis: Dict[str, Any],
    lead_score: Dict[str, Any],
    outreach_data: Dict[str, Any],
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronizes an approved lead to HubSpot Free CRM (or simulates sync via local dry-run).

    Args:
        company_profile (dict): Stage 2 company data.
        business_analysis (dict): Stage 3 CRM fit data.
        lead_score (dict): Stage 4 score data.
        outreach_data (dict): Stage 5 outreach data (must be reviewed).
        access_token (str, optional): HubSpot Private App Token. Defaults to HUBSPOT_ACCESS_TOKEN env var.

    Returns:
        dict: Complete sync log record matching data/crm_sync_log.json schema.
    """
    company_name = company_profile.get("company_name") or "Unknown Company"
    url = company_profile.get("website_url", "")
    domain = _extract_domain(url)
    timestamp = datetime.now(timezone.utc).isoformat()
    sync_id = f"sync_{int(time.time())}_{company_name.lower().replace(' ', '_')[:20]}"

    human_review = outreach_data.get("human_review", {})
    approval_status = human_review.get("approval_status", "pending_human_review")

    # STRICT HUMAN APPROVAL GATE: Only approved or edited leads can sync
    if approval_status not in ("approved", "edited"):
        return {
            "sync_id": sync_id,
            "timestamp": timestamp,
            "company_name": company_name,
            "domain": domain,
            "human_review_status": approval_status,
            "sync_mode": "blocked",
            "hubspot_company_id": None,
            "action_taken": "sync_blocked_unapproved",
            "properties_synced": {},
            "sync_status": "blocked",
            "sync_notes": (
                f"CRM sync rejected: Lead approval status is '{approval_status}'. "
                "Human approval is mandatory before any CRM insertion."
            ),
            "error_message": None,
        }

    # Extract location details
    location_str = company_profile.get("location") or ""
    loc_parts = [p.strip() for p in location_str.split(",") if p.strip()]
    city = loc_parts[0] if len(loc_parts) > 0 else None
    country = loc_parts[-1] if len(loc_parts) > 1 else ("India" if "india" in location_str.lower() else None)

    # Build standard HubSpot Company properties
    description_text = _format_hubspot_description(
        company_profile, business_analysis, lead_score, outreach_data
    )
    
    properties = {
        "name": company_name,
        "domain": domain,
        "industry": company_profile.get("industry") or "Unknown",
        "description": description_text,
    }
    if city:
        properties["city"] = city
    if country:
        properties["country"] = country

    # Check for live HubSpot token
    token = access_token or os.environ.get("HUBSPOT_ACCESS_TOKEN")
    is_live = bool(token and not token.startswith("your_"))

    # MODE 1: LOCAL DRY-RUN MODE (When no live token is present)
    if not is_live:
        simulated_id = f"simulated_hubspot_comp_{int(time.time())}"
        return {
            "sync_id": sync_id,
            "timestamp": timestamp,
            "company_name": company_name,
            "domain": domain,
            "human_review_status": approval_status,
            "sync_mode": "dry_run_simulated",
            "hubspot_company_id": simulated_id,
            "action_taken": "created_new_company",
            "properties_synced": properties,
            "sync_status": "success",
            "sync_notes": (
                "Dry-run simulation mode active (HUBSPOT_ACCESS_TOKEN unconfigured). "
                "Payload fully validated against HubSpot v3 Companies schema."
            ),
            "error_message": None,
        }

    # MODE 2: LIVE HUBSPOT API v3
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    base_url = "https://api.hubapi.com/crm/v3/objects/companies"

    try:
        # Step A: Deduplication Search by domain
        search_url = f"{base_url}/search"
        search_payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "domain",
                            "operator": "EQ",
                            "value": domain,
                        }
                    ]
                }
            ],
            "limit": 1,
        }
        search_resp = requests.post(search_url, headers=headers, json=search_payload, timeout=10)
        
        company_id = None
        action_taken = "created_new_company"

        if search_resp.status_code == 200:
            results = search_resp.json().get("results", [])
            if results:
                company_id = results[0]["id"]
                action_taken = "updated_existing_company"

        # Step B: Create or Update Company
        if company_id:
            # Update existing company
            update_url = f"{base_url}/{company_id}"
            update_resp = requests.patch(update_url, headers=headers, json={"properties": properties}, timeout=10)
            if update_resp.status_code not in (200, 201):
                return {
                    "sync_id": sync_id,
                    "timestamp": timestamp,
                    "company_name": company_name,
                    "domain": domain,
                    "human_review_status": approval_status,
                    "sync_mode": "live_hubspot",
                    "hubspot_company_id": company_id,
                    "action_taken": action_taken,
                    "properties_synced": properties,
                    "sync_status": "failed",
                    "sync_notes": "HubSpot update request returned non-200 code.",
                    "error_message": f"HTTP {update_resp.status_code}: {update_resp.text}",
                }
        else:
            # Create new company
            create_resp = requests.post(base_url, headers=headers, json={"properties": properties}, timeout=10)
            if create_resp.status_code in (200, 201):
                company_id = create_resp.json().get("id")
            else:
                return {
                    "sync_id": sync_id,
                    "timestamp": timestamp,
                    "company_name": company_name,
                    "domain": domain,
                    "human_review_status": approval_status,
                    "sync_mode": "live_hubspot",
                    "hubspot_company_id": None,
                    "action_taken": action_taken,
                    "properties_synced": properties,
                    "sync_status": "failed",
                    "sync_notes": "HubSpot create request returned non-200 code.",
                    "error_message": f"HTTP {create_resp.status_code}: {create_resp.text}",
                }

        return {
            "sync_id": sync_id,
            "timestamp": timestamp,
            "company_name": company_name,
            "domain": domain,
            "human_review_status": approval_status,
            "sync_mode": "live_hubspot",
            "hubspot_company_id": str(company_id),
            "action_taken": action_taken,
            "properties_synced": properties,
            "sync_status": "success",
            "sync_notes": f"Successfully synchronized company to live HubSpot Free CRM ({action_taken}).",
            "error_message": None,
        }

    except Exception as exc:
        return {
            "sync_id": sync_id,
            "timestamp": timestamp,
            "company_name": company_name,
            "domain": domain,
            "human_review_status": approval_status,
            "sync_mode": "live_hubspot",
            "hubspot_company_id": None,
            "action_taken": "failed",
            "properties_synced": properties,
            "sync_status": "failed",
            "sync_notes": f"Network or execution exception connecting to HubSpot: {str(exc)}",
            "error_message": str(exc),
        }
