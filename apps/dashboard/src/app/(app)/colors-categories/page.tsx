"use client";

import { BarList, Columns } from "@/components/charts";
import { ExcelButton } from "@/components/ExportButton";
import { RangePicker } from "@/components/RangePicker";
import { Card, Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { COLOR_HEX } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useRange } from "@/lib/range";

type Row = { name: string; count: number; unmet: number };

export default function ColorsPage() {
  const { qs } = useRange();
  const { data, error, mutate } = useApi<{ colors: Row[]; categories: Row[]; types: Row[]; hourly: { hour: number; count: number }[] }>(
    `/v1/dashboard/analytics/colors?${qs}`);
  const toItems = (rows: Row[]) => rows.map((r) => ({ name: r.name, value: r.count, sub: r.unmet ? `${r.unmet} topilmadi` : undefined }));
  const peak = data?.hourly.reduce((m, h) => (h.count > m.count ? h : m), { hour: 0, count: 0 });

  return (
    <>
      <PageHeader title="Rang va kategoriyalar" description="Xaridorlar qaysi rang, kategoriya va mahsulot turlarini ko'proq qidirmoqda" actions={<><RangePicker /><ExcelButton label="Excel yuklab olish" /></>} />
      {error && <ErrorBox error={error} retry={() => mutate()} />}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Ranglar">
          {!data ? <Skeleton className="h-72" /> : data.colors.length ? <BarList items={toItems(data.colors)} swatch={(n) => COLOR_HEX[n]} /> : <Empty title="Ma'lumot yo'q" />}
        </Card>
        <Card title="Kategoriyalar">
          {!data ? <Skeleton className="h-72" /> : data.categories.length ? <BarList items={toItems(data.categories)} /> : <Empty title="Ma'lumot yo'q" />}
        </Card>
        <Card title="Mahsulot turlari">
          {!data ? <Skeleton className="h-72" /> : data.types.length ? <BarList items={toItems(data.types)} /> : <Empty title="Ma'lumot yo'q" />}
        </Card>
      </div>
      <Card className="mt-4" title="Soatlik dinamika" description={peak && peak.count ? `Eng faol vaqt: ${String(peak.hour).padStart(2, "0")}:00 (do'kon vaqt zonasida)` : "Do'kon vaqt zonasida"}>
        {!data ? <Skeleton className="h-56" /> : <Columns data={data.hourly} x="hour" y="count" label="Qidiruvlar" format={(h) => `${String(h).padStart(2, "0")}:00`} />}
      </Card>
    </>
  );
}
