"""V1.4 批次 1：结构化卡片协议与 messages 迁移测试。

覆盖契约冻结中的四条硬要求：
- 完整 JSON 帧才渲染，未完成的帧/未知版本/未知类型一律降级 error_card；
- 卡片随消息持久化，刷新可按版本恢复；
- SQLite CHECK 约束必须通过 batch 表重建修改，且可降级可重升；
- 存量消息的行数与内容在迁移前后不变。
"""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.agent.tools import FORBIDDEN_TOOL_NAMES, tool_specs
from app.schemas.cards import (
    CARD_TYPES,
    CARD_VERSION,
    MESSAGE_TYPES,
    build_structured_data,
    card_version_for,
    cards_from_structured_data,
    message_type_for,
    normalize_card,
    normalize_card_frame,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "7e6ec48dafbe"


def _make_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def _engine_for(db_path: Path):
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def _valid_card(card_type: str = "task_card") -> dict:
    return {
        "card_version": "v1",
        "type": card_type,
        "payload": {"title": "今日任务", "minutes": 45},
    }


# ------------------------------------------------------------------ 纯函数

def test_normalize_card_keeps_complete_frame() -> None:
    raw = {**_valid_card(), "unexpected": "should-not-be-persisted"}
    card = normalize_card(raw)
    assert card == {
        "card_version": "v1",
        "type": "task_card",
        "payload": {"title": "今日任务", "minutes": 45},
    }


@pytest.mark.parametrize(
    "raw, reason_keyword",
    [
        (["not", "an", "object"], "JSON 对象"),
        ({"card_version": "v1", "type": "task_card"}, "payload"),
        ({"card_version": "v1", "type": "task_card", "payload": []}, "payload"),
        ({**_valid_card(), "card_version": "v9"}, "版本"),
        ({**_valid_card(), "type": "mystery_card"}, "类型"),
        ({"card_version": "v1", "type": "task_card", "payload": None}, "payload"),
    ],
)
def test_normalize_card_degrades_invalid_frames(raw, reason_keyword: str) -> None:
    card = normalize_card(raw)
    assert card["card_version"] == CARD_VERSION
    assert card["type"] == "error_card"
    assert reason_keyword in card["payload"]["reason"]


def test_normalize_card_frame_degrades_broken_event() -> None:
    assert normalize_card_frame("not-a-frame")["type"] == "error_card"
    assert normalize_card_frame({"structured_data": {"type": "task_card"}})[
        "type"
    ] == "error_card"
    assert normalize_card_frame({"structured_data": _valid_card()})[
        "type"
    ] == "task_card"


def test_structured_data_roundtrip_preserves_all_cards() -> None:
    cards = [_valid_card("task_card"), _valid_card("lesson_card")]
    data = build_structured_data(cards)
    assert data["card_version"] == CARD_VERSION
    assert data["type"] == "task_card"
    assert len(data["cards"]) == 2
    restored = cards_from_structured_data(data)
    assert [item["type"] for item in restored] == ["task_card", "lesson_card"]
    assert message_type_for(cards) == "task_card"
    assert card_version_for(cards) == CARD_VERSION


def test_structured_data_degrades_unsupported_version_on_refresh() -> None:
    stale = {
        "card_version": "v9",
        "type": "task_card",
        "cards": [{**_valid_card(), "card_version": "v9"}],
    }
    restored = cards_from_structured_data(stale)
    assert len(restored) == 1
    assert restored[0]["type"] == "error_card"
    assert "版本" in restored[0]["payload"]["reason"]


def test_plain_text_message_has_no_card_fields() -> None:
    assert build_structured_data(None) is None
    assert build_structured_data([]) is None
    assert message_type_for(None) == "text"
    assert card_version_for(None) is None
    assert len(MESSAGE_TYPES) == 10
    assert len(CARD_TYPES) == 9
    assert "text" not in CARD_TYPES
    assert "error_card" in CARD_TYPES


def test_confirmation_actions_remain_rest_only() -> None:
    """卡片协议不得给 Agent 新增确认/写计划入口（PRD §6.2 / 任务书阶段 6）。"""
    names = {item["name"] for item in tool_specs()}
    for forbidden in ("confirm_plan", "confirm_proposal", "adjust_plan"):
        assert forbidden in FORBIDDEN_TOOL_NAMES
        assert forbidden not in names


# -------------------------------------------------------------------- 迁移

def test_migration_adds_v14_message_card_fields(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "v14_schema.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(_make_config(), "head")

    engine = _engine_for(db_path)
    try:
        columns = {row["name"] for row in inspect(engine).get_columns("messages")}
        assert {"message_type", "structured_data", "card_version"} <= columns
        ddl = engine.connect().execute(
            text("SELECT sql FROM sqlite_master WHERE name = 'messages'")
        ).scalar_one()
        assert "'streaming'" in ddl and "'stopped'" in ddl
        # 外键与 role 约束必须在表重建后保留
        assert "fk_messages_conversation_id_conversations" in ddl
        assert "ck_messages_role" in ddl
        assert "DEFAULT 'text'" in ddl
    finally:
        engine.dispose()


def test_migration_cycle_preserves_existing_messages(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "v14_cycle.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cfg = _make_config()
    command.upgrade(cfg, PREVIOUS_HEAD)

    # 在旧结构上写入一条历史消息（SQLite 迁移引擎未开启外键，可独立插行）
    message_id = uuid4().hex
    conversation_id = uuid4().hex
    user_id = uuid4().hex
    engine = _engine_for(db_path)
    with engine.begin() as conn:
        # 先建完整父链，保证后续 foreign_key_check 检查的是迁移本身而非测试夹具
        conn.execute(
            sa.text(
                "INSERT INTO users (id, username, created_at, updated_at) "
                "VALUES (:uid, 'v14-migration-test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"uid": user_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, user_id, created_at, updated_at) "
                "VALUES (:cid, :uid, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"cid": conversation_id, "uid": user_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO messages "
                "(id, conversation_id, role, content, status, created_at, updated_at) "
                "VALUES (:id, :cid, 'user', '迁移前的历史消息', 'completed', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": message_id, "cid": conversation_id},
        )
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = _engine_for(db_path)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT content, status, message_type, structured_data, card_version "
                     "FROM messages WHERE id = :id"),
                {"id": message_id},
            ).one()
        assert row.content == "迁移前的历史消息"
        assert row.status == "completed"
        assert row.message_type == "text"
        assert row.structured_data is None
        assert row.card_version is None
        assert engine.connect().execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert not engine.connect().execute(text("PRAGMA foreign_key_check")).fetchall()
    finally:
        engine.dispose()

    command.downgrade(cfg, PREVIOUS_HEAD)
    engine = _engine_for(db_path)
    try:
        columns = {row["name"] for row in inspect(engine).get_columns("messages")}
        assert "message_type" not in columns
        assert "structured_data" not in columns
        assert "card_version" not in columns
        ddl = engine.connect().execute(
            text("SELECT sql FROM sqlite_master WHERE name = 'messages'")
        ).scalar_one()
        assert "'streaming'" not in ddl
        assert "status IN ('completed', 'error')" in ddl
        rows = engine.connect().execute(
            text("SELECT COUNT(*) FROM messages")
        ).scalar_one()
        assert rows == 1
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = _engine_for(db_path)
    try:
        rows = engine.connect().execute(
            text("SELECT COUNT(*) FROM messages")
        ).scalar_one()
        assert rows == 1
        assert engine.connect().execute(text("PRAGMA integrity_check")).scalar() == "ok"
    finally:
        engine.dispose()
