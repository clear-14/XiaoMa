/**
 * 测验结果卡片：PRD §5.4，得分 / 正确答案 / 解析均由后端评分结果提供。
 *
 * 百分比刻度条只由后端给出的 score 与 total_points 派生，用于可视化，
 * 不引入新的业务数字；所有文字数字直接展示后端原值。
 */

import type { CSSProperties, ReactNode } from "react";

import {
  formatValue,
  readBoolean,
  readNumber,
  readObjectArray,
  type QuizResultCard,
} from "@/lib/cards";

import CardShell, { CardFacts, CardSection } from "./CardShell";

export default function QuizResultCard({
  card,
  actions,
  index,
}: {
  card: QuizResultCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const { score, total_points: totalPoints } = payload;
  const percent =
    totalPoints > 0
      ? Math.max(0, Math.min(100, Math.round((score / totalPoints) * 100)))
      : 0;
  const meterStyle: CSSProperties = { width: `${percent}%` };
  const questions = readObjectArray(payload, "questions");
  const masteryUpdates = readObjectArray(payload, "mastery_updates");
  const masteryCount = readNumber(payload, "mastered_count");

  return (
    <CardShell
      type="quiz_result_card"
      title="测验结果"
      meta={payload.attempt_id}
      actions={actions}
      index={index}
    >
      <div className="win-card-score">
        <span className="win-card-score-value">
          {score}
          <span className="win-card-score-total"> / {totalPoints}</span>
        </span>
        <span className="win-card-score-unit">分</span>
      </div>
      <div
        className="win-card-meter"
        role="img"
        aria-label={`得分 ${score} 分，满分 ${totalPoints} 分`}
      >
        <span className="win-card-meter-fill" style={meterStyle} />
      </div>
      <CardFacts
        items={[
          { label: "得分", value: `${score} / ${totalPoints}` },
          ...(masteryCount !== null
            ? [{ label: "本轮新掌握", value: `${masteryCount} 个知识点` }]
            : []),
        ]}
      />
      {questions.length > 0 ? (
        <CardSection title="逐题解析">
          <ol className="win-card-questions">
            {questions.map((question, i) => {
              const correct = readBoolean(question, "is_correct");
              return (
                <li className="win-card-question" key={`r-${i}`}>
                  <div className="win-card-question-head">
                    <span className="win-card-question-no">{`Q${String(i + 1).padStart(2, "0")}`}</span>
                    {correct === null ? null : (
                      <span
                        className={`win-card-tag${correct ? " win-card-tag-ok" : " win-card-tag-bad"}`}
                      >
                        {correct ? "答对" : "答错"}
                      </span>
                    )}
                  </div>
                  <p className="win-card-question-stem">
                    {formatValue(question.stem)}
                  </p>
                  <CardFacts
                    items={[
                      {
                        label: "正确答案",
                        value: formatValue(question.correct_answer),
                      },
                      { label: "本题得分", value: formatValue(question.score) },
                    ]}
                  />
                  {typeof question.explanation === "string" &&
                  question.explanation.trim() ? (
                    <p className="win-card-prose win-card-explanation">
                      {question.explanation}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </CardSection>
      ) : null}
      {masteryUpdates.length > 0 ? (
        <CardSection title="掌握状态更新">
          <ul className="win-card-list">
            {masteryUpdates.map((item, i) => (
              <li key={`m-${i}`}>
                {formatValue(item.knowledge_point_name)}：
                {readBoolean(item, "achieved") === true ? "已达成" : "未达成"}
              </li>
            ))}
          </ul>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
