"""Gemini mijozi: timeout, strukturali JSON, 1 marta qayta so'rash."""
import asyncio
import json
import logging

from pydantic import ValidationError

from app.core.config import settings
from app.services.vision.prompts import VISION_PROMPT
from app.services.vision.schema import VisionResult

log = logging.getLogger("app.vision.gemini")


class ModelUnavailable(Exception):
    """429 / 5xx / timeout — model vaqtincha sovutiladi."""


class BadModelOutput(Exception):
    """JSON validatsiyadan o'tmadi."""


_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai  # lazy import — kalit bo'lmasa kerak emas

        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _parse(text: str) -> VisionResult:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        return VisionResult.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise BadModelOutput(str(exc)[:300])


async def analyze_with_model(model: str, jpeg: bytes) -> VisionResult:
    from google.genai import types

    client = _get_client()
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
    contents = [types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"), VISION_PROMPT]

    last_error: Exception | None = None
    for attempt in range(2):  # JSON buzilgan bo'lsa 1 marta qayta
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=contents, config=config),
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise ModelUnavailable("timeout")
        except Exception as exc:  # SDK xatolari: 429, 5xx, model topilmadi
            msg = str(exc)
            raise ModelUnavailable(msg[:300])
        try:
            return _parse(resp.text)
        except BadModelOutput as exc:
            last_error = exc
            log.warning("Gemini JSON noto'g'ri (urinish %s): %s", attempt + 1, exc)
    raise last_error or BadModelOutput("unknown")
