"""Model router: ai_models jadvali bo'yicha prioritet, circuit breaker (cooldown), rotatsiya.

GEMINI_API_KEY bo'lmasa — demo rejim: rang Pillow bilan aniqlanadi, tur/kategoriya fayl nomi
yoki foydalanuvchi izohidan (hint). Bu faqat dev/demo uchun.
"""
import logging
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.db.base import utcnow
from app.models import AiModel
from app.services.matching.normalizer import extract_attributes
from app.services.vision import gemini_client
from app.services.vision.image_utils import dominant_color
from app.services.vision.schema import VisionResult

log = logging.getLogger("app.vision.router")

COOLDOWN = timedelta(seconds=60)          # 429 / 5xx
COOLDOWN_TIMEOUT = timedelta(seconds=30)
COOLDOWN_GONE = timedelta(hours=24)        # 404: model o'chirilgan yoki nomi o'zgargan
DEMO_MODEL = "demo-local"


def demo_mode() -> bool:
    return not settings.GEMINI_API_KEY


async def ensure_models(db: AsyncSession) -> None:
    """Startup: jadval bo'sh bo'lsa .env dagi GEMINI_MODELS dan to'ldiriladi."""
    existing = (await db.execute(select(AiModel.name))).scalars().all()
    if existing:
        return
    for i, name in enumerate(settings.gemini_models):
        db.add(AiModel(name=name, priority=(i + 1) * 10, enabled=True))
    await db.commit()


def _demo_analyze(jpeg: bytes, hint: str) -> VisionResult:
    color, share = dominant_color(jpeg)
    attrs = extract_attributes(hint)
    category = attrs.get("category") or "boshqa"
    typ = attrs.get("type")
    query = " ".join(x for x in [color, typ or (category if category != "boshqa" else "")] if x)
    return VisionResult(
        category=category, color=attrs.get("color") or color, type=typ, style=None,
        tags=[t for t in [color, typ, category] if t], search_query=query or color,
        confidence=round(min(0.9, 0.4 + share / 2), 2),
    )


async def analyze(db: AsyncSession, jpeg: bytes, hint: str = "") -> tuple[VisionResult, str]:
    if demo_mode():
        return _demo_analyze(jpeg, hint), DEMO_MODEL

    now = utcnow()
    models = (await db.execute(
        select(AiModel).where(AiModel.enabled.is_(True)).order_by(AiModel.priority)
    )).scalars().all()
    candidates = [m for m in models if not m.cooldown_until or m.cooldown_until < now]
    if not candidates:
        raise AppError("AI_UNAVAILABLE", "Hozircha rasm tahlili mavjud emas. Birozdan keyin urinib ko'ring.", 503)

    deadline = time.monotonic() + settings.AI_TIMEOUT_SECONDS * 2   # foydalanuvchi cheksiz kutmasin
    for model in candidates:
        if time.monotonic() > deadline:
            break
        try:
            result = await gemini_client.analyze_with_model(model.name, jpeg)
            model.success_count += 1
            return result, model.name
        except gemini_client.ModelUnavailable as exc:
            msg = str(exc)
            gone = "404" in msg or "NOT_FOUND" in msg or "no longer available" in msg
            model.cooldown_until = now + (COOLDOWN_GONE if gone else COOLDOWN_TIMEOUT if msg == "timeout" else COOLDOWN)
            model.last_error = str(exc)
            model.error_count += 1
            log.warning("Model %s sovutildi: %s", model.name, exc)
        except gemini_client.BadModelOutput as exc:
            model.last_error = f"bad_json: {exc}"
            model.error_count += 1
    raise AppError("AI_UNAVAILABLE", "Hozircha rasm tahlili mavjud emas. Birozdan keyin urinib ko'ring.", 503)
