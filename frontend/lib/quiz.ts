/** 测验、错题与复习 API 封装及展示辅助。 */

import { api } from "@/lib/api";
import type {
  Mistake,
  QuizAnswerInput,
  QuizAttempt,
  QuizAttemptSummary,
  QuizCreateInput,
  QuizEligibility,
  QuizQuestion,
  ReviewResult,
  ReviewTask,
} from "@/lib/types";

export type {
  Mistake,
  QuizAnswerInput,
  QuizAttempt,
  QuizAttemptSummary,
  QuizCreateInput,
  QuizEligibility,
  QuizQuestion,
  QuizQuestionType,
  QuizScopeType,
  ReviewResult,
  ReviewTask,
} from "@/lib/types";

/** AI 变式题需要生成 + 独立复核，组卷请求使用更长超时。 */
const QUIZ_CREATE_TIMEOUT_MS = 180_000;

const SCOPE_LABELS: Record<string, string> = {
  knowledge_point: "知识点测验",
  chapter: "章节测验",
  stage: "阶段综合测验",
  review: "错题复习",
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  true_false: "判断题",
  fill_blank: "填空题",
  short_answer: "简答题",
  code_analysis: "代码分析题",
  code_writing: "代码编写题",
};

const STATUS_LABELS: Record<string, string> = {
  in_progress: "答题中",
  submitted: "已提交",
  pending: "待复习",
  resolved: "已解决",
  completed: "已完成",
  skipped: "已跳过",
  learning: "学习中",
  pending_verification: "待验证",
  mastered: "已掌握",
  review_due: "待复习",
  not_started: "未开始",
};

export function scopeTypeLabel(value: string): string {
  return SCOPE_LABELS[value] ?? value;
}

export function questionTypeLabel(value: string): string {
  return QUESTION_TYPE_LABELS[value] ?? value;
}

export function quizStatusLabel(value: string): string {
  return STATUS_LABELS[value] ?? value;
}

export function getQuizEligibility(): Promise<QuizEligibility> {
  return api.get<QuizEligibility>("/quizzes/eligibility");
}

export function listQuizAttempts(): Promise<QuizAttemptSummary[]> {
  return api.get<QuizAttemptSummary[]>("/quizzes");
}

export function createQuiz(input: QuizCreateInput): Promise<QuizAttempt> {
  return api.post<QuizAttempt>("/quizzes", input, QUIZ_CREATE_TIMEOUT_MS);
}

export function getQuizAttempt(attemptId: string): Promise<QuizAttempt> {
  return api.get<QuizAttempt>(`/quizzes/${attemptId}`);
}

export function submitQuiz(
  attemptId: string,
  answers: QuizAnswerInput[],
): Promise<QuizAttempt> {
  return api.post<QuizAttempt>(`/quizzes/${attemptId}/submit`, { answers });
}

export function listMistakes(
  reviewStatus?: "pending" | "resolved",
): Promise<Mistake[]> {
  const query = reviewStatus ? `?review_status=${reviewStatus}` : "";
  return api.get<Mistake[]>(`/mistakes${query}`);
}

export function listReviewTasks(): Promise<ReviewTask[]> {
  return api.get<ReviewTask[]>("/reviews/tasks");
}

export function submitReview(
  taskId: string,
  answer: unknown,
): Promise<ReviewResult> {
  return api.post<ReviewResult>(`/reviews/tasks/${taskId}/submit`, { answer });
}

/** 前端在提交前检查每道题是否已作答（空数组/空字符串视为未作答）。 */
export function isAnswerEmpty(
  question: QuizQuestion,
  answer: unknown,
): boolean {
  if (question.question_type === "multiple_choice") {
    return !Array.isArray(answer) || answer.length === 0;
  }
  if (question.question_type === "true_false") {
    return typeof answer !== "boolean";
  }
  return typeof answer !== "string" || answer.trim().length === 0;
}

/** 后端正确答结构 → 展示值（单选/判断 value、多选/填空 values、主观题 reference）。 */
export function correctAnswerValue(question: QuizQuestion): unknown {
  const answer = question.correct_answer;
  if (!answer || typeof answer !== "object") {
    return answer;
  }
  const record = answer as Record<string, unknown>;
  if ("value" in record) {
    return record.value;
  }
  if ("values" in record) {
    return record.values;
  }
  if ("reference" in record) {
    return record.reference;
  }
  return answer;
}

/** 把答案值格式化为可读文本（兼容字符串、布尔值与选项 key）。 */
export function formatAnswer(
  question: QuizQuestion,
  answer: unknown,
): string {
  if (answer === null || answer === undefined) {
    return "（未作答）";
  }
  if (question.question_type === "true_false") {
    return answer === true ? "正确（True）" : "错误（False）";
  }
  if (
    question.question_type === "single_choice" ||
    question.question_type === "multiple_choice"
  ) {
    const values = Array.isArray(answer) ? answer : [answer];
    const optionMap = new Map(
      (question.options ?? []).map((option) => [option.key, option.text]),
    );
    return values
      .map((value) => {
        const key = String(value).toUpperCase();
        const text = optionMap.get(key);
        return text ? `${key}. ${text}` : key;
      })
      .join("；");
  }
  if (Array.isArray(answer)) {
    return answer.map((item) => String(item)).join(" 或 ");
  }
  return String(answer);
}
