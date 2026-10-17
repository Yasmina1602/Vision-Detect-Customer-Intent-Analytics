"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const PLATFORMS = [
  ["woocommerce", "WooCommerce"], ["shopify", "Shopify"], ["opencart", "OpenCart"],
  ["laravel", "Laravel"], ["nextjs", "Next.js"], ["html", "Oddiy HTML"], ["custom", "Boshqa"],
];

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", shop_name: "", email: "", password: "", platform: "woocommerce" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setErrors({});
    try {
      await register(form);
      router.replace("/integrations?welcome=1");
    } catch (err) {
      const ae = err as ApiError;
      if (ae.fields?.length) {
        setErrors(Object.fromEntries(ae.fields.map((f) => [String(f.loc[f.loc.length - 1]), f.msg.replace(/^Value error, /, "")])));
      } else setError(ae.message);
    } finally { setBusy(false); }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Do'konni ulash</h1>
      <p className="mt-1.5 text-sm text-muted">2 daqiqada hisob oching — keyin bitta teg bilan saytingizga ulaysiz.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {error && <div role="alert" className="rounded-lg bg-bad-soft px-3 py-2.5 text-sm text-bad">{error}</div>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Ismingiz" error={errors.full_name}><input className="input" required value={form.full_name} onChange={set("full_name")} autoComplete="name" /></Field>
          <Field label="Do'kon nomi" error={errors.shop_name}><input className="input" required value={form.shop_name} onChange={set("shop_name")} /></Field>
        </div>
        <Field label="E-mail" error={errors.email}><input className="input" type="email" required value={form.email} onChange={set("email")} autoComplete="email" /></Field>
        <Field label="Parol" help="Kamida 8 belgi, harf va raqam" error={errors.password}>
          <input className="input" type="password" required minLength={8} value={form.password} onChange={set("password")} autoComplete="new-password" />
        </Field>
        <Field label="Sayt platformasi">
          <select className="input" value={form.platform} onChange={set("platform")}>
            {PLATFORMS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        <button className="btn-primary h-11 w-full" disabled={busy}>{busy && <Spinner />}Hisob ochish</button>
      </form>
      <p className="mt-8 text-center text-sm text-muted">
        Hisobingiz bormi? <Link href="/login" className="font-medium text-brand hover:underline">Kirish</Link>
      </p>
    </>
  );
}
