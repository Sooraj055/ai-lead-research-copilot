"""
scorer.py
=========
Deterministic Lead-Scoring Engine for the AI Lead-Research and Outreach Copilot.

This module applies a transparent, mathematical scoring rubric to evaluate
a company's suitability against the 'SalesFlow CRM' Ideal Customer Profile (ICP).

Design Philosophy:
- Pure Python deterministic math: Zero LLM calls, zero token costs, and 100% auditability.
- Avoids arbitrary LLM scoring: The LLM extracts signals in Stage 3; the scorer computes
  the score deterministically using weighted criteria.
- Flags 'Insufficient evidence' when key ICP signals are unknown to prevent false positives.
"""

from typing import Dict, Any, Tuple


# Rubric weight configuration (Total: 100 points)
WEIGHTS = {
    "industry_match": 25,
    "company_size_match": 20,
    "geography_match": 15,
    "sales_complexity": 15,
    "buying_triggers": 15,
    "pain_points_need": 10,
}

# Priority Classification Thresholds
PRIORITY_HIGH_THRESHOLD = 70
PRIORITY_MEDIUM_THRESHOLD = 45


def evaluate_industry(industry_signal: str) -> Tuple[int, str]:
    """Scores industry match signal (Max: 25 pts)."""
    sig = (industry_signal or "").lower()
    if sig == "high":
        return 25, "Priority target industry (Distribution, Manufacturing, FMCG, B2B Services)."
    elif sig == "medium":
        return 15, "Adjacent B2B sector with moderate sales pipeline relevance."
    elif sig == "low":
        return 5, "Low-match industry; minimal standard alignment with target CRM verticals."
    else:
        return 0, "No alignment with target priority industries or non-B2B."


def evaluate_company_size(size_signal: str) -> Tuple[int, str]:
    """Scores company size match signal (Max: 20 pts)."""
    sig = (size_signal or "").lower()
    if sig == "yes":
        return 20, "Optimal SMB scale (10-200 employees, 2-30 sales reps)."
    elif sig == "unknown":
        return 5, "Company headcount is unknown from public data; requires verification."
    else:
        return 0, "Outside target SMB band (e.g. large enterprise >1000 or solo micro-firm)."


def evaluate_geography(geo_signal: str) -> Tuple[int, str]:
    """Scores geography match signal (Max: 15 pts)."""
    sig = (geo_signal or "").lower()
    if sig == "yes":
        return 15, "Headquartered or substantial sales presence in India."
    elif sig == "unknown":
        return 5, "Geographic headquarters or India presence not confirmed."
    else:
        return 0, "Outside target geography (Non-India / foreign territory without local operations)."


def evaluate_sales_complexity(complexity_signal: str) -> Tuple[int, str]:
    """Scores sales complexity and pipeline operational need (Max: 15 pts)."""
    sig = (complexity_signal or "").lower()
    if sig == "high":
        return 15, "High sales complexity (multi-tier distributors, field reps, high follow-up volume)."
    elif sig == "medium":
        return 10, "Moderate sales complexity with standard B2B inquiry tracking."
    elif sig == "low":
        return 5, "Low sales complexity; self-serve or single-transaction model."
    else:
        return 0, "Unknown sales model complexity."


def evaluate_buying_triggers(triggers: list) -> Tuple[int, str]:
    """Scores observable buying triggers signaling urgency (Max: 15 pts)."""
    count = len(triggers) if isinstance(triggers, list) else 0
    if count >= 2:
        return 15, f"{count} active buying triggers verified (e.g. expansion and hiring initiatives)."
    elif count == 1:
        return 10, "1 verified buying trigger identified indicating timely operational change."
    else:
        return 0, "No recent verifiable buying triggers observed in scanned public data."


def evaluate_pain_points(pain_points: list) -> Tuple[int, str]:
    """Scores identified potential business pain points (Max: 10 pts)."""
    if not isinstance(pain_points, list) or len(pain_points) == 0:
        return 0, "No CRM-related operational bottlenecks or pain points identified."
    
    # Check highest confidence level among pain points
    has_high = any(p.get("confidence", "").lower() == "high" for p in pain_points)
    has_med = any(p.get("confidence", "").lower() == "medium" for p in pain_points)
    
    if has_high:
        return 10, f"{len(pain_points)} pain points identified with high contextual confidence."
    elif has_med:
        return 6, f"{len(pain_points)} pain points identified with moderate contextual confidence."
    else:
        return 3, f"{len(pain_points)} pain points identified with low confidence."


