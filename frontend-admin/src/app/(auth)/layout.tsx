import type { ReactNode } from "react";
import { ToastProvider } from "@/components/ui/Toast";

/**
 * (auth) 路由组布局：登录 / 找回密码等未登录页面共用。
 *
 * 保持极简：管理端登录页刻意不放 Sidebar/Header，突出"平台管理员通道"文案。
 * 背景为品牌色系淡渐变 + 柔和光斑，传递"严谨的运营控制台"气质。
 * ToastProvider 在此挂一份，避免登录失败/成功 toast 找不到 provider。
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[color:var(--color-surface-muted)] px-4">
        {/* 柔和品牌渐变光斑（装饰，不影响可读性） */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_-10%,var(--color-primary-100),transparent_70%)]"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-[color:var(--color-info-soft)] opacity-60 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-[color:var(--color-accent-soft)] opacity-50 blur-3xl"
        />
        <div className="relative z-10">{children}</div>
      </div>
    </ToastProvider>
  );
}
