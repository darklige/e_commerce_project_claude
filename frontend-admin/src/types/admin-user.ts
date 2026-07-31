/**
 * Phase 6 · 管理员账号管理 / 权限矩阵 / 审计日志 类型定义。
 *
 * 契约对应后端新增端点：
 * - GET    /admin/users                (admin:user:read)
 * - POST   /admin/users                (admin:user:manage)
 * - GET    /admin/users/{id}           (admin:user:read)
 * - PATCH  /admin/users/{id}           (admin:user:manage)
 * - POST   /admin/users/{id}/disable|enable|reset-password (admin:user:manage)
 * - POST   /admin/users/change-password (任意登录 admin)
 * - GET    /admin/rbac                 (admin:rbac:read)
 * - GET    /admin/audit-logs           (admin:audit_log:read)
 */

import type { AdminRole } from "@/lib/rbac";

/** 管理员账号全量投影（账号管理台使用）。 */
export interface AdminUserOut {
  id: number;
  username: string;
  display_name: string;
  role: AdminRole;
  status: "active" | "disabled";
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
}

export interface CreateAdminUserPayload {
  username: string;
  display_name: string;
  role: AdminRole;
  /** 8-64 位，须含字母与数字（后端 5001 兜底） */
  password: string;
}

export interface UpdateAdminUserPayload {
  display_name?: string;
  role?: AdminRole;
}

export interface ResetAdminPasswordPayload {
  new_password: string;
}

export interface ChangeAdminPasswordPayload {
  old_password: string;
  new_password: string;
}

/** 审计日志条目。 */
export interface AuditLogOut {
  id: number;
  actor_type: "user" | "merchant" | "admin" | "system" | "anonymous";
  actor_id: number | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  ip: string | null;
  created_at: string;
  extra: Record<string, unknown> | null;
}

/** 权限矩阵：角色 → 权限键集合。 */
export interface RbacMatrixOut {
  roles: Record<string, { label: string; permissions: string[] }>;
  permissions: { key: string; label: string }[];
}
