/**
 * V1.4 批次 4：卡片测试共享夹具。
 *
 * 文件名不含 `.test.`，不会被 Vitest 收集为测试；三份卡片测试
 * （协议纯函数 / SSE 帧解析 / 渲染分发）共用同一份合法 v1 载荷，
 * 避免字段表改了之后夹具不同步造成假通过。
 */

import type { CardType } from "./cards";

export { CARD_VERSION } from "./cards";

/** 每类 v1 卡片的合法载荷，与 CARD_FIELD_RULES 一一对应。 */
export const VALID_PAYLOADS: Record<CardType, Record<string, unknown>> = {
  task_card: {
    title: "变量与赋值",
    knowledge_point_code: "py-var",
    knowledge_point_name: "变量",
    learning_goal: "理解变量的含义",
    estimated_minutes: 30,
  },
  lesson_card: {
    knowledge_point_code: "py-var",
    knowledge_point_name: "变量",
    explanation: "变量是用来存放数据的名字。",
  },
  quiz_card: {
    attempt_id: "attempt-1",
    questions: [
      {
        id: "q1",
        stem: "下面哪个是变量？",
        question_type: "single_choice",
        correct_answer: "A",
        options: [
          { key: "A", text: "age = 18" },
          { key: "B", text: "18 = age" },
        ],
      },
    ],
  },
  quiz_result_card: {
    attempt_id: "attempt-1",
    score: 8,
    total_points: 10,
    questions: [
      {
        stem: "下面哪个是变量？",
        is_correct: true,
        correct_answer: "A",
        score: 8,
        explanation: "变量名在赋值号左侧。",
      },
    ],
  },
  mistake_card: {
    mistake_id: "mistake-1",
    question_stem: "写出变量声明语句",
    knowledge_point_name: "变量",
    last_answer: "18 = age",
    correct_answer: "age = 18",
    explanation: "赋值号左边必须是变量名。",
  },
  plan_card: {
    plan_id: "plan-1",
    course_name: "Python 零基础入门",
    version_number: 1,
    items: [
      { day_index: 1, knowledge_point_name: "变量", estimated_minutes: 30, status: "pending" },
    ],
  },
  plan_change_card: {
    proposal_id: "proposal-1",
    changes: { daily_study_minutes: 30 },
    reason: "每天只有 30 分钟",
    preview: {
      current: { daily_study_minutes: 60 },
      proposed: { daily_study_minutes: 30 },
    },
  },
  progress_card: {
    course_name: "Python 零基础入门",
    mastered_count: 3,
    learning_count: 2,
    plan_progress_percent: 33,
    next_step: "继续学习数据类型",
  },
  error_card: { reason: "模型请求超时" },
};

export const VALID_TASK_PAYLOAD = VALID_PAYLOADS.task_card;

/** 构造一张协议完整的原始卡片对象（尚未经过 normalizeCard 校验）。 */
export function validEnvelope(
  type: CardType,
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    card_version: "v1",
    type,
    payload: { ...VALID_PAYLOADS[type], ...extra },
  };
}
