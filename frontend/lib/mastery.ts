/** 阶段 5：知识点掌握度与学习诊断 API 封装及展示辅助。 */

import { api } from "@/lib/api";
import type {
  DiagnosisDimension,
  DiagnosisInput,
  DiagnosisReport,
  ExerciseSubmitResult,
  MasteryDetail,
  MasteryKnowledgePoint,
  MasteryOverview,
  MasteryStatus,
  PlacementInput,
  PlacementPlan,
  QuizAttempt,
  ReviewSuggestion,
  RouteAction,
  SelfReportResult,
  SkipCheck,
} from "@/lib/types";

export type {
  DiagnosisDimension,
  DiagnosisInput,
  DiagnosisReport,
  ExerciseSubmitResult,
  MasteryDetail,
  MasteryKnowledgePoint,
  MasteryOverview,
  MasteryStatus,
  PlacementInput,
  PlacementPlan,
  ReviewSuggestion,
  RouteAction,
  SelfReportResult,
  SkipCheck,
} from "@/lib/types";

/** 7 个状态的中文标签与配色（与后端 MASTERY_STATUS_LABELS 同源）。 */
export const MASTERY_STATUS_LABELS: Record<MasteryStatus, string> = {
  not_started: "未开始",
  learning: "学习中",
  self_reported_completed: "用户自述完成",
  understood: "基础理解通过",
  applied: "应用练习通过",
  mastered: "真正掌握",
  needs_review: "需要复习",
};

/** 状态归类：verified=有验证证据，claim=仅自述，progress=进行中，none=未开始。 */
export type MasteryTone = "verified" | "claim" | "progress" | "review" | "none";

export const MASTERY_TONES: Record<MasteryStatus, MasteryTone> = {
  not_started: "none",
  learning: "progress",
  self_reported_completed: "claim",
  understood: "verified",
  applied: "verified",
  mastered: "verified",
  needs_review: "review",
};

export const ROUTE_ACTION_LABELS: Record<RouteAction, string> = {
  study: "学习",
  review: "复习",
  verify: "验证（诊断测验）",
  skip: "跳过（已有掌握证据）",
  remedial: "补学先修",
};

/** 总览：7 状态计数 + 已验证掌握与仅自述分列。 */
export function getMasteryOverview(): Promise<MasteryOverview> {
  return api.get<MasteryOverview>("/mastery");
}

/** 按课程列出全部知识点的掌握状态（未学习的也返回）。 */
export function listMasteryKnowledgePoints(
  courseCode?: string,
): Promise<MasteryKnowledgePoint[]> {
  const query = courseCode ? `?course_code=${encodeURIComponent(courseCode)}` : "";
  return api.get<MasteryKnowledgePoint[]>(`/mastery/knowledge-points${query}`);
}

/** 单个知识点详情：当前态 + 证据流水 + 练习记录。 */
export function getMasteryDetail(kpCode: string): Promise<MasteryDetail> {
  return api.get<MasteryDetail>(
    `/mastery/knowledge-points/${encodeURIComponent(kpCode)}`,
  );
}

/** 用户自述完成（不会变成 MASTERED）。 */
export function reportSelfCompleted(
  knowledgePointCodes: string[],
  note?: string,
): Promise<SelfReportResult> {
  return api.post<SelfReportResult>("/mastery/self-report", {
    knowledge_point_codes: knowledgePointCodes,
    ...(note ? { note } : {}),
  });
}

/** 提交应用练习（按参考答案覆盖率判定，不执行用户代码）。 */
export function submitExercise(
  exerciseCode: string,
  answer: string,
): Promise<ExerciseSubmitResult> {
  return api.post<ExerciseSubmitResult>(
    `/mastery/exercises/${encodeURIComponent(exerciseCode)}/attempt`,
    { answer },
  );
}

/** 薄弱知识点复习建议。 */
export function getReviewSuggestions(): Promise<ReviewSuggestion[]> {
  return api.get<ReviewSuggestion[]>("/mastery/review-suggestions");
}

/** 跳级检查：只有 MASTERED 才进 skippable。 */
export function getSkipCheck(courseCode: string): Promise<SkipCheck> {
  return api.get<SkipCheck>(
    `/mastery/skip-check?course_code=${encodeURIComponent(courseCode)}`,
  );
}

/** 6 个诊断维度定义（含锚点知识点）。 */
export function getDiagnosisDimensions(): Promise<DiagnosisDimension[]> {
  return api.get<DiagnosisDimension[]>("/diagnosis/dimensions");
}

/** 发起诊断：六维画像 + 个性化学习路线。 */
export function runDiagnosis(input: DiagnosisInput): Promise<DiagnosisReport> {
  return api.post<DiagnosisReport>("/diagnosis", input);
}

/** 诊断测验预检：能验证哪些知识点、各能出几道题。 */
export function planPlacement(input: PlacementInput): Promise<PlacementPlan> {
  return api.post<PlacementPlan>("/diagnosis/placement/plan", input);
}

/** 生成诊断（跳级）测验；返回的测验用常规提交接口作答。 */
export function createPlacementQuiz(input: PlacementInput): Promise<QuizAttempt> {
  return api.post<QuizAttempt>("/diagnosis/placement", input);
}
