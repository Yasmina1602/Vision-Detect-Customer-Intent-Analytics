"use client";

import { Info } from "lucide-react";
import { Funnel, FunnelStep } from "@/components/charts";
import { ExcelButton } from "@/components/ExportButton";
import { RangePicker } from "@/components/RangePicker";
import { Card, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { num } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

export default function FunnelPage() {
  const { qs } = useRange();
  const { data, error, mutate } = useApi<{ steps: FunnelStep[]; no_results: number }>(`/v1/dashboard/analytics/funnel?${qs}`);
  const steps = data?.steps || [];
  const biggest = steps.slice(1).reduce<FunnelStep | null>((m, s) => (!m || s.drop > m.drop ? s : m), null);

  return (
    <>
      <PageHeader title="Konversiya voronkasi" description="Har bosqich noyob qidiruv (search_id) bo'yicha hisoblanadi" actions={<><RangePicker /><ExcelButton label="Excel yuklab olish" /></>} />
      {error && <ErrorBox error={error} retry={() => mutate()} />}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Qidirdi → Xarid qildi" className="lg:col-span-2">
          {data ? <Funnel steps={steps} /> : <Skeleton className="h-80" />}
        </Card>
        <div className="space-y-4">
          <Card title="Eng katta yo'qotish">
            {biggest ? (
              <>
                <p className="text-3xl font-semibold tabular-nums text-bad">−{num(biggest.drop)}</p>
                <p className="mt-1 text-sm text-muted">"{steps[steps.indexOf(biggest) - 1]?.label}" → "{biggest.label}" bosqichida</p>
                <p className="mt-4 rounded-lg bg-subtle p-3 text-sm">
                  {biggest.key === "viewed" && "Natija chiqmagan qidiruvlar ko'p — katalogni boyiting yoki threshold'ni pasaytiring."}
                  {biggest.key === "clicked" && "Natijalar bor, lekin bosilmayapti — rasm sifati va narxlarni tekshiring."}
                  {biggest.key === "carted" && "Mahsulot ko'rilmoqda, lekin savatga tushmayapti — mavjudlik va narxni tekshiring."}
                  {biggest.key === "purchased" && "Savat tashlab ketilmoqda — Tashlab ketilgan savat bo'limida promo tavsiyalarni ko'ring."}
                </p>
              </>
            ) : <Skeleton className="h-24" />}
          </Card>
          <Card title="Natijasiz qidiruvlar">
            <p className="text-3xl font-semibold tabular-nums">{data ? num(data.no_results) : "—"}</p>
            <p className="mt-1 text-sm text-muted">Hech qanday mos mahsulot ko'rsatilmagan qidiruvlar</p>
          </Card>
          <div className="flex gap-2 rounded-xl border border-line p-3 text-xs text-muted">
            <Info className="h-4 w-4 flex-none" />
            Xarid atribusiyasi: last-touch, sozlamalardagi oyna ichida (default 7 kun). Asosiy manba — server webhook.
          </div>
        </div>
      </div>
      {data && (
        <Card className="mt-4" title="Jadval ko'rinishi" pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-line bg-subtle/50"><tr>
                <th className="th">Bosqich</th><th className="th text-right">Soni</th><th className="th text-right">Jamidan %</th><th className="th text-right">Oldingidan %</th><th className="th text-right">Yo'qotish</th>
              </tr></thead>
              <tbody className="divide-y divide-line">
                {steps.map((s) => (
                  <tr key={s.key}>
                    <td className="td font-medium">{s.label}</td>
                    <td className="td text-right tabular-nums">{num(s.count)}</td>
                    <td className="td text-right tabular-nums">{s.pct_of_total}%</td>
                    <td className="td text-right tabular-nums">{s.pct_of_prev}%</td>
                    <td className="td text-right tabular-nums text-muted">{s.drop ? `−${num(s.drop)}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
