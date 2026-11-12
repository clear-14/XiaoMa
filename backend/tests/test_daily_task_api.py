"""每日任务接口测试：查询/生成当天任务、防重复、开始学习、标记完成。

覆盖验收标准：首页能够自动获取当天任务 ✅；同一天重复打开不会重复生成 ✅；
用户完成任务后状态正确 ✅；学习进度没有被错误标记为 mastered ✅。
"""

import uuid

from sqlalchemy import delete, select

from app.models.course import KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlanItem, LearningPlanVersion
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.seed.course_seed import seed_courses
from app.services.time_utils import utc_today_naive


def _seed(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def _create_plan(client):
    payload = {
        "course_code": "python-basics",
        "learning_goal": "三个月内掌握 Python 基础语法",
        "current_level": "L1",
        "daily_study_minutes": 45,
        "expected_duration_days": 30,
        "mastered_kp_codes": ["python-basics-01-02"],
    }
    resp = client.post("/api/v1/plans", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_and_confirm_plan(client) -> str:
    plan_id = _create_plan(client)
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    return plan_id


def _get_today(client):
    resp = client.get("/api/v1/daily-tasks/today")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _version_items(factory, plan_id: str, version_number: int) -> list[LearningPlanItem]:
    """按（day_index, 知识点 code）排序的版本项目列表。"""
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
        items.sort(key=lambda it: (it.day_index, it.knowledge_point.code))
        return items
    finally:
        db.close()


def _mark_items_completed(factory, plan_id: str, version_number: int, codes: set[str]) -> None:
    """把版本中指定知识点 code 的项目标记为已完成（模拟历史任务完成状态）。"""
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
        for item in items:
            if item.knowledge_point.code in codes:
                item.status = "completed"
                item.completed_at = utc_today_naive()
        db.commit()
    finally:
        db.close()


def _delete_all_tasks(factory) -> None:
    """清空每日任务（模拟新的一天：当天任务还不存在）。"""
    db = factory()
    try:
        db.execute(delete(DailyTask))
        db.commit()
    finally:
        db.close()


def _set_kp_mastered(factory, kp_code: str) -> None:
    """把知识点标记为已掌握（模拟测验阶段通过掌握验证后的状态写入）。"""
    db = factory()
    try:
        user_id = db.scalars(select(User.id).where(User.username == "local")).one()
        kp_id = db.scalars(
            select(KnowledgePoint.id).where(KnowledgePoint.code == kp_code)
        ).one()
        db.add(LearningProfile(user_id=user_id, knowledge_point_id=kp_id, status="mastered"))
        db.commit()
    finally:
        db.close()


def _profile_status(factory, kp_code: str) -> str | None:
    db = factory()
    try:
        return db.scalars(
            select(LearningProfile.status)
            .join(KnowledgePoint, KnowledgePoint.id == LearningProfile.knowledge_point_id)
            .where(KnowledgePoint.code == kp_code)
        ).first()
    finally:
        db.close()


# ---------------------------------------------------------------- 查询与生成

def test_today_without_plan_404(api_env):
    client, _ = api_env
    resp = client.get("/api/v1/daily-tasks/today")
    assert resp.status_code == 404
    assert "学习计划" in resp.json()["detail"]


def test_today_requires_confirmed_plan(api_env):
    client, factory = api_env
    _seed(factory)
    _create_plan(client)  # 只创建未确认

    resp = client.get("/api/v1/daily-tasks/today")
    assert resp.status_code == 409
    assert "确认" in resp.json()["detail"]


def test_today_generates_first_day_tasks(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)

    data = _get_today(client)
    assert data["generated"] is True
    assert data["task_date"] == utc_today_naive().isoformat()

    # 任务 = 当前生效版本第 1 天全部 pending 项目
    items = _version_items(factory, plan_id, 1)
    min_day = min(item.day_index for item in items if item.status == "pending")
    expected_codes = sorted(
        item.knowledge_point.code
        for item in items
        if item.status == "pending" and item.day_index == min_day
    )
    assert [task["knowledge_point"]["code"] for task in data["tasks"]] == expected_codes
    assert all(task["status"] == "pending" for task in data["tasks"])
    assert all(task["day_index"] == min_day for task in data["tasks"])
    # 阶段 5：自述完成不等于掌握，自述的知识点仍会被安排；
    # 「已掌握不安排」由 test_today_skips_mastered_knowledge_points 覆盖。
    assert "python-basics-01-02" in expected_codes
    assert data["note"] is None


def test_today_reopening_does_not_regenerate(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)

    first = _get_today(client)
    first_ids = {task["id"] for task in first["tasks"]}
    assert first["generated"] is True

    second = _get_today(client)
    assert second["generated"] is False
    assert {task["id"] for task in second["tasks"]} == first_ids
    assert second["tasks"] == first["tasks"]


def test_today_excludes_completed_items_same_day(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    _get_today(client)  # 生成第 1 天任务

    items = _version_items(factory, plan_id, 1)
    min_day = min(item.day_index for item in items if item.status == "pending")
    day1_codes = {item.knowledge_point.code for item in items if item.day_index == min_day}
    done_code = sorted(day1_codes)[0]
    _mark_items_completed(factory, plan_id, 1, {done_code})
    _delete_all_tasks(factory)  # 模拟新的一天

    data = _get_today(client)
    assert data["generated"] is True
    codes = [task["knowledge_point"]["code"] for task in data["tasks"]]
    assert done_code not in codes  # 已完成知识点不再安排
    assert codes == sorted(day1_codes - {done_code})


def test_today_rolls_forward_after_day_completed(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    _get_today(client)  # 生成第 1 天任务

    items = _version_items(factory, plan_id, 1)
    min_day = min(item.day_index for item in items if item.status == "pending")
    # 第 1 天全部完成（模拟前一天的学习）→ 新的一天生成第 2 天任务
    day1_codes = {item.knowledge_point.code for item in items if item.day_index == min_day}
    _mark_items_completed(factory, plan_id, 1, day1_codes)
    _delete_all_tasks(factory)

    data = _get_today(client)
    assert data["generated"] is True
    tasks = data["tasks"]
    assert tasks, "滚动追赶应生成下一个计划日的任务"
    next_day = tasks[0]["day_index"]
    assert next_day > min_day
    expected_codes = sorted(
        item.knowledge_point.code
        for item in items
        if item.status == "pending" and item.day_index == next_day
    )
    assert [task["knowledge_point"]["code"] for task in tasks] == expected_codes


def test_today_skips_mastered_knowledge_points(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)

    items = _version_items(factory, plan_id, 1)
    min_day = min(item.day_index for item in items if item.status == "pending")
    mastered_code = sorted(
        item.knowledge_point.code
        for item in items
        if item.day_index == min_day and item.status == "pending"
    )[0]
    _set_kp_mastered(factory, mastered_code)  # 模拟测验后已掌握

    data = _get_today(client)
    codes = [task["knowledge_point"]["code"] for task in data["tasks"]]
    assert mastered_code not in codes  # 不得重复安排已掌握知识点


def test_today_all_done_returns_empty_with_note(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)

    items = _version_items(factory, plan_id, 1)
    _mark_items_completed(
        factory, plan_id, 1, {item.knowledge_point.code for item in items}
    )

    data = _get_today(client)
    assert data["generated"] is False
    assert data["tasks"] == []
    assert data["note"] is not None


# ---------------------------------------------------------------- 任务详情

def test_task_detail_includes_knowledge_point_info(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task = _get_today(client)["tasks"][0]

    resp = client.get(f"/api/v1/daily-tasks/{task['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    kp = detail["knowledge_point"]
    assert kp["code"] == task["knowledge_point"]["code"]
    assert kp["name"]
    assert kp["learning_goal"]
    assert kp["estimated_minutes"] > 0
    assert kp["chapter_code"].startswith("python-basics")
    assert isinstance(kp["prerequisite_codes"], list)


def test_task_detail_not_found(api_env):
    client, factory = api_env
    _seed(factory)
    missing = str(uuid.uuid4())
    assert client.get(f"/api/v1/daily-tasks/{missing}").status_code == 404
    assert client.post(f"/api/v1/daily-tasks/{missing}/start").status_code == 404
    assert client.post(f"/api/v1/daily-tasks/{missing}/complete").status_code == 404


# ---------------------------------------------------------------- 开始学习

def test_start_task_marks_learning_and_profile(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task = _get_today(client)["tasks"][0]

    resp = client.post(f"/api/v1/daily-tasks/{task['id']}/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "learning"
    assert data["started_at"] is not None
    assert data["completed_at"] is None
    # 学习档案同步：知识点进入 learning（PRD 6.1）
    assert _profile_status(factory, task["knowledge_point"]["code"]) == "learning"


def test_start_task_twice_is_idempotent(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task_id = _get_today(client)["tasks"][0]["id"]

    first = client.post(f"/api/v1/daily-tasks/{task_id}/start").json()
    second = client.post(f"/api/v1/daily-tasks/{task_id}/start").json()
    assert second["status"] == "learning"
    assert second["started_at"] == first["started_at"]  # 首次开始时间不被覆盖


def test_start_completed_task_conflicts(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task_id = _get_today(client)["tasks"][0]["id"]
    client.post(f"/api/v1/daily-tasks/{task_id}/complete")

    resp = client.post(f"/api/v1/daily-tasks/{task_id}/start")
    assert resp.status_code == 409


# ---------------------------------------------------------------- 完成任务

def test_complete_task_marks_completed_and_records_time(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    task = _get_today(client)["tasks"][0]
    kp_code = task["knowledge_point"]["code"]

    resp = client.post(f"/api/v1/daily-tasks/{task['id']}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None  # 记录任务完成时间

    # 同步当前生效计划版本对应项目为已完成
    items = _version_items(factory, plan_id, 1)
    item = next(it for it in items if it.knowledge_point.code == kp_code)
    assert item.status == "completed"
    assert item.completed_at is not None

    # 学习档案：进入待验证状态，绝不直接标记为 mastered（验收标准）
    assert _profile_status(factory, kp_code) == "pending_verification"


def test_complete_task_twice_conflicts(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task_id = _get_today(client)["tasks"][0]["id"]
    assert client.post(f"/api/v1/daily-tasks/{task_id}/complete").status_code == 200
    assert client.post(f"/api/v1/daily-tasks/{task_id}/complete").status_code == 409


def test_complete_without_start_goes_pending_verification(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    task = _get_today(client)["tasks"][0]

    resp = client.post(f"/api/v1/daily-tasks/{task['id']}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert _profile_status(factory, task["knowledge_point"]["code"]) == "pending_verification"


def test_complete_after_plan_adjust_syncs_current_version(api_env):
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    tasks = _get_today(client)["tasks"]

    # 完成第一个任务 → 调整计划（60 分钟/天）→ 确认新版本
    assert client.post(f"/api/v1/daily-tasks/{tasks[0]['id']}/complete").status_code == 200
    assert client.post(
        f"/api/v1/plans/{plan_id}/adjust", json={"daily_study_minutes": 60}
    ).status_code == 200
    assert client.post(f"/api/v1/plans/{plan_id}/confirm").status_code == 200

    # 完成调整前生成的旧任务 → 新生效版本中的对应项目被标记完成
    second_kp = tasks[1]["knowledge_point"]["code"]
    assert client.post(f"/api/v1/daily-tasks/{tasks[1]['id']}/complete").status_code == 200
    items = _version_items(factory, plan_id, 2)
    completed = {it.knowledge_point.code for it in items if it.status == "completed"}
    assert tasks[0]["knowledge_point"]["code"] in completed  # 调整时携带
    assert second_kp in completed  # 旧任务完成同步到新版本


def test_today_task_ids_and_statuses_after_completion(api_env):
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    tasks = _get_today(client)["tasks"]
    assert tasks, "应生成当天任务"

    first = tasks[0]
    client.post(f"/api/v1/daily-tasks/{first['id']}/complete")

    # 完成后再打开首页：返回当天已有任务（含已完成状态），不重新生成
    again = _get_today(client)
    assert again["generated"] is False
    by_id = {task["id"]: task for task in again["tasks"]}
    assert by_id[first["id"]]["status"] == "completed"
    assert by_id[first["id"]]["completed_at"] is not None
