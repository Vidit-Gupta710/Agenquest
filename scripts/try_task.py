"""Usage: python -m scripts.try_task <url> <task_id> [query]"""

import asyncio
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from app.runner import run_task  # noqa: E402


async def show(event, **data):
    print(event, data.get("status"), data.get("steps"))


if __name__ == "__main__":
    url = sys.argv[1]
    task_id = sys.argv[2]
    query = (sys.argv[3:] or ["bestseller"])[0]
    result = asyncio.run(run_task(url, task_id, query, show))
    print(json.dumps(result, indent=2))
