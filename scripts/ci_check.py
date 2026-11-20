"""CI gate: send one agent journey to a staging URL; exit 1 if it gets stuck.
Usage: python -m scripts.ci_check <url> [journey] [min_progress]"""
import asyncio
import os
import sys

from dotenv import load_dotenv

os.environ["CACHE"] = "off"
load_dotenv()

from app.diagnose import diagnose_all  # noqa: E402
from app.runner import run_task  # noqa: E402


async def quiet(event, **data):
    pass


def report(t, need, diags):
    ok = t["progress"] >= need
    lines = [
        f"## Agent check: {'passed' if ok else 'blocked the deploy'}",
        f"Journey **{t['label']}**: reached `{t['furthest_milestone']}` "
        f"({t['progress']:.0%}, needed {need:.0%}) in {t['steps']} steps.",
    ]
    for d in diags:
        lines += [f"**Blocker:** {d['blocker']}. {d['root_cause']}", f"**Fix:** {d['fix']}"]
    return "\n\n".join(lines) + "\n"


async def main():
    url = sys.argv[1]
    jid = (sys.argv[2:] or ["buy_cheapest"])[0]
    need = float((sys.argv[3:] or ["1.0"])[0])
    t = await run_task(url, jid, os.getenv("CI_QUERY", "bestseller"), quiet)
    diags = await diagnose_all([t], url) if t["progress"] < need else []
    text = report(t, need, diags)
    print(text)
    with open(os.getenv("GITHUB_STEP_SUMMARY", "ci-report.md"), "a") as f:
        f.write(text)
    return 0 if t["progress"] >= need else 1


sys.exit(asyncio.run(main()))
