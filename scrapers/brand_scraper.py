import asyncio
import os
import json
import hashlib
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pipeline.database import get_connection, init_db

load_dotenv()

API_TOKEN = os.getenv("BRIGHT_DATA_API_TOKEN")

# ── MCP Connection ──────────────────────────────────────────
def get_server_params():
    return StdioServerParameters(
        command="npx",
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": API_TOKEN,
            "PATH": os.environ.get("PATH", "")
        }
    )

# ── Search paste sites ──────────────────────────────────────
async def search_paste_sites(session, brand_name: str) -> list:
    """Search for brand mentions on paste sites."""
    query = f'"{brand_name}" site:pastebin.com OR site:paste.ee OR site:rentry.co'
    mentions = []

    try:
        result = await session.call_tool(
            "search_engine",
            arguments={"query": query}
        )
        data = json.loads(result.content[0].text)
        organic = data.get("organic", [])

        for item in organic:
            mentions.append({
                "brand": brand_name,
                "source_url": item.get("link", ""),
                "mention_type": "paste_site",
                "raw_content": f"{item.get('title','')} | {item.get('description','')}"
            })

        print(f"  ✅ Paste sites → {len(mentions)} results")

    except Exception as e:
        print(f"  ❌ Paste site search failed: {e}")

    return mentions

# ── Search lookalike domains ────────────────────────────────
async def search_lookalike_domains(session, brand_name: str) -> list:
    """Search for typosquat and lookalike domains."""
    brand_lower = brand_name.lower().replace(" ", "")

    queries = [
        f"{brand_lower}-login.com",
        f"{brand_lower}-secure.com",
        f"login-{brand_lower}.com",
        f"{brand_lower}-support.com",
        f"{brand_lower}-verify.com",
    ]

    mentions = []

    for query in queries:
        try:
            result = await session.call_tool(
                "search_engine",
                arguments={"query": query}
            )
            data = json.loads(result.content[0].text)
            organic = data.get("organic", [])

            for item in organic:
                link = item.get("link", "")
                # only flag if brand name appears in the URL
                if brand_lower in link.lower() and link:
                    mentions.append({
                        "brand": brand_name,
                        "source_url": link,
                        "mention_type": "lookalike_domain",
                        "raw_content": f"{item.get('title','')} | {item.get('description','')}"
                    })

        except Exception as e:
            print(f"  ❌ Lookalike search failed for {query}: {e}")
            continue

    print(f"  ✅ Lookalike domains → {len(mentions)} results")
    return mentions

# ── Search social impersonation ─────────────────────────────
async def search_social_impersonation(session, brand_name: str) -> list:
    """Search for fake/impersonation profiles on social media."""
    queries = [
        f'"{brand_name}" fake account report site:twitter.com',
        f'"{brand_name}" impersonation scam site:linkedin.com',
        f'"{brand_name}" phishing warning',
    ]

    mentions = []

    for query in queries:
        try:
            result = await session.call_tool(
                "search_engine",
                arguments={"query": query}
            )
            data = json.loads(result.content[0].text)
            organic = data.get("organic", [])

            for item in organic:
                mentions.append({
                    "brand": brand_name,
                    "source_url": item.get("link", ""),
                    "mention_type": "social_impersonation",
                    "raw_content": f"{item.get('title','')} | {item.get('description','')}"
                })

        except Exception as e:
            print(f"  ❌ Social search failed: {e}")
            continue

    print(f"  ✅ Social impersonation → {len(mentions)} results")
    return mentions

# ── Search credential leaks ─────────────────────────────────
async def search_credential_leaks(session, brand_name: str) -> list:
    """Search for credential or data leaks mentioning the brand."""
    queries = [
        f'"{brand_name}" credentials leaked dump',
        f'"{brand_name}" data breach passwords',
        f'"{brand_name}" email password list',
    ]

    mentions = []

    for query in queries:
        try:
            result = await session.call_tool(
                "search_engine",
                arguments={"query": query}
            )
            data = json.loads(result.content[0].text)
            organic = data.get("organic", [])

            for item in organic:
                mentions.append({
                    "brand": brand_name,
                    "source_url": item.get("link", ""),
                    "mention_type": "credential_leak",
                    "raw_content": f"{item.get('title','')} | {item.get('description','')}"
                })

        except Exception as e:
            print(f"  ❌ Credential leak search failed: {e}")
            continue

    print(f"  ✅ Credential leaks → {len(mentions)} results")
    return mentions

# ── Hash mention to avoid duplicates ────────────────────────
def hash_mention(mention: dict) -> str:
    unique = f"{mention['brand']}_{mention['source_url']}_{mention['mention_type']}"
    return hashlib.md5(unique.encode()).hexdigest()

# ── Save mentions to database ────────────────────────────────
def save_mentions(mentions: list) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0

    for mention in mentions:
        mention_hash = hash_mention(mention)
        try:
            cursor.execute("""
                INSERT INTO brand_mentions
                (brand, source_url, mention_type, raw_content, hash)
                VALUES (?, ?, ?, ?, ?)
            """, (
                mention["brand"],
                mention["source_url"],
                mention["mention_type"],
                mention["raw_content"],
                mention_hash
            ))
            saved += 1
        except Exception:
            pass  # duplicate, skip

    conn.commit()
    conn.close()
    print(f"💾 Saved {saved} new brand mentions to database.")
    return saved

# ── Fetch unanalyzed mentions ────────────────────────────────
def get_unanalyzed_mentions(brand: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM brand_mentions
        WHERE brand = ? AND analyzed = 0
    """, (brand,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ── Mark mentions as analyzed ────────────────────────────────
def mark_mentions_analyzed(brand: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE brand_mentions
        SET analyzed = 1
        WHERE brand = ? AND analyzed = 0
    """, (brand,))
    conn.commit()
    conn.close()

# ── Main function ────────────────────────────────────────────
async def scrape_brand_threats(brand_name: str) -> list:
    """Main entry point — scrape all threat sources for a brand."""
    init_db()
    all_mentions = []

    server_params = get_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"🔍 Scanning threats for brand: {brand_name}\n")

            all_mentions += await search_paste_sites(session, brand_name)
            all_mentions += await search_lookalike_domains(session, brand_name)
            all_mentions += await search_social_impersonation(session, brand_name)
            all_mentions += await search_credential_leaks(session, brand_name)

    print(f"\n📦 Total mentions found: {len(all_mentions)}")
    save_mentions(all_mentions)
    return all_mentions

# ── Test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    brand = "PayPal"
    mentions = asyncio.run(scrape_brand_threats(brand))

    print(f"\n--- Sample Results for {brand} ---")
    for mention in mentions[:5]:
        print(f"\n🏷️  Type    : {mention['mention_type']}")
        print(f"🔗  URL     : {mention['source_url']}")
        print(f"📄  Content : {mention['raw_content'][:100]}")