"""Rasm orqali qidiruv jarayoni (README 9-bo'lim)."""
import logging
import time
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.cache import cache_get, cache_set, hit_rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import Tenant, VisualSearch
from app.services.events.collector import touch_session
from app.services.media import abs_url
from app.services.matching.engine import find_matches
from app.services.matching.normalizer import make_demand_key
from app.services.vision import router as vision_router
from app.services.vision.image_utils import sanitize_image
from app.services.vision.prompts import PROMPT_VERSION
from app.services.vision.schema import VisionResult

log = logging.getLogger("app.search")
VISION_CACHE_TTL = 7 * 24 * 3600


def with_vd(url: str, search_id: str) -> str:
    """Atribusiya uchun product_url?vd=<search_id>."""
    try:
        parts = urlparse(url)
        query = [(k, v) for k, v in parse_qsl(parts.query) if k != "vd"] + [("vd", search_id)]
        return urlunparse(parts._replace(query=urlencode(query)))
    except ValueError:
        return url


async def enforce_limits(tenant: Tenant, ip: str, session_id: str | None) -> None:
    if await hit_rate_limit(f"ip:{ip}", settings.RATE_LIMIT_SEARCH_PER_MIN_IP):
        raise AppError("RATE_LIMITED", "Juda ko'p so'rov. Bir daqiqadan so'ng urinib ko'ring.", 429)
    if session_id and await hit_rate_limit(f"sess:{session_id}", settings.RATE_LIMIT_SEARCH_PER_MIN_IP):
        raise AppError("RATE_LIMITED", "Juda ko'p so'rov. Bir daqiqadan so'ng urinib ko'ring.", 429)
    if await hit_rate_limit(f"tenant:{tenant.id}", settings.RATE_LIMIT_SEARCH_PER_MIN_TENANT):
        raise AppError("RATE_LIMITED", "Do'kon uchun daqiqalik limit tugadi.", 429)
    quota = int(tenant.setting("daily_search_quota") or 0)
    if quota and await hit_rate_limit(f"quota:{tenant.id}", quota, window_s=86400):
        raise AppError("QUOTA_EXCEEDED", "Kunlik qidiruv kvotasi tugadi.", 429)


async def visual_search(tenant: Tenant, raw: bytes, *, session_id: str | None, customer_ref: str | None,
                        consent: bool, hint: str = "", ip: str = "", device: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    await enforce_limits(tenant, ip, session_id)
    jpeg, image_hash = sanitize_image(raw)

    async with SessionLocal() as db:
        cache_key = f"vision:{image_hash}:{PROMPT_VERSION}:{hint[:40] if vision_router.demo_mode() else ''}"
        cached = await cache_get(cache_key)
        from_cache = cached is not None
        if cached:
            ai, model_used = VisionResult.model_validate(cached["ai"]), cached["model"]
        else:
            ai, model_used = await vision_router.analyze(db, jpeg, hint)
            await cache_set(cache_key, {"ai": ai.model_dump(), "model": model_used}, VISION_CACHE_TTL)
            await db.commit()   # model statistikasi / cooldown

        matches = await find_matches(db, tenant.id, ai)

    threshold = float(tenant.setting("unmet_threshold") or settings.DEFAULT_UNMET_THRESHOLD)
    best = matches[0].score if matches else 0.0
    good = [m for m in matches if m.score >= threshold * 0.8]
    is_unmet = best < threshold
    search_id = str(uuid.uuid4())
    latency = int((time.perf_counter() - started) * 1000)

    record = dict(
        id=search_id, tenant_id=tenant.id, session_id=session_id,
        customer_ref=customer_ref if consent else None, image_hash=image_hash,
        prompt_version=PROMPT_VERSION, ai_detected=ai.model_dump(), model_used=model_used,
        best_score=round(best, 4), results_count=len(good), is_unmet_demand=is_unmet,
        demand_key=make_demand_key(ai.category, ai.color, ai.type) if is_unmet else None,
        latency_ms=latency, from_cache=from_cache, created_at=utcnow(),
    )

    response = {
        "search_id": search_id,
        "ai_detected": {k: v for k, v in ai.model_dump().items()},
        "best_match_score": round(best, 4),
        "is_unmet_demand": is_unmet,
        "products": [{
            "id": m.product.external_id, "name": m.product.name, "price_minor": m.product.price_minor,
            "currency": m.product.currency, "image_url": abs_url(m.product.image_url),
            "product_url": with_vd(m.product.product_url, search_id), "in_stock": m.product.in_stock,
            "category": m.product.category, "color": m.product.color, "score": m.score,
        } for m in (good or matches[:4])],
        # model_used mijozga ko'rsatilmaydi
    }
    return {"response": response, "record": record, "session": (session_id, consent, device)}


async def persist_search(tenant_id: str, record: dict[str, Any], session: tuple) -> None:
    """Javobdan keyin saqlash. Xato bo'lsa foydalanuvchiga ta'sir qilmaydi."""
    try:
        async with SessionLocal() as db:
            sid, consent, device = session
            await touch_session(db, tenant_id, sid, consent, device)
            db.add(VisualSearch(**record))
            await db.commit()
    except Exception:
        log.exception("Qidiruvni saqlab bo'lmadi (search_id=%s)", record.get("id"))
