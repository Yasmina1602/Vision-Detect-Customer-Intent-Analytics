"use client";

import { useEffect, useState } from "react";
import { Badge, Card, Field, PageHeader, Skeleton, Spinner, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";

type S = Record<string, any>;

export default function SettingsPage() {
  const toast = useToast();
  const { reload } = useAuth();
  const { data, mutate } = useApi<any>("/v1/dashboard/settings");
  const [name, setName] = useState("");
  const [s, setS] = useState<S | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (data) { setName(data.name); setS(data.settings); } }, [data]);
  const premium = data?.plan === "premium";
  if (!data || !s) return <><PageHeader title="Sozlamalar" /><Skeleton className="h-96" /></>;

  const set = (k: string, v: any) => setS({ ...s, [k]: v });
  const dirty = JSON.stringify(s) !== JSON.stringify(data.settings) || name !== data.name;

  async function save() {
    setBusy(true);
    try {
      await api("/v1/dashboard/settings", { method: "PATCH", body: {
        name, unmet_threshold: Number(s!.unmet_threshold), language: s!.language, theme: s!.theme,
        search_selector: s!.search_selector, consent_mode: s!.consent_mode, attribution_days: Number(s!.attribution_days),
        abandon_after_hours: Number(s!.abandon_after_hours), currency: s!.currency, timezone: s!.timezone,
        customer_deeplink: s!.customer_deeplink, thank_you_url_pattern: s!.thank_you_url_pattern,
      } });
      toast("Sozlamalar saqlandi"); mutate(); reload();
    } catch (e: any) { toast(e.fields?.[0] ? `${e.fields[0].loc.at(-1)}: ${e.fields[0].msg}` : e.message, "bad"); }
    finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Sozlamalar" description="Vidjet ko'rinishi, analitika qoidalari va maxfiylik"
        actions={<button className="btn-primary" disabled={!dirty || busy} onClick={save}>{busy && <Spinner />}O'zgarishlarni saqlash</button>} />
      {process.env.NEXT_PUBLIC_EDITION !== "basic" && <PlanCard plan={data.plan} />}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Do'kon">
          <div className="space-y-4">
            <Field label="Do'kon nomi"><input className="input" value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <div className="flex flex-wrap gap-2 text-sm">
              <Badge tone="brand">{data.plan === "premium" ? "Premium tarif" : "Oddiy tarif"}</Badge>

            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Valyuta"><select className="input" value={s.currency} onChange={(e) => set("currency", e.target.value)}>
                {["UZS", "USD", "EUR", "RUB", "KZT"].map((c) => <option key={c}>{c}</option>)}</select></Field>
              <Field label="Vaqt zonasi"><select className="input" value={s.timezone} onChange={(e) => set("timezone", e.target.value)}>
                {["Asia/Tashkent", "Asia/Almaty", "Europe/Moscow", "Europe/Istanbul", "UTC"].map((c) => <option key={c}>{c}</option>)}</select></Field>
            </div>
          </div>
        </Card>

        <Card title={premium ? "Ko'rinish" : "Vidjet ko'rinishi"}>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Til"><select className="input" value={s.language} onChange={(e) => set("language", e.target.value)}>
                <option value="uz">O'zbekcha</option><option value="ru">Русский</option><option value="en">English</option></select></Field>
              <Field label="Tugma joylashuvi" help="Qidiruv maydoni topilmasa"><select className="input" value={s.theme?.position} onChange={(e) => set("theme", { ...s.theme, position: e.target.value })}>
                <option value="bottom-right">Pastki o'ng</option><option value="bottom-left">Pastki chap</option></select></Field>
            </div>
            <Field label="Asosiy rang">
              <div className="flex items-center gap-3">
                <input type="color" className="h-10 w-14 cursor-pointer rounded-lg border border-line bg-surface p-1" value={s.theme?.primary || "#6d28d9"}
                  onChange={(e) => set("theme", { ...s.theme, primary: e.target.value })} />
                <input className="input font-mono" value={s.theme?.primary || ""} onChange={(e) => set("theme", { ...s.theme, primary: e.target.value })} />
                <span className="inline-flex h-10 flex-none items-center gap-2 rounded-full px-4 text-sm font-semibold text-white" style={{ background: s.theme?.primary }}>📷 Namuna</span>
              </div>
            </Field>
            {!premium && (
              <Field label="Qidiruv maydoni (agar kamera tugmasi o'z joyida chiqmasa)" help="Odatda bo'sh qoladi — tugma avtomatik joylashadi">
                <input className="input font-mono" value={s.search_selector || ""} onChange={(e) => set("search_selector", e.target.value)} placeholder="input[name=q]" />
              </Field>
            )}
          </div>
        </Card>

        <Card title="Analitika qoidalari">
          <div className="space-y-5">
            <Field label={`Qondirilmagan talab chegarasi: ${Math.round(s.unmet_threshold * 100)}%`} help="Eng yaxshi moslik bundan past bo'lsa, qidiruv 'qondirilmagan talab' deb belgilanadi">
              <input type="range" min={0.1} max={0.9} step={0.05} className="w-full accent-[rgb(var(--brand))]" value={s.unmet_threshold} onChange={(e) => set("unmet_threshold", Number(e.target.value))} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Qidiruvdan keyin xarid hisoblanadigan muddat (kun)" help="Shu kunlar ichidagi xarid rasm qidiruviga bog'lanadi">
                <input type="number" min={1} max={30} className="input" value={s.attribution_days} onChange={(e) => set("attribution_days", e.target.value)} />
              </Field>
              <Field label="Savat tashlangan deb hisoblash (soat)">
                <input type="number" min={1} max={168} className="input" value={s.abandon_after_hours} onChange={(e) => set("abandon_after_hours", e.target.value)} />
              </Field>
            </div>
            {!premium && (
              <Field label="Buyurtma tasdiqlanish sahifasi manzili" help="Saytingizda xariddan keyin ochiladigan sahifa, masalan: /checkout/order-received">
                <input className="input font-mono" value={s.thank_you_url_pattern || ""} onChange={(e) => set("thank_you_url_pattern", e.target.value)} />
              </Field>
            )}
          </div>
        </Card>

        <Card title="Maxfiylik">
          <div className="space-y-4">
            <Field label="Rozilik (consent) rejimi">
              <select className="input" value={s.consent_mode} onChange={(e) => set("consent_mode", e.target.value)}>
                <option value="implied">Avtomatik — anonim statistika yig'iladi</option>
                <option value="explicit">Aniq rozilik — xaridor rozilik bermaguncha kuzatuv yo'q</option>
              </select>
            </Field>
            {!premium && (
              <Field label="Xaridor sahifasiga havola (ixtiyoriy)" help="Xaridor bosilganda saytingiz admin panelidagi uning sahifasi ochiladi. {customer_ref} o'rniga xaridor ID'si qo'yiladi.">
                <input className="input font-mono" value={s.customer_deeplink || ""} onChange={(e) => set("customer_deeplink", e.target.value)} placeholder="https://shop.uz/admin/customers/{customer_ref}" />
              </Field>
            )}
            <ul className="space-y-1.5 rounded-lg bg-subtle p-3 text-xs text-muted">
              <li>• Xaridor yuklagan rasm saqlanmaydi — faqat tahlil qilinadi.</li>
              <li>• {premium ? "Xaridorlar ma'lumoti faqat sizning do'koningizda; tahlilga ism va telefon qo'shilmaydi." : "Xaridor ismi, e-mail va telefoni qabul qilinmaydi — faqat ichki ID (customer_ref)."}</li>
              <li>• IP manzil to'liq saqlanmaydi; batafsil faollik 13 oydan keyin avtomatik o'chiriladi.</li>
            </ul>
          </div>
        </Card>
      </div>
    </>
  );
}


