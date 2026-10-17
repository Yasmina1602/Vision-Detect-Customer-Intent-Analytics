# Vision Detect — Core API (FastAPI)

Loyihaning to'liq spetsifikatsiyasi: [../../README.md](../../README.md). Bu fayl — lokal ishga tushirish va MySQL bo'yicha eslatmalar.

## Tez boshlash (Windows, PowerShell yoki Git Bash)

```bash
# 1) Muhit
cd apps/api
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp ../../.env.example ../../.env        # DATABASE_URL va APP_SECRET_KEY ni to'ldiring

# 2) Baza (MySQL 8)
.venv/Scripts/python -m alembic upgrade head

# 3) Demo ma'lumot + super admin
.venv/Scripts/python scripts/seed_demo.py
.venv/Scripts/python scripts/create_superadmin.py --email admin@vision.uz --password Admin12345

# 4) API
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

| Manzil | Tavsif |
|---|---|
| http://127.0.0.1:8000/docs | Swagger (faqat development) |
| http://127.0.0.1:8000/demo/vanilla | Oddiy HTML sayt + vidjet namunasi |
| http://127.0.0.1:8000/readyz | DB tekshiruvi |
| http://localhost:3000 | Dashboard (`apps/dashboard`, `npm run dev`) |

## README'dan farqlar (MySQL bosqichi)

| README (PostgreSQL) | Hozirgi holat (MySQL 8) |
|---|---|
| `UUID`, `JSONB`, `TEXT[]`, `timestamptz` | `CHAR(36)`, `JSON`, `DATETIME` (har doim UTC) |
| Row Level Security | `app/db/repositories.py` — `tenant_id` filtrisiz so'rov qurib bo'lmaydi |
| pgvector + Gemini embedding | lokal hashing-embedding (`services/matching/embeddings.py`), JSON ustunda |
| `events` oylik partitsiya | `(tenant_id, ts)` indeksi + `retention` job |
| Redis + ARQ worker | Redis ixtiyoriy (bo'lmasa xotira); worker — `app/workers/scheduler.py` (API ichida yoki `python -m app.workers.run`) |

`GEMINI_API_KEY` bo'sh bo'lsa **demo vision** rejimi ishlaydi: rang rasmdan (Pillow) aniqlanadi, tur/kategoriya fayl nomidan
(`qizil-krossovka.jpg`). Production uchun pullik Gemini kalitini qo'shing — modellar `ai_models` jadvalidan boshqariladi.

## Eski jadvallar

Agar bazada boshqa loyihaning shu nomdagi jadvallari (`users`, `visual_searches`, `orders` …) bo'lsa, `alembic upgrade head`
hech narsani o'zgartirmasdan to'xtaydi. Ikki yo'l bor:

```sql
-- A) eski jadvallarni saqlab, nomini o'zgartirish (ma'lumot yo'qolmaydi)
RENAME TABLE users TO legacy_v1_users, visual_searches TO legacy_v1_visual_searches,
             orders TO legacy_v1_orders, order_items TO legacy_v1_order_items,
             cart_items TO legacy_v1_cart_items, products TO legacy_v1_products,
             roles TO legacy_v1_roles, user_events TO legacy_v1_user_events;

-- B) yoki yangi baza: .env da DATABASE_URL=mysql://root:1234@127.0.0.1:3306/vision_detect_v2
CREATE DATABASE vision_detect_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Testlar

```bash
.venv/Scripts/python -m pytest -q
```
