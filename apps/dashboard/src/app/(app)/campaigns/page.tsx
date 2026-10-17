"use client";

import clsx from "clsx";
import { Globe, Megaphone, Plus, Send, Square, Trash2, Webhook, FileDown } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Badge, Card, Empty, Field, Modal, PageHeader, Skeleton, Spinner, useToast } from "@/components/ui";
import { api, download } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { can, dateTime, num } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const CHANNELS_BASIC = [
  { id: "onsite", label: "Saytdagi banner", sub: "Saytingizda shu segmentdagi xaridorlarga taklif va mos mahsulotlar ko'rinadi", icon: Globe },
  { id: "webhook", label: "Mening tizimimga", sub: "Ro'yxat sizning CRM / SMS tizimingizga avtomatik yuboriladi", icon: Webhook },
  { id: "export", label: "Ro'yxatni yuklab olish", sub: "Xaridorlar ro'yxatini faylda olib, o'zingiz yuborasiz", icon: FileDown },
];
const CHANNELS_PREMIUM = [
  { id: "onsite", label: "Do'kondagi banner", sub: "Do'koningizda shu segmentdagi xaridorlarga taklif va mos mahsulotlar ko'rinadi", icon: Globe },
  { id: "export", label: "Xaridorlar ro'yxati", sub: "Aksiyalarga rozi bo'lgan xaridorlar telefon va e-mail bilan — SMS/e-mail uchun", icon: FileDown },
];
const STATUS: Record<string, { label: string; tone: "neutral" | "ok" | "brand" | "warn" }> = {
  draft: { label: "Qoralama", tone: "neutral" }, active: { label: "Faol", tone: "ok" }, sent: { label: "Yuborildi", tone: "brand" }, stopped: { label: "To'xtatildi", tone: "warn" },
};

