"""Background jobs that stream events to the browser over SSE."""
import asyncio
import uuid

QUEUES: dict[str, asyncio.Queue] = {}
JOBS: set[asyncio.Task] = set()


def start_job(work) -> dict:
    """work(emit) is any coroutine function; its events go to /api/audit/{id}/events."""
    job_id = uuid.uuid4().hex[:8]
    queue = QUEUES[job_id] = asyncio.Queue()

    async def emit(event: str, **data) -> None:
        await queue.put({"type": event, **data})

    async def job() -> None:
        try:
            await work(emit)
        except Exception as e:
            await emit("error", message=str(e), recoverable=False)
        finally:
            await queue.put(None)

    task = asyncio.create_task(job())
    JOBS.add(task)
    task.add_done_callback(JOBS.discard)
    return {"audit_id": job_id}