const FEATURES: [string, boolean, boolean][] = [
  ["Rasm orqali qidiruv", true, true],
  ["Analitika: voronka, talab, savatlar, Excel", true, true],
  ["Auditoriya va shaxsiy takliflar", true, true],
  ["Mijozlar ro'yxati", true, true],
  ["O'z saytingizga ulash (vidjet)", true, false],
  ["Tayyor onlayn do'kon (sayt)", false, true],
  ["Mahsulot qo'shish va rasm yuklash", false, true],
  ["Buyurtmalar, to'lov, yetkazib berish", false, true],
  ["Xaridorlar kontakti (aksiyalarga rozilar)", false, true],
];

function PlanCard({ plan }: { plan: string }) {
  const premium = plan === "premium";
  return (
    <div className="card mb-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted">Tarifingiz</p>
          <p className="text-xl font-semibold">{premium ? "Premium — do'kon + analitika" : "Oddiy — analitika"}</p>
        </div>
        <Badge tone={premium ? "brand" : "neutral"}>{premium ? "Premium" : "Oddiy"}</Badge>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[460px] text-sm">
          <thead><tr className="border-b border-line text-left text-xs text-muted">
            <th className="py-2 font-medium">Imkoniyat</th>
            <th className={`py-2 text-center font-medium ${!premium ? "text-brand" : ""}`}>Oddiy</th>
            <th className={`py-2 text-center font-medium ${premium ? "text-brand" : ""}`}>Premium</th>
          </tr></thead>
          <tbody className="divide-y divide-line">
            {FEATURES.map(([f, b, p]) => (
              <tr key={f}><td className="py-2">{f}</td>
                <td className="py-2 text-center">{b ? <span className="text-ok">✓</span> : <span className="text-muted">—</span>}</td>
                <td className="py-2 text-center">{p ? <span className="text-ok">✓</span> : <span className="text-muted">—</span>}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-muted">Tarifni o'zgartirish uchun platforma administratoriga murojaat qiling.</p>
    </div>
  );
}
