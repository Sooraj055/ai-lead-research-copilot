"""
evaluate_copilot.py
===================
Phase 8 empirical benchmark for the AI Lead-Research and Outreach Copilot.

Evaluates a mixed lead set (Indian distributors, food processors, manufacturers,
B2B SaaS, enterprise non-fits, and intentional failure controls).

Measures:
1. Exact wall-clock execution time per lead vs. assumed manual SDR baseline (15.0 mins).
2. Scrape success rate and categorized failure modes (DNS, HTTP, SSL, timeouts).
3. Score distribution (High, Medium, Low) and 'Insufficient evidence' flags.
4. Token-saving low-priority outreach skips.
5. Control-case human review grades plus blank columns for live ICP audit.

Outputs:
- data/evaluation_results.csv
- data/evaluation_summary.json
- EVALUATION.md
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Unbuffered UTF-8 logs so long Gemini calls still show progress on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from research import (
    scrape_website,
    extract_company_info,
    analyze_company_crm_fit,
    score_lead,
    generate_outreach_drafts,
)
from research.evaluation import (
    MANUAL_BASELINE_MINUTES,
    apply_control_case_review,
    build_summary,
    categorize_scrape_failure,
    empty_failure_counts,
    increment_failure_counts,
    render_evaluation_markdown,
    write_json,
)


def _blank_human_fields() -> dict:
    return {
        "actual_manual_minutes_recorded": "",
        "human_research_accuracy_grade": "",
        "human_pain_point_relevance_grade": "",
        "human_trigger_accuracy_grade": "",
        "human_draft_accepted_without_edits": "",
        "human_hallucination_detected": "",
        "human_reviewer_notes": "",
    }


def run_benchmark(limit: int | None = None) -> None:
    input_csv = Path("data") / "evaluation_leads.csv"
    assert input_csv.exists(), f"Input dataset {input_csv} does not exist!"

    df = pd.read_csv(input_csv)
    if limit is not None:
        df = df.head(limit)

    total_leads = len(df)

    print("\n" + "=" * 75)
    print(f"   STARTING COPILOT EVALUATION BENCHMARK ({total_leads} COMPANIES)")
    print("=" * 75)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Assumed manual SDR baseline per lead: {MANUAL_BASELINE_MINUTES} minutes\n")

    results = []
    failure_counts = empty_failure_counts()
    successful_scrapes = 0
    total_copilot_runtimes = []

    for idx, row in df.iterrows():
        lead_num = idx + 1
        name_expected = row["company_name"]
        url = row["website_url"]
        category = row["expected_category"]
        notes = str(row.get("test_notes", "") or "")

        print(f"[{lead_num}/{total_leads}] Evaluating: {name_expected} ({url}) ...")
        lead_start_time = time.perf_counter()

        scrape_start = time.perf_counter()
        scraped = scrape_website(url, timeout=12)
        scrape_duration = round(time.perf_counter() - scrape_start, 2)

        if scraped["status"] == "error":
            fail_mode = categorize_scrape_failure(
                scraped.get("error_message", ""), scraped.get("http_status")
            )
            increment_failure_counts(failure_counts, fail_mode)

            total_runtime = round(time.perf_counter() - lead_start_time, 2)
            total_copilot_runtimes.append(total_runtime)
            print(f"  Scraping failed: {scraped.get('error_message')} ({total_runtime}s)")

            record = {
                "company_name": name_expected,
                "website_url": url,
                "expected_category": category,
                "scrape_status": fail_mode,
                "scrape_time_seconds": scrape_duration,
                "extracted_char_count": 0,
                "extraction_status": "skipped",
                "analysis_status": "skipped",
                "crm_relevance_classification": "N/A",
                "buying_triggers_detected": 0,
                "icp_score": 0,
                "priority_tier": "Unscored (Failed Scrape)",
                "confidence_level": "N/A",
                "outreach_status": "failed",
                "copilot_runtime_seconds": total_runtime,
                "assumed_manual_baseline_minutes": MANUAL_BASELINE_MINUTES,
                "time_saved_minutes": round(MANUAL_BASELINE_MINUTES - (total_runtime / 60), 2),
                **_blank_human_fields(),
            }
            record["human_reviewer_notes"] = f"Scrape failed: {scraped.get('error_message')}"
            results.append(apply_control_case_review(record))
            continue

        if scraped.get("char_count", 0) < 50:
            failure_counts["insufficient_content"] += 1
            total_runtime = round(time.perf_counter() - lead_start_time, 2)
            total_copilot_runtimes.append(total_runtime)
            print(f"  Sparse content: {scraped.get('char_count')} chars ({total_runtime}s)")

            record = {
                "company_name": name_expected,
                "website_url": url,
                "expected_category": category,
                "scrape_status": "insufficient_content",
                "scrape_time_seconds": scrape_duration,
                "extracted_char_count": scraped.get("char_count", 0),
                "extraction_status": "skipped",
                "analysis_status": "skipped",
                "crm_relevance_classification": "Insufficient information",
                "buying_triggers_detected": 0,
                "icp_score": 0,
                "priority_tier": "Low priority",
                "confidence_level": "Insufficient evidence",
                "outreach_status": "skipped_low_priority",
                "copilot_runtime_seconds": total_runtime,
                "assumed_manual_baseline_minutes": MANUAL_BASELINE_MINUTES,
                "time_saved_minutes": round(MANUAL_BASELINE_MINUTES - (total_runtime / 60), 2),
                **_blank_human_fields(),
            }
            record["human_reviewer_notes"] = "Website returned minimal or sparse text."
            results.append(apply_control_case_review(record))
            continue

        successful_scrapes += 1

        profile = extract_company_info(scraped)
        analysis = analyze_company_crm_fit(
            profile, additional_research=notes if notes else None
        )
        crm_rel = analysis.get("crm_relevance", {}).get("classification", "Unknown")
        triggers_count = len(analysis.get("buying_triggers", []) or [])

        lead_score_data = score_lead(analysis)
        score_val = lead_score_data.get("total_score", 0)
        priority = lead_score_data.get("priority", "Low priority")
        confidence = lead_score_data.get("confidence_level", "Medium confidence")

        outreach = generate_outreach_drafts(profile, analysis, lead_score_data)
        outreach_status = outreach.get("generation_status", "failed")

        total_runtime = round(time.perf_counter() - lead_start_time, 2)
        total_copilot_runtimes.append(total_runtime)

        print(
            f"  Evaluated: Score {score_val}/100 ({priority}) | "
            f"Triggers: {triggers_count} | Outreach: {outreach_status.upper()} ({total_runtime}s)"
        )

        record = {
            "company_name": name_expected,
            "website_url": url,
            "expected_category": category,
            "scrape_status": "success",
            "scrape_time_seconds": scrape_duration,
            "extracted_char_count": scraped.get("char_count", 0),
            "extraction_status": profile.get("extraction_status", ""),
            "analysis_status": analysis.get("analysis_status", ""),
            "crm_relevance_classification": crm_rel,
            "buying_triggers_detected": triggers_count,
            "icp_score": score_val,
            "priority_tier": priority,
            "confidence_level": confidence,
            "outreach_status": outreach_status,
            "copilot_runtime_seconds": total_runtime,
            "assumed_manual_baseline_minutes": MANUAL_BASELINE_MINUTES,
            "time_saved_minutes": round(MANUAL_BASELINE_MINUTES - (total_runtime / 60), 2),
            **_blank_human_fields(),
        }
        results.append(apply_control_case_review(record))
        time.sleep(2.5)

    results_df = pd.DataFrame(results)
    output_csv = Path("data") / "evaluation_results.csv"
    results_df.to_csv(output_csv, index=False)
    print(f"\n[Saved per-lead results to: {output_csv}]")

    summary_data = build_summary(
        results_df,
        total_leads,
        successful_scrapes,
        failure_counts,
        total_copilot_runtimes,
    )
    summary_json_file = Path("data") / "evaluation_summary.json"
    write_json(summary_json_file, summary_data)
    print(f"[Saved benchmark summary to: {summary_json_file}]")

    report_path = Path("EVALUATION.md")
    report_path.write_text(
        render_evaluation_markdown(summary_data, results_df), encoding="utf-8"
    )
    print(f"[Saved evaluation report to: {report_path}]")

    dist = summary_data["score_distribution"]
    bench = summary_data["performance_benchmarks"]
    print("\n" + "=" * 75)
    print("   BENCHMARK EVALUATION SUMMARY")
    print("=" * 75)
    print(f"Total Companies Evaluated:       {total_leads}")
    print(
        f"Scrape Success Rate:             {summary_data['scraping_success_rate_percent']}% "
        f"({successful_scrapes}/{total_leads})"
    )
    print(f"Failures Breakdown:              {failure_counts}")
    print(f"High Priority Leads (Score >=70):{dist['high_priority_count']}")
    print(f"Medium Priority Leads (45-69):   {dist['medium_priority_count']}")
    print(f"Low Priority Leads (<45):        {dist['low_priority_count']}")
    print(f"Token-Saving Low-Priority Skips: {summary_data['token_saving_low_priority_skips']}")
    print(
        f"Average Copilot Time per Lead:   {bench['copilot_average_seconds_per_lead']} seconds "
        f"(~{bench['copilot_average_minutes_per_lead']} mins)"
    )
    print(
        f"Average Time Saved vs Manual:    {bench['average_time_saved_per_lead_minutes']} minutes "
        f"({bench['average_time_reduction_percentage']}% reduction)"
    )
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stage 8 copilot evaluation benchmark.")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N rows.")
    args = parser.parse_args()
    run_benchmark(limit=args.limit)
