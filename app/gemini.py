"""Thin wrappers around the Gemini Interactions API."""
import asyncio
import json
import os
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

ARGON = "gemini-4-argon"
FLASH = "gemini-3.8-flash"
FLASH_LITE = "gemini-3.5-flash-lite"
DEEP_RESEARCH = "deep-research-preview-04-2026"

T = TypeVar("T", bound=BaseModel)
_client: genai.Client | None = None
_sem = asyncio.Semaphore(int(os.getenv("MAX_PARALLEL", "16")))


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(http_options=types.HttpOptions(timeout=20 * 60 * 1000))
    return _client


def aclient():
    return client().aio


async def structured(model: str, prompt: str | list, schema: type[T], thinking: str = "low",
                     previous_interaction_id: str | None = None, retries: int = 2) -> T:
    out, _ = await structured_with_id(model, prompt, schema, thinking, previous_interaction_id, retries)
    return out


async def structured_with_id(model: str, prompt: str | list, schema: type[T], thinking: str = "low",
                             previous_interaction_id: str | None = None, retries: int = 2) -> tuple[T, str]:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            kw = {"previous_interaction_id": previous_interaction_id} if previous_interaction_id else {}
            async with _sem:
                r = await aclient().interactions.create(
                    model=model,
                    input=prompt,
                    generation_config={"thinking_level": thinking},
                    response_format={"type": "text", "mime_type": "application/json",
                                     "schema": schema.model_json_schema()},
                    **kw,
                )
            return schema.model_validate_json(_strip(r.output_text or "")), r.id
        except Exception as e:  # network blips, schema violations
            last = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{model} structured call failed: {last}")


def _strip(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    json.loads(text)
    return text
