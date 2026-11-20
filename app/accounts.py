"""My Account mode routes: connect an account, save the session, run signed-in jobs."""
import json
import pathlib
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel

from app import cart, remote_login, tinyfish
from app.jobs import start_job

router = APIRouter()
STORE = pathlib.Path("data/accounts.json")
SETUPS: dict[str, dict] = {}


def _load():
    return json.loads(STORE.read_text()) if STORE.exists() else {"sites": {}}


def _save(d):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=2))


def _site(url):
    return urlparse(url if "://" in url else f"https://{url}").netloc


async def _profile_id():
    d = _load()
    if "profile_id" not in d:
        d["profile_id"] = (await tinyfish.create_profile("agentlighthouse-user"))["id"]
        _save(d)
    return d["profile_id"]


class ConnectIn(BaseModel):
    login_url: str


class RunIn(BaseModel):
    site: str
    request: str
    action: str = "cart"  # cart | apply_job | connect_note | message_draft


@router.get("/api/accounts")
def accounts():
    return _load()["sites"]


@router.post("/api/accounts/connect")
async def connect(body: ConnectIn):
    pid = await _profile_id()
    s = await tinyfish.start_setup(pid, body.login_url)
    SETUPS[s["session_id"]] = {"cdp_url": s["cdp_url"], "url": body.login_url, "pid": pid}
    return {"session_id": s["session_id"], "expires_at": s.get("expires_at")}


@router.websocket("/ws/login/{session_id}")
async def login_window(ws: WebSocket, session_id: str):
    setup = SETUPS.get(session_id)
    await ws.accept()
    if setup is None:
        return await ws.close(code=4404)
    await remote_login.bridge(ws, setup["cdp_url"], setup["url"])


@router.post("/api/accounts/save/{session_id}")
async def save(session_id: str):
    setup = SETUPS.pop(session_id, None)
    if setup is None:
        raise HTTPException(404, "login window expired; connect again")
    site = _site(setup["url"])
    await tinyfish.save_setup(setup["pid"], session_id, [site])
    d = _load()
    d["sites"][site] = {"saved_at": int(time.time())}
    _save(d)
    return {"site": site, "connected": True}


@router.delete("/api/accounts")
async def disconnect_all():
    d = _load()
    if "profile_id" in d:
        try:
            await tinyfish.delete_profile(d["profile_id"])
        except Exception:
            pass  # profile may already be gone
    _save({"sites": {}})
    return {"connected": False}


@router.post("/api/accounts/run")
async def run(body: RunIn):
    d = _load()
    if body.site not in d["sites"]:
        raise HTTPException(409, "connect this account first")
    return start_job(
        lambda emit: cart.run(body.site, body.request, body.action, d["profile_id"], emit)
    )
