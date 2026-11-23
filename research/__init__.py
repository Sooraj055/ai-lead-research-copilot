"""
Research package for AI Lead-Research and Outreach Copilot.
Handles web scraping, company information extraction, CRM business analysis, lead scoring, outreach drafting, and CRM sync.
"""

from .scraper import scrape_website
from .extractor import extract_company_info, get_empty_company_profile
from .analyzer import analyze_company_crm_fit, get_empty_business_analysis
from .scorer import score_lead
from .outreach import generate_outreach_drafts, get_empty_outreach_drafts
from .crm_sync import review_outreach_draft, sync_lead_to_crm
from .evaluation import categorize_scrape_failure

__all__ = [
    "scrape_website",
    "extract_company_info",
    "get_empty_company_profile",
    "analyze_company_crm_fit",
    "get_empty_business_analysis",
    "score_lead",
    "generate_outreach_drafts",
    "get_empty_outreach_drafts",
    "review_outreach_draft",
    "sync_lead_to_crm",
    "categorize_scrape_failure",
]
