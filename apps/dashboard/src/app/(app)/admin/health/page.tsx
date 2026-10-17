"use client";

import { Activity, Clock, Database, HardDrive, Sparkles, Zap } from "lucide-react";
import { Badge, Card, PageHeader, Skeleton } from "@/components/ui";
import { num } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function HealthPage() {
  const { data } = useApi<any>("/v1/admin/health", { refreshInterval: 15000 });
  const tiles = data ? [
    { icon: Database, label: "Ma'lumotlar bazasi", value: data.database === "ok" ? "Ishlayapti" : "Xato", tone: data.database === "ok" ? "ok" : "bad" },
    { icon: HardDrive, label: "Kesh", value: data.cache_backend === "redis" ? "Redis" : "Xotira (Redis yo'q)", tone: data.cache_backend === "redis" ? "ok" : "warn" },
    { icon: Sparkles, label: "Vision", value: data.vision_mode === "gemini" ? "Gemini" : "Demo rejim", tone: data.vision_mode === "gemini" ? (data.all_models_cooling ? "bad" : "ok") : "warn" },
    { icon: Activity, label: "Qidiruvlar (24 soat)", value: num(data.searches_24h) },
    { icon: Clock, label: "p95 javob vaqti", value: data.p95_latency_ms ? `${(data.p95_latency_ms / 1000).toFixed(2)} s` : "—", tone: data.p95_latency_ms > 6000 ? "bad" : "ok" },
    { icon: Zap, label: "Kesh hit-rate", value: `${data.cache_hit_rate_pct}%` },
  ] : [];

  return (
    <>
      <PageHeader title="Tizim holati" description="Har 15 soniyada yangilanadi" />
      {data?.all_models_cooling && <div className="mb-4 rounded-xl bg-bad-soft px-4 py-3 text-sm font-medium text-bad">Barcha AI modellar sovumoqda — qidiruvlar 503 qaytaradi!</div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {!data ? [0, 1, 2].map((i) => <Skeleton key={i} className="h-24" />) : tiles.map(({ icon: Icon, label, value, tone }) => (
          <div key={label} className="card flex items-center gap-4 p-5">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-subtle text-muted"><Icon className="h-5 w-5" /></span>
            <div className="min-w-0 flex-1"><p className="text-sm text-muted">{label}</p><p className="text-lg font-semibold">{value}</p></div>
            {tone && <Badge tone={tone as any}>{tone === "ok" ? "OK" : tone === "warn" ? "Diqqat" : "Xato"}</Badge>}
          </div>
        ))}
      </div>
      <Card className="mt-4" title="Fon vazifalari (worker)">
        {!data ? <Skeleton className="h-32" /> : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {data.jobs.map((j: any) => (
              <li key={j.name} className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm">
                <span className="font-mono">{j.name}</span><span className="text-muted">har {j.interval_s >= 3600 ? `${j.interval_s / 3600} soat` : `${j.interval_s / 60} daq`}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
