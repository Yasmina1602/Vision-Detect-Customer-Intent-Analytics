"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo } from "@/components/Logo";
import { Shell } from "@/components/Shell";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading || user) return;
    // O'zi chiqqan foydalanuvchi uchun "next" saqlanmaydi (keyingi kirgan odam boshqa sahifaga tushib qolmasin)
    const loggedOut = sessionStorage.getItem("vd_logged_out");
    sessionStorage.removeItem("vd_logged_out");
    router.replace(loggedOut ? "/login" : `/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="flex flex-col items-center gap-4 text-muted"><Logo /><Spinner /></div>
      </div>
    );
  }
  return <Shell>{children}</Shell>;
}
