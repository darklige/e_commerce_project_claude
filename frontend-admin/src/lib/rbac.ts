/**
 * 平台管理端角色 (RBAC) 与权限判定。
 *
 * 契约来源：docs/API/phase-1-contracts.md §7（RBAC 与权限清单）。
 *
 * 设计说明：
 * - AdminRole 四类角色与后端 admin_users.role 枚举 1:1 对齐
 * - Permission 类型直接使用契约中的字符串常量（形如 `scope:resource:action`）
 * - 前端权限来源为 GET /api/v1/admin/me 返回的 permissions 数组，
 *   由 auth-store 统一持有；hasPermission 从传入的权限集合判断
 * - 前端 gating **不构成安全边界**：后端每次调用仍会做二次鉴权
 */

/**
 * 平台管理端角色枚举（与后端 admin_users.role 一一对应）。
 */
export enum AdminRole {
  /** 超级管理员：拥有所有权限 */
  SUPER_ADMIN = "SUPER_ADMIN",
  /** 业务管理员：商家审核、商品审核、订单大盘等 */
  BUSINESS_ADMIN = "BUSINESS_ADMIN",
  /** 客服管理员：售后仲裁、用户投诉处理 */
  CUSTOMER_SERVICE_ADMIN = "CUSTOMER_SERVICE_ADMIN",
  /** 技术管理员：系统配置、日志、权限分配 */
  TECH_ADMIN = "TECH_ADMIN",
  /** Phase 6 客服组长：仲裁 + 派单管理（释放/重派） */
  CUSTOMER_SERVICE_LEAD = "CUSTOMER_SERVICE_LEAD",
  /** Phase 6 普通客服：仅可见待认领 / 自己认领的仲裁单 */
  CUSTOMER_SERVICE_AGENT = "CUSTOMER_SERVICE_AGENT",
}

/**
 * 权限点联合类型。
 *
 * 命名规则：`{scope}:{resource}[:{sub}]:{action}`，scope ∈ {user, merchant, admin}。
 * Phase 1 使用契约 §7.2 权限键；Phase 2 追加类目/品牌/商品审核（契约 §5）。
 *
 * 尚未在契约中出现但骨架页面仍需引用的占位键保留为未来 Phase 声明，
 * Sidebar 会将无匹配权限的项 disabled 化。
 */
export type Permission =
  // ---- 契约 §7.2 Phase 1 权限清单 ----
  | "user:self:read"
  | "user:self:update"
  | "user:merchant_application:submit"
  | "user:merchant_application:withdraw"
  | "user:merchant_application:read"
  | "merchant:self:read"
  | "merchant:shop:update"
  | "admin:self:read"
  | "admin:merchant_application:read"
  | "admin:merchant_application:review"
  | "admin:audit_log:read"
  // ---- Phase 2 契约 §5 新增：类目 / 品牌 / 商品审核 ----
  | "admin:category:manage"
  | "admin:brand:manage"
  | "admin:spu:review"
  | "admin:spu:force_offshelf"
  | "admin:spu:read_all"
  // ---- Phase 3 契约 §5 新增：订单大盘与干预 ----
  | "admin:order:read_all"
  | "admin:order:intervene"
  | "admin:order:add_note"
  // ---- Phase 4 契约 §6 新增：售后仲裁 ----
  | "admin:aftersales:read_all"
  | "admin:aftersales:arbitrate"
  | "admin:aftersales:force_refund"
  | "admin:aftersales:add_note"
  // ---- Phase 5 契约 §10 新增：评价审核 / 举报处理 / 通知 ----
  | "admin:review:moderate"
  | "admin:review_report:handle"
  | "admin:notification:read"
  // ---- Phase 6 契约新增：管理员账号管理 / 权限矩阵 / 售后派单 ----
  | "admin:user:read"
  | "admin:user:manage"
  | "admin:rbac:read"
  | "admin:aftersales:manage"
  // ---- 后续 Phase 预留（暂无对应权限时返回 false，UI 侧 disabled）----
  | "admin:product:review"
  | "admin:order:read"
  | "admin:refund:arbitrate"
  | "admin:rbac:manage";

