"""V1.4 批次 4：v1 卡片载荷字段表与「冻结语义不变」回归测试。

字段表是前端渲染层做必备字段校验、批次 5 让 Agent 生成卡片的共同依据，
必须与 ``frontend/lib/cards.ts`` 的 ``CARD_FIELD_RULES`` 逐项一致。
本文件同时守住一条契约底线：批次 1 已冻结的 ``normalize_card()`` 行为
不得因为新增字段表而改变 —— 后端仍只校验协议三字段，业务字段缺失的
卡片在后端依旧是合法 v1 消息，降级只发生在前端渲染层。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.schemas.cards import (
    CARD_FIELD_RULES,
    CARD_TYPES,
    CARD_VERSION,
    MESSAGE_TYPES,
    build_error_card,
    normalize_card,
    validate_card_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CARDS_TS = REPO_ROOT / "frontend" / "lib" / "cards.ts"

VALID_PAYLOADS: dict[str, dict[str, Any]] = {
    "task_card": {
        "title": "变量与赋值",
        "knowledge_point_code": "py-var",
        "knowledge_point_name": "变量",
        "learning_goal": "理解变量的含义",
        "estimated_minutes": 30,
    },
    "lesson_card": {
        "knowledge_point_code": "py-var",
        "knowledge_point_name": "变量",
        "explanation": "变量是用来存放数据的名字。",
    },
    "quiz_card": {"attempt_id": "attempt-1", "questions": [{"id": "q1"}]},
    "quiz_result_card": {"attempt_id": "attempt-1", "score": 8, "total_points": 10},
    "mistake_card": {
        "mistake_id": "mistake-1",
        "question_stem": "写出变量声明语句",
        "knowledge_point_name": "变量",
    },
    "plan_card": {
        "plan_id": "plan-1",
        "course_name": "Python 零基础入门",
        "version_number": 1,
        "items": [{"day_index": 1}],
    },
    "plan_change_card": {
        "proposal_id": "proposal-1",
        "changes": {"daily_study_minutes": 30},
    },
    "progress_card": {
        "course_name": "Python 零基础入门",
        "mastered_count": 3,
        "learning_count": 2,
    },
    "error_card": {"reason": "模型请求超时"},
}


def _parse_frontend_rules() -> dict[str, dict[str, str]]:
    """从前端 TS 源码解析 CARD_FIELD_RULES；解析失败必须显式报错，不静默跳过。"""
    text = FRONTEND_CARDS_TS.read_text(encoding="utf-8")
    marker = "export const CARD_FIELD_RULES"
    assert marker in text, "前端 lib/cards.ts 缺少 CARD_FIELD_RULES"
    start = text.index(marker)
    end = text.index("\n};", start)
    block = text[start:end]

    # 每个类型块形如 `task_card: { ... }`（允许单行或多行），块内不嵌套花括号。
    type_blocks = re.findall(r"(\w+):\s*\{([^{}]*)\}", block, flags=re.S)
    assert type_blocks, "未能从前端字段表解析出任何类型块"

    parsed: dict[str, dict[str, str]] = {}
    for type_name, body in type_blocks:
        fields = re.findall(
            r"(\w+):\s*\"(string|number|boolean|array|object)\"", body
        )
        parsed[type_name] = dict(fields)
    return parsed


class TestFieldTable:
    def test_message_and_card_types_match_contract(self) -> None:
        assert len(MESSAGE_TYPES) == 10
        assert MESSAGE_TYPES[0] == "text"
        assert len(CARD_TYPES) == 9
        assert CARD_VERSION == "v1"

    def test_field_rules_cover_every_card_type(self) -> None:
        assert set(CARD_FIELD_RULES) == set(CARD_TYPES)
        for card_type, rules in CARD_FIELD_RULES.items():
            assert rules, f"{card_type} 至少需要一个必备字段"
            assert set(rules.values()) <= {
                "string",
                "number",
                "boolean",
                "array",
                "object",
            }

    def test_frontend_and_backend_tables_are_identical(self) -> None:
        """前后端字段表逐项比对，防止只改一边造成卡片被误判降级。"""
        assert _parse_frontend_rules() == CARD_FIELD_RULES

    @pytest.mark.parametrize("card_type", sorted(VALID_PAYLOADS))
    def test_valid_payload_passes(self, card_type: str) -> None:
        assert validate_card_payload(card_type, VALID_PAYLOADS[card_type]) is None

    def test_missing_field_is_reported_with_field_name(self) -> None:
        # title 已给出，按字段表顺序第一个缺失的必备字段是 knowledge_point_code
        reason = validate_card_payload("task_card", {"title": "只有标题"})
        assert reason is not None
        assert "字段" in reason
        assert "knowledge_point_code" in reason

    def test_wrong_types_are_rejected(self) -> None:
        assert "estimated_minutes" in str(
            validate_card_payload(
                "task_card", {**VALID_PAYLOADS["task_card"], "estimated_minutes": "30"}
            )
        )
        # bool 是 int 的子类，但协议里不是 number
        assert "mastered_count" in str(
            validate_card_payload(
                "progress_card",
                {**VALID_PAYLOADS["progress_card"], "mastered_count": True},
            )
        )
        assert "questions" in str(
            validate_card_payload("quiz_card", {"attempt_id": "a", "questions": {}})
        )
        assert validate_card_payload("not_a_card", {}) is not None
        assert validate_card_payload("task_card", None) is not None

    def test_zero_and_empty_collection_are_valid(self) -> None:
        assert (
            validate_card_payload(
                "quiz_result_card",
                {"attempt_id": "a", "score": 0, "total_points": 10},
            )
            is None
        )
        assert (
            validate_card_payload(
                "plan_card",
                {
                    "plan_id": "p",
                    "course_name": "课程",
                    "version_number": 1,
                    "items": [],
                },
            )
            is None
        )


class TestFrozenNormalizeCard:
    def test_business_field_gap_does_not_change_backend_v1_semantics(self) -> None:
        """协议完整的卡片即使缺业务字段，后端仍原样保留（批次 1 冻结语义）。"""
        raw = {
            "card_version": CARD_VERSION,
            "type": "task_card",
            "payload": {"title": "只有标题"},
        }
        normalized = normalize_card(raw)
        assert normalized["type"] == "task_card"
        assert normalized["payload"] == {"title": "只有标题"}
        # 同一张卡片在渲染层会被判为不合法，这正是前后端职责边界。
        assert validate_card_payload("task_card", normalized["payload"]) is not None

    def test_unknown_version_and_type_still_degrade(self) -> None:
        assert normalize_card(
            {"card_version": "v9", "type": "task_card", "payload": {}}
        )["type"] == "error_card"
        assert normalize_card({"card_version": CARD_VERSION, "type": "future_card", "payload": {}})["type"] == "error_card"
        assert build_error_card("失败")["type"] == "error_card"
