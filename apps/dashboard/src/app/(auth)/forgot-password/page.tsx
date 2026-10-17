"use client";

import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Field, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState<{ message: string; dev_reset_link?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { setDone(await api("/v1/auth/forgot", { method: "POST", body: { email } })); }
    catch (err: any) { setError(err.message); }
    finally { setBusy(false); }
  }

  if (done) {
    return (
      <div>
        <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-ok-soft text-ok"><MailCheck className="h-6 w-6" /></div>
        <h1 className="text-2xl font-semibold tracking-tight">Pochtangizni tekshiring</h1>
        <p className="mt-2 text-sm text-muted">{done.message}</p>
        {done.dev_reset_link && (
          <div className="mt-5 rounded-xl border border-dashed border-warn/50 bg-warn-soft p-3 text-sm">
            <p className="font-medium text-warn">Dev rejim (SMTP sozlanmagan):</p>
            <a className="break-all text-brand underline" href={done.dev_reset_link.replace(/^https?:\/\/[^/]+/, "")}>Parolni tiklash havolasi</a>
          </div>
        )}
        <Link href="/login" className="btn-secondary mt-8 w-full">Kirishga qaytish</Link>
      </div>
    );
  }

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Parolni tiklash</h1>
      <p className="mt-1.5 text-sm text-muted">E-mailingizni kiriting — tiklash havolasini yuboramiz.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {error && <div role="alert" className="rounded-lg bg-bad-soft px-3 py-2.5 text-sm text-bad">{error}</div>}
        <Field label="E-mail"><input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <button className="btn-primary h-11 w-full" disabled={busy}>{busy && <Spinner />}Havola yuborish</button>
      </form>
      <p className="mt-8 text-center text-sm"><Link href="/login" className="font-medium text-brand hover:underline">← Kirishga qaytish</Link></p>
    </>
  );
}
