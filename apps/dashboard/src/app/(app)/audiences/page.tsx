"use client";

import clsx from "clsx";
import { Download, ExternalLink, Megaphone, RefreshCw, ShieldCheck, UsersRound } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge, Card, Empty, PageHeader, Pagination, Skeleton, Spinner, useToast } from "@/components/ui";
import { api, download } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, num, timeAgo, img } from "@/lib/format";
import { useApi } from "@/lib/hooks";

type Seg = { key: string; label: string; size: number; identified: number; abandoned_minor: number };

const GROUPS: [string, (k: string) => boolean][] = [
  ["Xatti-harakat", (k) => !k.includes(":")],
  ["Qiziqish (kategoriya)", (k) => k.startsWith("interest:")],
  ["Mahsulot turi", (k) => k.startsWith("type:")],
  ["Rang", (k) => k.startsWith("color:")],
  ["Topa olmagan talab", (k) => k.startsWith("unmet:")],
];

export default function AudiencesPage() {
  const toast = useToast();
  const { tenant } = useAuth();
  const { data, mutate } = useApi<{ total_profiles: number; identified: number; updated_at: string | null; segments: Seg[] }>("/v1/dashboard/audiences");
  const [segment, setSegment] = useState("all");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const profiles = useApi<any>(`/v1/dashboard/audiences/profiles?segment=${encodeURIComponent(segment)}&page=${page}&size=20`);
  const current = data?.segments.find((s) => s.key === segment);

  return (
    <>
      <PageHeader title="Auditoriya" description="Har bir xaridorning qiziqishlari — qidiruv, bosish, savat va xarid asosida. Shaxsiy ma'lumot (ism, telefon) ishlatilmaydi."
        actions={<>
          <button className="btn-secondary" disabled={busy} onClick={async () => {
            setBusy(true);
            try { const r = await api("/v1/dashboard/audiences/rebuild", { method: "POST" }); toast(`${r.profiles} ta profil yangilandi`); mutate(); profiles.mutate(); }
            catch (e: any) { toast(e.message, "bad"); } finally { setBusy(false); }
          }}>{busy ? <Spinner /> : <RefreshCw className="h-4 w-4" />}Qayta hisoblash</button>
          <Link href={`/campaigns?segment=${encodeURIComponent(segment)}`} className="btn-primary"><Megaphone className="h-4 w-4" />Kampaniya</Link>
        </>} />

      <Card className="mb-4" title="Har bir xaridorga mos taklif qanday yuboriladi?">
        <div className="grid gap-4 text-sm md:grid-cols-3">
          {(tenant?.plan === "premium" ? [
            ["1. Do'kondagi banner", "Xaridor do'koningizga kirganda unga qiziqishiga mos mahsulotlar va aksiya ko'rsatiladi — hatto ro'yxatdan o'tmagan bo'lsa ham."],
            ["2. SMS / e-mail ro'yxati", "Aksiyalarga rozi bo'lgan xaridorlar telefon va e-mail bilan yuklab olinadi, har biriga mos mahsulotlar bilan."],
            ["3. Mijozlar sahifasi", "Har bir xaridorning qiziqishlari, savati va xaridlari Mijozlar bo'limida ko'rinadi."],
          ] : [
            ["1. Saytdagi banner", "Saytingizga kirgan xaridorga uning qiziqishiga mos mahsulotlar va aksiya ko'rsatiladi — anonim mehmonga ham."],
            ["2. Sizning tizimingiz orqali", "Xaridor ro'yxati uning ID'si bilan beriladi. Telefon va e-mail sizning bazangizda — xabarni o'zingiz yuborasiz."],
            ["3. Ro'yxatni yuklab olish", "Segmentni faylga olib, SMS-xizmat yoki reklama kabinetiga yuklaysiz."],
          ]).map(([t, d]) => (
            <div key={t} className="rounded-xl bg-subtle p-4"><p className="font-semibold">{t}</p><p className="mt-1 text-muted">{d}</p></div>
          ))}
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs text-muted"><ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-ok" />
          Qiziqish xaridorning qidiruvlari, ko'rgan va savatga solgan mahsulotlaridan avtomatik aniqlanadi. Shaxsiy ma'lumot tahlil uchun ishlatilmaydi.</p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-5"><p className="text-sm text-muted">Profillar</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.total_profiles) : "—"}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Tanilgan (customer_ref bor)</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.identified) : "—"}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Oxirgi hisob</p><p className="mt-1 text-2xl font-semibold">{data?.updated_at ? timeAgo(data.updated_at) : "—"}</p><p className="text-xs text-muted">har 15 daqiqada avtomatik</p></div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[340px_1fr]">
        <Card title="Segmentlar" pad={false}>
          {!data ? <div className="p-5"><Skeleton className="h-80" /></div> : data.segments.length === 0 ? (
            <Empty icon={<UsersRound className="h-6 w-6" />} title="Hali profil yo'q" text="Vidjet orqali qidiruv va xaridlar kelgach, 'Qayta hisoblash' tugmasini bosing." />
          ) : (
            <div className="max-h-[640px] overflow-y-auto p-2">
              <button onClick={() => { setSegment("all"); setPage(1); }} className={clsx("mb-1 flex w-full justify-between rounded-lg px-3 py-2 text-sm", segment === "all" ? "bg-brand-soft font-semibold text-brand-ink dark:text-brand" : "hover:bg-subtle")}>
                Barcha profillar<span>{num(data.total_profiles)}</span></button>
              {GROUPS.map(([title, test]) => {
                const segs = data.segments.filter((s) => test(s.key));
                if (!segs.length) return null;
                return (
                  <div key={title} className="mt-3">
                    <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">{title}</p>
                    {segs.slice(0, 12).map((s) => (
                      <button key={s.key} onClick={() => { setSegment(s.key); setPage(1); }}
                        className={clsx("flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm", segment === s.key ? "bg-brand-soft font-semibold text-brand-ink dark:text-brand" : "hover:bg-subtle")}>
                        <span className="truncate capitalize">{s.label.replace(/^(Qiziqish|Rang|Tur|Topilmagan): /, "")}</span>
                        <span className="flex-none tabular-nums text-muted">{num(s.size)}</span>
                      </button>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card pad={false} title={current ? current.label : "Barcha profillar"}
          description={current ? `${num(current.size)} profil · ${num(current.identified)} tanilgan${current.abandoned_minor ? ` · tashlangan savat ${money(current.abandoned_minor, "UZS", true)}` : ""}` : undefined}
          actions={<button className="btn-secondary h-8 text-xs" onClick={() => download(`/v1/dashboard/audiences/export?segment=${encodeURIComponent(segment)}`, "auditoriya.csv").catch((e) => toast(e.message, "bad"))}>
            <Download className="h-3.5 w-3.5" />CSV</button>}>
          {!profiles.data ? <div className="p-5"><Skeleton className="h-80" /></div> : profiles.data.items.length === 0 ? <Empty title="Bu segmentda profil yo'q" /> : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px]">
                  <thead className="border-b border-line bg-subtle/50"><tr>
                    <th className="th">Xaridor</th><th className="th">Qiziqishlar</th><th className="th">Faollik</th><th className="th">Tavsiya etiladi</th><th className="th">Oxirgi</th>
                  </tr></thead>
                  <tbody className="divide-y divide-line">
                    {profiles.data.items.map((p: any) => (
                      <tr key={p.key} className="align-top hover:bg-subtle/40">
                        <td className="td">
                          {p.customer_link ? <a href={p.customer_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-brand hover:underline">{p.label}<ExternalLink className="h-3 w-3" /></a>
                            : <span className={p.customer_ref ? "font-medium" : "text-muted"}>{p.label}</span>}
                          <div className="mt-1 flex flex-wrap gap-1">{p.segments.slice(0, 3).map((s: any) => <Badge key={s.key}>{s.label}</Badge>)}</div>
                        </td>
                        <td className="td text-xs">
                          {(["category", "type", "color"] as const).map((d) => p.interests[d]?.length ? <p key={d} className="capitalize">{p.interests[d].join(", ")}</p> : null)}
                        </td>
                        <td className="td whitespace-nowrap text-xs text-muted">{p.searches} qidiruv · {p.clicks} bosish<br />{p.carts} savat · {p.purchases} xarid
                          {p.revenue_minor > 0 && <><br /><span className="text-ok">{money(p.revenue_minor, "UZS", true)}</span></>}</td>
                        <td className="td">
                          <div className="flex -space-x-2">{p.recommended.map((r: any) => r.image_url && <img key={r.id} src={img(r.image_url)} alt={r.name} title={r.name} className="h-9 w-9 rounded-lg border-2 border-surface object-cover" />)}</div>
                        </td>
                        <td className="td whitespace-nowrap text-xs text-muted">{timeAgo(p.last_seen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={page} size={20} total={profiles.data.total} onPage={setPage} />
            </>
          )}
        </Card>
      </div>
    </>
  );
}
