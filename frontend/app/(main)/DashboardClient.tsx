"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { ApiError, getErrorMessage } from "@/lib/api";
import {
  difficultyLabel,
  formatDateOnly,
  taskStatusLabel,
} from "@/lib/format";
import { getTodayTasks, type TodayTasks } from "@/lib/learning";

export default function DashboardClient() {
  const [data, setData] = useState<TodayTasks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; status: number } | null>(
    null,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getTodayTasks());
    } catch (err) {
      setError({
        message: getErrorMessage(err),
        status: err instanceof ApiError ? err.status : 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 在定时回调中发起请求，避免在 effect 主体同步触发状态更新
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (loading) {
    return <LoadingState label="加载今日任务…" />;
  }

  if (error) {
    if (error.status === 404) {
      return (
        <EmptyState
          title="暂无学习计划"
          description={error.message}
          action={
            <Link className="btn btn-primary" href="/plan">
              查看学习计划
            </Link>
          }
        />
      );
    }
    if (error.status === 409) {
      return (
        <ErrorState
          title="学习计划尚未确认"
          message={error.message}
          action={
            <Link className="btn" href="/plan">
              前往学习计划
            </Link>
          }
        />
      );
    }
    return (
      <ErrorState
        title="无法加载今日任务"
        message={error.message}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  if (!data || data.tasks.length === 0) {
    return (
      <EmptyState
        title="今日没有待学任务"
        description={data?.note ?? "当前没有需要生成的学习任务。"}
        action={
          <Link className="btn" href="/workspace">
            去和 AI 聊聊
          </Link>
        }
      />
    );
  }

  return (
    <section aria-labelledby="today-tasks-title">
      <div className="section-head">
        <div>
          <h2 id="today-tasks-title" className="section-title">
            今日任务
          </h2>
          <p className="muted">{formatDateOnly(data.task_date)}</p>
        </div>
        <span className="muted">共 {data.tasks.length} 个知识点</span>
      </div>

      <ul className="task-list">
        {data.tasks.map((task) => (
          <li key={task.id} className="task-card card">
            <div className="task-head">
              <span className={`badge badge-${task.status}`}>
                {taskStatusLabel(task.status)}
              </span>
              <span className="muted">计划第 {task.day_index} 天</span>
            </div>
            <h3 className="task-title">{task.knowledge_point.name}</h3>
            <p className="task-chapter">{task.knowledge_point.chapter_title}</p>
            <div className="task-meta">
              <span>{difficultyLabel(task.knowledge_point.difficulty)}</span>
              <span>约 {task.knowledge_point.estimated_minutes} 分钟</span>
            </div>
            <p className="task-goal">{task.knowledge_point.learning_goal}</p>
            <div className="task-actions">
              <Link
                className="btn btn-primary btn-sm"
                href={`/workspace?daily_task_id=${encodeURIComponent(task.id)}`}
              >
                让 AI 讲解
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
