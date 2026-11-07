"""内置题库种子测试：覆盖范围、幂等、答案可评分与防覆盖。"""

import copy
from collections import Counter
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models.course import KnowledgePoint
from app.models.quiz import QUESTION_TYPES, Question
from app.seed import question_seed as question_seed_module
from app.seed.course_seed import seed_courses
from app.seed.question_seed import (
    QUESTION_SEED,
    seed_questions,
    validate_question_definitions,
)
from app.services.quiz_grading import grade_answer


def _canonical_answer(question_type: str, answer: dict):
    if question_type == "single_choice":
        return answer["value"]
    if question_type == "multiple_choice":
        return answer["values"]
    if question_type == "true_false":
        return answer["value"]
    if question_type == "fill_blank":
        return answer["values"][0]
    return answer["reference"]


def test_seed_definition_covers_all_knowledge_points_and_types():
    validate_question_definitions()
    assert len(QUESTION_SEED) == 31
    counts = Counter(
        item["type"] for items in QUESTION_SEED.values() for item in items
    )
    assert set(counts) == set(QUESTION_TYPES)


def test_validation_rejects_duplicate_stem(monkeypatch):
    data = copy.deepcopy(QUESTION_SEED)
    first, second = data["python-basics-01-01"][:2]
    second["stem"] = first["stem"]
    monkeypatch.setattr(question_seed_module, "QUESTION_SEED", data)

    with pytest.raises(ValueError, match="题干与"):
        validate_question_definitions()


def test_validation_rejects_duplicate_option_text(monkeypatch):
    data = copy.deepcopy(QUESTION_SEED)
    question = data["python-basics-01-01"][0]
    question["options"][1]["text"] = question["options"][0]["text"]
    monkeypatch.setattr(question_seed_module, "QUESTION_SEED", data)

    with pytest.raises(ValueError, match="选项配置不合法"):
        validate_question_definitions()


def test_seed_is_idempotent_and_every_question_is_gradable(db_session):
    seed_courses(db_session)
    first = seed_questions(db_session)
    second = seed_questions(db_session)

    assert first == {"created": 93, "updated": 0, "total": 93}
    assert second == {"created": 0, "updated": 93, "total": 93}
    assert db_session.scalar(select(func.count()).select_from(Question)) == 93

    questions = list(db_session.scalars(select(Question)).all())
    per_kp = Counter(str(question.knowledge_point_id) for question in questions)
    assert set(per_kp.values()) == {3}
    for question in questions:
        assert question.source == "builtin"
        assert question.validation_status == "builtin"
        assert question.status == "approved"
        assert question.validation_notes
        result = grade_answer(
            SimpleNamespace(
                question_type=question.question_type,
                correct_answer=question.correct_answer,
            ),
            _canonical_answer(question.question_type, question.correct_answer),
        )
        assert result.is_correct is True, question.code
        assert result.score == 10


def test_seed_updates_modified_question_without_duplicating(db_session):
    seed_courses(db_session)
    seed_questions(db_session)
    question = db_session.scalars(
        select(Question).where(Question.code == "q-python-basics-01-01-1")
    ).one()
    question.stem = "被人工修改过的题干内容"
    db_session.commit()

    seed_questions(db_session)

    rows = list(
        db_session.scalars(
            select(Question).where(Question.code == "q-python-basics-01-01-1")
        ).all()
    )
    assert len(rows) == 1
    assert rows[0].stem == QUESTION_SEED["python-basics-01-01"][0]["stem"]


def test_seed_requires_course_data(db_session):
    with pytest.raises(RuntimeError, match="seed-courses"):
        seed_questions(db_session)


def test_seed_refuses_to_overwrite_ai_question_with_same_code(db_session):
    seed_courses(db_session)
    knowledge_point = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-01")
    ).one()
    db_session.add(
        Question(
            code="q-python-basics-01-01-1",
            knowledge_point_id=knowledge_point.id,
            question_type="single_choice",
            stem="AI 题占用了内置题代码的测试题干",
            options=[{"key": "A", "text": "A"}, {"key": "B", "text": "B"}],
            correct_answer={"value": "A"},
            explanation="这是用于测试的解析内容。",
            difficulty="beginner",
            source="ai",
            status="approved",
            validation_status="ai_validated",
        )
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        seed_questions(db_session)
