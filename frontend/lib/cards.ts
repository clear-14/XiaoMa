/**
 * V1.4 批次 4：结构化卡片的 TypeScript 判别联合与语义校验（纯函数层）。
 *
 * 契约依据：`docs/V1.4技术设计与契约.md` §2.5 / §3.2 / §3.3，PRD §5 / §6，
 * 任务书阶段 5 / 8；与后端 `app/schemas/cards.py` 双向对齐，字段名不转换。
 *
 * 边界（务必遵守）：
 * - 卡片数据只来自后端业务结果，前端不得从聊天文字推断卡片内容（PRD §3.3 第 5 条）；
 * - 本模块不访问网络、不读浏览器存储、不依赖 React，全部是可单测的纯函数；
 * - 后端 `normalize_card()` 在批次 1 已冻结，只校验「协议三字段 + payload 为对象」；
 *   本模块在其之上补做**渲染层**的必备字段校验：字段缺失或类型不对即降级
 *   `error_card`，绝不渲染半成品卡片（任务书阶段 5 第 4 / 6 条）。
 * - 版本自 `v1` 起算；未知版本一律降级，不改 `v1` 语义。
 */

import type { CardTypeName } from "@/lib/types";

export const CARD_VERSION = "v1";
export const SUPPORTED_CARD_VERSIONS: readonly string[] = [CARD_VERSION];

/** 9 类卡片（不含普通文本 `text`）。顺序与后端 `CARD_TYPES` 一致。 */
export const CARD_TYPES = [
  "task_card",
  "lesson_card",
  "quiz_card",
  "quiz_result_card",
  "mistake_card",
  "plan_card",
  "plan_change_card",
  "progress_card",
  "error_card",
] as const satisfies readonly Exclude<CardTypeName, "text">[];

export type CardType = (typeof CARD_TYPES)[number];

/** 10 类消息类型 = 9 类卡片 + 普通文本通道（文本由消息气泡渲染，不是卡片）。 */
export const MESSAGE_TYPES: readonly CardTypeName[] = ["text", ...CARD_TYPES];

export const TEXT_MESSAGE_TYPE = "text";
export const ERROR_CARD_TYPE = "error_card";

/* ------------------------------ v1 载荷字段表 ------------------------------ */

/**
 * 字段规则即「必备字段清单」：键是字段名，值是允许的类型。
 *
 * 这份表同时是批次 5 让 Agent 产出卡片时的生成依据，必须与后端
 * `app/schemas/cards.py` 的 `CARD_FIELD_RULES` 同名同序同规则。
 * 表外字段一律视为可选增强信息，由 `readString` / `readArray` 等安全读取，
 * 缺失不影响卡片成立（避免把可选的业务增强字段误判为协议错误）。
 */
export type FieldRule = "string" | "number" | "boolean" | "array" | "object";

export const CARD_FIELD_RULES: Record<CardType, Record<string, FieldRule>> = {
  // PRD §5.2：今日主题、关联知识点、学习目标、预计时长
  task_card: {
    title: "string",
    knowledge_point_code: "string",
    knowledge_point_name: "string",
    learning_goal: "string",
    estimated_minutes: "number",
  },
  // PRD §5.1：知识点讲解正文
  lesson_card: {
    knowledge_point_code: "string",
    knowledge_point_name: "string",
    explanation: "string",
  },
  // PRD §5.4：一次测验的题目集合，答案由后端评分，不在此处判定
  quiz_card: { attempt_id: "string", questions: "array" },
  quiz_result_card: {
    attempt_id: "string",
    score: "number",
    total_points: "number",
  },
  // PRD §5.5：错题题干与归属知识点
  mistake_card: {
    mistake_id: "string",
    question_stem: "string",
    knowledge_point_name: "string",
  },
  // PRD §5.3：当前正式计划版本
  plan_card: {
    plan_id: "string",
    course_name: "string",
    version_number: "number",
    items: "array",
  },
  // PRD §5.3：调整提案，必须经用户确认才保存（按钮在批次 5 接线）
  plan_change_card: {
    proposal_id: "string",
    changes: "object",
  },
  // PRD §5.6：进度数字必须与后端数据一致
  progress_card: {
    course_name: "string",
    mastered_count: "number",
    learning_count: "number",
  },
  // §3.5 / §9.7：失败态与降级终态
  error_card: { reason: "string" },
};

