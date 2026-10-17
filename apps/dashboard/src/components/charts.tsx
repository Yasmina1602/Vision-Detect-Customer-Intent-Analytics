"use client";

import clsx from "clsx";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num, shortDate } from "@/lib/format";

export type Series = { key: string; label: string; color: string };

/** Vaqt bo'yicha dinamika: bir o'q, yupqa chiziqlar, crosshair + tooltip, legend (qiymatlar bilan). */
export function TrendChart({ data, series, height = 280 }: { data: Record<string, any>[]; series: Series[]; height?: number }) {
  const totals = Object.fromEntries(series.map((s) => [s.key, data.reduce((a, d) => a + (d[s.key] || 0), 0)]));
  return (
    <div>
      <ul className="mb-4 flex flex-wrap gap-x-5 gap-y-2" aria-label="Legend">
        {series.map((s) => (
          <li key={s.key} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="text-muted">{s.label}</span>
            <span className="font-semibold tabular-nums">{num(totals[s.key])}</span>
          </li>
        ))}
      </ul>
      <div style={{ height }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
            <defs>
              {series.map((s) => (
                <linearGradient key={s.key} id={`g-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={24} />
            <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={44} />
            <Tooltip
              cursor={{ stroke: "rgb(var(--muted))", strokeDasharray: "3 3" }}
              labelFormatter={(l) => shortDate(String(l))}
              formatter={(v: number, k: string) => [num(v), series.find((s) => s.key === k)?.label ?? k]}
            />
            {series.map((s) => (
              <Area key={s.key} type="monotone" dataKey={s.key} stroke={s.color} strokeWidth={2} fill={`url(#g-${s.key})`}
                dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "rgb(var(--surface))" }} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Bitta seriya ustunlar (masalan soatlik dinamika). */
export function Columns({ data, x, y, label, height = 220, format = (v: any) => String(v) }: {
  data: Record<string, any>[]; x: string; y: string; label: string; height?: number; format?: (v: any) => string;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -16 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis dataKey={x} tickLine={false} axisLine={false} tickFormatter={format} interval="preserveStartEnd" minTickGap={8} />
          <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={40} />
          <Tooltip cursor={{ fill: "rgb(var(--subtle))" }} labelFormatter={format} formatter={(v: number) => [num(v), label]} />
          <Bar dataKey={y} fill="var(--chart-seq)" radius={[4, 4, 0, 0]} maxBarSize={28} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Gorizontal ro'yxat-bar: nom + qiymat matnda, bar faqat kattalikni ko'rsatadi. */
export function BarList({ items, swatch, suffix }: {
  items: { name: string; value: number; sub?: string }[]; swatch?: (name: string) => string | undefined; suffix?: (v: number) => string;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="space-y-2.5">
      {items.map((it) => {
        const sw = swatch?.(it.name);
        return (
          <li key={it.name} className="group" title={`${it.name}: ${num(it.value)}`}>
            <div className="mb-1 flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-2">
                {swatch && <span className="h-3 w-3 flex-none rounded-full ring-1 ring-line" style={{ background: sw ?? "rgb(var(--subtle))" }} />}
                <span className="truncate capitalize">{it.name}</span>
                {it.sub && <span className="text-xs text-muted">{it.sub}</span>}
              </span>
              <span className="font-semibold tabular-nums">{suffix ? suffix(it.value) : num(it.value)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-subtle">
              <div className="h-full rounded-full transition-all group-hover:brightness-110" style={{ width: `${(it.value / max) * 100}%`, background: "var(--chart-seq)" }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export type FunnelStep = { key: string; label: string; count: number; pct_of_total: number; pct_of_prev: number; drop: number };

/** Voronka: har bosqich noyob search_id bo'yicha; bosqichdan bosqichga % va yo'qotish. */
export function Funnel({ steps, compact = false }: { steps: FunnelStep[]; compact?: boolean }) {
  const max = Math.max(1, steps[0]?.count ?? 1);
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => (
        <li key={s.key}>
          <div className="mb-1.5 flex items-baseline justify-between gap-3">
            <span className="flex items-center gap-2 text-sm font-medium">
              <span className="grid h-5 w-5 place-items-center rounded-full bg-subtle text-[11px] font-semibold text-muted">{i + 1}</span>
              {s.label}
            </span>
            <span className="text-sm tabular-nums">
              <span className="font-semibold">{num(s.count)}</span>
              <span className="ml-2 text-muted">{s.pct_of_total}%</span>
            </span>
          </div>
          <div className={clsx("overflow-hidden rounded-lg bg-subtle", compact ? "h-2.5" : "h-8")}>
            <div className="flex h-full items-center rounded-lg px-2.5 text-xs font-semibold text-white transition-all"
              style={{ width: `${Math.max((s.count / max) * 100, s.count ? 2 : 0)}%`, background: "var(--chart-seq)", opacity: 1 - i * 0.12 }}>
              {!compact && s.count / max > 0.12 ? `${s.pct_of_total}%` : ""}
            </div>
          </div>
          {!compact && i > 0 && s.drop > 0 && (
            <p className="mt-1 text-xs text-muted">
              Oldingi bosqichdan <b className="text-ink">{s.pct_of_prev}%</b> o'tdi · <span className="text-bad">−{num(s.drop)}</span> yo'qotildi
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
