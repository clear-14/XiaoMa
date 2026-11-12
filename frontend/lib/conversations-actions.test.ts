/**
 * V1.4 批次 5：停止生成 / 重新生成 API 封装测试。
 * 验证请求路径、请求体与响应解析都与后端契约一致。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { regenerateMessage, stopGeneration } from "@/lib/conversations";

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("stopGeneration", () => {
  it("调用真实停止接口且不带请求体", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ conversation_id: "c1", stopped: true }),
    );
    const result = await stopGeneration("c1");
    expect(result).toEqual({ conversation_id: "c1", stopped: true });
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain(
      "/api/v1/conversations/c1/messages/stop",
    );
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeUndefined();
  });

  it("无进行中生成时原样返回幂等结果 stopped=false", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ conversation_id: "c1", stopped: false }),
    );
    await expect(stopGeneration("c1")).resolves.toMatchObject({
      stopped: false,
    });
  });
});

describe("regenerateMessage", () => {
  it("把真实 message_id 送到重新生成接口并解析新助手消息", async () => {
    const message = {
      id: "a2",
      conversation_id: "c1",
      role: "assistant",
      content: "重新生成的回复",
      status: "completed",
      error_message: null,
      model_name: null,
      created_at: "2026-11-09T10:00:00",
      message_type: "text",
      structured_data: null,
      card_version: null,
    };
    fetchMock.mockResolvedValue(jsonResponse(message));

    const result = await regenerateMessage("c1", "a1");
    expect(result.id).toBe("a2");
    expect(result.content).toBe("重新生成的回复");

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain(
      "/api/v1/conversations/c1/messages/regenerate",
    );
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ message_id: "a1" });
  });

  it("后端拒绝卡片消息时错误向上抛出，不吞异常", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "仅普通文本回复支持重新生成" }, 422),
    );
    await expect(regenerateMessage("c1", "a1")).rejects.toThrow();
  });
});