/** 角色元信息（用于 UI badge、下拉展示） */
export interface AdminRoleMeta {
  role: AdminRole;
  label: string;
  /** 用于 badge 的中性色调 */
  tone: "primary" | "info" | "warning" | "danger";
  description: string;
  /**
   * 该角色**理论上**默认拥有的权限（仅作 UI 文案与文档参考）。
   *
   * 权限的真实来源仍是后端 GET /admin/me 下发的 permissions 数组，
   * 前端不用此字段做鉴权判断（避免与后端矩阵漂移）。
   *
   * 契约 §5 Phase 2 分配：
   * - SUPER_ADMIN         → 全部
   * - BUSINESS_ADMIN      → 商家审核 + 类目/品牌/商品审核 + 强制下架
   * - CUSTOMER_SERVICE_ADMIN → 只读商品（read_all）+ 售后仲裁（Phase 4）
   * - TECH_ADMIN          → 系统 / RBAC / 日志
   *
   * Phase 4 契约 §6 追加：
   * - admin:aftersales:read_all     → SUPER, BUSINESS, CUSTOMER_SERVICE
   * - admin:aftersales:arbitrate    → SUPER, CUSTOMER_SERVICE
   * - admin:aftersales:force_refund → SUPER, CUSTOMER_SERVICE
   * - admin:aftersales:add_note     → SUPER, CUSTOMER_SERVICE
   *
   * Phase 5 契约 §10 追加：
   * - admin:review:moderate         → SUPER, BUSINESS, CUSTOMER_SERVICE
   * - admin:review_report:handle    → SUPER, CUSTOMER_SERVICE
   * - admin:notification:read       → 任何 admin
   *
   * Phase 6 契约追加：
   * - admin:user:read               → SUPER, TECH_ADMIN（只读账号列表）
   * - admin:user:manage             → SUPER（账号增删改）
   * - admin:rbac:read               → SUPER, BUSINESS_ADMIN, TECH_ADMIN
   * - admin:aftersales:manage       → SUPER, CUSTOMER_SERVICE_LEAD（释放/重派）
   * - 新增角色：CUSTOMER_SERVICE_LEAD / CUSTOMER_SERVICE_AGENT
   */
  defaultPermissions: readonly Permission[];
}

