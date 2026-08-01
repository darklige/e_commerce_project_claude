"use client";

/**
 * 售后仲裁详情页 (`/console/aftersales/[id]`)。
 *
 * 契约 §9：
 * - GET  /admin/aftersales/{id}                       完整详情（含 items / history / evidences / messages）
 * - POST /admin/aftersales/{id}/take-over             认领仲裁
 * - POST /admin/aftersales/{id}/resolve               裁决（3 种 outcome）
 * - POST /admin/aftersales/{id}/force-refund          强制退款
 * - POST /admin/aftersales/{id}/note                  内部备注（写入 messages(kind='reply', sender_type='admin')）
 *
 * UI 要素：
 * - 顶部：售后单号 + 状态大 badge + 升级原因 badge + 主操作按钮
 *   - admin_arbitrating 且未认领 → TakeOverButton
 *   - 已认领 → 显示仲裁员 + 「裁决」按钮 → ResolveModal
 *   - 非最终态且非 admin_arbitrating → 「强制退款」按钮 → ForceRefundModal
 * - 左栏：用户 / 商家 / 订单摘要 / 商品明细 / 金额（申请 vs 实际）
 * - 右栏：证据画廊按 stage 分组 + 完整 Timeline（含 messages）
 * - 底部：内部备注编辑（黄色框，仅管理员可见）
 * - 快捷跳转按钮：跳到关联订单页
 */

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { FormField } from "@/components/ui/FormField";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import {
  AftersalesStatusBadge,
  isTerminal,
} from "@/components/aftersales/AftersalesStatusBadge";
import { AftersalesTypeIcon } from "@/components/aftersales/AftersalesTypeIcon";
import { EscalationReasonBadge } from "@/components/aftersales/EscalationReasonBadge";
import { AftersalesTimeline } from "@/components/aftersales/AftersalesTimeline";
import { TakeOverButton } from "@/components/aftersales/TakeOverButton";
import { ResolveModal } from "@/components/aftersales/ResolveModal";
import { ForceRefundModal } from "@/components/aftersales/ForceRefundModal";
import { useAdminAftersalesDetail } from "@/hooks/useAftersales";
import { usePermission } from "@/hooks/useAuth";
import { useAdmin } from "@/hooks/useAuth";
import {
  addAdminNote,
  forceRefund,
  releaseArbitration,
  resolveArbitration,
} from "@/lib/aftersales-api";
import { ApiError } from "@/lib/api";
import { getErrorMessage } from "@/types/errors";
import { imagePlaceholder, imageUrl } from "@/lib/image";
import type {
  AdminAftersalesDetail,
  AftersalesEvidenceOut,
  AftersalesItemOut,
  EvidenceStage,
  ForceRefundPayload,
  ResolveArbitrationPayload,
} from "@/types/aftersales";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AdminAftersalesDetailPage(props: PageProps) {
  const { id } = use(props.params);
  return (
    <RequirePermission permission="admin:aftersales:read_all">
      <AdminAftersalesDetailInner id={id} />
    </RequirePermission>
  );
}

type ModalKind = "resolve" | "force-refund" | "note" | "release" | null;

