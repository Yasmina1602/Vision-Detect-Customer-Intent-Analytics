"use client";

import { FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import { download } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { can } from "@/lib/format";
import { useRange } from "@/lib/range";
import { Spinner, useToast } from "./ui";

/** Barcha bo'limlar bitta Excel faylda (har biri alohida varaqda), tanlangan sana oralig'i bo'yicha. */
export function ExcelButton({ label = "Excel" }: { label?: string }) {
  const { tenant } = useAuth();
  const { qs } = useRange();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!can(tenant?.role, "analyst")) return null;
  return (
    <button className="btn-secondary" disabled={busy} title="Barcha ma'lumotlarni Excel (.xlsx) faylda yuklab olish"
      onClick={async () => {
        setBusy(true);
        try { await download(`/v1/dashboard/analytics/export.xlsx?${qs}`, "vision-detect.xlsx"); toast("Excel fayl yuklab olindi"); }
        catch (e: any) { toast(e.message, "bad"); }
        finally { setBusy(false); }
      }}>
      {busy ? <Spinner /> : <FileSpreadsheet className="h-4 w-4 text-ok" />}{label}
    </button>
  );
}
