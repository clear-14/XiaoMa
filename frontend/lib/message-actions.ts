/**
 * V1.4 批次 5：消息级操作（复制 / 重新生成 / 停止生成）的纯判定层。
 *
 * 后端 `POST /conversations/{id}/messages/regenerate` 只接受普通文本助手消息
 * （卡片消息返回 422），且需要真实后端 message_id。这里把判定写成纯函数，
 * 避免界面渲染出点了必然失败的按钮。
 */

import type { Card } from "@/lib/cards";
import type { MessageRole, MessageStatus } from "@/lib/types";

export interface MessageActionTarget {
  role: MessageRole;
  status: MessageStatus;
  content: string;
  /** 后端真实消息 ID；流式期间尚未拿到时为 null。 */
  messageId: string | null;
  cards: Card[];
}

/**
 * 只有已落库的普通文本回复支持重新生成：
 * - 用户消息、生成中的消息、没有真实 ID 的本地消息一律排除；
 * - 带卡片的消息排除（后端明确拒绝 error_card / 业务卡片消息）；
 * - 失败回复在后端持久化为 error_card，也排除，避免必然 422 的按钮。
 */
export function canRegenerateMessage(message: MessageActionTarget): boolean {
  return (
    message.role === "assistant" &&
    message.messageId !== null &&
    message.cards.length === 0 &&
    (message.status === "completed" || message.status === "stopped")
  );
}

/** 有实际文本才提供复制操作。 */
export function canCopyMessage(message: MessageActionTarget): boolean {
  return message.content.trim().length > 0;
}
