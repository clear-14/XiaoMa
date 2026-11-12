"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";

import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import { UNAUTHORIZED_EVENT } from "@/lib/access-token";
import { getAuthStatus, login } from "@/lib/auth";

type GateState = "loading" | "login" | "ready" | "error";

/**
 * 前端访问密码门禁（PRD 11.1）。
 *
 * 后端才是访问控制的强制点：这里只负责在需要登录时展示密码页，
 * 并把登录后的令牌交给 API 层。即使绕过此页面，后端仍会拒绝无令牌请求。
 */
export default function AccessGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>("loading");
  const [required, setRequired] = useState(false);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const status = await getAuthStatus();
      setRequired(status.required);
      setState(status.required && !status.authenticated ? "login" : "ready");
    } catch (err) {
      setError(getErrorMessage(err));
      setState("error");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void check();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [check]);

  useEffect(() => {
    const onUnauthorized = () => {
      setState((current) => {
        if (current === "ready" && required) {
          setPassword("");
          setError("登录已过期，请重新输入访问密码");
          return "login";
        }
        return current;
      });
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [required]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!password.trim() || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await login(password);
      setPassword("");
      setState("ready");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (state === "loading") {
    return <LoadingState label="正在检查访问权限…" />;
  }

  if (state === "error") {
    return (
      <div className="login-shell">
        <ErrorState
          title="无法连接小码后端"
          message={error ?? undefined}
          action={
            <button type="button" className="btn btn-primary" onClick={() => void check()}>
              重试
            </button>
          }
        />
      </div>
    );
  }

  if (state === "login") {
    return (
      <div className="login-shell">
        <form className="login-card card" onSubmit={submit}>
          <div className="login-brand">
            <span className="sidebar-logo">小</span>
            <div>
              <h1 className="login-title">小码 Xiaoma</h1>
              <p className="muted">此部署已启用访问密码</p>
            </div>
          </div>
          <p className="login-desc">
            请输入部署时设置的访问密码。密码只发送到你自己部署的后端，
            不会上传到开发者服务器。
          </p>
          <div className="form-group">
            <label className="form-label" htmlFor="access-password">
              访问密码
            </label>
            <input
              id="access-password"
              className="form-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={submitting}
              autoFocus
            />
          </div>
          {error && <div className="inline-error">{error}</div>}
          <button
            type="submit"
            className="btn btn-primary login-submit"
            disabled={submitting || !password.trim()}
          >
            {submitting ? "正在登录…" : "进入小码"}
          </button>
          <p className="form-hint login-hint">
            忘记密码请查看部署目录 `.env` 中的 XIAOMA_ACCESS_PASSWORD；修改后需重启服务。
          </p>
        </form>
      </div>
    );
  }

  return <>{children}</>;
}
