/**
 * V1.4 批次 5：对话工作台消息级操作组件测试。
 *
 * 覆盖复制、重新生成、停止生成三个操作的接线，重点验证「停止生成只调
 * REST 置位、不主动 abort SSE」，以及卡片消息不渲染必然 422 的重生成按钮。
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getConversation,
  listConversations,
  regenerateMessage,
  stopGeneration,
  streamMessage,
} from "@/lib/conversations";
import { validEnvelope } from "@/lib/card-test-fixtures";

import WorkspaceClient from "./WorkspaceClient";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("conversation_id=c1"),
}));

vi.mock("@/lib/conversations", () => ({
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  renameConversation: vi.fn(),
  streamMessage: vi.fn(),
  stopGeneration: vi.fn(),
  regenerateMessage: vi.fn(),
}));

vi.mock("@/lib/learning", () => ({
  getTaskDetail: vi.fn(),
  getKnowledgePoint: vi.fn(),
}));

const STAMP = "2026-11-09T10:00:00";

function detail(messages: Record<string, unknown>[] = []) {
  return {
    id: "c1",
    title: "测试会话",
    knowledge_point: null,
    daily_task_id: null,
    message_count: messages.length,
    last_activity_at: STAMP,
    created_at: STAMP,
    updated_at: STAMP,
    messages,
  };
}

function userMessage() {
  return {
    id: "u1",
    conversation_id: "c1",
    role: "user",
    content: "你好",
    status: "completed",
    error_message: null,
    model_name: null,
    created_at: STAMP,
    message_type: "text",
    structured_data: null,
    card_version: null,
  };
}

function assistantMessage(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    id: "a1",
    conversation_id: "c1",
    role: "assistant",
    content: "回复内容",
    status: "completed",
    error_message: null,
    model_name: null,
    created_at: STAMP,
    message_type: "text",
    structured_data: null,
    card_version: null,
    ...overrides,
  };
}

let clipboardWrite: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
  clipboardWrite = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: clipboardWrite },
  });
  vi.mocked(listConversations).mockResolvedValue([]);
  vi.mocked(getConversation).mockResolvedValue(
    detail([userMessage(), assistantMessage()]) as never,
  );
  vi.mocked(streamMessage).mockResolvedValue(undefined);
  vi.mocked(stopGeneration).mockResolvedValue({
    conversation_id: "c1",
    stopped: true,
  });
  vi.mocked(regenerateMessage).mockResolvedValue(
    assistantMessage({ id: "a2", content: "新的回复" }) as never,
  );
});

async function renderWorkspace() {
  render(<WorkspaceClient />);
  await waitFor(() => {
    expect(screen.getByText("回复内容")).toBeInTheDocument();
  });
}

describe("复制与重新生成", () => {
  it("普通文本助手消息提供重新生成，用户消息不提供", async () => {
    await renderWorkspace();
    expect(
      screen.getAllByRole("button", { name: "复制" }),
    ).toHaveLength(2);
    expect(
      screen.getAllByRole("button", { name: "重新生成" }),
    ).toHaveLength(1);
  });

  it("点击重新生成调用真实接口并重新拉取会话详情", async () => {
    await renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    await waitFor(() => {
      expect(regenerateMessage).toHaveBeenCalledWith("c1", "a1");
    });
    await waitFor(() => {
      expect(getConversation).toHaveBeenCalledTimes(2);
    });
  });

  it("点击复制写入消息文本并展示已复制", async () => {
    await renderWorkspace();
    fireEvent.click(screen.getAllByRole("button", { name: "复制" })[0]);
    await waitFor(() => {
      expect(clipboardWrite).toHaveBeenCalledWith("你好");
    });
    expect(screen.getByRole("button", { name: "已复制" })).toBeInTheDocument();
  });

  it("卡片消息不渲染重新生成按钮（后端会返回 422）", async () => {
    vi.mocked(getConversation).mockResolvedValue(
      detail([
        userMessage(),
        assistantMessage({
          message_type: "lesson_card",
          structured_data: {
            card_version: "v1",
            type: "lesson_card",
            cards: [validEnvelope("lesson_card")],
          },
          card_version: "v1",
        }),
      ]) as never,
    );
    await renderWorkspace();
    expect(screen.queryByRole("button", { name: "重新生成" })).toBeNull();
  });
});

describe("停止生成", () => {
  it("只调用后端停止接口，不主动断开 SSE 连接", async () => {
    let capturedSignal: AbortSignal | undefined;
    vi.mocked(streamMessage).mockImplementation(
      (_id, _content, _handlers, signal) => {
        capturedSignal = signal;
        // 模拟尚未结束的流：保持 pending，让停止按钮保持可见。
        return new Promise<void>(() => undefined);
      },
    );
    await renderWorkspace();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "继续讲解" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    const stopButton = await screen.findByRole("button", {
      name: "停止生成",
    });
    fireEvent.click(stopButton);

    await waitFor(() => {
      expect(stopGeneration).toHaveBeenCalledWith("c1");
    });
    expect(capturedSignal?.aborted).toBe(false);
    expect(streamMessage).toHaveBeenCalledOnce();
  });
});
