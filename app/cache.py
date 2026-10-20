"""Disk cache + DEMO_MODE replay for all external calls."""

import functools
import hashlib
import json
import os
import pathlib

DIR = pathlib.Path("data/cache")
DIR.mkdir(parents=True, exist_ok=True)


def cached(fn):
    @functools.wraps(fn)
    async def wrap(*args, **kw):
        plain = [a for a in args if not callable(a)]
        plain += sorted((k, v) for k, v in kw.items() if not callable(v))
        key = hashlib.sha1(json.dumps([fn.__name__, plain], default=str).encode())
        path = DIR / f"{fn.__name__}-{key.hexdigest()[:16]}.json"
        if path.exists():
            return json.loads(path.read_text())
        if os.getenv("DEMO_MODE") == "1":
            raise RuntimeError(f"DEMO_MODE: nothing cached for {fn.__name__}")
        out = await fn(*args, **kw)
        if not (isinstance(out, dict) and out.get("status") == "FAILED"):
            path.write_text(json.dumps(out))
        return out

    return wrap
