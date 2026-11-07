"""知识点学习档案（learning_profiles）数据访问层。

状态机与写入规则见 PRD 6.1：用户点击任务完成不得直接将知识点标记为
mastered，必须经系统规定的掌握验证（由测验阶段实现）。
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import KnowledgePoint
from app.models.learning_profile import LearningProfile

# 「已学习」状态：只有这些状态的知识点允许进入正式测验。
LEARNED_STATUSES: tuple[str, ...] = (
    "learning",
    "pending_verification",
    "mastered",
    "review_due",
)


class LearningProfileRepository:
    """用户对单个知识点的学习状态记录读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_mastered_kp_codes(self, user_id: uuid.UUID) -> set[str]:
        """用户已通过掌握验证的知识点稳定 code 集合（每日任务排程排除用）。"""
        stmt = (
            select(KnowledgePoint.code)
            .join(
                LearningProfile,
                LearningProfile.knowledge_point_id == KnowledgePoint.id,
            )
            .where(
                LearningProfile.user_id == user_id,
                LearningProfile.status == "mastered",
            )
        )
        return set(self.db.scalars(stmt).all())

    def get_profile(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID
    ) -> LearningProfile | None:
        """用户对某知识点的状态记录（无记录时返回 None）。"""
        stmt = select(LearningProfile).where(
            LearningProfile.user_id == user_id,
            LearningProfile.knowledge_point_id == knowledge_point_id,
        )
        return self.db.scalars(stmt).first()

    def create_profile(
        self,
        user_id: uuid.UUID,
        knowledge_point_id: uuid.UUID,
        *,
        status: str = "not_started",
        started_at=None,
    ) -> LearningProfile:
        """创建状态记录（user_id + knowledge_point_id 唯一，由调用方保证不重复）。"""
        profile = LearningProfile(
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            status=status,
            started_at=started_at,
        )
        self.db.add(profile)
        return profile

    def list_learned(self, user_id: uuid.UUID) -> list[LearningProfile]:
        """用户已学习知识点的状态记录（含知识点与章节），按课程顺序排列。"""
        stmt = (
            select(LearningProfile)
            .join(
                KnowledgePoint,
                KnowledgePoint.id == LearningProfile.knowledge_point_id,
            )
            .where(
                LearningProfile.user_id == user_id,
                LearningProfile.status.in_(LEARNED_STATUSES),
                KnowledgePoint.deleted_at.is_(None),
            )
            .options(
                selectinload(LearningProfile.knowledge_point).selectinload(
                    KnowledgePoint.chapter
                )
            )
        )
        profiles = list(self.db.scalars(stmt).all())
        profiles.sort(
            key=lambda item: (
                item.knowledge_point.chapter.order_index,
                item.knowledge_point.order_index,
                item.knowledge_point.code,
            )
        )
        return profiles

    def set_mastered(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID, now: datetime
    ) -> None:
        """测验满足掌握条件后写入 mastered；已有记录才更新（已学习知识点必有）。"""
        profile = self.get_profile(user_id, knowledge_point_id)
        if profile is None:
            self.create_profile(
                user_id,
                knowledge_point_id,
                status="mastered",
                started_at=now,
            )
            return
        profile.status = "mastered"
        profile.mastered_at = now
        if profile.started_at is None:
            profile.started_at = now
