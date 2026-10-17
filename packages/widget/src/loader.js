/*!
 * Vision Detect loader v1 — <script src=".../cdn/v1/loader.js" data-key="pk_live_xxx" async></script>
 * Fail-open: har qanday xatoda jim to'xtaydi, mijoz saytini buzmaydi. Global faqat window.__vd (+ VisionAnalytics API).
 */
(function () {
  "use strict";
  try {
    if (window.__vd) return; // dublikat himoyasi
    var script = document.currentScript ||
      (function () { var s = document.querySelectorAll("script[data-key]"); return s[s.length - 1]; })();
    if (!script) return;
    var KEY = script.getAttribute("data-key");
    if (!KEY) return;
    var BASE = script.src.replace(/\/cdn\/v1\/loader\.js.*$/, "");
    var VERSION = "1.0.0";
    var LS = safeStorage();

    var vd = (window.__vd = { key: KEY, base: BASE, version: VERSION, config: null, ready: false });

    // ---------- sessiya (vd_sid) va consent ----------
    function uid() {
      if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
      return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        var r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      });
    }
    function getCookie(n) { var m = document.cookie.match("(?:^|; )" + n + "=([^;]*)"); return m ? decodeURIComponent(m[1]) : null; }
    var sid = LS.get("vd_sid") || getCookie("vd_sid");
    if (!sid) sid = "vd_" + uid().replace(/-/g, "").slice(0, 24);
    LS.set("vd_sid", sid);
    try { document.cookie = "vd_sid=" + sid + "; path=/; max-age=" + 60 * 60 * 24 * 365 + "; SameSite=Lax"; } catch (e) {}
    vd.sid = sid;
    var consentStored = LS.get("vd_consent");
    vd.consent = consentStored === null ? null : consentStored === "1";

    // ---------- atribusiya: ?vd=<search_id> ----------
    try {
      var vdParam = new URLSearchParams(location.search).get("vd");
      if (vdParam && /^[0-9a-f-]{36}$/i.test(vdParam)) LS.set("vd_search", JSON.stringify({ id: vdParam, t: Date.now() }));
    } catch (e) {}
    vd.currentSearch = function () {
      try {
        var s = JSON.parse(LS.get("vd_search") || "null");
        var days = (vd.config && vd.config.attribution_days) || 7;
        if (s && Date.now() - s.t < days * 864e5) return s.id;
      } catch (e) {}
      return null;
    };

    // ---------- hodisalar navbati (sendBeacon + oflayn navbat) ----------
    var queue = [];
    try { queue = JSON.parse(LS.get("vd_queue") || "[]").slice(-100); } catch (e) {}
    var flushTimer = null;
    function persist() { LS.set("vd_queue", JSON.stringify(queue.slice(-100))); }
    function consentOk() { return !(vd.config && vd.config.consent_mode === "explicit" && vd.consent !== true); }

    vd.track = function (type, data) {
      try {
        if (!consentOk()) return;
        data = data || {};
        var ev = {
          event_id: uid(), type: type, session_id: sid, ts: new Date().toISOString(),
          search_id: data.search_id || vd.currentSearch() || undefined,
          product_id: data.id != null ? String(data.id) : undefined,
          qty: data.qty || 1,
          price_minor: data.price_minor != null ? Math.round(data.price_minor) :
            (data.price != null ? Math.round(Number(data.price) * 100) : undefined),
          currency: data.currency || undefined,
          order_ref: data.order_ref != null ? String(data.order_ref) : undefined,
          items: data.items || undefined
        };
        queue.push(ev); persist();
        clearTimeout(flushTimer);
        flushTimer = setTimeout(flush, type === "PURCHASE" || type === "ADD_TO_CART" ? 0 : 1500);
      } catch (e) {}
    };

    function flush() {
      if (!queue.length || navigator.onLine === false) return;
      var batch = queue.splice(0, 50);
      persist();
      var body = JSON.stringify({ events: batch, consent: vd.consent !== false });
      var url = BASE + "/v1/public/events?key=" + encodeURIComponent(KEY);
      var sent = false;
      try {
        if (navigator.sendBeacon) sent = navigator.sendBeacon(url, new Blob([body], { type: "text/plain" }));
      } catch (e) {}
      if (!sent) {
        fetch(url, { method: "POST", body: body, keepalive: true, headers: { "Content-Type": "text/plain" } })
          .catch(function () { queue = batch.concat(queue); persist(); });
      }
      if (queue.length) setTimeout(flush, 200);
    }
    window.addEventListener("online", flush);
    document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") flush(); });

    // ---------- Ochiq API (sotuvchi sayti uchun) ----------
    var api = window.VisionAnalytics = window.VisionAnalytics || {};
    api.track = function (type, data) { vd.track(String(type).toUpperCase(), data); };
    api.identify = function (customerRef) {
      try {
        if (!customerRef || vd.consent === false) return;
        fetch(BASE + "/v1/public/identify", {
          method: "POST", headers: { "Content-Type": "application/json", "X-Vision-Key": KEY },
          body: JSON.stringify({ session_id: sid, customer_ref: String(customerRef), consent: vd.consent !== false })
        }).catch(function () {});
      } catch (e) {}
    };
    api.logout = function () {
      sid = "vd_" + uid().replace(/-/g, "").slice(0, 24); vd.sid = sid; LS.set("vd_sid", sid);
      try { document.cookie = "vd_sid=" + sid + "; path=/; SameSite=Lax"; } catch (e) {}
    };
    api.setConsent = function (v) { vd.consent = !!v; LS.set("vd_consent", v ? "1" : "0"); };
    api.open = function () { openWidget(); };

    // ---------- GA4 dataLayer tinglash ----------
    function onDataLayer(item) {
      try {
        if (!item || typeof item !== "object") return;
        var name = item.event, ec = item.ecommerce || {};
        var items = ec.items || [];
        if (name === "add_to_cart" && items[0]) {
          vd.track("ADD_TO_CART", { id: items[0].item_id, qty: items[0].quantity || 1, price: items[0].price, currency: ec.currency });
        } else if (name === "purchase" && ec.transaction_id) {
          vd.track("PURCHASE", { order_ref: ec.transaction_id, currency: ec.currency, items: items.map(function (i) {
            return { id: String(i.item_id), qty: i.quantity || 1, price_minor: Math.round(Number(i.price || 0) * 100) };
          }) });
        }
      } catch (e) {}
    }
    try {
      var dl = (window.dataLayer = window.dataLayer || []);
      var origPush = dl.push;
      dl.push = function () { for (var i = 0; i < arguments.length; i++) onDataLayer(arguments[i]); return origPush.apply(dl, arguments); };
    } catch (e) {}

    // ---------- Qidiruv maydonini topish va tugma ----------
    var SELECTORS = ['input[type="search"]', 'input[name="q"]', 'input[name="s"]', 'input[name="search"]',
      'input[name="query"]', 'input[placeholder*="qidir" i]', 'input[placeholder*="search" i]', 'input[placeholder*="поиск" i]'];

    function findInput() {
      var custom = vd.config && vd.config.search_selector;
      var list = custom ? [custom].concat(SELECTORS) : SELECTORS;
      for (var i = 0; i < list.length; i++) {
        try {
          var els = document.querySelectorAll(list[i]);
          for (var j = 0; j < els.length; j++) if (els[j].offsetParent !== null) return els[j];
        } catch (e) {}
      }
      return null;
    }

    var ICON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3.5"/></svg>';
    var LABEL = { uz: "Rasm orqali qidirish", ru: "Поиск по фото", en: "Search by image" };

    function makeButton(inline) {
      var host = document.createElement("span");
      host.setAttribute("data-vd", inline ? "inline" : "floating");
      var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
      var color = (vd.config.theme && vd.config.theme.primary) || "#6d28d9";
      var lang = vd.config.language || "uz";
      var pos = (vd.config.theme && vd.config.theme.position) === "bottom-left" ? "left:20px" : "right:20px";
      root.innerHTML = "<style>" +
        "button{all:unset;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;transition:transform .15s,box-shadow .15s}" +
        "button:focus-visible{outline:2px solid " + color + ";outline-offset:2px}" +
        ".in{width:36px;height:36px;border-radius:10px;color:" + color + ";background:transparent}" +
        ".in:hover{background:rgba(0,0,0,.06)}" +
        ".fl{position:fixed;bottom:20px;" + pos + ";z-index:2147483000;height:52px;padding:0 18px 0 16px;gap:8px;border-radius:999px;background:" + color + ";color:#fff;font:600 14px/1 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.18)}" +
        ".fl:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(0,0,0,.22)}" +
        "@media(max-width:480px){.fl span{display:none}.fl{width:52px;padding:0}}" +
        "</style><button class='" + (inline ? "in" : "fl") + "' title='" + LABEL[lang] + "' aria-label='" + LABEL[lang] + "'>" +
        ICON + (inline ? "" : "<span>" + LABEL[lang] + "</span>") + "</button>";
      root.querySelector("button").addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); openWidget(); });
      return host;
    }

    var mounted = null;
    function mount() {
      try {
        if (mounted && document.contains(mounted)) return;
        var input = findInput();
        if (input && input.parentNode) {
          var host = makeButton(true);
          host.style.cssText = "display:inline-flex;align-items:center;vertical-align:middle;margin-left:4px;";
          input.parentNode.insertBefore(host, input.nextSibling);
          mounted = host;
        } else if (!document.querySelector('[data-vd="floating"]')) {
          mounted = makeButton(false);
          document.body.appendChild(mounted);
        }
      } catch (e) {}
    }

    // ---------- Katta widget.js faqat bosilganda (lazy) ----------
    var loading = null;
    function openWidget() {
      if (vd.open) return vd.open();
      if (!loading) {
        loading = new Promise(function (resolve, reject) {
          var s = document.createElement("script");
          s.src = BASE + "/cdn/v1/widget.js?v=" + VERSION; s.async = true;
          s.onload = resolve; s.onerror = reject;
          document.head.appendChild(s);
        });
      }
      loading.then(function () { vd.open && vd.open(); }).catch(function () { loading = null; });
    }

    // ---------- "Rahmat" sahifasi: zaxira PURCHASE ----------
    function thankYouCheck() {
      try {
        var pattern = vd.config.thank_you_url_pattern;
        if (!pattern || location.pathname.indexOf(pattern) === -1) return;
        var p = new URLSearchParams(location.search);
        var order = p.get("order") || p.get("order_id") || p.get("order-received");
        if (order && !LS.get("vd_order_" + order)) {
          LS.set("vd_order_" + order, "1");
          vd.track("PURCHASE", { order_ref: order, items: safeJson(p.get("items")) || undefined });
        }
      } catch (e) {}
    }
    function safeJson(s) { try { return s ? JSON.parse(s) : null; } catch (e) { return null; } }

    // ---------- Shaxsiy tavsiyalar: <div data-vd-recs data-title="Siz uchun" data-limit="4"></div> ----------
    function money(minor, cur) {
      if (minor == null) return "";
      try { return new Intl.NumberFormat("ru-RU").format(Math.round(minor / 100)) + (cur === "UZS" || !cur ? " so'm" : " " + cur); }
      catch (e) { return String(minor / 100); }
    }
    function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
    function renderRecs() {
      try {
        var slots = document.querySelectorAll("[data-vd-recs]:not([data-vd-done])");
        if (!slots.length) return;
        var limit = Number(slots[0].getAttribute("data-limit")) || 4;
        fetch(BASE + "/v1/public/recommendations?key=" + encodeURIComponent(KEY) + "&session_id=" + encodeURIComponent(sid) + "&limit=" + limit)
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d || !d.products || !d.products.length) return;
            var color = (vd.config.theme && vd.config.theme.primary) || "#6d28d9";
            Array.prototype.forEach.call(slots, function (slot) {
              slot.setAttribute("data-vd-done", "1");
              var root = slot.attachShadow ? slot.attachShadow({ mode: "open" }) : slot;
              var title = slot.getAttribute("data-title") || (d.personalized ? "Siz uchun tanladik" : "Ommabop mahsulotlar");
              var banner = d.banner ? "<div class='bn'><b>" + esc(d.banner.title) + "</b><span>" + esc(d.banner.message || "") + "</span>" +
                (d.banner.discount_code ? "<code>" + esc(d.banner.discount_code) + "</code>" : "") + "</div>" : "";
              root.innerHTML = "<style>:host{all:initial;display:block}*{box-sizing:border-box;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}" +
                "h3{margin:0 0 12px;font-size:18px;color:#0f172a}.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}" +
                "a{color:inherit;text-decoration:none}.c img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:12px;background:#f1f5f9;display:block}" +
                ".n{font-size:13px;margin-top:8px;line-height:1.35;color:#0f172a;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}" +
                ".p{font-weight:700;font-size:14px;margin-top:4px;color:#0f172a}.o{color:#94a3b8;text-decoration:line-through;font-weight:400;font-size:12px;margin-left:6px}" +
                ".bn{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:14px 16px;border-radius:14px;margin-bottom:14px;background:" + color + "14;color:#0f172a}" +
                ".bn b{font-size:15px}.bn span{font-size:13px;color:#475569}.bn code{margin-left:auto;border:2px dashed " + color + ";border-radius:8px;padding:4px 10px;font-weight:700;color:" + color + "}</style>" +
                banner + "<h3>" + esc(title) + "</h3><div class='g'>" + d.products.map(function (p) {
                  return "<a class='c' href='" + esc(p.product_url) + "' data-id='" + esc(p.id) + "'><img loading='lazy' alt='' src='" + esc(p.image_url || "") + "'>" +
                    "<div class='n'>" + esc(p.name) + "</div><div class='p'>" + money(p.price_minor, p.currency) +
                    (p.compare_at_minor && p.compare_at_minor > p.price_minor ? "<span class='o'>" + money(p.compare_at_minor, p.currency) + "</span>" : "") + "</div></a>";
                }).join("") + "</div>";
              Array.prototype.forEach.call(root.querySelectorAll("a[data-id]"), function (a) {
                a.addEventListener("click", function () {
                  vd.track("PRODUCT_CLICK", { id: a.getAttribute("data-id") });
                  if (d.banner) campaignEvent(d.banner.campaign_id, "click");
                });
              });
            });
            if (d.banner) campaignEvent(d.banner.campaign_id, "impression");
          }).catch(function () {});
      } catch (e) {}
    }
    function campaignEvent(id, kind) {
      try {
        fetch(BASE + "/v1/public/campaign-event?key=" + encodeURIComponent(KEY), {
          method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
          body: JSON.stringify({ campaign_id: id, kind: kind })
        }).catch(function () {});
      } catch (e) {}
    }
    api.renderRecommendations = renderRecs;

    // ---------- Ishga tushirish ----------
    fetch(BASE + "/v1/public/config/" + encodeURIComponent(KEY), { credentials: "omit" })
      .then(function (r) { if (!r.ok) throw new Error("config " + r.status); return r.json(); })
      .then(function (cfg) {
        vd.config = cfg; vd.ready = true;
        var start = function () {
          mount();
          renderRecs();
          thankYouCheck();
          flush();
          try {
            var mo = new MutationObserver(function () { if (!mounted || !document.contains(mounted)) mount(); });
            mo.observe(document.body, { childList: true, subtree: true });
          } catch (e) {}
        };
        if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
      })
      .catch(function () { /* fail-open: vidjet jim yashirinadi */ });

    function safeStorage() {
      var mem = {};
      return {
        get: function (k) { try { return localStorage.getItem(k); } catch (e) { return k in mem ? mem[k] : null; } },
        set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { mem[k] = v; } }
      };
    }
  } catch (err) { /* fail-open */ }
})();
