"use client";

/**
 * 权限矩阵 (`/console/rbac`)。
 *
 * 契约（Phase 6）：GET /admin/rbac → { roles: { [role]: { label, permissions } }, permissions: [{ key, label }] }
 * 权限：admin:rbac:read（TECH_ADMIN 及以上可见）
 *
 * 交互：
 * - 行 = 权限项，列 = 角色，单元格 = 是否拥有
 * - 展示角色说明（description 由前端 ADMIN_ROLE_META 补充）
 * - 只读矩阵，不在此页改权限（权限由代码 + 后端下发）
 */

import { useMemo } from "react";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { Badge } from "@/components/ui/Badge";
import { useRbacMatrix } from "@/hooks/useAdminUsers";
import { ADMIN_ROLE_META } from "@/lib/rbac";
import type { RbacMatrixOut } from "@/types/admin-user";

export default function AdminRbacPage() {
  return (
    <RequirePermission permission="admin:rbac:read">
      <AdminRbacInner />
    </RequirePermission>
  );
}

function AdminRbacInner() {
  const { data, isLoading, isError, refetch } = useRbacMatrix();

  const roles = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.roles).map(([key, meta]) => ({
      key,
      label: meta.label,
      permissions: new Set(meta.permissions),
    }));
  }, [data]);

  const perms = data?.permissions ?? [];

  if (isError) {
    return (
      <div className="rounded border border-red-200 bg-[color:var(--color-danger-soft)] px-3 py-2 text-xs text-[color:var(--color-danger)]">
        权限矩阵加载失败，请刷新重试。
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">权限矩阵</h1>
          <p className="mt-1 text-sm text-neutral-500">
            角色 → 权限映射总览（只读）。实际生效权限以后端下发为准。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-md border border-[color:var(--color-border)] bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            disabled={isLoading}
          >
            刷新
          </button>
        </div>
      </header>

      {/* 角色说明卡片 */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {roles.map((role) => {
          const meta = ADMIN_ROLE_META[role.key as keyof typeof ADMIN_ROLE_META];
          if (!meta) return null;
          return (
            <div
              key={role.key}
              className="rounded-md border border-[color:var(--color-border)] bg-white p-3"
            >
              <div className="flex items-center gap-2">
                <Badge tone={meta.tone}>{meta.label}</Badge>
                <span className="text-xs text-neutral-400 tabular-nums">
                  {role.permissions.size} 项权限
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-neutral-500">
                {meta.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* 矩阵 */}
      <div className="overflow-hidden rounded-md border border-[color:var(--color-border)] bg-white">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-[color:var(--color-border)] bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
                <th scope="col" className="whitespace-nowrap px-3 py-2">
                  权限
                </th>
                {roles.map((role) => (
                  <th key={role.key} scope="col" className="whitespace-nowrap px-3 py-2 text-center">
                    {role.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? null
                : perms.map((perm) => (
                    <tr
                      key={perm.key}
                      className="border-b border-[color:var(--color-border)] hover:bg-neutral-50"
                    >
                      <td className="px-3 py-2 text-neutral-800">
                        <div className="flex flex-col gap-0.5">
                          <span>{perm.label}</span>
                          <span className="font-mono text-[11px] text-neutral-400">
                            {perm.key}
                          </span>
                        </div>
                      </td>
                      {roles.map((role) => (
                        <td
                          key={role.key}
                          className="px-3 py-2 text-center text-neutral-800"
                        >
                          {role.permissions.has(perm.key) ? (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-[11px] font-bold text-green-700">
                              ✓
                            </span>
                          ) : (
                            <span className="text-neutral-300">—</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        {isLoading ? (
          <div className="px-4 py-10 text-center text-sm text-neutral-400">
            加载中…
          </div>
        ) : null}
      </div>
    </div>
  );
}
