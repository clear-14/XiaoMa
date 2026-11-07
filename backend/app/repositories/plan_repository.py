"""学习计划数据访问层。"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.learning_plan import LearningPlan, LearningPlanVersion


class PlanRepository:
    """学习计划/版本/项目的数据库读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> LearningPlan | None:
        """按 ID 与用户查计划，预取全部版本与项目。"""
        stmt = (
            select(LearningPlan)
            .where(
                LearningPlan.id == plan_id,
                LearningPlan.user_id == user_id,
                LearningPlan.deleted_at.is_(None),
            )
            .options(
                selectinload(LearningPlan.versions).selectinload(
                    LearningPlanVersion.items
                )
            )
        )
        return self.db.scalars(stmt).first()

    def get_latest_plan(self, user_id: uuid.UUID) -> LearningPlan | None:
        """用户最近一份未删除计划（单用户产品下即当前计划）。"""
        stmt = (
            select(LearningPlan)
            .where(
                LearningPlan.user_id == user_id,
                LearningPlan.deleted_at.is_(None),
            )
            .order_by(LearningPlan.created_at.desc())
            .options(
                selectinload(LearningPlan.versions).selectinload(
                    LearningPlanVersion.items
                )
            )
        )
        return self.db.scalars(stmt).first()

    def add_plan(self, plan: LearningPlan) -> None:
        self.db.add(plan)

    def add_version(self, version: LearningPlanVersion) -> None:
        self.db.add(version)

    def flush(self) -> None:
        self.db.flush()
