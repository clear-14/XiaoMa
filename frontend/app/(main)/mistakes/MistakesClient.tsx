"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import AnswerInput from "@/components/quiz/AnswerInput";
import QuestionResult from "@/components/quiz/QuestionResult";
import { getErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  correctAnswerValue,
  formatAnswer,
  isAnswerEmpty,
  listMistakes,
  listReviewTasks,
  questionTypeLabel,
  submitReview,
  type Mistake,
  type ReviewResult,
  type ReviewTask,
} from "@/lib/quiz";

type MistakeFilter = "pending" | "resolved" | "all";

const FILTERS: { value: MistakeFilter; label: string }[] = [
  { value: "pending", label: "待复习" },
  { value: "resolved", label: "已解决" },
  { value: "all", label: "全部" },
];

export default function MistakesClient() {
  const [mistakes, setMistakes] = useState<Mistake[]>([]);
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [filter, setFilter] = useState<MistakeFilter>("pending");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activeTask, setActiveTask] = useState<ReviewTask | null>(null);
  const [answer, setAnswer] = useState<unknown>(undefined);
  const [submitting, setSubmitting] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const reviewRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
    }
    setLoadError(null);
    try {
      const [mistakeList, taskList] = await Promise.all([
        listMistakes(),
        listReviewTasks(),
      ]);
      setMistakes(mistakeList);
      setTasks(taskList);
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const counts = useMemo(
    () => ({
      pending: mistakes.filter((item) => item.review_status === "pending").length,
      resolved: mistakes.filter((item) => item.review_status === "resolved").length,
      all: mistakes.length,
    }),
    [mistakes],
  );

  const visibleMistakes = useMemo(
    () =>
      filter === "all"
        ? mistakes
        : mistakes.filter((item) => item.review_status === filter),
    [mistakes, filter],
  );

  const dueTaskCount = tasks.filter((task) => task.is_due).length;
  const taskById = useMemo(
    () => new Map(tasks.map((task) => [task.id, task])),
    [tasks],
  );

  const startReview = (task: ReviewTask) => {
    setActiveTask(task);
    setAnswer(undefined);
    setReviewError(null);
    setReviewResult(null);
    window.setTimeout(() => {
      reviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  const startReviewForMistake = (mistake: Mistake) => {
    if (!mistake.pending_review_task_id) {
      return;
    }
    const task = taskById.get(mistake.pending_review_task_id);
    if (task) {
      startReview(task);
    }
  };

  const closeReview = () => {
    setActiveTask(null);
    setAnswer(undefined);
    setReviewError(null);
    setReviewResult(null);
  };

  const submit = async () => {
    if (!activeTask) {
      return;
    }
    if (isAnswerEmpty(activeTask.question, answer)) {
      setReviewError("请先作答再提交复习");
      return;
    }
    setSubmitting(true);
    setReviewError(null);
    try {
      const result = await submitReview(activeTask.id, answer);
      setReviewResult(result);
      setAnswer(undefined);
      setActiveTask(null);
      void load(false);
    } catch (err) {
      setReviewError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingState label="加载错题与复习任务…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载错题本"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  return (
    <div className="mistakes-layout">
      {reviewResult && (
        <section ref={reviewRef} className="card review-result-card">
          <div className="section-head">
            <div>
              <h2 className="section-title">复习结果</h2>
              <p className="muted">{reviewResult.message}</p>
            </div>
            <button type="button" className="btn" onClick={closeReview}>
              完成
            </button>
          </div>
          <div className="review-progress-note">
            <span
              className={`badge ${
                reviewResult.mistake.review_status === "resolved"
                  ? "badge-completed"
                  : "badge-learning"
              }`}
            >
              {reviewResult.mistake.review_status === "resolved"
                ? "已解决"
                : "继续复习"}
            </span>
            {reviewResult.next_review_task ? (
              <span className="muted">
                下次复习：{formatDateTime(reviewResult.next_review_task.due_at)}
                （间隔 {reviewResult.next_review_task.interval_days} 天）
              </span>
            ) : (
              <span className="muted">
                该错题已完成全部复习间隔，知识点标记为已解决。
              </span>
            )}
          </div>
          <QuestionResult question={reviewResult.question} />
        </section>
      )}

      {activeTask && (
        <section ref={reviewRef} className="card review-panel">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                复习：{activeTask.knowledge_point.name}
              </h2>
              <p className="muted">
                {activeTask.knowledge_point.chapter_title} ·{" "}
                {questionTypeLabel(activeTask.question.question_type)} · 计划间隔{" "}
                {activeTask.interval_days} 天
              </p>
            </div>
            <button type="button" className="btn" onClick={closeReview}>
              取消
            </button>
          </div>
          {!activeTask.is_due && (
            <div className="notice notice-warning">
              该任务还未到计划复习时间；可以提前复习，答对同样会推进复习间隔。
            </div>
          )}
          <p className="question-stem">{activeTask.question.stem}</p>
          <AnswerInput
            question={activeTask.question}
            value={answer}
            disabled={submitting}
            onChange={setAnswer}
          />
          {reviewError && <div className="inline-error">{reviewError}</div>}
          <div className="quiz-submit-row">
            <button
              type="button"
              className="btn btn-primary"
              disabled={submitting}
              onClick={() => void submit()}
            >
              {submitting ? "正在评分…" : "提交复习答案"}
            </button>
            <span className="muted">
              回答后会立即评分，并更新下次复习时间。
            </span>
          </div>
        </section>
      )}

      <section className="review-queue">
        <div className="section-head">
          <div>
            <h2 className="section-title">复习任务</h2>
            <p className="muted">
              按 1、3、7、14 天间隔安排；答错会重置复习进度。
            </p>
          </div>
          <span className="badge badge-learning">
            {dueTaskCount} 个已到期 · 共 {tasks.length} 个待复习
          </span>
        </div>
        {tasks.length === 0 ? (
          <EmptyState
            title="暂无待复习任务"
            description="测验中答错的题目会自动生成复习任务。全部复习完成并通过后，错题会标记为已解决。"
          />
        ) : (
          <ul className="review-task-list">
            {tasks.map((task) => (
              <li key={task.id}>
                <article className="card review-task-card">
                  <div className="review-task-main">
                    <div className="tag-row">
                      <span
                        className={`badge ${
                          task.is_due ? "badge-learning" : "badge-pending"
                        }`}
                      >
                        {task.is_due ? "已到期" : "未到期"}
                      </span>
                      <span className="badge">
                        {questionTypeLabel(task.question.question_type)}
                      </span>
                    </div>
                    <p className="review-task-kp">
                      {task.knowledge_point.chapter_title} ·{" "}
                      {task.knowledge_point.name}
                    </p>
                    <p className="review-task-stem">{task.question.stem}</p>
                    <p className="muted">
                      计划复习：{formatDateTime(task.due_at)} · 间隔{" "}
                      {task.interval_days} 天
                      {task.last_result
                        ? ` · 上次复习${task.last_result === "correct" ? "答对" : "答错"}`
                        : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => startReview(task)}
                  >
                    {task.is_due ? "开始复习" : "提前复习"}
                  </button>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mistake-section">
        <div className="section-head">
          <h2 className="section-title">错题记录</h2>
          <div className="scope-tabs" role="tablist" aria-label="错题筛选">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                role="tab"
                aria-selected={filter === item.value}
                className={`course-tab${filter === item.value ? " active" : ""}`}
                onClick={() => setFilter(item.value)}
              >
                {item.label}（{counts[item.value]}）
              </button>
            ))}
          </div>
        </div>

        {visibleMistakes.length === 0 ? (
          <EmptyState
            title={filter === "pending" ? "暂无待复习错题" : "暂无错题记录"}
            description="测验中答错的题目会自动收录到这里，并保留你的答案、正确答案、解析与评分依据。"
          />
        ) : (
          <ul className="mistake-list">
            {visibleMistakes.map((mistake) => (
              <li key={mistake.id}>
                <article className="card mistake-card">
                  <div className="question-head">
                    <div className="tag-row">
                      <span className="badge">
                        {questionTypeLabel(mistake.question.question_type)}
                      </span>
                      <span
                        className={`badge ${
                          mistake.review_status === "resolved"
                            ? "badge-completed"
                            : "badge-learning"
                        }`}
                      >
                        {mistake.review_status === "resolved" ? "已解决" : "待复习"}
                      </span>
                      <span className="muted">
                        {mistake.knowledge_point.chapter_title} ·{" "}
                        {mistake.knowledge_point.name}
                      </span>
                    </div>
                    <span className="muted">
                      答错 {mistake.attempt_count} 次 · 最近{" "}
                      {formatDateTime(mistake.last_wrong_at)}
                    </span>
                  </div>

                  <p className="question-stem">{mistake.question.stem}</p>
                  <dl className="answer-summary">
                    <div>
                      <dt>你的上次答案</dt>
                      <dd>{formatAnswer(mistake.question, mistake.last_answer)}</dd>
                    </div>
                    <div>
                      <dt>正确答案</dt>
                      <dd>
                        {formatAnswer(
                          mistake.question,
                          correctAnswerValue(mistake.question),
                        )}
                      </dd>
                    </div>
                  </dl>

                  {mistake.question.explanation && (
                    <div className="explanation-block">
                      <h4>解析</h4>
                      <p>{mistake.question.explanation}</p>
                    </div>
                  )}

                  <div className="mistake-footer">
                    <span className="muted">
                      已通过复习 {mistake.review_stage} 次
                      {mistake.next_review_at
                        ? ` · 下次复习 ${formatDateTime(mistake.next_review_at)}`
                        : mistake.review_status === "resolved"
                          ? " · 已完成全部复习"
                          : ""}
                    </span>
                    {mistake.review_status === "pending" &&
                      mistake.pending_review_task_id && (
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => startReviewForMistake(mistake)}
                        >
                          进入复习
                        </button>
                      )}
                  </div>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
