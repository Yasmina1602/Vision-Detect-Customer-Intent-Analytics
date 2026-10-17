"use client";

import clsx from "clsx";
import { CalendarDays } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { iso, PRESETS, presetRange, useRange } from "@/lib/range";
import { shortDate } from "@/lib/format";

export function RangePicker() {
  const { range, setRange } = useRange();
  const [open, setOpen] = useState(false);
  const [from, setFrom] = useState(range.from);
  const [to, setTo] = useState(range.to);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => { setFrom(range.from); setTo(range.to); }, [range]);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-2" ref={ref}>
      <div className="inline-flex rounded-lg border border-line bg-surface p-0.5">
        {PRESETS.map((p) => (
          <button key={p.key} onClick={() => setRange(presetRange(p.key))}
            className={clsx("rounded-md px-2.5 py-1.5 text-sm font-medium transition",
              range.preset === p.key ? "bg-brand-soft text-brand-ink dark:text-brand" : "text-muted hover:text-ink")}>
            {p.label}
          </button>
        ))}
      </div>
      <div className="relative">
        <button onClick={() => setOpen(!open)}
          className={clsx("btn-secondary", range.preset === "custom" && "border-brand text-brand")}>
          <CalendarDays className="h-4 w-4" />
          {shortDate(range.from)} – {shortDate(range.to)}
        </button>
        {open && (
          <div className="absolute right-0 top-full z-30 mt-1 w-72 animate-in rounded-xl border border-line bg-surface p-4 shadow-pop">
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs font-medium text-muted">Dan<input type="date" className="input mt-1" value={from} max={to} onChange={(e) => setFrom(e.target.value)} /></label>
              <label className="text-xs font-medium text-muted">Gacha<input type="date" className="input mt-1" value={to} min={from} max={iso(new Date())} onChange={(e) => setTo(e.target.value)} /></label>
            </div>
            <button className="btn-primary mt-3 w-full" disabled={!from || !to}
              onClick={() => { setRange({ from, to, preset: "custom" }); setOpen(false); }}>Qo'llash</button>
          </div>
        )}
      </div>
    </div>
  );
}
