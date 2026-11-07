"""测验相关输出组装（API / 复习 / 错题共用）。"""

from __future__ import annotations

from typing import Any

from app.models.quiz import Question, QuizAnswer
from app.schemas.quiz import (
    QuestionOptionOut,
    QuizKnowledgePointOut,
    QuizQuestionOut,
)


def knowledge_point_out(kp) -> QuizKnowledgePointOut:
    return QuizKnowledgePointOut(
        code=kp.code,
        name=kp.name,
        chapter_code=kp.chapter.code,
        chapter_title=kp.chapter.title,
    )


def question_out(
    question: Question,
    *,
    order: int = 0,
    answer: QuizAnswer | None = None,
    include_result: bool = False,
    user_answer: Any = None,
) -> QuizQuestionOut:
    """组装题目输出；未提交/未复习时不得泄露答案与解析。"""
    if answer is not None:
        user_answer = answer.user_answer
    return QuizQuestionOut(
        id=question.id,
        order=order,
        question_type=question.question_type,
        stem=question.stem,
        options=(
            [QuestionOptionOut(**item) for item in question.options]
            if question.options
            else None
        ),
        points=answer.max_score if answer is not None else 10,
        source=question.source,
        knowledge_point=knowledge_point_out(question.knowledge_point),
        user_answer=user_answer,
        correct_answer=question.correct_answer if include_result else None,
        explanation=question.explanation if include_result else None,
        score=answer.score if answer is not None else None,
        max_score=answer.max_score if answer is not None else 10,
        is_correct=answer.is_correct if answer is not None else None,
        grading_basis=answer.grading_basis if answer is not None else None,
    )
