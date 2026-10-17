/*!
 * Vision Detect widget v1 — Shadow DOM ichidagi modal (lazy yuklanadi).
 * Savatni boshqarmaydi: platforma adapteri orqali sotuvchining o'z mexanizmini chaqiradi.
 */
(function () {
  "use strict";
  var vd = window.__vd;
  if (!vd || vd.open) return;

  var cfg = vd.config || {};
  var lang = cfg.language || "uz";
  var primary = (cfg.theme && cfg.theme.primary) || "#6d28d9";

  var T = {
    uz: {
      title: "Rasm orqali qidirish", drop: "Rasmni shu yerga tashlang", or: "yoki",
      choose: "Fayl tanlash", camera: "Suratga olish", hint: "JPEG, PNG yoki WebP · 5MB gacha",
      analyzing: "Rasm tahlil qilinmoqda…", matching: "Mos mahsulotlar qidirilmoqda…",
      found: "Topilgan mahsulotlar", detected: "Aniqlandi", none: "O'xshash tovar topilmadi",
      noneSub: "Talabingiz do'konga yetkazildi. Quyida yaqin variantlar:", view: "Ko'rish", add: "Savatga",
      added: "Savatga qo'shildi", out: "Tugagan", again: "Boshqa rasm", close: "Yopish",
      err: "Xatolik yuz berdi. Qayta urinib ko'ring.", errAi: "Hozircha rasm tahlili mavjud emas.",
      errBig: "Rasm juda katta.", errType: "Faqat rasm fayllari qabul qilinadi.", errRate: "Juda ko'p urinish. Birozdan so'ng qayta urinib ko'ring.",
      privacy: "Rasm saqlanmaydi — faqat tahlil uchun ishlatiladi.", match: "moslik"
    },
    ru: {
      title: "Поиск по фото", drop: "Перетащите фото сюда", or: "или", choose: "Выбрать файл", camera: "Сделать фото",
      hint: "JPEG, PNG или WebP · до 5МБ", analyzing: "Анализируем фото…", matching: "Ищем похожие товары…",
      found: "Найденные товары", detected: "Распознано", none: "Похожих товаров не найдено",
      noneSub: "Ваш запрос передан магазину. Близкие варианты:", view: "Смотреть", add: "В корзину",
      added: "Добавлено в корзину", out: "Нет в наличии", again: "Другое фото", close: "Закрыть",
      err: "Произошла ошибка. Попробуйте снова.", errAi: "Анализ фото временно недоступен.",
      errBig: "Файл слишком большой.", errType: "Принимаются только изображения.", errRate: "Слишком много попыток.",
      privacy: "Фото не сохраняется — используется только для анализа.", match: "совпадение"
    },
    en: {
      title: "Search by image", drop: "Drop an image here", or: "or", choose: "Choose file", camera: "Take photo",
      hint: "JPEG, PNG or WebP · up to 5MB", analyzing: "Analyzing image…", matching: "Finding matching products…",
      found: "Matching products", detected: "Detected", none: "No similar products found",
      noneSub: "We've let the store know. Closest options:", view: "View", add: "Add to cart",
      added: "Added to cart", out: "Out of stock", again: "Try another", close: "Close",
      err: "Something went wrong. Please try again.", errAi: "Image analysis is temporarily unavailable.",
      errBig: "Image is too large.", errType: "Only image files are accepted.", errRate: "Too many attempts.",
      privacy: "Your photo is not stored — used only for analysis.", match: "match"
    }
  }[lang] || {};

  var CSS = "" +
    ":host{all:initial}" +
    "*{box-sizing:border-box;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Inter,sans-serif}" +
    ".ov{position:fixed;inset:0;z-index:2147483646;background:rgba(15,23,42,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:16px;animation:fade .18s ease}" +
    ".md{--p:" + primary + ";width:100%;max-width:760px;max-height:min(88vh,860px);background:#fff;color:#0f172a;border-radius:20px;box-shadow:0 24px 64px rgba(0,0,0,.28);display:flex;flex-direction:column;overflow:hidden;animation:pop .22s cubic-bezier(.2,.9,.3,1.2)}" +
    "@media(max-width:600px){.ov{align-items:flex-end;padding:0}.md{max-height:92vh;border-radius:20px 20px 0 0;animation:up .25s ease}}" +
    "@keyframes fade{from{opacity:0}}@keyframes pop{from{opacity:0;transform:scale(.96)}}@keyframes up{from{transform:translateY(40px);opacity:0}}" +
    ".hd{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #eef0f4}" +
    ".hd h2{margin:0;font-size:17px;font-weight:700;display:flex;align-items:center;gap:10px}" +
    ".dot{width:30px;height:30px;border-radius:9px;background:color-mix(in srgb,var(--p) 14%,#fff);color:var(--p);display:grid;place-items:center}" +
    ".x{all:unset;cursor:pointer;width:34px;height:34px;border-radius:10px;display:grid;place-items:center;color:#64748b}.x:hover{background:#f1f5f9;color:#0f172a}" +
    ".x:focus-visible,.btn:focus-visible,.card a:focus-visible{outline:2px solid var(--p);outline-offset:2px}" +
    ".bd{padding:20px;overflow:auto}" +
    ".dz{border:2px dashed #cbd5e1;border-radius:16px;padding:36px 20px;text-align:center;transition:.15s;background:#f8fafc}" +
    ".dz.on{border-color:var(--p);background:color-mix(in srgb,var(--p) 6%,#fff)}" +
    ".dz .ic{width:56px;height:56px;margin:0 auto 14px;border-radius:16px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.06);display:grid;place-items:center;color:var(--p)}" +
    ".dz b{display:block;font-size:16px;margin-bottom:6px}.dz small{color:#64748b;font-size:13px}" +
    ".row{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:16px 0 10px}" +
    ".btn{all:unset;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;height:42px;padding:0 18px;border-radius:12px;font-weight:600;font-size:14px;transition:.15s}" +
    ".pri{background:var(--p);color:#fff}.pri:hover{filter:brightness(1.08)}" +
    ".sec{background:#fff;color:#0f172a;border:1px solid #e2e8f0}.sec:hover{background:#f8fafc}" +
    ".sm{height:34px;padding:0 12px;font-size:13px;border-radius:10px}" +
    ".pv{display:flex;gap:16px;align-items:center;margin-bottom:18px}" +
    ".pv img{width:84px;height:84px;object-fit:cover;border-radius:14px;border:1px solid #e2e8f0;flex:none}" +
    ".chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}" +
    ".chip{font-size:12px;padding:4px 10px;border-radius:999px;background:#f1f5f9;color:#334155;font-weight:500}" +
    ".chip.p{background:color-mix(in srgb,var(--p) 12%,#fff);color:var(--p)}" +
    ".lbl{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#64748b;font-weight:600}" +
    ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}" +
    "@media(max-width:600px){.grid{grid-template-columns:repeat(2,1fr);gap:10px}}" +
    ".card{border:1px solid #eef0f4;border-radius:14px;overflow:hidden;display:flex;flex-direction:column;background:#fff;transition:.15s}" +
    ".card:hover{box-shadow:0 8px 24px rgba(15,23,42,.08);transform:translateY(-2px)}" +
    ".im{aspect-ratio:1;background:#f8fafc;position:relative}.im img{width:100%;height:100%;object-fit:cover;display:block}" +
    ".sc{position:absolute;top:8px;left:8px;font-size:11px;font-weight:700;background:rgba(255,255,255,.92);padding:3px 8px;border-radius:999px;color:#0f172a}" +
    ".oos{position:absolute;top:8px;right:8px;font-size:11px;font-weight:600;background:#fee2e2;color:#b91c1c;padding:3px 8px;border-radius:999px}" +
    ".ci{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;flex:1}" +
    ".nm{font-size:13px;font-weight:600;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;color:#0f172a;text-decoration:none}" +
    ".pr{font-size:15px;font-weight:800}" +
    ".ac{display:flex;gap:6px;margin-top:auto}.ac .btn{flex:1}" +
    ".sk{border-radius:14px;background:linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 37%,#f1f5f9 63%);background-size:400% 100%;animation:sh 1.2s infinite}" +
    "@keyframes sh{0%{background-position:100% 50%}100%{background-position:0 50%}}" +
    ".st{display:flex;align-items:center;gap:10px;font-size:14px;color:#334155;margin-bottom:16px}" +
    ".spin{width:18px;height:18px;border:2.5px solid #e2e8f0;border-top-color:var(--p);border-radius:50%;animation:rot .7s linear infinite}" +
    "@keyframes rot{to{transform:rotate(360deg)}}" +
    ".empty{text-align:center;padding:8px 0 18px}.empty b{display:block;font-size:16px;margin-bottom:4px}.empty p{margin:0;color:#64748b;font-size:14px}" +
    ".err{background:#fef2f2;color:#b91c1c;border-radius:12px;padding:12px 14px;font-size:14px;margin-bottom:14px}" +
    ".ft{padding:12px 20px;border-top:1px solid #eef0f4;font-size:12px;color:#94a3b8;display:flex;align-items:center;gap:6px}" +
    ".toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#0f172a;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:2147483647;animation:fade .2s}" +
    ".sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}";

  var I = {
    cam: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3.5"/></svg>',
    up: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>',
    x: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    lock: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>'
  };

  var host, root, overlay, body, lastFocus, state = { busy: false };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function money(minor, cur) {
    if (minor == null) return "";
    var v = minor / 100;
    try { return new Intl.NumberFormat(lang === "en" ? "en-US" : lang === "ru" ? "ru-RU" : "uz-UZ", { maximumFractionDigits: 0 }).format(v) + " " + (cur === "UZS" ? (lang === "ru" ? "сум" : "so'm") : cur || ""); }
    catch (e) { return v + " " + (cur || ""); }
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }

  function build() {
    host = document.createElement("div");
    host.setAttribute("data-vd", "modal");
    root = host.attachShadow({ mode: "open" });
    root.innerHTML = "<style>" + CSS + "</style>" +
      "<div class='ov' part='overlay'><div class='md' role='dialog' aria-modal='true' aria-labelledby='vdt'>" +
      "<div class='hd'><h2 id='vdt'><span class='dot'>" + I.cam + "</span>" + esc(T.title) + "</h2>" +
      "<button class='x' aria-label='" + esc(T.close) + "'>" + I.x + "</button></div>" +
      "<div class='bd' aria-live='polite'></div>" +
      "<div class='ft'>" + I.lock + esc(T.privacy) + "</div></div></div>";
    overlay = root.querySelector(".ov");
    body = root.querySelector(".bd");
    root.querySelector(".x").addEventListener("click", close);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && host.isConnected) close(); });
  }

  function open() {
    if (!host) build();
    lastFocus = document.activeElement;
    document.body.appendChild(host);
    document.documentElement.style.overflow = "hidden";
    renderPicker();
    setTimeout(function () { var b = root.querySelector(".btn.pri"); b && b.focus(); }, 50);
  }
  function close() {
    if (host && host.parentNode) host.parentNode.removeChild(host);
    document.documentElement.style.overflow = "";
    try { lastFocus && lastFocus.focus(); } catch (e) {}
  }

  function renderPicker(error) {
    var mobile = /Android|iPhone|iPad/i.test(navigator.userAgent);
    body.innerHTML = (error ? "<div class='err' role='alert'>" + esc(error) + "</div>" : "") +
      "<div class='dz'><div class='ic'>" + I.up + "</div><b>" + esc(T.drop) + "</b><small>" + esc(T.or) + "</small>" +
      "<div class='row'><button class='btn pri'>" + esc(T.choose) + "</button>" +
      (mobile ? "<button class='btn sec cam'>" + I.cam + esc(T.camera) + "</button>" : "") + "</div>" +
      "<small>" + esc(T.hint) + "</small></div>" +
      "<input class='sr f1' type='file' accept='image/jpeg,image/png,image/webp' aria-hidden='true' tabindex='-1'>" +
      "<input class='sr f2' type='file' accept='image/*' capture='environment' aria-hidden='true' tabindex='-1'>";
    var dz = body.querySelector(".dz"), f1 = body.querySelector(".f1"), f2 = body.querySelector(".f2");
    body.querySelector(".btn.pri").addEventListener("click", function () { f1.click(); });
    var cam = body.querySelector(".cam"); cam && cam.addEventListener("click", function () { f2.click(); });
    [f1, f2].forEach(function (f) { f.addEventListener("change", function () { f.files[0] && handle(f.files[0]); }); });
    ["dragenter", "dragover"].forEach(function (n) { dz.addEventListener(n, function (e) { e.preventDefault(); dz.classList.add("on"); }); });
    ["dragleave", "drop"].forEach(function (n) { dz.addEventListener(n, function (e) { e.preventDefault(); dz.classList.remove("on"); }); });
    dz.addEventListener("drop", function (e) { var f = e.dataTransfer && e.dataTransfer.files[0]; f && handle(f); });
  }

  // Brauzerda 1024px gacha kichraytirish → JPEG (~200–400KB)
  function resize(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var max = 1024, w = img.naturalWidth, h = img.naturalHeight, k = Math.min(1, max / Math.max(w, h));
        var c = document.createElement("canvas"); c.width = Math.round(w * k); c.height = Math.round(h * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        c.toBlob(function (b) { URL.revokeObjectURL(url); b ? resolve({ blob: b, preview: c.toDataURL("image/jpeg", 0.6) }) : reject(new Error("blob")); }, "image/jpeg", 0.85);
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("type")); };
      img.src = url;
    });
  }

  function handle(file) {
    if (state.busy) return;
    if (!/^image\//.test(file.type)) return renderPicker(T.errType);
    if (file.size > 25 * 1024 * 1024) return renderPicker(T.errBig);
    state.busy = true;
    resize(file).then(function (r) {
      renderLoading(r.preview);
      var fd = new FormData();
      fd.append("image", r.blob, (file.name || "image").replace(/\.[^.]+$/, "") + ".jpg");
      fd.append("session_id", vd.sid);
      fd.append("consent", String(vd.consent !== false));
      fd.append("device", /Mobi/i.test(navigator.userAgent) ? "mobile" : "desktop");
      var timer = setTimeout(function () { var s = root.querySelector(".st span"); s && (s.textContent = T.matching); }, 1600);
      return fetch(vd.base + "/v1/public/visual-search", { method: "POST", body: fd, headers: { "X-Vision-Key": vd.key } })
        .then(function (res) {
          clearTimeout(timer);
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok) {
              var code = data && data.error && data.error.code;
              throw new Error(code === "AI_UNAVAILABLE" ? T.errAi : code === "RATE_LIMITED" || code === "QUOTA_EXCEEDED" ? T.errRate :
                code === "IMAGE_TOO_LARGE" ? T.errBig : code === "UNSUPPORTED_IMAGE" || code === "INVALID_IMAGE" ? T.errType : T.err);
            }
            renderResults(data, r.preview);
          });
        });
    }).catch(function (e) {
      renderPicker(e && e.message && e.message.length > 8 ? e.message : T.err);
    }).then(function () { state.busy = false; });
  }

  function renderLoading(preview) {
    var sk = "";
    for (var i = 0; i < 4; i++) sk += "<div><div class='sk' style='aspect-ratio:1'></div><div class='sk' style='height:12px;margin-top:10px;width:80%'></div><div class='sk' style='height:12px;margin-top:6px;width:50%'></div></div>";
    body.innerHTML = "<div class='pv'><img alt='' src='" + preview + "'><div><div class='st'><div class='spin'></div><span>" +
      esc(T.analyzing) + "</span></div></div></div><div class='grid'>" + sk + "</div>";
  }

  function renderResults(data, preview) {
    var ai = data.ai_detected || {}, products = data.products || [];
    var chips = [ai.category, ai.color, ai.type, ai.style].filter(function (x) { return x && x !== "boshqa"; })
      .map(function (c, i) { return "<span class='chip" + (i === 0 ? " p" : "") + "'>" + esc(c) + "</span>"; }).join("");
    var head = "<div class='pv'><img alt='' src='" + preview + "'><div style='flex:1;min-width:0'><div class='lbl'>" + esc(T.detected) +
      "</div><div class='chips'>" + chips + "</div></div><button class='btn sec sm again'>" + esc(T.again) + "</button></div>";
    var empty = data.is_unmet_demand ? "<div class='empty'><b>" + esc(T.none) + "</b><p>" + esc(T.noneSub) + "</p></div>" : "";
    var cards = products.map(function (p, i) {
      return "<div class='card'><a class='im' href='" + esc(safeUrl(p.product_url)) + "' data-i='" + i + "'>" +
        (p.image_url ? "<img loading='lazy' alt='" + esc(p.name) + "' src='" + esc(safeUrl(p.image_url)) + "'>" : "") +
        (!data.is_unmet_demand && p.score ? "<span class='sc'>" + Math.round(p.score * 100) + "% " + esc(T.match) + "</span>" : "") +
        (p.in_stock === false ? "<span class='oos'>" + esc(T.out) + "</span>" : "") + "</a>" +
        "<div class='ci'><a class='nm' href='" + esc(safeUrl(p.product_url)) + "' data-i='" + i + "'>" + esc(p.name) + "</a>" +
        "<div class='pr'>" + esc(money(p.price_minor, p.currency)) + "</div>" +
        "<div class='ac'><a class='btn sec sm' href='" + esc(safeUrl(p.product_url)) + "' data-i='" + i + "'>" + esc(T.view) + "</a>" +
        (p.in_stock === false ? "" : "<button class='btn pri sm add' data-i='" + i + "'>" + esc(T.add) + "</button>") + "</div></div></div>";
    }).join("");
    body.innerHTML = head + empty + (products.length ? (data.is_unmet_demand ? "" : "<div class='lbl' style='margin-bottom:10px'>" + esc(T.found) + " · " + products.length + "</div>") + "<div class='grid'>" + cards + "</div>" : "");
    body.querySelector(".again").addEventListener("click", function () { renderPicker(); });

    var sid = data.search_id;
    try { localStorage.setItem("vd_search", JSON.stringify({ id: sid, t: Date.now() })); } catch (e) {}
    if (products.length) vd.track("RESULT_VIEW", { search_id: sid });

    Array.prototype.forEach.call(body.querySelectorAll("a[data-i]"), function (a) {
      a.addEventListener("click", function () {
        var p = products[+a.getAttribute("data-i")];
        vd.track("PRODUCT_CLICK", { search_id: sid, id: p.id, price_minor: p.price_minor, currency: p.currency });
      });
    });
    Array.prototype.forEach.call(body.querySelectorAll("button.add"), function (b) {
      b.addEventListener("click", function () {
        var p = products[+b.getAttribute("data-i")];
        b.disabled = true;
        addToCart(p, sid).then(function (ok) {
          if (ok) { toast(T.added); vd.track("ADD_TO_CART", { search_id: sid, id: p.id, qty: 1, price_minor: p.price_minor, currency: p.currency }); }
        }).catch(function () { location.href = safeUrl(p.product_url); })
          .then(function () { b.disabled = false; });
      });
    });
  }

  // ---------- Savat adapterlari ----------
  function addToCart(p, sid) {
    var adapter = cfg.cart_adapter || "none";
    var api = window.VisionAnalytics || {};
    if (typeof api.onAddToCart === "function") {
      return Promise.resolve(api.onAddToCart({ id: p.id, name: p.name, price_minor: p.price_minor, currency: p.currency, search_id: sid })).then(function (r) { return r !== false; });
    }
    if (adapter === "woocommerce") {
      return fetch("/?add-to-cart=" + encodeURIComponent(p.id) + "&quantity=1", { credentials: "include" }).then(function (r) { return r.ok; });
    }
    if (adapter === "shopify") {
      return fetch("/cart/add.js", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: [{ id: Number(p.id), quantity: 1, properties: { _vd_search: sid } }], attributes: { vd_sid: vd.sid } }) })
        .then(function (r) { return r.ok; });
    }
    if (adapter === "opencart") {
      var fd = new URLSearchParams(); fd.set("product_id", p.id); fd.set("quantity", "1");
      return fetch("index.php?route=checkout/cart/add", { method: "POST", body: fd, credentials: "include" }).then(function (r) { return r.ok; });
    }
    // 0-daraja (nol sozlama): mahsulot sahifasiga ?vd=<search_id> bilan o'tish
    vd.track("PRODUCT_CLICK", { search_id: sid, id: p.id, price_minor: p.price_minor, currency: p.currency });
    location.href = safeUrl(p.product_url);
    return Promise.resolve(false);
  }

  function toast(msg) {
    var t = document.createElement("div"); t.className = "toast"; t.textContent = msg; t.setAttribute("role", "status");
    root.appendChild(t); setTimeout(function () { t.remove(); }, 2200);
  }

  vd.open = open;
  vd.close = close;
})();
