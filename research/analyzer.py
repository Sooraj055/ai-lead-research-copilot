"""
analyzer.py
===========
AI Business Analysis module for the AI Lead-Research and Outreach Copilot.

This module analyzes a structured company profile (from Stage 2) alongside optional
supplemental research (news, careers, expansion notices) to evaluate product fit
for 'SalesFlow CRM' against an Indian SMB Ideal Customer Profile (ICP).

Identifies:
1. CRM relevance and structured ICP signals.
2. Potential business pain points (rigorously separated into facts vs. hypotheses).
3. Observable buying triggers (expansion, hiring, product launches).
4. Tailored value hypotheses for SalesFlow CRM features.
5. Remaining information gaps to guide human sales reps.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Product and Ideal Customer Profile (ICP) Context
SALESFLOW_PRODUCT_CONTEXT = """
Product: SalesFlow CRM
Type: Cloud-based B2B Sales & Customer Relationship Management Software
Target Audience: Small and Medium Businesses (SMBs) in India (10-200 employees, 2-30 sales reps).

Core Capabilities:
1. Centralized customer & distributor database (replaces scattered spreadsheets/WhatsApp).
2. Lead and inquiry management across multiple distribution channels.
3. Visual sales pipeline tracking and deal-stage monitoring.
4. Automated follow-up reminders to ensure sales reps do not drop inquiries.
5. Sales team performance reporting and activity analytics.
6. Multi-user team collaboration and sales territory assignments.

Target ICP Parameters:
- Geography: Headquartered in India or substantial sales/distribution presence in India.
- Company Size: 10-200 employees (SMB scale). Enterprises (>1000 employees) likely use enterprise systems (Salesforce/SAP) and are Low potential.
- Business Model: B2B.
- Priority Industries: FMCG distributors, Wholesale distributors, Food processing, Manufacturing, B2B services, and SME SaaS.
- High-Fit Characteristics: Multi-tier dealer/retailer networks, field sales representatives, frequent client follow-ups, geographical market expansion.
"""


def get_empty_business_analysis(
    company_name: Optional[str] = None,
    website_url: str = "",
    status: str = "failed",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a standardized default dictionary matching the Phase 3 JSON schema.
    Used for failed analyses, missing data, or fallback responses.
    """
    return {
        "company_name": company_name or "Unknown Company",
        "website_url": website_url,
        "product_analyzed": "SalesFlow CRM",
        "crm_relevance": {
            "classification": "Insufficient information",
            "reasoning": "Analysis could not be completed.",
            "icp_signals": {
                "geography_match": "unknown",
                "industry_match": "none",
                "company_size_match": "unknown",
                "sales_complexity_signal": "unknown",
            },
        },
        "potential_pain_points": [],
        "buying_triggers": [],
        "no_trigger_reason": "Analysis incomplete or insufficient data provided.",
        "value_hypotheses": [],
        "information_gaps": ["Complete company profile data is missing."],
        "analysis_status": status,
        "analysis_notes": notes,
    }


def _heuristic_fallback_analysis(company_profile: Dict[str, Any], notes: str) -> Dict[str, Any]:
    """
    Rule-based fallback analysis when Gemini API is unavailable.
    Performs basic heuristic classification based on industry and business model.
    """
    company_name = company_profile.get("company_name", "Target Company")
    url = company_profile.get("website_url", "")
    industry = (company_profile.get("industry") or "").lower()
    biz_model = company_profile.get("business_model", "Unknown")

    # Simple heuristic checks
    is_b2b = biz_model == "B2B"
    is_target_ind = any(
        term in industry
        for term in ["distribut", "manufactur", "food", "wholesale", "software", "saas", "service"]
    )

    if is_b2b and is_target_ind:
        relevance = "Medium potential"
        reason = f"Company operates in B2B {industry or 'sector'}, which commonly benefits from pipeline and inquiry tracking."
        ind_match = "medium"
    elif is_b2b:
        relevance = "Low potential"
        reason = "B2B business model identified, but industry does not strongly match priority distribution sectors."
        ind_match = "low"
    else:
        relevance = "Low potential"
        reason = "Non-B2B or unverified business model. SalesFlow CRM targets B2B sales pipelines."
        ind_match = "none"

    analysis = get_empty_business_analysis(company_name=company_name, website_url=url, status="partial", notes=notes)
    analysis["crm_relevance"]["classification"] = relevance
    analysis["crm_relevance"]["reasoning"] = reason
    analysis["crm_relevance"]["icp_signals"] = {
        "geography_match": "unknown",
        "industry_match": ind_match,
        "company_size_match": "unknown",
        "sales_complexity_signal": "medium" if is_b2b else "low",
    }
    analysis["no_trigger_reason"] = "Rule-based fallback active. Buying triggers require LLM semantic analysis."
    analysis["value_hypotheses"].append({
        "feature": "Centralized Customer Database",
        "hypothesized_benefit": "Could consolidate client contact records and inquiry tracking."
    })
    return analysis