def score_lead(business_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a transparent, deterministic 0-100 ICP fit score for a lead.

    Args:
        business_analysis (dict): Structured output from Stage 3 analyze_company_crm_fit().

    Returns:
        dict: Structured lead score object with total score, individual criteria breakdown,
              priority tier ('High priority', 'Medium priority', 'Low priority'),
              and confidence indicator ('High confidence', 'Medium confidence', 'Insufficient evidence').
    """
    company_name = business_analysis.get("company_name", "Unknown Company")
    url = business_analysis.get("website_url", "")
    
    # Handle failed or missing incoming business analysis
    if business_analysis.get("analysis_status") == "failed":
        return {
            "company_name": company_name,
            "website_url": url,
            "total_score": 0,
            "max_score": 100,
            "priority": "Low priority",
            "confidence_level": "Insufficient evidence",
            "scoring_breakdown": {},
            "summary_recommendation": "Scoring aborted: Upstream business analysis failed.",
            "score_status": "failed",
            "scoring_notes": business_analysis.get("analysis_notes", "Analysis failed."),
        }

    crm_rel = business_analysis.get("crm_relevance", {})
    icp_signals = crm_rel.get("icp_signals", {})
    
    geo_sig = icp_signals.get("geography_match", "unknown")
    ind_sig = icp_signals.get("industry_match", "none")
    size_sig = icp_signals.get("company_size_match", "unknown")
    complexity_sig = icp_signals.get("sales_complexity_signal", "unknown")
    
    triggers = business_analysis.get("buying_triggers", [])
    pain_points = business_analysis.get("potential_pain_points", [])

    # Step 1: Calculate criterion scores
    ind_score, ind_reason = evaluate_industry(ind_sig)
    size_score, size_reason = evaluate_company_size(size_sig)
    geo_score, geo_reason = evaluate_geography(geo_sig)
    complexity_score, complexity_reason = evaluate_sales_complexity(complexity_sig)
    trigger_score, trigger_reason = evaluate_buying_triggers(triggers)
    pain_score, pain_reason = evaluate_pain_points(pain_points)

    total_score = (
        ind_score + size_score + geo_score + complexity_score + trigger_score + pain_score
    )

    # Step 2: Determine Priority Tier
    if total_score >= PRIORITY_HIGH_THRESHOLD:
        priority = "High priority"
    elif total_score >= PRIORITY_MEDIUM_THRESHOLD:
        priority = "Medium priority"
    else:
        priority = "Low priority"

    # Step 3: Check for Insufficient Evidence Flag
    # Count how many critical ICP signals are "unknown"
    unknown_signals = [
        sig_name for sig_name, val in [
            ("geography", geo_sig),
            ("company_size", size_sig),
            ("sales_complexity", complexity_sig),
        ] if val.lower() == "unknown"
    ]

    if len(unknown_signals) >= 2:
        confidence = "Insufficient evidence"
        rec = (
            f"Caution: {len(unknown_signals)} critical signals ({', '.join(unknown_signals)}) are unknown. "
            "Manual qualification required before sales outreach."
        )
    elif priority == "High priority":
        confidence = "High confidence"
        rec = "Strong ICP match across all operational dimensions. High priority candidate for SalesFlow CRM outreach."
    elif priority == "Medium priority":
        confidence = "Medium confidence"
        rec = "Moderate ICP fit. Investigate remaining information gaps before initiating outreach."
    else:
        confidence = "High confidence"
        rec = "Low ICP fit. Unfavorable company size, non-target industry, or enterprise non-fit."

    return {
        "company_name": company_name,
        "website_url": url,
        "total_score": total_score,
        "max_score": 100,
        "priority": priority,
        "confidence_level": confidence,
        "scoring_breakdown": {
            "industry_match": {
                "score": ind_score,
                "max": WEIGHTS["industry_match"],
                "signal": ind_sig,
                "reasoning": ind_reason,
            },
            "company_size_match": {
                "score": size_score,
                "max": WEIGHTS["company_size_match"],
                "signal": size_sig,
                "reasoning": size_reason,
            },
            "geography_match": {
                "score": geo_score,
                "max": WEIGHTS["geography_match"],
                "signal": geo_sig,
                "reasoning": geo_reason,
            },
            "sales_complexity": {
                "score": complexity_score,
                "max": WEIGHTS["sales_complexity"],
                "signal": complexity_sig,
                "reasoning": complexity_reason,
            },
            "buying_triggers": {
                "score": trigger_score,
                "max": WEIGHTS["buying_triggers"],
                "signal": f"{len(triggers)} trigger(s)",
                "reasoning": trigger_reason,
            },
            "pain_points_need": {
                "score": pain_score,
                "max": WEIGHTS["pain_points_need"],
                "signal": f"{len(pain_points)} pain point(s)",
                "reasoning": pain_reason,
            },
        },
        "summary_recommendation": rec,
        "score_status": "success",
        "scoring_notes": f"Deterministic score calculated based on Stage 3 business analysis signals. Unknown signals: {len(unknown_signals)}.",
    }
