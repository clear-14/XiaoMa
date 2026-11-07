/** AI 教学会话 API 封装（会话列表、详情、创建、物理删除、SSE 流式消息）。 */

import { api, streamApi } from "@/lib/api";
import type {
  ConversationDetail,
  ConversationStreamError,
  ConversationStreamInfo,
  ConversationSummary,
  CreateConversationInput,
} from "@/lib/types";

export type {
  ConversationDetail,
  ConversationMessage,
  ConversationSummary,
} from "@/lib/types";

export function listConversations(): Promise<ConversationSummary[]> {
  return api.get<ConversationSummary[]>("/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return api.get<ConversationDetail>(`/conversations/${id}`);
}

export function createConversation(
  input: CreateConversationInput,
): Promise<ConversationDetail> {
  return api.post<ConversationDetail>("/conversations", input);
}

/** 物理删除会话及其全部消息（不可恢复）。 */
export function deleteConversation(id: string): Promise<void> {
  return api.delete<void>(`/conversations/${id}`);
}

export interface StreamMessageHandlers {
  onStart?: (info: ConversationStreamInfo) => void;
  onDelta?: (text: string) => void;
  onDone?: (info: ConversationStreamInfo) => void;
  onError?: (info: ConversationStreamError) => void;
}

/**
 * 发送一条用户消息并接收 SSE 流式教学回复。
 *
 * `error` 事件不会抛异常：它表示后端已保存本轮用户消息和失败回复，
 * 调用方应据此展示失败标识；HTTP/网络层错误才以 ApiError 抛出。
 */
export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: StreamMessageHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await streamApi(
    `/conversations/${conversationId}/messages/stream`,
    { content },
    ({ event, data }) => {
      if (event === "start" && isStreamInfo(data)) {
        handlers.onStart?.(data);
      } else if (event === "delta" && typeof data === "object" && data !== null) {
        const text = (data as { text?: unknown }).text;
        if (typeof text === "string") {
          handlers.onDelta?.(text);
        }
      } else if (event === "done" && isStreamInfo(data)) {
        handlers.onDone?.(data);
      } else if (event === "error" && isStreamError(data)) {
        handlers.onError?.(data);
      }
    },
    signal,
  );
}

function isStreamInfo(data: unknown): data is ConversationStreamInfo {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof (data as { conversation_id?: unknown }).conversation_id === "string"
  );
}

function isStreamError(data: unknown): data is ConversationStreamError {
  return (
    isStreamInfo(data) &&
    typeof (data as { message?: unknown }).message === "string"
  );
}
