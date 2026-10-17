"use client";

import { Card, Empty, PageHeader, Skeleton } from "@/components/ui";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function AuditPage() {
  const { data } = useApi<any>("/v1/admin/audit?limit=200");
  return (
    <>
      <PageHeader title="Audit jurnali" description="Kalitlar, rollar, eksport va sozlamalar bo'yicha barcha nozik amallar" />
      <Card pad={false}>
        {!data ? <div className="p-5"><Skeleton className="h-60" /></div> : data.items.length === 0 ? <Empty title="Yozuv yo'q" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead className="border-b border-line bg-subtle/50"><tr>
                <th className="th">Vaqt</th><th className="th">Kim</th><th className="th">Amal</th><th className="th">Obyekt</th><th className="th">IP</th>
              </tr></thead>
              <tbody className="divide-y divide-line">
                {data.items.map((a: any) => (
                  <tr key={a.id}>
                    <td className="td whitespace-nowrap text-muted">{dateTime(a.created_at)}</td>
                    <td className="td">{a.actor || "—"}</td>
                    <td className="td"><code className="rounded bg-subtle px-1.5 py-0.5 text-xs">{a.action}</code></td>
                    <td className="td max-w-[280px] truncate text-xs text-muted" title={JSON.stringify(a.meta)}>{a.target || (a.meta ? JSON.stringify(a.meta) : "—")}</td>
                    <td className="td font-mono text-xs text-muted">{a.ip || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
