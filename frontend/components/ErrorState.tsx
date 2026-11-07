import type { ReactNode } from "react";

/** 统一错误状态视图。 */
export default function ErrorState({
  title = "出错了",
  message,
  action,
}: {
  title?: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="error-state" role="alert">
      <h2 className="error-state-title">{title}</h2>
      {message && <p className="error-state-desc">{message}</p>}
      {action && <div className="error-state-action">{action}</div>}
    </div>
  );
}
