"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import AnswerInput from "@/components/quiz/AnswerInput";
import QuestionResult from "@/components/quiz/QuestionResult";
import { getErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  createQuiz,
  getQuizAttempt,
  isAnswerEmpty,
  listQuizAttempts,
  getQuizEligibility,
  questionTypeLabel,
  quizStatusLabel,
  scopeTypeLabel,
  submitQuiz,
  type QuizAttempt,
  type QuizAttemptSummary,
  type QuizEligibility,
  type QuizScopeType,
} from "@/lib/quiz";

const SCOPE_TABS: { value: QuizScopeType; label: string; hint: string }[] = [
  { value: "knowledge_point", label: "知识点测验", hint: "针对一个已学习知识点" },
  { value: "chapter", label: "章节测验", hint: "该章节内已学习知识点" },
  { value: "stage", label: "阶段综合", hint: "当前学习计划内已学习内容" },
];

export default function QuizClient() {
  const [eligibility, setEligibility] = useState<QuizEligibility | null>(null);
  const [history, setHistory] = useState<QuizAttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [scopeType, setScopeType] = useState<QuizScopeType>("knowledge_point");
  const [selectedKp, setSelectedKp] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [aiCount, setAiCount] = useState(0);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const quizRef = useRef<HTMLDivElement | null>(null);

  const loadOverview = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
    }
    setLoadError(null);
    try {
      const [elig, attempts] = await Promise.all([
        getQuizEligibility(),
        listQuizAttempts(),
      ]);
      setEligibility(elig);
      setHistory(attempts);
      setSelectedKp((current) =>
        current ||
        elig.learned_knowledge_points.find((item) => item.quiz_available)?.code ||
        elig.learned_knowledge_points[0]?.code ||
        "",
      );
      setSelectedChapter((current) =>
        current ||
        elig.chapters.find((item) => item.quiz_available)?.code ||
        elig.chapters[0]?.code ||
        "",
      );
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
      void loadOverview();
      // 阶段 5：从「能力诊断」页生成诊断测验后带 ?attempt=<id> 跳转，
      // 自动打开该测验，避免用户再回到历史列表里翻找。
      const attemptId = new URLSearchParams(window.location.search).get(
        "attempt",
      );
      if (attemptId) {
        void getQuizAttempt(attemptId)
          .then((data) => {
            setAttempt(data);
            setAnswers({});
            window.setTimeout(() => {
              quizRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
            }, 0);
          })
          .catch((err) => setCreateError(getErrorMessage(err)));
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadOverview]);

  const startQuiz = async () => {
    setCreating(true);
    setCreateError(null);
    setSubmitError(null);
    try {
      const payload = {
        scope_type: scopeType,
        ai_variant_count: aiCount,
        ...(scopeType === "knowledge_point"
          ? { knowledge_point_code: selectedKp }
          : {}),
        ...(scopeType === "chapter" ? { chapter_code: selectedChapter } : {}),
      };
      const data = await createQuiz(payload);
      setAttempt(data);
      setAnswers({});
      window.setTimeout(() => {
        quizRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 0);
    } catch (err) {
      setCreateError(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const openAttempt = async (attemptId: string) => {
    setOpeningId(attemptId);
    setCreateError(null);
    setSubmitError(null);
    try {
      const data = await getQuizAttempt(attemptId);
      setAttempt(data);
      setAnswers({});
      window.setTimeout(() => {
        quizRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 0);
    } catch (err) {
      setCreateError(getErrorMessage(err));
    } finally {
      setOpeningId(null);
    }
  };

  const closeAttempt = () => {
    setAttempt(null);
    setAnswers({});
    setSubmitError(null);
    void loadOverview(false);
  };

  const updateAnswer = (questionId: string, value: unknown) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  };

  const submit = async () => {
    if (!attempt) {
      return;
    }
    const missing = attempt.questions.filter((question) =>
      isAnswerEmpty(question, answers[question.id]),
    );
    if (missing.length > 0) {
      setSubmitError(`还有 ${missing.length} 道题未作答，请完成全部题目后再提交`);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await submitQuiz(
        attempt.id,
        attempt.questions.map((question) => ({
          question_id: question.id,
          answer: answers[question.id],
        })),
      );
      setAttempt(result);
      void loadOverview(false);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingState label="加载测验范围与记录…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载测验中心"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void loadOverview()}>
            重试
          </button>
        }
      />
    );
  }

  if (attempt) {
    return (
      <div ref={quizRef} className="quiz-detail">
        <div className="section-head">
          <div>
            <h2 className="section-title">{attempt.scope_name}</h2>
            <p className="muted">
              {scopeTypeLabel(attempt.scope_type)} · {attempt.question_count} 题 ·{" "}
              {quizStatusLabel(attempt.status)} · 开始于{" "}
              {formatDateTime(attempt.started_at)}
            </p>
          </div>
          <button type="button" className="btn" onClick={closeAttempt}>
            返回测验中心
          </button>
        </div>

        {attempt.ai_requested > 0 && attempt.ai_note && (
          <div
            className={`notice ${
              attempt.ai_accepted > 0 ? "notice-success" : "notice-warning"
            }`}
          >
            {attempt.ai_note}
          </div>
        )}

        {attempt.status === "submitted" ? (
          <>
            <section className="result-summary card">
              <div>
                <p className="muted">百分制得分</p>
                <p className="score-value">
                  {attempt.score ?? 0}
                  <span className="score-unit">分</span>
                </p>
              </div>
              <div className="result-summary-meta">
                <p>
                  共 {attempt.question_count} 题 · 总分 {attempt.total_points} 分
                </p>
                {attempt.submitted_at && (
                  <p className="muted">提交于 {formatDateTime(attempt.submitted_at)}</p>
                )}
                {attempt.ai_accepted > 0 && (
                  <p className="muted">
                    本次使用 {attempt.ai_accepted} 道通过验证的 AI 变式题
                  </p>
                )}
              </div>
            </section>

            <section className="mastery-section">
              <h3 className="section-title">掌握状态判定</h3>
              {attempt.mastery_updates.length > 0 ? (
                attempt.mastery_updates.map((update) => (
                  <div
                    key={update.knowledge_point_code}
                    className={`card mastery-card ${
                      update.achieved ? "mastery-achieved" : "mastery-pending"
                    }`}
                  >
                    <div className="tag-row">
                      <strong>{update.knowledge_point_name}</strong>
                      <span
                        className={`badge ${
                          update.achieved ? "badge-completed" : "badge-learning"
                        }`}
                      >
                        {update.achieved ? "已标记为掌握" : "未标记为掌握"}
                      </span>
                    </div>
                    <ul className="reason-list">
                      {update.reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                ))
              ) : (
                <p className="muted">
                  {attempt.scope_type === "review"
                    ? "错题复习记录本次答题与复习进度，不直接改变知识点掌握状态。"
                    : "章节测验与阶段测验只记录成绩，不直接改变知识点掌握状态；掌握状态只能由知识点测验按后端规则更新。"}
                </p>
              )}
            </section>

            <section className="result-questions">
              <h3 className="section-title">答题结果与解析</h3>
              {attempt.questions.map((question) => (
                <QuestionResult key={question.id} question={question} />
              ))}
            </section>
          </>
        ) : (
          <>
            <div className="notice">
              提交后将显示正确答案、解析与评分依据。小码不会执行你提交的代码。
            </div>
            <section className="quiz-questions">
              {attempt.questions.map((question) => (
                <article key={question.id} className="card question-card">
                  <div className="question-head">
                    <div className="tag-row">
                      <span className="badge badge-pending">
                        第 {question.order} 题 ·{" "}
                        {questionTypeLabel(question.question_type)}
                      </span>
                      <span className="badge">
                        {question.source === "ai" ? "AI 变式题（已验证）" : "内置题库"}
                      </span>
                    </div>
                    <span className="muted">
                      {question.knowledge_point.chapter_title} ·{" "}
                      {question.knowledge_point.name}
                    </span>
                  </div>
                  <p className="question-stem">{question.stem}</p>
                  <AnswerInput
                    question={question}
                    value={answers[question.id]}
                    disabled={submitting}
                    onChange={(value) => updateAnswer(question.id, value)}
                  />
                </article>
              ))}
            </section>
            {submitError && <div className="inline-error">{submitError}</div>}
            <div className="quiz-submit-row">
              <button
                type="button"
                className="btn btn-primary"
                disabled={submitting}
                onClick={() => void submit()}
              >
                {submitting ? "正在评分…" : "提交测验"}
              </button>
              <span className="muted">
                已作答{" "}
                {attempt.questions.filter(
                  (question) => !isAnswerEmpty(question, answers[question.id]),
                ).length}
                /{attempt.question_count} 题
              </span>
            </div>
          </>
        )}
      </div>
    );
  }

  const hasAnyScope =
    eligibility !== null &&
    (eligibility.learned_knowledge_points.length > 0 ||
      eligibility.chapters.length > 0 ||
      eligibility.stage.available);
  const selectedKpItem = eligibility?.learned_knowledge_points.find(
    (item) => item.code === selectedKp,
  );
  const selectedChapterItem = eligibility?.chapters.find(
    (item) => item.code === selectedChapter,
  );
  const canStart =
    !creating &&
    (scopeType === "knowledge_point"
      ? Boolean(selectedKpItem?.quiz_available)
      : scopeType === "chapter"
        ? Boolean(selectedChapterItem?.quiz_available)
        : Boolean(eligibility?.stage.available));

  return (
    <div className="quiz-setup">
      <section className="card setup-card">
        <div className="section-head">
          <div>
            <h2 className="section-title">开始一次测验</h2>
            <p className="muted">
              正式测验只包含已学习知识点；未学习内容不会进入测验范围。
            </p>
          </div>
        </div>

        {!hasAnyScope ? (
          <EmptyState
            title="暂无可测验的知识点"
            description="请先在「课程学习」中开始学习，或在首页完成每日任务、到 AI 学习工作台学习知识点。完成学习后，这里会出现对应测验范围。"
          />
        ) : (
          <>
            <div className="scope-tabs" role="tablist" aria-label="测验范围">
              {SCOPE_TABS.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  role="tab"
                  aria-selected={scopeType === tab.value}
                  className={`course-tab${scopeType === tab.value ? " active" : ""}`}
                  onClick={() => setScopeType(tab.value)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <p className="muted">
              {SCOPE_TABS.find((tab) => tab.value === scopeType)?.hint}
            </p>

            {scopeType === "knowledge_point" && (
              <div className="form-group scope-field">
                <label className="form-label" htmlFor="quiz-kp">
                  选择已学习知识点
                </label>
                {eligibility.learned_knowledge_points.length === 0 ? (
                  <p className="form-hint">还没有已学习的知识点。</p>
                ) : (
                  <select
                    id="quiz-kp"
                    className="form-select"
                    value={selectedKp}
                    onChange={(event) => setSelectedKp(event.target.value)}
                  >
                    {eligibility.learned_knowledge_points.map((item) => (
                      <option
                        key={item.code}
                        value={item.code}
                        disabled={!item.quiz_available}
                      >
                        {item.name} · {item.chapter_title} ·{" "}
                        {item.question_count} 题
                        {item.quiz_available ? "" : "（暂无可用题目）"}
                      </option>
                    ))}
                  </select>
                )}
                {selectedKpItem && (
                  <p className="form-hint">
                    当前状态：{quizStatusLabel(selectedKpItem.status)} · 可用题目{" "}
                    {selectedKpItem.question_count} 道
                    {selectedKpItem.question_count < 3
                      ? " · 少于 3 道题时无法完成掌握验证"
                      : ""}
                  </p>
                )}
              </div>
            )}

            {scopeType === "chapter" && (
              <div className="form-group scope-field">
                <label className="form-label" htmlFor="quiz-chapter">
                  选择章节
                </label>
                {eligibility.chapters.length === 0 ? (
                  <p className="form-hint">当前还没有包含已学习知识点的章节。</p>
                ) : (
                  <select
                    id="quiz-chapter"
                    className="form-select"
                    value={selectedChapter}
                    onChange={(event) => setSelectedChapter(event.target.value)}
                  >
                    {eligibility.chapters.map((item) => (
                      <option
                        key={item.code}
                        value={item.code}
                        disabled={!item.quiz_available}
                      >
                        {item.title} · 已学习{" "}
                        {item.learned_knowledge_point_count} 个知识点 ·{" "}
                        {item.question_count} 题
                      </option>
                    ))}
                  </select>
                )}
                <p className="form-hint">
                  章节测验只使用该章节内已学习知识点，组卷目标 10 题（受题库数量限制）。
                </p>
              </div>
            )}

            {scopeType === "stage" && (
              <div className="form-group scope-field">
                <div className="stage-summary">
                  <span className="form-label">当前学习阶段</span>
                  {eligibility.stage.available ? (
                    <p>
                      {eligibility.stage.course_name} · 已学习{" "}
                      {eligibility.stage.learned_knowledge_point_count} 个知识点 ·{" "}
                      {eligibility.stage.question_count} 道可用题目
                    </p>
                  ) : (
                    <p className="form-hint">{eligibility.stage.note}</p>
                  )}
                </div>
              </div>
            )}

            <div className="form-group scope-field">
              <label className="form-label" htmlFor="quiz-ai-count">
                AI 变式题
              </label>
              <select
                id="quiz-ai-count"
                className="form-select"
                value={aiCount}
                onChange={(event) => setAiCount(Number(event.target.value))}
              >
                <option value={0}>仅使用内置题库</option>
                {[1, 2, 3, 4, 5].map((count) => (
                  <option key={count} value={count}>
                    请求 {count} 道 AI 变式题
                  </option>
                ))}
              </select>
              <p className="form-hint">
                每道 AI 变式题都会经过结构校验与独立复核调用（默认模型二次作答）；未通过验证的
                题目不会进入测验，失败时自动使用内置题库。
              </p>
            </div>

            {createError && <div className="inline-error">{createError}</div>}
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canStart}
              onClick={() => void startQuiz()}
            >
              {creating ? "正在组卷…（AI 变式题可能需要较长时间）" : "开始测验"}
            </button>
          </>
        )}
      </section>

      <section className="quiz-history">
        <div className="section-head">
          <h2 className="section-title">测验记录</h2>
          <span className="muted">保留每次答题与评分结果</span>
        </div>
        {history.length === 0 ? (
          <p className="muted">还没有测验记录。</p>
        ) : (
          <ul className="history-list">
            {history.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="card history-item history-button"
                  disabled={openingId === item.id}
                  onClick={() => void openAttempt(item.id)}
                >
                  <span className="history-main">
                    <span className="history-title">{item.scope_name}</span>
                    <span className="history-meta">
                      {scopeTypeLabel(item.scope_type)} · {item.question_count} 题
                      {item.purpose === "placement" ? " · 诊断测验（跳级验证）" : ""}
                      {item.ai_accepted > 0
                        ? ` · ${item.ai_accepted} 道 AI 变式题`
                        : ""}
                    </span>
                    <span className="history-time">
                      {formatDateTime(item.started_at)}
                    </span>
                  </span>
                  <span className="history-actions">
                    <span
                      className={`badge ${
                        item.status === "submitted"
                          ? "badge-completed"
                          : "badge-learning"
                      }`}
                    >
                      {item.status === "submitted"
                        ? `${item.score ?? 0} 分`
                        : quizStatusLabel(item.status)}
                    </span>
                    <span className="btn btn-sm">
                      {openingId === item.id ? "载入中…" : "查看"}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
