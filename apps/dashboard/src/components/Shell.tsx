"use client";

import clsx from "clsx";
import {
  Boxes, ChevronDown, Cpu, Filter, Gauge, LayoutDashboard, LogOut, Menu, Moon, Palette,
  PlugZap, ScrollText, Search, Settings, ShieldCheck, ShoppingCart, Sun, Target, Users, X, Building2,
  Receipt, Contact, Megaphone, UsersRound, ExternalLink, Package,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { can, ROLE_LABELS } from "@/lib/format";
import { Logo } from "./Logo";

type NavItem = { href: string; label: string; icon: React.ElementType; min?: string; superAdmin?: boolean; premium?: boolean; basic?: boolean };

const NAV: { title: string; items: NavItem[] }[] = [
  {
    title: "Analitika",
    items: [
      { href: "/overview", label: "Umumiy ko'rinish", icon: LayoutDashboard },
      { href: "/funnel", label: "Voronka", icon: Filter },
      { href: "/demand", label: "Qondirilmagan talab", icon: Target, min: "analyst" },
      { href: "/carts", label: "Tashlab ketilgan savat", icon: ShoppingCart, min: "analyst" },
      { href: "/searches", label: "Qidiruvlar jurnali", icon: Search, min: "analyst" },
      { href: "/colors-categories", label: "Rang va kategoriya", icon: Palette },
    ],
  },
  {
    title: "Savdo",
    items: [
      { href: "/orders", label: "Buyurtmalar", icon: Receipt, min: "analyst", premium: true },
      { href: "/products", label: "Mahsulotlar", icon: Package, premium: true },
      { href: "/customers", label: "Mijozlar", icon: Contact, min: "analyst" },
    ],
  },
  {
    title: "Marketing",
    items: [
      { href: "/audiences", label: "Auditoriya", icon: UsersRound, min: "analyst" },
      { href: "/campaigns", label: "Kampaniyalar", icon: Megaphone, min: "analyst" },
    ],
  },
  {
    title: "Do'kon",
    items: [
      { href: "/catalog", label: "Katalog", icon: Boxes, basic: true },
      { href: "/integrations", label: "Integratsiya", icon: PlugZap, min: "admin", basic: true },
      { href: "/team", label: "Jamoa", icon: Users, min: "admin" },
      { href: "/settings", label: "Sozlamalar", icon: Settings, min: "admin" },
    ],
  },
  {
    title: "Platforma",
    items: [
      { href: "/admin/tenants", label: "Do'konlar", icon: Building2, superAdmin: true },
      { href: "/admin/ai-models", label: "AI modellar", icon: Cpu, superAdmin: true },
      { href: "/admin/health", label: "Tizim holati", icon: Gauge, superAdmin: true },
      { href: "/admin/audit", label: "Audit jurnali", icon: ScrollText, superAdmin: true },
    ],
  },
];

function useTheme() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  return {
    dark,
    toggle: () => {
      const next = !document.documentElement.classList.contains("dark");
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("vd_theme", next ? "dark" : "light");
      setDark(next);
    },
  };
}

function TenantSwitcher() {
  const { user, tenant, setTenant } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  if (!user || !tenant) return null;
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 text-left hover:bg-subtle">
        <span className="grid h-8 w-8 flex-none place-items-center rounded-lg bg-brand-soft text-sm font-bold uppercase text-brand">{tenant.name[0]}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">{tenant.name}</span>
          <span className="block text-xs text-muted">{tenant.plan === "premium" ? "Premium" : "Oddiy"} · {ROLE_LABELS[tenant.role]}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-muted" />
      </button>
      {open && user.tenants.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 animate-in rounded-xl border border-line bg-surface p-1 shadow-pop">
          {user.tenants.map((t) => (
            <button key={t.id} onClick={() => { setTenant(t.id); setOpen(false); }}
              className={clsx("flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-subtle", t.id === tenant.id && "font-semibold")}>
              <span className="truncate">{t.name}</span>
              {t.plan === "premium" && <span className="text-[10px] font-bold uppercase text-brand">PRO</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, tenant, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const isSuper = user?.platform_role === "super_admin";

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between px-1 pt-1"><Logo /></div>
      <TenantSwitcher />
      <nav className="-mx-1 flex-1 space-y-5 overflow-y-auto px-1">
        {NAV.map((group) => {
          const items = group.items.filter((i) => (i.superAdmin ? isSuper : (!i.min || can(tenant?.role, i.min)) && (!i.premium || tenant?.plan === "premium") && (!i.basic || tenant?.plan !== "premium")));
          if (!items.length || (group.title !== "Platforma" && !tenant)) return null;
          return (
            <div key={group.title}>
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted/80">{group.title}</p>
              <ul className="space-y-0.5">
                {items.map(({ href, label, icon: Icon }) => {
                  const active = pathname === href || pathname.startsWith(href + "/");
                  return (
                    <li key={href}>
                      <Link href={href} onClick={onNavigate}
                        className={clsx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                          active ? "bg-brand-soft text-brand-ink dark:text-brand" : "text-muted hover:bg-subtle hover:text-ink")}>
                        <Icon className="h-[18px] w-[18px]" />{label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
      {tenant?.plan === "premium" && (
        <a href={process.env.NEXT_PUBLIC_STOREFRONT_URL || "http://localhost:3001"} target="_blank" rel="noreferrer"
          className="flex items-center justify-between rounded-xl border border-dashed border-line px-3 py-2.5 text-sm font-medium text-muted hover:border-brand hover:text-brand">
          Do'konni ochish<ExternalLink className="h-4 w-4" />
        </a>
      )}
      <div className="space-y-2 border-t border-line pt-3">
        <div className="flex items-center gap-3 px-1">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-subtle text-xs font-bold uppercase">
            {(user?.full_name || user?.email || "?").slice(0, 1)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.full_name || "Foydalanuvchi"}</p>
            <p className="truncate text-xs text-muted">{user?.email}</p>
          </div>
          {isSuper && <span title="Platforma administratori"><ShieldCheck className="h-4 w-4 text-brand" /></span>}
        </div>
        <div className="flex gap-1">
          <button onClick={toggle} className="btn-ghost h-8 flex-1 text-xs" aria-label="Mavzuni almashtirish">
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}{dark ? "Yorug'" : "Qorong'i"}
          </button>
          <button onClick={logout} className="btn-ghost h-8 flex-1 text-xs"><LogOut className="h-4 w-4" />Chiqish</button>
        </div>
      </div>
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="min-h-screen lg:pl-[264px]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[264px] border-r border-line bg-surface/60 backdrop-blur lg:block">
        <Sidebar />
      </aside>

      <div className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-surface/80 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button className="btn-ghost h-9 w-9 px-0" onClick={() => setMobileOpen(true)} aria-label="Menyu"><Menu className="h-5 w-5" /></button>
      </div>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[280px] animate-in bg-surface shadow-pop">
            <button className="btn-ghost absolute right-3 top-4 h-8 w-8 px-0" onClick={() => setMobileOpen(false)} aria-label="Yopish"><X className="h-4 w-4" /></button>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <main className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
    </div>
  );
}

