"use client";

import { Contact, Search, ShieldCheck, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Badge, Card, Empty, PageHeader, Pagination, Skeleton } from "@/components/ui";
import { money, num, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";

type Row = {
  customer_ref: string; full_name: string | null; email: string | null; phone: string | null; city: string | null;
  marketing_consent: boolean | null; registered_at: string | null; last_seen: string | null; sessions: number; searches: number;
  carts: number; purchases: number; revenue_minor: number; abandoned_minor: number; orders: number; spent_minor: number;
  interests: string[]; segments: string[];
};

function CustomersInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const ref = sp.get("ref") || "";
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { const t = setTimeout(() => { setQuery(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);
  const { data } = useApi<{ total: number; premium: boolean; items: Row[] }>(
    `/v1/dashboard/customers?page=${page}&size=25${ref ? `&ref=${encodeURIComponent(ref)}` : `&q=${encodeURIComponent(query)}`}`);
  const premium = data?.premium;

  return (
    <>
      <PageHeader title="Mijozlar"
        description={premium ? "Do'koningiz xaridorlari: kontakt, buyurtmalar va qiziqishlar"
          : "Saytingizda tanilgan xaridorlar (customer_ref). Ism va telefon sizning tizimingizda — bu yerga uzatilmaydi."} />
      {ref && (
        <div className="mb-4 flex items-center gap-2 text-sm">
          <Badge tone="brand">customer_ref: {ref}</Badge>
          <button className="btn-ghost h-7 px-2 text-xs" onClick={() => router.push("/customers")}><X className="h-3.5 w-3.5" />Barchasi</button>
        </div>
      )}
      <Card pad={false} title={data ? `${num(data.total)} ta xaridor` : "Xaridorlar"}
        actions={!ref && <div className="relative w-64"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input className="input h-9 pl-9" placeholder={premium ? "customer_ref, ism, telefon…" : "customer_ref…"} value={q} onChange={(e) => setQ(e.target.value)} /></div>}>
        {!data ? <div className="p-5"><Skeleton className="h-60" /></div> : data.items.length === 0 ? (
          <Empty icon={<Contact className="h-6 w-6" />} title="Xaridor topilmadi"
            text={premium ? "Xaridorlar do'konda ro'yxatdan o'tganda yoki buyurtma berganda shu yerda paydo bo'ladi."
              : "Saytingizda xaridor tizimga kirganda vidjet uning ichki ID'sini (customer_ref) bog'laydi — shundan keyin shu yerda ko'rinadi."} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead className="border-b border-line bg-subtle/50"><tr>
                  <th className="th">Xaridor</th>
                  {premium && <th className="th">Aloqa</th>}
                  <th className="th">Qiziqishlari</th>
                  <th className="th text-right">Qidiruv / savat</th>
                  <th className="th text-right">{premium ? "Buyurtmalar" : "Xaridlar"}</th>
                  <th className="th text-right">Summa</th>
                  <th className="th">Oxirgi faollik</th>
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {data.items.map((c) => (
                    <tr key={c.customer_ref} className="align-top hover:bg-subtle/40">
                      <td className="td">
                        {c.full_name && <p className="font-medium">{c.full_name}</p>}
                        <code className="rounded bg-subtle px-1.5 py-0.5 text-xs">{c.customer_ref}</code>
                        <div className="mt-1 flex flex-wrap gap-1">{c.segments.slice(0, 2).map((s) => <Badge key={s}>{s}</Badge>)}</div>
                      </td>
                      {premium && (
                        <td className="td text-sm">
                          {c.phone || c.email ? <><p>{c.phone || "—"}</p><p className="text-xs text-muted">{c.email}</p></> : <span className="text-muted">mehmon</span>}
                          {c.marketing_consent && <p className="mt-1 flex items-center gap-1 text-xs text-ok"><ShieldCheck className="h-3 w-3" />aksiyalarga rozi</p>}
                        </td>
                      )}
                      <td className="td text-sm capitalize">{c.interests.length ? c.interests.join(", ") : <span className="text-muted">—</span>}</td>
                      <td className="td text-right tabular-nums text-sm">{c.searches} / {c.carts}</td>
                      <td className="td text-right tabular-nums">{premium ? c.orders : c.purchases}</td>
                      <td className="td text-right font-medium tabular-nums">{money(premium ? c.spent_minor || c.revenue_minor : c.revenue_minor)}
                        {c.abandoned_minor > 0 && <span className="block text-xs font-normal text-bad">tashlangan: {money(c.abandoned_minor, "UZS", true)}</span>}</td>
                      <td className="td whitespace-nowrap text-sm text-muted">{timeAgo(c.last_seen || c.registered_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} size={25} total={data.total} onPage={setPage} />
          </>
        )}
      </Card>
      <p className="mt-3 text-xs text-muted">Qiziqish va faollik har 15 daqiqada yangilanadi (Auditoriya → "Qayta hisoblash" bilan darhol).</p>
    </>
  );
}

export default function CustomersPage() {
  return <Suspense><CustomersInner /></Suspense>;
}
