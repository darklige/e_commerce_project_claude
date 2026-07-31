"use client";

/**
 * Phase 6 · 审计日志 hooks。
 */

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import type { PaginatedData } from "@/types";
import type { AuditLogOut } from "@/types/admin-user";
import { listAuditLogs, type ListAuditLogsQuery } from "@/lib/admin-user-api";

/**
 * useAuditLogs — 审计日志列表。
 */
export function useAuditLogs(
  query: ListAuditLogsQuery,
  options?: Omit<
    UseQueryOptions<
      PaginatedData<AuditLogOut>,
      Error,
      PaginatedData<AuditLogOut>
    >,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["admin", "audit-logs", query],
    queryFn: () => listAuditLogs(query),
    placeholderData: (prev) => prev,
    ...options,
  });
}
