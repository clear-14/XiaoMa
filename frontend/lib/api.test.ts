import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_STORAGE_KEY,
  UNAUTHORIZED_EVENT,
  getAccessToken,
  setAccessToken,
} from "@/lib/access-token";
import { ApiError, api, streamApi } from "@/lib/api";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api 请求封装", () => {
  it("使用同源 /api/v1 并在登录后携带 Bearer 令牌", async () => {
    setAccessToken("test-token");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify([{ code: "python-basics" }]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const data = await api.get<{ code: string }[]>("/courses");

    expect(data).toEqual([{ code: "python-basics" }]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/courses");
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token");
  });

  it("把后端统一错误结构转换为 ApiError 提示", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "学习计划尚未确认" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(api.get("/daily-tasks/today")).rejects.toMatchObject({
      status: 409,
      message: "学习计划尚未确认",
    });
  });

  it("收到 401 时清除本地令牌并广播未授权事件", async () => {
    setAccessToken("expired-token");
    const onUnauthorized = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "需要访问密码登录" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(api.get("/profile")).rejects.toBeInstanceOf(ApiError);

    expect(getAccessToken()).toBeNull();
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  });
});

describe("SSE 流解析", () => {
  it("按事件名交付 start / delta / done 数据", async () => {
    const body = [
      'event: start\ndata: {"conversation_id":"c1"}',
      'event: delta\ndata: {"text":"你" }',
      'event: delta\ndata: {"text":"好" }',
      'event: done\ndata: {"conversation_id":"c1"}',
      "",
    ].join("\n\n");
    fetchMock.mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const events: { event: string; data: unknown }[] = [];

    await streamApi("/conversations/c1/messages/stream", { content: "hi" }, (event) =>
      events.push(event),
    );

    expect(events.map((item) => item.event)).toEqual([
      "start",
      "delta",
      "delta",
      "done",
    ]);
    expect(events[1].data).toEqual({ text: "你" });
  });

  it("HTTP 错误在流开始前抛出 ApiError", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "尚未配置默认模型" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      streamApi("/conversations/c1/messages/stream", { content: "hi" }, () => {}),
    ).rejects.toMatchObject({ status: 409, message: "尚未配置默认模型" });
  });
});
