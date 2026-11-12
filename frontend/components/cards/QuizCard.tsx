/**
 * 测验题目卡片：PRD §5.4。
 *
 * 只展示题干、题型与选项；**不读取也不展示** correct_answer / explanation /
 * score / is_correct —— 答案与评分必须由后端计算后在结果卡片呈现，
 * 前端不得从题目数据推断结果（PRD §5.4「不能只通过 AI 自由对话判断测验结果」）。
 */

import type { ReactNode } from "react";

import {
  formatValue,
  readObjectArray,
  readString,
  readStringArray,
  type QuizCard,
} from "@/lib/cards";
import { questionTypeLabel } from "@/lib/quiz";

import CardShell, { CardFacts } from "./CardShell";

export default function QuizCard({
  card,
  actions,
  index,
}: {
  card: QuizCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const scopeName = readString(payload, "scope_name");
  const questionCount = payload.questions.length;
  const questions = readObjectArray(payload, "questions");

  return (
    <CardShell
      type="quiz_card"
      title={scopeName ?? "知识点测验"}
      meta={payload.attempt_id}
      actions={actions}
      index={index}
    >
      <CardFacts
        items={[
          { label: "题目数量", value: `${questionCount} 题` },
          { label: "评分方式", value: "提交后由后端统一评分" },
        ]}
      />
      <ol className="win-card-questions">
        {questions.map((question, i) => {
          const stem = formatValue(question.stem);
          const questionType = readString(question, "question_type");
          const options = readObjectArray(question, "options");
          const keywords = readStringArray(question, "keywords");
          return (
            <li className="win-card-question" key={`q-${i}`}>
              <div className="win-card-question-head">
                <span className="win-card-question-no">{`Q${String(i + 1).padStart(2, "0")}`}</span>
                {questionType ? (
                  <span className="win-card-tag">
                    {questionTypeLabel(questionType)}
                  </span>
                ) : null}
              </div>
              <p className="win-card-question-stem">{stem}</p>
              {options.length > 0 ? (
                <ul className="win-card-options">
                  {options.map((option, oi) => (
                    <li key={`o-${i}-${oi}`}>
                      <span className="win-card-option-key">
                        {formatValue(option.key)}
                      </span>
                      <span>{formatValue(option.text)}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {keywords.length > 0 ? (
                <p className="win-card-hint">答题要点：{keywords.join("、")}</p>
              ) : null}
            </li>
          );
        })}
      </ol>
      {questions.length !== questionCount ? (
        <p className="win-card-warn">
          有 {questionCount - questions.length} 道题的数据格式不完整，已跳过展示。
        </p>
      ) : null}
    </CardShell>
  );
}
