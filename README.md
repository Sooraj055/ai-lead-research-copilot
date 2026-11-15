# AI Lead-Research and Outreach Copilot

A modular, human-in-the-loop AI sales research and outreach system.

## Project Vision
Automates researching prospective client websites, extracting core company information, assessing alignment against an Ideal Customer Profile (ICP), scoring leads transparently, and drafting personalized multi-channel outreach (Email and LinkedIn) for human review before synchronization with HubSpot CRM.

---

## Current Status
- [x] **Stage 1: Project Setup and Website Scraping** (Completed & Tested)
- [x] **Stage 2: Company Information Extraction** (Completed & Tested)
- [ ] **Stage 3: AI Integration & Business Analysis**
- [ ] **Stage 4: Ideal Customer Profile & Lead Scoring**
- [ ] **Stage 5: Personalized Outreach Generation**
- [ ] **Stage 6: Human Approval & HubSpot Integration**
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
├── .env.example           # Template for environment variables
├── app.py                 # Interactive command-line pipeline (Scrape + Extract)
├── test_scraper.py        # Automated test suite for Stage 1 (Scraper)
├── test_extractor.py      # Automated test suite for Stage 2 (Extractor)
│
├── research/              # Scraping and research engine module
│   ├── __init__.py        # Exports scrape_website and extract_company_info
│   ├── scraper.py         # Requests & BeautifulSoup clean text extractor
│   └── extractor.py       # AI-powered grounded company profile extractor
│
└── data/                  # Output storage for scraped leads and company profiles
    ├── sample_scrape.json
    └── company_profile.json
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Git
- Google Gemini API key (Free at https://aistudio.google.com)

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and paste your Gemini API key:
```bash
GEMINI_API_KEY="AIzaSy..."
```

### 3. Run Automated Tests
```powershell
# Test Stage 1 Scraper:
.\.venv\Scripts\python.exe test_scraper.py

# Test Stage 2 Extractor:
.\.venv\Scripts\python.exe test_extractor.py
```

### 4. Run the Copilot CLI Pipeline
```powershell
.\.venv\Scripts\python.exe app.py
```
