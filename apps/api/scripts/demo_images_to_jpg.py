"""Demo mahsulotlarning .svg rasmlarini .jpg ga almashtirish (bir martalik).

python scripts/demo_images_to_jpg.py

Faqat /media/<tenant>/demo-<id>.svg ko'rinishidagi (seed yaratgan) rasmlarga tegadi: JPG nusxasini qo'yadi,
bazadagi image_url va galereyani yangilaydi, eski .svg faylni o'chiradi. Siz yuklagan rasmlar o'zgarmaydi.
"""
import asyncio
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import CatalogProduct  # noqa: E402

DEMO_IMAGES = Path(__file__).resolve().parents[1] / "app" / "demo" / "products"
PATTERN = re.compile(r"^/media/([0-9a-f-]{36})/demo-([\w-]+)\.svg$")


def to_jpg(path: str | None, stale: set[Path]) -> str | None:
    m = PATTERN.match(path or "")
    if not m:
        return path
    tenant_id, pid = m.groups()
    src = DEMO_IMAGES / f"{pid}.jpg"
    if not src.exists():
        return path
    folder = settings.media_path / tenant_id
    shutil.copyfile(src, folder / f"demo-{pid}.jpg")
    stale.add(folder / f"demo-{pid}.svg")
    return f"/media/{tenant_id}/demo-{pid}.jpg"


async def main() -> None:
    stale: set[Path] = set()
    changed = 0
    async with SessionLocal() as db:
        for p in (await db.execute(select(CatalogProduct).where(CatalogProduct.image_url.like("%/demo-%.svg")))).scalars().all():
            p.image_url = to_jpg(p.image_url, stale)
            if p.images:
                p.images = [to_jpg(i, stale) for i in p.images]
            changed += 1
        await db.commit()
    for f in stale:
        f.unlink(missing_ok=True)
    print(f"{changed} ta mahsulot rasmi .jpg ga almashtirildi, {len(stale)} ta eski .svg o'chirildi")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
