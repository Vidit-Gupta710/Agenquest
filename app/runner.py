"""Run one journey with a TinyFish agent and turn the run into a TaskResult."""
import asyncio
from datetime import datetime

from app import tasks, tinyfish

SLOTS = asyncio.Semaphore(2)  # pay-as-you-go allows 2 agents at once


def _seconds(run):
    t = [run.get(k) for k in ("started_at", "finished_at")]
    if not all(t):
        return 0.0
    a, b = (datetime.fromisoformat(x.replace("Z", "+00:00")) for x in t)
    return round((b - a).total_seconds(), 1)


async def run_task(url, jid, query, emit, profile_id=None):
    async def on_update(run):
        steps = run.get("steps") or []
        await emit(
            "task_update", task_id=jid, status=run["status"], steps=len(steps),
            streaming_url=run.get("streaming_url"),
            last_action=(steps[-1].get("action") if steps else None),
        )

    signed_in = profile_id is not None
    try:
        async with SLOTS:
            run = await tinyfish.run_agent(
                url, tasks.goal(jid, query, signed_in), tasks.schema(jid),
                on_update=on_update, profile_id=profile_id,
            )
    except Exception as e:  # one bad journey must never crash the audit
        run = {"status": "FAILED", "error": {"message": str(e)}}

    steps = run.get("steps") or []
    jr = tasks.JOURNEYS[jid]
    result = {
        "id": jid, "label": jr["label"], "signed_in": signed_in,
        "milestones": jr["milestones"], "expected_steps": jr["steps"],
        **tinyfish.parse_result(run),
        "steps": run.get("num_of_steps") or len(steps),
        "seconds": _seconds(run), "run_id": run.get("run_id"),
        "trace": [s.get("action") for s in steps][-15:],
    }
    return {**result, "progress": round(tasks.progress(result), 2)}