function AdminAftersalesDetailInner({ id }: { id: string }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const canArbitrate = usePermission("admin:aftersales:arbitrate");
  const canForceRefund = usePermission("admin:aftersales:force_refund");
  const canAddNote = usePermission("admin:aftersales:add_note");
  // 组长 / 超级管理员：可释放任意已认领仲裁单；客服专员可释放自己认领的单。
  const canManage = usePermission("admin:aftersales:manage");
  const currentAdmin = useAdmin();

  const { data, isLoading, isError, error } = useAdminAftersalesDetail(id);
  const [modal, setModal] = useState<ModalKind>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({
      queryKey: ["admin", "aftersales", String(id)],
    });
    queryClient.invalidateQueries({ queryKey: ["admin", "aftersales-list"] });
    queryClient.invalidateQueries({ queryKey: ["admin", "aftersales-stats"] });
  };

  const releaseMutation = useMutation({
    mutationFn: () => releaseArbitration(id),
    onSuccess: () => {
      setModal(null);
      toast.push({ type: "success", message: "仲裁单已释放回公共池" });
      invalidate();
    },
    onError: (err) => showError(err, toast),
  });

  const resolveMutation = useMutation({
    mutationFn: (payload: ResolveArbitrationPayload) =>
      resolveArbitration(id, payload),
    onSuccess: () => {
      setModal(null);
      toast.push({ type: "success", message: "仲裁已裁决" });
      invalidate();
    },
    onError: (err) => showError(err, toast),
  });

  const forceRefundMutation = useMutation({
    mutationFn: (payload: ForceRefundPayload) => forceRefund(id, payload),
    onSuccess: () => {
      setModal(null);
      toast.push({ type: "success", message: "已发起强制退款" });
      invalidate();
    },
    onError: (err) => showError(err, toast),
  });

  const noteMutation = useMutation({
    mutationFn: (note: string) => addAdminNote(id, { note }),
    onSuccess: () => {
      setModal(null);
      toast.push({ type: "success", message: "内部备注已保存" });
      invalidate();
    },
    onError: (err) => showError(err, toast),
  });

  if (isLoading) return <DetailSkeleton />;

  if (isError || !data) {
    return (
      <div className="rounded border border-red-200 bg-[color:var(--color-danger-soft)] px-4 py-3 text-sm text-[color:var(--color-danger)]">
        {error instanceof ApiError
          ? getErrorMessage(error.code, error.message)
          : "售后详情加载失败"}
        <div className="mt-2">
          <Link
            href="/console/aftersales"
            className="text-[color:var(--color-info)] hover:underline"
          >
            返回售后仲裁台
          </Link>
        </div>
      </div>
    );
  }

  const aftersales = data;
  const isArbitrating = aftersales.status === "admin_arbitrating";
  const isClaimed = aftersales.arbitrator_admin_id !== null;
  const isClaimedByMe =
    isClaimed && aftersales.arbitrator_admin_id === currentAdmin?.id;
  const canResolve = canArbitrate && isArbitrating && isClaimedByMe;
  const terminal = isTerminal(aftersales.status);
  // 强制退款：非仲裁中 + 非最终态皆可
  const canDoForceRefund =
    canForceRefund && !terminal && !isArbitrating;

  // 已认领 admin 摘要
  const arbitratorLabel =
    aftersales.arbitrator_admin?.display_name ??
    aftersales.arbitrator_admin?.username ??
    (aftersales.arbitrator_admin_id
      ? `管理员 #${aftersales.arbitrator_admin_id}`
      : "");

  // 内部备注：从 messages 里过滤最新一条 admin reply
  const latestAdminNote = [...aftersales.messages]
    .filter((m) => m.kind === "reply" && m.sender_type === "admin")
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )[0];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/console/aftersales"
            className="mb-2 inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-800"
          >
            ← 返回售后仲裁台
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-mono text-lg font-semibold text-neutral-900">
              {aftersales.aftersales_no}
            </h1>
            <AftersalesStatusBadge status={aftersales.status} />
            <AftersalesTypeIcon type={aftersales.type} />
            {aftersales.escalation_reason ? (
              <EscalationReasonBadge reason={aftersales.escalation_reason} />
            ) : null}
          </div>
          <p className="mt-1 text-sm text-neutral-500">
            关联订单：
            <Link
              href={`/console/orders/${aftersales.order_no}`}
              className="ml-1 font-mono text-[color:var(--color-info)] hover:underline"
            >
              {aftersales.order_no}
            </Link>
            <span className="ml-3">创建于 {formatDateTime(aftersales.created_at)}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          {/* admin_arbitrating 分支 */}
          {isArbitrating && !isClaimed && canArbitrate ? (
            <TakeOverButton
              aftersalesId={aftersales.id}
              alreadyTakenOver={false}
            />
          ) : null}
          {isArbitrating && isClaimed && !isClaimedByMe ? (
            <span className="rounded border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-600">
              已被 {arbitratorLabel} 认领
            </span>
          ) : null}
          {isArbitrating && isClaimedByMe ? (
            <>
              <Badge tone="info">您已认领</Badge>
              {canResolve ? (
                <Button
                  variant="danger"
                  onClick={() => setModal("resolve")}
                  aria-label="裁决"
                >
                  裁决
                </Button>
              ) : null}
            </>
          ) : null}
          {/* 释放回池：组长可释放任何人，认领本人也可释放自己 */}
          {isArbitrating && isClaimed && (canManage || isClaimedByMe) ? (
            <Button variant="secondary" onClick={() => setModal("release")}>
              释放回池
            </Button>
          ) : null}
          {canDoForceRefund ? (
            <Button variant="danger" onClick={() => setModal("force-refund")}>
              强制退款
            </Button>
          ) : null}
          {canAddNote ? (
            <Button variant="secondary" onClick={() => setModal("note")}>
              {latestAdminNote ? "追加备注" : "添加内部备注"}
            </Button>
          ) : null}
        </div>
      </div>

      {/* Warning strip 若已认领且是当前 admin，提醒及时处理 */}
      {isArbitrating && isClaimedByMe ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          您已认领此仲裁，请及时处理。仲裁一旦作出即生效，不可撤销。
        </div>
      ) : null}

      {/* 纯只读角色提示（如业务管理员） */}
      {!canArbitrate && !canForceRefund && !canAddNote ? (
        <div className="rounded border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
          您当前为只读权限，可查看完整售后信息，但无法执行认领、裁决、强制退款或内部备注。
        </div>
      ) : null}

      {/* 内部备注（顶部展示最新一条） */}
      {latestAdminNote ? (
        <section
          aria-label="管理员内部备注"
          className="rounded-md border-2 border-amber-300 bg-amber-50 p-3"
        >
          <div className="mb-1 flex items-center gap-2">
            <Badge tone="warning">仅管理员可见</Badge>
            <span className="text-xs font-medium text-amber-800">
              最新备注 · {latestAdminNote.sender_display_name ?? `admin #${latestAdminNote.sender_id ?? "?"}`}
              <span className="ml-2 text-neutral-500">
                {formatDateTime(latestAdminNote.created_at)}
              </span>
            </span>
          </div>
          <p className="whitespace-pre-wrap text-sm text-amber-900">
            {latestAdminNote.content}
          </p>
        </section>
      ) : null}

      {/* 主体：左栏基础信息 + 右栏证据 & timeline */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ---- 左栏 ---- */}
        <div className="flex flex-col gap-4">
          {/* 用户 + 商家 */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card title="用户">
              <Field label="用户 ID">
                <span className="font-mono">#{aftersales.user_id}</span>
              </Field>
              {aftersales.user?.nickname ? (
                <Field label="昵称">{aftersales.user.nickname}</Field>
              ) : null}
              {aftersales.user?.phone ? (
                <Field label="手机（明文）">
                  <span className="tabular-nums">{aftersales.user.phone}</span>
                </Field>
              ) : null}
              {aftersales.user?.email ? (
                <Field label="邮箱">{aftersales.user.email}</Field>
              ) : null}
            </Card>
            <Card title="店铺">
              <Field label="店铺名">
                {aftersales.shop?.name ?? "—"}
                <span className="ml-1 text-xs text-neutral-400">
                  #{aftersales.shop_id}
                </span>
              </Field>
              {aftersales.shop?.contact_name ? (
                <Field label="联系人">{aftersales.shop.contact_name}</Field>
              ) : null}
              {aftersales.shop?.contact_phone ? (
                <Field label="联系电话">
                  <span className="tabular-nums">
                    {aftersales.shop.contact_phone}
                  </span>
                </Field>
              ) : null}
            </Card>
          </div>

          {/* 订单摘要 */}
          <Card
            title="关联订单"
            action={
              <Link
                href={`/console/orders/${aftersales.order_no}`}
                className="text-xs text-[color:var(--color-info)] hover:underline"
              >
                查看订单详情 →
              </Link>
            }
          >
            <Field label="订单号">
              <span className="font-mono">{aftersales.order_no}</span>
            </Field>
            {aftersales.order ? (
              <>
                <Field label="订单状态">{aftersales.order.status}</Field>
                <Field label="订单总额">
                  <span className="tabular-nums">
                    ¥{(aftersales.order.total_cents / 100).toFixed(2)}
                  </span>
                </Field>
                {aftersales.order.paid_at ? (
                  <Field label="支付时间">
                    <span className="tabular-nums">
                      {formatDateTime(aftersales.order.paid_at)}
                    </span>
                  </Field>
                ) : null}
              </>
            ) : null}
          </Card>

          {/* 申请说明 & 金额 */}
          <Card title="申请与金额">
            <Field label="原因分类">
              {reasonCategoryLabel(aftersales.reason_category)}
            </Field>
            <Field label="用户说明">
              <p className="whitespace-pre-wrap text-sm text-neutral-700">
                {aftersales.reason_note}
              </p>
            </Field>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div className="rounded border border-neutral-200 bg-neutral-50 p-2">
                <div className="text-xs text-neutral-500">用户申请金额</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-neutral-900">
                  ¥{(aftersales.refund_amount_cents / 100).toFixed(2)}
                </div>
              </div>
              <div className="rounded border-2 border-[color:var(--color-primary-200)] bg-[color:var(--color-primary-100)] p-2">
                <div className="text-xs text-[color:var(--color-primary-800)]">
                  实际退款金额
                </div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-[color:var(--color-primary)]">
                  {aftersales.actual_refund_cents !== null
                    ? `¥${(aftersales.actual_refund_cents / 100).toFixed(2)}`
                    : "—"}
                </div>
              </div>
            </div>
            {aftersales.refund_txn_no ? (
              <Field label="退款流水号">
                <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-[11px]">
                  {aftersales.refund_txn_no}
                </code>
              </Field>
            ) : null}
            {aftersales.arbitration_conclusion ? (
              <Field label="仲裁结论">
                <p className="whitespace-pre-wrap text-sm text-neutral-700">
                  {aftersales.arbitration_conclusion}
                </p>
              </Field>
            ) : null}
          </Card>

          {/* 商品明细 */}
          <Card title={`商品明细（${aftersales.items.length}）`}>
            {aftersales.items.length === 0 ? (
              <div className="text-xs text-neutral-400">暂无商品明细</div>
            ) : (
              <ul className="flex flex-col divide-y divide-neutral-100">
                {aftersales.items.map((item) => (
                  <ItemRow key={item.id} item={item} />
                ))}
              </ul>
            )}
          </Card>
        </div>

        {/* ---- 右栏 ---- */}
        <div className="flex flex-col gap-4">
          <Card title="证据画廊">
            <EvidenceGallery evidences={aftersales.evidences} />
          </Card>

          <Card title={`时间轴 & 消息（${aftersales.status_history.length + aftersales.messages.length}）`}>
            <AftersalesTimeline
              histories={aftersales.status_history}
              messages={aftersales.messages}
            />
          </Card>
        </div>
      </div>

      {/* Modals */}
      <ResolveModal
        open={modal === "resolve"}
        onClose={() => setModal(null)}
        onSubmit={(payload) => resolveMutation.mutate(payload)}
        submitting={resolveMutation.isPending}
        refundAmountCents={aftersales.refund_amount_cents}
        aftersalesNo={aftersales.aftersales_no}
      />
      <ForceRefundModal
        open={modal === "force-refund"}
        onClose={() => setModal(null)}
        onSubmit={(payload) => forceRefundMutation.mutate(payload)}
        submitting={forceRefundMutation.isPending}
        maxRefundCents={aftersales.refund_amount_cents}
        aftersalesNo={aftersales.aftersales_no}
      />
      <AdminNoteModal
        open={modal === "note"}
        onClose={() => setModal(null)}
        onSubmit={(note) => noteMutation.mutate(note)}
        submitting={noteMutation.isPending}
      />

      {/* 释放回公共池确认 */}
      <Modal
        open={modal === "release"}
        onClose={() => setModal(null)}
        closeOnOverlay={!releaseMutation.isPending}
        title="释放仲裁单回公共池"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setModal(null)}
              disabled={releaseMutation.isPending}
            >
              取消
            </Button>
            <Button
              variant="danger"
              loading={releaseMutation.isPending}
              onClick={() => releaseMutation.mutate()}
            >
              确认释放
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3 text-sm text-neutral-700">
          <p>
            确定要将仲裁单{" "}
            <strong className="font-mono">{aftersales.aftersales_no}</strong>{" "}
            释放回公共池吗？
          </p>
          <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            释放后该单回到未认领状态，任何客服专员均可接手；当前认领人将失去操作权。
          </p>
        </div>
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AdminNoteModal (inline，简单文本域 + 保存)
// ---------------------------------------------------------------------------

