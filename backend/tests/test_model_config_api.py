"""模型配置接口测试：增删改查、默认模型、连接测试、流式对话与密钥安全。

覆盖验收标准：至少成功接入一种真实模型（协议层由模拟服务验证，真实服务另行补验）、
能够测试连接 ✅、能够切换默认模型 ✅、能够正常进行一次流式对话 ✅、
模型异常时能够明确提示 ✅。
"""

import json
import uuid

import httpx
from sqlalchemy import select

from app.core.crypto import decrypt_secret
from app.models.model_config import ModelConfig
from app.services import model_config_service
from app.services.llm_client import LlmClient

API_KEY = "sk-test-1234567890"


def _payload(**overrides):
    data = {
        "name": "DeepSeek 默认",
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "base_url": None,
        "api_key": API_KEY,
        "temperature": 0.7,
        "max_tokens": 1024,
        "timeout": 30,
        "is_default": True,
    }
    data.update(overrides)
    return data


def _create(client, **overrides) -> dict:
    resp = client.post("/api/v1/model-configs", json=_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _db_config(factory, config_id: str) -> ModelConfig:
    db = factory()
    try:
        return db.scalars(
            select(ModelConfig).where(ModelConfig.id == uuid.UUID(config_id))
        ).one()
    finally:
        db.close()


def _patch_client(monkeypatch, handler) -> None:
    """替换 LLM 客户端工厂：使用 httpx.MockTransport 模拟服务商应答。"""
    transport = httpx.MockTransport(handler)

    def factory(request):
        return LlmClient(request, transport=transport)

    monkeypatch.setattr(model_config_service, "create_llm_client", factory)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    assert body["model"] == "deepseek-chat"
    assert body["stream"] is False
    assert str(request.url) == "https://api.deepseek.com/v1/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    return httpx.Response(
        200,
        json={
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 5},
        },
    )


