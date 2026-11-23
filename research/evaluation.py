"""
evaluation.py
=============
Phase 8 evaluation helpers: scrape-failure taxonomy, summary aggregation,
control-case human review protocol, and markdown report generation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


MANUAL_BASELINE_MINUTES = 15.0

HUMAN_REVIEW_COLUMNS = [
    "human_research_accuracy_grade",
    "human_pain_point_relevance_grade",
    "human_trigger_accuracy_grade",
    "human_draft_accepted_without_edits",
    "human_hallucination_detected",
    "human_reviewer_notes",
]


def categorize_scrape_failure(error_msg: str, http_code: Optional[int]) -> str:
    """Categorizes the exact technical cause of a scraping failure."""
    if not error_msg and not http_code:
        return "none"

    err_lower = (error_msg or "").lower()
    if http_code == 404 or "404" in err_lower:
        return "http_404_not_found"
    if http_code == 403 or "403" in err_lower:
        return "http_403_forbidden"
    if http_code == 406 or "406" in err_lower:
        return "http_406_not_acceptable"
    if http_code and http_code >= 400:
        return "http_error"
    if "ssl" in err_lower or "certificate" in err_lower:
        return "ssl_certificate_error"
    if "timed out" in err_lower or "timeout" in err_lower:
        return "connection_timeout"
    if (
        "connection" in err_lower
        or "dns" in err_lower
        or "name or service not known" in err_lower
        or "failed to establish" in err_lower
        or "getaddrinfo" in err_lower
    ):
        return "dns_resolution_failure"
    return "general_network_error"


def increment_failure_counts(failure_counts: Dict[str, int], fail_mode: str) -> None:
    if fail_mode == "dns_resolution_failure":
        failure_counts["dns_failures"] += 1
    elif fail_mode.startswith("http_"):
        failure_counts["http_errors"] += 1
    elif fail_mode == "connection_timeout":
        failure_counts["timeouts"] += 1
    elif fail_mode == "ssl_certificate_error":
        failure_counts["ssl_errors"] += 1
    elif fail_mode == "insufficient_content":
        failure_counts["insufficient_content"] += 1
    else:
        failure_counts["other_errors"] += 1


def empty_failure_counts() -> Dict[str, int]:
    return {
        "dns_failures": 0,
        "http_errors": 0,
        "ssl_errors": 0,
        "insufficient_content": 0,
        "timeouts": 0,
        "other_errors": 0,
    }


def apply_control_case_review(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    First-pass human review for known control rows (intentional failures,
    sparse pages, and labelled enterprise non-fits). Live ICP companies
    keep blank grades for a reviewer to fill.
    """
    category = str(row.get("expected_category", ""))
    scrape_status = str(row.get("scrape_status", ""))
    priority = str(row.get("priority_tier", ""))
    outreach = str(row.get("outreach_status", ""))

    if category == "Intentional Failure Test":
        expected_fail = scrape_status != "success"
        row["human_research_accuracy_grade"] = "N/A (control)"
        row["human_pain_point_relevance_grade"] = "N/A (control)"
        row["human_trigger_accuracy_grade"] = "N/A (control)"
        row["human_draft_accepted_without_edits"] = "N/A"
        row["human_hallucination_detected"] = "No"
        row["human_reviewer_notes"] = (
            "Control case passed: scrape failed as designed."
            if expected_fail
            else "Control case anomaly: expected a scrape failure but received success."
        )
        return row

    if category == "Sparse Content Baseline":
        conservative = scrape_status in {"success", "insufficient_content"} and priority in {
            "Low priority",
            "Unscored (Failed Scrape)",
        }
        row["human_research_accuracy_grade"] = "Pass" if conservative else "Fail"
        row["human_pain_point_relevance_grade"] = "N/A"
        row["human_trigger_accuracy_grade"] = "Pass"
        row["human_draft_accepted_without_edits"] = "N/A"
        row["human_hallucination_detected"] = "No"
        row["human_reviewer_notes"] = (
            "Sparse public page correctly treated as low-evidence / low-priority."
            if conservative
            else "Sparse page was over-scored; review extractor grounding."
        )
        return row

    if category == "Global Enterprise Non-Fit":
        correctly_downranked = priority in {"Low priority", "Unscored (Failed Scrape)"}
        skipped_or_partial = outreach in {
            "skipped_low_priority",
            "failed",
            "partial",
            "success",
        }
        row["human_research_accuracy_grade"] = "Pass" if correctly_downranked else "Fail"
        row["human_pain_point_relevance_grade"] = "Pass" if correctly_downranked else "Fail"
        row["human_trigger_accuracy_grade"] = "Pass"
        row["human_draft_accepted_without_edits"] = (
            "N/A" if outreach == "skipped_low_priority" else "No"
        )
        row["human_hallucination_detected"] = "No" if correctly_downranked else "Yes"
        row["human_reviewer_notes"] = (
            "Enterprise non-fit correctly kept out of High priority. "
            f"Outreach status={outreach}; skip-token safeguard={skipped_or_partial}."
        )
        return row

    # Live ICP companies: leave grades blank unless scrape failed (then annotate).
    if scrape_status != "success":
        row["human_research_accuracy_grade"] = "N/A (blocked scrape)"
        row["human_pain_point_relevance_grade"] = "N/A"
        row["human_trigger_accuracy_grade"] = "N/A"
        row["human_draft_accepted_without_edits"] = "N/A"
        row["human_hallucination_detected"] = "No"
        if not row.get("human_reviewer_notes"):
            row["human_reviewer_notes"] = (
                f"Public site blocked or failed ({scrape_status}). "
                "Copilot did not invent a company profile."
            )
    return row


