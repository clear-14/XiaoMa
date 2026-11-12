"""知识点掌握度数据访问层（knowledge_mastery / mastery_evidence / exercise_attempts）。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Chapter, Course, Exercise, KnowledgePoint
from app.models.mastery import (
    ExerciseAttempt,
    KnowledgeMastery,
    MasteryEvidence,
)


class MasteryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------- 当前态

    def get(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID
    ) -> KnowledgeMastery | None:
        stmt = select(KnowledgeMastery).where(
            KnowledgeMastery.user_id == user_id,
            KnowledgeMastery.knowledge_point_id == knowledge_point_id,
        )
        return self.db.scalars(stmt).first()

    def add(self, mastery: KnowledgeMastery) -> KnowledgeMastery:
        self.db.add(mastery)
        return mastery

    def list_for_user(self, user_id: uuid.UUID) -> list[KnowledgeMastery]:
        """用户的全部掌握记录（带知识点、章节与课程，按课程顺序返回）。"""
        stmt = (
            select(KnowledgeMastery)
            .join(
                KnowledgePoint,
                KnowledgePoint.id == KnowledgeMastery.knowledge_point_id,
            )
            .where(
                KnowledgeMastery.user_id == user_id,
                KnowledgePoint.deleted_at.is_(None),
            )
            .options(
                selectinload(KnowledgeMastery.knowledge_point)
                .selectinload(KnowledgePoint.chapter)
                .selectinload(Chapter.course)
            )
        )
        records = list(self.db.scalars(stmt).all())
        records.sort(key=self._order_key)
        return records

    def list_for_course(
        self, user_id: uuid.UUID, course_code: str
    ) -> list[KnowledgeMastery]:
        return [
            record
            for record in self.list_for_user(user_id)
            if record.knowledge_point.chapter.course.code == course_code
        ]

    @staticmethod
    def _order_key(record: KnowledgeMastery) -> tuple:
        kp = record.knowledge_point
        chapter = kp.chapter
        course = chapter.course
        return (
            course.sort_order,
            course.code,
            chapter.order_index,
            kp.order_index,
            kp.code,
        )

    def status_map(
        self, user_id: uuid.UUID, knowledge_point_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not knowledge_point_ids:
            return {}
        stmt = select(
            KnowledgeMastery.knowledge_point_id, KnowledgeMastery.status
        ).where(
            KnowledgeMastery.user_id == user_id,
            KnowledgeMastery.knowledge_point_id.in_(knowledge_point_ids),
        )
        return {kp_id: status for kp_id, status in self.db.execute(stmt).all()}

    def summary_map(
        self, user_id: uuid.UUID, knowledge_point_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, int]]:
        """阶段 6：批量取「当前掌握状态 + 证据条数」，供每日任务输出关联证据。

        返回 ``{kp_id: (status, evidence_count)}``；没有记录的知识点视为
        ``not_started`` / 0，不伪造证据。
        """
        if not knowledge_point_ids:
            return {}
        stmt = select(
            KnowledgeMastery.knowledge_point_id,
            KnowledgeMastery.status,
            KnowledgeMastery.evidence_count,
        ).where(
            KnowledgeMastery.user_id == user_id,
            KnowledgeMastery.knowledge_point_id.in_(knowledge_point_ids),
        )
        return {
            kp_id: (status, int(count or 0))
            for kp_id, status, count in self.db.execute(stmt).all()
        }

    def mastered_kp_codes(self, user_id: uuid.UUID) -> set[str]:
        """有 MASTERED 证据的知识点 code 集合（跳级与排期跳过的唯一依据）。"""
        stmt = (
            select(KnowledgePoint.code)
            .join(
                KnowledgeMastery,
                KnowledgeMastery.knowledge_point_id == KnowledgePoint.id,
            )
            .where(
                KnowledgeMastery.user_id == user_id,
                KnowledgeMastery.status == "mastered",
            )
        )
        return set(self.db.scalars(stmt).all())

    # ------------------------------------------------------------- 证据流水

    def count_evidence_by_source(
        self, user_id: uuid.UUID, source: str
    ) -> int:
        """阶段 6：按来源统计掌握证据条数（placement = 诊断/跳级验证）。"""
        from sqlalchemy import func

        stmt = select(func.count(MasteryEvidence.id)).where(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.source == source,
        )
        return int(self.db.scalar(stmt) or 0)

    def add_evidence(self, evidence: MasteryEvidence) -> MasteryEvidence:
        self.db.add(evidence)
        return evidence

    def list_evidence(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID, limit: int = 20
    ) -> list[MasteryEvidence]:
        stmt = (
            select(MasteryEvidence)
            .where(
                MasteryEvidence.user_id == user_id,
                MasteryEvidence.knowledge_point_id == knowledge_point_id,
            )
            .order_by(MasteryEvidence.created_at.desc(), MasteryEvidence.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    # ------------------------------------------------------------- 练习记录

    def add_exercise_attempt(self, attempt: ExerciseAttempt) -> ExerciseAttempt:
        self.db.add(attempt)
        return attempt

    def get_exercise_by_code(self, code: str) -> Exercise | None:
        stmt = select(Exercise).where(
            Exercise.code == code, Exercise.deleted_at.is_(None)
        )
        return self.db.scalars(stmt).first()

    def list_exercise_attempts(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID, limit: int = 20
    ) -> list[ExerciseAttempt]:
        stmt = (
            select(ExerciseAttempt)
            .where(
                ExerciseAttempt.user_id == user_id,
                ExerciseAttempt.knowledge_point_id == knowledge_point_id,
            )
            .order_by(ExerciseAttempt.graded_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_course_by_code(self, code: str) -> Course | None:
        stmt = select(Course).where(
            Course.code == code, Course.deleted_at.is_(None)
        )
        return self.db.scalars(stmt).first()
