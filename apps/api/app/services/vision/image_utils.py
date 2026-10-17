"""Rasm validatsiyasi: magic bytes, hajm, piksel limiti (decompression bomb), EXIF o'chirish, qayta kodlash."""
import hashlib
import io
from collections import Counter

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import AppError

MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
}


def detect_format(data: bytes) -> str | None:
    for magic, fmt in _MAGIC.items():
        if data.startswith(magic):
            return fmt
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def sanitize_image(data: bytes) -> tuple[bytes, str]:
    """Tekshiradi va EXIF'siz, ≤1024px JPEG qaytaradi. Qaytadi: (jpeg_bytes, sha256)."""
    if len(data) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise AppError("IMAGE_TOO_LARGE", f"Rasm hajmi {settings.MAX_IMAGE_MB}MB dan oshmasligi kerak", 413)
    if len(data) < 100 or detect_format(data) is None:
        raise AppError("UNSUPPORTED_IMAGE", "Faqat JPEG, PNG yoki WebP rasm qabul qilinadi", 415)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise AppError("INVALID_IMAGE", "Rasmni o'qib bo'lmadi", 415)
    if img.width * img.height > MAX_PIXELS:
        raise AppError("IMAGE_TOO_LARGE", "Rasm o'lchami juda katta", 413)

    img = img.convert("RGB")      # EXIF va boshqa metama'lumotlar yangi rasmga o'tmaydi
    img.thumbnail((1024, 1024))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    clean = out.getvalue()
    return clean, hashlib.sha256(data).hexdigest()


# ---------- Demo rejim uchun: dominant rangni aniqlash ----------
_PALETTE = {
    "qora": (20, 20, 20), "oq": (240, 240, 240), "kulrang": (128, 128, 128),
    "qizil": (200, 30, 40), "pushti": (235, 130, 170), "to'q sariq": (240, 130, 30),
    "sariq": (240, 210, 40), "yashil": (40, 150, 60), "ko'k": (40, 90, 200),
    "havorang": (120, 190, 235), "binafsha": (130, 60, 170), "jigarrang": (120, 75, 40),
    "bej": (215, 195, 160), "to'q ko'k": (25, 35, 90),
}


def dominant_color(jpeg: bytes) -> tuple[str, float]:
    """Markaziy hududdagi eng ko'p uchraydigan palitra rangi va uning ulushi."""
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    w, h = img.size
    img = img.crop((w * 0.2, h * 0.2, w * 0.8, h * 0.8)).resize((48, 48))
    counts: Counter[str] = Counter()
    for r, g, b in img.getdata():
        name = min(_PALETTE, key=lambda n: (r - _PALETTE[n][0]) ** 2 + (g - _PALETTE[n][1]) ** 2
                   + (b - _PALETTE[n][2]) ** 2)
        counts[name] += 1
    # fon odatda oq/kulrang — boshqa rang yetarlicha bo'lsa uni tanlaymiz
    total = sum(counts.values())
    for name, n in counts.most_common():
        if name in ("oq", "kulrang") and n / total < 0.7:
            continue
        return name, n / total
    name, n = counts.most_common(1)[0]
    return name, n / total
