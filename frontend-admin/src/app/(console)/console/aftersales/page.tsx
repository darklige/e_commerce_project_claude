"use client";

/**
 * 平台售后仲裁台 (`/console/aftersales`)。
 *
 * 契约 §9.1 GET /admin/aftersales?status=&type=&shop_id=&user_id=&escalation_reason=&keyword=&page=&size=
 * 契约 §9.6 GET /admin/aftersales/stats/overview
 *
 * UI 要素：
 * - 顶部 4 张统计卡（stats/overview）：
 *   1. 待商家审核数
 *   2. 待仲裁数（arbitrator 为空的 admin_arbitrating）
 *   3. 处理中总数
 *   4. 今日已解决 + 平均解决时长
 * - Status tab（含"待仲裁" tab = admin_arbitrating）
 * - 高级筛选：升级原因 / 店铺 / 用户 / 关键字 / 日期区间
 * - Table：售后单号 + 订单号 + 类型 + 店铺 + 用户 + 状态 + 升级原因 + 已认领仲裁员 + 时长 + 操作
 * - 分页 + URL 同步（与订单大盘保持体验一致）
 * - 需 admin:aftersales:read_all 才能进入
 */

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import clsx from "clsx";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { FormField } from "@/components/ui/FormField";
import { StatCard } from "@/components/console/StatCard";
import { Table, type TableColumn } from "@/components/ui/Table";
import { TakeOverButton } from "@/components/aftersales/TakeOverButton";
import {
  AFTERSALES_STATUS_OPTIONS,
  AftersalesStatusBadge,
} from "@/components/aftersales/AftersalesStatusBadge";
import {
  AftersalesTypeIcon,
} from "@/components/aftersales/AftersalesTypeIcon";
import {
  ESCALATION_REASON_OPTIONS,
  EscalationReasonBadge,
} from "@/components/aftersales/EscalationReasonBadge";
import {
  useAdminAftersales,
  useAftersalesStats,
} from "@/hooks/useAftersales";
import { useAdmin, usePermission } from "@/hooks/useAuth";
import { AdminRole } from "@/lib/rbac";
import type {
  AdminAftersalesListItem,
  AftersalesStatus,
  EscalationReason,
} from "@/types/aftersales";

const PAGE_SIZE = 20;

type StatusKey = "all" | AftersalesStatus;

export default function AdminAftersalesPage() {
  return (
    <RequirePermission permission="admin:aftersales:read_all">
      <Suspense
        fallback={<div className="text-sm text-neutral-400">加载中…</div>}
      >
        <AdminAftersalesInner />
      </Suspense>
    </RequirePermission>
  );
}

function AdminAftersalesInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentAdmin = useAdmin();
  const canArbitrate = usePermission("admin:aftersales:arbitrate");
  // 客服专员数据范围只覆盖 admin_arbitrating（未认领 / 本人认领），
  // 因此其 tab 与统计卡做对应收窄，避免"卡片有数、表格为空"的错觉。
  const isAgent = currentAdmin?.role === AdminRole.CUSTOMER_SERVICE_AGENT;
  const tabs = isAgent
    ? AFTERSALES_STATUS_OPTIONS.filter(
        (t) => t.key === "all" || t.key === "admin_arbitrating",
      )
    : AFTERSALES_STATUS_OPTIONS;

  const initialStatus = (searchParams.get("status") ?? "all") as StatusKey;
  const initialKeyword = searchParams.get("keyword") ?? "";
  const initialShop = searchParams.get("shop_id") ?? "";
  const initialUser = searchParams.get("user_id") ?? "";
  const initialEscalation = (searchParams.get("escalation_reason") ??
    "") as EscalationReason | "";
  const initialStart = searchParams.get("start_date") ?? "";
  const initialEnd = searchParams.get("end_date") ?? "";
  const initialPage = Number(searchParams.get("page") ?? "1") || 1;

  const [status, setStatus] = useState<StatusKey>(initialStatus);
  const [keywordInput, setKeywordInput] = useState(initialKeyword);
  const [debouncedKeyword, setDebouncedKeyword] = useState(initialKeyword);
  const [shopInput, setShopInput] = useState(initialShop);
  const [debouncedShop, setDebouncedShop] = useState(initialShop);
  const [userInput, setUserInput] = useState(initialUser);
  const [debouncedUser, setDebouncedUser] = useState(initialUser);
  const [escalation, setEscalation] = useState<EscalationReason | "">(
    initialEscalation,
  );
  const [startDate, setStartDate] = useState(initialStart);
  const [endDate, setEndDate] = useState(initialEnd);
  const [page, setPage] = useState(initialPage);

  // 输入去抖 300ms
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedKeyword(keywordInput.trim());
      setDebouncedShop(shopInput.trim());
      setDebouncedUser(userInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(handle);
  }, [keywordInput, shopInput, userInput]);

  // URL 同步
  useEffect(() => {
    const params = new URLSearchParams();
    if (status !== "all") params.set("status", status);
    if (debouncedKeyword) params.set("keyword", debouncedKeyword);
    if (debouncedShop) params.set("shop_id", debouncedShop);
    if (debouncedUser) params.set("user_id", debouncedUser);
    if (escalation) params.set("escalation_reason", escalation);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (page !== 1) params.set("page", String(page));
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : "?", { scroll: false });
  }, [
    status,
    debouncedKeyword,
    debouncedShop,
    debouncedUser,
    escalation,
    startDate,
    endDate,
    page,
    router,
  ]);

  const query = useMemo(
    () => ({
      status: status === "all" ? undefined : status,
      keyword: debouncedKeyword || undefined,
      shop_id: debouncedShop || undefined,
      user_id: debouncedUser || undefined,
      escalation_reason: escalation || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      page,
      size: PAGE_SIZE,
    }),
    [
      status,
      debouncedKeyword,
      debouncedShop,
      debouncedUser,
      escalation,
      startDate,
      endDate,
      page,
    ],
  );

  const { data, isLoading, isFetching, isError, refetch } =
    useAdminAftersales(query);
  const stats = useAftersalesStats();

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  const hasAnyFilter =
    debouncedKeyword ||
    debouncedShop ||
    debouncedUser ||
    escalation ||
    startDate ||
    endDate ||
    status !== "all";

  const columns: TableColumn<AdminAftersalesListItem>[] = [
    {
      key: "aftersales_no",
      title: "售后单号 / 订单号",
      render: (row) => (
        <div>
          <div className="font-mono text-xs font-medium text-neutral-900">
            {row.aftersales_no}
          </div>
          <div className="mt-0.5 font-mono text-[11px] text-neutral-500">
            → {row.order_no}
          </div>
          <div className="mt-0.5 text-xs text-neutral-400 tabular-nums">
            {formatDateTime(row.created_at)}
          </div>
        </div>
      ),
    },
    {
      key: "type",
      title: "类型",
      width: 100,
      render: (row) => <AftersalesTypeIcon type={row.type} />,
    },
    {
      key: "shop",
      title: "店铺",
      render: (row) => (
        <div className="text-xs text-neutral-700">
          {row.shop?.name ?? "—"}
          <div className="text-neutral-400">#{row.shop_id}</div>
        </div>
      ),
    },
    {
      key: "user",
      title: "用户",
      render: (row) => (
        <div className="text-xs text-neutral-700">
          <div>
            {row.user?.nickname || <span className="text-neutral-400">—</span>}
            <span className="ml-1 text-neutral-400">#{row.user_id}</span>
          </div>
          {row.user?.phone ? (
            <div className="text-neutral-500 tabular-nums">
              {row.user.phone}
            </div>
          ) : null}
        </div>
      ),
    },
    {
      key: "status",
      title: "状态",
      render: (row) => <AftersalesStatusBadge status={row.status} />,
    },
    {
      key: "escalation",
      title: "升级原因",
      render: (row) =>
        row.escalation_reason ? (
          <EscalationReasonBadge reason={row.escalation_reason} />
        ) : (
          <span className="text-xs text-neutral-400">—</span>
        ),
    },
    {
      key: "arbitrator",
      title: "认领仲裁员",
      render: (row) => {
        if (row.status !== "admin_arbitrating") {
          return <span className="text-xs text-neutral-400">—</span>;
        }
        if (row.arbitrator_admin) {
          return (
            <div className="text-xs">
              <div className="text-neutral-800">
                {row.arbitrator_admin.display_name ??
                  row.arbitrator_admin.username}
              </div>
              <div className="text-neutral-400">
                #{row.arbitrator_admin.id}
              </div>
            </div>
          );
        }
        return (
          <span className="inline-flex items-center rounded bg-[color:var(--color-danger-soft)] px-2 py-0.5 text-xs font-medium text-[color:var(--color-danger)]">
            未认领
          </span>
        );
      },
    },
    {
      key: "duration",
      title: "时长",
      align: "right",
      width: 80,
      render: (row) => (
        <span className="tabular-nums text-xs text-neutral-600">
          {formatDuration(row.created_at, row.closed_at ?? row.refunded_at)}
        </span>
      ),
    },
    {
      key: "actions",
      title: "操作",
      align: "right",
      width: 120,
      render: (row) => {
        const claimable =
          canArbitrate &&
          row.status === "admin_arbitrating" &&
          !row.arbitrator_admin;
        return (
          <div className="flex flex-col items-end gap-1">
            {claimable ? (
              <TakeOverButton
                aftersalesId={row.id}
                alreadyTakenOver={false}
                size="sm"
              />
            ) : null}
            <Link
              href={`/console/aftersales/${row.id}`}
              className="text-[color:var(--color-info)] hover:underline"
            >
              查看详情
            </Link>
          </div>
        );
      },
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">
            售后仲裁台
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            平台售后总览，支持认领仲裁、裁决、强制退款与内部备注。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          loading={isFetching && !isLoading}
        >
          刷新
        </Button>
      </header>

      {/* 客服专员数据范围提示 */}
      {isAgent ? (
        <div className="rounded border border-[color:var(--color-info-100)] bg-[color:var(--color-info-50)] px-3 py-2 text-xs text-[color:var(--color-info-800)]">
          您为客服专员：仅可见未认领或由您认领的仲裁单；表格每 30 秒自动刷新。
        </div>
      ) : null}

      {/* 统计卡 */}
      <section
        aria-label="售后大盘"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        {isAgent ? (
          <>
            <StatCard
              label="可认领仲裁"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.escalated_pending_count ?? 0)
              }
              hint="尚未被认领、可接手处理"
              tone="danger"
            />
            <StatCard
              label="我的在办"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.in_progress_count ?? 0)
              }
              hint="未认领 + 本人认领的仲裁中"
              tone="info"
            />
          </>
        ) : (
          <>
            <StatCard
              label="待商家审核"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.pending_review_count ?? 0)
              }
              hint="pending_merchant_review 状态数"
              tone="warning"
            />
            <StatCard
              label="待仲裁"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.escalated_pending_count ?? 0)
              }
              hint="已升级到平台且尚未认领"
              tone="danger"
            />
            <StatCard
              label="处理中总数"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.in_progress_count ?? 0)
              }
              hint="非最终态售后单总数"
              tone="info"
            />
            <StatCard
              label="今日已解决"
              value={
                stats.isLoading
                  ? "…"
                  : stats.isError
                    ? "—"
                    : String(stats.data?.resolved_today_count ?? 0)
              }
              hint={
                stats.isLoading || stats.isError
                  ? "平均解决时长 —"
                  : `平均解决时长 ${(stats.data?.avg_resolution_hours ?? 0).toFixed(
                      1,
                    )} h`
              }
              tone="success"
            />
          </>
        )}
      </section>

      {/* Status tab */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[color:var(--color-border)]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => {
              setStatus(tab.key);
              setPage(1);
            }}
            className={clsx(
              "-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm transition",
              status === tab.key
                ? "border-[color:var(--color-primary)] text-[color:var(--color-primary)] font-medium"
                : "border-transparent text-neutral-500 hover:text-neutral-800",
            )}
            aria-current={status === tab.key ? "page" : undefined}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 筛选区 */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-white p-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
          <FormField label="关键字（售后号 / 订单号 / 用户手机邮箱）">
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="例如 AS20260723… 或 138…"
              aria-label="关键字"
            />
          </FormField>
          <FormField label="升级原因">
            <select
              value={escalation}
              onChange={(e) => {
                setEscalation(e.target.value as EscalationReason | "");
                setPage(1);
              }}
              className="block h-8 w-full rounded border border-[color:var(--color-border)] bg-white px-2 text-sm outline-none focus:border-[color:var(--color-primary)] focus:ring-1 focus:ring-[color:var(--color-primary)]/20"
              aria-label="升级原因"
            >
              <option value="">全部</option>
              {ESCALATION_REASON_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="店铺 ID">
            <Input
              value={shopInput}
              onChange={(e) =>
                setShopInput(e.target.value.replace(/\D/g, ""))
              }
              placeholder="例如 12"
              aria-label="店铺 ID"
              inputMode="numeric"
            />
          </FormField>
          <FormField label="用户 ID">
            <Input
              value={userInput}
              onChange={(e) =>
                setUserInput(e.target.value.replace(/\D/g, ""))
              }
              placeholder="例如 5001"
              aria-label="用户 ID"
              inputMode="numeric"
            />
          </FormField>
          <FormField label="创建日期起">
            <Input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setPage(1);
              }}
              aria-label="创建日期起"
              max={endDate || undefined}
            />
          </FormField>
          <FormField label="创建日期止">
            <Input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setPage(1);
              }}
              aria-label="创建日期止"
              min={startDate || undefined}
            />
          </FormField>
        </div>
        {hasAnyFilter ? (
          <div className="mt-2 flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setStatus("all");
                setKeywordInput("");
                setShopInput("");
                setUserInput("");
                setEscalation("");
                setStartDate("");
                setEndDate("");
                setPage(1);
              }}
            >
              清空所有筛选
            </Button>
          </div>
        ) : null}
      </div>

      {isError ? (
        <div className="rounded border border-red-200 bg-[color:var(--color-danger-soft)] px-3 py-2 text-xs text-[color:var(--color-danger)]">
          加载失败，请点击右上角「刷新」重试。
        </div>
      ) : null}

      <Table
        columns={columns}
        rows={rows}
        loading={isLoading}
        rowKey={(row) => row.id}
        emptyText={
          isAgent
            ? "当前没有待认领或由您认领的仲裁单，表格会每 30 秒自动刷新，有新单会自动出现。"
            : "暂无符合条件的售后单"
        }
        pagination={{
          page,
          size: PAGE_SIZE,
          total,
          onPageChange: setPage,
        }}
      />
    </div>
  );
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

/**
 * 计算售后单已经进行的时长（人性化：<24h → xh，>=24h → xd yh）。
 * end 为空时按 now 计算。
 */
function formatDuration(startIso: string, endIso?: string | null): string {
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return "—";
  }
  const diffMs = end - start;
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) {
    const minutes = Math.max(1, Math.floor(diffMs / 60_000));
    return `${minutes}m`;
  }
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return remainingHours ? `${days}d ${remainingHours}h` : `${days}d`;
}
