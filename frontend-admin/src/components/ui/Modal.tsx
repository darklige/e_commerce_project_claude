"use client";

/**
 * 极简 Modal（无外部依赖） —— Phase 7 §5.1 焦点管理规范。
 *
 * 特性：
 * - ESC 关闭 / 点击遮罩关闭（破坏性操作可禁用）
 * - 打开时 focus 首个可交互元素
 * - Focus trap：Tab 循环在 Modal 内
 * - 关闭时归还焦点给触发元素
 * - 只支持 sm/md/lg 三档宽度，管理端不追求花哨动画（300ms 淡入）
 *
 * 用法：
 *   <Modal open={open} onClose={close} title="通过审批">...</Modal>
 */

import {
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  type MouseEvent as ReactMouseEvent,
} from "react";
import clsx from "clsx";

type ModalSize = "sm" | "md" | "lg";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: ModalSize;
  /** 是否允许点遮罩关闭。破坏性 confirm 建议设 false */
  closeOnOverlay?: boolean;
  /** 是否显示关闭 X。默认 true */
  showClose?: boolean;
}

const SIZE_CLASS: Record<ModalSize, string> = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
  closeOnOverlay = true,
  showClose = true,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  const getFocusables = useCallback((): HTMLElement[] => {
    const root = dialogRef.current;
    if (!root) return [];
    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((el) => !el.hasAttribute("aria-hidden"));
  }, []);

  useEffect(() => {
    if (!open) return;
    const prevActive = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const t = window.setTimeout(() => {
      const first = getFocusables()[0] ?? dialogRef.current;
      first?.focus();
    }, 0);

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const focusables = getFocusables();
        if (focusables.length === 0) {
          e.preventDefault();
          dialogRef.current?.focus();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prevOverflow;
      prevActive?.focus?.();
    };
  }, [open, onClose, getFocusables]);

  if (!open) return null;

  const onOverlayClick = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!closeOnOverlay) return;
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onClick={onOverlayClick}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        ref={dialogRef}
        tabIndex={-1}
        className={clsx(
          "flex w-full flex-col overflow-hidden rounded-md bg-white shadow-lg outline-none",
          "animate-[fade-in_300ms_ease-out]",
          SIZE_CLASS[size],
        )}
      >
        {(title || showClose) && (
          <header className="flex items-center justify-between border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="bg-brand-gradient inline-block h-3.5 w-1 rounded-full"
              />
              <h2
                id="modal-title"
                className="text-sm font-semibold text-neutral-900"
              >
                {title}
              </h2>
            </div>
            {showClose ? (
              <button
                type="button"
                aria-label="关闭"
                onClick={onClose}
                className="rounded p-1 text-neutral-500 hover:bg-neutral-100"
              >
                ×
              </button>
            ) : null}
          </header>
        )}
        <div className="flex-1 overflow-y-auto p-4 text-sm text-neutral-800">
          {children}
        </div>
        {footer ? (
          <footer className="flex items-center justify-end gap-2 border-t border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>
  );
}
