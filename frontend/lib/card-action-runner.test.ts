/**
 * V1.4 批次 5：卡片动作执行层测试。
 *
 * 验证每个按钮都调到真实且正确的业务接口，以及参数校验失败时不会发请求。
 * 这里 mock 的是 API 封装边界，不是业务规则本身。
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CardActionKind, CardActionSpec } from "@/lib/card-actions";
import { runCardAction } from "@/lib/card-action-runner";
import { completeDailyTask, startDailyTask } from "@/lib/learning";
import {
  confirmPlan,
  confirmPlanProposal,
  rejectPlanProposal,
} from "@/lib/plans";
import { getLearningOverview } from "@/lib/profile";
import { getQuizAttempt, submitQuiz, submitReview } from "@/lib/quiz";
import type {
  CurrentPlan,
  DailyTask,
  LearningOverview,
  QuizAttempt,
  ReviewResult,
} from "@/lib/types";

vi.mock("@/lib/learning", () => ({
  startDailyTask: vi.fn(),
  completeDailyTask: vi.fn(),
}));
vi.mock("@/lib/plans", () => ({
  confirmPlan: vi.fn(),
  confirmPlanProposal: vi.fn(),
  rejectPlanProposal: vi.fn(),
}));
vi.mock("@/lib/profile", () => ({ getLearningOverview: vi.fn() }));
vi.mock("@/lib/quiz", () => ({
  getQuizAttempt: vi.fn(),
  submitQuiz: vi.fn(),
  submitReview: vi.fn(),
}));

function spec(
  kind: CardActionKind,
  targetId: string | null = "id-1",
): CardActionSpec {
  return {
    kind,
    label: "操作",
    confirm: null,
    targetId,
    refreshPanels: true,
    write: true,
  };
}

function task(): DailyTask {
  return { knowledge_point: { name: "变量" } } as unknown as DailyTask;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("写操作只调用真实业务接口", () => {
  it("开始学习调用 POST /daily-tasks/{id}/start", async () => {
    vi.mocked(startDailyTask).mockResolvedValue(task());
    const text = await runCardAction(spec("start_task", "task-9"));
    expect(startDailyTask).toHaveBeenCalledWith("task-9");
    expect(text).toContain("变量");
  });

  it("标记完成调用 complete，且明确说明不等于掌握", async () => {
    vi.mocked(completeDailyTask).mockResolvedValue(task());
    const text = await runCardAction(spec("complete_task", "task-9"));
    expect(completeDailyTask).toHaveBeenCalledWith("task-9");
    expect(text).toContain("测验证据");
  });

  it("确认计划调用 /plans/{id}/confirm", async () => {
    vi.mocked(confirmPlan).mockResolvedValue({
      course_name: "Python 零基础入门",
    } as unknown as CurrentPlan);
    const text = await runCardAction(spec("confirm_plan", "plan-9"));
    expect(confirmPlan).toHaveBeenCalledWith("plan-9");
    expect(text).toContain("已确认生效");
  });

  it("确认调整调用提案确认接口并展示后端返回的原因", async () => {
    vi.mocked(confirmPlanProposal).mockResolvedValue({
      message: "已生成版本 2",
    } as unknown as Awaited<ReturnType<typeof confirmPlanProposal>>);
    const text = await runCardAction(spec("confirm_proposal", "proposal-9"));
    expect(confirmPlanProposal).toHaveBeenCalledWith("proposal-9");
    expect(text).toBe("已生成版本 2");
  });

  it("放弃调整调用提案拒绝接口，不修改正式计划", async () => {
    vi.mocked(rejectPlanProposal).mockResolvedValue(
      {} as unknown as Awaited<ReturnType<typeof rejectPlanProposal>>,
    );
    const text = await runCardAction(spec("reject_proposal", "proposal-9"));
    expect(rejectPlanProposal).toHaveBeenCalledWith("proposal-9");
    expect(text).toContain("保持不变");
  });

  it("提交测验调用 submit，评分结果来自后端返回", async () => {
    vi.mocked(submitQuiz).mockResolvedValue({
      score: 8,
      total_points: 10,
      question_count: 3,
    } as unknown as QuizAttempt);
    const answers = [{ question_id: "q1", answer: "A" }];
    const text = await runCardAction(spec("submit_quiz", "attempt-9"), {
      answers,
    });
    expect(submitQuiz).toHaveBeenCalledWith("attempt-9", answers);
    expect(text).toContain("8 / 10");
  });

  it("提交复习调用 submitReview，空答案不发请求", async () => {
    await expect(
      runCardAction(spec("submit_review", "review-9"), { reviewAnswer: "  " }),
    ).rejects.toThrow("请先填写复习答案");
    expect(submitReview).not.toHaveBeenCalled();

    vi.mocked(submitReview).mockResolvedValue({
      message: "复习已记录",
    } as unknown as ReviewResult);
    const text = await runCardAction(spec("submit_review", "review-9"), {
      reviewAnswer: "age = 18",
    });
    expect(submitReview).toHaveBeenCalledWith("review-9", "age = 18");
    expect(text).toBe("复习已记录");
  });
});

describe("只读刷新与参数校验", () => {
  it("查看最新评分调用真实测验详情接口", async () => {
    vi.mocked(getQuizAttempt).mockResolvedValue({
      status: "submitted",
      score: 7,
      total_points: 10,
    } as unknown as QuizAttempt);
    const text = await runCardAction(spec("refresh_quiz", "attempt-9"));
    expect(getQuizAttempt).toHaveBeenCalledWith("attempt-9");
    expect(text).toContain("7 / 10");
  });

  it("未提交的测验不编造评分", async () => {
    vi.mocked(getQuizAttempt).mockResolvedValue({
      status: "in_progress",
      score: null,
      total_points: 10,
    } as unknown as QuizAttempt);
    const text = await runCardAction(spec("refresh_quiz", "attempt-9"));
    expect(text).toContain("尚未提交");
  });

  it("刷新进度调用真实概览接口，不自行推算数字", async () => {
    vi.mocked(getLearningOverview).mockResolvedValue({
      mastered_count: 3,
      learning_count: 2,
    } as unknown as LearningOverview);
    const text = await runCardAction(
      spec("refresh_progress", null),
    );
    expect(getLearningOverview).toHaveBeenCalledOnce();
    expect(text).toContain("已掌握 3 个");
    expect(text).toContain("学习中 2 个");
  });

  it("缺少业务标识或答案时明确报错，不发起网络请求", async () => {
    await expect(runCardAction(spec("start_task", null))).rejects.toThrow(
      "缺少业务标识",
    );
    await expect(
      runCardAction(spec("submit_quiz", "attempt-9")),
    ).rejects.toThrow("请先完成所有题目");
    expect(startDailyTask).not.toHaveBeenCalled();
    expect(submitQuiz).not.toHaveBeenCalled();
  });
});