def _stream_handler(chunks: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        payload = "".join(
            f"data: {json.dumps({'choices': [{'delta': {'content': c}}]}, ensure_ascii=False)}\n\n"
            for c in chunks
        ) + "data: [DONE]\n\n"
        return httpx.Response(
            200,
            content=payload.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    return handler


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


# ---------------------------------------------------------------- 增删改查

def test_create_config_encrypts_and_masks_key(api_env):
    client, factory = api_env
    data = _create(client)

    assert data["provider"] == "deepseek"
    assert data["model_name"] == "deepseek-chat"
    assert data["base_url"] is None  # 使用服务商预设端点
    assert data["is_default"] is True
    assert data["has_api_key"] is True
    assert data["api_key_masked"] == "sk-****7890"
    # 响应绝不包含密钥原文或密文
    assert API_KEY not in json.dumps(data, ensure_ascii=False)
    assert "api_key_encrypted" not in data

    stored = _db_config(factory, data["id"]).api_key_encrypted
    assert stored != API_KEY
    assert API_KEY not in stored
    assert decrypt_secret(stored) == API_KEY


def test_create_config_validations(api_env):
    client, _ = api_env
    assert client.post(
        "/api/v1/model-configs", json=_payload(provider="custom", base_url=None)
    ).status_code == 422
    assert client.post(
        "/api/v1/model-configs", json=_payload(provider="anthropic")
    ).status_code == 422
    assert client.post(
        "/api/v1/model-configs", json=_payload(temperature=3)
    ).status_code == 422
    assert client.post(
        "/api/v1/model-configs", json=_payload(provider="custom", base_url="ftp://x")
    ).status_code == 422


def test_list_and_detail_are_masked(api_env):
    client, _ = api_env
    config = _create(client)

    listed = client.get("/api/v1/model-configs")
    assert listed.status_code == 200
    assert API_KEY not in listed.text
    assert listed.json()[0]["api_key_masked"] == "sk-****7890"

    detail = client.get(f"/api/v1/model-configs/{config['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "DeepSeek 默认"
    assert API_KEY not in detail.text


def test_update_without_api_key_keeps_existing_ciphertext(api_env):
    client, factory = api_env
    config = _create(client)
    before = _db_config(factory, config["id"]).api_key_encrypted

    resp = client.put(f"/api/v1/model-configs/{config['id']}", json={"temperature": 0.2})
    assert resp.status_code == 200
    assert resp.json()["temperature"] == 0.2

    after = _db_config(factory, config["id"]).api_key_encrypted
    assert after == before
    assert decrypt_secret(after) == API_KEY


def test_update_api_key_reencrypts(api_env):
    client, factory = api_env
    config = _create(client)
    before = _db_config(factory, config["id"]).api_key_encrypted

    new_key = "sk-new-key-9999"
    resp = client.put(f"/api/v1/model-configs/{config['id']}", json={"api_key": new_key})
    assert resp.status_code == 200
    assert resp.json()["api_key_masked"] == "sk-****9999"

    after = _db_config(factory, config["id"]).api_key_encrypted
    assert after != before
    assert decrypt_secret(after) == new_key


def test_switch_provider_without_base_url_uses_preset(api_env):
    client, _ = api_env
    config = _create(
        client, provider="custom", base_url="https://my-proxy.example.com/v1"
    )
    resp = client.put(f"/api/v1/model-configs/{config['id']}", json={"provider": "deepseek"})
    assert resp.status_code == 200
    assert resp.json()["base_url"] is None


def test_default_model_switching(api_env):
    client, _ = api_env
    first = _create(client)
    assert first["is_default"] is True

    second = _create(client, name="通义千问", provider="qwen", model_name="qwen-plus")
    assert second["is_default"] is True

    listed = {item["id"]: item for item in client.get("/api/v1/model-configs").json()}
    assert listed[second["id"]]["is_default"] is True
    assert listed[first["id"]]["is_default"] is False

    resp = client.post(f"/api/v1/model-configs/{first['id']}/default")
    assert resp.status_code == 200
    listed = {item["id"]: item for item in client.get("/api/v1/model-configs").json()}
    assert listed[first["id"]]["is_default"] is True
    assert listed[second["id"]]["is_default"] is False


def test_delete_default_leaves_no_default(api_env):
    """产品决策 2026-11-07：删除默认模型后保持无默认状态，不自动替用户选择。"""
    client, _ = api_env
    default_config = _create(client)
    other = _create(client, name="备用模型", is_default=False)

    assert client.delete(f"/api/v1/model-configs/{default_config['id']}").status_code == 204
    assert client.get(f"/api/v1/model-configs/{default_config['id']}").status_code == 404

    listed = client.get("/api/v1/model-configs").json()
    assert [item["id"] for item in listed] == [other["id"]]
    assert all(item["is_default"] is False for item in listed)


def test_delete_non_default_keeps_default(api_env):
    client, _ = api_env
    default_config = _create(client)
    other = _create(client, name="备用模型", is_default=False)

    assert client.delete(f"/api/v1/model-configs/{other['id']}").status_code == 204
    listed = client.get("/api/v1/model-configs").json()
    assert [item["id"] for item in listed] == [default_config["id"]]
    assert listed[0]["is_default"] is True


def test_config_not_found_errors(api_env):
    client, _ = api_env
    missing = str(uuid.uuid4())
    assert client.get(f"/api/v1/model-configs/{missing}").status_code == 404
    assert client.put(f"/api/v1/model-configs/{missing}", json={}).status_code == 404
    assert client.delete(f"/api/v1/model-configs/{missing}").status_code == 404
    assert client.post(f"/api/v1/model-configs/{missing}/default").status_code == 404
    assert client.post(f"/api/v1/model-configs/{missing}/test").status_code == 404


# ---------------------------------------------------------------- 连接测试

def test_custom_provider_uses_configured_base_url(api_env, monkeypatch):
    client, _ = api_env
    config = _create(
        client,
        provider="custom",
        base_url="https://my-proxy.example.com/custom/v1/",
        model_name="my-model",
    )

    def handler(request):
        assert str(request.url) == "https://my-proxy.example.com/custom/v1/chat/completions"
        assert json.loads(request.content)["model"] == "my-model"
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    _patch_client(monkeypatch, handler)
    data = client.post(f"/api/v1/model-configs/{config['id']}/test").json()
    assert data["ok"] is True


def test_connection_success(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client)
    _patch_client(monkeypatch, _ok_handler)

    resp = client.post(f"/api/v1/model-configs/{config['id']}/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["model"] == "deepseek-chat"
    assert data["reply"] == "OK"
    assert isinstance(data["latency_ms"], int)
    assert data["error"] is None
    # 测试响应不得泄露密钥
    assert API_KEY not in resp.text


def test_connection_invalid_key_message(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client)

    def handler(request):
        return httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})

    _patch_client(monkeypatch, handler)
    data = client.post(f"/api/v1/model-configs/{config['id']}/test").json()
    assert data["ok"] is False
    assert "API Key 无效" in data["error"]


def test_connection_timeout_message(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client)

    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    _patch_client(monkeypatch, handler)
    data = client.post(f"/api/v1/model-configs/{config['id']}/test").json()
    assert data["ok"] is False
    assert "超时" in data["error"]


def test_connection_unreachable_message(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client)

    def handler(request):
        raise httpx.ConnectError("connection refused")

    _patch_client(monkeypatch, handler)
    data = client.post(f"/api/v1/model-configs/{config['id']}/test").json()
    assert data["ok"] is False
    assert "无法连接模型服务" in data["error"]


def test_connection_empty_reply_message(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client)

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    _patch_client(monkeypatch, handler)
    data = client.post(f"/api/v1/model-configs/{config['id']}/test").json()
    assert data["ok"] is False
    assert "空回复" in data["error"]


def test_provider_error_message_is_sanitized(api_env, monkeypatch):
    """服务商错误信息即使回显密钥，也不得出现在接口响应中。"""
    client, _ = api_env
    config = _create(client)

    def handler(request):
        return httpx.Response(
            400, json={"error": {"message": f"invalid key {API_KEY}"}}
        )

    _patch_client(monkeypatch, handler)
    resp = client.post(f"/api/v1/model-configs/{config['id']}/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert API_KEY not in resp.text
    assert "***" in resp.json()["error"]


# ---------------------------------------------------------------- 流式对话

def _chat_payload(config_id: str | None = None):
    payload = {"messages": [{"role": "user", "content": "你好"}]}
    if config_id:
        payload["config_id"] = config_id
    return payload


def test_stream_chat_success(api_env, monkeypatch):
    client, _ = api_env
    _create(client)  # 默认模型
    _patch_client(monkeypatch, _stream_handler(["你好", "，世界"]))

    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    assert events[0][0] == "start"
    assert events[0][1]["model"] == "deepseek-chat"
    deltas = [data["text"] for event, data in events if event == "delta"]
    assert "".join(deltas) == "你好，世界"
    assert events[-1][0] == "done"
    assert API_KEY not in resp.text


def test_stream_chat_without_default_model_prompts_configuration(api_env):
    client, _ = api_env
    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload())
    assert resp.status_code == 409
    assert "尚未配置默认模型" in resp.json()["detail"]


def test_stream_chat_can_use_explicit_config(api_env, monkeypatch):
    client, _ = api_env
    config = _create(client, is_default=False)  # 无默认模型
    _patch_client(monkeypatch, _stream_handler(["OK"]))

    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload(config["id"]))
    assert resp.status_code == 200
    assert [data["text"] for event, data in _parse_sse(resp.text) if event == "delta"] == ["OK"]


def test_stream_chat_provider_error_emits_clear_message(api_env, monkeypatch):
    client, _ = api_env
    _create(client)

    def handler(request):
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    _patch_client(monkeypatch, handler)
    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload())
    assert resp.status_code == 200  # 流式响应已开始，错误通过事件明确提示
    events = _parse_sse(resp.text)
    assert events[-1][0] == "error"
    assert "API Key 无效" in events[-1][1]["message"]


def test_stream_chat_empty_reply_emits_error(api_env, monkeypatch):
    client, _ = api_env
    _create(client)
    _patch_client(monkeypatch, _stream_handler([]))

    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload())
    events = _parse_sse(resp.text)
    assert events[-1][0] == "error"
    assert "空回复" in events[-1][1]["message"]


def test_stream_chat_timeout_emits_error(api_env, monkeypatch):
    client, _ = api_env
    _create(client)

    def handler(request):
        raise httpx.ReadTimeout("read timeout")

    _patch_client(monkeypatch, handler)
    resp = client.post("/api/v1/llm/chat/stream", json=_chat_payload())
    events = _parse_sse(resp.text)
    assert events[-1][0] == "error"
    assert "超时" in events[-1][1]["message"]


def test_stream_chat_message_validation(api_env):
    client, _ = api_env
    assert client.post("/api/v1/llm/chat/stream", json={"messages": []}).status_code == 422
    assert client.post(
        "/api/v1/llm/chat/stream",
        json={"messages": [{"role": "tool", "content": "x"}]},
    ).status_code == 422
