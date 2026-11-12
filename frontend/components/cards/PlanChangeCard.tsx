/**
 * 计划调整建议卡片：PRD §5.3。
 *
 * 重要闸口：本卡片只展示调整前后差异与「需确认」标识，批次 4 不渲染任何
 * 按钮；真实确认动作在批次 5 接到 `/learning-loop` 提案确认接口，
 * 且必须经用户点击确认才保存新版本，绝不自动修改正式学习计划。
 */

import type { ReactNode } from "react";

import {
  formatValue,
  readObject,
  readString,
  readStringArray,
  type PlanChangeCard,
} from "@/lib/cards";

import CardShell, { CardSection } from "./CardShell";

const FIELD_LABELS: Record<string, string> = {
  learning_goal: "学习目标",
  daily_study_minutes: "每日学习分钟",
  expected_duration_days: "预计周期天数",
  reason: "调整原因",
  source: "来源",
};

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field;
}

export default function PlanChangeCard({
  card,
  actions,
  index,
}: {
  card: PlanChangeCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const reason = readString(payload, "reason");
  const impacts = readStringArray(payload, "impacts");
  const preview = readObject(payload, "preview");
  const current = preview ? readObject(preview, "current") : null;
  const proposed = preview ? readObject(preview, "proposed") : null;

  // 有 preview 时按「调整前 → 调整后」对照；否则退化为列出提案字段与新值。
  const comparisonKeys = new Set<string>([
    ...Object.keys(current ?? {}),
    ...Object.keys(proposed ?? {}),
    ...(current || proposed ? [] : Object.keys(payload.changes)),
  ]);

  return (
    <CardShell
      type="plan_change_card"
      title="计划调整建议"
      meta={payload.proposal_id}
      actions={actions}
      index={index}
    >
      <p className="win-card-gate" role="note">
        需你确认后才会保存为正式计划；在此之前学习计划不会发生变更。
      </p>
      {reason ? <p className="win-card-prose">调整原因：{reason}</p> : null}
      <CardSection title="调整前后差异">
        <dl className="win-card-diff">
          {[...comparisonKeys].map((field) => {
            const before = current?.[field];
            const after = proposed?.[field] ?? payload.changes[field];
            return (
              <div className="win-card-diff-row" key={field}>
                <dt>{fieldLabel(field)}</dt>
                <dd>
                  <span className="win-card-diff-before">
                    {current ? formatValue(before) : "—"}
                  </span>
                  <span className="win-card-diff-arrow" aria-hidden="true">
                    →
                  </span>
                  <span className="win-card-diff-after">
                    {formatValue(after)}
                  </span>
                </dd>
              </div>
            );
          })}
        </dl>
      </CardSection>
      {impacts.length > 0 ? (
        <CardSection title="影响范围">
          <ul className="win-card-list">
            {impacts.map((item, i) => (
              <li key={`i-${i}`}>{item}</li>
            ))}
          </ul>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
