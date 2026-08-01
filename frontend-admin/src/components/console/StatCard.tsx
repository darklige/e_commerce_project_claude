import type { ReactNode } from "react";
import clsx from "clsx";

export type StatCardTone = "default" | "info" | "warning" | "danger" | "success";

interface StatCardProps {
  label: string;
  value: number | string;
  hint?: ReactNode;
  tone?: StatCardTone;
}

/**
 * 数据统计卡片。
 *
 * 管理端惯例（Phase 6 UI 打磨）：
 * - 每个 tone 配柔和底色 + 图标圆角块，数值仍为深色大字号，保证信息可扫读
 * - 左上角渐变竖条保留，用于快速辨识风险等级
 * - 悬浮时轻微上浮 + 投影，提示可点击（卡片外包 Link）
 */
export function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  const meta: Record<
    StatCardTone,
    { bg: string; chip: string; bar: string; icon: ReactNode }
  > = {
    default: {
      bg: "bg-[color:var(--color-primary-50)]",
      chip: "bg-white text-[color:var(--color-primary-600)] border-[color:var(--color-primary-200)]",
      bar: "bg-[linear-gradient(180deg,var(--color-primary-500),var(--color-primary-700))]",
      icon: (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
          <path d="M4 3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H9.4a1 1 0 0 1-.7-.3L7.3 3.3A1 1 0 0 0 6.6 3H4Z" />
        </svg>
      ),
    },
    info: {
      bg: "bg-[color:var(--color-info-soft)]",
      chip: "bg-white text-[color:var(--color-info)] border-[color:var(--color-info)]/20",
      bar: "bg-[linear-gradient(180deg,#3b82f6,#1d4ed8)]",
      icon: (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
          <path
            fillRule="evenodd"
            d="M10 2a6 6 0 0 0-4.4 10.1c.6.6.9 1.4.9 2.2v.2a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1v-.2c0-.8.3-1.6.9-2.2A6 6 0 0 0 10 2Zm-1.5 14.5a.5.5 0 0 0 .5.5h2a.5.5 0 0 0 .5-.5V16h-3v.5Z"
            clipRule="evenodd"
          />
        </svg>
      ),
    },
    warning: {
      bg: "bg-[color:var(--color-warning-soft)]",
      chip: "bg-white text-[color:var(--color-warning)] border-[color:var(--color-warning)]/20",
      bar: "bg-[linear-gradient(180deg,#f59e0b,#b45309)]",
      icon: (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
          <path d="M10 2a1 1 0 0 1 .9.55l7 13A1 1 0 0 1 17 17H3a1 1 0 0 1-.9-1.45l7-13A1 1 0 0 1 10 2Zm0 5a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 10 7Zm0 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
        </svg>
      ),
    },
    danger: {
      bg: "bg-[color:var(--color-danger-soft)]",
      chip: "bg-white text-[color:var(--color-danger)] border-[color:var(--color-danger)]/20",
      bar: "bg-[linear-gradient(180deg,#ef4444,#b91c1c)]",
      icon: (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
          <path d="M10 3a1 1 0 0 0-.9.55L3.3 13.5A1 1 0 0 0 4.2 15h11.6a1 1 0 0 0 .9-1.45L10.9 3.55A1 1 0 0 0 10 3Zm0 3.25a.75.75 0 0 1 .75.75v3.25a.75.75 0 0 1-1.5 0V7a.75.75 0 0 1 .75-.75ZM10 13.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" />
        </svg>
      ),
    },
    success: {
      bg: "bg-[color:var(--color-success-soft)]",
      chip: "bg-white text-[color:var(--color-success)] border-[color:var(--color-success)]/20",
      bar: "bg-[linear-gradient(180deg,#22c55e,#15803d)]",
      icon: (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
          <path
            fillRule="evenodd"
            d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm3.7 5.4a.75.75 0 0 0-1.06 0L8.75 11.3 7.36 9.9a.75.75 0 0 0-1.06 1.06l1.94 1.94a.75.75 0 0 0 1.06 0l4.4-4.4a.75.75 0 0 0 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      ),
    },
  };

  const m = meta[tone];

  return (
    <article
      className={clsx(
        "relative flex items-start gap-3 overflow-hidden rounded-lg border border-[color:var(--color-border)] p-4 shadow-card transition",
        "hover:-translate-y-0.5 hover:border-[color:var(--color-primary-200)] hover:shadow-card-hover",
        m.bg,
      )}
    >
      <span
        aria-hidden
        className={`absolute left-0 top-0 h-full w-1 ${m.bar}`}
      />
      <span
        aria-hidden
        className={clsx(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border",
          m.chip,
        )}
      >
        {m.icon}
      </span>
      <div className="min-w-0 pl-1">
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-600">
          {label}
        </div>
        <div className="mt-1.5 text-2xl font-semibold tabular-nums text-neutral-900">
          {value}
        </div>
        {hint ? (
          <div className="mt-1.5 text-xs leading-relaxed text-neutral-500">
            {hint}
          </div>
        ) : null}
      </div>
    </article>
  );
}
