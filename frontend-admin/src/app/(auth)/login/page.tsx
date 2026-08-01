"use client";

/**
 * 管理员登录页 (`/login`)。
 *
 * 特性：
 * - username + password + 记住登录
 * - 契约 §5.3：POST /admin/auth/login
 * - 错误 1003（账号或密码错误）/ 1004（账号被禁用）友好提示
 * - 页面顶部明示"平台管理员通道"，避免误认为是用户/商家登录
 * - 登录成功后跳转 ?redirect= 或默认 /console
 */

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { FormField } from "@/components/ui/FormField";
import { ApiError } from "@/lib/api";
import { getErrorMessage } from "@/types/errors";

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="text-sm text-neutral-400">正在加载登录页…</div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const toast = useToast();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);

    // 前端极简校验；正式校验交给后端 5001
    if (!username.trim() || !password) {
      setFormError("请填写用户名与密码");
      return;
    }

    setSubmitting(true);
    try {
      await login({ username: username.trim(), password }, remember);
      toast.push({ type: "success", message: "登录成功" });
      const redirect = searchParams.get("redirect") || "/console";
      // decodeURIComponent 是为了处理 layout 里 encodeURIComponent 过的路径
      router.replace(decodeSafe(redirect));
    } catch (err) {
      if (err instanceof ApiError) {
        // 1003 / 1004 走专用文案，其余走通用映射
        setFormError(getErrorMessage(err.code, err.message));
      } else {
        setFormError("网络异常，请稍后重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-sm rounded-lg border border-[color:var(--color-border)] bg-white p-6 shadow-card">
      <div className="mb-6 flex flex-col items-center gap-1">
        <span
          aria-hidden
          className="bg-brand-gradient mb-2 inline-flex h-10 w-10 items-center justify-center rounded-lg text-white shadow-sm"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden>
            <path
              fillRule="evenodd"
              d="M4 3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-1.5a2 2 0 0 1-1.4-.6L12 4.6A2 2 0 0 0 10.6 4H4Z"
              clipRule="evenodd"
            />
          </svg>
        </span>
        <h1 className="text-lg font-semibold text-neutral-900">JD-Clone Admin</h1>
        <p className="text-xs text-neutral-500">平台管理员通道</p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={onSubmit} noValidate>
        <FormField label="用户名" htmlFor="admin-username" required>
          <Input
            id="admin-username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="请输入管理员用户名"
            invalid={Boolean(formError)}
            disabled={submitting}
          />
        </FormField>

        <FormField label="密码" htmlFor="admin-password" required>
          <PasswordInput
            id="admin-password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入密码"
            invalid={Boolean(formError)}
            disabled={submitting}
          />
        </FormField>

        <label className="flex items-center gap-2 text-xs text-neutral-600">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="h-3.5 w-3.5"
          />
          记住登录状态（30 天）
        </label>

        {formError ? (
          <div
            role="alert"
            className="rounded border border-red-200 bg-[color:var(--color-danger-soft)] px-3 py-2 text-xs text-[color:var(--color-danger)]"
          >
            {formError}
          </div>
        ) : null}

        <Button type="submit" fullWidth loading={submitting}>
          登录
        </Button>

        <p className="mt-2 text-center text-[11px] text-neutral-400">
          管理端账号由超级管理员分配。若无法登录请线下联系。
        </p>
      </form>
    </div>
  );
}

function decodeSafe(v: string): string {
  try {
    return decodeURIComponent(v);
  } catch {
    return v;
  }
}