const NOTE_MIN = 2;
const NOTE_MAX = 1000;

function AdminNoteModal({
  open,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (note: string) => void;
  submitting: boolean;
}) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const openKey = open ? "open" : "closed";
  const [lastOpen, setLastOpen] = useState("closed");
  if (openKey !== lastOpen) {
    setLastOpen(openKey);
    if (open) {
      setNote("");
      setError(null);
    }
  }

  const handleSubmit = () => {
    const trimmed = note.trim();
    if (trimmed.length < NOTE_MIN) {
      setError(`备注不能为空`);
      return;
    }
    if (trimmed.length > NOTE_MAX) {
      setError(`备注不得超过 ${NOTE_MAX} 字`);
      return;
    }
    setError(null);
    onSubmit(trimmed);
  };

  return (
    <Modal
      open={open}
      onClose={submitting ? () => undefined : onClose}
      title="内部备注（仅管理员可见）"
      closeOnOverlay={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button loading={submitting} onClick={handleSubmit}>
            保存备注
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="rounded bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
          此备注写入售后消息流（kind=reply），用户 / 商家看不到。用于团队内部记录跟进情况。
        </p>
        <FormField label="备注内容" required error={error}>
          <textarea
            className="block h-32 w-full resize-none rounded border border-[color:var(--color-border)] bg-white px-3 py-2 text-sm outline-none focus:border-[color:var(--color-primary)] focus:ring-1 focus:ring-[color:var(--color-primary)]/20"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={NOTE_MAX}
            placeholder="例如：已电话联系用户，用户同意继续等待…"
          />
        </FormField>
        <div className="text-right text-xs text-neutral-400">
          {note.trim().length} / {NOTE_MAX}
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// 证据画廊按 stage 分组
// ---------------------------------------------------------------------------

const STAGE_LABEL: Record<EvidenceStage, string> = {
  apply: "申请凭证",
  merchant_review: "商家审核凭证",
  user_return: "用户寄回凭证",
  merchant_receive: "商家收货凭证",
  exchange_ship: "换货再发货凭证",
  appeal: "用户申诉凭证",
  arbitration: "仲裁凭证",
};

const STAGE_ORDER: readonly EvidenceStage[] = [
  "apply",
  "merchant_review",
  "user_return",
  "merchant_receive",
  "exchange_ship",
  "appeal",
  "arbitration",
];

function EvidenceGallery({
  evidences,
}: {
  evidences: readonly AftersalesEvidenceOut[];
}) {
  if (evidences.length === 0) {
    return <div className="text-xs text-neutral-400">暂无凭证</div>;
  }
  const grouped = new Map<EvidenceStage, AftersalesEvidenceOut[]>();
  for (const ev of evidences) {
    const arr = grouped.get(ev.stage) ?? [];
    arr.push(ev);
    grouped.set(ev.stage, arr);
  }
  return (
    <div className="flex flex-col gap-3">
      {STAGE_ORDER.filter((s) => grouped.has(s)).map((stage) => {
        const list = grouped.get(stage) ?? [];
        return (
          <details key={stage} open className="group">
            <summary className="mb-2 flex cursor-pointer items-center gap-2 text-xs font-medium text-neutral-700">
              <span className="rounded bg-neutral-100 px-2 py-0.5 text-neutral-700">
                {STAGE_LABEL[stage]}
              </span>
              <span className="text-neutral-400">{list.length} 张</span>
            </summary>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {list.map((ev) => (
                <a
                  key={ev.id}
                  href={imageUrl(ev.image_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="group/pic relative block overflow-hidden rounded border border-neutral-200"
                  title={ev.note ?? `点击查看大图`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl(ev.image_url)}
                    alt={ev.note ?? "凭证图片"}
                    className="h-24 w-full object-cover transition group-hover/pic:scale-105"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).src =
                        imagePlaceholder();
                    }}
                  />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 truncate bg-black/50 px-1.5 py-0.5 text-[10px] text-white">
                    {ev.uploader_type} · {formatDate(ev.created_at)}
                  </div>
                </a>
              ))}
            </div>
          </details>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function ItemRow({ item }: { item: AftersalesItemOut }) {
  return (
    <li className="flex items-center gap-3 py-2">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageUrl(item.sku_image ?? undefined)}
        alt={item.spu_title ?? "商品"}
        width={40}
        height={40}
        className="h-10 w-10 shrink-0 rounded border border-neutral-200 object-cover"
        onError={(e) => {
          (e.currentTarget as HTMLImageElement).src = imagePlaceholder();
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="truncate text-sm text-neutral-900">
          {item.spu_title ?? `商品 #${item.order_item_id}`}
        </div>
        <div className="text-xs text-neutral-500">
          {item.sku_specs
            ? Object.entries(item.sku_specs)
                .map(([k, v]) => `${k}=${v}`)
                .join(" · ")
            : "—"}
        </div>
      </div>
      <div className="text-right text-xs text-neutral-700">
        <div className="tabular-nums">
          {item.unit_price_cents !== undefined
            ? `¥${(item.unit_price_cents / 100).toFixed(2)}`
            : "—"}
          <span className="ml-1 text-neutral-400">× {item.quantity}</span>
        </div>
        <div className="mt-0.5 font-semibold tabular-nums text-neutral-900">
          ¥{(item.refund_amount_cents / 100).toFixed(2)}
        </div>
      </div>
    </li>
  );
}

function Card({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-md border border-[color:var(--color-border)] bg-white">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {title}
        </span>
        {action}
      </header>
      <dl className="flex flex-col gap-2 p-4">{children}</dl>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-neutral-800">{children}</dd>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-6 w-56" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function reasonCategoryLabel(cat: AdminAftersalesDetail["reason_category"]): string {
  switch (cat) {
    case "quality_issue":
      return "质量问题";
    case "wrong_item":
      return "发错商品";
    case "damage_in_transit":
      return "运输破损";
    case "not_as_described":
      return "与描述不符";
    case "no_longer_needed":
      return "不想要了";
    case "duplicate_purchase":
      return "重复购买";
    case "other":
      return "其他";
    default:
      return cat;
  }
}

function showError(
  err: unknown,
  toast: { push: (t: { type: "error"; message: string }) => void },
) {
  const msg =
    err instanceof ApiError
      ? getErrorMessage(err.code, err.message)
      : "操作失败";
  toast.push({ type: "error", message: msg });
}
