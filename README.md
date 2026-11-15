# AI Lead-Research and Outreach Copilot

A modular, human-in-the-loop AI sales research and outreach system.

## Project Vision
Automates researching prospective client websites, extracting core company information, assessing alignment against an Ideal Customer Profile (ICP), scoring leads transparently, and drafting personalized multi-channel outreach (Email and LinkedIn) for human review before synchronization with HubSpot CRM.

---

## Current Status: Stage 1 Completed
- **Stage 1: Project Setup and Website Scraping** (Active & Tested)
- Stage 2: Company Information Extraction
- Stage 3: AI Integration & Business Analysis
- Stage 4: Ideal Customer Profile & Lead Scoring
- Stage 5: Personalized Outreach Generation
- Stage 6: Human Approval & HubSpot Integration
- Stage 7: Streamlit Application
- Stage 8: Evaluation and Testing
- Stage 9: Final Portfolio Deliverables

---

## Directory Structure
```
ai-lead-research-copilot/
│
├── .venv/                 # Isolated Python 3.11 virtual environment
├── requirements.txt       # Project dependencies
├── README.md              # Project documentation
├── .gitignore             # Ignored directories, venv, and secrets
├── app.py                 # Interactive entry point
├── test_scraper.py        # Automated test suite for website scraper
│
├── research/              # Scraping and research engine module
│   ├── __init__.py
│   └── scraper.py         # Requests & BeautifulSoup clean text extractor
│
└── data/                  # Output storage for scraped leads
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Activate Virtual Environment (Windows PowerShell)
```powershell
cd ai-lead-research-copilot
.\.venv\Scripts\Activate.ps1
```

### 3. Run Automated Scraper Tests
```powershell
python test_scraper.py
```

### 4. Run Interactive Scraper App
```powershell
python app.py
```