/** 卡片类型 → 中文标签（界面展示，不参与协议）。 */
export const CARD_TYPE_LABELS: Record<CardType, string> = {
  task_card: "今日学习任务",
  lesson_card: "知识点讲解",
  quiz_card: "测验题目",
  quiz_result_card: "测验结果",
  mistake_card: "错题复习",
  plan_card: "学习计划",
  plan_change_card: "计划调整建议",
  progress_card: "学习进度",
  error_card: "操作失败",
};

/** 卡片类型 → 等宽短码（左侧竖标记忆点，界面展示，不参与协议）。 */
export const CARD_TYPE_CODES: Record<CardType, string> = {
  task_card: "TASK",
  lesson_card: "LESSON",
  quiz_card: "QUIZ",
  quiz_result_card: "RESULT",
  mistake_card: "REVIEW",
  plan_card: "PLAN",
  plan_change_card: "CHANGE",
  progress_card: "PROGRESS",
  error_card: "ERROR",
};

/* ------------------------------ 判别联合类型 ------------------------------ */

interface CardBase<T extends CardType, P> {
  card_version: "v1";
  type: T;
  payload: P;
}

export interface TaskCardPayload {
  title: string;
  knowledge_point_code: string;
  knowledge_point_name: string;
  learning_goal: string;
  estimated_minutes: number;
  [key: string]: unknown;
}
export interface LessonCardPayload {
  knowledge_point_code: string;
  knowledge_point_name: string;
  explanation: string;
  [key: string]: unknown;
}
export interface QuizCardPayload {
  attempt_id: string;
  questions: unknown[];
  [key: string]: unknown;
}
export interface QuizResultCardPayload {
  attempt_id: string;
  score: number;
  total_points: number;
  [key: string]: unknown;
}
export interface MistakeCardPayload {
  mistake_id: string;
  question_stem: string;
  knowledge_point_name: string;
  [key: string]: unknown;
}
export interface PlanCardPayload {
  plan_id: string;
  course_name: string;
  version_number: number;
  items: unknown[];
  [key: string]: unknown;
}
export interface PlanChangeCardPayload {
  proposal_id: string;
  changes: Record<string, unknown>;
  [key: string]: unknown;
}
export interface ProgressCardPayload {
  course_name: string;
  mastered_count: number;
  learning_count: number;
  [key: string]: unknown;
}
export interface ErrorCardPayload {
  reason: string;
  [key: string]: unknown;
}

export type TaskCard = CardBase<"task_card", TaskCardPayload>;
export type LessonCard = CardBase<"lesson_card", LessonCardPayload>;
export type QuizCard = CardBase<"quiz_card", QuizCardPayload>;
export type QuizResultCard = CardBase<
  "quiz_result_card",
  QuizResultCardPayload
>;
export type MistakeCard = CardBase<"mistake_card", MistakeCardPayload>;
export type PlanCard = CardBase<"plan_card", PlanCardPayload>;
export type PlanChangeCard = CardBase<
  "plan_change_card",
  PlanChangeCardPayload
>;
export type ProgressCard = CardBase<"progress_card", ProgressCardPayload>;
export type ErrorCard = CardBase<"error_card", ErrorCardPayload>;

export type Card =
  | TaskCard
  | LessonCard
  | QuizCard
  | QuizResultCard
  | MistakeCard
  | PlanCard
  | PlanChangeCard
  | ProgressCard
  | ErrorCard;

/* ------------------------------ 校验纯函数 ------------------------------ */

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function buildErrorCard(reason: string): ErrorCard {
  return {
    card_version: CARD_VERSION,
    type: ERROR_CARD_TYPE,
    payload: { reason },
  };
}

function matchesRule(value: unknown, rule: FieldRule): boolean {
  switch (rule) {
    case "string":
      return typeof value === "string" && value.trim().length > 0;
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    case "boolean":
      return typeof value === "boolean";
    case "array":
      return Array.isArray(value);
    case "object":
      return isRecord(value);
  }
}

