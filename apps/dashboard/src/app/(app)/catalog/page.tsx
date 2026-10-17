"use client";

import { AlertTriangle, CheckCircle2, ImagePlus, Pencil, Plus, RefreshCw, Search, Trash2, Upload, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Badge, Card, Empty, ErrorBox, Field, Modal, PageHeader, Pagination, Skeleton, Spinner, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { can, dateTime, money, num, img } from "@/lib/format";
import { useApi } from "@/lib/hooks";

type Product = {
  id: string; external_id: string; name: string; description: string | null; category: string | null; color: string | null;
  type: string | null; price_minor: number | null; compare_at_minor: number | null; currency: string | null; image_url: string | null;
  image_path: string | null; product_url: string; in_stock: boolean; stock_qty: number | null; brand: string | null; sales_count: number;
};

const STOREFRONT = process.env.NEXT_PUBLIC_STOREFRONT_URL || "http://localhost:3001";
const EMPTY = { external_id: "", name: "", description: "", category: "", color: "", type: "", brand: "", price: "", old_price: "", stock: "",
  currency: "UZS", image: "", preview: "", product_url: "", in_stock: true };
const toMinor = (v: string) => (v.trim() ? Math.round(Number(v.replace(/\s/g, "").replace(",", ".")) * 100) : null);

function ProductModal({ open, onClose, product, onSaved }: { open: boolean; onClose: () => void; product: Product | null; onSaved: () => void }) {
  const toast = useToast();
  const [f, setF] = useState<typeof EMPTY>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    setF(product ? {
      external_id: product.external_id, name: product.name, description: product.description || "", category: product.category || "",
      color: product.color || "", type: product.type || "", brand: product.brand || "",
      price: product.price_minor != null ? String(product.price_minor / 100) : "",
      old_price: product.compare_at_minor != null ? String(product.compare_at_minor / 100) : "",
      stock: product.stock_qty != null ? String(product.stock_qty) : "", currency: product.currency || "UZS",
      image: product.image_path || "", preview: product.image_url || "", product_url: product.product_url, in_stock: product.in_stock,
    } : EMPTY);
  }, [product, open]);
  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  async function upload(file: File) {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api(`/v1/dashboard/catalog/images?analyze=true`, { method: "POST", body: fd });
      setF((x) => ({
        ...x, image: r.path, preview: r.url,
        category: x.category || (r.ai?.category !== "boshqa" ? r.ai?.category : "") || "", color: x.color || r.ai?.color || "", type: x.type || r.ai?.type || "",
        name: x.name || (r.ai?.search_query ? r.ai.search_query[0].toUpperCase() + r.ai.search_query.slice(1) : ""),
      }));
      toast(r.ai ? "Rasm yuklandi — AI kategoriya, rang va turni to'ldirdi" : "Rasm yuklandi");
      if (r.ai_error) toast(`AI: ${r.ai_error}`, "bad");
    } catch (e: any) { toast(e.message, "bad"); } finally { setUploading(false); }
  }

  async function save() {
    setBusy(true);
    try {
      const body = {
        external_id: f.external_id, name: f.name, description: f.description || null, category: f.category || null, color: f.color || null,
        brand: f.brand || null, currency: f.currency, image_url: f.image || null, in_stock: f.in_stock,
        price_minor: toMinor(f.price), compare_at_minor: toMinor(f.old_price), stock_qty: f.stock.trim() ? Number(f.stock) : null,
        product_url: f.product_url || `${STOREFRONT}/product/${encodeURIComponent(f.external_id)}`,
        attributes: f.type ? { type: f.type } : {},
      };
      await api(product ? `/v1/dashboard/catalog/products/${product.id}` : "/v1/dashboard/catalog/products", { method: product ? "PUT" : "POST", body });
      toast(product ? "Mahsulot yangilandi" : "Mahsulot qo'shildi");
      onSaved(); onClose();
    } catch (e: any) { toast(e.fields?.[0] ? `${e.fields[0].loc.at(-1)}: ${e.fields[0].msg}` : e.message, "bad"); }
    finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title={product ? "Mahsulotni tahrirlash" : "Yangi mahsulot"} size="lg"
      footer={<><button className="btn-secondary" onClick={onClose}>Bekor qilish</button><button className="btn-primary" disabled={busy || uploading} onClick={save}>{busy && <Spinner />}Saqlash</button></>}>
      <div className="mb-5 flex items-center gap-4">
        <div className="grid h-24 w-24 flex-none place-items-center overflow-hidden rounded-xl border border-dashed border-line bg-subtle">
          {f.preview ? <img src={img(f.preview)} alt="" className="h-full w-full object-cover" /> : <ImagePlus className="h-7 w-7 text-muted" />}
        </div>
        <div className="space-y-2">
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => { const x = e.target.files?.[0]; if (x) upload(x); e.target.value = ""; }} />
          <button className="btn-secondary" disabled={uploading} onClick={() => fileRef.current?.click()}>{uploading ? <Spinner /> : <Upload className="h-4 w-4" />}Rasm yuklash</button>
          <p className="text-xs text-muted">JPEG/PNG/WebP, 8MB gacha. EXIF o'chiriladi, 1600px gacha siqiladi.<br />AI kategoriya, rang va turni avtomatik to'ldiradi.</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="ID (SKU)"><input className="input" value={f.external_id} onChange={set("external_id")} disabled={!!product} /></Field>
        <Field label="Nomi"><input className="input" value={f.name} onChange={set("name")} /></Field>
        <Field label="Kategoriya" help="Bo'sh qolsa nomidan aniqlanadi"><input className="input" value={f.category} onChange={set("category")} placeholder="kiyim, poyabzal…" /></Field>
        <Field label="Tur"><input className="input" value={f.type} onChange={set("type")} placeholder="krossovka, xudi…" /></Field>
        <Field label="Rang"><input className="input" value={f.color} onChange={set("color")} placeholder="qora, qizil…" /></Field>
        <Field label="Brend"><input className="input" value={f.brand} onChange={set("brand")} /></Field>
        <Field label="Narx, so'm"><input className="input" inputMode="decimal" value={f.price} onChange={set("price")} placeholder="129000" /></Field>
        <Field label="Eski narx (aksiya)" help="To'ldirilsa, chegirma ko'rsatiladi"><input className="input" inputMode="decimal" value={f.old_price} onChange={set("old_price")} placeholder="159000" /></Field>
        <Field label="Ombordagi soni" help="Bo'sh — cheklanmagan"><input className="input" inputMode="numeric" value={f.stock} onChange={set("stock")} /></Field>
        <Field label="Valyuta"><input className="input" value={f.currency} onChange={set("currency")} maxLength={3} /></Field>
        <div className="sm:col-span-2"><Field label="Mahsulot sahifasi URL" help="Bo'sh qolsa — storefront sahifasi"><input className="input" value={f.product_url} onChange={set("product_url")} placeholder={`${STOREFRONT}/product/…`} /></Field></div>
        <div className="sm:col-span-2"><Field label="Tavsif"><textarea className="input h-20 py-2" value={f.description} onChange={set("description")} /></Field></div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.in_stock} onChange={(e) => setF({ ...f, in_stock: e.target.checked })} />Sotuvda</label>
      </div>
    </Modal>
  );
}

