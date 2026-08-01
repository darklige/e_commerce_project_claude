"use client";

/**
 * 顶部 Header。
 *
 * 结构：面包屑占位（左） · 当前管理员展示 + 角色 Badge + 下拉（右）
 * 下拉包含：修改密码 / 退出登录。
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { ADMIN_ROLE_META, type AdminRole } from "@/lib/rbac";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/components/ui/Toast";
import { NotificationBell } from "@/components/console/NotificationBell";

export function Header() {
  const { admin, logout } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const meta = admin ? ADMIN_ROLE_META[admin.role] : null;

  const handleLogout = async () => {
    setOpen(false);
    await logout();
    toast.push({ type: "info", message: "已退出登录" });
    router.replace("/login");
  };

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-[color:var(--color-border)] bg-white px-6">
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <span
          aria-hidden
          className="bg-brand-gradient inline-block h-2 w-2 rounded-full"
        />
        平台管理后台
      </div>

      <div className="relative flex items-center gap-3" ref={menuRef}>
        <NotificationBell />
        {admin && meta ? (
          <>
            <span
              className="text-sm text-neutral-700"
              aria-label="当前登录管理员"
            >
              {admin.display_name}
            </span>
            <RoleBadge label={meta.label} tone={meta.tone} />
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
              className="ml-1 rounded p-1 text-neutral-500 hover:bg-neutral-100"
            >
              <span aria-hidden>▾</span>
              <span className="sr-only">展开账号菜单</span>
            </button>
            {open ? (
              <div
                role="menu"
                className="absolute right-0 top-12 z-20 w-44 overflow-hidden rounded-md border border-[color:var(--color-border)] bg-white shadow-md"
              >
                <div className="border-b border-[color:var(--color-border)] px-3 py-2 text-xs text-neutral-500">
                  @{admin.username}
                </div>
                <Link
                  role="menuitem"
                  href="/console/account/change-password"
                  className="block px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                  onClick={() => setOpen(false)}
                >
                  修改密码
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="block w-full px-3 py-2 text-left text-sm text-[color:var(--color-danger)] hover:bg-red-50"
                >
                  退出登录
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <span className="text-xs text-neutral-400">未登录</span>
        )}
      </div>
    </header>
  );
}

function RoleBadge({
  label,
  tone,
}: {
  label: string;
  tone: "primary" | "info" | "warning" | "danger";
}) {
  const toneClass = {
    primary:
      "bg-[color:var(--color-primary-100)] text-[color:var(--color-primary-800)] border-[color:var(--color-primary-200)]",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    danger:
      "bg-[color:var(--color-danger-soft)] text-[color:var(--color-danger)] border-red-200",
  } as const;

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium",
        toneClass[tone],
      )}
      aria-label={`当前角色：${label}`}
    >
      {label}
    </span>
  );
}

/**
 * 供外部（如 storybook）显式引用 AdminRole 类型。
 */
export type { AdminRole };
