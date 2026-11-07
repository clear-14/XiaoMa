"""题库数据访问层。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import KnowledgePoint
from app.models.quiz import Question

# 正式组卷只允许：人工整理的内置题库，或通过独立验证的 AI 变式题。
SELECTABLE_VALIDATION_STATUSES = ("builtin", "ai_validated")


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, question: Question) -> None:
        self.db.add(question)

    def get_by_code(self, code: str) -> Question | None:
        return self.db.scalars(
            select(Question).where(Question.code == code)
        ).first()

    def get_by_id(self, question_id: uuid.UUID) -> Question | None:
        return self.db.get(Question, question_id)

    def list_selectable_by_knowledge_points(
        self, knowledge_point_ids: list[uuid.UUID]
    ) -> list[Question]:
        """指定知识点的正式可用题目（内置题库 + 已验证 AI 题）。"""
        if not knowledge_point_ids:
            return []
        stmt = (
            select(Question)
            .where(
                Question.knowledge_point_id.in_(knowledge_point_ids),
                Question.status == "approved",
                Question.validation_status.in_(SELECTABLE_VALIDATION_STATUSES),
            )
            .options(
                selectinload(Question.knowledge_point).selectinload(
                    KnowledgePoint.chapter
                )
            )
            .order_by(Question.knowledge_point_id, Question.code)
        )
        return list(self.db.scalars(stmt).all())

    def count_selectable_by_knowledge_point(self) -> dict[uuid.UUID, int]:
        """按知识点统计正式可用题目数量（可测验范围展示用）。"""
        stmt = (
            select(Question.knowledge_point_id, func.count(Question.id))
            .where(
                Question.status == "approved",
                Question.validation_status.in_(SELECTABLE_VALIDATION_STATUSES),
            )
            .group_by(Question.knowledge_point_id)
        )
        return {kp_id: count for kp_id, count in self.db.execute(stmt).all()}

    def stem_exists(self, knowledge_point_id: uuid.UUID, stem: str) -> bool:
        """同一知识点下题干完全相同的题目视为重复（AI 变式入库前去重）。"""
        stmt = select(Question.id).where(
            Question.knowledge_point_id == knowledge_point_id,
            Question.stem == stem,
        )
        return self.db.scalars(stmt).first() is not None

    def flush(self) -> None:
        self.db.flush()
