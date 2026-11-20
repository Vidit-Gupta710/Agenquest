"""Audit every URL in data/sites.txt, one at a time, and write data/leaderboard.json."""
import asyncio
import json
import pathlib

from dotenv import load_dotenv

load_dotenv()

from app.audit import audit  # noqa: E402


async def quiet(event, **d):
    if event in ("stage", "task_done"):
        print(event, d.get("stage") or d["task"]["id"], d.get("task", {}).get("outcome", ""))


async def main():
    rows = []
    for url in pathlib.Path("data/sites.txt").read_text().split():
        try:
            r = await audit(url, quiet)
            rows.append({"domain": r["domain"], "site_type": r["site_type"], **r["score"], **r["agent_tax"]})
        except Exception as e:
            print("SKIPPED", url, e)
    rows.sort(key=lambda r: -r["total"])
    pathlib.Path("data/leaderboard.json").write_text(json.dumps(rows, indent=2))


asyncio.run(main())