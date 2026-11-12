"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
import {
  completeDailyTask,
  generateTodayTasks,
  getTodayTasks,
  startDailyTask,
  type TodayTasks,
} from "@/lib/learning";
import { MASTERY_STATUS_LABELS } from "@/lib/mastery";
import {
  createPlacementQuiz,
  deleteSelfStudyTask,
  groupTodayTasks,
} from "@/lib/study";
import type { DailyTask, MasteryStatus } from "@/lib/types";

const PROGRESS_LABELS: Record<string, string> = {
  pending: "未开始",
  learning: "学习中",
  completed: "已学完（未验证）",
};

function statusLabel(task: DailyTask): string {
  return (
    task.progress_label ?? PROGRESS_LABELS[task.status] ?? taskStatusLabel(task.status)
  );
}

export default function DashboardClient() {
  const router = useRouter();
  const [data, setData] = useState<TodayTasks | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; status: number } | null>(
    null,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 阶段 6/7：先查询当天是否已有**计划**任务；已有直接读取，不存在才幂等生成。
      // 自选任务不参与这个判断，否则用户自己选一个就会把当天的计划任务挤掉。
      const existing = await getTodayTasks(false);
      const groups = groupTodayTasks(existing);
      if (groups.plan.length > 0) {
        setData(existing);
      } else {
        try {
          setData(await generateTodayTasks());
        } catch (err) {
          const hasOwn =
            groups.selfSelected.length > 0 || groups.carriedOver.length > 0;
          if (!hasOwn) {
            throw err;
          }
          // 无生效计划但已有自选内容：降级展示，不把整个首页打成错误
          setData(existing);
        }
      }
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

  const replaceTask = useCallback((updated: DailyTask) => {
    setData((current) => {
      if (!current) {
        return current;
      }
      const swap = (list?: DailyTask[]) =>
        list?.map((task) => (task.id === updated.id ? updated : task));
      return {
        ...current,
        tasks: current.tasks.map((task) =>
          task.id === updated.id ? updated : task,
        ),
        plan_tasks: swap(current.plan_tasks),
        self_selected_tasks: swap(current.self_selected_tasks),
        carried_over_tasks: swap(current.carried_over_tasks),
      };
    });
  }, []);

  const removeTask = useCallback((taskId: string) => {
    setData((current) => {
      if (!current) {
        return current;
      }
      const drop = (list?: DailyTask[]) =>
        list?.filter((task) => task.id !== taskId);
      return {
        ...current,
        tasks: current.tasks.filter((task) => task.id !== taskId),
        self_selected_tasks: drop(current.self_selected_tasks),
      };
    });
  }, []);

  const run = useCallback(
    async (taskId: string, action: () => Promise<void>) => {
      setBusyId(taskId);
      setActionError(null);
      try {
        await action();
      } catch (err) {
        setActionError(getErrorMessage(err));
      } finally {
        setBusyId(null);
      }
    },
    [],
  );

  const handleStart = (task: DailyTask) =>
    run(task.id, async () => replaceTask(await startDailyTask(task.id)));

  const handleComplete = (task: DailyTask) =>
    run(task.id, async () => replaceTask(await completeDailyTask(task.id)));

  const handleWithdraw = (task: DailyTask) =>
    run(task.id, async () => {
      await deleteSelfStudyTask(task.id);
      removeTask(task.id);
    });

  const handleVerify = (task: DailyTask) =>
    run(task.id, async () => {
      const attempt = await createPlacementQuiz(task.knowledge_point.code);
      router.push(`/quiz?attempt=${encodeURIComponent(attempt.id)}`);
    });

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
          <Link className="btn" href="/learn">
            去课程目录自己挑一个
          </Link>
        }
      />
    );
  }

  const { plan, selfSelected, carriedOver, summary } = groupTodayTasks(data);
  const busy = (task: DailyTask) => busyId === task.id;

  const renderTask = (task: DailyTask, source: "plan" | "self" | "carried") => (
    <li key={task.id} className="task-card card">
      <div className="task-head">
        <span className={`badge badge-${task.status}`}>{statusLabel(task)}</span>
        <span className="muted">
          {source === "self"
            ? "我自己选的"
            : source === "carried"
              ? `继续学习 · 已持续 ${task.carried_over_days ?? 1} 天`
              : `计划第 ${task.day_index} 天`}
        </span>
      </div>
      <h3 className="task-title">{task.knowledge_point.name}</h3>
      <p className="task-chapter">{task.knowledge_point.chapter_title}</p>
      {task.course_refs && (
        <p className="task-chapter">
          教材课时：{task.course_refs.lesson_title}（
          {task.course_refs.lesson_code}）
        </p>
      )}
      <div className="task-meta">
        <span>{difficultyLabel(task.knowledge_point.difficulty)}</span>
        <span>约 {task.knowledge_point.estimated_minutes} 分钟</span>
        <span>
          掌握：
          {MASTERY_STATUS_LABELS[task.mastery_status as MasteryStatus] ??
            task.mastery_status}
          · 证据 {task.mastery_evidence_count} 条
        </span>
      </div>
      <p className="task-goal">{task.knowledge_point.learning_goal}</p>
      <div className="task-actions">
        <Link
          className="btn btn-primary btn-sm"
          href={`/workspace?daily_task_id=${encodeURIComponent(task.id)}`}
        >
          {task.status === "learning" ? "继续学习" : "让 AI 讲解"}
        </Link>
        {task.status === "pending" && (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy(task)}
            onClick={() => void handleStart(task)}
          >
            开始学习
          </button>
        )}
        {task.status === "learning" && (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy(task)}
            onClick={() => void handleComplete(task)}
          >
            标记学完
          </button>
        )}
        {task.status === "completed" && task.mastery_status !== "mastered" && (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy(task)}
            onClick={() => void handleVerify(task)}
          >
            我会了，测一测
          </button>
        )}
        {source === "self" && task.status !== "completed" && (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy(task)}
            onClick={() => void handleWithdraw(task)}
          >
            撤回
          </button>
        )}
      </div>
    </li>
  );

  return (
    <section aria-labelledby="today-tasks-title">
      <div className="section-head">
        <div>
          <h2 id="today-tasks-title" className="section-title">
            今日任务
          </h2>
          <p className="muted">{formatDateOnly(data.task_date)}</p>
        </div>
        <span className="muted">
          共 {data.tasks.length} 个知识点 · 剩余约 {summary.remaining_minutes} 分钟
        </span>
      </div>

      <p className="muted">
        计划 {summary.plan_completed}/{summary.plan_total} · 自选{" "}
        {summary.self_selected_completed}/{summary.self_selected_total} · 学习中{" "}
        {summary.in_progress}
        {summary.carried_over > 0 ? ` · 跨天 ${summary.carried_over}` : ""}
        。「学完」只代表学过了，掌握需要测验验证。
      </p>

      {actionError && <p className="form-error">{actionError}</p>}

      {carriedOver.length > 0 && (
        <>
          <h3 className="subsection-title">继续学习</h3>
          <ul className="task-list">
            {carriedOver.map((task) => renderTask(task, "carried"))}
          </ul>
        </>
      )}

      {plan.length > 0 && (
        <>
          <h3 className="subsection-title">按计划安排</h3>
          <ul className="task-list">
            {plan.map((task) => renderTask(task, "plan"))}
          </ul>
        </>
      )}

      {selfSelected.length > 0 && (
        <>
          <h3 className="subsection-title">我自己选的</h3>
          <ul className="task-list">
            {selfSelected.map((task) => renderTask(task, "self"))}
          </ul>
        </>
      )}

      <p className="muted">
        想换内容或补基础？
        <Link className="link" href="/learn">
          去课程目录自己挑一个知识点
        </Link>
      </p>
    </section>
  );
}
