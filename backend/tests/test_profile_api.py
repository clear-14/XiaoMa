"""学习档案接口测试（获取/更新，单用户）。"""

from sqlalchemy import select

from app.models.user import User


def test_get_profile_creates_default_user(api_env):
    client, _ = api_env

    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "local"
    assert data["learning_goal"] is None
    assert data["current_level"] is None
    assert data["daily_study_minutes"] is None
    assert data["learning_preferences"] is None


def test_update_profile_partial_and_persisted(api_env):
    client, factory = api_env

    resp = client.put(
        "/api/v1/profile",
        json={
            "learning_goal": "三个月内掌握 Python 基础语法并完成一个小项目",
            "current_level": "L0",
            "daily_study_minutes": 45,
            "learning_preferences": {"节奏": "循序渐进"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["learning_goal"].startswith("三个月内")
    assert data["current_level"] == "L0"
    assert data["daily_study_minutes"] == 45
    assert data["learning_preferences"] == {"节奏": "循序渐进"}

    # 部分更新：仅提交 daily_study_minutes，其余字段保持不变
    resp = client.put("/api/v1/profile", json={"daily_study_minutes": 60})
    assert resp.status_code == 200
    data = resp.json()
    assert data["learning_goal"].startswith("三个月内")
    assert data["current_level"] == "L0"
    assert data["daily_study_minutes"] == 60

    # 重新读取验证持久化
    data = client.get("/api/v1/profile").json()
    assert data["daily_study_minutes"] == 60
    assert data["current_level"] == "L0"


def test_update_profile_validation(api_env):
    client, _ = api_env

    assert client.put("/api/v1/profile", json={"current_level": "L9"}).status_code == 422
    assert client.put("/api/v1/profile", json={"daily_study_minutes": 0}).status_code == 422
    assert client.put("/api/v1/profile", json={"daily_study_minutes": 1441}).status_code == 422
    assert client.put("/api/v1/profile", json={"learning_goal": "x" * 501}).status_code == 422


def test_profile_repeated_reads_single_user(api_env):
    client, factory = api_env

    client.get("/api/v1/profile")
    client.get("/api/v1/profile")
    client.put("/api/v1/profile", json={"current_level": "L1"})

    db = factory()
    try:
        users = list(db.scalars(select(User)).all())
        assert len(users) == 1
        assert users[0].profile is not None
    finally:
        db.close()
