"""访问密码与后端访问保护测试（PRD 11.1）。"""

import logging

import pytest
from pydantic import ValidationError

from app.core import access, config


@pytest.fixture(autouse=True)
def _reset_access_state():
    """每个测试前后清理内存会话与配置缓存。"""
    access.reset_access_sessions()
    config.get_settings.cache_clear()
    yield
    access.reset_access_sessions()
    config.get_settings.cache_clear()


def _set_password(monkeypatch, password: str) -> None:
    monkeypatch.setenv("XIAOMA_ACCESS_PASSWORD", password)
    config.get_settings.cache_clear()


def test_no_password_means_no_login(api_env, monkeypatch) -> None:
    """默认部署不启用密码，接口直接可用，状态接口明确 required=false。"""
    monkeypatch.delenv("XIAOMA_ACCESS_PASSWORD", raising=False)
    config.get_settings.cache_clear()
    client, _ = api_env

    status = client.get("/api/v1/auth/status")
    assert status.status_code == 200
    assert status.json() == {"required": False, "authenticated": True}
    assert client.get("/api/v1/courses").status_code == 200


def test_password_protects_all_private_api(api_env, monkeypatch) -> None:
    """启用密码后，未登录请求一律 401；健康检查仍公开。"""
    _set_password(monkeypatch, "正确密码-123")
    client, _ = api_env

    assert client.get("/api/v1/health").status_code == 200
    status = client.get("/api/v1/auth/status").json()
    assert status == {"required": True, "authenticated": False}

    blocked = client.get("/api/v1/courses")
    assert blocked.status_code == 401
    assert blocked.headers["www-authenticate"] == "Bearer"
    assert blocked.json()["detail"] == "需要访问密码登录"

    blocked_write = client.post(
        "/api/v1/model-configs",
        json={
            "name": "x",
            "provider": "deepseek",
            "model_name": "m",
            "api_key": "sk-test",
        },
    )
    assert blocked_write.status_code == 401


def test_login_logout_flow(api_env, monkeypatch) -> None:
    """正确密码登录后可访问，退出后令牌立即失效。"""
    _set_password(monkeypatch, "正确密码-123")
    client, _ = api_env

    wrong = client.post("/api/v1/auth/login", json={"password": "wrong"})
    assert wrong.status_code == 401

    login = client.post(
        "/api/v1/auth/login", json={"password": "正确密码-123"}
    )
    assert login.status_code == 200
    data = login.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    token = data["access_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/courses", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/status", headers=headers).json() == {
        "required": True,
        "authenticated": True,
    }

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert client.get("/api/v1/courses", headers=headers).status_code == 401


def test_login_when_password_not_configured(api_env, monkeypatch) -> None:
    """未启用访问密码时，登录接口明确返回 409，而不是签发令牌。"""
    monkeypatch.delenv("XIAOMA_ACCESS_PASSWORD", raising=False)
    config.get_settings.cache_clear()
    client, _ = api_env
    resp = client.post("/api/v1/auth/login", json={"password": "anything"})
    assert resp.status_code == 409


def test_invalid_token_is_rejected(api_env, monkeypatch) -> None:
    """伪造/空令牌不能访问私有接口。"""
    _set_password(monkeypatch, "secret")
    client, _ = api_env
    assert (
        client.get(
            "/api/v1/courses", headers={"Authorization": "Bearer forged"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/courses", headers={"Authorization": "Basic abc"}
        ).status_code
        == 401
    )


def test_failed_login_does_not_log_password(api_env, monkeypatch, caplog) -> None:
    """失败日志只记录来源 IP，不得记录用户输入的密码。"""
    _set_password(monkeypatch, "正确密码-123")
    client, _ = api_env
    with caplog.at_level(logging.WARNING, logger="xiaoma.access"):
        resp = client.post(
            "/api/v1/auth/login", json={"password": "不要出现在日志里的密码"}
        )
    assert resp.status_code == 401
    assert "不要出现在日志里的密码" not in caplog.text


def test_remote_mode_requires_password() -> None:
    """显式启用远程访问但没有密码时，配置校验直接拒绝。"""
    with pytest.raises(ValidationError, match="XIAOMA_ACCESS_PASSWORD"):
        config.Settings(
            xiaoma_allow_remote=True,
            xiaoma_access_password="",
        )


def test_token_ttl_minimum() -> None:
    """过短的会话有效期不允许，避免登录后立即失效。"""
    with pytest.raises(ValidationError, match="TTL"):
        config.Settings(
            xiaoma_allow_remote=False,
            xiaoma_access_token_ttl_seconds=10,
        )
