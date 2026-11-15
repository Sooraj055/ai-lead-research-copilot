"""
extractor.py
============
Company Information Extraction module for the AI Lead-Research and Outreach Copilot.

This module converts unstructured website text (collected by Stage 1 scraper)
into a structured, verified company profile matching the approved JSON schema.
It utilizes the Google Gemini API with strict grounding to prevent hallucinations,
distinguishes verified facts from uncertain information, and provides a graceful
fallback if the API key is not configured or an error occurs.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()


def get_empty_company_profile(url: str = "", status: str = "failed", notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a standardized default dictionary matching the approved JSON schema.
    Used for failed extractions, missing data, or initialization.
    """
    return {
        "company_name": None,
        "website_url": url,
        "industry": None,
        "location": None,
        "company_summary": None,
        "products_services": [],
        "target_customers": [],
        "business_model": "Unknown",
        "company_size": None,
        "verified_facts": [],
        "uncertain_information": [],
        "source_urls": [url] if url else [],
        "extraction_status": status,
        "extraction_notes": notes,
    }


def _heuristic_fallback_extraction(scraped_data: Dict[str, Any], notes: str) -> Dict[str, Any]:
    """
    Rule-based fallback extraction when Gemini API is unavailable or unconfigured.
    Derives best-effort company name from page title/URL domain and summary from meta description.
    """
    url = scraped_data.get("url", "")
    title = scraped_data.get("title", "")
    meta_desc = scraped_data.get("meta_description", "")

    # Derive candidate company name from page title or domain
    candidate_name = None
    if title:
        # Many page titles follow 'Brand Name | Headline' or 'Brand Name - Headline'
        parts = re.split(r"[-|:]", title)
        if parts:
            candidate_name = parts[0].strip()
    
    if not candidate_name and url:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        candidate_name = domain.split(".")[0].capitalize()

    profile = get_empty_company_profile(url=url, status="partial", notes=notes)
    profile["company_name"] = candidate_name
    profile["company_summary"] = meta_desc if meta_desc else None
    
    if meta_desc:
        profile["verified_facts"].append(f"Meta description: {meta_desc}")
    
    profile["uncertain_information"].append(
        "Company profile generated via heuristic fallback (LLM API was not utilized)."
    )
    return profile


def extract_company_info(
    scraped_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash",
) -> Dict[str, Any]:
    """
    Converts raw scraped website text into a structured, validated company profile.

    Args:
        scraped_data (dict): The output dictionary returned by Stage 1 scrape_website().
        api_key (str, optional): Google Gemini API key. Defaults to GEMINI_API_KEY env var.
        model_name (str): Gemini model to use. Defaults to 'gemini-2.5-flash'.

    Returns:
        dict: Structured company profile matching the approved JSON schema.
    """
    url = scraped_data.get("url", "")

    # Step 1: Validate Stage 1 scraping status
    if scraped_data.get("status") == "error":
        err_msg = scraped_data.get("error_message", "Scraper failed to retrieve website content.")
        return get_empty_company_profile(
            url=url,
            status="failed",
            notes=f"Extraction aborted because scraping failed: {err_msg}",
        )

    clean_text = (scraped_data.get("clean_text") or "").strip()
    title = (scraped_data.get("title") or "").strip()
    meta_desc = (scraped_data.get("meta_description") or "").strip()

    # Step 2: Check for sufficient content
    if len(clean_text) < 40 and not meta_desc:
        return get_empty_company_profile(
            url=url,
            status="failed",
            notes="Website returned insufficient text content for meaningful business analysis.",
        )

    # Step 3: Resolve Gemini API Key
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_api_key:
        return _heuristic_fallback_extraction(
            scraped_data,
            notes="GEMINI_API_KEY environment variable is not set. Generated partial profile using rule-based fallback.",
        )

    # Step 4: Construct Grounded System Prompt
    system_instruction = (
        "You are an expert sales intelligence research analyst. "
        "Your role is to analyze raw website text and extract a factual, structured company profile.\n\n"
        "CRITICAL RULES:\n"
        "1. Never invent or hallucinate company details, revenue numbers, or clients.\n"
        "2. If a field is not explicitly supported by the website text, return null or an empty list.\n"
        "3. Keep VERIFIED FACTS and UNCERTAIN INFORMATION strictly separate:\n"
        "   - 'verified_facts': Direct claims made in the text (e.g. products offered, technologies used).\n"
        "   - 'uncertain_information': Inferences, approximations, or assumptions that require human verification.\n"
        "4. Business Model must be one of: 'B2B', 'B2C', 'B2B2C', 'Marketplace', or 'Unknown'.\n"
        "5. Output ONLY valid JSON adhering strictly to the requested schema. No markdown backticks or commentary."
    )

    prompt = f"""
Target Website URL: {url}
Page Title: {title}
Meta Description: {meta_desc}

Website Clean Body Text:
{clean_text}

Extract the company profile adhering strictly to this JSON format:
{{
  "company_name": "string or null",
  "website_url": "{url}",
  "industry": "string or null",
  "location": "string or null (Headquarters city/country if mentioned, otherwise null)",
  "company_summary": "1-2 sentence factual summary of what the company does",
  "products_services": ["list", "of", "products", "or", "services"],
  "target_customers": ["list", "of", "target", "audiences", "or", "industries"],
  "business_model": "B2B | B2C | B2B2C | Marketplace | Unknown",
  "company_size": "string or null (e.g. '100-500 employees' only if explicitly stated, else null)",
  "verified_facts": ["explicit statements verified by website text"],
  "uncertain_information": ["inferences or unverified claims"],
  "source_urls": ["{url}"],
  "extraction_status": "success",
  "extraction_notes": "notes regarding text quality or missing fields"
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=effective_api_key)
        
        # Configure model to return pure JSON
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature to minimize creativity/hallucinations
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        raw_response_text = response.text.strip()
        # Clean any accidental code block formatting if present
        if raw_response_text.startswith("```"):
            raw_response_text = re.sub(r"^```(?:json)?\n?", "", raw_response_text)
            raw_response_text = re.sub(r"\n?```$", "", raw_response_text)

        parsed_profile = json.loads(raw_response_text)

        # Step 5: Validate and enforce approved schema keys
        default_profile = get_empty_company_profile(url=url, status="success")
        for key in default_profile:
            if key not in parsed_profile:
                parsed_profile[key] = default_profile[key]

        # Ensure source_urls always includes the original URL
        if not parsed_profile.get("source_urls"):
            parsed_profile["source_urls"] = [url]
        elif url not in parsed_profile["source_urls"]:
            parsed_profile["source_urls"].append(url)

        parsed_profile["extraction_status"] = "success"
        return parsed_profile

    except Exception as exc:
        # Fall back to heuristic profile on API error so application never crashes
        fallback = _heuristic_fallback_extraction(
            scraped_data,
            notes=f"Gemini API call failed ({type(exc).__name__}: {str(exc)}). Heuristic profile returned.",
        )
        fallback["extraction_status"] = "failed"
        return fallback
