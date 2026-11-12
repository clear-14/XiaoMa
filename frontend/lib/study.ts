/** 自主选题与学习进度 API 封装（阶段 7）。
 *
 * 与 `lib/learning.ts` 分开的原因：今日任务的读接口保持不变，
 * 这里只放阶段 7 新增的写接口与聚合读接口，避免影响既有页面测试的 mock。
 */

import { api } from "@/lib/api";
import type {
  CourseProgress,
  DailyTask,
  SelfStudyResult,
  StudyCandidates,
  TodayTasks,
  TodayTasksSummary,
} from "@/lib/types";

export type {
  CourseProgress,
  SelfStudyResult,
  StudyCandidates,
} from "@/lib/types";

/** 加入今日学习：知识点级自选，后端幂等（当天已有则 created=false）。 */
export function createSelfStudyTask(
  knowledgePointCode: string,
): Promise<SelfStudyResult> {
  return api.post<SelfStudyResult>("/daily-tasks/self-study", {
    knowledge_point_code: knowledgePointCode,
  });
}

/** 撤回自选任务：后端只允许撤回「自选且未完成」的任务。 */
export function deleteSelfStudyTask(taskId: string): Promise<void> {
  return api.delete<void>(`/daily-tasks/${encodeURIComponent(taskId)}`);
}

/** 课程学习页数据源：章节两轴进度 + 可自选知识点目录。 */
export function getStudyCandidates(
  courseCode: string,
): Promise<StudyCandidates> {
  return api.get<StudyCandidates>(
    `/study/candidates?course_code=${encodeURIComponent(courseCode)}`,
  );
}

/** 课程进度汇总：学习完成度与已验证掌握度分开返回。 */
export function getProgressSummary(courseCode: string): Promise<CourseProgress> {
  return api.get<CourseProgress>(
    `/progress/summary?course_code=${encodeURIComponent(courseCode)}`,
  );
}

/**
 * 「我会了，测一测」：复用诊断（跳级）测验。
 * 每个知识点 2 题且全对才会写入掌握证据；题量不足时后端返回 409。
 */
export function createPlacementQuiz(
  knowledgePointCode: string,
): Promise<{ id: string }> {
  return api.post<{ id: string }>("/diagnosis/placement", {
    knowledge_point_codes: [knowledgePointCode],
    questions_per_point: 2,
  });
}

const EMPTY_SUMMARY: TodayTasksSummary = {
  plan_total: 0,
  plan_completed: 0,
  self_selected_total: 0,
  self_selected_completed: 0,
  in_progress: 0,
  carried_over: 0,
  remaining_minutes: 0,
};

function summarize(
  plan: DailyTask[],
  selfSelected: DailyTask[],
  carriedOver: DailyTask[],
): TodayTasksSummary {
  const unfinished = [
    ...plan.filter((task) => task.status !== "completed"),
    ...selfSelected.filter((task) => task.status !== "completed"),
    ...carriedOver,
  ];
  return {
    plan_total: plan.length,
    plan_completed: plan.filter((t) => t.status === "completed").length,
    self_selected_total: selfSelected.length,
    self_selected_completed: selfSelected.filter((t) => t.status === "completed")
      .length,
    in_progress: [...plan, ...selfSelected, ...carriedOver].filter(
      (t) => t.status === "learning",
    ).length,
    carried_over: carriedOver.length,
    remaining_minutes: unfinished.reduce(
      (sum, task) => sum + task.knowledge_point.estimated_minutes,
      0,
    ),
  };
}

export interface TodayTaskGroups {
  plan: DailyTask[];
  selfSelected: DailyTask[];
  carriedOver: DailyTask[];
  summary: TodayTasksSummary;
}

/**
 * 今日任务按来源分组。
 *
 * 后端阶段 7 起直接返回分组字段；旧响应（或测试夹具）只有 `tasks` 时，
 * 按 `source` 兜底，`source` 缺失一律视为计划任务——保证旧数据仍可用。
 */
export function groupTodayTasks(data: TodayTasks | null): TodayTaskGroups {
  if (!data) {
    return {
      plan: [],
      selfSelected: [],
      carriedOver: [],
      summary: EMPTY_SUMMARY,
    };
  }
  const plan =
    data.plan_tasks ?? data.tasks.filter((t) => (t.source ?? "plan") === "plan");
  const selfSelected =
    data.self_selected_tasks ??
    data.tasks.filter((t) => t.source === "self_selected");
  const carriedOver = data.carried_over_tasks ?? [];
  return {
    plan,
    selfSelected,
    carriedOver,
    summary: data.summary ?? summarize(plan, selfSelected, carriedOver),
  };
}
