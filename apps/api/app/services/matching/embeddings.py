"""Yengil lokal embedding (hashing trick) — tashqi API talab qilmaydi.

pgvector + Gemini embedding'ga o'tilganda shu modul almashtiriladi; interfeys: embed(text) -> list[float].
"""
import hashlib
import math

from app.services.matching.normalizer import canonical_tokens

DIM = 256


def _bucket(token: str) -> tuple[int, float]:
    h = hashlib.md5(token.encode()).digest()
    idx = int.from_bytes(h[:4], "little") % DIM
    sign = 1.0 if h[4] & 1 else -1.0
    return idx, sign


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in canonical_tokens(text):
        weight = 2.0 if tok[:2] in ("c:", "t:", "k:") else 1.0
        idx, sign = _bucket(tok)
        vec[idx] += sign * weight
        if tok[:2] not in ("c:", "t:", "k:") and len(tok) > 4:   # imlo xatolariga chidamlilik
            for i in range(len(tok) - 2):
                j, s = _bucket("#" + tok[i:i + 3])
                vec[j] += s * 0.25
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 5) for v in vec]


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return max(0.0, sum(x * y for x, y in zip(a, b)))
