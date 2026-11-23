"""
scraper.py
==========
Website scraping engine for the AI Lead-Research and Outreach Copilot.

This module fetches publicly accessible HTML from target company websites,
cleans the content by removing unnecessary HTML tags (scripts, styles, navigation,
footers), extracts metadata (title, meta description), and returns clean, structured
readable text limited to a safe length for downstream LLM analysis.
"""

import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


# Standard browser header to avoid being rejected by basic anti-bot filters
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

# Unnecessary HTML tags that add noise without contributing to company business content
TAGS_TO_REMOVE = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "noscript",
    "svg",
    "iframe",
]


def normalize_url(raw_url: str) -> str:
    """
    Ensure the URL has a proper scheme (https://).
    
    Example:
        'stripe.com' -> 'https://stripe.com'
        'http://example.com' -> 'http://example.com'
    """
    cleaned_url = raw_url.strip()
    parsed = urlparse(cleaned_url)
    
    if not parsed.scheme:
        cleaned_url = "https://" + cleaned_url
        
    return cleaned_url


def _alternate_host_url(url: str) -> Optional[str]:
    """Flip www / non-www host to recover from some SSL hostname mismatches."""
    parsed = urlparse(url)
    host = parsed.netloc
    if not host:
        return None
    alt_host = host[4:] if host.startswith("www.") else "www." + host
    if alt_host == host:
        return None
    return parsed._replace(netloc=alt_host).geturl()


def scrape_website(
    url: str,
    timeout: int = 12,
    max_chars: int = 6000,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Scrapes a target website and extracts clean readable text and metadata.

    Args:
        url (str): The target website URL (e.g., 'https://stripe.com').
        timeout (int): Request timeout in seconds. Defaults to 12.
        max_chars (int): Maximum character limit for clean text output. Defaults to 6000.
        headers (dict, optional): Custom HTTP headers. Defaults to DEFAULT_HEADERS.

    Returns:
        dict: Structured dictionary containing:
            - 'url': The normalized URL
            - 'status': 'success' or 'error'
            - 'http_status': HTTP status code (e.g. 200, 404, None)
            - 'title': Page title (or empty string)
            - 'meta_description': Meta description or OpenGraph description
            - 'clean_text': Clean readable text (truncated to max_chars)
            - 'char_count': Character count of clean text
            - 'error_message': Description of the error if status == 'error'
    """
    target_url = normalize_url(url)
    req_headers = headers if headers is not None else DEFAULT_HEADERS

    result: Dict[str, Any] = {
        "url": target_url,
        "status": "error",
        "http_status": None,
        "title": "",
        "meta_description": "",
        "clean_text": "",
        "char_count": 0,
        "error_message": None,
    }

    try:
        # Step 1: Send the HTTP GET request (retry flipped www host on SSL mismatch)
        try:
            response = requests.get(
                target_url,
                headers=req_headers,
                timeout=timeout,
                allow_redirects=True,
            )
        except requests.exceptions.SSLError:
            alt_url = _alternate_host_url(target_url)
            if not alt_url:
                raise
            response = requests.get(
                alt_url,
                headers=req_headers,
                timeout=timeout,
                allow_redirects=True,
            )
            target_url = alt_url
            result["url"] = target_url
        result["http_status"] = response.status_code

        # Step 2: Handle HTTP errors (e.g., 403 Forbidden, 404 Not Found, 500 Server Error)
        if response.status_code != 200:
            result["error_message"] = (
                f"Website responded with HTTP status code {response.status_code} "
                f"({response.reason}). Access may be restricted or page not found."
            )
            return result

        # Step 3: Parse HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        # Step 4: Extract page title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            og_title = soup.find("meta", property="og:title")
            title = og_title.get("content", "").strip()
        result["title"] = title

        # Step 5: Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
        if not meta_tag:
            meta_tag = soup.find("meta", attrs={"property": re.compile(r"og:description", re.I)})

        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag.get("content", "").strip()
        result["meta_description"] = meta_desc

        # Step 6: Strip noise elements (scripts, styles, navs, footers, etc.)
        for tag_name in TAGS_TO_REMOVE:
            for element in soup.find_all(tag_name):
                element.decompose()  # completely removes element and its children

        # Step 7: Extract readable text
        # Use body text if available, otherwise entire parsed tree
        root = soup.body if soup.body else soup
        raw_text = root.get_text(separator="\n")

        # Step 8: Clean and normalize whitespace
        lines = [line.strip() for line in raw_text.splitlines()]
        # Filter out empty lines or standalone special characters
        meaningful_lines = [line for line in lines if len(line) > 1]
        clean_text = "\n".join(meaningful_lines)

        # Step 9: Truncate to maximum characters to protect downstream LLM context window
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + "\n... [Content truncated for length]"

        result["clean_text"] = clean_text
        result["char_count"] = len(clean_text)
        result["status"] = "success"
        return result

    except requests.exceptions.Timeout:
        result["error_message"] = f"Connection timed out after {timeout} seconds. The server took too long to respond."
        return result

    except requests.exceptions.SSLError as ssl_err:
        result["error_message"] = f"SSL Certificate verification failed: {str(ssl_err)}"
        return result

    except requests.exceptions.ConnectionError:
        result["error_message"] = "Failed to establish a connection. Check the domain name or your internet connection."
        return result

    except requests.exceptions.RequestException as req_err:
        result["error_message"] = f"Request error occurred: {str(req_err)}"
        return result

    except Exception as exc:
        result["error_message"] = f"Unexpected error during scraping: {str(exc)}"
        return result
