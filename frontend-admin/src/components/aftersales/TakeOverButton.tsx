"use client";

/**
 * 一键认领仲裁按钮。
 *
 * 契约 §9.2 POST /admin/aftersales/{id}/take-over
 * - 允许状态：admin_arbitrating 且 arbitrator_admin_id 为空
 * - 成功后：将 arbitrator_admin_id 设为当前 admin.id；不改状态
 * - 已被别的 admin 认领 → 后端返回 18002；前端 UI 层也做禁用（防抢占）
 *
 * 交互：
 * - 点击直接触发（无需二次确认，认领本身可逆——真正关键操作是"裁决"）
 * - 附强警告文案"认领后请及时处理"
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { takeOver } from "@/lib/aftersales-api";
import { ApiError } from "@/lib/api";
import { getErrorMessage } from "@/types/errors";
import type { AdminAftersalesDetail } from "@/types/aftersales";

export interface TakeOverButtonProps {
  aftersalesId: number | string;
  /**
   * 是否已被其他 admin 认领（前端 gating；防止 UI 层被点开）。
   * 后端会二次校验（18002）。
   */
  alreadyTakenOver: boolean;
  onSuccess?: (detail: AdminAftersalesDetail) => void;
  className?: string;
  /** 列表页行内快捷认领用小尺寸（sm）；详情页默认 md。 */
  size?: "sm" | "md";
}

export function TakeOverButton({
  aftersalesId,
  alreadyTakenOver,
  onSuccess,
  className,
  size = "md",
}: TakeOverButtonProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => takeOver(aftersalesId),
    onSuccess: (detail) => {
      toast.push({ type: "success", message: "已成功认领仲裁，请及时处理" });
      queryClient.invalidateQueries({
        queryKey: ["admin", "aftersales", String(aftersalesId)],
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "aftersales-list"] });
      queryClient.invalidateQueries({
        queryKey: ["admin", "aftersales-stats"],
      });
      onSuccess?.(detail);
    },
    onError: (err) => {
      const msg =
        err instanceof ApiError
          ? getErrorMessage(err.code, err.message)
          : "认领失败，请稍后重试";
      toast.push({ type: "error", message: msg });
    },
  });

  return (
    <Button
      variant="primary"
      size={size}
      loading={mutation.isPending}
      disabled={alreadyTakenOver}
      onClick={() => mutation.mutate()}
      aria-label="认领此仲裁"
      title={
        alreadyTakenOver
          ? "该仲裁已由其他管理员认领"
          : "认领后其他管理员不可接手，请及时处理"
      }
      className={className}
    >
      {alreadyTakenOver ? "已被认领" : "认领此仲裁"}
    </Button>
  );
}
