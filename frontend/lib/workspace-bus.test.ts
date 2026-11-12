import { afterEach, describe, expect, it, vi } from "vitest";

import {
  parseWorkspaceEvent,
  publishWorkspaceEvent,
  subscribeWorkspaceEvent,
  WORKSPACE_EVENT_NAME,
} from "@/lib/workspace-bus";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("窗口内事件总线", () => {
  it("接受五类结构完整的事件", () => {
    expect(parseWorkspaceEvent({ type: "conversation:new" })).toEqual({
      type: "conversation:new",
    });
    expect(parseWorkspaceEvent({ type: "conversation:select", id: "c1" })).toEqual({
      type: "conversation:select",
      id: "c1",
    });
    expect(parseWorkspaceEvent({ type: "panels:refresh" })).toEqual({
      type: "panels:refresh",
    });
  });

  it("拒绝未知类型、缺失 id 与非对象载荷", () => {
    expect(parseWorkspaceEvent(null)).toBeNull();
    expect(parseWorkspaceEvent("conversation:new")).toBeNull();
    expect(parseWorkspaceEvent({ type: "unknown" })).toBeNull();
    expect(parseWorkspaceEvent({ type: "conversation:select" })).toBeNull();
    expect(
      parseWorkspaceEvent({ type: "conversation:deleted", id: "" }),
    ).toBeNull();
  });

  it("发布后订阅者只收到校验通过的事件，取消订阅后不再收到", () => {
    const received: string[] = [];
    const unsubscribe = subscribeWorkspaceEvent((event) => {
      received.push(event.type);
    });

    expect(publishWorkspaceEvent({ type: "conversation:new" })).toBe(true);
    expect(publishWorkspaceEvent({ type: "panels:refresh" })).toBe(true);
    // 畸形事件直接经 window 派发，订阅端必须丢弃
    window.dispatchEvent(
      new CustomEvent(WORKSPACE_EVENT_NAME, { detail: { type: "inject" } }),
    );
    expect(received).toEqual(["conversation:new", "panels:refresh"]);

    unsubscribe();
    publishWorkspaceEvent({ type: "conversation:changed" });
    expect(received).toHaveLength(2);
  });
});
