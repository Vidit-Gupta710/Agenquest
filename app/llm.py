"""One way to call the LLM: prompt in, JSON dict out."""

import json
import os

from openai import AsyncOpenAI
from app.cache import cached

client = AsyncOpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY", "x"),
)


@cached
async def ask_json(system, user):
    r = await client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    return json.loads(r.choices[0].message.content)
