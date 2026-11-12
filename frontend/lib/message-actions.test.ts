/** V1.4 批次 5：消息级操作判定纯函数测试。 */

import { describe, expect, it } from "vitest";

import { normalizeCard } from "@/lib/cards";
import { validEnvelope } from "@/lib/card-test-fixtures";
import {
  canCopyMessage,
  canRegenerateMessage,
  type MessageActionTarget,
} from "@/lib/message-actions";

function target(
  overrides: Partial<MessageActionTarget> = {},
): MessageActionTarget {
  return {
    role: "assistant",
    status: "completed",
    content: "回复内容",
    messageId: "real-message-id",
    cards: [],
    ...overrides,
  };
}

describe("canRegenerateMessage", () => {
  it("已落库的普通文本助手消息可以重新生成", () => {
    expect(canRegenerateMessage(target())).toBe(true);
    expect(canRegenerateMessage(target({ status: "stopped" }))).toBe(true);
  });

  it("用户消息、生成中消息、无真实 ID 的本地消息都不可重新生成", () => {
    expect(canRegenerateMessage(target({ role: "user" }))).toBe(false);
    expect(canRegenerateMessage(target({ status: "streaming" }))).toBe(false);
    expect(canRegenerateMessage(target({ messageId: null }))).toBe(false);
  });

  it("卡片消息与失败回复不渲染必然 422 的重新生成按钮", () => {
    const card = normalizeCard(validEnvelope("task_card"));
    expect(canRegenerateMessage(target({ cards: [card] }))).toBe(false);
    expect(canRegenerateMessage(target({ status: "error" }))).toBe(false);
  });
});

describe("canCopyMessage", () => {
  it("只有实际文本才提供复制", () => {
    expect(canCopyMessage(target())).toBe(true);
    expect(canCopyMessage(target({ content: "   " }))).toBe(false);
    expect(canCopyMessage(target({ content: "" }))).toBe(false);
  });
});
