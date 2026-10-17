"""Mahsulot rasmlari: yuklash (EXIF'siz, ≤1600px JPEG), nisbiy saqlash, absolyut URL qaytarish.

DB'da o'zimizdagi fayllar "/media/<tenant>/<fayl>" ko'rinishida saqlanadi — PUBLIC_API_URL o'zgarsa (boshqa host,
tunnel, production domen) rasmlar buzilmaydi. Tashqi (feed'dan kelgan) URL'lar o'zgarishsiz qoladi.
"""
import io
import uuid

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import AppError
from app.services.vision.image_utils import MAX_PIXELS, detect_format

MAX_UPLOAD_MB = 8


def abs_url(url: str | None) -> str | None:
    if not url:
        return url
    if url.startswith("/media/") or url.startswith("/demo/"):
        return settings.PUBLIC_API_URL.rstrip("/") + url
    return url


def save_product_image(tenant_id: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise AppError("IMAGE_TOO_LARGE", f"Rasm {MAX_UPLOAD_MB}MB dan oshmasligi kerak", 413)
    if detect_format(data) is None:
        raise AppError("UNSUPPORTED_IMAGE", "Faqat JPEG, PNG yoki WebP", 415)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise AppError("INVALID_IMAGE", "Rasmni o'qib bo'lmadi", 415)
    if img.width * img.height > MAX_PIXELS:
        raise AppError("IMAGE_TOO_LARGE", "Rasm o'lchami juda katta", 413)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    folder = settings.media_path / tenant_id
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(folder / name, format="JPEG", quality=86, optimize=True, progressive=True)
    return f"/media/{tenant_id}/{name}"
