"use client";

import { ArrowRight, Camera, Percent, ShoppingCart, TrendingDown, Users, Wallet, Target, Timer } from "lucide-react";
import Link from "next/link";
import { Funnel, TrendChart } from "@/components/charts";
import { ExcelButton } from "@/components/ExportButton";
import { RangePicker } from "@/components/RangePicker";
import { Badge, Card, Empty, ErrorBox, Kpi, PageHeader, Skeleton } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { can, money, num, pct } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

function sumMoney(items: { currency: string; amount_minor: number }[] | undefined, currency: string) {
  return (items || []).filter((i) => i.currency === currency).reduce((a, i) => a + i.amount_minor, 0);
}

export default function OverviewPage() {
  const { tenant } = useAuth();
  const { qs } = useRange();
  const { data, error, isLoading, mutate } = useApi<any>(tenant ? `/v1/dashboard/analytics/overview?${qs}` : null);
  const funnel = useApi<any>(tenant ? `/v1/dashboard/analytics/funnel?${qs}` : null);
  const demand = useApi<any>(tenant && can(tenant.role, "analyst") ? `/v1/dashboard/analytics/demand?${qs}` : null);

  if (!tenant) return <Empty title="Do'kon tanlanmagan" text="Platforma admin bo'limidan do'kon yarating yoki sizni do'konga taklif qilishlarini so'rang." />;

  const k = data?.kpis;
  const d = data?.deltas || {};
  const cur = data?.currency || "UZS";
  const loading = isLoading && !data;

  return (
    <>
      <PageHeader title="Umumiy ko'rinish" description="Rasm orqali qidiruvdan sotuvgacha bo'lgan asosiy ko'rsatkichlar" actions={<><RangePicker /><ExcelButton label="Excel yuklab olish" /></>} />
      {error && <div className="mb-4"><ErrorBox error={error} retry={() => mutate()} /></div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="AI qidiruvlar" icon={<Camera className="h-4 w-4" />} loading={loading} value={num(k?.searches)} delta={d.searches}
          hint={k ? `${num(k.from_cache)} keshdan` : undefined} />
        <Kpi label="Savatga qo'shildi" icon={<ShoppingCart className="h-4 w-4" />} loading={loading} value={num(k?.add_to_cart)} delta={d.add_to_cart}
          hint={k ? `${pct(k.cart_rate_pct)} qidiruvdan` : undefined} />
        <Kpi label="Yo'qotilgan daromad" icon={<TrendingDown className="h-4 w-4" />} loading={loading} inverse
          value={money(sumMoney(k?.lost_revenue, cur), cur, true)} delta={d.lost_revenue}
          hint={k ? `${num((k.lost_revenue || []).reduce((a: number, x: any) => a + x.carts, 0))} savat` : undefined} />
        <Kpi label="Konversiya" icon={<Percent className="h-4 w-4" />} loading={loading} value={pct(k?.conversion_pct, 2)} delta={d.conversion_pct}
          hint={k ? `${num(k.purchases)} xarid` : undefined} />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { icon: Wallet, label: "Qidiruvdan kelgan daromad", value: money(sumMoney(k?.attributed_revenue, cur), cur, true), delta: d.attributed_revenue },
          { icon: Users, label: "Noyob qidiruvchilar", value: num(k?.searchers), delta: d.searchers },
          { icon: Target, label: "Qondirilmagan talab", value: num(k?.unmet_demand), delta: d.unmet_demand, inverse: true },
          { icon: Timer, label: "O'rtacha javob vaqti", value: k ? `${(k.avg_latency_ms / 1000).toFixed(1)} s` : "—" },
        ].map(({ icon: Icon, ...m }) => (
          <div key={m.label} className="card flex items-center gap-3 px-4 py-3.5">
            <Icon className="h-4 w-4 flex-none text-muted" />
            <span className="flex-1 truncate text-sm text-muted">{m.label}</span>
            {loading ? <Skeleton className="h-5 w-16" /> : <span className="font-semibold tabular-nums">{m.value}</span>}
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Kunlik dinamika" description="Qidiruvlar, savatga qo'shishlar va xaridlar (noyob qidiruvlar bo'yicha)" className="xl:col-span-2">
          {loading ? <Skeleton className="h-[300px]" /> : data?.kpis.searches === 0 ? (
            tenant.plan === "premium" ? (
              <Empty title="Bu davrda qidiruv yo'q" text="Do'koningizda xaridorlar rasm orqali qidirganda statistika shu yerda paydo bo'ladi."
                action={<a href={process.env.NEXT_PUBLIC_STOREFRONT_URL || "http://localhost:3001"} target="_blank" rel="noreferrer" className="btn-secondary">Do'konni ochish <ArrowRight className="h-4 w-4" /></a>} />
            ) : (
              <Empty title="Bu davrda qidiruv yo'q" text="Vidjet saytingizga ulanganini Integratsiya sahifasida tekshiring."
                action={<Link href="/integrations" className="btn-secondary">Integratsiya <ArrowRight className="h-4 w-4" /></Link>} />
            )
          ) : (
            <TrendChart data={data?.series || []} series={[
              { key: "searches", label: "Qidiruvlar", color: "var(--chart-1)" },
              { key: "add_to_cart", label: "Savatga", color: "var(--chart-2)" },
              { key: "purchases", label: "Xarid", color: "var(--chart-3)" },
            ]} />
          )}
        </Card>
        <Card title="Voronka" actions={<Link href="/funnel" className="text-sm font-medium text-brand hover:underline">Batafsil</Link>}>
          {funnel.data ? <Funnel steps={funnel.data.steps} compact /> : <Skeleton className="h-[260px]" />}
        </Card>
      </div>

      {can(tenant.role, "analyst") && (
        <Card className="mt-4" title="Eng ko'p qidirilgan, lekin do'konda yo'q" description="Katalogga qo'shish uchun imkoniyatlar"
          actions={<Link href="/demand" className="text-sm font-medium text-brand hover:underline">Hammasi</Link>} pad={false}>
          {!demand.data ? <div className="p-5"><Skeleton className="h-32" /></div> : demand.data.items.length === 0 ? (
            <Empty title="Qondirilmagan talab yo'q" text="Barcha qidiruvlarga mos mahsulot topildi." />
          ) : (
            <ul className="divide-y divide-line">
              {demand.data.items.slice(0, 5).map((it: any) => (
                <li key={it.demand_key} className="flex items-center gap-4 px-5 py-3">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium capitalize">{it.sample_query || it.demand_key}</span>
                    <span className="block truncate text-xs text-muted">{it.ai_suggestion}</span>
                  </span>
                  <Badge tone="brand">{num(it.search_count)} qidiruv</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </>
  );
}
