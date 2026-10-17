"use client";

import { ToastProvider } from "@/components/ui";
import { AuthProvider } from "@/lib/auth";
import { RangeProvider } from "@/lib/range";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <RangeProvider>
        <ToastProvider>{children}</ToastProvider>
      </RangeProvider>
    </AuthProvider>
  );
}
