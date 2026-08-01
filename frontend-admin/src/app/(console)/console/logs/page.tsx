"use client";

/**
 * 审计日志 (`/console/logs`)。
 *
 * 契约（Phase 6）：GET /admin/audit-logs
 *   query: actor_type / actor_id / action / target_type / target_id / page / size
 *   权限：admin:audit_log:read（TECH_ADMIN / SUPER_ADMIN）
 *
 * 交互：
 * - 顶部筛选：操作码（模糊）、主体类型、对象类型
 * - 表格：时间、主体、操作、对象、IP、附加信息
 * - 操作码高亮（mono），未知操作原样展示
 */

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Table, type TableColumn } from "@/components/ui/Table";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import type { AuditLogOut } from "@/types/admin-user";

const PAGE_SIZE = 20;

const ACTOR_TYPE_OPTIONS: { value: AuditLogOut["actor_type"]; label: string }[] = [
  { value: "admin", label: "管理员" },
  { value: "user", label: "用户" },
  { value: "merchant", label: "商家" },
  { value: "system", label: "系统" },
  { value: "anonymous", label: "匿名" },
];

const TARGET_TYPE_OPTIONS = [
  "user",
  "merchant",
  "order",
  "aftersales",
  "spu",
  "review",
  "notification",
  "admin_user",
  "arbitration",
].map((v) => ({ value: v, label: v }));

export default function AdminLogsPage() {
  return (
    <RequirePermission permission="admin:audit_log:read">
      <Suspense fallback={<div className="text-sm text-neutral-400">加载中…</div>}>
        <AdminLogsInner />
      </Suspense>
    </RequirePermission>
  );
}

function AdminLogsInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialAction = searchParams.get("action") ?? "";
  const initialActorType = (searchParams.get("actor_type") ?? "") as
    | AuditLogOut["actor_type"]
    | "";
  const initialTargetType = (searchParams.get("target_type") ?? "") as string;
  const initialPage = Number(searchParams.get("page") ?? "1") || 1;

  const [action, setAction] = useState(initialAction);
  const [actorType, setActorType] = useState(initialActorType);
  const [targetType, setTargetType] = useState(initialTargetType);
  const [page, setPage] = useState(initialPage);

  const syncUrl = () => {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (actorType) params.set("actor_type", actorType);
    if (targetType) params.set("target_type", targetType);
    if (page !== 1) params.set("page", String(page));
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : "?", { scroll: false });
  };

  const query = useMemo(
    () => ({
      action: action.trim() || undefined,
      actor_type: actorType || undefined,
      target_type: targetType || undefined,
      page,
      size: PAGE_SIZE,
    }),
    [action, actorType, targetType, page],
  );

  const { data, isLoading, isFetching, isError, refetch } = useAuditLogs(query);
  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  const columns: TableColumn<AuditLogOut>[] = [
    {
      key: "created_at",
      title: "时间",
      width: 170,
      render: (row) => (
        <span className="text-neutral-700 tabular-nums">
          {formatDateTime(row.created_at)}
        </span>
      ),
    },
    {
      key: "actor",
      title: "操作者",
      width: 150,
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <Badge tone={actorBadgeTone(row.actor_type)}>
            {actorTypeLabel(row.actor_type)}
          </Badge>
          <span className="text-neutral-700 tabular-nums">
            {row.actor_id ?? "-"}
          </span>
        </div>
      ),
    },
    {
      key: "action",
      title: "操作",
      width: 220,
      render: (row) => (
        <span className="font-mono text-xs text-neutral-800">{row.action}</span>
      ),
    },
    {
      key: "target",
      title: "对象",
      width: 160,
      render: (row) =>
        row.target_type ? (
          <div className="flex items-center gap-1.5">
            <span className="text-neutral-600">{row.target_type}</span>
            <span className="text-neutral-400 tabular-nums">
              #{row.target_id ?? "-"}
            </span>
          </div>
        ) : (
          <span className="text-neutral-400">—</span>
        ),
    },
    {
      key: "ip",
      title: "IP",
      width: 140,
      render: (row) => (
        <span className="font-mono text-xs text-neutral-500 tabular-nums">
          {row.ip ?? "-"}
        </span>
      ),
    },
    {
      key: "extra",
      title: "附加信息",
      render: (row) => {
        const text = describeExtra(row.extra);
        return text ? (
          <span className="text-neutral-500">{text}</span>
        ) : (
          <span className="text-neutral-300">—</span>
        );
      },
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">审计日志</h1>
          <p className="mt-1 text-sm text-neutral-500">
            平台关键操作记录（账号、权限、仲裁、资金类变更），日志不可修改。
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

      {/* 筛选 */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-white p-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <FormField label="操作码">
            <Input
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
              onBlur={syncUrl}
              placeholder="如 ADMIN_USER_DISABLE"
              aria-label="操作码筛选"
            />
          </FormField>
          <FormField label="操作者类型">
            <select
              value={actorType}
              onChange={(e) => {
                setActorType(e.target.value as AuditLogOut["actor_type"] | "");
                setPage(1);
              }}
              onBlur={syncUrl}
              className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
            >
              <option value="">全部</option>
              {ACTOR_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="对象类型">
            <select
              value={targetType}
              onChange={(e) => {
                setTargetType(e.target.value);
                setPage(1);
              }}
              onBlur={syncUrl}
              className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
            >
              <option value="">全部</option>
              {TARGET_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FormField>
          <div className="flex items-end">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setAction("");
                setActorType("");
                setTargetType("");
                setPage(1);
                router.replace("?", { scroll: false });
              }}
            >
              重置筛选
            </Button>
          </div>
        </div>
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
        emptyText="暂无符合条件的日志"
        pagination={{ page, size: PAGE_SIZE, total, onPageChange: setPage }}
      />
    </div>
  );
}

function actorTypeLabel(t: AuditLogOut["actor_type"]): string {
  switch (t) {
    case "admin":
      return "管理员";
    case "user":
      return "用户";
    case "merchant":
      return "商家";
    case "system":
      return "系统";
    case "anonymous":
      return "匿名";
    default:
      return t;
  }
}

function actorBadgeTone(
  t: AuditLogOut["actor_type"],
): "primary" | "default" | "warning" | "info" | "danger" {
  switch (t) {
    case "admin":
      return "primary";
    case "system":
      return "info";
    case "user":
      return "default";
    case "merchant":
      return "warning";
    case "anonymous":
      return "danger";
    default:
      return "default";
  }
}

function describeExtra(extra: Record<string, unknown> | null): string {
  if (!extra) return "";
  const entries = Object.entries(extra).slice(0, 3);
  return entries.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" ");
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
