"""测验与答题记录数据访问层。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import KnowledgePoint
from app.models.quiz import Question, QuizAnswer, QuizAttempt


class QuizRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_attempt(self, attempt: QuizAttempt) -> None:
        self.db.add(attempt)

    def add_answer(self, answer: QuizAnswer) -> None:
        self.db.add(answer)

    def get_attempt(
        self, attempt_id: uuid.UUID, user_id: uuid.UUID
    ) -> QuizAttempt | None:
        """按用户读取测验并预取题目、知识点与章节（答案/解析展示用）。"""
        stmt = (
            select(QuizAttempt)
            .where(
                QuizAttempt.id == attempt_id,
                QuizAttempt.user_id == user_id,
            )
            .options(
                selectinload(QuizAttempt.answers)
                .selectinload(QuizAnswer.question)
                .selectinload(Question.knowledge_point)
                .selectinload(KnowledgePoint.chapter)
            )
        )
        return self.db.scalars(stmt).first()

    def list_attempts(
        self, user_id: uuid.UUID, limit: int = 50, include_review: bool = False
    ) -> list[QuizAttempt]:
        stmt = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        if not include_review:
            stmt = stmt.where(QuizAttempt.scope_type != "review")
        stmt = stmt.order_by(QuizAttempt.started_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def flush(self) -> None:
        self.db.flush()
