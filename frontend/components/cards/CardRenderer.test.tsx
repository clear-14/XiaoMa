/**
 * V1.4 批次 4：卡片渲染分发器单测。
 *
 * 覆盖 10 类消息类型的分发口径（9 类卡片 + text 文本通道）、
 * 未知类型安全降级、actions 插槽、确认闸、题目卡不泄露答案，
 * 以及可访问性语义与窄屏不溢出的结构性保障。
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VALID_PAYLOADS, validEnvelope } from "@/lib/card-test-fixtures";
import {
  CARD_TYPES,
  CARD_TYPE_LABELS,
  MESSAGE_TYPES,
  normalizeCard,
  type Card,
  type CardType,
} from "@/lib/cards";

import CardRenderer from "./CardRenderer";

function cardOf(type: CardType): Card {
  return normalizeCard(validEnvelope(type));
}

describe("CardRenderer 九类卡片分发", () => {
  for (const type of CARD_TYPES) {
    it(`按判别联合渲染 ${type}，带类型标与可访问标签`, () => {
      render(<CardRenderer cards={[cardOf(type)]} />);
      const el = document.querySelector(`[data-card-type="${type}"]`);
      expect(el).not.toBeNull();
      expect(el?.getAttribute("role")).toBe("group");
      expect(el?.getAttribute("aria-label")).toContain(CARD_TYPE_LABELS[type]);
    });
  }

  it("10 类消息类型口径：9 类卡片 + text 文本通道", () => {
    expect(MESSAGE_TYPES).toHaveLength(10);
    expect(CARD_TYPES).toHaveLength(9);
    expect(MESSAGE_TYPES[0]).toBe("text");
  });

  it("一条消息可携带多张卡片，按 80ms 错峰入场", () => {
    render(
      <CardRenderer cards={[cardOf("task_card"), cardOf("progress_card"), cardOf("error_card")]} />,
    );
    expect(document.querySelectorAll("[data-card-type]")).toHaveLength(3);
    const styles = [...document.querySelectorAll<HTMLElement>(".win-card")].map(
      (el) => el.style.animationDelay,
    );
    expect(styles).toEqual(["0ms", "80ms", "160ms"]);
    expect(screen.getByRole("list", { name: "结构化业务卡片" })).toBeInTheDocument();
    expect(document.querySelectorAll('[role="listitem"]')).toHaveLength(3);
  });

  it("空卡片集合不渲染任何内容", () => {
    const { container } = render(<CardRenderer cards={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("卡片来源标注明确，不由对话内容推断", () => {
    render(<CardRenderer cards={[cardOf("task_card")]} />);
    expect(
      screen.getByText("卡片数据来自后端业务结果，不由对话内容推断。"),
    ).toBeInTheDocument();
  });
});

describe("CardRenderer 降级与闸口", () => {
  it("运行时未知类型降级为 error_card，明确展示失败而非空白", () => {
    const dirty = {
      card_version: "v1",
      type: "future_card",
      payload: {},
    } as unknown as Card;
    render(<CardRenderer cards={[dirty]} />);
    expect(document.querySelector('[data-card-type="error_card"]')).not.toBeNull();
    expect(screen.getByText("不支持的卡片类型")).toBeInTheDocument();
  });

  it("error_card 展示失败原因与降级标识", () => {
    render(<CardRenderer cards={[cardOf("error_card")]} />);
    expect(screen.getByText(VALID_PAYLOADS.error_card.reason as string)).toBeInTheDocument();
    expect(screen.getByText("降级展示")).toBeInTheDocument();
  });

  it("计划调整卡片显示「需确认」闸口，且不自动渲染确认按钮", () => {
    render(<CardRenderer cards={[cardOf("plan_change_card")]} />);
    expect(screen.getByRole("note")).toHaveTextContent("需你确认后才会保存");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("题目卡不展示正确答案与解析（评分只由后端给出）", () => {
    const quiz = normalizeCard(
      validEnvelope("quiz_card", {
        questions: [
          {
            id: "q1",
            stem: "下面哪个是变量？",
            question_type: "single_choice",
            correct_answer: "SECRET_ANSWER_VALUE",
            explanation: "SECRET_EXPLANATION_VALUE",
          },
        ],
      }),
    );
    render(<CardRenderer cards={[quiz]} />);
    expect(screen.queryByText(/SECRET_ANSWER_VALUE/)).toBeNull();
    expect(screen.queryByText(/SECRET_EXPLANATION_VALUE/)).toBeNull();
    expect(screen.getByText("提交后由后端统一评分")).toBeInTheDocument();
  });
});

describe("CardRenderer actions 插槽（批次 5 接线点）", () => {
  it("注入回调时渲染真实业务按钮，且按钮位于卡片操作区", () => {
    render(
      <CardRenderer
        cards={[cardOf("task_card")]}
        renderActions={(card) =>
          card.type === "task_card" ? <button type="button">开始学习</button> : null
        }
      />,
    );
    expect(screen.getByRole("button", { name: "开始学习" })).toBeInTheDocument();
    expect(document.querySelector(".win-card-actions")).not.toBeNull();
  });

  it("未注入回调时不产生任何假按钮", () => {
    render(<CardRenderer cards={[cardOf("quiz_card"), cardOf("plan_card")]} />);
    expect(screen.queryByRole("button")).toBeNull();
    expect(document.querySelector(".win-card-actions")).toBeNull();
  });
});
