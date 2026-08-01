/**
 * Admin 售后管理 API 封装。
 *
 * 契约 §9 Admin 售后仲裁与强制处理：
 * - GET  /admin/aftersales?status=&type=&shop_id=&user_id=&escalation_reason=&keyword=&page=&size=
 * - GET  /admin/aftersales/{id}                        完整详情
 * - POST /admin/aftersales/{id}/take-over              认领仲裁
 * - POST /admin/aftersales/{id}/resolve                仲裁裁决（3 种 outcome）
 * - POST /admin/aftersales/{id}/force-refund           强制退款
 * - POST /admin/aftersales/{id}/release                释放回池
 * - POST /admin/aftersales/{id}/note                   内部备注
 * - GET  /admin/aftersales/stats/overview              大盘统计
 *
 * 权限：
 * - listAdminAftersales / getAdminAftersales / getAftersalesStats → admin:aftersales:read_all
 * - takeOver / resolveArbitration / releaseArbitration            → admin:aftersales:arbitrate
 * - forceRefund                                                  → admin:aftersales:force_refund
 * - addAdminNote                                                 → admin:aftersales:add_note
 */

import { apiGet, apiPost } from "@/lib/api";
import type { PaginatedData } from "@/types";
import type {
  AddAdminAftersalesNotePayload,
  AdminAftersalesDetail,
  AdminAftersalesListItem,
  AftersalesStatsOverview,
  AftersalesStatus,
  AftersalesType,
  EscalationReason,
  ForceRefundPayload,
  ResolveArbitrationPayload,
} from "@/types/aftersales";

/**
 * GET /admin/aftersales 查询参数。
 *
 * - status: 单值或多值以逗号分隔（后端支持 `status=a,b` 语法）
 * - shop_id / user_id: 数字 ID；空串等价 undefined
 * - keyword: 匹配 aftersales_no / order_no / 用户手机邮箱
 * - escalation_reason: 升级原因筛选（5 种）
 * - start_date / end_date: ISO 日期字符串（yyyy-MM-dd），后端解释为 UTC 天区间
 */
export interface ListAdminAftersalesQuery {
  status?: AftersalesStatus | string;
  type?: AftersalesType;
  shop_id?: number | string;
  user_id?: number | string;
  keyword?: string;
  escalation_reason?: EscalationReason | string;
  start_date?: string;
  end_date?: string;
  page?: number;
  size?: number;
}

/**
 * GET /admin/aftersales
 * 权限：admin:aftersales:read_all
 * 默认按 escalated_at DESC NULLS LAST（仲裁台优先看已升级）。
 */
export function listAdminAftersales(
  query: ListAdminAftersalesQuery = {},
): Promise<PaginatedData<AdminAftersalesListItem>> {
  const searchParams: Record<string, string | number> = {};
  if (query.status) searchParams.status = query.status;
  if (query.type) searchParams.type = query.type;
  if (query.shop_id !== undefined && query.shop_id !== "") {
    searchParams.shop_id = query.shop_id;
  }
  if (query.user_id !== undefined && query.user_id !== "") {
    searchParams.user_id = query.user_id;
  }
  if (query.keyword) searchParams.keyword = query.keyword;
  if (query.escalation_reason) {
    searchParams.escalation_reason = query.escalation_reason;
  }
  if (query.start_date) searchParams.start_date = query.start_date;
  if (query.end_date) searchParams.end_date = query.end_date;
  if (query.page) searchParams.page = query.page;
  if (query.size) searchParams.size = query.size;
  return apiGet<PaginatedData<AdminAftersalesListItem>>("admin/aftersales", {
    searchParams,
  });
}

/**
 * GET /admin/aftersales/{id}
 * 权限：admin:aftersales:read_all
 * 错误：15001 售后单不存在 / 15002 无权访问
 */
export function getAdminAftersales(
  id: number | string,
): Promise<AdminAftersalesDetail> {
  return apiGet<AdminAftersalesDetail>(`admin/aftersales/${id}`);
}

/**
 * POST /admin/aftersales/{id}/take-over
 * 权限：admin:aftersales:arbitrate
 * 允许状态：admin_arbitrating（arbitrator_admin_id 为空时）。
 * 效果：将 arbitrator_admin_id 设为当前 admin.id；不改状态。
 * 错误：18001 尚未升级至平台 / 18002 已有其他 admin 认领
 */
export function takeOver(
  id: number | string,
): Promise<AdminAftersalesDetail> {
  return apiPost<AdminAftersalesDetail, Record<string, never>>(
    `admin/aftersales/${id}/take-over`,
    {},
  );
}

/**
 * POST /admin/aftersales/{id}/resolve
 * 权限：admin:aftersales:arbitrate
 * 允许状态：admin_arbitrating（且当前 admin 已认领）。
 *
 * outcome:
 * - side_with_user   → 状态 → refunding（触发全额退款）
 * - partial_refund   → 状态 → refunding（触发部分退款；actual_refund_cents 必填）
 * - side_with_merchant → 状态 → system_closed / close_reason='arbitration_closed'
 *
 * 错误：18001 / 18002 / 18003 / 15003
 */
export function resolveArbitration(
  id: number | string,
  payload: ResolveArbitrationPayload,
): Promise<AdminAftersalesDetail> {
  return apiPost<AdminAftersalesDetail, ResolveArbitrationPayload>(
    `admin/aftersales/${id}/resolve`,
    payload,
  );
}

/**
 * POST /admin/aftersales/{id}/force-refund
 * 权限：admin:aftersales:force_refund
 * 允许状态：非最终态皆可。
 * 效果：状态 → refunding；写 audit + 明确标记"admin 强制"。
 * 错误：18003 强制退款金额非法 / 15003 状态不允许
 */
export function forceRefund(
  id: number | string,
  payload: ForceRefundPayload,
): Promise<AdminAftersalesDetail> {
  return apiPost<AdminAftersalesDetail, ForceRefundPayload>(
    `admin/aftersales/${id}/force-refund`,
    payload,
  );
}

/**
 * POST /admin/aftersales/{id}/release
 * 权限：admin:aftersales:arbitrate（服务层限定：manage 角色可释放任何人，
 *      客服专员仅可释放自己认领的单）。
 * 允许状态：admin_arbitrating（且 arbitrator_admin_id 非空）。
 * 效果：arbitrator_admin_id → null（回到公共池），写 audit + 系统消息。
 * 错误：18001 未升级至平台 / 18003 已仲裁 / 18005 无权释放
 */
export function releaseArbitration(
  id: number | string,
): Promise<AdminAftersalesDetail> {
  return apiPost<AdminAftersalesDetail, Record<string, never>>(
    `admin/aftersales/${id}/release`,
    {},
  );
}

/**
 * POST /admin/aftersales/{id}/note
 * 权限：admin:aftersales:add_note
 * 内部备注（对用户/商家隐藏），通过 aftersales_messages(kind='reply', sender_type='admin') 写入。
 */
export function addAdminNote(
  id: number | string,
  payload: AddAdminAftersalesNotePayload,
): Promise<AdminAftersalesDetail> {
  return apiPost<AdminAftersalesDetail, AddAdminAftersalesNotePayload>(
    `admin/aftersales/${id}/note`,
    payload,
  );
}

/**
 * GET /admin/aftersales/stats/overview
 * 权限：admin:aftersales:read_all
 * 售后大盘 5 个数字：pending_review / escalated_pending / in_progress /
 * resolved_today / avg_resolution_hours。
 */
export function getAftersalesStats(): Promise<AftersalesStatsOverview> {
  return apiGet<AftersalesStatsOverview>("admin/aftersales/stats/overview");
}
