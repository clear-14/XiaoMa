/** 课程、知识点与每日任务 API 封装。 */

import { api } from "@/lib/api";
import type {
  CourseDetail,
  CourseSummary,
  DailyTask,
  KnowledgePointDetail,
  TodayTasks,
} from "@/lib/types";

export type {
  CourseDetail,
  CourseSummary,
  DailyTask,
  KnowledgePointDetail,
  TodayTasks,
} from "@/lib/types";

/**
 * 首页第一步：只读查询当天任务。
 * `generate=false` 保证不会在「先查」这一步写入任何数据。
 */
export function getTodayTasks(generate = true): Promise<TodayTasks> {
  return api.get<TodayTasks>(`/daily-tasks/today?generate=${generate}`);
}

/**
 * 首页第二步：仅在当天尚无任务时调用。后端先查后生成 + 唯一约束保证幂等，
 * 重复调用只会返回已有任务。
 */
export function generateTodayTasks(): Promise<TodayTasks> {
  return api.post<TodayTasks>("/daily-tasks/today/generate");
}

export function getTaskDetail(taskId: string): Promise<DailyTask> {
  return api.get<DailyTask>(`/daily-tasks/${taskId}`);
}

/** V1.4 批次 5：开始今日任务，调用真实业务写接口。 */
export function startDailyTask(taskId: string): Promise<DailyTask> {
  return api.post<DailyTask>(
    `/daily-tasks/${encodeURIComponent(taskId)}/start`,
  );
}

/**
 * V1.4 批次 5：完成今日任务，调用真实业务写接口。
 * 任务完成只是自述状态，不等于知识点掌握；掌握仍需后端测验证据。
 */
export function completeDailyTask(taskId: string): Promise<DailyTask> {
  return api.post<DailyTask>(
    `/daily-tasks/${encodeURIComponent(taskId)}/complete`,
  );
}

export function listCourses(): Promise<CourseSummary[]> {
  return api.get<CourseSummary[]>("/courses");
}

export function getCourseDetail(courseCode: string): Promise<CourseDetail> {
  return api.get<CourseDetail>(`/courses/${encodeURIComponent(courseCode)}`);
}

export function getKnowledgePoint(
  knowledgePointCode: string,
): Promise<KnowledgePointDetail> {
  return api.get<KnowledgePointDetail>(
    `/knowledge-points/${encodeURIComponent(knowledgePointCode)}`,
  );
}
