"""错题与复习任务数据访问层。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import KnowledgePoint
from app.models.quiz import Mistake, Question, ReviewTask


def _task_options():
    return (
        selectinload(ReviewTask.question)
        .selectinload(Question.knowledge_point)
        .selectinload(KnowledgePoint.chapter),
        selectinload(ReviewTask.knowledge_point).selectinload(
            KnowledgePoint.chapter
        ),
    )


class MistakeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, mistake: Mistake) -> None:
        self.db.add(mistake)

    def get(self, user_id: uuid.UUID, question_id: uuid.UUID) -> Mistake | None:
        stmt = select(Mistake).where(
            Mistake.user_id == user_id,
            Mistake.question_id == question_id,
        )
        return self.db.scalars(stmt).first()

    def get_by_id(
        self, mistake_id: uuid.UUID, user_id: uuid.UUID
    ) -> Mistake | None:
        stmt = (
            select(Mistake)
            .where(Mistake.id == mistake_id, Mistake.user_id == user_id)
            .options(
                selectinload(Mistake.question)
                .selectinload(Question.knowledge_point)
                .selectinload(KnowledgePoint.chapter),
                selectinload(Mistake.knowledge_point).selectinload(
                    KnowledgePoint.chapter
                ),
            )
        )
        return self.db.scalars(stmt).first()

    def list_for_user(
        self, user_id: uuid.UUID, review_status: str | None = None
    ) -> list[Mistake]:
        stmt = (
            select(Mistake)
            .where(Mistake.user_id == user_id)
            .options(
                selectinload(Mistake.question)
                .selectinload(Question.knowledge_point)
                .selectinload(KnowledgePoint.chapter),
                selectinload(Mistake.knowledge_point).selectinload(
                    KnowledgePoint.chapter
                ),
            )
            .order_by(Mistake.last_wrong_at.desc())
        )
        if review_status is not None:
            stmt = stmt.where(Mistake.review_status == review_status)
        return list(self.db.scalars(stmt).all())

    def flush(self) -> None:
        self.db.flush()


class ReviewTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, task: ReviewTask) -> None:
        self.db.add(task)

    def get(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> ReviewTask | None:
        stmt = (
            select(ReviewTask)
            .where(ReviewTask.id == task_id, ReviewTask.user_id == user_id)
            .options(*_task_options())
        )
        return self.db.scalars(stmt).first()

    def list_pending(self, user_id: uuid.UUID) -> list[ReviewTask]:
        stmt = (
            select(ReviewTask)
            .where(
                ReviewTask.user_id == user_id,
                ReviewTask.status == "pending",
            )
            .options(*_task_options())
            .order_by(ReviewTask.due_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_pending_for_mistake(self, mistake_id: uuid.UUID) -> list[ReviewTask]:
        stmt = select(ReviewTask).where(
            ReviewTask.mistake_id == mistake_id,
            ReviewTask.status == "pending",
        )
        return list(self.db.scalars(stmt).all())

    def get_pending_for_mistake(
        self, mistake_id: uuid.UUID
    ) -> ReviewTask | None:
        return self.db.scalars(
            select(ReviewTask)
            .where(
                ReviewTask.mistake_id == mistake_id,
                ReviewTask.status == "pending",
            )
            .order_by(ReviewTask.due_at.asc())
        ).first()

    def map_pending_for_user(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, ReviewTask]:
        """用户每道错题最近一条待复习任务（错题本展示入口）。"""
        stmt = (
            select(ReviewTask)
            .where(
                ReviewTask.user_id == user_id,
                ReviewTask.status == "pending",
            )
            .order_by(ReviewTask.due_at.asc())
        )
        result: dict[uuid.UUID, ReviewTask] = {}
        for task in self.db.scalars(stmt).all():
            result.setdefault(task.mistake_id, task)
        return result

    def flush(self) -> None:
        self.db.flush()
