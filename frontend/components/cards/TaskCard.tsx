/** 今日学习任务卡片：PRD §5.2，数据来自后端今日任务记录。 */

import type { ReactNode } from "react";

import { readNumber, readString, type TaskCard } from "@/lib/cards";

import CardShell, { CardFacts } from "./CardShell";

export default function TaskCard({
  card,
  actions,
  index,
}: {
  card: TaskCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const dayIndex = readNumber(payload, "day_index");
  const chapter = readString(payload, "chapter_title");
  const status = readString(payload, "status");
  const mastery = readString(payload, "mastery_status");

  return (
    <CardShell
      type="task_card"
      title={payload.title}
      meta={payload.knowledge_point_code}
      actions={actions}
      index={index}
    >
      <CardFacts
        items={[
          { label: "关联知识点", value: payload.knowledge_point_name },
          { label: "学习目标", value: payload.learning_goal },
          { label: "预计时长", value: `${payload.estimated_minutes} 分钟` },
          ...(chapter ? [{ label: "所属章节", value: chapter }] : []),
          ...(dayIndex !== null
            ? [{ label: "计划进度", value: `第 ${dayIndex} 天` }]
            : []),
          ...(status ? [{ label: "任务状态", value: status }] : []),
          ...(mastery ? [{ label: "掌握状态", value: mastery }] : []),
        ]}
      />
    </CardShell>
  );
}
