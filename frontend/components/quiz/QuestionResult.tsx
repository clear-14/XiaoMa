"use client";

import {
  correctAnswerValue,
  formatAnswer,
  questionTypeLabel,
} from "@/lib/quiz";
import type { QuizQuestion } from "@/lib/types";

function correctKeys(question: QuizQuestion): Set<string> {
  const raw = correctAnswerValue(question);
  const values = Array.isArray(raw) ? raw : [raw];
  return new Set(values.filter((item) => item !== null && item !== undefined).map(String));
}

export default function QuestionResult({ question }: { question: QuizQuestion }) {
  const keys = correctKeys(question);
  const userAnswer = question.user_answer;
  const selected = new Set(
    (Array.isArray(userAnswer) ? userAnswer : [userAnswer])
      .filter((item) => item !== null && item !== undefined)
      .map(String),
  );
  const basis = question.grading_basis;
  const isSubjective =
    question.question_type === "short_answer" ||
    question.question_type === "code_analysis" ||
    question.question_type === "code_writing";

  return (
    <article
      className={`card question-card question-result-card${
        question.is_correct ? " question-correct" : " question-wrong"
      }`}
    >
      <div className="question-head">
        <div className="tag-row">
          <span className="badge badge-pending">
            第 {question.order} 题 · {questionTypeLabel(question.question_type)}
          </span>
          <span className="badge">
            {question.source === "ai" ? "AI 变式题（已验证）" : "内置题库"}
          </span>
        </div>
        <span
          className={`badge ${
            question.is_correct ? "badge-completed" : "badge-danger"
          }`}
        >
          {question.is_correct ? "通过" : "未通过"} ·{" "}
          {question.score ?? 0}/{question.max_score} 分
        </span>
      </div>

      <p className="question-stem">{question.stem}</p>

      {question.options && question.options.length > 0 && (
        <ul className="result-options">
          {question.options.map((option) => {
            const isCorrectOption = keys.has(option.key);
            const isUserOption = selected.has(option.key);
            const className = [
              "result-option",
              isCorrectOption ? "result-option-correct" : "",
              !isCorrectOption && isUserOption ? "result-option-wrong" : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <li key={option.key} className={className}>
                <span className="answer-option-key">{option.key}</span>
                <span>{option.text}</span>
                {isCorrectOption && <span className="option-flag">正确答案</span>}
                {isUserOption && <span className="option-flag">你的选择</span>}
              </li>
            );
          })}
        </ul>
      )}

      <dl className="answer-summary">
        <div>
          <dt>你的答案</dt>
          <dd>{formatAnswer(question, userAnswer)}</dd>
        </div>
        <div>
          <dt>正确答案</dt>
          <dd>{formatAnswer(question, correctAnswerValue(question))}</dd>
        </div>
      </dl>

      {question.explanation && (
        <div className="explanation-block">
          <h4>解析</h4>
          <p>{question.explanation}</p>
        </div>
      )}

      {basis && (
        <div className="grading-basis">
          <h4>评分依据</h4>
          {basis.type === "keyword_rubric" ? (
            <>
              <p>
                主观题按参考答案关键词覆盖评分：命中{" "}
                {basis.matched_count ?? 0}/{basis.keyword_count ?? 0}（
                {Math.round((basis.ratio ?? 0) * 100)}%）。
              </p>
              {basis.matched_keywords && basis.matched_keywords.length > 0 && (
                <p className="keyword-line">
                  已命中：
                  {basis.matched_keywords.map((keyword) => (
                    <span key={keyword} className="keyword-tag keyword-hit">
                      {keyword}
                    </span>
                  ))}
                </p>
              )}
              {basis.missing_keywords && basis.missing_keywords.length > 0 && (
                <p className="keyword-line">
                  未命中：
                  {basis.missing_keywords.map((keyword) => (
                    <span key={keyword} className="keyword-tag keyword-miss">
                      {keyword}
                    </span>
                  ))}
                </p>
              )}
              {basis.reference && (
                <p className="muted">参考答案：{basis.reference}</p>
              )}
            </>
          ) : (
            <p className="muted">
              客观题全对得分；部分正确不得分。
              {isSubjective ? " 主观题会保留关键词评分依据。" : ""}
            </p>
          )}
          {basis.note && <p className="muted">{basis.note}</p>}
        </div>
      )}
    </article>
  );
}
