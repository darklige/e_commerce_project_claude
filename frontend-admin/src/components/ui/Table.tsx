"use client";

/**
 * 通用表格组件。
 *
 * 特性：
 * - 声明式 columns：{ key, title, render?, width?, align? }
 * - loading 状态渲染 Skeleton 行；empty 状态渲染文案
 * - 内建分页 footer（total/page/size）
 * - 泛型 T：行数据类型
 *
 * 管理端设计：
 * - 行高 40px、字号 13px、hover 高亮
 * - 表头 sticky（如包在滚动容器内）
 */

import { Fragment, type ReactNode } from "react";
import clsx from "clsx";
import { Skeleton } from "./Skeleton";
import { Button } from "./Button";

export interface TableColumn<T> {
  key: string;
  title: ReactNode;
  /** 自定义渲染，未提供则按 key 尝试 (row as any)[key] 展示（不推荐） */
  render?: (row: T, index: number) => ReactNode;
  width?: number | string;
  align?: "left" | "center" | "right";
}

export interface TablePagination {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  rows: T[];
  loading?: boolean;
  emptyText?: ReactNode;
  rowKey: (row: T, index: number) => string | number;
  pagination?: TablePagination;
  /** loading skeleton 行数，默认 5 */
  skeletonRows?: number;
}

export function Table<T>({
  columns,
  rows,
  loading = false,
  emptyText = "暂无数据",
  rowKey,
  pagination,
  skeletonRows = 5,
}: TableProps<T>) {
  const showEmpty = !loading && rows.length === 0;

  return (
    <div className="flex flex-col overflow-hidden rounded-md border border-[color:var(--color-border)] bg-white">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-[color:var(--color-border)] bg-[color:var(--color-primary-50)] text-left text-xs font-medium uppercase tracking-wide text-[color:var(--color-primary-800)]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={{
                    width: col.width,
                    textAlign: col.align ?? "left",
                  }}
                  className="whitespace-nowrap px-3 py-2"
                >
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: skeletonRows }).map((_, i) => (
                <tr
                  key={`sk-${i}`}
                  className="border-b border-[color:var(--color-border)]"
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-2.5">
                      <Skeleton className="h-4 w-full max-w-[160px]" />
                    </td>
                  ))}
                </tr>
              ))
            ) : showEmpty ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-16 text-center text-sm text-neutral-400"
                >
                  {emptyText}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <Fragment key={rowKey(row, index)}>
                  <tr className="border-b border-[color:var(--color-border)] transition hover:bg-[color:var(--color-primary-50)]/60">
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        style={{ textAlign: col.align ?? "left" }}
                        className={clsx("px-3 py-2.5 text-neutral-800")}
                      >
                        {col.render
                          ? col.render(row, index)
                          : String(
                              (row as unknown as Record<string, unknown>)[
                                col.key
                              ] ?? "",
                            )}
                      </td>
                    ))}
                  </tr>
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pagination ? (
        <TableFooter pagination={pagination} loading={loading} />
      ) : null}
    </div>
  );
}

function TableFooter({
  pagination,
  loading,
}: {
  pagination: TablePagination;
  loading?: boolean;
}) {
  const { page, size, total, onPageChange } = pagination;
  const totalPages = Math.max(1, Math.ceil(total / size));
  const start = total === 0 ? 0 : (page - 1) * size + 1;
  const end = Math.min(total, page * size);

  return (
    <div className="flex items-center justify-between border-t border-[color:var(--color-border)] bg-neutral-50 px-4 py-2 text-xs text-neutral-600">
      <div>
        共 <span className="font-semibold text-neutral-800">{total}</span> 条 ·
        当前 {start}-{end}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={loading || page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          上一页
        </Button>
        <span className="text-neutral-500">
          {page} / {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={loading || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          下一页
        </Button>
      </div>
    </div>
  );
}
