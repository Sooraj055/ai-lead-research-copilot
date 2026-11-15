"""
app.py
======
Main entry point for AI Lead-Research and Outreach Copilot.

Stage 1 Milestone:
CLI interface for testing company website scraping and inspecting extracted text.
(Streamlit UI will be connected in later stages as planned in the roadmap).
"""

import sys
import json
from pathlib import Path
from research.scraper import scrape_website


def run_cli_scraper():
    print("\n" + "=" * 55)
    print("   AI Lead-Research & Outreach Copilot - Stage 1")
    print("=" * 55)
    
    while True:
        url_input = input("\nEnter company website URL (or 'q' to quit): ").strip()
        if not url_input or url_input.lower() == "q":
            print("Exiting. Great job testing Stage 1!")
            break
            
        print(f"\n[+] Fetching and analyzing: {url_input} ...")
        result = scrape_website(url_input)
        
        print("\n" + "-" * 55)
        print(f"Status:          {result['status'].upper()}")
        print(f"HTTP Code:       {result['http_status']}")
        print(f"Title:           {result['title'] or '[No Title Found]'}")
        print(f"Meta Desc:       {result['meta_description'] or '[No Meta Description]'}")
        print(f"Text Length:     {result['char_count']} characters")
        
        if result["status"] == "error":
            print(f"Error Details:   {result['error_message']}")
        else:
            print("\nClean Text Preview (first 400 chars):")
            print("-" * 55)
            print(result["clean_text"][:400] + ("..." if len(result["clean_text"]) > 400 else ""))
            print("-" * 55)
            
            # Save extracted lead data to data directory
            safe_name = "".join(c for c in result["title"] if c.isalnum() or c in (" ", "_", "-")).strip()
            safe_name = safe_name.replace(" ", "_")[:30] or "extracted_lead"
            out_path = Path("data") / f"{safe_name}.json"
            
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n[Saved full structured data to: {out_path}]")


if __name__ == "__main__":
    run_cli_scraper()
