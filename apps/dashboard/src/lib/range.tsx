"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Range = { from: string; to: string; preset: string };

const Ctx = createContext<{ range: Range; setRange: (r: Range) => void; qs: string } | null>(null);

export const PRESETS: { key: string; label: string; days: number }[] = [
  { key: "today", label: "Bugun", days: 1 },
  { key: "7d", label: "7 kun", days: 7 },
  { key: "30d", label: "30 kun", days: 30 },
  { key: "90d", label: "90 kun", days: 90 },
];

export function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function presetRange(key: string): Range {
  const p = PRESETS.find((x) => x.key === key) ?? PRESETS[2];
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - (p.days - 1));
  return { from: iso(from), to: iso(to), preset: p.key };
}

export function RangeProvider({ children }: { children: React.ReactNode }) {
  const [range, setRangeState] = useState<Range>(() => presetRange("30d"));

  useEffect(() => {
    try {
      const saved = localStorage.getItem("vd_range");
      if (saved) {
        const r = JSON.parse(saved) as Range;
        setRangeState(r.preset === "custom" ? r : presetRange(r.preset));
      }
    } catch { /* */ }
  }, []);

  const value = useMemo(() => ({
    range,
    setRange: (r: Range) => {
      setRangeState(r);
      try { localStorage.setItem("vd_range", JSON.stringify(r)); } catch { /* */ }
    },
    qs: `from=${range.from}&to=${range.to}`,
  }), [range]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRange() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRange RangeProvider ichida");
  return ctx;
}
