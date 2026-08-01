"use client";

/**
 * 通用 Button 组件。
 *
 * 管理端设计约束：
 * - 主色沿用 --color-primary (#0f172a)，强调"沉稳"
 * - variant=danger 用 --color-danger，仅用于破坏性操作（reject / disable / delete）
 * - variant=ghost 用于表格行内操作（"查看""编辑"）
 * - 尺寸 sm(28px) / md(32px) 两档，管理端优先 md
 * - 支持 loading 状态：禁用交互 + 展示 spinner
 */

import { forwardRef, type ButtonHTMLAttributes } from "react";
import clsx from "clsx";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "danger"
  | "ghost"
  | "link";

export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-gradient text-white shadow-sm hover:brightness-110 disabled:brightness-90 disabled:shadow-none",
  secondary:
    "border border-[color:var(--color-border)] bg-white text-neutral-700 hover:border-[color:var(--color-primary-200)] hover:bg-[color:var(--color-primary-50)] disabled:text-neutral-400",
  danger:
    "bg-[color:var(--color-danger)] text-white shadow-sm hover:bg-[#b91c1c] disabled:bg-red-300 disabled:shadow-none",
  ghost:
    "bg-transparent text-[color:var(--color-primary-700)] hover:bg-[color:var(--color-primary-50)] disabled:text-neutral-400",
  link:
    "bg-transparent text-[color:var(--color-info)] hover:underline disabled:text-neutral-400 h-auto p-0",
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: "h-7 px-2 text-xs",
  md: "h-8 px-3 text-sm",
};

/**
 * 管理端标准按钮。ref 转发给底层 <button>，便于 react-hook-form 或
 * 无障碍焦点控制引用。
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    disabled,
    fullWidth,
    className,
    children,
    type = "button",
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={clsx(
        "inline-flex items-center justify-center gap-1 rounded font-medium transition disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-primary-400)]",
        variant !== "link" && SIZE_CLASS[size],
        VARIANT_CLASS[variant],
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden
          className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : null}
      {children}
    </button>
  );
});
