/** AI 教学会话 API 封装（会话列表、详情、创建、物理删除、SSE 流式消息）。 */

import { api, streamApi } from "@/lib/api";
import type {
  CardSseFrame,
  ConversationDetail,
  ConversationMessage,
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

/** V1.4 批次 1 新增接口：会话重命名（后端只接受 title）。 */
export function renameConversation(
  id: string,
  title: string,
): Promise<ConversationDetail> {
  return api.patch<ConversationDetail>(`/conversations/${id}`, { title });
}

/**
 * 重新生成是一次性 JSON 接口，内部会跑完整 Agent（可能调用模型），
 * 因此使用比默认 10 秒更长的超时。
 */
const REGENERATE_TIMEOUT_MS = 180_000;

export interface StopGenerationResult {
  conversation_id: string;
  /** 没有进行中的生成时后端返回 false，属幂等结果而非错误。 */
  stopped: boolean;
}

/** V1.4 批次 5：请求停止生成。只置位进程内标志，真正落库由 SSE 边界完成。 */
export function stopGeneration(
  id: string,
): Promise<StopGenerationResult> {
  return api.post<StopGenerationResult>(
    `/conversations/${id}/messages/stop`,
  );
}

/**
 * V1.4 批次 5：重新生成一条普通文本回复。
 * 后端不新增用户消息、不重复计数；返回的是新的助手消息（旧回复保留）。
 */
export function regenerateMessage(
  id: string,
  messageId: string,
): Promise<ConversationMessage> {
  return api.post<ConversationMessage>(
    `/conversations/${id}/messages/regenerate`,
    { message_id: messageId },
    REGENERATE_TIMEOUT_MS,
  );
}

export interface StreamMessageHandlers {
  onStart?: (info: ConversationStreamInfo) => void;
  onDelta?: (text: string) => void;
  /** V1.4 `card` 事件：一次性完整卡片帧；批次 4 负责校验与渲染。 */
  onCard?: (frame: CardSseFrame) => void;
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
      } else if (event === "card" && isCardFrame(data)) {
        handlers.onCard?.(data);
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

/**
 * `card` 帧只做传输层形状校验：完整 JSON 对象、版本与类型字段齐全。
 * 语义校验（未知版本/类型降级 error_card）由批次 4 的纯函数负责，
 * 此处不得把不完整帧当作可渲染卡片向上传递。
 */
function isCardFrame(data: unknown): data is CardSseFrame {
  if (!isStreamInfo(data)) {
    return false;
  }
  const frame = data as unknown as Record<string, unknown>;
  const structured = frame.structured_data;
  return (
    typeof frame.card_version === "string" &&
    typeof frame.message_type === "string" &&
    typeof structured === "object" &&
    structured !== null &&
    typeof (structured as { card_version?: unknown }).card_version === "string" &&
    typeof (structured as { type?: unknown }).type === "string" &&
    "payload" in (structured as Record<string, unknown>)
  );
}
