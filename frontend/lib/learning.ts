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

export function getTodayTasks(): Promise<TodayTasks> {
  return api.get<TodayTasks>("/daily-tasks/today");
}

export function getTaskDetail(taskId: string): Promise<DailyTask> {
  return api.get<DailyTask>(`/daily-tasks/${taskId}`);
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
