"""
outreach.py
===========
Personalised Outreach Generation module for the AI Lead-Research and Outreach Copilot.

This module synthesizes:
1. Stage 2 Company Profile (verified facts, products, audience)
2. Stage 3 Business Analysis (pain-point hypotheses, buying triggers, value hypotheses)
3. Stage 4 Lead Score (priority tier and recommendation)

Generates four grounded, anti-fluff outreach drafts:
- Email Variant A: Concise, direct, trigger-led
- Email Variant B: Consultative, hypothesis-led
- LinkedIn Variant A: Connection request strictly <= 300 characters
- LinkedIn Variant B: Conversational InMail / messaging note

Core Safety & Human-in-the-Loop Rules:
- Never sends messages automatically.
- Initializes all drafts as 'pending_human_review'.
- Skips token spend on 'Low priority' non-fits (like Stripe).
- Enforces strict character and word count calculations in Python.
"""

import os
import json
import re
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


def get_empty_outreach_drafts(
    company_name: str,
    website_url: str,
    lead_priority: str = "Low priority",
    lead_score: int = 0,
    status: str = "failed",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standard default dictionary matching the data/outreach_drafts.json schema.
    """
    return {
        "company_name": company_name,
        "website_url": website_url,
        "lead_priority": lead_priority,
        "lead_score": lead_score,
        "product_pitch": "SalesFlow CRM",
        "drafts": {
            "email_variant_a": {
                "variant_name": "Direct & Trigger-Led",
                "target_persona": "Head of Sales / Managing Director",
                "subject_line": "",
                "body_text": "",
                "word_count": 0,
                "evidence_used": [],
            },
            "email_variant_b": {
                "variant_name": "Consultative & Hypothesis-Led",
                "target_persona": "Commercial Director / Channel Operations Head",
                "subject_line": "",
                "body_text": "",
                "word_count": 0,
                "evidence_used": [],
            },
            "linkedin_variant_a": {
                "variant_name": "Connection Request Note",
                "target_persona": "Sales Leadership / Founder",
                "message_text": "",
                "character_count": 0,
                "character_limit": 300,
                "evidence_used": [],
            },
            "linkedin_variant_b": {
                "variant_name": "Conversational InMail Message",
                "target_persona": "Regional Sales Manager / Channel Head",
                "message_text": "",
                "word_count": 0,
                "evidence_used": [],
            },
        },
        "human_review": {
            "approval_status": "pending_human_review",
            "approved_variant": None,
            "edited_text": None,
            "reviewed_by": None,
            "review_timestamp": None,
        },
        "generation_status": status,
        "generation_notes": notes,
    }


def _heuristic_fallback_outreach(
    company_profile: Dict[str, Any],
    lead_score: Dict[str, Any],
    notes: str,
) -> Dict[str, Any]:
    """
    Rule-based template fallback outreach when Gemini API is unconfigured.
    """
    name = company_profile.get("company_name", "Target Company")
    url = company_profile.get("website_url", "")
    priority = lead_score.get("priority", "Medium priority")
    score = lead_score.get("total_score", 50)

    drafts = get_empty_outreach_drafts(
        company_name=name,
        website_url=url,
        lead_priority=priority,
        lead_score=score,
        status="partial",
        notes=notes,
    )

    email_a = (
        f"Hi [First Name],\n\n"
        f"I came across {name}'s operations and noticed your B2B sales presence.\n\n"
        "As sales teams scale their distributor and customer networks across multiple regions, "
        "tracking inquiries and dealer follow-ups without dropped orders becomes challenging.\n\n"
        "SalesFlow CRM gives growing Indian businesses a centralized pipeline to track distributor accounts "
        "and field rep visits in one clean dashboard.\n\n"
        "Would you be open to a 2-minute walkthrough to see how regional teams organize their pipelines?"
    )
    drafts["drafts"]["email_variant_a"]["subject_line"] = f"{name}'s sales inquiry & distributor pipeline"
    drafts["drafts"]["email_variant_a"]["body_text"] = email_a
    drafts["drafts"]["email_variant_a"]["word_count"] = len(email_a.split())
    drafts["drafts"]["email_variant_a"]["evidence_used"] = ["B2B sales model from company profile"]

    li_note = (
        f"Hi [First Name], saw {name}'s growth. We help Indian B2B companies track wholesale "
        f"distributor inquiries and field rep follow-ups in a centralized CRM. "
        f"Would love to connect!"
    )[:295]
    drafts["drafts"]["linkedin_variant_a"]["message_text"] = li_note
    drafts["drafts"]["linkedin_variant_a"]["character_count"] = len(li_note)
    drafts["drafts"]["linkedin_variant_a"]["evidence_used"] = ["Company profile"]

    return drafts


def generate_outreach_drafts(
    company_profile: Dict[str, Any],
    business_analysis: Dict[str, Any],
    lead_score: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash-lite",
) -> Dict[str, Any]:
    """
    Generates four personalized, human-in-the-loop outreach drafts grounded in company research.

    Args:
        company_profile (dict): Output from Stage 2 extract_company_info().
        business_analysis (dict): Output from Stage 3 analyze_company_crm_fit().
        lead_score (dict): Output from Stage 4 score_lead().
        api_key (str, optional): Gemini API key. Defaults to GEMINI_API_KEY env var.
        model_name (str): Model identifier. Defaults to 'gemini-3.5-flash-lite'.

    Returns:
        dict: Complete outreach drafts object with approval status initialized to 'pending_human_review'.
    """
    company_name = company_profile.get("company_name") or "Target Company"
    url = company_profile.get("website_url", "")
    priority = lead_score.get("priority", "Low priority")
    score = lead_score.get("total_score", 0)
    confidence = lead_score.get("confidence_level", "High confidence")

    # Safeguard 1: Skip token spend if lead is an enterprise or disqualified Low priority non-fit
    if priority == "Low priority" and confidence != "Insufficient evidence":
        return get_empty_outreach_drafts(
            company_name=company_name,
            website_url=url,
            lead_priority=priority,
            lead_score=score,
            status="skipped_low_priority",
            notes=(
                f"Outreach generation skipped: Lead scored {score}/100 ('Low priority'). "
                "Tokens preserved by bypassing outreach generation for enterprise or unqualified leads."
            ),
        )

    # Safeguard 2: Check for upstream failures
    if business_analysis.get("analysis_status") == "failed":
        return get_empty_outreach_drafts(
            company_name=company_name,
            website_url=url,
            lead_priority=priority,
            lead_score=score,
            status="failed",
            notes="Outreach generation aborted because Stage 3 business analysis failed.",
        )

    # Safeguard 3: Resolve API Key
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_api_key:
        return _heuristic_fallback_outreach(
            company_profile,
            lead_score,
            notes="GEMINI_API_KEY not configured. Generated template fallback drafts.",
        )

    # Construct Grounded Context
    system_instruction = (
        "You are an Elite B2B Sales Development Copywriter specializing in consultative, highly personalized "
        "outreach for 'SalesFlow CRM' (a cloud-based CRM for growing Indian SMBs managing field reps and distributors).\n\n"
        "STRICT ANTI-FLUFF & COPYWRITING RULES:\n"
        "1. NEVER use generic AI cliches: FORBIDDEN phrases include 'I hope this email finds you well', "
        "'In today's fast-paced digital world', 'I was deeply impressed', 'synergy', 'game-changer', or 'cutting-edge'.\n"
        "2. GROUNDING: The opening hook MUST reference a specific, verified fact or trigger from the research "
        "(e.g. recent depot expansion, hiring sales reps, or managing 450+ supermarket accounts).\n"
        "3. LOW-PRESSURE CALL TO ACTION: Do NOT ask for a 30-minute demo. Ask lightweight interest questions "
        "(e.g. 'Open to a 2-minute walkthrough of how regional distributors manage this?' or 'Worth a brief exchange?').\n"
        "4. HARD LIMIT ON LINKEDIN CONNECTION: 'linkedin_variant_a' MUST be strictly under 300 characters total.\n"
        "5. EVIDENCE CITATIONS: In each draft's 'evidence_used' list, cite the exact facts/triggers from research you used.\n"
        "6. OUTPUT FORMAT: Respond strictly in valid JSON adhering to the requested schema. No markdown codeblocks or commentary."
    )

    research_payload = {
        "company_profile": {
            "name": company_name,
            "industry": company_profile.get("industry"),
            "location": company_profile.get("location"),
            "products": company_profile.get("products_services", []),
            "target_customers": company_profile.get("target_customers", []),
            "verified_facts": company_profile.get("verified_facts", []),
        },
        "business_analysis": {
            "crm_relevance_reason": business_analysis.get("crm_relevance", {}).get("reasoning"),
            "pain_points": business_analysis.get("potential_pain_points", []),
            "buying_triggers": business_analysis.get("buying_triggers", []),
            "value_hypotheses": business_analysis.get("value_hypotheses", []),
        },
        "lead_score": {
            "score": score,
            "priority": priority,
        },
    }

    prompt = f"""
Target Lead Intelligence:
{json.dumps(research_payload, indent=2)}

Generate four personalized outreach drafts for SalesFlow CRM adhering strictly to this JSON structure:
{{
  "email_variant_a": {{
    "variant_name": "Direct & Trigger-Led",
    "target_persona": "Head of Sales / Managing Director",
    "subject_line": "Subject line under 7 words",
    "body_text": "75-110 words. Direct hook citing expansion or verified scale, core bottleneck, SalesFlow CRM value, light CTA.",
    "evidence_used": ["Exact facts or triggers cited"]
  }},
  "email_variant_b": {{
    "variant_name": "Consultative & Hypothesis-Led",
    "target_persona": "Commercial Director / Channel Operations Head",
    "subject_line": "Subject line under 7 words",
    "body_text": "120-160 words. Explores operational hypothesis, territory allocation during growth, SalesFlow CRM feature, light CTA.",
    "evidence_used": ["Exact facts or hypotheses cited"]
  }},
  "linkedin_variant_a": {{
    "variant_name": "Connection Request Note",
    "target_persona": "Sales Leadership / Founder",
    "message_text": "Strictly UNDER 280 characters. Friendly, relevant context referencing expansion or distributor scale.",
    "evidence_used": ["Fact cited"]
  }},
  "linkedin_variant_b": {{
    "variant_name": "Conversational InMail Message",
    "target_persona": "Regional Sales Manager / Channel Head",
    "message_text": "50-80 words. Conversational peer tone, short 1-2 sentence paragraphs.",
    "evidence_used": ["Fact cited"]
  }}
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=effective_api_key)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        )

        models_to_try = [model_name]
        for fallback_m in ["gemini-3.8-flash", "gemini-3.5-flash"]:
            if fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        response = None
        last_err = None
        for current_model in models_to_try:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=config,
                    )
                    break
                except Exception as api_err:
                    last_err = api_err
                    err_str = str(api_err)
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "rate" in err_str.lower()) and attempt < 1:
                        time.sleep(2)
                        continue
                    break
            if response is not None:
                break

        if response is None:
            raise last_err or RuntimeError("All model attempts failed")

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        parsed_drafts = json.loads(raw_text)

        output = get_empty_outreach_drafts(
            company_name=company_name,
            website_url=url,
            lead_priority=priority,
            lead_score=score,
            status="success",
            notes="Generated 4 grounded outreach variants with human review status initialized to pending.",
        )

        # Post-processing: Calculate exact word and character counts in Python
        if "email_variant_a" in parsed_drafts:
            draft_a = parsed_drafts["email_variant_a"]
            body = draft_a.get("body_text", "").strip()
            output["drafts"]["email_variant_a"] = {
                "variant_name": "Direct & Trigger-Led",
                "target_persona": draft_a.get("target_persona", "Head of Sales"),
                "subject_line": draft_a.get("subject_line", ""),
                "body_text": body,
                "word_count": len(body.split()),
                "evidence_used": draft_a.get("evidence_used", []),
            }

        if "email_variant_b" in parsed_drafts:
            draft_b = parsed_drafts["email_variant_b"]
            body = draft_b.get("body_text", "").strip()
            output["drafts"]["email_variant_b"] = {
                "variant_name": "Consultative & Hypothesis-Led",
                "target_persona": draft_b.get("target_persona", "Commercial Director"),
                "subject_line": draft_b.get("subject_line", ""),
                "body_text": body,
                "word_count": len(body.split()),
                "evidence_used": draft_b.get("evidence_used", []),
            }

        if "linkedin_variant_a" in parsed_drafts:
            draft_li_a = parsed_drafts["linkedin_variant_a"]
            msg = draft_li_a.get("message_text", "").strip()
            
            # Python Safeguard: Hard trim to strictly <= 300 characters for LinkedIn connection requests
            if len(msg) > 300:
                msg = msg[:295].rsplit(" ", 1)[0] + "..."
                
            output["drafts"]["linkedin_variant_a"] = {
                "variant_name": "Connection Request Note",
                "target_persona": draft_li_a.get("target_persona", "Sales Leadership"),
                "message_text": msg,
                "character_count": len(msg),
                "character_limit": 300,
                "evidence_used": draft_li_a.get("evidence_used", []),
            }

        if "linkedin_variant_b" in parsed_drafts:
            draft_li_b = parsed_drafts["linkedin_variant_b"]
            msg = draft_li_b.get("message_text", "").strip()
            output["drafts"]["linkedin_variant_b"] = {
                "variant_name": "Conversational InMail Message",
                "target_persona": draft_li_b.get("target_persona", "Regional Sales Manager"),
                "message_text": msg,
                "word_count": len(msg.split()),
                "evidence_used": draft_li_b.get("evidence_used", []),
            }

        return output

    except Exception as exc:
        fallback = _heuristic_fallback_outreach(
            company_profile,
            lead_score,
            notes=f"Gemini API outreach generation failed ({type(exc).__name__}: {str(exc)}). Heuristic drafts returned.",
        )
        # Keep partial so humans can still review template drafts when Gemini is rate-limited.
        fallback["generation_status"] = "partial"
        return fallback
