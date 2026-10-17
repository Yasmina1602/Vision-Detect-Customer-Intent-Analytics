"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, refreshSession, setAccessToken, setUnauthorizedHandler, TENANT_KEY } from "./api";

export type Tenant = { id: string; name: string; slug: string; plan: "basic" | "premium"; status: string; role: string };
export type User = { id: string; email: string; full_name: string | null; platform_role: string; tenants: Tenant[] };

type AuthState = {
  user: User | null;
  loading: boolean;
  tenant: Tenant | null;
  setTenant: (id: string, external?: Tenant) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (data: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [external, setExternal] = useState<Tenant | null>(null); // super_admin boshqa do'konni ko'rganda
  const router = useRouter();

  const accept = useCallback((data: { access_token: string; user: User }) => {
    setAccessToken(data.access_token);
    setUser(data.user);
    let tid: string | null = null;
    try { tid = localStorage.getItem(TENANT_KEY); } catch { /* */ }
    if (!data.user.tenants.some((t) => t.id === tid)) tid = data.user.tenants[0]?.id ?? null;
    if (tid) localStorage.setItem(TENANT_KEY, tid);
    setTenantId(tid);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setAccessToken(null);
      router.replace("/login?expired=1");
    });
    refreshSession().then((d) => d && accept(d)).catch(() => {}).finally(() => setLoading(false));
  }, [accept, router]);

  // access token 15 daqiqa — 12 daqiqada jim yangilaymiz
  useEffect(() => {
    if (!user) return;
    const t = setInterval(() => refreshSession().then((d) => d && setAccessToken(d.access_token)), 12 * 60 * 1000);
    return () => clearInterval(t);
  }, [user]);

  const value = useMemo<AuthState>(() => ({
    user,
    loading,
    tenant: user?.tenants.find((t) => t.id === tenantId) ?? (external?.id === tenantId ? external : null),
    setTenant: (id: string, ext?: Tenant) => {
      localStorage.setItem(TENANT_KEY, id);
      if (ext) setExternal(ext);
      setTenantId(id);
    },
    login: async (email, password) => accept(await api("/v1/auth/login", { method: "POST", body: { email, password } })),
    register: async (data) => accept(await api("/v1/auth/register", { method: "POST", body: data })),
    logout: async () => {
      try { sessionStorage.setItem("vd_logged_out", "1"); } catch { /* */ }
      await api("/v1/auth/logout", { method: "POST" }).catch(() => {});
      setAccessToken(null);
      setUser(null);
      router.replace("/login");
    },
    reload: async () => {
      const me = await api<User>("/v1/auth/me");
      setUser(me);
    },
  }), [user, loading, tenantId, external, accept, router]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth AuthProvider ichida ishlatilishi kerak");
  return ctx;
}
