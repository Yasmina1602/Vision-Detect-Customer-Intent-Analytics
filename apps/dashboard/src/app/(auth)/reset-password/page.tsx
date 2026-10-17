"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Field, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

function ResetForm() {
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) return setError("Parollar mos emas");
    setState("busy"); setError(null);
    try { await api("/v1/auth/reset", { method: "POST", body: { token, password } }); setState("done"); }
    catch (err: any) { setError(err.fields?.[0]?.msg?.replace(/^Value error, /, "") || err.message); setState("idle"); }
  }

  if (state === "done") {
    return (
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Parol yangilandi</h1>
        <p className="mt-2 text-sm text-muted">Endi yangi parol bilan kirishingiz mumkin.</p>
        <Link href="/login" className="btn-primary mt-8 h-11 w-full">Kirish</Link>
      </div>
    );
  }
  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Yangi parol</h1>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {error && <div role="alert" className="rounded-lg bg-bad-soft px-3 py-2.5 text-sm text-bad">{error}</div>}
        <Field label="Yangi parol" help="Kamida 8 belgi, harf va raqam">
          <input className="input" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </Field>
        <Field label="Parolni tasdiqlang">
          <input className="input" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
        </Field>
        <button className="btn-primary h-11 w-full" disabled={state === "busy" || !token}>{state === "busy" && <Spinner />}Saqlash</button>
      </form>
    </>
  );
}

export default function ResetPage() {
  return <Suspense><ResetForm /></Suspense>;
}
