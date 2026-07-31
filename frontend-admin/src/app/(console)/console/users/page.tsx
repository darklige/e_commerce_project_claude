"use client";

/**
 * 管理员账号管理 (`/console/users`)。
 *
 * 契约（Phase 6）：
 * - GET    /admin/users                      → admin:user:read
 * - POST   /admin/users                      → admin:user:manage
 * - PATCH  /admin/users/{id}                 → admin:user:manage
 * - POST   /admin/users/{id}/disable|enable  → admin:user:manage
 * - POST   /admin/users/{id}/reset-password  → admin:user:manage
 *
 * 交互：
 * - 顶部筛选：角色 / 状态 / 关键词
 * - 表格：账号、显示名、角色、状态、最后登录、密码变更时间、创建时间、操作
 * - 「新建账号」弹窗：用户名 / 显示名 / 角色 / 初始密码
 * - 行内操作：编辑（角色 / 显示名）、启用 / 禁用、重置密码
 * - 角色变更 / 禁用会级联释放其认领中的仲裁单并强制下线（弹窗内明示）
 * - 禁止操作自己的账号（后端 4003 兜底）
 * - 无 admin:user:manage 的角色（TECH_ADMIN）只读
 */

import { Suspense, useMemo, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Modal } from "@/components/ui/Modal";
import { Table, type TableColumn } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import { useAdminUsers } from "@/hooks/useAdminUsers";
import {
  ADMIN_ROLE_META,
  AdminRole,
  hasPermission,
  type Permission,
} from "@/lib/rbac";
import {
  createAdminUser,
  disableAdminUser,
  enableAdminUser,
  resetAdminUserPassword,
  updateAdminUser,
} from "@/lib/admin-user-api";
import { ApiError } from "@/lib/api";
import { getErrorMessage } from "@/types/errors";
import { useAuthStore } from "@/lib/auth-store";
import type { AdminUserOut } from "@/types/admin-user";

const PAGE_SIZE = 20;

const PWD_REGEX = /^(?=.*[A-Za-z])(?=.*\d)[\S]{8,64}$/;

const ROLE_OPTIONS = Object.values(AdminRole);
const STATUS_OPTIONS = [
  { value: "active", label: "启用" },
  { value: "disabled", label: "禁用" },
];

export default function AdminUsersPage() {
  return (
    <RequirePermission
      permissions={["admin:user:read", "admin:user:manage"]}
      mode="any"
    >
      <Suspense
        fallback={<div className="text-sm text-neutral-400">加载中…</div>}
      >
        <AdminUsersInner />
      </Suspense>
    </RequirePermission>
  );
}

function AdminUsersInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();
  const queryClient = useQueryClient();
  const permissions = useAuthStore((s) => s.permissions);
  const currentAdminId = useAuthStore((s) => s.admin?.id);

  const canManage = hasPermission(permissions, "admin:user:manage" as Permission);

  const initialRole = (searchParams.get("role") ?? "") as AdminRole | "";
  const initialStatus = (searchParams.get("status") ?? "") as
    | "active"
    | "disabled"
    | "";
  const initialKeyword = searchParams.get("keyword") ?? "";
  const initialPage = Number(searchParams.get("page") ?? "1") || 1;

  const [role, setRole] = useState<AdminRole | "">(initialRole);
  const [status, setStatus] = useState<"active" | "disabled" | "">(initialStatus);
  const [keyword, setKeyword] = useState(initialKeyword);
  const [page, setPage] = useState(initialPage);

  const syncUrl = (patch: { role?: string; status?: string; keyword?: string; page?: number }) => {
    const params = new URLSearchParams();
    const merged = { role, status, keyword, page, ...patch };
    if (merged.role) params.set("role", merged.role);
    if (merged.status) params.set("status", merged.status);
    if (merged.keyword) params.set("keyword", merged.keyword);
    if (merged.page && merged.page !== 1) params.set("page", String(merged.page));
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : "?", { scroll: false });
  };

  const query = useMemo(
    () => ({
      role: role || undefined,
      status: status || undefined,
      keyword: keyword.trim() || undefined,
      page,
      size: PAGE_SIZE,
    }),
    [role, status, keyword, page],
  );

  const { data, isLoading, isFetching, isError, refetch } = useAdminUsers(query);
  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
  };

  // ---- create / edit / reset / disable / enable ----
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<AdminUserOut | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUserOut | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<{
    row: AdminUserOut;
    action: "disable" | "enable";
  } | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const resetPasswordError =
    resetPassword && !PWD_REGEX.test(resetPassword)
      ? "密码需 8-64 位，且同时包含字母和数字"
      : null;

  const [form, setForm] = useState({
    username: "",
    display_name: "",
    role: AdminRole.TECH_ADMIN,
    password: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const createMutation = useMutation({
    mutationFn: () =>
      createAdminUser({
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        role: form.role,
        password: form.password,
      }),
    onSuccess: (row) => {
      setCreateOpen(false);
      setForm({ username: "", display_name: "", role: AdminRole.TECH_ADMIN, password: "" });
      toast.push({ type: "success", message: `已创建账号 ${row.username}` });
      invalidate();
    },
    onError: (err) => {
      toast.push({ type: "error", message: apiErrorMsg(err) });
    },
  });

  const editMutation = useMutation({
    mutationFn: (row: AdminUserOut) =>
      updateAdminUser(row.id, {
        display_name: row.display_name,
        role: row.role,
      }),
    onSuccess: (row) => {
      setEditTarget(null);
      toast.push({ type: "success", message: "账号信息已更新" });
      invalidate();
    },
    onError: (err) => {
      toast.push({ type: "error", message: apiErrorMsg(err) });
    },
  });

  const resetMutation = useMutation({
    mutationFn: ({ id, new_password }: { id: number; new_password: string }) =>
      resetAdminUserPassword(id, { new_password }),
    onSuccess: () => {
      setResetTarget(null);
      toast.push({
        type: "success",
        message: "密码已重置，目标账号将被强制下线",
      });
      invalidate();
    },
    onError: (err) => {
      toast.push({ type: "error", message: apiErrorMsg(err) });
    },
  });

  const resetPasswordValid = PWD_REGEX.test(resetPassword);

  const toggleMutation = useMutation({
    mutationFn: ({ row, action }: { row: AdminUserOut; action: "disable" | "enable" }) =>
      action === "disable" ? disableAdminUser(row.id) : enableAdminUser(row.id),
    onSuccess: (_row, vars) => {
      setConfirmTarget(null);
      toast.push({
        type: "success",
        message: vars.action === "disable" ? "账号已禁用" : "账号已启用",
      });
      invalidate();
    },
    onError: (err) => {
      toast.push({ type: "error", message: apiErrorMsg(err) });
    },
  });

  const validateCreate = (): boolean => {
    const next: Record<string, string> = {};
    if (!/^[A-Za-z0-9_]{1,60}$/.test(form.username.trim())) {
      next.username = "用户名仅限字母、数字、下划线（1-60 位）";
    }
    if (!form.display_name.trim()) next.display_name = "请输入显示名";
    if (!PWD_REGEX.test(form.password)) {
      next.password = "密码需 8-64 位，且同时包含字母和数字";
    }
    setFormErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmitCreate = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateCreate()) return;
    createMutation.mutate();
  };

  const columns: TableColumn<AdminUserOut>[] = [
    {
      key: "username",
      title: "账号",
      width: 200,
      render: (row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium tabular-nums text-neutral-900">
            {row.username}
          </span>
          {row.id === currentAdminId ? <Badge tone="info">自己</Badge> : null}
        </div>
      ),
    },
    {
      key: "display_name",
      title: "显示名",
      width: 160,
      render: (row) => <span className="text-neutral-700">{row.display_name}</span>,
    },
    {
      key: "role",
      title: "角色",
      width: 140,
      render: (row) => {
        const meta = ADMIN_ROLE_META[row.role];
        return <Badge tone={meta.tone}>{meta.label}</Badge>;
      },
    },
    {
      key: "status",
      title: "状态",
      width: 100,
      render: (row) => (
        <Badge tone={row.status === "active" ? "success" : "danger"}>
          {row.status === "active" ? "启用" : "禁用"}
        </Badge>
      ),
    },
    {
      key: "password_changed_at",
      title: "密码状态",
      width: 140,
      render: (row) =>
        row.password_changed_at ? (
          <span className="text-xs text-neutral-500 tabular-nums">
            已改 · {formatDateTime(row.password_changed_at)}
          </span>
        ) : (
          <Badge tone="warning">初始密码待修改</Badge>
        ),
    },
    {
      key: "last_login_at",
      title: "最后登录",
      width: 150,
      render: (row) => (
        <span className="text-xs text-neutral-500 tabular-nums">
          {row.last_login_at ? formatDateTime(row.last_login_at) : "从未登录"}
        </span>
      ),
    },
    {
      key: "created_at",
      title: "创建时间",
      width: 150,
      render: (row) => (
        <span className="text-xs text-neutral-500 tabular-nums">
          {formatDateTime(row.created_at)}
        </span>
      ),
    },
    {
      key: "actions",
      title: "操作",
      align: "right",
      width: 220,
      render: (row) => {
        const isSelf = row.id === currentAdminId;
        return (
          <div className="flex items-center justify-end gap-1">
            {canManage && !isSelf ? (
              <>
                <Button size="sm" variant="ghost" onClick={() => setEditTarget(row)}>
                  编辑
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setResetTarget(row)}>
                  重置密码
                </Button>
                <Button
                  size="sm"
                  variant={row.status === "active" ? "danger" : "ghost"}
                  onClick={() =>
                    setConfirmTarget({
                      row,
                      action: row.status === "active" ? "disable" : "enable",
                    })
                  }
                >
                  {row.status === "active" ? "禁用" : "启用"}
                </Button>
              </>
            ) : null}
          </div>
        );
      },
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">管理员账号</h1>
          <p className="mt-1 text-sm text-neutral-500">
            管理平台运营账号。禁用 / 降级会释放其认领中的仲裁单并强制下线；技术管理员仅可查看。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            loading={isFetching && !isLoading}
          >
            刷新
          </Button>
          {canManage ? (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              新建账号
            </Button>
          ) : null}
        </div>
      </header>

      {/* 筛选 */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-white p-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <FormField label="角色">
            <select
              value={role}
              onChange={(e) => {
                setRole(e.target.value as AdminRole | "");
                setPage(1);
                syncUrl({ role: e.target.value });
              }}
              className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
            >
              <option value="">全部角色</option>
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {ADMIN_ROLE_META[r].label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="状态">
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as "active" | "disabled" | "");
                setPage(1);
                syncUrl({ status: e.target.value });
              }}
              className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
            >
              <option value="">全部状态</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="关键词">
            <Input
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value);
                setPage(1);
                syncUrl({ keyword: e.target.value });
              }}
              placeholder="用户名 / 显示名"
              aria-label="关键词筛选"
            />
          </FormField>
          <div className="flex items-end">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setRole("");
                setStatus("");
                setKeyword("");
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
        emptyText="暂无符合条件的账号"
        pagination={{ page, size: PAGE_SIZE, total, onPageChange: setPage }}
      />

      {/* 新建账号 */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="新建管理员账号"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
              取消
            </Button>
            <Button
              type="submit"
              form="admin-create-form"
              loading={createMutation.isPending}
            >
              创建
            </Button>
          </>
        }
      >
        <form
          id="admin-create-form"
          onSubmit={onSubmitCreate}
          noValidate
          className="flex flex-col gap-4"
        >
          <FormField label="用户名" required error={formErrors.username}>
            <Input
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              placeholder="字母、数字、下划线"
              autoComplete="off"
            />
          </FormField>
          <FormField label="显示名" required error={formErrors.display_name}>
            <Input
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              placeholder="例如：客服张三"
            />
          </FormField>
          <FormField label="角色" required>
            <select
              value={form.role}
              onChange={(e) =>
                setForm((f) => ({ ...f, role: e.target.value as AdminRole }))
              }
              className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {ADMIN_ROLE_META[r].label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="初始密码"
            required
            error={formErrors.password}
            description="8-64 位，至少包含 1 个字母和 1 个数字"
          >
            <PasswordInput
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              autoComplete="new-password"
            />
          </FormField>
        </form>
      </Modal>

      {/* 编辑 */}
      <Modal
        open={editTarget !== null}
        onClose={() => setEditTarget(null)}
        title={editTarget ? `编辑账号 · ${editTarget.username}` : "编辑账号"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditTarget(null)} disabled={editMutation.isPending}>
              取消
            </Button>
            <Button
              loading={editMutation.isPending}
              onClick={() => editTarget && editMutation.mutate(editTarget)}
            >
              保存
            </Button>
          </>
        }
      >
        {editTarget ? (
          <div className="flex flex-col gap-4">
            <FormField label="显示名" required>
              <Input
                value={editTarget.display_name}
                onChange={(e) =>
                  setEditTarget({ ...editTarget, display_name: e.target.value })
                }
              />
            </FormField>
            <FormField
              label="角色"
              required
              description="降级为无仲裁权限的角色（或禁用）会释放该账号认领中的仲裁单并强制其下线。"
            >
              <select
                value={editTarget.role}
                onChange={(e) =>
                  setEditTarget({ ...editTarget, role: e.target.value as AdminRole })
                }
                className="h-8 rounded border border-[color:var(--color-border)] bg-white px-2 text-sm text-neutral-800"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {ADMIN_ROLE_META[r].label}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        ) : null}
      </Modal>

      {/* 重置密码 */}
      <Modal
        open={resetTarget !== null}
        onClose={() => setResetTarget(null)}
        title={resetTarget ? `重置密码 · ${resetTarget.username}` : "重置密码"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setResetTarget(null)} disabled={resetMutation.isPending}>
              取消
            </Button>
            <Button
              loading={resetMutation.isPending}
              disabled={!resetPasswordValid}
              onClick={() =>
                resetTarget &&
                resetMutation.mutate({
                  id: resetTarget.id,
                  new_password: resetPassword,
                })
              }
            >
              重置
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            重置后该账号的所有登录会话将立即失效，需使用新密码重新登录。此操作不可撤销。
          </div>
          <ResetPasswordForm
            value={resetPassword}
            onChange={setResetPassword}
            error={resetPasswordError}
          />
        </div>
      </Modal>

      {/* 禁用 / 启用确认 */}
      <Modal
        open={confirmTarget !== null}
        onClose={() => setConfirmTarget(null)}
        closeOnOverlay={false}
        title={confirmTarget?.action === "disable" ? "禁用账号" : "启用账号"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmTarget(null)} disabled={toggleMutation.isPending}>
              取消
            </Button>
            <Button
              variant={confirmTarget?.action === "disable" ? "danger" : "primary"}
              loading={toggleMutation.isPending}
              onClick={() => confirmTarget && toggleMutation.mutate(confirmTarget)}
            >
              确认{confirmTarget?.action === "disable" ? "禁用" : "启用"}
            </Button>
          </>
        }
      >
        {confirmTarget ? (
          <div className="text-sm text-neutral-700">
            {confirmTarget.action === "disable" ? (
              <>
                确定要禁用账号{" "}
                <strong className="text-neutral-900">
                  {confirmTarget.row.username}
                </strong>
                （{ADMIN_ROLE_META[confirmTarget.row.role].label}）吗？禁用会立即释放其认领中的仲裁单并强制下线。
              </>
            ) : (
              <>
                确定要启用账号{" "}
                <strong className="text-neutral-900">
                  {confirmTarget.row.username}
                </strong>{" "}
                吗？
              </>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function ResetPasswordForm({
  value,
  onChange,
  error,
}: {
  value: string;
  onChange: (v: string) => void;
  error: string | null;
}) {
  return (
    <FormField
      label="新密码"
      required
      error={error}
      description="8-64 位，至少包含 1 个字母和 1 个数字"
    >
      <PasswordInput
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="new-password"
      />
    </FormField>
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

function apiErrorMsg(err: unknown): string {
  return err instanceof ApiError
    ? getErrorMessage(err.code, err.message)
    : "网络异常，请稍后重试";
}
