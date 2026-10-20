"""The 6-step audit pipeline. Emits events as it goes; returns and saves the report."""
import asyncio
import json
import pathlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from app import diagnose, score, signals, tasks
from app.runner import run_task

REPORTS = pathlib.Path("data/reports")
REPORTS.mkdir(parents=True, exist_ok=True)


async def _task(url, task_id, query, emit):
    result = await run_task(url, task_id, query, emit)
    await emit("task_done", task=result)
    return result


async def _peers(url, query):
    try:
        return await signals.peers(url, query)
    except Exception:
        return []  # peers are a bonus, never a blocker


async def audit(url, emit):
    await emit("stage", stage="signals")
    sig, home = await signals.read_site(url)
    await emit("signals", signals=sig)

    await emit("stage", stage="classify")
    plan = await tasks.plan(url, home)
    await emit("tasks", tasks=[{"id": t, "label": tasks.TASKS[t]["label"]} for t in plan["task_ids"]])

    await emit("stage", stage="tasks")
    peers_task = asyncio.create_task(_peers(url, plan.get("peer_query", "")))
    results = await asyncio.gather(*(_task(url, t, plan.get("query", ""), emit) for t in plan["task_ids"]))

    await emit("stage", stage="diagnose")
    diags = await diagnose.diagnose_all(results, url)
    for d in diags:
        await emit("diagnosis", diagnosis=d)

    report = {
        "url": url,
        "domain": urlparse(signals.root(url)).netloc,
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site_type": plan["site_type"],
        "summary": plan.get("summary"),
        "signals": sig,
        "tasks": results,
        "diagnoses": diags,
        "score": score.score(results, sig),
        "agent_tax": score.agent_tax(results),
        "peers": await peers_task,
    }
    await emit("score", score=report["score"], agent_tax=report["agent_tax"])
    await emit("peers", peers=report["peers"])

    (REPORTS / f"{report['domain']}.json").write_text(json.dumps(report, indent=2))
    await emit("done", report=report)
    return report