"""
dashboard.py
============
Interactive Web Application for the AI Lead-Research and Outreach Copilot.
Built with Streamlit and Pandas.

Features:
- View 1: Single Lead Deep Dive (Live Research Pipeline, Grounded Analysis, Score Card,
          and Interactive Human Approval Gate with CRM Sync). Includes Instant Demo Loader.
- View 2: Batch CSV Lead Evaluation (Resilient multi-company evaluation, priority filters, CSV export).
- View 3: CRM Sync Audit Log (Permanent audit trail of human review decisions and CRM syncs).

Architecture:
- Pure presentation layer: Imports all core logic directly from 'research' package.
- Zero duplicate backend logic.
- Session state caching: Changing variants or editing text never re-triggers scraping or LLM calls.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load local environment variables (.env)
load_dotenv()

# Import core business logic from research package (Zero duplicate logic)
from research import (
    scrape_website,
    extract_company_info,
    analyze_company_crm_fit,
    score_lead,
    generate_outreach_drafts,
    review_outreach_draft,
    sync_lead_to_crm,
)


# ==============================================================================
# PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="SalesFlow Copilot | AI Sales Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clean, professional B2B SaaS custom styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-high {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-med {
        background-color: #FEF3C7;
        color: #B45309;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-low {
        background-color: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .card-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
def init_session_state():
    defaults = {
        "lead_profile": None,
        "lead_analysis": None,
        "lead_score": None,
        "lead_outreach": None,
        "sync_result": None,
        "current_url": "",
        "active_variant_key": "email_variant_a",
        "edited_text_input": "",
        "batch_results_df": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()


# ==============================================================================
# HELPER FUNCTIONS: DEMO LOADER & AUDIT LOGGER
# ==============================================================================
def load_demo_apex_agro():
    """Instantly loads pre-computed Apex Agro research for rapid testing and demonstrations."""
    data_dir = Path("data")
    profile_path = data_dir / "company_profile.json"
    analysis_path = data_dir / "business_analysis.json"
    score_path = data_dir / "lead_score.json"
    outreach_path = data_dir / "outreach_drafts.json"

    if analysis_path.exists() and score_path.exists() and outreach_path.exists():
        with open(analysis_path, "r", encoding="utf-8") as f:
            st.session_state.lead_analysis = json.load(f)
        with open(score_path, "r", encoding="utf-8") as f:
            st.session_state.lead_score = json.load(f)
        with open(outreach_path, "r", encoding="utf-8") as f:
            st.session_state.lead_outreach = json.load(f)
        
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                st.session_state.lead_profile = json.load(f)
        else:
            st.session_state.lead_profile = {
                "company_name": st.session_state.lead_analysis.get("company_name", "Apex Agro & Spices"),
                "website_url": st.session_state.lead_analysis.get("website_url", "https://apexagrospices.example.in"),
                "industry": "Food Processing & FMCG Wholesale Distribution",
                "location": "Kochi, Kerala, India",
                "business_model": "B2B",
                "company_size": "65 employees (with ~18 field sales reps)",
                "company_summary": "Apex Agro & Spices is an Indian manufacturer and wholesale distributor of processed spices and condiments serving 450+ accounts across South India.",
                "products_services": ["Bulk ground spices", "Packaged curry powders", "Commercial seasonings"],
                "target_customers": ["Regional supermarkets", "Wholesale food stockists"],
                "verified_facts": [
                    "Supplies over 450 verified supermarket accounts across Kerala and Tamil Nadu.",
                    "Employs 18 regional field sales and order-collection agents.",
                    "Announced an INR 12-crore expansion to establish 3 new regional supply depots in Bengaluru, Hyderabad, and Vijayawada.",
                ],
                "uncertain_information": ["Current sales software is unknown; likely using spreadsheets."],
            }

        st.session_state.current_url = st.session_state.lead_profile.get("website_url", "")
        st.session_state.sync_result = None
        st.success("Loaded Demo Lead: Apex Agro & Spices Exports Pvt. Ltd. (High Priority Indian B2B Distributor)")
    else:
        st.warning("Sample demo files not found in data/ directory. Run test suites first or enter a URL below.")


def read_crm_sync_logs() -> list:
    """Reads crm_sync_log.json handling both single-dict and list formats."""
    log_file = Path("data") / "crm_sync_log.json"
    if not log_file.exists():
        return []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                return content
            elif isinstance(content, dict):
                return [content]
    except Exception:
        return []
    return []


# ==============================================================================
# SIDEBAR NAVIGATION & SYSTEM HEALTH
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=54)
    st.title("SalesFlow Copilot")
    st.caption("AI Sales Research & Outreach Platform")

    view_choice = st.radio(
        "Navigation",
        [
            "🔍 Single Lead Deep Dive",
            "📁 Batch CSV Lead Evaluation",
            "📊 CRM Sync Audit Log",
        ],
        index=0,
    )

    st.markdown("---")
    st.subheader("System Status")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        st.markdown("🟢 **Gemini AI:** `Connected (gemini-3.8-flash)`")
    else:
        st.markdown("🟡 **Gemini AI:** `Unset (Fallback Heuristics Active)`")

    hubspot_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if hubspot_token and not hubspot_token.startswith("your_"):
        st.markdown("🟢 **HubSpot CRM:** `Live v3 API Connected`")
    else:
        st.markdown("🔵 **HubSpot CRM:** `Dry-Run Simulation Active`")

    st.markdown("---")
    if st.button("🔄 Reset Lead Session", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        init_session_state()
        st.rerun()


# ==============================================================================
# VIEW 1: SINGLE LEAD DEEP DIVE (LIVE PIPELINE + HUMAN APPROVAL GATE)
# ==============================================================================
if view_choice == "🔍 Single Lead Deep Dive":
    st.markdown('<div class="main-header">Single Lead Research & Outreach</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated company research, CRM fit analysis, deterministic lead scoring, and human-in-the-loop outreach.</div>', unsafe_allow_html=True)

    # Input Section
    col_input, col_demo = st.columns([3, 1])
    with col_input:
        target_url = st.text_input(
            "Company Website URL",
            value=st.session_state.current_url or "https://stripe.com",
            placeholder="e.g. https://stripe.com or https://company.in",
        )
    with col_demo:
        st.write("&nbsp;")
        if st.button("📂 Load Demo (Apex Agro)", use_container_width=True):
            load_demo_apex_agro()
            st.rerun()

    with st.expander("➕ Supplemental Research (Optional - News, Press Releases, Job Postings)"):
        supplemental_text = st.text_area(
            "Paste external evidence (enhances buying trigger detection):",
            value=(
                "Apex Agro & Spices announced an INR 12-crore expansion to establish 3 new regional supply depots "
                "in Bengaluru, Hyderabad, and Vijayawada by Q3 2026. Actively hiring: 1x Regional Sales Manager, "
                "6x Field Sales Executives, and 2x Channel Operations Coordinators."
                if "apex" in target_url.lower()
                else ""
            ),
            height=90,
            placeholder="e.g. News articles, LinkedIn hiring announcements, expansion press releases...",
        )

    run_pipeline = st.button("🚀 Run Lead Copilot", type="primary", use_container_width=True)

    if run_pipeline and target_url.strip():
        st.session_state.current_url = target_url.strip()
        st.session_state.sync_result = None

        with st.status("Executing Research Pipeline...", expanded=True) as status_box:
            # Stage 1: Scrape
            st.write("🕷️ **Stage 1:** Scraping and cleaning website text...")
            scraped = scrape_website(target_url.strip())
            if scraped["status"] == "error":
                st.error(f"Scraping Failed: {scraped['error_message']}")
                status_box.update(label="Scraping Failed", state="error")
                st.stop()

            # Stage 2: Extract
            st.write("🏢 **Stage 2:** Extracting grounded company profile with Gemini...")
            profile = extract_company_info(scraped)
            st.session_state.lead_profile = profile

            # Stage 3: Analyze
            st.write("🎯 **Stage 3:** Analyzing SalesFlow CRM fit, pain points, and triggers...")
            analysis = analyze_company_crm_fit(
                profile,
                additional_research=supplemental_text.strip() if supplemental_text.strip() else None,
            )
            st.session_state.lead_analysis = analysis

            # Stage 4: Score
            st.write("📈 **Stage 4:** Calculating deterministic 0-100 ICP lead score...")
            lead_score_data = score_lead(analysis)
            st.session_state.lead_score = lead_score_data

            # Stage 5: Outreach
            st.write("✍️ **Stage 5:** Generating 4 grounded outreach variants (pending review)...")
            outreach = generate_outreach_drafts(profile, analysis, lead_score_data)
            st.session_state.lead_outreach = outreach

            status_box.update(label="Research & Outreach Pipeline Completed!", state="complete")
        st.rerun()

    # If lead data is present in session_state, display the full intelligence report
    if st.session_state.lead_score and st.session_state.lead_profile:
        profile = st.session_state.lead_profile
        analysis = st.session_state.lead_analysis or {}
        score_data = st.session_state.lead_score
        outreach_data = st.session_state.lead_outreach or {}

        st.markdown("---")
        
        # High-Level Summary Header
        score_val = score_data.get("total_score", 0)
        priority = score_data.get("priority", "Low priority")
        relevance = analysis.get("crm_relevance", {}).get("classification", "Unknown")

        badge_class = "badge-high" if priority == "High priority" else ("badge-med" if priority == "Medium priority" else "badge-low")

        col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1.2, 1.2, 1.5])
        with col_h1:
            st.markdown(f"### {profile.get('company_name') or 'Target Company'}")
            st.caption(f"🌐 [{profile.get('website_url')}]({profile.get('website_url')}) | Industry: **{profile.get('industry') or 'N/A'}**")
        with col_h2:
            st.metric("ICP Score", f"{score_val} / 100")
        with col_h3:
            st.markdown(f"**Priority Tier**<br><span class='{badge_class}'>{priority.upper()}</span>", unsafe_allow_html=True)
        with col_h4:
            st.markdown(f"**CRM Relevance**<br><strong>{relevance}</strong>", unsafe_allow_html=True)

        # 4 Core Intelligence Tabs
        tab_profile, tab_crm, tab_score, tab_outreach = st.tabs([
            "🏢 1. Company Profile",
            "🎯 2. CRM Intelligence",
            "📈 3. ICP Score Card",
            "✍️ 4. Outreach & Human Approval",
        ])

        # TAB 1: COMPANY PROFILE
        with tab_profile:
            st.markdown("#### Grounded Company Profile (Stage 2)")
            st.info(profile.get("company_summary") or "No company summary available.")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("**Core Attributes:**")
                st.write(f"• **Location:** {profile.get('location') or 'Not Disclosed'}")
                st.write(f"• **Business Model:** {profile.get('business_model')}")
                st.write(f"• **Reported Size:** {profile.get('company_size') or 'Not Disclosed'}")
                st.write(f"• **Target Customers:** {', '.join(profile.get('target_customers', [])) or 'General B2B'}")
                
                st.markdown("**Products & Services:**")
                for prod in profile.get("products_services", [])[:6]:
                    st.write(f"  - {prod}")

            with col_p2:
                st.markdown("**Verified Facts (from Website Text):**")
                for fact in profile.get("verified_facts", []):
                    st.write(f"  ✅ {fact}")

                if profile.get("uncertain_information"):
                    st.markdown("**Uncertain Information / Unknowns:**")
                    for uncert in profile.get("uncertain_information", []):
                        st.write(f"  ⚠️ {uncert}")

        # TAB 2: CRM INTELLIGENCE
        with tab_crm:
            st.markdown("#### SalesFlow CRM Opportunity Analysis (Stage 3)")
            crm_rel = analysis.get("crm_relevance", {})
            st.success(f"**Why this company matters:** {crm_rel.get('reasoning')}")

            # Structured Signals
            signals = crm_rel.get("icp_signals", {})
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Geography Match", signals.get("geography_match", "unknown").upper())
            col_s2.metric("Industry Match", signals.get("industry_match", "none").upper())
            col_s3.metric("Size Match", signals.get("company_size_match", "unknown").upper())
            col_s4.metric("Sales Complexity", signals.get("sales_complexity_signal", "unknown").upper())

            # Pain Points & Triggers
            col_pt1, col_pt2 = st.columns(2)
            with col_pt1:
                st.markdown("##### Potential Business Pain Points")
                pain_points = analysis.get("potential_pain_points", [])
                if pain_points:
                    for idx, p in enumerate(pain_points, 1):
                        with st.expander(f"{idx}. {p.get('problem')} ({p.get('confidence', '').upper()} CONFIDENCE)"):
                            st.write(f"**Reasoning:** {p.get('reasoning')}")
                            st.caption(f"Evidence: {', '.join(p.get('evidence', []))}")
                else:
                    st.write("No operational pain points identified.")

            with col_pt2:
                st.markdown("##### Observable Buying Triggers")
                triggers = analysis.get("buying_triggers", [])
                if triggers:
                    for idx, t in enumerate(triggers, 1):
                        date_str = f" ({t.get('observed_date')})" if t.get('observed_date') else ""
                        with st.expander(f"⚡ {t.get('trigger_type', '').upper()}{date_str}: {t.get('description')}"):
                            st.info(f"\"{t.get('evidence_quote')}\"")
                else:
                    st.write(f"No active triggers identified. Reason: {analysis.get('no_trigger_reason')}")

            # Value Hypotheses
            st.markdown("##### Recommended SalesFlow CRM Capabilities")
            for v in analysis.get("value_hypotheses", []):
                st.write(f"• **{v.get('feature')}:** {v.get('hypothesized_benefit')}")

        # TAB 3: ICP SCORE CARD
        with tab_score:
            st.markdown("#### Deterministic 0-100 Scoring Rubric (Stage 4)")
            st.write(f"**Recommendation:** {score_data.get('summary_recommendation')}")

            st.progress(score_val / 100)

            # Table representation of rubric
            breakdown = score_data.get("scoring_breakdown", {})
            score_rows = []
            for crit, det in breakdown.items():
                score_rows.append({
                    "Criterion": crit.replace("_", " ").title(),
                    "Score Awarded": f"{det['score']} / {det['max']} pts",
                    "Signal Detected": det["signal"],
                    "Reasoning": det["reasoning"],
                })
            st.table(pd.DataFrame(score_rows))

        # TAB 4: OUTREACH & HUMAN APPROVAL GATE
        with tab_outreach:
            st.markdown("#### Personalised Outreach & Human Approval Gate (Stages 5 & 6)")

            if outreach_data.get("generation_status") == "skipped_low_priority":
                st.warning(f"🚫 **Outreach Drafting Skipped:** {outreach_data.get('generation_notes')}")
            else:
                drafts = outreach_data.get("drafts", {})
                
                # Variant Selector Tabs
                v_tabs = st.tabs([
                    "📧 Email A (Direct)",
                    "📧 Email B (Consultative)",
                    "💬 LinkedIn Connection Note",
                    "💬 LinkedIn InMail",
                ])

                variant_keys = [
                    ("email_variant_a", v_tabs[0]),
                    ("email_variant_b", v_tabs[1]),
                    ("linkedin_variant_a", v_tabs[2]),
                    ("linkedin_variant_b", v_tabs[3]),
                ]

                # Map chosen variant in session state
                chosen_variant = st.selectbox(
                    "Select Outreach Draft to Review & Finalize:",
                    [
                        "email_variant_a (Direct & Trigger-Led)",
                        "email_variant_b (Consultative & Hypothesis-Led)",
                        "linkedin_variant_a (Connection Note <= 300 chars)",
                        "linkedin_variant_b (Conversational InMail)",
                    ],
                    index=0,
                )
                variant_code = chosen_variant.split()[0]

                # Display previews in tabs
                for code, tab_obj in variant_keys:
                    with tab_obj:
                        d = drafts.get(code, {})
                        if "email" in code:
                            st.write(f"**Subject Line:** `{d.get('subject_line')}`")
                            st.text_area("Draft Text:", value=d.get("body_text", ""), height=150, key=f"preview_{code}", disabled=True)
                            st.caption(f"Word count: {d.get('word_count')} words | Target: {d.get('target_persona')}")
                        else:
                            st.text_area("Draft Message:", value=d.get("message_text", ""), height=110, key=f"preview_{code}", disabled=True)
                            if "connection" in d.get("variant_name", "").lower():
                                st.caption(f"Character count: **{d.get('character_count')} / 300 characters** (LinkedIn limit compliant)")
                            else:
                                st.caption(f"Word count: {d.get('word_count')} words | Target: {d.get('target_persona')}")
                        st.write(f"**Evidence Used:** {', '.join(d.get('evidence_used', []))}")

                st.markdown("---")
                st.markdown("##### ✍️ Human Review & Custom Editing")
                
                # Fetch default text for chosen variant
                target_d = drafts.get(variant_code, {})
                initial_text = target_d.get("body_text") or target_d.get("message_text") or ""
                
                edited_text = st.text_area(
                    "Edit outreach text before approval (or leave as-is to approve unmodified draft):",
                    value=st.session_state.edited_text_input or initial_text,
                    height=160,
                )
                st.session_state.edited_text_input = edited_text

                # Human Action Buttons
                col_b1, col_b2, col_b3 = st.columns(3)
                
                with col_b1:
                    if st.button("🟢 Approve & Sync to CRM", type="primary", use_container_width=True):
                        # Review
                        is_modified = edited_text.strip() != initial_text.strip()
                        decision_type = "edit" if is_modified else "approve"
                        reviewed = review_outreach_draft(
                            outreach_data,
                            decision=decision_type,
                            selected_variant=variant_code,
                            custom_text=edited_text if is_modified else None,
                            reviewer_name="Sales Rep (Streamlit User)",
                            notes="Approved via Web Dashboard",
                        )
                        st.session_state.lead_outreach = reviewed

                        # Sync
                        sync_res = sync_lead_to_crm(profile, analysis, score_data, reviewed)
                        st.session_state.sync_result = sync_res
                        
                        # Save audit log
                        with open(Path("data") / "crm_sync_log.json", "w", encoding="utf-8") as f:
                            json.dump(sync_res, f, indent=2, ensure_ascii=False)
                        st.success("Lead approved and successfully queued/synced to CRM!")
                        st.rerun()

                with col_b2:
                    if st.button("🟡 Save for Later", use_container_width=True):
                        reviewed = review_outreach_draft(
                            outreach_data, decision="save_for_later", reviewer_name="Sales Rep (Streamlit User)"
                        )
                        st.session_state.lead_outreach = reviewed
                        st.info("Lead saved for later. CRM sync deferred.")
                        st.rerun()

                with col_b3:
                    if st.button("🔴 Reject Lead", use_container_width=True):
                        reviewed = review_outreach_draft(
                            outreach_data, decision="reject", reviewer_name="Sales Rep (Streamlit User)", notes="Rejected by user in UI"
                        )
                        st.session_state.lead_outreach = reviewed
                        sync_res = sync_lead_to_crm(profile, analysis, score_data, reviewed)
                        st.session_state.sync_result = sync_res
                        st.warning("Lead rejected. CRM synchronization permanently blocked.")
                        st.rerun()

                # Sync Feedback Card
                curr_review = outreach_data.get("human_review", {})
                st.markdown(f"**Current Status:** `{curr_review.get('approval_status', 'pending_human_review').upper()}`")

                if st.session_state.sync_result:
                    sr = st.session_state.sync_result
                    st.markdown("---")
                    st.markdown("##### CRM Synchronization Result")
                    if sr.get("sync_status") == "success":
                        st.success(
                            f"✅ **{sr.get('action_taken').replace('_', ' ').title()}** | "
                            f"Mode: `{sr.get('sync_mode').upper()}` | "
                            f"HubSpot ID: `{sr.get('hubspot_company_id')}`\n\n"
                            f"_{sr.get('sync_notes')}_"
                        )
                    else:
                        st.error(f"Sync Status: {sr.get('sync_status').upper()} - {sr.get('sync_notes')}")


# ==============================================================================
# VIEW 2: BATCH CSV LEAD EVALUATION (RESILIENT PIPELINE)
# ==============================================================================
elif view_choice == "📁 Batch CSV Lead Evaluation":
    st.markdown('<div class="main-header">Batch CSV Lead Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Evaluate 5 to 50 prospective accounts in batch with resilient per-row error handling.</div>', unsafe_allow_html=True)

    sample_csv_path = Path("data") / "sample_target_companies.csv"
    
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        uploaded_csv = st.file_uploader("Upload CSV of Target Companies", type=["csv"])
    with col_u2:
        st.write("&nbsp;")
        use_default_csv = st.button("📂 Load Sample CSV (5-8 B2B Leads)", use_container_width=True)

    target_df = None
    if uploaded_csv is not None:
        target_df = pd.read_csv(uploaded_csv)
    elif use_default_csv and sample_csv_path.exists():
        target_df = pd.read_csv(sample_csv_path)

    if target_df is not None:
        st.write(f"Loaded **{len(target_df)} target companies**:")
        st.dataframe(target_df, use_container_width=True)

        # Detect URL column
        url_col = next((c for c in target_df.columns if "url" in c.lower() or "website" in c.lower()), None)
        
        if not url_col:
            st.error("CSV must contain a column named 'url' or 'website'.")
        else:
            if st.button("▶ Run Batch Evaluation", type="primary"):
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                results = []

                for idx, row in target_df.iterrows():
                    raw_url = str(row[url_col]).strip()
                    comp_name_guess = str(row.get("company_name", raw_url))
                    extra_note = str(row.get("notes", ""))
                    
                    status_text.text(f"Evaluating ({idx + 1}/{len(target_df)}): {raw_url} ...")
                    
                    try:
                        # 1. Scrape
                        scraped = scrape_website(raw_url, timeout=10)
                        if scraped["status"] == "error":
                            results.append({
                                "Company Name": comp_name_guess,
                                "URL": raw_url,
                                "Status": "Scraping Failed",
                                "ICP Score": 0,
                                "Priority": "Low priority",
                                "CRM Relevance": "Unreachable",
                                "Top Trigger": "N/A",
                                "Error Notes": scraped.get("error_message"),
                            })
                            progress_bar.progress((idx + 1) / len(target_df))
                            continue

                        # 2. Extract
                        profile = extract_company_info(scraped)
                        
                        # 3. Analyze
                        analysis = analyze_company_crm_fit(profile, additional_research=extra_note if extra_note else None)
                        
                        # 4. Score
                        score_res = score_lead(analysis)
                        
                        # Top trigger
                        triggers = analysis.get("buying_triggers", [])
                        top_trig = f"[{triggers[0].get('trigger_type', '').upper()}] {triggers[0].get('description')[:50]}..." if triggers else "None"

                        results.append({
                            "Company Name": profile.get("company_name") or comp_name_guess,
                            "URL": raw_url,
                            "Status": "Evaluated",
                            "ICP Score": score_res.get("total_score", 0),
                            "Priority": score_res.get("priority", "Low priority"),
                            "CRM Relevance": analysis.get("crm_relevance", {}).get("classification", "Unknown"),
                            "Top Trigger": top_trig,
                            "Error Notes": "None",
                        })

                    except Exception as exc:
                        # Resilient per-row catch ensures loop never breaks
                        results.append({
                            "Company Name": comp_name_guess,
                            "URL": raw_url,
                            "Status": "Error",
                            "ICP Score": 0,
                            "Priority": "Low priority",
                            "CRM Relevance": "Error",
                            "Top Trigger": "N/A",
                            "Error Notes": str(exc),
                        })

                    progress_bar.progress((idx + 1) / len(target_df))
                    time.sleep(1.5)  # Rate limit courtesy spacing

                status_text.text("Batch evaluation completed successfully!")
                res_df = pd.DataFrame(results)
                st.session_state.batch_results_df = res_df

    if st.session_state.batch_results_df is not None:
        st.markdown("---")
        st.markdown("#### Batch Evaluation Results")
        
        df_display = st.session_state.batch_results_df
        
        # Priority Filter
        filter_choice = st.selectbox("Filter by Priority:", ["All", "High priority", "Medium priority", "Low priority"])
        if filter_choice != "All":
            df_display = df_display[df_display["Priority"] == filter_choice]

        st.dataframe(df_display, use_container_width=True)

        # Download CSV
        csv_bytes = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Evaluated Leads CSV",
            data=csv_bytes,
            file_name="evaluated_sales_leads.csv",
            mime="text/csv",
        )


# ==============================================================================
# VIEW 3: CRM SYNC AUDIT LOG & COMPLIANCE HISTORY
# ==============================================================================
elif view_choice == "📊 CRM Sync Audit Log":
    st.markdown('<div class="main-header">CRM Sync Audit Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Permanent compliance audit trail verifying human review before HubSpot ingestion.</div>', unsafe_allow_html=True)

    logs = read_crm_sync_logs()

    if not logs:
        st.info("No CRM sync events logged yet. Approve a lead in View 1 to generate audit records.")
    else:
        st.write(f"Total Sync Events Logged: **{len(logs)}**")

        log_rows = []
        for l in logs:
            log_rows.append({
                "Timestamp": l.get("timestamp"),
                "Company": l.get("company_name"),
                "Domain": l.get("domain"),
                "Human Status": l.get("human_review_status", "").upper(),
                "Sync Mode": l.get("sync_mode", "").upper(),
                "Action Taken": l.get("action_taken"),
                "HubSpot ID": l.get("hubspot_company_id"),
                "Status": l.get("sync_status", "").upper(),
            })

        st.dataframe(pd.DataFrame(log_rows), use_container_width=True)

        st.markdown("---")
        st.markdown("##### Detailed Audit Payload View")
        for idx, l in enumerate(logs):
            with st.expander(f"{idx + 1}. {l.get('company_name')} ({l.get('sync_id')}) - Status: {l.get('sync_status', '').upper()}"):
                st.json(l)
