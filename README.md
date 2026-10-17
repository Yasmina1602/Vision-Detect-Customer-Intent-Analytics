# Vision Detect — Basic edition (Oddiy tarif)

Istalgan saytga **bitta `<script>` tegi** bilan ulanadigan rasm orqali qidiruv va xaridor talablari analitikasi.
Savdo-sotiq platformasi (storefront, buyurtma, to'lov) **yo'q** — mahsulotlar va savdo sotuvchining o'z saytida qoladi.

To'liq arxitektura va spetsifikatsiya: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tarkibi

| Bor | Yo'q (faqat to'liq versiyada) |
|---|---|
| API (FastAPI) + fon vazifalari, MySQL | Storefront (Next.js do'kon ilovasi) |
| Dashboard: analitika, qondirilmagan talab, savatlar, auditoriya, kampaniyalar, mijozlar (`customer_ref`), Excel | Mahsulot qo'shish, buyurtmalar, to'lov, ombor |
| Vidjet (`loader.js`, `widget.js`), WooCommerce plagini, PHP snippet, test sayt | Premium tarif |
| Katalog: feed (JSON/CSV/XML) yoki CSV yuklash | |

## Nima tejaladi

| Komponent | To'liq versiya | Basic edition |
|---|---|---|
| Jarayonlar | API + Dashboard (Node) + Storefront (Node) | **API** (dashboard — nginx beradigan statik fayllar) |
| RAM (taxminan) | ~1.2–1.6 GB | **~0.6–0.8 GB** (API ~200 MB + MySQL ~400 MB) |
| Server | 2 vCPU / 4 GB | **1 vCPU / 1–2 GB** VPS boshlash uchun yetarli |
| Domen / SSL | 2 ta (dashboard + do'kon) | **1 ta** |
| Rasm saqlash | yuklangan mahsulot rasmlari | yo'q (rasmlar sotuvchi saytidan) |
| Qo'llab-quvvatlash | to'lov, buyurtma, zaxira, xaridor hisoblari | yo'q |

**O'zgarmaydigan xarajat — AI (Gemini):** har bir rasm qidiruvi bitta so'rov. Uni kamaytirish uchun:
- bir xil rasm qayta tahlil qilinmaydi (kesh, 7 kun);
- Sozlamalardagi kunlik qidiruv limiti (`daily_search_quota`);
- `.env` dagi arzonroq modelni (`flash-lite`) birinchi prioritetga qo'ying;
- narxlarni Google AI Studio sahifasida tekshiring.

---

## 1. Kompyuterda ishga tushirish (Windows)

```powershell
copy .env.example .env          # DATABASE_URL, APP_SECRET_KEY, GEMINI_API_KEY ni to'ldiring
cd apps\api
py -3.11 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python scripts\create_superadmin.py --email admin@sizning.uz --password <parol>
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# ikkinchi terminal
cd apps\dashboard
npm install
npm run dev                     # http://localhost:3000
```

Dashboard'da "Ro'yxatdan o'tish" orqali do'kon oching yoki admin → Do'konlar → "Do'kon yaratish".

---

## 2. Serverga joylash (Ubuntu 24.04 VPS, bitta domen)

```bash
# 2.1 Paketlar
sudo apt update && sudo apt install -y python3.12-venv nodejs npm mysql-server nginx certbot python3-certbot-nginx git
sudo useradd -m -s /bin/bash vision

# 2.2 Kod
sudo mkdir -p /opt/vision-basic && sudo chown vision /opt/vision-basic
sudo -u vision git clone <sizning-repo-manzilingiz> /opt/vision-basic
cd /opt/vision-basic

# 2.3 Baza
sudo mysql -e "CREATE DATABASE vision_basic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'vision'@'localhost' IDENTIFIED BY 'KUCHLI_PAROL';
  GRANT ALL ON vision_basic.* TO 'vision'@'localhost';"

# 2.4 .env (production)
cp .env.example .env && nano .env
#   APP_ENV=production
#   EDITION=basic
#   APP_SECRET_KEY=<python3 -c "import secrets;print(secrets.token_hex(48))">
#   PUBLIC_API_URL=https://vision.example.uz
#   DASHBOARD_URL=https://vision.example.uz
#   CORS_DASHBOARD_ORIGINS=https://vision.example.uz
#   DATABASE_URL=mysql://vision:KUCHLI_PAROL@127.0.0.1:3306/vision_basic
#   GEMINI_API_KEY=...

# 2.5 API
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head          # .env ni ilova o'zi o'qiydi
.venv/bin/python scripts/create_superadmin.py --email admin@sizning.uz
sudo cp ../../infra/basic/vision-api.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now vision-api

# 2.6 Dashboard (statik)
cd ../dashboard && npm ci && npm run build      # natija: apps/dashboard/out/

# 2.7 nginx + HTTPS
sudo cp ../../infra/basic/nginx.conf /etc/nginx/sites-available/vision      # server_name ni o'zgartiring
sudo ln -s /etc/nginx/sites-available/vision /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d vision.example.uz
```

Tekshirish: `https://vision.example.uz/readyz` → `{"status":"ok"}`, `https://vision.example.uz` → login sahifasi.

**Yangilash:**
```bash
git pull
cd apps/api && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m alembic upgrade head
sudo systemctl restart vision-api
cd ../dashboard && npm ci && npm run build
```

**Zaxira nusxa:** `infra/basic/backup.sh` (cron'ga qo'shing: `0 3 * * *`).

---

## 3. Istalgan platformaga ulash

Dashboard → **Integratsiya** sahifasida tayyor teg bor:

```html
<script src="https://vision.example.uz/cdn/v1/loader.js" data-key="pk_live_…" async></script>
```

| Platforma | 1. Teg | 2. Katalog | 3. Buyurtmalar (xarid statistikasi) |
|---|---|---|---|
| **WordPress / WooCommerce** | `integrations/woocommerce/vision-detect` plagini (teg o'zi qo'yiladi) | plagin feed URL'i → Dashboard → Katalog | plagin o'zi yuboradi |
| **Shopify** | `theme.liquid`, `</body>` oldiga | Shopify mahsulot eksporti (CSV) → Katalog → yuklash | Settings → Notifications → Webhooks → Order creation → `…/v1/server/webhooks/shopify?key=pk_…` |
| **OpenCart** | `footer.twig` | CSV eksport → yuklash | `…/webhooks/opencart?key=pk_…` |
| **Laravel / PHP** | asosiy layout | `POST /v1/server/catalog/push` yoki CSV | `integrations/generic-php/vision_detect.php` → `vd_send_purchase()` |
| **Tilda, Wix, oddiy HTML** | "HTML kod qo'shish" bloki / har sahifa `</body>` oldi | CSV yuklash | Sozlamalar → "Buyurtma tasdiqlanish sahifasi manzili" |
| **Next.js / React** | `<Script src=… data-key=… strategy="afterInteractive" />` | feed URL | backend'dan `POST /v1/server/events` |

Ulangandan keyin:
1. **Integratsiya → Ruxsat etilgan domenlar** ga saytingiz domenini (`https://shop.uz`) qo'shing.
2. **Integratsiya → O'rnatish holati** — vidjet, hodisalar, webhook va katalog ✓ bo'lishi kerak.
3. Saytda qidiruv maydoni yonida 📷 tugma chiqadi. Rasm yuklang va Dashboard → **Qidiruvlar jurnali** da ko'ring.
4. Shaxsiy tavsiyalar bloki (ixtiyoriy): sahifaga `<div data-vd-recs data-title="Siz uchun"></div>` qo'ying.

**Lokal test (server qilmasdan):**
```bash
cd integrations/examples/test-shop && python -m http.server 5500     # http://localhost:5500
```
Internetdagi saytdan sinash uchun API'ni vaqtincha ochish mumkin: `cloudflared tunnel --url http://127.0.0.1:8000`. Chiqqan manzilni `.env` dagi `PUBLIC_API_URL` va tegga yozasiz.
