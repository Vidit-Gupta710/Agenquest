"""HTTP API: start an audit, stream its events, serve reports and the UI."""
import asyncio
import json
import pathlib
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, field_validator  # noqa: E402

from app.audit import audit  # noqa: E402

app = FastAPI(title="AgentLighthouse")
DATA = pathlib.Path("data")
QUEUES: dict[str, asyncio.Queue] = {}
JOBS: set[asyncio.Task] = set()  # keep references so jobs are not garbage-collected


class AuditIn(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def http_only(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url must be http or https")
        if "://" not in v:
            v = f"https://{v}"
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must be http or https")
        return v


@app.post("/api/audit")
async def start(body: AuditIn) -> dict:
    audit_id = uuid.uuid4().hex[:8]
    queue = QUEUES[audit_id] = asyncio.Queue()

    async def emit(event: str, **data) -> None:
        await queue.put({"type": event, **data})

    async def job() -> None:
        try:
            await audit(body.url, emit)
        except Exception as e:
            await emit("error", message=str(e), recoverable=False)
        finally:
            await queue.put(None)  # end of stream

    task = asyncio.create_task(job())
    JOBS.add(task)
    task.add_done_callback(JOBS.discard)
    return {"audit_id": audit_id}


@app.get("/api/audit/{audit_id}/events")
async def events(audit_id: str) -> StreamingResponse:
    queue = QUEUES.get(audit_id)
    if queue is None:
        raise HTTPException(404, "unknown audit")

    async def stream():
        while (msg := await queue.get()) is not None:
            yield f"data: {json.dumps(msg)}\n\n"
        QUEUES.pop(audit_id, None)

    return StreamingResponse(stream(), media_type="text/event-stream")


def _json(path: pathlib.Path, default):
    return json.loads(path.read_text()) if path.exists() else default


@app.get("/api/report/{domain}")
def report(domain: str) -> dict:
    data = _json(DATA / "reports" / f"{pathlib.Path(domain).name}.json", None)
    if data is None:
        raise HTTPException(404, "no report for this domain")
    return data


@app.get("/api/leaderboard")
def leaderboard() -> list:
    return _json(DATA / "leaderboard.json", [])


app.mount("/", StaticFiles(directory="web", html=True), name="web")