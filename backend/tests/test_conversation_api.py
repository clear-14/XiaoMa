"""AI 教学与聊天历史接口测试（阶段 8）。

覆盖验收标准：
- 对话正常 ✅（真实 LLM 客户端协议层由 MockTransport 模拟，真实模型另行验收）
- 刷新页面后历史仍存在 ✅（消息持久化，GET 详情可读回）
- 可以继续历史会话 ✅（上下文按顺序带入模型）
- AI 能够结合当前学习知识点回答 ✅（系统提示词包含知识点/档案/任务）
另覆盖：新建会话不覆盖旧会话、删除会话、模型失败不伪造回复、失败消息持久化。
"""

import json
import uuid

import httpx
from sqlalchemy import select

from app.models.conversation import Conversation, LearningSession, Message
from app.models.course import KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.seed.course_seed import seed_courses
from app.services import teaching_graph
from app.services.llm_client import LlmClient

KP_CODE = "python-basics-01-01"
OTHER_KP_CODE = "python-basics-06-01"
KP_NAME = "什么是编程与 Python"


# ---------------------------------------------------------------- 工具

def _seed(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def _set_profile(client) -> None:
    resp = client.put(
        "/api/v1/profile",
        json={
            "learning_goal": "转行做后端开发",
            "current_level": "L1",
            "daily_study_minutes": 45,
        },
    )
    assert resp.status_code == 200, resp.text


def _create_default_model(client) -> None:
    resp = client.post(
        "/api/v1/model-configs",
        json={
            "name": "测试模型",
            "provider": "custom",
            "base_url": "https://llm.example/v1",
            "api_key": "sk-test-conversation",
            "model_name": "test-model",
            "temperature": 0.7,
            "max_tokens": 512,
            "timeout": 30,
            "is_default": True,
        },
    )
    assert resp.status_code == 201, resp.text


def _set_learning_status(factory, status: str = "learning") -> None:
    db = factory()
    try:
        user_id = db.scalars(select(User.id).where(User.username == "local")).one()
        kp_id = db.scalars(
            select(KnowledgePoint.id).where(KnowledgePoint.code == KP_CODE)
        ).one()
        db.add(
            LearningProfile(
                user_id=user_id, knowledge_point_id=kp_id, status=status
            )
        )
        db.commit()
    finally:
        db.close()


def _create_task(client) -> dict:
    """通过计划流程创建并生成今日任务，返回首个任务。"""
    resp = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "三个月内掌握 Python 基础语法",
            "current_level": "L1",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
            "mastered_kp_codes": ["python-basics-01-02"],
        },
    )
    assert resp.status_code == 201, resp.text
    plan_id = resp.json()["id"]
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    resp = client.get("/api/v1/daily-tasks/today")
    assert resp.status_code == 200, resp.text
    tasks = resp.json()["tasks"]
    assert tasks
    return tasks[0]


