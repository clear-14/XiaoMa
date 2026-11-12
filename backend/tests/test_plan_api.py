"""学习计划接口测试：创建（诊断→草稿）、确认、调整（新版本）、历史版本。

覆盖验收标准：能创建计划 ✅、能查看计划项目 ✅、能调整计划 ✅、
历史版本保留 ✅、已完成任务不因调整计划丢失 ✅。
"""

import uuid
from datetime import datetime

from sqlalchemy import select

from app.models.learning_plan import LearningPlanItem, LearningPlanVersion
from app.seed.course_seed import seed_courses
from app.services.mastery_service import MasteryService

GOAL = "三个月内掌握 Python 基础语法"


def _seed(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def _grant_mastery(factory, codes: list[str]) -> None:
    """写入掌握证据（模拟知识点测验/诊断测验已通过）。

    阶段 5 起 ``mastered_kp_codes`` 只作为自述线索记录，不再直接跳过；
    要让某个知识点真正不排期，必须有掌握证据。
    """
    db = factory()
    try:
        service = MasteryService(db)
        for code in codes:
            service.grant_mastery(code, source="placement", quiz_difficulty="beginner")
    finally:
        db.close()


def _create_payload(**overrides):
    payload = {
        "course_code": "python-basics",
        "learning_goal": GOAL,
        "current_level": "L1",
        "daily_study_minutes": 45,
        "expected_duration_days": 30,
        "mastered_kp_codes": ["python-basics-01-02"],
    }
    payload.update(overrides)
    return payload


def _create_plan(client):
    resp = client.post("/api/v1/plans", json=_create_payload())
    assert resp.status_code == 201, resp.text
    return resp.json()


def _mark_items_completed(factory, plan_id: str, version_number: int, count: int) -> list[datetime]:
    """按知识点 code 顺序把版本中前 count 个项目标记为已完成（模拟每日任务阶段写入）。"""
    db = factory()
    try:
        items = list(
            db.scalars(
                select(LearningPlanItem)
                .join(LearningPlanVersion)
                .where(
                    LearningPlanVersion.plan_id == uuid.UUID(plan_id),
                    LearningPlanVersion.version_number == version_number,
                )
            ).all()
        )
        items.sort(key=lambda it: it.knowledge_point.code)
        completed_times = []
        for item in items[:count]:
            item.status = "completed"
            item.completed_at = datetime(2026, 11, 3, 10, 0, 0)
            completed_times.append(item.completed_at)
        db.commit()
        return completed_times
    finally:
        db.close()


def test_create_plan_generates_draft_schedule(api_env):
    client, factory = api_env
    _seed(factory)
    _grant_mastery(factory, ["python-basics-01-02"])

    data = _create_plan(client)
    assert data["status"] == "draft"
    assert data["course_code"] == "python-basics"
    assert data["current_version_number"] is None
    assert data["pending_version_number"] == 1
    assert data["current_version"] is None

    pending = data["pending_version"]
    assert pending["version_number"] == 1
    assert pending["status"] == "draft"
    assert pending["learning_goal"] == GOAL
    assert pending["daily_study_minutes"] == 45
    assert pending["mastered_kp_codes"] == ["python-basics-01-02"]
    # 30 个知识点排期（31 - 1 已掌握）
    items = pending["items"]
    assert len(items) == 30
    assert all(item["status"] == "pending" for item in items)
    # 已掌握知识点不再安排
    assert all(item["knowledge_point_code"] != "python-basics-01-02" for item in items)
    # day_index 从 1 开始且与 computed_duration_days 一致
    assert min(item["day_index"] for item in items) == 1
    assert pending["computed_duration_days"] == max(item["day_index"] for item in items)
    assert pending["warning"] is None


def test_create_plan_warns_when_exceeding_expected_duration(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.post(
        "/api/v1/plans", json=_create_payload(expected_duration_days=1)
    )
    assert resp.status_code == 201
    pending = resp.json()["pending_version"]
    assert pending["computed_duration_days"] > 1
    assert pending["warning"] is not None
    assert "超出期望周期" in pending["warning"]


def test_confirm_plan_activates_and_sets_start_date(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_plan(client)["id"]

    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["start_date"] is not None
    assert data["current_version_number"] == 1
    assert data["pending_version_number"] is None
    assert data["current_version"]["status"] == "active"
    assert data["pending_version"] is None


def test_confirm_without_pending_version_conflicts(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_plan(client)["id"]
    client.post(f"/api/v1/plans/{plan_id}/confirm")

    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 409


def test_create_second_plan_conflicts(api_env):
    client, factory = api_env
    _seed(factory)
    _create_plan(client)

    resp = client.post("/api/v1/plans", json=_create_payload())
    assert resp.status_code == 409
    assert "调整接口" in resp.json()["detail"]


def test_adjust_creates_new_version_and_keeps_history(api_env):
    client, factory = api_env
    _seed(factory)
    _grant_mastery(factory, ["python-basics-01-02"])
    plan_id = _create_plan(client)["id"]
    client.post(f"/api/v1/plans/{plan_id}/confirm")

    # 调整每日时长 → 新草稿版本 2，当前生效版本仍为 1
    resp = client.post(
        f"/api/v1/plans/{plan_id}/adjust", json={"daily_study_minutes": 60}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_version_number"] == 1
    assert data["pending_version_number"] == 2
    assert data["current_version"]["daily_study_minutes"] == 45
    assert data["pending_version"]["daily_study_minutes"] == 60
    # 未提交字段沿用当前版本参数
    assert data["pending_version"]["learning_goal"] == GOAL
    assert data["pending_version"]["expected_duration_days"] == 30

    # 确认 → 版本 2 生效，版本 1 转为历史保留
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_version_number"] == 2
    assert data["current_version"]["status"] == "active"

    detail = client.get(f"/api/v1/plans/{plan_id}").json()
    assert [v["version_number"] for v in detail["versions"]] == [1, 2]
    assert detail["versions"][0]["status"] == "superseded"
    assert detail["versions"][0]["daily_study_minutes"] == 45
    assert detail["versions"][1]["status"] == "active"

    # 历史版本详情仍可查看（版本 1 项目原样保留）
    v1 = client.get(f"/api/v1/plans/{plan_id}/versions/1").json()
    assert v1["version_number"] == 1
    assert len(v1["items"]) == 30
    assert all(item["status"] == "pending" for item in v1["items"])


def test_adjust_keeps_completed_items(api_env):
    client, factory = api_env
    _seed(factory)
    _grant_mastery(factory, ["python-basics-01-02"])
    plan_id = _create_plan(client)["id"]
    client.post(f"/api/v1/plans/{plan_id}/confirm")

    _mark_items_completed(factory, plan_id, 1, 3)

    resp = client.post(
        f"/api/v1/plans/{plan_id}/adjust", json={"daily_study_minutes": 90}
    )
    assert resp.status_code == 200
    pending = resp.json()["pending_version"]
    completed = [item for item in pending["items"] if item["status"] == "completed"]
    assert len(completed) == 3
    # 已完成项目保留原 day_index 与完成时间
    assert all(item["completed_at"] is not None for item in completed)
    # 其余未完成项目重新排期（排除已完成 + 已掌握）
    pending_items = [item for item in pending["items"] if item["status"] == "pending"]
    assert len(pending_items) == 30 - 3

    # 确认后：已完成项目仍在新生效版本中（任务不丢失）
    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm").json()
    current_completed = [
        item for item in confirmed["current_version"]["items"] if item["status"] == "completed"
    ]
    assert len(current_completed) == 3
    # 历史版本 1 原样保留（含已完成项目）
    v1 = client.get(f"/api/v1/plans/{plan_id}/versions/1").json()
    assert sum(1 for item in v1["items"] if item["status"] == "completed") == 3


def test_adjust_before_confirm_rebuilds_draft_in_place(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_plan(client)["id"]

    # 未确认时调整：以现有草稿为基准原地重建，版本号不变，前一次草稿的调整被保留
    client.post(f"/api/v1/plans/{plan_id}/adjust", json={"learning_goal": "新目标"})
    resp = client.post(
        f"/api/v1/plans/{plan_id}/adjust", json={"daily_study_minutes": 60}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_version_number"] == 1
    assert data["pending_version"]["learning_goal"] == "新目标"
    assert data["pending_version"]["daily_study_minutes"] == 60

    detail = client.get(f"/api/v1/plans/{plan_id}").json()
    assert len(detail["versions"]) == 1


def test_adjust_without_any_field_rejected(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_plan(client)["id"]

    resp = client.post(f"/api/v1/plans/{plan_id}/adjust", json={})
    assert resp.status_code == 422


def test_get_current_plan_without_plan_404(api_env):
    client, _ = api_env
    resp = client.get("/api/v1/plans/current")
    assert resp.status_code == 404


def test_create_plan_validation_errors(api_env):
    client, factory = api_env
    _seed(factory)

    # 课程不存在
    resp = client.post(
        "/api/v1/plans", json=_create_payload(course_code="no-such-course")
    )
    assert resp.status_code == 404
    assert resp.json() == {"detail": "课程不存在"}

    # 已掌握知识点不属于课程
    resp = client.post(
        "/api/v1/plans", json=_create_payload(mastered_kp_codes=["fake-kp-1"])
    )
    assert resp.status_code == 422
    assert "fake-kp-1" in resp.json()["detail"]

    # 参数校验：每日时长为 0
    resp = client.post("/api/v1/plans", json=_create_payload(daily_study_minutes=0))
    assert resp.status_code == 422


def test_plan_not_found_errors(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_plan(client)["id"]

    import uuid

    missing = str(uuid.uuid4())
    assert client.get(f"/api/v1/plans/{missing}").status_code == 404
    assert client.post(f"/api/v1/plans/{missing}/confirm").status_code == 404
    assert client.post(
        f"/api/v1/plans/{missing}/adjust", json={"daily_study_minutes": 60}
    ).status_code == 404
    assert client.get(f"/api/v1/plans/{plan_id}/versions/99").status_code == 404
