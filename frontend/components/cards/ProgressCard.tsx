/**
 * 学习进度卡片：PRD §5.6。
 *
 * 所有数字直接展示后端原值，不做前端推算；唯一的百分比刻度条取自可选的
 * `plan_progress_percent`，缺失时不显示刻度，绝不编造进度。
 */

import type { CSSProperties, ReactNode } from "react";

import {
  formatValue,
  readNumber,
  readObjectArray,
  readString,
  readStringArray,
  type ProgressCard,
} from "@/lib/cards";

import CardShell, { CardFacts, CardSection } from "./CardShell";

export default function ProgressCard({
  card,
  actions,
  index,
}: {
  card: ProgressCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const chapter = readString(payload, "chapter_title");
  const pendingVerification = readNumber(payload, "pending_verification_count");
  const reviewDue = readNumber(payload, "review_due_count");
  const nextStep = readString(payload, "next_step");
  const percentRaw = readNumber(payload, "plan_progress_percent");
  const percent =
    percentRaw === null ? null : Math.max(0, Math.min(100, percentRaw));
  const meterStyle: CSSProperties = { width: `${percent ?? 0}%` };

  const weakObjects = readObjectArray(payload, "weak_points");
  const weakPoints =
    weakObjects.length > 0
      ? weakObjects.map((item) =>
          formatValue(item.name ?? item.knowledge_point_name),
        )
      : readStringArray(payload, "weak_points");

  return (
    <CardShell
      type="progress_card"
      title={payload.course_name}
      meta={chapter ?? undefined}
      actions={actions}
      index={index}
    >
      <CardFacts
        items={[
          { label: "已掌握知识点", value: `${payload.mastered_count} 个` },
          { label: "学习中知识点", value: `${payload.learning_count} 个` },
          ...(pendingVerification !== null
            ? [{ label: "待验证", value: `${pendingVerification} 个` }]
            : []),
          ...(reviewDue !== null
            ? [{ label: "待复习", value: `${reviewDue} 个` }]
            : []),
        ]}
      />
      {percent !== null ? (
        <div
          className="win-card-meter"
          role="img"
          aria-label={`计划完成度 ${percent}%`}
        >
          <span className="win-card-meter-fill" style={meterStyle} />
        </div>
      ) : null}
      {weakPoints.length > 0 ? (
        <CardSection title="薄弱知识点">
          <ul className="win-card-list">
            {weakPoints.map((item, i) => (
              <li key={`w-${i}`}>{item}</li>
            ))}
          </ul>
        </CardSection>
      ) : null}
      {nextStep ? (
        <CardSection title="推荐下一步">
          <p className="win-card-prose">{nextStep}</p>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
