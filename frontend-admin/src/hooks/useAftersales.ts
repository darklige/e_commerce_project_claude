"use client";

/**
 * Admin 售后相关 React Query hooks。
 *
 * 契约 §9：
 * - useAdminAftersales       — GET /admin/aftersales 列表（多筛选）
 * - useAdminAftersalesDetail — GET /admin/aftersales/{id} 详情
 * - useAftersalesStats       — GET /admin/aftersales/stats/overview 大盘
 *
 * 权限：admin:aftersales:read_all
 */

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import type { PaginatedData } from "@/types";
import type {
  AdminAftersalesDetail,
  AdminAftersalesListItem,
  AftersalesStatsOverview,
} from "@/types/aftersales";
import {
  getAdminAftersales,
  getAftersalesStats,
  listAdminAftersales,
  type ListAdminAftersalesQuery,
} from "@/lib/aftersales-api";

// ---------------------------------------------------------------------------
// 列表
// ---------------------------------------------------------------------------

/**
 * useAdminAftersales — 跨店售后列表。
 *
 * placeholderData 保留上一次结果，翻页 / 筛选切换时避免"闪空"。
 */
export function useAdminAftersales(
  query: ListAdminAftersalesQuery,
  options?: Omit<
    UseQueryOptions<
      PaginatedData<AdminAftersalesListItem>,
      Error,
      PaginatedData<AdminAftersalesListItem>
    >,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["admin", "aftersales-list", query],
    queryFn: () => listAdminAftersales(query),
    placeholderData: (prev) => prev,
    // 工作台性质：30s 轮询，保证仲裁池/状态不陈旧（refetchInterval 对 disabled 查询不生效）
    refetchInterval: 30_000,
    ...options,
  });
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

/**
 * useAdminAftersalesDetail — 单个售后单详情（含 items / history / evidences / messages）。
 */
export function useAdminAftersalesDetail(
  id: string | number | null | undefined,
  options?: Omit<
    UseQueryOptions<AdminAftersalesDetail, Error, AdminAftersalesDetail>,
    "queryKey" | "queryFn" | "enabled"
  >,
) {
  return useQuery({
    queryKey: ["admin", "aftersales", String(id ?? "")],
    queryFn: () => getAdminAftersales(id as string | number),
    enabled: id !== null && id !== undefined && id !== "",
    ...options,
  });
}

// ---------------------------------------------------------------------------
// 大盘统计
// ---------------------------------------------------------------------------

/**
 * useAftersalesStats — 售后大盘 5 个数字。
 *
 * staleTime 30s，与其他 dashboard 卡片保持一致。
 */
export function useAftersalesStats(
  options?: Omit<
    UseQueryOptions<AftersalesStatsOverview, Error, AftersalesStatsOverview>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["admin", "aftersales-stats"],
    queryFn: getAftersalesStats,
    staleTime: 30_000,
    // 工作台性质：30s 轮询（refetchInterval 对 disabled 查询不生效）
    refetchInterval: 30_000,
    ...options,
  });
}
