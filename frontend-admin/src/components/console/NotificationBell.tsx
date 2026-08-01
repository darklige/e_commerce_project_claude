"use client";

/**
 * Header 站内信铃铛。
 *
 * 契约 §6：GET /admin/notifications/unread-count 每 60s 轮询。
 *
 * UI：
 * - 铃铛 icon + 未读徽章（99+ 截断）
 * - 点击跳转 /console/notifications
 * - 无 admin:notification:read 权限时不渲染
 */

import Link from "next/link";
import clsx from "clsx";
import { useUnreadCount } from "@/hooks/useNotifications";
import { usePermission } from "@/hooks/useAuth";

export function NotificationBell({ className }: { className?: string }) {
  const canRead = usePermission("admin:notification:read");
  const { data } = useUnreadCount({ enabled: canRead });

  if (!canRead) return null;

  const count = data?.count ?? 0;

  return (
    <Link
      href="/console/notifications"
      aria-label={
        count > 0 ? `站内通知，未读 ${count} 条` : "站内通知"
      }
      className={clsx(
        "relative inline-flex h-8 w-8 items-center justify-center rounded text-neutral-500 hover:bg-[color:var(--color-primary-50)] hover:text-[color:var(--color-primary-800)]",
        className,
      )}
    >
      {/* 铃铛（纯 SVG，避免额外 icon 依赖） */}
      <svg
        aria-hidden
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      {count > 0 ? (
        <span
          aria-hidden
          className="absolute -right-0.5 -top-0.5 inline-flex min-w-[16px] items-center justify-center rounded-full bg-[color:var(--color-danger)] px-1 py-0.5 text-[10px] font-semibold leading-none text-white"
        >
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </Link>
  );
}
