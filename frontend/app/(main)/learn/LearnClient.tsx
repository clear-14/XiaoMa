"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import { difficultyLabel } from "@/lib/format";
import { listCourses, type CourseSummary } from "@/lib/learning";
import { createPlacementQuiz, createSelfStudyTask, getStudyCandidates } from "@/lib/study";
import type { StudyCandidateKp, StudyCandidates } from "@/lib/types";

const TODAY_TASK_LABELS: Record<string, string> = {
  pending: "今日任务 · 未开始",
  learning: "今日任务 · 学习中",
  completed: "今日任务 · 已学完",
};

export default function LearnClient() {
  const router = useRouter();
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [data, setData] = useState<StudyCandidates | null>(null);
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyCode, setBusyCode] = useState<string | null>(null);
  const detailRequestRef = useRef(0);

  const loadCourses = useCallback(async () => {
    setCoursesLoading(true);
    setCoursesError(null);
    try {
      const list = await listCourses();
      setCourses(list);
      setSelectedCode((current) => current ?? list[0]?.code ?? null);
    } catch (err) {
      setCoursesError(getErrorMessage(err));
    } finally {
      setCoursesLoading(false);
    }
  }, []);

  useEffect(() => {
    // 在定时回调中发起请求，避免在 effect 主体同步触发状态更新
    const timer = window.setTimeout(() => {
      void loadCourses();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadCourses]);

  const loadDetail = useCallback(async (code: string) => {
    const requestId = ++detailRequestRef.current;
    setDetailLoading(true);
    setDetailError(null);
    try {
      const next = await getStudyCandidates(code);
      if (detailRequestRef.current === requestId) {
        setData(next);
      }
    } catch (err) {
      if (detailRequestRef.current === requestId) {
        setData(null);
        setDetailError(getErrorMessage(err));
      }
    } finally {
      if (detailRequestRef.current === requestId) {
        setDetailLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!selectedCode) {
      return;
    }
    const timer = window.setTimeout(() => {
      void loadDetail(selectedCode);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectedCode, loadDetail]);

  /** 加入今日学习：幂等，成功后就地更新该知识点的今日任务状态。 */
  const handleAddToToday = useCallback(
    async (kp: StudyCandidateKp) => {
      setBusyCode(kp.code);
      setActionError(null);
      try {
        const result = await createSelfStudyTask(kp.code);
        setData((current) => {
          if (!current) {
            return current;
          }
          return {
            ...current,
            chapters: current.chapters.map((chapter) => ({
              ...chapter,
              knowledge_points: chapter.knowledge_points.map((item) =>
                item.code === kp.code
                  ? {
                      ...item,
                      today_task_status: result.task.status,
                      today_task_source: result.task.source ?? "self_selected",
                    }
                  : item,
              ),
            })),
          };
        });
      } catch (err) {
        setActionError(getErrorMessage(err));
      } finally {
        setBusyCode(null);
      }
    },
    [],
  );

  /** 我会了，测一测：直接生成 2 题诊断测验，通过后写入掌握证据。 */
  const handleVerify = useCallback(
    async (kp: StudyCandidateKp) => {
      setBusyCode(kp.code);
      setActionError(null);
      try {
        const attempt = await createPlacementQuiz(kp.code);
        router.push(`/quiz?attempt=${encodeURIComponent(attempt.id)}`);
      } catch (err) {
        setActionError(getErrorMessage(err));
      } finally {
        setBusyCode(null);
      }
    },
    [router],
  );

  if (coursesLoading) {
    return <LoadingState label="加载课程…" />;
  }

  if (coursesError) {
    return (
      <ErrorState
        title="无法加载课程"
        message={coursesError}
        action={
          <button type="button" className="btn" onClick={() => void loadCourses()}>
            重试
          </button>
        }
      />
    );
  }

  if (courses.length === 0) {
    return (
      <EmptyState
        title="暂无课程内容"
        description="课程数据尚未初始化，请先在后端执行课程种子命令后刷新页面。"
      />
    );
  }

  return (
    <>
      <div className="course-tabs" role="tablist" aria-label="课程列表">
        {courses.map((course) => (
          <button
            key={course.code}
            type="button"
            role="tab"
            aria-selected={course.code === selectedCode}
            className={`course-tab${
              course.code === selectedCode ? " active" : ""
            }`}
            onClick={() => setSelectedCode(course.code)}
          >
            {course.name}
          </button>
        ))}
      </div>

      {detailLoading && <LoadingState label="加载课程内容…" />}

      {detailError && (
        <ErrorState
          title="无法加载课程内容"
          message={detailError}
          action={
            <button
              type="button"
              className="btn"
              onClick={() => {
                if (selectedCode) {
                  void loadDetail(selectedCode);
                }
              }}
            >
              重试
            </button>
          }
        />
      )}

      {actionError && <p className="form-error">{actionError}</p>}

      {!detailLoading && !detailError && data && (
        <div className="course-detail">
          <section className="course-intro card">
            <h2 className="section-title">{data.course_name}</h2>
            <p className="muted course-description">
              共 {data.progress.chapters.length} 个章节 ·{" "}
              {data.progress.kp_total} 个知识点 · 已学{" "}
              {data.progress.kp_learned} 个 · 已验证掌握{" "}
              {data.progress.kp_mastered} 个
            </p>
            <div className="progress-two-axes">
              <span>
                学习完成 {data.progress.learning_percent}%（
                {data.progress.minutes_learned}/{data.progress.minutes_total} 分钟）
              </span>
              <span>
                已验证掌握 {data.progress.mastery_percent}%（
                {data.progress.kp_mastered}/{data.progress.kp_total} 个知识点）
              </span>
            </div>
            <p className="muted">
              两个数字不是一回事：「学完」只说明花时间学了，掌握要通过测验验证。
            </p>
            {data.notes.map((note) => (
              <p key={note} className="muted">
                {note}
              </p>
            ))}
          </section>

          <div className="chapter-list">
            {data.chapters.map((chapter) => (
              <section key={chapter.code} className="chapter-card card">
                <div className="chapter-head">
                  <h3 className="chapter-title">
                    {chapter.order_index + 1}. {chapter.title}
                  </h3>
                  <span className="muted">
                    学完 {chapter.learning_percent}% · 掌握{" "}
                    {chapter.mastery_percent}%（{chapter.kp_mastered}/
                    {chapter.kp_total}）
                  </span>
                </div>
                <ul className="kp-list">
                  {chapter.knowledge_points.map((kp) => (
                    <li key={kp.code} className="kp-item">
                      <div className="kp-info">
                        <span className="kp-name">
                          {kp.name}
                          <span className={`badge badge-${kp.mastery_status}`}>
                            {kp.mastery_status_label}
                          </span>
                          {kp.today_task_status && (
                            <span className="badge badge-today">
                              {TODAY_TASK_LABELS[kp.today_task_status] ??
                                "今日任务"}
                            </span>
                          )}
                        </span>
                        <span className="kp-meta">
                          {difficultyLabel(kp.difficulty)} · 约{" "}
                          {kp.estimated_minutes} 分钟
                          {kp.unmastered_prerequisite_codes.length > 0
                            ? ` · 建议先学 ${kp.unmastered_prerequisite_codes.length} 个前置知识点`
                            : ""}
                        </span>
                        {kp.block_reason && (
                          <span className="kp-meta">{kp.block_reason}</span>
                        )}
                      </div>
                      <div className="kp-actions">
                        {kp.today_task_status === "pending" ||
                        kp.today_task_status === "learning" ? (
                          <Link
                            className="btn btn-sm btn-primary"
                            href={`/workspace?knowledge_point_code=${encodeURIComponent(
                              kp.code,
                            )}`}
                          >
                            {kp.today_task_status === "learning"
                              ? "继续学习"
                              : "开始学习"}
                          </Link>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-sm"
                            disabled={!kp.can_start || busyCode === kp.code}
                            onClick={() => void handleAddToToday(kp)}
                          >
                            加入今日学习
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={busyCode === kp.code}
                          onClick={() => void handleVerify(kp)}
                        >
                          我会了，测一测
                        </button>
                        <Link
                          className="btn btn-sm"
                          href={`/workspace?knowledge_point_code=${encodeURIComponent(
                            kp.code,
                          )}`}
                        >
                          向 AI 提问
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
