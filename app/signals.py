"""Machine-readability signals and competitor discovery via TinyFish Fetch and Search."""
import asyncio
import re
from urllib.parse import urlparse

from app import tinyfish
from app.score import readability

PATHS = ["/", "/robots.txt", "/llms.txt", "/sitemap.xml"]
BAD = {"bot_blocked", "login_required", "target_http_error", "target_unreachable", "timeout"}
AI_BOTS = (r"\*", "gptbot", "claudebot", "perplexitybot", "google-extended")
SKIP = ("wikipedia", "youtube", "reddit", "quora", "facebook", "instagram", "linkedin", "medium")


def root(url):
    p = urlparse(url if "://" in url else f"https://{url}")
    return f"{p.scheme}://{p.netloc}"


def robots_ok(text):
    """robots.txt exists and does not disallow everything for all or for AI agents."""
    t = text.lower()
    return bool(t) and not any(
        re.search(rf"user-agent:\s*{bot}\s*\ndisallow:\s*/\s*$", t, re.M) for bot in AI_BOTS
    )


def signals_from(base, out):
    """Pure function: Fetch output -> signals. Unit-tested."""
    got = {r["url"]: r for r in out.get("results", [])}
    err = {e["url"]: e["error"] for e in out.get("errors", [])}
    home, llms = got.get(base + "/", {}), got.get(base + "/llms.txt", {})
    return {
        "fetchable": err.get(base + "/") not in BAD,
        "text_rendered": len(home.get("text") or "") > 500,
        "llms_txt": len(llms.get("text") or "") > 20
        and (llms.get("final_url") or "").endswith("llms.txt"),
        "robots_ok": robots_ok((got.get(base + "/robots.txt") or {}).get("text") or ""),
        "sitemap": base + "/sitemap.xml" in got,
        "meta": bool(home.get("title") and home.get("description")),
        "fetch_error": err.get(base + "/"),
    }


async def read_site(url):
    base = root(url)
    out = await tinyfish.fetch([base + p for p in PATHS])
    home = next((r for r in out["results"] if r["url"] == base + "/"), {})
    return signals_from(base, out), (home.get("text") or "")[:4000]


async def peers(url, query, n=3):
    """Pick up to n real competitors: skip the audited domain, SKIP list, and bot-blocked sites."""
    mine = urlparse(root(url)).netloc.removeprefix("www.")
    found = [
        urlparse(r["url"]).netloc.removeprefix("www.") for r in await tinyfish.search(query)
    ]
    # fetch a wider pool so we can drop ones where TinyFish Fetch itself fails
    pool = list(
        dict.fromkeys(d for d in found if d and d != mine and not any(s in d for s in SKIP))
    )[: n * 3]
    sigs = await asyncio.gather(*(read_site(f"https://{d}") for d in pool), return_exceptions=True)
    scored = []
    for d, result in zip(pool, sigs):
        if isinstance(result, Exception):
            continue
        s, _ = result
        # drop peers where Fetch was bot-blocked / unreachable: all-false signals are uninformative
        if not s.get("fetchable") or not s.get("text_rendered"):
            continue
        scored.append({"domain": d, "signals": s, "readability": readability(s)})
    return scored[:n]