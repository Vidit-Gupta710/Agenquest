"""Phase 0 check: one Fetch, one Search, one tiny agent run, one LLM call."""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from app import llm, tinyfish  # noqa: E402
from app.tasks import SCHEMA  # noqa: E402

GOAL = (
    "Report the main heading of this page in 'answer'. "
    "Set outcome to success if you found it, and blocker to none."
)


async def main():
    f = await tinyfish.fetch(["https://example.com"])
    print("FETCH OK :", f["results"][0]["title"])
    s = await tinyfish.search("online bookstore india")
    print("SEARCH OK:", [r["url"] for r in s[:3]])
    run = await tinyfish.run_agent("https://example.com", GOAL, SCHEMA)
    print("AGENT    :", run["status"], run.get("num_of_steps"), tinyfish.parse_result(run))
    print("LLM OK   :", await llm.ask_json("Reply only in JSON.", 'Return {"ok": true}'))


asyncio.run(main())