def analyze_company_crm_fit(
    company_profile: Dict[str, Any],
    additional_research: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash",
) -> Dict[str, Any]:
    """
    Analyzes a company profile against SalesFlow CRM capabilities and the Indian SMB ICP.

    Args:
        company_profile (dict): Structured profile from Stage 2 (extract_company_info).
        additional_research (str, optional): Additional text (job postings, press releases, expansion news).
        api_key (str, optional): Google Gemini API key. Defaults to GEMINI_API_KEY env var.
        model_name (str): Model identifier. Defaults to 'gemini-3.8-flash'.

    Returns:
        dict: Validated business analysis matching the approved Phase 3 JSON schema.
    """
    company_name = company_profile.get("company_name") or "Unknown Company"
    url = company_profile.get("website_url", "")

    # Step 1: Defensive validation of incoming profile
    if company_profile.get("extraction_status") == "failed":
        notes = company_profile.get("extraction_notes", "Company extraction failed.")
        return get_empty_business_analysis(
            company_name=company_name,
            website_url=url,
            status="failed",
            notes=f"Business analysis aborted because Stage 2 extraction failed: {notes}",
        )

    # Step 2: Resolve Gemini API Key
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_api_key:
        return _heuristic_fallback_analysis(
            company_profile,
            notes="GEMINI_API_KEY environment variable is not set. Generated partial analysis using heuristic fallback.",
        )

    # Step 3: Construct Grounded System Prompt
    system_instruction = (
        "You are a Senior B2B Sales Operations & CRM Strategy Analyst.\n"
        "Your task is to analyze target company research and evaluate fit for 'SalesFlow CRM'.\n\n"
        f"{SALESFLOW_PRODUCT_CONTEXT}\n\n"
        "STRICT GROUNDING & METHODOLOGY RULES:\n"
        "1. GROUNDING & HYPOTHESES: Never claim an internal company problem is a verified fact without explicit public proof. "
        "Label all inferred CRM bottlenecks as 'hypothesis'. Use 'verified fact' ONLY if the source explicitly states it.\n"
        "2. BUYING TRIGGERS: Must be concrete, observable events (e.g. expansion, hiring sales reps, launching new products). "
        "If no evidence of recent triggers exists in the provided text, return an empty array [] for 'buying_triggers' and "
        "explain why in 'no_trigger_reason'. DO NOT fabricate hiring or expansion events.\n"
        "3. CRM RELEVANCE: Classify as 'High potential', 'Medium potential', 'Low potential', or 'Insufficient information'. "
        "Large global enterprises (>1000 employees or billions in revenue, like Stripe) must be marked 'Low potential' because "
        "they use enterprise suites (Salesforce, SAP) and do not fit an Indian SMB tool.\n"
        "4. ICP SIGNALS: Explicitly evaluate geography_match ('yes'|'no'|'unknown'), industry_match ('high'|'medium'|'low'|'none'), "
        "company_size_match ('yes'|'no'|'unknown'), and sales_complexity_signal ('high'|'medium'|'low'|'unknown').\n"
        "5. OUTPUT FORMAT: Respond strictly in valid JSON matching the exact schema provided. Do not include markdown codeblocks or commentary."
    )

    profile_text = json.dumps(company_profile, indent=2)
    research_section = f"\nSupplemental Research Evidence:\n{additional_research.strip()}" if additional_research else ""

    prompt = f"""
Target Company Profile (from Stage 2):
{profile_text}
{research_section}

Analyze this company and return valid JSON adhering strictly to this schema:
{{
  "company_name": "{company_name}",
  "website_url": "{url}",
  "product_analyzed": "SalesFlow CRM",
  "crm_relevance": {{
    "classification": "High potential | Medium potential | Low potential | Insufficient information",
    "reasoning": "Detailed justification comparing company against SalesFlow CRM's Indian SMB ICP",
    "icp_signals": {{
      "geography_match": "yes | no | unknown",
      "industry_match": "high | medium | low | none",
      "company_size_match": "yes | no | unknown",
      "sales_complexity_signal": "high | medium | low | unknown"
    }}
  }},
  "potential_pain_points": [
    {{
      "problem": "Specific operational or sales challenge",
      "reasoning": "Why this bottleneck likely applies given their business model/scale",
      "evidence": ["Direct statements or observations from research"],
      "source_urls": ["{url}"],
      "classification": "hypothesis | verified fact",
      "confidence": "high | medium | low"
    }}
  ],
  "buying_triggers": [
    {{
      "trigger_type": "expansion | hiring | product_launch | leadership_change | partnership | other",
      "description": "Observable event indicating urgency or operational change",
      "evidence_quote": "Exact quote or citation from research text",
      "source_url": "Source URL",
      "observed_date": "YYYY-MM or null"
    }}
  ],
  "no_trigger_reason": "string explaining lack of triggers if buying_triggers is empty, otherwise null",
  "value_hypotheses": [
    {{
      "feature": "Name of specific SalesFlow CRM feature",
      "hypothesized_benefit": "Specific operational benefit tailored to this company"
    }}
  ],
  "information_gaps": ["Key unknown details a sales rep should clarify before contacting"],
  "analysis_status": "success",
  "analysis_notes": "Observations on data quality and confidence"
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=effective_api_key)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        analysis = json.loads(raw_text)

        # Enforce all required schema keys
        default_analysis = get_empty_business_analysis(
            company_name=company_name, website_url=url, status="success"
        )
        for key in default_analysis:
            if key not in analysis:
                analysis[key] = default_analysis[key]

        # Enforce icp_signals sub-keys
        if "crm_relevance" in analysis and "icp_signals" not in analysis["crm_relevance"]:
            analysis["crm_relevance"]["icp_signals"] = default_analysis["crm_relevance"]["icp_signals"]

        analysis["analysis_status"] = "success"
        return analysis

    except Exception as exc:
        fallback = _heuristic_fallback_analysis(
            company_profile,
            notes=f"Gemini API analysis failed ({type(exc).__name__}: {str(exc)}). Heuristic analysis returned.",
        )
        fallback["analysis_status"] = "failed"
        return fallback
