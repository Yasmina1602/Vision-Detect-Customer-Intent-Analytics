"use client";

import clsx from "clsx";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Check, Copy, Inbox, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, description, actions, children, className, pad = true }: {
  title?: React.ReactNode; description?: string; actions?: React.ReactNode; children: React.ReactNode; className?: string; pad?: boolean;
}) {
  return (
    <section className={clsx("card animate-in", className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-[15px] font-semibold">{title}</h2>
            {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className={clsx(pad && "p-5")}>{children}</div>
    </section>
  );
}

export function Delta({ value, inverse = false }: { value: number | null | undefined; inverse?: boolean }) {
  if (value == null) return <span className="text-xs text-muted">oldingi davr yo'q</span>;
  const good = inverse ? value <= 0 : value >= 0;
  const Icon = value >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={clsx("inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-semibold",
      good ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad")}>
      <Icon className="h-3.5 w-3.5" />{Math.abs(value).toFixed(1)}%
    </span>
  );
}

export function Kpi({ label, value, delta, inverse, icon, hint, loading }: {
  label: string; value: React.ReactNode; delta?: number | null; inverse?: boolean; icon?: React.ReactNode; hint?: string; loading?: boolean;
}) {
  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted">{label}</span>
        {icon && <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-soft text-brand">{icon}</span>}
      </div>
      {loading ? <div className="skeleton mt-3 h-8 w-28" /> : <div className="mt-2 text-[28px] font-semibold tracking-tight tabular-nums">{value}</div>}
      <div className="mt-2 flex items-center gap-2">
        {delta !== undefined && !loading && <Delta value={delta} inverse={inverse} />}
        {hint && <span className="text-xs text-muted">{hint}</span>}
      </div>
    </div>
  );
}

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: "neutral" | "brand" | "ok" | "warn" | "bad"; className?: string }) {
  const tones = {
    neutral: "bg-subtle text-muted", brand: "bg-brand-soft text-brand-ink dark:text-brand",
    ok: "bg-ok-soft text-ok", warn: "bg-warn-soft text-warn", bad: "bg-bad-soft text-bad",
  };
  return <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", tones[tone], className)}>{children}</span>;
}

export function Empty({ title, text, action, icon }: { title: string; text?: string; action?: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-subtle text-muted">{icon ?? <Inbox className="h-6 w-6" />}</div>
      <p className="font-medium">{title}</p>
      {text && <p className="mt-1 max-w-sm text-sm text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: any; retry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-bad/30 bg-bad-soft px-4 py-3 text-sm text-bad">
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
      <div className="flex-1">{error?.message || "Ma'lumotni yuklab bo'lmadi"}</div>
      {retry && <button className="font-semibold underline" onClick={retry}>Qayta urinish</button>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton", className)} />;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("h-4 w-4 animate-spin", className)} />;
}

export function CopyField({ value, mono = true, secret = false }: { value: string; mono?: boolean; secret?: boolean }) {
  const [copied, setCopied] = useState(false);
  const [shown, setShown] = useState(!secret);
  return (
    <div className="flex items-stretch overflow-hidden rounded-lg border border-line bg-subtle">
      <code className={clsx("flex-1 overflow-x-auto whitespace-nowrap px-3 py-2.5 text-[13px]", mono && "font-mono")}>
        {shown ? value : "•".repeat(Math.min(value.length, 32))}
      </code>
      {secret && (
        <button className="border-l border-line px-3 text-xs font-medium text-muted hover:text-ink" onClick={() => setShown(!shown)}>
          {shown ? "Yashirish" : "Ko'rsatish"}
        </button>
      )}
      <button
        className="flex items-center gap-1.5 border-l border-line px-3 text-xs font-medium text-muted hover:bg-surface hover:text-ink"
        onClick={async () => { await navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        aria-label="Nusxa olish"
      >
        {copied ? <Check className="h-4 w-4 text-ok" /> : <Copy className="h-4 w-4" />}
        <span className="hidden sm:inline">{copied ? "Nusxalandi" : "Nusxa"}</span>
      </button>
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer, size = "md" }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode; footer?: React.ReactNode; size?: "md" | "lg";
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("input,select,textarea,button")?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 backdrop-blur-[2px] sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" className={clsx("card w-full animate-in rounded-b-none sm:rounded-2xl", size === "lg" ? "max-w-2xl" : "max-w-md")}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h3 className="font-semibold">{title}</h3>
          <button className="btn-ghost h-8 w-8 px-0" onClick={onClose} aria-label="Yopish"><X className="h-4 w-4" /></button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Pagination({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
      <span>{total === 0 ? "0" : `${(page - 1) * size + 1}–${Math.min(page * size, total)}`} / {total}</span>
      <div className="flex gap-2">
        <button className="btn-secondary h-8" disabled={page <= 1} onClick={() => onPage(page - 1)}>Oldingi</button>
        <button className="btn-secondary h-8" disabled={page >= pages} onClick={() => onPage(page + 1)}>Keyingi</button>
      </div>
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: string }[] }) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-subtle p-0.5" role="tablist">
      {items.map((it) => (
        <button key={it.value} role="tab" aria-selected={value === it.value} onClick={() => onChange(it.value)}
          className={clsx("rounded-md px-3 py-1.5 text-sm font-medium transition",
            value === it.value ? "bg-surface text-ink shadow-card" : "text-muted hover:text-ink")}>
          {it.label}
        </button>
      ))}
    </div>
  );
}

export function Field({ label, help, error, children }: { label: string; help?: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {error ? <p className="mt-1 text-xs text-bad">{error}</p> : help ? <p className="help">{help}</p> : null}
    </label>
  );
}

// ---------- Toast ----------
type ToastItem = { id: number; text: string; tone: "ok" | "bad" | "info" };
const ToastCtx = createContext<(text: string, tone?: ToastItem["tone"]) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, tone: ToastItem["tone"] = "ok") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, text, tone }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={clsx("pointer-events-auto flex animate-in items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium shadow-pop",
            t.tone === "bad" ? "bg-bad text-white" : "bg-ink text-bg")}>
            {t.tone === "ok" && <Check className="h-4 w-4" />}{t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);
