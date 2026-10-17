"use client";

import { Download, Lightbulb, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { RangePicker } from "@/components/RangePicker";
import { Badge, Card, Empty, ErrorBox, PageHeader, Skeleton, useToast } from "@/components/ui";
import { download } from "@/lib/api";
import { COLOR_HEX, dateTime, num } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

export default function DemandPage() {
  const { qs } = useRange();
  const toast = useToast();
  const { data, error, mutate } = useApi<any>(`/v1/dashboard/analytics/demand?${qs}`);
  const [q, setQ] = useState("");
  const items = useMemo(() => (data?.items || []).filter((i: any) =>
    !q || `${i.sample_query} ${i.demand_key}`.toLowerCase().includes(q.toLowerCase())), [data, q]);
  const max = Math.max(1, ...items.map((i: any) => i.search_count));

  return (
    <>
      <PageHeader title="Qondirilmagan talab" description="Xaridorlar qidirgan, lekin katalogingizda mos topilmagan mahsulotlar. Sinonimlar bitta talabga birlashtiriladi."
        actions={<>
          <RangePicker />
          <button className="btn-secondary" onClick={() => download(`/v1/dashboard/analytics/export/demand?${qs}`, "demand.csv").catch((e) => toast(e.message, "bad"))}>
            <Download className="h-4 w-4" />CSV
          </button>
        </>} />
      {error && <ErrorBox error={error} retry={() => mutate()} />}

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <div className="card p-5"><p className="text-sm text-muted">Jami qondirilmagan qidiruv</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.total_unmet) : "—"}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Noyob talablar</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.items.length) : "—"}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Eng talabgir</p><p className="mt-1 truncate text-2xl font-semibold capitalize">{data?.items[0]?.sample_query || "—"}</p></div>
      </div>

      <Card pad={false} title="Talablar ro'yxati" actions={
        <div className="relative w-56">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input className="input h-9 pl-9" placeholder="Qidirish…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>}>
        {!data ? <div className="space-y-3 p-5">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div> : items.length === 0 ? (
          <Empty title="Qondirilmagan talab topilmadi" text="Tanlangan davrda barcha qidiruvlarga mos mahsulot bor edi." />
        ) : (
          <ul className="divide-y divide-line">
            {items.map((it: any) => (
              <li key={it.demand_key} className="grid gap-3 px-5 py-4 md:grid-cols-[1fr_220px_auto] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {it.color && COLOR_HEX[it.color] && <span className="h-3.5 w-3.5 rounded-full ring-1 ring-line" style={{ background: COLOR_HEX[it.color] }} />}
                    <span className="font-medium capitalize">{it.sample_query || it.demand_key}</span>
                    {it.category && <Badge>{it.category}</Badge>}
                  </div>
                  <p className="mt-1.5 flex items-start gap-1.5 text-sm text-muted"><Lightbulb className="mt-0.5 h-3.5 w-3.5 flex-none text-warn" />{it.ai_suggestion}</p>
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs text-muted"><span>{num(it.unique_sessions)} xaridor</span><span>oxirgi: {dateTime(it.last_seen)}</span></div>
                  <div className="h-2 rounded-full bg-subtle"><div className="h-2 rounded-full" style={{ width: `${(it.search_count / max) * 100}%`, background: "var(--chart-seq)" }} /></div>
                </div>
                <div className="text-right"><span className="text-xl font-semibold tabular-nums">{num(it.search_count)}</span><span className="ml-1 text-xs text-muted">qidiruv</span></div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
