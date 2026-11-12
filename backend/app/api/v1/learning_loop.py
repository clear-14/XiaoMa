"""阶段 6 接口：动态计划调整提案与复习申请。

所有写操作都经 Service：
- 提案接口只生成「待确认方案」，不产生计划版本；
- 确认接口是唯一会写入并生效学习计划版本的入口；
- 复习申请接口只写申请记录，掌握状态仍由测验/练习证据驱动。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.phase6 import (
    PlanAdjustmentProposalOut,
    PlanSignalsOut,
    ProposalConfirmOut,
    ProposalCreate,
    ReviewRequestIn,
    ReviewRequestOut,
)
from app.services.plan_adjustment_service import PlanAdjustmentService
from app.services.review_request_service import ReviewRequestService

router = APIRouter(tags=["learning-loop"])


@router.get(
    "/plan-adjustments/signals", response_model=PlanSignalsOut
)
def get_adjustment_signals(
    plan_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PlanSignalsOut:
    """盘点调整信号：先按真实数据判定；调用方声明的线索会明确标注为未实测。"""
    return PlanAdjustmentService(db).get_signals(plan_id)


@router.post(
    "/plan-adjustments/proposals",
    response_model=PlanAdjustmentProposalOut,
    status_code=201,
)
def create_proposal(
    payload: ProposalCreate, db: Session = Depends(get_db)
) -> PlanAdjustmentProposalOut:
    """生成待确认方案。**不保存、不生效**任何学习计划修改。"""
    return PlanAdjustmentService(db).propose(payload)


@router.get(
    "/plan-adjustments/proposals",
    response_model=list[PlanAdjustmentProposalOut],
)
def list_proposals(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PlanAdjustmentProposalOut]:
    """列出调整提案（可按 proposed / confirmed / rejected 过滤）。"""
    return PlanAdjustmentService(db).list_proposals(status)


@router.get(
    "/plan-adjustments/proposals/{proposal_id}",
    response_model=PlanAdjustmentProposalOut,
)
def get_proposal(
    proposal_id: uuid.UUID, db: Session = Depends(get_db)
) -> PlanAdjustmentProposalOut:
    """查看一份待确认方案的全部细节（确认前用户应能看到）。"""
    return PlanAdjustmentService(db).get_proposal(proposal_id)


@router.post(
    "/plan-adjustments/proposals/{proposal_id}/confirm",
    response_model=ProposalConfirmOut,
)
def confirm_proposal(
    proposal_id: uuid.UUID, db: Session = Depends(get_db)
) -> ProposalConfirmOut:
    """用户确认后，才生成并生效新的学习计划版本。"""
    return PlanAdjustmentService(db).confirm(proposal_id)


@router.post(
    "/plan-adjustments/proposals/{proposal_id}/reject",
    response_model=PlanAdjustmentProposalOut,
)
def reject_proposal(
    proposal_id: uuid.UUID, db: Session = Depends(get_db)
) -> PlanAdjustmentProposalOut:
    """拒绝方案：只改提案状态，计划保持原样。"""
    return PlanAdjustmentService(db).reject(proposal_id)


@router.post(
    "/review-requests", response_model=ReviewRequestOut, status_code=201
)
def create_review_request(
    payload: ReviewRequestIn, db: Session = Depends(get_db)
) -> ReviewRequestOut:
    """申请复习某知识点（幂等；返回真实待复习任务，不伪造任务）。"""
    return ReviewRequestService(db).request(payload)
