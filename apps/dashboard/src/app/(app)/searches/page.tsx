"use client";

import { Download, RefreshCw, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { RangePicker } from "@/components/RangePicker";
import { Badge, Card, Empty, ErrorBox, PageHeader, Pagination, Skeleton, Tabs, useToast } from "@/components/ui";
import { download } from "@/lib/api";
import { COLOR_HEX, dateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

export default function SearchesPage() {
  const { qs } = useRange();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<"all" | "unmet">("all");
  const [live, setLive] = useState(false);
  useEffect(() => setPage(1), [qs, filter]);
  const { data, error, mutate, isValidating } = useApi<any>(
    `/v1/dashboard/analytics/searches?${qs}&page=${page}&size=25${filter === "unmet" ? "&unmet=true" : ""}`,
    { refreshInterval: live ? 5000 : 0 });

  return (
    <>
      <PageHeader title="Qidiruvlar jurnali" description="Har bir rasm qidiruvi: AI nimani aniqladi va katalogdan qanchalik mos topildi"
        actions={<>
          <RangePicker />
          <button className="btn-secondary" onClick={() => download(`/v1/dashboard/analytics/export/searches?${qs}`, "searches.csv").catch((e) => toast(e.message, "bad"))}>
            <Download className="h-4 w-4" />CSV
          </button>
        </>} />
      {error && <ErrorBox error={error} retry={() => mutate()} />}
      <Card pad={false} title={<Tabs value={filter} onChange={setFilter} items={[{ value: "all", label: "Hammasi" }, { value: "unmet", label: "Qondirilmagan" }]} />}
        actions={
          <div className="flex items-center gap-2">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
              <input type="checkbox" className="accent-[rgb(var(--brand))]" checked={live} onChange={(e) => setLive(e.target.checked)} />
              Real-time
              {live && <span className="h-2 w-2 animate-pulse rounded-full bg-ok" />}
            </label>
            <button className="btn-ghost h-8 w-8 px-0" onClick={() => mutate()} aria-label="Yangilash"><RefreshCw className={`h-4 w-4 ${isValidating ? "animate-spin" : ""}`} /></button>
          </div>}>
        {!data ? <div className="space-y-2 p-5">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10" />)}</div> : data.items.length === 0 ? (
          <Empty title="Qidiruv topilmadi" text="Tanlangan davr va filtr bo'yicha yozuv yo'q." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px]">
                <thead className="border-b border-line bg-subtle/50"><tr>
                  <th className="th">Vaqt</th><th className="th">Aniqlangan</th><th className="th">So'rov</th>
                  <th className="th text-right">Moslik</th><th className="th text-right">Natija</th><th className="th">Model</th><th className="th text-right">Vaqt</th>
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {data.items.map((s: any) => (
                    <tr key={s.id} className="hover:bg-subtle/40">
                      <td className="td whitespace-nowrap text-muted">{dateTime(s.created_at)}</td>
                      <td className="td">
                        <div className="flex items-center gap-2">
                          {s.color && <span className="h-3 w-3 rounded-full ring-1 ring-line" style={{ background: COLOR_HEX[s.color] || "rgb(var(--subtle))" }} title={s.color} />}
                          <span className="capitalize">{[s.color, s.type].filter(Boolean).join(" ")}</span>
                          {s.category && <Badge>{s.category}</Badge>}
                        </div>
                      </td>
                      <td className="td max-w-[220px] truncate text-muted">{s.query}</td>
                      <td className="td text-right tabular-nums">
                        <span className={s.unmet ? "text-bad" : "text-ok"}>{s.best_score != null ? Math.round(s.best_score * 100) + "%" : "—"}</span>
                      </td>
                      <td className="td text-right">{s.unmet ? <Badge tone="bad">topilmadi</Badge> : <span className="tabular-nums">{s.results}</span>}</td>
                      <td className="td whitespace-nowrap text-xs text-muted">{s.model}{s.from_cache && <Badge tone="ok" className="ml-1.5"><Zap className="h-3 w-3" />kesh</Badge>}</td>
                      <td className="td text-right tabular-nums text-muted">{s.latency_ms != null ? `${(s.latency_ms / 1000).toFixed(1)}s` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} size={25} total={data.total} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
