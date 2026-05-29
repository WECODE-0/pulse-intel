import os
import sys
import json
from groq import Groq

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pipeline.database import get_connection, mark_jobs_analyzed

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Build prompt from jobs ───────────────────────────────────
def build_prompt(company: str, jobs: list) -> str:
    jobs_text = ""
    for i, job in enumerate(jobs, 1):
        jobs_text += f"{i}. {job['title']}\n"
        if job.get('description'):
            jobs_text += f"   Description: {job['description'][:150]}\n"
        jobs_text += f"   URL: {job['source_url']}\n\n"

    prompt = f"""
You are a competitive intelligence analyst. 
Analyze these recent job postings from {company} and extract strategic signals.

JOB POSTINGS:
{jobs_text}

Based on these job postings, provide a structured analysis in this EXACT JSON format:
{{
    "company": "{company}",
    "signal": "One sentence — what is this company building or planning?",
    "intel": "2-3 sentences of deeper analysis — what do these hires reveal about strategy?",
    "confidence": "High / Medium / Low",
    "expected_timeline": "When might this launch or become visible? e.g. Q3 2026",
    "key_roles": ["list", "of", "most", "strategic", "job", "titles"],
    "departments_hiring": ["list", "of", "departments"],
    "threat_to_competitors": "Which competitors should be most concerned and why?"
}}

Return ONLY the JSON. No explanation, no markdown, no extra text.
"""
    return prompt

# ── Call Groq API ──────────────────────────────────────────
def analyze_jobs(company: str, jobs: list) -> dict:
    if not jobs:
        print(f"⚠️  No jobs to analyze for {company}")
        return {}

    print(f"🤖 Groq analyzing {len(jobs)} jobs for {company}...")

    prompt = build_prompt(company, jobs)

    try:
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.choices[0].message.content.strip()

        # clean any accidental markdown
        raw = raw.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw)
        print(f"✅ Analysis complete for {company}")
        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"Raw response: {raw}")
        return {}
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return {}

def save_brief(brief: dict):
    if not brief:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO strategy_briefs
        (company, signal, intel, confidence, 
         expected_timeline, jobs_analyzed, threat_to_competitors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        brief.get("company", ""),
        brief.get("signal", ""),
        brief.get("intel", ""),
        brief.get("confidence", ""),
        brief.get("expected_timeline", ""),
        brief.get("jobs_analyzed", 0),
        brief.get("threat_to_competitors", "")
    ))

    conn.commit()
    conn.close()
    print(f"💾 Strategy brief saved to database.")

# ── Fetch jobs from DB ───────────────────────────────────────
def get_jobs_for_company(company: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM job_postings
        WHERE company = ? AND analyzed = 0
    """, (company,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ── Main function ────────────────────────────────────────────
def run_gtm_analysis(company: str) -> dict:
    """Main entry point — analyze jobs and generate strategy brief."""
    jobs = get_jobs_for_company(company)

    if not jobs:
        print(f"⚠️  No unanalyzed jobs found for {company}")
        print("    Run jobs_scraper.py first!")
        return {}

    print(f"📋 Found {len(jobs)} unanalyzed jobs for {company}")

    brief = analyze_jobs(company, jobs)

    if brief:
        brief["jobs_analyzed"] = len(jobs)
        save_brief(brief)
        mark_jobs_analyzed(company)

    return brief

# ── Test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    company = "Stripe"
    result = run_gtm_analysis(company)

    if result:
        print("\n" + "="*50)
        print("📊 STRATEGY BRIEF")
        print("="*50)
        print(f"🏢 Company       : {result.get('company')}")
        print(f"📡 Signal        : {result.get('signal')}")
        print(f"🔍 Intel         : {result.get('intel')}")
        print(f"💪 Confidence    : {result.get('confidence')}")
        print(f"📅 Timeline      : {result.get('expected_timeline')}")
        print(f"👥 Key Roles     : {', '.join(result.get('key_roles', []))}")
        print(f"🏗️  Departments   : {', '.join(result.get('departments_hiring', []))}")
        print(f"⚔️  Threat To     : {result.get('threat_to_competitors')}")