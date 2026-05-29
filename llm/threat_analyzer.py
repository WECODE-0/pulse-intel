import os
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from groq import Groq
from pipeline.database import get_connection, mark_mentions_analyzed

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Build prompt from mentions ───────────────────────────────
def build_prompt(brand: str, mentions: list) -> str:
    mentions_text = ""
    for i, mention in enumerate(mentions, 1):
        mentions_text += f"""
{i}. Type: {mention['mention_type']}
   URL: {mention['source_url']}
   Content: {mention['raw_content'][:200]}
"""

    prompt = f"""
You are a cybersecurity analyst specializing in brand protection.
Analyze these web mentions of "{brand}" and identify threats.

MENTIONS FOUND:
{mentions_text}

Analyze these and return a JSON array of threats in this EXACT format:
[
    {{
        "threat_type": "phishing / credential_leak / lookalike_domain / impersonation / other",
        "risk_level": "CRITICAL / HIGH / MEDIUM / LOW",
        "risk_score": <number 1-10>,
        "source_url": "the url of this threat",
        "summary": "One sentence explaining this specific threat",
        "recommended_action": "What should the security team do about this?"
    }}
]

Rules:
- Only include genuine threats, skip irrelevant mentions
- CRITICAL = active phishing or credential dump
- HIGH = lookalike domain or impersonation
- MEDIUM = suspicious mention or potential risk
- LOW = minor brand misuse
- Return ONLY the JSON array, no extra text
"""
    return prompt

# ── Call Groq API ────────────────────────────────────────────
def analyze_threats(brand: str, mentions: list) -> list:
    if not mentions:
        print(f"⚠️  No mentions to analyze for {brand}")
        return []

    print(f"🤖 AI analyzing {len(mentions)} mentions for {brand}...")

    # send in batches of 20 to avoid token limits
    batch_size = 20
    all_threats = []

    for i in range(0, len(mentions), batch_size):
        batch = mentions[i:i + batch_size]
        print(f"  📦 Processing batch {i//batch_size + 1}...")

        time.sleep(10)

        prompt = build_prompt(brand, batch)

        try:
            message = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = message.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            threats = json.loads(raw)

            if isinstance(threats, list):
                all_threats.extend(threats)
                print(f"  ✅ Batch {i//batch_size + 1} → {len(threats)} threats found")

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parse error in batch: {e}")
            continue
        except Exception as e:
            print(f"  ❌ API error in batch: {e}")
            continue

    print(f"\n✅ Total threats identified: {len(all_threats)}")
    return all_threats

# ── Save threats to database ─────────────────────────────────
def save_threats(brand: str, threats: list) -> int:
    if not threats:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    saved = 0

    for threat in threats:
        try:
            cursor.execute("""
                INSERT INTO threat_alerts
                (brand, threat_type, risk_level, risk_score, source_url, summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                brand,
                threat.get("threat_type", ""),
                threat.get("risk_level", ""),
                threat.get("risk_score", 0),
                threat.get("source_url", ""),
                threat.get("summary", "")
            ))
            saved += 1
        except Exception as e:
            print(f"  ⚠️ Save error: {e}")
            continue

    conn.commit()
    conn.close()
    print(f"💾 Saved {saved} threat alerts to database.")
    return saved

# ── Fetch mentions from DB ───────────────────────────────────
def get_mentions_for_brand(brand: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM brand_mentions
        WHERE brand = ? AND analyzed = 0
    """, (brand,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ── Fetch saved threats from DB ──────────────────────────────
def get_threats_for_brand(brand: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM threat_alerts
        WHERE brand = ?
        ORDER BY risk_score DESC
    """, (brand,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ── Main function ────────────────────────────────────────────
def run_threat_analysis(brand: str) -> list:
    """Main entry point — analyze mentions and generate threat alerts."""
    mentions = get_mentions_for_brand(brand)

    if not mentions:
        print(f"⚠️  No unanalyzed mentions found for {brand}")
        print("    Run brand_scraper.py first!")
        return []

    print(f"📋 Found {len(mentions)} unanalyzed mentions for {brand}")

    threats = analyze_threats(brand, mentions)

    if threats:
        save_threats(brand, threats)
        mark_mentions_analyzed(brand)

    return threats

# ── Test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    brand = "PayPal"
    threats = run_threat_analysis(brand)

    if threats:
        print("\n" + "="*50)
        print("🛡️  THREAT REPORT")
        print("="*50)

        # sort by risk score
        threats_sorted = sorted(
            threats,
            key=lambda x: x.get("risk_score", 0),
            reverse=True
        )

        for threat in threats_sorted[:5]:
            risk = threat.get("risk_level", "")
            emoji = "🔴" if risk == "CRITICAL" else "🟠" if risk == "HIGH" else "🟡" if risk == "MEDIUM" else "🟢"

            print(f"\n{emoji} Risk Level  : {risk} ({threat.get('risk_score')}/10)")
            print(f"🏷️  Type       : {threat.get('threat_type')}")
            print(f"🔗 URL        : {threat.get('source_url')}")
            print(f"📄 Summary    : {threat.get('summary')}")
            print(f"✅ Action     : {threat.get('recommended_action')}")