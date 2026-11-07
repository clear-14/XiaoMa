"""测验接口测试：范围限制、组卷、提交评分、掌握判定与 AI 降级。"""

import uuid

from sqlalchemy import select

from app.models.course import KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.quiz import Question
from app.models.user import User
from app.seed.course_seed import seed_courses
from app.seed.question_seed import seed_questions
from app.services.ai_question_service import AiQuestionService
from app.services.time_utils import utc_now_naive


def _seed(factory) -> None:
    db = factory()
    try:
        seed_courses(db)
        seed_questions(db)
    finally:
        db.close()


def _ensure_user(db) -> User:
    user = db.scalars(select(User).where(User.username == "local")).first()
    if user is None:
        user = User(username="local")
        db.add(user)
        db.flush()
    return user


def _learn(factory, codes: list[str], status: str = "pending_verification") -> None:
    db = factory()
    try:
        user = _ensure_user(db)
        for code in codes:
            kp = db.scalars(
                select(KnowledgePoint).where(KnowledgePoint.code == code)
            ).one()
            existing = db.scalars(
                select(LearningProfile).where(
                    LearningProfile.user_id == user.id,
                    LearningProfile.knowledge_point_id == kp.id,
                )
            ).first()
            if existing is None:
                db.add(
                    LearningProfile(
                        user_id=user.id,
                        knowledge_point_id=kp.id,
                        status=status,
                        started_at=utc_now_naive(),
                    )
                )
            else:
                existing.status = status
        db.commit()
    finally:
        db.close()


def _profile_status(factory, kp_code: str) -> str | None:
    db = factory()
    try:
        user = db.scalars(select(User).where(User.username == "local")).one()
        kp = db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == kp_code)
        ).one()
        profile = db.scalars(
            select(LearningProfile).where(
                LearningProfile.user_id == user.id,
                LearningProfile.knowledge_point_id == kp.id,
            )
        ).first()
        return profile.status if profile else None
    finally:
        db.close()


def _canonical(question: Question):
    answer = question.correct_answer
    if question.question_type == "single_choice":
        return answer["value"]
    if question.question_type == "multiple_choice":
        return answer["values"]
    if question.question_type == "true_false":
        return answer["value"]
    if question.question_type == "fill_blank":
        return answer["values"][0]
    return answer["reference"]


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


def _create_quiz(client, **payload):
    resp = client.post("/api/v1/quizzes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_and_confirm_plan(client) -> str:
    payload = {
        "course_code": "python-basics",
        "learning_goal": "三个月内掌握 Python 基础语法",
        "current_level": "L1",
        "daily_study_minutes": 45,
        "expected_duration_days": 30,
    }
    resp = client.post("/api/v1/plans", json=payload)
    assert resp.status_code == 201, resp.text
    plan_id = resp.json()["id"]
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    return plan_id


def test_eligibility_only_contains_learned_knowledge_points(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])

    resp = client.get("/api/v1/quizzes/eligibility")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [kp["code"] for kp in data["learned_knowledge_points"]] == [
        "python-basics-01-01"
    ]
    assert data["learned_knowledge_points"][0]["question_count"] == 3
    assert data["learned_knowledge_points"][0]["quiz_available"] is True
    assert [chapter["code"] for chapter in data["chapters"]] == ["python-basics-01"]
    assert data["chapters"][0]["question_count"] == 3
    assert data["stage"]["available"] is False
    assert data["stage"]["note"]