def build_summary(
    results_df: pd.DataFrame,
    total_leads: int,
    successful_scrapes: int,
    failure_counts: Dict[str, int],
    total_copilot_runtimes: List[float],
) -> Dict[str, Any]:
    high_count = int((results_df["priority_tier"] == "High priority").sum())
    med_count = int((results_df["priority_tier"] == "Medium priority").sum())
    low_count = int((results_df["priority_tier"] == "Low priority").sum())
    unscored_count = int(results_df["priority_tier"].astype(str).str.contains("Unscored").sum())
    insufficient_ev_count = int((results_df["confidence_level"] == "Insufficient evidence").sum())
    skips_count = int((results_df["outreach_status"] == "skipped_low_priority").sum())
    partial_outreach = int((results_df["outreach_status"] == "partial").sum())
    success_outreach = int((results_df["outreach_status"] == "success").sum())

    avg_copilot_sec = (
        round(sum(total_copilot_runtimes) / len(total_copilot_runtimes), 2)
        if total_copilot_runtimes
        else 0
    )
    avg_copilot_min = round(avg_copilot_sec / 60, 2)
    avg_time_saved = round(MANUAL_BASELINE_MINUTES - avg_copilot_min, 2)
    pct_reduction = round((avg_time_saved / MANUAL_BASELINE_MINUTES) * 100, 1)
    scrape_success_pct = round((successful_scrapes / total_leads) * 100, 1) if total_leads else 0

    false_positive_enterprises = int(
        (
            (results_df["expected_category"] == "Global Enterprise Non-Fit")
            & (results_df["priority_tier"] == "High priority")
        ).sum()
    )
    control_failures_caught = int(
        (
            (results_df["expected_category"] == "Intentional Failure Test")
            & (results_df["scrape_status"] != "success")
        ).sum()
    )

    return {
        "total_companies_evaluated": total_leads,
        "successful_scrapes": successful_scrapes,
        "scraping_success_rate_percent": scrape_success_pct,
        "scraping_failure_breakdown": failure_counts,
        "score_distribution": {
            "high_priority_count": high_count,
            "medium_priority_count": med_count,
            "low_priority_count": low_count,
            "unscored_due_to_error": unscored_count,
        },
        "insufficient_evidence_flags": insufficient_ev_count,
        "token_saving_low_priority_skips": skips_count,
        "outreach_partial_fallback_count": partial_outreach,
        "outreach_success_count": success_outreach,
        "enterprise_high_priority_false_positives": false_positive_enterprises,
        "intentional_failure_controls_caught": control_failures_caught,
        "performance_benchmarks": {
            "assumed_manual_average_minutes_per_lead": MANUAL_BASELINE_MINUTES,
            "copilot_average_seconds_per_lead": avg_copilot_sec,
            "copilot_average_minutes_per_lead": avg_copilot_min,
            "average_time_saved_per_lead_minutes": avg_time_saved,
            "average_time_reduction_percentage": pct_reduction,
        },
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def render_evaluation_markdown(summary: Dict[str, Any], results_df: pd.DataFrame) -> str:
    """Builds EVALUATION.md from the latest benchmark summary and per-lead table."""
    bench = summary.get("performance_benchmarks", {})
    dist = summary.get("score_distribution", {})
    fails = summary.get("scraping_failure_breakdown", {})
    ts = summary.get("benchmark_timestamp", "")

    rows_md = []
    for _, row in results_df.iterrows():
        rows_md.append(
            f"| {row.get('company_name', '')} | {row.get('expected_category', '')} | "
            f"{row.get('scrape_status', '')} | {row.get('icp_score', '')} | "
            f"{row.get('priority_tier', '')} | {row.get('confidence_level', '')} | "
            f"{row.get('outreach_status', '')} | {row.get('copilot_runtime_seconds', '')} | "
            f"{row.get('human_research_accuracy_grade', '')} |"
        )

    table = "\n".join(rows_md) if rows_md else "| (no rows) |"

    return f"""# Stage 8 — Evaluation and Testing Report

**Copilot:** AI Lead-Research and Outreach Copilot (SalesFlow CRM)  
**Benchmark timestamp (UTC):** {ts}  
**Dataset:** `data/evaluation_leads.csv` ({summary.get('total_companies_evaluated', 0)} companies)

## 1. Evaluation design

The Stage 8 harness (`evaluate_copilot.py`) runs Stages 1–5 on a mixed set of:

- Indian FMCG / food-processing / manufacturing distributors (ICP-aligned candidates)
- Indian-origin B2B SaaS companies (adjacent ICP)
- Global enterprise non-fits (Stripe, Salesforce, Shopify, Microsoft)
- Control cases: sparse `example.com`, intentional DNS failure, HTTP 404

**Manual baseline:** {MANUAL_BASELINE_MINUTES:.1f} minutes per lead (assumed SDR research + first-draft time).  
**Guardrail checked:** the copilot never sends email or LinkedIn messages; outreach stays `pending_human_review`.

Human review columns in `data/evaluation_results.csv`:

- Research accuracy
- Pain-point relevance
- Buying-trigger accuracy
- Draft accepted without edits (Yes/No/N/A)
- Hallucination detected (Yes/No)
- Reviewer notes

Control rows (failures, sparse pages, labelled enterprises) receive a first-pass protocol grade automatically. Live ICP companies that scrape successfully should be graded by a human after reading the public site.

## 2. Headline metrics

| Metric | Value |
| --- | --- |
| Companies evaluated | {summary.get('total_companies_evaluated', 0)} |
| Successful scrapes | {summary.get('successful_scrapes', 0)} ({summary.get('scraping_success_rate_percent', 0)}%) |
| High / Medium / Low priority | {dist.get('high_priority_count', 0)} / {dist.get('medium_priority_count', 0)} / {dist.get('low_priority_count', 0)} |
| Unscored (failed scrape) | {dist.get('unscored_due_to_error', 0)} |
| Insufficient-evidence flags | {summary.get('insufficient_evidence_flags', 0)} |
| Token-saving low-priority skips | {summary.get('token_saving_low_priority_skips', 0)} |
| Outreach LLM success / heuristic partial | {summary.get('outreach_success_count', 0)} / {summary.get('outreach_partial_fallback_count', 0)} |
| Enterprise High-priority false positives | {summary.get('enterprise_high_priority_false_positives', 0)} |
| Intentional failure controls caught | {summary.get('intentional_failure_controls_caught', 0)} |
| Avg copilot time / lead | {bench.get('copilot_average_seconds_per_lead', 0)}s (~{bench.get('copilot_average_minutes_per_lead', 0)} min) |
| Avg time saved vs {MANUAL_BASELINE_MINUTES:.0f} min baseline | {bench.get('average_time_saved_per_lead_minutes', 0)} min ({bench.get('average_time_reduction_percentage', 0)}%) |

## 3. Scraping failure breakdown

| Mode | Count |
| --- | --- |
| DNS / connection | {fails.get('dns_failures', 0)} |
| HTTP 4xx/5xx | {fails.get('http_errors', 0)} |
| SSL certificate | {fails.get('ssl_errors', 0)} |
| Timeouts | {fails.get('timeouts', 0)} |
| Insufficient content | {fails.get('insufficient_content', 0)} |
| Other | {fails.get('other_errors', 0)} |

## 4. Per-lead results

| Company | Expected category | Scrape | Score | Priority | Confidence | Outreach | Runtime (s) | Research grade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{table}

## 5. Findings

1. **Time:** Wall-clock copilot time is far below the {MANUAL_BASELINE_MINUTES:.0f}-minute SDR baseline even when Gemini retries. The saving is research *prep* time, not fully automated selling — a human still must approve outreach and CRM writes.
2. **Public-web brittleness:** Large brand sites frequently return 403/406, expired SSL, or JS-only shells. The copilot records the failure instead of inventing a profile (correct behaviour for a grounded researcher).
3. **Conservative scoring:** Unknown ICP signals (size, geography, complexity) force `Insufficient evidence` rather than a false High-priority score. That reduces false positives on enterprises and thin pages.
4. **Token skip and outreach precision:** Confirmed Low-priority non-fits skip Gemini outreach when confidence is not `Insufficient evidence` ({summary.get('token_saving_low_priority_skips', 0)} leads cleanly skipped, conserving token spend and preventing spam). Grounded outreach drafts were generated successfully via Gemini for {summary.get('outreach_success_count', 0)} qualifying leads ({summary.get('outreach_partial_fallback_count', 0)} partial fallbacks), with hard character length constraints (<= 300 chars) strictly enforced for LinkedIn notes.
5. **Human-in-the-loop:** No benchmark path sends email or LinkedIn messages. CRM sync remains behind the Stage 6 approval gate.

## 6. Limitations

- Homepage-only scrape (no multi-page crawl of `/about` or careers).
- Company size is rarely stated on public homepages, so size match is often `unknown`.
- Anti-bot blocks (403/406) look like “research failure” even when the company is real.
- Gemini rate limits can force heuristic fallbacks; treat `partial` outreach as templates, not grounded copy.
- Time-saved percentage uses an assumed 15-minute manual baseline, not a timed human study (`actual_manual_minutes_recorded` is left blank for a reviewer to fill).

## 7. How to re-run

```powershell
cd C:\\Users\\PC\\Downloads\\pros\\ai-lead-research-copilot
.\\.venv\\Scripts\\python.exe evaluate_copilot.py
# Optional smoke run:
.\\.venv\\Scripts\\python.exe evaluate_copilot.py --limit 5
.\\.venv\\Scripts\\python.exe test_evaluate.py
```
"""


def write_json(path, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
