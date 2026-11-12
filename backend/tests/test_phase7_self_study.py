"""阶段 7：自主选题与学习完成度。

对应用例编号见 ``docs/课程扩展阶段7_自主选题与学习完成度.md`` 7.2。
覆盖 P7-2（自选准入 / 幂等 / 撤回）与 P7-3（计划联动 / 跨天承接 / 证据）。
"""

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.models.course import Chapter, Course, KnowledgePoint
from app.models.daily_task import SOURCE_PLAN, SOURCE_SELF_SELECTED, DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanVersion
from app.models.mastery import KnowledgeMastery, MasteryEvidence
from app.seed.course_seed import seed_courses
from app.services.mastery_service import MasteryService
from app.services.time_utils import utc_today_naive


# ------------------------------------------------------------------ 公共夹具


def _seed(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def _kp_codes(
    factory, course_code: str = "python-basics", limit: int | None = 1
) -> list[str]:
    """取指定课程的若干个知识点 code（按 code 排序，结果稳定）。"""
    db = factory()
    try:
        codes = list(
            db.scalars(
                select(KnowledgePoint.code)
                .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
                .join(Course, Chapter.course_id == Course.id)
                .where(Course.code == course_code)
                .order_by(KnowledgePoint.code.asc())
            ).all()
        )
    finally:
        db.close()
    assert codes, f"课程 {course_code} 没有知识点"
    if limit is None:
        return codes
    assert len(codes) >= limit, f"课程 {course_code} 知识点不足 {limit} 个"
    return codes[:limit]


def _self_study(client, kp_code: str):
    return client.post(
        "/api/v1/daily-tasks/self-study",
        json={"knowledge_point_code": kp_code},
    )


def _tasks_of_today(factory) -> list[DailyTask]:
    db = factory()
    try:
        return list(
            db.scalars(
                select(DailyTask).where(DailyTask.task_date == utc_today_naive())
            ).all()
        )
    finally:
        db.close()


def _create_and_confirm_plan(client, daily_minutes: int = 45) -> str:
    payload = {
        "course_code": "python-basics",
        "learning_goal": "三个月内掌握 Python 基础语法",
        "current_level": "L1",
        "daily_study_minutes": daily_minutes,
        "expected_duration_days": 30,
    }
    resp = client.post("/api/v1/plans", json=payload)
    assert resp.status_code == 201, resp.text
    plan_id = resp.json()["id"]
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    return plan_id


def _version_items(factory, plan_id: str) -> list[dict]:
    """当前生效版本的计划项目快照（按 day_index、kp_code 排序）。"""
    db = factory()
    try:
        plan = db.get(LearningPlan, uuid.UUID(plan_id))
        assert plan is not None and plan.current_version_number is not None
        version = db.scalars(
            select(LearningPlanVersion).where(
                LearningPlanVersion.plan_id == plan.id,
                LearningPlanVersion.version_number == plan.current_version_number,
            )
        ).one()
        items = [
            {
                "version_number": version.version_number,
                "kp_code": item.knowledge_point.code,
                "day_index": item.day_index,
                "status": item.status,
            }
            for item in version.items
        ]
    finally:
        db.close()
    items.sort(key=lambda i: (i["day_index"], i["kp_code"]))
    return items


def _first_day_kp_codes(items: list[dict]) -> list[str]:
    first_day = min(item["day_index"] for item in items)
    return sorted(i["kp_code"] for i in items if i["day_index"] == first_day)


def _plan_item_status(factory, plan_id: str, kp_code: str) -> str:
    return next(
        i["status"] for i in _version_items(factory, plan_id) if i["kp_code"] == kp_code
    )


def _move_task_date(factory, task_id: str, days_ago: int) -> None:
    """把任务挪到 N 天前（模拟跨天未完成）。"""
    db = factory()
    try:
        task = db.get(DailyTask, uuid.UUID(task_id))
        assert task is not None
        task.task_date = utc_today_naive() - timedelta(days=days_ago)
        db.commit()
    finally:
        db.close()


def _drop_plan_item(factory, plan_id: str, kp_code: str) -> None:
    """从生效版本里移除一个计划项目，构造「不在当前计划内」的知识点。

    测试库只播种 ``python-basics`` 的知识点（其余课程为纯目录），
    因此用「计划调整后该知识点不在计划内」这一真实场景代替跨课程自选。
    """
    db = factory()
    try:
        plan = db.get(LearningPlan, uuid.UUID(plan_id))
        assert plan is not None and plan.current_version_number is not None
        version = db.scalars(
            select(LearningPlanVersion).where(
                LearningPlanVersion.plan_id == plan.id,
                LearningPlanVersion.version_number == plan.current_version_number,
            )
        ).one()
        item = next(i for i in version.items if i.knowledge_point.code == kp_code)
        db.delete(item)
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------- P7-2 自选任务


def test_self_study_task_references_real_course_data(api_env):
    """#1 自选任务固化四 ID，且与知识点真实归属一致。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]

    resp = _self_study(client, code)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] is True

    task = body["task"]
    assert task["source"] == SOURCE_SELF_SELECTED
    assert task["status"] == "pending"
    assert task["progress_label"] == "未开始"
    refs = task["course_refs"]
    assert refs is not None
    assert refs["knowledge_point_code"] == code
    assert refs["course_code"] == "python-basics"
    assert refs["module_code"] and refs["lesson_code"]

    db = factory()
    try:
        kp = db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == code)
        ).one()
        assert str(kp.id) == refs["knowledge_point_id"]
        assert str(kp.chapter_id) == refs["module_id"]
        assert str(kp.lesson.id) == refs["lesson_id"]
    finally:
        db.close()


def test_self_study_is_idempotent_per_day(api_env):
    """#2 同一天重复自选同一知识点：created=false、任务 ID 不变、库内仍 1 条。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]

    first = _self_study(client, code)
    assert first.status_code == 200
    assert first.json()["created"] is True
    task_id = first.json()["task"]["id"]

    second = _self_study(client, code)
    assert second.status_code == 200
    body = second.json()
    assert body["created"] is False
    assert body["task"]["id"] == task_id
    assert "已在今天的学习任务中" in (body["note"] or "")

    assert len(_tasks_of_today(factory)) == 1


def test_self_study_outside_plan_has_no_plan_id(api_env):
    """无学习计划时也能自选：plan_id 为空，并明确提示不在计划内。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]

    resp = _self_study(client, code)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task"]["plan_id"] is None
    assert "不在当前学习计划内" in (body["note"] or "")

    # 无计划时首页仍能看到自选内容，并给出说明
    today = client.get("/api/v1/daily-tasks/today?generate=false")
    assert today.status_code == 200, today.text
    assert len(today.json()["self_selected_tasks"]) == 1
    assert "暂无生效的学习计划" in (today.json()["note"] or "")


def test_mastered_point_cannot_be_self_selected(api_env):
    """#3 已通过验证（mastered）的知识点不再排学习任务。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]

    db = factory()
    try:
        MasteryService(db).grant_mastery(code, source="placement")
    finally:
        db.close()

    resp = _self_study(client, code)
    assert resp.status_code == 409
    assert "已通过验证" in resp.json()["detail"]
    assert _tasks_of_today(factory) == []


def test_draft_course_point_cannot_be_self_selected(api_env):
    """#4 草稿课程的知识点被拒绝，且不落库。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]

    db = factory()
    try:
        course = db.scalars(
            select(Course).where(Course.code == "python-basics")
        ).one()
        course.publish_status = "draft"
        db.commit()
    finally:
        db.close()

    resp = _self_study(client, code)
    assert resp.status_code == 409
    assert "尚未正式发布" in resp.json()["detail"]
    assert _tasks_of_today(factory) == []


def test_unknown_knowledge_point_returns_404(api_env):
    """不存在的知识点返回 404，不创建任何任务。"""
    client, factory = api_env
    _seed(factory)

    resp = _self_study(client, "not-a-real-kp")
    assert resp.status_code == 404
    assert _tasks_of_today(factory) == []


def test_delete_only_uncompleted_self_selected(api_env):
    """#13 撤回规则：自选未完成可删；已完成 409；计划任务 409。"""
    client, factory = api_env
    _seed(factory)
    first_code, second_code, third_code = _kp_codes(factory, limit=3)

    # 已完成的自选任务不可撤回
    completed = _self_study(client, first_code).json()["task"]
    assert (
        client.post(f"/api/v1/daily-tasks/{completed['id']}/complete").status_code
        == 200
    )
    resp = client.delete(f"/api/v1/daily-tasks/{completed['id']}")
    assert resp.status_code == 409
    assert "已完成" in resp.json()["detail"]

    # 计划任务不可撤回（把来源改成 plan 模拟计划下发）
    plan_like = _self_study(client, second_code).json()["task"]
    db = factory()
    try:
        row = db.get(DailyTask, uuid.UUID(plan_like["id"]))
        assert row is not None
        row.source = SOURCE_PLAN
        db.commit()
    finally:
        db.close()
    resp = client.delete(f"/api/v1/daily-tasks/{plan_like['id']}")
    assert resp.status_code == 409
    assert "计划内任务" in resp.json()["detail"]

    # 未完成的自选任务可以撤回
    fresh = _self_study(client, third_code).json()["task"]
    resp = client.delete(f"/api/v1/daily-tasks/{fresh['id']}")
    assert resp.status_code == 204
    assert fresh["id"] not in [str(t.id) for t in _tasks_of_today(factory)]


def test_self_study_prerequisite_warning_does_not_block(api_env):
    """未掌握的先修只提示，不阻止自选（阶段 5/6 口径）。"""
    client, factory = api_env
    _seed(factory)

    db = factory()
    try:
        kp = db.scalars(
            select(KnowledgePoint)
            .where(KnowledgePoint.prerequisites.any())
            .order_by(KnowledgePoint.code.asc())
        ).first()
        assert kp is not None, "种子课程里应存在带前置依赖的知识点"
        code = kp.code
        expected = sorted(p.code for p in kp.prerequisites)
    finally:
        db.close()

    resp = _self_study(client, code)
    assert resp.status_code == 200, resp.text
    warnings = resp.json()["prerequisite_warnings"]
    assert [w["knowledge_point_code"] for w in warnings] == expected
    assert all(w["status"] != "mastered" for w in warnings)


# ----------------------------------------------------- P7-3 计划联动与承接


def test_self_selection_does_not_block_plan_tasks(api_env):
    """#5 自选任务不吞掉当天的计划任务：两者并存。"""
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    last_code = _kp_codes(factory, limit=None)[-1]

    created = _self_study(client, last_code)
    assert created.status_code == 200, created.text

    before = client.get("/api/v1/daily-tasks/today?generate=false").json()
    assert before["plan_tasks"] == []
    assert [t["id"] for t in before["self_selected_tasks"]] == [
        created.json()["task"]["id"]
    ]

    after = client.post("/api/v1/daily-tasks/today/generate")
    assert after.status_code == 200, after.text
    body = after.json()
    assert body["plan_tasks"], "自选任务不应吞掉计划任务"
    assert len(body["self_selected_tasks"]) == 1
    assert body["summary"]["plan_total"] >= 1
    assert body["summary"]["self_selected_total"] == 1


def test_self_selection_excludes_duplicate_plan_candidate(api_env):
    """#6 自选恰为当天计划候选：不撞唯一约束，该知识点只出现一次。"""
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    day1 = _first_day_kp_codes(_version_items(factory, plan_id))
    assert day1, "第一天应有计划知识点"

    chosen = _self_study(client, day1[0])
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["created"] is True

    body = client.post("/api/v1/daily-tasks/today/generate").json()
    plan_codes = [t["knowledge_point"]["code"] for t in body["plan_tasks"]]
    assert day1[0] not in plan_codes, "已自选的知识点不应再被计划重复下发"
    all_codes = [t["knowledge_point"]["code"] for t in body["tasks"]]
    assert all_codes.count(day1[0]) == 1


def test_self_study_completion_syncs_plan_item_when_in_plan(api_env):
    """#7 计划内自选任务完成 → 对应计划项目标记完成（自选即顶替）。"""
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    day1 = _first_day_kp_codes(_version_items(factory, plan_id))

    task = _self_study(client, day1[0]).json()["task"]
    assert task["plan_id"] == plan_id
    assert _plan_item_status(factory, plan_id, day1[0]) == "pending"

    resp = client.post(f"/api/v1/daily-tasks/{task['id']}/complete")
    assert resp.status_code == 200, resp.text
    assert _plan_item_status(factory, plan_id, day1[0]) == "completed"


def test_self_study_outside_plan_keeps_plan_untouched(api_env):
    """#8 计划外知识点可自选，但计划一个字段都不改。"""
    client, factory = api_env
    _seed(factory)
    plan_id = _create_and_confirm_plan(client)
    outside_code = _kp_codes(factory, limit=None)[-1]
    _drop_plan_item(factory, plan_id, outside_code)
    before = _version_items(factory, plan_id)

    resp = _self_study(client, outside_code)
    assert resp.status_code == 200, resp.text
    assert resp.json()["task"]["plan_id"] is None
    assert "不在当前学习计划内" in (resp.json()["note"] or "")

    assert _version_items(factory, plan_id) == before


def test_learning_task_carries_over_and_is_not_regenerated(api_env):
    """#9 「学习中」任务跨天承接，且同一知识点不重复下发。"""
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    today = client.post("/api/v1/daily-tasks/today/generate").json()
    first = today["plan_tasks"][0]
    code = first["knowledge_point"]["code"]
    assert client.post(f"/api/v1/daily-tasks/{first['id']}/start").status_code == 200

    _move_task_date(factory, first["id"], 3)

    body = client.get("/api/v1/daily-tasks/today?generate=false").json()
    carried = [t for t in body["carried_over_tasks"] if t["id"] == first["id"]]
    assert carried, "前天没学完的任务应跨天承接"
    assert carried[0]["carried_over"] is True
    assert carried[0]["carried_over_days"] == 3
    assert body["summary"]["carried_over"] >= 1

    regenerated = client.post("/api/v1/daily-tasks/today/generate").json()
    plan_codes = [t["knowledge_point"]["code"] for t in regenerated["plan_tasks"]]
    assert code not in plan_codes, "进行中的知识点不应被重新下发"


def test_carried_over_list_is_bounded(api_env):
    """#10 超出 7 天窗口的「学习中」任务不进入承接列表。"""
    client, factory = api_env
    _seed(factory)
    _create_and_confirm_plan(client)
    today = client.post("/api/v1/daily-tasks/today/generate").json()
    first = today["plan_tasks"][0]
    assert client.post(f"/api/v1/daily-tasks/{first['id']}/start").status_code == 200

    _move_task_date(factory, first["id"], 10)

    body = client.get("/api/v1/daily-tasks/today?generate=false").json()
    assert body["carried_over_tasks"] == []
    assert body["summary"]["carried_over"] == 0


def test_completion_writes_only_self_report_evidence(api_env):
    """#11 任务完成只写自述证据，绝不进入 mastered。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]
    task = _self_study(client, code).json()["task"]

    assert client.post(f"/api/v1/daily-tasks/{task['id']}/complete").status_code == 200

    db = factory()
    try:
        kp_id = db.scalars(
            select(KnowledgePoint.id).where(KnowledgePoint.code == code)
        ).one()
        mastery = db.scalars(
            select(KnowledgeMastery).where(
                KnowledgeMastery.knowledge_point_id == kp_id
            )
        ).one()
        assert mastery.status == "self_reported_completed"
        sources = set(
            db.scalars(
                select(MasteryEvidence.source).where(
                    MasteryEvidence.knowledge_point_id == kp_id
                )
            ).all()
        )
        assert sources == {"self_report"}
    finally:
        db.close()


# ------------------------------------------------- P7-4 进度总览与可自选目录


def test_progress_summary_separates_two_axes(api_env):
    """#12 学习完成度与已验证掌握度是两个轴：自述学完只能抬高前者。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]
    task = _self_study(client, code).json()["task"]

    assert client.post(f"/api/v1/daily-tasks/{task['id']}/complete").status_code == 200

    resp = client.get(
        "/api/v1/progress/summary", params={"course_code": "python-basics"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kp_learned"] == 1
    assert body["kp_mastered"] == 0
    assert body["learning_percent"] > 0
    assert body["mastery_percent"] == 0, "自述学完不得计入已验证掌握"
    assert sum(c["kp_learned"] for c in body["chapters"]) == 1

    # 写入真实掌握证据后，掌握度这一轴才上升
    db = factory()
    try:
        MasteryService(db).grant_mastery(code, source="placement")
    finally:
        db.close()

    after = client.get(
        "/api/v1/progress/summary", params={"course_code": "python-basics"}
    ).json()
    assert after["kp_mastered"] == 1
    assert after["mastery_percent"] > 0
    assert after["learning_percent"] >= body["learning_percent"]


def test_progress_summary_unknown_course_404(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/progress/summary", params={"course_code": "nope"})
    assert resp.status_code == 404


def test_study_candidates_expose_two_axes_and_block_reasons(api_env):
    """可自选目录：初始全部可开始；掌握后该知识点不可再选并给出原因。"""
    client, factory = api_env
    _seed(factory)

    resp = client.get(
        "/api/v1/study/candidates", params={"course_code": "python-basics"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["course_name"]
    assert body["chapters"], "应返回章节目录"
    kps = [kp for c in body["chapters"] for kp in c["knowledge_points"]]
    assert kps
    assert all(kp["can_start"] for kp in kps)
    assert all(kp["mastery_status"] == "not_started" for kp in kps)
    assert body["progress"]["learning_percent"] == 0

    target_code = kps[0]["code"]
    db = factory()
    try:
        MasteryService(db).grant_mastery(target_code, source="placement")
    finally:
        db.close()

    body2 = client.get(
        "/api/v1/study/candidates", params={"course_code": "python-basics"}
    ).json()
    target = next(
        kp
        for c in body2["chapters"]
        for kp in c["knowledge_points"]
        if kp["code"] == target_code
    )
    assert target["can_start"] is False
    assert target["mastery_status"] == "mastered"
    assert "已通过验证" in (target["block_reason"] or "")


def test_study_candidates_marks_draft_course_unavailable(api_env):
    """草稿课程整门不可开始，并明确原因（不假装可学）。"""
    client, factory = api_env
    _seed(factory)

    db = factory()
    try:
        course = db.scalars(
            select(Course).where(Course.code == "python-basics")
        ).one()
        course.publish_status = "draft"
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/v1/study/candidates", params={"course_code": "python-basics"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    kps = [kp for c in body["chapters"] for kp in c["knowledge_points"]]
    assert kps and all(kp["can_start"] is False for kp in kps)
    assert any("尚未正式发布" in (kp["block_reason"] or "") for kp in kps)
    assert any("尚未正式发布" in note for note in body["notes"])


def test_study_candidates_reports_today_task_state(api_env):
    """目录能看到今天是否已在该知识点的任务里（前端据此换成「继续学习」）。"""
    client, factory = api_env
    _seed(factory)
    code = _kp_codes(factory)[0]
    _self_study(client, code)

    body = client.get(
        "/api/v1/study/candidates", params={"course_code": "python-basics"}
    ).json()
    target = next(
        kp for c in body["chapters"] for kp in c["knowledge_points"] if kp["code"] == code
    )
    assert target["today_task_status"] == "pending"
    assert target["today_task_source"] == SOURCE_SELF_SELECTED
