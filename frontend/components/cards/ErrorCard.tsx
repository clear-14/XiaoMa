/**
 * 失败 / 降级卡片：契约 §3.5、§9.7。
 *
 * 未知版本、未知类型、不完整 JSON、缺必备字段，以及后端明确写入的失败回复
 * 都会收敛到这张卡片，用虚线边框与 danger 色明确展示失败原因，不渲染空白。
 */

import type { ReactNode } from "react";

import { readString, type ErrorCard } from "@/lib/cards";

import CardShell from "./CardShell";

export default function ErrorCard({
  card,
  actions,
  index,
}: {
  card: ErrorCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const detail = readString(payload, "detail");

  return (
    <CardShell
      type="error_card"
      title="操作失败"
      meta="降级展示"
      actions={actions}
      index={index}
      tone="danger"
    >
      <p className="win-card-error-reason" role="alert">
        {payload.reason}
      </p>
      {detail ? <p className="win-card-prose">{detail}</p> : null}
    </CardShell>
  );
}
