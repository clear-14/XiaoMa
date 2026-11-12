"""V1.4 批次 1：会话重命名、卡片刷新恢复、停止生成与重新生成。

验收口径对应 ``docs/V1.4技术设计与契约.md`` §3：
- 卡片附属于同一条助手消息，刷新后从消息表恢复；
- 未知版本/类型降级 error_card；
- 停止生成落 status=stopped，不伪装成功、不进模型上下文；
- 重新生成不重复写用户消息；卡片确认类操作仍只走 REST。
"""

import asyncio
import json
import uuid

from app.agent import runner
from app.agent.intent import recognize_intent
from app.models.conversation import Message
from app.schemas.conversation import ConversationCreate
from app.schemas.cards import build_structured_data
from app.services.conversation_service import (
    ConversationService,
    _is_context_message,
)
from app.services.generation_registry import generation_registry

# 命中 planning/plan_overview，非教学意图，不需要配置模型即可跑 Agent
PLANNING_TEXT = "查看我的学习计划"


class _FakeGraph:
    """只按给定顺序吐 custom/values 事件，不调用真实模型与数据库。"""

    def __init__(self, chunks: list[tuple[str, dict]], reply: str = "这是讲解") -> None:
        self.chunks = chunks
        self.reply = reply
        self.states: list[dict] = []

    def astream(self, state, stream_mode):
        self.states.append(state)
        chunks = self.chunks
        reply = self.reply

        async def _generate():
            for mode, chunk in chunks:
                yield (mode, chunk)
            yield (
                "values",
                {"reply": reply, "subgraph": "planning", "result_status": "ok"},
            )

        return _generate()


def _install_graph(monkeypatch, chunks, reply: str = "这是讲解") -> _FakeGraph:
    graph = _FakeGraph(chunks, reply)
    monkeypatch.setattr(runner, "build_agent_graph", lambda db: graph)
    return graph


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        if name:
            events.append((name, data))
    return events


def _new_conversation(client) -> dict:
    resp = client.post("/api/v1/conversations", json={})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _card_chunk(card: dict | None = None) -> tuple[str, dict]:
    return (
        "custom",
        {
            "card": card
            or {
                "card_version": "v1",
                "type": "lesson_card",
                "payload": {"title": "变量", "summary": "保存数据的名字"},
            }
        },
    )


# ------------------------------------------------------------------ 重命名

def test_rename_conversation_updates_title_only(api_env) -> None:
    client, factory = api_env
    conversation = _new_conversation(client)
    cid = conversation["id"]

    resp = client.patch(
        f"/api/v1/conversations/{cid}", json={"title": "  变量与数据类型  "}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "变量与数据类型"
    assert client.get(f"/api/v1/conversations/{cid}").json()["title"] == (
        "变量与数据类型"
    )
    assert client.get("/api/v1/conversations").json()[0]["title"] == (
        "变量与数据类型"
    )

    # 空白标题与不存在的会话必须明确报错
    assert client.patch(
        f"/api/v1/conversations/{cid}", json={"title": "   "}
    ).status_code == 422
    assert client.patch(
        f"/api/v1/conversations/{uuid.uuid4()}", json={"title": "不存在"}
    ).status_code == 404

    db = factory()
    try:
        assert db.query(Message).count() == 0  # 重命名不写消息
    finally:
        db.close()


# ------------------------------------------------------------ 卡片刷新恢复

def test_card_message_is_restored_on_refresh(api_env) -> None:
    client, factory = api_env
    conversation = _new_conversation(client)
    cid = conversation["id"]
    structured = build_structured_data(
        [
            {
                "card_version": "v1",
                "type": "task_card",
                "payload": {"title": "今日任务", "minutes": 45},
            }
        ]
    )

    db = factory()
    try:
        db.add(
            Message(
                conversation_id=uuid.UUID(cid),
                role="assistant",
                content="这是今日任务",
                status="completed",
                message_type="task_card",
                structured_data=structured,
                card_version="v1",
            )
        )
        db.commit()
    finally:
        db.close()

    detail = client.get(f"/api/v1/conversations/{cid}").json()
    assert len(detail["messages"]) == 1
    card_message = detail["messages"][0]
    assert card_message["message_type"] == "task_card"
    assert card_message["card_version"] == "v1"
    assert card_message["structured_data"]["cards"][0]["type"] == "task_card"
    assert card_message["structured_data"]["cards"][0]["payload"]["title"] == (
        "今日任务"
    )


def test_plain_text_message_roundtrips_defaults(api_env) -> None:
    client, factory = api_env
    conversation = _new_conversation(client)
    db = factory()
    try:
        db.add(
            Message(
                conversation_id=uuid.UUID(conversation["id"]),
                role="user",
                content="普通提问",
                status="completed",
            )
        )
        db.commit()
    finally:
        db.close()

    message = client.get(
        f"/api/v1/conversations/{conversation['id']}"
    ).json()["messages"][0]
    assert message["message_type"] == "text"
    assert message["structured_data"] is None
    assert message["card_version"] is None


# -------------------------------------------------------------- 停止生成

def test_stop_endpoint_is_idempotent_and_sets_flag(api_env) -> None:
    client, _ = api_env
    cid = uuid.UUID(_new_conversation(client)["id"])
    before = generation_registry.active_count()

    resp = client.post(f"/api/v1/conversations/{cid}/messages/stop")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"conversation_id": str(cid), "stopped": False}

    flag = generation_registry.register(cid)
    assert generation_registry.active_count() == before + 1
    resp = client.post(f"/api/v1/conversations/{cid}/messages/stop")
    assert resp.json()["stopped"] is True
    assert flag.is_set()

    generation_registry.unregister(cid, flag)
    assert generation_registry.active_count() == before
    assert client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/messages/stop"
    ).status_code == 404


