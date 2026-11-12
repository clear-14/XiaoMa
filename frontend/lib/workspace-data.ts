/**
 * V1.4 批次 3：右侧学习工作区的数据聚合。
 *
 * 全部数据来自既有只读业务接口（技术设计 §2.6、PRD §3.3 第 4/5 条）：
 * 前端不推断掌握状态、不生成任何占位数据。404 表示「尚无该业务记录」，
 * 按空状态展示；其余错误按错误状态展示并允许重试。
 */

import { ApiError, getErrorMessage } from "@/lib/api";
import {
  generateTodayTasks,
  getKnowledgePoint,
  getTodayTasks,
  type KnowledgePointDetail,
  type TodayTasks,
} from "@/lib/learning";
import { getMasteryOverview, type MasteryOverview } from "@/lib/mastery";
import { getCurrentPlan, type CurrentPlan } from "@/lib/plans";
import { getLearningOverview, type LearningOverview } from "@/lib/profile";

export interface PanelResult<T> {
  data: T | null;
  error: string | null;
}

export interface WorkspaceSnapshot {
  plan: PanelResult<CurrentPlan>;
  today: PanelResult<TodayTasks>;
  knowledgePoint: PanelResult<KnowledgePointDetail>;
  overview: PanelResult<LearningOverview>;
  mastery: PanelResult<MasteryOverview>;
}

/** 404 = 业务记录尚不存在（空状态），不是接口故障。 */
export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/**
 * 今日任务严格「先查后生成」：只有查询确认当天没有任何任务时才调用生成接口，
 * 后端幂等保证重复打开工作台不会重复创建任务（PRD §4.2）。
 */
export function shouldGenerateTodayTasks(today: TodayTasks): boolean {
  return Array.isArray(today.tasks) && today.tasks.length === 0;
}

/** 当前知识点取当天第一个任务关联的知识点；没有任务时返回 null。 */
export function pickKnowledgePointCode(today: TodayTasks | null): string | null {
  return today?.tasks?.[0]?.knowledge_point?.code ?? null;
}

/** 把 Promise.allSettled 的单项结果归一成面板状态，纯函数便于单测。 */
export function toPanelResult<T>(
  result: PromiseSettledResult<T>,
): PanelResult<T> {
  if (result.status === "fulfilled") {
    return { data: result.value, error: null };
  }
  if (isNotFound(result.reason)) {
    return { data: null, error: null };
  }
  return { data: null, error: getErrorMessage(result.reason) };
}

/** 今日任务单独处理：先查，为空才生成；404 视为空态。 */
export async function loadTodayTasks(): Promise<PanelResult<TodayTasks>> {
  try {
    const existing = await getTodayTasks(false);
    const data = shouldGenerateTodayTasks(existing)
      ? await generateTodayTasks()
      : existing;
    return { data, error: null };
  } catch (err) {
    if (isNotFound(err)) {
      return { data: null, error: null };
    }
    return { data: null, error: getErrorMessage(err) };
  }
}

/** 标题栏「今日学习刻度尺」的真实刻度：已完成计划项 / 计划总项。 */
export interface LearningRuler {
  completed: number;
  total: number;
  dayIndex: number | null;
  label: string;
}

export function computeLearningRuler(
  today: TodayTasks | null,
  plan: CurrentPlan | null,
): LearningRuler {
  const items = plan?.current_version?.items ?? [];
  const completed = items.filter((item) => item.status === "completed").length;
  const total = items.length;
  const dayIndex = today?.tasks?.[0]?.day_index ?? null;
  return {
    completed,
    total,
    dayIndex,
    label:
      total > 0
        ? `${completed}/${total} 项${dayIndex !== null ? ` · 第 ${dayIndex} 天` : ""}`
        : "尚未建立学习计划",
  };
}

/** 并发拉取四面板数据，互不影响：单个接口失败不会拖垮整个工作区。 */
export async function loadWorkspaceSnapshot(): Promise<WorkspaceSnapshot> {
  const [plan, today, overview, mastery] = await Promise.allSettled([
    getCurrentPlan(),
    loadTodayTasks(),
    getLearningOverview(),
    getMasteryOverview(),
  ] as const);

  const todayResult: PanelResult<TodayTasks> =
    today.status === "fulfilled"
      ? today.value
      : { data: null, error: getErrorMessage(today.reason) };

  const kpCode = pickKnowledgePointCode(todayResult.data);
  let knowledgePoint: PanelResult<KnowledgePointDetail> = {
    data: null,
    error: null,
  };
  if (kpCode) {
    try {
      knowledgePoint = { data: await getKnowledgePoint(kpCode), error: null };
    } catch (err) {
      knowledgePoint = isNotFound(err)
        ? { data: null, error: null }
        : { data: null, error: getErrorMessage(err) };
    }
  }

  return {
    plan: toPanelResult(plan),
    today: todayResult,
    knowledgePoint,
    overview: toPanelResult(overview),
    mastery: toPanelResult(mastery),
  };
}
