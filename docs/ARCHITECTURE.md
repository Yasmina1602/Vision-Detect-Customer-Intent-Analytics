# 🛍️ Vision Detect — Rasm orqali qidiruv va Xaridor talablari analitikasi (SaaS)

> Istalgan e-commerce saytga **bitta `<script>` tegi** bilan ulanadigan, multi-tenant, production darajasidagi AI vizual qidiruv va marketing analitika platformasi.

**Versiya:** 2.1 (Storefront, target marketing, Excel eksport — [26-bo'lim](#26-v21-yangilanishlar-ozgarishlar-jurnali)) · **Til:** O'zbekcha · **Litsenziya:** MIT

---

## Mundarija

1. [Qisqacha mazmun](#1-qisqacha-mazmun)
2. [Tariflar](#2-tariflar)
3. [Umumiy arxitektura](#3-umumiy-arxitektura)
4. [Texnologiyalar steki](#4-texnologiyalar-steki)
5. [Loyiha papkalar ierarxiyasi](#5-loyiha-papkalar-ierarxiyasi)
6. [Rollar va ruxsatlar](#6-rollar-va-ruxsatlar)
7. [Ma'lumotlar bazasi sxemasi](#7-malumotlar-bazasi-sxemasi)
8. [Sotuvchi katalogi bilan ulanish](#8-sotuvchi-katalogi-bilan-ulanish)
9. [Rasm orqali qidiruv jarayoni](#9-rasm-orqali-qidiruv-jarayoni)
10. [Vidjet: 1 teg bilan integratsiya](#10-vidjet-1-teg-bilan-integratsiya)
11. [Savat va xaridni kuzatish](#11-savat-va-xaridni-kuzatish)
12. [Ro'yxatdan o'tgan foydalanuvchi (identifikatsiya) va sotuvchi bazasiga ta'sir](#12-royxatdan-otgan-foydalanuvchi-identifikatsiya-va-sotuvchi-bazasiga-tasir)
13. [Analitika: metrikalar va formulalar](#13-analitika-metrikalar-va-formulalar)
14. [Admin va Dashboard sahifalari](#14-admin-va-dashboard-sahifalari)
15. [Premium Storefront](#15-premium-storefront)
16. [API ro'yxati](#16-api-royxati)
17. [Xatoliklarning oldini olish (risk jadvali)](#17-xatoliklarning-oldini-olish-risk-jadvali)
18. [Xavfsizlik va maxfiylik](#18-xavfsizlik-va-maxfiylik)
19. [Sozlamalar (.env)](#19-sozlamalar-env)
20. [Lokal ishga tushirish](#20-lokal-ishga-tushirish)
21. [Production deploy](#21-production-deploy)
22. [Test va CI/CD](#22-test-va-cicd)
23. [Monitoring, zaxira nusxa, masshtablash](#23-monitoring-zaxira-nusxa-masshtablash)
24. [0 dan production gacha yo'l xaritasi](#24-0-dan-production-gacha-yol-xaritasi)
25. [Ishga tushirishdan oldingi checklist](#25-ishga-tushirishdan-oldingi-checklist)
26. [v2.1 yangilanishlar](#26-v21-yangilanishlar-ozgarishlar-jurnali)
27. [Savdo do'koni va rasm qidiruvi: nima qayerda](#27-savdo-dokoni-va-rasm-qidiruvi-nima-qayerda-ajratilish)
28. [Auditoriya va target reklama](#28-auditoriya-va-target-reklama-neytral-customer_ref-bilan)
29. [Boshqa platformaga ulash (test)](#29-boshqa-platformaga-ulash-test-qollanmasi)
30. [Excel eksport](#30-excel-eksport)
31. [API qo'shimchalari (v2.1)](#31-api-qoshimchalari-v21)
32. [Tariflar amalda: Oddiy va Premium](#32-tariflar-amalda-oddiy-va-premium)
33. [v2.2 yangilanishlar](#33-v22-yangilanishlar-2026-10-17)
34. [Basic edition — alohida loyiha](#34-basic-edition--faqat-oddiy-tarif-alohida-loyiha-2026-10-17)

---

## 1. Qisqacha mazmun

Mijoz (xaridor) qidiruv paneliga rasm yuklaydi → **Gemini Multimodal AI** rasmni tahlil qiladi (kategoriya, rang, tur, teglar) → tizim do'kon katalogidan eng mos tovarlarni topadi. Barcha xatti-harakatlar (ko'rdi, savatga soldi, tashlab ketdi, sotib oldi) yig'ilib, do'kon egasiga **konversiya voronkasi**, **qondirilmagan talab** va **yo'qotilgan daromad** hisoboti ko'rsatiladi.

**Asosiy qarorlar:**

| Qaror | Sabab |
|---|---|
| Bitta yadro (**Vision Core**), multi-tenant | Ikkala tarif bitta kod bazasida ishlaydi |
| Sotuvchi bazasiga **hech qachon to'g'ridan-to'g'ri ulanmaymiz** | Xavfsizlik, ruxsat, turli DB turlari. Faqat feed / API / webhook |
| Vidjet **fail-open** va **Shadow DOM**da | Mijoz saytini hech qachon buzmaydi |
| Foydalanuvchi **username/email/telefon** analitikaga **uzatilmaydi** | Maxfiylik. Faqat neytral `customer_ref` (ichki ID) |
| Hodisalar **idempotent** (`event_id`) | Takror yuborilsa ikki marta sanalmaydi |
| Xarid asosan **server-to-server webhook** orqali | Brauzerga ishonib bo'lmaydi (yopilishi, adblock) |
| Hamma narsa `tenant_id` + PostgreSQL **RLS** bilan izolyatsiya | Bir do'kon boshqasining ma'lumotini ko'ra olmaydi |

---

## 2. Tariflar

| Imkoniyat | 🟢 Oddiy (Analytics) | 🟣 Premium (Store + Analytics) |
|---|:---:|:---:|
| Rasm orqali qidiruv vidjeti (1 teg) | ✅ | ✅ |
| Katalog manbasi | Mijozning feed/API/proxy | Bizning bazamiz |
| Hodisa kuzatuvi va atribusiya | ✅ | ✅ |
| Marketing dashboard (voronka, qondirilmagan talab, tashlab ketilgan savat) | ✅ | ✅ |
| Bizning sotuv veb-ilovamiz (Storefront) | ❌ | ✅ |
| Mahsulot / buyurtma / mijozlarni boshqarish (Admin) | ❌ | ✅ |
| To'lov (Payme / Click) | ❌ | ✅ (2-bosqich) |

Tarif `tenants.plan` va **feature flag**lar orqali boshqariladi. Kod ikkiga bo'linmaydi: Premium'dagi do'kon Core'ning oddiy klienti.

---

## 3. Umumiy arxitektura

```
┌───────────────────── MIJOZ SAYTI (WordPress/Shopify/OpenCart/Laravel/Next.js/HTML) ─────────────────────┐
│  <script src="https://cdn.vision.uz/v1/loader.js" data-key="pk_live_xxx" async></script>                 │
│   Loader(~5KB) → config → [Shadow DOM Vidjet] [Cart Adapter] [Event Collector]                           │
│   (ixtiyoriy) Platforma plagini: feed endpoint, order webhook, vd_sid → buyurtma meta                    │
└───────────────┬──────────────────────────────────────────────┬───────────────────────────────────────────┘
                │ HTTPS · public key + Origin                  │ server→server · secret key · HMAC webhook
                ▼                                              ▼
┌──────────────────────────────────── EDGE: Nginx / Cloudflare ──────────────────────────────────────────┐
│  TLS · WAF · rate limit (qo'pol) · gzip · CDN (loader.js, widget.js)                                    │
└───────────────────────────────────────────┬─────────────────────────────────────────────────────────────┘
                                            ▼
┌──────────────────────────────── API (FastAPI, async, stateless) ────────────────────────────────────────┐
│ Middleware: request-id · auth(key/JWT) · tenant context · rate limit · validatsiya · xato formati       │
│ ┌────────────┐ ┌──────────────┐ ┌─────────────┐ ┌───────────────┐ ┌───────────┐ ┌──────────────────┐   │
│ │ Vision     │ │ Matching     │ │ Event       │ │ Catalog       │ │ Analytics │ │ Admin/Auth/      │   │
│ │ Service    │ │ Engine       │ │ Collector   │ │ Service       │ │ Service   │ │ Tenants (RBAC)   │   │
│ └─────┬──────┘ └──────┬───────┘ └──────┬──────┘ └───────┬───────┘ └─────┬─────┘ └────────┬─────────┘   │
└───────┼───────────────┼────────────────┼────────────────┼───────────────┼────────────────┼─────────────┘
        ▼               ▼                ▼                ▼               ▼                ▼
     Gemini API    PostgreSQL 16 + pgvector (RLS, partitsiya)         Redis (kesh, limit, navbat)
     (router +            ▲                                                   ▲
      breaker)            │                                                   │
                   ┌──────┴──────────────────────────────────────────────────┴──────┐
                   │ WORKER (ARQ): katalog sinxron · embedding · abandoned cart ·    │
                   │ kunlik agregat · retention (eski ma'lumot o'chirish) · webhook  │
                   │ retry · demand clustering                                       │
                   └─────────────────────────────────────────────────────────────────┘

   Dashboard (Next.js)  ← JWT, rollar          Storefront (Next.js, faqat Premium) ← Core ochiq API
```

**Uchta oqim:**

1. **Sinxron (foydalanuvchi kutadi):** rasm → Gemini → moslashtirish → javob. Maqsad: p95 < 4 s.
2. **Asinxron (kutmaydi):** qidiruvni saqlash, hodisalar, agregatlar, klasterlash.
3. **Fon (rejalashtirilgan):** katalog sinxroni, abandoned cart, retention.

---

## 4. Texnologiyalar steki

| Qatlam | Tanlov |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| DB | PostgreSQL 16 + **pgvector**, `pg_partman` (events partitsiya) |
| Kesh/Navbat | Redis 7 |
| Worker | ARQ (yengil) yoki Celery |
| AI | Google Gemini (**pullik** kalit production uchun), `google-genai` SDK |
| Vidjet/SDK | TypeScript → esbuild → `loader.js` + `widget.js` (CDN) |
| Dashboard / Storefront | Next.js (App Router), Tailwind, Recharts |
| Auth | JWT (access 15 daq) + refresh (httpOnly cookie), **argon2id** |
| Infra | Docker, Docker Compose → (keyin) Kubernetes/Nomad; Nginx, Cloudflare |
| Kuzatuv | Sentry, Prometheus + Grafana, Loki (loglar), Uptime monitoring |
| CI/CD | GitHub Actions |

> **Joriy amalga oshirish (v2.1):** DB hozircha **MySQL 8** (PostgreSQL + pgvector'ga o'tish rejada). RLS o'rniga majburiy tenant filtri (`app/db/repositories.py`), pgvector o'rniga lokal embedding, Redis/ARQ ixtiyoriy (yo'q bo'lsa xotira va API ichidagi rejalashtiruvchi). Batafsil: [apps/api/README.md](apps/api/README.md).

> **Eslatma:** Gemini model nomlari kodga yozilmaydi. Ular `ai_models` jadvali/konfiguratsiyada saqlanadi va ishga tushganda tekshiriladi (17-bo'lim).

---

## 5. Loyiha papkalar ierarxiyasi

Monorepo (bitta repozitoriy, alohida deploy qilinadigan ilovalar):

```text
vision-platform/
├── apps/
│   ├── api/                          # FastAPI (Core)
│   │   ├── app/
│   │   │   ├── main.py               # create_app(), middleware, routerlar
│   │   │   ├── core/
│   │   │   │   ├── config.py         # pydantic-settings, .env validatsiyasi
│   │   │   │   ├── security.py       # argon2, JWT, HMAC, key hashing
│   │   │   │   ├── logging.py        # JSON loglar, request_id
│   │   │   │   ├── errors.py         # yagona xato formati, exception handlerlar
│   │   │   │   └── rate_limit.py     # Redis token bucket
│   │   │   ├── db/
│   │   │   │   ├── session.py        # async engine, SET LOCAL app.tenant_id (RLS)
│   │   │   │   ├── base.py
│   │   │   │   └── repositories/     # tenant_id'siz so'rov yozish mumkin emas
│   │   │   ├── models/               # SQLAlchemy modellari
│   │   │   │   ├── tenant.py  user.py  api_key.py  catalog.py
│   │   │   │   ├── search.py  event.py  cart.py  order.py  analytics.py
│   │   │   ├── schemas/              # Pydantic (request/response), versiyalangan
│   │   │   ├── api/
│   │   │   │   ├── deps.py           # get_tenant, require_role(), get_db
│   │   │   │   └── v1/
│   │   │   │       ├── public/       # vidjet uchun (public key)
│   │   │   │       │   ├── config.py  visual_search.py  events.py  products.py
│   │   │   │       ├── server/       # sotuvchi serveri uchun (secret key)
│   │   │   │       │   ├── events.py  webhooks.py  catalog_push.py
│   │   │   │       ├── dashboard/    # JWT + rollar
│   │   │   │       │   ├── auth.py  analytics.py  catalog.py  settings.py  keys.py
│   │   │   │       ├── admin/        # platforma super_admin
│   │   │   │       │   ├── tenants.py  users.py  ai_models.py
│   │   │   │       └── storefront/   # faqat Premium (feature flag)
│   │   │   │           ├── catalog.py  cart.py  checkout.py  customers.py  orders.py
│   │   │   ├── services/
│   │   │   │   ├── vision/
│   │   │   │   │   ├── gemini_client.py   # timeout, retry, structured JSON
│   │   │   │   │   ├── router.py          # model rotatsiyasi + circuit breaker
│   │   │   │   │   ├── prompts.py         # PROMPT_VERSION
│   │   │   │   │   └── image_utils.py     # magic bytes, EXIF strip, resize
│   │   │   │   ├── matching/
│   │   │   │   │   ├── engine.py  scoring.py  embeddings.py
│   │   │   │   ├── catalog/
│   │   │   │   │   ├── providers/         # base.py, feed.py, rest_proxy.py, hosted.py
│   │   │   │   │   ├── normalizer.py      # → yagona Product formati
│   │   │   │   │   └── sync.py
│   │   │   │   ├── events/
│   │   │   │   │   ├── collector.py  attribution.py  identity.py
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── funnel.py  demand.py  abandoned.py  revenue.py
│   │   │   │   └── webhooks/
│   │   │   │       ├── verify.py          # HMAC + timestamp (replay himoyasi)
│   │   │   │       └── handlers/          # woocommerce.py shopify.py opencart.py generic.py
│   │   │   └── workers/
│   │   │       ├── settings.py            # ARQ
│   │   │       └── jobs/                  # sync_catalog.py embed_products.py
│   │   │                                  # detect_abandoned.py aggregate_daily.py
│   │   │                                  # cluster_demand.py retention.py retry_webhooks.py
│   │   ├── migrations/                    # Alembic
│   │   ├── tests/                         # unit/ integration/ contract/ e2e/
│   │   ├── scripts/                       # create_superadmin.py, seed_demo.py
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── dashboard/                         # Next.js: Analitika + Admin sahifalari
│   │   └── src/app/
│   │       ├── (auth)/login  register  forgot-password
│   │       ├── (app)/
│   │       │   ├── overview/              # KPI
│   │       │   ├── funnel/  demand/  carts/  searches/  colors-categories/
│   │       │   ├── catalog/               # sinxron holati, mahsulotlar
│   │       │   ├── integrations/          # kalitlar, domenlar, webhook, plagin
│   │       │   ├── team/                  # a'zolar va rollar
│   │       │   └── settings/              # threshold, til, tema, consent
│   │       └── (platform-admin)/          # faqat super_admin: tenantlar, modellar, monitoring
│   │
│   └── storefront/                        # Next.js (Premium)
│       └── src/app/  (catalog, product, cart, checkout, account, orders)
│
├── packages/
│   ├── widget/                            # TypeScript vidjet
│   │   ├── src/
│   │   │   ├── loader.ts                  # ~5KB, config olib, widget.js ni lazy yuklaydi
│   │   │   ├── widget/                    # UI (Shadow DOM), modal, kamera/upload
│   │   │   ├── detect/search-input.ts     # qidiruv maydonini avtomatik topish
│   │   │   ├── cart-adapters/             # none.ts woocommerce.ts shopify.ts opencart.ts custom.ts
│   │   │   ├── tracker/                   # events, sendBeacon, offline queue, listeners (dataLayer/fbq)
│   │   │   ├── identity.ts                # vd_sid, identify(), consent
│   │   │   └── i18n/                      # uz.json ru.json en.json
│   │   ├── tests/                         # Playwright: har platformada
│   │   └── build.config.ts                # → dist/v1/loader.js, widget.[hash].js
│   ├── sdk-js/                            # npm: @vision/sdk (React/Next uchun)
│   └── shared-types/                      # OpenAPI'dan generatsiya qilingan tiplar
│
├── integrations/                          # Platforma plaginlari (sotuvchi tomoni)
│   ├── woocommerce/                       # PHP plagin: feed, webhook, vd_sid → order meta
│   ├── shopify/                           # App/Script tag + webhook
│   ├── opencart/                          # extension (ocmod)
│   ├── laravel/                           # composer package (middleware + event)
│   ├── generic-php/                       # oddiy PHP snippet
│   └── README.md
│
├── infra/
│   ├── docker/                            # compose.dev.yml, compose.prod.yml
│   ├── nginx/                             # nginx.conf, security headers
│   ├── monitoring/                        # prometheus.yml, grafana/, alerts.yml
│   ├── backup/                            # pg_dump skriptlari, restore tekshiruvi
│   └── scripts/                           # deploy.sh, rollback.sh
│
├── docs/
│   ├── architecture.md  api-spec.md  data-model.md
│   ├── integration-guides/                # woocommerce.md shopify.md opencart.md custom.md
│   ├── privacy-and-consent.md  runbook.md  incident-playbook.md
│
├── .github/workflows/                     # ci.yml, deploy.yml, widget-release.yml
├── .env.example                           # hech qachon haqiqiy kalit emas
├── Makefile                               # make dev | test | migrate | lint
└── README.md                              # ushbu fayl
```

**Qatlam qoidasi:** `api/` → `services/` → `db/repositories/`. Router ichida SQL yozilmaydi; servis ichida HTTP tushunchasi bo'lmaydi.

---

## 6. Rollar va ruxsatlar

Ikki xil "foydalanuvchi" **aralashtirilmaydi**:

- **`users`** = bizning platforma foydalanuvchilari (dashboard/admin'ga kiruvchilar).
- **`shoppers` / `customers`** = do'kon xaridorlari (faqat Premium'da `customers` jadvali bor; Oddiy tarifda xaridor faqat anonim/opaque ID).

### Platforma darajasi (`users.platform_role`)

| Rol | Tavsif |
|---|---|
| `super_admin` | Barcha tenantlar, AI modellar, billing, monitoring |
| `support` | Tenantni ko'rish (faqat o'qish), impersonation faqat audit logi bilan |
| `user` | Oddiy (tenant a'zosi) |

### Tenant darajasi (`tenant_memberships.role`)

| Imkoniyat | owner | admin | catalog_manager* | analyst | viewer |
|---|:--:|:--:|:--:|:--:|:--:|
| Analitikani ko'rish | ✅ | ✅ | ✅ | ✅ | ✅ |
| Eksport (CSV) | ✅ | ✅ | ❌ | ✅ | ❌ |
| Katalog sozlash/sinxron | ✅ | ✅ | ✅ | ❌ | ❌ |
| Mahsulot/buyurtma boshqarish* | ✅ | ✅ | ✅ | ❌ | ❌ |
| API kalit/domen/webhook | ✅ | ✅ | ❌ | ❌ | ❌ |
| A'zolarni boshqarish | ✅ | ✅ | ❌ | ❌ | ❌ |
| Tarif/billing/tenantni o'chirish | ✅ | ❌ | ❌ | ❌ | ❌ |

\* Mahsulot/buyurtma boshqarish faqat **Premium**.

**Amalga oshirish:** `Depends(require_role("admin"))`. Ruxsat tekshiruvi servis qatlamida ham takrorlanadi, faqat frontendga ishonilmaydi. Barcha nozik amallar `audit_logs`ga yoziladi.

---

## 7. Ma'lumotlar bazasi sxemasi

**Qoidalar:** barcha vaqt `timestamptz` (UTC); pul **butun son** (`*_minor`, eng kichik birlik) + `currency CHAR(3)`; har bir tenant jadvalida `tenant_id` + **RLS**; tashqi ID'lar `UUID`, mahsulotning mijozdagi ID'si `external_id TEXT`.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ===== Platforma va kirish =====
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  plan TEXT NOT NULL CHECK (plan IN ('basic','premium')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('trial','active','suspended','deleted')),
  catalog_mode TEXT NOT NULL DEFAULT 'feed' CHECK (catalog_mode IN ('feed','proxy','hosted')),
  platform TEXT,                        -- woocommerce|shopify|opencart|custom
  settings JSONB NOT NULL DEFAULT '{}', -- threshold, til, tema, selektorlar, consent_mode, attribution_days
  data_region TEXT DEFAULT 'eu',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,          -- argon2id
  full_name TEXT,
  platform_role TEXT NOT NULL DEFAULT 'user' CHECK (platform_role IN ('super_admin','support','user')),
  totp_secret_enc BYTEA,                -- ixtiyoriy 2FA
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenant_memberships (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner','admin','catalog_manager','analyst','viewer')),
  PRIMARY KEY (user_id, tenant_id)
);

CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  public_key TEXT UNIQUE NOT NULL,      -- pk_live_xxx (vidjet)
  secret_key_hash TEXT NOT NULL,        -- sk_live_xxx faqat hash (bir marta ko'rsatiladi)
  webhook_secret_enc BYTEA NOT NULL,    -- HMAC uchun
  allowed_origins TEXT[] NOT NULL DEFAULT '{}',
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY, tenant_id UUID, actor_user_id UUID,
  action TEXT NOT NULL, target TEXT, meta JSONB, ip INET, created_at timestamptz DEFAULT now()
);

CREATE TABLE ai_models (                -- admin paneldan boshqariladi
  name TEXT PRIMARY KEY, priority INT NOT NULL, enabled BOOLEAN DEFAULT true,
  cooldown_until timestamptz, last_error TEXT
);

-- ===== Katalog (barcha rejimlar yagona formatga keltiriladi) =====
CREATE TABLE catalog_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  external_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT, color TEXT, attributes JSONB DEFAULT '{}',
  price_minor BIGINT, currency CHAR(3),
  image_url TEXT, product_url TEXT NOT NULL,
  in_stock BOOLEAN NOT NULL DEFAULT true,
  embedding vector(768),               -- o'lcham embedding modeliga mos (config)
  content_hash TEXT,                   -- o'zgarmagan mahsulotni qayta embedding qilmaslik uchun
  is_deleted BOOLEAN NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, external_id)
);
CREATE INDEX ON catalog_products USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON catalog_products (tenant_id, category) WHERE in_stock AND NOT is_deleted;

CREATE TABLE catalog_sync_runs (
  id BIGSERIAL PRIMARY KEY, tenant_id UUID NOT NULL, status TEXT, items_seen INT, items_changed INT,
  error TEXT, started_at timestamptz, finished_at timestamptz
);

-- ===== Qidiruv va xaridor identifikatsiyasi =====
CREATE TABLE sessions (                -- anonim first-party sessiya
  id TEXT PRIMARY KEY,                 -- vd_sid
  tenant_id UUID NOT NULL, first_seen timestamptz DEFAULT now(), last_seen timestamptz,
  consent BOOLEAN NOT NULL DEFAULT false, device TEXT, country CHAR(2)
);

CREATE TABLE identity_links (          -- sessiya ↔ sotuvchining ichki xaridor ID'si
  tenant_id UUID NOT NULL, session_id TEXT NOT NULL,
  customer_ref TEXT NOT NULL,          -- masalan "u_1842" (username/email EMAS)
  linked_at timestamptz DEFAULT now(),
  PRIMARY KEY (tenant_id, session_id, customer_ref)
);

CREATE TABLE visual_searches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL, session_id TEXT, customer_ref TEXT,
  image_hash TEXT NOT NULL,            -- sha256; asl rasm SAQLANMAYDI
  prompt_version TEXT NOT NULL,
  ai_detected JSONB NOT NULL,          -- category,color,type,tags,confidence
  model_used TEXT, best_score REAL,
  is_unmet_demand BOOLEAN NOT NULL DEFAULT false,
  demand_key TEXT,                     -- "kiyim|sariq|xudi"
  latency_ms INT, from_cache BOOLEAN DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON visual_searches (tenant_id, created_at DESC);
CREATE INDEX ON visual_searches (tenant_id, demand_key) WHERE is_unmet_demand;

-- ===== Hodisalar (oyiga partitsiyalanadi) =====
CREATE TABLE events (
  event_id UUID NOT NULL,              -- idempotentlik kaliti
  tenant_id UUID NOT NULL, session_id TEXT, customer_ref TEXT, search_id UUID,
  type TEXT NOT NULL CHECK (type IN ('SEARCH','RESULT_VIEW','PRODUCT_CLICK','ADD_TO_CART','REMOVE_FROM_CART','PURCHASE')),
  product_external_id TEXT, qty INT DEFAULT 1,
  price_minor BIGINT, currency CHAR(3),
  order_ref TEXT,                      -- PURCHASE uchun
  source TEXT NOT NULL CHECK (source IN ('widget','webhook','server','storefront')),
  ts timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, event_id, ts)
) PARTITION BY RANGE (ts);

CREATE TABLE cart_sessions (           -- tashlab ketilgan savat hisobi uchun
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL, session_id TEXT, customer_ref TEXT, search_id UUID,
  items JSONB NOT NULL, total_minor BIGINT, currency CHAR(3),
  state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open','purchased','abandoned')),
  last_activity_at timestamptz NOT NULL, closed_at timestamptz
);

-- ===== Agregatlar =====
CREATE TABLE unmet_demand_clusters (
  tenant_id UUID, demand_key TEXT, sample_query TEXT, search_count INT, unique_sessions INT,
  first_seen timestamptz, last_seen timestamptz, ai_suggestion TEXT,
  PRIMARY KEY (tenant_id, demand_key)
);
CREATE TABLE daily_stats (
  tenant_id UUID, date DATE, metrics JSONB NOT NULL, PRIMARY KEY (tenant_id, date)
);

-- ===== Webhooklar =====
CREATE TABLE webhook_deliveries (
  id BIGSERIAL PRIMARY KEY, tenant_id UUID, source TEXT, external_id TEXT,
  payload JSONB, status TEXT, attempts INT DEFAULT 0, next_retry_at timestamptz, error TEXT,
  UNIQUE (tenant_id, source, external_id)          -- takror webhook'dan himoya
);

-- ===== Faqat PREMIUM =====
CREATE TABLE customers (id UUID PRIMARY KEY, tenant_id UUID, email CITEXT, phone TEXT,
  password_hash TEXT, full_name TEXT, created_at timestamptz DEFAULT now(), UNIQUE (tenant_id, email));
CREATE TABLE carts (id UUID PRIMARY KEY, tenant_id UUID, customer_id UUID, session_id TEXT, updated_at timestamptz);
CREATE TABLE cart_items (cart_id UUID, product_id UUID, qty INT CHECK (qty > 0), price_minor BIGINT);
CREATE TABLE orders (id UUID PRIMARY KEY, tenant_id UUID, customer_id UUID, number TEXT,
  status TEXT, total_minor BIGINT, currency CHAR(3), search_id UUID, session_id TEXT, created_at timestamptz);
CREATE TABLE order_items (order_id UUID, product_id UUID, name TEXT, qty INT, price_minor BIGINT);

-- ===== RLS (har tenant jadvali uchun) =====
ALTER TABLE visual_searches ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON visual_searches
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
-- (events, catalog_products, cart_sessions, ... uchun ham xuddi shunday)
```

**Retention (ma'lumot saqlash muddati):** xom `events` 13 oy, `visual_searches` 13 oy, `sessions` 90 kun harakatsiz bo'lsa o'chiriladi; agregatlar cheksiz. Worker `retention` jobi bajaradi.

---

## 8. Sotuvchi katalogi bilan ulanish

**Asosiy qoida:** sotuvchining bazasiga to'g'ridan-to'g'ri ulanmaymiz. Hamma manba `CatalogProvider` interfeysi orqali yagona `Product` formatiga keltiriladi:

```
Product { external_id, name, description?, category, color?, attributes{},
          price_minor, currency, image_url, product_url, in_stock }
```

| Rejim | Tarif | Qanday ishlaydi | Eslatma |
|---|---|---|---|
| **feed** (tavsiya) | Oddiy | Plagin yoki Google Merchant XML / CSV / REST feed. Worker har 15–60 daq yangilaydi, o'zgarganlarini (`content_hash`) embedding qiladi | Tez, sotuvchi serveriga yuk yo'q. Narx/zaxira tezkor yangilanishi uchun webhook `product.updated` |
| **proxy** | Oddiy (maxsus tizimlar) | Biz sotuvchi `GET /search?q=&category=&color=&limit=` endpointini chaqiramiz | Timeout 2 s; xato bo'lsa avtomatik **feed snapshot**ga qaytadi |
| **hosted** | Premium | Katalog bizning bazamizda | To'liq nazorat |

**Sinxron xatolaridan himoya:**
- Feed 0 ta mahsulot qaytarsa yoki 50% dan ko'pi yo'qolsa, **eski katalog o'chirilmaydi**, sinxron `failed` deb belgilanadi va dashboardda ogohlantirish chiqadi.
- O'chirilgan mahsulotlar darhol o'chirilmaydi: `is_deleted=true` (soft delete).
- Natijada ko'rsatishdan oldin (ixtiyoriy) narx/zaxira **live tekshiruv** (`GET product` yoki cache TTL 5 daq).

---

## 9. Rasm orqali qidiruv jarayoni

```
Vidjet: rasmni brauzerda 1024px gacha kichraytirish → JPEG (~200–400KB)
   │ POST /v1/public/visual-search  (public key, Origin, session_id, consent)
   ▼
1. Gateway: key + Origin tekshiruvi → rate limit (IP, tenant, session) → hajm ≤ 5MB, magic bytes (JPEG/PNG/WebP), EXIF o'chirish
2. Kesh: sha256(rasm) + PROMPT_VERSION  → bor bo'lsa Gemini chaqirilmaydi
3. Vision Service: Gemini'ga strukturali JSON (response schema) — category, color, type, style, tags, search_query, confidence
      • Model router: timeout 8 s, 429/5xx → model "sovutiladi" (circuit breaker), keyingisiga o'tadi
      • Hammasi ishlamasa → fallback: matn-yo'q rejimi? yo'q → 503 + vidjetda "Hozircha rasm tahlili mavjud emas"
      • JSON validatsiyadan o'tmasa → 1 marta qayta so'rash, so'ng xato
4. Matching Engine (tenant katalogi bo'yicha):
      a) atribut filtri (kategoriya, in_stock)
      b) pgvector o'xshashlik (query embedding)
      c) ball = 0.6·vektor + 0.25·atribut moslik (rang/tur) + 0.1·mavjudlik + 0.05·mashhurlik
5. Unmet demand: best_score < tenant.threshold  (default 0.45) → belgilanadi, demand_key hisoblanadi
6. Javob: { search_id, ai_detected, products[], is_unmet_demand }  — saqlash asinxron
```

**Muhim:**
- **Asl rasm hech qayerda saqlanmaydi** (faqat hash va atributlar).
- Natija bo'sh bo'lsa vidjet "O'xshash tovar topilmadi" ko'rsatadi va yaqin kategoriyadan tavsiya beradi (bu ham `unmet demand` bo'ladi).
- Javob muvaffaqiyatli, lekin saqlash xato bo'lsa — foydalanuvchiga ta'sir qilmaydi (navbatga qaytariladi).

---

## 10. Vidjet: 1 teg bilan integratsiya

```html
<script src="https://cdn.vision.uz/v1/loader.js" data-key="pk_live_xxx" async></script>
```

`</body>` oldiga qo'yish yetarli. Loader quyidagilarni o'zi bajaradi:

1. `GET /v1/public/config/{public_key}` (CDN keshlangan, 5 daq) → rejim, tema, til, selektorlar, savat adapteri, consent rejimi.
2. **Qidiruv maydonini topish:** `input[type=search]`, `[name=q|s|search|query]`, `[placeholder*=qidir i]`; topilmasa tenant sozlamasidagi selektor; hech biri bo'lmasa **suzuvchi kamera tugmasi**. Dinamik (SPA) sahifalar uchun `MutationObserver`.
3. Katta `widget.js` faqat tugma bosilganda **lazy** yuklanadi (sayt tezligiga ta'sir yo'q).
4. UI **Shadow DOM** ichida (mijoz CSS i bilan to'qnashmaydi); `z-index` faqat modal uchun.
5. **Fail-open:** hamma narsa `try/catch`da; config/API ishlamasa vidjet **jim yashirinadi**, sayt ishlashda davom etadi. Global faqat `window.__vd`.
6. Mobil: `<input type="file" accept="image/*" capture="environment">`, drag&drop.
7. Dublikat himoyasi: loader ikki marta qo'shilsa, ikkinchisi o'zini to'xtatadi.

**Integratsiyada tez uchraydigan muammolar va yechimlar:**

| Muammo | Yechim |
|---|---|
| Mijoz saytida CSP (`script-src`/`connect-src`) bloklaydi | Docs'da aniq CSP qatori beriladi: `script-src https://cdn.vision.uz; connect-src https://api.vision.uz` |
| Adblock "analytics/track" so'zlarini bloklaydi | Neytral endpoint nomlari (`/v1/e`, `/v1/s`) va ixtiyoriy **CNAME** (`vision.mijoz.uz` → bizning API) |
| Safari ITP cookie'ni 7 kunda o'chiradi | `vd_sid` localStorage + CNAME orqali server-set cookie |
| HTTPS saytda HTTP API (mixed content) | Faqat HTTPS, `127.0.0.1` faqat dev rejimida |
| CORS xatolari | Tenant `allowed_origins` bo'yicha dinamik `Access-Control-Allow-Origin` |
| Eski kesh qolishi | `loader.js` qisqa TTL (5 daq), `widget.[hash].js` cheksiz TTL |
| Kod xatosi hamma saytni buzishi | Kanary release (1% tenant), `widget-release.yml`da avtomatik rollback |

---

## 11. Savat va xaridni kuzatish

Oddiy tarifda bizda savat yo'q. Vidjet savatni **boshqarmaydi**, platformaga topshiradi.

### 11.1 Savatga qo'shish (Cart Adapter)

| Daraja | Qanday | Qachon |
|---|---|---|
| **0. Nol sozlama** | Tugma `product_url?vd=<search_id>` ga olib boradi, sotuvchining o'z sahifasi savatga qo'shadi | Default, hamma saytda ishlaydi |
| **1. Platforma adapteri** | WooCommerce `?add-to-cart=ID` / `wc-ajax`; Shopify `POST /cart/add.js`; OpenCart `route=checkout/cart.add` | `tenant.platform` bo'yicha |
| **2. Maxsus callback** | `window.VisionAnalytics.onAddToCart = (p) => myShop.add(p.id)` | Maxsus saytlar |

### 11.2 Hodisalarni yig'ish

- **Avtomatik:** vidjet `dataLayer` (GA4 `add_to_cart`, `purchase`), `fbq` va platforma hodisalarini (Woo `added_to_cart`, Shopify `/cart/add` fetch) tinglaydi.
- **Qo'lda:** `VisionAnalytics.track('ADD_TO_CART', { id: '7', price: 129000, currency: 'UZS', qty: 1 })`.
- Yuborish: `navigator.sendBeacon` (sahifa yopilsa ham ketadi), har hodisada `event_id` (UUID), oflayn bo'lsa localStorage navbatida saqlab keyin yuboriladi.

### 11.3 Atribusiya (qaysi qidiruv sotuvga olib keldi)

- Qidiruvda `search_id` + `vd_sid` yoziladi.
- Mahsulot havolasiga `?vd=<search_id>` qo'shiladi; loader uni o'qib saqlaydi (30 kun, sozlanadi: `attribution_days`).
- Model: **last-touch**, oyna 7 kun (default). `PURCHASE` oxirgi `search_id` ga bog'lanadi.

### 11.4 Xarid (PURCHASE): ishonchli yo'l

1. **Server webhook (asosiy):** `order.created` → `POST /v1/server/webhooks/{platform}`, HMAC-SHA256 imzo + `X-Timestamp` (±5 daq, replay himoyasi), `UNIQUE(source, external_id)` bilan takrorlanish yo'q.
2. Savat yaratilganda `vd_sid` ni **savat/buyurtma meta**ga yozish (Woo: order meta, Shopify: cart attribute, OpenCart: session→order comment/meta). Plagin buni avtomatik bajaradi.
3. **Zaxira:** "rahmat" sahifasida URL pattern bo'yicha loader `PURCHASE` yuboradi (brauzer yopilsa yo'qolishi mumkin, shuning uchun webhook ustun; ikkalasi kelsa `order_ref` bo'yicha birlashtiriladi).

### 11.5 "Tashlab ketilgan savat"

Bu to'g'ridan-to'g'ri hodisa emas, **hisoblanadi**: `ADD_TO_CART` → `cart_sessions.state='open'`; `abandon_after_hours` (default 24) ichida `PURCHASE` bo'lmasa, fon vazifasi `abandoned` qiladi. `PURCHASE` kelsa `purchased`.

---

## 12. Ro'yxatdan o'tgan foydalanuvchi (identifikatsiya) va sotuvchi bazasiga ta'sir

**Savol:** foydalanuvchi sotuvchi saytida ro'yxatdan o'tgan bo'lsa, uning *username*'ini analitikaga uzatamizmi?

**Javob: yo'q, username/email/telefon uzatilmaydi.** Faqat sotuvchining **ichki neytral ID**si (`customer_ref`, masalan `u_1842` yoki `1842`) uzatiladi. Sabab: maxfiylik (shaxsiy ma'lumot bizga kerak emas), huquqiy xavf, ma'lumot sizib chiqish xavfini kamaytirish. Analitika uchun bu yetarli.

### Identifikatsiya darajalari

| Daraja | Nima uzatiladi | Nima beradi |
|---|---|---|
| **L0 – Anonim** (default) | faqat `vd_sid` | Voronka, talab, rang, kategoriya |
| **L1 – Identify** | `VisionAnalytics.identify('u_1842')` (login bo'lganda) | Bir xaridorning qurilmalararo harakati, takroriy xaridorlar (repeat rate), LTV |
| **L2 – Server** | Webhookda `customer_ref` + `order_ref` | Eng ishonchli: buyurtma ↔ xaridor ↔ qidiruv |

```js
// Sotuvchi saytida, foydalanuvchi login qilgandan keyin (1 qator):
window.VisionAnalytics.identify('u_1842');   // username/email BERILMAYDI
window.VisionAnalytics.logout();             // sessiyani uzadi
```

### Qoidalar

1. **PII validatsiyasi:** `customer_ref` e-mail/telefon ko'rinishida bo'lsa (`@`, `+998...`), API `422` qaytaradi va saqlamaydi.
2. **Consent:** `consent=false` bo'lsa `identify` e'tiborga olinmaydi (L0 da qoladi).
3. **Stitching:** `identity_links` jadvali orqali `vd_sid ↔ customer_ref` bog'lanadi; identify'dan oldingi anonim hodisalar ham (oxirgi 30 kun) shu xaridorga bog'lanadi.
4. **Dashboardda:** xaridor `Mijoz #a91f` ko'rinishida (ID hash'ining qisqa qismi). Haqiqiy profilni ochish uchun tenant sozlamasida **deep-link shablon**: `https://shop.uz/admin/customers/{customer_ref}`, bosilganda sotuvchining o'z adminkasi ochiladi (ma'lumot bizdan o'tmaydi).
5. **O'chirish huquqi (GDPR/shaxsiy ma'lumotlar):** `DELETE /v1/server/customers/{customer_ref}` barcha bog'liq yozuvlarni o'chiradi/anonimlashtiradi.

### Sotuvchi bazasiga ta'sir (muhim)

| Savol | Javob |
|---|---|
| Sotuvchi bazasiga yozamizmi? | **Yo'q.** Biz sotuvchi DB'siga umuman ulanmaymiz |
| Qanday ma'lumot olamiz? | Faqat u o'zi bergan: feed/API (mahsulotlar) va webhook (buyurtmalar) |
| Savatga qo'shish qayerda sodir bo'ladi? | **Sotuvchining o'z platformasida.** Biz tugma orqali uning mexanizmini chaqiramiz |
| Plagin nima qiladi? | Faqat 3 ta: (1) feed endpoint ochadi, (2) `order.created` webhook yuboradi, (3) `vd_sid` ni buyurtma meta'siga yozadi. Mavjud jadvallarni o'zgartirmaydi (Woo `postmeta`/`order meta` kabi standart kengaytma joylaridan foydalanadi) |
| Plagin sayt tezligiga ta'sir qiladimi? | Webhooklar asinxron, xato bo'lsa buyurtma jarayonini **bloklamaydi** (try/catch + timeout 3 s) |
| Plagin o'chirilsa? | Sotuvchi ma'lumotlari saqlanib qoladi, faqat `vd_*` meta qiymatlari qoladi (zararsiz) |
| Maxsus sayt (plaginsiz) | Sotuvchi backend'i `POST /v1/server/events` (secret key bilan) chaqiradi, 10 qator kod |

```php
// Maxsus PHP/Laravel sayt: buyurtma yaratilgandan keyin (server-to-server)
$payload = ['event_id'=>Str::uuid(), 'type'=>'PURCHASE', 'order_ref'=>$order->id,
            'customer_ref'=>(string)$user->id, 'session_id'=>$order->vd_sid,
            'items'=>[['id'=>'7','qty'=>1,'price_minor'=>12900000]], 'currency'=>'UZS'];
$sig = hash_hmac('sha256', $ts.'.'.json_encode($payload), $webhookSecret);
Http::timeout(3)->withHeaders(['X-Timestamp'=>$ts,'X-Signature'=>$sig])
    ->post('https://api.vision.uz/v1/server/events', $payload);   // xato bo'lsa, buyurtma baribir davom etadi
```

---

## 13. Analitika: metrikalar va formulalar

Barcha metrikalar **bir xil ta'rif** bilan hisoblanadi (xatolik va mos kelmaslikni oldini olish uchun):

| Metrika | Ta'rif |
|---|---|
| **AI qidiruvlar** | `COUNT(visual_searches)` (kesh orqali kelganlari ham, `from_cache` ajratiladi) |
| **Qidiruvchilar** | `COUNT(DISTINCT session_id)` |
| **Natija ko'rdi** | Natija ro'yxati ko'rsatilgan qidiruvlar |
| **Bosdi (click)** | `PRODUCT_CLICK` bo'lgan qidiruvlar |
| **Savatga qo'shdi** | `ADD_TO_CART` bog'langan **noyob qidiruvlar** |
| **Xarid** | `PURCHASE` bog'langan noyob qidiruvlar (atribusiya oynasi ichida) |
| **Konversiya %** | `xarid qilgan qidiruvlar / jami qidiruvlar × 100` |
| **Yo'qotilgan daromad** | `SUM(cart_sessions.total_minor) WHERE state='abandoned'` (valyuta bo'yicha alohida) |
| **Qondirilmagan talab** | `is_unmet_demand=true` qidiruvlar, `demand_key` bo'yicha guruhlangan (soni, noyob sessiyalar) |
| **Attributed revenue** | Qidiruvga bog'langan `PURCHASE` summasi |

**Voronka:** Qidirdi → Natija ko'rdi → Mahsulot bosdi → Savatga soldi → Xarid qildi (har bosqich noyob `search_id` bo'yicha, bosqichdan bosqichga % ko'rsatiladi).

**Qondirilmagan talab sifati:** "sariq xudi", "sariq kapyushonli kofta", "yellow hoodie" **bir** talab bo'lishi uchun `demand_key = kategoriya|rang|tur` AI atributlaridan **normalizatsiya** qilinadi (lug'at: xudi=hoodie=kapyushon). Keyin worker embedding klasterlash bilan yaqin kalitlarni birlashtiradi. `ai_suggestion` — "bu tovarni katalogga qo'shing" tavsiyasi.

**Hisoblash strategiyasi:** real-time so'rovlar faqat oxirgi 24 soat uchun; qolgani `daily_stats` agregatidan (dashboard tez ishlashi uchun). Vaqt zonasi tenant sozlamasida (default `Asia/Tashkent`), saqlash UTC'da.

---

## 14. Admin va Dashboard sahifalari

### 14.1 Tenant dashboard (analitika sahifasi)

| Sahifa | Mazmun | Minimal rol |
|---|---|---|
| **Overview** | 4 KPI (qidiruvlar, savatga qo'shilgan, yo'qotilgan daromad, konversiya) + sana filtri | viewer |
| **Funnel** | Voronka diagrammasi va bosqichlar bo'yicha yo'qotish | viewer |
| **Unmet Demand** | Qondirilmagan talab jadvali, AI tavsiya, CSV eksport | analyst |
| **Abandoned Carts** | Tovar bo'yicha yo'qotilgan summa; promo taklif qilish uchun ro'yxat | analyst |
| **Searches Log** | Real-time jurnal (vaqt, kategoriya, rang, model, kesh) | analyst |
| **Colors & Categories** | Eng ommabop ranglar/kategoriyalar, soatlik dinamika | viewer |
| **Catalog** | Sinxron holati, oxirgi xato, mahsulotlar soni, qo'lda "Sync now" | catalog_manager |
| **Integrations** | Public/secret kalit, domen allowlist, webhook URL va maxfiy kalit, platforma tanlash, "Ulanishni tekshirish" tugmasi (test hodisa yuboradi) | admin |
| **Team** | A'zolarni taklif qilish, rol berish | admin |
| **Settings** | Threshold, til, tema, consent rejimi, attribution oynasi, abandoned soati, valyuta | admin |

**Integratsiya diagnostikasi (xatolarni ertaroq ushlash):** Integrations sahifasi "Install check" beradi: vidjet saytda topildimi, domen allowlist'dami, oxirgi hodisa qachon kelgan, webhook imzosi to'g'rimi, feed oxirgi sinxron natijasi. Hodisalar 24 soat kelmasa, owner'ga e-mail ogohlantirish.

### 14.2 Platforma admin (faqat `super_admin`)

Tenantlar (yaratish, tarif, to'xtatish), foydalanuvchilar, **AI modellar** (priority, yoqish/o'chirish, cooldown holati, xatolar), tizim salomatligi (queue uzunligi, Gemini xato %, p95), audit log, impersonation (faqat jurnal bilan).

---

## 15. Premium Storefront

Storefront Core'ning oddiy klienti: faqat `storefront/` API'larini ishlatadi, `hosted` katalog rejimi.

- **Sahifalar:** katalog, mahsulot, savat, checkout, hisob (buyurtmalar tarixi), qidiruv (matn + rasm).
- **Savat/buyurtma:** `carts`, `orders` jadvallari; narx **serverda qayta hisoblanadi** (klientdan kelgan narxga ishonilmaydi); zaxira tranzaksiyada kamaytiriladi (`SELECT ... FOR UPDATE`).
- **Hodisalar:** Storefront o'zi `source='storefront'` hodisalarini yuboradi, analitika bilan bir xil quvur.
- **Auth:** xaridorlar `customers` jadvalida (dashboard `users`dan alohida), JWT.
- **Admin (Premium):** mahsulot CRUD, rasm yuklash (S3-mos storage), buyurtma statuslari, mijozlar.
- **To'lov (2-bosqich):** Payme/Click: idempotent callback, buyurtma `pending → paid`, imzo tekshiruvi.

---

## 16. API ro'yxati

Versiya: `/v1`. Xato formati yagona:
`{ "error": { "code": "RATE_LIMITED", "message": "...", "request_id": "..." } }`

| Guruh | Endpoint | Auth |
|---|---|---|
| **Public (vidjet)** | `GET /v1/public/config/{pk}` | public key + Origin |
| | `POST /v1/public/visual-search` (multipart) | public key + Origin |
| | `POST /v1/public/events` (batch, `event_id`) | public key + Origin |
| | `POST /v1/public/identify` | public key + Origin + consent |
| | `GET /v1/public/products?q=&category=` | public key + Origin |
| **Server** | `POST /v1/server/events` | secret key + HMAC |
| | `POST /v1/server/webhooks/{platform}` | HMAC + timestamp |
| | `POST /v1/server/catalog/push` (mahsulotlar batch) | secret key |
| | `DELETE /v1/server/customers/{ref}` | secret key |
| **Dashboard** | `POST /v1/auth/login · refresh · logout · forgot` | — |
| | `GET /v1/dashboard/analytics/{overview,funnel,demand,carts,searches,colors}` | JWT + rol |
| | `GET/POST /v1/dashboard/catalog · /sync` | JWT + rol |
| | `GET/POST/DELETE /v1/dashboard/keys · /members · /settings` | JWT + admin |
| **Platform admin** | `/v1/admin/tenants · users · ai-models · health` | JWT + super_admin |
| **Storefront** | `/v1/storefront/*` | Premium + JWT/anonim |
| **Tizim** | `GET /healthz` (liveness), `GET /readyz` (DB+Redis tekshiradi), `/metrics` (ichki tarmoq) | — |

**Visual-search javobi:**
```json
{
  "search_id": "9b926a65-def9-47ed-8e42-dc4e41ae4bab",
  "ai_detected": { "category": "poyabzal", "color": "qizil", "type": "krossovka",
                   "tags": ["sport"], "search_query": "qizil sport krossovka", "confidence": 0.93 },
  "best_match_score": 0.85,
  "is_unmet_demand": false,
  "products": [ { "id": "7", "name": "...", "price_minor": 129000000, "currency": "UZS",
                  "image_url": "...", "product_url": "...?vd=9b926a65...", "in_stock": true, "score": 0.85 } ]
}
```
(`model_used` mijozga ko'rsatilmaydi, faqat ichki jurnalda.)

---

## 17. Xatoliklarning oldini olish (risk jadvali)

| # | Xavf | Oldini olish |
|---|---|---|
| 1 | Vidjet mijoz saytini buzadi | Shadow DOM, fail-open, `try/catch`, lazy yuklash, kanary release, Playwright testlari har platformada |
| 2 | Gemini model o'chdi/nomi o'zgardi/limit | `ai_models` jadvali, startup tekshiruvi, circuit breaker, model rotatsiyasi, timeout, pullik kalit, Sentry ogohlantirish |
| 3 | Gemini noto'g'ri JSON qaytaradi | Response schema + Pydantic validatsiya + 1 retry; aks holda xato, hodisa buzilmaydi |
| 4 | Birov kvotani tugatadi (abuse) | Public key + Origin allowlist, rate limit (IP/session/tenant), kunlik tenant kvotasi, 5MB limit, kesh, Cloudflare WAF/Turnstile |
| 5 | Bir do'kon boshqasini ma'lumotini ko'radi | `tenant_id` hamma jadvalda, **PostgreSQL RLS**, repository qatlami, tenant izolyatsiya testlari |
| 6 | Hodisa takror/yo'qoladi | `event_id` idempotentlik, `sendBeacon`, oflayn navbat, webhook retry (eksponensial, DLQ) |
| 7 | Konversiya noto'g'ri | `search_id` atribusiyasi, yagona formulalar (13-bo'lim), webhook asosiy manba |
| 8 | Pul hisobida yaxlitlash xatosi | Butun son (`*_minor`) + valyuta; hech qachon `float` |
| 9 | Vaqt zonasi chalkashligi | Saqlash UTC, ko'rsatish tenant zonasida |
| 10 | Katalog sinxroni katalogni "bo'shatib" yuboradi | 0/50% himoyasi, soft delete, snapshot, sinxron tarixi |
| 11 | Mijoz API'si sekin/ishlamaydi (proxy) | Timeout 2 s, circuit breaker, feed snapshot fallback |
| 12 | Webhook soxta/takror | HMAC + timestamp ±5 daq + `UNIQUE(source, external_id)` |
| 13 | Plagin buyurtmani bloklaydi | Webhook asinxron, timeout 3 s, xatoda buyurtma davom etadi |
| 14 | Migratsiya ishlab turgan bazani buzadi | Alembic, backward-compatible o'zgarishlar (expand → migrate → contract), staging'da sinov, deploydan oldin backup |
| 15 | Ma'lumot hajmi o'sib ketadi | `events` oylik partitsiya, retention job, agregatlar, indekslar |
| 16 | Dashboard sekin | `daily_stats` agregatlar, Redis kesh (60 s), so'rov limitlari |
| 17 | Parol/kalitlar sizadi | argon2id, kalitlar faqat hash, `.env` git'da yo'q, secrets manager, kalit rotatsiyasi, 2FA |
| 18 | Foydalanuvchi shaxsiy ma'lumoti sizadi | PII validatsiyasi, rasm saqlanmaydi, IP anonimlashtirish (oxirgi oktet), consent, o'chirish API'si |
| 19 | Dependency zaifliklari | Dependabot, `pip-audit`, `npm audit`, Docker image skanerlash (Trivy) |
| 20 | Worker to'xtab qoladi | Healthcheck, avto-restart, navbat uzunligi alerti, joblar idempotent |
| 21 | Bitta komponent yiqilsa hammasi yiqiladi | Graceful degradation: Redis yo'q → kesh/limit o'tkazib yuboriladi (qidiruv ishlaydi); saqlash xato → navbat; Gemini yo'q → 503 va tushunarli xabar |
| 22 | Noto'g'ri sozlama bilan ishga tushish | `pydantic-settings` startup validatsiyasi: majburiy o'zgaruvchi yo'q bo'lsa server **ishga tushmaydi** |
| 23 | Rasm bilan hujum (zararli fayl, katta piksel) | Magic bytes, piksel limiti (decompression bomb), EXIF o'chirish, qayta kodlash |
| 24 | Prompt injection (rasm ichidagi matn) | AI faqat strukturali maydonlar qaytaradi; natija whitelist bo'yicha tekshiriladi, o'zi buyruq bajarmaydi |

---

## 18. Xavfsizlik va maxfiylik

- **Kalitlar:** `pk_live_` (ochiq, domenga bog'langan) va `sk_live_` (maxfiy, faqat hash saqlanadi). Rotatsiya va bekor qilish dashboardda.
- **Transport:** faqat HTTPS, HSTS; ichki servislar yopiq tarmoqda; DB/Redis tashqariga ochilmaydi.
- **Sarlavhalar:** CSP, `X-Content-Type-Options`, `Referrer-Policy`; Swagger/`/docs` production'da **o'chiq** (yoki IP allowlist).
- **Auth:** JWT 15 daq, refresh httpOnly+Secure+SameSite cookie, login rate limit va lockout, ixtiyoriy TOTP 2FA, parol tiklash bir martalik token bilan.
- **Maxfiylik:** asl rasm saqlanmaydi; faqat hash va atributlar; IP oxirgi oktet maskalanadi; consent bayrog'i; retention muddati; o'chirish so'rovi API'si; xaridor analitikasida PII yo'q.
- **Gemini:** production uchun pullik kalit (bepul tarifda ma'lumotlar xizmatni yaxshilash uchun ishlatilishi mumkin, shartlarni tekshiring).
- **Audit:** kalit yaratish/o'chirish, rol o'zgartirish, eksport, impersonation: hammasi `audit_logs`da.
- **Zaxira:** shifrlangan backup, restore muntazam sinovdan o'tkaziladi.

---

## 19. Sozlamalar (.env)

`.env.example` (haqiqiy qiymatlar faqat secrets manager/serverda):

```ini
APP_ENV=production                    # development|staging|production
APP_SECRET_KEY=                       # majburiy, 64+ belgi
PUBLIC_API_URL=https://api.vision.uz
CDN_URL=https://cdn.vision.uz

DATABASE_URL=postgresql+asyncpg://vision:***@db:5432/vision
REDIS_URL=redis://redis:6379/0

GEMINI_API_KEY=                       # pullik loyiha kaliti
GEMINI_MODELS=                        # boshlang'ich ro'yxat (keyin ai_models jadvalidan)
EMBEDDING_MODEL=                      # config orqali; vector o'lchami migratsiyaga mos
AI_TIMEOUT_SECONDS=8
AI_DAILY_BUDGET_USD=50                # tenant va umumiy kunlik limit

JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=30
CORS_DASHBOARD_ORIGINS=https://app.vision.uz

MAX_IMAGE_MB=5
RATE_LIMIT_SEARCH_PER_MIN_IP=10
RATE_LIMIT_SEARCH_PER_MIN_TENANT=120
DEFAULT_UNMET_THRESHOLD=0.45
ABANDON_AFTER_HOURS=24
ATTRIBUTION_DAYS=7

SENTRY_DSN=
SMTP_URL=                             # parol tiklash va ogohlantirishlar
STORAGE_URL=                          # S3-mos (Premium rasmlar, backup)
```

---

## 20. Lokal ishga tushirish

> Joriy holat (v2.1): baza — **MySQL 8**, Redis ixtiyoriy, Windows'da sinalgan. Batafsil MySQL farqlari: [apps/api/README.md](apps/api/README.md).

### 20.1 Bir martalik o'rnatish

| Talab | Versiya |
|---|---|
| Python | 3.11+ |
| Node.js | 20+ |
| MySQL | 8.0 (`vision_detect_event_handler` bazasi) |
| Gemini API kalit | ixtiyoriy — bo'lmasa "demo vision" rejimi |

```bash
# 1) Muhit fayli
cp .env.example .env
#   DATABASE_URL=mysql://root:1234@127.0.0.1:3306/vision_detect_event_handler
#   APP_SECRET_KEY=<64+ belgili tasodifiy satr>
#   GEMINI_API_KEY=<kalit>   GEMINI_MODELS=gemini-3.5-flash,gemini-3.1-flash-lite,gemini-flash-latest

# 2) API (Python)
cd apps/api
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt          # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m alembic upgrade head           # jadvallar (0001 + 0002)
.venv/Scripts/python scripts/create_superadmin.py --email admin@vision.uz --password Admin12345
.venv/Scripts/python scripts/seed_demo.py              # demo do'kon + 24 mahsulot (analitika BO'SH)

# 3) Frontendlar
cd ../dashboard  && npm install
cd ../storefront && npm install                         # .env.local ni seed_demo.py o'zi yozadi
```

### 20.2 Har kuni ishga tushirish (3 ta terminal)

```bash
# Terminal 1 — API + fon vazifalari (RUN_WORKER_IN_API=true)
cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Dashboard (analitika va admin)
cd apps/dashboard && npm run dev        # http://localhost:3000

# Terminal 3 — Storefront (Premium savdo do'koni)
cd apps/storefront && npm run dev       # http://localhost:3001
```

| Manzil | Nima | Kirish |
|---|---|---|
| http://localhost:3000 | Dashboard | `demo@vision.uz` / `Demo12345` (do'kon egasi) |
| http://localhost:3000/admin/tenants | Platforma admin | `admin@vision.uz` / `Admin12345` |
| http://localhost:3001 | Storefront (savdo do'koni) | xaridor sifatida ro'yxatdan o'ting yoki mehmon |
| http://localhost:3001/image-search | Rasm orqali qidiruv sahifasi | — |
| http://127.0.0.1:8000/demo/vanilla | Vidjet ulangan oddiy HTML sayt | — |
| http://127.0.0.1:8000/docs | Swagger (faqat development) | — |

**Test to'lov kartalari** (haqiqiy pul yechilmaydi): `4242 4242 4242 4242` — muvaffaqiyatli, `4000 0000 0000 0002` — rad etiladi, muddat istalgan kelajak sanasi (`12/29`).

### 20.3 Foydali buyruqlar

```bash
python scripts/reset_analytics.py              # nimalar o'chishini ko'rsatadi (hech narsa o'chirmaydi)
python scripts/reset_analytics.py --yes        # analitikani 0 ga tushiradi (katalog/buyurtma/mijoz saqlanadi)
python scripts/seed_demo.py --with-history     # faqat taqdimot uchun: 30 kunlik SINTETIK analitika
python scripts/seed_demo.py --reset            # demo do'konni butunlay qaytadan yaratish
python -m app.workers.run                      # worker'ni alohida jarayonda (production)
python -m pytest -q                            # testlar
npx next build                                 # dashboard/storefront production build
```

**Muammolar:**

| Belgi | Sabab va yechim |
|---|---|
| Mahsulot rasmlari ko'rinmaydi | API (8000) ishlamayapti yoki `PUBLIC_API_URL` boshqa hostga qaragan. Rasmlar `/media/...` nisbiy yo'l bilan saqlanadi, storefront ularni o'z domeni orqali proxy qiladi. Eski demo rasmlar uchun `seed_demo.py` ni qayta ishga tushiring |
| Storefront "Do'kon kaliti sozlanmagan" | `apps/storefront/.env.local` da `NEXT_PUBLIC_STORE_KEY` yo'q → `seed_demo.py` ni ishga tushiring yoki Integratsiya sahifasidan kalitni yozing, so'ng storefront'ni qayta ishga tushiring |
| Rasm qidiruvi 503 | Barcha Gemini modellari "sovigan" (404/429/timeout). Dashboard → AI modellar sahifasida holatni ko'ring, ishlaydigan modelni yuqori prioritetga qo'ying |
| `alembic upgrade` "boshqa tuzilmadagi jadvallar" | Bazada eski loyiha jadvallari bor — [apps/api/README.md](apps/api/README.md) → "Eski jadvallar" |
| Dashboard raqamlari 0 | To'g'ri: soxta ma'lumot yo'q. Vidjet yoki storefront orqali qidiruv/xarid qiling — raqamlar real vaqtda paydo bo'ladi |

---

## 21. Production deploy

**Minimal topologiya (boshlash uchun, 1–2 server):**

```
Cloudflare (DNS, CDN, WAF)
   ├── cdn.vision.uz   → statik: loader.js, widget.[hash].js (R2/S3 + CDN)
   ├── api.vision.uz   → Nginx → api (N replika)
   ├── app.vision.uz   → dashboard
   └── shop.vision.uz  → storefront (Premium)
Server: api ×2, worker ×1–2, dashboard, storefront, Redis
Managed PostgreSQL (pgvector) + avtomatik backup (PITR)
```

**Deploy tartibi (har release):**
1. CI: lint, type-check, testlar, image build + skan → registry.
2. Staging'ga deploy → smoke test (`/readyz`, test qidiruv, test hodisa).
3. DB backup → `alembic upgrade head` (faqat backward-compatible migratsiyalar).
4. Production: rolling update (bitta-bitta replika, `readyz` o'tgach keyingisi).
5. Widget: avval 1% tenant (kanary) → 10% → 100%; xato ko'rsatkichi oshsa avtomatik rollback.
6. Release'dan keyin 30 daq alertlarni kuzatish.

**Rollback:** oldingi image tegi + (kerak bo'lsa) migratsiyani `downgrade`; widget uchun oldingi `loader.js` versiyasiga qaytarish. `infra/scripts/rollback.sh` bir buyruq.

**Docker (api) tavsiyalari:** non-root foydalanuvchi, multi-stage build, `uvicorn --workers N` (yoki gunicorn+uvicorn), healthcheck, resurs limitlari.

---

## 22. Test va CI/CD

| Daraja | Nima tekshiriladi |
|---|---|
| **Unit** | scoring, demand_key normalizatsiya, HMAC, atribusiya, abandoned logika, pul hisobi |
| **Integration** | API + haqiqiy Postgres/Redis (testcontainers), **RLS tenant izolyatsiyasi** (A tenant B ni ko'ra olmaydi) |
| **Contract** | Gemini javob sxemasi (mock), katalog feed/proxy shartnomasi, webhook payloadlari (Woo/Shopify/OpenCart namunalari) |
| **E2E (Playwright)** | Vidjet haqiqiy sahifalarda: WooCommerce, Shopify, OpenCart, Next.js, oddiy HTML (shu jumladan CSP bilan) |
| **Yuk testi** | k6: 50 RPS qidiruv, Gemini mock bilan; p95 va xato foizi |
| **Xavfsizlik** | `bandit`, `pip-audit`, `npm audit`, Trivy, OWASP ZAP (staging) |

**GitHub Actions:** `ci.yml` (PR'da: lint → test → build), `deploy.yml` (main → staging → qo'lda tasdiq → prod), `widget-release.yml` (build → CDN → kanary).

---

## 23. Monitoring, zaxira nusxa, masshtablash

**Metrikalar (Prometheus) va alertlar:**

| Metrika | Alert sharti |
|---|---|
| API 5xx foizi | > 1% (5 daq) |
| `visual-search` p95 | > 6 s |
| Gemini xato foizi / barcha modellar sovigan | > 10% / darhol |
| Navbat (queue) uzunligi / eng eski job yoshi | o'sib borsa |
| Webhook muvaffaqiyatsiz yetkazish | > 5% |
| Katalog sinxroni muvaffaqiyatsiz (tenant bo'yicha) | 2 marta ketma-ket |
| Tenantdan hodisa kelmayapti | 24 soat |
| DB ulanishlari, disk, replika kechikishi | chegaradan oshsa |

- **Loglar:** JSON, `request_id`, `tenant_id` bilan (PII va rasm yo'q) → Loki.
- **Backup:** kunlik to'liq + PITR (WAL), 30 kun saqlash, **oyiga bir marta restore sinovi**.
- **Masshtablash:** API stateless → gorizontal; qidiruv ko'p bo'lsa AI chaqiruvlari alohida navbat/semafor; DB: read replica (dashboard so'rovlari uchun), `events` partitsiya; pgvector HNSW indeksi.
- **Xarajat nazorati:** tenant bo'yicha kunlik AI kvota, kesh hit-rate ko'rsatkichi, `AI_DAILY_BUDGET_USD`.

---

## 24. 0 dan production gacha yo'l xaritasi

| Bosqich | Muddat* | Natija | Tayyorlik mezoni |
|---|---|---|---|
| **0. Poydevor** | 1 hafta | Monorepo, Docker, CI, Alembic, config validatsiyasi, logging | `make dev` bilan hamma narsa ko'tariladi, CI yashil |
| **1. Multi-tenant + Auth + Rollar** | 1–2 hafta | `tenants`, `users`, `memberships`, `api_keys`, RLS, login, taklif | RLS izolyatsiya testi o'tadi |
| **2. Vision Core** | 2 hafta | Gemini client, router + breaker, kesh, strukturali JSON, rasm validatsiyasi | 50 ta test rasm bo'yicha barqaror natija, fallback ishlaydi |
| **3. Katalog + Matching** | 2 hafta | Feed/CSV/push, embedding, pgvector, scoring, unmet demand | Namunaviy katalogda relevantlik qo'lda baholanadi (≥80% to'g'ri top-3) |
| **4. Vidjet** | 2 hafta | Loader, Shadow DOM, auto-detect, kamera/upload, nol-sozlama savat | 5 xil platformada Playwright testlari o'tadi |
| **5. Hodisalar + Atribusiya** | 1–2 hafta | `events`, idempotentlik, `search_id`, identify, `sendBeacon`, oflayn navbat | Sinov oqimida konversiya qo'lda hisoblangan bilan teng |
| **6. Analitika + Dashboard** | 2 hafta | Voronka, demand, abandoned job, agregatlar, sahifalar | Formulalar (13-b) testlar bilan tasdiqlangan |
| **7. Platforma plaginlari + webhook** | 2–3 hafta | WooCommerce → Shopify → OpenCart, HMAC webhook, `vd_sid` meta | Haqiqiy test do'konda buyurtma → analitikada paydo bo'ladi |
| **8. Production tayyorlik** | 1–2 hafta | Monitoring, alert, backup/restore, yuk testi, xavfsizlik auditi, hujjatlar | 25-bo'lim checklist to'liq |
| **🚀 MVP (Oddiy tarif sotuvga)** | **≈ 3 oy** | 0–8 bosqichlar | 2–3 pilot mijoz bilan 2 hafta beta |
| **9. Premium Storefront + Admin** | 4–6 hafta | Katalog, savat, buyurtma, admin, hosted katalog | Premium pilot do'kon |
| **10. Keyingi** | — | Payme/Click, proxy rejimi, A/B, promo-kod tavsiyalari, Rus/Ingliz tillari | — |

\* Muddatlar 2–3 kishilik jamoa uchun taxminiy.

---

## 25. Ishga tushirishdan oldingi checklist

**Xavfsizlik**
- [ ] `.env` va kalitlar git'da yo'q; secrets manager ishlatilgan
- [ ] `/docs` production'da yopiq; `/metrics` faqat ichki tarmoqda
- [ ] RLS yoqilgan va izolyatsiya testi o'tgan
- [ ] Rate limit, Origin allowlist, hajm limiti ishlayapti
- [ ] 2FA `super_admin` uchun majburiy
- [ ] Dependency va image skanerlari yashil

**Ishonchlilik**
- [ ] `/readyz`, healthcheck, avto-restart sozlangan
- [ ] Gemini barcha modellari sovigan holatda ham tizim yiqilmaydi (503 + xabar)
- [ ] Redis o'chganda qidiruv ishlashda davom etadi
- [ ] Webhook retry va DLQ sinalgan; takror hodisa ikki marta sanalmaydi
- [ ] Backup'dan restore sinab ko'rilgan
- [ ] Rollback `rollback.sh` bilan sinalgan

**Integratsiya**
- [ ] `<script>` tegi 5 platformada (Woo, Shopify, OpenCart, Next.js, HTML) sinalgan, CSP bilan ham
- [ ] Vidjet API o'chiq bo'lsa sayt buzilmaydi (jim yashirinadi)
- [ ] Plagin buyurtmani bloklamasligi tasdiqlangan
- [ ] Integrations sahifasidagi "Install check" ishlaydi

**Maxfiylik va huquqiy**
- [ ] Rasm saqlanmaydi; IP maskalanadi; PII validatsiyasi ishlaydi
- [ ] Consent mexanizmi va maxfiylik siyosati matni tayyor
- [ ] Ma'lumotni o'chirish (`DELETE customers/{ref}`) ishlaydi
- [ ] Gemini pullik kalit va shartlari tekshirilgan

**Biznes**
- [ ] Tarif cheklovlari (feature flag) Oddiy/Premium bo'yicha tekshirilgan
- [ ] Kunlik AI byudjet limiti va ogohlantirish yoqilgan
- [ ] Mijoz uchun integratsiya qo'llanmasi (docs) va qo'llab-quvvatlash kanali tayyor

---

## 26. v2.1 yangilanishlar (o'zgarishlar jurnali)

**2026-10-17**

| Bo'lim | O'zgarish |
|---|---|
| Ma'lumotlar | Analitikadagi sintetik (soxta) ma'lumot olib tashlandi: `seed_demo.py` endi faqat katalog yaratadi; tozalash uchun `scripts/reset_analytics.py --yes`. Sintetik tarix faqat `--with-history` bilan |
| Rasmlar | Mahsulot rasmlari `/media/<tenant>/...` da saqlanadi (DB'da nisbiy yo'l) — host o'zgarsa ham buzilmaydi. Dashboard'dan rasm yuklash (EXIF o'chiriladi, 1600px), **AI bilan avtomatik to'ldirish** (kategoriya/rang/tur) |
| Storefront | Alohida Next.js ilova `apps/storefront` (:3001): bosh sahifa, katalog + filtrlar, mahsulot sahifasi, savat, checkout, to'lov, buyurtma kuzatuvi, xaridor hisobi, rasm qidiruvi sahifasi |
| Tranzaksiyalar | Server tomonda narx qayta hisoblash, `SELECT … FOR UPDATE` bilan zaxirani band qilish, idempotent checkout, `payments` jadvali, test to'lov shlyuzi (Luhn), bekor qilishda zaxirani qaytarish |
| Aksiyalar | `compare_at_minor` (eski narx), chegirma foizi, "Aksiyalar" bo'limi, zaxira soni, sotilganlar soni |
| Savdo (dashboard) | **Buyurtmalar** (holatlar: yangi → tasdiqlandi → yo'lda → yetkazildi / bekor), **Mijozlar** |
| Marketing | **Auditoriya** (qiziqish profillari, segmentlar), **Kampaniyalar** (sayt banneri, sotuvchi webhook'i, eksport), shaxsiy tavsiyalar `<div data-vd-recs>` |
| Eksport | **Barcha ma'lumotlar bitta Excel (.xlsx) faylda** — 12 ta varaq (Overview, Voronka, Buyurtmalar sahifalaridagi "Excel" tugmasi) |
| Integratsiya | WooCommerce plagini, oddiy PHP snippet, "boshqa platforma" test sayti, integratsiya qo'llanmasi (29-bo'lim) |
| AI router | O'chirilgan model (404) 24 soatga chetlatiladi, umumiy kutish chegarasi, `AI_TIMEOUT_SECONDS=15` |

---

## 27. Savdo do'koni va rasm qidiruvi: nima qayerda (ajratilish)

Ha — **uchta qatlam alohida**: savdo do'koni sahifalari, rasm qidiruvi va analitika. Ular bir-biriga faqat API va hodisalar orqali bog'langan.

```
┌───────────── apps/storefront (:3001) ─────────────┐   ┌──── istalgan boshqa sayt ────┐
│ /  /catalog  /product/[id]  /cart  /checkout       │   │ WooCommerce / HTML / Laravel │
│ /pay/[n]  /order/[n]  /account  /image-search      │   │  + 1 teg: loader.js (vidjet) │
└──────────┬──────────────────────────┬──────────────┘   └──────────────┬───────────────┘
           │ /v1/storefront/*          │ /v1/public/visual-search        │ /v1/public/*
           ▼                           ▼                                  ▼
   SAVDO jadvallari            QIDIRUV jadvallari                 ANALITIKA jadvallari
   customers, carts,           visual_searches,                   events, cart_sessions,
   cart_items, orders,         catalog_products (umumiy katalog)  sessions, identity_links,
   order_items, payments                                          customer_profiles, campaigns,
                                                                  daily_stats, unmet_demand_clusters
```

| Qism | Sahifa | API | Jadvallar |
|---|---|---|---|
| **Savdo do'koni** (Premium) | `apps/storefront` | `/v1/storefront/*` | `customers`, `carts`, `cart_items`, `orders`, `order_items`, `payments` |
| **Rasm qidiruvi** | storefront `/image-search` + sarlavhadagi kamera; boshqa saytlarda vidjet | `/v1/public/visual-search` | `visual_searches` (+ o'qish: `catalog_products`) |
| **Katalog** (umumiy) | dashboard → Katalog | `/v1/dashboard/catalog/*`, `/v1/server/catalog/push` | `catalog_products`, `catalog_sync_runs` |
| **Analitika** | dashboard | `/v1/dashboard/analytics/*` | `events`, `cart_sessions`, `sessions`, `identity_links`, `daily_stats`, `unmet_demand_clusters` |
| **Marketing** | dashboard → Auditoriya, Kampaniyalar | `/v1/dashboard/audiences*`, `/campaigns*` | `customer_profiles`, `campaigns` |

Muhim nuqtalar:

- Storefront o'z savatini `carts` da yuritadi. Analitikaga esa boshqa saytlar kabi oddiy hodisa yuboradi (`source='storefront'`). Shu sababli Oddiy va Premium tarif uchun bitta analitika quvuri ishlaydi.
- Analitikadagi `cart_sessions` — tashlab ketilgan savatni hisoblash uchun. Do'kon savati (`carts`) bilan aralashmaydi.
- Storefront'da xaridorning ismi va telefoni `customers`/`orders` da saqlanadi (do'kon o'zimizda). Analitikaga esa faqat `customer_ref = c_<id>` uzatiladi.

---

## 28. Auditoriya va target reklama (neytral `customer_ref` bilan)

**Savol:** biz xaridorni faqat `customer_ref` (masalan `u_1842`) orqali bilsak, unga qiziqishiga mos reklamani qanday yuboramiz?

**Javob:** biz kontaktni bilmaymiz va bilishimiz shart emas. Biz **kimga va nima** yuborishni hisoblaymiz: segment, qiziqish va tavsiya mahsulotlar. **Yuborishni** esa kontaktga ega bo'lgan sotuvchi qiladi. Anonim mehmonlarga saytning o'zida ko'rsatamiz.

### 28.1 Profil qanday quriladi

Worker har 15 daqiqada `customer_profiles` ni qayta hisoblaydi (dashboard → Auditoriya → "Qayta hisoblash" ham bor):

| Signal | Og'irlik |
|---|---|
| Rasm qidiruvi (AI aniqlagan kategoriya/rang/tur) | 1 |
| Mahsulotni bosish | 2 |
| Savatga qo'shish | 3 |
| Xarid | 4 |

Signallar 30 kunlik yarim yemirilish bilan so'nadi: eski qiziqish asta-sekin pasayadi. Profil kaliti `customer_ref` bo'ladi, identify qilinmagan mehmon uchun esa `s:<vd_sid>`.

**Avtomatik segmentlar:** `interest:<kategoriya>`, `type:<tur>`, `color:<rang>`, `abandoned_cart`, `buyer`, `repeat_buyer`, `high_value` (top 20%), `browser` (ko'rib ketgan), `unmet_demand`, `unmet:<talab>`, `identified`.

### 28.2 Yetkazish kanallari

| Kanal | Kimga | Qanday |
|---|---|---|
| **Sotuvchi webhook'i** | tanilgan xaridorlar (`customer_ref`) | Kampaniya `POST <marketing_webhook_url>` ga yuboriladi. Ichida `recipients: [{customer_ref, top_interests, products[]}]` bor, HMAC bilan imzolangan. Sotuvchi o'z bazasidan `customer_ref → telefon/e-mail/Telegram` ni topib, xabarni o'zi yuboradi (namuna: `integrations/generic-php/vision_detect.php` → `vd_receive_campaign()`) |
| **Saytdagi shaxsiy blok** | hamma, **anonimlar ham** | Saytga `<div data-vd-recs data-title="Siz uchun"></div>` qo'yiladi. Vidjet uni `GET /v1/public/recommendations` bilan shu sessiya qiziqishiga mos mahsulotlar va faol kampaniya banneri bilan to'ldiradi. Storefront bosh sahifasidagi "Siz uchun" bloki ham shu |
| **Eksport** | segment | CSV yoki Excel faylni CRM, SMS-xizmat yoki reklama kabinetiga (Custom Audience) yuklash. Premium'da `marketing_consent=true` mijozlar kontakti bilan |
| **Pull API** | sotuvchi serveri | `GET /v1/server/audiences?segment=interest:poyabzal` va `GET /v1/server/profiles/{customer_ref}` (secret key bilan) |

**Misol:** `u_1842` 3 marta qizil krossovka qidirdi va savatni tashlab ketdi. U `interest:poyabzal`, `type:krossovka`, `abandoned_cart` segmentlariga tushadi. "Krossovka −10%" kampaniyasi uni sotuvchiga `products: [Qizil sport krossovka Runner …?vd_c=…]` bilan yuboradi. Sotuvchi unga SMS jo'natadi. Havola orqali qaytsa, xarid shu kampaniya va qidiruvga atribusiya qilinadi.

**Maxfiylik:** PII bizga kelmaydi. Kampaniya webhook'i faqat sotuvchining o'z serveriga boradi. Consent `false` bo'lsa `identify` e'tiborga olinmaydi.

---

## 29. Boshqa platformaga ulash (test qo'llanmasi)

Ha, tizim boshqa saytga o'rnatib sinashga tayyor. Har qanday sayt uchun minimal ulanish — **bitta teg**:

```html
<script src="http://127.0.0.1:8000/cdn/v1/loader.js" data-key="pk_live_…" async></script>
```

Kalit: dashboard → **Integratsiya** → "Vidjetni o'rnatish" (tayyor teg nusxalanadi).

### 29.1 Shu kompyuterdagi boshqa sayt (eng tez test, 2 daqiqa)

```bash
cd integrations/examples/test-shop
python -m http.server 5500          # http://localhost:5500
```

Sahifada API manzili va public key'ni kiriting → **Saqlash**. Qidiruv maydoni yonida 📷 tugma paydo bo'ladi. Rasm yuklang, so'ng dashboard → **Qidiruvlar jurnali** va **Integratsiya → O'rnatish holati** ni tekshiring.

### 29.2 WordPress + WooCommerce (lokal: LocalWP yoki XAMPP)

1. `integrations/woocommerce/vision-detect/` papkasini `wp-content/plugins/` ga nusxalang. **Plaginlar → Vision Detect → Faollashtirish**.
2. **Sozlamalar → Vision Detect** sahifasida: API manzili, Public key, Webhook secret (Integratsiya → "Webhook maxfiy kalitini ko'rsatish").
3. Plagin sozlamalar sahifasidagi feed URL'ni (`/wp-json/vision-detect/v1/feed`) dashboard → Katalog → Feed manbasi (JSON) maydoniga kiriting → **Hozir sinxronlash**.
4. Do'konda xarid qiling. Buyurtma HMAC webhook bilan keladi, Buyurtma Analitika → Voronka va Integratsiya → "Buyurtma webhook'i" ✓ da ko'rinadi.
5. Dashboard → Sozlamalar/Integratsiya: platforma = WooCommerce. Shunda vidjetdagi "Savatga" tugmasi `?add-to-cart=ID` orqali ishlaydi.

### 29.3 Shopify, OpenCart, Laravel, Next.js, oddiy HTML

| Platforma | Teg qayerga | Buyurtmalar |
|---|---|---|
| Shopify | Online Store → Themes → Edit code → `theme.liquid`, `</body>` oldiga | Settings → Notifications → Webhooks → Order creation → `…/v1/server/webhooks/shopify?key=pk_…` |
| OpenCart | `catalog/view/theme/*/template/common/footer.twig` | `…/webhooks/opencart?key=pk_…` |
| Laravel / PHP | asosiy Blade layout | `integrations/generic-php/vision_detect.php` → `vd_send_purchase()` |
| Next.js | `app/layout.tsx` → `<Script src=… data-key=… strategy="afterInteractive"/>` | backend'dan `POST /v1/server/events` |
| Oddiy HTML | har sahifada `</body>` oldiga | "rahmat" sahifasi URL shablonini Sozlamalarga kiriting (zaxira PURCHASE) |

### 29.4 Internetdagi (boshqa kompyuterdagi) saytdan test

Real sayt HTTPS'da bo'ladi, `127.0.0.1` ga murojaat qila olmaydi. Shuning uchun API'ni vaqtincha tunnel orqali oching:

```bash
cloudflared tunnel --url http://127.0.0.1:8000      # yoki: ngrok http 8000
# chiqqan https://xxxx.trycloudflare.com manzilini:
#   .env → PUBLIC_API_URL=https://xxxx.trycloudflare.com   (API'ni qayta ishga tushiring)
#   tegda: <script src="https://xxxx.trycloudflare.com/cdn/v1/loader.js" data-key="pk_live_…" async></script>
```

So'ng dashboard → Integratsiya → **Ruxsat etilgan domenlar** ga saytingiz domenini (`https://shop.uz`) qo'shing.

### 29.5 Ulanish to'g'riligini tekshirish

| Tekshiruv | Qayerda |
|---|---|
| Vidjet signal yubordimi | Integratsiya → O'rnatish holati → "Vidjet saytda o'rnatilgan" ✓ |
| Domen ruxsat etilganmi | 403 `ORIGIN_NOT_ALLOWED` bo'lsa — allowlist'ga qo'shing |
| Webhook imzosi to'g'rimi | Integratsiya → "Ulanishni tekshirish" (imzo namunasi bilan solishtiring) |
| Katalog sinxroni | Katalog → Sinxron tarixi |
| CSP | Saytda CSP bo'lsa: `script-src <API>; connect-src <API>; img-src * data:` |

---

## 30. Excel eksport

Dashboard'dagi **Excel yuklab olish** tugmasi (Umumiy ko'rinish, Voronka, Rang va kategoriya, Buyurtmalar) tanlangan sana oralig'i bo'yicha bitta `.xlsx` fayl beradi. Endpoint: `GET /v1/dashboard/analytics/export.xlsx?from=&to=`. Fayl ichida 12 ta varaq:

`Umumiy` · `Kunlik dinamika` · `Voronka` · `Qondirilmagan talab` · `Tashlangan savat - mahsulot` · `Tashlangan savatlar` · `Qidiruvlar` · `Rang va kategoriya` · `Auditoriya segmentlari` · `Xaridor profillari` · `Buyurtmalar` (Premium) · `Mahsulotlar`

Pul ustunlari so'mda (butun son `*_minor / 100`), vaqtlar UTC'da. Har eksport `audit_logs` ga yoziladi. Alohida CSV eksportlar ham saqlanib qolgan: talab, savatlar, qidiruvlar, auditoriya.

---

## 31. API qo'shimchalari (v2.1)

| Guruh | Endpoint | Auth |
|---|---|---|
| Storefront | `GET /v1/storefront/info · /products · /products/{id}` | public key (faqat Premium, aks holda 402 `PLAN_REQUIRED`) |
| | `GET/POST/PUT /v1/storefront/cart · /cart/items` | public key (+ xaridor tokeni) |
| | `POST /v1/storefront/checkout` (idempotency_key) | public key |
| | `GET /v1/storefront/orders/{number}?t=` · `POST …/pay` · `POST …/cancel` | buyurtma tokeni yoki xaridor |
| | `POST /v1/storefront/auth/register · /auth/login`, `GET/PATCH /me` | public key / xaridor JWT |
| Public | `GET /v1/public/recommendations?session_id=` · `POST /v1/public/campaign-event` | public key |
| Dashboard | `GET /v1/dashboard/orders · /orders/{id}`, `PATCH /orders/{id}` (holat) | JWT + rol (Premium) |
| | `GET /v1/dashboard/customers?q=&ref=` (ikkala tarif) · `GET/PATCH /catalog/products/{id}` | JWT + rol |
| | `POST /v1/dashboard/catalog/images?analyze=true` (rasm yuklash + AI) | catalog_manager |
| | `GET /audiences · /audiences/profiles · /audiences/export`, `POST /audiences/rebuild` | analyst |
| | `GET/POST /campaigns`, `POST /campaigns/{id}/send · /stop`, `DELETE`, `PUT /campaigns-settings` | admin |
| | `GET /v1/dashboard/analytics/export.xlsx` | analyst |
| Server | `GET /v1/server/audiences?segment=` · `GET /v1/server/profiles/{customer_ref}` | secret key |

---

## 32. Tariflar amalda: Oddiy va Premium

Tarifni platforma administratori o'zgartiradi (Dashboard → Platforma → Do'konlar → "Tarif" ustuni). Katalog rejimi tarif bilan birga avtomatik almashadi: Premium → `hosted`, Oddiy → `feed`.

| Imkoniyat | 🟢 Oddiy | 🟣 Premium |
|---|:---:|:---:|
| Rasm orqali qidiruv, analitika, Excel | ✅ | ✅ |
| Auditoriya, kampaniyalar, shaxsiy takliflar | ✅ | ✅ |
| **Mijozlar** — `customer_ref` ro'yxati, qiziqish va faollik | ✅ (kontaktsiz) | ✅ + ism, telefon, e-mail |
| Katalog: feed / CSV (sotuvchi saytidan) | ✅ | — |
| Integratsiya (vidjet tegi, webhook) | ✅ | — (kerak emas) |
| Tayyor onlayn do'kon (`apps/storefront`) | — ("Do'kon vaqtincha yopiq") | ✅ |
| **Mahsulotlar** bo'limi: qo'shish, rasmlar (8 tagacha, AI to'ldiradi), aksiya narxi, ombor | — | ✅ |
| Buyurtmalar, to'lov, yetkazib berish | — | ✅ |
| Kampaniya kanallari | sayt banneri, "Mening tizimimga", ro'yxat | do'kondagi banner, SMS/e-mail ro'yxati (roziligi borlar) |

Dashboard menyusi va sahifalari tarifga qarab o'zgaradi. Premium'da dasturchiga oid bo'limlar (vidjet tegi, webhook, payload) ko'rsatilmaydi. Oddiy tarifda Sozlamalar → "Tarifingiz" kartasida farqlar ko'rinadi.

---

## 33. v2.2 yangilanishlar (2026-10-17)

| Bo'lim | O'zgarish |
|---|---|
| Rasmlar | Dashboard va storefront rasmlarni o'z domeni orqali (`/media` proxy) oladi |
| Storefront | Tarif oddiy bo'lsa yoki server ishlamasa, bo'sh sahifa o'rniga "Do'kon vaqtincha yopiq" yoki "vaqtincha ishlamayapti" chiqadi |
| Premium | Yangi **Mahsulotlar** bo'limi (`/products`): ro'yxat, ombor sonini tezkor tahrirlash, to'liq forma (`/products/new`, `/products/{id}`) — galereya, AI bilan to'ldirish, aksiya, jonli ko'rinish |
| Mijozlar | Ikkala tarifda ishlaydi. `customer_ref` manbalari: identify, server hodisalari, profillar va (Premium) do'kon xaridorlari. `?ref=c_…` havolasi aniq xaridorni ochadi |
| Login | Chiqqandan keyin boshqa foydalanuvchi kirsa, oldingi sahifaga (masalan `/admin/audit`) yo'naltirilmaydi. `next` faqat ruxsat etilgan sahifa bo'lsa ishlatiladi |
| Interfeys | Kampaniyalardagi "payload" qo'llanmasi olib tashlandi. Matnlar texnik atamalarsiz. Tarifga mos kanallar va sozlamalar |
| Excel | Har varaqda sarlavha, do'kon va davr. Joriy va oldingi davr yonma-yon. Pul, foiz, sana va ms formatlari, chegaralar, filtr va muzlatilgan sarlavha. "Soatlik faollik" alohida varaqda |

---

## 34. Basic edition — faqat Oddiy tarif, alohida loyiha (2026-10-17)

Savdo-sotiq platformasisiz ishlatish uchun loyihaning yengil nusxasi yasaladi:

```bash
python tools/make_basic_edition.py D:\Projectsision-detect-basic
```

| | To'liq | Basic edition |
|---|---|---|
| Ishlaydigan jarayonlar | API + Dashboard (Node) + Storefront (Node) | **faqat API** (dashboard statik, nginx beradi) |
| RAM | ~1.2–1.6 GB | ~0.6–0.8 GB |
| Domen / SSL | 2 | 1 |
| AI (Gemini) xarajati | qidiruvlar soniga bog'liq | **o'zgarmaydi** — kesh va kunlik limit bilan boshqariladi |

- `EDITION=basic` (`.env`) bo'lsa, storefront API yuklanmaydi va do'konlarni Premium'ga o'tkazib bo'lmaydi.
- Dashboard `STATIC_EXPORT=1` bilan `out/` papkaga statik fayl sifatida yig'iladi (~2 MB).
- Deploy fayllari: `infra/basic/` (`nginx.conf`, `vision-api.service`, `backup.sh`).
- Batafsil qo'llanma nusxaning `README.md` faylida: kompyuterda ishga tushirish, VPS'ga joylash, istalgan platformaga ulash.

**Demo rasmlar:** demo mahsulotlar endi `.jpg` (800×800). Manba: `apps/api/app/demo/products/*.jpg`. Eski bazadagi `.svg` havolalar `python scripts/demo_images_to_jpg.py` bilan almashtiriladi.

---

## Litsenziya

MIT License. © Vision Detect team.