/**
 * 校验一张卡片的必备字段。返回失败原因字符串，或 `null` 表示通过。
 * 单独导出以便批次 5 生成卡片时复用同一份规则自检。
 */
export function validateCardPayload(
  type: CardType,
  payload: Record<string, unknown>,
): string | null {
  const rules = CARD_FIELD_RULES[type];
  for (const [field, rule] of Object.entries(rules)) {
    if (!matchesRule(payload[field], rule)) {
      return `卡片 ${type} 的字段 ${field} 缺失或类型不正确`;
    }
  }
  return null;
}

/**
 * 把任意输入校验成一张完整卡片；任何不合法输入都返回 `error_card`。
 * 与后端 `normalize_card()` 的降级终态一致，但额外校验渲染所需必备字段。
 */
export function normalizeCard(raw: unknown): Card {
  if (!isRecord(raw)) {
    return buildErrorCard("卡片数据必须是完整的 JSON 对象");
  }
  const version = raw.card_version;
  if (typeof version !== "string" || !SUPPORTED_CARD_VERSIONS.includes(version)) {
    return buildErrorCard(`不支持的卡片协议版本：${String(version)}`);
  }
  const type = raw.type;
  if (
    typeof type !== "string" ||
    !(CARD_TYPES as readonly string[]).includes(type)
  ) {
    return buildErrorCard(`不支持的卡片类型：${String(type)}`);
  }
  const payload = raw.payload;
  if (!isRecord(payload)) {
    return buildErrorCard("卡片缺少完整的 payload 对象");
  }
  const cardType = type as CardType;
  const failure = validateCardPayload(cardType, payload);
  if (failure) {
    return buildErrorCard(failure);
  }
  // 运行时已按字段表逐项校验，此处收窄为判别联合；保留 payload 全量字段，
  // 供组件安全读取可选增强信息。
  return { card_version: CARD_VERSION, type, payload } as unknown as Card;
}

/**
 * 从持久化的 `messages.structured_data` 恢复卡片。
 * 与后端 `cards_from_structured_data()` 同构：集合对象取 `cards`，
 * 单卡片对象兼容读取，`null` 表示普通文本消息。
 */
export function cardsFromStructuredData(raw: unknown): Card[] {
  if (raw === null || raw === undefined) {
    return [];
  }
  if (isRecord(raw) && "cards" in raw) {
    if (!Array.isArray(raw.cards)) {
      return [buildErrorCard("卡片集合格式不完整")];
    }
    return raw.cards.map(normalizeCard);
  }
  if (isRecord(raw)) {
    return [normalizeCard(raw)];
  }
  return [buildErrorCard("卡片数据格式不完整")];
}

/* ------------------------------ 可选字段安全读取 ------------------------------ */

/** 可选字符串：缺失或非字符串返回 `null`，由组件决定占位文案。 */
export function readString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim() ? value : null;
}

/** 可选数值：非有限数值返回 `null`，不把 0 误判为缺失。 */
export function readNumber(
  payload: Record<string, unknown>,
  key: string,
): number | null {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function readBoolean(
  payload: Record<string, unknown>,
  key: string,
): boolean | null {
  const value = payload[key];
  return typeof value === "boolean" ? value : null;
}

/** 可选数组：只保留对象元素，避免把字符串数组误当结构化条目渲染。 */
export function readObjectArray(
  payload: Record<string, unknown>,
  key: string,
): Record<string, unknown>[] {
  const value = payload[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRecord);
}

export function readStringArray(
  payload: Record<string, unknown>,
  key: string,
): string[] {
  const value = payload[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

export function readObject(
  payload: Record<string, unknown>,
  key: string,
): Record<string, unknown> | null {
  const value = payload[key];
  return isRecord(value) ? value : null;
}

/**
 * 把任意可选值格式化为可展示文本；对象一律不展开成 JSON，
 * 避免把内部结构化数据直接糊到界面上。
 */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "string") {
    return value.trim() ? value : "—";
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (Array.isArray(value)) {
    const parts = value.map(formatValue).filter((part) => part !== "—");
    return parts.length > 0 ? parts.join("、") : "—";
  }
  return "—";
}
