"use client";

import useSWR, { SWRConfiguration } from "swr";
import { fetcher } from "./api";
import { useAuth } from "./auth";

/** Tenantga bog'langan so'rov: tenant almashsa kesh kaliti ham almashadi. */
export function useApi<T = any>(path: string | null, opts?: SWRConfiguration) {
  const { tenant, user } = useAuth();
  const key = path && user ? [path, tenant?.id ?? "-"] : null;
  return useSWR<T>(key, ([p]: [string]) => fetcher(p), { revalidateOnFocus: false, keepPreviousData: true, ...opts });
}
