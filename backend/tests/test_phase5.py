"""阶段 5：知识点掌握度与学习诊断测试。

覆盖需求「六、测试」的 7 条硬要求：
- 用户自述不会直接成为 MASTERED；
- 测验通过可以更新对应知识点状态；
- 测验失败可以生成复习建议；
- 一个知识点的记录不会错误覆盖另一个知识点；
- 跳级必须通过实际掌握证据；
- 不影响原有学习档案；
- 不影响原有测验历史。

另加：7 态定义、状态机纯函数、练习判定、诊断 6 维度、诊断测验（跳级验证）、
证据流水只追加、每日任务完成只算自述。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.course import Exercise, KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.mastery import (
    LEGACY_TO_MASTERY,
    MASTERY_RANK,
    MASTERY_STATUS_LABELS,
    MASTERY_STATUSES,
    MASTERY_TO_LEGACY,
    KnowledgeMastery,
    MasteryEvidence,
)
from app.models.quiz import Question, QuizAnswer, QuizAttempt
from app.models.user import User
from app.seed.course_catalog_seed import seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.phase4a_seed import seed_phase4a
from app.seed.textbook_seed import seed_textbook
from app.services.mastery_rules import (
    EXERCISE_PASS_COVERAGE,
    derive_quiz_level,
    grade_exercise_answer,
    on_exercise,
    on_quiz,
    on_self_report,
    on_start,
)
from app.services.mastery_service import MasteryService
from app.services.time_utils import utc_now_naive


# ---------------------------------------------------------------- 夹具与工具


def _seed(factory) -> None:
    """建库数据：Python 基础教材（含练习题与题库）+ 进阶/数据库两门课。"""
    db = factory()
    try:
        seed_courses(db)
        seed_course_catalog(db)
        seed_textbook(db)
        seed_phase4a(db)
    finally:
        db.close()


def _mastery_status(factory, kp_code: str) -> str | None:
    db = factory()
    try:
        return db.scalars(
            select(KnowledgeMastery.status)
            .join(
                KnowledgePoint,
                KnowledgePoint.id == KnowledgeMastery.knowledge_point_id,
            )
            .where(KnowledgePoint.code == kp_code)
        ).first()
    finally:
        db.close()


def _profile_status(factory, kp_code: str) -> str | None:
    db = factory()
    try:
        return db.scalars(
            select(LearningProfile.status)
            .join(
                KnowledgePoint,
                KnowledgePoint.id == LearningProfile.knowledge_point_id,
            )
            .where(KnowledgePoint.code == kp_code)
        ).first()
    finally:
        db.close()


def _canonical(question: Question):
    """正确答案。

    主观题按「参考答案 + 全部评分关键词」作答：关键词不一定出现在参考答案里，
    只抄参考答案可能拿不到满分（这本身是题库质量问题，不在本阶段改动范围）。
    """
    answer = question.correct_answer
    if question.question_type == "single_choice":
        return answer["value"]
    if question.question_type == "multiple_choice":
        return answer["values"]
    if question.question_type == "true_false":
        return answer["value"]
    if question.question_type == "fill_blank":
        return answer["values"][0]
    keywords = answer.get("keywords") or []
    return " ".join([str(answer.get("reference") or ""), *map(str, keywords)])


def _submit_body(factory, questions: list[dict], *, correct: bool) -> dict:
    db = factory()
    try:
        items = []
        for item in questions:
            question = db.get(Question, uuid.UUID(item["id"]))
            assert question is not None
            items.append(
                {
                    "question_id": item["id"],
                    "answer": _canonical(question) if correct else "wrong",
                }
            )
        return {"answers": items}
    finally:
        db.close()


def _self_report(client, codes: list[str]) -> dict:
    resp = client.post(
        "/api/v1/mastery/self-report", json={"knowledge_point_codes": codes}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_quiz(client, **payload) -> dict:
    resp = client.post("/api/v1/quizzes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _submit_quiz(client, attempt_id: str, body: dict) -> dict:
    resp = client.post(f"/api/v1/quizzes/{attempt_id}/submit", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------- 模型与规则


def test_seven_mastery_statuses_are_defined_and_projected():
    """7 个状态齐全，且新旧状态的双向投影不留空。"""
    assert MASTERY_STATUSES == (
        "not_started",
        "learning",
        "self_reported_completed",
        "understood",
        "applied",
        "mastered",
        "needs_review",
    )
    assert set(MASTERY_STATUS_LABELS) == set(MASTERY_STATUSES)
    assert set(MASTERY_TO_LEGACY) == set(MASTERY_STATUSES)
    assert set(LEGACY_TO_MASTERY.values()) <= set(MASTERY_STATUSES)
    # 旧状态只有 5 个，新状态多出的两个必须能投影回去
    assert MASTERY_TO_LEGACY["understood"] == "pending_verification"
    assert MASTERY_TO_LEGACY["applied"] == "pending_verification"
    assert MASTERY_TO_LEGACY["needs_review"] == "review_due"
    # 等级单调性：自述低于基础理解，基础理解低于应用，应用低于掌握
    assert (
        MASTERY_RANK["learning"]
        < MASTERY_RANK["self_reported_completed"]
        < MASTERY_RANK["understood"]
        < MASTERY_RANK["applied"]
        < MASTERY_RANK["mastered"]
    )
    assert "needs_review" not in MASTERY_RANK


@pytest.mark.parametrize("current", MASTERY_STATUSES)
def test_self_report_never_becomes_mastered(current: str):
    """用户自述在任何状态下都不能「产生」MASTERED（需求三）。

    唯一的例外是本来就已 MASTERED：自述不降级也不升级，保持原结论。
    """
    result = on_self_report(current)
    if current != "mastered":
        assert result != "mastered"
    assert result in (current, "self_reported_completed")


def test_state_machine_rules():
    """推进与降级的分界：练习失败不推翻掌握，正式测验失败才降级。"""
    assert on_start("not_started") == "learning"
    assert on_start("applied") == "applied"

    assert on_exercise("self_reported_completed", passed=True) == "applied"
    assert on_exercise("applied", passed=False) == "needs_review"
    # 已掌握：单次练习失败不降级
    assert on_exercise("mastered", passed=False) == "mastered"

    # 正式测验：向上推进
    assert on_quiz("self_reported_completed", level="understood") == "understood"
    assert on_quiz("understood", level="applied") == "applied"
    assert on_quiz("applied", level="mastered") == "mastered"
    # 低档结论不把高档状态拉下来
    assert on_quiz("mastered", level="understood") == "mastered"
    # 唯一允许把 MASTERED 拉下来的路径
    assert on_quiz("mastered", level="needs_review") == "needs_review"
    # 复习后重新通过：直接按本次结论落位
    assert on_quiz("needs_review", level="understood") == "understood"
    with pytest.raises(ValueError):
        on_quiz("learning", level="unknown")


def test_quiz_level_ladder():
    """同一批题按分类推导等级：全对且够题量才是掌握。"""
    assert (
        derive_quiz_level(
            [("基础理解", True), ("代码阅读", True), ("应用练习", True)], score=100.0
        )
        == "mastered"
    )
    # 题量不足 3 道：最高到应用档
    assert (
        derive_quiz_level([("基础理解", True), ("应用练习", True)], score=100.0)
        == "applied"
    )
    # 应用练习没过：只到基础理解
    assert (
        derive_quiz_level(
            [("基础理解", True), ("代码阅读", True), ("应用练习", False)], score=66.7
        )
        == "understood"
    )
    # 基础理解也错了：需要复习
    assert (
        derive_quiz_level(
            [("基础理解", False), ("应用练习", False)], score=0.0
        )
        == "needs_review"
    )
    # 历史内置题没有分类时按基础理解处理
    assert (
        derive_quiz_level([(None, True), (None, True), (None, True)], score=100.0)
        == "mastered"
    )


def test_exercise_grading_uses_reference_coverage():
    """练习判定是确定性的文本比对，不执行代码。"""
    reference = 'print("小明", 18, "杭州")'
    passed = grade_exercise_answer(reference, reference)
    assert passed.result == "passed"
    assert passed.coverage == 1.0

    failed = grade_exercise_answer(reference, "完全不相干的一句话")
    assert failed.result == "failed"
    assert failed.coverage < EXERCISE_PASS_COVERAGE

    with pytest.raises(ValueError):
        grade_exercise_answer("   ", "随便写")


# ---------------------------------------------------------------- 自述与档案


def test_self_report_only_sets_self_reported(api_env):
    """自述 → self_reported_completed，不是 MASTERED；旧状态为 pending_verification。"""
    client, factory = api_env
    _seed(factory)

    data = _self_report(client, ["python-basics-01-01"])
    assert data["items"][0]["status_after"] == "self_reported_completed"
    assert data["items"][0]["changed"] is True
    assert "不会标记为" in data["note"]

    assert _mastery_status(factory, "python-basics-01-01") == "self_reported_completed"
    assert _profile_status(factory, "python-basics-01-01") == "pending_verification"

    overview = client.get("/api/v1/mastery").json()
    assert overview["counts"]["self_reported_completed"] == 1
    assert overview["counts"]["mastered"] == 0
    assert overview["verified_mastered_count"] == 0
    assert overview["self_reported_only_count"] == 1


def test_self_report_does_not_skip_in_plan(api_env):
    """自述不能直接让知识点从计划里消失（需求五.4）。"""
    client, factory = api_env
    _seed(factory)

    resp = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "掌握 Python 基础",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
            "mastered_kp_codes": ["python-basics-01-02"],
        },
    )
    assert resp.status_code == 201, resp.text
    pending = resp.json()["pending_version"]
    codes = {item["knowledge_point_code"] for item in pending["items"]}
    # 自述的知识点仍在计划中
    assert "python-basics-01-02" in codes
    assert pending["skipped_kp_codes"] == []
    assert pending["pending_verification_kp_codes"] == ["python-basics-01-02"]
    assert pending["skip_note"] and "诊断测验" in pending["skip_note"]


def test_legacy_learning_profile_is_preserved(api_env):
    """原有学习档案不被覆盖：老数据只补建掌握记录，不丢状态。"""
    client, factory = api_env
    _seed(factory)

    db = factory()
    try:
        user = db.scalars(select(User).where(User.username == "local")).first()
        if user is None:
            user = User(username="local")
            db.add(user)
            db.flush()
        kp = db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-03")
        ).one()
        db.add(
            LearningProfile(
                user_id=user.id,
                knowledge_point_id=kp.id,
                status="mastered",
                started_at=utc_now_naive(),
                mastered_at=utc_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()

    detail = client.get("/api/v1/mastery/knowledge-points/python-basics-01-03").json()
    assert detail["knowledge_point"]["status"] == "mastered"
    # 旧档案保持原样，没有被改写
    assert _profile_status(factory, "python-basics-01-03") == "mastered"

    overview = client.get("/api/v1/mastery").json()
    assert overview["counts"]["mastered"] == 1


def test_daily_task_completion_is_only_self_report(api_env):
    """每日任务点完成 → 自述完成，绝不写 mastered（原有验收标准）。"""
    client, factory = api_env
    _seed(factory)

    plan = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "掌握 Python 基础",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
        },
    ).json()
    client.post(f"/api/v1/plans/{plan['id']}/confirm")
    tasks = client.get("/api/v1/daily-tasks/today").json()["tasks"]
    assert tasks

    task = tasks[0]
    code = task["knowledge_point"]["code"]
    client.post(f"/api/v1/daily-tasks/{task['id']}/start")
    assert _mastery_status(factory, code) == "learning"
    client.post(f"/api/v1/daily-tasks/{task['id']}/complete")
    assert _mastery_status(factory, code) == "self_reported_completed"
    assert _profile_status(factory, code) == "pending_verification"


# ---------------------------------------------------------------- 测验联动


def test_quiz_pass_updates_mastery(api_env):
    """测验通过 → MASTERED，证据带上正确率、难度与测验记录（需求二、三）。"""
    client, factory = api_env
    _seed(factory)
    _self_report(client, ["python-basics-01-01"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    result = _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )
    update = result["mastery_updates"][0]
    assert update["achieved"] is True
    assert update["status"] == "mastered"

    assert _mastery_status(factory, "python-basics-01-01") == "mastered"
    assert _profile_status(factory, "python-basics-01-01") == "mastered"

    detail = client.get("/api/v1/mastery/knowledge-points/python-basics-01-01").json()
    kp = detail["knowledge_point"]
    assert kp["status"] == "mastered"
    assert kp["accuracy"] == 100.0
    assert kp["quiz_difficulty"] in ("beginner", "intermediate", "advanced")
    assert kp["verified_at"] is not None

    evidence = detail["evidence"]
    assert evidence[0]["source"] == "quiz"
    assert evidence[0]["status_after"] == "mastered"
    assert evidence[0]["quiz_attempt_id"] == quiz["id"]
    # 自述的证据也在，历史不覆盖
    assert any(item["source"] == "self_report" for item in evidence)


def test_quiz_failure_generates_review_suggestions(api_env):
    """测验失败 → NEEDS_REVIEW，并给出复习建议（需求六第 3 条）。"""
    client, factory = api_env
    _seed(factory)
    _self_report(client, ["python-basics-01-01"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    result = _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=False)
    )
    assert result["mastery_updates"][0]["status"] == "needs_review"
    assert _mastery_status(factory, "python-basics-01-01") == "needs_review"

    suggestions = client.get("/api/v1/mastery/review-suggestions").json()
    assert len(suggestions) == 1
    item = suggestions[0]
    assert item["knowledge_point"]["knowledge_point_code"] == "python-basics-01-01"
    assert item["knowledge_point"]["status"] == "needs_review"
    assert item["reasons"]
    assert item["actions"]
    assert item["exercise_codes"]
    assert item["question_count"] >= 3

    # 错题与复习任务照旧生成（不影响原有测验链路）
    mistakes = client.get("/api/v1/mistakes").json()
    assert len(mistakes) == 3


def test_one_knowledge_point_does_not_overwrite_another(api_env):
    """一个知识点的掌握记录不会覆盖另一个（需求六第 4 条）。"""
    client, factory = api_env
    _seed(factory)
    _self_report(client, ["python-basics-01-01", "python-basics-01-02"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )

    assert _mastery_status(factory, "python-basics-01-01") == "mastered"
    assert _mastery_status(factory, "python-basics-01-02") == "self_reported_completed"

    db = factory()
    try:
        codes = {
            row.knowledge_point.code: row.status
            for row in db.scalars(select(KnowledgeMastery)).all()
        }
    finally:
        db.close()
    assert codes["python-basics-01-01"] == "mastered"
    assert codes["python-basics-01-02"] == "self_reported_completed"


def test_chapter_quiz_records_score_without_mastery(api_env):
    """章节测验只记成绩，不改掌握度（PRD 6.4 口径不变）。"""
    client, factory = api_env
    _seed(factory)
    _self_report(client, ["python-basics-01-01", "python-basics-01-02"])

    quiz = _create_quiz(
        client, scope_type="chapter", chapter_code="python-basics-01"
    )
    result = _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )
    assert result["mastery_updates"] == []
    assert _mastery_status(factory, "python-basics-01-01") == "self_reported_completed"
    assert _profile_status(factory, "python-basics-01-01") == "pending_verification"


def test_quiz_history_is_not_affected(api_env):
    """掌握度写入不影响原有测验历史与答题记录（需求六第 7 条）。"""
    client, factory = api_env
    _seed(factory)
    _self_report(client, ["python-basics-01-01"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    body = _submit_body(factory, quiz["questions"], correct=True)
    _submit_quiz(client, quiz["id"], body)

    history = client.get("/api/v1/quizzes").json()
    assert len(history) == 1
    assert history[0]["id"] == quiz["id"]
    assert history[0]["status"] == "submitted"
    assert history[0]["score"] == 100.0
    # 阶段 5：历史记录新增 purpose 字段，常规练习仍为 practice
    assert history[0]["purpose"] == "practice"

    detail = client.get(f"/api/v1/quizzes/{quiz['id']}").json()
    assert len(detail["questions"]) == quiz["question_count"]
    assert all(item["is_correct"] for item in detail["questions"])
    assert detail["purpose"] == "practice"

    db = factory()
    try:
        attempt = db.get(QuizAttempt, uuid.UUID(quiz["id"]))
        assert attempt is not None
        answers = db.scalars(
            select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id)
        ).all()
        assert len(answers) == quiz["question_count"]
        assert all(item.graded_at is not None for item in answers)
    finally:
        db.close()


def test_evidence_history_is_append_only(api_env):
    """证据流水只追加：自述 → 练习 → 测验，三条都在，顺序可回溯。"""
    client, factory = api_env
    _seed(factory)

    _self_report(client, ["python-basics-01-01"])
    db = factory()
    try:
        exercise = db.scalars(
            select(Exercise).where(
                Exercise.knowledge_point.has(
                    KnowledgePoint.code == "python-basics-01-01"
                ),
                Exercise.reference_answer.is_not(None),
            )
        ).first()
        assert exercise is not None
        exercise_code, reference = exercise.code, exercise.reference_answer
        kp_id = exercise.knowledge_point_id
    finally:
        db.close()

    resp = client.post(
        f"/api/v1/mastery/exercises/{exercise_code}/attempt",
        json={"answer": reference},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["attempt"]["result"] == "passed"
    assert body["status_after"] == "applied"
    assert body["attempt"]["coverage"] >= EXERCISE_PASS_COVERAGE

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )

    db = factory()
    try:
        rows = db.scalars(
            select(MasteryEvidence)
            .where(MasteryEvidence.knowledge_point_id == kp_id)
            .order_by(MasteryEvidence.created_at, MasteryEvidence.id)
        ).all()
        sources = [item.source for item in rows]
        assert sources[0] == "self_report"
        assert "exercise" in sources and "quiz" in sources
        assert sources[-1] == "quiz"
        # 每条证据都记录了前后状态，不是只留最终结论
        assert all(item.status_before and item.status_after for item in rows)
    finally:
        db.close()


# ---------------------------------------------------------------- 跳级


def test_skip_requires_mastery_evidence(api_env):
    """自述只能进「需验证」，普通学习更进不了「可跳过」（需求五.1—五.4）。"""
    client, factory = api_env
    _seed(factory)

    _self_report(client, ["python-basics-01-01"])
    data = client.get(
        "/api/v1/mastery/skip-check", params={"course_code": "python-basics"}
    ).json()

    skippable = {item["knowledge_point_code"] for item in data["skippable"]}
    verification = {
        item["knowledge_point_code"] for item in data["needs_verification"]
    }
    assert skippable == set()
    assert "python-basics-01-01" in verification
    assert any("诊断测验" in item["reason"] for item in data["needs_verification"])

    # 拿到掌握证据后才能跳过
    _create_and_pass_quiz(client, factory, "python-basics-01-01")
    data = client.get(
        "/api/v1/mastery/skip-check", params={"course_code": "python-basics"}
    ).json()
    assert "python-basics-01-01" in {
        item["knowledge_point_code"] for item in data["skippable"]
    }


def test_self_report_cannot_skip_whole_course(api_env):
    """不允许仅凭自述跳过所有前置（需求五.4）。"""
    client, factory = api_env
    _seed(factory)

    db = factory()
    try:
        course_codes = sorted(
            kp.code
            for kp in db.scalars(select(KnowledgePoint)).all()
            if kp.chapter.course.code == "python-basics"
        )
    finally:
        db.close()
    assert len(course_codes) > 20

    _self_report(client, course_codes)
    data = client.get(
        "/api/v1/mastery/skip-check", params={"course_code": "python-basics"}
    ).json()
    assert data["skippable"] == []
    assert "不允许仅凭自述跳过所有前置要求" in " ".join(data["notes"])


def test_plan_skips_only_with_evidence(api_env):
    """排期跳过只认证据：有 MASTERED 才不安排，自述仍安排。"""
    client, factory = api_env
    _seed(factory)
    _create_and_pass_quiz(client, factory, "python-basics-01-02")

    resp = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "掌握 Python 基础",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
            "mastered_kp_codes": ["python-basics-01-02", "python-basics-01-03"],
        },
    )
    assert resp.status_code == 201, resp.text
    pending = resp.json()["pending_version"]
    codes = {item["knowledge_point_code"] for item in pending["items"]}
    assert "python-basics-01-02" not in codes  # 有证据 → 跳过
    assert "python-basics-01-03" in codes  # 仅自述 → 仍安排
    assert pending["skipped_kp_codes"] == ["python-basics-01-02"]
    assert pending["self_reported_kp_codes"] == [
        "python-basics-01-02",
        "python-basics-01-03",
    ]


def test_learning_path_default_uses_evidence(api_env):
    """学习路径接口默认只采信后端证据，客户端参数只在 preview 模式生效。"""
    client, factory = api_env
    _seed(factory)

    base = "/api/v1/courses/langgraph-agent/learning-path"
    # 只传参数：默认按证据计算 → 前端课程仍未满足
    resp = client.get(base, params={"mastered": "python-basics-05-02,python-basics-06-03"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["ready"] is False

    # preview=true 才按参数演算
    resp = client.get(
        base,
        params={
            "preview": "true",
            "mastered": "python-basics-05-02,python-basics-06-03",
            "mastered_courses": "python-advanced,llm-api",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ready"] is True


def _create_and_pass_quiz(client, factory, kp_code: str) -> dict:
    """辅助：先自述（获得测验资格）→ 组卷 → 全对提交 → 拿到 MASTERED。"""
    _self_report(client, [kp_code])
    quiz = _create_quiz(
        client, scope_type="knowledge_point", knowledge_point_code=kp_code
    )
    _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )
    return quiz


# ---------------------------------------------------------------- 诊断


def test_diagnosis_dimensions_are_mapped_to_knowledge_points(api_env):
    """6 个维度固定，且每个维度都落到具体知识点（需求四）。"""
    client, factory = api_env
    _seed(factory)

    dims = client.get("/api/v1/diagnosis/dimensions").json()
    assert [item["code"] for item in dims] == [
        "python-basics",
        "python-engineering",
        "python-database",
        "web-backend",
        "llm-api",
        "langgraph-agent",
    ]
    assert [item["name"] for item in dims][:2] == ["Python 基础", "Python 工程能力"]
    for dim in dims:
        if dim["available"]:
            assert dim["knowledge_points"], f"{dim['code']} 没有映射到知识点"
            for kp in dim["knowledge_points"]:
                assert kp["knowledge_point_code"]
                assert kp["status"] in MASTERY_STATUSES
                assert kp["status_label"]
        else:
            # 课程尚未建设时明确说明，而不是伪造结论
            assert dim["level"] == "no_data"
            assert dim["note"]


def test_diagnosis_reflects_mastery_evidence(api_env):
    """诊断按证据给结论：已掌握的知识点 source=evidence，自述的 source=claim。"""
    client, factory = api_env
    _seed(factory)

    _create_and_pass_quiz(client, factory, "python-basics-06-03")  # 字典 → 掌握
    _self_report(client, ["python-basics-05-01"])  # 函数 → 仅自述

    report = client.post(
        "/api/v1/diagnosis",
        json={
            "learning_goal": "学 LangGraph",
            "target_course_code": "python-basics",
        },
    ).json()
    basics = next(item for item in report["dimensions"] if item["code"] == "python-basics")
    by_code = {kp["knowledge_point_code"]: kp for kp in basics["knowledge_points"]}
    assert by_code["python-basics-06-03"]["status"] == "mastered"
    assert by_code["python-basics-06-03"]["source"] == "evidence"
    assert by_code["python-basics-05-01"]["status"] == "self_reported_completed"
    assert by_code["python-basics-05-01"]["source"] == "claim"
    assert basics["level"] == "partial"
    assert basics["mastered_count"] == 1
    assert 0 < basics["coverage_percent"] < 100


def test_diagnosis_route_has_actions_and_remedial(api_env):
    """个性化路线：已掌握跳过、自述去验证、其余学习、入学知识点补学。"""
    client, factory = api_env
    _seed(factory)

    _create_and_pass_quiz(client, factory, "python-basics-06-03")
    _self_report(client, ["python-basics-05-01"])

    report = client.post(
        "/api/v1/diagnosis",
        json={
            "learning_goal": "学习数据库",
            "target_course_code": "python-database",
        },
    ).json()
    actions = {step["knowledge_point_code"]: step["action"] for step in report["route"]}
    assert actions["python-basics-06-03"] == "skip"
    assert actions["python-basics-05-01"] == "verify"
    assert any(action == "study" for action in actions.values())
    # 目标课程的入学知识点未达标 → 补学
    assert report["remedial_kp_codes"]
    assert "python-basics-06-03" not in report["remedial_kp_codes"]
    assert "python-basics-05-04" in report["remedial_kp_codes"]
    # 路线步骤顺序连续、动作有中文说明
    assert [step["order_index"] for step in report["route"]] == list(
        range(1, len(report["route"]) + 1)
    )
    assert all(step["action_label"] for step in report["route"])
    assert report["summary"]
    assert "只采信掌握证据" in " ".join(report["notes"])


def test_diagnosis_placement_verifies_unlearned_knowledge_point(api_env):
    """诊断测验允许对未学知识点出题，通过后写入掌握证据（需求五.3）。"""
    client, factory = api_env
    _seed(factory)

    plan = client.post(
        "/api/v1/diagnosis/placement/plan",
        json={"course_code": "python-basics", "questions_per_point": 2},
    ).json()
    # 没有自述也没有指定知识点时给出明确提示
    assert plan["knowledge_points"] == []
    assert plan["notes"]

    _self_report(client, ["python-basics-02-01"])
    # 未学习（只是自述）也能出题
    resp = client.post(
        "/api/v1/diagnosis/placement",
        json={"knowledge_point_codes": ["python-basics-02-01"], "questions_per_point": 2},
    )
    assert resp.status_code == 201, resp.text
    quiz = resp.json()
    assert quiz["scope_type"] == "stage"
    assert quiz["question_count"] == 2
    # 阶段 5：诊断测验在输出里被明确标记，不与普通练习混淆
    assert quiz["purpose"] == "placement"
    assert client.get("/api/v1/quizzes").json()[0]["purpose"] == "placement"

    result = _submit_quiz(
        client, quiz["id"], _submit_body(factory, quiz["questions"], correct=True)
    )
    updates = result["mastery_updates"]
    assert len(updates) == 1
    assert updates[0]["knowledge_point_code"] == "python-basics-02-01"
    assert updates[0]["status"] == "mastered"
    assert _mastery_status(factory, "python-basics-02-01") == "mastered"

    detail = client.get("/api/v1/mastery/knowledge-points/python-basics-02-01").json()
    sources = [item["source"] for item in detail["evidence"]]
    assert "placement" in sources


def test_mastery_overview_splits_verified_and_claimed(api_env):
    """总览把「真正掌握」与「仅自述」分开报，避免把自述当能力。"""
    client, factory = api_env
    _seed(factory)

    _create_and_pass_quiz(client, factory, "python-basics-01-01")
    _self_report(client, ["python-basics-01-02", "python-basics-01-03"])

    overview = client.get("/api/v1/mastery").json()
    counts = overview["counts"]
    assert counts["mastered"] == 1
    assert counts["self_reported_completed"] == 2
    assert counts["total"] == 3
    assert overview["verified_mastered_count"] == 1
    assert overview["self_reported_only_count"] == 2
    assert 0 < overview["mastered_percent"] < 100
    courses = {item["course_code"]: item for item in overview["courses"]}
    assert courses["python-basics"]["counts"]["mastered"] == 1


def test_knowledge_point_list_covers_course(api_env):
    """知识点级列表覆盖整门课，未学习的也在（前端才能画完整进度）。"""
    client, factory = api_env
    _seed(factory)

    items = client.get(
        "/api/v1/mastery/knowledge-points", params={"course_code": "python-basics"}
    ).json()
    assert len(items) >= 50
    assert {item["status"] for item in items} == {"not_started"}
    assert all(item["next_action"] for item in items)
    assert items[0]["course_code"] == "python-basics"


def test_mastery_service_rejects_unknown_and_bad_source(api_env):
    """未知知识点 404；内部授权入口只接受 quiz / placement 来源。"""
    client, factory = api_env
    _seed(factory)

    resp = client.post(
        "/api/v1/mastery/self-report", json={"knowledge_point_codes": ["no-such-kp"]}
    )
    assert resp.status_code == 404

    db = factory()
    try:
        with pytest.raises(ValueError):
            MasteryService(db).grant_mastery(
                "python-basics-01-01", source="self_report"
            )
    finally:
        db.close()
