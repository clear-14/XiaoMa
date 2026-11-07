"""AI 变式题验证测试：结构校验、独立复核与失败降级（不调用真实模型）。"""

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.quiz import Question
from app.repositories.question_repository import QuestionRepository
from app.seed.course_seed import seed_courses
from app.seed.question_seed import seed_questions
from app.services.ai_question_service import (
    AiQuestionService,
    validate_generated_payload,
)
from app.services.llm_client import LlmRequest
from app.services.model_config_service import ModelConfigService


def _prepare(db):
    seed_courses(db)
    seed_questions(db)
    source = QuestionRepository(db).get_by_code("q-python-basics-01-01-1")
    assert source is not None
    return source


def _payload(source):
    kp = source.knowledge_point
    return {
        "question_type": "single_choice",
        "stem": "以下哪项最能说明 Python 是一种高级语言？",
        "options": [
            {"key": "A", "text": "语法接近自然语言并由解释器执行"},
            {"key": "B", "text": "直接由 CPU 逐条执行机器码"},
            {"key": "C", "text": "只能保存数字"},
        ],
        "correct_answer": {"value": "A"},
        "explanation": "Python 语法接近自然语言，源码由解释器执行，因此属于高级语言。",
        "knowledge_point_code": kp.code,
        "difficulty": kp.difficulty,
    }


def _llm_request() -> LlmRequest:
    return LlmRequest(
        provider="deepseek",
        model_name="test-model",
        base_url=None,
        api_key="test-key",
        temperature=0.7,
        max_tokens=512,
        timeout=30,
    )


def test_valid_payload_passes_structure_validation(db_session):
    source = _prepare(db_session)
    assert validate_generated_payload(_payload(source), source.knowledge_point, source) == []


def test_structure_validation_rejects_wrong_type_copied_stem_and_bad_answer(db_session):
    source = _prepare(db_session)
    payload = _payload(source)
    payload["question_type"] = "true_false"
    assert any("题型" in issue for issue in validate_generated_payload(payload, source.knowledge_point, source))

    payload = _payload(source)
    payload["stem"] = source.stem
    assert any("照抄" in issue for issue in validate_generated_payload(payload, source.knowledge_point, source))

    payload = _payload(source)
    payload["correct_answer"] = {"value": "Z"}
    assert any("选项" in issue for issue in validate_generated_payload(payload, source.knowledge_point, source))

    payload = _payload(source)
    payload["knowledge_point_code"] = "python-basics-99-99"
    payload["difficulty"] = "advanced"
    issues = validate_generated_payload(payload, source.knowledge_point, source)
    assert any("知识点" in issue for issue in issues)
    assert any("难度" in issue for issue in issues)


def test_verification_reasons_requires_flags_and_matching_answer():
    payload = {"question_type": "single_choice", "correct_answer": {"value": "A"}}
    good = {
        "answer_correct": True,
        "verified_answer": {"value": "a"},
        "explanation_ok": True,
        "knowledge_point_ok": True,
        "within_scope": True,
    }
    assert AiQuestionService._verification_reasons(payload, good) == []

    bad = dict(good, answer_correct=False, explanation_ok=False, within_scope=False)
    reasons = AiQuestionService._verification_reasons(payload, bad)
    assert any("答案" in reason for reason in reasons)
    assert any("解析" in reason for reason in reasons)
    assert any("范围" in reason for reason in reasons)

    mismatched = dict(good, verified_answer={"value": "B"})
    assert any("不一致" in reason for reason in AiQuestionService._verification_reasons(payload, mismatched))


def test_generate_variants_saves_only_fully_verified_question(db_session, monkeypatch):
    source = _prepare(db_session)
    payload = _payload(source)

    async def fake_generate(self, source_question, llm_request):
        return payload

    async def fake_verify(self, candidate, knowledge_point, llm_request):
        return {
            "answer_correct": True,
            "verified_answer": {"value": "A"},
            "explanation_ok": True,
            "knowledge_point_ok": True,
            "within_scope": True,
            "reason": "答案与知识点一致",
        }

    monkeypatch.setattr(
        ModelConfigService,
        "get_default_llm_request",
        lambda self: (_llm_request(), "test-model"),
    )
    monkeypatch.setattr(AiQuestionService, "_generate_payload", fake_generate)
    monkeypatch.setattr(AiQuestionService, "_verify_payload", fake_verify)

    accepted, note = asyncio.run(
        AiQuestionService(db_session).generate_variants([source], 1)
    )

    assert len(accepted) == 1
    assert "通过验证 1 道" in note
    question = accepted[0]
    assert question.source == "ai"
    assert question.status == "approved"
    assert question.validation_status == "ai_validated"
    assert question.generated_from_id == source.id
    assert "test-model" in (question.validation_notes or "")
    assert db_session.scalar(select(func.count()).select_from(Question)) == 94


def test_generate_variants_rejects_when_verification_fails(db_session, monkeypatch):
    source = _prepare(db_session)
    payload = _payload(source)

    async def fake_generate(self, source_question, llm_request):
        return payload

    async def fake_verify(self, candidate, knowledge_point, llm_request):
        return {
            "answer_correct": False,
            "verified_answer": {"value": "B"},
            "explanation_ok": True,
            "knowledge_point_ok": True,
            "within_scope": True,
            "reason": "独立作答认为是 B",
        }

    monkeypatch.setattr(
        ModelConfigService,
        "get_default_llm_request",
        lambda self: (_llm_request(), "test-model"),
    )
    monkeypatch.setattr(AiQuestionService, "_generate_payload", fake_generate)
    monkeypatch.setattr(AiQuestionService, "_verify_payload", fake_verify)

    accepted, note = asyncio.run(
        AiQuestionService(db_session).generate_variants([source], 1)
    )

    assert accepted == []
    assert "独立复核未通过" in note
    assert "已使用内置题库" in note
    assert db_session.scalar(select(func.count()).select_from(Question)) == 93


def test_generate_variants_rejects_structural_errors_without_verification(db_session, monkeypatch):
    source = _prepare(db_session)
    payload = _payload(source)
    payload["correct_answer"] = {"value": "Z"}

    async def fake_generate(self, source_question, llm_request):
        return payload

    async def fail_verify(self, candidate, knowledge_point, llm_request):
        raise AssertionError("结构校验失败时不应再调用独立复核")

    monkeypatch.setattr(
        ModelConfigService,
        "get_default_llm_request",
        lambda self: (_llm_request(), "test-model"),
    )
    monkeypatch.setattr(AiQuestionService, "_generate_payload", fake_generate)
    monkeypatch.setattr(AiQuestionService, "_verify_payload", fail_verify)

    accepted, note = asyncio.run(
        AiQuestionService(db_session).generate_variants([source], 1)
    )

    assert accepted == []
    assert "结构校验未通过" in note
    assert db_session.scalar(select(func.count()).select_from(Question)) == 93


def test_generate_variants_degrades_when_no_default_model(db_session, monkeypatch):
    source = _prepare(db_session)

    def no_model(self):
        raise HTTPException(status_code=409, detail="未配置默认模型")

    monkeypatch.setattr(ModelConfigService, "get_default_llm_request", no_model)

    accepted, note = asyncio.run(
        AiQuestionService(db_session).generate_variants([source], 2)
    )

    assert accepted == []
    assert "未配置默认模型" in note
    assert "已仅使用内置题库" in note
    assert db_session.scalar(select(func.count()).select_from(Question)) == 93
