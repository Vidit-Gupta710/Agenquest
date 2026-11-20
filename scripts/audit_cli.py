"""Usage: python -m scripts.audit_cli <url>"""
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from app.audit import audit  # noqa: E402


async def show(event, **d):
    print(f"{event:12}", d.get("stage") or d.get("task_id") or d.get("score") or "")


if __name__ == "__main__":
    r = asyncio.run(audit(sys.argv[1], show))
    print("\nSCORE", r["score"]["total"], r["score"]["grade"], "| Agent Tax", r["agent_tax"])