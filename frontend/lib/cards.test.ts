/**
 * V1.4 批次 4：卡片协议纯函数单测。
 *
 * 覆盖任务书阶段 5 的四条硬要求：TypeScript 类型定义、structured_data
 * 校验、协议版本、未识别类型安全降级；以及「流式未完成时不能渲染不完整
 * 卡片」——任何缺字段帧都收敛为明确展示失败的 error_card。
 */

import { describe, expect, it } from "vitest";

import { VALID_PAYLOADS, validEnvelope } from "./card-test-fixtures";
import {
  CARD_FIELD_RULES,
  CARD_TYPES,
  CARD_VERSION,
  MESSAGE_TYPES,
  buildErrorCard,
  cardsFromStructuredData,
  formatValue,
  normalizeCard,
  readBoolean,
  readNumber,
  readObjectArray,
  readString,
  readStringArray,
  validateCardPayload,
} from "./cards";

describe("卡片协议常量", () => {
  it("10 类消息类型 = 9 类卡片 + text 文本通道", () => {
    expect(MESSAGE_TYPES).toHaveLength(10);
    expect(CARD_TYPES).toHaveLength(9);
    expect(MESSAGE_TYPES[0]).toBe("text");
    expect(MESSAGE_TYPES.slice(1)).toEqual([...CARD_TYPES]);
    expect(CARD_TYPES).toContain("error_card");
  });

  it("字段表逐类覆盖且每类至少一个必备字段", () => {
    expect(Object.keys(CARD_FIELD_RULES).sort()).toEqual([...CARD_TYPES].sort());
    for (const type of CARD_TYPES) {
      expect(Object.keys(CARD_FIELD_RULES[type]).length).toBeGreaterThan(0);
      expect(validateCardPayload(type, VALID_PAYLOADS[type])).toBeNull();
    }
  });
});

describe("normalizeCard 语义校验与降级", () => {
  it("9 类合法卡片原样通过，保留可选增强字段", () => {
    for (const type of CARD_TYPES) {
      const enriched = { ...validEnvelope(type), payload: { ...VALID_PAYLOADS[type], chapter_title: "第 1 章" } };
      const card = normalizeCard(enriched);
      expect(card.type).toBe(type);
      expect(card.card_version).toBe(CARD_VERSION);
      expect((card.payload as Record<string, unknown>).chapter_title).toBe("第 1 章");
    }
  });

  it("非对象、未知版本、未知类型、payload 非对象一律降级 error_card", () => {
    const cases: unknown[] = [
      null,
      "not a card",
      42,
      [],
      { ...validEnvelope("task_card"), card_version: "v2" },
      { ...validEnvelope("task_card"), card_version: "" },
      { ...validEnvelope("task_card"), type: "unknown_card" },
      { ...validEnvelope("task_card"), payload: null },
      { ...validEnvelope("task_card"), payload: "text" },
      { ...validEnvelope("task_card"), payload: [] },
    ];
    for (const raw of cases) {
      const card = normalizeCard(raw);
      expect(card.type).toBe("error_card");
      expect(typeof card.payload.reason).toBe("string");
      expect(String(card.payload.reason).length).toBeGreaterThan(0);
    }
  });

  it("缺必备字段或字段类型不对时明确写出原因，不渲染半成品", () => {
    const missing = normalizeCard({
      card_version: CARD_VERSION,
      type: "task_card",
      payload: { title: "变量" },
    });
    expect(missing.type).toBe("error_card");
    expect(missing.payload.reason).toContain("字段");

    const wrongType = normalizeCard({
      card_version: CARD_VERSION,
      type: "task_card",
      payload: { ...VALID_PAYLOADS.task_card, estimated_minutes: "30" },
    });
    expect(wrongType.type).toBe("error_card");
    expect(wrongType.payload.reason).toContain("estimated_minutes");
  });

  it("空白字符串与 NaN / 布尔伪数字不算合法字段", () => {
    expect(
      normalizeCard({
        card_version: CARD_VERSION,
        type: "lesson_card",
        payload: { ...VALID_PAYLOADS.lesson_card, explanation: "   " },
      }).type,
    ).toBe("error_card");
    expect(
      normalizeCard({
        card_version: CARD_VERSION,
        type: "progress_card",
        payload: { ...VALID_PAYLOADS.progress_card, mastered_count: Number.NaN },
      }).type,
    ).toBe("error_card");
    expect(
      normalizeCard({
        card_version: CARD_VERSION,
        type: "progress_card",
        payload: { ...VALID_PAYLOADS.progress_card, mastered_count: true },
      }).type,
    ).toBe("error_card");
  });

  it("0 分是合法结果，不被当成字段缺失", () => {
    const card = normalizeCard({
      card_version: CARD_VERSION,
      type: "quiz_result_card",
      payload: { attempt_id: "a1", score: 0, total_points: 10 },
    });
    expect(card.type).toBe("quiz_result_card");
  });

  it("buildErrorCard 本身是合法 v1 卡片", () => {
    const card = buildErrorCard("降级");
    expect(normalizeCard(card)).toEqual(card);
  });
});

describe("cardsFromStructuredData 刷新恢复", () => {
  it("null / undefined 表示普通文本消息，返回空数组", () => {
    expect(cardsFromStructuredData(null)).toEqual([]);
    expect(cardsFromStructuredData(undefined)).toEqual([]);
  });

  it("卡片集合按序恢复，单张降级不影响其余卡片", () => {
    const raw = {
      card_version: CARD_VERSION,
      type: "task_card",
      cards: [validEnvelope("task_card"), { type: "v9-card" }, validEnvelope("progress_card")],
    };
    const cards = cardsFromStructuredData(raw);
    expect(cards.map((card) => card.type)).toEqual([
      "task_card",
      "error_card",
      "progress_card",
    ]);
  });

  it("兼容单卡片对象；cards 非数组或数据非对象时降级", () => {
    expect(cardsFromStructuredData(validEnvelope("plan_card")).map((c) => c.type)).toEqual([
      "plan_card",
    ]);
    expect(cardsFromStructuredData({ cards: "oops" })[0].type).toBe("error_card");
    expect(cardsFromStructuredData("oops")[0].type).toBe("error_card");
  });
});

describe("可选字段安全读取", () => {
  const payload = {
    title: "  变量  ",
    blank: "   ",
    count: 0,
    bad: "3",
    flag: false,
    items: [{ a: 1 }, "skip", null],
    tags: ["a", 1, "b"],
    nested: { x: 1 },
  };

  it("只接受真实类型的可选值", () => {
    expect(readString(payload, "title")).toBe("  变量  ");
    expect(readString(payload, "blank")).toBeNull();
    expect(readNumber(payload, "count")).toBe(0);
    expect(readNumber(payload, "bad")).toBeNull();
    expect(readBoolean(payload, "flag")).toBe(false);
    expect(readBoolean(payload, "bad")).toBeNull();
    expect(readObjectArray(payload, "items")).toEqual([{ a: 1 }]);
    expect(readStringArray(payload, "tags")).toEqual(["a", "b"]);
  });

  it("formatValue 不把对象展开成 JSON", () => {
    expect(formatValue(payload.nested)).toBe("—");
    expect(formatValue([1, "a", null])).toBe("1、a");
    expect(formatValue(true)).toBe("是");
    expect(formatValue(undefined)).toBe("—");
  });
});
