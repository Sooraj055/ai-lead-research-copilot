# AI Lead-Research and Outreach Copilot

A modular, human-in-the-loop AI sales research and outreach system.

## Project Vision
Automates researching prospective client websites, extracting core company information, assessing alignment against an Ideal Customer Profile (ICP), scoring leads transparently, and drafting personalized multi-channel outreach (Email and LinkedIn) for human review before synchronization with HubSpot CRM.

---

## Current Status
- [x] **Stage 1: Project Setup and Website Scraping** (Completed & Tested)
- [x] **Stage 2: Company Information Extraction** (Completed & Tested)
- [x] **Stage 3: AI Business Analysis — CRM Fit, Pain Points & Triggers** (Completed & Tested)
- [x] **Stage 4: Ideal Customer Profile & Lead Scoring** (Completed & Tested)
- [x] **Stage 5: Personalised Outreach Generation** (Completed & Tested)
- [x] **Stage 6: Human Approval & HubSpot Free CRM Integration** (Completed & Tested)
- [ ] **Stage 7: Streamlit Application**
- [ ] **Stage 8: Evaluation and Testing**
- [ ] **Stage 9: Final Portfolio Deliverables**

---

## Directory Structure
```
ai-lead-research-copilot/
│
├── .venv/                 # Isolated Python 3.11 virtual environment
├── requirements.txt       # Project dependencies (requests, bs4, google-genai, python-dotenv)
├── README.md              # Project documentation
├── .gitignore             # Ignored directories, venv, and secrets (.env)
├── .env.example           # Template for environment variables (GEMINI_API_KEY, HUBSPOT_ACCESS_TOKEN)
├── app.py                 # Interactive CLI pipeline (Scrape + Extract + Analyze + Score + Outreach + CRM Sync)
├── test_scraper.py        # Automated test suite for Stage 1 (Scraper)
├── test_extractor.py      # Automated test suite for Stage 2 (Extractor)
├── test_analyzer.py       # Automated test suite for Stage 3 (Business Analyzer)
├── test_scorer.py         # Automated test suite for Stage 4 (Deterministic Lead Scorer)
├── test_outreach.py       # Automated test suite for Stage 5 (Personalised Outreach Generator)
├── test_crm_sync.py       # Automated test suite for Stage 6 (Human Approval & CRM Sync)
│
├── research/              # Research, scoring, outreach, and CRM sync modules
│   ├── __init__.py        # Exports scraper, extractor, analyzer, scorer, outreach, crm_sync
│   ├── scraper.py         # Stage 1: Requests & BeautifulSoup clean text extractor
│   ├── extractor.py       # Stage 2: Grounded company profile extractor (Gemini)
│   ├── analyzer.py        # Stage 3: CRM relevance, pain points & buying triggers (Gemini)
│   ├── scorer.py          # Stage 4: Deterministic 0-100 ICP scoring engine (Pure Python)
│   ├── outreach.py        # Stage 5: Grounded 4-variant sales messaging engine (Gemini)
│   └── crm_sync.py        # Stage 6: Human approval gate & HubSpot Free CRM v3 integration
│
└── data/                  # Output storage for scraped leads and profiles
    ├── sample_scrape.json
    ├── company_profile.json
    ├── business_analysis.json
    ├── lead_score.json
    ├── outreach_drafts.json
    └── crm_sync_log.json
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Git
- Google Gemini API key (Free at https://aistudio.google.com)
- HubSpot Free CRM Private App Token (Optional; automatic dry-run fallback active if unconfigured)

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and add your keys:
```ini
GEMINI_API_KEY="AIzaSy..."
HUBSPOT_ACCESS_TOKEN="pat-na1-..."  # Optional
```

### 3. Run Automated Tests
```powershell
# Test Stage 1 Scraper:
.\.venv\Scripts\python.exe test_scraper.py

# Test Stage 2 Extractor:
.\.venv\Scripts\python.exe test_extractor.py

# Test Stage 3 Business Analyzer:
.\.venv\Scripts\python.exe test_analyzer.py

# Test Stage 4 Deterministic Scorer:
.\.venv\Scripts\python.exe test_scorer.py

# Test Stage 5 Outreach Generator:
.\.venv\Scripts\python.exe test_outreach.py

# Test Stage 6 Human Approval & CRM Sync:
.\.venv\Scripts\python.exe test_crm_sync.py
```

### 4. Run Interactive Copilot CLI
```powershell
.\.venv\Scripts\python.exe app.py
```