def test_knowledge_point_quiz_submit_and_mastery(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    assert quiz["status"] == "in_progress"
    assert quiz["question_count"] == 3
    assert {q["knowledge_point"]["code"] for q in quiz["questions"]} == {
        "python-basics-01-01"
    }
    # 未提交前不泄露答案与解析
    for question in quiz["questions"]:
        assert question["correct_answer"] is None
        assert question["explanation"] is None
        assert question["is_correct"] is None
        assert question["grading_basis"] is None

    # 少交一题应被拒绝
    partial = _submit_body(factory, quiz["questions"][:2], correct=True)
    resp = client.post(f"/api/v1/quizzes/{quiz['id']}/submit", json=partial)
    assert resp.status_code == 400, resp.text

    body = _submit_body(factory, quiz["questions"], correct=True)
    resp = client.post(f"/api/v1/quizzes/{quiz['id']}/submit", json=body)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["status"] == "submitted"
    assert result["score"] == 100.0
    assert len(result["mastery_updates"]) == 1
    update = result["mastery_updates"][0]
    assert update["knowledge_point_code"] == "python-basics-01-01"
    assert update["achieved"] is True
    assert update["reasons"]

    for question in result["questions"]:
        assert question["correct_answer"] is not None
        assert question["explanation"]
        assert question["is_correct"] is True
        assert question["score"] == 10
        assert question["grading_basis"]
    subjective = [
        q for q in result["questions"] if q["question_type"] == "code_writing"
    ]
    assert subjective and subjective[0]["grading_basis"]["type"] == "keyword_rubric"
    assert subjective[0]["grading_basis"]["reference"]

    assert _profile_status(factory, "python-basics-01-01") == "mastered"

    resp = client.post(f"/api/v1/quizzes/{quiz['id']}/submit", json=body)
    assert resp.status_code == 409, resp.text

    resp = client.get("/api/v1/quizzes")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["scope_type"] == "knowledge_point"
    assert history[0]["score"] == 100.0


def test_unlearned_knowledge_point_and_empty_chapter_are_rejected(api_env):
    client, factory = api_env
    _seed(factory)

    resp = client.get("/api/v1/quizzes/eligibility")
    assert resp.status_code == 200
    assert resp.json()["learned_knowledge_points"] == []

    resp = client.post(
        "/api/v1/quizzes",
        json={
            "scope_type": "knowledge_point",
            "knowledge_point_code": "python-basics-01-01",
        },
    )
    assert resp.status_code == 400, resp.text
    assert "尚未学习" in resp.json()["detail"]

    resp = client.post(
        "/api/v1/quizzes",
        json={"scope_type": "chapter", "chapter_code": "python-basics-01"},
    )
    assert resp.status_code == 400, resp.text
    assert "已学习" in resp.json()["detail"]


def test_wrong_answers_are_saved_and_mastery_is_rejected(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    body = _submit_body(factory, quiz["questions"], correct=False)
    resp = client.post(f"/api/v1/quizzes/{quiz['id']}/submit", json=body)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["score"] == 0.0
    update = result["mastery_updates"][0]
    assert update["achieved"] is False
    assert any("未通过" in reason for reason in update["reasons"])
    assert _profile_status(factory, "python-basics-01-01") == "pending_verification"

    resp = client.get("/api/v1/mistakes")
    assert resp.status_code == 200, resp.text
    mistakes = resp.json()
    assert len(mistakes) == 3
    for mistake in mistakes:
        assert mistake["review_status"] == "pending"
        assert mistake["review_stage"] == 0
        assert mistake["attempt_count"] == 1
        assert mistake["next_review_at"]
        assert mistake["pending_review_task_id"]
        # 错题本可查看解析
        assert mistake["question"]["correct_answer"] is not None
        assert mistake["question"]["explanation"]

    resp = client.get("/api/v1/reviews/tasks")
    assert resp.status_code == 200, resp.text
    tasks = resp.json()
    assert len(tasks) == 3
    for task in tasks:
        assert task["interval_days"] == 1
        assert task["status"] == "pending"
        assert task["is_due"] is False
        assert task["question"]["correct_answer"] is None
        assert task["question"]["explanation"] is None


def test_chapter_quiz_excludes_unlearned_knowledge_points(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01", "python-basics-01-02"])

    quiz = _create_quiz(
        client, scope_type="chapter", chapter_code="python-basics-01"
    )
    assert quiz["question_count"] == 6
    assert {q["knowledge_point"]["code"] for q in quiz["questions"]} == {
        "python-basics-01-01",
        "python-basics-01-02",
    }


def test_stage_quiz_requires_confirmed_plan_and_uses_learned_scope(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])

    resp = client.post("/api/v1/quizzes", json={"scope_type": "stage"})
    assert resp.status_code == 404, resp.text

    _create_and_confirm_plan(client)

    resp = client.get("/api/v1/quizzes/eligibility")
    stage = resp.json()["stage"]
    assert stage["available"] is True
    assert stage["course_code"] == "python-basics"
    assert stage["learned_knowledge_point_count"] == 1
    assert stage["question_count"] == 3

    quiz = _create_quiz(client, scope_type="stage")
    assert quiz["question_count"] == 3
    assert quiz["scope_ref"] is None
    assert {q["knowledge_point"]["code"] for q in quiz["questions"]} == {
        "python-basics-01-01"
    }


def test_ai_variant_failure_falls_back_to_builtin_bank(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])

    async def fake_generate(self, sources, count):
        return [], "AI 变式题：请求 1 道，没有题目通过验证，已使用内置题库"

    monkeypatch.setattr(AiQuestionService, "generate_variants", fake_generate)

    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
        ai_variant_count=1,
    )
    assert quiz["question_count"] == 3
    assert quiz["ai_requested"] == 1
    assert quiz["ai_accepted"] == 0
    assert "已使用内置题库" in quiz["ai_note"]
    assert all(q["source"] == "builtin" for q in quiz["questions"])
