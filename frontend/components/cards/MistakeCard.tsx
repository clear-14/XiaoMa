/** 错题复习卡片：PRD §5.5，展示真实错题、原始答案与解析。 */

import type { ReactNode } from "react";

import {
  formatValue,
  readNumber,
  readString,
  type MistakeCard,
} from "@/lib/cards";

import CardShell, { CardFacts, CardSection } from "./CardShell";

export default function MistakeCard({
  card,
  actions,
  index,
}: {
  card: MistakeCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const lastAnswer = readString(payload, "last_answer");
  const correctAnswer = readString(payload, "correct_answer");
  const explanation = readString(payload, "explanation");
  const nextReview = readString(payload, "next_review_at");
  const reviewStatus = readString(payload, "review_status");
  const attemptCount = readNumber(payload, "attempt_count");

  return (
    <CardShell
      type="mistake_card"
      title={payload.knowledge_point_name}
      meta={payload.mistake_id}
      actions={actions}
      index={index}
    >
      <CardSection title="错题题干">
        <p className="win-card-prose">{payload.question_stem}</p>
      </CardSection>
      <CardFacts
        items={[
          { label: "当时的答案", value: lastAnswer ?? formatValue(payload.last_answer) },
          { label: "正确答案", value: correctAnswer ?? formatValue(payload.correct_answer) },
          ...(attemptCount !== null
            ? [{ label: "作答次数", value: `${attemptCount} 次` }]
            : []),
          ...(reviewStatus ? [{ label: "复习状态", value: reviewStatus }] : []),
          ...(nextReview ? [{ label: "下次复习", value: nextReview }] : []),
        ]}
      />
      {explanation ? (
        <CardSection title="解析">
          <p className="win-card-prose">{explanation}</p>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
