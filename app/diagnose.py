"""LLM reads a failed or slow agent run and explains the blocker and the fix."""
import asyncio
import json
import os

from app import llm
from app.tasks import BLOCKERS

SYSTEM = f"""You are a senior web engineer explaining why an AI web agent struggled on a website.
You get the task, the agent's own report and its last browser actions. Reply in JSON with:
blocker (one of {BLOCKERS}); root_cause (1-2 specific sentences; name the UI element if the
trace mentions it); fix (a concrete change for the site's developers, with a short HTML, ARIA
or robots.txt snippet when useful); severity (high if it blocks purchase or sign-up, medium if
it slows the agent a lot, else low); confidence (0 to 1).
Use only evidence in the input. If the trace is too thin, write "insufficient evidence" as
root_cause and set confidence below 0.4."""

FIELDS = ("label", "outcome", "blocker", "blocker_detail", "answer", "steps",
          "expected_steps", "final_url", "trace")

DEMO_DIAGNOSIS = {
    "blocker": "other",
    "root_cause": "DEMO_MODE: diagnosis not cached. Run without DEMO_MODE=1 to generate real diagnoses.",
    "fix": "Add LLM API key to .env and run audit again.",
    "severity": "low",
    "confidence": 0.1,
}


def needs_diagnosis(t):
    return t.get("outcome") != "success" or t["steps"] > 2 * t["expected_steps"]


async def diagnose(task, url):
    if os.getenv("DEMO_MODE") == "1":
        return {"task_id": task["id"], **DEMO_DIAGNOSIS}
    evidence = {k: task.get(k) for k in FIELDS} | {"site": url}
    d = await llm.ask_json(SYSTEM, json.dumps(evidence))
    if d.get("blocker") not in BLOCKERS:
        d["blocker"] = task.get("blocker") or "other"
    return {"task_id": task["id"], **d}


async def diagnose_all(tasks, url):
    return await asyncio.gather(*(diagnose(t, url) for t in tasks if needs_diagnosis(t)))