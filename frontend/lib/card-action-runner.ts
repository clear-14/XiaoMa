/**
 * V1.4 批次 5：卡片动作的**真实 API 执行层**。
 *
 * 每个分支都调用已经存在的后端业务接口，不构造模拟数据、不用聊天文本冒充
 * 业务结果。返回值只是给用户的中文即时反馈；评分、掌握状态、计划版本等
 * 权威数据仍保存在后端业务表，由右栏真实只读接口再次读取。
 *
 * 与 `card-actions.ts` 的纯函数描述层分开，便于对「哪些按钮会渲染」和
 * 「按钮到底调了哪个接口」分别做确定性单测。
 */

import type { CardActionSpec } from "@/lib/card-actions";
import { completeDailyTask, startDailyTask } from "@/lib/learning";
import {
  confirmPlan,
  confirmPlanProposal,
  rejectPlanProposal,
} from "@/lib/plans";
import { getLearningOverview } from "@/lib/profile";
import { getQuizAttempt, submitQuiz, submitReview } from "@/lib/quiz";
import type { QuizAnswerInput } from "@/lib/types";

export interface CardActionInput {
  answers?: QuizAnswerInput[];
  reviewAnswer?: string;
}

function requireId(spec: CardActionSpec): string {
  if (!spec.targetId) {
    throw new Error("卡片缺少业务标识，无法执行该操作");
  }
  return spec.targetId;
}

export async function runCardAction(
  spec: CardActionSpec,
  input: CardActionInput = {},
): Promise<string> {
  switch (spec.kind) {
    case "start_task": {
      const task = await startDailyTask(requireId(spec));
      return `已开始学习「${task.knowledge_point.name}」`;
    }

    case "complete_task": {
      const task = await completeDailyTask(requireId(spec));
      return (
        `已完成「${task.knowledge_point.name}」；` +
        "任务完成只是学习记录，掌握状态仍以后端测验证据为准。"
      );
    }

    case "confirm_plan": {
      const plan = await confirmPlan(requireId(spec));
      return `学习计划已确认生效：${plan.course_name}`;
    }

    case "confirm_proposal": {
      const result = await confirmPlanProposal(requireId(spec));
      return result.message || "调整已确认，新的计划版本已生效";
    }

    case "reject_proposal": {
      await rejectPlanProposal(requireId(spec));
      return "已放弃调整建议，当前学习计划保持不变";
    }

    case "submit_quiz": {
      const attemptId = requireId(spec);
      if (!input.answers || input.answers.length === 0) {
        throw new Error("请先完成所有题目再提交");
      }
      const attempt = await submitQuiz(attemptId, input.answers);
      return (
        `后端已评分：${attempt.score ?? 0} / ${attempt.total_points} 分` +
        `（共 ${attempt.question_count} 题）；结果已保存到测验记录。`
      );
    }

    case "submit_review": {
      const taskId = requireId(spec);
      const answer = input.reviewAnswer?.trim();
      if (!answer) {
        throw new Error("请先填写复习答案");
      }
      const result = await submitReview(taskId, answer);
      return result.message || "复习答案已提交，后端已更新复习记录";
    }

    case "refresh_quiz": {
      const attempt = await getQuizAttempt(requireId(spec));
      return attempt.status === "submitted"
        ? `后端评分：${attempt.score ?? 0} / ${attempt.total_points} 分`
        : "这份测验尚未提交，暂无评分结果";
    }

    case "refresh_progress": {
      const overview = await getLearningOverview();
      return (
        `已掌握 ${overview.mastered_count} 个、` +
        `学习中 ${overview.learning_count} 个知识点（数据来自后端概览）`
      );
    }

    default:
      throw new Error("不支持的卡片操作");
  }
}
