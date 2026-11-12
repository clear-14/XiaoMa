/**
 * V1.4 批次 5：卡片动作描述层纯函数测试。
 *
 * 重点验证「没有真实业务标识就不生成按钮」与「重要修改必须二次确认」，
 * 防止批次 4 明确禁止的假按钮回潮。
 */

import { describe, expect, it } from "vitest";

import {
  buildQuizAnswers,
  getCardActionSpecs,
  isAnswerFilled,
  readQuizQuestions,
} from "@/lib/card-actions";
import { normalizeCard, type Card, type CardType } from "@/lib/cards";
import { validEnvelope } from "@/lib/card-test-fixtures";

function cardOf(
  type: CardType,
  extra: Record<string, unknown> = {},
): Card {
  return normalizeCard(validEnvelope(type, extra));
}

function kinds(card: Card): string[] {
  return getCardActionSpecs(card).map((spec) => spec.kind);
}

describe("getCardActionSpecs：无真实业务标识不渲染按钮", () => {
  it("今日任务卡片缺少 task_id 时不产生任何按钮", () => {
    expect(kinds(cardOf("task_card"))).toEqual([]);
  });

  it("计划卡片缺少 plan_id 时不产生任何按钮", () => {
    expect(
      kinds(cardOf("plan_card", { plan_id: "  " })),
    ).toEqual([]);
  });

  it("测验卡片题目缺少 id 时不产生提交按钮", () => {
    expect(
      kinds(cardOf("quiz_card", { questions: [{ stem: "题目" }] })),
    ).toEqual([]);
  });

  it("错题卡片缺少复习任务标识时不产生按钮", () => {
    expect(kinds(cardOf("mistake_card"))).toEqual([]);
  });

  it("讲解卡片与失败卡片没有写操作", () => {
    expect(kinds(cardOf("lesson_card"))).toEqual([]);
    expect(kinds(cardOf("error_card"))).toEqual([]);
  });
});

describe("getCardActionSpecs：真实动作与确认闸口", () => {
  it("今日任务：开始学习无需确认，标记完成必须确认", () => {
    const specs = getCardActionSpecs(cardOf("task_card", { task_id: "task-1" }));
    expect(specs.map((spec) => spec.kind)).toEqual([
      "start_task",
      "complete_task",
    ]);
    expect(specs[0].confirm).toBeNull();
    expect(specs[1].confirm).toContain("确定");
    expect(specs.every((spec) => spec.targetId === "task-1")).toBe(true);
    expect(specs.every((spec) => spec.write)).toBe(true);
  });

  it("任务已完成的卡片不再提供重复写操作", () => {
    expect(
      kinds(cardOf("task_card", { task_id: "task-1", status: "completed" })),
    ).toEqual([]);
  });

  it("学习计划：确认计划必须二次确认", () => {
    const specs = getCardActionSpecs(cardOf("plan_card"));
    expect(specs.map((spec) => spec.kind)).toEqual(["confirm_plan"]);
    expect(specs[0].targetId).toBe("plan-1");
    expect(specs[0].confirm).toContain("生效");
  });

  it("已确认的计划不再提供确认按钮", () => {
    expect(kinds(cardOf("plan_card", { status: "confirmed" }))).toEqual([]);
  });

  it("计划调整：确认与放弃都必须二次确认，且共用真实 proposal_id", () => {
    const specs = getCardActionSpecs(cardOf("plan_change_card"));
    expect(specs.map((spec) => spec.kind)).toEqual([
      "confirm_proposal",
      "reject_proposal",
    ]);
    expect(specs.every((spec) => spec.targetId === "proposal-1")).toBe(true);
    expect(specs.every((spec) => spec.confirm)).toBe(true);
  });

  it("已处理或明确无需确认的调整提案不再产生按钮", () => {
    expect(
      kinds(cardOf("plan_change_card", { status: "confirmed" })),
    ).toEqual([]);
    expect(
      kinds(
        cardOf("plan_change_card", { requires_confirmation: false }),
      ),
    ).toEqual([]);
  });

  it("测验卡片：提交按钮要求确认且绑定真实 attempt_id", () => {
    const specs = getCardActionSpecs(cardOf("quiz_card"));
    expect(specs.map((spec) => spec.kind)).toEqual(["submit_quiz"]);
    expect(specs[0].targetId).toBe("attempt-1");
    expect(specs[0].confirm).toContain("评分");
  });

  it("错题卡片：复习提交绑定真实复习任务标识", () => {
    const specs = getCardActionSpecs(
      cardOf("mistake_card", { review_task_id: "review-1" }),
    );
    expect(specs.map((spec) => spec.kind)).toEqual(["submit_review"]);
    expect(specs[0].targetId).toBe("review-1");
  });

  it("结果卡与进度卡只提供只读刷新按钮", () => {
    const result = getCardActionSpecs(cardOf("quiz_result_card"));
    expect(result.map((spec) => spec.kind)).toEqual(["refresh_quiz"]);
    expect(result[0].write).toBe(false);
    expect(result[0].confirm).toBeNull();

    const progress = getCardActionSpecs(cardOf("progress_card"));
    expect(progress.map((spec) => spec.kind)).toEqual(["refresh_progress"]);
    expect(progress[0].write).toBe(false);
    expect(progress[0].targetId).toBeNull();
  });

  it("所有动作成功后都会刷新右侧真实业务面板", () => {
    const cards: CardType[] = [
      "task_card",
      "plan_card",
      "plan_change_card",
      "quiz_card",
      "mistake_card",
      "quiz_result_card",
      "progress_card",
    ];
    for (const type of cards) {
      const extra: Record<string, unknown> = {};
      if (type === "task_card") extra.task_id = "task-1";
      if (type === "mistake_card") extra.review_task_id = "review-1";
      const specs = getCardActionSpecs(cardOf(type, extra));
      expect(specs.length).toBeGreaterThan(0);
      expect(specs.every((spec) => spec.refreshPanels)).toBe(true);
    }
  });
});

describe("readQuizQuestions 与答案构造", () => {
  it("只提取有 id 的题目，不读取答案与解析字段", () => {
    const questions = readQuizQuestions(cardOf("quiz_card"));
    expect(questions).toHaveLength(1);
    expect(questions[0].questionId).toBe("q1");
    expect(questions[0].options).toEqual([
      { key: "A", text: "age = 18" },
      { key: "B", text: "18 = age" },
    ]);
    expect(JSON.stringify(questions)).not.toContain("correct_answer");
    expect(JSON.stringify(questions)).not.toContain("explanation");
  });

  it("未完成全部题目时答案为 null", () => {
    const questions = readQuizQuestions(cardOf("quiz_card"));
    expect(buildQuizAnswers(questions, {})).toBeNull();
    expect(buildQuizAnswers(questions, { q1: "  " })).toBeNull();
    expect(buildQuizAnswers(questions, { q1: "A" })).toEqual([
      { question_id: "q1", answer: "A" },
    ]);
  });

  it("按题型判定答案是否已填写", () => {
    expect(isAnswerFilled("single_choice", "A")).toBe(true);
    expect(isAnswerFilled("multiple_choice", ["A"])).toBe(true);
    expect(isAnswerFilled("multiple_choice", [])).toBe(false);
    expect(isAnswerFilled("true_false", false)).toBe(true);
    expect(isAnswerFilled("true_false", "false")).toBe(false);
    expect(isAnswerFilled("short_answer", "  ")).toBe(false);
  });
});
