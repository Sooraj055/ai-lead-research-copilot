"""
Research package for AI Lead-Research and Outreach Copilot.
Handles web scraping, company information extraction, and CRM business analysis.
"""

from .scraper import scrape_website
from .extractor import extract_company_info, get_empty_company_profile
from .analyzer import analyze_company_crm_fit, get_empty_business_analysis

__all__ = [
    "scrape_website",
    "extract_company_info",
    "get_empty_company_profile",
    "analyze_company_crm_fit",
    "get_empty_business_analysis",
]
