"""
test_evaluate.py
================
Automated test suite for evaluation helpers (no live network, no Gemini calls).
"""

from research.evaluation import (
    apply_control_case_review,
    build_summary,
    categorize_scrape_failure,
    empty_failure_counts,
    increment_failure_counts,
)
import pandas as pd


def test_failure_taxonomy():
    print("\n[TEST 1] Scrape failure taxonomy...")
    assert categorize_scrape_failure("HTTP status code 404 (Not Found)", 404) == "http_404_not_found"
    assert categorize_scrape_failure("HTTP status code 403 (Forbidden)", 403) == "http_403_forbidden"
    assert categorize_scrape_failure("HTTP status code 406 (Not Acceptable)", 406) == "http_406_not_acceptable"
    assert (
        categorize_scrape_failure("SSL Certificate verification failed: hostname mismatch", None)
        == "ssl_certificate_error"
    )
    assert (
        categorize_scrape_failure("Failed to establish a connection. Check the domain name", None)
        == "dns_resolution_failure"
    )
    assert categorize_scrape_failure("Connection timed out after 12 seconds", None) == "connection_timeout"
    print("  Passed.")


def test_control_reviews():
    print("\n[TEST 2] Control-case human review protocol...")
    dns_row = apply_control_case_review(
        {
            "company_name": "Fake Co",
            "expected_category": "Intentional Failure Test",
            "scrape_status": "dns_resolution_failure",
            "priority_tier": "Unscored (Failed Scrape)",
            "outreach_status": "failed",
        }
    )
    assert dns_row["human_hallucination_detected"] == "No"
    assert "Control case passed" in dns_row["human_reviewer_notes"]

    sparse = apply_control_case_review(
        {
            "company_name": "Example Domain",
            "expected_category": "Sparse Content Baseline",
            "scrape_status": "success",
            "priority_tier": "Low priority",
            "outreach_status": "partial",
        }
    )
    assert sparse["human_research_accuracy_grade"] == "Pass"

    stripe = apply_control_case_review(
        {
            "company_name": "Stripe",
            "expected_category": "Global Enterprise Non-Fit",
            "scrape_status": "success",
            "priority_tier": "High priority",
            "outreach_status": "success",
        }
    )
    assert stripe["human_research_accuracy_grade"] == "Fail"
    assert stripe["human_hallucination_detected"] == "Yes"

    salesforce = apply_control_case_review(
        {
            "company_name": "Salesforce",
            "expected_category": "Global Enterprise Non-Fit",
            "scrape_status": "http_403_forbidden",
            "priority_tier": "Unscored (Failed Scrape)",
            "outreach_status": "failed",
        }
    )
    assert salesforce["human_research_accuracy_grade"] == "Pass"
    print("  Passed.")


def test_summary_math():
    print("\n[TEST 3] Summary aggregation...")
    df = pd.DataFrame(
        [
            {
                "priority_tier": "High priority",
                "confidence_level": "High confidence",
                "outreach_status": "success",
                "expected_category": "Indian FMCG Food Manufacturer",
                "scrape_status": "success",
            },
            {
                "priority_tier": "Low priority",
                "confidence_level": "High confidence",
                "outreach_status": "skipped_low_priority",
                "expected_category": "Global Enterprise Non-Fit",
                "scrape_status": "success",
            },
            {
                "priority_tier": "Unscored (Failed Scrape)",
                "confidence_level": "N/A",
                "outreach_status": "failed",
                "expected_category": "Intentional Failure Test",
                "scrape_status": "http_404_not_found",
            },
        ]
    )
    counts = empty_failure_counts()
    increment_failure_counts(counts, "http_404_not_found")
    summary = build_summary(df, total_leads=3, successful_scrapes=2, failure_counts=counts, total_copilot_runtimes=[10.0, 20.0, 1.0])
    assert summary["total_companies_evaluated"] == 3
    assert summary["score_distribution"]["high_priority_count"] == 1
    assert summary["token_saving_low_priority_skips"] == 1
    assert summary["enterprise_high_priority_false_positives"] == 0
    assert summary["intentional_failure_controls_caught"] == 1
    assert summary["performance_benchmarks"]["copilot_average_seconds_per_lead"] == 10.33
    print("  Passed.")


def main():
    print("=== Running Evaluation Helper Test Suite ===")
    test_failure_taxonomy()
    test_control_reviews()
    test_summary_math()
    print("\nAll Evaluation helper tests completed successfully!")


if __name__ == "__main__":
    main()
