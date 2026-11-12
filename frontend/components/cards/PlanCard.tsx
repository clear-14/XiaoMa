/** 学习计划卡片：PRD §5.3，展示当前正式计划版本与排期条目。 */

import type { ReactNode } from "react";

import {
  formatValue,
  readNumber,
  readObjectArray,
  readString,
  type PlanCard,
} from "@/lib/cards";

import CardShell, { CardFacts, CardSection } from "./CardShell";

export default function PlanCard({
  card,
  actions,
  index,
}: {
  card: PlanCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const goal = readString(payload, "learning_goal");
  const dailyMinutes = readNumber(payload, "daily_study_minutes");
  const durationDays = readNumber(payload, "expected_duration_days");
  const planStatus = readString(payload, "status");
  const items = readObjectArray(payload, "items");

  return (
    <CardShell
      type="plan_card"
      title={payload.course_name}
      meta={`v${payload.version_number}`}
      actions={actions}
      index={index}
    >
      <CardFacts
        items={[
          { label: "计划条目", value: `${payload.items.length} 项` },
          ...(goal ? [{ label: "学习目标", value: goal }] : []),
          ...(dailyMinutes !== null
            ? [{ label: "每日学习", value: `${dailyMinutes} 分钟` }]
            : []),
          ...(durationDays !== null
            ? [{ label: "预计周期", value: `${durationDays} 天` }]
            : []),
          ...(planStatus ? [{ label: "计划状态", value: planStatus }] : []),
        ]}
      />
      {items.length > 0 ? (
        <CardSection title="排期明细">
          <ol className="win-card-plan-items">
            {items.map((item, i) => {
              const day = readNumber(item, "day_index");
              const minutes = readNumber(item, "estimated_minutes");
              return (
                <li className="win-card-plan-item" key={`p-${i}`}>
                  <span className="win-card-plan-day">
                    {day !== null ? `D${String(day).padStart(2, "0")}` : `—`}
                  </span>
                  <span className="win-card-plan-name">
                    {formatValue(item.knowledge_point_name)}
                  </span>
                  <span className="win-card-plan-meta">
                    {minutes !== null ? `${minutes} 分钟` : "—"}
                    {readString(item, "status")
                      ? ` · ${readString(item, "status")}`
                      : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
