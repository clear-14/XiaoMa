"""阶段 6 新增表的数据访问层（计划调整提案 / 复习申请）。

只做对象读写与 flush，事务提交由 Service 负责；所有查询按单用户过滤，
避免跨用户读到提案或复习申请。
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.phase6 import PlanAdjustmentProposal, ReviewRequest


class PlanAdjustmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, proposal: PlanAdjustmentProposal) -> PlanAdjustmentProposal:
        self.db.add(proposal)
        self.db.flush()
        return proposal

    def get(
        self, proposal_id: uuid.UUID, user_id: uuid.UUID
    ) -> PlanAdjustmentProposal | None:
        stmt = select(PlanAdjustmentProposal).where(
            PlanAdjustmentProposal.id == proposal_id,
            PlanAdjustmentProposal.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def list_for_user(
        self, user_id: uuid.UUID, status: str | None = None
    ) -> list[PlanAdjustmentProposal]:
        stmt = select(PlanAdjustmentProposal).where(
            PlanAdjustmentProposal.user_id == user_id
        )
        if status:
            stmt = stmt.where(PlanAdjustmentProposal.status == status)
        stmt = stmt.order_by(PlanAdjustmentProposal.created_at.desc())
        return list(self.db.scalars(stmt).all())


class ReviewRequestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_kp_date(
        self, user_id: uuid.UUID, knowledge_point_id: uuid.UUID, request_date: date
    ) -> ReviewRequest | None:
        stmt = (
            select(ReviewRequest)
            .where(
                ReviewRequest.user_id == user_id,
                ReviewRequest.knowledge_point_id == knowledge_point_id,
                ReviewRequest.request_date == request_date,
            )
            .options(selectinload(ReviewRequest.knowledge_point))
        )
        return self.db.scalars(stmt).first()

    def add(self, request: ReviewRequest) -> ReviewRequest:
        self.db.add(request)
        self.db.flush()
        return request

    def list_for_user(
        self, user_id: uuid.UUID, status: str | None = None
    ) -> list[ReviewRequest]:
        stmt = (
            select(ReviewRequest)
            .where(ReviewRequest.user_id == user_id)
            .options(selectinload(ReviewRequest.knowledge_point))
            .order_by(ReviewRequest.request_date.desc())
        )
        if status:
            stmt = stmt.where(ReviewRequest.status == status)
        return list(self.db.scalars(stmt).all())
