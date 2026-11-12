import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { streamMessage } from "@/lib/conversations";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AI 教学会话流", () => {
  it("把 SSE 事件分发给 start / delta / done 回调", async () => {
    const body = [
      'event: start\ndata: {"conversation_id":"c1","message_id":"m1","intent":"teaching"}',
      'event: delta\ndata: {"text":"变量" }',
      'event: delta\ndata: {"text":"是什么" }',
      'event: done\ndata: {"conversation_id":"c1","message_id":"m1","result_status":"ok"}',
      "",
    ].join("\n\n");
    fetchMock.mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const starts: unknown[] = [];
    const deltas: string[] = [];
    const dones: unknown[] = [];

    await streamMessage(
      "c1",
      "解释变量",
      {
        onStart: (info) => starts.push(info),
        onDelta: (text) => deltas.push(text),
        onDone: (info) => dones.push(info),
      },
      new AbortController().signal,
    );

    expect(starts).toHaveLength(1);
    expect(deltas).toEqual(["变量", "是什么"]);
    expect(dones).toHaveLength(1);
  });

  it("error 事件转为 onError 回调而不是抛异常", async () => {
    const body = [
      'event: start\ndata: {"conversation_id":"c1"}',
      'event: error\ndata: {"conversation_id":"c1","message_id":null,"message":"模型调用失败"}',
      "",
    ].join("\n\n");
    fetchMock.mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const errors: string[] = [];

    await streamMessage("c1", "解释变量", {
      onError: (info) => errors.push(info.message),
    });

    expect(errors).toEqual(["模型调用失败"]);
  });

  it("V1.4 card 事件只把完整卡片帧交给回调，半成品 JSON 不渲染", async () => {
    const complete = {
      card_version: "v1",
      type: "task_card",
      payload: { title: "今日任务" },
    };
    const body = [
      'event: start\ndata: {"conversation_id":"c1","message_id":"m1"}',
      `event: card\ndata: ${JSON.stringify({
        conversation_id: "c1",
        message_id: "m1",
        card_version: "v1",
        message_type: "task_card",
        structured_data: complete,
      })}`,
      // 缺 payload，属于未完成帧，必须被丢弃
      'event: card\ndata: {"conversation_id":"c1","message_id":"m1","card_version":"v1","message_type":"task_card","structured_data":{"card_version":"v1","type":"task_card"}}',
      'event: done\ndata: {"conversation_id":"c1","message_id":"m1"}',
      "",
    ].join("\n\n");
    fetchMock.mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const cards: unknown[] = [];

    await streamMessage("c1", "今天学什么", {
      onCard: (frame) => cards.push(frame),
    });

    expect(cards).toHaveLength(1);
    expect(cards[0]).toMatchObject({
      card_version: "v1",
      message_type: "task_card",
      structured_data: complete,
    });
  });
});
