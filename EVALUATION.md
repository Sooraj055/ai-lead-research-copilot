# Stage 8 — Evaluation and Testing Report

**Copilot:** AI Lead-Research and Outreach Copilot (SalesFlow CRM)  
**Benchmark timestamp (UTC):** 2026-11-23T12:37:49.907285+00:00  
**Dataset:** `data/evaluation_leads.csv` (22 companies)

## 1. Evaluation design

The Stage 8 harness (`evaluate_copilot.py`) runs Stages 1–5 on a mixed set of:

- Indian FMCG / food-processing / manufacturing distributors (ICP-aligned candidates)
- Indian-origin B2B SaaS companies (adjacent ICP)
- Global enterprise non-fits (Stripe, Salesforce, Shopify, Microsoft)
- Control cases: sparse `example.com`, intentional DNS failure, HTTP 404

**Manual baseline:** 15.0 minutes per lead (assumed SDR research + first-draft time).  
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
| Companies evaluated | 22 |
| Successful scrapes | 15 (68.2%) |
| High / Medium / Low priority | 1 / 8 / 7 |
| Unscored (failed scrape) | 6 |
| Insufficient-evidence flags | 2 |
| Token-saving low-priority skips | 6 |
| Outreach LLM success / heuristic partial | 10 / 0 |
| Enterprise High-priority false positives | 0 |
| Intentional failure controls caught | 2 |
| Avg copilot time / lead | 6.63s (~0.11 min) |
| Avg time saved vs 15 min baseline | 14.89 min (99.3%) |

## 3. Scraping failure breakdown

| Mode | Count |
| --- | --- |
| DNS / connection | 1 |
| HTTP 4xx/5xx | 3 |
| SSL certificate | 1 |
| Timeouts | 1 |
| Insufficient content | 1 |
| Other | 0 |

## 4. Per-lead results

| Company | Expected category | Scrape | Score | Priority | Confidence | Outreach | Runtime (s) | Research grade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Synthite Industries | Indian B2B Agro/Spice Exporter | success | 51 | Medium priority | Medium confidence | success | 9.84 | nan |
| Haldiram Snacks | Indian FMCG Food Manufacturer | success | 41 | Low priority | High confidence | skipped_low_priority | 7.24 | nan |
| Bikaji Foods | Indian FMCG Food Distributor | success | 51 | Medium priority | Medium confidence | success | 9.48 | nan |
| Everest Spices | Indian FMCG Wholesale Distributor | success | 61 | Medium priority | Medium confidence | success | 9.04 | nan |
| MDH Spices | Indian FMCG Wholesale Distributor | success | 66 | Medium priority | Medium confidence | success | 9.07 | nan |
| Parle Products | Indian FMCG Food Manufacturer | success | 71 | High priority | High confidence | success | 9.49 | nan |
| LT Foods (Daawat) | Indian Food Processing & Distribution | ssl_certificate_error | 0 | Unscored (Failed Scrape) | nan | failed | 0.97 | N/A (blocked scrape) |
| V-Guard Industries | Indian Electrical Manufacturer | success | 61 | Medium priority | Medium confidence | success | 8.57 | nan |
| Havells India | Indian Electrical Manufacturer | http_406_not_acceptable | 0 | Unscored (Failed Scrape) | nan | failed | 0.44 | N/A (blocked scrape) |
| Tata Consumer Products | Indian FMCG Enterprise | success | 51 | Medium priority | Medium confidence | success | 11.9 | nan |
| Postman | B2B Developer SaaS | success | 55 | Medium priority | Medium confidence | success | 12.02 | nan |
| BrowserStack | B2B Cloud Software SaaS | success | 56 | Medium priority | Medium confidence | success | 9.66 | nan |
| CleverTap | B2B Customer Engagement SaaS | success | 43 | Low priority | High confidence | skipped_low_priority | 6.91 | nan |
| Khatabook | Indian Merchant Utility SaaS | insufficient_content | 0 | Low priority | Insufficient evidence | skipped_low_priority | 1.19 | N/A (blocked scrape) |
| Zoho Corporation | B2B Software Enterprise | success | 30 | Low priority | High confidence | skipped_low_priority | 5.04 | nan |
| Stripe | Global Enterprise Non-Fit | success | 31 | Low priority | High confidence | skipped_low_priority | 6.93 | Pass |
| Salesforce | Global Enterprise Non-Fit | http_403_forbidden | 0 | Unscored (Failed Scrape) | nan | failed | 0.41 | Pass |
| Shopify | Global Enterprise Non-Fit | success | 23 | Low priority | High confidence | skipped_low_priority | 5.93 | Pass |
| Microsoft | Global Enterprise Non-Fit | connection_timeout | 0 | Unscored (Failed Scrape) | nan | failed | 12.05 | Pass |
| Example Domain | Sparse Content Baseline | success | 10 | Low priority | Insufficient evidence | success | 8.47 | Pass |
| Non-Existent Domain | Intentional Failure Test | dns_resolution_failure | 0 | Unscored (Failed Scrape) | nan | failed | 0.2 | N/A (control) |
| HTTP 404 Endpoint | Intentional Failure Test | http_404_not_found | 0 | Unscored (Failed Scrape) | nan | failed | 1.07 | N/A (control) |

## 5. Findings

1. **Time:** Wall-clock copilot time is far below the 15-minute SDR baseline even when Gemini retries. The saving is research *prep* time, not fully automated selling — a human still must approve outreach and CRM writes.
2. **Public-web brittleness:** Large brand sites frequently return 403/406, expired SSL, or JS-only shells. The copilot records the failure instead of inventing a profile (correct behaviour for a grounded researcher).
3. **Conservative scoring:** Unknown ICP signals (size, geography, complexity) force `Insufficient evidence` rather than a false High-priority score. That reduces false positives on enterprises and thin pages.
4. **Token skip and outreach precision:** Confirmed Low-priority non-fits skip Gemini outreach when confidence is not `Insufficient evidence` (6 leads cleanly skipped, conserving token spend and preventing spam). Grounded outreach drafts were generated successfully via Gemini for 10 qualifying leads (0 partial fallbacks), with hard character length constraints (<= 300 chars) strictly enforced for LinkedIn notes.
5. **Human-in-the-loop:** No benchmark path sends email or LinkedIn messages. CRM sync remains behind the Stage 6 approval gate.

## 6. Limitations

- Homepage-only scrape (no multi-page crawl of `/about` or careers).
- Company size is rarely stated on public homepages, so size match is often `unknown`.
- Anti-bot blocks (403/406) look like “research failure” even when the company is real.
- Gemini rate limits can force heuristic fallbacks; treat `partial` outreach as templates, not grounded copy.
- Time-saved percentage uses an assumed 15-minute manual baseline, not a timed human study (`actual_manual_minutes_recorded` is left blank for a reviewer to fill).

## 7. How to re-run

```powershell
cd C:\Users\PC\Downloads\pros\ai-lead-research-copilot
.\.venv\Scripts\python.exe evaluate_copilot.py
# Optional smoke run:
.\.venv\Scripts\python.exe evaluate_copilot.py --limit 5
.\.venv\Scripts\python.exe test_evaluate.py
```
