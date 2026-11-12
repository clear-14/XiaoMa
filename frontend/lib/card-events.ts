/**
 * V1.4 批次 4：SSE `card` 事件帧 → 已校验卡片的解析层（纯函数）。
 *
 * 与设计文档 §2「`lib/card-events.ts`（SSE 卡片帧解析）」对应，职责边界：
 * - `lib/conversations.ts` 的 `isCardFrame()` 是**传输层**：只保证帧是完整
 *   JSON 对象、协议字段齐全；半成品 `card_delta` 类帧在此被丢弃。
 * - 本模块是**语义层**：独立校验帧级完整性，并把 `structured_data` 交给
 *   `normalizeCard()`。版本/类型/必备字段不合法时降级为 `error_card`，
 *   让界面明确展示失败，而不是渲染空白或半成品（契约 §3.3、PRD §11）。
 * - 本模块不依赖 `conversations.ts`，畸形帧可独立单测。
 */

import { isRecord, normalizeCard, type Card } from "@/lib/cards";

export interface ParsedCardFrame {
  conversationId: string;
  /** 生成开始时预建的助手消息 ID；后端 §3.3 保证 `card` 帧携带真实 ID。 */
  messageId: string | null;
  cardVersion: string;
  messageType: string;
  /** 已校验卡片；不合法输入已降级为 `error_card`。 */
  card: Card;
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * 解析一个 `card` 事件帧。
 *
 * 帧级字段（conversation_id / card_version / message_type / structured_data）
 * 缺失或类型错误时返回 `null`，表示这不是一个可归属会话的完整帧，应当丢弃；
 * 卡片内容本身不合法时不返回 `null`，而是返回 `card=error_card` 的已解析帧，
 * 由界面明确展示失败原因。
 */
export function parseCardFrame(raw: unknown): ParsedCardFrame | null {
  if (!isRecord(raw)) {
    return null;
  }
  if (!nonEmptyString(raw.conversation_id)) {
    return null;
  }
  if (!nonEmptyString(raw.card_version)) {
    return null;
  }
  if (!nonEmptyString(raw.message_type)) {
    return null;
  }
  if (!isRecord(raw.structured_data)) {
    return null;
  }

  const messageId = nonEmptyString(raw.message_id) ? raw.message_id : null;
  return {
    conversationId: raw.conversation_id,
    messageId,
    cardVersion: raw.card_version,
    messageType: raw.message_type,
    card: normalizeCard(raw.structured_data),
  };
}
