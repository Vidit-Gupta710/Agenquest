"""Every TinyFish call: Fetch, Search, Agent run + parse_result."""

import asyncio
import json
import os

import httpx
from app.cache import cached

HEAD = {"X-API-Key": os.getenv("TINYFISH_API_KEY", "")}
AGENT = "https://agent.tinyfish.ai/v1"
DONE = {"COMPLETED", "FAILED", "CANCELLED"}


@cached
async def fetch(urls):
    async with httpx.AsyncClient(timeout=150) as c:
        r = await c.post(
            "https://api.fetch.tinyfish.ai",
            headers=HEAD,
            json={"urls": urls, "format": "markdown", "links": True},
        )
        r.raise_for_status()
        return r.json()


@cached
async def search(query, location="IN"):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            "https://api.search.tinyfish.ai",
            headers=HEAD,
            params={"query": query, "location": location},
        )
        r.raise_for_status()
        return r.json()["results"]


@cached
async def run_agent(url, goal, schema, on_update=None):
    body = {
        "url": url,
        "goal": goal,
        "output_schema": schema,
        "agent_config": {"max_duration_seconds": 150},
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{AGENT}/automation/run-async", headers=HEAD, json=body)
        r.raise_for_status()
        run_id = r.json()["run_id"]
        while True:
            run = (
                await c.get(
                    f"{AGENT}/runs/{run_id}",
                    headers=HEAD,
                    params={"screenshots": "none"},
                )
            ).json()
            if on_update:
                await on_update(run)
            if run["status"] in DONE:
                return run
            await asyncio.sleep(3)


def parse_result(run):
    res = run.get("result") or {}
    if isinstance(res, str):
        res = json.loads(res) if res.strip().startswith("{") else {}
    if run["status"] != "COMPLETED":
        return {
            "outcome": "failure",
            "blocker": "other",
            "blocker_detail": (run.get("error") or {}).get("message"),
        }
    return {"outcome": "failure", "blocker": "other", **res}
