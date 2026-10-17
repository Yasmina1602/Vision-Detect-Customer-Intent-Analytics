"use client";

import { Download, ExternalLink, Sparkles } from "lucide-react";
import { BarList } from "@/components/charts";
import { RangePicker } from "@/components/RangePicker";
import { Badge, Card, Empty, ErrorBox, PageHeader, Skeleton, useToast } from "@/components/ui";
import { download } from "@/lib/api";
import { money, num, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

export default function CartsPage() {
  const { qs } = useRange();
  const toast = useToast();
  const { data, error, mutate } = useApi<any>(`/v1/dashboard/analytics/carts?${qs}`);
  const cur = data?.currency || "UZS";

  return (
    <>
      <PageHeader title="Tashlab ketilgan savatlar" description="Savatga qo'shilgan, lekin belgilangan vaqt ichida sotib olinmagan mahsulotlar"
        actions={<>
          <RangePicker />
          <button className="btn-secondary" onClick={() => download(`/v1/dashboard/analytics/export/carts?${qs}`, "carts.csv").catch((e) => toast(e.message, "bad"))}>
            <Download className="h-4 w-4" />CSV
          </button>
        </>} />
      {error && <ErrorBox error={error} retry={() => mutate()} />}

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <div className="card p-5">
          <p className="text-sm text-muted">Yo'qotilgan summa</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-bad">{data ? money(data.total_lost_minor, cur) : "—"}</p>
        </div>
        <div className="card p-5"><p className="text-sm text-muted">Tashlab ketilgan savatlar</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.abandoned_count) : "—"}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Hozir ochiq savatlar</p><p className="mt-1 text-2xl font-semibold tabular-nums">{data ? num(data.open_count) : "—"}</p></div>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card title="Mahsulot bo'yicha yo'qotish" description="Promo taklif qilish uchun nomzodlar" className="lg:col-span-2">
          {!data ? <Skeleton className="h-64" /> : data.products.length === 0 ? <Empty title="Yo'qotish yo'q" /> : (
            <>
              <BarList items={data.products.slice(0, 8).map((p: any) => ({ name: p.name || `#${p.product_id}`, value: p.amount_minor, sub: `${p.carts} savat` }))}
                suffix={(v) => money(v, cur, true)} />
              <div className="mt-5 flex gap-2 rounded-lg bg-brand-soft p-3 text-sm text-brand-ink dark:text-brand">
                <Sparkles className="h-4 w-4 flex-none" />
                <span><b>{data.products[0]?.name}</b> eng ko'p tashlab ketilmoqda — 5–10% chegirma yoki bepul yetkazib berish taklif qiling.</span>
              </div>
            </>
          )}
        </Card>

        <Card title="Savatlar" pad={false} className="lg:col-span-3">
          {!data ? <div className="p-5"><Skeleton className="h-64" /></div> : data.carts.length === 0 ? <Empty title="Tashlab ketilgan savat yo'q" /> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-line bg-subtle/50"><tr>
                  <th className="th">Xaridor</th><th className="th">Mahsulotlar</th><th className="th text-right">Summa</th><th className="th">Oxirgi faollik</th>
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {data.carts.slice(0, 50).map((c: any) => (
                    <tr key={c.id} className="hover:bg-subtle/40">
                      <td className="td">
                        {c.customer_link ? (
                          <a href={c.customer_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
                            {c.customer}<ExternalLink className="h-3 w-3" /></a>
                        ) : <span className="text-muted">{c.customer}</span>}
                        {c.from_search && <Badge tone="brand" className="ml-2">qidiruvdan</Badge>}
                      </td>
                      <td className="td max-w-[260px] truncate">{c.items.map((i: any) => `${i.name || "#" + i.id} ×${i.qty}`).join(", ")}</td>
                      <td className="td text-right font-semibold tabular-nums">{money(c.total_minor, c.currency || cur)}</td>
                      <td className="td whitespace-nowrap text-muted">{timeAgo(c.last_activity_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
