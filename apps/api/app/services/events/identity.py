"""Identifikatsiya: faqat neytral customer_ref. Username/email/telefon QABUL QILINMAYDI."""
import re
from datetime import timedelta

from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.repositories import tupdate
from app.models import Event, IdentityLink, VisualSearch, CartSession

_EMAIL = re.compile(r"@")
_PHONE = re.compile(r"^\+?\d[\d\s\-()]{8,}$")
_ALLOWED = re.compile(r"^[A-Za-z0-9_\-:.]{1,128}$")
STITCH_DAYS = 30


def validate_customer_ref(ref: str) -> str:
    ref = (ref or "").strip()
    if _EMAIL.search(ref) or _PHONE.match(ref) or ref.startswith("+998"):
        raise AppError("PII_NOT_ALLOWED",
                       "customer_ref e-mail yoki telefon bo'lishi mumkin emas. Ichki ID yuboring (masalan 'u_1842').", 422)
    if not _ALLOWED.match(ref):
        raise AppError("INVALID_CUSTOMER_REF", "customer_ref faqat harf, raqam va _-:. belgilaridan iborat bo'lsin", 422)
    return ref


async def link_identity(db: AsyncSession, tenant_id: str, session_id: str, customer_ref: str) -> None:
    customer_ref = validate_customer_ref(customer_ref)
    await db.execute(
        insert(IdentityLink).values(tenant_id=tenant_id, session_id=session_id, customer_ref=customer_ref,
                                    linked_at=utcnow()).prefix_with("IGNORE")
    )
    # Stitching: identify'dan oldingi anonim hodisalar (30 kun) shu xaridorga bog'lanadi
    since = utcnow() - timedelta(days=STITCH_DAYS)
    for model, ts_col in ((Event, Event.ts), (VisualSearch, VisualSearch.created_at),
                          (CartSession, CartSession.last_activity_at)):
        await db.execute(
            tupdate(model, tenant_id)
            .where(model.session_id == session_id, model.customer_ref.is_(None), ts_col >= since)
            .values(customer_ref=customer_ref)
        )


async def delete_customer(db: AsyncSession, tenant_id: str, customer_ref: str) -> dict[str, int]:
    """O'chirish huquqi: customer_ref bilan bog'liq yozuvlar anonimlashtiriladi."""
    counts = {}
    for model in (Event, VisualSearch, CartSession):
        res = await db.execute(tupdate(model, tenant_id).where(model.customer_ref == customer_ref)
                               .values(customer_ref=None))
        counts[model.__tablename__] = res.rowcount
    res = await db.execute(
        IdentityLink.__table__.delete().where(IdentityLink.tenant_id == tenant_id,
                                              IdentityLink.customer_ref == customer_ref))
    counts["identity_links"] = res.rowcount
    return counts
