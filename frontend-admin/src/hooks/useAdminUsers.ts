"use client";

/**
 * Phase 6 · 管理员账号管理 hooks。
 *
 * - useAdminUsers      — 账号列表（role / status / keyword 筛选 + 分页）
 * - useRbacMatrix      — 权限矩阵（角色 → 权限键）
 */

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import type { PaginatedData } from "@/types";
import type { AdminUserOut } from "@/types/admin-user";
import {
  getRbacMatrix,
  listAdminUsers,
  type ListAdminUsersQuery,
} from "@/lib/admin-user-api";
import type { RbacMatrixOut } from "@/types/admin-user";

/**
 * useAdminUsers — 账号列表。
 */
export function useAdminUsers(
  query: ListAdminUsersQuery,
  options?: Omit<
    UseQueryOptions<
      PaginatedData<AdminUserOut>,
      Error,
      PaginatedData<AdminUserOut>
    >,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["admin", "users", query],
    queryFn: () => listAdminUsers(query),
    placeholderData: (prev) => prev,
    ...options,
  });
}

/**
 * useRbacMatrix — 权限矩阵。
 * staleTime 长：矩阵只在角色/权限定义变更时变化。
 */
export function useRbacMatrix(
  options?: Omit<
    UseQueryOptions<RbacMatrixOut, Error, RbacMatrixOut>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["admin", "rbac", "matrix"],
    queryFn: getRbacMatrix,
    staleTime: 5 * 60_000,
    ...options,
  });
}