def _create_conversation(client, **payload) -> dict:
    resp = client.post("/api/v1/conversations", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        event, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event:
            events.append((event, data))
    return events


class ModelStub:
    """模拟 OpenAI 兼容服务商：记录请求，按配置返回流式文本/错误。"""

    def __init__(
        self,
        chunks: list[str] | None = None,
        *,
        error_after: int | None = None,
        status: int = 200,
    ) -> None:
        self.chunks = chunks or []
        self.error_after = error_after
        self.status = status
        self.requests: list[dict] = []

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if self.status != 200:
            return httpx.Response(
                self.status, json={"error": {"message": "upstream boom"}}
            )
        count = len(self.chunks) if self.error_after is None else self.error_after
        events = [
            {"choices": [{"delta": {"content": chunk}}]}
            for chunk in self.chunks[:count]
        ]
        if self.error_after is not None:
            events.append({"error": {"message": "upstream failed"}})
        payload = "".join(
            f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events
        ) + "data: [DONE]\n\n"
        return httpx.Response(
            200,
            content=payload.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    def install(self, monkeypatch) -> None:
        transport = httpx.MockTransport(self._handler)
        monkeypatch.setattr(
            teaching_graph,
            "create_llm_client",
            lambda request: LlmClient(request, transport=transport),
        )


def _send(client, conversation_id: str, content: str):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": content},
    )


# ---------------------------------------------------------------- 会话创建

def test_create_conversation_with_knowledge_point(api_env):
    client, factory = api_env
    _seed(factory)

    data = _create_conversation(client, knowledge_point_code=KP_CODE)

    assert data["title"] == "新对话"
    assert data["knowledge_point"]["code"] == KP_CODE
    assert data["knowledge_point"]["name"] == KP_NAME
    assert data["message_count"] == 0
    assert data["messages"] == []
    assert data["daily_task_id"] is None

    db = factory()
    try:
        session = db.scalars(
            select(LearningSession).where(
                LearningSession.conversation_id == uuid.UUID(data["id"])
            )
        ).one()
        assert session.message_count == 0
        assert session.knowledge_point_id is not None
        assert session.started_at is not None
        assert session.last_activity_at is not None
    finally:
        db.close()


def test_create_conversation_without_context(api_env):
    client, _ = api_env
    data = _create_conversation(client)
    assert data["knowledge_point"] is None
    assert data["title"] == "新对话"


def test_create_conversation_unknown_knowledge_point(api_env):
    client, factory = api_env
    _seed(factory)
    resp = client.post(
        "/api/v1/conversations",
        json={"knowledge_point_code": "not-exists"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "知识点不存在"


def test_create_conversation_with_daily_task_links_knowledge_point(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    task = _create_task(client)

    data = _create_conversation(client, daily_task_id=task["id"])

    assert data["daily_task_id"] == task["id"]
    assert data["knowledge_point"]["code"] == task["knowledge_point"]["code"]

    db = factory()
    try:
        conversation = db.get(Conversation, uuid.UUID(data["id"]))
        assert conversation.daily_task_id is not None
        # 会话级关联同时写入 1:1 学习会话
        assert conversation.learning_session.daily_task_id == conversation.daily_task_id
        assert (
            conversation.learning_session.knowledge_point_id
            == conversation.knowledge_point_id
        )
    finally:
        db.close()


def test_create_conversation_task_and_knowledge_point_mismatch(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    task = _create_task(client)
    other = KP_CODE if task["knowledge_point"]["code"] != KP_CODE else OTHER_KP_CODE

    resp = client.post(
        "/api/v1/conversations",
        json={"daily_task_id": task["id"], "knowledge_point_code": other},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "每日任务与知识点不匹配"


def test_create_conversation_unknown_task(api_env):
    client, _ = api_env
    resp = client.post(
        "/api/v1/conversations", json={"daily_task_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "每日任务不存在"


def test_new_conversation_does_not_overwrite_old(api_env):
    client, factory = api_env
    _seed(factory)
    first = _create_conversation(client, title="第一个会话")
    second = _create_conversation(client, knowledge_point_code=KP_CODE)

    listing = client.get("/api/v1/conversations").json()
    ids = {item["id"] for item in listing}
    assert ids == {first["id"], second["id"]}

    detail = client.get(f"/api/v1/conversations/{first['id']}").json()
    assert detail["title"] == "第一个会话"
    assert detail["knowledge_point"] is None


# ---------------------------------------------------------------- 流式对话

def test_stream_reply_is_persisted_and_history_survives(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    stub = ModelStub(["变量是", "保存数据的名字。"])
    stub.install(monkeypatch)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    resp = _send(client, conversation["id"], "什么是变量？")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert events[0][0] == "start"
    # V1.4 批次 5：teaching 意图在 done 之前下发一张讲解卡片（lesson_card）。
    # 卡片一次性完整下发，不分片、不拼接，因此事件序列固定为单张 card。
    assert [e[0] for e in events] == ["start", "delta", "delta", "card", "done"]
    assert "".join(e[1]["text"] for e in events if e[0] == "delta") == (
        "变量是保存数据的名字。"
    )
    card_frame = next(e[1] for e in events if e[0] == "card")
    assert card_frame["card_version"] == "v1"
    assert card_frame["message_type"] == "lesson_card"
    assert card_frame["structured_data"]["type"] == "lesson_card"
    assert card_frame["structured_data"]["payload"]["knowledge_point_code"] == KP_CODE
    assert (
        card_frame["structured_data"]["payload"]["explanation"]
        == "变量是保存数据的名字。"
    )
    done = events[-1][1]
    assert done["title"] == "什么是变量？"
    assert done["model"] == "test-model"
    assert done["message_count"] == 2

    # 刷新页面 → 重新查询历史，消息与卡片都仍存在
    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["title"] == "什么是变量？"
    assert detail["message_count"] == 2
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "什么是变量？"
    assistant = detail["messages"][1]
    assert assistant["content"] == "变量是保存数据的名字。"
    assert assistant["status"] == "completed"
    assert assistant["model_name"] == "test-model"
    # 卡片附属于同一条助手消息：不新增消息行，只带结构化数据
    assert card_frame["message_id"] == assistant["id"]
    assert assistant["message_type"] == "lesson_card"
    assert assistant["card_version"] == "v1"
    collection = assistant["structured_data"]
    assert collection["card_version"] == "v1"
    assert [card["type"] for card in collection["cards"]] == ["lesson_card"]
    assert (
        collection["cards"][0]["payload"]["knowledge_point_name"]
        == card_frame["structured_data"]["payload"]["knowledge_point_name"]
    )

    listing = client.get("/api/v1/conversations").json()
    assert listing[0]["id"] == conversation["id"]
    assert listing[0]["message_count"] == 2


def test_continue_conversation_sends_history_and_context(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _set_learning_status(factory, "learning")
    _create_default_model(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    first = ModelStub(["第一轮回复"])
    first.install(monkeypatch)
    assert _send(client, conversation["id"], "第一问").status_code == 200

    second = ModelStub(["第二轮回复"])
    second.install(monkeypatch)
    assert _send(client, conversation["id"], "第二问").status_code == 200

    payload = second.requests[0]
    system_prompt = payload["messages"][0]
    assert system_prompt["role"] == "system"
    # 读取学习档案、当前知识点与掌握状态
    assert "转行做后端开发" in system_prompt["content"]
    assert "L1 碎片化学习者" in system_prompt["content"]
    assert KP_NAME in system_prompt["content"]
    assert "正在学习" in system_prompt["content"]
    # 继续历史会话：前一轮用户消息与 AI 回复按顺序带入
    assert payload["messages"][1:] == [
        {"role": "user", "content": "第一问"},
        {"role": "assistant", "content": "第一轮回复"},
        {"role": "user", "content": "第二问"},
    ]

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert [m["role"] for m in detail["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert detail["message_count"] == 4


def test_prompt_without_context_explains_no_knowledge_point(api_env, monkeypatch):
    client, _ = api_env
    _create_default_model(client)
    stub = ModelStub(["好的"])
    stub.install(monkeypatch)
    conversation = _create_conversation(client)

    assert _send(client, conversation["id"], "你好").status_code == 200
    system_prompt = stub.requests[0]["messages"][0]["content"]
    assert "本次对话未关联具体知识点" in system_prompt
    assert "本次对话未关联每日任务" in system_prompt


def test_task_context_included_in_prompt(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    task = _create_task(client)
    stub = ModelStub(["好的"])
    stub.install(monkeypatch)
    conversation = _create_conversation(client, daily_task_id=task["id"])

    # 使用教学类问题，避免阶段 10 的意图识别把「今天学什么」路由到 Planning 子图
    assert _send(client, conversation["id"], "请讲解当前任务涉及的知识点").status_code == 200
    system_prompt = stub.requests[0]["messages"][0]["content"]
    assert "【当前学习任务】" in system_prompt
    assert f"第 {task['day_index']} 天" in system_prompt
    assert task["task_date"] in system_prompt


# ---------------------------------------------------------------- 失败处理

def test_model_failure_saves_error_message_with_partial_content(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    stub = ModelStub(["部分", "内容"], error_after=2)
    stub.install(monkeypatch)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    resp = _send(client, conversation["id"], "请解释变量")
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert [e[0] for e in events] == ["start", "delta", "delta", "error"]
    error_event = events[-1][1]
    assert "upstream failed" in error_event["message"]
    assert error_event["message_id"] is not None

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    failed = detail["messages"][-1]
    assert failed["role"] == "assistant"
    assert failed["status"] == "error"
    assert failed["content"] == "部分内容"  # 保留已生成部分
    assert "upstream failed" in failed["error_message"]
    assert detail["message_count"] == 2

    # 失败回复不进入下一轮模型上下文，避免把未完成输出当作事实
    second = ModelStub(["重新回答"])
    second.install(monkeypatch)
    assert _send(client, conversation["id"], "再试一次").status_code == 200
    context_messages = second.requests[0]["messages"][1:]
    assert all("部分内容" not in message["content"] for message in context_messages)
    assert [m["content"] for m in context_messages] == ["请解释变量", "再试一次"]


def test_empty_model_reply_is_saved_as_error(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _create_default_model(client)
    stub = ModelStub([])  # 只有 [DONE]，无任何内容
    stub.install(monkeypatch)
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "你好")
    events = _parse_sse(resp.text)
    assert events[-1][0] == "error"
    assert events[-1][1]["message"] == "模型返回了空回复"

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    failed = detail["messages"][-1]
    assert failed["status"] == "error"
    assert failed["content"] == ""
    assert failed["error_message"] == "模型返回了空回复"


def test_http_model_error_is_saved_as_error(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _create_default_model(client)
    stub = ModelStub(status=500)
    stub.install(monkeypatch)
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "你好")
    events = _parse_sse(resp.text)
    assert events[-1][0] == "error"
    assert "HTTP 500" in events[-1][1]["message"]

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["messages"][-1]["status"] == "error"


def test_no_default_model_returns_409_without_saving_message(api_env):
    client, _ = api_env
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "你好")
    assert resp.status_code == 409
    assert "尚未配置默认模型" in resp.json()["detail"]

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["messages"] == []
    assert detail["message_count"] == 0


# ---------------------------------------------------------------- 删除/校验

def test_delete_conversation_keeps_others(api_env):
    client, factory = api_env
    _seed(factory)
    first = _create_conversation(client, title="待删除")
    second = _create_conversation(client, title="保留")

    # 预置一条消息，验证物理删除时消息与学习会话一并移除
    first_id = uuid.UUID(first["id"])
    db = factory()
    try:
        db.add(Message(conversation_id=first_id, role="user", content="待删除消息"))
        db.commit()
    finally:
        db.close()

    resp = client.delete(f"/api/v1/conversations/{first['id']}")
    assert resp.status_code == 204

    assert client.get(f"/api/v1/conversations/{first['id']}").status_code == 404
    listing = client.get("/api/v1/conversations").json()
    assert [item["id"] for item in listing] == [second["id"]]

    db = factory()
    try:
        # 物理删除：会话及其消息、学习会话不再存在（而非仅标记 deleted_at）
        assert db.get(Conversation, first_id) is None
        assert (
            db.scalars(
                select(Message).where(Message.conversation_id == first_id)
            ).all()
            == []
        )
        assert (
            db.scalars(
                select(LearningSession).where(
                    LearningSession.conversation_id == first_id
                )
            ).all()
            == []
        )
        assert db.get(Conversation, uuid.UUID(second["id"])) is not None
    finally:
        db.close()


def test_deleted_conversation_cannot_continue(api_env):
    client, _ = api_env
    conversation = _create_conversation(client)
    assert client.delete(f"/api/v1/conversations/{conversation['id']}").status_code == 204

    resp = _send(client, conversation["id"], "还在吗")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "聊天会话不存在"


def test_unknown_conversation_404(api_env):
    client, _ = api_env
    missing = str(uuid.uuid4())
    assert client.get(f"/api/v1/conversations/{missing}").status_code == 404
    assert _send(client, missing, "你好").status_code == 404
    assert client.delete(f"/api/v1/conversations/{missing}").status_code == 404


def test_empty_message_rejected(api_env):
    client, _ = api_env
    conversation = _create_conversation(client)
    resp = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/stream",
        json={"content": "   "},
    )
    assert resp.status_code == 422


def test_title_from_first_message_is_truncated(api_env, monkeypatch):
    client, _ = api_env
    _create_default_model(client)
    stub = ModelStub(["好的"])
    stub.install(monkeypatch)
    conversation = _create_conversation(client)

    long_question = "这是一个非常非常长的问题" * 5
    assert _send(client, conversation["id"], long_question).status_code == 200
    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["title"] == long_question[:24] + "…"
    assert len(detail["title"]) == 25


def test_user_provided_title_is_kept(api_env, monkeypatch):
    client, _ = api_env
    _create_default_model(client)
    stub = ModelStub(["好的"])
    stub.install(monkeypatch)
    conversation = _create_conversation(client, title="我的变量课")

    assert _send(client, conversation["id"], "第一句话").status_code == 200
    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["title"] == "我的变量课"
