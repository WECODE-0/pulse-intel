# ⚡ PulseIntel

**Enterprise Web Intelligence Platform**  
Built for the Web Data UNLOCKED Hackathon 2026 by **WeCoders**

---

## What Is PulseIntel?

PulseIntel is an enterprise intelligence platform with two layers:

- **GTM Intelligence** — Monitor competitor job postings and generate AI-powered strategy briefs
- **Security & Compliance** — Scan the open web for brand threats, phishing, credential leaks, and impersonation

Powered by **Bright Data MCP Server** for real-time web access and **Groq LLaMA 3.3 70B** for AI analysis.

---

## The Problem

Every company has two blind spots:

1. Competitors are quietly hiring ML engineers and fraud analysts — revealing their next product move — but nobody is reading thousands of job postings and connecting the dots manually.

2. Phishing pages, fake domains, and credential dumps appear on the open web daily — but security teams find out only after customers complain. Internal tools cannot monitor what is outside the firewall.

PulseIntel solves both problems with one platform.

---

## How It Works
You enter a company or brand name
↓
Bright Data MCP Server searches + scrapes the open web
(bypasses bot detection, JS rendering, geo-blocks)
↓
Raw data saved to SQLite database
↓
Groq AI (LLaMA 3.3 70B) analyzes the data
↓
Results shown on Streamlit dashboard

---

## Features

### Track 1 — GTM Intelligence
- Scrapes job postings from LinkedIn, Greenhouse, Lever, and company career pages
- Deduplicates and filters noise automatically
- AI generates a structured strategy brief:
  - What is this company building?
  - Which departments are growing?
  - Which competitors should be concerned?
  - Expected timeline

### Track 2 — Security & Compliance
- Scans paste sites, social media, and open web for brand mentions
- Detects phishing campaigns, credential leaks, lookalike domains, impersonation
- AI scores each finding from 1 to 10 by risk level
- Filters by CRITICAL, HIGH, MEDIUM, LOW
- Provides recommended action for each threat

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Scraping | Bright Data MCP Server |
| AI Analysis | Groq — LLaMA 3.3 70B |
| Language | Python 3.10+ |
| Parsing | BeautifulSoup4, lxml |
| Database | SQLite |
| Dashboard | Streamlit |
| Async | Python asyncio + MCP client |

---

## Project Structure
pulseintel/
├── .env                     # API keys
├── requirements.txt
├── README.md
├── pipeline/
│   └── database.py          # SQLite tables and helpers
├── scrapers/
│   ├── jobs_scraper.py      # Scrapes job postings
│   └── brand_scraper.py     # Scrapes brand mentions
├── llm/
│   ├── gtm_analyzer.py      # Jobs → strategy brief
│   └── threat_analyzer.py   # Mentions → threat alerts
└── dashboard/
└── app.py               # Streamlit UI

---

## Setup

### Requirements
- Python 3.10+
- Node.js 18+
- Bright Data account
- Groq account

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/pulseintel.git
cd pulseintel
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
npm install -g @brightdata/mcp
```

### Step 4 — Create .env file
```env
BRIGHT_DATA_API_TOKEN=your_brightdata_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

**Getting API Keys:**
- Bright Data → brightdata.com → Account Settings → API Keys → use promo code `unlocked` for $250 free credits
- Groq → console.groq.com → free tier available

### Step 5 — Initialize database
```bash
python pipeline/database.py
```

### Step 6 — Run the dashboard
```bash
streamlit run dashboard/app.py
```

Visit `http://localhost:8501` in your browser.

---

## Usage

### GTM Intelligence
1. Go to the GTM Intelligence tab
2. Type a company name — example: `Stripe`
3. Click **Analyze**
4. Wait 30 seconds for scraping and analysis
5. Read the strategy brief

### Security & Compliance
1. Go to the Security & Compliance tab
2. Type a brand name — example: `PayPal`
3. Click **Scan**
4. Wait 60 seconds for scanning and analysis
5. Use the filter to view threats by risk level

---

## Why Bright Data?

Without Bright Data, scraping LinkedIn, Greenhouse, Pastebin, and
social media reliably at scale is nearly impossible due to:

- Bot detection and IP blocking
- JavaScript rendered pages
- Geo-restrictions
- Rate limiting

Bright Data MCP Server handles all of this automatically.
It returns clean markdown directly — perfect for feeding into an LLM.
Free tier includes 5,000 requests per month.

---

## Hackathon Tracks

| Track | Description |
|---|---|
| Track 1 — GTM Intelligence | Competitor hiring signals and strategy briefs |
| Track 3 — Security & Compliance | Brand threat detection and risk scoring |

PulseIntel competes in both tracks with a single submission.

---

## Team

**WeCoders** — Web Data UNLOCKED Hackathon 2026

---

## License

MIT