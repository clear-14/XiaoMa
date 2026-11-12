/**
 * V1.4 批次 4：SSE `card` 帧语义解析层单测。
 *
 * 两级边界（与 lib/conversations.ts 的传输层 isCardFrame 互补）：
 * - 帧级不完整 → 返回 null，调用方丢弃，不渲染半成品；
 * - 卡片内容不合法 → 返回 card=error_card 的已解析帧，界面明确展示失败。
 */

import { describe, expect, it } from "vitest";

import { parseCardFrame } from "./card-events";
import { CARD_VERSION, VALID_TASK_PAYLOAD } from "./card-test-fixtures";

const FULL_FRAME = {
  conversation_id: "conv-1",
  message_id: "msg-1",
  card_version: CARD_VERSION,
  message_type: "task_card",
  structured_data: {
    card_version: CARD_VERSION,
    type: "task_card",
    payload: VALID_TASK_PAYLOAD,
  },
};

describe("parseCardFrame 帧级完整性", () => {
  it("完整帧解析出会话 / 消息 / 类型与已校验卡片", () => {
    const parsed = parseCardFrame(FULL_FRAME);
    expect(parsed).not.toBeNull();
    expect(parsed?.conversationId).toBe("conv-1");
    expect(parsed?.messageId).toBe("msg-1");
    expect(parsed?.cardVersion).toBe(CARD_VERSION);
    expect(parsed?.messageType).toBe("task_card");
    expect(parsed?.card.type).toBe("task_card");
  });

  it("message_id 缺失或不是字符串时降级为 null，不伪造消息归属", () => {
    expect(parseCardFrame({ ...FULL_FRAME, message_id: undefined })?.messageId).toBeNull();
    expect(parseCardFrame({ ...FULL_FRAME, message_id: 123 })?.messageId).toBeNull();
  });

  it("帧级字段缺失 / 类型错误一律丢弃，返回 null", () => {
    const cases: unknown[] = [
      null,
      [],
      "frame",
      { ...FULL_FRAME, conversation_id: 123 },
      { ...FULL_FRAME, conversation_id: "  " },
      { ...FULL_FRAME, card_version: undefined },
      { ...FULL_FRAME, card_version: 1 },
      { ...FULL_FRAME, message_type: "" },
      { ...FULL_FRAME, structured_data: null },
      { ...FULL_FRAME, structured_data: "half-json" },
      { ...FULL_FRAME, structured_data: [] },
    ];
    for (const raw of cases) {
      expect(parseCardFrame(raw)).toBeNull();
    }
  });
});

describe("parseCardFrame 卡片语义降级", () => {
  it("未知协议版本降级为 error_card 且保留帧归属", () => {
    const parsed = parseCardFrame({
      ...FULL_FRAME,
      structured_data: { ...FULL_FRAME.structured_data, card_version: "v9" },
    });
    expect(parsed).not.toBeNull();
    expect(parsed?.card.type).toBe("error_card");
    expect(String(parsed?.card.payload.reason)).toContain("版本");
    expect(parsed?.conversationId).toBe("conv-1");
  });

  it("未知类型与缺必备字段降级为 error_card，不返回 null", () => {
    const unknownType = parseCardFrame({
      ...FULL_FRAME,
      structured_data: { ...FULL_FRAME.structured_data, type: "future_card" },
    });
    expect(unknownType?.card.type).toBe("error_card");

    const missingField = parseCardFrame({
      ...FULL_FRAME,
      structured_data: {
        card_version: CARD_VERSION,
        type: "task_card",
        payload: { title: "只有标题" },
      },
    });
    expect(missingField?.card.type).toBe("error_card");
    expect(String(missingField?.card.payload.reason)).toContain("字段");
  });

  it("帧上 message_type 与卡片真实 type 不一致时，以结构化数据为准", () => {
    const parsed = parseCardFrame({ ...FULL_FRAME, message_type: "lesson_card" });
    expect(parsed?.messageType).toBe("lesson_card");
    expect(parsed?.card.type).toBe("task_card");
  });
});
