"""错题复习接口测试：待复习任务、1/3/7/14 天推进、答错重置与历史记录。"""

import uuid

from sqlalchemy import func, select

from app.models.quiz import Mistake, Question, QuizAnswer, QuizAttempt, ReviewTask
from tests.test_quiz_api import (
    _canonical,
    _create_quiz,
    _learn,
    _seed,
    _submit_body,
)


def _wrong_quiz(client, factory) -> None:
    quiz = _create_quiz(
        client,
        scope_type="knowledge_point",
        knowledge_point_code="python-basics-01-01",
    )
    body = _submit_body(factory, quiz["questions"], correct=False)
    resp = client.post(f"/api/v1/quizzes/{quiz['id']}/submit", json=body)
    assert resp.status_code == 200, resp.text


def _tasks(client) -> list[dict]:
    resp = client.get("/api/v1/reviews/tasks")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _submit_review(client, factory, task: dict, *, correct: bool) -> dict:
    db = factory()
    try:
        question = db.get(Question, uuid.UUID(task["question"]["id"]))
        assert question is not None
        answer = _canonical(question) if correct else "wrong"
    finally:
        db.close()
    resp = client.post(
        f"/api/v1/reviews/tasks/{task['id']}/submit",
        json={"answer": answer},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_review_progresses_through_1_3_7_14_and_resolves(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])
    _wrong_quiz(client, factory)

    tasks = _tasks(client)
    assert len(tasks) == 3
    current = tasks[0]
    question_id = current["question"]["id"]

    first = _submit_review(client, factory, current, correct=True)
    assert first["review_task"]["status"] == "completed"
    assert first["review_task"]["last_result"] == "correct"
    assert first["question"]["correct_answer"] is not None
    assert first["question"]["explanation"]
    assert first["mistake"]["review_stage"] == 1
    assert first["mistake"]["review_status"] == "pending"
    assert first["next_review_task"]["interval_days"] == 3
    assert first["next_review_task"]["question"]["correct_answer"] is None
    assert "3 天后" in first["message"]

    second = _submit_review(client, factory, first["next_review_task"], correct=True)
    assert second["next_review_task"]["interval_days"] == 7
    third = _submit_review(client, factory, second["next_review_task"], correct=True)
    assert third["next_review_task"]["interval_days"] == 14
    fourth = _submit_review(client, factory, third["next_review_task"], correct=True)

    assert fourth["next_review_task"] is None
    assert fourth["mistake"]["review_status"] == "resolved"
    assert fourth["mistake"]["review_stage"] == 4
    assert fourth["mistake"]["resolved_at"]
    assert fourth["mistake"]["next_review_at"] is None
    assert "已解决" in fourth["message"]

    # 已完成的复习任务不能重复提交
    resp = client.post(
        f"/api/v1/reviews/tasks/{fourth['review_task']['id']}/submit",
        json={"answer": "wrong"},
    )
    assert resp.status_code == 409, resp.text

    # 每次复习都保留一条 scope_type=review 的测验与答题记录
    db = factory()
    try:
        attempts = list(
            db.scalars(
                select(QuizAttempt).where(QuizAttempt.scope_type == "review")
            ).all()
        )
        assert len(attempts) == 4
        assert all(attempt.status == "submitted" for attempt in attempts)
        answers = list(
            db.scalars(
                select(QuizAnswer)
                .join(QuizAttempt)
                .where(QuizAttempt.scope_type == "review")
            ).all()
        )
        assert len(answers) == 4
        assert all(answer.grading_basis for answer in answers)
        completed = db.scalar(
            select(func.count())
            .select_from(ReviewTask)
            .where(
                ReviewTask.question_id == uuid.UUID(question_id),
                ReviewTask.status == "completed",
            )
        )
        assert completed == 4
        mistake = db.scalars(
            select(Mistake).where(
                Mistake.question_id == uuid.UUID(question_id)
            )
        ).one()
        assert mistake.review_status == "resolved"
    finally:
        db.close()

    resp = client.get("/api/v1/mistakes", params={"review_status": "resolved"})
    assert resp.status_code == 200
    resolved = resp.json()
    assert len(resolved) == 1
    assert resolved[0]["review_stage"] == 4
    assert resolved[0]["pending_review_task_id"] is None

    resp = client.get("/api/v1/mistakes", params={"review_status": "pending"})
    assert len(resp.json()) == 2


def test_wrong_review_resets_interval_and_updates_attempt_count(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])
    _wrong_quiz(client, factory)

    current = _tasks(client)[0]
    result = _submit_review(client, factory, current, correct=False)

    assert result["review_task"]["last_result"] == "wrong"
    assert result["mistake"]["review_stage"] == 0
    assert result["mistake"]["review_status"] == "pending"
    assert result["mistake"]["attempt_count"] == 2
    assert result["next_review_task"]["interval_days"] == 1
    assert "重置" in result["message"]

    db = factory()
    try:
        attempt = db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.scope_type == "review")
            .order_by(QuizAttempt.started_at.desc())
        ).first()
        assert attempt is not None
        assert attempt.score == 0.0
        answer = db.scalars(
            select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id)
        ).one()
        assert answer.is_correct is False
        assert answer.grading_basis
    finally:
        db.close()


def test_review_task_list_only_returns_pending_tasks(api_env):
    client, factory = api_env
    _seed(factory)
    _learn(factory, ["python-basics-01-01"])
    _wrong_quiz(client, factory)

    first = _tasks(client)[0]
    _submit_review(client, factory, first, correct=True)

    tasks = _tasks(client)
    assert len(tasks) == 3  # 1 个新任务 + 另外 2 道错题的待复习任务
    assert all(task["status"] == "pending" for task in tasks)
    assert first["id"] not in {task["id"] for task in tasks}
