"use client";

/**
 * V1.4 批次 5：卡片真实业务操作区。
 *
 * - 按钮由 `getCardActionSpecs()` 纯函数按 payload 中的真实业务标识生成，
 *   没有标识就不渲染按钮，杜绝批次 4 明确避免的「假按钮」；
 * - 每个动作调用 `runCardAction()` 中已存在的真实后端接口；
 * - 覆盖加载中 / 成功 / 失败三态，失败明确展示后端返回的原因；
 * - 重要修改（计划确认、任务完成、测验提交）先经用户二次确认；
 * - 成功后发布 `panels:refresh`，右栏四面板重新读取真实业务数据。
 *
 * 评分结果、掌握状态、计划版本等权威数据仍保存在后端业务表；这里只展示
 * 本次操作的即时反馈，不把渲染结果写回聊天记录。
 */

import { useState } from "react";

import { getErrorMessage } from "@/lib/api";
import {
  buildQuizAnswers,
  getCardActionSpecs,
  readQuizQuestions,
  type CardActionKind,
  type CardActionSpec,
} from "@/lib/card-actions";
import { runCardAction } from "@/lib/card-action-runner";
import type { Card } from "@/lib/cards";
import { publishWorkspaceEvent } from "@/lib/workspace-bus";

interface Feedback {
  tone: "ok" | "error";
  text: string;
}

export default function CardActions({ card }: { card: Card }) {
  const specs = getCardActionSpecs(card);
  const questions = readQuizQuestions(card);
  const [busy, setBusy] = useState<CardActionKind | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [reviewAnswer, setReviewAnswer] = useState("");

  if (specs.length === 0) {
    return null;
  }

  const quizAnswers = buildQuizAnswers(questions, answers);
  const needsQuizForm = specs.some((spec) => spec.kind === "submit_quiz");
  const needsReviewInput = specs.some((spec) => spec.kind === "submit_review");

  function isReady(spec: CardActionSpec): boolean {
    if (spec.kind === "submit_quiz") {
      return quizAnswers !== null;
    }
    if (spec.kind === "submit_review") {
      return reviewAnswer.trim().length > 0;
    }
    return true;
  }

  function setAnswer(questionId: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }

  async function run(spec: CardActionSpec) {
    if (spec.confirm && !window.confirm(spec.confirm)) {
      return;
    }
    setBusy(spec.kind);
    setFeedback(null);
    try {
      const text = await runCardAction(spec, {
        answers: quizAnswers ?? undefined,
        reviewAnswer,
      });
      setFeedback({ tone: "ok", text });
      publishWorkspaceEvent({ type: "panels:refresh" });
      if (spec.write) {
        publishWorkspaceEvent({ type: "conversation:changed" });
      }
    } catch (err) {
      setFeedback({ tone: "error", text: getErrorMessage(err) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="win-card-action-group">
      {needsQuizForm && questions.length > 0 ? (
        <div className="win-card-answer-form">
          {questions.map((question, index) => {
            const value = answers[question.questionId];
            return (
              <fieldset className="win-card-answer" key={question.questionId}>
                <legend>{`Q${index + 1}. ${question.stem}`}</legend>
                {question.questionType === "true_false" ? (
                  <div className="win-card-answer-options">
                    {[
                      { label: "正确", value: true },
                      { label: "错误", value: false },
                    ].map((option) => (
                      <label key={option.label}>
                        <input
                          type="radio"
                          name={question.questionId}
                          checked={value === option.value}
                          onChange={() =>
                            setAnswer(question.questionId, option.value)
                          }
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                ) : question.options.length > 0 &&
                  question.questionType !== "short_answer" ? (
                  <div className="win-card-answer-options">
                    {question.options.map((option) => {
                      const multiple =
                        question.questionType === "multiple_choice";
                      const selected = multiple
                        ? Array.isArray(value) && value.includes(option.key)
                        : value === option.key;
                      return (
                        <label key={option.key}>
                          <input
                            type={multiple ? "checkbox" : "radio"}
                            name={question.questionId}
                            value={option.key}
                            checked={selected}
                            onChange={() => {
                              if (!multiple) {
                                setAnswer(question.questionId, option.key);
                                return;
                              }
                              const current = Array.isArray(value)
                                ? value.filter(
                                    (item): item is string =>
                                      typeof item === "string",
                                  )
                                : [];
                              setAnswer(
                                question.questionId,
                                selected
                                  ? current.filter(
                                      (item) => item !== option.key,
                                    )
                                  : [...current, option.key],
                              );
                            }}
                          />
                          {`${option.key}. ${option.text}`}
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <input
                    className="form-input"
                    type="text"
                    value={typeof value === "string" ? value : ""}
                    placeholder="填写答案"
                    onChange={(event) =>
                      setAnswer(question.questionId, event.target.value)
                    }
                  />
                )}
              </fieldset>
            );
          })}
          {quizAnswers === null ? (
            <p className="win-card-answer-hint">请完成全部题目后再提交。</p>
          ) : null}
        </div>
      ) : null}

      {needsReviewInput ? (
        <label className="win-card-answer">
          <span>重新作答</span>
          <input
            className="form-input"
            type="text"
            value={reviewAnswer}
            placeholder="填写本次复习答案"
            onChange={(event) => setReviewAnswer(event.target.value)}
          />
        </label>
      ) : null}

      <div className="win-card-action-row">
        {specs.map((spec) => (
          <button
            key={spec.kind}
            type="button"
            className={`btn btn-sm${spec.write ? " btn-primary" : ""}`}
            disabled={busy !== null || !isReady(spec)}
            onClick={() => void run(spec)}
          >
            {busy === spec.kind ? "处理中…" : spec.label}
          </button>
        ))}
      </div>

      {feedback ? (
        <p
          className={`win-card-feedback win-card-feedback-${feedback.tone}`}
          role={feedback.tone === "error" ? "alert" : "status"}
        >
          {feedback.text}
        </p>
      ) : null}
    </div>
  );
}
