"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import { difficultyLabel } from "@/lib/format";
import {
  getCourseDetail,
  listCourses,
  type CourseDetail,
  type CourseSummary,
} from "@/lib/learning";

export default function LearnClient() {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
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
      const data = await getCourseDetail(code);
      if (detailRequestRef.current === requestId) {
        setDetail(data);
      }
    } catch (err) {
      if (detailRequestRef.current === requestId) {
        setDetail(null);
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

  if (coursesLoading) {
    return <LoadingState label="加载课程…" />;
  }

  if (coursesError) {
    return (
      <ErrorState
        title="无法加载课程"
        message={coursesError}
        action={
          <button
            type="button"
            className="btn"
            onClick={() => void loadCourses()}
          >
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

      {!detailLoading && !detailError && detail && (
        <div className="course-detail">
          <section className="course-intro card">
            <h2 className="section-title">{detail.name}</h2>
            {detail.description && (
              <p className="muted course-description">{detail.description}</p>
            )}
            <p className="muted">
              共 {detail.chapter_count} 个章节 · 点击知识点右侧按钮可围绕该知识点向
              AI 提问
            </p>
          </section>

          <div className="chapter-list">
            {detail.chapters.map((chapter) => (
              <section key={chapter.id} className="chapter-card card">
                <h3 className="chapter-title">
                  {chapter.order_index + 1}. {chapter.title}
                </h3>
                {chapter.description && (
                  <p className="muted chapter-desc">{chapter.description}</p>
                )}
                <ul className="kp-list">
                  {chapter.knowledge_points.map((kp) => (
                    <li key={kp.id} className="kp-item">
                      <div className="kp-info">
                        <span className="kp-name">{kp.name}</span>
                        <span className="kp-meta">
                          {difficultyLabel(kp.difficulty)} · 约{" "}
                          {kp.estimated_minutes} 分钟
                        </span>
                      </div>
                      <Link
                        className="btn btn-sm"
                        href={`/workspace?knowledge_point_code=${encodeURIComponent(
                          kp.code,
                        )}`}
                      >
                        向 AI 提问
                      </Link>
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
