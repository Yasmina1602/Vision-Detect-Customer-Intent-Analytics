"use client";

import { Info, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Badge, Card, Empty, Field, Modal, PageHeader, Skeleton, Spinner, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, num } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function AiModelsPage() {
  const toast = useToast();
  const { data, mutate } = useApi<any>("/v1/admin/ai-models", { refreshInterval: 15000 });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", priority: 50 });
  const [busy, setBusy] = useState(false);

  async function patch(name: string, body: object) {
    try { await api(`/v1/admin/ai-models/${encodeURIComponent(name)}`, { method: "PATCH", body }); mutate(); }
    catch (e: any) { toast(e.message, "bad"); }
  }

  return (
    <>
      <PageHeader title="AI modellar" description="Model nomlari kodga yozilmaydi. Router prioritet bo'yicha tanlaydi; 429/5xx bo'lsa model 60 s sovutiladi (circuit breaker)."
        actions={<button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Model qo'shish</button>} />
      {data?.demo_mode && (
        <div className="mb-4 flex gap-3 rounded-xl border border-warn/40 bg-warn-soft px-4 py-3 text-sm text-warn">
          <Info className="mt-0.5 h-4 w-4 flex-none" />
          <span><b>Demo rejim:</b> GEMINI_API_KEY sozlanmagan. Rasm rangi lokal aniqlanadi, tur fayl nomidan olinadi. Production uchun .env ga pullik kalit qo'shing.</span>
        </div>
      )}
      <Card pad={false}>
        {!data ? <div className="p-5"><Skeleton className="h-40" /></div> : data.items.length === 0 ? <Empty title="Model yo'q" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead className="border-b border-line bg-subtle/50"><tr>
                <th className="th">Model</th><th className="th">Prioritet</th><th className="th">Holat</th><th className="th text-right">Muvaffaqiyat</th>
                <th className="th text-right">Xato %</th><th className="th">Oxirgi xato</th><th className="th" />
              </tr></thead>
              <tbody className="divide-y divide-line">
                {data.items.map((m: any) => (
                  <tr key={m.name}>
                    <td className="td font-mono text-[13px]">{m.name}</td>
                    <td className="td"><input type="number" className="input h-8 w-20" defaultValue={m.priority}
                      onBlur={(e) => Number(e.target.value) !== m.priority && patch(m.name, { priority: Number(e.target.value) })} /></td>
                    <td className="td">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={m.enabled} onChange={(e) => patch(m.name, { enabled: e.target.checked })} />
                        {!m.enabled ? <Badge>o'chiq</Badge> : m.cooling ? <Badge tone="warn">sovumoqda · {dateTime(m.cooldown_until)}</Badge> : <Badge tone="ok">faol</Badge>}
                      </label>
                    </td>
                    <td className="td text-right tabular-nums">{num(m.success_count)}</td>
                    <td className="td text-right tabular-nums"><span className={m.error_rate_pct > 10 ? "text-bad" : ""}>{m.error_rate_pct}%</span></td>
                    <td className="td max-w-[240px] truncate text-xs text-muted" title={m.last_error || ""}>{m.last_error || "—"}</td>
                    <td className="td whitespace-nowrap text-right">
                      {m.cooling && <button className="btn-ghost h-8 text-xs" onClick={() => patch(m.name, { reset_cooldown: true })}><RotateCcw className="h-3.5 w-3.5" />Tiklash</button>}
                      <button className="btn-ghost h-8 w-8 px-0 hover:text-bad" aria-label="O'chirish" onClick={async () => {
                        if (!confirm(`${m.name} o'chirilsinmi?`)) return;
                        await api(`/v1/admin/ai-models/${encodeURIComponent(m.name)}`, { method: "DELETE" }).catch((e) => toast(e.message, "bad")); mutate();
                      }}><Trash2 className="h-4 w-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title="Model qo'shish"
        footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Bekor qilish</button>
          <button className="btn-primary" disabled={busy || !form.name} onClick={async () => {
            setBusy(true);
            try { await api("/v1/admin/ai-models", { method: "POST", body: form }); setOpen(false); setForm({ name: "", priority: 50 }); mutate(); }
            catch (e: any) { toast(e.message, "bad"); } finally { setBusy(false); }
          }}>{busy && <Spinner />}Qo'shish</button></>}>
        <div className="space-y-4">
          <Field label="Model nomi" help="Masalan: gemini-2.5-flash"><input className="input font-mono" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Prioritet" help="Kichik raqam — birinchi"><input type="number" className="input" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></Field>
        </div>
      </Modal>
    </>
  );
}