export default function CatalogPage() {
  const { tenant } = useAuth();
  const toast = useToast();
  const manage = can(tenant?.role, "catalog_manager");
  const premium = tenant?.plan === "premium";
  const router = useRouter();
  useEffect(() => { if (premium) router.replace("/products"); }, [premium, router]);
  const summary = useApi<any>("/v1/dashboard/catalog");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const products = useApi<{ total: number; items: Product[] }>(`/v1/dashboard/catalog/products?page=${page}&size=24&q=${encodeURIComponent(query)}`);
  const [feed, setFeed] = useState({ feed_url: "", feed_format: "json" });
  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState<Product | null>(null);
  const [modal, setModal] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (summary.data) setFeed({ feed_url: summary.data.feed_url || "", feed_format: summary.data.feed_format || "json" }); }, [summary.data]);
  useEffect(() => { const t = setTimeout(() => { setQuery(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);
  const refresh = () => { summary.mutate(); products.mutate(); };

  async function run(label: string, fn: () => Promise<any>, ok: string) {
    setBusy(label);
    try {
      const r = await fn();
      if (r?.status === "failed") toast(r.error || "Sinxron muvaffaqiyatsiz", "bad"); else toast(ok);
      refresh();
    } catch (e: any) { toast(e.message, "bad"); }
    finally { setBusy(null); }
  }

  const s = summary.data;
  const last = s?.runs?.[0];

  return (
    <>
      <PageHeader title="Katalog" description="Vidjet mahsulotlarni shu yerdan qidiradi. Sotuvchi bazasiga to'g'ridan-to'g'ri ulanmaymiz — faqat feed, fayl yoki API."
        actions={manage && <>
          <input ref={fileRef} type="file" accept=".csv,.json,.xml" className="hidden" onChange={(e) => {
            const file = e.target.files?.[0]; if (!file) return;
            const fd = new FormData(); fd.append("file", file);
            run("upload", () => api("/v1/dashboard/catalog/upload", { method: "POST", body: fd }), "Fayl yuklandi");
            e.target.value = "";
          }} />
          <button className="btn-secondary" onClick={() => fileRef.current?.click()} disabled={!!busy}>{busy === "upload" ? <Spinner /> : <Upload className="h-4 w-4" />}CSV / JSON yuklash</button>
          {premium && <button className="btn-primary" onClick={() => { setEditing(null); setModal(true); }}><Plus className="h-4 w-4" />Mahsulot</button>}
        </>} />

      {s?.last_failed && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-warn/40 bg-warn-soft px-4 py-3 text-sm text-warn">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
          <div><b>Oxirgi sinxron muvaffaqiyatsiz.</b> {last?.error} Eski katalog saqlab qolindi.</div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="grid grid-cols-3 gap-4 lg:col-span-3 xl:col-span-1 xl:grid-cols-1">
          {[["Jami mahsulot", s?.stats.total], ["Zaxirada", s?.stats.in_stock], ["Tugagan", s?.stats.out_of_stock]].map(([l, v]) => (
            <div key={l as string} className="card p-4"><p className="text-sm text-muted">{l}</p><p className="mt-1 text-2xl font-semibold tabular-nums">{s ? num(v as number) : "—"}</p></div>
          ))}
        </div>

        <Card title="Feed manbasi" description="Har 60 daqiqada avtomatik yangilanadi (JSON, CSV yoki Google Merchant XML)" className="lg:col-span-3 xl:col-span-2">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input className="input flex-1" placeholder="https://do'kon.uz/feed.json" value={feed.feed_url} disabled={!manage}
              onChange={(e) => setFeed({ ...feed, feed_url: e.target.value })} />
            <select className="input sm:w-28" value={feed.feed_format} disabled={!manage} onChange={(e) => setFeed({ ...feed, feed_format: e.target.value })}>
              <option value="json">JSON</option><option value="csv">CSV</option><option value="xml">XML</option>
            </select>
            {manage && <>
              <button className="btn-secondary" disabled={!!busy} onClick={() => run("feed", () => api("/v1/dashboard/catalog/feed", { method: "PUT", body: feed }), "Feed saqlandi")}>Saqlash</button>
              <button className="btn-primary" disabled={!!busy || !feed.feed_url} onClick={() => run("sync", () => api("/v1/dashboard/catalog/sync", { method: "POST" }), "Sinxron yakunlandi")}>
                {busy === "sync" ? <Spinner /> : <RefreshCw className="h-4 w-4" />}Hozir sinxronlash
              </button>
            </>}
          </div>
          <div className="mt-5">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Sinxron tarixi</p>
            {!s ? <Skeleton className="h-20" /> : s.runs.length === 0 ? <p className="text-sm text-muted">Hali sinxron bo'lmagan.</p> : (
              <ul className="divide-y divide-line rounded-lg border border-line">
                {s.runs.slice(0, 5).map((r: any) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 text-sm">
                    {r.status === "success" ? <CheckCircle2 className="h-4 w-4 text-ok" /> : <XCircle className="h-4 w-4 text-bad" />}
                    <span className="text-muted">{dateTime(r.started_at)}</span>
                    <Badge>{r.source}</Badge>
                    <span className="tabular-nums">{num(r.items_seen)} ko'rildi · {num(r.items_changed)} o'zgardi · {num(r.items_deleted)} o'chdi</span>
                    {r.error && <span className="w-full truncate text-xs text-bad sm:w-auto sm:flex-1">{r.error}</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>

      <Card className="mt-4" pad={false} title={`Mahsulotlar${products.data ? ` · ${num(products.data.total)}` : ""}`}
        actions={<div className="relative w-56"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input className="input h-9 pl-9" placeholder="Nomi yoki ID…" value={q} onChange={(e) => setQ(e.target.value)} /></div>}>
        {products.error && <div className="p-5"><ErrorBox error={products.error} /></div>}
        {!products.data ? <div className="grid grid-cols-2 gap-4 p-5 md:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-56" />)}</div> :
          products.data.items.length === 0 ? (
            <Empty title="Mahsulot yo'q" text="Feed URL kiriting yoki CSV fayl yuklang. Ustunlar: id, name, price, url, image, category, color, in_stock." />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
                {products.data.items.map((p) => (
                  <div key={p.id} className="group overflow-hidden rounded-xl border border-line">
                    <div className="relative aspect-square bg-subtle">
                      {p.image_url && <img src={img(p.image_url)} alt="" className="h-full w-full object-cover" loading="lazy" />}
                      {!p.in_stock && <span className="absolute right-2 top-2"><Badge tone="bad">tugagan</Badge></span>}
                      {premium && manage && (
                        <div className="absolute inset-x-2 bottom-2 hidden gap-1 group-hover:flex">
                          <button className="btn-secondary h-8 flex-1 text-xs" onClick={() => { setEditing(p); setModal(true); }}><Pencil className="h-3.5 w-3.5" />Tahrirlash</button>
                          <button className="btn-secondary h-8 w-8 px-0 text-bad" aria-label="O'chirish" onClick={() => confirm(`"${p.name}" o'chirilsinmi?`) &&
                            run("del", () => api(`/v1/dashboard/catalog/products/${p.id}`, { method: "DELETE" }), "O'chirildi")}><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      )}
                    </div>
                    <div className="space-y-1 p-3">
                      <p className="line-clamp-2 text-sm font-medium leading-snug">{p.name}</p>
                      <p className="text-sm font-semibold tabular-nums">{money(p.price_minor, p.currency || "UZS")}
                        {p.compare_at_minor ? <span className="ml-1.5 text-xs font-normal text-muted line-through">{money(p.compare_at_minor, p.currency || "UZS")}</span> : null}</p>
                      {p.stock_qty != null && <p className="text-xs text-muted">Omborda: {p.stock_qty} · sotilgan: {p.sales_count}</p>}
                      <div className="flex flex-wrap gap-1">{[p.category, p.color, p.type].filter(Boolean).map((t) => <Badge key={t}>{t}</Badge>)}</div>
                    </div>
                  </div>
                ))}
              </div>
              <Pagination page={page} size={24} total={products.data.total} onPage={setPage} />
            </>
          )}
      </Card>
      <ProductModal open={modal} onClose={() => setModal(false)} product={editing} onSaved={refresh} />
    </>
  );
}
