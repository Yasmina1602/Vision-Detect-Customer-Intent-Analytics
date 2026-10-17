/** API mijoz: access token xotirada, refresh — httpOnly cookie. 401 da bir marta jim yangilanadi. */

export class ApiError extends Error {
  code: string;
  status: number;
  fields?: { loc: (string | number)[]; msg: string }[];
  constructor(status: number, code: string, message: string, fields?: ApiError["fields"]) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onUnauthorized: (() => void) | null = null;

export const TENANT_KEY = "vd_tenant";

export function setAccessToken(t: string | null) { accessToken = t; }
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }
export function currentTenantId(): string | null {
  if (typeof window === "undefined") return null;
  try { return localStorage.getItem(TENANT_KEY); } catch { return null; }
}

export async function refreshSession(): Promise<any | null> {
  const res = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
  if (!res.ok) return null;
  const data = await res.json();
  accessToken = data.access_token;
  return data;
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = refreshSession().then((d) => !!d).catch(() => false).finally(() => { setTimeout(() => (refreshing = null), 0); });
  }
  return refreshing;
}

type Opts = Omit<RequestInit, "body"> & { body?: unknown; raw?: boolean; noTenant?: boolean };

export async function api<T = any>(path: string, opts: Opts = {}, retried = false): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const tid = currentTenantId();
  if (tid && !opts.noTenant) headers["X-Tenant-Id"] = tid;
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) body = opts.body;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }

  const res = await fetch(`/api${path}`, { ...opts, headers, body, credentials: "include" });

  if (res.status === 401 && !retried && !path.startsWith("/v1/auth/")) {
    if (await tryRefresh()) return api<T>(path, opts, true);
    onUnauthorized?.();
  }
  if (!res.ok) {
    let payload: any = null;
    try { payload = await res.json(); } catch { /* bo'sh javob */ }
    const e = payload?.error;
    throw new ApiError(res.status, e?.code || "HTTP_ERROR", e?.message || "Server bilan bog'lanishda xatolik", e?.fields);
  }
  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const fetcher = (path: string) => api(path);

/** CSV kabi fayllarni yuklab olish (token bilan). */
export async function download(path: string, fallbackName: string) {
  const res = await api<Response>(path, { raw: true });
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const name = /filename="([^"]+)"/.exec(cd)?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
