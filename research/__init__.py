"""
Research package for AI Lead-Research and Outreach Copilot.
Handles web scraping, content extraction, and AI-powered company profiling.
"""

from .scraper import scrape_website
from .extractor import extract_company_info, get_empty_company_profile

__all__ = ["scrape_website", "extract_company_info", "get_empty_company_profile"]
