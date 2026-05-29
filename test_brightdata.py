import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BRIGHT_DATA_API_TOKEN")

async def test_search():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": API_TOKEN,
            "PATH": os.environ.get("PATH", "")
        }
    )

    print("Connecting to Bright Data MCP...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected successfully!")

            # Test 1 — search Google
            print("\nTesting search...")
            result = await session.call_tool(
                "search_engine",
                arguments={"query": "Stripe jobs machine learning"}
            )
            print("Search result preview:")
            print(result.content[0].text[:500])

            # Test 2 — scrape a page
            print("\nTesting scrape...")
            page = await session.call_tool(
                "scrape_as_markdown",
                arguments={"url": "https://httpbin.org/ip"}
            )
            print("Scrape result:")
            print(page.content[0].text[:300])

if __name__ == "__main__":
    asyncio.run(test_search())