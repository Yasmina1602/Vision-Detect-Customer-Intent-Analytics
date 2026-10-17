import io
import time

import pytest
from PIL import Image

from app.core.errors import AppError
from app.core.security import hash_password, sign_payload, verify_password, verify_signature
from app.services.catalog.normalizer import enrich, from_raw, price_to_minor
from app.services.catalog.providers import parse_csv
from app.services.events.identity import validate_customer_ref
from app.services.matching.embeddings import cosine, embed
from app.services.matching.normalizer import extract_attributes, make_demand_key
from app.services.matching.scoring import ScoreParts, attribute_match
from app.services.search import with_vd
from app.services.vision.image_utils import dominant_color, sanitize_image
from app.services.vision.schema import VisionResult


# ---------- demand_key normalizatsiya ----------
@pytest.mark.parametrize("text", ["sariq xudi", "sariq kapyushonli kofta", "yellow hoodie", "Жёлтый худи"])
def test_same_demand_for_synonyms(text):
    a = extract_attributes(text)
    assert make_demand_key(a.get("category"), a.get("color"), a.get("type")) == "kiyim|sariq|xudi"


def test_longer_phrase_wins():
    assert extract_attributes("to'q ko'k ko'ylak")["color"] == "to'q ko'k"
    assert extract_attributes("to‘q ko‘k ko‘ylak")["color"] == "to'q ko'k"   # turli apostroflar


def test_suffixes():
    assert extract_attributes("qizil krossovkalar")["type"] == "krossovka"


def test_vision_result_whitelist():
    r = VisionResult.model_validate({"category": "Shoes", "color": "RED", "type": "sneakers",
                                     "tags": ["a"] * 20, "confidence": 0.9})
    assert (r.category, r.color, r.type) == ("poyabzal", "qizil", "krossovka")
    assert len(r.tags) == 10


# ---------- matching ----------
def test_embedding_similarity_prefers_same_item():
    q = embed("qizil sport krossovka")
    same = embed("Nike qizil krossovka sport poyabzal")
    other = embed("Qora charm sumka")
    assert cosine(q, same) > cosine(q, other)


def test_score_weights():
    parts = ScoreParts(vector=1, attr=1, stock=1, popularity=1)
    assert parts.total == 1.0
    assert attribute_match("qizil", "krossovka", "poyabzal", "qizil", "krossovka", "poyabzal") == pytest.approx(1.0)
    assert attribute_match("qizil", "krossovka", None, "qora", "krossovka", None) == pytest.approx(0.55)


# ---------- pul (hech qachon float) ----------
@pytest.mark.parametrize("raw,expected", [("129000", 12900000), ("129 000.50 UZS", 12900050), ("1,5", 150),
                                          (None, None), ("", None), ("1.234.567", 123456700)])
def test_price_to_minor(raw, expected):
    assert price_to_minor(raw) == expected


def test_feed_normalization_google_fields():
    p = from_raw({"g:id": "7", "g:title": "Qizil krossovka Nike", "g:price": "129000 UZS", "g:link": "https://s.uz/p/7",
                  "g:availability": "in stock"})
    d = enrich(p)
    assert d["external_id"] == "7" and d["price_minor"] == 12900000 and d["in_stock"]
    assert d["category"] == "poyabzal" and d["color"] == "qizil" and d["attributes"]["type"] == "krossovka"


def test_csv_semicolon():
    rows = parse_csv("id;name;price;url\n1;Oq futbolka;50000;https://s.uz/1\n")
    assert rows[0]["name"] == "Oq futbolka"


# ---------- xavfsizlik ----------
def test_password_hash():
    h = hash_password("Secret123")
    assert verify_password("Secret123", h) and not verify_password("x", h)


def test_hmac_and_replay():
    body = b'{"a":1}'
    ts = str(int(time.time()))
    sig = sign_payload("whsec_x", ts, body)
    assert verify_signature("whsec_x", ts, body, sig)
    assert not verify_signature("whsec_x", ts, body + b" ", sig)
    old = str(int(time.time()) - 600)
    assert not verify_signature("whsec_x", old, body, sign_payload("whsec_x", old, body))


@pytest.mark.parametrize("ref", ["ali@mail.uz", "+998901234567", "998901234567"])
def test_pii_rejected(ref):
    with pytest.raises(AppError) as e:
        validate_customer_ref(ref)
    assert e.value.status == 422


def test_customer_ref_ok():
    assert validate_customer_ref("u_1842") == "u_1842"


def test_with_vd():
    assert with_vd("https://s.uz/p/7?color=red&vd=old", "abc") == "https://s.uz/p/7?color=red&vd=abc"


# ---------- rasm ----------
def _img(color=(220, 30, 40), fmt="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), color).save(buf, format=fmt)
    return buf.getvalue()


def test_sanitize_and_color():
    jpeg, sha = sanitize_image(_img())
    assert jpeg[:3] == b"\xff\xd8\xff" and len(sha) == 64
    assert dominant_color(jpeg)[0] == "qizil"


def test_reject_non_image():
    with pytest.raises(AppError):
        sanitize_image(b"GIF89a" + b"0" * 200)
