"""健康检查接口测试。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    """健康检查应返回 200 与状态、版本信息。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "xiaoma-backend"
    assert data["version"]


def test_health_unknown_path_returns_404() -> None:
    """未定义路径应返回 404。"""
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
