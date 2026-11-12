/**
 * V1.4 批次 5：卡片可执行动作的**纯函数描述层**。
 *
 * 这里不发起任何网络请求，只回答三个问题：这张卡片能做什么、依赖哪个真实
 * 业务标识、是否需要二次确认。执行副作用在 `lib/card-action-runner.ts`。
 *
 * 硬约束（PRD §6）：
 * 1. 卡片展示数据来自后端业务结果——动作所需 id 只从 `payload` 读取，
 *    不从聊天文本推断，也不凭卡片类型编造；
 * 2. 卡片按钮必须调用真实 API——没有真实业务标识就不生成动作，绝不渲染假按钮；
 * 3. 重要修改操作（计划确认、任务完成、测验提交）必须有确认步骤。
 */

import {
  readBoolean,
  readObjectArray,
  readString,
  type Card,
} from "@/lib/cards";
import type { QuizAnswerInput } from "@/lib/types";

export type CardActionKind =
  | "start_task"
  | "complete_task"
  | "confirm_plan"
  | "confirm_proposal"
  | "reject_proposal"
  | "submit_quiz"
  | "submit_review"
  | "refresh_quiz"
  | "refresh_progress";

export interface CardActionSpec {
  kind: CardActionKind;
  label: string;
  /** 重要修改操作的二次确认文案；`null` 表示无需确认。 */
  confirm: string | null;
  /** 动作依赖的真实业务标识；缺失时不会生成该动作。 */
  targetId: string | null;
  /** 成功后是否刷新右侧四面板（右栏数据来自真实只读接口）。 */
  refreshPanels: boolean;
  /** 是否为业务写操作（用于区分只读刷新按钮）。 */
  write: boolean;
}

export interface QuizAnswerDraft {
  questionId: string;
  questionType: string;
  stem: string;
  options: { key: string; text: string }[];
}

/** 从 payload 读取可选字符串；联合类型在这里统一收口。 */
function field(card: Card, key: string): string | null {
  return readString(card.payload as Record<string, unknown>, key);
}

function action(
  kind: CardActionKind,
  label: string,
  targetId: string | null,
  confirm: string | null,
  write = true,
): CardActionSpec {
  return {
    kind,
    label,
    confirm,
    targetId,
    refreshPanels: true,
    write,
  };
}

/** 已处理过的卡片不再提供重复写操作，避免刷新历史消息后误触。 */
function isProcessed(status: string | null): boolean {
  if (status === null) {
    return false;
  }
  return status === "completed" || status === "confirmed" || status === "rejected";
}

/**
 * 按卡片类型返回真实可执行的动作列表。
 * 字段缺失、卡片已处理、缺少题目 id 时都不生成动作。
 */
export function getCardActionSpecs(card: Card): CardActionSpec[] {
  const status = field(card, "status");

  switch (card.type) {
    case "task_card": {
      const taskId = field(card, "task_id");
      if (!taskId || isProcessed(status)) {
        return [];
      }
      const specs: CardActionSpec[] = [];
      if (status === null || status === "pending") {
        specs.push(
          action("start_task", "开始学习", taskId, null),
        );
      }
      specs.push(
        action(
          "complete_task",
          "标记完成",
          taskId,
          `确定将「${card.payload.title}」标记为完成吗？任务完成只记录学习进度，不会自动判定知识点已掌握。`,
        ),
      );
      return specs;
    }

    case "plan_card": {
      const planId = field(card, "plan_id");
      if (!planId || isProcessed(status)) {
        return [];
      }
      return [
        action(
          "confirm_plan",
          "确认计划",
          planId,
          "确定确认这份学习计划吗？确认后该版本将正式生效并用于安排每日任务。",
        ),
      ];
    }

    case "plan_change_card": {
      const proposalId = field(card, "proposal_id");
      const needsConfirmation = readBoolean(
        card.payload as Record<string, unknown>,
        "requires_confirmation",
      );
      if (!proposalId || isProcessed(status) || needsConfirmation === false) {
        return [];
      }
      return [
        action(
          "confirm_proposal",
          "确认并保存调整",
          proposalId,
          "确定采纳这份调整建议吗？确认后才会生成并生效新的学习计划版本，当前正式计划会随之更新。",
        ),
        action(
          "reject_proposal",
          "放弃调整",
          proposalId,
          "确定放弃这份调整建议吗？放弃后当前学习计划保持不变。",
        ),
      ];
    }

    case "quiz_card": {
      const attemptId = field(card, "attempt_id");
      if (!attemptId || readQuizQuestions(card).length === 0) {
        return [];
      }
      return [
        action(
          "submit_quiz",
          "提交答案",
          attemptId,
          "确定提交本次测验答案吗？提交后由后端统一评分，答案不能再修改，错题会进入错题本。",
        ),
      ];
    }

    case "mistake_card": {
      const taskId = field(card, "review_task_id");
      if (!taskId || isProcessed(status)) {
        return [];
      }
      return [action("submit_review", "提交复习答案", taskId, null)];
    }

    case "quiz_result_card": {
      const attemptId = field(card, "attempt_id");
      if (!attemptId) {
        return [];
      }
      return [
        action("refresh_quiz", "查看最新评分", attemptId, null, false),
      ];
    }

    case "progress_card":
      return [action("refresh_progress", "刷新进度", null, null, false)];

    default:
      // lesson_card / error_card 没有写操作，不渲染任何按钮。
      return [];
  }
}

/** 从测验卡片提取可作答题目；缺 `id` 的题目无法提交，直接跳过。 */
export function readQuizQuestions(card: Card): QuizAnswerDraft[] {
  if (card.type !== "quiz_card") {
    return [];
  }
  const questions = readObjectArray(card.payload, "questions");
  const drafts: QuizAnswerDraft[] = [];
  for (const question of questions) {
    const questionId = readString(question, "id");
    const stem = readString(question, "stem");
    if (!questionId || !stem) {
      continue;
    }
    const options = readObjectArray(question, "options")
      .map((option) => ({
        key: readString(option, "key") ?? "",
        text: readString(option, "text") ?? "",
      }))
      .filter((option) => option.key && option.text);
    drafts.push({
      questionId,
      questionType: readString(question, "question_type") ?? "short_answer",
      stem,
      options,
    });
  }
  return drafts;
}

/** 判断某个题型的答案是否已填写。 */
export function isAnswerFilled(questionType: string, value: unknown): boolean {
  if (questionType === "multiple_choice") {
    return Array.isArray(value) && value.length > 0;
  }
  if (questionType === "true_false") {
    return typeof value === "boolean";
  }
  return typeof value === "string" && value.trim().length > 0;
}

/** 构造真实提交载荷；有任一题未作答时返回 `null`。 */
export function buildQuizAnswers(
  questions: QuizAnswerDraft[],
  values: Record<string, unknown>,
): QuizAnswerInput[] | null {
  if (questions.length === 0) {
    return null;
  }
  const answers: QuizAnswerInput[] = [];
  for (const question of questions) {
    const value = values[question.questionId];
    if (!isAnswerFilled(question.questionType, value)) {
      return null;
    }
    answers.push({ question_id: question.questionId, answer: value });
  }
  return answers;
}
