"use client";

import { ShieldOff } from "lucide-react";
import { Empty } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.platform_role !== "super_admin") {
    return <Empty icon={<ShieldOff className="h-6 w-6" />} title="Ruxsat yo'q" text="Bu bo'lim faqat platforma administratorlari uchun." />;
  }
  return <>{children}</>;
}
