"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Field, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

function LoginForm() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(params.get("expired") ? "Sessiya muddati tugadi. Qayta kiring." : null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    // "next" faqat shu foydalanuvchiga ruxsat etilgan ichki sahifa bo'lsa ishlatiladi
    const next = params.get("next") || "";
    const safe = next.startsWith("/") && !next.startsWith("//") && next !== "/login"
      && (!next.startsWith("/admin") || user.platform_role === "super_admin");
    const home = user.tenants.length ? "/overview" : user.platform_role === "super_admin" ? "/admin/tenants" : "/overview";
    router.replace(safe ? next : home);
  }, [loading, user, router, params]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await login(email, password); }
    catch (err: any) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Xush kelibsiz</h1>
      <p className="mt-1.5 text-sm text-muted">Do'koningiz analitikasiga kiring</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {error && <div role="alert" className="rounded-lg bg-bad-soft px-3 py-2.5 text-sm text-bad">{error}</div>}
        <Field label="E-mail">
          <input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="siz@do'kon.uz" />
        </Field>
        <Field label="Parol">
          <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-sm font-medium text-brand hover:underline">Parolni unutdingizmi?</Link>
        </div>
        <button className="btn-primary h-11 w-full" disabled={busy}>{busy && <Spinner />}Kirish</button>
      </form>
      <p className="mt-8 text-center text-sm text-muted">
        Hisobingiz yo'qmi? <Link href="/register" className="font-medium text-brand hover:underline">Ro'yxatdan o'ting</Link>
      </p>
      <div className="mt-6 rounded-xl border border-dashed border-line p-3 text-xs text-muted">
        Demo: <button type="button" className="font-mono text-ink underline-offset-2 hover:underline" onClick={() => { setEmail("demo@vision.uz"); setPassword("Demo12345"); }}>demo@vision.uz / Demo12345</button>
      </div>
    </>
  );
}

export default function LoginPage() {
  return <Suspense><LoginForm /></Suspense>;
}
