"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import { difficultyLabel, taskStatusLabel } from "@/lib/format";
import { MASTERY_STATUS_LABELS } from "@/lib/mastery";
import type { MasteryStatus } from "@/lib/types";
import type {
  PanelResult,
  WorkspaceSnapshot,
} from "@/lib/workspace-data";

/** 四个面板共用的三态包装：加载 / 错误（可重试） / 空 / 真实内容。 */
export function PanelState<T>({
  result,
  loading,
  onRetry,
  emptyTitle,
  emptyDescription,
  children,
}: {
  result: PanelResult<T>;
  loading: boolean;
  onRetry: () => void;
  emptyTitle: string;
  emptyDescription: string;
  children: (data: T) => ReactNode;
}) {
  if (loading && !result.data) {
    return <div className="panel-loading" role="status">正在读取真实数据…</div>;
  }
  if (result.error) {
    return (
      <ErrorState
        title="数据读取失败"
        message={result.error}
        action={
          <button type="button" className="btn btn-sm" onClick={onRetry}>
            重试
          </button>
        }
      />
    );
  }
  if (!result.data) {
    return (
      <EmptyState title={emptyTitle} description={emptyDescription} />
    );
  }
  return <>{children(result.data)}</>;
}

/** A 当前学习计划：字段全部来自 GET /plans/current。 */
export function PlanPanel({
  snapshot,
  loading,
  onRetry,
}: {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <PanelState
      result={snapshot.plan}
      loading={loading}
      onRetry={onRetry}
      emptyTitle="尚无学习计划"
      emptyDescription="完成首次引导或在「学习计划」中建立计划后，这里会显示真实进度。"
    >
      {(plan) => {
        const version = plan.current_version ?? plan.pending_version;
        const nextItem = version?.items.find((item) => item.status === "pending");
        const completed = version?.items.filter(
          (item) => item.status === "completed",
        ).length ?? 0;
        return (
          <div className="panel-stack">
            <div className="panel-kv">
              <span>当前课程</span>
              <strong>{plan.course_name}</strong>
            </div>
            <div className="panel-kv">
              <span>计划状态</span>
              <strong>{plan.status === "active" ? "已生效" : plan.status}</strong>
            </div>
            <div className="panel-kv">
              <span>生效版本</span>
              <strong>
                {plan.current_version_number ?? "待确认"}
                {plan.pending_version_number !== null
                  ? ` · 待确认 v${plan.pending_version_number}`
                  : ""}
              </strong>
            </div>
            {version && (
              <>
                <div className="panel-kv">
                  <span>每日学习时间</span>
                  <strong>{version.daily_study_minutes} 分钟</strong>
                </div>
                <div className="panel-kv">
                  <span>计划项进度</span>
                  <strong>
                    {completed} / {version.items.length}
                  </strong>
                </div>
                <div className="panel-progress" aria-hidden="true">
                  <span
                    style={{
                      width: `${
                        version.items.length > 0
                          ? Math.round((completed / version.items.length) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </>
            )}
            <div className="panel-note">
              <span className="panel-note-label">当前章节 / 下一步目标</span>
              <p>{nextItem?.knowledge_point_name ?? "计划项已全部完成"}</p>
            </div>
            <Link className="btn btn-sm" href="/plan">
              查看完整计划
            </Link>
          </div>
        );
      }}
    </PanelState>
  );
}

/** B 今日学习任务：GET /daily-tasks/today?generate=false，无任务才幂等生成。 */
export function TodayPanel({
  snapshot,
  loading,
  onRetry,
}: {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <PanelState
      result={snapshot.today}
      loading={loading}
      onRetry={onRetry}
      emptyTitle="今日暂无学习任务"
      emptyDescription="确认学习计划已生效后，任务会由后端按计划生成。"
    >
      {(today) => (
        <div className="panel-stack">
          {today.tasks.length === 0 ? (
            <EmptyState
              title="今天没有待学任务"
              description={today.note ?? "当前没有需要生成的学习任务。"}
            />
          ) : (
            <ul className="panel-tasks">
              {today.tasks.map((task) => (
                <li key={task.id} className="panel-task">
                  <div className="panel-task-head">
                    <span className={`badge badge-${task.status}`}>
                      {taskStatusLabel(task.status)}
                    </span>
                    <span className="panel-muted">计划第 {task.day_index} 天</span>
                  </div>
                  <h3 className="panel-task-title">
                    {task.knowledge_point.name}
                  </h3>
                  <p className="panel-muted">
                    {task.knowledge_point.chapter_title} ·{" "}
                    {difficultyLabel(task.knowledge_point.difficulty)} · 约{" "}
                    {task.knowledge_point.estimated_minutes} 分钟
                  </p>
                  <p className="panel-task-goal">
                    {task.knowledge_point.learning_goal}
                  </p>
                  <p className="panel-muted">
                    掌握状态：
                    {MASTERY_STATUS_LABELS[task.mastery_status as MasteryStatus] ??
                      task.mastery_status}{" "}
                    · 证据 {task.mastery_evidence_count} 条
                  </p>
                  <Link
                    className="btn btn-primary btn-sm"
                    href={`/workspace?daily_task_id=${encodeURIComponent(task.id)}`}
                  >
                    开始学习
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </PanelState>
  );
}

/** C 当前知识点：来自今日任务关联知识点的真实详情接口。 */
export function KnowledgePanel({
  snapshot,
  loading,
  onRetry,
}: {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <PanelState
      result={snapshot.knowledgePoint}
      loading={loading}
      onRetry={onRetry}
      emptyTitle="暂无当前知识点"
      emptyDescription="今日任务确定后，这里会显示该任务关联知识点的真实详情。"
    >
      {(point) => {
        const review = snapshot.mastery.data?.needs_review.find(
          (item) => item.knowledge_point_code === point.code,
        );
        return (
          <div className="panel-stack">
            <div className="panel-kv">
              <span>知识点</span>
              <strong>{point.name}</strong>
            </div>
            <div className="panel-kv">
              <span>所属章节</span>
              <strong>{point.chapter.title}</strong>
            </div>
            <div className="panel-kv">
              <span>难度 / 时长</span>
              <strong>
                {difficultyLabel(point.difficulty)} · {point.estimated_minutes} 分钟
              </strong>
            </div>
            <div className="panel-note">
              <span className="panel-note-label">学习目标</span>
              <p>{point.learning_goal}</p>
            </div>
            <div className="panel-note">
              <span className="panel-note-label">前置知识点</span>
              <p>
                {point.prerequisites.length > 0
                  ? point.prerequisites.map((item) => item.name).join("、")
                  : "无"}
              </p>
            </div>
            <div className="panel-kv">
              <span>掌握状态</span>
              <strong>
                {review
                  ? MASTERY_STATUS_LABELS[review.status]
                  : "以后端掌握度记录为准"}
              </strong>
            </div>
            {point.resources && point.resources.length > 0 && (
              <div className="panel-note">
                <span className="panel-note-label">学习资源</span>
                <ul className="panel-resources">
                  {point.resources.map((resource, index) => (
                    <li key={`${resource.title}-${index}`}>{resource.title}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      }}
    </PanelState>
  );
}

/** D 学习进度：GET /overview 与 GET /mastery 的真实计数，前端不计算掌握状态。 */
export function ProgressPanel({
  snapshot,
  loading,
  onRetry,
}: {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
  onRetry: () => void;
}) {
  return (
    <PanelState
      result={snapshot.overview}
      loading={loading}
      onRetry={onRetry}
      emptyTitle="暂无学习进度数据"
      emptyDescription="建立学习计划并开始学习后，这里会显示服务端的真实统计。"
    >
      {(overview) => (
        <div className="panel-stack">
          <div className="panel-stats">
            <div>
              <span className="panel-stat-value">{overview.mastered_count}</span>
              <span className="panel-muted">已掌握</span>
            </div>
            <div>
              <span className="panel-stat-value">{overview.learning_count}</span>
              <span className="panel-muted">学习中</span>
            </div>
            <div>
              <span className="panel-stat-value">
                {overview.pending_verification_count}
              </span>
              <span className="panel-muted">待验证</span>
            </div>
          </div>
          <div className="panel-kv">
            <span>最近测验得分</span>
            <strong>
              {overview.latest_quiz_score === null
                ? "暂无记录"
                : `${overview.latest_quiz_score} 分`}
            </strong>
          </div>
          <div className="panel-kv">
            <span>计划进度</span>
            <strong>{overview.plan_progress_percent}%</strong>
          </div>
          <div className="panel-kv">
            <span>错题 / 待复习</span>
            <strong>
              {overview.mistake_pending_count} / {overview.review_due_count}
            </strong>
          </div>
          <div className="panel-note">
            <span className="panel-note-label">当前薄弱知识点</span>
            {snapshot.mastery.data?.needs_review.length ? (
              <ul className="panel-resources">
                {snapshot.mastery.data.needs_review.slice(0, 5).map((item) => (
                  <li key={item.knowledge_point_code}>
                    {item.knowledge_point_name}
                  </li>
                ))}
              </ul>
            ) : (
              <p>后端暂无需要复习的知识点记录</p>
            )}
          </div>
        </div>
      )}
    </PanelState>
  );
}
