"""Matching Engine: tenant katalogi bo'yicha atribut filtri → vektor o'xshashlik → ball."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import tq
from app.models import CatalogProduct
from app.services.matching.embeddings import cosine, embed
from app.services.matching.scoring import ScoreParts, attribute_match
from app.services.vision.schema import VisionResult

MAX_CANDIDATES = 3000


@dataclass
class Match:
    product: CatalogProduct
    score: float


def query_text(ai: VisionResult) -> str:
    return " ".join(x for x in [ai.search_query, ai.type or "", ai.color or "", ai.category, *ai.tags] if x)


async def find_matches(db: AsyncSession, tenant_id: str, ai: VisionResult, limit: int = 8) -> list[Match]:
    stmt = (tq(CatalogProduct, tenant_id)
            .where(CatalogProduct.is_deleted.is_(False))
            .order_by(CatalogProduct.in_stock.desc(), CatalogProduct.popularity.desc())
            .limit(MAX_CANDIDATES))
    products = (await db.execute(stmt)).scalars().all()
    if not products:
        return []

    q_vec = embed(query_text(ai))
    scored: list[Match] = []
    for p in products:
        attrs = p.attributes or {}
        p_type = attrs.get("type")
        parts = ScoreParts(
            vector=cosine(q_vec, p.embedding),
            attr=attribute_match(ai.color, ai.type, ai.category, p.color, p_type, p.category),
            stock=1.0 if p.in_stock else 0.0,
            popularity=min(1.0, p.popularity or 0.0),
        )
        # boshqa kategoriya — kuchli jarima (krossovka so'ralganda sumka chiqmasin)
        total = parts.total
        if ai.category != "boshqa" and p.category and p.category != ai.category:
            total *= 0.5
        scored.append(Match(p, round(total, 4)))

    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:limit]
