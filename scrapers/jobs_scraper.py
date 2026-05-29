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

SKIP_KEYWORDS = [
    "jobs home", "careers home", "job search",
    "all jobs", "view all", "job board",
    "jobs hiring near you", "jobs university",
    "hiring alert", "jobs near", "browse jobs",
    "search jobs", "find jobs", "job listings",
    "jobs & careers", "work at", "working at",
    "life at", "about us", "company overview",
    "salary", "compensation", "glassdoor",
    "levels.fyi", "ziprecruiter", "indeed.com/q-",
    "web3.career", "captivateiq","squire",
    "finom","1000+", "jobs worldwide",
    "jobs in worldwide",
]

def get_server_params():
    return StdioServerParameters(
        command="npx",
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": API_TOKEN,
            "PATH": os.environ.get("PATH", "")
        }
    )

def is_valid_job(title: str, company: str) -> bool:
    """Filter out generic pages, keep real job titles."""
    title_lower = title.lower()
    company_lower = company.lower()

    generic_patterns = [
        f"{company_lower} jobs",
        f"{company_lower} careers",
        f"{company_lower}: jobs",
        f"{company_lower}: careers",
        f"jobs at {company_lower}",
        f"careers at {company_lower}",
        "1000+",          
        "jobs in worldwide",
        "jobs worldwide",   
    ]
    for pattern in generic_patterns:
        if title_lower.strip() == pattern.strip():
            return False

    for keyword in SKIP_KEYWORDS:
        if keyword in title_lower:
            return False

    if len(title.strip()) < 10:
        return False

    return True

async def search_job_urls(session, company_name: str) -> list:
    """
    Search Google broadly for ALL jobs at a company.
    No hardcoded job types — just find job postings.
    """
    queries = [
        f"{company_name} job opening site:greenhouse.io",
        f"{company_name} job opening site:lever.co",
        f"{company_name} job opening site:linkedin.com/jobs",
        f"{company_name} job opening site:stripe.com/jobs",
        f'"{company_name}" new job opening hiring 2026',
    ]

    # last query uses company's own careers page pattern
    # replace stripe.com with dynamic company domain
    company_domain = company_name.lower().replace(" ", "") + ".com"
    queries[3] = f"{company_name} job opening site:{company_domain}"

    all_urls = []

    for query in queries:
        try:
            result = await session.call_tool(
                "search_engine",
                arguments={"query": query}
            )

            raw = result.content[0].text
            data = json.loads(raw)
            organic = data.get("organic", [])

            for item in organic:
                title = item.get("title", "")
                url = item.get("link", "")
                description = item.get("description", "")

                if is_valid_job(title, company_name) and url:
                    all_urls.append({
                        "title": title,
                        "url": url,
                        "description": description
                    })

            print(f"  ✅ '{query[:55]}' → {len(organic)} results")

        except Exception as e:
            print(f"  ❌ Query failed: {e}")
            continue

    # deduplicate by URL
    seen = set()
    unique_urls = []
    for item in all_urls:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_urls.append(item)

    return unique_urls

async def scrape_job_details(session, url: str) -> str:
    """
    Visit the actual job page and extract full details.
    Returns clean markdown text.
    """
    try:
        result = await session.call_tool(
            "scrape_as_markdown",
            arguments={"url": url}
        )
        content = result.content[0].text

        # keep only first 500 chars to save tokens
        return content[:500]

    except Exception as e:
        return ""

async def search_jobs(company_name: str) -> list:
    """
    Main scraping flow:
    1. Search Google for job URLs broadly
    2. Visit each URL to get real description
    3. Return enriched job list
    """
    all_jobs = []
    server_params = get_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"🔍 Searching ALL jobs for: {company_name}\n")

            # Step 1 — get job URLs from Google
            job_urls = await search_job_urls(session, company_name)
            print(f"\n📋 Found {len(job_urls)} unique job URLs")

            # Step 2 — scrape each job page for details
            print(f"🌐 Scraping job pages for full details...\n")

            for i, job in enumerate(job_urls[:20]):  # limit to 20
                print(f"  [{i+1}/{min(len(job_urls), 20)}] Scraping: {job['title'][:50]}")

                details = await scrape_job_details(session, job["url"])

                # use scraped content if available
                # otherwise fall back to Google description
                description = details if details else job["description"]

                all_jobs.append({
                    "company": company_name,
                    "title": job["title"],
                    "location": "Unknown",
                    "source_url": job["url"],
                    "source_site": "google_search",
                    "description": description
                })

    print(f"\n📦 Total jobs with details: {len(all_jobs)}")
    return all_jobs

def hash_job(job: dict) -> str:
    unique = f"{job['company']}_{job['title']}_{job['source_url']}"
    return hashlib.md5(unique.encode()).hexdigest()

def save_jobs(jobs: list) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0

    for job in jobs:
        job_hash = hash_job(job)
        try:
            cursor.execute("""
                INSERT INTO job_postings
                (company, title, location, source_url, source_site, hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job["company"],
                job["title"],
                job["location"],
                job["source_url"],
                job["source_site"],
                job_hash
            ))
            saved += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"💾 Saved {saved} new jobs to database.")
    return saved

def get_unanalyzed_jobs(company: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM job_postings
        WHERE company = ? AND analyzed = 0
    """, (company,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

async def scrape_company_jobs(company_name: str) -> list:
    """Main entry point."""
    init_db()
    jobs = await search_jobs(company_name)
    save_jobs(jobs)
    return jobs

if __name__ == "__main__":
    company = "Stripe"
    jobs = asyncio.run(scrape_company_jobs(company))

    print(f"\n--- Sample Results for {company} ---")
    for job in jobs[:5]:
        print(f"\n💼 {job['title']}")
        print(f"🔗 {job['source_url']}")
        print(f"📄 {job['description'][:150]}")