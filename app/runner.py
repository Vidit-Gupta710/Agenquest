"""Run one task with a TinyFish agent and turn the run into a TaskResult."""

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


async def run_task(url, task_id, query, emit):
    async def on_update(run):
        await emit(
            "task_update",
            task_id=task_id,
            status=run["status"],
            steps=len(run.get("steps") or []),
            streaming_url=run.get("streaming_url"),
        )

    try:
        async with SLOTS:
            run = await tinyfish.run_agent(
                url, tasks.goal(task_id, query), tasks.SCHEMA, on_update=on_update
            )
    except Exception as e:  # one bad task must never crash the audit
        run = {"status": "FAILED", "error": {"message": str(e)}}

    steps = run.get("steps") or []
    return {
        "id": task_id,
        "label": tasks.TASKS[task_id]["label"],
        "expected_steps": tasks.TASKS[task_id]["steps"],
        **tinyfish.parse_result(run),
        "steps": run.get("num_of_steps") or len(steps),
        "seconds": _seconds(run),
        "run_id": run.get("run_id"),
        "trace": [s.get("action") for s in steps][-15:],
    }
