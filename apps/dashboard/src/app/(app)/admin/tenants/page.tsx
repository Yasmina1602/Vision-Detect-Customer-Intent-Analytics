"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { Badge, Card, CopyField, Field, Modal, PageHeader, Skeleton, Spinner, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateTime, num } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const BASIC_EDITION = process.env.NEXT_PUBLIC_EDITION === "basic";
const STATUS_TONE: Record<string, "ok" | "warn" | "bad" | "neutral"> = { active: "ok", trial: "warn", suspended: "bad", deleted: "neutral" };

export default function TenantsPage() {
  const toast = useToast();
  const { user, setTenant, reload } = useAuth();
  const { data, mutate } = useApi<any>("/v1/admin/tenants");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", plan: "basic", owner_email: "", owner_password: "" });
  const [created, setCreated] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function patch(id: string, body: Record<string, string>) {
    try { await api(`/v1/admin/tenants/${id}`, { method: "PATCH", body }); toast("Yangilandi"); mutate(); }
    catch (e: any) { toast(e.message, "bad"); }
  }

  return (
    <>
      <PageHeader title="Do'konlar (tenantlar)" description="Barcha mijoz do'konlari, tariflar va holat"
        actions={<button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Do'kon yaratish</button>} />
      <Card pad={false}>
        {!data ? <div className="p-5"><Skeleton className="h-60" /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px]">
              <thead className="border-b border-line bg-subtle/50"><tr>
                <th className="th">Do'kon</th><th className="th">Tarif</th><th className="th">Holat</th><th className="th text-right">Qidiruv (30k)</th>
                <th className="th text-right">Mahsulot</th><th className="th text-right">A'zo</th><th className="th">Yaratilgan</th><th className="th" />
              </tr></thead>
              <tbody className="divide-y divide-line">
                {data.items.map((t: any) => (
                  <tr key={t.id} className="hover:bg-subtle/40">
                    <td className="td"><p className="font-medium">{t.name}</p><p className="text-xs text-muted">{t.slug} · {t.platform || "—"}</p></td>
                    <td className="td"><select className="input h-8 w-auto text-xs" value={t.plan} onChange={(e) => patch(t.id, { plan: e.target.value })}>
                      <option value="basic">Oddiy</option>{!BASIC_EDITION && <option value="premium">Premium</option>}</select></td>
                    <td className="td"><select className="input h-8 w-auto text-xs" value={t.status} onChange={(e) => patch(t.id, { status: e.target.value })}>
                      {["active", "trial", "suspended", "deleted"].map((s) => <option key={s}>{s}</option>)}</select>
                      <Badge tone={STATUS_TONE[t.status]} className="ml-2">{t.status}</Badge></td>
                    <td className="td text-right tabular-nums">{num(t.searches_30d)}</td>
                    <td className="td text-right tabular-nums">{num(t.products)}</td>
                    <td className="td text-right tabular-nums">{num(t.members)}</td>
                    <td className="td whitespace-nowrap text-muted">{dateTime(t.created_at)}</td>
                    <td className="td text-right">
                      {user?.tenants.some((x) => x.id === t.id) ? null : (
                        <button className="btn-ghost h-8 text-xs" title="Audit jurnaliga yoziladi" onClick={() => { setTenant(t.id, { id: t.id, name: t.name, slug: t.slug, plan: t.plan, status: t.status, role: "owner" }); toast(`${t.name} tanlandi`); }}>
                          Ko'rish
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Yangi do'kon"
        footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Bekor qilish</button>
          <button className="btn-primary" disabled={busy} onClick={async () => {
            setBusy(true);
            try { setCreated(await api("/v1/admin/tenants", { method: "POST", body: form })); setOpen(false); mutate(); reload(); }
            catch (e: any) { toast(e.fields?.[0]?.msg || e.message, "bad"); } finally { setBusy(false); }
          }}>{busy && <Spinner />}Yaratish</button></>}>
        <div className="space-y-4">
          <Field label="Do'kon nomi"><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Tarif"><select className="input" value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })}>
            <option value="basic">Oddiy (Analytics)</option>{!BASIC_EDITION && <option value="premium">Premium (Store + Analytics)</option>}</select></Field>
          <Field label="Egasi e-mail"><input className="input" type="email" value={form.owner_email} onChange={(e) => setForm({ ...form, owner_email: e.target.value })} /></Field>
          <Field label="Egasi paroli" help="Mavjud foydalanuvchi bo'lsa e'tiborga olinmaydi"><input className="input" type="password" value={form.owner_password} onChange={(e) => setForm({ ...form, owner_password: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={!!created} onClose={() => setCreated(null)} title="Do'kon yaratildi" footer={<button className="btn-primary" onClick={() => setCreated(null)}>Saqladim</button>}>
        {created && <div className="space-y-3"><div><p className="label">Public key</p><CopyField value={created.public_key} /></div>
          <div><p className="label">Secret key (faqat hozir)</p><CopyField value={created.secret_key} /></div></div>}
      </Modal>
    </>
  );
}