export const ADMIN_ROLE_META: Record<AdminRole, AdminRoleMeta> = {
  [AdminRole.SUPER_ADMIN]: {
    role: AdminRole.SUPER_ADMIN,
    label: "超级管理员",
    tone: "danger",
    description: "拥有所有权限，请谨慎操作",
    defaultPermissions: [
      "admin:self:read",
      "admin:merchant_application:read",
      "admin:merchant_application:review",
      "admin:audit_log:read",
      "admin:category:manage",
      "admin:brand:manage",
      "admin:spu:review",
      "admin:spu:force_offshelf",
      "admin:spu:read_all",
      "admin:order:read",
      "admin:order:read_all",
      "admin:order:intervene",
      "admin:order:add_note",
      "admin:aftersales:read_all",
      "admin:aftersales:arbitrate",
      "admin:aftersales:force_refund",
      "admin:aftersales:add_note",
      "admin:review:moderate",
      "admin:review_report:handle",
      "admin:notification:read",
      "admin:refund:arbitrate",
      "admin:user:read",
      "admin:user:manage",
      "admin:rbac:read",
      "admin:aftersales:manage",
    ],
  },
  [AdminRole.BUSINESS_ADMIN]: {
    role: AdminRole.BUSINESS_ADMIN,
    label: "业务管理员",
    tone: "primary",
    description: "商家 / 商品 / 订单业务侧管理",
    defaultPermissions: [
      "admin:self:read",
      "admin:merchant_application:read",
      "admin:merchant_application:review",
      "admin:category:manage",
      "admin:brand:manage",
      "admin:spu:review",
      "admin:spu:force_offshelf",
      "admin:spu:read_all",
      "admin:order:read",
      "admin:order:read_all",
      "admin:aftersales:read_all",
      "admin:review:moderate",
      "admin:notification:read",
    ],
  },
  [AdminRole.CUSTOMER_SERVICE_ADMIN]: {
    role: AdminRole.CUSTOMER_SERVICE_ADMIN,
    label: "客服管理员",
    tone: "info",
    description: "售后仲裁与用户投诉处理",
    defaultPermissions: [
      "admin:self:read",
      "admin:spu:read_all",
      "admin:refund:arbitrate",
      "admin:order:read",
      "admin:order:read_all",
      "admin:order:intervene",
      "admin:order:add_note",
      "admin:aftersales:read_all",
      "admin:aftersales:arbitrate",
      "admin:aftersales:force_refund",
      "admin:aftersales:add_note",
      "admin:review:moderate",
      "admin:review_report:handle",
      "admin:notification:read",
    ],
  },
  [AdminRole.CUSTOMER_SERVICE_LEAD]: {
    role: AdminRole.CUSTOMER_SERVICE_LEAD,
    label: "客服组长",
    tone: "info",
    description: "仲裁 + 售后派单管理（释放 / 重派）",
    defaultPermissions: [
      "admin:self:read",
      "admin:spu:read_all",
      "admin:order:read_all",
      "admin:order:intervene",
      "admin:order:add_note",
      "admin:aftersales:read_all",
      "admin:aftersales:arbitrate",
      "admin:aftersales:force_refund",
      "admin:aftersales:add_note",
      "admin:aftersales:manage",
      "admin:review:moderate",
      "admin:review_report:handle",
      "admin:notification:read",
    ],
  },
  [AdminRole.CUSTOMER_SERVICE_AGENT]: {
    role: AdminRole.CUSTOMER_SERVICE_AGENT,
    label: "普通客服",
    tone: "info",
    description: "仅处理待认领 / 自己认领的仲裁单",
    defaultPermissions: [
      "admin:self:read",
      "admin:spu:read_all",
      "admin:order:read_all",
      "admin:aftersales:read_all",
      "admin:aftersales:arbitrate",
      "admin:aftersales:add_note",
      "admin:notification:read",
    ],
  },
  [AdminRole.TECH_ADMIN]: {
    role: AdminRole.TECH_ADMIN,
    label: "技术管理员",
    tone: "warning",
    description: "系统配置、日志与权限分配",
    defaultPermissions: [
      "admin:self:read",
      "admin:audit_log:read",
      "admin:user:read",
      "admin:rbac:read",
      "admin:notification:read",
    ],
  },
};

/**
 * 判断权限集合中是否包含指定权限。
 *
 * Phase 1 起前端权限完全由后端下发（GET /api/v1/admin/me 返回的
 * permissions 数组），本函数只做集合包含判断，不再依赖前端硬编码矩阵。
 * 这样后端矩阵变更时无需前后端同步发版。
 *
 * @param permissions 当前登录 admin 拥有的权限（来自 auth store），
 *                    未登录时可传 null/undefined/[] 一律返回 false
 * @param permission 待检查的权限键
 */
export function hasPermission(
  permissions: readonly Permission[] | null | undefined,
  permission: Permission,
): boolean {
  if (!permissions || permissions.length === 0) return false;
  return permissions.includes(permission);
}

/**
 * 便捷方法：具备任一权限即可（用于导航项显示）。
 */
export function hasAnyPermission(
  permissions: readonly Permission[] | null | undefined,
  required: readonly Permission[],
): boolean {
  if (!permissions || permissions.length === 0) return false;
  if (required.length === 0) return true;
  return required.some((p) => permissions.includes(p));
}