function CampaignsInner() {
  const { tenant } = useAuth();
  const toast = useToast();
  const initialSeg = useSearchParams().get("segment");
  const { data, mutate } = useApi<any>("/v1/dashboard/campaigns");
  const audiences = useApi<any>("/v1/dashboard/audiences");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", segment: "all", channel: "onsite", title: "", message: "", discount_code: "" });
  const [webhook, setWebhook] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const admin = can(tenant?.role, "admin");
  const premium = tenant?.plan === "premium";
  const CHANNELS = premium ? CHANNELS_PREMIUM : CHANNELS_BASIC;
  const ALL = [...CHANNELS_PREMIUM, ...CHANNELS_BASIC];

  useEffect(() => { if (initialSeg) { setF((x) => ({ ...x, segment: initialSeg })); setOpen(true); } }, [initialSeg]);
  useEffect(() => { if (data) setWebhook(data.webhook_url || ""); }, [data]);

  async function act(id: string, path: string, method = "POST", msg = "Bajarildi") {
    setBusy(id + path);
    try {
      const r = await api(`/v1/dashboard/campaigns/${id}${path}`, { method });
      const res = r?.result;
      if (res?.status === "error") toast(res.error, "bad");
      else toast(res ? `${msg}: ${res.recipients} ta qabul qiluvchi` : msg);
      mutate();
    } catch (e: any) { toast(e.message, "bad"); } finally { setBusy(null); }
  }

  return (
    <>
      <PageHeader title="Kampaniyalar" description={premium ? "Har bir xaridorga qiziqishiga mos taklif: do'kondagi banner yoki SMS/e-mail ro'yxati" : "Har bir xaridorga qiziqishiga mos taklif: saytdagi banner, tizimingizga yuborish yoki ro'yxat"}
        actions={admin && <button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Yangi kampaniya</button>} />

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Card pad={false} title="Kampaniyalar">
          {!data ? <div className="p-5"><Skeleton className="h-60" /></div> : data.items.length === 0 ? (
            <Empty icon={<Megaphone className="h-6 w-6" />} title="Hali kampaniya yo'q" text="Auditoriya bo'limidan segment tanlab, unga mos taklif yarating." />
          ) : (
            <ul className="divide-y divide-line">
              {data.items.map((c: any) => {
                const ch = CHANNELS.find((x) => x.id === c.channel) ?? ALL.find((x) => x.id === c.channel)!;
                return (
                  <li key={c.id} className="flex flex-wrap items-start gap-4 px-5 py-4">
                    <span className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-brand-soft text-brand"><ch.icon className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2"><p className="font-semibold">{c.name}</p><Badge tone={STATUS[c.status]?.tone}>{STATUS[c.status]?.label}</Badge></div>
                      <p className="mt-0.5 text-sm">{c.title}{c.discount_code && <code className="ml-2 rounded bg-subtle px-1.5 py-0.5 text-xs">{c.discount_code}</code>}</p>
                      <p className="mt-1 text-xs text-muted">{c.segment_label} · {ch.label} · {num(c.audience_size)} qabul qiluvchi
                        {c.stats?.sent ? ` · ${num(c.stats.sent)} yuborildi` : ""}{c.stats?.impressions ? ` · ${num(c.stats.impressions)} ko'rildi` : ""}
                        {c.stats?.clicks ? ` · ${num(c.stats.clicks)} bosildi` : ""}{c.sent_at ? ` · ${dateTime(c.sent_at)}` : ""}</p>
                      {c.stats?.error && <p className="mt-1 text-xs text-bad">{c.stats.error}</p>}
                    </div>
                    {admin && (
                      <div className="flex gap-1">
                        {c.channel === "export" ? (
                          <button className="btn-secondary h-8 text-xs" onClick={() => download(`/v1/dashboard/audiences/export?segment=${encodeURIComponent(c.segment)}`, "kampaniya.csv")}><FileDown className="h-3.5 w-3.5" />CSV</button>
                        ) : c.status === "active" ? (
                          <button className="btn-secondary h-8 text-xs" onClick={() => act(c.id, "/stop", "POST", "To'xtatildi")}><Square className="h-3.5 w-3.5" />To'xtatish</button>
                        ) : (
                          <button className="btn-primary h-8 text-xs" disabled={busy === c.id + "/send"} onClick={() => act(c.id, "/send", "POST", c.channel === "onsite" ? "Faollashtirildi" : "Yuborildi")}>
                            {busy === c.id + "/send" ? <Spinner /> : <Send className="h-3.5 w-3.5" />}{c.channel === "onsite" ? "Faollashtirish" : "Yuborish"}</button>
                        )}
                        <button className="btn-ghost h-8 w-8 px-0 hover:text-bad" aria-label="O'chirish" onClick={() => confirm("Kampaniya o'chirilsinmi?") && act(c.id, "", "DELETE", "O'chirildi")}><Trash2 className="h-4 w-4" /></button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <div className="space-y-4">
          <Card title="Qanday ishlaydi?">
            <ol className="space-y-3 text-sm">
              <li className="flex gap-3"><span className="grid h-6 w-6 flex-none place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand">1</span>
                <span>Auditoriya bo'limida segment tanlang — masalan "krossovkaga qiziqqanlar" yoki "savatni tashlab ketganlar".</span></li>
              <li className="flex gap-3"><span className="grid h-6 w-6 flex-none place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand">2</span>
                <span>Taklif matni va promo-kod yozing.</span></li>
              <li className="flex gap-3"><span className="grid h-6 w-6 flex-none place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand">3</span>
                <span>Har bir xaridorga uning qiziqishiga mos mahsulotlar avtomatik tanlanadi va ko'rsatiladi.</span></li>
            </ol>
          </Card>
          {!premium && admin && (
            <Card title="Tizimingiz manzili" description="'Mening tizimimga' kanali uchun. Manzilni saytingizni qo'llab-quvvatlovchi mutaxassis beradi.">
              <input className="input text-[13px]" placeholder="https://…" value={webhook} onChange={(e) => setWebhook(e.target.value)} />
              <button className="btn-secondary mt-3 w-full" onClick={async () => {
                try { await api("/v1/dashboard/campaigns-settings", { method: "PUT", body: { marketing_webhook_url: webhook } }); toast("Saqlandi"); mutate(); }
                catch (e: any) { toast(e.fields?.[0]?.msg || e.message, "bad"); }
              }}>Saqlash</button>
            </Card>
          )}
        </div>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Yangi kampaniya" size="lg"
        footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Bekor qilish</button>
          <button className="btn-primary" disabled={busy === "create" || !f.name || !f.title} onClick={async () => {
            setBusy("create");
            try { await api("/v1/dashboard/campaigns", { method: "POST", body: { ...f, discount_code: f.discount_code || null } }); toast("Kampaniya yaratildi"); setOpen(false); mutate(); }
            catch (e: any) { toast(e.fields?.[0] ? `${e.fields[0].loc.at(-1)}: ${e.fields[0].msg}` : e.message, "bad"); } finally { setBusy(null); }
          }}>{busy === "create" && <Spinner />}Yaratish</button></>}>
        <div className="space-y-4">
          <Field label="Nomi (ichki)"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Krossovka sevuvchilarga -10%" /></Field>
          <Field label="Segment" help="Auditoriya bo'limidagi segmentlar">
            <select className="input" value={f.segment} onChange={(e) => setF({ ...f, segment: e.target.value })}>
              <option value="all">Barcha profillar</option>
              {audiences.data?.segments.map((s: any) => <option key={s.key} value={s.key}>{s.label} ({s.size})</option>)}
              {f.segment !== "all" && !audiences.data?.segments.some((s: any) => s.key === f.segment) && <option value={f.segment}>{f.segment}</option>}
            </select>
          </Field>
          <div>
            <span className="label">Kanal</span>
            <div className={clsx("grid gap-2", premium ? "sm:grid-cols-2" : "sm:grid-cols-3")}>
              {CHANNELS.map((c) => (
                <button key={c.id} type="button" onClick={() => setF({ ...f, channel: c.id })}
                  className={clsx("rounded-xl border-2 p-3 text-left text-sm transition", f.channel === c.id ? "border-brand bg-brand-soft/50" : "border-line hover:border-muted")}>
                  <c.icon className="mb-1.5 h-4 w-4 text-brand" /><p className="font-semibold">{c.label}</p><p className="mt-0.5 text-xs text-muted">{c.sub}</p>
                </button>
              ))}
            </div>
          </div>
          <Field label="Sarlavha (xaridor ko'radi)"><input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Siz uchun maxsus: krossovkalarga −10%" /></Field>
          <Field label="Xabar"><textarea className="input h-20 py-2" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} placeholder="Qidirgan modellaringiz endi chegirmada" /></Field>
          <Field label="Promo-kod (ixtiyoriy)"><input className="input font-mono uppercase" value={f.discount_code} onChange={(e) => setF({ ...f, discount_code: e.target.value.toUpperCase() })} placeholder="RUN10" /></Field>
          {f.channel === "webhook" && !data?.webhook_url && <p className="rounded-lg bg-warn-soft p-3 text-sm text-warn">Avval o'ngdagi "Tizimingiz manzili"ni saqlang.</p>}
        </div>
      </Modal>
    </>
  );
}

export default function CampaignsPage() {
  return <Suspense><CampaignsInner /></Suspense>;
}
