/**
 * Phase 6 · 管理员账号管理 / 权限矩阵 / 审计日志 API 封装。
 *
 * 端点与权限：
 * - 账号列表 / 详情        GET  admin/users         → admin:user:read
 * - 创建 / 更新 / 禁用 / 启用 / 重置密码
 *                           POST/PATCH admin/users/* → admin:user:manage
 * - 自助改密               POST admin/users/change-password → 任意登录 admin
 * - 权限矩阵               GET  admin/rbac          → admin:rbac:read
 * - 审计日志               GET  admin/audit-logs    → admin:audit_log:read
 *
 * 级联副作用（后端事务内完成）：
 * - 禁用 / 降级：释放其认领中的仲裁单 + 吊销其全部 refresh token + 写审计 + 通知
 * - 重置密码：吊销全部 refresh token + 通知
 */

import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { PaginatedData } from "@/types";
import type { AdminRole } from "@/lib/rbac";
import type {
  AdminUserOut,
  AuditLogOut,
  ChangeAdminPasswordPayload,
  CreateAdminUserPayload,
  RbacMatrixOut,
  ResetAdminPasswordPayload,
  UpdateAdminUserPayload,
} from "@/types/admin-user";

/** GET /admin/users 查询参数。 */
export interface ListAdminUsersQuery {
  role?: AdminRole;
  status?: "active" | "disabled";
  keyword?: string;
  page?: number;
  size?: number;
}

/**
 * GET /admin/users
 * 权限：admin:user:read
 */
export function listAdminUsers(
  query: ListAdminUsersQuery = {},
): Promise<PaginatedData<AdminUserOut>> {
  const params: Record<string, string | number> = {};
  if (query.role) params.role = query.role;
  if (query.status) params.status = query.status;
  if (query.keyword) params.keyword = query.keyword;
  if (query.page) params.page = query.page;
  if (query.size) params.size = query.size;
  return apiGet<PaginatedData<AdminUserOut>>("admin/users", { searchParams: params });
}

/**
 * GET /admin/users/{id}
 * 权限：admin:user:read
 */
export function getAdminUser(id: number): Promise<AdminUserOut> {
  return apiGet<AdminUserOut>(`admin/users/${id}`);
}

/**
 * POST /admin/users
 * 权限：admin:user:manage
 */
export function createAdminUser(
  payload: CreateAdminUserPayload,
): Promise<AdminUserOut> {
  return apiPost<AdminUserOut, CreateAdminUserPayload>("admin/users", payload);
}

/**
 * PATCH /admin/users/{id}
 * 权限：admin:user:manage
 */
export function updateAdminUser(
  id: number,
  payload: UpdateAdminUserPayload,
): Promise<AdminUserOut> {
  return apiPatch<AdminUserOut, UpdateAdminUserPayload>(`admin/users/${id}`, payload);
}

/**
 * POST /admin/users/{id}/disable
 * 权限：admin:user:manage
 * 级联：释放仲裁单 + 吊销会话 + 审计 + 通知。
 */
export function disableAdminUser(id: number): Promise<AdminUserOut> {
  return apiPost<AdminUserOut>(`admin/users/${id}/disable`);
}

/**
 * POST /admin/users/{id}/enable
 * 权限：admin:user:manage
 */
export function enableAdminUser(id: number): Promise<AdminUserOut> {
  return apiPost<AdminUserOut>(`admin/users/${id}/enable`);
}

/**
 * POST /admin/users/{id}/reset-password
 * 权限：admin:user:manage
 * 返回更新后的账号；前端应提示"目标账号将被强制下线"。
 */
export function resetAdminUserPassword(
  id: number,
  payload: ResetAdminPasswordPayload,
): Promise<AdminUserOut> {
  return apiPost<AdminUserOut, ResetAdminPasswordPayload>(
    `admin/users/${id}/reset-password`,
    payload,
  );
}

/**
 * POST /admin/auth/change-password
 * 权限：任意登录 admin
 * 成功后会吊销自己全部 refresh token，需引导重新登录。
 */
export function changeOwnAdminPassword(
  payload: ChangeAdminPasswordPayload,
): Promise<null> {
  return apiPost<null, ChangeAdminPasswordPayload>(
    "admin/auth/change-password",
    payload,
  );
}

/**
 * GET /admin/rbac
 * 权限：admin:rbac:read
 */
export function getRbacMatrix(): Promise<RbacMatrixOut> {
  return apiGet<RbacMatrixOut>("admin/rbac");
}

/** GET /admin/audit-logs 查询参数。 */
export interface ListAuditLogsQuery {
  actor_type?: string;
  actor_id?: number;
  action?: string;
  target_type?: string;
  target_id?: number;
  page?: number;
  size?: number;
}

/**
 * GET /admin/audit-logs
 * 权限：admin:audit_log:read
 */
export function listAuditLogs(
  query: ListAuditLogsQuery = {},
): Promise<PaginatedData<AuditLogOut>> {
  const params: Record<string, string | number> = {};
  if (query.actor_type) params.actor_type = query.actor_type;
  if (query.actor_id !== undefined) params.actor_id = query.actor_id;
  if (query.action) params.action = query.action;
  if (query.target_type) params.target_type = query.target_type;
  if (query.target_id !== undefined) params.target_id = query.target_id;
  if (query.page) params.page = query.page;
  if (query.size) params.size = query.size;
  return apiGet<PaginatedData<AuditLogOut>>("admin/audit-logs", {
    searchParams: params,
  });
}
