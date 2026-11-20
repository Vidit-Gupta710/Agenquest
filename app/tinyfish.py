"""Every TinyFish call: Fetch, Search, Agent run (+ profiles) + parse_result."""

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
async def run_agent(url, goal, schema, on_update=None, profile_id=None):
    """Start a web agent (optionally signed in via a saved profile) and poll until it ends."""
    body = {
        "url": url,
        "goal": goal,
        "output_schema": schema,
        "agent_config": {"max_duration_seconds": 300},
    }
    if profile_id:
        body |= {"use_profile": True, "profile_id": profile_id}
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


async def _call(method, path, **kw):
    """Profile endpoints are never cached: they change real account state."""
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.request(method, f"{AGENT}{path}", headers=HEAD, **kw)
        r.raise_for_status()
        return r.json() if r.content else {}


async def create_profile(name):
    return await _call("POST", "/profiles", json={"name": name})


async def start_setup(profile_id, login_url):
    return await _call(
        "POST", f"/profiles/{profile_id}/setup-session",
        json={"url": login_url, "timeout_seconds": 900},
    )


async def save_setup(profile_id, session_id, sites):
    return await _call(
        "POST", f"/profiles/{profile_id}/save",
        json={"session_id": session_id, "signed_in_sites": sites},
    )


async def cancel_setup(profile_id, session_id):
    return await _call(
        "POST", f"/profiles/{profile_id}/setup-session/cancel",
        json={"session_id": session_id},
    )


async def delete_profile(profile_id):
    return await _call("DELETE", f"/profiles/{profile_id}")


def parse_result(run):
    res = run.get("result") or {}
    if isinstance(res, str):
        res = json.loads(res) if res.strip().startswith("{") else {}
    if run["status"] != "COMPLETED":
        return {
            "outcome": "failure",
            "furthest_milestone": "none",
            "blocker": "other",
            "blocker_detail": (run.get("error") or {}).get("message"),
        }
    return {"outcome": "failure", "furthest_milestone": "none", "blocker": "other", **res}