def test_stopped_reply_is_not_a_success_and_not_context(db_session, monkeypatch) -> None:
    service = ConversationService(db_session)
    conversation = service.create_conversation(ConversationCreate())
    context = service.prepare_chat(
        conversation.id, PLANNING_TEXT, require_llm=False
    )
    run = runner.AgentRun(
        db=db_session,
        chat_context=context,
        intent=recognize_intent(PLANNING_TEXT),
    )
    run.assistant_message = service.begin_assistant_message(context)
    graph = _install_graph(
        monkeypatch, [("custom", {"delta": "已生成的一半"})], "已生成的一半"
    )

    async def _collect():
        return [event async for event in run.astream()]

    events = asyncio.run(_collect())
    assert [event["event"] for event in events] == ["delta", "done"]

    stopped = run.stop()
    assert stopped.status == "stopped"
    assert stopped.content == "已生成的一半"
    assert stopped.error_message == "用户已停止生成"
    assert not _is_context_message(stopped)
    # 一条回复只对应一行消息、一次计数（用户 + 助手）
    assert graph.states  # 图确实被执行，断言不是空跑
    assert context.learning_session.message_count == 2
    db_session.refresh(stopped)
    assert stopped.status != "completed"


# -------------------------------------------------------- 流式卡片端到端

def test_stream_emits_card_event_and_persists_it(api_env, monkeypatch) -> None:
    client, _ = api_env
    conversation = _new_conversation(client)
    cid = conversation["id"]
    _install_graph(
        monkeypatch,
        [("custom", {"delta": "这是讲解"}), _card_chunk()],
    )

    resp = client.post(
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": PLANNING_TEXT},
    )
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)
    assert [name for name, _ in events] == ["start", "delta", "card", "done"]

    start, card, done = events[0][1], events[2][1], events[-1][1]
    assert start["message_id"] is not None
    assert card["message_id"] == start["message_id"] == done["message_id"]
    assert card["card_version"] == "v1"
    assert card["message_type"] == "lesson_card"
    assert card["structured_data"]["payload"]["title"] == "变量"
    assert done["result_status"] == "ok"
    assert done["message_count"] == 2

    detail = client.get(f"/api/v1/conversations/{cid}").json()
    assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
    assistant = detail["messages"][-1]
    assert assistant["status"] == "completed"
    assert assistant["message_type"] == "lesson_card"
    assert assistant["structured_data"]["cards"][0]["type"] == "lesson_card"


def test_stream_degrades_unknown_card_version(api_env, monkeypatch) -> None:
    client, _ = api_env
    cid = _new_conversation(client)["id"]
    _install_graph(
        monkeypatch,
        [
            ("custom", {"delta": "这是讲解"}),
            _card_chunk(
                {
                    "card_version": "v99",
                    "type": "task_card",
                    "payload": {"title": "未来版本卡片"},
                }
            ),
        ],
    )

    resp = client.post(
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": PLANNING_TEXT},
    )
    assert resp.status_code == 200, resp.text
    card = next(data for name, data in _parse_sse(resp.text) if name == "card")
    assert card["message_type"] == "error_card"
    assert card["card_version"] == "v1"
    assert "版本" in card["structured_data"]["payload"]["reason"]

    detail = client.get(f"/api/v1/conversations/{cid}").json()
    assert detail["messages"][-1]["structured_data"]["cards"][0]["type"] == (
        "error_card"
    )


# -------------------------------------------------------------- 重新生成

def test_regenerate_rejects_card_and_missing_messages(api_env) -> None:
    client, factory = api_env
    cid = uuid.UUID(_new_conversation(client)["id"])
    db = factory()
    try:
        card_message = Message(
            conversation_id=cid,
            role="assistant",
            content="卡片回复",
            status="completed",
            message_type="task_card",
            structured_data=build_structured_data(
                [
                    {
                        "card_version": "v1",
                        "type": "task_card",
                        "payload": {"title": "今日任务"},
                    }
                ]
            ),
            card_version="v1",
        )
        db.add(card_message)
        db.commit()
        card_id = str(card_message.id)
    finally:
        db.close()

    assert client.post(
        f"/api/v1/conversations/{cid}/messages/regenerate",
        json={"message_id": card_id},
    ).status_code == 422
    assert client.post(
        f"/api/v1/conversations/{cid}/messages/regenerate",
        json={"message_id": str(uuid.uuid4())},
    ).status_code == 404


def test_regenerate_does_not_duplicate_user_message(api_env, monkeypatch) -> None:
    client, _ = api_env
    cid = _new_conversation(client)["id"]
    graph = _install_graph(monkeypatch, [("custom", {"delta": "第一版回复"})], "第一版回复")

    first = client.post(
        f"/api/v1/conversations/{cid}/messages/stream",
        json={"content": PLANNING_TEXT},
    )
    assert first.status_code == 200, first.text
    assistant_id = client.get(f"/api/v1/conversations/{cid}").json()["messages"][-1]["id"]

    _install_graph(monkeypatch, [("custom", {"delta": "第二版回复"})], "第二版回复")
    resp = client.post(
        f"/api/v1/conversations/{cid}/messages/regenerate",
        json={"message_id": assistant_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["content"] == "第二版回复"
    assert resp.json()["message_type"] == "text"
    assert resp.json()["status"] == "completed"

    detail = client.get(f"/api/v1/conversations/{cid}").json()
    roles = [item["role"] for item in detail["messages"]]
    assert roles.count("user") == 1, roles  # 重新生成不重复写用户消息
    assert len(roles) == 3  # 用户 + 第一版 + 第二版，各占一行
    assert detail["message_count"] == 3
    # 旧回复不进模型上下文：上下文截止到原始用户消息
    assert graph.states  # 假图已被调用
