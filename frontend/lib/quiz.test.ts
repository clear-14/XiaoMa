import { describe, expect, it } from "vitest";

import {
  correctAnswerValue,
  formatAnswer,
  isAnswerEmpty,
  questionTypeLabel,
  scopeTypeLabel,
} from "@/lib/quiz";
import type { QuizQuestion } from "@/lib/types";

function question(overrides: Partial<QuizQuestion>): QuizQuestion {
  return {
    id: "q1",
    order: 1,
    question_type: "single_choice",
    stem: "题干",
    options: [
      { key: "A", text: "选项 A" },
      { key: "B", text: "选项 B" },
    ],
    points: 10,
    source: "builtin",
    knowledge_point: {
      code: "kp",
      name: "知识点",
      chapter_code: "ch",
      chapter_title: "章节",
    },
    user_answer: null,
    correct_answer: { value: "A" },
    explanation: null,
    score: null,
    max_score: 10,
    is_correct: null,
    grading_basis: null,
    ...overrides,
  };
}

describe("测验前端辅助逻辑", () => {
  it("各类题型的空答案判定", () => {
    expect(isAnswerEmpty(question({}), "")).toBe(true);
    expect(isAnswerEmpty(question({}), "A")).toBe(false);
    expect(
      isAnswerEmpty(question({ question_type: "multiple_choice" }), []),
    ).toBe(true);
    expect(
      isAnswerEmpty(question({ question_type: "multiple_choice" }), ["A"]),
    ).toBe(false);
    expect(isAnswerEmpty(question({ question_type: "true_false" }), false)).toBe(
      false,
    );
    expect(isAnswerEmpty(question({ question_type: "true_false" }), null)).toBe(
      true,
    );
  });

  it("选择题答案展示为选项 key + 文本", () => {
    expect(formatAnswer(question({}), ["A", "B"])).toBe(
      "A. 选项 A；B. 选项 B",
    );
  });

  it("判断题与未作答展示", () => {
    expect(
      formatAnswer(question({ question_type: "true_false" }), true),
    ).toBe("正确（True）");
    expect(formatAnswer(question({}), null)).toBe("（未作答）");
  });

  it("正确答结构提取与标签回退", () => {
    expect(correctAnswerValue(question({}))).toBe("A");
    expect(
      correctAnswerValue(
        question({ correct_answer: { values: ["A", "B"] } }),
      ),
    ).toEqual(["A", "B"]);
    expect(questionTypeLabel("single_choice")).toBe("单选题");
    expect(questionTypeLabel("unknown")).toBe("unknown");
    expect(scopeTypeLabel("chapter")).toBe("章节测验");
  });
});
