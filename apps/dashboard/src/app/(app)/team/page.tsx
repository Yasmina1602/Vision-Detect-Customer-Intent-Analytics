"use client";

import { Trash2, UserPlus } from "lucide-react";
import { useState } from "react";
import { Badge, Card, CopyField, Field, Modal, PageHeader, Skeleton, Spinner, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS, ROLE_RANK, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const ROLES = ["owner", "admin", "catalog_manager", "analyst", "viewer"];
const MATRIX: [string, string][] = [
  ["Analitikani ko'rish", "viewer"], ["CSV eksport", "analyst"], ["Katalog sozlash", "catalog_manager"],
  ["Kalitlar, domenlar, webhook", "admin"], ["A'zolarni boshqarish", "admin"], ["Tarif / do'konni o'chirish", "owner"],
];

export default function TeamPage() {
  const { tenant } = useAuth();
  const toast = useToast();
  const { data, mutate } = useApi<any>("/v1/dashboard/members");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", full_name: "", role: "analyst" });
  const [busy, setBusy] = useState(false);
  const [temp, setTemp] = useState<string | null>(null);
  const myRank = ROLE_RANK[tenant?.role || "viewer"];
  const assignable = ROLES.filter((r) => ROLE_RANK[r] <= myRank && (r !== "owner" || tenant?.role === "owner"));

  async function invite() {
    setBusy(true);
    try {
      const r = await api("/v1/dashboard/members", { method: "POST", body: form });
      setOpen(false); setForm({ email: "", full_name: "", role: "analyst" });
      if (r.temp_password) setTemp(r.temp_password); else toast("A'zo qo'shildi");
      mutate();
    } catch (e: any) { toast(e.message, "bad"); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Jamoa" description="Do'kon dashboardiga kirish huquqi bo'lgan a'zolar va ularning rollari"
        actions={<button className="btn-primary" onClick={() => setOpen(true)}><UserPlus className="h-4 w-4" />Taklif qilish</button>} />
      <div className="grid gap-4 xl:grid-cols-3">
        <Card pad={false} title="A'zolar" className="xl:col-span-2">
          {!data ? <div className="p-5"><Skeleton className="h-40" /></div> : (
            <ul className="divide-y divide-line">
              {data.items.map((m: any) => (
                <li key={m.user_id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                  <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-sm font-bold uppercase text-brand">{(m.full_name || m.email)[0]}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{m.full_name || m.email} {m.is_me && <Badge className="ml-1">siz</Badge>}</p>
                    <p className="truncate text-xs text-muted">{m.email} · oxirgi kirish: {timeAgo(m.last_login_at)}</p>
                  </div>
                  <select className="input h-9 w-auto" value={m.role} disabled={m.is_me || ROLE_RANK[m.role] > myRank}
                    onChange={async (e) => {
                      try { await api(`/v1/dashboard/members/${m.user_id}`, { method: "PUT", body: { role: e.target.value } }); toast("Rol o'zgartirildi"); mutate(); }
                      catch (err: any) { toast(err.message, "bad"); }
                    }}>
                    {ROLES.map((r) => <option key={r} value={r} disabled={!assignable.includes(r)}>{ROLE_LABELS[r]}</option>)}
                  </select>
                  {!m.is_me && (
                    <button className="btn-ghost h-9 w-9 px-0 hover:text-bad" aria-label="Olib tashlash" onClick={async () => {
                      if (!confirm(`${m.email} jamoadan olib tashlansinmi?`)) return;
                      try { await api(`/v1/dashboard/members/${m.user_id}`, { method: "DELETE" }); toast("Olib tashlandi"); mutate(); }
                      catch (err: any) { toast(err.message, "bad"); }
                    }}><Trash2 className="h-4 w-4" /></button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Rollar va ruxsatlar" pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-line">
                <th className="px-3 py-2 text-left font-medium text-muted">Imkoniyat</th>
                {ROLES.map((r) => <th key={r} className="px-1 py-2 font-medium text-muted" title={ROLE_LABELS[r]}>{ROLE_LABELS[r].slice(0, 5)}</th>)}
              </tr></thead>
              <tbody className="divide-y divide-line">
                {MATRIX.map(([label, min]) => (
                  <tr key={label}><td className="px-3 py-2">{label}</td>
                    {ROLES.map((r) => <td key={r} className="text-center">{ROLE_RANK[r] >= ROLE_RANK[min] ? <span className="text-ok">●</span> : <span className="text-line">●</span>}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="A'zoni taklif qilish"
        footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Bekor qilish</button><button className="btn-primary" disabled={busy || !form.email} onClick={invite}>{busy && <Spinner />}Taklif qilish</button></>}>
        <div className="space-y-4">
          <Field label="E-mail"><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="Ism (ixtiyoriy)"><input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <Field label="Rol"><select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {assignable.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}</select></Field>
        </div>
      </Modal>
      <Modal open={!!temp} onClose={() => setTemp(null)} title="Vaqtinchalik parol" footer={<button className="btn-primary" onClick={() => setTemp(null)}>Tushunarli</button>}>
        <p className="mb-3 text-sm text-muted">Yangi foydalanuvchi yaratildi. Parolni xavfsiz kanal orqali yuboring — u faqat bir marta ko'rsatiladi. Birinchi kirishda "Parolni unutdingizmi?" orqali almashtirish tavsiya etiladi.</p>
        {temp && <CopyField value={temp} />}
      </Modal>
    </>
  );
}
