"""V1.4 结构化卡片协议（批次 1，契约冻结）。

对应 ``docs/V1.4技术设计与契约.md`` §2.5 / §3.2 / §3.3：

- 本模块全部是纯函数：不访问数据库、不调用模型、不读配置；
- SSE ``card`` 事件只携带一个**完整**卡片对象。未完成的 JSON 帧、未知版本、
  未知类型一律降级为 ``error_card``，绝不把半成品当完整卡片渲染；
- 持久化到 ``messages.structured_data`` 的是一个完整的「卡片集合」JSON 对象，
  其中 ``cards`` 数组的每个元素都是含 ``card_version`` / ``type`` /
  ``payload`` 的完整卡片；这样一条助手消息可携带多张卡片而不新增消息行，
  ``learning_sessions.message_count`` 口径保持不变；
- 版本自 ``v1`` 起算，后续扩展只增版本，不改 ``v1`` 语义。
"""

from __future__ import annotations

import math
from typing import Any

CARD_VERSION = "v1"
SUPPORTED_CARD_VERSIONS: tuple[str, ...] = ("v1",)
TEXT_MESSAGE_TYPE = "text"
ERROR_CARD_TYPE = "error_card"

MESSAGE_TYPES: tuple[str, ...] = (
    "text",
    "task_card",
    "lesson_card",
    "quiz_card",
    "quiz_result_card",
    "mistake_card",
    "plan_card",
    "plan_change_card",
    "progress_card",
    "error_card",
)
CARD_TYPES: tuple[str, ...] = tuple(
    name for name in MESSAGE_TYPES if name != TEXT_MESSAGE_TYPE
)

# ---------------------------------------------------------------------------
# 批次 4：v1 载荷字段表（渲染层）
#
# 只新增常量与校验函数，**不修改**批次 1 已冻结的 normalize_card() 行为：
# 该纯函数仍只校验「协议三字段 + payload 为对象」，缺业务字段的卡片在后端
# 依旧是合法 v1 消息；前端渲染层用同一份表做更严格的降级，避免展示半成品。
# 这张表同时是批次 5 让 Agent 产出卡片时的生成依据，必须与前端
# frontend/lib/cards.ts 的 CARD_FIELD_RULES 同名同序同规则。
# ---------------------------------------------------------------------------
CARD_FIELD_RULES: dict[str, dict[str, str]] = {
    "task_card": {
        "title": "string",
        "knowledge_point_code": "string",
        "knowledge_point_name": "string",
        "learning_goal": "string",
        "estimated_minutes": "number",
    },
    "lesson_card": {
        "knowledge_point_code": "string",
        "knowledge_point_name": "string",
        "explanation": "string",
    },
    "quiz_card": {"attempt_id": "string", "questions": "array"},
    "quiz_result_card": {
        "attempt_id": "string",
        "score": "number",
        "total_points": "number",
    },
    "mistake_card": {
        "mistake_id": "string",
        "question_stem": "string",
        "knowledge_point_name": "string",
    },
    "plan_card": {
        "plan_id": "string",
        "course_name": "string",
        "version_number": "number",
        "items": "array",
    },
    "plan_change_card": {"proposal_id": "string", "changes": "object"},
    "progress_card": {
        "course_name": "string",
        "mastered_count": "number",
        "learning_count": "number",
    },
    "error_card": {"reason": "string"},
}


def _matches_rule(value: object, rule: str) -> bool:
    """按字段表规则判定单个值；bool 不是 number，NaN / inf 也不是 number。"""
    if rule == "string":
        return isinstance(value, str) and bool(value.strip())
    if rule == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
    if rule == "boolean":
        return isinstance(value, bool)
    if rule == "array":
        return isinstance(value, list)
    if rule == "object":
        return isinstance(value, dict)
    return False


def validate_card_payload(card_type: str, payload: object) -> str | None:
    """校验一张 v1 卡片的必备字段；返回失败原因，通过时返回 ``None``。

    供批次 5 生成卡片时自检，以及与前端 ``normalizeCard()`` 共用同一份口径。
    """
    rules = CARD_FIELD_RULES.get(card_type)
    if rules is None:
        return f"不支持的卡片类型：{card_type!r}"
    if not isinstance(payload, dict):
        return "卡片缺少完整的 payload 对象"
    for field, rule in rules.items():
        if not _matches_rule(payload.get(field), rule):
            return f"卡片 {card_type} 的字段 {field} 缺失或类型不正确"
    return None


def build_error_card(reason: str) -> dict[str, Any]:
    """构造一张明确展示失败原因的错误卡片（降级终态）。"""
    return {
        "card_version": CARD_VERSION,
        "type": ERROR_CARD_TYPE,
        "payload": {"reason": reason},
    }


def normalize_card(raw: object) -> dict[str, Any]:
    """把任意输入校验成一张完整卡片；任何不合法输入都返回 ``error_card``。"""
    if not isinstance(raw, dict):
        return build_error_card("卡片数据必须是完整的 JSON 对象")
    version = raw.get("card_version")
    if version not in SUPPORTED_CARD_VERSIONS:
        return build_error_card(f"不支持的卡片协议版本：{version!r}")
    card_type = raw.get("type")
    if card_type not in CARD_TYPES:
        return build_error_card(f"不支持的卡片类型：{card_type!r}")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        return build_error_card("卡片缺少完整的 payload 对象")
    # 只保留协议字段，避免把流式中间态或多余字段写进历史记录
    return {"card_version": version, "type": card_type, "payload": payload}


def normalize_card_frame(frame: object) -> dict[str, Any]:
    """校验一个 SSE ``card`` 帧，返回可直接下发的完整卡片。"""
    if not isinstance(frame, dict):
        return build_error_card("卡片事件帧不是完整的 JSON 对象")
    return normalize_card(frame.get("structured_data"))


def build_structured_data(
    cards: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """把已校验卡片打包成可持久化的完整 JSON 对象；无卡片返回 ``None``。"""
    if not cards:
        return None
    normalized = [normalize_card(card) for card in cards]
    return {
        "card_version": CARD_VERSION,
        "type": normalized[0]["type"],
        "cards": normalized,
    }


def cards_from_structured_data(raw: object) -> list[dict[str, Any]]:
    """从持久化数据恢复卡片；不合法或不受支持的数据全部降级为 ``error_card``。

    供未来前端刷新重放与后端审计共用；单卡片对象也能兼容读取。
    """
    if raw is None:
        return []
    if isinstance(raw, dict) and "cards" in raw:
        items = raw.get("cards")
        if not isinstance(items, list):
            return [build_error_card("卡片集合格式不完整")]
        return [normalize_card(item) for item in items]
    return [normalize_card(raw)]


def message_type_for(cards: list[dict[str, Any]] | None) -> str:
    """一条助手消息的 ``message_type``：无卡片为 text，否则取首张卡片类型。"""
    if not cards:
        return TEXT_MESSAGE_TYPE
    return normalize_card(cards[0])["type"]


def card_version_for(cards: list[dict[str, Any]] | None) -> str | None:
    """普通文本消息不写协议版本；有卡片才写 ``v1``。"""
    return CARD_VERSION if cards else None
