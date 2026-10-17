"use client";

import clsx from "clsx";
import { AlertTriangle, CheckCircle2, KeyRound, Loader2, PartyPopper, RefreshCw, ShieldAlert, Store, XCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CopyField, Empty, Modal, PageHeader, Skeleton, Spinner, Tabs, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const PLATFORMS = [
  { value: "woocommerce", label: "WooCommerce" }, { value: "shopify", label: "Shopify" }, { value: "opencart", label: "OpenCart" },
  { value: "laravel", label: "Laravel" }, { value: "nextjs", label: "Next.js" }, { value: "html", label: "HTML" }, { value: "custom", label: "Boshqa" },
];

const GUIDE: Record<string, string[]> = {
  woocommerce: ["Tegni mavzuning footer.php faylida </body> oldiga qo'ying (yoki \"Insert Headers and Footers\" plagini).",
    "WooCommerce → Sozlamalar → Kengaytirilgan → Webhooks: \"Order created\" uchun quyidagi WooCommerce webhook URL'ini kiriting.",
    "Savatga qo'shish avtomatik ishlaydi (?add-to-cart=ID)."],
  shopify: ["Online Store → Themes → Edit code → theme.liquid: tegni </body> oldiga qo'ying.",
    "Settings → Notifications → Webhooks: \"Order creation\" (JSON) uchun Shopify webhook URL'ini qo'shing.",
    "Savatga qo'shish /cart/add.js orqali, vd_sid savat atributiga yoziladi."],
  opencart: ["Tegni catalog/view/theme/.../footer.twig ichida </body> oldiga qo'ying.", "Buyurtma hodisasi uchun OpenCart webhook URL'ini ishlating."],
  laravel: ["Tegni asosiy Blade layout'da </body> oldiga qo'ying.", "Buyurtma yaratilgach server-to-server: POST /v1/server/events (secret key bilan)."],
  nextjs: ["app/layout.tsx da <Script src=... data-key=... strategy=\"afterInteractive\" /> ishlating.", "Buyurtmalar uchun backend'dan /v1/server/events chaqiring."],
  html: ["Tegni har bir sahifada </body> oldiga qo'ying — tamom.", "Xarid uchun \"rahmat\" sahifasi URL shablonini Sozlamalarda kiriting."],
  custom: ["Tegni </body> oldiga qo'ying.", "Savatga qo'shishni ulash: window.VisionAnalytics.onAddToCart = (p) => myShop.add(p.id)",
    "Login'dan keyin: VisionAnalytics.identify('u_1842') — e-mail/telefon EMAS."],
};

function StatusIcon({ s }: { s: string }) {
  if (s === "ok") return <CheckCircle2 className="h-5 w-5 text-ok" />;
  if (s === "warn") return <AlertTriangle className="h-5 w-5 text-warn" />;
  return <XCircle className="h-5 w-5 text-bad" />;
}

function IntegrationsInner() {
  const { tenant } = useAuth();
  if (tenant?.plan === "premium") {
    return (
      <Empty icon={<Store className="h-6 w-6" />} title="Premium'da ulash shart emas"
        text="Do'koningiz va rasm qidiruvi allaqachon tayyor ishlayapti. Mahsulotlarni qo'shing — ular darhol do'konda ko'rinadi."
        action={<Link href="/products" className="btn-primary">Mahsulotlarga o'tish</Link>} />
    );
  }
  return <IntegrationsBody />;
}

function IntegrationsBody() {
  const toast = useToast();
  const welcome = useSearchParams().get("welcome");
  const { data, mutate } = useApi<any>("/v1/dashboard/integrations");
  const check = useApi<any>("/v1/dashboard/integrations/install-check");
  const settings = useApi<any>("/v1/dashboard/settings");
  const [platform, setPlatform] = useState("html");
  const [origins, setOrigins] = useState("");
  const [secrets, setSecrets] = useState<{ secret_key?: string; webhook_secret?: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any>(null);

  useEffect(() => { if (data) { setOrigins((data.key.allowed_origins || []).join("\n")); setPlatform(data.platform || "html"); } }, [data]);

  async function act(name: string, fn: () => Promise<any>) {
    setBusy(name);
    try { return await fn(); } catch (e: any) { toast(e.message, "bad"); } finally { setBusy(null); }
  }

  const webhookPlatform = ["woocommerce", "shopify", "opencart"].includes(platform) ? platform : "generic";

  return (
    <>
      <PageHeader title="Integratsiya" description="Bitta <script> tegi bilan vidjetni saytingizga ulang va ulanishni tekshiring." />

      {welcome && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-brand/30 bg-brand-soft px-4 py-3 text-sm text-brand-ink dark:text-brand">
          <PartyPopper className="mt-0.5 h-4 w-4 flex-none" />
          <div><b>Do'kon yaratildi!</b> Endi 3 qadam: tegni saytga qo'ying → domeningizni allowlist'ga qo'shing → katalogni ulang.</div>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card title="1. Vidjetni o'rnatish" description="Saytingizning har bir sahifasida </body> oldiga qo'ying">
            {!data ? <Skeleton className="h-12" /> : <CopyField value={data.snippet} />}
            <div className="mt-5">
              <Tabs value={platform} onChange={(v) => {
                setPlatform(v);
                api("/v1/dashboard/integrations/platform", { method: "PUT", body: { platform: v } }).then(() => settings.mutate()).catch(() => {});
              }} items={PLATFORMS} />
              <ol className="mt-4 space-y-2 text-sm">
                {(GUIDE[platform] || GUIDE.custom).map((g, i) => (
                  <li key={i} className="flex gap-3"><span className="grid h-5 w-5 flex-none place-items-center rounded-full bg-brand-soft text-[11px] font-bold text-brand">{i + 1}</span><span>{g}</span></li>
                ))}
              </ol>
            </div>
            {data && (
              <details className="mt-4 rounded-lg border border-line p-3 text-sm">
                <summary className="cursor-pointer font-medium">Saytingizda CSP bo'lsa</summary>
                <p className="my-2 text-muted">Content-Security-Policy'ga quyidagilarni qo'shing:</p>
                <CopyField value={data.csp} />
              </details>
            )}
          </Card>

          <Card title="2. Ruxsat etilgan domenlar" description="Public key faqat shu domenlarda ishlaydi (har qatorda bitta; *.shop.uz ham mumkin)">
            <textarea className="input h-24 py-2 font-mono text-[13px]" value={origins} onChange={(e) => setOrigins(e.target.value)} placeholder={"https://shop.uz\nhttps://www.shop.uz"} />
            <div className="mt-3 flex justify-end">
              <button className="btn-primary" disabled={busy === "origins"} onClick={() => act("origins", async () => {
                await api("/v1/dashboard/integrations/origins", { method: "PUT", body: { allowed_origins: origins.split(/\s+/).filter(Boolean) } });
                toast("Domenlar saqlandi"); mutate(); check.mutate();
              })}>{busy === "origins" && <Spinner />}Saqlash</button>
            </div>
          </Card>

          <Card title="3. Buyurtmalarni ulash (webhook)" description="Xarid server-to-server keladi — eng ishonchli manba. Imzo: HMAC-SHA256(X-Timestamp + '.' + body)">
            {!data ? <Skeleton className="h-24" /> : (
              <div className="space-y-4">
                <div><p className="label">Webhook URL ({webhookPlatform})</p><CopyField value={data.webhook_urls[webhookPlatform]} /></div>
                <div><p className="label">Server events URL</p><CopyField value={data.server_events_url} /></div>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-secondary" disabled={!!busy} onClick={() => act("reveal", async () => setSecrets(await api("/v1/dashboard/integrations/webhook-secret", { method: "POST" })))}>
                    <KeyRound className="h-4 w-4" />Webhook maxfiy kalitini ko'rsatish
                  </button>
                  <button className="btn-secondary" disabled={!!busy} onClick={() => act("test", async () => { setTestResult(await api("/v1/dashboard/integrations/test-event", { method: "POST" })); check.mutate(); })}>
                    {busy === "test" ? <Spinner /> : <RefreshCw className="h-4 w-4" />}Ulanishni tekshirish
                  </button>
                </div>
                {testResult && (
                  <div className="rounded-lg bg-subtle p-3 text-sm">
                    <p className={clsx("font-medium", testResult.event_accepted ? "text-ok" : "text-bad")}>
                      {testResult.event_accepted ? "✓ Test hodisa qabul qilindi" : "Test hodisa qabul qilinmadi"}
                    </p>
                    <p className="mt-2 text-muted">Imzo namunasi (o'z serveringiz natijasi bilan solishtiring):</p>
                    <pre className="mt-1 overflow-x-auto rounded-md bg-surface p-2 text-xs">{JSON.stringify(testResult.signature_example, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="O'rnatish holati" actions={<button className="btn-ghost h-8 w-8 px-0" aria-label="Yangilash" onClick={() => check.mutate()}>
            {check.isValidating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}</button>}>
            {!check.data ? <Skeleton className="h-64" /> : (
              <>
                <div className="mb-4 flex items-center gap-3">
                  <div className="relative h-12 w-12">
                    <svg viewBox="0 0 36 36" className="h-12 w-12 -rotate-90"><circle cx="18" cy="18" r="15.5" fill="none" stroke="rgb(var(--subtle))" strokeWidth="4" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="rgb(var(--ok))" strokeWidth="4" strokeLinecap="round"
                        strokeDasharray={`${(check.data.score / check.data.total) * 97.4} 97.4`} /></svg>
                    <span className="absolute inset-0 grid place-items-center text-xs font-bold">{check.data.score}/{check.data.total}</span>
                  </div>
                  <p className="text-sm text-muted">{check.data.score === check.data.total ? "Hammasi joyida!" : "Quyidagi bandlarni tekshiring"}</p>
                </div>
                <ul className="space-y-3">
                  {check.data.checks.map((c: any) => (
                    <li key={c.key} className="flex gap-3"><StatusIcon s={c.status} />
                      <div className="min-w-0"><p className="text-sm font-medium">{c.title}</p><p className="break-words text-xs text-muted">{c.detail}</p></div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>

          <Card title="API kalitlar">
            {!data ? <Skeleton className="h-28" /> : (
              <div className="space-y-3 text-sm">
                <div><p className="label">Public key</p><CopyField value={data.key.public_key} /></div>
                <div><p className="label">Secret key</p><p className="rounded-lg border border-line bg-subtle px-3 py-2.5 font-mono text-[13px] text-muted">{data.key.secret_key_hint}</p>
                  <p className="help">Faqat yaratilganda bir marta ko'rsatiladi. Oxirgi ishlatilgan: {dateTime(data.key.last_used_at)}</p></div>
                <button className="btn-secondary w-full text-bad" disabled={!!busy} onClick={() => confirm("Kalitlar almashtirilsinmi? Eski kalitlar darhol ishlamay qoladi — saytdagi tegni yangilashingiz kerak.") &&
                  act("rotate", async () => { setSecrets(await api("/v1/dashboard/integrations/rotate", { method: "POST" })); mutate(); })}>
                  <ShieldAlert className="h-4 w-4" />Kalitlarni yangilash (rotatsiya)
                </button>
              </div>
            )}
          </Card>
        </div>
      </div>

      <Modal open={!!secrets} onClose={() => setSecrets(null)} title="Maxfiy kalitlar" footer={<button className="btn-primary" onClick={() => setSecrets(null)}>Saqladim</button>}>
        <div className="space-y-4">
          <p className="rounded-lg bg-warn-soft p-3 text-sm text-warn">Bu kalitlarni hech kimga bermang va brauzer kodiga qo'ymang. Faqat serveringizda saqlang.</p>
          {secrets?.secret_key && <div><p className="label">Secret key (faqat hozir ko'rinadi)</p><CopyField value={secrets.secret_key} /></div>}
          {secrets?.webhook_secret && <div><p className="label">Webhook secret</p><CopyField value={secrets.webhook_secret} secret /></div>}
        </div>
      </Modal>
    </>
  );
}

export default function IntegrationsPage() {
  return <Suspense><IntegrationsInner /></Suspense>;
}
